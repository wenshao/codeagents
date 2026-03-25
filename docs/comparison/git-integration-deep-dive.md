# 35. Git 集成与版本控制深度对比

> Git 集成决定了 AI 编程代理的代码安全网——能否安全回退、自动提交、追踪归因。从"无 Git 集成"到"每步自动 Checkpoint + 三种回退选项"。

## 总览

| 工具 | 自动提交 | 归因系统 | 检查点/回退 | Worktree 隔离 | Git 命令 | 独特设计 |
|------|---------|---------|-----------|-------------|---------|---------|
| **Aider** | **✓（每次编辑）** | **✓（3 标志）** | /undo | ✗ | /commit /undo /diff /git | Co-authored-by 归因 |
| **Claude Code** | ✗（需指令） | ✗ | **✓ /rewind + Esc** | **✓** | 对话式 | Esc 键快速回退 |
| **Cline** | **✓（每步）** | ✗ | **✓ Git Checkpoint** | ✗ | 可视化回滚 | 每步 Git 快照 |
| **Gemini CLI** | ✗ | ✗ | **✓ /rewind（3 选项）** | ✗ | ✗ | 影响分析 UI |
| **Qwen Code** | ✗ | ✗ | ✓ /restore | **✓（Arena）** | ✗ | /btw 旁问 |
| **OpenCode** | ✗ | ✗ | **✓ /restore + fork** | **✓** | ✗ | Session Fork |
| **Codex CLI** | ✗ | ✗ | ✗ | ✗ | codex apply | .git 受保护 |
| **Kimi CLI** | ✗ | ✗ | ✗ | ✗ | ✗ | D-Mail 实验 |
| **Goose** | ✗ | ✗ | ✗ | ✗ | ✗ | MCP 驱动 |

---

## 一、Aider：最完整的 Git 集成

> 源码：`repo.py:commit()`、`commands.py`

### 自动提交 + 归因系统

每次 AI 编辑后自动调用 `auto_commit()`，提交消息由弱模型生成：

```
AI 编辑 → auto_commit(aider_edits=True)
  → 弱模型生成提交消息
  → 添加归因标记
  → git commit
```

**三个独立归因标志**：

| 标志 | 默认 | 效果 |
|------|------|------|
| `--attribute-co-authored-by` | **开启** | 添加 `Co-authored-by: aider (<model>) <aider@aider.chat>` |
| `--attribute-author` | 关闭 | 修改 Author 为 `"User (aider)"` |
| `--attribute-committer` | 关闭 | 修改 Committer 为 `"User (aider)"` |

### 4 个 Git 命令

```bash
/commit 修复了 typo       # 手动提交（AI 生成消息）
/undo                     # 撤销上一次 aider 提交
/diff                     # 显示最近的代码变更
/git log --oneline -5     # 执行任意 Git 命令
```

### /undo 安全检查（源码：`commands.py` raw_cmd_undo，103 行）

```python
def raw_cmd_undo():
    last_commit = repo.head.commit

    # 检查 1: 仅撤销 aider 创建的提交
    if last_commit.hexsha not in aider_commit_hashes:
        error("Can only undo aider-created commits")
        return

    # 检查 2: 拒绝撤销已推送的提交
    if is_pushed(last_commit):
        error("Cannot undo commits already pushed to remote")
        return

    # 检查 3: 拒绝撤销 merge 提交
    if is_merge_commit(last_commit):
        error("Cannot undo merge commits")
        return

    # 检查 4: 拒绝 dirty 工作目录
    if repo.is_dirty():
        error("Cannot undo with uncommitted changes")
        return

    # 执行撤销：逐文件恢复 + soft reset
    for file in affected_files:
        repo.git.checkout("HEAD~1", "--", file)
    repo.git.reset("--soft", "HEAD~1")
```

**设计理念**：4 层安全检查确保 /undo 永远不会破坏用户的工作——不碰非 aider 提交、不碰远程历史、不碰复杂合并、不丢未保存修改。

---

## 二、Claude Code：Esc 键检查点 + Worktree

> 来源：02-commands.md、07-session.md

### 检查点系统

```
按 Esc → 显示 checkpoint 菜单 → 选择回退点
       → 文件系统 + 对话历史同时回退
       → worktree 隔离确保安全
```

### /rewind 命令

```bash
/rewind         # 交互式选择回退点（别名 /checkpoint）
```

### Worktree 隔离

```bash
claude --worktree feature-x    # 创建独立 worktree
claude --tmux                  # tmux 分屏 + worktree
```

- EnterWorktree / ExitWorktree 工具动态切换
- Teammates 每个代理独立 worktree

### 系统提示安全指令

二进制中提取的 Git 安全规则：
- "NEVER update the git config"
- "NEVER run destructive git commands (push --force, reset --hard...)"
- "CRITICAL: Always create NEW commits rather than amending"

---

## 三、Gemini CLI：/rewind 三选项 + 影响分析

> 源码：`rewindCommand.tsx`、`rewindFileOps.ts`

### 三种回退选项

| 选项 | 回退代码 | 回退对话 | 用途 |
|------|---------|---------|------|
| **全部回退** | ✓ | ✓ | Agent 完全走偏 |
| **仅回退对话** | ✗ | ✓ | 代码正确但对话被污染 |
| **仅回退代码** | ✓ | ✗ | 对话有价值但代码改坏了 |

### RewindViewer 交互式 UI 流程

```
1. 用户输入 /rewind（或按 Esc Esc）
2. RewindViewer 组件显示检查点列表：
   ┌─ Checkpoint #3 (2 minutes ago)
   │  Modified: src/index.ts (+15, -3)
   │  Created: src/utils.ts (+42)
   │  Deleted: src/old.ts (-28)
   └─
3. 上下箭头选择目标检查点
4. 确认对话框：三种选项
5. 执行选中的回退策略
6. 显示回退结果摘要
```

### 影响分析（`rewindFileOps.ts:calculateTurnStats()`）

基于 diff 计算的文件变更统计：
- 添加行数 / 删除行数 / 修改文件数
- **限制**：仅回退 AI 工具造成的修改，不回退手动编辑或 Shell 工具（`!`）执行的变更

### 检查点存储

| 组件 | 位置 | 格式 |
|------|------|------|
| 文件快照 | `~/.gemini/history/<project_hash>` | Git 影子仓库（不影响用户 Git） |
| 对话索引 | `~/.gemini/tmp/<project_hash>/checkpoints` | 消息位置标记 |
| 工具参数 | 检查点元数据 | 参数快照 |

---

## 四、Cline：每步 Git Checkpoint

> 来源：cline.md

每个工具执行步骤自动创建 Git 快照：

```
Tool 执行 → Git commit（自动）→ 用户可视化回滚
```

- 支持多文件 Checkpoint
- VS Code WebView 中一键回滚
- 自动排除 node_modules/.git

---

## 五、OpenCode：Session Fork + Git-backed Review

> 来源：03-architecture.md

```
git write-tree → 捕获状态快照
git diff → 计算变更
SessionRevert.revert() → git checkout {hash} -- {file}
```

- **Session Fork**：任意消息点创建分支，类似 Git 分支模型
- **Restore-to-Message**：回退到指定消息时的文件状态
- 快照存储：`~/.local/share/opencode/snapshot/{project_id}`
- **Git-backed Review**：变更以 snapshot diff 形式可视化

---

## 六、Kimi CLI：D-Mail 时间回溯（实验性）

> 源码：`soul/denwarenji.py` + `dmail/`

`okabe` 代理中的 `SendDMail` 工具，灵感来自 Steins;Gate 动画的 D-Mail 概念：

- 向过去的检查点"发送消息"
- 回滚上下文到指定时间点
- 实验性功能，不推荐生产使用

---

## 七、Codex CLI：.git 受保护

> 来源：03-architecture.md

- `.git`、`.agents`、`.codex` 目录**始终只读**
- `codex apply <task-id>` 通过 `git apply` 应用 diff
- `codex review` 基于 `git diff` 结构化审查
- 沙箱内所有 Git 操作受 OS 级隔离保护

---

## 设计模式对比

### 安全网策略

| 策略 | 代表 | 回退粒度 | 自动化 |
|------|------|---------|--------|
| **每次编辑自动提交** | Aider | 单次编辑 | 全自动 |
| **每步工具自动快照** | Cline | 单步操作 | 全自动 |
| **手动检查点 + Esc** | Claude Code | 用户选择 | 半自动 |
| **三选项回退** | Gemini CLI | 代码/对话独立 | 手动 |
| **Session Fork** | OpenCode | 消息级别 | 手动 |

---

## 证据来源

| 工具 | 来源 | 获取方式 |
|------|------|---------|
| Aider | 02-commands.md + 03-architecture.md | 开源 |
| Claude Code | 02-commands.md + 07-session.md | 二进制分析 |
| Gemini CLI | btw-rewind.md + 02-commands.md | 开源 |
| Cline | cline.md | 开源 |
| OpenCode | 03-architecture.md | 开源 |
