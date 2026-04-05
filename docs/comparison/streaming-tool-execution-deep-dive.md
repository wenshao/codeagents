# Qwen Code 改进建议 — 流式工具执行流水线 (Streaming Tool Execution Pipeline)

> 核心洞察：当大模型在一个回合中连续输出多个工具调用（Tool Calls）时，Qwen Code 必须等待模型将整个回合的所有文本和 JSON 全部生成完毕后，才开始串行或并行执行工具；而 Claude Code 实现了一个“流式工具执行流水线”（Streaming Tool Executor），在模型生成流的过程中，只要解析出一个工具调用，就立即异步启动执行，极大缩短了端到端延迟。
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md)

## 一、架构对比与性能瓶颈

### 1. Qwen Code 的当前实现：阻塞式执行
在 `packages/core/src/agents/runtime/agent-core.ts` 中，Qwen Code 的主运行循环 `runReasoningLoop` 是这样处理模型响应流的：

```typescript
// Qwen Code: 等待完整流结束后再执行
const functionCalls: FunctionCall[] = [];
for await (const streamEvent of responseStream) {
  // ... 收集所有的 functionCalls
  if (resp.functionCalls) functionCalls.push(...resp.functionCalls);
}

// 整个响应生成完毕后，才开始批量处理
if (functionCalls.length > 0) {
  currentMessages = await this.processFunctionCalls(functionCalls, ...);
}
```

**性能损耗分析**：
假设模型生成 5 个工具调用（例如连续读取 5 个不同文件）需要 3 秒钟，而这 5 个文件的 I/O 操作总共需要 1 秒钟。
在 Qwen Code 的架构下，总耗时为：`模型生成时间 (3s) + 工具执行时间 (1s) = 4s`。
前几个解析完毕的工具在排队干等模型生成完最后的话语。

### 2. Claude Code 的解决方案：流水线并发
在 `services/tools/StreamingToolExecutor.ts` 和 `query.ts` 中，Claude Code 通过引入异步并发流水线彻底消灭了这段干等的时间。

它在流式解析的过程中拦截工具块（Tool Use Block）：
```typescript
// Claude Code 的处理逻辑简述
const streamingToolExecutor = new StreamingToolExecutor(...);

// 在 API Stream 回调中：
onStreamChunk(chunk => {
    if (chunk.isToolUseBlockCompleted) {
        // 立即加入队列并尝试触发执行！
        streamingToolExecutor.addTool(toolBlock, message);
    }
});

// 在外部并发获取已经完成的结果
for (const result of streamingToolExecutor.getCompletedResults()) {
    // 渲染结果或装填进下一轮 Prompt
}
```
`StreamingToolExecutor` 维护了一个执行状态机（`queued` | `executing` | `completed`）。当判断一个工具是并发安全的（`isConcurrencySafe: true`，例如只读工具），它会在模型还在生成后续字符的同时，在后台发起子进程或异步 I/O 操作。

**性能优化结果**：
同样是生成 5 个工具耗时 3s，执行耗时 1s。
在 Claude Code 的流水线架构下，前几个工具在第 0.5s、1.0s 时就已经开始执行了，总耗时被压缩到了约 `max(模型生成时间 3s, 首工具生成时间+所有执行时间) ≈ 3s ~ 3.5s`。
**端到端延迟直接缩减了约 30% 到 50%（在多工具重度探索场景下尤为明显）。**

## 二、Qwen Code 的改进路径 (P1 优先级)

为了达到接近"零延迟"的丝滑体验，Qwen Code 需要重构 Agent 运行时的事件循环与工具调度器。

### 阶段 1：流式 JSON 拦截与触发器
1. 修改 `agent-core.ts` 中的流处理逻辑（或者在更底层的流合并层）。不能只维护简单的 `functionCalls` 数组。
2. 引入 `StreamingToolCallParser`，在 `streamEvent.type === 'chunk'` 期间，一旦某个 `functionCall` 的 JSON 参数对象闭合且有效，立即触发 `TOOL_CALL_READY` 事件。

### 阶段 2：重构 CoreToolScheduler 为动态队列
1. 当前的 `CoreToolScheduler` 是在收集齐所有 Calls 后一次性初始化的（`const scheduler = new CoreToolScheduler(...)`）。
2. 需要将其重构为长生命周期的动态队列（类似 Claude Code 的 `StreamingToolExecutor`）。它应当拥有 `.addTool(call)` 方法。
3. 每当 `TOOL_CALL_READY` 被触发，立即通过 `.addTool` 压入调度器。调度器根据并发策略（是否为只读命令等）决定是立即执行还是挂起等待。

### 阶段 3：UI 渲染解耦
1. CLI 与 TUI 组件需要能够响应增量抛出的 `TOOL_RESULT`，而不是等待整个 `processFunctionCalls` 返回。
2. 这样用户可以看到 Agent 边写字（思考），状态栏里的 Spinner 边显示某个工具已经执行完毕并反馈了结果。

## 三、改进收益评估
- **实现成本**：中。需要改造核心事件循环（异步生成器改造），约 300 - 500 行核心代码变动，对稳定性和竞态条件控制要求较高。
- **直接收益**：
  1. **显著降低延迟感**：多工具调用的响应速度极大提升。
  2. **提高吞吐量**：使得 Agent 探索代码库（如并行多次执行 `grep` 或 `read_file`）的速度达到物理极限。
  3. **平滑的终端体验**：视觉上完全消除了"停顿-集中爆发现象"。