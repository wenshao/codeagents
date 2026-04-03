# Qwen Code 改进建议报告

> 基于对 Claude Code（源码分析，56 个顶层模块，~1800 文件）与 Qwen Code（开源源码，~500 文件）的系统性源码对比分析。
>
> 如需查阅源码，可参考本地仓库（不在本文档库中）：
> - Claude Code: `../claude-code-leaked/`
> - Qwen Code: `../qwen-code/`

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
| `bridge/` | 31 项 | REPL 远程桥接 (Bridge) |
| `utils/` | 大量 | 工具函数库 |
| `context/` | 9 项 | 上下文管理 |
| `memdir/` | 8 项 | 记忆 (Memory) 目录/检索 |
| `coordinator/` | 1 项 | 协调器模式 |
| `plugins/` | 2 项 | 插件 (Plugin) 系统 |
| `services/contextCollapse/` | 多文件 | 上下文折叠 (Context Collapse / History Snip) |
| `services/autoDream/` | 4 文件 | 自动记忆 (Memory) 整理 |
| `services/PromptSuggestion/` | 2 文件 | 预测建议 + 投机执行 (Speculation) |
| `services/SessionMemory/` | 3 文件 | 会话记忆 (Session Memory) 系统 |
| `services/compact/` | 11 文件 | 多层压缩策略 |
| `services/lsp/` | 7 文件 | LSP 客户端管理 |
| `services/mcp/` | 23 文件 | MCP 服务器管理 |
| `services/analytics/` | 9 文件 | 分析 + GrowthBook 特性开关 |
| `native-ts/file-index/` | 1 文件 | 文件索引（fzf 风格模糊搜索） |

## 二、Qwen Code 改进建议矩阵

| 优先级 | 改进点 | Claude Code 实现 | Qwen Code 现状 | 实现难度 | 用户价值 | 建议方案 |
|--------|--------|------------------|----------------|----------|----------|----------|
| **P0** | 多层上下文压缩 (Context Compression) 策略 | 4 层：microCompact, autoCompact, reactiveCompact, sessionMemoryCompact | 仅单一 ChatCompressionService，基于固定 token 阈值 | 中 | 高 | 引入 micro-compact（turn 级）+ session-memory compact 分层策略 |
| **P0** | Fork 子代理 (Subagent)（继承上下文） | forkSubagent.ts 支持隐式 fork，子代理 (Subagent) 继承父对话上下文 + 系统 prompt | Agent 工具仅支持预定义的 subagent_type，无法 fork 当前会话上下文 | 中 | 高 | 实现 forkSubagent 机制，支持 `subagent_type` 可选时的上下文继承 |
| **P1** | 投机执行 (Speculation) 系统 | speculation.ts 实现 overlay-fs + copy-on-write，在用户确认前预执行只读工具 | 已有 speculation.ts 和 overlayFs.ts 骨架，但功能不完整，与 followup 耦合度低 | 小 | 高 | 完善 speculation 的 overlay-fs 隔离层，增加 copy-overlay-to-main 机制 |
| **P1** | 会话记忆 (Session Memory) 系统 | SessionMemory 服务 + memdir 实现跨 session 记忆 (Memory) 提取与检索 | 仅有 memoryTool.ts 的简单笔记功能，无跨 session 记忆 (Memory) | 大 | 高 | 实现 SessionMemory 服务 + 记忆 (Memory) 提取 hook + 记忆 (Memory) 检索工具 |
| **P1** | Auto Dream（自动记忆 (Memory) 整理） | autoDream.ts 基于时间门控 + session 数量门控触发 forked agent 整理 | 无对应功能 | 中 | 高 | 实现基于 GrowthBook 门控的自动记忆 (Memory) 整理，后台 fork agent 执行 |
| **P1** | 上下文折叠 (Context Collapse / History Snip) | contextCollapse 服务实现 span 级上下文摘要 + staging，feature-gated | 无对应功能 | 大 | 中 | 引入 History Snip 机制，对早期对话 span 进行摘要压缩 |
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
| **P3** | 插件 (Plugin) 市场 | thinkback 等插件 (Plugin) 可从市场安装，带前端 UI | 无插件 (Plugin) 市场 | 大 | 低 | 需插件 (Plugin) 发现、安装、版本管理基础设施 |

## 三、Top 5 改进点详细说明

### 1. 多层上下文压缩 (Context Compression) 策略（P0）

**Claude Code 实现**：
- `services/compact/microCompact.ts` — turn 级微压缩，移除冗余工具结果
- `services/compact/autoCompact.ts` — 基于 token 阈值的自动压缩
- `services/compact/reactiveCompact.ts` — 响应式压缩（feature-gated）
- `services/compact/sessionMemoryCompact.ts` — 基于会话记忆 (Memory) 的压缩，保留关键上下文
- `services/compact/postCompactCleanup.ts` — 压缩后清理
- `services/compact/grouping.ts` — 消息分组优化

**源码引用**：
- 源码: `services/compact/autoCompact.ts`
- 源码: `services/compact/sessionMemoryCompact.ts`
- 源码: `services/compact/compact.ts`（1706 行）

**Qwen Code 现状**：
- 源码: `packages/core/src/services/chatCompressionService.ts`（369 行），基于固定 token 阈值（70%）的单一压缩策略
- 无 micro-compact、无 memory-aware compact、无 reactive compact

**相关文章**：
- [上下文压缩深度对比](./context-compression-deep-dive.md)

**建议方案**：
1. 实现 micro-compact：在每个 turn 结束后，自动裁剪冗余的工具结果（如大文件读取的截断部分）
2. 实现 session-memory compact：压缩时保留已提取的会话记忆 (Memory)，而非简单丢弃
3. 引入多级压缩阈值（而非单一 70%），根据模型 token 限制动态调整

---

### 2. Fork 子代理 (Subagent)（P0）

**Claude Code 实现**：
- `tools/AgentTool/forkSubagent.ts` — fork 机制核心
- 当 `subagent_type` 未指定时，自动 fork 当前会话上下文
- 子代理继承父代理的完整对话历史、系统 prompt、工具池
- 使用 `FORK_BOILERPLATE_TAG` 防止递归 fork
- prompt cache 优化：所有 fork 子代理产生字节一致的 API 请求前缀

**源码引用**：
- 源码: `tools/AgentTool/forkSubagent.ts`（211 行）
- 源码: `tools/AgentTool/AgentTool.tsx`（1398 行）
- 源码: `tools/AgentTool/runAgent.ts`（974 行）

**Qwen Code 现状**：
- 源码: `packages/core/src/tools/agent.ts` — Agent 工具存在，但必须显式指定 `subagent_type`
- 源码: `packages/core/src/subagents/` — 子代理管理器，但仅支持预定义类型
- 无法 fork 当前会话上下文，无法继承对话历史

**相关文章**：
- [Claude Code 多代理系统](../tools/claude-code/09-multi-agent.md)

**建议方案**：
1. 在 Agent 工具 schema 中将 `subagent_type` 改为可选
2. 实现 fork 消息构建逻辑：从当前对话历史构建子代理上下文
3. 实现递归 fork 防护（检测 fork boilerplate tag）
4. 优化 prompt cache：确保 fork 前缀的字节一致性

---

### 3. 投机执行 (Speculation) 系统完善（P1）

**Claude Code 实现**：
- `services/PromptSuggestion/speculation.ts` — 992 行完整投机执行 (Speculation) 引擎
- 使用 overlay-fs 实现 copy-on-write 文件隔离
- 写操作写入 overlay 目录，用户确认后 copy-overlay-to-main
- 自动检测 write tools（Edit/Write/NotebookEdit）并拒绝投机
- 与 PromptSuggestion 深度集成：suggestion 展示时自动启动投机

**源码引用**：
- 源码: `services/PromptSuggestion/speculation.ts`（992 行）
- 源码: `services/PromptSuggestion/promptSuggestion.ts`

**Qwen Code 现状**：
- 源码: `packages/core/src/followup/speculation.ts`（564 行）— 有骨架但功能不完整
- 源码: `packages/core/src/followup/overlayFs.ts` — overlay 文件系统存在
- 源码: `packages/core/src/followup/suggestionGenerator.ts`（368 行）
- 缺少：overlay 到主文件系统的复制机制、投机边界检测、write tool 过滤

**相关文章**：
- [Claude Code 提示建议](../tools/claude-code/10-prompt-suggestions.md)
- [启动阶段优化深度对比](./startup-optimization-deep-dive.md)
- [输入队列深度对比](./input-queue-deep-dive.md)

**建议方案**：
1. 完善 `speculation.ts` 的 write tool 过滤（SAFE_READ_ONLY_TOOLS 白名单）
2. 实现 `acceptSpeculation()` 函数，将 overlay 变更应用到主文件系统
3. 实现投机边界检测（遇到非安全工具或 user input 时停止）
4. 增加投机结果的 pipelined suggestion 生成（完成后立即展示下一个建议）

---

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

**相关文章**：
- [记忆系统深度对比](./memory-system-deep-dive.md)

**建议方案**：
1. 实现 SessionMemoryService：管理会话记忆 (Memory) 的提取、存储和检索
2. 实现记忆 (Memory) 提取 hook：在 compact 或 session 结束时自动提取关键信息
3. 实现记忆 (Memory) 检索工具：在新 session 开始时检索相关记忆 (Memory)
4. 记忆 (Memory) 持久化到 `.qwen/` 目录，支持项目级和用户级记忆 (Memory)

---

### 5. Auto Dream 自动记忆 (Memory) 整理（P1）

**Claude Code 实现**：
- `services/autoDream/autoDream.ts` — 自动记忆 (Memory) 整理引擎（325 行）
- 双门控触发：时间门控（默认 24h）+ session 数量门控（默认 5 个 session）
- 使用 forked agent 在后台执行记忆 (Memory) 整理
- `services/autoDream/consolidationPrompt.ts` — 整理 prompt
- `services/autoDream/consolidationLock.ts` — 防止多进程并发整理

**源码引用**：
- 源码: `services/autoDream/autoDream.ts`（325 行）
- 源码: `services/autoDream/consolidationPrompt.ts`
- 源码: `services/autoDream/consolidationLock.ts`

**相关文章**：
- [记忆系统深度对比](./memory-system-deep-dive.md)
- [上下文压缩深度对比](./context-compression-deep-dive.md)

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
| 压缩 (Compression) 策略 | 4 层分层压缩 | 单一阈值压缩 | 显著落后 |
| 子代理 (Subagent) | 支持 fork + 上下文继承 | 仅预定义类型 | 显著落后 |
| 投机执行 (Speculation) | 完整 overlay-fs + cow | 有骨架不完整 | 中等差距 |
| 会话记忆 (Session Memory) | SessionMemory + memdir | 简单笔记工具 | 显著落后 |
| 自动记忆 (Memory) 整理 | Auto Dream | 无 | 缺失 |
| 上下文折叠 (Context Collapse) | History Snip | 无 | 缺失 |
| 工具发现 | ToolSearchTool | 无 | 缺失 |
| 并发控制 | 可配置上限（默认 10） | 无上限 | 小差距 |
| 多代理通信 | SendMessageTool | 无 | 缺失 |
| 文件索引 | FileIndex（fzf 风格） | 依赖 rg/glob | 中等差距 |
