# Qwen Code 改进建议 — PR Webhook 事件实时订阅 (PR Webhook Event Subscription)

> 核心洞察：当我们使用大模型对 GitHub / GitLab 上的 Pull Request (PR) 进行 Code Review 时，当前的业界普遍做法是一次性执行脚本（One-off Execution）。比如，有新的 Commit 提交了，CI 触发跑一次 Agent，Agent 留下一条审查评论然后进程就退出了。但是，如果人类开发者在这个审查下面跟评（“这个变量为什么不能叫 id？”），Agent 是“听不见”的。若要让它继续回答，必须人类再手工去触发一次 CI 任务。Claude Code 在其 Coordinator（调度者模式）下实现了一种极具想象力的持续聆听机制——通过动态的 Webhook 订阅工具，Agent 能在一个活跃的会话中实时“监听并对话”；而 Qwen Code 目前还是传统的“跑完即走”架构。
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md)

## 一、一锤子买卖带来的沟通割裂

### 1. Qwen Code 现状：一次性审查的哑巴助理
设想我们通过一个 GitHub Actions 使用 Qwen Code 实现了自动 Code Review：
- **痛点一（失去连贯上下文）**：人类在 PR 评论区对 Agent 的审查结论提出疑问，由于之前的 Agent 进程已经死掉，系统只能重新起一个全新的 Agent 实例去读取这段长长的新旧代码，它完全丢失了上一次它自己“为什么这么改”的思维链（Thinking Process）。
- **痛点二（极高的操作摩擦）**：如果你在这个 PR 里改了一行代码，导致了另一个 Linting CI 报错，传统的 Agent 不会主动发现这件事。你需要手工在 PR 里敲个命令（例如 `@qwen-code please fix CI`），这完全不具备主动智能（Proactive Intelligence）的特性。

### 2. Claude Code 的赛博外挂：长连接监听
在 Claude Code 的顶级架构（如 `coordinator/coordinatorMode.ts` 和内部的 `ToolPool` 中），隐藏了一对极其先进的系统级工具：`subscribe_pr_activity` 与 `unsubscribe_pr_activity`。

#### 机制一：让大模型自己决定是否“驻留”
当一个 Coordinator Agent（主调度的核心模型）收到审查代码的任务时，它可以通过调用 `subscribe_pr_activity` 工具。这使得底层的 Node 进程不再于生成完一条代码建议后立刻 `process.exit(0)`。
相反，进程会转入后台挂起（后台可能利用了 GitHub App 的 WebSocket 事件转发、或者长轮询 Polling 机制），保持一个长效的会话连接（Persistent Session）。

#### 机制二：事件映射为 User Message (Event Injection)
这是最精妙的一步！
当 GitHub 上的该 PR 发生了任何变动（例如：另一个 Reviewer 留下了评论，或者底层的单元测试 CI 返回了 Failed 状态），底层的 Webhook 接收器会将这些 JSON 结构化的平台事件，动态“捏造”成一条条 `UserMessage`：
> `[System Notification] The CI test "Jest E2E" just failed on the latest commit with error: Null Pointer Exception...`

这段话会被直接推（Inject）给挂在后台的主大模型。大模型在收到这个“意外的聊天消息”后，会瞬间被唤醒，开始自动思考修复方案，并直接在这个打开的长会话中推回代码补丁！

## 二、Qwen Code 的改进路径 (P2 优先级)

让工具从“被动响应器”蜕变为“主动并肩作战的战友”。

### 阶段 1：开发轮询或 SSE 监听网关
如果是为了降低开发复杂度，可以先从“长轮询（Polling）”做起。
1. 在 `packages/core/src/services/` 中开发 `githubActivityMonitor.ts`。
2. 它接受一个指定的 PR Number。并在后台使用一个不会阻断事件循环的 `setInterval`，每 15 秒通过 `octokit` 查询该 PR 的最新 comments 列表。

### 阶段 2：实现消息注入层 (Event Injection Pipeline)
1. 建立基准锚点（Cursor）：记录 Agent 自己最后一次说话的时间或最后处理的 Comment ID。
2. 一旦拉取到比这个时间新的、由其他人类用户或系统留下的 Comment。
3. 拦截当前的交互流框（通常是等待终端人工输入的 `inquirer`），并强制使用新的 Comment 作为输入，唤醒下一轮 `runReasoningLoop`。

### 阶段 3：大模型内置订阅工具
向带有高权限的主 Agent 注册工具：
```json
{
  "name": "watch_pr",
  "description": "Call this to keep the session alive and automatically respond to human comments or CI failures in the PR."
}
```
通过大模型自主调用来控制是否启用长监听，在节省 API 费用和保持主动响应之间做到完美平衡。

## 三、改进收益评估
- **实现成本**：高。它挑战了传统命令行工具“输入->输出->结束”的短生命周期范式，需要将底层的状态机改为长期活跃的守护进程（Daemon）模式，并应对断网容错等各种边缘分支。
- **直接收益**：
  1. **超越界限的协作感**：它彻底模糊了人类与 AI 的协作边界。在 PR 页面下，AI 成为了一个随叫随到、并且时刻旁听技术讨论的“活体同事”。
  2. **终极自动化闭环**：结合之前提到的并发与子代理技术，Qwen Code 有望成为能完全托管整个 Code Review 生命周期的“超级监理”。