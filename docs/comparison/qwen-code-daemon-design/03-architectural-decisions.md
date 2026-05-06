# 03 — 6 个架构决策

> [← 上一篇：现有资产盘点](./02-existing-assets.md) · [下一篇：HTTP API 设计 →](./04-http-api.md)

> [SDK / ACP / Daemon 架构 Deep-Dive §七.3](../sdk-acp-daemon-architecture-deep-dive.md#73-真正的难点架构决策) 列出 6 个"真正的难点是几个架构决策——而不是代码量"。本文为每个决策点给出明确选择 + 理由。

## 1. session 是否跨 client 共享

**问题**：用户在手机微信上发了一条消息让 agent 跑研究，回到电脑想继续——同一个 session 还是新 session？多个 client（CLI + VSCode + WebUI）同时打开同一个项目，互相能看到对方的 prompt 吗？

### 选择

**默认跨 client 共享**——`daemon.sessionScope: 'single'`（同 workspace 全局共享一个 session）。多租户企业部署可切到 `'thread'` 严格隔离。

| settings | 行为 | 适用场景 |
|---|---|---|
| **`daemon.sessionScope: 'single'`（默认）** | **同 workspace 多 client 共享同一 session** | **单用户多 client（CLI + IDE + Web 同时跑）** |
| `daemon.sessionScope: 'user'` | 同 user-id 跨 channel 共享 | 手机/电脑续行（含 IM channel）|
| `daemon.sessionScope: 'thread'` | 每 HTTP request 独立 session | 多租户企业 daemon、严格隔离 |

### 共享 session 的具体语义

多 client 接入同一 session 时：

| 操作 | 行为 |
|---|---|
| Client A 发 prompt（POST /session/:id/prompt）| Client B 通过 SSE 看到完整事件流（message_part / tool_call / tool_result）|
| Client B 同时也想发 prompt | **同 session 串行**——B 的请求挂起等 A 完成（决策 §6）|
| Client A 等待 permission（SSE permission_request）| **任何 client（A 或 B）都能 POST /permission/:requestId 应答** |
| Client A 关闭浏览器 / SDK 退出 | Session 不影响（daemon 进程内仍存活）；其他 client 继续观察 |
| Client B 通过 LoadSession 加载历史 | 从 SQLite/JSONL transcript 重建（含跑过的 tool 调用）|

这是 **"live collaboration" 模型** —— 与 Google Docs 多人编辑一个文档同构。

### 理由

1. **匹配单用户多 client 的真实场景**：典型 Qwen 用户同时开着 CLI + VSCode + 手机微信，都在同一项目工作 —— 共享 session 让所有视图实时同步是更直觉的默认
2. **复用 Channels 已有的 3 种 scope**：`SessionRouter.routingKey()` 已实现 `single/user/thread` 三档
3. **PR#3739 transcript-first fork resume 加成**：一个 session 中断后，任意 client 能 LoadSession 重建并从断点继续
4. **跨 client审批解锁桌面 UX**：CLI 跑命令时弹出权限请求，用户可以在更舒适的 WebUI 上点"批准"——不被 CLI 的 TUI 困住

### 安全 / 隔离边界

**`single` 默认下的隔离层级**：
- ✓ 跨 workspace 隔离（workspace A 的 client 看不到 workspace B 的 session）
- ✓ 跨 daemon 实例隔离（不同 daemon 进程互不可见）
- ⚠️ 同 workspace 跨 client **能互相看见** —— 这是有意设计，不是 bug

**多租户场景必须切到 `thread`**：
```json
{
  "daemon": {
    "sessionScope": "thread",  // 严格隔离
    "auth": {
      "tokens": [
        { "id": "tok-alice", "userId": "alice" },
        { "id": "tok-bob",   "userId": "bob" }
      ]
    }
  }
}
```

### 实现要点

```ts
// daemon settings
{
  "daemon": {
    "sessionScope": "single",                     // 默认 single（共享）
    "perChannelScope": {                          // 不同 channel 用不同 scope
      "http": "single",                            //   SDK / Web UI / IDE 都默认共享
      "vscode": "single",                          //   VSCode workspace 共享
      "telegram": "user",                          //   IM 用户视角共享
      "enterprise": "thread"                       //   多租户企业部署严格隔离
    }
  }
}
```

```ts
// SessionRouter routing key（复用现有逻辑）
single: `${channelName}:__single__`               // 同 channel 共享一个
user:   `${channelName}:${userId}:${workspaceId}` // 同 user 同 workspace 共享
thread: `${channelName}:${requestId}`             // 每请求独立
```

### Client 怎么发现已存在的 session

```http
# 选项 A：明确指定 session ID
POST /session/sess-existing-id/prompt
{ "prompt": [...] }
→ 200 OK

# 选项 B：列举 workspace 内所有 session，让用户选
GET /workspace/:id/sessions
→ 200 OK
{ "sessions": [{ "id": "sess-xxx", "lastActivity": ..., "title": "..." }] }

# 选项 C：自动 attach 到 default session（single scope 下）
POST /session
{ "meta": { "workspaceId": "ws-a", "scope": "single" } }
→ 200 OK
{ "sessionId": "sess-xxx", "attached": true }   // attached=true 表示复用已存在
```

SDK 客户端默认走 C —— 用户感受到的就是"同 workspace 自动共享"，无需手动管理 session ID。

---

## 2. 状态进程模型

**问题**：所有 session 都跑在 daemon 主进程？还是 daemon 路由到子进程，每 session 一个？

### 决策（最终）

**单 daemon 进程承载全部 session**。**不**走 "daemon 路由到子进程" 的方案。

### 决策依据

1. **OpenCode 已经在生产上验证此模式可行** —— `Map<directory, InstanceContext>` + Effect-TS `LocalContext` + SQLite 持久化兜底
2. **跨 session 资源共享是关键收益** —— LSP server / MCP server pool / Provider registry / Skill registry 全部在 daemon 进程内单例共享，per-session 子进程方案这些都要重新设计 IPC
3. **决策 §1 跨 client 共享 session 与单进程模型天然契合** —— fan-out 事件分发 + 任意 client 应答 permission 都依赖共享内存
4. **Node fork 在生产环境并不便宜** —— V8 heap 不能 fork，每个子进程要重新跑 module 加载 + 初始化（典型 Qwen Code 启动 1-3s），N 个 session = N × 这个开销
5. **应用层隔离机制充分** —— `AsyncLocalStorage` 跨 await 自动隔离 + `Instance.directory` 显式取值 + 子进程 spawn 显式传 cwd（详见 [05-进程模型](./05-process-model.md)）

### 拒绝多进程模型的具体理由

| 多进程方案的"优点" | 反驳 |
|---|---|
| "进程级隔离，单 session 崩溃不影响他人" | core 内未捕获异常导致整 daemon 崩溃的概率，与单 session 漏掉 await 链中错误的概率差不多——靠应用层 hardening（详尽 try/catch + crash-recovery）解决 |
| "OOM 隔离" | 单 session 跑爆 LLM 上下文导致内存膨胀的场景，应用层有 microcompact / context overflow 保护（PR#3735 OPEN）—— OOM 是异常路径，不应为此付永久启动开销 |
| "CPU 隔离" | Node 单线程模型下 CPU 隔离本来就要靠 worker_threads；session 间事件循环时间片本来就不公平共享。要真做 CPU 隔离，正确方案是 worker pool 而不是 child_process |

### 必要的工程约束

为了让单进程模型稳定运行，必须严格满足以下约束（落地时硬性要求）：

| 约束 | 验证手段 |
|---|---|
| daemon 主线程**永不**调用 `process.chdir()` | CI grep audit + 落地后 boundary test |
| daemon 主线程**永不**调用 sync I/O 在 hot path（PR#3581 已修） | 沿用 PR#3581 的 tracer 脚本作回归 |
| 所有 session-state 走 `AsyncLocalStorage` 显式传播，不走 module-level 全局变量 | 静态分析 + code review |
| 关键状态都有 SQLite/JSONL 持久化（重启可恢复）| PR#3739 transcript-first fork resume 已具备 |
| 未捕获异常**只能**杀掉 affected session 而不是整 daemon | top-level uncaughtException + per-session AbortController |

### 实现要点

- Node `AsyncLocalStorage`（Qwen 已有等价物 `LocalContext`，在 PR#3707 OPEN 引入 per-agent ContentGenerator 时也用过）
- session 状态写入 SQLite（permission decisions）+ JSONL（transcript，Qwen 现有 SessionService）
- daemon 顶层 `process.on('uncaughtException')` 只 log + 通知 affected session 的 client，不退进程
- Health check 路由 `/health` 返回内存 / session 数 / 长跑请求等指标，便于运维识别异常 daemon

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

**问题**：两个 client 同时连同一个 session（决策 §1 默认共享）—— 谁能发 prompt？事件流怎么分发？

### 选择

**同 session 串行 prompt（FIFO 队列）+ 多 client 同时观察事件流（fan-out SSE/WS）+ 跨 session 并行**。

### 多 client 事件分发模型

```
Client A → POST /session/:id/prompt    "请重构 src/foo.ts"
Client B → GET /session/:id/events     (SSE 已订阅)
Client C → GET /session/:id/events     (SSE 已订阅)

daemon:
  ├─ Session.handlePrompt(req from A) 启动
  └─ SessionNotification stream
      ├─ A 走 POST 的 SSE response stream
      ├─ B 走 GET /events 的 SSE stream    ← fan-out
      └─ C 走 GET /events 的 SSE stream    ← fan-out

  → A/B/C 都看到完整事件流：message_part / tool_call / tool_result / permission_request
```

实现：每个 Session 维护 `Set<ClientSubscription>`，notification 时 broadcast 到所有订阅者。

### 谁能发 prompt？谁能审批权限？

| 操作 | 谁能做 | 冲突处理 |
|---|---|---|
| **发 prompt** | 任何 client | 同 session 串行 FIFO，第二个挂起等 |
| **审批 permission_request** | **任何 client（first responder wins）** | A 触发 permission_request → B 抢先 POST /permission/:id 应答 → daemon 接受 B 的应答，A/C 收到通知 "permission resolved by another client" |
| **取消** | 任何 client | POST /session/:id/cancel —— 取消当前 active prompt |
| **设置 model / mode** | 任何 client | 立即生效，所有 client 收到 SessionNotification |

### 理由

| 选项 | 适用 |
|---|---|
| **A：同 session 串行 prompt + fan-out 事件（本设计）** | 与 ACP 协议天然契合（一次只能有一个 active prompt）；多 client 协作场景（用户跨设备 / IDE+CLI）天然支持 |
| B：同 session 并行 prompt | 复杂——LLM 调用 / 工具调用并行化、FileReadCache / context state 都要重新设计同步；几乎没有实际收益（多用户在同一 conversation 中并发对话本身就是混乱的）|

ACP 协议本身就是"client → agent → 同步 response"语义，不允许同 session 并发 prompt。daemon 跟随这个约束 + 加上事件 fan-out 实现"多 client 协作观察"。

### 实现要点

```ts
class Session {
  private subscribers: Set<ClientSubscription> = new Set()
  private taskQueue: Promise<void> = Promise.resolve()
  
  subscribe(sub: ClientSubscription): () => void {
    this.subscribers.add(sub)
    return () => this.subscribers.delete(sub)
  }
  
  async handlePrompt(req: PromptRequest, originatingClient: ClientId) {
    // 同 session FIFO（第二个 prompt 挂起等）
    return this.taskQueue = this.taskQueue.then(() => this.doPrompt(req, originatingClient))
  }
  
  private notify(event: SessionNotification) {
    // fan-out 给所有订阅者（包括 originating client 和 observer client）
    for (const sub of this.subscribers) {
      sub.send(event)
    }
  }
}

class PermissionRequestHandler {
  async waitForResponse(requestId: string): Promise<PermissionResponse> {
    return new Promise((resolve, reject) => {
      // 任何 client POST /permission/:id 都能 resolve
      this.pending.set(requestId, { resolve, reject })
      // first responder wins
    })
  }
}
```

### 多 client 体验

| 场景 | 行为 |
|---|---|
| 用户在 CLI 发 prompt，同时打开 WebUI 观察 | WebUI 实时看到 message_part 流 + tool_call + tool_result |
| Agent 跑到 Bash 工具弹 permission，CLI 用户去喝咖啡了 | WebUI 用户能直接在浏览器点"批准"——不需要回到 CLI |
| Client A 发 prompt 跑到一半，Client B 想发新 prompt | B 的 HTTP request 挂起；B 也可以选择 POST /cancel 终止 A 的 prompt 后发自己的 |
| 用户从手机微信切到电脑 SDK 续行 | 手机端的 SubAgent 在后台继续跑，电脑端 LoadSession + 实时观察后台进度 |

---

## 决策矩阵汇总

| # | 决策 | 选择 | 关键依据 PR / 工具 |
|---|---|---|---|
| 1 | session 跨 client 共享 | **默认 single（共享）**，可切 user / thread | Channels SessionRouter scope 系统 |
| 2 | 状态进程模型 | 单 daemon 进程承载全部 session | 与 OpenCode 一致 + Qwen LocalContext / `AsyncLocalStorage` |
| 3 | MCP server 生命周期 | daemon 内 pool 跨 session 复用 + per-server fallback | PR#3818 coalesce |
| 4 | FileReadCache 共享 | session 内私有（保守起步）| PR#3717 + PR#3810 invalidation fragility |
| 5 | Permission flow | 复用 PR#3723 + daemon 第 4 mode + SSE permission_request | PR#3723 evaluatePermissionFlow() |
| 6 | 多 client 并发 | **同 session prompt 串行 + 事件 fan-out 多 client + 任何 client 可应答 permission** | ACP 协议语义 + Session task queue + subscriber set |

---

下一篇：[04-HTTP API 设计 →](./04-http-api.md)
