# Qwen Code 改进建议 — Fast Mode 速度分级与冷却 (Dynamic Fast Mode & Cooldown)

> 核心洞察：不同开发场景对大模型推理能力的需求截然不同。在排查高危并发死锁时，我们需要算力最高、最昂贵的旗舰模型；但在只是让 Agent 补充一批无聊的单元测试，或写一点 CSS 样式时，我们更看重响应的“快”和“便宜”。Claude Code 创造性地引入了基于同一个旗舰模型的“Fast Mode（极速模式）”，提供一键降本增效的体验，并且配备了应对限流的冷却回退（Cooldown Fallback）机制；而 Qwen Code 目前若想改变速度，只能强行切换不同的模型本体，打乱上下文连贯性。
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md)

## 一、缺乏弹性调度的成本黑洞

### 1. Qwen Code 现状：非黑即白
在 Qwen Code 中，你可以通过 `/model` 或者是环境变量指定大模型（例如定死在 `qwen-max`）。
- **痛点一（大炮打蚊子）**：当你让 `qwen-max` 去做大量琐碎的 AST 文件结构读取或变量名重构时，高达几十秒的响应延迟和高昂的 Token 费用让人难以忍受。
- **痛点二（切换上下文断层）**：如果用户觉得慢，手动切成了 `qwen-turbo`，那么之前在 `qwen-max` 里沉淀的一些深层逻辑理解（因为小模型能力的欠缺）可能会直接崩盘。而且反复切换模型操作很繁琐。

### 2. Claude Code 解决方案：同一生态下的弹性滑档
Claude Code 在 `utils/fastMode.ts` 中实现了一个被称为“极速模式（Fast Mode / Penguin Mode）”的精妙设计。

#### 机制一：同宗同源的模型降档
在 Anthropic 的体系下，如果你觉得 `Claude-3.5-Sonnet` 太贵，你可以用 `/fast` 命令瞬间切换。
系统底层并不是让你重新走一遍模型选择向导，而是内部建立了一个极速路由表（Router）。它会将流量无缝切换到 `Claude-3-Haiku` 这一同系、兼容同样 Tokenizer、同样能继承上下文缓存且极其便宜快速的模型上。
你甚至可以在输入提示词时，仅为当前这一句话加上 `--fast` 后缀，执行完这一条轻量指令，下一轮对话又自动切回最强形态的旗舰模型。

#### 机制二：智能的冷却池 (Cooldown State Machine)
如果由于用户开启了极速模式，导致那个小模型被并发调用太多触发了 HTTP 429（Rate Limit），Claude Code 不会让任务卡死。
`fastMode.ts` 中维护了一个带时间戳的 `FastModeCooldown` 状态。
一旦捕获到极速版模型的限流报错：
1. 立即触发长达数分钟的冷却（Cooldown）。
2. 在冷却期间，任何尝试走向 Fast Mode 的网络请求，都会被**强制回退（Fallback）**到宽带充足的标准版旗舰模型中。
3. 等冷却期过去后，又默默地恢复成极速省钱模式。

这种“快慢交替、互为备胎”的策略，将模型 API 的压榨到了极限。

## 二、Qwen Code 的改进路径 (P2 优先级)

让开发者在使用 Agent 时，像开跑车一样可以随时切换“运动模式”和“经济模式”。

### 阶段 1：开发 `/effort` 或 `/fast` 指令
1. 在 `packages/core/src/commands/` 增加 `fast.ts` 或者 `effort.ts`。
2. 建立内置映射字典。比如用户当前主模型是 `qwen-max`，极速模式被绑定为 `qwen-turbo`；主模型如果是 `qwen-plus`，极速模式同样绑定。
3. 允许按单次交互级别进行触发。

### 阶段 2：集成请求路由层 (Request Router)
在核心的 API 发送层 `client.ts` 组装 Payload 前，探测全局或局部的 `Fast` 状态：
```typescript
let targetModel = this.config.getMainModel();
if (isFastModeRequested && !isFastModeInCooldown()) {
    targetModel = this.config.getFastModelFallback();
}
```

### 阶段 3：在 Retry 模块加入冷却与软回退
与上一个报告提到的 `API Retry & Fallback` 结合：
1. 修改 `utils/retry.ts`，如果在请求快速模型时收到特定的超载错误。
2. 激活冷却时间：`triggerFastModeCooldown(Date.now() + 5 * 60 * 1000)`。
3. 在同一轮重试中将请求参数直接替换回主模型（Standard Mode）继续执行。

## 三、改进收益评估
- **实现成本**：低。无需更改渲染层，只需在模型下发调度处增加重写规则。代码量不足 150 行。
- **直接收益**：
  1. **断崖式的成本与延迟缩减**：对于诸如批量文档注释生成等简单操作，能让费用缩减 90%，响应从 10 秒加速至 1 秒内。
  2. **高可用的请求链路**：相当于隐形中给大模型 API 加了一道极其强悍的双保险异地容灾机制。