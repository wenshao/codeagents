# 12 — 多租户水平越权防御

> [← 上一篇：多租户与 Shell 沙箱](./11-multi-tenancy-and-sandbox.md) · [回到 README](./README.md)

> 多租户下"水平越权"（Horizontal Privilege Escalation, HPE）= 同等级 tenant 访问另一 tenant 的资源。本章系统列出 **17 个攻击向量** 并给出**分层防御**方案。

## 一、TL;DR — 防御纵深 5 层

```
┌────────────────────────────────────────────────────────────┐
│ 第 5 层: Audit & Anomaly Detection                          │
│   异常访问模式检测（同 tenant 短时间访问大量他人 ID）         │
└────────────────────────────────────────────────────────────┘
                           ↑
┌────────────────────────────────────────────────────────────┐
│ 第 4 层: 数据保护层                                          │
│   ID 不可猜（UUID v4 / cryptographic random）                │
│   敏感数据加密（API key / OAuth token）                       │
└────────────────────────────────────────────────────────────┘
                           ↑
┌────────────────────────────────────────────────────────────┐
│ 第 3 层: 应用层 ACL（每次操作前显式校验）                     │
│   每个 session/workspace ID 操作都验证归属                    │
│   AsyncLocalStorage tenantId 强制传播                         │
└────────────────────────────────────────────────────────────┘
                           ↑
┌────────────────────────────────────────────────────────────┐
│ 第 2 层: 资源边界（自然隔离）                                 │
│   Workspace path realpath + chroot/symlink 防御              │
│   FileReadCache per-session（决策 §4）                        │
│   MCP per-workspace（决策 §3）                                │
└────────────────────────────────────────────────────────────┘
                           ↑
┌────────────────────────────────────────────────────────────┐
│ 第 1 层: 认证                                                │
│   Bearer Token + 强随机 + 不可猜测                            │
│   Token 与 tenant 1:1 / 1:N 绑定                              │
└────────────────────────────────────────────────────────────┘
```

**核心原则**（OWASP 推荐）：
1. **不信任 client 提供的任何 ID**——server 端必须显式校验所有 workspace/session/task ID 的归属
2. **不依赖单层防御**——5 层防御都失效才会被攻破
3. **失败默认 deny**——任何不确定都拒绝，记录 audit log
4. **不可猜测 ID**——所有面向客户端的 ID 用 cryptographic random（UUID v4 不行，必须 ≥128 bit unguessable）

## 二、17 个水平越权攻击向量分类

### 2.1 Auth / ACL 层（4 个）

| # | 攻击 | 描述 |
|---|---|---|
| **A1** | Token 泄漏后越权访问 | 攻击者拿到 tenant 的 bearer token，可访问该 tenant 全部资源 |
| **A2** | Token 替换 | client 用 tenant A 的 token 但请求 body 中带 tenant B 的 ID |
| **A3** | Workspace ID 越权 | tenant A 用自己的 token + tenant B 的 workspace ID 试图访问 |
| **A4** | Session ID 猜测 | session ID 可猜（如自增 ID） → 直接访问其他 tenant 的 session |

### 2.2 Filesystem 层（5 个）

| # | 攻击 | 描述 |
|---|---|---|
| **F1** | Path traversal | `cwd: '../../../etc/passwd'` 突破 workspace 边界 |
| **F2** | Symlink attack | tenant 的 workspace 内创建 symlink 指向 `/tenants/other/` 目录 |
| **F3** | Mount escape | tenant 在 workspace 内 mount 其他 tenant 的目录（仅 sandbox 内可能）|
| **F4** | Hard link cross-tenant | 在多 tenant workspace 共用一个 mount 时，hardlink 跨 inode 边界 |
| **F5** | Race condition (TOCTOU) | tenant A 注册 workspace 时和 tenant B 同时操作，竞争抢注 |

### 2.3 Cache / State 层（4 个）

| # | 攻击 | 描述 |
|---|---|---|
| **C1** | FileReadCache key 碰撞 | 跨 mount namespace `(dev, ino)` key 重叠（不同 mount 同 inode 号）|
| **C2** | MCP server state 泄漏 | 同 fingerprint MCP server 跨 tenant 复用（决策 §3 已选 per-workspace 防御）|
| **C3** | Permission `alwaysAllow` 决策跨 tenant 泄漏 | SQLite `permission_decisions` 表读取 / 写入未做 tenant ACL |
| **C4** | GlobalBus event 跨 tenant 订阅 | tenant A 订阅了 tenant B 的 SessionNotification |

### 2.4 Sandbox 层（4 个）

| # | 攻击 | 描述 |
|---|---|---|
| **S1** | Sandbox escape | 容器/namespace 逃逸，直接访问 daemon 主进程内存 |
| **S2** | cgroup limit 绕过 | 通过 fork bomb / 大文件填满 cgroup 影响其他 tenant |
| **S3** | Network namespace 漏洞 | 一个 tenant 通过 raw socket 嗅探其他 tenant 流量 |
| **S4** | Sandbox 共享资源 | 共享 `/tmp` / shared memory / IPC 跨 tenant 泄漏 |

### 2.5 Side-channel & DoS 层（4 个）

| # | 攻击 | 描述 |
|---|---|---|
| **D1** | Timing attack 推断 ID 存在性 | 通过响应时间差异判断某 tenant ID 是否存在 |
| **D2** | Quota 共享导致跨 tenant DoS | 共享 LLM rate limit 池 → 一个 tenant 跑爆影响他人 |
| **D3** | Audit log 跨 tenant 读 | 一个 tenant 调试时看到他人 audit |
| **D4** | Resource exhaustion | 一个 tenant 启大量 MCP / shell 占满 daemon 资源 |

## 三、分层防御方案（每个攻击向量）

### 3.1 Auth / ACL 层防御

#### A1: Token 泄漏

```ts
// 1. 短期 token + refresh 模式
interface TenantToken {
  id: string                    // tok_abc123
  secret: string                // bcrypt hash 存储
  expiresAt: number            // 默认 7 天
  scope: string[]              // ['workspace:ws-alice-*', 'tool:bash:read']
  ipAllowlist?: string[]       // 可选：仅允许某 IP / CIDR
}

// 2. Token rotation（建议每 7 天）
async function rotateToken(oldToken: string): Promise<TenantToken> {
  const newToken = generateCryptoRandom(256)  // 32 bytes / 256 bit
  await db.transaction(async (tx) => {
    await tx.expireToken(oldToken)
    await tx.createToken(newToken)
  })
  return newToken
}

// 3. Anomaly detection（详见 §3.5）
// 同一 token 短时间从 5 个不同 IP 访问 → 触发 lockdown
```

#### A2: Token 替换攻击防御

**关键**：所有请求中的 ID 必须**与 token 绑定的 tenant 校验**：

```ts
// auth middleware (扩展自 §11 §4.3)
export const authMiddleware = async (c, next) => {
  const token = c.req.header('Authorization')?.slice(7)
  const tenant = await tokenToTenant.get(token)
  if (!tenant) return c.json({ error: 'unauthorized' }, 401)
  
  // ⚠️ 关键: 所有 path / body / query 中的 ID 都必须属于这个 tenant
  const checks = [
    c.req.param('workspaceId'),
    c.req.param('sessionId'),
    c.req.param('taskId'),
    c.req.body?.meta?.workspaceId,
    c.req.body?.meta?.tenantId,        // body 中显式声明的 tenantId 必须 == token 解析出的
  ]
  
  for (const id of checks.filter(Boolean)) {
    if (!await belongsToTenant(id, tenant.id)) {
      // 不直接报 "forbidden" 或 "not found"——会泄漏 ID 存在性
      // 用 timing-safe 的 404
      await timingSafeDelay()
      return c.json({ error: 'not found' }, 404)
    }
  }
  
  return Instance.provide({ tenantId: tenant.id, ... }, next)
}
```

#### A3: Workspace ID 越权

```ts
// belongsToTenant 必须查询持久化数据，不依赖 client 提供
async function belongsToTenant(workspaceId: string, tenantId: string): Promise<boolean> {
  // 优先查内存 Map（防止 SQL 注入风险 + 性能）
  const ws = workspaceMap.get(workspaceId)
  if (!ws) {
    // workspace 不存在或已删除，等同于"不属于"
    return false
  }
  // 严格相等（不接受通配符 / 子串匹配等模糊语义）
  return ws.tenantId === tenantId
}
```

#### A4: Session ID 不可猜测

```ts
// 使用 cryptographic random 生成 ID（不是 UUID v4，UUID v4 仅 122 bit）
import { randomBytes } from 'crypto'

function newSessionId(): string {
  // 256 bit unguessable
  return 'sess_' + randomBytes(32).toString('base64url')
}

// ❌ 不要用：
// - 自增 ID
// - 时间戳为主的 ID
// - hash(tenant_id + counter)
// - UUID v1 (含 MAC + timestamp)
// 
// ✓ 推荐：UUID v4 / nanoid (>=128 bit) / randomBytes(32)
```

### 3.2 Filesystem 层防御

#### F1: Path traversal

```ts
// packages/core/src/util/path-safety.ts (新建)
export function safeJoinWithinWorkspace(
  workspaceRoot: string,
  userProvidedPath: string,
): string {
  // 1. 拒绝绝对路径
  if (path.isAbsolute(userProvidedPath)) {
    throw new ErrorPathOutsideWorkspace(userProvidedPath)
  }
  
  // 2. resolve to absolute
  const resolved = path.resolve(workspaceRoot, userProvidedPath)
  
  // 3. realpath 解 symlink（关键 — 见 F2）
  const real = await fs.promises.realpath(resolved).catch(() => resolved)
  
  // 4. 边界检查：必须在 workspaceRoot 内（含 root 自身但不能等于其父）
  const workspaceRootReal = await fs.promises.realpath(workspaceRoot)
  if (!isWithin(real, workspaceRootReal)) {
    throw new ErrorPathOutsideWorkspace(userProvidedPath)
  }
  
  return real
}

function isWithin(child: string, parent: string): boolean {
  const rel = path.relative(parent, child)
  return rel === '' || (!rel.startsWith('..') && !path.isAbsolute(rel))
}
```

**所有 file 工具必须用** `safeJoinWithinWorkspace()`：

| 工具 | 当前 | 加防御后 |
|---|---|---|
| `read_file` | `fs.readFile(path)` | `fs.readFile(safeJoinWithinWorkspace(ws, path))` |
| `write_file` | 同上 | 同上 |
| `edit` | 同上 | 同上 |
| `bash` 的 `cwd` 参数 | 同上 | 同上 + sandbox 内 chroot |
| `glob` / `grep` | 同上 | 同上 |

#### F2: Symlink attack

`realpath` 解 symlink 后做边界检查（已在 F1 中包含）。

**额外防御**：`fs.lstat` 检测目标是否为 symlink，可在 settings 中禁用：

```json
{
  "daemon": {
    "filesystem": {
      "followSymlinks": false   // 默认 true，多租户严格模式可禁用
    }
  }
}
```

`followSymlinks: false` 时，遇 symlink 直接拒绝（很多场景接受不了，因为 node_modules 等会用 symlink，仅适合极严格场景）。

#### F3: Mount escape（sandbox 内）

依赖 sandbox 实现：

| Sandbox | 防御 |
|---|---|
| OsUserSandbox | 用户没有 mount 权限 → 不能 mount |
| NamespaceSandbox | unshare mount namespace + 子进程不可见外部 mount |
| ContainerSandbox | container 默认无 `CAP_SYS_ADMIN` → mount 被禁 |

**关键**：Sandbox 内**禁用 `CAP_SYS_ADMIN`** capability：

```yaml
# 容器配置（Stage 5+）
securityContext:
  capabilities:
    drop:
    - SYS_ADMIN          # 禁止 mount / namespace 操作
    - SYS_PTRACE         # 禁止 attach 其他进程
    - NET_ADMIN          # 禁止改网络配置
    - SETUID             # 禁止 setuid
```

#### F4: Hard link cross-tenant

**根本防御**：每个 tenant 的 workspace **挂在不同的 filesystem mount**（不同 device）。hard link 不能跨 device。

```yaml
# k8s 配置：每 tenant 一个独立 PVC
volumeClaims:
- name: tenant-alice-workspace
  storageClassName: per-tenant
  resources: { requests: { storage: 100Gi } }
- name: tenant-bob-workspace
  storageClassName: per-tenant
  resources: { requests: { storage: 100Gi } }
```

**简化部署**：所有 tenant 共享一个 NFS，但用 `EXDEV` 检查 + 应用层防御：

```ts
async function checkNoHardlinkAcrossTenants(path: string, tenantId: string) {
  const stat = await fs.lstat(path)
  if (stat.nlink > 1) {
    // 多个 link 存在，需要查所有 link 是否都在本 tenant workspace 内
    // 这个检查很贵，建议直接拒绝 nlink > 1 的文件操作
    throw new ErrorMultipleLinks(path)
  }
}
```

#### F5: Workspace 注册 race condition (TOCTOU)

```ts
// ❌ 错误（race condition）
async function registerWorkspace(tenant: Tenant, dir: string) {
  if (await workspaceMap.has(dir)) throw new Error('exists')
  // ← 此处其他 tenant 可能抢注
  workspaceMap.set(dir, new Workspace(tenant.id, dir))
}

// ✓ 正确（原子操作）
async function registerWorkspace(tenant: Tenant, dir: string) {
  const id = newWorkspaceId()  // crypto random
  
  // 用 SQLite UNIQUE constraint 防 race
  try {
    await db.run(`
      INSERT INTO workspaces (id, tenant_id, directory, created_at)
      VALUES (?, ?, ?, ?)
    `, [id, tenant.id, dir, Date.now()])
    // INSERT 成功 = 原子拿下
  } catch (e) {
    if (e.code === 'SQLITE_CONSTRAINT') throw new Error('exists')
    throw e
  }
  
  // 后续才加入内存 Map（认 SQLite 为权威）
  workspaceMap.set(id, new Workspace(tenant.id, id, dir))
}
```

**关键设计**：workspace ID 是**服务端生成**的不可猜测 ID（不是用户提供的目录路径）。请求时 client 用 daemon 返回的 ID，daemon 通过 ID → tenantId 校验归属。

### 3.3 Cache / State 层防御

#### C1: FileReadCache key 碰撞

`(dev, ino)` 在跨 mount 场景**不保证全局唯一**——不同 device 可能有相同 inode 号：

```ts
// 现有 PR#3717 设计 (FileReadCache)
type DevInoKey = { dev: number, ino: number }

// 多租户加 mountId 维度
type SafeFileKey = {
  tenantId: string  // ← 加 tenant 隔离（决策 §4 已 session-scoped 已满足）
  dev: number
  ino: number
}
```

但因为 **§4 决策 FileReadCache per-session 私有**，跨 session 跨 tenant 本来就不共享——这个攻击向量在当前设计下**已经被 §4 决策天然防御**。

**额外审计**：确保 SessionService 内 FileReadCache 的 instance 不被任何全局 Map 持有引用（防止泄漏）。

#### C2: MCP server state 泄漏

决策 §3 已选 **per-workspace MCP**——每 workspace 独立子进程，跨 workspace 跨 tenant 不复用，**已天然防御**。

但仍需审计：
- **Auth credentials** 是否 per-workspace 传递（不是全局）—— ✓ 决策 §6 已确认
- **MCP server 自己的 state** 是否泄漏（如某 MCP 把 sessionId 写到全局文件）—— 需 MCP server 自己保证，daemon 提供 metadata 透传 + `requiresPerSession` 选项

#### C3: Permission `alwaysAllow` 跨 tenant 泄漏

```sql
-- 必须加 tenant_id 维度 + ACL
CREATE TABLE permission_decisions (
  tenant_id TEXT NOT NULL,            -- ← 必加
  workspace_id TEXT NOT NULL,
  pattern TEXT NOT NULL,
  scope TEXT NOT NULL,
  decision TEXT NOT NULL,
  expires_at INTEGER,
  PRIMARY KEY (tenant_id, workspace_id, pattern, scope)
);

-- 所有查询都带 tenant_id
SELECT decision FROM permission_decisions
WHERE tenant_id = ? AND workspace_id = ? AND pattern = ?;
```

**应用代码强制 tenant_id 传播**：

```ts
class PermissionDecisionStore {
  // ⚠️ 错误：没传 tenantId
  async get(workspaceId: string, pattern: string) { ... }
  
  // ✓ 正确：必传 tenantId
  async get(tenantId: string, workspaceId: string, pattern: string) {
    // 永远不能从全局取，必须显式过滤
    return db.get('SELECT ... WHERE tenant_id = ? AND ...', [tenantId, ...])
  }
}

// Caller 用 Instance.tenantId（来自 AsyncLocalStorage）
const decision = await store.get(
  Instance.current().tenantId,
  Instance.current().workspaceId,
  pattern,
)
```

#### C4: GlobalBus event 跨 tenant 订阅

```ts
// ❌ 错误：直接订阅全局 bus
GlobalBus.on('session.message_part', handler)
// 所有 tenant 的 message_part 都会触发，泄漏

// ✓ 正确：按 sessionId / tenantId 过滤
class TenantScopedBus {
  on(event: string, sessionId: string, handler) {
    GlobalBus.on(event, (e) => {
      if (e.sessionId !== sessionId) return  // 严格过滤
      handler(e)
    })
  }
}

// 或者每 tenant 独立 EventEmitter（推荐，根本不共享）
class Tenant {
  private bus = new EventEmitter()
}
```

**SSE 订阅同样过滤**：

```ts
// /session/:id/events SSE handler
app.get('/session/:id/events', authMiddleware, (c) => {
  const sessionId = c.req.param('id')
  const tenantId = Instance.current().tenantId
  
  // ⚠️ 关键：再次校验 session 归属（即使 middleware 已校验，多防御一层）
  if (!belongsToTenant(sessionId, tenantId)) {
    return c.json({ error: 'not found' }, 404)
  }
  
  return streamSSE(c, async (stream) => {
    const session = sessionMap.get(sessionId)
    const unsub = session.subscribe((event) => stream.writeSSE(event))
    c.req.signal.addEventListener('abort', unsub)
  })
})
```

### 3.4 Sandbox 层防御

#### S1: Sandbox escape

防御依赖 sandbox 类型——**最安全是 container/k8s + 严格 capability dropping**：

```yaml
securityContext:
  runAsNonRoot: true
  runAsUser: 10000          # 非 root
  allowPrivilegeEscalation: false
  capabilities:
    drop: ["ALL"]            # 删全部 capability
    add: ["NET_BIND_SERVICE"]  # 仅按需加
  seccompProfile:
    type: RuntimeDefault     # 启用 seccomp
  readOnlyRootFilesystem: true  # / 只读，仅 /tmp / /workspace 可写
```

加 **AppArmor / SELinux profile**（如果系统支持）：

```yaml
annotations:
  container.apparmor.security.beta.kubernetes.io/qwen-sandbox: |
    runtime/default
```

#### S2: cgroup limit 绕过

cgroup v2 强制限制 + memory.max + cpu.max + pids.max：

```bash
# 创建 cgroup
cgcreate -g cpu,memory,pids:qwen/tenant-alice
echo "2G" > /sys/fs/cgroup/qwen/tenant-alice/memory.max
echo "100000 100000" > /sys/fs/cgroup/qwen/tenant-alice/cpu.max  # 1 core
echo "256" > /sys/fs/cgroup/qwen/tenant-alice/pids.max  # 防 fork bomb
```

#### S3: Network namespace

每 sandbox 独立 net namespace + 默认无外网：

```yaml
networkPolicy:
  podSelector: { matchLabels: { tenant: alice } }
  policyTypes: [Egress, Ingress]
  egress:
  - to:
    - podSelector: { matchLabels: { app: qwen-allowed-services } }
  - to:                       # 允许出站到公共 LLM API
    - ipBlock: { cidr: 0.0.0.0/0 }
    ports:
    - protocol: TCP
      port: 443
  # 禁止跨 tenant pod 通信
```

#### S4: 共享 `/tmp` 防御

每 sandbox 独立 `/tmp`（不共享 daemon 主进程的 `/tmp`）：

```ts
// NamespaceSandbox / ContainerSandbox spawn 时创建独立 tmpfs
spawn(cmd, {
  ...,
  // mount tmpfs to /tmp 仅本 sandbox 可见
  preExec: () => mountTmpfs('/tmp', { size: '1G' })
})
```

container 模式天然每容器独立 `/tmp`。

### 3.5 Side-channel & DoS 防御

#### D1: Timing attack 推断 ID 存在性

```ts
// ❌ 错误：response time 泄漏 ID 是否存在
async function checkSession(sessionId, tenantId) {
  const session = sessionMap.get(sessionId)  // 不存在: 1ms
  if (!session) return 404                    // 存在但越权: 5ms (db 查询)
  if (session.tenantId !== tenantId) return 403
  return 200
}

// ✓ 正确：timing-safe + 统一返回 404
async function checkSession(sessionId, tenantId) {
  const session = sessionMap.get(sessionId)
  
  // 始终做相同工作量
  const fakeWork = await db.get('SELECT 1')  // 让"不存在"也走 db 查询
  
  if (!session || session.tenantId !== tenantId) {
    return 404  // 不存在 / 越权 都返回 404
  }
  return 200
}
```

#### D2: Quota 共享导致跨 tenant DoS

**每 tenant 独立 quota counter**（不共享池）：

```ts
class Tenant {
  private quota: QuotaTracker  // ← per-tenant 独立
}

// 拒绝某 tenant 不影响其他 tenant
```

**全局 fallback**：daemon 也有总配额（防止 tenant 总和打爆 daemon）：

```ts
class DaemonQuota {
  private totalLlmTokensPerHour: number = 10_000_000
  private toolCallsPerHour: number = 50_000
}
```

#### D3: Audit log 跨 tenant 读

```ts
// audit log API 只允许读自己 tenant 的日志
app.get('/audit', authMiddleware, async (c) => {
  const tenantId = Instance.current().tenantId
  
  // ⚠️ 关键：必须 WHERE tenant_id 过滤
  const logs = await db.all(`
    SELECT * FROM audit_log
    WHERE tenant_id = ?           -- ← 不可缺
    ORDER BY timestamp DESC LIMIT 100
  `, [tenantId])
  
  return c.json(logs)
})

// admin API（仅 root tenant 能用）
app.get('/admin/audit', adminAuthMiddleware, async (c) => {
  // 校验 tenant 是 admin role
  if (!Instance.current().tenant.isAdmin) return c.json({ error: 'forbidden' }, 403)
  // ... 跨 tenant 查询
})
```

#### D4: Resource exhaustion

每 tenant 限制：
- **MCP server 数**：每 workspace 最多 10 个 MCP server
- **并发 session 数**：每 tenant 最多 50 个 active session
- **Background task 数**：每 tenant 最多 20 个并发 background task
- **WebSocket 连接数**：每 token 最多 5 个 SSE/WS 连接

```ts
class Tenant {
  async tryAcquireSession(): boolean {
    if (this.sessions.size >= this.config.maxConcurrentSessions) {
      return false  // 拒绝创建新 session
    }
    return true
  }
}
```

## 四、防御纵深（Defense in Depth）汇总

每个攻击向量对应的防御层：

| # | 攻击 | 第 1 层 | 第 2 层 | 第 3 层 | 第 4 层 | 第 5 层 |
|---|---|:---:|:---:|:---:|:---:|:---:|
| A1 Token 泄漏 | ✓ short-lived + rotation | | | | ✓ anomaly detection |
| A2 Token 替换 | | | ✓ ACL middleware | | |
| A3 Workspace 越权 | | ✓ workspace_id binding | ✓ belongsToTenant() | | ✓ audit |
| A4 Session 猜测 | | | | ✓ unguessable ID | |
| F1 Path traversal | | ✓ realpath + isWithin | | | |
| F2 Symlink | | ✓ realpath + lstat | | | |
| F3 Mount escape | | ✓ sandbox capability drop | | | |
| F4 Hard link | | ✓ EXDEV / per-tenant mount | | | |
| F5 Race condition | | ✓ SQLite UNIQUE | | | |
| C1 Cache key 碰撞 | | ✓ §4 session-scoped | | | |
| C2 MCP state 泄漏 | | ✓ §3 per-workspace | | | |
| C3 Permission cache | | ✓ tenant_id WHERE | ✓ Instance.tenantId | | |
| C4 Bus event 泄漏 | | | ✓ tenant-scoped bus | | |
| S1 Sandbox escape | | ✓ capability drop + seccomp + AppArmor | | | |
| S2 cgroup 绕过 | | ✓ pids.max | | | |
| S3 Network ns | | ✓ NetworkPolicy | | | |
| S4 共享 /tmp | | ✓ tmpfs per sandbox | | | |
| D1 Timing | | | ✓ timing-safe response | | |
| D2 Quota DoS | | | ✓ per-tenant quota + daemon cap | | |
| D3 Audit 跨读 | | | ✓ WHERE tenant_id | ✓ admin role check | ✓ audit |
| D4 Resource | | | ✓ per-tenant limits | | |

## 五、安全测试清单（Red Team 场景）

落地前必须通过以下渗透测试：

### 5.1 Auth 层

- [ ] 用 tenant A token 请求 `POST /workspace/ws-of-tenant-B/session` → 期望 404 / 403
- [ ] 用 tenant A token 请求 `POST /session/sess-of-tenant-B/prompt` → 期望 404 (timing-safe)
- [ ] 不带 token 请求任何 endpoint → 期望 401
- [ ] 用 expired / revoked token → 期望 401
- [ ] 用 SQL 注入字符 `' OR 1=1 --` 作为 workspaceId → 期望 invalid 拒绝（zod schema 校验）

### 5.2 Filesystem 层

- [ ] `read_file(path: '../../../etc/passwd')` → 期望 ErrorPathOutsideWorkspace
- [ ] `read_file(path: '/etc/passwd')`（绝对路径）→ 期望同上
- [ ] 在 workspace 内 `ln -s /tenants/other-tenant/secret /workspace/link` 然后 `read_file('link')` → 期望 realpath 后越界拒绝
- [ ] `bash(cmd: 'mount -o bind /tenants/other /workspace/mounted')` → sandbox 内拒绝（CAP_SYS_ADMIN dropped）
- [ ] 同时两个 client 用相同目录 `POST /workspace { directory: '/path' }` → 期望仅一个成功，另一个 conflict

### 5.3 Cache / State 层

- [ ] tenant A 在 workspace W1 设 `alwaysAllow: 'Bash(npm test)'` → tenant B 在另一 workspace 不应继承此决策
- [ ] tenant A 订阅 `GET /session/:id/events` 后用 ID 替换 → 期望被中断或拒绝
- [ ] FileReadCache 在 session A 的 readEntry，session B 不应能 trigger PR#3774 prior-read 守卫为 hit-fresh

### 5.4 Sandbox 层

- [ ] sandbox 内运行 `mount` / `unshare` / `nsenter` → 期望 EPERM
- [ ] sandbox 内 `fork bomb`（`:(){ :|:& };:`）→ 期望 cgroup pids.max 限制
- [ ] sandbox 内 `dd if=/dev/zero of=/tmp/big.bin bs=1M count=10000` → 期望 cgroup memory / disk quota 限制
- [ ] sandbox 内 `cat /proc/<daemon-pid>/maps` → 期望 PID namespace 隔离 / EPERM
- [ ] sandbox 内 `nc -l 8080`（监听端口）→ 期望 NetworkPolicy 拒绝外部连接

### 5.5 Timing / DoS 层

- [ ] 测量"不存在的 session ID" vs "存在但越权 session ID" 的响应时间差 → 应 < 1ms 差异
- [ ] tenant A 跑爆 quota 后，tenant B 仍能正常使用 → ✓
- [ ] `/audit` GET 只返回当前 tenant 的日志 → 不能用 query param 跨 tenant 查
- [ ] tenant A 起 100 个并发 session → 应在第 51 个被拒（per-tenant max=50）

### 5.6 端到端

- [ ] 模拟"恶意 tenant" 完整攻击链：申请 token → 注册 workspace → 试 16 个攻击向量 → 期望全部拒绝 + audit log 记录
- [ ] Daemon 重启后所有 ACL 持久化生效（不会有"刚启动短暂期间"的安全空白）

## 六、与已有设计的协调

| 已有设计 | 安全加成 |
|---|---|
| 决策 §1 sessionScope: 'thread'（多租户模式）| 严格隔离 mode 已经定义，多 tenant 必用此 scope |
| 决策 §3 MCP per-workspace | 天然防御 C2 (MCP state 泄漏) |
| 决策 §4 FileReadCache per-session | 天然防御 C1 (cache key 碰撞) |
| 决策 §5 Permission flow PR#3723 | 加 tenant 第 5 mode 后扩展防御 C3 |
| 决策 §6 fan-out 多 client 同 session | session 内多 client 都属同 tenant，不存在跨租户问题 |
| §7 bearer token | 直接 scaling 到多 token + ACL |
| §11 ShellSandbox interface | 4 种实现各自隔离强度梯度，根据 tenant tier 选 |

## 七、推荐实施顺序

```
Stage 4 (多租户) 必做的 16 项安全防御：
  ├─ A1-A4 Auth/ACL 层（最优先）：token 强随机 + ACL middleware + unguessable ID
  ├─ F1-F2 Path traversal + symlink（基础）
  ├─ F5 Workspace race condition (SQLite UNIQUE)
  ├─ C1-C4 Cache/state 层（依赖 §4 / §3 决策已天然防御）
  ├─ D1 Timing-safe response
  ├─ D3 Audit log WHERE tenant_id
  └─ D4 Per-tenant resource limits

Stage 5 (sandbox) 加的 5 项：
  ├─ F3-F4 Mount / hard link 防御（依赖 sandbox capability drop）
  ├─ S1-S4 Sandbox escape / cgroups / network / tmp 隔离

Stage 6 (SaaS) 加的:
  ├─ A1 Token rotation + anomaly detection
  ├─ Container 严格 capability drop + AppArmor / SELinux
  └─ 红队渗透测试基线
```

## 八、与 OWASP Top 10 的映射

本章防御覆盖 OWASP Top 10 (2021) 中的多个类别：

| OWASP | 本章覆盖 |
|---|---|
| A01 Broken Access Control | A1-A4 / D3 / 第 3 层 ACL |
| A02 Cryptographic Failures | A1 token 加密 / A4 unguessable ID |
| A03 Injection | F1 path / SQL via zod |
| A05 Security Misconfiguration | S1-S4 / 默认 0.0.0.0 拒绝启动（§07）|
| A07 Identification & Auth Failures | A1-A4 整章 |
| A08 Software & Data Integrity Failures | F2 symlink / F4 hard link / C3 cache |
| A09 Logging & Monitoring Failures | 第 5 层 audit / anomaly detection |

## 九、一句话总结

**多租户水平越权防御靠 5 层纵深 + 17 个具体攻击向量的逐项加固，关键 4 条原则：**
1. **不信任客户端 ID**——服务端必须通过 SQLite `tenant_id` WHERE 过滤所有查询
2. **不可猜测 ID**——所有面向客户端的 ID 用 ≥256 bit cryptographic random
3. **timing-safe 响应**——不存在和越权返回相同 status + 相同延迟
4. **失败默认 deny + audit**——任何不确定都拒绝并记录

**当前设计的几个决策（§1 sessionScope: 'thread' / §3 MCP per-workspace / §4 FileReadCache per-session / §5 PR#3723 mode-based / §11 ShellSandbox interface）天然提供了多个攻击向量的防御**——不是为了多租户专门加的，但落地多租户时这些决策会成为 free lunch。

---

[← 回到 README](./README.md)
