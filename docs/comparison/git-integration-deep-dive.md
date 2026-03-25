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

### /undo 安全检查

`raw_cmd_undo()` 实现 4 层安全检查：
1. 仅撤销 `aider_commit_hashes` 集合中的提交
2. 拒绝撤销已推送的提交
3. 拒绝撤销 merge 提交
4. 检查工作目录是否 dirty

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

### 影响分析 UI

回退前自动展示：
- 哪些文件会被修改（变更行数统计）
- 哪些新文件会被删除
- 对话历史回退到哪个节点

### 检查点存储

- Git 快照：`~/.gemini/history/<project_hash>`
- 对话历史 + 工具调用：`~/.gemini/tmp/<project_hash>/checkpoints`

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

- **Session Fork**：任意消息点创建分支
- **Restore-to-Message**：回退到指定消息的文件状态
- 快照存储：`~/.local/share/opencode/snapshot/{project_id}`

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
