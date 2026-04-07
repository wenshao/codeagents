# 12. Hook 系统——开发者参考

> Claude Code 的 Hook 系统覆盖 27 种事件、6 种处理器类型，支持 shell 命令、LLM 推理、Agent 验证、HTTP 回调等多种执行方式。这是目前 CLI Code Agent 中最完整的 Hook 实现。
>
> **Qwen Code 对标**：Qwen Code 有 BeforeTool/AfterTool/Notification 等基础 Hook 事件。Claude Code 的 27 种事件 + prompt/agent 类型 Hook（LLM 推理决策）是主要差距。

## 一、27 种 Hook 事件

### 工具执行（5 种）

| 事件 | 触发时机 | 可干预行为 |
|------|---------|-----------|
| `PreToolUse` | 工具执行前 | 阻止执行、修改输入、更改权限 |
| `PostToolUse` | 工具执行成功后 | 替换输出、注入上下文 |
| `PostToolUseFailure` | 工具执行失败后 | 注入错误上下文 |
| `PermissionRequest` | 权限系统请求审批时 | allow/deny/ask 决策 |
| `PermissionDenied` | 权限被拒绝后 | 请求重试 |

### 会话生命周期（3 种）

| 事件 | 触发时机 | 用途 |
|------|---------|------|
| `SessionStart` | 会话开始（启动/恢复/清除/压缩后） | 注入初始上下文、设置监控路径 |
| `SessionEnd` | 会话结束 | 清理资源、发送通知 |
| `Setup` | 初始化设置 | 环境配置 |

### Agent 生命周期（4 种）

| 事件 | 触发时机 | 用途 |
|------|---------|------|
| `Stop` | Agent 执行停止 | 后处理（格式化、测试、通知） |
| `StopFailure` | Stop Hook 失败 | 错误处理 |
| `SubagentStart` | Subagent 启动前 | 注入上下文、权限检查 |
| `SubagentStop` | Subagent 停止后 | 结果聚合 |

### 上下文压缩（2 种）

| 事件 | 触发时机 | 用途 |
|------|---------|------|
| `PreCompact` | 压缩前 | 保存关键信息 |
| `PostCompact` | 压缩后 | 验证压缩结果 |

### 任务与团队（3 种）

| 事件 | 触发时机 | 用途 |
|------|---------|------|
| `TeammateIdle` | 队友空闲 | 分配新任务 |
| `TaskCreated` | 任务创建 | 通知、分配 |
| `TaskCompleted` | 任务完成 | 后处理、通知 |

### 文件与配置（4 种）

| 事件 | 触发时机 | 用途 |
|------|---------|------|
| `FileChanged` | 监控的文件变更 | 自动重载、触发构建 |
| `CwdChanged` | 工作目录变更 | 刷新上下文 |
| `ConfigChange` | 设置变更 | 重载配置 |
| `InstructionsLoaded` | 指令文件加载 | 指令验证 |

### Worktree（2 种）

| 事件 | 触发时机 | 用途 |
|------|---------|------|
| `WorktreeCreate` | Git worktree 创建 | 初始化隔离环境 |
| `WorktreeRemove` | Git worktree 删除 | 清理 |

### 用户交互（2 种）

| 事件 | 触发时机 | 用途 |
|------|---------|------|
| `UserPromptSubmit` | 用户提交 prompt | 输入预处理、验证 |
| `Notification` | 通知事件 | 外部推送 |

### MCP（2 种）

| 事件 | 触发时机 | 用途 |
|------|---------|------|
| `Elicitation` | MCP 引导请求 | 自定义引导流程 |
| `ElicitationResult` | MCP 引导结果 | 处理结果 |

## 二、6 种 Hook 处理器类型

### 1. Command Hook（shell 命令）

最常用的类型。执行 shell 命令，通过 stdin 接收事件 JSON，通过 exit code 和 stdout JSON 返回结果。

```json
{
  "type": "command",
  "command": "bash /path/to/check.sh",
  "shell": "bash",
  "timeout": 30,
  "if": "Bash(git *)",
  "statusMessage": "Checking...",
  "async": false
}
```

**Exit Code 约定**：
- `0`：成功，不阻止
- `2`：阻止（触发 `decision: 'block'`）
- `1` 或其他：非阻止性错误（记录日志但不阻止）

### 2. Prompt Hook（LLM 推理决策）

**Claude Code 独有设计**——用 LLM 判断 Hook 是否应该阻止操作。使用 `$ARGUMENTS` 占位符注入事件数据。

```json
{
  "type": "prompt",
  "prompt": "This command will be executed: $ARGUMENTS. Is it safe? Answer {\"ok\": true} or {\"ok\": false, \"reason\": \"...\"}",
  "model": "claude-haiku-4-5",
  "timeout": 15
}
```

**开发者启示**：这是一种"用 AI 验证 AI"的模式。相比静态规则（command hook），prompt hook 可以理解语义——例如判断 `rm -rf node_modules` 是安全的（清理依赖）而 `rm -rf /` 是危险的，即使两者都匹配 `rm -rf` 模式。

### 3. Agent Hook（完整 Agent 验证）

创建一个临时 Agent，可以读取 transcript、使用工具进行深度验证。最多 50 轮交互。

```json
{
  "type": "agent",
  "prompt": "Verify the implementation is correct: $ARGUMENTS",
  "model": "claude-opus-4-6",
  "timeout": 60
}
```

### 4. HTTP Hook（外部 webhook）

POST JSON 到外部 HTTP 端点。支持 SSRF 防护和环境变量注入。

```json
{
  "type": "http",
  "url": "https://api.example.com/hooks",
  "headers": {
    "Authorization": "Bearer $MY_TOKEN"
  },
  "allowedEnvVars": ["MY_TOKEN"],
  "timeout": 30
}
```

### 5. Callback Hook（内部 TypeScript）

运行时注册的 TypeScript 函数，无子进程开销。用于系统级 Hook（文件追踪、归因）。

### 6. Function Hook（会话级回调）

会话内临时注册的 TypeScript 回调，用于结构化输出校验等临时验证。不可持久化。

## 三、Hook 输入/输出 Schema

### 通用输入（所有 Hook 都接收）

```typescript
{
  session_id: string,
  transcript_path: string,    // 可用于读取完整对话历史
  cwd: string,
  permission_mode?: string,
  agent_id?: string,          // Subagent 时有值
  agent_type?: string,
  hook_event_name: string     // 事件名称
  // + 事件特定字段
}
```

### 事件特定输入

| 事件 | 特定字段 |
|------|---------|
| `PreToolUse` | `tool_name`、`tool_input`、`tool_use_id` |
| `PostToolUse` | `tool_name`、`tool_input`、`tool_response`、`tool_use_id` |
| `SessionStart` | `source`（'startup'/'resume'/'clear'/'compact'）、`model`、`agent_type` |
| `PermissionRequest` | `tool_name`、`tool_input`、`behavior` |

### 输出 Schema

```typescript
{
  continue?: boolean,          // false = 阻止继续执行
  decision?: 'approve'|'block',
  reason?: string,
  systemMessage?: string,      // 注入给用户的警告
  suppressOutput?: boolean,    // 隐藏 stdout
  hookSpecificOutput?: {
    hookEventName: string,
    permissionDecision?: 'allow'|'deny'|'ask',
    updatedInput?: {...},      // 修改工具输入
    updatedMCPToolOutput?: any, // 替换工具输出
    additionalContext?: string, // 注入模型上下文
    initialUserMessage?: string, // SessionStart 初始消息
    watchPaths?: string[],     // 监控文件路径
    retry?: boolean            // PermissionDenied 后重试
  }
}
```

## 四、Hook 执行流程

```
事件触发
  │
  ├─ getMatchingHooks()        ← 按 matcher 匹配
  │     ├─ 简单字符串：精确匹配
  │     ├─ 管道分隔：多值匹配（"Write|Edit"）
  │     ├─ 正则：完整 regex
  │     └─ *：匹配所有
  │
  ├─ if 条件过滤              ← 权限规则语法（如 "Bash(git *)"）
  │     └─ 在 spawn 子进程前过滤（节省开销）
  │
  ├─ 去重                     ← 跨来源（user/project/local）去重
  │
  ├─ 并行执行所有匹配 Hook    ← 每个 Hook 独立超时
  │
  ├─ 结果聚合
  │     └─ 权限优先级：deny > ask > allow
  │
  └─ 应用结果
        ├─ continue:false → 阻止执行
        ├─ updatedInput → 修改工具输入
        ├─ permissionDecision → 更改权限行为
        └─ additionalContext → 注入系统消息
```

## 五、配置示例

### 示例 1：自动格式化（PostToolUse）

```json
{
  "hooks": {
    "PostToolUse": [{
      "matcher": "Write|Edit",
      "hooks": [{
        "type": "command",
        "command": "npx prettier --write \"$TOOL_INPUT_PATH\"",
        "if": "Write(*.ts)|Write(*.tsx)|Edit(*.ts)|Edit(*.tsx)"
      }]
    }]
  }
}
```

### 示例 2：危险命令 LLM 审查（PreToolUse）

```json
{
  "hooks": {
    "PreToolUse": [{
      "matcher": "Bash",
      "hooks": [{
        "type": "prompt",
        "prompt": "A shell command is about to execute: $ARGUMENTS. Is this command safe and appropriate? Consider: destructive operations, network access, credential exposure. Reply {\"ok\": true} or {\"ok\": false, \"reason\": \"...\"}",
        "model": "claude-haiku-4-5"
      }]
    }]
  }
}
```

### 示例 3：测试保护（Stop）

```json
{
  "hooks": {
    "Stop": [{
      "matcher": "*",
      "hooks": [{
        "type": "command",
        "command": "npm test 2>&1 | tail -20; exit $?"
      }]
    }]
  }
}
```

## 六、与 Qwen Code Hook 系统对比

| 能力 | Claude Code | Qwen Code | Gemini CLI |
|------|-------------|-----------|-----------|
| 事件数量 | **27 种** | ~6 种（BeforeTool/AfterTool/SessionStart/SessionEnd/PreCompress/Notification） | ~8 种（BeforeTool/AfterTool/SessionStart/SessionEnd/PreCompress/Notification/BeforeAgent/AfterAgent） |
| 处理器类型 | command + **prompt + agent** + http + callback + function | command | command |
| LLM 驱动决策 | ✓（prompt/agent 类型） | — | — |
| 工具输入修改 | ✓（updatedInput） | — | — |
| 工具输出替换 | ✓（updatedMCPToolOutput） | — | — |
| 权限集成 | ✓（allow/deny/ask） | ✓（通过 hook 返回值） | — |
| HTTP Webhook | ✓（带 SSRF 防护） | — | — |
| 异步执行 | ✓（async/asyncRewake） | — | — |
| 条件过滤 | ✓（if 字段，权限规则语法） | — | — |
| 去重 | ✓（跨来源去重） | — | — |

### 开发者建议

Qwen Code 可分阶段增强 Hook 系统：

1. **P1：扩展事件类型**——增加 `SubagentStart/Stop`、`FileChanged`、`WorktreeCreate/Remove` 等事件
2. **P1：if 条件过滤**——支持 `"if": "Bash(git *)"` 语法，避免所有 Bash 命令都触发 Hook
3. **P2：prompt 类型 Hook**——用 LLM 做语义级安全审查（Claude Code 独有创新）
4. **P2：HTTP Hook**——支持 POST 到外部 webhook（CI/CD 集成）
5. **P3：updatedInput**——允许 Hook 修改工具输入（如自动添加 `--dry-run`）

## 七、hookify 自动规则生成

Claude Code 的 `/hookify` 插件能从对话中自动生成 Hook 规则：

1. 分析最近 10-15 条用户消息，查找挫败信号（"不要这样做"、"停止"、"为什么又..."）
2. 识别导致挫败的行为模式
3. 生成 `.claude/hookify.{rule-name}.local.md` 规则文件
4. 规则即时生效，无需重启

```bash
/hookify                         # 从对话分析创建规则
/hookify 禁止使用 rm -rf 命令    # 指定要阻止的行为
/hookify list                    # 列出已有规则
/hookify configure               # 启用/禁用规则
```

**开发者启示**：hookify 展示了一种"从用户反馈中自动学习约束"的模式——用户的挫败表达被转化为持久化的行为规则。Qwen Code 可以参考这种"对话 → 规则"的自动化路径。
