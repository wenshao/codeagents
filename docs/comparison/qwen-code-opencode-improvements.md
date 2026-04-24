# Qwen Code 改进建议 — 对标 OpenCode

> 基于 OpenCode (anomalyco/opencode) 源码逐项比对，识别 Qwen Code 可借鉴的 **29 项**能力（其中 **4 项已赶超**——item-13 Hook / item-14 Worktree / item-16 LSP / item-20 Skill）。OpenCode 共 **437 文件、78,174 行**——一个功能完备的多客户端 AI 平台。
>
> **最后核对日期**：2026-04-24（两侧源码均已 `git pull` 刷新，新增 item-28/29）
>
> **相关报告**：
> - [Claude Code 改进建议报告（256 项）](./qwen-code-improvement-report.md)——行业领先者对比
> - [Gemini CLI 上游 backport 报告（53 项）](./qwen-code-gemini-upstream-report.md)——上游可 backport 改进
> - [Codex CLI 对标改进报告（25 项）](./qwen-code-codex-improvements.md)——沙箱、Apply Patch、Feature Flag、网络代理等
> - [/review 功能分析](./qwen-code-review-improvements.md)——审查功能 5 方对比

---

## 改进项索引

| # | 功能 | 优先级 | 工作量 | 来源模块 | 规模 |
|:-:|------|:------:|:------:|----------|:----:|
| [1](#item-1) | 文件时间锁（外部修改检测） | **P0** | 1 天 | `file/time.ts` | — |
| [2](#item-2) | apply_patch 工具（GPT 模型适配） | **P1** | 3 天 | `tool/apply_patch.ts` | — |
| [3](#item-3) | MultiEdit 工具（单文件批量编辑） | **P1** | 1 天 | `tool/multiedit.ts` | — |
| [4](#item-4) | Session 分叉与回退 | **P1** | 5 天 | `session/revert.ts` | — |
| [5](#item-5) | SQLite 持久化 | **P1** | 2 周 | `session/session.sql.ts` | — |
| [6](#item-6) | 语义代码搜索（Exa） | **P1** | 2 天 | `tool/codesearch.ts` | — |
| [11](#item-11) | Snapshot 会话快照与回滚 | **P1** | 5 天 | `snapshot/` | 726 行 |
| [12](#item-12) | Provider 多模型提供商系统 | **P1** | 3 周 | `provider/` | 7,927 行 31 文件 |
| [13](#item-13) | Plugin 插件系统（18 种 Hook）⚠️ 部分赶超 | **P1** | 2 周 | `plugin/` | 2,618 行 → Qwen **17,443 行**（Hook 反超，但无 npm 分发） |
| [14](#item-14) | Worktree 增强管理 ✅ | **P1** | 1 天 | `worktree/` | 612 行 → Qwen **826 行** |
| [7](#item-7) | Batch 工具（并行工具调用） | **P2** | 3 天 | `tool/batch.ts` | — |
| [8](#item-8) | HTTP 服务器（多客户端架构） | **P2** | 3 周 | `server/server.ts` | — |
| [9](#item-9) | Instance 上下文隔离 | **P2** | 3 天 | `server/instance.ts` | — |
| [15](#item-15) | ACP Agent 协议服务端 | **P2** | 2 周 | `acp/` | 1,987 行 3 文件 |
| [16](#item-16) | LSP 多语言服务器管理 ✅ | **P2** | ✅ 已实现 | `lsp/` | 2,919 行 → Qwen **7,422 行** |
| [17](#item-17) | NPM 动态包安装 | **P2** | 2 天 | `npm/` | 188 行 |
| [18](#item-18) | Permission 规则引擎 | **P2** | 3 天 | `permission/` | 520 行 4 文件 |
| [19](#item-19) | PTY 伪终端管理 | **P2** | 2 周 | `pty/` | 492 行 5 文件 |
| [20](#item-20) | Skill 动态发现系统 ✅ | **P2** | ✅ 已实现 | `skill/` | 393 行 → Qwen **2,673 行** |
| [21](#item-21) | Git 操作抽象层 | **P2** | 2 天 | `git/` | 303 行 |
| [22](#item-22) | Session Share 会话分享 | **P2** | 2 周 | `share/` | 382 行 2 文件 |
| [23](#item-23) | Event Sync 事件溯源 | **P2** | 2 周 | `sync/` | 293 行 3 文件 |
| [24](#item-24) | Control-Plane 多工作区 | **P2** | 2 周 | `control-plane/` | 362 行 7 文件 |
| [10](#item-10) | MDNS 服务发现 | **P3** | 1 天 | `server/mdns.ts` | — |
| [25](#item-25) | Format 代码格式化集成 | **P3** | 1 周 | `format/` | 616 行 2 文件 |
| [26](#item-26) | Command 动态命令注册 | **P3** | 2 天 | `command/` | 195 行 |
| [27](#item-27) | Effect 框架工具集 | **P3** | — | `effect/` | 851 行 6 文件 |
| [28](#item-28) | 可配置工具输出截断限制 🆕 | **P2** | 1 天 | `tool/truncate.ts` + `config/config.ts` | 106 行（PR#23770）|
| [29](#item-29) | TUI 编辑器上下文 builtin protocol 🆕 | **P2** | 1 周 | `cli/cmd/tui/context/editor.ts` | 448 行（PR#24034）|

---

<a id="item-1"></a>

### 1. 文件时间锁——外部修改检测（P0）

**问题**：用户在 IDE 中编辑文件的同时，Agent 也在编辑同一文件。如果 Agent 不知道文件已被外部修改，会直接覆盖用户在 IDE 中的修改——这是**数据丢失风险**。

**OpenCode 的解决方案——FileTime 服务**：

OpenCode 设计了 `FileTime` 命名空间，为每个 session 追踪所有读取过的文件的 `mtime` 和 `size`。在每次写入前断言文件未被外部修改：

| 步骤 | 做什么 |
|------|--------|
| 1. Read 工具读取文件 | `FileTime.read(sessionID, filePath)` 记录 `{mtime, size, readTime}` |
| 2. Edit/Write 工具写入前 | `FileTime.assert(sessionID, filePath)` 重新 stat 文件 |
| 3. assert 比对 mtime 和 size | 如不一致 → 抛错："File has been modified since last read, please read again" |
| 4. 写入时加文件锁 | `FileTime.withLock(filePath, fn)` 使用 Semaphore 防止并发写 |

**关键设计细节**：

- **每 Session 独立追踪**：`Map<SessionID, Map<string, Stamp>>` 结构，不同会话的读取时间互不影响
- **双指标校验**：同时比对 `mtime` 和 `size`——mtime 可能因文件系统精度问题不变，size 提供额外保障
- **Semaphore 文件锁**：`withLock()` 基于 Effect 框架的 Semaphore（permits=1），防止 Agent 并发写同一文件
- **可禁用**：`OPENCODE_DISABLE_FILETIME_CHECK` 环境变量允许用户关闭（调试场景）
- **路径规范化**：所有路径经过 `Filesystem.normalizePath()` 处理，避免 `/a/b/../c` 和 `/a/c` 被视为不同文件

**OpenCode 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `file/time.ts` (~110行) | `FileTime.read()`、`FileTime.assert()`、`FileTime.withLock()`、`Stamp` 类型 |
| `file/watcher.ts` | `FileWatcher.Event.Updated` —— 写入后发布事件通知其他模块 |
| `tool/edit.ts` | 写入前调用 `FileTime.assert()`，写入后调用 `FileTime.read()` 更新时间戳 |
| `tool/write.ts` | 同上 |
| `tool/apply_patch.ts` | 同上（批量写入场景） |

**Qwen Code 现状**：**无任何外部修改检测**。Edit 工具使用 `old_string` → `new_string` 替换——如果文件被外部修改导致 `old_string` 不存在会报错，但这是副作用而非有意设计。Write 工具直接覆盖文件，完全无保护。

**Qwen Code 修改方向**：

```
① 新增 FileTimeTracker 服务（~100 行）
   - Map<sessionId, Map<filePath, {mtime, size}>>
   - read(sessionId, path)：stat + 记录
   - assert(sessionId, path)：stat + 比对 → 不一致则抛错

② 在 Read 工具中调用 tracker.read()
③ 在 Edit/Write 工具中调用 tracker.assert() + 写后 tracker.read()
④ 可选：Semaphore 防并发写（需评估 Node.js 单线程下的必要性）
```

**实现成本评估**：
- 涉及文件：~4 个（新建 tracker + 修改 Read/Edit/Write）
- 新增代码：~100 行
- 开发周期：~1 天（1 人）
- 难点：无——纯 `fs.stat` + Map 对比

**意义**：文件覆盖是**不可逆的数据丢失**——用户在 IDE 中改了半小时的代码被 Agent 一次 Write 覆盖。
**缺失后果**：用户必须手动确保 Agent 和 IDE 不同时编辑同一文件——违反"人机协作"的核心场景。
**改进收益**：1 天工作量 → 彻底消除外部修改覆盖风险。投入产出比最高的改进项。

---

<a id="item-2"></a>

### 2. apply_patch 工具——GPT 模型适配（P1）

**问题**：GPT 系列模型（GPT-4.1、O3/O4）的训练数据中大量使用 unified diff 格式编辑文件。当 Qwen Code 强制 GPT 使用 `old_string/new_string` 替换时，模型容易犯错——生成不精确的 `old_string` 导致匹配失败或误匹配。OpenCode 为此提供了 GPT 原生的 `apply_patch` 工具。

**OpenCode 的解决方案——apply_patch 工具**：

OpenCode 的 `apply_patch` 接受一段自定义的 patch 文本（非标准 unified diff，而是 GPT 训练数据中的格式），解析出 hunk 后逐文件应用修改：

| 操作类型 | 做什么 |
|----------|--------|
| `add` | 创建新文件（递归创建父目录） |
| `update` | 应用 chunk 修改到已有文件（`Patch.deriveNewContentsFromChunks`） |
| `move` | 移动文件（写入新路径 + 删除旧路径） |
| `delete` | 删除文件 |

**关键设计细节**：

- **非标准 diff 格式**：GPT 输出的 patch 格式为 `*** Begin Patch / *** End Patch` 包裹，内含 `*** Add File: / *** Update File: / *** Delete File:` 等标记
- **验证先于执行**：先解析所有 hunk 并计算预期结果（`fileChanges` 数组），全部验证通过后批量应用——类似数据库的 "prepare → commit"
- **安全检查**：`assertExternalDirectory()` 防止写入项目目录外的文件
- **LSP 集成**：每个修改文件后调用 `LSP.touchFile()` + `LSP.diagnostics()` 收集错误，并在输出中报告 LSP errors（最多 20 条/文件）
- **格式化**：写入后自动调用 `Format.file()` 运行配置的 formatter
- **完整 diff 输出**：使用 `diff` 库的 `createTwoFilesPatch()` 生成标准 unified diff 用于权限审查和 UI 展示
- **文件事件**：通过 `Bus.publish(FileWatcher.Event.Updated)` 通知文件系统观察者

**OpenCode 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `tool/apply_patch.ts` (~280行) | `ApplyPatchTool.execute()`、hunk 解析、验证-提交分离、LSP 集成 |
| `tool/apply_patch.txt` | GPT 专用的 tool description（训练数据对齐） |
| `patch/` 目录 | `Patch.parsePatch()`、`Patch.deriveNewContentsFromChunks()` —— patch 格式解析器 |
| `tool/edit.ts` | `trimDiff()` 工具函数（被 apply_patch 复用） |

**Qwen Code 现状**：仅有 `Edit` 工具（`old_string/new_string` 替换）。所有模型统一使用同一套编辑工具。GPT 模型使用 search/replace 时经常匹配失败——尤其对大块代码修改，`old_string` 容易与实际内容有细微差异。

**Qwen Code 修改方向**：

```
① 新增 apply_patch 工具（~250 行）
   - 解析 *** Begin Patch / *** End Patch 格式
   - 支持 add/update/delete/move 四种操作
   - 验证-提交两阶段：先解析全部 hunk 并验证，再批量写入

② 新增 Patch 解析器（~200 行）
   - parsePatch()：解析 patch 文本为 Hunk[]
   - deriveNewContentsFromChunks()：将 chunk 应用到源文件

③ 按模型动态注册工具
   - GPT/O 系列：注册 apply_patch（替代 edit）
   - Claude/Qwen/Gemini：保留 edit
   - 在 ToolRegistry 中按 model 前缀路由
```

**实现成本评估**：
- 涉及文件：~5 个（新建 apply_patch + patch 解析器 + 修改 ToolRegistry）
- 新增代码：~450 行
- 开发周期：~3 天（1 人）
- 难点：patch 格式解析——GPT 的 patch 格式非标准，需参考 OpenCode 的 `Patch.parsePatch()` 实现

**意义**：多模型支持是 Qwen Code 的核心竞争力——但工具层没有适配不同模型的输出偏好。
**缺失后果**：GPT 模型在 Qwen Code 中编辑准确性低于 OpenCode——用户可能因此弃用。
**改进收益**：GPT 用原生 diff 格式编辑 → 大幅减少编辑失败率 → 多模型体验统一。

---

<a id="item-3"></a>

### 3. MultiEdit 工具——单文件批量编辑（P1）

**问题**：修改一个文件中的 N 处代码，当前需要调用 N 次 Edit 工具。每次调用都是一次完整的工具调用循环（模型生成 → 权限检查 → 执行 → 返回结果）——**N 次网络往返 + N 次权限弹窗**。

**OpenCode 的解决方案——MultiEdit 工具**：

OpenCode 的 `multiedit` 工具接受一个 edits 数组，在单次工具调用中对同一文件执行多次编辑：

```typescript
// OpenCode: tool/multiedit.ts
parameters: z.object({
  filePath: z.string(),
  edits: z.array(z.object({
    filePath: z.string(),
    oldString: z.string(),
    newString: z.string(),
    replaceAll: z.boolean().optional(),
  })),
})
```

**关键设计细节**：

- **顺序执行**：edits 数组按顺序逐个应用（前一个编辑的结果是后一个的输入），避免偏移量冲突
- **复用 EditTool**：内部直接调用 `EditTool.execute()`——不重复实现编辑逻辑
- **单次权限检查**：只弹一次权限确认，覆盖所有编辑
- **统一结果**：返回最后一次编辑的 output（包含完整文件内容），metadata 包含所有编辑的结果

**OpenCode 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `tool/multiedit.ts` (~40行) | `MultiEditTool.execute()`、顺序循环调用 `EditTool` |
| `tool/multiedit.txt` | tool description（指导模型何时用 multiedit vs edit） |
| `tool/edit.ts` | 底层 `EditTool`——被 multiedit 复用 |

**Qwen Code 现状**：仅有单次 Edit 工具。修改同一文件 5 处 = 5 轮工具调用。每轮调用增加 ~1-3 秒延迟 + 1 次权限弹窗（如未全局放行）。

**Qwen Code 修改方向**：

```
① 新增 MultiEdit 工具（~50 行）
   - 接受 edits: Array<{oldString, newString, replaceAll}>
   - 循环调用现有 Edit 工具逻辑
   - 单次权限检查

② 在 system prompt 中添加使用指导
   - 修改同一文件多处时优先使用 MultiEdit
   - 编辑顺序：从文件尾部到头部（避免行号偏移）
```

**实现成本评估**：
- 涉及文件：~2 个（新建 MultiEdit + 注册到工具列表）
- 新增代码：~50 行
- 开发周期：~1 天（1 人）
- 难点：无

**意义**：编辑效率直接影响用户感知的 Agent 速度。
**缺失后果**：5 处修改 = 5 轮往返 = 用户等 10-15 秒看 5 次权限弹窗。
**改进收益**：5 处修改 = 1 轮往返 = 用户等 2-3 秒看 1 次弹窗。**5x 编辑速度提升**。

---

<a id="item-4"></a>

### 4. Session 分叉与回退（P1）

**问题**：用户让 Agent 用方案 A 修改了代码，效果不好，想回到修改前试方案 B。当前只能手动 git stash/checkout 恢复代码，重新开始对话——对话上下文全部丢失。

**OpenCode 的解决方案——SessionRevert 服务**：

OpenCode 实现了完整的 session 分叉/回退系统，核心是 `SessionRevert` 命名空间：

| 操作 | 做什么 |
|------|--------|
| `revert(sessionID, messageID, partID?)` | 将文件系统回退到指定消息/工具调用之前的状态 |
| `unrevert(sessionID)` | 撤销回退——恢复到回退前的状态 |
| `cleanup(session)` | 确认回退——删除被回退的消息，释放 snapshot |

**关键设计细节**：

- **Git Snapshot 驱动**：`Snapshot.track()` 在回退前创建 git snapshot（stash 或 commit），`Snapshot.restore()` 恢复——利用 git 作为文件系统时间旅行的基础设施
- **Patch 反向应用**：收集从回退点到当前的所有 `patch` 类型 part，通过 `Snapshot.revert(patches)` 反向应用
- **Diff 计算**：回退后自动计算 `summary_additions / summary_deletions / summary_files`，用于 UI 展示"本次回退影响了多少代码"
- **Session 表支持**：`session.revert` JSON 字段存储 `{messageID, partID?, snapshot?, diff?}`——持久化回退状态，刷新后可继续
- **`parent_id` 支持分叉**：Session 表有 `parent_id` 字段，支持从某个会话分叉出新会话（继承部分历史）
- **安全检查**：`SessionPrompt.assertNotBusy()` 确保回退时 Agent 不在执行中——避免并发修改

**OpenCode 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `session/revert.ts` (~176行) | `SessionRevert.revert()`、`unrevert()`、`cleanup()`、git snapshot 集成 |
| `session/session.sql.ts` | `revert` JSON 列、`parent_id` 分叉支持、`version` 字段 |
| `snapshot/` 目录 | `Snapshot.track()`、`Snapshot.restore()`、`Snapshot.revert()`、`Snapshot.diff()` |
| `session/index.ts` | `Session.setRevert()`、`Session.clearRevert()`——持久化回退状态 |

**Qwen Code 现状**：**线性会话，无分叉/回退**。用户只能通过 `/clear` 清空重来，或依赖 git 手动恢复文件。对话历史一旦前进就不可撤回。

**Qwen Code 修改方向**：

```
① 新增 SessionSnapshot 服务（~150 行）
   - 利用 git stash 或临时 commit 创建文件快照
   - restore()：git checkout 恢复快照
   - diff()：计算快照与当前状态的差异

② 新增 SessionRevert 逻辑（~100 行）
   - revert(sessionId, messageIndex)：截断消息历史 + 恢复文件快照
   - unrevert()：恢复截断的消息 + 恢复文件到回退前状态

③ 在 JSONL 会话格式中增加元数据
   - revert_state: {messageIndex, snapshotRef}
   - 或迁移到 SQLite 后直接用列存储（见第 5 项）

④ 新增 /revert 命令（~30 行）
   - /revert <n>：回退到第 n 条消息
   - /unrevert：撤销回退
```

**实现成本评估**：
- 涉及文件：~6 个
- 新增代码：~300 行
- 开发周期：~5 天（1 人）
- 难点：git snapshot 管理——需处理 dirty working tree、untracked files 等边界情况

**意义**："试错-回退-再试"是 AI 辅助开发的核心工作流——用户经常需要 Agent 尝试多种方案。
**缺失后果**：方案失败后用户需手动恢复代码 + 重新建立对话上下文——严重中断工作流。
**改进收益**：一键回退到任意对话节点 + 文件系统同步恢复——探索多方案的成本从"分钟级"降为"秒级"。

---

<a id="item-5"></a>

### 5. SQLite 持久化（P1）

**问题**：Qwen Code 使用 JSONL 文件存储会话历史——追加写入简单但读取性能差。一个 500 轮对话的 JSONL 文件可能 10MB+，加载需读取整个文件。无法按条件查询（如"找所有提到 auth 的会话"），无索引、无并发写安全。

### 5.1 行业背景：Code Agent 会话存储的现状

| Agent | 存储格式 | 位置 | 特点 |
|-------|---------|------|------|
| **Claude Code** | JSONL（每会话一文件） | `~/.claude/projects/<cwd-hash>/*.jsonl` | 追加写入，崩溃安全（每行独立 JSON），可 `grep` 查看 |
| **Gemini CLI** | JSON 文件 | `~/.gemini/tmp/<project>/chats/` | 30 天自动过期，含 token 统计 |
| **OpenCode** | **SQLite（Drizzle ORM）** | `~/.local/share/opencode/opencode.db` | WAL 模式，索引查询，v1.1 从 JSON 迁移 |
| **Qwen Code** | JSONL（继承 Gemini CLI） | `~/.qwen/projects/<hash>/*.jsonl` | 追加写入，无索引 |

一个实际案例的数据（来源：[社区博客](https://stanislas.blog/2026/01/tui-index-search-coding-agent-sessions/)）：某开发者的 OpenCode 有 **9,847 个 JSON 文件**（迁移前），而 Claude Code 仅 **827 个 JSONL 文件**——OpenCode 原来的格式将 session/message/part 分到不同目录，造成海量小文件。这是驱动 SQLite 迁移的关键原因之一。

### 5.2 SQLite vs JSONL：权衡分析

| 维度 | JSONL | SQLite |
|------|-------|--------|
| **读取速度** | O(n) 全文件扫描 | O(log n) 索引查询 |
| **写入安全** | ✓ 追加写入天然崩溃安全 | ⚠ 需 WAL 模式保证 |
| **并发安全** | ⚠ 多进程追加可能交错 | ✓ WAL 模式读写并发 |
| **查询能力** | 无（需全量加载 + 内存过滤） | ✓ SQL + 索引 + FTS5 全文搜索 |
| **人类可读** | ✓ `cat` / `grep` 直接查看 | ✗ 需工具查看 |
| **Git 可追踪** | ✓ 可提交到版本控制 | ✗ 二进制文件不适合 Git |
| **NFS 兼容** | ✓ 普通文件 I/O | ✗ SQLite 在 NFS 上不可靠（[OpenCode #14970](https://github.com/anomalyco/opencode/issues/14970)） |
| **空间效率** | 中等 | 优（JSON 18GB → SQLite 4.8GB 的实际案例） |
| **迁移风险** | — | ⚠ 见下方"已知问题" |

**性能数据**（来源：[sqlite.org](https://sqlite.org/fasterthanfs.html)、[better-sqlite3 benchmarks](https://github.com/WiseLibs/better-sqlite3/blob/master/docs/benchmark.md)）：
- SQLite 读取 blob 比文件系统快 **35%**（内存映射 I/O 可达 10x）
- WAL 模式：**70,000 读/秒 + 3,600 写/秒**（vs 回滚模式 5,600 读 + 291 写）
- better-sqlite3 vs node-sqlite3：读取单行快 **12x**（313,899 vs 26,780 ops/sec）

### 5.3 OpenCode 的实现与演进

OpenCode 于 **2026-02-13** 引入 SQLite（PR [#10597](https://github.com/anomalyco/opencode/pull/10597) "sqlite again"——暗示此前有过一次尝试后回滚）。后续经历了多次迁移修复和重构。

**Schema 设计**（Drizzle ORM）：

| 表 | 主要字段 | 用途 |
|----|---------|------|
| `session` | id(ULID), project_id, parent_id, title, version, revert(JSON), permission(JSON) | 会话元数据 + 分叉 |
| `message` | id, session_id, data(JSON) | 消息信息（role/model/token 统计） |
| `part` | id, message_id, session_id, data(JSON) | 消息部件（text/tool/patch/image 等） |
| `todo` | session_id, content, status, priority, position | 待办事项 |
| `permission` | project_id, data(JSON) | 权限规则集 |

**关键设计细节**：

- **WAL 模式 + NORMAL 同步**：平衡性能和安全——WAL 允许读写并发，NORMAL 同步避免每次写入 fsync
- **级联删除**：`onDelete: "cascade"` 确保删除 session 时自动级联
- **索引优化**：`session_project_idx`、`message_session_time_created_id_idx` 等
- **事件总线**：所有 session 变更发布事件（Created/Updated/Deleted/Diff/Error），驱动 TUI 实时更新
- **迁移工具**：首次启动扫描旧 JSON 目录导入 SQLite，通过 index 文件追踪一次性执行（[PR #13874](https://github.com/anomalyco/opencode/pull/13874)）
- **惰性初始化**：数据库连接延迟到首次使用

### 5.4 已知问题与教训

OpenCode 的 SQLite 迁移暴露了多个问题，对 Qwen Code 的决策有重要参考：

| Issue | 问题 | 教训 |
|-------|------|------|
| [#14970](https://github.com/anomalyco/opencode/issues/14970) | NFS 上 SQLite 损坏 | **不支持网络文件系统**——Docker 挂载 / NFS 场景需降级到文件模式 |
| [#14194](https://github.com/anomalyco/opencode/issues/14194) | 本地 + Docker 共享配置导致 SQLite 损坏 | 多进程跨容器访问同一 DB 不安全 |
| [#13636](https://github.com/anomalyco/opencode/issues/13636) | 迁移丢失会话 | CLI 和 Desktop 迁移路径不一致 |
| [#17589](https://github.com/anomalyco/opencode/issues/17589) | SQLITE_FULL 未处理崩溃 | 磁盘满时无优雅降级 |
| [#13969](https://github.com/anomalyco/opencode/issues/13969) | 迁移后 100% CPU | 后台大量 IO |
| [#16885](https://github.com/anomalyco/opencode/issues/16885) | 非 latest 通道重复迁移 | 迁移状态追踪不完善 |

**核心教训**：SQLite 引入了 JSONL 不存在的失败模式——NFS 不兼容、跨容器损坏、迁移数据丢失。选择 SQLite 需要同时解决这些边缘场景。

### 5.5 竞品选择 JSONL 的理由

Claude Code 和 Gemini CLI 选择 JSONL 而非 SQLite，并非因为不知道 SQLite 的优势，而是有意为之：

1. **崩溃安全**：JSONL 每行独立——部分写入不影响已有行。SQLite 需 WAL + journal 保护
2. **可调试性**：`cat session.jsonl | grep "error"` 直接可用
3. **简单性**：无 ORM、无迁移、无 native 模块编译
4. **跨环境兼容**：NFS、Docker、WSL 都没问题

### 5.6 推荐方案：混合架构

| 层 | 技术 | 用途 |
|---|------|------|
| **持久化层** | JSONL（保留现有） | 追加写入，崩溃安全，人类可读 |
| **查询层** | SQLite（新增） | 启动时从 JSONL 构建索引，支持查询/搜索/分页 |
| **同步** | 后台监听 | JSONL 变更时增量更新 SQLite 索引 |

这种混合架构兼顾了两者优势：
- JSONL 作为"source of truth"——崩溃安全、可调试、NFS 兼容
- SQLite 作为"查询加速层"——启动时构建，丢失可重建

**OpenCode 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `session/session.sql.ts` (~85行) | `SessionTable`、`MessageTable`、`PartTable`、`TodoTable`、`PermissionTable` |
| `storage/storage.ts` | 通用 KV 存储（SQLite 后端） |

**Qwen Code 修改方向**：

```
方案 A：直接迁移到 SQLite（OpenCode 模式）
  ① 引入 better-sqlite3 + drizzle-orm
  ② Session/Message/Part 三表设计 + WAL 模式
  ③ JSONL → SQLite 迁移工具
  ④ 需处理 NFS/Docker 边缘场景
  ⚠ 风险：OpenCode 已暴露 6+ 个迁移问题

方案 B：混合架构（推荐）
  ① 保留 JSONL 作为持久层（不改现有写入逻辑）
  ② 新增 SQLite 索引层（启动时从 JSONL 构建）
  ③ 查询/搜索/分页通过 SQLite 提供
  ④ SQLite 丢失可从 JSONL 重建——无数据丢失风险
  ⚠ 需要同步机制（JSONL 变更 → 增量更新 SQLite）
```

**实现成本评估**：
- 方案 A：~2 周（含迁移工具和边缘场景处理）
- 方案 B：~1 周（无迁移风险，SQLite 仅做索引）
- 难点：方案 A 的迁移兼容性和 NFS 处理；方案 B 的 JSONL→SQLite 同步一致性

**意义**：会话存储是 CLI Agent 的基础设施——影响启动速度、历史搜索、并发安全。
**缺失后果**：大会话加载慢（10MB JSONL 全量读取）、无法搜索历史、分叉/回退功能缺乏持久化基础。
**改进收益**：毫秒级会话查询 + 全文搜索 + 为 session 分叉/HTTP 服务器提供数据基础。

---

<a id="item-6"></a>

### 6. 语义代码搜索——Exa 集成（P1）

**问题**：Agent 需要了解某个库/API 的用法，当前只能通过 WebSearch 搜索然后 WebFetch 抓取页面——两步操作，且搜索结果质量参差不齐。更重要的是，通用搜索不理解代码语义——搜索 "React useState" 可能返回新闻文章而非代码示例。

**OpenCode 的解决方案——CodeSearch 工具（Exa MCP）**：

OpenCode 内置 `codesearch` 工具，通过 Exa 的 MCP 接口（`mcp.exa.ai`）进行语义级代码搜索：

```
模型调用 codesearch("React useState hook examples", tokensNum=5000)
  → POST https://mcp.exa.ai/mcp
  → 返回结构化代码上下文（代码片段 + 文档摘要）
```

**关键设计细节**：

- **MCP 协议**：使用标准 JSON-RPC 2.0 调用 Exa 的 `get_code_context_exa` 方法——不是普通 HTTP API
- **Token 控制**：`tokensNum` 参数（1000-50000）控制返回内容量——小查询 5K，全面文档 50K
- **SSE 响应解析**：响应格式为 Server-Sent Events，需解析 `data:` 前缀行
- **超时控制**：30 秒超时 + AbortController，防止网络问题导致 Agent 挂起
- **权限检查**：`permission: "codesearch"` 需用户授权——搜索查询可能暴露项目上下文
- **无 API Key**：直接通过 Exa MCP 公共端点，无需用户配置 API Key

**OpenCode 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `tool/codesearch.ts` (~100行) | `CodeSearchTool.execute()`、`API_CONFIG.BASE_URL = "https://mcp.exa.ai"`、SSE 解析 |
| `tool/codesearch.txt` | tool description——指导模型何时使用代码搜索 vs 普通搜索 |

**Qwen Code 现状**：有 `web-search`（Tavily/Google/DashScope）和 `web-fetch`，但无专用代码搜索。搜索 "Next.js partial prerendering configuration" 得到的是博客文章而非精确的 API 文档和代码示例。

**Qwen Code 修改方向**：

```
① 新增 CodeSearch 工具（~100 行）
   - 接入 Exa MCP 端点（公共，无需 API Key）
   - tokensNum 参数控制返回量
   - 30 秒超时 + SSE 响应解析

② 或：接入 DashScope 代码搜索 API
   - 如果阿里云有类似的代码语义搜索能力
   - 可复用现有 DashScope 认证

③ 在 system prompt 中添加使用指导
   - 搜索 API/库用法 → 优先用 codesearch
   - 搜索新闻/文章 → 用 web-search
```

**实现成本评估**：
- 涉及文件：~2 个
- 新增代码：~100 行
- 开发周期：~2 天（1 人）
- 难点：无——纯 HTTP 请求 + SSE 解析

**意义**：Agent 经常需要查阅外部库的 API 用法——代码搜索质量直接影响生成代码的正确性。
**缺失后果**：Agent 使用不熟悉的库时，只能靠训练数据中的知识（可能过时）——导致 API 用法错误。
**改进收益**：精确的代码上下文 → 模型生成正确 API 调用的概率大幅提升。

---

<a id="item-7"></a>

### 7. Batch 工具——并行工具调用（P2）

**问题**：Agent 需要同时读取 5 个文件、同时 grep 3 个关键词。当前每个工具调用串行执行——5 个 Read = 5 轮往返。模型无法在一次响应中表达"这些操作可以并行"。

**OpenCode 的解决方案——Batch 工具**：

OpenCode 的 `batch` 工具接受一个 `tool_calls` 数组（最多 25 个），使用 `Promise.all()` 并行执行所有工具调用：

```typescript
// 模型调用示例
batch({
  tool_calls: [
    { tool: "read", parameters: { filePath: "src/a.ts" } },
    { tool: "read", parameters: { filePath: "src/b.ts" } },
    { tool: "grep", parameters: { pattern: "TODO", path: "src/" } },
  ]
})
// → 3 个操作并行执行，单次返回
```

**关键设计细节**：

- **并行执行**：`Promise.all(toolCalls.map(call => executeCall(call)))` 真正并行
- **上限 25**：超过 25 个调用的部分被丢弃并标记错误 `"Maximum of 25 tools allowed in batch"`
- **禁止递归**：`DISALLOWED = new Set(["batch"])` 防止 batch 嵌套 batch
- **独立 UI 追踪**：每个子调用生成独立的 `Part`（partID），UI 可分别展示运行状态/结果
- **错误隔离**：单个调用失败不影响其他——`try/catch` 包裹每个调用
- **安全限制**：MCP 和外部工具不能被 batch——`"External tools (MCP, environment) cannot be batched"`
- **鼓励使用**：成功时输出 `"Keep using the batch tool for optimal performance in your next response!"`

**OpenCode 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `tool/batch.ts` (~150行) | `BatchTool.execute()`、`DISALLOWED` Set、`Promise.all()` 并行、错误隔离 |
| `tool/batch.txt` | tool description——指导模型何时 batch（独立操作）vs 串行（有依赖） |
| `tool/registry.ts` | 工具注册——batch 可调用所有内置工具 |

**Qwen Code 现状**：模型可在单次响应中返回多个工具调用（`parallel_tool_calls`），但 Qwen Code 的工具执行引擎**串行处理**——失去了并行优势。

**Qwen Code 修改方向**：

```
方案 A：工具执行层支持真正的并行（改引擎）
  - 检测模型返回的多个 tool_use block 之间无依赖 → Promise.all()
  - 影响面大，需改消息处理管线

方案 B：新增 Batch 工具（改工具层，推荐）
  - 与 OpenCode 方案一致
  - ~150 行，不改引擎
  - 模型自己决定何时 batch
```

**实现成本评估**：
- 涉及文件：~2 个
- 新增代码：~150 行
- 开发周期：~3 天（1 人，含测试并发安全性）
- 难点：并发文件操作的安全性——两个 Edit 同时修改同一文件需 FileTime Lock（第 1 项）

**意义**：工具调用延迟是 Agent 执行时间的主要瓶颈。
**缺失后果**：5 个 Read 串行 = 5 秒；并行 = 1 秒——用户感知 5x 差异。
**改进收益**：独立操作并行化 → Agent 执行速度显著提升，尤其在探索阶段（大量 Read/Grep）。

---

<a id="item-8"></a>

### 8. HTTP 服务器——多客户端架构（P2）

**问题**：Qwen Code 是单进程 CLI 应用——TUI 和 Agent 引擎紧耦合。无法实现：① Web UI 远程访问 Agent；② 多个终端共享同一 Agent 会话；③ 桌面应用连接 Agent 后端。

**OpenCode 的解决方案——Hono HTTP 服务器**：

OpenCode 内置 Hono HTTP 框架 + WebSocket，作为 Agent 后端的统一入口：

| 组件 | 技术栈 | 作用 |
|------|--------|------|
| HTTP Server | Hono + `@hono/node-server` | RESTful API，默认端口 4096 |
| WebSocket | `@hono/node-ws` | 实时事件推送（消息更新、工具执行状态） |
| CORS | `hono/cors` | 允许 localhost + tauri://localhost + opencode.ai |
| Auth | `hono/basic-auth` | 可选密码保护（`OPENCODE_SERVER_PASSWORD`） |
| Compression | `hono/compress` | gzip 压缩（跳过 SSE 和大 POST） |
| OpenAPI | `hono-openapi` | 自动生成 `/doc` API 文档 |

**关键设计细节**：

- **端口策略**：先尝试 4096，失败则 fallback 到随机端口（`start(4096).catch(() => start(0))`）
- **多客户端共享**：TUI、Web UI、桌面应用都是 HTTP 客户端——共享同一后端的 session 数据
- **Workspace 路由**：`WorkspaceRouterMiddleware` 根据 `directory` query param 路由到不同项目实例
- **可选 MDNS**：非 loopback 地址时自动发布 mDNS 服务（局域网设备自动发现）
- **优雅关闭**：`stop(close?)` 先 unpublish mDNS，再 close server + close idle connections
- **SSE 跳过压缩**：`/event`、`/global/event`、`/global/sync-event` 路径跳过 gzip——SSE 流不能被压缩

**OpenCode 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `server/server.ts` (~350行) | `Server.listen()`、`ControlPlaneRoutes()`、Hono app 配置 |
| `server/router.ts` | `WorkspaceRouterMiddleware`——按目录路由 |
| `server/routes/` | API 路由定义（session CRUD、message、auth 等） |
| `server/mdns.ts` | MDNS 服务发现（见第 10 项） |
| `server/instance.ts` | 项目实例管理 |

**Qwen Code 现状**：单进程 CLI，`packages/webui/` 仅是 UI 组件库（不含 HTTP 服务器）。无法从浏览器或其他终端访问 Agent。

**Qwen Code 修改方向**：

```
① 新增可选 --serve 模式（不改默认行为）
   - 启动 HTTP 服务器（Express 或 Hono）
   - WebSocket 推送实时事件

② API 设计
   - POST /session/:id/message —— 发送用户消息
   - GET /session/:id/messages —— 获取消息列表
   - GET /event —— SSE 实时事件流
   - 复用现有 Agent 引擎

③ Web UI 客户端
   - 复用 packages/webui/ 组件
   - 连接 HTTP 后端
```

**实现成本评估**：
- 涉及文件：~15 个
- 新增代码：~1000 行
- 开发周期：~3 周（1 人）
- 难点：将现有紧耦合的 TUI ↔ Agent 交互抽象为 API

**意义**：HTTP 服务器是"多端"战略的基础——Web UI、桌面应用、API 集成都依赖它。
**缺失后果**：Qwen Code 局限于单终端使用——无法远程访问、无法 Web 集成。
**改进收益**：解锁 Web UI + 桌面应用 + API 集成——从 CLI 工具进化为平台。

---

<a id="item-9"></a>

### 9. Instance 上下文隔离（P2）

**问题**：用户可能同时在两个终端中、两个不同项目目录下使用 Qwen Code。如果全局状态（如文件追踪、权限规则、session 列表）不按目录隔离，项目 A 的 permission 规则会影响项目 B。

**OpenCode 的解决方案——Instance 命名空间**：

OpenCode 通过 `Instance` 管理每个项目目录的独立状态：

- **`Instance.directory`**：当前项目根目录（从 CWD 向上查找 `.git` 或 `.opencode.json`）
- **`Instance.worktree`**：git worktree 根目录（可能与 directory 不同）
- **`InstanceState`**：Effect 框架的状态容器——每个 Instance 有自己的 state 实例
- **HTTP 路由隔离**：`WorkspaceRouterMiddleware` 根据请求的 `directory` 参数路由到对应 Instance

**Qwen Code 现状**：会话按目录存储在 `~/.qwen/projects/<hash>/` 中（已有基础隔离），但运行时状态（如工具注册、权限、文件追踪）是全局的。

**Qwen Code 修改方向**：

```
① 如果实现文件时间锁（第 1 项），FileTimeTracker 需按 session 隔离（已含）
② 如果实现 HTTP 服务器（第 8 项），需按 directory 路由到不同 Instance
③ 当前单终端场景下，隔离需求不紧迫
```

**实现成本评估**：~3 天（与 HTTP 服务器联合实现时自然解决）

---

<a id="item-10"></a>

### 10. MDNS 服务发现（P3）

**问题**：HTTP 服务器启动后，其他设备如何知道它的 IP 和端口？手动输入 URL 不友好。

**OpenCode 的解决方案——Bonjour mDNS**：

```typescript
// server/mdns.ts（~60行）
bonjour.publish({
  name: `opencode-${port}`,
  type: "http",
  host: "opencode.local",
  port,
  txt: { path: "/" },
})
```

- 使用 `bonjour-service` npm 包
- 非 loopback 地址时自动发布
- 其他设备通过 mDNS 发现 → 自动连接

**前提**：需要先实现 HTTP 服务器（第 8 项）。

**实现成本评估**：~1 天（~60 行）

---

## 优先级矩阵

| 功能 | 工作量 | 用户价值 | 优先级 | 依赖 |
|------|:------:|:--------:|:------:|------|
| 文件时间锁 | 1 天 | **极高**（防数据丢失） | **P0** | 无 |
| apply_patch | 3 天 | **高**（多模型适配） | **P1** | 无 |
| MultiEdit | 1 天 | **高**（编辑效率 5x） | **P1** | 无 |
| Session 分叉回退 | 5 天 | **高**（探索多方案） | **P1** | SQLite（可选） |
| SQLite 持久化 | 2 周 | **高**（性能+可扩展） | **P1** | 无 |
| 语义代码搜索 | 2 天 | 中 | **P1** | 无 |
| Batch 工具 | 3 天 | 中 | **P2** | 文件时间锁 |
| HTTP 服务器 | 3 周 | 中（平台基础） | **P2** | SQLite |
| Instance 隔离 | 3 天 | 低 | **P2** | HTTP 服务器 |
| MDNS 发现 | 1 天 | 低 | **P3** | HTTP 服务器 |

---

## Qwen Code 的竞争优势（无需对标）

| 功能 | Qwen Code | OpenCode |
|------|-----------|----------|
| **Agent Arena** | ✅ 多模型并行竞争评估 | ❌ |
| **免费 OAuth** | ✅ 每天 1000 次 | ❌ |
| **扩展格式转换** | ✅ Claude/Gemini 扩展自动转换 | ❌ |
| **6 语言 CLI** | ✅ 中/英/日/韩/法/德 | ❌ TUI 仅英文 |
| **Doom Loop 检测** | ✅ 工具 5 次 + 内容 10 次 | ⚠️ 仅权限拒绝 3 次 |
| **多渠道部署** | ✅ DingTalk/Telegram/WeChat/Web | ❌ TUI + Web |
| **Gemini CLI 兼容** | ✅ fork 自 Gemini CLI | ❌ 独立架构 |

---

<a id="item-11"></a>

### 11. Snapshot 会话快照与回滚（P1）

**问题**：Agent 修改代码后发现方向错误，用户需要手动 `git checkout` 回退。没有会话级别的快照和回滚。

**OpenCode 的解决方案**：`snapshot/index.ts`（726 行）——基于 Git 的隔离快照系统：

| API | 功能 |
|-----|------|
| `track()` | 在关键操作后创建文件快照 |
| `patch(hash)` | 获取两次快照间的文件变更 |
| `restore(snapshot)` | 回滚到指定快照 |
| `diff(hash)` / `diffFull(from, to)` | 行级变更对比（additions/deletions） |

快照存储在 `Global.Path.data/snapshot/` 独立目录，与项目 Git 仓库隔离。

**Qwen Code 现状**：无会话快照系统。检查点功能（checkpoint）默认关闭且不支持回滚。

**Qwen Code 修改方向**：参考 OpenCode 的 Git 隔离快照模式，在每次工具执行后自动 track，提供 `/rewind` 回退命令。

**实现成本**：~5 天（Git 快照管理 + 回滚逻辑 + UI 集成）

---

<a id="item-12"></a>

### 12. Provider 多模型提供商系统（P1）

**问题**：Qwen Code 硬编码支持 Anthropic/Google/Qwen 等少数 Provider。添加新 Provider 需要修改核心代码。

**OpenCode 的解决方案**：`provider/`（31 文件 7,927 行）——可扩展的多 Provider 架构：

**内置 Provider**（25+）：

| 类别 | Provider |
|------|---------|
| 大厂 | Anthropic、OpenAI、Azure、Google、Vertex |
| 开源 | Groq、Together AI、Mistral、Cohere |
| 平台 | GitHub Copilot、GitLab、Amazon Bedrock |
| 其他 | XAI、Perplexity、Venice |

**核心特性**：
- 动态 Provider 发现（npm 包 + 插件加载）
- Per-provider 认证（API Key / OAuth / Service Account）
- 模型列表 + 模糊搜索
- Provider 特定的响应转换（Copilot 分页、GitHub Models API 适配）
- 速率限制 + SSE 超时处理

**Qwen Code 现状**：`packages/core/src/content/` 中硬编码 3-4 个 Provider。

**实现成本**：~3 周（Provider 插件框架 + 5-10 个主要 Provider 适配）

---

<a id="item-13"></a>

### 13. Plugin 插件系统（P1）⚠️ 部分赶超（Hook 能力反超，但架构模式不同）

**问题**：Qwen Code 的 Hook 系统和扩展机制无法通过 npm 包分发和加载第三方插件。

**OpenCode 的解决方案**：`plugin/`（10 文件 2,618 行）——完整的插件基础设施：

| 组件 | 功能 |
|------|------|
| `loader.ts` | npm 包 + 本地插件加载 |
| `meta.ts` | 插件元数据管理 |
| `shared.ts` | 插件间共享能力 |
| 内置 auth 插件 | Codex、GitHub Copilot、GitLab、Poe、Cloudflare |

**18 种 Hook 类型**（`packages/plugin/src/index.ts`）

**Qwen Code 现状（2026-04-16 核对）**：[PR#2827](https://github.com/QwenLM/qwen-code/pull/2827) 于 2026-04-15 合并，Qwen Code hook 系统已达 **17,443 行**（src only），远超 OpenCode 的 2,618 行。支持 **12+ 种事件**（SessionStart/End、UserPromptSubmit、PreToolUse/PostToolUse/PostToolUseFailure、StopFailure、PostCompact 等）+ **4 种 Hook 类型**（command / HTTP POST / Function / Async）+ **SSRF 防护**（`ssrfGuard.ts` / `urlValidator.ts`）。

**仍存差距**：Qwen Code 的 Hook **不支持 npm 包分发**——OpenCode 的 plugin 系统允许 `npm install @opencode/plugin-xxx` 加载第三方插件并自动注册 hook，Qwen Code 的 hook 是配置文件级注册（`settings.json`），无法跨用户分发。

**实现成本**：npm 插件加载层 ~2 周（Hook 核心已就绪，差的是分发和加载）

---

<a id="item-14"></a>

### 14. Worktree 增强管理（P1）✅ 已赶超

**问题**：Qwen Code 的 `gitWorktreeService.ts`（826 行）提供基础 worktree 支持，但缺少自动命名、子模块处理、fsmonitor 管理等。

**OpenCode 的解决方案**：`worktree/index.ts`（612 行）——生产级 worktree 管理：

| 功能 | OpenCode | Qwen Code |
|------|---------|-----------|
| 自动命名 | `opencode/slug-name` 格式 | 手动指定 |
| 子模块处理 | `--recurse-submodules` | 无 |
| fsmonitor | 自动管理 daemon | 无 |
| 启动脚本 | 每 worktree 自动执行 | 无 |
| 失败恢复 | 智能清理 + 重试 | 基础清理 |

**Qwen Code 现状（2026-04-16 核对）**：`gitWorktreeService.ts` **826 行**（src only），超过 OpenCode 的 612 行。已支持自动命名、智能清理、worktree 隔离执行。

**仍存差距**：子模块递归（`--recurse-submodules`）、fsmonitor daemon 自动管理、每 worktree 启动脚本——这些 OpenCode 特色在 Qwen Code 中仍缺失，但核心 worktree 管理**已达到可用水平**。

**实现成本**：✅ 核心已实现（子模块/fsmonitor 增强约 1 天）

---

<a id="item-15"></a>

### 15. ACP Agent Client Protocol 服务端（P2）

**问题**：Qwen Code 只能被用户直接操作，不能被其他 Agent 或应用程序以 API 形式调用。

**OpenCode 的解决方案**：`acp/`（3 文件 1,987 行）——完整的 Agent Client Protocol 服务端实现：

- `agent.ts`（1,847 行）：ACP agent 完整实现
- Session fork/resume 支持
- 模型中途切换
- 权限请求/审批流程
- 多 MCP 服务器支持
- 流式响应 + 上下文限制管理

**Qwen Code 现状**：有 ACP 客户端集成工具，但无 ACP 服务端。

**实现成本**：~2 周（协议实现 + 会话管理）

---

<a id="item-16"></a>

### 16. LSP 多语言服务器管理（P2）✅ 已赶超

**问题**：代码智能依赖 AST 解析和 grep，缺少 LSP 提供的精确语义信息（go-to-definition、hover、diagnostics）。

**OpenCode 的解决方案**：`lsp/`（5 文件 2,919 行）——完整 LSP 客户端：

| 功能 | 说明 |
|------|------|
| 服务器生命周期 | 按语言自动启动/停止 Language Server |
| 文档符号 | `documentSymbol` 查询 |
| 跳转定义 | `gotoDefinition` |
| Hover 信息 | 类型/文档提示 |
| 诊断聚合 | 多服务器错误/警告汇总 |
| 自动发现 | 从配置和 PATH 自动检测 Language Server |

**Qwen Code 现状（2026-04-16 核对）**：`packages/core/src/lsp/` 已发展为 **7,422 行**（src only），**2.5× 超过** OpenCode 的 2,919 行。包含：

| 模块 | 功能 |
|---|---|
| `NativeLspService.ts` | 完整 LSP 客户端管理 |
| `LspServerManager.ts` | 多服务器生命周期管理 |
| `LspConfigLoader.ts` | 配置自动加载 |
| `LspConnectionFactory.ts` | 连接工厂 |
| `LspLanguageDetector.ts` | 语言检测 |
| 进行中 PR | [PR#3170](https://github.com/QwenLM/qwen-code/pull/3170) 官方 SDK + didSave 实时诊断 |

**实现成本**：✅ 已实现（7,422 行 vs OpenCode 2,919 行）

---

<a id="item-17"></a>

### 17. NPM 动态包安装（P2）

**问题**：工具和 Provider 插件需要用户手动安装依赖，缺乏运行时动态安装能力。

**OpenCode 的解决方案**：`npm/index.ts`（188 行）——使用 `@npmcli/arborist`（npm 官方库）：

- 依赖解析 + 版本检查
- 文件锁防止并发安装
- 入口点解析（multi-bin 包）
- 缓存到 `~/.opencode/cache/packages/`

**Qwen Code 现状**：`extension/npm.ts`（~100 行）使用不同方案。

**实现成本**：~2 天

---

<a id="item-18"></a>

### 18. Permission 规则引擎（P2）

**问题**：Qwen Code 的权限系统基于简单的请求/批准流程，缺少基于规则的自动化权限决策。

**OpenCode 的解决方案**：`permission/`（4 文件 520 行）——规则驱动权限系统：

| 组件 | 功能 |
|------|------|
| `evaluate.ts` | 规则求值引擎 |
| `schema.ts` | 权限规则 Schema |
| Actions | allow / deny / ask |
| Pattern 匹配 | 通配符路径匹配 |
| Bus 集成 | 权限请求发布为事件（UI/API 响应） |
| 缓存 | always / once / never |

**Qwen Code 现状**：L3→L4→L5 多层评估已存在，但规则定义不如 OpenCode 灵活。

**实现成本**：~3 天

---

<a id="item-19"></a>

### 19. PTY 伪终端管理（P2）

**问题**：Qwen Code 的 Shell 执行是简单的 `spawn()`，不支持 PTY 分配和交互式命令。

**OpenCode 的解决方案**：`pty/`（5 文件 492 行）：

- PTY 分配 + 进程管理
- WebSocket 多路复用（多客户端共享一个 PTY）
- 光标位置追踪（0x00 + JSON 元数据）
- 循环 buffer（2MB 上限）防止内存泄漏
- Socket 订阅输出流

**Qwen Code 现状**：基础终端执行，无 PTY 支持。

**实现成本**：~2 周

---

<a id="item-20"></a>

### 20. Skill 动态发现 + 自创/自改进（P2）✅ 已赶超

**问题**：Qwen Code 的 Skill 由人类编写和维护——Agent 完成复杂任务后，成功的方法没有被自动沉淀为可复用的 Skill。下次遇到类似任务，Agent 从零开始。

**OpenCode 的解决方案**：`skill/`（2 文件 393 行）——多路径 Skill 发现。

**Qwen Code 现状（2026-04-16 核对）**：`packages/core/src/skills/` 已发展为 **2,673 行**（src only），**6.8× 超过** OpenCode 的 393 行。包含：

| 模块 | 功能 |
|---|---|
| `skill-load.ts` | 多路径 Skill 发现（`.qwen/`、`.agents/`、`.claude/`、项目目录） |
| `skill-manager.ts` | Skill 注册、验证、生命周期管理 |
| `types.ts` | YAML frontmatter Schema 定义 |
| 内置 Skill | `/review`（bundled，500+ 行 SKILL.md） |
| `model:` 覆盖 | [PR#2949](https://github.com/QwenLM/qwen-code/pull/2949) ✓ Skill 级模型切换 |

**参考实现**：[Hermes Agent](https://github.com/nousresearch/hermes-agent)（`tools/skill_manager_tool.py`）实现了 **Agent 自创 + 自改进 Skill**——详见 [闭环学习系统](./closed-learning-loop-deep-dive.md)。

**仍存差距**：Agent 自创 Skill 能力（Hermes 模式）尚未实现——当前所有 Skill 仍由人类编写。[PR#3087](https://github.com/QwenLM/qwen-code/pull/3087)（auto-memory + auto-dream）正在推进。

**实现成本**：✅ 动态发现已实现；自创 Skill ~1 周（参考 Hermes）

---

<a id="item-21"></a>

### 21. Git 操作抽象层（P2）

**问题**：Git 操作分散在多个文件中，缺少统一的错误处理和配置管理。

**OpenCode 的解决方案**：`git/index.ts`（303 行）——集中式 Git 服务：

- 统一 `spawn()` + 标准化 config flags（`autocrlf=false`、`longpaths=true`）
- Status 查询（added/deleted/modified）
- Diff 统计（additions/deletions）
- Base branch 检测
- NUL 分隔输出解析（处理文件名空格）

**Qwen Code 现状**：Git 操作分散在多处。

**实现成本**：~2 天

---

<a id="item-22"></a>

### 22. Session Share 会话分享（P2）

**问题**：无法将 Agent 会话分享给同事查看或协作。

**OpenCode 的解决方案**：`share/`（2 文件 382 行）：

- 生成可分享的会话 URL
- 会话同步到云端（可选）
- Share secrets 管理
- 会话 diff 导出（`FileDiff[]`）
- 队列化多客户端分享

**Qwen Code 现状**：无会话分享功能。

**实现成本**：~2 周（需要后端 API）

---

<a id="item-23"></a>

### 23. Event Sync 事件溯源（P2）

**问题**：会话状态是内存中的可变对象，难以审计、回放和分布式同步。

**OpenCode 的解决方案**：`sync/`（3 文件 293 行）——Event Sourcing / CQRS 模式：

- `SyncEvent.define()` 注册带版本的事件类型
- 事件从数据库回放
- Projector 模式（事件→状态映射）
- 多版本事件迁移
- 事件订阅

**Qwen Code 现状**：EventEmitter 模式，非事件溯源。

**实现成本**：~2 周

---

<a id="item-24"></a>

### 24. Control-Plane 多工作区管理（P2）

**问题**：单一工作区限制，难以同时管理多个项目。

**OpenCode 的解决方案**：`control-plane/`（7 文件 362 行）：

- Workspace 创建（类型/适配器模式）
- 分支隔离
- SSE 流式就绪通知
- Adaptor 模式（不同工作区类型不同实现）

**Qwen Code 现状**：单工作区上下文。

**实现成本**：~2 周

---

<a id="item-25"></a>

### 25. Format 代码格式化集成（P3）

**问题**：Agent 生成的代码不一定符合项目的格式化规范。

**OpenCode 的解决方案**：`format/`（2 文件 616 行）——可插拔格式化器：

- 自动检测文件类型对应的格式化器（prettier / black / gofmt 等）
- 配置驱动的格式化命令
- 格式化器可用性检查
- Per-session 格式化器状态

**Qwen Code 现状**：有基础格式化，无可插拔系统。

**实现成本**：~1 周

---

<a id="item-26"></a>

### 26. Command 动态命令注册（P3）

**问题**：命令（斜杠命令）是硬编码的，插件无法注册新命令。

**OpenCode 的解决方案**：`command/index.ts`（195 行）——动态命令注册表：

- Schema 驱动的命令注册
- 参数解析
- 帮助文档自动生成
- 权限检查

**Qwen Code 现状**：命令硬编码在 `commands/` 目录。

**实现成本**：~2 天

---

<a id="item-27"></a>

### 27. Effect 框架工具集（P3）

**问题**：OpenCode 使用 Effect-ts 框架管理副作用，提供了一套完整的工具集。

**OpenCode 的解决方案**：`effect/`（6 文件 851 行）——Effect-ts 基础设施：

- Instance 状态管理
- 服务运行时创建
- 跨平台进程 spawn
- Scoped 资源管理

**Qwen Code 现状**：不使用 Effect 框架。此项仅在考虑 Effect-ts 迁移时参考。

> **2026-04-24 更新**：OpenCode 正在大规模迁移到 Effect Schema（PR#23244 migrate 18 built-in tools / PR#24005 session / PR#24027 provider / PR#24040 bus / PR#24029 consolidate PositiveInt/NonNegativeInt / PR#23763/23764/23757 MessageV2 DTOs）。Qwen 对标价值仍低——TypeScript 生态 zod/valibot 更轻量。

---

<a id="item-28"></a>

### 28. 可配置工具输出截断限制 🆕（P2）

**问题**：Qwen Code 的 `BASH_MAX_OUTPUT_DEFAULT = 30_000` 和 `UPPER_LIMIT = 150_000` 硬编码在 `utils/shell/outputLimits.ts`，用户遇到"大量日志被截断"时只能改源码重编译。

**OpenCode 的解决方案**（[PR#23770](https://github.com/sst/opencode/pull/23770)，2026-04-23 合并）——**配置化截断限制**：

- `opencode.json` 新增 `truncate:` 配置项
- `tool/truncate.ts` 读取配置，`tool/bash.ts` 使用配置上限
- 测试覆盖 `truncation.test.ts` 64 个 case

**核心设计**：
```jsonc
{
  "truncate": {
    "bash": { "stdout": 50000, "stderr": 10000 },
    "tool_output": 100000
  }
}
```

**Qwen Code 现状**：三层硬编码上限（Bash 30K / 单工具 50K / 单消息 200K），已在 p2-stability item-45 记录，但**未支持配置化**。

**Qwen Code 修改方向**：
1. `settings.json` 新增 `outputLimits: { bash: {...}, tool: {...}, message: {...} }` schema
2. `outputLimits.ts` / `toolLimits.ts` 读取配置（fallback 到当前硬编码默认）
3. `settings.ts` 添加 `/settings outputLimits` slash command 便捷查看
4. 文档说明上限含义（LLM context 占用、prompt cache 成本）

**实现成本**：~1 天（低风险，配置只是读路径调整）。

**意义**：**高级用户可调**——长日志调试场景下临时放大 stdout 上限；成本敏感场景收紧到 10K 以省 context。
**改进收益**：告别"改源码 → 重编译 → 用完复原"的噩梦循环。

---

<a id="item-29"></a>

### 29. TUI 编辑器上下文 builtin protocol 🆕（P2）

**问题**：用户在 VSCode 里编辑代码遇到问题，想把**当前文件 + 当前选区 + 打开的 tabs + 诊断信息**一起发给 CLI agent。手动复制粘贴太累，而且丢失语义（agent 不知道这是"主动引用"还是"背景提示"）。

**OpenCode 的解决方案**（[PR#24034](https://github.com/sst/opencode/pull/24034)，2026-04-23 合并）——**builtin editor context protocol**：

- 新增 318 行 `cli/cmd/tui/context/editor.ts` —— 定义 context bundle 协议
- `autocomplete.tsx` + `prompt/index.tsx` 消费 context —— `@`  触发补全时能从编辑器读取文件/选区/诊断
- TUI 理解 "selection" / "cursor" / "diagnostics" / "tabs" 四种语义

**核心设计**：
```
Editor (VSCode / Neovim) 
   ↓ builtin protocol (JSON over IPC)
{ type: "selection", file, range, text }
{ type: "cursor", file, line, col }
{ type: "diagnostics", file, diags[] }
{ type: "tabs", openFiles[] }
   ↓
TUI autocomplete + prompt
```

**Qwen Code 现状**：有 VSCode IDE Companion（`packages/vscode-ide-companion/`），但 context 传输是**单向注入**——IDE 推变更到 CLI，CLI 无法按语义请求"当前选区"。用户 `@` 补全只能列文件路径，不能请求"当前编辑器上下文"。

**Qwen Code 修改方向**：
1. `packages/cli/src/ui/context/editor.ts` 定义 `EditorContextBundle` schema（selection/cursor/diagnostics/tabs/activeFile）
2. `vscode-ide-companion` 响应 `ide.getContext()` RPC
3. Prompt `@` 补全新增 pseudo-paths：`@selection` / `@cursor` / `@diagnostics` / `@tabs` / `@active-file`
4. 输入 `@selection` 自动注入当前选中代码 + 语义 tag `<editor-selection file="..." range="L10-L20">`

**实现成本**：~1 周（1 人）—— Schema + RPC + autocomplete 多处协同。

**意义**：**IDE ↔ CLI 的语义桥**——把编辑器原生概念（selection / cursor / diagnostic）暴露给 agent，让 prompt 简洁准确。
**改进收益**：
- **改进前**：用户复制整个文件 + 描述"第 50 行到 80 行这段"→ token 浪费 + 易搞错行号
- **改进后**：`@selection` 自动把选中代码 + 文件路径 + 行号 + 语义标签一起发给 agent

---

## 模块级架构差异

### OpenCode 独有模块（Qwen Code 无对应）

| 模块 | 规模 | 功能 | backport 建议 |
|------|:----:|------|:------------:|
| `provider/` | 7,927 行 | 25+ LLM Provider 动态插件 | P1 |
| `plugin/` | 2,594 行 | 18 种 Hook + npm 插件加载 | P1 |
| `lsp/` | 2,919 行 | 多语言 Language Server 客户端 | P2 |
| `acp/` | 1,987 行 | Agent Client Protocol 服务端 | P2 |
| `snapshot/` | 726 行 | Git 隔离快照 + 回滚 | P1 |
| `worktree/` | 612 行 | 增强 Worktree 管理 | P1 |
| `format/` | 616 行 | 可插拔代码格式化 | P3 |
| `permission/` | 520 行 | 规则驱动权限引擎 | P2 |
| `pty/` | 492 行 | PTY + WebSocket 多路复用 | P2 |
| `skill/` | 393 行 | 多路径 Skill 发现 | P2 |
| `share/` | 382 行 | 会话分享/导出 | P2 |
| `control-plane/` | 362 行 | 多工作区管理 | P2 |
| `sync/` | 293 行 | Event Sourcing 事件溯源 | P2 |
| `npm/` | 188 行 | 动态包安装 | P2 |

### Qwen Code 独有能力（OpenCode 无对应）

| 能力 | 说明 |
|------|------|
| **Agent Arena** | 多模型并行竞赛评估 |
| **免费 OAuth** | 1000 次/天免费额度 |
| **Gemini CLI 兼容** | fork 自 Gemini CLI，共享上游改进 |
| **扩展格式转换** | Claude/Gemini 扩展自动转换 |
| **多渠道部署** | DingTalk/Telegram/WeChat/Web |
| **6 语言 i18n** | 中/英/日/韩/法/德 |
| **Doom Loop 双重检测** | 工具 5 次 + 内容 10 次 |

### 核心差异总结

| 维度 | OpenCode | Qwen Code | 评估 |
|------|---------|-----------|------|
| **代码规模** | 74,418 行 373 文件 | ~50,000 行 ~500 文件 | 相当 |
| **Provider 数** | 25+ 动态加载 | 3-4 硬编码 | OpenCode 领先 |
| **插件生态** | npm 包分发 + 18 Hook | 内置 Hook ~10 种 | OpenCode 领先 |
| **持久化** | SQLite + Event Sourcing | JSONL | OpenCode 领先 |
| **多客户端** | TUI + Web + Desktop + Electron | CLI + Web + IDE | 相当 |
| **会话管理** | Snapshot + Revert + Share | 基础 resume | OpenCode 领先 |
| **多模型竞赛** | 无 | Arena | **Qwen Code 领先** |
| **多渠道** | 无 | DingTalk/Telegram/WeChat | **Qwen Code 领先** |
| **国际化** | 仅英文 | 6 语言 | **Qwen Code 领先** |

## 实施路线图

| 阶段 | 时间 | 内容 | 预期效果 |
|------|------|------|---------|
| **第一周** | 1 天 | FileTime 文件时间锁（#1） | 防止数据丢失 |
| | 3 天 | Snapshot 快照（#11）+ Worktree 增强（#14） | 会话回滚 + 并行开发 |
| **第二周** | 5 天 | apply_patch + MultiEdit + Batch（#2/#3/#7） | 多模型编辑能力 |
| **第三至四周** | 2 周 | Provider 系统（#12） | 25+ 模型支持 |
| **第五至六周** | 2 周 | Plugin 系统（#13） | 生态扩展能力 |
| **第七至八周** | 2 周 | SQLite（#5）+ ACP（#15） | 持久化 + API 服务 |
| **后续** | 按需 | LSP / PTY / Share / Control-Plane 等 | 平台进化 |

## 更新日志

### 2026-04-24（OpenCode 上游 `git pull` · 新增 2 项）

**OpenCode 源码扫描**：`2026-04-10 → 2026-04-24` 间 60+ commit（含大量 Effect Schema 迁移）。识别出 **2 项新可借鉴能力**。

#### 新增 2 项

| # | 功能 | 关键 PR | 合并日期 |
|---|---|---|---|
| [item-28](#item-28) | 可配置工具输出截断限制 | [#23770](https://github.com/sst/opencode/pull/23770) | 2026-04-23 |
| [item-29](#item-29) | TUI 编辑器上下文 builtin protocol | [#24034](https://github.com/sst/opencode/pull/24034) | 2026-04-23 |

#### 值得提及但未单列 item 的 OpenCode 变更

| PR | 方向 | 为什么不单列 |
|---|---|---|
| [#23244](https://github.com/sst/opencode/pull/23244) `migrate 18 built-in tools to Effect Schema` + 后续 PR 栈 | 大规模 Effect Schema 迁移 | item-27 已覆盖；Qwen 对标价值低（zod/valibot 更轻） |
| [#23771](https://github.com/sst/opencode/pull/23771) `support pull diagnostics in the LSP client (C#, Kotlin, etc)` | LSP pull diagnostics 协议 | item-16 LSP 已赶超（Qwen 7,422 行），作为 item-16 内部 refinement 方向记录 |
| [#23870](https://github.com/sst/opencode/pull/23870) `improve session compaction` | 压缩改进（198 行 + 279 行 test） | Qwen 压缩已经更分层（参考 Claude 对比 p0-p1-core item-1），对标价值低 |
| [#23797](https://github.com/sst/opencode/pull/23797) `preserve BOM in text tool round-trips` | BOM 保留 | 细节修复，可在 Qwen 文本工具做等价 check |
| [#19054](https://github.com/sst/opencode/pull/19054) `use git common dir for bare repo project cache` | bare repo 支持 | 小众场景，不单列 |
| [#24062](https://github.com/sst/opencode/pull/24062) `bridge workspace read endpoints` | 工作区 HTTP API | 已在 item-8 HTTP 服务器覆盖 |
| [#14471](https://github.com/sst/opencode/pull/14471) `beta badge for desktop app` | 桌面 app UI 改动 | Qwen 无桌面 app |

---

### 2026-04-16

**全量核对**：`git pull` 刷新两侧源码后逐项验证 27 项。OpenCode 437 文件 / 78,174 行（原 373 / 74,418，增长 ~5%），Qwen Code 282,115 行。

- **4 项标记 ✅ 已赶超**：
  - **item-13 Plugin/Hook**：Qwen Code hook 系统 17,443 行 vs OpenCode plugin 2,618 行（**6.7× 反超**），但 Qwen Code 是 config 注册，OpenCode 是 npm 分发——标记 ⚠️ 部分赶超
  - **item-14 Worktree**：Qwen Code `gitWorktreeService.ts` 826 行 vs OpenCode 612 行（**1.3× 超过**），核心功能已对齐
  - **item-16 LSP**：Qwen Code LSP 7,422 行 vs OpenCode 2,919 行（**2.5× 超过**），含 NativeLspService / LspServerManager / LspConfigLoader / LspConnectionFactory / LspLanguageDetector
  - **item-20 Skill**：Qwen Code skills 2,673 行 vs OpenCode 393 行（**6.8× 超过**），含 skill-load / skill-manager / 内置 /review + PR#2949 model 覆盖
- **其他 23 项状态确认为"准确"**——差距不变
- **修正代码量**：报告头 74,418 → 78,174 行、373 → 437 文件；引用 253 项 → 251 项

### 2026-04-09

- 扩充报告从 10 项到 27 项（+17 项新发现）
- 新增模块级架构差异对比（OpenCode 14 独有模块 vs Qwen Code 7 独有能力）
- 新增实施路线图（8 周阶段规划）
- 扩展 Qwen Code 独有优势（+多渠道、Gemini CLI 兼容）
- 更新相关报告引用（248 项、53 项）

### 2026-04-05

- 初始版本：10 项改进建议

---

*分析基于 OpenCode (anomalyco/opencode v1.3.0, 74,418 行) 和 Qwen Code 源码，截至 2026 年 4 月。*
