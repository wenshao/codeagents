# 11. 终端渲染与防闪烁——开发者参考

> DEC 2026 同步输出、差分渲染、双缓冲、硬件滚动、缓存池化、60fps 节流等 13 项防闪烁机制。Claude Code 自建 Ink fork 实现了这些底层优化。
>
> **Qwen Code 对标**：Qwen Code 使用标准 Ink，存在大输出闪烁问题。Gemini CLI 已在上游实现了 SlicingMaxSizedBox + 硬上限等部分方案（见 [工具输出限高](../../comparison/tool-output-height-limiting-deep-dive.md)）。本文的 DEC 同步输出和差分渲染是更底层的解决方案。

## 问题背景

终端 UI 不同于浏览器 DOM——没有硬件合成层、没有 `requestAnimationFrame`、没有 GPU 加速。每次输出都是往 stdout 写入 ANSI 转义序列的字节流，终端模拟器实时逐字解析并渲染。如果一次渲染涉及"清屏→重绘"两步，终端会先显示空白画面再显示新内容，产生可见闪烁。

Claude Code 使用 React + Ink 构建 TUI（Terminal UI），需要在以下场景保持视觉稳定：

- **文本流式输出**：assistant 回复按 chunk 到达，每秒多次更新
- **Spinner / 进度指示**：高频旋转动画
- **滚动**：对话历史上下滚动
- **布局变化**：工具调用展开/折叠、权限面板弹出
- **窗口大小调整**：终端 resize 后全量重排

## 架构总览

```
┌────────────────────────────────────────────────────────────────┐
│  React 组件树（Ink）                                            │
│  JSX → Yoga 布局 → 虚拟屏幕（Screen Buffer）                    │
└────────────────────┬───────────────────────────────────────────┘
                     │ renderNodeToOutput()
                     ▼
┌────────────────────────────────────────────────────────────────┐
│  Screen Buffer（二维 cell 数组）                                │
│  output.ts: 损伤追踪 + CharCache + blit 优化                    │
└────────────────────┬───────────────────────────────────────────┘
                     │ logUpdate()
                     ▼
┌────────────────────────────────────────────────────────────────┐
│  差分引擎（log-update.ts, 773 行）                              │
│  前后帧 diff → Diff 补丁数组                                    │
│  DECSTBM 硬件滚动 / 逐 cell 增量写入                            │
└────────────────────┬───────────────────────────────────────────┘
                     │ writeDiffToTerminal()
                     ▼
┌────────────────────────────────────────────────────────────────┐
│  终端输出（terminal.ts, 248 行）                                │
│  BSU/ESU 包裹 → 单次 stdout.write()                             │
└────────────────────────────────────────────────────────────────┘
```

## 核心渲染文件

| 文件 | LOC | 职责 |
|------|-----|------|
| `ink/ink.tsx` | 1,722 | Ink 主循环：调度渲染、双缓冲、池管理、alt-screen |
| `ink/log-update.ts` | 773 | 差分引擎：逐 cell diff、DECSTBM 滚动、全量回退检测 |
| `ink/output.ts` | 797 | 屏幕绘制：损伤追踪、CharCache、blit 优化 |
| `ink/screen.ts` | 1,486 | Screen buffer：StylePool、CharPool、HyperlinkPool |
| `ink/render-node-to-output.ts` | 1,462 | React 节点 → Screen buffer 渲染 |
| `ink/terminal.ts` | 248 | 终端能力检测、BSU/ESU 包裹、单次写入 |
| `ink/renderer.ts` | 178 | 光标管理、alt-screen 切换 |
| `utils/bufferedWriter.ts` | 100 | 流式文本批量写入 |

## 机制 1：DEC 2026 同步输出（原子更新）

源码: `ink/terminal.ts#L66-118`, `ink/terminal.ts#L190-248`

**最关键的防闪烁机制**。所有终端输出用 BSU/ESU（Begin/End Synchronized Update）包裹，终端在收到 ESU 前不会渲染任何中间状态。这里的"DEC 2026"是 DEC 私有模式 DECSET/DECRST `?2026`（synchronized output）的编号，并非年份：

```
CSI ?2026h   ← BSU: 开始缓冲
...清屏、光标移动、文本写入...
CSI ?2026l   ← ESU: 一次性刷新到屏幕
```

### 终端检测

`isSynchronizedOutputSupported()` 在模块加载时计算一次（能力不会中途变化）。DEC 2026 检测除 VTE 外**不做版本检查**——VTE 需 `VTE_VERSION >= 6800`（0.68+），其他终端只匹配名称/环境变量。注意：版本检查也存在于独立的 `isProgressReportingAvailable()` 函数中（用于 OSC 9;4 进度报告），两者是不同功能：

| 终端 | 检测方式 |
|------|----------|
| iTerm2 | `TERM_PROGRAM === 'iTerm.app'` |
| WezTerm | `TERM_PROGRAM === 'WezTerm'` |
| Ghostty | `TERM_PROGRAM === 'ghostty'` 或 `TERM === 'xterm-ghostty'` |
| Kitty | `TERM` 含 `kitty` 或 `KITTY_WINDOW_ID` 存在 |
| Alacritty | `TERM_PROGRAM === 'alacritty'` 或 `TERM` 含 `alacritty` |
| foot | `TERM` 以 `foot` 开头 |
| Windows Terminal | `WT_SESSION` 存在 |
| VS Code | `TERM_PROGRAM === 'vscode'` |
| Warp | `TERM_PROGRAM === 'WarpTerminal'` |
| Contour | `TERM_PROGRAM === 'contour'` |
| Zed | `ZED_TERM` 存在 |
| VTE 系列（GNOME Terminal、Tilix 等） | `VTE_VERSION >= 6800`（VTE 0.68+） |
| **tmux** | **跳过**：tmux 不实现 DEC 2026，BSU/ESU 穿透到外层终端但 tmux 已破坏原子性 |

> **SSH 场景**：`TERM_PROGRAM` 默认不被 SSH 转发。Claude Code 在启动时通过 XTVERSION 查询（`CSI > 0 q → DCS > | name ST`）异步检测终端名称，补充 env 检测的盲区（源码: `terminal.ts#L120-147`）。

### 输出管线

`writeDiffToTerminal()`（源码: `terminal.ts#L190-248`）将所有 diff 补丁拼接为单个字符串，用 BSU/ESU 包裹后单次 `stdout.write()` 发送：

```typescript
let buffer = useSync ? BSU : ''
for (const patch of diff) {
  switch (patch.type) {
    case 'stdout':        buffer += patch.content; break
    case 'clear':         buffer += eraseLines(patch.count); break
    case 'clearTerminal': buffer += getClearTerminalSequence(); break
    case 'cursorMove':    buffer += cursorMove(patch.x, patch.y); break
    case 'styleStr':      buffer += patch.str; break
    // ...
  }
}
if (useSync) buffer += ESU
terminal.stdout.write(buffer)  // 单次写入
```

## 机制 2：差分渲染引擎

源码: `ink/log-update.ts`（773 行）

不做全屏重绘，而是逐 cell 对比前后两帧，只输出变化的单元格。

### diff 算法

1. **损伤区域检查**：只扫描 `screen.damage` 矩形范围内的 cell（源码: `log-update.ts#L268-305`）
2. **逐行比较**：对每行的每个 cell，比较 charId、styleId、hyperlinkId 三元组
3. **跳过规则**：
   - 空 cell 不覆写已有内容（避免尾部空格导致终端换行）
   - 宽字符占位符（`SpacerTail`/`SpacerHead`）跳过
   - 前后帧相同的 cell 跳过（大部分 cell）
4. **光标管理**：追踪虚拟光标位置，使用相对移动（CR+LF、CUD）而非绝对定位

### 全量回退检测

某些场景 diff 无法处理，必须全屏重绘（源码: `log-update.ts#L142-147`）：

| 触发条件 | 原因 |
|----------|------|
| `viewport.height` 缩小 | 终端高度变化无法增量处理 |
| `viewport.width` 变化 | 文本换行完全改变 |
| 内容超出视口 | 需要清除滚动缓冲区 |

全量重绘通过 `fullResetSequence_CAUSES_FLICKER()` 执行——函数名本身就是对开发者的警告。

### diff 后优化

diff 产生的补丁数组在写入终端前经过 `optimize()` 后处理（源码: `ink.tsx#L621`），合并相邻光标移动、消除冗余样式序列、将多个小补丁拼接为更少的写入单元，进一步减少输出字节数。

## 机制 3：DECSTBM 硬件滚动

源码: `ink/log-update.ts#L149-185`

当 ScrollBox 的 `scrollTop` 变化时，用终端硬件滚动指令替代逐行重写：

```
CSI top;bottom r    ← DECSTBM: 设置滚动区域
CSI n S             ← SU: 向上滚动 n 行
CSI r               ← 重置滚动区域
CSI H               ← 光标回原点
```

关键优化：在 `prev.screen` 上模拟同样的 `shiftRows()`，使 diff 循环自然只发现滚入的新行。

**安全条件**（源码: `log-update.ts#L158-164`）：
- 必须在 alt-screen 模式
- 必须有 DEC 2026 支持（`decstbmSafe` 参数）
- 无 BSU/ESU 时回退到逐行重写——多输出字节，但无中间状态闪烁

> **源码注释原文**：*"Without atomicity the outer terminal renders the intermediate state — region scrolled, edge rows not yet painted — a visible vertical jump on every frame where scrollTop moves."*

## 机制 4：双缓冲

源码: `ink/ink.tsx#L99-100, #L593-595`

```typescript
private frontFrame: Frame;   // 当前可见帧（diff 基准）
private backFrame: Frame;    // 上一帧（复用为渲染目标）
```

每帧 diff 后交换：`backFrame = frontFrame; frontFrame = frame`。

**`prevFrameContaminated` 标志**（源码: `ink.tsx#L739-743`）：当选区覆盖（selection overlay）或搜索高亮（search highlight）在 screen buffer 上原地修改了 cell styleId 时，上一帧被"污染"（`selActive || hlActive`）——下一帧必须强制全量 diff，避免 blit 出反色/高亮的陈旧 cell。

## 机制 5：损伤追踪（Damage Tracking）

源码: `ink/output.ts#L268-305, #L522-528`

损伤矩形记录哪些区域有变化，diff 引擎只扫描脏区域：

- **稳态帧**（spinner 旋转、文本追加）：窄损伤 → O(变化 cell) diff
- **布局变化**（`layoutShifted`）：全损伤 → 防止兄弟组件边界处残影
- **blit 优化**：父节点递归 blit 未变化的子树，避免 O(children) 重绘

```typescript
// 源码: render-node-to-output.ts#L28-42
// layoutShifted: 任何 yoga 节点位置/尺寸变化时设置
// → 触发全损伤兜底（PR #20120 修复兄弟 resize 边界伪影）
```

## 机制 6：缓存池化

源码: `ink/output.ts`, `ink/screen.ts`

### CharCache（output.ts#L178, #L198-205）

文本字符串 → 字素簇（`ClusteredChar[]`，含宽度、styleId、hyperlinkId）的缓存。大多数行跨帧不变，命中率极高。上限 16k 条目，超出时清空。

### StylePool（screen.ts#L112-163）

ANSI 样式序列驻留池：
- 以 stylecode 字符串为 key 驻留
- 缓存样式转换：`transition(fromId, toId)` → 预序列化 ANSI 字符串
- 预热后零分配：样式转换变为 Map 查找 + 字符串拼接
- styleId 的 bit 0 编码"空格是否可见"（背景色、反色），用于优化空格 cell 的跳过

### CharPool / HyperlinkPool

字符串 → ID 映射，blit 时直接复制 ID（O(1) 比较），无需重新 intern。会话级生命周期。

### 池重置（ink.tsx#L597-603）

每 5 分钟重置一次，防止长会话内存膨胀。O(cells) 迁移成本在 5 分钟间隔下可忽略。

## 机制 7：渲染节流（60fps 上限）

源码: `ink/ink.tsx#L205-216`

```typescript
const FRAME_INTERVAL_MS = 16  // 60fps
const deferredRender = (): void => queueMicrotask(this.onRender)
this.scheduleRender = throttle(deferredRender, FRAME_INTERVAL_MS, {
  leading: true,
  trailing: true
})
```

- **微任务延迟**：`queueMicrotask` 确保 React `useLayoutEffect`（如 `useDeclaredCursor`）先提交，光标位置不会滞后一帧
- **同一事件循环**：不影响吞吐量
- **ScrollBox drain timer**：硬件滚动后，以 `FRAME_INTERVAL_MS >> 2`（4ms）间隔快速排空积压帧（源码: `ink.tsx#L756-758`），而非持续高帧率渲染

## 机制 8：光标隐藏与定位

源码: `ink/renderer.ts#L170-175`, `ink/ink.tsx#L653-734`

- **初始光标状态**：非 TTY 模式或屏幕高度为 0 时隐藏（源码: `renderer.ts#L173`）
- **渲染期间隐藏**：alt-screen TTY 模式下，通过 BSU 内 `HIDE_CURSOR`/`SHOW_CURSOR` 包裹渲染过程，防止光标在帧更新时闪烁
- `useDeclaredCursor()` 将终端光标停放在输入框位置，支持 IME 预编辑内联渲染
- 每帧开头 `CSI H` 锚定光标到 (0,0)——自愈 tmux 状态栏、pane 刷新等造成的光标漂移
- 每帧结尾停放光标到 prompt 行——防止 iTerm2 cursor guide 随光标位置逐帧跳动

> **源码注释原文**：*"BSU/ESU protects content atomicity but iTerm2's guide tracks cursor position independently. Parking at bottom (not 0,0) keeps the guide where the user's attention is."*（源码: `ink.tsx#L631-634`）

## 机制 9：宽字符补偿

源码: `ink/log-update.ts#L638-750`

终端对 emoji/CJK 字符宽度的判断可能与 Unicode 标准不一致：

| 问题类别 | 说明 |
|----------|------|
| Unicode 12.0+ emoji | 新版 emoji 在旧终端显示为窄字符 |
| 带 VS16（U+FE0F）的文本默认 emoji | 是否渲染为宽取决于终端实现 |

检测到宽度不匹配时，发送 CHA（Cursor Horizontal Absolute）跳过补偿列。正确终端上 emoji glyph 自然覆写；旧终端上填充间隙。

## 机制 10：批量写入（BufferedWriter）

源码: `utils/bufferedWriter.ts`（100 行）

`BufferedWriter` 用于错误日志（`errorLogSink.ts`）、asciicast 录像（`asciicast.ts`）和调试日志（`debug.ts`）的批量写入，避免高频小写入阻塞磁盘 I/O：

- 缓冲上限：100 条目
- 定时刷新：1000ms 间隔
- 溢出处理：`setImmediate` 延迟（不阻塞按键输入）
- 保序写入：即使溢出也保持顺序

> **注意**：Assistant 回复的流式渲染不经过 `BufferedWriter`，而是通过 React → Ink → screen buffer → diff → `writeDiffToTerminal()` 的渲染管线完成。每个 chunk 写入 screen buffer 后，damage 标记变化行，下一帧 diff 只更新新增/变化的行。

## 机制 11：Alt-Screen 特化

源码: `ink/ink.tsx#L568-651`

Alt-screen（备用屏幕缓冲区）有专门优化：

- 每帧开头 `CSI H` 锚定光标到 (0,0)，自愈外部光标漂移
- `cursor.y` 钳制到视口范围，防止 LF 导致意外滚动
- resize 后的 `ERASE_SCREEN` 放在 BSU/ESU **内部**——旧内容保持可见直到新帧就绪

```typescript
// 源码: ink.tsx#L644-646
if (this.needsEraseBeforePaint) {
  this.needsEraseBeforePaint = false
  optimized.unshift(ERASE_THEN_HOME_PATCH)  // 擦除 + 重绘在同一个 BSU 块内
}
```

> **对比**：如果在 `handleResize` 中同步写入 `ERASE_SCREEN`，屏幕会空白 ~80ms（render() 耗时），用户可见闪烁。

## 机制 12：闪烁原因追踪（调试用）

源码: `ink/ink.tsx#L604-617`

当全量重绘不可避免时，系统记录闪烁元数据用于调试：

```typescript
if (isDebugRepaintsEnabled() && patch.debug) {
  const chain = dom.findOwnerChainAtRow(this.rootNode, patch.debug.triggerY)
  logForDebugging(
    `[REPAINT] full reset · ${patch.reason} · row ${patch.debug.triggerY}\n` +
    `  prev: "${patch.debug.prevLine}"\n` +
    `  next: "${patch.debug.nextLine}"\n` +
    `  culprit: ${chain.join(' < ')}`
  )
}
```

记录：闪烁原因（resize/offscreen/clear）、触发行号、前后帧内容差异、导致重绘的 React 组件链。

## 机制 13：Windows/WSL 特殊处理

源码: `ink/terminal.ts#L171-179`

Windows conhost 的 `SetConsoleCursorPosition` 在流式输出中会将视口拉回滚动缓冲区（viewport yank bug），通过 `process.platform === 'win32'` 或 `WT_SESSION` 检测。

此外，据官方 CHANGELOG（外部来源: [github.com/anthropics/claude-code/CHANGELOG.md](https://github.com/anthropics/claude-code/blob/main/CHANGELOG.md) v2.1.81 条目），v2.1.81 禁用了 Windows（含 WSL in Windows Terminal）的逐行流式渲染，因为渲染问题导致视觉异常。

## 设计权衡

| 决策 | 权衡 | 理由 |
|------|------|------|
| 单次 `stdout.write()` 而非多次小写入 | 内存拼接 vs I/O 次数 | 单次写入避免终端在 write 间隙渲染中间状态 |
| 差分渲染而非全屏重绘 | diff 复杂度 vs 输出字节数 | 稳态帧只写少量 cell，带宽/延迟大幅降低 |
| 硬件滚动 + BSU/ESU 依赖 | 需要终端支持 | 不支持时回退到逐行重写，多字节但无闪烁 |
| 池化 5 分钟重置 | 偶尔 O(cells) 迁移 vs 内存膨胀 | 长会话（数小时）不重置会导致 Map 无限增长 |
| `queueMicrotask` 延迟渲染 | 微量延迟 vs 光标同步 | 确保 layout effects 先提交，IME/光标不滞后 |
| Alt-screen 内擦除而非同步擦除 | 需要 BSU/ESU | 避免 resize 时 ~80ms 空白屏 |
| `fullResetSequence_CAUSES_FLICKER` 命名 | — | 函数名本身是对开发者的"闪烁预警" |

## 源码文件索引

| 文件 | LOC | 关键函数/类 |
|------|-----|-------------|
| `ink/ink.tsx` | 1,722 | `Ink` 类、`onRender()`、`scheduleRender`、双缓冲交换 |
| `ink/log-update.ts` | 773 | `logUpdate()`、`fullResetSequence_CAUSES_FLICKER()`、DECSTBM 滚动 |
| `ink/output.ts` | 797 | `renderNodeToOutput()`、CharCache、损伤追踪 |
| `ink/screen.ts` | 1,486 | `Screen`、`StylePool`、`CharPool`、`HyperlinkPool` |
| `ink/render-node-to-output.ts` | 1,462 | `renderNodeToOutput()`、`layoutShifted`、blit 优化 |
| `ink/terminal.ts` | 248 | `isSynchronizedOutputSupported()`、`writeDiffToTerminal()` |
| `ink/optimizer.ts` | 93 | `optimize()` 补丁优化：合并光标移动、消除冗余样式 |
| `ink/renderer.ts` | 178 | `createRenderer()`、光标可见性管理 |
| `utils/bufferedWriter.ts` | 100 | `BufferedWriter` 类、定时刷新 |
