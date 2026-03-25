# Kimi Code CLI (月之暗面)

> **📌 本文档已拆分为多文件目录，内容更详尽。请访问 [kimi-cli/](./kimi-cli/) 查看最新版本。**
> 本单文件保留供向后兼容，可能与目录版本存在差异。

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

## 技术架构（源码分析）

### Monorepo 结构

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

### 核心架构

```
CLI 入口 (__main__.py → Typer)
    │
    ▼
KimiCLI.create() [工厂模式]
    ├── 配置加载 (Pydantic 2 + TOML, 环境变量覆盖)
    ├── OAuth 认证 (浏览器重定向 / keyring / 文件)
    ├── 插件系统初始化 (plugin.json → 子进程工具)
    └── KimiSoul 代理引擎 (kosong LLM 抽象)
    │
    ▼
执行模式选择
    ├── run_shell()      → TUI 交互模式 (prompt-toolkit + Rich)
    ├── run_print()      → 非交互模式 (脚本/CI)
    ├── run_acp()        → IDE 集成 (ACP JSON-RPC over stdio)
    └── run_wire_stdio() → Wire 事件流 (自定义 UI)
    │
    ▼
代理循环 (KimiSoul)
    → 动态提示注入 (plan_mode, yolo_mode, 通知)
    → LLM 调用 (kosong.step → 多提供商)
    → 工具调用解析
    → 审批检查 (YOLO / auto-approve / 用户确认)
    → 工具执行 (内置 + MCP + 插件)
    → 上下文管理 (自动压缩 @ 85%)
    → Wire 事件广播 (TurnBegin → StepBegin → ToolCall → ToolResult → TurnEnd)
    → 子代理委派 (前台/后台，结果摘要)
    → 重复直到完成 (max_steps_per_turn=100)
```

### 技术栈
- **语言**：Python 3.12+（3.14 推荐）
- **CLI 框架**：Typer（懒加载子命令）
- **TUI**：prompt-toolkit + Rich（终端渲染）
- **Web 框架**：FastAPI + Uvicorn（WebSocket + REST）
- **LLM 抽象**：kosong（自研，支持多提供商统一接口）
- **MCP SDK**：fastmcp（stdio + HTTP）
- **ACP SDK**：agent-client-protocol 0.8.0
- **类型安全**：Pydantic 2（配置 + 数据模型）
- **模板引擎**：Jinja2（系统提示模板）
- **内容提取**：trafilatura + lxml（网页解析）
- **搜索**：ripgrepy（Grep 工具后端）
- **打包**：uv（包管理 + 构建）、PyInstaller（独立二进制）
- **代码质量**：ruff（lint + format）、pyright + ty（类型检查）

### 多代理系统

| 代理 | 类型 | 工具权限 | 用途 |
|------|------|---------|------|
| **default** | 主代理 | 全部工具 + Agent + AskUserQuestion + EnterPlanMode | 默认代理，完整能力 |
| **coder** | 子代理 | Shell, ReadFile, ReadMediaFile, Glob, Grep, WriteFile, StrReplaceFile, SearchWeb, FetchURL | 软件工程任务，读写执行 |
| **explore** | 子代理 | Shell, ReadFile, ReadMediaFile, Glob, Grep, SearchWeb, FetchURL（只读） | 快速代码库探索，不修改文件 |
| **plan** | 子代理 | ReadFile, ReadMediaFile, Glob, Grep, SearchWeb, FetchURL（无 Shell） | 架构规划，纯只读分析 |
| **okabe** | 实验代理 | default + SendDMail | 含 D-Mail 时间回溯能力 |

- 子代理通过 `Agent` 工具创建，指定 `subagent_type`（coder/explore/plan）
- 每个子代理实例在会话内持久化，可通过 `agent_id` 恢复
- 支持前台（等待结果）和后台（立即返回，自动通知）执行
- 子代理有独立上下文，父代理只看到结果摘要
- 支持通过 YAML 文件定义自定义代理（工具策略、系统提示、模型覆盖）

### 工具系统

| 工具 | 用途 | 关键参数 |
|------|------|---------|
| **Agent** | 委派任务给子代理 | description, prompt, subagent_type (coder/explore/plan), model, resume, run_in_background |
| **Shell** | 执行 bash/PowerShell 命令 | command, timeout (1-86400s), run_in_background, description |
| **ReadFile** | 读取文件内容 | path, line_offset, n_lines |
| **ReadMediaFile** | 读取图片/视频文件 | path |
| **WriteFile** | 创建/覆写文件 | path, contents |
| **StrReplaceFile** | 精确文本替换 | path, old_str, new_str |
| **Glob** | 文件模式匹配搜索 | pattern (glob), path |
| **Grep** | 正则内容搜索 | pattern (regex), glob, path, output_mode, context |
| **SearchWeb** | Web 搜索（Moonshot Search） | query |
| **FetchURL** | 抓取网页内容（Moonshot Fetch + trafilatura） | url |
| **AskUserQuestion** | 向用户提出结构化问题 | questions (1-4), 支持 single/multi-select + 自定义文本 |
| **SetTodoList** | 更新任务列表 | todos: [{title, status: pending/in_progress/done}] |
| **TaskList** | 列出后台任务 | active_only (default: true) |
| **TaskOutput** | 获取后台任务输出 | task_id, block (default: false) |
| **TaskStop** | 停止后台任务 | task_id |
| **EnterPlanMode** | 进入只读规划模式 | （自动触发） |
| **ExitPlanMode** | 提交规划方案供用户选择 | options (2-3 labeled choices) |
| **Think** | 内部推理思考 | thought（默认禁用） |
| **SendDMail** | 时间回溯消息 | message, checkpoint_id（仅 okabe 代理） |

此外，MCP 工具和插件工具在运行时动态加载。

### 权限系统

```
审批模式：
  - YOLO 模式：自动审批所有操作（--yolo / /yolo）
  - 会话级自动审批：approve_for_session 后该操作不再询问
  - 逐次确认：approve / reject (可附带 feedback)

Shell 工具：需要用户审批，显示命令预览
文件写入：需要用户审批，显示 diff 预览
文件读取：自动允许
Web 工具：自动允许
MCP 工具：需要用户审批
```

- 审批请求通过 Wire 协议统一下发，所有客户端（Shell/Web/ACP）共享
- 拒绝时可附带 feedback 文本引导模型下次尝试
- 后台子代理的审批请求通过根 UI 通道浮出

### Wire 事件流协议（v1.6）

```
控制流事件：
  TurnBegin          → 代理回合开始（含用户输入）
  TurnEnd            → 代理回合结束
  StepBegin          → LLM 步骤开始（含步骤号）
  StepInterrupted    → 步骤被中断
  SteerInput         → 用户发送跟进引导消息

内容事件：
  ContentPart        → 文本/思考/图片/音频/视频

工具事件：
  ToolCall           → 工具调用
  ToolCallPart       → 工具调用流式部分
  ToolResult         → 工具执行结果

状态更新：
  StatusUpdate       → 上下文使用率、token 统计、plan_mode、MCP 状态

交互请求/响应：
  ApprovalRequest    → 审批请求（含 source metadata, display blocks）
  ApprovalResponse   → 审批响应（approve/approve_for_session/reject + feedback）
  QuestionRequest    → 结构化问题（含 options, multi_select）
  QuestionResponse   → 问题回答

压缩/MCP 加载：
  CompactionBegin/End       → 上下文压缩
  MCPLoadingBegin/End       → MCP 服务器连接
  MCPServerSnapshot         → 单个 MCP 服务器状态
  MCPStatusSnapshot         → MCP 整体状态

子代理事件：
  SubagentEvent      → 嵌套子代理事件（含 agent_id, subagent_type, parent_tool_call_id）

通知：
  Notification       → 后台任务完成等通知
```

### Skill 系统

**Skill 发现路径**（优先级递增）：
1. **内置 Skill**：`src/kimi_cli/skills/`（如 `kimi-cli-help`、`skill-creator`）
2. **用户级 Skill**：`~/.config/agents/skills`、`~/.agents/skills`、`~/.kimi/skills`、`~/.claude/skills`、`~/.codex/skills`
3. **项目级 Skill**：`./.agents/skills`、`./.kimi/skills`、`./.claude/skills`、`./.codex/skills`
4. **插件 Skill**：从已安装插件中发现

**Skill 类型**：
- **标准 Skill**：`SKILL.md` 文件包含指令文本，通过 `/skill:<name>` 加载
- **Flow Skill**：`SKILL.md` 中嵌入 Mermaid 或 D2 流程图，通过 `/flow:<name>` 执行代理工作流

### 插件系统（v1.25.0 新增）

```jsonc
// plugin.json 格式
{
  "name": "my-plugin",
  "version": "1.0.0",
  "description": "Plugin description",
  "config_file": "config.json",
  "inject": {
    "services.moonshot.api_key": "api_key",
    "services.moonshot.base_url": "base_url"
  },
  "tools": [
    {
      "name": "my-tool",
      "description": "Tool description",
      "command": ["python", "run.py"],
      "parameters": { ... }
    }
  ]
}
```

- **安装**：`kimi plugin install <git-url> [--subpath PATH]`，支持 monorepo
- **执行**：工具在隔离子进程中运行，参数通过 stdin JSON 传入，stdout 作为结果
- **凭证注入**：`inject` 声明自动从宿主 LLM 配置注入 `api_key` 和 `base_url`（OAuth 令牌实时刷新）
- **存储**：`~/.kimi/plugins/`

### `/init` 与 AGENTS.md（源码：`soul/slash.py`、`soul/agent.py`）

**`/init` 命令**：分析代码库并自动生成 `AGENTS.md` 项目配置文件。

**实现机制**（`slash.py:init()`）：
1. 创建临时目录和临时上下文（`Context(file_backend=...)`），避免污染当前会话
2. 使用临时 `KimiSoul` 实例运行内置 `prompts.INIT` 提示，让 LLM 分析代码库结构
3. LLM 生成 `AGENTS.md` 文件到项目工作目录（`KIMI_WORK_DIR`）
4. 生成完成后，通过 `load_agents_md()` 读取文件内容，注入到当前会话上下文

**AGENTS.md 加载**（`agent.py:load_agents_md()`）：
- 查找路径：`<work_dir>/AGENTS.md` 或 `<work_dir>/agents.md`（大小写不敏感）
- 文件内容作为 `KIMI_AGENTS_MD` 变量注入到系统提示模板（Jinja2）
- 在 `Runtime.create()` 时自动加载

**与其他工具对比**：
- 类似 Claude Code 的 `CLAUDE.md` 和 Gemini CLI 的 `GEMINI.md`
- 不同之处：Kimi CLI 提供 `/init` 自动生成功能（Claude Code 和 Gemini CLI 需手动创建）

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

## 配置

```toml
# ~/.kimi/config.toml

# 默认设置
default_model = "kimi-k2.5"
default_thinking = false
default_yolo = false
default_editor = "vim"        # 或 "code --wait"

# LLM 提供商
[providers.kimi]
type = "kimi"
base_url = "https://api.moonshot.cn/v1"
# api_key 通过 OAuth 或环境变量

[providers.openai]
type = "openai_responses"
api_key = "sk-..."

[providers.anthropic]
type = "anthropic"
api_key = "sk-ant-..."

# 模型配置
[models.kimi-k2-5]
provider = "kimi"
model = "kimi-k2.5"
max_context_size = 256000
capabilities = ["image_in", "video_in", "thinking"]

# 代理循环控制
[loop_control]
max_steps_per_turn = 100        # 每回合最大步数（默认 100）
max_retries_per_step = 3        # 每步重试次数（默认 3）
max_ralph_iterations = 0        # 额外 Ralph 迭代（-1=无限，默认 0）
reserved_context_size = 50000   # 保留上下文大小（默认 50000 token）
compaction_trigger_ratio = 0.85 # 自动压缩触发比例（默认 0.85）

# 后台任务
[background]
max_running_tasks = 4           # 最大并发后台任务
read_max_bytes = 30000          # 输出读取上限
notification_tail_lines = 20    # 通知尾部行数
keep_alive_on_exit = false      # 退出时保持后台任务

# Moonshot 服务（Kimi 提供商专用）
[services.moonshot_search]
base_url = "..."
# api_key 通过 OAuth

[services.moonshot_fetch]
base_url = "..."

# MCP 客户端配置
[mcp.client]
tool_call_timeout_ms = 60000    # MCP 工具调用超时
```

**配置优先级（低→高）**：
1. 默认值
2. 配置文件 `~/.kimi/config.toml`
3. `--config-file PATH` CLI 参数
4. `--config TEXT` CLI 内联 TOML/JSON
5. 环境变量（`KIMI_*`）

## CLI 命令

```bash
# 交互式会话（默认 Shell 模式）
kimi

# 带提示启动
kimi -p "重构 auth 模块"

# 非交互模式（适合脚本/CI）
kimi --print -p "解释这段代码"

# 流式 JSON 输出
kimi --print --stream-json -p "..."

# 指定模型和思维模式
kimi -m claude-sonnet --thinking

# 恢复会话
kimi -S <session-id>
kimi -C    # 继续上一个会话

# YOLO 模式（自动审批所有操作）
kimi --yolo

# 指定工作目录和附加目录
kimi -w /path/to/project --add-dir /path/to/docs

# 登录/登出
kimi login
kimi logout

# Web UI
kimi web [--port 5494]
kimi web --network --auth-token <token>    # 网络访问模式

# ACP 模式（IDE 集成）
kimi acp

# MCP 服务器管理
kimi mcp list
kimi mcp add --transport stdio my-server -- command args
kimi mcp add --transport http --auth oauth my-server https://mcp.example.com
kimi mcp remove my-server
kimi mcp auth my-server
kimi mcp test my-server

# 插件管理
kimi plugin install https://github.com/org/repo.git
kimi plugin install https://github.com/org/repo.git/plugins/my-plugin  # monorepo
kimi plugin list
kimi plugin uninstall my-plugin

# 导出会话
kimi export [session-id]

# 系统信息
kimi info [--json]

# 可视化仪表板
kimi vis

# Wire 模式（自定义 UI）
kimi --wire
```

### 斜杠命令（会话内）

| 命令 | 用途 |
|------|------|
| `/init` | 分析代码库，生成 AGENTS.md（见下方详细说明） |
| `/compact [FOCUS]` | 压缩上下文历史（可指定保留重点） |
| `/clear`, `/reset` | 清除上下文 |
| `/yolo` | 切换 YOLO 模式 |
| `/plan` | 切换 Plan 模式 |
| `/model` | 切换模型和思维模式 |
| `/sessions`, `/resume` | 列出并切换/恢复会话 |
| `/new` | 创建新会话 |
| `/export` | 导出会话 |
| `/import` | 导入上下文 |
| `/editor` | 配置外部编辑器 |
| `/add-dir` | 添加工作目录 |
| `/mcp` | 显示 MCP 状态 |
| `/task` | 后台任务浏览器（TUI） |
| `/web` | 抓取网页内容加入上下文 |
| `/help` | 显示帮助 |
| `/version` | 显示版本信息 |
| `/changelog` | 显示更新日志 |
| `/feedback` | 提交反馈 |
| `/exit`, `/quit` | 退出 |
| `/skill:<name>` | 加载标准 Skill |
| `/flow:<name>` | 执行 Flow Skill |

> **注意：** 认证（登录/登出）和用量查看通过 CLI 参数或配置命令处理，而非交互式斜杠命令。

### 键盘快捷键

| 快捷键 | 功能 |
|--------|------|
| `Ctrl-X` | 切换 Agent ↔ Shell 模式 |
| `Ctrl-C` | 中断当前操作 |
| `Ctrl-D` | 退出 |
| `Ctrl-O` | 在外部编辑器中打开输入 |
| `Ctrl-V` | 粘贴文本/图片/视频 |
| `Ctrl-E` | 展开审批预览详情 |
| `Shift-Tab` | 切换 Plan 模式 |
| `1/2/3/4` | 审批面板快捷操作（审批/会话审批/拒绝/拒绝+反馈） |

## ACP（Agent Client Protocol）IDE 集成

```bash
# 以 ACP 模式启动（JSON-RPC over stdio）
kimi acp
```

### 支持的编辑器

| 编辑器 | 状态 | 说明 |
|--------|------|------|
| **VS Code** | 原生扩展 | 自动安装/激活扩展 |
| **Zed** | 原生 ACP | 实时编辑、agent following |
| **JetBrains IDEs** | ACP Registry | acp.json 配置 |
| **Neovim** | 通过 Avante.nvim / CodeCompanion.nvim | 完整 ACP 集成 |

### ACP 能力
- `load_session: True`：支持恢复会话
- `embedded_context: True`：支持嵌入式文件内容
- `image: True`：支持图片输入
- `mcp_capabilities: {http: True}`：支持远程 MCP 服务器
- 斜杠命令通告（`/init`, `/compact`, `/yolo` 等）
- Shell 命令路由：通过 ACP 客户端终端执行
- 文件读写路由：通过 ACP 客户端同步编辑
- MCP 服务器：加载 ACP 客户端管理的 MCP 服务器

## Web UI

```bash
# 启动 Web UI
kimi web                          # 默认 localhost:5494
kimi web --port 8080              # 自定义端口
kimi web --network --auth-token my-secret  # 网络模式 + 认证
kimi web --lan-only               # 仅局域网
kimi web --public                 # 公网（需配合认证）
```

### 功能
- **多会话管理**：创建、切换、归档、删除、搜索
- **实时 WebSocket**：通过 Wire 协议实时推送代理事件
- **审批对话框**：Diff 预览、命令预览、approve/reject + feedback
- **结构化问题**：Tab 导航的多问题面板
- **后台任务可视化**：子代理活动渲染、任务状态追踪
- **文件变更面板**：Git diff 状态栏、文件列表、"Open in" 菜单
- **会话 Fork**：从任意回复分叉新会话
- **Plan 模式切换**：输入框工具栏切换
- **@ 文件提及**：自动补全引用工作区文件
- **斜杠命令菜单**：自动补全 + 键盘导航
- **消息队列**：代理运行时队列后续消息
- **数学公式渲染**：支持 `$...$` 行内和 `$$...$$` 块级数学
- **媒体预览**：图片/视频工具结果的缩略图预览
- **安全**：Token 认证、CORS 控制、敏感 API 限制、Origin 验证

### 环境变量
- `KIMI_WEB_SESSION_TOKEN`：认证令牌
- `KIMI_WEB_ALLOWED_ORIGINS`：允许的跨域来源
- `KIMI_WEB_ENFORCE_ORIGIN`：强制 Origin 检查
- `KIMI_WEB_RESTRICT_SENSITIVE_APIS`：限制敏感端点

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

1. **社区规模**：与 OpenCode（130k Stars）相比社区较小
2. **Python 启动速度**：不如 Rust/Go 原生编译（但提供 PyInstaller 二进制）
3. **文档**：英文文档相对较新，中文资源更丰富
4. **部分功能实验性**：D-Mail、okabe 代理、远程执行仍在演进
5. **Moonshot 服务依赖**：搜索/抓取服务在非 Kimi 提供商下需额外配置
6. **版本号体系**：采用 minor-bump-only（PATCH 始终为 0），不遵循严格语义化版本

## 项目演进（2025.09 — 2026.03）

### 里程碑时间线

| 时间 | 版本 | 里程碑 |
|------|------|--------|
| 2026-03-23 | **v1.25.0** | **插件系统**（plugin.json + 凭证注入）、**Agent 工具**（子代理委派）、**统一审批运行时**、Wire v1.6 |
| 2026-03-17~18 | v1.23~1.24 | **后台 Bash 任务**、Plan 模式多选项方案、延迟 MCP 启动 |
| 2026-03-10~12 | v1.19~1.21 | **Plan 模式**、**kimi vis 可视化仪表板**、**Steer Input**（运行时引导）、内联运行提示 |
| 2026-02-27 | v1.16 | **--add-dir 多目录**、**Ctrl-O 外部编辑器**、/new 和 /editor 命令 |
| 2026-02-09~11 | v1.9~1.12 | Web UI 大升级（Fork、归档、审批快捷键、文件引用、消息队列）、YOLO 配置 |
| 2026-02-03~05 | v1.6~1.7 | **Web UI 认证和网络模式**、Wire replay、kagent Rust 实验 |
| 2026-01-27~30 | **v1.0~1.5** | **正式发布 1.0**（login/logout）、**Web UI 首发**（kimi web）、Git diff 状态栏 |
| 2026-01-19~24 | v0.79~0.86 | **项目级 Skill**、**Flow Skill（Mermaid/D2）**、**跨平台二进制构建** |
| 2026-01-04~16 | v0.71~0.78 | **ACP 文件路由**、/model 命令、/skill 命令、kimi info/term |
| 2025-12-15~31 | v0.64~0.70 | **MCP 子命令组**、session 管理、Wire 重实现、config TOML 迁移 |
| 2025-11-08~28 | v0.51~0.62 | 基础稳定化：Shell/CMD 工具、MCP 审批、子代理 MCP、ACP 兼容性 |
| 2025-09~11 | v0.8~0.50 | 早期开发：基础代理循环、TUI Shell、ACP 原型、Wire 协议雏形 |

六个月内从 v0.8 发展到 v1.25.0，经历约 **110 个版本发布**，从基础 CLI 代理成长为含 Web UI、IDE 集成、插件系统的多客户端 AI 编程平台。

### v1.25.0 关键变化（2026-03-23）

- **插件系统**：`plugin.json` 声明式插件，子进程隔离执行，自动凭证注入，支持 monorepo
- **Agent 工具**：子代理委派（coder/explore/plan），前台/后台运行，结果自动摘要
- **统一审批运行时**：前台和后台子代理的审批请求统一协调，支持拒绝反馈
- **Wire v1.6**：SubagentEvent 新增 agent_id/subagent_type，ApprovalResponse 支持 feedback
- **Shell**：交互式审批面板（Diff/命令预览 + 4 种操作），工具栏显示工作目录/Git 分支/后台任务

### v1.19~1.24 关键变化（2026-03-10~18）

- **Plan 模式**：只读分析阶段 + ExitPlanMode 多方案选择 + 增量编辑
- **kimi vis**：Wire 事件时间线、上下文查看器、会话浏览器、用量统计
- **Steer Input**：运行时发送跟进消息引导代理方向
- **后台 Bash 任务**：Shell 工具支持 `run_in_background`，完整生命周期管理
- **延迟 MCP 启动**：异步初始化 + 进度指示，优化启动体验

### v1.0~1.5 关键变化（2026-01-27~30）

- **正式发布 1.0**：login/logout 命令，认证流程完善
- **Web UI 首发**：`kimi web` 命令启动浏览器界面
- **Git diff 状态栏**：显示未提交变更
- **会话搜索和 Open in 菜单**

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
