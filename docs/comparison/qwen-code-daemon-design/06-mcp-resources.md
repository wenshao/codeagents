# 06 — MCP / FileReadCache / LSP 资源共享

> [← 上一篇：进程模型](./05-process-model.md) · [下一篇：权限 / 认证 →](./07-permission-auth.md)

> daemon 模式下"哪些资源跨 session 共享、哪些隔离"是性能与正确性的关键平衡。

## 1. MCP server 共享策略

### 1.1 决策回顾（[03 §3](./03-architectural-decisions.md#3-mcp-server-生命周期)）

**per-workspace MCP state**（与 OpenCode `packages/opencode/src/mcp/index.ts` 模式一致）—— 每 workspace 持有自己的一套 MCP client 集，**不跨 workspace 共享**。同 workspace 内的多 session 共享同一组 MCP client。

### 1.2 与 OpenCode 一致的 4 条工程实践

直接借鉴 OpenCode 的成熟设计（参考 `packages/opencode/src/mcp/index.ts` 917 行）：

| 实践 | OpenCode 实现 | Qwen daemon 复制 |
|---|---|---|
| Lazy 初始化 | `InstanceState.make<State>(...)` 第一次访问 workspace 才启动 MCP | 同——Workspace.start() 第一次被请求时触发 |
| 并发启动 | `Effect.forEach(..., { concurrency: 'unbounded' })` 全部 MCP 同时连 | 同——`Promise.all(configs.map(spawn))` |
| 单失败不传染 | `Effect.catch(() => Effect.void)` 单个 MCP 启动失败不影响其他 | 同——try/catch + log + 状态变 'failed' |
| Resource safety | `Effect.acquireUseRelease` 失败时自动 close transport | 用 try/finally + AbortController |

### 1.3 实现细节

```ts
// 复用 Qwen 现有 mcp-client-manager.ts (per-instance 多 client) 
// daemon 化主要改动：把 manager 绑定到 Workspace 而非全局

class Workspace {
  private mcpManager: McpClientManager
  private mcpStatus: Map<string, McpStatus> = new Map()
  
  constructor(private id: string, private directory: string) {
    this.mcpManager = new McpClientManager({
      configFor: this.id,
      cwd: this.directory,
    })
  }
  
  // Lazy 启动：第一次访问 workspace 才初始化 MCP
  async start() {
    const config = await loadMcpConfig(this.directory)
    
    await Promise.allSettled(
      Object.entries(config).map(async ([name, mcp]) => {
        if (mcp.enabled === false) {
          this.mcpStatus.set(name, { status: 'disabled' })
          return
        }
        
        try {
          const client = await this.spawn(name, mcp)
          this.mcpManager.set(name, client)
          this.mcpStatus.set(name, { status: 'connected' })
        } catch (err) {
          // 单 server 失败不影响其他 server
          if (isOAuthError(err)) {
            this.mcpStatus.set(name, { status: 'needs_auth' })
          } else {
            this.mcpStatus.set(name, { status: 'failed', error: String(err) })
          }
        }
      })
    )
  }
  
  // 显式 connect / disconnect API（与 OpenCode 一致）
  async connect(name: string) { ... }
  async disconnect(name: string) {
    const client = this.mcpManager.get(name)
    await client?.close()
    this.mcpStatus.set(name, { status: 'disabled' })
  }
  
  async dispose() {
    await Promise.all(
      Array.from(this.mcpManager.entries())
        .map(([_, c]) => c.close().catch(() => {}))
    )
    this.mcpManager.clear()
  }
}
```

### 1.4 Qwen 保留的两项独有优化（OpenCode 没有）

#### 优化 1：PR#3818 in-flight rediscovery coalesce（已合并）

OpenCode 没有这个机制——多个 session 并发触发同 server reconnect 时，OpenCode 会起多个 client，留游离进程。Qwen PR#3818（已合并）已经修这个：

```ts
// 现有 mcp-client-manager.ts 行为（PR#3818 + workspace 化）
private spawning: Map<string, Promise<McpClient>> = new Map()

async reconnect(name: string) {
  if (this.spawning.has(name)) {
    // 同 server 的并发 reconnect 合并为一次
    return this.spawning.get(name)
  }
  const promise = this.doReconnect(name)
  this.spawning.set(name, promise)
  try { return await promise } finally { this.spawning.delete(name) }
}
```

#### 优化 2：30s 健康检查 + 自动重连（PR#3741 footer pill 暗示已存在）

OpenCode 没有自动健康检查——MCP server 掉线后用户必须主动 `/mcp` connect。Qwen 保留 30s 周期 ping + 自动重连机制：

```ts
// 每 workspace 一个 health check timer
setInterval(async () => {
  for (const [name, client] of this.mcpManager.entries()) {
    if (this.mcpStatus.get(name)?.status !== 'connected') continue
    try {
      await withTimeout(client.ping(), 5_000)
    } catch {
      log.warn('MCP server unresponsive, reconnecting', { name })
      this.reconnect(name)  // 走 PR#3818 coalesce 路径
    }
  }
}, 30_000)
```

### 1.5 重复 spawn 的代价与权衡

per-workspace 的代价：daemon 内 5 个 workspace 都用 `github` MCP → 启 5 个独立子进程。

| 维度 | 评估 |
|---|---|
| 单 MCP server 内存 | 50-200MB |
| 启动开销 | 0.5-2s（lazy 初始化，第一次访问才启）|
| 同时 active workspace | 大多数 ≤ 3 个 |
| 重复 spawn 数 | active workspace × 配置 MCP server 数 = 有限 |
| **隔离收益** | **token / cache / connection 绝对不跨 workspace 泄漏** |

**结论**：可接受。优化跨 workspace 共享是过早优化。

### 1.6 状态机（与 OpenCode 一致）

```ts
type McpStatus =
  | { status: 'connected' }
  | { status: 'disabled' }
  | { status: 'failed', error: string }
  | { status: 'needs_auth' }                                  // OAuth 未完成
  | { status: 'needs_client_registration', error: string }    // dynamic client registration
```

Qwen 现有 `MCPServerStatus`（`packages/core/src/tools/mcp-client.ts:73`）3 种 → daemon 化扩展到 5 种与 OpenCode 对齐。

---

## 2. FileReadCache 共享策略

### 2.1 决策回顾（[03 §4](./03-architectural-decisions.md#4-filereadcache-共享语义)）

**Session 内私有**（终态决策）—— **不**跨 session 共享，包括同 workspace 内的多个 session。**daemon 化无需任何修改**，PR#3717 当前实现已经是 session-scoped。

### 2.2 与 §1 MCP 共享策略不对称

注意 FileReadCache 比 MCP **更激进的隔离边界**：

| 资源 | 共享边界 |
|---|---|
| MCP server | per-workspace（多 session 共享）|
| **FileReadCache** | **per-session**（多 session 即使同 workspace 也不共享）|

不对称是有意的——理由：

| 资源 | 状态变更频率 | 状态泄漏后果 |
|---|---|---|
| MCP server | 配置变才变（低频）| 跨 workspace 风险（数据库连接 / token）|
| FileReadCache | 每个 Read / Write 都可能变 | **正确性 bug**（PR#3774 prior-read 守卫语义直接崩坏）|

### 2.3 PR#3717 当前实现已是 session-scoped

```ts
// PR#3717 设计
class FileReadCache {
  // session-private state
  private byKey: Map<DevInoKey, ReadEntry>   // (dev, ino) → entry
}

// 每 SessionService 持一个实例
class SessionService {
  private fileReadCache = new FileReadCache()
}
```

**daemon 化天然兼容**：每 session 各自持 FileReadCache instance，跟着 Session 生命周期生灭，无需修改。

### 2.4 PR#3810 invalidation 在 daemon 模式下的语义

PR#3810（已合并）修复 5 条 history-rewrite 路径的 cache invalidation：

| 路径 | daemon 模式语义 |
|---|---|
| `microcompactHistory` | per-session compaction → session 自己 clear cache |
| `setHistory` / `truncateHistory` / `resetChat` | per-session 操作 → session 自己 clear |
| `stripOrphanedUserEntriesFromHistory` | per-session 重试 → session 自己 clear |

session 隔离 → daemon 模式下 PR#3810 的所有 fix 路径都是 session 内操作，invalidation 半径**不会扩大到 workspace 级别**——这是个工程上的安全保证。

### 2.5 PR#3774 prior-read enforcement 的关键依赖

PR#3774（已合并 2026-05-06）实现的两个错误码语义如下：

| 错误码 | 触发条件 |
|---|---|
| `EDIT_REQUIRES_PRIOR_READ` | cache `miss`（当前 session 没看过该文件）|
| `FILE_CHANGED_SINCE_READ` | cache `hit-stale`（mtime 已变）|

**这两个错误码的语义假设是 "session-private cache"**：
- `miss` = "**当前 session** 从未 read 过该文件"
- `hit-fresh` = "**当前 session** 已 read 且文件未变"

如果共享 cache（比如 workspace 内跨 session）：
- `miss` 失去 "当前 session 未读过" 含义（其他 session 可能读过但当前没读过）
- PR#3774 的 prior-read 守卫**整套语义失效**

**结论**：FileReadCache 必须保持 session 内私有，**不评估 Stage 3 升级**——这是与 PR#3774 已落地实现的硬约束。

### 2.6 跨 session 重复 read 的实际代价

| 场景 | 评估 |
|---|---|
| 同 workspace 两个 session 都看 README.md | 第二次 OS page cache 命中（disk 0 I/O）+ 仅多耗 LLM token（FileReadCache 没短路）|
| 频率 | 在决策 §1 默认 `single` scope 下，多 client 实际共享同一 session（同 cache）—— 不存在两个 session 看同文件场景 |
| 仅在 fork session / `LoadSession` 后才出现 | cold path |

**结论**：跨 session 重复 read 在 daemon 默认 scope 下基本不发生；为了一个不存在的优化破坏 PR#3774 守卫不划算。

---

## 3. LSP server 共享策略

### 3.1 决策

**每 workspace 一个 LSP server，跨 session 共享**（与 OpenCode 一致）。

### 3.2 理由

| 选项 | 说明 |
|---|---|
| **A：每 workspace 一个 LSP（本设计）** | LSP 服务端就是为"项目"设计的（不是 per-conversation）;TypeScript LSP 启动 5-15s，session 共享是必须的 |
| B：每 session 一个 LSP | 启动开销爆炸，文件索引重复 |

### 3.3 实现

Qwen Code 当前 LSP 实现（`packages/core/src/lsp/`）已经是 per-workspace 设计——daemon 化无需修改。

```ts
// daemon 内
class Workspace {
  private lspManager: LspClientManager  // 每 workspace 唯一
  
  getSession(sessionId: string) {
    return new Session({ ...config, lsp: this.lspManager })  // 共享 LSP
  }
}
```

### 3.4 状态隔离

LSP request 通过 `textDocument/uri` 等显式参数传文件路径，没有跨 session 的状态泄漏风险。LSP server 自身可能维护打开文档的 cache，但这是文件级别（与 session 无关）。

---

## 4. PTY / Background shell 共享策略

### 4.1 决策

**按 PR#3642 已有的 `BackgroundShellRegistry` 行为，每个 task 独立 PTY，但调度面跨 session 共享**。

### 4.2 现状

PR#3642（已合并）+ PR#3687 + PR#3720 已经把 background shell 接入统一调度面：

```ts
// 现有
BackgroundShellRegistry  // workspace 级别（不是 session）
  ├─ Shell #1 (taskId=t1, sessionId=s1)
  ├─ Shell #2 (taskId=t2, sessionId=s1)
  ├─ Shell #3 (taskId=t3, sessionId=s2)  ← 不同 session 的 shell
```

**daemon 化无需修改**——已经是跨 session 调度。

### 4.3 跨 client 可见性

PR#3801 让 `/tasks` 命令在 headless / non-interactive / ACP 路径列出 monitor 任务。daemon 模式下：

```http
GET /workspace/:id/tasks HTTP/1.1
→ 200 OK
{
  "tasks": [
    { "kind": "shell", "id": "t1", "sessionId": "s1", "status": "running", ... },
    { "kind": "agent", "id": "t2", "sessionId": "s1", "status": "completed", ... },
    { "kind": "monitor", "id": "t3", "sessionId": "s2", ... },
    { "kind": "dream", "id": "t4", "sessionId": "s1", ... }
  ]
}
```

跨 client / 跨 session 的全部 4 种 kind 任务都能列出——这是 daemon 模式独有的"global view"，单 session 模式下做不到。

---

## 5. Skill registry 共享策略

### 5.1 决策

**全局共享（daemon 进程内单例），按 path-conditional 激活**（PR#3852 路径动态发现机制天然支持）。

### 5.2 理由

Skill registry 是声明式的（不可变）—— 跨 session 共享同一个 registry 单例无任何问题。

PR#3852（已合并）让 path-conditional 激活基于"discovered result paths"——这本来就是 per-tool-call 决策，与 session 状态无关。

### 5.3 实现

```ts
// daemon 启动时加载一次
const skillRegistry = await loadSkillRegistry()

// 每 workspace 复用
class Workspace {
  getSkillsForSession(session: Session) {
    return skillRegistry.activate({
      directory: this.directory,
      conditionalRules: collectFromSession(session),
    })
  }
}
```

### 5.4 reload 机制

```http
POST /workspace/:id/skill/reload HTTP/1.1
→ 200 OK
{ "reloaded": 42 }
```

允许 `.qwen/skills/` 目录修改后无需重启 daemon。

---

## 6. Provider config / Auth 共享策略

### 6.1 决策

**Provider registry 全局共享；Auth credentials per-workspace 隔离**。

| 资源 | 共享范围 | 理由 |
|---|---|---|
| Provider 注册（DashScope / Anthropic / OpenAI 等的能力描述）| daemon 全局 | 不可变配置 |
| Auth credentials（API key / OAuth token）| **workspace** | 不同 workspace 可能用不同账号（个人 / 公司）|
| Model registry（具体模型名/参数）| daemon 全局 | 不可变 |
| `extra_body` / `samplingParams` / `reasoning` 等模型设置 | per-session | 用户可在 session 层修改 |

### 6.2 PR#3815 加成

PR#3815（已合并 2026-05-05）修复 fast model side queries 用 main model 的 `ContentGeneratorConfig` 导致设置泄漏的 bug。**daemon 化下这个修复直接生效**——side queries 用 per-model 配置而非 session 层全局共享。

---

## 7. 资源共享决策汇总表

| 资源 | 共享范围 | 隔离机制 | 现有 PR |
|---|---|---|---|
| Provider registry | daemon 全局 | 不可变 | — |
| Skill registry | daemon 全局 + path-conditional 激活 | 不可变 + per-tool-call 激活 | PR#3852 |
| Auth credentials | per-workspace | workspace 隔离 | — |
| LSP server | per-workspace | workspace 隔离，session 共享 | — |
| MCP server | daemon pool（按 fingerprint）| 每 MCP request 带 sessionId metadata + per-server fallback | PR#3818 / PR#3819 |
| Background shell | per-task / 调度面 workspace 级 | task ID + sessionId 关联 | PR#3642 / PR#3687 / PR#3720 |
| Background agent | per-task / 调度面 workspace 级 | 同上 | PR#3471 / PR#3488 |
| Monitor | per-task / 调度面 workspace 级 | 同上 | PR#3684 / PR#3791 |
| Dream task | per-task / 调度面 workspace 级 | 同上 | PR#3836 |
| **Session state** | **per-session** | **AsyncLocalStorage 隔离 + SessionService 持久化** | PR#3739 |
| **FileReadCache** | **per-session** | **PR#3717 设计天然 session-scoped** | PR#3717 / PR#3810 |
| Permission flow | per-tool-call | PR#3723 | PR#3723 |
| FastModel config | per-model（不再泄漏 main model）| PR#3815 修复 | PR#3815 |

---

下一篇：[07-权限 / 认证 →](./07-permission-auth.md)
