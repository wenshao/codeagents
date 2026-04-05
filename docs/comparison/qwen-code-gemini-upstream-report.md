# Qwen Code 上游回移建议报告（Gemini CLI 源码对比）

> 基于 Gemini CLI（开源，`../gemini-cli/`）与 Qwen Code（fork 分支，`../qwen-code/`）的源码对比。Qwen Code 最后同步上游为 2025-10-23（v0.8.2），此后 Gemini CLI 新增了大量功能和性能优化。本报告梳理可回移的改进点。
>
> 与 [Claude Code 改进建议报告](./qwen-code-improvement-report.md) 互补——Claude Code 报告关注"行业领先者有什么"，本报告关注"自己的上游已经做了什么"。

## 一、回移建议矩阵

| 优先级 | 改进点 | Qwen Code 现状 | 难度 | 上游 PR |
|:------:|--------|----------------|:----:|---------|
| **P0** | [渲染前数据裁剪（SlicingMaxSizedBox）](#item-1) — 渲染前 `.slice()` 到 maxLines，避免 Ink 布局全量内容 | 渲染后视觉裁剪（布局全部数据） | 小 | [#21416](https://github.com/google-gemini/gemini-cli/pull/21416) |
| **P0** | [工具输出硬上限常量](#item-2) — `ACTIVE_SHELL_MAX_LINES=15` 等 4 个常量 + `calculateShellMaxLines()` | 无硬上限（=终端高度） | 小 | [#20378](https://github.com/google-gemini/gemini-cli/pull/20378) |
| **P0** | [Shell buffer 摊销截断](#item-3) — 10MB 上限 + 1MB 摊销截断 + UTF-16 surrogate 保护 | 无 buffer 上限 | 小 | [#21416](https://github.com/google-gemini/gemini-cli/pull/21416) |
| **P1** | [LRU 文本处理缓存](#item-4) — 字符串宽度 / codePoints / 高亮 token 三级缓存 | 无缓存，每次击键重新计算 | 小 | — |
| **P1** | [紧凑工具视图（DenseToolMessage）](#item-5) — diff 折叠 + 15 行上限 + 紧凑布局 | 缺失 | 中 | [#20974](https://github.com/google-gemini/gemini-cli/pull/20974) |
| **P1** | [组件 memo 化](#item-6) — `HistoryItemDisplay` / `AppHeader` 等高频组件 `React.memo()` | 未 memo 化 | 小 | — |
| **P1** | [字符上限降级](#item-7) — `MAXIMUM_RESULT_DISPLAY_CHARACTERS` 从 1MB 降到 20KB | 1MB（Gemini 的 50 倍） | 小 | [#21416](https://github.com/google-gemini/gemini-cli/pull/21416) |
| **P2** | [虚拟化列表（VirtualizedList）](#item-8) — 仅渲染可视区域 + `StaticRender` 离屏项 | 全量渲染 | 中 | — |
| **P2** | [批量滚动（useBatchedScroll）](#item-9) — 同一 tick 内多次滚动合并为一次渲染 | 无批量滚动 | 小 | — |
| **P2** | [Scrollable 滚动容器](#item-10) — ResizeObserver 锚定 + 动画滚动条 + backbuffer | 缺失 | 中 | — |
| **P2** | [终端能力管理器](#item-11) — Kitty 键盘协议 + bracketed paste + 鼠标事件 | 缺失 | 中 | — |
| **P2** | [URL 安全检测](#item-12) — Unicode 同形攻击 / Punycode 检测 | 缺失 | 小 | — |
| **P2** | [ANSI-aware 表格渲染器](#item-13) — `TableRenderer` CJK 2-width + 列对齐 + 换行 | CJK 列错位 | 小 | — |
| **P2** | [Shell 命令参数补全](#item-14) — git/npm 命令参数补全 provider | 缺失 | 中 | — |
| **P2** | [任务追踪工具（trackerTools）](#item-15) — 6 个子工具：创建/更新/依赖/可视化 | 缺失 | 大 | — |
| **P3** | [自定义 Ink 构建](#item-16) — `@jrichman/ink@6.6.7` 优化 fork | 标准 `ink@6.2.3` | 大 | — |
| **P3** | [超长回复分片渲染](#item-17) — `GeminiMessageContent` 分片避免单组件过大 | 单组件渲染全部 | 中 | — |
| **P3** | [闪烁检测器](#item-18) — `useFlickerDetector` 自动检测并缓解 | 缺失 | 小 | — |

> 注：详情见 [回移建议详情](./qwen-code-gemini-upstream-report-details.md)
