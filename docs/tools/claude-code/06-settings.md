# 6. 设置与安全

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

> 来源：[官方 Hooks 文档](https://code.claude.com/docs/en/hooks)，部分事件同时在 v2.1.81 二进制中确认。

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
