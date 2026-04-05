# Qwen Code 改进建议 — 反应式压缩 (Reactive Compression / prompt_too_long 恢复)

> 核心洞察：大模型的上下文窗口是有限的（如 128K 或 200K Tokens）。即使有各种预防性的上下文清理（如 Token Budget 预警），在极端情况下（例如一次全局搜索返回了超大体积的代码片段，或者堆积了海量的对话历史），发往 API 的请求仍可能触发致命的 `prompt_too_long` (413 Payload Too Large) 错误。面对这种报错，Qwen Code 目前会直接让任务崩溃；而 Claude Code 实现了一套优雅的“反应式重试裁剪（Reactive Retry）”机制，能在用户无感的情况下自动切除过期上下文并挽救当前会话。
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md)

## 一、被动溢出引发的死局

### 1. Qwen Code 现状：主动拦截，被动崩溃
Qwen Code 目前在 `chatCompressionService.ts` 中实现了一套基于阈值的**主动压缩**（当判断字数达到 70% 限制时进行摘要）。
然而，Token 计数永远只是一种不精确的**客户端估算**（尤其在涉及到复杂的工具 Schema 和多模态附件时）。
- **痛点**：当某次 API 调用的实际 Token 数意外超过了服务端硬限制，服务端会抛出一个类似 `prompt_too_long` 的 HTTP 错误。此时 Qwen Code 没有任何降级和挽救机制，整个长任务会直接被抛出的异常中断。用户唯一的选择是手动输入 `/clear` 放弃全部历史重头再来，体验极具挫败感。

### 2. Claude Code 的解决方案：自动裁剪与反应式重试
Claude Code 在执行所有 API 请求（尤其是 Compact 压缩请求和主控交互请求）时，如果捕获到 `PROMPT_TOO_LONG_ERROR_MESSAGE`，并不会直接向终端抛出红字，而是进入 `services/compact/compact.ts` 中的 `truncateHeadForPTLRetry` 恢复序列。

该序列包含三个极其精细的步骤：

#### 步骤一：精准计算 Token Gap (缺口差值)
当触发限流时，API 报错信息中通常会包含 `actual` 和 `limit` 的值（例如：`prompt is too long: 205000 > 200000`）。
Claude Code 在 `services/api/errors.ts` 中会通过正则表达式抓取这个缺口（Gap = 5000 Tokens）。

#### 步骤二：基于 API Round 的安全裁剪
它不是简单地砍掉最早的 5000 个字符，而是将消息数组按 `Api Round`（一组 User + Assistant 交互回合）进行编组（Group）。
- 如果解析到了具体的 Token Gap，它会从最早的回合开始逐个抛弃，直到释放出足够的空间。
- 如果没有具体数字，则默认抛弃最早的 20% 的历史交互记录。

#### 步骤三：注入截断标记并防死锁重试
由于 API 严格要求对话必须以 `User` 角色起手，在切掉早期的交互记录后，它会在开头强行注入一个 Synthetic User Marker（合成标记）：
```json
{
  "role": "user",
  "content": "[earlier conversation truncated]"
}
```
随后，它会带着这套瘦身过的上下文重新向 API 发起调用。如果在极少见的情况下一次裁剪不够，该机制允许**最多重试 3 次 (`MAX_PTL_RETRIES`)**。超过 3 次才会真正认为会话不可救药而报错，极大提升了边界情况下的容错率。

## 二、Qwen Code 的改进路径 (P1 优先级)

为了防止长进程的“猝死”，必须赋予核心执行流面对过载错误时的自愈能力。

### 阶段 1：Error 层捕获机制
1. 修改 `packages/core/src/core/client.ts`（或底层的 `retryWithBackoff`）。
2. 当拦截到底层大模型返回特定的上下文超载报错（如 HTTP 413，或者 Qwen API 的特定 Error Code）时，抛出一个可被捕获的专有错误 `PromptTooLongError`，并附带解析出的超量大小（如果正则提取成功）。

### 阶段 2：重构消息裁剪逻辑 (Truncate Recovery)
1. 在 `agent-core.ts` 主推理循环的最外层加入 `catch (e instanceof PromptTooLongError)`。
2. 触发恢复函数 `recoverFromPromptTooLong(messages, tokenGap)`：
   - 过滤保留最后几个最近的交互回合（保护核心工作区记忆）。
   - 将最顶端的最早历史对话轮次删除。
   - 在新数组的开头拼接一句系统旁白（System / User）：`[Previous historical context has been truncated due to length limits.]` 以向大模型解释突兀的开场。

### 阶段 3：建立三次重试循环
将恢复后的 `messages` 再次压入 API 发送队列。设置一个局部的计数器 `ptlAttempts`，限制最多递归重试 3 次，防止因单条恶意的超大文本块导致应用进入无限死循环。

## 三、改进收益评估
- **实现成本**：低到中等。属于外围的控制流保护，改动集中在重试逻辑和数组切片操作上，约 100 - 200 行代码。
- **直接收益**：
  1. **极端场景下的鲁棒性**：彻底消除了由于“无意识的大结果注入”导致应用崩溃的问题。
  2. **无需精准计数的降级**：弥补了前端 Token 计数器估算不准带来的硬边界误差。
  3. **平滑的用户体验**：用户在运行耗时极长的数据分析任务时，再也不会因为“最后临门一脚超了 10 个 Token”而痛失整个进度。