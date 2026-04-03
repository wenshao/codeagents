# Qwen Code 改进建议 — P0/P1 详细说明

> 最高优先级改进项的 Claude Code 实现机制、Qwen Code 现状、缺失后果、改进收益和建议方案。
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md)

<a id="item-1"></a>

### 1. 多层上下文压缩 (Context Compression) 策略（P0）

**Claude Code 实现**：
- `services/compact/microCompact.ts` — turn 级微压缩，移除冗余工具结果
- `services/compact/autoCompact.ts` — 基于 token 阈值的自动压缩
- `services/compact/apiMicrocompact.ts` — API 原生上下文管理（`clear_tool_uses` / `clear_thinking`）
- `services/compact/sessionMemoryCompact.ts` — 基于会话记忆 (Memory) 的压缩，保留关键上下文
- `services/compact/postCompactCleanup.ts` — 压缩后清理
- `services/compact/grouping.ts` — 消息分组优化

**源码引用**：
- 源码: `services/compact/autoCompact.ts`
- 源码: `services/compact/sessionMemoryCompact.ts`
- 源码: `services/compact/compact.ts`（1705 行）

**Qwen Code 现状**：
- 源码: `packages/core/src/services/chatCompressionService.ts`（369 行），基于固定 token 阈值（70%）的单一压缩策略
- 无 micro-compact、无 memory-aware compact、无 API 原生上下文管理

**缺失后果**：
- 长会话中工具结果（大文件内容、长命令输出）持续累积，用户必须手动执行 `/compress`，否则上下文溢出报错
- 压缩时一次性丢弃所有历史，丢失已提取的会话记忆——压缩后模型"失忆"，需重新描述上下文
- 无 `cache_edits` API 支持——每次压缩重建整个 prompt cache，浪费 cache write tokens

**改进收益**：
- **MicroCompact**：自动在 turn 间裁剪旧工具结果，长会话可无限延续而无需手动干预
- **Session-Memory Compact**：压缩时保留关键记忆 + 最近 5 个文件重注入——压缩后模型仍能"接着干"
- **多级阈值**：~93% 自动触发（Claude Code 默认）vs 70% 手动触发——用户感知不到压缩发生

**相关文章**：
- [上下文压缩深度对比](./context-compression-deep-dive.md)

**建议方案**：
1. 实现 micro-compact：在每个 turn 结束后，自动裁剪冗余的工具结果（如大文件读取的截断部分）
2. 实现 session-memory compact：压缩时保留已提取的会话记忆 (Memory)，而非简单丢弃
3. 引入多级压缩阈值（而非单一 70%），根据模型 token 限制动态调整

---

<a id="item-2"></a>

### 2. Fork 子代理 (Subagent)（P0）

**Claude Code 实现**：
- `tools/AgentTool/forkSubagent.ts` — fork 机制核心
- 当 `subagent_type` 未指定时，自动 fork 当前会话上下文
- 子代理继承父代理的完整对话历史、系统 prompt、工具池
- 使用 `FORK_BOILERPLATE_TAG` 防止递归 fork
- prompt cache 优化：所有 fork 子代理产生字节一致的 API 请求前缀

**源码引用**：
- 源码: `tools/AgentTool/forkSubagent.ts`（210 行）
- 源码: `tools/AgentTool/AgentTool.tsx`（1397 行）
- 源码: `tools/AgentTool/runAgent.ts`（973 行）

**Qwen Code 现状**：
- 源码: `packages/core/src/tools/agent.ts` — Agent 工具存在，但必须显式指定 `subagent_type`
- 源码: `packages/core/src/subagents/` — 子代理管理器，但仅支持预定义类型
- 无法 fork 当前会话上下文，无法继承对话历史

**缺失后果**：
- 子代理无法获得父代理的对话上下文——每次委派任务都需要在 prompt 中重复描述背景，增加 token 消耗和信息丢失风险
- 每个子代理的 API 请求前缀完全不同——无法共享 prompt cache，5 个子代理 = 5× 完整 prompt 费用（100K context 下约 500K tokens vs fork 模式 ~105K）
- 用户必须显式指定 `subagent_type`——模型无法自然地"分叉去做"，降低了自主性

**改进收益**：
- **上下文零成本传递**：子代理继承完整对话历史，无需重复描述——任务理解准确率提升
- **Prompt Cache 共享**：N 个 fork 子代理共享一份缓存，成本从 N× 降为 ~1×——典型场景节省 80%+ token 费用
- **隐式调用**：省略 `subagent_type` 即 fork——降低模型认知负担，让委派更自然

**相关文章**：
- [Fork 子代理 Deep-Dive](./fork-subagent-deep-dive.md)
- [Claude Code 多代理系统](../tools/claude-code/09-multi-agent.md)

**建议方案**：
1. 在 Agent 工具 schema 中将 `subagent_type` 改为可选
2. 实现 fork 消息构建逻辑：从当前对话历史构建子代理上下文
3. 实现递归 fork 防护（检测 fork boilerplate tag）
4. 优化 prompt cache：确保 fork 前缀的字节一致性

---

<a id="item-3"></a>

### 3. 投机执行 (Speculation) 系统完善（P1）

**Claude Code 实现**：
- `services/PromptSuggestion/speculation.ts` — 991 行完整投机执行 (Speculation) 引擎
- 使用 overlay-fs 实现 copy-on-write 文件隔离
- 写操作写入 overlay 目录，用户确认后 copy-overlay-to-main
- 自动检测 write tools（Edit/Write/NotebookEdit）并拒绝投机
- 与 PromptSuggestion 深度集成：suggestion 展示时自动启动投机

**源码引用**：
- 源码: `services/PromptSuggestion/speculation.ts`（991 行）
- 源码: `services/PromptSuggestion/promptSuggestion.ts`

**Qwen Code 现状**：
- 源码: `packages/core/src/followup/speculation.ts`（563 行）— v0.15.0 已实现完整系统
- 源码: `packages/core/src/followup/overlayFs.ts`（140 行）— Copy-on-Write overlay 文件系统
- 源码: `packages/core/src/followup/speculationToolGate.ts`（146 行）— 工具安全分类（safe/write/boundary/unknown）
- 源码: `packages/core/src/followup/suggestionGenerator.ts`（367 行）— 建议生成 + 12 条过滤规则
- 已实现 `acceptSpeculation()` + `generatePipelinedSuggestion()` + 边界检测
- **当前限制**：`enableSpeculation` 默认关闭，需用户手动开启

**缺失后果（默认关闭）**：
- 用户每次按 Tab 接受建议后，仍需等待完整的 API 调用 + 工具执行——典型等待 2-10 秒
- 无法实现"Tab-Tab-Tab"连续操作模式——每次接受后都有延迟中断

**改进收益（默认开启后）**：
- **零感知延迟**：建议展示时 speculation 已在后台预执行，Tab 接受后结果立即呈现
- **Pipelined Suggestion**：speculation 完成后自动预生成下一个建议——用户可连续 Tab 操作
- 预计首次交互延迟改善 2-5 秒（取决于工具执行时间）

**相关文章**：
- [Claude Code 提示建议](../tools/claude-code/10-prompt-suggestions.md)
- [启动阶段优化深度对比](./startup-optimization-deep-dive.md)
- [输入队列深度对比](./input-queue-deep-dive.md)

**建议方案**：
1. 将 `enableSpeculation` 默认值改为 `true`（当前为 `false`）
2. 扩大 speculationToolGate 的 safe 工具列表覆盖度
3. 增加 speculation 完成率的遥测追踪，评估 boundary 命中频率
4. 优化 `MAX_SPECULATION_TURNS`（当前 20）的动态调节策略

---

<a id="item-4"></a>

### 4. 会话记忆 (Session Memory) 系统（P1）

**Claude Code 实现**：
- `services/SessionMemory/sessionMemory.ts` — 会话记忆 (Memory) 管理
- `services/SessionMemory/sessionMemoryUtils.ts` — 记忆 (Memory) 提取和检索
- `services/SessionMemory/prompts.ts` — 记忆 (Memory) 提取 prompt
- `memdir/` 目录（8 文件）— 记忆 (Memory) 目录和检索系统
- `memdir/findRelevantMemories.ts` — 基于相关性的记忆 (Memory) 检索
- 跨 session 持久化：记忆 (Memory) 在 session 结束后自动提取并存储

**源码引用**：
- 源码: `services/SessionMemory/sessionMemory.ts`
- 源码: `memdir/findRelevantMemories.ts`
- 源码: `memdir/memdir.ts`

**Qwen Code 现状**：
- 源码: `packages/core/src/tools/memoryTool.ts` — 仅支持简单的笔记读写
- 无跨 session 记忆 (Memory)
- 无记忆 (Memory) 提取/检索机制
- 无记忆 (Memory) 生命周期管理

**缺失后果**：
- 每次新 session 从零开始——用户需反复告知项目背景、编码规范、已踩过的坑
- 复杂项目中同一问题被多次排查——前次 session 的发现未持久化
- 与 `/compact` 冲突——压缩后丢失的上下文无法从记忆中恢复

**改进收益**：
- **跨 session 连续性**：关键决策、文件结构、技术栈信息自动提取并持久化——新 session 自动注入相关记忆
- **压缩后恢复**：记忆在 compact 时被保留（session-memory compact），模型不会因压缩而"失忆"
- **项目级知识积累**：多人/多 session 的发现汇聚为项目知识库——团队共享学习曲线

**相关文章**：
- [记忆系统深度对比](./memory-system-deep-dive.md)

**建议方案**：
1. 实现 SessionMemoryService：管理会话记忆 (Memory) 的提取、存储和检索
2. 实现记忆 (Memory) 提取 hook：在 compact 或 session 结束时自动提取关键信息
3. 实现记忆 (Memory) 检索工具：在新 session 开始时检索相关记忆 (Memory)
4. 记忆 (Memory) 持久化到 `.qwen/` 目录，支持项目级和用户级记忆 (Memory)

---

<a id="item-5"></a>

### 5. Auto Dream 自动记忆 (Memory) 整理（P1）

**Claude Code 实现**：
- `services/autoDream/autoDream.ts` — 自动记忆 (Memory) 整理引擎（325 行）
- 双门控触发：时间门控（默认 24h）+ session 数量门控（默认 5 个 session）
- 使用 forked agent 在后台执行记忆 (Memory) 整理
- `services/autoDream/consolidationPrompt.ts` — 整理 prompt
- `services/autoDream/consolidationLock.ts` — 防止多进程并发整理

**源码引用**：
- 源码: `services/autoDream/autoDream.ts`（324 行）
- 源码: `services/autoDream/consolidationPrompt.ts`
- 源码: `services/autoDream/consolidationLock.ts`

**相关文章**：
- [记忆系统深度对比](./memory-system-deep-dive.md)
- [上下文压缩深度对比](./context-compression-deep-dive.md)

**Qwen Code 现状**：
- 完全缺失此功能

**缺失后果**：
- 记忆文件（QWEN.md / MEMORY.md）随使用增长无限膨胀——token 预算被陈旧记忆占满
- 相互矛盾的记忆（旧决策 vs 新决策）共存——模型收到冲突指令
- 用户需手动清理过时记忆——违背"AI 代理应自治"原则

**改进收益**：
- **自动整合**：后台 agent 定期合并、去重、删除过时记忆——记忆始终精简且一致
- **门控保护**：仅在 24h + 5 session 门控同时满足时触发——避免频繁整理干扰正常使用
- **并发安全**：文件锁防止多进程同时整理——适合多终端/CI 场景

**建议方案**：
1. 实现 DreamConfig：定义时间门控和 session 数量门控参数
2. 实现 DreamScheduler：在 post-sampling hook 中检查门控条件
3. 当门控触发时，fork 一个只读 agent 执行记忆整理
4. 实现 ConsolidationLock：使用文件锁防止并发整理
5. 整理结果写入 `.qwen/dream/` 目录，供后续 session 检索

---

<a id="item-6"></a>

### 6. Mid-Turn Queue Drain（P0）

**Claude Code 实现**：`query.ts#L1550-L1643` 在每个工具批次执行完成后、下一次 API 调用前，drain 命令队列，将用户输入作为 attachment 注入 `toolResults`，使模型在**当前 turn 的下一个 step** 即可看到新输入。

**Qwen Code 现状**：`agent-core.ts` 的 `runReasoningLoop` 内无队列检查。用户输入仅在整个 round 结束后通过外层 `runLoop` 的 `dequeue()` 处理。

**缺失后果**：Agent 执行 5 步修改时用户发现方向错误，必须等全部完成后才能纠正——已完成的错误修改需要撤销。

**改进收益**：用户可在 Agent 执行中途发送指令（如"停，先改 config"），模型在下一个 step 的 API 调用中立即看到——避免无用工作。

**相关文章**：[输入队列与中断机制](./input-queue-deep-dive.md)

**进展**：PR [QwenLM/qwen-code#2854](https://github.com/QwenLM/qwen-code/pull/2854)（open）

---

<a id="item-7"></a>

### 7. 智能工具并行 Kind-based Batching（P1）

**Claude Code 实现**：`services/tools/toolOrchestration.ts` 通过 `isConcurrencySafe()` 判断工具是否可并行，连续只读工具合并为并行批次（最大 10 并发），写工具独立串行。

**Qwen Code 现状**：Agent 工具并发，其他所有工具顺序执行。

**缺失后果**：代码探索场景（多个 Glob + Grep + Read）延迟 7× vs 1×（7 个只读工具串行 vs 并行）。

**改进收益**：I/O 密集型任务速度提升 5-10×。上下文修改队列化防止并行竞态。

**相关文章**：[工具并行执行](./tool-parallelism-deep-dive.md)

**进展**：PR [QwenLM/qwen-code#2864](https://github.com/QwenLM/qwen-code/pull/2864)（open）

---

<a id="item-8"></a>

### 8. 启动优化 API Preconnect + Early Input（P1）

**Claude Code 实现**：`utils/apiPreconnect.ts`（71 行）fire-and-forget HEAD 请求预热 TCP+TLS 连接；`utils/earlyInput.ts`（191 行）启动期间 raw mode 捕获键盘输入，REPL 就绪后预填充。

**Qwen Code 现状**：完全缺失。首次 API 需完整握手（+100-200ms），启动期间键入丢失。

**缺失后果**：用户输入 `qwen-code` 后立即打字的内容全部丢失；首次 API 调用多 100-200ms。

**改进收益**：首次交互延迟改善 ~150ms + 打字不丢失——启动体验更流畅。

**相关文章**：[启动阶段优化](./startup-optimization-deep-dive.md)

---

<a id="item-9"></a>

### 9. 指令条件规则 frontmatter `paths:` + 惰加载（P1）

**Claude Code 实现**：`.claude/rules/*.md` 支持 `paths:` frontmatter glob 模式。有 `paths:` 的规则仅在操作匹配文件时惰加载；无 `paths:` 的规则急加载。支持 HTML 注释剥离。

**Qwen Code 现状**：无 frontmatter、无条件加载、无 HTML 注释剥离。所有指令文件急加载。

**缺失后果**：`src/`、`tests/`、`docs/` 的不同编码规范必须全部写在一个 QWEN.md 中——系统提示膨胀。

**改进收益**：按文件路径匹配加载规则——TypeScript 文件操作时只注入 TS 规范，节省 token 且规则更精准。

**相关文章**：[指令文件加载](./instruction-loading-deep-dive.md)

---

<a id="item-11"></a>

### 11. 工具动态发现 ToolSearchTool（P1）

**Claude Code 实现**：`tools/ToolSearchTool/ToolSearchTool.ts` 支持关键词搜索和 `select:` 直接选择 deferred 工具。延迟加载的工具不占系统提示 token，需要时按需加载。

**Qwen Code 现状**：缺失。所有工具始终加载到系统提示中。

**缺失后果**：39+ 工具的 schema 全部注入系统提示——占用大量 token 预算。

**改进收益**：仅加载核心工具（~10 个），其余按需——系统提示 token 减少 50%+。

---

<a id="item-12"></a>

### 12. Commit Attribution Co-Authored-By（P1）

**Claude Code 实现**：`utils/commitAttribution.ts`（961 行）跟踪每个文件的 AI vs 人类字符贡献比例，`Co-Authored-By` 注入 commit 消息，attribution 元数据存储在 git notes 中。

**Qwen Code 现状**：缺失。

**缺失后果**：git 历史中无法区分 AI 生成代码和人类代码——开源合规和审计困难。

**改进收益**：透明的 AI 代码归因——满足开源项目 AI 贡献披露要求。

**相关文章**：[Git 工作流与会话管理](./git-workflow-session-deep-dive.md)

---

<a id="item-13"></a>

### 13. 会话分支 /branch（P1）

**Claude Code 实现**：`commands/branch/branch.ts`（296 行）fork 当前 transcript 为新 session，保留 `forkedFrom: { sessionId, messageUuid }` 溯源，自动命名 "(Branch)"。

**Qwen Code 现状**：缺失。

**缺失后果**：探索替代方案时必须丢弃当前进度，或手动复制/粘贴上下文。

**改进收益**：从任意节点创建分支——A/B 对比架构决策，原始 session 可随时 `--resume`。

**相关文章**：[Git 工作流与会话管理](./git-workflow-session-deep-dive.md)

---

<a id="item-49"></a>

### 49. Channels 消息推送系统（P1）

**Claude Code**：通过 MCP 协议支持从 Telegram、Discord、iMessage 或自定义 webhook 推送消息到运行中的 session。用户可在聊天应用中发消息，Agent 实时接收并响应。

**Qwen Code**：缺失。

**缺失后果**：用户只能在终端/IDE 中与 Agent 交互——无法从手机聊天应用远程发送补充信息。

**改进收益**：用户外出时可通过 Telegram/Discord 向 Agent 发送指令或补充上下文——真正的"随时随地"协作。

---

<a id="item-50"></a>

### 50. GitHub Actions CI 集成（P1）

**Claude Code**：官方 `anthropics/claude-code-action` GitHub Action，支持自动 PR 审查、issue 分类、代码修复。支持 AWS Bedrock 和 Google Vertex AI 后端。

**Qwen Code**：缺失。

**缺失后果**：用户需手动运行 Agent 审查 PR——无法在 CI 中自动化。

**改进收益**：每次 PR 自动触发 Agent 审查 + 提出修改建议——减少人工审查负担。类似功能可通过 `qwen-code -p` headless 模式实现。

---

<a id="item-51"></a>

### 51. GitHub Code Review 多代理自动审查（P1）

**Claude Code**：多代理自动 PR review——多个 Agent 并行审查不同文件，生成 inline 评论。Team/Enterprise 功能。

**Qwen Code**：已有 `/review` Skill，但为单代理、手动触发。

**缺失后果**：大 PR 审查慢——单 Agent 逐文件审查。

**改进收益**：多代理并行审查 + 自动 inline 评论——大 PR 审查时间从 N 分钟缩短到 ~1 分钟。

---

<a id="item-52"></a>

### 52. HTTP Hooks（P1）

**Claude Code**：Hooks 支持 `type: "http"`——POST JSON 到 URL 并接收 JSON 响应，而非仅执行 shell 命令。适合与外部服务（CI、审批系统、消息平台）集成。

**Qwen Code**：Hooks 仅支持 shell 命令执行。

**缺失后果**：与外部服务集成需通过 shell 中的 `curl` 间接实现——脆弱且难以处理 JSON 响应。

**改进收益**：Hook 原生 HTTP 支持——直接与 webhook/API 交互，响应可结构化解析并影响 Agent 决策。

---

<a id="item-58"></a>

### 58. Structured Output --json-schema（P1）

**Claude Code**：`tools/SyntheticOutputTool/SyntheticOutputTool.ts` + `--json-schema` CLI 参数。headless 模式下强制模型输出符合 JSON Schema 的结构化数据。使用 Ajv 运行时验证 + WeakMap 缓存。

**Qwen Code**：`-p` 模式仅输出纯文本，无 schema 验证。

**缺失后果**：CI 脚本解析 Agent 输出需自行 parse——脆弱且不可靠。

**改进收益**：`--json-schema '{"type":"object",...}'` → 输出保证符合 schema——CI 集成可靠性大幅提升。

---

<a id="item-59"></a>

### 59. Agent SDK 增强（P1）

**Claude Code**：`entrypoints/sdk/` 提供 Python + TypeScript 双语言 SDK，支持流式回调、工具审批回调、消息对象访问。

**Qwen Code**：已有 `@qwen-code/sdk`（TypeScript），但无 Python SDK。

**缺失后果**：Python 生态开发者（数据科学、后端）无法原生集成——需通过 shell 调用 CLI。

**改进收益**：补充 Python SDK — `from qwen_code import Agent` 原生接口，覆盖 Python 生态。

---

<a id="item-60"></a>

### 60. Bare Mode --bare（P1）

**Claude Code**：`entrypoints/cli.tsx#L283` + `main.tsx#L394`。跳过 hooks、LSP、plugins、auto-memory、CLAUDE.md 发现、OAuth/keychain。仅通过 CLI 参数显式传入上下文。CI 最快启动。

**Qwen Code**：`-p` 模式仍加载所有配置。

**缺失后果**：CI 中启动慢——加载了不需要的 hooks/plugins/memory。不同环境的 hooks 导致结果不可复现。

**改进收益**：`qwen-code --bare -p "task"` — 确定性执行，每台机器同样结果。

---

<a id="item-61"></a>

### 61. Remote Control Bridge（P1）

**Claude Code**：`bridge/` 目录（bridgeMain.ts + bridgeApi.ts + bridgeConfig.ts）。通过 `claude.ai/code` 网页驱动本地终端 session。Outbound-only 模式保证安全。

**Qwen Code**：缺失。

**缺失后果**：离开电脑后无法继续与 Agent 交互——任务需等用户回来。

**改进收益**：手机/浏览器远程驱动终端 Agent——外出时可继续审批权限、补充上下文。

---

<a id="item-62"></a>

### 62. /teleport 跨平台迁移（P1）

**Claude Code**：`utils/teleport.tsx` + `utils/teleport/`（api.ts + gitBundle.ts + environments.ts）。Web session → 终端迁移，包含分支 checkout + 完整会话历史加载。

**Qwen Code**：缺失。

**改进收益**：Web 上启动长任务 → 完成后 `/teleport` 到终端继续本地调试——跨平台无缝切换。

---

<a id="item-63"></a>

### 63. GitLab CI/CD 集成（P1）

**Claude Code**：官方 GitLab pipeline 集成，类似 GitHub Actions 的自动 PR 审查 + issue 分类。

**Qwen Code**：仅有 GitHub 相关集成。

**改进收益**：覆盖 GitLab 用户群——企业用户中 GitLab 占比显著。

---


