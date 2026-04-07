# 5. 会话管理与 Git 快照——开发者参考

> OpenCode 的会话管理是所有 CLI Code Agent 中最丰富的——SQLite 持久化、Session Fork/Restore、云端 Share、Git-backed 快照。Claude Code 有 /rewind 但没有 fork，Qwen Code 两者都没有。
>
> **Qwen Code 对标**：Session Fork（从任意消息点分叉）、Git 快照（文件状态追踪）、SQLite 替代 JSONL。

## 一、为什么会话管理是 Code Agent 的差异化

### 问题定义

| 场景 | 无高级会话管理 | 有 Fork/Restore/Snapshot |
|------|-------------|------------------------|
| Agent 在第 20 步走错方向 | 手动 git checkout 恢复 + 从头开始新会话 | `/restore 18` 回退到第 18 步，文件自动恢复 |
| 想尝试两种不同方案 | 只能串行：先试 A，不行再重来试 B | Fork 两个分支并行尝试 |
| 想分享审查结果给同事 | 复制粘贴终端输出 | `/share` 生成云端链接，含完整 diff 和对话 |
| 想看 Agent 修改了哪些文件 | `git diff` 手动检查 | Session Review 面板，行内 diff + 注释 |

### 竞品会话能力对比

| 能力 | OpenCode | Claude Code | Qwen Code | Gemini CLI |
|------|---------|-------------|-----------|-----------|
| 持久化 | SQLite (Drizzle ORM) | JSONL 文件 | JSONL 文件 | File-based |
| Fork | ✓ 从任意消息点 | — | — | — |
| Restore/Revert | ✓ 回退到历史消息 | ✓ /rewind | — | — |
| Share（云端） | ✓ 增量同步 + SSR | — | — | — |
| Git Snapshot | ✓ 每步快照 | ✓ 文件检查点 | — | — |
| Session Review | ✓ diff 面板 + 行内注释 | — | — | — |

## 二、Git 快照系统

源码: `packages/opencode/src/snapshot/index.ts`

### 工作原理

```
每步工具执行前：
  │
  ├─ Snapshot.track()
  │   ├─ git add -A（当前目录）
  │   ├─ git write-tree → 返回 tree hash
  │   └─ 存储 hash 到 MessagePart（type: "snapshot"）
  │
  └─ 工具执行...

回退时：
  │
  ├─ Snapshot.revert(patches)
  │   ├─ 收集目标消息之后的所有 patch
  │   ├─ git checkout {hash} -- {file}（批量，每批 100 个文件）
  │   └─ 文件恢复到目标状态
  │
  └─ 会话截断到目标消息
```

**关键设计**：
- git 数据存储在 `~/.local/share/opencode/snapshot/{project_hash}/`（不污染项目仓库）
- 文件 > 2MB 自动排除（`.git/info/exclude`）
- 每个项目目录一个 Semaphore 锁（防止并发 git 操作）
- 定期 `git gc --prune=7.days` 清理过期数据

## 三、Session Fork

源码: `packages/opencode/src/session/index.ts`

```typescript
Session.fork(sessionID, messageID?)
  │
  ├─ 创建新 session（parent_id = 原 session）
  │
  ├─ 复制 messages（到 messageID 为止）
  │   ├─ 创建 ID 映射（旧 ID → 新 ID）
  │   ├─ 修复 parent 引用（assistant 消息指向对应 user 消息）
  │   └─ 复制 parts
  │
  └─ 返回新 session ID
```

## 四、SQLite 持久化

使用 Drizzle ORM + WAL 模式：

| 表 | 核心字段 | 用途 |
|---|---------|------|
| `session` | id, parent_id, share_url, revert(JSON), summary_diffs(JSON), time_compacting | 会话元数据 |
| `message` | id, session_id, data(JSON: InfoData) | 消息内容 |
| `part` | id, message_id, data(JSON: PartData) | 消息部件（text/tool/snapshot/...） |
| `todo` | session_id, data | 任务清单 |
| `permission` | project_id, pattern, action | 权限规则 |

**vs JSONL（Qwen Code 当前）**：SQLite 支持 `WHERE session_id = ? ORDER BY time_created`、按项目/代理/时间范围查询、Session Fork 的跨行引用——这些在 JSONL 中需要全量加载 + 内存过滤。

## 五、Qwen Code 改进建议

### P2：Session Fork/Restore

实现从任意消息点分叉会话——让用户可以"在第 15 步尝试另一种方案"。核心是消息复制 + ID 映射 + 文件状态恢复。

### P2：Git Snapshot

每步工具执行前用 `git write-tree` 记录文件状态，恢复时用 `git checkout {hash} -- {file}`。独立的 git 目录不污染项目仓库。

### P3：SQLite 替代 JSONL

长期看，SQLite 比 JSONL 更适合会话持久化——支持复杂查询、Fork 引用、增量更新。但迁移成本高，建议作为 v2 架构目标。
