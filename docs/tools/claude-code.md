# Claude Code

**开发者：** Anthropic
**许可证：** 专有（Claude Pro/Max 订阅内含，或 API 按量付费）
**仓库：** [github.com/anthropics/claude-code](https://github.com/anthropics/claude-code)（插件/示例仓库）
**文档：** [docs.anthropic.com/claude-code](https://docs.anthropic.com/en/docs/claude-code)
**最后更新：** 2026-03

## 概述

Claude Code 是 Anthropic 官方的 AI 编程代理，运行在终端中。核心为闭源 Rust 原生二进制（非 Node.js），通过原生安装脚本分发（npm 方式已废弃）。基于 Claude 系列模型（Sonnet 4.6、Opus 4.6、Haiku 4.5），拥有业界最大的 100 万 token 上下文窗口（Opus 4.6[1m]）。具备 20+ 内置工具（含延迟加载工具）、7 层企业级设置体系、10 种 Prompt Hook 事件、沙箱执行隔离、多代理协作、~60 个斜杠命令等能力。它也是唯一深度集成 Anthropic 模型的终端代理工具，在 SWE-bench 等复杂编程基准上表现领先。

主要特点：
- **Rust 原生二进制**：亚秒级冷启动，低内存占用，不依赖 Node.js 运行时
- **100 万 token 上下文**：Opus 4.6[1m] 模型支持超长上下文，适合大型代码库分析
- **~60 个斜杠命令**：覆盖会话管理、Git 操作、配置调整、插件激活等
- **企业级管控**：7 层设置 + managed-settings 远程下发 + 沙箱隔离
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
- **Prompt Hook**：10 种事件类型，支持 LLM 推理驱动的 Hook 决策
- **7 层设置**：企业->组织->用户->项目->本地->CLI->默认，支持远程下发
- **沙箱执行**：macOS sandbox-exec / Linux Docker 文件系统隔离 + 网络域名白名单
- **Teammates**：tmux/iTerm2 分屏多代理团队协作，每个代理独立 worktree
- **Remote Control**：`/remote-control` 桥接到 claude.ai/code 浏览器界面
- **Voice 模式**：`/voice` 命令启动 Push-to-talk 语音交互，基于 speech-to-text API
- **Channels**：`--channels` 允许 MCP 服务器主动推送消息到会话
- **`--bare` 模式**：脚本/CI 场景跳过 hooks/插件/LSP，纯净输出
- **CLAUDE.md**：项目级 AI 行为指令文件（类似 Gemini CLI 的 GEMINI.md）
- **Worktrees**：Git worktree 隔离并行分支，支持多代理同时操作不同分支
- **自动记忆**：跨会话学习用户偏好，存储到 `~/.claude/projects/` 目录
- **Chrome 扩展**（Beta）：浏览器标签页集成，提供页面读取、网络请求监控等能力
- **延迟工具加载**：通过 ToolSearch 按需加载不常用工具，减少系统提示占用

## 工具系统

Claude Code 内置 20+ 工具，分为核心工具、延迟加载工具和内部工具三类。

### 核心工具（始终可用）

| 工具 | 用途 | 说明 |
|------|------|------|
| **Read** | 读取文件内容 | 支持行范围读取、图片/PDF 查看、Jupyter Notebook 解析 |
| **Write** | 创建/覆写文件 | 整文件写入，要求先读后写 |
| **Edit** | 精确编辑文件 | 基于 old_string/new_string 的精确替换，支持 replace_all |
| **MultiEdit** | 批量编辑文件 | 对同一文件执行多次编辑操作，减少工具调用次数 |
| **Bash** | 执行 Shell 命令 | 支持后台运行、超时控制、工作目录保持 |
| **Glob** | 文件模式搜索 | 支持 `**/*.ts` 等 glob 模式，按修改时间排序 |
| **Grep** | 内容正则搜索 | 基于 ripgrep，支持多行匹配、文件类型过滤、上下文显示 |
| **Agent** | 启动子代理 | 创建独立上下文的子代理执行复杂子任务 |
| **TodoWrite** | 创建待办列表 | 管理任务规划和进度追踪 |

### 延迟加载工具（通过 ToolSearch 按需激活）

| 工具 | 用途 | 说明 |
|------|------|------|
| **WebFetch** | 抓取网页内容 | 获取 URL 内容，HTML 转文本 |
| **WebSearch** | Web 搜索 | 搜索互联网获取最新信息 |
| **NotebookEdit** | 编辑 Jupyter Notebook | 操作 .ipynb 文件的单元格 |
| **TaskCreate** | 创建后台任务 | 启动并行子代理任务，不阻塞主对话 |
| **TaskGet** | 获取任务详情 | 读取后台任务结果 |
| **TaskList** | 列出所有任务 | 查看所有后台任务状态 |
| **TaskUpdate** | 更新任务状态 | 向运行中的任务发送更新 |
| **CronCreate** | 创建定时任务 | 设置定时执行的自动化任务 |
| **CronDelete** | 删除定时任务 | 移除已创建的定时任务 |
| **CronList** | 列出定时任务 | 查看所有定时任务列表 |
| **EnterWorktree** | 进入 Worktree | 切换到独立的 Git worktree 工作区 |
| **ExitWorktree** | 退出 Worktree | 返回主工作区 |
| **RemoteTrigger** | 远程触发 | 触发远程操作或工作流 |
| **ToolSearch** | 搜索延迟工具 | 查找并加载按需注册的工具 Schema |

### 内部工具

| 工具 | 用途 | 说明 |
|------|------|------|
| **KillShell** | 终止 Shell | 终止正在运行的后台 Shell 进程 |
| **Brief** | 简洁模式 | 控制响应的详细程度 |
| **Skill** | 激活技能 | 调用已注册的自定义技能/斜杠命令 |

此外，MCP 工具以 `mcp__serverName__toolName` 格式动态注册（注意双下划线），可通过策略规则统一管控。

## 斜杠命令

Claude Code v2.1.81 包含约 60 个斜杠命令，按执行类型分为四类。

### prompt 类型（发送提示给 LLM）

| 命令 | 用途 |
|------|------|
| `/commit` | 分析当前 diff 并生成规范化 commit |
| `/commit-push-pr` | 一键完成 commit、push 和创建 PR |
| `/init` | 初始化项目的 CLAUDE.md 配置文件 |
| `/init-verifiers` | 初始化验证器配置（测试/lint 等自动检查） |
| `/insights` | 分析项目代码并生成见解摘要 |
| `/review` | 代码审查——自动分析当前 diff 或指定 PR，生成审查意见 |

### local-jsx 类型（本地 React/Ink UI 渲染）

| 命令 | 用途 |
|------|------|
| `/add-dir` | 添加额外目录到当前会话的工作区 |
| `/agents` | 查看和管理子代理状态 |
| `/branch` | 创建或切换 Git 分支 |
| `/brief` | 切换简洁输出模式 |
| `/btw` | 发送旁注消息（不打断当前任务） |
| `/color` | 配置终端颜色方案 |
| `/config` | 查看/修改配置（主题、通知等） |
| `/copy` | 复制最近响应到剪贴板 |
| `/desktop` | 配置桌面应用集成 |
| `/diff` | 查看当前文件变更的 diff |
| `/effort` | 调整推理努力程度（低/中/高） |
| `/exit` | 退出当前会话 |
| `/export` | 导出对话历史 |
| `/extra-usage` | 查看额外用量信息 |
| `/fast` | 切换到快速模式（使用较小模型） |
| `/feedback` | 提交反馈或报告问题 |
| `/help` | 显示帮助信息和可用命令列表 |
| `/hooks` | 查看和管理 Prompt Hook 配置 |
| `/ide` | 配置 IDE 集成（VS Code 等） |
| `/install` | 安装 Claude Code 组件或更新 |
| `/install-github-app` | 安装 Claude Code GitHub App |
| `/login` | 切换账户或重新登录 |
| `/logout` | 登出当前账户 |
| `/mcp` | 查看 MCP 服务器连接状态和工具列表 |
| `/memory` | 查看/编辑 CLAUDE.md 记忆文件 |
| `/mobile` | 配置移动端远程访问 |
| `/model` | 切换模型（Sonnet/Opus/Haiku） |
| `/output-style` | 设置输出风格（已废弃，用 `/brief` 替代） |
| `/passes` | 配置多轮验证通过次数 |
| `/permissions` | 管理工具权限（allow/deny 规则） |
| `/plan` | 切换计划模式（仅规划不执行） |
| `/plugin` | 管理插件（安装/卸载/列表） |
| `/privacy-settings` | 查看和修改隐私设置 |
| `/rate-limit-options` | 查看速率限制选项和当前状态 |
| `/remote-control` | 启用远程控制，桥接到 claude.ai/code |
| `/remote-env` | 配置远程环境连接 |
| `/rename` | 重命名当前会话 |
| `/resume` | 恢复之前的会话 |
| `/session` | 管理会话（列表/切换/删除） |
| `/skills` | 查看已注册的技能列表 |
| `/stats` | 查看会话统计信息（token 用量等） |
| `/status` | 显示当前状态（模型、工具、MCP 等） |
| `/tag` | 为当前会话添加标签 |
| `/tasks` | 查看和管理后台任务 |
| `/terminal-setup` | 配置终端环境 |
| `/theme` | 切换界面主题 |
| `/think-back` | 回溯思考（重新审视之前的推理） |
| `/upgrade` | 升级 Claude Code 到最新版本 |
| `/usage` | 查看 token 用量和费用统计 |
| `/web-setup` | 配置 Web 相关设置 |

### local 类型（直接本地执行，不涉及 LLM）

| 命令 | 用途 |
|------|------|
| `/clear` | 清除对话历史 |
| `/compact` | 压缩对话历史，释放上下文空间 |
| `/context` | 查看当前上下文窗口使用情况 |
| `/cost` | 查看当前会话 token 消耗和费用 |
| `/doctor` | 诊断 Claude Code 运行环境问题 |
| `/files` | 查看当前会话已读取的文件列表 |
| `/keybindings` | 查看和配置快捷键 |
| `/release-notes` | 查看当前版本的发布说明 |
| `/vim` | 切换 Vim 编辑模式 |
| `/voice` | 启动语音模式（Push-to-talk） |
| `/stickers` | 彩蛋——显示 Claude 贴纸 |

### Skill/插件提供的命令

> Skill 通过 SKILL.md 文件定义，由 Skill 系统动态加载。与内置命令不同，Skill 是可扩展的——用户和插件都可以定义新的 `/command`。

| 命令 | 来源 | 用途 |
|------|------|------|
| `/security-review` | 官方插件 | 安全审查——对当前分支的代码变更进行安全漏洞分析 |
| `/pr-comments` | 官方插件 | 查看和处理 PR 评论 |
| `/commit` | 内置 Skill | 提交暂存的更改 |
| `/review` | 内置 Skill | 代码审查——分析 diff 或指定 PR |
| `/init` | 内置 Skill | 初始化项目配置 |
| `/loop` | 内置 Skill | 按间隔循环执行命令（如 `/loop 5m /review`） |
| `/schedule` | 内置 Skill | 管理定时远程代理任务（cron 调度） |
| `/simplify` | 内置 Skill | 审查修改过的代码，检查复用、质量和效率 |
| `/claude-api` | 内置 Skill | 使用 Claude API/Anthropic SDK 构建应用时触发 |
| `/update-config` | 内置 Skill | 配置 settings.json（hooks、权限、环境变量等） |
| `/keybindings-help` | 内置 Skill | 自定义键盘快捷键绑定 |

**自定义 Skill 示例**（`.claude/skills/my-skill/SKILL.md`）：
```markdown
---
name: 我的自定义技能
description: 执行自定义操作
user-invocable: true
allowed-tools: ["Bash", "Edit"]
---

你的技能提示内容...
```

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

## 7 层设置系统

Claude Code 采用 7 层优先级设置体系，从高到低：

| 层级 | 来源 | 路径/方式 | 说明 |
|------|------|-----------|------|
| 1（最高） | 系统/企业 | managed-settings 远程下发 | 管理员强制策略，不可覆盖 |
| 2 | 工作区 | `.claude/settings.json`（项目根目录） | 项目级共享配置 |
| 3 | 用户 | `~/.claude/settings.json` | 个人全局偏好 |
| 4 | 组织 | 组织级配置 | 跨项目组织策略 |
| 5 | 本地 | `.claude/settings.local.json`（项目根目录） | 本地覆盖，不提交到 Git |
| 6 | CLI 参数 | `--model`、`--allowedTools` 等 | 命令行临时覆盖 |
| 7（最低） | 默认 | 内置默认值 | 兜底配置 |

**注意**：系统设置（managed-settings）优先级最高，工作区设置优先于用户设置。

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
| **SubagentStart** | 子代理启动时 | 子代理创建前的准备或检查 |
| **SubagentStop** | 子代理停止时 | 子代理完成后处理 |
| **SessionStart** | 会话开始时 | 初始化操作（如环境检查） |
| **Setup** | 初始设置时 | 首次配置时的自动化操作 |
| **Stop** | 代理停止时 | 清理或追加操作 |
| **PreCompact** | 上下文压缩前 | 压缩前保存关键信息 |
| **PostCompact** | 上下文压缩后 | 压缩后注入补充上下文 |

此外，**UserPromptSubmit** 可用于在用户提交提示时注入额外上下文信息。

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
    ],
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 /path/to/check_env.py"
          }
        ]
      }
    ],
    "PreCompact": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "echo '即将压缩上下文' >> /tmp/audit.log"
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
- Hook 支持：PreCompact/PostCompact 事件允许自定义压缩前后行为

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
Git worktree 隔离允许多个 Claude Code 实例在不同分支上并行工作，互不干扰。EnterWorktree/ExitWorktree 工具支持在会话内动态切换 worktree。

## 内存系统

Claude Code 的记忆系统通过 CLAUDE.md 文件跨会话保存项目知识和用户偏好：

### CLAUDE.md 层级结构

```
~/.claude/CLAUDE.md                      # 全局记忆（所有项目通用偏好）
<project-root>/CLAUDE.md                 # 项目级记忆（提交到 Git 共享给团队）
<project-root>/.claude/CLAUDE.md         # 项目隐藏配置目录下的记忆
<subdirectory>/CLAUDE.md                 # 子目录级记忆（操作该目录文件时加载）
~/.claude/projects/<project-hash>/CLAUDE.md  # 用户私有的项目特定记忆（不提交到 Git）
```

### 记忆内容类型
- **项目知识**：架构决策、技术栈说明、构建/测试命令
- **代码规范**：编码风格、命名约定、文件组织规则
- **用户偏好**：语言偏好、交互风格、常用工作流

### 记忆管理
- **自动学习**：Claude Code 在对话中识别到有价值的项目知识时，自动提议保存到 CLAUDE.md
- **手动管理**：`/memory` 命令查看和编辑记忆文件（在外部编辑器中打开）
- **层级合并**：会话开始时自动加载所有层级的 CLAUDE.md，合并为系统提示的一部分
- **与 Gemini CLI 对比**：机制类似（分层 Markdown 文件），但 Claude Code 使用 CLAUDE.md，Gemini CLI 使用 GEMINI.md

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

## Chrome 扩展（Beta）

Claude Code 提供 Chrome 浏览器扩展，支持在终端代理中直接操作浏览器标签页。通过 MCP 协议桥接，提供以下工具：

| 工具 | 用途 |
|------|------|
| **tabs_context_mcp** | 获取当前打开的标签页上下文信息 |
| **tabs_create_mcp** | 创建新的浏览器标签页 |
| **read_page** | 读取页面内容（DOM 文本） |
| **read_console_messages** | 读取浏览器控制台消息 |
| **read_network_requests** | 读取网络请求记录 |
| **switch_browser** | 切换到指定标签页 |
| **navigate** | 导航到指定 URL |
| **resize_window** | 调整浏览器窗口大小 |

使用 `/web-setup` 命令配置 Chrome 扩展连接。

## 语音模式

通过 `/voice` 命令启动语音交互模式：

- **Push-to-talk**：按住快捷键说话，松开后自动转录为文字输入
- **语音识别**：基于 speech-to-text API 实现语音转文字
- **适用场景**：手不方便打字时、快速口述需求、代码审查讨论

## 插件系统

Claude Code 通过 `/plugin` 命令管理插件，支持从 marketplace 安装：

### 插件管理
```bash
/plugin                  # 查看插件管理界面
/plugin install <name>   # 安装插件
/plugin list             # 列出已安装插件
```

### 官方插件示例

| 插件 | 用途 |
|------|------|
| **security-review** | 安全漏洞审查，对应 `/security-review` 命令 |
| **pr-comments** | PR 评论处理，对应 `/pr-comments` 命令 |

### 插件结构
```
.claude-plugin/
  plugin.json            # 插件元数据和配置
  commands/              # 自定义斜杠命令
  agents/                # 代理模板
  skills/                # 技能定义
  hooks/                 # Hook 脚本
  .mcp.json              # 插件 MCP 服务器配置
```

## Skill 系统实现机制

> 以下基于 v2.1.81 二进制逆向分析和运行时观察。Skill 是 Claude Code 的命令扩展机制——用户看到的 `/commit`、`/review`、`/loop` 等都是 Skill。

### Skill 定义格式（SKILL.md）

每个 Skill 是一个 Markdown 文件，通过 YAML Frontmatter 声明元数据：

```markdown
---
name: 技能显示名
description: 技能描述（用于模型判断何时调用）
user-invocable: true          # 是否在 / 菜单中显示
disable-model-invocation: false # 是否禁止模型主动调用
allowed-tools: ["Bash", "Edit", "Read"]  # 允许使用的工具
argument-hint: "<参数说明>"    # 参数提示
when_to_use: "当用户要求..."   # 触发条件描述
model: sonnet                  # 使用的模型（可选，默认继承）
effort: high                   # 推理努力级别
context: fork                  # 执行上下文（fork = 独立上下文）
shell: bash                    # Shell 类型
---

你的技能提示内容...可以使用 ${CLAUDE_SKILL_DIR} 引用技能目录
```

### Skill 加载路径（优先级从高到低）

| 来源 | 路径 | 说明 |
|------|------|------|
| 管理员策略 | `~/.claude/settings.json` 中的 policySettings | 企业管控，不可覆盖 |
| 用户级 | `~/.claude/skills/` | 个人全局技能 |
| 项目级 | `<project>/.claude/skills/` | 项目共享技能（可提交到 Git） |
| 附加目录 | `--add-dir` 指定目录的 `.claude/skills/` | 运行时附加 |
| 旧版 commands | `.claude/commands/` 目录（DEPRECATED） | 向后兼容 |

### Skill 类型

| 类型 | 注册方式 | 执行方式 |
|------|----------|----------|
| **prompt** | SKILL.md 文件 | 将 Markdown 内容作为提示发送给 LLM |
| **local-jsx** | 代码内注册 | 渲染本地 React/Ink UI 组件 |
| **local** | 代码内注册 | 直接本地执行（不调用 LLM） |

### Skill 加载流程（源码分析）

```
启动 → pdA() 扫描所有 Skill 目录
     → 读取每个 SKILL.md 的 Frontmatter
     → hw() 解析 YAML 元数据
     → 去重（同一文件不同路径只保留一个）
     → 条件 Skill 暂存到 TTH Map（等待匹配文件被访问时激活）
     → 无条件 Skill 注册到 Vn Map（全局命令注册表）
```

**条件激活（Conditional Skills）**：
- Skill 的 Frontmatter 中可设置 `paths` 字段（glob 模式数组）
- 只有当用户操作匹配的文件时，该 Skill 才被激活
- 使用 `ignore` 库匹配（类似 .gitignore 规则）
- 一旦激活，发射 `tengu_dynamic_skills_changed` 事件通知 UI 更新

**去重机制**：
- 使用文件内容哈希（crypto SHA）判断是否为同一 Skill
- 多个路径发现同一文件时，保留先发现的，记录来源

### 内置 Skill 详情

| Skill | 实现 | 工作流 |
|-------|------|--------|
| `/commit` | prompt 类型 | 分析 `git diff --staged`，生成提交消息，执行 `git commit` |
| `/review` | prompt 类型 | 获取 diff 或 PR 信息，分析代码变更，生成审查意见 |
| `/commit-push-pr` | prompt 类型 | commit + push + 创建 PR 一键完成 |
| `/init` | prompt 类型 | 分析项目结构，生成/更新 CLAUDE.md |
| `/init-verifiers` | prompt 类型 | 创建 verifier Skill 用于自动化验证代码变更 |
| `/loop` | prompt 类型 | 按间隔重复执行命令（默认 10 分钟），如 `/loop 5m /review` |
| `/schedule` | prompt 类型 | 管理 cron 定时远程代理任务（创建/更新/列出/执行） |
| `/simplify` | prompt 类型 | 审查已修改代码的复用性、质量和效率 |
| `/update-config` | prompt 类型 | 通过对话式界面修改 settings.json |
| `/claude-api` | prompt 类型 | 导入 anthropic SDK 时自动触发，辅助 API 开发 |

## 内部特性（Codenames）

通过二进制分析发现的内部标识符：

| 代号 | 推测用途 |
|------|----------|
| **tengu** | 遥测系统（telemetry） |
| **penguin** | Penguin 模式（可能与 Linux 沙箱相关） |
| **grove** | 内部功能标识（具体用途未公开） |

### API 端点
Claude Code 与 Anthropic 后端通信使用以下 API 端点：
- **team_memory**：团队共享记忆同步
- **policy_limits**：策略限制查询
- **settings**：远程设置下发

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

## 技术架构（二进制逆向分析）

> 以下基于 v2.1.81 二进制分析。Claude Code 是闭源产品，无公开源码。

### 运行时

| 项目 | 详情 |
|------|------|
| **二进制格式** | ELF 64-bit LSB executable, x86-64, dynamically linked |
| **大小** | ~227 MB（单文件可执行） |
| **运行时** | **Bun v1.2**（非 Node.js），Bun 编译的单文件打包 |
| **UI 框架** | Ink（React for CLI）+ Yoga 布局引擎 |
| **分发方式** | `curl install.sh` 下载二进制到 `~/.local/share/claude/versions/` |

### 内嵌原生模块

| 模块 | 用途 |
|------|------|
| `tree-sitter-bash.node` | Bash AST 解析 |
| `tree-sitter-typescript.node` | TypeScript AST 解析 |
| `tree-sitter-json.node` | JSON 解析 |
| `tree-sitter-yaml.node` | YAML 解析 |
| `tree-sitter-kotlin.node` | Kotlin 解析 |
| `sharp.node` / `image-processor.node` | 图片处理（Sharp 库） |
| `audio-capture.node` | 音频捕获（语音模式） |
| `file-index.node` | 文件索引（代码搜索） |
| `color-diff.node` | 颜色 diff 显示 |
| `yaml.node` | YAML 解析 |
| `resvg.wasm` | SVG 渲染（WebAssembly） |

### API 层

| 端点 | 用途 |
|------|------|
| `api.anthropic.com/v1/messages` | 核心 LLM API（Claude 模型调用） |
| `claude.ai/api/oauth/authorize` | OAuth 认证 |
| `claude.ai/api/claude_code/settings` | 远程设置获取 |
| `claude.ai/api/claude_code/policy_limits` | 策略限制查询 |
| `claude.ai/api/claude_code/team_memory` | 团队记忆（按仓库） |
| `claude.ai/api/ws/speech_to_text/voice_stream` | 语音转文字（WebSocket） |
| `claude.ai/api/claude_cli_feedback` | 反馈提交 |
| `claude.ai/api/claude_code/metrics` | 遥测上报 |

### 遥测系统（tengu）

内置 30+ 个 `tengu_` 前缀的遥测事件，涵盖：
- **代理生命周期**：`tengu_agent_created`、`tengu_agent_tool_selected`、`tengu_agent_tool_completed`
- **API 交互**：`tengu_api`、`tengu_api_error`、`tengu_api_opus_fallback_triggered`、`tengu_api_cache_breakpoints`
- **特性标志**：`tengu_amber_flint`、`tengu_amber_prism`、`tengu_amber_quartz_disabled`（A/B 测试系统）
- **压缩**：`tengu_compact_failed`
- **Skill 变更**：`tengu_dynamic_skills_changed`

### 消息类型（Content Block）

| 类型 | 说明 |
|------|------|
| `Text` | 文本内容 |
| `Thinking` / `RedactedThinking` | 思维过程（可编辑/可屏蔽） |
| `ToolUse` / `ServerToolUse` | 客户端/服务端工具调用 |
| `McpToolUse` / `McpToolResult` | MCP 工具调用与结果 |
| `WebSearchToolResult` / `WebFetchToolResult` | Web 搜索/抓取结果 |
| `CodeExecutionToolResult` / `BashCodeExecutionToolResult` | 代码执行结果 |
| `Compaction` | 压缩摘要 |
| `ContainerUpload` | 容器上传 |

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

### 高级选项
```bash
claude --channels                         # 启用 MCP 消息推送
claude --worktree                         # 在独立 worktree 中运行
claude --output-format json               # JSON 输出格式
claude --output-format stream-json        # 流式 JSON 输出
claude --max-turns 10                     # 限制最大轮次
claude --verbose                          # 详细日志输出
```

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
- **模型**：Claude Sonnet 4.6 / Opus 4.6 / Haiku 4.5（及全系列变体）
- **上下文窗口**：200K（标准）/ 1M（扩展上下文变体）
- **工具系统**：核心工具始终加载 + 延迟工具按需通过 ToolSearch 激活
- **插件结构**：`.claude-plugin/plugin.json` + commands/ + agents/ + skills/ + hooks/ + `.mcp.json`
- **Hook 系统**：10 种事件 + UserPromptSubmit 上下文注入

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
    ],
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 ~/.claude/hooks/session_init.py"
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
2. **丰富的斜杠命令**：~60 个命令覆盖几乎所有操作场景
3. **企业管控**：7 层设置 + managed-settings 远程下发 + 沙箱隔离
4. **Prompt Hook**：10 种事件类型，LLM 推理决策（超越传统脚本 Hook）
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

## 使用场景

- **最适合**：复杂重构、架构决策、企业部署、长上下文分析
- **适合**：代码审查（/review 和 /security-review）、多文件编辑、CI/CD 集成、Web 前端调试（Chrome 扩展）
- **不太适合**：需要多模型切换、纯开源需求、成本敏感场景

## 资源链接

- [官方文档](https://docs.anthropic.com/en/docs/claude-code)
- [插件仓库](https://github.com/anthropics/claude-code)
- [CHANGELOG](https://github.com/anthropics/claude-code/blob/main/CHANGELOG.md)
- [API 定价](https://www.anthropic.com/pricing)
- [SWE-bench 结果](https://www.swebench.com/)
