# Qwen Code 改进建议 — 工具输出限高与防闪烁 (Tool Output Height Limiting & Anti-Flicker)

> 核心洞察：当 Agent 执行 `npm install`（输出数千行）或 `git log`（输出数百行）时，Gemini CLI 的终端始终稳定——输出框固定在 15 行，超出部分静默裁剪。而 Qwen Code 在相同场景下可能出现明显的屏幕闪烁甚至卡顿。根因不在"渲染速度"而在"数据量控制"：Gemini CLI 在 React/Ink 渲染**之前**就把数据裁剪到安全范围，而 Qwen Code 将全部数据交给 Ink 布局，再用 CSS-like 的 `overflow: hidden` 裁剪视觉区域——但布局成本已经产生。
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md)

## 一、问题定义：大输出为什么导致闪烁？

### 1. 闪烁的底层机制

Ink（React for CLI）的渲染流程是：

```
数据变化 → React reconciliation → Ink 布局（测量每个 Box 高度）→ 终端写入
```

当 shell 输出 500 行时：
- **Gemini CLI**：只给 Ink 15 行数据 → 布局快 → 写入快 → 无闪烁
- **Qwen Code**：给 Ink 500 行数据 → 布局慢 → 写入慢 → **每次新增一行都触发完整重新布局** → 闪烁

关键洞察：`MaxSizedBox` 的 `overflow="hidden"` 只是视觉裁剪——**Ink 仍然需要计算全部内容的高度才能决定哪些"溢出"**。这意味着即使用户只看到 15 行，Ink 也在布局 500 行。

### 2. 实际场景

| 操作 | 输出量 | Gemini CLI | Qwen Code |
|------|--------|-----------|-----------|
| `npm install` | ~500 行 | 稳定 15 行窗口 | 闪烁 |
| `git log --oneline` | ~200 行 | 稳定 15 行窗口 | 闪烁 |
| `find . -name "*.ts"` | ~1000 行 | 稳定 15 行窗口 | 严重闪烁 |
| `cat large-file.json` | ~5000 行 | 稳定 15 行窗口 | 卡顿 |
| Subagent 长输出 | ~300 行 | 折叠到 15 行 | 无限增长 |

## 二、为什么 Qwen Code（Gemini CLI fork）缺少这些机制？

Qwen Code 是 Gemini CLI 的 fork 分支，但两者的输出限高能力差异来自**分叉时间点**：

| 事件 | 时间 | 说明 |
|------|------|------|
| Qwen Code 最后一次上游同步 | 2025-10-23 | `Sync upstream Gemini-CLI v0.8.2 (#838)` |
| Gemini CLI 添加 `SlicingMaxSizedBox` | 2026-03-18 | `fix(ui): fix flickering on small terminal heights (#21416)` |
| Gemini CLI 添加 `toolLayoutUtils.ts` | 2026-03-18 | 同一个 PR，引入 `calculateShellMaxLines()` |
| Gemini CLI 添加 `ACTIVE_SHELL_MAX_LINES` 等常量 | 2026-03-09 | `feat(core): improve subagent result display (#20378)` |
| Gemini CLI 完善 compact tool output | 2026-03-30 | `feat(cli): implement compact tool output (#20974)` |

**结论**：Gemini CLI 的整个防闪烁体系（`SlicingMaxSizedBox`、`toolLayoutUtils.ts`、硬上限常量）都是在 2026 年 3 月 Qwen Code 停止同步上游之后才加入的。Qwen Code 的 `ToolMessage.tsx` 停留在 2025 年 10 月的上游状态——那时 Gemini CLI 自身也没有这些机制。

> 注：Qwen Code 在 fork 后独立发展了许多功能（Plan Mode、Team Agent、MCP 增强等），但上游后来解决的闪烁问题没有被回移。

## 三、架构对比

### 1. Gemini CLI 的四层防线（2026-03 新增）

Gemini CLI 使用四层递进式限制确保输出永远不会失控：

```
                        Gemini CLI 数据流
                        
原始数据 (可能 10MB)
  │
  ├─ 第 1 层：后台 buffer 上限
  │   shellReducer.ts: MAX_SHELL_OUTPUT_SIZE = 10MB
  │   超出时 .slice(-10MB) 保留尾部
  │
  ├─ 第 2 层：字符数裁剪
  │   SlicingMaxSizedBox: MAXIMUM_RESULT_DISPLAY_CHARACTERS = 20,000
  │   超出时 .slice() 到 20KB
  │
  ├─ 第 3 层：行数裁剪（渲染前）
  │   SlicingMaxSizedBox: lines.slice(-maxLines)
  │   AnsiOutput: data.slice(-numLinesRetained)
  │   最终只有 ≤15 行进入 React 渲染树
  │
  └─ 第 4 层：视觉裁剪（兜底）
      MaxSizedBox: maxHeight + overflow="hidden"
      即使前三层有遗漏，视觉上也不会溢出
```

源码: `packages/cli/src/ui/components/shared/SlicingMaxSizedBox.tsx`

```typescript
// 第 2 层：20KB 字符上限（渲染前裁剪）
const MAXIMUM_RESULT_DISPLAY_CHARACTERS = 20000;

export function SlicingMaxSizedBox({ data, maxLines, ... }) {
  const { truncatedData } = useMemo(() => {
    // 字符裁剪
    if (typeof data === 'string') {
      if (text.length > MAXIMUM_RESULT_DISPLAY_CHARACTERS) {
        text = '...' + text.slice(-MAXIMUM_RESULT_DISPLAY_CHARACTERS);
      }
      // 行数裁剪
      if (maxLines !== undefined) {
        const lines = text.split('\n');
        if (lines.length > maxLines) {
          const targetLines = Math.max(1, maxLines - 1);
          text = lines.slice(-targetLines).join('\n');  // ← 渲染前只保留最后 N 行
        }
      }
    }
    return { truncatedData: text };
  }, [data, maxLines]);

  // 裁剪后的数据才进入 MaxSizedBox 渲染
  return <MaxSizedBox {...boxProps}>{children(truncatedData)}</MaxSizedBox>;
}
```

### 2. Gemini CLI 的硬上限常量体系

源码: `packages/cli/src/ui/constants.ts`

```typescript
export const ACTIVE_SHELL_MAX_LINES = 15;       // 执行中 shell
export const COMPLETED_SHELL_MAX_LINES = 15;     // 完成的 shell
export const SUBAGENT_MAX_LINES = 15;            // Subagent 输出
export const COMPACT_TOOL_SUBVIEW_MAX_LINES = 15; // Diff 视图
export const MAX_SHELL_OUTPUT_SIZE = 10_000_000;  // 10MB buffer 上限
export const SHELL_OUTPUT_TRUNCATION_BUFFER = 1_000_000; // 1MB 摊销截断
```

源码: `packages/cli/src/ui/utils/toolLayoutUtils.ts`

```typescript
export function calculateShellMaxLines(options) {
  // 用户主动展开 → 无限制
  if (!constrainHeight && isExpandable) return undefined;

  const maxLinesBasedOnHeight = Math.max(
    1, availableTerminalHeight - RESERVED_LINES
  );

  // 关键：取 min(终端可用高度, 硬上限)
  const shellMaxLinesLimit = isExecuting
    ? ACTIVE_SHELL_MAX_LINES - SHELL_CONTENT_OVERHEAD   // = 10
    : COMPLETED_SHELL_MAX_LINES - SHELL_CONTENT_OVERHEAD; // = 10

  return Math.min(maxLinesBasedOnHeight, shellMaxLinesLimit);
  // ↑ 即使终端 200 行高，shell 输出也最多 10 行
}
```

### 3. Qwen Code 的单层防线

Qwen Code 只有一层防线——视觉裁剪：

```
                        Qwen Code 数据流

原始数据 (可能 1MB)
  │
  ├─ 字符截断：MAXIMUM_RESULT_DISPLAY_CHARACTERS = 1,000,000
  │   （1MB！几乎不会触发）
  │
  └─ 视觉裁剪：MaxSizedBox overflow="hidden"
      但 Ink 已经完整布局了全部数据
      → 布局 1MB 文本 → 闪烁
```

源码: `packages/cli/src/ui/components/messages/ToolMessage.tsx`

```typescript
const MAXIMUM_RESULT_DISPLAY_CHARACTERS = 1000000; // 1MB（Gemini 的 50 倍）

// 高度计算：直接用终端高度，无硬上限
const availableHeight = availableTerminalHeight
  ? Math.max(
      availableTerminalHeight - STATIC_HEIGHT - RESERVED_LINE_COUNT,
      MIN_LINES_SHOWN + 1,
    )
  : undefined;  // ← undefined 时完全无限制！

// 无渲染前行数裁剪，数据直接进入 MaxSizedBox
return (
  <MaxSizedBox maxHeight={availableHeight} maxWidth={childWidth}>
    <Text wrap="wrap">{displayData}</Text>  {/* displayData 可能有几万行 */}
  </MaxSizedBox>
);
```

### 4. 关键差异汇总

| 机制 | Gemini CLI | Qwen Code | 差距 |
|------|-----------|-----------|------|
| Shell 输出硬上限 | 15 行（`ACTIVE_SHELL_MAX_LINES`） | 无（= 终端高度） | Gemini 固定 15 行，Qwen 随终端伸缩 |
| Subagent 输出上限 | 15 行（`SUBAGENT_MAX_LINES`） | 无 | Subagent 嵌套时输出无限增长 |
| 渲染前行数裁剪 | `SlicingMaxSizedBox` `.slice(-maxLines)` | 无 | Gemini 裁剪后才渲染，Qwen 全部渲染再裁剪 |
| 字符上限 | 20,000 (20KB) | 1,000,000 (1MB) | 50 倍差距 |
| 后台 buffer 上限 | 10MB + 1MB 摊销截断 | 无 | 长时间运行命令可能耗尽内存 |
| `calculateShellMaxLines()` | 专用函数，区分执行中/完成/聚焦/展开 | 无等价函数 | 缺乏状态感知的精细控制 |
| Markdown 与限高 | 独立处理 | 互斥（限高时禁用 Markdown） | 限高模式损失 Markdown 可读性 |

## 四、Gemini CLI 的额外设计细节

### 1. 用户可展开机制

Gemini CLI 不是死板地限制在 15 行——用户可以按 **Ctrl+S** 展开查看完整输出。展开时 `constrainHeight` 设为 `false`，`calculateShellMaxLines()` 返回 `undefined`，视觉裁剪解除。再按 Ctrl+S 恢复限制。

源码: `packages/cli/src/ui/AppContainer.tsx#L1642-1665`

这个设计兼顾了"默认安全"和"需要时可看全部"。

### 2. 溢出指示器

当内容被裁剪时，`MaxSizedBox` 显示 "... first X line(s) hidden" 或 "... last X line(s) hidden"，告知用户有多少内容被隐藏。`ShowMoreLines` 组件在底部显示 "Press ctrl-s to show more lines" 引导操作。

### 3. 后台 buffer 摊销截断

源码: `packages/cli/src/ui/hooks/shellReducer.ts`

后台运行的 shell 命令输出持续追加到字符串 buffer。为避免频繁截断（每次追加都 `.slice()` 是 O(n)），Gemini CLI 使用摊销策略：只有当 buffer 超过 `MAX_SHELL_OUTPUT_SIZE + SHELL_OUTPUT_TRUNCATION_BUFFER`（11MB）时才截断到 10MB。这将 O(n) 的截断成本分摊到每 1MB 新输入一次。

### 4. AnsiOutput 预裁剪

源码: `packages/cli/src/ui/components/AnsiOutput.tsx`

```typescript
const DEFAULT_HEIGHT = 24;
// 渲染前只保留最后 N 行
const lastLines = data.slice(
  -(availableTerminalHeight ?? DEFAULT_HEIGHT)
);
```

ANSI 输出（含颜色代码）在进入 React 渲染树前就被裁剪到最后 N 行，避免 Ink 解析数千行 ANSI 转义序列。

## 五、Qwen Code PR#2770：compact/verbose 模式（互补方案）

[PR#2770](https://github.com/QwenLM/qwen-code/pull/2770) 从另一个角度解决了同一个问题——不限制输出高度，而是在 compact 模式下**完全隐藏**工具输出：

```
Compact 模式（默认，Ctrl+O 切换）：
  ✓ ReadFile src/index.ts          ← 仅工具名 + 状态图标
  ✓ Edit src/index.ts
  ✓ Bash npm run build

Verbose 模式：
  ✓ ReadFile src/index.ts
    1  import React from 'react';   ← 完整输出可见
    ...
  ✓ Bash npm run build
  ▎ tsc --project tsconfig.json
  ▎ Done in 2.3s
```

**实现机制**：通过 `VerboseModeContext`（React Context）在渲染层过滤——compact 模式下 `ToolMessage` 返回 `{ type: 'none' }`，不渲染输出内容。`frozenSnapshot` 在流式传输期间冻结 pending items 视口，防止切换模式时的布局抖动。设置持久化到 `~/.qwen/settings.json`。

**与 Gemini CLI 方案的互补关系**：

| 维度 | Gemini CLI 高度限制 | PR#2770 compact/verbose |
|------|-------------------|----------------------|
| 解决的问题 | "输出太多行"→ 限制到 15 行 | "要不要看输出"→ 完全隐藏 |
| 默认可见输出 | 15 行（带溢出指示） | 0 行（仅状态图标） |
| 信息密度 | 中（能看到部分输出） | 低（看不到任何输出内容） |
| 防闪烁效果 | 完全解决（渲染前裁剪） | 完全解决（不渲染） |
| 用户操作 | Ctrl+S 展开/折叠 | Ctrl+O 切换模式 |

**最佳方案是两者结合**：compact 模式解决"要不要看"，height limiting 解决 verbose 模式下"看多少"。当前 PR#2770 的 verbose 模式仍然没有高度限制——切换到 verbose 后，大输出的闪烁问题依然存在。

## 六、Qwen Code 改进方案

### 阶段 1：添加硬上限常量和计算函数（最高优先级）

```typescript
// constants.ts — 新增
export const ACTIVE_SHELL_MAX_LINES = 15;
export const COMPLETED_SHELL_MAX_LINES = 15;
export const SUBAGENT_MAX_LINES = 15;

// utils/toolLayoutUtils.ts — 新建
export function calculateShellMaxLines(options: {
  status: ToolCallStatus;
  availableTerminalHeight: number | undefined;
  constrainHeight: boolean;
}): number | undefined {
  if (!constrainHeight) return undefined;
  
  const maxFromTerminal = availableTerminalHeight
    ? Math.max(1, availableTerminalHeight - RESERVED_LINES)
    : ACTIVE_SHELL_MAX_LINES;
  
  const hardLimit = status === ToolCallStatus.Executing
    ? ACTIVE_SHELL_MAX_LINES
    : COMPLETED_SHELL_MAX_LINES;
  
  return Math.min(maxFromTerminal, hardLimit);
}
```

### 阶段 2：降低字符上限 + 渲染前裁剪

```typescript
// ToolMessage.tsx
const MAXIMUM_RESULT_DISPLAY_CHARACTERS = 20000; // 1MB → 20KB

// 新建 SlicingMaxSizedBox 或在 ToolMessage 中预裁剪
const truncatedData = useMemo(() => {
  let text = displayData;
  if (text.length > MAXIMUM_RESULT_DISPLAY_CHARACTERS) {
    text = '...' + text.slice(-MAXIMUM_RESULT_DISPLAY_CHARACTERS);
  }
  if (maxLines) {
    const lines = text.split('\n');
    if (lines.length > maxLines) {
      text = lines.slice(-(maxLines - 1)).join('\n');
    }
  }
  return text;
}, [displayData, maxLines]);
```

### 阶段 3：后台 buffer 上限

为长时间运行的 shell 命令添加 buffer 上限，防止内存无限增长：

```typescript
const MAX_SHELL_OUTPUT_SIZE = 10_000_000;      // 10MB
const TRUNCATION_BUFFER = 1_000_000;           // 1MB 摊销

// shellExecutionService.ts — 追加输出时检查
if (output.length > MAX_SHELL_OUTPUT_SIZE + TRUNCATION_BUFFER) {
  output = output.slice(-MAX_SHELL_OUTPUT_SIZE);
}
```

### 阶段 4：用户可展开 + 溢出指示

添加 Ctrl+S 展开/折叠快捷键，以及 "X lines hidden" 溢出指示。Qwen Code 已有 `constrainHeight` 状态和 `ShowMoreLines` 组件（从 Gemini CLI fork 而来），但需要确保与阶段 1 的硬上限联动。

## 七、改进收益评估

- **实现成本**：小。核心改动集中在 `ToolMessage.tsx`（添加硬上限 + 预裁剪）和新建 `toolLayoutUtils.ts`（~50 行）。总计 ~200 行代码。
- **改进效果**：
  1. 消除大输出场景的屏幕闪烁——从 500 行渲染降到 15 行
  2. 降低 Ink 布局开销——减少 React reconciliation 的 DOM 节点数
  3. 防止长时间运行命令耗尽内存——10MB buffer 上限
  4. Subagent 输出不再无限增长——固定 15 行 + 折叠
- **风险**：低。硬上限 + 用户可展开 = 默认安全 + 需要时可查看全部。

## 八、与现有深度文章的关系

| 相关文章 | 关联点 |
|---------|-------|
| [终端渲染优化](./terminal-rendering-string-pooling-deep-dive.md) | DEC 2026 同步输出、差分渲染等底层渲染优化 |
| [紧凑状态栏](./compact-status-bar-deep-dive.md) | 状态栏高度优化释放更多内容空间 |
| [Shell 输出 FD Bypass](./shell-output-fd-bypass-deep-dive.md) | Shell 输出的底层管道机制 |
