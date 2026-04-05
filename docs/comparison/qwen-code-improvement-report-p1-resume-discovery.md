# Qwen Code 改进建议 — P1 会话恢复发现与导航

> 会话恢复改进项：不仅要“能 resume”，还要在多目录、多 worktree、长历史会话中更容易找到并恢复正确的 session。
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md)

---

<a id="item-1"></a>

### 1. Worktree-aware Resume + Agentic Session Search（P1）

**思路**：现有“会话恢复”讨论通常聚焦在崩溃后如何继续执行、如何重建 transcript、如何恢复上下文状态。但从日常使用体验看，用户在 `/resume` 前真正遇到的第一个问题往往不是“能不能恢复”，而是：

- 我到底该恢复哪一个 session？
- 这个 session 是不是在另一个 worktree 里启动的？
- 如果它来自同一仓库的另一个 worktree，能不能直接恢复？
- 如果它来自完全不同的目录，能不能给我正确的恢复命令？
- 当我只记得“之前聊过某个 bug / 某个 API 设计”，能不能靠语义而不是时间顺序把它找出来？

Claude Code 在这一层明显更完整：它不仅有 resume 命令，还实现了 **跨项目 / worktree 感知的恢复导航**，以及 **基于 session 元数据与 transcript 的 agentic semantic search**。这使 `/resume` 从“打开一个历史列表”变成“帮用户重新回到正确工作上下文”的恢复工作流。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/crossProjectResume.ts` | `checkCrossProjectResume()`：区分同目录、同 repo worktree、不同项目三类恢复场景 |
| `utils/agenticSessionSearch.ts` | `agenticSessionSearch()`：综合 title/tag/branch/summary/transcript 做语义检索 |
| `commands/resume/resume.tsx` | `/resume` 交互入口 |

从 `crossProjectResume.ts` 可以直接看到 Claude Code 会区分三种结果：
- `isCrossProject: false`：当前目录直接恢复；
- `isSameRepoWorktree: true`：同一仓库 worktree，可直接恢复；
- 不同项目：生成 `cd <projectPath> && claude --resume <sessionId>` 的正确命令。

而 `agenticSessionSearch.ts` 则不是简单的字符串过滤：它会综合 `title`、`tag`、`branch`、`summary`、`first message`、`transcript` 等字段，优先用字面命中做预筛，再把候选交给小模型做更宽松的语义召回与排序。

**Qwen Code 现状**：Qwen Code 已有基础 session 恢复能力，但更偏“列表式浏览”。

- `packages/cli/src/ui/commands/resumeCommand.ts`：`/resume` 只是打开 dialog；
- `packages/cli/src/ui/components/SessionPicker.tsx`：主要展示 `prompt + 相对时间 + messageCount + gitBranch`，支持上下移动与按 branch 过滤；
- `packages/core/src/services/sessionService.ts`：支持分页列出本项目会话、按 mtime 排序、加载完整会话数据；
- 但当前没有看到：
  - 跨目录 / worktree 恢复导航；
  - 不同项目时生成正确恢复命令；
  - 基于 transcript 的语义搜索；
  - “我只记得聊过什么，不记得时间和标题”这种使用场景下的高召回检索。

换句话说，Qwen Code 现在更像“session list picker”，而不是“resume discovery system”。

**Qwen Code 修改方向**：
1. 在 session metadata 中显式保留项目路径 / worktree 信息；
2. `/resume` 入口增加 cross-project/worktree 判断：
   - 当前目录：直接恢复；
   - 同 repo worktree：直接恢复或提示 worktree 路径；
   - 不同项目：给出可复制的 `cd ... && qwen --resume ...` 命令；
3. 在 `SessionPicker` 上层增加搜索模式，不只按时间排序和 branch 过滤；
4. 引入 agentic session search：在 title/branch/summary 命中的基础上，再把 transcript 摘要交给小模型做相关性排序；
5. 将“恢复导航”与“崩溃恢复”分层：前者解决“找得到正确 session”，后者解决“恢复后能否无缝续跑”。

**实现成本评估**：
- 涉及文件：~6 个
- 新增代码：~320 行
- 开发周期：~4 天（1 人）
- 难点：session 元数据扩展与语义搜索结果排序

**改进前后对比**：
- **改进前**：`/resume` 主要是按时间顺序列历史会话——跨目录场景需要用户自己判断，想找老会话主要靠滚动和记忆
- **改进后**：`/resume auth bug` 可直接按语义找回相关 session；若 session 属于同仓库其他 worktree，则直接提示正确恢复路径；若来自不同项目，则生成可执行恢复命令

**意义**：长周期、多分支、多 worktree 工作流下，找对 session 和恢复 session 同样重要。
**缺失后果**：历史会话越多，`/resume` 越像时间排序日志——用户知道“以前聊过”，却很难高效回到那次上下文。
**改进收益**：恢复导航 worktree-aware + 语义搜索，让 session 从“日志文件”升级成“可检索、可回到的工作资产”。

---

## 为什么这不是现有“会话崩溃恢复”条目的重复

- **会话崩溃恢复与中断检测** 关注的是：session 异常中断后如何重建状态并继续执行；
- **Worktree-aware Resume + Agentic Search** 关注的是：用户如何在大量历史 session 中找到正确会话，并在跨目录 / worktree 场景下恢复到正确位置。

前者是 **恢复执行引擎**，后者是 **恢复发现与导航层**，问题层次不同。

---

## 可分阶段演进路径

| 阶段 | 能力 | 说明 |
|------|------|------|
| Stage 1 | 路径感知 resume | 区分当前目录 / 同 repo worktree / 不同项目 |
| Stage 2 | resume command suggestion | 对跨项目 session 自动生成恢复命令 |
| Stage 3 | metadata search | title/branch/summary 搜索 |
| Stage 4 | agentic transcript search | transcript 摘要 + 小模型语义召回 |

这样 Qwen Code 的 session 恢复才能从“按时间翻列表”升级为“按上下文找回工作”。

---

## 相关文章

- [Git 工作流与会话管理](./git-workflow-session-deep-dive.md)
- [Qwen Code 改进建议总览](./qwen-code-improvement-report.md)
