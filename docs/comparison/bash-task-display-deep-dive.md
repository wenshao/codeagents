# Bash 任务展示 Deep-Dive——Claude Code vs Qwen Code

> **核心问题**：Claude Code 与 Qwen Code 在展示 Bash 工具执行时的 UI 差异具体在哪里？Qwen Code 能借鉴什么？
>
> 返回 [Qwen Code 改进建议总览](./qwen-code-improvement-report.md)

## 一、两条完全不同的路线

**Claude Code = 极简+时间轴**——屏幕永远紧凑（最多 5 行输出 + 计数器），强调**剩余时间**（timeout 倒计时），视觉靠颜色而非图标。

**Qwen Code = 完整+数据维度**——展示完整 PTY 缓冲区（xterm headless Terminal 实例），强调**字节量**（二进制检测），视觉靠容器+icon+label 多维标记。

---

## 二、执行中状态（Streaming）

### 2.1 Claude Code：`ShellProgressMessage` 的 "5 行 + 计数" 模式

**源码**：`components/shell/ShellProgressMessage.tsx`

**核心逻辑**（L42-82）：

```tsx
// L42-44：永远只取最后 5 行
const strippedOutput = stripAnsi(output.trim())
lines = strippedOutput.split("\n").filter(notEmpty)
t2 = verbose ? strippedFullOutput : lines.slice(-5).join("\n")

// L65：包在 MessageResponse + OffscreenFreeze 里（无输出时）
return <MessageResponse>
  <OffscreenFreeze>
    <Text dimColor>Running… </Text>
    <ShellTimeDisplay elapsedTimeSeconds={elapsedTimeSeconds} timeoutMs={timeoutMs} />
  </OffscreenFreeze>
</MessageResponse>

// L74-81：计算多出的行数
const extraLines = totalLines ? Math.max(0, totalLines - 5) : 0
let lineStatus = ""
if (!verbose && totalBytes && totalLines) {
  lineStatus = `~${totalLines} lines`    // 大概行数
} else if (!verbose && extraLines > 0) {
  lineStatus = `+${extraLines} lines`    // 精确"多出 N 行"
}
```

**关键观察**：
- **verbose=false 是默认**——普通用户看到 5 行 + 计数器
- **verbose=true** 才展开全部（由 `ExpandShellOutputContext` 驱动）
- **复用 item-44 的 `MessageResponse` + `OffscreenFreeze`**——无输出时高度锁定 1 行；滚出屏幕后历史 spinner 零 CPU

### 2.2 Claude Code：`ShellTimeDisplay` 三模式时间展示

**源码**：`components/shell/ShellTimeDisplay.tsx`（73 行，完整 dim color `<Text>`）

**三种显示形态**：

| 条件 | 显示 | 源码行 |
|-----|-----|-------|
| 仅有 `timeoutMs`（尚未开始） | `(timeout 30s)` | L30 |
| `elapsed` + `timeoutMs` | `(10.5s · timeout 30s)` | L52 |
| 仅有 `elapsed`（无限制） | `(10.5s)` | L63 |

**用 `formatDuration` 自动选择单位**（`10500ms` → `10.5s`，`125000ms` → `2m5s`），`hideTrailingZeros: true` 避免 `30s0ms` 这种冗余。

**用户感知**：一眼看到 `Running… (42.1s · timeout 2m) +1234 lines`——**时间 + 进度** 同框。

### 2.3 Qwen Code：完整 PTY 缓冲区实时渲染

**源码**：`packages/core/src/services/shellExecutionService.ts`

**核心机制**（L612-706）：

```typescript
const RENDER_THROTTLE_MS = 100

// L636-650：每 100ms 渲染整个 xterm headless Terminal 状态
const renderFn = () => {
  if (!isStreamingRawContent) return
  if (!hasStartedOutput) {
    const bufferText = getFullBufferText(headlessTerminal)
    if (bufferText.trim().length === 0) return
    hasStartedOutput = true
  }
  // ... 渲染整个虚拟终端状态（默认 30 行 × 80 列）
}

// L179-182：二进制流检测（前 4KB）
const MAX_SNIFF_SIZE = 4096
let sniffedBytes = 0
if (sniffedBytes < MAX_SNIFF_SIZE) {
  isStreamingRawContent = !isBinary(chunk)
}
```

**默认窗口**：30 行 × 80 列（可通过 `shellExecutionConfig.terminalRows/Cols` 配置）
**更新频率**：100ms throttle（硬编码）
**二进制检测**：首 4KB 用 magic bytes 判断，检测到切换为 `[Receiving binary output... 2.5MB received]`

### 2.4 两种模式对比

| 维度 | Claude Code | Qwen Code |
|------|-----------|----------|
| 可见行数 | **5 行**（默认） | 整窗（默认 30 行） |
| 计数提示 | `+N lines` / `~N lines` | **无**——用户不知道还有多少 |
| 刷新节流 | 父组件 props（~秒级） | **100ms** 硬编码 |
| 进度指示 | **时间**（elapsed + timeout） | **字节**（`2.5MB received`） |
| 历史 spinner 开销 | **0 CPU**（OffscreenFreeze） | 每 100ms 整屏重渲染 |
| 高度锁定 | **1 行**（无输出时 MessageResponse） | 根据输出动态 |

---

## 三、执行完成（成功）

### 3.1 Claude Code：分层截断 + `(No output)` 特判

**关键文件**：

| 文件 | 行号 | 关键逻辑 |
|-----|------|--------|
| `tools/BashTool/BashToolResultMessage.tsx` | 103-109 | 检测图像：`[Image data detected and sent to Claude]` |
| `tools/BashTool/BashToolResultMessage.tsx` | 156 | `(No output)` / `Done` / `Running in the background` 均 `height={1}` |
| `utils/shell/outputLimits.ts` | 3-14 | `BASH_MAX_OUTPUT_DEFAULT = 30_000` / UPPER 150K |
| `components/shell/OutputLine.tsx` | — | 自适应终端宽度截断，`isError={true}` 触发红色 |
| `components/shell/ExpandShellOutputContext.tsx` | — | 按上下文展开完整输出 |

**典型场景（5000 行 find）**：截断到 30K 字符（~300-500 行） + 显示 `[4500 lines truncated]` + 完整内容持久化到磁盘。

### 3.2 Qwen Code：500 字符 Web UI 预览

**Web UI**（`packages/webui/src/components/toolcalls/ShellToolCall.tsx`）：

```tsx
// L215-216
const truncatedOutput = output.length > 500
  ? output.substring(0, 500) + '...'
  : output

// L140-149：无展开，点击打开临时文件
<button onClick={() => openTempFile(output)}>View full output</button>
```

**问题**：默认 500 字符预览可能截在第 20 行，**无行数计数**，用户以为输出已完整。

---

## 四、错误状态

| 维度 | Claude Code | Qwen Code |
|-----|-----------|----------|
| 视觉 | `<Text color="error">` **仅颜色变红** | 红色容器边框 + icon bullet + "Error" 独立卡片 |
| exit code | 一般隐藏（非零时文本说明） | 显式 `Command exited with code X.` |
| stderr 位置 | `<OutputLine isError={true} />` 与 stdout 混排 | 独立 `Error` 卡片区域（L196-205） |

**可访问性取舍**：Qwen 的多维度标记（色+形状+卡片）对色盲用户更友好；Claude 极简但依赖色彩辨识。

---

## 五、用户中断

| | Claude Code | Qwen Code |
|---|---|---|
| 消息 | **隐式**（`interrupted` 字段，不主动提示） | 显式 `Command was cancelled.` 前缀 |
| 保留输出 | 完整保留 stdout/stderr | 保留，加前缀消息 |

---

## 六、Bash 命令本身展示

| | Claude Code | Qwen Code |
|---|---|---|
| 语法高亮 | 否 | 否 |
| 多行命令 | 单行显示 + `!` 前缀 | 多行 `<pre>` 块 |
| 显示 cwd | 无（仅 `Shell cwd was reset` 警告） | 无（`WARNING: shell mode is stateless`）|
| 命令预览 | Bash Mode 下 `<bash-input>` 标签 | Web UI：`<pre>` + 复制按钮 |

---

## 七、四个用户场景的体验对比

### 场景 A：`find / -name "*.log"` 输出 5000 行

**Claude**：`Running… (12.3s) +4995 lines`（**3 行屏幕占用**），完成后 `[4500 lines truncated]` + 磁盘持久化。
**Qwen**：整屏滚动 5000 行，100ms 刷一次。完成后 Web UI 500 字符预览（≈第 20 行）+ 无行数提示。

**差距**：Claude 用户**始终知道剩余量**；Qwen 用户可能误判输出已完整。

### 场景 B：`npm install` 耗时 2 分钟

**Claude**：`Running… (1m23s · timeout 5m) +234 lines`——时间进度清晰。
**Qwen**：`[Receiving binary output... 2.5MB received]`——字节量清晰但无时间。

**差距**：长任务场景 Claude **"还剩多久"** 维度缺失是 Qwen 最明显的劣势。

### 场景 C：`ls /nonexistent` 错误

**Claude**：`ls: cannot access '/nonexistent': No such file or directory`（红色文本混在输出中）
**Qwen**：红色容器 + ❌ icon + "Error" 卡片独占区域。

**差距**：Qwen 错误更**"抢眼"**，Claude 需眼力辨识。

### 场景 D：20 个并行工具调用（含 5 个 Bash）

**Claude**：每个 Bash 占 1-2 行，历史滚出视口后 `OffscreenFreeze` 冻结。总屏占 ≤ 20 行，无 spinner 性能负担。
**Qwen**：每个 Bash 整屏 PTY（30 行 × 5 = 150 行），历史仍参与 reconcile，spinner 动画每帧整终端重排。

**差距**：**并行工具多时 Qwen 屏幕被爆 + CPU 负担重**。

---

## 八、Qwen Code 最值得借鉴的前 3 项

### 🥇 优先级 1：`ShellProgressMessage` "5 行窗口 + `+N lines` 计数"

- **Claude 源码**：`components/shell/ShellProgressMessage.tsx:42-82`
- **Qwen 现状**：整屏 xterm Terminal 渲染，无行数截断
- **实现方案**：在 `shellExecutionService.ts` 之上增加 UI 侧 slice —— `lines.slice(-5).join('\n')` + `extraLines = totalLines - 5`，verbose 模式保持当前完整 PTY
- **成本**：**~100 行**，1-2 天
- **依赖**：需要先落地 item-44（MessageResponse + OffscreenFreeze），或独立实现简化版
- **收益**：场景 A、D 的屏幕压力立刻缓解

### 🥈 优先级 2：`ShellTimeDisplay` 时间 + timeout 倒计时

- **Claude 源码**：`components/shell/ShellTimeDisplay.tsx`（完整 73 行）
- **Qwen 现状**：无时间展示，仅字节计数
- **实现方案**：新建 `packages/cli/src/ui/components/ShellTimeDisplay.tsx`，接收 `elapsedTimeSeconds` + `timeoutMs`，三种格式：`(timeout X)` / `(elapsed · timeout X)` / `(elapsed)`；用 `dim color` 避免视觉干扰
- **成本**：**~80 行**，1 天
- **收益**：场景 B 长任务用户能一眼看到"还剩多久"

### 🥉 优先级 3：Bash 输出截断 + `[N lines truncated]`

已在 [item-45 三级输出截断](./qwen-code-improvement-report-p2-stability.md#item-45) 追踪。关键是**截断后显式提示剩余行数**，让用户知道输出被截断而不是命令已结束。

---

## 九、两条路线各自的优势：反向借鉴

Claude Code 可从 Qwen Code 借鉴的**二进制流检测**值得注意：

**Qwen 源码**：`shellExecutionService.ts:179-182`

```typescript
const MAX_SNIFF_SIZE = 4096
if (sniffedBytes < MAX_SNIFF_SIZE) {
  isStreamingRawContent = !isBinary(chunk)
  if (!isStreamingRawContent) {
    // 切换为 "[Binary output detected. Downloading... XMB]"
  }
}
```

**价值**：执行 `cat /bin/ls`、`curl -o image.png url` 这类命令时避免二进制流污染终端渲染。Claude Code 目前无此保护。

---

## 十、相关追踪 item

| item | 覆盖范围 | 关系 |
|------|---------|-----|
| [p2-stability item-44](./qwen-code-improvement-report-p2-stability.md#item-44) | `MessageResponse` + `OffscreenFreeze` 基础设施 | Bash UI 的**前置依赖** |
| [p2-stability item-45](./qwen-code-improvement-report-p2-stability.md#item-45) | 三级输出截断（Bash 30K / 工具 50K / 消息 200K） | 覆盖本 Deep-Dive "执行完成" 部分 |
| [p2-stability item-46](./qwen-code-improvement-report-p2-stability.md#item-46)（本次新增） | `ShellProgressMessage` "5 行 + `+N lines`" | 本 Deep-Dive 第 2.1 节 |
| [p2-stability item-47](./qwen-code-improvement-report-p2-stability.md#item-47)（本次新增） | `ShellTimeDisplay` 时间 + timeout | 本 Deep-Dive 第 2.2 节 |
| [task-display-height-deep-dive](./task-display-height-deep-dive.md) | 通用高度控制机制 | 相邻主题 |

---

## 十一、关键文件速查表

| 技术 | Claude Code 源码 | Qwen Code 目标位置 |
|------|---------------|-----------------|
| 5 行截断 + `+N lines` | `components/shell/ShellProgressMessage.tsx:42-82` | `packages/cli/src/ui/components/ShellProgressMessage.tsx` |
| 时间 + timeout 展示 | `components/shell/ShellTimeDisplay.tsx`（73 行完整） | `packages/cli/src/ui/components/ShellTimeDisplay.tsx` |
| 自适应宽度输出 | `components/shell/OutputLine.tsx` | `packages/cli/src/ui/components/shell/OutputLine.tsx` |
| 上下文展开 | `components/shell/ExpandShellOutputContext.tsx` | `packages/cli/src/ui/contexts/ExpandShellOutputContext.tsx` |
| (No output) / Done 特判 | `tools/BashTool/BashToolResultMessage.tsx:103-189` | `packages/cli/src/ui/components/messages/ShellToolMessage.tsx` |
| Bash 输出截断 | `utils/shell/outputLimits.ts:3-14` | `packages/cli/src/utils/shell/outputLimits.ts`（见 item-45）|
| 二进制流检测（Qwen 独有） | — | `packages/core/src/services/shellExecutionService.ts:179-182` |
