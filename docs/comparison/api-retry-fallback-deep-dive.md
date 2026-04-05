# Qwen Code 改进建议 — API 指数退避与降级重试 (API Backoff & Fallback Retry)

> 核心洞察：代码 Agent 执行复杂任务通常需要连续几十次 API 调用。任何一次瞬态网络故障（如 500、502）、服务限流（429）或模型过载（529）都不应该导致整个长任务立即失败并丢失进度。Claude Code 拥有极其精细的网络错误处理、指数退避、429 尊重和 529 模型降级机制，保证了极高的稳定性；而 Qwen Code 的重试机制相对单薄，缺乏降级与特殊错误码的智能处理。
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md)

## 一、架构对比与稳定性痛点

### 1. Qwen Code 现状：基础重试
在 `packages/core/src/utils/retry.ts` 中，Qwen Code 提供了一个基础的 `retryWithBackoff` 函数：
- **最大次数**：默认 `maxAttempts: 7`。
- **触发条件**：仅在 HTTP 状态码为 429 或 5xx 时重试。
- **退避策略**：简单的基础时间乘以 2，加上 `30%` 的抖动 (Jitter)。

**目前的痛点与缺失**：
1. **不尊重 Retry-After**：当遭遇 HTTP 429 Rate Limit 时，服务端通常会在 Header 中返回 `retry-after`（告诉客户端应该等多少秒后再试）。Qwen Code 忽略了该字段，直接盲目重试，容易被服务端彻底封禁。
2. **无模型降级 (Fallback)**：在晚高峰等服务过载（HTTP 529 Overloaded）时，盲目重试大模型（如 `qwen-max`）往往徒劳无功。如果任务直接失败，用户体验极差。
3. **网络层异常未覆盖**：未特殊处理底层的 `ECONNRESET` 或 `EPIPE` 等 TCP 连接被重置的错误（这类错误通常需要禁用 HTTP Keep-Alive 重建连接）。
4. **Token 过期无法自愈**：在耗时数小时的长会话中，如果遭遇 401/403，Qwen Code 会直接抛错。而它本应挂起当前请求，触发 Auth 模块刷新 Token 后再无缝重试。

### 2. Claude Code 解决方案：高弹性网络层
Claude Code 的重试网关（位于 `services/api/withRetry.ts`）具有企业级的异常容错能力：

#### 机制一：智能读取 Retry-After
```typescript
// Claude Code: 解析 429 限流
if (status === 429 && headers.has('retry-after')) {
    // 优先遵循服务端指导的等待时间，而不是自己的指数退避
    const delayMs = parseRetryAfter(headers.get('retry-after'));
    await sleep(delayMs);
}
```

#### 机制二：529 过载降级 (FallbackTriggeredError)
当检测到服务端严重过载（如连续 3 次返回 529 错误）时，抛出专门的 `FallbackTriggeredError`，并**自动无缝降级到备用的小型模型**（如从 `claude-3-5-sonnet` 降级到 `claude-3-haiku`）继续执行当前不那么重要的工具输出总结任务。
这保证了“降级总比彻底宕机强”。

#### 机制三：网络底座容错与持久化重试
针对底层的 `ECONNRESET` / `UND_ERR_SOCKET`，Claude Code 知道这是底层的 Keep-Alive 遇到了失效连接，它会在重试时自动带上特殊的标志，让底层网关禁用 Keep-Alive 重建纯净的 TCP 连接。
另外，它还支持配置“持久化重试模式（Persistent Retry）”——在 CI/CD 或后台无人值守环境下，它可以每隔 5 分钟重试一次，永远不轻易放弃任务。

## 二、Qwen Code 的改进路径 (P1 优先级)

为了确保 Qwen Code 在不稳定的网络环境下依然能像一台“不知疲倦的机器”一样完成任务，我们需要升级网络重试层。

### 阶段 1：增强基础 Retry 逻辑
1. 升级 `utils/retry.ts`，提升 `maxAttempts` 至 10 次。
2. 在捕获 Error 时，深度解析 Axios/Fetch 的 `response.headers`。如果遇到状态码 `429`，提取 `retry-after` 字段，作为本次 `delay` 的绝对时间（如果该字段存在）。

### 阶段 2：底层网络异常与 Token 自愈
1. 捕获特定的系统级错误码（如 `ECONNRESET`, `ETIMEDOUT`, `ENOTFOUND`）加入重试白名单。
2. 处理 401 Unauthorized：拦截到 401 时，不要立即失败，而是触发一个 `eventEmitter.emit('TOKEN_REFRESH_REQUIRED')`。等待（await）凭证刷新器获取到新的 Token 后，修改请求头并重新发起请求。

### 阶段 3：引入模型降级 (Fallback)
1. 在 `Config` 中允许用户配置主模型和备用模型（如 `model: qwen-max, fallbackModel: qwen-turbo`）。
2. 在 `client.ts` 的 `generateContent` 包装器中：如果遇到连续 N 次 529 或 500 服务器错误，捕获并捕获并捕获后，自动将请求的 `model` 参数替换为 `fallbackModel`，并在 TUI 上打印一条黄色警告：“主模型过载，已自动降级为 qwen-turbo 以保证任务继续”。

## 三、改进收益评估
- **实现成本**：中。需要改造底层 HTTP 调用的拦截器和重试函数，代码量约 200 - 300 行。
- **直接收益**：
  1. **极高的任务完成率**：长任务（如几十步的大型重构）再也不会因为中间某一次微小的网络抖动或服务端限流而前功尽弃。
  2. **平台合规性**：尊重 API 的 `Retry-After`，大幅降低因为野蛮重试被云厂商账号封禁的风险。
  3. **出色的弱网/晚高峰体验**：在 API 调用最拥堵的时间段，通过自动降级依然能保持 Agent 活跃运行。