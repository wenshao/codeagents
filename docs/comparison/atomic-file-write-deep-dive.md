# Qwen Code 改进建议 — 原子文件写入与事务回滚 (Atomic File Write & Persistent Storage)

> 核心洞察：CLI Agent 的长期稳定性很大程度上取决于其持久化存储（会话历史、记忆缓存、项目配置）的健壮性。如果因为电脑意外断电或 OOM 导致写入进程中断，直接使用 `fs.writeFile` 极易留下半写文件，导致整个会话 JSON 彻底损坏报废。Claude Code 全面采用了“`temp + rename` 原子写”以及对超大结果（如几十 MB 的命令输出）的“Persist to disk”降级策略；而 Qwen Code 的绝大部分模块依然在使用有风险的直接覆写机制。
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md)

## 一、架构对比与数据损坏风险

### 1. Qwen Code 现状：直接写入与内存膨胀
Qwen Code 中核心的配置存储和会话存档，大量使用了 `fs.writeFile` 或同步的 `fs.writeFileSync`：
- **半写风险（Torn Writes）**：当写入一个 5MB 的会话历史 `history.json` 时，如果写入中途 Node.js 崩溃或遭遇断电，文件中可能只包含了一半的 JSON 结构，导致该文件彻底损坏且无法恢复，用户丢失所有对话进度。
- **历史内存膨胀**：如果一个工具（比如一次失败的 `npm build` 或者一个 `grep`）返回了 5 万行的日志（2MB 文本），这些数据会被直接原封不动地塞进 `history` 数组中持久化。这不仅导致下次启动读取缓慢，还会立刻撑爆大模型的输入上下文。

*注：虽然 Qwen Code 在 `packages/core/src/utils/atomicFileWrite.ts` 中实现了一个 `atomicWriteJSON`，但目前仅在实验性的 Arena 模块中使用，核心引擎仍处于裸奔状态。*

### 2. Claude Code 的解决方案：原子事务与防膨胀脱水
Claude Code 设计了两套底座机制来保证长对话的数据安全：

#### 机制一：全局原子写 (Atomic Rename)
所有的关键持久化（无论是 Session、TeamMemory 还是 Config），一律强制走包装好的原子写函数：
```typescript
// 1. 写到与目标同一磁盘的隐藏临时文件
await fs.writeFile(`${filePath}.tmp`, data);

// 2. 利用 POSIX 系统的 fs.rename() 的原子性，瞬间替换目标文件
await fs.rename(`${filePath}.tmp`, filePath);
```
由于 `rename` 在操作系统层是原子的，即使在此刻拔断电源，用户也只会看到“全新的文件”或“完好无损的旧文件”，绝不存在被写破了一半的损坏状态。

#### 机制二：大结果持久化降级 (Persist to Disk)
当检测到工具调用的输出（如 `BashTool` 的标准输出或大文件的 `FileReadTool`）超过了 `50K chars`（约 8MB 内存上限）时：
1. Claude Code **不会** 把这段文本放进历史消息记录（Message Array）中。
2. 而是调用 `persistToolResult` 函数，用 `SHA-256` 算个 Hash，将这 8MB 文本单独持久化到本地 `.claude/tool-results/` 目录下。
3. 在真实的对话历史中，只保存一个极短的“脱水占位符（Stub）”：
```xml
<persisted-output>
  Preview (first 2KB): npm WARN deprecated...
  Full output saved to: ~/.claude/tool-results/mcp-bash-1738...
</persisted-output>
```
这避免了 OOM 崩溃，也防止了无意义的海量垃圾日志污染下一次会话的大模型 Context。

## 二、Qwen Code 的改进路径 (P1 优先级)

保证用户数据（尤其是耗时几小时的 Coding Session 存档）绝对不丢失，是 Agent 工具的及格线要求。

### 阶段 1：全域推行原子写 (Rollout Atomic Write)
1. 找出项目中所有的 `fs.writeFileSync`、`fs.writeFile`（尤其是针对 `.qwen/sessions/`、`.qwen/config.json` 等高价值资产的操作）。
2. 全部替换为 `utils/atomicFileWrite.ts` 中提供的方案。
3. 确保临时文件和目标文件处于同一挂载点（Volume），否则 `rename` 会退化为非原子的 `copy+delete`（此时仍需处理跨盘回滚逻辑）。

### 阶段 2：引入 ToolResult 脱水存储
1. 新建 `utils/toolResultStorage.ts`，定义一个 `MAX_INLINE_RESULT_CHARS` 阈值（建议为 100,000，约 25K Tokens）。
2. 在 `agent-core.ts` 收集 `TOOL_RESULT` 事件时，对 `result.length > 阈值` 的内容进行截断（保留前后各 10% 的摘要供大模型判断执行是否成功）。
3. 将完整内容异步写入到磁盘的 `.qwen/tool-results/` 目录下。

### 阶段 3：会话恢复清理机制
1. 当用户运行 `/clear` 清除缓存或退出长会话时，启动一个无阻塞的后台 Worker。
2. 清理超过 7 天的 `tool-results` 脱水文件，防止长期运行占用过多硬盘空间。

## 三、改进收益评估
- **实现成本**：低。Qwen Code 已有 `atomicWriteJSON` 基础工具，只需大规模重构替换。持久化降级逻辑只需几十行代码。
- **直接收益**：
  1. **告别丢存档**：彻底根绝由于异常退出导致的 "Session JSON parse error" 致命 Bug。
  2. **避免内存 OOM**：让 Agent 可以安全执行极长输出的打包或编译命令，无需担心缓冲区撑爆 Node.js 内存。
  3. **降低 Token 费用**：只给大模型看长命令的头尾截断，阻止了无效日志刷屏带来的天价 Token 账单。