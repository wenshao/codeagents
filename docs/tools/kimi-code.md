# Kimi CLI (月之暗面)

**开发者：** Moonshot AI (月之暗面)
**许可证：** 开源
**仓库：** [github.com/nicepkg/kimi-cli](https://github.com/nicepkg/kimi-cli)
**Stars：** -

## 概述

Kimi CLI 是月之暗面推出的 AI 编程代理，**主要用 Python 编写**（68.8%），辅以 TypeScript（Web UI + SDK）。核心特色是双模式交互（Agent + Shell，Ctrl-X 切换）和 Wire 协议支持多客户端（TUI、Web、IDE）。支持 Kimi、OpenAI、Anthropic、Google 等多个 LLM 提供商。

## 核心功能

### 基础能力
- **Python 代理引擎**：Pydantic 2 类型安全 + FastAPI 服务器
- **10+ 内置工具**：文件操作、Shell 执行、Web 搜索/抓取、规划、推理等
- **多提供商**：Kimi、OpenAI、Anthropic、Google Gemini
- **多客户端**：TUI 终端、Web UI（React）、IDE（ACP 协议）
- **MCP 支持**：Model Context Protocol 集成
- **会话持久化**：Wire 格式存储，可导出/恢复

### 独特功能
- **双模式交互**：Agent 模式（AI 处理）与 Shell 模式（直接执行），Ctrl-X 无缝切换
- **Wire 协议**：统一的客户端-服务器通信协议
- **ACP（Agent Client Protocol）**：IDE 编辑器原生集成
- **Moonshot 服务**：集成 Moonshot Search 和 Fetch API
- **扩展思维模式**：`thinking_mode = "enabled"` 支持深度推理
- **上下文压缩**：80% 容量时自动压缩历史

## 技术架构（源码分析）

### 项目结构

```
kimi-cli/
├── src/kimi_cli/           # Python 主应用
│   ├── __main__.py         # CLI 入口
│   ├── app.py              # KimiCLI 核心编排器
│   ├── config.py           # Pydantic 配置（TOML/JSON）
│   ├── llm.py              # LLM 提供商工厂
│   ├── session.py          # 会话状态管理
│   ├── agents/             # 代理实现
│   ├── tools/              # 10+ 工具实现
│   │   ├── file/           # 文件读写编辑
│   │   ├── shell/          # Shell 执行（AST 安全分析）
│   │   ├── web/            # Web 搜索/抓取（Moonshot）
│   │   ├── think/          # 推理
│   │   ├── plan/           # 规划
│   │   ├── multiagent/     # 多代理协调
│   │   ├── background/     # 后台任务
│   │   └── todo/           # 任务管理
│   ├── wire/               # Wire 协议（多客户端通信）
│   ├── auth/               # OAuth 认证
│   ├── cli/                # CLI 命令（Typer）
│   └── ui/                 # TUI 组件
├── sdks/kimi-sdk/          # TypeScript SDK
├── web/                    # React Web UI
└── tests/                  # 测试套件
```

### 核心架构

```
CLI 入口 (__main__.py)
    │
    ▼
KimiCLI.create() [工厂模式]
    ├── 配置加载 (Pydantic + TOML)
    ├── OAuth 认证 (浏览器重定向)
    ├── 插件系统初始化
    └── KimiSoul 代理引擎
    │
    ▼
执行模式选择
    ├── run_shell()    → TUI 交互模式
    ├── run_print()    → 格式化输出
    ├── run_acp()      → IDE 集成
    └── run_wire_stdio() → IPC 通信
    │
    ▼
代理循环
    → LLM 调用 (create_llm 工厂)
    → 工具调用解析
    → 权限检查 (AST 分析)
    → 工具执行
    → 上下文管理 (自动压缩)
    → 重复直到完成
```

### 双模式交互

```
Agent 模式（默认）：
> 重构 auth 模块     ← AI 处理，可调用工具

按 Ctrl-X → Shell 模式：
$ ls -la             ← 直接执行，保留上下文

按 ESC → 回到 Agent 模式
```

Wire 协议在模式切换间维持上下文，无丢失。

### 权限系统

```
规则优先级：deny > ask > allow > default

Shell 工具：AST 解析命令，提取目录和操作
文件工具：read=allow, write=ask
Web 工具：allow
危险模式：["rm -rf", "sudo"] → deny
```

## 安装

```bash
# 使用 uv（推荐）
uv tool install kimi-cli

# 使用 pip
pip install kimi-cli

# 验证
kimi --version

# 首次使用（会引导 OAuth 认证）
kimi
```

## 支持的模型

| 提供商 | 模型 | 说明 |
|--------|------|------|
| **Kimi** | kimi-k2.5 | 最新，多模态 |
| OpenAI | GPT-4, GPT-4o | 标准支持 |
| Anthropic | Claude Sonnet/Opus | 标准支持 |
| Google | Gemini | 标准支持 |

## 配置

```toml
# ~/.config/kimi-cli/config.toml

[default_model]
provider = "kimi"
name = "kimi-k2.5"
max_context_size = 256000

[llm_config]
temperature = 0.7
thinking_mode = "enabled"
max_tokens = 4096

[agent_loop]
max_steps = 20
compaction_trigger_ratio = 0.8

[permissions]
shell = "ask"
file = { read = "allow", write = "ask" }
```

## 优势

1. **双模式交互**：Agent + Shell 无缝切换，效率高
2. **Wire 协议**：多客户端统一通信
3. **Moonshot 集成**：原生搜索和网页抓取服务
4. **扩展思维**：支持深度推理模式
5. **Python 生态**：Pydantic 类型安全，FastAPI 服务器
6. **多提供商**：不锁定 Kimi，支持主流模型

## 劣势

1. **技术预览**：功能和 API 可能变化
2. **社区较小**：用户群较少
3. **Python 性能**：启动速度不如 Rust/Go
4. **文档有限**：中文资源为主

## CLI 命令

```bash
# 交互式会话
kimi

# 导出会话
kimi export

# MCP 服务器管理
kimi mcp list

# 启动 Web 服务器
kimi web

# 插件管理
kimi plugin list
```

## 使用场景

- **最适合**：Kimi 用户、需要双模式交互的终端用户
- **适合**：中文开发者、多提供商切换
- **不太适合**：需要成熟生态的生产环境

## 资源链接

- [GitHub](https://github.com/nicepkg/kimi-cli)
- [Kimi 官网](https://kimi.moonshot.cn/)
