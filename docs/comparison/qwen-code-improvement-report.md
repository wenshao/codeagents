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
| **P0** | [Mid-Turn Queue Drain](./input-queue-deep-dive.md) — Agent 执行中途注入用户输入，无需等整轮结束 [↓](./qwen-code-improvement-report-p0-p1-core.md#item-6) | 推理循环内无队列检查 | 中 | [PR#2854](https://github.com/QwenLM/qwen-code/pull/2854) |
| **P0** | [多层上下文压缩](./context-compression-deep-dive.md) — 自动裁剪旧工具结果 + 摘要，用户无需手动 /compress [↓](./qwen-code-improvement-report-p0-p1-core.md#item-1) | 仅单一 70% 手动压缩 | 中 | — |
| **P0** | [Fork Subagent](./fork-subagent-deep-dive.md) — Subagent 继承完整对话上下文，共享 prompt cache 省 80%+ 费用 [↓](./qwen-code-improvement-report-p0-p1-core.md#item-2) | Subagent 必须从零开始 | 中 | — |
| **P0** | [会话崩溃恢复与中断检测](./crash-recovery-deep-dive.md) — 3 种中断状态检测 + 合成续行 + 全量恢复 [↓](./qwen-code-improvement-report-p0-p1-engine.md#item-7) | 无崩溃恢复 | 大 | — |
| **P1** | [Speculation](../tools/claude-code/10-prompt-suggestions.md) — 预测用户下一步并提前执行，Tab 接受零延迟 [↓](./qwen-code-improvement-report-p0-p1-core.md#item-3) | 已实现但默认关闭 | 小 | [PR#2525](https://github.com/QwenLM/qwen-code/pull/2525) ✓ |
| **P1** | [会话记忆](./memory-system-deep-dive.md) — 关键决策/文件结构自动提取，新 session 自动注入 [↓](./qwen-code-improvement-report-p0-p1-core.md#item-4) | 仅简单笔记工具 | 大 | — |
| **P1** | [Auto Dream](./memory-system-deep-dive.md) — 后台 agent 自动合并去重过时记忆 [↓](./qwen-code-improvement-report-p0-p1-core.md#item-5) | 缺失 | 中 | — |
| **P1** | [工具动态发现](./tool-search-deep-dive.md) — 仅加载核心工具，其余按需搜索，省 50%+ token [↓](./qwen-code-improvement-report-p0-p1-core.md#item-11) | 全部工具始终加载 | 小 | — |
| **P1** | [智能工具并行](./tool-parallelism-deep-dive.md) — 连续只读工具并行执行，代码探索快 5-10× [↓](./qwen-code-improvement-report-p0-p1-core.md#item-7) | 除 Agent 外全部顺序 | 小 | [PR#2864](https://github.com/QwenLM/qwen-code/pull/2864) |
| **P1** | [启动优化](./startup-optimization-deep-dive.md) — TCP preconnect + 启动期间键盘捕获不丢失 [↓](./qwen-code-improvement-report-p0-p1-core.md#item-8) | 完全缺失 | 小 | — |
| **P1** | [指令条件规则](./instruction-loading-deep-dive.md) — 按文件路径匹配加载不同编码规范 [↓](./qwen-code-improvement-report-p0-p1-core.md#item-9) | 所有指令始终加载 | 中 | — |
| **P1** | [Commit Attribution](./git-workflow-session-deep-dive.md) — git commit 中标注 AI vs 人类代码贡献比例 [↓](./qwen-code-improvement-report-p0-p1-core.md#item-12) | 缺失 | 小 | — |
| **P1** | [会话分支](./git-workflow-session-deep-dive.md) — /branch 从任意节点 fork 对话，探索替代方案 [↓](./qwen-code-improvement-report-p0-p1-core.md#item-13) | 缺失 | 中 | — |
| **P1** | GitHub Actions CI — 自动 PR 审查/issue 分类 action [↓](./qwen-code-improvement-report-p0-p1-platform.md#item-1) | 缺失 | 中 | — |
| **P1** | GitHub Code Review — 多 Agent自动 PR review + inline 评论 [↓](./qwen-code-improvement-report-p0-p1-platform.md#item-2) | 缺失 | 大 | — |
| **P1** | [HTTP Hooks](./http-hooks-deep-dive.md) — Hook 可 POST JSON 到 URL 并接收响应（不仅 shell 命令）[↓](./qwen-code-improvement-report-p0-p1-platform.md#item-3) | 仅 shell 命令 | 小 | — |
| **P1** | [Ghost Text 输入补全](./ghost-text-completion-deep-dive.md) — 输入时显示命令/路径建议灰字，Tab 接受 [↓](./qwen-code-improvement-report-p0-p1-platform.md#item-10) | 缺失 | 中 | — |
| **P1** | [Structured Output](./structured-output-deep-dive.md) — `--json-schema` 强制 JSON Schema 验证输出 [↓](./qwen-code-improvement-report-p0-p1-platform.md#item-4) | 缺失 | 小 | — |
| **P1** | Agent SDK 增强 — Python SDK + 流式回调 + 工具审批回调（Qwen 仅 TS SDK）[↓](./qwen-code-improvement-report-p0-p1-platform.md#item-5) | 仅 TypeScript SDK | 中 | — |
| **P1** | [Bare Mode](./bare-mode-deep-dive.md) — `--bare` 跳过所有自动发现，CI/脚本最快启动 [↓](./qwen-code-improvement-report-p0-p1-platform.md#item-6) | 缺失 | 小 | — |
| **P1** | [Remote Control Bridge](./remote-control-bridge-deep-dive.md) — 从手机/浏览器驱动本地终端 session [↓](./qwen-code-improvement-report-p0-p1-platform.md#item-7) | 缺失 | 大 | — |
| **P1** | [/teleport 跨端双向迁移](./teleport-session-migration-deep-dive.md) — Web session → 终端 session 双向迁移 [↓](./qwen-code-improvement-report-p0-p1-platform.md#item-8) | 缺失 | 大 | — |
| **P1** | GitLab CI/CD — 官方 GitLab pipeline 集成 [↓](./qwen-code-improvement-report-p0-p1-platform.md#item-9) | 缺失 | 中 | — |
| **P1** | [流式工具执行流水线](./streaming-tool-execution-deep-dive.md) — API 流式返回 tool_use 时立即开始执行，不等完整响应 [↓](./qwen-code-improvement-report-p0-p1-engine.md#item-1) | 等完整响应后执行 | 中 | — |
| **P1** | [文件读取缓存 + 批量并行 I/O](./file-read-cache-deep-dive.md) — 1000 条 LRU + mtime 失效 + 32 批并行 [↓](./qwen-code-improvement-report-p0-p1-engine.md#item-2) | 无缓存，顺序读取 | 小 | — |
| **P1** | 记忆/附件异步prefetch — 工具执行期间并行搜索相关记忆 [↓](./qwen-code-improvement-report-p0-p1-engine.md#item-3) | 无prefetch | 中 | — |
| **P1** | [Token Budget 续行与自动交接](./token-budget-continuation-deep-dive.md) — 90% 续行 + 递减检测 + 分层压缩回退 [↓](./qwen-code-improvement-report-p0-p1-engine.md#item-4) | 70% 一次性压缩 | 中 | — |
| **P1** | 同步 I/O 异步化 — readFileSync/statSync 替换为 async，解阻塞事件循环 [↓](./qwen-code-improvement-report-p0-p1-engine.md#item-5) | 多处 readFileSync | 中 | — |
| **P1** | [Prompt Cache 分段与工具稳定排序](./prompt-cache-optimization-deep-dive.md) — static/dynamic 分界 + 内置工具前缀 + schema 锁定 [↓](./qwen-code-improvement-report-p0-p1-engine.md#item-6) | 无分段缓存 | 中 | — |
| **P1** | [API 指数退避与降级重试](./api-retry-fallback-deep-dive.md) — 10 次退避 + 529 模型降级 + 401 token 刷新 [↓](./qwen-code-improvement-report-p0-p1-engine.md#item-8) | 仅配置重试次数 | 中 | — |
| **P1** | [优雅关闭序列与信号处理](./graceful-shutdown-deep-dive.md) — SIGINT/SIGTERM + 清理注册 + 5s failsafe [↓](./qwen-code-improvement-report-p0-p1-engine.md#item-9) | 无信号处理 | 中 | — |
| **P1** | [反应式压缩](./reactive-compression-deep-dive.md) — prompt_too_long 自动裁剪最早消息 + 重试 3 次 [↓](./qwen-code-improvement-report-p0-p1-engine.md#item-10) | 无被动恢复 | 中 | — |
| **P1** | [持久化重试模式](./persistent-retry-deep-dive.md) — CI/后台无限重试 + 5min 退避上限 + 30s 心跳 [↓](./qwen-code-improvement-report-p0-p1-engine.md#item-11) | 失败即退出 | 中 | — |
| **P1** | [原子文件写入与事务回滚](./atomic-file-write-deep-dive.md) — temp+rename 原子写 + 大结果persist to disk [↓](./qwen-code-improvement-report-p0-p1-engine.md#item-12) | 直接 writeFileSync | 中 | — |
| **P1** | 自动检查点默认启用 — 每轮工具执行后自动创建文件快照 [↓](./qwen-code-improvement-report-p0-p1-engine.md#item-13) | 检查点默认关闭 | 小 | — |
| **P1** | Coordinator/Swarm 多 Agent编排 — Leader/Worker 团队 + 3 种执行后端 [↓](./qwen-code-improvement-report-p0-p1-engine.md#item-14) | 仅 Arena 竞赛 | 大 | — |
| **P1** | [Task Management 任务协同与跨进程并发调度](./task-management-deep-dive.md) — 支持 blocks/blockedBy 的任务拓扑、跨进程安全锁与 Swarm 集成 [↓](./qwen-code-improvement-report-p0-p1-engine.md#item-25) | 仅提供简易无状态 TodoWriteTool | 大 | — |
| **P1** | [Agent 工具细粒度访问控制](./agent-tool-access-control-deep-dive.md) — 3 层allowlist/denylist + per-agent 限制 [↓](./qwen-code-improvement-report-p0-p1-engine.md#item-15) | 全部或指定列表 | 中 | — |
| **P1** | [InProcess 同进程多 Agent隔离](./in-process-agent-isolation-deep-dive.md) — AsyncLocalStorage 上下文隔离 [↓](./qwen-code-improvement-report-p0-p1-engine.md#item-16) | 全局状态可能泄漏 | 中 | — |
| **P1** | [Agent 记忆持久化](./agent-memory-persistence-deep-dive.md) — user/project/local 3 级跨 session 记忆 [↓](./qwen-code-improvement-report-p0-p1-engine.md#item-17) | 无跨 session 记忆 | 中 | — |
| **P1** | Agent 恢复与续行 — SendMessage 继续已完成代理 + transcript 重建 [↓](./qwen-code-improvement-report-p0-p1-engine.md#item-18) | 执行完即销毁 | 中 | — |
| **P1** | 系统提示模块化组装 — sections 缓存 + dynamic boundary + uncached 标记 [↓](./qwen-code-improvement-report-p0-p1-engine.md#item-19) | 单一字符串 | 中 | — |
| **P1** | 系统提示内容完善 — OWASP 安全 + prompt injection检测 + 代码风格约束 + 输出格式 [↓](./qwen-code-improvement-report-p0-p1-engine.md#item-24) | 缺少具体指导 | 中 | — |
| **P1** | [@include 指令与嵌套记忆发现](./nested-memory-include-deep-dive.md) — @path 递归引用 + 文件操作触发目录遍历 [↓](./qwen-code-improvement-report-p0-p1-engine.md#item-20) | 无 @include/嵌套发现 | 中 | — |
| **P1** | [附件类型协议与令牌预算](./attachment-protocol-budget-deep-dive.md) — 40+ 类型 + per-type 预算 + 3 阶段有序执行 [↓](./qwen-code-improvement-report-p0-p1-engine.md#item-21) | 字符串拼接/无预算 | 中 | — |
| **P1** | Thinking 块跨轮保留与空闲清理 — 活跃保留 + 1h 空闲清理 + latch 防缓存破坏 [↓](./qwen-code-improvement-report-p0-p1-engine.md#item-22) | 每轮独立/无清理 | 中 | [PR#2897](https://github.com/QwenLM/qwen-code/pull/2897) |
| **P1** | 输出 Token 自适应升级 — 8K 默认 + max_tokens 截断时自动 64K 重试 [↓](./qwen-code-improvement-report-p0-p1-engine.md#item-23) | 固定值/不重试 | 小 | [PR#2898](https://github.com/QwenLM/qwen-code/pull/2898) |
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
| **P2** | [`/context` 非交互输出](./context-usage-noninteractive-deep-dive.md) — 将上下文诊断暴露给脚本、CI 与外部控制器 [↓](./qwen-code-improvement-report-p2-tools.md#item-41) | 仅交互式 | 小 | — |
| **P1** | [Team Memory](./team-memory-deep-dive.md) — 团队共享项目知识 + 29 条 gitleaks 密钥扫描 + ETag 同步 [↓](./qwen-code-improvement-report-p0-p1-core.md#item-10) | 缺失 | 大 | — |
| **P2** | Plan 模式 Interview — 先收集信息再制定计划，分离探索和规划阶段 [↓](./qwen-code-improvement-report-p2-core.md#item-12) | 无 interview 阶段 | 中 | — |
| **P2** | BriefTool — Agent 向用户发送异步消息（含附件），不中断工具执行 [↓](./qwen-code-improvement-report-p2-core.md#item-13) | 缺失 | 中 | — |
| **P2** | [SendMessageTool](./multi-agent-deep-dive.md) — 多 Agent间消息传递、shutdown 请求、plan 审批 [↓](./qwen-code-improvement-report-p2-core.md#item-14) | 缺失 | 中 | — |
| **P2** | FileIndex — fzf 风格模糊文件搜索 + 异步增量索引 [↓](./qwen-code-improvement-report-p2-core.md#item-15) | 依赖 rg/glob | 中 | — |
| **P2** | Notebook Edit — Jupyter cell 编辑 + 自动 cell ID 追踪 + 文件历史快照 [↓](./qwen-code-improvement-report-p2-core.md#item-16) | 缺失 | 中 | — |
| **P2** | 自定义快捷键 — multi-chord 组合键 + 跨平台适配 + `keybindings.json` 自定义 [↓](./qwen-code-improvement-report-p2-core.md#item-17) | 缺失 | 中 | — |
| **P2** | Session Ingress Auth — 远程会话 bearer token 认证（企业多用户环境） [↓](./qwen-code-improvement-report-p2-core.md#item-18) | 缺失 | 中 | — |
| **P2** | 企业代理 — CONNECT relay + CA cert 注入 + NO_PROXY allowlist（容器环境） [↓](./qwen-code-improvement-report-p2-core.md#item-19) | 缺失 | 大 | — |
| **P2** | ConfigTool — 模型通过工具读写设置（主题/模型/权限等），带 schema 验证 [↓](./qwen-code-improvement-report-p2-core.md#item-20) | 仅 /settings 命令 | 小 | — |
| **P2** | 终端主题检测 — OSC 11 查询 dark/light + COLORFGBG 环境变量回退 [↓](./qwen-code-improvement-report-p2-core.md#item-21) | 缺失 | 小 | — |
| **P2** | 自动后台化 Agent — 超过阈值自动转后台执行，不阻塞用户交互 [↓](./qwen-code-improvement-report-p2-core.md#item-22) | 需显式指定 | 小 | — |
| **P2** | Denial Tracking — 连续权限拒绝自动回退到手动确认模式，防止静默阻塞 [↓](./qwen-code-improvement-report-p2-core.md#item-7) | 缺失 | 小 | — |
| **P2** | [队列输入编辑](./input-queue-deep-dive.md) — 排队中的指令可通过方向键弹出到输入框重新编辑 [↓](./qwen-code-improvement-report-p2-core.md#item-23) | 缺失 | 小 | [PR#2871](https://github.com/QwenLM/qwen-code/pull/2871) |
| **P2** | 状态栏紧凑布局 — 固定高度不伸缩，最大化终端内容区域 [↓](./qwen-code-improvement-report-p2-core.md#item-24) | Footer 占用偏高 | 小 | — |
| **P2** | 会话标签与搜索 — /tag 命令打标签 + 按标签/仓库/标题搜索历史会话 [↓](./qwen-code-improvement-report-p2-core.md#item-25) | 仅按时间排序 | 小 | — |
| **P2** | Conditional Hooks — Hook `if` 字段用权限规则语法按工具/路径过滤 [↓](./qwen-code-improvement-report-p2-tools.md#item-1) | 缺失 | 小 | — |
| **P2** | Transcript Search — 按 `/` 搜索会话记录，`n`/`N` 导航匹配项 [↓](./qwen-code-improvement-report-p2-tools.md#item-2) | 缺失 | 小 | — |
| **P2** | [Bash File Watcher](./file-watcher-stale-edit-deep-dive.md) — 检测 formatter/linter 修改已读文件，防止 stale-edit [↓](./qwen-code-improvement-report-p2-tools.md#item-3) | 缺失 | 小 | — |
| **P2** | /batch 并行操作 — 编排大规模并行变更（多文件/多任务）[↓](./qwen-code-improvement-report-p2-tools.md#item-4) | 缺失 | 中 | — |
| **P2** | Chrome Extension — 调试 live web 应用（读 DOM/Console/Network）[↓](./qwen-code-improvement-report-p2-tools.md#item-5) | 缺失 | 中 | — |
| **P2** | MCP Auto-Reconnect — 连续 3 次错误自动重连 + SSE 断线恢复 [↓](./qwen-code-improvement-report-p2-tools.md#item-13) | 缺失 | 小 | — |
| **P2** | Tool Result 大小限制 — 超限结果持久化到磁盘，发文件路径给模型 [↓](./qwen-code-improvement-report-p2-tools.md#item-14) | 缺失 | 小 | — |
| **P2** | Output Token 升级重试 — 首次 8K 截断后自动 64K 重试 [↓](./qwen-code-improvement-report-p2-tools.md#item-15) | 缺失 | 小 | — |
| **P2** | [Ripgrep 三级回退](./ripgrep-fallback-deep-dive.md) — System→Embedded→Builtin + EAGAIN 单线程重试 [↓](./qwen-code-improvement-report-p2-tools.md#item-16) | 缺失 | 小 | — |
| **P2** | MAGIC DOC 自更新文档 — 空闲时 Agent 自动更新标记文件的内容 [↓](./qwen-code-improvement-report-p2-tools.md#item-17) | 缺失 | 中 | — |
| **P2** | 目录/文件路径补全 — 输入路径时 Tab 补全 + LRU 缓存 [↓](./qwen-code-improvement-report-p2-tools.md#item-18) | 缺失 | 小 | — |
| **P2** | 上下文 Tips 系统 — 根据配置/IDE/插件状态显示上下文相关提示 [↓](./qwen-code-improvement-report-p2-tools.md#item-19) | 缺失 | 小 | — |
| **P2** | 权限对话框文件预览 — 审批时展示文件内容 + 语法高亮 + 上下文说明 [↓](./qwen-code-improvement-report-p2-tools.md#item-20) | 缺失 | 中 | — |
| **P2** | Token 使用实时警告 — 显示 token 用量 + 压缩进度 + 错误计数 [↓](./qwen-code-improvement-report-p2-tools.md#item-21) | 仅基础显示 | 小 | — |
| **P2** | 快捷键提示组件 — UI 全局统一显示当前操作的键盘快捷方式 [↓](./qwen-code-improvement-report-p2-tools.md#item-22) | 缺失 | 小 | — |
| **P2** | 终端完成通知 — 后台任务完成时 iTerm2/Kitty/Ghostty OSC 通知 + 进度百分比 [↓](./qwen-code-improvement-report-p2-tools.md#item-23) | 仅 bell | 小 | — |
| **P2** | Spinner 工具名 + 计时 — 显示"正在执行 Bash(npm test) · 15s"而非通用 spinner [↓](./qwen-code-improvement-report-p2-tools.md#item-24) | 通用 Responding | 小 | — |
| **P2** | /rewind 检查点回退 — 会话内代码 + 对话恢复到之前的检查点 [↓](./qwen-code-improvement-report-p2-tools.md#item-25) | 缺失 | 中 | — |
| **P2** | /copy OSC 52 剪贴板 — 复制代码块到剪贴板，OSC 52 + temp 文件回退 [↓](./qwen-code-improvement-report-p2-tools.md#item-26) | 缺失 | 小 | — |
| **P2** | 首次运行引导向导 — 主题/认证/API Key/安全/终端设置多步引导 [↓](./qwen-code-improvement-report-p2-tools.md#item-27) | 缺失 | 中 | — |
| **P2** | /doctor 诊断工具 — 系统环境检查（git/node/shell/权限/代理）[↓](./qwen-code-improvement-report-p2-tools.md#item-28) | 缺失 | 小 | — |
| **P2** | 结构化 Diff 渲染 — Rust NAPI 快速着色 + 行号 gutter + 语法高亮 [↓](./qwen-code-improvement-report-p2-tools.md#item-29) | 基础 inline diff | 中 | — |
| **P2** | Slash Command 命名空间治理 — source namespace + reserved names + 来源透明 [↓](./qwen-code-improvement-report-p2-tools.md#item-30) | 后者覆盖前者 | 中 | — |
| **P2** | /plan 计划模式 — Agent 只分析不动手 + 用户确认后执行 [↓](./qwen-code-improvement-report-p2-tools.md#item-31) | 无计划模式 | 小 | — |
| **P2** | /rename 重命名会话 — 手动修改会话标题 [↓](./qwen-code-improvement-report-p2-tools.md#item-32) | AI 自动标题不可改 | 小 | — |
| **P2** | /upgrade 版本升级 — changelog 展示 + 一键更新 [↓](./qwen-code-improvement-report-p2-tools.md#item-33) | 手动 npm update | 小 | — |
| **P2** | Plugin 系统增强 — 聚合容器（commands+skills+hooks+MCP）+ 一键安装/卸载 [↓](./qwen-code-improvement-report-p2-tools.md#item-34) | extension 分散管理 | 中 | — |
| **P2** | 文件编辑引号风格保留 — preserveQuoteStyle() 检测并保持原文件引号风格 [↓](./qwen-code-improvement-report-p2-tools.md#item-35) | 直接替换不保留 | 小 | — |
| **P2** | 文件编辑等价性判断 — areFileEditsInputsEquivalent() 跳过重复编辑 [↓](./qwen-code-improvement-report-p2-tools.md#item-36) | 重复编辑也执行 | 小 | — |
| **P2** | MCP 通道权限管理 — channel plugin allowlist + GrowthBook gate [↓](./qwen-code-improvement-report-p2-tools.md#item-37) | 无 plugin allowlist | 小 | — |
| **P2** | 消息类型丰富化 — 11 种 → 30+ 种 SDK 消息类型 [↓](./qwen-code-improvement-report-p2-tools.md#item-38) | ~11 种 | 中 | — |
| **P2** | /clear 多模式增强 — 清屏/清对话/完全重置三种力度 [↓](./qwen-code-improvement-report-p2-tools.md#item-39) | 仅清屏 | 小 | — |
| **P2** | /thinkback 会话回忆 — 时间线式关键事件回顾 + 时间/主题过滤 [↓](./qwen-code-improvement-report-p2-tools.md#item-40) | 仅即时摘要 | 小 | — |
| **P2** | /effort — 设置模型 effort 级别（○ 低 / ◐ 中 / ● 高）[↓](./qwen-code-improvement-report-p2-tools.md#item-6) | 缺失 | 小 | — |
| **P2** | Status Line 自定义 — shell 脚本在状态栏展示自定义信息 [↓](./qwen-code-improvement-report-p2-tools.md#item-7) | 缺失 | 小 | — |
| **P2** | 终端渲染优化 — DEC 2026 同步输出 + 差分渲染 + 双缓冲 + DECSTBM 硬件滚动 + 缓存池化 + alt-screen [↓](./qwen-code-improvement-report-p2-tools.md#item-8) | 仅消息拆分防闪烁 | 大 | — |
| **P2** | Image [Image #N] Chips — 粘贴图片后生成位置引用标记 [↓](./qwen-code-improvement-report-p2-tools.md#item-9) | 缺失 | 小 | — |
| **P2** | --max-turns — headless 模式最大 turn 数限制 [↓](./qwen-code-improvement-report-p2-tools.md#item-10) | 缺失 | 小 | — |
| **P2** | --max-budget-usd — headless 模式 USD 花费上限 [↓](./qwen-code-improvement-report-p2-tools.md#item-11) | 缺失 | 小 | — |
| **P2** | Connectors — 托管式 MCP 连接（GitHub/Slack/Linear/Google Drive OAuth）[↓](./qwen-code-improvement-report-p2-tools.md#item-12) | 缺失 | 大 | — |
| **P2** | MCP 并行连接 — pMap 动态插槽调度 + 双层并发（local:3/remote:20）[↓](./qwen-code-improvement-report-p2-perf.md#item-1) | 已并行但无并发上限 | 小 | — |
| **P2** | 插件/Skill 并行加载 — marketplace + session 双源并行 + 目录检查并行 [↓](./qwen-code-improvement-report-p2-perf.md#item-2) | 顺序 for 循环 | 小 | — |
| **P2** | Speculation 流水线建议 — 投机完成后立即并行生成下一建议 [↓](./qwen-code-improvement-report-p2-perf.md#item-3) | 每次重新生成 | 小 | — |
| **P2** | [write-through缓存与 TTL 后台刷新](./memoize-ttl-cache-deep-dive.md) — stale-while-revalidate + LRU 有界缓存 [↓](./qwen-code-improvement-report-p2-perf.md#item-4) | 无通用缓存模式 | 小 | — |
| **P2** | 上下文收集并行化 — 多源附件 Promise.all 并行获取（~20 并发）[↓](./qwen-code-improvement-report-p2-perf.md#item-5) | 串行追加 | 小 | — |
| **P2** | 输出缓冲与防阻塞渲染 — setImmediate 延迟写入 + 内存缓冲 [↓](./qwen-code-improvement-report-p2-perf.md#item-6) | 直接 appendFileSync | 小 | — |
| **P2** | [LSP 服务器并行启动](./lsp-parallel-startup-deep-dive.md) — Promise.all 并行启动 + Promise.race 端口探测 [↓](./qwen-code-improvement-report-p2-perf.md#item-7) | 顺序 for 循环 | 小 | — |
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
| **P2** | Markdown 表格终端渲染 — ANSI-aware + CJK-aware 列宽计算 [↓](./qwen-code-improvement-report-p2-stability.md#item-10) | CJK 列错位 | 小 | — |
| **P2** | 屏幕阅读器无障碍支持 — Diff/Spinner/Progress 纯文本替代渲染 [↓](./qwen-code-improvement-report-p2-stability.md#item-11) | hook 存在但使用有限 | 小 | — |
| **P2** | 色觉无障碍主题 — daltonized 红绿→蓝橙 diff 色板 [↓](./qwen-code-improvement-report-p2-stability.md#item-12) | 无色觉主题 | 小 | — |
| **P2** | 动画系统与卡顿状态检测 — shimmer 微光 + 30s 超时变红 [↓](./qwen-code-improvement-report-p2-stability.md#item-13) | 固定动画/无超时检测 | 小 | — |
| **P2** | Agent 权限冒泡 — bubble 模式 + Leader 桥接 + 邮箱回退 [↓](./qwen-code-improvement-report-p2-stability.md#item-14) | 继承父级模式 | 中 | — |
| **P2** | Agent 专属 MCP 服务器 — frontmatter mcpServers + 按需连接/清理 [↓](./qwen-code-improvement-report-p2-stability.md#item-15) | 共享全局 MCP | 小 | — |
| **P2** | Agent 创建向导 — 11 步交互式向导 + AI 生成模式 [↓](./qwen-code-improvement-report-p2-stability.md#item-16) | 基础命令行创建 | 中 | — |
| **P2** | Agent 进度追踪与实时状态 — ProgressTracker + task-notification + kill 控制 [↓](./qwen-code-improvement-report-p2-stability.md#item-17) | 仅最终结果 | 中 | — |
| **P2** | Agent 邮箱系统 — 文件 IPC + lockfile + 单播/广播 [↓](./qwen-code-improvement-report-p2-stability.md#item-18) | 仅 Arena 文件 IPC | 中 | — |
| **P2** | cache_edits 增量缓存删除 — API 原地删除旧工具结果不破坏缓存前缀 [↓](./qwen-code-improvement-report-p2-perf.md#item-13) | 重建消息数组 | 小 | — |
| **P2** | 消息规范化与配对修复 — 合并连续 user + 修复孤立 tool_use/result + 100 媒体上限 [↓](./qwen-code-improvement-report-p2-perf.md#item-14) | 格式转换/无修复 | 中 | — |
| **P2** | Git 状态自动注入上下文 — gitBranch/cwd/platform/fileCount 每轮注入 [↓](./qwen-code-improvement-report-p2-perf.md#item-15) | 仅平台和日期 | 小 | — |
| **P2** | IDE 上下文注入与嵌套记忆触发 — 选区→目录规范自动注入 + 诊断双源收集 [↓](./qwen-code-improvement-report-p2-perf.md#item-16) | 无嵌套记忆触发 | 中 | — |
| **P2** | 图片压缩多策略流水线 — format→resize→quality 阶梯 + JPEG fallback [↓](./qwen-code-improvement-report-p2-perf.md#item-17) | 仅计算 token/不压缩 | 中 | — |
| **P2** | WeakRef/WeakMap 防止 GC 保留 — AbortController/渲染缓存/span 自动释放 [↓](./qwen-code-improvement-report-p2-perf.md#item-18) | 全部强引用 Map | 小 | — |
| **P2** | 环形缓冲区与磁盘溢出 — CircularBuffer + BoundedUUIDSet + 8MB 溢出 [↓](./qwen-code-improvement-report-p2-perf.md#item-19) | 无上限数据结构 | 小 | — |
| **P2** | [终端渲染字符串池化](./terminal-rendering-string-pooling-deep-dive.md) — CharPool/StylePool 整数 ID 替代字符串 [↓](./qwen-code-improvement-report-p2-perf.md#item-20) | Ink 标准渲染 | 小 | — |
| **P2** | 文件描述符与句柄追踪 — >100 handles / >500 fd 预警 [↓](./qwen-code-improvement-report-p2-perf.md#item-21) | 无追踪 | 小 | — |
| **P2** | Memoization cold start去重 — inFlight Map + TTL 后台刷新 + identity guard [↓](./qwen-code-improvement-report-p2-perf.md#item-22) | 无去重 | 小 | — |
| **P2** | 正则表达式编译缓存 — Hook/LS hot path new RegExp 缓存到 Map [↓](./qwen-code-improvement-report-p2-perf.md#item-23) | 每次重新编译 | 小 | — |
| **P2** | 搜索结果流式解析 — 流式逐行处理 + --max-count 提前终止 [↓](./qwen-code-improvement-report-p2-perf.md#item-24) | split('\n') 全量加载 | 小 | — |
| **P2** | React.memo 自定义相等性 — 消息组件防止击键重渲染（500ms→16ms）[↓](./qwen-code-improvement-report-p2-perf.md#item-25) | 需确认覆盖度 | 小 | — |
| **P2** | [Bun 原生 API 优化](./bun-native-api-optimization-deep-dive.md) — stringWidth/JSONL.parseChunk/argv0 dispatch [↓](./qwen-code-improvement-report-p2-perf.md#item-26) | Node.js 标准 API | 小 | — |
| **P2** | 行宽缓存与 Blit 屏幕 Diff — 4096-LRU + 未变化区域直接复制 [↓](./qwen-code-improvement-report-p2-perf.md#item-27) | 每帧完整重算 | 中 | — |
| **P2** | 编译时特性门控 — feature() 编译求值 + 死代码消除 [↓](./qwen-code-improvement-report-p2-perf.md#item-28) | 运行时 env 检查 | 小 | — |
| **P2** | Shell 环境快照 — 一次性捕获 aliases/functions/PATH + 会话级 memoize [↓](./qwen-code-improvement-report-p2-perf.md#item-29) | 每次 spawn 干净环境 | 中 | — |
| **P2** | Shell 输出文件直写 — stdout/stderr 直写 fd 绕过 JS + 1s 文件轮询 [↓](./qwen-code-improvement-report-p2-perf.md#item-30) | PTY + JSON.stringify | 中 | — |
| **P2** | [增量文件索引签名](./incremental-file-index-deep-dive.md) — .git/index mtime + FNV-1a 采样签名 <1ms [↓](./qwen-code-improvement-report-p2-perf.md#item-31) | SHA256 全量 hash | 小 | — |
| **P2** | Shell AST 解析缓存 — 同一命令 2 次解析→Map 缓存 [↓](./qwen-code-improvement-report-p2-perf.md#item-32) | 每次重新解析 | 小 | — |
| **P2** | 终端输出浅比较 — JSON.stringify O(n)→浅比较 O(1) + 脏行范围 [↓](./qwen-code-improvement-report-p2-perf.md#item-33) | JSON.stringify 深比较 | 小 | — |
| **P2** | Diff 渲染 useMemo — parseDiff 缓存 + Regex 模块级预编译 [↓](./qwen-code-improvement-report-p2-perf.md#item-34) | 每帧重新解析 | 小 | — |
| **P2** | 远程触发器 REST API — CRUD 定时远程 Agent + 云端 CCR 执行 [↓](./qwen-code-improvement-report-p2-stability.md#item-19) | 仅会话内 cron | 中 | — |
| **P2** | SDK 双向控制协议 — 权限回调 + 模型切换 + MCP 管理 + 文件回退 [↓](./qwen-code-improvement-report-p2-stability.md#item-20) | 基础 canUseTool 回调 | 中 | — |
| **P2** | CI 环境自动检测 — GitHub Actions/CircleCI/Jenkins 检测 + 上下文提取 [↓](./qwen-code-improvement-report-p2-stability.md#item-21) | 仅通用 CI 变量 | 小 | — |
| **P2** | PR Webhook 事件订阅 — review/CI 事件实时注入 Agent 对话 [↓](./qwen-code-improvement-report-p2-stability.md#item-22) | 一次性审查 | 中 | — |
| **P2** | UltraReview 远程深度审查 — 10-20 min CCR 审查 + 配额追踪 + 进度心跳 [↓](./qwen-code-improvement-report-p2-stability.md#item-23) | 本地审查 | 大 | — |
| **P2** | GitHub App 自动安装 — 一键生成 workflow YAML + 配置 secret + 创建 PR [↓](./qwen-code-improvement-report-p2-stability.md#item-24) | 手动配置 workflow | 中 | — |
| **P2** | Headless 性能剖析 — TTFT/turn latency/overhead 采样追踪 [↓](./qwen-code-improvement-report-p2-stability.md#item-25) | 无剖析 | 小 | — |
| **P2** | 退出码标准化与 Hook 唤醒 — exit 2 唤醒模型 + CI 语义文档 [↓](./qwen-code-improvement-report-p2-stability.md#item-26) | 有自定义码/无唤醒 | 小 | — |
| **P2** | 破坏性命令警告系统 — 8 种高风险 git 操作 + 权限对话框风险说明 [↓](./qwen-code-improvement-report-p2-stability.md#item-27) | 仅读写分类/无风险说明 | 小 | — |
| **P2** | 系统提示危险操作行为指导 — 4 类危险操作列举 + 行为准则 + 审批范围限定 [↓](./qwen-code-improvement-report-p2-stability.md#item-28) | 仅 "never push" 一条 | 小 | [PR#2889](https://github.com/QwenLM/qwen-code/pull/2889) |
| **P2** | Unicode sanitization与 ASCII 走私防御 — NFKC + 不可见字符剥离 + 递归sanitization [↓](./qwen-code-improvement-report-p2-stability.md#item-29) | 无sanitization | 中 | — |
| **P2** | sandbox运行时集成 — seatbelt/bubblewrap/Docker + 文件/网络限制 [↓](./qwen-code-improvement-report-p2-stability.md#item-30) | 可选/非默认 | 大 | — |
| **P2** | SSRF 防护 — 私有 IP 阻断 + IPv4-mapped + DNS rebinding 防护 [↓](./qwen-code-improvement-report-p2-stability.md#item-31) | 仅基础 isPrivateIp | 中 | — |
| **P2** | WebFetch 域名allowlist — 130+ 预批准域名 + 路径段边界匹配 [↓](./qwen-code-improvement-report-p2-stability.md#item-32) | 无内置allowlist | 小 | — |
| **P2** | 子进程环境变量清洗 — 30+ 敏感变量自动剥离 [↓](./qwen-code-improvement-report-p2-stability.md#item-33) | 继承完整环境 | 中 | — |
| **P2** | 工具输出密钥扫描 — 50+ gitleaks 规则 + 写入阻断 [↓](./qwen-code-improvement-report-p2-stability.md#item-34) | 无扫描 | 中 | — |
| **P2** | privilege escalation防护 — auto 模式 60+ 危险规则自动剥离 [↓](./qwen-code-improvement-report-p2-stability.md#item-35) | yolo 批准所有 | 中 | — |
| **P3** | [动态状态栏](./dynamic-status-bar-deep-dive.md) — 模型/工具可实时更新状态文本 [↓](./qwen-code-improvement-report-p3.md#item-1) | 仅静态 Footer | 小 | — |
| **P3** | [上下文折叠](./context-compression-deep-dive.md) — History Snip（Claude Code 自身仅 scaffolding，未完整实现） [↓](./qwen-code-improvement-report-p3.md#item-2) | 缺失 | 大 | — |
| **P3** | [内存诊断](./memory-diagnostics-deep-dive.md) — V8 heap dump + 1.5GB 阈值触发 + leak 建议 + smaps 分析 [↓](./qwen-code-improvement-report-p3.md#item-3) | 缺失 | 中 | — |
| **P3** | [Feature Gates](./feature-gates-deep-dive.md) — GrowthBook 远程特性开关 + A/B 测试 + 按事件动态采样 [↓](./qwen-code-improvement-report-p3.md#item-4) | 缺失 | 中 | — |
| **P3** | DXT/MCPB 插件包 — zip bomb 防护（512MB/文件，1GB 总量，50:1 压缩比限制） [↓](./qwen-code-improvement-report-p3.md#item-5) | 缺失 | 中 | — |
| **P3** | [/security-review](./security-review-command-deep-dive.md) — 基于 git diff 的安全审查命令，聚焦漏洞检测 [↓](./qwen-code-improvement-report-p3.md#item-6) | 缺失 | 小 | — |
| **P3** | Ultraplan — 启动远程 CCR 会话，用更强模型深度规划后回传结果 [↓](./qwen-code-improvement-report-p3.md#item-7) | 缺失 | 大 | — |
| **P3** | [Advisor 顾问模型](./advisor-model-deep-dive.md) — /advisor 配置副模型审查主模型输出，多模型协作 [↓](./qwen-code-improvement-report-p3.md#item-8) | 缺失 | 中 | — |
| **P3** | [Vim 完整实现](./vim-emulation-deep-dive.md) — motions + operators + textObjects + transitions 完整体系 [↓](./qwen-code-improvement-report-p3.md#item-9) | 基础 vim.ts | 中 | — |
| **P3** | [语音模式](./voice-mode-deep-dive.md) — push-to-talk 语音输入 + 流式 STT 转录 + 可重绑快捷键 [↓](./qwen-code-improvement-report-p3.md#item-10) | 缺失 | 大 | — |
| **P3** | [插件市场](./plugin-marketplace-lifecycle-deep-dive.md) — 插件发现、安装、版本管理 + 生命周期治理 [↓](./qwen-code-improvement-report-p3.md#item-11) | 缺失 | 大 | — |
| **P3** | [sandbox excludedCommands](./sandbox-excluded-commands-deep-dive.md) — 安全命令排除 sandbox 限制 [↓](./qwen-code-improvement-report-p3.md#item-12) | 无排除机制 | 小 | — |
| **P3** | /privacy-settings 交互式隐私对话框 [↓](./qwen-code-improvement-report-p3.md#item-13) | 无交互 UI | 小 | — |
| **P3** | /extra-usage 企业用量管理 [↓](./qwen-code-improvement-report-p3.md#item-14) | 仅 /cost | 中 | — |
| **P3** | /rate-limit-options 限速选项菜单 [↓](./qwen-code-improvement-report-p3.md#item-15) | 仅错误消息 | 小 | — |
| **P3** | /remote-setup CCR 远程环境设置 [↓](./qwen-code-improvement-report-p3.md#item-16) | 无远程配置 | 中 | — |
| **P3** | Virtual Scrolling 虚拟滚动 — 仅渲染可视区域消息 [↓](./qwen-code-improvement-report-p3.md#item-17) | 全量渲染 | 中 | — |
| **P3** | [Feedback Survey 用户反馈](./feedback-survey-deep-dive.md) — 内置 /feedback 评分+文字表单 [↓](./qwen-code-improvement-report-p3.md#item-18) | 无内置反馈 | 小 | — |
| **P3** | [Turn Diffs 轮次差异统计](./turn-diffs-deep-dive.md) — 每轮变更文件数+增删行数汇总 [↓](./qwen-code-improvement-report-p3.md#item-19) | 仅 per-file diff | 小 | — |
| **P3** | LogoV2 品牌标识 — ASCII art + 启动功能引导 [↓](./qwen-code-improvement-report-p3.md#item-20) | 纯文本 | 小 | — |
| **P3** | [Buddy 伴侣精灵](./buddy-companion-deep-dive.md) — 可见助手 + 状态动画 + 空闲引导 [↓](./qwen-code-improvement-report-p3.md#item-21) | 无 | 中 | — |
| **P3** | [useMoreRight 右面板](./right-panel-ui-deep-dive.md) — 对话+文件预览并排显示 [↓](./qwen-code-improvement-report-p3.md#item-22) | 单列布局 | 中 | — |

> 点击改进点名称可跳转到 Deep-Dive 文章；每项的详细说明（缺失后果 + 改进收益 + 建议方案）见 [§三](#三全部改进点详细说明)。

## 三、全部改进点详细说明

按优先级分文件，点击查看每项的 Claude Code 实现机制、缺失后果、改进收益和建议方案：

| 文件 | 内容 | 项数 |
|------|------|:----:|
| [P0/P1 核心能力](./qwen-code-improvement-report-p0-p1-core.md) | 上下文压缩、Subagent、Speculation、记忆系统、工具并行、启动优化等 | 13 |
| [P0/P1 平台集成](./qwen-code-improvement-report-p0-p1-platform.md) | GitHub Actions CI、Code Review、SDK、Remote Control Bridge、GitLab 等 | 10 |
| [P0/P1 引擎优化](./qwen-code-improvement-report-p0-p1-engine.md) | 流式执行、缓存、Token 管理、崩溃恢复、Agent 编排、上下文管理、安全等 | 24 |
| [P2 核心功能与企业特性](./qwen-code-improvement-report-p2-core.md) | 中等优先级（Shell 安全、MDM 企业策略、Token 计数、Computer Use 等） | 24 |
| [P2 工具与命令扩展](./qwen-code-improvement-report-p2-tools.md) | 中等优先级（MCP 动态插槽、Ripgrep 回退、Notebook Edit、LSP 等） | 29 |
| [P2 性能优化](./qwen-code-improvement-report-p2-perf.md) | 中等优先级（流式执行、缓存模式、延迟初始化、请求合并等） | 34 |
| [P2 稳定性、安全与 CI/CD](./qwen-code-improvement-report-p2-stability.md) | 中等优先级（Unicode sanitization、sandbox集成、SSRF 防护、密钥扫描等） | 34 |
| [P3 详细说明](./qwen-code-improvement-report-p3.md) | 低优先级（Feature Gates、Vim、语音、插件市场等） | 11 |

## 四、架构差异总结

| 维度 | Claude Code | Qwen Code | 差距评估 | 进展 |
|------|-------------|-----------|----------|------|
| **Mid-Turn Queue Drain** | `query.ts` 工具批次间 drain | 无 | 显著落后 | [PR#2854](https://github.com/QwenLM/qwen-code/pull/2854) |
| 压缩 (Compression) 策略 | 4 层分层压缩 | 单一阈值压缩 | 显著落后 | — |
| Subagent | 支持 fork + 上下文继承 | 仅预定义类型 | 显著落后 | — |
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
| 多 Agent通信 | SendMessageTool | 无 | 缺失 | — |
| 文件索引 | FileIndex（fzf 风格） | 依赖 rg/glob | 中等差距 | — |
| Commit Attribution | Co-Authored-By 追踪 | 无 | 缺失 | — |
| 会话分支 | /branch 对话分叉 | 无 | 缺失 | — |
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
| **API 重试** | 10 次退避 + 529 降级 + 持久化重试 | 仅重试次数 | 显著落后 | — |
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
| Mid-Turn Queue Drain | [输入队列与中断机制](./input-queue-deep-dive.md) |
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
