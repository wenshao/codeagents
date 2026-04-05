# Qwen Code 改进建议 — 输出 Token 自适应升级 (Output Token Adaptive Upgrade)

> 核心洞察：当我们通过 API 调用大模型时，通常需要设定一个 `max_tokens` 参数来限制它的最大输出长度。如果你设定得太小（如 4K），在让大模型生成整个文件（如 500 行的 React 组件）时，代码会在半路被无情截断；如果你设定得极大（如 32K），哪怕你只是让它回答一句“OK”，模型 API 提供商也会在后台的 GPU 显存上为你硬生生预留 32K 的计算槽位（KV Cache Slot），这不仅极其浪费服务器资源，而且更容易被平台限流。Claude Code 运用了极具智慧的“默认低配 + 截断时自动 64K 重试升级”的双轨策略，做到了并发和超长输出两不误；而 Qwen Code 目前只能配置固定的静态输出配额。
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md)

## 一、静态 Token 设定带来的浪费与截断

### 1. Qwen Code 现状：固定上限的僵局
在现有的架构中，`max_tokens` 通常被静态绑定在配置文件或 SDK 初始化中。
- **痛点一（截断阻断流）**：假设设置为默认的 8K。当 Agent 被要求将一个长达 1500 行的遗留代码完全用新语法重写一遍时，它洋洋洒洒输出了 8K tokens，但才写到第 800 行。API 直接返回完成，Agent 以为任务成功了，就直接把截断的半残文件通过 `writeFile` 写入了硬盘，导致项目全盘崩溃。
- **痛点二（极低效的槽位占用）**：如果强行在启动时就给 `qwen-code` 传参设定 32K 输出。根据海量真实数据的统计（例如 Claude 团队统计的 p99=4911 tokens），99% 的回答根本用不到 5K。但由于强行占了 32K，你的请求在并发高峰期会被网关排到极靠后的队列中，导致了无意义的 TTFT（首字延迟）变慢和高频 429 报错。

### 2. Claude Code 的解决方案：自适应档位跃迁
在 Claude Code 的网络请求核心层，他们完美利用了 API 返回的 `stop_reason`（停止原因）字段，构建了动态跃迁机制。

#### 机制一：8K 标准模式探路
系统默认以极具“高并发友好”特性的 **8K `max_tokens`** 向服务器发起请求。对于日常的绝大多数代码编辑、阅读目录、回答提问，8K 已经能装下几千行的代码差异了。

#### 机制二：截断探针与 64K 满血重试 (Adaptive Upgrade)
由于 8K 不够用的情况不到 1%，一旦它真的发生了，Claude 的网络底座并不是抛错给用户，而是执行神级操作：
1. 拦截到 API 响应，发现 `stop_reason === 'max_tokens'`。
2. 说明大模型刚刚的话没说完就被强制闭麦了。
3. 系统**瞬间丢弃刚才这半截回复**，在底层将参数中的 `max_tokens` 直接拉满到恐怖的 **64K**（甚至是 `128K`）。
4. 对用户完全静默地重新发送上一次的 API 请求！

这一次，虽然请求由于分配了巨大的 Slot 可能会慢一点，但它能以满血状态一口气输出哪怕长达 3 万行的究极代码重构，不会再发生任何物理截断。这种 1% 的特殊对待，拯救了 99% 场景的并发性能！

## 二、Qwen Code 的改进路径 (P1 优先级)

让底层的网络引擎具备极强的智能弹性。

### 阶段 1：提取 `stop_reason`
1. 审查 `packages/core/src/core/client.ts` 或对底座大模型 API（如阿里云百炼大模型）的包装器。
2. 确保在每次完整的推理返回后，都能准确抓取到服务端告知的 `finishReason`（结束原因，如 `STOP`, `MAX_TOKENS`, `LENGTH`）。

### 阶段 2：开发拦截与重试适配器
在推理发起点包裹一层自适应重试逻辑：
```typescript
let maxTokens = 8192; // Default conservative limit

async function generateWithAdaptiveTokens() {
    let response = await sendApiRequest({ ...config, maxTokens });
    
    // 如果碰壁了，并且我们还没有使用最大档位
    if (response.finishReason === 'MAX_TOKENS' && maxTokens < 64000) {
        logDebug("Hit output token limit. Upgrading to 64K max_tokens and retrying...");
        maxTokens = 64000;
        // 瞬间满血重试！
        response = await sendApiRequest({ ...config, maxTokens });
    }
    
    return response;
}
```

### 阶段 3：暴漏配置与旁白提示
1. 允许高端极客通过环境变量 `QWEN_CODE_MAX_OUTPUT_TOKENS` 来彻底覆盖这个上限。
2. 当发生自动升级重试时，在终端的流式输出 Spinner 处，短暂地闪过一句：`[Extending output capacity and retrying...]`，安抚在此刻觉得“为什么停住了”的用户。

## 三、改进收益评估
- **实现成本**：极低。只需修改一层几十行的包裹函数，完全不侵入现有的复杂业务逻辑。
- **直接收益**：
  1. **根绝被切断的代码残肢**：再也不会出现写入一半烂文件的致命灾难。
  2. **享受最佳的云端并发通道**：绝不盲目浪费云平台的超长 Token Slot 计算资源，极大降低由于抢占大显存造成的 `529 Overloaded` 或排队限流报错的概率。