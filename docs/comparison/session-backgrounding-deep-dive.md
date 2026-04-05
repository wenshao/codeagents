# Qwen Code 改进建议 — 自动后台化 Agent（Session Backgrounding）

> 核心洞察：当一次长任务已经启动，用户往往不是真的想“取消它”，而是想“先让它继续跑，我去做别的事，稍后再回来”。Claude Code 已经把这种需求实现成完整的 session backgrounding 机制：当前会话可以快速转后台继续执行，用户稍后再把它拉回前台，并通过后台任务列表统一查看状态。Qwen Code 当前虽然有 `fastModel` / background model 一类“后台任务模型”配置，但那更偏底层模型选择，而不是用户可感知的“当前会话后台化”工作流。两者差距不在于有没有 background 概念，而在于是否把“会话后台化”做成一等交互能力。
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md)

## 一、为什么“会话后台化”是单独的系统能力

CLI Agent 处理长任务时，用户通常会遇到几种典型场景：

1. 正在跑复杂修改、测试或大规模搜索，但用户不想一直盯着屏幕
2. 当前任务还在执行，用户突然想到另一个更紧急的问题
3. 同一个终端里需要同时跟踪多个耗时任务
4. 用户不想直接中断长任务，只想先把交互焦点切走

如果系统只有两种状态：
- 前台运行
- 直接中断

那么用户体验会很僵硬。真正成熟的交互系统应该提供第三种状态：

> **继续执行，但把当前 session 退到后台，等我需要时再前台恢复。**

这和“多 Agent”“异步通知”“任务恢复”有关，但又不等于它们。它更像是：

> **长任务的人机交互调度层。**

---

## 二、Claude Code：把当前 session 当成可后台化对象

Claude Code 在这一点上的优势，是它没有把后台化理解成“换个模型偷偷跑”，而是把**整个当前交互 session**都视为可 background / foreground 的对象。

### 1. `useSessionBackgrounding.ts`：当前 session 可直接转后台

Claude 的 `hooks/useSessionBackgrounding.ts` 注释写得非常直接：

- `Ctrl+B to background/foreground sessions`
- `Calling onBackgroundQuery to spawn a background task for the current query`
- `Re-backgrounding foregrounded tasks`
- `Syncing foregrounded task messages/state to main view`

这说明 Claude 的设计目标不是“后台做一些辅助工作”，而是：

> **把当前正在进行的 query / session 本身切到后台。**

`handleBackgroundSession()` 的逻辑清楚体现了这一点：
- 如果当前已有 `foregroundedTaskId`，就把它重新 background
- 否则调用 `onBackgroundQuery()`，把当前会话转成后台任务

这意味着前后台之间是双向切换，而不是单向逃逸。

### 2. 前后台切换是有显式状态的

Claude 不是靠“猜当前是不是后台任务”，而是在状态层显式维护：
- `foregroundedTaskId`
- `isBackgrounded`
- `tasks[taskId]`

这类状态设计非常关键，因为一旦你真的支持前后台切换，就必须清楚回答：
- 哪个任务当前被前台接管？
- 哪些任务只是后台运行？
- 任务完成后是否自动退出 foreground？
- Escape / abort 时谁接管控制器？

在 `useSessionBackgrounding.ts` 中，Claude 还会：
- 同步 foregrounded task 的 messages 到主视图
- 同步 loading state
- 把 foregrounded task 的 `abortController` 接到主交互上
- 在任务完成或 abort 后恢复 background 状态并清空 foreground view

这已经不是简单的 UI 切换，而是完整的 session 控制权转移。

### 3. foregrounded task 的消息会同步回主视图

Claude 的一个关键点是：

> **当前被拉回前台的后台任务，看起来就像重新接管了主会话。**

`useSessionBackgrounding.ts` 会检查：
- `foregroundedTask.messages`
- 仅在长度变化时同步到主消息区
- 同步 loading 状态
- 同步 abort controller

这意味着用户体验上不是“你去看一个单独的日志面板”，而是可以真正把后台任务“带回主对话体验里继续看”。

这是 session backgrounding 成熟度很高的表现。

---

## 三、Claude 的 UI 层：后台任务不是黑盒，而是可管理对象

### 1. `BackgroundTasksDialog.tsx`：完整后台任务管理界面

Claude 的 `components/tasks/BackgroundTasksDialog.tsx` 表明，这不是一个隐藏功能，而是完整的产品能力。

从源码可以看出，它支持：
- 列表模式 / 详情模式切换
- 自动跳过列表直接打开单任务详情
- 按类型区分任务
- 任务选择、导航、详情查看
- 结合 overlay / keybinding 的专门交互

更重要的是，后台任务类型非常丰富：
- `local_bash`
- `remote_agent`
- `local_agent`
- `in_process_teammate`
- `local_workflow`
- `monitor_mcp`
- `dream`
- `leader`

这说明 Claude 并不是只后台化“一个 shell 命令”，而是已经把后台任务抽象为平台级能力。

### 2. 任务列表有过滤和排序逻辑

`BackgroundTasksDialog.tsx` 中还体现了很多产品细节：
- foregrounded 的 `local_agent` 不再算 background task 列表项
- running 状态优先排序
- 再按时间排序
- teammates / workflow / remote session / bash 等按 UI 展示顺序组织

这些看起来像“列表实现细节”，其实恰恰说明这个功能已经经过真实使用打磨。

### 3. Claude 甚至有专门的背景提示组件

`components/SessionBackgroundHint.tsx` 进一步显示，Claude 不只是“支持 background”，还做了发现性设计：
- 用户按 `Ctrl+B`
- 首次触发 hint
- 双击确认才真正 background
- 和前景任务 background 行为做优先级协调
- 在 tmux 环境下还会调整快捷键提示文案

这说明 Claude 把“如何安全、可发现地让用户学会 background session”也当成产品的一部分。

这个 hint 的产品价值很大，因为 backgrounding 是高价值但并不天然显眼的功能。

---

## 四、Qwen Code：目前更像“后台模型配置”，而不是会话后台化

Qwen Code 并不是完全没有 background 相关概念，但从这次读到的源码看，它的重点还不在 session backgrounding。

### 1. `modelCommand.ts` 与 `settingsSchema.ts` 里的 background，更偏模型层

在 Qwen 的：
- `packages/cli/src/ui/commands/modelCommand.ts`
- `packages/cli/src/config/settingsSchema.ts`

可以看到 `--fast` / `fastModel` 这类设定，文案是：
- `Set fast model for background tasks`

这表明 Qwen 已经有一种思路：

> **某些后台任务可以使用不同模型。**

这是有价值的，但它解决的问题更偏：
- 性能 / 成本分层
- fast model vs main model 的调度

它并没有直接解决：
- 当前 session 如何一键转后台
- 用户如何看到后台 session 列表
- 如何把某个后台 session 拉回前台
- 如何同步后台 session 的消息与 abort 控制

也就是说，Qwen 现在更像：
- 有 background task 的模型配置

而 Claude 是：
- 有真正的 background session 工作流

### 2. 没看到等价的 foreground / background state machine

这次对照的 Claude 关键状态有：
- `foregroundedTaskId`
- `isBackgrounded`
- `tasks` 中的前后台切换

而 Qwen 这次读到的路径里，并没有看到明确对等的：
- session foreground / background 状态机
- foregrounded task message 同步
- abort controller 转移
- background tasks dialog

这说明 Qwen 当前至少在 CLI 主产品层，还没有 Claude 那种完整的 session backgrounding 体验。

### 3. 缺的不是“后台执行能力”，而是“后台交互能力”

这个区分非常重要。

很多系统都能做后台执行：
- 开一个线程
- 开一个子进程
- 用更快模型异步算一件事

但 Claude 解决的是更高一层的问题：

> **如何让用户把“当前正在进行的人机对话任务”无缝退到后台，并在之后恢复交互。**

Qwen 现在距离这一层还有明显差距。

---

## 五、差距本质：Qwen 缺的是 session lifecycle orchestration

如果只看表面，很容易把这个主题误读成：
- Claude 有后台任务
- Qwen 也有 background model
- 所以差距不大

实际上差距很大，因为两者在解决的问题层级不同。

Claude 解决的是：
1. 当前 query 如何转后台
2. 如何把后台任务重新 foreground
3. foreground task 如何同步消息到主视图
4. 如何共享 abort / loading 控制
5. 如何给用户可视化地管理后台任务
6. 如何通过 hint / keybinding 让能力可发现

Qwen 目前更多解决的是：
1. 后台任务用什么模型跑

所以更准确的表述应该是：

> **Qwen 不是缺 background 配置，而是缺“会话后台化”的完整生命周期编排。**

---

## 六、Qwen Code 的改进方向

### 阶段 1：先把“当前 session 后台化”做成显式动作

建议先引入一个明确入口，例如：
- 快捷键
- slash command
- UI action

让当前会话在任务执行中可以转成后台任务继续跑。

### 阶段 2：建立前后台状态机

核心状态至少包括：
- `foregroundedTaskId`
- task 是否 `isBackgrounded`
- 当前前台是否接管后台任务的消息流
- task 完成后是否自动退出 foreground

### 阶段 3：补一个后台任务管理界面

最小可行版本也应该支持：
- 查看后台任务列表
- 看状态（running / completed / failed）
- 进入某任务详情
- 把某任务切回前台

### 阶段 4：补消息与控制器同步

如果没有这个环节，foreground 只是“看详情”，而不是“恢复会话”。

真正完整的 foreground 应该同步：
- messages
- loading state
- abort controller
- 任务完成后的回收逻辑

### 阶段 5：把 backgrounding 与后续能力串起来

这个能力一旦补好，会自然支撑：
- 多任务并行工作流
- 长时间代码迁移 / 测试 / benchmark
- channels / remote control 下的异步任务管理
- background agent 与 notification 系统

也就是说，这不是单一 feature，而是未来很多高级交互能力的底座之一。

---

## 七、为什么这个主题适合现在独立成文

### 1. 源码证据集中、边界清晰

Claude 侧证据很集中：
- `useSessionBackgrounding.ts`
- `BackgroundTasksDialog.tsx`
- `SessionBackgroundHint.tsx`

Qwen 侧也很清楚：
- 目前能看到的是 background model 配置与命令
- 尚未看到会话级 background / foreground 交互闭环

### 2. 与现有文档重合较低

它和这些主题有联系，但不是重复：
- `agent-resume-continuation-deep-dive.md`
- `automatic-checkpoint-restore-deep-dive.md`
- `coordinator-swarm-orchestration-deep-dive.md`
- `brieftool-async-user-messages-deep-dive.md`

这些讲的是恢复、多 Agent、异步消息；而这篇讨论的是：

> **当前 session 如何退后台、继续跑、再回前台。**

主题边界很独立。

### 3. 对用户价值非常直观

用户很容易理解这个能力：
- “别停，先去后台跑着”
- “我待会儿回来继续看”

这比很多底层改进点更直观，也更容易转化为产品优先级。

---

## 八、结论

Claude Code 与 Qwen Code 在“后台能力”上的差距，不是有没有 background model 的差距，而是有没有把**当前会话后台化**做成一等交互能力的差距。

Claude 已经具备：
- session background / foreground 切换
- 显式状态机（`foregroundedTaskId` / `isBackgrounded`）
- 前台消息同步与 abort 控制接管
- 后台任务管理对话框
- 专门 hint / keybinding 发现机制

Qwen 当前更接近：
- 为 background tasks 提供模型配置
- 但没有完整的 session backgrounding 生命周期

因此这个改进点最准确的表述是：

> **把 Qwen 的“后台模型配置”升级为真正的“当前会话后台化”能力，让长任务能够脱离前台继续执行，并可被用户随时重新接回主交互。**

这会显著改善长任务、多任务和高频切换场景下的 CLI 使用体验。

---

## 关键源码索引

### Claude Code
- `hooks/useSessionBackgrounding.ts`
- `components/tasks/BackgroundTasksDialog.tsx`
- `components/SessionBackgroundHint.tsx`

### Qwen Code
- `packages/cli/src/ui/commands/modelCommand.ts`
- `packages/cli/src/config/settingsSchema.ts`

> **免责声明**：以上结论基于 2026-04 本地源码与当前仓库文档对比，后续版本可能已变更。