# Qwen Code 改进建议报告

> 基于对 Claude Code（源码分析，56 个顶层模块，~1800 文件）与 Qwen Code（开源源码，~500 文件）的系统性源码对比分析。
>
> 如需查阅源码，可参考本地仓库（不在本文档库中）：
> - Claude Code: `../claude-code/`（源码快照）
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

| 优先级 | 改进点 | Qwen Code 现状 | 难度 | 进展 |
|:------:|--------|----------------|:----:|------|
| **P0** | [Mid-Turn Queue Drain](./input-queue-deep-dive.md)（工具批次间注入用户输入） | 推理循环内无队列检查 | 中 | PR [#2854](https://github.com/QwenLM/qwen-code/pull/2854) open |
| **P0** | [多层上下文压缩](./context-compression-deep-dive.md)（4 层 vs 单一 70% 阈值） | 仅 ChatCompressionService | 中 | — |
| **P0** | [Fork 子代理](./fork-subagent-deep-dive.md)（隐式 fork + 上下文继承 + prompt cache 共享） | 仅预定义 subagent_type | 中 | — |
| **P1** | [Speculation](../tools/claude-code/10-prompt-suggestions.md) 默认启用 | v0.15.0 已实现，默认关闭 | 小 | PR [#2525](https://github.com/QwenLM/qwen-code/pull/2525) merged |
| **P1** | [会话记忆](./memory-system-deep-dive.md)（SessionMemory + memdir 跨 session 检索） | 仅简单笔记工具 | 大 | — |
| **P1** | Auto Dream（自动记忆整理，24h + 5 session 门控） | 缺失 | 中 | — |
| **P1** | 上下文折叠（History Snip，span 级摘要） | 缺失 | 大 | — |
| **P1** | 工具动态发现（ToolSearchTool，延迟加载 + 搜索） | 缺失 | 小 | — |
| **P1** | [智能工具并行](./tool-parallelism-deep-dive.md)（Kind-based Batching，默认 10 并发） | Agent 并发 / 其他顺序 | 小 | PR [#2864](https://github.com/QwenLM/qwen-code/pull/2864) open |
| **P1** | [启动优化](./startup-optimization-deep-dive.md)（API Preconnect + Early Input Capture） | 完全缺失 | 小 | — |
| **P1** | [指令条件规则](./instruction-loading-deep-dive.md)（frontmatter `paths:` + 惰加载） | 无 frontmatter / 条件加载 | 中 | — |
| **P2** | [Shell 安全增强](./shell-security-deep-dive.md)（25+ 检查 vs AST-only 读写分类） | 不覆盖 IFS/Unicode/Zsh | 中 | — |
| **P2** | [MDM 企业策略](./mdm-enterprise-deep-dive.md)（plist + Registry + 远程 API） | 无 OS 级策略 | 大 | — |
| **P2** | [API 实时 Token 计数](./token-estimation-deep-dive.md)（vs 静态 82 模式匹配） | 静态模式匹配 | 中 | — |
| **P2** | Plan 模式 Interview Phase | 无 interview 阶段 | 中 | — |
| **P2** | BriefTool（异步消息 + 附件） | 缺失 | 中 | — |
| **P2** | [SendMessageTool](./multi-agent-deep-dive.md)（多代理通信） | 缺失 | 中 | — |
| **P2** | FileIndex（fzf 风格模糊搜索） | 依赖 rg/glob | 中 | — |
| **P2** | ConfigTool（工具化设置读写） | 仅 /settings 命令 | 小 | — |
| **P2** | 自动后台化 Agent（超时转后台） | 需显式指定 | 小 | — |
| **P3** | /security-review 安全审查命令 | 缺失 | 小 | — |
| **P3** | Ultraplan 远程计划探索 | 缺失 | 大 | — |
| **P3** | Advisor 顾问模型 | 缺失 | 中 | — |
| **P3** | Vim 完整实现（motions/operators/textObjects） | 基础 vim.ts | 中 | — |
| **P3** | 语音模式 | 缺失 | 大 | — |
| **P3** | [插件市场](./hook-plugin-extension-deep-dive.md) | 缺失 | 大 | — |

> 详细的 Claude Code 实现机制和建议方案见下文 Top 5 详细说明及各 [Deep-Dive 文章](#五相关-deep-dive-文章)。

## 三、Top 5 改进点详细说明

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

## 四、架构差异总结

| 维度 | Claude Code | Qwen Code | 差距评估 | 进展 |
|------|-------------|-----------|----------|------|
| **Mid-Turn Queue Drain** | `query.ts` 工具批次间 drain | 无 | 显著落后 | PR [#2854](https://github.com/QwenLM/qwen-code/pull/2854) open |
| 压缩 (Compression) 策略 | 4 层分层压缩 | 单一阈值压缩 | 显著落后 | — |
| 子代理 (Subagent) | 支持 fork + 上下文继承 | 仅预定义类型 | 显著落后 | — |
| **智能工具并行** | Kind-based batching（默认 10 并发） | Agent 并发 / 其他顺序 | 中等差距 | PR [#2864](https://github.com/QwenLM/qwen-code/pull/2864) open |
| 投机执行 (Speculation) | 完整 overlay-fs + cow（991 行） | v0.15.0 已完整实现（563 行），默认关闭 | 小差距 | PR [#2525](https://github.com/QwenLM/qwen-code/pull/2525) merged |
| 启动优化 | API Preconnect + Early Input | 无 | 缺失 | — |
| CLAUDE.md 条件规则 | frontmatter `paths:` + 惰加载 | 无 | 中等差距 | — |
| 会话记忆 (Session Memory) | SessionMemory + memdir | 简单笔记工具 | 显著落后 | — |
| 自动记忆 (Memory) 整理 | Auto Dream | 无 | 缺失 | — |
| 上下文折叠 (Context Collapse) | History Snip | 无 | 缺失 | — |
| Shell 安全增强 | 25+ 检查 + tree-sitter | AST-only 读写分类 | 中等差距 | — |
| MDM 企业策略 | plist + Registry + 远程 API | 无 | 缺失 | — |
| Token 实时计数 | API 计数 + VCR 缓存 | 静态模式匹配 | 中等差距 | — |
| 工具发现 | ToolSearchTool | 无 | 缺失 | — |
| 多代理通信 | SendMessageTool | 无 | 缺失 | — |
| 文件索引 | FileIndex（fzf 风格） | 依赖 rg/glob | 中等差距 | — |

## 五、相关 Deep-Dive 文章

### 对比分析（Claude Code vs Qwen Code）

| 改进领域 | 文章 |
|----------|------|
| Mid-Turn Queue Drain | [输入队列与中断机制](./input-queue-deep-dive.md) |
| 上下文压缩 | [上下文压缩算法](./context-compression-deep-dive.md) |
| Fork 子代理 | [Fork 子代理](./fork-subagent-deep-dive.md) |
| 智能工具并行 | [工具并行执行](./tool-parallelism-deep-dive.md) |
| Shell 安全 | [Shell 安全模型](./shell-security-deep-dive.md) |
| 启动优化 | [启动阶段优化](./startup-optimization-deep-dive.md) |
| 指令文件加载 | [指令文件加载](./instruction-loading-deep-dive.md) |
| MDM 企业配置 | [MDM 企业配置管理](./mdm-enterprise-deep-dive.md) |
| 遥测架构 | [遥测架构](./telemetry-architecture-deep-dive.md) |
| Token 估算 | [Token 估算与 Thinking](./token-estimation-deep-dive.md) |
| 会话记忆 | [记忆系统](./memory-system-deep-dive.md) |
| 多代理通信 | [多代理系统](./multi-agent-deep-dive.md) |
| 插件/Hook 扩展 | [Hook 与插件扩展](./hook-plugin-extension-deep-dive.md) |
| MCP 集成 | [MCP 集成](./mcp-integration-deep-dive.md) |
| 功能矩阵 | [功能对比矩阵](./features.md) |

### Claude Code 源码文档

| 领域 | 文章 |
|------|------|
| 架构总览 | [技术架构（22 节）](../tools/claude-code/03-architecture.md) |
| 工具系统 | [工具系统](../tools/claude-code/04-tools.md) |
| 多代理 / Swarm | [多代理系统](../tools/claude-code/09-multi-agent.md) |
| Prompt Suggestions | [Prompt Suggestions + Speculation](../tools/claude-code/10-prompt-suggestions.md) |
| 终端渲染 | [终端渲染与防闪烁](../tools/claude-code/11-terminal-rendering.md) |
| 设置与安全 | [设置与安全](../tools/claude-code/06-settings.md) |
| 会话与记忆 | [会话与记忆](../tools/claude-code/07-session.md) |
