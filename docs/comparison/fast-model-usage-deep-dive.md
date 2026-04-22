# Fast Model 应用场景 Deep-Dive——Claude Code 的 18 处用法 + Qwen Code 借鉴路径

> **核心问题**：除了 Recap 和 follow-up suggestions，Claude Code 还用 fast model（Haiku）做哪些事？哪些值得 Qwen Code 借鉴？
>
> 返回 [Qwen Code 改进建议总览](./qwen-code-improvement-report.md)

## 一、Claude Code 的 18 处 fast-model 调用

基于 `/root/git/claude-code-leaked/` 源码全量搜索 `getSmallFastModel()` + `queryHaiku()` 调用点。

### 1.1 会话元信息生成（3 处）

| # | 用途 | 源码 | Prompt 精髓 |
|---|---|---|---|
| 1 | **会话标题自动生成** | `utils/sessionTitle.ts:87` | "Generate a concise, sentence-case title (3-7 words) ... **git-commit-subject**" |
| 2 | `/rename` 命令生成会话名 | `commands/rename/generateSessionName.ts:20` | kebab-case name for session |
| 3 | **Session Recap** | `services/awaySummary.ts` | "stepped away and is coming back ... 1-3 short sentences ... skip status reports" |

**共性**：JSON schema 强制输出格式（`{ title: string }`），短 prompt + 短输出，强 example 引导（good/bad 各 4 例）。

### 1.2 语义搜索（2 处）

| # | 用途 | 源码 |
|---|---|---|
| 4 | **`/resume` 会话检索** — 基于历史对话语义匹配当前查询 | `utils/agenticSessionSearch.ts:261` |
| 5 | **Web 搜索工具** (feature-gated `tengu_plum_vx3`) | `tools/WebSearchTool/WebSearchTool.ts:280` |

**设计点**：Web 搜索走 Haiku 变体时 `toolChoice: { type: 'tool', name: 'web_search' }` 强制走 tool，`thinkingConfig: disabled` 避免 Haiku 浪费 thinking token。

### 1.3 Hook LLM 评估（3 处）

| # | 用途 | 源码 | 特点 |
|---|---|---|---|
| 6 | **Prompt Hook 条件判断** | `utils/hooks/execPromptHook.ts:79` | JSON schema `{ ok: bool, reason?: string }` |
| 7 | **Agent Hook stop condition 验证** | `utils/hooks/execAgentHook.ts:118` | 支持**工具调用**（检查 codebase），最多 50 turns，独立 `agentId` |
| 8 | **Skill 改进建议** (feature-gated `tengu_copper_panda`) | `utils/hooks/skillImprovement.ts:169, 241` | post-sampling hook，分析刚完成的 assistant message，建议修订 skill |

**价值**：让用户用自然语言（而非脚本）定义 hook 条件——例如 `if.condition: "user is discussing security issues"` 交给 Haiku 判断。

### 1.4 内容处理/转换（5 处）

| # | 用途 | 源码 | 输入 → 输出 |
|---|---|---|---|
| 9 | **WebFetch HTML 处理** | `tools/WebFetchTool/utils.ts:503` | HTML → prompt-consumable 内容 |
| 10 | **工具调用摘要生成** | `services/toolUseSummary/toolUseSummaryGenerator.ts:69` | N 个 tool calls → "**30 字符**" git-commit-subject 风格 label（移动端行显示用）|
| 11 | **Shell 命令前缀提取**（权限分类）| `utils/shell/prefix.ts:220` | `git commit -m "fix"` → `git commit` 前缀，供权限规则匹配 |
| 12 | **MCP 日期时间解析** | `utils/mcp/dateTimeParser.ts:68` | `@tomorrow 3pm` → ISO 8601 |
| 13 | **`/bug` 反馈内容处理** | `components/Feedback.tsx:449` | 对话内容 → 结构化反馈 |

**`prefix.ts:220` 的精妙之处**：Shell 权限分类是安全关键路径，用 Haiku + `policySpec` 精确提取命令前缀，避免 regex 的边界错误（如 `git commit && rm -rf /` 的解析）。Feature-gated `tengu_cork_m4q` 控制是否把 policy spec 放 system prompt 走 prompt caching（10 秒超时告警）。

### 1.5 系统级查询（3 处）

| # | 用途 | 源码 | 场景 |
|---|---|---|---|
| 14 | **Token 计数** | `services/tokenEstimation.ts:277` | 用 Haiku `count_tokens` API（而非 Sonnet）节省成本；Vertex global / Bedrock with thinking 时 fallback 到 Sonnet |
| 15 | **Quota 配额检查** | `services/claudeAiLimits.ts:200` | 1-token 测试请求，`max_tokens: 1` |
| 16 | **API key 验证**（交互式启动时）| `services/api/claude.ts:541` | `isNonInteractiveSession` 跳过 |

### 1.6 实用功能（2 处）

| # | 用途 | 源码 |
|---|---|---|
| 17 | **`/teleport` 跨设备会话迁移** | `utils/teleport.tsx:107` |
| 18 | `queryHaiku()` 通用 wrapper | `services/api/claude.ts:3241-3290` |

---

## 二、Claude Code 的 fast-model 调用设计模式

**所有调用共享的约定**：

```typescript
await queryModelWithoutStreaming({
  // ...
  thinkingConfig: { type: 'disabled' },   // ❶ 禁用 thinking
  tools: [],                              // ❷ 禁用 tool use（多数情况）
  options: {
    model: getSmallFastModel(),           // ❸ 尊重 ANTHROPIC_SMALL_FAST_MODEL env var
    enablePromptCaching: false,           // ❹ 一次性查询不污染 cache
    outputFormat: { type: 'json_schema' } // ❺ 可选：强制结构化输出
  }
})
```

**6 条共同哲学**：

1. **禁用 thinking**——摘要/分类/判断类任务不需要扩展推理
2. **禁用 tools**——纯文本生成，避免 tool use 循环
3. **非流式**——`queryModelWithoutStreaming`，减少 UI 渲染开销
4. **JSON schema 约束**（Hook / title 类）——减少解析失败
5. **Env var 兜底**——`ANTHROPIC_SMALL_FAST_MODEL` 允许 Bedrock/Vertex 自选模型
6. **Fallback 到 Sonnet**（`tokenEstimation.ts:274-277`）——Vertex global endpoint / Bedrock with thinking 场景 Haiku 不可用时回退

---

## 三、Qwen Code 现状

**Qwen Code 已有 fastModel 基础设施**：[PR#3120](https://github.com/QwenLM/qwen-code/pull/3120)（已合并）引入了 `fastModel` 配置。搜索 `grep -rn "fastModel\|smallFastModel" /root/git/qwen-code/packages/` 得到以下调用点：

| 调用点 | 用途 |
|---|---|
| `packages/core/src/config/config.ts` | 配置定义 |
| 若干 Skill / Hook 内部（2026-04-16 PR#3087 Auto-Memory / Auto-Dream）| 后台记忆管理 |
| `services/sessionSummary`（相关，估算）| Session summary 生成 |

**对比 Claude Code 的 18 处用法，Qwen Code 的实际调用集中在 3-5 处**（记忆/摘要相关）。**6 类方向是明确的 gap**。

---

## 四、Qwen Code 借鉴优先级（按 ROI 排序）

### 🥇 优先级 1：会话标题自动生成

**Claude 实现**（`utils/sessionTitle.ts:56-100`）：

```typescript
const SESSION_TITLE_PROMPT = `Generate a concise, sentence-case title (3-7 words)...`

const result = await queryHaiku({
  systemPrompt: asSystemPrompt([SESSION_TITLE_PROMPT]),
  userPrompt: extractConversationText(messages).slice(-1000),
  outputFormat: {
    type: 'json_schema',
    schema: { type: 'object', properties: { title: { type: 'string' } }, required: ['title'] }
  }
})
```

**精妙细节**：
- `MAX_CONVERSATION_TEXT = 1000` 字符 tail-slice——长对话只看最近 1000 字符
- Prompt 给 4 个 good example + 3 个 bad example（太模糊 / 太长 / 错误大小写）
- `extractConversationText()` 过滤掉 meta 消息和非 human origin

**Qwen Code 借鉴路径**：
- 新建 `packages/core/src/services/sessionTitle.ts`
- 从 session 第一条 user message + 最近对话抽取 prompt
- 在 `/resume` 列表 UI 中展示生成的 title
- 存储在 session metadata 中（next time open 直接读）

**成本**：~1-1.5 天，~120 行

---

### 🥇 优先级 2：工具调用摘要生成（compact mode / SDK 进度）

**Claude 实现**（`services/toolUseSummary/toolUseSummaryGenerator.ts:69`）：

```typescript
const TOOL_USE_SUMMARY_SYSTEM_PROMPT = `Write a short summary label describing
what these tool calls accomplished. It appears as a single-line row in a
mobile app and truncates around 30 characters, so think git-commit-subject,
not sentence.

Keep the verb in past tense and the most distinctive noun.
Drop articles, connectors, and long location context first.

Examples:
- Searched in auth/
- Fixed NPE in UserService
- Created signup endpoint
- Read config.json
- Ran failing tests`
```

**用途**：
- compact mode 下一批 N 个并行 tool calls 折叠为一行 "Fixed NPE in UserService"
- SDK 客户端（手机 app 等）进度展示

**Qwen Code 借鉴路径**：
- 新建 `packages/core/src/services/toolUseSummary.ts`
- 输入 `ToolCall[]`（含 name / input / output 摘要）
- 输出 30 字符标签
- 接入已有的 ToolGroupMessage 或 compact mode UI

**成本**：~1 天，~100 行

---

### 🥈 优先级 3：Hook LLM 条件评估

**Claude 实现**：允许 hook 定义 `if.condition: "..."` 自然语言条件，LLM 判断是否触发。

```typescript
// execPromptHook.ts:79
const response = await queryModelWithoutStreaming({
  systemPrompt: `You are evaluating a hook in Claude Code.
Your response must be a JSON object matching one of:
1. {"ok": true}
2. {"ok": false, "reason": "..."}`,
  options: {
    model: hook.model ?? getSmallFastModel(),
    outputFormat: { type: 'json_schema', schema: { ... { ok: 'boolean', reason: 'string' } } }
  }
})
```

**Qwen Code 借鉴路径**：
- Qwen 的 HTTP/Function/Async Hook 系统已经很强（item-14 已追踪），增加**"LLM 评估" hook 类型**
- schema 例：
  ```yaml
  hooks:
    - event: PreToolUse
      if:
        condition: "User is asking about production database"
        model: haiku  # 可选，默认 fastModel
      run: { deny: true }
  ```
- 实现：在 Hook runner 加 `if.condition` 分支，调用 fastModel 获取 `{ok, reason}`

**成本**：~2 天，~200 行

---

### 🥈 优先级 4：WebFetch 内容处理

**Claude 实现**（`tools/WebFetchTool/utils.ts:503`）：HTML → prompt-consumable 内容（去掉 navigation / ads / script，保留核心内容 + 关键 metadata）

**Qwen Code 现状**：WebFetch 目前直接截断或用简单 HTML parser

**借鉴路径**：
- 在 `packages/core/src/tools/web-fetch.ts` 增加"LLM 内容清洗"步骤
- 大文档（>5K chars）走 fastModel 抽取关键内容
- 小文档直接返回

**成本**：~1.5 天，~150 行

---

### 🥉 优先级 5：Shell 命令前缀 LLM 提取（权限分类）

**Claude 实现**（`utils/shell/prefix.ts:220`）：

```typescript
const response = await queryHaiku({
  systemPrompt: `Your task is to process ${toolName} commands...
This policy spec defines how to determine the prefix of a ${toolName} command:`,
  userPrompt: `${policySpec}\n\nCommand: ${command}`,
  options: { enablePromptCaching: true, ... }
})
```

**为什么用 LLM 而非 regex**：
- `git commit && rm -rf /` 这种复合命令正确切分
- Shell alias / subshell / backtick 等边界情况
- 安全关键路径，regex 的边界错误=安全漏洞

**Qwen Code 现状**：当前 shell 权限走 regex / 硬编码 prefix 列表

**借鉴路径**：
- 在权限检查路径加 fastModel 前缀提取
- Feature flag 控制（默认关，有完整 test suite 后再默认开）

**成本**：~2 天 + 大量测试，~200 行

---

### 🥉 优先级 6：Skill 改进建议（post-sampling hook）

**Claude 实现**（`utils/hooks/skillImprovement.ts`）：每次 assistant message 完成后，feature-gated 调用 Haiku 分析"这个 skill 是否可以改进"。

**Qwen Code 借鉴路径**：
- Qwen Skill 系统（`skills/bundled/`）可加同类 hook
- 对 `tengu_copper_panda` gate 保持谨慎——默认关闭，让用户 opt-in

**成本**：~1.5 天，~150 行

---

## 五、实施路线图

| 阶段 | 周期 | 方向 | 累计成本 |
|-----|------|------|---------|
| **阶段 1**（立即可做，高可见度）| 第 1 周 | 会话标题 + 工具调用摘要 | 2-3 天 |
| **阶段 2**（能力扩展）| 第 2-3 周 | Hook LLM 评估 + WebFetch 内容处理 | 5-7 天 |
| **阶段 3**（高风险/高 ROI）| 第 4-5 周 | Shell 前缀权限 + Skill 改进 | 4-5 天 |

**总投入 ~12-15 天**，覆盖 Claude Code 18 处 fast-model 用法中最有用户价值的 6 处。

---

## 六、相关追踪 item

| item | 覆盖范围 |
|------|---------|
| [p2-stability item-43](./qwen-code-improvement-report-p2-stability.md#item-43) | Session Recap（✓ PR#3434 已合并）|
| [p2-stability item-50](./qwen-code-improvement-report-p2-stability.md#item-50)（本次新增）| 会话标题自动生成 |
| [p2-stability item-51](./qwen-code-improvement-report-p2-stability.md#item-51)（本次新增）| 工具调用摘要生成 |
| [p2-stability item-52](./qwen-code-improvement-report-p2-stability.md#item-52)（本次新增）| Hook LLM 条件评估 |
| [p2-stability item-53](./qwen-code-improvement-report-p2-stability.md#item-53)（本次新增）| WebFetch 内容处理 |
| [p2-stability item-54](./qwen-code-improvement-report-p2-stability.md#item-54)（本次新增）| Shell 命令前缀 LLM 提取 |
| [p2-stability item-55](./qwen-code-improvement-report-p2-stability.md#item-55)（本次新增）| Skill 改进建议 |
