# Git 工作流与会话管理 Deep-Dive

> AI Agent 如何追踪代码归属、管理文件历史、支持对话分支？本文基于 Claude Code（v2.1.89 源码分析）和 Qwen Code（v0.15.0 开源）的源码分析，对比两者在 commit attribution、文件历史快照、会话分支和输出模式方面的差异。

---

## 1. 架构总览

| 维度 | Claude Code | Qwen Code |
|------|------------|-----------|
| **Commit Attribution** | ✅ Co-Authored-By + 按文件字符归因 + git notes | ❌ |
| **Git Diff 统计** | ✅ numstat + hunks 解析（50 文件 / 1MB 上限） | 依赖 simple-git npm |
| **文件历史** | ✅ per-file SHA256 快照（100 个/session） | Git worktree checkpoint |
| **会话分支** | ✅ /branch（transcript 完整 fork + forkedFrom 溯源） | ❌ |
| **Output Styles** | ✅ Learning（教学模式）+ Explanatory（解释模式） | ❌ |

---

## 2. Commit Attribution（代码归因）

### 2.1 Claude Code

**Co-Authored-By 注入**（源码: `utils/commitAttribution.ts`）：

```
git commit 消息末尾自动追加:
Co-Authored-By: Claude <noreply@anthropic.com>
```

**按文件字符归因**：
- 跟踪每个文件的 `claudeChars`（AI 贡献字符数）vs `humanChars`（人类贡献字符数）
- 通过 diff 前缀/后缀匹配计算贡献比例
- SHA256 哈希标识文件版本

**Attribution 元数据**（存储在 git notes 中）：

```json
{
  "version": 1,
  "summary": { "claudeChars": 1500, "humanChars": 200 },
  "files": [
    { "path": "src/main.ts", "claudeChars": 800, "humanChars": 50, "hash": "abc123" }
  ],
  "surface": "cli/opus-4-6",
  "sessionId": "session-uuid"
}
```

**模型名清理**：内部模型名（`opus-4-6-fast`）在外部仓库自动清理为公开名（`claude-opus-4-6`），避免泄露内部代号。

### 2.2 Qwen Code

无 commit attribution 机制——commit 消息中不标注 AI 贡献，无法区分 AI vs 人类代码。

**影响**：开源项目中 AI 生成代码的透明度缺失；审计场景无法追溯。

---

## 3. Git Diff 统计

### 3.1 Claude Code

**结构化 diff 解析**（源码: `utils/gitDiff.ts`）：

```typescript
// 两阶段 diff:
// 1. git diff HEAD --numstat → O(1) 内存快速探测（文件数 + 行数）
// 2. git diff HEAD → 完整 hunks（仅在文件数不超限时）

// 限制:
MAX_FILES = 50                  // 超过 50 文件跳过详情
MAX_DIFF_SIZE_BYTES = 1_000_000 // 单文件 >1MB 跳过
MAX_LINES_PER_FILE = 400        // GitHub auto-load 限制
MAX_FILES_FOR_DETAILS = 500     // 超过 500 文件仅显示 numstat

// 特殊处理:
// - merge/rebase/cherry-pick/revert 期间跳过 diff
// - 未跟踪文件: git ls-files --others（仅文件名）
// - 单文件 diff: 与默认分支 merge-base 比较（PR 风格视图）
```

**统计信息**：
- `filesCount`、`linesAdded`、`linesRemoved`
- 按文件：`added`、`removed`、`isBinary`、`isUntracked`
- 结构化 hunks：`oldStart`、`oldLines`、`newStart`、`newLines`、`lines[]`

### 3.2 Qwen Code

使用 `simple-git` npm 包调用 git 命令，无专门的 diff 解析器。无 numstat 快速探测、无文件数限制、无结构化 hunks 输出。

---

## 4. 文件历史快照

### 4.1 Claude Code

**Per-file SHA256 快照**（源码: `utils/fileHistory.ts`）：

```
编辑前 → fileHistoryTrackEdit() → 备份原始文件
                                   ├── 计算 SHA256 内容哈希
                                   ├── 检查 mtime 避免重复备份
                                   └── 存储: {hash}@v{version}

消息完成后 → fileHistoryMakeSnapshot() → 创建快照
                                          ├── 记录所有已跟踪文件的当前版本
                                          ├── 删除的文件标记 backupFileName: null
                                          └── 快照上限: 100 个/session
```

**恢复**：按消息 ID 回滚到特定快照——比 git-level checkpoint 更细粒度。

### 4.2 Qwen Code

**Git Worktree Checkpoint**（源码: `packages/core/src/services/gitWorktreeService.ts`）：

```
setupWorktrees() → git worktree add（创建独立工作副本）
                → git stash create（捕获脏状态）
                → 复制未跟踪文件
                → 创建 baseline commit

// Diff 从 baseline 开始——仅捕获 agent 变更，排除预先存在的编辑
```

**区别**：Git-level（整体快照）vs file-level（按文件版本），Qwen 的粒度更粗但与 git 生态天然兼容。

---

## 5. 会话分支（/branch）

### 5.1 Claude Code

```typescript
// 源码: commands/branch/branch.ts
// /branch [名称] → fork 当前 transcript 为新 session

// 保留的元数据:
// - 完整消息历史（时间戳、gitBranch、parentUuid、isSidechain）
// - content-replacement 条目（prompt cache 预览）
// - forkedFrom: { sessionId, messageUuid }（溯源）

// 命名: "对话标题 (Branch)" → "(Branch 2)" → "(Branch 3)"
// 分支自动成为活跃 session；原始 session 可通过 --resume 恢复
```

**用例**：
- 探索替代实现方案而不丢失当前进度
- A/B 对比不同架构决策
- 从某个关键节点创建多个实验分支

### 5.2 Qwen Code

无会话分支功能。`forkedQuery.ts` 用于 speculation/followup 的 cache-aware 二次查询，不是对话分叉。

---

## 6. Output Styles（输出模式）

### 6.1 Claude Code

**两种内置模式**（源码: `constants/outputStyles.ts`）：

| 模式 | 行为 |
|------|------|
| **Explanatory** | 在代码变更后添加 "Insight" 块：解释实现选择和代码库模式——"提供教育性洞察" |
| **Learning** | 暂停执行，要求用户编写代码——"通过动手实践学习" |

**Learning 模式详情**：
- 对 20+ 行的函数，请求用户贡献 2-10 行设计决策/业务逻辑/算法
- 格式：Context → Your Task → Guidance
- 代码中插入 `TODO(human)` 占位符
- 等待人类实现后继续
- 适用场景：教学、代码审查培训、新人上手

**加载优先级**：built-in → plugin → user settings → project settings

### 6.2 Qwen Code

无内置 output style 模式。`settingsSchema.ts` 有通用设置框架，但未定义 Learning/Explanatory 等具体模式。

---

## 7. 对比总结

| 维度 | Claude Code | Qwen Code | 差距 |
|------|------------|-----------|------|
| Commit Attribution | 按文件字符归因 + git notes | 无 | 缺失 |
| Diff 统计 | 原生解析（numstat + hunks + 限制） | simple-git 库 | 中等 |
| 文件快照 | per-file SHA256（100 个/session） | Git worktree（整体） | 粒度差异 |
| 会话分支 | /branch + forkedFrom 溯源 | 无 | 缺失 |
| Output Styles | Learning + Explanatory | 无 | 缺失 |

---

## 8. 关键源码文件

### Claude Code

| 文件 | 职责 |
|------|------|
| `utils/commitAttribution.ts` | Co-Authored-By + 按文件字符归因 |
| `utils/gitDiff.ts` | 结构化 diff 解析（numstat + hunks + 限制） |
| `utils/fileHistory.ts` | Per-file SHA256 快照 + 按消息恢复 |
| `commands/branch/branch.ts` | /branch 会话分叉 |
| `constants/outputStyles.ts` | Learning / Explanatory 输出模式 |

### Qwen Code

| 文件 | 职责 |
|------|------|
| `packages/core/src/services/gitWorktreeService.ts` | Git worktree checkpoint |
| `packages/core/src/followup/forkedQuery.ts` | Cache-aware 二次查询（非对话分叉） |

> **免责声明**: 以上分析基于 2026 年 Q1 源码，后续版本可能已变更。
