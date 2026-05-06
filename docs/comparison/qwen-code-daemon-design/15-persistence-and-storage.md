# 15 — 持久层与外部存储

> [← 上一篇：实体模型与层级关系](./14-entity-model.md) · [下一篇：HA 高可用与故障恢复 →](./16-high-availability.md)

> 当前 Qwen Code 持久化是纯 JSON / JSONL 文件栈（**没有 SQLite / 任何 ORM**）。本章讨论：daemon 化进程中**何时引入 SQLite**（不是 Stage 1 起就引入）、何时继续用文件、何时跳到 Postgres，以及如何抽象 Storage Adapter 让各阶段可平滑切换。

## 一、TL;DR

| Stage | 持久化栈 | 关键变化 |
|---|---|---|
| **当前 Qwen Code（无 daemon）** | JSON + JSONL 文件 | 现状基线 |
| **Stage 1（HTTP-bridge MVP）** | **沿用 JSON + JSONL** | 不加新依赖 |
| **Stage 2（原生 daemon，单租户）** | + 内存 Map cache | 暂不加 SQLite |
| **Stage 3（完整 daemon，长跑 + 多 client）** | **首次引入 SQLite**（permission/audit/tokens 需要 ACID + 索引）| 新依赖：`better-sqlite3` + `drizzle-orm` |
| **Stage 4-5（多租户 + sandbox）** | SQLite + JSONL + 加密敏感字段 | quota / tenant config 上 SQLite |
| **Stage 6（SaaS HA）** | **Postgres + S3 + 可选 Redis** | 替换 SQLite，drizzle 同 ORM 切 dialect |

**关键设计原则**：
- **MVP 不引入新依赖**：Stage 1 沿用现有 JSON/JSONL 路线，验证 daemon 架构本身
- **数据形态决定存储**，不是阶段早晚：append-only 大 blob → 文件；并发频写 + 索引查询 → SQLite；多 daemon 共享 → Postgres
- **不是所有数据都要进 RDBMS**：transcript / settings.json / skills 永远文件
- **Storage Adapter 抽象**：Stage 3 引入接口，Stage 6 切 Postgres 时业务代码 0 改动
- **ORM 选 drizzle-orm**：在它真正引入时（Stage 3）选——和 OpenCode 同栈，跨 SQLite/Postgres/MySQL 三 dialect

## 二、当前 Qwen Code 持久化栈（事实基线）

**实测**（`grep` qwen-code/packages 全文，排除 node_modules 和 tsbuildinfo）：

| 检查 | 结果 |
|---|---|
| `sqlite` / `better-sqlite3` 依赖 | **0 个直接引用** |
| `drizzle` / `prisma` / `typeorm` / `sequelize` | **0 个** |
| `level` / `lmdb` / `rocksdb` | **0 个** |

**当前数据全部走文件系统**：

| 数据 | 存储位置 | 写入方式 |
|---|---|---|
| User config | `~/.qwen/settings.json` | `fs.writeFile(JSON.stringify(...))` |
| Session transcript | JSONL 文件（chatRecordingService）| `appendFileSync` |
| Session config（git worktree）| `<dir>/config.json`（gitWorktreeService.ts:357）| `fs.writeFile(JSON.stringify(...))` |
| Permission rules | settings.json（permission-manager.ts:771 注释明确）| 同上 |
| OAuth credentials | `~/.qwen/` 文件 | 同上 |
| MCP server registry | settings.json | 同上 |

**优点**：零依赖、人工可读、git diff 友好、无 schema migration 痛苦
**痛点（daemon 化后会暴露）**：
- 多 client 并发写 settings.json 互相覆盖
- audit_log 高频 append 后查询 grep 全文件慢
- 按 hash 查 token 需要全表扫
- quota counter 原子 increment 困难

## 三、引入 SQLite 的边界（Stage 3 才发生）

### 3.1 决策原则：让数据形态决定存储

不是按 stage 切换，而是按数据特性。下表把每类数据按特性归类：

| 数据 | 并发写频率 | 查询模式 | 推荐存储 | 引入时机 |
|---|---|---|---|---|
| settings.json / tenant.json | 低（人工编辑）| key 直接读 | **JSON 文件** | 永远（沿用现状）|
| Session transcript | 中（每条消息）| 顺序读 / fork resume | **JSONL** | 永远（沿用 PR#3739）|
| Skill registry | 启动时一次 | 内存 lookup | **内存 + JSON 索引** | 永远 |
| OAuth credentials | 低 | key 直接读 | **JSON + 加密** | 永远 |
| **permission_decisions** | 高（多 client 并发）| 复合键查询 | **SQLite** | **Stage 3** |
| **audit_log** | 极高（每 tool call）| 按 tenant + time 范围 | **SQLite** | **Stage 3** |
| **tokens** | 低写 / 高读 | hash lookup + 索引 | **SQLite** | **Stage 3** |
| **background_tasks meta** | 中 | 按 status / session 过滤 | **SQLite** | **Stage 3** |
| **workspaces meta** | 低写 | UNIQUE 约束防 race | **SQLite** | **Stage 4**（多租户起）|
| **tenant_quotas** | 极高（每次 tool call increment）| 原子 +1 | **SQLite** → Redis | **Stage 4** |

### 3.2 4 类数据为什么必须升级到 SQLite（Stage 3）

**a) `permission_decisions` —— 文件 race condition**

[决策 §6 多 client 并发](./03-architectural-decisions.md) 下，多 client 可能同时记录 `alwaysAllow` 决策：

```
T=0   Client A 收到 'Bash(npm test)' 权限请求 → user 选 alwaysAllow
T=0   Client B 几乎同时收到 'Bash(git status)' 权限请求 → user 选 alwaysAllow
T=1   两 client 都 read settings.json → 修改 → write
      → 后写赢，前者决策丢失
```

JSON 文件无 ACID。SQLite `INSERT ... ON CONFLICT` + WAL 解决。

**b) `audit_log` —— 查询性能**

`audit_log.jsonl` 100MB+ 后：
- `grep tenant_id=t-alice` 全文扫 → 秒级
- 按时间范围筛 → 慢
- WHERE tenant + time + tool_name 复合条件 → 不可行

SQLite `idx_audit_tenant_ts` 复合索引 → ms 级。

**c) `tokens` —— hash lookup**

每次 HTTP request 验证 bearer token：
- JSON 文件：read all + bcrypt.compare 全部
- SQLite：`WHERE secret_hash = ?` + 索引 → 直接 hit

每秒 100+ 请求时差距明显。

**d) `background_tasks` —— 状态机查询**

[§subagent-display PR#3471/3488/3791/3836](../subagent-display-deep-dive.md) 4 kinds 后台任务：
- UI 需 `WHERE session_id = ? AND status = 'running'` 列出
- JSON 文件方案需要把所有 task 加载到内存遍历
- SQLite `idx_task_session` + `idx_task_status` 自然支持

### 3.3 哪些数据继续用文件（明确不进 SQLite）

| 数据 | 不进 SQLite 的理由 |
|---|---|
| `settings.json` / `tenant.json` | 人工编辑友好 / git diff 可读 / 低并发 |
| Transcript JSONL | 大 blob / append-only / 文件性能最高 / S3 归档兼容 |
| Skill registry | 启动 immutable / 内存 lookup 即可 |
| MCP server config | 同 settings.json |
| OAuth tokens | 加密文件比 SQLite 字段加密简单 |

### 3.4 替代方案对比（为什么是 SQLite 不是别的）

|  | SQLite | LMDB / level | DuckDB | 直接 Postgres | 继续 JSON |
|---|---|---|---|---|---|
| 部署 | 0 | 0 | 0 | 需服务 | 0 |
| 关系查询 | ✓ | ✗（KV）| ✓✓ OLAP | ✓✓ | ✗ |
| ACID | ✓ | ✓ | ✓ | ✓ | ✗ |
| 跨 SQLite/PG ORM | drizzle ✓ | drizzle ✗ | drizzle ✗ | drizzle ✓ | N/A |
| Stage 6 切 Postgres 平滑 | ✓ | 重写 | 重写 | 已是 | 重写 |
| Bundle size 增量 | ~2MB（better-sqlite3 native）| 小 | ~30MB | 0 | 0 |
| 测试友好 | `:memory:` | partial | ✓ | 需 testcontainers | ✓ |
| 与 OpenCode 同栈 | ✓ | ✗ | ✗ | (Stage 6 同) | ✗ |

**SQLite 胜在**：跨阶段平滑（Stage 3 SQLite → Stage 6 Postgres，drizzle 同 ORM 仅切 dialect）、与 OpenCode 同栈降低生态学习成本、bundle size 可接受。

**为什么不直接跳过 SQLite 上 Postgres**：
- Stage 3 单 daemon 部署，Postgres 是过度工程
- 个人 / 小团队 self-host 不该被强制装数据库
- SQLite `:memory:` 单元测试比 Postgres testcontainers 快 100x

### 3.5 Stage 3 数据迁移（从文件到 SQLite）

升级到 Stage 3 时一次性 import：

```ts
// scripts/migrate-to-sqlite.ts (Stage 3 升级工具)
async function migrateFromFiles() {
  const db = drizzle(new Database('/var/lib/qwen/qwen.db'))
  
  // 1. permission_decisions 从 settings.json 抽取
  const settings = JSON.parse(await fs.readFile('~/.qwen/settings.json', 'utf-8'))
  for (const rule of settings.permissions?.alwaysAllow ?? []) {
    await db.insert(permissionDecisions).values({
      tenantId: 'default',
      workspaceId: 'default',
      pattern: rule,
      scope: 'global',
      decision: 'allow',
    })
  }
  
  // 2. tokens 类似 import
  // 3. audit_log JSONL 顺序导入
  // 4. transcript / skill registry / settings 留在文件，不动
}
```

迁移可逆——保留原 JSON 文件，SQLite 仅作为运行时 mirror。**Stage 3 → Stage 4 切回纯文件**只需 SQL `SELECT * INTO json_export.json` + 删 db 文件。

## 四、SQLite 选型理由（Stage 3-5 适用）

### 4.1 优点

- **零部署**：embedded，daemon 启动时 open file 即可
- **WAL 模式**：高并发读 + 单写者，足够 daemon 内多 session 并发
- **单文件备份**：`cp qwen.db backup.db` 即可
- **跨平台**：Linux / macOS / Windows 一致
- **drizzle-orm 一线支持**：与 OpenCode 同栈
- **测试友好**：`:memory:` 数据库 + 单元测试快速重置

### 4.2 限制

- **单写者**：所有写串行；高并发写场景（>100 写/秒）会成瓶颈
- **单进程**：daemon 重启时锁定文件（不支持多进程同时写）
- **不支持跨机**：无 replication / clustering
- **大数据量**：超 100GB 性能下降（适合中小 deployment）
- **新依赖成本**：`better-sqlite3` 是 native module，需要 prebuild binary 或编译环境

### 4.3 适用边界

```
Stage 1-2 (HTTP-bridge / 原生单租户): JSON 文件足够，不引入
Stage 3 (完整 daemon 多 client):       SQLite 引入（permission/audit/tokens）
Stage 4 多租户单 daemon:               SQLite 撑万级 tenant + 百万级 audit log
Stage 5 + sandbox:                     同上
─────────────────────────────────────────────
Stage 6 多 daemon 实例:                SQLite 不够，必须升级 Postgres
```

## 五、何时需要外部 RDBMS

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

## 六、Storage Adapter 抽象设计

### 6.1 Interface

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
class SqliteAdapter implements StorageAdapter {  // Stage 3-5 默认
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

### 6.2 配置选择

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

### 6.3 与现有 Qwen Code 协调

Qwen Code 当前用什么？

```bash
$ find /root/git/qwen-code/packages -name "package.json" 2>/dev/null \
  | xargs grep -l "drizzle\|better-sqlite3\|sequelize\|typeorm\|prisma" 2>/dev/null
# (检查现有依赖)
```

如果 Qwen Code 还没有 ORM，daemon 化引入 `drizzle-orm` 是合理选择（与 OpenCode 一致）；如果已有其他 ORM，需评估迁移成本。

## 七、ORM 选型：drizzle-orm

### 7.1 为什么 drizzle

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

### 7.2 跨数据库 schema

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

### 7.3 查询 API（跨数据库一致）

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

## 八、完整 Schema 设计

### 8.1 核心表

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

### 8.2 大 blob 不入库：Transcript 文件

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

## 九、Stage 6 多 daemon 共享状态架构

### 9.1 架构图

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

### 9.2 sticky session 设计

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

### 9.3 Redis 加速

可选优化（Stage 6+），不是必须：

| 数据 | 何时进 Redis |
|---|---|
| **session subscribers** | 跨 daemon pod 共享订阅状态（主用 SSE 路由）|
| **quota counters** | 高频 increment，避免 Postgres 写阻塞 |
| **permission decision cache** | LRU 1000 条热点 pattern 命中 |

**Stage 6.5+ 加 Redis** —— 不是 Stage 6 起步必需。

### 9.4 多 daemon 配置

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

## 十、迁移与升级

### 10.1 drizzle-kit migration

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

### 10.2 SQLite → Postgres 迁移工具

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

### 10.3 多 daemon 同时升级

```yaml
# k8s rolling update
strategy:
  type: RollingUpdate
  rollingUpdate:
    maxUnavailable: 1
    maxSurge: 1
```

要求 schema 向前兼容（新 daemon 能读旧 schema 一两个版本）。drizzle-kit 默认生成 additive migration（只加列 / 表，不破坏旧字段）。

## 十一、安全考虑

### 11.1 加密

| 数据 | 是否加密 | 方案 |
|---|---|---|
| Transcript（含 LLM 对话）| **应该** | 文件系统 LUKS / S3 SSE-S3 / SSE-KMS |
| Tenant API keys / OAuth tokens | **必须** | AES-GCM with master key（master key 在 KMS / HSM）|
| Audit log | optional | 整库 TDE（PostgreSQL）|
| Bearer token secret | **必须** | bcrypt hash 存（不存明文）|

### 11.2 敏感字段示例

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

### 11.3 权限隔离

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

## 十二、性能基准（推测）

实测数据需要落地后 benchmark；下面是合理估算：

| 场景 | SQLite | Postgres | MySQL |
|---|---|---|---|
| 单 daemon 1k tenant + 10k session 启动 | <1s | 1-2s（连接池暖）| 1-2s |
| Permission decision 查询（hot cache）| <0.1ms | 1-2ms（含网络）| 1-2ms |
| Audit log 1k 写/秒 | OK（WAL）| OK | OK |
| Audit log 10k 写/秒 | 瓶颈 | OK（partitioning）| OK |
| 跨 daemon session 订阅同步 | ❌ | ✓ via PUB/SUB | ✓ |
| 100GB audit log 历史查询 | ❌ 慢 | ✓ partition + index | ✓ |

## 十三、与 OpenCode / Claude Code 对比

| 维度 | OpenCode | Claude Code | Qwen Daemon Stage 6 |
|---|---|---|---|
| ORM | drizzle-orm | N/A（local files）| **drizzle-orm（同 OpenCode）** |
| 默认存储 | SQLite | local files | JSON Stage 1-2 / SQLite Stage 3-5 / Postgres Stage 6 |
| 多 daemon 共享状态 | ❌ | ❌ | **✓ Postgres + S3** |
| Transcript 存储 | SQLite blob | local files | **JSONL 文件 + S3 归档** |
| 配置 | settings.json | `~/.claude` | settings cascade（4 层 + tenant）|
| 加密敏感字段 | ❌ | minimal | **✓ AES-GCM + KMS** |
| Migration 工具 | drizzle-kit | N/A | **drizzle-kit** |
| 跨 region 支持 | ❌ | ❌ | **✓ Stage 6 multi-region** |

## 十四、Stage 1 → Stage 6 渐进路径

```
当前 Qwen Code (无 daemon): JSON + JSONL 文件
  └─ ~/.qwen/settings.json + transcripts JSONL

Stage 1 (HTTP-bridge MVP): 沿用现状
  └─ 不引入 SQLite / 任何 ORM
  └─ daemon 仅是 HTTP 包装，文件 IO 不变

Stage 2 (原生 daemon 单租户): + 内存 Map cache
  └─ FileReadCache / Subscriber Map / AsyncLocalStorage 都在内存
  └─ 持久化仍是 JSON / JSONL

Stage 3 (完整 daemon 多 client): 首次引入 SQLite
  └─ 新依赖：better-sqlite3 + drizzle-orm
  └─ permission_decisions / audit_log / tokens / background_tasks 入 SQLite
  └─ transcript 仍 JSONL / settings 仍 JSON
  └─ Storage Adapter 接口定义（仅 SqliteAdapter 实现）

Stage 4-5 (多租户 + sandbox): + tenant 抽象 + 加密
  └─ tenants[] / tenant_quotas 表
  └─ per-tenant transcript 子目录
  └─ 敏感字段 AES-GCM 加密
  └─ 仍是 SQLite

Stage 6 (SaaS HA): + Postgres + S3 + 可选 Redis
  └─ 引入 PostgresAdapter（drizzle 同 ORM 切 dialect）
  └─ Transcript 迁到 S3
  └─ 多 daemon 实例 + sticky session
  └─ KMS 主密钥
```

## 十五、测试与验证

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

## 十六、一句话总结

**Qwen Code 当前持久化是 JSON + JSONL 文件（无 SQLite / 无 ORM），daemon 化的 Stage 1-2 沿用此栈不引入新依赖；Stage 3 完整 daemon 时首次引入 SQLite（better-sqlite3 + drizzle-orm）解决多 client 并发写 / audit_log 索引查询 / tokens hash lookup / background_tasks 状态机查询四类痛点；Stage 4-5 在 SQLite 上扩多租户 + 加密；Stage 6 SaaS 通过 drizzle 切 dialect 平滑升级 Postgres + S3 + 可选 Redis。Transcript 大 blob 永远走文件（不入 RDBMS），settings.json / skill registry 永远人工编辑友好的 JSON。Storage Adapter 抽象层让阶段切换业务代码 0 改动。schema 设计 8 张核心表（tenants / tokens / workspaces / sessions / permission_decisions / audit_log / background_tasks / tenant_quotas）+ drizzle-kit migration + 跨 SQLite/Postgres/MySQL 一致 API。设计哲学：让数据形态决定存储，不是按阶段早晚切换；MVP 优先沿用现状，新依赖按真实痛点引入。**

---

[← 返回 README](./README.md) · [下一篇：HA 高可用与故障恢复 →](./16-high-availability.md)
