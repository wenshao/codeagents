# Qwen Code vs Gemini CLI 上游差距分析

> Qwen Code 是 Gemini CLI 的 fork 分支，最后一次同步上游为 2025-10-23（Gemini CLI v0.8.2）。此后 Gemini CLI 持续演进，增加了大量新功能和性能优化。本文档通过源码对比，系统梳理 Qwen Code 可从上游回移的改进点。
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md)

## 一、分叉时间线

```
2025-09-15  Qwen Code sync v0.3.4
2025-10-23  Qwen Code sync v0.8.2 ← 最后一次上游同步
    ↓ (此后 Qwen Code 独立发展)
2026-03-09  Gemini CLI: subagent result display + ACTIVE_SHELL_MAX_LINES
2026-03-18  Gemini CLI: SlicingMaxSizedBox + toolLayoutUtils + 防闪烁
2026-03-23  Gemini CLI: foundational layout refactor
2026-03-30  Gemini CLI: compact tool output (DenseToolMessage)
2026-04-06  当前（本文分析时间点）
```

## 二、渲染性能（最高优先级）

### 1. 工具输出限高与预裁剪

> 详见 [工具输出限高防闪烁](./tool-output-height-limiting-deep-dive.md)

**Gemini CLI 新增**（2026-03）：

| 文件 | 功能 |
|------|------|
| `ui/components/shared/SlicingMaxSizedBox.tsx` | 渲染前将数据 `.slice()` 到 maxLines，避免 Ink 布局全量内容 |
| `ui/utils/toolLayoutUtils.ts` | `calculateShellMaxLines()` + `calculateToolContentMaxLines()` 动态计算高度 |
| `ui/constants.ts` 新增常量 | `ACTIVE_SHELL_MAX_LINES=15`、`COMPLETED_SHELL_MAX_LINES=15`、`SUBAGENT_MAX_LINES=15`、`COMPACT_TOOL_SUBVIEW_MAX_LINES=15` |

**Qwen Code 现状**：`MAXIMUM_RESULT_DISPLAY_CHARACTERS=1,000,000`（1MB，Gemini 为 20KB）；无渲染前行数裁剪；无硬上限常量。

**改进建议**：回移 `SlicingMaxSizedBox` + `toolLayoutUtils.ts` + 硬上限常量。

### 2. LRU 缓存体系

**Gemini CLI 新增**：使用 `mnemonist` 库的 LRUCache，缓存上限 `LRU_BUFFER_PERF_CACHE_LIMIT=20000`。

| 缓存目标 | 文件 | 效果 |
|---------|------|------|
| `toCodePoints()` | `ui/utils/textUtils.ts` | 避免重复 `Array.from(str)` |
| `getCachedStringWidth()` | `ui/utils/textUtils.ts` | 单字符 ASCII 快速路径 + 缓存宽度计算 |
| Highlight token | `ui/utils/highlight.ts` | 输入高亮结果缓存 |

**Qwen Code 现状**：无 `mnemonist` 依赖，无文本处理 LRU 缓存。每次击键都重新计算字符串宽度。

### 3. 虚拟化列表与批量滚动

| 组件 | 文件 | 功能 |
|------|------|------|
| `VirtualizedList` | `ui/components/shared/VirtualizedList.tsx` | 仅渲染可视区域，离屏项用 `StaticRender` |
| `useBatchedScroll` | `ui/hooks/useBatchedScroll.ts` | 同一 tick 内多次滚动合并为一次渲染 |
| `Scrollable` | `ui/components/shared/Scrollable.tsx` | ResizeObserver 锚定 + 动画滚动条 |
| `ScrollableList` | `ui/components/shared/ScrollableList.tsx` | 搭配 VirtualizedList 的列表滚动 |

**Qwen Code 现状**：无虚拟化列表，无批量滚动，长消息历史全量渲染。

### 4. 组件 memo 化

**Gemini CLI**：`MainContent.tsx` 中：
```typescript
const MemoizedHistoryItemDisplay = memo(HistoryItemDisplay);
const MemoizedAppHeader = memo(AppHeader);
```

**Qwen Code 现状**：未对 `HistoryItemDisplay` 等高频组件使用 `React.memo()`。

### 5. 自定义 Ink 构建

**Gemini CLI**：`"ink": "npm:@jrichman/ink@6.6.7"`（自定义 Ink fork，可能含渲染优化）。

**Qwen Code**：`"ink": "^6.2.3"`（标准版本）。

### 6. Shell 输出 Buffer 管理

**Gemini CLI**（`ui/hooks/shellReducer.ts`）：
- `MAX_SHELL_OUTPUT_SIZE=10MB` + `SHELL_OUTPUT_TRUNCATION_BUFFER=1MB`
- 摊销截断（每 1MB 新输入截断一次，避免每 chunk O(n)）
- UTF-16 surrogate pair 保护

**Qwen Code 现状**：无 buffer 上限，长时间运行命令可能耗尽内存。

## 三、UI 组件（中等优先级）

### 1. 新增共享组件

| 组件 | 文件 | 功能 | Qwen Code 状态 |
|------|------|------|----------------|
| `SearchableList` | `ui/components/shared/SearchableList.tsx` | 可搜索列表 + 模糊匹配 | 缺失 |
| `ExpandableText` | `ui/components/shared/ExpandableText.tsx` | 可展开文本 + 高亮匹配 | 缺失 |
| `TabHeader` | `ui/components/shared/TabHeader.tsx` | 标签页导航头 | 缺失 |
| `SectionHeader` | `ui/components/shared/SectionHeader.tsx` | 分区标题 | 缺失 |
| `HalfLinePaddedBox` | `ui/components/shared/HalfLinePaddedBox.tsx` | 半行填充容器（低色深终端适配） | 缺失 |
| `BaseSettingsDialog` | `ui/components/shared/BaseSettingsDialog.tsx` | 高级设置对话框 | 缺失 |
| `TextInput` | `ui/components/shared/TextInput.tsx` | 文本输入组件 | 缺失 |
| `TableRenderer` | `ui/utils/TableRenderer.tsx` | ANSI/CJK-aware 表格渲染 | 缺失 |

### 2. 新增消息组件

| 组件 | 功能 | Qwen Code 状态 |
|------|------|----------------|
| `DenseToolMessage` | 紧凑工具输出（diff 视图等） | 缺失 |
| `SubagentGroupDisplay` | Subagent 组进度展示 | 缺失 |
| `SubagentProgressDisplay` | 单个 Subagent 进度 + spinner | 缺失 |
| `SubagentHistoryMessage` | Subagent 执行历史 | 缺失 |
| `ThinkingMessage` | 模型推理过程展示（过滤噪音） | 缺失 |
| `HintMessage` | 提示消息（灯泡图标 + 背景色） | 缺失 |
| `TopicMessage` | 对话主题更新展示 | 缺失 |
| `GeminiMessageContent` | 超长回复分片渲染 | 缺失 |
| `UserShellMessage` | 用户 shell 命令展示 | 缺失 |
| `Todo` / `TodoTray` | 任务清单展示 | 缺失 |

### 3. 新增 Hooks

| Hook | 功能 | 优先级 |
|------|------|--------|
| `useFlickerDetector` | 检测终端闪烁并自动启用缓解 | 高 |
| `useMemoryMonitor` | 内存使用监控 | 高 |
| `useBatchedScroll` | 批量滚动更新 | 高 |
| `useAnimatedScrollbar` | 动画滚动条 | 中 |
| `useInactivityTimer` | 不活跃计时器 | 中 |
| `useTurnActivityMonitor` | 轮次活动监控 | 中 |
| `useBackgroundTaskManager` | 后台任务管理 | 中 |
| `useRewind` | 会话回退 | 中 |
| `useShellCompletion` | Shell 命令补全 | 中 |
| `useSessionBrowser` | 会话浏览器 | 中 |
| `useKittyKeyboardProtocol` | Kitty 键盘协议支持 | 低 |

## 四、工具与核心功能（中等优先级）

### 1. 新增核心工具

| 工具 | 文件 | 功能 | Qwen Code 状态 |
|------|------|------|----------------|
| `trackerTools.ts` | 6 个子工具 | 任务追踪（创建/更新/依赖/可视化） | 缺失 |
| `shellBackgroundTools.ts` | 2 个子工具 | 后台进程列表 + 输出读取 | 缺失 |
| `complete-task.ts` | | Subagent 结构化输出完成 | 缺失 |
| `get-internal-docs.ts` | | 内部文档访问（带路径遍历防护） | 缺失 |
| `web-search.ts` | | Web 搜索 | 缺失 |
| `read-many-files.ts` | | 批量文件读取 | 缺失 |
| `topicTool.ts` | | 对话主题 + 战术意图更新 | 缺失 |
| `activate-skill.ts` | | 技能激活 + 确认对话框 | 缺失 |
| `ask-user.ts` | | 向用户提问（choice/text） | 缺失 |

### 2. 新增核心模块

| 模块 | 目录 | 功能 |
|------|------|------|
| `sandbox/` | `core/src/sandbox/{linux,macos,windows}/` | 平台级 sandbox（Linux bwrap, macOS sandbox-exec） |
| `availability/` | `core/src/availability/` | 模型健康追踪 + 容量/配额感知 |
| `fallback/` | `core/src/fallback/` | 模型不可用时自动降级 |
| `billing/` | `core/src/billing/` | G1 credits 管理 + 超额策略 |
| `voice/` | `core/src/voice/` | 语音输出格式化 |
| `scheduler/` | `core/src/scheduler/` | 工具调度（独立于 Qwen 的 CoreToolScheduler） |
| `agent/` | `core/src/agent/` | Agent 协议 + 事件翻译 |
| `safety/` | `core/src/safety/` | 内容安全评估 |
| `routing/` | `core/src/routing/` | 模型路由策略 |

### 3. 新增命令

| 命令 | 功能 | Qwen Code 状态 |
|------|------|----------------|
| `/skills` (install/enable/disable/link/list/uninstall) | 完整技能管理 | 部分实现 |
| `/hooks migrate` | Hook 迁移工具 | 缺失 |
| 键盘快捷键帮助对话框 | 全局快捷键查看 | 缺失 |

## 五、实用工具（低优先级但有价值）

| 工具 | 文件 | 功能 |
|------|------|------|
| `terminalCapabilityManager.ts` | `ui/utils/` | Kitty 键盘协议 + bracketed paste + 鼠标事件 + 清理序列 |
| `urlSecurityUtils.ts` | `ui/utils/` | URL 同形攻击检测（Unicode/Punycode） |
| `ConsolePatcher.ts` | `ui/utils/` | 拦截 console.log/warn/error 重定向 |
| `borderStyles.ts` | `ui/utils/` | 工具组消息边框颜色计算 |
| `contextUsage.ts` | `ui/utils/` | 上下文使用率计算 + 高阈值检测 |
| `historyExportUtils.ts` | `ui/utils/` | 聊天历史导出为 Markdown |
| `markdownParsingUtils.ts` | `ui/utils/` | Markdown → ANSI 转义码 |
| `inlineThinkingMode.ts` | `ui/utils/` | 内联思维模式管理 |
| `editorUtils.ts` | `ui/utils/` | 外部编辑器打开/等待 |
| Shell 补全 provider | `ui/hooks/shell-completions/` | Git/npm 命令参数补全 |

## 六、Qwen Code 独有优势（不应丢失）

在回移上游改进的同时，需要保留 Qwen Code 独立发展的优势：

| 能力 | Qwen Code 实现 | Gemini CLI 状态 |
|------|----------------|----------------|
| 多 Provider 内容生成 | Anthropic / OpenAI / DashScope / DeepSeek / OpenRouter / ModelScope | 仅 Gemini |
| `CoreToolScheduler` | Agent/Task 工具并行执行 + 顺序工具串行 | 全部串行 |
| 规则权限系统 | `permission-helpers.ts`：L3→L4→L5 多层权限评估 | 仅 IDE 层 |
| 非交互工具执行 | `nonInteractiveToolExecutor.ts` | 缺失 |
| 分离重试预算 | 内容重试 / 流异常重试 / 速率限制重试 分别计数 | 统一重试 |
| 模态默认值 | `modalityDefaults.ts`：按模型声明图片/PDF/音频/视频支持 | 缺失 |
| 专用系统提示 | Arena / Plan / Subagent / Sandbox 感知 | 单一 `getCoreSystemPrompt()` |
| Auth 系统 | 独立认证模块 | 缺失 |
| Channel 系统 | 多通道通信 | 缺失 |
| VerboseMode | PR#2770 compact/verbose 切换 | 无等价 |

## 七、推荐回移优先级

### P0（立即回移）
1. **`SlicingMaxSizedBox`** + **`toolLayoutUtils.ts`** + 硬上限常量 → 解决闪烁
2. **Shell buffer 上限**（`MAX_SHELL_OUTPUT_SIZE` + 摊销截断）→ 防内存溢出

### P1（尽快回移）
3. **LRU 缓存体系**（`mnemonist` + 字符串宽度/高亮缓存）→ 击键性能
4. **`useFlickerDetector`** → 自动检测并缓解闪烁
5. **组件 `memo()`** → 减少不必要重渲染
6. **`DenseToolMessage`** → 紧凑工具视图

### P2（有条件回移）
7. **`VirtualizedList` + `StaticRender`** → 长会话性能
8. **`Scrollable` + `useBatchedScroll`** → 滚动性能
9. **`terminalCapabilityManager`** → 终端特性管理
10. **`urlSecurityUtils`** → URL 安全检测
11. **`trackerTools`** → 任务追踪
12. **`shellBackgroundTools`** → 后台进程管理

### P3（视需求回移）
13. 自定义 Ink 构建 → 底层渲染优化
14. 语音支持 → 新交互模态
15. Billing/credits → 商业化需求
16. Platform sandbox → 安全加固
