# Qwen Code 上游回移建议报告（Gemini CLI 源码对比）

> 基于 Gemini CLI（开源，`../gemini-cli/`）与 Qwen Code（fork 分支，`../qwen-code/`）的源码对比。Qwen Code 最后同步上游为 2025-10-23（v0.8.2），此后 Gemini CLI 从 v0.9.0 演进到 v0.36.0（28 个大版本，2041 个 commit）。本报告梳理可回移的改进点。
>
> 与 [Claude Code 改进建议报告](./qwen-code-improvement-report.md) 互补——Claude Code 报告关注"行业领先者有什么"，本报告关注"自己的上游已经做了什么"。

## 一、回移建议矩阵（44 项，按优先级排序）

| 优先级 | 改进点 | Qwen Code 现状 | 难度 | 上游 PR |
|:------:|--------|----------------|:----:|---------|
| **P0** | [渲染前数据裁剪（SlicingMaxSizedBox）](./qwen-code-gemini-upstream-report-details.md#item-1) — 渲染前 `.slice()` 到 maxLines，避免 Ink 布局全量内容 | 渲染后视觉裁剪（布局全部数据） | 小 | [#21416](https://github.com/google-gemini/gemini-cli/pull/21416) |
| **P0** | [工具输出硬上限常量](./qwen-code-gemini-upstream-report-details.md#item-2) — `ACTIVE_SHELL_MAX_LINES=15` 等 4 个常量 + `calculateShellMaxLines()` | 无硬上限（=终端高度） | 小 | [#20378](https://github.com/google-gemini/gemini-cli/pull/20378) |
| **P0** | [Shell buffer 摊销截断](./qwen-code-gemini-upstream-report-details.md#item-3) — 10MB 上限 + 1MB 摊销截断 + UTF-16 surrogate 保护 | 无 buffer 上限 | 小 | [#21416](https://github.com/google-gemini/gemini-cli/pull/21416) |
| **P0** | [环境变量净化](./qwen-code-gemini-upstream-report-details.md#item-19) — 25+ 模式过滤 secrets/API keys/credentials | 无净化，secrets 泄漏到 shell | 中 | — |
| **P0** | [危险命令黑名单](./qwen-code-gemini-upstream-report-details.md#item-20) — `rm -rf`/`find -exec`/`git -c` 等深度验证 | 仅 AST 只读检测 | 中 | — |
| **P1** | [LRU 文本处理缓存](./qwen-code-gemini-upstream-report-details.md#item-4) — 字符串宽度 / codePoints / 高亮 token 三级缓存 | 无缓存，每次击键重新计算 | 小 | — |
| **P1** | [紧凑工具视图（DenseToolMessage）](./qwen-code-gemini-upstream-report-details.md#item-5) — diff 折叠 + 15 行上限 + 紧凑布局 | 缺失 | 中 | [#20974](https://github.com/google-gemini/gemini-cli/pull/20974) |
| **P1** | [组件 memo 化](./qwen-code-gemini-upstream-report-details.md#item-6) — `HistoryItemDisplay` / `AppHeader` 等高频组件 `React.memo()` | 未 memo 化 | 小 | — |
| **P1** | [字符上限降级](./qwen-code-gemini-upstream-report-details.md#item-7) — `MAXIMUM_RESULT_DISPLAY_CHARACTERS` 从 1MB 降到 20KB | 1MB（Gemini 的 50 倍） | 小 | [#21416](https://github.com/google-gemini/gemini-cli/pull/21416) |
| **P1** | [Edit 模糊匹配（Levenshtein）](./qwen-code-gemini-upstream-report-details.md#item-21) — 10% 容差 + 空白低惩罚 + LLM 修复回退 | 仅精确匹配 | 中 | — |
| **P1** | [省略占位符检测](./qwen-code-gemini-upstream-report-details.md#item-22) — 拦截 "rest of methods..." 等不完整内容 | 无检测 | 小 | — |
| **P1** | [JIT 上下文发现](./qwen-code-gemini-upstream-report-details.md#item-23) — 读/写/编辑文件时自动附加子目录上下文 | 缺失 | 中 | — |
| **P1** | [OS 级 sandbox](./qwen-code-gemini-upstream-report-details.md#item-24) — Linux bwrap + macOS Seatbelt + Windows 受限 token | 无进程隔离 | 大 | — |
| **P1** | [Tool Output Masking](./qwen-code-gemini-upstream-report-details.md#item-33) — Hybrid Backward Scanned FIFO 裁剪大工具输出，保留最近 50k token | 全量加载到上下文 | 中 | — |
| **P1** | [/rewind 检查点回退](./qwen-code-gemini-upstream-report-details.md#item-34) — 会话内任意消息回退 + 文件恢复 + 确认对话框 | 缺失 | 中 | — |
| **P1** | [Model Availability Service](./qwen-code-gemini-upstream-report-details.md#item-35) — 模型健康追踪 + 容量/配额感知 + 自动降级 | 无模型健康追踪 | 中 | — |
| **P2** | [虚拟化列表（VirtualizedList）](./qwen-code-gemini-upstream-report-details.md#item-8) — 仅渲染可视区域 + `StaticRender` 离屏项 | 全量渲染 | 中 | — |
| **P2** | [批量滚动（useBatchedScroll）](./qwen-code-gemini-upstream-report-details.md#item-9) — 同一 tick 内多次滚动合并为一次渲染 | 无批量滚动 | 小 | — |
| **P2** | [Scrollable 滚动容器](./qwen-code-gemini-upstream-report-details.md#item-10) — ResizeObserver 锚定 + 动画滚动条 + backbuffer | 缺失 | 中 | — |
| **P2** | [终端能力管理器](./qwen-code-gemini-upstream-report-details.md#item-11) — Kitty 键盘协议 + bracketed paste + 鼠标事件 | 缺失 | 中 | — |
| **P2** | [URL 安全检测](./qwen-code-gemini-upstream-report-details.md#item-12) — Unicode 同形攻击 / Punycode 检测 | 缺失 | 小 | — |
| **P2** | [ANSI-aware 表格渲染器](./qwen-code-gemini-upstream-report-details.md#item-13) — `TableRenderer` CJK 2-width + 列对齐 + 换行 | CJK 列错位 | 小 | — |
| **P2** | [Shell 命令参数补全](./qwen-code-gemini-upstream-report-details.md#item-14) — git/npm 命令参数补全 provider | 缺失 | 中 | — |
| **P2** | [任务追踪工具（trackerTools）](./qwen-code-gemini-upstream-report-details.md#item-15) — 6 个子工具：创建/更新/依赖/可视化 | 缺失 | 大 | — |
| **P2** | [Folder Trust 发现](./qwen-code-gemini-upstream-report-details.md#item-25) — 信任前扫描项目配置（hooks/agents/MCP/allowlist） | 无预执行扫描 | 中 | — |
| **P2** | [Web Fetch 速率限制与 SSRF 加固](./qwen-code-gemini-upstream-report-details.md#item-26) — 10 次/分钟/host + async DNS 验证 + IANA 段阻断 | 最小 SSRF 检查 | 中 | — |
| **P2** | [Grep 高级参数](./qwen-code-gemini-upstream-report-details.md#item-27) — `include_pattern`/`exclude_pattern`/`names_only`/per-file 上限 | 仅基础 pattern+path+glob | 小 | — |
| **P2** | [高级 Vim 操作](./qwen-code-gemini-upstream-report-details.md#item-28) — 大词(dW/cW) + 查找(f/F/t/T) + 替换(r) + 大小写切换(~) | 仅基础词操作 | 中 | — |
| **P2** | [Footer 自定义](./qwen-code-gemini-upstream-report-details.md#item-29) — `FooterConfigDialog` 可配置状态指示器 | 固定布局 | 中 | — |
| **P2** | [Write File LLM 内容修正](./qwen-code-gemini-upstream-report-details.md#item-30) — 写入前 LLM 校正畸形内容 | 直接写入 | 中 | — |
| **P2** | [Markdown 渲染切换](./qwen-code-gemini-upstream-report-details.md#item-36) — Alt+M 切换渲染/原始 Markdown 视图 | 缺失 | 小 | — |
| **P2** | [A2A Agent-to-Agent 协议](./qwen-code-gemini-upstream-report-details.md#item-37) — gRPC/REST 远程 Agent 通信 + 30 分钟超时 | 缺失 | 大 | — |
| **P2** | [Workspace TOML Policy](./qwen-code-gemini-upstream-report-details.md#item-38) — 项目级策略引擎 + 自动接受 + 完整性校验 | 仅权限规则 | 中 | — |
| **P2** | [后台 Shell 管理工具](./qwen-code-gemini-upstream-report-details.md#item-39) — list/status/wait/terminate 4 个专用工具 | 仅 `is_background` 参数 | 中 | — |
| **P2** | [Wave-based 并行工具调度](./qwen-code-gemini-upstream-report-details.md#item-40) — 安全工具按波次并发执行 | 仅 Agent 工具并行 | 中 | — |
| **P3** | [自定义 Ink 构建](./qwen-code-gemini-upstream-report-details.md#item-16) — `@jrichman/ink@6.6.7` 优化 fork | 标准 `ink@6.2.3` | 大 | — |
| **P3** | [超长回复分片渲染](./qwen-code-gemini-upstream-report-details.md#item-17) — `GeminiMessageContent` 分片避免单组件过大 | 单组件渲染全部 | 中 | — |
| **P3** | [闪烁检测器](./qwen-code-gemini-upstream-report-details.md#item-18) — `useFlickerDetector` 自动检测并缓解 | 缺失 | 小 | — |
| **P3** | [OAuth 流程重构](./qwen-code-gemini-upstream-report-details.md#item-31) — 共享 `oauth-flow.ts` + RFC 9728 + OIDC 路径发现 | 内联实现 | 中 | — |
| **P3** | [Conseca 安全框架](./qwen-code-gemini-upstream-report-details.md#item-32) — 策略生成 + 执行 + 可扩展 checker 链 | 无内容安全评估 | 大 | — |
| **P3** | [Ctrl+Z 终端挂起](./qwen-code-gemini-upstream-report-details.md#item-41) — 挂起/恢复 + 终端状态管理 | 缺失 | 小 | — |
| **P3** | [Shell 不活跃超时](./qwen-code-gemini-upstream-report-details.md#item-42) — 可配置超时 + 状态标题变化 | 缺失 | 小 | — |
| **P3** | [Startup Profiler](./qwen-code-gemini-upstream-report-details.md#item-43) — 启动阶段 CPU 计时 + 遥测集成 | 缺失 | 小 | — |
| **P3** | [大文本粘贴占位](./qwen-code-gemini-upstream-report-details.md#item-44) — 超过 5 行/500 字符的粘贴替换为 `[Pasted Text]` | 缺失 | 小 | — |

## 二、优先级分布

| 优先级 | 数量 | 核心主题 |
|--------|------|---------|
| P0 | 5 项 | 防闪烁（3）+ 安全加固（2） |
| P1 | 11 项 | 渲染性能（4）+ 工具智能化（4）+ 上下文/会话管理（3） |
| P2 | 19 项 | UI 组件（6）+ 安全（3）+ 工具增强（4）+ 调度/协议（3）+ UX（3） |
| P3 | 9 项 | 底层优化（3）+ 终端特性（3）+ 安全框架（2）+ UX（1） |

> 注：详情见 [回移建议详情](./qwen-code-gemini-upstream-report-details.md)
