# Qwen Code 改进建议 — Prompt Cache 分段与工具稳定排序 (Prompt Cache Optimization)

> 核心洞察：现代大模型（如 Claude 3.5、Gemini 1.5 等）普遍支持 Prompt Caching（提示词缓存），能够为长且固定的前缀上下文节省高达 90% 的输入 Token 费用，并使首字响应时间减半。但 Prompt Cache 对前缀的**字节级一致性**要求极高。Claude Code 设计了极致的分段缓存、稳定排序与 Schema 锁定策略；而 Qwen Code 的 System Prompt 和工具列表容易发生微小抖动，导致极高的缓存未命中率。
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md)

## 一、为什么 Prompt Cache 容易失效？

在 API 调用时，Agent 的前缀通常由以下两部分构成（约占几万 Tokens）：
1. **System Prompt (系统提示词)**：包含大段行为准则、项目规范、当前状态。
2. **Tools Schema (工具定义)**：包含所有工具名称、描述和 JSON Schema。

**Qwen Code 的现状问题**：
在 `packages/core/src/core/client.ts` (`getMainSessionSystemInstruction`) 中，Qwen Code 会将动态状态（如当前工作目录、当前打开的文件、动态的内存片段）直接拼接在整个 System Prompt 中发送。
此外，工具数组的顺序没有严格保证（如果加载了外部 MCP 工具，顺序可能会变化）。
**后果**：
只要前缀中有一个字符发生变化（例如当前活跃的文件变了），整个数万 Token 的前缀缓存就会被击穿，API 每次都会重新收取全量输入费用，且响应迟缓。

## 二、Claude Code 的解决方案：分界与锁定

在 Claude Code 的源码中（`utils/api.ts`, `utils/toolSchemaCache.ts`, `services/api/promptCacheBreakDetection.ts`），它为极致的缓存命中率做了四层设计：

### 1. Static / Dynamic 系统提示词分界
Claude Code 显式地将系统提示词分为两半：
- **Static Section (静态区)**：包含永不改变的系统身份、核心能力、通用指令规则。
- **Dynamic Section (动态区)**：包含当前时间、活跃文件、临时的用户偏好等。

它会在两者的交界处插入一个 `SYSTEM_PROMPT_DYNAMIC_BOUNDARY` 标记，并且**仅对静态区域和其上方的工具定义**应用 `cache_control: { type: 'ephemeral' }` 缓存断点。
这样，动态区的内容随意改变，都不会影响前面数万 Token 的缓存命中。

### 2. 工具列表的稳定排序 (Stable Sorting)
工具 Schema 是最长的前缀之一（十几 K Token）。
Claude Code 在 `utils/toolPool.ts` 中强制所有**内置工具（Built-in Tools）**按照字母表顺序**固定排列**在数组最前面。
对于动态加载的 MCP 工具或项目局部工具，则始终**追加**在内置工具之后。这样可以确保“内置工具前缀”永远命中缓存。

### 3. 工具 Schema 的首帧锁定
大型 Agent 的工具 Schema 中可能会因为 A/B 测试（GrowthBook）或配置热更新而发生微小变动。
Claude Code 设计了 `toolSchemaCache.ts`。在会话（Session）的第一次调用时，它会深度冻结（Snapshot）并缓存当前的 Tool Schema。即使后续环境变量或开关发生改变，只要不重启 Session，它发送给 API 的 Schema 就保证**绝对字节级一致**。

### 4. 自动缓存击穿检测
Claude Code 包含一个 `promptCacheBreakDetection.ts` 服务。它会监控每次 API 响应中的 `cache_read_input_tokens` 指标。如果发现原本应该命中的缓存突然变成 0，它会在内部日志中记录警告，帮助开发者迅速定位是哪一段 Prompt 引入了抖动。

## 三、Qwen Code 的改进路径 (P1 优先级)

为了将长会话的 API 成本砍掉一大半并加速响应，Qwen Code 必须重构 Prompt 组装逻辑。

### 阶段 1：拆分核心 System Prompt
1. 重构 `getCoreSystemPrompt()` (位于 `packages/core/src/core/prompts.ts`)。
2. 将原本混合在一起的 `userMemory`、环境状态等剥离到数组的后半部分。
3. 确保前半部分的指令字符串**完全纯净、静态**。

### 阶段 2：强制工具数组稳定排序
1. 在 `client.ts` 或 `agent-core.ts` 组装 `toolsList` 时，增加 `sort()` 逻辑。
2. 确保 `Qwen Code` 自带的基础工具（如 `read_file`, `shell`, `todo_write`）具有固定的索引位置。

### 阶段 3：注入 Cache Control 标记
1. 对于支持 Prompt Caching 的模型 API（目前主要是 Anthropic Claude 系列，以及部分提供兼容 API 的国产模型）。
2. 在组装 `messages` 数组发送前，对 Static System Prompt block 和 Tools block 附加底层协议要求的 Cache 断点标记（例如 Anthropic 的 `cache_control`）。

## 四、改进收益评估
- **实现成本**：中等。需要深入了解不同 LLM 供应商的 Prompt Caching 协议。
- **直接收益**：
  1. **巨额成本节约**：将平均 20K~50K Tokens 的全量输入费用转化为廉价的 Cache Read 费用，API 成本直降 50%-80%。
  2. **响应速度起飞**：模型省略了庞大系统设定的 Context 阶段，首 Token 吐出延迟（TTFT）通常可缩短一半以上。