# Qwen Code 改进建议 — Command Queue Orchestration（命令队列编排）

> 核心洞察：当用户在 Agent 还没完成当前回合时继续输入新指令，系统到底只是“把几条文本先存起来”，还是已经具备一个统一的、带优先级和类型感知的命令队列？Claude Code 在这件事上明显走得更远：它不是单纯堆积用户消息，而是把 user input、bash 输入、task notification、channel message、孤儿权限请求等统一成模块级队列，提供优先级调度、订阅式快照、可见性过滤，以及专门的 queued commands UI。Qwen Code 当前则更接近“流式响应期间的消息缓冲区”：`useMessageQueue` 只维护 `string[]`，空闲后一次性拼接提交。两者差异不只是实现细节，而是交互系统抽象层级的差异。
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md)

## 一、为什么“命令队列”值得单独写一篇

在简单 CLI 工具里，用户排队输入几条消息并不复杂：
- 当前回答没结束
- 先把输入记下来
- 等模型空闲再一次性交出去

但在更成熟的 Agent 系统里，真正要排队的往往不只有“用户文本消息”：

| 队列对象 | 典型例子 |
|---------|---------|
| 用户下一条 prompt | `run the tests` |
| shell / bash 输入 | 在 shell mode 中补一条命令 |
| task notification | 子任务完成、后台任务结束 |
| channel message | 外部入口送来的消息 |
| orphaned permission | 权限请求没有在当前主交互中及时消费 |
| system-generated tick | 某些异步机制主动注入的命令 |

一旦队列对象变多，就会出现几个核心问题：

1. **不同对象是否共用一条统一队列？**
2. **谁优先？用户输入应不应该被系统通知饿死？**
3. **哪些队列项应该显示给用户，哪些应该静默处理？**
4. **UI 如何展示一堆异构命令，而不是只列几行字符串？**
5. **React 和非 React 逻辑如何共享这条队列？**

Claude Code 已经把这些问题系统化；Qwen Code 目前还停留在“排队中的文本消息”这一层。

---

## 二、Claude Code：统一命令队列，而不是单纯消息缓冲

### 1. `messageQueueManager.ts`：模块级统一 command queue

Claude 的 `utils/messageQueueManager.ts` 直接把问题抽象到了更高层：

> **所有 command 都进同一条模块级队列。**

源码注释写得很清楚：
- `All commands — user input, task notifications, orphaned permissions — go through this single queue.`
- React 组件通过 `useSyncExternalStore` 订阅
- 非 React 代码也可以直接读取 `getCommandQueue()` / `getCommandQueueLength()`

这意味着 Claude 并没有把队列视为某个组件局部状态，而是：

> **队列是交互运行时的基础设施。**

这点很关键，因为一旦队列是模块级基础设施，它才能被：
- 输入组件使用
- 流式打印循环使用
- 各类异步通知使用
- 多种 UI 视图共享

### 2. 队列项是 typed command，不是裸字符串

Claude 队列中的对象不是 `string`，而是 `QueuedCommand`。从后续逻辑可以看出，队列项至少拥有：
- `value`
- `mode`
- `priority`
- 可用于过滤的其他元信息

这带来决定性的能力差异：
- bash 输入可特殊渲染
- task notification 可聚合
- channel message 可作为例外显示
- 某些 meta command 可隐藏

也就是说，Claude 的队列不是“存文本”，而是“存有类型和调度语义的命令对象”。

### 3. 优先级是内建语义：`now > next > later`

Claude 的 `messageQueueManager.ts` 明确内建：

```ts
const PRIORITY_ORDER: Record<QueuePriority, number> = {
  now: 0,
  next: 1,
  later: 2,
}
```

`enqueue()` 默认 `next`，而 `enqueuePendingNotification()` 默认 `later`。这背后体现了很明确的产品决策：

> **用户的直接输入，默认应优先于系统通知。**

这可以避免一个典型问题：
- 后台任务完成很多
- 系统不断吐 task notification
- 用户真正要输入的新指令反而被“系统噪声”挤到后面

Claude 通过优先级机制显式避免了这种情况。

### 4. 队列支持多种读写操作，而不只是 append + flush

Claude 队列提供的不是简单的 push/pop，而是一组完整操作：
- `enqueue()`
- `enqueuePendingNotification()`
- `dequeue(filter?)`
- `dequeueAll()`
- `peek(filter?)`
- `dequeueAllMatching(predicate)`
- `recheckCommandQueue()`

这说明它并不是一个“组件内部临时数组”，而是：

> **可被不同运行时环节反复探测、选择性消费、重新检查的共享队列。**

尤其 `filter` 版本的 `dequeue()` / `peek()` 非常重要，意味着：
- 某一消费方可以只取主线程相关 command
- 非匹配项留在队列中
- 系统不必为了不同消费方拆分多条平行数组

这是典型的队列编排能力，而不是普通消息缓存。

### 5. 队列还有订阅式快照，服务于 React 与非 React 双栈

Claude 通过：
- `subscribeToCommandQueue`
- `getCommandQueueSnapshot()`
- `useSyncExternalStore`

把 command queue 变成一个非常标准的外部 store。

`hooks/useCommandQueue.ts` 极薄，只负责：
- 订阅
- 取 snapshot

这说明 Claude 的架构边界很清晰：
- 队列管理在 util / runtime 层
- React 只是订阅者之一

这是非常适合复杂交互系统扩张的设计。

---

## 三、Claude 的 UI 层：不是显示文本列表，而是“队列命令投影”

### 1. `PromptInputQueuedCommands.tsx`：专门的 queued commands 组件

Claude 并没有把队列仅仅隐藏在内部，而是有一个专门的 UI 组件：
- `components/PromptInput/PromptInputQueuedCommands.tsx`

它会：
- 使用 `useCommandQueue()` 订阅队列
- 根据 `isQueuedCommandVisible()` 过滤可见项
- 针对不同 mode 做不同处理
- 将 command 转换为消息渲染

这说明在 Claude 的产品语义里，“排队中的命令”本身就是用户需要感知的一等对象。

### 2. 隐藏 idle notification，控制系统噪声

该组件中特别定义了：
- `isIdleNotification()`

并在 `processQueuedCommands()` 里直接过滤 idle notification。这一点非常重要：

> **不是所有排队项都值得展示。**

很多系统做队列 UI 时，会把所有东西一股脑扔给用户，结果就是噪音太大。Claude 明显已经踩过坑，所以专门把 idle 类通知静默掉。

### 3. task notification 有上限与 overflow summary

Claude 还专门对 task notification 做了上限控制：
- 最多显示 3 条
- 超出的部分折叠成类似 `+N more tasks completed` 的 summary

这体现了非常成熟的产品经验：
- 队列 UI 的目标不是“完整日志”
- 而是“让用户知道发生了什么，同时别把输入区淹没”

### 4. 不同 mode 可做定制渲染

例如 bash 输入会被包装成：
- `<bash-input>...</bash-input>`

channel message 作为一个特例，即便某些 meta command 会被隐藏，它仍然应该显示，确保键盘用户能看到外部消息到达。

这类逻辑再次说明：

> **Claude 队列的核心不是 FIFO 文本，而是 typed commands + visibility policy + projection UI。**

---

## 四、Qwen Code：目前更像“流式阶段的消息缓冲”

Qwen 这部分并不是没有排队机制，但抽象层次明显更低。

### 1. `useMessageQueue.ts`：队列项只是 `string[]`

Qwen 的 `packages/cli/src/ui/hooks/useMessageQueue.ts` 非常直白：
- 状态是 `messageQueue: string[]`
- `addMessage(message: string)` 把文本压入数组
- `getQueuedMessagesText()` 用 `\n\n` 拼接
- streaming 结束、状态变成 idle 后，把整个数组 join 后一次性 `submitQuery()`

这套机制能解决一个最基本的问题：
- 模型还在回答时，用户继续输入
- 等模型空闲后，把几条输入拼成一条再送出去

但它也很明显地暴露出能力边界：
- 没有 typed item
- 没有 priority
- 没有 mode
- 没有 selective dequeue
- 没有多消费方共享
- 没有“哪些队列项该显示、哪些不该显示”的策略层

换句话说，Qwen 当前更像一个：

> **during-stream input buffer**

而不是统一命令队列。

### 2. `QueuedMessageDisplay.tsx`：只是文本预览组件

Qwen 的 `QueuedMessageDisplay.tsx` 做的事情也很简单：
- 展示前 3 条消息
- 把多余项折叠成 `... (+N more)`
- 每条只做文本 preview

它当然是有用的，但本质还是：

> **“排队文本列表”的展示**，不是“异构命令队列”的投影。

没有类型信息，UI 就很难进一步做：
- bash 输入高亮
- task notification 聚合
- channel message 特殊标识
- 不同来源的 visibility policy

### 3. 输入组件很强，但队列基础设施仍薄

Qwen 的 `InputPrompt.tsx` 本身其实已经有很多现代输入增强：
- command completion
- reverse search
- shell history
- followup suggestion
- prompt suggestion
- pasted content / attachment 处理

说明 Qwen 在“输入框能力”上并不弱。

但这恰恰凸显了另一个问题：

> **输入层已经越来越复杂，队列层却还停留在字符串缓冲。**

随着系统继续演进，如果没有更高抽象的 queue orchestration，后面会越来越难把：
- 用户输入
- 外部 channel 消息
- agent 通知
- 背景任务完成信号
- 权限提示
统一整合进来。

---

## 五、差距的本质：Qwen 不是缺“排队”，而是缺“统一命令队列抽象”

这篇里最重要的结论，不是“Qwen 没有 queue”。

Qwen 有，而且已经能解决一个实用问题：
- 用户在 streaming 时追加消息
- idle 后自动提交

但 Claude 更进一步的地方在于：

1. **队列项是 typed command，不是字符串**
2. **队列是模块级共享基础设施，不是局部 hook 状态**
3. **存在优先级调度，而不只是 FIFO 拼接**
4. **存在 selective dequeue / peek / matching consume**
5. **存在 visibility 策略与 UI 投影层**
6. **React 与非 React 运行时都能共享同一队列**

因此更准确的说法是：

> **Qwen 当前实现了“排队输入”，但还没有实现 Claude 那种统一的命令队列编排系统。**

---

## 六、Qwen Code 的改进方向

### 阶段 1：把 `string[]` 升级为 typed queue item

第一步不是大改 UI，而是先把队列对象升级为结构化类型，例如：
- `value`
- `mode`（prompt / bash / task-notification / channel / system）
- `priority`
- `source`
- 可见性 / 元信息字段

一旦 item typed 化，很多能力才有落点。

### 阶段 2：抽离成模块级 queue store

把现在的 `useMessageQueue()` 从组件级 hook，提升成共享 store：
- React 组件订阅 snapshot
- 非 React 执行环节也能 peek / dequeue

这样未来 channels、background tasks、remote messages 才能进统一编排层。

### 阶段 3：引入优先级与 selective consume

建议至少引入类似：
- `now`
- `next`
- `later`

并支持：
- `peek(filter)`
- `dequeue(filter)`
- `dequeueAllMatching(predicate)`

否则一旦异步来源增多，队列很容易失控。

### 阶段 4：把 queue UI 从“文本列表”升级为“命令投影”

对应 UI 层可逐步加入：
- bash command 特殊样式
- task notification 折叠摘要
- channel / system message 图标区分
- hidden / silent command 过滤

### 阶段 5：与现有异步能力自然对接

这个方向特别适合和已有 / 计划中的能力衔接：
- BriefTool 异步消息
- channels 外部消息入口
- background agent / auto backgrounding
- task completion notifications
- prompt suggestion / followup flows

如果这些能力未来都各自维护一套队列，系统会越来越碎；反之，统一 queue orchestration 会成为很强的交互中枢。

---

## 七、为什么这个主题适合现在独立成文

### 1. 源码证据足够集中

Claude 侧证据很清楚：
- `messageQueueManager.ts`
- `useCommandQueue.ts`
- `PromptInputQueuedCommands.tsx`

Qwen 侧也很直接：
- `useMessageQueue.ts`
- `QueuedMessageDisplay.tsx`
- `InputPrompt.tsx`

很容易形成一篇边界清晰的 deep-dive。

### 2. 与现有文档重合较低

它和这些文章只有邻近关系，但不是重复：
- `brieftool-async-user-messages-deep-dive.md`：讲异步对用户发消息
- `input-queue-deep-dive.md`：讲排队输入可重新编辑
- `prompt-suggestion-deep-dive.md`：讲预测下一步输入

而这篇讨论的是：

> **这些异步对象最终如何进入统一队列并被调度、过滤、展示。**

### 3. 它是一个“从局部 feature 走向运行时基础设施”的典型改进点

很多改进点只是补一个命令、一个对话框、一个 UI 小功能。

命令队列编排不一样，它影响的是整个交互运行时的组织方式。这种能力一旦补好，会对后续很多主题形成支撑。

---

## 八、结论

Claude Code 与 Qwen Code 在“排队输入”上的差距，不只是功能多少的差距，而是抽象层次的差距。

Claude 已经把这件事做成：
- 模块级统一 command queue
- typed queue item
- priority scheduling
- selective dequeue / peek
- visibility policy
- 专门的 queued commands UI

Qwen 当前则更接近：
- streaming 时把用户补充消息先缓存到 `string[]`
- idle 后 join 成一条文本提交
- 用简单列表预览前几项

因此这个改进点最准确的表述是：

> **把 Qwen 的“排队消息缓冲”升级为统一的命令队列编排系统，让用户输入、异步通知、外部消息与后台任务都能被同一条 typed queue 调度和展示。**

这会让 Qwen 后续很多交互能力拥有一个更稳固的底层组织层。

---

## 关键源码索引

### Claude Code
- `utils/messageQueueManager.ts`
- `hooks/useCommandQueue.ts`
- `components/PromptInput/PromptInputQueuedCommands.tsx`

### Qwen Code
- `packages/cli/src/ui/hooks/useMessageQueue.ts`
- `packages/cli/src/ui/components/QueuedMessageDisplay.tsx`
- `packages/cli/src/ui/components/InputPrompt.tsx`

> **免责声明**：以上结论基于 2026-04 本地源码与当前仓库文档对比，后续版本可能已变更。