# 1. Kimi CLI 概述

**开发者：** Moonshot AI（[月之暗面](https://www.moonshot.cn/)）
**许可证：** Apache 2.0
**仓库：** [github.com/MoonshotAI/kimi-cli](https://github.com/MoonshotAI/kimi-cli)（PyPI: `kimi-cli`）
**文档：** [moonshotai.github.io/kimi-cli](https://moonshotai.github.io/kimi-cli/en/)（英/中双语）
**Stars：** 7k+
**最后更新：** 2026-03

## 概述

Kimi Code CLI 是月之暗面推出的 AI 编程终端代理，**主要用 Python 编写**（Python 3.12+），采用 monorepo 工作区架构（kosong LLM 抽象、PyKAOS OS 抽象、kimi-code 核心）。核心特色是双模式交互（Agent + Shell，Ctrl-X 切换）、Wire 事件流协议支持多客户端（TUI、Web、IDE）、完整的子代理系统（coder/explore/plan）、以及插件系统和 Skill 系统。支持 Kimi、OpenAI、Anthropic、Google Gemini、Vertex AI 等多个 LLM 提供商。当前版本为 v1.25.0。

## 核心功能

### 基础能力
- **多客户端**：TUI 终端（prompt-toolkit + Rich）、Web UI（FastAPI + React）、IDE（ACP 协议）、Wire 模式（自定义 UI）
- **多代理系统**：default、coder、explore、plan 等 4+ 内置代理，支持前台/后台运行和会话内持久化
- **17+ 内置工具**（默认代理 17 种，另有 Think 和 SendDMail 在特定代理中启用）：文件操作（ReadFile/WriteFile/StrReplaceFile/Glob/Grep/ReadMediaFile）、Shell 执行（前台/后台）、Web 搜索/抓取（Moonshot API）、子代理委派（Agent）、结构化提问（AskUserQuestion）、任务管理（SetTodoList/TaskList/TaskOutput/TaskStop）、规划（EnterPlanMode/ExitPlanMode）
- **多提供商**：Kimi（默认）、OpenAI（Legacy + Responses）、Anthropic、Google Gemini（GenAI）、Vertex AI，通过环境变量可自定义端点
- **MCP 支持**：完整的 Model Context Protocol 集成（stdio + HTTP），支持 OAuth 认证、后台并行加载、工具超时配置
- **插件系统**（v1.25.0 新增）：`plugin.json` 声明式插件，子进程隔离执行，自动凭证注入
- **Skill 系统**：标准 Skill（SKILL.md 指令）和 Flow Skill（Mermaid/D2 流程图），多层发现（builtin → user → project）
- **会话持久化**：Wire JSONL 格式存储，可导出/恢复/重放

### 独特功能
- **双模式交互**：Agent 模式（AI 处理）与 Shell 模式（直接执行），Ctrl-X 无缝切换，Wire 协议维持上下文
- **Wire 事件流协议**：统一的客户端-服务器通信协议（v1.6），支持 WebSocket 实时推送，可用于构建自定义 UI
- **ACP（Agent Client Protocol）**：IDE 编辑器原生集成，支持 Zed、VS Code、JetBrains、Neovim
- **子代理系统**：可生成持久化子代理实例（coder/explore/plan），前台或后台运行，自动结果摘要
- **D-Mail 时间回溯**：发送消息到过去的检查点，回滚上下文到指定状态（实验性，okabe 代理）
- **后台任务管理**：Shell 命令和子代理支持后台执行，完整的任务生命周期管理（创建/监控/停止）
- **Moonshot 服务**：集成 Moonshot Search 和 Fetch API 提供高质量搜索和网页解析
- **扩展思维模式**：支持 thinking / always_thinking 深度推理能力
- **上下文压缩**：基于 LLM 的自动摘要压缩，可配置触发比例（默认 85%）和保留空间
- **Plan 模式**：只读分析阶段，生成结构化计划文件，支持多选项方案和增量编辑
- **Steer Input**：在代理运行时发送跟进消息引导方向，无需等待当前回合结束
- **Prompt Flow**：基于 Mermaid/D2 流程图的代理工作流编排，支持分支和迭代

## Monorepo 结构

```
kimi-cli/                          # Python monorepo (uv 工作区)
├── src/kimi_cli/                  # 主应用
│   ├── __main__.py                # CLI 入口
│   ├── app.py                     # KimiCLI 核心编排器（工厂模式）
│   ├── config.py                  # Pydantic 2 配置（TOML）
│   ├── llm.py                     # LLM 提供商工厂
│   ├── session.py                 # 会话状态管理
│   ├── agents/                    # 代理规格（YAML + Jinja2 系统提示）
│   │   ├── default/               # 默认代理族
│   │   │   ├── agent.yaml         # 主代理（全部工具）
│   │   │   ├── coder.yaml         # 软件工程子代理
│   │   │   ├── explore.yaml       # 只读探索子代理
│   │   │   ├── plan.yaml          # 架构规划子代理
│   │   │   └── system.md          # Jinja2 系统提示模板
│   │   └── okabe/                 # 实验代理（含 D-Mail）
│   ├── soul/                      # 核心运行时
│   │   ├── kimisoul.py            # 代理循环引擎
│   │   ├── agent.py               # 运行时配置和代理加载
│   │   ├── toolset.py             # 工具注册和 MCP 加载
│   │   ├── context.py             # 上下文历史和检查点
│   │   ├── approval.py            # 审批系统
│   │   ├── compaction.py          # 上下文压缩
│   │   ├── denwarenji.py          # D-Mail 状态机
│   │   ├── slash.py               # Soul 级斜杠命令
│   │   └── dynamic_injection.py   # 动态提示注入
│   ├── tools/                     # 17+ 内置工具
│   │   ├── agent/                 # 子代理委派
│   │   ├── shell/                 # Shell 执行（前台/后台）
│   │   ├── file/                  # 文件操作（6 种工具）
│   │   ├── web/                   # Web 搜索/抓取（Moonshot）
│   │   ├── ask_user/              # 结构化提问
│   │   ├── background/            # 后台任务管理（3 种工具）
│   │   ├── todo/                  # 任务列表
│   │   ├── think/                 # 内部推理
│   │   ├── plan/                  # Plan 模式（进入/退出）
│   │   └── dmail/                 # D-Mail 时间回溯
│   ├── subagents/                 # 子代理系统
│   │   ├── models.py              # AgentTypeDefinition, ToolPolicy
│   │   ├── registry.py            # LaborMarket（子代理类型注册表）
│   │   ├── runner.py              # 前台/后台执行器
│   │   └── store.py               # 实例持久化存储
│   ├── wire/                      # Wire 事件流协议
│   │   ├── types.py               # 30+ 事件/请求/响应类型
│   │   ├── server.py              # WebSocket 服务器
│   │   └── jsonrpc.py             # JSON-RPC 支持
│   ├── ui/                        # 多 UI 前端
│   │   ├── shell/                 # TUI（prompt-toolkit + Rich）
│   │   ├── print/                 # 非交互模式（脚本/CI）
│   │   ├── acp/                   # ACP IDE 集成
│   │   └── wire/                  # Wire 事件流模式
│   ├── acp/                       # ACP 服务器组件
│   ├── web/                       # Web UI（FastAPI + React）
│   ├── skill/                     # Skill 系统（标准 + Flow）
│   ├── plugin/                    # 插件系统
│   ├── approval_runtime/          # 统一审批运行时
│   ├── background/                # 后台任务运行时
│   └── prompts/                   # 共享提示模板
├── packages/
│   ├── kosong/                    # LLM 抽象层
│   ├── kaos/                      # OS 抽象层（本地/SSH）
│   └── kimi-code/                 # 核心代理包
├── sdks/kimi-sdk/                 # TypeScript SDK
├── docs/                          # VitePress 文档（英/中）
├── tests/                         # pytest 测试套件
├── tests_ai/                      # AI 集成测试
└── klips/                         # Kimi CLI Improvement Proposals
```

## 安装

```bash
# 安装脚本（推荐）
curl -LsSf https://code.kimi.com/install.sh | bash   # Linux/macOS
Invoke-RestMethod https://code.kimi.com/install.ps1 | Invoke-Expression  # Windows

# 使用 uv
uv tool install --python 3.13 kimi-cli

# 使用 pip
pip install kimi-cli

# Nix
nix profile install github:MoonshotAI/kimi-cli#kimi-cli

# 验证
kimi --version

# 首次使用（引导 OAuth 认证）
kimi
```

**独立二进制**：提供 Windows、macOS（含代码签名和公证）、Linux（x86_64 + ARM64）的 PyInstaller 打包二进制。

## 支持的模型

| 提供商 | 模型 | 说明 |
|--------|------|------|
| **Kimi** | kimi-k2.5, kimi-for-coding | 默认，多模态，集成 Moonshot 搜索/抓取服务 |
| OpenAI | GPT-4, GPT-4o, GPT-5+ | Legacy 和 Responses 两种 API 模式 |
| Anthropic | Claude Sonnet/Opus | 支持 thinking 模式，session_id 作为 user_id |
| Google Gemini | Gemini (GenAI API) | 标准支持 |
| Vertex AI | Gemini (Vertex AI API) | 企业级，独立 provider type |

**模型能力标记**：`image_in`（图片输入）、`video_in`（视频输入）、`thinking`（可选深度推理）、`always_thinking`（始终深度推理）

**环境变量覆盖**：
```bash
KIMI_BASE_URL, KIMI_API_KEY, KIMI_MODEL_NAME, KIMI_MODEL_MAX_CONTEXT_SIZE, KIMI_MODEL_CAPABILITIES
OPENAI_BASE_URL, OPENAI_API_KEY
# 类似的覆盖可用于其他提供商
```

## 优势

1. **双模式交互**：Agent + Shell 无缝切换，开发和执行一体化，效率极高
2. **Wire 协议**：统一事件流协议，支持 TUI/Web/IDE/自定义 UI 四种客户端形态
3. **子代理系统**：coder/explore/plan 三种专业化子代理，前台/后台运行，自动结果摘要
4. **Moonshot 集成**：原生搜索和网页抓取服务，高质量中文支持
5. **扩展思维**：支持深度推理模式（thinking/always_thinking）
6. **Python 生态**：Pydantic 2 类型安全，FastAPI Web 服务器，asyncio 并发
7. **多提供商**：不锁定 Kimi，支持 OpenAI、Anthropic、Google Gemini、Vertex AI
8. **Plan 模式**：结构化规划-执行分离，支持多方案选择
9. **Web UI**：功能丰富的浏览器界面，支持远程访问和多会话
10. **ACP 集成**：原生 IDE 集成（VS Code、Zed、JetBrains、Neovim）
11. **完整的后台任务管理**：Shell 命令和子代理的后台执行、监控、停止
12. **插件 + Skill 生态**：声明式插件 + 标准/流程 Skill，多层发现

## 劣势

1. **社区规模**：与 OpenCode（~133k Stars）、Gemini CLI（~100k Stars）相比社区较小
2. **Python 启动速度**：不如 Rust/Go 原生编译（但提供 PyInstaller 二进制）
3. **文档**：英文文档相对较新，中文资源更丰富
4. **部分功能实验性**：D-Mail、okabe 代理、远程执行仍在演进
5. **Moonshot 服务依赖**：搜索/抓取服务在非 Kimi 提供商下需额外配置
6. **版本号体系**：采用 minor-bump-only（PATCH 始终为 0），不遵循严格语义化版本

## 使用场景

- **最适合**：Kimi/Moonshot 用户、需要双模式交互（Agent + Shell）的终端重度用户、需要 Web UI 远程访问的团队
- **适合**：中文开发者、多 LLM 提供商切换需求、需要子代理系统处理复杂任务、IDE 集成（VS Code/Zed）
- **不太适合**：需要 100+ LLM 提供商的场景（建议 OpenCode）、需要桌面应用的用户

## 资源链接

- [GitHub](https://github.com/MoonshotAI/kimi-cli)
- [英文文档](https://moonshotai.github.io/kimi-cli/en/)
- [中文文档](https://moonshotai.github.io/kimi-cli/zh/)
- [PyPI](https://pypi.org/project/kimi-cli/)
- [Kimi 官网](https://kimi.moonshot.cn/)
- [Changelog](https://github.com/MoonshotAI/kimi-cli/blob/main/CHANGELOG.md)
