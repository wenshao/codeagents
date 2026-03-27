# 13. Hooks 配置指南

> 本文介绍终端 AI 编程代理的 Hook（钩子）系统——什么是 Hook、各工具支持的事件、配置格式、以及实用示例。

## 什么是 Hooks

Hooks 是在代理执行特定操作前后自动触发的脚本或规则。它们允许你：

- **拦截危险操作**：在工具执行前检查命令安全性
- **自动化后处理**：在文件编辑后自动运行 lint/format
- **审计记录**：记录代理的所有操作到日志
- **自定义通知**：在任务完成时发送通知
- **LLM 驱动决策**：（Claude Code 独有）让 LLM 分析操作意图后决定是否允许

各工具的 Hook 支持：

| Agent | Hook 事件数 | 配置格式 | Hook 类型 | 特色 |
|------|------------|----------|-----------|------|
| **Claude Code** | 22 种 | `settings.json` | command / http / prompt | 唯一支持 Prompt Hook（LLM 驱动决策） |
| **Gemini CLI** | 11 种 | `settings.json` | command / runtime | BeforeModel / AfterModel 可修改 LLM 请求 |
| **Kimi CLI** | 审批系统 | `config.toml` | 审批规则 | 统一审批运行时，非传统 Hook |
| **Codex CLI** | — | — | — | 通过沙箱和审批模式控制，无 Hook 系统 |
| **Copilot CLI** | — | — | — | 通过 GitHub Actions 和策略控制 |

## Claude Code Hooks（24 种事件）

### 配置位置

Hooks 在 `settings.json` 的 `hooks` 字段中配置，遵循 5 层设置优先级：

| 优先级 | 路径 | 说明 |
|--------|------|------|
| 1（最高） | `managed-settings.json` | 企业管控，MDM 下发 |
| 2 | `.claude/settings.local.json` | 本地覆盖（不提交 Git） |
| 3 | `.claude/settings.json` | 项目共享（提交 Git） |
| 4（最低） | `~/.claude/settings.json` | 用户全局偏好 |

### 配置格式

```json
{
  "hooks": {
    "<事件名>": [
      {
        "matcher": "<工具名>",
        "hooks": [
          {
            "type": "command",
            "command": "<Shell 命令>"
          }
        ]
      }
    ]
  }
}
```

### 三种 Hook 类型

| 类型 | 说明 | 示例 |
|------|------|------|
| **command** | 执行外部 Shell 命令 | `"command": "python3 check.py \"$TOOL_INPUT\""` |
| **http** | 发送 HTTP 请求 | `"type": "http", "url": "https://..."` |
| **prompt** | LLM 驱动决策（Claude Code 独有） | 让 LLM 分析工具调用意图后决定是否允许 |

### 24 种事件完整列表

| 事件 | 触发时机 | 典型用途 |
|------|----------|----------|
| `PreToolUse` | 工具执行前 | 拦截危险命令、修改参数 |
| `PostToolUse` | 工具执行成功后 | 自动 lint、审计日志 |
| `PostToolUseFailure` | 工具执行失败后 | 错误报告、自动重试逻辑 |
| `UserPromptSubmit` | 用户提交提示时 | 输入过滤、自动补充上下文 |
| `SessionStart` | 会话开始时 | 环境检查、加载项目配置 |
| `SessionEnd` | 会话结束时 | 清理临时文件、保存统计 |
| `PermissionRequest` | 请求权限时 | 自定义权限逻辑 |
| `Notification` | 通知事件 | 桌面通知、Slack/飞书推送 |
| `SubagentStart` | 子代理启动时 | 子代理资源管理 |
| `SubagentStop` | 子代理停止时 | 子代理结果收集 |
| `Stop` | 代理停止时 | 最终清理 |
| `StopFailure` | 代理停止失败时 | 异常处理 |
| `PreCompact` | 上下文压缩前 | 保存重要上下文 |
| `PostCompact` | 上下文压缩后 | 验证压缩结果 |
| `TaskCompleted` | 后台任务完成时 | 任务结果通知 |
| `TeammateIdle` | Teammate 空闲时 | 多代理协调 |
| `InstructionsLoaded` | 指令文件加载时 | 动态修改指令 |
| `ConfigChange` | 配置变更时 | 重新加载配置 |
| `WorktreeCreate` | 创建 Git worktree 时 | 初始化 worktree 环境 |
| `WorktreeRemove` | 移除 Git worktree 时 | 清理 worktree 资源 |
| `Elicitation` | 向用户请求信息时 | 自定义信息请求逻辑 |
| `ElicitationResult` | 用户回复请求时 | 处理用户回复 |

### Hook 决策返回值

Hook 脚本通过 stdout 输出 JSON 控制行为：

| 返回值 | 效果 |
|--------|------|
| `{"decision": "approve"}` | 允许执行（跳过用户确认） |
| `{"decision": "deny", "message": "原因"}` | 拒绝执行 |
| `{"decision": "block", "message": "原因"}` | 阻止并显示消息 |
| 无输出或空输出 | 继续正常流程（不干预） |

## Gemini CLI Hooks（11 种事件）

### 配置格式

```jsonc
// ~/.gemini/settings.json 或 .gemini/settings.json
{
  "hooks": {
    "<事件名>": [
      {
        "matcher": "<工具名>",
        "hooks": [
          { "type": "command", "command": "<Shell 命令>", "timeout": 5000 }
        ]
      }
    ]
  }
}
```

### 11 种事件

| 事件 | 触发时机 | 特殊能力 |
|------|----------|---------|
| `BeforeTool` | 工具执行前 | 修改输入参数、阻止/拒绝/批准执行 |
| `AfterTool` | 工具执行后 | 后处理工具输出 |
| `BeforeAgent` | 代理启动前 | 预处理、环境检查 |
| `AfterAgent` | 代理完成后 | 后处理、统计收集 |
| `BeforeModel` | LLM 调用前 | **修改 LLM 请求**（独有） |
| `AfterModel` | LLM 响应后 | **后处理 LLM 响应**（独有） |
| `BeforeToolSelection` | 工具选择前 | 覆盖工具选择逻辑 |
| `Notification` | 通知事件 | 自定义通知 |
| `SessionStart` | 会话开始 | 初始化 |
| `SessionEnd` | 会话结束 | 清理 |
| `PreCompress` | 上下文压缩前 | 预处理 |

### Hook 决策

Gemini CLI 支持 5 种决策：`ask`（询问用户）、`block`（阻止）、`deny`（拒绝）、`approve`（批准）、`allow`（允许）。

## Claude Code hookify 插件

Claude Code 的官方 `hookify` 插件能从对话分析中自动生成 Hook 规则——当代理检测到用户的挫败信号（如"不要这样做"、"停止"等），自动将行为模式提取为 Hook 规则。

### 使用方式

```bash
# 从对话分析中自动创建 Hook 规则
/hookify

# 指定要阻止的行为
/hookify 禁止使用 rm -rf 命令

# 管理已有规则
/hookify list       # 列出规则
/hookify configure  # 启用/禁用规则
```

### 工作原理

1. 分析最近 10-15 条用户消息，查找挫败信号
2. 识别有问题的行为模式
3. 生成 `.claude/hookify.{rule-name}.local.md` 规则文件
4. 规则文件使用 YAML Frontmatter 定义事件类型、正则匹配模式、显示消息
5. **无需重启**——规则立即对下一次工具调用生效

## 实用 Hook 示例

### 示例 1：拦截危险 Shell 命令

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "python3 ~/.claude/hooks/check_dangerous.py \"$TOOL_INPUT\""
          }
        ]
      }
    ]
  }
}
```

对应的 Python 检查脚本：

```python
#!/usr/bin/env python3
# ~/.claude/hooks/check_dangerous.py
import sys, json

dangerous_patterns = [
    "rm -rf /", "rm -rf ~", "rm -rf .",
    "dd if=", "mkfs.", "> /dev/sd",
    "chmod 777", "curl | bash", "wget | sh"
]

tool_input = sys.argv[1] if len(sys.argv) > 1 else ""
for pattern in dangerous_patterns:
    if pattern in tool_input:
        print(json.dumps({
            "decision": "block",
            "message": f"已拦截危险命令：包含 '{pattern}'"
        }))
        sys.exit(0)

# 无输出 = 继续正常流程
```

### 示例 2：编辑后自动 lint

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write",
        "hooks": [
          {
            "type": "command",
            "command": "npx eslint --fix \"$TOOL_OUTPUT_PATH\" 2>/dev/null || true"
          }
        ]
      },
      {
        "matcher": "Edit",
        "hooks": [
          {
            "type": "command",
            "command": "npx eslint --fix \"$TOOL_OUTPUT_PATH\" 2>/dev/null || true"
          }
        ]
      }
    ]
  }
}
```

### 示例 3：会话开始时检查环境

```json
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 ~/.claude/hooks/check_env.py"
          }
        ]
      }
    ]
  }
}
```

### 示例 4：任务完成桌面通知

```json
{
  "hooks": {
    "Notification": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "terminal-notifier -message \"$NOTIFICATION_MESSAGE\" -title 'Claude Code'"
          }
        ]
      }
    ]
  }
}
```

### 示例 5：审计日志

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "echo \"$(date '+%Y-%m-%d %H:%M:%S') PRE  $TOOL_NAME $TOOL_INPUT\" >> /tmp/claude-audit.log"
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "echo \"$(date '+%Y-%m-%d %H:%M:%S') POST $TOOL_NAME\" >> /tmp/claude-audit.log"
          }
        ]
      }
    ]
  }
}
```

## Prompt Hooks vs Script Hooks

Prompt Hook 是 Claude Code 的独有能力——不同于传统的脚本 Hook（执行一段固定逻辑），Prompt Hook 让 LLM 分析工具调用的上下文和意图后做出决策。

| 维度 | Script Hook（脚本） | Prompt Hook（LLM 驱动） |
|------|---------------------|------------------------|
| **决策方式** | 固定规则（正则匹配、关键词检查） | LLM 理解意图后判断 |
| **灵活性** | 低——只能匹配已知模式 | 高——能理解未见过的危险操作 |
| **延迟** | 低（毫秒级） | 高（需要 LLM 推理，秒级） |
| **成本** | 无额外成本 | 消耗额外 token |
| **适用场景** | 已知的危险命令拦截、格式检查 | 语义级安全检查、上下文相关的决策 |
| **工具支持** | Claude Code、Gemini CLI | 仅 Claude Code |

### Prompt Hook 使用场景

- **语义安全检查**：不仅检查命令本身，还理解命令在当前上下文中的含义
- **上下文相关决策**：同一个命令在不同场景下可能安全或危险
- **复杂规则**：难以用正则表达式描述的安全策略

### Script Hook 使用场景

- **已知模式拦截**：`rm -rf`、`curl | bash` 等明确的危险模式
- **格式强制**：自动 lint、格式化
- **审计记录**：所有操作都需要记录
- **通知推送**：任务完成通知

## Hook 设计最佳实践

### 1. Hook 脚本要快

Hook 在代理执行路径上同步运行。脚本执行时间过长会明显拖慢代理响应。建议 Hook 脚本在 1-2 秒内完成。

### 2. 失败安全

Hook 脚本异常退出时，代理的默认行为是继续正常流程。如果你的安全 Hook 崩溃了，操作仍会执行。确保 Hook 脚本健壮，关键安全检查要有兜底逻辑。

### 3. 使用 matcher 缩小范围

不要给所有工具都挂 Hook——只针对需要检查的工具（如 `Bash`、`Write`）设置 matcher，避免不必要的性能开销。

### 4. 日志方便调试

在 Hook 脚本中添加日志输出，便于排查 Hook 未按预期工作的问题。

### 5. 项目级 vs 全局

- **全局 Hook**（`~/.claude/settings.json`）：适用于所有项目的通用安全规则
- **项目级 Hook**（`.claude/settings.json`）：项目特定的自动化（如特定项目的 lint 配置）

## 相关资源

- Claude Code 设置与安全：`docs/tools/claude-code/06-settings.md`
- Gemini CLI 策略与 Hooks：`docs/tools/gemini-cli/05-policies.md`
- Claude Code 插件系统：`docs/tools/claude-code/05-skills.md`（hookify 插件）
- 配置示例对比：`docs/guides/config-examples.md`

## 相关资源

- [Hook/插件/扩展系统深度对比](../comparison/hook-plugin-extension-deep-dive.md) — 24 事件 + Prompt Hook vs 17 Hook 类型
- [沙箱与安全隔离深度对比](../comparison/sandbox-security-deep-dive.md) — 28 BLOCK 规则 + 三平台沙箱
- [Claude Code 设置详解](../tools/claude-code/06-settings.md) — 24 种 Hook 事件完整列表
- [Gemini CLI 策略引擎](../tools/gemini-cli/05-policies.md) — 11 Hook 事件 + TOML 策略
- [Skill 设计指南](./skill-design.md) — Skill + Hook 协作模式
- [安全加固指南](./security-hardening.md) — Hook 在安全场景的应用
