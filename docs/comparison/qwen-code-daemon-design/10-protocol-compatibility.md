# 10 — SDK / ACP 协议兼容性（单进程 vs Daemon）

> [← 上一篇：与 OpenCode 详细对比](./09-comparison-with-opencode.md) · [下一篇：多租户与沙箱 →](./11-multi-tenancy-and-sandbox.md)

> 单进程模式（当前 `qwen --acp` stdio NDJSON）与 Daemon 模式（设计中 `qwen serve` HTTP）的协议兼容性分析。**结论：Schema 层完全兼容、Wire 层不兼容、SDK 抽象层用户代码 0 改动**。

## 一、TL;DR — 4 层兼容性矩阵

| 层 | 单进程模式 | Daemon 模式 | 兼容性 |
|---|---|---|---|
| **Schema 层** | ACP zod schema（`@agentclientprotocol/sdk`）| **复用同一组 ACP zod schema** | ✅ **100% 兼容** |
| **业务逻辑层** | `Session.handleXxx()` in-process（CLI 子进程内）| **同样的 `Session.handleXxx()`**（daemon 内 in-process）| ✅ **100% 兼容**（HttpAcpAdapter 调用同样函数）|
| **SDK 抽象层** | `ProcessTransport implements Transport` | `HttpTransport implements Transport` | ✅ **接口兼容**（用户代码 0 改动）|
| **Wire 层** | stdin/stdout NDJSON | HTTP body / SSE / WebSocket | ❌ **不兼容**（字节格式根本不同，但被 Transport 抽象层屏蔽）|

## 二、每个 ACP RPC 的兼容性详解

### 2.1 完整 RPC 映射表

| ACP RPC | stdio 模式 | HTTP daemon 模式 | Body 兼容 | 流程兼容 |
|---|---|---|:---:|:---:|
| `initialize` | NDJSON 首次握手 | 改为 `/authenticate` + workspace 注册 | ✅ | ⚠️ 不同 bootstrap |
| `newSession` | NDJSON request | `POST /session` | ✅ | ✅ |
| `prompt` | NDJSON request | `POST /session/:id/prompt` | ✅ | ✅ |
| `cancel` | NDJSON notification | `POST /session/:id/cancel` | ✅ | ✅ |
| `setSessionModel` | NDJSON request | `POST /session/:id/model` | ✅ | ✅ |
| `loadSession` | NDJSON request | `POST /session/:id/load` | ✅ | ✅ |
| `listSessions` | NDJSON request | `GET /session` | ✅ | ✅ |
| `setSessionMode` | NDJSON request | `POST /session/:id/mode` | ✅ | ✅ |
| `setSessionConfigOption` | NDJSON request | `POST /session/:id/config` | ✅ | ✅ |
| Session notifications（`message_part` / `tool_call` / `tool_result`）| NDJSON 流 | SSE / WebSocket 流 | ✅ | ✅ wire 不同但语义同 |
| **`permission_request`（agent → client）** | NDJSON 推 + 等下条 NDJSON 响应 | SSE 推 + **单独** `POST /permission/:requestId` | ✅ body | ⚠️ **同步→异步** |
| **`read_text_file` / `write_text_file`（client capability）** | NDJSON 双向（agent 调 client）| 需 SSE 推 + client 的 callback HTTP endpoint | ✅ body | ⚠️ **更复杂** |

### 2.2 Body 兼容 = 100%

所有 ACP RPC 的请求/响应 body 都是 `@agentclientprotocol/sdk` 已经导出的 zod schema：

```ts
// 同一份 schema 两种模式都用
import {
  PromptRequest,         // body schema
  PromptResponse,        // response schema
  CancelNotification,    // notification schema
  SessionNotification,   // streaming event schema
  ...
} from '@agentclientprotocol/sdk'

// stdio 模式: NDJSON 帧的 JSON.parse 出来直接是这些类型
// HTTP 模式: HTTP body 的 JSON.parse 出来也是这些类型
```

**协议设计上的关键决定**（[01 §2.2](./01-overview.md#22-qwen-独有的-3-条特色)）：daemon 路由 body 直接复用 ACP zod schema，**不自创新 schema**——这是 schema 100% 兼容的工程基础。

## 三、核心不兼容点：双向 RPC 的不对称

### 3.1 ACP 协议本质是双向 RPC

```
                     Agent
                       ↑↓
           bidirectional ACP NDJSON
                       ↑↓
                     Client

Client → Agent 方向（最常见）:
  - newSession / prompt / cancel / setSessionModel / ...

Agent → Client 方向（client capabilities）:
  - permission_request（永远都有，需要客户端审批）
  - read_text_file（如果 client 声明 fs.readTextFile capability）
  - write_text_file（同上）
  - call_tool_in_client（少见，client-side tools）
```

### 3.2 stdio 模式的对称性

```
stdio:
─────────────────────────────────────────────────────
   Agent  ←—————— pipe ——————→  Client

   双向都用同一个 NDJSON pipe:
   - Agent 写 stdout → Client 从 stdin 读
   - Client 写 stdin → Agent 从 stdout 读
   
   permission_request 流:
   1. Agent 写 NDJSON: { method: 'permission_request', id: 42, params: {...} }
   2. Agent 阻塞 await pipe.read()
   3. Client 接收 → 弹 UI → 用户决定 → 写 NDJSON: { id: 42, result: { allow: true } }
   4. Agent 读到响应，继续执行
```

**关键**：stdio NDJSON pipe 是**双向同步**的，agent 可以在任何时刻写请求并阻塞等响应。

### 3.3 HTTP 模式的不对称

```
HTTP:
─────────────────────────────────────────────────────
   Client ─── HTTP request ───→  Agent  (request 单向)
          ←── SSE/WS event ────  Agent  (notification 单向)

   permission_request 流:
   1. Agent 想发请求给 Client，但没有"反向 HTTP"机制
   2. Agent 通过 SSE 推 event: data: { type: 'permission_request', requestId: 'r1', ... }
   3. Agent 把 r1 加入 pendingRequests Map，await 一个 Promise
   4. Client 收到 SSE event → 弹 UI → 用户决定
   5. Client 单独发 HTTP: POST /permission/r1 { allow: true }
   6. Agent 的 HTTP handler 找到 pendingRequests.get('r1').resolve({ allow: true })
   7. 原 Promise resolve，agent 继续
```

**关键**：HTTP 协议本身**单向**（请求→响应），所以 agent → client 的 RPC 必须**拆成两次单向交互**（SSE 推 + 单独 POST）。这是协议层面的根本差异。

### 3.4 实际影响

| 场景 | stdio 模式 | HTTP 模式 |
|---|---|---|
| 模型调 Bash 触发 permission | agent 写 NDJSON → 阻塞读下条 | agent 发 SSE event → 异步等 `POST /permission/:id` |
| 实现复杂度 | 直接 `await pipe.read()` | 需要 `pendingRequests Map<requestId, { resolve, reject }>` + 60s 超时 |
| 失败模式 | pipe 断了 = 进程死了 = clear 故障 | client 不应答 → 60s 超时 → 默认 deny + log warning |
| 用户代码改动 | — | SDK 帮你藏在 `query.on('permission_request', ...)` 回调下 |

## 四、SDK 抽象层让用户代码 0 改动

### 4.1 现有 Transport 接口（已设计）

`packages/sdk-typescript/src/transport/Transport.ts`：

```ts
export interface Transport {
  close(): Promise<void>
  waitForExit(): Promise<void>
  write(message: string): void              // ← 写入 NDJSON 帧
  readMessages(): AsyncGenerator<unknown>   // ← 读出 NDJSON 帧
  readonly isReady: boolean
  readonly exitError: Error | null
}
```

**注释明确预告**：

> - `ProcessTransport`: Local subprocess via stdin/stdout (initial implementation)
> - `HttpTransport`: Remote CLI via HTTP (future)
> - `WebSocketTransport`: Remote CLI via WebSocket (future)

### 4.2 ProcessTransport（已实现）

```ts
// 现状：spawn 子进程 + 读写 stdin/stdout
class ProcessTransport implements Transport {
  private childProcess: ChildProcess
  
  write(message: string) {
    this.childStdin.write(message + '\n')   // NDJSON 帧
  }
  
  async *readMessages() {
    for await (const line of readlines(this.childStdout)) {
      yield JSON.parse(line)
    }
  }
}
```

### 4.3 HttpTransport（设计中）

```ts
// HTTP 实现：把 NDJSON 帧映射成 HTTP/SSE 调用
class HttpTransport implements Transport {
  private sse: EventSource
  private pendingRequests = new Map<number, { resolve, reject }>()
  
  async write(message: string) {
    const msg = JSON.parse(message)  // ACP request 类型
    
    // 路由到对应 HTTP endpoint
    switch (msg.method) {
      case 'session/new':
        return this.fetch('POST', '/session', msg.params)
      case 'session/prompt':
        return this.fetch('POST', `/session/${msg.params.sessionId}/prompt`, msg.params)
      case 'session/cancel':
        return this.fetch('POST', `/session/${msg.params.sessionId}/cancel`, msg.params)
      case 'session/setModel':
        return this.fetch('POST', `/session/${msg.params.sessionId}/model`, msg.params)
      
      // permission response 走单独 HTTP route
      case 'permission/respond':
        return this.fetch('POST', `/permission/${msg.params.requestId}`, msg.params)
      
      // ...
    }
  }
  
  async *readMessages() {
    // SSE event stream → emit as NDJSON-shaped messages
    for await (const event of this.sseStream()) {
      yield JSON.parse(event.data)  // 与 NDJSON 同 shape 的 SessionNotification
    }
  }
}
```

### 4.4 用户视角：同一份代码两种 transport 都跑

```ts
import { query } from '@qwen-code/sdk'
import { ProcessTransport, HttpTransport } from '@qwen-code/sdk/transport'

// 切换 transport 是这一行的事
const transport = process.env.QWEN_DAEMON_URL
  ? new HttpTransport({
      baseUrl: process.env.QWEN_DAEMON_URL,
      bearerToken: process.env.QWEN_SERVER_TOKEN,
      workspaceId: 'my-project',
    })
  : new ProcessTransport({ executable: 'qwen' })

// 业务代码两边相同
const q = query({
  transport,
  prompt: '请重构 src/foo.ts',
  canUseTool: async (req) => {
    return await myCustomUI.confirm(`Allow ${req.tool}?`)
  },
})

for await (const msg of q) {
  if (isAssistantMessage(msg)) {
    console.log(msg.content)
  }
}
```

**用户代码 0 改动**——SDK 封装下两种模式行为一致。

## 五、3 个 Stage 的兼容性演进

| Stage | 实现方式 | 与 stdio 兼容性 |
|---|---|---|
| **Stage 1**（`--http-bridge` flag）| daemon spawn 现有 ACP agent 子进程 + HTTP↔stdio 桥接 | **业务逻辑 100% 同源** —— 实际就是同一个 ACP agent，仅外面包了层 HTTP 翻译 |
| **Stage 2**（原生 daemon）| daemon 内 in-process Session + HttpAcpAdapter 翻译 | **业务逻辑同源** —— `Session.handleXxx()` 复用 ACP agent 调用的同样代码路径 |
| **Stage 3**（对标 OpenCode 完整设计）| 同上 + workspace router + mDNS + OpenAPI | 同 Stage 2，加企业能力（不影响 SDK 兼容性）|

**Stage 1 是最强兼容性保证**——daemon 进程内的 ACP agent 子进程**没有任何改动**，所以行为绝对一致。

```
Stage 1 拓扑:

SDK Client → HTTP → daemon → spawn → ACP agent 子进程 (无改动)
                ↑               ↓
                ←── HTTP ──     stdio NDJSON
                              ↑
                       同一个 ACP agent 实现
                       (与 qwen --acp 一致)
```

Stage 2 拓扑：

```
SDK Client → HTTP → daemon (in-process)
                     ├─ HttpAcpAdapter
                     └─ Session.handleXxx() in-process
                        (与 ACP agent 的 Session.handleXxx() 完全相同函数)
```

## 六、用户感知的差异（即使 SDK 抽象都藏好了）

业务逻辑兼容不代表用户感受一致。daemon 模式下用户会注意到：

| 维度 | stdio 模式 | HTTP daemon 模式 |
|---|---|---|
| 启动延迟 | 每次 `query()` ~1-3s（spawn + core 加载）| 首次 ~1-3s，后续 ~10ms |
| 多 client 并发 | ❌ 一次只能一个（stdio pipe 不能 fan-out）| ✅ 默认支持（决策 §1 跨 client 共享 session）|
| 中断性 | Ctrl+C SDK 进程也杀 daemon | Ctrl+C SDK 进程，daemon session 继续跑 |
| 权限审批 UX | TUI dialog（同步）| SSE event + 任意 client 应答（决策 §6 fan-out + first responder）|
| 资源（LSP/MCP）| 每次 spawn 重新加载 | 跨 query 复用（决策 §3 per-workspace MCP 共享）|
| 故障半径 | 一个 query 崩溃只死自己 | 一个 session 崩溃可能影响其他 session（共进程 — 决策 §2）|
| Working directory | 子进程 spawn 时 OS 级 cwd | AsyncLocalStorage 应用层 cwd（[05-进程模型](./05-process-model.md)）|

## 七、不兼容点的 Adapter 责任

`HttpAcpAdapter`（在 Stage 2 daemon 内部）需要处理 5 件事：

| 不兼容点 | Adapter 责任 |
|---|---|
| HTTP body ↔ ACP request | 用 zod schema 校验 + 字段映射 |
| SSE event ↔ ACP notification | wrapper 把 SessionNotification → SSE `data:` 帧 |
| `permission_request` 同步→异步 | `pendingRequests Map<id, resolver>` + 60s 超时 + 60s 默认 deny + log |
| Client capabilities (`read_text_file` 等) | client 需注册 callback URL，agent 发 SSE 调 client，client 调 callback HTTP |
| Connection 生命周期 | HTTP keep-alive vs process exit；daemon 重启后 SSE auto-reconnect |

### 7.1 Adapter 关键代码示意

```ts
// daemon 内 HttpAcpAdapter
class HttpAcpAdapter {
  private session: Session  // 复用现有 ACP Session 实现
  private pendingPermissions = new Map<string, PromiseResolver>()
  private sseSubscribers = new Set<SseStream>()
  
  // HTTP request 进入
  async handlePromptRequest(req: PromptRequest, originatingClient: ClientId) {
    // 调用与 stdio ACP 完全相同的函数
    return this.session.handlePrompt(req)
  }
  
  // session 发出 SessionNotification（无论触发源）
  onSessionNotification(notif: SessionNotification) {
    if (notif.type === 'permission_request') {
      const requestId = notif.requestId
      // 转 SSE 推给所有订阅者
      this.broadcastSse({ type: 'permission_request', requestId, ... })
      // 等任意 client 通过 POST /permission/:id 应答
      return new Promise((resolve) => {
        this.pendingPermissions.set(requestId, resolve)
        setTimeout(() => {
          if (this.pendingPermissions.has(requestId)) {
            this.pendingPermissions.delete(requestId)
            resolve({ allow: false })  // 60s 超时默认 deny
          }
        }, 60_000)
      })
    } else {
      // 普通 notification 直接 fan-out
      this.broadcastSse(notif)
    }
  }
  
  // POST /permission/:id 入口
  handlePermissionResponse(requestId: string, response: PermissionResponse) {
    const resolver = this.pendingPermissions.get(requestId)
    if (resolver) {
      this.pendingPermissions.delete(requestId)
      resolver(response)
      // 通知其他 client "permission resolved by another client"
      this.broadcastSse({ type: 'permission_resolved', requestId, by: response.respondedBy })
    }
  }
}
```

## 八、向后兼容承诺

设计落地时的兼容性承诺：

| 承诺 | 说明 |
|---|---|
| **stdio ACP 模式不弃用** | 始终保持作为 reference impl + IDE/Zed 集成默认方式 |
| **SDK Transport 接口不变** | 现有 ProcessTransport 用户代码不需改 |
| **新增 HttpTransport opt-in** | 用户主动 `new HttpTransport(...)` 才走 daemon 路径，不主动切的代码继续用 ProcessTransport |
| **业务行为应一致** | 同一个 prompt 在两种 mode 下结果应相同（除并发 / 多 client 等 daemon 独有特性）|
| **测试覆盖** | E2E 测试套件应在两种 transport 下都跑（防止业务逻辑分裂）|

## 九、典型 client 代码迁移路径

### 9.1 SDK 用户（最简单）

```ts
// 旧代码（stdio）
const q = query({ prompt: '...' })  // 默认用 ProcessTransport

// 新代码（daemon）：仅改一行
const q = query({
  prompt: '...',
  transport: new HttpTransport({ baseUrl: '...' }),
})
```

### 9.2 Web UI（packages/webui）

WebUI 已有 `ACPAdapter`（stdio）+ `JSONLAdapter`（reading transcripts）。daemon 化加 `HttpAcpAdapter`：

```ts
// 旧
const adapter = new ACPAdapter({ child: spawn('qwen', ['--acp']) })

// 新
const adapter = new HttpAcpAdapter({ baseUrl: 'http://localhost:5096' })

// 业务代码不变（adapter 接口相同）
adapter.onMessagePart((msg) => { ... })
adapter.send(promptRequest)
```

### 9.3 VSCode IDE companion

当前 `vscode-ide-companion` 自起 express server 给 IDE 用。daemon 推出后建议直接连 daemon：

```ts
// 旧：自起 express + 跑独立 ACP agent 子进程
this.ideServer = express()
this.acpAgent = spawn('qwen', ['--acp'])

// 新：直接连 daemon
const adapter = new HttpAcpAdapter({
  baseUrl: process.env.QWEN_DAEMON_URL ?? 'http://localhost:5096',
  workspaceId: this.detectWorkspaceId(),
})
```

VSCode 的 ide-server.ts 在 Stage 3 可考虑弃用（保留兼容期）。

### 9.4 IM Channels（Telegram / 微信 / 钉钉）

`packages/channels/base/src/AcpBridge.ts` 当前 spawn 子进程跑 ACP。daemon 化后可改为连 daemon HTTP：

```ts
// 旧
this.child = spawn(cliEntryPath, ['--acp'])
this.connection = new ClientSideConnection(...)

// 新
this.connection = new HttpAcpClientConnection({
  baseUrl: 'http://localhost:5096',
  channelName: 'telegram',  // 用于 daemon 端 SessionRouter 路由
})
```

Channels 的 `SessionRouter` 在 daemon 模式下能处理多 channel 路由（决策 §1）。

## 十、关键测试用例（验证两种 mode 兼容性）

落地时必须保证以下测试在两种 transport 下都通过：

| 测试 | stdio | HTTP daemon |
|---|---|---|
| simple prompt → assistant message | ✓ | ✓（应行为一致）|
| prompt → tool call → tool result → continue | ✓ | ✓ |
| prompt + permission_request → user allow → continue | ✓ | ✓（adapter 转换异步）|
| prompt + cancel mid-execution | ✓ | ✓ |
| LoadSession + replay transcript | ✓ | ✓ |
| setSessionModel during running prompt | ✓ | ✓ |
| Long-running prompt + reconnect | N/A（pipe 断 = die）| ✓（daemon 独有）|
| Multi-client observe same session | N/A（stdio 单 client）| ✓（daemon 独有）|
| Permission cross-client响应（A 触发，B 应答）| N/A | ✓（daemon 独有）|

**用户代码同一份**——CI 跑 matrix 测试覆盖两种 transport。

## 十一、一句话总结

**SDK / ACP 在两种模式下：**

- ✅ **Schema 层（zod 类型）100% 兼容** —— 同一组类型 import
- ✅ **业务语义层 100% 兼容** —— 同一组 `Session.handleXxx()` 函数被调用
- ✅ **SDK 抽象层用户代码 0 改动** —— Transport 接口屏蔽 wire 差异
- ❌ **Wire 层不兼容**（NDJSON vs HTTP+SSE）—— 但被 HttpTransport adapter 完全隐藏
- ⚠️ **双向 RPC 同步→异步是结构差异** —— adapter 层 `pendingRequests Map` + 60s 超时处理，用户感知不到

**Stage 1 是最强兼容性保证**——daemon 内部直接 spawn 现有 ACP agent 子进程，业务行为绝对一致；Stage 2/3 通过 HttpAcpAdapter 复用 `Session.handleXxx()` 同源函数，仍然保证业务一致。

---

[← 回到 README](./README.md)
