# Qwen Code 改进建议报告

> 基于对 Claude Code（源码分析，56 个顶层模块，~1800 文件）与 Qwen Code（开源源码，~500 文件）的系统性源码对比分析。
>
> **相关报告**：
> - [Gemini CLI 上游 backport 报告（53 项）](./qwen-code-gemini-upstream-report.md)——Qwen Code 上游的可 backport 改进
> - [Codex CLI 对标改进报告（25 项）](./qwen-code-codex-improvements.md)——沙箱、Apply Patch、Feature Flag、网络代理等
> - [OpenCode 对标改进报告（27 项）](./qwen-code-opencode-improvements.md)——Provider 系统、Plugin 插件、Snapshot 快照等
> - [/review 功能分析](./qwen-code-review-improvements.md)——审查功能 5 方对比（含 gstack）

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
| **P0** | [[Mid-Turn Queue Drain](./command-queue-orchestration-deep-dive.md)](./input-queue-deep-dive.md) — Agent 执行中途注入用户输入，无需等整轮结束 [↓](./qwen-code-improvement-report-p0-p1-core.md#item-6) | 推理循环内无队列检查 | 中 | [PR#2854](https://github.com/QwenLM/qwen-code/pull/2854) ✓ |
| **P0** | [多层上下文压缩](./context-compression-deep-dive.md) — 自动裁剪旧工具结果 + 摘要，用户无需手动 /compress [↓](./qwen-code-improvement-report-p0-p1-core.md#item-1) | 仅单一 70% 手动压缩 | 中 | [PR#3006](https://github.com/QwenLM/qwen-code/pull/3006) ✓（L2 microcompaction） |
| **P0** | [Fork Subagent](./fork-subagent-deep-dive.md) — Subagent 继承完整对话上下文，共享 prompt cache 省 80%+ 费用 [↓](./qwen-code-improvement-report-p0-p1-core.md#item-2) | Subagent 必须从零开始 | 中 | [PR#2936](https://github.com/QwenLM/qwen-code/pull/2936) ✓ / [Roadmap#2409](https://github.com/QwenLM/qwen-code/issues/2409) |
| **P0** | [会话崩溃恢复与中断检测](./crash-recovery-deep-dive.md) — 3 种中断状态检测 + 合成续行 + 全量恢复 [↓](./qwen-code-improvement-report-p0-p1-engine.md#item-7) | 无崩溃恢复 | 大 | — |
| **P1** | [Speculation](../tools/claude-code/10-prompt-suggestions.md) — 预测用户下一步并提前执行，Tab 接受零延迟 [↓](./qwen-code-improvement-report-p0-p1-core.md#item-3) | 已实现但默认关闭 | 小 | [PR#2525](https://github.com/QwenLM/qwen-code/pull/2525) ✓ |
| **P1** | [会话记忆](./memory-system-deep-dive.md) — 关键决策/文件结构自动提取，新 session 自动注入 [↓](./qwen-code-improvement-report-p0-p1-core.md#item-4) | 仅简单笔记工具 | 大 | [PR#3087](https://github.com/QwenLM/qwen-code/pull/3087) ✓ |
| **P1** | [Auto Dream](./memory-system-deep-dive.md) — 后台 agent 自动合并去重过时记忆 [↓](./qwen-code-improvement-report-p0-p1-core.md#item-5) | 缺失 | 中 | [PR#3087](https://github.com/QwenLM/qwen-code/pull/3087) ✓（managed auto-memory + auto-dream） |
| **P1** | [Nudge 驱动的闭环学习](./closed-learning-loop-deep-dive.md) — 双计数器 + 后台 review 子代理 + 冻结快照 + 自修补（Hermes Agent 参考） [↓](./qwen-code-improvement-report-p0-p1-core.md#item-14) | 被动记忆（无 nudge） | 中 | [PR#3087](https://github.com/QwenLM/qwen-code/pull/3087) ✓（部分覆盖） |
| **P1** | [工具动态发现](./tool-search-deep-dive.md) — 仅加载核心工具，其余按需搜索，省 50%+ token [↓](./qwen-code-improvement-report-p0-p1-core.md#item-11) | 全部工具始终加载 | 小 | — |
| **P1** | [智能工具并行](./tool-parallelism-deep-dive.md) — 连续只读工具并行执行，代码探索快 5-10× [↓](./qwen-code-improvement-report-p0-p1-core.md#item-7) | 除 Agent 外全部顺序 | 小 | [PR#2864](https://github.com/QwenLM/qwen-code/pull/2864) ✓ / [Roadmap#2516](https://github.com/QwenLM/qwen-code/issues/2516) |
| **P1** | [启动优化](./startup-optimization-deep-dive.md) — TCP preconnect + 启动期间键盘捕获不丢失 [↓](./qwen-code-improvement-report-p0-p1-core.md#item-8) | preconnect 开发中 / early input ✓ | 小 | [PR#3085](https://github.com/QwenLM/qwen-code/pull/3085) ✗（关闭，拆分）/ [PR#3318](https://github.com/QwenLM/qwen-code/pull/3318)（preconnect，open）/ [PR#3319](https://github.com/QwenLM/qwen-code/pull/3319) ✓（early input，2026-04-18 合并）/ [PR#3232](https://github.com/QwenLM/qwen-code/pull/3232) ✓（profiler） |
| **P1** | [指令条件规则](./instruction-loading-deep-dive.md) — 按文件路径匹配加载不同编码规范 [↓](./qwen-code-improvement-report-p0-p1-core.md#item-9) | 所有指令始终加载 | 中 | [PR#3339](https://github.com/QwenLM/qwen-code/pull/3339) ✓ / [Roadmap#125](https://github.com/QwenLM/qwen-code/issues/125) |
| **P1** | [Commit Attribution](./git-workflow-session-deep-dive.md) — git commit 中标注 AI vs 人类代码贡献比例 [↓](./qwen-code-improvement-report-p0-p1-core.md#item-12) | 缺失 | 小 | [PR#3115](https://github.com/QwenLM/qwen-code/pull/3115) |
| **P1** | [会话分支](./git-workflow-session-deep-dive.md) — /branch 从任意节点 fork 对话，探索替代方案 [↓](./qwen-code-improvement-report-p0-p1-core.md#item-13) | 缺失 | 中 | [PR#3022](https://github.com/QwenLM/qwen-code/pull/3022) ✗（已关闭）/ [PR#3292](https://github.com/QwenLM/qwen-code/pull/3292)（后续 session rewind + restore flows） |
| **P1** | GitHub Actions CI — 自动 PR 审查/issue 分类 action [↓](./qwen-code-improvement-report-p0-p1-platform.md#item-1) | 缺失 | 中 | — |
| **P1** | GitHub Code Review — 多 Agent自动 PR review + inline 评论 [↓](./qwen-code-improvement-report-p0-p1-platform.md#item-2) | **已实现**（内置 `/review` skill，5 agent 并行 + Create Review API） | — | [PR#2348](https://github.com/QwenLM/qwen-code/pull/2348) ✓ / [PR#2687](https://github.com/QwenLM/qwen-code/pull/2687) ✓ / [PR#2932](https://github.com/QwenLM/qwen-code/pull/2932) ✓ / [PR#3276](https://github.com/QwenLM/qwen-code/pull/3276)（弱模型并行强化） / [Roadmap#742](https://github.com/QwenLM/qwen-code/issues/742) |
| **P1** | [HTTP Hooks](./http-hooks-deep-dive.md) — Hook 可 POST JSON 到 URL 并接收响应（不仅 shell 命令）[↓](./qwen-code-improvement-report-p0-p1-platform.md#item-3) | 仅 shell 命令 | 小 | [PR#2827](https://github.com/QwenLM/qwen-code/pull/2827) ✓ |
| **P1** | [Structured Output](./structured-output-deep-dive.md) — `--json-schema` 强制 JSON Schema 验证输出 [↓](./qwen-code-improvement-report-p0-p1-platform.md#item-4) | 缺失 | 小 | — |
| **P1** | [Agent SDK 增强](./agent-sdk-python-deep-dive.md) — Python SDK + 流式回调 + 工具审批回调（Qwen 仅 TS SDK）[↓](./qwen-code-improvement-report-p0-p1-platform.md#item-5) | 仅 TypeScript SDK | 中 | — |
| **P1** | [Bare Mode](./bare-mode-deep-dive.md) — `--bare` 跳过所有自动发现，CI/脚本最快启动 [↓](./qwen-code-improvement-report-p0-p1-platform.md#item-6) | 缺失 | 小 | — |
| **P1** | [Remote Control Bridge](./remote-control-bridge-deep-dive.md) — 从手机/浏览器驱动本地终端 session [↓](./qwen-code-improvement-report-p0-p1-platform.md#item-7) | Channels 平台已合并（IM 路径），Web/QR 路径 review 中 | 大 | [PR#2628](https://github.com/QwenLM/qwen-code/pull/2628) ✓（Telegram/WeChat/DingTalk） / [PR#2330](https://github.com/QwenLM/qwen-code/pull/2330)（Web UI + QR code） |
| **P1** | [/teleport 跨端双向迁移](./teleport-session-migration-deep-dive.md) — Web session → 终端 session 双向迁移 [↓](./qwen-code-improvement-report-p0-p1-platform.md#item-8) | 缺失 | 大 | — |
| **P1** | [GitLab CI/CD](./gitlab-ci-cd-deep-dive.md) — 官方 GitLab pipeline 集成 [↓](./qwen-code-improvement-report-p0-p1-platform.md#item-9) | 缺失 | 中 | — |
| **P1** | [流式工具执行流水线](./streaming-tool-execution-deep-dive.md) — API 流式返回 tool_use 时立即开始执行，不等完整响应 [↓](./qwen-code-improvement-report-p0-p1-engine.md#item-1) | 等完整响应后执行 | 中 | — |
| **P1** | [文件读取缓存 + 批量并行 I/O](./file-read-cache-deep-dive.md) — 1000 条 LRU + mtime 失效 + 32 批并行 [↓](./qwen-code-improvement-report-p0-p1-engine.md#item-2) | 无缓存，顺序读取 | 小 | — |
| **P1** | [记忆/附件异步prefetch](./memory-prefetch-deep-dive.md) — 工具执行期间并行搜索相关记忆 [↓](./qwen-code-improvement-report-p0-p1-engine.md#item-3) | 无prefetch | 中 | — |
| **P1** | [Token Budget 续行与自动交接](./token-budget-continuation-deep-dive.md) — 90% 续行 + 递减检测 + 分层压缩回退 [↓](./qwen-code-improvement-report-p0-p1-engine.md#item-4) | 70% 一次性压缩 | 中 | — |
| **P1** | 同步 I/O 异步化 — readFileSync/statSync 替换为 async，解阻塞事件循环 [↓](./qwen-code-improvement-report-p0-p1-engine.md#item-5) | 多处 readFileSync | 中 | — |
| **P1** | [Prompt Cache 分段与工具稳定排序](./prompt-cache-optimization-deep-dive.md) — static/dynamic 分界 + 内置工具前缀 + schema 锁定 [↓](./qwen-code-improvement-report-p0-p1-engine.md#item-6) | 无分段缓存 | 中 | — |
| **P1** | [API 指数退避与降级重试](./api-retry-fallback-deep-dive.md) — 10 次退避 + 529 模型降级 + 401 token 刷新 [↓](./qwen-code-improvement-report-p0-p1-engine.md#item-8) | 仅配置重试次数 | 中 | [PR#3246](https://github.com/QwenLM/qwen-code/pull/3246) ✓（SSE 流式 429 检测） |
| **P1** | [优雅关闭序列与信号处理](./graceful-shutdown-deep-dive.md) — SIGINT/SIGTERM + 清理注册 + 5s failsafe [↓](./qwen-code-improvement-report-p0-p1-engine.md#item-9) | 无信号处理 | 中 | — |
| **P1** | [反应式压缩](./reactive-compression-deep-dive.md) — prompt_too_long 自动裁剪最早消息 + 重试 3 次 [↓](./qwen-code-improvement-report-p0-p1-engine.md#item-10) | 无被动恢复 | 中 | — |
| **P1** | [持久化重试模式](./persistent-retry-deep-dive.md) — CI/后台无限重试 + 5min 退避上限 + 30s 心跳 [↓](./qwen-code-improvement-report-p0-p1-engine.md#item-11) | 失败即退出 | 中 | [PR#3080](https://github.com/QwenLM/qwen-code/pull/3080) |
| **P1** | [原子文件写入与事务回滚](./atomic-file-write-deep-dive.md) — temp+rename 原子写 + 大结果persist to disk [↓](./qwen-code-improvement-report-p0-p1-engine.md#item-12) | 直接 writeFileSync | 中 | — |
| **P1** | [自动检查点默认启用](./automatic-checkpoint-restore-deep-dive.md) — 每轮工具执行后自动创建文件快照 [↓](./qwen-code-improvement-report-p0-p1-engine.md#item-13) | 检查点默认关闭 | 小 | — |
| **P1** | [Coordinator/Swarm 多 Agent编排](./coordinator-swarm-orchestration-deep-dive.md) — Leader/Worker 团队 + 3 种执行后端 [↓](./qwen-code-improvement-report-p0-p1-engine.md#item-14) | 仅 Arena 竞赛 | 大 | [PR#2886](https://github.com/QwenLM/qwen-code/pull/2886) / [PR#3433](https://github.com/QwenLM/qwen-code/pull/3433) ⚠️ **已 revert**（[PR#3468](https://github.com/QwenLM/qwen-code/pull/3468) 2026-04-20 合并 revert） / [Roadmap#1815](https://github.com/QwenLM/qwen-code/issues/1815) |
| **P1** | [Task Management 任务协同与跨进程并发调度](./task-management-deep-dive.md) — 支持 blocks/blockedBy 的任务拓扑、跨进程安全锁与 Swarm 集成 [↓](./qwen-code-improvement-report-p0-p1-engine.md#item-25) | 仅提供简易无状态 TodoWriteTool | 大 | [PR#2886](https://github.com/QwenLM/qwen-code/pull/2886) |
| **P1** | [Agent 工具细粒度访问控制](./agent-tool-access-control-deep-dive.md) — 3 层allowlist/denylist + per-agent 限制 [↓](./qwen-code-improvement-report-p0-p1-engine.md#item-15) | 全部或指定列表 | 中 | [PR#3064](https://github.com/QwenLM/qwen-code/pull/3064) ✓ / [PR#3066](https://github.com/QwenLM/qwen-code/pull/3066) ✓ |
| **P1** | [InProcess 同进程多 Agent隔离](./in-process-agent-isolation-deep-dive.md) — AsyncLocalStorage 上下文隔离 [↓](./qwen-code-improvement-report-p0-p1-engine.md#item-16) | 全局状态可能泄漏 | 中 | [PR#2886](https://github.com/QwenLM/qwen-code/pull/2886) |
| **P1** | [Agent 记忆持久化](./agent-memory-persistence-deep-dive.md) — user/project/local 3 级跨 session 记忆 [↓](./qwen-code-improvement-report-p0-p1-engine.md#item-17) | 无跨 session 记忆 | 中 | — |
| **P1** | [Agent 恢复与续行](./agent-resume-continuation-deep-dive.md) — SendMessage 继续已完成代理 + transcript 重建 [↓](./qwen-code-improvement-report-p0-p1-engine.md#item-18) | 执行完即销毁 | 中 | — |
| **P1** | 系统提示模块化组装 — sections 缓存 + dynamic boundary + uncached 标记 [↓](./qwen-code-improvement-report-p0-p1-engine.md#item-19) | 单一字符串 | 中 | — |
| **P1** | [系统提示内容完善](./system-prompt-content-guidelines-deep-dive.md) — OWASP 安全 + prompt injection检测 + 代码风格约束 + 输出格式 [↓](./qwen-code-improvement-report-p0-p1-engine.md#item-24) | 缺少具体指导 | 中 | — |
| **P1** | [@include 指令与嵌套记忆发现](./nested-memory-include-deep-dive.md) — @path 递归引用 + 文件操作触发目录遍历 [↓](./qwen-code-improvement-report-p0-p1-engine.md#item-20) | 无 @include/嵌套发现 | 中 | — |
| **P1** | [附件类型协议与令牌预算](./attachment-protocol-budget-deep-dive.md) — 40+ 类型 + per-type 预算 + 3 阶段有序执行 [↓](./qwen-code-improvement-report-p0-p1-engine.md#item-21) | 字符串拼接/无预算 | 中 | — |
| **P1** | [Thinking 块跨轮保留与空闲清理](./thinking-block-retention-deep-dive.md) — 活跃保留 + 1h 空闲清理 + latch 防缓存破坏 [↓](./qwen-code-improvement-report-p0-p1-engine.md#item-22) | 每轮独立/无清理 | 中 | [PR#2897](https://github.com/QwenLM/qwen-code/pull/2897) ✓ |
| **P1** | [输出 Token 自适应升级](./output-token-adaptive-upgrade-deep-dive.md) — 8K 默认 + max_tokens 截断时自动 64K 重试 [↓](./qwen-code-improvement-report-p0-p1-engine.md#item-23) | 固定值/不重试 | 小 | [PR#2898](https://github.com/QwenLM/qwen-code/pull/2898) ✓ |
| **P1** | QWEN.md system-reminder 注入 — 项目指令从系统提示移到用户消息 `<system-reminder>` 标签注入，避免打破 Prompt Cache [↓](./qwen-code-improvement-report-p0-p1-engine.md#item-26) | 直接拼入系统提示 | 小 | — |
| **P1** | 错误恢复分类路由 — truncation→continuation、overflow→compaction、transport→backoff 三分支 + per-category 重试预算 [↓](./qwen-code-improvement-report-p0-p1-engine.md#item-27) | 统一 catch 重试 | 中 | — |
| **P2** | [Shell 安全增强](./shell-security-deep-dive.md) — IFS 注入/Unicode 空白/Zsh 命令等 25+ 专项检查 [↓](./qwen-code-improvement-report-p2-core.md#item-1) | AST-only 读写分类 | 中 | — |
| **P2** | [MDM 企业策略](./mdm-enterprise-deep-dive.md) — macOS plist + Windows Registry + 远程 API 集中管控 [↓](./qwen-code-improvement-report-p2-core.md#item-2) | 无 OS 级策略 | 大 | — |
| **P2** | [API 实时 Token 计数](./token-estimation-deep-dive.md) — 每次 API 调用前精确计数，3 层回退 [↓](./qwen-code-improvement-report-p2-core.md#item-3) | 静态 82 种模式匹配 | 中 | — |
| **P2** | [Output Styles](./git-workflow-session-deep-dive.md) — Learning 模式暂停让用户写代码，Explanatory 添加教育洞察 [↓](./qwen-code-improvement-report-p2-core.md#item-4) | 缺失 | 中 | — |
| **P2** | [Fast Mode](./cost-fastmode-deep-dive.md) — 同一模型标准/快速推理切换（$5→$30/Mtok），含冷却机制 [↓](./qwen-code-improvement-report-p2-core.md#item-5) | ⚠️ 部分实现（`fastModel` 走不同方案——另一个更快模型，非同模型速度分级） | 小 | [PR#3077](https://github.com/QwenLM/qwen-code/pull/3077) ✓ / [PR#3086](https://github.com/QwenLM/qwen-code/pull/3086) ✓ / [PR#3120](https://github.com/QwenLM/qwen-code/pull/3120) ✓ |
| **P2** | [并发 Session](./cost-fastmode-deep-dive.md) — 多终端 PID 追踪 + 后台 Agent 脱附/重附 [↓](./qwen-code-improvement-report-p2-core.md#item-8) | 缺失 | 中 | — |
| **P2** | [Git Diff 统计](./git-workflow-session-deep-dive.md) — 编辑后 numstat + hunks 结构化 diff（50 文件/1MB 上限） [↓](./qwen-code-improvement-report-p2-core.md#item-9) | 无 git-aware diff | 小 | — |
| **P2** | [文件历史快照](./git-workflow-session-deep-dive.md) — per-file SHA256 备份，按消息粒度恢复（100 个/session） [↓](./qwen-code-improvement-report-p2-core.md#item-10) | git-level checkpoint | 中 | — |
| **P2** | [Computer Use](./computer-use-deep-dive.md) — macOS 截图 + 鼠标/键盘 + 剪贴板，通过 MCP 桥接 [↓](./qwen-code-improvement-report-p2-core.md#item-6) | 缺失 | 大 | — ⚠️ **Claude Code 侧默认禁用（`tengu_malort_pedway` gate），降级建议** |
| **P2** | [Deep Link](./deep-link-protocol-deep-dive.md) — `claude-cli://` 一键从浏览器/IDE 启动 Agent + 预填充 prompt [↓](./qwen-code-improvement-report-p2-core.md#item-11) | 缺失 | 中 | — ⚠️ **Claude Code 侧默认禁用（`tengu_lodestone_enabled` gate），降级建议** |
| **P2** | [`/context` 非交互输出](./context-usage-noninteractive-deep-dive.md) — 将上下文诊断暴露给脚本、CI 与外部控制器 [↓](./qwen-code-improvement-report-p2-tools-ui.md#item-20) | 仅交互式 | 小 | [PR#2916](https://github.com/QwenLM/qwen-code/pull/2916) ✓ / [PR#3042](https://github.com/QwenLM/qwen-code/pull/3042) ✓ |
| **P3** | 大粘贴内容自动存到工作区文件 — 粘贴 >30KB 内容自动外化到 tmp 文件 + 输入框显示引用（Copilot CLI v0.0.397 参考） [↓](./qwen-code-improvement-report-p2-tools-ui.md#item-21) | 直接进 prompt | 小 | — |
| **P1** | [Team Memory](./team-memory-deep-dive.md) — 团队共享项目知识 + 29 条 gitleaks 密钥扫描 + ETag 同步 [↓](./qwen-code-improvement-report-p0-p1-core.md#item-10) | 缺失 | 大 | — |
| **P2** | [Plan 模式 Interview](./plan-mode-interview-deep-dive.md) — 先澄清需求再形成计划，分离访谈/规划/执行阶段 [↓](./qwen-code-improvement-report-p2-core.md#item-12) | 无 interview 阶段 | 中 | — |
| **P2** | [BriefTool 异步用户消息](./brieftool-async-user-messages-deep-dive.md) — Agent 主动发消息/附件给用户，不阻塞当前工具执行 [↓](./qwen-code-improvement-report-p2-core.md#item-13) | 缺失 | 中 | — |
| **P2** | [SendMessageTool](./multi-agent-deep-dive.md) — 多 Agent间消息传递、shutdown 请求、plan 审批 [↓](./qwen-code-improvement-report-p2-core.md#item-14) | 缺失 | 中 | — |
| **P2** | [FileIndex 模糊文件搜索](./file-index-fuzzy-search-deep-dive.md) — fzf 风格模糊文件搜索 + 异步增量索引 [↓](./qwen-code-improvement-report-p2-core.md#item-15) | 依赖 rg/glob | 中 | [PR#3214](https://github.com/QwenLM/qwen-code/pull/3214)（git ls-files + rg 回退） |
| **P2** | [Notebook Edit 原子级编辑](./notebook-edit-deep-dive.md) — Jupyter cell 编辑 + 自动 cell ID 追踪 + 文件历史快照 [↓](./qwen-code-improvement-report-p2-core.md#item-16) | 缺失 | 中 | — |
| **P2** | 自定义快捷键 — multi-chord 组合键 + 跨平台适配 + `keybindings.json` 自定义 [↓](./qwen-code-improvement-report-p2-core.md#item-17) | 缺失 | 中 | — |
| **P2** | [Session Ingress Auth](./session-ingress-auth-deep-dive.md) — 远程会话 bearer token 认证（企业多用户环境） [↓](./qwen-code-improvement-report-p2-core.md#item-18) | 缺失 | 中 | — |
| **P2** | [企业代理](./enterprise-proxy-support-deep-dive.md) — CONNECT relay + CA cert 注入 + NO_PROXY allowlist（容器环境） [↓](./qwen-code-improvement-report-p2-core.md#item-19) | 缺失 | 大 | — |
| **P2** | [终端主题检测](./terminal-theme-detection-deep-dive.md) — OSC 11 查询 dark/light + COLORFGBG 环境变量回退 [↓](./qwen-code-improvement-report-p2-core.md#item-20) | 缺失 | 小 | — |
| **P2** | Denial Tracking — 连续权限拒绝自动回退到手动确认模式，防止静默阻塞 [↓](./qwen-code-improvement-report-p2-core.md#item-7) | 缺失 | 小 | — |
| **P2** | [队列输入编辑](./input-queue-deep-dive.md) — 排队中的指令可通过方向键弹出到输入框重新编辑 [↓](./qwen-code-improvement-report-p2-core.md#item-21) | 缺失 | 小 | [PR#2871](https://github.com/QwenLM/qwen-code/pull/2871) ✓ |
| **P2** | [状态栏紧凑布局](./compact-status-bar-deep-dive.md) — 固定高度不伸缩，最大化终端内容区域 [↓](./qwen-code-improvement-report-p2-core.md#item-22) | Footer 占用偏高 | 小 | — |
| **P2** | [会话标签与搜索](./session-tags-search-deep-dive.md) — /tag 命令打标签 + 按标签/仓库/标题搜索历史会话 [↓](./qwen-code-improvement-report-p2-core.md#item-23) | 仅按时间排序 | 小 | — |
| **P2** | Plan 状态机化 + Hint 注入 — 4 状态 subtask + 每轮 hint 注入（AgentScope 参考） [↓](./qwen-code-improvement-report-p2-core.md#item-24) | `/plan` 是一次性文档 | 中 | — |
| **P2** | A2A 协议集成 — 跨 agent 通信 + AgentCard + 服务发现（AgentScope 参考） [↓](./qwen-code-improvement-report-p2-core.md#item-25) | 仅 MCP Client | 大 | — |
| **P2** | OTel 原生 Tracing — 5 类 span extractor（Agent/LLM/Tool/Formatter/Embedding，AgentScope 参考） [↓](./qwen-code-improvement-report-p2-core.md#item-26) | 仅阿里云 RUM | 中 | — |
| **P2** | Conditional Hooks — Hook `if` 字段用权限规则语法按工具/路径过滤 [↓](./qwen-code-improvement-report-p2-tools-commands.md#item-1) | 缺失 | 小 | — |
| **P2** | [Transcript Search 会话记录搜索](./transcript-search-navigation-deep-dive.md) — 按 `/` 搜索会话记录，`n`/`N` 导航匹配项 [↓](./qwen-code-improvement-report-p2-tools-commands.md#item-2) | 缺失 | 小 | — |
| **P2** | [Bash File Watcher](./file-watcher-stale-edit-deep-dive.md) — 检测 formatter/linter 修改已读文件，防止 stale-edit [↓](./qwen-code-improvement-report-p2-tools-commands.md#item-3) | 缺失 | 小 | — |
| **P2** | [/batch 并行操作](./batch-parallel-execution-deep-dive.md) — 编排大规模并行变更（多文件/多任务）[↓](./qwen-code-improvement-report-p2-tools-commands.md#item-4) | 缺失 | 中 | [PR#3079](https://github.com/QwenLM/qwen-code/pull/3079) ✓ |
| **P2** | PDF / 二进制文件读取 — read_file 内置 PDF + 图片 + Notebook 支持 [↓](./qwen-code-improvement-report-p2-tools-commands.md#item-21) | ✓ PDF + Notebook 已实现（[PR#3160](https://github.com/QwenLM/qwen-code/pull/3160) ✓ 2026-04-20 合并）；图片/DOCX/XLSX 仍缺 | 中 | [Issue#38](https://github.com/QwenLM/qwen-code/issues/38)、[PR#2024](https://github.com/QwenLM/qwen-code/pull/2024) ✓ |
| **P2** | Skill 级模型覆盖 — SKILL.md frontmatter `model:` 字段，按阶段切换模型 [↓](./qwen-code-improvement-report-p2-tools-commands.md#item-22) | 仅 session 级 | 小 | [PR#2949](https://github.com/QwenLM/qwen-code/pull/2949) ✓ |
| **P2** | PreCompact Hook — 压缩前钩子，支持 block/modify/continue（Claude Code v2.1.105 新增） [↓](./qwen-code-improvement-report-p2-tools-commands.md#item-23) | 仅 PostCompact | 小 | — |
| **P2** | 模型通过 Skill 工具调用内置 Slash 命令 — Agent 自主调用 `/init` / `/review` / `/security-review`（v2.1.108 新增） [↓](./qwen-code-improvement-report-p2-tools-commands.md#item-24) | 用户手动触发 | 中 | — |
| **P3** | Statusline Refresh Interval — 按秒级间隔重跑 statusline 脚本（v2.1.97 新增） [↓](./qwen-code-improvement-report-p2-tools-commands.md#item-25) | 仅状态变化时刷新 | 小 | [PR#3383](https://github.com/QwenLM/qwen-code/pull/3383) ✓（2026-04-19 合并） |
| **P2** | `/experimental` 实验特性统一门控 — 统一注册表 + `/experimental list` + `--experimental <id>` flag（Copilot CLI v0.0.396 参考） [↓](./qwen-code-improvement-report-p2-tools-commands.md#item-26) | 实验特性分散在 env var / settings / 命令参数 | 中 | — |
| **P2** | Chrome Extension — 调试 live web 应用（读 DOM/Console/Network）[↓](./qwen-code-improvement-report-p2-tools-commands.md#item-5) | 缺失 | 中 | — |
| **P2** | [MCP Auto-Reconnect](./mcp-auto-reconnect-deep-dive.md) — 连续 3 次错误自动重连 + SSE 断线恢复 [↓](./qwen-code-improvement-report-p2-tools-commands.md#item-13) | 缺失 | 小 | — |
| **P2** | Tool Result 大小限制 — 超限结果持久化到磁盘，发文件路径给模型 [↓](./qwen-code-improvement-report-p2-tools-commands.md#item-14) | 缺失 | 小 | — |
| | ↳ 参考：[RTK](https://github.com/rtk-ai/rtk)——在命令输出端过滤压缩（58 个 TOML 规则，-80% token），30 分钟会话节省 118K→24K token | | | |
| **P2** | Output Token 升级重试 — 首次 8K 截断后自动 64K 重试 [↓](./qwen-code-improvement-report-p2-tools-commands.md#item-15) | 缺失 | 小 | — |
| **P2** | [Ripgrep 三级回退](./ripgrep-fallback-deep-dive.md) — System→Embedded→Builtin + EAGAIN 单线程重试 [↓](./qwen-code-improvement-report-p2-tools-commands.md#item-16) | 缺失 | 小 | — |
| **P2** | MAGIC DOC 自更新文档 — 空闲时 Agent 自动更新标记文件的内容 [↓](./qwen-code-improvement-report-p2-tools-commands.md#item-17) | 缺失 | 中 | — |
| **P2** | 目录/文件路径补全 — 输入路径时 Tab 补全 + LRU 缓存 [↓](./qwen-code-improvement-report-p2-tools-commands.md#item-18) | 缺失 | 小 | [PR#2879](https://github.com/QwenLM/qwen-code/pull/2879) |
| **P2** | [上下文 Tips 系统](./context-tips-system-deep-dive.md) — 根据配置/IDE/插件状态显示上下文相关提示 [↓](./qwen-code-improvement-report-p2-tools-commands.md#item-19) | 缺失 | 小 | [PR#2904](https://github.com/QwenLM/qwen-code/pull/2904) ✓ |
| **P2** | [权限对话框文件预览](./permission-dialog-file-preview-deep-dive.md) — 审批时展示文件内容 + 语法高亮 + 上下文说明 [↓](./qwen-code-improvement-report-p2-tools-commands.md#item-20) | 缺失 | 中 | — |
| **P2** | Token 使用实时警告 — 显示 token 用量 + 压缩进度 + 错误计数 [↓](./qwen-code-improvement-report-p2-tools-ui.md#item-1) | 仅基础显示 | 小 | — |
| **P2** | 快捷键提示组件 — UI 全局统一显示当前操作的键盘快捷方式 [↓](./qwen-code-improvement-report-p2-tools-ui.md#item-2) | 缺失 | 小 | — |
| **P2** | 终端完成通知 — 后台任务完成时 iTerm2/Kitty/Ghostty OSC 通知 + 进度百分比 [↓](./qwen-code-improvement-report-p2-tools-ui.md#item-3) | 仅 bell | 小 | — |
| **P2** | Spinner 工具名 + 计时 — 显示"正在执行 Bash(npm test) · 15s"而非通用 spinner [↓](./qwen-code-improvement-report-p2-tools-ui.md#item-4) | 通用 Responding | 小 | — |
| **P2** | /rewind 检查点回退 — 会话内代码 + 对话恢复到之前的检查点 [↓](./qwen-code-improvement-report-p2-tools-ui.md#item-5) | 缺失 | 中 | [PR#3441](https://github.com/QwenLM/qwen-code/pull/3441) / [PR#3292](https://github.com/QwenLM/qwen-code/pull/3292) / [Roadmap#2342](https://github.com/QwenLM/qwen-code/issues/2342) |
| **P2** | /copy OSC 52 剪贴板 — 复制代码块到剪贴板，OSC 52 + temp 文件回退 [↓](./qwen-code-improvement-report-p2-tools-ui.md#item-6) | 缺失 | 小 | — |
| **P2** | 首次运行引导向导 — 主题/认证/API Key/安全/终端设置多步引导 [↓](./qwen-code-improvement-report-p2-tools-ui.md#item-7) | 缺失 | 中 | — |
| **P2** | /doctor 诊断工具 — 系统环境检查（git/node/shell/权限/代理）[↓](./qwen-code-improvement-report-p2-tools-ui.md#item-8) | 缺失 | 小 | — |
| **P2** | 结构化 Diff 渲染 — Rust NAPI 快速着色 + 行号 gutter + 语法高亮 [↓](./qwen-code-improvement-report-p2-tools-ui.md#item-9) | 基础 inline diff | 中 | — |
| **P2** | Slash Command 命名空间治理 — source namespace + reserved names + 来源透明 [↓](./qwen-code-improvement-report-p2-tools-ui.md#item-10) | 后者覆盖前者 | 中 | — |
| **P2** | /plan 计划模式 — Agent 只分析不动手 + 用户确认后执行 [↓](./qwen-code-improvement-report-p2-tools-ui.md#item-11) | 无计划模式 | 小 | [PR#2921](https://github.com/QwenLM/qwen-code/pull/2921) ✓ / [PR#3008](https://github.com/QwenLM/qwen-code/pull/3008) ✓ |
| **P2** | /rename 重命名会话 — 手动修改会话标题 [↓](./qwen-code-improvement-report-p2-tools-ui.md#item-12) | AI 自动标题不可改 | 小 | [PR#3093](https://github.com/QwenLM/qwen-code/pull/3093) / [Roadmap#2933](https://github.com/QwenLM/qwen-code/issues/2933) |
| **P2** | /upgrade 版本升级 — changelog 展示 + 一键更新 [↓](./qwen-code-improvement-report-p2-tools-ui.md#item-13) | 手动 npm update | 小 | — |
| **P2** | Plugin 系统增强 — 聚合容器（commands+skills+hooks+MCP）+ 一键安装/卸载 [↓](./qwen-code-improvement-report-p2-tools-ui.md#item-14) | extension 分散管理 | 中 | — |
| **P2** | 文件编辑引号风格保留 — preserveQuoteStyle() 检测并保持原文件引号风格 [↓](./qwen-code-improvement-report-p2-tools-ui.md#item-15) | 直接替换不保留 | 小 | — |
| **P2** | 文件编辑等价性判断 — areFileEditsInputsEquivalent() 跳过重复编辑 [↓](./qwen-code-improvement-report-p2-tools-ui.md#item-16) | 重复编辑也执行 | 小 | — |
| **P2** | MCP 通道权限管理 — channel plugin allowlist + GrowthBook gate [↓](./qwen-code-improvement-report-p2-tools-ui.md#item-17) | 无 plugin allowlist | 小 | — |
| **P2** | 消息类型丰富化 — 11 种 → 30+ 种 SDK 消息类型 [↓](./qwen-code-improvement-report-p2-tools-ui.md#item-18) | ~11 种 | 中 | — |
| **P2** | /clear 多模式增强 — 清屏/清对话/完全重置三种力度 [↓](./qwen-code-improvement-report-p2-tools-ui.md#item-19) | 仅清屏 | 小 | [PR#2915](https://github.com/QwenLM/qwen-code/pull/2915) / [Roadmap#2487](https://github.com/QwenLM/qwen-code/issues/2487) |
| **P2** | /effort — 设置模型 effort 级别（○ 低 / ◐ 中 / ● 高）[↓](./qwen-code-improvement-report-p2-tools-commands.md#item-6) | 缺失 | 小 | [Roadmap#2876](https://github.com/QwenLM/qwen-code/issues/2876) |
| **P2** | Status Line 自定义 — shell 脚本在状态栏展示自定义信息 [↓](./qwen-code-improvement-report-p2-tools-commands.md#item-7) | 缺失 | 小 | [PR#2923](https://github.com/QwenLM/qwen-code/pull/2923) ✓ / [Roadmap#2418](https://github.com/QwenLM/qwen-code/issues/2418) |
| **P2** | Query TransitionReason 枚举 — 6 种查询转换原因显式标记（tool_result/max_tokens/compaction/retry/stop_hook/budget） [↓](./qwen-code-improvement-report-p2-stability.md#item-36) | 隐式 if-else | 小 | — |
| **P2** | 工具并发安全分类 — 每个工具标记 `concurrencySafe`，并发分区后批量执行 [↓](./qwen-code-improvement-report-p2-stability.md#item-37) | 仅 Agent 工具并行 | 中 | — |
| **P2** | 工具执行进度消息 — 长时间工具（>3s）发射进度事件 + elapsed time + shell stats bar + OSC 9;4 标签进度 [↓](./qwen-code-improvement-report-p2-stability.md#item-38) | 🟡 部分实现（墙钟/字节 ✓ / 语义 progress events 未覆盖）| 小 | [PR#3155](https://github.com/QwenLM/qwen-code/pull/3155) ✓（2026-04-20 合并，视觉反馈部分）|
| **P2** | 运行时任务模型 — 区分 work-graph task（持久目标）vs runtime task（执行槽），防止状态混淆 [↓](./qwen-code-improvement-report-p2-stability.md#item-39) | 仅 TodoWriteTool | 中 | — |
| **P2** | 后台通知 drain-before-call — LLM 调用前排空后台任务通知队列，确保模型看到最新结果 [↓](./qwen-code-improvement-report-p2-stability.md#item-40) | 无通知排空 | 小 | — |
| **P2** | 压缩后身份重注入 — 上下文压缩后 messages<3 条时注入 Agent 身份块，防止 Agent "忘记自己是谁" [↓](./qwen-code-improvement-report-p2-stability.md#item-41) | 无身份重注入 | 小 | — |
| **P2** | 子进程 PID 命名空间沙箱 + 脚本次数限制 — Linux PID namespace + env scrub + SCRIPT_CAPS（v2.1.98 新增） [↓](./qwen-code-improvement-report-p2-stability.md#item-42) | 无 PID 隔离 | 中 | — |
| **P2** | 会话 Recap（返回时上下文摘要）— `/recap` 命令 + 自动展示（v2.1.108/v2.1.110 新增）[↓](./qwen-code-improvement-report-p2-stability.md#item-43) | **已实现**（/recap + auto-show） | 小 | [PR#3434](https://github.com/QwenLM/qwen-code/pull/3434) ✓（2026-04-19 合并） |
| **P2** | [瞬态消息单行容器 + 离屏历史冻结](./task-display-height-deep-dive.md) — MessageResponse `height=1 overflowY=hidden` + OffscreenFreeze 引用缓存避免历史 spinner 拖累 [↓](./qwen-code-improvement-report-p2-stability.md#item-44) | 无统一容器/无离屏冻结 | 中 | — |
| **P2** | [三级输出截断](./task-display-height-deep-dive.md) — Bash 30K/150K + 单工具 50K + 单消息 200K 批量预算 + env var `BASH_MAX_OUTPUT_LENGTH` [↓](./qwen-code-improvement-report-p2-stability.md#item-45) | 无统一上限 | 小 | — |
| **P2** | [Bash 执行中 "5 行窗口 + +N lines 计数"](./bash-task-display-deep-dive.md) — ShellProgressMessage `lines.slice(-5)` + `+${extraLines} lines` 计数 [↓](./qwen-code-improvement-report-p2-stability.md#item-46) | 🟡 拆分实现中（两 PR 合后 ✓ 完整）| 小 | [PR#3155](https://github.com/QwenLM/qwen-code/pull/3155) ✓（`+N lines`）+ [PR#3508](https://github.com/QwenLM/qwen-code/pull/3508) 🟡 OPEN（5 行窗口 + 6 bypasses + settings）|
| **P2** | [ShellTimeDisplay 时间 + timeout 倒计时](./bash-task-display-deep-dive.md) — `(10.5s · timeout 30s)` 三种格式 + dim color [↓](./qwen-code-improvement-report-p2-stability.md#item-47) | 🟡 变体实现（3s 阈值 + 右对齐，分散到 elapsed + stats bar 两处，非 Claude 的单单元组合）| 小 | [PR#3155](https://github.com/QwenLM/qwen-code/pull/3155) ✓（变体，2026-04-20 合并）|
| **P2** | [语义化 hunk 模型 + singleHunk 智能上下文](./update-tool-display-deep-dive.md) — `structuredPatch` + `singleHunk ? 100_000 : 3` 智能 context + 消除 UI 层 regex re-parse [↓](./qwen-code-improvement-report-p2-stability.md#item-48) | `createPatch` 字符串 + UI regex 重解析 + 固定 5 行上下文 | 中 | — |
| **P2** | [多 hunk `...` 省略分隔符](./update-tool-display-deep-dive.md) — StructuredDiffList 在 hunk 之间插入 dim color `...` [↓](./qwen-code-improvement-report-p2-stability.md#item-49) | 多 hunk 直接堆叠无分隔 | 小 | — |
| **P2** | [终端渲染优化（紧凑 + 低闪烁）](./terminal-low-flicker-deep-dive.md) — DEC 2026 同步输出 + 差分渲染 + 双缓冲 + DECSTBM 硬件滚动 + 缓存池化 + alt-screen [↓](./qwen-code-improvement-report-p2-tools-commands.md#item-8) | 仅消息拆分防闪烁 + PR#3381 游标移动优化 | 大 | [PR#3381](https://github.com/QwenLM/qwen-code/pull/3381) ✓（局部） |
| **P2** | Image [Image #N] Chips — 粘贴图片后生成位置引用标记 [↓](./qwen-code-improvement-report-p2-tools-commands.md#item-9) | 缺失 | 小 | — |
| **P2** | --max-turns — headless 模式最大 turn 数限制 [↓](./qwen-code-improvement-report-p2-tools-commands.md#item-10) | 缺失 | 小 | — |
| **P2** | --max-budget-usd — headless 模式 USD 花费上限 [↓](./qwen-code-improvement-report-p2-tools-commands.md#item-11) | 缺失 | 小 | — |
| **P2** | Connectors — 托管式 MCP 连接（GitHub/Slack/Linear/Google Drive OAuth）[↓](./qwen-code-improvement-report-p2-tools-commands.md#item-12) | 缺失 | 大 | — |
| **P2** | MCP 并行连接 — pMap 动态插槽调度 + 双层并发（local:3/remote:20）[↓](./qwen-code-improvement-report-p2-perf.md#item-1) | 已并行但无并发上限 | 小 | — |
| **P2** | 插件/Skill 并行加载 — marketplace + session 双源并行 + 目录检查并行 [↓](./qwen-code-improvement-report-p2-perf.md#item-2) | 顺序 for 循环 | 小 | — |
| **P2** | Speculation 流水线建议 — 投机完成后立即并行生成下一建议 [↓](./qwen-code-improvement-report-p2-perf.md#item-3) | 每次重新生成 | 小 | — |
| **P2** | [write-through缓存与 TTL 后台刷新](./memoize-ttl-cache-deep-dive.md) — stale-while-revalidate + LRU 有界缓存 [↓](./qwen-code-improvement-report-p2-perf.md#item-4) | 无通用缓存模式 | 小 | — |
| **P2** | 上下文收集并行化 — 多源附件 Promise.all 并行获取（~20 并发）[↓](./qwen-code-improvement-report-p2-perf.md#item-5) | 串行追加 | 小 | — |
| **P2** | 输出缓冲与防阻塞渲染 — setImmediate 延迟写入 + 内存缓冲 [↓](./qwen-code-improvement-report-p2-perf.md#item-6) | 直接 appendFileSync | 小 | — |
| **P2** | [LSP 服务器并行启动](./lsp-parallel-startup-deep-dive.md) — Promise.all 并行启动 + Promise.race 端口探测 [↓](./qwen-code-improvement-report-p2-perf.md#item-7) | 顺序 for 循环 | 小 | [PR#3034](https://github.com/QwenLM/qwen-code/pull/3034) / [PR#3170](https://github.com/QwenLM/qwen-code/pull/3170)（官方 SDK + didSave 实时诊断） |
| **P2** | 请求合并与去重 — 1-in-flight + 1-pending + BoundedUUIDSet + inFlight 去重 [↓](./qwen-code-improvement-report-p2-perf.md#item-8) | 无合并机制 | 中 | — |
| **P2** | 延迟初始化与按需加载 — lazySchema + 动态 import() + 延迟prefetch [↓](./qwen-code-improvement-report-p2-perf.md#item-9) | 全量同步加载 | 小 | — |
| **P2** | 流式超时检测与级联取消 — 90s 空闲watchdog + siblingAbortController 级联 [↓](./qwen-code-improvement-report-p2-perf.md#item-10) | 固定超时/无级联 | 小 | — |
| **P2** | Git 文件系统直读 — .git/HEAD+refs 直读 + 批量 check-ignore + LRU 缓存 [↓](./qwen-code-improvement-report-p2-perf.md#item-11) | 每次 spawn git | 小 | — |
| **P2** | 设置/Schema 缓存防抖动 — 3 层设置缓存 + schema 首次锁定 + parse 去重 [↓](./qwen-code-improvement-report-p2-perf.md#item-12) | 每次重新读取解析 | 小 | — |
| **P2** | Bash 交互提示卡顿检测 — 45s 无输出 + prompt regex 匹配 + 自动通知 [↓](./qwen-code-improvement-report-p2-stability.md#item-1) | 无卡顿检测 | 小 | — |
| **P2** | TTY orphan process检测 — 30s 检查终端存活 + 自动优雅退出 [↓](./qwen-code-improvement-report-p2-stability.md#item-2) | 无检测 | 小 | — |
| **P2** | MCP 服务器优雅关闭升级 — SIGINT(100ms)→SIGTERM(400ms)→SIGKILL 3 阶段 [↓](./qwen-code-improvement-report-p2-stability.md#item-3) | 直接断开 | 小 | — |
| **P2** | 事件循环卡顿检测 — 主线程阻塞 >500ms 诊断日志 [↓](./qwen-code-improvement-report-p2-stability.md#item-4) | 无监控 | 小 | — |
| **P2** | 会话活动心跳 — refcount 活动追踪 + 30s keepalive + 空闲退出 [↓](./qwen-code-improvement-report-p2-stability.md#item-5) | 无心跳 | 小 | — |
| **P2** | Markdown 渲染缓存 — 500-LRU token cache + 纯文本快速路径 [↓](./qwen-code-improvement-report-p2-stability.md#item-6) | 每次重新解析 | 小 | — |
| **P2** | OSC 8 终端超链接 — 文件路径/URL Cmd+Click 直接打开 [↓](./qwen-code-improvement-report-p2-stability.md#item-7) | 纯文本路径 | 小 | — |
| **P2** | 模糊搜索选择器 — FuzzyPicker 通用组件 + 异步预览 + 匹配高亮 [↓](./qwen-code-improvement-report-p2-stability.md#item-8) | 无模糊搜索 | 中 | — |
| **P2** | 统一设计系统组件库 — 12 个语义 UI 原语 + ThemeProvider [↓](./qwen-code-improvement-report-p2-stability.md#item-9) | 组件分散 | 中 | — |
| **P2** | Markdown 表格终端渲染 — ANSI-aware + CJK-aware 列宽计算 [↓](./qwen-code-improvement-report-p2-stability.md#item-10) | CJK 列错位 | 小 | [PR#2914](https://github.com/QwenLM/qwen-code/pull/2914) ✓ |
| **P2** | 屏幕阅读器无障碍支持 — Diff/Spinner/Progress 纯文本替代渲染 [↓](./qwen-code-improvement-report-p2-stability.md#item-11) | hook 存在但使用有限 | 小 | — |
| **P2** | 色觉无障碍主题 — daltonized 红绿→蓝橙 diff 色板 [↓](./qwen-code-improvement-report-p2-stability.md#item-12) | 无色觉主题 | 小 | — |
| **P2** | 动画系统与卡顿状态检测 — shimmer 微光 + 30s 超时变红 [↓](./qwen-code-improvement-report-p2-stability.md#item-13) | 固定动画/无超时检测 | 小 | — |
| **P2** | [Agent 权限冒泡](./agent-permission-bubble-deep-dive.md) — bubble 模式 + Leader 桥接 + 邮箱回退 [↓](./qwen-code-improvement-report-p2-stability.md#item-14) | 继承父级模式 | 中 | [PR#2886](https://github.com/QwenLM/qwen-code/pull/2886) |
| **P2** | Agent 专属 MCP 服务器 — frontmatter mcpServers + 按需连接/清理 [↓](./qwen-code-improvement-report-p2-stability.md#item-15) | 共享全局 MCP | 小 | — |
| **P2** | [Agent 创建向导](./interactive-agent-creation-deep-dive.md) — 11 步交互式向导 + AI 生成模式 [↓](./qwen-code-improvement-report-p2-stability.md#item-16) | 基础命令行创建 | 中 | — |
| **P2** | Agent 进度追踪与实时状态 — ProgressTracker + task-notification + kill 控制 [↓](./qwen-code-improvement-report-p2-stability.md#item-17) | 仅最终结果 | 中 | — |
| **P2** | Agent 邮箱系统 — 文件 IPC + lockfile + 单播/广播 [↓](./qwen-code-improvement-report-p2-stability.md#item-18) | 仅 Arena 文件 IPC | 中 | [PR#2886](https://github.com/QwenLM/qwen-code/pull/2886) |
| **P2** | cache_edits 增量缓存删除 — API 原地删除旧工具结果不破坏缓存前缀 [↓](./qwen-code-improvement-report-p2-perf.md#item-13) | 重建消息数组 | 小 | [PR#3006](https://github.com/QwenLM/qwen-code/pull/3006) ✓ |
| **P2** | 消息规范化与配对修复 — 合并连续 user + 修复孤立 tool_use/result + 100 媒体上限 [↓](./qwen-code-improvement-report-p2-perf.md#item-14) | 格式转换/无修复 | 中 | — |
| **P2** | [Git 状态自动注入上下文](./git-context-auto-injection-deep-dive.md) — gitBranch/cwd/platform/fileCount 每轮注入 [↓](./qwen-code-improvement-report-p2-perf.md#item-15) | 仅平台和日期 | 小 | — |
| **P2** | IDE 上下文注入与嵌套记忆触发 — 选区→目录规范自动注入 + 诊断双源收集 [↓](./qwen-code-improvement-report-p2-perf.md#item-16) | 无嵌套记忆触发 | 中 | — |
| **P2** | [图片压缩多策略流水线](./image-compression-pipeline-deep-dive.md) — format→resize→quality 阶梯 + JPEG fallback [↓](./qwen-code-improvement-report-p2-perf.md#item-17) | 仅计算 token/不压缩 | 中 | — |
| **P2** | WeakRef/WeakMap 防止 GC 保留 — AbortController/渲染缓存/span 自动释放 [↓](./qwen-code-improvement-report-p2-perf.md#item-18) | 全部强引用 Map | 小 | — |
| **P2** | [环形缓冲区与磁盘溢出](./circular-buffer-disk-spill-deep-dive.md) — CircularBuffer + BoundedUUIDSet + 8MB 溢出 [↓](./qwen-code-improvement-report-p2-perf.md#item-19) | 无上限数据结构 | 小 | — |
| **P2** | [终端渲染字符串池化](./terminal-rendering-string-pooling-deep-dive.md) — CharPool/StylePool 整数 ID 替代字符串 [↓](./qwen-code-improvement-report-p2-perf.md#item-20) | Ink 标准渲染 | 小 | — |
| **P2** | 文件描述符与句柄追踪 — >100 handles / >500 fd 预警 [↓](./qwen-code-improvement-report-p2-perf.md#item-21) | 无追踪 | 小 | — |
| **P2** | Memoization cold start去重 — inFlight Map + TTL 后台刷新 + identity guard [↓](./qwen-code-improvement-report-p2-perf.md#item-22) | 无去重 | 小 | — |
| **P2** | 正则表达式编译缓存 — Hook/LS hot path new RegExp 缓存到 Map [↓](./qwen-code-improvement-report-p2-perf.md#item-23) | 每次重新编译 | 小 | — |
| **P2** | 搜索结果流式解析 — 流式逐行处理 + --max-count 提前终止 [↓](./qwen-code-improvement-report-p2-perf.md#item-24) | split('\n') 全量加载 | 小 | — |
| **P2** | React.memo 自定义相等性 — 消息组件防止击键重渲染（500ms→16ms）[↓](./qwen-code-improvement-report-p2-perf.md#item-25) | 需确认覆盖度 | 小 | [PR#2891](https://github.com/QwenLM/qwen-code/pull/2891) ✓ |
| **P2** | [Bun 原生 API 优化](./bun-native-api-optimization-deep-dive.md) — stringWidth/JSONL.parseChunk/argv0 dispatch [↓](./qwen-code-improvement-report-p2-perf.md#item-26) | Node.js 标准 API | 小 | [PR#2838](https://github.com/QwenLM/qwen-code/pull/2838) |
| **P2** | 行宽缓存与 Blit 屏幕 Diff — 4096-LRU + 未变化区域直接复制 [↓](./qwen-code-improvement-report-p2-perf.md#item-27) | 每帧完整重算 | 中 | — |
| **P2** | 编译时特性门控 — feature() 编译求值 + 死代码消除 [↓](./qwen-code-improvement-report-p2-perf.md#item-28) | 运行时 env 检查 | 小 | — |
| **P2** | Shell 环境快照 — 一次性捕获 aliases/functions/PATH + 会话级 memoize [↓](./qwen-code-improvement-report-p2-perf.md#item-29) | 每次 spawn 干净环境 | 中 | — |
| **P2** | Shell 输出文件直写 — stdout/stderr 直写 fd 绕过 JS + 1s 文件轮询 [↓](./qwen-code-improvement-report-p2-perf.md#item-30) | PTY + JSON.stringify | 中 | — |
| **P2** | [增量文件索引签名](./incremental-file-index-deep-dive.md) — .git/index mtime + FNV-1a 采样签名 <1ms [↓](./qwen-code-improvement-report-p2-perf.md#item-31) | SHA256 全量 hash | 小 | — |
| **P2** | Shell AST 解析缓存 — 同一命令 2 次解析→Map 缓存 [↓](./qwen-code-improvement-report-p2-perf.md#item-32) | 每次重新解析 | 小 | — |
| **P2** | 终端输出浅比较 — JSON.stringify O(n)→浅比较 O(1) + 脏行范围 [↓](./qwen-code-improvement-report-p2-perf.md#item-33) | JSON.stringify 深比较 | 小 | — |
| **P2** | Diff 渲染 useMemo — parseDiff 缓存 + Regex 模块级预编译 [↓](./qwen-code-improvement-report-p2-perf.md#item-34) | 每帧重新解析 | 小 | — |
| **P2** | 自定义指令文件去重 — 多层 QWEN.md 相同内容只保留一份，节省 context（Copilot CLI v0.0.394 参考） [↓](./qwen-code-improvement-report-p2-perf.md#item-35) | 直接拼接，重复也计入 | 小 | — |
| **P2** | 远程触发器 REST API — CRUD 定时远程 Agent + 云端 CCR 执行 [↓](./qwen-code-improvement-report-p2-stability.md#item-19) | 仅会话内 cron | 中 | — |
| **P2** | [SDK 双向控制协议](./sdk-bidirectional-control-deep-dive.md) — 权限回调 + 模型切换 + MCP 管理 + 文件回退 [↓](./qwen-code-improvement-report-p2-stability.md#item-20) | 基础 canUseTool 回调 | 中 | — |
| **P2** | [CI 环境自动检测](./ci-environment-detection-deep-dive.md) — GitHub Actions/CircleCI/Jenkins 检测 + 上下文提取 [↓](./qwen-code-improvement-report-p2-stability.md#item-21) | 仅通用 CI 变量 | 小 | — |
| **P2** | [PR Webhook 事件订阅](./pr-webhook-event-subscription-deep-dive.md) — review/CI 事件实时注入 Agent 对话 [↓](./qwen-code-improvement-report-p2-stability.md#item-22) | 一次性审查 | 中 | — |
| **P2** | [UltraReview 远程深度审查](./ultrareview-remote-deep-review-deep-dive.md) — 10-20 min CCR 审查 + 配额追踪 + 进度心跳 [↓](./qwen-code-improvement-report-p2-stability.md#item-23) | 本地审查 | 大 | — |
| **P2** | GitHub App 自动安装 — 一键生成 workflow YAML + 配置 secret + 创建 PR [↓](./qwen-code-improvement-report-p2-stability.md#item-24) | 手动配置 workflow | 中 | — |
| **P2** | Headless 性能剖析 — TTFT/turn latency/overhead 采样追踪 [↓](./qwen-code-improvement-report-p2-stability.md#item-25) | 无剖析 | 小 | — |
| **P2** | 退出码标准化与 Hook 唤醒 — exit 2 唤醒模型 + CI 语义文档 [↓](./qwen-code-improvement-report-p2-stability.md#item-26) | 有自定义码/无唤醒 | 小 | — |
| **P2** | 破坏性命令警告系统 — 8 种高风险 git 操作 + 权限对话框风险说明 [↓](./qwen-code-improvement-report-p2-stability.md#item-27) | 仅读写分类/无风险说明 | 小 | — |
| **P2** | 系统提示危险操作行为指导 — 4 类危险操作列举 + 行为准则 + 审批范围限定 [↓](./qwen-code-improvement-report-p2-stability.md#item-28) | 仅 "never push" 一条 | 小 | [PR#2889](https://github.com/QwenLM/qwen-code/pull/2889) ✓ |
| **P2** | Unicode sanitization与 ASCII 走私防御 — NFKC + 不可见字符剥离 + 递归sanitization [↓](./qwen-code-improvement-report-p2-stability.md#item-29) | 无sanitization | 中 | — |
| **P2** | sandbox运行时集成 — seatbelt/bubblewrap/Docker + 文件/网络限制 [↓](./qwen-code-improvement-report-p2-stability.md#item-30) | 可选/非默认 | 大 | [PR#3146](https://github.com/QwenLM/qwen-code/pull/3146) ✓（配置项，非默认启用） |
| **P2** | SSRF 防护 — 私有 IP 阻断 + IPv4-mapped + DNS rebinding 防护 [↓](./qwen-code-improvement-report-p2-stability.md#item-31) | 仅基础 isPrivateIp | 中 | — |
| **P2** | WebFetch 域名allowlist — 130+ 预批准域名 + 路径段边界匹配 [↓](./qwen-code-improvement-report-p2-stability.md#item-32) | 无内置allowlist | 小 | — |
| **P2** | 子进程环境变量清洗 — 30+ 敏感变量自动剥离 [↓](./qwen-code-improvement-report-p2-stability.md#item-33) | 继承完整环境 | 中 | — |
| **P2** | 工具输出密钥扫描 — 50+ gitleaks 规则 + 写入阻断 [↓](./qwen-code-improvement-report-p2-stability.md#item-34) | 无扫描 | 中 | — |
| **P2** | privilege escalation防护 — auto 模式 60+ 危险规则自动剥离 [↓](./qwen-code-improvement-report-p2-stability.md#item-35) | yolo 批准所有 | 中 | [PR#3048](https://github.com/QwenLM/qwen-code/pull/3048) |
| **P3** | [动态状态栏](./dynamic-status-bar-deep-dive.md) — 模型/工具可实时更新状态文本 [↓](./qwen-code-improvement-report-p3-features.md#item-1) | 仅静态 Footer | 小 | — |
| **P3** | [上下文折叠](./context-compression-deep-dive.md) — History Snip（Claude Code 自身仅 scaffolding，未完整实现） [↓](./qwen-code-improvement-report-p3-features.md#item-2) | 缺失 | 大 | — |
| **P3** | [内存诊断](./memory-diagnostics-deep-dive.md) — V8 heap dump + 1.5GB 阈值触发 + leak 建议 + smaps 分析 [↓](./qwen-code-improvement-report-p3-features.md#item-3) | 缺失 | 中 | — |
| **P3** | [Feature Gates](./feature-gates-deep-dive.md) — GrowthBook 远程特性开关 + A/B 测试 + 按事件动态采样 [↓](./qwen-code-improvement-report-p3-features.md#item-4) | 缺失 | 中 | — |
| **P3** | [DXT/MCPB 插件包](./zip-bomb-protection-deep-dive.md) — zip bomb 防护（512MB/文件，1GB 总量，50:1 压缩比限制） [↓](./qwen-code-improvement-report-p3-features.md#item-5) | 缺失 | 中 | — |
| **P3** | [/security-review](./security-review-command-deep-dive.md) — 基于 git diff 的安全审查命令，聚焦漏洞检测 [↓](./qwen-code-improvement-report-p3-features.md#item-6) | 缺失 | 小 | — |
| **P3** | [Ultraplan](./ultraplan-remote-planning-deep-dive.md) — 启动远程 CCR 会话，用更强模型深度规划后回传结果 [↓](./qwen-code-improvement-report-p3-features.md#item-7) | 缺失 | 大 | — |
| **P3** | [Advisor 顾问模型](./advisor-model-deep-dive.md) — /advisor 配置副模型审查主模型输出，多模型协作 [↓](./qwen-code-improvement-report-p3-features.md#item-8) | 缺失 | 中 | — |
| **P3** | [Vim 完整实现](./vim-emulation-deep-dive.md) — motions + operators + textObjects + transitions 完整体系 [↓](./qwen-code-improvement-report-p3-features.md#item-9) | 基础 vim.ts | 中 | — |
| **P3** | [语音模式](./voice-mode-deep-dive.md) — push-to-talk 语音输入 + 流式 STT 转录 + 可重绑快捷键 [↓](./qwen-code-improvement-report-p3-features.md#item-10) | 缺失 | 大 | — |
| **P3** | [插件市场](./plugin-marketplace-lifecycle-deep-dive.md) — 插件发现、安装、版本管理 + 生命周期治理 [↓](./qwen-code-improvement-report-p3-features.md#item-11) | 缺失 | 大 | — |
| **P3** | [sandbox excludedCommands](./sandbox-excluded-commands-deep-dive.md) — 安全命令排除 sandbox 限制 [↓](./qwen-code-improvement-report-p3-features.md#item-12) | 无排除机制 | 小 | — |
| **P3** | [/privacy-settings 交互式隐私对话框](./privacy-settings-dialog-deep-dive.md) [↓](./qwen-code-improvement-report-p3-features.md#item-13) | 无交互 UI | 小 | — |
| **P3** | [/extra-usage 企业用量管理](./enterprise-usage-management-deep-dive.md) [↓](./qwen-code-improvement-report-p3-features.md#item-14) | 仅 /cost | 中 | — |
| **P3** | [/rate-limit-options 限速选项菜单](./rate-limit-options-deep-dive.md) [↓](./qwen-code-improvement-report-p3-features.md#item-15) | 仅错误消息 | 小 | — |
| **P3** | [/remote-setup CCR 远程环境设置](./remote-ccr-setup-deep-dive.md) [↓](./qwen-code-improvement-report-p3-features.md#item-16) | 无远程配置 | 中 | — |
| **P3** | `--config-dir` CLI flag — 覆盖 `~/.qwen/` 配置目录（CI/多租户/DevContainer 场景，Copilot CLI v0.0.382 参考） [↓](./qwen-code-improvement-report-p3-features.md#item-17) | 仅 `QWEN_HOME` env var（PR#2953 open） | 小 | — |
| **P3** | [Virtual Scrolling 虚拟滚动](./virtual-scrolling-deep-dive.md) — 仅渲染可视区域消息 [↓](./qwen-code-improvement-report-p3-ux.md#item-1) | 全量渲染 | 中 | — |
| **P3** | [Feedback Survey 用户反馈](./feedback-survey-deep-dive.md) — 内置 /feedback 评分+文字表单 [↓](./qwen-code-improvement-report-p3-ux.md#item-2) | 无内置反馈 | 小 | — |
| **P3** | [Turn Diffs 轮次差异统计](./turn-diffs-deep-dive.md) — 每轮变更文件数+增删行数汇总 [↓](./qwen-code-improvement-report-p3-ux.md#item-3) | 仅 per-file diff | 小 | — |
| **P3** | [LogoV2 品牌标识](./logov2-brand-identity-deep-dive.md) — ASCII art + 启动功能引导 [↓](./qwen-code-improvement-report-p3-ux.md#item-4) | 纯文本 | 小 | — |
| **P3** | [Buddy 伴侣精灵](./buddy-companion-deep-dive.md) — 可见助手 + 状态动画 + 空闲引导 [↓](./qwen-code-improvement-report-p3-ux.md#item-5) | 无 | 中 | — |
| **P3** | [useMoreRight 右面板](./right-panel-ui-deep-dive.md) — 对话+文件预览并排显示 [↓](./qwen-code-improvement-report-p3-ux.md#item-6) | 单列布局 | 中 | — |
| **P3** | iTerm/Terminal 状态备份恢复 — 异常退出后终端状态自动修复 [↓](./qwen-code-improvement-report-p3-ux.md#item-7) | 基础清理 | 小 | — |
| **P3** | settingsSync 设置同步 — 跨设备设置同步到云端/git [↓](./qwen-code-improvement-report-p3-ux.md#item-8) | 仅本地存储 | 中 | — |
| **P3** | Auto Mode 子命令管理 — defaults/config/critique 三个子命令 [↓](./qwen-code-improvement-report-p3-ux.md#item-9) | 无子命令 | 小 | — |
| **P3** | useInboxPoller 收件箱轮询 — 多 Agent 邮箱定期检查 [↓](./qwen-code-improvement-report-p3-hooks.md#item-1) | 无统一轮询 | 小 | [PR#2886](https://github.com/QwenLM/qwen-code/pull/2886) |
| **P3** | 团队通信协议 — 邮箱协议（SendMessage/心跳/关闭请求/RequestRecord） [↓](./qwen-code-improvement-report-p3-hooks.md#item-33) | 仅文件 IPC | 中 | — |
| **P3** | useRemoteSession 远程会话 Hook [↓](./qwen-code-improvement-report-p3-hooks.md#item-2) | 无 | 小 | — |
| **P3** | useDiffInIDE IDE 差异查看 [↓](./qwen-code-improvement-report-p3-hooks.md#item-3) | 终端内 diff | 小 | — |
| **P3** | useCancelRequest 取消请求 Hook [↓](./qwen-code-improvement-report-p3-hooks.md#item-4) | 分散处理 | 小 | — |
| **P3** | AgentSummary 代理摘要 [↓](./qwen-code-improvement-report-p3-hooks.md#item-5) | 无 | 小 | — |
| **P3** | useBackgroundTaskNavigation 后台任务导航 [↓](./qwen-code-improvement-report-p3-hooks.md#item-6) | 无 | 小 | — |
| **P3** | useTaskListWatcher 任务监控 [↓](./qwen-code-improvement-report-p3-hooks.md#item-7) | 无 | 小 | — |
| **P3** | useDirectConnect 直连 [↓](./qwen-code-improvement-report-p3-hooks.md#item-8) | 无 | 小 | — |
| **P3** | useAssistantHistory 代理历史 [↓](./qwen-code-improvement-report-p3-hooks.md#item-9) | 无 | 小 | — |
| **P3** | useSSHSession SSH 会话 [↓](./qwen-code-improvement-report-p3-hooks.md#item-10) | 无 | 小 | — |
| **P3** | useSwarmPermissionPoller 权限轮询 [↓](./qwen-code-improvement-report-p3-hooks.md#item-11) | 无 | 小 | — |
| **P3** | useTasksV2 任务 Hook [↓](./qwen-code-improvement-report-p3-hooks.md#item-12) | 无 | 小 | — |
| **P3** | useArrowKeyHistory 历史导航 [↓](./qwen-code-improvement-report-p3-hooks.md#item-13) | 无 | 小 | — |
| **P3** | useCanUseTool 工具可用性 [↓](./qwen-code-improvement-report-p3-hooks.md#item-14) | 无 | 小 | — |
| **P3** | useSearchInput 搜索输入 [↓](./qwen-code-improvement-report-p3-hooks.md#item-15) | 无 | 小 | — |
| **P3** | usePasteHandler 粘贴处理 [↓](./qwen-code-improvement-report-p3-hooks.md#item-16) | 分散处理 | 小 | — |
| **P3** | useScheduledTasks 定时任务 [↓](./qwen-code-improvement-report-p3-hooks.md#item-17) | 无 UI hook | 小 | — |
| **P3** | useVimInput Vim 输入 [↓](./qwen-code-improvement-report-p3-hooks.md#item-18) | 基础 vim | 小 | — |
| **P3** | useLspPluginRecommendation LSP 推荐 [↓](./qwen-code-improvement-report-p3-hooks.md#item-19) | 无 | 小 | — |
| **P3** | unifiedSuggestions 统一建议 [↓](./qwen-code-improvement-report-p3-hooks.md#item-20) | 分散 | 小 | — |
| **P3** | useInputBuffer 输入缓冲 [↓](./qwen-code-improvement-report-p3-hooks.md#item-21) | 无 | 小 | — |
| **P3** | useIssueFlagBanner 问题通知 [↓](./qwen-code-improvement-report-p3-hooks.md#item-22) | 无 | 小 | — |
| **P3** | useDiffData 差异数据 [↓](./qwen-code-improvement-report-p3-hooks.md#item-23) | 组件内部 | 小 | — |
| **P3** | toolUseSummary 工具使用摘要 [↓](./qwen-code-improvement-report-p3-hooks.md#item-24) | 无 | 小 | — |
| **P3** | useAwaySummary 离开摘要 [↓](./qwen-code-improvement-report-p3-hooks.md#item-25) | 无 | 小 | — |
| **P3** | useCommandKeybindings 命令快捷键 [↓](./qwen-code-improvement-report-p3-hooks.md#item-26) | 分离管理 | 小 | — |
| **P3** | usePluginRecommendationBase 插件推荐 [↓](./qwen-code-improvement-report-p3-hooks.md#item-27) | 无 | 小 | — |
| **P3** | useSkillImprovementSurvey Skill 反馈 [↓](./qwen-code-improvement-report-p3-hooks.md#item-28) | 无 | 小 | — |
| **P3** | usePrStatus PR 状态 [↓](./qwen-code-improvement-report-p3-hooks.md#item-29) | 无 | 小 | — |
| **P3** | useLogMessages 日志消息 [↓](./qwen-code-improvement-report-p3-hooks.md#item-30) | 分散 | 小 | — |
| **P3** | useClaudeCodeHintRecommendation 提示推荐 [↓](./qwen-code-improvement-report-p3-hooks.md#item-31) | 无 | 小 | — |
| **P3** | /sandbox-toggle sandbox 切换 [↓](./qwen-code-improvement-report-p3-hooks.md#item-32) | 需重启 | 小 | — |

> 点击改进点名称可跳转到 Deep-Dive 文章；每项的详细说明（缺失后果 + 改进收益 + 建议方案）见 [§三](#三全部改进点详细说明)。

## 三、全部改进点详细说明

按优先级分文件，点击查看每项的 Claude Code 实现机制、缺失后果、改进收益和建议方案：

| 文件 | 内容 | 项数 |
|------|------|:----:|
| [P0/P1 核心能力](./qwen-code-improvement-report-p0-p1-core.md) | 上下文压缩、Subagent、Speculation、记忆系统、工具并行、启动优化、闭环学习等 | 14 |
| [P0/P1 平台集成](./qwen-code-improvement-report-p0-p1-platform.md) | GitHub Actions CI、Code Review、SDK、Remote Control Bridge、GitLab 等 | 9 |
| [P0/P1 引擎优化](./qwen-code-improvement-report-p0-p1-engine.md) | 流式执行、缓存、Token 管理、崩溃恢复、Agent 编排、上下文管理、安全等 | 27 |
| [P2 核心功能与企业特性](./qwen-code-improvement-report-p2-core.md) | 中等优先级（Shell 安全、MDM 企业策略、Token 计数、Computer Use、AgentScope Plan/A2A/OTel 参考等） | 26 |
| [P2 工具与命令](./qwen-code-improvement-report-p2-tools-commands.md) | 中等优先级（Conditional Hooks、/batch、MCP 重连、Ripgrep 回退、Skill 模型覆盖、PreCompact Hook、模型调用 Slash 命令、/experimental 门控等） | 26 |
| [P2 界面与 UX](./qwen-code-improvement-report-p2-tools-ui.md) | 中等优先级（Token 警告、Spinner、/rewind、Diff 渲染、/plan、大粘贴外化等） | 21 |
| [P2 性能优化](./qwen-code-improvement-report-p2-perf.md) | 中等优先级（流式执行、缓存模式、延迟初始化、请求合并、指令文件去重等） | 35 |
| [P2 稳定性、安全与 CI/CD](./qwen-code-improvement-report-p2-stability.md) | 中等优先级（Unicode sanitization、sandbox集成、SSRF 防护、密钥扫描、PID namespace、Session Recap、显示高度控制、输出截断、Bash UI、Update/Diff UI 等） | 49 |
| [P3 功能特性](./qwen-code-improvement-report-p3-features.md) | 低优先级功能特性（动态状态栏、Feature Gates、Vim、语音、插件市场、--config-dir 等） | 17 |
| [P3 用户体验](./qwen-code-improvement-report-p3-ux.md) | 低优先级用户体验（Virtual Scrolling、Turn Diffs、Buddy、settingsSync 等） | 9 |
| [P3 Hook 与组件](./qwen-code-improvement-report-p3-hooks.md) | 低优先级 Hook 与组件（useInboxPoller、AgentSummary、usePrStatus 等） | 33 |

## 四、架构差异总结

| 维度 | Claude Code | Qwen Code | 差距评估 | 进展 |
|------|-------------|-----------|----------|------|
| **[Mid-Turn Queue Drain](./command-queue-orchestration-deep-dive.md)** | `query.ts` 工具批次间 drain | 无 | 显著落后 | [PR#2854](https://github.com/QwenLM/qwen-code/pull/2854) ✓ |
| 压缩 (Compression) 策略 | 4 层分层压缩 | 单一阈值压缩 | 显著落后 | — |
| Subagent | 支持 fork + 上下文继承 | 仅预定义类型 | 显著落后 | [PR#2936](https://github.com/QwenLM/qwen-code/pull/2936) ✓ |
| **智能工具并行** | Kind-based batching（默认 10 并发） | Agent 并发 / 其他顺序 | 中等差距 | [PR#2864](https://github.com/QwenLM/qwen-code/pull/2864) ✓ |
| 投机执行 (Speculation) | 完整 overlay-fs + cow（991 行） | v0.15.0 已完整实现（563 行），默认关闭 | 小差距 | [PR#2525](https://github.com/QwenLM/qwen-code/pull/2525) ✓ |
| 启动优化 | API Preconnect + Early Input | 无 | 缺失 | [PR#3085](https://github.com/QwenLM/qwen-code/pull/3085) / [PR#3232](https://github.com/QwenLM/qwen-code/pull/3232) ✓（profiler） |
| 按路径注入上下文规则 | `.claude/rules/` + frontmatter `paths:` 惰加载 | ✅ `.qwen/rules/` + frontmatter `paths:` + 嵌套子目录 | **已对齐** | [PR#3339](https://github.com/QwenLM/qwen-code/pull/3339) ✓ |
| 会话记忆 (Session Memory) | SessionMemory + memdir | 简单笔记工具 | 显著落后 | — |
| 自动记忆 (Memory) 整理 | Auto Dream | 无 | 缺失 | — |
| 上下文折叠 (Context Collapse) | History Snip | 无 | 缺失 | — |
| Shell 安全增强 | 25+ 检查 + tree-sitter | AST-only 读写分类 | 中等差距 | — |
| MDM 企业策略 | plist + Registry + 远程 API | 无 | 缺失 | — |
| Token 实时计数 | API 计数 + VCR 缓存 | 静态模式匹配 | 中等差距 | — |
| 工具发现 | ToolSearchTool | 无 | 缺失 | — |
| 多 Agent通信 | SendMessageTool | 无 | 缺失 | — |
| 文件索引 | FileIndex（fzf 风格） | 依赖 rg/glob | 中等差距 | [PR#3214](https://github.com/QwenLM/qwen-code/pull/3214)（git ls-files + rg） |
| Commit Attribution | Co-Authored-By 追踪 | 无 | 缺失 | [PR#3115](https://github.com/QwenLM/qwen-code/pull/3115) |
| 会话分支 | /branch 对话分叉 | 无 | 缺失 | [PR#3022](https://github.com/QwenLM/qwen-code/pull/3022) ✗（已关闭）/ [PR#3292](https://github.com/QwenLM/qwen-code/pull/3292)（跟进） |
| Output Styles | Learning / Explanatory 模式 | 无 | 缺失 | — |
| Fast Mode | 速度/成本分级推理 | `fastModel` 不同方案（另一个模型） | ⚠️ 部分 | [PR#3077](https://github.com/QwenLM/qwen-code/pull/3077) ✓ / [PR#3086](https://github.com/QwenLM/qwen-code/pull/3086) ✓ / [PR#3120](https://github.com/QwenLM/qwen-code/pull/3120) ✓ |
| 并发 Session | 多终端 PID 追踪 + 后台脱附 | 无 | 缺失 | — |
| Git Diff 统计 | 结构化 diff + 按文件统计 | 无 git-aware stats | 中等差距 | — |
| 文件历史快照 | per-file SHA256 + 按消息恢复 | checkpoint（git 级） | 小差距 | — |
| **流式工具执行** | StreamingToolExecutor 流水线 | 等完整响应 | 显著落后 | — |
| **文件读取缓存** | FileReadCache 1000 LRU + 批量并行 | 无缓存/顺序读取 | 显著落后 | — |
| **记忆异步prefetch** | Memory prefetch + skill prefetch | 无 | 缺失 | — |
| **Token Budget 续行** | 90% 续行 + 递减检测 + 分层回退 | 70% 一次性压缩 | 中等差距 | — |
| **MCP 动态插槽** | pMap + dual-tier concurrency | 无并发限制 | 小差距 | — |
| **通用缓存模式** | memoizeWithTTL + memoizeWithLRU | 仅搜索缓存 | 中等差距 | — |
| **同步 I/O** | 绝大多数 async | 多处 readFileSync | 显著落后 | — |
| **Prompt Cache** | 分段 + schema 锁定 + 缓存失效检测 | 无分段 | 显著落后 | — |
| **请求合并** | coalescing + BoundedUUIDSet | 无 | 缺失 | — |
| **延迟初始化** | lazySchema + 延迟 import + 延迟prefetch | 全量同步加载 | 中等差距 | — |
| **Git 直读** | .git/HEAD+refs 直读 + LRU | spawn git | 中等差距 | — |
| **崩溃恢复** | 中断检测 + 合成续行 + 全量恢复 | 无 | 缺失 | — |
| **API 重试** | 10 次退避 + 529 降级 + 持久化重试 | 仅重试次数 | 显著落后 | [PR#3080](https://github.com/QwenLM/qwen-code/pull/3080) / [PR#3246](https://github.com/QwenLM/qwen-code/pull/3246) ✓ |
| **优雅关闭** | SIGINT/SIGTERM + 清理注册 + failsafe | 无信号处理 | 缺失 | — |
| **反应式压缩** | prompt_too_long 自动裁剪重试 | 无 | 缺失 | — |
| **原子写入** | temp+rename + 大结果persist to disk | 直接 writeFileSync | 中等差距 | — |
| **自动检查点** | 默认启用 + per-message 快照 | 默认关闭 | 中等差距 | — |
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
| [Mid-Turn Queue Drain](./command-queue-orchestration-deep-dive.md) | [输入队列与中断机制](./input-queue-deep-dive.md) |
| 上下文压缩 | [上下文压缩算法](./context-compression-deep-dive.md) |
| Fork Subagent | [Fork Subagent](./fork-subagent-deep-dive.md) |
| 智能工具并行 | [工具并行执行](./tool-parallelism-deep-dive.md) |
| Shell 安全 | [Shell 安全模型](./shell-security-deep-dive.md) |
| 启动优化 | [启动阶段优化](./startup-optimization-deep-dive.md) |
| 指令文件加载 | [指令文件加载](./instruction-loading-deep-dive.md) |
| MDM 企业配置 | [MDM 企业配置管理](./mdm-enterprise-deep-dive.md) |
| 遥测架构 | [遥测架构](./telemetry-architecture-deep-dive.md) |
| Token 估算 | [Token 估算与 Thinking](./token-estimation-deep-dive.md) |
| 会话记忆 | [记忆系统](./memory-system-deep-dive.md) |
| 多 Agent通信 | [多 Agent系统](./multi-agent-deep-dive.md) |
| 插件/Hook 扩展 | [Hook 与插件扩展](./hook-plugin-extension-deep-dive.md) |
| MCP 集成 | [MCP 集成](./mcp-integration-deep-dive.md) |
| 成本与 Fast Mode | [成本追踪与 Fast Mode](./cost-fastmode-deep-dive.md) |
| Git 工作流与会话 | [Git 工作流与会话管理](./git-workflow-session-deep-dive.md) |
| 工具动态发现 | [工具搜索与延迟加载](./tool-search-deep-dive.md) |
| Team Memory | [组织级记忆同步](./team-memory-deep-dive.md) |
| Computer Use | [桌面自动化](./computer-use-deep-dive.md) |
| Deep Link | [协议处理与终端启动](./deep-link-protocol-deep-dive.md) |
| Remote Control Bridge | [远程控制桥接](./remote-control-bridge-deep-dive.md) |
| 功能矩阵 | [功能对比矩阵](./features.md) |

### Claude Code 源码文档

| 领域 | 文章 |
|------|------|
| 架构总览 | [技术架构（22 节）](../tools/claude-code/03-architecture.md) |
| 工具系统 | [工具系统](../tools/claude-code/04-tools.md) |
| 多 Agent / Swarm | [多 Agent系统](../tools/claude-code/09-multi-agent.md) |
| Prompt Suggestions | [Prompt Suggestions + Speculation](../tools/claude-code/10-prompt-suggestions.md) |
| 终端渲染 | [终端渲染与防闪烁](../tools/claude-code/11-terminal-rendering.md) |
| 设置与安全 | [设置与安全](../tools/claude-code/06-settings.md) |
| 会话与记忆 | [会话与记忆](../tools/claude-code/07-session.md) |
| Hook 系统 | [Hook 系统（27 事件）](../tools/claude-code/12-hooks.md) |
| 系统提示 | [系统提示构建](../tools/claude-code/13-system-prompt.md) |
| MCP 集成 | [MCP 集成（6 传输）](../tools/claude-code/14-mcp.md) |
| 遥测与 Feature Flag | [遥测与 Feature Flag](../tools/claude-code/15-telemetry-feature-flags.md) |
| 参考速查 | [数据结构 + 术语表](../tools/claude-code/19-reference.md) |
| 查询状态转换 | [查询状态转换模型](../tools/claude-code/20-query-transitions.md) |
| 工具执行运行时 | [工具执行运行时](../tools/claude-code/21-tool-execution-runtime.md) |
| 消息管线 | [消息与提示管线](../tools/claude-code/22-message-pipeline.md) |

---

## 六、更新日志

### 2026-04-22（反馈循环最快记录 · item-46 5-line window 由用户本人补齐）

**[PR#3508](https://github.com/QwenLM/qwen-code/pull/3508)（2026-04-21 23:10 UTC 提交，OPEN）—— 作者 `wenshao`（即 codeagents 项目维护者本人）**。

**闭环链路**：
1. 2026-04-20 深夜——我添加 item-46 / item-47 / Bash Deep-Dive，明确"5 行窗口"缺失
2. 2026-04-21 09:00——扫描 PR#3155，标记 item-46 为 🟡 部分实现（`+N lines` 有 / 5 行窗口缺）
3. 2026-04-21 17:00——用户追问 "结合 PR#3155 看 item-47"，勘误 ✓ → 🟡 变体实现
4. 2026-04-21 23:10 UTC——**用户亲自提交 PR#3508**，补齐 5 行窗口部分

**PR#3508 设计亮点**（超越 Claude Code 原设计）：

| 特性 | Claude `ShellProgressMessage` | PR#3508 |
|---|---|---|
| 默认行数 | 硬编码 `lines.slice(-5)` | `ui.shellOutputMaxLines: 5`（settings dialog 可视化编辑）|
| bypass 机制 | 1 种（verbose mode）| **6 种**（`!` 用户命令 / 确认等待 / 真实失败 / Ctrl+F focus / opt-out / 自定义值）|
| 覆盖面 | Streaming 流式 | Streaming + 完成态字符串渲染器（两处都裁剪）|
| 语义区分 | 无 | **exit≠0 不算 tool failure**——避免命令偶然失败导致整屏输出 |

**设计决策的精妙**（PR 原文）：

> A shell command exiting with non-zero status (e.g. `seq 1 30 && false`, `command not found`) does **not** trigger the Error bypass — **the tool itself succeeded**, the spawned command failed. This is intentional: cap behavior stays consistent regardless of command exit code.

这是 Claude Code 原设计**没有**体现的语义分离——tool success ≠ command exit code。

**状态变更**：
- item-46 主矩阵：🟡 部分实现 → 🟡 **拆分实现中**（PR#3155 ✓ `+N lines` + PR#3508 🟡 OPEN 5 行窗口，合并后 ✓ 完整）
- item-46 的追踪 PR 列表：从 PR#3155 单独 → **PR#3155 + PR#3508 组合**

**反馈链路观察**：**从规格补充到 PR 提交耗时约 24 小时**——创纪录的闭环速度。项目的规格文档**不仅描述现状，还在主动塑造实现方向**。

**PR#3508 合并后应跟进**：
1. 将 item-46 状态从 🟡 → ✓ 完整实现
2. 更新 Bash Deep-Dive 第 2.1 节的"Qwen Code 现状"描述
3. README 已合并 ✓ 66 → 67（+PR#3508）
4. 考虑是否基于 PR#3508 的 6-bypass 模式，反向优化 Claude Code（可写入 update-tool-display-deep-dive 第 7 节）

### 2026-04-21（勘误 · PR#3155 与 item-47 的设计差异）

**勘误动机**：用户指出应"结合 PR#3155 仔细看 item-47"。经逐行对比 PR#3155 代码与 item-47 原规格，发现之前标记 "✓ 完整实现" 不准确——**PR#3155 和 Claude Code 的 `ShellTimeDisplay` 功能等价但设计差异显著**。

**PR#3155 vs item-47 spec 5 处关键差异**：

| 方面 | Claude `ShellTimeDisplay` | PR#3155 | 判断 |
|---|---|---|---|
| 起始可见性 | 始终可见 | 3s 阈值 | 设计哲学差异（连续反馈 vs 静默到慢才显示）|
| 格式 | `(10.5s · timeout 30s)` 组合单元 | `3s` 独立 + `timeout 3s` 在 stats bar | 信息分散——Claude 的组合更紧凑 |
| 亚秒精度 | `formatDuration` `hideTrailingZeros: true`，支持 `10.5s` | 自定义 `formatElapsed`，仅整数秒 | PR 精度损失 |
| 位置 | 与 `Running…` 前缀**内联** | 工具行**右对齐**独立 flex child | Claude 语义连贯 vs PR 状态行装饰 |
| 工具范围 | Shell only | **所有工具**（覆盖更广）| PR 优势 |

**状态变更**：
- item-47 主矩阵：**✓ 完整实现 → 🟡 变体实现**（5 处差异明确列出）
- item-38 主矩阵：**✓ 完整实现 → 🟡 部分实现**（重要发现：PR#3155 覆盖墙钟/字节视觉反馈，**未**覆盖 Claude Code 的"语义化 progress events"——即 `yield { type: 'progress', toolUseCount }` 类结构化进度 + "Installing packages 42/100" 类 stdout 解析）
- item-46：保持 🟡 部分实现（之前就已正确标注）

**补齐成本（若要做 Claude 风格）**：
- item-47 补齐：~1 天（在现有 `ToolElapsedTime.tsx` 基础上增加组合格式选项 + Shell 专属 ShellProgressMessage 包装）
- item-38 补齐（真正的 progress events）：~3-5 天（core tool.execute 支持 yield + Shell stdout 解析器 + UI 语义映射）

**反思**：这次反馈循环教训——**"功能等价" 不等于 "完整实现"**。PR 合并后应该对比**设计细节**而非仅是**功能名称**。后续对 PR #3478/#3482/#3080 也需同样的精细比对。

### 2026-04-21（两日合并潮 · 项目史上反馈闭环最快的一次 🎯）

**极其重要的 48 小时**：我在 2026-04-20 晚间新增的 item-46/47（Bash 5 行窗口 + ShellTimeDisplay），被同一天上午已合并的 **[PR#3155](https://github.com/QwenLM/qwen-code/pull/3155)** 基本覆盖——这是**文档补上标签的速度落后于实现速度**的首次出现。

**🎯 追踪 item 直接落地（6 个 item，覆盖度不等）**：

| PR | 合并时间 | 对应 item | 状态变更 |
|---|---|---|---|
| **[PR#3155](https://github.com/QwenLM/qwen-code/pull/3155) ✓** | 2026-04-20 08:04 UTC | [item-38 工具执行进度消息](./qwen-code-improvement-report-p2-stability.md#item-38) | 未实现 → **✓ 完整实现**（3 合 1：elapsed + stats bar + OSC 9;4）|
| **同 PR#3155** | 同上 | [item-47 ShellTimeDisplay](./qwen-code-improvement-report-p2-stability.md#item-47) | 刚加入追踪 → **✓ 完整实现**（全工具右对齐 3s 阈值，覆盖面比 Claude Code 更广）|
| **同 PR#3155** | 同上 | [item-46 "5 行窗口 + +N lines 计数"](./qwen-code-improvement-report-p2-stability.md#item-46) | 刚加入追踪 → **🟡 部分实现**（`+N lines` 已实现，5 行窗口未实现）|
| **[PR#3478](https://github.com/QwenLM/qwen-code/pull/3478) ✓** | 2026-04-20 15:58 UTC | [item-43 会话 Recap](./qwen-code-improvement-report-p2-stability.md#item-43) | ✓ 进一步打磨（`/recap` pin 到输入框上方 + fastModel 默认对齐）|
| **[PR#3482](https://github.com/QwenLM/qwen-code/pull/3482) ✓** | 2026-04-21 06:39 UTC | 同上 item-43 | ✓ 进一步打磨（rework rendering + blur threshold setting）|
| **[PR#3080](https://github.com/QwenLM/qwen-code/pull/3080) ✓** | 2026-04-21 14:08 UTC | [item-21 CI 环境检测](./qwen-code-improvement-report-p2-stability.md#item-21) | ✓ 部分实现（persistent retry mode for unattended CI/CD）|

**⚠️ Revert**：

- **[PR#3468](https://github.com/QwenLM/qwen-code/pull/3468) ✓** 2026-04-20 08:40 UTC — **Revert "feat(core): add dynamic swarm worker tool"**。[PR#3433](https://github.com/QwenLM/qwen-code/pull/3433) 昨日刚合的动态 swarm worker 今天被整体回滚。[item-14 Coordinator/Swarm](./qwen-code-improvement-report-p0-p1-engine.md#item-14) 主矩阵标记从 ✓ 改为 ⚠️ revert。

**🆕 其他值得关注的合并（维护/新能力）**：

- [PR#3467](https://github.com/QwenLM/qwen-code/pull/3467) ✓ 2026-04-20 10:56 UTC — **安全修复**：防止格式不合法的 permission rule 退化为工具级 catch-all（权限系统 bug 防御）
- [PR#3329](https://github.com/QwenLM/qwen-code/pull/3329) ✓ 2026-04-21 09:01 UTC — `display real-time token consumption during streaming (#2742)`——对应 item-20 `/context` 的交互增强
- [PR#3313](https://github.com/QwenLM/qwen-code/pull/3313) ✓ 2026-04-21 09:04 UTC — `recover from truncated tool calls via multi-turn continuation`——截断工具调用的恢复机制
- [PR#3229](https://github.com/QwenLM/qwen-code/pull/3229) ✓ 2026-04-21 03:44 UTC — `/stats` 按起源 subagent 分行归因
- [PR#3469](https://github.com/QwenLM/qwen-code/pull/3469) ✓ 2026-04-21 07:53 UTC — `render markdown in generic and web-fetch tool outputs`（WebUI）
- [PR#3398](https://github.com/QwenLM/qwen-code/pull/3398) ✓ 2026-04-21 14:20 UTC — VSCode OAuth → Coding Plan / API Key provider setup
- [PR#3303](https://github.com/QwenLM/qwen-code/pull/3303) ✓ 2026-04-21 09:06 UTC — detect Zed.app on macOS
- [PR#3451](https://github.com/QwenLM/qwen-code/pull/3451) ✓ 2026-04-20 07:22 UTC — Windows PATH normalization for MCP stdio servers
- [PR#3458](https://github.com/QwenLM/qwen-code/pull/3458) ✓ 2026-04-21 13:47 UTC — OpenAI samplingParams pass-through
- [PR#3283](https://github.com/QwenLM/qwen-code/pull/3283) ✓ 2026-04-20 06:34 UTC — slash command capability-based filtering（Phase 1）
- [PR#3489](https://github.com/QwenLM/qwen-code/pull/3489) ✓ 2026-04-21 08:44 UTC — MCP OAuth URL clickable when wrapped
- [PR#3394](https://github.com/QwenLM/qwen-code/pull/3394) ✓ 2026-04-21 21:31 UTC — arena comparison summary

**⭐ 新开的重磅 PR**：

- **[PR#3491](https://github.com/QwenLM/qwen-code/pull/3491)**（OPEN）— `feat: add /diff command and git diff statistics utility` —— 新增 `/diff` 命令 + git diff 统计
- **[PR#3488](https://github.com/QwenLM/qwen-code/pull/3488)**（OPEN）— `feat(cli): background-agent UI — pill, combined dialog, detail view` —— background agent UI，对应 PR#3076（显式 run_in_background）的 UI 侧
- **[PR#3471](https://github.com/QwenLM/qwen-code/pull/3471)**（OPEN）— `feat(core): model-facing agent control (task_stop, send_message, per-agent transcript)` —— Agent 内部对 sub-agent 的控制能力
- **[PR#3507](https://github.com/QwenLM/qwen-code/pull/3507)**（OPEN）— `feat(cli): add sticky todo panel to app layouts` —— **sticky todo 面板**，新 UI 方向
- **[PR#3505](https://github.com/QwenLM/qwen-code/pull/3505)**（OPEN）— `fix(core): reject truncated subagent write_file calls` —— subagent 截断写入防护
- **[PR#3460](https://github.com/QwenLM/qwen-code/pull/3460)**（OPEN）— `feat(cli): auto-detect terminal theme ('auto' or unset)` —— 对应 terminal theme 检测方向

**📊 反馈循环观察**：PR#3155 的存在证明 Qwen Code 团队**在我写 item-46/47 规格时已经在做同样的事情**——这是**社区驱动优先级**和**独立工程推进**的巧合共振。我的规格不是因果原因，但文档的存在帮助未来开发者理解 PR#3155 的设计空间。

**计数更新**：
- 已合并 ✓ 65 → **66**（+PR#3155 覆盖 item-38+47，同时部分覆盖 item-46）
- 主矩阵 item-14 Coordinator/Swarm 状态：PR#3433 ✓ → ⚠️ revert（PR#3468）
- 主矩阵 item-38 状态：未实现 → ✓ 完整实现
- 主矩阵 item-47 状态：未实现 → ✓ 完整实现
- 主矩阵 item-46 状态：未实现 → 🟡 部分实现
- 主矩阵 item-43 Recap 继续累积合并：增 PR#3478 + PR#3482 两次打磨
- 主矩阵 item-21 CI 检测：PR#3080 ✓ persistent retry mode 补充

### 2026-04-20（深夜新增 2 项 · Update 工具展示）

**用户提问**："Update 的展示区别也调查一下" —— 延续前两轮对 Bash / 高度控制的分析，覆盖 Edit / Write / MultiEdit 类工具的 UI 差异。

**反直觉的发现**：**这个维度两边各有优势**——与 Bash/高度控制不同：
- Claude Code 默认展示**完整 diff**（`FileEditToolUpdatedMessage.tsx:88-97`）
- Qwen Code **WebUI 默认单行摘要**（`EditToolCall.tsx:149-181`），比 Claude 更紧凑
- Qwen Code **CLI 中等**，用 `MaxSizedBox` 自适应高度 + `═` 间隙符

**新增 Deep-Dive**：[Update 工具展示 Deep-Dive](./update-tool-display-deep-dive.md) —— 4 个场景对比（3 行小改 / 200 行大重构 / 500 行新文件 / string not found 失败），双向借鉴分析。

**新增 2 个追踪 item**（p2-stability 47 → 49）：
- **[item-48](./qwen-code-improvement-report-p2-stability.md#item-48)** 语义化 hunk 模型 + `singleHunk` 智能上下文——把 `Diff.createPatch()` 字符串改为 `Diff.structuredPatch()` 的 `StructuredPatchHunk[]`，消除 UI 层 `parseDiffWithLineNumbers()` regex（60 行代码可删），加入 `singleHunk ? 100_000 : 3` 智能 context（~150 行净改动，2-3 天）
- **[item-49](./qwen-code-improvement-report-p2-stability.md#item-49)** 多 hunk `...` 省略分隔符——参考 `StructuredDiffList.tsx` 用 `intersperse` 在 hunk 之间插入 dim color `...`（~30 行，0.5 天，依赖 item-48）

**关键源码验证**：
- `utils/diff.ts:9` `CONTEXT_LINES = 3`
- `utils/diff.ts:103` `context: singleHunk ? 100_000 : CONTEXT_LINES` ⭐ 智能上下文核心
- `utils/diff.ts:81-114` `getPatchFromContents()` 返回 `StructuredPatchHunk[]`
- `components/StructuredDiffList.tsx:16-29` 完整 `intersperse` + `NoSelect` + `Text dimColor` 实现
- `components/FileEditToolUpdatedMessage.tsx:62-110` 三种展示模式（preview hint / condensed / 默认完整 diff）
- Qwen `packages/core/src/tools/edit.ts:308, 433` `Diff.createPatch()` 字符串 patch
- Qwen `DiffRenderer.tsx:23-81` `parseDiffWithLineNumbers()` regex re-parse

**反向借鉴**（Qwen → Claude 的亮点，写入 Deep-Dive 第 7 节）：
- WebUI 默认单行摘要 + 展开交互（Claude 可作为用户选项）
- `═` 全宽横线 gap 折叠（Claude 的 `...` 仅 hunk 间，不处理 hunk 内大段无修改）

**总项数**：263 → **265**（+2）。p2-stability 47 → **49**。

### 2026-04-20（晚间新增 2 项 · Bash 任务展示）

**用户提问**："Claude Code 展示 Bash 任务时和 Qwen Code 的差别是怎样的？" —— 触发对 Bash 工具 UI 差异的深度研究。

**新增 Deep-Dive**：[Bash 任务展示 Deep-Dive](./bash-task-display-deep-dive.md) —— 归纳两条完全不同的路线：
- **Claude = 极简 + 时间轴**：5 行窗口 + `+N lines` 计数 + elapsed/timeout 倒计时
- **Qwen = 完整 + 数据维度**：整屏 PTY 30 行 + 100ms 刷新 + 字节计数 + 二进制检测

4 个用户场景对比（find 5000 行 / npm install 2m / ls 错误 / 并行 20 工具），揭示 Qwen 在**长任务时间维度**和**并行屏幕占用**上的明显劣势。

**新增 2 个追踪 item**（p2-stability 45 → 47）：
- **[item-46](./qwen-code-improvement-report-p2-stability.md#item-46)** Bash 执行中 "5 行窗口 + `+N lines` 计数" —— 复刻 `ShellProgressMessage` 的 `lines.slice(-5)` + `extraLines` 模式（~100 行，1-2 天，前置 item-44）
- **[item-47](./qwen-code-improvement-report-p2-stability.md#item-47)** `ShellTimeDisplay` 时间 + timeout 倒计时 —— 三种格式 `(timeout X)` / `(elapsed · timeout X)` / `(elapsed)`，dim color 显示（~80 行，1 天）

**组合效果**：item-44（MessageResponse + OffscreenFreeze）+ item-46（5 行 + 计数）+ item-47（时间显示）三项合并后，Qwen 的 Bash UI 达到与 Claude 相当的"紧凑 + 进度可见"效果。总投入 **~4-5 天**。

**关键源码验证**：
- `components/shell/ShellProgressMessage.tsx:42-82` 确认 `lines.slice(-5)` + `+${extraLines} lines` / `~${totalLines} lines` 双模式
- `components/shell/ShellProgressMessage.tsx:65` 确认 `<MessageResponse><OffscreenFreeze>` 包裹（复用 item-44 基础设施）
- `components/shell/ShellTimeDisplay.tsx` 完整 73 行，三种格式分支 L30/L52/L63 全部对应
- Qwen `packages/core/src/services/shellExecutionService.ts:636` 确认 `RENDER_THROTTLE_MS = 100`
- Qwen `shellExecutionService.ts:179-182` 确认二进制流检测 `MAX_SNIFF_SIZE = 4096`（**反向借鉴点**：Claude 无此保护）

**反向借鉴**：Claude Code 可从 Qwen 学习**二进制流检测**，防止 `cat /bin/ls` / `curl -o image.png` 破坏终端渲染。

**总项数**：261 → **263**（+2）。p2-stability 45 → **47**。

### 2026-04-20（下午新增 2 项 · 任务显示高度控制）

**用户提问**："Claude Code 的任务怎么控制显示高度，有哪些值得借鉴的？" —— 触发对 Claude Code UI 高度控制机制的深度研究。

**新增 Deep-Dive**：[任务显示高度控制 Deep-Dive](./task-display-height-deep-dive.md) —— 归纳 Claude Code 的 4 条高度控制机制：
- `MessageResponse` 单行容器（`height=1 overflowY=hidden`）—— 所有瞬态消息压缩到 1 行
- `OffscreenFreeze` 离屏冻结（`useRef` 引用缓存 + `useTerminalViewport`）—— 历史 spinner 0 CPU
- `Ratchet` 最小高度锁定 —— 滚动不抖动
- 三级输出截断（Bash 30K / 单工具 50K / 单消息 200K）—— 防 context 爆炸

**新增 2 个追踪 item**（p2-stability 43 → 45）：
- **[item-44](./qwen-code-improvement-report-p2-stability.md#item-44)** 瞬态消息单行容器 + 离屏历史冻结 —— 复刻 MessageResponse + OffscreenFreeze 模式（~200 行，~3-4 天）
- **[item-45](./qwen-code-improvement-report-p2-stability.md#item-45)** 三级输出截断 —— Bash 30K default / 150K upper + env var `QWEN_BASH_MAX_OUTPUT_LENGTH` + 单工具 50K 持久化 + 单消息 200K 批量预算（~250 行，~4 天，可拆 3 PR）

**关键源码验证**（`/root/git/claude-code-leaked/`）：
- `components/MessageResponse.tsx:37` 确认 `<Box height={height} overflowY="hidden">`
- `components/OffscreenFreeze.tsx:23-42` 确认 `'use no memo'` + `useRef` 冻结
- `components/design-system/Ratchet.tsx:38-65` 确认 `measureElement` + `setMinHeight`
- `utils/shell/outputLimits.ts:3-14` 确认 `BASH_MAX_OUTPUT_DEFAULT=30_000` + `UPPER_LIMIT=150_000`
- `constants/toolLimits.ts:13-56` 确认 6 个常量（`DEFAULT_MAX_RESULT_SIZE_CHARS=50_000`、`MAX_TOOL_RESULTS_PER_MESSAGE_CHARS=200_000` 等）

**总项数**：260 → **261**（+2，同时修正历史计数 1 处偏差）。p2-stability 43 → **45**。

### 2026-04-20（清晨合并潮 🎉）

**昨晚 item 规格 → 今晨直接合并**——再次出现 "今天完整规格补充 → 次日合并实现" 的正反馈循环。

**🎯 追踪 item 直接落地（1 个）**：

| PR | 合并时间 | 对应 item | 意义 |
|---|---|---|---|
| **[PR#3160](https://github.com/QwenLM/qwen-code/pull/3160) ✓** | 2026-04-20 03:09 UTC | [p2-tools-commands item-21 PDF / 二进制文件读取](./qwen-code-improvement-report-p2-tools-commands.md#item-21) | **昨晚刚加入追踪（09:09 UTC 左右），6 小时后即合并**——`read_file` 现已支持 PDF 文本提取 + Jupyter Notebook 解析。item-21 状态：🟡 追踪 → ✓ 部分实现（P0 + P2 完成，仅剩图片/Office 两项） |

**🆕 新合并（3 个，维护/新能力但未在追踪 item 内）**：

- [PR#3448](https://github.com/QwenLM/qwen-code/pull/3448) ✓ **2026-04-20 02:01 UTC** — `feat(cli): add bare startup mode`：新增 `--bare` 启动模式（CI/脚本专用），跳过 hooks/LSP/auto memory/skills/ambient extensions/MCP 等所有隐式启动发现，仅保留最小工具集 `read_file + edit + run_shell_command`，也可通过 `QWEN_CODE_SIMPLE=1` 环境变量启用。对标 Claude Code 的 `--print`/非交互模式。**可考虑加入追踪 item**（CI 场景启动优化新方向）。
- [PR#3445](https://github.com/QwenLM/qwen-code/pull/3445) ✓ **2026-04-20 03:06 UTC** — `feat(cli): add slashCommands.disabled setting to gate slash commands`：新增 `slashCommands.disabled` 配置以禁用特定 slash 命令，是 [item-26 /experimental 实验特性统一门控](./qwen-code-improvement-report-p2-tools-commands.md#item-26) 思路的部分实现（gate 层已就位，但不是专门的 "experimental" 注册表）。
- [PR#3450](https://github.com/QwenLM/qwen-code/pull/3450) ✓ **2026-04-20 02:01 UTC** — `fix(vscode-ide-companion): preserve split stream message ordering`（VSCode IDE companion 消息排序修复）
- [PR#2593](https://github.com/QwenLM/qwen-code/pull/2593) ✓ **2026-04-20 02:02 UTC** — `feat(vscode-ide-companion): support /insight command`（VSCode companion 支持 `/insight` 命令）

**⭐ 新开的重磅 PR（1 个）**：

- **[PR#3455](https://github.com/QwenLM/qwen-code/pull/3455)**（🟡 OPEN，2026-04-20 02:25 UTC 创建）— **`perf(filesearch): move @-picker crawl and fzf index to worker_threads`**：将 `@`-picker 的递归文件爬取 + fzf 索引构建移出主线程到 `worker_threads`，避免在大仓库（100k 文件）按 `@` 时卡住 1–9 秒；同时引入 ripgrep 作为大仓库爬取后端（50k+ 文件下 3–4× 快于 `fdir`），CLI 启动时 pre-warm 索引。**这是对 [p2-perf item-9 延迟初始化与按需加载](./qwen-code-improvement-report-p2-perf.md#item-9) 的强化实现**（线程卸载 + ripgrep fast path）。

**计数更新**：已合并 ✓ 64 → **65**（+PR#3160 覆盖追踪 item-21 的 P0+P2）。其他 4 个 PR（#3448/#3445/#3450/#2593）属于能力扩展或维护修复，暂不计入 "追踪 item 直接实现" 计数。

### 2026-04-19（勘误 + 追加）

**勘误**：用户指出 [PR#2916](https://github.com/QwenLM/qwen-code/pull/2916)（`/context` 非交互输出 + SDK API）早在 **2026-04-13** 就已合并，但主矩阵 item-20 行仅标注了 PR#3042 的 ✓，遗漏了 PR#2916 本身。现已补标：
- 主矩阵 item-20 行：PR#2916 → **✓**
- p2-tools-ui item-20 详细页"进展"段落：`(open)` → **`✓（2026-04-13 合并）`**

此 item 的两个 PR 均已合并：
- [PR#2916](https://github.com/QwenLM/qwen-code/pull/2916) ✓ — 非交互模式 `/context` + `getContextUsage()` SDK API
- [PR#3042](https://github.com/QwenLM/qwen-code/pull/3042) ✓ — `/context` 新增 `detail` 子命令

**追踪合并数**：63 → **64**（+PR#2916）。

### 2026-04-19（晚间追加 · PDF/Notebook 支持 PR#3160）

**用户指出**：[p2-tools-commands item-21 PDF / 二进制文件读取](./qwen-code-improvement-report-p2-tools-commands.md#item-21) 应该跟踪 [PR#3160](https://github.com/QwenLM/qwen-code/pull/3160)（`feat(core): PDF text extraction fallback and Jupyter notebook parsing`）——此 PR 为 `read_file` 增加 PDF 文本提取 fallback + `.ipynb` Notebook 解析支持，合并后可直接覆盖 item-21 的 P0（PDF）+ P2（Notebook）两个目标。

**已更新**：
- 主矩阵 item-21 行：追踪 PR 列补充 [PR#3160](https://github.com/QwenLM/qwen-code/pull/3160) 🟡（OPEN），并将历史引用 PR#2024（拒绝 PDF）标记为 ✓ 合并
- [p2-tools-commands.md item-21](./qwen-code-improvement-report-p2-tools-commands.md#item-21)：新增 "追踪中的 PR" 小节 + 在修改方向中标注 PR#3160 正在推进 P0/P2 目标

**勘误**：此前主矩阵只标了 PR#2024 但未在该 PR 后打 ✓ 标记（该 PR 2026-03-15 已合并，拒绝 PDF 以防 session 污染）。现已补 ✓。

**待关注**：PR#3160 合并后需回头将 item-21 状态更新为"部分实现"——覆盖 PDF + Notebook，仅剩图片支持 + DOCX/XLSX/PPTX 两项尚未覆盖。

### 2026-04-19（凌晨大合并潮 🎉）

**极其重要的一天** —— 一夜之间 **多个长期追踪的 item 同时落地**，包括我昨天刚刚充实的 item-43 Session Recap！

**🎯 追踪 item 直接实现（6 个）**：

| PR | 合并时间 | 对应 item | 意义 |
|---|---|---|---|
| **[PR#3434](https://github.com/QwenLM/qwen-code/pull/3434) ✓** | 13:38 UTC | [p2-stability item-43 会话 Recap](./qwen-code-improvement-report-p2-stability.md#item-43) | **我昨天刚刚完整补充了 item-43 的版本/UI/Prompt 工程细节，今天就实现了！** |
| **[PR#3383](https://github.com/QwenLM/qwen-code/pull/3383) ✓** | 03:12 UTC | [p2-tools-commands item-25 Refresh Interval Statusline](./qwen-code-improvement-report-p2-tools-commands.md#item-25) | **refreshInterval 落地** |
| **[PR#3404](https://github.com/QwenLM/qwen-code/pull/3404) ✓** | 11:25 UTC | `/doctor` 诊断命令（对标 Claude Code） | 系统诊断命令（预期加入矩阵） |
| **[PR#3236](https://github.com/QwenLM/qwen-code/pull/3236) ✓** | 10:06 UTC | 增强 loop detection（含 PR#3178 stop directive） | 循环检测完整版 |
| **[PR#3433](https://github.com/QwenLM/qwen-code/pull/3433) ✓** | 06:47 UTC | [p0-p1-engine item-14 Coordinator/Swarm](./qwen-code-improvement-report-p0-p1-engine.md#item-14) | 动态 swarm worker 工具 |
| **[PR#3375](https://github.com/QwenLM/qwen-code/pull/3375) ✓** | 01:45 UTC | CI 治理 | 60+30 stale 策略正式合并（之前 item-42 note 里提到） |

**🆕 追踪 item 未覆盖的新合并（7 个，维护/改进）**：

- [PR#2734](https://github.com/QwenLM/qwen-code/pull/2734) ✓ 12:17 UTC — `add Markdown for Agents support to WebFetch tool`
- [PR#2857](https://github.com/QwenLM/qwen-code/pull/2857) ✓ 07:42 UTC — `constrain shell output width to prevent box overflow`
- [PR#2766](https://github.com/QwenLM/qwen-code/pull/2766) ✓ 07:25 UTC — `display ">100%" when context usage exceeds limit`
- [PR#3431](https://github.com/QwenLM/qwen-code/pull/3431) ✓ 06:59 UTC — `/clear dismisses /btw side-question dialog`
- [PR#3429](https://github.com/QwenLM/qwen-code/pull/3429) ✓ 07:06 UTC — `/btw use live conversation context`
- [PR#3436](https://github.com/QwenLM/qwen-code/pull/3436) ✓ 06:25 UTC — `support older Git during repository initialization`
- [PR#3438](https://github.com/QwenLM/qwen-code/pull/3438) ✓ 09:28 UTC — `remove abort listener during cleanup`
- [PR#2551](https://github.com/QwenLM/qwen-code/pull/2551) ✓ 12:45 UTC — `enable Plan Mode toggle and approval UI` (VSCode)

**⭐ 新开 PR（重磅）**：

- **[PR#3441](https://github.com/QwenLM/qwen-code/pull/3441)**（open）— **`add conversation rewind feature with double-ESC and /rewind command`** —— **对标 Claude Code 的 `/rewind` 命令！** 这是 [p2-tools-ui item-5 /rewind 检查点回退](./qwen-code-improvement-report-p2-tools-ui.md#item-5) 的直接实现。
- [PR#3445](https://github.com/QwenLM/qwen-code/pull/3445) — `slashCommands.disabled setting to gate slash commands`（slash 命令禁用配置）
- [PR#3442](https://github.com/QwenLM/qwen-code/pull/3442) — OAuth redirect URI 支持 MCP add
- [PR#3439](https://github.com/QwenLM/qwen-code/pull/3439) — `render LaTeX math in markdown output`

**📊 闭环奇迹观察**：**PR#3434 Recap 的实现直接受益于昨日 item-43 的完整规格补充**——包括版本时间线、UI rendering（dimColor + REFERENCE_MARK）、Prompt 工程要点（禁止 status reports/commit recaps）等。这是 codeagents 项目首次出现**"今天丰富 item 规格 → 明天 Qwen Code 合并实现"** 的正反馈循环。

**计数更新**：已合并 ✓ 57 → **63**（+PR#3434、+PR#3383、+PR#3404、+PR#3236、+PR#3433、+PR#3429 等 6 个追踪项）。

### 2026-04-18（晚间第三次补更）

自下午扫描（17:00 UTC）至晚间（19:30 UTC），qwen-code 合并节奏显著放缓——仅 **1 个维护性 PR**：

- [PR#3237](https://github.com/QwenLM/qwen-code/pull/3237) ✓ 19:14 UTC — `fix(build): invoke tsx directly via node --import instead of npx`（构建工具链优化，减少 npx 间接层）

**新开 PR**（观察）：

- [PR#3429](https://github.com/QwenLM/qwen-code/pull/3429) ✓（2026-04-19 合并）— `fix(cli): let /btw use live conversation context`（`/btw` 侧问题的上下文修复）

**观察**：合并节奏从全天 15+ PR 的高峰回落到单一维护性合并，符合发布前**清理收尾**的典型模式。结合 PR#3298 bumped version to 0.14.5（昨日合并），推测新版本即将发布。

**计数**：已合并 ✓ **57**（不变，PR#3237 是维护性合并不计入矩阵追踪）。

### 2026-04-18（下午第二次补更）

继续扫描 qwen-code PR（updated > 上午 05:00 UTC）：

**追踪范围内的合并**（1 个）：

- [PR#3319](https://github.com/QwenLM/qwen-code/pull/3319) ✓ **2026-04-18 16:40 UTC** — `feat(cli): add early input capture to prevent keystroke loss during startup`。**补齐 [item-8 启动优化](./qwen-code-improvement-report-p0-p1-core.md#item-8) 双支柱的下半段**（early input），preconnect 部分 PR#3318 仍 open。item-8 的早期输入捕获能力已落地。

**维护性合并**（5 个，无对应矩阵 item）：

- [PR#3393](https://github.com/QwenLM/qwen-code/pull/3393) ✓ 12:22 UTC — `feat(mcp): add OSC 52 copy hotkey for OAuth authorization URL`（改善 remote/SSH 场景复制 OAuth URL 体验）
- [PR#3416](https://github.com/QwenLM/qwen-code/pull/3416) ✓ 10:11 UTC — `wait for dual output stream shutdown`（PR#3352 sidecar mode 的后续修复）
- [PR#3415](https://github.com/QwenLM/qwen-code/pull/3415) ✓ 05:46 UTC — `update scheduler registry mock`（测试稳定性）
- [PR#2590](https://github.com/QwenLM/qwen-code/pull/2590) ✓ 15:39 UTC — `feat(vscode-ide-companion): add dedicated agent execution display`（VSCode IDE 集成增强）
- [PR#2550](https://github.com/QwenLM/qwen-code/pull/2550) ✓ 15:43 UTC — `perf(vscode): fix input lag in long conversations`（VSCode 长会话性能）

**批量 Stale 关闭**（~11 个 PR 在 09:21 UTC 同时关闭）：

PR#3375 的 stale 策略（60+30 天）生效后，清理了长期无活动的 PR：PR#2357（Node SEA binary）、PR#2509（anthropic thinking budget）、PR#2568-2585（一批 2026 年 2-3 月的 core 改进 PR）等。这是 qwen-code 项目治理成熟化的标志——**非关闭 = 放弃，而是路线调整**，部分方向已被后续更好的 PR 替代。

**新开 PR**（观察）：

- [PR#3428](https://github.com/QwenLM/qwen-code/pull/3428) — `fix(cli): dismiss /btw side-question dialog on /clear`（/btw UX）

**计数更新**：已合并 ✓ 56 → **57**（+PR#3319 追踪；其他 5 个是维护性合并不计入矩阵跟踪计数；批量 stale 关闭不影响追踪计数，因为那些都不在本报告追踪列表中）。

### 2026-04-18（次日清晨补更）

夜间到清晨 qwen-code 又合并了大量 PR：

**追踪范围内的合并**（4 个之前已纳入观察的 PR）：

- [PR#3178](https://github.com/QwenLM/qwen-code/pull/3178) ✓ **2026-04-18 02:24 UTC** — `detect tool validation retry loops and inject stop directive`（**循环检测增强**，防止 schema 验证失败时模型无限重试）
- [PR#3297](https://github.com/QwenLM/qwen-code/pull/3297) ✓ **2026-04-18 02:31 UTC** — `tool-registry: add lazy factory registration with inflight concurrency dedup`（**工具注册表性能优化**：懒加载工厂 + 并发去重）
- [PR#3381](https://github.com/QwenLM/qwen-code/pull/3381) ✓ **2026-04-18 00:02 UTC** — `reduce terminal redraw cursor movement`（终端重绘性能）
- [PR#3407](https://github.com/QwenLM/qwen-code/pull/3407) ✓ **2026-04-18 02:03 UTC** — `auto-submit on number key press in AskUserQuestionDialog`

**维护性合并**（11 个，无对应矩阵 item，仅记录）：

- [PR#2962](https://github.com/QwenLM/qwen-code/pull/2962) ✓ sandbox 镜像名 'latest' tag fallback
- [PR#2963](https://github.com/QwenLM/qwen-code/pull/2963) ✓ JSON schema "undefined Options" fix
- [PR#2964](https://github.com/QwenLM/qwen-code/pull/2964) ✓ clean script duplicate rmSync
- [PR#2966](https://github.com/QwenLM/qwen-code/pull/2966) ✓ integration tests stdinDoesNotEnd
- [PR#2969](https://github.com/QwenLM/qwen-code/pull/2969) ✓ text-buffer offset-to-position 统一
- [PR#2970](https://github.com/QwenLM/qwen-code/pull/2970) ✓ weixin PNG magic 4-byte 检查
- [PR#2975](https://github.com/QwenLM/qwen-code/pull/2975) ✓ 重新连接 AcpBridge listener
- [PR#2977](https://github.com/QwenLM/qwen-code/pull/2977) ✓ dingtalk 续传后缀 '(cont.)' 仅在续段
- [PR#2978](https://github.com/QwenLM/qwen-code/pull/2978) ✓ dingtalk @mention 后保留空文本
- [PR#2979](https://github.com/QwenLM/qwen-code/pull/2979) ✓ dingtalk reactionContext 内存泄漏
- [PR#2981](https://github.com/QwenLM/qwen-code/pull/2981) ✓ SDK Stream.return() promise hang

**计数**：已合并 ✓ 52 → **56**（仅追踪 4 个匹配 item 的合并；维护性的 11 个不计入矩阵跟踪计数）。

**观察**：今天上午（UTC 时间）**单一时间窗口内有 15+ PR 合并**，表明 qwen-code 在做发布前的批量清理（推测下一个 release 即将发布）。`channels/dingtalk` 4 连续修复（PR#2977/2978/2979 + PR#2980 待合并）说明国内 IM 渠道质量在快速打磨。

### 2026-04-17（晚间第三次补更）

继续扫描 qwen-code PR（updated > 今早）：

**新合并 PR（4 个）**：

- [PR#3076](https://github.com/QwenLM/qwen-code/pull/3076) ✓ 2026-04-17 10:23 UTC — **`background subagents with headless and SDK support`**。这是 Agent tool 的显式 `run_in_background: true` 参数**真实落地**！之前作为 item-22 自动后台化伪需求删除时，我已明确此 PR 是"真正的正规路径"——今天合并印证了判断。
- [PR#3339](https://github.com/QwenLM/qwen-code/pull/3339) ✓ 2026-04-17 14:05 UTC — `.qwen/rules/` 路径规则（已在上一轮更新中标注）
- [PR#3352](https://github.com/QwenLM/qwen-code/pull/3352) ✓ 2026-04-17 18:19 UTC — `dual-output sidecar mode for TUI`（新颖 UX）
- [PR#3358](https://github.com/QwenLM/qwen-code/pull/3358) ✓ 2026-04-17 22:43 UTC — `bind M-d to Emacs-like default`（输入 UX 微优化）
- [PR#3402](https://github.com/QwenLM/qwen-code/pull/3402) ✓ 2026-04-17 14:57 UTC — `match new cron notification format in interactive tests`（测试修复）

**新开 PR（未追踪，观察）**：

- [PR#3407](https://github.com/QwenLM/qwen-code/pull/3407) ✓（2026-04-18 合并）— `auto-submit on number key press in AskUserQuestionDialog`（UX 微优化）
- [PR#3404](https://github.com/QwenLM/qwen-code/pull/3404) ✓（**2026-04-19 合并**）— **`/doctor` 诊断命令**（对标 Claude Code 的 `/doctor`），Qwen Code 加了一个常用的诊断命令
- [PR#3398](https://github.com/QwenLM/qwen-code/pull/3398) — vscode OAuth → Coding Plan/API Key（重要 provider 策略调整）
- [PR#3394](https://github.com/QwenLM/qwen-code/pull/3394) — `feat(arena): add comparison summary for agent results`
- [PR#3393](https://github.com/QwenLM/qwen-code/pull/3393) ✓（2026-04-18 合并）— `feat(mcp): add OSC 52 copy hotkey for OAuth authorization URL`
- [PR#3381](https://github.com/QwenLM/qwen-code/pull/3381) ✓（2026-04-18 合并）— `reduce terminal redraw cursor movement`（性能微优化）

**计数更新**：已合并 ✓ 48 → **52**（+PR#3076、+PR#3352、+PR#3358、+PR#3402）。

### 2026-04-17（qwen-code PR 状态全量刷新）

全量扫描 qwen-code PRs `updated:>=2026-04-16`，发现多项合并：

**⚠️ 勘误**：用户指出 [PR#2827 HTTP Hook + Function Hook + Async Hook](https://github.com/QwenLM/qwen-code/pull/2827) 也已于 **2026-04-16 合并**，但本轮更新最初漏标为 ✓。已补标：
- 主矩阵 item-3 HTTP Hooks 行标 ✓
- `p0-p1-platform.md` item-3 改写为 **✅ 已实现（反超 Claude Code）** —— Qwen Code 实现 4 种 Hook 类型（command / http / function / async） + SSRF 防护，**超过 Claude Code 的 2 种（command / http）**

**🔥 重大合并：PR#3087 Auto-Memory + Auto-Dream 已合并**

- [PR#3087](https://github.com/QwenLM/qwen-code/pull/3087) ✓ **2026-04-16 合并**（LaZzyMan）— 实现完整的 `managed auto-memory + auto-dream` 系统
- 这是 **item-4 会话记忆** + **item-5 Auto Dream** 两个 P1 item 的同时实现！
- 同时是 [item-14 Nudge 驱动的闭环学习](./qwen-code-improvement-report-p0-p1-core.md#item-14) 的部分覆盖（仍缺 ① 双计数器 ② 冻结快照 ③ 保守 review prompt 三个关键要素）
- 全部标记为 ✓

**新合并 PR**（共 10+ 个）：

- [PR#3079](https://github.com/QwenLM/qwen-code/pull/3079) ✓ `/batch skill for parallel batch operations`（对应 item `/batch` 并行操作）
- [PR#3100](https://github.com/QwenLM/qwen-code/pull/3100) ✓ `optimize compact mode UX`
- [PR#3248](https://github.com/QwenLM/qwen-code/pull/3248) ✓ `add complete hooks support for ACP integration`
- [PR#3255](https://github.com/QwenLM/qwen-code/pull/3255) ✓ `move fork subagent params from execute() to construction time`（item-2 Fork Subagent 重构）
- [PR#3311](https://github.com/QwenLM/qwen-code/pull/3311) ✓ `support multi-line status line output`
- [PR#3379](https://github.com/QwenLM/qwen-code/pull/3379) ✓ `headless support and SDK task events for background agents`
- [PR#3315](https://github.com/QwenLM/qwen-code/pull/3315) ✓ `strip thinking blocks from history on model switch`
- [PR#3320](https://github.com/QwenLM/qwen-code/pull/3320) ✓ `limit skill watcher depth to prevent FD exhaustion`
- [PR#3327](https://github.com/QwenLM/qwen-code/pull/3327) ✓ `add shell argument quoting guidance to prevent special char errors`
- [PR#3321](https://github.com/QwenLM/qwen-code/pull/3321) ✓ `defer update notifications until model response completes`
- [PR#3308](https://github.com/QwenLM/qwen-code/pull/3308) ✓ `remember "Start new chat session" until summary changes`
- [PR#3310](https://github.com/QwenLM/qwen-code/pull/3310) ✓ `prevent statusline spawn EBADF from crashing CLI`
- [PR#3295](https://github.com/QwenLM/qwen-code/pull/3295) ✓ `avoid leaking process exit listeners in ProcessTransport`
- [PR#3270](https://github.com/QwenLM/qwen-code/pull/3270) ✓ `ignore literal Tab input`
- [PR#3322](https://github.com/QwenLM/qwen-code/pull/3322) ✓ `stabilize glob truncation tests`
- [PR#3325](https://github.com/QwenLM/qwen-code/pull/3325) ✓ docs update for OAuth discontinuation
- [PR#3252](https://github.com/QwenLM/qwen-code/pull/3252) ✓ Windows install docs fix

**新开 PR 并对接现有 item**：

- [PR#3383](https://github.com/QwenLM/qwen-code/pull/3383)（open）— `support refreshInterval in statusLine for periodic refresh` —— **直接实现我昨天新增的 [item-25 Refresh Interval Statusline](./qwen-code-improvement-report-p2-tools-commands.md#item-25)**！已挂到该 item 的进展列
- [PR#3339](https://github.com/QwenLM/qwen-code/pull/3339) ✓（**2026-04-17 合并**，tanzhenxin）— `add path-based context rule injection from .qwen/rules/` —— **实现 [p0-p1-core item-9 指令条件规则](./qwen-code-improvement-report-p0-p1-core.md#item-9)**！长期等待的功能落地
- [PR#3318](https://github.com/QwenLM/qwen-code/pull/3318)（open）preconnect + [PR#3319](https://github.com/QwenLM/qwen-code/pull/3319) ✓（2026-04-18 16:40 UTC 合并）early input — 启动优化拆分为两个独立 PR，原 [PR#3085](https://github.com/QwenLM/qwen-code/pull/3085) 已关闭被替代

**新 hook 类型 PR（暂不单独追踪，归入 hook 系统扩展）**：

- [PR#3388](https://github.com/QwenLM/qwen-code/pull/3388)（open）— `add prompt hook type with LLM evaluation support`（延续 [PR#2990](https://github.com/QwenLM/qwen-code/pull/2990) 关闭后的方向）
- [PR#3378](https://github.com/QwenLM/qwen-code/pull/3378)（open）— `Add TodoCreated and TodoCompleted hooks`

**其他观察到的新开 PR**：

- [PR#3352](https://github.com/QwenLM/qwen-code/pull/3352) ✓（2026-04-17 合并）— `dual-output sidecar mode for TUI`（新颖 UX 方向）
- [PR#3329](https://github.com/QwenLM/qwen-code/pull/3329) — real-time token consumption display（UI polish）
- [PR#3377](https://github.com/QwenLM/qwen-code/pull/3377) — slash command multi-mode expansion Phase 2（延续 PR#3283）
- [PR#3377](https://github.com/QwenLM/qwen-code/pull/3377) — slash command Phase 2

**关闭的 PR**（不作为伪需求，只是路线调整）：

- PR#3085（startup optimization）被 PR#3318 + PR#3319 替代
- PR#2990（prompt hook LLM condition）被 PR#3388 替代
- PR#3261（/history command）— closed
- PR#3258、PR#2760、PR#3082 — 各类关闭

**计数变化**：追踪 PR 49 → **52**（+PR#3318、+PR#3319、+PR#3339、+PR#3383；-PR#3085 关闭），已合并 ✓ 28 → **48**（本轮 +18 merged，主要是 Claude Code/AgentScope 等项目的长期打磨成果；**晚间补 PR#3339 ✓ 于 2026-04-17 14:05 UTC 合并**）。

### 2026-04-17（Copilot CLI 0.0.381 → 0.0.402 更新扫描）

扫描 GitHub Copilot CLI v0.0.381 到 v0.0.402 的 `changelog.json`（22 个版本，来自 `@github/copilot@0.0.403` 本地 npm 包 + `github/copilot-cli` GitHub 仓库 releases），识别 Qwen Code 可借鉴的新能力。本次排除了已被 Qwen Code 覆盖的特性（如 `/review`、`/resume`、`/yolo`、plan mode、shell parallel、MCP OAuth）。

**新增追踪（4 项）**：

| # | 功能 | Copilot CLI 版本 | 审查 |
|---|---|---|---|
| [p2-tools-commands item-26](./qwen-code-improvement-report-p2-tools-commands.md#item-26) | **`/experimental` 实验特性统一门控** | v0.0.396 | ✅ Copilot 提供了统一注册表，优于 Qwen 目前 env var/settings 分散配置 |
| [p2-perf item-35](./qwen-code-improvement-report-p2-perf.md#item-35) | **自定义指令文件 SHA-256 去重** | v0.0.394 | ✅ 零风险 context 节约 |
| [p2-tools-ui item-21](./qwen-code-improvement-report-p2-tools-ui.md#item-21) | **大粘贴内容自动存到工作区文件**（>30KB） | v0.0.397 | ✅ 具体 UX 痛点修复 |
| [p3-features item-17](./qwen-code-improvement-report-p3-features.md#item-17) | **`--config-dir` CLI flag** | v0.0.382 | ✅ CI/多租户场景原生支持，补 PR#2953 `QWEN_HOME` env var |

**观察到但不追踪**（Qwen Code 已覆盖或不适用）：

| Copilot 新特性 | 不追踪原因 |
|---|---|
| Autopilot mode（v0.0.400, experimental） | Anthropic/Claude Code 已有 Auto mode，qwen-code `/loop` 类似方向 |
| `/review`（v0.0.388） | Qwen Code 已有（PR#2932 等，见 platform item-2）|
| `/resume`（v0.0.386）、`/yolo`（v0.0.381）、`/init`（v0.0.396）、`/rename`（v0.0.392）| Qwen Code 已有 |
| OAuth MCP（v0.0.389）、MCP 插件分发（v0.0.389）| Qwen Code MCP 基础已有 |
| `/delegate` / `&` 前缀后台（v0.0.384/v0.0.394）| Qwen Code 已有 [PR#3076](https://github.com/QwenLM/qwen-code/pull/3076) ✓（2026-04-17 合并）background subagents |
| `/diff` + Esc-Esc 回退（v0.0.395/v0.0.399）| 重叠 p2-core item-10 文件历史快照 + PR#3292 session rewind |
| LSP 工具（v0.0.399, experimental）| Qwen Code LSP 已 7,422 行（见 opencode 对比 item-16） |
| **移除捆绑 LSP**（v0.0.400）| Qwen 方向相反：PR#3170 正在加强 LSP，Copilot 的这个决策不适合借鉴 |
| Extended thinking for Claude（v0.0.384）| Provider 特定功能 |
| MSI installer（v0.0.389）| 安装器工具链，非核心能力 |

**排除（伪需求审查）**：

- Copilot CLI changelog 中未发现明显 gated 特性（相比 Claude Code 的 `tengu_*` 或 `USER_TYPE === 'ant'` 模式）
- 大部分新特性是**直接可用**的 stable 功能，Copilot CLI 的门控方式更宽松（`/experimental` 主动 opt-in）

**有趣的反向观察**（Copilot 做了 Qwen/Claude 没做的**减法**）：

- v0.0.400 **移除捆绑 LSP servers**（TypeScript、Python）—— 从"大而全"改为"按需外部调用"。值得注意的是 Qwen Code/Claude Code 都在加强 LSP（Qwen Code LSP 7,422 行 vs Copilot 移除）。这是架构哲学差异，不必盲目跟随。

**总项数**：256 → **260**（+4），p2-tools-commands 25→26，p2-perf 34→35，p2-tools-ui 20→21，p3-features 16→17。

### 2026-04-17（Claude Code 2.1.82 → 2.1.112 更新扫描）

扫描 Claude Code v2.1.82 到 v2.1.112 的 CHANGELOG（30 个版本，涵盖 2 月时间窗口），识别 Qwen Code 可借鉴的新能力。系统性地检查每个新特性的**源码门控**（避免 item-22/item-20 那样的伪需求），**已验证 5 项值得追踪 + 1 项排除**：

**新增追踪（5 项，各 item 含 ⚠️ 伪需求审查结果）**：

| # | 功能 | 优先级 | Claude Code 来源 | 审查 |
|---|---|---|---|---|
| [p2-tools-commands item-23](./qwen-code-improvement-report-p2-tools-commands.md#item-23) | **PreCompact Hook**（压缩前钩子） | P2 | v2.1.105 `commands/compact/compact.ts` `executePreCompactHooks()` | ✅ 真实能力，与现有 PostCompact 对称 |
| [p2-tools-commands item-24](./qwen-code-improvement-report-p2-tools-commands.md#item-24) | **模型通过 Skill 工具调用内置 Slash 命令** | P2 | v2.1.108 "The model can now discover and invoke built-in slash commands like `/init`, `/review`, and `/security-review` via the Skill tool" | ✅ 真实能力 |
| [p2-tools-commands item-25](./qwen-code-improvement-report-p2-tools-commands.md#item-25) | **Statusline Refresh Interval** | P3 | v2.1.97 `refreshInterval` setting | ✅ 真实能力，扩展 PR#2923 |
| [p2-stability item-42](./qwen-code-improvement-report-p2-stability.md#item-42) | **子进程 PID 命名空间沙箱 + 脚本次数限制** | P2 | v2.1.98 `CLAUDE_CODE_SUBPROCESS_ENV_SCRUB` + `CLAUDE_CODE_SCRIPT_CAPS` | ✅ 真实能力（env var 控制不是 gate） |
| [p2-stability item-43](./qwen-code-improvement-report-p2-stability.md#item-43) | **会话 Recap（返回时上下文摘要）** | P2 | v2.1.108 `/recap` + v2.1.110 auto-show; `services/awaySummary.ts` | ✅ 真实能力 |

**排除（1 项，伪需求审查发现）**：

- **`/ultrareview`**（v2.1.111）— "cloud parallel multi-agent review"。**源码 `commands/review/ultrareviewEnabled.ts:13` 验证是 `tengu_review_bughunter_config.enabled === true` 门控**（GrowthBook feature flag，默认 false）。当前是**实验性功能对外不可用**——同 item-22/item-20 一类伪需求，**不作为 Qwen Code 改进目标**。

**观察到但暂不追踪（合理理由）**：

| 新功能 | 为何不追踪 |
|---|---|
| `/effort` slider + `xhigh` 等级（v2.1.111） | Anthropic Opus 4.7 specific，不适用于多 provider 的 Qwen Code |
| PowerShell tool（v2.1.111） | 平台特定（Windows），Bash 工具已覆盖多数场景 |
| Auto mode（v2.1.111） | Anthropic Max 订阅专属，模型特定 |
| `/tui fullscreen`（v2.1.110） | 已有 PR#3013 SlicingMaxSizedBox 追踪防闪烁 |
| `/focus` command（v2.1.110） | 可合并到现有 UI 相关 item 作为增强 |
| `/team-onboarding`（v2.1.101） | 较专一的用例（团队协作），低优先级 |
| OS CA cert 默认信任（v2.1.101） | 已被 p2-core item-19 企业代理覆盖 |
| `/powerup` 交互式教程（v2.1.90） | UX 糖衣，不是核心能力 |
| PID namespace (v2.1.98) | ✅ 已追踪（item-42） |
| WebFetch strip `<style>/<script>`（v2.1.105） | 微优化，可合并到 Web 工具文档 |
| Skill description cap 1536（v2.1.105） | 已有 Skill 相关 items 可合并 |
| Plugin `bin/` executables（v2.1.91） | 已有 plugin 相关 item（OpenCode 对比中） |
| Session memory auto-discovery + auto-dream | 已追踪（item-4 / item-5 / PR#3087） |

**总项数**：251 → **256**（+5），p2-tools-commands 22→25，p2-stability 41→43。

**审查规则强化**：Claude Code 2.1.82→2.1.112 的 CHANGELOG 是未来**每次版本升级都该做的例行审查源**——新能力可能是**真实功能**或**gated 伪需求**，必须逐项检查源码门控（`tengu_*` GrowthBook flag / `USER_TYPE === 'ant'` / `CLAUDE_CODE_EXPERIMENTAL_*` 等）才能判断。

### 2026-04-16（伪需求删除：ConfigTool）

用户质疑 [p2-core item-20 ConfigTool](./qwen-code-improvement-report-p2-core.md) 必要性，经源码验证发现这是一个 **Anthropic 内部专属工具**，对外部 Claude Code 用户**完全不可见**。

**源码证据** `/root/git/claude-code-leaked/tools.ts:214-215`：

```typescript
...(process.env.USER_TYPE === 'ant' ? [ConfigTool] : []),
...(process.env.USER_TYPE === 'ant' ? [TungstenTool] : []),
```

`USER_TYPE === 'ant'` 表示 **Anthropic 内部员工**——只有在此条件下 ConfigTool / TungstenTool / REPLTool 才会被注册到工具列表。**所有公开 Claude Code 用户从未访问过 ConfigTool**。

**结论**：这是比 item-22 auto-background 更严重的伪需求：
- item-22 是 GrowthBook flag 默认关闭但可开启
- item-20 是**硬编码的 `USER_TYPE === 'ant'` gate**——**没有外部启用路径**

**作者行为佐证**：[PR#2911](https://github.com/QwenLM/qwen-code/pull/2911) 由 wenshao 提交后**自己关闭**，很可能在实现中发现该能力对外部用户无意义。Agent 需要读写配置可以直接用 Read/Write 工具读 `settings.json`，无需独立的 ConfigTool 抽象。

**变更**：

1. p2-core item-20 ConfigTool **删除**
2. p2-core items 21-27 重编号为 20-26（终端主题检测、队列输入编辑、状态栏紧凑布局、会话标签与搜索、Plan 状态机化、A2A、OTel）
3. 主矩阵删除 ConfigTool 行，更新所有 `#item-N` 链接
4. 子报告表 p2-core 27 → **26**，总项数 252 → **251**
5. Changelog 记录 + 指向 `tools.ts:214-215` 源码证据

**强化的审查规则**（加入审计清单）：

> **5. 是否有 `USER_TYPE === 'ant'` 条件注册？** 这比 GrowthBook flag 更封闭——是"Anthropic 内部专属"的硬编码 gate。任何此类工具都**不应进入外部对标矩阵**（TungstenTool / REPLTool 同理）。

**查同类工具**：`tools.ts` 中其他 `USER_TYPE === 'ant'` 条件注册的工具有 **TungstenTool**（Anthropic 内部实验工具，性质不明）和 **REPLTool**（Python REPL，内部专属）。这两个都不在改进报告中，确认保持不追踪。

### 2026-04-16（PR 状态全面刷新）

全量扫描 qwen-code PRs `updated:>=2026-04-14`，发现多项状态变化：

**1. 重大更新：Fork Subagent 已合并**

- [PR#2936](https://github.com/QwenLM/qwen-code/pull/2936) ✓ **合并于 2026-04-14**（tanzhenxin 提交）— `feat(core): implement fork subagent for context sharing`
- 这是 **P0 item-2 Fork Subagent** 的主实现 PR，标记所有引用为 ✓
- **P0 级别的核心能力落地**：子代理继承完整对话上下文 + 共享 prompt cache 省 80%+ 费用

**2. 勘误：PR#2380 之前错标为 merged**

- 2026-04-14 的 "2026-04-14（晚间更新）" changelog 条目写"[#2380] 全部已合并"**不准确**
- `gh pr view 2380` 实际状态：**CLOSED（未合并）**
- 已修正 `p0-p1-platform.md` item-2 的 PR 表格标注 + 主 changelog 对应段落
- /review skill 的 **4 个合并 PR** 是 #2348 / #2376 / #2687 / #2932，不包括 #2380

**3. 状态纠正：3 个曾标注 open 的 PR 现已 CLOSED**

- [PR#3022](https://github.com/QwenLM/qwen-code/pull/3022) `/branch 会话分支` → **CLOSED**（未合并）。由 [PR#3292](https://github.com/QwenLM/qwen-code/pull/3292) `feat(cli): add session rewind and restore flows`（open）跟进（合并 /branch + /rewind 两个方向）
- [PR#2911](https://github.com/QwenLM/qwen-code/pull/2911) `ConfigTool` → **CLOSED**（未合并，wenshao 自己提交后关闭）
- [PR#2866](https://github.com/QwenLM/qwen-code/pull/2866) upstream backports → CLOSED（从未纳入追踪，观察记录）

**4. 新合并 PR（其他维护项）**

- [PR#2984](https://github.com/QwenLM/qwen-code/pull/2984) ✓ — `feat(vscode-ide-companion): add /account for account display`
- [PR#3191](https://github.com/QwenLM/qwen-code/pull/3191) ✓ — `feat(acp): LLM-based message rewrite middleware with custom prompts`（此前已在 04-15 changelog 记录）
- [PR#3212](https://github.com/QwenLM/qwen-code/pull/3212) ✓ — `fix(core): respect custom Gemini baseUrl from modelProviders`
- [PR#3251](https://github.com/QwenLM/qwen-code/pull/3251) ✓ — `fix(core): allow thought-only responses in GeminiChat stream validation`
- [PR#3257](https://github.com/QwenLM/qwen-code/pull/3257) ✓ — `fix(cli): make /bug easier to open in terminals without hyperlink support`
- [PR#3270](https://github.com/QwenLM/qwen-code/pull/3270) ✓ — `fix(cli): ignore literal Tab input in BaseTextInput`
- [PR#3294](https://github.com/QwenLM/qwen-code/pull/3294) ✓ — `fix(channels/dingtalk): prioritize senderStaffId over senderId for allowedUsers matching`
- [PR#3298](https://github.com/QwenLM/qwen-code/pull/3298) ✓ — `chore(release): bump version to 0.14.5`
- [PR#3299](https://github.com/QwenLM/qwen-code/pull/3299) ✓ — `fix(cli): block discontinued qwen-oauth model selection in ModelDialog`

**5. 政策变更（值得留意）**

- [PR#3291](https://github.com/QwenLM/qwen-code/pull/3291) ✓ — **`feat(auth): discontinue Qwen OAuth free tier (2026-04-15 cutoff)`**——Qwen OAuth 免费层已于 2026-04-15 终止。Qwen Code 文档的"免费层"描述（README / SUMMARY / pricing.md 等）可能需要相应更新，但这是文档维护任务，不影响改进矩阵
- [PR#3217](https://github.com/QwenLM/qwen-code/pull/3217) ✓（2026-04-13）— docs 更新 quota 耗尽后替代方案（OpenRouter/Fireworks），配套政策变更

**6. 新开 PR（观察中，暂不追踪）**

- [PR#3292](https://github.com/QwenLM/qwen-code/pull/3292) — session rewind and restore flows（顶替已关闭的 #3022 /branch + #3013 /rewind 方向）
- [PR#3303](https://github.com/QwenLM/qwen-code/pull/3303) — 检测 macOS 上不在 PATH 的 Zed.app
- [PR#3297](https://github.com/QwenLM/qwen-code/pull/3297) ✓（2026-04-18 合并）— tool registry lazy factory with concurrency dedup
- [PR#3295](https://github.com/QwenLM/qwen-code/pull/3295) — SDK ProcessTransport exit listener leak 修复

**计数变化**：
- 追踪 PR：49 → **49**（新增 PR#3292 顶替已关闭的 PR#3022，计数抵消）
- 已合并 ✓：27 → **28**（+PR#2936 Fork Subagent 核心合并）
- 已关闭 ✗：2 → **5**（+PR#3022、+PR#2911、+PR#2380 勘误）

### 2026-04-15（伪需求审计 + 实验性功能警告）

用户指出 [p2-core item-22 自动后台化 Agent](./qwen-code-improvement-report-p2-core.md) 可能是伪需求。经源码验证 `/root/git/claude-code-leaked/tools/AgentTool/AgentTool.tsx:72-78`：

```typescript
function getAutoBackgroundMs(): number {
  if (isEnvTruthy(process.env.CLAUDE_AUTO_BACKGROUND_TASKS) ||
      getFeatureValue_CACHED_MAY_BE_STALE('tengu_auto_background_agents', false)) {
    return 120_000;
  }
  return 0;  // disabled by default
}
```

**确认为伪需求**：Claude Code 此功能**默认禁用**，仅在 `CLAUDE_AUTO_BACKGROUND_TASKS` 环境变量 **或** GrowthBook feature flag `tengu_auto_background_agents` 被启用时才生效（两者默认均关闭）。绝大多数 Claude Code 用户**从未体验过**此功能。把 feature-gated 实验能力描述为"核心能力"会误导 Qwen Code 开发者投入低 ROI 工作。

**正确的方向是显式 `run_in_background: true`**——已在 Agent tool schema 中作为 first-class 参数，也是 Qwen Code [PR#3076](https://github.com/QwenLM/qwen-code/pull/3076) ✓（**2026-04-17 合并**）的**真实需求**，已落地。

**用户追加要求：** "同时仔细检查其他的建议，避免误导开发者投入" —— 系统性审计 `/root/git/claude-code-leaked` 中所有 GrowthBook gates (`tengu_*`) 和 env var gates (`CLAUDE_CODE_EXPERIMENTAL_*`)，交叉对比改进报告。

**审计决策**（每个发现都人工验证源码后）：

| item | 审计结论 | 动作 |
|---|---|---|
| p2-core **item-22 自动后台化 Agent** | 伪需求（`tengu_auto_background_agents` default false） | **删除**（后续 items 23-28 重编号为 22-27） |
| p2-core **item-6 Computer Use** | 真实功能但 **默认禁用**（`tengu_malort_pedway` gate + Max/Pro 订阅双重门控） | **保留 + ⚠️ 实验性警告**，建议降级 P3 |
| p2-core **item-11 Deep Link** | 真实功能但 **默认禁用**（`tengu_lodestone_enabled` gate，`utils/deepLink/registerProtocol.ts:302`） | **保留 + ⚠️ 实验性警告**，建议降级 P3 |
| p0-p1-core **item-4 Session Memory** | Explore 建议删除 — **拒绝**。源码验证 `services/SessionMemory/sessionMemory.ts` 真实存在，被 `skills/bundled/skillify.ts:180` 和 `commands/compact/compact.ts:58-79` 引用 | 保留 |
| p0-p1-core **item-5 Auto Dream** | Explore 建议删除 — **拒绝**。`services/autoDream/autoDream.ts` 真实存在，`executeAutoDream` 被 `query/stopHooks.ts:52` 调用，`ConfigTool.autoDreamEnabled` 配置项存在，`components/memory/MemoryFileSelector.tsx:163` 和 `FeedbackSurvey/usePostCompactSurvey.tsx:179-194` 使用 | 保留（也是 PR#3087 的正确 backport 目标） |
| p0-p1-engine **item-14 Coordinator/Swarm** + **item-25 Task Management** | 已有"Agent Team 实验性功能"注释，补充源码引用：`utils/agentSwarmsEnabled.ts:21-32` 显示 `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` env var 开启 | 扩展注释，非删除 |

**关键修正**：Explore agent 的初次建议包含了两个高影响错误（建议删除 item-4/5），经我直接 `grep` 验证后**驳回**。这说明对 audit 结果必须逐项核对源码，不能盲信 agent 输出。

**最终变更**：

1. p2-core item-22 **删除**，items 23→22, 24→23, 25→24, 26→25, 27→26, 28→27 重编号
2. p2-core item-6 Computer Use + item-11 Deep Link 添加 **⚠️ 实验性功能警告** 段落（引用具体 gate 名和源文件行号）
3. 主矩阵对应行状态列追加 ⚠️ 标记
4. p0-p1-engine Coordinator/Swarm 实验性注释补充 `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` 源码引用
5. 主矩阵 p2-core 链接全部更新（`#item-23`→`#item-22` 等）
6. 子报告表 p2-core 28 → 27，总项数 253 → **252**

**验证**：子报告合 `14+9+27+27+22+20+34+41+16+9+33 = 252` ✓，主矩阵 `grep -c '^| \*\*P[0-3]\*\*' = 252` ✓

**对开发者的建议**：未来追踪 Claude Code 新功能进入改进矩阵前，**必须验证源码** —— 不能只看文档/截图/PR 描述。检查点：
1. 该功能是否有 `getFeatureValue_CACHED_MAY_BE_STALE('tengu_*', false)` 调用？
2. 该功能是否需要 `CLAUDE_CODE_EXPERIMENTAL_*` 或 `CLAUDE_*` 环境变量？
3. `is*Enabled()` / `get*Ms()` 等 guard 函数的默认返回值是什么？
4. 该功能是否要求特定订阅等级（Max/Pro）？

有任一"是"则**不应作为 Qwen Code 的 P2/P1 核心改进目标**——要么降级到 P3，要么标注 ⚠️ 实验性警告，要么完全拒绝。

### 2026-04-15（补充追踪：Fast Mode 部分实现）

用户指出 [p2-core item-5 Fast Mode](./qwen-code-improvement-report-p2-core.md#item-5) 标注"仅指定备用模型"不准确——Qwen Code 已实现 `fastModel` 配置体系。审查 qwen-code 源码 + git log 后确认：

**Qwen Code 的 `fastModel` 实现时间线**：
- `49702ce26` refactor: 合并 `suggestionModel + speculationModel` → 统一 `fastModel`
- `e9bc686f0` refactor: `fastModel` 移到顶层配置（与 `model` 并列）
- `fea1739d2` feat: **`/model --fast` 命令**
- `c06276799` feat: `/model --fast` 打开选择对话框
- [PR#3077](https://github.com/QwenLM/qwen-code/pull/3077) ✓ improve /model --fast description clarity
- [PR#3086](https://github.com/QwenLM/qwen-code/pull/3086) ✓ add --fast hint to /model description
- [PR#3120](https://github.com/QwenLM/qwen-code/pull/3120) ✓ replace text input with model picker for Fast Model in /settings

**但不完全对齐 Claude Code Fast Mode**：
- Claude Code Fast Mode = **同一模型的速度分级**（Opus 4.6 standard vs Opus 4.6 fast，依赖 Anthropic priority tier 定价）
- Qwen Code fastModel = **另一个更快/更便宜的模型**（如 qwen-turbo 作为 qwen-plus 的 fastModel）
- 两者解决**相似问题**（fast-response 场景），但实现路径不同。Qwen Code 走"换模型"方案的根本原因是 DashScope / OpenAI 不提供 priority tier 定价，**只有 Anthropic 有**。

**修复**：
- item-5 标题加 ⚠️ 部分实现标记
- 详细页加完整实现时间线（4 commits + 3 merged PRs）+ 两种方案对比表 + "为什么走不同方案"说明
- 主矩阵 item-5 行：状态 "仅指定备用模型" → "⚠️ 部分实现（`fastModel` 走不同方案）"，进展列补 3 个 merged PRs
- 架构差异总结表同步更新

**追踪计数不变**：PR#3077 / #3086 / #3120 早已在报告其他位置引用（changelog + 历史表），本次只是把它们**归属到 item-5 的进展列**，不是新增追踪。总追踪 PR 仍为 **49**，merged 仍为 **27**。

### 2026-04-15（补充追踪：Remote Control Bridge 3 个 PR）

用户指出 [item-7 Remote Control Bridge](./qwen-code-improvement-report-p0-p1-platform.md#item-7) "进展"列为空，搜索后发现 **3 个未追踪 PR**，分两条路径推进同一个 item：

**路径 A：本地 HTTP/WebSocket + Web UI + QR code**（对标 Claude Code Bridge）
- **[PR#2330](https://github.com/QwenLM/qwen-code/pull/2330)**（open）— `feat: remote-control feature for browser-based CLI interaction`：`http://localhost:7373/` + 64-char hex token + qrcode-terminal 扫码连手机 + rate limit + idle timeout + XSS sanitization
- [PR#1678](https://github.com/QwenLM/qwen-code/pull/1678)（open，较早）— Web GUI，和 #2330 有重叠

**路径 B：Channels 平台**（通过消息平台远程驱动）
- **[PR#2628](https://github.com/QwenLM/qwen-code/pull/2628) ✓**（**2026-04-01 合并**）— `feat(channels): extensible Channels platform`：`@qwen-code/channel-base` 插件系统 + 内置 Telegram/WeChat/DingTalk 3 个 adapter + allowlist/pairing/group policies + session 管理。这是**另一种 remote control**——通过 IM 驱动本地 Agent

**修正**：
- 主矩阵 item-7 行"进展"列从 "—" 补上 3 个 PR
- "Qwen Code 现状"列从"缺失"改为"Channels 平台已合并（IM 路径），Web/QR 路径 review 中"
- p0-p1-platform item-7 详细页新增长段落，对比两种路径的适用场景、实时性、已合并状态

总追踪 PR：**47 → 49**（+PR#2330、+PR#2628；PR#1678 只提及不单独计数），merged 26 → **27**（+PR#2628 ✓）。

### 2026-04-15（补充追踪）

系统扫描 `pull/` URL 跨报告交叉引用，发现 5 个此前未追踪的 PR。两个**应立即追踪**（已执行），3 个**changelog 级记录**（无对应 matrix item）：

**已加入追踪**（主矩阵 + 详细页都更新）：

- [PR#3170](https://github.com/QwenLM/qwen-code/pull/3170)（open，huww98）— **LSP 官方 SDK + didSave 实时诊断**。挂到 [p2-perf item-7 LSP 服务器并行启动](./qwen-code-improvement-report-p2-perf.md#item-7)，与 PR#3034（diagnostics caching）互补。核心是"实时诊断"而非"启动并行"——解决 Edit 后必须手动 refresh 才能看到新 diagnostics 的问题
- [PR#3276](https://github.com/QwenLM/qwen-code/pull/3276)（open）— **`/review` Step 4 并行 dispatch 强化（弱模型）**。挂到 [p0-p1-platform item-2 GitHub Code Review](./qwen-code-improvement-report-p0-p1-platform.md#item-2) 的"进行中的增强"。修复 qwen3.6-plus 等弱模型会串行执行 5 agent 的问题（替换单行指令为 callout + ASCII 正反例 + self-check + "STOP" 模式打断）

**仅 changelog 记录**（无对应 matrix item，为社区开发方向观察）：

- [PR#3191](https://github.com/QwenLM/qwen-code/pull/3191) ✓（2026-04-15 合并）— **ACP LLM 消息重写中间件**：`TurnBuffer` 累积 turn content（thoughts + messages），`LlmRewriter` 用 user-defined system prompt 重写为用户友好格式。ACP 模式专用，不影响其他 session path
- [PR#3283](https://github.com/QwenLM/qwen-code/pull/3283)（open）— **命令能力化 metadata（Phase 1）**：替换硬编码的 `ALLOWED_BUILTIN_COMMANDS_NON_INTERACTIVE` 白名单为 per-command `commandType` + `supportedModes` 元数据。是 broader slash command 架构重构的 Phase 1，零行为回归
- [PR#3165](https://github.com/QwenLM/qwen-code/pull/3165)（open）— **MiniMax provider 支持**。扩展 qwen-code 的 provider 生态到 MiniMax

总追踪 PR：**45 → 47**（新增 PR#3170 + PR#3276），merged 26 → 26（这次追加的 2 个 PR 都是 open）。

### 2026-04-14（追加：PR#3087 Auto Dream 追踪修复）

用户指出 [item-5 Auto Dream](./qwen-code-improvement-report-p0-p1-core.md#item-5) 主矩阵的"进展"列为空，但 [PR#3087](https://github.com/QwenLM/qwen-code/pull/3087) 标题明确是 `managed auto-memory + auto-dream system`，即同时覆盖 [item-4 会话记忆](./qwen-code-improvement-report-p0-p1-core.md#item-4)（`extract` 子系统）和 item-5 Auto Dream（`dream` 子系统）。

验证 PR 内容后确认：
- `extract` → item-4（提取记忆）—— **顺便修复了一个 bug**：`saveCacheSafeParams` 被 `skipNextSpeakerCheck` early-return 路径跳过，导致 extract 从未触发
- `dream` → item-5（后台整理/去重/合并）
- 含 `PermissionManager` wrapper 限制 memory scope 写入权限
- PR 描述明确声明对齐 Claude Code 的 `extract` + `dream` 实现模式

**修复**：主矩阵 item-5 行的"进展"列补上 PR#3087，并在 p0-p1-core item-5 详细页补充 "进展" 段落说明双子系统覆盖。

### 2026-04-14（追加：PR#2949 追踪缺口修复）

社区反馈发现 [PR#2949](https://github.com/QwenLM/qwen-code/pull/2949)（**Skill 级模型覆盖**，tanzhenxin 提交，2026-04-13 合并）未被追踪。检查后确认这是一个**真实的追踪缺口**：

- [skill-system-deep-dive.md 矩阵](./skill-system-deep-dive.md) 的"模型覆盖"列此前标注 Qwen Code 为 ✗（Claude Code / Copilot CLI 为 ✓）
- 改进报告从未为"Skill 模型覆盖"单独立过 item

**补救**：
- 新增 [item-22 Skill 级模型覆盖](./qwen-code-improvement-report-p2-tools-commands.md#item-22)（p2-tools-commands 子报告），直接标注 ✓ 已合并
- 更新 [skill-system-deep-dive.md](./skill-system-deep-dive.md) Qwen Code 行的"模型覆盖"列从 ✗ 改为 ✓（同 provider）
- PR#2949 实现要点：skill frontmatter `model:` 字段 → `SkillConfig.model` → skill tool call 之后的 API 请求使用该 model → agentic loop 结束自然恢复。**Phase 1 仅同 provider 切换**，跨 provider 需要 ContentGenerator threading，延到 follow-up PR。

总项数 **252 → 253**，p2-tools-commands 子报告 21 → 22。
总追踪 PR：**45 个（26 已合并 ✓）**。

### 2026-04-14（AgentScope 参考新增 3 项）

基于对 [AgentScope](https://github.com/agentscope-ai/agentscope)（阿里 Tongyi Lab，215 文件 / 43K 行）的源码级分析，新增 3 条 P2 improvement item，均标注"AgentScope 参考"：

- **[item-24 Plan 状态机化](./qwen-code-improvement-report-p2-core.md#item-24)** — 4 状态 subtask（todo/in_progress/done/abandoned）+ 每轮自动 hint 注入，升级 `/plan` 从"一次性文档"到"持久状态机"
- **[item-25 A2A 协议集成](./qwen-code-improvement-report-p2-core.md#item-25)** — 集成 `a2a-sdk` + AgentCard + Well-known/File/HTTP resolver，让 qwen-code 参与跨 agent 网络
- **[item-26 OTel 原生 Tracing](./qwen-code-improvement-report-p2-core.md#item-26)** — 5 类 span extractor（Agent/LLM/Tool/Formatter/Embedding），对标 AgentScope `src/agentscope/tracing/_trace.py:24-45` 的 13 个 extractor 实现

总项数 **249 → 252**，p2-core 子报告 25 → 28。（后于 2026-04-15 伪需求审计删除 item-22，最终项数 252，见该日 changelog 条目）。

新增文档章节 [`docs/frameworks/`](../frameworks/)：
- [`agentscope/`](../frameworks/agentscope/) — AgentScope 源码级 deep-dive（6 文件）
- [`comparison.md`](../frameworks/comparison.md) — 6 款 framework 横向对比
- 5 个 framework 单文件（LangGraph / CrewAI / AG2 / MAF / LangChain）—— 基于文档级分析

### 2026-04-14（晚间更新）

**勘误**：social 反馈指出 platform item-2 "GitHub Code Review 多 Agent 审查" 已被 qwen-code 内置 `/review` skill 完整覆盖。审查源码 `packages/core/src/skills/bundled/review/SKILL.md` 后确认：

- **Step 4**：dispatch 5 个 task agent 并行执行（5 个维度：correctness / security / quality / performance / build-test）
- **Step 9**：用 GitHub Create Review API 一次性提交 verdict + inline comments 数组（模仿 Copilot Code Review）
- **Step 5/6/8**：去重、反向审计、autofix 流程完整
- **`.qwen/review-rules.md`** 项目规则（等同 REVIEW.md 概念）
- **增量 cache**、**worktree 隔离**、**跨仓库 lightweight 模式**等额外能力

实现深度**已超过 Claude Code 托管的 GitHub Code Review**。涉及 PR：[#2348](https://github.com/QwenLM/qwen-code/pull/2348) ✓ / [#2687](https://github.com/QwenLM/qwen-code/pull/2687) ✓ / [#2932](https://github.com/QwenLM/qwen-code/pull/2932) ✓ —— **3 个 PR 已合并**。[#2376](https://github.com/QwenLM/qwen-code/pull/2376)（multi-model arbitration，CLOSED 2026-04-13）和 [#2380](https://github.com/QwenLM/qwen-code/pull/2380)（`extends: bundled`）**均已关闭**（未合并，勘误：之前错标为 merged）。

更新 platform item-2 状态为"✓ 已实现"，新增 5 个 PR 的 ✓ 标记到主矩阵。

总追踪 PR 重新计数：**44 个（25 已合并 ✓，2 已关闭移除）**

### 2026-04-14

**继续追踪社区 PR**（qwen-code 4/14 连续合并 + 新开）：

- **新标记已合并**（2 个 ✓）：
  - [#3232](https://github.com/QwenLM/qwen-code/pull/3232) ✓（**启动性能剖析器**，7 检查点 + `QWEN_CODE_PROFILE_STARTUP=1` 环境变量）— 作为 item-8 启动优化的**测量基线**，与主 PR#3085 互补
  - [#3246](https://github.com/QwenLM/qwen-code/pull/3246) ✓（**从流式 SSE 帧中检测 rate-limit 错误**）— 解决 DashScope 子代理 `Throttling.AllocationQuota` 立即失败问题，是 engine item-8 API 退避逻辑的**前置条件**
- **新增追踪 PR**（3 个 open）：
  - [#3214](https://github.com/QwenLM/qwen-code/pull/3214)（tanzhenxin）— **替换 fdir 爬虫为 `git ls-files + ripgrep` 两级回退**，Closes [Issue#3137](https://github.com/QwenLM/qwen-code/issues/3137)。直接解决 `@` 文件补全在大项目里按键每次重新扫描的性能问题；关联 p2-core item-15 FileIndex
  - [#3242](https://github.com/QwenLM/qwen-code/pull/3242)（open）— 保证 startup input 穿透 full init 流程不丢失，补充 PR#3085
  - [#3266](https://github.com/QwenLM/qwen-code/pull/3266)（open）— 新增 `PostTurn` hook 事件（每次模型 turn 边界触发），延续 PR#2825 的"新 hook 事件类型"方向
- **其他新开 PR（观察中，暂不追踪）**：
  - [#3178](https://github.com/QwenLM/qwen-code/pull/3178) ✓（2026-04-18 合并）+ [#3236](https://github.com/QwenLM/qwen-code/pull/3236) 工具验证重试循环检测 + 停止指令
  - [#3255](https://github.com/QwenLM/qwen-code/pull/3255) Fork Subagent params 构造时注入重构
  - [#3261](https://github.com/QwenLM/qwen-code/pull/3261) `/history` 命令管理已保存的聊天会话
  - [#3248](https://github.com/QwenLM/qwen-code/pull/3248) ACP 集成完整 hooks 支持
- **其他维护合并**（未对应矩阵条目）：
  - [#3217](https://github.com/QwenLM/qwen-code/pull/3217) docs：更新 quota 耗尽后的替代方案（OpenRouter/Fireworks）
  - [#3249](https://github.com/QwenLM/qwen-code/pull/3249) ✓ VS Code 会话 tab 标题长度限制
- 总追踪 PR：**40 个（21 已合并 ✓，2 已关闭移除）**

### 2026-04-13（全量审计 + 晚间更新）

**追踪社区 PR 合并**（由社区反馈触发审计 + 全量扫描最近 4 天 PR 状态）：

- **标记已合并**（新增 7 个 ✓）：
  - [#2864](https://github.com/QwenLM/qwen-code/pull/2864) ✓（**智能工具并行** — Kind-based consecutive batching，item-7 + item-37 双侧面）
  - [#2904](https://github.com/QwenLM/qwen-code/pull/2904) ✓（上下文 Tips 系统，registry-based + LRU 跨会话轮转 + Responding→Idle hook）
  - [#3006](https://github.com/QwenLM/qwen-code/pull/3006) ✓（L2 microcompaction — 空闲上下文清理 + `cache_edits` 增量缓存删除）
  - [#3064](https://github.com/QwenLM/qwen-code/pull/3064) ✓（subagent `disallowedTools` 字段）
  - [#3066](https://github.com/QwenLM/qwen-code/pull/3066) ✓（approval mode 传播到 sub-agents）
  - [#3146](https://github.com/QwenLM/qwen-code/pull/3146) ✓（tools.sandboxImage 配置项，**部分**覆盖 item-30）
- **移除已关闭 PR**：
  - [#3082](https://github.com/QwenLM/qwen-code/pull/3082) CLOSED（终端主题检测，未合并 — 由作者 BZ-D 关闭）
  - [#3105](https://github.com/QwenLM/qwen-code/pull/3105) CLOSED（/chat 命令，已关闭待 [#3190](https://github.com/QwenLM/qwen-code/pull/3190) 替代）
- **勘误**：从 item-1 Conditional Hooks 移除错误的 PR#2825 关联——PR#2825 实际实现的是 StopFailure + PostCompact 两个新 hook 事件，和 Hook `if` 字段条件过滤完全不同
- **item-37 状态更新**：重写为"已合并"版本，对比 PR#2864 与 Claude Code `StreamingToolExecutor` 在 Kind 分类、batching 策略、shell 读写检测上的差异
- **观察到的重要维护性合并**（未对应改进矩阵条目）：
  - [#3138](https://github.com/QwenLM/qwen-code/pull/3138) ✓ 文件爬虫 100k OOM 保护（对应 [Issue#3164](https://github.com/QwenLM/qwen-code/issues/3164) heap exhaustion）
  - [#3197](https://github.com/QwenLM/qwen-code/pull/3197) ✓ `@file` 注入遵循 `respectGitIgnore`（对应 [Issue#3142](https://github.com/QwenLM/qwen-code/issues/3142) feature request）
  - [#3192](https://github.com/QwenLM/qwen-code/pull/3192) ✓ MCP server cwd 不存在时明确报错（对应 [Issue#3163](https://github.com/QwenLM/qwen-code/issues/3163)）
  - [#3194](https://github.com/QwenLM/qwen-code/pull/3194) ✓ agent 名称支持 Unicode / 中文（对应 [Issue#3149](https://github.com/QwenLM/qwen-code/issues/3149)）
  - [#3201](https://github.com/QwenLM/qwen-code/pull/3201) ✓ 输入 `exit` / `quit` 直接退出（对应 [Issue#3169](https://github.com/QwenLM/qwen-code/issues/3169)）
- 总追踪 PR：**38 个（19 已合并 ✓，2 已关闭移除）**

### 2026-04-13

**新增 item-14（闭环学习系统）**：基于对 [Hermes Agent](https://github.com/NousResearch/hermes-agent) 源码的分析（822 .py / 369K 行），新增 p0-p1-core item-14 "Nudge 驱动的闭环学习"。总项数 248→249。

- **触发**：[codeagents Issue #129](https://github.com/wenshao/codeagents/issues/129)（pomelo-nwu 建议加入 Hermes Agent 研究）
- **核心发现**：Hermes 的"闭环学习系统"由 4 个子系统组成 — 冻结快照 Memory / 自主 Skill + patch 自修补 / SQLite FTS5 跨会话搜索 / 双计数器 Nudge 触发
- **对 Qwen Code 的价值**：PR#3087（managed auto-memory + auto-dream）缺少 ① 双计数器 ② 冻结快照保护 prompt cache ③ 保守 review prompt 三个关键要素
- **新增文档**：
  - [`docs/tools/hermes-agent/`](../tools/hermes-agent/)（5 文件：README + 01-overview + 02-architecture + 03-closed-learning-loop + 04-tools-channels + EVIDENCE）
  - [`docs/comparison/closed-learning-loop-deep-dive.md`](./closed-learning-loop-deep-dive.md)（横向对比 Hermes / Claude Code / Qwen Code / Codex / Cursor / Aider / Gemini CLI / OpenCode）
- **Code Agent 总数**：18 → **19**（新增 Hermes Agent）

### 2026-04-11

- 标记已合并：[#2871](https://github.com/QwenLM/qwen-code/pull/2871) ✓（队列输入编辑 Up arrow key）、[#2914](https://github.com/QwenLM/qwen-code/pull/2914) ✓（Markdown 表格 CJK 列宽）
- 移除已关闭：[#3105](https://github.com/QwenLM/qwen-code/pull/3105)（/chat——已关闭，由 [#3093](https://github.com/QwenLM/qwen-code/pull/3093) 替代）
- 新增 PR 追踪：[#3146](https://github.com/QwenLM/qwen-code/pull/3146)（sandbox settings 中配置 sandboxImage）、[#3034](https://github.com/QwenLM/qwen-code/pull/3034)（LSP diagnostics caching）、[#3048](https://github.com/QwenLM/qwen-code/pull/3048)（vibe mode 安全 shell 自动批准）
- 总追踪 PR：38 个（13 已合并 ✓）— 后于 04-13 晚间全量审计更新为 19 已合并

### 2026-04-10（晚间更新）

- 新增 PR 追踪：[#3087](https://github.com/QwenLM/qwen-code/pull/3087)（auto-memory + auto-dream 记忆系统）、[#3082](https://github.com/QwenLM/qwen-code/pull/3082)（终端 dark/light 主题检测）、[#3093](https://github.com/QwenLM/qwen-code/pull/3093)（会话 rename/delete/auto-title）、[#3105](https://github.com/QwenLM/qwen-code/pull/3105)（/chat 命名会话管理）、[#3115](https://github.com/QwenLM/qwen-code/pull/3115)（Commit Attribution per-file AI 贡献追踪）
- 总追踪 PR：36 个（11 已合并 ✓）

### 2026-04-10

- 标记已合并：[#3042](https://github.com/QwenLM/qwen-code/pull/3042) ✓（/context detail 子命令）
- 新增 PR 追踪：[#3085](https://github.com/QwenLM/qwen-code/pull/3085)（启动优化 API preconnect + 早期输入捕获）、[#3080](https://github.com/QwenLM/qwen-code/pull/3080)（CI/CD 持久化重试模式）、[#3079](https://github.com/QwenLM/qwen-code/pull/3079)（/batch 并行批量操作 Skill）、[#3076](https://github.com/QwenLM/qwen-code/pull/3076)（Agent 工具 run_in_background）
- 总追踪 PR：31 个（10 已合并 ✓）

### 2026-04-09（晚间更新）

- 标记已合并：[#2923](https://github.com/QwenLM/qwen-code/pull/2923) ✓（Status Line 自定义）、[#3008](https://github.com/QwenLM/qwen-code/pull/3008) ✓（/plan 退出恢复模式）
- 新增 PR 追踪：[#3064](https://github.com/QwenLM/qwen-code/pull/3064)（disallowedTools Agent 工具黑名单）、[#3066](https://github.com/QwenLM/qwen-code/pull/3066)（approval mode 传播到 sub-agent）、[#3042](https://github.com/QwenLM/qwen-code/pull/3042)（/context detail 子命令）
- 总追踪 PR：27 个（9 已合并 ✓）

### 2026-04-09

- 修正子报告项数：engine 24→27、stability 34→41、hooks 32→33
- 修正 Deep-Dive 索引数：134→133（实际值）
- 同步 README.md 数据
- 重写 5 个 Agent 文档系列（Copilot CLI / Codex CLI / Aider / Goose / Kimi CLI）为开发者视角

### 2026-04-08（晚间更新）

- 标记已合并：[#2897](https://github.com/QwenLM/qwen-code/pull/2897) ✓（Thinking 块保留）、[#2898](https://github.com/QwenLM/qwen-code/pull/2898) ✓（输出 Token 升级）、[#2921](https://github.com/QwenLM/qwen-code/pull/2921) ✓（/plan 计划模式）
- 新增 PR 追踪：[#3013](https://github.com/QwenLM/qwen-code/pull/3013)（**SlicingMaxSizedBox 防闪烁——P0 backport 项！**）、[#3006](https://github.com/QwenLM/qwen-code/pull/3006)（microcompaction 空闲压缩）、[#2990](https://github.com/QwenLM/qwen-code/pull/2990)（prompt hook——LLM 推理决策 Hook，Claude Code 独有能力的 backport）
- 总追踪 PR：27 个（9 已合并 ✓）

### 2026-04-08

**新增 9 项改进建议**（来源：[learn-claude-code](https://github.com/shareAI-lab/learn-claude-code) 概念分析），总项数 240→248：

| 优先级 | 新增项 | 详情 |
|--------|--------|------|
| P1 | QWEN.md system-reminder 注入 | [engine#26](./qwen-code-improvement-report-p0-p1-engine.md#item-26) |
| P1 | 错误恢复分类路由（truncation/overflow/transport 三分支） | [engine#27](./qwen-code-improvement-report-p0-p1-engine.md#item-27) |
| P2 | Query TransitionReason 枚举（6 种转换原因） | [stability#36](./qwen-code-improvement-report-p2-stability.md#item-36) |
| P2 | 工具并发安全分类（concurrencySafe 标记） | [stability#37](./qwen-code-improvement-report-p2-stability.md#item-37) |
| P2 | 工具执行进度消息（>3s 发射进度） | [stability#38](./qwen-code-improvement-report-p2-stability.md#item-38) |
| P2 | 运行时任务模型（work-graph vs runtime task） | [stability#39](./qwen-code-improvement-report-p2-stability.md#item-39) |
| P2 | 后台通知 drain-before-call | [stability#40](./qwen-code-improvement-report-p2-stability.md#item-40) |
| P2 | 压缩后身份重注入（messages≤3 时注入身份） | [stability#41](./qwen-code-improvement-report-p2-stability.md#item-41) |
| P3 | 团队通信协议（邮箱/心跳/关闭请求） | [hooks#33](./qwen-code-improvement-report-p3-hooks.md#item-33) |

**勘误**：删除 item-20（/thinkback）——经源码验证 Claude Code 的 `/thinkback` 是 Year in Review 动画功能，非会话时间线回顾。原 item-21（/context）重编号为 item-20。

### 2026-04-07

- 新增 PR 追踪：[#2936](https://github.com/QwenLM/qwen-code/pull/2936)（Fork Subagent）、[#2932](https://github.com/QwenLM/qwen-code/pull/2932) ✓（/review 增强——实现了审查报告 10 项建议中的 9 项）
- 标记已合并：[#2854](https://github.com/QwenLM/qwen-code/pull/2854) ✓（Mid-Turn Queue Drain）、[#2889](https://github.com/QwenLM/qwen-code/pull/2889) ✓（危险操作指导）

### 2026-04-06

- 新增 7 个 PR 追踪：[#2921](https://github.com/QwenLM/qwen-code/pull/2921)（/plan）、[#2923](https://github.com/QwenLM/qwen-code/pull/2923)（StatusLine）、[#2914](https://github.com/QwenLM/qwen-code/pull/2914)（表格渲染）、[#2915](https://github.com/QwenLM/qwen-code/pull/2915)（/clear）、[#2916](https://github.com/QwenLM/qwen-code/pull/2916)（/context SDK）、[#2911](https://github.com/QwenLM/qwen-code/pull/2911)（ConfigTool）、[#2904](https://github.com/QwenLM/qwen-code/pull/2904)（Tips 系统）

### 2026-04-05

- 初始版本：240 项改进建议 + 133 篇 Deep-Dive 索引
