# ReadFile 工具 Deep-Dive：Claude Code vs Qwen Code

> 逐源码对比 **Claude Code `tools/FileReadTool/FileReadTool.ts` (1,183 行) + `limits.ts` (92 行) + `imageProcessor.ts` (94 行)** vs **Qwen Code `tools/read-file.ts` (294 行) + `utils/fileUtils.ts` (908 行)**。
>
> 识别 Qwen Code 可借鉴的 12 项 ReadFile 能力 + 实施 roadmap。

---

## 速查表

| 维度 | Claude Code | Qwen Code | 差距 |
|---|---|---|:-:|
| 输出类型多样性 | 6 类（text / image / notebook / pdf / parts / file_unchanged）| 3 类（text / image / pdf）| 🟡 |
| Token-aware 上限 | ✓ maxSizeBytes + maxTokens 双重 | ✗ 仅 char 限制 | 🔴 |
| 重复读去重 | ✓ `file_unchanged` stub（30 字节）| ✗ 全量重读 | 🔴 |
| 图像处理 | ✓ Sharp resize + 压缩到 token 预算 | ✗ 直接 base64 | 🔴 |
| ENOENT 智能建议 | ✓ findSimilarFile + CWD 上下文 | ✗ 系统错误 | 🟡 |
| macOS screenshot 路径 | ✓ thin space 自动尝试 | ✗ | 🟡 |
| PDF 多策略 | 3 档（inline / text / pages-as-images）| 仅 text 一档 | 🟡 |
| Notebook cells 结构化 | ✓ cells 数组 | 仅合并文本 | 🟡 |
| Lazy zod schema | ✓ | ✗ | ⚪ |
| `searchHint` for ToolSearch | ✓ | ✗ | ⚪ |
| Skill 自动发现 + conditional 激活 | ✓ Read 前置触发 | 🟡 仅工具完成后（PR#3604 OPEN）| ⚪ |
| GrowthBook 限制 + env override | ✓ 远程可调 | ✗ | ⚪ |

---

## 一、Qwen Code 已具备的（基线）

✓ text / image / PDF 类型分流（`utils/fileUtils.ts:496` `getSpecificMimeType`）
✓ `pages` 参数 PDF 范围（`utils/pdf.ts:parsePDFPageRange`）
✓ `memoryFreshnessNote`（PR#3087 加入，识别旧 memory 文件）
✓ workspace permission gate（`tools/read-file.ts:101` `getDefaultPermission`，含 workspace / temp / userSkills / userExtensions / autoMem 五类授权路径）
✓ Telemetry（`logFileOperation` + `getProgrammingLanguage`）
✓ Auto-mem path 识别（`isAutoMemPath`）
✓ BOM-aware 读取（`utils/fileUtils.ts:707` UTF-16/32 透明）
✓ Char-based 截断（`getTruncateToolOutputThreshold` + `getTruncateToolOutputLines`，配置化）

---

## 二、🥇 Tier 1 — 高 ROI（每轮 token / I/O 节省）

### 1. **`file_unchanged` 去重** ⭐⭐⭐ 最大收益

**Claude `FileReadTool.ts:540-573`**：

```typescript
// readFileState: Map<absPath, { offset, limit, timestamp(mtimeMs), isPartialView }>

const existingState = readFileState.get(fullFilePath)
if (existingState && !existingState.isPartialView && existingState.offset !== undefined) {
  const rangeMatch =
    existingState.offset === offset && existingState.limit === limit
  if (rangeMatch) {
    const mtimeMs = await getFileModificationTimeAsync(fullFilePath)
    if (mtimeMs === existingState.timestamp) {
      logEvent('tengu_file_read_dedup', { ext })
      return {
        data: {
          type: 'file_unchanged' as const,
          file: { filePath: file_path },
        },
      }
    }
  }
}
```

**关键设计点**：

- **stub 是协议层的 30 字节 placeholder**（`FILE_UNCHANGED_STUB`），不是缓存内容
- 只去重 **offset !== undefined** 的 entry —— 区分 "Read 来源" vs "Edit/Write 副作用更新"。Edit/Write 后 `offset === undefined`，不参与去重（避免指错 pre-edit content）
- mtime 变化即失效（无需复杂 invalidation）
- killswitch：GrowthBook flag `tengu_file_read_dedup` 可远程关闭
- 命中后发 telemetry event 跟踪命中率

**Qwen 现状**：`tools/read-file.ts` 每次 Read 全量返回。Agent 验证场景（Read → Edit → Read 验证）每次都重发 5-50K content tokens。

**收益**：典型 Edit-then-Read 验证流 **每轮省 5-50K tokens**。10 轮验证累计 50K-500K tokens。

**实施**：~80 行 / 0.5 天

```typescript
// packages/core/src/tools/read-file.ts (改造)
class ReadFileToolInvocation {
  // 引入 readFileState（per-session Map）
  private async dedupCheck(filePath, offset, limit): Promise<Output | null> {
    const state = this.config.getReadFileState().get(filePath)
    if (!state || state.isPartialView || state.offset === undefined) return null
    if (state.offset !== offset || state.limit !== limit) return null
    const stat = await fs.stat(filePath)
    if (stat.mtimeMs !== state.timestamp) return null
    return { type: 'file_unchanged', file: { filePath } }
  }
}
```

---

### 2. **Token-based 双重上限**

**Claude `limits.ts:1-15`**：

```
| limit         | default | 检查时机     | 超限处理        |
|---------------|---------|-------------|-----------------|
| maxSizeBytes  | 256 KB  | 读前 stat    | throw pre-read  |
| maxTokens     | 25,000  | 读后 API 计数 | throw post-read |
```

**A/B 测试结论**（PR#21841，2026-03 内部实验）：throw 比 truncate 更省 tokens —— 错误信息只 ~100B，truncate 满载是 25K tokens。

**优先级**：env `CLAUDE_CODE_FILE_READ_MAX_OUTPUT_TOKENS` > GrowthBook `tengu_amber_wren` > 默认 25,000。

**Qwen 现状**：仅 char-based 截断（`config.getTruncateToolOutputThreshold()`），**无 token-aware 上限**。50K chars 中文可能只是 12K tokens，但代码可能爆 60K tokens。

**实施**：~60 行 / 0.5 天

```typescript
// packages/core/src/tools/read-file.ts:execute (改造前置 token 校验)
const maxTokens = parseInt(process.env.QWEN_FILE_READ_MAX_TOKENS ?? '25000')
const stat = await fs.stat(filePath)
if (stat.size > 256 * 1024) throw new FileTooLargeError(...)

// 读后再校验 token 数（如有 token counter）
const tokenCount = roughTokenEstimation(content)  // 或调 API count
if (tokenCount > maxTokens) {
  throw new TokenLimitExceededError(
    `File content (${tokenCount} tokens) exceeds maximum allowed tokens (${maxTokens}). ` +
    `Use offset and limit parameters to read specific portions, or search for specific content.`
  )
}
```

---

### 3. **图像 resize + token 压缩**

**Claude `imageProcessor.ts` + `imageResizer.ts`**：

```typescript
// 三步处理：
//   1. detectImageFormatFromBuffer
//   2. maybeResizeAndDownsampleImageBuffer — 大图缩放到目标尺寸
//   3. compressImageBufferWithTokenLimit — JPEG/PNG/WebP 压缩到 token 预算

const sharp = await getImageProcessor()  // lazy load Sharp
const buf = await sharp(imageBuffer)
  .resize(targetWidth, targetHeight, { fit: 'inside', withoutEnlargement: true })
  .jpeg({ quality: 80 })
  .toBuffer()
```

**输出 metadata 含原始 + 显示尺寸**：

```typescript
{
  type: 'image',
  file: {
    base64, type: 'image/jpeg',
    originalSize: bytes,
    dimensions: {
      originalWidth, originalHeight,    // 原始
      displayWidth, displayHeight       // 缩放后
    }
  }
}
```

让模型知道压缩尺寸 → 坐标点击等场景可正确换算。

**Qwen 现状**：`utils/fileUtils.ts:783-` 直接 base64 编码原图。retina 截图（2880×1800）→ 单图 ~80K tokens。

**实施**：~250 行（含 sharp 依赖加载）/ 3 天

**收益**：典型截图（2880×1800）从 ~80K → ~15K tokens（**5× 节省**）。1MB+ 图片从 OOM 风险变为可控。

**复用方向**：本项与 [p2-perf item-17 图片压缩多策略流水线](./qwen-code-improvement-report-p2-perf.md#item-17) 是同一方向 —— 应作为 ReadFile 入口的第一个落地点。

---

## 三、🥈 Tier 2 — UX 改进（错误信息友好性）

### 4. **ENOENT 智能建议**

**Claude `FileReadTool.ts:findSimilarFile + suggestPathUnderCwd + FILE_NOT_FOUND_CWD_NOTE`**：

```typescript
catch (error) {
  if (getErrnoCode(error) === 'ENOENT') {
    const altPath = getAlternateScreenshotPath(fullFilePath)  // macOS 路径变体
    if (altPath) return await callInner(altPath, ...)

    const similar = await findSimilarFile(fullFilePath)  // Levenshtein 匹配
    if (similar) return errorWith(`Did you mean ${similar}?`)

    return errorWith(FILE_NOT_FOUND_CWD_NOTE)  // CWD 上下文提示
  }
}
```

**Qwen 现状**：仅返回 ENOENT 系统错误。Agent 路径打错时反复试错（多轮 token 浪费）。

**实施**：~50 行 / 0.5 天

```typescript
// packages/core/src/utils/fileUtils.ts 新增
import { distance } from 'fast-levenshtein'  // 已是 dep

export async function findSimilarFile(missingPath: string): Promise<string | null> {
  const dir = path.dirname(missingPath)
  const target = path.basename(missingPath)
  try {
    const entries = await fs.readdir(dir)
    const sorted = entries
      .map(e => ({ e, d: distance(target, e) }))
      .sort((a, b) => a.d - b.d)
    return sorted[0]?.d < target.length / 2 ? path.join(dir, sorted[0].e) : null
  } catch { return null }
}
```

---

### 5. **macOS Screenshot 路径变体处理**

**Claude `FileReadTool.ts:130-160`**：

```typescript
// macOS 截图文件名中 "AM/PM" 前空格可能是  （regular space）或  （thin space, U+202F）
// 不同 macOS 版本不一致

function getAlternateScreenshotPath(filePath: string): string | null {
  if (filePath.includes(' ')) {
    return filePath.replace(/ /g, ' ')
  }
  if (filePath.includes(' ') && /\d{1,2}\.\d{2}\.\d{2}\s+(AM|PM)/i.test(filePath)) {
    return filePath.replace(' ', ' ')
  }
  return null
}
```

**Qwen 现状**：用户从 macOS Finder 复制截图路径就 ENOENT。

**实施**：~10 行 / 0.1 天 —— 直接 backport

---

### 6. **`searchHint` for ToolSearch**

**Claude**：

```typescript
export const FileReadTool = buildTool({
  name: FILE_READ_TOOL_NAME,
  searchHint: 'read files, images, PDFs, notebooks',
  // ...
})
```

ToolSearch 模糊匹配时给搜索权重（`scoreTool` 中 `searchHint` 权重 4 / 5 / 10 等）。

**Qwen 现状**：ToolSearch 路径（PR#3589 CLOSED）尚未启用。但 hint 字段可为后续 ToolSearch 重启准备。

---

## 四、🥉 Tier 3 — 媒体类型扩展

### 7. **PDF 多策略（3 档）**

**Claude `FileReadTool.ts:431, 897, 948`**：

```typescript
PDF_AT_MENTION_INLINE_THRESHOLD  // 小 PDF (<2MB) → 整 base64 inline
PDF_EXTRACT_SIZE_THRESHOLD       // 大 PDF + page 范围 → text 提取（readPDF）
PDF_MAX_PAGES_PER_READ = 20      // 超大 PDF → 页面渲染为图片输出到目录（'parts' type）
```

**第三档 'parts' 输出**：

```typescript
{
  type: 'parts',
  file: {
    filePath, originalSize,
    count: 5,                     // 提取了 5 页
    outputDir: '/tmp/pdf-parts'  // 页面图片所在目录
  }
}
```

模型用 ReadFile + image type 分别读每个页面图。

**Qwen 现状**：PR#3160 实现了 text 提取一档（`utils/pdf.ts`），无大 PDF parts 模式。复杂排版 PDF（学术论文 / 设计稿 / 扫描件）只能丢失视觉信息。

**实施**：~150 行 / 2 天

**对应 codeagents item**：[p2-tools-commands item-21 PDF / 二进制文件读取](./qwen-code-improvement-report-p2-tools-commands.md#item-21) 的**第三档**。

---

### 8. **Notebook cells 结构化输出**

**Claude `FileReadTool.ts:300-305`**：

```typescript
{
  type: 'notebook',
  file: {
    filePath,
    cells: [
      { cell_type: 'code', source: '...', outputs: [...], execution_count: 1 },
      { cell_type: 'markdown', source: '## Heading' },
      // ...
    ]
  }
}
```

**Qwen 现状**：PR#3160 已支持 `.ipynb` 解析，但输出是合并文本而非 cells 数组。Agent 修改 cell 时无 structured 引用（要描述"第 3 个 code cell"而不是直接 `cell_id`）。

**实施**：~80 行 / 1 天

---

## 五、协议层补充（Tier 4）

### 9. **Lazy zod schema**

**Claude `FileReadTool.ts:227`**：

```typescript
const inputSchema = lazySchema(() => z.strictObject({ ... }))
type InputSchema = ReturnType<typeof inputSchema>
```

避免启动时构建所有 zod schema。和 [perf-roadmap 项 ⑤b 静态 import lazy 化](./qwen-code-perf-roadmap.md) 同方向。

### 10. **`semanticNumber` 包装**

**Claude `FileReadTool.ts:230`**：

```typescript
offset: semanticNumber(z.number().int().nonnegative().optional())
```

模型有时把数字传成字符串 `"42"`，`semanticNumber` 自动 coerce。

**Qwen 现状**：仅 zod 严格模式，模型传 `"42"` 时报错。

### 11. **GrowthBook 化的限制 + env override**

**Claude `limits.ts:53-92`**：

```typescript
export const getDefaultFileReadingLimits = memoize((): FileReadingLimits => {
  const override = getFeatureValue_CACHED_MAY_BE_STALE<Partial<FileReadingLimits>>(
    'tengu_amber_wren', {}
  )
  // env > GrowthBook > 默认
  const maxTokens = envMaxTokens ?? override?.maxTokens ?? DEFAULT_MAX_OUTPUT_TOKENS
  // ...
})
```

**Qwen 现状**：限制硬编码或仅 settings.json。无远程动态调整能力。

**实施方向**：先做 `QWEN_FILE_READ_MAX_TOKENS` env var，feature flag 系统建立后再扩展。

### 12. **Read 前置触发 skill 自动发现 + conditional 激活**

**Claude `FileReadTool.ts:578-591`**（在 callInner 之前）：

```typescript
const newSkillDirs = await discoverSkillDirsForPaths([fullFilePath], cwd)
if (newSkillDirs.length > 0) {
  for (const dir of newSkillDirs) context.dynamicSkillDirTriggers?.add(dir)
  addSkillDirectories(newSkillDirs).catch(() => {})  // fire-and-forget
}
activateConditionalSkillsForPaths([fullFilePath], cwd)
```

**Qwen 现状**：PR#3604（OPEN）已实现 `paths:` conditional skills 在 `coreToolScheduler.ts:1703-1716` 工具调用 **完成后** 触发。Claude 是 Read **发起前**就触发，让 skill 在 Read 结果一起返回时已加载。

---

## 六、推荐实施顺序

| 优先级 | 项 | 工作量 | 收益 |
|:-:|---|:-:|---|
| **P0** | #1 file_unchanged 去重 | ~80 行 / 0.5 天 | Edit-then-Read 验证流每轮省 5-50K token |
| **P0** | #2 Token-based 双重上限 | ~60 行 / 0.5 天 | 大文件防爆 token |
| **P1** | #3 图像 resize + 压缩 | ~250 行 / 3 天 | 截图场景 5× token 节省 |
| **P1** | #4 ENOENT 智能建议 | ~50 行 / 0.5 天 | 减少 agent 路径试错 |
| **P2** | #7 PDF parts 多策略 | ~150 行 / 2 天 | 复杂 PDF 视觉信息 |
| **P2** | #8 Notebook cells 结构化 | ~80 行 / 1 天 | Agent 编辑 cell 精准引用 |
| **P3** | #5 macOS screenshot 路径 | ~10 行 / 0.1 天 | 边角 UX |
| **P3** | #6/#9/#10/#11/#12 | 各 ~30 行 | 协议层补充 |

**总投入**：P0+P1 ~440 行 / ~5 天（图像 sharp 集成是大头）

---

## 七、度量驱动方法

参考 [PR#3581 范式](./qwen-code-perf-roadmap.md#五度量驱动方法参考-pr3581-范式)，每个 perf PR 带 tracer：

### A. Read 重复率 tracer（验证 file_unchanged 价值）

```js
// /tmp/qwen-trace/trace-read-dedup.cjs
const reads = new Map()
const orig = require('fs').promises.readFile
require('fs').promises.readFile = function(path, ...args) {
  reads.set(path, (reads.get(path) ?? 0) + 1)
  return orig.call(this, path, ...args)
}
process.on('exit', () => {
  const dup = [...reads.entries()].filter(([, n]) => n > 1)
  console.error(`Total reads: ${[...reads.values()].reduce((a, b) => a+b, 0)}`)
  console.error(`Duplicate paths: ${dup.length}`)
  console.error('Top duplicates:', dup.sort((a, b) => b[1] - a[1]).slice(0, 5))
})
```

### B. Token vs Char 对比 tracer

```bash
QWEN_DEBUG_TOKEN_COUNT=1 qwen -p "Read large.json"
# 输出: char count = 95000, estimated token = 28500, actual API token = 31200
# 决策：估算偏低 8.6%，maxTokens 25000 应在 char ~80K 时触发
```

### C. 图像压缩率 tracer

```bash
QWEN_DEBUG_IMAGE_COMPRESS=1 qwen -p "Look at screenshot.png"
# 输出: original 2880x1800 (4.2MB) → display 1024x640 (180KB) → 88K base64 chars → ~22K tokens
```

---

## 八、与现有 codeagents item 关联

| 本 deep-dive 项 | 关联 codeagents 资源 | 说明 |
|---|---|---|
| #1 file_unchanged | [item-2 文件读取缓存](./qwen-code-improvement-report-p0-p1-engine.md#item-2) | 协议层补充（更轻量，~30B vs 内容缓存）|
| #2 Token-based 上限 | [item-45 三级输出截断](./qwen-code-improvement-report-p2-stability.md#item-45) | 截断维度从 char 升级到 token |
| #3 图像 resize | [p2-perf item-17 图片压缩多策略](./qwen-code-improvement-report-p2-perf.md#item-17) | ReadFile 入口落地 |
| #7 PDF parts | [p2-tools-commands item-21 PDF / 二进制文件读取](./qwen-code-improvement-report-p2-tools-commands.md#item-21) | 第三档（已有 P0+P2，缺 P1 大 PDF parts）|
| #8 Notebook cells | 同 item-21 | Notebook 结构化输出维度 |
| #12 Skill auto-discovery | [item-28 Skill 装载性能](./qwen-code-improvement-report-p0-p1-engine.md#item-28) sub-point #6 | 触发时机优化（前置 vs 后置）|

---

## 九、源码索引

### Claude Code

| 文件 | 行 | 功能 |
|---|---|---|
| `tools/FileReadTool/FileReadTool.ts` | 1-1183 | 主体 |
| `tools/FileReadTool/FileReadTool.ts:227-243` | input schema（lazy） |
| `tools/FileReadTool/FileReadTool.ts:248-332` | output schema（6 类）|
| `tools/FileReadTool/FileReadTool.ts:540-573` | file_unchanged 去重 |
| `tools/FileReadTool/FileReadTool.ts:578-591` | skill 自动发现 + conditional 激活 |
| `tools/FileReadTool/FileReadTool.ts:614-622` | macOS screenshot 路径变体 |
| `tools/FileReadTool/FileReadTool.ts:755` | validateContentTokens |
| `tools/FileReadTool/limits.ts:1-92` | maxSizeBytes + maxTokens 双重上限 |
| `tools/FileReadTool/imageProcessor.ts:1-94` | Sharp lazy 加载 |
| `utils/imageResizer.ts` | 图像 resize + 压缩 |
| `utils/file.ts:findSimilarFile` | Levenshtein 路径匹配 |

### Qwen Code

| 文件 | 行 | 功能 |
|---|---|---|
| `tools/read-file.ts` | 1-294 | 主体 |
| `tools/read-file.ts:101-144` | getDefaultPermission（5 类授权路径）|
| `tools/read-file.ts:168` | memoryFreshnessNote |
| `utils/fileUtils.ts:496-526` | getSpecificMimeType（mime 分类）|
| `utils/fileUtils.ts:707-781` | text 读取 + char 截断 |
| `utils/fileUtils.ts:783-` | image / pdf 处理 |
| `utils/pdf.ts` | parsePDFPageRange + readPDF |
| `config/config.ts:2392-2406` | getTruncateToolOutputThreshold + Lines |

---

**最后更新**：2026-04-29
**相关文档**：
- [改进报告主矩阵](./qwen-code-improvement-report.md)
- [item-2 文件读取缓存](./qwen-code-improvement-report-p0-p1-engine.md#item-2)
- [item-45 三级输出截断](./qwen-code-improvement-report-p2-stability.md#item-45)
- [item-21 PDF / 二进制文件读取](./qwen-code-improvement-report-p2-tools-commands.md#item-21)
- [Qwen Code 性能优化 Roadmap](./qwen-code-perf-roadmap.md)
