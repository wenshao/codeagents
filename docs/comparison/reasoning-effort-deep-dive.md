# Reasoning Effort 设计对比 Deep-Dive：Claude Code vs Codex CLI

> 处理 [Issue #130](https://github.com/wenshao/codeagents/issues/130)。逐源码核对 Claude Code 与 Codex CLI 在 `reasoning_effort` / `effort` 设计上的差异、源码证据、cache 影响，以及对其他 Code Agent（特别是 Qwen Code）的设计启发。
>
> **数据范围**：Claude Code（`utils/effort.ts` 329 行 + `commands/effort/`）vs Codex CLI（`codex-rs/protocol/src/openai_models.rs` + `codex-rs/core/src/config/mod.rs`）
>
> **最后核对**：2026-04-29

---

## 一、TL;DR

| 维度 | Claude Code | Codex CLI |
|---|---|---|
| **levels** | `low / medium / high / max` (4) | `none / minimal / low / medium / high / xhigh` (6) |
| **CLI flag** | `--effort <level>` | 无独立 flag，用 `-c model_reasoning_effort=<level>` |
| **Slash 命令** | ✓ `/effort` | ✗（无独立命令；`/model` 选项中可调）|
| **环境变量** | `CLAUDE_CODE_EFFORT_LEVEL`（含 `unset`/`auto`）| 无 |
| **配置项** | settings.json `effortLevel` | TOML `model_reasoning_effort` |
| **Plan 模式专用** | ✗（无独立 plan-mode 配置）| ✓ `plan_mode_reasoning_effort` |
| **Agent 级配置** | ✓ skill / subagent frontmatter `effort` | ✓ agent toml `model_reasoning_effort`（如 `awaiter.toml`）|
| **运行时模型支持探测** | ✓ `modelSupportsEffort` + `modelSupportsMaxEffort` | ✓ `nearest_effort()` 自动 snap 到模型支持的最近档位 |
| **per-call override** | ⚠️ 技术可，但 **prompt-suggestion 经验**避免（cache 影响）| ✓ `spawn_agent` tool 含 `reasoning_effort` 参数 |
| **数值/连续值** | ✓ ANT-only 数值 effort | ✗ 仅枚举 |
| **核心源码量** | `utils/effort.ts` 329 行 + 配套 ~200 行 | `openai_models.rs` 部分 + `config/mod.rs` 部分 |

**核心区别**：

- **Claude 偏向"用户交互式调档"** —— 提供独立 CLI flag、`/effort` slash 命令、env var、settings.json 4 层入口；模型默认值由 subscription tier 影响（Pro vs Max vs Team）
- **Codex 偏向"配置文件 + 模式分支"** —— 全局 `model_reasoning_effort` + Plan 模式专用 + spawn_agent 时可注入；通过 `nearest_effort()` 自动适配模型能力

---

## 二、Claude Code 的 effort 设计

### 2.1 levels

```typescript
// utils/effort.ts:13-18
export const EFFORT_LEVELS = [
  'low',
  'medium',
  'high',
  'max',
] as const satisfies readonly EffortLevel[]
```

**注意**：`max` 仅在 **Opus 4.6** 上支持（`utils/effort.ts:53-65` `modelSupportsMaxEffort`），其他模型 API 会拒绝。从非 Opus-4.6 模型上读 `max` 时自动**降级为 `high`**（line 162-164）。

### 2.2 优先级链（解析顺序）

源码 `utils/effort.ts:152-172` `resolveAppliedEffort`：

```typescript
// 优先级（高到低）：
//   env CLAUDE_CODE_EFFORT_LEVEL
//   → appState.effortValue (CLI --effort / /effort / settings.json)
//   → getDefaultEffortForModel(model)
```

### 2.3 4 层用户入口

| 层级 | 机制 | 持久化 | 源码 |
|---|---|:-:|---|
| **CLI flag** | `--effort low\|medium\|high\|max` | ✗ session-only | `main.tsx:993` |
| **Slash command** | `/effort low` `/effort medium` `/effort high` `/effort max` | **写 userSettings.json** | `commands/effort/effort.tsx` |
| **环境变量** | `CLAUDE_CODE_EFFORT_LEVEL=<value>`（特殊值 `unset` / `auto`）| ✗ env-controlled | `utils/effort.ts:136-142` `getEffortEnvOverride` |
| **settings.json** | `effortLevel: 'low'\|'medium'\|'high'` | ✓ 持久 | `utils/effort.ts:107-111` `getInitialEffortSetting` |

**注意**：
- `'max'` 不持久化到 settings.json（line 95-104 `toPersistableEffort` 过滤）—— 即使用户 `/effort max` 也只 in-memory，避免脏 settings 污染下次 session
- `'max'` 持久化对 `USER_TYPE === 'ant'` 例外（Anthropic 内部）

### 2.4 Agent / Skill 级 effort

源码 `skills/loadSkillsDir.ts:205, 230`：

```typescript
// frontmatter 解析
effort: EffortValue | undefined  // ← skill / agent 可声明独立 effort
const effortRaw = frontmatter['effort']
const effort = effortRaw !== undefined ? parseEffortValue(effortRaw) : undefined
```

**支持值**：`'low'` / `'medium'` / `'high'` / `'max'` 或**整数**（数值 effort，仅 ANT-only 路径）。

### 2.5 模型支持检测

源码 `utils/effort.ts:23-49`：

```typescript
export function modelSupportsEffort(model: string): boolean {
  // ANT 内部：CLAUDE_CODE_ALWAYS_ENABLE_EFFORT 强制开
  // 1P：opus-4-6 / sonnet-4-6 ✓
  // 1P：haiku / 老 opus/sonnet ✗
  // 1P 未知模型默认 true
  // 3P 未知模型默认 false（避免 model 字符串格式不一致）
}
```

### 2.6 数值 effort（ANT-only）

`utils/effort.ts:243-246`：

```typescript
if (process.env.USER_TYPE === 'ant' && typeof value === 'number') {
  return `[ANT-ONLY] Numeric effort value of ${value}`
}
```

外部用户只能用 4 个枚举值。

### 2.7 模型默认 + 订阅 tier 影响

源码 `utils/effort.ts:279-329` `getDefaultEffortForModel`：

```typescript
// Opus 4.6 + Pro subscriber → default 'medium'
// Opus 4.6 + Max/Team + tengu_grey_step2 enabled → default 'medium'
// 启用 ultrathink + modelSupportsEffort → default 'medium'
// 否则 → undefined（API 端解析为 'high'）
```

**关键**：默认值由 GrowthBook flag `tengu_grey_step2` + subscription 共同决定。Pro 用户对 Opus 4.6 的默认是 `medium`（控制 rate limit + 成本），其他用户走 `undefined`。

### 2.8 ⚠️ Prompt cache 影响（issue 中提到的关键点）

源码 `query.ts:694`：

```typescript
effortValue: appState.effortValue
```

主 loop 用 appState 的 effort。**prompt-suggestion 等 forked agent 调用尝试覆盖 effort 但避免** —— 因为细粒度 effort 不同会**破坏 prompt cache 命中率**。

**实际机制**：API request 的 `reasoning_effort` 参数是 prompt cache key 的一部分。同一对话用 `medium` vs `high` 是两个独立 cache slot —— 反复切换会导致每次都 cache miss。

**因此 Claude 的设计权衡**：

1. **session-level 持久** —— `/effort` 改动持久整 session 不变（除非用户主动改）
2. **subagent 继承** —— spawn 子 agent 时**继承父 effort**，除非 frontmatter 显式覆盖
3. **避免 per-call 覆盖** —— prompt suggestion 等高频路径**不**覆盖 effort

---

## 三、Codex CLI 的 reasoning_effort 设计

### 3.1 levels（6 档，比 Claude 多 2 档）

源码 `codex-rs/protocol/src/openai_models.rs:43-51`：

```rust
#[strum(serialize_all = "lowercase")]
pub enum ReasoningEffort {
    None,      // 不发送 reasoning 参数
    Minimal,   // 最低
    Low,
    #[default]
    Medium,    // ← 默认
    High,
    XHigh,     // 比 Claude 'max' 更高一档（OpenAI 模型才有）
}
```

**注意**：
- `None` 表示**不发送** reasoning 字段（不是 effort=0）—— 适用于不支持 reasoning 的模型
- `Default = Medium`（不像 Claude `undefined → high`）

### 3.2 优先级链

源码 `codex-rs/core/src/config/mod.rs:2575-2580`：

```rust
model_reasoning_effort: config_profile
    .model_reasoning_effort           // 当前 profile 优先
    .or(cfg.model_reasoning_effort),  // 否则全局 config
```

**3 层结构**：

```
spawn_agent reasoning_effort 参数 (per-call override)
    ↓
config_profile.model_reasoning_effort （profile 级，类似环境切换）
    ↓
cfg.model_reasoning_effort（全局 config 默认）
```

### 3.3 配置入口

| 层级 | 机制 | 源码 |
|---|---|---|
| **TOML config** | `model_reasoning_effort = "medium"` | `codex-rs/core/src/config/mod.rs:595` |
| **Plan 模式专用** | `plan_mode_reasoning_effort = "high"` | `codex-rs/core/src/config/mod.rs:602` |
| **CLI 临时 override** | `codex -c model_reasoning_effort=high` | 通用 `-c key=value` 机制 |
| **Profile 切换** | `config_profile.model_reasoning_effort` | `codex-rs/core/src/config/mod.rs:2575-2577` |
| **Agent toml** | 内置 agent 的 `.toml` 含 `model_reasoning_effort = "low"` | 例 `core/src/agent/builtins/awaiter.toml:2` |
| **Spawn agent override** | `spawn_agent` tool 参数 `reasoning_effort` | `codex-rs/tools/src/agent_tool.rs:539, 572` |
| **Multi-agent** | `multi_agents_common.rs:317-331` 主动写入 sub config | 见源码 |

### 3.4 Plan 模式专用配置（Codex 独有）

源码 `codex-rs/core/src/config/mod.rs:596-602`：

```rust
/// Optional Plan-mode-specific reasoning effort override used by the TUI.
///
/// When unset, Plan mode uses the built-in Plan preset default (currently
/// `medium`). When explicitly set (including `none`), this overrides the
/// Plan preset. The `none` value means "no reasoning" (not "inherit the
/// global default").
pub plan_mode_reasoning_effort: Option<ReasoningEffort>,
```

**关键**：
- Plan mode 默认 `medium`（preset），但用户可单独设置
- `None` 是**显式值**（不发送 reasoning 参数），不等于"未设置走全局默认"
- Claude Code **没有** Plan-mode 专用 effort 配置（统一走 session effort）

### 3.5 模型能力 snap：`nearest_effort()`

源码 `codex-rs/protocol/src/openai_models.rs:514-532`：

```rust
fn effort_rank(effort: ReasoningEffort) -> i32 {
    match effort {
        ReasoningEffort::None => 0,
        ReasoningEffort::Minimal => 1,
        ReasoningEffort::Low => 2,
        ReasoningEffort::Medium => 3,
        ReasoningEffort::High => 4,
        ReasoningEffort::XHigh => 5,
    }
}

fn nearest_effort(target: ReasoningEffort, supported: &[ReasoningEffort]) -> ReasoningEffort {
    supported
        .iter()
        .copied()
        .min_by_key(|c| (effort_rank(*c) - target_rank).abs())
        .unwrap_or(target)
}
```

**机制**：用户配置 `xhigh` 但模型只支持 `[low, medium, high]` → 自动 snap 到 `high`（最近）。Claude 是直接降级 `max → high` 单条规则，Codex 是通用 nearest neighbor。

### 3.6 spawn_agent 工具的 per-call override

源码 `codex-rs/tools/src/agent_tool.rs:539-541`：

```rust
"reasoning_effort".to_string(),
"Optional reasoning effort override for the new agent. Replaces the inherited reasoning effort."
```

**与 Claude 区别**：Codex 主动鼓励 spawn_agent 时按需覆盖（不担心 cache 影响）。可能因为：
- Codex 走 OpenAI Responses API，cache 行为不同
- spawn 子 agent 本身就是新 conversation，cache 无重叠

### 3.7 内置 agent 的 effort 声明

`codex-rs/core/src/agent/builtins/awaiter.toml`:

```toml
background_terminal_max_timeout = 3600000
model_reasoning_effort = "low"
developer_instructions = """You are an awaiter..."""
```

`awaiter` 是 polling-only agent（等命令完成），不需要复杂推理 → 显式 `low`。这种**任务专属 effort 配置**类似 Claude 的 skill frontmatter `effort`，但 Codex 是 toml 文件级而非 frontmatter。

### 3.8 ⚠️ Cache 行为（待源码验证）

Codex 走 OpenAI Responses API。从源码看，Codex 在 `multi_agents_common.rs:317-331` 主动注入 `reasoning_effort` 到 sub config，**不像 Claude 那样规避**。这暗示 Codex 团队**判定 cache 影响可接受**或采用了不同 cache 策略。

**待补充**：需要进一步源码核对 OpenAI Responses API 的 cache key 是否含 `reasoning_effort`。

---

## 四、设计差异汇总（双向对比表）

| 维度 | Claude Code | Codex CLI | 差异分析 |
|---|---|---|---|
| **levels 数量** | 4 (`low/medium/high/max`) | 6 (`none/minimal/low/medium/high/xhigh`) | Codex 更细，含"不发送" 显式值 |
| **default** | `undefined`（→ 'high'）+ Opus 4.6 + Pro = 'medium' | `Medium` 默认 | Claude 由 subscription tier 调；Codex 静态 |
| **CLI flag** | ✓ `--effort` | ✗ 用 `-c` | Claude UX 更直 |
| **Slash command** | ✓ `/effort` | ✗ | Claude 交互式优势 |
| **Env var** | ✓ `CLAUDE_CODE_EFFORT_LEVEL` 含 `unset`/`auto` | ✗ | Claude 灵活 |
| **Persisted settings** | ✓ settings.json `effortLevel`（max 不持久）| ✓ TOML `model_reasoning_effort` | 同等 |
| **Plan mode 专用** | ✗ | ✓ `plan_mode_reasoning_effort` | Codex 独有 |
| **Profile 切换** | ✗（统一 settings）| ✓ `config_profile` | Codex 独有，多环境/多 model 切换 |
| **Per-agent toml** | — | ✓ 内置 agent 含 effort | Codex 路径 |
| **Frontmatter 声明** | ✓ skill / subagent | ✗ | Claude 路径 |
| **per-call spawn override** | ⚠️ 不鼓励（cache 影响）| ✓ spawn_agent 参数 | 设计哲学差异 |
| **Numeric effort** | ✓ ANT-only | ✗ | Claude 灵活但仅内部用 |
| **Model capability check** | ✓ `modelSupportsEffort` 白/黑名单 | ✓ `nearest_effort()` snap | Codex 通用化 |
| **Max-tier 限制** | ✓ `max` 仅 Opus 4.6 | ⚠️ XHigh 由模型 catalog 控制 | 不同模型生态 |

---

## 五、Cache 命中率影响分析

> Issue #130 特别提到："prompt suggestion 曾尝试设置 `effort: 'low'`，但因影响 prompt cache 命中率，最终避免覆盖 effortValue"

### 5.1 Claude Code 的 Cache 影响

源码 `query.ts:694`：

```typescript
effortValue: appState.effortValue  // 主 loop 用 appState
```

**机制猜测**（未在源码中找到 cache key 直接拼接 effort 的代码，但 issue 已确认实际行为）：

- Anthropic API 把 `reasoning_effort` 纳入 prompt cache key
- 同一 conversation 用 `medium` vs `high` 视为两条独立 cache 链
- 反复切换 → 每次 cache miss → token 成本爆炸

**Claude 的应对**：
1. session-scoped 持久（`/effort` 设置后整 session 不变）
2. 主 loop + subagent 默认继承
3. 高频路径（prompt suggestion 等）**禁止覆盖**

### 5.2 Codex CLI 的 Cache 行为

源码暗示 Codex **不那么规避**：

- `multi_agents_common.rs:317-331` 在 spawn agent 时主动写入 effort
- `spawn_agent` tool 暴露 `reasoning_effort` 参数

**可能原因**：
- OpenAI Responses API 的 cache 策略与 Anthropic Messages API 不同
- spawn agent 本身就是独立 conversation context（无 cache 重叠）

**待验证**：需要核对 OpenAI Responses API 文档中 cache key 是否含 `reasoning_effort`。

### 5.3 启示

**对实施 reasoning effort 的项目**：

1. **优先 session-level 持久** —— 用户体验稳定 + cache 友好
2. **subagent spawn 时谨慎覆盖** —— 仅在子 agent 是独立 conversation 时安全
3. **同一 turn 内禁止 effort 切换** —— 避免破坏 cache 链
4. **测试 cache hit rate** —— 设计 dashboard 监控 effort 切换对 token cost 的影响

---

## 六、对 Qwen Code 的设计启发

> ⚠️ 以下是**设计建议**，非"已实现能力"。Qwen Code 当前**没有** reasoning effort 控制。

### 6.1 现状审计

```bash
cd /root/git/qwen-code
grep -rn "reasoning_effort\|effortLevel\|EFFORT" packages/ 2>/dev/null | grep -v node_modules | grep -v dist | head
```

**结果**：Qwen Code 当前**不识别** `reasoning_effort` 参数（无源码引用）。Qwen3 系列的"thinking 控制"目前是 `enable_thinking` 二元 + `thinking_budget` 数值，与 OpenAI/Anthropic 的 `reasoning_effort` 枚举不同。

### 6.2 Phase 1：Codex 风格（最简，~150 行）

先采用 Codex 模型 —— 配置文件 + plan-mode 特例：

```jsonc
// .qwen/settings.json
{
  "reasoning": {
    "effort": "medium",          // 全局默认
    "planModeEffort": "high"     // Plan 模式专用
  }
}
```

**支持值**：可对齐 OpenAI 6 档（`none / minimal / low / medium / high / xhigh`）或 Anthropic 4 档。建议先做 4 档兼容（与 Qwen3 thinking 档位映射）：

```typescript
// 概念性 mapping（需源码验证 Qwen3 的实际 thinking_budget 阈值）
'low'    → enable_thinking: true,  thinking_budget: 1024
'medium' → enable_thinking: true,  thinking_budget: 8192
'high'   → enable_thinking: true,  thinking_budget: 32768
'none'   → enable_thinking: false
```

### 6.3 Phase 2：Claude 风格交互（~80 行）

加入用户交互层：

```bash
qwen --effort medium                  # CLI flag
/effort high                          # slash command
QWEN_EFFORT_LEVEL=low qwen           # env var
/status                               # 显示当前 effort
```

### 6.4 Phase 3：Agent 级（~120 行）

类似 Claude skill/subagent frontmatter：

```yaml
---
name: code-reviewer
effort: high      # ← 此 agent 用 high effort
---
```

或类似 Codex agent toml：

```toml
# .qwen/agents/code-reviewer.toml
model_reasoning_effort = "high"
```

### 6.5 ⚠️ 必须注意 Cache 影响

**关键警告**（来自 Claude Code prompt-suggestion 经验）：

- **不要** per-tool / per-call 细粒度切换 effort
- **不要** 在主 loop 中改 effort（除非是用户显式 `/effort`）
- **subagent spawn 时 override** 是相对安全的（独立 conversation context）

**建议**：实施前先**测量**当前 prompt cache hit rate 作为 baseline，加入 effort 切换后对比。

### 6.6 推荐实施顺序

| Phase | 工作量 | 验收 |
|---|:-:|---|
| **P0** Phase 1（Codex 风格全局 + plan-mode）| ~150 行 / 1.5 天 | settings.json 可读 + Qwen3 API 调用带 thinking_budget |
| **P1** Phase 2（CLI flag + slash + env + /status）| ~80 行 / 1 天 | 4 个用户入口 |
| **P2** Phase 3（agent frontmatter）| ~120 行 / 1.5 天 | subagent 继承 + 覆盖 |
| **P3** Cache 监控仪表盘 | ~100 行 / 1 天 | prompt cache hit rate 追踪 |

**总计 ~450 行 / 5 天**。

### 6.7 与现有 codeagents item 关系

- 与 [api-params-deep-dive.md](./api-params-deep-dive.md) **同 family**（API 参数维度）—— 本文聚焦 reasoning_effort 单点
- 不在现有 [改进报告](./qwen-code-improvement-report.md) 275 项里 —— **新方向**，建议创建独立 item 追踪
- 与 [token-estimation-deep-dive.md](./token-estimation-deep-dive.md) 配套 —— effort 高 → token 多 → 估算需调整

---

## 七、源码引用索引

### Claude Code

| 文件 | 行 | 功能 |
|---|---|---|
| `utils/effort.ts:13-18` | EFFORT_LEVELS 定义 4 档 |
| `utils/effort.ts:23-49` | `modelSupportsEffort` 模型支持检测 |
| `utils/effort.ts:53-65` | `modelSupportsMaxEffort` Opus 4.6 限制 |
| `utils/effort.ts:71-92` | `parseEffortValue` 解析（含 ANT 数值）|
| `utils/effort.ts:95-105` | `toPersistableEffort` `max` 不持久（除 ant）|
| `utils/effort.ts:107-111` | `getInitialEffortSetting` 从 settings 读 |
| `utils/effort.ts:136-142` | `getEffortEnvOverride` 含 unset/auto |
| `utils/effort.ts:152-172` | `resolveAppliedEffort` 优先级链 |
| `utils/effort.ts:279-329` | `getDefaultEffortForModel` 默认值 + subscription tier |
| `commands/effort/effort.tsx` | `/effort` slash command |
| `main.tsx:993` | `--effort <level>` CLI flag |
| `main.tsx:54, 2633, 3024` | `parseEffortValue(options.effort)` 入口 |
| `query.ts:694` | 主 loop 用 `appState.effortValue` |
| `skills/loadSkillsDir.ts:205, 230` | skill frontmatter `effort` 解析 |

### Codex CLI

| 文件 | 行 | 功能 |
|---|---|---|
| `codex-rs/protocol/src/openai_models.rs:43-51` | `ReasoningEffort` enum 6 档 |
| `codex-rs/protocol/src/openai_models.rs:514-532` | `nearest_effort` snap to model capability |
| `codex-rs/core/src/config/mod.rs:595` | `model_reasoning_effort` 全局 |
| `codex-rs/core/src/config/mod.rs:602` | `plan_mode_reasoning_effort` Plan 模式专用 |
| `codex-rs/core/src/config/mod.rs:2575-2580` | profile 优先 → cfg fallback |
| `codex-rs/core/src/tools/handlers/multi_agents_common.rs:317-331` | spawn agent 时注入 |
| `codex-rs/core/src/session/review.rs:87` | review session 用 per-turn config |
| `codex-rs/core/src/agent/builtins/awaiter.toml:2` | 内置 agent 的 toml `model_reasoning_effort = "low"` |
| `codex-rs/tools/src/agent_tool.rs:539, 572` | `spawn_agent` tool 的 `reasoning_effort` 参数 |
| `codex-rs/tui/src/slash_command.rs:102` | `/model` 描述含"and reasoning effort"（无独立 `/effort`）|

---

## 八、验收清单（对应 Issue #130）

- [x] 新增 reasoning effort deep-dive 文档（本文件）
- [x] 明确区分 Claude Code 与 Codex CLI 的实现层级（§2 / §3 / §4）
- [x] 每个关键结论都有源码分析、行号引用（§7 索引）
- [x] 标注未验证项（§3.8 cache 行为待源码核对；§6.2 Qwen3 thinking_budget 阈值待验证）
- [x] Qwen Code 建议明确为"设计启发"（§6 全节）
- [ ] 补充现有相关文档的交叉引用（README + improvement report header 待更新）

---

## 九、相关文档

- [API 参数与重试策略对比](./api-params-deep-dive.md)
- [Token 估算策略](./token-estimation-deep-dive.md)
- [Codex CLI 对标改进报告](./qwen-code-codex-improvements.md)
- [Claude Code 命令清单](../tools/claude-code/02-commands.md)
- [Claude Code 多 Agent](../tools/claude-code/09-multi-agent.md)
- [Claude Code Prompt Suggestions](../tools/claude-code/10-prompt-suggestions.md)
- [Codex CLI 命令清单](../tools/codex-cli/02-commands.md)
- [Codex CLI Evidence](../tools/codex-cli/EVIDENCE.md)

---

## 十、修订历史

- **2026-04-29 v1**：初版，处理 [Issue #130](https://github.com/wenshao/codeagents/issues/130)。源码核对 Claude Code `utils/effort.ts` (329 行) + Codex `codex-rs/protocol/src/openai_models.rs` + `core/src/config/mod.rs`。

---

**最后更新**：2026-04-29
**Issue**：[#130](https://github.com/wenshao/codeagents/issues/130)
**审计提示**：本文经一轮源码核对，引用行号已与 2026-04-29 当前 source 对齐。如发现源码 drift，请提 issue 反馈。
