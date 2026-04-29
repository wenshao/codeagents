# Reasoning Effort 设计对比：Claude Code vs Codex CLI

> 处理 [Issue #130](https://github.com/wenshao/codeagents/issues/130)。逐源码对比 `reasoning_effort` / `effort` 在两家的设计差异、cache 影响、对 Qwen Code 的启发。
>
> **数据**：Claude `utils/effort.ts` 329 行 + `commands/effort/` ~80 行 · Codex `protocol/src/openai_models.rs` + `core/src/config/mod.rs` + `tools/src/agent_tool.rs`

---

## 一、TL;DR

| 维度 | Claude Code | Codex CLI |
|---|---|---|
| **levels** | 4：`low / medium / high / max` | 6：`none / minimal / low / medium / high / xhigh` |
| **default** | `undefined`（→API 解析为 high）；Opus 4.6 + Pro 默认 `medium` | `Medium`（静态）|
| **CLI flag** | `--effort <level>` | ✗（用 `-c model_reasoning_effort=...`）|
| **Slash 命令** | ✓ `/effort` | ✗（合并在 `/model`）|
| **环境变量** | ✓ `CLAUDE_CODE_EFFORT_LEVEL`（含 `unset`/`auto`）| ✗ |
| **持久化配置** | ✓ settings.json `effortLevel` | ✓ TOML `model_reasoning_effort` |
| **Plan 模式专用** | ✗ | ✓ `plan_mode_reasoning_effort` |
| **Profile 切换** | ✗ | ✓ `config_profile.model_reasoning_effort` |
| **Agent 级** | ✓ skill / subagent **frontmatter** `effort` | ✓ agent **TOML** 文件 `model_reasoning_effort` |
| **per-call override** | ⚠️ 不鼓励（cache 影响）| ✓ `spawn_agent` 工具暴露 `reasoning_effort` 参数 |
| **数值 effort** | ✓ ANT-only | ✗ |
| **模型适配** | 白/黑名单（`modelSupportsEffort`）| `nearest_effort()` snap 到最近档 |
| **设计哲学** | **session-level 持久 + cache-friendly 优先** | **配置文件驱动 + 模式分支 + spawn 时灵活覆盖** |

---

## 二、关键差异深度分析

### 2.1 Levels 与默认值

**Claude（4 档）**：

```typescript
// utils/effort.ts:13-18
EFFORT_LEVELS = ['low', 'medium', 'high', 'max']
```

- `'max'` **仅 Opus 4.6 支持**（其他模型从 `max` 自动降级到 `high`，line 162-164）
- `'max'` 不持久化到 `settings.json`（除 `USER_TYPE === 'ant'`）—— 避免 session-only 选择泄漏到下次启动
- 默认值由 **subscription tier** 决定：Opus 4.6 + Pro/Max/Team + `tengu_grey_step2` flag → `medium`；其他 → `undefined`（API 解析为 high）

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

---

### 2.2 用户入口（Claude 4 层 vs Codex 主走配置）

**Claude 4 层入口**：

| 层 | 机制 | 持久 | 源码 |
|---|---|:-:|---|
| CLI | `--effort low\|medium\|high\|max` | ✗ | `main.tsx:993` |
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

### 2.5 ⚠️ Cache 影响（Issue 核心点）

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

## 三、对 Qwen Code 的设计启发

> ⚠️ 以下是**设计建议**，非已实现能力。Qwen Code 当前**无** `reasoning_effort` 控制（`grep -rn "reasoning_effort\|EFFORT" packages/` 无源码引用）。

### 3.1 推荐路线图（3 阶段）

| Phase | 风格 | 范围 | 工作量 | 验收 |
|:-:|---|---|:-:|---|
| **P0** | Codex 风格 | 全局配置 + Plan 模式专用 | ~150 行 / 1.5 天 | settings 可读 + Qwen3 API 带 thinking_budget |
| **P1** | Claude 风格 | CLI flag + slash + env + `/status` 显示 | ~80 行 / 1 天 | 4 个用户入口齐全 |
| **P2** | Agent 级 | subagent / skill frontmatter | ~120 行 / 1.5 天 | spawn 时继承 + override 工作 |
| **P3** | Cache 监控 | hit rate dashboard | ~100 行 / 1 天 | 切换前后 baseline 对比 |

**总 ~450 行 / 5 天**。建议先 P0 + P3（先建立度量再加复杂度）。

### 3.2 与 Qwen3 thinking 的映射

Qwen3 系列已有 `enable_thinking` 二元 + `thinking_budget` 数值。建议 4 档映射（**实际阈值待源码核对**）：

```typescript
'low'    → enable_thinking: true,  thinking_budget: 1024
'medium' → enable_thinking: true,  thinking_budget: 8192
'high'   → enable_thinking: true,  thinking_budget: 32768
'none'   → enable_thinking: false
```

### 3.3 ⚠️ Cache 影响警告

实施前**必读 §2.5**。基本原则：

1. session-level 持久（用户显式改才变）
2. 不在主 loop 中改 effort
3. subagent spawn 时 override **可以**（独立 conversation context）
4. 实施前测量 prompt cache hit rate 作为 baseline

---

## 四、附录 A：源码引用索引

### Claude Code

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

### Codex CLI

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

---

## 五、附录 B：相关文档

- [Codex CLI 对标改进](./qwen-code-codex-improvements.md)
- [API 参数与重试策略对比](./api-params-deep-dive.md)
- [Token 估算策略](./token-estimation-deep-dive.md)
- [Claude Code 命令清单](../tools/claude-code/02-commands.md) · [多 Agent](../tools/claude-code/09-multi-agent.md) · [Prompt Suggestions](../tools/claude-code/10-prompt-suggestions.md)
- [Codex CLI 命令清单](../tools/codex-cli/02-commands.md) · [Evidence](../tools/codex-cli/EVIDENCE.md)

---

**最后更新**：2026-04-29 · **Issue**：[#130](https://github.com/wenshao/codeagents/issues/130)
