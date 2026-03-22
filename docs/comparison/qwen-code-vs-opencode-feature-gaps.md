# Qwen Code 功能补全建议：对标 OpenCode

> 基于源码逐项比对，识别 Qwen Code 应该借鉴的 OpenCode 功能

## 功能全景对比

| 功能 | OpenCode | Qwen Code | 状态 |
|------|---------|-----------|------|
| **核心代理循环** | ✅ | ✅ | 对等 |
| 多代理（build/plan/general/explore） | ✅ | ✅ 子代理 + Arena | 对等 |
| MCP 集成（4 种传输） | ✅ HTTP/SSE/Stdio/WS | ✅ SSE/Stdio | Qwen 传输方式较少 |
| 会话管理 | ✅ SQLite | ✅ JSONL | 架构不同 |
| 工具系统 | ✅ 19 个内置工具 | ✅ 16 个内置工具 | 接近对等 |
| 权限系统 | ✅ 分层规则 | ✅ deny>ask>allow | 对等 |
| 上下文压缩 | ✅ | ✅ | 对等 |
| Git Worktree | ✅ | ✅ | 对等 |
| Hook 系统 | ✅ 插件 Hook | ✅ 12 事件类型 | 对等 |
| 非交互模式 | ✅ `run` 命令 | ✅ `--prompt` | 对等 |
| 输出截断 | ✅ 32K + 文件存储 | ✅ 截断实现 | 对等 |
| i18n 多语言 | ❌ 仅英文 | ✅ 6 语言 | **Qwen 独有** |
| Agent Arena | ❌ | ✅ | **Qwen 独有** |
| 免费 OAuth | ❌ | ✅ 1000 次/天 | **Qwen 独有** |
| 扩展格式转换 | ❌ | ✅ Claude/Gemini 格式 | **Qwen 独有** |
| **SQLite 持久化** | ✅ Drizzle ORM | ❌ JSONL 文件 | **需补全** |
| **HTTP 服务器** | ✅ Hono:4096 | ❌ | **需补全** |
| Doom Loop / 循环检测 | ✅ 权限拒绝 3 次阈值 | ✅ `LoopDetectionService`（工具 5 次 + 内容 10 次） | 对等（Qwen 更全面） |
| **文件时间锁** | ✅ 外部修改检测 | ❌ | **需补全** |
| **MDNS 服务发现** | ✅ 远程连接 | ❌ | **需补全** |
| **apply_patch 工具** | ✅ GPT 专用 | ❌ | **需补全** |
| **Session 版本/分叉** | ✅ | ❌ 线性会话 | **需补全** |
| **批量操作工具** | ✅ 实验性 | ❌ | **需补全** |
| **统一 AI SDK** | ✅ Vercel AI v5 | ❌ 各提供商独立 | **架构差异** |
| **插件系统** | ✅ Hook 式插件（npm 包 + file://） | ✅ 扩展系统（Git clone + GitHub release） | 架构不同 |
| **Instance 上下文** | ✅ 每目录状态隔离 | ❌ | **需补全** |
| **Exa 代码搜索** | ✅ 语义搜索 | ❌ 仅 Web 搜索 | **需补全** |
| Tauri 桌面应用 | ✅ | ❌ | 架构差异 |
| OpenTUI + Solid.js | ✅ | ❌（Ink + React） | 架构差异 |

---

## 一、高优先级（核心体验差距）

### ~~1. Doom Loop 保护~~ ✅ 已验证存在

Qwen Code 有完整的 `LoopDetectionService`（`services/loopDetectionService.ts`），**比 OpenCode 更全面**：
- **工具调用循环**：`TOOL_CALL_LOOP_THRESHOLD = 5`（连续 5 次相同工具调用）
- **内容重复循环**：`CONTENT_LOOP_THRESHOLD = 10`（内容句子重复 10 次）
- 支持会话级禁用（`disabledForSession`）
- 遥测集成（`LoopDetectedEvent`）

OpenCode 的 Doom Loop（`DOOM_LOOP_THRESHOLD = 3`）仅检测权限拒绝，Qwen Code 的检测范围更广。

---

### 2. 文件时间锁（外部修改检测）

**OpenCode 实现**：
- `file/time.ts`：`FileTime.withLock()` 和读取时间追踪
- 代理编辑文件时，检测文件是否被外部修改
- 防止覆盖用户在编辑器中的并行修改

**Qwen Code 缺失影响**：代理可能覆盖用户刚在 IDE 中做的修改。

**建议实现**：
```typescript
// packages/core/src/tools/edit.ts
class FileTimeTracker {
  private lastModifiedTimes = new Map<string, number>();

  async checkBeforeEdit(filePath: string): Promise<boolean> {
    const stat = await fs.stat(filePath);
    const lastKnown = this.lastModifiedTimes.get(filePath);
    if (lastKnown && stat.mtimeMs > lastKnown) {
      // 文件被外部修改
      return false;  // 需要用户确认
    }
    return true;
  }

  recordEdit(filePath: string) {
    this.lastModifiedTimes.set(filePath, Date.now());
  }
}
```

**工作量**：低（1 天）

---

### 3. apply_patch 工具（GPT 模型适配）

**OpenCode 实现**：
- `tool/apply_patch.ts`：GPT 模型专用的 diff 格式工具
- GPT 系列模型输出 unified diff 比 search/replace 更可靠
- 按模型自动选择编辑工具（GPT 用 apply_patch，Claude 用 edit）

**Qwen Code 缺失影响**：使用 GPT/OpenAI 兼容模型时，编辑准确性可能不如 OpenCode。

**建议实现**：
```typescript
// 在工具注册时按模型选择：
if (model.startsWith('gpt-') || model.startsWith('o1-')) {
  registry.register(new ApplyPatchTool());  // unified diff
} else {
  registry.register(new EditTool());        // search/replace
}
```

**工作量**：中（2-3 天），需实现 patch 解析和应用逻辑

---

### 4. Session 版本/分叉

**OpenCode 实现**：
- Session 表有 `version` 字段
- 支持 session forking（从某个点分叉新会话）
- 支持 revert（回到之前的版本）
- 分享 URL 支持

**Qwen Code 缺失影响**：无法从对话中某个点分叉尝试不同方案。

**建议实现**：
```typescript
// 在 JSONL 会话文件中增加版本标记：
interface SessionVersion {
  versionId: string;
  parentVersionId?: string;  // 分叉来源
  messageIndex: number;      // 分叉点
  timestamp: number;
}
```

**工作量**：中（3-5 天）

---

## 二、中优先级（架构提升）

### 5. SQLite 持久化（替代 JSONL）

**OpenCode 实现**：
- Drizzle ORM + SQLite（WAL 模式）
- Session/Message/Part 三张关系表
- 支持 SQL 查询、索引、迁移
- 并发安全（WAL 模式）

**Qwen Code 现状**：JSONL 追加写入，分页靠文件读取，无索引。

**建议路线**：
1. 引入 `better-sqlite3` + Drizzle ORM
2. 迁移 session 存储到 SQLite
3. 保留 JSONL 导出兼容
4. WAL 模式支持并发读写

**收益**：大会话加载速度 10x+，支持复杂查询（搜索历史会话）

**工作量**：高（1-2 周）

---

### 6. HTTP 服务器（多客户端支持）

**OpenCode 实现**：
- Hono HTTP 框架 + WebSocket，端口 4096
- TUI、Web 控制台、桌面应用共享同一后端
- RESTful API + WebSocket 实时同步
- MDNS 服务发现（局域网设备自动发现）

**Qwen Code 现状**：单进程 CLI，无 HTTP 服务器。`packages/webui/` 仅是 UI 组件库。

**建议路线**：
1. 可选 `--serve` 模式启动 HTTP 服务器
2. 现有 CLI 作为默认客户端
3. Web UI 作为可选远程客户端
4. WebSocket 推送实时更新

**工作量**：高（2-3 周）

---

### 7. 插件系统差异（架构不同，非缺失）

**OpenCode 实现**：
- `packages/plugin/`：Hook 式插件，支持 npm 包和 `file://` 加载
- 内置插件：CodexAuthPlugin、CopilotAuthPlugin、GitlabAuthPlugin
- Hook 类型：auth、event、tool、chat.system.transform 等

**Qwen Code 实现**：
- `marketplace.ts`（280 行）+ `extensionManager.ts`：扩展系统
- 安装方式：Git clone、GitHub release、本地目录、符号链接
- 支持 Claude/Gemini 扩展格式自动转换

**评估**：两者架构不同但功能覆盖相当。OpenCode 的 npm 加载更适合 Node.js 生态插件分发；Qwen Code 的 Git 方式更灵活（不限语言）。**非核心缺口**。

---

### 8. 代码搜索工具（Exa 集成）

**OpenCode 实现**：
- `codesearch.ts`：通过 Exa API 进行语义级代码搜索
- 不同于 grep 的文本匹配——理解代码语义

**Qwen Code 现状**：有 `web-search`（Tavily），但无语义代码搜索。

**建议实现**：增加 Exa 或类似的语义代码搜索工具。

**工作量**：低（1-2 天），主要是 API 集成

---

### 9. Instance 上下文模式（每目录状态隔离）

**OpenCode 实现**：
- `project/instance.ts`：`Instance.provide()` 包装执行上下文
- 每个目录有独立的懒加载状态
- 自动清理和 disposal 回调
- 防止不同项目间状态泄露

**Qwen Code 缺失影响**：多项目场景下状态可能混淆。

**工作量**：中（3-5 天）

---

## 三、低优先级（锦上添花）

### 10. 批量操作工具

**OpenCode 实现**：`tool/batch.ts`（实验性），支持批量文件操作。

**工作量**：低（1-2 天）

---

### 11. MDNS 服务发现

**OpenCode 实现**：`server/mdns.ts` 使用 `bonjour-service`，局域网设备自动发现。

**前提**：需要先实现 HTTP 服务器（第 6 项）。

**工作量**：低（1 天），但依赖 HTTP 服务器

---

### 12. 统一 AI SDK（Vercel AI v5）

**OpenCode 实现**：通过 `ai` 包的 `streamText()` API 统一所有 LLM 提供商。

**Qwen Code 现状**：每个提供商独立实现 ContentGenerator（Anthropic、OpenAI、Gemini、Qwen OAuth），代码量大但灵活。

**评估**：统一 SDK 减少代码量，但牺牲灵活性。Qwen Code 的独立实现允许深度定制（如 DashScope 缓存、Qwen OAuth），迁移到统一 SDK 需谨慎评估。

**工作量**：高（3-4 周），且有风险（可能丧失定制能力）

---

## 四、优先级矩阵

| 功能 | 工作量 | 用户价值 | 优先级 |
|------|--------|---------|--------|
| ~~Doom Loop 保护~~ | — | — | ✅ 已有（`LoopDetectionService`，比 OpenCode 更全面） |
| 文件时间锁 | 低（1 天） | **高**（防覆盖用户修改） | **P0** |
| apply_patch 工具 | 中（2-3 天） | **高**（GPT 模型适配） | **P1** |
| Session 版本/分叉 | 中（3-5 天） | **高**（探索多方案） | **P1** |
| 代码搜索（Exa） | 低（1-2 天） | 中 | **P1** |
| SQLite 持久化 | 高（1-2 周） | **高**（大会话性能） | **P1** |
| HTTP 服务器 | 高（2-3 周） | 中（多客户端基础） | P2 |
| ~~npm 插件系统~~ | — | — | ✅ 两者架构不同（npm vs Git），非缺口 |
| Instance 上下文 | 中（3-5 天） | 中 | P2 |
| 批量操作工具 | 低（1-2 天） | 低 | P3 |
| MDNS 服务发现 | 低（1 天） | 低（依赖 HTTP 服务器） | P3 |
| 统一 AI SDK | 高（3-4 周） | 低（有风险） | P3 |

---

## 五、Qwen Code 的竞争优势（无需对标）

| 功能 | Qwen Code 实现 | OpenCode 缺失 |
|------|---------------|--------------|
| **Agent Arena** | 多模型并行竞争评估 | ❌ |
| **6 语言 UI** | 中/英/日/德/俄/葡 | ❌ 仅英文 |
| **免费 OAuth** | 每天 1000 次 | ❌ |
| **扩展格式转换** | Claude/Gemini 扩展自动转换 | ❌ |

> 注：多提供商支持（Qwen 5 个 vs OpenCode 20+ via Vercel AI）、Plan 模式审批（两者都有权限系统）、交互式 Shell（两者都支持 bash 执行）经 R2 核实非 Qwen 独有优势，已移除。

---

## 六、一句话总结

**1 个半天可完成的 P0**：文件时间锁（防覆盖用户并行修改）

**4 个需要投入的 P1**：apply_patch 工具 + Session 版本分叉 + 代码搜索 + SQLite 持久化

> 注：~~Doom Loop 保护~~ 经 R1 核实，Qwen Code 已有 `LoopDetectionService`（工具 5 次 + 内容 10 次阈值），比 OpenCode 的权限拒绝检测更全面。

**Qwen Code 不需要复制 OpenCode 的一切**——统一 AI SDK 的迁移风险高、HTTP 服务器对 CLI 工具非必需。重点补全文件时间锁这个**安全防护缺口**，以及 apply_patch 提升**多模型适配**能力。

---

*分析基于 OpenCode 和 Qwen Code 本地源码，截至 2026 年 3 月。*
