# Fast Model 应用场景 Deep-Dive——Claude Code 的 18 处用法 + Qwen Code 借鉴路径

> **核心问题**：除了 Recap 和 follow-up suggestions，Claude Code 还用 fast model（Haiku）做哪些事？哪些值得 Qwen Code 借鉴？
>
> 返回 [Qwen Code 改进建议总览](./qwen-code-improvement-report.md)

## 一、Claude Code 的 18 处 fast-model 调用

基于 `/root/git/claude-code-leaked/` 源码全量搜索 `getSmallFastModel()` + `queryHaiku()` 调用点。每条都给出**触发时机 / 用户视角 / 为什么用 fast model / 源码位置**四要素，方便学习模仿。

---

### 1.1 会话元信息生成（3 处）

#### ① 会话标题自动生成

- 🎯 **触发时机**：任意 session 结束/保存时后台异步生成；`/resume` 列表打开前也会触发
- 👁️ **用户视角**：`/resume` 列表从 `abc123 · 2h ago` → `Fix login button on mobile · 2h ago`——可以从长列表中扫读找回目标 session
- 💡 **为什么 fast model**：摘要任务（输入 → 3-7 词标题），无需推理深度；JSON schema 强制 `{ title: string }` 避免冗余解释
- 📝 **Prompt 精髓**：`"Generate a concise, sentence-case title (3-7 words) ... git-commit-subject"`，附 4 good + 3 bad 示例（太模糊/太长/错误大小写）
- 📂 **源码**：`utils/sessionTitle.ts:56-100`，`MAX_CONVERSATION_TEXT = 1000` tail-slice 对话末尾

#### ② `/rename` 命令生成会话名

- 🎯 **触发时机**：用户在 session 中输入 `/rename`，或从 Web/桌面 app 端选择 "rename this session"
- 👁️ **用户视角**：当前 session 文件名从 `session-uuid.jsonl` → `fix-login-button-mobile.jsonl`（kebab-case，可在 OS 文件管理器中辨识）
- 💡 **为什么 fast model**：与①类似的短摘要任务；kebab-case 格式约束简单
- 📝 **区别于①**：kebab-case 输出（文件系统安全）而非 sentence-case
- 📂 **源码**：`commands/rename/generateSessionName.ts:20`（遗留实现，新调用应走 `sessionTitle.ts` 的统一入口）

#### ③ Session Recap（"while you were away" card）

- 🎯 **触发时机**：失焦 ≥5 分钟（DECSET 1004 焦点协议）+ 当前无 turn + 上次 user turn 后无 recap；或用户 `/recap` 手动
- 👁️ **用户视角**：回到终端时输入框上方显示 dim color 1-3 句 `"You were refactoring the auth middleware to use OAuth2. Next: implement the token refresh endpoint."`
- 💡 **为什么 fast model**：1-3 句话生成成本低；Prompt 显式禁止 "status reports" / "commit recaps" 避免 Haiku 模板化输出
- 📝 **Prompt 精髓**：`"The user stepped away and is coming back. Write exactly 1-3 short sentences. Start by stating the high-level task ... Skip status reports and commit recaps."`
- 📂 **源码**：`services/awaySummary.ts`，`RECENT_MESSAGE_WINDOW = 30` 限制输入

**共性**：都是**从对话抽取/压缩为短文本**，JSON schema 强制输出格式，tail-slice 限制输入长度，示例引导输出风格。

---

### 1.2 语义搜索（2 处）

#### ④ `/resume` 会话检索（Agentic Search）

- 🎯 **触发时机**：用户输入 `/resume <query>`，如 `/resume "auth bug"` 或 `/resume "yesterday's refactor"`
- 👁️ **用户视角**：输入自然语言 query，系统返回最相关的 N 个 session（按相关性排序），而非按时间
- 💡 **为什么 fast model**：对 M 个 session 元数据（title + first prompt + transcript excerpt）做语义匹配——**M 可能达几百**，用 Sonnet 每次查询成本过高
- 📝 **Prompt 结构**：
  ```
  Sessions:
  - session_1: First message: "..." Transcript: "..."
  - session_2: ...
  Search query: "{用户 query}"
  Find the sessions that are most relevant to this query.
  ```
- 📂 **源码**：`utils/agenticSessionSearch.ts:248-270`，`sideQuery` 调用而非主循环

#### ⑤ Web 搜索工具（Haiku 变体）

- 🎯 **触发时机**：feature flag `tengu_plum_vx3` 启用时，WebSearch tool 调用走 Haiku 而非主模型
- 👁️ **用户视角**：对用户透明——主模型调用 `WebSearch` tool → 内部转给 Haiku 生成精确 query、选择候选 → 返回结果给主模型
- 💡 **为什么 fast model**：**"生成搜索 query + 筛选结果"本身就是 LLM 元任务**，用 Haiku 节省 token；主模型专注于 "基于结果回答"
- 📝 **设计点**：`toolChoice: { type: 'tool', name: 'web_search' }` 强制走 tool；`thinkingConfig: disabled` 避免 Haiku 浪费 thinking token
- 📂 **源码**：`tools/WebSearchTool/WebSearchTool.ts:262-290`，`useHaiku` 由 feature flag 决定

**核心洞察**：**语义搜索 = Haiku 大规模元数据筛选 + Sonnet 少量内容理解**，是经典的"分级推理"模式。

---

### 1.3 Hook LLM 评估（3 处）

#### ⑥ Prompt Hook 条件判断

- 🎯 **触发时机**：用户定义了 `hooks.if.condition: "<自然语言>"` 的 hook，每次 hook 事件（PreToolUse/UserPromptSubmit 等）触发时评估
- 👁️ **用户视角**：用户写 `hooks.yaml`：
  ```yaml
  - event: PreToolUse
    if:
      condition: "The user is trying to delete production data"
      model: haiku
    run: { deny: true, message: "Production data deletion requires manual approval" }
  ```
  非程序员也能定义精准 hook
- 💡 **为什么 fast model**：Hook 条件评估是**高频调用**（每个工具调用都可能触发），低延迟低成本至关重要
- 📝 **Prompt 约束**：JSON schema `{ok: bool, reason?: string}`——`ok: false` 时可选 reason 写入 audit log
- 📂 **源码**：`utils/hooks/execPromptHook.ts:62-99`

#### ⑦ Agent Hook stop condition 验证

- 🎯 **触发时机**：Agent 声明完成（`SubagentStop` event），但用户定义了 stop condition verification hook
- 👁️ **用户视角**：Agent 说"完成了实现 X 功能"——hook 启动一个**独立的 Haiku agent**（最多 50 turns + 工具访问）去**真的验证**：read 代码、跑 test、grep 关键词，确认后才允许主 agent 退出
- 💡 **为什么 fast model**：验证过程可能需要多次 tool use，Sonnet 成本过高；Haiku 足以完成验证类任务
- 📝 **关键约束**：独立 `agentId`（`hook-agent-${randomUUID()}`）避免与主 agent 状态混淆；`MAX_AGENT_TURNS = 50` 硬上限
- 📂 **源码**：`utils/hooks/execAgentHook.ts:100-130`

#### ⑧ Skill 改进建议（post-sampling hook）

- 🎯 **触发时机**：feature flag `tengu_copper_panda` 启用时，每次 assistant message 完成后触发
- 👁️ **用户视角**：用户不主动感知；后台 Haiku 分析 "这个 skill 的本次表现，有没有值得改进的 prompt 片段"，结果暂存到 `appState.skillImprovement`，用户可在 `/skills --review` 中查看建议并决定应用
- 💡 **为什么 fast model**：持续后台任务，成本敏感；风险：LLM 建议可能不准确，必须 opt-in + 人工审核
- 📂 **源码**：`utils/hooks/skillImprovement.ts:155-182`

**共性**：都把"判断/验证"从主循环剥离给 Haiku，主循环保持纯净（Sonnet 专注 reasoning + tool use）。

---

### 1.4 内容处理/转换（5 处）

#### ⑨ WebFetch HTML 内容清洗

- 🎯 **触发时机**：`WebFetch(url, prompt)` 返回的 HTML/Markdown 过大（navigation / ads / tracking script 占多数）
- 👁️ **用户视角**：Agent 调用 `WebFetch("https://docs.stripe.com/...")` 后，只看到核心文档而非整页 HTML，回答质量提升
- 💡 **为什么 fast model**：内容清洗是纯"信号 vs 噪音"分类，不需要 reasoning；大文档 → 核心内容 = token 压缩 70%+
- 📂 **源码**：`tools/WebFetchTool/utils.ts:503`

#### ⑩ 工具调用摘要生成（compact mode / SDK progress）

- 🎯 **触发时机**：compact view（subagent 视图、移动端行显示）需要把 N 个并行 tool calls 折叠为一行
- 👁️ **用户视角**：主 agent 看 subagent 的进度时，不再是 `Read × 5 + Grep × 3 + Bash × 2` 列表，而是 `"Debugged auth middleware"` 30 字符 label
- 💡 **为什么 fast model**：30 字符输出量极小；移动端 SDK 客户端需要低延迟进度推送
- 📝 **Prompt 精髓（git-commit-subject 风格）**：
  ```
  think git-commit-subject, not sentence.
  Keep the verb in past tense and the most distinctive noun.
  Drop articles, connectors, and long location context first.
  
  Examples:
  - Searched in auth/
  - Fixed NPE in UserService
  ```
- 📂 **源码**：`services/toolUseSummary/toolUseSummaryGenerator.ts:15-85`

#### ⑪ Shell 命令前缀提取（权限分类 · 安全关键）

- 🎯 **触发时机**：每次 Shell 工具执行前，需要对照权限规则判断"这个命令属于哪个类别"
- 👁️ **用户视角**：用户定义 `allow: ["git commit", "npm install"]`——系统需要正确识别 `git commit -m "fix" && rm -rf /` 中的**两个前缀**，而不是错判为仅 `git commit`
- 💡 **为什么 fast model**：安全关键路径——regex 的边界错误（alias / subshell / backtick / pipe）可能导致权限绕过；Haiku + policy spec 更鲁棒
- 📝 **高级优化**：feature flag `tengu_cork_m4q` 控制是否把 `policySpec` 放 **system prompt 走 prompt caching**（后续所有 Shell 命令复用同一缓存）；10 秒超时告警
- 📂 **源码**：`utils/shell/prefix.ts:215-245`

#### ⑫ MCP 日期时间解析（`@date` 表达式）

- 🎯 **触发时机**：MCP tool 参数中出现自然语言日期表达式，如 `@tomorrow 3pm` / `@next monday` / `@2 hours ago`
- 👁️ **用户视角**：MCP 工具（如 calendar/issue tracker）无需教用户 ISO 8601 格式，直接写 `reminder_at: "@tomorrow 3pm"` 即可
- 💡 **为什么 fast model**：解析是纯 pattern matching 任务；`INVALID` 字面量返回值让调用方明确错误处理
- 📝 **Prompt 注入 context**：当前 UTC 时间 + 本地时区 + 星期几（让 Haiku 能正确处理 "next monday" 这类相对表达）
- 📂 **源码**：`utils/mcp/dateTimeParser.ts:55-80`

#### ⑬ `/bug` 反馈标题生成

- 🎯 **触发时机**：用户输入 `/bug`，触发 bug report 提交流程，生成 GitHub issue 标题
- 👁️ **用户视角**：用户只需描述 bug 现象，系统自动生成 `"[Bug] Auto-Compact triggers too soon"` 规范化标题，直接用于 GitHub issue URL
- 💡 **为什么 fast model**：80 字符标题，短输出；提取 key error 而非整条消息（"Missing Tool Result Block" 而非完整 stack trace）
- 📝 **风格约束**：`[Bug]` / `[Feature Request]` 前缀；技术术语；不含任何 "commentary or explanation"（直接用作 issue 标题）
- 📂 **源码**：`components/Feedback.tsx:447-462`

**共性**：都是**输入大 → 输出小**的压缩/结构化任务，zero reasoning 需求，用 Sonnet 属于"杀鸡用牛刀"。

---

### 1.5 系统级查询（3 处）

#### ⑭ Token 计数 API

- 🎯 **触发时机**：每次 prompt 组装前需要估算 token 数（判断是否超上限、是否触发 compact）
- 👁️ **用户视角**：context meter `/context` 显示的百分比，依赖频繁调用 token counting API
- 💡 **为什么 fast model**：**count_tokens endpoint 不产生完整回答，仅返回 token 数**——用 Haiku endpoint 节省路由成本
- 📝 **Fallback 逻辑**：Vertex global endpoint（Haiku 不可用）/ Bedrock with thinking（Haiku 3.5 不支持 thinking）/ Vertex with thinking 时自动 fallback 到 Sonnet
- 📂 **源码**：`services/tokenEstimation.ts:255-290`

#### ⑮ Quota 配额检查（1-token 测试请求）

- 🎯 **触发时机**：系统定期（或启动时）检查用户 Claude.ai 订阅配额状态
- 👁️ **用户视角**：看到 `/status` 中显示 "12% of quota used this session"——背后是定期发送的 1-token 测试请求
- 💡 **为什么 fast model + `max_tokens: 1`**：这是**纯连通性测试**，不需要实际输出；Haiku + 1 token 成本最低
- 📂 **源码**：`services/claudeAiLimits.ts:199-218`

#### ⑯ API key 验证（启动时）

- 🎯 **触发时机**：交互式启动时（`isNonInteractiveSession: false`），需要验证 API key 是否有效、可访问哪些模型
- 👁️ **用户视角**：启动时的 "Connecting..." 阶段——失败时明确报错而非在用户输入第一句话时才失败
- 💡 **为什么 fast model**：仅需一次握手验证；非交互式模式（`--print`）跳过以加速 CI/CD 启动
- 📂 **源码**：`services/api/claude.ts:534-550`

**共性**：都是**系统侧的 probe/validation**，对用户透明，Haiku 是成本/延迟最优解。

---

### 1.6 实用功能 + 基础设施（2 处）

#### ⑰ `/teleport` 跨设备会话迁移（CCR）

- 🎯 **触发时机**：用户在设备 A 用 `/teleport` 命令，把当前 session 转移到设备 B（Claude Code Router）
- 👁️ **用户视角**：打包当前 session → 生成 `title + branchName` 元数据 → 推送到 CCR → 设备 B 接收时看到 `Fix login button mobile` 标题 + `claude/fix-login` 分支名
- 💡 **为什么 fast model**：`title + branchName` 两个字段都是短文本生成，JSON schema 约束输出
- 📝 **与①②的区别**：`/teleport` 一次生成**两个字段**（title + branch name），`/rename` 只生成一个
- 📂 **源码**：`utils/teleport.tsx:97-120`，`generateTitleAndBranch()`

#### ⑱ `queryHaiku()` 通用 wrapper（基础设施）

- 🎯 **触发时机**：上面 ①②③⑨⑩⑪⑫⑬⑰ 等多数场景的底层入口
- 💡 **为什么独立**：统一 6 条默认约束（thinking disabled / tools [] / 非流式 / prompt caching 可选 / JSON schema 可选 / VCR 录制支持）
- 📂 **源码**：`services/api/claude.ts:3241-3290`

```typescript
// queryHaiku 最小使用示例：
const result = await queryHaiku({
  systemPrompt: asSystemPrompt([SYSTEM_PROMPT_STRING]),
  userPrompt: USER_INPUT,
  outputFormat: { type: 'json_schema', schema: {...} },  // 可选
  signal: abortSignal,
  options: {
    querySource: 'your_use_case_tag',  // 遥测用
    enablePromptCaching: false,         // 默认 false，显式设 true 才启用
    agents: [],
    isNonInteractiveSession: false,
    hasAppendSystemPrompt: false,
    mcpTools: [],
  }
})
```

**18 处的统一模式**：`queryHaiku()` wrapper + system prompt（定义任务 + 格式约束 + 示例）+ user prompt（实际输入，常带 tail-slice/truncate）+ JSON schema（确定性输出）。

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
