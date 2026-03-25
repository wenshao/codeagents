# 1. Claude Code 概述

**开发者：** Anthropic
**许可证：** 专有（Claude Pro/Max 订阅内含，或 API 按量付费）
**仓库：** [github.com/anthropics/claude-code](https://github.com/anthropics/claude-code)（插件/示例仓库）
**文档：** [docs.anthropic.com/claude-code](https://docs.anthropic.com/en/docs/claude-code)
**最后更新：** 2026-03

## 概述

Claude Code 是 Anthropic 官方的 AI 编程代理，运行在终端中。核心为闭源 Rust 原生二进制（非 Node.js），通过原生安装脚本分发（npm 方式已废弃）。基于 Claude 系列模型（Sonnet 4.6、Opus 4.6、Haiku 4.5），拥有业界最大的 100 万 token 上下文窗口（Opus 4.6[1m]）。具备 20+ 内置工具（含延迟加载工具）、5 层设置优先级体系、22 种 Hook 事件、沙箱执行隔离、多代理协作、~79 个斜杠命令等能力。它也是唯一深度集成 Anthropic 模型的终端代理工具，在 SWE-bench 等复杂编程基准上表现领先。

主要特点：
- **Rust 原生二进制**：亚秒级冷启动，低内存占用，不依赖 Node.js 运行时
- **100 万 token 上下文**：Opus 4.6[1m] 模型支持超长上下文，适合大型代码库分析
- **~79 个斜杠命令**：覆盖会话管理、Git 操作、配置调整、插件激活等
- **企业级管控**：5 层设置 + managed-settings 远程下发 + 沙箱隔离
- **插件系统**：marketplace 分发，security-review、pr-comments 等插件

## 核心功能

### 基础能力
- **Rust 原生二进制**：`curl install.sh | bash` 安装，亚秒级启动，低资源占用
- **20+ 内置工具**：Read、Write、Edit、MultiEdit、Bash、Glob、Grep、Agent/Task、WebFetch、WebSearch、TodoWrite、NotebookEdit、Skill、ToolSearch、Cron 系列等
- **MCP 集成**：Stdio/SSE/Streamable-HTTP 三种传输协议，工具以 `mcp__serverName__toolName` 格式命名
- **Git 深度集成**：理解 Git 历史、创建提交/PR、worktree 隔离、checkpoint/rewind 回退
- **上下文窗口**：最高 100 万 token（Opus 4.6[1m]、Sonnet 4.5[1m]、Sonnet 4.6[1m]），支持自动上下文压缩
- **会话恢复**：`--resume` 恢复中断会话，`--session-id` 指定会话

### 独特功能
- **插件系统**：通过 `/plugin` 命令和 marketplace 安装管理插件（security-review、pr-comments 等）
- **Prompt Hook**：22 种事件类型，支持 LLM 推理驱动的 Hook 决策
- **5 层设置**：企业->组织->用户->项目->本地->CLI->默认，支持远程下发
- **沙箱执行**：macOS sandbox-exec / Linux Docker 文件系统隔离 + 网络域名白名单
- **Teammates**：tmux/iTerm2 分屏多代理团队协作，每个代理独立 worktree
- **Remote Control**：`/remote-control` 桥接到 claude.ai/code 浏览器界面
- **Voice 模式**：`/voice` 命令启动 Push-to-talk 语音交互，基于 speech-to-text API
- **Channels**：`--channels` 激活 Channel 插件（研究预览 2026-03-20），支持 Telegram/Discord 消息推送到会话
- **`--bare` 模式**：脚本/CI 场景跳过 hooks/插件/LSP，纯净输出
- **CLAUDE.md**：项目级 AI 行为指令文件（类似 Gemini CLI 的 GEMINI.md）
- **Worktrees**：Git worktree 隔离并行分支，支持多代理同时操作不同分支
- **自动记忆**：跨会话学习用户偏好，存储到 `~/.claude/projects/` 目录
- **Chrome 扩展**（Beta）：浏览器标签页集成，提供页面读取、网络请求监控等能力
- **延迟工具加载**：通过 ToolSearch 按需加载不常用工具，减少系统提示占用

## 安装

```bash
# 推荐方式（原生二进制）
curl -fsSL https://claude.ai/install.sh | bash

# Homebrew（macOS）
brew install --cask claude-code

# npm（已 deprecated，不推荐）
npm install -g @anthropic-ai/claude-code
```

## 模型

Claude Code 支持以下模型及其变体：

| 模型 ID | 系列 | 上下文窗口 | 说明 |
|---------|------|------------|------|
| `claude-opus-4` | Opus 4 | 200K | Opus 4 基础版 |
| `claude-opus-4-1` | Opus 4.1 | 200K | Opus 4.1 |
| `claude-opus-4-5` | Opus 4.5 | 200K | Opus 4.5 |
| `claude-opus-4-6` | Opus 4.6 | 200K | Opus 4.6 标准上下文 |
| `claude-opus-4-6[1m]` | Opus 4.6 | 1M | Opus 4.6 扩展上下文（100 万 token） |
| `claude-sonnet-4` | Sonnet 4 | 200K | Sonnet 4 基础版 |
| `claude-sonnet-4-5` | Sonnet 4.5 | 200K | Sonnet 4.5 标准上下文 |
| `claude-sonnet-4-5[1m]` | Sonnet 4.5 | 1M | Sonnet 4.5 扩展上下文 |
| `claude-sonnet-4-6` | Sonnet 4.6 | 200K | Sonnet 4.6 标准上下文（默认模型） |
| `claude-sonnet-4-6[1m]` | Sonnet 4.6 | 1M | Sonnet 4.6 扩展上下文 |
| `claude-haiku-4` | Haiku 4 | 200K | Haiku 4 基础版 |
| `claude-haiku-4-5` | Haiku 4.5 | 200K | Haiku 4.5（快速/低成本） |

扩展上下文变体（`[1m]`）支持最高 100 万 token 的上下文窗口，适合大型代码库分析和长对话场景。

## 定价

Claude Code 基于 API 按量付费或通过订阅计划使用：

### 订阅计划

| 计划 | 价格 | Claude Code 额度 |
|------|------|-------------------|
| **Pro** | $20/月 | 有限使用额度 |
| **Max 5x** | $100/月 | 5 倍使用额度 |
| **Max 20x** | $200/月 | 20 倍使用额度 |
| **Team** | $30/用户/月 | 团队额度 |
| **Enterprise** | 自定义 | 企业额度 |

### API 按量付费

| 模型 | 输入价格 | 输出价格 |
|------|----------|----------|
| **Claude Sonnet 4.6** | $3/M tokens | $15/M tokens |
| **Claude Opus 4.6** | $15/M tokens | $75/M tokens |
| **Claude Haiku 4.5** | $0.80/M tokens | $4/M tokens |

- 支持 Prompt Caching：缓存命中的 token 享受折扣
- 典型编程会话消耗：单次对话约 10K-100K token

## CLI 命令

### 基础用法
```bash
claude                                    # 交互式会话
claude "重构这个函数"                      # 直接提问
claude -p "修复 bug"                      # 管道模式（非交互）
cat file.py | claude -p "审查这段代码"     # 管道输入
```

### 会话管理
```bash
claude --resume                           # 恢复最近会话
claude --resume <session-id>              # 恢复指定会话
claude -c                                 # 继续上次对话
```

### 模型与配置
```bash
claude --model claude-opus-4-6            # 指定模型
claude --model claude-sonnet-4-6          # 使用 Sonnet
claude --model claude-opus-4-6[1m]        # 使用扩展上下文 Opus
claude --allowedTools "Read,Glob,Grep"    # 限制可用工具
claude --bare                             # 脚本模式（跳过 hooks/插件）
```

### 高级选项（`claude --help` 确认，47 个参数）
```bash
# 会话管理
claude -c / --continue                    # 继续最近对话
claude -r / --resume [id]                 # 恢复指定会话
claude --session-id <uuid>                # 使用指定会话 ID
claude --fork-session                     # 恢复时创建新会话 ID
claude --from-pr [PR]                     # 恢复 PR 关联的会话
claude -n / --name <name>                 # 设置会话显示名

# 输入输出
claude -p / --print                       # 管道模式（非交互）
claude --output-format json|stream-json   # 输出格式
claude --input-format text|stream-json    # 输入格式
claude --json-schema <schema>             # 结构化输出验证
claude --include-partial-messages         # 包含流式部分消息

# 模型与工具
claude --model <model>                    # 指定模型
claude --fallback-model <model>           # 过载时回退模型（仅 --print）
claude --effort low|medium|high|max       # 推理努力级别
claude --allowedTools "Read,Glob"         # 允许的工具
claude --disallowedTools "Write"          # 禁止的工具
claude --tools "Bash,Edit,Read"           # 指定可用工具列表

# 提示与指令
claude --system-prompt <prompt>           # 替换系统提示
claude --append-system-prompt <prompt>    # 追加系统提示
claude --agent <agent>                    # 指定代理
claude --agents <json>                    # 自定义代理定义（JSON）

# MCP 与扩展
claude --mcp-config <file|json>           # MCP 服务器配置
claude --strict-mcp-config                # 仅使用 --mcp-config 中的 MCP
claude --chrome                           # 启用 Chrome 集成
claude --no-chrome                        # 禁用 Chrome 集成
claude --plugin-dir <path>                # 加载插件目录
claude --ide                              # 自动连接 IDE

# 安全与权限
claude --permission-mode <mode>           # acceptEdits|default|plan|auto|dontAsk|bypassPermissions
claude --dangerously-skip-permissions     # 绕过所有权限检查
claude --allow-dangerously-skip-permissions  # 允许绕过权限作为选项
claude --settings <file|json>             # 额外设置文件
claude --setting-sources user,project,local  # 设置来源

# 运行模式
claude --bare                             # 跳过 hooks/插件/LSP/归因/记忆
claude --brief                            # 启用简洁代理通信模式
claude --verbose                          # 详细日志
claude -d / --debug [filter]              # 调试模式
claude --debug-file <path>                # 调试日志文件
claude --tmux                             # tmux 会话（需 --worktree）
claude -w / --worktree [name]             # 独立 Git worktree
claude --max-budget-usd <amount>          # 最大花费（仅 --print）
claude --betas <headers>                  # Beta 功能头
claude --file <specs>                     # 启动时下载文件
claude --disable-slash-commands           # 禁用所有技能
claude --no-session-persistence           # 禁用会话持久化
```

> 证据：`claude --help` 完整输出已记录在 [EVIDENCE.md](./EVIDENCE.md)

## 使用场景

- **最适合**：复杂重构、架构决策、企业部署、长上下文分析
- **适合**：代码审查（/review 和 /security-review）、多文件编辑、CI/CD 集成、Web 前端调试（Chrome 扩展）
- **不太适合**：需要多模型切换、纯开源需求、成本敏感场景

## 优势

1. **Rust 性能**：亚秒级冷启动，低内存占用，不依赖 Node.js
2. **丰富的斜杠命令**：~79 个命令覆盖几乎所有操作场景
3. **企业管控**：5 层设置 + managed-settings 远程下发 + 沙箱隔离
4. **Prompt Hook**：22 种事件类型，LLM 推理决策（超越传统脚本 Hook）
5. **推理能力**：SWE-bench 复杂问题表现领先
6. **超长上下文**：100 万 token 上下文窗口（Opus 4.6[1m]）
7. **深度 Git 集成**：检查点、回退、worktree 隔离
8. **延迟工具加载**：按需激活工具，优化系统提示空间
9. **Chrome 扩展**：浏览器集成支持 Web 开发调试

## 劣势

1. **模型锁定**：仅支持 Claude 模型，无法切换到 GPT/Gemini
2. **闭源**：核心 Rust 二进制不可审计
3. **成本**：Opus 4.6 API 价格较高（$15/$75 per M tokens）
4. **无多提供商**：不支持自定义模型端点（不同于 aider/Cline）
5. **Linux 沙箱依赖 Docker**：不如 Gemini CLI 的 Bubblewrap/Seccomp 轻量

## 架构

- **语言**：Rust（闭源核心）+ 插件（Markdown/Python/Bash）
- **模型**：Claude Sonnet 4.6 / Opus 4.6 / Haiku 4.5（及全系列变体）
- **上下文窗口**：200K（标准）/ 1M（扩展上下文变体）
- **工具系统**：核心工具始终加载 + 延迟工具按需通过 ToolSearch 激活
- **插件结构**：`.claude-plugin/plugin.json` + commands/ + agents/ + skills/ + hooks/ + `.mcp.json`
- **Hook 系统**：22 种事件（含 UserPromptSubmit） 上下文注入

## 验证记录

> 本文档通过二进制逆向分析和官方文档双重验证。

**二进制分析（v2.1.81，227MB ELF x86-64，Bun v1.2 编译）：**
- 斜杠命令：通过 `strings` + `d4({name:"..."})` 模式提取，确认 ~75 个注册命令
- Hook 事件：通过事件名字符串匹配确认全部 22 个事件
- 工具系统：通过工具名和 Schema 字符串确认 20+ 个内置工具
- 模型 ID：通过 `claude-*` 模式匹配确认 12 个模型变体
- 原生模块：确认 tree-sitter (5 语言)、sharp、audio-capture、file-index、resvg.wasm
- 遥测系统：确认 30+ 个 `tengu_` 前缀事件
- Skill 系统：确认 SKILL.md 解析器、Frontmatter 字段、加载路径

**官方文档验证：**
- [斜杠命令/Skills](https://code.claude.com/docs/en/slash-commands)
- [Hooks 参考](https://code.claude.com/docs/en/hooks) — 22 个事件完整列表
- [模型配置](https://code.claude.com/docs/en/model-config)
- [code-review 插件源码](https://github.com/anthropics/claude-code/tree/main/plugins/code-review)

**注意：** Anthropic 文档已从 `docs.anthropic.com` 迁移至 `code.claude.com/docs`（301 重定向）。

## 资源链接

- [官方文档](https://docs.anthropic.com/en/docs/claude-code)
- [插件仓库](https://github.com/anthropics/claude-code)
- [CHANGELOG](https://github.com/anthropics/claude-code/blob/main/CHANGELOG.md)
