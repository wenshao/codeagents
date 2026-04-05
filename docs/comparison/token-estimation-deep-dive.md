# Qwen Code 改进建议 — API 实时 Token 计数与精确回退 (Token Count Estimation)

> 核心洞察：长上下文管理是 AI Agent 的生存基石。如果不知道自己到底花了多少 Token，Agent 就不知道什么时候该把旧日志压缩，什么时候该阻断请求以防爆炸。而在混合了 CJK 字符（中日韩汉字）、Base64 图片附件以及复杂 JSON Schema 的情况下，传统的通过“字符串长度除以 4”来估算 Token 的方式误差极大。Claude Code 构建了基于 API 层级精确统计结合本地分层降级回退（3-Tier Fallback）的极致计数器；而 Qwen Code 目前主要依赖粗糙的本地静态匹配法则，这在中文环境下会频繁导致过度压缩或溢出崩溃。
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md)

## 一、静态估算带来的致命误差

### 1. Qwen Code 的现状：粗估之痛
在目前的 `packages/core/src/utils/tokenLimits.ts` 中，Qwen Code 主要使用静态字符模式或正则来估算 Token 消耗：
- **痛点一（截断时机误判）**：假设你发了一大段中文报错，由于中文在不同 Tokenizer（分词器）下 1 个汉字可能被切分为 2 个甚至 3 个 Token，而传统的简单算法可能会认为它只有 1 个 Token。这会导致 Qwen 认为自己还没碰到 70% 的危险红线，于是把这个其实已经超载的包砸向服务器，直接收到 `HTTP 400 Prompt Too Long` 的死锁报错。
- **痛点二（成本统计失真）**：当你的终端提示你“本轮消耗了 200 Token”时，月底你看着阿里云平台上的账单发现扣了相当于 400 Token 的钱。这会极大地伤害企业用户的信任。

### 2. Claude Code 解决方案：3 层金字塔回退模型
在 Claude Code 的 `services/tokenEstimation.ts` 和网络调用底层，他们对这个数字的准确度到了吹毛求疵的地步。

#### 机制一：金字塔层级 (3-Tier Strategy)
为了绝对的精准，它在计数时会采取如下优先级的层级回退（Fallback）策略：
1. **Tier 1 - 精确调用 API (`countTokensWithAPI`)**：直接将准备发送的消息体（不带实际推理任务）发送到模型提供商自带的 `count_tokens` HTTP 接口。这保证了哪怕包含复杂的图表，数字也是 100% 服务端权威对齐的。
2. **Tier 2 - 小型模型/本地分词器推算**：如果在断网或者 API 限流时，调用本地包含相同词表的 WASM / Node.js 扩展包进行切分。
3. **Tier 3 - 经验粗估兜底**：最糟糕的情况，按照英文 `~4 bytes/token`，中文额外加权的经验公式凑合估算。

#### 机制二：请求去重与 SHA1 散列缓存 (`withTokenCountVCR`)
调用 API 去数 Token 虽然准，但会增加巨大的网络延迟，岂不是拖慢了整个应用？
Claude Code 极其巧妙地引入了一层 `VCR (Video Cassette Recorder)` 缓存。它将需要测算的巨型系统提示词、长代码字符串利用高效率的 `SHA-1` 算法进行 Hash，并将 `[Hash -> Token Count]` 的结果缓存在内存里。
由于大段的 System Prompt 几个小时都不会变，它几乎永远是 `0ms` 命中缓存返回绝对精确的 Token 数量，兼顾了快与准。

## 二、Qwen Code 的改进路径 (P2 优先级)

给大模型 Agent 挂上最精准的仪表盘。

### 阶段 1：对接官方的 Count Token API
1. 查阅通义千问 / DashScope API 文档，找出专门用于计算 Token 的端点。
2. 在 `packages/core/src/core/client.ts` 抽象出 `countTokens(messages): Promise<number>` 的异步方法。

### 阶段 2：构建防抖 Hash 缓存池
1. 在 `packages/core/src/utils/` 下增加 `tokenEstimationCache.ts`。
2. 利用 Node.js 内置的 `crypto.createHash('sha1')` 将长文本散列化。
3. 把散列后的摘要和向 API 请求回来的精准数字进行 LRU (Least Recently Used) 缓存绑定。

### 阶段 3：替换全局计数器
找到所有曾经调用静态计数逻辑（比如触发上下文压缩截断阈值判断、以及 `Footer` 状态栏打印当前花销）的地方。
将老旧的静态算法全部更换为由上述异步 Promise 返回的精准度极高的数值。

## 三、改进收益评估
- **实现成本**：中等。核心是重写一个带有散列缓存的异步获取类，代码量约 150-200 行。
- **直接收益**：
  1. **终结不可预知的 400 崩溃**：让 Agent 可以极其自信地在上下文窗口的 99% 的刀尖上跳舞，绝不多浪费一丝内存，也绝不会发生物理溢出。
  2. **透明的信任感**：在终端打出的每一个计费消耗，都和次日去阿里云控制台查看到的最终账单分毫不差。