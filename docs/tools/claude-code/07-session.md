# 7. 会话、记忆与 MCP

## 会话管理

### 上下文压缩
当对话历史接近上下文窗口限制时，Claude Code 自动压缩早期对话内容，保留关键信息：
- 自动触发：接近 ~95% token 上限时
- 手动触发：`/compact` 命令
- Hook 支持：PreCompact/PostCompact 事件允许自定义压缩前后行为

**压缩后 UI 行为**：压缩完成后清空屏幕旧对话，仅显示 "Summarized conversation" 标记——屏幕内容与模型上下文保持同步。详见[压缩后 UI 行为分析](../../comparison/context-compression-deep-dive.md)。

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

### Prompt Suggestions（下一步提示预测）

Claude Code 在每轮对话结束后，自动预测用户下一步可能输入的内容，以蓝紫色提示文本显示在输入框中。该功能内部代号为 **tengu_chomp_inflection**。

#### 架构概览

```
┌─────────────────────────────────────────────────────────────────┐
│  stopHooks.ts                                                   │
│  query/stopHooks.ts#L139                                        │
│  每轮 assistant 回复完成后触发                                      │
│  void executePromptSuggestion(stopHookContext)                  │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│  executePromptSuggestion()                                      │
│  services/PromptSuggestion/promptSuggestion.ts#L184             │
│  仅处理 querySource === 'repl_main_thread' 的主线程请求             │
│                                                                 │
│  1. tryGenerateSuggestion() — 守卫检查 + 生成 + 过滤              │
│  2. 写入 AppState.promptSuggestion                              │
│  3. 如果 Speculation 启用 → startSpeculation()                  │
└────────────────────┬────────────────────────────────────────────┘
                     │
              ┌──────┴──────┐
              ▼             ▼
┌──────────────────┐  ┌──────────────────────────────────────────┐
│ usePromptSuggestion│  │ startSpeculation()                       │
│ hooks/             │  │ services/PromptSuggestion/speculation.ts │
│ usePromptSuggestion│  │ 以 suggestion 为假设输入预执行 agent       │
│ .ts                │  │ (仅限 Anthropic 内部用户启用)              │
│                    │  └──────────────────────────────────────────┘
│ 管理 UI 显示       │
│ Tab/Enter 接受     │
│ 遥测日志           │
└──────────────────┘
```

#### 工作原理

1. **触发时机**：每轮 assistant 回复完成后，在 stop hooks 阶段以 fire-and-forget 方式异步发起（源码: `query/stopHooks.ts#L139`）
2. **生成方式**：调用 `runForkedAgent()` 复用主对话的缓存参数（`cacheSafeParams`），将专用 prompt 作为 user message 追加到对话历史，请求模型预测用户下一条消息（源码: `services/PromptSuggestion/promptSuggestion.ts#L294-352`）
3. **独立请求**：suggestion 请求标记为 `querySource: "prompt_suggestion"`、`forkLabel: "prompt_suggestion"`，不写入对话 transcript，也不写入缓存（`skipTranscript: true, skipCacheWrite: true`）
4. **禁止工具**：suggestion 请求中所有工具调用均通过 `canUseTool` 回调拒绝（`behavior: "deny"`），模型只能返回纯文本
5. **缓存复用**：刻意不覆盖任何 API 参数（不设 `effortValue`、`maxOutputTokens` 等），以确保命中主对话的 prompt cache。历史教训：PR #18143 尝试设置 `effort:'low'` 导致 cache 命中率从 92.7% 暴跌至 61%（源码注释: `promptSuggestion.ts#L308-318`）

#### 专用 Prompt

suggestion 生成使用常量 `SUGGESTION_PROMPT`（源码: `services/PromptSuggestion/promptSuggestion.ts#L258-287`）：

```
[SUGGESTION MODE: Suggest what the user might naturally type next into Claude Code.]

FIRST: Look at the user's recent messages and original request.

Your job is to predict what THEY would type - not what you think they should do.

THE TEST: Would they think "I was just about to type that"?

EXAMPLES:
User asked "fix the bug and run tests", bug is fixed → "run the tests"
After code written → "try it out"
Claude offers options → suggest the one the user would likely pick, based on conversation
Claude asks to continue → "yes" or "go ahead"
Task complete, obvious follow-up → "commit this" or "push it"
After error or misunderstanding → silence (let them assess/correct)

Be specific: "run the tests" beats "continue".

NEVER SUGGEST:
- Evaluative ("looks good", "thanks")
- Questions ("what about...?")
- Claude-voice ("Let me...", "I'll...", "Here's...")
- New ideas they didn't ask about
- Multiple sentences

Stay silent if the next step isn't obvious from what the user said.

Format: 2-12 words, match the user's style. Or nothing.

Reply with ONLY the suggestion, no quotes or explanation.
```

Prompt 通过 `PromptVariant` 类型索引（源码: `promptSuggestion.ts#L31-35`），当前仅有 `'user_intent'` 和 `'stated_intent'` 两个变体，均映射到同一 prompt 模板。

#### 过滤机制

生成的 suggestion 经过 12 条过滤规则严格筛选（源码: `services/PromptSuggestion/promptSuggestion.ts#L354-456`，函数 `shouldFilterSuggestion`），不满足条件的被静默丢弃：

| 过滤规则 | 说明 | 匹配示例 |
|----------|------|----------|
| `done` | 内容恰好为 "done" | `done` |
| `meta_text` | 模型输出元描述而非真实预测 | "nothing to suggest"、"silence"、"nothing found" |
| `meta_wrapped` | 被括号包裹的元推理 | `(silence — ...)`、`[no suggestion]` |
| `error_message` | API 错误信息泄漏 | "api error: ..."、"prompt is too long"、"image was too large" |
| `prefixed_label` | 带 `word: ` 标签前缀 | "Next step: run tests" |
| `too_few_words` | 少于 2 个单词（允许斜杠命令和特定单词） | 单个普通单词（非 yes/ok/push/commit 等） |
| `too_many_words` | 超过 12 个单词 | 过长的句子 |
| `too_long` | ≥100 个字符 | — |
| `multiple_sentences` | 包含多个句子（`/[.!?]\s+[A-Z]/`） | "Do this. Then that." |
| `has_formatting` | 包含换行符或 Markdown 格式 | 含 `\n`、`*`、`**` |
| `evaluative` | 评价性/感谢语句 | "looks good"、"thanks"、"perfect"、"awesome" |
| `claude_voice` | 模型自身语气开头 | "Let me..."、"I'll..."、"Here's..."、"You should..." |

**允许的单词白名单**（即使只有 1 个单词也不过滤）：

| 类别 | 单词 |
|------|------|
| 肯定词 | yes, yeah, yep, yea, yup, sure, ok, okay |
| 动作词 | push, commit, deploy, stop, continue, check, exit, quit |
| 否定词 | no |

#### 交互方式

| 操作 | 效果 | 遥测 `acceptMethod` |
|------|------|---------------------|
| **Tab** | 接受 suggestion 填入输入框（可继续编辑后再提交） | `tab` |
| **Enter**（输入框为空时） | 接受 suggestion 并直接提交 | `enter` |
| **→**（右箭头） | 接受 suggestion 填入输入框 | — |
| 开始输入其他内容 | suggestion 自动消失，Speculation 被中止 | — |
| 忽略（直接输入新内容提交） | suggestion 在下一轮对话后被新预测替换 | `ignored` |

接受判定逻辑（源码: `hooks/usePromptSuggestion.ts#L116-117`）：
- Tab 按下：`acceptedAt > shownAt`
- 或：用户最终提交内容 === suggestion 文本（空 Enter 场景）

#### 状态数据结构

```typescript
// 源码: state/AppStateStore.ts#L385-391
promptSuggestion: {
  text: string | null           // suggestion 文本内容
  promptId: 'user_intent' | 'stated_intent' | null  // prompt 变体标识
  shownAt: number               // 首次渲染时间戳（用于计算 timeToAcceptMs）
  acceptedAt: number            // Tab 接受时间戳
  generationRequestId: string | null  // 关联的 API 请求 ID（用于 RL 数据集关联）
}
```

#### 抑制条件

suggestion 生成分为两层守卫——**初始化守卫**和**运行时守卫**：

**初始化守卫**（源码: `promptSuggestion.ts#L37-94`，函数 `shouldEnablePromptSuggestion`）：

| 检查顺序 | 条件 | 结果 |
|----------|------|------|
| 1 | 环境变量 `CLAUDE_CODE_ENABLE_PROMPT_SUGGESTION` 为 falsy | 禁用 |
| 2 | 环境变量 `CLAUDE_CODE_ENABLE_PROMPT_SUGGESTION` 为 truthy | 启用 |
| 3 | GrowthBook flag `tengu_chomp_inflection` 为 false | 禁用 |
| 4 | 非交互模式（`-p`、管道输入、SDK） | 禁用 |
| 5 | Swarm teammate（非 leader） | 禁用 |
| 6 | `settings.promptSuggestionEnabled !== false` | 按设置值 |

**运行时守卫**（源码: `promptSuggestion.ts#L107-119`，函数 `getSuggestionSuppressReason`）：

| 条件 | 抑制原因 |
|------|----------|
| `promptSuggestionEnabled === false` | `disabled` |
| 存在待审批的 Worker/Sandbox 权限请求 | `pending_permission` |
| MCP elicitation 队列非空 | `elicitation_active` |
| Plan mode 激活 | `plan_mode` |
| 外部用户且速率限制触发 | `rate_limit` |

**生成前守卫**（源码: `promptSuggestion.ts#L125-182`，函数 `tryGenerateSuggestion`）：

| 条件 | 抑制原因 |
|------|----------|
| AbortController 已中止 | `aborted` |
| assistant 回复不足 2 轮 | `early_conversation` |
| 上一条回复是 API 错误 | `last_response_error` |
| 上一条回复未缓存 token 数 > 10,000 | `cache_cold` |

#### 配置方式

| 方式 | 说明 |
|------|------|
| `/config` → "Prompt suggestions" | 交互式配置菜单中切换开关 |
| `settings.json` 中设置 `"promptSuggestionEnabled": false` | 持久化关闭 |
| 环境变量 `CLAUDE_CODE_ENABLE_PROMPT_SUGGESTION=0` | 强制关闭（优先级最高） |
| 环境变量 `CLAUDE_CODE_ENABLE_PROMPT_SUGGESTION=1` | 强制开启（优先级最高） |
| GrowthBook feature flag `tengu_chomp_inflection` | 服务端灰度发布控制 |

#### UI 样式

suggestion 文本使用主题中的 `suggestion` 颜色渲染：

| 主题 | 颜色 |
|------|------|
| Light | `rgb(87, 105, 247)`（蓝紫色） |
| Dark | `rgb(177, 185, 249)`（浅蓝紫色） |
| ANSI Light | `ansi:blue` |
| ANSI Dark | `ansi:blueBright` |

#### 遥测事件

**初始化事件** `tengu_prompt_suggestion_init`（源码: `promptSuggestion.ts#L41-92`）：

| 字段 | 说明 |
|------|------|
| `enabled` | 是否启用 |
| `source` | 决策来源：`env` / `growthbook` / `non_interactive` / `swarm_teammate` / `setting` |

**结果事件** `tengu_prompt_suggestion`（源码: `hooks/usePromptSuggestion.ts#L120-157`、`promptSuggestion.ts#L462-523`）：

| 字段 | 说明 |
|------|------|
| `source` | `cli`（TUI）或 `sdk`（API 消费方） |
| `outcome` | `accepted` / `ignored` / `suppressed` |
| `prompt_id` | `user_intent` / `stated_intent` |
| `reason` | 抑制原因（仅 suppressed 时） |
| `acceptMethod` | `tab` / `enter`（仅 CLI 且 accepted 时） |
| `timeToAcceptMs` | 从显示到接受的毫秒数 |
| `timeToIgnoreMs` | 从显示到忽略的毫秒数 |
| `timeToFirstKeystrokeMs` | 从显示到首次按键的毫秒数 |
| `wasFocusedWhenShown` | suggestion 出现时终端是否有焦点 |
| `similarity` | `finalInput.length / suggestion.length`（相似度） |

> Anthropic 内部用户（`USER_TYPE === 'ant'`）额外记录 `suggestion` 和 `userInput` 原文，用于 RL 数据集训练。

#### Speculation（推测执行）

Prompt Suggestions 是更深层 **Speculation** 系统的触发器。当 suggestion 生成后，系统立即使用该 suggestion 作为假设的用户输入，预执行一轮 agent 响应。

**核心参数**（源码: `services/PromptSuggestion/speculation.ts#L58-70`）：

```typescript
const MAX_SPECULATION_TURNS = 20    // 最大推测轮数
const MAX_SPECULATION_MESSAGES = 100 // 最大消息数

// 允许在推测中执行的工具
const WRITE_TOOLS = new Set(['Edit', 'Write', 'NotebookEdit'])
const SAFE_READ_ONLY_TOOLS = new Set([
  'Read', 'Glob', 'Grep', 'ToolSearch', 'LSP', 'TaskGet', 'TaskList'
])
```

**文件隔离机制**（Copy-on-Write Overlay）：
- 推测执行在独立目录中进行：`$CLAUDE_TEMP_DIR/speculation/{pid}/{id}/`
- 写操作使用 Copy-on-Write：首次写入时将原文件复制到 overlay 目录，后续读写均重定向到 overlay
- CWD 外的写操作被拒绝
- 接受时：overlay 文件复制回主目录；中止时：overlay 直接删除

**边界检测**（`CompletionBoundary` 类型，源码: `state/AppStateStore.ts#L41-50`）：

| 边界类型 | 触发条件 | 行为 |
|----------|----------|------|
| `complete` | agent 自然完成 | 记录 outputTokens |
| `bash` | 非只读 Bash 命令 | 中止推测 |
| `edit` | 文件编辑但权限不足 | 中止推测 |
| `denied_tool` | 不在允许列表中的工具 | 中止推测 |

**Pipeline 机制**：推测执行完成后，如果用户尚未做出响应，会立即生成下一轮 suggestion（`generatePipelinedSuggestion`，源码: `speculation.ts#L345-400`）。当用户接受当前 suggestion 时，pipelined suggestion 被提升为新的 suggestion 显示，形成连续的预测-预执行链。

**启用条件**（源码: `speculation.ts#L337-343`）：

```typescript
export function isSpeculationEnabled(): boolean {
  const enabled =
    process.env.USER_TYPE === 'ant' &&
    (getGlobalConfig().speculationEnabled ?? true)
  return enabled
}
```

> **注意**：Speculation 仅对 Anthropic 内部用户启用（`USER_TYPE === 'ant'`），外部用户仅使用 Prompt Suggestions 文本预测功能。

#### 源码文件索引

| 文件 | 职责 |
|------|------|
| `services/PromptSuggestion/promptSuggestion.ts` | 核心服务：启用检查、生成、过滤、遥测（524 行） |
| `services/PromptSuggestion/speculation.ts` | 推测执行：overlay 隔离、边界检测、pipeline（992 行） |
| `hooks/usePromptSuggestion.ts` | React Hook：UI 状态管理、接受/显示/遥测（178 行） |
| `components/PromptInput/PromptInput.tsx` | 输入框组件：集成 suggestion 显示与 Enter 接受 |
| `components/PromptInput/useTypeahead.tsx` | Tab/→ 键接受与 ghost text 渲染 |
| `state/AppStateStore.ts#L385-393` | 状态定义：`promptSuggestion` + `speculation` + `speculationSessionTimeSavedMs` |
| `query/stopHooks.ts#L139` | 入口：在 stop hooks 中 fire-and-forget 调用 |
| `components/Settings/Config.tsx` | `/config` 菜单中的开关切换 |

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
```

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
