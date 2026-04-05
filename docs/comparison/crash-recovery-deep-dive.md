# Qwen Code 改进建议 — 会话崩溃恢复与中断检测 (Crash Recovery & Interruption Detection)

> 核心洞察：CLI Agent 进程在长时间运行（长任务、重构、多文件分析）时，极易因内存溢出 (OOM)、系统休眠、网络中断或用户误触 `Ctrl+C` 等意外退出。Claude Code 设计了极其完善的崩溃恢复（Crash Recovery）机制，能够精准识别上次中断的状态并无缝续行，而 Qwen Code 目前完全缺失此能力。
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md)

## 一、问题背景：为什么直接恢复历史记录是不行的？

假设我们将多轮对话持久化到了本地磁盘。当进程崩溃并重新启动时，如果简单地将最后保存的 Message 数组直接发给模型 API，经常会遭遇 `API 400 Bad Request` 错误。

这是因为 LLM API 要求严格的消息配对格式：
- `tool_use` 必须跟随 `tool_result`。
- 不能连续出现两个相同角色（例如连续两个 `user`），或结尾状态异常。

如果崩溃发生在工具执行中途，历史记录里会存在一个"孤立的" `tool_use`；如果发生在刚处理完用户附件但还没生成回复时，尾部会留下不规范的边界。直接发送这些残缺的对话链会导致 API 拒绝服务，**最终导致哪怕有本地存档，用户也只能被迫新建会话，前功尽弃**。

## 二、Claude Code 的解决方案：三态中断检测与合成续行

在 Claude Code 的源码 `utils/conversationRecovery.ts` 中，设计了一个非常巧妙的 `deserializeMessagesWithInterruptDetection` 机制。

### 1. 数据清理与规范化 (Data Normalization)
每次从本地持久化文件读取历史消息时，Claude Code 会先执行一系列清理：
- **`filterUnresolvedToolUses`**: 扫描并移除所有只发出了 `tool_use` 请求但由于崩溃未能返回 `tool_result` 的孤立区块。
- **`filterOrphanedThinkingOnlyMessages`**: 移除只有 `<thinking>` 但没有实际行动块的未完成思考片段。

### 2. 三态中断检测 (detectTurnInterruption)
接着，它会检查最后一个有效消息的类型，判断崩溃具体发生在什么阶段，返回 3 种内部状态：

1. **`none` (正常完成)**
   - 最后一个消息是 `assistant`（由于 `stop_reason` 在持久化时处理的特性，只要最后一个是完整的 assistant 块且没有遗漏的 tool，就被认为是正常结束）。
   - 或者最后一个是类似于 `SendUserMessage` 的终端（Terminal） `tool_result`。
2. **`interrupted_prompt` (提示词被中断)**
   - 最后一个消息是纯文本的 `user` 提示，这意味着用户刚发完指令，Claude 还没开始思考（或没想完）就崩溃了。
3. **`interrupted_turn` (执行轮次被中断)**
   - 最后一个消息是 `tool_result` 或 `attachment`，这意味着 Claude 在工具执行间隙（Mid-Turn）被打断，它本来应该继续根据上一个工具的结果进行思考的。

### 3. 合成续行 (Synthetic Continuation)
对于 `interrupted_turn` 状态，Claude 采用了一种极其优雅的处理方式：**注入合成提示词**。

```typescript
// 源码摘录：将 interrupted_turn 转换为 interrupted_prompt
if (internalState.kind === 'interrupted_turn') {
    const [continuationMessage] = normalizeMessages([
    createUserMessage({
        content: 'Continue from where you left off.',
        isMeta: true,
    }),
    ])
    filteredMessages.push(continuationMessage!)
    turnInterruptionState = {
        kind: 'interrupted_prompt',
        message: continuationMessage!,
    }
}
```
系统会强行在末尾追加一条虚拟的用户消息：`"Continue from where you left off."`。这样，不规范的结尾被抹平了（因为现在是 user 发起的新一轮），并且 LLM 被自然引导去阅读上文并在上次崩溃的点继续执行。

## 三、Qwen Code 的现状与改进路径 (P0 优先级)

Qwen Code 当前缺乏这一套复杂的异常恢复机制。一旦 Node 进程退出，会话状态（除了偶尔残留在外部平台的上下文）在本地内存中即宣告丢失。

### 改进阶段：

#### 阶段 1：增量式持久化存储
- 为 Qwen Code 引入 Append-only JSONL 会话存储机制。每一轮交互实时写入 `.qwen/sessions/<session_id>.jsonl`。
- 采用追加写入避免崩溃瞬间的写入损坏。

#### 阶段 2：恢复与清洗模块 (Recovery Service)
- 编写 `packages/core/src/utils/conversationRecovery.ts`。
- 实现 `filterUnresolvedToolUses`：如果最后一个消息里包含了 `tool_calls` 但是后续数组中没有紧跟的 `tool_messages` (结果)，必须从 `assistant` 消息中将其切除。

#### 阶段 3：合成续行与自动启动
- 在 CLI 启动入口（`cli.ts` 或 `agent.ts`）检测到未完成的会话恢复时，自动应用三态中断检测逻辑。
- 对于 `interrupted_turn`，自动推入 `[{ role: "user", content: "Continue from where you left off." }]`，绕过等待用户输入的阶段，直接触发大模型推理，实现**断点续传**（无缝重启）。

## 四、改进收益
- **用户体验**：解决了 "跑了 10 分钟的重构由于 OOM 突然终止，不得不重头再来" 的痛点。
- **稳定性**：通过彻底剔除孤立的 `tool_use`，消除了长对话中隐秘且频繁的 API 400 格式错误。
- **Agent 连续性**：配合未来可能引入的 Swarm 和后台代理模式，崩溃恢复将是代理持久存活的基石。