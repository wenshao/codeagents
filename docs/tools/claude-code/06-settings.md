# 6. 设置与安全

## 5 层设置优先级体系

Claude Code 采用 5 层优先级设置体系，从高到低：

| 优先级 | 来源 | 路径/方式 | 说明 |
|--------|------|-----------|------|
| 1（最高） | Managed（托管） | `managed-settings.json`（MDM 部署/服务器下发） | 管理员强制策略，不可覆盖 |
| 2 | CLI 参数 | `--model`、`--allowedTools` 等 | 命令行参数覆盖所有项目及用户设置 |
| 3 | 本地项目 | `.claude/settings.local.json`（项目根目录） | 本地覆盖，不提交到 Git |
| 4 | 共享项目 | `.claude/settings.json`（项目根目录） | 项目级共享配置，提交到 Git |
| 5（最低） | 用户 | `~/.claude/settings.json` | 个人全局偏好 |

**注意**：Managed 设置优先级最高；CLI 参数优先级高于项目设置；本地项目设置（`.local.json`）优先于共享项目设置。

> **第六轮修正：** 原文档声称"7 层设置系统"，经官方文档（code.claude.com/docs/en/settings）验证，实际为 5 层优先级体系。优先级从高到低为：Managed > CLI 参数 > 本地项目 > 共享项目 > 用户。原"Organization"层不存在，CLI 参数优先级高于项目设置（非最低）。

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

### Hook 事件类型（22 种）

| 事件 | 触发时机 | 来源 |
|------|----------|------|
| `SessionStart` | 会话开始时 | 二进制+官方 |
| `SessionEnd` | 会话结束时 | 官方 |
| `UserPromptSubmit` | 用户提交提示时 | 二进制+官方 |
| `PreToolUse` | 工具执行前 | 二进制+官方 |
| `PostToolUse` | 工具执行成功后 | 二进制+官方 |
| `PostToolUseFailure` | 工具执行失败后 | 官方 |
| `PermissionRequest` | 请求权限时 | 官方 |
| `Notification` | 通知事件 | 二进制+官方 |
| `SubagentStart` | 子代理启动时 | 二进制+官方 |
| `SubagentStop` | 子代理停止时 | 二进制+官方 |
| `Stop` | 代理停止时 | 二进制+官方 |
| `StopFailure` | 代理停止失败时 | 官方 |
| `PreCompact` | 上下文压缩前 | 二进制+官方 |
| `PostCompact` | 上下文压缩后 | 二进制+官方 |
| `TaskCompleted` | 后台任务完成时 | 官方 |
| `TeammateIdle` | Teammate 空闲时 | 官方 |
| `InstructionsLoaded` | 指令文件加载时 | 官方 |
| `ConfigChange` | 配置变更时 | 官方 |
| `WorktreeCreate` | 创建 Git worktree 时 | 官方 |
| `WorktreeRemove` | 移除 Git worktree 时 | 官方 |
| `Elicitation` | 向用户请求信息时 | 官方 |
| `ElicitationResult` | 用户回复请求时 | 官方 |

> 来源：[官方 Hooks 文档](https://code.claude.com/docs/en/hooks)，全部 22 个事件在 v2.1.81 二进制中确认存在。

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

### 权限规则语法（二进制提取 + 官方文档）

规则格式：`ToolName` 或 `ToolName(specifier)`，支持通配符 `*`。

**Bash 命令规则（从二进制提取的内置模式，38 个）：**

| 模式 | 说明 |
|------|------|
| `Bash(git:*)` | 所有 git 命令 |
| `Bash(git add:*)` | git add 及其参数 |
| `Bash(git commit:*)` | git commit |
| `Bash(git push:*)` | git push |
| `Bash(git diff:*)` | git diff |
| `Bash(git log:*)` | git log |
| `Bash(git status:*)` | git status |
| `Bash(git show:*)` | git show |
| `Bash(git checkout -b:*)` | 创建新分支 |
| `Bash(git checkout --branch:*)` | 创建新分支（长参数） |
| `Bash(git remote show:*)` | 查看远程信息 |
| `Bash(gh:*)` | 所有 GitHub CLI 命令 |
| `Bash(gh pr:*)` | GitHub PR 操作 |
| `Bash(gh pr create:*)` | 创建 PR |
| `Bash(gh pr edit:*)` | 编辑 PR |
| `Bash(gh pr merge:*)` | 合并 PR |
| `Bash(gh pr view:*)` | 查看 PR |
| `Bash(npm:*)` | 所有 npm 命令 |
| `Bash(npm install)` | npm install（精确匹配） |
| `Bash(npm run *)` | npm run 脚本 |
| `Bash(npm run build)` | npm run build（精确） |
| `Bash(npm run lint)` | npm run lint（精确） |
| `Bash(npm run test)` | npm run test（精确） |
| `Bash(pnpm:*)` | 所有 pnpm 命令 |
| `Bash(yarn:*)` | 所有 yarn 命令 |
| `Bash(bun:*)` | 所有 bun 命令 |
| `Bash(curl:*)` | curl 命令（通常放 deny） |
| `Bash(http:*)` | HTTP 相关命令 |
| `Bash(asciinema:*)` | 终端录制 |
| `Bash(rm -rf:*)` | 危险删除（通常放 deny） |
| `Bash(sleep ...)` | sleep 命令 |

**文件操作规则：**

| 模式 | 说明 |
|------|------|
| `Read` | 允许所有文件读取 |
| `Read(~/**)` | 允许读取用户目录 |
| `Read(~/.zshrc)` | 只允许读取特定文件 |
| `Write(/etc/*)` | 允许写入 /etc（危险） |
| `Edit(.claude)` | 允许编辑 .claude 目录 |
| `Edit(~/.claude/settings.json)` | 编辑特定设置文件 |
| `Edit(docs/**)` | 编辑 docs 目录下所有文件 |

**网络规则：**

| 模式 | 说明 |
|------|------|
| `WebFetch(domain:example.com)` | 限制到特定域名 |
| `WebFetch(domain:github.com)` | 允许 GitHub |
| `WebFetch(domain:*.google.com)` | 通配符域名 |
| `WebSearch(claude ai)` | 搜索特定主题 |

**MCP 工具规则：** `mcp__serverName__toolName` 格式（双下划线）

**三层评估顺序**（官方文档）：deny → ask → allow → 默认需确认

### --permission-mode 选项（`claude --help` 确认）

| 模式 | 说明 |
|------|------|
| `default` | 默认模式——未匹配规则的操作需确认 |
| `acceptEdits` | 自动接受文件编辑，其他操作仍需确认 |
| `plan` | 规划模式——仅允许只读操作 |
| `auto` | 自动模式——减少确认频率 |
| `dontAsk` | 不询问——自动执行所有操作 |
| `bypassPermissions` | 绕过所有权限检查（需 `--dangerously-skip-permissions`） |

> 证据：`claude --help` 输出 `--permission-mode <mode> (choices: "acceptEdits", "bypassPermissions", "default", "dontAsk", "plan", "auto")`

### 权限配置示例
```json
{
  "permissions": {
    "allow": [
      "Read",
      "Glob",
      "Grep",
      "Bash(npm run *)",
      "Bash(git:*)",
      "Bash(gh pr view:*)"
    ],
    "deny": [
      "Bash(curl *)",
      "Bash(rm -rf:*)",
      "Write(/etc/*)"
    ]
  }
}
```

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
