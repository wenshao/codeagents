# Qwen Code 上游backport建议详情（Gemini CLI 源码对比）

> 返回 [backport建议矩阵](./qwen-code-gemini-upstream-report.md) | [Claude Code 改进建议](./qwen-code-improvement-report.md)

---

<a id="item-1"></a>

### 1. 渲染前数据裁剪 — SlicingMaxSizedBox（P0）

**问题**：Agent 执行 `npm install`（输出 500 行）或 `git log`（输出 200 行）时，Qwen Code 将全部数据交给 `MaxSizedBox`，由 Ink 先布局全部内容再用 `overflow="hidden"` 视觉裁剪。但 Ink 仍需计算全部内容高度——500 行的布局成本与 15 行相差 30 倍以上。每新增一行输出就触发完整重新布局 → 屏幕闪烁。

**Gemini CLI 的解决方案**：在 `MaxSizedBox` 之外包裹 `SlicingMaxSizedBox`，在 React 渲染**之前**用 `useMemo()` 将数据 `.slice()` 到 `maxLines` 行。Ink 只收到 15 行数据 → 布局瞬间完成 → 无闪烁。

**Gemini CLI 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `packages/cli/src/ui/components/shared/SlicingMaxSizedBox.tsx` | `MAXIMUM_RESULT_DISPLAY_CHARACTERS=20000` + `useMemo()` 内 `.slice()` |
| `packages/cli/src/ui/components/messages/ToolResultDisplay.tsx` | 使用 `SlicingMaxSizedBox` 包裹工具输出 |

**Qwen Code 现状**：无 `SlicingMaxSizedBox`。`ToolMessage.tsx` 直接将数据传入 `MaxSizedBox`，依赖 Ink 的 `overflow="hidden"` 做视觉裁剪。

**Qwen Code 修改方向**：从上游复制 `SlicingMaxSizedBox.tsx`（103 行）；在 `ToolMessage.tsx` 和 `ToolGroupMessage.tsx` 中用 `SlicingMaxSizedBox` 替换直接的 `MaxSizedBox` 调用。

**实现成本评估**：
- 涉及文件：~3 个（新建 1 个，修改 2 个）
- 新增代码：~120 行
- 开发周期：~0.5 天（1 人）
- 难点：无，直接从上游复制

**改进前后对比**：
- **改进前**：`npm install` 输出 500 行 → Ink 布局 500 行 → 每行新增触发重布局 → 闪烁
- **改进后**：`npm install` 输出 500 行 → `SlicingMaxSizedBox` 裁剪到 15 行 → Ink 布局 15 行 → 无闪烁

**意义**：工具输出是最频繁的 TUI 更新场景——预裁剪直接消除布局成本。
**缺失后果**：大输出命令导致屏幕闪烁，长输出命令导致卡顿。
**改进收益**：布局成本从 O(输出行数) 降到 O(15) = 常数时间。

**相关文章**：[工具输出限高防闪烁](./tool-output-height-limiting-deep-dive.md)

---

<a id="item-2"></a>

### 2. 工具输出硬上限常量 + calculateShellMaxLines（P0）

**问题**：Qwen Code 的 `ToolMessage.tsx` 用 `availableTerminalHeight` 直接作为输出高度上限——如果终端 80 行高，工具输出也可以占满 80 行。没有任何硬上限约束。Gemini CLI 则固定 15 行上限，无论终端多高。

**Gemini CLI 的解决方案**：

```typescript
// constants.ts
export const ACTIVE_SHELL_MAX_LINES = 15;
export const COMPLETED_SHELL_MAX_LINES = 15;
export const SUBAGENT_MAX_LINES = 15;
export const COMPACT_TOOL_SUBVIEW_MAX_LINES = 15;
```

`calculateShellMaxLines()` 根据 shell 状态（执行中/完成）、焦点状态、展开状态动态计算，但始终 `Math.min(terminalHeight, hardLimit)`。

**Gemini CLI 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `packages/cli/src/ui/constants.ts#L48-L67` | 4 个 `*_MAX_LINES` 常量 |
| `packages/cli/src/ui/utils/toolLayoutUtils.ts#L75-123` | `calculateShellMaxLines()` 5 种条件分支 |
| `packages/cli/src/ui/utils/toolLayoutUtils.ts#L38-65` | `calculateToolContentMaxLines()` 通用工具高度计算 |

**Qwen Code 现状**：`ToolMessage.tsx#L37-44` 定义了 `STATIC_HEIGHT=1`、`RESERVED_LINE_COUNT=5`、`MIN_LINES_SHOWN=2`，但**无上限常量**。`availableHeight` 计算结果直接等于 `终端高度 - 6`。

**Qwen Code 修改方向**：① `constants.ts` 添加 4 个 `*_MAX_LINES=15` 常量；② 新建 `utils/toolLayoutUtils.ts`（~50 行）；③ `ToolMessage.tsx` 中 `availableHeight = Math.min(计算值, hardLimit)`。

**实现成本评估**：
- 涉及文件：~3 个（新建 1 个，修改 2 个）
- 新增代码：~80 行
- 开发周期：~0.5 天（1 人）
- 难点：无

**改进前后对比**：
- **改进前**：终端 80 行高 → 工具输出占 74 行 → 主消息区几乎不可见
- **改进后**：终端 80 行高 → 工具输出最多 15 行 → 主消息区始终可见

**意义**：硬上限是防闪烁体系的基础——没有上限，任何输出都可能撑满终端。
**缺失后果**：大输出时主消息区被挤压，用户看不到 Agent 的文本回复。
**改进收益**：工具输出固定在 15 行 = 终端布局稳定可预期。

---

<a id="item-3"></a>

### 3. Shell buffer 摊销截断（P0）

**问题**：长时间运行的 shell 命令（如 `tail -f log.txt`）持续产生输出。如果不限制 buffer 大小，字符串会无限增长直到耗尽内存。如果每次追加都 `.slice()`，O(n) 的字符串复制在 buffer 较大时会成为瓶颈。

**Gemini CLI 的解决方案**：摊销截断策略——只有当 buffer 超过 `MAX_SHELL_OUTPUT_SIZE + SHELL_OUTPUT_TRUNCATION_BUFFER`（11MB）时才截断到 10MB。此外还处理了 UTF-16 surrogate pair 边界问题。

**Gemini CLI 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `packages/cli/src/ui/constants.ts#L69-80` | `MAX_SHELL_OUTPUT_SIZE=10MB`、`SHELL_OUTPUT_TRUNCATION_BUFFER=1MB` |
| `packages/cli/src/ui/hooks/shellReducer.ts#L97-143` | `APPEND_TASK_OUTPUT` reducer：摊销截断 + surrogate 保护 |

**Qwen Code 现状**：`shellCommandProcessor.ts` 追加输出时无 buffer 大小检查，无截断逻辑。

**Qwen Code 修改方向**：① `constants.ts` 添加 `MAX_SHELL_OUTPUT_SIZE` 和 `SHELL_OUTPUT_TRUNCATION_BUFFER`；② 输出追加逻辑中添加超限检查 + `.slice(-MAX_SIZE)` + surrogate 保护。

**实现成本评估**：
- 涉及文件：~2 个
- 新增代码：~40 行
- 开发周期：~0.5 天（1 人）
- 难点：UTF-16 surrogate pair 边界处理（直接复制上游逻辑即可）

**改进前后对比**：
- **改进前**：`tail -f` 运行 1 小时 → buffer 持续增长 → 终端逐渐卡顿 → OOM
- **改进后**：buffer 超过 11MB → 截断到 10MB → 每 1MB 新输入截断一次 → 内存恒定

**意义**：后台长命令是常见场景——无 buffer 限制 = 内存泄漏。
**缺失后果**：长时间运行的 shell 命令耗尽内存。
**改进收益**：10MB 恒定 buffer = 内存可预测，摊销截断 = 无性能毛刺。

---

<a id="item-4"></a>

### 4. LRU 文本处理缓存（P1）

**问题**：终端渲染涉及大量文本计算——字符串宽度（CJK 2-width、ANSI 转义）、Unicode codePoints 分割、语法高亮 token。这些计算在每次击键、每行输出时都会触发。相同字符串的重复计算是纯浪费。

**Gemini CLI 的解决方案**：使用 `mnemonist` 库的 LRUCache（上限 20000 条），对三种高频计算做缓存：

```typescript
// textUtils.ts — 字符串宽度缓存 + ASCII 快速路径
export const getCachedStringWidth = (str: string): number => {
  if (str.length === 1) {
    const code = str.charCodeAt(0);
    if (code >= 0x20 && code <= 0x7e) return 1; // ASCII 快速路径，无查表
  }
  const cached = stringWidthCache.get(str);
  if (cached !== undefined) return cached;
  const width = stringWidth(str);
  stringWidthCache.set(str, width);
  return width;
};
```

**Gemini CLI 源码索引**：

| 文件 | 缓存目标 |
|------|---------|
| `packages/cli/src/ui/utils/textUtils.ts#L45-73` | `toCodePoints()` — `Array.from(str)` 结果缓存 |
| `packages/cli/src/ui/utils/textUtils.ts#L162-196` | `getCachedStringWidth()` — 字符串宽度 + ASCII 快速路径 |
| `packages/cli/src/ui/utils/highlight.ts#L32-54` | 语法高亮 token 缓存 |
| `packages/cli/src/ui/constants.ts#L45` | `LRU_BUFFER_PERF_CACHE_LIMIT=20000` |

**Qwen Code 现状**：无 `mnemonist` 依赖，无 LRU 缓存。`stringWidth()` 每次调用都重新计算。

**Qwen Code 修改方向**：① `npm install mnemonist`（或自建简易 LRU）；② 在 `textUtils.ts` 中包裹 `stringWidth()` 和 `toCodePoints()`；③ 高亮缓存。

**实现成本评估**：
- 涉及文件：~3 个
- 新增代码：~100 行
- 开发周期：~1 天（1 人）
- 难点：选择合适的缓存上限（Gemini 用 20000）

**改进前后对比**：
- **改进前**：每次击键 → `stringWidth()` 重新计算所有可见行 → 10-30ms 延迟
- **改进后**：每次击键 → 95%+ 行缓存命中 → <1ms 延迟

**意义**：文本宽度计算是 TUI 最热的代码路径——缓存命中率极高（大量重复文本）。
**缺失后果**：每次击键都完整计算字符串宽度——CJK 和 ANSI 内容开销更大。
**改进收益**：LRU 缓存 + ASCII 快速路径 = 击键零感知延迟。

---

<a id="item-5"></a>

### 5. 紧凑工具视图 — DenseToolMessage（P1）

**问题**：工具执行结果（特别是 diff）在标准视图中占用大量垂直空间。一个修改了 3 个文件的编辑操作可能占 60+ 行——推开 Agent 的文本回复，用户需要大量滚动。

**Gemini CLI 的解决方案**：`DenseToolMessage` 组件提供紧凑视图——diff 折叠到 15 行，文件列表用单行摘要，状态图标居左对齐。搭配 `COMPACT_TOOL_SUBVIEW_MAX_LINES=15` 常量。

**Gemini CLI 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `packages/cli/src/ui/components/messages/DenseToolMessage.tsx` | 紧凑工具消息渲染 |
| `packages/cli/src/ui/constants.ts#L67` | `COMPACT_TOOL_SUBVIEW_MAX_LINES=15` |

**Qwen Code 现状**：有 `CompactToolGroupDisplay.tsx`（PR#2770 新增），但这是 compact/verbose 模式切换——compact 模式**完全隐藏**输出。没有 Gemini 的"紧凑但仍可见"的中间态。

**Qwen Code 修改方向**：① 从上游复制 `DenseToolMessage.tsx`；② 适配 Qwen Code 的主题和类型系统；③ 作为 verbose 模式的默认渲染器（而非完整输出）。

**实现成本评估**：
- 涉及文件：~3 个
- 新增代码：~300 行
- 开发周期：~2 天（1 人）
- 难点：适配 Qwen Code 的 diff 渲染管线

**改进前后对比**：
- **改进前**：3 个文件的 diff → 60 行输出 → Agent 回复被推到终端底部
- **改进后**：3 个文件的 diff → 15 行紧凑视图 → Agent 回复始终可见

**意义**：compact 模式太极端（完全不可见），verbose 模式太宽松（无限高度）。DenseToolMessage 是两者之间的"刚好"。
**缺失后果**：verbose 模式下 diff 占用过多空间。
**改进收益**：紧凑 diff = 信息可见 + 空间可控。

---

<a id="item-6"></a>

### 6. 组件 React.memo() 化（P1）

**问题**：`HistoryItemDisplay` 是消息列表的核心组件——每条消息一个实例。当新消息到达时，React 默认会重新渲染**所有** `HistoryItemDisplay` 实例，即使旧消息的 props 没有变化。50 条消息的列表 → 每次新增触发 50 次不必要的渲染。

**Gemini CLI 的解决方案**：

```typescript
// MainContent.tsx
const MemoizedHistoryItemDisplay = memo(HistoryItemDisplay);
const MemoizedAppHeader = memo(AppHeader);
```

**Gemini CLI 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `packages/cli/src/ui/components/MainContent.tsx#L28-29` | `memo(HistoryItemDisplay)` + `memo(AppHeader)` |

**Qwen Code 现状**：`MainContent.tsx` 直接使用 `HistoryItemDisplay`，未包裹 `React.memo()`。

**Qwen Code 修改方向**：① `HistoryItemDisplay` 包裹 `React.memo()`；② `AppHeader` 包裹 `React.memo()`；③ 确保 props 为引用稳定（避免内联对象/函数破坏 memo）。

**实现成本评估**：
- 涉及文件：~2 个
- 新增代码：~5 行
- 开发周期：~0.5 天（1 人）
- 难点：确保 props 引用稳定——如果有内联对象/回调，需要提升到 `useMemo`/`useCallback`

**改进前后对比**：
- **改进前**：50 条消息 → 新消息到达 → React 重渲染全部 50 个 HistoryItemDisplay
- **改进后**：50 条消息 → 新消息到达 → 仅渲染 1 个新增的 HistoryItemDisplay

**意义**：消息列表是 TUI 最大的组件树——memo 化直接减少 98% 的不必要渲染。
**缺失后果**：每条新消息触发全量重渲染 → 长会话时明显卡顿。
**改进收益**：`memo()` = O(1) 渲染而非 O(n)。

---

<a id="item-7"></a>

### 7. 字符上限降级（P1）

**问题**：`ToolMessage.tsx` 的 `MAXIMUM_RESULT_DISPLAY_CHARACTERS` 控制工具输出的字符截断阈值。Qwen Code 设为 1,000,000（1MB），Gemini CLI 设为 20,000（20KB）——50 倍差距。1MB 的文本在终端中约 25,000 行——远超用户可消化的范围，但 Ink 仍需完整布局。

**Gemini CLI 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `packages/cli/src/ui/components/shared/SlicingMaxSizedBox.tsx#L12` | `MAXIMUM_RESULT_DISPLAY_CHARACTERS=20000` |

**Qwen Code 现状**：`ToolMessage.tsx#L44`：`MAXIMUM_RESULT_DISPLAY_CHARACTERS=1000000`。

**Qwen Code 修改方向**：将 `MAXIMUM_RESULT_DISPLAY_CHARACTERS` 从 `1000000` 改为 `20000`。一行改动。

**实现成本评估**：
- 涉及文件：1 个
- 修改代码：1 行
- 开发周期：~5 分钟
- 难点：无

**改进前后对比**：
- **改进前**：工具输出 1MB → Ink 布局 25,000 行 → 严重卡顿
- **改进后**：工具输出 1MB → 截断到 20KB（~500 行）→ 布局快速

**意义**：这是最低成本的防闪烁改进——改一个数字。
**缺失后果**：1MB 文本进入 Ink 布局 = 必然卡顿。
**改进收益**：50 倍的数据量削减 = 50 倍的布局性能提升。

---

<a id="item-8"></a>

### 8. 虚拟化列表 — VirtualizedList（P2）

**问题**：长会话可能有 200+ 条消息。当前所有消息的 React 组件都存在于虚拟 DOM 中，即使大部分已滚动出视口。每次状态更新都要遍历全部组件树。

**Gemini CLI 的解决方案**：`VirtualizedList` 只为可视区域内的项创建真实 React 节点，离屏项用 `StaticRender`（预渲染为静态文本，不参与 React reconciliation）。

**Gemini CLI 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `packages/cli/src/ui/components/shared/VirtualizedList.tsx` | `VirtualizedListItem` + `StaticRender` + `memo()` |

**Qwen Code 现状**：`MainContent.tsx` 使用 Ink 的 `<Static>` 组件处理历史消息，但所有 pending 消息仍全量渲染。

**Qwen Code 修改方向**：从上游复制 `VirtualizedList.tsx` 和 `StaticRender`；在消息列表中替换直接 `.map()` 渲染。

**实现成本评估**：
- 涉及文件：~3 个
- 新增代码：~200 行
- 开发周期：~2 天（1 人）
- 难点：正确计算可视区域边界 + ResizeObserver 的生命周期管理

**改进前后对比**：
- **改进前**：200 条消息 → React 维护 200 个组件 → 状态更新遍历全部
- **改进后**：200 条消息 → React 只维护 ~15 个可视组件 → 93% 的组件不参与更新

**意义**：长会话是重度用户的核心场景——虚拟化是列表性能的终极方案。
**缺失后果**：200+ 消息会话时明显卡顿。
**改进收益**：渲染成本从 O(总消息数) 降到 O(可视区域)。

---

<a id="item-9"></a>

### 9. 批量滚动 — useBatchedScroll（P2）

**问题**：滚动操作（鼠标滚轮、快捷键翻页）可能在同一个事件循环 tick 内触发多次。每次滚动都更新状态 → 触发重新渲染 → 一个 tick 内多次渲染 = 浪费。

**Gemini CLI 的解决方案**：`useBatchedScroll` hook 用 `useRef` 暂存 pending 滚动位置，`useLayoutEffect` 在渲染后重置。同一 tick 内的多次滚动合并为一次渲染。

**Gemini CLI 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `packages/cli/src/ui/hooks/useBatchedScroll.ts` | `getScrollTop()` + `setPendingScrollTop()` |

**Qwen Code 现状**：无批量滚动机制。

**实现成本评估**：
- 涉及文件：~2 个（新建 1 个，修改 1 个）
- 新增代码：~30 行
- 开发周期：~0.5 天（1 人）
- 难点：确保 `useLayoutEffect` 在正确的时机重置 pending state

**改进前后对比**：
- **改进前**：快速滚动 → 1 tick 内 3 次状态更新 → 3 次渲染
- **改进后**：快速滚动 → 1 tick 内合并为 1 次渲染

---

<a id="item-10"></a>

### 10. Scrollable 滚动容器（P2）

**问题**：Ink 内置的 `Box` 组件支持 `overflowY="scroll"` 但缺少锚定（新内容到达时自动滚到底部）、动画滚动条、backbuffer 支持等功能。

**Gemini CLI 的解决方案**：自建 `Scrollable` 组件，使用 `ResizeObserver` 监听内容高度变化，自动锚定到底部，搭配 `useAnimatedScrollbar` 提供渐隐滚动条。

**Gemini CLI 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `packages/cli/src/ui/components/shared/Scrollable.tsx` | `overflowToBackbuffer` + `stableScrollback` + ResizeObserver |
| `packages/cli/src/ui/hooks/useAnimatedScrollbar.ts` | 三阶段动画：fade in → visible → fade out |

**Qwen Code 现状**：无 `Scrollable` 组件。长内容使用 `MaxSizedBox` 截断而非滚动。

**实现成本评估**：
- 涉及文件：~3 个
- 新增代码：~300 行
- 开发周期：~2 天（1 人）

---

<a id="item-11"></a>

### 11. 终端能力管理器 — terminalCapabilityManager（P2）

**问题**：不同终端模拟器支持不同的特性——Kitty 支持完整的键盘协议（可检测 Ctrl+Shift+Letter），iTerm2 支持图片内联，WezTerm 支持 hyperlinks。当前 Qwen Code 不检测终端能力，无法利用高级特性。

**Gemini CLI 的解决方案**：`terminalCapabilityManager.ts` 集中管理：Kitty 键盘协议启用/禁用、bracketed paste mode、鼠标事件监听、终端清理序列。

**Gemini CLI 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `packages/cli/src/ui/utils/terminalCapabilityManager.ts` | Kitty 协议 + bracketed paste + 鼠标事件 + cleanup |
| `packages/cli/src/ui/hooks/useKittyKeyboardProtocol.ts` | Kitty 键盘协议 React hook |

**Qwen Code 现状**：无终端能力检测。

**实现成本评估**：
- 涉及文件：~2 个
- 新增代码：~200 行
- 开发周期：~2 天（1 人）

---

<a id="item-12"></a>

### 12. URL 安全检测 — urlSecurityUtils（P2）

**问题**：Agent 输出的 URL 可能包含 Unicode 同形攻击——用 Cyrillic 字母 `а`（U+0430）替代 Latin `a`（U+0061），使 `аpple.com` 看起来像 `apple.com`。用户点击这类 URL 会进入钓鱼网站。

**Gemini CLI 的解决方案**：`urlSecurityUtils.ts` 检测 Punycode 标记和混合 Unicode 脚本，对可疑 URL 标记警告。

**Gemini CLI 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `packages/cli/src/ui/utils/urlSecurityUtils.ts` | 同形攻击检测 + Punycode 验证 |

**Qwen Code 现状**：无 URL 安全检测。

**实现成本评估**：
- 涉及文件：~1 个
- 新增代码：~100 行
- 开发周期：~1 天（1 人）
- 难点：Unicode 脚本分类的完整性

---

<a id="item-14"></a>

### 14. Shell 命令参数补全（P2）

**问题**：用户在嵌入式 shell 中输入 `git checkout ` 后，应该能补全分支名。输入 `npm run ` 后应该能补全 `package.json` 中定义的 scripts。

**Gemini CLI 的解决方案**：`shell-completions/` 目录下的 provider 系统：`gitProvider.ts`（git 分支/tag/远程补全）、`npmProvider.ts`（npm scripts 补全）。

**Gemini CLI 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `packages/cli/src/ui/hooks/shell-completions/gitProvider.ts` | Git 命令参数补全 |
| `packages/cli/src/ui/hooks/shell-completions/npmProvider.ts` | npm scripts 补全 |
| `packages/cli/src/ui/hooks/shell-completions/types.ts` | 补全 provider 接口 |

**Qwen Code 现状**：仅有斜杠命令补全和文件路径补全（PR#2879），无 shell 命令参数补全。

**实现成本评估**：
- 涉及文件：~4 个
- 新增代码：~300 行
- 开发周期：~2 天（1 人）

---

<a id="item-15"></a>

### 15. 任务追踪工具 — trackerTools（P2）

**问题**：复杂任务需要拆分为子任务，子任务之间有依赖关系。当前 Qwen Code 只有 `TodoWriteTool`（简单清单），无法表达依赖、阻塞、可视化进度。

**Gemini CLI 的解决方案**：`trackerTools.ts` 提供 6 个子工具：
- `TRACKER_CREATE_TASK` — 创建任务
- `TRACKER_UPDATE_TASK` — 更新状态（pending/in_progress/completed/cancelled/blocked）
- `TRACKER_ADD_DEPENDENCY` — 添加依赖关系
- `TRACKER_GET_TASK` — 获取单个任务
- `TRACKER_LIST_TASKS` — 列出所有任务
- `TRACKER_VISUALIZE` — 可视化任务拓扑

**Gemini CLI 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `packages/core/src/tools/trackerTools.ts` | 6 个 tracker 子工具 |

**Qwen Code 现状**：仅 `TodoWriteTool`（平面清单，无依赖/阻塞/可视化）。

**实现成本评估**：
- 涉及文件：~3 个
- 新增代码：~500 行
- 开发周期：~3 天（1 人）
- 难点：依赖拓扑的正确性验证（循环检测）

---

<a id="item-16"></a>

### 16. 自定义 Ink 构建（P3）

**问题**：标准 Ink 6.x 在高频更新场景下可能有渲染瓶颈——每次 `setState` 都触发完整 Yoga 布局 + ANSI 差分输出。

**Gemini CLI 的解决方案**：使用 `@jrichman/ink@6.6.7`（自定义 fork），可能包含 Yoga 布局缓存、ANSI 输出批量化等底层优化。

**Qwen Code 现状**：使用标准 `ink@6.2.3`。

**实现成本评估**：
- 难度：大（需要评估自定义 fork 的改动范围和兼容性）
- 建议先完成 P0-P1 的应用层优化，再评估是否需要 Ink 底层优化

---

<a id="item-17"></a>

### 17. 超长回复分片渲染 — GeminiMessageContent（P3）

**问题**：模型生成超长回复（10,000+ token）时，单个 React 组件渲染全部内容 → Ink 的 Yoga 布局计算成本随文本量线性增长。

**Gemini CLI 的解决方案**：`GeminiMessageContent` 将超长回复拆分为多个子组件，每个子组件渲染一部分——利用 React 的增量渲染特性，避免单次布局计算过大。

**Gemini CLI 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `packages/cli/src/ui/components/messages/GeminiMessageContent.tsx` | 回复分片渲染 |

**Qwen Code 现状**：`GeminiMessage.tsx` 单组件渲染完整回复。

**实现成本评估**：
- 涉及文件：~2 个
- 新增代码：~150 行
- 开发周期：~1 天（1 人）

---

<a id="item-18"></a>

### 18. 闪烁检测器 — useFlickerDetector（P3）

**问题**：终端闪烁是多因素导致的——输出量过大、渲染过慢、终端模拟器不支持同步输出。很难在开发时覆盖所有场景。需要运行时检测机制。

**Gemini CLI 的解决方案**：`useFlickerDetector` hook 检测渲染频率异常（如 1 秒内渲染超过 N 次），自动启用缓解策略（如降低更新频率、增大 debounce 间隔）。

**Gemini CLI 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `packages/cli/src/ui/hooks/useFlickerDetector.ts` | 闪烁检测 + 自动缓解 |

**Qwen Code 现状**：无闪烁检测机制。

**实现成本评估**：
- 涉及文件：~2 个
- 新增代码：~80 行
- 开发周期：~1 天（1 人）

---

<a id="item-19"></a>

### 19. 环境变量净化（P0）

**问题**：Agent 执行 shell 命令时继承当前进程的全部环境变量。如果开发者的 `.env` 或 shell profile 中包含 `AWS_SECRET_ACCESS_KEY`、`GITHUB_TOKEN`、`DATABASE_URL` 等敏感信息，这些 secrets 会被传递到 Agent 执行的每一个子进程中——包括 `npm install`（可能运行 postinstall 脚本）、`curl`（可能泄漏到日志）等。

**Gemini CLI 的解决方案**：`environmentSanitization.ts` 实现多层过滤：
- **Always Allowed**（25+ 变量）：`PATH`、`HOME`、`LANG`、`SHELL`、`TERM`、`TMPDIR`、`USER` 等
- **Never Allowed 名称**（11 个正则）：匹配 `TOKEN`、`SECRET`、`PASSWORD`、`KEY`、`AUTH`、`CREDENTIAL`、`PRIVATE`、`CERT` 等
- **Never Allowed 值模式**（8 个正则）：RSA/PGP 私钥、GitHub token（`ghp_`/`gho_`/`ghu_`）、Google API key（`AIzaSy...`）、AWS Access Key（`AKIA...`）、OAuth/JWT token、Stripe/Slack token
- GitHub Actions 严格模式：只放行 allowlist

**Gemini CLI 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `packages/core/src/services/environmentSanitization.ts` | `sanitizeEnvironment()` + 名称/值模式匹配 |

**Qwen Code 现状**：无环境变量过滤。`environmentContext.ts` 仅提供工作区上下文信息，不做净化。

**Qwen Code 修改方向**：① 新建 `environmentSanitization.ts`；② 在 shell 执行前调用 `sanitizeEnvironment(process.env)`；③ 配置允许/阻断自定义列表。

**实现成本评估**：
- 涉及文件：~2 个
- 新增代码：~200 行
- 开发周期：~1.5 天（1 人）
- 难点：平衡安全性和可用性——过度过滤会导致 shell 命令因缺少环境变量而失败

**改进前后对比**：
- **改进前**：`npm install` 的 postinstall 脚本能读到 `AWS_SECRET_ACCESS_KEY` → 供应链攻击风险
- **改进后**：敏感变量被过滤 → postinstall 只能访问 `PATH`、`HOME` 等安全变量

**意义**：环境变量泄漏是 CLI Agent 最常见的安全风险之一。
**缺失后果**：每个子进程都能读取所有 secrets → 恶意 npm 包可窃取凭证。
**改进收益**：环境净化 = 默认安全，secrets 不离开主进程。

---

<a id="item-20"></a>

### 20. 危险命令黑名单（P0）

**问题**：Qwen Code 用 AST 分析判断命令是否"只读"，但无法检测特定危险模式——`find . -exec rm {} \;`（AST 分析可能只看到 `find`）、`git -c core.hooksPath=/tmp/evil git pull`（通过 git config 注入代码）、`rg --pre 'evil.sh'`（ripgrep 的 `--pre` 执行任意脚本）。

**Gemini CLI 的解决方案**：`commandSafety.ts` 维护深度验证规则：

| 命令 | 黑名单模式 |
|------|-----------|
| `find` | `-exec`、`-execdir`、`-ok`、`-delete`、`-fls`、`-fprint*` |
| `git` | `-c`、`--config-env`（代码执行）；允许只读子命令：`status`、`log`、`diff`、`show` |
| `rg` | `--pre`、`--hostname-bin`（任意脚本执行） |
| `sed` | 仅允许 `sed -n {N}p`（行打印），阻断脚本 |
| `base64` | `-o`、`--output`（文件重定向） |
| `rm` | `-rf`、`-f`（强制删除） |

同时检测危险操作符：子 shell `()`、文件重定向 `>`/`>>`/`<`。

**Gemini CLI 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `packages/core/src/sandbox/utils/commandSafety.ts` | `isKnownSafeCommand()` + `isDangerousCommand()` + 每工具深度验证 |
| `packages/core/src/utils/shell-utils.ts` | `hasRedirection()` + `parseCommandDetails()` + `getCommandRoots()` |

**Qwen Code 现状**：`shellAstParser.ts` 做 AST 只读分析，`shell-semantics.ts` 提取操作语义。无显式危险命令黑名单。

**Qwen Code 修改方向**：① 新建 `commandSafety.ts`；② 在权限检查前增加黑名单过滤；③ 按工具深度验证参数。

**实现成本评估**：
- 涉及文件：~2 个
- 新增代码：~250 行
- 开发周期：~2 天（1 人）
- 难点：规则完整性——需要持续维护危险模式列表

**改进前后对比**：
- **改进前**：Agent 执行 `find . -exec rm -rf {} \;` → AST 只看到 `find` → 判为只读 → 直接执行
- **改进后**：检测到 `find -exec` → 标记为危险 → 要求用户确认

---

<a id="item-21"></a>

### 21. Edit 模糊匹配 — Levenshtein 距离恢复（P1）

**问题**：Agent 生成的 `old_string` 经常与文件实际内容有微小差异——空格 vs Tab、尾部空格、引号风格。当前 Qwen Code 只支持精确匹配，任何差异都导致编辑失败 → Agent 重试 → 浪费 token。

**Gemini CLI 的解决方案**：`edit.ts`（1333 行，Qwen 的 2 倍）实现 4 级匹配策略：
1. **精确匹配**
2. **柔性匹配**（空白变体）
3. **正则匹配**
4. **模糊匹配**（Levenshtein 距离，`FUZZY_MATCH_THRESHOLD=0.1` 允许 10% 差异，空白惩罚因子 0.1x）

使用 `fast-levenshtein` 库计算编辑距离，匹配失败时还会尝试 LLM 修复（`FixLLMEditWithInstruction`）。

**Gemini CLI 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `packages/core/src/tools/edit.ts#L55-77` | `FUZZY_MATCH_THRESHOLD=0.1` + `WHITESPACE_PENALTY_FACTOR=0.1` |
| `packages/core/src/tools/edit.ts#L966-1190` | 模糊匹配实现 + Levenshtein |

**Qwen Code 现状**：`edit.ts`（658 行）仅精确匹配 + 归一化字符串比较。

**Qwen Code 修改方向**：① `npm install fast-levenshtein`；② 在精确匹配失败后增加模糊匹配回退；③ 可选 LLM 修复层。

**实现成本评估**：
- 涉及文件：~1 个
- 新增代码：~250 行
- 开发周期：~2 天（1 人）
- 难点：模糊匹配阈值调优——太宽松可能错误匹配

**改进前后对比**：
- **改进前**：`old_string` 有 1 个空格差异 → 匹配失败 → Agent 重试 2-3 次 → 浪费 token
- **改进后**：精确失败 → 模糊匹配（10% 容差）→ 找到正确位置 → 一次成功

**意义**：编辑工具是 Agent 使用频率最高的工具——匹配成功率直接影响任务效率。
**缺失后果**：空白差异导致编辑失败率高 → Agent 反复重试。
**改进收益**：模糊匹配 = 首次编辑成功率从 ~80% 提升到 ~95%。

---

<a id="item-22"></a>

### 22. 省略占位符检测（P1）

**问题**：LLM 生成文件内容时经常偷懒——用 `// ... rest of methods` 或 `/* remaining implementation */` 等占位符代替实际代码。如果直接写入，会破坏文件完整性。

**Gemini CLI 的解决方案**：`omissionPlaceholderDetector.ts` 检测占位符模式，在 `write-file.ts` 和 `edit.ts` 中拦截包含占位符的内容，返回错误提示要求 LLM 提供完整代码。

**Gemini CLI 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `packages/core/src/tools/omissionPlaceholderDetector.ts` | `detectOmissionPlaceholders()` |
| `packages/core/src/tools/write-file.ts#L519-522` | 写入前拦截 |
| `packages/core/src/tools/edit.ts#L58` | 编辑前拦截 |

**Qwen Code 现状**：无占位符检测。LLM 生成的 `// ... rest` 会被直接写入文件。

**Qwen Code 修改方向**：① 新建 `omissionPlaceholderDetector.ts`（~50 行，正则匹配常见占位符模式）；② 在 write-file 和 edit 工具中调用检测。

**实现成本评估**：
- 涉及文件：~3 个（新建 1 个，修改 2 个）
- 新增代码：~80 行
- 开发周期：~0.5 天（1 人）
- 难点：正则覆盖度——需要匹配多种语言的占位符风格

**改进前后对比**：
- **改进前**：LLM 写入 `// ... rest of the implementation` → 文件被截断 → 编译失败
- **改进后**：检测到占位符 → 拒绝写入 → 提示 LLM 提供完整代码

---

<a id="item-23"></a>

### 23. JIT 上下文发现（P1）

**问题**：Agent 读取 `src/utils/auth.ts` 时，不知道同目录下还有 `README.md` 解释了认证架构、`types.ts` 定义了接口。如果 Agent 能自动获得这些上下文，就能更好地理解文件。

**Gemini CLI 的解决方案**：`jit-context.ts` 在 read-file、write-file、edit 工具执行时，自动发现并附加当前文件所在目录的上下文（如 README、配置文件、类型定义）。

**Gemini CLI 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `packages/core/src/tools/jit-context.ts` | `discoverJitContext()` + `appendJitContext()` |
| `packages/core/src/tools/read-file.ts#L178-186` | 读取后附加 JIT 上下文 |
| `packages/core/src/tools/write-file.ts#L408-416` | 写入后附加 JIT 上下文 |

**Qwen Code 现状**：无 JIT 上下文发现。工具结果只返回文件本身内容。

**实现成本评估**：
- 涉及文件：~4 个（新建 1 个，修改 3 个）
- 新增代码：~150 行
- 开发周期：~1.5 天（1 人）

**改进前后对比**：
- **改进前**：Agent 读取 `auth.ts` → 只看到代码 → 不知道接口定义在 `types.ts`
- **改进后**：Agent 读取 `auth.ts` → 自动获得同目录 README + types.ts 概要 → 理解更深

---

<a id="item-24"></a>

### 24. OS 级 sandbox（P1）

**问题**：Agent 执行的 shell 命令拥有与用户相同的全部系统权限——可以读写任意文件、访问网络、安装软件。一条恶意命令就能造成不可逆损害。

**Gemini CLI 的解决方案**：平台级进程隔离：
- **Linux**：Bubblewrap (bwrap) + seccomp BPF 过滤
- **macOS**：Seatbelt profile（`sandbox-exec`）
- **Windows**：受限 token + Job Object + Low Integrity Level

**Gemini CLI 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `packages/core/src/sandbox/linux/LinuxSandboxManager.ts` | bwrap namespace + seccomp |
| `packages/core/src/sandbox/macos/MacOsSandboxManager.ts` | Seatbelt profile |
| `packages/core/src/sandbox/windows/WindowsSandboxManager.ts` | 受限 token + Low IL |
| `packages/core/src/sandbox/utils/commandSafety.ts` | 命令安全验证 |

**Qwen Code 现状**：无 sandbox。shell 命令以用户全权限执行。

**实现成本评估**：
- 涉及文件：~10 个（每平台 ~3 个 + 共享工具）
- 新增代码：~1500 行
- 开发周期：~10 天（1 人）
- 难点：跨平台兼容性、sandbox 逃逸防护、权限粒度控制

**改进前后对比**：
- **改进前**：Agent 执行 `rm -rf /` → 直接以用户权限运行 → 灾难
- **改进后**：Agent 执行 `rm -rf /` → sandbox 限制文件系统访问范围 → 命令失败

---

<a id="item-25"></a>

### 25. Folder Trust 发现（P2）

**问题**：用户用 `cd malicious-repo && qwen-code` 打开一个不受信任的项目。该项目的 `.qwen/` 目录可能包含恶意 hooks、自动批准的工具 allowlist、甚至 sandbox 禁用配置。当前 Qwen Code 不扫描这些配置就直接信任。

**Gemini CLI 的解决方案**：`FolderTrustDiscoveryService.ts` 在信任文件夹前扫描并警告：
- 自定义命令、MCP 服务器、hooks、skills、agents
- 工具 allowlist（自动审批工具 = 安全风险）
- Sandbox 禁用尝试
- Folder trust 禁用尝试

**Gemini CLI 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `packages/core/src/services/FolderTrustDiscoveryService.ts` | 预执行扫描 + 安全警告 |

**Qwen Code 现状**：`trustedHooks.ts` 仅追踪已信任的 hooks，无预执行扫描。

**实现成本评估**：
- 涉及文件：~2 个
- 新增代码：~300 行
- 开发周期：~2 天（1 人）

---

<a id="item-26"></a>

### 26. Web Fetch 速率限制与 SSRF 加固（P2）

**问题**：Agent 的 web-fetch 工具可能被 LLM 指令注入利用来扫描内网（SSRF）。当前 Qwen Code 仅做基础的私有 IP 检查。

**Gemini CLI 的解决方案**：
- **速率限制**：10 次/分钟/host
- **Async DNS 验证**：解析后验证 IP 是否为私有地址（防 DNS rebinding）
- **IANA 基准测试段阻断**：`198.18.0.0/15` 显式阻断
- **IPv4-mapped IPv6 处理**：检测 `::ffff:10.0.0.1` 等绕过
- **内容限制**：250KB + 截断警告

**Gemini CLI 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `packages/core/src/tools/web-fetch.ts` | 速率限制 + SSRF 防护 |
| `packages/core/src/utils/fetch.ts` | `isPrivateIp()` + `isPrivateIpAsync()` + `isLoopbackHost()` |

**Qwen Code 现状**：`web-fetch.ts` 有 `isPrivateIp()` 但无速率限制、无 async DNS 验证、无 IANA 段阻断。内容限制 100KB。

**实现成本评估**：
- 涉及文件：~2 个
- 新增代码：~150 行
- 开发周期：~1.5 天（1 人）

---

<a id="item-27"></a>

### 27. Grep 高级参数（P2）

**问题**：Agent 搜索代码时经常需要"只在 `.ts` 文件中搜索"或"排除 `node_modules`"或"只要文件名"。当前 Qwen Code 的 grep 工具仅支持 `pattern`、`path`、`glob`、`limit`，缺少精细控制。

**Gemini CLI 的解决方案**：新增参数：
- `include_pattern`：文件 glob 过滤
- `exclude_pattern`：正则排除匹配结果
- `names_only`：只返回文件路径
- `max_matches_per_file`：每文件匹配上限
- `total_max_matches`：总结果上限

**Gemini CLI 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `packages/core/src/tools/grep.ts#L45-80` | 扩展参数定义 |
| `packages/core/src/tools/grep-utils.ts` | `formatGrepResults()` 格式化输出 |

**Qwen Code 现状**：`grep.ts` 仅 `pattern`/`path`/`glob`/`limit` 4 个参数。

**实现成本评估**：
- 涉及文件：~1 个
- 新增代码：~100 行
- 开发周期：~1 天（1 人）

---

<a id="item-28"></a>

### 28. 高级 Vim 操作（P2）

**问题**：Qwen Code 的 vim 模式仅支持基础词操作（`dw`/`db`/`de`/`cw`/`cb`/`ce`）。重度 vim 用户需要大词操作（`dW`/`cW`）、查找操作（`f`/`F`/`t`/`T`）、替换字符（`r`）、大小写切换（`~`）等。

**Gemini CLI 的解决方案**：`vim.ts`（49KB，远大于 Qwen 版本）实现完整 vim 操作集：
- 大词操作：`dW`/`dB`/`dE`/`cW`/`cB`/`cE`/`yW`/`yE`
- 查找操作：`f`/`F`/`t`/`T` + `lastFind` 记忆重复
- 替换字符：`r`
- 大小写切换：`~`
- 行操作：`d0`/`d^`/`dgg`/`dG`/`cgg`/`cG`
- Yank 操作：`yy`/`yw`/`yW`/`ye`/`yE`/`y$` + paste `p`/`P`

**Gemini CLI 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `packages/cli/src/ui/hooks/vim.ts` | 完整 vim 模式实现（49KB） |

**Qwen Code 现状**：`vim.ts` 仅基础操作。

**实现成本评估**：
- 涉及文件：~1 个
- 新增代码：~500 行
- 开发周期：~3 天（1 人）

---

<a id="item-29"></a>

### 29. Footer 自定义（P2）

**问题**：Footer 显示状态信息（cwd、vim 模式、审批模式等），但不同用户关注不同指标——有人想看内存，有人想看 context 用量，有人不需要 sandbox 状态。当前 Footer 是固定布局。

**Gemini CLI 的解决方案**：`FooterConfigDialog` 允许用户选择显示哪些状态指示器，配置持久化到 settings。

**Gemini CLI 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `packages/cli/src/ui/components/FooterConfigDialog.tsx` | 配置对话框 |
| `packages/cli/src/ui/components/footerItems.ts` | 可配置项定义 |

**Qwen Code 现状**：`Footer.tsx` 固定布局，不可自定义。

**实现成本评估**：
- 涉及文件：~3 个
- 新增代码：~200 行
- 开发周期：~1.5 天（1 人）

---

<a id="item-30"></a>

### 30. Write File LLM 内容修正（P2）

**问题**：LLM 生成的文件内容可能包含错误的转义、缺失的闭合标签、JSON 语法错误等。直接写入会导致编译/解析失败。

**Gemini CLI 的解决方案**：`write-file.ts` 中 `getCorrectedFileContent()` 在写入前调用 LLM 校正畸形内容（可选激进 unescape 模式）。

**Gemini CLI 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `packages/core/src/tools/write-file.ts#L100-143` | `getCorrectedFileContent()` LLM 校正 |

**Qwen Code 现状**：直接写入 LLM 输出，无校正层。

**实现成本评估**：
- 涉及文件：~1 个
- 新增代码：~100 行
- 开发周期：~1 天（1 人）
- 难点：LLM 校正的额外延迟和 token 成本

---

<a id="item-31"></a>

### 31. OAuth 流程重构（P3）

**问题**：Qwen Code 的 MCP OAuth 实现是内联的——认证流程、PKCE 参数生成、token 交换全部写在 `oauth-provider.ts` 中。无法复用给其他 OAuth 场景（如 Agent-to-Agent 认证）。

**Gemini CLI 的解决方案**：抽取共享 `oauth-flow.ts`（协议无关），支持 PKCE（64 字节 verifier）、RFC 9728 protected resource metadata、OIDC 路径发现（Keycloak 等）。

**Gemini CLI 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `packages/core/src/utils/oauth-flow.ts` | 共享 OAuth 流程工具 |
| `packages/core/src/mcp/oauth-utils.ts` | `ResourceMismatchError` + RFC 9728 |

**Qwen Code 现状**：`oauth-provider.ts` 内联实现，不可复用。

**实现成本评估**：
- 涉及文件：~3 个
- 新增代码：~200 行
- 开发周期：~2 天（1 人）

---

<a id="item-32"></a>

### 32. Conseca 安全框架（P3）

**问题**：缺少基于对话上下文的动态安全评估——同一条命令 `rm config.json` 在"清理测试文件"的上下文中是安全的，在"删除生产配置"的上下文中是危险的。静态规则无法区分。

**Gemini CLI 的解决方案**：`safety/conseca/` 框架：
- `policy-generator.ts`：根据用户意图和对话历史生成安全策略
- `policy-enforcer.ts`：在工具调用时执行策略（ALLOW/DENY/ASK_USER）
- `registry.ts`：可扩展的 checker 链，支持插件式安全检查器
- `protocol.ts`：标准化输入/输出格式，支持外部 checker via stdin/stdout

**Gemini CLI 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `packages/core/src/safety/conseca/conseca.ts` | 安全检查单例 |
| `packages/core/src/safety/conseca/policy-generator.ts` | 策略生成 |
| `packages/core/src/safety/conseca/policy-enforcer.ts` | 策略执行 |
| `packages/core/src/safety/registry.ts` | checker 注册 |

**Qwen Code 现状**：无内容安全评估。依赖静态权限规则。

**实现成本评估**：
- 涉及文件：~5 个
- 新增代码：~500 行
- 开发周期：~5 天（1 人）
- 难点：策略生成的 LLM 调用成本与延迟权衡

---

<a id="item-33"></a>

### 33. Tool Output Masking — 上下文窗口优化（P1）

**问题**：Agent 执行 `cat large-file.json`（5000 行）或 `npm test`（输出 200 行），工具结果全量注入上下文窗口。几轮操作后，上下文被大量工具输出填满，挤压了 Agent 的推理空间和用户的 prompt。

**Gemini CLI 的解决方案**：`toolOutputMaskingService.ts` 实现 "Hybrid Backward Scanned FIFO" 算法：
- 保护最近 50k token 不被裁剪
- 从最旧的大体积工具输出开始替换为"摘要 + 文件路径引用"
- 豁免高信号工具（memory、ask_user、activate_skill）
- 主要裁剪 shell 输出和文件读取结果

**Gemini CLI 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `packages/core/src/context/toolOutputMaskingService.ts` | Hybrid Backward Scanned FIFO 裁剪 |

**Qwen Code 现状**：工具输出全量保留在上下文中，依赖压缩时统一处理。

**互补方案**：[RTK](https://github.com/rtk-ai/rtk)（23,650 stars）从**命令执行端**解决同一问题——通过 Hook 拦截 Agent 的 shell 命令，在输出**进入上下文之前**就过滤压缩（58 个 TOML 声明式规则，覆盖 git/npm/cargo/pytest 等 100+ 命令）。RTK 实测 30 分钟会话节省 118K→24K token（-80%）。两者互补：RTK 在**输入端**减少 token，Tool Output Masking 在**历史端**裁剪已有的大输出。

**Qwen Code 修改方向**：① 新建 `toolOutputMaskingService.ts`；② 在发送 API 请求前对历史消息中的大工具输出做预览替换；③ 配置保护区大小和豁免工具列表。也可考虑在 shell 工具中内置类似 RTK 的输出过滤能力（声明式 TOML 规则），从源头减少 token 消耗。

**实现成本评估**：
- 涉及文件：~2 个
- 新增代码：~300 行
- 开发周期：~2 天（1 人）
- 难点：确定裁剪阈值——太激进会丢失重要上下文

**改进前后对比**：
- **改进前**：5 轮工具调用 → 上下文被工具输出填满 → Agent 推理空间不足 → 频繁压缩
- **改进后**：旧工具输出自动替换为摘要 → 上下文保持健康 → 压缩频率降低

**意义**：上下文窗口是 Agent 最稀缺的资源——工具输出裁剪直接延长有效会话长度。
**缺失后果**：大工具输出快速耗尽上下文 → 频繁压缩 → 丢失对话连贯性。
**改进收益**：自动裁剪 = 上下文利用率提升 50%+。

---

<a id="item-34"></a>

### 34. /rewind 检查点回退（P1）

**问题**：Agent 在第 20 轮做了一个错误决策（比如重构了不该改的文件），用户想"回到第 18 轮的状态"。当前只能手动 `git checkout` 恢复文件，且对话历史无法回退。

**Gemini CLI 的解决方案**：`/rewind` 命令 + `RewindViewer` 组件 + `rewindFileOps.ts`：
- 可视化每轮的文件变化影响
- 选择目标轮次后，恢复文件到该轮状态
- 截断对话历史到目标轮次
- 确认对话框防止误操作

**Gemini CLI 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `packages/cli/src/ui/hooks/useRewind.ts` | 回退逻辑 + 轮次统计 |
| `packages/cli/src/ui/components/RewindViewer.tsx` | 回退可视化 |
| `packages/cli/src/ui/utils/rewindFileOps.ts` | 文件恢复操作 |
| `packages/cli/src/ui/commands/rewindCommand.tsx` | `/rewind` 命令 |

**Qwen Code 现状**：无 `/rewind` 命令。用户只能手动恢复文件。

**实现成本评估**：
- 涉及文件：~4 个
- 新增代码：~400 行
- 开发周期：~3 天（1 人）
- 难点：文件恢复的原子性——需要处理中间状态

**改进前后对比**：
- **改进前**：Agent 错误修改了 5 个文件 → 手动 `git diff` + `git checkout` 逐个恢复 → 5 分钟
- **改进后**：`/rewind 18` → 确认 → 文件 + 对话自动回退到第 18 轮 → 5 秒

---

<a id="item-35"></a>

### 35. Model Availability Service（P1）

**问题**：模型可能因配额耗尽、容量不足、服务降级等原因临时不可用。当前 Qwen Code 在遇到 429/503 错误时简单重试，没有健康追踪和智能降级。

**Gemini CLI 的解决方案**：`availability/` 模块追踪每个模型的健康状态：
- **健康状态**：available / sticky_retry / terminal
- **错误分类**：配额错误 vs 容量错误 vs 终端错误
- **策略目录**：每个模型有独立的降级策略
- **自动降级**：主模型不可用时自动切换到 fallback 模型

**Gemini CLI 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `packages/core/src/availability/modelAvailabilityService.ts` | 健康追踪 + 状态机 |
| `packages/core/src/availability/errorClassification.ts` | 错误分类 |
| `packages/core/src/availability/policyCatalog.ts` | 模型降级策略 |
| `packages/core/src/availability/fallbackIntegration.ts` | 降级集成 |

**Qwen Code 现状**：有分离的重试预算（内容/流异常/速率限制），但无模型健康追踪和自动降级。

**实现成本评估**：
- 涉及文件：~5 个
- 新增代码：~500 行
- 开发周期：~3 天（1 人）

---

<a id="item-36"></a>

### 36. Markdown 渲染切换 — Alt+M（P2）

**问题**：Agent 输出的 Markdown 经过渲染后（加粗、列表、代码块），有时用户想看原始 Markdown 源码——比如复制代码块时不想包含渲染字符，或者调试 Markdown 格式问题。

**Gemini CLI 的解决方案**：Alt+M（macOS: Option+M）切换渲染/原始 Markdown 视图，`RawMarkdownIndicator` 组件显示当前模式。

**Gemini CLI 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `packages/cli/src/ui/components/RawMarkdownIndicator.tsx` | 模式指示器 |
| `packages/cli/src/ui/key/keyBindings.ts` | `Command.TOGGLE_MARKDOWN` + Alt+M |

**Qwen Code 现状**：无 Markdown 渲染切换。

**实现成本评估**：
- 涉及文件：~3 个
- 新增代码：~50 行
- 开发周期：~0.5 天（1 人）

---

<a id="item-37"></a>

### 37. A2A Agent-to-Agent 协议（P2）

**问题**：复杂任务可能需要多个专业 Agent 协作——代码 Agent 写代码，测试 Agent 跑测试，部署 Agent 发布。当前 Qwen Code 的 Subagent 是进程内的，无法与远程 Agent 通信。

**Gemini CLI 的解决方案**：完整的 A2A 协议实现：
- `a2a-client-manager.ts`：协议协商 + 认证 + 传输选择
- 专用 `packages/a2a-server/` 包
- 支持 gRPC / REST / JsonRpc 传输
- 30 分钟超时（支持 Deep Research 等长任务）

**Gemini CLI 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `packages/core/src/agents/a2a-client-manager.ts` | 远程 Agent 通信管理 |
| `packages/a2a-server/` | A2A 服务端 |

**Qwen Code 现状**：仅进程内 Subagent 和 Arena 竞赛模式，无远程 Agent 通信。

**实现成本评估**：
- 涉及文件：~10 个
- 新增代码：~1000 行
- 开发周期：~7 天（1 人）
- 难点：协议兼容性、认证、错误恢复

---

<a id="item-38"></a>

### 38. Workspace TOML Policy（P2）

**问题**：团队想对项目中 Agent 的行为设置统一规则——禁止修改 `production.config`、限制只能使用特定工具、要求所有 shell 命令需确认。当前只能通过权限规则逐条设置。

**Gemini CLI 的解决方案**：项目根目录放置 `.gemini/policies/*.toml` 文件，定义策略规则。`PolicyEngine` 在运行时解析并执行策略，支持完整性校验防篡改。

**Gemini CLI 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `packages/cli/src/config/policy.ts` | `createPolicyEngineConfig()` + 策略引擎 |
| `packages/core/src/policy/` | 策略定义 + 完整性管理 |

**Qwen Code 现状**：仅 `permission-manager.ts` 规则匹配，无 TOML 策略文件支持。

**实现成本评估**：
- 涉及文件：~5 个
- 新增代码：~400 行
- 开发周期：~3 天（1 人）

---

<a id="item-39"></a>

### 39. 后台 Shell 管理工具（P2）

**问题**：Agent 启动了 `npm run dev` 后台进程，但无法查看它的状态、读取输出、或终止它。当前 `is_background` 参数只能启动后台进程，没有后续管理能力。

**Gemini CLI 的解决方案**：`shellBackgroundTools.ts` 提供 4 个专用工具：
- `ListBackgroundProcesses`：列出所有后台进程
- `GetBackgroundProcessStatus`：获取特定进程状态
- `WaitForBackgroundProcess`：等待进程完成
- `TerminateBackgroundProcess`：终止进程

**Gemini CLI 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `packages/core/src/tools/shellBackgroundTools.ts` | 4 个后台管理工具 |
| `packages/cli/src/ui/hooks/useBackgroundTaskManager.ts` | UI 层后台任务管理 |

**Qwen Code 现状**：仅 `is_background` 参数启动后台进程，无管理工具。

**实现成本评估**：
- 涉及文件：~3 个
- 新增代码：~300 行
- 开发周期：~2 天（1 人）

---

<a id="item-40"></a>

### 40. Wave-based 并行工具调度（P2）

**问题**：Agent 一次返回多个工具调用（如 3 个 read_file + 1 个 write_file），当前按顺序执行。但只读工具之间没有依赖，可以并行。

**Gemini CLI 的解决方案**：`scheduler/scheduler.ts` 将工具调用分成"波次"（wave），每波内的工具并发执行：
- `[read, read, write, read]` → 波次 1: `[read, read]` 并发 → 波次 2: `[write]` → 波次 3: `[read]`
- 自动检测读写依赖关系

**Gemini CLI 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `packages/core/src/scheduler/scheduler.ts` | 波次划分 + 并发执行 |
| `integration-tests/parallel-tools.test.ts` | 并行工具集成测试 |

**Qwen Code 现状**：`CoreToolScheduler` 仅对 Agent/Task 工具并行，其他工具串行。

**实现成本评估**：
- 涉及文件：~2 个
- 新增代码：~200 行
- 开发周期：~2 天（1 人）
- 难点：读写依赖分析——需要正确识别哪些工具是只读的

---

<a id="item-41"></a>

### 41. Ctrl+Z 终端挂起（P3）

**问题**：用户按 Ctrl+Z 期望像普通终端程序一样挂起到后台，但 Ink 框架默认不处理 SIGTSTP。

**Gemini CLI 的解决方案**：`useSuspend.ts` hook 管理挂起/恢复流程：退出 raw mode → 退出 alternate screen → 发送 SIGTSTP → 恢复时重建终端状态。双击 Ctrl+Z 检测防误触。

**Gemini CLI 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `packages/cli/src/ui/hooks/useSuspend.ts` | 挂起/恢复 + 终端状态管理 |

**Qwen Code 现状**：无 Ctrl+Z 挂起支持。

**实现成本评估**：
- 涉及文件：~2 个
- 新增代码：~80 行
- 开发周期：~0.5 天（1 人）

---

<a id="item-42"></a>

### 42. Shell 不活跃超时（P3）

**问题**：交互式 shell 命令（如 `python` REPL）可能在等待输入时看起来像"卡住了"。需要在标题栏显示不活跃状态提示。

**Gemini CLI 的解决方案**：`useShellInactivityStatus.ts` 配合 `useInactivityTimer.ts`，在 shell 输出停止后显示 "Action required" 或 "Silently working" 标题。可通过 `shellInactivityTimeoutMs` 配置。

**Gemini CLI 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `packages/cli/src/ui/hooks/useShellInactivityStatus.ts` | Shell 不活跃检测 |
| `packages/cli/src/ui/hooks/useInactivityTimer.ts` | 通用不活跃计时器 |

**Qwen Code 现状**：无 shell 不活跃检测。

**实现成本评估**：
- 涉及文件：~2 个
- 新增代码：~60 行
- 开发周期：~0.5 天（1 人）

---

<a id="item-43"></a>

### 43. Startup Profiler（P3）

**问题**：CLI 启动慢但不知道瓶颈在哪——是 MCP 连接？配置加载？扩展初始化？需要分阶段计时。

**Gemini CLI 的解决方案**：`StartupProfiler` 单例，track 每个启动阶段的 CPU 时间，通过 `DebugProfiler.tsx` 组件展示，集成到遥测系统。

**Gemini CLI 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `packages/core/src/telemetry/startupProfiler.ts` | 阶段计时 + CPU 采样 |
| `packages/cli/src/ui/components/DebugProfiler.tsx` | 性能数据展示 |

**Qwen Code 现状**：无启动性能分析。

**实现成本评估**：
- 涉及文件：~2 个
- 新增代码：~100 行
- 开发周期：~1 天（1 人）

---

<a id="item-44"></a>

### 44. Model Routing 多策略路由（P1）

**问题**：Qwen Code 直接使用用户指定的模型，没有智能路由层。当请求类型不同（代码生成 vs 问答 vs 审查）时，同一模型并非最优选择。也没有根据模型负载/容量自动切换的能力。

**Gemini CLI 的解决方案**：`ModelRouterService`——可组合的多策略路由引擎，支持 8 种策略：

| 策略 | 功能 |
|------|------|
| `DefaultStrategy` | 默认模型选择 |
| `OverrideStrategy` | 用户/配置强制指定 |
| `ApprovalModeStrategy` | 根据审批模式选择（ask/always） |
| `ClassifierStrategy` | 基于 LLM 分类器选择最优模型 |
| `GemmaClassifierStrategy` | Gemma 本地分类器快速路由 |
| `NumericalClassifierStrategy` | 数值分类器（token 数/复杂度） |
| `CompositeStrategy` | 组合多个策略 |
| `FallbackStrategy` | 主策略失败时降级 |

路由决策包含完整元数据（source、latencyMs、reasoning），集成遥测日志。

**Gemini CLI 源码索引**：

| 文件 | 关键函数/类 |
|------|-------------|
| `packages/core/src/routing/routingStrategy.ts` | `RoutingDecision`, `RoutingContext`, `RoutingStrategy` 接口 |
| `packages/core/src/routing/modelRouterService.ts` | `ModelRouterService` 主服务 |
| `packages/core/src/routing/strategies/` | 8 个策略实现文件 |

**Qwen Code 现状**：无模型路由层。用户通过 `/model` 命令直接指定模型，不根据请求类型自动选择。

**Qwen Code 修改方向**：实现简化版路由——至少支持 Default + Override + Fallback 三层策略。分类器路由需要本地小模型（Gemma），可作为进阶功能。

**实现成本评估**：
- 涉及文件：~8 个（新建路由层 + 修改模型选择入口）
- 新增代码：~500 行（简化版）
- 开发周期：~3 天（1 人）
- 难点：策略组合的正确性 + 与现有多 Provider 系统的集成

**改进前后对比**：
- **改进前**：用户手动选模型 → 简单任务浪费高端模型配额
- **改进后**：路由器自动选最优模型 → 省配额 + 更好匹配

---

<a id="item-45"></a>

### 45. Agent Session 协议层（P1）

**问题**：Qwen Code 的 Agent 通信是同步调用式——发请求、等结果。无法做事件回放、流中断恢复、多流并行管理。

**Gemini CLI 的解决方案**：`AgentSession`——基于 AsyncIterable 的 Agent 通信协议，支持事件历史和重新附加：

- `AgentSession`：AsyncIterable 包装，支持 streamId 追踪和事件历史
- `EventTranslator`：协议事件格式转换
- `ContentUtils`：Agent 消息内容类型转换
- `LegacyAgentSession`：向后兼容旧协议

**Gemini CLI 源码索引**：

| 文件 | 关键函数/类 |
|------|-------------|
| `packages/core/src/agent/agent-session.ts` | `AgentSession` 主类 |
| `packages/core/src/agent/event-translator.ts` | 事件格式转换 |
| `packages/core/src/agent/content-utils.ts` | 内容类型工具 |
| `packages/core/src/agent/types.ts` | Agent 协议类型定义 |

**Qwen Code 现状**：`packages/core/src/agents/` 存在但结构不同，无 AsyncIterable 协议、无事件回放、无流管理。

**实现成本评估**：
- 涉及文件：~6 个（新建协议层 + 适配现有 Agent 系统）
- 新增代码：~400 行
- 开发周期：~3 天（1 人）
- 难点：与现有 Arena/Agent Team 系统的兼容

---

<a id="item-46"></a>

### 46. Session Browser 会话浏览器（P1）

**问题**：Qwen Code 的会话恢复依赖 `--resume` 命令行参数或 `/restore` 命令，需要用户记住会话 ID。无法在 TUI 内交互式浏览和搜索历史会话。

**Gemini CLI 的解决方案**：完整的 Session Browser 组件系列：

| 组件 | 功能 |
|------|------|
| `SessionBrowserNav` | 主导航组件（列表 + 键盘导航） |
| `SessionBrowserSearchNav` | 搜索过滤（模糊匹配） |
| `SessionListHeader` | 会话列表标题栏 |
| `SessionBrowserLoading` | 加载状态 |
| `SessionBrowserError` | 错误状态 |
| `SessionBrowserEmpty` | 空状态 |

**Gemini CLI 源码索引**：

| 文件 | 行数 |
|------|:----:|
| `packages/cli/src/ui/components/SessionBrowser/SessionBrowserNav.tsx` | ~120 |
| `packages/cli/src/ui/components/SessionBrowser/SessionBrowserSearchNav.tsx` | ~80 |
| `packages/cli/src/ui/components/SessionBrowser/SessionListHeader.tsx` | ~50 |

**Qwen Code 现状**：仅有 `--resume`、`/restore`、`/resume` 命令行方式。无交互式会话浏览。

**实现成本评估**：
- 涉及文件：~6 个（新建组件 + 集成到命令系统）
- 新增代码：~400 行
- 开发周期：~2 天（1 人）
- 难点：会话列表渲染性能（如果会话数很多）

---

<a id="item-47"></a>

### 47. A2A Server 服务端包（P2）

**问题**：item-37 已覆盖 A2A 客户端协议，但没有服务端实现——Agent 只能**调用**远程 Agent，不能**被调用**。

**Gemini CLI 的解决方案**：独立的 `packages/a2a-server/` 包（33 文件 9,044 行），提供：
- HTTP 应用服务器接受远程 Agent 请求
- Agent 执行器管理远程任务生命周期
- 超时管理（30 分钟默认）
- 与 A2A 客户端配套形成双向 Agent 通信

**Gemini CLI 源码索引**：`packages/a2a-server/src/` 目录

**Qwen Code 现状**：无 A2A 支持（客户端和服务端均无）。

**实现成本评估**：
- 新增代码：~1000+ 行
- 开发周期：~5 天（1 人）
- 前置依赖：需先实现 Agent Session 协议层（item-45）

---

<a id="item-48"></a>

### 48. DevTools Inspector 调试面板（P2）

**问题**：Agent 在运行时的 API 调用、工具执行、错误日志无法实时观察。出问题时只能看最终输出，无法追溯过程。

**Gemini CLI 的解决方案**：`packages/devtools/` 提供 Web 端实时调试面板：
- WebSocket 服务器（端口 25417）
- 网络日志（API 请求/响应）实时流式推送
- 控制台日志收集和回放
- 多 CLI 实例同时连接支持
- 日志大小限制防止内存泄漏

**Gemini CLI 源码索引**：

| 文件 | 关键函数 |
|------|---------|
| `packages/devtools/src/devtools-viewer.ts` | HTTP 服务器 + WebSocket 推送 |

**Qwen Code 现状**：无调试面板。只有 `--verbose` 命令行日志。

**实现成本评估**：
- 涉及文件：~3 个
- 新增代码：~400 行
- 开发周期：~2 天（1 人）

---

<a id="item-49"></a>

### 49. MCP Resource Registry 资源注册表（P2）

**问题**：MCP 服务器除了提供 tools 外，还可以暴露 resources（文档、数据库、文件等），但 Qwen Code 只消费 tools，忽略了 resources。

**Gemini CLI 的解决方案**：`ResourceRegistry` 中央注册表：
- 按 URI 查找资源（格式：`server-name/resource-uri`）
- 按服务器过滤资源列表
- 发现时间戳追踪（用于缓存失效）
- 与 MCP 服务器生命周期集成

**Gemini CLI 源码索引**：

| 文件 | 关键类 |
|------|--------|
| `packages/core/src/resources/resource-registry.ts` | `ResourceRegistry` |

**Qwen Code 现状**：MCP 客户端仅消费 tools，不处理 resources。

**实现成本评估**：
- 涉及文件：~2 个
- 新增代码：~150 行
- 开发周期：~0.5 天（1 人）

---

<a id="item-50"></a>

### 50. Voice Response Formatter 语音格式化（P2）

**问题**：Agent 的 Markdown 输出包含代码块、ANSI 颜色码、表格等，直接用 TTS 朗读效果极差。

**Gemini CLI 的解决方案**：`responseFormatter.ts`（473 行）将 Markdown 转为语音友好文本：
- ANSI 颜色码剥离
- 代码块折叠为 JSON 摘要
- Stack trace 折叠
- Markdown 语法移除（加粗/斜体/链接/列表/引用/标题）
- 路径缩写（保留最后 N 段）
- 长度截断 + 溢出提示

**Gemini CLI 源码索引**：`packages/core/src/voice/responseFormatter.ts`

**Qwen Code 现状**：无语音/TTS 支持。

**实现成本评估**：
- 涉及文件：~2 个
- 新增代码：~200 行（可直接参考上游实现）
- 开发周期：~1 天（1 人）

---

<a id="item-51"></a>

### 51. Triage 代码问题检测（P2）

**问题**：Agent 缺少主动的代码质量分析能力——无法自动识别 Issue 或检测重复代码模式。

**Gemini CLI 的解决方案**：两个大型 UI 组件：
- `TriageIssues.tsx`（~700 行）——代码问题识别与展示
- `TriageDuplicates.tsx`（~1000 行）——重复代码模式检测与高亮

**Gemini CLI 源码索引**：`packages/cli/src/ui/components/triage/`

**Qwen Code 现状**：无专用代码分析 UI 组件。

**实现成本评估**：
- 涉及文件：~3 个
- 新增代码：~800 行
- 开发周期：~3 天（1 人）
- 难点：需要分析引擎（MCP 或内置）

---

<a id="item-52"></a>

### 52. CodeAssist 企业集成（P2）

**问题**：Qwen Code 面向个人开发者，缺少企业级管理能力——用户分层、管理员策略、MCP 管控。

**Gemini CLI 的解决方案**：`packages/core/src/code_assist/`（26 文件 9,825 行），集成 Google Cloud CodeAssist：
- 用户分层（免费/标准/付费）
- 管理员控制（强制 MCP 服务器、工具白名单/黑名单）
- 客户端元数据（IDE 类型、平台、版本）
- 隐私通知管理
- Onboarding 流程支持
- OAuth2 服务账户凭据

**Gemini CLI 源码索引**：`packages/core/src/code_assist/` 完整目录

**Qwen Code 现状**：无企业集成。使用免费 OAuth 额度模型。

**实现成本评估**：
- 新增代码：~2000+ 行
- 开发周期：~10 天（需要后端配合）
- 难点：需要企业管理后端服务

**意义**：商业化必经之路。Google 已经建好了这套基础设施，值得在需要时参考其 API 设计。

---

<a id="item-53"></a>

### 53. Billing/Credits 计费系统（P2）

**问题**：当用户免费额度耗尽时，没有优雅的处理方式——要么硬停止、要么不限制。

**Gemini CLI 的解决方案**：`packages/core/src/billing/`（3 文件 449 行）：
- 信用类型追踪（`GOOGLE_ONE_AI`）
- 超额策略配置：`ask`（询问用户）/ `always`（自动付费）/ `never`（硬停止）
- 模型付费资格检查
- UTM 追踪用于信用购买流程
- 与 CodeAssist 分层系统集成

**Gemini CLI 源码索引**：`packages/core/src/billing/`

**Qwen Code 现状**：免费模型，无计费系统。

**实现成本评估**：
- 涉及文件：~3 个
- 新增代码：~300 行
- 开发周期：~2 天（1 人，不含后端）

---

<a id="item-54"></a>

### 54. 流式高度稳定化 — useStableHeight（P0）

**问题**：即使 SlicingMaxSizedBox（item-1）解决了大数据量的闪烁，流式输出期间仍然存在第二类闪烁——`availableTerminalHeight` 因 footer 重测量、工具数变化、tab bar 切换而波动，导致显示行数跳动。

**来源**：[QwenLM/qwen-code PR#3013](https://github.com/QwenLM/qwen-code/pull/3013) Phase 2（社区贡献，chiga0）。

**解决方案**：`useStableHeight` Hook，在流式输出期间缓存高度值：

| 场景 | 策略 |
|------|------|
| 高度增加 | 立即接受（更多空间不会跳动） |
| 小幅减少（<5 行）+ 流式中 | 吸收——MaxSizedBox 视觉裁剪溢出 |
| 大幅减少（≥5 行）或缓存过期（>2s） | 接受为真实布局变化 |
| 空闲状态 | 立即同步 |

**同时新增**：`MIN_TOOL_OUTPUT_HEIGHT = 8` 防止工具数变化时每个工具高度剧烈跳动（如 2→3 工具时从 15→9 行）。

**源码索引**（PR#3013）：

| 文件 | 关键函数 |
|------|---------|
| `packages/cli/src/ui/hooks/useStableHeight.ts` | 65 行，高度缓存 + 阈值过滤 |
| `packages/cli/src/ui/components/messages/ToolGroupMessage.tsx` | `MIN_TOOL_OUTPUT_HEIGHT` 下限 |
| `packages/cli/src/ui/AppContainer.tsx` | Shell PTY 使用原始高度（不稳定化） |

**Qwen Code 现状**：无高度稳定化。`availableTerminalHeight` 直接传入组件。

**Review 状态**：PR#3013 Phase 2 已实现，但 Review 指出 `useStableHeight` 在 render 中 mutate ref 是 React 反模式（StrictMode 下 `Date.now()` 会被调用两次），建议改用 `useMemo` 或 `useEffect` + state。

**实现成本评估**：
- 涉及文件：~3 个
- 新增代码：~80 行
- 开发周期：~0.5 天（1 人）

**与 item-1 的关系**：item-1 解决"数据量大导致的闪烁"（O(n)→O(15)），item-54 解决"高度波动导致的闪烁"。两者配合才能完全消除闪烁。

**改进前后对比**：
- **改进前**：流式输出时 footer 重测量 → 高度波动 → 行数跳动 → 闪烁
- **改进后**：useStableHeight 吸收小幅波动 → 高度稳定 → 无跳动


---

<a id="item-55"></a>

### 55. Memory 系统重构 — Prompt-Driven 4 层编辑（P1）

**问题**：Qwen Code 的 `MemoryManager`（继承自上游早期版本）通过**专用 agent**（`MemoryManagerAgent`）执行记忆编辑——每次更新都要单独 spawn 一个子 agent 调用模型，开销大、链路长、与主对话上下文割裂。

**来源**：[Gemini CLI PR#25716](https://github.com/google-gemini/gemini-cli/pull/25716) `refactor(memory): replace MemoryManagerAgent with prompt-driven memory editing across four tiers`，2026-04-21 合并。

**解决方案**：删掉 `MemoryManagerAgent`（157 行）+ `memory-manager-agent.test.ts`（160 行），改为**主 agent 直接通过 prompt 编辑 4 层记忆**：

```
Tier 1: 项目级 (.qwen/memory.md or QWEN.md project)
Tier 2: 全局级 (~/.qwen/memory.md)
Tier 3: 会话级 (in-memory session state)
Tier 4: 上下文级 (per-turn temporary)
```

主 agent 在 system prompt 中拿到 4 层当前内容 + 编辑指令模板，直接生成 `add_memory` / `delete_memory` / `update_memory` 工具调用，无需 spawn 子 agent。

**核心收益**：
- 消除一次额外的模型调用（save_memory 路径延迟 ~50%）
- 主 agent 保持完整对话上下文，记忆编辑决策更准确
- `evals/save_memory.eval.ts` 扩充 312 行测试覆盖 4 层场景

**Qwen Code 现状**：`config.ts:703` `MemoryManager` 单层（user memory），无分层、无 agent，结构上反而比 Gemini 旧设计**更简单**——但缺 4 层语义和 prompt-driven 编辑能力。

**Qwen Code 修改方向**：
1. 扩展 `MemoryManager` 支持 4 层（project / global / session / turn）
2. system prompt 注入"当前 4 层快照 + 编辑示例"
3. 主 agent 通过 `add_memory` 工具按 tier 写入
4. 测试覆盖 4 层互不干扰

**实现成本**：~3 天（1 人）。已删除的 MemoryManagerAgent 代码可作为反向参考（"不要这样做"）。

---

<a id="item-56"></a>

### 56. 安全 .env 加载 + Workspace Trust Headless 模式（P0 · 安全关键）

**问题**：headless / CI 模式下，恶意 `.env` 文件可以静默注入 API key、URL、PROXY 等敏感配置，agent 启动时就把 secrets 暴露给所有子进程。Qwen Code 与 Gemini 同样的 fork 期 bug。

**来源**：3 个互补的上游 PR，均 2026-04-22~23 合并：

| PR | 修复 |
|---|---|
| [Gemini PR#25022](https://github.com/google-gemini/gemini-cli/pull/25022) | **RCE Fix**：禁止 workspace `.env` 覆盖 IDE stdio 配置——避免 `IDE_STDIO=evil-script` 注入 |
| [Gemini PR#25814](https://github.com/google-gemini/gemini-cli/pull/25814) | **secure .env loading**：headless 模式下 enforce workspace trust，未信任的 workspace 不加载 `.env` |
| [Gemini PR#24170](https://github.com/google-gemini/gemini-cli/pull/24170) | **Command injection shell**：shell 命令构造路径修复注入漏洞 |

**核心机制**：
1. `.env` 加载前先检查 `workspace.trust` 状态（settings.json）
2. headless mode（`-p` / CI / SDK）默认 `untrusted` 除非显式 `--trust-workspace`
3. 关键 env keys（`IDE_STDIO` / `MCP_*_COMMAND` / `*_HOOK` 等）即使 workspace 信任也**禁止** `.env` 覆盖（必须从 user settings 显式声明）
4. shell 命令构造走结构化 args 而非 string concat（PR#24170）

**Qwen Code 现状**：
- `loadEnvironment()` 直接读 `.env` 无 trust 检查
- `acpAgent.ts` 提到 `IDE_STDIO` 但无 .env override 防护
- headless 模式（`qwen -p`）不区分 trusted vs untrusted workspace

**Qwen Code 修改方向**：
1. `config.ts` 加 `loadEnvironment()` 入口的 `requireTrustedWorkspace` 守卫
2. 维护 `BLOCKED_ENV_OVERRIDES = ['IDE_STDIO', 'MCP_*_COMMAND', '*_HOOK', ...]` 黑名单
3. `qwen -p` 默认行为改为：未 `~/.qwen/trust.json` 标记则不加载 workspace `.env`
4. 添加 `--trust-workspace` 显式开关 + warning 提示

**实现成本**：~2 天（1 人）。**P0 优先级**——这是已知可被利用的 RCE 路径。

---

<a id="item-57"></a>

### 57. Core Tools Allowlist + Shell 命令验证增强（P1）

**问题**：Qwen Code 的工具权限是**deny-list 模型**（"除了这些之外都允许"），新增工具时如果没显式 deny 就默认开放。安全 posture 偏宽松。

**来源**：[Gemini PR#25720](https://github.com/google-gemini/gemini-cli/pull/25720) `feat(core): enhance shell command validation and add core tools allowlist`，2026-04-23 合并。

**解决方案**：
1. **Core tools allowlist**：`settingsSchema.ts` 新增 `tools.coreToolsAllowlist`——白名单模式，**只允许列出的工具**，未列出的全部 deny
2. **`policy/core-tools-mapping.test.ts`**（76 行）：核心工具到 policy 规则的精确映射
3. **`shell-substitution.test.ts`**（97 行）：覆盖 `$(...)` / 反引号 / `${...}` / heredoc 等 shell substitution 攻击向量
4. **`shell-safety-regression.test.ts`**（134 行）：历史漏洞回归用例

**配置示例**：
```jsonc
{
  "tools": {
    "coreToolsAllowlist": ["read_file", "write_file", "shell"]
    // ↑ 启用后只有这 3 个 core tool 可用，其他全 deny
  }
}
```

**Qwen Code 现状**：`policy-engine.ts` 是 allow/ask/deny 三态，但配置层只有 `coreTools` 黑名单（deny-list），无白名单模式。

**Qwen Code 修改方向**：
1. `settings.json` schema 新增 `tools.coreToolsAllowlist: string[]`
2. policy-engine 优先级：`allowlist (if set) > deny rules > default ask`
3. 移植 `shell-substitution.test.ts` 96 个 case 到 Qwen 的 shell tool 测试套件
4. 文档说明 allowlist 模式的 trade-off（更安全但需用户主动维护）

**实现成本**：~3 天（含测试移植）。

---

<a id="item-58"></a>

### 58. Boot 性能 — 异步 Experiments / Quota 拉取（P1）

**问题**：启动时同步拉取 GrowthBook experiments + quota 信息（用于 feature flag 和模型选择），冷启动延迟 200-500ms。Qwen Code 同样的问题（继承自上游早期）。

**来源**：[Gemini PR#25758](https://github.com/google-gemini/gemini-cli/pull/25758) `perf(core): fix slow boot by fetching experiments and quota asynchronously`，2026-04-23 合并。

**解决方案**：
1. Experiments + quota fetch 改为 fire-and-forget Promise，启动**不阻塞**
2. 首个 turn 真正需要 feature flag 时再 await（一般已经返回）
3. fallback：未返回时用 cached snapshot 或 hardcoded default

**核心收益**：冷启动 -300ms 左右（用户感知显著）。

**Qwen Code 现状**：`config.ts` 启动期同步加载 modelsConfig + auth + telemetry。无 experiments/quota 概念但有类似的同步初始化路径（如 `modelRegistry.warmAll()`、`toolRegistry.warmAll()`）可借鉴异步化思路。

**Qwen Code 修改方向**：
1. 审计 `init()` 中所有可异步化的 fetch（modelRegistry / toolRegistry / mcpServers）
2. 改为 lazy promise + 首次访问 await
3. 测试启动延迟前后对比

**实现成本**：~2 天。

---

<a id="item-59"></a>

### 59. `@` 文件推荐 — Watcher-based 增量更新（P2）

**问题**：用户输入 `@`触发文件补全时，Qwen Code 当前每次都重新扫描 workspace。新建的文件可能因为缓存未刷新而不出现，或者扫描慢导致补全延迟。

**来源**：[Gemini PR#25256](https://github.com/google-gemini/gemini-cli/pull/25256) `feat: detect new files in @ recommendations with watcher based updates`，2026-04-22 合并。

**解决方案**：
1. `chokidar` 文件系统 watcher 监听 workspace 变化
2. 增量更新候选文件列表（add / unlink / rename）
3. `useAtCompletion` Hook 直接读 in-memory 缓存，无需重新 glob
4. settings 提供开关（`atRecommendations.watcher.enabled`）

**Qwen Code 现状**：`useAtCompletion`（如果存在）每次扫描，无 watcher。

**Qwen Code 修改方向**：直接 backport，文件层基本通用。注意 watcher 资源限制（大型 monorepo 可能有 inotify 上限问题，需要 `usePolling` fallback）。

**实现成本**：~1 天。

---

<a id="item-60"></a>

### 60. Skill 提取质量门 — Recurrence Evidence + Skill-Creator Agent（P2）

**问题**：Qwen Code 的 skill 提取容易把"一次性事件"误识别为可复用 skill（如某次特殊调试经历被存成 skill）。结果 skill 库充满低价值噪音。

**来源**：2 个上游 PR：

| PR | 改进 |
|---|---|
| [Gemini PR#25147](https://github.com/google-gemini/gemini-cli/pull/25147) `improve(core): require recurrence evidence before extracting skills` | 提取前**要求至少 N 次重复发生**作为证据 |
| [Gemini PR#25421](https://github.com/google-gemini/gemini-cli/pull/25421) `feat(core): integrate skill-creator into skill extraction agent` | 提取 agent 与 `skill-creator` agent 集成，使用 LLM 生成结构化 skill 定义 |

**核心机制**：
1. 用户行为流入 skill candidate 池前先做 fingerprint
2. `recurrenceCount >= MIN_RECURRENCE` 才进入提取队列（默认 3）
3. 提取 agent 调用 skill-creator 生成 SKILL.md frontmatter + body
4. 同 fingerprint skill 后续触发只更新 `lastSeenAt` + `count`，不重复创建

**Qwen Code 现状**：skills 系统已有（PR#2949），但提取门槛较低，缺 recurrence 证据机制。

**Qwen Code 修改方向**：
1. `skill-extraction-agent.ts` 引入 `RecurrenceLedger`（持久化 candidate fingerprint + count）
2. 设置 `MIN_RECURRENCE_FOR_EXTRACTION = 3` 配置
3. 集成 `skill-creator` agent（已存在的 Qwen 内置 skill）作为生成步骤
4. UI 提示："Skill candidate detected (2/3 occurrences)"

**实现成本**：~1 周。

---

<a id="item-61"></a>

### 61. Topic Update Narration + autoMemory 配置拆分（P3）

**问题**：Gemini CLI 在 2026-04 把"topic update narration"（agent 在长对话中主动播报"我们正在讨论 X"）从实验性提升到默认启用，并把 `memoryManager` 配置拆分出独立的 `autoMemory` 标记，避免"想关 auto memory 但同时也关掉了显式 save_memory"的两难。

**来源**：3 个相关 PR：

| PR | 改进 |
|---|---|
| [Gemini PR#25586](https://github.com/google-gemini/gemini-cli/pull/25586) | `enable topic update narration by default and promote to general` |
| [Gemini PR#25567](https://github.com/google-gemini/gemini-cli/pull/25567) | `Disable topic updates for subagents`（subagent 不应该自我播报）|
| [Gemini PR#25601](https://github.com/google-gemini/gemini-cli/pull/25601) | `feat(config): split memoryManager flag into autoMemory` |

**Qwen Code 现状**：`memoryManager` 单一开关；无 topic narration。

**Qwen Code 修改方向**：
1. `settings.json` 拆分 `memoryManager` → `autoMemory`（自动）+ `memoryToolsEnabled`（手动 save_memory 可用性）
2. 实现 topic narration（背景 fastModel 跑摘要 → 长对话每 ~15 turn 输出一行 "── Topic: refactoring auth module ──"）
3. subagent 路径跳过 narration

**实现成本**：~3 天。建议**先实现 autoMemory 拆分**（PR#25601 配置变更，几十行），narration 可选。

---

<a id="item-62"></a>

### 62. 小型 backport 集合（P3）

低优先级但可顺手 backport 的小项：

| Gemini PR | 内容 | Qwen 现状 | 工作量 |
|---|---|---|---|
| [PR#17865](https://github.com/google-gemini/gemini-cli/pull/17865) | `/new` 作为 `/clear` 的 alias | `clearCommand.ts` 无 aliases | 1 行（添加 `aliases: ['new']`）|
| [PR#25801](https://github.com/google-gemini/gemini-cli/pull/25801) | fix `/clear (new)` command bug | 待检查 | 验证后决定 |
| [PR#22620](https://github.com/google-gemini/gemini-cli/pull/22620) | Bun 下禁用 detached mode 防 SIGHUP | 待检查 | 1 行（如果 Qwen 支持 Bun runtime）|
| [PR#25090](https://github.com/google-gemini/gemini-cli/pull/25090) | get-internal-docs 工具支持 `.mdx` | Qwen 无 internal-docs 工具 | 跳过 |
| [PR#25513](https://github.com/google-gemini/gemini-cli/pull/25513) | Vertex AI request routing 设置 | Qwen 用 DashScope/OpenAI-compat 为主 | 跳过 |
| [PR#25497](https://github.com/google-gemini/gemini-cli/pull/25497) | 允许 `GEMINI_API_KEY` 含点 | `QWEN_API_KEY` 待验证 | 验证后决定 |
| [PR#25541](https://github.com/google-gemini/gemini-cli/pull/25541) | seatbelt profile 从 `$HOME/.gemini` 优先 | 改为 `$HOME/.qwen` | 1 行 |
| [PR#25300](https://github.com/google-gemini/gemini-cli/pull/25300) | Use OSC 777 for terminal notifications | Qwen 已经在跟 OSC 9/8 路线 (PR#3562 等) | 评估 OSC 777 vs 9 |
| [PR#25342](https://github.com/google-gemini/gemini-cli/pull/25342) | bundle ripgrep into SEA for offline | **Qwen 已实现**（`packages/core/vendor/ripgrep/` 6 平台）| ✓ 跳过 |

