# Qwen Code 改进建议 — 对标 OpenCode

> 基于 OpenCode (anomalyco/opencode v1.3.0) 源码逐项比对，识别 Qwen Code 可借鉴的能力
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md)

---

## 改进项索引

| # | 功能 | 优先级 | 工作量 | 来源文件 |
|:-:|------|:------:|:------:|----------|
| [1](#item-1) | 文件时间锁（外部修改检测） | **P0** | 1 天 | `file/time.ts` |
| [2](#item-2) | apply_patch 工具（GPT 模型适配） | **P1** | 3 天 | `tool/apply_patch.ts` |
| [3](#item-3) | MultiEdit 工具（单文件批量编辑） | **P1** | 1 天 | `tool/multiedit.ts` |
| [4](#item-4) | Session 分叉与回退 | **P1** | 5 天 | `session/revert.ts` |
| [5](#item-5) | SQLite 持久化 | **P1** | 2 周 | `session/session.sql.ts` |
| [6](#item-6) | 语义代码搜索（Exa） | **P1** | 2 天 | `tool/codesearch.ts` |
| [7](#item-7) | Batch 工具（并行工具调用） | **P2** | 3 天 | `tool/batch.ts` |
| [8](#item-8) | HTTP 服务器（多客户端架构） | **P2** | 3 周 | `server/server.ts` |
| [9](#item-9) | Instance 上下文隔离 | **P2** | 3 天 | `server/instance.ts` |
| [10](#item-10) | MDNS 服务发现 | **P3** | 1 天 | `server/mdns.ts` |

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
| `tool/apply_patch.ts` (~230行) | `ApplyPatchTool.execute()`、hunk 解析、验证-提交分离、LSP 集成 |
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
| `session/revert.ts` (~130行) | `SessionRevert.revert()`、`unrevert()`、`cleanup()`、git snapshot 集成 |
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

**OpenCode 的解决方案——SQLite + Drizzle ORM**：

OpenCode 使用 SQLite（WAL 模式）+ Drizzle ORM，设计了关系型 schema：

| 表 | 主要字段 | 用途 |
|----|---------|------|
| `session` | id, project_id, workspace_id, parent_id, title, version, revert, permission | 会话元数据 + 分叉支持 |
| `message` | id, session_id, data(JSON) | 消息信息（role/model/token 统计） |
| `part` | id, message_id, session_id, data(JSON) | 消息部件（text/tool/patch/image 等） |
| `todo` | session_id, content, status, priority, position | 待办事项（per-session） |
| `permission` | project_id, data(JSON) | 权限规则集（per-project） |

**关键设计细节**：

- **WAL 模式**：Write-Ahead Logging 允许读写并发——多个客户端可同时读取会话，写入不阻塞读取
- **级联删除**：`onDelete: "cascade"` 确保删除 session 时自动删除关联的 message、part、todo
- **索引优化**：`session_project_idx`、`message_session_time_created_id_idx`、`part_message_id_id_idx` 等索引加速常见查询
- **JSON 列**：`data` 列使用 `text({ mode: "json" })` 存储结构化数据——兼顾灵活性和查询能力
- **Drizzle ORM**：类型安全的查询构建器 + 自动迁移（`drizzle-kit`）
- **Timestamps**：所有表继承 `Timestamps` mixin（`time_created`、`time_updated`）

**OpenCode 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `session/session.sql.ts` (~85行) | `SessionTable`、`MessageTable`、`PartTable`、`TodoTable`、`PermissionTable` |
| `storage/storage.ts` | 通用 KV 存储（SQLite 后端） |
| `storage/schema.sql.ts` | `Timestamps` mixin、其他表定义 |

**Qwen Code 现状**：JSONL 追加写入。加载会话需读取整个文件并逐行解析。无索引——搜索历史会话只能全量扫描。无并发安全——理论上多进程写入同一 JSONL 可能数据损坏。

**Qwen Code 修改方向**：

```
① 引入 better-sqlite3（或 drizzle-orm + better-sqlite3）
   - WAL 模式 + 关系型 schema
   - Session/Message/Part 三表设计

② 迁移工具
   - 扫描现有 JSONL 文件 → 导入 SQLite
   - 保留 JSONL 导出能力（用于备份/迁移）

③ 查询接口
   - 按时间范围加载消息（分页）
   - 全文搜索（SQLite FTS5 扩展）
   - 按项目/目录过滤会话

④ 并发安全
   - WAL 模式 + 单写锁（better-sqlite3 天然支持）
```

**实现成本评估**：
- 涉及文件：~10 个
- 新增代码：~500 行（schema + 迁移 + 查询接口）
- 开发周期：~2 周（1 人）
- 难点：JSONL → SQLite 迁移的兼容性；better-sqlite3 的跨平台编译

**意义**：会话存储是 CLI Agent 的基础设施——影响启动速度、历史搜索、并发安全。
**缺失后果**：大会话加载慢（10MB JSONL 全量读取）、无法搜索历史、分叉/回退功能缺乏持久化基础。
**改进收益**：毫秒级会话加载 + 全文搜索 + 为 session 分叉/HTTP 服务器提供数据基础。

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
| `server/server.ts` (~250行) | `Server.listen()`、`ControlPlaneRoutes()`、Hono app 配置 |
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

---

## 一句话总结

**1 个 P0（1 天）**：文件时间锁——防止 Agent 覆盖用户在 IDE 中的修改。

**5 个 P1（~2 周 + 2 周 SQLite）**：apply_patch 提升多模型编辑准确性 + MultiEdit 5x 编辑速度 + Session 分叉支持多方案探索 + SQLite 奠定数据基础 + 语义代码搜索提升 API 理解。

**P2/P3 是平台进化方向**：HTTP 服务器 → Web UI → 桌面应用 → 从 CLI 工具进化为开发平台。不急，但方向明确。

---

*分析基于 OpenCode (anomalyco/opencode v1.3.0) 和 Qwen Code 源码，截至 2026 年 4 月。*
