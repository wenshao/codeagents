# 1. Gemini CLI 概述

**开发者：** Google
**许可证：** Apache-2.0
**仓库：** [github.com/google-gemini/gemini-cli](https://github.com/google-gemini/gemini-cli)（npm: `@google/gemini-cli`）
**文档：** [geminicli.com](https://geminicli.com)
**Stars：** ~99k（100+ 贡献者，12.5k Forks）
**最后更新：** 2026-03

## 概述

Gemini CLI 是 Google 官方的开源 AI 编程代理，运行在终端中，基于 TypeScript + Ink/React 19 构建。采用 ReAct 模式驱动代理循环，主循环最多 100 轮对话，子代理默认 30 轮/10 分钟。项目于 2025 年 6 月 25 日首次公开发布（v0.1.0），当前稳定版为 v0.34.0（2026-03-17），采用每周二稳定/预览/夜间三通道发布模式。整体代码量约 22 万行 TypeScript（不含测试，含测试约 53 万行），是 GitHub 上增长最快的开源项目之一（不到一年从 0 到 ~99k Stars）。它也是 Qwen Code 的上游项目，其架构被广泛借鉴。

## 核心功能

### 基础能力
- **ReAct 代理循环**：推理 + 行动模式，主循环最多 100 轮，子代理默认 30 轮/10 分钟
- **23 种内置工具**（17 核心 + 6 任务追踪）：文件读写、编辑、Bash 执行、Grep 搜索、Web 搜索/抓取、记忆、规划、技能、任务追踪等
- **5 个内置代理**：generalist（通用）、codebase_investigator（代码库分析）、memory_manager（记忆管理）、cli_help（帮助）、browser（浏览器自动化）
- **MCP 支持**：完整的模型上下文协议（Stdio/SSE 传输），支持 OAuth 认证
- **事件驱动调度器**：并发工具调用，状态机管理生命周期（Validating → Scheduled → AwaitingApproval → Executing → Success/Error/Cancelled）
- **TOML 策略引擎**：灵活的权限控制，支持通配符和正则匹配，四种审批模式
- **11 种 Hook 事件**：BeforeTool、AfterTool、BeforeAgent、AfterAgent、BeforeModel、AfterModel、BeforeToolSelection、Notification、SessionStart、SessionEnd、PreCompress
- **扩展系统**：Git/Local/GitHub Release 安装，扩展可贡献 MCP 服务器、工具、主题、技能、代理、策略规则
- **流式输出**：实时显示 LLM 推理和工具执行结果
- **会话管理**：UUID 会话、压缩、恢复、检查点、回退（Rewind）
- **17 种内置主题**：Dark（9 种：Ayu Dark、Atom One Dark、Dracula、GitHub Dark、Solarized Dark 等）+ Light（7 种：Google Code、GitHub Light、Xcode 等）+ NoColor，支持自定义主题
- **多种沙箱**：macOS Seatbelt、Linux Bubblewrap/Seccomp、Docker、Podman、gVisor（runsc）、LXC、Windows Sandbox

### 独特功能
- **策略引擎（Policy Engine）**：TOML 格式的策略文件，支持优先级、通配符、正则参数匹配、工具注解匹配、审批模式过滤
- **安全检查器**：内置 `allowed-path`（路径验证）和 `conseca`（语义安全检查）+ 可外挂进程级安全检查
- **模型路由器**：7 种可插拔路由策略（Override、Fallback、ApprovalMode、Classifier、NumericalClassifier、Composite、Default），动态模型选择
- **检查点 & 回退（Checkpoint & Rewind）**：基于 Git 快照的检查点系统，`Esc Esc` 快速回退，带影响分析和确认 UI
- **浏览器代理**：Puppeteer 驱动的 Web 自动化代理，支持导航、点击、截图分析、域名限制
- **Token 缓存**：自动优化后续请求中的缓存 Token，减少处理量（API Key 用户可用）
- **A2A 服务器**：实验性 Agent-to-Agent 协议支持，Express.js 实现，HTTP/JSON 通信
- **Headless 模式**：CI/GitHub Actions/非 TTY 环境自动激活，支持 `-p` 标志
- **`.geminiignore`**：类似 `.gitignore` 的文件过滤，支持 glob、目录、否定模式
- **Qwen Code 上游**：其架构被阿里云 Qwen Code 分叉和扩展

## Monorepo 结构

```
gemini-cli/                              # 7 个包
├── packages/cli/                        # 终端 UI（Ink + React 19），斜杠命令，TUI 组件
├── packages/core/                       # 核心引擎（代理、工具、策略、调度器、认证、Hook、路由、遥测）
├── packages/sdk/                        # 公共 SDK（编程式使用，导出 Config、Agent 等核心类型）
├── packages/a2a-server/                 # Agent-to-Agent 实验协议（Express.js 5.x）
├── packages/devtools/                   # 开发工具（WebSocket 服务器，DevTools 客户端通信）
├── packages/vscode-ide-companion/       # VS Code 扩展（Diff 编辑器，工作区上下文，需 VS Code 1.99+）
├── packages/test-utils/                 # 测试工具（node-pty 终端模拟，mock 实现）
├── evals/                               # 行为评估（25 个评估套件）
├── integration-tests/                   # 集成测试（Docker/Podman 沙箱）
├── schemas/                             # JSON Schema 定义
├── sea/                                 # Single Executable Application 构建
└── scripts/                             # 构建和发布脚本
```

## 安装

```bash
# npm（全局安装）
npm install -g @google/gemini-cli

# npx（免安装运行）
npx @google/gemini-cli

# Homebrew（macOS/Linux）
brew install gemini-cli

# MacPorts（macOS）
sudo port install gemini-cli

# Conda（受限环境）
conda install -c conda-forge gemini-cli

# 启动（首次会引导认证）
gemini
```

**发布通道**：
- **Stable**：每周二 UTC 20:00，完全验证
- **Preview**：每周二 UTC 23:59，已测试但未完全验证
- **Nightly**：每日 UTC 00:00，main 分支最新代码

## 支持的模型

| 模型系列 | 说明 |
|----------|------|
| **Gemini 3.1 Pro** | 最新预览模型（v0.31.0+ 可用） |
| **Gemini 3 Pro** | v0.29.0 起为所有用户默认模型 |
| **Gemini 3 Flash** | 轻量级快速模型（子代理默认使用） |
| **Gemini 2.5 Flash** | 上一代快速模型 |
| **Gemini 2.5 Pro** | 上一代专业模型 |
| **Gemini 2.0 Flash** | 基础模型（免费 API Key 用户可用） |

- 模型路由器根据任务复杂度自动在 Flash/Pro 间切换（v0.12.0+）
- 通过 `/model` 命令手动切换模型
- 1M Token 上下文窗口（Pro 模型）
- **仅支持 Gemini 系列模型**，Google 官方拒绝了所有第三方模型后端 PR

## 优势

1. **Google 官方**：第一方支持，与 Gemini 模型深度集成，1M Token 上下文
2. **极高免费额度**：Google 账号登录 1000 req/day/user，远超竞品
3. **架构优雅**：事件驱动调度器 + 声明式工具 + 可插拔策略引擎 + Hook 系统
4. **策略系统强大**：TOML 策略文件 + 双安全检查器 + 四种审批模式 + 优先级排序
5. **扩展生态**：v0.8.0 起支持扩展系统，官方和社区扩展丰富
6. **多代理架构**：5 个内置代理 + 自定义代理 + 远程 A2A 代理
7. **丰富沙箱**：7 种沙箱后端（Seatbelt/Bubblewrap/Docker/Podman/gVisor/LXC/Windows Sandbox）
8. **检查点 & 回退**：基于 Git 快照的安全网，`Esc Esc` 即时回退
9. **开源**：Apache-2.0 许可，~99k Stars，代码质量高
10. **生态影响力大**：Qwen Code 基于此分叉，众多社区衍生项目

## 劣势

1. **单模型锁定**：仅支持 Gemini 系列模型，Google 明确拒绝多模型支持
2. **文件编辑可靠性**：社区反映编辑操作有时会覆写文件而非精确编辑，消耗过多 Token
3. **速率限制问题**：用户报告在 29% 配额时即被限流，滥用缓解措施按许可类型优先排序
4. **认证复杂**：Code Assist 许可有时无法被 OAuth 识别
5. **无多客户端**：仅终端 TUI，无 Web 或桌面应用
6. **社区规模**：虽 Stars 高但活跃开发者社区比 Claude Code 小
7. **Git 集成问题**：偶有未经请求的 `git add` 非跟踪文件
8. **功能迭代快**：API 和功能变化较快，文档可能滞后

## 使用场景

- **最适合**：Google Cloud 用户、需要大免费额度的开发者、Gemini 1M 上下文场景
- **适合**：需要策略引擎精细控制的安全敏感场景、CI/CD 自动化（Headless 模式）
- **不太适合**：需要多模型切换的用户、非 Google 生态用户、需要 Web/桌面客户端的用户

## 定价/配额

| 计划 | 价格 | 请求限制 | 可用模型 |
|------|------|---------|---------|
| **Google 账号登录** | 免费 | 1,000 req/day, 60/min | Gemini Pro + Flash |
| **Gemini API Key（免费）** | 免费 | 250 req/day, 10/min | Flash only |
| **Code Assist Standard** | 付费 | 1,500 req/day, 120/min | Pro + Flash |
| **Code Assist Enterprise** | 付费 | 2,000 req/day, 120/min | Pro + Flash |
| **Vertex AI** | 按量付费 | 按 Token 计费 | 全系列 |
| **AI Pro / AI Ultra 订阅** | 固定月费 | 更高限额 | Pro + Flash |
| **Vertex AI Express Mode** | 90 天免费试用 | 试用期限额 | 全系列 |

## 项目演进（2025.06 — 2026.03）

### 里程碑时间线

| 版本 | 日期 | 里程碑 |
|------|------|--------|
| **v0.1.0** | 2025-06-25 | **首次公开发布**，基础代理循环 + 文件工具 + Shell 执行 |
| v0.1.14 | 2025-07-25 | **P1 安全修复**：提示注入/命令劫持漏洞修复 |
| **v0.4.0** | 2025-09-01 | CloudRun + Security 扩展，智能编辑工具 |
| **v0.6.0** | 2025-09-15 | 数据库扩展（AlloyDB、BigQuery、Cloud SQL 等），聊天分享，提示历史 |
| **v0.8.0** | 2025-09-29 | **扩展系统上线**，geminicli.com 文档站 |
| **v0.9.0** | 2025-10-06 | **交互式 Shell**（vim、rebase、嵌套 gemini） |
| **v0.12.0** | 2025-10-27 | **模型路由**（Flash vs Pro），`/model` 命令，子代理 |
| **v0.16.0** | 2025-11-10 | **Gemini 3 模型发布** |
| v0.19.0 | 2025-11-24 | Zed 编辑器集成 |
| **v0.22.0** | 2025-12-22 | 免费层 Gemini 3 访问，预装到 Google Colab |
| **v0.23.0** | 2026-01-07 | **Agent Skills**（实验性） |
| **v0.26.0** | 2026-01-27 | Agent Skills 默认启用 |
| v0.28.0 | 2026-02-10 | Positron IDE 支持 |
| **v0.29.0** | 2026-02-17 | **Plan Mode**，Gemini 3 成为所有用户默认模型 |
| **v0.30.0** | 2026-02-25 | **SDK 包**，策略引擎 |
| v0.31.0 | 2026-02-27 | Gemini 3.1 Pro 预览，实验性浏览器代理 |
| v0.33.0 | 2026-03-11 | 远程代理 HTTP 认证（A2A） |
| **v0.34.0** | 2026-03-17 | Plan Mode 默认启用，原生 gVisor + LXC 沙箱 |
| v0.36.0-preview | 2026-03-24 | 最新预览版（Linux Bubblewrap/Seccomp 沙箱等） |

不到一年发布 **36 个主要版本**，从零开始成长为 ~99k Stars 的顶级开源项目。

### 开发节奏
- **总提交数**：8,910+
- **活跃开发天数**：339 天
- **峰值日**：2026-03-19（152 次提交）
- **发布频率**：每周稳定版 + 每日夜间版
- **Google Summer of Code 2026**：4 个项目被接受（性能监控、行为评估、测试套件优化、长上下文评估数据集）

### 与 Qwen Code 的关系

Qwen Code 是 Gemini CLI 的分叉项目（Apache-2.0 合法），继承了：
- 代理循环架构（GeminiClient + Scheduler）
- 工具系统（声明式工具 + 注册表）
- 策略/权限模型
- Ink + React 终端 UI
- MCP 集成
- 会话管理

## 资源链接

- **仓库**：[github.com/google-gemini/gemini-cli](https://github.com/google-gemini/gemini-cli)
- **文档站**：[geminicli.com](https://geminicli.com)
- **npm**：[@google/gemini-cli](https://www.npmjs.com/package/@google/gemini-cli)

## 社区生态

### 主要分叉
- **Qwen Code**（`QwenLM/qwen-code`）：阿里云官方分叉，使用 Qwen3-Coder-480B，增加多提供商支持、免费 OAuth、6 语言国际化
- **LLxprt Code**：社区分叉，支持 Ollama/OpenAI/Anthropic/OpenRouter 多模型
- **qwen_cli_coder**、**easy-llm-cli**、**open-gemini-cli**、**ollama-code**：各类社区多模型分叉

### 社区项目
- **awesome-gemini-cli**（Piebald-AI）：扩展和资源精选列表
- **Tars**：本地优先长时间自主代理编排
- **hcom**：跨终端代理间消息通信
- **Gemini-flow**：多代理工作流
- **nvim Gemini Companion / gemini-cli.nvim**：Neovim 集成
- **iFlow CLI**：仓库分析 + 复杂工作流自动化

### 官方扩展
CloudRun、Security、Hugging Face、Monday.com、ElevenLabs、Jules、Conductor、Endor Labs、Data Commons，以及 AlloyDB、BigQuery、Cloud SQL 等数据库扩展。

### 社区活动
- **GitHub Discussions**：22,000+ 讨论
- **Google Summer of Code 2026**：4 个项目被接受
- 100+ 贡献者，活跃的 PR 周转
