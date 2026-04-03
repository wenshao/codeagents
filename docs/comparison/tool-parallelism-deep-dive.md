# 工具并行执行 Deep-Dive

> 当模型一次返回多个工具调用时，Agent 如何执行它们？串行逐个执行还是智能并行？本文基于 Claude Code（v2.1.89 反编译）和 Qwen Code（v0.15.0 开源）的源码分析，对比两者在工具执行并发模型、依赖分析和流式处理方面的架构差异。

---

## 1. 问题定义

现代 LLM 可在一次响应中返回多个 `tool_use` block。例如模型可能同时请求：

```
tool_use: Read("src/main.ts")
tool_use: Read("src/config.ts")  
tool_use: Grep("TODO", "src/")
tool_use: Bash("npm test")
```

前三个是只读操作，可安全并行；第四个可能依赖前三个结果。Agent 如何处理这种混合场景？

---

## 2. Claude Code：智能分批 + 流式执行

### 2.1 并发配置

```typescript
// 源码: services/tools/toolOrchestration.ts#L8-L12
function getMaxToolUseConcurrency(): number {
  return parseInt(process.env.CLAUDE_CODE_MAX_TOOL_USE_CONCURRENCY || '', 10) || 10
}
// 默认最大 10 个工具并发，可通过环境变量调整
```

### 2.2 分批算法

Claude Code 将工具调用分为**连续的批次**，每批要么全部并行，要么单独串行：

```typescript
// 源码: services/tools/toolOrchestration.ts#L91-L116
function partitionToolCalls(toolUseMessages, toolUseContext): Batch[] {
  return toolUseMessages.reduce((acc, toolUse) => {
    const isConcurrencySafe = tool?.isConcurrencySafe(parsedInput.data) ?? false
    // fail-closed: 解析失败时视为不安全
    
    if (isConcurrencySafe && acc[acc.length - 1]?.isConcurrencySafe) {
      acc[acc.length - 1].blocks.push(toolUse)  // 追加到当前并行批次
    } else {
      acc.push({ isConcurrencySafe, blocks: [toolUse] })  // 新批次
    }
    return acc
  }, [])
}
```

**分批规则**：
- 连续的并发安全工具 → 合并为一个并行批次
- 遇到非并发安全工具 → 独立为一个串行批次
- 非并发安全工具后的并发安全工具 → 新的并行批次

**示例**：

```
输入: [Read, Read, Grep, Edit, Read, Read]
分批: [Read, Read, Grep]  →  [Edit]  →  [Read, Read]
       ↑ 并行批次(3个)    ↑ 串行      ↑ 并行批次(2个)
```

### 2.3 isConcurrencySafe() 分类

每个工具定义自己是否并发安全：

```typescript
// 源码: Tool.ts#L402, L759
// 默认实现（fail-closed）
isConcurrencySafe: (_input?: unknown) => false
```

| 工具 | 并发安全 | 原因 |
|------|:--------:|------|
| FileReadTool | ✅ | 纯读取 |
| GlobTool | ✅ | 纯读取 |
| GrepTool | ✅ | 纯读取 |
| WebFetchTool | ✅ | 无副作用 |
| WebSearchTool | ✅ | 无副作用 |
| BashTool | ⚠️ 条件 | 仅当命令被判定为只读时 |
| FileEditTool | ❌ | 文件修改 |
| FileWriteTool | ❌ | 文件写入 |
| AgentTool | ❌ | 子进程副作用 |
| 其他 | ❌ | 默认不安全 |

### 2.4 并行执行路径

```typescript
// 源码: services/tools/toolOrchestration.ts#L152-L177
async function* runToolsConcurrently(toolUseMessages, ...): AsyncGenerator<MessageUpdate> {
  yield* all(
    toolUseMessages.map(async function* (toolUse) {
      // 标记为执行中
      toolUseContext.setInProgressToolUseIDs(prev => new Set(prev).add(toolUse.id))
      // 执行工具
      yield* runToolUse(toolUse, ...)
      // 标记完成
      markToolUseAsComplete(toolUseContext, toolUse.id)
    }),
    getMaxToolUseConcurrency(),  // 并发上限: 10
  )
}
```

`all()` 是自定义的并发 AsyncGenerator 合并器，限制最大并发数。

### 2.5 上下文修改队列（防竞态）

并行执行的工具可能修改共享上下文（如文件状态缓存）。Claude Code 使用**队列化**策略：

```typescript
// 源码: services/tools/toolOrchestration.ts#L31-L62
// 并行批次：上下文修改先队列化，批次结束后按工具顺序串行应用
const queuedContextModifiers: Record<string, Function[]> = {}
for await (const update of runToolsConcurrently(...)) {
  if (update.contextModifier) {
    queuedContextModifiers[toolUseID].push(modifyContext)
  }
}
// 批次完成后：
for (const block of blocks) {
  for (const modifier of queuedContextModifiers[block.id] ?? []) {
    currentContext = modifier(currentContext)  // 按工具顺序串行应用
  }
}
```

```typescript
// 源码: services/tools/toolOrchestration.ts#L118-L150
// 串行批次：上下文修改立即应用
for (const toolUse of toolUseMessages) {
  for await (const update of runToolUse(toolUse, ..., currentContext)) {
    if (update.contextModifier) {
      currentContext = update.contextModifier.modifyContext(currentContext)  // 立即
    }
  }
}
```

### 2.6 StreamingToolExecutor（流式路径）

当 `config.gates.streamingToolExecution` 开启时，工具在 API 响应**流式到达时**就开始执行，无需等待完整响应：

```typescript
// 源码: services/tools/StreamingToolExecutor.ts#L129-L150
private canExecuteTool(isConcurrencySafe: boolean): boolean {
  const executingTools = this.tools.filter(t => t.status === 'executing')
  return (
    executingTools.length === 0 ||                              // 无工具执行中
    (isConcurrencySafe && executingTools.every(t => t.isConcurrencySafe))  // 都是安全的
  )
}
```

**工具状态机**：

```
queued → executing → completed → yielded
```

**Bash 错误级联**：

```typescript
// 源码: StreamingToolExecutor.ts#L359-L363
if (tool.block.name === BASH_TOOL_NAME) {
  this.hasErrored = true
  this.siblingAbortController.abort('sibling_error')
  // Bash 失败时取消同批次其他工具（隐式依赖假设）
}
```

仅 Bash 工具的错误会级联取消兄弟工具——因为 Bash 命令常有隐式依赖（如 `mkdir` 失败后续命令无意义）。

### 2.7 查询循环集成

```typescript
// 源码: query.ts#L561-L568, L1366-L1382
const toolUpdates = streamingToolExecutor
  ? streamingToolExecutor.getRemainingResults()  // 流式路径
  : runTools(toolUseBlocks, ...)                  // 非流式路径（partitionToolCalls）

for await (const update of toolUpdates) {
  yield update.message       // 逐条 yield 结果
  toolResults.push(...)      // 收集
}
```

---

## 3. Qwen Code：类型分流 + 顺序执行

### 3.1 执行模型

Qwen Code 不按并发安全性分批，而是按**工具类型**分流：

```typescript
// 源码: qwen-code/packages/core/src/core/coreToolScheduler.ts#L1303-L1314
// Agent 工具 → 并发（独立子代理，无共享状态）
const taskCalls = callsToExecute.filter(c => c.request.name === ToolNames.AGENT)
// 其他所有工具 → 顺序
const otherCalls = callsToExecute.filter(c => c.request.name !== ToolNames.AGENT)

const taskPromise = Promise.all(
  taskCalls.map(tc => this.executeSingleToolCall(tc, signal)),  // 并发
)
const othersPromise = (async () => {
  for (const toolCall of otherCalls) {
    await this.executeSingleToolCall(toolCall, signal)           // 顺序
  }
})()
await Promise.all([taskPromise, othersPromise])  // 两组同时执行
```

### 3.2 工具状态机（7 状态）

```
validating → scheduled → awaiting_approval → executing → success / error / cancelled
```

```typescript
// 源码: coreToolScheduler.ts#L86-L163
type Status = 'validating' | 'scheduled' | 'awaiting_approval'
             | 'executing' | 'success' | 'error' | 'cancelled'
```

### 3.3 权限流程

5 阶段权限评估（源码: `coreToolScheduler.ts#L842-L940`）：

```
L3(Tool 默认) → L4(PermissionManager 策略) → L5(ApprovalMode) → Hooks → 非交互处理
```

### 3.4 无流式工具执行

Qwen Code 等待完整 API 响应后才开始工具执行，不支持流式到达时即执行。

---

## 4. 逐维度对比

| 维度 | Claude Code | Qwen Code |
|------|------------|-----------|
| **并发模型** | 按 `isConcurrencySafe()` 智能分批 | 按工具类型分流（Agent 并发 / 其他顺序） |
| **默认并发上限** | 10（`CLAUDE_CODE_MAX_TOOL_USE_CONCURRENCY`） | Agent 工具无限制 / 其他为 1 |
| **安全判定** | 每个工具实现 `isConcurrencySafe(input)` | 仅 Agent 工具硬编码为并发安全 |
| **分批策略** | 连续并发安全工具合并为一批 | 全局分两组（Agent vs 其他） |
| **流式执行** | ✅ 工具在 API 响应流到达时开始执行 | ❌ 等待完整响应 |
| **上下文修改** | 并行时队列化，批次后串行应用 | 顺序执行，立即应用 |
| **错误级联** | Bash 错误取消同批次兄弟 | 无级联，各工具独立 |
| **工具状态机** | 4 状态（queued/executing/completed/yielded） | 7 状态（含 validating/awaiting_approval） |
| **进度显示** | 并行工具各自独立显示进度 | 顺序显示当前执行工具 |

---

## 5. 性能影响

### 5.1 典型场景对比

| 场景 | Claude Code | Qwen Code |
|------|------------|-----------|
| 模型返回 5 个 Read 调用 | **并行**执行，~1× 延迟 | **顺序**执行，~5× 延迟 |
| 模型返回 3 个 Read + 1 个 Edit + 2 个 Read | 批次 1: 3×Read 并行 → 批次 2: Edit 串行 → 批次 3: 2×Read 并行 | 6 个工具顺序执行 |
| 模型返回 2 个 Agent 调用 | 并行（如果 Agent 工具 `isConcurrencySafe` 返回 true） | **并行**（Agent 工具始终并发） |
| 模型返回 1 个 Bash + 1 个 Read | Bash 串行 → Read 串行（Bash 非并发安全） | 顺序执行（同） |

### 5.2 大规模代码探索

当模型需要探索大型代码库时（典型 pattern：多个 Glob + Grep + Read），Claude Code 的并行执行优势显著：

```
Claude Code: [Glob₁ + Glob₂ + Grep₁ + Grep₂ + Read₁ + Read₂ + Read₃]
             → 一个并行批次，~1× 延迟（受最慢工具限制）

Qwen Code:   Glob₁ → Glob₂ → Grep₁ → Grep₂ → Read₁ → Read₂ → Read₃
             → 7× 延迟（顺序执行）
```

---

## 6. 关键源码文件

### Claude Code

| 文件 | 行数 | 职责 |
|------|------|------|
| `services/tools/toolOrchestration.ts` | ~189 | 分批算法 + 并行/串行执行路径 |
| `services/tools/StreamingToolExecutor.ts` | ~531 | 流式工具执行 + 状态机 + Bash 错误级联 |
| `Tool.ts` | L402, L759 | `isConcurrencySafe()` 接口定义 + 默认实现 |
| `utils/generators.ts` | L32-L72 | `all()` 并发 AsyncGenerator 合并器 |
| `query.ts` | L561-L568 | 流式 vs 非流式路径选择 |

### Qwen Code

| 文件 | 行数 | 职责 |
|------|------|------|
| `packages/core/src/core/coreToolScheduler.ts` | 1,710 | 工具调度器（Agent 并发 / 其他顺序） |
| `packages/core/src/agents/runtime/agent-core.ts` | L485 | `processFunctionCalls` 调用调度器 |
| `packages/core/src/agents/runtime/agent-events.ts` | L27-L40 | 工具事件类型定义 |

---

## 7. 设计启示

1. **`isConcurrencySafe()` 比类型分流更精确**：Claude Code 允许每个工具根据输入参数动态判断安全性（如 Bash 只读命令可并行），而 Qwen Code 硬编码 Agent 为唯一并发类型
2. **流式执行缩短总延迟**：Claude Code 在 API 响应流到达时就开始执行工具，不等完整响应，进一步重叠 I/O
3. **上下文修改队列化是并行执行的前提**：没有竞态保护，并行工具可能产生不一致的文件状态缓存
4. **Bash 错误级联**是一个值得借鉴的设计：Bash 命令失败后取消兄弟工具，避免无意义执行

> **免责声明**: 以上分析基于 2026 年 Q1 源码（Claude Code v2.1.89、Qwen Code v0.15.0），后续版本可能已变更。
