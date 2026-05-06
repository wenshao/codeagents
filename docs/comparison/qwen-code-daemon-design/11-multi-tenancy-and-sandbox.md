# 11 — 多租户与 Shell 沙箱

> [← 上一篇：协议兼容性](./10-protocol-compatibility.md) · [回到 README](./README.md)

> 当前设计（Stage 1-3）针对单租户。本章评估**多租户 + Shell 沙箱**的演进路径——结论：核心抽象已为多租户预留（Stage 4 是 soft launch），shell sandbox 需要 Stage 5 单独工程投入。

## 一、TL;DR

| Level | 内容 | 工作量 | 适合 |
|---|---|---|---|
| **Level 1** | 单租户 daemon（当前 Stage 1-3）| —— | 个人开发 / 小团队信任部署 |
| **Level 2** | 多租户共 daemon 进程 + ACL + quota | ~1-2 周 / 1 人 | 同公司团队（trusted multi-user）|
| **Level 3** | + Shell 沙箱（OS user / namespace / container）| ~2-3 周 / 1 人 | 半信任多用户（学校 / 大型团队 / consulting）|
| **Level 4** | 完整 SaaS（每 tenant 独立 daemon worker + OIDC + quota engine + Prometheus）| ~1-2 月 / 2-3 人 | 完全不信任的 SaaS 部署 |

**关键判断**：当前设计**核心抽象已为多租户预留**——Workspace 作为基础抽象、AsyncLocalStorage `Instance` 上下文、PR#3723 mode-based permission flow、per-workspace MCP/LSP 隔离等设计都允许 soft launch 到 Level 2。Level 3 是显著但可达的工程投入。Level 4 是产品级 SaaS 工作。

## 二、4 个演进 Level

### Level 1：单租户 daemon（当前设计）

```
qwen daemon
  ├─ token: env QWEN_SERVER_TOKEN
  ├─ Workspace A
  ├─ Workspace B
  └─ shell 工具：spawn(cmd, { cwd })  ← 跑 daemon 进程权限
```

适合：个人开发者、本地 IDE 集成、小团队信任部署。

### Level 2：多租户共 daemon 进程

```
qwen daemon
  ├─ Tenant alice
  │   ├─ tokens: ['bear-xxx']
  │   ├─ workspaces: ['ws-alice-*']
  │   ├─ quota: { llmTokensPerDay: 1M, toolCallsPerHour: 500 }
  │   └─ Workspace ws-alice-A / B
  ├─ Tenant bob
  │   ├─ tokens: ['bear-yyy']
  │   ├─ workspaces: ['ws-bob-only']
  │   ├─ quota: { llmTokensPerDay: 100K, toolCallsPerHour: 100 }
  │   └─ Workspace ws-bob-only
  └─ Shell 工具：spawn(cmd, { cwd })  ← 仍跑 daemon 权限 ❌
```

**完成的隔离**：
- ✓ Auth: per-tenant token，跨 tenant 不可访问
- ✓ Workspace ACL: tenant 只能访问 allowlist 的 workspace
- ✓ Resource quota: per-tenant LLM token + tool call rate
- ✓ Audit log: per-tenant 操作日志
- ✓ MCP/LSP/FileReadCache 已经按 workspace 边界自然隔离

**未隔离**：
- ❌ Shell 命令：tenant 的 `bash` / `monitor` 工具调用跑 daemon 进程权限——可能读全机文件、跨 tenant 看进程
- ❌ 文件路径：tenant 用 `../../../etc/passwd` 仍可能突破 workspace 边界（取决于 workspace 路径处理）

**适合**：信任度高的多用户（同公司团队、internal hackathon），不适合 untrusted SaaS。

### Level 3：+ Shell 沙箱

```
qwen daemon
  ├─ Tenant abstraction (Level 2)
  └─ Shell 工具：sandbox.spawn(cmd, opts)  ← 通过 sandbox dispatcher
       ├─ NoSandbox        (Level 1 兼容)
       ├─ OsUserSandbox    (setuid/setgid)
       ├─ NamespaceSandbox (Linux unshare PID/mount/net)
       └─ ContainerSandbox (Docker / Podman exec)
```

详见 [§五 Shell 沙箱设计](#五shell-沙箱方案设计)。

**适合**：半信任多用户（学校、大型团队、consulting）。**不适合**完全不信任的 SaaS（仍共 daemon 进程，应用层 bug 会跨 tenant）。

### Level 4：完整 SaaS

```
k8s cluster
  ├─ Pod: qwen-daemon-tenant-alice  (独立进程)
  │   └─ alice 的所有 workspaces + sessions
  ├─ Pod: qwen-daemon-tenant-bob    (独立进程)
  │   └─ bob 的所有 workspaces + sessions
  ├─ Pod: qwen-router (sticky session 入口)
  ├─ Pod: redis-state (共享配置 / quota counters)
  ├─ Pod: postgres (持久化 sessions / audit logs)
  └─ Pod: prometheus / grafana
```

**完成的隔离**：
- ✓ daemon 进程级隔离（每 tenant 独立 daemon worker，崩溃不传染）
- ✓ k8s namespace 资源限制
- ✓ Container 网络策略
- ✓ Per-tenant SLO + Prometheus metrics
- ✓ OIDC / SSO 企业认证

**适合**：公开 SaaS、企业 production 部署、跨地理区域多租户。

## 三、当前设计为多租户预留的"软兼容"点

回顾本系列已经做出的、为多租户预留的关键决策：

| 决策 | 多租户扩展时的作用 |
|---|---|
| **§1 sessionScope: 'thread'** | 严格隔离 mode 已经定义，多租户用此 scope |
| **§2 单 daemon 进程**（最终决策）| Level 2/3 仍用此模式；Level 4 升级为 daemon-pool |
| **§3 MCP per-workspace** | MCP 状态天然按 workspace 边界，跨 tenant 不会泄漏 |
| **§4 FileReadCache per-session** | session 内私有，跨 tenant 不会泄漏（前提：session ID 不被猜中）|
| **§5 PR#3723 permission flow mode-based** | 已支持 4 mode，加 'multi-tenant' 第 5 mode 即可 |
| **§7 bearer token + 应用层权限流** | Stage 3 已规划"多 token + workspace allowlist" |
| **§8 Stage 3 评估项** | 已列 "多 token + workspace allowlist + 企业认证 OIDC / SSO" |

**结论**：Level 2 是 **soft launch**——架构骨架已经为此准备好，主要是补 Tenant 抽象 + ACL + quota 这些上层组件。

## 四、Tenant 抽象层（Stage 4 设计草案）

### 4.1 Tenant class

```ts
// packages/server/src/tenant/Tenant.ts (新建)
export class Tenant {
  id: string                          // tenant-id（与 token 关联）
  tokens: Set<string>                 // 一个 tenant 可有多个 token（CI / 用户 / SDK）
  workspaceAllowlist: string[]        // glob 模式，如 ['ws-alice-*']
  
  workspaces: Map<string, Workspace>  // 当前 active 的 workspaces
  
  quota: QuotaTracker                 // LLM tokens + tool calls 配额
  audit: AuditLog                     // per-tenant 操作日志
  
  permissionDefaults: PermissionConfig // tenant 级默认权限策略
  sandboxFactory: () => ShellSandbox   // 见 §五
  
  // Lifecycle
  async start() { /* lazy 初始化 */ }
  async dispose() { /* 关闭所有 workspace */ }
}
```

### 4.2 InstanceContext 加 tenantId

```ts
// packages/core/src/util/instance-context.ts (在 §05 已设计基础上扩展)
export interface InstanceContext {
  tenantId: string                    // ← 新增（Level 2+）
  workspaceId: string
  directory: string
  worktree: string
  sessionId?: string
  clientId?: string
}

// 所有 Instance.directory / Instance.workspaceId 等 getter 自动通过 AsyncLocalStorage 取到当前请求的 tenantId
```

### 4.3 Auth + ACL middleware

```ts
// packages/server/src/middleware/auth.ts
export const authMiddleware = async (c, next) => {
  if (c.req.path === '/health') return next()
  
  const token = c.req.header('Authorization')?.slice(7)
  const tenant = tokenToTenant.get(token)
  if (!tenant) return c.json({ error: 'unauthorized' }, 401)
  
  // ACL: workspace 越权检查
  const wsId = c.req.param('workspaceId') ?? c.req.header('x-qwen-workspace')
  if (wsId && !matchesAllowlist(wsId, tenant.workspaceAllowlist)) {
    return c.json({ error: 'workspace forbidden' }, 403)
  }
  
  // Quota 检查
  if (tenant.quota.toolCallsPerHourExceeded()) {
    return c.json({ error: 'rate limited' }, 429)
  }
  
  // 写 audit log
  tenant.audit.log({ method: c.req.method, path: c.req.path, ip: c.req.header('x-real-ip') })
  
  return Instance.provide({
    tenantId: tenant.id,
    workspaceId: wsId,
    ...
  }, next)
}
```

### 4.4 Tenant 配置（settings.json）

```json
{
  "daemon": {
    "tenants": [
      {
        "id": "tenant-alice",
        "tokens": ["bear-alice-xxx"],
        "workspaceAllowlist": ["ws-alice-*"],
        "quota": {
          "llmTokensPerDay": 1000000,
          "toolCallsPerHour": 500,
          "storageBytes": 10737418240
        },
        "permissionMode": "ask-on-edit",
        "sandboxType": "namespace"
      },
      {
        "id": "tenant-bob",
        "tokens": ["bear-bob-yyy"],
        "workspaceAllowlist": ["ws-bob-only"],
        "quota": {
          "llmTokensPerDay": 100000,
          "toolCallsPerHour": 100
        },
        "permissionMode": "yolo",
        "sandboxType": "container"
      }
    ]
  }
}
```

### 4.5 Permission flow 第 5 mode

```ts
// 复用 PR#3723 evaluatePermissionFlow()，加新 mode
type ExecutionMode =
  | 'interactive'
  | 'non-interactive'
  | 'acp'
  | 'daemon-http'
  | 'daemon-multi-tenant'   // ← 新增 Level 2+

// daemon-multi-tenant mode 的特殊处理
function evaluatePermissionFlow(tool, ctx) {
  if (ctx.mode === 'daemon-multi-tenant') {
    // 1. tenant.permissionDefaults override 用户决策
    // 2. quota 检查（拒绝超额）
    // 3. workspace ACL 二次验证
    // 4. fall through to standard L3→L4 evaluation
  }
  // ...
}
```

### 4.6 Quota engine

```ts
class QuotaTracker {
  private llmTokensUsed: Map<string, number>   // per-day
  private toolCalls: Map<string, number[]>      // sliding window per-hour
  
  // 调用 LLM 前检查
  checkLlmTokensAvailable(estimated: number): boolean {
    const today = currentDay()
    const used = this.llmTokensUsed.get(today) ?? 0
    return used + estimated <= this.tenant.quota.llmTokensPerDay
  }
  
  // 工具调用频率
  checkToolCallRate(): boolean {
    const calls = this.toolCalls.get(currentHourKey()) ?? []
    return calls.length < this.tenant.quota.toolCallsPerHour
  }
  
  recordLlmTokens(tokens: number) { ... }
  recordToolCall() { ... }
  
  // 持久化（重启后恢复）
  async save() { /* SQLite */ }
}
```

### 4.7 Audit log schema

```sql
CREATE TABLE audit_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  tenant_id TEXT NOT NULL,
  timestamp INTEGER NOT NULL,
  client_ip TEXT,
  method TEXT NOT NULL,
  path TEXT NOT NULL,
  workspace_id TEXT,
  session_id TEXT,
  tool_name TEXT,
  decision TEXT,           -- 'allow' / 'deny' / 'ask-resolved-yes' / ...
  details TEXT             -- JSON blob 含 tool args / response code
);
CREATE INDEX idx_audit_tenant_ts ON audit_log(tenant_id, timestamp);
```

## 五、Shell 沙箱方案设计

shell 工具是多租户**最危险的攻击面**。当前 `spawn(cmd, { cwd })` 跑 daemon 进程权限，多租户场景必须加 sandbox。

### 5.1 5 种沙箱方案对比

| 方案 | 隔离级别 | 启动开销 | 复杂度 | 平台 | 适合 |
|---|---|:---:|:---:|---|---|
| **① OS user 切换 (setuid/setgid)** | 文件系统权限 + 进程独立 | <10ms | 低 | Unix | Level 2 MVP |
| **② Linux namespace (PID/mount/net)** | 完整 namespace 隔离 | ~50-100ms | 中 | Linux only | **Level 3 推荐** |
| **③ rootless container (Podman)** | 完整 container 隔离 | 200-500ms | 中 | Linux+macOS | Level 3 alternative |
| **④ Docker 容器** | 完整隔离 + 跨平台 | 500-2000ms | 高 | 跨平台 | Level 4 |
| **⑤ WASM/V8 isolate** | syscall 完全屏蔽 | <50ms | 极高（兼容性差）| 跨平台 | 实验性，不推荐 |

### 5.2 ShellSandbox 抽象接口

```ts
// packages/core/src/tools/bash/sandbox.ts (新建)
export interface ShellSandbox {
  spawn(cmd: string, opts: SandboxSpawnOpts): Promise<SandboxedProcess>
  dispose(): Promise<void>
}

interface SandboxSpawnOpts {
  cwd: string
  env: Record<string, string>
  timeout?: number
  stdin?: string
}

interface SandboxedProcess {
  stdout: Readable
  stderr: Readable
  exitCode: Promise<number>
  kill(signal?: string): void
}

// 实现矩阵
class NoSandbox implements ShellSandbox        // Level 1（单租户兼容）
class OsUserSandbox implements ShellSandbox    // Level 2 MVP
class NamespaceSandbox implements ShellSandbox // Level 3 推荐
class ContainerSandbox implements ShellSandbox // Level 3+/4
```

### 5.3 OS user 切换方案（Level 2 MVP）

**前置**：daemon 跑 root（或具备 `CAP_SETUID` capability），每 tenant 注册一个 unprivileged user。

```ts
class OsUserSandbox implements ShellSandbox {
  constructor(private uid: number, private gid: number) {}
  
  async spawn(cmd: string, opts: SandboxSpawnOpts) {
    const child = spawn(cmd, {
      cwd: opts.cwd,
      env: this.scrubEnv(opts.env),
      uid: this.uid,                  // setuid
      gid: this.gid,                  // setgid
      detached: false,
      shell: '/bin/bash',
    })
    
    return wrapAsSandboxedProcess(child)
  }
  
  private scrubEnv(env: Record<string, string>) {
    // 仿 Claude Code v2.1.98 env scrub
    const allowlist = new Set(['PATH', 'HOME', 'LANG', 'SHELL', 'USER'])
    const lcRe = /^LC_/
    return Object.fromEntries(
      Object.entries(env).filter(([k]) => allowlist.has(k) || lcRe.test(k))
    )
  }
  
  async dispose() { /* nothing to cleanup */ }
}
```

**隔离效果**：
- ✓ 文件系统权限（tenant 不能写其他 tenant 的 home）
- ✓ 进程信号无法跨 user 发送
- ✓ Resource limit（rlimit）per-user
- ❌ 共享 PID/network/mount namespace（可见全系统进程列表）
- ❌ 共享 hostname / IPC

**部署要求**：
1. daemon 用 root + dropped capabilities 启动（仅保留 `CAP_SETUID`/`CAP_SETGID`）
2. 每 tenant 系统层创建 unprivileged user（`useradd qwen-tenant-alice`）
3. workspace 目录权限设置 tenant user owns

### 5.4 Linux namespace 方案（Level 3 推荐 · 与 Claude Code v2.1.98 对齐）

```ts
class NamespaceSandbox implements ShellSandbox {
  constructor(
    private cgroupPath: string,    // cgroup v2 子目录
    private maxMemory: string,      // '2G'
    private maxCpuPercent: number,  // 100 = 1 core
  ) {}
  
  async spawn(cmd: string, opts: SandboxSpawnOpts) {
    // unshare 新建 PID + mount + net + UTS + IPC namespace
    const child = spawn('unshare', [
      '--pid', '--fork',          // PID namespace（看不到其他 tenant 进程）
      '--mount-proc',              // 新 /proc
      '--mount',                   // mount namespace（独立 mount table）
      '--net',                     // network namespace（无外网，需 bridge 才能访问）
      '--uts',                     // hostname 隔离
      '--ipc',                     // System V IPC 隔离
      'bash', '-c', cmd,
    ], {
      cwd: opts.cwd,
      env: this.scrubEnv(opts.env),
    })
    
    // 进 cgroup（CPU + memory 限制）
    await this.attachToCgroup(child.pid!)
    
    return wrapAsSandboxedProcess(child)
  }
  
  private async attachToCgroup(pid: number) {
    await fs.appendFile(`${this.cgroupPath}/cgroup.procs`, `${pid}\n`)
  }
}
```

**与 Claude Code v2.1.98 对齐**：codeagents 报告 [P2 item-42](../qwen-code-improvement-report-p2-stability.md#item-42) 描述 Claude Code 的 "Linux PID namespace + env scrub + SCRIPT_CAPS"——完全同思路。Qwen 推 Stage 5 时直接对齐 Claude 设计。

**额外建议**：
- `seccomp-bpf` 过滤危险 syscall（`ptrace` / `mount` / `unshare` 嵌套等）
- cgroups v2 加 IO 限制 + memory.swap.max 防止 OOM 导致整 daemon 卡死

### 5.5 Container 方案（Level 4）

```ts
class ContainerSandbox implements ShellSandbox {
  private containerId: string
  
  async start(tenant: Tenant) {
    // 每 tenant 一个 long-running container
    this.containerId = await docker.run('qwen-tenant-runtime:latest', {
      mountSrc: tenant.workspaceRoot,
      mountDst: '/workspace',
      cpuLimit: '1.0',
      memLimit: '2g',
      networkMode: `tenant-bridge-${tenant.id}`,  // 仅访问允许服务
      labels: { tenant: tenant.id },
    })
  }
  
  async spawn(cmd: string, opts: SandboxSpawnOpts) {
    return docker.exec(this.containerId, ['bash', '-c', cmd], {
      cwd: this.translatePath(opts.cwd),  // /workspace/repo-a
      env: this.scrubEnv(opts.env),
    })
  }
  
  async dispose() {
    await docker.kill(this.containerId)
  }
}
```

**优点**：跨平台（Linux + macOS）+ 完整隔离 + 网络限制 + image 复用 + k8s native
**缺点**：
- 启动开销大（500-2000ms 首次 + ~50ms exec）
- 文件挂载映射复杂
- macOS/Windows 的 Docker 是 VM（更慢）
- 需要 Docker daemon 或 Podman 运行时

适合 SaaS production，不适合 self-host 场景。

### 5.6 Sandbox 选择逻辑

```ts
// 按 tenant.tier 决定 sandbox 类型
function createSandbox(tenant: Tenant): ShellSandbox {
  const type = tenant.config.sandboxType ?? 'os-user'
  
  switch (type) {
    case 'none':
      // 仅 Level 1 兼容性，多租户严禁用
      if (isMultiTenantMode()) throw new Error('NoSandbox not allowed in multi-tenant mode')
      return new NoSandbox()
    
    case 'os-user':
      return new OsUserSandbox(tenant.osUid, tenant.osGid)
    
    case 'namespace':
      if (process.platform !== 'linux') {
        log.warn('namespace sandbox requires Linux, falling back to os-user')
        return new OsUserSandbox(tenant.osUid, tenant.osGid)
      }
      return new NamespaceSandbox(...)
    
    case 'container':
      return new ContainerSandbox(...)
    
    case 'remote':
      return new RemoteSandbox(tenant.remoteSandboxConfig)  // 见 §5.7
  }
}
```

### 5.7 远程 sandbox（**daemon 与 shell 不在同一台机器**）

**问题**：在某些场景下，shell 命令应该跑在**与 daemon 不同的物理机器**上：

| 场景 | 理由 |
|---|---|
| **daemon 在控制平面 / shell 在 worker 节点** | k8s native 部署：daemon 是 lightweight controller，shell 调度到 worker pool |
| **平台不匹配** | daemon 在 macOS（Docker for Mac 慢 + 不真正 Linux），shell 必须在 Linux server 才能跑 production-grade build |
| **GPU / 大型 build server** | shell 需要访问特殊硬件（GPU / 大内存 / 高 IO 节点），daemon 进程不应绑定这些机器 |
| **企业合规边界** | shell 必须在 production 同一安全/合规分区内（如 PCI / HIPAA），daemon 在 dev/management 分区 |
| **SaaS 调度** | tenant 的 shell 调度到 cloud-region 同地理位置的 worker 节点（降延迟 + 满足数据驻留法规）|
| **资源弹性** | shell worker 自动扩缩容（k8s HPA），daemon 是 stateful 不容易扩 |

#### 5.7.1 4 种远程 sandbox 实现

| 方案 | 协议 | 启动开销 | 适合 |
|---|---|---|---|
| **SSH-based** | SSH + scp/rsync 传 workspace | 100-300ms | 简单运维场景、中小团队 |
| **gRPC sandbox protocol** | 自定义 gRPC + mTLS | 50-100ms | 自建 sandbox cluster |
| **k8s Job / Pod** | k8s API 创建 ephemeral pod | 1-3s（pod cold start）| 云原生 SaaS |
| **Container runtime over network** | containerd / OCI runtime over TCP | 200-500ms | 企业内部 |

#### 5.7.2 RemoteSandbox 抽象

```ts
// packages/core/src/tools/bash/sandbox/RemoteSandbox.ts
interface RemoteSandboxConfig {
  endpoint: string                         // gRPC / SSH / k8s API URL
  auth: SandboxAuth                        // mTLS cert / SSH key / k8s SA token
  workspaceMount: WorkspaceMount           // 共享 workspace 策略
  region?: string                          // 调度地理位置（SaaS 用）
  resourceProfile: 'small' | 'large' | 'gpu'  // 节点类型
}

type WorkspaceMount =
  | { kind: 'nfs', server: string, path: string }              // 共享 NFS（推荐）
  | { kind: 'rsync-on-spawn' }                                  // 每次 spawn 同步
  | { kind: 'shared-volume', volumeId: string }                 // k8s PVC / cloud volume
  | { kind: 'object-storage', bucket: string, syncStrategy: ... } // S3 / OSS

class RemoteSandbox implements ShellSandbox {
  constructor(private config: RemoteSandboxConfig) {}
  
  async spawn(cmd: string, opts: SandboxSpawnOpts): Promise<SandboxedProcess> {
    // 1. 选 worker（健康检查 + region 匹配 + 负载）
    const worker = await this.selectWorker()
    
    // 2. 确保 workspace 在 worker 可访问
    await this.ensureWorkspaceAvailable(worker, opts.cwd)
    
    // 3. 远程 spawn（gRPC / SSH / k8s API）
    const remoteHandle = await worker.spawnRemote({
      cmd,
      cwd: this.translatePath(opts.cwd, worker),
      env: this.scrubEnv(opts.env),
      timeout: opts.timeout,
    })
    
    // 4. 包装成本地 SandboxedProcess（流式 stdout/stderr 回传）
    return wrapRemoteAsSandboxedProcess(remoteHandle)
  }
  
  async dispose() {
    await this.releaseWorkers()
  }
}
```

#### 5.7.3 关键挑战与解法

##### 挑战 1：Workspace 文件同步

shell sandbox 不能直接看到 daemon 机器上的 workspace 文件。3 种解法：

| 方案 | 适用 | 成本 |
|---|---|---|
| **A. 共享存储（NFS / k8s PVC / S3）**（推荐）| workspace 一开始就放在共享存储，daemon + sandbox 都挂载 | 设置一次，运行时 0 同步开销 |
| B. 每次 spawn 前 rsync | workspace 在 daemon 本地，spawn 时 rsync 到 sandbox + 完成后同步回 | 大 workspace 启动慢（GB 级别 rsync 几秒）|
| C. Object storage with sync strategy | workspace ↔ S3 同步，sandbox 拉 S3 cache | 适合 batch 跑，不适合交互 |

**推荐方案 A**：
```yaml
# k8s 部署示例
volumes:
- name: workspace-storage
  persistentVolumeClaim:
    claimName: tenant-alice-workspace-pvc

# daemon pod
volumeMounts:
- name: workspace-storage
  mountPath: /tenants/alice/workspaces

# sandbox worker pod
volumeMounts:
- name: workspace-storage
  mountPath: /workspace
  # daemon 端 /tenants/alice/workspaces/ws-a/foo.ts
  # sandbox 端 /workspace/foo.ts (按 mount 翻译)
```

##### 挑战 2：实时 stdout/stderr 流式回传

长跑命令（如 `npm test --watch` 或 PR#3684 monitor 模式）需要实时回传输出，不能等命令完成。

**方案**：复用 PR#3684 monitor 的 token-bucket 节流机制，`RemoteSandbox` 内部把远程 stream 转成本地 Readable：

```ts
class RemoteStreamWrapper {
  private grpcStream: GrpcStreamingCall  // 服务端 push stdout 帧
  
  asNodeReadable(): Readable {
    return new Readable({
      read() {
        for await (const chunk of this.grpcStream) {
          if (chunk.type === 'stdout') this.push(chunk.data)
          if (chunk.type === 'exit') this.push(null)
        }
      }
    })
  }
}
```

##### 挑战 3：取消（远程 SIGINT）

```ts
class RemoteSandboxedProcess {
  async kill(signal: string = 'SIGTERM') {
    // 通过 gRPC / API 通知远程 worker 杀进程
    await this.worker.killRemote(this.remotePid, signal)
  }
}
```

需要远程协议支持 `kill` RPC（不是所有 SSH wrapper 都现成支持，要单独加）。

##### 挑战 4：网络可靠性

| 故障模式 | 处理 |
|---|---|
| sandbox worker 离线 | daemon 检测心跳超时 → fail-fast 报错给 LLM（"sandbox unavailable, retry?"）|
| 网络分区 | 命令执行中分区 → daemon 回传 `error: 'network_partition'` + 远程进程超时自杀（worker 端 watchdog）|
| 部分输出已收到 | 把已收到的 stdout 包装成 partial result + error tag，让模型决策是否重试 |

##### 挑战 5：延迟

| 操作 | 本地 | 远程 |
|---|---|---|
| spawn 启动 | <10ms | 50-300ms |
| stdout 首字节 | <10ms | 50-150ms |
| 命令完成回传 | 同步 | 取决于网络 RTT |

**用户体验影响**：交互式开发场景（频繁 ls / cat / 小脚本）远程 sandbox 会有明显延迟。建议：
- **混合模式**：read-only 命令（`ls` / `cat` / `grep`）走本地 sandbox（快），write/risk 命令（`npm install` / `git push` / `bash` ad-hoc）走远程 sandbox（隔离）
- 或：tenant 配置全局选 local 还是 remote

#### 5.7.4 SaaS 部署典型架构

```
┌──────────────────────────────────────────────────────────┐
│ k8s cluster                                               │
│                                                            │
│  Control Plane:                                            │
│  ├─ qwen-daemon-tenant-alice (Pod)   ← 1 daemon per tenant│
│  │   └─ 不直接跑 shell                                     │
│  │                                                         │
│  Worker Pool (auto-scaled):                               │
│  ├─ qwen-sandbox-worker-1 (Pod, GPU)                      │
│  ├─ qwen-sandbox-worker-2 (Pod, GPU)                      │
│  ├─ qwen-sandbox-worker-3 (Pod, large-mem)                │
│  ├─ ...                                                    │
│  └─ qwen-sandbox-worker-N                                  │
│                                                            │
│  Storage:                                                  │
│  ├─ NFS / Ceph: workspace volumes                         │
│  ├─ Postgres: sessions / audit                            │
│  └─ Redis: quota counters / session locks                  │
│                                                            │
│  daemon → gRPC → sandbox worker (跨 pod)                   │
│  workspace 通过 PVC 在 daemon + sandbox 间共享              │
└──────────────────────────────────────────────────────────┘
```

#### 5.7.5 与本地 sandbox 的渐进路线

```
Stage 5 (本地 sandbox):
  └─ Bash tool 走 sandbox interface (NoSandbox / OsUser / Namespace / Container 4 选一)

Stage 5.5 (本地 + 远程并存):
  └─ + RemoteSandbox 实现（仅 SSH-based，最简单）
     用于"我想把 shell 跑到办公室服务器"的个人场景

Stage 6 (SaaS 远程优先):
  └─ 默认 RemoteSandbox + k8s 调度
     │ 本地 sandbox 仅 self-host 模式保留
     └─ Mixed mode: 简单命令走本地，复杂命令走远程
```

#### 5.7.6 与现有 PR 的协调

| PR | 与远程 sandbox 的关系 |
|---|---|
| PR#3684 Phase C event monitor | monitor 工具同样需要走 sandbox 抽象——远程 sandbox 实现可复用 |
| PR#3471 task_stop / send_message | 远程进程的 cancel 通过 `task_stop` 工具入口 → RemoteSandbox.kill() RPC |
| PR#3717 FileReadCache | 与远程 sandbox **正交**：FileReadCache 在 daemon 进程内，sandbox 是子进程层；但 sandbox 写文件后 daemon 的 cache invalidation 必须考虑（Stage 5+ audit）|
| PR#3820 unescape shell-escaped paths | 远程 sandbox 同样需要处理（path translation 时 escape 处理）|
| PR#3818 MCP coalesce | 不影响（MCP 仍在 daemon 内）|

#### 5.7.7 隔离强度对比（含远程方案）

| 方案 | 隔离强度 | 启动开销 | 跨平台 |
|---|---|---|---|
| OS user | ★★ | <10ms | Unix |
| Namespace | ★★★ | 50-100ms | Linux |
| Local Container | ★★★★ | 500-2000ms | 跨平台 |
| **Remote SSH** | ★★★★（机器隔离）| 100-300ms | 跨平台 |
| **Remote gRPC + Container** | ★★★★★（机器 + 容器双隔离）| 200-500ms | 云原生 |
| **Remote k8s Job** | ★★★★★ | 1-3s | k8s |

**推荐 SaaS 部署**：Remote gRPC + Container（双重隔离）—— shell 命令在远程 worker 节点的 container 内跑，提供机器级 + 进程级双隔离。

#### 5.7.8 一句话

**远程 sandbox 是 Stage 6 SaaS 部署的关键架构** —— 本地 sandbox 适合 self-host 和小团队，但生产 SaaS 必须把 shell 调度到独立 worker pool（隔离 + 弹性 + 合规）。`ShellSandbox` interface 在 Stage 5 设计时就抽象好，Stage 5.5 加 `RemoteSandbox` 实现，Stage 6 默认走远程 + k8s 调度。

## 六、Monitor tool 也需要沙箱

PR#3684 引入的 `Monitor` 工具（Phase C event monitor）也是 spawn 长跑 shell 进程——多租户下同样需要走 sandbox：

```ts
// 现有 packages/core/src/tools/monitor.ts (PR#3684)
const child = spawn(cmd, { cwd, env })

// 改造为
const sandbox = Instance.current().tenant.sandboxFactory()
const child = await sandbox.spawn(cmd, { cwd, env })
```

token-bucket throttling、`MonitorRegistry` 等机制不变。

## 七、Stage 4-6 路线图（在已有 Stage 1-3 之后）

```
[已设计 Stage 1-3]
└─ Stage 1 (~1 周) http-bridge MVP
└─ Stage 2 (~3 周) 原生 daemon
└─ Stage 3 (~1.5-2 月) 对标 OpenCode

[新增 Stage 4-6]
├─ Stage 4 (~1-2 周) 多租户共 daemon 进程
│   ├─ Tenant abstraction（packages/server/src/tenant/）
│   ├─ AsyncLocalStorage InstanceContext 加 tenantId 字段
│   ├─ Auth middleware 多 token + ACL
│   ├─ QuotaTracker（LLM tokens / tool call rate）
│   ├─ AuditLog（SQLite per-tenant 操作日志）
│   └─ Permission flow 第 5 mode 'daemon-multi-tenant'
│
├─ Stage 5 (~2-3 周) Shell 沙箱
│   ├─ ShellSandbox interface + 4 实现
│   ├─ Bash tool / Monitor tool 改用 sandbox.spawn()
│   ├─ env scrub allowlist（与 Claude Code v2.1.98 对齐）
│   ├─ cgroups v2 集成（CPU/memory/IO）
│   ├─ seccomp-bpf 危险 syscall 过滤
│   └─ Tenant 配置 sandbox 类型（os-user / namespace / container）
│
└─ Stage 6 (~1-2 月) 完整 SaaS
    ├─ Container runtime（每 tenant 独立 daemon worker / k8s pod）
    ├─ k8s helm chart + sticky session + Redis state
    ├─ OIDC / OAuth 2.0 / SSO（替换 simple bearer token）
    ├─ Postgres for sessions/audit（替换 SQLite，支持多 daemon 实例）
    ├─ Prometheus metrics + per-tenant SLO
    ├─ 跨可用区部署文档
    └─ 性能基准（100+ 并发 tenant 验证）
```

## 八、当前设计的"软兼容"audit

为了保证 Stage 4-6 是平滑演进而不是推倒重来，本系列设计文档**已经做了几个软兼容选择**：

| 当前选择 | 软兼容性 |
|---|---|
| Workspace 是基础抽象（不是 Session）| ✅ Tenant 自然加在 Workspace 之上 |
| AsyncLocalStorage `Instance` 上下文 | ✅ 加 tenantId 字段不破坏现有代码 |
| MCP / LSP per-workspace（决策 §3）| ✅ 跨 tenant 隔离天然成立（workspace 边界 ⊆ tenant 边界）|
| FileReadCache per-session（决策 §4）| ✅ 跨 tenant 不共享天然（session 是 workspace 子级）|
| Permission flow mode-based（PR#3723 + 决策 §5）| ✅ 加新 mode 不破坏现有 4 mode |
| `spawn({ cwd })` 显式参数模式（[05-进程模型](./05-process-model.md)）| ✅ 替换为 `sandbox.spawn(cmd, opts)` 调用对称 |
| Bearer token 已经是 ACL 入口（决策 §7）| ✅ 升级到 token 集合 + ACL 自然 |
| Channels SessionRouter 多 channel 路由 | ✅ tenant 是更高层路由维度 |
| ACP zod schema 复用（[04-HTTP API](./04-http-api.md)）| ✅ schema 不变，只是 Hono middleware 多层 ACL |

**结论**：Level 2（多租户 ACL）在当前设计下是 **soft launch**——核心抽象已经支持，主要是补上层 Tenant + ACL + quota 模块；Level 3（shell sandbox）需要**新模块**但不破坏现有架构（Bash tool 内部 dispatch 切换）；Level 4（完整 SaaS）需要**进程模型重构**（决策 §2 的"单 daemon 进程"在 Level 4 升级为"daemon worker pool"，但 application logic 层仍单进程多 session 模式）。

## 九、与 OpenCode / Claude Code 的多租户对比

| 维度 | OpenCode | Claude Code v2.1.98 | Qwen Daemon Level 2-4 |
|---|---|---|---|
| Multi-tenant | ❌ 单租户（个人 dev tool）| ❌ 单用户 CLI | **✓ Stage 4 起支持** |
| Shell sandbox | ❌ 无 | **✓ PID namespace + env scrub + SCRIPT_CAPS** | **Stage 5 与 Claude 对齐** |
| Quota / rate limit | ❌ | ❌ | **Stage 4 加** |
| Audit log | ❌ | log files | **Stage 4 SQLite 持久化** |
| OIDC / SSO | ❌ | ❌ | **Stage 6 加** |
| Container runtime | ❌ | ❌ | **Stage 5+ 支持 Docker/Podman/k8s** |
| k8s deployment | ❌ | ❌ | **Stage 6 helm chart** |

**Qwen daemon 在 Stage 5+ 将成为 5 大 Code Agent 中第一个原生支持企业级多租户部署的开源方案**——这是相对 Claude Code（闭源 + 单用户）和 OpenCode（开源但单租户）的差异化定位。

## 十、关键设计权衡

### 10.1 单进程 vs 多进程（Level 4 边界）

Level 4 的核心问题：是继续 "1 daemon 进程承载多 tenant" 还是 "每 tenant 一个 daemon worker 进程"？

| 选项 | 优点 | 缺点 |
|---|---|---|
| 单进程多 tenant | 资源利用高（共享 LLM client / network 连接池）| OOM/崩溃影响所有 tenant；违反零信任 |
| **每 tenant 一 daemon worker（Stage 6 推荐）** | 进程级隔离 + k8s native + 横向扩展简单 | Container 启动开销 + 每 tenant LLM client 重复初始化 |

Level 4 推荐选 **per-tenant worker**——与 OpenCode "single daemon all sessions" 模式不同——因为完全不信任的 SaaS 必须有进程级隔离。

### 10.2 Sandbox 类型选择

不同 tenant tier 用不同 sandbox：

| Tenant tier | Sandbox |
|---|---|
| Free / 公开试用 | **Container**（最强隔离）|
| Paid / 企业 internal | **Namespace**（性能 + 隔离平衡）|
| Trusted（员工 / CI）| **OS user**（性能优先）|

Tenant 配置 `sandboxType` 决定。

### 10.3 Quota 边界

Quota 应该 per-tenant 还是 per-user？

- 推荐 **per-tenant**（一个 tenant 可有多个 user / token，共享 quota pool）
- 例外：tenant 内部可以再做 sub-quota（如 alice 团队总 quota 1M tokens/day，分给 dev / CI / scripts 各 200K）

## 十一、一句话总结

**当前设计（Stage 1-3）虽针对单租户，但核心架构（Workspace 抽象 + AsyncLocalStorage + per-workspace 资源 + mode-based permission flow + bearer token）已为多租户 soft launch（Stage 4 ~1-2 周）预留。Shell sandbox 在 Stage 5 加入（与 Claude Code v2.1.98 PID namespace 对齐），Stage 6 升级为完整 SaaS（per-tenant daemon worker + k8s + OIDC）。整个 6 阶段路线总投入 ~3-4 个月，Qwen 将成为第一个原生支持企业多租户的开源 Code Agent daemon。**

---

[← 回到 README](./README.md)
