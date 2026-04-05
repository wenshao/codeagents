# Qwen Code 改进建议 — BriefTool 异步用户消息通道 (Async User Messaging)

> 核心洞察：当 Agent 在后台持续工作数分钟时，用户真正缺的往往不是“最终答案”，而是“中途能不能收到一条高信号的状态消息”。Claude Code 为此单独设计了 `BriefTool`：Agent 可以在不中断当前工具执行的前提下，主动向用户发送一条异步消息，必要时还可以附上截图、日志或 diff 文件。这与普通 assistant 回复、阻塞式提问工具、todo 面板完全不是一回事。Qwen Code 目前已经拥有 `todo_write`、`ask_user_question`、`exit_plan_mode` 等流程工具，但仍缺少一个真正面向用户、非阻塞、可并发、可带附件的“主动消息通道”。
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md)

## 一、问题定义：长任务场景下，用户需要“异步可见性”

在实际使用 Agent 时，最常见的不确定感通常发生在这类场景：

- 让 Agent 重构一批测试，预计要跑 3 分钟
- 让 Agent 生成 PR 描述、检查构建、整理 diff
- 让 Agent 在后台继续分析多个文件或子任务

如果系统只能在“任务全部完成之后”一次性给出最终回复，用户会遇到几个问题：

| 场景 | 没有异步消息通道时的问题 |
|------|------------------------|
| 长任务执行 | 不知道现在做到哪一步 |
| 途中发现 blocker | Agent 只能等到最后统一报错 |
| 用户短暂离开终端 | 回来后看不到关键中间事件 |
| 想附带证据 | 无法自然地把截图、日志、diff 当作“消息附件”发给用户 |

这类需求不能简单交给：
- 普通 assistant 文本输出
- 阻塞式 `ask_user_question`
- 内部 `todo_write`
- 状态栏 UI

因为它们的语义都不一样。

真正缺的是一个底层原语：

> **Agent 可以在继续工作的同时，随时主动给用户发一条清晰、轻量、可选带附件的消息。**

这正是 Claude Code 的 `BriefTool` 所解决的问题。

---

## 二、Claude Code 的做法：把“给用户发消息”做成一个一等工具

Claude Code 没有把这件事藏在 UI hack 或隐式日志里，而是直接把它定义成一个正式 Tool。

### 1. `BriefTool.ts`：明确的输入模型

`tools/BriefTool/BriefTool.ts` 定义的输入非常有代表性：

- `message`：要发送给用户的消息正文
- `attachments`：可选附件路径
- `status`：`normal` 或 `proactive`

这三个字段一起说明，Claude 设计的并不是一个简单的“toast 通知”：

1. 它是 **用户可读消息**，而不是内部事件
2. 它支持 **附件**，意味着它可以成为“证据传递通道”
3. 它区分 **被动响应** 与 **主动提醒**，说明这是带交互语义的消息系统

尤其 `status` 字段很关键：
- `normal`：正常回复用户刚刚说的话
- `proactive`：用户没问，但系统认为“现在必须让用户看到”

这相当于把“消息的重要性与主动性”显式建模了。

### 2. 它是主输出通道，而不是旁路功能

源码中的 `searchHint` 直接写着：

> `send a message to the user — your primary visible output channel`

这句定义非常重要。它意味着在 Claude 的某些模式下，BriefTool 不只是“附加功能”，而是：

> **模型向用户发出可见消息的主要机制。**

这与很多 CLI Agent 的思路完全不同。很多工具默认把所有用户可见信息都揉进 assistant 最终文本里；Claude 则把“主动发送用户消息”提升成独立协议层。

### 3. 并发安全：`isConcurrencySafe()`

`BriefTool` 明确返回：

```ts
isConcurrencySafe() {
  return true
}
```

这意味着它天生适合在其他工具执行期间并行触发，而无需像写文件、改配置那样串行排队。

这点非常关键，因为如果一个“用户消息工具”本身不能并发，就会丧失它作为实时状态通道的意义。

Claude 实际上是在告诉调度器：
- 这是个只读型工具
- 它不会破坏系统状态
- 可以安全地和其他工作同时发生

对于长任务中的进度播报，这个设计非常自然。

### 4. 附件支持：消息不只是一行文本

`BriefTool` 的另一项强能力是附件处理：
- 输入允许 `attachments`
- `validateAttachmentPaths()` 先做路径校验
- `resolveAttachments()` 将附件解析为带 metadata 的结构
- 输出中返回 `path / size / isImage / file_uuid`

这表明 Claude 不是把 Brief 视为纯文本聊天气泡，而是把它当成：

> **轻量但完整的“用户通知消息 + 证据载体”协议。**

举例来说，Agent 可以：
- 发一条“测试失败，关键日志已附上”
- 发一条“浏览器截图见附件，这里是我发现的 UI 偏移”
- 发一条“差异摘要如下，完整 patch 在附件中”

这类能力会显著提升长任务场景中的可解释性。

### 5. 启用机制：entitlement + opt-in + feature gate

`BriefTool.ts` 还展示了 Claude 对这个能力的产品化态度非常克制：

- `isBriefEntitled()`：是否有权限使用 Brief
- `isBriefEnabled()`：当前 session 是否真正启用
- 与 `feature('KAIROS')` / `feature('KAIROS_BRIEF')`、GrowthBook、assistant mode、用户 opt-in 联动

这说明 Claude 不是简单把消息功能粗暴默认开启，而是把它做成：
- 可灰度发布
- 可 kill-switch
- 可按模式启用
- 可通过 UI/flag/命令 opt-in

这对新交互原语很重要，因为“太多主动消息”很容易打扰用户。Claude 通过 feature gate 与 opt-in，把这个风险控制在协议层。

**Claude Code 关键源码**：
- `tools/BriefTool/BriefTool.ts`

---

## 三、为什么 Qwen Code 现有工具不能替代 BriefTool

Qwen Code 不是没有“与用户交互”的能力，但这些能力的语义与 BriefTool 有本质差别。

### 1. `ask_user_question`：它是阻塞式决策，不是异步消息

`packages/core/src/tools/askUserQuestion.ts` 的用途非常清晰：
- 收集用户偏好
- 让用户做实现选择
- 在执行过程中提问澄清

它默认需要用户确认与答复，而且在非交互模式下还会受限。这说明它本质上是：

> **等待用户参与决策的交互工具**

而 BriefTool 是：

> **Agent 单向发给用户的主动消息通道**

两者的差异至少体现在：

| 维度 | `ask_user_question` | BriefTool |
|------|---------------------|-----------|
| 交互方向 | Agent → 用户，并等待回答 | Agent → 用户，通常无需回答 |
| 是否阻塞流程 | 通常会 | 不需要 |
| 目标 | 决策/澄清 | 状态通知/证据传递 |
| 非交互模式适配 | 受限 | 更适合控制器/桥接场景 |

所以 `ask_user_question` 不能替代 BriefTool。

### 2. `todo_write`：它是内部任务面板，不是用户消息

`packages/core/src/tools/todoWrite.ts` 的职责是：
- 组织任务列表
- 追踪进度
- 对复杂任务做结构化管理

这当然非常有价值，但它主要解决的是：

> **Agent 如何管理自己的工作计划**

而不是：

> **Agent 如何主动把关键中间状态发给用户**

todo 适合记录：
- 已完成哪些任务
- 当前进行到哪一项
- 后续还有什么待办

但它不适合承载下面这种用户体验：
- “我刚发现测试卡在 migration 阶段”
- “这里有一张截图，UI 问题很明显”
- “我先把排查结果发给你，你回来后可以直接看”

换句话说，todo 是工作台，不是消息总线。

### 3. `exit_plan_mode`：它是流程切换，不是通用消息

`exit_plan_mode` 代表的是一个明确的 workflow transition：
- 已完成规划
- 准备请求用户批准

这类工具是流程节点，不是通用通信原语。

### 4. 终端输出与状态栏也不是一回事

Qwen 未来即使继续强化：
- 动态状态栏
- 右侧面板
- 背景代理进度

这些也依然不能完整替代 BriefTool。

因为它们主要是 **UI 呈现层**，而 BriefTool 是 **模型可直接调用的消息协议层**。

这个差别决定了：
- UI 能否出现是前端实现问题
- BriefTool 能否被模型稳定使用，是系统能力问题

---

## 四、差距本质：Qwen 缺的是“异步用户消息协议”，不是某个 UI 小组件

| 维度 | Claude Code BriefTool | Qwen Code 当前状态 |
|------|-----------------------|---------------------|
| 主动向用户发消息 | 有 | 无独立通道 |
| 不中断当前工作流 | 有 | 缺失 |
| 并发安全 | 有 | 无对应工具 |
| 附件支持 | 有 | 无对应工具 |
| 主动/被动语义区分 | `proactive` / `normal` | 无 |
| Feature Gate / opt-in | 有 | 无对应能力 |

因此这里最值得强调的不是“Qwen 少了一个通知功能”，而是：

> **Qwen 还没有把“Agent 向用户主动发异步消息”设计成一等协议。**

这会带来一个很直接的结果：

- 要么把中途状态硬塞进最终回复
- 要么过度依赖阻塞式提问
- 要么只能靠 UI 面板被动展示，而模型本身没有显式消息出口

这些方案都不如 BriefTool 清晰。

---

## 五、Qwen Code 的改进路径

### 阶段 1：新增 `brief` / `send_user_message` 工具

最小实现可以先在 `packages/core/src/tools/` 新建一个只读工具，例如：
- `message: string`
- `status?: 'normal' | 'proactive'`
- `attachments?: string[]`

至少先让模型拥有一个显式的用户消息出口。

### 阶段 2：将其标记为并发安全

如果这个工具只负责把消息事件推给 UI / ACP / controller，它天然应具备：
- `readOnly`
- `isConcurrencySafe`

这样才能在长任务执行中即时播报状态，而不是排队等其他工具结束。

### 阶段 3：把附件作为一等输入

Qwen 现有生态里已经有：
- 文件读取
- 差异生成
- web fetch
- MCP / channel / IDE companion 等外部桥接基础设施

因此附件支持并不是毫无基础。下一步可以允许模型附带：
- 图片
- 日志文件
- patch/diff
- 生成的报告文件

这会让“中间结果通知”从一句话升级为“可审阅事件”。

### 阶段 4：对接现有 UI 与 ACP 通道

BriefTool 的输出不一定要只在 CLI 主界面显示。Qwen 其实还有多个潜在落点：
- CLI 终端 UI
- IDE companion
- ACP/stream-json 控制器
- channels（如果未来允许桥接到外部端）

也就是说，这个工具非常适合做成“统一消息出口”，由不同前端各自决定如何展示。

### 阶段 5：加 gate，避免打扰用户

Claude 的一个重要经验是：这类能力必须防噪音。

Qwen 若引入同类工具，建议一开始就考虑：
- 默认关闭或限量启用
- 只在特定模式打开
- 控制 proactive 消息频率
- 提供用户设置来关闭异步播报

否则很容易从“高信号消息”退化为“刷屏”。

---

## 六、为什么这个改进点值得优先补齐

### 1. 它能显著改善长任务体验

很多 Agent 任务失败并不是因为能力不够，而是因为用户在等待时缺乏信心：
- 不知道它是不是卡住了
- 不知道是否需要介入
- 不知道中间是否已经发现风险

BriefTool 可以明显降低这种不确定感。

### 2. 它与现有 Qwen 工具形成互补，而不是冲突

- `todo_write`：管理计划
- `ask_user_question`：请求决策
- `exit_plan_mode`：请求批准
- `brief`：主动播报高信号状态

这四类工具组合起来，Qwen 的人机交互层会更完整。

### 3. 它非常适合未来的控制器生态

一旦 Qwen 继续强化：
- IDE 集成
- ACP
- channels
- 后台代理

“主动异步消息”会成为越来越基础的需求。越早做成协议层，后续越容易复用。

---

## 七、结论

Claude Code 的 BriefTool 证明了一件事：

> **用户可见的中间状态，不应该只是 UI 上偶然出现的一行字，而应该是一个模型可调用、并发安全、支持附件、具备主动性语义的正式工具。**

Qwen Code 当前虽然已经有 `todo_write`、`ask_user_question`、`exit_plan_mode` 等优秀流程工具，但还没有一条真正的“Agent → 用户异步消息通道”。

因此这个改进点最准确的描述不是：
- 再做一个通知组件
- 再加一个问答框
- 再做一个状态栏提示

而是：

> **把“异步用户消息”补成一等协议能力，让 Agent 能在不中断工作的情况下，向用户主动发送高信号消息与附件。**

这会显著改善长任务、后台任务和多前端集成场景下的可见性与信任感。

---

## 关键源码索引

### Claude Code
- `tools/BriefTool/BriefTool.ts`

### Qwen Code
- `packages/core/src/tools/askUserQuestion.ts`
- `packages/core/src/tools/todoWrite.ts`
- `packages/core/src/tools/exitPlanMode.ts`

> **免责声明**：以上结论基于 2026-04 本地源码与当前仓库文档对比，后续版本可能已变更。