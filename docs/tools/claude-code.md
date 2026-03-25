# Claude Code

**开发者：** Anthropic
**许可证：** 专有（Claude Pro/Max 订阅内含，或 API 按量付费）
**仓库：** [github.com/anthropics/claude-code](https://github.com/anthropics/claude-code)（插件/示例仓库）
**文档：** [docs.anthropic.com/claude-code](https://docs.anthropic.com/en/docs/claude-code)
**最后更新：** 2026-03

## 概述

Claude Code 是 Anthropic 官方的 AI 编程代理，运行在终端中。核心为闭源 Rust 原生二进制（非 Node.js），通过原生安装脚本分发（npm 方式已废弃）。基于 Claude 系列模型（Sonnet 4.6、Opus 4.6、Haiku 4.5），拥有业界最大的 100 万 token 上下文窗口（Opus 4.6）。具备 14+ 内置工具、7 层企业级设置体系、Prompt Hook（LLM 驱动决策）、沙箱执行隔离、多代理协作等能力。它也是唯一深度集成 Anthropic 模型的终端代理工具，在 SWE-bench 等复杂编程基准上表现领先。

主要特点：
- **Rust 原生二进制**：亚秒级冷启动，低内存占用，不依赖 Node.js 运行时
- **100 万 token 上下文**：Opus 4.6 模型支持超长上下文，适合大型代码库分析
- **13 个官方插件**：code-review、feature-dev、security-guidance、hookify 等，通过 marketplace 分发
- **企业级管控**：7 层设置 + managed-settings 远程下发 + 沙箱隔离

## 核心功能

### 基础能力
- **Rust 原生二进制**：`curl install.sh | bash` 安装，亚秒级启动，低资源占用
- **14+ 内置工具**：Read、Write、Edit、Bash、Glob、Grep、WebFetch、WebSearch、Task（子代理）、Skill、TodoWrite、NotebookEdit、Agent 等
- **MCP 集成**：Stdio/SSE/Streamable-HTTP 三种传输协议，工具以 `mcp__serverName__toolName` 格式命名
- **Git 深度集成**：理解 Git 历史、创建提交/PR、worktree 隔离、checkpoint/rewind 回退
- **上下文窗口**：最高 100 万 token（Opus 4.6），支持自动上下文压缩
- **会话恢复**：`--resume` 恢复中断会话，`--session-id` 指定会话

### 独特功能
- **13 个官方插件**：code-review（4 并行代理）、feature-dev（7 阶段流程）、security-guidance、hookify 等
- **Prompt Hook**：LLM 推理驱动的 Hook 决策（不只是脚本匹配，而是让 LLM 判断是否应执行）
- **7 层设置**：企业→组织→用户→项目→本地→CLI→默认，支持远程下发
- **沙箱执行**：macOS sandbox-exec / Linux Docker 文件系统隔离 + 网络域名白名单
- **Teammates**：tmux/iTerm2 分屏多代理团队协作，每个代理独立 worktree
- **Remote Control**：`/remote-control` 桥接到 claude.ai/code 浏览器界面
- **Voice 模式**：Push-to-talk 语音交互
- **Channels**：`--channels` 允许 MCP 服务器主动推送消息到会话
- **`--bare` 模式**：脚本/CI 场景跳过 hooks/插件/LSP，纯净输出
- **CLAUDE.md**：项目级 AI 行为指令文件（类似 Gemini CLI 的 GEMINI.md）
- **Worktrees**：Git worktree 隔离并行分支，支持多代理同时操作不同分支
- **自动记忆**：跨会话学习用户偏好，存储到 `~/.claude/projects/` 目录

## 工具系统

Claude Code 内置 14+ 工具，覆盖文件操作、搜索、代码执行、Web 访问、多代理协作等场景：

| 工具 | 用途 | 说明 |
|------|------|------|
| **Read** | 读取文件内容 | 支持行范围读取、图片/PDF 查看、Jupyter Notebook 解析 |
| **Write** | 创建/覆写文件 | 整文件写入，要求先读后写 |
| **Edit** | 精确编辑文件 | 基于 old_string/new_string 的精确替换，支持 replace_all |
| **Bash** | 执行 Shell 命令 | 支持后台运行、超时控制、工作目录保持 |
| **Glob** | 文件模式搜索 | 支持 `**/*.ts` 等 glob 模式，按修改时间排序 |
| **Grep** | 内容正则搜索 | 基于 ripgrep，支持多行匹配、文件类型过滤、上下文显示 |
| **Agent** | 启动子代理 | 创建独立上下文的子代理执行复杂子任务 |
| **TaskCreate** | 创建后台任务 | 启动并行子代理任务，不阻塞主对话 |
| **TaskUpdate** | 更新任务状态 | 查询/更新后台任务进度 |
| **TaskGet** | 获取任务详情 | 读取后台任务结果 |
| **TaskList** | 列出所有任务 | 查看所有后台任务状态 |
| **WebSearch** | Web 搜索 | 搜索互联网获取最新信息 |
| **WebFetch** | 抓取网页内容 | 获取 URL 内容，HTML 转文本 |
| **NotebookEdit** | 编辑 Jupyter Notebook | 操作 .ipynb 文件的单元格 |
| **TodoWrite** | 创建待办列表 | 管理任务规划和进度追踪 |
| **Skill** | 激活技能 | 调用已注册的自定义技能 |
| **ToolSearch** | 搜索延迟工具 | 查找并加载按需注册的工具 Schema |

此外，MCP 工具以 `mcp__serverName__toolName` 格式动态注册（注意双下划线），可通过策略规则统一管控。

## 多代理系统

Claude Code 支持通过 Agent 工具和 Task 工具创建子代理，实现多代理并行协作：

### Agent 工具
Agent 工具创建一个独立上下文的子代理，继承主代理的工具集但拥有独立的对话历史。适用于：
- 探索性任务：调查代码库结构、搜索相关文件
- 独立子任务：不影响主对话上下文的操作
- 并行执行：多个子代理同时处理不同任务

### Task 工具（后台任务）
TaskCreate/TaskUpdate/TaskGet/TaskList 提供后台并行执行能力：
- **TaskCreate**：启动后台子代理，主对话不阻塞
- **TaskGet**：查询任务结果
- **TaskList**：列出所有活跃/已完成任务
- **TaskUpdate**：向运行中的任务发送更新

### Teammates（团队协作）
通过 tmux 或 iTerm2 分屏，多个 Claude Code 实例协作：
- 每个代理运行在独立的 Git worktree 中
- 支持代理间消息传递
- 适合大规模重构：一个代理负责规划，多个代理并行实现

## 7 层设置系统

Claude Code 采用 7 层优先级设置体系，从高到低：

| 层级 | 来源 | 路径/方式 | 说明 |
|------|------|-----------|------|
| 1（最高） | 系统/企业 | managed-settings 远程下发 | 管理员强制策略，不可覆盖 |
| 2 | 组织 | 组织级配置 | 跨项目组织策略 |
| 3 | 用户 | `~/.claude/settings.json` | 个人全局偏好 |
| 4 | 项目（工作区） | `.claude/settings.json`（项目根目录） | 项目级共享配置 |
| 5 | 本地 | `.claude/settings.local.json`（项目根目录） | 本地覆盖，不提交到 Git |
| 6 | CLI 参数 | `--model`、`--allowedTools` 等 | 命令行临时覆盖 |
| 7（最低） | 默认 | 内置默认值 | 兜底配置 |

**设置文件示例**（`~/.claude/settings.json`）：
```json
{
  "permissions": {
    "allow": [
      "Bash(npm test)",
      "Bash(npm run lint)",
      "Read",
      "Glob",
      "Grep"
    ],
    "deny": [
      "Bash(rm -rf /)"
    ]
  },
  "model": "claude-sonnet-4-6",
  "hooks": {}
}
```

**项目级设置**（`.claude/settings.json`）：
```json
{
  "permissions": {
    "allow": [
      "Bash(npm test)",
      "Bash(npm run build)"
    ]
  }
}
```

## Prompt Hook 系统

Claude Code 的 Hook 系统是其最独特的能力之一。与传统脚本 Hook 不同，Claude Code 支持 **LLM 驱动的 Hook 决策**——让 LLM 分析工具调用的意图和参数，决定是否允许执行。

### Hook 事件类型

| 事件 | 触发时机 | 用途 |
|------|----------|------|
| **PreToolUse** | 工具执行前 | 检查/修改/拦截工具调用 |
| **PostToolUse** | 工具执行后 | 后处理工具输出 |
| **Notification** | 通知事件 | 自定义通知（如桌面提醒） |
| **Stop** | 代理停止时 | 清理或追加操作 |
| **SubagentStop** | 子代理停止时 | 子代理完成后处理 |

### Hook 配置示例

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "python3 /path/to/check_command.py \"$TOOL_INPUT\""
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Write",
        "hooks": [
          {
            "type": "command",
            "command": "echo '文件已写入' >> /tmp/audit.log"
          }
        ]
      }
    ],
    "Notification": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "terminal-notifier -message \"$NOTIFICATION_MESSAGE\""
          }
        ]
      }
    ]
  }
}
```

### Hook 决策返回值
Hook 脚本通过 stdout 输出 JSON 控制行为：
- **approve**：允许工具调用（跳过用户确认）
- **deny**：拒绝工具调用
- **block**：阻止并附带消息
- 无输出或空输出：继续正常流程

## 权限与安全

### 沙箱模式

| 平台 | 沙箱技术 | 说明 |
|------|----------|------|
| **macOS** | sandbox-exec（Seatbelt） | 基于 Apple 沙箱配置文件，限制文件系统和网络访问 |
| **Linux** | Docker 容器 | 通过容器隔离文件系统和网络 |

### 权限控制
- **工具级白名单**：通过 `permissions.allow` 精确控制哪些工具/参数可自动执行
- **工具级黑名单**：通过 `permissions.deny` 禁止特定操作
- **模式匹配**：`Bash(npm test)` 只允许 `npm test` 命令
- **交互式确认**：未在白名单中的操作需要用户确认
- **域名限制**：网络访问可限制到特定域名

### 权限配置模式
```json
{
  "permissions": {
    "allow": [
      "Read",
      "Glob",
      "Grep",
      "Bash(npm test)",
      "Bash(npm run lint)",
      "Bash(git status)",
      "Bash(git diff *)"
    ],
    "deny": [
      "Bash(curl *)",
      "Bash(wget *)"
    ]
  }
}
```

## 会话管理

### 上下文压缩
当对话历史接近上下文窗口限制时，Claude Code 自动压缩早期对话内容，保留关键信息：
- 自动触发：接近 token 上限时
- 手动触发：`/compact` 命令

### 会话恢复
```bash
# 恢复最近会话
claude --resume

# 恢复指定会话
claude --resume <session-id>

# 继续上次对话
claude -c
```

### 检查点与回退（Checkpoint & Rewind）
- Claude Code 在每次工具调用前自动创建 Git 检查点
- 用户可通过 Esc 键回退到之前的状态
- 回退会恢复文件系统和对话历史

### Worktrees
```bash
# 在独立 worktree 中启动 Claude Code
claude --worktree
```
Git worktree 隔离允许多个 Claude Code 实例在不同分支上并行工作，互不干扰。

## 内存系统

Claude Code 的自动记忆系统跨会话保存用户偏好和项目知识：

### 记忆存储位置
```
~/.claude/
├── CLAUDE.md                    # 全局用户记忆
└── projects/
    └── <project-hash>/
        └── CLAUDE.md            # 项目特定记忆
```

### 记忆类型
- **用户偏好**：编码风格、命名规范、语言偏好
- **项目知识**：架构决策、依赖关系、构建命令
- **工作流程**：常用命令序列、测试策略

### 记忆管理
- **自动学习**：Claude Code 自动从对话中提取有用信息
- **手动管理**：`/memory` 命令查看和编辑记忆
- **MEMORY.md**：项目记忆索引文件

## MCP 集成

Claude Code 支持 Model Context Protocol（MCP），允许接入外部工具服务器：

### 传输协议

| 协议 | 说明 | 适用场景 |
|------|------|----------|
| **stdio** | 通过标准输入/输出通信 | 本地进程，最常用 |
| **sse** | Server-Sent Events | 远程服务器 |
| **streamable-http** | 可流式 HTTP | 云端部署 |

### 配置方式

**项目级**（`.claude/settings.json`）：
```json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_TOKEN": "ghp_xxx"
      }
    },
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/dir"]
    },
    "remote-server": {
      "type": "sse",
      "url": "https://mcp.example.com/sse"
    }
  }
}
```

### 工具命名
MCP 工具以 `mcp__serverName__toolName` 格式注册（双下划线分隔）。例如：
- `mcp__github__create_issue`
- `mcp__filesystem__read_file`

## CLAUDE.md 项目配置

CLAUDE.md 是 Claude Code 的项目级指令文件，类似于 Gemini CLI 的 GEMINI.md。它告诉 Claude Code 项目的背景、规范和偏好。

### 层级结构

| 位置 | 作用域 | 说明 |
|------|--------|------|
| `~/.claude/CLAUDE.md` | 全局 | 所有项目通用的个人偏好 |
| 项目根目录 `CLAUDE.md` | 项目 | 项目级指令，提交到 Git 共享给团队 |
| 子目录 `CLAUDE.md` | 目录 | 仅在操作该目录内文件时加载 |
| `.claude/CLAUDE.md` | 项目（隐藏） | 项目配置目录下的指令 |

### 内容建议

```markdown
# CLAUDE.md

## 项目概述
这是一个 React + TypeScript 前端项目，使用 Vite 构建。

## 开发命令
- `npm run dev` - 启动开发服务器
- `npm test` - 运行测试
- `npm run lint` - 代码检查
- `npm run build` - 构建生产版本

## 代码规范
- 使用 TypeScript strict 模式
- 组件使用函数式组件 + Hooks
- 文件命名使用 kebab-case
- 测试文件使用 .test.ts 后缀

## 架构说明
- src/components/ - React 组件
- src/hooks/ - 自定义 Hooks
- src/utils/ - 工具函数
- src/api/ - API 请求层
```

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
claude --allowedTools "Read,Glob,Grep"    # 限制可用工具
claude --bare                             # 脚本模式（跳过 hooks/插件）
```

### 高级选项
```bash
claude --channels                         # 启用 MCP 消息推送
claude --worktree                         # 在独立 worktree 中运行
claude --output-format json               # JSON 输出格式
claude --output-format stream-json        # 流式 JSON 输出
claude --max-turns 10                     # 限制最大轮次
claude --verbose                          # 详细日志输出
```

### 斜杠命令（交互式会话内）

| 命令 | 用途 |
|------|------|
| `/review` | 代码审查——自动分析当前 diff 或指定 PR，生成审查意见 |
| `/help` | 显示帮助信息 |
| `/compact` | 压缩对话历史，释放上下文空间 |
| `/clear` | 清除对话历史 |
| `/memory` | 查看/编辑记忆文件 |
| `/model` | 切换模型（Sonnet/Opus/Haiku） |
| `/permissions` | 管理工具权限（allow/deny 规则） |
| `/mcp` | 查看 MCP 服务器连接状态 |
| `/remote-control` | 启用远程控制，桥接到 claude.ai/code |
| `/cost` | 查看当前会话 token 消耗和费用 |
| `/login` | 切换账户或重新登录 |
| `/logout` | 登出当前账户 |
| `/config` | 查看/修改配置（主题、通知等） |
| `/vim` | 切换 Vim 编辑模式 |

## Teammates 与远程控制

### Teammates（tmux/iTerm2 协作）
Teammates 允许多个 Claude Code 实例以团队形式协作：

```bash
# 通过 tmux 启动多代理团队
claude --teammates "agent1:实现前端组件" "agent2:编写后端API" "agent3:编写测试"
```

- 每个代理运行在独立的 tmux/iTerm2 窗格中
- 每个代理使用独立的 Git worktree
- 代理之间可以通过消息进行协调
- 适合大规模重构和多模块并行开发

### Remote Control
```bash
# 在终端启用远程控制
/remote-control
```
允许通过 claude.ai/code 浏览器界面远程操控终端中的 Claude Code 实例，实现：
- 浏览器端查看终端代理的实时输出
- 从浏览器发送指令到终端代理
- 多设备协作

## 安装

```bash
# 推荐方式（原生二进制）
curl -fsSL https://claude.ai/install.sh | bash

# Homebrew（macOS）
brew install --cask claude-code

# npm（已 deprecated，不推荐）
npm install -g @anthropic-ai/claude-code
```

## 架构

- **语言**：Rust（闭源核心）+ 插件（Markdown/Python/Bash）
- **模型**：Claude Sonnet 4.6 / Opus 4.6 / Haiku 4.5
- **上下文窗口**：200K（Sonnet 4.6）/ 1M（Opus 4.6）
- **插件结构**：`.claude-plugin/plugin.json` + commands/ + agents/ + skills/ + hooks/ + `.mcp.json`

## 配置示例

### 完整设置文件（`~/.claude/settings.json`）
```json
{
  "model": "claude-sonnet-4-6",
  "permissions": {
    "allow": [
      "Read",
      "Glob",
      "Grep",
      "Bash(npm test)",
      "Bash(npm run lint)",
      "Bash(git *)"
    ],
    "deny": [
      "Bash(rm -rf *)",
      "Bash(curl *)"
    ]
  },
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_TOKEN": "ghp_xxx"
      }
    }
  },
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "python3 ~/.claude/hooks/check_bash.py"
          }
        ]
      }
    ],
    "Notification": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "notify-send 'Claude Code' \"$CLAUDE_NOTIFICATION\""
          }
        ]
      }
    ]
  }
}
```

### 项目级配置（`.claude/settings.json`）
```json
{
  "permissions": {
    "allow": [
      "Bash(npm test)",
      "Bash(npm run build)",
      "Bash(npx prisma *)"
    ]
  },
  "mcpServers": {
    "database": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-postgres"],
      "env": {
        "DATABASE_URL": "postgresql://localhost:5432/mydb"
      }
    }
  }
}
```

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

## 优势

1. **Rust 性能**：亚秒级冷启动，低内存占用，不依赖 Node.js
2. **插件生态**：13 个官方插件，marketplace 支持第三方插件
3. **企业管控**：7 层设置 + managed-settings 远程下发 + 沙箱隔离
4. **Prompt Hook**：LLM 推理决策（超越传统脚本 Hook）
5. **推理能力**：SWE-bench 复杂问题表现领先
6. **超长上下文**：100 万 token 上下文窗口（Opus 4.6）
7. **深度 Git 集成**：检查点、回退、worktree 隔离

## 劣势

1. **模型锁定**：仅支持 Claude 模型，无法切换到 GPT/Gemini
2. **闭源**：核心 Rust 二进制不可审计
3. **成本**：Opus 4.6 API 价格较高（$15/$75 per M tokens）
4. **无多提供商**：不支持自定义模型端点（不同于 aider/Cline）
5. **Linux 沙箱依赖 Docker**：不如 Gemini CLI 的 Bubblewrap/Seccomp 轻量

## 使用场景

- **最适合**：复杂重构、架构决策、企业部署、长上下文分析
- **适合**：代码审查（code-review 插件）、多文件编辑、CI/CD 集成
- **不太适合**：需要多模型切换、纯开源需求、成本敏感场景

## 资源链接

- [官方文档](https://docs.anthropic.com/en/docs/claude-code)
- [插件仓库](https://github.com/anthropics/claude-code)
- [CHANGELOG](https://github.com/anthropics/claude-code/blob/main/CHANGELOG.md)
- [API 定价](https://www.anthropic.com/pricing)
- [SWE-bench 结果](https://www.swebench.com/)
