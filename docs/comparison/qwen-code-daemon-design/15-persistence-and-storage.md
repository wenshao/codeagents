# 15 — 持久层与外部存储

> [← 上一篇：实体模型与层级关系](./14-entity-model.md) · [回到 README](./README.md)

> 当前设计在 SQLite + JSONL + 内存的混合栈上工作。本章讨论何时需要引入外部 RDBMS（MySQL / Postgres）、如何抽象 Storage Adapter、与 OpenCode `drizzle-orm` 选型对齐，以及 Stage 6 SaaS 的多 daemon 共享状态架构。

## 一、TL;DR

| Stage | 持久化栈 | 适合场景 |
|---|---|---|
| **Stage 1-3** | **SQLite + JSONL + 内存** | 单 daemon，单/多用户信任部署 |
| **Stage 4-5** | 同上（SQLite WAL 可撑万级 tenant）| 多租户 + sandbox 部署 |
| **Stage 6** | **Storage Adapter 抽象 + Postgres / MySQL** | 多 daemon 实例 / SaaS / 跨 region |

**核心选型**：
- **ORM**：`drizzle-orm`（与 OpenCode 一致 + 同时支持 SQLite/Postgres/MySQL）
- **默认**：SQLite WAL（`better-sqlite3`）—— Stage 1-5 足够
- **Stage 6 推荐**：**Postgres**（JSONB / partial index / array type 对配置存储更友好）
- **Transcript（大 blob）**：**保留 JSONL 文件**（不入 RDBMS，可 S3/OSS 长期归档）
- **配置 settings.json**：**保留文件系统**（YAML/JSON，§16 配置 cascade）

## 二、当前持久化栈（Stage 1-3）

复用 [§14 实体模型](./14-entity-model.md) 的资源所有权层级表：

| 数据 | 存储 | 选型理由 |
|---|---|---|
| Session transcript | JSONL（PR#3739 transcript-first fork resume）| 大 blob 不入 RDBMS，文件追加最快 |
| Permission decisions | SQLite | 频繁查 + 关系型（tenant + workspace + pattern 三键）|
| Audit log | SQLite | 频繁追加 + 按 tenant_id / timestamp 索引 |
| Workspace 元信息 | SQLite | UNIQUE 约束防 race condition（§12 §3.2 F5）|
| Token / Tenant 配置 | settings.json + SQLite mirror | Daemon 启动时从 settings 读 + 运行时 SQLite 增量更新 |
| FileReadCache | 内存（per-session）| 完全瞬时，决策 §4 |
| AsyncLocalStorage Instance | 内存 | 完全瞬时，§05 |
| MCP / LSP server 子进程 | 内存 + 子进程 | 不持久化（重启重新拉起）|

```
┌────────────────────────────────────────────────┐
│ Daemon process                                  │
│                                                  │
│ ┌────────────────────────────────────────┐     │
│ │ 内存层（瞬时）                           │     │
│ │ - FileReadCache                          │     │
│ │ - Session subscribers Set                │     │
│ │ - AsyncLocalStorage Instance             │     │
│ │ - Workspace/Session Map                  │     │
│ └────────────────────────────────────────┘     │
│                                                  │
│ ┌────────────────────────────────────────┐     │
│ │ SQLite 层（结构化数据）                  │     │
│ │ /var/lib/qwen/qwen.db                    │     │
│ │ - permission_decisions                   │     │
│ │ - audit_log                              │     │
│ │ - workspaces                             │     │
│ │ - tokens (Stage 4+)                      │     │
│ │ - background_tasks (meta, 状态)          │     │
│ └────────────────────────────────────────┘     │
│                                                  │
│ ┌────────────────────────────────────────┐     │
│ │ 文件系统层（大 blob / 可读配置）         │     │
│ │ /var/lib/qwen/transcripts/<sid>.jsonl    │     │
│ │ /etc/qwen/daemon.json                    │     │
│ │ /etc/qwen/tenants/<id>.json (Stage 4+)   │     │
│ │ <workspace>/.qwen/settings.json          │     │
│ └────────────────────────────────────────┘     │
└────────────────────────────────────────────────┘
```

## 三、SQLite 选型理由（Stage 1-5 默认）

### 3.1 优点

- **零部署**：embedded，daemon 启动时 open file 即可
- **WAL 模式**：高并发读 + 单写者，足够 daemon 内多 session 并发
- **单文件备份**：`cp qwen.db backup.db` 即可
- **跨平台**：Linux / macOS / Windows 一致
- **drizzle-orm 一线支持**：与 OpenCode 同栈
- **测试友好**：`:memory:` 数据库 + 单元测试快速重置

### 3.2 限制

- **单写者**：所有写串行；高并发写场景（>100 写/秒）会成瓶颈
- **单进程**：daemon 重启时锁定文件（不支持多进程同时写）
- **不支持跨机**：无 replication / clustering
- **大数据量**：超 100GB 性能下降（适合中小 deployment）

### 3.3 适用边界

```
Stage 1-3 单 daemon: SQLite 完全够用
Stage 4 多租户单 daemon: SQLite 撑万级 tenant + 百万级 audit log
Stage 5 + sandbox: 同上
─────────────────────────────────────────────
Stage 6 多 daemon 实例: SQLite 不够，必须升级
```

## 四、何时需要外部 RDBMS

5 个明确触发外部 RDBMS 的场景：

| 触发 | 详细 | 推荐方案 |
|---|---|---|
| **多 daemon 实例（Stage 6 SaaS）** | k8s 部署多 daemon worker pod 共享状态 | Postgres / MySQL + sticky session |
| **跨数据中心 / 灾备** | 主从复制 / 异地容灾 | Postgres streaming replication |
| **企业合规（PII 不落本地）** | 审计日志必须写入 SOC2 合规存储 | 外部 Postgres + TDE 加密 |
| **Analytics（跨 tenant BI 查询）** | 数据分析师查跨 tenant 用量趋势 | Postgres + read replica |
| **超大规模 audit log** | TB 级历史，SQLite 单文件吃不下 | Postgres 分区表 / TimescaleDB |

**反向案例（不需要外部 RDBMS）**：
- 单团队内部 daemon
- self-hosted 小项目
- 离线 / 局域网部署
- 个人开发者本地

## 五、Storage Adapter 抽象设计

### 5.1 Interface

```ts
// packages/server/src/storage/StorageAdapter.ts (Stage 6 新增)
export interface StorageAdapter {
  // 启动 / 关闭
  init(): Promise<void>
  close(): Promise<void>
  
  // Tenant
  tenants: TenantStorage
  
  // Workspace
  workspaces: WorkspaceStorage
  
  // Session 元信息（transcript 走文件）
  sessions: SessionStorage
  
  // Permission decisions
  permissions: PermissionDecisionStorage
  
  // Audit log
  audit: AuditStorage
  
  // Background tasks meta
  tasks: BackgroundTaskStorage
  
  // Health
  ping(): Promise<{ ok: boolean, latencyMs: number }>
}

// 4 个实现
class SqliteAdapter implements StorageAdapter {  // Stage 1-5 默认
  constructor(path: string) { ... }
}
class PostgresAdapter implements StorageAdapter {  // Stage 6 推荐
  constructor(connectionString: string) { ... }
}
class MysqlAdapter implements StorageAdapter {  // Stage 6 可选
  constructor(connectionString: string) { ... }
}
class InMemoryAdapter implements StorageAdapter {  // 单元测试用
  constructor() { ... }
}
```

### 5.2 配置选择

```json
// /etc/qwen/daemon.json
{
  "storage": {
    "type": "sqlite",                        // sqlite | postgres | mysql | memory
    "sqlite": { "path": "/var/lib/qwen/qwen.db" },
    "postgres": {
      "host": "postgres.internal",
      "port": 5432,
      "database": "qwen",
      "user": "qwen",
      "password": "${secret:postgres-pass}",
      "ssl": "require",
      "poolSize": 20
    },
    "mysql": { /* 类似 */ }
  }
}
```

### 5.3 与现有 Qwen Code 协调

Qwen Code 当前用什么？

```bash
$ find /root/git/qwen-code/packages -name "package.json" 2>/dev/null \
  | xargs grep -l "drizzle\|better-sqlite3\|sequelize\|typeorm\|prisma" 2>/dev/null
# (检查现有依赖)
```

如果 Qwen Code 还没有 ORM，daemon 化引入 `drizzle-orm` 是合理选择（与 OpenCode 一致）；如果已有其他 ORM，需评估迁移成本。

## 六、ORM 选型：drizzle-orm

### 6.1 为什么 drizzle

| 标准 | drizzle-orm | TypeORM | Prisma | Sequelize |
|---|---|---|---|---|
| **TypeScript 优先** | ✓ 原生 | ✓ | ✓ | partial |
| **多数据库支持** | ✓ SQLite/PG/MySQL | ✓ | ✓ | ✓ |
| **SQL-like API** | ✓ 写起来像 SQL | OOP | DSL | OOP |
| **Bundle size** | 小 | 大 | 中 | 大 |
| **OpenCode 已用** | ✓ | ✗ | ✗ | ✗ |
| **Bun 兼容** | ✓ | partial | partial | ✓ |
| **drizzle-kit migration** | ✓ | typeorm migrations | prisma migrate | sequelize-cli |

**选择 drizzle-orm 的关键理由**：与 OpenCode 同栈降低生态学习成本（2 个项目共享同一套 schema 模式 / migration 工具）。

### 6.2 跨数据库 schema

```ts
// packages/server/src/storage/schema/sqlite.ts
import { sqliteTable, text, integer, primaryKey, index } from 'drizzle-orm/sqlite-core'

export const permissionDecisions = sqliteTable('permission_decisions', {
  tenantId: text('tenant_id').notNull(),
  workspaceId: text('workspace_id').notNull(),
  pattern: text('pattern').notNull(),
  scope: text('scope').notNull(),              // 'session' | 'workspace' | 'global'
  decision: text('decision').notNull(),         // 'allow' | 'deny'
  expiresAt: integer('expires_at'),             // unix ms, NULL = 永久
}, (t) => ({
  pk: primaryKey({ columns: [t.tenantId, t.workspaceId, t.pattern, t.scope] }),
  idxTenant: index('idx_perm_tenant').on(t.tenantId),
}))

// packages/server/src/storage/schema/postgres.ts (并行版本)
import { pgTable, text, bigint, primaryKey, index } from 'drizzle-orm/pg-core'

export const permissionDecisions = pgTable('permission_decisions', {
  tenantId: text('tenant_id').notNull(),
  workspaceId: text('workspace_id').notNull(),
  pattern: text('pattern').notNull(),
  scope: text('scope').notNull(),
  decision: text('decision').notNull(),
  expiresAt: bigint('expires_at', { mode: 'number' }),
}, (t) => ({
  pk: primaryKey({ columns: [t.tenantId, t.workspaceId, t.pattern, t.scope] }),
  idxTenant: index('idx_perm_tenant').on(t.tenantId),
}))
```

### 6.3 查询 API（跨数据库一致）

```ts
import { drizzle } from 'drizzle-orm/better-sqlite3'  // 或 'drizzle-orm/postgres-js'
import { eq, and } from 'drizzle-orm'

const db = drizzle(connection)

// 跨数据库一致 API
const decisions = await db
  .select()
  .from(permissionDecisions)
  .where(and(
    eq(permissionDecisions.tenantId, tenantId),
    eq(permissionDecisions.workspaceId, workspaceId),
  ))
```

## 七、完整 Schema 设计

### 7.1 核心表

```ts
// 1. Tenants
export const tenants = sqliteTable('tenants', {
  id: text('id').primaryKey(),               // 'tenant-alice'
  name: text('name').notNull(),
  createdAt: integer('created_at').notNull(),
  deletedAt: integer('deleted_at'),
  configRev: integer('config_rev').default(0), // 配置变更计数（hot reload）
})

// 2. Tokens
export const tokens = sqliteTable('tokens', {
  id: text('id').primaryKey(),                // 'tok-xxx'
  tenantId: text('tenant_id').references(() => tenants.id),
  secretHash: text('secret_hash').notNull(),  // bcrypt hash
  scope: text('scope').notNull(),             // JSON array of patterns
  expiresAt: integer('expires_at'),
  createdAt: integer('created_at').notNull(),
  lastUsedAt: integer('last_used_at'),
}, (t) => ({
  idxTenant: index('idx_tokens_tenant').on(t.tenantId),
}))

// 3. Workspaces
export const workspaces = sqliteTable('workspaces', {
  id: text('id').primaryKey(),                // 'ws-xxx' unguessable
  tenantId: text('tenant_id').references(() => tenants.id).notNull(),
  directory: text('directory').notNull(),     // /work/repo-a (real path)
  worktree: text('worktree'),
  createdAt: integer('created_at').notNull(),
  disposedAt: integer('disposed_at'),
}, (t) => ({
  uniqTenantDir: uniqueIndex('uniq_tenant_dir').on(t.tenantId, t.directory),
  idxTenant: index('idx_ws_tenant').on(t.tenantId),
}))

// 4. Sessions（meta only，transcript 走文件）
export const sessions = sqliteTable('sessions', {
  id: text('id').primaryKey(),                // 'sess-xxx' unguessable
  workspaceId: text('workspace_id').references(() => workspaces.id).notNull(),
  transcriptPath: text('transcript_path').notNull(),  // /var/lib/qwen/transcripts/<id>.jsonl
  currentModel: text('current_model'),
  currentMode: text('current_mode'),
  createdAt: integer('created_at').notNull(),
  archivedAt: integer('archived_at'),
  lastActivityAt: integer('last_activity_at').notNull(),
}, (t) => ({
  idxWs: index('idx_sess_ws').on(t.workspaceId),
  idxLastActivity: index('idx_sess_last_activity').on(t.lastActivityAt),
}))

// 5. Permission decisions
export const permissionDecisions = sqliteTable('permission_decisions', {
  tenantId: text('tenant_id').notNull(),
  workspaceId: text('workspace_id').notNull(),
  pattern: text('pattern').notNull(),
  scope: text('scope').notNull(),
  decision: text('decision').notNull(),
  expiresAt: integer('expires_at'),
}, (t) => ({
  pk: primaryKey({ columns: [t.tenantId, t.workspaceId, t.pattern, t.scope] }),
  idxTenant: index('idx_perm_tenant').on(t.tenantId),
}))

// 6. Audit log
export const auditLog = sqliteTable('audit_log', {
  id: integer('id').primaryKey({ autoIncrement: true }),
  tenantId: text('tenant_id').references(() => tenants.id).notNull(),
  timestamp: integer('timestamp').notNull(),
  clientIp: text('client_ip'),
  method: text('method').notNull(),
  path: text('path').notNull(),
  workspaceId: text('workspace_id'),
  sessionId: text('session_id'),
  toolName: text('tool_name'),
  decision: text('decision'),
  details: text('details'),                   // JSON blob
}, (t) => ({
  idxTenantTs: index('idx_audit_tenant_ts').on(t.tenantId, t.timestamp),
}))

// 7. Background tasks (meta only)
export const backgroundTasks = sqliteTable('background_tasks', {
  id: text('id').primaryKey(),
  sessionId: text('session_id').references(() => sessions.id).notNull(),
  kind: text('kind').notNull(),               // 'agent' | 'shell' | 'monitor' | 'dream'
  status: text('status').notNull(),           // 'running' | 'completed' | 'failed' | 'cancelled' | 'paused'
  description: text('description'),
  payload: text('payload'),                    // JSON blob (kind-specific)
  createdAt: integer('created_at').notNull(),
  terminatedAt: integer('terminated_at'),
  exitCode: integer('exit_code'),
  errorMessage: text('error_message'),
}, (t) => ({
  idxSession: index('idx_task_session').on(t.sessionId),
  idxStatus: index('idx_task_status').on(t.status),
}))

// 8. Tenant quotas (per-window counters)
export const tenantQuotas = sqliteTable('tenant_quotas', {
  tenantId: text('tenant_id').references(() => tenants.id).notNull(),
  windowKey: text('window_key').notNull(),    // 'day:2026-05-06' / 'hour:2026-05-06T03'
  llmTokensUsed: integer('llm_tokens_used').default(0),
  toolCallsUsed: integer('tool_calls_used').default(0),
}, (t) => ({
  pk: primaryKey({ columns: [t.tenantId, t.windowKey] }),
}))
```

### 7.2 大 blob 不入库：Transcript 文件

**为什么不入 RDBMS**：

| 维度 | RDBMS 大 blob | 文件系统 |
|---|---|---|
| 写入性能 | 一次性 INSERT，事务开销 | append-only，最快 |
| 增量追加 | UPDATE 整个 blob | append 部分 |
| 备份 | dump 时间 cubic 增长 | rsync / cp |
| 跨服务读 | 需 connection | NFS / S3 通用 |
| 长期归档 | warm storage 不便 | 可移到 S3 Glacier |

**Transcript 路径方案**：

```
/var/lib/qwen/
├─ tenants/
│   ├─ tenant-alice/
│   │   ├─ transcripts/
│   │   │   ├─ sess-xxx.jsonl
│   │   │   └─ sess-yyy.jsonl
│   │   └─ ...
│   └─ tenant-bob/
│       └─ transcripts/
└─ qwen.db                  ← SQLite 仅存 path 引用
```

SQLite 的 `sessions.transcript_path` 字段保存路径；daemon 读 transcript 时直接 open file（不通过 ORM）。

**S3 / OSS 长期归档**（Stage 6+）：

```ts
// 老 transcript 自动迁移到 S3
const ARCHIVE_AFTER_DAYS = 30

async function archiveOldTranscripts() {
  const cutoff = Date.now() - ARCHIVE_AFTER_DAYS * 86400_000
  const oldSessions = await db.select().from(sessions)
    .where(and(
      lt(sessions.lastActivityAt, cutoff),
      isNull(sessions.archivedAt),
    ))
  
  for (const s of oldSessions) {
    const localPath = s.transcriptPath
    const s3Key = `tenants/${s.tenantId}/archived/${s.id}.jsonl.gz`
    
    await s3.upload(s3Key, gzip(await fs.readFile(localPath)))
    await db.update(sessions)
      .set({ archivedAt: Date.now(), transcriptPath: `s3://${bucket}/${s3Key}` })
      .where(eq(sessions.id, s.id))
    
    await fs.unlink(localPath)
  }
}
```

## 八、Stage 6 多 daemon 共享状态架构

### 8.1 架构图

```
┌──────────────────────────────────────────────────┐
│ k8s cluster                                       │
│                                                    │
│  Load Balancer (sticky session by tenant_id)       │
│      ↓                                             │
│  ┌─────────────┬─────────────┬─────────────┐      │
│  │ daemon-1    │ daemon-2    │ daemon-N    │      │
│  │ (pod)       │ (pod)       │ (pod)       │      │
│  └──────┬──────┴──────┬──────┴──────┬──────┘      │
│         │              │              │             │
│         ↓              ↓              ↓             │
│  ┌──────────────────────────────────────┐          │
│  │ Postgres cluster (主从)               │          │
│  │ - permission_decisions / audit_log    │          │
│  │ - tenants / workspaces / sessions     │          │
│  └──────────────────────────────────────┘          │
│                                                      │
│  ┌──────────────────────────────────────┐          │
│  │ Object storage (S3 / OSS / MinIO)     │          │
│  │ - transcripts/<tenant>/<sess>.jsonl   │          │
│  └──────────────────────────────────────┘          │
│                                                      │
│  ┌──────────────────────────────────────┐          │
│  │ Redis (可选，加速 hot path)            │          │
│  │ - session subscribers map             │          │
│  │ - quota counters (TTL)                │          │
│  │ - permission decision cache           │          │
│  └──────────────────────────────────────┘          │
└──────────────────────────────────────────────────┘
```

### 8.2 sticky session 设计

```yaml
# k8s Ingress sticky session
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  annotations:
    nginx.ingress.kubernetes.io/affinity: "cookie"
    nginx.ingress.kubernetes.io/session-cookie-name: "qwen-daemon-id"
    nginx.ingress.kubernetes.io/session-cookie-hash: "sha1"
```

**为什么需要 sticky**：
- 同一 session 的 SSE 长连接保持在同一 daemon pod
- 避免事件流被切到不同 pod 时丢失订阅状态

### 8.3 Redis 加速

可选优化（Stage 6+），不是必须：

| 数据 | 何时进 Redis |
|---|---|
| **session subscribers** | 跨 daemon pod 共享订阅状态（主用 SSE 路由）|
| **quota counters** | 高频 increment，避免 Postgres 写阻塞 |
| **permission decision cache** | LRU 1000 条热点 pattern 命中 |

**Stage 6.5+ 加 Redis** —— 不是 Stage 6 起步必需。

### 8.4 多 daemon 配置

```json
{
  "daemon": {
    "instanceId": "${HOSTNAME}",                // k8s pod name
    "storage": {
      "type": "postgres",
      "postgres": {
        "host": "postgres-primary.qwen.svc.cluster.local",
        "readReplicas": [
          "postgres-replica-1.qwen.svc.cluster.local",
          "postgres-replica-2.qwen.svc.cluster.local"
        ],
        "poolSize": 20
      }
    },
    "transcriptStorage": {
      "type": "s3",
      "bucket": "qwen-transcripts",
      "region": "us-west-2",
      "prefix": "tenants/"
    },
    "redis": {
      "url": "redis://redis.qwen.svc.cluster.local:6379",
      "useFor": ["subscribers", "quota", "permission_cache"]
    }
  }
}
```

## 九、迁移与升级

### 9.1 drizzle-kit migration

```bash
# 生成迁移
$ pnpm drizzle-kit generate:sqlite
# 或
$ pnpm drizzle-kit generate:pg

# 应用
$ pnpm drizzle-kit push:sqlite
```

migration 文件提交到 repo（与 OpenCode 一致）：

```
packages/server/src/storage/migrations/
├─ 0001_initial.sql
├─ 0002_add_tenant_quotas.sql
├─ 0003_add_background_tasks_partition.sql  # Postgres 分区
└─ ...
```

### 9.2 SQLite → Postgres 迁移工具

```bash
# Stage 5 → Stage 6 升级
$ qwen-migrate sqlite-to-postgres \
    --from /var/lib/qwen/qwen.db \
    --to "postgres://..." \
    --transcript-from /var/lib/qwen/transcripts \
    --transcript-to "s3://..."
```

迁移步骤：
1. **暂停 daemon**（read-only mode）
2. dump SQLite → 转为 Postgres SQL
3. transcript 同步到 S3
4. 启动新 Postgres-backed daemon
5. 验证数据完整性
6. 退役旧 daemon

### 9.3 多 daemon 同时升级

```yaml
# k8s rolling update
strategy:
  type: RollingUpdate
  rollingUpdate:
    maxUnavailable: 1
    maxSurge: 1
```

要求 schema 向前兼容（新 daemon 能读旧 schema 一两个版本）。drizzle-kit 默认生成 additive migration（只加列 / 表，不破坏旧字段）。

## 十、安全考虑

### 10.1 加密

| 数据 | 是否加密 | 方案 |
|---|---|---|
| Transcript（含 LLM 对话）| **应该** | 文件系统 LUKS / S3 SSE-S3 / SSE-KMS |
| Tenant API keys / OAuth tokens | **必须** | AES-GCM with master key（master key 在 KMS / HSM）|
| Audit log | optional | 整库 TDE（PostgreSQL）|
| Bearer token secret | **必须** | bcrypt hash 存（不存明文）|

### 10.2 敏感字段示例

```json
// /etc/qwen/tenants/alice.json
{
  "providers": {
    "dashscope": {
      "apiKey": "${enc:AESGCM:base64-ciphertext}"
    }
  }
}
```

```ts
// daemon 启动时解密
const masterKey = await loadFromKms('qwen-master-key')
const config = decryptSensitiveFields(rawConfig, masterKey)
```

### 10.3 权限隔离

```bash
# SQLite 文件
chmod 600 /var/lib/qwen/qwen.db
chown qwen:qwen /var/lib/qwen/qwen.db

# Transcript 目录
chmod 700 /var/lib/qwen/transcripts
chmod 600 /var/lib/qwen/transcripts/*.jsonl

# Postgres
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO qwen_app;
REVOKE ALL ON pg_catalog FROM qwen_app;
```

## 十一、性能基准（推测）

实测数据需要落地后 benchmark；下面是合理估算：

| 场景 | SQLite | Postgres | MySQL |
|---|---|---|---|
| 单 daemon 1k tenant + 10k session 启动 | <1s | 1-2s（连接池暖）| 1-2s |
| Permission decision 查询（hot cache）| <0.1ms | 1-2ms（含网络）| 1-2ms |
| Audit log 1k 写/秒 | OK（WAL）| OK | OK |
| Audit log 10k 写/秒 | 瓶颈 | OK（partitioning）| OK |
| 跨 daemon session 订阅同步 | ❌ | ✓ via PUB/SUB | ✓ |
| 100GB audit log 历史查询 | ❌ 慢 | ✓ partition + index | ✓ |

## 十二、与 OpenCode / Claude Code 对比

| 维度 | OpenCode | Claude Code | Qwen Daemon Stage 6 |
|---|---|---|---|
| ORM | drizzle-orm | N/A（local files）| **drizzle-orm（同 OpenCode）** |
| 默认存储 | SQLite | local files | SQLite Stage 1-5 / Postgres Stage 6 |
| 多 daemon 共享状态 | ❌ | ❌ | **✓ Postgres + S3** |
| Transcript 存储 | SQLite blob | local files | **JSONL 文件 + S3 归档** |
| 配置 | settings.json | `~/.claude` | settings cascade（4 层 + tenant）|
| 加密敏感字段 | ❌ | minimal | **✓ AES-GCM + KMS** |
| Migration 工具 | drizzle-kit | N/A | **drizzle-kit** |
| 跨 region 支持 | ❌ | ❌ | **✓ Stage 6 multi-region** |

## 十三、Stage 1-3 → Stage 6 渐进路径

```
Stage 1-3: SQLite + JSONL
  └─ 单文件 SQLite + transcript 在 /var/lib/qwen/

Stage 4-5: 同上 + Tenant 抽象
  └─ tenants[] 表 + per-tenant transcript 子目录
  └─ Storage adapter 接口已定义但只有 SqliteAdapter 实现

Stage 6: + Postgres + S3 + 可选 Redis
  └─ 引入 PostgresAdapter
  └─ Transcript 迁到 S3
  └─ 多 daemon 实例 + sticky session
  └─ 加密敏感字段 + KMS
```

## 十四、测试与验证

落地时必须保证：

| 测试 | 范围 |
|---|---|
| Storage adapter contract test | 同一组测试在 Sqlite/Postgres/MySQL 都能跑通 |
| Schema 跨数据库一致 | drizzle 同时生成 3 种数据库迁移，diff 无业务字段差异 |
| Transcript 文件 ↔ S3 互通 | 同一 session 在文件 / S3 间迁移后 LoadSession 正确 |
| Concurrent write stress test | 1k 并发写入 audit log，数据无丢失 |
| Migration backward compat | drizzle-kit 生成的迁移可在 daemon-1 / daemon-2 不同版本 rolling update 期间共存 |
| 备份恢复 | SQLite cp / Postgres pg_dump 备份 → 恢复后数据完整 |
| 加密字段往返 | tenant.json 写入加密 → 读取解密 → 业务可用 |

## 十五、一句话总结

**Qwen daemon 持久层默认 SQLite + JSONL（Stage 1-5 单 daemon 足够），Storage Adapter 抽象层让 Stage 6 平滑切换到 Postgres + S3 + 可选 Redis。ORM 用 drizzle-orm（与 OpenCode 同栈）。Transcript 大 blob 永远走文件系统（不入 RDBMS），可归档到 S3 / OSS。敏感字段（API key / OAuth token）AES-GCM 加密 with KMS 主密钥。多 daemon 实例 Stage 6 通过 sticky session + Postgres 主从 + S3 共享 transcript 实现集群部署。schema 设计 8 张核心表（tenants / tokens / workspaces / sessions / permission_decisions / audit_log / background_tasks / tenant_quotas）+ drizzle-kit migration + 跨数据库一致 API。**

---

[← 返回 README](./README.md) · [下一篇：HA 高可用与故障恢复 →](./16-high-availability.md)
