# 1. OpenCode 概述

**开发者：** Anomaly Innovations（[anoma.ly](https://anoma.ly)）
**许可证：** MIT
**仓库：** [github.com/anomalyco/opencode](https://github.com/anomalyco/opencode)（npm: `opencode-ai`）
**网站：** [opencode.ai](https://opencode.ai/)
**Stars：** ~12k（项目已于 2025-09 归档，后续项目为 Crush）
**最后更新：** 2026-03

## 概述

OpenCode 是一个功能丰富的 AI 编程平台。最初以 Go 项目知名，当前版本已完全重写为 TypeScript monorepo 架构，提供 TUI、Web 控制台和桌面应用（Tauri + Electron 双平台）三种客户端形态。其核心特色是多代理系统、插件 / Hook 架构、37 种主题、丰富的 LSP / Formatter 集成，以及通过 models.dev 动态加载 100+ LLM 提供商的统一支持。当前版本为 v1.3.0。

## 核心功能

### 基础能力
- **多客户端**：TUI（终端）、Web 控制台、桌面应用（Tauri + Electron 双平台）
- **多代理系统**：build、plan、general、explore 等 7 个内置代理，支持自定义
- **18 种内置工具**（14 无条件 + 4 有条件）：文件编辑、Bash 执行、Grep/Glob 搜索、Web 抓取/搜索、代码搜索、Skill、Task、Todo、apply_patch 等；有条件工具包括 Question（需客户端支持）、LSP（实验性）、Batch（实验性）、PlanExit（实验性 + CLI）
- **100+ LLM 提供商**：通过 [models.dev](https://models.dev) + Vercel AI SDK 动态加载（目前 models.dev 提供 104 个 provider），其中 11 个在代码中定义为 well-known：OpenCode、Anthropic、OpenAI、Google、Google Vertex、Amazon Bedrock、Azure、OpenRouter、Mistral、GitHub Copilot、GitLab
- **MCP 支持**：完整的模型上下文协议集成（StreamableHTTP / SSE / Stdio），支持 OAuth 认证
- **37 种 LSP 服务器**：TypeScript、Deno、Python (Pyright + Ty)、Go (gopls)、Rust (rust-analyzer)、Java (JDTLS)、C/C++ (clangd)、C#、F#、Ruby、Elixir、Zig (zls)、Kotlin、Swift (sourcekit-lsp)、Haskell、Dart、OCaml、Lua、PHP (Intelephense)、Bash、Terraform、LaTeX (texlab)、Dockerfile、Gleam、Clojure、Nix (nixd)、Typst (tinymist)、Julia、Vue、Svelte、Astro、Prisma、YAML、ESLint、Biome、OxLint
- **26 种 Formatter**：Prettier、Biome、gofmt、mix (Elixir)、oxfmt、shfmt、latexindent、zig、clang-format、ktlint、ruff (Python)、air (R)、uv (Python)、rubocop (Ruby)、standardrb (Ruby)、htmlbeautifier (Ruby)、dart、ocamlformat、terraform、gleam、nixfmt、rustfmt、pint (PHP)、ormolu (Haskell)、cljfmt (Clojure)、dfmt (D)
- **SQLite 持久化**：Drizzle ORM，会话/消息完整存储，WAL 模式
- **37 种主题**：Nord、Catppuccin (3 variants)、Gruvbox、Kanagawa、Tokyo Night、Dracula、Monokai、One Dark、AMOLED、Ayu、Flexoki、Solarized、Rose Pine、Vercel、Material 等

### 独特功能
- **插件 / Hook 系统**：基于 Hook 的可扩展架构，支持 npm 包和文件插件。Hook 类型包括 event、config、auth、tool（工具定义）、tool.definition（修改工具描述/参数）、tool.execute.before/after、chat.message、chat.params、chat.headers、permission.ask、command.execute.before、shell.env、experimental.chat.messages.transform、experimental.chat.system.transform、experimental.session.compacting、experimental.text.complete 共 17 种
- **Skill 系统**：原生 Agent Skill，带权限系统和 per-agent 过滤
- **Tree-sitter Bash 分析**：AST 解析 bash 命令，智能权限判断
- **Doom Loop 保护**：检测连续 3 次权限拒绝，自动中断无限循环
- **文件时间锁**：检测编辑期间文件被外部修改，防止冲突
- **会话压缩**：长对话自动压缩（auto-compact），支持配置化开关和 compacting hook
- **Git Worktree 隔离**：每个会话可使用独立 worktree
- **远程工作区**（实验性）：Adaptor 模式 + SSE 实时同步，支持 `workspace-serve` 命令
- **Session Fork & Restore**：从任意消息点分叉会话，或回退到历史消息并恢复文件状态
- **Git-backed Session Review**：基于 git 快照的变更追踪，侧面板 diff 可视化，支持行内注释
- **Session 分享**：同步会话到云端生成公开链接，支持增量同步和 SSR 渲染的 diff

## 安装

```bash
# npm / pnpm / bun
npm install -g opencode-ai

# Homebrew（推荐使用官方 tap）
brew install anomalyco/tap/opencode

# Scoop (Windows)
scoop install opencode

# Arch Linux
sudo pacman -S opencode

# 或使用安装脚本
curl -fsSL https://opencode.ai/install | bash
```

## 支持的模型

| 提供商 | 模型示例 | 说明 |
|--------|---------|------|
| Anthropic | Claude 4.5 Sonnet, Opus 4 | 专有 beta 头支持 |
| OpenAI | GPT-4, GPT-5.4, o1 | 完整支持 + apply_patch |
| Google | Gemini (Generative AI + Vertex AI) | 双通道 |
| Amazon | Bedrock | 企业级 |
| Azure | Azure OpenAI + Cognitive Services | 企业 |
| xAI | Grok | Responses API |
| Mistral, Groq, Cohere | 各类模型 | 通过统一接口 |
| DeepInfra, Cerebras, Together AI | 各类模型 | OpenAI 兼容 |
| Perplexity, OpenRouter | 各类模型 | 多模型聚合 |
| Cloudflare | Workers AI + AI Gateway | 边缘推理 |
| SAP | AI Core | 企业级 |
| GitHub Copilot | 集成模型 | 插件认证 |
| GitLab | Agent Platform | 插件认证 + workflow model discovery |
| 自定义 | OpenAI 兼容端点 | 本地/私有部署 |

模型数据通过 [models.dev](https://models.dev) API 动态拉取，自动获取最新模型信息和定价。

## 优势

1. **真正的多提供商**：100+ LLM 提供商通过 Vercel AI SDK + models.dev 动态统一接入
2. **多客户端架构**：TUI + Web + 桌面（Tauri + Electron），共享同一后端
3. **插件 + Skill 生态**：Hook 系统 + npm 插件 + MCP 服务器 + Agent Skill
4. **智能权限**：Tree-sitter bash AST 分析 + Doom Loop 保护 + 文件时间锁
5. **深度语言支持**：37 种 LSP 服务器 + 26 种 Formatter，覆盖主流和小众语言
6. **Git-native 协作**：快照 review、session fork/restore、远程工作区
7. **TypeScript 全栈**：类型安全，Zod 验证 + Effect 框架贯穿全栈
8. **丰富的主题**：37 种精心设计的主题
9. **开源 MIT**：企业友好许可

## 劣势

1. **架构复杂**：19 个包的 Monorepo + 多客户端，学习曲线较陡
2. **Bun 依赖**：主要运行时非 Node.js 主流（已有 Node.js 兼容入口）
3. **部分功能实验性**：远程工作区、batch tool、LSP tool 仍在实验阶段
4. **TUI 无国际化**：TUI 界面仅英文，但 Web/桌面应用支持 16 种 UI 语言（中/英/日/韩/德/法/西/俄/阿拉伯/土耳其等）
5. **模型数据外部依赖**：模型信息来自 models.dev，离线场景需预缓存（但构建时会生成 snapshot）

## 使用场景

- **最适合**：需要多 LLM 提供商切换、深度 LSP 集成、插件扩展的开发者
- **适合**：终端原生工作流、多客户端需求、企业远程配置场景
- **不太适合**：追求简单开箱即用的用户、纯终端 TUI 且需要非英语 UI 的场景

## 付费计划

| 计划 | 价格 | 包含内容 |
|------|------|---------|
| **免费 / 开源** | $0 | 自带 API Key 使用任意 provider |
| **OpenCode Zen** | 按量付费（余额 < $5 时自动充值 $20） | 针对编码代理优化的模型列表，月度消费限额 |
| **OpenCode Go** | $5 首月 → $10/月 | GLM-5、Kimi K2.5、MiniMax M2.5/M2.7；US/EU/SG 多区域 |

## 企业功能

- **集中配置**：通过 `.well-known/opencode` 远程下发组织级配置
- **SSO 集成**：对接现有身份管理系统
- **内部 AI 网关**：所有请求只走内部基础设施
- **数据安全**：不存储代码和上下文数据
- **禁用分享**：可为合规需求关闭 /share 功能
- **私有 NPM Registry**：支持企业内部 npm 仓库（bun .npmrc）
- **按席位定价**

## 社区生态

- **454 贡献者**，500 万月活开发者
- **社区插件**：opencode-helicone-session（Helicone 追踪）等
- **社区项目**：Remote-OpenCode（通过 Discord 远程控制）、agent-of-empires（多代理会话管理）
- **安全事件**：曾披露未认证 RCE 漏洞（任何网站可在 OpenCode 安装的机器上执行任意代码），已修复

## 资源链接

- [网站](https://opencode.ai/)
- [GitHub](https://github.com/anomalyco/opencode)
- [Changelog](https://opencode.ai/changelog)
- [桌面下载](https://opencode.ai/download)（Beta）
- [models.dev](https://models.dev) — 模型数据源
- [ACP 文档](https://opencode.ai/docs/acp/)
- [Zen 计划](https://opencode.ai/zen)
- [Go 计划](https://opencode.ai/go)
