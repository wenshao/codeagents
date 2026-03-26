# AI 编程 Code Agent 对比

> 基于源码分析和二进制反编译的 AI 编程 Code Agent 全面对比 | 118 文件 | 34,600+ 行 | 9 个 EVIDENCE.md 证据文件

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**👉 [一页总结（选型速查）](./docs/SUMMARY.md)** — 给没时间看全部文档的人

## 概述

本仓库提供了 17 款 AI 编程 Code Agent 的全面对比。**核心内容基于源码分析（开源 Agent）和二进制反编译（闭源 Agent）**，并附带 EVIDENCE.md 证据文件支撑每项声明。

## 快速对比表

| Agent | 开发者 | 许可证 | Stars | 语言 | LLM 提供商 | 特色 |
|------|--------|--------|-------|------|-----------|------|
| [OpenCode](./docs/tools/opencode/) | Anomaly | MIT | **130k** | **Go + TS** | 100+ | 多客户端（TUI+Web+桌面），37 LSP，ACP IDE |
| [Gemini CLI](./docs/tools/gemini-cli/) | Google | Apache-2.0 | **99k** | TypeScript | 1 (Gemini) | Google 官方，Qwen Code 上游 |
| [Claude Code](./docs/tools/claude-code/) | Anthropic | 专有 | **83k** | Rust | 1 (Claude) | 13 官方插件，Prompt Hook，100 万上下文 |
| [OpenHands](./docs/tools/openhands.md) | OpenHands | MIT | **70k** | Python | 100+ | 浏览器操作，Docker 沙箱，多代理委托 |
| [Codex CLI](./docs/tools/codex-cli/) | OpenAI | Apache-2.0 | **68k** | TypeScript | 1 (OpenAI) | OpenAI 官方，默认网络隔离沙箱 |
| [Cline](./docs/tools/cline.md) | Cline | Apache-2.0 | **59k** | TypeScript | 48+ | VS Code 原生，Git Checkpoint 回滚 |
| [Aider](./docs/tools/aider/) | Paul Gauthier | GPL-3.0 | **42k** | Python | 100+ | 14 种编辑格式，Git 原生自动提交 |
| [Goose](./docs/tools/goose.md) | Block | Apache-2.0 | **34k** | **Rust** | 58+ | MCP 原生，Recipe 任务模板 |
| [Continue](./docs/tools/continue.md) | Continue | Apache-2.0 | **32k** | TypeScript | 60+ | PR Checks CI 审查，语义索引 |
| [Warp](./docs/tools/warp.md) | Warp | 专有 | **26k** | Rust | 多种 | 终端替代品，GPU 渲染 |
| [Qwen Code](./docs/tools/qwen-code.md) | 阿里云 | Apache-2.0 | **21k** | TypeScript | 6+ | 免费 OAuth 1000 次/天，6 语言 UI |
| [SWE-agent](./docs/tools/swe-agent.md) | Princeton NLP | MIT | **19k** | Python | 100+ | SWE-bench 74%（增强版），Docker 沙箱 |
| [Copilot CLI](./docs/tools/copilot-cli/) | GitHub | 专有 | **10k** | Shell | 多种 | 终端原生代理，GitHub 深度集成，MCP 扩展 |
| [Kimi CLI](./docs/tools/kimi-cli/) | 月之暗面 | Apache-2.0 | **7k** | **Python** | 6 | 双模式 Agent↔Shell，Wire 协议，子代理系统 |
| [Cursor](./docs/tools/cursor-cli.md) | Cursor | 专有 | - | TypeScript | 多种 | AI 原生 IDE，Background Agent |
| [Qoder CLI](./docs/tools/qoder-cli/) | QoderAI（阿里） | 专有 | - | **Go** | 多种 | Quest 模式，Claude Code 兼容，信用制定价 |

## 30 秒选型指南

- **日常编码** → Claude Code（推理强）或 Aider（Git 集成好）
- **免费使用** → Qwen Code（1000 次/天）或 Gemini CLI
- **多模型切换** → OpenCode（100+ via models.dev）或 Goose（58+）
- **VS Code 用户** → Cline（58k Stars）或 Continue（PR Checks）
- **中文开发者** → Qwen Code 或 Kimi CLI
- **自动化/CI** → SWE-agent 或 OpenHands
- **安全沙箱** → Codex CLI（默认网络隔离）或 Gemini CLI（TOML 策略引擎）
- **OpenAI 用户** → Codex CLI（官方开源）

---

## 文档导航

### Agent 详情（源码级）

- **[Agent 索引](./docs/tools/)** — 16 个 Agent 的详细分析，含架构图和代码引用
- **[Claude Code 专题](./docs/tools/claude-code/)** — 7 篇深度文档（概述/79 命令/架构/工具/Skill+13 插件/设置/会话）
- **[Copilot CLI 专题](./docs/tools/copilot-cli/)** — 3 篇深度文档（概述/34 命令 + 67 工具 + 3 代理/架构）
- **[Codex CLI 专题](./docs/tools/codex-cli/)** — 3 篇深度文档（概述/28 交互命令 + 15 CLI/Rust 架构）
- **[Gemini CLI 专题](./docs/tools/gemini-cli/)** — 5 篇深度文档（概述/39 命令/架构/23 工具/策略引擎）
- **[Kimi CLI 专题](./docs/tools/kimi-cli/)** — 3 篇深度文档（概述/28 命令/Wire 协议+18 工具）
- **[Aider 专题](./docs/tools/aider/)** — 3 篇深度文档（概述/42 命令/PageRank RepoMap）
- **[OpenCode 专题](./docs/tools/opencode/)** — 3 篇深度文档（概述/18 工具+7 代理/多客户端架构）

### 全局对比（选型必读）

- [功能对比矩阵](./docs/comparison/features.md) — 14 Agent × 多维度横向对比
- [隐私与遥测对比](./docs/comparison/privacy-telemetry.md) — 遥测端点、数据采集、安全监控
- [定价与成本](./docs/comparison/pricing.md) | [系统要求](./docs/comparison/system-requirements.md) | [版本迭代](./docs/comparison/evolution-community.md)

### 架构与内部机制

- [架构深度对比](./docs/comparison/architecture-deep-dive.md) — 10 Agent 代理循环、Mermaid 架构图、源码级参数
- [功能性内部机制](./docs/comparison/functional-internals.md) — API 参数、编辑格式、上下文管理

### 命令实现对比

| 命令 | 文章 | 核心对比 |
|------|------|---------|
| `/review` | [代码审查命令](./docs/comparison/review-command.md) | 9 步流水线 vs 4 代理并行 vs 8 维度 |
| `/compact /plan /init` | [关键命令实现](./docs/comparison/key-commands-deep-dive.md) | 压缩算法、策略引擎、隔离执行 |
| `/loop /schedule` | [循环与调度](./docs/comparison/loop-schedule.md) | 本地循环 vs 远程调度 vs Cloud |
| `/simplify` | [代码简化](./docs/comparison/simplify-command.md) | 三代理 21 检查项自动修复 |
| `/hooks /model /mcp` | [基础设施命令](./docs/comparison/infra-commands.md) | Hook、沙箱、权限、MCP |
| `/btw /rewind` | [旁问与回退](./docs/comparison/btw-rewind.md) | 上下文隔离 + 三选项回退 |
| 全命令总览 | [内置命令能力](./docs/comparison/slash-commands-deep-dive.md) | 11 节全命令逐项对比 |

### 系统能力深度对比（15 篇 Deep-Dive）

**核心架构：**

| 主题 | 文章 | 核心对比 |
|------|------|---------|
| 模型路由 | [自动选择](./docs/comparison/model-routing.md) | 8 策略自动路由 vs 三槽位 vs 手动切换 |
| 上下文压缩 | [压缩算法](./docs/comparison/context-compression-deep-dive.md) | 四阶段验证 vs 递归分割 vs 渐进移除 |
| MCP 集成 | [协议实现](./docs/comparison/mcp-integration-deep-dive.md) | MCP 原生 vs TOML 策略 vs 双下划线命名 |
| 安全隔离 | [沙箱对比](./docs/comparison/sandbox-security-deep-dive.md) | OS 沙箱 vs 28 规则 vs 三层分析 |
| 多代理 | [架构对比](./docs/comparison/multi-agent-deep-dive.md) | Teammates 协作 vs Arena 竞争 vs A2A 远程 |

**扩展系统：**

| 主题 | 文章 | 核心对比 |
|------|------|---------|
| Hook/插件 | [扩展系统](./docs/comparison/hook-plugin-extension-deep-dive.md) | 24 事件 + Prompt Hook vs 17 Hook 类型 |
| Skill 技能 | [技能系统](./docs/comparison/skill-system-deep-dive.md) | SKILL.md frontmatter vs Flow Skill vs Recipe |
| 长期记忆 | [项目指令](./docs/comparison/memory-system-deep-dive.md) | 4 层 CLAUDE.md vs AI memory_manager vs 跨格式读取 |

**工程实践：**

| 主题 | 文章 | 核心对比 |
|------|------|---------|
| 终端 UI | [UI 框架](./docs/comparison/terminal-ui-deep-dive.md) | Ink+React vs prompt_toolkit vs Rust 原生 vs GPU |
| Git 集成 | [版本控制](./docs/comparison/git-integration-deep-dive.md) | 自动提交归因 vs Esc 检查点 vs /rewind 三选项 |
| 测试反射 | [反射循环](./docs/comparison/test-reflection-deep-dive.md) | 3 次反射 vs 实际编译验证 vs 沙箱测试 |
| CI 模式 | [非交互](./docs/comparison/ci-scripting-deep-dive.md) | stream-json 协议 vs TTY 自动检测 vs 批量评估 |
| 遥测隐私 | [隐私实现](./docs/comparison/telemetry-privacy-deep-dive.md) | 782 事件 vs 零遥测 vs Opt-in 10% |
| 系统提示 | [Prompt 工程](./docs/comparison/system-prompt-deep-dive.md) | 8 模块硬编码 vs XML 结构 vs Jinja2 动态 |
| API 参数 | [重试策略](./docs/comparison/api-params-deep-dive.md) | 温度/重试/循环上限/缓存跨 Agent 对比 |

### Agent 间 1v1 对比

- [Claude Code vs Cursor](./docs/comparison/claude-code-vs-cursor.md) | [vs Copilot CLI](./docs/comparison/claude-code-vs-copilot-cli.md) | [Aider vs Goose](./docs/comparison/aider-vs-goose.md)
- [Qwen vs Claude Code](./docs/comparison/qwen-vs-claude-code.md) | [vs Gemini vs Kimi](./docs/comparison/qwen-vs-gemini-vs-kimi.md) | [OpenCode vs Qwen](./docs/comparison/opencode-vs-qwen-source.md)

<details><summary>Qwen Code 功能补全系列（5 篇）</summary>

- [对标 Claude Code](./docs/comparison/qwen-code-feature-gaps.md) | [对标 OpenCode](./docs/comparison/qwen-code-vs-opencode-feature-gaps.md) | [对标 Gemini CLI](./docs/comparison/qwen-code-vs-gemini-feature-gaps.md)
- [vs Kimi CLI 双向缺口](./docs/comparison/qwen-code-vs-kimi-feature-gaps.md) | [性能差距+改进路线图](./docs/comparison/claude-code-speed-qwen-improvements.md)
</details>

### 使用指南

**用户指南：**
- [Claude Code](./docs/guides/claude-code-user-guide.md) | [Copilot CLI](./docs/guides/copilot-cli-user-guide.md) | [Qwen Code](./docs/guides/qwen-code-user-guide.md) | [入门指南](./docs/guides/getting-started.md)

**实操：**
- [工作流教程](./docs/guides/workflows.md) | [配置示例](./docs/guides/config-examples.md) | [迁移指南](./docs/guides/migration.md) | [故障排查](./docs/guides/troubleshooting.md) | [高效提示词](./docs/guides/effective-prompts.md)

**深度配置：**
- [CLAUDE.md 写作](./docs/guides/writing-claude-md.md) | [AGENTS.md 配置](./docs/guides/agents-md.md) | [Skill 设计](./docs/guides/skill-design.md) | [Hooks 配置](./docs/guides/hooks-config.md)
- [上下文管理](./docs/guides/context-management.md) | [安全加固](./docs/guides/security-hardening.md)

### 参考文档

- **[架构原理](./docs/architecture/overview.md)** — 代理循环、MCP、上下文管理
- **[基准测试](./docs/benchmarks/overview.md)** — SWE-bench、Aider Benchmark、Terminal-Bench 等
- **[外部资源](./docs/resources.md)** — 视频教程、博客、论文、社区

---

## 架构流派（源码分析发现）

| 流派 | 代表 Agent | 核心模式 |
|------|---------|---------|
| **编辑优先** | Aider | LLM 直接输出代码修改（14 种格式），工具是辅助 |
| **工具调用** | Claude Code, Codex CLI, OpenCode, Cline, Goose | 结构化 function calling 操作环境 |
| **事件驱动** | OpenHands | EventStream 发布/订阅，最灵活但最复杂 |
| **ReAct 循环** | Gemini CLI, Qwen Code, SWE-agent | 思考→行动→观察→重复 |

## 技术栈分布

| 语言 | Agent | 特点 |
|------|-------|------|
| **Rust** | Goose, Claude Code, Warp | 性能最佳，内存最低 |
| **TypeScript** | Gemini CLI, Qwen Code, Codex CLI, Cline, Continue | Ink/React TUI 成熟，生态丰富 |
| **Go + TS** | OpenCode | Go 后端 + TypeScript TUI，SolidJS 响应式 |
| **Python** | Aider, SWE-agent, OpenHands, Kimi CLI | LiteLLM 100+ 模型，学术研究首选 |

## 性能基准（2026-03 实测 + SWE-bench）

### 启动性能（本机实测，2026-03-26）

| Agent | 版本 | 启动时间 | 安装大小 | 二进制类型 |
|-------|------|---------|---------|-----------|
| **Claude Code** | v2.1.84 | **50ms** | 225MB | Rust ELF x86-64 |
| **Copilot CLI** | v1.0.10 | **72ms** | 268MB | Node.js SEA |
| **Codex CLI** | — | **76ms** | 142MB | Node.js SEA |
| **Qwen Code** | v0.13.0 | **608ms** | 48MB | Node.js (npm) |
| **Gemini CLI** | v0.34.0 | **1.5s** | 509MB | Node.js (npm) |

> 测量方式：`time <agent> --version`，3 次取中位数。Gemini CLI 首次冷启动 4s，后续热启动 1.5s。Qwen Code 作为 Gemini CLI 分叉，安装大小仅 48MB（vs 上游 509MB），启动快 2.5 倍。

### 采用量（2026-03-26 实时数据）

| Agent | npm 周下载 | 增长趋势（4 周） | GitHub Stars | 总版本数 | 首次发布 |
|-------|-----------|----------------|-------------|---------|---------|
| **Claude Code** | **1,020 万** | 934→951→987→**1,020 万** ↑ | **83k** | 359 | 2025-02 |
| **Codex CLI** | **368 万** | 214→275→356→**368 万** ↑↑ | **68k** | 1,543 | 2025-04 |
| **Gemini CLI** | **74 万** | 76→66→73→**74 万** → | **99k** | 539 | 2025-06 |
| **Copilot CLI** | **64 万** | 19→25→42→**64 万** ↑↑↑ | **10k** | 588 | 2025-09 |
| **Qwen Code** | **8.4 万** | 6→16→11→**8.4 万** ↑ | **21k** | 353 | 2025-07 |

| Agent | PyPI 月下载 | GitHub Stars |
|-------|-----------|-------------|
| **OpenHands** | **125 万** | **70k** |
| **Aider** | **78 万** | **42k** |
| **Kimi CLI** | **45 万** | **7k** |
| **OpenCode** | — | **130k** |

> **关键洞察**：
> - Claude Code npm 周下载 **1020 万**，是第二名 Codex CLI（368 万）的 **2.8 倍**
> - Codex CLI 和 Copilot CLI 增长最快（4 周分别 ↑72%、↑240%）
> - Gemini CLI Stars（99k）远超下载量（74 万/周），实际采用率与热度不成比例
> - Qwen Code 周下载 8.4 万，与 Stars 21k 比例正常

*数据来源：[npm Registry API](https://api.npmjs.org/) 实时查询、[PyPI Stats](https://pypistats.org/)、`gh api` GitHub Stars*

### SWE-bench Verified（模型排行，2026-03）

| 模型 | SWE-bench Verified | 说明 |
|------|-------------------|------|
| Claude Opus 4.5 | **80.9%** | 排行榜第 1 |
| Gemini 3.1 Pro | **80.6%** | Google 最强 |
| GPT-5.2 | **80.0%** | OpenAI 最强 |
| Claude Sonnet 4.6 | **79.6%** | 中端模型接近旗舰 |
| Claude Code（Agent 框架） | **58.0%** | 作为 Agent 框架独立评分 |

*数据来源：[SWE-bench 排行榜](https://www.swebench.com/)、[npm](https://www.npmjs.com/)、[PyPI Stats](https://pypistats.org/)、`gh api` 实时查询*

---

## 附录

### 源码分析纠正的重要事实

| Agent | 官方/常见说法 | 源码实际情况 |
|------|-------------|-------------|
| **Goose** | TypeScript | **Rust**（55k 行） |
| **OpenCode** | Go | **Go + TypeScript**（混合 Monorepo，Go 后端 + TS TUI） |
| **Kimi CLI** | TypeScript | **Python**（68.8%） |
| **Qwen Code** | 原创 | **Gemini CLI 分叉**（大幅增强） |

### 本仓库的源码分析基础

本仓库的对比文档基于以下本地源码仓库的深度分析：

| 项目 | 实际语言 | 代码量 | 关键发现 |
|------|---------|--------|---------|
| Aider | Python | ~30k 行 | 14 种编辑格式，RepoMap AST |
| Goose | **Rust** | ~55k 行 | MCP 原生，58+ 提供商 |
| Gemini CLI | TypeScript | ~191k 行 | TOML 策略引擎，Qwen Code 上游 |
| Qwen Code | TypeScript | ~191k 行 | Gemini 分叉 + 多提供商 + Arena |
| OpenCode | **Go + TS** | ~983 TS + 359 TSX 文件 | 100+ Provider（models.dev）+ 37 LSP + ACP IDE |
| Cline | TypeScript | ~40k 行 | Git Checkpoint + 48 提供商 |
| SWE-agent | Python | ~20k 行 | ACI 设计 + Bundle 工具 |
| OpenHands | Python | ~60k 行 | EventStream + 多代理委托 |
| Continue | TypeScript | ~80k 行 | 语义索引 + PR Checks |
| Kimi CLI | **Python** | ~20k 行 | 双模式 Ctrl-X + Wire 协议 |

### 资源链接

- [awesome-cli-coding-agents](https://github.com/bradAGI/awesome-cli-coding-agents) — CLI 编程代理精选列表
- [SWE-bench](https://www.swebench.com/) — 软件工程基准测试
- [MCP 协议](https://modelcontextprotocol.io/) — 模型上下文协议标准

## 贡献

欢迎贡献！请查看 [CONTRIBUTING.md](./CONTRIBUTING.md) 了解指南。

## 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](./LICENSE)

---

**注意**：本项目与上述任何 Agent 无关联。信息基于源码分析，仅供参考。
