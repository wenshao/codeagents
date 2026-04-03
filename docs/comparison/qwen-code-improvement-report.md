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
| **P0** | [Mid-Turn Queue Drain](./input-queue-deep-dive.md) — Agent 执行中途注入用户输入，无需等整轮结束 [↓](#item-6) | 推理循环内无队列检查 | 中 | [PR#2854](https://github.com/QwenLM/qwen-code/pull/2854) |
| **P0** | [多层上下文压缩](./context-compression-deep-dive.md) — 自动裁剪旧工具结果 + 摘要，用户无需手动 /compress [↓](#item-1) | 仅单一 70% 手动压缩 | 中 | — |
| **P0** | [Fork 子代理](./fork-subagent-deep-dive.md) — 子代理继承完整对话上下文，共享 prompt cache 省 80%+ 费用 [↓](#item-2) | 子代理必须从零开始 | 中 | — |
| **P1** | [Speculation](../tools/claude-code/10-prompt-suggestions.md) — 预测用户下一步并提前执行，Tab 接受零延迟 [↓](#item-3) | 已实现但默认关闭 | 小 | [PR#2525](https://github.com/QwenLM/qwen-code/pull/2525) ✓ |
| **P1** | [会话记忆](./memory-system-deep-dive.md) — 关键决策/文件结构自动提取，新 session 自动注入 [↓](#item-4) | 仅简单笔记工具 | 大 | — |
| **P1** | [Auto Dream](./memory-system-deep-dive.md) — 后台 agent 自动合并去重过时记忆 [↓](#item-5) | 缺失 | 中 | — |
| **P1** | [工具动态发现](./tool-search-deep-dive.md) — 仅加载核心工具，其余按需搜索，省 50%+ token [↓](#item-11) | 全部工具始终加载 | 小 | — |
| **P1** | [智能工具并行](./tool-parallelism-deep-dive.md) — 连续只读工具并行执行，代码探索快 5-10× [↓](#item-7) | 除 Agent 外全部顺序 | 小 | [PR#2864](https://github.com/QwenLM/qwen-code/pull/2864) |
| **P1** | [启动优化](./startup-optimization-deep-dive.md) — TCP 预连接 + 启动期间键盘捕获不丢失 [↓](#item-8) | 完全缺失 | 小 | — |
| **P1** | [指令条件规则](./instruction-loading-deep-dive.md) — 按文件路径匹配加载不同编码规范 [↓](#item-9) | 所有指令始终加载 | 中 | — |
| **P1** | [Commit Attribution](./git-workflow-session-deep-dive.md) — git commit 中标注 AI vs 人类代码贡献比例 [↓](#item-12) | 缺失 | 小 | — |
| **P1** | [会话分支](./git-workflow-session-deep-dive.md) — /branch 从任意节点 fork 对话，探索替代方案 [↓](#item-13) | 缺失 | 中 | — |
| **P2** | [Shell 安全增强](./shell-security-deep-dive.md) — IFS 注入/Unicode 空白/Zsh 命令等 25+ 专项检查 [↓](#item-14) | AST-only 读写分类 | 中 | — |
| **P2** | [MDM 企业策略](./mdm-enterprise-deep-dive.md) — macOS plist + Windows Registry + 远程 API 集中管控 [↓](#item-15) | 无 OS 级策略 | 大 | — |
| **P2** | [API 实时 Token 计数](./token-estimation-deep-dive.md) — 每次 API 调用前精确计数，3 层回退 [↓](#item-16) | 静态 82 种模式匹配 | 中 | — |
| **P2** | [Output Styles](./git-workflow-session-deep-dive.md) — Learning 模式暂停让用户写代码，Explanatory 添加教育洞察 [↓](#item-17) | 缺失 | 中 | — |
| **P2** | [Fast Mode](./cost-fastmode-deep-dive.md) — 同一模型标准/快速推理切换（$5→$30/Mtok），含冷却机制 [↓](#item-18) | 仅指定备用模型 | 小 | — |
| **P2** | [并发 Session](./cost-fastmode-deep-dive.md) — 多终端 PID 追踪 + 后台 Agent 脱附/重附 [↓](#item-21) | 缺失 | 中 | — |
| **P2** | [Git Diff 统计](./git-workflow-session-deep-dive.md) — 编辑后 numstat + hunks 结构化 diff（50 文件/1MB 上限） [↓](#item-22) | 无 git-aware diff | 小 | — |
| **P2** | [文件历史快照](./git-workflow-session-deep-dive.md) — per-file SHA256 备份，按消息粒度恢复（100 个/session） [↓](#item-23) | git-level checkpoint | 中 | — |
| **P2** | [Computer Use](./computer-use-deep-dive.md) — macOS 截图 + 鼠标/键盘 + 剪贴板，通过 MCP 桥接 [↓](#item-19) | 缺失 | 大 | — |
| **P2** | [Deep Link](./deep-link-protocol-deep-dive.md) — `claude-cli://` 一键从浏览器/IDE 启动 Agent + 预填充 prompt [↓](#item-24) | 缺失 | 中 | — |
| **P2** | [Team Memory](./team-memory-deep-dive.md) — 团队共享项目知识 + 29 条 gitleaks 密钥扫描 + ETag 同步 [↓](#item-10) | 缺失 | 大 | — |
| **P2** | Plan 模式 Interview — 先收集信息再制定计划，分离探索和规划阶段 [↓](#item-25) | 无 interview 阶段 | 中 | — |
| **P2** | BriefTool — Agent 向用户发送异步消息（含附件），不中断工具执行 [↓](#item-26) | 缺失 | 中 | — |
| **P2** | [SendMessageTool](./multi-agent-deep-dive.md) — 多代理间消息传递、shutdown 请求、plan 审批 [↓](#item-27) | 缺失 | 中 | — |
| **P2** | FileIndex — fzf 风格模糊文件搜索 + 异步增量索引 [↓](#item-28) | 依赖 rg/glob | 中 | — |
| **P2** | Notebook Edit — Jupyter cell 编辑 + 自动 cell ID 追踪 + 文件历史快照 [↓](#item-29) | 缺失 | 中 | — |
| **P2** | 自定义快捷键 — multi-chord 组合键 + 跨平台适配 + `keybindings.json` 自定义 [↓](#item-30) | 缺失 | 中 | — |
| **P2** | Session Ingress Auth — 远程会话 bearer token 认证（企业多用户环境） [↓](#item-31) | 缺失 | 中 | — |
| **P2** | 企业代理 — CONNECT relay + CA cert 注入 + NO_PROXY 白名单（容器环境） [↓](#item-32) | 缺失 | 大 | — |
| **P2** | ConfigTool — 模型通过工具读写设置（主题/模型/权限等），带 schema 验证 [↓](#item-33) | 仅 /settings 命令 | 小 | — |
| **P2** | 终端主题检测 — OSC 11 查询 dark/light + COLORFGBG 环境变量回退 [↓](#item-34) | 缺失 | 小 | — |
| **P2** | 自动后台化 Agent — 超过阈值自动转后台执行，不阻塞用户交互 [↓](#item-35) | 需显式指定 | 小 | — |
| **P2** | Denial Tracking — 连续权限拒绝自动回退到手动确认模式，防止静默阻塞 [↓](#item-20) | 缺失 | 小 | — |
| **P2** | [队列输入编辑](./input-queue-deep-dive.md) — 排队中的指令可通过方向键弹出到输入框重新编辑 [↓](#item-36) | 缺失 | 小 | — |
| **P2** | 状态栏紧凑布局 — 固定高度不伸缩，最大化终端内容区域 [↓](#item-48) | Footer 占用偏高 | 小 | — |
| **P1** | Channels — Telegram/Discord/iMessage/webhook 推送消息到运行中 session [↓](#item-49) | 缺失 | 中 | — |
| **P1** | GitHub Actions CI — 自动 PR 审查/issue 分类 action [↓](#item-50) | 缺失 | 中 | — |
| **P1** | GitHub Code Review — 多代理自动 PR review + inline 评论 [↓](#item-51) | 缺失 | 大 | — |
| **P1** | HTTP Hooks — Hook 可 POST JSON 到 URL 并接收响应（不仅 shell 命令）[↓](#item-52) | 仅 shell 命令 | 小 | — |
| **P2** | Conditional Hooks — Hook `if` 字段用权限规则语法按工具/路径过滤 [↓](#item-53) | 缺失 | 小 | — |
| **P2** | Transcript Search — 按 `/` 搜索会话记录，`n`/`N` 导航匹配项 [↓](#item-54) | 缺失 | 小 | — |
| **P2** | Bash File Watcher — 检测 formatter/linter 修改已读文件，防止 stale-edit [↓](#item-55) | 缺失 | 小 | — |
| **P2** | /batch 并行操作 — 编排大规模并行变更（多文件/多任务）[↓](#item-56) | 缺失 | 中 | — |
| **P2** | Chrome Extension — 调试 live web 应用（读 DOM/Console/Network）[↓](#item-57) | 缺失 | 中 | — |
| **P3** | 动态状态栏 — 模型/工具可实时更新状态文本 [↓](#item-37) | 仅静态 Footer | 小 | — |
| **P3** | [上下文折叠](./context-compression-deep-dive.md) — History Snip（Claude Code 自身仅 scaffolding，未完整实现） [↓](#item-38) | 缺失 | 大 | — |
| **P3** | 内存诊断 — V8 heap dump + 1.5GB 阈值触发 + leak 建议 + smaps 分析 [↓](#item-39) | 缺失 | 中 | — |
| **P3** | Feature Gates — GrowthBook 远程特性开关 + A/B 测试 + 按事件动态采样 [↓](#item-40) | 缺失 | 中 | — |
| **P3** | DXT/MCPB 插件包 — zip bomb 防护（512MB/文件，1GB 总量，50:1 压缩比限制） [↓](#item-41) | 缺失 | 中 | — |
| **P3** | /security-review — 基于 git diff 的安全审查命令，聚焦漏洞检测 [↓](#item-42) | 缺失 | 小 | — |
| **P3** | Ultraplan — 启动远程 CCR 会话，用更强模型深度规划后回传结果 [↓](#item-43) | 缺失 | 大 | — |
| **P3** | Advisor 顾问模型 — /advisor 配置副模型审查主模型输出，多模型协作 [↓](#item-44) | 缺失 | 中 | — |
| **P3** | Vim 完整实现 — motions + operators + textObjects + transitions 完整体系 [↓](#item-45) | 基础 vim.ts | 中 | — |
| **P3** | 语音模式 — push-to-talk 语音输入 + 流式 STT 转录 + 可重绑快捷键 [↓](#item-46) | 缺失 | 大 | — |
| **P3** | [插件市场](./hook-plugin-extension-deep-dive.md) — 插件发现、安装、版本管理 + 前端 UI [↓](#item-47) | 缺失 | 大 | — |

> 点击改进点名称可跳转到 Deep-Dive 文章；每项的详细说明（缺失后果 + 改进收益 + 建议方案）见 [§三](#三全部改进点详细说明)。

## 三、全部改进点详细说明

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

<a id="item-10"></a>

### 10. Team Memory Sync 组织级记忆同步（P2）

**Claude Code 实现**：`services/teamMemorySync/` 实现 per-repo 级别的组织记忆同步。API 端点 `/api/claude_code/team_memory`，使用 ETag + SHA256 per-key 校验和进行 delta 上传。`fs.watch` 2 秒 debounce 实时推送。29 条 gitleaks 规则在上传前扫描密钥。

**Qwen Code 现状**：缺失。仅有用户私有的简单笔记工具。

**缺失后果**：
- 团队成员各自维护独立记忆——项目知识无法共享，新成员需从零积累
- 同一项目的编码规范、架构决策、已知坑点散落在各人本地——知识孤岛

**改进收益**：
- **团队知识共享**：一人学到的项目知识自动同步给全团队——新成员 session 自动注入团队积累
- **密钥安全**：29 条 gitleaks 规则客户端扫描——敏感凭据永不上传到服务端
- **冲突安全**：ETag + 412 重试机制——多人同时编辑不会丢失数据

**相关文章**：[Team Memory 组织级记忆同步](./team-memory-deep-dive.md)

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

<a id="item-14"></a>

### 14. Shell 安全增强（P2）

**Claude Code 实现**：`tools/BashTool/bashSecurity.ts`（2,592 行）25+ 安全检查管线 + tree-sitter AST 辅助消除误报。覆盖 IFS 注入、Unicode 空白、Zsh 命令、花括号展开等。

**Qwen Code 现状**：AST-only 读写分类（`shellAstParser.ts` 1,248 行）。不覆盖 IFS、Unicode、Zsh 等维度。

**缺失后果**：IFS 注入、Unicode 空白字符等边缘攻击可能绕过只读检测。

**改进收益**：AST 主路径（精确）+ 专项检查补充（IFS/Unicode/Zsh）——覆盖面与精确度兼得。

**相关文章**：[Shell 安全模型](./shell-security-deep-dive.md)

---

<a id="item-15"></a>

### 15. MDM 企业配置（P2）

**Claude Code 实现**：macOS plist（`com.anthropic.claudecode`）+ Windows Registry（`HKLM\SOFTWARE\Policies\ClaudeCode`）+ `managed-settings.d/` drop-in 目录 + 远程 API 策略。5 级 First-Source-Wins 优先级。

**Qwen Code 现状**：无 OS 级策略管理，仅文件配置。

**缺失后果**：企业 IT 无法通过 Jamf/Intune/SCCM 集中管控 AI Agent 配置。

**改进收益**：管理员可锁定权限模式、限制模型选择、强制遥测——满足 SOC 2 / HIPAA 合规。

**相关文章**：[MDM 企业配置管理](./mdm-enterprise-deep-dive.md)

---

<a id="item-16"></a>

### 16. API 实时 Token 计数（P2）

**Claude Code 实现**：`services/tokenEstimation.ts`（495 行）3 层回退：`countTokensWithAPI()` → Haiku fallback → 粗估（4 bytes/token）。支持 4 Provider（Direct/Bedrock/Vertex/Foundry）。VCR fixture 缓存避免重复计数。

**Qwen Code 现状**：静态模式匹配（`tokenLimits.ts` 82 种模型模式）。配置时确定，非运行时计数。

**缺失后果**：上下文窗口占用率估算不准确——可能过早或过晚触发压缩。

**改进收益**：精确 token 计数——压缩触发更准确，避免不必要的压缩或溢出。

**相关文章**：[Token 估算与 Thinking](./token-estimation-deep-dive.md)

---

<a id="item-17"></a>

### 17. Output Styles Learning / Explanatory（P2）

**Claude Code 实现**：`constants/outputStyles.ts`（216 行）内置 Explanatory（"Insight" 教育块）和 Learning（暂停要求用户写代码，`TODO(human)` 占位符）两种模式。

**Qwen Code 现状**：缺失。

**缺失后果**：无法为教学/培训场景定制输出——新人无法通过动手实践学习。

**改进收益**：Learning 模式让 Agent 成为教练——暂停、出题、等待用户实现——适合编程教学。

**相关文章**：[Git 工作流与会话管理](./git-workflow-session-deep-dive.md)

---

<a id="item-18"></a>

### 18. Fast Mode 速度/成本分级（P2）

**Claude Code 实现**：`utils/fastMode.ts`（532 行）同一模型（Opus 4.6）的标准/快速切换。快速模式 $30/$150/Mtok（标准 $5/$25），含冷却机制和重试集成。

**Qwen Code 现状**：`/model --fast` 指定备用快速模型（不是同模型速度切换）。

**缺失后果**：无法在同一模型上灵活切换延迟/成本——时间敏感任务仍用标准速度。

**改进收益**：一键切换推理速度——紧急任务用 Fast，日常用 Standard，两者共享同一上下文。

**相关文章**：[成本追踪与 Fast Mode](./cost-fastmode-deep-dive.md)

---

<a id="item-19"></a>

### 19. Computer Use 桌面自动化（P2）

**Claude Code 实现**：macOS-native Swift 实现（NSWorkspace + TCC + SCContentFilter），支持截图捕获、鼠标/键盘控制、前台应用检测、剪贴板操作。通过 MCP 协议桥接。

**Qwen Code 现状**：缺失。

**缺失后果**：无法跨应用自动化——Agent 只能操作文件和终端，不能操作浏览器/IDE/桌面应用。

**改进收益**：解锁跨应用工作流——如自动在浏览器中验证 UI、从 Figma 提取设计规范、操作数据库 GUI。

---

<a id="item-20"></a>

### 20. Denial Tracking 权限拒绝学习（P2）

**Claude Code 实现**：`utils/permissions/denialTracking.ts`（45 行）记录权限分类器的拒绝/成功次数。连续拒绝超过阈值（`DENIAL_LIMITS`）时自动回退到 prompting 模式——避免分类器陷入"全拒绝"死循环。

**Qwen Code 现状**：缺失。权限拒绝后无学习机制。

**缺失后果**：如果自动审批模式（auto-edit/yolo）连续拒绝某类操作，用户无感知——分类器可能永久阻塞合法操作。

**改进收益**：连续拒绝自动检测 → 回退到手动确认模式——用户看到被拒绝的操作并可手动批准，避免"静默失败"。

---

<a id="item-21"></a>

### 21. 并发 Session 管理（P2）

**Claude Code**：`utils/concurrentSessions.ts` 通过 PID 文件（`~/.claude/sessions/{pid}.json`）追踪多终端会话，支持 `bg`/`daemon` 后台脱附。`countConcurrentSessions()` 扫描并过滤已退出进程。

**Qwen Code**：缺失。无跨终端会话追踪。

**改进收益**：用户可在多终端并行使用 Agent，追踪后台任务状态，脱附/重附会话。

---

<a id="item-22"></a>

### 22. Git Diff 统计（P2）

**Claude Code**：`utils/gitDiff.ts` 两阶段 diff——`git diff --numstat` 快速探测 + 完整 hunks。限制：50 文件、1MB/文件、400 行/文件。merge/rebase 期间跳过。

**Qwen Code**：依赖 `simple-git` npm 包，无结构化 diff 统计。

**改进收益**：编辑后展示清晰的按文件行数统计——用户在 commit 前了解变更影响范围。

---

<a id="item-23"></a>

### 23. 文件历史快照（P2）

**Claude Code**：`utils/fileHistory.ts` 编辑前自动备份（SHA256 哈希 + mtime），按消息 ID 创建快照（上限 100 个/session）。支持按消息粒度恢复。

**Qwen Code**：Git worktree checkpoint（整体快照），粒度更粗。

**改进收益**：比 git-level 更细粒度的恢复——可回滚到任意消息时刻，而非仅 checkpoint 时刻。

---

<a id="item-24"></a>

### 24. Deep Link 协议（P2）

**Claude Code**：`utils/deepLink/` 实现 `claude-cli://` URI scheme，支持 `q`（prompt）、`cwd`（目录）、`repo`（GitHub slug）参数。自动检测 10+ 终端（iTerm/Ghostty/Kitty 等），3 平台协议注册。

**Qwen Code**：缺失。

**改进收益**：从浏览器/IDE/Slack 一键启动 Agent 并预填充 prompt——大幅降低上下文切换成本。

**相关文章**：[Deep Link 协议](./deep-link-protocol-deep-dive.md)

---

<a id="item-25"></a>

### 25. Plan 模式 Interview（P2）

**Claude Code**：`EnterPlanMode` 支持 interview 阶段——先通过提问收集需求，再制定实施计划。分离"探索"和"执行"。

**Qwen Code**：有 `exitPlanMode` 工具但无 interview 阶段。

**改进收益**：复杂任务前先充分理解需求——减少返工。

---

<a id="item-26"></a>

### 26. BriefTool（P2）

**Claude Code**：`tools/BriefTool/` 允许 Agent 向用户发送异步消息（含附件），不中断工具执行。用于 proactive status 更新。

**Qwen Code**：缺失。Agent 只能通过工具结果与用户通信。

**改进收益**：长时间任务中用户可收到进度更新——"已完成 3/5 个文件修改"。

---

<a id="item-27"></a>

### 27. SendMessageTool（P2）

**Claude Code**：`tools/SendMessageTool/` 支持队友间通信（单播/广播）、shutdown 请求、plan approval。路由支持 name/UDS/bridge。

**Qwen Code**：缺失。Arena 模式下无跨代理通信。

**改进收益**：多代理协作时可协调任务——Leader 分配工作后 Worker 通过消息报告进度。

**相关文章**：[多代理系统](./multi-agent-deep-dive.md)

---

<a id="item-28"></a>

### 28. FileIndex（P2）

**Claude Code**：`native-ts/file-index/` 实现 fzf 风格模糊文件搜索，支持异步增量索引。

**Qwen Code**：依赖 `rg`/`glob`，无模糊搜索。

**改进收益**：大型仓库中快速定位文件——不需要精确文件名。

---

<a id="item-29"></a>

### 29. Notebook Edit（P2）

**Claude Code**：`tools/NotebookEditTool/` 支持 Jupyter notebook cell 编辑——插入/修改 code/markdown cell，自动追踪 cell ID，集成文件历史快照。

**Qwen Code**：缺失。

**改进收益**：数据科学工作流原生支持——直接操作 `.ipynb` 文件。

---

<a id="item-30"></a>

### 30. 自定义快捷键（P2）

**Claude Code**：`keybindings/` 支持 multi-chord 组合键（如 `Ctrl+K Ctrl+S`）、平台适配（Windows VT mode 检测）、`~/.claude/keybindings.json` 自定义。

**Qwen Code**：缺失。仅有 IDE keybindings.json 终端集成配置。

**改进收益**：高级用户自定义操作快捷方式——提升重复操作效率。

---

<a id="item-31"></a>

### 31. Session Ingress Auth（P2）

**Claude Code**：`utils/sessionIngressAuth.ts` 提供 bearer token 远程会话认证，支持文件描述符和 well-known 文件方式。

**Qwen Code**：缺失。

**改进收益**：企业多用户环境下安全的远程 Agent 访问——支持 CCR 式部署。

---

<a id="item-32"></a>

### 32. 企业代理支持（P2）

**Claude Code**：`upstreamproxy/` 提供 CONNECT-to-WebSocket relay，CA cert 链注入，NO_PROXY 白名单（覆盖 RFC1918、Anthropic API、GitHub、包注册表）。失败时 fail-open。

**Qwen Code**：缺失。

**改进收益**：企业网络（代理/VPN/防火墙）环境下正常使用——无需手动配置代理。

---

<a id="item-33"></a>

### 33. ConfigTool（P2）

**Claude Code**：`tools/ConfigTool/` 允许模型通过工具 get/set 设置（主题、模型、权限等），带 schema 验证。

**Qwen Code**：设置通过 `/settings` 命令，模型无法程序化修改。

**改进收益**：模型可根据任务自动调整设置——如切换到适合当前任务的模型。

---

<a id="item-34"></a>

### 34. 终端主题检测（P2）

**Claude Code**：`utils/systemTheme.ts` 通过 OSC 11 查询终端背景色 + `$COLORFGBG` 环境变量回退，解析 `auto` 主题为具体 dark/light。

**Qwen Code**：缺失。

**改进收益**：终端 dark/light 模式自动适配——代码高亮和 UI 颜色与终端背景匹配。

---

<a id="item-35"></a>

### 35. 自动后台化 Agent（P2）

**Claude Code**：`getAutoBackgroundMs()` 基于 GrowthBook 门控，超过阈值的 Agent 自动转后台执行。

**Qwen Code**：需显式指定 `run_in_background`。

**改进收益**：长时间 Agent 任务自动后台化——不阻塞用户交互。

---

<a id="item-36"></a>

### 36. 队列输入编辑（P2）

**Claude Code**：`utils/messageQueueManager.ts` 的 `popAllEditable()` 允许用户按 Escape 将队列中的可编辑命令弹出到输入框重新编辑。队列在 prompt 下方实时可见。

**Qwen Code**：缺失。排队输入后无法修改。

**缺失后果**：用户在 Agent 执行中输入了错误指令但无法撤回——只能等 Agent 处理完错误指令后再纠正。

**改进收益**：排队中的输入可重新编辑——发现输入错误时按 Escape 弹回修改，避免浪费一轮执行。

**相关文章**：[输入队列与中断机制](./input-queue-deep-dive.md)

---

<a id="item-37"></a>

### 37. 动态状态栏（P3）

**Claude Code**：`AppState.statusLineText` 允许模型/工具实时更新状态文本（如"正在分析 5 个文件..."）。

**Qwen Code**：仅静态 Footer。

**改进收益**：用户实时了解 Agent 当前在做什么——减少等待焦虑。

---

<a id="item-38"></a>

### 38. 上下文折叠 History Snip（P3）

**Claude Code**：`feature('HISTORY_SNIP')` 门控，目前仅 scaffolding（SnipTool 有 lazy require 占位，无完整实现）。已有 `collapseReadSearch.ts` 的 UI 级消息折叠。

**Qwen Code**：缺失。

**说明**：Claude Code 自身未完整实现，列为参考方向。

---

<a id="item-39"></a>

### 39. 内存诊断（P3）

**Claude Code**：`utils/heapDumpService.ts` 在 1.5GB 阈值触发 V8 heap snapshot，解析 Linux smaps_rollup，分析内存增长率并给出 leak 建议。

**Qwen Code**：缺失。

**改进收益**：长会话内存泄漏自动检测和诊断——帮助开发者定位 Agent 的内存问题。

---

<a id="item-40"></a>

### 40. Feature Gates（P3）

**Claude Code**：`services/analytics/growthbook.ts` 集成 GrowthBook 远程特性开关 + A/B 测试 + 按事件动态采样率。

**Qwen Code**：缺失。

**改进收益**：新功能渐进式灰度发布——降低全量上线风险。

---

<a id="item-41"></a>

### 41. DXT/MCPB 插件包格式（P3）

**Claude Code**：支持 `.dxt`/`.mcpb` 打包格式，含 zip bomb 防护（512MB/文件、1GB 总量、50:1 压缩比限制）。

**Qwen Code**：缺失。

**改进收益**：安全的插件分发——单文件安装 MCP 服务器 + 依赖。

---

<a id="item-42"></a>

### 42. /security-review 安全审查（P3）

**Claude Code**：基于 frontmatter 模板的安全审查命令，聚焦 git diff 中的漏洞检测。

**Qwen Code**：缺失。

**改进收益**：代码提交前自动安全扫描——减少安全漏洞。

---

<a id="item-43"></a>

### 43. Ultraplan 远程计划探索（P3）

**Claude Code**：`/ultraplan` 启动远程 CCR 会话，使用更强模型进行深度规划后回传结果。

**Qwen Code**：缺失。依赖远程执行基础设施。

---

<a id="item-44"></a>

### 44. Advisor 顾问模型（P3）

**Claude Code**：`/advisor` 配置副模型（如 Opus）审查主模型（如 Sonnet）输出。`server_tool_use` 方式，Backend 确定审查模型。

**Qwen Code**：缺失。需多模型同时调用能力。

---

<a id="item-45"></a>

### 45. Vim 完整实现（P3）

**Claude Code**：`keybindings/` 含 `motions.ts`、`operators.ts`、`textObjects.ts`、`transitions.ts` 完整 Vim 键绑定系统。

**Qwen Code**：有基础 `vim.ts` 实现。

**改进收益**：Vim 用户获得完整的 modal editing 体验。

---

<a id="item-46"></a>

### 46. 语音模式（P3）

**Claude Code**：`commands/voice/` + push-to-talk 快捷键 + 流式 STT 转录。快捷键可通过 `keybindings.json` 重绑。

**Qwen Code**：缺失。需音频捕获 + STT 基础设施。

---

<a id="item-47"></a>

### 47. 插件市场（P3）

**Claude Code**：支持从官方 marketplace 安装插件（hooks/commands/agents/output styles/MCP），自动更新。含安装状态追踪（pending → installing → installed/failed）。

**Qwen Code**：缺失。需插件发现、安装、版本管理基础设施。

**相关文章**：[Hook 与插件扩展](./hook-plugin-extension-deep-dive.md)

---

<a id="item-48"></a>

### 48. 状态栏紧凑布局（P2）

**Claude Code**：`PromptInputFooterLeftSide.tsx` 注释明确"height so the footer never grows/shrinks and shifts scroll content"——状态栏固定高度，不随内容伸缩。`StatusLine` 组件仅在需要时显示，默认隐藏。

**Qwen Code**：Footer 始终显示多项信息（exit 提示 / 模式指示 / sandbox / debug / context usage），占用终端空间偏高。

**缺失后果**：终端高度有限时（如笔记本 + 分屏），Footer 挤压内容区域——Agent 输出和用户输入可见行数减少。

**改进收益**：紧凑 Footer 最大化内容区域——在小终端上也能舒适工作。

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

<a id="item-53"></a>

### 53. Conditional Hooks（P2）

**Claude Code**：Hooks 支持 `if` 字段，使用权限规则语法（如 `Bash(git:*)` 或 `Edit(src/**)`）过滤何时执行。

**Qwen Code**：Hooks 无条件过滤——注册后所有匹配事件都触发。

**改进收益**：精细控制 Hook 触发范围——如"仅在 git 命令时运行 pre-commit 检查"。

---

<a id="item-54"></a>

### 54. Transcript Search（P2）

**Claude Code**：按 `/` 进入搜索模式，`n`/`N` 在匹配项间导航。支持 transcript 模式下的会话内搜索。

**Qwen Code**：缺失。

**改进收益**：长会话中快速定位之前的讨论——"刚才说的那个 API 端点是什么来着？"

---

<a id="item-55"></a>

### 55. Bash File Watcher（P2）

**Claude Code**：检测 formatter/linter 在 Agent 读取文件后修改了该文件（如 prettier 自动格式化），发出警告防止 stale-edit 错误。

**Qwen Code**：缺失。

**缺失后果**：Agent 读取文件后 formatter 自动修改 → Agent 基于旧内容编辑 → 冲突或丢失格式化。

**改进收益**：自动检测文件被外部修改 → 提醒 Agent 重新读取——避免 stale-edit 导致的编辑冲突。

---

<a id="item-56"></a>

### 56. /batch 并行操作（P2）

**Claude Code**：`/batch` bundled 命令，编排大规模并行变更——多文件/多任务同时处理。

**Qwen Code**：缺失。

**改进收益**：批量重构场景（如 "将所有 class 组件迁移到 hooks"）可并行处理——速度倍增。

---

<a id="item-57"></a>

### 57. Chrome Extension 浏览器调试（P2）

**Claude Code**：Chrome 扩展通过 MCP 协议桥接，提供 `read_page`（DOM）、`read_console_messages`（Console）、`read_network_requests`（Network）、`navigate`、`switch_browser` 等工具。通过 `/web-setup` 配置。

**Qwen Code**：缺失。

**缺失后果**：前端调试时 Agent 无法"看到"浏览器中的实际渲染结果/错误日志。

**改进收益**：Agent 可直接读取浏览器 DOM 和控制台错误——前端调试效率大幅提升。

---

## 四、架构差异总结

| 维度 | Claude Code | Qwen Code | 差距评估 | 进展 |
|------|-------------|-----------|----------|------|
| **Mid-Turn Queue Drain** | `query.ts` 工具批次间 drain | 无 | 显著落后 | [PR#2854](https://github.com/QwenLM/qwen-code/pull/2854) |
| 压缩 (Compression) 策略 | 4 层分层压缩 | 单一阈值压缩 | 显著落后 | — |
| 子代理 (Subagent) | 支持 fork + 上下文继承 | 仅预定义类型 | 显著落后 | — |
| **智能工具并行** | Kind-based batching（默认 10 并发） | Agent 并发 / 其他顺序 | 中等差距 | [PR#2864](https://github.com/QwenLM/qwen-code/pull/2864) |
| 投机执行 (Speculation) | 完整 overlay-fs + cow（991 行） | v0.15.0 已完整实现（563 行），默认关闭 | 小差距 | [PR#2525](https://github.com/QwenLM/qwen-code/pull/2525) ✓ |
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
| Commit Attribution | Co-Authored-By 追踪 | 无 | 缺失 | — |
| 会话分支 | /branch 对话分叉 | 无 | 缺失 | — |
| Output Styles | Learning / Explanatory 模式 | 无 | 缺失 | — |
| Fast Mode | 速度/成本分级推理 | 无 | 缺失 | — |
| 并发 Session | 多终端 PID 追踪 + 后台脱附 | 无 | 缺失 | — |
| Git Diff 统计 | 结构化 diff + 按文件统计 | 无 git-aware stats | 中等差距 | — |
| 文件历史快照 | per-file SHA256 + 按消息恢复 | checkpoint（git 级） | 小差距 | — |
| Session Ingress Auth | bearer token 远程认证 | 无 | 缺失 | — |
| Computer Use | macOS 桌面自动化 | 无 | 缺失 | — |
| Deep Link | `claude-cli://` URI scheme | 无 | 缺失 | — |
| Notebook Edit | Jupyter cell 编辑 | 无 | 缺失 | — |
| Team Memory | 组织级记忆同步 | 无 | 缺失 | — |
| 自定义快捷键 | multi-chord + keybindings.json | 无 | 缺失 | — |
| 企业代理 | CONNECT relay + CA cert 注入 | 无 | 缺失 | — |
| 终端主题 | OSC 11 dark/light 检测 | 无 | 缺失 | — |
| Denial Tracking | 权限拒绝学习 + 自动回退 | 无 | 缺失 | — |

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
| 成本与 Fast Mode | [成本追踪与 Fast Mode](./cost-fastmode-deep-dive.md) |
| Git 工作流与会话 | [Git 工作流与会话管理](./git-workflow-session-deep-dive.md) |
| 工具动态发现 | [工具搜索与延迟加载](./tool-search-deep-dive.md) |
| Team Memory | [组织级记忆同步](./team-memory-deep-dive.md) |
| Computer Use | [桌面自动化](./computer-use-deep-dive.md) |
| Deep Link | [协议处理与终端启动](./deep-link-protocol-deep-dive.md) |
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
