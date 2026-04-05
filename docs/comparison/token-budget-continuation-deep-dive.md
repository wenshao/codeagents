# Qwen Code 改进建议 — Token Budget 续行与分层压缩 (Token Budget Continuation & Compaction)

> 核心洞察：对于自动执行复杂任务（如跨多文件重构）的 Agent，经常会遇到单次对话上下文（Context Window）爆满，或者单次输出（Output Tokens）被截断的情况。Claude Code 采用了一套极其成熟的“预算续行预警（Token Budget Continuation）+ 多级后备压缩（Layered Compaction）”机制，确保大任务能够不间断完成；而 Qwen Code 目前只有粗暴的 70% 一次性截断压缩，缺乏续行与降级策略。
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md)

## 一、架构对比与断点分析

### 1. Qwen Code 的当前实现：一刀切的 70% 压缩
在 `packages/core/src/services/chatCompressionService.ts` 中，Qwen Code 的策略非常简单：

```typescript
export const COMPRESSION_TOKEN_THRESHOLD = 0.7;
// 当判断 tokens > max_tokens * 0.7 时：
// 1. 强行砍掉前 70% 的历史记录
// 2. 用 LLM 对这 70% 记录生成一份 `<state_snapshot>` 摘要
// 3. 带着摘要和后 30% 的记录继续
```

**目前的痛点**：
- **无输出预警与续行**：Qwen Code 无法感知自身是否接近单次生成的输出上限（如 8K 限制）。如果 Agent 正在输出大量代码修改，到达 8K 截断时，任务会直接失败，没有任何“自动接力”机制。
- **僵硬的压缩时机**：一旦触发 70% 阈值，立即发起一次昂贵的全局摘要请求。摘要会丢失精确的文件路径、工具调用的具体参数和执行细节，导致模型在压缩后立刻产生“失忆”性幻觉（例如忘记刚读过的文件内容）。

### 2. Claude Code 的解决方案：预算管理与递减检测
Claude Code 在 `query/tokenBudget.ts` 和 `services/compact/` 中建立了一套名为 Token Budget 的系统：

#### 第一道防线：90% 续行预警 (Continuation)
它不轻易丢弃上下文。系统会监控每轮交互消耗的 Token。当上下文接近上限的 90% (`COMPLETION_THRESHOLD = 0.9`) 时，引擎会在用户的最后一条消息背后，**悄悄注入一段合成的警告 Prompt**：
> "You have used 90% of your context budget. Please finish your current immediate thought and return a response. I will continue your execution in the next turn."

模型收到这个预警后，会主动保存关键状态并优雅地结束当前轮次，然后在下一次被引擎自动唤醒继续，从而**将一个超大任务拆分为多个无缝衔接的子回合**，完美避开 Token 截断。

#### 第二道防线：收益递减断路器 (Diminishing Returns Detection)
如果 Agent 陷入死循环，不断触发续行，Claude Code 有一个断路器：
```typescript
const isDiminishing =
  tracker.continuationCount >= 3 &&
  deltaSinceLastCheck < 500 &&
  tracker.lastDeltaTokens < 500
```
连续 3 次增量不足 500 Tokens 时，系统判定它卡住了，强制中断续行链。

#### 第三道防线：分层压缩回退 (Layered Compaction)
当真的必须压缩上下文时，Claude Code 不会立刻做全局摘要，而是分 3 层进行无损/有损降级：
1. **Micro Compact (微压缩)**：遍历历史记录，静默删除过去的所有临时工具输出（如大段的 `BashTool`、`GrepTool` 结果），只保留命令本身。这通常能瞬间释放 50% 的空间且无损！
2. **Session Memory Compact**：清理内存中的附件和不再需要的缓存结构。
3. **Full Compact (全量压缩)**：只有前两步无效时，才回退到类似 Qwen Code 的历史摘要截断（最后手段）。

## 二、Qwen Code 的改进路径 (P1 优先级)

Qwen Code 要支撑复杂的企业级代码生成，必须废弃单层的 70% 截断，重构为柔性的预算管理。

### 阶段 1：引入续行预警机制 (Nudge/Continuation)
1. 新建 `packages/core/src/services/tokenBudgetService.ts`。
2. 在 `agent-core.ts` 的推理循环末尾增加拦截：在模型生成的 Token 总数达到 85%-90% 时，通过 `TOOL_RESULT` 或系统消息注入 `nudgeMessage`，引导模型进入下一轮。

### 阶段 2：实现 Micro Compact (无损瘦身)
1. 拦截并识别占用 Token 最多的部分（通常是长命令的输出 `stdout`、长文件读取）。
2. 在触发全量 `compressContext` 之前，先执行一次清理循环：将旧回合（非当前回合）的 `tool_response` 里的长文本替换为 `[Output elided to save tokens]`。
3. 往往执行完 Micro Compact，Token 水位就会降到 30%，根本不需要耗费时间去做不精准的全量摘要。

### 阶段 3：收益递减与无限死循环防护
1. 追踪每次 Agent 自动续行的增量 Token (`delta_tokens`)。
2. 设定阈值（例如连续 3 个回合都没推进实际进度），强制停止并交还控制权给人类用户，防止浪费 API 额度和费用。

## 三、改进收益评估
- **实现成本**：中等。核心在于修改 Prompt 拦截和改造 `chatCompressionService.ts` 的执行流。
- **直接收益**：
  1. **彻底解决大任务截断问题**：Agent 终于可以处理动辄几万行修改的巨型重构，不受单次 max_tokens 的物理限制。
  2. **大幅降低压缩后幻觉**：优先采用清理工具日志的 Micro Compact，上下文的“精确记忆”得以保留，Agent 变聪明的直观感受极强。