# 2. Qoder CLI 技术架构（Go 二进制分析）

> 基于 v0.1.35 二进制文件（43MB, ELF 64-bit, Go 静态链接, stripped）分析。

## 二进制结构

| 项目 | 详情 |
|------|------|
| **格式** | ELF 64-bit LSB executable, x86-64, 静态链接, stripped |
| **大小** | 43 MB |
| **语言** | **Go**（runtime.go, goroutine 确认） |
| **构建** | 静态链接（无外部 .so 依赖） |
| **分发** | npm `@qoder-ai/qodercli`（Shell 启动脚本 + Go 二进制） |

## 内部包结构（从二进制 strings 提取）

```
code.alibaba-inc.com/qoder-core/qodercli/
├── acp/                    # Agent Communication Protocol
│   ├── acp/                # ACP 核心
│   ├── json/               # JSON 序列化
│   ├── option/             # 选项管理
│   ├── qoder/              # Qoder 特定 ACP 实现
│   ├── session/            # 会话管理
│   └── tools/              # ACP 工具
├── cmd/                    # CLI 子命令
│   ├── commit/             # AI 提交 + Hook
│   ├── endpoint/           # API 端点管理
│   ├── feedback/           # 反馈
│   ├── install/            # 安装 + 下载 + 遥测
│   ├── internal/           # 内部命令
│   ├── jobs/               # 并发任务（attach/fetch/rm/stop）
│   ├── login/              # 登录
│   ├── mcp/                # MCP 管理
│   ├── status/             # 状态
│   └── update/             # 自更新
├── core/                   # 核心逻辑
│   ├── agent/              # 代理系统
│   │   ├── state/          # 状态管理
│   │   │   ├── memory/     # 记忆系统
│   │   │   └── quest/      # Quest 模式状态
│   │   ├── context/        # 上下文管理
│   │   └── tool/           # 工具注册
│   ├── auth/               # 认证
│   ├── config/             # 配置系统
│   ├── constant/           # 常量
│   ├── mcp/                # MCP 客户端
│   ├── permission/         # 权限系统
│   │   └── quest/          # Quest 模式权限
│   └── rule/               # 规则引擎
├── tui/                    # 终端 UI
│   ├── components/         # UI 组件
│   │   ├── chat/           # 聊天界面
│   │   ├── dialog/         # 对话框
│   │   ├── input/          # 输入
│   │   ├── output/         # 输出
│   │   ├── permission/     # 权限 UI
│   │   │   └── quest/      # Quest 权限 UI
│   │   └── status/         # 状态栏
│   ├── event/              # 事件系统
│   ├── render/             # 渲染引擎
│   ├── state/              # UI 状态
│   ├── styles/             # 样式
│   ├── theme/              # 10 个内置主题
│   │   ├── catppuccin/
│   │   ├── dracula/
│   │   ├── flexoki/
│   │   ├── gruvbox/
│   │   ├── monokai/
│   │   ├── onedark/
│   │   ├── qoder/          # Qoder 自定义主题
│   │   ├── tokyonight/
│   │   └── tron/
│   └── util/               # 工具函数
│       ├── code/           # 代码高亮
│       ├── diff/           # 差异显示
│       ├── markdown/       # Markdown 渲染
│       └── path/           # 路径处理
└── packages/               # 外部包集成
```

## SDK 依赖（二进制引用计数）

| SDK | 引用数 | 说明 |
|-----|--------|------|
| **openai-go** | 11,464 | OpenAI Go SDK（主要 LLM 接口） |
| **anthropic-sdk-go** | 3,901 | Anthropic Go SDK（Claude 支持） |
| **mcp-go** | 744 | MCP Go SDK |
| **charmbracelet/bubbletea** | — | TUI 框架 |
| **charmbracelet/lipgloss** | — | 终端样式 |
| **charmbracelet/glamour** | — | Markdown 渲染 |
| **yuin** | 1,771 | Goldmark Markdown 解析器 |
| **spf/cobra** | 1,009 | CLI 框架 |
| **pflag** | 695 | 命令行参数解析 |
| **zap** | 893 | 日志框架 |

## API 端点（二进制提取）

| 端点 | 用途 |
|------|------|
| `api1.qoder.sh` | 主 API |
| `api3.qoder.sh` | 备用 API |
| `center.qoder.sh` | 中心服务 |
| `openapi.qoder.sh` | OpenAPI 端点（含 BYOK 配置、设备认证） |
| `download.qoder.com/qodercli` | 自更新下载 |
| `docs.qoder.com` | 文档 |
| `forum.qoder.com` | 社区论坛 |
| `daily-api2.qoder.sh` | 日常/测试 API |
| `daily-openapi.qoder.sh` | 日常 OpenAPI |
| `daily.qoder.ai` | 日常环境 |
| `api.openai.com` | OpenAI API（BYOK） |
| `dashscope.aliyuncs.com` | 阿里云 DashScope（BYOK） |

## Machine ID / 设备指纹

| 函数 | 用途 |
|------|------|
| `getMachineKey` | 设备唯一标识（用于遥测和许可证绑定） |
| `SystemFingerprint` | 系统指纹（OpenAI API 响应字段） |
| `Hostname` | 主机名 |

> **注意：** `getMachineKey` 存在于二进制中，用于设备级标识。这与 Claude Code 的 IOPlatformUUID 和 Gemini CLI 的 Installation UUID 类似。

## 遥测系统

从内部包路径 `cmd/install/telemetry` 可见，遥测与安装系统绑定。但未找到 PostHog/Segment/Datadog 等第三方分析 SDK 的引用——可能使用 Qoder 自有的遥测基础设施（通过 `api1.qoder.sh` 或 `center.qoder.sh` 上报）。

## 权限系统

从内部包路径分析：
- `core/permission/` — 核心权限
- `core/permission/quest/` — Quest 模式特有权限
- `tui/components/permission/` — 权限 UI
- `tui/components/permission/quest/` — Quest 权限 UI
- `core/rule/` — 规则引擎

权限系统有独立的 Quest 模式分支——Quest 模式（自主执行）有不同于普通模式的权限规则。

## Claude Code 兼容实现

`--with-claude-config` 参数启用后加载：
- `.claude/` 目录下的配置
- Claude Code Skills（SKILL.md 文件）
- Claude Code Commands（commands 目录）
- Claude Code Subagents（代理定义）

这表明 Qoder CLI 内部实现了 Claude Code 的配置解析器。

## 10 个内置主题

从 `tui/theme/` 包提取：catppuccin, dracula, flexoki, gruvbox, monokai, onedark, **qoder**（自定义）, tokyonight, tron + 默认主题。

## 与其他闭源 Agent 的架构对比

| 维度 | Qoder CLI | Claude Code | Copilot CLI | Codex CLI |
|------|-----------|-------------|-------------|-----------|
| **语言** | Go | TypeScript/Bun | TypeScript/Node SEA | Rust |
| **二进制大小** | 43 MB | 227 MB | 133 MB | 137 MB |
| **TUI 框架** | Bubbletea (Go) | Ink/React | Ink/React | 自定义 (Rust) |
| **CLI 框架** | Cobra | 内置 | 内置 | Clap |
| **LLM SDK** | openai-go + anthropic-sdk-go | 内置 Anthropic | 内置 | 内置 OpenAI |
| **MCP SDK** | mcp-go | 内置 | 内置 | 内置 |
| **静态链接** | ✓ | ✗（动态） | ✗ | ✓ |
