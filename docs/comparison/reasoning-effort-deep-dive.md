# Reasoning Effort 设计对比：Claude Code / Codex CLI / OpenCode

> 处理 [Issue #130](https://github.com/wenshao/codeagents/issues/130)。逐源码对比 `reasoning_effort` / `effort` 在三家的设计差异、cache 影响、对 Qwen Code 支持 **DeepSeek `reasoning_effort`** 的启发。
>
> **数据**：
> - Claude `utils/effort.ts` 329 行 + `commands/effort/` ~80 行
> - Codex `protocol/src/openai_models.rs` + `core/src/config/mod.rs` + `tools/src/agent_tool.rs`
> - OpenCode `provider/transform.ts` ~1100 行（per-provider effort 适配器）
>
> **DeepSeek 支持参考**：[DeepSeek API 文档](https://api-docs.deepseek.com/zh-cn) · DeepSeek-Chat / DeepSeek-Reasoner / DeepSeek-V3 / DeepSeek-V4 系列均通过 OpenAI-compatible API 接收 `reasoning_effort`。

---

## 一、TL;DR

| 维度 | Claude Code | Codex CLI | OpenCode |
|---|---|---|---|
| **levels** | **5**：`low / medium / high / xhigh / max`（v2.1.123 二进制确认）| 6：`none / minimal / low / medium / high / xhigh` | **per-provider 自适应**（见 §2.5） |
| **default** | **Opus 4.7 launch pin = `xhigh`**；Opus 4.6 + Pro = `medium`；其他 = `undefined`(→API high) | `Medium`（静态） | provider 默认 |
| **CLI flag** | `--effort <level>` | ✗（用 `-c`）| ✗（走 model variants）|
| **Slash 命令** | ✓ `/effort` | ✗（合并在 `/model`）| ✗ |
| **环境变量** | ✓ `CLAUDE_CODE_EFFORT_LEVEL` | ✗ | ✗ |
| **持久化配置** | ✓ settings.json | ✓ TOML | ✓ JSON `provider.<id>.options` |
| **Plan 模式专用** | ✗ | ✓ `plan_mode_reasoning_effort` | ✗ |
| **Profile 切换** | ✗ | ✓ `config_profile` | 通过 model variant |
| **Agent 级** | ✓ skill **frontmatter** | ✓ agent **TOML** | ✓ `agent.<name>.model` 含 variant |
| **per-call override** | ⚠️ 不鼓励 | ✓ `spawn_agent` 参数 | 通过 variant 机制 |
| **per-provider 适配** | 白/黑名单 | `nearest_effort()` snap | **per-provider 表驱动**（最丰富）|
| **DeepSeek 支持** | ⚠️ 仅 1P 模型默认开 effort | ✓ 通过 `-c` 通用机制 | ✓ **明确支持 V3/Chat/Reasoner/V4**（V4 含 `max`）|
| **设计哲学** | session-level + cache-friendly | 配置驱动 + 模式分支 + 灵活 | **per-provider 适配 + variant 机制** |

---

## 二、关键差异深度分析

### 2.1 Levels 与默认值

**Claude（v2.1.123 实测 5 档）**：

```typescript
// 二进制 v2.1.123 反编译 (LB 常量)
EFFORT_LEVELS = ['low', 'medium', 'high', 'xhigh', 'max']
```

> ⚠️ **泄露源码（`utils/effort.ts:13-18`）只有 4 档**（`low / medium / high / max`），但 v2.1.123 的二进制已添加 **`xhigh`**。差异说明泄露源码早于 Opus 4.7 发布（`undercover.ts:49` 把 `opus-4-7` 列为 "Unreleased model version numbers"）。

**支持矩阵（v2.1.123 确认）**：

| Level | Opus 4.7 | Opus 4.6 | Sonnet 4.6 | 其他 |
|---|:-:|:-:|:-:|:-:|
| `low / medium / high` | ✓ | ✓ | ✓ | （3P override 决定）|
| **`xhigh`** | ✓ **独占** | snap → `high` | snap → `high` | snap → `high` |
| `max` | ✓ | ✓ | ✓ | snap → `high` |

**默认值（关键）**：

- **Opus 4.7 launch pin**：`Y86()` 函数返回 `xhigh`（专门为 4.7 launch 启用）
- **Opus 4.6 + Pro/Max/Team subscriber + `tengu_grey_step2`**：`medium`
- **其他**：`undefined`（API 解析为 `high`）

**Opus 4.7 的 launch pin 机制**：

```js
// 二进制 v2.1.123 反编译核心逻辑（vxH = resolveAppliedEffort）
function vxH(model, appStateEffort) {
  let isLaunchPinActive = model.includes("opus-4-7") &&
                          !globalConfig.unpinOpus47LaunchEffort
  let launchDefault = Y86(model)              // opus-4-7 → "xhigh", 其他 → "high"
  let envOverride   = mPH()                    // CLAUDE_CODE_EFFORT_LEVEL

  if (envOverride === null) return isLaunchPinActive ? launchDefault : undefined
  let resolved = envOverride ?? (isLaunchPinActive ? launchDefault : undefined)
                              ?? appStateEffort
                              ?? launchDefault
  if (resolved === "max"   && !V9$(model)) return "high"  // max 不支持 → snap
  if (resolved === "xhigh" && !k9$(model)) return "high"  // xhigh 不支持 → snap
  return resolved
}

// 用户首次显式选 effort → 永久解除 launch pin（globalConfig 写盘）
function setOpusLaunchEffort(value) {
  if (parsed !== undefined) {
    setGlobalConfig(c => c.unpinOpus47LaunchEffort
                          ? c
                          : { ...c, unpinOpus47LaunchEffort: true })
  }
  return parsed ?? bN1()
}
```

**Anthropic 在二进制内嵌的官方说明**（`shared/models.md` 等内置文档字符串）：

> "Opus 4.7 adds `"xhigh"` (between `high` and `max`) — the best setting for most coding and agentic use cases on 4.7, and **the default in Claude Code**; use a minimum of `high` for most intelligence-sensitive work."

**持久化（`N9$` = `toPersistableEffort`）**：

```js
function N9$(value) {
  if (value === "low" || value === "medium" || value === "high" || value === "xhigh") return value
  // max 仍然不持久化（避免 session-only 选择泄漏）
  return undefined
}
```

`xhigh` 已加入持久化白名单；`max` 维持非持久化。

**Codex（6 档）**：

```rust
// protocol/src/openai_models.rs:43-51
pub enum ReasoningEffort {
    None, Minimal, Low, #[default] Medium, High, XHigh,
}
```

- 比 Claude 多 `None`（**不发送** reasoning 字段，不是 effort=0）和 `Minimal`
- 默认 `Medium`（静态 enum default）
- `nearest_effort()` (line 525) 把不支持的 effort snap 到最近档（用户配 `xhigh` 但模型只支持 `[low, medium, high]` → `high`）

**xhigh 趋同**：Claude v2.1.123 + Codex 都引入 `xhigh`（位于 `high` 与 `max` 之间），但 Codex 的 `xhigh` 是**全局枚举的一档**，Claude 的 `xhigh` 是 **opus-4-7 独占**且**默认值**。

---

### 2.2 用户入口（Claude 4 层 vs Codex 主走配置）

**Claude 4 层入口**：

| 层 | 机制 | 持久 | 源码 |
|---|---|:-:|---|
| CLI | `--effort low\|medium\|high\|xhigh\|max` | ✗ | `main.tsx:993`（`xhigh` 仅 Opus 4.7）|
| Slash | `/effort low` | ✓ 写 settings.json | `commands/effort/effort.tsx` |
| Env | `CLAUDE_CODE_EFFORT_LEVEL` | env-controlled | `utils/effort.ts:136-142` |
| Config | `settings.json` `effortLevel` | ✓ | `utils/effort.ts:107-111` |

**优先级**（`utils/effort.ts:152-172`）：env → appState → model default

**Codex 主走配置**：

| 层 | 机制 | 源码 |
|---|---|---|
| CLI 临时 | `codex -c model_reasoning_effort=high`（通用 `-c`，**无独立 flag**）| 通用机制 |
| Profile | `config_profile.model_reasoning_effort` | `config/mod.rs:2575-2577` |
| 全局 TOML | `model_reasoning_effort = "medium"` | `config/mod.rs:595` |
| **Plan 模式专用** | `plan_mode_reasoning_effort = "high"` | `config/mod.rs:602` |

**优先级**（`config/mod.rs:2575-2580`）：profile → global config

---

### 2.3 Plan 模式专用（Codex 独有）

```rust
// codex-rs/core/src/config/mod.rs:596-602
/// When unset, Plan mode uses the built-in Plan preset default (currently
/// `medium`). When explicitly set (including `none`), this overrides the
/// Plan preset. The `none` value means "no reasoning" (not "inherit").
pub plan_mode_reasoning_effort: Option<ReasoningEffort>,
```

**关键**：`None` 是显式值（不发送 reasoning），**不等于"未设置走全局默认"**。这是 Rust `Option<Option<T>>` 风格的二阶可选语义。

**Claude 没有 Plan-mode 专用配置** —— Plan 模式走当前 session effort。

---

### 2.4 Agent / Skill 级配置（双方均有，路径不同）

**Claude**：YAML frontmatter

```yaml
# .claude/skills/code-reviewer/SKILL.md
---
name: code-reviewer
effort: high      # 或数值（ANT-only）
---
```

源码 `skills/loadSkillsDir.ts:205, 230`：`parseEffortValue(frontmatter['effort'])`

**Codex**：独立 TOML 文件

```toml
# codex-rs/core/src/agent/builtins/awaiter.toml
background_terminal_max_timeout = 3600000
model_reasoning_effort = "low"      # awaiter 是 polling-only，无需复杂推理
developer_instructions = """..."""
```

**Codex 还允许 `spawn_agent` 工具 per-call 覆盖**（`tools/src/agent_tool.rs:539-541`）：

```rust
"reasoning_effort".to_string(),
"Optional reasoning effort override for the new agent. Replaces the inherited reasoning effort."
```

---

### 2.5 OpenCode 的 per-provider 适配器模式

OpenCode `provider/transform.ts` 用**单一函数 + provider 大 switch** 给每个 provider/model 组合返回一份 effort 列表，作为 model 的 **variants**。

**核心常量**（line ~447）：

```typescript
const WIDELY_SUPPORTED_EFFORTS = ["low", "medium", "high"]
const OPENAI_EFFORTS = ["none", "minimal", ...WIDELY_SUPPORTED_EFFORTS, "xhigh"]
```

**Provider 适配示例**：

```typescript
// transform.ts 简化版
switch (sdkName) {
  case "@ai-sdk/openai":
    return OPENAI_EFFORTS  // 6 档全开

  case "@ai-sdk/anthropic":
    if (apiId.includes("opus-4-7")) return ["low","medium","high","xhigh","max"]
    if (apiId.includes("opus-4-6") || apiId.includes("sonnet-4-6")) return ["low","medium","high","max"]
    return []

  case "@ai-sdk/openai-compatible":  // ← DeepSeek 走这里
    const efforts = [...WIDELY_SUPPORTED_EFFORTS]  // [low, medium, high]
    if (model.api.id.includes("deepseek-v4")) efforts.push("max")  // V4 加 max
    return efforts

  case "@ai-sdk/azure":
    if (id === "o1-mini") return []
    return ["low","medium","high"]

  case "@ai-sdk/github-copilot":
    if (id.includes("gemini")) return []  // gemini 不支持
    if (id.includes("claude")) return ["low","medium","high"]
    if (id.includes("5.1-codex-max")||id.includes("5.2")||id.includes("5.3"))
      return [...WIDELY_SUPPORTED_EFFORTS, "xhigh"]
    return OPENAI_EFFORTS
}
```

**核心机制**：每个 effort 注册为 model 的 **variant**（`provider.<id>.models.<id>.variants.high = { reasoningEffort: "high" }`），用户通过 model variant 切换：

```jsonc
{
  "agent": {
    "build": { "model": "anthropic/claude-sonnet-4-6", "variant": "high" },
    "plan":  { "model": "anthropic/claude-sonnet-4-6", "variant": "max" }
  }
}
```

**与 Claude/Codex 区别**：
- Claude / Codex：effort 是**独立 API 参数**
- OpenCode：effort 通过 **model variant 名字**间接表达 → variant name 进入 model id → 完全融入 model 选择路径

**OpenCode 对 DeepSeek 的特别处理（双层）**：

**Layer 1**：assistant 消息强制含 `reasoning` part（`transform.ts:200-215`）：

```typescript
// Deepseek requires all assistant messages to have reasoning on them
if (model.api.id.includes("deepseek")) {
  msgs = msgs.map((msg) => {
    if (msg.role !== "assistant") return msg
    if (Array.isArray(msg.content)) {
      if (msg.content.some((part) => part.type === "reasoning")) return msg
      return { ...msg, content: [...msg.content, { type: "reasoning", text: "" }] }
    }
    // ...
  })
}
```

**Layer 2**：`interleaved.field = "reasoning_content"` 触发的 `providerOptions` 注入（`transform.ts:217-249`）：

```typescript
if (typeof model.capabilities.interleaved === "object" &&
    model.capabilities.interleaved.field &&
    model.api.npm !== "@openrouter/ai-sdk-provider") {
  const field = model.capabilities.interleaved.field   // "reasoning_content"
  return msgs.map((msg) => {
    if (msg.role === "assistant" && Array.isArray(msg.content)) {
      const reasoningParts = msg.content.filter(p => p.type === "reasoning")
      const reasoningText  = reasoningParts.map(p => p.text).join("")
      return {
        ...msg,
        content: msg.content.filter(p => p.type !== "reasoning"),  // 提出 reasoning
        providerOptions: {
          openaiCompatible: { [field]: reasoningText }              // 转 reasoning_content
        }
      }
    }
    return msg
  })
}
```

**自动检测（commit 738b3065d, 2026-04-27 合并 PR#24630）**：当 DeepSeek 模型走 `@ai-sdk/openai-compatible` 且无 `existingModel` 定义时，OpenCode 自动设置 `interleaved = { field: "reasoning_content" }`：

```typescript
// provider.ts:1182-1187
interleaved:
  model.interleaved ??
  existingModel?.capabilities.interleaved ??
  (!existingModel && apiNpm === "@ai-sdk/openai-compatible" && apiID.includes("deepseek")
    ? { field: "reasoning_content" }
    : false),
```

DeepSeek 多轮对话需要 reasoning 字段在 message 间持续传递，OpenCode 通过两层处理保证：
- **Layer 1** 保证 message 结构合法（即使空 reasoning 也补占位符）
- **Layer 2** 把 reasoning 文本提到 `providerOptions.openaiCompatible.reasoning_content`，符合 DeepSeek API 格式

**Qwen Code 当前未处理任一层约束**（`provider/deepseek.ts` 仅做 content array → string 扁平化）。

---

### 2.6 ⚠️ Cache 影响（Issue 核心点）

**Claude 的设计权衡**：

源码 `query.ts:694` 主 loop 用 `appState.effortValue`（session-level）。Issue #130 引用的关键证据：

> "prompt suggestion 曾尝试设置 `effort: 'low'`，但因影响 prompt cache 命中率，最终避免覆盖 effortValue"

**机制**：Anthropic API 把 `reasoning_effort` 纳入 prompt cache key，同一 conversation 用 `medium` vs `high` 是**独立 cache 链**。反复切换 → 每次 cache miss → token 成本爆炸。

**Claude 的应对**：
1. session-scoped 持久（`/effort` 改后整 session 不变）
2. subagent 默认继承父 effort
3. **高频路径禁止覆盖**（prompt suggestion / forked agent 不改 effort）

**Codex 的不同选择**：

源码 `tools/src/agent_tool.rs:539-541` 主动暴露 `reasoning_effort` per-call 参数。`multi_agents_common.rs:317-331` 在 spawn agent 时主动注入 effort。**与 Claude 的"高频禁覆盖"哲学相反**。

**可能原因**（待源码核对）：
- OpenAI Responses API 的 cache 策略与 Anthropic Messages API 不同
- spawn agent 是独立 conversation context，与父 cache 无重叠

> ⚠️ **未验证项**：OpenAI Responses API 的 cache key 是否含 `reasoning_effort` —— 待官方文档/源码进一步核对。

**结论**：

| 路径 | 是否安全 | 原因 |
|---|:-:|---|
| Session-level 持久切换 | ✓ | cache 链一致 |
| Subagent spawn 时设置（独立 context）| ✓ | 无 cache 重叠 |
| 同一 turn 内反复切换 | ✗ | 破坏 cache 链 |
| prompt suggestion 等高频路径 override | ✗ | Claude 实测确认 |

---

## 三、对 Qwen Code 支持 DeepSeek `reasoning_effort` 的具体方案

> 用户主要诉求："**主要是要支持 deepseek 的 reasoning_effort**"。本节聚焦 DeepSeek（通用 effort 框架是基础）。

### 3.1 Qwen Code 当前状态

源码 `packages/core/src/core/openaiContentGenerator/pipeline.ts:437-464` `buildReasoningConfig`：

```typescript
// 已经支持透传 reasoning 字段到 OpenAI-compatible 请求
private buildReasoningConfig(request: GenerateContentParameters) {
  if (request.config?.thinkingConfig?.includeThoughts === false) return {}
  const reasoning = this.contentGeneratorConfig.reasoning
  if (reasoning === false || reasoning === undefined) return {}
  return { reasoning }
}
```

**已具备的基础**：
- ✓ `pipeline.ts:431` 在请求中拼入 reasoning 配置
- ✓ `pipeline.ts:443-447` 注释列出多 provider 的 thinking 行为差异（含 deepseek-reasoner）
- ✓ `provider/deepseek.ts:13` `DeepSeekOpenAICompatibleProvider` 类已存在（处理 content array → string flatten）

**当前缺失**：
- ✗ **无 user-facing 入口**让用户传 `reasoning.effort = "high"`（settings.json / CLI / slash 都没）
- ✗ **DeepSeek V4 的 `max` 档**未识别（OpenCode V4 加 max 是关键 differentiator）
- ✗ **DeepSeek assistant-message-must-have-reasoning 约束**未处理（OpenCode Layer 1，`transform.ts:200-215`）
- ✗ **DeepSeek `reasoning_content` 字段往返**未处理（OpenCode Layer 2 + 自动检测，`transform.ts:217-249` + `provider.ts:1182-1187`，PR#24630 / commit `738b3065d` 2026-04-27 合并）
- ✗ **no per-provider effort 列表表**（Claude 用白/黑名单，Codex 用 nearest_effort，OpenCode 用 per-provider switch）

### 3.2 DeepSeek 系列的实际 effort 行为

参考 [DeepSeek API 文档](https://api-docs.deepseek.com/zh-cn) + OpenCode 源码确认：

| 模型 | `reasoning_effort` 支持档 | 默认行为 |
|---|---|---|
| `deepseek-chat` | `low / medium / high`（推测，参考 OpenCode `WIDELY_SUPPORTED_EFFORTS`）| 不开 thinking |
| `deepseek-reasoner` (R1) | thinking 默认开，无法 disable（pipeline.ts:443 注释）| 始终 reasoning |
| `deepseek-v3` | `low / medium / high` | 见模型卡 |
| **`deepseek-v4`** | `low / medium / high / **max**` ← V4 独有 max 档 | OpenCode `transform.ts:576-579` 确认 |

> ⚠️ **未现场验证**：上表 effort 档列表来自 OpenCode 源码推断 + 行业惯例，建议实施时对照 [DeepSeek 官方 API 文档](https://api-docs.deepseek.com/zh-cn) 最新值确认。

### 3.3 推荐实施方案（4 步）

#### Step 1：扩展 `ContentGeneratorConfig.reasoning` schema 支持 effort（~30 行 / 0.5 天）

```typescript
// packages/core/src/core/contentGenerator.ts
export type ReasoningEffort = 'low' | 'medium' | 'high' | 'max' | 'none'

export interface ReasoningConfig {
  effort?: ReasoningEffort
  // ... 其他保留字段
}
```

#### Step 2：DeepSeek provider 实现 effort 映射（~80 行 / 1 天）

```typescript
// packages/core/src/core/openaiContentGenerator/provider/deepseek.ts
export class DeepSeekOpenAICompatibleProvider extends DefaultOpenAICompatibleProvider {

  private supportedEfforts(): string[] {
    const model = this.contentGeneratorConfig.model ?? ''
    if (model.toLowerCase().includes('deepseek-v4')) {
      return ['low', 'medium', 'high', 'max']  // V4 加 max
    }
    if (model.toLowerCase().includes('deepseek-reasoner')) {
      return []  // R1 always thinking, no effort override
    }
    return ['low', 'medium', 'high']  // V3 / chat
  }

  override buildRequest(request, userPromptId): OpenAI.Chat.ChatCompletionCreateParams {
    const baseRequest = super.buildRequest(request, userPromptId)

    // Step A: 现有 content flatten 逻辑保留

    // Step B: 验证 effort 在该模型支持档内（snap 不支持的到最近档）
    if (baseRequest.reasoning_effort) {
      const supported = this.supportedEfforts()
      if (supported.length === 0) {
        delete baseRequest.reasoning_effort  // R1 模型移除
      } else if (!supported.includes(baseRequest.reasoning_effort)) {
        baseRequest.reasoning_effort = nearestEffort(baseRequest.reasoning_effort, supported)
      }
    }

    // Step C: assistant message 必须含 reasoning（OpenCode Layer 1，transform.ts:200-215）
    baseRequest.messages = baseRequest.messages.map(msg => {
      if (msg.role !== 'assistant') return msg
      // 给 array content 加空 reasoning 占位
      if (Array.isArray(msg.content) && !msg.content.some(p => p.type === 'reasoning')) {
        return { ...msg, content: [...msg.content, { type: 'reasoning', text: '' }] }
      }
      return msg
    })

    // Step D: reasoning 文本提到顶层 reasoning_content（OpenCode Layer 2，transform.ts:217-249）
    //         多轮对话时 DeepSeek 期望 reasoning_content 跟随 assistant 消息一起回传
    baseRequest.messages = baseRequest.messages.map((msg: any) => {
      if (msg.role !== 'assistant' || !Array.isArray(msg.content)) return msg
      const reasoningParts = msg.content.filter((p: any) => p.type === 'reasoning')
      const reasoningText  = reasoningParts.map((p: any) => p.text).join('')
      return {
        ...msg,
        content: msg.content.filter((p: any) => p.type !== 'reasoning'),
        reasoning_content: reasoningText,  // 即使空字符串也保留（OpenCode 注释说明）
      }
    })

    return baseRequest
  }
}
```

#### Step 3：用户入口（settings.json 优先，~50 行 / 0.5 天）

```jsonc
// .qwen/settings.json
{
  "reasoning": {
    "effort": "high"     // 全局
  }
}
```

`pipeline.ts:457` 的 `this.contentGeneratorConfig.reasoning` 已经从 settings 读取 —— 只需保证 schema 支持 effort 字段。

可选扩展（参考 Codex）：
```jsonc
{
  "reasoning": {
    "effort": "medium",
    "planModeEffort": "high"   // 如 Qwen 实现 Plan 模式
  }
}
```

#### Step 4：可选 - CLI flag + `/effort` slash（~80 行 / 1 天）

参考 Claude `--effort` + `/effort` 的实现模式。**警告**：实施 `/effort` 之前先做 cache 度量（见 §2.6）。

### 3.4 实施 checklist

| 任务 | 文件 | 工作量 |
|---|---|:-:|
| 扩展 `ReasoningConfig.effort` 类型 | `core/contentGenerator.ts` | 0.5 天 |
| DeepSeek provider 模型映射 | `core/openaiContentGenerator/provider/deepseek.ts` | 1 天 |
| DeepSeek V4 `max` 档支持 | 同上 | 含 |
| DeepSeek assistant message reasoning placeholder | 同上 | 含 |
| settings.json schema 支持 `reasoning.effort` | `cli/src/config/settingsSchema.ts` | 0.5 天 |
| 单测：3 模型 × 4 effort 档行为 | `provider/deepseek.test.ts` | 0.5 天 |
| 文档更新：Qwen Code DeepSeek 配置示例 | `docs/users/...` | 0.3 天 |
| **`--effort` CLI flag**（可选）| `cli/src/cli.ts` | 0.5 天 |
| **`/effort` slash**（可选）| `cli/src/commands/effortCommand.ts` | 0.5 天 |

**核心实施 ~3 天**（不含 CLI/slash）。

### 3.5 通用 effort 框架（更长期）

如果除了 DeepSeek 还想做通用支持：

| Phase | 内容 | 工作量 |
|:-:|---|:-:|
| **P0** | DeepSeek `reasoning_effort` 完整支持（§3.3 全 4 步）| ~3 天 |
| **P1** | OpenAI / GPT-5.x / Anthropic Opus 4.6+ 的 effort 适配 | ~2 天 |
| **P2** | per-provider effort 表（OpenCode 风格 transform.ts）| ~3 天 |
| **P3** | CLI / slash / env / `/status` 显示（Claude 风格）| ~2 天 |
| **P4** | Cache 监控 dashboard | ~1 天 |

**总 ~11 天**。建议**先 P0 + P4**（DeepSeek 落地 + cache 度量基线）。

### 3.6 ⚠️ Cache 影响（实施前必读）

参考 §2.6 Claude 经验。**对 DeepSeek 特别注意**：

- DeepSeek 走 OpenAI-compatible API，cache 行为可能跟 OpenAI 一致（待官方文档确认）
- `reasoning_effort` 切换可能破坏 prompt cache hit rate
- 建议：**session-level 持久**（用户改才变），不在 turn 中切换

---

## 四、附录 A：源码引用索引

### Claude Code（泄露源码）

> ⚠️ 泄露源码先于 Opus 4.7 发布。下表反映泄露源码的 4 档设计；v2.1.123 二进制已升级为 5 档（见下方"v2.1.123 二进制反编译"）。

| 文件 | 行 | 功能 |
|---|---|---|
| `utils/effort.ts` | 13-18 | `EFFORT_LEVELS` 4 档 |
| 同 | 23-49 | `modelSupportsEffort` |
| 同 | 53-65 | `modelSupportsMaxEffort`（仅 Opus 4.6）|
| 同 | 71-92 | `parseEffortValue`（含 ANT 数值）|
| 同 | 95-105 | `toPersistableEffort`（max 不持久）|
| 同 | 107-111 | `getInitialEffortSetting` |
| 同 | 136-142 | `getEffortEnvOverride` |
| 同 | 152-172 | `resolveAppliedEffort` 优先级链 |
| 同 | 279-329 | `getDefaultEffortForModel`（subscription tier）|
| `commands/effort/effort.tsx` | — | `/effort` slash |
| `main.tsx` | 993 | `--effort` CLI flag |
| `query.ts` | 694 | 主 loop 用 `appState.effortValue` |
| `skills/loadSkillsDir.ts` | 205, 230 | skill frontmatter `effort` |
| `utils/undercover.ts` | 49 | 把 `opus-4-7` 列为 unreleased（说明泄露时点）|

### Claude Code（v2.1.123 二进制反编译）

> 反编译 ID 为 mangled 标识符（`Y86`/`vxH`/`V9$`/`k9$` 等）；功能映射到原源码语义。

| Mangled 名 | 源码对应 | 功能 |
|---|---|---|
| `LB` | `EFFORT_LEVELS` | 5 档：`["low","medium","high","xhigh","max"]` |
| `Y86` | 新增（无源码对应） | 返回模型的 launch 默认 effort：`opus-4-7 → "xhigh"`，其他 → `"high"` |
| `vxH` | `resolveAppliedEffort` | 含 `unpinOpus47LaunchEffort` 状态分支 |
| `z86` | 新增（unpin trigger）| 用户首次设置 effort 时把 `unpinOpus47LaunchEffort = true` 写盘 |
| `V9$` | `modelSupportsMaxEffort` | 允许：`opus-4-7` + `opus-4-6` + `sonnet-4-6` |
| `k9$` | 新增（xhigh 支持检测）| 允许：**仅 `opus-4-7`** |
| `kfH` / `x5$` | `modelSupportsEffort` | 允许：`opus-4-7` / `opus-4-6` / `sonnet-4-6` |
| `N9$` | `toPersistableEffort` | 持久化：`low/medium/high/xhigh`；`max` 仍排除 |
| 全局配置字段 | — | `unpinOpus47LaunchEffort: boolean`（写到 `~/.claude.json`）|

**对应的 Anthropic 内嵌文档（二进制内 `shared/models.md` 字符串）**：

- "Opus 4.7 adds `"xhigh"` (between `high` and `max`) — the best setting for most coding and agentic use cases on 4.7, and **the default in Claude Code**"
- "On Opus 4.7, effort matters more than on any prior Opus — re-tune it when migrating"
- Opus 4.7 同时移除 `temperature` / `top_p` / `top_k` / `budget_tokens`（强制 adaptive thinking）

### Codex CLI（main 分支 @ 2026-04-28 21:41 commit `3d10ba9f36`）

| 文件 | 行 | 功能 |
|---|---|---|
| `codex-rs/protocol/src/openai_models.rs` | 43-51 | `ReasoningEffort` enum 6 档 |
| 同 | 514-532 | `nearest_effort` snap |
| `codex-rs/core/src/config/mod.rs` | 595 | `model_reasoning_effort` 全局 |
| 同 | 596-602 | `plan_mode_reasoning_effort` Plan 模式 |
| 同 | 2575-2580 | profile → cfg fallback |
| `codex-rs/core/src/tools/handlers/multi_agents_common.rs` | 317-331 | spawn 时注入 |
| `codex-rs/core/src/agent/builtins/awaiter.toml` | 2 | 内置 agent `model_reasoning_effort = "low"` |
| `codex-rs/tools/src/agent_tool.rs` | 539, 572 | `spawn_agent` 工具 `reasoning_effort` 参数 |
| `codex-rs/tui/src/slash_command.rs` | 102 | `/model` 描述含 reasoning effort |
| `codex-rs/core/src/session/turn_context.rs` | — | `Add reasoning effort to turn tracing spans` (commit `99b39b6350` 在 `dev/charley/turn-reasoning-effort-tracing` 分支，**未合并 main**) |

### OpenCode（dev 分支 @ 2026-04-29 13:23 commit `d71b827d8`）

| 文件 | 行 | 功能 |
|---|---|---|
| `packages/opencode/src/provider/transform.ts` | 200-215 | **Layer 1**：DeepSeek assistant message 补 `reasoning` 占位符 |
| 同 | 217-249 | **Layer 2**：`interleaved.field = "reasoning_content"` → `providerOptions.openaiCompatible.reasoning_content` 注入 |
| 同 | ~446-449 | `WIDELY_SUPPORTED_EFFORTS = [low,medium,high]` / `OPENAI_EFFORTS` |
| 同 | 大 switch | per-provider effort 列表（openai / anthropic / openai-compatible / azure / github-copilot 等）|
| 同 | ~576-579 | DeepSeek-V4 在 `openai-compatible` 分支加 `max` |
| `packages/opencode/src/provider/provider.ts` | 1182-1187 | 自动检测 DeepSeek + openai-compatible → 默认 `interleaved = { field: "reasoning_content" }`（PR#24630 / commit `738b3065d` 2026-04-27 合并）|

每个 effort 注册为 model 的 **variant**（参见 `Provider.ts` `model.variants`），用户通过 `provider/<id>:variant` 间接选 effort。

### Qwen Code（当前状态参考）

| 文件 | 行 | 功能 |
|---|---|---|
| `packages/core/src/core/openaiContentGenerator/pipeline.ts` | 437-464 | `buildReasoningConfig` 已支持 reasoning passthrough |
| `packages/core/src/core/openaiContentGenerator/provider/deepseek.ts` | — | `DeepSeekOpenAICompatibleProvider`（仅 content 扁平化，无 effort 适配）|

---

## 五、附录 B：相关文档

- [Codex CLI 对标改进](./qwen-code-codex-improvements.md)
- [API 参数与重试策略对比](./api-params-deep-dive.md)
- [Token 估算策略](./token-estimation-deep-dive.md)
- [Claude Code 命令清单](../tools/claude-code/02-commands.md) · [多 Agent](../tools/claude-code/09-multi-agent.md) · [Prompt Suggestions](../tools/claude-code/10-prompt-suggestions.md)
- [Codex CLI 命令清单](../tools/codex-cli/02-commands.md) · [Evidence](../tools/codex-cli/EVIDENCE.md)
- [OpenCode 多模型架构](./model-routing.md)
- [DeepSeek 官方 API 文档（reasoning_effort）](https://api-docs.deepseek.com/zh-cn/guides/reasoning_model)

---

**最后更新**：2026-04-29 · **Issue**：[#130](https://github.com/wenshao/codeagents/issues/130)
