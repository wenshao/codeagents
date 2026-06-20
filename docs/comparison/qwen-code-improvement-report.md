# Qwen Code 改进建议报告

> 基于对 Claude Code（源码分析，56 个顶层模块，~1800 文件）与 Qwen Code（开源源码，**~4,750 文件 / ~2,700 源 `.ts(x)`**，14 包，含 daemon/web-shell/desktop）的系统性源码对比分析。
>
> **相关报告**：
> - [Gemini CLI 上游 backport 报告（61 项）](./qwen-code-gemini-upstream-report.md)——Qwen Code 上游的可 backport 改进
> - [Codex CLI 对标改进报告（28 项）](./qwen-code-codex-improvements.md)——沙箱、Apply Patch、Feature Flag、网络代理、Sticky Env、Permission Profiles 等
> - [OpenCode 对标改进报告（29 项）](./qwen-code-opencode-improvements.md)——Provider 系统、Plugin 插件、Snapshot 快照、可配置截断、编辑器上下文协议等
> - [/review 功能分析](./qwen-code-review-improvements.md)——审查功能 5 方对比（含 gstack）
> - [Qwen Code 性能优化 Roadmap](./qwen-code-perf-roadmap.md)——按 ROI 排序的可执行优化清单（P0/P1/P2/P3 + 度量驱动方法）
> - [ReadFile 工具 Deep-Dive](./read-file-tool-deep-dive.md)——12 项 Claude Code 可借鉴能力（file_unchanged 去重 / 图像压缩 / token 上限 / PDF 多策略等）
> - [Reasoning Effort Deep-Dive](./reasoning-effort-deep-dive.md)——Claude `/effort` 4 档 vs Codex `reasoning_effort` 6 档对比 + cache 影响 + Qwen 设计启发（处理 [Issue #130](https://github.com/wenshao/codeagents/issues/130)）
> - [Claude Code `/agents` UI Deep-Dive](./claude-code-agents-command-deep-dive.md)——Subagent 定义管理 UI（~3042 LOC 7-mode + 11-step wizard + AI 生成 agent + 17+ 字段格式 + 6 source 分层）+ Qwen Code 借鉴项（`omitClaudeMd` / `criticalSystemReminder` / `isolation: worktree` / Stage 1.5c daemon-side state CRUD 范本）
> - [Qwen Code 贡献者页面](./qwen-code-contributors.md)——项目治理总览 · Alibaba 内部团队 + 外部社区 + 治理结构图
> - [Qwen Code 外部贡献者分析](./qwen-code-external-contributors.md)——外部社区深度分析 + 5 种贡献模式

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
| **P0** | [多层上下文压缩](./context-compression-deep-dive.md) — 自动裁剪旧工具结果 + 摘要，用户无需手动 /compress [↓](./qwen-code-improvement-report-p0-p1-core.md#item-1) | ✅ 多层自动压缩（microcompaction 空闲裁剪旧工具结果 + warn/auto/hard 三档自动阈值 ladder + reactive 溢出压缩 + subagent/堆压力 auto + state_snapshot 摘要 + `/compress-fast` 无 LLM 规则压缩）；用户无需手动 /compress（压缩后文件/Skill 重注入仍缺）| 中 | [PR#3006](https://github.com/QwenLM/qwen-code/pull/3006) ✓（microcompaction 空闲裁剪）/ [PR#3879](https://github.com/QwenLM/qwen-code/pull/3879) ✓（reactive 溢出）/ [PR#4345](https://github.com/QwenLM/qwen-code/pull/4345) ✓（三档 ladder 自动阈值）/ [PR#4893](https://github.com/QwenLM/qwen-code/pull/4893) ✓（/compress-fast）|
| **P0** | [Fork Subagent](./fork-subagent-deep-dive.md) — Subagent 继承完整对话上下文，共享 prompt cache 省 80%+ 费用 [↓](./qwen-code-improvement-report-p0-p1-core.md#item-2) | ✅ Fork 已实现且默认启用（`subagent_type:"fork"`：继承父代理完整对话历史 + systemInstruction/工具声明 verbatim 共享 DashScope cache 前缀 + `FORK_PLACEHOLDER_RESULT` 占位一致 + AsyncLocalStorage 递归防护 + worktree 隔离；fire-and-forget 后台执行，仅交互式）。常规 subagent 仍从零（fork 为显式选择）| 中 | [PR#2936](https://github.com/QwenLM/qwen-code/pull/2936) ✓（2026-04-14 · 实现 + cache 共享）/ [PR#3255](https://github.com/QwenLM/qwen-code/pull/3255) ✓（构造期参数）/ [PR#4574](https://github.com/QwenLM/qwen-code/pull/4574) ✓（feature gate + don't peek/race）/ [PR#4963](https://github.com/QwenLM/qwen-code/pull/4963) ✓（2026-06-13 · 默认启用）/ [PR#5155](https://github.com/QwenLM/qwen-code/pull/5155) ✓（fire-and-forget 语义收敛）|
| **P0** | [会话崩溃恢复与中断检测](./crash-recovery-deep-dive.md) — 3 种中断状态检测 + 合成续行 + 全量恢复 [↓](./qwen-code-improvement-report-p0-p1-engine.md#item-7) | 🟡 读端容错已加，3 状态中断检测 + 合成续行仍待 | 大 | [PR#3656](https://github.com/QwenLM/qwen-code/pull/3656) ✓（2026-04-27 合并 · JSONL `}{` 粘连记录 brace-depth 扫描恢复 + per-line 容错 · 修复 #3606）|
| **P1** | [Speculation](../tools/claude-code/10-prompt-suggestions.md) — 预测用户下一步并提前执行，Tab 接受零延迟 [↓](./qwen-code-improvement-report-p0-p1-core.md#item-3) | 已实现但默认关闭 | 小 | [PR#2525](https://github.com/QwenLM/qwen-code/pull/2525) ✓ |
| **P1** | [会话记忆](./memory-system-deep-dive.md) — 关键决策/文件结构自动提取，新 session 自动注入 [↓](./qwen-code-improvement-report-p0-p1-core.md#item-4) | 仅简单笔记工具 | 大 | [PR#3087](https://github.com/QwenLM/qwen-code/pull/3087) ✓ |
| **P1** | [Auto Dream](./memory-system-deep-dive.md) — 后台 agent 自动合并去重过时记忆 [↓](./qwen-code-improvement-report-p0-p1-core.md#item-5) | **✓ 已实现**（managed auto-memory + auto-dream）| 中 | [PR#3087](https://github.com/QwenLM/qwen-code/pull/3087) ✓（managed auto-memory + auto-dream） |
| **P1** | [Nudge 驱动的闭环学习](./closed-learning-loop-deep-dive.md) — 双计数器 + 后台 review 子代理 + 冻结快照 + 自修补（Hermes Agent 参考） [↓](./qwen-code-improvement-report-p0-p1-core.md#item-14) | 被动记忆（无 nudge） | 中 | [PR#3087](https://github.com/QwenLM/qwen-code/pull/3087) ✓（部分覆盖） |
| **P1** | [工具动态发现](./tool-search-deep-dive.md) — 仅加载核心工具，其余按需搜索（Qwen 实测节省 ~46% token / Claude 设计 ~60%；但 DeepSeek-v4 prefix cache 实测日成本 +214% — 详 PR#4069）[↓](./qwen-code-improvement-report-p0-p1-core.md#item-11) | **✅ 已合并** [PR#3589](https://github.com/QwenLM/qwen-code/pull/3589) MERGED 2026-05-10 +3796/-22 + [PR#4022](https://github.com/QwenLM/qwen-code/pull/4022) 扩展 4 deferred 工具 + [PR#4041](https://github.com/QwenLM/qwen-code/pull/4041) ask_user_question 反向修复 + [PR#4069](https://github.com/QwenLM/qwen-code/pull/4069) `tools.toolSearch.enabled` 全局开关 + `deepseek-v4-*` auto-disable | 小 | ✓ |
| **P1** | [智能工具并行](./tool-parallelism-deep-dive.md) — 连续只读工具并行执行，代码探索快 5-10× [↓](./qwen-code-improvement-report-p0-p1-core.md#item-7) | 除 Agent 外全部顺序 | 小 | [PR#2864](https://github.com/QwenLM/qwen-code/pull/2864) ✓ / [Roadmap#2516](https://github.com/QwenLM/qwen-code/issues/2516) |
| **P1** | [启动优化](./startup-optimization-deep-dive.md) — TCP preconnect + 启动期间键盘捕获不丢失 [↓](./qwen-code-improvement-report-p0-p1-core.md#item-8) | preconnect ✓ / early input ✓ | 小 | [PR#3085](https://github.com/QwenLM/qwen-code/pull/3085) ✗（关闭，拆分）/ [PR#3318](https://github.com/QwenLM/qwen-code/pull/3318) ✓（preconnect，2026-04-27 合并）/ [PR#3319](https://github.com/QwenLM/qwen-code/pull/3319) ✓（early input，2026-04-18 合并）/ [PR#3232](https://github.com/QwenLM/qwen-code/pull/3232) ✓（profiler） |
| **P1** | [指令条件规则](./instruction-loading-deep-dive.md) — 按文件路径匹配加载不同编码规范 [↓](./qwen-code-improvement-report-p0-p1-core.md#item-9) | 所有指令始终加载 | 中 | [PR#3339](https://github.com/QwenLM/qwen-code/pull/3339) ✓ / [Roadmap#125](https://github.com/QwenLM/qwen-code/issues/125) |
| **P1** | [Commit Attribution](./git-workflow-session-deep-dive.md) — git commit 中标注 AI vs 人类代码贡献比例 [↓](./qwen-code-improvement-report-p0-p1-core.md#item-12) | **✅ 已实现且超 Claude**（独家 git notes refs/notes/ai-attribution + per-file aiChars/humanChars 字符级追踪 + 不污染 commit message）| 小 | **[PR#3115](https://github.com/QwenLM/qwen-code/pull/3115) ✓ 2026-05-08 MERGED · +7075/-224** |
| **P1** | [会话分支](./git-workflow-session-deep-dive.md) — /branch 从任意节点 fork 对话，探索替代方案 [↓](./qwen-code-improvement-report-p0-p1-core.md#item-13) | **✅ 已实现**（`/branch` 命令 · 对标 Claude `--fork-session` flag；`/fork` 另属 fork-subagent，非分支别名）| 中 | [PR#3022](https://github.com/QwenLM/qwen-code/pull/3022) ✗（已关闭）/ [PR#3292](https://github.com/QwenLM/qwen-code/pull/3292) ✗（已关闭）/ **[PR#3539](https://github.com/QwenLM/qwen-code/pull/3539) ✓ 2026-05-08 MERGED · +1538/-18**（JSONL 复制 + `forkedFrom` stamp + atomic create + rollback-safe swap）|
| **P1** | GitHub Actions CI — 自动 PR 审查/issue 分类 action [↓](./qwen-code-improvement-report-p0-p1-platform.md#item-1) | 缺失 | 中 | — |
| **P1** | GitHub Code Review — 多 Agent自动 PR review + inline 评论 [↓](./qwen-code-improvement-report-p0-p1-platform.md#item-2) | **已实现 + 持续扩展**（内置 `/review` skill，9 agent 并行 + 3 personas + 迭代反向审计 + 6 个 `qwen review` CLI 子命令） | — | [PR#2348](https://github.com/QwenLM/qwen-code/pull/2348) ✓ / [PR#2687](https://github.com/QwenLM/qwen-code/pull/2687) ✓ / [PR#2932](https://github.com/QwenLM/qwen-code/pull/2932) ✓ / [PR#3276](https://github.com/QwenLM/qwen-code/pull/3276)（弱模型并行强化） / [PR#3754](https://github.com/QwenLM/qwen-code/pull/3754) ✓（**2026-05-01 合并 · +2423/-138** · 5→9 agent + 3 undirected personas + iterative reverse audit + self-PR/CI 检测 + `qwen review fetch-pr/pr-context/load-rules/deterministic/presubmit/cleanup` 子命令） / [Roadmap#742](https://github.com/QwenLM/qwen-code/issues/742) |
| **P1** | [HTTP Hooks](./http-hooks-deep-dive.md) — Hook 可 POST JSON 到 URL 并接收响应（不仅 shell 命令）[↓](./qwen-code-improvement-report-p0-p1-platform.md#item-3) | ✓ 已实现（hook `type:'http'` POST JSON + `HttpHookRunner` + `allowedHttpUrls` + env 插值；另支持 function/prompt 类型）| 小 | [PR#2827](https://github.com/QwenLM/qwen-code/pull/2827) ✓（2026-04-16） |
| **P1** | [Structured Output](./structured-output-deep-dive.md) — headless 模式 `--json-schema '<json>'` / `--json-schema @path` 注册 synthetic `structured_output` 工具 + Ajv parse-time 验证；model 首次成功调用即终结 session 并返回 `result` (text) + `structured_result` (json) [↓](./qwen-code-improvement-report-p0-p1-platform.md#item-4) | **✅ 已合并** [PR#3598](https://github.com/QwenLM/qwen-code/pull/3598) MERGED 2026-05-11 +2619/-752（PR#4001 +1543/-283 替代方案 CLOSED 2026-05-11；[PR#4051](https://github.com/QwenLM/qwen-code/pull/4051) ✓ docs 2026-05-17 MERGED）| 小 | ✓ |
| **P1** | [Agent SDK 增强](./agent-sdk-python-deep-dive.md) — Python SDK + 流式回调 + 工具审批回调（Qwen 现有 TS + Python + Java SDK）[↓](./qwen-code-improvement-report-p0-p1-platform.md#item-5) | ✓ Python SDK 已合并；另有 Java SDK（`packages/sdk-java`）（流式/审批回调仍待验证） | 中 | [PR#3494](https://github.com/QwenLM/qwen-code/pull/3494) ✓（2026-04-24 23:02 UTC 合并 · `packages/sdk-python` · async `query` + sync `query_sync` + process transport + control/permission · 4676 行新增 · 追踪 #3010） |
| **P1** | [Bare Mode](./bare-mode-deep-dive.md) — `--bare` 跳过所有自动发现，CI/脚本最快启动 [↓](./qwen-code-improvement-report-p0-p1-platform.md#item-6) | 缺失 | 小 | — |
| **P1** | [Remote Control Bridge](./remote-control-bridge-deep-dive.md) — 从手机/浏览器驱动本地终端 session [↓](./qwen-code-improvement-report-p0-p1-platform.md#item-7) | Channels 平台已合并（IM 路径），Web/QR 路径 review 中 | 大 | [PR#2628](https://github.com/QwenLM/qwen-code/pull/2628) ✓（Telegram/WeChat/DingTalk） / [PR#2330](https://github.com/QwenLM/qwen-code/pull/2330)（Web UI + QR code） |
| **P1** | [/teleport 跨端双向迁移](./teleport-session-migration-deep-dive.md) — Web session → 终端 session 双向迁移 [↓](./qwen-code-improvement-report-p0-p1-platform.md#item-8) | 缺失 | 大 | — |
| **P1** | [GitLab CI/CD](./gitlab-ci-cd-deep-dive.md) — 官方 GitLab pipeline 集成 [↓](./qwen-code-improvement-report-p0-p1-platform.md#item-9) | 缺失 | 中 | — |
| **P1** | [流式工具执行流水线](./streaming-tool-execution-deep-dive.md) — API 流式返回 tool_use 时立即开始执行，不等完整响应 [↓](./qwen-code-improvement-report-p0-p1-engine.md#item-1) | 等完整响应后执行（交互/agent-runtime/非交互 3 路径均 collect-then-schedule：流内只 push，stream 结束后才 `scheduleToolCalls`/`processFunctionCalls`；`streamingToolCallParser` 仅重组 OpenAI 流式 tool-call JSON delta，非流式执行器）| 中 | — |
| **P1** | [文件读取缓存 + 批量并行 I/O](./file-read-cache-deep-dive.md) — 1000 条 LRU + mtime 失效 + 32 批并行 [↓](./qwen-code-improvement-report-p0-p1-engine.md#item-2) | ✅ **prior-read 守卫链完整闭环（与 Claude Code 行为一致）**——查询缓存 ✓ + FileReadCache ✓ + 5 条 history-rewrite invalidation ✓ + prior-read 守卫 ✓ + partial-read 接受 ✓ + binary detection 统一 ✓；仅 32 批并行 `readManyFiles` 仍待 | 小 | [PR#3581](https://github.com/QwenLM/qwen-code/pull/3581) ✓（2026-04-24 · 查询缓存）/ [PR#3717](https://github.com/QwenLM/qwen-code/pull/3717) ✓（2026-04-30 · FileReadCache）/ [PR#3810](https://github.com/QwenLM/qwen-code/pull/3810) ✓（2026-05-04 · +579/-0 · 5 路径 invalidation）/ [PR#3774](https://github.com/QwenLM/qwen-code/pull/3774) ✓（2026-05-06 · +1891/-118 · `EDIT_REQUIRES_PRIOR_READ` / `FILE_CHANGED_SINCE_READ` 错误码）/ [PR#3932](https://github.com/QwenLM/qwen-code/pull/3932) ✓（2026-05-08 · Edit 接受 partial read）/ [PR#4002](https://github.com/QwenLM/qwen-code/pull/4002) ✓（**2026-05-10 · +707/-127** · 3 部分修复 close #3964 + #3945：① 解耦 cacheable 与 truncation · ② `detectFileType` 优先 mime/扩展名（`KNOWN_TEXT_EXTENSIONS` 50+ 文本扩展）防 `isBinaryFile` 4KB sample 误判 · ③ 修 WriteFile partial-read 死锁）|
| **P1** | [记忆/附件异步prefetch](./memory-prefetch-deep-dive.md) — 工具执行期间并行搜索相关记忆 [↓](./qwen-code-improvement-report-p0-p1-engine.md#item-3) | 🟡 记忆 prefetch 已实现（`MemoryPrefetchHandle` 非阻塞 auto-memory recall：UserQuery 触发即发射 → zero-wait settled poll 优先消费，未结算则下个 ToolResult 轮次消费，工具执行期并行召回）；skill write-pivot / 附件 prefetch 仍待 | 中 | [PR#4172](https://github.com/QwenLM/qwen-code/pull/4172) ✓（2026-05-19 · decouple auto-memory recall from request path · `client.ts` MemoryPrefetchHandle）+ [PR#3087](https://github.com/QwenLM/qwen-code/pull/3087) ✓（managed auto-memory 底座）|
| **P1** | [Token Budget 续行与自动交接](./token-budget-continuation-deep-dive.md) — 90% 续行 + 递减检测 + 分层压缩回退 [↓](./qwen-code-improvement-report-p0-p1-engine.md#item-4) | 🟡 三档压缩阈梯（warn/auto/hard，`chatCompressionService.ts`）；无 90% 续行 + handoff 交接 | 中 | — |
| **P1** | 同步 I/O 异步化 — readFileSync/statSync 替换为 async，解阻塞事件循环 [↓](./qwen-code-improvement-report-p0-p1-engine.md#item-5) | ✓ 已实现 | 中 | [PR#3581](https://github.com/QwenLM/qwen-code/pull/3581) ✓（2026-04-24 合并 · hot path 110→10 syscall/prompt，-91%）|
| **P1** | [Prompt Cache 分段与工具稳定排序](./prompt-cache-optimization-deep-dive.md) — static/dynamic 分界 + 内置工具前缀 + schema 锁定 [↓](./qwen-code-improvement-report-p0-p1-engine.md#item-6) | 🟡 无分段（已有 cache 稳定化 #4896）| 中 | [PR#4896](https://github.com/QwenLM/qwen-code/pull/4896) ✓（cache 稳定化）|
| **P1** | [API 指数退避与降级重试](./api-retry-fallback-deep-dive.md) — 10 次退避 + 529 模型降级 + 401 token 刷新 [↓](./qwen-code-improvement-report-p0-p1-engine.md#item-8) | 🟡 部分（429 SSE 检测 ✓；正式 classifier 进行中）| 中 | [PR#3246](https://github.com/QwenLM/qwen-code/pull/3246) ✓（SSE 流式 429 检测） / [PR#3798](https://github.com/QwenLM/qwen-code/pull/3798) ✗ CLOSED（`classifyError()` classifier 方案已关闭，未合并）|
| **P1** | [优雅关闭序列与信号处理](./graceful-shutdown-deep-dive.md) — SIGINT/SIGTERM + 清理注册 + 5s failsafe [↓](./qwen-code-improvement-report-p0-p1-engine.md#item-9) | ✅ 已实现（`cleanup.ts` 集中式 registerCleanup/runExitCleanup · 每函数 2s + 整体 5s failsafe · SIGINT/SIGTERM 挂载）| 中 | [PR#1884](https://github.com/QwenLM/qwen-code/pull/1884) ✓（ACP SIGTERM/SIGINT）+ 源码 `cleanup.ts`（`OVERALL_CLEANUP_TIMEOUT_MS=5000`）|
| **P1** | [反应式压缩](./reactive-compression-deep-dive.md) — prompt_too_long 自动裁剪最早消息 + 重试 3 次 [↓](./qwen-code-improvement-report-p0-p1-engine.md#item-10) | ✓ 已实现（context overflow 触发反应式压缩）| 中 | [PR#3879](https://github.com/QwenLM/qwen-code/pull/3879) ✓（reactive compression on context overflow）/ [PR#4526](https://github.com/QwenLM/qwen-code/pull/4526) ✓ |
| **P1** | [持久化重试模式](./persistent-retry-deep-dive.md) — CI/后台无限重试 + 5min 退避上限 + 30s 心跳 [↓](./qwen-code-improvement-report-p0-p1-engine.md#item-11) | ✅ 已实现（`retry.ts` persistentMode：无限重试 + 5min 退避上限 + 30s 心跳）| 中 | [PR#3080](https://github.com/QwenLM/qwen-code/pull/3080) ✓（2026-04-21 合并）|
| **P1** | [原子文件写入与事务回滚](./atomic-file-write-deep-dive.md) — temp+rename 原子写 + 大结果persist to disk [↓](./qwen-code-improvement-report-p0-p1-engine.md#item-12) | ✅ 已实现（`atomicWriteFile` temp+fsync+rename + EPERM 重试；已接入 Write/Edit + 凭据/memory/config/JSONL）| 中 | [PR#4096](https://github.com/QwenLM/qwen-code/pull/4096) ✓（2026-05-15 · 通用 atomicWriteFile + Write/Edit）/ [PR#4333](https://github.com/QwenLM/qwen-code/pull/4333) ✓（2026-06-02 · 凭据/memory/config/JSONL）/ [PR#4431](https://github.com/QwenLM/qwen-code/pull/4431) ✓（preserve uid）|
| **P1** | [自动检查点默认启用](./automatic-checkpoint-restore-deep-dive.md) — 每轮工具执行后自动创建文件快照 [↓](./qwen-code-improvement-report-p0-p1-engine.md#item-13) | 🟡 部分实现（`restoreCommand.ts` + `/rewind` 文件恢复 ✓；默认关闭 + picker UX 仍待）| 小 | [PR#4064](https://github.com/QwenLM/qwen-code/pull/4064) ✓（2026-05-16 · `/rewind` 文件恢复）/ [PR#3292](https://github.com/QwenLM/qwen-code/pull/3292) ✗（已关闭 · picker UX 方案未合并）|
| **P1** | [Coordinator/Swarm 多 Agent编排](./coordinator-swarm-orchestration-deep-dive.md) — Leader/Worker 团队 + 3 种执行后端 [↓](./qwen-code-improvement-report-p0-p1-engine.md#item-14) | 🟡 控制面 + UI 已合并；**Workflow 工具(P1–P5)提供确定性编排** | 大 | [PR#3433](https://github.com/QwenLM/qwen-code/pull/3433) ⚠️ revert（[PR#3468](https://github.com/QwenLM/qwen-code/pull/3468) 2026-04-20）/ [PR#3471](https://github.com/QwenLM/qwen-code/pull/3471) ✓（2026-04-27 · task_stop / send_message / per-agent transcript）/ [PR#3488](https://github.com/QwenLM/qwen-code/pull/3488) ✓（2026-04-28 · background-agent UI）/ [PR#4844](https://github.com/QwenLM/qwen-code/pull/4844) ✓（2026-06-11 · Agent Team 实验特性）/ Workflow [#4721](https://github.com/QwenLM/qwen-code/pull/4721) P1–P5 ✓（2026-06，详更新日志）|
| **P1** | [Task Management 任务协同与跨进程并发调度](./task-management-deep-dive.md) — 支持 blocks/blockedBy 的任务拓扑、跨进程安全锁与 Swarm 集成 [↓](./qwen-code-improvement-report-p0-p1-engine.md#item-25) | 🟡 控制面 + UI 已合并，依赖拓扑/跨进程锁仍待 | 大 | [PR#3471](https://github.com/QwenLM/qwen-code/pull/3471) ✓（2026-04-27 合并 · `task_stop` / `send_message` / per-agent transcript）/ [PR#3507](https://github.com/QwenLM/qwen-code/pull/3507) ✓（2026-04-26 合并 · sticky todo panel）/ [PR#3647](https://github.com/QwenLM/qwen-code/pull/3647) ✓（2026-04-29 合并 · sticky todo 紧凑化 +560/-37）|
| **P1** | [Agent 工具细粒度访问控制](./agent-tool-access-control-deep-dive.md) — 3 层allowlist/denylist + per-agent 限制 [↓](./qwen-code-improvement-report-p0-p1-engine.md#item-15) | 全部或指定列表 | 中 | [PR#3064](https://github.com/QwenLM/qwen-code/pull/3064) ✓ / [PR#3066](https://github.com/QwenLM/qwen-code/pull/3066) ✓ |
| **P1** | [InProcess 同进程多 Agent隔离](./in-process-agent-isolation-deep-dive.md) — AsyncLocalStorage 上下文隔离 [↓](./qwen-code-improvement-report-p0-p1-engine.md#item-16) | ✓ 已实现（AsyncLocalStorage 隔离：fork-subagent + Agent Team identity）| 中 | [PR#2936](https://github.com/QwenLM/qwen-code/pull/2936) ✓（fork-subagent）/ [PR#4844](https://github.com/QwenLM/qwen-code/pull/4844) ✓（2026-06-11 · team identity 隔离）|
| **P1** | [Agent 记忆持久化](./agent-memory-persistence-deep-dive.md) — user/project/local 3 级跨 session 记忆 [↓](./qwen-code-improvement-report-p0-p1-engine.md#item-17) | 🟡 部分实现（跨 session 记忆 ✓ via PR#3087；per-agent 私有记忆绑定 ✗）| 中 | [PR#3087](https://github.com/QwenLM/qwen-code/pull/3087) ✓（2026-04-16 合并 · auto-memory + auto-dream，6,015 行 30+ 文件）|
| **P1** | [Agent 恢复与续行](./agent-resume-continuation-deep-dive.md) — SendMessage 继续已完成代理 + transcript 重建 [↓](./qwen-code-improvement-report-p0-p1-engine.md#item-18) | **✓ 已实现** | 中 | [PR#3739](https://github.com/QwenLM/qwen-code/pull/3739) ✓（2026-05-01 合并 · `BackgroundAgentResumeService` + paused 生命周期 + transcript-first fork resume + `SubagentStart` hook 重放 · **+4087/-165**）|
| **P1** | 系统提示模块化组装 — sections 缓存 + dynamic boundary + uncached 标记 [↓](./qwen-code-improvement-report-p0-p1-engine.md#item-19) | 🟡 已有模块化 section 函数（`getActionsSection`/`buildSystemPromptSuffix` 等）；无 section 级缓存 + dynamic boundary 标记 | 中 | — |
| **P1** | [系统提示内容完善](./system-prompt-content-guidelines-deep-dive.md) — OWASP 安全 + prompt injection检测 + 代码风格约束 + 输出格式 [↓](./qwen-code-improvement-report-p0-p1-engine.md#item-24) | 🟡 已有 Security & Safety Rules + Conventions/代码风格 + 危险操作指导（#2889）+ 输出/语气规范；OWASP 框架 + prompt-injection 检测指引未必 | 中 | — |
| **P1** | [@include 指令与嵌套记忆发现](./nested-memory-include-deep-dive.md) — @path 递归引用 + 文件操作触发目录遍历 [↓](./qwen-code-improvement-report-p0-p1-engine.md#item-20) | **✓ 已实现**（`memoryImportProcessor` @path + `maxDepth=5` + 循环防护；`memoryDiscovery` upward scan；`ConditionalRulesRegistry` 按 `paths:` glob 匹配工具调用时注入）| — | — |
| **P1** | [附件类型协议与令牌预算](./attachment-protocol-budget-deep-dive.md) — 40+ 类型 + per-type 预算 + 3 阶段有序执行 [↓](./qwen-code-improvement-report-p0-p1-engine.md#item-21) | 字符串拼接/无预算 | 中 | — |
| **P1** | [Thinking 块跨轮保留与空闲清理](./thinking-block-retention-deep-dive.md) — 活跃保留 + 1h 空闲清理 + latch 防缓存破坏 [↓](./qwen-code-improvement-report-p0-p1-engine.md#item-22) | 每轮独立/无清理 | 中 | [PR#2897](https://github.com/QwenLM/qwen-code/pull/2897) ✓ + [PR#3590](https://github.com/QwenLM/qwen-code/pull/3590) ✓（resume + active session 保留 · GH#3579）+ [PR#3682](https://github.com/QwenLM/qwen-code/pull/3682) ✓（2026-04-28 · model switch + history load 不剥离 reasoning）+ [PR#3691](https://github.com/QwenLM/qwen-code/pull/3691) ✓（preserve description in subject-bearing thought chunks）+ [PR#3729](https://github.com/QwenLM/qwen-code/pull/3729) ✓（2026-04-29 · DeepSeek tool-call replay 注入 reasoning_content）+ [PR#3747](https://github.com/QwenLM/qwen-code/pull/3747) ✓（2026-04-29 · DeepSeek 全 assistant turn replay reasoning_content）+ [PR#3737](https://github.com/QwenLM/qwen-code/pull/3737) ✓（2026-04-30 · rewind / compression / merge 路径全保留 reasoning_content · −361 行清理）+ [PR#3788](https://github.com/QwenLM/qwen-code/pull/3788) ✓（**2026-05-02 合并 · +1407/-76** · DeepSeek anthropic-compat 端点：`normalizeAssistantThinkingSignature` 跨提供商补 `signature: ''` + `injectThinkingOnToolUseTurns` 给带 tool_use 但缺 thinking 的 assistant turn 注入空 thinking block）|
| **P1** | [输出 Token 自适应升级](./output-token-adaptive-upgrade-deep-dive.md) — 8K 默认 + max_tokens 截断时自动 64K 重试 [↓](./qwen-code-improvement-report-p0-p1-engine.md#item-23) | 固定值/不重试 | 小 | [PR#2898](https://github.com/QwenLM/qwen-code/pull/2898) ✓ |
| **P1** | QWEN.md system-reminder 注入 — 项目指令从系统提示移到用户消息 `<system-reminder>` 标签注入，避免打破 Prompt Cache [↓](./qwen-code-improvement-report-p0-p1-engine.md#item-26) | 直接拼入系统提示 | 小 | — |
| **P1** | 错误恢复分类路由 — truncation→continuation、overflow→compaction、transport→backoff 三分支 + per-category 重试预算 [↓](./qwen-code-improvement-report-p0-p1-engine.md#item-27) | 统一 catch 重试 | 中 | — |
| **P1** | [Skill 装载性能综合优化](./qwen-code-improvement-report-p0-p1-engine.md#item-28) — 9 项 Claude Code 参考：3 层 `Promise.all` 并行 + `memoize()` + `sentSkillNames` 去重 + `paths:` conditional + realpath 去重 + chokidar debounce + Bun polling workaround 等 | 3 层 for 串行 / 每轮重注 skill 列表 / 无 conditional | 中 | — |
| **P0** | [`omitClaudeMd` for read-only agents](./claude-code-agents-command-deep-dive.md#104-omitclaudemd-优化值得移植) — Explore/Plan 等 read-only agents 启用后**省 ~5-15 Gtok/周** token cost（Claude 实测）。`AgentDefinition` 加 `omitClaudeMd?: boolean` 字段，`newSessionConfig` 中跳过 CLAUDE.md 注入。可加 kill-switch（Claude 用 `tengu_slim_subagent_claudemd`）| 直接拼 CLAUDE.md 到 subagent context | 小 | — |
| **P1** | [Agent AI 自动生成（`/agents generate`）](./claude-code-agents-command-deep-dive.md#七ai-生成-agent杀手-feature) — 用户描述 "I need an agent that..." → 长 system prompt + LLM 调 `queryModelWithoutStreaming` 生成完整 agent 配置（identifier / whenToUse / systemPrompt JSON 输出）。Wizard "Generate" 分支预填后续 step | ✓ 已实现（本地 Wizard "Generate with Qwen Code" 分支 + daemon `POST /workspace/agents/generate`；`subagentGenerator` runSideQuery 生成 name/description/systemPrompt JSON）| 中 | 源码 `subagentGenerator.ts` + [PR#4249](https://github.com/QwenLM/qwen-code/pull/4249) ✓（2026-05-18 · daemon `/generate` 路由）|
| **P1** | [`criticalSystemReminder_EXPERIMENTAL` per-agent 每 turn 重注入](./claude-code-agents-command-deep-dive.md#105-criticalsystemreminderexperimental--每-turn-重注入) — agent 定义中 `criticalSystemReminder?: string` 字段会**每 user turn 重新注入** `<system-reminder>` 标签到 context——确保关键约束（如 "Always verify with tests"）不被 context 滚动遗忘。配合 Qwen 已有 system-reminder 机制（item-26）| 缺失（无 per-turn 重注入）| 小 | — |
| **P1** | [Agent `isolation: worktree` 定义字段](./claude-code-agents-command-deep-dive.md#106-isolation-worktree-与-pr4073-协调) — `AgentDefinition` 加 `isolation?: 'worktree' \| 'remote'` 字段，agent spawn 时根据该字段在独立 worktree 运行（依赖 PR#4073 Worktree* tools）| **✓ Worktree 工具已合并**（Workflow `isolation:'worktree'` 已使用）| 小 | [PR#4073](https://github.com/QwenLM/qwen-code/pull/4073) ✓（2026-05-14 合并 · EnterWorktree/ExitWorktree + Agent isolation）|
| **P1** | [Subagent 定义管理 UI（`/agents` UI Stage 1.5c daemon-side state CRUD）](./claude-code-agents-command-deep-dive.md#101-stage-15c-daemon-side-state-crud-的范本) — 远端 client 等价 Mode A 本地 `/agents` 管理能力。7 routes：`GET/POST /workspace/agents` + `:agentType` CRUD + `/generate` AI 生成。详 [daemon-design §04 §二](./qwen-code-daemon-design/04-deployment-and-client.md) + [§06 §三 Stage 1.5c](./qwen-code-daemon-design/06-roadmap.md)| ✓ 已实现（daemon serve 层 6 routes：`GET/POST /workspace/agents` + `:agentType` CRUD + `/generate` AI 生成）| 中 | [PR#4249](https://github.com/QwenLM/qwen-code/pull/4249) ✓（2026-05-18 · workspace memory + agents CRUD · `serve/workspaceAgents.ts`）|
| **P2** | [Shell 安全增强](./shell-security-deep-dive.md) — IFS 注入/Unicode 空白/Zsh 命令等 25+ 专项检查 [↓](./qwen-code-improvement-report-p2-core.md#item-1) | 🟡 LLM classifier（Auto 模式 `classifier.ts` #4151）+ `denialTracking` + shell-semantics 解析（不同路线）；IFS/Unicode/Zsh 等 25+ 专项注入检查未逐条覆盖 | 中 | [PR#4151](https://github.com/QwenLM/qwen-code/pull/4151) ✓（Auto 模式 LLM classifier）|
| **P2** | [MDM 企业策略](./mdm-enterprise-deep-dive.md) — macOS plist + Windows Registry + 远程 API 集中管控 [↓](./qwen-code-improvement-report-p2-core.md#item-2) | 无 OS 级策略 | 大 | — |
| **P2** | [API 实时 Token 计数](./token-estimation-deep-dive.md) — 每次 API 调用前精确计数，3 层回退 [↓](./qwen-code-improvement-report-p2-core.md#item-3) | ✓ 流式实时计数（streaming token consumption + `/context` breakdown 对齐实际请求）| 中 | [PR#3329](https://github.com/QwenLM/qwen-code/pull/3329) ✓（实时 token 计数）/ [PR#4512](https://github.com/QwenLM/qwen-code/pull/4512) ✓（breakdown 对齐）|
| **P2** | [Output Styles](./git-workflow-session-deep-dive.md) — Learning 模式暂停让用户写代码，Explanatory 添加教育洞察 [↓](./qwen-code-improvement-report-p2-core.md#item-4) | 缺失 | 中 | — |
| **P2** | [Fast Mode](./cost-fastmode-deep-dive.md) — 同一模型标准/快速推理切换（$5→$30/Mtok），含冷却机制 [↓](./qwen-code-improvement-report-p2-core.md#item-5) | ⚠️ 部分实现（`fastModel` 走不同方案——另一个更快模型，非同模型速度分级） | 小 | [PR#3077](https://github.com/QwenLM/qwen-code/pull/3077) ✓ / [PR#3086](https://github.com/QwenLM/qwen-code/pull/3086) ✓ / [PR#3120](https://github.com/QwenLM/qwen-code/pull/3120) ✓ |
| **P2** | [并发 Session](./cost-fastmode-deep-dive.md) — 多终端 PID 追踪 + 后台 Agent 脱附/重附 [↓](./qwen-code-improvement-report-p2-core.md#item-8) | 🟡 部分（managed 后台 shell 池 + `/tasks` 脱附/重附；多终端 PID 追踪未必）| 中 | [PR#3642](https://github.com/QwenLM/qwen-code/pull/3642) ✓（后台 shell 池 + /tasks）|
| **P2** | [Git Diff 统计](./git-workflow-session-deep-dive.md) — 编辑后 numstat + hunks 结构化 diff（50 文件/1MB 上限） [↓](./qwen-code-improvement-report-p2-core.md#item-9) | ✓ 已实现（`/diff` 命令 + git diff 统计工具 · `diffCommand.ts`）| 小 | [PR#3491](https://github.com/QwenLM/qwen-code/pull/3491) ✓ |
| **P2** | [文件历史快照](./git-workflow-session-deep-dive.md) — per-file SHA256 备份，按消息粒度恢复（100 个/session） [↓](./qwen-code-improvement-report-p2-core.md#item-10) | ✓ 已实现（`fileHistoryService` per-file 快照 + 跨会话 `/rewind` 恢复）| 中 | [PR#4897](https://github.com/QwenLM/qwen-code/pull/4897) ✓（cross-session 文件历史快照）|
| **P2** | [Computer Use](./computer-use-deep-dive.md) — macOS 截图 + 鼠标/键盘 + 剪贴板，通过 MCP 桥接 [↓](./qwen-code-improvement-report-p2-core.md#item-6) | **✅ 已实现且超 Claude（跨平台 vs Claude macOS-only）**——`open-computer-use` MCP 零配置内建 + cua-driver 跨平台 + 35 工具面（`tools/computer-use/`，含签名公证 fork）| 大 | [PR#4590](https://github.com/QwenLM/qwen-code/pull/4590) ✓（2026-05-29 · 零配置内建）/ [PR#4726](https://github.com/QwenLM/qwen-code/pull/4726) ✓（2026-06-03 · signed+notarized fork）/ [PR#5051](https://github.com/QwenLM/qwen-code/pull/5051) ✓（2026-06-14 · cua-driver 跨平台）/ [PR#5122](https://github.com/QwenLM/qwen-code/pull/5122) ✓（截图尺寸可配）⚠️ Claude Code 侧默认禁用（`tengu_malort_pedway` gate）|
| **P2** | [Deep Link](./deep-link-protocol-deep-dive.md) — `claude-cli://` 一键从浏览器/IDE 启动 Agent + 预填充 prompt [↓](./qwen-code-improvement-report-p2-core.md#item-11) | 🟡 desktop app 有 `craftagents://` deep link（auth-complete + `deeplink:navigate` 内部路由，`server-core/.../system.ts`）；CLI browser/IDE 一键启动+prefill 未实现 | 中 | desktop `craftagents://` ⚠️ **Claude Code 侧默认禁用（`tengu_lodestone_enabled` gate）** |
| **P2** | [`/context` 非交互输出](./context-usage-noninteractive-deep-dive.md) — 将上下文诊断暴露给脚本、CI 与外部控制器 [↓](./qwen-code-improvement-report-p2-tools-ui.md#item-20) | 仅交互式 | 小 | [PR#2916](https://github.com/QwenLM/qwen-code/pull/2916) ✓（2026-04-14 · 删除张冠李戴的 #3042 引用）|
| **P3** | 大粘贴内容自动存到工作区文件 — 粘贴 >30KB 内容自动外化到 tmp 文件 + 输入框显示引用（Copilot CLI v0.0.397 参考） | 直接进 prompt | 小 | — |
| **P1** | [Team Memory](./team-memory-deep-dive.md) — 团队共享项目知识 + 29 条 gitleaks 密钥扫描 + ETag 同步 [↓](./qwen-code-improvement-report-p0-p1-core.md#item-10) | 缺失 | 大 | — |
| **P2** | [Plan 模式 Interview](./plan-mode-interview-deep-dive.md) — 先澄清需求再形成计划，分离访谈/规划/执行阶段 [↓](./qwen-code-improvement-report-p2-core.md#item-12) | 无 interview 阶段 | 中 | — |
| **P2** | [BriefTool 异步用户消息](./brieftool-async-user-messages-deep-dive.md) — Agent 主动发消息/附件给用户，不阻塞当前工具执行 [↓](./qwen-code-improvement-report-p2-core.md#item-13) | 缺失 | 中 | — |
| **P2** | [SendMessageTool](./multi-agent-deep-dive.md) — 多 Agent间消息传递、shutdown 请求、plan 审批 [↓](./qwen-code-improvement-report-p2-core.md#item-14) | ✓ 已实现（`tools/send-message.ts`：teammate 单播 + `*` 广播 + `shutdown_request` + plan_approval）| 中 | [PR#3471](https://github.com/QwenLM/qwen-code/pull/3471) ✓（send-message.ts）|
| **P2** | [FileIndex 模糊文件搜索](./file-index-fuzzy-search-deep-dive.md) — fzf 风格模糊文件搜索 + 异步增量索引 [↓](./qwen-code-improvement-report-p2-core.md#item-15) | ✓ 已实现（fzf AsyncFzf + worker-thread 索引 + git ls-files/rg 文件枚举 + mtime 增量）| 中 | [PR#3214](https://github.com/QwenLM/qwen-code/pull/3214) ✓（2026-05-12 · git ls-files + rg 回退）+ [PR#4621](https://github.com/QwenLM/qwen-code/pull/4621) ✓（AsyncFzf 移入 worker thread）|
| **P2** | [Notebook Edit 原子级编辑](./notebook-edit-deep-dive.md) — Jupyter cell 编辑 + 自动 cell ID 追踪 + 文件历史快照 [↓](./qwen-code-improvement-report-p2-core.md#item-16) | **✓ 已实现**（`notebook_edit` 工具）| 中 | [PR#3900](https://github.com/QwenLM/qwen-code/pull/3900) ✓（2026-05-21 合并 · NotebookEdit tool · `ed14a3306`）+ [PR#4373](https://github.com/QwenLM/qwen-code/pull/4373) ✓（tab 缩进保留）|
| **P2** | 自定义快捷键 — multi-chord 组合键 + 跨平台适配 + `keybindings.json` 自定义 [↓](./qwen-code-improvement-report-p2-core.md#item-17) | 🟡 部分（内部 `keyBindings.ts` 集中键位定义 + 新增键位如 Ctrl+B；无用户级 `keybindings.json` 自定义 + multi-chord 配置）| 中 | [PR#3969](https://github.com/QwenLM/qwen-code/pull/3969) ✓（keybind 系列）|
| **P2** | [Session Ingress Auth](./session-ingress-auth-deep-dive.md) — 远程会话 bearer token 认证（企业多用户环境） [↓](./qwen-code-improvement-report-p2-core.md#item-18) | 缺失 | 中 | — |
| **P2** | [企业代理](./enterprise-proxy-support-deep-dive.md) — CONNECT relay + CA cert 注入 + NO_PROXY allowlist（容器环境） [↓](./qwen-code-improvement-report-p2-core.md#item-19) | 缺失 | 大 | — |
| **P2** | [终端主题检测](./terminal-theme-detection-deep-dive.md) — OSC 11 查询 dark/light + COLORFGBG 环境变量回退 [↓](./qwen-code-improvement-report-p2-core.md#item-20) | **✓ 已实现** | 小 | [PR#3460](https://github.com/QwenLM/qwen-code/pull/3460) ✓（2026-04-22 合并，`'auto'` 或未设置 theme 时自动检测）|
| **P2** | Denial Tracking — 连续权限拒绝自动回退到手动确认模式，防止静默阻塞 [↓](./qwen-code-improvement-report-p2-core.md#item-7) | ✓ 已实现（`permissions/denialTracking.ts` + AUTO 模式拒绝可观测性与上限）| 小 | [PR#4476](https://github.com/QwenLM/qwen-code/pull/4476) ✓（AUTO mode denial observability + caps）|
| **P2** | [队列输入编辑](./input-queue-deep-dive.md) — 排队中的指令可通过方向键弹出到输入框重新编辑 [↓](./qwen-code-improvement-report-p2-core.md#item-21) | **✓ 已实现** | 小 | [PR#2871](https://github.com/QwenLM/qwen-code/pull/2871) ✓（2026-04-11 · ↑/ESC 弹出队列消息编辑）|
| **P2** | [状态栏紧凑布局](./compact-status-bar-deep-dive.md) — 固定高度不伸缩，最大化终端内容区域 [↓](./qwen-code-improvement-report-p2-core.md#item-22) | Footer 占用偏高 | 小 | — |
| **P2** | [会话标签与搜索](./session-tags-search-deep-dive.md) — /tag 命令打标签 + 按标签/仓库/标题搜索历史会话 [↓](./qwen-code-improvement-report-p2-core.md#item-23) | 仅按时间排序 | 小 | — |
| **P2** | Plan 状态机化 + Hint 注入 — 4 状态 subtask + 每轮 hint 注入（AgentScope 参考） [↓](./qwen-code-improvement-report-p2-core.md#item-24) | `/plan` 是一次性文档 | 中 | — |
| **P2** | A2A 协议集成 — 跨 agent 通信 + AgentCard + 服务发现（AgentScope 参考） [↓](./qwen-code-improvement-report-p2-core.md#item-25) | 仅 MCP Client | 大 | — |
| **P2** | OTel 原生 Tracing — 5 类 span extractor（Agent/LLM/Tool/Formatter/Embedding，AgentScope 参考） [↓](./qwen-code-improvement-report-p2-core.md#item-26) | 🟡 OTel SDK 已集成（@opentelemetry/sdk-node + 6 exporters traces/logs/metrics × http/grpc）+ HTTP OTLP routing 已落地（PR#3779），AgentScope 风格 5 类 span extractor 自动埋点仍缺 | 中 | [PR#3779](https://github.com/QwenLM/qwen-code/pull/3779) ✓（**2026-05-01 合并 · +1387/-102** · `resolveHttpOtlpUrl()` `/v1/traces` `/v1/logs` `/v1/metrics` 自动追加 + per-signal endpoint overrides + `LogToSpanProcessor` 桥接 logs→spans 给 traces-only 后端如阿里云）|
| **P2** | Conditional Hooks — Hook `if` 字段用权限规则语法按工具/路径过滤 [↓](./qwen-code-improvement-report-p2-tools-commands.md#item-1) | 🟡 hook `matcher` 按工具/路径过滤已有；`if` + 权限规则语法精确条件未必 | 小 | — |
| **P2** | [Transcript Search 会话记录搜索](./transcript-search-navigation-deep-dive.md) — 按 `/` 搜索会话记录，`n`/`N` 导航匹配项 [↓](./qwen-code-improvement-report-p2-tools-commands.md#item-2) | 缺失 | 小 | — |
| **P2** | [Bash File Watcher](./file-watcher-stale-edit-deep-dive.md) — 检测 formatter/linter 修改已读文件，防止 stale-edit [↓](./qwen-code-improvement-report-p2-tools-commands.md#item-3) | 缺失 | 小 | — |
| **P2** | [/batch 并行操作](./batch-parallel-execution-deep-dive.md) — 编排大规模并行变更（多文件/多任务）[↓](./qwen-code-improvement-report-p2-tools-commands.md#item-4) | **✓ 已实现**（`/batch` skill）| 中 | [PR#3079](https://github.com/QwenLM/qwen-code/pull/3079) ✓（2026-04-17）|
| **P2** | PDF / 二进制文件读取 — read_file 内置 PDF + 图片 + Notebook 支持 [↓](./qwen-code-improvement-report-p2-tools-commands.md#item-21) | ✓ PDF + 图片(PNG/JPG/GIF/WEBP/SVG/BMP) + Notebook 已实现（图片走 inlineData base64，`fileUtils.ts`）；DOCX/XLSX 仍缺 | 中 | [PR#3160](https://github.com/QwenLM/qwen-code/pull/3160) ✓（2026-04-20 · PDF 文本提取 + Notebook）|
| **P2** | Skill 级模型覆盖 — SKILL.md frontmatter `model:` 字段，按阶段切换模型 [↓](./qwen-code-improvement-report-p2-tools-commands.md#item-22) | ✓ 已实现（SKILL.md frontmatter `model:` 字段 · `skill-load.ts` parseModelField + `types.ts` model?:string）| 小 | [PR#2949](https://github.com/QwenLM/qwen-code/pull/2949) ✓（2026-04-13） |
| **P2** | PreCompact Hook — 压缩前钩子，支持 block/modify/continue（Claude Code v2.1.105 新增） [↓](./qwen-code-improvement-report-p2-tools-commands.md#item-23) | ✓ 已实现（`hookSystem.firePreCompactEvent` + `HookEventName.PreCompact` + PreCompactTrigger）| 小 | [PR#4688](https://github.com/QwenLM/qwen-code/pull/4688) ✓（PreCompact hook plumb）|
| **P2** | 模型通过 Skill 工具调用内置 Slash 命令 — Agent 自主调用 `/init` / `/review` / `/security-review`（v2.1.108 新增） [↓](./qwen-code-improvement-report-p2-tools-commands.md#item-24) | 用户手动触发 | 中 | — |
| **P3** | Statusline Refresh Interval — 按秒级间隔重跑 statusline 脚本（v2.1.97 新增） [↓](./qwen-code-improvement-report-p2-tools-commands.md#item-25) | 仅状态变化时刷新 | 小 | [PR#3383](https://github.com/QwenLM/qwen-code/pull/3383) ✓（2026-04-19 合并） |
| **P2** | `/experimental` 实验特性统一门控 — 统一注册表 + `/experimental list` + `--experimental <id>` flag（Copilot CLI v0.0.396 参考） [↓](./qwen-code-improvement-report-p2-tools-commands.md#item-26) | 实验特性分散在 env var / settings / 命令参数 | 中 | — |
| **P2** | Chrome Extension — 调试 live web 应用（读 DOM/Console/Network）[↓](./qwen-code-improvement-report-p2-tools-commands.md#item-5) | 缺失 | 中 | — |
| **P2** | [MCP Auto-Reconnect](./mcp-auto-reconnect-deep-dive.md) — 连续 3 次错误自动重连 + SSE 断线恢复 [↓](./qwen-code-improvement-report-p2-tools-commands.md#item-13) | 🟡 部分（reconnect-on-error 已有：`mcp-tool.ts:attemptReconnect()` / `handleReconnectOnError()` + `MAX_RECONNECT_RETRIES`；30s 周期健康检查已核实：`mcp-client-manager.ts` checkIntervalMs=30000 + healthCheckTimers，默认开启；UI 健康 pill ✓ via PR#3741）| 小 | [PR#3741](https://github.com/QwenLM/qwen-code/pull/3741) ✓（**2026-05-02 合并** · footer 健康 pill 显示 DISCONNECTED 状态 +182/-0）|
| **P2** | Tool Result 大小限制 — 超限结果持久化到磁盘，发文件路径给模型 [↓](./qwen-code-improvement-report-p2-tools-commands.md#item-14) | ✓ 已实现 — 分层工具输出截断 + per-message/per-tool 预算已覆盖所有工具（`coreToolScheduler` 调度层调 `truncateToolOutput` + 全局阈值，默认 ~25K chars 写临时文件 + head/tail 预览 + 文件路径 hint，源码 `utils/truncation.ts`）；原 [PR#2814](https://github.com/QwenLM/qwen-code/pull/2814) ✗ CLOSED，功能经 [PR#4880](https://github.com/QwenLM/qwen-code/pull/4880) 落地 | 小 | [PR#4880](https://github.com/QwenLM/qwen-code/pull/4880) ✓ |
| | ↳ 参考：[RTK](https://github.com/rtk-ai/rtk)——在命令输出端过滤压缩（58 个 TOML 规则，-80% token），30 分钟会话节省 118K→24K token | | | |
| **P2** | Output Token 升级重试 — 首次 8K 截断后自动 64K 重试 [↓](./qwen-code-improvement-report-p2-tools-commands.md#item-15) ⚠️ **与 P1 item-23 重复**（同一概念 line 93）| **✅ 已合并** [PR#2898](https://github.com/QwenLM/qwen-code/pull/2898) MERGED 2026-04-08 +299/-57（与 line 93 P1 同一项）| 小 | ✓ |
| **P2** | [Ripgrep 三级回退](./ripgrep-fallback-deep-dive.md) — System→Embedded→Builtin + EAGAIN 单线程重试 [↓](./qwen-code-improvement-report-p2-tools-commands.md#item-16) | 缺失 | 小 | — |
| **P2** | MAGIC DOC 自更新文档 — 空闲时 Agent 自动更新标记文件的内容 [↓](./qwen-code-improvement-report-p2-tools-commands.md#item-17) | 缺失 | 中 | — |
| **P2** | 目录/文件路径补全 — 输入路径时 Tab 补全 + LRU 缓存 [↓](./qwen-code-improvement-report-p2-tools-commands.md#item-18) | ✓ 已实现（目录/文件 Tab 补全）| 小 | [PR#4092](https://github.com/QwenLM/qwen-code/pull/4092) ✓（directory completions）+ [PR#4288](https://github.com/QwenLM/qwen-code/pull/4288) ✓ |
| **P2** | [上下文 Tips 系统](./context-tips-system-deep-dive.md) — 根据配置/IDE/插件状态显示上下文相关提示 [↓](./qwen-code-improvement-report-p2-tools-commands.md#item-19) | **✓ 已实现** | 小 | [PR#2904](https://github.com/QwenLM/qwen-code/pull/2904) ✓（2026-04-13）|
| **P2** | [权限对话框文件预览](./permission-dialog-file-preview-deep-dive.md) — 审批时展示文件内容 + 语法高亮 + 上下文说明 [↓](./qwen-code-improvement-report-p2-tools-commands.md#item-20) | 缺失 | 中 | — |
| **P2** | Token 使用实时警告 — 显示 token 用量 + 压缩进度 + 错误计数 [↓](./qwen-code-improvement-report-p2-tools-ui.md#item-1) | 仅基础显示 | 小 | — |
| **P2** | 快捷键提示组件 — UI 全局统一显示当前操作的键盘快捷方式 [↓](./qwen-code-improvement-report-p2-tools-ui.md#item-2) | 缺失 | 小 | — |
| **P2** | 终端完成通知 — 后台任务完成时 iTerm2/Kitty/Ghostty OSC 通知 + 进度百分比 [↓](./qwen-code-improvement-report-p2-tools-ui.md#item-3) | ✓ 已实现（iTerm2/Kitty/Ghostty OSC 通知 + terminal sequence notifications + 后台 shell 完成通知）| 小 | [PR#3562](https://github.com/QwenLM/qwen-code/pull/3562) ✓（OSC 通知）/ [PR#4895](https://github.com/QwenLM/qwen-code/pull/4895) ✓（terminal sequence）/ [PR#4355](https://github.com/QwenLM/qwen-code/pull/4355) ✓（后台 shell 完成）|
| **P2** | Spinner 工具名 + 计时 — 显示"正在执行 Bash(npm test) · 15s"而非通用 spinner [↓](./qwen-code-improvement-report-p2-tools-ui.md#item-4) | 通用 Responding | 小 | — |
| **P2** | /rewind 检查点回退 — 会话内代码 + 对话恢复到之前的检查点 [↓](./qwen-code-improvement-report-p2-tools-ui.md#item-5) | ✓ 已实现 | 中 | [PR#3441](https://github.com/QwenLM/qwen-code/pull/3441) ✓（2026-04-25 合并 · double-ESC + /rewind · +1533/-6）|
| **P2** | /copy OSC 52 剪贴板 — 复制代码块到剪贴板，OSC 52 + temp 文件回退 [↓](./qwen-code-improvement-report-p2-tools-ui.md#item-6) | ✓ 已实现（`/copy` + `/copy N` 复制第 N 条 AI 消息）| 小 | [PR#4761](https://github.com/QwenLM/qwen-code/pull/4761) ✓（/copy N）/ [PR#5110](https://github.com/QwenLM/qwen-code/pull/5110) ✓ |
| **P2** | 首次运行引导向导 — 主题/认证/API Key/安全/终端设置多步引导 [↓](./qwen-code-improvement-report-p2-tools-ui.md#item-7) | 缺失 | 中 | — |
| **P2** | /doctor 诊断工具 — 系统环境检查（git/node/shell/权限/代理）[↓](./qwen-code-improvement-report-p2-tools-ui.md#item-8) | **✓ 已实现 + 持续扩展**（`/doctor` 基础诊断 + `/doctor memory` 内存子命令已合并）| 小 | [PR#3404](https://github.com/QwenLM/qwen-code/pull/3404) ✓（2026-04-19 合并 · 基础 `/doctor` 命令）/ [PR#3785](https://github.com/QwenLM/qwen-code/pull/3785) ✓（2026-05-17 合并 · `/doctor memory` + `--json` + `collectMemoryDiagnostics()` · #3000 系列首层）|
| **P2** | 结构化 Diff 渲染 — Rust NAPI 快速着色 + 行号 gutter + 语法高亮 [↓](./qwen-code-improvement-report-p2-tools-ui.md#item-9) | 基础 inline diff | 中 | — |
| **P2** | Slash Command 命名空间治理 — source namespace + reserved names + 来源透明 [↓](./qwen-code-improvement-report-p2-tools-ui.md#item-10) | 后者覆盖前者 | 中 | — |
| **P2** | /plan 计划模式 — Agent 只分析不动手 + 用户确认后执行 [↓](./qwen-code-improvement-report-p2-tools-ui.md#item-11) | 无计划模式 | 小 | [PR#2921](https://github.com/QwenLM/qwen-code/pull/2921) ✓ / [PR#3008](https://github.com/QwenLM/qwen-code/pull/3008) ✓ |
| **P2** | /rename 重命名会话 — 手动修改会话标题 [↓](./qwen-code-improvement-report-p2-tools-ui.md#item-12) | ✓ 已实现（`/rename` + `/rename --auto` 重新生成标题）| 小 | [PR#3540](https://github.com/QwenLM/qwen-code/pull/3540) ✓（/rename --auto）/ [PR#4048](https://github.com/QwenLM/qwen-code/pull/4048) ✓（argument hint）|
| **P2** | /upgrade 版本升级 — changelog 展示 + 一键更新 [↓](./qwen-code-improvement-report-p2-tools-ui.md#item-13) | 手动 npm update | 小 | — |
| **P2** | Plugin 系统增强 — 聚合容器（commands+skills+hooks+MCP）+ 一键安装/卸载 [↓](./qwen-code-improvement-report-p2-tools-ui.md#item-14) | extension 分散管理 | 中 | — |
| **P2** | 文件编辑引号风格保留 — preserveQuoteStyle() 检测并保持原文件引号风格 [↓](./qwen-code-improvement-report-p2-tools-ui.md#item-15) | 直接替换不保留 | 小 | — |
| **P2** | 文件编辑等价性判断 — areFileEditsInputsEquivalent() 跳过重复编辑 [↓](./qwen-code-improvement-report-p2-tools-ui.md#item-16) | 重复编辑也执行 | 小 | — |
| **P2** | MCP 通道权限管理 — channel plugin allowlist + GrowthBook gate [↓](./qwen-code-improvement-report-p2-tools-ui.md#item-17) | 无 plugin allowlist | 小 | — |
| **P2** | 消息类型丰富化 — 11 种 → 30+ 种 SDK 消息类型 [↓](./qwen-code-improvement-report-p2-tools-ui.md#item-18) | ~11 种 | 中 | — |
| **P2** | /clear 多模式增强 — 清屏/清对话/完全重置三种力度 [↓](./qwen-code-improvement-report-p2-tools-ui.md#item-19) | 仅清屏 | 小 | [PR#2915](https://github.com/QwenLM/qwen-code/pull/2915) / [Roadmap#2487](https://github.com/QwenLM/qwen-code/issues/2487) |
| **P2** | /effort — 设置模型 effort 级别（○ 低 / ◐ 中 / ● 高）[↓](./qwen-code-improvement-report-p2-tools-commands.md#item-6) | 🟡 reasoning_effort API 已支持（含 'max' tier）；用户面 `/effort` 命令未实现 | 小 | [PR#3800](https://github.com/QwenLM/qwen-code/pull/3800) ✓（reasoning effort 'max'）/ [Roadmap#2876](https://github.com/QwenLM/qwen-code/issues/2876) |
| **P2** | Status Line 自定义 — shell 脚本在状态栏展示自定义信息 [↓](./qwen-code-improvement-report-p2-tools-commands.md#item-7) | **✓ 已实现**（custom statusline script + stdin payload，settings `statusLine`）| 小 | [PR#2923](https://github.com/QwenLM/qwen-code/pull/2923) ✓（2026-04-09 合并）/ [Roadmap#2418](https://github.com/QwenLM/qwen-code/issues/2418) |
| **P2** | Query TransitionReason 枚举 — 6 种查询转换原因显式标记（tool_result/max_tokens/compaction/retry/stop_hook/budget） [↓](./qwen-code-improvement-report-p2-stability.md#item-36) | 隐式 if-else | 小 | — |
| **P2** | 工具并发安全分类 — 每个工具标记 `concurrencySafe`，并发分区后批量执行 [↓](./qwen-code-improvement-report-p2-stability.md#item-37) | **✅ 已合并** [PR#2864](https://github.com/QwenLM/qwen-code/pull/2864) `feat(core): intelligent tool parallelism with Kind-based batching and shell read-only detection` MERGED 2026-04-13 | 中 | ✓ |
| **P2** | 工具执行进度消息 — 长时间工具（>3s）发射进度事件 + elapsed time + shell stats bar + OSC 9;4 标签进度 [↓](./qwen-code-improvement-report-p2-stability.md#item-38) | 🟡 部分实现（墙钟/字节 ✓ / 语义 progress events 未覆盖）| 小 | [PR#3155](https://github.com/QwenLM/qwen-code/pull/3155) ✓（2026-04-20 合并，视觉反馈部分）|
| **P2** | 运行时任务模型 — 区分 work-graph task（持久目标）vs runtime task（执行槽），防止状态混淆 [↓](./qwen-code-improvement-report-p2-stability.md#item-39) | 仅 TodoWriteTool | 中 | — |
| **P2** | 后台通知 drain-before-call — LLM 调用前排空后台任务通知队列，确保模型看到最新结果 [↓](./qwen-code-improvement-report-p2-stability.md#item-40) | 无通知排空 | 小 | — |
| **P2** | 压缩后身份重注入 — 上下文压缩后 messages<3 条时注入 Agent 身份块，防止 Agent "忘记自己是谁" [↓](./qwen-code-improvement-report-p2-stability.md#item-41) | 无身份重注入 | 小 | — |
| **P2** | 子进程 PID 命名空间沙箱 + 脚本次数限制 — Linux PID namespace + env scrub + SCRIPT_CAPS（v2.1.98 新增） [↓](./qwen-code-improvement-report-p2-stability.md#item-42) | 无 PID 隔离 | 中 | — |
| **P2** | 会话 Recap（返回时上下文摘要）— `/recap` 命令 + 自动展示（v2.1.108/v2.1.110 新增）[↓](./qwen-code-improvement-report-p2-stability.md#item-43) | **已实现**（/recap + auto-show） | 小 | [PR#3434](https://github.com/QwenLM/qwen-code/pull/3434) ✓（2026-04-19 合并） |
| **P2** | [瞬态消息单行容器 + 离屏历史冻结](./task-display-height-deep-dive.md) — MessageResponse `height=1 overflowY=hidden` + OffscreenFreeze 引用缓存避免历史 spinner 拖累 [↓](./qwen-code-improvement-report-p2-stability.md#item-44) | 🟡 部分覆盖（pre-slice + visual-height slicing + SubAgent 视觉高度 bounding 已合并；MessageResponse 严格容器仍待）| 中 | [PR#3591](https://github.com/QwenLM/qwen-code/pull/3591) ✓ partial（2026-04-25）+ [PR#3721](https://github.com/QwenLM/qwen-code/pull/3721) ✓（2026-04-29 合并 · SubAgent 显示按视觉高度 bound 防 flicker · +1336/-57）|
| **P2** | [三级输出截断](./task-display-height-deep-dive.md) — Bash 30K/150K + 单工具 50K + 单消息 200K 批量预算 + env var `BASH_MAX_OUTPUT_LENGTH` [↓](./qwen-code-improvement-report-p2-stability.md#item-45) | 🟡 部分覆盖（通用预切片已合并；三级数字预算仍待）| 小 | [PR#3591](https://github.com/QwenLM/qwen-code/pull/3591) ✓ partial（2026-04-25）|
| **P2** | [Bash 执行中 "5 行窗口 + +N lines 计数"](./bash-task-display-deep-dive.md) — ShellProgressMessage `lines.slice(-5)` + `+${extraLines} lines` 计数 [↓](./qwen-code-improvement-report-p2-stability.md#item-46) | **✓ 已完整实现**（超越 Claude 原设计 · 可配置 + 6 bypasses + 语义化 tool success ≠ exit code）| 小 | [PR#3155](https://github.com/QwenLM/qwen-code/pull/3155) ✓（`+N lines`，2026-04-20）+ [PR#3508](https://github.com/QwenLM/qwen-code/pull/3508) ✓（5 行窗口 + 6 bypasses + settings，2026-04-22）|
| **P2** | [ShellTimeDisplay 时间 + timeout 倒计时](./bash-task-display-deep-dive.md) — `(10.5s · timeout 30s)` 三种格式 + dim color [↓](./qwen-code-improvement-report-p2-stability.md#item-47) | **✓ 已完整实现**（5/5 对齐 Claude + 1 处 Qwen 优势）| 小 | [PR#3155](https://github.com/QwenLM/qwen-code/pull/3155) ✓ + [PR#3512](https://github.com/QwenLM/qwen-code/pull/3512) ✓（2026-04-23 合并，补齐组合格式 + 亚秒精度 + 条件阈值）|
| **P2** | [语义化 hunk 模型（消除双重 diff 序列化）](./update-tool-display-deep-dive.md) — `structuredPatch` 替代 `createPatch` 字符串 + 删除 UI 层 62 行 regex re-parse [↓](./qwen-code-improvement-report-p2-stability.md#item-48) | core createPatch 字符串 → UI regex 反解析（双序列化浪费）| 中 | — |
| **P2** | [多 hunk `...` 省略分隔符](./update-tool-display-deep-dive.md) — StructuredDiffList 在 hunk 之间插入 dim color `...` [↓](./qwen-code-improvement-report-p2-stability.md#item-49) | 多 hunk 直接堆叠无分隔 | 小 | — |
| **P2** | [会话标题自动生成 Fast Model](./fast-model-usage-deep-dive.md) — Haiku 3-7 词 sentence-case title + tail-1000 字符 + JSON schema [↓](./qwen-code-improvement-report-p2-stability.md#item-50) | **✓ 已完整实现**（fastModel + sentence-case + 自动触发 + `titleSource` 元数据 + cross-process race 保护）| 小 | [PR#3093](https://github.com/QwenLM/qwen-code/pull/3093) ✓ + [PR#3540](https://github.com/QwenLM/qwen-code/pull/3540) ✓（2026-04-23 合并，补齐 fastModel + sentence-case + 自动触发）|
| **P2** | [工具调用摘要 Compact Mode Fast Model](./fast-model-usage-deep-dive.md) — Haiku 30 字符 git-commit-subject 风格 label 折叠 N 个工具 [↓](./qwen-code-improvement-report-p2-stability.md#item-51) | ✓ 已实现（fastModel + ~30 字符 git-commit-subject label 折叠 N 个工具）| 小 | [PR#3538](https://github.com/QwenLM/qwen-code/pull/3538) ✓（2026-04-27 · `toolUseSummary.ts`）|
| **P2** | [Hook LLM 条件评估 Fast Model](./fast-model-usage-deep-dive.md) — `if.condition: "自然语言"` + Haiku JSON `{ok, reason}` [↓](./qwen-code-improvement-report-p2-stability.md#item-52) | 仅代码条件 | 中 | — |
| **P2** | [WebFetch 内容 LLM 清洗 Fast Model](./fast-model-usage-deep-dive.md) — Haiku 抽取核心内容 + 去 nav/ads/tracker [↓](./qwen-code-improvement-report-p2-stability.md#item-53) | ⚠️ 已否决（`web-fetch.ts` 刻意 pin 主模型：fast model 损失保真度，不路由 fastModel）| 小 | [PR#3537](https://github.com/QwenLM/qwen-code/pull/3537) ✗ CLOSED（web-fetch fastModel 路由方案被否决）|
| **P2** | [Shell 命令前缀 LLM 提取（权限）Fast Model](./fast-model-usage-deep-dive.md) — Haiku + policySpec 精确分类复合命令/alias/subshell [↓](./qwen-code-improvement-report-p2-stability.md#item-54) | Regex 分类（边界有漏洞）| 中 | — |
| **P2** | [Skill 改进建议 Post-Sampling Hook Fast Model](./fast-model-usage-deep-dive.md) — Haiku 分析刚完成 turn，建议 skill 修订（opt-in）[↓](./qwen-code-improvement-report-p2-stability.md#item-55) | 无自动改进机制 | 中 | — |
| **P2** | [真正后台并发 SubAgent + TTL 驱逐](./subagent-display-deep-dive.md) — `evictAfter` 时间戳 + 1s tick + 30s TTL，长时任务不阻塞主 loop [↓](./qwen-code-improvement-report-p2-stability.md#item-56) | **✓ 已实现**（控制面 + UI 层 + 注册表 + 后台 shell 池整合均已合并；`evictAfter` TTL 数值或与 Claude 略有差异）| 大 | [PR#3471](https://github.com/QwenLM/qwen-code/pull/3471) ✓（2026-04-27 合并 · `task_stop` / `send_message` / per-agent transcript）+ [PR#3488](https://github.com/QwenLM/qwen-code/pull/3488) ✓（2026-04-28 合并 · pill + combined dialog + detail view + cancel flow + 状态分类 Running/Completed/Failed/Cancelled）+ [PR#3642](https://github.com/QwenLM/qwen-code/pull/3642) ✓（2026-04-28 合并 · managed background shell pool + `/tasks` 命令 +1025/-411）+ [PR#3687](https://github.com/QwenLM/qwen-code/pull/3687) ✓（2026-04-29 合并 · 后台 shell 接入 `task_stop` 工具）+ [PR#3720](https://github.com/QwenLM/qwen-code/pull/3720) ✓（2026-04-29 合并 · 后台 shell 与 SubAgent 合并到统一 Background tasks dialog）|
| **P2** | [`/agents` 独立管理视图](./subagent-display-deep-dive.md) — subagent 历史归档 + 过滤 + 对比 [↓](./qwen-code-improvement-report-p2-stability.md#item-57) | 仅消息流线性回滚 | 中 | — |
| **P2** | [Coordinator 协调器面板](./subagent-display-deep-dive.md) — footer 上方紧凑多 agent 列表 + `↑↓` 导航 + `Enter` 详情 + `x` 驱逐 [↓](./qwen-code-improvement-report-p2-stability.md#item-58) | **✓ 已实现**（pill + combined dialog + detail view，与 Claude 设计略有差异：状态行 pill + 全屏对话 vs Claude footer 上方常驻面板）| 中 | [PR#3488](https://github.com/QwenLM/qwen-code/pull/3488) ✓（2026-04-28 合并 · pill 显示运行计数 + Down 键打开 dialog + Enter 进详情 + x 取消 + ↑↓ 导航 + Left/Esc 关闭）|
| **P2** | [终端渲染优化（紧凑 + 低闪烁）](./terminal-low-flicker-deep-dive.md) — DEC 2026 同步输出 + 差分渲染 + 双缓冲 + DECSTBM 硬件滚动 + 缓存池化 + alt-screen [↓](./qwen-code-improvement-report-p2-tools-commands.md#item-8) | 仅消息拆分防闪烁 + PR#3381 游标移动优化 | 大 | [PR#3381](https://github.com/QwenLM/qwen-code/pull/3381) ✓（局部） |
| **P2** | Image [Image #N] Chips — 粘贴图片后生成位置引用标记 [↓](./qwen-code-improvement-report-p2-tools-commands.md#item-9) | 缺失 | 小 | — |
| **P2** | --max-turns — headless 模式最大 turn 数限制 [↓](./qwen-code-improvement-report-p2-tools-commands.md#item-10) | 🟡 部分（已有 `--max-session-turns` 会话回合上限 + `--max-tool-calls`；命名/语义与 Claude `--max-turns` 略异）| 小 | — |
| **P2** | --max-budget-usd — headless 模式 USD 花费上限 [↓](./qwen-code-improvement-report-p2-tools-commands.md#item-11) | 缺失 | 小 | — |
| **P2** | Connectors — 托管式 MCP 连接（GitHub/Slack/Linear/Google Drive OAuth）[↓](./qwen-code-improvement-report-p2-tools-commands.md#item-12) | 缺失 | 大 | — |
| **P2** | MCP 并行连接 — pMap 动态插槽调度 + 双层并发（local:3/remote:20）[↓](./qwen-code-improvement-report-p2-perf.md#item-1) | 已并行但无并发上限 | 小 | — |
| **P2** | 插件/Skill 并行加载 — marketplace + session 双源并行 + 目录检查并行 [↓](./qwen-code-improvement-report-p2-perf.md#item-2)（⚠️ 已合并到 [P1 item-28 Skill 装载综合优化](./qwen-code-improvement-report-p0-p1-engine.md#item-28) 子项 #1+#2）| 🟡 部分（skill levels 级 `Promise.allSettled` 已有；marketplace+session 双源并行未必）| 小 | — |
| **P2** | Speculation 流水线建议 — 投机完成后立即并行生成下一建议 [↓](./qwen-code-improvement-report-p2-perf.md#item-3) | 每次重新生成 | 小 | — |
| **P2** | [write-through缓存与 TTL 后台刷新](./memoize-ttl-cache-deep-dive.md) — stale-while-revalidate + LRU 有界缓存 [↓](./qwen-code-improvement-report-p2-perf.md#item-4) | 仅搜索缓存（无通用 memoizeWithTTL/LRU util）| 小 | — |
| **P2** | 上下文收集并行化 — 多源附件 Promise.all 并行获取（~20 并发）[↓](./qwen-code-improvement-report-p2-perf.md#item-5) | 串行追加 | 小 | — |
| **P2** | 输出缓冲与防阻塞渲染 — setImmediate 延迟写入 + 内存缓冲 [↓](./qwen-code-improvement-report-p2-perf.md#item-6) | 直接 appendFileSync | 小 | — |
| **P2** | [LSP 服务器并行启动](./lsp-parallel-startup-deep-dive.md) — Promise.all 并行启动 + Promise.race 端口探测 [↓](./qwen-code-improvement-report-p2-perf.md#item-7) | 顺序 for 循环 | 小 | [PR#3034](https://github.com/QwenLM/qwen-code/pull/3034) 🟡 OPEN（LSP 诊断缓存）/ [PR#3170](https://github.com/QwenLM/qwen-code/pull/3170) 🟡 OPEN（官方 SDK + didSave 实时诊断）—— 均针对诊断，非本项并行启动 |
| **P2** | 请求合并与去重 — 1-in-flight + 1-pending + BoundedUUIDSet + inFlight 去重 [↓](./qwen-code-improvement-report-p2-perf.md#item-8) | 🟡 部分（MCP rediscovery coalescing + tool-registry lazy factory inflight 去重）| 中 | [PR#3818](https://github.com/QwenLM/qwen-code/pull/3818) ✓（MCP coalescing）/ [PR#3297](https://github.com/QwenLM/qwen-code/pull/3297) ✓（inflight dedup）|
| **P2** | 延迟初始化与按需加载 — lazySchema + 动态 import() + 延迟prefetch [↓](./qwen-code-improvement-report-p2-perf.md#item-9) | ✓ 延迟工具/registry/计数（defer 低频内置工具 + lazy factory + lazy message count）| 小 | [PR#4022](https://github.com/QwenLM/qwen-code/pull/4022) ✓（defer 内置工具）/ [PR#3297](https://github.com/QwenLM/qwen-code/pull/3297) ✓（lazy factory）/ [PR#3897](https://github.com/QwenLM/qwen-code/pull/3897) ✓（lazy count）|
| **P2** | 流式超时检测与级联取消 — 90s 空闲watchdog + siblingAbortController 级联 [↓](./qwen-code-improvement-report-p2-perf.md#item-10) | 固定超时/无级联 | 小 | — |
| **P2** | Git 文件系统直读 — .git/HEAD+refs 直读 + 批量 check-ignore + LRU 缓存 [↓](./qwen-code-improvement-report-p2-perf.md#item-11) | 每次 spawn git | 小 | — |
| **P2** | 设置/Schema 缓存防抖动 — 3 层设置缓存 + schema 首次锁定 + parse 去重 [↓](./qwen-code-improvement-report-p2-perf.md#item-12) | 每次重新读取解析 | 小 | — |
| **P2** | Bash 交互提示卡顿检测 — 45s 无输出 + prompt regex 匹配 + 自动通知 [↓](./qwen-code-improvement-report-p2-stability.md#item-1) | 无卡顿检测 | 小 | — |
| **P2** | TTY orphan process检测 — 30s 检查终端存活 + 自动优雅退出 [↓](./qwen-code-improvement-report-p2-stability.md#item-2) | 无检测 | 小 | — |
| **P2** | MCP 服务器优雅关闭升级 — SIGINT(100ms)→SIGTERM(400ms)→SIGKILL 3 阶段 [↓](./qwen-code-improvement-report-p2-stability.md#item-3) | 直接断开 | 小 | — |
| **P2** | 事件循环卡顿检测 — 主线程阻塞 >500ms 诊断日志 [↓](./qwen-code-improvement-report-p2-stability.md#item-4) | 无监控 | 小 | — |
| **P2** | 会话活动心跳 — refcount 活动追踪 + 30s keepalive + 空闲退出 [↓](./qwen-code-improvement-report-p2-stability.md#item-5) | 无心跳 | 小 | — |
| **P2** | Markdown 渲染缓存 — 500-LRU token cache + 纯文本快速路径 [↓](./qwen-code-improvement-report-p2-stability.md#item-6) | 每次重新解析 | 小 | — |
| **P2** | OSC 8 终端超链接 — 文件路径/URL Cmd+Click 直接打开 [↓](./qwen-code-improvement-report-p2-stability.md#item-7) | ✓ 已实现（markdown 链接 OSC 8 包裹，wrapped URL 仍可点）| 小 | [PR#4037](https://github.com/QwenLM/qwen-code/pull/4037) ✓ |
| **P2** | 模糊搜索选择器 — FuzzyPicker 通用组件 + 异步预览 + 匹配高亮 [↓](./qwen-code-improvement-report-p2-stability.md#item-8) | 无模糊搜索 | 中 | — |
| **P2** | 统一设计系统组件库 — 12 个语义 UI 原语 + ThemeProvider [↓](./qwen-code-improvement-report-p2-stability.md#item-9) | 组件分散 | 中 | — |
| **P2** | Markdown 表格终端渲染 — ANSI-aware + CJK-aware 列宽计算 [↓](./qwen-code-improvement-report-p2-stability.md#item-10) | CJK 列错位 | 小 | [PR#2914](https://github.com/QwenLM/qwen-code/pull/2914) ✓ |
| **P2** | 屏幕阅读器无障碍支持 — Diff/Spinner/Progress 纯文本替代渲染 [↓](./qwen-code-improvement-report-p2-stability.md#item-11) | hook 存在但使用有限 | 小 | — |
| **P2** | 色觉无障碍主题 — daltonized 红绿→蓝橙 diff 色板 [↓](./qwen-code-improvement-report-p2-stability.md#item-12) | 无色觉主题 | 小 | — |
| **P2** | 动画系统与卡顿状态检测 — shimmer 微光 + 30s 超时变红 [↓](./qwen-code-improvement-report-p2-stability.md#item-13) | 固定动画/无超时检测 | 小 | — |
| **P2** | [Agent 权限冒泡](./agent-permission-bubble-deep-dive.md) — bubble 模式 + Leader 桥接 + 邮箱回退 [↓](./qwen-code-improvement-report-p2-stability.md#item-14) | ✓ 已实现（bubble 模式 + `leaderPermissionBridge` 桥接 + 邮箱回退）| 中 | [PR#4844](https://github.com/QwenLM/qwen-code/pull/4844) ✓（2026-06-11 · Agent Team：bubble 审批 + leaderPermissionBridge）|
| **P2** | Agent 专属 MCP 服务器 — frontmatter mcpServers + 按需连接/清理 [↓](./qwen-code-improvement-report-p2-stability.md#item-15) | 共享全局 MCP | 小 | — |
| **P2** | [Agent 创建向导](./interactive-agent-creation-deep-dive.md) — 11 步交互式向导 + AI 生成模式 [↓](./qwen-code-improvement-report-p2-stability.md#item-16) | 基础命令行创建 | 中 | — |
| **P2** | Agent 进度追踪与实时状态 — ProgressTracker + task-notification + kill 控制 [↓](./qwen-code-improvement-report-p2-stability.md#item-17) | 仅最终结果 | 中 | — |
| **P2** | Agent 邮箱系统 — 文件 IPC + lockfile + 单播/广播 [↓](./qwen-code-improvement-report-p2-stability.md#item-18) | ✓ 已实现（team 邮箱：文件 IPC + proper-lockfile + 单播/广播）| 中 | [PR#4844](https://github.com/QwenLM/qwen-code/pull/4844) ✓（2026-06-11 · `agents/team/mailbox.ts`）|
| **P2** | cache_edits 增量缓存删除 — API 原地删除旧工具结果不破坏缓存前缀 [↓](./qwen-code-improvement-report-p2-perf.md#item-13) | 重建消息数组 | 小 | [PR#3006](https://github.com/QwenLM/qwen-code/pull/3006) ✓ |
| **P2** | 消息规范化与配对修复 — 合并连续 user + 修复孤立 tool_use/result + 100 媒体上限 [↓](./qwen-code-improvement-report-p2-perf.md#item-14) | 格式转换/无修复 | 中 | — |
| **P2** | [Git 状态自动注入上下文](./git-context-auto-injection-deep-dive.md) — gitBranch/cwd/platform/fileCount 每轮注入 [↓](./qwen-code-improvement-report-p2-perf.md#item-15) | ✓ 已实现（git status 注入系统提示 + Explore/git-log 指引）| 小 | [PR#4110](https://github.com/QwenLM/qwen-code/pull/4110) ✓ |
| **P2** | IDE 上下文注入与嵌套记忆触发 — 选区→目录规范自动注入 + 诊断双源收集 [↓](./qwen-code-improvement-report-p2-perf.md#item-16) | 无嵌套记忆触发 | 中 | — |
| **P2** | [图片压缩多策略流水线](./image-compression-pipeline-deep-dive.md) — format→resize→quality 阶梯 + JPEG fallback [↓](./qwen-code-improvement-report-p2-perf.md#item-17) | 仅计算 token/不压缩 | 中 | — |
| **P2** | WeakRef/WeakMap 防止 GC 保留 — AbortController/渲染缓存/span 自动释放 [↓](./qwen-code-improvement-report-p2-perf.md#item-18) | 全部强引用 Map | 小 | — |
| **P2** | [环形缓冲区与磁盘溢出](./circular-buffer-disk-spill-deep-dive.md) — CircularBuffer + BoundedUUIDSet + 8MB 溢出 [↓](./qwen-code-improvement-report-p2-perf.md#item-19) | 无上限数据结构 | 小 | — |
| **P2** | [终端渲染字符串池化](./terminal-rendering-string-pooling-deep-dive.md) — CharPool/StylePool 整数 ID 替代字符串 [↓](./qwen-code-improvement-report-p2-perf.md#item-20) | Ink 标准渲染 | 小 | — |
| **P2** | 文件描述符与句柄追踪 — >100 handles / >500 fd 预警 [↓](./qwen-code-improvement-report-p2-perf.md#item-21) | ✓ 已实现（`memoryDiagnostics`：`OPEN_FD_THRESHOLD=500` + activeHandles + fd-leak 检测）| 小 | [PR#3785](https://github.com/QwenLM/qwen-code/pull/3785) ✓（结构化内存诊断）|
| **P2** | Memoization cold start去重 — inFlight Map + TTL 后台刷新 + identity guard [↓](./qwen-code-improvement-report-p2-perf.md#item-22) | 无去重 | 小 | — |
| **P2** | 正则表达式编译缓存 — Hook/LS hot path new RegExp 缓存到 Map [↓](./qwen-code-improvement-report-p2-perf.md#item-23) | 每次重新编译 | 小 | — |
| **P2** | 搜索结果流式解析 — 流式逐行处理 + --max-count 提前终止 [↓](./qwen-code-improvement-report-p2-perf.md#item-24) | split('\n') 全量加载 | 小 | — |
| **P2** | React.memo 自定义相等性 — 消息组件防止击键重渲染（500ms→16ms）[↓](./qwen-code-improvement-report-p2-perf.md#item-25) | 🟡 部分（消息组件有普通 React.memo，无自定义相等性比较器）| 小 | 源码 `BtwMessage.tsx`（普通 memo）—— 原 [PR#2891](https://github.com/QwenLM/qwen-code/pull/2891) 引用有误（系 InputPrompt 清理）|
| **P2** | [Bun 原生 API 优化](./bun-native-api-optimization-deep-dive.md) — stringWidth/JSONL.parseChunk/argv0 dispatch [↓](./qwen-code-improvement-report-p2-perf.md#item-26) | Node.js 标准 API | 小 | [PR#2838](https://github.com/QwenLM/qwen-code/pull/2838) ✗ CLOSED（bun runtime 方案未合并）|
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
| **P2** | 系统提示危险操作行为指导 — 4 类危险操作列举 + 行为准则 + 审批范围限定 [↓](./qwen-code-improvement-report-p2-stability.md#item-28) | ✓ 已实现（`prompts.ts`：4 类危险操作 + reversibility/blast-radius 准则 + 审批范围限定 + 禁用破坏性操作走捷径）| 小 | [PR#2889](https://github.com/QwenLM/qwen-code/pull/2889) ✓ |
| **P2** | Unicode sanitization与 ASCII 走私防御 — NFKC + 不可见字符剥离 + 递归sanitization [↓](./qwen-code-improvement-report-p2-stability.md#item-29) | 无sanitization | 中 | — |
| **P2** | sandbox运行时集成 — seatbelt/bubblewrap/Docker + 文件/网络限制 [↓](./qwen-code-improvement-report-p2-stability.md#item-30) | seatbelt/Docker 运行时已存在（`utils/sandbox.ts`），非默认启用 | 大 | [PR#3146](https://github.com/QwenLM/qwen-code/pull/3146) ✓（仅新增 `tools.sandboxImage` 配置项；seatbelt/Docker 运行时见 `sandbox.ts`，非该 PR）|
| **P2** | SSRF 防护 — 私有 IP 阻断 + IPv4-mapped + DNS rebinding 防护 [↓](./qwen-code-improvement-report-p2-stability.md#item-31) | ✓ 已实现（`ssrfGuard.ts`：私有 IP + IPv4-mapped + fc00::/7 + cloud-metadata 169.254 + DNS 校验）| 中 | [PR#2827](https://github.com/QwenLM/qwen-code/pull/2827) ✓（2026-04-16 · 随 HTTP Hook 引入 `hooks/ssrfGuard.ts`）|
| **P2** | WebFetch 域名allowlist — 130+ 预批准域名 + 路径段边界匹配 [↓](./qwen-code-improvement-report-p2-stability.md#item-32) | 无内置allowlist | 小 | — |
| **P2** | 子进程环境变量清洗 — 30+ 敏感变量自动剥离 [↓](./qwen-code-improvement-report-p2-stability.md#item-33) | 继承完整环境 | 中 | — |
| **P2** | 工具输出密钥扫描 — 50+ gitleaks 规则 + 写入阻断 [↓](./qwen-code-improvement-report-p2-stability.md#item-34) | 无扫描 | 中 | — |
| **P2** | privilege escalation防护 — auto 模式 60+ 危险规则自动剥离 [↓](./qwen-code-improvement-report-p2-stability.md#item-35) | AUTO 模式已自动剥离危险 allow 规则（`permission-manager.ts` stripDangerousRulesForAutoMode + `dangerousRules.ts`），非 yolo 全批准 | 中 | [PR#3048](https://github.com/QwenLM/qwen-code/pull/3048) 🟡 OPEN（session-scoped vibe mode，未合并）；AUTO 剥离机制已落地（源码 `permission-manager.ts`）|
| **P3** | [动态状态栏](./dynamic-status-bar-deep-dive.md) — 模型/工具可实时更新状态文本 [↓](./qwen-code-improvement-report-p3-features.md#item-1) | 仅静态 Footer | 小 | — |
| **P3** | [上下文折叠](./context-compression-deep-dive.md) — History Snip（Claude Code 自身仅 scaffolding，未完整实现） [↓](./qwen-code-improvement-report-p3-features.md#item-2) | 缺失 | 大 | — |
| **P3** | [内存诊断](./memory-diagnostics-deep-dive.md) — V8 heap dump + 1.5GB 阈值触发 + leak 建议 + smaps 分析 [↓](./qwen-code-improvement-report-p3-features.md#item-3) | ✓ 已实现（`memoryDiagnostics`：RSS/heap gap 分析 + `smapsRollup` + fd-leak + 压力检测自动落盘）| 中 | [PR#4654](https://github.com/QwenLM/qwen-code/pull/4654) ✓（压力自动 dump）/ [PR#3785](https://github.com/QwenLM/qwen-code/pull/3785) ✓（结构化诊断）|
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
| **P3** | `--config-dir` CLI flag — 覆盖 `~/.qwen/` 配置目录（CI/多租户/DevContainer 场景，Copilot CLI v0.0.382 参考） [↓](./qwen-code-improvement-report-p3-features.md#item-17) | 仅 `QWEN_HOME` env var（[PR#2953](https://github.com/QwenLM/qwen-code/pull/2953) ✓ 已合并），无 `--config-dir` flag | 小 | — |
| **P3** | [Virtual Scrolling 虚拟滚动](./virtual-scrolling-deep-dive.md) — 仅渲染可视区域消息 [↓](./qwen-code-improvement-report-p3-ux.md#item-1) | ✓ 已实现（long conversation 虚拟视口 · ink 7）| 中 | [PR#4146](https://github.com/QwenLM/qwen-code/pull/4146) ✓（virtual viewport）|
| **P3** | [Feedback Survey 用户反馈](./feedback-survey-deep-dive.md) — 内置 /feedback 评分+文字表单 [↓](./qwen-code-improvement-report-p3-ux.md#item-2) | 无内置反馈 | 小 | — |
| **P3** | [Turn Diffs 轮次差异统计](./turn-diffs-deep-dive.md) — 每轮变更文件数+增删行数汇总 [↓](./qwen-code-improvement-report-p3-ux.md#item-3) | 仅 per-file diff | 小 | — |
| **P3** | [LogoV2 品牌标识](./logov2-brand-identity-deep-dive.md) — ASCII art + 启动功能引导 [↓](./qwen-code-improvement-report-p3-ux.md#item-4) | 纯文本 | 小 | — |
| **P3** | [Buddy 伴侣精灵](./buddy-companion-deep-dive.md) — 可见助手 + 状态动画 + 空闲引导 [↓](./qwen-code-improvement-report-p3-ux.md#item-5) | 无 | 中 | — |
| **P3** | [useMoreRight 右面板](./right-panel-ui-deep-dive.md) — 对话+文件预览并排显示 [↓](./qwen-code-improvement-report-p3-ux.md#item-6) | 单列布局 | 中 | — |
| **P3** | iTerm/Terminal 状态备份恢复 — 异常退出后终端状态自动修复 [↓](./qwen-code-improvement-report-p3-ux.md#item-7) | 基础清理 | 小 | — |
| **P3** | settingsSync 设置同步 — 跨设备设置同步到云端/git [↓](./qwen-code-improvement-report-p3-ux.md#item-8) | 仅本地存储 | 中 | — |
| **P3** | Auto Mode 子命令管理 — defaults/config/critique 三个子命令 [↓](./qwen-code-improvement-report-p3-ux.md#item-9) | 无子命令 | 小 | — |
| **P3** | useInboxPoller 收件箱轮询 — 多 Agent 邮箱定期检查 [↓](./qwen-code-improvement-report-p3-hooks.md#item-1) | 已有 leader inbox 轮询（500ms，实验性 Agent Team）| 小 | [PR#4844](https://github.com/QwenLM/qwen-code/pull/4844) ✓（2026-06-11 · `TeamManager` startInboxPolling）|
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
| **P3** | useSearchInput 搜索输入 [↓](./qwen-code-improvement-report-p3-hooks.md#item-15) | 已有 `useSessionSearchInput`（/resume 搜索）| 小 | [PR#3880](https://github.com/QwenLM/qwen-code/pull/3880) ✓ |
| **P3** | usePasteHandler 粘贴处理 [↓](./qwen-code-improvement-report-p3-hooks.md#item-16) | 分散处理 | 小 | — |
| **P3** | useScheduledTasks 定时任务 [↓](./qwen-code-improvement-report-p3-hooks.md#item-17) | 无 UI hook | 小 | — |
| **P3** | useVimInput Vim 输入 [↓](./qwen-code-improvement-report-p3-hooks.md#item-18) | 基础 vim | 小 | — |
| **P3** | useLspPluginRecommendation LSP 推荐 [↓](./qwen-code-improvement-report-p3-hooks.md#item-19) | 无 | 小 | — |
| **P3** | unifiedSuggestions 统一建议 [↓](./qwen-code-improvement-report-p3-hooks.md#item-20) | 分散 | 小 | — |
| **P3** | useInputBuffer 输入缓冲 [↓](./qwen-code-improvement-report-p3-hooks.md#item-21) | 无 | 小 | — |
| **P3** | useIssueFlagBanner 问题通知 [↓](./qwen-code-improvement-report-p3-hooks.md#item-22) | 无 | 小 | — |
| **P3** | useDiffData 差异数据 [↓](./qwen-code-improvement-report-p3-hooks.md#item-23) | 已有 `useDiffData` hook | 小 | [PR#4277](https://github.com/QwenLM/qwen-code/pull/4277) ✓ |
| **P3** | toolUseSummary 工具使用摘要 [↓](./qwen-code-improvement-report-p3-hooks.md#item-24) | 无 | 小 | — |
| **P3** | useAwaySummary 离开摘要 [↓](./qwen-code-improvement-report-p3-hooks.md#item-25) | 已有 `useAwaySummary`（/recap 会话摘要，焦点返回自动触发）| 小 | [PR#3434](https://github.com/QwenLM/qwen-code/pull/3434) ✓ |
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
| [P0/P1 引擎优化](./qwen-code-improvement-report-p0-p1-engine.md) | 流式执行、缓存、Token 管理、崩溃恢复、Agent 编排、上下文管理、安全、Skill 装载性能等 | 28 |
| [P2 核心功能与企业特性](./qwen-code-improvement-report-p2-core.md) | 中等优先级（Shell 安全、MDM 企业策略、Token 计数、Computer Use、AgentScope Plan/A2A/OTel 参考等） | 26 |
| [P2 工具与命令](./qwen-code-improvement-report-p2-tools-commands.md) | 中等优先级（Conditional Hooks、/batch、MCP 重连、Ripgrep 回退、Skill 模型覆盖、PreCompact Hook、模型调用 Slash 命令、/experimental 门控等） | 26 |
| [P2 界面与 UX](./qwen-code-improvement-report-p2-tools-ui.md) | 中等优先级（Token 警告、Spinner、/rewind、Diff 渲染、/plan 等） | 20 |
| [P2 性能优化](./qwen-code-improvement-report-p2-perf.md) | 中等优先级（流式执行、缓存模式、延迟初始化、请求合并、指令文件去重等） | 35 |
| [P2 稳定性、安全与 CI/CD](./qwen-code-improvement-report-p2-stability.md) | 中等优先级（Unicode sanitization、sandbox集成、SSRF 防护、密钥扫描、PID namespace、Session Recap、显示高度控制、输出截断、Bash UI、Update/Diff UI、Fast Model 应用、SubAgent 展示 等） | 58 |
| [P3 功能特性](./qwen-code-improvement-report-p3-features.md) | 低优先级功能特性（动态状态栏、Feature Gates、Vim、语音、插件市场、--config-dir 等） | 17 |
| [P3 用户体验](./qwen-code-improvement-report-p3-ux.md) | 低优先级用户体验（Virtual Scrolling、Turn Diffs、Buddy、settingsSync 等） | 9 |
| [P3 Hook 与组件](./qwen-code-improvement-report-p3-hooks.md) | 低优先级 Hook 与组件（useInboxPoller、AgentSummary、usePrStatus 等） | 33 |

## 四、架构差异总结

> **2026-06-20 逐项重新核实**（对照 origin/main `f35a10ba1` 源码 + git log）：原表多数"无/缺失/落后"已过时——约 24 项实际已实现。下表为核实后状态，PR# 均经 `git log --grep "(#NNNN)"` 确认合并。

| 维度 | Claude Code | Qwen Code | 差距评估 | 进展 |
|------|-------------|-----------|----------|------|
| **[Mid-Turn Queue Drain](./command-queue-orchestration-deep-dive.md)** | `query.ts` 工具批次间 drain | **✓ 已实现** | 已对齐 | [PR#2854](https://github.com/QwenLM/qwen-code/pull/2854) ✓ |
| 压缩 (Compression) 策略 | 4 层分层压缩 | **多层（microcompaction + reactive + /compress-fast）** | 接近对齐 | [PR#3006](https://github.com/QwenLM/qwen-code/pull/3006) ✓（L2）/ [PR#3879](https://github.com/QwenLM/qwen-code/pull/3879) ✓（reactive）/ [PR#4893](https://github.com/QwenLM/qwen-code/pull/4893) ✓（compress-fast） |
| Subagent | 支持 fork + 上下文继承 | **✓ fork + 上下文继承** | 已对齐 | [PR#2936](https://github.com/QwenLM/qwen-code/pull/2936) ✓ |
| **智能工具并行** | Kind-based batching（默认 10 并发） | **✓ Kind-based batching** | 已对齐 | [PR#2864](https://github.com/QwenLM/qwen-code/pull/2864) ✓ |
| 投机执行 (Speculation) | 完整 overlay-fs + cow（991 行） | v0.15.0 已完整实现（563 行），默认关闭 | 小差距 | [PR#2525](https://github.com/QwenLM/qwen-code/pull/2525) ✓ |
| 启动优化 | API Preconnect + Early Input | ✓ preconnect + early input | 已对齐 | [PR#3318](https://github.com/QwenLM/qwen-code/pull/3318) ✓（preconnect 2026-04-27）/ [PR#3319](https://github.com/QwenLM/qwen-code/pull/3319) ✓（early input）/ [PR#3232](https://github.com/QwenLM/qwen-code/pull/3232) ✓（profiler） |
| 按路径注入上下文规则 | `.claude/rules/` + frontmatter `paths:` 惰加载 | ✅ `.qwen/rules/` + frontmatter `paths:` + 嵌套子目录 | **已对齐** | [PR#3339](https://github.com/QwenLM/qwen-code/pull/3339) ✓ |
| 会话记忆 (Session Memory) | SessionMemory + memdir | **✓ 托管 auto-memory** | 接近对齐 | [PR#3087](https://github.com/QwenLM/qwen-code/pull/3087) ✓ + [PR#4747](https://github.com/QwenLM/qwen-code/pull/4747) ✓（`~/.qwen/memories`） |
| 自动记忆 (Memory) 整理 | Auto Dream | **✓ 已实现** | 已对齐 | [PR#3087](https://github.com/QwenLM/qwen-code/pull/3087) ✓ + [PR#3836](https://github.com/QwenLM/qwen-code/pull/3836) ✓（dream UI） |
| 上下文折叠 (Context Collapse) | History Snip | **部分**（microcompaction / reactive 压缩，非专门 history-snip）| 中等差距 | [PR#3006](https://github.com/QwenLM/qwen-code/pull/3006) ✓ / [PR#3879](https://github.com/QwenLM/qwen-code/pull/3879) ✓ |
| Shell 安全增强 | 25+ 检查 + tree-sitter | **LLM 分类器 + shell-semantics + denial tracking** | 接近对齐 | [PR#4151](https://github.com/QwenLM/qwen-code/pull/4151) ✓ + `permissions/classifier.ts` |
| MDM 企业策略 | plist + Registry + 远程 API | 无 | 缺失 | — |
| Token 实时计数 | API 计数 + VCR 缓存 | **✓ 流式实时计数** | 接近对齐 | [PR#3329](https://github.com/QwenLM/qwen-code/pull/3329) ✓ + [PR#4512](https://github.com/QwenLM/qwen-code/pull/4512) ✓（breakdown） |
| 工具发现 | ToolSearchTool | **✓ 已实现** | 已对齐 | [PR#3589](https://github.com/QwenLM/qwen-code/pull/3589) ✓ MERGED 2026-05-26（`tools/tool-search.ts`）+ PR#4022/#4069 |
| 多 Agent通信 | SendMessageTool | **✓ 已实现** | 已对齐 | [PR#3471](https://github.com/QwenLM/qwen-code/pull/3471) ✓（`tools/send-message.ts`） |
| 文件索引 | FileIndex（fzf 风格） | **✓ git ls-files + rg** | 小差距 | [PR#3214](https://github.com/QwenLM/qwen-code/pull/3214) ✓（2026-05-12 合并） |
| Commit Attribution | Co-Authored-By 追踪 | **git notes 元数据追踪（独家更精细）** | **超 Claude**（per-file 字符级 aiChars/humanChars，refs/notes/ai-attribution，不污染 commit message）| **[PR#3115](https://github.com/QwenLM/qwen-code/pull/3115) ✓ 2026-05-08 MERGED · +7075/-224** |
| 会话分支 | /branch 对话分叉 | **`/branch` + `/fork` alias** | **已对标 Claude `--fork-session` flag**（slash 命令更顺手 + JSONL 完整复制 + forkedFrom stamp + atomic create + rollback-safe swap）| **[PR#3539](https://github.com/QwenLM/qwen-code/pull/3539) ✓ 2026-05-08 MERGED · +1538/-18** |
| Output Styles | Learning / Explanatory 模式 | 无 | 缺失 | — |
| Fast Mode | 速度/成本分级推理 | `fastModel` 不同方案 + 多场景应用（auto-title + tool-summary 已合并；web-fetch 方案被否决）| ⚠️ 部分→扩展中 | [PR#3077](https://github.com/QwenLM/qwen-code/pull/3077) ✓ / [PR#3086](https://github.com/QwenLM/qwen-code/pull/3086) ✓ / [PR#3120](https://github.com/QwenLM/qwen-code/pull/3120) ✓ / [PR#3540](https://github.com/QwenLM/qwen-code/pull/3540) ✓（auto-title via fastModel，2026-04-23）/ [PR#3538](https://github.com/QwenLM/qwen-code/pull/3538) ✓（tool-summary via fastModel）/ [PR#3537](https://github.com/QwenLM/qwen-code/pull/3537) ✗ CLOSED（web-fetch fastModel 方案被否决）|
| 并发 Session | 多终端 PID 追踪 + 后台脱附 | **部分**（后台 shell 池 + monitor）| 中等差距 | [PR#3642](https://github.com/QwenLM/qwen-code/pull/3642) ✓ + [PR#3684](https://github.com/QwenLM/qwen-code/pull/3684) ✓ |
| Git Diff 统计 | 结构化 diff + 按文件统计 | **✓ /diff 命令** | 已对齐 | [PR#3491](https://github.com/QwenLM/qwen-code/pull/3491) ✓ |
| 文件历史快照 | per-file SHA256 + 按消息恢复 | **✓ per-file 跨会话恢复** | 已对齐 | [PR#4897](https://github.com/QwenLM/qwen-code/pull/4897) ✓（`fileHistoryService.ts`） |
| **流式工具执行** | StreamingToolExecutor 流水线 | 缺失（已核实：3 路径均 collect-then-execute / post-stream；`streamingToolCallParser` 仅 OpenAI delta 重组解析层，非执行器；`StreamingToolExecutor` 仅 `useGeminiStream.ts` 注释引用）| 中等差距 | — |
| **文件读取缓存** | FileReadCache 1000 LRU + 批量并行 | **✓ FileReadCache + 失效 + prior-read**（仅 32 批并行待）| 接近对齐 | [PR#3717](https://github.com/QwenLM/qwen-code/pull/3717)/[#3774](https://github.com/QwenLM/qwen-code/pull/3774)/[#3810](https://github.com/QwenLM/qwen-code/pull/3810)/[#3932](https://github.com/QwenLM/qwen-code/pull/3932)/[#4002](https://github.com/QwenLM/qwen-code/pull/4002) ✓ |
| **记忆异步prefetch** | Memory prefetch + skill prefetch | **部分**（记忆 prefetch ✓：非阻塞 auto-memory recall + settled 注入；skill prefetch 仍缺）| 中等差距 | [PR#4172](https://github.com/QwenLM/qwen-code/pull/4172) ✓（2026-05-19）+ [PR#3087](https://github.com/QwenLM/qwen-code/pull/3087) ✓ |
| **Token Budget 续行** | 90% 续行 + 递减检测 + 分层回退 | 部分（Workflow budget；session 90% 续行未确认）| 中等差距 | [PR#5231](https://github.com/QwenLM/qwen-code/pull/5231) ✓（Workflow budget） |
| **MCP 动态插槽** | pMap + dual-tier concurrency | 无并发限制 | 小差距 | — |
| **通用缓存模式** | memoizeWithTTL + memoizeWithLRU | 仅搜索缓存 | 中等差距 | — |
| **同步 I/O** | 绝大多数 async | ✓ 已实现 | 显著落后→已追平 | [PR#3581](https://github.com/QwenLM/qwen-code/pull/3581) ✓（2026-04-24 合并 · hot path 110→10 syscall/prompt，-91%）|
| **Prompt Cache** | 分段 + schema 锁定 + 缓存失效检测 | 无分段（有 cache 稳定化）| 中等差距 | [PR#4896](https://github.com/QwenLM/qwen-code/pull/4896) ✓（cache 稳定化）|
| **请求合并** | coalescing + BoundedUUIDSet | 部分（MCP rediscovery coalescing）| 小差距 | [PR#3818](https://github.com/QwenLM/qwen-code/pull/3818) ✓ |
| **延迟初始化** | lazySchema + 延迟 import + 延迟prefetch | **✓ 延迟工具/registry/计数** | 接近对齐 | [PR#4022](https://github.com/QwenLM/qwen-code/pull/4022) ✓ + [PR#3297](https://github.com/QwenLM/qwen-code/pull/3297) ✓ + [PR#3897](https://github.com/QwenLM/qwen-code/pull/3897) ✓ |
| **Git 直读** | .git/HEAD+refs 直读 + LRU | spawn git | 中等差距 | — |
| **崩溃恢复** | 中断检测 + 合成续行 + 全量恢复 | 部分（JSONL 粘连恢复；3 状态检测+合成续行仍待）| 中等差距 | [PR#3656](https://github.com/QwenLM/qwen-code/pull/3656) ✓ |
| **API 重试** | 10 次退避 + 529 降级 + 持久化重试 | **退避 + 429 SSE + 持久化重试** | 接近对齐（classifier 方案已关闭）| [PR#3246](https://github.com/QwenLM/qwen-code/pull/3246) ✓（429 SSE）+ [PR#3080](https://github.com/QwenLM/qwen-code/pull/3080) ✓ + [PR#4708](https://github.com/QwenLM/qwen-code/pull/4708) ✓ / [PR#3798](https://github.com/QwenLM/qwen-code/pull/3798) ✗ CLOSED |
| **优雅关闭** | SIGINT/SIGTERM + 清理注册 + failsafe | **✓ 信号处理** | 接近对齐 | [PR#1884](https://github.com/QwenLM/qwen-code/pull/1884) ✓ + [PR#3544](https://github.com/QwenLM/qwen-code/pull/3544) ✓ |
| **反应式压缩** | prompt_too_long 自动裁剪重试 | **✓ 已实现** | 已对齐 | [PR#3879](https://github.com/QwenLM/qwen-code/pull/3879) ✓ + [PR#4526](https://github.com/QwenLM/qwen-code/pull/4526) ✓ |
| **原子写入** | temp+rename + 大结果persist to disk | **✓ temp+rename** | 已对齐 | [PR#4333](https://github.com/QwenLM/qwen-code/pull/4333) ✓ |
| **自动检查点** | 默认启用 + per-message 快照 | **✓ per-message + /rewind** | 接近对齐 | [PR#4064](https://github.com/QwenLM/qwen-code/pull/4064) ✓ + [PR#4897](https://github.com/QwenLM/qwen-code/pull/4897) ✓ + [PR#3441](https://github.com/QwenLM/qwen-code/pull/3441) ✓ |
| Session Ingress Auth | bearer token 远程认证 | 无 | 缺失 | — |
| Computer Use | macOS 桌面自动化 | **✓ 已实现（跨平台，超 Claude）** | 超 Claude | [PR#4590](https://github.com/QwenLM/qwen-code/pull/4590) ✓ + [PR#5051](https://github.com/QwenLM/qwen-code/pull/5051) ✓（cua-driver 跨平台）|
| Deep Link | `claude-cli://` URI scheme | **✓ `craftagents://` URI scheme** | 已对齐 | `desktop/.../deep-link.ts` |
| Notebook Edit | Jupyter cell 编辑 | **✓ `notebook_edit` 工具** | 已对齐 | PR#3900 / `ed14a3306`（2026-05-21）|
| Team Memory | 组织级记忆同步 | 无（有 Agent Team，非组织记忆同步）| 缺失 | — |
| 自定义快捷键 | multi-chord + keybindings.json | **✓ keybindings 系统** | 接近对齐 | `config/keyBindings.ts` + [PR#3969](https://github.com/QwenLM/qwen-code/pull/3969) ✓ |
| 企业代理 | CONNECT relay + CA cert 注入 | 部分（proxy base URL + Anthropic 兼容；CONNECT relay+CA 注入未必）| 中等差距 | [PR#3991](https://github.com/QwenLM/qwen-code/pull/3991) ✓ + [PR#4020](https://github.com/QwenLM/qwen-code/pull/4020) ✓ + [PR#4607](https://github.com/QwenLM/qwen-code/pull/4607) ✓ |
| 终端主题 | OSC 11 dark/light 检测 | ✓ 已实现 | **已对齐** | [PR#3460](https://github.com/QwenLM/qwen-code/pull/3460) ✓（2026-04-22 合并）|
| Denial Tracking | 权限拒绝学习 + 自动回退 | **✓ 已实现** | 已对齐 | `permissions/denialTracking.ts` + [PR#4476](https://github.com/QwenLM/qwen-code/pull/4476) ✓ |

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

> 📎 本节仅内联**最近一次 rollup**（下方 2026-06-20）。完整逐日更新日志（2026-06-20 → 2026-04-05，共 75 条）已拆分至 **[qwen-code-improvement-report-changelog.md](./qwen-code-improvement-report-changelog.md)**，以保持本报告可读。

### 2026-06-20 月度增量（2026-05-16 → 2026-06-20 · **608 commits / 176 feat PR** · origin/main `f35a10ba1`）

> 5 周窗口的滚动汇总（非逐 PR 深挖；逐项深挖见 [changelog](./qwen-code-improvement-report-changelog.md)）。Qwen Code 体量再增：`packages/**` 从 ~500 → **~4,750 文件**（~2,700 源 `.ts(x)`，14 包）。主线 = **Workflow 工具编排 P1–P5 落地** + **桌面 app 新包** + **daemon/web-shell 成熟** + 多渠道（QQ/飞书）。

**🌟 Workflow 工具 P1–P5 全栈落地**（umbrella [#4721](https://github.com/QwenLM/qwen-code/pull/4721)）——确定性多 agent 编排，对标本报告 Coordinator/Swarm（[line 83](#二qwen-code-改进建议矩阵)）+ Codex multi-agent v2：
- **P1** [#4732](https://github.com/QwenLM/qwen-code/pull/4732)（2026-06-10）：`node:vm` 最小沙箱 + 顺序 `agent()`
- **P2** [#4947](https://github.com/QwenLM/qwen-code/pull/4947)（2026-06-12）：`parallel()` + `pipeline()` 并发 fan-out
- **P3** [#5034](https://github.com/QwenLM/qwen-code/pull/5034)（2026-06-14）：`agent({schema, agentType, model, isolation:'worktree'})`
- **P4** [#5094](https://github.com/QwenLM/qwen-code/pull/5094)（2026-06-16）：`meta` + `/workflows` + phase-tree 进度
- **P5** [#5231](https://github.com/QwenLM/qwen-code/pull/5231)（2026-06-18）：token budget + per-run UI surfacing

**🌟 桌面 app 新子系统**：[#3778](https://github.com/QwenLM/qwen-code/pull/3778)（2026-06-11）`packages/desktop` + Qwen ACP SDK 集成（macOS 公证 / Windows 自更新 / git branch badge）；后续 desktop qwen 集成（#4728）+ macOS 26 Liquid Glass（#5284）+ desktop-pet skill（#4808）。

**daemon / web-shell 成熟**：`qwen serve` 直接托管 Web Shell UI（[#5392](https://github.com/QwenLM/qwen-code/pull/5392)）+ DaemonTransport/ACP 合规（#5040）+ mid-turn 消息投递（#5175）+ web-shell token/设置/重试/流式指标（#5066）+ 完成 turn 折叠为 prompt+答案（#5125）+ per-turn time/token（#5163）。

**多渠道 IM**：QQ Bot（[#5202](https://github.com/QwenLM/qwen-code/pull/5202)，2026-06-19）+ 飞书/Lark（#4379，2026-05-28）。

**Durable cron / loop**：可重启存活的定时任务（#5004）+ 秒级 wakeup 引擎（#5182）+ prompt-only `/loop` 自定速唤醒（#5197）。

**Computer Use 跨平台**：迁移到 cua-driver（#5051）+ open-computer-use MCP 零配置内建（#4590）。

**记忆 / Goal / Plan**：`/rewind` 文件恢复（#4064，2026-05-16）+ `/goal` judge-driven（#4123，详 changelog 2026-05-16 条）+ 用户级 auto-memory `~/.qwen/memories/`（#4747）+ Plan `plansDirectory` 可配置（#4062）+ `QWEN.local.md` project-local 上下文（#4091）。

**Skills**：`/skills` picker 对话框（#4532）+ triage skill（#4577）+ user-invocable frontmatter（#5037）+ skill `allowedTools` 自动批准（#4704）+ `auto-skill-` 前缀强制（#4839）。

**性能 / 截断**：分层工具输出截断 + per-message/per-tool 预算（#4880）+ `/compress-fast` 无 LLM 规则压缩（#4893）+ 内存压力监控/诊断落盘（#4403/#4654）+ grep 结果可满足 prior-read 检查（#5043）。

**遥测**：#3731 Phase 2–4（tool.blocked_on_user / subagent span 并发隔离 / TTFT / GenAI semconv，#4321 等）+ 运行时内存/CPU OTel 采样（#4868）。

**Hooks / 权限**：post tool batch hooks（#4454）+ user prompt expansion hooks（#4377）+ toolCallId 传入 hook（#4918）+ ACP 权限超时可配（#5260）+ 专用 agent 权限对话框（#5105）。

#### 矩阵状态修正（本次同步修正 8 项 stale OPEN/缺失 + 3 项历史 现状/进展 矛盾，均经 `git log origin/main` 核实）

| item | 旧 | 新 |
|---|---|---|
| 启动 preconnect（line 58）| PR#3318 open | ✓ 2026-04-27（`3b0b6c052`）|
| Coordinator/Swarm（line 83）| PR#3471/#3488 🟡 OPEN | ✓ 2026-04-27 / 04-28（与 line 193 一致）+ Workflow #4721 |
| Agent `isolation:worktree`（line 101）| PR#4073 OPEN | ✓ 2026-05-14（`609e05bae`）|
| 自动检查点（line 82）| 仅 PR#3292 OPEN | + PR#4064 ✓ 2026-05-16（`/rewind` 文件恢复）；picker UX 仍缺（#3292 已关闭）|
| /doctor memory（line 159）| PR#3785 🟡 OPEN | ✓ 2026-05-17（`eef06ce37`）|
| **Computer Use（line 111）** | **缺失** | **✅ 已实现且超 Claude（跨平台）**——#4590 零配置内建（2026-05-29）+ #5051 cua-driver 跨平台 + 35 工具面 |
| **Auto Dream（line 54）** | 缺失（与 PR 列 ✓ 自相矛盾）| ✓ 已实现（PR#3087 managed auto-memory + auto-dream）|
| **Notebook Edit（line 120）** | 缺失 | ✓ 已实现（NotebookEdit 工具，2026-05-21 · #3900 + #4373）|

> 另校正 3 项历史"现状=缺失 但进展=✓"矛盾：队列输入编辑（#2871）/ `/batch`（#3079）/ 上下文 Tips（#2904），均 2026-04 已合并。
>
> 其余 `缺失` 项（Team Memory / Transcript Search / Output Styles / Deep Link / `/teleport` / Bare Mode / GitLab CI/CD / 并发 Session / 企业代理 / Session Ingress Auth 等）经窗口 git log 关键词核对，**确为未实现**，维持 `缺失`。

已关闭/未合并（已核实）：API retry classifyError（#3798 CLOSED）、rewind picker UX（#3292 CLOSED）、WebFetch fastModel（#3537 CLOSED · 方案被否决）；仍 OPEN：Web UI+QR remote control（#2330）。

#### §二 改进建议矩阵逐行重核（2026-06-20 · ~140 行全表对照 `ef2c82fd6` 源码 + git log）

> 9 路并行核查 + 主控复核。共修正 **32 行**（§二）+ §四/§六 连带一致性。主题三类：

**① stale「缺失/无」→ 实际已实现**（经源码符号 + 引入 commit 双证）：优雅关闭（`cleanup.ts` 5s failsafe · #1884）/ 持久化重试（`retry.ts` persistentMode · #3080）/ 原子写（`atomicWriteFile` · #4096+#4333+#4431）/ InProcess 隔离（AsyncLocalStorage · #2936+#4844）/ Agent AI 生成（`subagentGenerator` · #4249）/ daemon agents CRUD（`workspaceAgents.ts` 6 routes · #4249）/ 模糊文件搜索（fzf AsyncFzf · #3214+#4621）/ 图片读取（inlineData · #3160）/ 通用工具输出截断（`coreToolScheduler` · #4880）/ 工具摘要 fast-model（#3538）/ Agent 邮箱 + 权限冒泡（`team/mailbox.ts` + `leaderPermissionBridge.ts` · #4844）/ SSRF 防护（`ssrfGuard.ts` · #2827）/ privilege-escalation 剥离（`permission-manager.ts`）/ 3 个 P3 hook（useSearchInput #3880 · useDiffData #4277 · useAwaySummary #3434 · useInboxPoller #4844）/ 记忆 prefetch（`MemoryPrefetchHandle` 非阻塞 auto-memory recall · #4172——复核时发现 9 路 agent 漏判，现改 🟡：记忆 ✓ / skill·附件 prefetch 待）。

**② 错误 / 已撤 PR 引用纠正**：**#2886**（实为 "session_id in API calls"，非 Agent Team——6 处误citing 已改为 #4844 / #2936 / #3471）；#3537 / #3798 / #3292 / #2838（均 CLOSED，非 OPEN）；#3048（OPEN vibe-mode，非本项实现）；#3034 / #3170（OPEN，针对诊断非并行启动）；张冠李戴 #4051(docs 已 MERGED) / #3042(无关 2025-07 docs) / #2024(早期拒绝 PDF) / #2891(InputPrompt 清理)。

**③ 增量事实**：新增 `packages/sdk-java`（Java SDK）→ "Qwen 仅 TS SDK" 已过时（现 TS+Python+Java 三套）；WebFetch fastModel 路由经核实**被否决**（`web-fetch.ts` 刻意 pin 主模型）。

#### §二 二轮深度复核（2026-06-20 · 抽查触发→全表系统核实，再修正 ~33 行）

> 用户两次抽查（记忆 prefetch / Fork Subagent）均命中 9 路 agent 漏判的 stale，遂转为系统性核实。三种高产方法叠加，又揪出 ~33 行 stale（多为近 1–2 月合入但 §二 未同步）：
>
> **① 自相矛盾检测**（现状=缺失/仅 但进展=✓ PR）：HTTP Hooks（#2827）、Skill 模型覆盖（#2949）、危险操作指导（#2889）。
> **② §二↔§四 交叉比对**（§四 近期已核实，§二 落后）：反应式压缩 #3879、Token 实时计数 #3329、并发 Session #3642、Git `/diff` #3491、文件历史快照 #4897、Deep Link `craftagents://`、keybindings #3969、Denial Tracking #4476、SendMessageTool #3471、Shell 安全 classifier #4151、请求合并 #3818、延迟初始化 #4022 等。
> **③ recent-feat-PR 反扫**（按合入 PR 标题反查"缺失"行——最高产）：OSC 通知 iTerm2/Kitty/Ghostty #3562、`/copy` #4761、OSC 8 超链接 #4037、fd 追踪 memoryDiagnostics #3785、Virtual Scrolling #4146、路径补全 #4092、`/rename` #4048、Git 状态注入 #4110、PreCompact Hook #4688、内存诊断 #4654 等。
>
> **大教训**：`git log --grep "(#N)"` 假阳性（PR 号复用/正文交叉引用）+ 反向 grep 假阴性（功能在 `core/client.ts` 等非预期文件）令首轮 agent 系统性漏判"近期已实现"项。可靠法：`--diff-filter=A -- <file>` 定引入 commit + recent-feat-PR 标题反扫 + §四 交叉比对。两次"Fork/prefetch 实为已实现"另引发 [fork-subagent-deep-dive](./fork-subagent-deep-dive.md) §9 对比表与 [memory-prefetch](./memory-prefetch-deep-dive.md)、[item-2](./qwen-code-improvement-report-p0-p1-core.md#item-2)/[item-3](./qwen-code-improvement-report-p0-p1-engine.md#item-3) 连带更新。

---

*更早历史（2026-05-16 → 2026-04-05，逐日逐 PR 深度对照）见 [qwen-code-improvement-report-changelog.md](./qwen-code-improvement-report-changelog.md)。*
