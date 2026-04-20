# Update（文件编辑）工具展示 Deep-Dive——Claude Code vs Qwen Code

> **核心问题**：Claude Code 和 Qwen Code 在展示 `Edit` / `Write` / `MultiEdit` 等 Update 类工具时的 UI 差异？
>
> 返回 [Qwen Code 改进建议总览](./qwen-code-improvement-report.md)

## 一、反直觉的发现：**这个维度两边各有优势**

Bash 和高度控制维度上，Claude Code 比 Qwen Code 更紧凑。但 Update 展示维度**反过来**——**Qwen Code WebUI 默认单行摘要**，Claude Code 默认展开完整 diff。

具体：

| | Claude Code | Qwen Code WebUI | Qwen Code CLI |
|---|---|---|---|
| Edit 成功默认展示 | Summary + **完整 `StructuredDiffList` diff** | **单行 `⎿ +15 lines, -3 lines`** | Summary + `DiffRenderer` diff（MaxSizedBox 限高） |
| 单行触发条件 | `style="condensed"`（仅 subagent 视图）| **默认** | 无单行模式 |
| 源码 | `FileEditToolUpdatedMessage.tsx:88-103` | `EditToolCall.tsx:149-181` | `DiffRenderer.tsx:248-276` |

**实际含义**：
- 如果你在 Qwen Code WebUI 看 Edit 结果——**最简**（单行）
- 如果你在 Claude Code 终端看 Edit 结果——**最详**（多行 diff）
- 如果你在 Qwen Code 终端看 Edit 结果——**中等**（diff + 自适应限高）

两边做了完全不同的**信息密度取舍**。

---

## 二、Claude Code 的技术亮点

### 2.1 `structuredPatch` 语义化 hunk 模型（`utils/diff.ts`）

Claude 使用 `diff` npm library 的 `structuredPatch()`，返回 `StructuredPatchHunk[]`：

```typescript
// utils/diff.ts:9
export const CONTEXT_LINES = 3
export const DIFF_TIMEOUT_MS = 5_000

// utils/diff.ts:81-114
export function getPatchFromContents({
  filePath, oldContent, newContent, ignoreWhitespace = false,
  singleHunk = false,
}): StructuredPatchHunk[] {
  const result = structuredPatch(
    filePath, filePath,
    escapeForDiff(oldContent), escapeForDiff(newContent),
    undefined, undefined,
    {
      ignoreWhitespace,
      context: singleHunk ? 100_000 : CONTEXT_LINES,  // ⭐ 智能上下文
      timeout: DIFF_TIMEOUT_MS,
    }
  )
  return result?.hunks.map(h => ({ ...h, lines: h.lines.map(unescapeFromDiff) }))
}
```

**关键 `singleHunk` 逻辑**（L103）：

- **单 hunk**（整个 diff 只有一处修改区域）→ `context: 100_000` = **全量上下文**，整个文件展示
- **多 hunk**（修改多处）→ `context: 3` = **紧凑**，每个 hunk 仅 3 行上下文

**设计意图**：单处修改时用户想看**完整上下文**；多处修改时用户想看**每处变更的紧凑预览**。

### 2.2 `StructuredDiffList` 多 hunk 省略分隔符

**源码**（`components/StructuredDiffList.tsx:16-29`）：

```tsx
export function StructuredDiffList({ hunks, ... }) {
  return intersperse(
    hunks.map(hunk => (
      <Box flexDirection="column" key={hunk.newStart}>
        <StructuredDiff patch={hunk} ... />
      </Box>
    )),
    i => <NoSelect fromLeftEdge key={`ellipsis-${i}`}>
      <Text dimColor>...</Text>
    </NoSelect>
  )
}
```

**效果**：

```
--- foo/bar.ts
@@ -10,3 +10,3 @@
  function hello() {
-   return "world"
+   return "world!"
  }

...                                              ← 省略分隔符（dim color）

@@ -42,3 +42,3 @@
  function goodbye() {
-   return "bye"
+   return "see ya"
  }
```

**用户体验**：多个 hunk 时不会混在一起，视觉上清晰分隔。

### 2.3 `FileEditToolUpdatedMessage` 三种展示模式

**源码**（`components/FileEditToolUpdatedMessage.tsx:62-110`）：

| 触发条件 | 展示内容 |
|---------|---------|
| `previewHint && style !== "condensed" && !verbose` | **仅 preview hint**（如 plan 文件）|
| `style === "condensed" && !verbose` | **仅文本摘要**（subagent 视图：`Added 15 lines, Removed 3 lines`）|
| 默认 + `verbose` | **完整 `StructuredDiffList`**（多行 diff）|

**`condensed` 模式用在 subagent 视图**——父 Agent 看子 Agent 的工具调用时用最简展示。

### 2.4 `FileWritePermissionRequest` 完整新文件预览

**源码**（`components/permissions/FileWritePermissionRequest/FileWritePermissionRequest.tsx:24-25`）：
- Create 场景：权限对话显示**完整新文件内容**
- Overwrite 场景：权限对话显示**完整 diff**

**设计意图**：用户在授权**任何写入**前，能看清楚**将写什么**。

---

## 三、Qwen Code 的技术亮点

### 3.1 WebUI 默认单行摘要（`EditToolCall.tsx:149-181`）

```tsx
if (diffs.length > 0) {
  const firstDiff = diffs[0]
  const path = firstDiff.path || locations?.[0]?.path || ''
  const summary = getDiffSummary(firstDiff.oldText, firstDiff.newText)
  // ↓ 单行摘要，无 diff 展开
  return (
    <div className="toolcall-edit-content ...">
      <div>
        <span>Edit</span>
        <FileLink path={path} showFullPath={false} />
      </div>
      <div>
        <span>⎿</span>
        <span>{summary}</span>  {/* "+15 lines, -3 lines" */}
      </div>
    </div>
  )
}
```

**效果**：

```
Edit foo/bar.ts
⎿ +15 lines, -3 lines
```

**用户体验**：消息流中每个 Edit 只占 2 行屏幕，大量 Edit 也不会爆屏。

### 3.2 CLI `DiffRenderer` 自适应高度 + `═` 间隙折叠

**源码**（`packages/cli/src/ui/components/messages/DiffRenderer.tsx`）：

```typescript
// L245
const MAX_CONTEXT_LINES_WITHOUT_GAP = 5

// L248-276
<MaxSizedBox maxHeight={availableTerminalHeight} maxWidth={contentWidth}>
  {parsedLines.map((line, idx) => {
    // 检测两个修改区间之间的无修改 gap
    if (relevantLineNumberForGapCalc > lastLineNumber + 5 + 1) {
      acc.push(<Text>{'═'.repeat(contentWidth)}</Text>)  // 插入间隙符
    }
    // ... 渲染行
  })}
</MaxSizedBox>
```

**效果**：

```
 10 |   function hello() {
-11 |     return "world"
+11 |     return "world!"
 12 |   }
═══════════════════════════════════════         ← 5+ 行无修改插入间隙
 42 |   function goodbye() {
-43 |     return "bye"
+43 |     return "see ya"
 44 |   }
```

**与 Claude 的 `...` 分隔符对比**：
- Claude `...`（3 个点）= hunk 之间
- Qwen `═════`（全宽横线）= hunk 内大段无修改区间

设计目标相同（视觉分隔无修改区间），实现方式不同。

### 3.3 二进制流预防（反向借鉴点）

Qwen 的 `shellExecutionService.ts:179-182` 的二进制检测也适用于 Write 工具——防止新建二进制文件时把 binary 内容塞进上下文。Claude Code 的 `FileWriteTool.ts` 对此无检测。

---

## 四、四个用户场景的体验对比

### 场景 A：修改 3 行函数（单 hunk 小改）

**Claude**：
```
Added 1 line, removed 1 line
 10   function hello() {
-11     return "world"
+11     return "world!"
 12   }
```
`singleHunk` 触发 → context 设为 100_000（实际只显示文件小于 100K 行的全部上下文），用户看到**完整函数**。

**Qwen WebUI**：`Edit foo/bar.ts ⎿ +0 lines, -1 lines`（wait — `getDiffSummary` 逻辑可能算"改了 1 行"而非 +0/-0，实际取决于 `getDiffSummary` 实现）

**Qwen CLI**：类似 Claude，但仅 5 行上下文，不会全量展开。

### 场景 B：大重构修改 200 行（多 hunk）

**Claude**：
- 每个 hunk 独立展示，3 行上下文
- 中间用 `...` 分隔
- 超过 400 行（`MAX_LINES_PER_FILE`）显示 `… diff truncated`

**Qwen WebUI**：仍是 `Edit foo/bar.ts ⎿ +150 lines, -50 lines`——**一行**。用户需要点击查看详情。

**Qwen CLI**：MaxSizedBox 限高，自动 `═` 分隔无修改区间。

### 场景 C：创建 500 行新文件

**Claude**：`FileWritePermissionRequest` 权限对话显示**完整新文件内容**（带行号、语法高亮）。

**Qwen WebUI**：
- 成功时：`WriteFile foo/bar.ts ⎿ 500 lines`
- 失败时：**只显示前 200 字符**（`WriteToolCall.tsx:47-51, 87`）

**差距**：Claude 的 write 权限预览是 Qwen 缺失的安全相关功能。

### 场景 D：Edit 失败（string not found）

**Claude**：`FileEditToolUseRejectedMessage`——显示原编辑 diff + 灰化 + `❌ User rejected edit to {filename}`

**Qwen**：`edit failed` + `errors` 数组

**差距**：Claude 保留了失败的 diff 预览让用户知道**"想改什么"**；Qwen 只说**"失败了"**。

---

## 五、核心设计哲学对比

| 哲学 | Claude Code | Qwen Code |
|------|-----------|----------|
| 前（批准时）vs 后（执行后）信息密度 | **前重后重**（批准完整 diff + 执行后完整 diff）| **前轻后轻**（CLI 直接执行 + WebUI 单行摘要）|
| 智能上下文 | `singleHunk ? 100_000 : 3` 二分 | 固定 `MAX_CONTEXT_LINES_WITHOUT_GAP=5`|
| Hunk 模型 | **语义化**（`StructuredPatchHunk[]` 可直接操作）| **字符串**（string patch，UI 层需 regex 重解析）|
| 多 hunk 分隔 | `...`（dim color 省略号）| `═════`（全宽横线，仅 Qwen CLI）|
| 错误信息 | **保留失败 diff 预览**（知道想改什么）| 仅错误文本 |
| Write 权限预览 | **完整新文件内容** | WebUI 仅失败时显示前 200 字 |

---

## 六、Qwen Code 借鉴方向（按 ROI 排序）

### 🥇 优先级 1：语义化 hunk 模型 + `singleHunk` 智能上下文

**Claude 源码**：
- `utils/diff.ts:1` `import { structuredPatch } from 'diff'`（使用标准库）
- `utils/diff.ts:103` `context: singleHunk ? 100_000 : CONTEXT_LINES`

**Qwen 现状**（`packages/core/src/tools/edit.ts:308, 433`）：
```typescript
const fileDiff = Diff.createPatch(/*...*/);  // 返回 string
```
UI 层（`DiffRenderer.tsx:23-81`）用 regex `parseDiffWithLineNumbers()` 重新解析字符串——**语义信息在序列化/反序列化过程中丢失**。

**改造方案**：
1. 在 core 层改为 `Diff.structuredPatch()` 返回 `StructuredPatchHunk[]`
2. 新增 `singleHunk` 启发式：`hunks.length === 1` 时请求更大 context
3. UI 层 `DiffRenderer.tsx` 直接接收 `StructuredPatchHunk[]`，**消除 regex re-parse**

**成本**：~2-3 天（core + UI 改造）
**收益**：
- 单行修改时展示完整函数上下文（用户最想要的）
- 消除 `parseDiffWithLineNumbers` regex 维护负担（~60 行代码可删）
- 性能提升（不再每次渲染 re-parse）

### 🥈 优先级 2：多 hunk `...` 省略分隔符（StructuredDiffList 模式）

**Claude 源码**：`components/StructuredDiffList.tsx:16-29`（~30 行完整实现）

**Qwen 现状**：CLI 用 `═` 全宽横线分隔 gap，但**这是同一 hunk 内无修改行**的处理，不是 hunk 之间。WebUI 则完全无多 hunk 分隔（因为只显示单行摘要）。

**改造方案**：在 `DiffRenderer.tsx` 中检测 hunk 边界（当 `hunks.length > 1` 且渲染完一个 hunk 后），插入 `<Text dimColor>...</Text>` 分隔符。

**成本**：~0.5 天（~20 行代码）
**依赖**：优先级 1 完成（需要 `StructuredPatchHunk[]` 输入而非字符串）
**收益**：多 hunk 场景视觉层次清晰

### 🥉 优先级 3：Edit 失败时保留 diff 预览

**Claude 源码**：`components/permissions/FileEditToolUseRejectedMessage.tsx`

**Qwen 现状**：`EditToolCall.tsx:124-145` 仅显示 `errors.join('\n')` 文本

**改造方案**：失败时仍传递 `oldText` / `newText` 到 UI，渲染灰化 diff + 错误横幅

**成本**：~1 天
**收益**：调试"string not found"场景时用户能看到**想改什么**，快速定位 whitespace/typo 问题

---

## 七、反向借鉴：Qwen → Claude 的亮点

如果 Claude Code 想借鉴 Qwen Code，最值得学的：

### A. WebUI 默认单行摘要 + 展开交互

Claude Code 的 CLI 有 `style="condensed"` 但仅在 subagent 视图激活。可考虑**作为全局用户选项**，让喜欢"一目十行"的用户设置 `edit_display: "condensed"`，默认行为不变。

### B. `═` 间隙折叠长段无修改区间

Claude `CONTEXT_LINES=3` 直接截断，Qwen 的 `═` 横线更明确表达"这里省略了 N 行"。

### C. 二进制文件写入预防

`shellExecutionService.ts:179-182` 的二进制检测也适用于 `FileWriteTool.ts`——防止创建二进制文件污染 session。

---

## 八、与现有追踪 item 的关系

| item | 覆盖范围 | 与本 Deep-Dive 的关系 |
|------|---------|---------------------|
| [item-6](./qwen-code-improvement-report-p2-stability.md#item-6) | Markdown 渲染缓存 | DiffRenderer 每帧 re-parse 是同类问题（优先级 1 顺带解决）|
| [item-44](./qwen-code-improvement-report-p2-stability.md#item-44) | MessageResponse + OffscreenFreeze | Claude `FileEditToolUpdatedMessage.tsx:103, 67` 复用（验证 item-44 的普适性）|
| [item-45](./qwen-code-improvement-report-p2-stability.md#item-45) | 三级输出截断 | 与 `MAX_LINES_PER_FILE=400` 同类，但针对 diff 而非 Bash |
| [item-48](./qwen-code-improvement-report-p2-stability.md#item-48)（本次新增）| 语义化 hunk + singleHunk 智能上下文 | 本 Deep-Dive 第 2.1 节 |
| [item-49](./qwen-code-improvement-report-p2-stability.md#item-49)（本次新增）| 多 hunk `...` 省略分隔符 | 本 Deep-Dive 第 2.2 节 |

---

## 九、关键文件速查表

| 技术 | Claude Code 源码 | Qwen Code 源码/目标 |
|------|---------------|------------------|
| 语义化 hunk 模型 | `utils/diff.ts:1, 81-114` `structuredPatch()` | 目标：`packages/core/src/tools/edit.ts` 改用 `Diff.structuredPatch()` |
| `singleHunk` 智能上下文 | `utils/diff.ts:103` | 目标：`edit.ts` 增加 `singleHunk` 启发式 |
| Edit 结果展示 | `components/FileEditToolUpdatedMessage.tsx:62-110` | `packages/cli/src/ui/components/messages/ToolMessage.tsx` |
| 多 hunk `...` 分隔 | `components/StructuredDiffList.tsx:16-29` | 目标：`DiffRenderer.tsx` 增加 hunk 边界检测 |
| Diff 底层渲染 | `components/StructuredDiff.tsx` | `DiffRenderer.tsx:23-81` `parseDiffWithLineNumbers()` |
| WebUI 单行摘要 | — （Claude 无 WebUI）| `packages/webui/src/components/toolcalls/EditToolCall.tsx:149-181` |
| CLI 自适应高度 | — | `DiffRenderer.tsx:248-276` `<MaxSizedBox>` |
| Write 权限完整预览 | `components/permissions/FileWritePermissionRequest/FileWritePermissionRequest.tsx:24-25` | 目标：Qwen 需要先有交互式权限对话 |
| Edit 失败保留 diff | `components/FileEditToolUseRejectedMessage.tsx` | 目标：`EditToolCall.tsx:124-145` 扩展失败态 |
