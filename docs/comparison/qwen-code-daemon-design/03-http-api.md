# 03 — HTTP API & Protocol

> [← 上一篇：Design Decisions](./02-architectural-decisions.md) · [下一篇：Deployment & Client →](./04-deployment-and-client.md)

## TL;DR

PR#3889 Stage 1 ✅ MERGED daemon HTTP front 暴露 9 个 STAGE1_FEATURES routes + SSE 事件流 + Last-Event-ID 重连。**协议层 0 设计成本**——HTTP body 直接复用 ACP NDJSON 的 zod schema（不自创 OpenAPI）。SDK 客户端可用 `HttpTransport` 替代 `ProcessTransport`，业务代码 0 改动。

**Stage 1 实现状态**：9/9 STAGE1_FEATURES ✅；SSE Last-Event-ID 重连 ✅；first-responder permission vote ✅。**Stage 1.5 候选**：WebSocket bidi / `loadSession` HTTP / per-request scope override / capability negotiation / daemon-side state CRUD。

**兼容性原则**：所有 Stage 1.5+ route / event / capability 必须 additive。旧 route 不移除，旧 event envelope 不破坏；client 通过 `/capabilities` feature tag 决定是否启用新 UI，不能因为新 daemon 缺某个 Stage 1.5 能力而崩溃。

---

## 一、路由总览

```
GET    /                                   服务端版本元信息（qwen / daemon / acp 版本号）
GET    /capabilities                       完整能力清单 + 当前绑定状态
GET    /health                             浅层健康检查（仅检测 listener，无认证）
GET    /health?deep=1                      深度健康检查（含 ACP child liveness + EventBus 状态，Stage 2a）
POST   /authenticate                       HTTP-only bearer token 取换 long-lived token

# Session 生命周期（ACP RPC 直接映射）
POST   /session                            create / attach session   ← NewSessionRequest
GET    /session                            list sessions             ← ListSessionsRequest（Stage 1.5）
POST   /session/:id/load                   load existing session     ← LoadSessionRequest（Stage 1.5 must-have #2）
POST   /session/:id/resume                 resume paused session     ← Stage 1.5
DELETE /session/:id                        archive / delete

# Session 交互
POST   /session/:id/prompt                 send prompt               ← PromptRequest
POST   /session/:id/cancel                 cancel current            ← CancelNotification
POST   /session/:id/model                  set model                 ← SetSessionModelRequest
POST   /session/:id/mode                   set mode                  ← SetSessionModeRequest
GET    /session/:id/events                 SSE 事件流
POST   /session/:id/heartbeat              client-initiated 心跳（Stage 1.5 must-have #4）

# Permission 流（first-responder）
POST   /permission/:requestId              vote on permission request

# Workspace（daemon 启动时绑定 cwd，无需 :id 参数）
GET    /workspace                           workspace info（cwd + 启动参数）
GET    /workspace/sessions                  list sessions
GET    /workspace/skills                    已加载 skill
GET    /workspace/mcp                       MCP server 状态
GET    /workspace/lsp                       LSP 状态
GET    /workspace/tasks                     background tasks（4 kinds）
GET    /workspace/file                      read file
POST   /workspace/file                      write file（PR#3774 prior-read 守卫）
POST   /workspace/file/edit                 edit file
POST   /workspace/pty                       open PTY（Upgrade: websocket）

# Stage 1.5c daemon-side state CRUD（支撑 TUI / channels / web / IDE）
GET    /workspace/memory                    read ~/.qwen/memory.json
POST   /workspace/memory                    update memory
POST   /workspace/mcp/:server/restart       restart MCP server
GET    /workspace/agents                    list agents
POST   /workspace/agents                    add / remove agents
POST   /workspace/tools/:name/enable        enable/disable tool
POST   /session/:id/approval-mode           set approval mode
POST   /workspace/init                      workspace init
POST   /session/:id/_meta                   per-session context（Stage 1.5 must-have #8）

# Stage 2a — Protocol Completion
POST   /ext/:method                         ACP extMethod 桥接（给 vendor zero-fork 扩展）
WS     /session/:id                         WebSocket bidi 升级（与 SSE 并存）
```

### `:id` 校验语义

- `sessionId` 必须存在于 `QwenAgent.sessions: Map` 内；不匹配 `404 session_not_found`
- daemon 启动时绑定单 workspace（cwd 启动参数）；多 workspace 部署 = 多 daemon process 各占独立 port
- 保留 sessionId 在 URL 是 fail-fast 防御（防 client 拿错 daemon URL）

> **PR#3889 现状**：commit `6a170ef8` 实现的是 `/workspace/:id/*` multi-workspace 路由（要求 client 提供 cwd path 作 `:id`）；[PR#4113](https://github.com/QwenLM/qwen-code/pull/4113) 简化为 `/workspace/*` 单 workspace 路由（client 不再传 cwd，daemon 启动时已绑定）+ 新增 `CapabilitiesEnvelope.workspaceCwd` 字段让 client pre-flight check + cross-workspace `POST /session` 返回 `400 workspace_mismatch`。

---

## 二、ACP wire 兼容性 — 4 层矩阵

> **术语**：**wire** = 两端点之间通过协议实际传输的字节流（"over the wire" = "通过协议传"）。本系列指 daemon ↔ client 之间通过 HTTP+SSE/WebSocket 传的 ACP NDJSON 协议。与 **schema**（zod 类型定义 / IDL）区分——schema 是契约，wire 是按 schema 编码后**实际字节**。常见用法：
> - **"wire 字节级一致"** = 不同 transport（HTTP SSE / future WebSocket facade）下序列化结果 bit-for-bit 相同（client 单一代码路径）
> - **"不出 wire"** = 仅在 daemon 内处理，不通过 HTTP 协议暴露给 client（详 [§04 §二 TUI / client 边界](./04-deployment-and-client.md)）
> - **"wire 协议锁定"** = HTTP routes + SSE event schema + zod schema 不再扩展（Stage 2 后）
> - **"新 wire route"** = 新增 HTTP 路由（Stage 1.5c daemon-side state CRUD）
> - **"ACP wire 版本"** = ACP NDJSON 协议本身的版本号（与 SDK 版本 / daemon envelope 版本区分）

> 单进程模式（`qwen --acp` stdio NDJSON）与 Daemon 模式（`qwen serve` HTTP）的协议兼容性分析。**结论：Schema 层完全兼容、Wire 层不兼容、SDK 抽象层用户代码 0 改动**。

| 层 | 单进程 | Daemon | 兼容性 |
|---|---|---|---|
| **Schema 层**（ACP zod schema）| `PromptRequest` / `NewSessionRequest` 等 | **复用同一组 ACP zod schema**（`@agentclientprotocol/sdk`）| ✅ **100%** |
| **Wire 层**（传输）| stdio NDJSON | HTTP request/response + SSE/WS 事件流 | ⚠️ 字节级不兼容 |
| **业务逻辑层**（Session.handleXxx）| `Session.handlePromptRequest()` 直接调用 | **同一函数**（daemon 内 wrapper 把 HTTP body 解为 ACP request 后调同一个函数）| ✅ **100% 同源** |
| **SDK 抽象层**（Transport）| `ProcessTransport` | `HttpTransport`（Stage 2b）| ✅ 用户代码 0 改动 |

### 关键非兼容点（4 项）+ Adapter 处理

| 不兼容点 | Adapter 责任 |
|---|---|
| HTTP body ↔ ACP request | 用 zod schema 校验 + 字段映射 |
| SSE event ↔ ACP notification | wrapper 把 `SessionNotification` → SSE `data:` 帧 |
| `permission_request` 同步→异步 | `pendingRequests Map<id, resolver>` + 60s 超时 + 60s 默认 deny |
| Client capabilities（`read_text_file` 等）| client 需注册 callback URL，agent 发 SSE 调 client，client 调 callback HTTP |

### 复用 ACP zod schema 的工程价值

```ts
// 现有 ACP request:  PromptRequest / NewSessionRequest / SetSessionModelRequest 等
// daemon HTTP body 沿用同结构，仅把传输层从 stdio NDJSON 换成 HTTP
POST /session                  body: NewSessionRequest
POST /session/:id/prompt       body: PromptRequest
POST /session/:id/model        body: SetSessionModelRequest
```

**好处**：协议层 0 设计成本（ACP 已经把 session 生命周期、permission 流、cancel、resume、fork 验证过），唯一新增的是传输层桥接。

---

## 三、SSE 事件流（PR#3889 commit `41aa95094` 已实现）

### SSE event 结构

```
event: session_update
id: 42
data: {"id":42,"v":1,"type":"session_update","data":{"sessionUpdate":"agent_message_chunk","content":{"type":"text","text":"…"}},"originatorClientId":"…"}
```

每帧带：
- SSE 标准 `id:` / `event:` 行（EventSource 客户端约定）
- 完整 JSON envelope（`{id?, v, type, data, originatorClientId?}`）—— raw-fetch 消费者也能拿到

### 事件类型枚举

| 类型 | 含义 |
|---|---|
| `session_update` | LLM stream / tool call / tool result / usage 等 ACP `SessionNotification` |
| `permission_request` | agent 请审批（与 wire request id 配对）|
| `permission_resolved` | first-responder 已应答 |
| `permission_already_resolved` | vote loser 收到（Stage 1.5 must-have #5）|
| `model_switched` | model 切换成功 |
| `model_switch_failed` | model 切换失败 |
| `session_died` | daemon 内嵌 `qwen --acp` child 退出 → 该 daemon 全部 session 死亡 |
| `client_evicted` | 该 subscriber queue overflow，被踢 |
| `slow_client_warning` | overflow 前 soft 警告（Stage 1.5 must-have #7）|

### Last-Event-ID 重连协议

CLI 重连时传 `Last-Event-ID` header：
1. daemon 用 PR#3739 transcript-first fork resume 重建 session 状态（如 daemon restart 过）
2. 从 `Last-Event-ID + 1` 拉 missed events
3. 客户端 UI 无缝续接

**Ring 大小**：default 1000 帧 → 增至 4000（commit `41aa95094`）；Stage 1.5 must-have #6 改为 per-session 可配置（默认 8000）。

### Ring overflow

慢消费 client 队列满 → 发 `client_evicted` event 后从 subscriber set 移除 → daemon 不再积压 memory。Stage 1.5 must-have #7 加 `slow_client_warning` soft 警告。

---

## 四、双向 RPC 的不对称（核心难点）

### ACP 协议本质：双向 RPC

stdio NDJSON 模式下，client 和 agent 双方都能发起 request：

```
Client → Agent: prompt / cancel / setSessionModel ...
Agent → Client: requestPermission / readTextFile / writeTextFile ...
```

### stdio 模式：对称

```
                    bidirectional ACP NDJSON
       Client                                     Agent
       writeLine ─────────────────────────────→
                                                   ← writeLine
       readLine  ←─────────────────────────────
                                                   ← readLine
```

### HTTP 模式：不对称（只 client→daemon）

```
HTTP request: client → daemon （单向）
SSE event:    daemon → client （单向）
HTTP response: daemon → client （同步 client→daemon 的 reply）

但 daemon 没法主动发 HTTP request 到 client！
```

**实际影响**：
- ✅ client→agent: 直接 HTTP request
- ⚠️ agent→client: 改成 SSE event + client callback URL（client 注册自己能接收的 capabilities）
- ⚠️ `permission_request`: 改成 SSE event + client `POST /permission/:requestId` 应答

### `permission_request` 异步流模式

```
1. agent 调用 tool → 触发 permission check
2. PermissionManager → SSE 推 `permission_request` event 到所有订阅 client
3. HTTP request 挂起（pending）
4. 任意 client `POST /permission/:requestId` 应答（first-responder）
5. PermissionManager 收到应答 → 解锁 HTTP request → 继续 tool 执行
6. SSE 推 `permission_resolved` event 让其他 client 知道结果
```

详 [§05 Security & Permission](./05-permission-auth.md)。

---

## 五、Capability negotiation（Stage 1.5 must-have #9 + chiga0 finding 5）

**Stage 1 现状**：`/capabilities` 返回 hard-coded 9-tag 数组——`v: 2` client 接 `v: 1` daemon 时新 frame 类型只能 fall through。

**Stage 1.5+ 修订**：`/capabilities` 加 `protocol_versions` 字段：

```jsonc
GET /capabilities
{
  "v": 1,
  "mode": "http-bridge",
  "features": [/* Stage 1 9 tags + Stage 1.5c 新 tags */],
  "protocol_versions": {                              // 🆕
    "acp": "0.14.x",                                   // ACP wire 版本
    "daemon_envelope": 1                               // SSE envelope schema 版本
  },
  "modelServices": [/* ... */]
}
```

**chiga0 finding 5（Stage 1.5b / Stage 2a）**：hard-coded `STAGE1_FEATURES` 数组改为 plug-in capability registry——让 `POST /ext/:method` ACP extMethod 桥接给 vendor zero-fork 扩展（vendor 注册 capability tag → registry → `/capabilities` 自动包括）。

**Stage 1.5c daemon-side state CRUD 注册的新 tags**：

```
'workspace_memory_crud'    'workspace_mcp_management'
'workspace_agents_crud'    'workspace_tools_crud'
'session_approval_mode'    'workspace_init'
'auth_device_flow'
```

远端 client 通过 `GET /capabilities` 协商可用功能集——daemon 不支持的 tag client 优雅降级（gray-out dialog）。

---

## 六、Daemon 层 vs Orchestrator 层

> **Daemon 层** = PR#3889 已落地的主线 routes（§一 + §三 + §四 + §五）。
> **Orchestrator 层** = External Reference Architecture（[§06 §5.1](./06-roadmap.md#51-cross-daemon-orchestrator跨-daemon-process--跨机器)）—— 仅跨 daemon process / 跨机器场景需要。**单机部署完全不需要 orchestrator**。

### Orchestrator API（External，仅跨 daemon process 场景）

```
GET    /coordinator/sessions                       列出所有 active daemon processes
POST   /coordinator/sessions/:id/route             解析 sessionId → daemonUrl
GET    /coordinator/aggregate                      跨 daemon "我所有 task" 聚合
POST   /coordinator/sessions                       create session（orchestrator 路由到 daemon）
```

SDK 加 `coordinatorUrl` 配置项区分两种部署：
- 单机部署（单 daemon Mode B）：跳过 orchestrator 直连 daemon URL
- 跨 daemon process 部署：通过 orchestrator 路由 sessionId → daemonUrl

---

## 七、SDK 用户代码 0 改动

```ts
// 旧（单进程 stdio）
const q = query({ transport: new ProcessTransport(...) })

// 新（daemon HTTP，Stage 2b 落地后）
const q = query({ transport: new HttpTransport({
  baseUrl: 'http://localhost:5096',
  bearerToken: process.env.QWEN_SERVER_TOKEN,
}) })
```

`Transport` 接口不变；业务代码一行不改。

---

## 八、Stage 演进的兼容性

| Stage | 实现方式 | 与 stdio 兼容性 |
|---|---|---|
| **Stage 1**（✅ MERGED 2026-05-13）| daemon 内 `qwen --acp` child + HTTP↔stdio 桥接 | **业务逻辑 100% 同源**——同一个 ACP agent，仅外面包了层 HTTP 翻译 |
| **1.5-prereq**（Mode B event contract）| typed `SessionEvent` / `ControlEvent` + shared `DaemonSessionClient` over HTTP/SSE | wire 仍是 HTTP/SSE；client 共享 reducer / event schema |
| **Stage 1.5c**（primary client adapters）| TUI / channels / web / IDE 接入 daemon HTTP/SSE | 适配层变化；daemon wire 向后兼容 |
| **Stage 1.5c**（daemon-side state CRUD）| 加 memory / MCP / skills / tools / agents / auth / provider / context 等 HTTP routes | 协议扩展，向后兼容（new capabilities via tag）|
| **Stage 2a**（Protocol completion）| WebSocket bidi + /health?deep + /ext/:method | 协议扩展，向后兼容 |
| **Stage 2e**（可选 native in-process）| 去 `qwen --acp` child，daemon 直接 import `QwenAgent` | wire 协议不变，业务逻辑同源 |

---

下一篇：[04 — Deployment & Client →](./04-deployment-and-client.md)
