# 07 — 权限流与认证

> [← 上一篇：MCP / 资源共享](./06-mcp-resources.md) · [下一篇：3 阶段路线图 →](./08-roadmap.md)

> 设计原则：**双层权限**——传输层 bearer token 阻止未授权访问，应用层复用 PR#3723 已合并的 `evaluatePermissionFlow()` 把 daemon 加为第 4 种 execution mode。

## 一、双层权限模型

```
┌────────────────────────────────────────────────────┐
│ Layer 1：传输层 Bearer Token                          │
│ ├─ daemon 启动: QWEN_SERVER_TOKEN env / --token flag │
│ ├─ 中间件: AuthMiddleware 校验 Authorization header   │
│ └─ 401 拒绝未授权请求                                 │
└────────────────────────────────────────────────────┘
                       ↓
┌────────────────────────────────────────────────────┐
│ Layer 2：应用层 Permission Flow（PR#3723）            │
│ ├─ L3: Tool 内置默认权限                              │
│ ├─ L4: PermissionManager 规则覆盖 (allowlist/etc)    │
│ ├─ finalPermission: allow / deny / ask               │
│ └─ L5: 调用方覆盖 (YOLO / AUTO_EDIT / PLAN / 新加 daemon)│
└────────────────────────────────────────────────────┘
                       ↓
                tool 执行 / 拒绝 / 弹审批
```

## 二、Layer 1：传输层 Bearer Token

### 2.1 启动配置

```bash
# 方式 A：环境变量（推荐）
QWEN_SERVER_TOKEN=$(openssl rand -hex 32) qwen serve

# 方式 B：CLI flag
qwen serve --token=$(openssl rand -hex 32)

# 方式 C：settings.json
{ "daemon": { "token": "..." } }

# 方式 D：随机生成 + 写入 ~/.qwen/daemon-token
qwen serve --auto-token
# → daemon 启动时随机生成一次性 token，写到本地 ~/.qwen/daemon-token
# → SDK 客户端默认从该路径读取（与 OpenCode 模式接近）
```

### 2.2 Middleware 实现

```ts
// packages/server/src/middleware/auth.ts (新建位置)
export const authMiddleware: MiddlewareHandler = async (c, next) => {
  if (c.req.path === '/health') return next()  // 健康检查不验证
  
  const token = process.env.QWEN_SERVER_TOKEN ?? loadFromSettings()
  if (!token) {
    log.warn('QWEN_SERVER_TOKEN not set — daemon is unsecured')
    return next()  // 开发模式
  }
  
  const auth = c.req.header('Authorization')
  if (!auth?.startsWith('Bearer ') || auth.slice(7) !== token) {
    return c.json({ error: 'unauthorized' }, 401)
  }
  
  return next()
}
```

### 2.3 默认 binding

| 配置 | 默认 binding | 安全级别 |
|---|---|---|
| 未设 token + 未指定 host | `127.0.0.1:5096` only | 仅本机 |
| 未设 token + `--hostname=0.0.0.0` | **拒绝启动** + 提示需设 token | 强制安全 |
| 设了 token | 允许任意 binding | token 保护 |

参考 OpenCode 的默认行为，但比 OpenCode 更严格（OpenCode 仅警告 unsecured 不拒绝启动）。

### 2.4 多 client / multi-tenant？

**Stage 1 / Stage 2 不支持**——单 token = 单租户（所有 client 用同一 token）。

**Stage 3 评估**：如果需要多用户隔离（如部署在云端给团队用），可加 `tokens.json` 多 token + 每 token 绑定 user-id + workspace allowlist：

```json
{
  "tokens": [
    { "id": "tok-alice", "secret": "...", "userId": "alice", "workspaces": ["*"] },
    { "id": "tok-bob",   "secret": "...", "userId": "bob",   "workspaces": ["ws-bob-only"] }
  ]
}
```

## 三、Layer 2：应用层 Permission Flow

### 3.1 复用 PR#3723

PR#3723（已合并 2026-04-30 +461/-95）引入的 `evaluatePermissionFlow()` 已经支持 Interactive / Non-Interactive / ACP 三种 mode：

```
L3: Tool 内置默认权限
 ↓
L4: PermissionManager 规则覆盖
 ↓
finalPermission: allow | deny | ask
 ↓
L5: 调用方覆盖（YOLO / AUTO_EDIT / PLAN）
```

**daemon 加为第 4 种 mode 的扩展点**：

```ts
// packages/core/src/core/permissionFlow.ts (现有 PR#3723)
type ExecutionMode =
  | 'interactive'
  | 'non-interactive'
  | 'acp'
  | 'daemon-http'   // ← 新增

// daemon mode 的 ask 决策处理 — 与 ACP 类似但通过 HTTP/SSE
function handleAskInDaemonHttp(
  result: PermissionFlowResult,
  ctx: DaemonContext,
): Promise<boolean> {
  const requestId = uuid()
  
  // 通过 SSE 推 permission_request 给所有订阅当前 session 的 client
  ctx.sseStream.send({
    type: 'permission_request',
    requestId,
    tool: result.tool.name,
    args: result.tool.args,
    rationale: result.askReason,
  })
  
  // 等 client 回 POST /permission/:requestId
  return waitForPermissionResponse(requestId, {
    timeout: 60_000,
    fallback: 'deny',
  })
}
```

### 3.2 跨 client 审批语义（核心 UX 设计）

[决策 §1](./03-architectural-decisions.md#1-session-是否跨-client-共享) 默认 `single` scope（同 workspace 多 client 共享 session）+ [决策 §6](./03-architectural-decisions.md#6-多-client-并发请求)（事件 fan-out + 任何 client 应答 permission）—— 这给 daemon 带来一个独有的 UX 优势：**审批可以从最舒适的 client 上做**。

**典型场景**：

```
1. 用户在 CLI（terminal）发 prompt: "请重构 src/foo.ts"
2. Agent 决定调 Bash 跑 npm test → permission_request
3. CLI / VSCode / Web UI 三个 client 都通过 SSE 收到 permission_request 事件
4. 用户在哪个 client 都能批准:
   - CLI: y/n（TUI dialog）
   - VSCode: 弹原生通知 [Allow] [Deny]
   - Web UI: 浏览器对话框点击
5. 任何一个 client 先 POST /permission/:id —— first responder wins
6. 其他 client 收到 SessionNotification "permission resolved by another client"
   → 自动关闭弹窗
```

**实现选择**：

| 选项 | 评估 |
|---|---|
| **A：first responder wins（本设计选）** | ✓ 简单可用 ✓ UX 直觉（哪个 client 顺手就批） ✗ 多人模式下可能有"别人替我批了"的困惑 |
| B：仅 primary client 能审批 | 需要"主控端 + 观察端"角色概念 → 增加 client 类型 ✗ 用户额外管理负担 |
| C：majority vote | 多人协作场景才有意义；单用户多 client 反而不便 |

Stage 1/2 选 A；Stage 3 评估 B 作为多用户企业部署可选项。

### 3.3 审批响应 schema

```http
POST /permission/r1 HTTP/1.1
Authorization: Bearer xxx

{
  "allow": true,
  "alwaysAllowFor": "session",     // 'session' / 'workspace' / 'global' / null（仅本次）
  "respondedBy": "client-vscode-1" // 可选 metadata，用于审计 + 通知其他 client 谁批准了
}
```

daemon 收到后：
1. resolve `waitForPermissionResponse(requestId)` —— 阻塞中的 prompt 继续
2. 通过 SSE 广播 `permission_resolved` 事件给所有 client（含 originating client + observer）：
   ```json
   { "type": "permission_resolved", "requestId": "r1", "decision": "allow", "by": "client-vscode-1" }
   ```
3. 如果 `alwaysAllowFor` 不为 null，写 SQLite `permission_decisions` 表（详见 §4）
4. 后续相同 pattern 的工具调用直接走 cache，不再发 permission_request

### 3.3 DaemonContext 中的 permission 配置

```ts
// 每 session 的 permission settings
interface DaemonSessionPermissionConfig {
  mode: 'strict' | 'autoEdit' | 'plan' | 'yolo'
  allowedDomains: string[]    // WebSearch + WebFetch
  blockedDomains: string[]
  bashAllowlist: string[]      // bash 命令前缀 allowlist
  fileWriteAllowlist: string[] // 文件写入路径 allowlist
}

// 通过 settings 或 SetSessionConfigOptionRequest 配置
```

## 四、`alwaysAllow` 持久化

```ts
// 当前 ACP 已有 alwaysAllow 概念（用于"始终允许 npm test"等模式）
// daemon 把 alwaysAllow 决策持久化到 SQLite（不只是内存）

CREATE TABLE permission_decisions (
  workspace_id TEXT NOT NULL,
  pattern TEXT NOT NULL,           -- 如 'Bash(npm test)'
  scope TEXT NOT NULL,              -- 'session' / 'workspace' / 'global'
  decision TEXT NOT NULL,           -- 'allow' / 'deny'
  expires_at INTEGER,               -- TTL（NULL=永久）
  PRIMARY KEY (workspace_id, pattern, scope)
);
```

每次 daemon 启动时加载 workspace + global scope 的决策；session scope 不持久化（重启即失效）。

## 五、PR#3726 Monitor permission namespace 在 daemon 模式下

PR#3726（已合并）为 `Monitor` 工具加了独立 permission namespace：

```
Monitor(*)         # 所有 monitor 调用允许
Monitor(npm test)  # 仅 npm test
Bash(npm test)     # 不影响 Monitor 调用，避免 "Always Allow Bash" 误授权 Monitor
```

**daemon 化无需修改**——permission flow 复用 namespace 检查逻辑。

## 六、与 OpenCode 认证对比

| 维度 | OpenCode | Qwen Daemon（本设计）|
|---|---|---|
| 默认 token | 无（警告 unsecured）| 无 token + 0.0.0.0 binding **拒绝启动** |
| Token 来源 | `OPENCODE_SERVER_PASSWORD` env | env / CLI flag / settings / 自动生成 4 选 1 |
| 多 token | ❌ | 🟡 Stage 3 评估 |
| 工具级权限 | 走 OpenCode permission system | **复用 PR#3723 evaluatePermissionFlow()** —— 与现有 ACP/CLI 实现共享 |
| 审批 UI | dialog | **SSE event + POST /permission/:id** —— 异步流模式 |
| `alwaysAllow` 持久化 | settings JSON | **SQLite per-workspace + 永久/TTL** |
| Monitor namespace | ❌ | ✓（PR#3726）|

## 七、典型权限审批流程

### 场景：用户跑 `qwen "重构 src/foo.ts"` 通过 SDK

```
1. SDK Client → POST /session/:id/prompt HTTP/1.1
   Authorization: Bearer xxx
   { "prompt": [...] }
   
2. daemon middleware 校验 token ✓ → 进入 evaluatePermissionFlow()

3. core 决定调 Edit 工具 (改 src/foo.ts)
   permissionFlow → L4 评估 → 'ask'

4. daemon SSE → client:
   data: {"type":"permission_request","requestId":"r1","tool":"Edit","args":{"path":"src/foo.ts",...}}

5. SDK 客户端代码:
   q.on('permission_request', async (req, resolve) => {
     const allow = await myUI.confirm(`Edit ${req.args.path}?`)
     await fetch(`/permission/${req.requestId}`, {
       method: 'POST', body: JSON.stringify({ allow })
     })
   })

6. daemon 收到 POST /permission/r1 → resolve waitForPermissionResponse()
   → permission flow 决策 'allow'
   → core 执行 Edit
   
7. daemon SSE → client:
   data: {"type":"tool_result","output":"..."}
   data: {"type":"message_part","content":"我重构了..."}

8. POST /session/:id/prompt 返回 PromptResponse
```

## 八、安全边界检查清单

daemon 落地前必须确认：

- [ ] 默认仅 127.0.0.1 binding（防止意外暴露）
- [ ] Token 缺失 + 0.0.0.0 → 拒绝启动（不仅警告）
- [ ] CORS 白名单仅 `localhost` / `127.0.0.1`（默认）
- [ ] WebSocket 升级时复用 token 校验（不能绕过）
- [ ] SSE 长连接 + token 失效 → 服务端主动断开
- [ ] `alwaysAllow` 持久化的 SQLite 文件权限 0600（只 owner 可读）
- [ ] Permission flow 的 `daemon-http` mode **不要**默认走 YOLO（OpenCode 一些场景默认 YOLO，不适合 daemon）
- [ ] Tool result（含 WebSearch / WebFetch 抓回的外部数据）走 prompt-injection 防御（参考 PR#3844 设计）

---

下一篇：[08-3 阶段路线图 →](./08-roadmap.md)
