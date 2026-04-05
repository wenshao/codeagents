# Qwen Code 改进建议 — 持久化重试模式 (Persistent Retry Mode)

> 核心洞察：当 CLI Agent 被配置为 CI/CD 自动化流水线的一环，或是作为后台 Daemon 代理运行夜间批处理任务（如全局重构、大规模安全审计）时，系统的容错性要求会发生质变。在交互模式下，如果大模型 API 宕机或遇到限流（429 Rate Limit），快速失败（Fail-fast）并让用户知晓是合理的；但在无人值守（Unattended）模式下，一次长达数小时的任务因为偶发的 529 过载而直接退出，将导致前功尽弃。Claude Code 针对此场景专门设计了“无限持久化重试模式（Persistent Retry）”；而 Qwen Code 目前所有模式均采用一刀切的固定次数重试，无法胜任严苛的自动化场景。
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md)

## 一、自动化场景下的网络雪崩与痛点

### 1. Qwen Code 的现状：短视的重试
在 `packages/core/src/utils/retry.ts` 中，Qwen Code 设定了全局统一的 `maxAttempts: 7`。
- **痛点**：假设凌晨 2 点触发了 GitHub Actions 自动化重构任务。如果 3 点时大模型服务遭遇突发的大规模高峰拥堵，连续抛出 529 错误。Qwen Code 在尝试 7 次（可能总跨度只有一两分钟）后，就会抛出致命错误，彻底终结 CI 进程。早上 9 点开发者来上班时，看到的只是一个红色的 Pipeline 和只做了一半的损坏代码树。这违背了自动化流水线“最终一致性（Eventual Consistency）”的初衷。

### 2. Claude Code 的解决方案：无人值守持久化
Claude Code 在 `services/api/withRetry.ts` 中，通过检测 `CLAUDE_CODE_UNATTENDED_RETRY` 环境变量（或者检测自身是否在 `--bg` / CI 环境），会激活 `isPersistentRetryEnabled()` 分支。

#### 机制一：无视 maxRetries 的无限等待
当抛出错误被 `isTransientCapacityError(error)` 判定为暂时性的容量错误（特指 HTTP 429 限流和 HTTP 529 服务过载）时：
```typescript
const persistent = isPersistentRetryEnabled() && isTransientCapacityError(error);
if (attempt > maxRetries && !persistent) {
    throw new CannotRetryError(error, retryContext);
}
// 如果 persistent 为 true，直接 bypass 掉 maxRetries 检查，进入下一轮 while 循环。
```
它会变成一只有耐心的“僵尸”，永远不主动退出任务，直到 API 恢复响应。

#### 机制二：心跳与退避上限锁定
无限重试并不意味着无限地用请求去轰炸 API 服务器：
1. **退避上限 (Cap)**：普通的指数退避可能很快就会涨到每次等待几十分钟。但在持久化模式下，它将单次重试的最长等待时间封顶为 **5 分钟**（`PERSISTENT_MAX_BACKOFF_MS`）。
2. **重置计数器 (Reset Cap)**：如果累计退避时间达到了 6 小时，它会将退避重置机制清零，防止跨天任务出现等待过长的问题。
3. **心跳保活 (Heartbeat)**：在干等的漫长周期内（比如等了 20 分钟），它还会每隔 30 秒向外部的遥测系统（或 CI Runner 的控制台）打印或发送一个心跳探测：`Agent is waiting for API capacity...`，防止 CI 系统因为长期没有 `stdout` 产出而强行把任务 `timeout` 杀掉。

## 二、Qwen Code 的改进路径 (P1 优先级)

为了使 Qwen Code 能够作为可信赖的基础设施接入企业的 DevOps 管道，必须引入环境感知的容错层。

### 阶段 1：环境探针与 CLI 参数
1. 在 `packages/core/src/core/config.ts` 中引入 `isUnattendedMode()` 探测逻辑（例如检查是否配置了 `--ci` 参数、或者环境变量 `CI=true`）。
2. 让该状态可被底层的 `geminiChat.ts` 或 `retry.ts` 访问。

### 阶段 2：重写 Retry 循环
在现有的 `retryWithBackoff` 函数中，修改判定退出条件的逻辑：
```typescript
// Qwen Code: 改进的重试退出判定
const isTransient = status === 429 || status === 529 || status === 500;
const persistentMode = isUnattendedMode() && isTransient;

if (attempt >= maxAttempts && !persistentMode) {
  throw error;
}
```

### 阶段 3：加入 CI 友好的日志与退避盖帽
1. 设置 `maxDelayMs`：如果启用持久化模式，将指数退避的 `delay` 强制 `Math.min(delay, 5 * 60 * 1000)`。
2. 在 `delay()` 函数运行期间，如果时间大于 1 分钟，每隔 30 秒通过 `debugLogger` 或向 `stderr` 抛出一条低噪音日志，安抚 CI Runner。

## 三、改进收益评估
- **实现成本**：极低。只需在原有的重试函数上增加环境判断分支即可。
- **直接收益**：
  1. **解放生产力**：让 Qwen Code 真正具备“彻夜批处理”的能力，成为不知疲倦的代码审计员。
  2. **应对拥堵利器**：在国内各种“百模大战”引发 API 限流的大背景下，不至于因为一时的配额枯竭而丢失几十个并发运行的宝贵任务。