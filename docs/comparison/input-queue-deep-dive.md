# 输入队列与中断机制 Deep-Dive

> 当 AI Agent 正在执行工具调用时，用户能否继续输入？输入会被丢弃、阻塞，还是排队等待下一轮？本文基于 Claude Code（v2.1.89 反编译）和 Qwen Code（Gemini CLI fork，开源）的源码分析，深度对比两者在输入队列、中断机制和交互流畅性方面的设计差异。

---

## 1. 问题定义

终端 AI Agent 的典型交互模式是 **"用户输入 → Agent 执行 → 用户输入 → …"** 的多轮对话。一个关键 UX 问题是：

**Agent 执行期间（API 调用、工具执行、文件写入），用户的键盘输入如何处理？**

| 设计策略 | 体验 | 代表 |
|----------|------|------|
| **丢弃** | 输入丢失，用户需重新输入 | 早期 CLI 工具 |
| **阻塞** | 输入框不可用，必须等 Agent 完成 | 部分 IDE Agent |
| **排队** | 输入被缓存，Agent 完成后自动执行 | Claude Code、Qwen Code |
| **排队 + 中断** | 排队的同时可中断当前执行 | Claude Code |
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
│     │ 命令队列       │   queryGuard.end()                        │
│     │ ┌───────────┐ │              │                             │
│     │ │ now  (0)  │ │   useQueueProcessor                       │
│     │ │ next (1)  │ │──────────────┘                             │
│     │ │ later(2)  │ │   isActive=false + queue.length>0          │
│     │ └───────────┘ │   → processQueueIfReady()                  │
│     └───────────────┘   → dequeue() → 自动执行下一轮              │
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
| `next` | 1 | 用户键入（默认） | 当前 turn 结束后**自动**执行 |
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

  // 立即入队，不等待当前 turn
  enqueue({
    value: finalInput.trim(),
    mode,
    priority: 'next',
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

### 2.8 Early Input（启动阶段输入捕获）

用户输入 `claude` 后立即开始打字——此时 REPL 尚未初始化。Early Input 机制在启动阶段原始模式捕获 stdin，REPL 就绪后注入输入框：

```typescript
// 源码: utils/earlyInput.ts#L29-L60
export function startCapturingEarlyInput(): void {
  process.stdin.setRawMode(true)   // 原始模式
  readableHandler = () => {
    let chunk = process.stdin.read()
    while (chunk !== null) {
      processChunk(chunk)           // 逐字符处理：Ctrl+C 退出、退格删除、转义序列忽略
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

### 3.5 取消机制（两层）

```typescript
// 源码: agent-interactive.ts#L227-L259
cancelCurrentRound(): void {           // 取消当前轮
  this.roundCancelledByUser = true
  this.roundAbortController?.abort()   // 仅取消当前 round 的 AbortController
  // → runLoop 继续处理队列中的下一条消息
}

abort(): void {                        // 全局终止
  this.masterAbortController.abort()   // 终止所有执行
  this.queue.drain()                   // 禁止新消息入队
  this.pendingApprovals.clear()
  // → runLoop 检测到 masterAbortController.signal.aborted → 设为 CANCELLED
}
```

| 操作 | Claude Code | Qwen Code |
|------|------------|-----------|
| 取消当前轮 | `abort('interrupt')` + 工具级粒度 | `cancelCurrentRound()` → round 级 |
| 全局终止 | `abort('user-cancel')` + `forceEnd()` | `abort()` + `drain()` |
| 取消后队列 | 队列保留，继续处理 | `drain()` 清空队列 |

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
| 输入立即可见 | ✅ 队列在 UI 中渲染 | ❌ 无队列可视化 |
| 可编辑已排队输入 | ✅ Esc 弹出到输入框 | ❌ 入队后不可编辑 |
| 多条排队 | ✅ 按优先级排序 | ✅ FIFO 顺序 |
| 自动执行下一轮 | ✅ useQueueProcessor Hook | ✅ runLoop while 循环 |

### 4.4 中断粒度

| 粒度 | Claude Code | Qwen Code |
|------|------------|-----------|
| 工具级 | ✅ `interruptBehavior: 'cancel' \| 'block'` | ❌ |
| Round 级 | ✅ `abort('interrupt')` | ✅ `cancelCurrentRound()` |
| 全局级 | ✅ `abort('user-cancel')` + `forceEnd()` | ✅ `abort()` + `drain()` |
| 中断后队列 | 保留，自动继续 | `drain()` 清空 |

### 4.5 预测与预执行

| 能力 | Claude Code | Qwen Code |
|------|------------|-----------|
| Prompt Suggestion | ✅ 预测下一步输入 | ❌ |
| Speculation | ✅ 预执行预测结果 | ❌ |
| Early Input | ✅ 启动阶段捕获键入 | ❌ |
| Tab 接受 | ✅ 预执行结果直接注入 | — |

---

## 5. 体验差异根因分析

用户感知 **"Claude Code 输入可纳入下一轮，Qwen Code 要等任务完成"** 的根本原因不是能否排队（两者都可以），而是以下差异的叠加效应：

### 5.1 可视化反馈

Claude Code 的队列在 prompt 下方实时渲染，用户**看得到**自己的输入已被排队。Qwen Code 无队列可视化，用户不确定输入是否生效，体感上像"被忽略"。

### 5.2 自动衔接机制

两者都有自动执行下一轮的机制，但触发方式不同：

- **Claude Code**：React `useEffect` 订阅 `useSyncExternalStore`，状态变更**同步**触发 re-render → 自动 dequeue。Turn 间衔接延迟约为一个 React 渲染周期（~16ms）。
- **Qwen Code**：`runLoop()` 内的 `while` 循环，在 `await runOneRound()` resolve 后**同步** dequeue。Turn 间衔接延迟为 0（同一 microtask）。

实际上 Qwen Code 的衔接**更快**（同一事件循环 tick），但因缺少可视化反馈，用户感知不到。

### 5.3 中断恢复

Claude Code 中断后队列保留，Qwen Code 的 `abort()` 调用 `drain()` 清空队列。当用户在执行中按 Ctrl+C 后，Claude Code 的排队输入仍在，Qwen Code 的排队输入丢失。

### 5.4 Speculation 零等待

Claude Code 的 Speculation 系统在用户还未输入时就预测并预执行下一步。当用户按 Tab 接受建议时，结果已经准备好——体感上是**零延迟**。这是两者差距最大的地方，Qwen Code 完全没有等价机制。

---

## 6. 其他 Agent 对比

| Agent | 队列模型 | 执行中可输入 | 优先级 | 中断粒度 | 预测/预执行 |
|-------|----------|:-----------:|:------:|----------|:----------:|
| **Claude Code** | 优先级队列 | ✅ | 3 级 | 工具级 | ✅ |
| **Qwen Code** | FIFO 队列 | ✅ | 无 | Round 级 | ❌ |
| **Gemini CLI** | FIFO 队列 | ✅ | 无 | Round 级 | ❌ |
| **Copilot CLI** | 无队列 | ❌ 阻塞 | — | 全局级 | ❌ |
| **Aider** | 无队列 | ❌ 阻塞 | — | 全局级 | ❌ |
| **Codex CLI** | 无队列 | ❌ 阻塞 | — | 全局级 | ❌ |
| **Cursor** | IDE 事件队列 | ✅ | 无 | 全局级 | ❌ |

> Copilot CLI、Aider、Codex CLI 在 Agent 执行期间使用同步阻塞模式，stdin 被 Agent 进程占用。Cursor 基于 VS Code 事件循环，输入不阻塞但无优先级调度。

---

## 7. 关键源码文件

### Claude Code

| 文件 | 行数 | 职责 |
|------|------|------|
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
| `packages/core/src/agents/runtime/agent-interactive.ts` | ~350 | 交互代理（消息循环 + 取消） |
| `packages/cli/src/ui/contexts/KeypressContext.tsx` | ~170 | Ink 键盘输入捕获 |

---

## 8. 设计启示

### 对 Agent 开发者

1. **队列可视化**比队列本身更重要——用户看不到排队状态就会认为输入被丢弃
2. **中断不应清空队列**——用户中断的是当前操作，不是排队的后续指令
3. **优先级队列**允许系统消息（如远程控制命令）不等待用户输入处理
4. **状态机需要覆盖异步间隙**——布尔锁在 React 的异步渲染模型中会导致竞态

### 对用户

- Claude Code 用户可以在 Agent 执行时**放心输入**——输入不会丢失，会自动成为下一轮
- Qwen Code 用户同样可以输入，但 `abort()` 后队列会被清空——避免在取消后依赖已排队的输入
- Speculation 是 Claude Code 独有的"零等待"体验——但仅限 Anthropic 内部用户（`USER_TYPE === 'ant'`）

> **免责声明**: 以上分析基于 2026 年 Q1 源码，后续版本可能已变更。Qwen Code 为 Gemini CLI fork，其队列模型继承自 Gemini CLI。
