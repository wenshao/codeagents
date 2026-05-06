# 04 — HTTP API 设计

> [← 上一篇：6 个架构决策](./03-architectural-decisions.md) · [下一篇：进程模型 →](./05-process-model.md)

> daemon HTTP 路由的核心创新：**复用 ACP NDJSON 的 zod schema** —— body 结构与 `PromptRequest` / `NewSessionRequest` 等 ACP 类型 1:1 对应。

## 一、根路由总览

```
GET    /                                   服务端元信息
GET    /health                             健康检查（无认证）
POST   /authenticate                       (HTTP-only) bearer token 取换 long-lived token

# Session 生命周期（直接映射 ACP RPC）
POST   /session                            new session       ← NewSessionRequest
GET    /session                            list sessions     ← ListSessionsRequest
GET    /session/:id                        session info      ← (新加 schema)
POST   /session/:id/load                   load session      ← LoadSessionRequest
DELETE /session/:id                        archive / delete

# 与 session 交互
POST   /session/:id/prompt                 send prompt       ← PromptRequest
POST   /session/:id/cancel                 cancel current    ← CancelNotification
POST   /session/:id/model                  set model         ← SetSessionModelRequest
POST   /session/:id/mode                   set mode          ← SetSessionModeRequest
POST   /session/:id/config                 set config option ← SetSessionConfigOptionRequest

# 流式事件（核心 — daemon 与 stdio ACP 的唯一传输层差异）
GET    /session/:id/events                 SSE / WebSocket   ← SessionNotification[]
                                            (Upgrade: websocket 走 WS，否则 SSE)

# 权限审批（HTTP 异步流模式）
POST   /permission/:requestId              respond to permission_request

# Workspace 管理（多 workspace 路由）
GET    /workspace                          list workspaces
POST   /workspace                          register workspace  body: { directory }
DELETE /workspace/:id                      dispose workspace

# 工具能力查询
GET    /workspace/:id/skills               已加载 skill 列表
GET    /workspace/:id/mcp                  已连接 MCP server 列表
GET    /workspace/:id/lsp                  LSP server 状态

# 后台任务（PR#3471/3488/3642/3791/3836 4 kinds 暴露）
GET    /workspace/:id/tasks                list background tasks（agent / shell / monitor / dream）
POST   /workspace/:id/tasks/:taskId/cancel cancel task     ← task_stop tool 的 HTTP 入口

# 文件操作
GET    /workspace/:id/file?path=...        read file
POST   /workspace/:id/file                 write file (受 PR#3774 prior-read 守卫，需先 read)
POST   /workspace/:id/file/edit            edit file (同上)

# 终端 / Bash（PTY）
POST   /workspace/:id/pty                  open PTY (Upgrade: websocket)

# Skill 管理
POST   /workspace/:id/skill/reload         reload skill registry
```

## 二、请求 / 响应 schema 设计

### 核心原则：**复用 ACP zod schema**

Qwen Code 的 ACP agent（`packages/cli/src/acp-integration/acpAgent.ts`）已经导入 `@agentclientprotocol/sdk` 的所有 RequestType。**daemon 路由直接用同一组 zod schema 作为请求 body 校验**：

```ts
// daemon HTTP route handler
import {
  PromptRequest,         // 已有
  NewSessionRequest,     // 已有
  CancelNotification,    // 已有
  SetSessionModelRequest,// 已有
  ...
} from '@agentclientprotocol/sdk'

// 用 hono-zod-validator 做请求体校验
app.post('/session/:id/prompt',
  zValidator('json', PromptRequest),
  async (c) => {
    const req = c.req.valid('json')   // 已是 PromptRequest 类型
    const session = getSession(c.req.param('id'))
    const response = await session.handlePrompt(req)  // 复用现有 ACP 逻辑
    return c.json(response)            // PromptResponse
  }
)
```

**意义**：协议 schema 0 设计成本——与 ACP agent 共用一份 zod schema，daemon route handler 与 ACP `Session.handleXxx()` 共用同一组业务函数。

### Daemon 特有的扩展字段

少数 HTTP 特有字段需要新增 schema：

```ts
// 新增 schema（daemon 特有）
const DaemonSessionMeta = z.object({
  workspaceId: z.string(),                // 多 workspace 路由
  cwd: z.string().optional(),              // 显式 cwd（覆盖 workspace 默认）
  clientId: z.string().optional(),         // 多 client 标识
  scope: z.enum(['thread', 'single', 'user']).optional(),
})

const DaemonNewSessionRequest = NewSessionRequest.extend({
  meta: DaemonSessionMeta,
})
```

## 三、SSE / WebSocket 事件流（核心）

### 选择：默认 SSE，按 client 升级到 WebSocket

```
GET /session/:id/events
Accept: text/event-stream         → 用 SSE
Upgrade: websocket                 → 用 WebSocket
```

**SSE 优势**：HTTP/2 友好、自动重连（client 用 EventSource API）、防火墙透明。
**WebSocket 优势**：双向通信（permission response / interrupt 可同 channel 发回，免单独 POST 路由）。

### 事件 schema 复用 ACP `SessionNotification`

```ts
// SessionNotification 是 ACP 的现成类型
export interface SessionNotification {
  type: 'message_part' | 'tool_call' | 'tool_result' | 'permission_request' |
        'task_progress' | 'subagent_event' | ...
  ...
}

// SSE 帧
data: {"type":"message_part","content":"..."}\n\n
data: {"type":"tool_call","name":"Bash","args":{...}}\n\n
data: {"type":"permission_request","requestId":"abc","tool":"Bash","args":{...}}\n\n
```

### Permission request 的双向交互

```
client → daemon: POST /session/:id/prompt
daemon → client: SSE { type: 'tool_call', name: 'Bash', ... }
                 SSE { type: 'permission_request', requestId: 'r1', ... }
                 (HTTP request 挂起等 client 响应)

client → daemon: POST /permission/r1  body: { allow: true, alwaysAllow: false }
daemon → client: SSE { type: 'tool_result', ... }
                 SSE { type: 'message_part', content: '...' }
                 (response body 是 PromptResponse)
```

## 四、典型请求/响应示例

### 4.1 创建 session + 发 prompt

```http
POST /workspace HTTP/1.1
Authorization: Bearer xxx
Content-Type: application/json

{ "directory": "/work/my-project" }

→ 200 OK
{ "workspaceId": "ws-abc123" }
```

```http
POST /session HTTP/1.1
Authorization: Bearer xxx
Content-Type: application/json

{
  "meta": { "workspaceId": "ws-abc123" },
  "clientCapabilities": { "fs": { "readTextFile": true } },
  "mcpServers": [...]
}

→ 200 OK (NewSessionResponse)
{ "sessionId": "sess-xyz" }
```

```http
POST /session/sess-xyz/prompt HTTP/1.1
Authorization: Bearer xxx
Content-Type: application/json

{ "prompt": [{ "type": "text", "text": "请重构这个函数" }] }

(同时 client 打开 GET /session/sess-xyz/events SSE 监听)

→ 200 OK (PromptResponse) — 等待中，事件流持续推送

← SSE event_stream 同时推送中:
data: {"type":"message_part","content":"我来帮..."}

data: {"type":"tool_call","name":"ReadFile","args":{"path":"src/foo.ts"}}

data: {"type":"tool_result","name":"ReadFile","output":"..."}

...

(最后)
→ 200 OK 返回 PromptResponse
{ "stopReason": "end_turn", "tokenUsage": {...} }
```

### 4.2 加载历史 session

```http
POST /session/sess-yesterday/load HTTP/1.1

(无 body，或带 maxMessages 等过滤)

→ 200 OK (LoadSessionResponse)
{
  "messages": [...],          // transcript replay
  "currentMode": "edit",
  "currentModel": "qwen3-max",
  "tasks": [...]              // 4 kinds (agent/shell/monitor/dream) running
}
```

### 4.3 多 client 跨设备续行

```
[手机微信]: 通过 channels/weixin → SessionRouter → session sess-foo
            scope='user', user-id=u123

[电脑 SDK]:
POST /session HTTP/1.1
{ "meta": { "workspaceId": "...", "scope": "user", "userId": "u123" } }

  daemon SessionRouter.routingKey('http', 'u123', 'main', undefined)
  = "http:u123:main"
  
  匹配到现有 session sess-foo（如果已注册 user-id u123）

→ 200 OK
{ "sessionId": "sess-foo" }   // ← 同一 session ID

GET /session/sess-foo/events （SSE 接入）
client 现在能看到手机端正在跑的 background task
```

## 五、错误码与状态码

| HTTP code | 含义 | 对应 ACP error code |
|---|---|---|
| 401 | bearer token 缺失/错误 | — |
| 403 | workspace 越权 / permission denied | — |
| 404 | session/workspace not found | `errorCodes.SESSION_NOT_FOUND` |
| 409 | 同 session 已有 active prompt（多 client 并发冲突）| 新增 `SESSION_BUSY` |
| 422 | request body schema 校验失败 | — |
| 429 | rate limit | — |
| 500 | core internal error | `errorCodes.INTERNAL_ERROR` |
| 504 | LLM upstream timeout | `errorCodes.UPSTREAM_TIMEOUT` |

`packages/cli/src/acp-integration/errorCodes.ts` 已定义 ACP 错误码，daemon 加 HTTP code 映射即可。

## 六、OpenAPI 自动生成

参考 OpenCode 的 `hono-openapi` 模式，从 zod schema 自动生成 OpenAPI 3.0 spec：

```ts
// server.ts
import { generateSpecs } from 'hono-openapi'

app.get('/openapi.json', (c) => {
  return c.json(generateSpecs(app))
})
```

SDK 客户端可以从 `/openapi.json` codegen 出 typed HTTP client（参考 OpenCode `@opencode-ai/sdk` 的做法）——但 Qwen 也可以选**手写 SDK 客户端**（更精准控制，复用 ACP zod 类型），不强制 codegen。

## 七、版本与向后兼容

```
GET / HTTP/1.1
→ 200 OK
{
  "qwen": "0.16.0",              // qwen-code package version
  "daemon": "1",                  // daemon API major version
  "acp": "0.14",                  // ACP protocol version (ACP_PROTOCOL_VERSION)
  "capabilities": {
    "websocket": true,
    "sse": true,
    "openapi": true
  }
}
```

- **daemon API 版本独立于 qwen 包版本** —— 允许 qwen 包升级时不破坏 SDK 客户端
- **ACP 协议版本透传** —— 与底层 ACP 库版本一致（当前 0.14）

---

下一篇：[05-进程模型 →](./05-process-model.md)
