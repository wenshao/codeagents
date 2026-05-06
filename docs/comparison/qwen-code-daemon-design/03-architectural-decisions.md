# 03 — 6 个架构决策

> [← 上一篇：现有资产盘点](./02-existing-assets.md) · [下一篇：HTTP API 设计 →](./04-http-api.md)

> [SDK / ACP / Daemon 架构 Deep-Dive §七.3](../sdk-acp-daemon-architecture-deep-dive.md#73-真正的难点架构决策) 列出 6 个"真正的难点是几个架构决策——而不是代码量"。本文为每个决策点给出明确选择 + 理由。

## 1. session 是否跨 client 共享

**问题**：用户在手机微信上发了一条消息让 agent 跑研究，回到电脑想继续——同一个 session 还是新 session？

### 选择

**支持双模式，默认每 client 独立 session（scope=`thread`），可通过 settings 切到跨 client 共享（scope=`user`）**。

| settings | 行为 | 适用场景 |
|---|---|---|
| `daemon.sessionScope: 'thread'`（默认）| 每 HTTP client 独立 session | 多用户共用 daemon、避免互相污染 |
| `daemon.sessionScope: 'single'` | 同 workspace 全局一 session | 单人桌面 + IDE 同时观察 |
| `daemon.sessionScope: 'user'` | 同 user-id 跨 channel 共享 | 手机/电脑续行 |

### 理由

1. **复用 Channels 已有的 3 种 scope** —— `SessionRouter.routingKey()` 已经实现这套语义
2. **默认保守**（`thread`）防止意外的跨 client 数据泄漏
3. **`user` scope 配合 PR#3739 的 transcript-first fork resume** —— 一个 session 的 transcript 能被另一个 client（不同 IP 的 SDK / 移动端）通过 `LoadSessionRequest` 拉到本地 replay

### 实现要点

```ts
// daemon settings
{
  "daemon": {
    "sessionScope": "thread" | "single" | "user",
    "perChannelScope": {                          // 不同 channel 用不同 scope
      "http": "thread",                            //   SDK 客户端默认隔离
      "vscode": "single",                          //   VSCode workspace 共享
      "telegram": "user"                           //   IM 用户视角共享
    }
  }
}
```

把这套配置直接喂给 `SessionRouter.setChannelScope()`。

---

## 2. 状态进程模型

**问题**：所有 session 都跑在 daemon 主进程？还是 daemon 路由到子进程，每 session 一个？

### 选择

**单 daemon 进程承载所有 session**（OpenCode 同模式）。

### 理由

| 选项 | 优点 | 缺点 |
|---|---|---|
| **A：单 daemon 进程 全部 session（本设计）** | 启动开销摊销、跨 session 状态共享简单（直接 Map）、core 加载 1 次 | OOM/崩溃影响所有 session、CPU/内存隔离弱 |
| B：daemon 路由到子进程，每 session 一个 | 进程级隔离、单 session 崩溃不影响他人 | 每 session 都付启动开销、跨 session 共享 MCP/LSP 复杂、节点 fork 方案在 Node 中并不便宜 |

OpenCode 选 A 已经验证可行（用 Effect-TS 的 `LocalContext.create()` 做应用层隔离 + SQLite 兜底）。Qwen 跟进同模式。

### 实现要点

- Node `AsyncLocalStorage`（Qwen 已有 `LocalContext` 等价物，在 PR#3707 OPEN 引入 per-agent ContentGenerator 时也用过）
- session 状态写入 SQLite + JSONL（Qwen 现有 SessionService）
- 关键状态序列化（PR#3739 transcript-first 已经具备）

进程模型详解见 [05-进程模型](./05-process-model.md)。

---

## 3. MCP server 生命周期

**问题**：MCP server 是每 session 启动一个？还是 daemon 内 pool 跨 session 复用？

### 选择

**daemon 内 pool 跨 session 复用，按 MCP 配置 fingerprint 去重**。

### 理由

每 session 启 MCP server 重复成本高（典型 MCP server 启动 0.5-2s + 占用一个进程）。OpenCode 已经走"daemon 内共享 MCP" 路线。Qwen 跟进。

### 状态泄漏风险与缓解

**风险**：MCP server 内部可能持有 session-specific 状态（如对话上下文）。

**缓解**：
1. MCP server 初始化时不绑定 session，session 通过 MCP request 的 metadata 传递
2. 如果某个 MCP server 不支持 session-less 模式，**fallback 到 per-session spawn**（settings 提供 `mcpSharedPool: false` 开关）
3. PR#3818（已合并）的 MCP rediscovery coalesce 机制确保多 session 并发请求同一个 MCP server 时不会起重复进程（PR#3819 follow-up 已 closed，主要功能已被 PR#3818 覆盖）

### 实现要点

```ts
// 现有 mcp-client-manager.ts 已有 PR#3818 的 in-flight restart coalesce
// daemon 化只需新增 fingerprint key:
const fingerprint = hash(JSON.stringify({ command, args, env }))
mcpClientPool.get(fingerprint)  // ← 跨 session 共享
```

详见 [06-MCP/资源共享](./06-mcp-resources.md)。

---

## 4. FileReadCache 共享语义

**问题**：FileReadCache（PR#3717）的"模型已看过整文件"标记是 session 级私有、还是跨 session 共享？

### 选择

**保守起步：session 内私有，跨 session 不共享**。Stage 3 评估是否升级为 daemon 全局共享（带 mtime 二次校验）。

### 理由

| 选项 | 优点 | 缺点 |
|---|---|---|
| **A：session 内私有（本设计）** | 与 PR#3717 当前行为一致、无新风险、不影响 PR#3774 prior-read enforcement 语义 | 跨 session 有重复 read |
| B：daemon 全局共享（用 `(dev,ino)` key + mtime） | 两个 session 看同 workspace 时 read 命中 | session A 改 mtime 但 session B 还没看到 → 状态错位、PR#3810 invalidation 5 路径需扩展到全局 |

PR#3810 的 audit 已经表明 cache invalidation 是个 fragile point（PR#3717 漏了 5 条路径）。daemon 化先不要扩大 invalidation 半径，保守起步。

### 实现要点

```ts
// FileReadCache 当前是 session-scoped（PR#3717 设计）
class FileReadCache {
  private byKey: Map<string, ...>  // 已经是 per-instance（每 SessionService）
}
// daemon 化下，每 session 各自持一个 FileReadCache instance — 不共享
```

详见 [06-MCP/资源共享 §2](./06-mcp-resources.md#2-filereadcache-共享策略)。

---

## 5. Permission flow

**问题**：daemon 模式下，工具调用是否需要审批？审批 UI 怎么做（HTTP 不像 stdio 能等用户回车）？

### 选择

**复用 PR#3723 共享 L3→L4 permission flow，加 daemon 第 4 种 execution mode + permission_request 走 SSE/WS 推给 client**。

### 理由

PR#3723（已合并 2026-04-30 +461/-95）把 Interactive / Non-Interactive / ACP 三模式的 L3→L4 决策合一为 `evaluatePermissionFlow()`。daemon 加为第 4 种 mode 是最自然的扩展。

### 实现要点

```ts
// 现有 PR#3723
type ExecutionMode = 'interactive' | 'non-interactive' | 'acp'

// 新增
type ExecutionMode = 'interactive' | 'non-interactive' | 'acp' | 'daemon-http'

// daemon-http mode 下的 ask 决策处理：
async function executeTool(tool: Tool, ctx: Context) {
  const result = evaluatePermissionFlow(tool, ctx)
  if (result.decision === 'ask') {
    // HTTP 不能阻塞等输入，改 SSE 推给 client
    sendSseEvent(ctx.sessionId, {
      type: 'permission_request',
      requestId: uuid(),
      tool: tool.name,
      args: tool.args,
    })
    // HTTP request 挂起等 POST /permission/:requestId 响应
    const response = await waitForPermissionResponse(requestId, { timeout: 60_000 })
    if (response.allow) { ... }
  }
}
```

详见 [07-权限/认证](./07-permission-auth.md)。

---

## 6. 多 client 并发请求

**问题**：两个 client 同时连同一个 session 发 prompt，行为如何？

### 选择

**同 session 串行处理（FIFO 队列），跨 session 并行**。

### 理由

| 选项 | 适用 |
|---|---|
| **A：同 session 串行（本设计）** | 与 ACP 协议天然契合（一次只能有一个 active prompt），状态简单 |
| B：同 session 并行 | 复杂——需要把 LLM 调用 / 工具调用并行化，FileReadCache / context state 都要重新设计同步 |

ACP 协议本身就是"client → agent → 同步 response"语义，不允许同 session 并发 prompt。daemon 跟随这个约束。

### 实现要点

```ts
// daemon 内每 session 一个 mutex（或 await 队列）
class Session {
  private taskQueue: Promise<void> = Promise.resolve()
  
  async handlePrompt(req: PromptRequest) {
    // 同 session FIFO
    const result = await this.taskQueue.then(() => this.doPrompt(req))
    return result
  }
}

// 跨 session 并行：daemon 进程内不同 Session instance 的 prompt 互不阻塞
```

**对 client 的体验**：第二个 client 在同 session 发 prompt，HTTP request 挂起等前一个完成（最多 60s 超时）。如果不希望等待，client 可以选择：
1. 用不同 session ID（推荐）
2. 用 `LoadSessionRequest` fork 一个 session 后再 prompt（PR#3739 transcript-first fork resume 支持）
3. 改用 `cancel` 当前 prompt 然后发新 prompt

---

## 决策矩阵汇总

| # | 决策 | 选择 | 关键依据 PR / 工具 |
|---|---|---|---|
| 1 | session 跨 client 共享 | 默认 thread，可配 single/user | Channels SessionRouter scope 系统 |
| 2 | 状态进程模型 | 单 daemon 进程承载全部 session | 与 OpenCode 一致 + Qwen LocalContext / `AsyncLocalStorage` |
| 3 | MCP server 生命周期 | daemon 内 pool 跨 session 复用 + per-server fallback | PR#3818 coalesce |
| 4 | FileReadCache 共享 | session 内私有（保守起步）| PR#3717 + PR#3810 invalidation fragility |
| 5 | Permission flow | 复用 PR#3723 + daemon 第 4 mode + SSE permission_request | PR#3723 evaluatePermissionFlow() |
| 6 | 多 client 并发 | 同 session 串行 + 跨 session 并行 | ACP 协议语义 + Session task queue |

---

下一篇：[04-HTTP API 设计 →](./04-http-api.md)
