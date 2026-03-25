# 5. 策略引擎与安全

## 策略/权限系统

```toml
# .gemini/policies/my-rules.toml（策略目录下可有多个 .toml 文件）
[[rule]]
toolName = "run_shell_command"
decision = "ask_user"
priority = 10

[[rule]]
toolName = "read_file"
decision = "allow"
priority = 5

[[rule]]
toolName = "mcp_*"
decision = "ask_user"
priority = 3

[[rule]]
toolName = "*"
argsPattern = ".*\\.env.*"
decision = "deny"
denyMessage = "禁止访问 .env 文件"
priority = 100
```

**四种审批模式**（ApprovalMode）：
- **DEFAULT**：每个非只读工具调用都询问用户
- **AUTO_EDIT**：自动跳过编辑操作的确认
- **YOLO**：自动批准所有工具调用（无确认）
- **PLAN**：只读规划模式，仅允许只读工具

**策略规则字段**：
- `toolName` — 目标工具（支持 `*` 通配符）
- `mcpName` — MCP 服务器名称
- `argsPattern` — 正则表达式匹配参数
- `toolAnnotations` — 工具元数据匹配（如 `readOnlyHint`）
- `decision` — ALLOW / DENY / ASK_USER
- `priority` — 数值越大优先级越高
- `modes` — 审批模式过滤
- `interactive` — 交互/非交互环境过滤
- `allowRedirection` — 允许 Shell 重定向
- `denyMessage` — 自定义拒绝消息

**策略优先级**（5 级 Tier，从高到低）：Admin（Tier 5）→ User（Tier 4，含 settings 动态规则）→ Workspace/Project（Tier 3）→ Extension（Tier 2）→ Default（Tier 1）

**内置策略文件**（9 个）：conseca.toml、discovered.toml、memory-manager.toml、plan.toml、read-only.toml、sandbox-default.toml、tracker.toml、write.toml、yolo.toml

## Hook 系统

```jsonc
// settings.json 或 .gemini/settings.json
{
  "hooks": {
    "BeforeTool": [
      {
        "matcher": "run_shell_command",
        "hooks": [
          { "type": "command", "command": "echo 检查命令安全性", "timeout": 5000 }
        ]
      }
    ],
    "AfterAgent": [
      {
        "hooks": [
          { "type": "command", "command": "echo 代理完成" }
        ]
      }
    ]
  }
}
```

**11 种 Hook 事件**：

| 事件 | 触发时机 | 可用操作 |
|------|----------|---------|
| **BeforeTool** | 工具执行前 | 修改输入参数、阻止/拒绝/批准执行 |
| **AfterTool** | 工具执行后 | 后处理 |
| **BeforeAgent** | 代理启动前 | 预处理 |
| **AfterAgent** | 代理完成后 | 后处理 |
| **BeforeModel** | LLM 调用前 | 修改请求 |
| **AfterModel** | LLM 响应后 | 后处理响应 |
| **BeforeToolSelection** | 工具选择前 | 覆盖工具选择 |
| **Notification** | 通知事件 | 自定义通知处理 |
| **SessionStart** | 会话开始 | 初始化 |
| **SessionEnd** | 会话结束 | 清理 |
| **PreCompress** | 上下文压缩前 | 预处理 |

**Hook 类型**：
- **Command**：执行外部子进程，支持环境变量和超时
- **Runtime**：TypeScript 函数（扩展内部使用）

**Hook 决策**：`ask`（询问用户）| `block`（阻止）| `deny`（拒绝）| `approve`（批准）| `allow`（允许）

## 会话管理

- **AgentSession**：实现 AsyncIterable 协议，支持事件流式订阅和回放
- **事件类型**：agent_start、agent_end、tool_call、thought
- **会话压缩**：长对话自动压缩（`/compress` 命令）
- **会话恢复**：`gemini --resume <session-id>`
- **检查点（Checkpointing）**（源码：`checkpointing.md`、`rewindCommand.tsx`、`rewindFileOps.ts`）：
  - 默认关闭，需在 `settings.json` 中启用：`{ "general": { "checkpointing": { "enabled": true } } }`
  - 当批准文件修改工具（write_file/replace）时自动创建检查点
  - 每个检查点包含三部分：
    1. **Git 快照**：在影子 Git 仓库 `~/.gemini/history/<project_hash>` 中创建提交（不影响用户项目 Git）
    2. **对话历史**：完整会话上下文保存在 `~/.gemini/tmp/<project_hash>/checkpoints`
    3. **工具调用**：记录即将执行的工具调用参数
  - 恢复检查点（`/restore` 命令）：还原文件 + 恢复对话 + 重新提议原工具调用
- **回退（Rewind）**（源码：`rewindCommand.tsx`、`rewindFileOps.ts`、`docs/cli/rewind.md`）：
  - 触发方式：`/rewind` 命令或 `Esc Esc` 快捷键
  - 交互式 UI：上下箭头选择回退点，显示每步的用户提示和文件变更统计
  - 三种回退选项（确认对话框）：
    1. **回退对话 + 还原代码**：同时撤销聊天和文件修改
    2. **仅回退对话**：保留文件修改，仅撤销聊天历史
    3. **仅还原代码**：保留聊天历史，仅撤销文件修改
  - 文件变更统计（`rewindFileOps.ts:calculateTurnStats()`）：基于工具调用结果的 diff 计算添加/删除行数和文件数
  - 限制：仅回退 AI 工具造成的文件修改，不回退手动编辑或 Shell 工具（`!`）执行的变更
  - 支持跨会话压缩点回退（从存储的 session 数据重建历史）

## 记忆系统（源码：`memoryTool.ts`、`memory.ts`、`memoryDiscovery.ts`）

**分层记忆结构**（`HierarchicalMemory` 接口，`config/memory.ts`）：
```typescript
{
  global: string    // ~/.gemini/GEMINI.md（全局记忆）
  extension: string // 扩展级记忆
  project: string   // ./GEMINI.md 或 .gemini/GEMINI.md（项目级记忆）
}
```

展平时按 `--- Global ---`、`--- Extension ---`、`--- Project ---` 区段拼接（`flattenMemory()` 函数）。

**GEMINI.md 层级**（`memoryDiscovery.ts`）：
1. `~/.gemini/GEMINI.md` — 全局（所有项目通用偏好）
2. 项目根目录 `GEMINI.md` — 项目级（提交到 Git 共享给团队）
3. 子目录 `GEMINI.md` — 目录特定规则
4. 文件名可自定义（`setGeminiMdFilename()`），支持数组配置多个文件名

**save_memory 工具**（`memoryTool.ts`）：
- 存储格式：Markdown 列表项（`- fact text`）
- 写入位置：全局 GEMINI.md（`~/.gemini/GEMINI.md`）
- 区段标记：`## Gemini Added Memories` 头部，追加写入
- 需用户确认（工具调用前显示 diff 预览）

**文件发现**（`memoryDiscovery.ts`）：
- BFS 搜索发现所有 GEMINI.md 文件
- 按文件标识（device + inode）去重（处理大小写不敏感文件系统和符号链接）
- 支持 `@import` 语法导入其他 Markdown 文件（`memoryImportProcessor.ts`）

**`/memory` 命令**（`packages/core/src/commands/memory.ts`）：
- `/memory show`：显示所有层级的记忆内容和文件数
- `/memory add <text>`：触发 save_memory 工具保存事实
- `/memory reload`：重新扫描并加载所有 GEMINI.md 文件
- `/memory files`：列出当前生效的所有 GEMINI.md 文件路径

**记忆管理代理**：专用 memory_manager 代理（条件注册，需设置启用）处理增删改、去重、组织，使用 Flash 模型

## 技能系统（Agent Skills）

**技能定义结构**：
```typescript
{
  name: string        // 唯一标识
  description: string // 用户可见描述
  body: string        // 提示内容
  isBuiltin: boolean  // 是否内置
  disabled: boolean   // 管理控制
  location: string    // 文件路径
}
```

**技能加载层级**（优先级从低到高）：
1. 内置技能
2. 扩展技能
3. 用户技能（`~/.gemini/skills/` 或 `~/.agents/skills/`）
4. 项目技能（`.gemini/skills/` 或 `.agents/skills/`）

- **`/skills` 命令**：查看和管理技能
- **`activate_skill` 工具**：在代理对话中激活指定技能
- 技能管理器支持发现、启用/禁用、管理员覆盖

## 安全

**已修复漏洞**：
- **P1 提示注入漏洞**（2025-06-27 Tracebit 发现，v0.1.14 修复）：命令白名单绕过、空白字符视觉隐藏、通过 README.md/项目上下文文件注入，可导致静默任意代码执行
- **数据泄露漏洞**（已修复）：修复了可能导致静默数据外泄的缺陷

**安全特性**：
- **沙箱**：无沙箱（默认，带红色警告）→ Seatbelt / Bubblewrap / Docker / Podman / gVisor / LXC / Windows Sandbox（7 种后端可选）
- **安全扩展**：官方安全扩展，支持代码变更和 PR 的漏洞扫描
- **Shell 命令白名单**（v0.24.0+）
- **默认 untrusted 文件夹**（v0.24.0+）
- **所有 Shell 命令需权限**（v0.1.14+）
- **私有 IP 阻止**：web_fetch 工具阻止访问私有 IP 地址
- **`.env` 文件保护**：默认拒绝访问环境文件
