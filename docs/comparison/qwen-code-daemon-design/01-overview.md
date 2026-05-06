# 01 — 架构总览

> [← 返回 README](./README.md) · [下一篇：现有资产盘点 →](./02-existing-assets.md)

## 一、daemon 模型 vs Qwen 当前的 subprocess 模型

Qwen Code 当前的程序化访问形态：

```
┌─────────────────────┐  spawn  ┌────────────────────────┐
│ SDK 客户端           │────────▶│ qwen CLI 子进程（短生命）│
│ (TS/Python/Java)    │  stdin  │ ├─ ProcessTransport     │
│                     │  stdout │ │  NDJSON 流             │
│                     │         │ └─ core (库调用)         │
└─────────────────────┘         └────────────────────────┘

每次 SDK query() / Client 实例 = 1 个 CLI 子进程
```

引入 daemon 后：

```
┌─────────────────────┐  HTTP/WS  ┌──────────────────────────────┐
│ SDK 客户端 1         │──────────▶│ qwen daemon 进程（长生命）     │
└─────────────────────┘           │ ├─ Hono / Bun.serve           │
                                   │ ├─ Instance Map               │
┌─────────────────────┐  HTTP/WS  │ │   ├─ workspace A             │
│ Web UI / VSCode     │──────────▶│ │   │   ├─ session 1 (in-mem)  │
└─────────────────────┘           │ │   │   ├─ session 2 (in-mem)  │
                                   │ │   │   └─ LSP server (子进程) │
┌─────────────────────┐  HTTP/WS  │ │   └─ workspace B             │
│ Channel adapters    │──────────▶│ │       └─ ...                 │
│ (IM / Telegram)     │           │ ├─ MCP servers (跨 session 复用) │
└─────────────────────┘           │ └─ core in-process（库调用）   │
                                   └──────────────────────────────┘

启动 daemon 一次 → N 个 client 永久 HTTP/WS 复用
```

## 二、本质差异（与 OpenCode 共识 + Qwen 特色）

### 2.1 与 OpenCode 共识的 4 条原则

| 原则 | OpenCode | Qwen Daemon（本设计）|
|---|---|---|
| daemon 不再 spawn CLI | core 直接 import | 同样 |
| 多 session 共享主进程 | `Map<directory, InstanceContext>` | 同样（`Map<workspaceId, Instance>`）|
| `process.cwd()` 不变 | `AsyncLocalStorage` 上下文传播 | 同样（详见 [05-进程模型](./05-process-model.md)）|
| SQLite 持久化关键状态 | `session.sql.ts:SessionTable` | 复用 Qwen 已有 JSONL session（PR#3739 强化）|

### 2.2 Qwen 独有的 3 条特色

#### 特色 1：复用 ACP NDJSON schema 作为内部 RPC

OpenCode 自创 OpenAPI schema（13525 行 `openapi.json`），Qwen Code 已经有 838 行的 ACP agent 实现完整 NDJSON 协议（`packages/cli/src/acp-integration/acpAgent.ts`）。

**daemon HTTP 路由的请求/响应 body 直接复用 ACP 的 zod schema**：

```ts
// 现有 ACP request:  PromptRequest / NewSessionRequest / SetSessionModelRequest 等
// daemon HTTP body 沿用同结构，仅把传输层从 stdio NDJSON 换成 HTTP

POST /session                  body: NewSessionRequest
POST /session/:id/prompt       body: PromptRequest
POST /session/:id/model        body: SetSessionModelRequest
```

详见 [04-HTTP API 设计](./04-http-api.md)。

**好处**：协议层 0 设计成本（ACP 已经把 session 生命周期、permission 流、cancel、resume、fork 验证过），唯一新增的是传输层桥接。

#### 特色 2：Channels SessionRouter 天然适配多 client

OpenCode 是 daemon 的"单租户"——只有 SDK 客户端连。Qwen Code 的 `packages/channels/base/src/SessionRouter.ts` 已经为多用户 / 多 IM 平台设计：

```ts
// SessionRouter.ts 现有能力
private toSession: Map<string, string>    // routing key → session ID
private toTarget: Map<string, SessionTarget>
private channelScopes: Map<string, SessionScope>  // 'thread' | 'single' | 'user'
```

daemon 模式下，**HTTP/WS 客户端就是另一种 channel**——直接复用 SessionRouter 的多路由能力，IM / WebUI / IDE / SDK 都走同一个路由层。

#### 特色 3：双轨认证（bearer token + 复用 PR#3723 权限流）

OpenCode 用单一 `OPENCODE_SERVER_PASSWORD`（粗粒度访问控制）。Qwen 设计采用**两层权限**：

| 层 | 作用 | 复用 |
|---|---|---|
| **传输层 bearer token** | 阻止未授权访问 daemon | env var + middleware（参考 OpenCode）|
| **应用层 permission flow** | 工具调用是否需要审批 / domain allowlist | **直接复用 PR#3723 的 `evaluatePermissionFlow()`** —— Interactive / Non-Interactive / ACP 三模式已合并，daemon 是第 4 种 |

详见 [07-权限/认证](./07-permission-auth.md)。

## 三、整体架构图

```
┌────────────────────────────────────────────────────────────────┐
│  qwen daemon 进程 (qwen serve)                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ HTTP / WebSocket 入口（Hono · 默认 Bun.serve / Node 回退）│  │
│  │ ├─ Auth middleware (bearer token)                        │  │
│  │ ├─ /session / /file / /pty / /event / ...                │  │
│  │ └─ WS upgrade → SSE/WebSocket 流式事件                   │  │
│  └──────────────────────────────────────────────────────────┘  │
│                          ↓                                      │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ HTTP → ACP Adapter（HttpAcpBridge）                       │  │
│  │ - 把 HTTP body 解析为 ACP request 类型                    │  │
│  │ - 调用 core 的 ACP-equivalent in-process API              │  │
│  │ - 把 SessionNotification stream 转 SSE/WS                 │  │
│  └──────────────────────────────────────────────────────────┘  │
│                          ↓                                      │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Channels SessionRouter（多 client 路由）                   │  │
│  │ - 复用现有 SessionRouter / PairingStore                   │  │
│  │ - HTTP client 注册为 'http' channel                       │  │
│  └──────────────────────────────────────────────────────────┘  │
│                          ↓                                      │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Instance Map（workspaceId → Instance）                    │  │
│  │ ┌──────────┬──────────┬──────────┬─────────────────────┐ │  │
│  │ │ ws-A     │ ws-B     │ ws-C     │ AsyncLocalStorage   │ │  │
│  │ │ ├ ses 1  │ ├ ses 1  │ ├ ses 1  │ Instance.directory  │ │  │
│  │ │ ├ ses 2  │ ├ ses 2  │ ├ ses 2  │ 跨 await 隔离       │ │  │
│  │ │ ├ LSP    │ ├ LSP    │ ├ LSP    │                     │ │  │
│  │ │ └ shared │ └ shared │ └ shared │                     │ │  │
│  │ └──────────┴──────────┴──────────┴─────────────────────┘ │  │
│  └──────────────────────────────────────────────────────────┘  │
│                          ↓                                      │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ core (in-process 库调用)                                  │  │
│  │ - SessionService（PR#3739 transcript-first resume）        │  │
│  │ - FileReadCache（PR#3717 + PR#3810 5 路径 invalidation）   │  │
│  │ - Permission flow（PR#3723 共享 L3→L4）                   │  │
│  │ - MCP client manager（PR#3818 coalesce rediscovery）      │  │
│  │ - Background tasks（PR#3471/3488/3642/3791/3836 4 kinds） │  │
│  └──────────────────────────────────────────────────────────┘  │
│                          ↓                                      │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ 子进程层（按需 spawn，跨 session 复用）                    │  │
│  │ - LSP servers（每 workspace 一个）                         │  │
│  │ - MCP servers（每 MCP 配置一个，全局共享）                  │  │
│  │ - PTY / Bash 工具调用（按工具调用粒度）                    │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────┘
```

## 四、关键设计决策预告

| # | 决策 | 选择 | 详细 |
|---|---|---|---|
| 1 | session 是否跨 client 共享 | **默认 `single`（同 workspace 多 client 共享）—— 匹配单用户多 client 真实场景** | [03 §1](./03-architectural-decisions.md#1-session-是否跨-client-共享) |
| 2 | 状态进程模型 | **单 daemon 进程承载全部 session** | [03 §2](./03-architectural-decisions.md#2-状态进程模型) |
| 3 | MCP server 生命周期 | **per-workspace MCP state（与 OpenCode 一致）+ Qwen 保留 PR#3818 in-flight coalesce + 30s 健康检查 2 项独有优化** | [06](./06-mcp-resources.md) |
| 4 | FileReadCache 共享 | **session 内私有，绝不跨 session**（PR#3774 prior-read 守卫语义依赖此）| [06 §2](./06-mcp-resources.md#2-filereadcache-共享策略) |
| 5 | Permission flow | **复用 PR#3723，daemon 是第 4 种 mode + 任何 client 都能应答** | [07](./07-permission-auth.md) |
| 6 | 多 client 并发请求 | **同 session prompt 串行 + 事件 fan-out 多 client 协作观察** | [03 §6](./03-architectural-decisions.md#6-多-client-并发请求) |

## 五、最终用户体验

启动 daemon：

```bash
qwen serve                                # 默认 127.0.0.1:5096，无认证（开发场景）
QWEN_SERVER_TOKEN=xxx qwen serve --port 8080 --hostname 0.0.0.0  # 远程访问
```

SDK 用法（无需修改现有 ProcessTransport，新加 HttpTransport）：

```ts
// 现有 SDK Transport 抽象（packages/sdk-typescript/src/transport/Transport.ts）
// 注释已经预告: "HttpTransport: Remote CLI via HTTP (future)"

import { query, HttpTransport } from '@qwen-code/sdk'

const q = query({
  transport: new HttpTransport({
    baseUrl: 'http://localhost:5096',
    bearerToken: process.env.QWEN_SERVER_TOKEN,
    workspaceId: 'my-project',
    cwd: '/path/to/project',
  }),
  prompt: '请帮我重构这个文件',
})

for await (const msg of q) { ... }
```

WebUI 用法：

```ts
// packages/webui 已有 ACPAdapter（packages/webui/src/adapters/ACPAdapter.ts）
// 把传输层从 stdio 切到 HTTP/WS 即可
const adapter = new HttpAcpAdapter({ baseUrl: 'http://localhost:5096', ... })
```

VSCode 用法（替代当前的 ide-server 模式）：

```ts
// 现状：vscode-ide-companion 自己起 ide-server (express)
// 新：vscode-ide-companion 直接连 qwen daemon (HTTP)，省去自起 server
```

Channels（IM / Telegram / 微信）用法：保持不变（ChannelAdapter → AcpBridge → daemon HTTP route，与 stdio 等价）。

## 六、与 OpenCode 设计的核心差异

| 维度 | OpenCode | Qwen Daemon（本设计）|
|---|---|---|
| **HTTP 框架** | Hono | Hono（同款）|
| **Schema 来源** | 自创 OpenAPI（13525 行 codegen）| **复用 ACP NDJSON zod schema** |
| **多 channel 支持** | 仅 SDK / TUI / Web | **SDK / TUI / Web / IM / IDE 全走 SessionRouter** |
| **认证** | 单密码 `OPENCODE_SERVER_PASSWORD` | **bearer token + 应用层 PR#3723 权限流** |
| **mDNS 发现** | ✓ 默认开启 | 🟡 Stage 2 可选（默认关）|
| **session 跨 client 共享** | 否（每 SDK call 独立 session）| **是（默认 single + 事件 fan-out + 跨 client审批）**——live collaboration 模型 |
| **WebSocket** | Bun 原生 | 同款 + SSE 兜底 |

详见 [09-与 OpenCode 详细对比](./09-comparison-with-opencode.md)。

---

下一篇：[02-现有资产盘点 →](./02-existing-assets.md)
