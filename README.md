# Code Agent CLI 工具对比

> AI 编程助手命令行工具的全面对比

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 概述

本仓库提供了各种 Code Agent CLI 工具的全面对比——这些是运行在终端中、帮助你编写、编辑和理解代码的 AI 助手。

## 快速对比表

| 工具 | 开发者 | 许可证 | Stars | 语言 | 主要模型 |
|------|--------|--------|-------|------|----------|
| [Claude Code](#claude-code) | Anthropic | 专有 | - | Rust | Claude 4.5/4.6 |
| [GitHub Copilot CLI](#github-copilot-cli) | GitHub | 专有 | - | TypeScript | GPT-4 |
| [Aider](#aider) | Paul Gauthier | GPL-3.0 | 40k+ | Python | GPT-4, Claude |
| [Cursor CLI](#cursor-cli) | Cursor | 专有 | - | TypeScript | 多种 |
| [SWE-agent](#swe-agent) | Princeton NLP | MIT | 19k+ | Python | Claude, GPT-4 |
| [Cline](#cline) | Cline | Apache-2.0 | 58k+ | TypeScript | Claude |
| [Goose](#goose) | Block | Apache-2.0 | 27k+ | Rust | 模型无关 |
| [OpenCode](#opencode) | OpenCode AI | MIT | 3k+ | TypeScript | Claude, GPT, Gemini |
| [Gemini CLI](#gemini-cli) | Google | Apache-2.0 | 1k+ | TypeScript | Gemini |
| [Warp](#warp) | Warp | 专有 | 30k+ | Rust | 多种 |
| [Continue](#continue) | Continue | Apache-2.0 | 27k+ | TypeScript | 多种 |
| [OpenHands/OpenDevin](#openhandsopendevin) | OpenHands | MIT | 32k+ | Python | 多种 |
| [Qwen Code](#qwen-code) | 阿里云 | Apache-2.0 | 2k+ | TypeScript | Qwen3-Coder |
| [Kimi CLI](#kimi-cli) | 月之暗面 | 开源 | - | Python | Kimi |

## 文档导航

- **[工具详情](./docs/tools/)** - 每个工具的详细分析
- **[功能对比](./docs/comparison/features.md)** - 功能横向对比
- **[OpenCode vs Qwen Code 源码对比](./docs/comparison/opencode-vs-qwen-source.md)** - 基于源码的深度分析
- **[架构深度对比](./docs/comparison/architecture-deep-dive.md)** - 9 个项目源码级架构对比
- **[基准测试](./docs/benchmarks/)** - SWE-bench 等性能测试
- **[架构分析](./docs/architecture/overview.md)** - 工作原理深度解析
- **[入门指南](./docs/guides/getting-started.md)** - 如何选择和开始使用

## 工具分类

### 1. 商业工具
成熟的企业级解决方案，UI/UX 精良：
- Claude Code
- GitHub Copilot CLI
- Cursor CLI
- Warp

### 2. 开源 CLI 工具
免费、开源的终端原生代理：
- Aider
- OpenCode
- Goose
- Gemini CLI

### 3. 国内工具
中国厂商推出的 CLI 编程工具：
- **Qwen Code** (阿里云) - 每日 2000 次免费额度
- **Kimi CLI** (月之暗面) - 双模式交互（Agent + Shell，Ctrl-X 切换）

### 4. 研究/学术项目
有公开基准测试的学术项目：
- SWE-agent
- OpenHands/OpenDevin

### 5. 带 CLI 功能的 IDE 扩展
主要作为 IDE 扩展但提供 CLI 访问：
- Cline
- Continue

## 核心差异对比

| 特性 | 领先者 | 说明 |
|---------|--------|------|
| **代码编辑** | Claude Code | 原生编辑，MCP 生态 |
| **Git 集成** | Aider | 最佳 Git 工作流集成 |
| **基准性能** | Claude Code | SWE-bench 复杂推理领先 |
| **终端速度** | Gemini CLI | 轻量级，简单任务快 |
| **模型灵活性** | OpenCode, Goose | 20+ 提供商支持 |
| **隐私/自托管** | TabbyML | 自托管选项 |

## 性能基准 (2026)

基于 SWE-bench Verified 的数据：

| Agent | 得分 | 说明 |
|-------|------|------|
| SWE-agent (增强版) | 74% | 专门调优后 |
| Claude Code | ~60% | 复杂推理能力强 |
| OpenHands | ~55% | 全栈任务表现好 |
| Aider | ~45% | 专注代码编辑 |
| Continue | ~40% | 重构能力不错 |

*数据来源：[SWE-bench 排行榜](https://www.swebench.com/)*

## 资源链接

- [awesome-cli-coding-agents](https://github.com/bradAGI/awesome-cli-coding-agents) - CLI 编程代理精选列表
- [AI Agent Benchmark](https://github.com/murataslan1/ai-agent-benchmark) - 全面对比
- [SWE-bench](https://www.swebench.com/) - 软件工程基准测试

## 贡献

欢迎贡献！请查看 [CONTRIBUTING.md](./CONTRIBUTING.md) 了解指南。

## 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](./LICENSE)

---

**注意**：本项目与上述任何工具无关联。信息仅供参考。
