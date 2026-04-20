# 任务显示高度控制 Deep-Dive——Claude Code vs Qwen Code

> **核心问题**：Claude Code 执行任务时屏幕"紧凑不爆"——工具输出、思考、Todo、进度更新都占最小空间，历史消息不拖性能。Qwen Code 能借鉴什么？
>
> 返回 [Qwen Code 改进建议总览](./qwen-code-improvement-report.md)

## 一、Claude Code 的 4 条高度控制机制

### 1.1 `MessageResponse` 单行容器——**瞬态消息永远只占 1 行**

**源码**：`components/MessageResponse.tsx:37`

```tsx
<MessageResponseProvider>
  <Box flexDirection="row" height={height} overflowY="hidden">
    {t1}{t2}
  </Box>
</MessageResponseProvider>
```

**适用范围**：所有**瞬态消息**——工具进度、Waiting、Running hook、Done、(No output)、图像检测消息、Hook 进度消息。所有这些共享一个 `height={1} overflowY="hidden"` 容器。

**关键设计决策**：
- `height` 属性**外部传入**（默认 1），允许特定组件扩展到更多行
- `overflowY="hidden"` 意味着超出的内容**不是 scroll 而是 clip**——看不到就是看不到
- `flexDirection="row"` 让"前缀符号（⏺/✓/✗） + 主文本"水平排布

**效果**：工具执行中屏幕**始终只多 1 行**，不会因输出量变化而抖动。

---

### 1.2 `OffscreenFreeze` 离屏冻结——**滚出视口的历史零 CPU 成本**

**源码**：`components/OffscreenFreeze.tsx:22-42`

```tsx
export function OffscreenFreeze({ children }: Props): React.ReactNode {
  'use no memo'  // React Compiler: 手动缓存是整个冻结机制，memo 会破坏它

  const inVirtualList = useContext(InVirtualListContext)
  const [ref, { isVisible }] = useTerminalViewport()
  const cached = useRef(children)

  if (isVisible || inVirtualList) {
    cached.current = children  // 可见时更新缓存
  }
  return <Box ref={ref}>{cached.current}</Box>
}
```

**为什么需要**（源码注释，精准道出设计动机）：

> Any content change above the viewport forces `log-update.ts` into a **full terminal reset**（无法部分更新已滚出的行）. For content that updates on a timer — **spinners, elapsed counters** — this produces a reset per tick.

即：屏幕外的消息如果有 spinner/计时器在动，**每次 tick 都强制整个终端 reset**。Claude 用引用缓存让 reconciler 看到相同引用直接 bail out → 整个子树 0 diff。

**one-slot deep** 设计：回到可视区时首次重新渲染就拾取最新 children，不影响实时性。

**效果**：即使屏幕上有 20 条历史工具调用（各带 spinner），也不拖慢当前帧。

---

### 1.3 `Ratchet` 最小高度锁定——**防止向下滚动时 UI 抖动**

**源码**：`components/design-system/Ratchet.tsx:38-65`

```tsx
const engaged = lock === "always" || !isVisible

useLayoutEffect(() => {
  if (!innerRef.current) return
  const { height } = measureElement(innerRef.current)
  if (height > maxHeight.current) {
    maxHeight.current = Math.min(height, rows)  // 跟踪最大高度（不超过屏幕行数）
    setMinHeight(maxHeight.current)
  }
})

// 锁定时用 minHeight 强制不收缩
<Box minHeight={engaged ? minHeight : undefined} flexDirection="column">
  {children}
</Box>
```

**用途**：消息区块滚出可视区时"engage"，`minHeight` 锁定为最大观察高度。如果此时内容收缩（例如 spinner 停止导致 1 行变 0 行），Ratchet 保持最小高度——**屏幕不抖动**。

---

### 1.4 三级输出截断——**工具 → 消息 → Summary**

**源码**：`constants/toolLimits.ts` + `utils/shell/outputLimits.ts`

| 层级 | 常量 | 值 | 用途 |
|-----|-----|-----|-----|
| Bash 默认输出上限 | `BASH_MAX_OUTPUT_DEFAULT` | 30,000 字符 | 单次 Bash 命令输出 |
| Bash 硬上限（可调） | `BASH_MAX_OUTPUT_UPPER_LIMIT` | 150,000 字符 | `BASH_MAX_OUTPUT_LENGTH` env var 可在此范围内调整 |
| 单工具结果默认上限 | `DEFAULT_MAX_RESULT_SIZE_CHARS` | 50,000 字符 | 超出持久化到磁盘，模型收到文件路径预览 |
| 单工具 token 硬上限 | `MAX_TOOL_RESULT_TOKENS` | 100,000 tokens (~400KB) | context 保护 |
| **单条 user 消息所有工具结果** | `MAX_TOOL_RESULTS_PER_MESSAGE_CHARS` | 200,000 字符 | **防 N 个并行工具各吃 50K 爆掉 context**（注释原话）|
| 工具 summary 展示长度 | `TOOL_SUMMARY_MAX_LENGTH` | 50 字符 | 折叠视图下工具名的截断长度 |

**env var 可调机制**（`utils/shell/outputLimits.ts`）：

```typescript
export function getMaxOutputLength(): number {
  const result = validateBoundedIntEnvVar(
    'BASH_MAX_OUTPUT_LENGTH',
    process.env.BASH_MAX_OUTPUT_LENGTH,
    BASH_MAX_OUTPUT_DEFAULT,      // 30,000
    BASH_MAX_OUTPUT_UPPER_LIMIT,  // 150,000
  )
  return result.effective
}
```

用户可通过 env var 在 `[30K, 150K]` 范围调整。超出上限自动 clamp，不会让用户意外写爆。

**per-message 200K 上限的精妙**（注释原文）：

> This prevents N parallel tools from each hitting the per-tool max and collectively producing e.g. 10 × 40K = 400K in one turn's user message.

**截断后的用户可见提示**：`[N lines truncated]` — 保留完整内容到磁盘，模型可后续读取。

**GrowthBook flag**：`tengu_hawthorn_window` 可运行时调整 per-message 预算（`toolResultStorage.ts` 的 `getPerMessageBudgetLimit()`）。

---

## 二、四条机制的协同效果

| 场景 | 屏幕占用 | 机制 |
|-----|---------|------|
| Bash 命令执行中 | **1 行**："⏺ Running bash..." | MessageResponse |
| Bash 输出 1MB | 截断到 30K，显示 `[...N lines truncated]` | 三级截断 |
| 10 个并行 Read 工具 | 每个 1 行进度，共 10 行 | MessageResponse × 10 |
| 历史 spinner 动画 | **0 CPU** 开销 | OffscreenFreeze |
| 向下翻页看历史 | 高度不抖动 | Ratchet |
| 单次 user 消息含 10×40K 工具结果 | 按大小排序，最大的持久化，总保证 ≤ 200K | MAX_TOOL_RESULTS_PER_MESSAGE_CHARS |

**核心设计哲学**：

1. **瞬态消息 = 单行**：进度、等待、结果摘要——任何非最终产出都压缩到 1 行
2. **活跃 vs 历史分离**：历史冻结（OffscreenFreeze）+ 活跃高度锁定（Ratchet）
3. **三级截断守护 context**：工具层 30K → 消息层 50K → 批量层 200K，层层设防

---

## 三、Qwen Code 现状对比

| 机制 | Claude Code | Qwen Code 现状 | 差距 |
|------|-----------|-------------|------|
| 瞬态消息单行容器 | `MessageResponse.tsx` 统一容器 | 消息组件分散，部分有固定高度但无统一抽象 | 中等 |
| 离屏历史冻结 | `OffscreenFreeze.tsx` + `useTerminalViewport` | 无此机制，所有消息每帧参与 reconcile | 大 |
| 滚动抖动抑制 | `Ratchet` minHeight 锁定 | 无 | 中等 |
| Bash 输出截断 | 30K default / 150K upper / env var | 未见明确上限，长输出可能直接塞进上下文 | 大 |
| 工具结果持久化 | 50K 触发持久化 + 路径预览 | 无 | 大 |
| per-message 批量预算 | 200K 硬顶 + GrowthBook 可调 | 无 | 大 |
| 工具 summary 截断 | 50 字符 | 可能整行展开 | 小 |

**验证方法**：`grep -rn "BASH_MAX_OUTPUT\|MAX_RESULT_SIZE\|overflowY" /root/git/qwen-code/packages/` 未命中同类常量（2026-04-20 验证）。

---

## 四、Qwen Code 借鉴路径（按 ROI 排序）

### 🥇 优先级 1：Bash 输出字符截断（1 天，立竿见影）

**为什么优先**：
- 实现最简单——纯 utility 函数，不涉及 UI 改造
- 直接解决"工具输出爆屏 + 爆 context"
- env var 可调，不破坏用户现有 workflow

**实现路径**：

```typescript
// packages/cli/src/utils/shell/outputLimits.ts（新建）
export const BASH_MAX_OUTPUT_DEFAULT = 30_000
export const BASH_MAX_OUTPUT_UPPER_LIMIT = 150_000

export function getMaxOutputLength(): number {
  const raw = Number(process.env.QWEN_BASH_MAX_OUTPUT_LENGTH)
  if (!raw || !Number.isFinite(raw)) return BASH_MAX_OUTPUT_DEFAULT
  return Math.min(Math.max(raw, 1000), BASH_MAX_OUTPUT_UPPER_LIMIT)
}

export function truncateOutput(output: string): { text: string; truncatedLines: number } {
  const max = getMaxOutputLength()
  if (output.length <= max) return { text: output, truncatedLines: 0 }
  const remainder = output.slice(max)
  const truncatedLines = remainder.split('\n').length
  return { text: output.slice(0, max) + `\n\n[${truncatedLines} lines truncated]`, truncatedLines }
}
```

在 ShellExecutionService / ShellTool 执行路径调用 `truncateOutput()`。

**工期**：~20 行代码 + 测试 = 半天。

### 🥇 优先级 2：MessageResponse 单行容器模式（半天）

**实现路径**：

```tsx
// packages/cli/src/ui/components/MessageResponse.tsx（新建）
export function MessageResponse({
  children,
  height = 1
}: { children: React.ReactNode; height?: number }) {
  return (
    <Box flexDirection="row" height={height} overflowY="hidden">
      {children}
    </Box>
  )
}
```

把现有 `ToolGroupMessage.tsx`、工具进度消息、Waiting 组件改为 `<MessageResponse>` 包裹。

**效果**：工具执行中屏幕增量固定为 1 行，不再因为长标题/输出爆屏。

### 🥈 优先级 3：OffscreenFreeze 离屏冻结（中等工期）

**前提**：Qwen Code 需要先实现 `useTerminalViewport()` hook（Ink 标准版无此 API，需要自定义基于 `measureElement` + scroll 位置计算）。

**实现路径**：

```tsx
// packages/cli/src/ui/hooks/useTerminalViewport.ts（新建）
export function useTerminalViewport(): [RefCallback, { isVisible: boolean }] {
  const [isVisible, setVisible] = useState(true)
  const scrollRef = useContext(ScrollContext)  // 需要有全局滚动位置
  // 用 scrollRef.current.scrollTop 与元素 offsetTop 比较
  ...
}

// packages/cli/src/ui/components/OffscreenFreeze.tsx
export function OffscreenFreeze({ children }) {
  const [ref, { isVisible }] = useTerminalViewport()
  const cached = useRef(children)
  if (isVisible) cached.current = children
  return <Box ref={ref}>{cached.current}</Box>
}
```

**工期**：2-3 天（主要花在 viewport 检测实现上）。

**效果**：滚动查看历史时，屏幕外的 spinner 不再导致整个终端 reset。

### 🥈 优先级 4：单工具结果 50K + 持久化到磁盘（2-3 天）

参考 `constants/toolLimits.ts`：单工具超过 50K 字符时写入 `.qwen/tool-results/<hash>.txt`，model 收到路径 preview（前 2K 字符 + 文件路径）。后续 Agent 若需要完整内容，通过 `read_file` 拉回。

**收益**：解决"一次 Read 读 500K 文件就爆 context"的问题。

### 🥉 优先级 5：per-message 200K 批量预算（1 天，依赖优先级 4）

实现 `MAX_TOOL_RESULTS_PER_MESSAGE_CHARS = 200_000`，按大小排序后持久化最大的工具结果。

### 可选：Ratchet（滚动抖动抑制）

优先级最低，收益集中在重度滚动历史的用户。实现需要与 OffscreenFreeze 配合。

---

## 五、快速实施清单（建议顺序）

| 阶段 | 任务 | 工期 | 累计 |
|-----|------|------|------|
| 1 | Bash 输出截断（30K default / 150K upper / env var） | 0.5d | 0.5d |
| 2 | MessageResponse 单行容器抽象 | 0.5d | 1d |
| 3 | 接入现有进度消息组件到 MessageResponse | 1d | 2d |
| 4 | OffscreenFreeze + useTerminalViewport | 2-3d | 4-5d |
| 5 | 单工具结果 50K 持久化 | 2d | 6-7d |
| 6 | per-message 200K 批量预算 | 1d | 7-8d |

**关键判断**：前 3 步（~2 天）能解决 70% 的"屏幕爆"感知问题，建议独立 PR。后续 4-6 是性能/context 优化，可以后再排。

---

## 六、关键文件速查表

| 机制 | Claude Code 参考 | Qwen Code 目标位置 |
|------|-----------------|------------------|
| MessageResponse | `components/MessageResponse.tsx:37` | `packages/cli/src/ui/components/MessageResponse.tsx` |
| OffscreenFreeze | `components/OffscreenFreeze.tsx:23-42` | `packages/cli/src/ui/components/OffscreenFreeze.tsx` |
| Ratchet | `components/design-system/Ratchet.tsx:38-65` | `packages/cli/src/ui/components/Ratchet.tsx` |
| Bash 输出截断 | `utils/shell/outputLimits.ts:3-14` | `packages/cli/src/utils/shell/outputLimits.ts` |
| 工具结果上限 | `constants/toolLimits.ts:13-49` | `packages/core/src/constants/toolLimits.ts` |
| useTerminalViewport | `ink/hooks/use-terminal-viewport.ts` | `packages/cli/src/ui/hooks/useTerminalViewport.ts` |

---

## 七、相关追踪 item

| item | 覆盖范围 | 关系 |
|------|---------|-----|
| [p2-stability item-44](./qwen-code-improvement-report-p2-stability.md#item-44)（本次新增） | MessageResponse 单行容器 + OffscreenFreeze | 本 Deep-Dive 第 1.1/1.2 节 |
| [p2-stability item-45](./qwen-code-improvement-report-p2-stability.md#item-45)（本次新增） | 三级输出截断（Bash 30K / 工具 50K / 消息 200K） | 本 Deep-Dive 第 1.4 节 |
| [p2-stability item-6](./qwen-code-improvement-report-p2-stability.md#item-6) | Markdown 渲染缓存 | 相邻主题：减少重解析成本 |
| [terminal-low-flicker-deep-dive](./terminal-low-flicker-deep-dive.md) | DEC 2026 + 池化 + 差分 | 相邻主题：低闪烁技术 |
