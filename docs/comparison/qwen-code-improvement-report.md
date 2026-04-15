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
| **P0** | [Fork Subagent](./fork-subagent-deep-dive.md) — Subagent 继承完整对话上下文，共享 prompt cache 省 80%+ 费用 [↓](./qwen-code-improvement-report-p0-p1-core.md#item-2) | Subagent 必须从零开始 | 中 | [PR#2936](https://github.com/QwenLM/qwen-code/pull/2936) / [Roadmap#2409](https://github.com/QwenLM/qwen-code/issues/2409) |
| **P0** | [会话崩溃恢复与中断检测](./crash-recovery-deep-dive.md) — 3 种中断状态检测 + 合成续行 + 全量恢复 [↓](./qwen-code-improvement-report-p0-p1-engine.md#item-7) | 无崩溃恢复 | 大 | — |
| **P1** | [Speculation](../tools/claude-code/10-prompt-suggestions.md) — 预测用户下一步并提前执行，Tab 接受零延迟 [↓](./qwen-code-improvement-report-p0-p1-core.md#item-3) | 已实现但默认关闭 | 小 | [PR#2525](https://github.com/QwenLM/qwen-code/pull/2525) ✓ |
| **P1** | [会话记忆](./memory-system-deep-dive.md) — 关键决策/文件结构自动提取，新 session 自动注入 [↓](./qwen-code-improvement-report-p0-p1-core.md#item-4) | 仅简单笔记工具 | 大 | [PR#3087](https://github.com/QwenLM/qwen-code/pull/3087) |
| **P1** | [Auto Dream](./memory-system-deep-dive.md) — 后台 agent 自动合并去重过时记忆 [↓](./qwen-code-improvement-report-p0-p1-core.md#item-5) | 缺失 | 中 | — |
| **P1** | [Nudge 驱动的闭环学习](./closed-learning-loop-deep-dive.md) — 双计数器 + 后台 review 子代理 + 冻结快照 + 自修补（Hermes Agent 参考） [↓](./qwen-code-improvement-report-p0-p1-core.md#item-14) | 被动记忆（无 nudge） | 中 | [PR#3087](https://github.com/QwenLM/qwen-code/pull/3087)（部分覆盖） |
| **P1** | [工具动态发现](./tool-search-deep-dive.md) — 仅加载核心工具，其余按需搜索，省 50%+ token [↓](./qwen-code-improvement-report-p0-p1-core.md#item-11) | 全部工具始终加载 | 小 | — |
| **P1** | [智能工具并行](./tool-parallelism-deep-dive.md) — 连续只读工具并行执行，代码探索快 5-10× [↓](./qwen-code-improvement-report-p0-p1-core.md#item-7) | 除 Agent 外全部顺序 | 小 | [PR#2864](https://github.com/QwenLM/qwen-code/pull/2864) ✓ / [Roadmap#2516](https://github.com/QwenLM/qwen-code/issues/2516) |
| **P1** | [启动优化](./startup-optimization-deep-dive.md) — TCP preconnect + 启动期间键盘捕获不丢失 [↓](./qwen-code-improvement-report-p0-p1-core.md#item-8) | 完全缺失 | 小 | [PR#3085](https://github.com/QwenLM/qwen-code/pull/3085) / [PR#3242](https://github.com/QwenLM/qwen-code/pull/3242) / [PR#3232](https://github.com/QwenLM/qwen-code/pull/3232) ✓（profiler） |
| **P1** | [指令条件规则](./instruction-loading-deep-dive.md) — 按文件路径匹配加载不同编码规范 [↓](./qwen-code-improvement-report-p0-p1-core.md#item-9) | 所有指令始终加载 | 中 | [Roadmap#125](https://github.com/QwenLM/qwen-code/issues/125) |
| **P1** | [Commit Attribution](./git-workflow-session-deep-dive.md) — git commit 中标注 AI vs 人类代码贡献比例 [↓](./qwen-code-improvement-report-p0-p1-core.md#item-12) | 缺失 | 小 | [PR#3115](https://github.com/QwenLM/qwen-code/pull/3115) |
| **P1** | [会话分支](./git-workflow-session-deep-dive.md) — /branch 从任意节点 fork 对话，探索替代方案 [↓](./qwen-code-improvement-report-p0-p1-core.md#item-13) | 缺失 | 中 | [PR#3022](https://github.com/QwenLM/qwen-code/pull/3022) |
| **P1** | GitHub Actions CI — 自动 PR 审查/issue 分类 action [↓](./qwen-code-improvement-report-p0-p1-platform.md#item-1) | 缺失 | 中 | — |
| **P1** | GitHub Code Review — 多 Agent自动 PR review + inline 评论 [↓](./qwen-code-improvement-report-p0-p1-platform.md#item-2) | **已实现**（内置 `/review` skill，5 agent 并行 + Create Review API） | — | [PR#2348](https://github.com/QwenLM/qwen-code/pull/2348) ✓ / [PR#2376](https://github.com/QwenLM/qwen-code/pull/2376) ✓ / [PR#2687](https://github.com/QwenLM/qwen-code/pull/2687) ✓ / [PR#2932](https://github.com/QwenLM/qwen-code/pull/2932) ✓ / [Roadmap#742](https://github.com/QwenLM/qwen-code/issues/742) |
| **P1** | [HTTP Hooks](./http-hooks-deep-dive.md) — Hook 可 POST JSON 到 URL 并接收响应（不仅 shell 命令）[↓](./qwen-code-improvement-report-p0-p1-platform.md#item-3) | 仅 shell 命令 | 小 | [PR#2827](https://github.com/QwenLM/qwen-code/pull/2827) |
| **P1** | [Structured Output](./structured-output-deep-dive.md) — `--json-schema` 强制 JSON Schema 验证输出 [↓](./qwen-code-improvement-report-p0-p1-platform.md#item-4) | 缺失 | 小 | — |
| **P1** | [Agent SDK 增强](./agent-sdk-python-deep-dive.md) — Python SDK + 流式回调 + 工具审批回调（Qwen 仅 TS SDK）[↓](./qwen-code-improvement-report-p0-p1-platform.md#item-5) | 仅 TypeScript SDK | 中 | — |
| **P1** | [Bare Mode](./bare-mode-deep-dive.md) — `--bare` 跳过所有自动发现，CI/脚本最快启动 [↓](./qwen-code-improvement-report-p0-p1-platform.md#item-6) | 缺失 | 小 | — |
| **P1** | [Remote Control Bridge](./remote-control-bridge-deep-dive.md) — 从手机/浏览器驱动本地终端 session [↓](./qwen-code-improvement-report-p0-p1-platform.md#item-7) | 缺失 | 大 | — |
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
| **P1** | [Coordinator/Swarm 多 Agent编排](./coordinator-swarm-orchestration-deep-dive.md) — Leader/Worker 团队 + 3 种执行后端 [↓](./qwen-code-improvement-report-p0-p1-engine.md#item-14) | 仅 Arena 竞赛 | 大 | [PR#2886](https://github.com/QwenLM/qwen-code/pull/2886) / [Roadmap#1815](https://github.com/QwenLM/qwen-code/issues/1815) / [#1816](https://github.com/QwenLM/qwen-code/issues/1816) |
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
| **P2** | [Fast Mode](./cost-fastmode-deep-dive.md) — 同一模型标准/快速推理切换（$5→$30/Mtok），含冷却机制 [↓](./qwen-code-improvement-report-p2-core.md#item-5) | 仅指定备用模型 | 小 | — |
| **P2** | [并发 Session](./cost-fastmode-deep-dive.md) — 多终端 PID 追踪 + 后台 Agent 脱附/重附 [↓](./qwen-code-improvement-report-p2-core.md#item-8) | 缺失 | 中 | — |
| **P2** | [Git Diff 统计](./git-workflow-session-deep-dive.md) — 编辑后 numstat + hunks 结构化 diff（50 文件/1MB 上限） [↓](./qwen-code-improvement-report-p2-core.md#item-9) | 无 git-aware diff | 小 | — |
| **P2** | [文件历史快照](./git-workflow-session-deep-dive.md) — per-file SHA256 备份，按消息粒度恢复（100 个/session） [↓](./qwen-code-improvement-report-p2-core.md#item-10) | git-level checkpoint | 中 | — |
| **P2** | [Computer Use](./computer-use-deep-dive.md) — macOS 截图 + 鼠标/键盘 + 剪贴板，通过 MCP 桥接 [↓](./qwen-code-improvement-report-p2-core.md#item-6) | 缺失 | 大 | — |
| **P2** | [Deep Link](./deep-link-protocol-deep-dive.md) — `claude-cli://` 一键从浏览器/IDE 启动 Agent + 预填充 prompt [↓](./qwen-code-improvement-report-p2-core.md#item-11) | 缺失 | 中 | — |
| **P2** | [`/context` 非交互输出](./context-usage-noninteractive-deep-dive.md) — 将上下文诊断暴露给脚本、CI 与外部控制器 [↓](./qwen-code-improvement-report-p2-tools-ui.md#item-20) | 仅交互式 | 小 | [PR#2916](https://github.com/QwenLM/qwen-code/pull/2916) / [PR#3042](https://github.com/QwenLM/qwen-code/pull/3042) ✓ |
| **P1** | [Team Memory](./team-memory-deep-dive.md) — 团队共享项目知识 + 29 条 gitleaks 密钥扫描 + ETag 同步 [↓](./qwen-code-improvement-report-p0-p1-core.md#item-10) | 缺失 | 大 | — |
| **P2** | [Plan 模式 Interview](./plan-mode-interview-deep-dive.md) — 先澄清需求再形成计划，分离访谈/规划/执行阶段 [↓](./qwen-code-improvement-report-p2-core.md#item-12) | 无 interview 阶段 | 中 | — |
| **P2** | [BriefTool 异步用户消息](./brieftool-async-user-messages-deep-dive.md) — Agent 主动发消息/附件给用户，不阻塞当前工具执行 [↓](./qwen-code-improvement-report-p2-core.md#item-13) | 缺失 | 中 | — |
| **P2** | [SendMessageTool](./multi-agent-deep-dive.md) — 多 Agent间消息传递、shutdown 请求、plan 审批 [↓](./qwen-code-improvement-report-p2-core.md#item-14) | 缺失 | 中 | — |
| **P2** | [FileIndex 模糊文件搜索](./file-index-fuzzy-search-deep-dive.md) — fzf 风格模糊文件搜索 + 异步增量索引 [↓](./qwen-code-improvement-report-p2-core.md#item-15) | 依赖 rg/glob | 中 | [PR#3214](https://github.com/QwenLM/qwen-code/pull/3214)（git ls-files + rg 回退） |
| **P2** | [Notebook Edit 原子级编辑](./notebook-edit-deep-dive.md) — Jupyter cell 编辑 + 自动 cell ID 追踪 + 文件历史快照 [↓](./qwen-code-improvement-report-p2-core.md#item-16) | 缺失 | 中 | — |
| **P2** | 自定义快捷键 — multi-chord 组合键 + 跨平台适配 + `keybindings.json` 自定义 [↓](./qwen-code-improvement-report-p2-core.md#item-17) | 缺失 | 中 | — |
| **P2** | [Session Ingress Auth](./session-ingress-auth-deep-dive.md) — 远程会话 bearer token 认证（企业多用户环境） [↓](./qwen-code-improvement-report-p2-core.md#item-18) | 缺失 | 中 | — |
| **P2** | [企业代理](./enterprise-proxy-support-deep-dive.md) — CONNECT relay + CA cert 注入 + NO_PROXY allowlist（容器环境） [↓](./qwen-code-improvement-report-p2-core.md#item-19) | 缺失 | 大 | — |
| **P2** | [ConfigTool](./config-tool-dynamic-settings-deep-dive.md) — 模型通过工具读写设置（主题/模型/权限等），带 schema 验证 [↓](./qwen-code-improvement-report-p2-core.md#item-20) | 仅 /settings 命令 | 小 | [PR#2911](https://github.com/QwenLM/qwen-code/pull/2911) |
| **P2** | [终端主题检测](./terminal-theme-detection-deep-dive.md) — OSC 11 查询 dark/light + COLORFGBG 环境变量回退 [↓](./qwen-code-improvement-report-p2-core.md#item-21) | 缺失 | 小 | — |
| **P2** | [自动后台化 Agent](./session-backgrounding-deep-dive.md) — 当前会话可转后台继续执行，并在稍后恢复到前台 [↓](./qwen-code-improvement-report-p2-core.md#item-22) | 需显式指定 | 小 | — |
| **P2** | Denial Tracking — 连续权限拒绝自动回退到手动确认模式，防止静默阻塞 [↓](./qwen-code-improvement-report-p2-core.md#item-7) | 缺失 | 小 | — |
| **P2** | [队列输入编辑](./input-queue-deep-dive.md) — 排队中的指令可通过方向键弹出到输入框重新编辑 [↓](./qwen-code-improvement-report-p2-core.md#item-23) | 缺失 | 小 | [PR#2871](https://github.com/QwenLM/qwen-code/pull/2871) ✓ |
| **P2** | [状态栏紧凑布局](./compact-status-bar-deep-dive.md) — 固定高度不伸缩，最大化终端内容区域 [↓](./qwen-code-improvement-report-p2-core.md#item-24) | Footer 占用偏高 | 小 | — |
| **P2** | [会话标签与搜索](./session-tags-search-deep-dive.md) — /tag 命令打标签 + 按标签/仓库/标题搜索历史会话 [↓](./qwen-code-improvement-report-p2-core.md#item-25) | 仅按时间排序 | 小 | — |
| **P2** | Plan 状态机化 + Hint 注入 — 4 状态 subtask + 每轮 hint 注入（AgentScope 参考） [↓](./qwen-code-improvement-report-p2-core.md#item-26) | `/plan` 是一次性文档 | 中 | — |
| **P2** | A2A 协议集成 — 跨 agent 通信 + AgentCard + 服务发现（AgentScope 参考） [↓](./qwen-code-improvement-report-p2-core.md#item-27) | 仅 MCP Client | 大 | — |
| **P2** | OTel 原生 Tracing — 5 类 span extractor（Agent/LLM/Tool/Formatter/Embedding，AgentScope 参考） [↓](./qwen-code-improvement-report-p2-core.md#item-28) | 仅阿里云 RUM | 中 | — |
| **P2** | Conditional Hooks — Hook `if` 字段用权限规则语法按工具/路径过滤 [↓](./qwen-code-improvement-report-p2-tools-commands.md#item-1) | 缺失 | 小 | — |
| **P2** | [Transcript Search 会话记录搜索](./transcript-search-navigation-deep-dive.md) — 按 `/` 搜索会话记录，`n`/`N` 导航匹配项 [↓](./qwen-code-improvement-report-p2-tools-commands.md#item-2) | 缺失 | 小 | — |
| **P2** | [Bash File Watcher](./file-watcher-stale-edit-deep-dive.md) — 检测 formatter/linter 修改已读文件，防止 stale-edit [↓](./qwen-code-improvement-report-p2-tools-commands.md#item-3) | 缺失 | 小 | — |
| **P2** | [/batch 并行操作](./batch-parallel-execution-deep-dive.md) — 编排大规模并行变更（多文件/多任务）[↓](./qwen-code-improvement-report-p2-tools-commands.md#item-4) | 缺失 | 中 | [PR#3079](https://github.com/QwenLM/qwen-code/pull/3079) |
| **P2** | PDF / 二进制文件读取 — read_file 内置 PDF + 图片 + Notebook 支持 [↓](./qwen-code-improvement-report-p2-tools-commands.md#item-21) | 拒绝 PDF（[#2024](https://github.com/QwenLM/qwen-code/pull/2024)） | 中 | [Issue#38](https://github.com/QwenLM/qwen-code/issues/38) |
| **P2** | Skill 级模型覆盖 — SKILL.md frontmatter `model:` 字段，按阶段切换模型 [↓](./qwen-code-improvement-report-p2-tools-commands.md#item-22) | 仅 session 级 | 小 | [PR#2949](https://github.com/QwenLM/qwen-code/pull/2949) ✓ |
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
| **P2** | /rewind 检查点回退 — 会话内代码 + 对话恢复到之前的检查点 [↓](./qwen-code-improvement-report-p2-tools-ui.md#item-5) | 缺失 | 中 | [Roadmap#2342](https://github.com/QwenLM/qwen-code/issues/2342) |
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
| **P2** | 工具执行进度消息 — 长时间工具（>3s）发射进度事件，UI 显示"正在安装依赖 42/100..." [↓](./qwen-code-improvement-report-p2-stability.md#item-38) | 仅 Spinner | 小 | — |
| **P2** | 运行时任务模型 — 区分 work-graph task（持久目标）vs runtime task（执行槽），防止状态混淆 [↓](./qwen-code-improvement-report-p2-stability.md#item-39) | 仅 TodoWriteTool | 中 | — |
| **P2** | 后台通知 drain-before-call — LLM 调用前排空后台任务通知队列，确保模型看到最新结果 [↓](./qwen-code-improvement-report-p2-stability.md#item-40) | 无通知排空 | 小 | — |
| **P2** | 压缩后身份重注入 — 上下文压缩后 messages<3 条时注入 Agent 身份块，防止 Agent "忘记自己是谁" [↓](./qwen-code-improvement-report-p2-stability.md#item-41) | 无身份重注入 | 小 | — |
| **P2** | 终端渲染优化 — DEC 2026 同步输出 + 差分渲染 + 双缓冲 + DECSTBM 硬件滚动 + 缓存池化 + alt-screen [↓](./qwen-code-improvement-report-p2-tools-commands.md#item-8) | 仅消息拆分防闪烁 | 大 | — |
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
| **P2** | [LSP 服务器并行启动](./lsp-parallel-startup-deep-dive.md) — Promise.all 并行启动 + Promise.race 端口探测 [↓](./qwen-code-improvement-report-p2-perf.md#item-7) | 顺序 for 循环 | 小 | [PR#3034](https://github.com/QwenLM/qwen-code/pull/3034) |
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
| [P2 核心功能与企业特性](./qwen-code-improvement-report-p2-core.md) | 中等优先级（Shell 安全、MDM 企业策略、Token 计数、Computer Use、AgentScope Plan/A2A/OTel 参考等） | 28 |
| [P2 工具与命令](./qwen-code-improvement-report-p2-tools-commands.md) | 中等优先级（Conditional Hooks、/batch、MCP 重连、Ripgrep 回退、Skill 模型覆盖等） | 22 |
| [P2 界面与 UX](./qwen-code-improvement-report-p2-tools-ui.md) | 中等优先级（Token 警告、Spinner、/rewind、Diff 渲染、/plan 等） | 20 |
| [P2 性能优化](./qwen-code-improvement-report-p2-perf.md) | 中等优先级（流式执行、缓存模式、延迟初始化、请求合并等） | 34 |
| [P2 稳定性、安全与 CI/CD](./qwen-code-improvement-report-p2-stability.md) | 中等优先级（Unicode sanitization、sandbox集成、SSRF 防护、密钥扫描等） | 41 |
| [P3 功能特性](./qwen-code-improvement-report-p3-features.md) | 低优先级功能特性（动态状态栏、Feature Gates、Vim、语音、插件市场等） | 16 |
| [P3 用户体验](./qwen-code-improvement-report-p3-ux.md) | 低优先级用户体验（Virtual Scrolling、Turn Diffs、Buddy、settingsSync 等） | 9 |
| [P3 Hook 与组件](./qwen-code-improvement-report-p3-hooks.md) | 低优先级 Hook 与组件（useInboxPoller、AgentSummary、usePrStatus 等） | 33 |

## 四、架构差异总结

| 维度 | Claude Code | Qwen Code | 差距评估 | 进展 |
|------|-------------|-----------|----------|------|
| **[Mid-Turn Queue Drain](./command-queue-orchestration-deep-dive.md)** | `query.ts` 工具批次间 drain | 无 | 显著落后 | [PR#2854](https://github.com/QwenLM/qwen-code/pull/2854) ✓ |
| 压缩 (Compression) 策略 | 4 层分层压缩 | 单一阈值压缩 | 显著落后 | — |
| Subagent | 支持 fork + 上下文继承 | 仅预定义类型 | 显著落后 | [PR#2936](https://github.com/QwenLM/qwen-code/pull/2936) |
| **智能工具并行** | Kind-based batching（默认 10 并发） | Agent 并发 / 其他顺序 | 中等差距 | [PR#2864](https://github.com/QwenLM/qwen-code/pull/2864) ✓ |
| 投机执行 (Speculation) | 完整 overlay-fs + cow（991 行） | v0.15.0 已完整实现（563 行），默认关闭 | 小差距 | [PR#2525](https://github.com/QwenLM/qwen-code/pull/2525) ✓ |
| 启动优化 | API Preconnect + Early Input | 无 | 缺失 | [PR#3085](https://github.com/QwenLM/qwen-code/pull/3085) / [PR#3232](https://github.com/QwenLM/qwen-code/pull/3232) ✓（profiler） |
| 按路径注入上下文规则 | `.claude/rules/` + frontmatter `paths:` 惰加载 | 单一 QWEN.md | 中等差距 | — |
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
| 会话分支 | /branch 对话分叉 | 无 | 缺失 | [PR#3022](https://github.com/QwenLM/qwen-code/pull/3022) |
| Output Styles | Learning / Explanatory 模式 | 无 | 缺失 | — |
| Fast Mode | 速度/成本分级推理 | 无 | 缺失 | — |
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

- **[item-26 Plan 状态机化](./qwen-code-improvement-report-p2-core.md#item-26)** — 4 状态 subtask（todo/in_progress/done/abandoned）+ 每轮自动 hint 注入，升级 `/plan` 从"一次性文档"到"持久状态机"
- **[item-27 A2A 协议集成](./qwen-code-improvement-report-p2-core.md#item-27)** — 集成 `a2a-sdk` + AgentCard + Well-known/File/HTTP resolver，让 qwen-code 参与跨 agent 网络
- **[item-28 OTel 原生 Tracing](./qwen-code-improvement-report-p2-core.md#item-28)** — 5 类 span extractor（Agent/LLM/Tool/Formatter/Embedding），对标 AgentScope `src/agentscope/tracing/_trace.py:24-45` 的 13 个 extractor 实现

总项数 **249 → 252**，p2-core 子报告 25 → 28。

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

实现深度**已超过 Claude Code 托管的 GitHub Code Review**。涉及 PR：[#2348](https://github.com/QwenLM/qwen-code/pull/2348) / [#2376](https://github.com/QwenLM/qwen-code/pull/2376) / [#2380](https://github.com/QwenLM/qwen-code/pull/2380) / [#2687](https://github.com/QwenLM/qwen-code/pull/2687) / [#2932](https://github.com/QwenLM/qwen-code/pull/2932) — 全部已合并。

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
  - [#3178](https://github.com/QwenLM/qwen-code/pull/3178) + [#3236](https://github.com/QwenLM/qwen-code/pull/3236) 工具验证重试循环检测 + 停止指令
  - [#3255](https://github.com/QwenLM/qwen-code/pull/3255) Fork Subagent params 构造时注入重构
  - [#3261](https://github.com/QwenLM/qwen-code/pull/3261) `/history` 命令管理已保存的聊天会话
  - [#3248](https://github.com/QwenLM/qwen-code/pull/3248) ACP 集成完整 hooks 支持
- **其他维护合并**（未对应矩阵条目）：
  - [#3217](https://github.com/QwenLM/qwen-code/pull/3217) docs：更新 quota 耗尽后的替代方案（OpenRouter/Fireworks）
  - [#3249](https://github.com/QwenLM/qwen-code/pull/3249) VS Code 会话 tab 标题长度限制
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
  - [#3138](https://github.com/QwenLM/qwen-code/pull/3138) 文件爬虫 100k OOM 保护（对应 [Issue#3164](https://github.com/QwenLM/qwen-code/issues/3164) heap exhaustion）
  - [#3197](https://github.com/QwenLM/qwen-code/pull/3197) `@file` 注入遵循 `respectGitIgnore`（对应 [Issue#3142](https://github.com/QwenLM/qwen-code/issues/3142) feature request）
  - [#3192](https://github.com/QwenLM/qwen-code/pull/3192) MCP server cwd 不存在时明确报错（对应 [Issue#3163](https://github.com/QwenLM/qwen-code/issues/3163)）
  - [#3194](https://github.com/QwenLM/qwen-code/pull/3194) agent 名称支持 Unicode / 中文（对应 [Issue#3149](https://github.com/QwenLM/qwen-code/issues/3149)）
  - [#3201](https://github.com/QwenLM/qwen-code/pull/3201) 输入 `exit` / `quit` 直接退出（对应 [Issue#3169](https://github.com/QwenLM/qwen-code/issues/3169)）
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
