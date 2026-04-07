# 12. Hook 系统——开发者参考

> Hook 系统是 Claude Code 中演进最快的子系统——从 2025-06 首次引入的 5 个事件，到 2026-03 的 27 个事件 + 6 种处理器类型，经历了 9 个月的持续扩展。它解决了一个 Code Agent 的根本问题：**如何让用户对 Agent 行为拥有确定性控制，而不是仅靠 LLM 的"好意"**。
>
> **Qwen Code 对标**：Qwen Code 有 12 种事件（与 Claude Code 早期版本接近），仅 command 处理器。Claude Code 的 prompt/agent 类型 Hook（LLM 推理决策）和 hookify 自动规则生成是主要差距。

## 一、为什么需要 Hook 系统

### 1.1 问题定义：LLM 指令的不确定性

在 CLAUDE.md / QWEN.md 中写"不要修改 .env 文件"，模型**大部分时候**会遵守。但"大部分时候"在生产环境中是不够的。Hook 解决的核心问题是：

| 场景 | 仅靠 LLM 指令 | 有 Hook |
|------|-------------|---------|
| "不要删除 production.config" | 模型可能在复杂推理链中遗忘 | `PreToolUse` Hook 在 Write/Edit 前检查路径，**确定性拦截** |
| "每次编辑后运行 prettier" | 模型可能忘记或判断"不需要" | `PostToolUse` Hook 在 Write/Edit 后**始终执行** |
| "提交前必须通过测试" | 模型可能跳过 | `Stop` Hook 在结束前**强制运行** `npm test` |
| "记录所有 API 调用到审计日志" | 模型完全不知道这个需求 | `PostToolUse` Hook 静默执行，**不占 token** |

Claude Code 官方文档的原话：

> *"Hooks provide **deterministic control** over Claude Code's behavior, ensuring certain actions **always happen** rather than relying on the LLM to choose to run them."*

### 1.2 设计原则

| 原则 | 含义 | 实现 |
|------|------|------|
| **确定性 > 概率性** | Hook 保证在特定生命周期点执行，不依赖 LLM 判断 | 事件驱动 + 匹配器触发 |
| **纵深防御** | PreToolUse Hook 在权限检查之前触发，deny 决策不可被权限模式覆盖 | Hook 优先于 permission mode |
| **可组合** | 多个 Hook 匹配同一事件时，全部并行执行，最严格决策生效 | deny > ask > allow |
| **渐进复杂度** | 简单场景只需 exit code（0=允许，2=阻止），高级场景用结构化 JSON | 阶梯式 API |
| **不触碰上下文** | Hook 在 LLM 对话之外执行，不消耗 token | stdin/stdout 管道 |

### 1.3 演进时间线

| 版本 | 时间 | 新增事件 | 里程碑 |
|------|------|---------|--------|
| v1.0.38 | 2025-06 | PreToolUse, PostToolUse, Stop, Notification, SessionStart | 首次引入，[Issue #712](https://github.com/anthropics/claude-code/issues/712) |
| v2.1.0 | 2026 初 | — | Hooks 支持在 agents/skills frontmatter 中定义 |
| v2.1.49 | 2026-02 | ConfigChange, WorktreeCreate, WorktreeRemove | 配置和工作树生命周期 |
| v2.1.76 | 2026-03-14 | Elicitation, ElicitationResult, PostCompact | MCP 交互 + 压缩后 |
| v2.1.78 | 2026-03-17 | StopFailure | Stop Hook 失败恢复 |
| v2.1.83 | 2026-03-25 | CwdChanged, FileChanged, PermissionDenied | 文件监控 + 权限拒绝 |
| v2.1.84 | 2026-03-26 | TaskCreated | 任务系统集成 |
| v2.1.85 | 2026-03-26 | — | `if` 条件过滤字段 |
| 当前 | 2026-04 | 共 27 种 | 6 种处理器类型 |

> 注：首次引入前，社区曾开发 [cc-hook](https://github.com/nahco314/cc-hook) 作为非官方替代方案。原始需求受 React 组件生命周期 Hook 和 Google ADK 回调启发。

## 二、27 种事件详解

### 工具执行（5 种）——**最常用**

| 事件 | 触发时机 | 可干预行为 | 典型用例 |
|------|---------|-----------|---------|
| `PreToolUse` | 工具执行前 | 阻止、修改输入、更改权限 | 拦截危险命令、保护文件 |
| `PostToolUse` | 工具执行成功后 | 替换输出、注入上下文 | 自动格式化、审计日志 |
| `PostToolUseFailure` | 工具执行失败后 | 注入错误上下文 | 错误分析、自动重试提示 |
| `PermissionRequest` | 权限系统请求审批 | allow/deny/ask | 自动审批安全操作 |
| `PermissionDenied` | 权限被拒绝后 | 请求重试 | 提示用户调整权限 |

### 会话 + Agent 生命周期（7 种）

| 事件 | 触发时机 | 典型用例 |
|------|---------|---------|
| `SessionStart` | 会话开始 | 注入项目上下文、设置文件监控路径 |
| `SessionEnd` | 会话结束 | 清理临时文件、自动提交 |
| `Setup` | 初始化 | 环境配置 |
| `Stop` | Agent 执行停止 | 运行测试、生成摘要 |
| `StopFailure` | Stop Hook 失败 | 错误恢复 |
| `SubagentStart` | Subagent 启动前 | 权限检查、上下文注入 |
| `SubagentStop` | Subagent 停止后 | 结果聚合 |

### 上下文 + 任务 + 文件 + Worktree + MCP + 用户（15 种）

| 类别 | 事件 | 触发时机 |
|------|------|---------|
| 压缩 | `PreCompact` / `PostCompact` | 上下文压缩前/后 |
| 任务 | `TaskCreated` / `TaskCompleted` / `TeammateIdle` | 任务创建/完成/队友空闲 |
| 文件 | `FileChanged` / `CwdChanged` / `ConfigChange` / `InstructionsLoaded` | 文件/目录/配置/指令变更 |
| Worktree | `WorktreeCreate` / `WorktreeRemove` | Git worktree 创建/删除 |
| 用户 | `UserPromptSubmit` / `Notification` | 用户输入/通知 |
| MCP | `Elicitation` / `ElicitationResult` | MCP 引导请求/结果 |

## 三、6 种处理器类型

### 3.1 Command Hook（shell 命令）——基础型

通过 stdin 接收事件 JSON，exit code 控制行为。最简单也最常用。

```json
{
  "type": "command",
  "command": "bash /path/to/check.sh",
  "timeout": 30,
  "if": "Bash(git *)"
}
```

**Exit Code**：`0`=允许，`2`=阻止，其他=非阻止性错误。

### 3.2 Prompt Hook（LLM 推理决策）——Claude Code 独有创新

用**另一个 LLM**（默认 Haiku，低成本快速）来判断操作是否安全。解决静态规则无法处理的**语义级判断**问题。

```json
{
  "type": "prompt",
  "prompt": "A shell command will execute: $ARGUMENTS. Is it safe? Consider: destructive operations, credential exposure, network access. Reply {\"ok\": true} or {\"ok\": false, \"reason\": \"...\"}",
  "model": "claude-haiku-4-5"
}
```

**为什么需要这个？**

静态规则（command hook）能拦截 `rm -rf`，但无法区分：
- `rm -rf node_modules`（安全——清理依赖）
- `rm -rf /`（灾难——删除系统）
- `rm -rf build/`（可能安全——清理构建产物，取决于上下文）

Prompt Hook 让 LLM 基于上下文做语义级判断——这是命令行规则引擎做不到的。

### 3.3 Agent Hook（完整 Agent 验证）

创建临时 Agent，可读取 transcript、使用工具进行**多轮深度验证**。最多 50 轮交互。适合复杂场景（如验证架构变更是否破坏模块边界）。

### 3.4 HTTP Hook（外部 Webhook）

POST JSON 到外部 HTTP 端点。支持 SSRF 防护（私有 IP 阻断）、环境变量隔离（显式 `allowedEnvVars` 白名单）、Header 注入防护（CRLF/NUL 过滤）。

### 3.5 Callback / Function Hook（内部运行时）

TypeScript 函数直接注册，无子进程开销。Callback 用于系统级 Hook（文件追踪、归因），Function 用于会话级临时验证（如结构化输出校验）。不可持久化到 settings.json。

## 四、Hook 执行架构

### 4.1 执行流程

```
事件触发
  │
  ├─ 1. 匹配：getMatchingHooks()
  │     ├─ 简单字符串精确匹配
  │     ├─ 管道分隔多值（"Write|Edit"）
  │     ├─ 正则匹配
  │     └─ * = 全部匹配
  │
  ├─ 2. if 条件过滤（权限规则语法）
  │     └─ "Bash(git *)" — 仅 git 命令触发
  │     └─ 在 spawn 子进程前执行，节省开销
  │
  ├─ 3. 跨来源去重（user/project/local/plugin）
  │
  ├─ 4. 并行执行所有匹配 Hook
  │     └─ 每个 Hook 独立超时
  │
  └─ 5. 结果聚合
        └─ 权限优先级：deny > ask > allow > passthrough
```

### 4.2 关键设计：Hook 优先于权限

```
PreToolUse Hook
  │ deny
  ▼
[阻止] ← 即使 permission mode = bypassPermissions 也无法覆盖

PreToolUse Hook
  │ allow
  ▼
Permission Mode 检查 ← Hook 可以放行，但权限系统仍然生效
```

**含义**：Hook 可以加强限制（deny），但不能绕过权限系统。这是"纵深防御"的核心——Hook 是额外的安全层，不是替代品。

### 4.3 输入/输出 Schema

**通用输入**（所有 Hook 接收）：
```json
{
  "session_id": "...",
  "transcript_path": "/path/to/transcript.jsonl",
  "cwd": "/project",
  "permission_mode": "default",
  "hook_event_name": "PreToolUse",
  "tool_name": "Bash",
  "tool_input": {"command": "rm -rf node_modules"}
}
```

**输出能力**：

| 输出字段 | 效果 | 适用事件 |
|---------|------|---------|
| `continue: false` | 阻止后续执行 | 全部 |
| `decision: 'block'` | 阻止工具执行 | PreToolUse |
| `permissionDecision: 'allow'/'deny'/'ask'` | 更改权限行为 | PreToolUse, PermissionRequest |
| `updatedInput: {...}` | 修改工具输入 | PreToolUse |
| `updatedMCPToolOutput` | 替换工具输出 | PostToolUse |
| `additionalContext: "..."` | 注入系统消息给模型 | 全部 |
| `initialUserMessage: "..."` | 设置首条用户消息 | SessionStart |
| `watchPaths: [...]` | 监控文件变更 | SessionStart, CwdChanged |
| `retry: true` | 权限拒绝后重试 | PermissionDenied |

## 五、竞品 Hook 系统对比

### 5.1 设计哲学差异

| Agent | Hook 设计哲学 | 核心特点 |
|-------|-------------|---------|
| **Claude Code** | 最大覆盖 + LLM 决策 | 27 事件、6 种处理器、prompt/agent 类型独有 |
| **Gemini CLI** | 类型安全 + 模型级拦截 | 11 事件、BeforeModel/AfterModel（模型层拦截）、runtime Handler |
| **Qwen Code** | MessageBus 集成 | 12 事件、权限决策框架、与 CoreToolScheduler 深度集成 |
| **Cursor** | 最小必要 | ~5 事件（beforeShellExecution/afterFileEdit/stop 等） |
| **Copilot CLI** | 插件生态 | 6 事件、插件可打包 hooks + agents + skills + MCP |
| **Aider** | 无 Hook | 依赖 Git 集成和配置 flag，社区 fork AiderDesk 有 30+ 事件 |

### 5.2 能力矩阵

| 能力 | Claude Code | Gemini CLI | Qwen Code | Copilot CLI | Cursor |
|------|-------------|-----------|-----------|------------|--------|
| 事件数 | **27** | 11 | 12 | 6 | ~5 |
| 处理器类型 | **6**（含 LLM） | 2 | 1 | 1 | 1 |
| LLM 驱动决策 | ✓ prompt + agent | — | — | — | — |
| 工具输入修改 | ✓ | ✓ | ✓ | — | ✓ |
| 工具输出替换 | ✓ | ✓ (tail call) | ✓ | — | — |
| 模型层拦截 | — | ✓ BeforeModel | — | — | — |
| 工具选择修改 | — | ✓ BeforeToolSelection | — | — | — |
| HTTP Webhook | ✓ | — | — | — | — |
| 文件监控 | ✓ FileChanged | — | — | — | — |
| 条件过滤（if） | ✓ | matcher | matcher | — | matcher |
| 异步后台 | ✓ async/asyncRewake | — | — | — | — |
| 合成 LLM 响应 | — | ✓ getSyntheticResponse | — | — | — |

### 5.3 独特能力分析

**Claude Code 独有**：
- `prompt` / `agent` 类型 Hook：LLM 语义级判断
- `FileChanged`：文件监控驱动的响应式 Hook
- `hookify`：从对话中自动生成 Hook 规则
- HTTP Hook：与外部系统集成

**Gemini CLI 独有**：
- `BeforeModel` / `AfterModel`：在 LLM 调用层面拦截（可注入合成响应）
- `BeforeToolSelection`：修改工具选择（动态调整可用工具集）
- `runtime` 处理器：原生 TypeScript 函数，零序列化开销

**Qwen Code 独有**：
- MessageBus 异步协议：与 CoreToolScheduler 深度集成
- 权限决策框架：`getPermissionDecision()` / `getPermissionDecisionReason()`

### 5.4 安全模型

| Agent | 信任模型 | 说明 |
|-------|---------|------|
| Claude Code | **显式信任** | 所有 Hook 需用户接受工作区信任对话框 |
| Gemini CLI | 隐式信任 | 项目 Hook 在不受信任目录中被阻止 |
| Qwen Code | 隐式信任 | Hook 通过 MessageBus 执行 |

Claude Code 的显式信任对话框是**防止恶意仓库通过 `.claude/settings.json` 执行任意命令**的关键防线。

## 六、实际使用场景

### 场景 1：保护关键文件

```json
{
  "hooks": {
    "PreToolUse": [{
      "matcher": "Write|Edit",
      "hooks": [{
        "type": "command",
        "command": "echo $TOOL_INPUT | jq -r '.file_path // .path' | grep -qE '\\.(env|pem|key)$' && exit 2 || exit 0"
      }]
    }]
  }
}
```

### 场景 2：LLM 安全审查（prompt Hook）

```json
{
  "hooks": {
    "PreToolUse": [{
      "matcher": "Bash",
      "hooks": [{
        "type": "prompt",
        "prompt": "Shell command: $ARGUMENTS. Is it safe? Consider: destructive ops, credential exposure, network access, production impact. Reply {\"ok\": true} or {\"ok\": false, \"reason\": \"...\"}",
        "model": "claude-haiku-4-5"
      }]
    }]
  }
}
```

### 场景 3：编辑后自动格式化

```json
{
  "hooks": {
    "PostToolUse": [{
      "matcher": "Write|Edit",
      "hooks": [{
        "type": "command",
        "command": "npx prettier --write \"$(echo $TOOL_INPUT | jq -r '.file_path // .path')\"",
        "if": "Write(*.ts)|Write(*.tsx)|Edit(*.ts)|Edit(*.tsx)"
      }]
    }]
  }
}
```

### 场景 4：结束前强制测试

```json
{
  "hooks": {
    "Stop": [{
      "matcher": "*",
      "hooks": [{
        "type": "command",
        "command": "npm test 2>&1 | tail -20; exit $?",
        "statusMessage": "Running tests..."
      }]
    }]
  }
}
```

### 场景 5：压缩后重注入关键上下文

```json
{
  "hooks": {
    "PostCompact": [{
      "matcher": "*",
      "hooks": [{
        "type": "command",
        "command": "echo '{\"hookSpecificOutput\":{\"hookEventName\":\"PostCompact\",\"additionalContext\":\"REMINDER: This project uses pnpm, not npm. Always use pnpm commands.\"}}'"
      }]
    }]
  }
}
```

## 七、hookify：从对话中自动生成规则

这是 Claude Code Hook 系统中最具创新性的设计——**将用户的挫败转化为持久化的行为约束**。

### 7.1 问题

用户反复纠正 Agent 同样的错误——"不要用 npm，我们用 pnpm"、"别改 .env"、"停止删测试"。每次纠正消耗 token 但不留痕迹，下次会话又犯。

### 7.2 解决方案

```bash
/hookify                          # 分析对话，自动发现需要约束的行为
/hookify 禁止使用 rm -rf 命令     # 指定要阻止的行为
/hookify list                     # 查看已有规则
/hookify configure                # 启用/禁用规则
```

### 7.3 工作原理

1. 分析最近 10-15 条用户消息，用 NLP 识别挫败信号（"不要这样做"、"停止"、"为什么又..."）
2. 识别导致挫败的 Agent 行为模式
3. 生成 `.claude/hookify.{rule-name}.local.md` 规则文件
4. 规则文件使用 YAML Frontmatter 定义事件类型、正则匹配、显示消息
5. **即时生效**——无需重启

### 7.4 开发者启示

hookify 展示了一条"**对话 → 规则**"的自动化路径——用户的自然语言纠正被结构化为持久化的 Hook 规则。这比让用户手动编辑 settings.json 写 Hook 配置要友好得多。Qwen Code 可以实现类似机制：分析用户对 Agent 行为的否定表达，自动生成 `.qwen/hooks/` 规则。

## 八、Qwen Code Hook 系统改进建议

### P1：扩展事件类型

当前 Qwen Code 有 12 种事件，与 Claude Code 早期版本（v1.0.38）接近。建议优先补充：

| 新增事件 | 价值 | 难度 |
|---------|------|------|
| `PostCompact` | 压缩后重注入关键上下文 | 小 |
| `FileChanged` | 文件监控驱动的响应式 Hook | 中 |
| `TaskCreated` / `TaskCompleted` | 多 Agent 任务追踪 | 小 |
| `StopFailure` | Stop Hook 失败恢复 | 小 |
| `PermissionDenied` | 权限拒绝后引导 | 小 |

### P1：if 条件过滤

当前所有匹配 matcher 的 Hook 都会触发。添加 `if` 字段支持权限规则语法（如 `"Bash(git *)"` 只对 git 命令触发），避免不必要的 Hook 执行开销。

### P2：prompt 类型 Hook

Claude Code 的核心创新。用 LLM 做语义级安全判断——超越静态规则的能力边界。实现要点：
- 默认使用小模型（如 qwen3.5-flash）降低成本和延迟
- `$ARGUMENTS` 占位符注入事件数据
- 返回 `{"ok": true/false, "reason": "..."}`

### P2：HTTP Hook

支持 POST 到外部 webhook，为 CI/CD 集成、审计日志、Slack 通知等场景打开大门。需注意 SSRF 防护。

### P3：hookify 自动规则生成

分析用户对 Agent 的否定表达，自动生成 Hook 规则。长期看这是提升用户体验的关键——从"手动配置"到"对话式学习"。
