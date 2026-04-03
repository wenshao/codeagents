# Qwen Code 改进建议报告

> 基于对 Claude Code（leaked 源码，56 个顶层模块，~1800 文件）与 Qwen Code（开源源码，~500 文件）的系统性源码对比分析。

## 一、Claude Code 功能模块清单

| 模块 | 文件数 | 核心职责 |
|------|--------|----------|
| `tools/` | 43 目录 + 1 文件 | 工具系统（含 40+ 内置工具） |
| `services/` | 36 目录 + 10 文件 | 后端服务（compact/MCP/analytics/SessionMemory 等） |
| `commands/` | 101 目录 + 13 文件 | 斜杠命令系统 |
| `components/` | 144 项 | TUI 组件库（React/Ink） |
| `hooks/` | 85 项 | React hooks 系统 |
| `tasks/` | 9 项 | 任务系统（LocalAgent/RemoteAgent/Dream/Teammate 等） |
| `state/` | 6 项 | 全局状态管理 |
| `bridge/` | 31 项 | REPL 远程桥接 |
| `utils/` | 大量 | 工具函数库 |
| `context/` | 9 项 | 上下文管理 |
| `memdir/` | 8 项 | 记忆目录/检索 |
| `coordinator/` | 1 项 | 协调器模式 |
| `plugins/` | 2 项 | 插件系统 |
| `services/contextCollapse/` | 多文件 | 上下文折叠（History Snip） |
| `services/autoDream/` | 4 文件 | 自动记忆整理 |
| `services/PromptSuggestion/` | 2 文件 | 预测建议 + 投机执行 |
| `services/SessionMemory/` | 3 文件 | 会话记忆系统 |
| `services/compact/` | 11 文件 | 多层压缩策略 |
| `services/lsp/` | 7 文件 | LSP 客户端管理 |
| `services/mcp/` | 23 文件 | MCP 服务器管理 |
| `services/analytics/` | 9 文件 | 分析 + GrowthBook 特性开关 |
| `native-ts/file-index/` | 1 文件 | 文件索引（fzf 风格模糊搜索） |

## 二、Qwen Code 改进建议矩阵

| 优先级 | 改进点 | Claude Code 实现 | Qwen Code 现状 | 实现难度 | 用户价值 | 建议方案 |
|--------|--------|------------------|----------------|----------|----------|----------|
| **P0** | 多层上下文压缩策略 | 4 层：microCompact, apiMicrocompact, autoCompact, sessionMemoryCompact | 仅单一 ChatCompressionService，基于固定 token 阈值 | 中 | 高 | 引入 micro-compact（turn 级）+ session-memory compact 分层策略 |
| **P0** | Fork 子代理（继承上下文） | forkSubagent.ts 支持隐式 fork，子代理继承父对话上下文 + 系统 prompt | Agent 工具仅支持预定义的 subagent_type，无法 fork 当前会话上下文 | 中 | 高 | 实现 forkSubagent 机制，支持 `subagent_type` 可选时的上下文继承 |
| **P1** | 投机执行（Speculation）系统 | speculation.ts（991 行）实现 overlay-fs + copy-on-write，在用户确认前预执行只读工具 | v0.15.0 已实现完整系统（563 行 speculation.ts + overlayFs + speculationToolGate），但默认关闭（`enableSpeculation: false`） | 小 | 高 | 默认启用 speculation，优化 speculationToolGate 的工具分类覆盖度 |
| **P1** | 会话记忆系统（Session Memory） | SessionMemory 服务 + memdir 实现跨 session 记忆提取与检索 | 仅有 memoryTool.ts 的简单笔记功能，无跨 session 记忆 | 大 | 高 | 实现 SessionMemory 服务 + 记忆提取 hook + 记忆检索工具 |
| **P1** | Auto Dream（自动记忆整理） | autoDream.ts 基于时间门控 + session 数量门控触发 forked agent 整理 | 无对应功能 | 中 | 高 | 实现基于 GrowthBook 门控的自动记忆整理，后台 fork agent 执行 |
| **P1** | 上下文折叠（Context Collapse/History Snip） | contextCollapse 服务实现 span 级上下文摘要 + staging，feature-gated | 无对应功能 | 大 | 中 | 引入 History Snip 机制，对早期对话 span 进行摘要压缩 |
| **P1** | 工具池动态发现（Tool Search） | ToolSearchTool 支持关键词搜索和 `select:` 直接选择 deferred 工具 | 无对应工具，工具选择完全依赖模型 | 小 | 中 | 实现 ToolSearchTool，支持 deferred 工具的延迟加载和搜索 |
| **P2** | 并行工具调用优化 | 最大并发度可配置（CLAUDE_CODE_MAX_TOOL_USE_CONCURRENCY，默认 10），基于 `isConcurrencySafe` 分区 | 已有 CONCURRENCY_SAFE_KINDS 分区和并行批处理，但无并发度上限控制 | 小 | 中 | 增加 `QWEN_MAX_TOOL_CONCURRENCY` 环境变量控制并发度上限 |
| **P2** | 计划模式 Interview Phase | EnterPlanMode 支持 interview 阶段，分离探索和规划 | exitPlanMode 工具存在，但无 interview 阶段 | 中 | 中 | 实现 plan_mode 附件系统，支持 interview 阶段的详细工作流 |
| **P2** | Brief 工具（异步消息） | BriefTool 支持向用户发送异步消息（含附件），proactive status | 无对应工具，Agent 只能通过工具结果与用户通信 | 中 | 中 | 实现 BriefTool，支持 agent 向用户发送带附件的异步消息 |
| **P2** | SendMessage 工具（多代理通信） | SendMessageTool 支持队友间通信、shutdown 请求、plan approval | 无跨代理通信机制 | 中 | 中 | 实现代理间消息传递机制，支持 arena 模式下的通信 |
| **P2** | 文件索引（File Index） | FileIndex 实现 fzf 风格模糊文件搜索，支持异步增量索引 | 依赖 rg/glob，无模糊搜索能力 | 中 | 中 | 实现纯 TS 文件索引器（nucleo 风格），提供模糊文件搜索工具 |
| **P2** | 配置工具（Config Tool） | ConfigTool 支持 get/set 设置（主题、模型、权限等），带 schema 验证 | 设置通过 /settings 命令，无工具化访问 | 小 | 中 | 实现 ConfigTool，支持模型通过工具读写设置 |
| **P2** | 自动后台化 Agent | getAutoBackgroundMs() 基于 GrowthBook 门控自动后台化长时 agent | agent 的 run_in_background 需显式指定 | 小 | 中 | 增加自动后台化阈值，超时自动转后台 |
| **P3** | 安全审查命令（/security-review） | 基于 frontmatter 模板的安全审查命令，聚焦漏洞检测 | 无对应命令 | 小 | 低 | 实现 /security-review 命令，基于 git diff 的安全扫描 |
| **P3** | Ultraplan（远程计划探索） | /ultraplan 启动远程 CCR 会话，使用更强模型进行深度规划 | 无对应功能 | 大 | 低 | 依赖远程执行基础设施，暂不推荐 |
| **P3** | 顾问模型（Advisor Model） | /advisor 命令配置副模型提供建议 | 无对应功能 | 中 | 低 | 需多模型同时调用能力，架构改动大 |
| **P3** | Vim 模式完整实现 | motions.ts, operators.ts, textObjects.ts, transitions.ts 完整实现 | 已有 vim.ts 基础实现 | 中 | 低 | 完善 Vim keybinding，补充 text objects 和 operators |
| **P3** | 语音模式 | voice/ 目录 + voice hooks + STT 流式处理 | 无对应功能 | 大 | 低 | 需音频采集 + STT 基础设施 |
| **P3** | 插件市场 | thinkback 等插件可从市场安装，带前端 UI | 无插件市场 | 大 | 低 | 需插件发现、安装、版本管理基础设施 |

## 三、Top 5 改进点详细说明

### 1. 多层上下文压缩策略（P0）

**Claude Code 实现**：
- `services/compact/microCompact.ts` — turn 级微压缩，移除冗余工具结果
- `services/compact/autoCompact.ts` — 基于 token 阈值的自动压缩
- `services/compact/apiMicrocompact.ts` — API 原生上下文管理（`clear_tool_uses` / `clear_thinking`）
- `services/compact/sessionMemoryCompact.ts` — 基于会话记忆的压缩，保留关键上下文
- `services/compact/postCompactCleanup.ts` — 压缩后清理
- `services/compact/grouping.ts` — 消息分组优化

**源码引用**：
- `../claude-code-leaked/services/compact/autoCompact.ts` — 自动压缩触发逻辑
- `../claude-code-leaked/services/compact/sessionMemoryCompact.ts` — 记忆感知压缩
- `../claude-code-leaked/services/compact/compact.ts` — 主压缩引擎（1706 行）

**Qwen Code 现状**：
- 仅有 `packages/core/src/services/chatCompressionService.ts`（369 行），基于固定 token 阈值（70%）的单一压缩策略
- 无 micro-compact、无 memory-aware compact、无 API 原生上下文管理

**建议方案**：
1. 实现 micro-compact：在每个 turn 结束后，自动裁剪冗余的工具结果（如大文件读取的截断部分）
2. 实现 session-memory compact：压缩时保留已提取的会话记忆，而非简单丢弃
3. 引入多级压缩阈值（而非单一 70%），根据模型 token 限制动态调整

---

### 2. Fork 子代理（P0）

**Claude Code 实现**：
- `tools/AgentTool/forkSubagent.ts` — fork 机制核心
- 当 `subagent_type` 未指定时，自动 fork 当前会话上下文
- 子代理继承父代理的完整对话历史、系统 prompt、工具池
- 使用 `FORK_BOILERPLATE_TAG` 防止递归 fork
- prompt cache 优化：所有 fork 子代理产生字节一致的 API 请求前缀

**源码引用**：
- `../claude-code-leaked/tools/AgentTool/forkSubagent.ts` — fork 逻辑（211 行）
- `../claude-code-leaked/tools/AgentTool/AgentTool.tsx` — Agent 工具主逻辑（1398 行）
- `../claude-code-leaked/tools/AgentTool/runAgent.ts` — agent 执行（974 行）

**Qwen Code 现状**：
- `packages/core/src/tools/agent.ts` — Agent 工具存在，但必须显式指定 `subagent_type`
- `packages/core/src/subagents/` — 子代理管理器，但仅支持预定义类型
- 无法 fork 当前会话上下文，无法继承对话历史

**建议方案**：
1. 在 Agent 工具 schema 中将 `subagent_type` 改为可选
2. 实现 fork 消息构建逻辑：从当前对话历史构建子代理上下文
3. 实现递归 fork 防护（检测 fork boilerplate tag）
4. 优化 prompt cache：确保 fork 前缀的字节一致性

---

### 3. 投机执行系统完善（P1）

**Claude Code 实现**：
- `services/PromptSuggestion/speculation.ts` — 991 行完整投机执行引擎
- 使用 overlay-fs 实现 copy-on-write 文件隔离
- 写操作写入 overlay 目录，用户确认后 copy-overlay-to-main
- 自动检测 write tools（Edit/Write/NotebookEdit）并拒绝投机
- 与 PromptSuggestion 深度集成：suggestion 展示时自动启动投机

**源码引用**：
- `../claude-code-leaked/services/PromptSuggestion/speculation.ts` — 投机执行引擎
- `../claude-code-leaked/services/PromptSuggestion/promptSuggestion.ts` — 建议生成器

**Qwen Code 现状**（v0.15.0 已更新）：
- `packages/core/src/followup/speculation.ts` — 563 行，已实现完整投机执行系统
- `packages/core/src/followup/overlayFs.ts` — 140 行，Copy-on-Write overlay 文件系统
- `packages/core/src/followup/speculationToolGate.ts` — 146 行，工具安全分类（safe/write/boundary/unknown）
- `packages/core/src/followup/suggestionGenerator.ts` — 367 行，建议生成 + 12 条过滤规则
- 已实现 `acceptSpeculation()` + `generatePipelinedSuggestion()` + 边界检测
- **当前限制**：`enableSpeculation` 默认关闭，需用户手动开启

**建议方案**：
1. 将 `enableSpeculation` 默认值改为 `true`（当前为 `false`）
2. 扩大 speculationToolGate 的 safe 工具列表覆盖度
3. 增加 speculation 完成率的遥测追踪，评估 boundary 命中频率
4. 优化 `MAX_SPECULATION_TURNS`（当前 20）的动态调节策略

---

### 4. 会话记忆系统（P1）

**Claude Code 实现**：
- `services/SessionMemory/sessionMemory.ts` — 会话记忆管理
- `services/SessionMemory/sessionMemoryUtils.ts` — 记忆提取和检索
- `services/SessionMemory/prompts.ts` — 记忆提取 prompt
- `memdir/` 目录（8 文件）— 记忆目录和检索系统
- `memdir/findRelevantMemories.ts` — 基于相关性的记忆检索
- 跨 session 持久化：记忆在 session 结束后自动提取并存储

**源码引用**：
- `../claude-code-leaked/services/SessionMemory/sessionMemory.ts`
- `../claude-code-leaked/memdir/findRelevantMemories.ts`
- `../claude-code-leaked/memdir/memdir.ts`

**Qwen Code 现状**：
- `packages/core/src/tools/memoryTool.ts` — 仅支持简单的笔记读写
- 无跨 session 记忆
- 无记忆提取/检索机制
- 无记忆生命周期管理

**建议方案**：
1. 实现 SessionMemoryService：管理会话记忆的提取、存储和检索
2. 实现记忆提取 hook：在 compact 或 session 结束时自动提取关键信息
3. 实现记忆检索工具：在新 session 开始时检索相关记忆
4. 记忆持久化到 `.qwen/` 目录，支持项目级和用户级记忆

---

### 5. Auto Dream 自动记忆整理（P1）

**Claude Code 实现**：
- `services/autoDream/autoDream.ts` — 自动记忆整理引擎（325 行）
- 双门控触发：时间门控（默认 24h）+ session 数量门控（默认 5 个 session）
- 使用 forked agent 在后台执行记忆整理
- `services/autoDream/consolidationPrompt.ts` — 整理 prompt
- `services/autoDream/consolidationLock.ts` — 防止多进程并发整理

**源码引用**：
- `../claude-code-leaked/services/autoDream/autoDream.ts`
- `../claude-code-leaked/services/autoDream/consolidationPrompt.ts`
- `../claude-code-leaked/services/autoDream/consolidationLock.ts`

**Qwen Code 现状**：
- 完全缺失此功能

**建议方案**：
1. 实现 DreamConfig：定义时间门控和 session 数量门控参数
2. 实现 DreamScheduler：在 post-sampling hook 中检查门控条件
3. 当门控触发时，fork 一个只读 agent 执行记忆整理
4. 实现 ConsolidationLock：使用文件锁防止并发整理
5. 整理结果写入 `.qwen/dream/` 目录，供后续 session 检索

---

## 四、架构差异总结

| 维度 | Claude Code | Qwen Code | 差距评估 |
|------|-------------|-----------|----------|
| 压缩策略 | 4 层分层压缩 | 单一阈值压缩 | 显著落后 |
| 子代理 | 支持 fork + 上下文继承 | 仅预定义类型 | 显著落后 |
| 投机执行 | 完整 overlay-fs + cow（991 行） | v0.15.0 已完整实现（563 行），默认关闭 | 小差距（仅默认值） |
| 会话记忆 | SessionMemory + memdir | 简单笔记工具 | 显著落后 |
| 自动记忆整理 | Auto Dream | 无 | 缺失 |
| 上下文折叠 | History Snip | 无 | 缺失 |
| 工具发现 | ToolSearchTool | 无 | 缺失 |
| 并发控制 | 可配置上限（默认 10） | 无上限 | 小差距 |
| 多代理通信 | SendMessageTool | 无 | 缺失 |
| 文件索引 | FileIndex（fzf 风格） | 依赖 rg/glob | 中等差距 |
