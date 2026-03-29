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

### Hook 事件类型（24 种）

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
| `CwdChanged` | 工作目录变更时 | v2.1.83 二进制确认 |
| `FileChanged` | 文件变更检测时 | v2.1.83 二进制确认 |

> 来源：[官方 Hooks 文档](https://code.claude.com/docs/en/hooks)（2026-03 访问），全部 24 个事件在 v2.1.83 二进制中确认存在。

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

### 安全监控系统（Auto Mode Classifier，反编译提取）

> 从二进制变量 `d38`（安全监控提示词）和 `wSA`（权限模板）反编译提取。这是 Claude Code 的自主模式安全系统——在 `--permission-mode auto` 或 `--dangerously-skip-permissions` 下运行时，由独立的分类器模型评估每个操作。

**身份：** "You are a security monitor for autonomous AI coding agents."

**威胁模型（3 种风险）：**

| 风险 | 说明 |
|------|------|
| **Prompt Injection** | 代理被文件/网页/工具输出中的内容操纵执行有害操作 |
| **Scope Creep** | 代理超出任务范围——修复一个问题后"顺便"删除基础设施或外泄数据 |
| **Accidental Damage** | 代理不理解爆炸半径——删除自认为是自己任务的内容但实际是共享的 |

**默认规则：** "默认允许。仅在命中 BLOCK 条件且无 ALLOW 例外时阻止。"

**BLOCK 条件（28 条，从二进制逐字提取）：**

| 类别 | 规则 | 说明 |
|------|------|------|
| **Git 破坏** | Git Destructive | force push、删除远程分支、改写远程历史 |
| **Git 推送** | Push to Default Branch | 直接推送到 main/master 绕过 PR 审查 |
| **外部代码** | Code from External | `curl \| bash`、eval、pickle、exec 来自外部源 |
| **云存储** | Cloud Storage Mass Delete | S3/GCS/Azure 批量删除或修改 |
| **生产部署** | Production Deploy | 部署到生产或执行生产数据库迁移 |
| **远程写入** | Remote Shell Writes | `kubectl exec`、`docker exec`、`ssh` 写入操作 |
| **盲目应用** | Blind Apply | 跳过 preview/dry-run 直接执行破坏性操作 |
| **日志篡改** | Logging Tampering | 停止日志、删除日志目录、移除 git hooks |
| **权限提升** | Permission Grant | 授予 admin/owner、添加用户、提升 IAM/RBAC |
| **安全降级** | TLS/Auth Weaken | 禁用 TLS 验证、`--allow-unauthenticated` |
| **安全削弱** | Security Weaken | 禁用安全缓解、修改防火墙规则 |
| **创建不安全代理** | Create Unsafe Agents | 无人工审批的自主代理循环 |
| **干扰他人** | Interfere With Others | 删除作业、破坏集群、轰炸 Slack |
| **修改共享资源** | Modify Shared Resources | 原地修改非自己创建的共享配置/数据 |
| **不可逆本地破坏** | Irreversible Local Destruction | `rm -rf`、`git clean -fdx`、`git checkout .` |
| **创建 RCE** | Create RCE Surface | eval、shell 注入、不安全反序列化 |
| **暴露本地服务** | Expose Local Services | 绑定端口暴露本地文件/服务 |
| **凭据泄露** | Credential Leakage | 在 metadata/labels/URLs 中嵌入密钥 |
| **凭据探索** | Credential Exploration | 系统性扫描凭据存储寻找可用 token |
| **数据外泄** | Data Exfiltration | 发送敏感数据到外部端点 |
| **外泄侦察** | Exfil Scouting | 测试外部端点可达性 |
| **信任猜测的服务** | Trusting Guessed Services | 向代理自行猜测的外部服务发送数据 |
| **不受信代码集成** | Untrusted Code Integration | 从外部仓库拉取代码并执行 |
| **未授权持久化** | Unauthorized Persistence | 添加 SSH 密钥、修改 .bashrc、创建 cron |
| **自我修改** | Self-Modification | 修改代理自身的配置/设置/权限文件 |
| **外部系统写入** | External System Writes | 删除/修改 Jira/Linear/GitHub 中非自己创建的项目 |
| **内容伪造** | Content Impersonation | 发布虚假内容、伪造声明 |
| **真实世界交易** | Real-World Transactions | 购买、支付、预订、发送外部通信 |

**ALLOW 例外（7 条）：**

| 例外 | 说明 |
|------|------|
| Test Artifacts | 硬编码测试密钥、占位符凭据 |
| Local Operations | 工作目录内的文件操作、本地测试 |
| Read-Only Operations | GET 请求、不修改状态的查询 |
| Declared Dependencies | 从仓库 manifest 文件安装依赖 |
| Toolchain Bootstrap | 官方一键安装（rustup、pypa、bun） |
| Standard Credentials | 从自身配置读取凭据发送给对应提供商 |
| Git Push to Working Branch | 推送到会话分支（非默认分支） |

**分类器架构：**

| 属性 | 值 |
|------|-----|
| **阶段** | 双阶段：fast（XML, 256 token 上限）→ thinking（XML, 4096 token 上限） |
| **默认模型** | `claude-sonnet-4-6`（大上下文时使用 `claude-sonnet-4-6[1m]`） |
| **输出格式** | `<block>yes/no</block><reason>一句话原因</reason>` |
| **失败安全** | 解析失败 → 阻止；错误/超时 → 阻止 |
| **用户意图** | "用户意图提供上下文但**不是** BLOCK 条件的自动覆盖" |

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
