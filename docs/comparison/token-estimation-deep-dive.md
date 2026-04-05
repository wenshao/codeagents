# Token 估算与 Thinking 模型 Deep-Dive

> Agent 如何在发送 API 请求前估算 token 数？如何支持模型的扩展思维能力？本文基于 Claude Code（v2.1.89 源码分析）和 Qwen Code（v0.15.0 开源）的源码分析，对比两者在 token 计数、thinking 预算管理和多 Provider 适配方面的差异。

---

## 1. 架构总览

| 维度 | Claude Code | Qwen Code |
|------|------------|-----------|
| **Token 计数方式** | API 实时计数（主路径）+ 粗估回退 | 静态模式匹配（配置时） |
| **Thinking 支持** | 3 模式（adaptive/enabled/disabled）+ token 预算 | 3 档 effort（low/medium/high） |
| **Provider 适配** | 4 种（Direct/Bedrock/Vertex/Foundry） | 多 Provider 抽象（Anthropic/Gemini/OpenAI/DashScope） |
| **Token 缓存** | ✅ VCR fixture 系统（hash-based） | ❌ |
| **预算解析** | ✅ 自然语言（"+500k", "spend 2M tokens"） | ❌ |

---

## 2. Claude Code：API 实时计数

### 2.1 计数策略分层

```
首选: countTokensWithAPI()         → Anthropic beta.messages.countTokens()
      ↓ 不可用时
回退: countTokensViaHaikuFallback() → 使用 Haiku 4.5 计数（避免 Bedrock 限制）
      ↓ 不可用时
粗估: roughTokenCountEstimation()   → 4 字节/token（JSON 文件 2 字节/token）
```

> 源码: `services/tokenEstimation.ts`（496 行）

### 2.2 API 计数实现

```typescript
// 源码: services/tokenEstimation.ts#L124-L201
// 调用 Anthropic SDK: anthropic.beta.messages.countTokens()
// 参数: model, system prompt, messages, tools, thinking config
// 返回: { input_tokens: number }
```

**Thinking 计数常量**：

```typescript
// 源码: services/tokenEstimation.ts#L32-L33
const TOKEN_COUNT_THINKING_BUDGET = 1024    // 最小 thinking 预算
const TOKEN_COUNT_MAX_TOKENS = 2048         // 开启 thinking 时最低 max_tokens
```

**工具 Schema 预处理**（源码: `tokenEstimation.ts#L59-L122`）：
- 计数前剥离 `caller` 字段（ToolSearch 专用）
- 剥离 `tool_reference` 字段（ToolResult 内部引用）
- 防止内部元数据膨胀 token 计数

### 2.3 多 Provider 适配

| Provider | 计数方式 | 特殊处理 |
|----------|----------|----------|
| **Direct API** | `beta.messages.countTokens()` | 完整支持 |
| **Bedrock** | `CountTokensCommand`（动态加载 AWS SDK ~279KB） | 推理配置文件 → 底层模型解析 |
| **Vertex** | 1P API（过滤 web-search beta 防 400） | Beta header 兼容处理 |
| **Foundry** | 同 Direct API | — |

> 源码: `tokenEstimation.ts#L437-L495`（Bedrock）, `L150-L170`（Vertex）

### 2.4 粗估算法

```typescript
// 源码: tokenEstimation.ts#L203-L224
function roughTokenCountEstimation(text: string): number {
  // 默认: 4 bytes per token
  // JSON 文件: 2 bytes per token（JSON 更密集）
  return Math.ceil(Buffer.byteLength(text) / bytesPerToken)
}
```

### 2.5 Token VCR（缓存/录制）

```typescript
// 源码: services/vcr.ts#L382-L406
// withTokenCountVCR():
// - 用 SHA1 hash 键缓存 token 计数结果
// - 脱水: 移除 UUID、时间戳、工作目录 slug
// - 存储: fixtures/token-count-{hash}.json
// - 启用条件: 测试模式 或 FORCE_VCR=1（ant-only）
```

### 2.6 Token 预算自然语言解析

```typescript
// 源码: query/tokenBudget.ts#L21-L29
// 支持格式:
// "+500k"           → 500,000 tokens
// "spend 2M tokens" → 2,000,000 tokens
// "use 1b"          → 1,000,000,000 tokens
// 乘数: k=1K, m=1M, b=1B
//
// 继续条件: 已用 < 90% 预算，或 3 次以上连续增量 < 500 tokens
```

---

## 3. Claude Code：Thinking 模型支持

### 3.1 三种模式

```typescript
// 源码: utils/thinking.ts
type ThinkingConfig =
  | { type: 'adaptive' }                           // 模型自行决定
  | { type: 'enabled'; budgetTokens: number }       // 强制启用 + 预算
  | { type: 'disabled' }                            // 完全禁用
```

### 3.2 模型兼容性检测

```typescript
// 源码: utils/thinking.ts#L90-L144
// 1P/Foundry: 所有 Claude 4+ 模型（含 Haiku 4.5）
// 3P (Bedrock/Vertex): 仅 Opus 4+ 和 Sonnet 4+
//
// Adaptive Thinking: 仅 Opus 4.6、Sonnet 4.6 及更新（Claude 4.6+ 系列）
```

### 3.3 默认行为

```typescript
// 源码: utils/thinking.ts#L146-L162
function shouldEnableThinkingByDefault(): boolean {
  // 可通过 MAX_THINKING_TOKENS 环境变量覆盖
  // 可通过 alwaysThinkingEnabled 设置覆盖
  // 否则: 支持 adaptive → adaptive, 支持 enabled → enabled(budget), 不支持 → disabled
}
```

---

## 4. Qwen Code：静态模式匹配

### 4.1 Token 限制注册表

```typescript
// 源码: qwen-code/packages/core/src/core/tokenLimits.ts#L11-L12
DEFAULT_TOKEN_LIMIT = 131_072      // 128K（默认输入）
DEFAULT_OUTPUT_TOKEN_LIMIT = 32_000 // 32K（默认输出）
```

**模式匹配算法**（源码: `tokenLimits.ts#L20-L144`）：

```typescript
// 模型名规范化:
// "google/gemini-1.5-pro-20250219" → "gemini-1.5-pro" → 1M tokens
// "qwen-plus-latest" → 保留（特殊模型）
// 规范化: 剥离 provider 前缀、版本、日期、量化后缀
```

**部分模型映射（82 种模式）**：

| 模型 | 输入上限 | 输出上限 |
|------|:--------:|:--------:|
| Gemini 3.x | 1M | — |
| Claude 全系列 | 200K | 128K（Opus 4.6） |
| Qwen 3.x（商业 API） | 1M | 32K |
| Qwen 3.x（开源） | 256K | 32K |
| DeepSeek | 128K | — |

### 4.2 自动检测

```typescript
// 源码: modelsConfig.ts#L777-L780
if (gc.contextWindowSize === undefined) {
  this._generationConfig.contextWindowSize = tokenLimit(model.id, 'input')
}
// 在配置时自动从注册表查询，而非运行时 API 调用
```

### 4.3 Thinking/Reasoning 支持

```typescript
// 源码: qwen-code/packages/core/src/core/contentGenerator.ts#L96-L101
reasoning?: false | {
  effort?: 'low' | 'medium' | 'high';
  budget_tokens?: number;
}
```

**Provider 映射**：

| Provider | effort 映射 |
|----------|-----------|
| **Anthropic** | effort → beta header; `thinking: { type: 'enabled', budget_tokens }` |
| **Gemini** | `low → THINKING_MODE_OFF`, `medium → STANDARD`, `high → EXTENDED` |

---

## 5. 对比

| 维度 | Claude Code | Qwen Code |
|------|------------|-----------|
| Token 计数精度 | **精确**（API 实时） | **估算**（静态注册表） |
| 计数时机 | 运行时（每次 API 调用前） | 配置时（初始化） |
| 回退策略 | 3 层（API → Haiku → 粗估） | 单一默认值 |
| Thinking 模式 | 3 种（adaptive/enabled/disabled） | 3 档 effort（low/medium/high） |
| Thinking 预算 | 显式 token 数（`budget_tokens`） | effort 级别（无精确 token 控制） |
| Adaptive Thinking | ✅（Claude 4.6+ 独有） | ❌ |
| Token 缓存 | ✅ VCR fixture | ❌ |
| 预算语言解析 | ✅ "+500k"、"spend 2M" | ❌ |
| 多 Provider | 4 种，各有适配 | 多 Provider 抽象层 |

---

## 6. 关键源码文件

### Claude Code

| 文件 | 行数 | 职责 |
|------|------|------|
| `services/tokenEstimation.ts` | 496 | Token 计数（API + Haiku + 粗估） |
| `utils/thinking.ts` | 163 | Thinking 配置（模式/兼容性/默认值） |
| `query/tokenBudget.ts` | 94 | Token 预算自然语言解析 |
| `services/vcr.ts` | L382-L406 | Token 计数缓存（VCR fixture） |

### Qwen Code

| 文件 | 行数 | 职责 |
|------|------|------|
| `packages/core/src/core/tokenLimits.ts` | 233 | 静态 token 限制注册表（82 模式） |
| `packages/core/src/core/contentGenerator.ts` | L96-L101 | Reasoning 配置接口 |
| `packages/core/src/models/modelsConfig.ts` | L777-L780 | Token 限制自动检测 |

> **免责声明**: 以上分析基于 2026 年 Q1 源码（Claude Code v2.1.89、Qwen Code v0.15.0），后续版本可能已变更。
