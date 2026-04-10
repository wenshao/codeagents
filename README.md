# AI 编程 Code Agent 对比

> 基于源码分析和二进制反编译的 18 款 AI 编程 Code Agent 全面对比 | 284 文件 | 72,000+ 行 | 134 篇 Deep-Dive | 10 个 EVIDENCE.md

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 高频入口

| 入口 | 说明 |
|------|------|
| **[Deep-Dive 索引（133 篇）](./docs/comparison/deep-dive-index.md)** | 按主题分类的全部深度分析文章 |
| **[Qwen Code 改进报告（248 项）](./docs/comparison/qwen-code-improvement-report.md)** | Claude Code 对比 + 31 个社区 PR 追踪 |
| **[Gemini CLI backport（53 项）](./docs/comparison/qwen-code-gemini-upstream-report.md)** | 上游可 backport 改进 + 模块级架构对比 |
| **[/review 功能分析](./docs/comparison/qwen-code-review-improvements.md)** | 审查功能 5 方对比（含 gstack） |
| **[Codex CLI 对标改进（25 项）](./docs/comparison/qwen-code-codex-improvements.md)** | 沙箱 + Apply Patch + Feature Flag + 网络代理 |
| **[OpenCode 对标改进（27 项）](./docs/comparison/qwen-code-opencode-improvements.md)** | Provider 系统 + Plugin 插件 + Snapshot 快照 |
| **[功能对比矩阵](./docs/comparison/features.md)** | 14 Agent × 多维度横向对比 |
| **[一页总结（选型速查）](./docs/SUMMARY.md)** | 给没时间看全部文档的人 |

## 30 秒选型指南

| 场景 | 推荐 | 理由 |
|------|------|------|
| **日常编码** | Claude Code 或 Aider | 最强推理 / 最好 Git 集成 |
| **免费使用** | Qwen Code 或 Gemini CLI | 1000 次/天免费 OAuth / Google 账号 |
| **多模型切换** | OpenCode、Goose 或 Qwen Code | 100+ models.dev / 58+ 提供商 / Arena |
| **VS Code 用户** | Cline 或 Continue | IDE 原生集成 / PR Checks |
| **中文开发者** | Qwen Code 或 Kimi CLI | 6 语言 UI / 中文模型 |
| **CI/CD 自动化** | SWE-agent 或 OpenHands | 批量评估 / Docker 沙箱 |
| **安全沙箱** | Codex CLI 或 Gemini CLI | 三平台 OS 沙箱 / TOML 策略引擎 |
| **GitHub 生态** | Copilot CLI | 67 GitHub 工具 |

## 快速对比表

> Stars 为 2026-03-31 快照，按 Stars 降序。详细数据见 [`docs/data/agents-metadata.json`](./docs/data/agents-metadata.json)。

| Agent | 开发者 | 许可证 | 语言 | Stars | 提供商 | 特色 |
|------|--------|--------|------|------|-------|------|
| [OpenCode](./docs/tools/opencode/) | Anomaly | MIT | TypeScript（Bun） | 133k | 100+ | 多客户端（TUI+Web+桌面），37 LSP |
| [Gemini CLI](./docs/tools/gemini-cli/) | Google | Apache-2.0 | TypeScript | 100k | 1 | 8 策略模型路由，TOML 策略引擎 |
| [Claude Code](./docs/tools/claude-code/) | Anthropic | 专有 | Rust | 85k | 1 | 50ms 启动，27 Hook 事件，Channels |
| [OpenHands](./docs/tools/openhands.md) | OpenHands | MIT | Python | 70k | 100+ | Docker 沙箱，三层安全，多代理 |
| [Codex CLI](./docs/tools/codex-cli/) | OpenAI | Apache-2.0 | Rust | 68k | 1 | 三平台 OS 沙箱，Cloud 远程执行 |
| [Cline](./docs/tools/cline.md) | Cline | Apache-2.0 | TypeScript | 60k | 48+ | VS Code 原生，Git Checkpoint |
| [Oh My OpenAgent](./docs/tools/oh-my-openagent.md) | code-yeongyu | SUL-1.0 | TypeScript | ~45k | 多种 | OpenCode Harness 层 |
| [Aider](./docs/tools/aider/) | Paul Gauthier | GPL-3.0 | Python | 43k | 100+ | 14 编辑格式，三槽位模型，/undo |
| [Goose](./docs/tools/goose/) | Block | Apache-2.0 | Rust | 34k | 58+ | MCP 原生，11 Platform Extension |
| [Continue](./docs/tools/continue.md) | Continue | Apache-2.0 | TypeScript | 32k | 68+ | PR Checks CI 审查 |
| [Cursor](./docs/tools/cursor-cli.md) | Cursor | 专有 | TypeScript | ~33k | 多种 | AI 原生 IDE，Background Agent |
| [Warp](./docs/tools/warp.md) | Warp | 专有 | Rust | 26k | 多种 | GPU 渲染终端 |
| [Qwen Code](./docs/tools/qwen-code/) | 阿里云 | Apache-2.0 | TypeScript | 21k | 6+ | 免费 1000 次/天，Arena 多模型竞争 |
| [SWE-agent](./docs/tools/swe-agent.md) | Princeton | MIT | Python | 19k | 100+ | SWE-bench 评估 |
| [Copilot CLI](./docs/tools/copilot-cli/) | GitHub | 专有 | TypeScript | 10k | 多种 | 67 GitHub 工具 |
| [Kimi CLI](./docs/tools/kimi-cli/) | 月之暗面 | Apache-2.0 | Python | 7k | 6 | Wire 协议，D-Mail |
| [Qoder CLI](./docs/tools/qoder-cli/) | QoderAI | 专有 | Go | — | 多种 | Quest 模式 |

---

## 文档导航

### Agent 源码分析

| Agent | 文件数 | 核心内容 |
|-------|--------|---------|
| [Claude Code](./docs/tools/claude-code/) | 20 | 79 命令 / 42 工具 / 14 Skill / 27 Hook / 会话 / 多 Agent / 系统提示 / MCP / 遥测 |
| [Gemini CLI](./docs/tools/gemini-cli/) | 7 | 41 命令 / 23 工具 / 策略引擎（Qwen Code 上游） |
| [OpenCode](./docs/tools/opencode/) | 9 | 18 工具 / 7 代理 / 18 Hook / Session Fork / 多客户端 |
| [Qwen Code](./docs/tools/qwen-code/) | 8 | 41 命令 / 16 工具 / Arena / CoreToolScheduler / 多 Provider |
| [Copilot CLI](./docs/tools/copilot-cli/) | 3 | 34 命令 + 67 工具 + 3 代理 |
| [Codex CLI](./docs/tools/codex-cli/) | 3 | 28 命令 + 三平台沙箱 |
| [Aider](./docs/tools/aider/) | 3 | 42 命令 / PageRank RepoMap |
| [Goose](./docs/tools/goose/) | 4 | MCP 原生架构 / 11 Platform Extension |
| [Kimi CLI](./docs/tools/kimi-cli/) | 3 | 28 命令 / Wire 协议 |
| [全部 Agent 索引](./docs/tools/) | — | 18 个 Agent 的详细分析 |

### Qwen Code 改进报告

| 报告 | 说明 |
|------|------|
| [Claude Code 对比（248 项）](./docs/comparison/qwen-code-improvement-report.md) | 改进建议 + 31 个社区 PR 追踪（10 已合并） |
| [Gemini CLI backport（53 项）](./docs/comparison/qwen-code-gemini-upstream-report.md) | 上游可 backport 改进 + 模块级架构对比 |
| [/review 功能分析](./docs/comparison/qwen-code-review-improvements.md) | 审查功能 5 方对比（含 gstack） |
| [工具输出限高](./docs/comparison/tool-output-height-limiting-deep-dive.md) | Gemini CLI SlicingMaxSizedBox vs Qwen Code |
| [Codex CLI 对标改进（25 项）](./docs/comparison/qwen-code-codex-improvements.md) | 沙箱 + Apply Patch + Feature Flag + 网络代理 |
| [OpenCode 对标改进（27 项）](./docs/comparison/qwen-code-opencode-improvements.md) | Provider 系统 + Plugin + Snapshot |
| [Kairos Always-On](./docs/comparison/kairos-always-on-agent-deep-dive.md) | Claude Code 自治 Agent 模式 |

### 全局对比

- [功能对比矩阵](./docs/comparison/features.md) | [隐私与遥测](./docs/comparison/privacy-telemetry.md) | [定价与成本](./docs/comparison/pricing.md) | [系统要求](./docs/comparison/system-requirements.md)
- [架构深度对比](./docs/comparison/architecture-deep-dive.md) | [CLI vs IDE](./docs/comparison/cli-vs-ide-agents.md)

### 系统能力 Deep-Dive

**核心架构：** [模型路由](./docs/comparison/model-routing.md) | [上下文压缩](./docs/comparison/context-compression-deep-dive.md) | [MCP 集成](./docs/comparison/mcp-integration-deep-dive.md) | [沙箱安全](./docs/comparison/sandbox-security-deep-dive.md) | [多代理](./docs/comparison/multi-agent-deep-dive.md)

**扩展系统：** [Hook/插件](./docs/comparison/hook-plugin-extension-deep-dive.md) | [Skill 技能](./docs/comparison/skill-system-deep-dive.md) | [长期记忆](./docs/comparison/memory-system-deep-dive.md)

**工程实践：** [终端 UI](./docs/comparison/terminal-ui-deep-dive.md) | [Git 集成](./docs/comparison/git-integration-deep-dive.md) | [测试反射](./docs/comparison/test-reflection-deep-dive.md) | [CI 模式](./docs/comparison/ci-scripting-deep-dive.md) | [系统提示](./docs/comparison/system-prompt-deep-dive.md)

**命令对比：** [/review](./docs/comparison/review-command.md) | [/compact /plan /init](./docs/comparison/key-commands-deep-dive.md) | [/loop /schedule](./docs/comparison/loop-schedule.md) | [/btw /rewind](./docs/comparison/btw-rewind.md) | [内置命令总览](./docs/comparison/slash-commands-deep-dive.md)

**完整索引：** [134 篇 Deep-Dive 文章索引](./docs/comparison/deep-dive-index.md)

### Agent 1v1 对比

- [Claude Code vs Cursor](./docs/comparison/claude-code-vs-cursor.md) | [vs Copilot CLI](./docs/comparison/claude-code-vs-copilot-cli.md) | [Aider vs Goose](./docs/comparison/aider-vs-goose.md)
- [Qwen vs Claude Code](./docs/comparison/qwen-vs-claude-code.md) | [vs Gemini vs Kimi](./docs/comparison/qwen-vs-gemini-vs-kimi.md) | [OpenCode vs Qwen](./docs/comparison/opencode-vs-qwen-source.md)

<details><summary><b>使用指南</b></summary>

**用户指南：** [Claude Code](./docs/guides/claude-code-user-guide.md) | [Copilot CLI](./docs/guides/copilot-cli-user-guide.md) | [Qwen Code](./docs/guides/qwen-code-user-guide.md) | [入门指南](./docs/guides/getting-started.md)

**实操：** [工作流](./docs/guides/workflows.md) | [配置示例](./docs/guides/config-examples.md) | [迁移](./docs/guides/migration.md) | [故障排查](./docs/guides/troubleshooting.md) | [高效提示词](./docs/guides/effective-prompts.md)

**深度配置：** [CLAUDE.md 写作](./docs/guides/writing-claude-md.md) | [AGENTS.md](./docs/guides/agents-md.md) | [Skill 设计](./docs/guides/skill-design.md) | [Hooks](./docs/guides/hooks-config.md) | [上下文管理](./docs/guides/context-management.md) | [安全加固](./docs/guides/security-hardening.md)

**架构选型：** [构建自己的 Agent](./docs/guides/build-your-own-agent.md)

</details>

---

## 架构流派

| 流派 | 代表 Agent | 核心模式 |
|------|---------|---------|
| **工具调用** | Claude Code, Codex CLI, Gemini CLI, Qwen Code, OpenCode, Cline, Goose, Copilot CLI, Kimi CLI | 结构化 function calling |
| **编辑优先** | Aider | LLM 直接输出代码修改（14 种格式） |
| **混合 ReAct** | SWE-agent | function calling + 文本动作解析 |
| **事件驱动** | OpenHands | EventStream 发布/订阅 |

## 技术栈

| 语言 | Agent | 特点 |
|------|-------|------|
| **Rust** | Claude Code, Codex CLI, Goose, Warp | 50ms 启动，内存最低 |
| **TypeScript** | Gemini CLI, Qwen Code, Cline, Continue | Ink/React TUI |
| **TypeScript（Bun）** | OpenCode | 多客户端平台 |
| **Python** | Aider, SWE-agent, OpenHands, Kimi CLI | LiteLLM 100+ 模型 |

---

## 附录

### 源码分析纠正的"常识"

| Agent | 官方/常见说法 | 源码实际情况 |
|------|-------------|-------------|
| **Goose** | TypeScript | **Rust**（55k 行） |
| **OpenCode** | Go | **TypeScript**（Bun monorepo，v1.0+ 全面重写） |
| **Kimi CLI** | TypeScript | **Python**（68.8%） |
| **Qwen Code** | 原创 | **Gemini CLI 分叉**（大幅增强） |

### 实测性能（2026-03-26 本机测量）

| Agent | 启动时间 | 安装大小 | 二进制类型 |
|-------|---------|---------|-----------|
| **Claude Code** v2.1.84 | **50ms** | 225MB | Rust ELF |
| **Copilot CLI** v1.0.10 | 72ms | 268MB | Node.js SEA |
| **Codex CLI** | 76ms | 142MB | Node.js SEA |
| **Qwen Code** v0.14.1 | 608ms | 48MB | Node.js npm |
| **Gemini CLI** v0.34.0 | 1.5s | 509MB | Node.js npm |

### 源码分析基础

| 项目 | 语言 | 代码量 | 关键发现 |
|------|------|--------|---------|
| Aider | Python | ~30k 行 | 14 编辑格式，PageRank RepoMap |
| Goose | **Rust** | ~55k 行 | MCP 原生，58+ 提供商 |
| Gemini CLI | TypeScript | ~191k 行 | 8 策略路由，TOML 引擎 |
| Qwen Code | TypeScript | ~191k 行 | Gemini 分叉 + Arena |
| OpenCode | **TypeScript（Bun）** | 983 TS + 359 TSX | 100+ Provider + 37 LSP |
| Cline | TypeScript | ~40k 行 | Git Checkpoint |
| SWE-agent | Python | ~20k 行 | ACI + Bundle 工具 |
| OpenHands | Python | ~60k 行 | EventStream + 多代理 |
| Kimi CLI | **Python** | ~20k 行 | Wire 协议 + D-Mail |

**资源：** [awesome-cli-coding-agents](https://github.com/bradAGI/awesome-cli-coding-agents) | [SWE-bench](https://www.swebench.com/) | [MCP 协议](https://modelcontextprotocol.io/) | [架构原理](./docs/architecture/overview.md) | [基准测试](./docs/benchmarks/overview.md)

## 贡献

欢迎贡献！请查看 [CONTRIBUTING.md](./CONTRIBUTING.md) 了解指南。

## 许可证

MIT — 详见 [LICENSE](./LICENSE)

---

**注意**：本项目与上述任何 Agent 无关联。信息基于源码分析，仅供参考。
