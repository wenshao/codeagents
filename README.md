# Code Agent CLI 工具对比

> 基于源码分析的 AI 编程助手命令行工具全面对比

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 概述

本仓库提供了 15 款 AI 编程 CLI 工具的全面对比。**核心内容基于 11 个开源项目的本地源码深度分析**，而非仅依赖官方文档，确保技术细节的准确性。

### 源码分析纠正的重要事实

| 工具 | 官方/常见说法 | 源码实际情况 |
|------|-------------|-------------|
| **Goose** | TypeScript | **Rust**（55k 行） |
| **OpenCode** | Go | **TypeScript**（Bun + Monorepo） |
| **Kimi CLI** | TypeScript | **Python**（68.8%） |
| **Qwen Code** | 原创 | **Gemini CLI 分叉**（大幅增强） |

## 快速对比表

| 工具 | 开发者 | 许可证 | Stars | 语言 | LLM 提供商 | 特色 |
|------|--------|--------|-------|------|-----------|------|
| [Gemini CLI](./docs/tools/gemini-cli.md) | Google | Apache-2.0 | 98k+ | TypeScript | 1 (Gemini) | Google 官方，Qwen Code 上游 |
| [OpenHands](./docs/tools/openhands.md) | OpenHands | MIT | 69k+ | Python | 100+ | 浏览器操作，Docker 沙箱，多代理委托 |
| [Codex CLI](./docs/tools/codex-cli.md) | OpenAI | Apache-2.0 | 66k+ | TypeScript | 1 (OpenAI) | OpenAI 官方，默认网络隔离沙箱 |
| [Cline](./docs/tools/cline.md) | Cline | Apache-2.0 | 59k+ | TypeScript | 48+ | VS Code 原生，Git Checkpoint 回滚 |
| [Aider](./docs/tools/aider.md) | Paul Gauthier | GPL-3.0 | 42k+ | Python | 100+ | 14 种编辑格式，Git 原生自动提交 |
| [Goose](./docs/tools/goose.md) | Block | Apache-2.0 | 33k+ | **Rust** | 58+ | MCP 原生，Recipe 任务模板 |
| [Continue](./docs/tools/continue.md) | Continue | Apache-2.0 | 31k+ | TypeScript | 60+ | PR Checks CI 审查，语义索引 |
| [Warp](./docs/tools/warp.md) | Warp | 专有 | 26k+ | Rust | 多种 | 终端替代品，GPU 渲染 |
| [Qwen Code](./docs/tools/qwen-code.md) | 阿里云 | Apache-2.0 | 20k+ | TypeScript | 5 | 免费 OAuth 1000 次/天，6 语言 UI |
| [SWE-agent](./docs/tools/swe-agent.md) | Princeton NLP | MIT | 18k+ | Python | 100+ | SWE-bench 74%（增强版），Docker 沙箱 |
| [OpenCode](./docs/tools/opencode.md) | Anomaly | MIT | 130k+ | **TypeScript** | 100+ | 多客户端（TUI+Web+桌面），37 LSP，26 Formatter，ACP IDE 集成 |
| [Kimi CLI](./docs/tools/kimi-code.md) | 月之暗面 | Apache-2.0 | 7k+ | **Python** | 6 | 双模式 Agent↔Shell，Wire 协议，子代理系统 |
| [Claude Code](./docs/tools/claude-code.md) | Anthropic | 专有 | - | Rust | 1 (Claude) | 13 官方插件，Prompt Hook，100 万上下文 |
| [Cursor](./docs/tools/cursor-cli.md) | Cursor | 专有 | - | TypeScript | 多种 | AI 原生 IDE，Background Agent |
| [Copilot CLI](./docs/tools/github-copilot-cli.md) | GitHub | 专有 | 9k+ | Shell | 多种 | 终端原生代理，GitHub 深度集成，MCP 扩展 |

## 文档导航

### 工具详情（源码级）
- **[工具索引](./docs/tools/)** — 16 个工具的详细分析，含架构图和代码引用
- **[Claude Code 专题](./docs/tools/claude-code/)** — 7 篇深度文档（概述/60+ 命令/架构/工具/Skill+13 插件/设置/会话）
- **[Copilot CLI 专题](./docs/tools/copilot-cli/)** — 3 篇深度文档（概述/34 命令 + 67 工具 + 3 代理/架构）
- **[Codex CLI 专题](./docs/tools/codex-cli/)** — 3 篇深度文档（概述/28 交互命令 + 15 CLI/Rust 架构）
- **[Gemini CLI 专题](./docs/tools/gemini-cli/)** — 5 篇深度文档（概述/39 命令/架构/23 工具/策略引擎）
- **[Kimi CLI 专题](./docs/tools/kimi-cli/)** — 3 篇深度文档（概述/28 命令/Wire 协议+18 工具）
- **[Aider 专题](./docs/tools/aider/)** — 3 篇深度文档（概述/42 命令/PageRank RepoMap）
- **[OpenCode 专题](./docs/tools/opencode/)** — 3 篇深度文档（概述/18 工具+7 代理/多客户端架构）

### 对比文档
- **[功能对比矩阵](./docs/comparison/features.md)** — 14 工具横向对比（模型、架构、Git、安全、多模态、平台、成本等）
- **[内置命令能力深度对比](./docs/comparison/slash-commands-deep-dive.md)** — 10 大关键命令的源码级实现对比
- **[隐私与遥测对比](./docs/comparison/privacy-telemetry.md)** — 遥测端点、数据采集、安全监控、Machine ID 全工具对比
- **[架构深度对比](./docs/comparison/architecture-deep-dive.md)** — 11 个项目的代理循环、工具系统、安全模型等
- **[Claude Code vs Cursor](./docs/comparison/claude-code-vs-cursor.md)** — 终端代理 vs AI IDE，两大商业头部对比
- **[Claude Code vs Copilot CLI](./docs/comparison/claude-code-vs-copilot-cli.md)** — 终端代理双雄对比
- **[Aider vs Goose](./docs/comparison/aider-vs-goose.md)** — 开源代理双雄对比
- **[Qwen Code vs Claude Code](./docs/comparison/qwen-vs-claude-code.md)** — 开源 vs 闭源头部代理全面对比
- **[Claude Code 为什么更快？Qwen Code 改进建议](./docs/comparison/claude-code-speed-qwen-improvements.md)** — 性能差距根因 + 改进路线图
- **[Qwen Code 功能补全：对标 Claude Code](./docs/comparison/qwen-code-feature-gaps.md)** — 功能缺口与优先级
- **[Qwen Code 功能补全：对标 OpenCode](./docs/comparison/qwen-code-vs-opencode-feature-gaps.md)** — 功能缺口与优先级
- **[Qwen Code 功能补全：对标上游 Gemini CLI](./docs/comparison/qwen-code-vs-gemini-feature-gaps.md)** — 分叉后未移植的功能
- **[Qwen Code vs Kimi CLI 双向缺口](./docs/comparison/qwen-code-vs-kimi-feature-gaps.md)** — 两个国内工具的功能互补
- **[Qwen vs Gemini vs Kimi](./docs/comparison/qwen-vs-gemini-vs-kimi.md)** — 三者谱系与分叉差异
- **[OpenCode vs Qwen Code](./docs/comparison/opencode-vs-qwen-source.md)** — 15 维度源码对比

### 使用指南
- **[入门指南](./docs/guides/getting-started.md)** — 决策树和安装教程
- **[实操工作流教程](./docs/guides/workflows.md)** — 5 个真实场景的完整操作流程
- **[工具迁移指南](./docs/guides/migration.md)** — 配置映射与迁移路径
- **[故障排查指南](./docs/guides/troubleshooting.md)** — 常见问题与解决方案

### 参考文档
- **[架构原理](./docs/architecture/overview.md)** — 代理循环、MCP、上下文管理
- **[基准测试](./docs/benchmarks/overview.md)** — SWE-bench、Aider Benchmark、Terminal-Bench 等
- **[外部资源](./docs/resources.md)** — 视频教程、博客、论文、社区

## 架构流派（源码分析发现）

| 流派 | 代表工具 | 核心模式 |
|------|---------|---------|
| **编辑优先** | Aider | LLM 直接输出代码修改（14 种格式），工具是辅助 |
| **工具调用** | Claude Code, Codex CLI, OpenCode, Cline, Goose | 结构化 function calling 操作环境 |
| **事件驱动** | OpenHands | EventStream 发布/订阅，最灵活但最复杂 |
| **ReAct 循环** | Gemini CLI, Qwen Code, SWE-agent | 思考→行动→观察→重复 |

## 技术栈分布

| 语言 | 工具 | 特点 |
|------|------|------|
| **Rust** | Goose, Claude Code, Warp | 性能最佳，内存最低 |
| **TypeScript** | Gemini CLI, Qwen Code, OpenCode, Codex CLI, Cline, Continue | Ink/React TUI 成熟，生态丰富 |
| **Python** | Aider, SWE-agent, OpenHands, Kimi CLI | LiteLLM 100+ 模型，学术研究首选 |

## 30 秒选型指南

- **日常编码** → Claude Code（推理强）或 Aider（Git 集成好）
- **免费使用** → Qwen Code（1000 次/天）或 Gemini CLI
- **多模型切换** → OpenCode（100+ via models.dev）或 Goose（58+）
- **VS Code 用户** → Cline（58k Stars）或 Continue（PR Checks）
- **中文开发者** → Qwen Code 或 Kimi CLI
- **自动化/CI** → SWE-agent 或 OpenHands
- **安全沙箱** → Codex CLI（默认网络隔离）或 Gemini CLI（TOML 策略引擎）
- **OpenAI 用户** → Codex CLI（官方开源）

## 性能基准 (2026)

| Agent | SWE-bench Verified | 说明 |
|-------|-------------------|------|
| SWE-agent (增强版) | 74% | RetryAgent + 代码审查循环 |
| Claude Code | ~60% | 复杂推理能力强 |
| OpenHands | ~55% | 全栈任务，浏览器操作 |
| Aider | ~45% | 14 种编辑格式适配 |
| Continue | ~40% | 语义索引 + 重构 |

*数据来源：[SWE-bench 排行榜](https://www.swebench.com/)*

## 本仓库的源码分析基础

本仓库的对比文档基于以下本地源码仓库的深度分析：

| 项目 | 实际语言 | 代码量 | 关键发现 |
|------|---------|--------|---------|
| Aider | Python | ~30k 行 | 14 种编辑格式，RepoMap AST |
| Goose | **Rust** | ~55k 行 | MCP 原生，58+ 提供商 |
| Gemini CLI | TypeScript | ~191k 行 | TOML 策略引擎，Qwen Code 上游 |
| Qwen Code | TypeScript | ~191k 行 | Gemini 分叉 + 多提供商 + Arena |
| OpenCode | **TypeScript** | ~983 TS + 359 TSX 文件 | 100+ Provider（models.dev）+ 37 LSP + 26 Formatter + ACP IDE |
| Cline | TypeScript | ~40k 行 | Git Checkpoint + 48 提供商 |
| SWE-agent | Python | ~20k 行 | ACI 设计 + Bundle 工具 |
| OpenHands | Python | ~60k 行 | EventStream + 多代理委托 |
| Continue | TypeScript | ~80k 行 | 语义索引 + PR Checks |
| Kimi CLI | **Python** | ~20k 行 | 双模式 Ctrl-X + Wire 协议 |

## 资源链接

- [awesome-cli-coding-agents](https://github.com/bradAGI/awesome-cli-coding-agents) — CLI 编程代理精选列表
- [SWE-bench](https://www.swebench.com/) — 软件工程基准测试
- [MCP 协议](https://modelcontextprotocol.io/) — 模型上下文协议标准

## 贡献

欢迎贡献！请查看 [CONTRIBUTING.md](./CONTRIBUTING.md) 了解指南。

## 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](./LICENSE)

---

**注意**：本项目与上述任何工具无关联。信息基于源码分析，仅供参考。
