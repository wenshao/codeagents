# Qwen Code 功能补全建议：对标 Claude Code

> 基于源码逐项比对，识别 Qwen Code 应该补全的 Claude Code 功能

## 功能全景对比

| 功能 | Claude Code | Qwen Code | 状态 |
|------|------------|-----------|------|
| **核心代理循环** | ✅ | ✅ | 对等 |
| Git Worktree | ✅ | ✅ `gitWorktreeService.ts` | 对等 |
| 子代理/Task 工具 | ✅ | ✅ `subagent-manager.ts` | 对等 |
| Plan 模式 | ✅ | ✅ | 对等 |
| Hook 系统（11+ 事件） | ✅ | ✅ 11 个事件类型 | 对等 |
| MCP 集成 | ✅ | ✅ `mcp-client.ts` | 对等 |
| 会话恢复 | ✅ `--resume` | ✅ `resumeHistoryUtils.ts` | 对等 |
| 自动记忆 | ✅ | ✅ `memoryTool.ts` | 对等 |
| 非交互模式 | ✅ `-p` | ✅ `--prompt` + `--output-format` | 对等 |
| 上下文压缩 | ✅ + 断路器（N 次计数） | ✅ + 简单断路器（布尔标志） | Qwen 断路器较简单 |
| 操作检查点 | ✅ 隐含 | ✅ `checkpointService.ts` + `/restore` | Qwen 更强 |
| 扩展思维/推理 | ✅ | ✅ `thinkingConfig` | 对等 |
| Agent Arena | ❌ | ✅ `ArenaManager.ts` | **Qwen 独有** |
| 视觉/图像 | ✅ 图片粘贴/读取 | ✅ YOLO 自动切换视觉模型 | 对等（Qwen 自动切换更强） |
| 6 语言 UI | ❌ | ✅ 中/英/日/德/俄/葡 | **Qwen 独有** |
| 免费 OAuth | ❌ | ✅ 1000 次/天 | **Qwen 独有** |
| **`--bare` 模式** | ✅ | ❌ | **需补全** |
| **延迟工具加载** | ✅ ToolSearch | ❌ | **需补全** |
| **断路器增强** | ✅ 连续 N 次计数 | 部分（布尔标志） | **需增强** |
| **Voice 模式** | ✅ | ❌ | **需补全** |
| **交互式 Bash** | ✅ `!` 命令 | ❌ | **需补全** |
| **Remote Control** | ✅ `/remote-control` | ❌ | **需补全** |
| **Teammates 协作** | ✅ | ❌ | **需补全** |
| **Channels** | ✅ MCP 消息推送 | ❌ | **需补全** |
| **插件市场** | ✅ 13 官方插件 | ❌ 仅扩展系统 | **需补全** |
| **结构化输出** | ✅ | ❌ | **需补全** |
| **细粒度工具流** | ✅ | 部分（`updateOutput` 回调已有） | **需增强** |
| **企业管控** | ✅ managed-settings | ❌ | **需补全** |
| **Notebook 编辑** | ✅ NotebookEdit | 部分（仅读取） | **需增强** |
| LSP 集成 | ✅ | ✅ `lsp.ts`（完整 LSP 工具：定义、引用、诊断等） | 对等 |

---

## 一、高优先级（用户体验核心差距）

### 1. `--bare` 模式（脚本/CI 场景）

**Claude Code 实现**：
- `--bare` 标志跳过 hooks、LSP、插件同步、技能目录扫描
- 要求显式 API key
- 自动禁用 auto-memory
- 专为 `-p` 脚本调用优化

**Qwen Code 缺失影响**：非交互模式仍加载完整启动链（包括 React/Ink），CI/CD 集成启动慢。

**建议实现**：
```typescript
// packages/cli/src/gemini.tsx
if (argv.bare) {
  // 跳过：hooks, 技能扫描, 插件加载, i18n 完整初始化
  // 直接：认证 → 加载模型 → 执行 prompt → 输出结果
  const config = await loadMinimalConfig(argv);
  await runNonInteractive(config, settings, input, prompt_id);
  process.exit(0);
}
```

**工作量**：低（1-2 天），复用现有 `nonInteractiveCli.ts`

---

### 2. 断路器增强（布尔 → 计数器）

**Claude Code 实现**：
- 自动压缩连续 3 次失败后停止重试
- 计数器模式，重置条件可控

**Qwen Code 现状**：已有简单断路器——`hasFailedCompressionAttempt` 布尔标志（`client.ts:113,877`），压缩失败后设为 `true`，后续非强制压缩跳过（`chatCompressionService.ts:97`）。但布尔标志意味着**一次失败就永远放弃**，无法区分暂时性和持续性错误。

**建议增强**：
```typescript
// 当前（client.ts:113）：
private hasFailedCompressionAttempt = false;  // 一次失败永远放弃

// 改进：计数器 + 超时重置
private compressionFailures = 0;
private lastFailureTime = 0;
private readonly MAX_FAILURES = 3;
private readonly RESET_AFTER_MS = 5 * 60 * 1000;  // 5 分钟后重试

// 判断逻辑：
if (this.compressionFailures >= this.MAX_FAILURES &&
    Date.now() - this.lastFailureTime < this.RESET_AFTER_MS) {
  return NOOP;  // 断路器打开
}
```

**工作量**：极低（半天），改 1 个布尔为计数器 + 时间戳

---

### 3. 延迟工具加载（ToolSearch）

**Claude Code 实现**：
- 工具 schema 在模型首次请求时才加载
- 减少初始 prompt token 消耗
- 缩短首次响应时间

**Qwen Code 缺失影响**：所有工具定义在启动时全部注入系统 prompt，增加每次请求的 token 开销。

**建议实现**：
```typescript
// 当前：所有工具一次性注入
const tools = toolRegistry.getAllFunctionDeclarations();

// 改进：分层加载
const coreTools = toolRegistry.getCoreTools();        // read, edit, bash, grep
const deferredTools = toolRegistry.getDeferredTools(); // web, lsp, mcp...
// 首次请求仅包含 coreTools
// 模型请求 ToolSearch 时才加载 deferredTools
```

**工作量**：中（3-5 天），需要改工具注册和 prompt 构建逻辑

---

### 4. 交互式 Bash（`!` 命令）

**Claude Code 实现**：
- 在会话中输入 `! command` 直接执行 shell 命令
- 输出留在上下文中供 AI 参考
- 快速调试不需要 AI 介入的操作

**Qwen Code 缺失影响**：用户需要切换终端窗口执行命令，或让 AI 代执行简单命令（浪费轮次）。

**建议实现**：
```typescript
// packages/cli/src/ui/InputPrompt.tsx
if (input.startsWith('!')) {
  const command = input.slice(1).trim();
  const result = await execAsync(command, { cwd: config.targetDir });
  // 显示输出，并将结果加入上下文
  appendToContext({ role: 'user', content: `Shell: ${command}\n${result}` });
  return; // 不发送给 LLM
}
```

**工作量**：低（1-2 天）

---

## 二、中优先级（差异化竞争力）

### 5. 插件市场

**Claude Code 实现**：
- 13 个官方插件（code-review、feature-dev、security-guidance 等）
- `.claude-plugin/marketplace.json` 插件清单
- 插件包含：commands + agents + skills + hooks + MCP

**Qwen Code 现状**：有扩展系统（skills + agents + hooks），但无集中市场。

**建议路线**：
1. 定义 `.qwen-plugin/plugin.json` 标准格式
2. 建立官方插件仓库（GitHub org）
3. 移植 Claude Code 的 code-review、feature-dev 等高价值插件
4. 利用已有的 Claude/Gemini 扩展转换能力，自动导入社区插件

**工作量**：高（2-4 周），但生态价值巨大

---

### 6. 企业管控（Managed Settings）

**Claude Code 实现**：
- 7 层设置优先级（企业→组织→用户→项目→本地→CLI→默认）
- `managed-settings.json` 远程下发
- `allowManagedHooksOnly` / `allowManagedPermissionRulesOnly`
- `strictKnownMarketplaces` 限制插件来源
- `disableBypassPermissionsMode` 禁止绕过权限

**Qwen Code 现状**：2 层设置（全局 + 项目），无企业管控。

**建议路线**：
1. 增加组织/企业层设置加载
2. 实现远程设置下发（API 端点）
3. 添加 `managed` 标记的 hooks 和 permissions

**工作量**：高（2-3 周），面向企业客户关键

---

### 7. 结构化输出

**Claude Code 实现**：
- 工具输出可按 JSON Schema 验证
- 支持 beta header 管理
- proxy gateway 兼容

**Qwen Code 缺失影响**：程序化集成（SDK、CI）时输出格式不可预期。

**建议实现**：在非交互模式中添加 `--schema` 参数：
```bash
qwen -p "分析这个函数的复杂度" --schema '{"type":"object","properties":{"complexity":{"type":"number"}}}'
```

**工作量**：中（3-5 天）

---

### 8. Remote Control（远程控制）

**Claude Code 实现**：
- `/remote-control` 桥接终端会话到浏览器/手机
- 通过 claude.ai/code 远程查看和操作

**Qwen Code 缺失影响**：无法在移动设备上监控/操作长时间运行的任务。

**建议实现**：利用现有 WebSocket/Wire 协议基础设施，增加远程客户端。

**工作量**：高（2-3 周）

---

## 三、低优先级（锦上添花）

### 9. Voice 模式

**Claude Code 实现**：
- Push-to-talk（Ctrl+K）
- 音频流式传输（WebSocket）
- 多语言支持
- 音频恢复（断线重连）

**Qwen Code 缺失影响**：无法语音交互（小众需求）。

**工作量**：高（3-4 周），需要音频处理和 WebSocket 集成

---

### 10. Teammates 协作

**Claude Code 实现**：
- 分屏协作（iTerm2、tmux）
- Leader-Follower 模型
- 实时同步

**Qwen Code 现状**：有 Arena 模式（多代理竞争），但无人-AI 实时协作。

**工作量**：高（3-4 周）

---

### 11. Channels（MCP 消息推送）

**Claude Code 实现**：
- `--channels` 允许 MCP 服务器主动推送消息到会话
- 用于外部事件通知（CI/CD 状态、监控告警等）

**工作量**：中（1-2 周）

---

### 12. Notebook 完整编辑

**Claude Code 实现**：NotebookEdit 工具支持完整的 Jupyter cell 操作。

**Qwen Code 现状**：`notebook-handler.ts` 仅支持读取/上下文，不支持编辑。

**工作量**：中（1-2 周）

---

### 13. 细粒度工具流式输出

**Claude Code 实现**：
- 工具执行过程中实时流式返回部分结果
- 支持 Bedrock/Vertex API proxy

**Qwen Code 现状**：有 `updateOutput` 回调，但非所有工具支持。

**工作量**：中（1-2 周），需逐工具适配

---

## 四、优先级矩阵

| 功能 | 工作量 | 用户价值 | 优先级 |
|------|--------|---------|--------|
| `--bare` 模式 | 低（1-2 天） | **高**（CI/脚本） | **P0** |
| 断路器增强（布尔→计数器） | 极低（半天） | **高**（稳定性） | **P0** |
| 交互式 Bash `!` | 低（1-2 天） | **高**（效率） | **P0** |
| 延迟工具加载 | 中（3-5 天） | **高**（性能 + token） | **P1** |
| 结构化输出 | 中（3-5 天） | **高**（SDK 集成） | **P1** |
| 插件市场 | 高（2-4 周） | **高**（生态） | **P1** |
| 企业管控 | 高（2-3 周） | **高**（企业客户） | **P1** |
| Remote Control | 高（2-3 周） | 中 | P2 |
| Notebook 编辑 | 中（1-2 周） | 中 | P2 |
| Channels | 中（1-2 周） | 中 | P2 |
| 细粒度工具流 | 中（1-2 周） | 中 | P2 |
| Voice 模式 | 高（3-4 周） | 低 | P3 |
| Teammates 协作 | 高（3-4 周） | 低 | P3 |

---

## 五、Qwen Code 的竞争优势（无需补全）

以下功能是 Qwen Code 的差异化优势，Claude Code 尚未实现：

| 功能 | Qwen Code 实现 | 竞争价值 |
|------|---------------|---------|
| **Agent Arena** | `ArenaManager.ts`，多模型并行 worktree 对比 | 独一无二的多模型评估能力 |
| **视觉模型 YOLO 自动切换** | 根据输入自动切换视觉模型（Claude Code 支持图片但无自动切换） | 多模态体验更流畅 |
| **6 语言 UI** | 中/英/日/德/俄/葡完整本地化 | 全球化覆盖 |
| **免费 OAuth** | 每天 1000 次 | 零门槛试用 |
| **多提供商** | Qwen + OpenAI + Anthropic + Gemini + Vertex | 模型灵活性 |
| **Claude/Gemini 扩展转换** | 自动格式转换 | 跨生态兼容 |
| **操作检查点** | `/restore` 命令回滚 | 安全网 |

---

## 六、一句话总结

**3 个半天可完成的 P0**：`--bare` 模式 + 断路器增强（布尔→计数器） + 交互式 Bash `!`

**4 个需要投入的 P1**：延迟工具加载 + 结构化输出 + 插件市场 + 企业管控

**Qwen Code 不需要复制 Claude Code 的一切**——Agent Arena、视觉模型、6 语言、免费 OAuth 是独有竞争力。重点补全影响用户体验和企业采用的核心缺口。

---

*分析基于 Claude Code 插件仓库（v2.1.81）和 Qwen Code 本地源码，截至 2026 年 3 月。*
