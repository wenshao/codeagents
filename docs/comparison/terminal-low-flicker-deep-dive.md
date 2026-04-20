# 终端紧凑显示与低闪烁技术 Deep-Dive——Claude Code vs Qwen Code

> **核心问题**：Claude Code 在终端上显示紧凑、信息密度高、几乎不闪烁。Qwen Code 借鉴哪些技术、按什么优先级投入，能最接近这种体验？
>
> 返回 [Qwen Code 改进建议总览](./qwen-code-improvement-report.md)

## 一、为什么 Claude Code 感觉"紧凑不闪烁"

Claude Code 在 `ink/` 目录维护了 **~7,000 行自定义 Ink fork**（非原版 Ink），围绕 2 个核心目标：

1. **消除 GC 停顿** —— 流式输出 30 token/s 时，GC 进入休眠，输入响应稳定在 60fps。
2. **消除无效输出** —— 稳态帧（光标 spinner、追加一行文字）仅写变化 cell，带宽降 70-90%。

这两点靠 7 项技术叠加实现。下表按 **影响 × 实现成本** 排序，把每一项映射到 Qwen Code 的借鉴路径：

| 排名 | 技术 | Claude 源码位置 | Qwen Code 现状 | 成本 | 借鉴阶段 |
|------|------|---------------|-------------|------|-----|
| 1 | **DEC 2026 同步输出（BSU/ESU）** | `ink/terminal.ts#66-126`、`ink/termio/dec.js` | Ink 标准实现未检测 | **1d** | 阶段 1 |
| 2 | **60fps 渲染节流 + microtask 延迟** | `ink/ink.tsx#205-216` | Ink 默认无限频率 | 1-2d | 阶段 1 |
| 3 | **Markdown/Diff LRU 缓存** | 已有 item-6 覆盖 | MarkdownDisplay 每帧重解析 | 1-2d | 阶段 1 |
| 4 | **对象池化（CharPool + StylePool）** | `ink/screen.ts#21-163` | 无池 | 3-5d | 阶段 2 |
| 5 | **cell 级差分渲染 + 损伤矩形** | `ink/log-update.ts#268-305` | 仅 PR#3381 优化了游标移动 | 1-2w | 阶段 2 |
| 6 | **DECSTBM 硬件滚动** | `ink/log-update.ts#149-185` | 无 | 依赖 #5 | 阶段 3 |
| 7 | **光标 IME 停放 + 宽字符补偿** | `ink/ink.tsx#653-734`、`log-update.ts#638-750` | 基础管理 | 2-3d | 阶段 3 |

---

## 二、阶段 1：非侵入式改造（1 周，低风险高回报）

这三项**不需要修改 Ink 核心**，上层包裹即可，立竿见影减少闪烁和响应卡顿。

### 2.1 DEC 2026 同步输出（BSU/ESU）——**单条最直接的防闪烁机制**

**原理**：现代终端（VTE/iTerm2/WezTerm/Ghostty/Kitty/Alacritty/foot/Windows Terminal）支持 DEC mode 2026。启用后，`CSI ?2026h`（BSU）到 `CSI ?2026l`（ESU）之间的所有输出被终端视为**一个原子帧**——终端不渲染任何中间状态直到收到 ESU，**视觉上完全消除闪烁**。

**Claude Code 做法**（`ink/terminal.ts`）：

```typescript
// L66-126: 终端支持检测
function supportsDEC2026(): boolean {
  // tmux 反向代理字节，不实现 DEC 2026 → BSU/ESU 透传到外层终端，
  //   但 tmux 已拆分输出为多帧，无法原子化 → 回退
  if (isTmux()) return false
  // VTE (GNOME/Tilix/...)、iTerm2、WezTerm、Ghostty、Kitty、Alacritty、foot、Windows Terminal
  //   均已知支持
  if (knownSupportingTerminal()) return true
  return false
}

// L200-248: 输出包裹
let buffer = useSync ? BSU : ''
buffer += diffPayload
if (useSync) buffer += ESU
stdout.write(buffer)  // 单次写入，原子帧
```

**Qwen Code 借鉴路径**：

```typescript
// 新建 packages/cli/src/ui/utils/syncOutput.ts
export const BSU = '\x1b[?2026h'
export const ESU = '\x1b[?2026l'

export function detectDEC2026Support(): boolean {
  if (process.env.TMUX) return false  // tmux 环境回退
  const term = process.env.TERM_PROGRAM ?? ''
  const termEnv = process.env.TERM ?? ''
  return (
    term === 'iTerm.app' ||
    term === 'WezTerm' ||
    term === 'ghostty' ||
    termEnv.includes('kitty') ||
    termEnv.includes('alacritty') ||
    process.env.WT_SESSION !== undefined  // Windows Terminal
  )
}

// 在 packages/cli/src/gemini.tsx 的 render 入口
const useSync = detectDEC2026Support() && process.stdout.isTTY
```

拦截 Ink 的 `stdout.write` 调用，用 BSU/ESU 包裹每一帧。**工期：1 天，约 50 行**。

**预期收益**：在支持 DEC 2026 的现代终端上，Markdown 流式输出、工具执行、spinner 刷新均不再闪烁。

---

### 2.2 60fps 渲染节流 + microtask 延迟

**原理**：Ink 默认每次 React 状态更新就触发一次 stdout 写入。流式回复时一秒可能触发 30+ 次 render，互相堆积造成**帧抖动**（前一帧还没写完，后一帧已经开始覆盖）。Claude 用 16ms throttle 强制最高 60fps 输出，并通过 `queueMicrotask` 确保 React `useLayoutEffect` 先提交，光标位置不滞后一帧。

**Claude Code 做法**（`ink/ink.tsx#205-216`）：

```typescript
const deferredRender = throttle(
  () => {
    queueMicrotask(() => {
      // 此时 React layout effects 已提交，DOM 树是最终态
      const frame = renderToScreen(currentNode)
      writeFrameToStdout(frame)
    })
  },
  16,  // 60fps
  { leading: true, trailing: true },
)
```

**Qwen Code 借鉴路径**：

```typescript
// packages/cli/src/ui/hooks/useRenderThrottle.ts
import { throttle } from 'lodash-es'

export function useRenderThrottle(renderFn: () => void) {
  return useMemo(
    () =>
      throttle(
        () => queueMicrotask(renderFn),
        16,
        { leading: true, trailing: true },
      ),
    [renderFn],
  )
}
```

在 `AppContainer.tsx` 或 Ink 的 render 入口包裹。**工期：1-2 天**。

**预期收益**：长流式回复期间输入框不卡顿；spinner 稳定在 60fps 不飘动。

---

### 2.3 Markdown / Diff LRU 缓存（已有 item-6）

已在 [p2-stability item-6](./qwen-code-improvement-report-p2-stability.md#item-6) 追踪。要点：
- `packages/cli/src/ui/utils/markdownUtilities.ts` + `components/messages/DiffRenderer.tsx`
- 添加 `LRU<contentHash, parsedTokens>(500)` + 纯文本快速路径
- **工期：1-2 天**

---

## 三、阶段 2：对象池化 + 行级 diff（3-5 周，架构改动）

### 3.1 对象池化（CharPool + StylePool）

**详见** [终端渲染字符串池化 Deep-Dive](./terminal-rendering-string-pooling-deep-dive.md)（对应 [p2-perf item-20](./qwen-code-improvement-report-p2-perf.md#item-20)）。

Claude 的 `ink/screen.ts#21-163`：
- **CharPool**（L21-53）：ASCII 快速路径 `Int32Array[char.charCodeAt()]` O(1)，非 ASCII 走 `Map<string, number>`；上限 16k 条目 + 5 分钟重置
- **StylePool**（L112-163）：样式转换预缓存为 ANSI 字符串；**bit-0 编码空格可见性**——背景色/反色影响时 bit=1，否则 bit=0，O(1) bitmask 跳过隐形 cell
- **HyperlinkPool**（L57-111）：会话级生命周期，blit 时仅复制 ID

**Qwen Code 借鉴路径**（工期 3-5 天）：

1. 新建 `packages/cli/src/ui/rendering/pool.ts`，实现简化版 CharPool + StylePool
2. 改造 Markdown 高亮器（`highlight.ts`）返回 `StyleId[]` 而非 ANSI 字符串
3. DiffRenderer 的颜色映射改为 `pool.intern()`
4. 验收指标：GC heap size 下降 40-60%，流式回复期间无输入卡顿

---

### 3.2 cell 级差分渲染 + 损伤矩形

**Claude 做法**（`ink/log-update.ts#268-305`）：逐 cell 对比前后两帧的 `(charId, styleId, hyperlinkId)` 三元组，仅扫描**损伤矩形**范围内的 cell，损伤区域外完全跳过。复杂度 O(变化 cell 数) 而非 O(屏幕 cell 数)。

**全量回退条件**：
- `viewport.height` 缩小
- `viewport.width` 变化
- 内容超出视口

**Qwen Code 借鉴路径**（工期 1-2 周）：

**不建议完全 fork Ink**——维护成本过高。替代方案：在 Ink 上层引入**行级 diff**：

1. 扩展已有的 `packages/cli/src/ui/utils/terminalRedrawOptimizer.ts`（当前只优化游标移动）
2. 记录上一帧的 `lines: string[]`
3. 每次 render 后对比两帧的行数组，仅输出变化的行 + `CUP` 光标定位序列
4. 在 Ink render 调用后拦截 stdout.write，做行级 diff

---

## 四、阶段 3：细节打磨（可选）

### 4.1 DECSTBM 硬件滚动

依赖阶段 2 的 diff 引擎。ScrollBox `scrollTop` 变化时用终端硬件滚动指令替代逐行重写：

```
CSI top;bottom r    ← DECSTBM: 设置滚动区域
CSI n S             ← SU: 向上滚动 n 行
CSI r               ← 重置滚动区域
```

**安全条件**：必须 alt-screen + DEC 2026 支持。

### 4.2 光标 IME 停放 + 宽字符补偿

- **IME 停放**（`ink/ink.tsx#653-734`）：每帧结尾把终端光标停在输入框位置，CJK IME 预编辑在正确位置内联渲染
- **iTerm2 特殊处理**：光标停在底部而非 (0,0)，防止 cursor guide 逐帧跳动
- **宽字符补偿**（`ink/log-update.ts#638-750`）：检测终端对 emoji/CJK 字符宽度判断差异，发送 CHA 序列跳过补偿列

**工期**：2-3 天；**受益群体**：CJK 用户、使用 iTerm2 的用户。

---

## 五、实施路线图

| 阶段 | 时间窗 | 技术 | 累计成本 | 预期效果 |
|-----|-------|-----|---------|---------|
| **阶段 1** | 第 1 周 | DEC 2026 + 60fps 节流 + Markdown LRU | 3-5 天 | **用户可感知**：现代终端上闪烁消失、长回复不卡输入 |
| **阶段 2** | 第 2-5 周 | CharPool + StylePool + 行级 diff | 3-4 周 | **稳态帧带宽 -70%**、GC heap -50%、tmux 环境也流畅 |
| **阶段 3** | 第 6-7 周 | DECSTBM + IME + 宽字符 | 1 周 | 细节打磨，IME 用户 + 旧终端用户体验提升 |

**关键决策点**：如果只投入 1 周，优先做**阶段 1**——ROI 最高。阶段 2 需要架构改动但价值显著。阶段 3 属于打磨，可按用户反馈决定。

---

## 六、相关追踪 item

| item | 覆盖范围 | 状态 |
|------|---------|-----|
| [p2-tools-commands item-8](./qwen-code-improvement-report-p2-tools-commands.md#item-8) | 综合（DEC 2026 + diff + 双缓冲 + DECSTBM + 池化 + alt-screen） | 未合并 |
| [p2-perf item-20](./qwen-code-improvement-report-p2-perf.md#item-20) | 字符串池化（CharPool/StylePool） | 未合并 |
| [p2-stability item-6](./qwen-code-improvement-report-p2-stability.md#item-6) | Markdown 渲染缓存 | 未合并 |
| [p2-stability item-10](./qwen-code-improvement-report-p2-stability.md#item-10) | Markdown 表格 CJK 对齐 | ✓ PR#2914 已合并 |
| 相关 PR | [PR#3381](https://github.com/QwenLM/qwen-code/pull/3381) ✓ 2026-04-18 合并 | 终端重绘游标移动优化（仅覆盖阶段 2 cell diff 的一个局部） |

---

## 七、关键文件速查表

| 技术 | Claude Code 参考 | Qwen Code 目标位置 |
|------|-----------------|------------------|
| DEC 2026 检测 | `ink/terminal.ts#66-126`、`ink/termio/dec.js`（BSU/ESU 常量） | `packages/cli/src/ui/utils/syncOutput.ts` |
| 60fps 节流 | `ink/ink.tsx#205-216` | `packages/cli/src/ui/hooks/useRenderThrottle.ts` |
| CharPool | `ink/screen.ts#21-53` | `packages/cli/src/ui/rendering/charPool.ts` |
| StylePool | `ink/screen.ts#112-163` | `packages/cli/src/ui/rendering/stylePool.ts` |
| 差分引擎 | `ink/log-update.ts#268-305` | 扩展 `packages/cli/src/ui/utils/terminalRedrawOptimizer.ts` |
| DECSTBM 滚动 | `ink/log-update.ts#149-185` | 阶段 2 完成后的扩展 |
| 宽字符补偿 | `ink/log-update.ts#638-750` | `packages/cli/src/ui/utils/widthDetection.ts` |
| 光标 IME 停放 | `ink/ink.tsx#653-734` | `packages/cli/src/ui/hooks/useDeclaredCursor.ts` |

---

## 八、小结

Claude Code 的 "紧凑不闪烁" 不是单一魔法，而是 **7 项叠加技术**。Qwen Code 不必一次吞下全部：

- **1 周投入**：DEC 2026 + 节流 + Markdown 缓存 → 覆盖 60% 用户感知提升
- **4-5 周投入**：再加池化 + 行级 diff → 覆盖 90% 场景包括 tmux
- **不建议**：完全 fork Ink（维护成本过高）；优先改造 `terminalRedrawOptimizer.ts` 和在 Ink 上层包裹
