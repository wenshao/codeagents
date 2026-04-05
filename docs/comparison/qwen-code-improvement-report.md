# Qwen Code 改进建议报告

> 基于对 Claude Code（源码分析，56 个顶层模块，~1800 文件）与 Qwen Code（开源源码，~500 文件）的系统性源码对比分析。
>
> **审计方法**: 五轮无方向 + 反方向 + 交叉审计（详见 [§六](#六审计方法说明)）。
>
> 如需查阅源码，可参考本地仓库（不在本文档库中）：
> - Claude Code: `../claude-code-leaked/`（反编译分析）
> - Qwen Code: `../qwen-code/`（开源）

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
| **P0** | 会话崩溃恢复与中断检测 — 3 种中断状态检测 + 合成续行 + 全量恢复 [↓](./qwen-code-improvement-report-p0-p1-engine.md#item-7) | 无崩溃恢复 | 大 | — |
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
| **P1** | HTTP Hooks — Hook 可 POST JSON 到 URL 并接收响应（不仅 shell 命令）[↓](./qwen-code-improvement-report-p0-p1-platform.md#item-3) | 仅 shell 命令 | 小 | — |
| **P1** | Ghost Text 输入补全 — 输入时显示命令/路径建议灰字，Tab 接受 [↓](./qwen-code-improvement-report-p0-p1-platform.md#item-10) | 缺失 | 中 | — |
| **P1** | Structured Output — `--json-schema` 强制 JSON Schema 验证输出 [↓](./qwen-code-improvement-report-p0-p1-platform.md#item-4) | 缺失 | 小 | — |
| **P1** | Agent SDK 增强 — Python SDK + 流式回调 + 工具审批回调（Qwen 仅 TS SDK）[↓](./qwen-code-improvement-report-p0-p1-platform.md#item-5) | 仅 TypeScript SDK | 中 | — |
| **P1** | Bare Mode — `--bare` 跳过所有自动发现，CI/脚本最快启动 [↓](./qwen-code-improvement-report-p0-p1-platform.md#item-6) | 缺失 | 小 | — |
| **P1** | [Remote Control Bridge](./remote-control-bridge-deep-dive.md) — 从手机/浏览器驱动本地终端 session [↓](./qwen-code-improvement-report-p0-p1-platform.md#item-7) | 缺失 | 大 | — |
| **P1** | /teleport — Web session → 终端 session 双向迁移 [↓](./qwen-code-improvement-report-p0-p1-platform.md#item-8) | 缺失 | 大 | — |
| **P1** | GitLab CI/CD — 官方 GitLab pipeline 集成 [↓](./qwen-code-improvement-report-p0-p1-platform.md#item-9) | 缺失 | 中 | — |
| **P1** | 流式工具执行流水线 — API 流式返回 tool_use 时立即开始执行，不等完整响应 [↓](./qwen-code-improvement-report-p0-p1-engine.md#item-1) | 等完整响应后执行 | 中 | — |
| **P1** | 文件读取缓存 + 批量并行 I/O — 1000 条 LRU + mtime 失效 + 32 批并行 [↓](./qwen-code-improvement-report-p0-p1-engine.md#item-2) | 无缓存，顺序读取 | 小 | — |
| **P1** | 记忆/附件异步prefetch — 工具执行期间并行搜索相关记忆 [↓](./qwen-code-improvement-report-p0-p1-engine.md#item-3) | 无prefetch | 中 | — |
| **P1** | Token Budget 续行与自动交接 — 90% 续行 + 递减检测 + 分层压缩回退 [↓](./qwen-code-improvement-report-p0-p1-engine.md#item-4) | 70% 一次性压缩 | 中 | — |
| **P1** | 同步 I/O 异步化 — readFileSync/statSync 替换为 async，解阻塞事件循环 [↓](./qwen-code-improvement-report-p0-p1-engine.md#item-5) | 多处 readFileSync | 中 | — |
| **P1** | Prompt Cache 分段与工具稳定排序 — static/dynamic 分界 + 内置工具前缀 + schema 锁定 [↓](./qwen-code-improvement-report-p0-p1-engine.md#item-6) | 无分段缓存 | 中 | — |
| **P1** | API 指数退避与降级重试 — 10 次退避 + 529 模型降级 + 401 token 刷新 [↓](./qwen-code-improvement-report-p0-p1-engine.md#item-8) | 仅配置重试次数 | 中 | — |
| **P1** | 优雅关闭序列与信号处理 — SIGINT/SIGTERM + 清理注册 + 5s failsafe [↓](./qwen-code-improvement-report-p0-p1-engine.md#item-9) | 无信号处理 | 中 | — |
| **P1** | 反应式压缩 — prompt_too_long 自动裁剪最早消息 + 重试 3 次 [↓](./qwen-code-improvement-report-p0-p1-engine.md#item-10) | 无被动恢复 | 中 | — |
| **P1** | 持久化重试模式 — CI/后台无限重试 + 5min 退避上限 + 30s 心跳 [↓](./qwen-code-improvement-report-p0-p1-engine.md#item-11) | 失败即退出 | 中 | — |
| **P1** | 原子文件写入与事务回滚 — temp+rename 原子写 + 大结果persist to disk [↓](./qwen-code-improvement-report-p0-p1-engine.md#item-12) | 直接 writeFileSync | 中 | — |
| **P1** | 自动检查点默认启用 — 每轮工具执行后自动创建文件快照 [↓](./qwen-code-improvement-report-p0-p1-engine.md#item-13) | 检查点默认关闭 | 小 | — |
| **P1** | Coordinator/Swarm 多 Agent编排 — Leader/Worker 团队 + 3 种执行后端 [↓](./qwen-code-improvement-report-p0-p1-engine.md#item-14) | 仅 Arena 竞赛 | 大 | — |
| **P1** | Agent 工具细粒度访问控制 — 3 层allowlist/denylist + per-agent 限制 [↓](./qwen-code-improvement-report-p0-p1-engine.md#item-15) | 全部或指定列表 | 中 | — |
| **P1** | InProcess 同进程多 Agent隔离 — AsyncLocalStorage 上下文隔离 [↓](./qwen-code-improvement-report-p0-p1-engine.md#item-16) | 全局状态可能泄漏 | 中 | — |
| **P1** | Agent 记忆持久化 — user/project/local 3 级跨 session 记忆 [↓](./qwen-code-improvement-report-p0-p1-engine.md#item-17) | 无跨 session 记忆 | 中 | — |
| **P1** | Agent 恢复与续行 — SendMessage 继续已完成代理 + transcript 重建 [↓](./qwen-code-improvement-report-p0-p1-engine.md#item-18) | 执行完即销毁 | 中 | — |
| **P1** | 系统提示模块化组装 — sections 缓存 + dynamic boundary + uncached 标记 [↓](./qwen-code-improvement-report-p0-p1-engine.md#item-19) | 单一字符串 | 中 | — |
| **P1** | 系统提示内容完善 — OWASP 安全 + prompt injection检测 + 代码风格约束 + 输出格式 [↓](./qwen-code-improvement-report-p0-p1-engine.md#item-24) | 缺少具体指导 | 中 | — |
| **P1** | @include 指令与嵌套记忆发现 — @path 递归引用 + 文件操作触发目录遍历 [↓](./qwen-code-improvement-report-p0-p1-engine.md#item-20) | 无 @include/嵌套发现 | 中 | — |
| **P1** | 附件类型协议与令牌预算 — 40+ 类型 + per-type 预算 + 3 阶段有序执行 [↓](./qwen-code-improvement-report-p0-p1-engine.md#item-21) | 字符串拼接/无预算 | 中 | — |
| **P1** | Thinking 块跨轮保留与空闲清理 — 活跃保留 + 1h 空闲清理 + latch 防缓存破坏 [↓](./qwen-code-improvement-report-p0-p1-engine.md#item-22) | 每轮独立/无清理 | 中 | — |
| **P1** | 输出 Token 自适应升级 — 8K 默认 + max_tokens 截断时自动 64K 重试 [↓](./qwen-code-improvement-report-p0-p1-engine.md#item-23) | 固定值/不重试 | 小 | — |
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
| **P1** | [Team Memory](./team-memory-deep-dive.md) — 团队共享项目知识 + 29 条 gitleaks 密钥扫描 + ETag 同步 [↓](./qwen-code-improvement-report-p0-p1-core.md#item-10) | 缺失 | 大 | — |
| **P2** | Plan 模式 Interview — 先收集信息再制定计划，分离探索和规划阶段 [↓](./qwen-code-improvement-report-p2-core.md#item-12) | 无 interview 阶段 | 中 | — |
| **P2** | BriefTool — Agent 向用户发送异步消息（含附件），不中断工具执行 [↓](./qwen-code-improvement-report-p2-core.md#item-13) | 缺失 | 中 | — |
| **P2** | [SendMessageTool](./multi-agent-deep-dive.md) — 多 Agent间消息传递、shutdown 请求、plan 审批 [↓](./qwen-code-improvement-report-p2-core.md#item-14) | 缺失 | 中 | — |
| **P2** | FileIndex — fzf 风格模糊文件搜索 + 异步增量索引 [↓](./qwen-code-improvement-report-p2-core.md#item-15) | 依赖 rg/glob | 中 | — |
| **P2** | Notebook Edit — Jupyter cell 编辑 + 自动 cell ID 追踪 + 文件历史快照 [↓](./qwen-code-improvement-report-p2-core.md#item-16) | 缺失 | 中 | — |
| **P2** |  [自定义快捷键](#custom-keybindings) — multi-chord 组合键 + 跨平台适配 + `keybindings.json` 自定义 [↓](./qwen-code-improvement-report-p2-core.md#item-17) | 缺失 | 中 | — |
| **P2** | Session Ingress Auth — 远程会话 bearer token 认证（企业多用户环境） [↓](./qwen-code-improvement-report-p2-core.md#item-18) | 缺失 | 中 | — |
| **P2** | 企业代理 — CONNECT relay + CA cert 注入 + NO_PROXY allowlist（容器环境） [↓](./qwen-code-improvement-report-p2-core.md#item-19) | 缺失 | 大 | — |
| **P2** | ConfigTool — 模型通过工具读写设置（主题/模型/权限等），带 schema 验证 [↓](./qwen-code-improvement-report-p2-core.md#item-20) | 仅 /settings 命令 | 小 | — |
| **P2** |  [终端主题检测](#terminal-theme) — OSC 11 查询 dark/light + COLORFGBG 环境变量回退 [↓](./qwen-code-improvement-report-p2-core.md#item-21) | 缺失 | 小 | — |
| **P2** |  [自动后台化 Agent](#auto-background) — 超过阈值自动转后台执行，不阻塞用户交互 [↓](./qwen-code-improvement-report-p2-core.md#item-22) | 需显式指定 | 小 | — |
| **P2** | Denial Tracking — 连续权限拒绝自动回退到手动确认模式，防止静默阻塞 [↓](./qwen-code-improvement-report-p2-core.md#item-7) | 缺失 | 小 | — |
| **P2** | [队列输入编辑](./input-queue-deep-dive.md) — 排队中的指令可通过方向键弹出到输入框重新编辑 [↓](./qwen-code-improvement-report-p2-core.md#item-23) | 缺失 | 小 | [PR#2871](https://github.com/QwenLM/qwen-code/pull/2871) |
| **P2** | 状态栏紧凑布局 — 固定高度不伸缩，最大化终端内容区域 [↓](./qwen-code-improvement-report-p2-core.md#item-24) | Footer 占用偏高 | 小 | — |
| **P2** | Conditional Hooks — Hook `if` 字段用权限规则语法按工具/路径过滤 [↓](./qwen-code-improvement-report-p2-tools.md#item-1) | 缺失 | 小 | — |
| **P2** | Transcript Search — 按 `/` 搜索会话记录，`n`/`N` 导航匹配项 [↓](./qwen-code-improvement-report-p2-tools.md#item-2) | 缺失 | 小 | — |
| **P2** | Bash File Watcher — 检测 formatter/linter 修改已读文件，防止 stale-edit [↓](./qwen-code-improvement-report-p2-tools.md#item-3) | 缺失 | 小 | — |
| **P2** | /batch 并行操作 — 编排大规模并行变更（多文件/多任务）[↓](./qwen-code-improvement-report-p2-tools.md#item-4) | 缺失 | 中 | — |
| **P2** | Chrome Extension — 调试 live web 应用（读 DOM/Console/Network）[↓](./qwen-code-improvement-report-p2-tools.md#item-5) | 缺失 | 中 | — |
| **P2** | MCP Auto-Reconnect — 连续 3 次错误自动重连 + SSE 断线恢复 [↓](./qwen-code-improvement-report-p2-tools.md#item-13) | 缺失 | 小 | — |
| **P2** | Tool Result 大小限制 — 超限结果持久化到磁盘，发文件路径给模型 [↓](./qwen-code-improvement-report-p2-tools.md#item-14) | 缺失 | 小 | — |
| **P2** | Output Token 升级重试 — 首次 8K 截断后自动 64K 重试 [↓](./qwen-code-improvement-report-p2-tools.md#item-15) | 缺失 | 小 | — |
| **P2** | Ripgrep 三级回退 — System→Embedded→Builtin + EAGAIN 单线程重试 [↓](./qwen-code-improvement-report-p2-tools.md#item-16) | 缺失 | 小 | — |
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
| **P2** | write-through缓存与 TTL 后台刷新 — stale-while-revalidate + LRU 有界缓存 [↓](./qwen-code-improvement-report-p2-perf.md#item-4) | 无通用缓存模式 | 小 | — |
| **P2** | 上下文收集并行化 — 多源附件 Promise.all 并行获取（~20 并发）[↓](./qwen-code-improvement-report-p2-perf.md#item-5) | 串行追加 | 小 | — |
| **P2** | 输出缓冲与防阻塞渲染 — setImmediate 延迟写入 + 内存缓冲 [↓](./qwen-code-improvement-report-p2-perf.md#item-6) | 直接 appendFileSync | 小 | — |
| **P2** | LSP 服务器并行启动 — Promise.all 并行启动 + Promise.race 端口探测 [↓](./qwen-code-improvement-report-p2-perf.md#item-7) | 顺序 for 循环 | 小 | — |
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
| **P2** |  [色觉无障碍主题](#colorblind-theme) — daltonized 红绿→蓝橙 diff 色板 [↓](./qwen-code-improvement-report-p2-stability.md#item-12) | 无色觉主题 | 小 | — |
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
| **P2** | 终端渲染字符串池化 — CharPool/StylePool 整数 ID 替代字符串 [↓](./qwen-code-improvement-report-p2-perf.md#item-20) | Ink 标准渲染 | 小 | — |
| **P2** | 文件描述符与句柄追踪 — >100 handles / >500 fd 预警 [↓](./qwen-code-improvement-report-p2-perf.md#item-21) | 无追踪 | 小 | — |
| **P2** | Memoization cold start去重 — inFlight Map + TTL 后台刷新 + identity guard [↓](./qwen-code-improvement-report-p2-perf.md#item-22) | 无去重 | 小 | — |
| **P2** | 正则表达式编译缓存 — Hook/LS hot path new RegExp 缓存到 Map [↓](./qwen-code-improvement-report-p2-perf.md#item-23) | 每次重新编译 | 小 | — |
| **P2** | 搜索结果流式解析 — 流式逐行处理 + --max-count 提前终止 [↓](./qwen-code-improvement-report-p2-perf.md#item-24) | split('\n') 全量加载 | 小 | — |
| **P2** | React.memo 自定义相等性 — 消息组件防止击键重渲染（500ms→16ms）[↓](./qwen-code-improvement-report-p2-perf.md#item-25) | 需确认覆盖度 | 小 | — |
| **P2** | Bun 原生 API 优化 — stringWidth/JSONL.parseChunk/argv0 dispatch [↓](./qwen-code-improvement-report-p2-perf.md#item-26) | Node.js 标准 API | 小 | — |
| **P2** | 行宽缓存与 Blit 屏幕 Diff — 4096-LRU + 未变化区域直接复制 [↓](./qwen-code-improvement-report-p2-perf.md#item-27) | 每帧完整重算 | 中 | — |
| **P2** | 编译时特性门控 — feature() 编译求值 + 死代码消除 [↓](./qwen-code-improvement-report-p2-perf.md#item-28) | 运行时 env 检查 | 小 | — |
| **P2** | Shell 环境快照 — 一次性捕获 aliases/functions/PATH + 会话级 memoize [↓](./qwen-code-improvement-report-p2-perf.md#item-29) | 每次 spawn 干净环境 | 中 | — |
| **P2** | Shell 输出文件直写 — stdout/stderr 直写 fd 绕过 JS + 1s 文件轮询 [↓](./qwen-code-improvement-report-p2-perf.md#item-30) | PTY + JSON.stringify | 中 | — |
| **P2** | 增量文件索引签名 — .git/index mtime + FNV-1a 采样签名 <1ms [↓](./qwen-code-improvement-report-p2-perf.md#item-31) | SHA256 全量 hash | 小 | — |
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
| **P2** |  [子进程环境变量清洗](#env-sanitization) — 30+ 敏感变量自动剥离 [↓](./qwen-code-improvement-report-p2-stability.md#item-33) | 继承完整环境 | 中 | — |
| **P2** | 工具输出 [密钥扫描](#secret-scanning) — 50+ gitleaks 规则 + 写入阻断 [↓](./qwen-code-improvement-report-p2-stability.md#item-34) | 无扫描 | 中 | — |
| **P2** | privilege escalation防护 — auto 模式 60+ 危险规则自动剥离 [↓](./qwen-code-improvement-report-p2-stability.md#item-35) | yolo 批准所有 | 中 | — |
| **P3** | 动态状态栏 — 模型/工具可实时更新状态文本 [↓](./qwen-code-improvement-report-p3.md#item-1) | 仅静态 Footer | 小 | — |
| **P3** | [上下文折叠](./context-compression-deep-dive.md) — History Snip（Claude Code 自身仅 scaffolding，未完整实现） [↓](./qwen-code-improvement-report-p3.md#item-2) | 缺失 | 大 | — |
| **P3** | 内存诊断 — V8 heap dump + 1.5GB 阈值触发 + leak 建议 + smaps 分析 [↓](./qwen-code-improvement-report-p3.md#item-3) | 缺失 | 中 | — |
| **P3** | Feature Gates — GrowthBook 远程特性开关 + A/B 测试 + 按事件动态采样 [↓](./qwen-code-improvement-report-p3.md#item-4) | 缺失 | 中 | — |
| **P3** | DXT/MCPB 插件包 — zip bomb 防护（512MB/文件，1GB 总量，50:1 压缩比限制） [↓](./qwen-code-improvement-report-p3.md#item-5) | 缺失 | 中 | — |
| **P3** | /security-review — 基于 git diff 的安全审查命令，聚焦漏洞检测 [↓](./qwen-code-improvement-report-p3.md#item-6) | 缺失 | 小 | — |
| **P3** | Ultraplan — 启动远程 CCR 会话，用更强模型深度规划后回传结果 [↓](./qwen-code-improvement-report-p3.md#item-7) | 缺失 | 大 | — |
| **P3** | Advisor 顾问模型 — /advisor 配置副模型审查主模型输出，多模型协作 [↓](./qwen-code-improvement-report-p3.md#item-8) | 缺失 | 中 | — |
| **P3** | Vim 完整实现 — motions + operators + textObjects + transitions 完整体系 [↓](./qwen-code-improvement-report-p3.md#item-9) | 基础 vim.ts | 中 | — |
| **P3** | 语音模式 — push-to-talk 语音输入 + 流式 STT 转录 + 可重绑快捷键 [↓](./qwen-code-improvement-report-p3.md#item-10) | 缺失 | 大 | — |
| **P3** | [插件市场](./hook-plugin-extension-deep-dive.md) — 插件发现、安装、版本管理 + 前端 UI [↓](./qwen-code-improvement-report-p3.md#item-11) | 缺失 | 大 | — |
| **P1** |  [系统提示模块化](#system-prompt-modular) — sections 缓存 + dynamic boundary + uncached 标记  | 单一字符串拼接 | 中 | — |
| **P1** |  [消息规范化](#message-normalization) — 合并连续 user + 修复孤立 tool_use/result  | 构造即正确，无需后处理 | 中 | — |
| **P2** |  [Git Worktree](#git-worktree) — gitWorktreeService.ts 已实现(826行)  | 已实现 | 小 | — |
| **P2** |  [REPL 沙箱](#repl-sandbox) — AST 读写分类已覆盖  | 已覆盖 | 中 | — |
| **P2** |  [工作流脚本](#workflow-scripts) — Hook 系统可替代  | 已覆盖 | 中 | — |
| **P2** |  [会话标签与搜索](#session-tags-search) — `/tag` 会话标签 + 按 repo/标题搜索  | 仅基础 load/save | 小 | — |
| **P2** |  [MCP OAuth](#mcp-oauth) — oauth-provider.ts 已实现(960行)  | 已实现 | 中 | — |
| **P2** |  [MCP 通道通知](#mcp-notification) — MCP channel notification 支持服务器主动推送  | mcp-client.ts 无 channel 概念 | 中 | — |
| **P3** |  [会话分支](#session-branch) — `/branch` 从历史会话创建分支  | 可用 sessionService 扩展 | 中 | — |
| **P3** |  [安全审查](#security-review) — skill 可快速补齐  | skill 可补齐 | 小 | — |
| **P3** |  [PR 评论](#pr-comments) — GitHub Actions 可实现  | Actions 可实现 | 中 | — |
| **P2** |  [@include 指令](#include-directive) — 递归引用 + 外部文件审批 + 40+ 文本类型白名单  | 缺失 | 中 | — |
| **P2** |  [附件协议](#attachment-protocol) — 60+ 类型 + per-type token 预算 + 3 阶段有序执行  | 缺失 | 中 | — |
| **P2** |  [图片压缩流水线](#image-compression) — format→resize→quality 阶梯 + JPEG fallback  | 无压缩 | 中 | — |
| **P2** |  [Git 状态自动注入](#git-status-injection) — gitBranch/cwd/fileCount 每轮自动注入系统提示  | 仅统计/不注入 | 小 | — |
| **P2** |  [IDE 诊断注入](#ide-diagnostics) — LSP 诊断自动收集 + 选区自动注入  | 依赖 IDE 推送 | 中 | — |
| **P2** |  [终端主题检测](#terminal-theme) — OSC 11 dark/light + COLORFGBG 回退  | 缺失 | 小 | — |
| **P2** |  [自动后台化 Agent](#auto-background) — 超时 15s 自动转后台 + Assistant 模式检测  | 需显式指定 | 小 | — |
| **P2** |  [密钥扫描](#secret-scanning) — 工具输出 50+ gitleaks 规则扫描 + 写入阻断  | 仅 Team Memory 场景需要 | 中 | — |
| **P2** |  [子进程环境变量清洗](#env-sanitization) — 30+ 敏感变量自动剥离  | OS 层职责 | 中 | — |
| **P2** |  [结构化 Diff](#structured-diff) — 纯 JS 快速着色 + 行号 gutter + 语法高亮  | 基础 inline diff | 中 | — |
| **P2** |  [OSC 通知](#osc-notifications) — iTerm2/Kitty/Ghostty 通知 + 进度  | 仅 bell 响铃 | 小 | — |
| **P2** |  [OSC 8 超链接](#osc-8) — Cmd+Click 打开文件/URL  | MarkdownRenderer.tsx 无 OSC 8 | 小 | — |
| **P2** |  [色觉无障碍主题](#colorblind-theme) — daltonized 红绿→蓝橙 diff 色板  | 小众需求 | 小 | — |
| **P2** |  [自定义快捷键](#custom-keybindings) — multi-chord + keybindings.json  | keyMatchers.ts 不可配置 | 中 | — |

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
| [P2 稳定性、安全与 CI/CD](./qwen-code-improvement-report-p2-stability.md) | 中等优先级（Unicode sanitization、sandbox集成、SSRF 防护、密钥扫描等） | 60 |
| [P3 详细说明](./qwen-code-improvement-report-p3.md) | 低优先级（Feature Gates、Vim、语音、插件市场等） | 30 |

## 四、架构差异总结

| 维度 | Claude Code | Qwen Code | 差距评估 | 进展 |
|------|-------------|-----------|----------|------|
| **Mid-Turn Queue Drain** | `query.ts` 工具批次间 drain | 无 | 显著落后 | [PR#2854](https://github.com/QwenLM/qwen-code/pull/2854) |
| 压缩 (Compression) 策略 | 4 层分层压缩 | 单一阈值压缩 | 显著落后 | — |
| Subagent | 支持 fork + 上下文继承 | 仅预定义类型 | 显著落后 | — |
| **智能工具并行** | Kind-based batching（默认 10 并发） | Agent 并发 / 其他顺序 | 中等差距 | [PR#2864](https://github.com/QwenLM/qwen-code/pull/2864) |
| 投机执行 (Speculation) | 完整 overlay-fs + cow（991 行） | v0.15.0 已完整实现（563 行），默认关闭 | 小差距 | [PR#2525](https://github.com/QwenLM/qwen-code/pull/2525) ✓ |
| 启动优化 | API Preconnect + Early Input | 无 | 缺失 | — |
| CLAUDE.md 条件规则 | frontmatter `paths:` + 惰加载 | 无条件加载 | 中等差距 | — |
| 系统提示模块化 | sections 缓存 + dynamic boundary | 单一字符串拼接 | 中等差距 | — |
| 消息规范化 | 合并连续 user + 修复孤立 tool_use | 构造即正确 | 小差距 | — |
| MCP Channel Notification | Channel notification 服务器推送 | 无 channel 概念 | 中等差距 | — |
| @include 指令 | 递归引用 + 外部审批 | 缺失 | 缺失 | — |
| 会话记忆 (Session Memory) | SessionMemory + memdir | 简单笔记工具 | 显著落后 | — |
| 自动记忆 (Memory) 整理 | Auto Dream | 无 | 缺失 | — |
| 上下文折叠 (Context Collapse) | History Snip | 无 | 缺失 | — |
| Shell 安全增强 | 25+ 检查 + tree-sitter | AST-only 读写分类 | 中等差距 | — |
| MDM 企业策略 | plist + Registry + 远程 API | 无 | 缺失 | — |
| Token 实时计数 | API 计数 + VCR 缓存 | 静态模式匹配 | 中等差距 | — |
| 工具发现 | ToolSearchTool | 无 | 缺失 | — |
| 多 Agent通信 | SendMessageTool | 无 | 缺失 | — |
| 任务管理 | TaskCreate/Get/Update/List/Output/Stop | todoWrite 已覆盖 | 小差距 | — |
| Team Agent Management | TeamCreateTool/TeamDeleteTool (Swarms) | Arena 模式更简洁 | 小差距 | — |
| 文件索引 | FileIndex（fzf 风格） | 依赖 rg/glob | 中等差距 | — |
| Commit Attribution | Co-Authored-By 追踪 | 无 | 缺失 | — |
| 会话分支 | /branch 对话分叉 | 无 | 缺失 | — |
| Output Styles | Learning / Explanatory 模式 | 无 | 缺失 | — |
| Fast Mode | 速度/成本分级推理 | 无 | 缺失 | — |
| 并发 Session | 多终端 PID 追踪 + 后台脱附 | 无 | 缺失 | — |
| Git Worktree | gitWorktreeService.ts 已实现 | 已实现 | 无差距 | — |
| REPL Sandbox | AST 读写分类已覆盖 | 已覆盖 | 无差距 | — |
| Workflow Scripts | Hook 系统可替代 | 已覆盖 | 无差距 | — |
| MCP OAuth | oauth-provider.ts 已实现(960行) | 已实现 | 无差距 | — |
| Session Tags & Search | `/tag` + 搜索 | 仅基础 load/save | 中等差距 | — |
| Git Status Auto-Injection | gitBranch/cwd/fileCount 每轮注入 | 仅统计/不注入 | 小差距 | — |
| IDE Diagnostics Injection | LSP 诊断自动收集 + 选区注入 | 依赖 IDE 推送 | 中等差距 | — |
| Terminal Theme Detection | OSC 11 + COLORFGBG 回退 | 缺失 | 小差距 | — |
| Auto-Background Agent | 超时 15s 自动转后台 | 需显式指定 | 小差距 | — |
| Thinking Block Retention | 跨轮保留 + 空闲清理 | 每轮独立 | 中等差距 | — |
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
| MCP OAuth | McpAuthTool + OAuth 端口管理 | 缺失 | 缺失 | — |
| MCP Channel Notification | Channel notification 服务器推送 | 缺失 | 缺失 | — |
| Privacy Protection | PII 脱敏 + Killswitch + 事件采样 | 无保护 | 显著落后 | — |
| Extended Hooks | FileChanged/ConfigChange/TaskLifecycle 等 | 仅基础 Hook | 中等差距 | — |
| Structured Diff | Rust NAPI + 行号 + 语法高亮 | 基础 inline diff | 中等差距 | — |
| Spinner Tool Timer | 工具名 + 单独计时 | 仅全局计时 | 小差距 | — |
| OSC Notifications | iTerm2/Kitty/Ghostty + 进度 | 仅 bell 响铃 | 小差距 | — |
| OSC 52 Clipboard | 复制代码 + tmux 回退 | 缺失 | 小差距 | — |
| OSC 8 Hyperlinks | Cmd+Click 打开文件/URL | 纯文本链接 | 小差距 | — |
| Colorblind Theme | daltonized 红绿→蓝橙 | 无专门主题 | 小差距 | — |
| Custom Keybindings | multi-chord + keybindings.json | 不可配置 | 中等差距 | — |
| Image Chips | [Image #N] 位置引用 | 附件形式 | 小差距 | — |
| Permission File Preview | 内容预览 + 语法高亮 | 基础确认 | 中等差距 | — |
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

## 六、审计方法说明

本报告采用 **五轮审计法** 确保结论完整性和客观性：

| 轮次 | 方法 | 目标 | 发现数 |
|------|------|------|:------:|
| **第一轮** | 无方向审计 | 全面扫描双方架构差异，不预设结论 | 87 项 |
| **第二轮** | 无方向审计 | 深入对比 10 大核心模块实现差异 | 43 项 |
| **第三轮** | 反方向审计 | 假设 Qwen Code 更优，找出其优势 | 7 项 |
| **第四轮** | 反方向审计 | 假设 Claude Code 更优，验证 Qwen Code 不足 | 已覆盖 |
| **第五轮** | 交叉审计 | 随机抽样验证前四轮结论的准确性 | 6 项确认 |

> **免责声明**: 审计基于 2026 年 Q1 源码快照，可能已过时。Claude Code 为闭源二进制，分析基于反编译结果，可能与实际行为有差异。

## 七、Qwen Code 优势分析

经第三轮反方向审计，确认 Qwen Code 在以下方面优于 Claude Code：

| 维度 | Qwen Code | Claude Code | 优势评估 |
|------|-----------|-------------|----------|
| **开源可审计** | 全部源码可审计（~500 文件） | 闭源 Bun 二进制（需反编译） | **显著优势** |
| **LSP 工具** | 12 种操作（含 diagnostics/codeActions） | 8 种操作 | **优势** |
| **代码简洁度** | ~500 文件，~17.7 万行 | ~1800 文件，~38 万行 | **维护成本低** |
| **记忆系统** | global + project 两级，文件透明 | 单级 MEMORY.md，自动管理 | **更可控** |
| **搜索提供商** | Google/Tavily/Dashscope 3 种 | 仅内置搜索 | **更灵活** |
| **多语言 SDK** | TypeScript + Java SDK | 仅 Node.js | **更广泛** |
| **IDE 扩展** | VS Code + Zed 编辑器 | 仅 Chrome 集成 | **更开放** |
| **/restore 命令** | 开源可验证的 checkpoint 恢复 | 闭源实现（不可审计） | **更透明** |

> **总结**: Qwen Code 的核心优势在于 **透明性、可审计性、代码简洁度** 和 **LSP 功能完整性**。Claude Code 的优势在于 **功能丰富度**（101 vs 38 命令）和 **企业特性**（durable cron、teammate 等）。

---


## 八、新增改进点详细说明

> 以下为五轮审计新增的 25 项改进点详细说明。**每项告诉你：改哪些文件、怎么改。**
> 原有改进点的详细说明见 [§三](#三全部改进点详细说明) 对应分文件。

---

<a id="git-worktree"></a>

### 1. Git Worktree（P2，已实现）

**结论**：`packages/core/src/services/gitWorktreeService.ts`（826行）已实现完整功能，无需改动。

---

<a id="repl-sandbox"></a>

### 2. REPL 沙箱（P2，已覆盖）

**结论**：`packages/core/src/utils/shellAstParser.ts` 的 AST 读写分类已覆盖 REPL 安全防护，无需单独实现 REPL 工具。

---

<a id="workflow-scripts"></a>

### 3. 工作流脚本（P2，Hook 可替代）

**结论**：`packages/core/src/hooks/` 已有 13 种 Hook 事件类型，可通过 Hook 链实现工作流，无需单独实现。

---

<a id="mcp-oauth"></a>

### 4. MCP OAuth（P2，已实现）

**结论**：`packages/core/src/tools/mcp-server-manager.ts` 中的 `oauth-provider.ts`（960行）+ `keychain-token-storage.ts` 已实现完整 OAuth，无需改动。

---

<a id="message-normalization"></a>

### 5. 消息规范化（P1，Qwen 已优）

**结论**：Qwen 采用"构造即正确"哲学，`converter.ts` 中 `cleanOrphanedToolCalls()` + `mergeConsecutiveAssistantMessages()` 已做轻量清理，无需重度规范化。

---

### 6. 会话标签与搜索（P2）

**做什么**：给会话打标签，支持按标签快速搜索。

**改哪些文件**：
- `packages/core/src/services/sessionService.ts` — 新增 `tags` 字段和搜索方法
- `packages/cli/src/ui/commands/tagCommand.ts` — 新建命令

**怎么改**：
```typescript
// sessionService.ts — 在 ChatSession 接口加 tags 字段
interface ChatSession {
  // ... 现有字段
  tags: string[];  // 新增
}

// 新增搜索方法
async searchByTags(tags: string[]): Promise<ChatSession[]> {
  const sessions = await this.listSessions();
  return sessions.filter(s => tags.every(t => s.tags.includes(t)));
}
```
```typescript
// cli/src/ui/commands/tagCommand.ts — 新建
// /tag add <tag> / /tag remove <tag> / /tag list / /tag search <tag>
// 复用现有 permissionsCommand 的模式
```

**改完后效果**：用户执行 `/tag add 重构` 后，会话被标记。后续 `/tag search 重构` 可快速找到所有重构相关会话。

---

### 7. MCP 通道通知（P2）

**做什么**：让 MCP 服务器能主动向客户端推送通知（如资源变更），减少轮询。

**改哪些文件**：
- `packages/core/src/tools/mcp-client.ts` — 新增 channel 订阅和通知处理

**怎么改**：
```typescript
// mcp-client.ts — 在 McpClient 类中新增
private notificationHandlers = new Map<string, (data: any) => void>();

// 订阅通知
subscribe(channel: string, handler: (data: any) => void) {
  this.notificationHandlers.set(channel, handler);
}

// 处理服务器推送
private handleNotification(method: string, params: any) {
  const handler = this.notificationHandlers.get(method);
  handler?.(params);
}
```

**改完后效果**：MCP 服务器资源变更时主动推送，延迟从轮询间隔（通常 30s）降到 <1s。

---

### 8. @include 指令（P2）

**做什么**：CLAUDE.md/AGENTS.md 中用 `@path` 引用其他文件，递归加载，最大深度 5 层。

**改哪些文件**：
- `packages/core/src/config/` — 指令加载器（具体文件名待确认，搜索 `CLAUDE.md` 加载逻辑）
- `packages/cli/src/ui/components/` — 外部文件审批对话框

**怎么改**：
```typescript
// 在指令加载器中新增 @include 解析
const INCLUDE_RE = /(?:^|\s)@((?:[^\s\\]|\\ )+)/g;

async function processIncludes(content: string, basePath: string, depth = 0): Promise<string> {
  if (depth >= 5) return content;  // 最大深度限制
  
  const includes = content.matchAll(INCLUDE_RE);
  for (const match of includes) {
    const path = match[1];
    const fullPath = resolve(basePath, path);
    // 外部文件需用户审批
    if (!isWithinProject(fullPath)) {
      const approved = await askUserApproval(fullPath);
      if (!approved) continue;
    }
    const included = await readFile(fullPath, 'utf-8');
    const processed = await processIncludes(included, fullPath, depth + 1);
    content = content.replace(match[0], processed);
  }
  return content;
}
```

**改完后效果**：团队规范可拆分为多个文件，用 `@coding-style.md` 引用，避免巨型单文件。

---

### 9. 附件协议（P2）

**做什么**：定义 60+ 附件类型（文件/IDE/内存/Hook 等），每类独立 token 预算，3 阶段有序执行。

**改哪些文件**：
- `packages/core/src/core/` — 附件类型枚举和预算配置
- `packages/core/src/core/client.ts` — 附件收集和执行流程

**怎么改**：
```typescript
// 新增附件类型枚举
enum AttachmentType {
  File = 'file',
  SelectedLines = 'selected_lines_in_ide',
  Diagnostics = 'diagnostics',
  Memory = 'nested_memory',
  // ... 60+ 类型
}

// 新增预算配置
const ATTACHMENT_BUDGETS = {
  [AttachmentType.File]: { maxLines: 200, maxBytes: 4096 },
  [AttachmentType.Memory]: { maxSessionBytes: 60 * 1024 },
  // ...
};

// 客户端收集附件时按预算截断
function collectAttachments(session: Session) {
  const budget = ATTACHMENT_BUDGETS[type];
  return truncateToBudget(rawContent, budget);
}
```

**改完后效果**：防止单一附件类型（如大量诊断信息）撑爆上下文窗口。

---

### 10. 图片压缩流水线（P2）

**做什么**：上传前压缩图片：PNG 调色板 → JPEG 质量阶梯 → 尺寸缩放。

**改哪些文件**：
- `packages/core/src/utils/imageUtils.ts` — 新建

**怎么改**：
```typescript
// 新建 imageUtils.ts
import sharp from 'sharp';

export async function compressImage(buffer: Buffer): Promise<Buffer> {
  // 阶段1：格式保留压缩
  let result = await sharp(buffer).png({ compressionLevel: 9, palette: true }).toBuffer();
  
  if (result.length > budget) {
    // 阶段2：尺寸缩放
    result = await sharp(buffer)
      .resize(2000, 2000, { fit: 'inside', withoutEnlargement: true })
      .jpeg({ quality: 80 })
      .toBuffer();
  }
  
  if (result.length > budget) {
    // 阶段3：激进压缩
    result = await sharp(buffer)
      .resize(400, 400)
      .jpeg({ quality: 20 })
      .toBuffer();
  }
  
  return result;
}
```

**改完后效果**：多图场景（截图分析）省 50-80% 图片 token。

---

### 11. Git 状态自动注入（P2）

**做什么**：每轮自动把 gitBranch/cwd/fileCount 注入系统提示，模型始终知道当前上下文。

**改哪些文件**：
- `packages/core/src/core/prompts.ts` — 系统提示中新增动态段
- `packages/core/src/utils/gitUtils.ts` — 复用现有 git 工具

**怎么改**：
```typescript
// prompts.ts — 在 getMainSessionSystemInstruction() 中新增
async function getGitContextSection(): Promise<string> {
  const branch = await getGitBranch();
  const fileCount = await countProjectFiles();
  return `## Current Context
Branch: ${branch}
Working directory: ${cwd}
Project files: ~${fileCount}`;
}
```

**改完后效果**：模型知道自己在哪个分支、项目规模，不再给错命令。

---

### 12. IDE 诊断注入（P2）

**做什么**：自动收集 LSP 诊断（编译错误/警告）注入到系统提示，模型即时修复。

**改哪些文件**：
- `packages/core/src/tools/lsp.ts` — 新增诊断收集
- `packages/core/src/core/prompts.ts` — 注入诊断到系统提示

**怎么改**：
```typescript
// lsp.ts — 在 LSP 服务中新增诊断收集
private diagnostics = new Map<string, Diagnostic[]>();

onDiagnostics(uri: string, diags: Diagnostic[]) {
  this.diagnostics.set(uri, diags);
}

// 获取活跃诊断（最近 10 个）
getActiveDiagnostics(): Diagnostic[] {
  return [...this.diagnostics.values()]
    .flat()
    .filter(d => d.severity <= 2)  // 仅 error/warning
    .slice(-10);
}
```
```typescript
// prompts.ts — 在系统提示中注入
const diags = lspService.getActiveDiagnostics();
if (diags.length > 0) {
  context += `\n## Current Diagnostics\n${formatDiagnostics(diags)}`;
}
```

**改完后效果**：模型自动看到编译错误，无需用户手动粘贴。

---

### 13. 终端主题检测（P2）

**做什么**：启动时通过 OSC 11 查询终端背景色，自动适配 dark/light 主题。

**改哪些文件**：
- `packages/cli/src/utils/theme.ts` — 新建或修改现有主题工具

**怎么改**：
```typescript
// theme.ts — 新增自动检测
import { queryTerminal } from './terminal-utils';

export async function detectTheme(): Promise<'dark' | 'light'> {
  // 尝试 OSC 11 查询
  const bgColor = await queryTerminal('OSC 11');
  if (bgColor) {
    const brightness = parseBrightness(bgColor);
    return brightness > 0.5 ? 'light' : 'dark';
  }
  
  // 回退：COLORFGBG 环境变量
  const colorfgbg = process.env.COLORFGBG;
  if (colorfgbg) {
    const bg = parseInt(colorfgbg.split(';').pop());
    return bg >= 7 && bg !== 8 ? 'light' : 'dark';
  }
  
  return 'dark';  // 默认
}
```

**改完后效果**：浅色终端启动 Agent 不再出现浅黄色文字不可见。

---

### 14. 自动后台化 Agent（P2）

**做什么**：Agent 任务超过 15s 自动转后台，不阻塞用户交互。

**改哪些文件**：
- `packages/core/src/tools/agent.ts` — 执行流程中加 timer

**怎么改**：
```typescript
// agent.ts — 在执行函数中新增
const AUTO_BACKGROUND_MS = 15_000;

async function executeAgent(agent: Agent) {
  const timeout = setTimeout(() => {
    agent.markAsBackground();  // 转后台
    notifyUser('Agent moved to background after 15s');
  }, AUTO_BACKGROUND_MS);
  
  try {
    await agent.run();
  } finally {
    clearTimeout(timeout);
  }
}
```

**改完后效果**：长任务执行 15s 后自动释放前台，用户可继续交互。

---

### 15. 密钥扫描（P2）

**做什么**：工具输出后扫描是否包含 API 密钥/密码，发现则警告或阻断。

**改哪些文件**：
- `packages/core/src/utils/secretScanner.ts` — 新建
- `packages/core/src/tools/shell.ts` — 输出后调用扫描

**怎么改**：
```typescript
// secretScanner.ts — 新建，参考 gitleaks 规则
const SECRET_PATTERNS = [
  { name: 'AWS Key',     re: /AKIA[0-9A-Z]{16}/ },
  { name: 'Generic API', re: /api[_-]?key["']?\s*[:=]\s*["']?[A-Za-z0-9]{20,}/ },
  // ... 50+ 规则
];

export function scanForSecrets(text: string): string[] {
  const found: string[] = [];
  for (const { name, re } of SECRET_PATTERNS) {
    if (re.test(text)) found.push(name);
  }
  return found;
}
```
```typescript
// shell.ts — 在工具输出后调用
const output = await runCommand(cmd);
const secrets = scanForSecrets(output);
if (secrets.length > 0) {
  warnUser(`Potential secrets detected: ${secrets.join(', ')}`);
  return redactSecrets(output);
}
```

**改完后效果**：防止模型意外输出 API 密钥到对话中。

---

### 16. 子进程环境变量清洗（P2）

**做什么**：启动子进程前剥离 30+ 敏感环境变量。

**改哪些文件**：
- `packages/core/src/utils/envSanitizer.ts` — 新建
- `packages/core/src/tools/shell.ts` — 启动子进程时调用

**怎么改**：
```typescript
// envSanitizer.ts — 新建
const SENSITIVE_VARS = new Set([
  'AWS_SECRET_ACCESS_KEY', 'AWS_SESSION_TOKEN',
  'GITHUB_TOKEN', 'GH_TOKEN',
  'OPENAI_API_KEY', 'ANTHROPIC_API_KEY',
  // ... 30+ 敏感变量
]);

export function sanitizeEnv(env: NodeJS.ProcessEnv): NodeJS.ProcessEnv {
  const clean = { ...env };
  for (const key of SENSITIVE_VARS) {
    delete clean[key];
  }
  return clean;
}
```

**改完后效果**：敏感环境变量不泄漏到工具执行的子进程中。

---

### 17. 结构化 Diff（P2）

**做什么**：Diff 渲染带行号 gutter + 语法高亮 + 上下文分隔线。

**改哪些文件**：
- `packages/cli/src/ui/components/DiffRenderer.tsx` — 已有，增强渲染
- `packages/cli/src/ui/utils/diffFormatter.ts` — 新建

**怎么改**：
```typescript
// diffFormatter.ts — 新建
import { diffLines } from 'diff';
import { highlight } from 'cli-highlight';

export function formatStructuredDiff(oldStr: string, newStr: string, lang: string): string {
  const changes = diffLines(oldStr, newStr);
  let oldLine = 1, newLine = 1;
  let output = '';
  
  for (const change of changes) {
    if (change.added) {
      for (const line of change.value.split('\n')) {
        output += `+ ${newLine++} | ${highlight(line, { language: lang })}\n`;
      }
    } else if (change.removed) {
      for (const line of change.value.split('\n')) {
        output += `- ${oldLine++} | ${highlight(line, { language: lang })}\n`;
      }
    } else {
      // 上下文行
      oldLine += change.value.split('\n').length - 1;
      newLine += change.value.split('\n').length - 1;
    }
  }
  return output;
}
```

**改完后效果**：代码变更带行号 + 语法高亮，可读性大幅提升。

---

### 18. OSC 通知（P2）

**做什么**：后台任务完成时推送系统通知（iTerm2/Kitty/Ghostty），带进度百分比。

**改哪些文件**：
- `packages/cli/src/utils/notifications.ts` — 新建

**怎么改**：
```typescript
// notifications.ts — 新建
export function sendTerminalNotification(type: 'complete' | 'progress', message: string, progress?: number) {
  if (process.env.TERM_PROGRAM === 'iTerm.app') {
    // iTerm2
    process.stdout.write(`\x1b]9;4;${progress || 100};${message}\x07`);
  } else if (process.env.KITTY_LISTEN_ON) {
    // Kitty
    process.stdout.write(`\x1b]99;i=1:${message}\x1b\\`);
  } else {
    // 回退：bell
    process.stdout.write('\x07');
  }
}
```

**改完后效果**：后台任务完成时收到带进度的系统通知，无需盯着终端。

---

### 19. OSC 8 超链接（P2）

**做什么**：文件路径和 URL 渲染为可点击超链接，Cmd+Click 直接打开。

**改哪些文件**：
- `packages/cli/src/ui/components/MarkdownRenderer.tsx` — 链接渲染处

**怎么改**：
```typescript
// MarkdownRenderer.tsx — 在链接渲染处修改
function renderLink(text: string, url: string): string {
  // OSC 8 超链接格式: ESC ] 8 ; params ; uri ST text ESC ] 8 ; ; ST
  return `\x1b]8;;${url}\x1b\\${text}\x1b]8;;\x1b\\`;
}

// 使用示例
renderLink('src/index.ts', 'file:///path/to/src/index.ts');
renderLink('github.com', 'https://github.com');
```

**改完后效果**：终端中文件路径/URL 可直接 Cmd+Click 打开，零复制。

---

### 20. 色觉无障碍主题（P2）

**做什么**：新增色觉无障碍主题，diff 配色红绿→蓝橙，适配红绿色盲用户。

**改哪些文件**：
- `packages/cli/src/ui/themes/theme-manager.ts` — 新增主题

**怎么改**：
```typescript
// theme-manager.ts — 新增主题
const COLORBLIND_SAFE = {
  name: 'Colorblind Safe',
  diff: {
    added:   '#0066CC',  // 蓝（非绿）
    removed: '#CC6600',  // 橙（非红）
  },
  // 其他颜色使用 daltonized 调色板
};
```

**改完后效果**：色盲用户能清晰区分 diff 中的增删行。

---

### 21. 自定义快捷键（P2）

**做什么**：支持 `keybindings.json` 自定义快捷键配置。

**改哪些文件**：
- `packages/cli/src/config/keyBindings.ts` — 已有基础架构，新增加载和解析
- `packages/cli/src/ui/keyboard/` — 新建快捷键处理

**怎么改**：
```typescript
// keyBindings.ts — 新增用户配置加载
interface KeyBinding {
  key: string;
  command: string;
  when?: string;
}

async function loadUserKeyBindings(): Promise<KeyBinding[]> {
  const configPath = path.join(getConfigDir(), 'keybindings.json');
  try {
    const content = await fs.readFile(configPath, 'utf-8');
    return JSON.parse(content).keybindings;
  } catch {
    return [];  // 无用户配置，使用默认
  }
}
```

**改完后效果**：Vim/Emacs 用户可自定义习惯键位。

---

### 22. 会话分支（P3）

**做什么**：从历史会话任意节点分叉，探索不同方案。

**改哪些文件**：
- `packages/core/src/services/sessionService.ts` — 新增 fork 方法
- `packages/cli/src/ui/commands/branchCommand.ts` — 新建命令

**怎么改**：
```typescript
// sessionService.ts
async forkSession(sessionId: string, fromMessageId: string, newTitle: string): Promise<string> {
  const source = await this.loadSession(sessionId);
  const messages = source.messages.slice(0, source.messages.findIndex(m => m.id === fromMessageId) + 1);
  const newSessionId = uuid();
  await this.createSession(newSessionId, newTitle, messages);
  return newSessionId;
}
```

**改完后效果**：用户可从任意对话节点分叉，并行探索多个方案。

---

### 23. 安全审查（P3，skill 可补齐）

**做什么**：编写 `SKILL.md` 即可实现，无需代码改动。

**改哪些文件**：
- `.qwen/skills/security-review/SKILL.md` — 新建

**怎么改**：
```markdown
---
name: security-review
description: 基于 git diff 进行安全审查
---

# Security Review

检查最近的 git diff，关注：
1. 硬编码密钥/凭证
2. SQL 注入/XSS 漏洞
3. 权限绕过
4. 不安全的反序列化
...
```

**改完后效果**：用户执行 `/skills security-review` 即可自动审查代码安全。

---

### 24. PR 评论（P3）

**做什么**：通过 GitHub Actions skill 实现，无需核心代码改动。

**改哪些文件**：
- `.qwen/skills/pr-review/SKILL.md` — 新建 skill
- `.github/workflows/pr-review.yml` — 新建 workflow

**改完后效果**：PR 提交时自动 review 并添加 inline 评论。

---

### 25. Thinking 块保留（P2）

**做什么**：thinking 块跨轮保留，1h 空闲自动清理。

**改哪些文件**：
- `packages/core/src/core/client.ts` — thinking 块存储和清理
- 仅 Anthropic 模型适用

**怎么改**：
```typescript
// client.ts — thinking 块持久化
private thinkingBlocks: ThinkingBlock[] = [];
private lastThinkingActivity = Date.now();

function persistThinking(blocks: ThinkingBlock[]) {
  this.thinkingBlocks = blocks;
  this.lastThinkingActivity = Date.now();
}

// 空闲 1h 后清理
function cleanupIdleThinking() {
  if (Date.now() - this.lastThinkingActivity > 3600_000) {
    this.thinkingBlocks = [];
  }
}
```

**改完后效果**：模型推理过程中的思考跨轮保留，提升复杂任务的连续性。

---
