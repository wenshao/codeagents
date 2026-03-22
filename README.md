# Code Agent CLI 工具对比

> 基于源码分析的 AI 编程助手命令行工具全面对比

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 概述

本仓库提供了 14 款 AI 编程 CLI 工具的全面对比。**核心内容基于 11 个开源项目的本地源码深度分析**，而非仅依赖官方文档，确保技术细节的准确性。

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
| [Claude Code](./docs/tools/claude-code.md) | Anthropic | 专有 | - | Rust | 1 (Claude) | MCP 生态，100 万上下文 |
| [Aider](./docs/tools/aider.md) | Paul Gauthier | GPL-3.0 | 40k+ | Python | 100+ | 14 种编辑格式，Git 原生 |
| [Cline](./docs/tools/cline.md) | Cline | Apache-2.0 | 58k+ | TypeScript | 48+ | Git Checkpoint 回滚 |
| [OpenHands](./docs/tools/openhands.md) | OpenHands | MIT | 32k+ | Python | 100+ | 浏览器操作，多代理委托 |
| [Goose](./docs/tools/goose.md) | Block | Apache-2.0 | 27k+ | **Rust** | 58+ | MCP 原生，Recipe 系统 |
| [Continue](./docs/tools/continue.md) | Continue | Apache-2.0 | 27k+ | TypeScript | 60+ | PR Checks，语义索引 |
| [Warp](./docs/tools/warp.md) | Warp | 专有 | 30k+ | Rust | 多种 | AI 终端替代品 |
| [SWE-agent](./docs/tools/swe-agent.md) | Princeton NLP | MIT | 19k+ | Python | 100+ | SWE-bench 74%，Docker 沙箱 |
| [Cursor](./docs/tools/cursor-cli.md) | Cursor | 专有 | - | TypeScript | 多种 | Background Agent |
| [Copilot CLI](./docs/tools/github-copilot-cli.md) | GitHub | 专有 | - | TypeScript | GPT-4 | GitHub 生态 |
| [OpenCode](./docs/tools/opencode.md) | OpenCode AI | MIT | 3k+ | **TypeScript** | 20+ | 多客户端，插件系统 |
| [Gemini CLI](./docs/tools/gemini-cli.md) | Google | Apache-2.0 | 1k+ | TypeScript | 1 (Gemini) | TOML 策略引擎 |
| [Qwen Code](./docs/tools/qwen-code.md) | 阿里云 | Apache-2.0 | 2k+ | TypeScript | 5 | 免费 OAuth，6 语言 UI |
| [Kimi CLI](./docs/tools/kimi-code.md) | 月之暗面 | 开源 | - | **Python** | 4 | 双模式 Ctrl-X |

## 文档导航

### 工具详情（源码级）
- **[工具索引](./docs/tools/)** — 14 个工具的详细分析，含架构图和代码引用

### 对比文档
- **[功能对比矩阵](./docs/comparison/features.md)** — 14 工具 × 8 维度横向对比
- **[架构深度对比](./docs/comparison/architecture-deep-dive.md)** — 11 个项目的代理循环、工具系统、安全模型等
- **[Qwen vs Gemini vs Kimi](./docs/comparison/qwen-vs-gemini-vs-kimi.md)** — 三者谱系与分叉差异
- **[OpenCode vs Qwen Code](./docs/comparison/opencode-vs-qwen-source.md)** — 15 维度源码对比

### 参考文档
- **[架构原理](./docs/architecture/overview.md)** — 代理循环、MCP、上下文管理
- **[基准测试](./docs/benchmarks/overview.md)** — SWE-bench 等性能数据
- **[入门指南](./docs/guides/getting-started.md)** — 决策树和安装教程

## 架构流派（源码分析发现）

| 流派 | 代表工具 | 核心模式 |
|------|---------|---------|
| **编辑优先** | Aider | LLM 直接输出代码修改（14 种格式），工具是辅助 |
| **工具调用** | Claude Code, OpenCode, Cline, Goose | 结构化 function calling 操作环境 |
| **事件驱动** | OpenHands | EventStream 发布/订阅，最灵活但最复杂 |
| **ReAct 循环** | Gemini CLI, Qwen Code, SWE-agent | 思考→行动→观察→重复 |

## 技术栈分布

| 语言 | 工具 | 特点 |
|------|------|------|
| **Rust** | Goose, Claude Code, Warp | 性能最佳，内存最低 |
| **TypeScript** | Gemini CLI, Qwen Code, OpenCode, Cline, Continue | Ink/React TUI 成熟，生态丰富 |
| **Python** | Aider, SWE-agent, OpenHands, Kimi CLI | LiteLLM 100+ 模型，学术研究首选 |

## 30 秒选型指南

- **日常编码** → Claude Code（推理强）或 Aider（Git 集成好）
- **免费使用** → Qwen Code（1000 次/天）或 Gemini CLI
- **多模型切换** → Goose（58+）或 OpenCode（20+）
- **VS Code 用户** → Cline（58k Stars）或 Continue（PR Checks）
- **中文开发者** → Qwen Code 或 Kimi CLI
- **自动化/CI** → SWE-agent 或 OpenHands
- **安全敏感** → Gemini CLI（TOML 策略引擎）

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
| OpenCode | **TypeScript** | ~50k 行 | Vercel AI SDK + 多客户端 |
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
