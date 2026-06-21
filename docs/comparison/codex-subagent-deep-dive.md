# Codex SubAgent / 多代理 Deep-Dive（对标 Claude / Qwen subagent）

> OpenAI **Codex** 有没有"一个 agent 派生 / 委托子代理"的能力？怎么定义、怎么调度、子代理继承什么上下文？本文以本地 Rust 源码（`/root/git/codex` @ `6f5dd7b` 2026-06-21）+ 官方文档 + 项目反编译二进制三方核验，并与 [Claude Fork Subagent](./fork-subagent-deep-dive.md) / Qwen subagent 对比。
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md) · [Deep-Dive 索引](./deep-dive-index.md)

> **一句话结论**：Codex **有一套已发布、默认开启**的 CLI 子代理系统（内部 `Feature::Collab` / "multi_agent" V1）——模型按用户**显式请求**并行 fan-out 多个专用子代理、自动汇总；用户用 **TOML 文件**定义具名 agent（与 Claude/Qwen 的 Markdown 不同）。另有一个 **under-development 的 `multi_agent_v2` 重写**（未发布、未文档化），以及云端独立的 **best-of-N**（`--attempts 1–4`）。

---

## 一、CLI 子代理系统：已发布、默认开启

```rust
// 源码: codex-rs/features/src/lib.rs:1021-1024
FeatureSpec {
    id: Feature::Collab,
    key: "multi_agent",
    stage: Stage::Stable,       // ← 稳定
    default_enabled: true,       // ← 默认开启
},
```

- **触发 = 模型调用的 spawn 工具，仅在用户显式要求时**——不是 slash 命令、不靠 config 开关。官方："Codex only spawns subagents when you explicitly ask it to."（[subagents](https://developers.openai.com/codex/subagents)）
- **编排自动 fan-out / fan-in**：spawn N 个子代理 → 可发 follow-up → 等齐全部结果 → 汇总成一条回复。
- **编排归工具 handler，不是模型自主决定何时派生**：

> 源码 `codex-rs/core/src/agent/role.rs:6`："It does not decide when to spawn a sub-agent or which role to use; the multi-agent tool handler owns that orchestration."

- 源码落点：`core/src/agent/`（`control/spawn`、`registry`、`role`、`agent_resolver`、`builtins`、`status`）+ `core/src/tools/handlers/multi_agents.rs`。并发由 `registry.rs` 的 `max_threads` 限制（超限 `CodexErr::AgentLimitReached`）。
- **一个子能力仍实验性**：`spawn_agents_on_csv`（按 CSV 每行 fan-out 一个 agent + `max_concurrency`）——官方标 "experimental and may change"。
- **成本提示**：官方明确每个子代理各自跑模型 + 工具，"subagent workflows consume more tokens than comparable single-agent runs"（[cli/features](https://developers.openai.com/codex/cli/features)）。

---

## 二、Agent 定义 = TOML（与 Claude/Qwen 的 Markdown 最大区别）

用户用 **TOML 文件**定义具名自定义 agent：

| 项 | 内容 |
|----|------|
| 位置 | `~/.codex/agents/*.toml`（个人）或 `<project>/.codex/agents/*.toml`（项目），一文件一 agent |
| 必填 | `name` / `description` / `developer_instructions` |
| 可选 | `model` / `model_reasoning_effort` / `sandbox_mode` / `mcp_servers` / `skills.config` / `nickname_candidates` |
| 全局上限 | `agents.max_threads`（`config.toml`），不设时默认 **6** |

```toml
# 示例（官方 docs）
name = "reviewer"
description = "PR reviewer focused on correctness, security..."
developer_instructions = "Review code like an owner..."
model = "gpt-5.4"
sandbox_mode = "read-only"
```

> 源码 `codex-rs/core/src/agent/role.rs:1-5`：内部称 **"agent roles"**——"Roles are selected at spawn time and are loaded with the same config machinery as `config.toml`… inserts the role as a **high-precedence layer**"。即 agent 定义被当作**高优先级配置层叠加**到 session config 上，而非一段 prompt 文件——这是与 Claude（Markdown + YAML frontmatter）/ Qwen（subagent config）的根本设计差异。`agent_type` 在 spawn 时选 role，缺省 role 名为 `"default"`。

---

## 三、`/agent` 命令 = 线程导航器，**不是** spawner

```rust
// 源码: codex-rs/tui/src/slash_command.rs:123
SlashCommand::Agent | SlashCommand::MultiAgents => "switch the active agent thread"
```

`/agent`（与 `/multi-agents`）作用是**切换 / 检视已 spawn 的子代理线程**：Enter 弹出线程 picker → 选一个切过去查看或续作；也可在批准/拒绝某子代理的审批请求前先打开它的线程（[cli/slash-commands](https://developers.openai.com/codex/cli/slash-commands)）。**创建** agent 是 §一 的模型工具，`/agent` 不创建。

---

## 四、上下文继承：子代理**继承**父级（与 Claude / Qwen 不同）

Codex 子代理**继承**父 turn 的 live 运行时覆盖，而非隔离 / 从零：

- 官方："Codex reapplies the parent turn's live runtime overrides when it spawns a child… such as `/permissions` changes or `--yolo`, even if the selected custom agent file sets different defaults."（[subagents](https://developers.openai.com/codex/subagents)）
- 源码 `core/src/agent/control/spawn.rs`：`SpawnAgentThreadInheritance` 携带 `inherited_environments` / `inherited_exec_policy` / `inherited_multi_agent_mode` + 可选 `fork_mode`；V2 测试断言 child 继承父 developer context（`spawned_multi_agent_v2_child_inherits_parent_developer_context`）。
- **优先级**：父级 live override > agent role 文件默认。即 role 文件可设额外默认，但运行时 `/permissions`/`--yolo` 等覆盖仍下传并优先。
- **per-agent 权限**：每个 agent 可设 `sandbox_mode`（如 `read-only`/`workspace-write`）+ 自己的 `mcp_servers`；否则**继承父级当前 sandbox 策略**。
- **递归防护**：官方称嵌套深度受限（默认约 1）防失控 fan-out。

> 对照：**Claude** subagent 偏隔离上下文窗口（返回浓缩摘要）；**Qwen** 常规 subagent 从零起（`fork` 例外才继承）。**Codex** 则默认**选择性继承**父运行时/权限 + developer context——三家在"子代理拿到多少父上下文"上取向不同。

---

## 五、`multi_agent_v2`：under-development 重写（未发布）

```rust
// 源码: codex-rs/features/src/lib.rs:1027-1030
FeatureSpec {
    id: Feature::MultiAgentV2,
    key: "multi_agent_v2",
    stage: Stage::UnderDevelopment,   // ← 开发中
    default_enabled: false,            // ← 默认关
},
```

- 启用即警告（测试断言）："Under-development features… incomplete and may behave unpredictably."
- 版本解析（`config/mod.rs`）：`multi_agent_v2` 开 → `MultiAgentVersion::V2`；否则 `Feature::Collab`（默认开）→ `V1`。**今天发布的子代理 = V1**；V2 是 opt-in 且不完整。
- V2 有独立 handler 集 `core/src/tools/handlers/multi_agents_v2/`（`spawn` / `send_message` / `followup_task` / `wait` / `interrupt_agent` / `list_agents` / `message_tool`）+ 更细 config（`max_concurrent_threads_per_session`、wait-timeout、`tool_namespace`、`hide_spawn_agent_metadata` 等），且禁止与 `agents.max_threads` 同设。另有独立 flag `MultiAgentMode`（"per-turn multi-agent mode selection"）。
- **官方文档无任何提及 V1/V2/multi_agent_v2** → 内部未发布，不应作为用户功能宣传。

---

## 六、`child_agents_md` 已移除 + AGENTS.md 层级

- **`child_agents_md` 已从当前源码移除**（当前 `codex-rs` grep `child_agents_md`/`hierarchical_agents` 0 命中）。曾名 `hierarchical_agents` → 改名 `child_agents_md` → 移除（web 研究指向 commit `#28993` "Remove child AGENTS.md prompt experiment"）。
  > ⚠️ 项目 [codex-cli EVIDENCE.md](../tools/codex-cli/EVIDENCE.md) 是 v0.116.0（2026-03）二进制转储，仍含 `child_agents_md under development`——**已过时**，以当前源码为准。
- **AGENTS.md ≠ agent 定义**：它是自定义**指令 / 上下文**（类 CLAUDE.md/QWEN.md），不是子代理定义。源码 `core/src/agents_md.rs`：从 git root **向下**逐级收集 `AGENTS.md`（`.override.md` 优先），root-first 拼接、就近覆盖；叠加 host 提供的 user 指令。

---

## 七、云端 best-of-N（与 CLI 子代理无关的另一条并行线）

```
codex cloud exec --env ENV_ID --attempts N      # N ∈ [1,4]
```

- 同一任务**并行生成至多 4 个解**，开发者**人工挑选**最佳——**无自动 LLM-judge / 排序**。
- 源码 `codex-rs/cloud-tasks/src/cli.rs` 的 `parse_attempts` 越界报错 "attempts must be an integer between 1 and 4"；内部字段 `best_of_n`；TUI 在 Ctrl+N 暴露 attempts。
- Changelog **2025-06-13**："generate multiple responses simultaneously for a single task"（[changelog](https://developers.openai.com/codex/changelog)）。
- **仅云端**（`codex cloud exec`），非交互 CLI；交互 CLI 的并行是 §一 的子代理。另有"并行**不同**任务"（各跑隔离云环境 / worktree）——与 best-of-N 是两回事。

---

## 八、三方对比：Codex vs Claude Code vs Qwen Code

| 维度 | **Codex（CLI V1/Collab）** | **Claude Code** | **Qwen Code** |
|------|------|------|------|
| spawn 机制 | 模型工具，**仅显式请求** + 自动 fan-out/汇总 | `Task`/`Agent` 工具（模型自主决定委托）| `subagent_type` 参数 |
| 定义格式 | **TOML**（`~/.codex/agents/`，配置层）| **Markdown** `.claude/agents/*.md`（YAML frontmatter）| subagent config 文件 |
| 关键字段 | `name`/`description`/`developer_instructions`/`model`/`model_reasoning_effort`/`sandbox_mode`/`mcp_servers` | name/description/tools/model | name/description/tools/model |
| 上下文继承 | **选择性继承**父运行时/权限 + developer context | 偏隔离（fresh context，返回摘要）| 从零起（`fork` 例外才继承）|
| per-agent 权限 | `sandbox_mode` + `mcp_servers`，否则继承父 sandbox | per-agent tool allowlist | per-agent tool scoping |
| 默认并发 | `agents.max_threads` 默认 **6** | 并发 Task agents | 并发 subagents |
| `/agent` 命令 | **线程导航器**（切换/检视，不创建）| —（Task 工具创建）| —（agent 工具创建）|
| 指令层级 | `AGENTS.md` 链（root→cwd，`.override.md`）| `CLAUDE.md` 层级 | `QWEN.md`/`AGENTS.md` |
| 云端 best-of-N | **`codex cloud exec --attempts 1–4`（独家，人工挑选）** | 无第一方云 best-of-N | 无 |
| under-dev 重写 | `multi_agent_v2`（`UnderDevelopment`，未文档化）| — | — |

**关键差异**：① Codex agent 是 **TOML 配置层**，非 Markdown prompt 文件；② Codex 子代理**继承**父 live 权限/上下文覆盖（vs Claude 隔离 / Qwen 从零）；③ Codex 独家**云端 best-of-N**（至多 4 解人工挑）；④ Codex 设计上**显式 spawn**（模型不自作主张派生）。

---

## 九、源码验证说明

> 本项目要求闭源/半闭源声明须有 EVIDENCE 或官方文档 URL 支撑。Codex 子代理可在**本地 Rust 源码直接钉死**，云端 best-of-N 以源码 + changelog 为准。

- **本地源码钉死**（`/root/git/codex` @ `6f5dd7b` 2026-06-21）：`Feature::Collab`/"multi_agent" = `Stable/default true`、`MultiAgentV2` = `UnderDevelopment/false`（`features/src/lib.rs:1021,1027`）；agent roles = 高优先级 TOML 配置层（`agent/role.rs:1-6`）；`max_threads` 限并发（`agent/registry.rs:82-86`）；`/agent` = "switch the active agent thread"（`tui/src/slash_command.rs:123`）；`child_agents_md` 已移除（grep 0 命中）；best-of-N `--attempts 1–4`（`cloud-tasks/src/cli.rs`）；AGENTS.md root-down 层级（`core/src/agents_md.rs`）。
- **官方文档**（spawn 语义、TOML 字段/位置、max_threads 默认 6、上下文继承、best-of-N changelog、AGENTS.md guide）：见正文各 URL。
- **web 研究但本地仅核实结果**：`child_agents_md` 移除 PR `#28993`——本地仅能核实"当前源码无该 flag"，PR# 本身以 web 研究为准。
- **过时证据提醒**：项目 codex-cli EVIDENCE.md（v0.116.0，2026-03）仍列 `child_agents_md`，已过时。
- **不确定项**：V1 子代理系统与 `/agent` 的确切上线日期（无 dated changelog 条目）；best-of-N 无自动排序（人工挑选，官方未述自动 judge）。

---

## 十、启示

1. **三种"子代理上下文"哲学**：Codex = **继承父运行时/权限**（轻量、连续，适合"接着我现在的环境去并行干"）；Claude = **隔离 + 返回摘要**（防上下文污染）；Qwen = **从零 / fork 二选一**。做编排设计时，"子代理拿到多少父上下文"是第一性选择——Codex 的继承模型让"权限/sandbox 一致下传"很自然，但也意味着子代理不是干净沙盒。
2. **TOML 配置层 vs Markdown prompt**：Codex 把 agent 当**配置层叠加**（可设 model/effort/sandbox/mcp），表达力偏"运行时参数"；Claude/Qwen 的 Markdown 偏"角色 prompt + 工具白名单"。Qwen 若要增强 subagent 定义，可参考 Codex 的 per-agent `sandbox_mode`/`mcp_servers`/`model_reasoning_effort` 字段粒度。
3. **云端 best-of-N 是 Codex 独家差异点**：`--attempts 1–4` 人工挑选——对"探索多解"场景有价值；Claude/Qwen 均无第一方对标（Qwen 的 Workflow 可脚本化 N 路 agent，但需自写编排 + 无云端隔离 best-of-N 产品化）。
4. **`/agent` 作为线程导航器**值得借鉴：当并行子代理多时，一个"切换/检视子代理线程 + 审批前打开"的 UI，比纯消息流更可控——对标本报告 [Coordinator 协调器面板](./subagent-display-deep-dive.md) 思路。

---

## 证据来源

| 来源 | 类型 | 获取方式 |
|------|------|---------|
| `/root/git/codex` @ `6f5dd7b`（2026-06-21）| Rust 源码（feature/role/registry/slash/agents_md/cloud-tasks 直接钉死）| 本地 grep + Read |
| [developers.openai.com/codex/subagents](https://developers.openai.com/codex/subagents) | 官方文档（spawn 语义 / TOML 定义 / 继承 / max_threads）| WebFetch |
| [developers.openai.com/codex/cli/slash-commands](https://developers.openai.com/codex/cli/slash-commands) | 官方（`/agent` 行为）| WebFetch |
| [developers.openai.com/codex/cli/features](https://developers.openai.com/codex/cli/features) · [/cloud](https://developers.openai.com/codex/cloud) | 官方（成本提示 / 云并行）| WebFetch |
| [developers.openai.com/codex/guides/agents-md](https://developers.openai.com/codex/guides/agents-md) | 官方（AGENTS.md 层级）| WebFetch |
| [developers.openai.com/codex/changelog](https://developers.openai.com/codex/changelog) | 官方（best-of-N 2025-06-13）| WebFetch |
| [codex-cli EVIDENCE.md](../tools/codex-cli/EVIDENCE.md) | v0.116.0 二进制（部分已过时，标注用）| 本仓库二进制分析 |
| `#28993`（child_agents_md 移除）| web 研究（本地仅核实结果）| GitHub |

> **免责声明**：Codex 多代理演进快（V2 在途、云端功能频繁更新），本文官方文档部分截至 2026-06-21；feature flag 与源码细节以本地 `6f5dd7b` 为准，后续版本可能变更。
