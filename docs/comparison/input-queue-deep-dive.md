# 输入队列与中断机制 Deep-Dive

> 当 AI Agent 正在执行工具调用时，用户能否继续输入？输入会被丢弃、阻塞，还是排队等待下一轮？本文基于 Claude Code（v2.1.89 反编译）和 Qwen Code（v0.15.0，Gemini CLI fork，开源）的源码分析，深度对比两者在输入队列、中断机制和交互流畅性方面的设计差异。

---

## 1. 问题定义

终端 AI Agent 的典型交互模式是 **"用户输入 → Agent 执行 → 用户输入 → …"** 的多轮对话。一个关键 UX 问题是：

**Agent 执行期间（API 调用、工具执行、文件写入），用户的键盘输入如何处理？**

| 设计策略 | 体验 | 代表 |
|----------|------|------|
| **丢弃** | 输入丢失，用户需重新输入 | 早期 CLI 工具 |
| **阻塞** | 输入框不可用，必须等 Agent 完成 | 部分 IDE Agent |
| **排队** | 输入被缓存，Agent 完成后自动执行 | Qwen Code |
| **排队 + Mid-Turn Drain** | 排队输入在当前 turn 的下一个 step 注入 | Claude Code |
| **排队 + 预测 + 预执行** | 预测下一步并提前执行 | Claude Code（Speculation） |

---

## 2. Claude Code：优先级队列 + QueryGuard 状态机

### 2.1 架构总览

```
┌──────────────────────────────────────────────────────────────────┐
│                     用户按下 Enter                                │
│                         ↓                                        │
│                 handlePromptSubmit()                              │
│                         ↓                                        │
│              queryGuard.isActive ?                                │
│             ┌────YES────┴────NO────┐                             │
│             ↓                      ↓                             │
│     ┌───────────────┐    ┌──────────────────┐                    │
│     │ enqueue()     │    │ executeUserInput()│                    │
│     │ priority:next │    │ queryGuard.tryStart()                 │
│     │ 清空输入框     │    │ → API 调用 + 工具执行                  │
│     └───────┬───────┘    └──────────────────┘                    │
│             │                      ↑                             │
│             │                      │                             │
│             ↓                      │                             │
│     ┌───────────────┐              │                             │
│     │ 命令队列       │                                            │
│     │ ┌───────────┐ │   路径 A: Mid-Turn Drain (query.ts)        │
│     │ │ now  (0)  │ │──▶ 工具执行完成后注入当前 turn 的下一 step  │
│     │ │ next (1)  │ │                                            │
│     │ │ later(2)  │ │   路径 B: Between-Turn (useQueueProcessor) │
│     │ └───────────┘ │──▶ queryGuard.end() → 自动执行下一轮       │
│     └───────────────┘                                            │
└──────────────────────────────────────────────────────────────────┘
```

> 源码: `utils/handlePromptSubmit.ts`、`utils/messageQueueManager.ts`、`hooks/useQueueProcessor.ts`

### 2.2 QueryGuard 状态机

QueryGuard 是一个 **同步** 状态机（不受 React 批量更新延迟影响），管理 Agent 执行生命周期：

```
        reserve()          tryStart()           end(gen)
 idle ──────────▶ dispatching ──────────▶ running ──────────▶ idle
  ▲                    │                                       │
  │    cancelReservation()                     forceEnd()      │
  │                    │                          │            │
  └────────────────────┘──────────────────────────┘────────────┘
```

```typescript
// 源码: utils/QueryGuard.ts#L29-L121
class QueryGuard {
  private _status: 'idle' | 'dispatching' | 'running' = 'idle'
  private _generation = 0

  reserve(): boolean {            // idle → dispatching（队列处理器预留）
    if (this._status !== 'idle') return false
    this._status = 'dispatching'
    return true
  }

  tryStart(): number | null {     // dispatching/idle → running（查询开始）
    if (this._status === 'running') return null
    this._status = 'running'
    return ++this._generation     // generation 防止过期 finally 块误操作
  }

  end(generation: number): boolean {  // running → idle（查询正常结束）
    if (this._generation !== generation) return false
    this._status = 'idle'
    return true
  }

  forceEnd(): void {              // 任何状态 → idle（Escape 强制终止）
    this._status = 'idle'
    ++this._generation            // 递增 generation 使旧 Promise 的 finally 失效
  }

  get isActive(): boolean {       // dispatching 和 running 均为 active
    return this._status !== 'idle'
  }
}
```

**为何需要 `dispatching` 状态？** 从 `dequeue()` 到 `onQuery()` 之间存在异步间隙。若无此状态，队列处理器会在间隙中重复 dequeue。`isActive` 覆盖 dispatching + running，阻止重入。

> 源码: `utils/QueryGuard.ts#L1-L26`（注释详解）

### 2.3 优先级队列

```typescript
// 源码: utils/messageQueueManager.ts#L42-L56
// 模块级单例队列，独立于 React 状态
const commandQueue: QueuedCommand[] = []
let snapshot: readonly QueuedCommand[] = Object.freeze([])  // useSyncExternalStore
const queueChanged = createSignal()
```

**三级优先级**：

| 优先级 | 数值 | 来源 | 处理策略 |
|--------|:----:|------|----------|
| `now` | 0 | UDS Socket / Remote Control 远程命令 | **中断当前 turn** 后立即执行 |
| `next` | 1 | 用户键入（默认） | Mid-turn drain 注入当前 turn，或 turn 结束后自动执行 |
| `later` | 2 | Task Notification / 系统消息 | 最低优先，不抢占用户输入 |

**Dequeue 算法**：遍历队列，找到最高优先级（最小数值）的第一个命令，支持 filter 过滤：

```typescript
// 源码: utils/messageQueueManager.ts#L167-L193
export function dequeue(filter?): QueuedCommand | undefined {
  let bestIdx = -1, bestPriority = Infinity
  for (let i = 0; i < commandQueue.length; i++) {
    const cmd = commandQueue[i]!
    if (filter && !filter(cmd)) continue
    const priority = PRIORITY_ORDER[cmd.priority ?? 'next']
    if (priority < bestPriority) { bestIdx = i; bestPriority = priority }
  }
  if (bestIdx === -1) return undefined
  const [dequeued] = commandQueue.splice(bestIdx, 1)
  return dequeued
}
```

### 2.4 Agent 执行中的输入处理

```typescript
// 源码: utils/handlePromptSubmit.ts#L313-L351
if (queryGuard.isActive || isExternalLoading) {
  // 仅允许 prompt 和 bash 模式入队
  if (mode !== 'prompt' && mode !== 'bash') return

  // 如果当前有可中断工具正在执行 → 中断它
  if (params.hasInterruptibleToolInProgress) {
    params.abortController?.abort('interrupt')
  }

  // 立即入队，不等待当前 turn（priority 默认 'next'）
  enqueue({
    value: finalInput.trim(),
    mode,
    // priority 未显式传递，enqueue() 内部默认 'next'
  })

  // 清空输入框——用户可以继续输入下一条
  onInputChange('')
  setCursorOffset(0)
  return
}
```

### 2.5 自动队列处理（Turn 间无缝衔接）

```typescript
// 源码: hooks/useQueueProcessor.ts#L28-L68
function useQueueProcessor({ executeQueuedInput, queryGuard }) {
  const isQueryActive = useSyncExternalStore(queryGuard.subscribe, queryGuard.getSnapshot)
  const queueSnapshot = useSyncExternalStore(subscribeToCommandQueue, getCommandQueueSnapshot)

  useEffect(() => {
    if (isQueryActive) return          // Agent 还在执行
    if (hasActiveLocalJsxUI) return    // 有 UI 对话框
    if (queueSnapshot.length === 0) return  // 队列为空

    processQueueIfReady({ executeInput: executeQueuedInput })
    // ↑ 自动 dequeue → handlePromptSubmit(queuedCommands) → 下一轮执行
  }, [queueSnapshot, isQueryActive, ...])
}
```

**关键点**：`useEffect` 依赖 `isQueryActive` 和 `queueSnapshot`。当 Agent turn 结束（`queryGuard.end()` → `isActive` 变 false）且队列非空，effect 自动触发，**无需用户任何操作**。

### 2.6 中断机制（三层）

| 层级 | 触发 | abort reason | 行为 |
|------|------|-------------|------|
| **工具级中断** | 用户在可中断工具执行中按 Enter | `'interrupt'` | 仅中断 `interruptBehavior: 'cancel'` 的工具（如 SleepTool），其他工具继续 |
| **优先级中断** | `now` 优先级命令入队 | `'interrupt'` | REPL 的 `useEffect` 检测到 `now` → 中断当前 turn |
| **用户取消** | Escape / Ctrl+C | `'user-cancel'` | `forceEnd()` → 立即停止所有工具，保留部分响应 |

```typescript
// 源码: services/tools/StreamingToolExecutor.ts#L210-L241
// 'interrupt' 信号仅取消 interruptBehavior === 'cancel' 的工具
// 'user-cancel' 信号取消所有工具
private getAbortReason(tool: TrackedTool) {
  if (signal.reason === 'interrupt') {
    return this.getToolInterruptBehavior(tool) === 'cancel'
      ? 'user_interrupted' : null  // 不可中断的工具被跳过
  }
  return 'user_interrupted'  // user-cancel 无差别取消
}
```

### 2.7 队列可视化与编辑

排队的命令在 prompt 输入框下方可见。用户按 Escape 可将队列中的可编辑命令弹出到输入框重新编辑：

```typescript
// 源码: utils/messageQueueManager.ts#L428-L484
export function popAllEditable(): { popped: QueuedCommand[]; newInput: string } {
  // 过滤掉 task-notification、isMeta 等不可编辑命令
  // 将可编辑命令从队列中移除，合并为输入文本返回
}
```

### 2.8 Early Input（启动阶段输入捕获 (Early Input Capture)）

用户输入 `claude` 后立即开始打字——此时 REPL 尚未初始化。Early Input 机制在启动阶段原始模式 (Raw Mode) 捕获 stdin，REPL 就绪后注入输入框：

```typescript
// 源码: utils/earlyInput.ts#L29-L60
export function startCapturingEarlyInput(): void {
  process.stdin.setRawMode(true)   // 原始模式 (Raw Mode)
  readableHandler = () => {
    let chunk = process.stdin.read()
    while (chunk !== null) {
      processChunk(chunk)           // 逐字符处理：Ctrl+C 退出、退格删除、转义序列 (Escape Sequence) 忽略
      chunk = process.stdin.read()
    }
  }
}
// REPL 就绪后: consumeEarlyInput() 取出缓冲区内容 → 预填充输入框
```

### 2.9 Speculation（预测 + 预执行）

在用户还未输入时，Claude Code 可预测下一步并**提前执行**：

```
Prompt Suggestion 生成 "generate README"  ← 源码: services/PromptSuggestion/
       ↓
Speculation 以该预测为假设输入，在 overlay 文件系统中预执行
       ↓
用户按 Tab 接受 → 预执行结果直接注入对话（省去等待时间）
用户输入其他内容 → Speculation abort，结果丢弃
```

> 详见 [10-Prompt Suggestions](../tools/claude-code/10-prompt-suggestions.md)

---

## 3. Qwen Code：FIFO 队列 + 布尔锁

### 3.1 架构总览

```
┌──────────────────────────────────────────────────────────────────┐
│                     用户按下 Enter                                │
│                         ↓                                        │
│                 enqueueMessage(message)                           │
│                         ↓                                        │
│                 processing ?                                     │
│             ┌────YES────┴────NO────┐                             │
│             ↓                      ↓                             │
│     ┌───────────────┐    ┌──────────────────┐                    │
│     │ queue.enqueue()│    │ runLoop()        │                    │
│     │ 等待当前 round │    │ processing=true  │                    │
│     │ 完成后被消费   │    │ while(dequeue()) │                    │
│     └───────────────┘    │   runOneRound()   │                    │
│                          │ processing=false  │                    │
│                          └──────────────────┘                    │
└──────────────────────────────────────────────────────────────────┘
```

> 源码: `qwen-code/packages/core/src/agents/runtime/agent-interactive.ts`、`qwen-code/packages/core/src/utils/asyncMessageQueue.ts`

### 3.2 AsyncMessageQueue（极简 FIFO）

```typescript
// 源码: qwen-code/packages/core/src/utils/asyncMessageQueue.ts#L22-L54
export class AsyncMessageQueue<T> {
  private items: T[] = []
  private drained = false

  enqueue(item: T): void {
    if (this.drained) return   // drain 后丢弃
    this.items.push(item)      // FIFO 入队
  }

  dequeue(): T | null {
    return this.items.length > 0 ? this.items.shift()! : null  // FIFO 出队
  }

  drain(): void { this.drained = true }  // 终止信号
  get size(): number { return this.items.length }
}
```

**对比 Claude Code**：无优先级、无 filter、无 useSyncExternalStore 集成、无可视化。

### 3.3 执行循环

```typescript
// 源码: agent-interactive.ts#L133-L155
private async runLoop(): Promise<void> {
  this.processing = true
  try {
    let message = this.queue.dequeue()
    while (message !== null && !this.masterAbortController.signal.aborted) {
      this.addMessage('user', message)
      await this.runOneRound(message)    // 完整执行一轮（含所有工具调用链）
      message = this.queue.dequeue()     // 取下一条
    }
    // 队列清空后判断状态
    this.settleRoundStatus()             // → IDLE 或 COMPLETED
  } finally {
    this.processing = false
  }
}
```

### 3.4 enqueueMessage 入口

```typescript
// 源码: agent-interactive.ts#L266-L271
enqueueMessage(message: string): void {
  this.queue.enqueue(message)
  if (!this.processing) {
    this.executionPromise = this.runLoop()  // 仅在空闲时启动循环
  }
  // 如果 processing === true：消息在队列中等待，
  // runLoop 的 while 循环会在当前 round 结束后消费
}
```

### 3.5 取消机制（三层）

```typescript
// 源码: agent-interactive.ts#L227-L259
cancelCurrentRound(): void {           // 1. 取消当前轮
  this.roundCancelledByUser = true
  this.roundAbortController?.abort()   // 仅取消当前 round 的 AbortController
  this.pendingApprovals.clear()
  // → runLoop 继续处理队列中的下一条消息（队列保留）
}

async shutdown(): Promise<void> {      // 2. 优雅关闭
  this.queue.drain()                   // 禁止新消息入队
  await this.executionPromise          // 等待当前处理完成
  // → 不中断当前 round，但不再处理新消息
}

abort(): void {                        // 3. 立即终止
  this.masterAbortController.abort()   // 终止所有执行
  this.queue.drain()                   // 禁止新消息入队
  this.pendingApprovals.clear()
  // → runLoop 检测到 abort 信号 → 循环退出 → 已排队项被放弃
}
```

| 操作 | Claude Code | Qwen Code |
|------|------------|-----------|
| 取消当前轮 | `abort('interrupt')` + 工具级粒度 | `cancelCurrentRound()` → round 级 |
| 优雅关闭 | — | `shutdown()` → drain + 等待当前轮完成 |
| 立即终止 | `abort('user-cancel')` + `forceEnd()` | `abort()` + `drain()` |
| 取消后队列 | 队列保留，继续处理 | `cancelCurrentRound`: 保留 / `abort`: 已排队项被放弃 |

---

## 4. 逐维度对比

### 4.1 队列模型

| 维度 | Claude Code | Qwen Code |
|------|------------|-----------|
| 数据结构 | `QueuedCommand[]` + 优先级排序 | `T[]` 简单数组 |
| 优先级 | 3 级（`now` / `next` / `later`） | 无 |
| Dequeue | 扫描最高优先级 + filter 支持 | `shift()`（FIFO） |
| React 集成 | `useSyncExternalStore` + frozen snapshot | 无 |
| 队列容量 | 无限制 | 无限制 |
| 终止语义 | 无 drain（队列始终可用） | `drain()` 后 enqueue 静默丢弃 |

### 4.2 状态机

| 维度 | Claude Code | Qwen Code |
|------|------------|-----------|
| 状态数 | 3（idle / dispatching / running） | 2（processing: true / false） |
| 防重入 | `dispatching` 状态覆盖异步间隙 | `processing` 布尔锁 |
| Generation | 递增计数器防止过期 finally 块 | 无 |
| React 集成 | `useSyncExternalStore` 同步快照 | 无（Ink 直接读状态） |

### 4.3 输入时机

| 场景 | Claude Code | Qwen Code |
|------|------------|-----------|
| Agent 执行中输入 | ✅ 输入框始终可用 | ✅ stdin 不阻塞 |
| 输入立即可见 | ✅ 队列在 UI 中渲染 (Rendering) | ❌ 无队列可视化 |
| 可编辑已排队输入 | ✅ Esc 弹出到输入框 | ❌ 入队后不可编辑 |
| 多条排队 | ✅ 按优先级排序 | ✅ FIFO 顺序 |
| 自动执行下一轮 | ✅ useQueueProcessor Hook | ✅ runLoop while 循环 |

### 4.4 中断粒度

| 粒度 | Claude Code | Qwen Code |
|------|------------|-----------|
| 工具级 | ✅ `interruptBehavior` 区分 cancel/block | ❌ |
| Round 级 | ✅ `abort('interrupt')` | ✅ `cancelCurrentRound()` |
| 全局级 | ✅ `abort('user-cancel')` + `forceEnd()` | ✅ `abort()` + `drain()` |
| 中断后队列 | 保留，自动继续 | `cancelCurrentRound`: 保留 / `abort`: 放弃 |

### 4.5 Turn 内输入注入（核心差异）

| 维度 | Claude Code | Qwen Code |
|------|------------|-----------|
| Turn 内 queue drain | ✅ 每个 step 之间 drain | ❌ 无 |
| Drain 位置 | `query.ts#L1550-L1643` | — |
| 注入方式 | `getAttachmentMessages()` → `toolResults` | — |
| 用户输入何时被模型看到 | **当前 turn 的下一个 step** | **整个 round 结束后的新 round** |
| Drain 过滤 | 斜杠命令排除，按 agentId 隔离 | — |

### 4.6 预测与预执行

| 能力 | Claude Code | Qwen Code（v0.15.0+） |
|------|------------|-----------|
| Prompt Suggestion | ✅ 默认开启 | ✅ 默认开启（`followupSuggestionsEnabled`） |
| Speculation | ✅（ant-only，`USER_TYPE === 'ant'`） | ✅ opt-in（`enableSpeculation: false` 默认关闭） |
| Overlay FS 隔离 | ✅ Copy-on-Write | ✅ Copy-on-Write（`/tmp/qwen-speculation/{pid}/`） |
| Tab 接受 → 结果注入 | ✅ 直接注入对话 | ✅ `acceptSpeculation()` → `addHistory()` |
| 工具安全分类 | ✅ `interruptBehavior` | ✅ `speculationToolGate.ts`（safe/write/boundary/unknown 4 类） |
| Pipelined Suggestion | ✅ speculation 完成后预生成下一个 | ✅ `generatePipelinedSuggestion()` |
| Early Input | ✅ 启动阶段 stdin 捕获 | ❌ |

> **重要变化**：Qwen Code v0.15.0（2026-04-03 合入 `#2525`）新增了完整的 follow-up suggestions + speculation 系统，架构与 Claude Code 高度相似。但 speculation 默认关闭，需手动启用。
>
> 源码: `qwen-code/packages/core/src/followup/`（6 个文件，~1,900 行）、`qwen-code/packages/cli/src/config/settingsSchema.ts#L520-L544`

---

## 5. 核心差异：Mid-Turn Queue Drain vs Between-Round Queue Drain

**这是两者最根本的架构差异。**

### 5.1 Claude Code：Turn 内 Mid-Turn Queue Drain

在 Claude Code 中，一个 "turn" 包含多个 "step"（API 调用 → 工具执行 → 结果收集 → 下一次 API 调用）。**在每个 step 之间**，`query.ts` 主动 drain 命令队列，将用户输入注入当前 turn：

```
Step 1: API 调用 → 模型返回 tool_use → 执行工具 → 收集 toolResults
                                                    ↓
                                          ┌─────────────────────────┐
                                          │ MID-TURN QUEUE DRAIN    │
                                          │                         │
                                          │ getCommandsByMaxPriority│
                                          │ → 获取排队中的用户输入    │
                                          │ → getAttachmentMessages  │
                                          │ → 转为 attachment        │
                                          │ → 注入 toolResults       │
                                          │ → removeFromQueue        │
                                          └─────────────────────────┘
                                                    ↓
Step 2: API 调用（toolResults 中包含用户新输入） → 模型同时处理工具结果 + 用户输入
```

**关键源码**：

```typescript
// 源码: query.ts#L1550-L1643
// 工具执行完成后，下一次 API 调用前——drain 命令队列
const sleepRan = toolUseBlocks.some(b => b.name === SLEEP_TOOL_NAME)
const queuedCommandsSnapshot = getCommandsByMaxPriority(
  sleepRan ? 'later' : 'next',     // SleepTool 时drain 更多级别
).filter(cmd => {
  if (isSlashCommand(cmd)) return false        // 斜杠命令不在 turn 内处理
  if (isMainThread) return cmd.agentId === undefined  // 主线程只取用户输入
  return cmd.mode === 'task-notification' && cmd.agentId === currentAgentId
})

// 将排队命令转为 attachment 消息，注入 toolResults
for await (const attachment of getAttachmentMessages(
  null, updatedToolUseContext, null,
  queuedCommandsSnapshot,                      // ← 用户排队输入
  [...messagesForQuery, ...assistantMessages, ...toolResults],
  querySource,
)) {
  yield attachment
  toolResults.push(attachment)                 // ← 注入到下一次 API 调用的上下文
}

// 从队列中移除已消费的命令
const consumedCommands = queuedCommandsSnapshot.filter(
  cmd => cmd.mode === 'prompt' || cmd.mode === 'task-notification',
)
if (consumedCommands.length > 0) {
  removeFromQueue(consumedCommands)
}
```

**效果**：用户在工具执行期间输入的消息，会在**当前 turn 的下一个 step** 被模型看到。模型可以根据新输入调整后续行为——无需等整个 turn 结束。

**Drain 优先级规则**：

| 条件 | Drain 级别 | Drain 内容 |
|------|----------|----------|
| 普通工具执行后 | `'next'` | 用户输入（mode: 'prompt'） |
| SleepTool 执行后 | `'later'` | 用户输入 + 任务通知 |
| — | — | 斜杠命令**始终排除**（turn 间处理） |

### 5.2 Qwen Code：Turn 间 dequeue

在 Qwen Code 中，`runReasoningLoop()` 内部**没有任何队列检查**。工具执行后直接进入下一轮 API 调用，不检查是否有新的用户输入：

```typescript
// 源码: qwen-code/packages/core/src/agents/runtime/agent-core.ts#L355-L533
while (true) {
  // 1. 检查 abort/限制
  // 2. API 调用 → 流式处理
  // 3. 工具执行
  const currentMessages = await this.processFunctionCalls(...)
  // 4. ROUND_END 事件
  // ← 这里没有任何 queue.dequeue() 或 queue check
  // 5. 继续下一轮循环
}
```

用户输入只在**外层** `runLoop` 的 `while` 循环中被 dequeue——即 `runOneRound()` **完全返回**之后：

```typescript
// 源码: agent-interactive.ts#L133-L155
let message = this.queue.dequeue()           // ← 仅在这里 dequeue
while (message !== null) {
  await this.runOneRound(message)            // 整个 round 执行完毕
  message = this.queue.dequeue()             // ← 然后才取下一条
}
```

### 5.3 对比图

```
Claude Code (Mid-Turn Drain):
═══════════════════════════════════════════════════════════
Turn 开始 → [Step1: API→工具] → queue drain → [Step2: API(含用户输入)→工具] → ... → end_turn
                                    ↑
                              用户在此期间输入
                              → 被注入到 Step2

Qwen Code (Between-Round Drain):
═══════════════════════════════════════════════════════════
Round 开始 → [API→工具→API→工具→...→完成] → dequeue → Round 开始(新消息) → ...
                                              ↑
                                        用户在此期间输入
                                        → 必须等整个 Round 结束
```

### 5.4 实际影响

| 场景 | Claude Code | Qwen Code |
|------|------------|-----------|
| Agent 分多步执行（Step1 修改 2 文件，Step2 修改 3 文件），用户在 Step1 完成后发现方向错误 | 用户输入 "停，先改 config.json" → Step1 的工具批次完成后 drain → Step2 的 API 调用中模型看到新指令 → 调整方向 | 用户输入相同内容 → 整个 round（所有 step）全部完成 → 新消息才被处理 |
| Agent 在运行长命令，用户想补充上下文 | 用户输入 "注意 port 要用 8080" → 当前工具批次完成后 drain → 下一个 step 的 API 调用中模型已知 | round 完成后才能看到 |
| 后台任务完成通知 | SleepTool 执行后自动 drain task-notification | 无法 mid-turn 感知任务完成 |

---

## 6. 其他差异（辅助因素）

### 6.1 可视化反馈

Claude Code 的队列在 prompt 下方实时渲染 (Rendering)，用户**看得到**自己的输入已被排队。Qwen Code 无队列可视化，用户不确定输入是否生效。

### 6.2 中断恢复

Claude Code 中断后队列**始终保留**（`messageQueueManager` 无 drain 机制）。Qwen Code 的行为取决于取消方式：

- **Escape** → `cancelCurrentRound()` → 队列保留，`runLoop` 继续处理下一条
- **`abort()`** → 循环退出 + `drain()` → 已排队消息被放弃

日常使用中 Escape 都保留队列，差异仅在程序级终止时显现。

> 源码: Qwen Code `AgentComposer.tsx#L88`（Escape → `cancelCurrentRound()`）

### 6.3 Speculation 预执行

两者现在都支持 Speculation 预执行，但启用状态不同：

| 维度 | Claude Code | Qwen Code |
|------|------------|-----------|
| 默认状态 | ant-only 自动启用 | **默认关闭**（`enableSpeculation: false`） |
| 启用方式 | `USER_TYPE === 'ant'` | 用户手动在 settings 中开启 |
| Overlay FS | 内存级覆盖层 | `/tmp/qwen-speculation/{pid}/{uuid}/` |
| 工具限制 | `interruptBehavior` 区分 | `speculationToolGate` 分 4 类（safe/write/boundary/unknown） |
| 最大 turn 数 | 无硬编码上限 | `MAX_SPECULATION_TURNS = 20` |
| Tab 接受路径 | 注入对话历史 | `acceptSpeculation()` → `addHistory()` 绕过队列 |
| Cache 共享 | prompt cache breakpoint 机制 | `saveCacheSafeParams()` 捕获 cache 参数 |

> Qwen Code 的 speculation 实现于 2026-04-03 合入（PR #2525），与 Claude Code 架构高度相似。
> 源码: `qwen-code/packages/core/src/followup/speculation.ts`（563 行）

---

## 7. 其他 Agent 对比

| Agent | 队列模型 | 执行中可输入 | Mid-Turn Drain | 优先级 | 中断粒度 | 预测/预执行 |
|-------|----------|:-----------:|:--------------:|:------:|----------|:----------:|
| **Claude Code** | 优先级队列 | ✅ | ✅ | 3 级 | 工具级 | ✅ |
| **Qwen Code** | FIFO 队列 | ✅ | ❌ | 无 | Round 级 | ✅ opt-in |
| **Gemini CLI** | FIFO 队列 | ✅ | ❌ | 无 | Round 级 | ❌ |
| **Copilot CLI** | 无队列 | ⚠️ 无排队 | ❌ | — | 全局级 | ❌ |
| **Aider** | 无队列 | ⚠️ 无排队 | ❌ | — | 全局级 | ❌ |
| **Codex CLI** | 无队列 | ⚠️ 无排队 | ❌ | — | 全局级 | ❌ |
| **Cursor** | IDE 事件队列 | ✅ | ❌ | 无 | 全局级 | ❌ |

> ⚠️ Copilot CLI（Ink）、Aider（prompt_toolkit）、Codex CLI（Rust TUI）均使用非阻塞 UI 框架，stdin 未被底层阻塞。但在 Agent 执行期间，输入框不可用或不可见——用户无法排队下一条消息，需等待当前 turn 完成后方可输入。这与 Claude Code / Qwen Code 的"执行中可输入 + 自动排队"模型本质不同。

---

## 8. 关键源码文件

### Claude Code

| 文件 | 行数 | 职责 |
|------|------|------|
| `query.ts` | ~1,728 | 主 Agent 循环（含 mid-turn queue drain #L1550-L1643） |
| `utils/messageQueueManager.ts` | ~548 | 优先级命令队列（模块级单例） |
| `utils/QueryGuard.ts` | 122 | 三状态状态机（idle/dispatching/running） |
| `utils/handlePromptSubmit.ts` | ~610 | 输入分发（直接执行 vs 入队） |
| `hooks/useQueueProcessor.ts` | 68 | React Hook 自动队列消费 |
| `utils/queueProcessor.ts` | ~96 | 队列处理逻辑（slash/bash/prompt 分类） |
| `utils/earlyInput.ts` | ~192 | 启动阶段 stdin 原始捕获 |
| `services/tools/StreamingToolExecutor.ts` | ~241 | 工具级中断（interrupt vs cancel 区分） |
| `services/PromptSuggestion/speculation.ts` | ~715 | Speculation 预执行引擎 |

### Qwen Code

| 文件 | 行数 | 职责 |
|------|------|------|
| `packages/core/src/utils/asyncMessageQueue.ts` | 54 | 通用 FIFO 队列 |
| `packages/core/src/agents/runtime/agent-core.ts` | ~540 | 推理循环（`runReasoningLoop`，无 mid-turn drain） |
| `packages/core/src/agents/runtime/agent-interactive.ts` | 512 | 交互代理（消息循环 + 三层取消） |
| `packages/core/src/followup/speculation.ts` | 563 | Speculation 引擎（v0.15.0 新增） |
| `packages/core/src/followup/suggestionGenerator.ts` | 367 | 建议生成 + 12 条过滤规则 |
| `packages/core/src/followup/overlayFs.ts` | 140 | Copy-on-Write overlay 文件系统 |
| `packages/core/src/followup/speculationToolGate.ts` | 146 | 工具安全分类（safe/write/boundary） |
| `packages/cli/src/ui/contexts/KeypressContext.tsx` | ~170 | Ink 键盘输入捕获 |

---

## 9. 设计启示

### 对 Agent 开发者

1. **Mid-Turn Queue Drain 是核心竞争力**——在工具批次之间注入用户输入，让模型在同一 turn 内响应方向修正，避免完成无用工作后再返工
2. **队列可视化**比队列本身更重要——用户看不到排队状态就会认为输入被丢弃
3. **中断不应清空队列**——用户中断的是当前操作，不是排队的后续指令
4. **优先级队列**允许系统消息（如远程控制命令）不等待用户输入处理
5. **状态机需要覆盖异步间隙**——布尔锁在 React 的异步渲染模型中会导致竞态

### 对用户

- Claude Code 用户可以在 Agent 执行时**放心输入**——输入不会丢失，会自动成为下一轮
- Qwen Code 用户同样可以输入，但 `abort()` 后已排队输入被放弃（`drain()` 阻止新入队 + abort 信号使循环退出）——Escape 取消当前轮则队列保留
- Speculation 预执行：Claude Code 仅限 Anthropic 内部用户（`USER_TYPE === 'ant'`）；Qwen Code v0.15.0 支持但默认关闭（需在 settings 中开启 `enableSpeculation`）

> **免责声明**: 以上分析基于 2026 年 Q1 源码（Claude Code v2.1.89、Qwen Code v0.15.0 commit `3bce84d`），后续版本可能已变更。Qwen Code 为 Gemini CLI fork，其队列模型继承自 Gemini CLI，follow-up suggestions + speculation 为 Qwen Code 独立实现。
