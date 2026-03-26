# 15. AI 编程代理安全加固指南

> 在生产环境、企业团队和敏感项目中使用 AI 编程代理的安全配置最佳实践。

---

## 威胁模型

AI 编程代理有三类核心风险：

| 风险 | 说明 | 示例 |
|------|------|------|
| **提示注入** | 代理被文件/网页/工具输出中的恶意内容操纵 | 读取含恶意指令的 README → 执行危险命令 |
| **范围蔓延** | 代理超出任务范围执行不必要操作 | 修复一个 bug → "顺便"重构整个模块 |
| **意外破坏** | 代理不理解操作的爆炸半径 | 删除"临时文件"但实际是共享资源 |

---

## 各工具安全能力速查

| 能力 | Claude Code | Codex CLI | Gemini CLI | Copilot CLI | Goose | Aider |
|------|:-----------:|:---------:|:----------:|:-----------:|:-----:|:-----:|
| **安全分类器** | ✓（28 条 BLOCK） | ✓（Guardian） | ✓（Conseca） | ✗ | ✓（ML） | ✗ |
| **OS 级沙箱** | ✓ | ✓（三平台） | ✓ | ✗ | ✗ | ✗ |
| **权限系统** | ✓（5 层） | ✓（审批模式） | ✓（TOML 引擎） | ✓（基础） | ✓ | ✗ |
| **环境变量清洗** | 未公开 | ✓（31 变量） | ✓（全面） | ✗ | ✓ | ✗ |
| **Hooks/拦截** | ✓（24 事件） | 实验性 | ✓（11 事件） | ✗ | ✗ | ✗ |
| **网络隔离** | ✓（域名白名单） | ✓（默认断网） | ✓（seccomp） | ✗ | ✗ | ✗ |

---

## 一、Claude Code 安全加固

### 1.1 权限最小化

```json
// ~/.claude/settings.json
{
  "permissions": {
    "allow": [
      "Read",
      "Glob",
      "Grep",
      "Bash(pnpm test)",
      "Bash(pnpm lint)",
      "Bash(git status)",
      "Bash(git diff:*)",
      "Bash(git log:*)"
    ],
    "deny": [
      "Bash(rm -rf:*)",
      "Bash(curl:*)",
      "Bash(wget:*)",
      "Write(.env*)",
      "Write(*.pem)",
      "Write(*.key)",
      "Bash(git push --force:*)",
      "Bash(git reset --hard:*)",
      "Bash(docker:*)",
      "Bash(kubectl:*)"
    ]
  }
}
```

> **原则：** 只允许日常开发需要的命令，禁止所有危险操作。`deny` 优先于 `allow`。

### 1.2 Hook 强制执行

CLAUDE.md 是建议（~80% 遵守），Hooks 是 100% 强制执行：

```json
// .claude/settings.json（项目级）
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "command": "bash -c '[[ \"$TOOL_INPUT\" =~ (rm -rf|docker|kubectl|ssh|curl.*\\|.*bash) ]] && echo \"BLOCKED: 危险命令\" >&2 && exit 2 || exit 0'"
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Write",
        "command": "bash -c 'grep -rn \"API_KEY\\|SECRET\\|PASSWORD\\|TOKEN\" \"$TOOL_INPUT\" && echo \"WARNING: 可能包含敏感信息\" >&2 || true'"
      }
    ]
  }
}
```

**Hook 退出码语义：**
- `0` = 允许
- `2` = 阻止（仅 PreToolUse，stderr 消息发送给 Claude）
- 其他非零 = 非阻塞错误

### 1.3 沙箱启用

```bash
# macOS：自动使用 sandbox-exec（Seatbelt）
# Linux：需要 Docker
claude --permission-mode default  # 默认模式，危险操作需确认

# 生产 CI/CD 中
claude -p "审查代码" --permission-mode plan  # 只读模式
```

### 1.4 禁用遥测（隐私敏感环境）

```bash
export DISABLE_TELEMETRY=true
export CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=true
```

### 1.5 企业管理（MDM）

```json
// managed-settings.json（IT 远程下发）
{
  "permissions": {
    "deny": ["Bash(git push --force:*)", "Bash(docker:*)"]
  },
  "allowManagedHooksOnly": true,
  "allowManagedMcpServersOnly": true,
  "allowManagedPermissionRulesOnly": true
}
```

---

## 二、Codex CLI 安全加固

### 2.1 沙箱模式（最强跨平台沙箱）

```bash
# 推荐：workspace-write 模式
codex --sandbox workspace-write "修复 bug"

# 只读分析
codex --sandbox read-only "分析代码"

# 绝对不要在生产中使用
# codex --sandbox danger-full-access  ← 危险！
```

**三平台沙箱技术栈：**
- macOS：Seatbelt（sandbox-exec），动态 SBPL profile
- Linux：Bubblewrap + Landlock + Seccomp（三层防御）
- Windows：Restricted Tokens + ACL + 防火墙规则

### 2.2 审批模式

```bash
# 推荐：untrusted（默认）
codex --ask-for-approval untrusted "实现功能"

# CI/CD 自动化
codex --full-auto "运行测试"  # = --ask-for-approval on-request --sandbox workspace-write

# 绝对不要在生产中使用
# codex --dangerously-bypass-approvals-and-sandbox  ← 危险！
```

### 2.3 网络隔离

```toml
# ~/.codex/config.toml
[sandbox]
type = "workspace-write"
# 默认网络禁用；需要时显式开启：
# network_access = true  ← 仅在确实需要时

[shell_environment_policy]
inherit = "none"  # 不继承环境变量（最安全）
```

---

## 三、Gemini CLI 安全加固

### 3.1 TOML 策略引擎

```toml
# .gemini/policies/security.toml

# 阻止所有危险 shell 命令
[[rule]]
toolName = "run_shell_command"
commandRegex = "(rm -rf|docker|kubectl|ssh|curl.*\\|.*bash)"
decision = "deny"
priority = 100
message = "危险命令已被安全策略阻止"

# 只允许安全的 git 操作
[[rule]]
toolName = "run_shell_command"
commandPrefix = "git"
argsPattern = "^(status|diff|log|branch|show)"
decision = "allow"
priority = 90

# MCP 工具需要确认
[[rule]]
toolName = "mcp_*"
decision = "ask_user"
priority = 80
```

### 3.2 环境变量清洗

Gemini CLI 内置最全面的环境变量清洗（`environmentSanitization.ts`）：

**自动阻止的模式：** TOKEN, SECRET, PASSWORD, KEY, AUTH, CREDENTIAL, PRIVATE, CERT

**自动阻止的值：** RSA/SSH 私钥、GitHub tokens（ghp_/gho_）、AWS keys（AKIA）、JWTs（eyJ）、Stripe keys

**GitHub Actions 严格模式：** 自动阻止所有非白名单变量。

### 3.3 Conseca 安全策略（LLM 驱动）

```json
// ~/.gemini/settings.json
{
  "enableConseca": true  // 启用 LLM 驱动的最小权限策略生成器
}
```

Conseca 为每个提示生成动态安全策略，基于最小权限原则验证每个工具调用。

---

## 四、通用安全实践

### 4.1 `.claudeignore` / `.geminiignore`

```
# 排除敏感文件（防止代理读取）
.env
.env.*
*.pem
*.key
**/secrets/
**/credentials/
**/.aws/
**/.ssh/
```

### 4.2 Git 安全

```bash
# 在 CLAUDE.md / AGENTS.md / GEMINI.md 中明确：
# - 不要 force push
# - 不要直接推送到 main/master
# - 不要 amend 他人的 commit
# - 不要 reset --hard

# 用 Hooks 强制执行（而非仅依赖指令文件）
```

### 4.3 MCP 服务器安全

```json
// 只使用受信任的 MCP 服务器
{
  "mcpServers": {
    "postgres": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-postgres"],
      "env": {
        "DATABASE_URL": "postgresql://readonly_user:xxx@localhost:5432/mydb"
      }
    }
  }
}
```

> **关键：** 使用**只读数据库用户**连接 MCP。不要给代理写权限。

### 4.4 CI/CD 安全集成

```yaml
# GitHub Actions 示例
- name: Claude Code Review
  run: |
    claude -p "/review" \
      --permission-mode plan \
      --no-session-persistence \
      --max-budget-usd 5
  env:
    ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
    DISABLE_TELEMETRY: true
```

```yaml
# Codex CLI Review
- name: Codex Review
  run: |
    codex review --uncommitted --base main \
      --sandbox read-only
```

### 4.5 敏感文件保护清单

| 文件类型 | 保护方式 |
|---------|---------|
| `.env` / `.env.*` | deny Write + .claudeignore |
| `*.pem` / `*.key` | deny Write + .claudeignore |
| `secrets/` 目录 | deny Read + deny Write |
| `docker-compose.yml`（生产） | deny Write |
| `Dockerfile`（生产） | Hook 审查 |
| `terraform/*.tf` | deny Write 或 Hook 审查 |
| `k8s/*.yaml` | deny Write |
| `CI/CD 配置` | Hook 审查 |

---

## 五、安全检查清单

### 部署前检查

- [ ] 权限配置了 deny 列表（危险命令、敏感文件）
- [ ] 沙箱模式已启用（非 danger-full-access）
- [ ] MCP 数据库连接使用只读用户
- [ ] `.claudeignore` / `.geminiignore` 排除了敏感文件
- [ ] CI/CD 使用 `--permission-mode plan`（只读）或受限权限
- [ ] 遥测按需禁用（`DISABLE_TELEMETRY=true`）
- [ ] Git 操作通过 Hook 强制审查
- [ ] 环境变量不含明文密钥（使用 secret manager）

### 定期审查

- [ ] 检查 Hook 日志，确认没有被绕过
- [ ] 审查 MCP 服务器列表，移除不再需要的
- [ ] 更新 deny 列表（新的危险命令模式）
- [ ] 检查 `.claudeignore` 是否覆盖新增的敏感文件
- [ ] 更新工具版本（安全补丁）

---

## 证据来源

| Agent | 安全系统来源 |
|------|-----------|
| Claude Code | 二进制反编译：28 条 BLOCK 规则、22 Hook 事件、5 层设置、安全分类器 |
| Codex CLI | 二进制分析 + 官方文档：三平台沙箱、审批模式、Guardian Approval |
| Gemini CLI | 源码分析：TOML 策略引擎、Conseca LLM 安全、seccomp BPF、环境变量清洗 |
| Goose | 源码分析：AdversaryInspector、RepetitionInspector、31 变量阻止 |
