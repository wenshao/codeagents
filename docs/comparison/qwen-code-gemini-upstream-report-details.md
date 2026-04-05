# Qwen Code 上游回移建议详情（Gemini CLI 源码对比）

> 返回 [回移建议矩阵](./qwen-code-gemini-upstream-report.md) | [Claude Code 改进建议](./qwen-code-improvement-report.md)

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
**缺失��果**：长时间运行的 shell 命令耗尽内存。
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
- 涉��文件：~2 个
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

<a id="item-13"></a>

### 13. ANSI-aware 表格渲染器 — TableRenderer（P2）

**问题**：Agent 输出 Markdown 表格时，CJK 字符占 2 列宽、ANSI 转义码不占宽但影响长度计算——标准 `stringWidth()` 不够用。表格列对不齐，中文内容基本不可读。

**Gemini CLI 的解决方案**：`TableRenderer.tsx` 组件，ANSI-aware 列宽计算 + CJK 2-width + 对齐标记（`:---`/`:---:`/`---:`）+ cell 内容自动换行。

> 注：Qwen Code 的 PR#2914 正在实现类似功能——可参考 Gemini CLI 的实现确保覆盖度。

**Gemini CLI 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `packages/cli/src/ui/utils/TableRenderer.tsx` | 完整表格渲染 React 组件 |

**Qwen Code 现状**：`MarkdownDisplay.tsx` 的表格渲染 CJK/ANSI 列对齐不准确。PR#2914 正在修复。

**进展**：[PR#2914](https://github.com/QwenLM/qwen-code/pull/2914)（open）

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
