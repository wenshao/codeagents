# 06 — MCP / FileReadCache / LSP 资源共享

> [← 上一篇：进程模型](./05-process-model.md) · [下一篇：权限 / 认证 →](./07-permission-auth.md)

> daemon 模式下"哪些资源跨 session 共享、哪些隔离"是性能与正确性的关键平衡。

## 1. MCP server 共享策略

### 1.1 决策回顾（[03 §3](./03-architectural-decisions.md#3-mcp-server-生命周期)）

**daemon 内 pool 跨 session 复用，按 MCP 配置 fingerprint 去重，per-server fallback 机制兜底**。

### 1.2 实现细节

```ts
// packages/core/src/tools/mcp-client-manager.ts (现有 + daemon 化扩展)

class McpClientManager {
  // 现有: PR#3818 已加 in-flight restart coalesce
  private spawning: Map<string, Promise<McpClient.Info | undefined>>
  
  // daemon 新增
  private pool: Map<string, McpClient> = new Map()  // fingerprint → client
  
  private fingerprint(config: McpServerConfig): string {
    // 包含 command + args + env + transport type，但不含 session id
    return crypto.createHash('sha256')
      .update(JSON.stringify({
        command: config.command,
        args: config.args,
        env: config.env,
        type: config.type,  // stdio / sse / http
      }))
      .digest('hex')
  }
  
  async getOrSpawn(config: McpServerConfig, sessionId: string): Promise<McpClient> {
    const fp = this.fingerprint(config)
    
    if (this.pool.has(fp)) {
      // ✓ 跨 session 复用
      this.pool.get(fp).bindSession(sessionId)
      return this.pool.get(fp)
    }
    
    // PR#3818 coalesce: 同 fp 的并发 request 共享 in-flight spawn
    if (this.spawning.has(fp)) {
      return await this.spawning.get(fp)
    }
    
    const promise = this.spawn(config)
    this.spawning.set(fp, promise)
    
    const client = await promise
    this.pool.set(fp, client)
    this.spawning.delete(fp)
    return client
  }
  
  // 当所有 session 都释放某 MCP server 时，可考虑回收（reference counting）
  releaseSession(sessionId: string) {
    for (const [fp, client] of this.pool) {
      client.unbindSession(sessionId)
      if (client.boundSessionCount() === 0) {
        // 选项 A: 立即关闭（积极回收）
        // 选项 B: 30s TTL 后关闭（避免频繁 spawn/kill）
        scheduleClose(fp, 30_000)
      }
    }
  }
}
```

### 1.3 状态泄漏防护

**风险**：MCP server 可能持有 session-specific 状态（如对话上下文 / 鉴权 token / 缓存）。

**防护机制**：

```ts
// 每次 MCP request 把 session metadata 显式传给 server
const result = await mcpClient.callTool(toolName, args, {
  metadata: {
    sessionId: Instance.sessionId,        // 让 MCP server 自行做 per-session 隔离
    workspaceId: Instance.workspaceId,
    clientId: Instance.clientId,
  }
})
```

**Fallback**：settings 提供 `mcpSharedPool: false` 开关，强制 per-session spawn。某些 MCP server（如有状态的数据库连接 server）应该显式标记 `requiresPerSession: true`：

```json
{
  "mcpServers": {
    "github": {
      "command": "...",
      "requiresPerSession": false   // 默认 false（共享）
    },
    "private-db": {
      "command": "...",
      "requiresPerSession": true    // 强制 per-session
    }
  }
}
```

### 1.4 现有 PR 加成

| PR | 加成 |
|---|---|
| PR#3818 ✓ | rediscovery in-flight coalesce —— 同 fingerprint 并发请求合一 |
| PR#3819 CLOSED 2026-05-05 | prevent duplicate MCP processes from concurrent discovery —— 后续被 PR#3818 主体覆盖，本 PR 关闭 |

PR#3818 已合并 → daemon 模式的 MCP 共享 pool 核心机制（in-flight coalesce）已经在 master 中可用。

---

## 2. FileReadCache 共享策略

### 2.1 决策回顾（[03 §4](./03-architectural-decisions.md#4-filereadcache-共享语义)）

**保守起步：session 内私有，跨 session 不共享**。Stage 3 评估升级为 daemon 全局共享。

### 2.2 现状

PR#3717 引入的 `FileReadCache` 当前**已经是 session-scoped 设计**：

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

**daemon 化天然兼容**：每 session 各自持 FileReadCache instance，无需修改。

### 2.3 PR#3810 invalidation 在 daemon 模式下的语义

PR#3810（已合并）修复 5 条 history-rewrite 路径的 cache invalidation：

| 路径 | daemon 模式语义 |
|---|---|
| `microcompactHistory` | per-session compaction → session 自己 clear cache |
| `setHistory` / `truncateHistory` / `resetChat` | per-session 操作 → session 自己 clear |
| `stripOrphanedUserEntriesFromHistory` | per-session 重试 → session 自己 clear |

session 隔离 → daemon 模式下 PR#3810 的所有 fix 路径都是 session 内操作，无需扩展。

### 2.4 Stage 3 升级路线（暂缓）

如果将来跨 session 共享 cache 收益足够大（如多 client 同 workspace 大量重复读 README.md），可以考虑：

```ts
// 升级方案（Stage 3 评估）
class WorkspaceFileReadCache {
  // workspace 内多 session 共享
  private byKey: Map<DevInoKey, { mtime, sessionsViewed: Set<sessionId> }>
  
  check(key: DevInoKey, sessionId: string): 'hit-fresh' | 'hit-stale-or-unseen' | 'miss' {
    const entry = this.byKey.get(key)
    if (!entry) return 'miss'
    
    // 必须：mtime 没变 + 当前 session 看过
    if (entry.mtime === currentMtime && entry.sessionsViewed.has(sessionId))
      return 'hit-fresh'
    
    // 其他 session 看过但当前 session 没看过 — 仍需重新 read（保 PR#3774 prior-read 语义）
    return 'hit-stale-or-unseen'
  }
}
```

**风险**：PR#3774 prior-read enforcement 假设 cache "miss 表示当前 session 没看过"——共享 cache 后这个假设失效。Stage 3 实施前必须重新审计 PR#3774 / PR#3840 双轨守卫的语义。

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
