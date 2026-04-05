# AI 编程 Code Agent 对比

> 基于源码分析和二进制反编译的 18 款 AI 编程 Code Agent 全面对比 | 120+ 文件 | 36,000+ 行 | 21 篇 Deep-Dive | 9 个 EVIDENCE.md

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**👉 [一页总结（选型速查）](./docs/SUMMARY.md)** — 给没时间看全部文档的人

> **维护说明**：高频变化的数据（Stars、下载量、价格、验证日期）开始统一沉淀到 [`docs/data/`](./docs/data/README.md)。证据完备度与验证状态见 [`docs/evidence-index.md`](./docs/evidence-index.md)。

## 核心发现

### 源码分析纠正的"常识"

| Agent | 官方/常见说法 | 源码实际情况 |
|------|-------------|-------------|
| **Goose** | TypeScript | **Rust**（55k 行） |
| **OpenCode** | Go | **TypeScript**（Bun monorepo，v1.0+ 全面重写，Go→TS 渐进迁移完成） |
| **Kimi CLI** | TypeScript | **Python**（68.8%） |
| **Qwen Code** | 原创 | **Gemini CLI 分叉**（大幅增强） |

### 实测性能（2026-03-26 本机测量）

| Agent | 启动时间 | 安装大小 | 二进制类型 |
|-------|---------|---------|-----------|
| **Claude Code** v2.1.84 | **50ms** | 225MB | Rust ELF |
| **Copilot CLI** v1.0.10 | 72ms | 268MB | Node.js SEA |
| **Codex CLI** | 76ms | 142MB | Node.js SEA |
| **Qwen Code** v0.13.0 | 608ms | 48MB | Node.js npm |
| **Gemini CLI** v0.34.0 | 1.5s（冷启动 4s） | 509MB | Node.js npm |

> Rust 二进制（50ms）比 Node.js SEA（72ms）快 30%，比 npm 包（1.5s）快 **30 倍**。Qwen Code 作为 Gemini CLI 分叉，安装仅 48MB（上游 509MB 的 9%），启动快 2.5 倍。

### 实际采用量（汇总入口）

> 高频变化数据已集中维护在 [`docs/data/agents-metadata.json`](./docs/data/agents-metadata.json)。
>
> 当前 README 仅保留结论性摘要，详细数字、验证日期和证据状态请查看：
> - [`docs/data/agents-metadata.json`](./docs/data/agents-metadata.json)
> - [`docs/evidence-index.md`](./docs/evidence-index.md)
> - [`docs/comparison/evolution-community.md`](./docs/comparison/evolution-community.md)

- Claude Code、Codex CLI 在 npm 生态采用量领先
- Gemini CLI 社区热度高，但采用量与 Claude Code 不完全同步
- Qwen Code、Kimi CLI 在中文开发者语境下增长明显
- OpenHands、Aider 在 Python / research-oriented 场景保持稳定关注度

*数据来源：[npm Registry API](https://api.npmjs.org/)、[PyPI Stats](https://pypistats.org/)、`gh api`；具体数值请以 `docs/data/agents-metadata.json` 为准。*

---

## 30 秒选型指南

| 场景 | 推荐 | 理由 |
|------|------|------|
| **日常编码** | Claude Code 或 Aider | 最强推理 / 最好 Git 集成 |
| **免费使用** | Qwen Code 或 Gemini CLI | 1000 次/天免费 OAuth / Google 账号 |
| **多模型切换** | OpenCode、Goose 或 Qwen Code | 100+ models.dev / 58+ 提供商 / Arena 多模型竞争 |
| **VS Code 用户** | Cline 或 Continue | IDE 原生集成 / PR Checks |
| **中文开发者** | Qwen Code 或 Kimi CLI | 6 语言 UI / 月之暗面中文模型 |
| **CI/CD 自动化** | SWE-agent 或 OpenHands | 批量评估 / Docker 沙箱 |
| **安全沙箱** | Codex CLI 或 Gemini CLI | 三平台 OS 沙箱 / TOML 策略引擎 |
| **OpenAI 生态** | Codex CLI | 官方开源，GPT-5 系列 |
| **GitHub 生态** | Copilot CLI | 67 GitHub 工具，增长最快 |

---

## 快速对比表

> 高频变化数据（Stars / 下载量 / 免费层）的权威来源为 [`docs/data/agents-metadata.json`](./docs/data/agents-metadata.json)。下表 Stars 列为 **2026-03-31 快照**，按 Stars 降序排列；后续更新将通过脚本从数据层自动生成，不再手工同步。

| Agent | 开发者 | 许可证 | 语言 | Stars | 提供商 | 特色 |
|------|--------|--------|------|------|-------|------|
| [OpenCode](./docs/tools/opencode/) | Anomaly | MIT | TypeScript（Bun） | 133k | 100+ | 多客户端（TUI+Web+桌面），37 LSP |
| [Gemini CLI](./docs/tools/gemini-cli/) | Google | Apache-2.0 | TypeScript | 100k | 1 | 8 策略模型路由，TOML 策略引擎 |
| [Claude Code](./docs/tools/claude-code/) | Anthropic | 专有 | Rust | 85k | 1 | 50ms 启动，24 Hook 事件，Channels |
| [OpenHands](./docs/tools/openhands.md) | OpenHands | MIT | Python | 70k | 100+ | Docker 沙箱，三层安全，多代理 |
| [Codex CLI](./docs/tools/codex-cli/) | OpenAI | Apache-2.0 | Rust | 68k | 1 | 三平台 OS 沙箱，Cloud 远程执行 |
| [Cline](./docs/tools/cline.md) | Cline | Apache-2.0 | TypeScript | 60k | 48+ | VS Code 原生，Git Checkpoint |
| [Oh My OpenAgent](./docs/tools/oh-my-openagent.md) | code-yeongyu | SUL-1.0 | TypeScript | ~45k | 多种 | OpenCode Harness 层，7~10 Discipline Agent |
| [Aider](./docs/tools/aider/) | Paul Gauthier | GPL-3.0 | Python | 43k | 100+ | 14 编辑格式，三槽位模型，/undo |
| [Goose](./docs/tools/goose/) | Block | Apache-2.0 | Rust | 34k | 58+ | MCP 原生，11 Platform Extension，Recipe + Cron 调度 |
| [Continue](./docs/tools/continue.md) | Continue | Apache-2.0 | TypeScript | 32k | 68+ | PR Checks CI 审查，语义索引 |
| [Cursor](./docs/tools/cursor-cli.md) | Cursor | 专有 | TypeScript | ~33k | 多种 | AI 原生 IDE，Background Agent |
| [Warp](./docs/tools/warp.md) | Warp | 专有 | Rust | 26k | 多种 | GPU 渲染终端，块结构输出 |
| [Qwen Code](./docs/tools/qwen-code/) | 阿里云 | Apache-2.0 | TypeScript | 21k | 6+ | 免费 1000 次/天，Arena 多模型竞争，41 命令 |
| [SWE-agent](./docs/tools/swe-agent.md) | Princeton | MIT | Python | 19k | 100+ | SWE-bench 评估，Docker 沙箱 |
| [Copilot CLI](./docs/tools/copilot-cli/) | GitHub | 专有 | TypeScript | 10k | 多种 | 67 GitHub 工具，GitHub 生态集成 |
| [Kimi CLI](./docs/tools/kimi-cli/) | 月之暗面 | Apache-2.0 | Python | 7k | 6 | Wire 协议，D-Mail 时间回溯 |
| [Qoder CLI](./docs/tools/qoder-cli/) | QoderAI | 专有 | Go | — | 多种 | Quest 模式，Claude Code 兼容 |

---

> **基准测试**：SWE-bench 等评测数据见 [基准测试文档](./docs/benchmarks/overview.md)。本仓库聚焦 Agent 架构与功能的源码级对比，不做模型能力评测。

---

## 架构流派

| 流派 | 代表 Agent | 核心模式 |
|------|---------|---------|
| **编辑优先** | Aider | LLM 直接输出代码修改（14 种格式），需文本解析 |
| **工具调用** | Claude Code, Codex CLI, Gemini CLI, Qwen Code, OpenCode, Cline, Goose, Copilot CLI, Kimi CLI | 结构化 function calling，LLM 通过 API 返回 tool calls |
| **混合 ReAct** | SWE-agent, mini-swe-agent | 兼容 function calling（默认）与文本动作解析，文本解析是其鲜明特征 |
| **事件驱动** | OpenHands | EventStream 发布/订阅，Action/Observation 完全解耦 |

> **注 1**：许多交互式 coding agent 都可以理解为 ReAct-like 循环（reasoning → acting → observation → repeat）。上表为了可操作地分类，主要按**动作表达/编排机制**区分：function calling、文本解析、编辑格式、事件流等。
>
> **注 2**：以下 Agent 未列入上表，原因各异：
> - **Cursor、Warp、Continue、Qoder CLI**：闭源/IDE 嵌入式 Agent，具有工具系统能力（多支持 MCP），但本仓库现有证据不足以确认其使用原生 API function calling
> - **Oh My OpenAgent**：基于 OpenCode 的 Harness 层，继承工具调用架构但不直接调用 LLM API，视为「工具调用」的间接成员

## 技术栈

| 语言 | Agent | 特点 |
|------|-------|------|
| **Rust** | Claude Code, Codex CLI, Goose, Warp | 50ms 启动，内存最低 |
| **TypeScript** | Gemini CLI, Qwen Code, Cline, Continue | Ink/React TUI 成熟 |
| **TypeScript（Bun）** | OpenCode | TypeScript（Bun）后端 + SolidJS TUI（v1.0 前 Go，已全面重写） |
| **Python** | Aider, SWE-agent, OpenHands, Kimi CLI | LiteLLM 100+ 模型 |

---

## 文档导航

<details><summary><b>Agent 详情（源码级）— 8 个专题</b></summary>

- **[Agent 索引](./docs/tools/)** — 18 个 Agent 的详细分析
- **[Claude Code](./docs/tools/claude-code/)** — 8 篇（79 命令/架构/Skill+13 插件/24 Hook/会话/Remote Control）
- **[Copilot CLI](./docs/tools/copilot-cli/)** — 3 篇（34 命令 + 67 工具 + 3 代理）
- **[Codex CLI](./docs/tools/codex-cli/)** — 3 篇（28 命令 + 三平台沙箱）
- **[Gemini CLI](./docs/tools/gemini-cli/)** — 5 篇（39 命令/8 策略路由/策略引擎）
- **[Kimi CLI](./docs/tools/kimi-cli/)** — 3 篇（28 命令/Wire 协议）
- **[Aider](./docs/tools/aider/)** — 3 篇（42 命令/PageRank RepoMap）
- **[OpenCode](./docs/tools/opencode/)** — 3 篇（18 工具+7 代理/多客户端）
- **[Qwen Code](./docs/tools/qwen-code/)** — 4 篇（41 命令/16 工具/Arena+扩展系统）
- **[Goose](./docs/tools/goose/)** — 4 篇（MCP 原生架构/11 Platform Extension/Recipe）

</details>

<details><summary><b>全局对比（选型必读）</b></summary>

- [功能对比矩阵](./docs/comparison/features.md) — 14 Agent × 多维度横向对比
- [隐私与遥测对比](./docs/comparison/privacy-telemetry.md) — 遥测端点、数据采集、安全监控
- [定价与成本](./docs/comparison/pricing.md) | [系统要求](./docs/comparison/system-requirements.md) | [版本迭代](./docs/comparison/evolution-community.md)

</details>

<details><summary><b>架构与命令对比</b></summary>

- [架构深度对比](./docs/comparison/architecture-deep-dive.md) — 10 Agent 代理循环 + Mermaid 图
- [功能性内部机制](./docs/comparison/functional-internals.md) — API 参数、编辑格式
- [/review](./docs/comparison/review-command.md) | [/security-review](./docs/comparison/security-review-command-deep-dive.md) | [/compact /plan /init](./docs/comparison/key-commands-deep-dive.md) | [/loop /schedule](./docs/comparison/loop-schedule.md) | [/simplify](./docs/comparison/simplify-command.md)
- [/hooks /model /mcp](./docs/comparison/infra-commands.md) | [/btw /rewind](./docs/comparison/btw-rewind.md) | [插件 Marketplace 生命周期](./docs/comparison/plugin-marketplace-lifecycle-deep-dive.md) | [BriefTool 异步消息](./docs/comparison/brieftool-async-user-messages-deep-dive.md) | [/context 自动化诊断](./docs/comparison/context-usage-noninteractive-deep-dive.md) | [内置命令总览](./docs/comparison/slash-commands-deep-dive.md)

</details>

<details><summary><b>系统能力 Deep-Dive（15 篇）</b></summary>

**范式对比：**
[CLI Agent vs IDE Agent](./docs/comparison/cli-vs-ide-agents.md) — 终端原生 vs 编辑器内嵌的根本差异

**核心架构：**
[模型路由](./docs/comparison/model-routing.md) | [上下文压缩](./docs/comparison/context-compression-deep-dive.md) | [MCP 集成](./docs/comparison/mcp-integration-deep-dive.md) | [沙箱安全](./docs/comparison/sandbox-security-deep-dive.md) | [多代理](./docs/comparison/multi-agent-deep-dive.md)

**扩展系统：**
[Hook/插件](./docs/comparison/hook-plugin-extension-deep-dive.md) | [Skill 技能](./docs/comparison/skill-system-deep-dive.md) | [长期记忆](./docs/comparison/memory-system-deep-dive.md)

**工程实践：**
[终端 UI](./docs/comparison/terminal-ui-deep-dive.md) | [Git 集成](./docs/comparison/git-integration-deep-dive.md) | [测试反射](./docs/comparison/test-reflection-deep-dive.md) | [CI 模式](./docs/comparison/ci-scripting-deep-dive.md) | [遥测隐私](./docs/comparison/telemetry-privacy-deep-dive.md) | [系统提示](./docs/comparison/system-prompt-deep-dive.md) | [API 参数](./docs/comparison/api-params-deep-dive.md)

</details>

<details><summary><b>Agent 间 1v1 对比 + Qwen 功能补全</b></summary>

- [Claude Code vs Cursor](./docs/comparison/claude-code-vs-cursor.md) | [vs Copilot CLI](./docs/comparison/claude-code-vs-copilot-cli.md) | [Aider vs Goose](./docs/comparison/aider-vs-goose.md)
- [Qwen vs Claude Code](./docs/comparison/qwen-vs-claude-code.md) | [vs Gemini vs Kimi](./docs/comparison/qwen-vs-gemini-vs-kimi.md) | [OpenCode vs Qwen](./docs/comparison/opencode-vs-qwen-source.md)
- [对标 Claude Code](./docs/comparison/qwen-code-feature-gaps.md) | [对标 Gemini CLI](./docs/comparison/qwen-code-vs-gemini-feature-gaps.md) | [对标 OpenCode](./docs/comparison/qwen-code-vs-opencode-feature-gaps.md) | [vs Kimi CLI](./docs/comparison/qwen-code-vs-kimi-feature-gaps.md)
- [性能差距+改进路线图](./docs/comparison/claude-code-speed-qwen-improvements.md)

</details>

<details><summary><b>使用指南</b></summary>

**用户指南：**
[Claude Code](./docs/guides/claude-code-user-guide.md) | [Copilot CLI](./docs/guides/copilot-cli-user-guide.md) | [Qwen Code](./docs/guides/qwen-code-user-guide.md) | [入门指南](./docs/guides/getting-started.md)

**实操：**
[工作流](./docs/guides/workflows.md) | [配置示例](./docs/guides/config-examples.md) | [迁移](./docs/guides/migration.md) | [故障排查](./docs/guides/troubleshooting.md) | [高效提示词](./docs/guides/effective-prompts.md)

**深度配置：**
[CLAUDE.md 写作](./docs/guides/writing-claude-md.md) | [AGENTS.md](./docs/guides/agents-md.md) | [长期记忆与个性化](./docs/guides/long-term-memory.md) | [Skill 设计](./docs/guides/skill-design.md) | [Hooks](./docs/guides/hooks-config.md) | [上下文管理](./docs/guides/context-management.md) | [安全加固](./docs/guides/security-hardening.md)

**架构选型：**
[构建自己的 Agent](./docs/guides/build-your-own-agent.md) — SDK 框架 vs 成品 Agent 扩展，4 层扩展路径（SKILL → Hooks → MCP → 插件）

</details>

**参考文档：**
[架构原理](./docs/architecture/overview.md) | [基准测试](./docs/benchmarks/overview.md) | [外部资源](./docs/resources.md)

---

## 本仓库的源码分析基础

| 项目 | 语言 | 代码量 | 关键发现 |
|------|------|--------|---------|
| Aider | Python | ~30k 行 | 14 编辑格式，PageRank RepoMap |
| Goose | **Rust** | ~55k 行 | MCP 原生，58+ 提供商 |
| Gemini CLI | TypeScript | ~191k 行 | 8 策略路由，TOML 引擎 |
| Qwen Code | TypeScript | ~191k 行 | Gemini 分叉 + Arena + 6+ 提供商 |
| OpenCode | **TypeScript（Bun）** | 983 TS + 359 TSX | 100+ Provider + 37 LSP + ACP |
| Cline | TypeScript | ~40k 行 | Git Checkpoint + 48 提供商 |
| SWE-agent | Python | ~20k 行 | ACI + Bundle 工具 |
| OpenHands | Python | ~60k 行 | EventStream + 多代理 |
| Kimi CLI | **Python** | ~20k 行 | Wire 协议 + D-Mail |

**资源链接：**
[awesome-cli-coding-agents](https://github.com/bradAGI/awesome-cli-coding-agents) | [SWE-bench](https://www.swebench.com/) | [MCP 协议](https://modelcontextprotocol.io/)

## 贡献

欢迎贡献！请查看 [CONTRIBUTING.md](./CONTRIBUTING.md) 了解指南。

## 许可证

MIT — 详见 [LICENSE](./LICENSE)

---

**注意**：本项目与上述任何 Agent 无关联。信息基于源码分析，仅供参考。
