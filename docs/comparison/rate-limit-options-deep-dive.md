# Qwen Code 改进建议 — 交互式限速选项菜单 (Rate Limit Options Menu)

> 核心洞察：在国内各大大模型平台（包括通义千问）的公测阶段或是晚高峰时期，开发者频繁遇到 API 限速（HTTP 429 Rate Limit）是家常便饭。对于一个运行中的 CLI Agent 而言，当底层抛出限流错误时，如果仅仅是在终端上打印一句红色的 `Error 429: Too Many Requests` 然后退出程序，体验是灾难性的。Claude Code 为限速场景设计了一套极其优雅的“缓兵之计”——包含等待、无缝模型降级以及升级套餐建议的交互式选项菜单；而 Qwen Code 目前对限速的处理仅仅停留在静态的报错文本。
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md)

## 一、API 限流时的挫败感

### 1. Qwen Code 的现状：硬着陆
目前，当大模型 API 拒绝服务（无论是并发数超标还是分钟级 Token 数超标）：
- **痛点一（无路可退）**：Qwen 会将底层网络库的报错直接抛出。用户此时除了不停地按“上方向键 + 回车”反复重试（这往往会触发更严厉的限流黑名单）外，毫无办法。
- **痛点二（任务中断）**：如果此时 Agent 正在执行一个极其漫长的文件读取梳理工作，这个硬报错会导致整个 `runReasoningLoop` 结束，刚读到脑子里的状态直接失效。

### 2. Claude Code 解决方案：高情商的阻断体验
在 Claude Code 的 `services/rateLimitMessages.ts` 和对应的通知 Hooks 中，作者展现了什么叫“把 Error 变成 Feature”。

当引擎在经过 [持久化重试 (Persistent Retry)](./persistent-retry-deep-dive.md) 后仍无法穿透 429 屏障时，它绝不会粗暴退出，而是暂停事件循环，并渲染出一个包含几个选项的交互菜单：

```text
Rate Limit Exceeded (You have hit the 100,000 tokens/min limit).

How would you like to proceed?
❯ Wait 30 seconds and automatically retry.
  Switch to a faster, less constrained model (Claude-3-Haiku).
  View usage and upgrade tier options.
  Abort current task.
```

#### 机制一：无缝的降级接力 (Model Switch on-the-fly)
如果用户选择了“Switch to a faster model”，引擎会在当前卡住的断点，瞬间将底层的 API 调用方从 `Opus` 换成 `Haiku`（一种并发度额度宽裕得多的小模型），然后直接用小模型把未完成的任务接着做完！

#### 机制二：智能等待与预测 (Smart Wait)
基于 `Retry-After` Header，它甚至能准确告诉用户需要等多久。用户选择等待后，会出现一个倒计时 Spinner，时间一到原样发送请求，不损失任何上下文。

## 二、Qwen Code 的改进路径 (P3 优先级)

将异常处理提升到与正常交互同等的优先级。

### 阶段 1：全局拦截 429 报错
修改底层的 API Client 或 Error Boundary。
如果是 429 报错，不再直接通过抛出 `throw new Error()` 中断循环，而是触发一个 `AgentEventType.RATE_LIMITED` 挂起事件。

### 阶段 2：开发 `RateLimitMenu` TUI 组件
在 CLI 层监听这个事件，覆盖当前的输入框，渲染出一个用方向键选择的单选列表（Ink `SelectInput`）：
1. **自动等待**（如果有 retry-after，显示秒数）。
2. **切换到降级模型**（比如推荐切换到 `qwen-turbo`）。
3. **取消当前步骤**。

### 阶段 3：执行上下文的恢复 (Resume Continuation)
一旦用户做出选择（比如选了模型降级），将修改注入全局 `Config` 单例，然后 `resolve` 这个挂起的拦截器，让中断的工具执行或者回答推理顺着原本的代码流继续流淌。

## 三、改进收益评估
- **实现成本**：中等。核心难点在于如何在深层的递归或流式响应（Stream）中优雅地挂起（Suspend）执行并等待前端组件的回调，不破坏状态机。
- **直接收益**：
  1. **极其出色的错误恢复能力**：即使在最差的网络和平台条件下，也能让用户的开发流不被强行打断，这能极大地挽回由于平台算力不足带来的负面口碑。
  2. **提高降级模型的活跃度**：通过主动推荐，让用户体会到即使是更小规模的模型在特定任务下依然能用。