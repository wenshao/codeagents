# OpenCode

**开发者：** Anomaly Innovations（[anoma.ly](https://anoma.ly)）
**许可证：** MIT
**仓库：** [github.com/anomalyco/opencode](https://github.com/anomalyco/opencode)（npm: `opencode-ai`）
**网站：** [opencode.ai](https://opencode.ai/)
**Stars：** 约 11k+

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

## 技术架构（源码分析）

### Monorepo 结构

```
opencode/                     # 19 个包
├── packages/opencode/        # 核心 CLI/TUI 应用 + 代理后端
├── packages/app/             # Web 应用前端（SolidJS）
├── packages/console/         # 控制台（含 app/core/function/mail/resource 子模块）
├── packages/desktop/         # Tauri 桌面应用（Vite + SolidJS + Tauri v2）
├── packages/desktop-electron/# Electron 桌面应用
├── packages/sdk/js/          # JavaScript SDK
├── packages/ui/              # 共享 UI 组件库（含 37 种主题）
├── packages/plugin/          # 插件系统
├── packages/enterprise/      # 企业功能
├── packages/identity/        # 认证/身份
├── packages/extensions/      # 扩展支持
├── packages/containers/      # 容器相关
├── packages/slack/           # Slack 集成
├── packages/storybook/       # Storybook 组件文档
├── packages/docs/            # 文档
├── packages/web/             # Web 相关工具
├── packages/function/        # 函数处理
├── packages/util/            # 工具函数
└── packages/script/          # 构建和工具脚本
```

### 核心架构

```
客户端 (TUI / Web / Desktop-Tauri / Desktop-Electron)
    ↓
Hono HTTP 服务器 (localhost) + WebSocket + MDNS 服务发现
    ↓
代理系统 (Agent Layer) ← Skill 系统 / Plugin Hook
    ↓
Vercel AI SDK v5 → models.dev 动态模型注册 → 100+ LLM 提供商
    ↓
工具注册表 (18 工具) → 文件系统 / Shell / LSP / MCP
    ↓
SQLite (Drizzle ORM, WAL) + Git Snapshot (~/.local/share/opencode/snapshot/)
    ↓
远程工作区（实验性）← Adaptor + SSE 事件同步
```

### 技术栈
- **语言**：TypeScript 5.8
- **运行时**：Bun 1.3.11（主要）/ Node.js 22（兼容，已有入口和构建脚本）
- **TUI 框架**：OpenTUI + Solid.js（响应式信号驱动）
- **HTTP 框架**：Hono（轻量级）
- **数据库**：SQLite + Drizzle ORM（WAL 模式）+ Git 对象（快照）
- **AI SDK**：Vercel AI SDK v5（统一 LLM 接口）+ models.dev 动态模型数据
- **MCP SDK**：@modelcontextprotocol/sdk（StreamableHTTP / SSE / Stdio）
- **桌面**：Tauri v2（主要）+ Electron（备选）
- **类型安全框架**：Effect（函数式效果系统，核心服务逐步 Effect 化）

### 多代理系统

| 代理 | 类型 | 权限 | 用途 |
|------|------|------|------|
| **build** | 主代理 | 完全访问 + question + plan_enter | 默认代理，代码开发、文件编辑 |
| **plan** | 主代理 | 只读（edit deny）+ plan_exit | 代码分析、规划，只能写 plan 文件 |
| **general** | 子代理 | 受限（无 todo） | 复杂多步骤研究，可并行执行 |
| **explore** | 子代理 | 只读（grep/glob/list/read/bash/webfetch/websearch/codesearch） | 快速代码库搜索，支持 quick/medium/thorough |
| **compaction** | 隐藏 | 全部 deny | 会话压缩 |
| **title** | 隐藏 | 内部 | 自动标题生成 |
| **summary** | 隐藏 | 内部 | 自动摘要生成 |

- 支持通过 `opencode.json` 定义自定义代理（独立模型、温度、系统提示、最大步数）
- 子代理通过 `@general`、`@explore` 消息引用调用

### 工具系统

注册在 `registry.ts` 中的工具（14 无条件 + 4 有条件）：

| 工具 | 用途 | 条件 |
|------|------|------|
| **bash** | Shell 命令执行 | 始终可用 |
| **read** | 读取文件内容 | 始终可用 |
| **write** | 创建/覆写文件 | 始终注册，GPT-5+ 模型排除（改用 apply_patch） |
| **edit** | 精确字符串替换编辑 | 始终注册，GPT-5+ 模型排除（改用 apply_patch） |
| **glob** | 文件模式匹配搜索 | 始终可用 |
| **grep** | 正则内容搜索 | 始终可用 |
| **apply_patch** | Git 补丁格式应用 | 始终注册，仅 GPT-5+ 模型启用（替代 edit/write） |
| **websearch** | Web 搜索（Exa） | 需 opencode provider 或 OPENCODE_ENABLE_EXA |
| **codesearch** | 代码搜索（Exa） | 需 opencode provider 或 OPENCODE_ENABLE_EXA |
| **webfetch** | 抓取 Web 页面 | 始终可用 |
| **task** | 任务创建/更新/查询 | 始终可用 |
| **todowrite** | 待办写入 | 始终可用 |
| **skill** | 执行自定义 Skill | 始终可用 |
| **invalid** | 无效工具标记 | 始终可用 |
| **question** | 向用户提问 | 需客户端为 app/cli/desktop |
| **lsp** | LSP 语言服务交互 | 需 OPENCODE_EXPERIMENTAL_LSP_TOOL |
| **batch** | 批量工具执行 | 需 experimental.batch_tool = true |
| **plan_exit** | 退出 Plan 模式 | 需 OPENCODE_EXPERIMENTAL_PLAN_MODE + CLI |

此外，`ls`、`multiedit`、`todoread`、`plan_enter` 定义了工具文件但未注册到 registry，属于未启用/预留代码。

### 权限系统

```
规则优先级：远程 → 全局 → 项目 → .opencode → 内联
权限类型（config schema 定义）：
  read, edit, glob, grep, list, bash, task,
  external_directory, todowrite, todoread, question,
  webfetch, websearch, codesearch, lsp, doom_loop, skill
  + catchall（任意自定义 key）
操作：allow / deny / ask
```

- 基于 Tree-sitter 的 bash 命令 AST 解析，自动提取目录和操作
- `.env*` 文件默认 ask 确认（`.env.example` 除外）
- 外部目录默认 ask 确认
- Doom Loop 保护：连续权限拒绝自动中断
- Provider whitelist/blacklist：`enabled_providers` / `disabled_providers` 配置

### 工作区 & 协作系统

#### 远程工作区（实验性，`OPENCODE_EXPERIMENTAL_WORKSPACES`）

```
Control Plane ──SSE──→ Workspace Server ──git worktree──→ 隔离环境
     ↑                        ↓
GlobalBus ←── 文件变更/状态事件（10 秒心跳 + 自动重连）
```

- **Adaptor 模式**：可插拔的工作区类型，当前实现 worktree 适配器
- **Worktree 适配器**：基于 `git worktree`，随机人性化命名（如 "brave-cabin"）
- **Workspace Server**：独立 HTTP + SSE 服务，通过 `x-opencode-directory` header 路由请求
- 数据库表 `WorkspaceTable` 持久化工作区记录

#### Git-backed Session Review

- 基于 git 对象的快照系统，存储在 `~/.local/share/opencode/snapshot/{project_id}`（XDG data 目录）
- `git write-tree` 捕获状态，`git diff` 计算变更
- 侧面板支持 unified diff 和 split diff 两种视图
- 支持行内注释，懒加载 diff
- VCS 监听 `HEAD` 文件变更，发布 `BranchUpdated` 事件

#### Session Fork & Restore

- **Fork**：`Session.fork()` 创建新会话，复制目标消息前所有内容，保留消息关系映射
- **Restore-to-Message**：`SessionRevert.revert()` 收集目标消息后的所有 Patch，执行 `git checkout {hash} -- {file}` 恢复文件
- 支持 unrevert（撤销回退）和 cleanup（永久删除回退点后消息）

#### Session 分享

- `ShareNext.create()` → 云端 API 返回 `{ id, url, secret }`
- 订阅 GlobalBus 事件（session/message/part/diff），1 秒防抖批量同步
- 支持组织级 OAuth bearer token 认证
- 可通过 `OPENCODE_DISABLE_SHARE=true` 禁用

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

## CLI 命令

```bash
# 启动 TUI
opencode

# 非交互模式执行
opencode run "重构这个函数"

# 指定代理（如 plan 模式）
opencode --agent plan

# 仅启动 HTTP 服务器
opencode serve

# 启动工作区服务（实验性）
opencode workspace-serve

# 管理认证
opencode auth login anthropic

# 列出可用模型
opencode models

# 管理 MCP 服务器
opencode mcp list

# 管理代理
opencode agent list

# 会话管理
opencode session list

# 统计信息
opencode stats

# Web 控制台
opencode web

# 卸载
opencode uninstall
```

## 配置

```jsonc
// opencode.json 或 .opencode/opencode.json
{
  "agent": {
    "build": {
      "model": "anthropic/claude-sonnet-4"
    },
    // 自定义代理
    "my-agent": {
      "description": "Custom agent",
      "mode": "subagent",
      "model": "openai/gpt-5.4",
      "temperature": 0.7,
      "steps": 50
    }
  },
  "provider": {
    "anthropic": { "apiKey": "${ANTHROPIC_API_KEY}" },
    // 自定义 provider
    "my-local": {
      "api": "http://localhost:11434/v1",
      "models": {
        "llama3": { "id": "llama3" }
      }
    }
  },
  "plugin": ["opencode-plugin-example"],
  "permission": {
    "read": "allow",
    "edit": { "**": "allow", "*.env": "ask" },
    "bash": "ask",
    "external_directory": { "*": "ask" }
  },
  // Provider 白/黑名单
  "enabled_providers": ["anthropic", "openai"],
  "disabled_providers": ["groq"]
}
```

**配置优先级（低→高）**：
1. 远程 `.well-known/opencode`（企业）
2. 全局 `~/.config/opencode/opencode.json`
3. `OPENCODE_CONFIG` 环境变量
4. 项目 `opencode.json`
5. `.opencode/opencode.json`
6. `OPENCODE_CONFIG_CONTENT` 内联 JSON

## 使用场景

- **最适合**：需要多 LLM 提供商切换、深度 LSP 集成、插件扩展的开发者
- **适合**：终端原生工作流、多客户端需求、企业远程配置场景
- **不太适合**：追求简单开箱即用的用户、纯终端 TUI 且需要非英语 UI 的场景

## 资源链接

- [网站](https://opencode.ai/)
- [GitHub](https://github.com/anomalyco/opencode)
- [models.dev](https://models.dev) — 模型数据源
