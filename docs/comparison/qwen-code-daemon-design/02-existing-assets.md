# 02 — 现有资产盘点

> [← 上一篇：架构总览](./01-overview.md) · [下一篇：6 个架构决策 →](./03-architectural-decisions.md)

> 把 Qwen Code 现有代码逐一对照"daemon 化需要什么"——结论：**~70% 已具备**，只需补传输层。

## 一、资产清单总览

| 资产 | 位置 | 行数 | daemon 复用度 |
|---|---|:---:|:---:|
| ACP agent（NDJSON 协议实现）| `packages/cli/src/acp-integration/acpAgent.ts` | 838 | **~95%** |
| ACP session 状态机 | `packages/cli/src/acp-integration/session/` | ~4400（17 文件）| **~95%** |
| Channels SessionRouter | `packages/channels/base/src/SessionRouter.ts` | 234 | **~80%** |
| Channels AcpBridge | `packages/channels/base/src/AcpBridge.ts` | 250 | **~70%** |
| SessionService（核心 session 持久化）| `packages/core/src/services/...` | — | **~100%**（无需改动）|
| FileReadCache（PR#3717 + PR#3810）| `packages/core/src/services/fileReadCache.ts` | 188 | **~100%**（已是 session-scoped）|
| Shared permission flow（PR#3723）| `packages/core/src/core/permissionFlow.ts` | 161 | **~95%**（加 daemon mode 即可）|
| SDK Transport 抽象 | `packages/sdk-typescript/src/transport/Transport.ts` | 22 | **~100%** —— 注释已预告 HttpTransport |
| ProcessTransport（参考实现）| `packages/sdk-typescript/src/transport/ProcessTransport.ts` | 536 | 镜像写 HttpTransport |
| WebUI 包 + ACPAdapter | `packages/webui/src/adapters/ACPAdapter.ts` | 109 | 改传输层即可接入 daemon |
| VSCode IDE companion + express | `packages/vscode-ide-companion/src/ide-server.ts` | 477 | 参考模板 + 可弃用（直接连 daemon）|
| Background task management（PR#3471/3488/3642/3791/3836）| 多文件 | ~3000 | **~100%**（kind framework 4 消费者已稳定）|
| `/tasks` 命令 | `packages/cli/src/ui/commands/tasksCommand.ts` | 271 | **~95%**（headless / non-TTY 路径）|

## 二、关键资产详解

### 2.1 ACP agent（最核心的可复用资产）

**位置**：`packages/cli/src/acp-integration/acpAgent.ts`（838 行 · 已被 [SubAgent Display Deep-Dive](../subagent-display-deep-dive.md) 等多篇文档分析）

**已实现的 ACP 协议能力**（覆盖 daemon 所需的 95%+）：

```ts
// acpAgent.ts 头部 import 节选
import {
  AgentSideConnection,    // ACP 服务端
  ndJsonStream,           // NDJSON 流封装
  PROTOCOL_VERSION,
} from '@agentclientprotocol/sdk';
import type {
  Agent,
  AuthenticateRequest,
  AuthMethod,
  CancelNotification,
  ClientCapabilities,
  InitializeRequest, InitializeResponse,
  ListSessionsRequest, ListSessionsResponse,
  LoadSessionRequest, LoadSessionResponse,
  McpServer, McpServerHttp, McpServerSse, McpServerStdio,
  NewSessionRequest, NewSessionResponse,
  PromptRequest, PromptResponse,
  SessionConfigOption, SessionInfo, SessionModeState,
  SetSessionConfigOptionRequest, SetSessionConfigOptionResponse,
  SetSessionModelRequest, SetSessionModelResponse,
  SetSessionModeRequest, SetSessionModeResponse,
} from '@agentclientprotocol/sdk';
```

**这意味着 ACP 已经定义好的 session 生命周期 RPC**（`InitializeRequest` / `NewSessionRequest` / `PromptRequest` / `LoadSessionRequest` / `ListSessionsRequest` / `CancelNotification` / `SetSessionModelRequest` 等）**全都可以直接映射成 daemon HTTP 路由**——不用从头设计 schema。

**daemon 改造方式**：

```
┌──────────────────────────────────────────────────────────────┐
│ acpAgent.ts (838 行)                                          │
│                                                                │
│  当前: stdin/stdout NDJSON ─→ AgentSideConnection ─→ Agent impl │
│        ─→ Session.handleXxx() ─→ core                          │
│                                                                │
│  daemon: HTTP body ─→ HttpAcpAdapter ─→ 同样的 Agent impl       │
│          ─→ Session.handleXxx() ─→ core                        │
│          ─→ SessionNotification ─→ SSE/WS                      │
│                                                                │
│  Session.handleXxx() 完全不用改                                │
└──────────────────────────────────────────────────────────────┘
```

新增代码量：~200-300 行（HTTP→ACP request 适配 + SSE/WS→ACP notification 适配）。

### 2.2 ACP session 状态机

**位置**：`packages/cli/src/acp-integration/session/`

包含：
- `Session.ts` —— 单 session 完整状态机
- `HistoryReplayer.ts` —— transcript replay（用于 LoadSession）
- `SubAgentTracker.ts` —— 子 agent 追踪
- `permissionUtils.ts` —— 与 PR#3723 permission flow 桥接
- `emitters/` —— SessionNotification 事件流
- `rewrite/` —— history 重写工具（关联 PR#3810 invalidation）

**daemon 视角**：每个 HTTP 客户端的 session 操作（new / prompt / load / set-model / set-mode / cancel）**直接路由到现有 Session 实例**，不需要新代码。

### 2.3 Channels SessionRouter

**位置**：`packages/channels/base/src/SessionRouter.ts`

```ts
export class SessionRouter {
  private toSession: Map<string, string> = new Map();      // routing key → session ID
  private toTarget: Map<string, SessionTarget> = new Map(); // session ID → target
  private toCwd: Map<string, string> = new Map();           // session ID → cwd
  private channelScopes: Map<string, SessionScope> = new Map();

  private routingKey(channelName, senderId, chatId, threadId) {
    const scope = this.channelScopes.get(channelName) || this.defaultScope;
    switch (scope) {
      case 'thread': return `${channelName}:${threadId || chatId}`
      case 'single': return `${channelName}:__single__`
      case 'user':   return `${channelName}:${senderId}:${chatId}`
    }
  }
}
```

**daemon 视角**：HTTP 客户端就是新 channel `'http'`。`routingKey` 由 daemon 用 `clientId + workspaceId` 组合。已有的 `'thread' / 'single' / 'user'` scope 在 daemon 上下文里映射为：

| scope | daemon 含义 |
|---|---|
| `thread` | 每 HTTP request 独立 session（headless 短任务）|
| `single` | 每 workspace 一个 session（典型 IDE 用法）|
| `user` | 跨 client 共享同一 session（手机→电脑续行）|

### 2.4 SDK Transport 抽象

**位置**：`packages/sdk-typescript/src/transport/Transport.ts`（28 行）

```ts
/**
 * Transport interface for SDK-CLI communication
 *
 * The Transport abstraction enables communication between SDK and CLI via different mechanisms:
 * - ProcessTransport: Local subprocess via stdin/stdout (initial implementation)
 * - HttpTransport: Remote CLI via HTTP (future)         ← 注释明确预告
 * - WebSocketTransport: Remote CLI via WebSocket (future) ← 注释明确预告
 */

export interface Transport {
  close(): Promise<void>;
  waitForExit(): Promise<void>;
  write(message: string): void;
  readMessages(): AsyncGenerator<unknown, void, unknown>;
  readonly isReady: boolean;
  readonly exitError: Error | null;
}
```

**这是 SDK 团队预留的 daemon 接口**——HttpTransport 只需镜像 ProcessTransport 的形态，把 spawn 改成 fetch + EventSource。

新增代码量：~150-200 行（HttpTransport 类）。

### 2.5 PR#3723 共享 L3→L4 permission flow

**位置**：`packages/core/src/core/permissionFlow.ts`（PR#3723 引入，161 行）

**已合并**——支持 Interactive / Non-Interactive / ACP 三种 mode。daemon 加为第 4 种 mode 即可：

```ts
// 现有 (PR#3723)
export function evaluatePermissionFlow(
  tool: Tool,
  context: ExecutionContext,  // 含 mode: 'interactive' | 'non-interactive' | 'acp'
): PermissionFlowResult { ... }

// daemon 改造（最小）
type ExecutionMode = 'interactive' | 'non-interactive' | 'acp' | 'daemon-http'
//                                                                  ^^^^^^^^^^ 新增
```

**daemon 模式下的特殊行为**：
- `ask` 决策不能阻塞 HTTP request（HTTP 不像 stdio 能等用户回车）
- 改用 SSE 推 `permission_request` 事件给 client，HTTP request 挂起等 client 回 `POST /permission/:requestId` 响应

### 2.6 vscode-ide-companion 的 ide-server.ts（参考模板）

**位置**：`packages/vscode-ide-companion/src/ide-server.ts`（~500 行）

已用 express + cors + auth token 起 HTTP 服务，给 IDE 用。**daemon 设计可直接参考这套模板**：

```ts
// ide-server.ts 已有的代码模式
import { StreamableHTTPServerTransport } from '@modelcontextprotocol/sdk/server/streamableHttp.js';
import express from 'express';
import cors from 'cors';

const MCP_SESSION_ID_HEADER = 'mcp-session-id';
const IDE_SERVER_PORT_ENV_VAR = 'QWEN_CODE_IDE_SERVER_PORT';

// auth token 校验逻辑、session header 路由、CORS 配置等都可以参考
this.server = app.listen(0, '127.0.0.1', async () => { ... });
```

**daemon 设计建议升级 express → Hono**（与 OpenCode 一致 + Bun 友好），但逻辑结构可参考。

### 2.7 WebUI ACPAdapter

**位置**：`packages/webui/src/adapters/ACPAdapter.ts`

WebUI 已经设计为通过 ACPAdapter 与后端通信。daemon 模式下，**只需新加 HttpAcpAdapter**（继承同接口，传输层换 HTTP/WS）：

```ts
// 现有
export class ACPAdapter implements WebUIAdapter { ... }
export class JSONLAdapter implements WebUIAdapter { ... }

// 新增
export class HttpAcpAdapter implements WebUIAdapter {
  constructor(opts: { baseUrl: string, bearerToken?: string }) { ... }
  // 复用 ACPAdapter 的事件分发逻辑，仅传输层换 fetch + EventSource
}
```

新增代码量：~150 行。

## 三、复用度统计

按"daemon 化所需总工作"作分母，估算复用率：

| 模块 | 总工作量 | 现有可复用 | 净新增 |
|---|---|---|---|
| 协议 schema（session / permission / cancel / model 等） | 100% | 95%（ACP zod schema）| 5%（daemon-mode flag 等扩展）|
| 核心业务逻辑（Session / SessionService / FileReadCache / ...）| 100% | 100% | 0 |
| 多客户端路由 | 100% | 80%（SessionRouter）| 20%（HTTP scope 适配）|
| HTTP server（路由 / middleware / WS）| 100% | 30%（ide-server.ts 参考）| 70%（新建 server/）|
| SDK 客户端（HttpTransport）| 100% | 50%（Transport 接口 + ProcessTransport 模式）| 50%（HTTP 实现）|
| 权限流 | 100% | 95%（PR#3723）| 5%（加 daemon mode 分支）|
| WebUI 接入 | 100% | 90%（ACPAdapter）| 10%（HttpAcpAdapter）|
| **加权平均** | — | **~75%** | **~25%** |

实际新增代码量估算：~2000-3000 行（其中 HTTP server / 路由 / 中间件占大头）。

## 四、不需要复用 / 需要 弃用 的资产

### 4.1 不应复用：ProcessTransport 的 spawn 逻辑

ProcessTransport 假设"对端是 CLI 子进程"，daemon 模式下对端是 daemon HTTP server——HttpTransport 必须从零写，不能直接继承。但 ProcessTransport 的**生命周期管理 / abort 处理 / 错误分类**模式可以复用（这部分在 ~150 行的 HttpTransport 里继续用类似设计）。

### 4.2 可考虑弃用：vscode-ide-companion 的 ide-server.ts

VSCode 当前自起 express server 给 IDE 用。daemon 推出后，**VSCode 直接连 daemon 即可**——可弃用 ide-server。但需确认：
- VSCode 的"打开多 workspace 各自独立"语义是否能在 daemon 的 multi-workspace router 下复现 ✓
- ide-server 当前的特殊功能（代码补全提示等）是否在 daemon HTTP 路由有等价物 —— 需逐项核对

**建议**：Stage 2 把 VSCode companion 切到 daemon，Stage 3 弃用 ide-server.ts（保留兼容性 deprecation 期）。

## 五、PR#3723 / PR#3717 / PR#3739 的 daemon 化加成

5 月份的几个关键 PR**为 daemon 化扫清了关键障碍**：

| PR | 对 daemon 的加成 |
|---|---|
| **PR#3723** 共享 permission flow | daemon 是第 4 种 mode，复用现有 evaluator |
| **PR#3717** FileReadCache | 已是 session-scoped + `(dev,ino)` key，跨 session 隔离天然支持 |
| **PR#3810** FileReadCache 5 路径 invalidation | 长 session 正确性保障，daemon 长跑不会出 read-empty bug |
| **PR#3739** Background agent resume + transcript-first fork | daemon 重启后 paused agent 能恢复 |
| **PR#3642** `/tasks` + background shell pool | 跨 session 任务调度框架 |
| **PR#3836** Kind framework 4 消费者（agent/shell/monitor/dream）| 后台任务的统一调度面在 daemon 模式下天然多 client 可见 |

**结论**：5 月初 daemon 化的所有前置条件都已就绪。

---

下一篇：[03-6 个架构决策 →](./03-architectural-decisions.md)
