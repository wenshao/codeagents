# 10. Prompt Suggestions（下一步提示预测）

> 本文基于 Claude Code v2.1.89 源码分析（`services/PromptSuggestion/promptSuggestion.ts` 524 LOC + `services/PromptSuggestion/speculation.ts` 992 LOC + `hooks/usePromptSuggestion.ts` 178 LOC 等共 ~1,700 行），覆盖 suggestion 生成、过滤、交互、遥测和 Speculation 推测执行。
>
> **数据来源**：文中所有源码路径和行号均引用自 Claude Code 应用源码（非本仓库文件），通过反编译 SEA 二进制获得。源码行数基于 TypeScript 文件的 `wc -l` 统计。
>
> **功能内部代号**：`tengu_chomp_inflection`（GrowthBook feature flag 名称）。

## 功能概述

Claude Code 在每轮 assistant 回复完成后，自动预测用户下一步可能输入的内容，以蓝紫色提示文本显示在输入框中。用户可通过 Tab/Enter 接受，或直接输入覆盖。

## 架构概览

```
┌─────────────────────────────────────────────────────────────────┐
│  stopHooks.ts                                                   │
│  query/stopHooks.ts#L139                                        │
│  每轮 assistant 回复完成后触发                                   │
│  void executePromptSuggestion(stopHookContext)                  │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│  executePromptSuggestion()                                      │
│  services/PromptSuggestion/promptSuggestion.ts#L184             │
│  仅处理 querySource === 'repl_main_thread' 的主线程请求          │
│                                                                 │
│  1. tryGenerateSuggestion() — 守卫检查 + 生成 + 过滤             │
│  2. 写入 AppState.promptSuggestion                              │
│  3. 如果 Speculation 启用 → startSpeculation()                  │
└────────────────────┬────────────────────────────────────────────┘
                     │
              ┌──────┴──────┐
              ▼             ▼
┌──────────────────────┐  ┌──────────────────────────────────────┐
│ usePromptSuggestion  │  │ startSpeculation()                   │
│ hooks/               │  │ services/PromptSuggestion/           │
│ usePromptSuggestion  │  │ speculation.ts                       │
│ .ts                  │  │ 以 suggestion 为假设输入预执行 agent  │
│                      │  │ (仅限 Anthropic 内部用户启用)         │
│ 管理 UI 显示         │  └──────────────────────────────────────┘
│ Tab/Enter 接受       │
│ 遥测日志             │
└──────────────────────┘
```

## 生成流程

### 触发入口

每轮 assistant 回复完成后，在 stop hooks 阶段以 fire-and-forget 方式异步发起：

```typescript
// 源码: query/stopHooks.ts#L138-139
if (!isEnvDefinedFalsy(process.env.CLAUDE_CODE_ENABLE_PROMPT_SUGGESTION)) {
  void executePromptSuggestion(stopHookContext)
}
```

`--bare` 模式（最小化模式，跳过 hooks、LSP、插件同步等）和 `-p`（非交互管道模式）均跳过 suggestion 生成。

### API 调用方式

源码: `services/PromptSuggestion/promptSuggestion.ts#L294-352`

调用 `runForkedAgent()` 发起独立的 API 请求：

- **缓存复用**：复用主对话的 `cacheSafeParams`，刻意不覆盖任何 API 参数（不设 `effortValue`、`maxOutputTokens` 等），以确保命中主对话的 prompt cache
- **独立标记**：`querySource: "prompt_suggestion"`、`forkLabel: "prompt_suggestion"`
- **不写 transcript**：`skipTranscript: true, skipCacheWrite: true`
- **禁止工具**：所有工具调用通过 `canUseTool` 回调拒绝（`behavior: "deny"`），模型只能返回纯文本

> **历史教训**：据源码注释（`promptSuggestion.ts#L308-318`），Anthropic 内部曾尝试设置 `effort:'low'` 降低 suggestion 成本，结果导致 cache 命中率从 92.7% 暴跌至 61%（45x cache write spike）。billing cache key 包含的参数比文档描述的更多，任何差异都会 bust cache。

### Suggestion Prompt

源码: `services/PromptSuggestion/promptSuggestion.ts#L258-287`，常量 `SUGGESTION_PROMPT`

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

Prompt 通过 `PromptVariant` 类型索引（源码: `promptSuggestion.ts#L31-35`），当前仅有 `'user_intent'` 和 `'stated_intent'` 两个变体，均映射到同一模板。

## 过滤机制

源码: `services/PromptSuggestion/promptSuggestion.ts#L354-456`，函数 `shouldFilterSuggestion`

生成的 suggestion 经过 12 条过滤规则严格筛选，不满足条件的被静默丢弃：

| 过滤规则 | 说明 | 匹配示例 |
|----------|------|----------|
| `done` | 内容恰好为 "done" | `done` |
| `meta_text` | 模型输出元描述而非真实预测 | "nothing to suggest"、"silence"、"nothing found" |
| `meta_wrapped` | 被括号包裹的元推理 | `(silence — ...)`、`[no suggestion]` |
| `error_message` | API 错误信息泄漏 | "api error: ..."、"prompt is too long"、"image was too large" |
| `prefixed_label` | 带 `word: ` 标签前缀 | "Next step: run tests" |
| `too_few_words` | 少于 2 个单词（允许斜杠命令和特定单词） | 单个普通单词（非白名单词） |
| `too_many_words` | 超过 12 个单词 | 过长的句子 |
| `too_long` | ≥100 个字符 | — |
| `multiple_sentences` | 包含多个句子（`/[.!?]\s+[A-Z]/`） | "Do this. Then that." |
| `has_formatting` | 包含换行符或 Markdown 格式 | 含 `\n`、`*`、`**` |
| `evaluative` | 评价性/感谢语句 | "looks good"、"thanks"、"perfect"、"awesome" |
| `claude_voice` | 模型自身语气开头 | "Let me..."、"I'll..."、"Here's..."、"You should..." |

**单词白名单**（源码: `promptSuggestion.ts#L403-424`，即使只有 1 个单词也不过滤）：

| 类别 | 单词 |
|------|------|
| 肯定词 | yes, yeah, yep, yea, yup, sure, ok, okay |
| 动作词 | push, commit, deploy, stop, continue, check, exit, quit |
| 否定词 | no |

## 交互方式

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

## 状态数据结构

源码: `state/AppStateStore.ts#L385-393`

```typescript
promptSuggestion: {
  text: string | null           // suggestion 文本内容
  promptId: 'user_intent' | 'stated_intent' | null  // prompt 变体标识
  shownAt: number               // 首次渲染时间戳（用于计算 timeToAcceptMs）
  acceptedAt: number            // Tab 接受时间戳
  generationRequestId: string | null  // 关联的 API 请求 ID（用于 RL 数据集关联）
}
```

## 抑制条件（三层守卫）

### 初始化守卫

源码: `promptSuggestion.ts#L37-94`，函数 `shouldEnablePromptSuggestion`

| 检查顺序 | 条件 | 结果 |
|----------|------|------|
| 1 | 环境变量 `CLAUDE_CODE_ENABLE_PROMPT_SUGGESTION` 为 falsy | 禁用 |
| 2 | 环境变量 `CLAUDE_CODE_ENABLE_PROMPT_SUGGESTION` 为 truthy | 启用 |
| 3 | GrowthBook flag `tengu_chomp_inflection` 为 false | 禁用 |
| 4 | 非交互模式（`-p`、管道输入、SDK） | 禁用 |
| 5 | Swarm teammate（非 leader） | 禁用 |
| 6 | `settings.promptSuggestionEnabled !== false` | 按设置值 |

### 运行时守卫

源码: `promptSuggestion.ts#L107-119`，函数 `getSuggestionSuppressReason`

| 条件 | 抑制原因 |
|------|----------|
| `promptSuggestionEnabled === false` | `disabled` |
| 存在待审批的 Worker/Sandbox 权限请求 | `pending_permission` |
| MCP elicitation 队列非空 | `elicitation_active` |
| Plan mode 激活 | `plan_mode` |
| 外部用户且速率限制触发 | `rate_limit` |

### 生成前守卫

源码: `promptSuggestion.ts#L125-182`，函数 `tryGenerateSuggestion`

| 条件 | 抑制原因 |
|------|----------|
| AbortController 已中止 | `aborted` |
| assistant 回复不足 2 轮 | `early_conversation` |
| 上一条回复是 API 错误 | `last_response_error` |
| 上一条回复未缓存 token 数 > 10,000 | `cache_cold` |

## 配置方式

| 方式 | 说明 |
|------|------|
| `/config` → "Prompt suggestions" | 交互式配置菜单中切换开关 |
| `settings.json` 中设置 `"promptSuggestionEnabled": false` | 持久化关闭 |
| 环境变量 `CLAUDE_CODE_ENABLE_PROMPT_SUGGESTION=0` | 强制关闭（优先级最高） |
| 环境变量 `CLAUDE_CODE_ENABLE_PROMPT_SUGGESTION=1` | 强制开启（优先级最高） |
| GrowthBook feature flag `tengu_chomp_inflection` | 服务端灰度发布控制 |

## UI 样式

suggestion 文本使用主题中的 `suggestion` 颜色渲染：

| 主题 | 颜色 |
|------|------|
| Light | `rgb(87, 105, 247)`（蓝紫色） |
| Dark | `rgb(177, 185, 249)`（浅蓝紫色） |
| ANSI Light | `ansi:blue` |
| ANSI Dark | `ansi:blueBright` |

## 遥测事件

### 初始化事件

事件名: `tengu_prompt_suggestion_init`（源码: `promptSuggestion.ts#L41-92`）

| 字段 | 说明 |
|------|------|
| `enabled` | 是否启用 |
| `source` | 决策来源：`env` / `growthbook` / `non_interactive` / `swarm_teammate` / `setting` |

### 结果事件

事件名: `tengu_prompt_suggestion`（源码: `hooks/usePromptSuggestion.ts#L120-157`、`promptSuggestion.ts#L462-523`）

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

## Speculation（推测执行）

Prompt Suggestions 是更深层 **Speculation** 系统的触发器。当 suggestion 生成后，系统立即使用该 suggestion 作为假设的用户输入，预执行一轮 agent 响应。

### 启用条件

源码: `speculation.ts#L337-343`

```typescript
export function isSpeculationEnabled(): boolean {
  const enabled =
    process.env.USER_TYPE === 'ant' &&
    (getGlobalConfig().speculationEnabled ?? true)
  return enabled
}
```

> **注意**：Speculation 仅对 Anthropic 内部用户启用（`USER_TYPE === 'ant'`），外部用户仅使用 Prompt Suggestions 文本预测功能。

### 核心参数

源码: `services/PromptSuggestion/speculation.ts#L58-70`

```typescript
const MAX_SPECULATION_TURNS = 20    // 最大推测轮数
const MAX_SPECULATION_MESSAGES = 100 // 最大消息数

// 允许在推测中执行的工具
const WRITE_TOOLS = new Set(['Edit', 'Write', 'NotebookEdit'])
const SAFE_READ_ONLY_TOOLS = new Set([
  'Read', 'Glob', 'Grep', 'ToolSearch', 'LSP', 'TaskGet', 'TaskList'
])
```

### 文件隔离机制（Copy-on-Write Overlay）

源码: `speculation.ts#L80-81, #L402-715`

- 推测执行在独立目录中进行：`$CLAUDE_TEMP_DIR/speculation/{pid}/{id}/`
- 写操作使用 Copy-on-Write：首次写入时将原文件复制到 overlay 目录，后续读写均重定向到 overlay
- CWD 外的写操作被拒绝
- 接受时：overlay 文件复制回主目录（`copyOverlayToMain`）；中止时：overlay 直接删除（`safeRemoveOverlay`）

### 边界检测

`CompletionBoundary` 类型（源码: `state/AppStateStore.ts#L41-50`）：

| 边界类型 | 触发条件 | 行为 |
|----------|----------|------|
| `complete` | agent 自然完成 | 记录 `outputTokens` |
| `bash` | 非只读 Bash 命令 | 中止推测 |
| `edit` | 文件编辑但权限不足（非 `acceptEdits`/`bypassPermissions` 模式） | 中止推测 |
| `denied_tool` | 不在允许列表中的工具 | 中止推测 |

### Pipeline 机制

源码: `speculation.ts#L345-400`，函数 `generatePipelinedSuggestion`

推测执行完成后，如果用户尚未做出响应，会立即生成下一轮 suggestion。当用户接受当前 suggestion 时，pipelined suggestion 被提升为新的 suggestion 显示，并启动新一轮 speculation，形成连续的预测→预执行→预测链。

```
用户发送消息 → Claude 回复
  → 生成 suggestion A → 开始 speculation A
    → speculation A 完成 → 生成 pipelined suggestion B
      → 用户接受 A → 提升 B 为当前 suggestion → 开始 speculation B
        → ...
```

## 源码文件索引

| 文件 | LOC | 职责 |
|------|-----|------|
| `services/PromptSuggestion/promptSuggestion.ts` | 524 | 核心服务：启用检查、生成、过滤、遥测 |
| `services/PromptSuggestion/speculation.ts` | 992 | 推测执行：overlay 隔离、边界检测、pipeline |
| `hooks/usePromptSuggestion.ts` | 178 | React Hook：UI 状态管理、接受/显示/遥测 |
| `components/PromptInput/PromptInput.tsx` | — | 输入框组件：集成 suggestion 显示与 Enter 接受 |
| `components/PromptInput/useTypeahead.tsx` | — | Tab/→ 键接受与 ghost text 渲染 |
| `state/AppStateStore.ts` | — | 状态定义：`promptSuggestion` + `speculation` + `speculationSessionTimeSavedMs` |
| `query/stopHooks.ts` | — | 入口：在 stop hooks 中 fire-and-forget 调用 |
| `components/Settings/Config.tsx` | — | `/config` 菜单中的开关切换 |
