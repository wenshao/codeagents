# 03 — HTTP API & Protocol

> [← 上一篇：Design Decisions](./02-architectural-decisions.md) · [下一篇：Deployment & Client →](./04-deployment-and-client.md)

## TL;DR

PR#3889 Stage 1 → Wave 1-4 + Wave 2.5 ✅ 完整 (2026-05-13~18, 21 Wave PRs MERGED, Wave plan 进度 22.5/31 ≈ 73%)。**协议层 0 设计成本**——HTTP body 复用 ACP NDJSON 的 zod schema。SDK 客户端可用 `DaemonClient` / `DaemonSessionClient` 替代 `ProcessTransport`。

**当前实现状态**（截至 2026-05-18）：
- **HTTP routes** ~40 个（Stage 1 9 个 + Wave 1-4 新增 ~30 个），全部走 capability registry 协商
- **`/capabilities.features`** ~28 个 capability tag（PR#4191 capability registry 之后 additive registration）
- **Typed event schema v1**（PR#4217）—— SDK-layer discriminated union + reducer skeleton
- **Closed `errorKind` 7-value taxonomy**（PR#4251）—— `missing_binary` / `blocked_egress` / `auth_env_error` / `init_timeout` / `protocol_error` / `missing_file` / `parse_error`
- **三套来源 lockstep 模式**（PR#4214 立 invariant）—— 生产 `SERVE_CAPABILITY_REGISTRY` ↔ unit `EXPECTED_STAGE1_FEATURES` ↔ integration `caps.features` toEqual

**兼容性原则**：所有 Stage 1.5+ route / event / capability 必须 additive。旧 route 不移除，旧 event envelope 不破坏；client 通过 `/capabilities` feature tag 决定是否启用新 UI，不能因为新 daemon 缺某个 Stage 1.5 能力而崩溃。**`v: 1` envelope 不破坏** —— PR#4217 `narrowDaemonEvent` 对未知 type 返 `kind: 'unknown'` 而非报错，让 SDK 向前兼容新 daemon。

---

## 一、路由总览

### Stage 1（PR#3889 ✅ MERGED 2026-05-13）

```
GET    /                                   服务端版本元信息（qwen / daemon / acp 版本号）
GET    /capabilities                       完整能力清单 + 当前绑定状态
GET    /health                             浅层健康检查（仅检测 listener，无认证）
POST   /authenticate                       HTTP-only bearer token 取换 long-lived token

POST   /session                            create / attach session   ← NewSessionRequest
DELETE /session/:id                        archive / delete
POST   /session/:id/prompt                 send prompt               ← PromptRequest
POST   /session/:id/cancel                 cancel current            ← CancelNotification
POST   /session/:id/model                  set model                 ← SetSessionModelRequest
POST   /session/:id/mode                   set mode                  ← SetSessionModeRequest
GET    /session/:id/events                 SSE 事件流
POST   /permission/:requestId              vote on permission request
```

### Wave 1 — Protocol foundation（✅ MERGED）

| PR | Route / 能力 | 说明 |
|---|---|---|
| **PR#4191** ✅ | capability registry refactor | hard-coded `STAGE1_FEATURES` → plug-in registry，未来 routes additive 注册不需改 capability 数组 |
| **PR#4205** ✅ | `DaemonSessionClient` skeleton | SDK 侧统一接口（HTTP/SSE 之上 `subscribe()` / `prompt()` / `cancel()`），remote web chat / web terminal 先共享 reducer；channel / IDE future migration 复用 |
| **PR#4209** ✅ | typed `SessionEvent` / `ControlEvent` schema 草案 | wire envelope `{id, v, type, data, originatorClientId?}` + zod schema lockstep |
| **PR#4217** ✅ | typed event schema **v1** | `narrowDaemonEvent()` discriminated union；未知 type → `kind: 'unknown'` 向前兼容；reducer skeleton |
| **PR#4214** ✅ | 三套来源 lockstep 立 invariant | 生产 `SERVE_CAPABILITY_REGISTRY` ↔ unit `EXPECTED_STAGE1_FEATURES` ↔ integration `caps.features` `toEqual` |

### Wave 2 — Session lifecycle（✅ MERGED）

```
POST   /session                            create / attach session（PR#4201 加 sessionScope override + idempotent attach）
POST   /session/:id/load                   load existing session（PR#4222 ✅ ACP LoadSessionRequest 直通；prior-state 守卫）
POST   /session/:id/resume                 resume paused session（PR#4222 ✅）

# clientId daemon 端 stamping（PR#4231）
X-Qwen-Client-Id: client_<randomUUID>      daemon 启动时 randomUUID；client 不允许伪造；122 bits entropy
                                           所有 mutation / permission 路由强制带；缺失返 401

# session-scoped permission（PR#4232）
POST   /session/:id/permission/:requestId  scoped permission vote（与 §05 permission flow 对齐）
                                           bounded record（同 sessionId 同 requestId 只能投一次）
                                           解析共享 helper `parsePermissionOutcome()`
                                           失败 → `permission_already_resolved` event
```

### Wave 2.5 — Reliability（✅ MERGED）

| PR | Route / 事件 | 说明 |
|---|---|---|
| **PR#4235** ✅ | `POST /session/:id/heartbeat` | client-initiated 心跳；daemon 用 `lastSeenAt` 跟踪 client liveness |
| **PR#4237** ✅ | SSE Last-Event-ID replay + `slow_client_warning` event | ring overflow 前 soft 警告；overflow 后 `client_evicted` 才踢；replay 边界 `bufferedSinceFirstId` 字段 |
| **PR#4240** ✅ | `DELETE /session/:id` close-delete + session metadata | 显式 close + tombstone（防 attach-after-close 竞态）|

### Wave 3 — Read-only control plane（✅ MERGED）

```
GET    /workspace                          workspace info（PR#4241 ✅）
GET    /workspace/sessions                 list sessions（PR#4241 ✅）
GET    /workspace/mcp                      MCP server 状态（PR#4241 ✅, PR#4271 ✅ 加 push 事件）
GET    /workspace/skills                   已加载 skill
GET    /workspace/tasks                    background tasks（4 kinds）
GET    /workspace/preflight                preflight 诊断（PR#4247 ✅ 关 `errorKind` 7-value taxonomy）
GET    /workspace/env                      env 诊断（PR#4247 ✅）
POST   /workspace/mcp/:server/restart      restart MCP server（PR#4251 ✅，readonly-stage 守卫）
GET    /workspace/mcp/budget               MCP budget（PR#4271 ✅ snapshot + `mcp_budget_warning` push 事件，rate-limited）
```

### Wave 4 — Auth-gated mutation routes（✅ 7/7 MERGED）

```
# Wave 4 启动 — mutation gate（PR#4236）
--require-auth flag                        启用后所有 mutation 路由强制 401 if 无 bearer + clientId
CONDITIONAL_SERVE_FEATURES                 capability registry 增加 4-cell behavior matrix（gate × auth state）

# Memory CRUD（PR#4249 ✅）
GET    /workspace/memory                   read ~/.qwen/memory
POST   /workspace/memory                   update memory（mutation gate）

# Agents CRUD（PR#4249 ✅）
GET    /workspace/agents                   list agents
POST   /workspace/agents                   add / remove agents

# Approval / tools / init / MCP restart（PR#4250 ✅）
POST   /session/:id/approval-mode          set approval mode
POST   /workspace/tools/:name/enable       enable / disable tool
POST   /workspace/init                     workspace init
POST   /workspace/mcp/:server/restart      restart MCP server（mutation 版本）

# FS boundary 强约束（PR#4282 ✅ PR 17 ：rebase 风暴后 +6080 改 26 文件 135 reviews 终合）
sandbox roots / no-escape policy           audit hooks 强制 originatorClientId + SHA-256-hashed paths

# File read（PR#4269 ✅）
GET    /workspace/file?path=…              read file（prior-read 跟踪）

# File write / edit（PR#4280 ✅ PR 20: +6172 39 文件 +135 reviews）
POST   /workspace/file                     write file
POST   /workspace/file/edit                edit file（patch 模型）
                                           PR#3774 prior-read 守卫 / write-without-read 守 / unicode danger 守

# OAuth device-flow（PR#4255 ✅ PR 21: +4828 35 文件 20h39m 史上最难合）
POST   /workspace/auth/device-flow         initiate device flow（RFC 8628）
POST   /workspace/auth/device-flow/poll    poll for token
                                           BrandedSecret 4-way redaction（serialize / inspect / toString / JSON.stringify）
                                           0o600 file mode（umask-respecting）
                                           6 leak-path coverage tests
                                           build-time grep 防 client browser-spawn
```

### Wave 5 — Architecture extraction（部分 MERGED）

| PR | 阶段 | 状态 | 说明 |
|---|---|---|---|
| **PR#4295** | PR 22a zero-coupling lift | ✅ MERGED | `BridgeTimeoutError` / `BridgeChannelClosedError` / `MissingCliEntryError` typed errors 提取（零业务耦合） |
| **PR#4298** | PR 22b/1 pure-type lift | ✅ MERGED | bridge primitive type 提取（与运行时实现分离） |
| **PR#4304** | PR 22b/2 design slice: lift BridgeOptions + DaemonStatusProvider seam | ✅ MERGED | 6 design decisions baked in；为 Stage 2 native in-process 开 seam；机械 bulk lift 留 PR 22b/3 |
| PR 22b/3 | mechanical bulk lift（BridgeClient + factory closure + 5064-LOC test move） | ⏳ 待开 | 凝结 PR 22b/2 契约后纯机械 IDE-driven `git mv`，零设计决定 |

### Stage 2 — 远期（候选）

```
WS     /session/:id                         WebSocket bidi 升级（与 SSE 并存，候选）
GET    /health?deep=1                       深度健康检查（含 ACP child liveness + EventBus 状态）
POST   /ext/:method                         ACP extMethod 桥接（给 vendor zero-fork 扩展）
POST   /workspace/pty                       open PTY（Upgrade: websocket）
GET    /workspace/lsp                       LSP 状态
POST   /session/:id/_meta                   per-session context
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

### 事件类型枚举（typed discriminated union, PR#4217）

| 类型 | 来源 PR | 含义 |
|---|---|---|
| `session_update` | Stage 1 ✅ | LLM stream / tool call / tool result / usage 等 ACP `SessionNotification` |
| `permission_request` | Stage 1 ✅ | agent 请审批（与 wire request id 配对）|
| `permission_resolved` | Stage 1 ✅ | first-responder 已应答 |
| `permission_already_resolved` | PR#4232 ✅ | vote loser 收到；bounded record（同 sessionId 同 requestId 只能投一次）|
| `model_switched` | Stage 1 ✅ | model 切换成功 |
| `model_switch_failed` | Stage 1 ✅ | model 切换失败 |
| `session_died` | Stage 1 ✅ | daemon 内嵌 `qwen --acp` child 退出 → 该 daemon 全部 session 死亡 |
| `client_evicted` | Stage 1 ✅ | 该 subscriber queue overflow，被踢 |
| `slow_client_warning` | PR#4237 ✅ | overflow 前 soft 警告 |
| `heartbeat_ack` | PR#4235 ✅ | client `POST /session/:id/heartbeat` 之后 daemon ack |
| `session_closed` | PR#4240 ✅ | `DELETE /session/:id` 之后 broadcast 给其他 subscriber |
| `mcp_budget_warning` | PR#4271 ✅ | MCP budget snapshot 超阈值；rate-limited，push channel atop snapshot |
| `mcp_server_state_changed` | PR#4271 ✅ | MCP server restart / 状态变化 |
| `auth_state_changed` | PR#4255 ✅ | OAuth device-flow 状态变化（pending / authorized / failed）|
| `unknown` | PR#4217 ✅ | 未知 type fallthrough（向前兼容新 daemon）|

> **typed envelope**：`{id, v, type, data, originatorClientId?}`，`narrowDaemonEvent()` 把 wire JSON narrow 成 discriminated union；SDK 上层 reducer 用 `kind` 字段分发，未知 type 不 throw。

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

## 五、Capability negotiation（PR#4191 capability registry refactor ✅）

### 现状：plug-in registry，不再 hard-coded

PR#4191 ✅ 把 hard-coded `STAGE1_FEATURES` 数组重构为 `SERVE_CAPABILITY_REGISTRY` —— 后续 route additive 注册不需改一处常量，只在 registry 里 `register({ tag, ... })`。

```jsonc
GET /capabilities
{
  "v": 1,
  "mode": "http-bridge",
  "workspaceCwd": "/home/user/project",                    // PR#4113 ✅
  "features": [/* ~28 tags, by-Wave 分组见下 */],
  "protocol_versions": {
    "acp": "0.14.x",
    "daemon_envelope": 1
  },
  "modelServices": [/* ... */],
  "auth": { "required": true, "type": "bearer" }           // PR#4236 mutation gate ✅
}
```

### 实际 capability tags（截至 2026-05-18，~28 个）

**Wave 0 / Stage 1 baseline**（9 个）：
```
session_lifecycle          session_prompt             session_cancel
session_model_switch       session_mode_switch        permission_vote
sse_events                 last_event_id_replay       capabilities_endpoint
```

**Wave 1 新增**（PR#4191 / 4205 / 4209 / 4217 / 4214）：
```
capability_registry_v1     typed_session_event_v1     typed_control_event_v1
daemon_session_client_v1   lockstep_invariant_v1
```

**Wave 2 新增**（PR#4201 / 4222 / 4231 / 4232）：
```
session_scope_override     session_load               session_resume
client_id_stamped          session_scoped_permission  permission_bounded_record
```

**Wave 2.5 新增**（PR#4235 / 4237 / 4240）：
```
session_heartbeat          slow_client_warning        session_close_delete
```

**Wave 3 新增**（PR#4241 / 4247 / 4251 / 4271）：
```
workspace_status_readonly  preflight_diagnostics      env_diagnostics
mcp_restart_guarded        mcp_budget_push
```

**Wave 4 新增**（PR#4236 / 4249 / 4250 / 4282 / 4269 / 4280 / 4255）：
```
mutation_gate              workspace_memory_crud      workspace_agents_crud
workspace_tools_crud       workspace_init             session_approval_mode
fs_boundary_enforced       workspace_file_read        workspace_file_write
auth_device_flow           branded_secret
```

> **CONDITIONAL_SERVE_FEATURES**（PR#4236 ✅）：mutation gate 加 4-cell behavior matrix —— `{gate: on|off} × {auth: present|absent}`，registry 根据 4 cell 状态决定是否暴露 capability。例：`auth_device_flow` 仅在 `gate=on + auth=absent` 时返回（让 client 知道走 device flow 拿 token）。

### 三套来源 lockstep（PR#4214 ✅ 立 invariant）

```
生产 (src/serve/registry.ts):
  SERVE_CAPABILITY_REGISTRY = registerTag('capability_registry_v1', ...)
                            + registerTag('session_lifecycle', ...) ...

unit (test/serve/capabilities.test.ts):
  EXPECTED_STAGE1_FEATURES = ['capability_registry_v1', 'session_lifecycle', ...]
  expect(SERVE_CAPABILITY_REGISTRY.tags).toEqual(EXPECTED_STAGE1_FEATURES)

integration (test/serve/http.integration.test.ts):
  const caps = await fetch('/capabilities').then(r => r.json())
  expect(caps.features).toEqual(EXPECTED_STAGE1_FEATURES)
```

任何新增 capability 必须三处同步改 —— invariant violation = CI 红，防 SDK 客户端假阳"feature 探测"。

### 客户端协商语义

```ts
const caps = await daemon.fetchCapabilities()
if (!caps.features.includes('workspace_memory_crud')) {
  // gray-out memory CRUD UI；不 throw，优雅降级
}
```

远端 client 通过 `GET /capabilities` 协商可用功能集——daemon 不支持的 tag client 优雅降级。

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

## 八、Closed `errorKind` 7-value taxonomy（PR#4251 ✅）

PR#4251 把 daemon HTTP 错误从 ad-hoc string 收敛为 closed enum，让 SDK 客户端可以 `switch (err.errorKind)` 而非靠 message regex。

```ts
type DaemonErrorKind =
  | 'missing_binary'    // qwen CLI 找不到（PR#4300 BridgeChannelClosedError / MissingCliEntryError 之前的早期变体）
  | 'blocked_egress'    // 网络出口被防火墙阻断（egress probe 失败）
  | 'auth_env_error'    // 必要 auth env 缺失 / 无效
  | 'init_timeout'      // ACP child init 超时
  | 'protocol_error'    // ACP NDJSON 协议错误（schema 不匹配 / 帧损坏）
  | 'missing_file'      // 文件读路径不存在 / 越 sandbox 边界
  | 'parse_error'       // request body parse / zod schema 失败
```

跨 PR 复用模式：
- PR#4247 ✅ `/workspace/preflight` + `/workspace/env` 用该枚举返诊断结果
- PR#4251 ✅ MCP restart 守卫用 `missing_binary` / `protocol_error`
- PR#4282 ✅ FS boundary 越界用 `missing_file`
- PR#4295 ✅ Wave 5 PR 22a `BridgeTimeoutError` / `BridgeChannelClosedError` / `MissingCliEntryError` 在 typed-error 层进一步细化

> typed-error 设计哲学：HTTP wire 仅暴露 7 个 closed enum；daemon 内部用富类型 `Error` 子类（`TrustGateError` / `BridgeTimeoutError` 等）保留 stack / cause / metadata，序列化到 wire 时降级到 enum + redacted message。

---

## 九、Stage 演进的兼容性

| Stage | 实现方式 | 状态 |
|---|---|---|
| **Stage 1**（PR#3889 daemon 雏形）| daemon 内 `qwen --acp` child + HTTP↔stdio 桥接 | ✅ MERGED 2026-05-13 |
| **Wave 1**（protocol foundation）| capability registry / DaemonSessionClient / typed event schema / 三套来源 lockstep | ✅ 4/4 MERGED |
| **Wave 2**（session lifecycle）| sessionScope override / load / resume / clientId stamping / scoped permission | ✅ 4/4 MERGED |
| **Wave 2.5**（reliability）| heartbeat / Last-Event-ID replay / slow_client_warning / session metadata + close-delete | ✅ 3/3 MERGED |
| **Wave 3**（read-only control plane）| status routes / preflight + env diagnostics / MCP guardrails + budget push | ✅ 3/3 MERGED |
| **Wave 4**（auth-gated mutation）| mutation gate / memory&agents CRUD / approval+tools+init / FS boundary / file r/w / OAuth device-flow | ✅ 7/7 MERGED |
| **Wave 5**（architecture extraction）| bridge primitives / MCP shared pool / PermissionMediator / output sinks / web client + render-core extraction | 🟢 22a + 22b/1 + 22b/2 design ✅ / 22b/3 mechanical 待开 |
| **Wave 6**（release hardening + v0.16）| docs / metrics / changelog / RC / GA | 🚧 待启动 |

**业务逻辑 100% 同源**——daemon 复用 ACP zod schema 与 `Session.handleXxx`，HTTP 仅是传输层桥接。Wave 5 PR 22 系列剥离桥接 primitives 后，未来 Stage 2 native in-process（直接 import `QwenAgent`，去 `qwen --acp` child）只是另一种 transport，wire 协议不变。

---

下一篇：[04 — Deployment & Client →](./04-deployment-and-client.md)
