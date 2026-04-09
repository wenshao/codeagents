# Qwen Code 上游 backport 建议报告（Gemini CLI 源码对比）

> Qwen Code 于 2025-10-23 从 Gemini CLI v0.8.2 fork。此后 Gemini CLI 独立演进了 **28 个大版本**（v0.9.0 → v0.36.0）、**2041 个 commit**——大量新功能和优化未被 backport。本报告系统梳理 **52 项**可 backport 的改进点，并附 Qwen Code 独有优势的反向对比。
>
> **相关报告**：
> - [Claude Code 改进建议报告（248 项）](./qwen-code-improvement-report.md)——行业领先者有什么
> - [OpenCode 对标改进报告（10 项）](./qwen-code-opencode-improvements.md)——文件时间锁、Session Fork、SQLite 等
> - [/review 功能改进建议](./qwen-code-review-improvements.md)——审查功能改进
> - [工具输出限高防闪烁](./tool-output-height-limiting-deep-dive.md)——Gemini CLI SlicingMaxSizedBox vs Qwen Code

## 一、为什么需要 backport

### 1.1 fork 时间线

```
2025-06-25  Gemini CLI v0.1.0 首次发布
2025-10-23  Qwen Code 最后同步上游（v0.8.2）← fork 点
    ↓ (此后 Qwen Code 独立发展，未再同步上游)
2025-11    Gemini CLI: Hook 引擎、模型路由器、会话恢复
2025-12    Gemini CLI: Hook 默认启用、/rewind、事件驱动调度器
2026-01    Gemini CLI: A2A 协议、远程 Agent、Plan 模式
2026-02    Gemini CLI: 后台 Shell、Vim 增强、sandbox 加固
2026-03    Gemini CLI: SlicingMaxSizedBox 防闪烁、Edit 模糊匹配、环境变量净化
2026-03    Gemini CLI: Model Routing 多策略路由、DevTools Inspector、Voice Formatter
2026-04    Gemini CLI v0.36.0（当前最新）——新增 Billing/Credits、CodeAssist 企业集成、Triage 代码分析
```

### 1.2 差距的实际影响

| 问题 | 根因 | 影响 |
|------|------|------|
| 大输出屏幕闪烁 | 无 SlicingMaxSizedBox + 无硬上限 | 用户体验差 |
| 环境变量泄漏 | 无环境净化 | secrets 传递给 `npm install` 等命令 |
| 编辑匹配失败率高 | 仅精确匹配 | Agent 反复重试浪费 token |
| 长命令内存泄漏 | 无 Shell buffer 上限 | `tail -f` 等命令耗尽内存 |
| 无 /rewind 回退 | 未 backport | 用户需手动 git checkout |

### 1.3 Qwen Code 的独有优势（不受 backport 影响）

backport 不会丢失 Qwen Code 独立发展的优势：

| 能力 | 说明 | 规模 |
|------|------|------|
| 多 Provider 内容生成 | Anthropic/OpenAI/DashScope/DeepSeek 等 | 核心差异 |
| CoreToolScheduler | Agent 工具并行执行 | 核心差异 |
| 规则权限系统 | L3→L4→L5 多层评估 | 核心差异 |
| Arena 多模型竞赛 | 竞品无 | 独有 |
| 免费 OAuth 额度 | 1000 次/天 | 独有 |
| 分离重试预算 | 内容/流异常/速率限制分别计数 | 工程优势 |
| 三格式扩展兼容 | Qwen + Claude + Gemini | 生态优势 |
| **多渠道部署** | DingTalk/Telegram/WeChat/Web（webui 14,414 行） | **Gemini CLI 无** |
| **Web UI** | 浏览器端完整交互界面（web-templates 2,996 行） | **Gemini CLI 无** |
| **Java SDK** | JVM 生态集成 | **Gemini CLI 无** |
| **Zed 编辑器扩展** | 除 VS Code 外的 IDE 生态 | **Gemini CLI 无** |
| **国际化 (i18n)** | 内置中英多语言支持 | **Gemini CLI 无** |

### 1.4 backport 策略建议

| 策略 | 适用场景 | 风险 |
|------|---------|------|
| **直接复制文件** | 新增功能（SlicingMaxSizedBox、toolLayoutUtils） | 低——不改现有代码 |
| **改一个数字** | 字符上限降级（1MB→20KB） | 极低——改一行 |
| **新增常量** | ACTIVE_SHELL_MAX_LINES=15 | 低——新增不影响 |
| **参考实现重写** | Edit 模糊匹配 | 中——需适配 Qwen Code 的 edit 逻辑 |
| **大型 backport** | OS 级 sandbox | 高——跨平台+安全边界 |

## 二、backport 建议矩阵（52 项，按优先级排序）

| 优先级 | 改进点 | Qwen Code 现状 | 难度 | 上游 PR |
|:------:|--------|----------------|:----:|---------|
| **P0** | [渲染前数据裁剪（SlicingMaxSizedBox）](./qwen-code-gemini-upstream-report-details.md#item-1) — 渲染前 `.slice()` 到 maxLines，避免 Ink 布局全量内容 | 渲染后视觉裁剪（布局全部数据） | 小 | [#21416](https://github.com/google-gemini/gemini-cli/pull/21416) / [QwenPR#3013](https://github.com/QwenLM/qwen-code/pull/3013) |
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
| **P1** | [Model Routing 多策略路由](./qwen-code-gemini-upstream-report-details.md#item-44) — 8 种可组合路由策略 + Gemma 分类器 + 遥测集成（3,667 行） | 无路由层 | 大 | — |
| **P1** | [Agent Session 协议层](./qwen-code-gemini-upstream-report-details.md#item-45) — AsyncIterable Agent 通信 + 事件回放 + 多流管理（4,997 行） | 无 Agent 会话协议 | 大 | — |
| **P1** | [Session Browser 会话浏览器](./qwen-code-gemini-upstream-report-details.md#item-46) — TUI 内交互式历史会话搜索/筛选/切换（512 行） | 仅 `--resume` 命令行 | 中 | — |
| **P2** | [A2A Server 服务端包](./qwen-code-gemini-upstream-report-details.md#item-47) — HTTP 应用服务器 + 远程 Agent 执行器（9,044 行） | 无 A2A 支持 | 大 | — |
| **P2** | [DevTools Inspector 调试面板](./qwen-code-gemini-upstream-report-details.md#item-48) — WebSocket 实时网络/控制台日志查看器（433 行） | 无调试面板 | 中 | — |
| **P2** | [MCP Resource Registry 资源注册表](./qwen-code-gemini-upstream-report-details.md#item-49) — MCP 资源发现 + URI 查找 + 缓存失效追踪（161 行） | 无资源注册 | 小 | — |
| **P2** | [Voice Response Formatter 语音格式化](./qwen-code-gemini-upstream-report-details.md#item-50) — Markdown→语音友好纯文本转换（473 行） | 无语音支持 | 小 | — |
| **P2** | [Triage 代码问题检测](./qwen-code-gemini-upstream-report-details.md#item-51) — Issue 识别 + 重复代码检测 UI（1,728 行） | 无代码分析 UI | 中 | — |
| **P2** | [CodeAssist 企业集成](./qwen-code-gemini-upstream-report-details.md#item-52) — 用户分层 + 信用额度 + 管理员策略 + MCP 管控（9,825 行） | 无企业集成 | 大 | — |
| **P2** | [Billing/Credits 计费系统](./qwen-code-gemini-upstream-report-details.md#item-53) — Google One AI 额度管理 + 超额策略 + 计费集成（449 行） | 免费模型 | 中 | — |

## 三、优先级分布

| 优先级 | 数量 | 核心主题 |
|--------|------|---------|
| P0 | 5 项 | 防闪烁（3）+ 安全加固（2） |
| P1 | 14 项 | 渲染性能（4）+ 工具智能化（4）+ 上下文/会话管理（3）+ **模型路由 + Agent 协议 + 会话浏览器** |
| P2 | 25 项 | UI 组件（5）+ 安全（3）+ 工具增强（4）+ 调度/协议（3）+ UX（3）+ **A2A Server + DevTools + 资源注册 + 语音 + Triage + 企业集成 + 计费** |
| P3 | 8 项 | 底层优化（3）+ 终端特性（3）+ 安全框架（2） |

## 四、30 分钟快速见效——P0 实施指南

如果只有 30 分钟，做这 3 件事立即改善用户体验：

### 4.1 字符上限降级（5 分钟）

```typescript
// packages/cli/src/ui/components/messages/ToolMessage.tsx
// 改一个数字：
const MAXIMUM_RESULT_DISPLAY_CHARACTERS = 20000; // 原来是 1000000
```

### 4.2 添加硬上限常量（10 分钟）

```typescript
// packages/cli/src/ui/constants.ts — 新增：
export const ACTIVE_SHELL_MAX_LINES = 15;
export const COMPLETED_SHELL_MAX_LINES = 15;
export const SUBAGENT_MAX_LINES = 15;
```

在 `ToolMessage.tsx` 中添加 `Math.min(计算值, ACTIVE_SHELL_MAX_LINES)`。

### 4.3 从上游复制 SlicingMaxSizedBox（15 分钟）

从 Gemini CLI 复制 `SlicingMaxSizedBox.tsx`（103 行），在 `ToolMessage.tsx` 中用它包裹工具输出——渲染前裁剪数据到 maxLines 行。

**效果**：大输出闪烁问题基本消除。

### 4.4 扩展路线图

| 时间 | 范围 | 预期效果 |
|------|------|---------|
| **30 分钟** | 上述 3 项 P0 | 大输出闪烁消除 |
| **1 天** | + LRU 缓存 + 组件 memo + 字符上限 + 省略检测 | 击键响应 + 工具输出体验显著提升 |
| **1 周** | + Edit 模糊匹配 + JIT 上下文 + /rewind + Session Browser | 编辑成功率 + 会话管理完整化 |
| **1 月** | + Model Routing + Agent Session + 环境净化 + 沙箱 | 模型智能选择 + 安全模型完善 |
| **1 季度** | + A2A Server + DevTools + Triage + Voice | 远程 Agent + 调试 + 代码分析 |

## 五、Gemini CLI vs Qwen Code 模块级架构差异

fork 后 Gemini CLI 新增了大量 Qwen Code 中完全不存在的模块：

### 5.1 Gemini CLI 独有模块

| 模块 | 路径 | 规模 | 功能 | 对标建议 |
|------|------|:----:|------|---------|
| **Model Routing** | `core/routing/` | 19 文件 3,667 行 | 8 种可组合策略 + Gemma 分类器自动选模型 | P1——参考实现 |
| **CodeAssist** | `core/code_assist/` | 26 文件 9,825 行 | 企业分层 + 管理员策略 + MCP 管控 | P2——商业化需要时 |
| **Agent Session** | `core/agent/` | 11 文件 4,997 行 | AsyncIterable 通信 + 事件回放 + 多流 | P1——远程 Agent 基础 |
| **A2A Server** | `packages/a2a-server/` | 33 文件 9,044 行 | HTTP Agent 服务器 + gRPC 远程执行 | P2——与 item-37 配套 |
| **Triage** | `ui/components/triage/` | 2 文件 1,728 行 | Issue 检测 + 重复代码分析 UI | P2——代码质量 |
| **Session Browser** | `ui/components/SessionBrowser/` | 9 文件 512 行 | 交互式历史会话搜索/切换 | P1——用户体验 |
| **Voice** | `core/voice/` | 2 文件 473 行 | Markdown→TTS 友好文本转换 | P2——可访问性 |
| **Billing** | `core/billing/` | 3 文件 449 行 | Google One AI 额度 + 超额策略 | P2——商业化 |
| **DevTools** | `packages/devtools/` | 2 文件 433 行 | WebSocket 实时日志查看器 | P2——开发调试 |
| **Resources** | `core/resources/` | 2 文件 161 行 | MCP 资源注册 + URI 查找 | P2——MCP 增强 |

### 5.2 Qwen Code 独有模块（Gemini CLI 无）

| 模块 | 路径 | 规模 | 功能 |
|------|------|:----:|------|
| **多渠道部署** | `packages/channels/` | 多子包 | DingTalk/Telegram/WeChat 渠道适配 |
| **Web UI** | `packages/webui/` | 111 文件 14,414 行 | 浏览器端完整交互界面 |
| **Web Templates** | `packages/web-templates/` | 20 文件 2,996 行 | Web 部署模板 |
| **Java SDK** | `packages/sdk-java/` | — | JVM 生态集成 |
| **Zed 扩展** | `packages/zed-extension/` | — | Zed 编辑器集成 |
| **国际化** | `packages/cli/src/i18n/` | — | 中英多语言支持 |
| **Arena** | 内置 | — | 多模型竞赛对比 |
| **多 Provider** | 内置 | — | Anthropic/OpenAI/DashScope/DeepSeek 等 |

### 5.3 核心差异总结

| 维度 | Gemini CLI | Qwen Code | 评估 |
|------|-----------|-----------|------|
| **模型路由** | 8 策略组合 + 分类器 | 直接指定模型 | Gemini 显著领先 |
| **Agent 协议** | AsyncIterable + 事件回放 | 基础 Agent 调用 | Gemini 领先 |
| **企业功能** | CodeAssist 分层 + 计费 | 免费 OAuth | 不同路线 |
| **多渠道** | 仅 CLI + IDE | CLI + IDE + Web + 聊天平台 | **Qwen Code 领先** |
| **多模型** | 仅 Gemini 系列 | 10+ Provider | **Qwen Code 领先** |
| **代码分析** | Triage Issue/Duplicate | 无 | Gemini 领先 |
| **调试工具** | DevTools Inspector | 无 | Gemini 领先 |
| **语音** | Voice Formatter | 无 | Gemini 领先 |
| **国际化** | 无 | i18n 多语言 | **Qwen Code 领先** |

## 六、完整实施详情

每项的完整实现细节（问题定义、源码索引、修改方向、成本评估、前后对比）见 **[backport 建议详情](./qwen-code-gemini-upstream-report-details.md)**。

## 七、更新日志

### 2026-04-09

- 新增 10 项 backport 建议（#44-#53），总项数 42→52
- 新增第五节"模块级架构差异"——Gemini 独有 10 模块 vs Qwen Code 独有 8 模块
- 扩展 Qwen Code 独有优势（+5 项：多渠道/Web UI/Java SDK/Zed/i18n）
- 扩展实施路线图（30 分钟→1 季度阶段规划）
- 新增第七节"更新日志"

### 2026-04-06

- 初始版本：42 项 backport 建议 + 1271 行详情文档
