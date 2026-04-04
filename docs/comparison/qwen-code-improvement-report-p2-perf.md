# Qwen Code 改进建议 — P2 性能优化

> 中等优先级改进项。每项包含：问题场景、现状分析、改进前后对比、实现成本评估、Claude Code 源码索引、Qwen Code 修改方向。
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md)

---

<a id="item-1"></a>

### 1. MCP 并行连接 — 动态插槽调度 + 双层并发（P2）

**问题**：企业环境通常配置 10+ MCP 服务器（数据库、搜索、CI/CD 等）。启动时如果同时 spawn 全部 stdio 服务器，会瞬间耗尽进程资源（类似 fork bomb）。如果改为固定批次顺序启动，一个响应慢的服务器会阻塞整批——10 个服务器中只要 1 个慢，所有人都在等。开发者感受到的就是"Agent 启动要等 10 秒"。

**Claude Code 的解决方案**：MCP 服务器分两组并行初始化——本地（stdio/sdk，并发 3）和远程（sse/http/ws，并发 20），`Promise.all()` 同时启动两组。关键优化：用 `pMap` 动态插槽调度替代固定批次——一个慢服务器只占一个插槽，不阻塞整批。工具/命令/资源获取也并行（`Promise.all([fetchTools, fetchCommands, fetchResources])`）。LRU 缓存（20 条）避免重复获取。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `services/mcp/client.ts` (L2226-2403) | `getMcpToolsCommandsAndResources()` 双组并行、`processBatched()` pMap 动态调度 |
| `services/mcp/client.ts` (L552-560) | `getMcpServerConnectionBatchSize() = 3`、`getRemoteMcpServerConnectionBatchSize() = 20` |
| `services/mcp/client.ts` (L2171-2178) | `Promise.all([fetchTools, fetchCommands, fetchSkills, fetchResources])` |
| `services/mcp/client.ts` (L1726) | `MCP_FETCH_CACHE_SIZE = 20` LRU 缓存 |
| `services/mcp/client.ts` (L595) | `connectToServer = memoize(...)` 连接记忆化 |

**Qwen Code 现状**：`mcp-client-manager.ts` 已用 `Promise.all(discoveryPromises)` 并行初始化，但无并发上限控制——10 个 stdio 服务器同时 spawn 可能耗尽进程资源。无工具/资源并行获取，无 LRU 缓存。

**Qwen Code 修改方向**：① `McpClientManager.initializeAllClients()` 分 local/remote 两组，用 `p-limit` 控制并发上限（local:3, remote:20）；② `McpClient.discover()` 内部用 `Promise.all([tools, commands, resources])` 并行获取；③ 工具列表加 LRU 缓存，reconnect 时清除。

**实现成本评估**：
- 涉及文件：~3 个
- 新增代码：~150 行
- 开发周期：~2 天（1 人）
- 难点：动态插槽调度逻辑与错误隔离（一个服务器失败不影响其他）

**改进前后对比**：
- **改进前**：10 个 MCP 服务器同时 spawn，无并发控制，1 个慢服务器阻塞整批，工具列表每次重新获取
- **改进后**：local/remote 分组 + 动态插槽并发控制，慢服务器只占 1 个槽位，工具列表 LRU 缓存复用

**意义**：企业环境配置 10+ MCP 服务器——启动时全部 spawn 可能 fork bomb。
**缺失后果**：无并发限制 = 进程资源争抢；固定批次 = 一个慢服务器阻塞整批。
**改进收益**：动态插槽 + 双层并发——启动快且资源可控；LRU 缓存避免重复获取。

---

<a id="item-2"></a>

### 2. 插件/Skill 并行加载与启动缓存（P2）

**问题**：开发者安装了 10+ 插件/Skill（代码生成、lint 检查、测试框架等），Agent 启动时逐个顺序加载——每个 50ms，10 个就是 500ms。更糟的是 `/reload` 时即使只改了 1 个插件也全部重新加载。开发者感受到"装的插件越多启动越慢"。

**Claude Code 的解决方案**：3 层并行——① marketplace 插件 + session 插件 `Promise.all()` 并行加载；② 每个插件内部 commands/agents/hooks 目录存在检查 `Promise.all([pathExists(commandsDir), pathExists(agentsDir), pathExists(hooksDir)])`；③ 加载结果缓存，热重载时仅增量更新变更的插件。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/plugins/pluginLoader.ts` (L3165) | `Promise.all([marketplaceResult, sessionResult])` 双源并行 |
| `utils/plugins/pluginLoader.ts` (L1374-1386) | `Promise.all([commandsDirExists, agentsDirExists, skillsDirExists, outputStylesDirExists])` 4 目录检查并行 |
| `utils/plugins/pluginLoader.ts` (L1962) | `Promise.allSettled(plugins.map(...))` marketplace 并行加载 |

**Qwen Code 现状**：`skill-manager.ts` 用 `for` 循环顺序扫描 skill 目录 + 顺序读取 manifest 文件；`extensionManager.ts` 顺序加载 MCP/skills/subagents/hooks。

**Qwen Code 修改方向**：① `loadSkillsFromDir()` 改为 `Promise.all(entries.map(readManifest))`；② `extensionManager.ts` 中 MCP 初始化与 skill/hook 加载 `Promise.all()` 并行（无依赖关系）；③ 加载结果存入 Map 缓存，`/reload` 时仅重新加载变更的插件。

**实现成本评估**：
- 涉及文件：~3 个
- 新增代码：~100 行
- 开发周期：~1 天（1 人）
- 难点：增量热重载的变更检测（对比 mtime 或内容 hash）

**改进前后对比**：
- **改进前**：10 个插件顺序加载 = 500ms 启动延迟，`/reload` 全量重载
- **改进后**：并行加载 = ~50ms（取决于最慢的一个），`/reload` 仅增量更新变更插件

**意义**：用户安装 10+ 插件后启动时间线性增长——并行加载控制在常数时间。
**缺失后果**：10 个插件 × 50ms/插件 = 500ms 启动延迟（顺序加载）。
**改进收益**：并行加载 = ~50ms（最慢的一个）；缓存 = 热重载几乎免费。

---

<a id="item-3"></a>

### 3. Speculation 流水线建议（Pipelined Suggestions）（P2）

**问题**：开发者使用 Speculation（投机建议）时，按 Tab 接受一个建议后需要等 1-2 秒才能看到下一个建议。这个"空白间隙"打破了用户的"心流"——本应是连续 Tab-Tab-Tab 的自动驾驶体验，变成了 Tab-等-Tab-等的断断续续。

**Claude Code 的解决方案**：当前 speculation 执行完成后，**立即并行生成下一个建议**（pipelined suggestion）。用户接受当前建议时，下一个建议已经准备好——连续 Tab 接受零延迟。投机结果作为上下文传给下一轮建议生成，确保连贯性。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `services/PromptSuggestion/speculation.ts` (L345-400) | `generatePipelinedSuggestion()` 并行生成下一建议 |
| `services/PromptSuggestion/speculation.ts` (L672-679) | speculation 完成后触发 pipelined generation |
| `services/PromptSuggestion/speculation.ts` (L928-955) | 接受建议时提升 pipelined suggestion |

**Qwen Code 现状**：speculation 已实现（PR#2525），但每次接受建议后需重新生成下一建议——间有 1-2 秒空白等待。

**Qwen Code 修改方向**：speculation 完成回调中立即调用 `generateNextSuggestion()`，将投机结果 + 新消息传入作为上下文；`state.pipelinedSuggestion` 存储预生成的建议；接受时直接提升，无需等待。

**实现成本评估**：
- 涉及文件：~2 个
- 新增代码：~120 行
- 开发周期：~2 天（1 人）
- 难点：流水线取消逻辑（用户修改输入时需丢弃已预生成的建议）

**改进前后对比**：
- **改进前**：Tab 接受建议 → 等待 1-2 秒 → 生成下一建议 → 显示，体验断续
- **改进后**：Tab 接受建议 → 下一建议已预生成立即显示 → 连续 Tab 零延迟

**意义**：Speculation 的价值在于连续流——中间有停顿会打破用户"心流"。
**缺失后果**：每次 Tab 接受后等 1-2 秒才出现下一建议——体验不够连贯。
**改进收益**：流水线预生成——连续 Tab 零延迟，真正的"自动驾驶"体验。

---

<a id="item-4"></a>

### 4. write-through缓存与 TTL 后台刷新（P2）

**问题**：MCP 工具列表、Git 状态、环境检测这类数据被频繁访问（每轮对话 2-5 次），但实际变化很慢（几分钟甚至几小时才变一次）。每次都重新 fetch 浪费 10-50ms。更糟的是缓存过期时如果同步刷新，用户会感受到一次明显卡顿。

**Claude Code 的解决方案**：`memoizeWithTTL` 实现 stale-while-revalidate 模式——缓存过期后**立即返回旧值**，同时后台异步刷新。防止多个并发请求同时触发刷新（`refreshing` 标志位）。`memoizeWithLRU` 提供有界缓存（默认 100 条），防止内存无限增长。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/memoize.ts` (L40-100) | `memoizeWithTTL()` write-through + background refresh、`cacheLifetimeMs = 5min` |
| `utils/memoize.ts` (L234-269) | `memoizeWithLRU()` LRU 有界缓存、`LRUCache` 封装 |
| `services/mcp/client.ts` (L595) | `connectToServer = memoize(...)` 连接缓存 |
| `services/mcp/client.ts` (L1743) | `fetchToolsForClient = memoizeWithLRU(...)` 工具列表 LRU |

**Qwen Code 现状**：`filesearch/result-cache.ts` 有搜索结果缓存；`crawlCache.ts` 有爬取缓存；但无通用 stale-while-revalidate 模式。MCP 工具列表每次重新获取。

**Qwen Code 修改方向**：① 新建 `utils/memoize.ts` 实现 `memoizeWithTTL`（过期返旧值 + 后台刷新）+ `memoizeWithLRU`（有界缓存）；② MCP 工具列表包装为 `memoizeWithLRU`；③ Git 状态检测包装为 `memoizeWithTTL(5min)`。

**实现成本评估**：
- 涉及文件：~4 个
- 新增代码：~200 行
- 开发周期：~2 天（1 人）
- 难点：stale-while-revalidate 的并发刷新去重（防止多个 caller 同时触发后台刷新）

**改进前后对比**：
- **改进前**：每次查询 MCP 工具列表/Git 状态都触发完整 fetch（10-50ms），缓存过期时同步阻塞
- **改进后**：缓存命中 = 0ms 立即返回，过期后返回旧值 + 后台静默刷新，用户零等待

**意义**：MCP 工具列表、Git 状态等热点数据——每次 fetch 浪费 10-50ms。
**缺失后果**：每次查询触发完整 fetch——高频路径累积延迟显著。
**改进收益**：缓存命中 = 0ms + 后台静默刷新——用户永远不等待过期数据。

---

<a id="item-5"></a>

### 5. 上下文收集并行化（P2）

**问题**：每轮对话前 Agent 需要收集 5-10 种上下文（文件内容、图片、MCP 资源、诊断信息、LSP 数据等）。如果串行收集，每种来源 20ms，10 种就是 200ms——用户按回车后要等近 200ms 才开始 API 调用。这个延迟在每一轮对话中都存在，累积起来非常显著。

**Claude Code 的解决方案**：分两阶段并行收集——① 用户输入附件先完成（可能触发嵌套记忆加载）；② 线程附件 + 主线程附件 `Promise.all()` 并行处理，~20+ 并发计算。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/attachments.ts` (L819) | `Promise.all(userInputAttachments)` 用户附件并行 |
| `utils/attachments.ts` (L990-994) | `Promise.all([Promise.all(threadAttachments), Promise.all(mainThreadAttachments)])` 双阶段并行 |

**Qwen Code 现状**：上下文通过 `appendAdditionalContext()` 串行追加；hook 输出通过 `hookRunner.ts` 可并行但上下文收集本身是顺序的。

**Qwen Code 修改方向**：抽取上下文收集为独立函数；文件内容、MCP 资源、诊断信息等无依赖项用 `Promise.all()` 并行获取；有依赖项（如记忆触发嵌套加载）按拓扑顺序处理。

**实现成本评估**：
- 涉及文件：~3 个
- 新增代码：~100 行
- 开发周期：~2 天（1 人）
- 难点：识别上下文来源之间的依赖关系（记忆加载依赖文件路径解析）

**改进前后对比**：
- **改进前**：10 种上下文来源串行收集 = 200ms 等待（每轮对话都有）
- **改进后**：无依赖项并行收集 = ~20ms（取决于最慢的来源），每轮省 150-180ms

**意义**：每轮对话的上下文收集涉及 5-10 种来源——串行 = 延迟叠加。
**缺失后果**：10 种上下文来源 × 20ms = 200ms 串行等待。
**改进收益**：并行收集 = ~20ms（最慢的一个来源）——每轮省 150-180ms。

---

<a id="item-6"></a>

### 6. 输出缓冲与防阻塞渲染（P2）

**问题**：开发者在运行 Agent 时偶尔遇到"键盘输入没反应"或"渲染卡住一下"。原因是 Node.js 单线程模型下，`writeFileSync`（写日志、PID 文件）或大量 shell 输出推送阻塞了事件循环——磁盘 I/O 慢时主线程被卡住，键盘事件和渲染帧都无法处理。

**Claude Code 的解决方案**：`createBufferedWriter` 在写入目标可能阻塞时，将输出缓冲到内存队列。溢出时用 `setImmediate` 延迟写入——当前 tick 不阻塞，保证键盘响应和渲染帧率。参数可调：`flushIntervalMs`（默认 1s）、`maxBufferSize`（默认 100 条）、`maxBufferBytes`。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/bufferedWriter.ts` | `createBufferedWriter()`、`flushDeferred()` setImmediate 延迟、`pendingOverflow` 排序保证 |

**Qwen Code 现状**：`pidfile.ts` 用 `writeFileSync` 写 PID 文件；`trustedFolders.ts` 用 `readFileSync`/`writeFileSync`；`shellExecutionService.ts` 输出直接推送——长输出可能阻塞渲染。

**Qwen Code 修改方向**：① 新建 `utils/bufferedWriter.ts`——内存缓冲 + 定时 flush + 溢出 `setImmediate`；② 同步写入 hot path 改用 `bufferedWriter.write()`；③ shell 输出推送改用 buffered writer（`maxBufferBytes` 限制内存占用）。

**实现成本评估**：
- 涉及文件：~4 个
- 新增代码：~150 行
- 开发周期：~2 天（1 人）
- 难点：溢出时的写入顺序保证（`pendingOverflow` 队列排序）

**改进前后对比**：
- **改进前**：同步 I/O 阻塞主线程，磁盘慢时键盘输入延迟、渲染卡顿
- **改进后**：内存缓冲 + setImmediate 延迟写入，主线程永不阻塞，UI 始终流畅

**意义**：同步写入和大量输出推送可能阻塞 Node.js 事件循环——导致 UI 卡顿和键盘无响应。
**缺失后果**：同步 I/O 在磁盘慢时阻塞主线程——用户输入延迟。
**改进收益**：缓冲 + 延迟写入——主线程永不阻塞，UI 始终流畅。

---

<a id="item-7"></a>

### 7. LSP 服务器并行启动/关闭（P2）

**问题**：多语言项目（如 TypeScript + Python + Go）配置 3-5 个 LSP 服务器。当前顺序启动——每个 500ms，3 个就是 1.5 秒。关闭时更糟：如果一个 LSP 挂住，后续的都无法关闭。开发者感受到"退出 Agent 要等好几秒"。

**Claude Code 的解决方案**：多个 LSP 服务器相互独立，启动和关闭 `Promise.all()` 并行。端口探测用 `Promise.race()` 并行尝试——首个成功连接即返回。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `services/lsp/` (7 文件) | LSP 客户端管理——多服务器独立启动 |

**Qwen Code 现状**：`LspServerManager.ts` 的 `startAll()` 和 `stopAll()` 用 `for` 循环顺序启动/关闭每个服务器（L81-92）。`LspConfigLoader.ts` 用 `readFileSync` 顺序读取配置文件。

**Qwen Code 修改方向**：① `startAll()` 改为 `Promise.all(servers.map(s => this.startServer(s)))` 并行启动；② `stopAll()` 改为 `Promise.allSettled()` 确保全部关闭（一个失败不影响其他）；③ 端口探测用 `Promise.race()` 并行尝试多个端口。

**实现成本评估**：
- 涉及文件：~2 个
- 新增代码：~50 行
- 开发周期：~1 天（1 人）
- 难点：`Promise.allSettled` 的错误收集与报告（需要汇总哪些 LSP 启动/关闭失败）

**改进前后对比**：
- **改进前**：3 个 LSP 顺序启动 = 1.5s，关闭时 1 个挂住阻塞其他
- **改进后**：并行启动 = ~500ms（最慢的一个），`Promise.allSettled` 确保全部关闭不互相阻塞

**意义**：多语言项目配置 3-5 个 LSP——顺序启动延迟线性叠加。
**缺失后果**：3 个 LSP × 500ms/个 = 1.5s 启动延迟（顺序）。
**改进收益**：并行启动 = ~500ms（最慢的一个）；端口探测首个成功即返回。

---

<a id="item-8"></a>

### 8. 请求合并与去重（Request Coalescing）（P2）

**问题**：开发者保存 10 个文件（如 format-on-save），每次保存都触发 MCP 工具列表刷新、lint 检查、状态上报——结果是 10 次完全相同的网络请求和 I/O 操作。API 认证失败时更严重：5 个并发请求同时收到 401，每个都去读 keychain——macOS 上读一次 800ms，5 次 = 4 秒。

**Claude Code 的解决方案**：3 种请求合并模式——① PUT 合并（1 in-flight + 1 pending，新请求合并到 pending）；② 401 去重（同 token 的多个 401 只触发一次 keychain 读取）；③ UUID 去重（BoundedUUIDSet 环形缓冲区 O(1) 查重）。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `cli/transports/WorkerStateUploader.ts` (131行) | 1 in-flight + 1 pending slot、RFC 7396 patch 合并 |
| `utils/auth.ts` (L1343) | `pending401Handlers: Map<token, Promise>` 防止 N 个 401 并发读 keychain（省 800ms+） |
| `bridge/bridgeMessaging.ts` (L429-459) | `BoundedUUIDSet` 环形缓冲区（cap=2000）O(1) 去重 |
| `utils/memoize.ts` (L125-162) | `inFlight` Map 防止 N 个 cold-miss 并发调用同一函数 |

**Qwen Code 现状**：无通用请求合并机制；MCP 工具列表每次 reconnect 全量重新获取；无认证去重。

**Qwen Code 修改方向**：① 新建 `utils/requestCoalescer.ts`——通用 1-in-flight + 1-pending 合并器；② MCP 工具刷新包装为 coalescer（多个 reconnect 事件合并）；③ API 认证失败处理加 inFlight 去重。

**实现成本评估**：
- 涉及文件：~4 个
- 新增代码：~200 行
- 开发周期：~2 天（1 人）
- 难点：通用合并器的 API 设计（需支持 PUT 合并、Promise 去重、UUID 去重三种模式）

**改进前后对比**：
- **改进前**：10 次文件保存 → 10 次 MCP 刷新 + 10 次 lint；401 错误 → N 次并发 keychain 读取
- **改进后**：10 次文件保存 → 1 次合并后的 MCP 刷新；401 错误 → 1 次 keychain 读取，其他等待结果

**意义**：高频事件（文件保存触发 lint + format + refresh）产生重复请求——合并后只执行一次。
**缺失后果**：10 个文件保存 → 10 次 MCP 工具列表刷新 → 10× 不必要 I/O。
**改进收益**：请求合并 = 1 次实际执行——消除 90% 重复操作。

---

<a id="item-9"></a>

### 9. 延迟初始化与按需加载（Lazy Init）（P2）

**问题**：开发者启动 Agent 时感觉"要等一两秒才能输入"。根本原因是启动时同步加载了所有模块（包括 113KB 的 insights.ts 等大模块）、构建了所有 Zod schema、预取了所有远程配置——但实际上 90% 的模块在第一次交互时根本不需要。cold start 慢 200-500ms。

**Claude Code 的解决方案**：3 层延迟策略——① `lazySchema()`：Zod schema 定义推迟到首次使用时构建（启动不触发 Zod）；② 延迟模块导入：大模块在命令执行时 `import()` 而非启动时 `require`；③ 延迟 prefetch（`startDeferredPrefetches`）：AWS/GCP 凭证、MCP 官方 URL 等在首帧渲染后才开始。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/lazySchema.ts` (8行) | `lazySchema(factory)` 缓存式惰构建 |
| `commands.ts` (L188) | 113KB insights.ts 延迟导入 |
| `main.tsx` (L383-418) | `startDeferredPrefetches()` 首帧后 prefetch |
| `Tool.ts` (L439-442) | `shouldDefer` 属性（对应 `defer_loading`）工具延迟加载到 prompt |

**Qwen Code 现状**：所有模块启动时同步加载；Zod schema 在模块求值时构建；所有工具定义启动时全量生成。

**Qwen Code 修改方向**：① 大型命令模块改为 `await import()` 动态导入；② 工具 Zod schema 包装为 `lazySchema()`——首次调用时才构建；③ 非关键 prefetch（凭证、远程配置）推迟到首帧渲染后。

**实现成本评估**：
- 涉及文件：~6 个
- 新增代码：~100 行
- 开发周期：~2 天（1 人）
- 难点：识别哪些模块可以安全延迟加载（需梳理启动依赖图）

**改进前后对比**：
- **改进前**：启动时同步加载全量模块 + 构建全量 schema + 预取全部远程配置 = cold start 200-500ms
- **改进后**：仅加载核心模块，schema/大模块首次使用时才加载，prefetch 延迟到首帧后 = 启动缩短 30-50%

**意义**：启动时间 = 所有模块加载时间之和——延迟非关键模块直接缩短启动。
**缺失后果**：启动加载全量模块 + 全量 schema 构建——cold start 慢 200-500ms。
**改进收益**：惰加载 = 仅加载核心模块——启动时间缩短 30-50%。

---

<a id="item-10"></a>

### 10. 流式超时检测与级联取消（P2）

**问题**：开发者遇到过两个痛点：① API 流式响应偶尔 hang（网络问题或服务端异常），进度条不动但没有超时——只能手动 Ctrl+C。② Agent 并行执行 Bash + Grep + FileRead 三个工具，Bash 已经报错了（比如命令不存在），但 Grep 和 FileRead 还在继续跑——浪费时间和 API token。

**Claude Code 的解决方案**：API 流式响应设置 90 秒空闲 watchdog——收到 chunk 时重置计时器，超时则 abort stream 触发重试。工具执行层面：子 AbortController 实现级联取消——Bash 工具出错时 `siblingAbortController.abort()` 立即终止同批次的其他子进程。`createChildAbortController()` 用 WeakRef 防止 GC 泄漏。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `services/api/claude.ts` (L1868-1954) | 90s 流式空闲 watchdog、stall 计数 + 时间统计 |
| `utils/abortController.ts` | `createChildAbortController()` WeakRef 子控制器 |
| `services/tools/StreamingToolExecutor.ts` (L45-48) | `siblingAbortController` Bash 错误级联 |
| `hooks/useTypeahead.tsx` (L206-217) | 每次击键取消上一次 shell 补全 |

**Qwen Code 现状**：API 流式超时使用全局固定超时（无空闲检测）；工具执行无级联取消——一个工具失败其他继续运行。

**Qwen Code 修改方向**：① API stream 处理添加空闲检测（每个 chunk 重置 timer，超时 abort + 重试）；② `coreToolScheduler.ts` 添加 `siblingAbortController`——写工具（Bash）失败时取消同批次其他工具；③ 输入补全/搜索添加 AbortController——新输入取消旧搜索。

**实现成本评估**：
- 涉及文件：~4 个
- 新增代码：~200 行
- 开发周期：~3 天（1 人）
- 难点：级联取消的粒度控制（只取消同批次兄弟工具，不终止整轮查询）

**改进前后对比**：
- **改进前**：API hang 时用户只能手动 Ctrl+C；Bash 报错后 Grep/FileRead 继续白跑
- **改进后**：空闲 90s 自动 abort + 重试；Bash 出错时自动级联取消同批次工具

**意义**：API 偶尔 hang——无超时检测则用户永远等待；工具失败不级联取消则浪费资源。
**缺失后果**：API hang = 用户手动 Ctrl+C；Bash 报错后 Grep 继续白跑。
**改进收益**：空闲 watchdog 自动重试 + 级联取消——异常恢复自动化，资源零浪费。

---

<a id="item-11"></a>

### 11. Git 文件系统直读避免进程 Spawn（P2）

**问题**：每次工具执行前后 Agent 都需要查询 git 状态（当前分支、是否有未提交更改等）。当前通过 `simple-git` 库每次 spawn 一个 `git` 子进程——10 次工具调用 × 2 次 git 查询 × 5ms/spawn = 100ms 纯进程 fork 开销。这些查询的结果（当前分支名、HEAD 指向）在短时间内几乎不变，完全可以避免。

**Claude Code 的解决方案**：频繁的 git 状态查询直接读取 `.git/HEAD` 和 `.git/refs/` 文件（0.1ms），无需 spawn 子进程。`git check-ignore` 用批量路径参数代替逐文件调用。`findGitRoot` 结果 LRU 缓存（max 50），避免每次 stat 向上遍历目录。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/git/gitFilesystem.ts` | 文件系统级 git 状态读取——避免 spawn git 子进程 |
| `tools/LSPTool/LSPTool.ts` (L554) | `git check-ignore` 批量路径参数 |
| `utils/git.ts` | `findGitRoot` LRU 记忆化（max 50）、`gitExe` 单例查找 |

**Qwen Code 现状**：`gitService.ts` 通过 `simple-git` 库调用 git 命令（每次 spawn 子进程）；无文件系统直读优化；无 git 操作 LRU 缓存。

**Qwen Code 修改方向**：① 高频查询（当前分支、HEAD 解析）直接读取 `.git/HEAD` + `.git/refs/`（async readFile，无 spawn）；② `git check-ignore` 合并为批量调用（一次传多个路径）；③ `findGitRoot` 结果 LRU 缓存（防止每次 stat 向上遍历）。

**实现成本评估**：
- 涉及文件：~3 个
- 新增代码：~150 行
- 开发周期：~2 天（1 人）
- 难点：处理 `.git/HEAD` 的各种格式（分离 HEAD、符号引用、packed-refs）

**改进前后对比**：
- **改进前**：每次 git 查询 spawn 子进程（~5ms），`check-ignore` 逐文件调用，`findGitRoot` 每次重新遍历
- **改进后**：直读 `.git/HEAD` = 0.1ms（无 fork），批量 `check-ignore` = 1 次替代 N 次，`findGitRoot` LRU 缓存

**意义**：git 状态查询是 hot path——每次工具执行前后都需检查。
**缺失后果**：10 次工具调用 × 2 次 git 查询 × 5ms/spawn = 100ms 开销。
**改进收益**：直读 .git/HEAD = 0.1ms（无 fork）；批量 check-ignore = 1 次 spawn 替代 N 次。

---

<a id="item-12"></a>

### 12. 设置/Schema 缓存与 Parse 去重（P2）

**问题**：每轮对话 Agent 都重新读取配置文件（`readFileSync` + `JSON.parse`）、重新生成工具 schema（~11K tokens）。但配置文件和工具定义在整个会话中几乎不变——这意味着每轮 10-50ms 的纯重复工作。50 轮对话累积 0.5-2.5 秒的无意义 I/O 和计算。

**Claude Code 的解决方案**：3 层设置缓存——① `sessionSettingsCache`：每 session 合并后的设置；② `perSourceCache`：按来源缓存（用户/项目/本地）；③ `parseFileCache`：路径级去重（同一文件只读一次 + Zod parse 一次）。Schema 缓存在首次渲染时锁定快照，防止特性开关翻转导致工具定义变化。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/settings/settingsCache.ts` | 3 层缓存：session/perSource/parseFile |
| `utils/toolSchemaCache.ts` (26行) | 首次渲染锁定 tool schema，防止 mid-session 抖动 |
| `utils/fileStateCache.ts` | `FileStateCache` LRU（max 100 条/25MB） |

**Qwen Code 现状**：`settings.ts` 每次调用重新读取 + 解析配置文件（`readFileSync` + JSON.parse）；工具 schema 每轮重新生成；无文件状态缓存。

**Qwen Code 修改方向**：① 设置加载结果缓存——文件 mtime 变化时才重新读取/解析；② 工具 schema 首次生成后缓存，MCP 工具变化时增量更新；③ 文件状态（内容 + 编码）LRU 缓存。

**实现成本评估**：
- 涉及文件：~4 个
- 新增代码：~200 行
- 开发周期：~2 天（1 人）
- 难点：缓存失效策略（mtime 检测 vs 文件 watcher vs 手动 invalidate）

**改进前后对比**：
- **改进前**：每轮重新 readFileSync + JSON.parse 配置文件，重新生成工具 schema = 10-50ms/轮
- **改进后**：缓存命中 = 0ms，仅在文件 mtime 变化或 MCP 工具变更时才重新加载

**意义**：设置文件和工具 schema 在会话中变化极少，但每轮都重新读取/生成。
**缺失后果**：每轮读配置 + parse + schema 生成 = 10-50ms 重复工作。
**改进收益**：缓存命中 = 0ms——消除 90%+ 的重复解析和生成。

---

<a id="item-13"></a>

### 13. cache_edits 增量缓存删除（P2）

**问题**：Agent 每 3-5 轮触发一次 Microcompact 清理旧工具结果。当前实现通过重建整个消息数组——但这会破坏 prompt cache，导致 ~20K tokens 需要重新编码。开发者感受到的是：压缩后下一轮的首 token 延迟突然翻倍（从 ~1 秒变成 ~2 秒），同时产生额外的缓存写入费用。

**Claude Code 的解决方案**：通过 API `cache_edits` 参数指定要删除的 `cache_reference`，服务端在缓存前缀上原地删除指定 block——缓存前缀不变，省去重新编码。`pinCacheEdits()` 追踪已发送的 edits 确保重发时不遗漏。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `services/compact/microCompact.ts` (L52-136) | `getPinnedCacheEdits()`、`consumePendingCacheEdits()`、`pinCacheEdits()` |
| `services/api/claude.ts` (L3108-3161) | cache_edits block 插入 + `cache_reference` 去重 |

**Qwen Code 现状**：压缩通过重新生成完整消息数组实现——每次压缩破坏缓存。

**Qwen Code 修改方向**：① 检测 API 是否支持 `cache_edits`（Anthropic API feature）；② 旧工具结果标记 `cache_reference = tool_use_id`；③ 清理时发送 `cache_edits: [{ type: 'delete', cache_reference }]` 而非重建消息。

**实现成本评估**：
- 涉及文件：~3 个
- 新增代码：~150 行
- 开发周期：~2 天（1 人）
- 难点：`cache_edits` 是 Anthropic API 特性，需确认 Qwen 后端 API 是否支持类似能力

**改进前后对比**：
- **改进前**：Microcompact 重建消息数组 → 缓存失效 → 首 token 延迟翻倍 + 缓存写入费用
- **改进后**：通过 `cache_edits` 原地删除 → 缓存前缀不变 → 压缩零延迟成本

**意义**：Microcompact 每 3-5 轮触发一次——每次破坏缓存 = 重新编码 20K+ tokens。
**缺失后果**：压缩 = 缓存失效 = 首 token 延迟翻倍 + 缓存写入费用。
**改进收益**：cache_edits = 缓存前缀不变——压缩零延迟成本。

---

<a id="item-14"></a>

### 14. 消息规范化与工具配对修复（P2）

**问题**：开发者在长对话中偶尔遇到 API 400 错误导致对话突然中断。原因是崩溃恢复、压缩后消息数组中出现了"孤立"的 tool_use（没有对应的 tool_result）或连续的 user 消息（API 要求 user/assistant 交替）。长对话中粘贴大量截图也会超出 API 的 100 个媒体项限制。

**Claude Code 的解决方案**：发送 API 前规范化消息数组——① 合并连续 user 消息；② 修复孤立 tool_use（注入合成错误结果 `[tool execution was interrupted]`）；③ 修复孤立 tool_result（移除）；④ 超出 100 个媒体项时裁剪最老的图片/文档；⑤ 规范化工具输入 JSON 格式。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/messages.ts` (L1989+) | `normalizeMessagesForAPI()` 合并 + 过滤 + thinking 合并 |
| `utils/messages.ts` (L1298-1301) | `ensureToolResultPairing()` 孤立 tool_use/result 修复 |
| `utils/messages.ts` (L1308-1315) | `stripExcessMediaItems()` 100 媒体项上限裁剪 |

**Qwen Code 现状**：`converter.ts` 在 Anthropic/OpenAI 间转换格式，`validateHistory()` 检查角色交替——但无配对修复和媒体裁剪。

**Qwen Code 修改方向**：① 合并连续同角色消息；② 检测孤立 tool_use → 注入 `[tool execution was interrupted]` 合成结果；③ 检测孤立 tool_result → 移除；④ 媒体项超 100 时裁剪最老的。

**实现成本评估**：
- 涉及文件：~2 个
- 新增代码：~200 行
- 开发周期：~2 天（1 人）
- 难点：正确识别孤立的 tool_use/tool_result 配对关系（需按 tool_use_id 匹配）

**改进前后对比**：
- **改进前**：崩溃恢复/压缩后消息不配对 → API 400 错误 → 对话中断，用户需手动新建会话
- **改进后**：发送前自动规范化消息数组 → API 永不因格式错误拒绝 → 对话不中断

**意义**：崩溃恢复、压缩后、长对话中容易出现消息不配对——API 会直接报错。
**缺失后果**：孤立 tool_use = API 400 错误 = 对话中断。
**改进收益**：自动配对修复 = API 永不因格式错误拒绝——对话不中断。

---

<a id="item-15"></a>

### 15. Git 状态与仓库上下文自动注入（P2）

**问题**：开发者让 Agent "提交代码"，但 Agent 不知道当前在哪个分支——可能建议直接 push 到 main。开发者让 Agent "清理代码"，但 Agent 不知道这是一个 50 万文件的 monorepo 还是 10 个文件的小项目——搜索策略完全不同。模型缺少项目上下文就会做出错误决策。

**Claude Code 的解决方案**：每轮 API 调用前自动收集 Git/仓库上下文注入系统提示——当前分支、工作目录、平台、文件数（四舍五入到 10 的幂保护隐私）。通过 `appendSystemContext()` 以 `<system-reminder>` 格式注入。不 spawn git 进程——直接读 `.git/HEAD` 和 refs。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `context.ts` | `getSystemContext()` 返回 gitStatus/cwd/platform dict |
| `utils/api.ts` (L437-447) | `appendSystemContext()` 以 `<system-reminder>` 注入 |

**Qwen Code 现状**：`getEnvironmentContext()` 仅注入平台和日期；Git 分支仅 VSCode 插件通过 `useGitBranchName` 提供。CLI 模式下模型不知道当前分支。

**Qwen Code 修改方向**：① `getSystemContext()` 收集 gitBranch + cwd + platform + fileCount；② 每轮 `appendSystemContext()` 注入；③ fileCount 四舍五入保护隐私。

**实现成本评估**：
- 涉及文件：~3 个
- 新增代码：~80 行
- 开发周期：~1 天（1 人）
- 难点：fileCount 在大仓库中的高效计算（需用采样或 `git ls-files | wc -l` 缓存）

**改进前后对比**：
- **改进前**：模型不知道当前分支/项目规模，可能建议在 main 上直接提交或对大仓库用低效策略
- **改进后**：每轮自动注入 gitBranch/cwd/platform/fileCount，模型决策基于准确的项目上下文

**意义**：模型需要知道项目上下文才能做出正确决策——"这是 monorepo 还是小项目？哪个分支？"
**缺失后果**：模型不知道当前分支——可能建议在 main 上直接提交。
**改进收益**：自动注入 = 模型始终知道当前分支/目录/项目规模——决策更准确。

---

<a id="item-16"></a>

### 16. IDE 上下文注入与嵌套记忆触发（P2）

**问题**：开发者在 VS Code 中选中一段 TypeScript 代码，切到 Agent 说"重构这段代码"。但 Agent 不知道这个目录有特定的编码规范（比如 `src/api/` 下要求用 class-based 风格，`src/utils/` 下用 functional 风格）。结果 Agent 用了错误的风格重构，开发者还要手动修正。

**Claude Code 的解决方案**：IDE 伴侣注入 3 种上下文：选区内容、打开文件列表、诊断信息。关键特性：IDE 选区和打开文件自动触发**嵌套记忆发现**——从文件路径向上遍历查找 `.qwen/rules/*.md`，注入该目录的编码规范。诊断信息来自 MCP + 被动 LSP 两个来源，交付后清除防止重复。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/attachments.ts` (L1614-1892) | IDE selection → `getNestedMemoryAttachmentsForFile()` 嵌套记忆触发 |
| `utils/attachments.ts` (L2865-2916) | MCP diagnostics + LSP diagnostics 收集与交付后清除 |

**Qwen Code 现状**：IDE 伴侣提供选区/光标/打开文件，但不触发嵌套记忆发现。诊断信息仅来自单一来源。

**Qwen Code 修改方向**：① IDE 选区附件处理时调用 `getNestedMemoryForFile(filePath)` 查找该目录的 rules；② 诊断信息从 MCP + LSP 双源收集，交付后标记已读。

**实现成本评估**：
- 涉及文件：~3 个
- 新增代码：~120 行
- 开发周期：~2 天（1 人）
- 难点：嵌套记忆的目录遍历效率（需缓存已发现的 rules 路径）

**改进前后对比**：
- **改进前**：IDE 选区只提供代码内容，Agent 不知道该目录的编码规范，可能用错风格
- **改进后**：IDE 选区自动触发嵌套记忆发现，注入目录级编码规范，Agent 输出符合项目约定

**意义**：用户在 IDE 中选择代码后切到 Agent——Agent 应该自动知道该文件的编码规范。
**缺失后果**：选择 TypeScript 代码但 Agent 不知道项目的 TS 规范——可能用错风格。
**改进收益**：IDE 选区 → 自动注入目录规范 = 无需用户手动指定。

---

<a id="item-17"></a>

### 17. 图片压缩多策略流水线（P2）

**问题**：开发者粘贴了一张截图或设计稿到 Agent，API 直接报错"image too large"——base64 编码后超过了 API 限制。开发者只能手动用图片工具压缩后再粘贴。如果一次性压缩太狠（比如直接缩到 200×200），图中的代码文字就看不清了。

**Claude Code 的解决方案**：图片进入上下文前经过多策略压缩流水线——① 检测格式（magic bytes 识别 PNG/JPEG/GIF/WebP）；② 尺寸约束（保持宽高比）；③ 格式特定压缩（JPEG quality=80/60/40/20 阶梯递减）；④ 尺寸不够再 resize（75%/50%/25% 逐步缩小）；⑤ 最后手段 1000×1000 + JPEG quality=20。渐进式策略保证在满足 API 限制的同时最大保留图片质量。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/imageResizer.ts` | 多策略压缩流水线、`compressImageBufferWithTokenLimit()` token→bytes 换算 |
| `constants/apiLimits.ts` | `API_IMAGE_MAX_BASE64_SIZE` base64 上限 |

**Qwen Code 现状**：`imageTokenizer.ts` 仅计算 token 数（28×28 像素 = 1 token），不做实际压缩/resize。大图片直接发送会被 API 拒绝。

**Qwen Code 修改方向**：① 发送前检查图片 base64 大小是否超限；② 超限时用 sharp 库按 quality 阶梯压缩；③ 仍超限则逐步 resize；④ token 预算转换：`maxBytes = (maxTokens / 0.125) * 0.75`。

**实现成本评估**：
- 涉及文件：~2 个
- 新增代码：~200 行
- 开发周期：~2 天（1 人）
- 难点：多格式支持（PNG/JPEG/GIF/WebP 各有不同的压缩参数）和 Sharp 实例复用 bug 规避

**改进前后对比**：
- **改进前**：大图片直接发送 → API 报错 → 用户需手动压缩再粘贴
- **改进后**：自动按 quality 阶梯 + resize 阶梯渐进压缩 → 任何图片自动适配 API 限制 → 粘贴即用

**意义**：截图/设计稿常超过 API base64 上限——直接发送 = 被拒绝。
**缺失后果**：大图片 = API 报错 = 用户需手动压缩再粘贴。
**改进收益**：自动压缩流水线 = 任何图片自动适配 API 限制——粘贴即用。

---

<a id="item-18"></a>

### 18. WeakRef/WeakMap 防止 GC 保留（P2）

**问题**：开发者使用 Agent 进行 8+ 小时的长会话（如大型重构），发现内存占用持续增长——从 200MB 涨到 800MB 甚至更多。根本原因是缓存（AbortController 引用、Span 追踪、消息渲染结果等）使用强引用 Map，即使原始对象已经不再使用，缓存条目也永远不会被 GC 回收。

**Claude Code 的解决方案**：关键缓存使用 WeakRef/WeakMap 替代强引用——① AbortController 父子关系用 WeakRef 防止子保留父；② Span 追踪用 `WeakRef<SpanContext>` + 30 分钟 TTL 清理孤儿；③ 消息渲染缓存用 `WeakMap<Message, string>` 随消息替换自动释放。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/abortController.ts` (L30-96) | `WeakRef<AbortController>` 父子关系 |
| `utils/telemetry/sessionTracing.ts` (L71) | `activeSpans: Map<string, WeakRef<SpanContext>>` + 30min TTL |
| `components/VirtualMessageList.tsx` (L24) | `WeakMap<RenderableMessage, string>` 渲染缓存 |
| `ink/node-cache.ts` | `nodeCache: WeakMap<DOMElement, CachedLayout>` 布局缓存 |

**Qwen Code 现状**：无 WeakRef/WeakMap 使用——所有缓存用强引用 Map，长会话中内存持续增长。

**Qwen Code 修改方向**：① AbortController 父子关系用 WeakRef；② 消息渲染缓存改用 WeakMap；③ 搜索结果缓存改用 WeakMap。

**实现成本评估**：
- 涉及文件：~5 个
- 新增代码：~50 行（主要是替换现有 Map 为 WeakMap）
- 开发周期：~1 天（1 人）
- 难点：识别哪些缓存适合 WeakRef/WeakMap（key 必须是对象，且不能有其他强引用）

**改进前后对比**：
- **改进前**：所有缓存用强引用 Map，8 小时长会话内存从 200MB 涨到 800MB+，永不回收
- **改进后**：关键缓存用 WeakRef/WeakMap，缓存条目随原始对象 GC 自动释放，内存稳定

**意义**：长会话 8+ 小时——强引用缓存累积数百 MB 不可回收内存。
**缺失后果**：Map 缓存 = 即使对象不再使用，内存永不释放。
**改进收益**：WeakRef/WeakMap = 缓存随原始对象 GC 释放——零手动清理。

---

<a id="item-19"></a>

### 19. 环形缓冲区与磁盘溢出（P2）

**问题**：开发者在长会话中运行大量搜索（1000 次搜索 × 10KB 结果 = 10MB 不可回收内存）或执行长输出命令（如 `npm install` 输出数万行），内存持续增长直到 OOM。根本原因是搜索结果缓存、消息数组、shell 输出 Buffer 都是无上限的——数据只进不出。

**Claude Code 的解决方案**：需要保留"最近 N 条"的场景使用 CircularBuffer（固定容量，满时覆盖最老）和 BoundedUUIDSet（cap=2000 环形 + Set O(1) 去重）。工具输出超过 8MB 内存限制自动溢出到磁盘文件。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/CircularBuffer.ts` | 固定容量环形缓冲区 |
| `bridge/bridgeMessaging.ts` (L429-459) | `BoundedUUIDSet` cap=2000 |
| `utils/task/TaskOutput.ts` | `CircularBuffer(1000)` + `DEFAULT_MAX_MEMORY = 8MB` 磁盘溢出 |

**Qwen Code 现状**：`result-cache.ts` 和 `agent-interactive.ts` 的 messages 数组无上限；shell 输出 Buffer 无大小限制。

**Qwen Code 修改方向**：① 搜索结果缓存加 `maxSize` 或改用 LRU；② 代理消息数组加 `MAX_MESSAGES` 上限；③ shell 输出缓冲加磁盘溢出机制。

**实现成本评估**：
- 涉及文件：~4 个
- 新增代码：~200 行
- 开发周期：~2 天（1 人）
- 难点：磁盘溢出机制（需要在读取时透明地从磁盘回读，对上层调用者透明）

**改进前后对比**：
- **改进前**：搜索结果/消息/shell 输出无上限增长，长会话最终 OOM
- **改进后**：固定容量环形缓冲区 + 8MB 磁盘溢出，内存有确定上限，会话无限延续

**意义**：无上限数据结构是长会话内存泄漏的首要原因。
**缺失后果**：1000 次搜索 × 10KB = 10MB 不可回收；长 shell 输出 = 数百 MB Buffer。
**改进收益**：有界结构 = 内存有确定上限——无论会话多长都不超限。

---

<a id="item-20"></a>

### 20. 终端渲染字符串池化（P2）

**问题**：终端 UI 以 60fps 渲染，每帧处理数千个 cell（字符 + 样式 + 超链接）。如果每个 cell 都存储完整字符串，帧间 diff 需要逐字符比较数千次，同时产生大量临时字符串对象——GC pause 导致渲染闪烁和输入延迟。

**Claude Code 的解决方案**：CharPool/StylePool/HyperlinkPool 将重复字符串驻留为整数 ID，cell 存储 ID 而非字符串。帧间 diff 比较整数（O(1)）替代字符串比较。每行仅 3 次 intern 调用（非每字符），JIT 友好。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `ink/output.ts` (L553-584) | `styledCharsWithGraphemeClustering()` 每行仅 3 次 intern |
| `ink/screen.ts` | CharPool、StylePool、HyperlinkPool 字符串→整数映射 |

**Qwen Code 现状**：使用 Ink 标准渲染，无自定义池化。代码高亮/diff 渲染每帧重复着色计算。

**Qwen Code 修改方向**：① 代码高亮/diff 渲染场景使用行级缓存（避免重复着色）；② 如扩展自定义渲染层，考虑字符串驻留。

**实现成本评估**：
- 涉及文件：~3 个
- 新增代码：~300 行
- 开发周期：~3 天（1 人）
- 难点：字符串池化需要自定义渲染层，与 Ink 标准渲染集成复杂度高

**改进前后对比**：
- **改进前**：每帧 10K+ 字符串对象创建和比较，GC pause 导致渲染闪烁
- **改进后**：字符串池化为整数 ID，帧间 diff 为整数比较 O(1)，GC 压力减少 90%+

**意义**：60fps 渲染每帧 10K+ 字符串 = GC 压力导致卡顿。
**缺失后果**：GC pause = 渲染闪烁 + 输入延迟。
**改进收益**：字符串池化 = 整数比较 + 零临时对象——GC 压力减少 90%+。

---

<a id="item-21"></a>

### 21. 文件描述符与活跃句柄追踪（P2）

**问题**：开发者在长会话中突然遇到 `EMFILE: too many open files` 错误，Agent 直接崩溃。排查困难——不知道是哪个模块泄漏了文件描述符（fd）。MCP 断连后 transport 可能未完全关闭、LSP 服务器重启留下僵尸句柄、文件 watcher 未清理——每个占 1-2 fd，系统默认限制仅 1024。

**Claude Code 的解决方案**：定期检查 `process._getActiveHandles()` 和 `/proc/self/fd` 数量。超过阈值（>100 handles / >500 fd）记录诊断警告，包含类型分布信息帮助定位泄漏源。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/heapDumpService.ts` (L106-119) | `process._getActiveHandles().length`、`/proc/self/fd` 计数 |
| `utils/heapDumpService.ts` (L141, L156) | >100 handles 警告、>500 fd 警告 |

**Qwen Code 现状**：无句柄/fd 追踪——MCP 断连后 transport 可能未完全关闭，fd 泄漏无任何诊断信息。

**Qwen Code 修改方向**：① 定期检查句柄数；② 超阈值记录类型分布日志；③ 配合 heapDump 一起报告。

**实现成本评估**：
- 涉及文件：~2 个
- 新增代码：~80 行
- 开发周期：~1 天（1 人）
- 难点：跨平台兼容（`/proc/self/fd` 仅 Linux，macOS 需用 `lsof`）

**改进前后对比**：
- **改进前**：fd 泄漏无感知，突然 EMFILE 崩溃，无法定位泄漏源
- **改进后**：定期检查 fd 数量，超阈值时记录类型分布警告，在耗尽前提前发现并修复

**意义**：fd 耗尽 = EMFILE 错误 = 无法打开文件/建立连接。
**缺失后果**：fd 泄漏无诊断——突然崩溃无法定位原因。
**改进收益**：定期追踪 = 提前发现泄漏——在耗尽前修复。

---

<a id="item-22"></a>

### 22. Memoization cold start去重与 Identity Guard（P2）

**问题**：Agent 启动时 10 个组件同时请求 MCP 工具列表——缓存为空（cold start），每个组件都触发一次完整的网络请求。结果是 10 次完全相同的 API 调用。更隐蔽的 bug：缓存清除（`cache.clear()`）和新的 cold start 并发时，旧的后台刷新结果可能覆盖新的缓存值。

**Claude Code 的解决方案**：`memoizeWithTTLAsync` 的 `inFlight` Map 防止 N 个并发调用在缓存 cold start 时触发 N 次昂贵操作——第一个调用创建 Promise 并存入 inFlight，后续调用直接等待同一个 Promise。Identity guard 防止并发 `cache.clear()` + cold start 导致旧刷新覆盖新缓存。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/memoize.ts` (L120-220) | `memoizeWithTTLAsync()`——`inFlight: Map` cold start 去重 |
| `utils/memoize.ts` (L147-150, L175-189) | identity guard 防止 clear + cold-miss 数据错乱 |

**Qwen Code 现状**：`crawlCache.ts` 有 TTL 但无 cold start 去重，高并发场景会触发 N 次相同请求。

**Qwen Code 修改方向**：① 新建 `memoizeAsync.ts`——Promise 去重 inFlight Map；② TTL 过期返旧值 + 后台刷新；③ identity guard 防 race condition。

**实现成本评估**：
- 涉及文件：~2 个
- 新增代码：~150 行
- 开发周期：~2 天（1 人）
- 难点：identity guard 的正确性（防止 clear + cold-miss 交错导致数据错乱）

**改进前后对比**：
- **改进前**：10 个并发请求在 cold start 时触发 10 次相同 API 调用，clear + cold-miss 可能数据错乱
- **改进后**：inFlight Map 去重 = 1 次调用 + 9 次等待同一 Promise，identity guard 防止 race condition

**意义**：10 个并发 MCP 工具刷新 → 无去重 = 10 次相同 API 调用。
**缺失后果**：cold start 雪崩——高并发场景 N× 重复网络请求。
**改进收益**：inFlight 去重 = 1 次调用，N-1 次等待——网络开销减少 90%。

---

<a id="item-23"></a>

### 23. 正则表达式编译缓存（P2）

**问题**：每次工具调用都会触发 Hook 事件匹配——`hookPlanner.ts` 中 `new RegExp(matcher)` 对每个 hook 的 matcher 重新编译正则表达式。一轮对话可能触发 10 次工具调用 × 5 个 hook matcher = 50 次重复正则编译。LS 工具的 glob→regex 转换也是每个文件重新编译一次。这些都是纯 CPU 浪费。

**Claude Code 的解决方案**：正则模式在模块作用域预编译（`const PATTERN = /regex/`），运行时直接复用。动态模式使用缓存 Map 存储编译结果。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| 多处 | 正则模式在模块作用域预编译（如 `const PATTERN = /regex/`） |

**Qwen Code 现状**：`hookPlanner.ts` (L152, L169) 每次 `new RegExp(matcher)` 重新编译；`ls.ts` (L98-102) 每文件重新编译 glob regex。

**Qwen Code 修改方向**：① `regexCache: Map<string, RegExp>` 缓存编译结果；② LS 工具 glob→regex 编译一次后复用；③ 可选 LRU 上限（1000 条）防止长会话内存增长。

**实现成本评估**：
- 涉及文件：~3 个
- 新增代码：~40 行
- 开发周期：~0.5 天（1 人）
- 难点：几乎无难点，纯机械性优化

**改进前后对比**：
- **改进前**：每次工具调用 × 每个 hook matcher = N 次重复正则编译
- **改进后**：首次编译后缓存到 Map，后续 O(1) 查找，hot path CPU 降低 90%

**意义**：Hook 匹配是每次工具调用的 hot path——数百次重复编译浪费 CPU。
**缺失后果**：每次工具调用 × 每个 hook matcher × new RegExp = 无谓 CPU 开销。
**改进收益**：编译缓存 = 首次编译后 O(1) 查找——hot path CPU 降低 90%。

---

<a id="item-24"></a>

### 24. 搜索结果流式解析与提前终止（P2）

**问题**：在大型代码库（如 Linux kernel）中执行搜索，ripgrep 可能返回 10 万+ 行结果。当前实现 `rawOutput.split('\n').filter(...)` 把所有结果全量加载到内存后再过滤——创建 10 万个字符串对象，GC 压力巨大。更糟的是 `grepOutput += ...` 在循环中拼接字符串（O(n^2) 性能）。而实际上用户可能只需要前 100 行结果。

**Claude Code 的解决方案**：ripgrep 输出流式逐行解析——边读边去重边截断。配合 `--max-count` 参数让 ripgrep 在达到限制后提前退出。流式计数文件数时仅统计换行字节，不存储路径字符串。`MAX_BUFFER_SIZE = 20MB` 截断防止内存爆炸。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/ripgrep.ts` (L246-279) | `countFilesRoundedRg()` 流式计数——仅统计换行字节，不存路径 |
| `utils/ripgrep.ts` (L295-343) | `ripGrepStream()` 流式回调——每 chunk 调用 `onLines()` |
| `utils/ripgrep.ts` (L108-232) | `MAX_BUFFER_SIZE = 20MB` 截断防止内存爆炸 |

**Qwen Code 现状**：`ripGrep.ts` (L109) `rawOutput.split('\n').filter(...)` 全量加载；`grep.ts` (L203-209) 字符串拼接 `grepOutput += ...` 在循环中。

**Qwen Code 修改方向**：① ripgrep 结果用流式 `onData` 回调逐行处理；② 字符串拼接改为 `array.push()` + `join()`；③ 传 `--max-count` 参数提前终止大搜索。

**实现成本评估**：
- 涉及文件：~2 个
- 新增代码：~100 行
- 开发周期：~1 天（1 人）
- 难点：流式解析的行分割逻辑（处理跨 chunk 的不完整行）

**改进前后对比**：
- **改进前**：10 万行结果全量 `split('\n')` = 10 万个字符串对象 + O(n^2) 拼接，内存暴涨
- **改进后**：流式逐行处理 = O(1) 内存，`--max-count` 提前终止 = 只搜索需要的量

**意义**：大型代码库搜索可能返回 10 万+ 行——全量 split 创建 10 万个字符串对象。
**缺失后果**：split('\n') + filter + deduplicate = 3× O(n) 内存 + GC 压力。
**改进收益**：流式解析 = O(1) 内存（逐行处理）；--max-count = 搜索提前终止。

---

<a id="item-25"></a>

### 25. React.memo 自定义相等性优化（P2）

**问题**：开发者在长对话（100+ 条消息）中打字时感到明显卡顿——每次击键延迟 500ms+。原因是每次击键触发父组件状态更新，整个消息列表（100 条）全部重渲染。实际上只有输入框内容变了，历史消息根本不需要重渲染。

**Claude Code 的解决方案**：每条消息用 `React.memo` + 自定义 `arePropsEqual` 防止不必要重渲染。自定义比较器仅检查消息 ID 和内容变化，忽略回调函数引用变化（避免因 useCallback 缺失导致的无效重渲染）。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `components/Message.tsx` (L626) | `React.memo` + `areMessagePropsEqual` 自定义比较 |
| `components/Messages.tsx` (L730-741) | 消息列表 `React.memo` 防止结构未变时重渲染 |
| `components/messages/UserPromptMessage.tsx` (L23-48) | `React.memo` 防止击键 500ms+ 延迟 |

**Qwen Code 现状**：`useGeminiStream.ts` 有 useMemo/useCallback，但消息列表组件（`MessageList.tsx`）和单条消息组件是否有 React.memo 需确认。

**Qwen Code 修改方向**：① 消息组件加 `React.memo(MessageComponent, arePropsEqual)`；② `arePropsEqual` 仅比较 `message.id` + `message.content` 变化；③ `useCallback` 包裹所有传给子组件的回调。

**实现成本评估**：
- 涉及文件：~3 个
- 新增代码：~50 行
- 开发周期：~1 天（1 人）
- 难点：设计正确的 `arePropsEqual`（漏比较会导致不更新，多比较会降低效果）

**改进前后对比**：
- **改进前**：100 条历史消息 × 每次击键全部重渲染 = 500ms+ 延迟，明显卡顿
- **改进后**：React.memo 跳过未变化消息 = 仅输入框重渲染 = 击键延迟 <16ms

**意义**：终端 UI 渲染是主线程 hot path——不必要重渲染 = 击键延迟。
**缺失后果**：100 条历史消息 × 每次击键全部重渲染 = 明显卡顿。
**改进收益**：React.memo = 仅变化的消息重渲染——击键延迟从 500ms 降到 <16ms。

---

<a id="item-26"></a>

### 26. Bun 原生 API 性能优化（P2）

**问题**：终端渲染的最热函数是字符串宽度计算（每帧调用 ~10 万次）。纯 JS 实现（`string-width` npm 包）每帧需要 10-50ms——60fps 渲染预算仅 16ms，光宽度计算就超时了。JSONL 解析和子进程 spawn 也有类似的 JS 层开销。

**Claude Code 的解决方案**：3 个 Bun 原生 API 替代纯 JS——① `Bun.stringWidth` 原生宽度计算（50-100× 快于 JS）；② `Bun.JSONL.parseChunk` 流式 JSONL 解析（无需全量 split）；③ `Bun.spawn` 的 `argv0` 参数实现单二进制多工具调度。非 Bun 环境自动回退到 JS 实现。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `ink/stringWidth.ts` (L213-222) | 模块作用域 Bun.stringWidth 解析——避免 hot path typeof 检查 |
| `utils/json.ts` (L94-127) | `Bun.JSONL.parseChunk` 流式 JSONL 解析 + 非 Bun 回退 |
| `utils/ripgrep.ts` (L562-567) | `Bun.spawn` argv0 dispatch 嵌入式 ripgrep |

**Qwen Code 现状**：使用 Node.js 标准 API（`string-width` npm 包、`JSON.parse` 逐行、`execFile` 子进程），无 Bun 原生优化。

**Qwen Code 修改方向**：① 检测 Bun 运行时时使用原生 API（条件导入）；② 非 Bun 环境保持现有实现作为回退；③ stringWidth 结果模块作用域缓存（避免重复 typeof 检查）。

**实现成本评估**：
- 涉及文件：~3 个
- 新增代码：~80 行
- 开发周期：~1 天（1 人）
- 难点：需要先迁移到 Bun 运行时（或保持双运行时支持的条件分支）

**改进前后对比**：
- **改进前**：纯 JS stringWidth 每帧 10-50ms（超出 16ms 渲染预算），JSONL 全量 split
- **改进后**：Bun 原生 API = 0.1-0.5ms/帧，流式 JSONL 解析，非 Bun 环境自动回退

**意义**：字符串宽度计算是终端渲染最热的函数——每帧调用 10 万次。
**缺失后果**：JS 实现 = 每帧 10-50ms 用于宽度计算——60fps 渲染预算仅 16ms。
**改进收益**：Bun 原生 = 0.1-0.5ms/帧——渲染预算充裕。

---

<a id="item-27"></a>

### 27. 终端行宽缓存与 Blit 屏幕 Diff（P2）

**问题**：Agent 流式输出代码时，每帧只新增 1 行，但渲染器需要重算全部 1000 行的宽度——因为没有缓存机制。这意味着每帧的计算量是 O(total_lines) 而非 O(new_lines)，1000 行输出时每帧计算量是实际需要的 1000 倍。渲染帧率直线下降。

**Claude Code 的解决方案**：① 行宽缓存：已完成的行（不再变化）的 stringWidth 结果缓存到 4096-entry LRU——流式输出场景减少 50× 调用；② Blit 屏幕 diff：未变化的子树从上一帧直接 block-transfer（blit），仅对 damage region 内的 cell 逐个 diff。滚动时用 `shiftRows()` 原地移动行。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `ink/line-width-cache.ts` | 4096-entry 行宽 LRU 缓存——完成行不再计算 |
| `ink/output.ts` (L208-384) | Blit 屏幕 diff——未变化区域直接复制 + damage tracking |
| `ink/render-node-to-output.ts` (L508-522) | `hasRemovedChild` 禁用 blit（防止删除元素残留） |

**Qwen Code 现状**：使用 Ink 标准渲染——每帧完整重算布局和宽度，无行级缓存。

**Qwen Code 修改方向**：① 代码高亮/diff 渲染行添加行级缓存（内容不变则复用上次渲染结果）；② 长输出滚动时仅更新新增行，不重绘已有行。

**实现成本评估**：
- 涉及文件：~3 个
- 新增代码：~250 行
- 开发周期：~3 天（1 人）
- 难点：damage region 追踪（需要准确标记哪些行/区域在帧间发生了变化）

**改进前后对比**：
- **改进前**：每帧重算全部 1000 行宽度 = O(total_lines)，渲染帧率随内容增长下降
- **改进后**：已完成行宽度 LRU 缓存 + blit diff = O(new_lines) 每帧，渲染帧率稳定 60fps

**意义**：流式输出 1000 行——每帧只新增 1 行，但无缓存时重算 1000 行宽度。
**缺失后果**：O(total_lines) 每帧 vs O(new_lines) 每帧——1000× 性能差距。
**改进收益**：行宽缓存 + blit diff = 仅新增/变化行参与计算——渲染帧率稳定 60fps。

---

<a id="item-28"></a>

### 28. 编译时特性门控与死代码消除（P2）

**问题**：生产环境的 bundle 中包含了大量调试日志、内部工具、实验性功能的代码——占 bundle 5-10%。这些代码虽然被 `if (process.env.DEBUG)` 包裹，运行时不执行，但仍然需要加载和解析，占用启动时间和内存。每次调用还要检查一次环境变量。

**Claude Code 的解决方案**：`feature('FLAG_NAME')` 在编译时求值——Bun 构建器将未启用的特性分支完全移除（dead code elimination）。运行时零成本：不检查 flag，不加载代码，不占 bundle 体积。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/slowOperations.ts` (L157) | `feature('SLOW_OPERATION_LOGGING')` 编译时消除调试日志 |
| `tools.ts` | `feature('PROACTIVE')`, `feature('COORDINATOR_MODE')` 等条件工具加载 |

**Qwen Code 现状**：使用运行时环境变量（`process.env.DEBUG`）控制特性——未使用的代码仍在 bundle 中，每次调用都检查环境变量。

**Qwen Code 修改方向**：① 定义编译时常量（如 `__DEV__`、`__INTERNAL__`）；② 构建工具（esbuild/rollup）配置 `define` 替换；③ 调试日志、内部工具包裹在 `if (__DEV__)` 中——生产构建自动消除。

**实现成本评估**：
- 涉及文件：~6 个（构建配置 + 各模块中的 flag 替换）
- 新增代码：~50 行
- 开发周期：~1 天（1 人）
- 难点：确保 tree-shaking 正确工作（需要 side-effect-free 模块标记）

**改进前后对比**：
- **改进前**：调试代码在 bundle 中占 5-10%，运行时每次检查环境变量，占用内存
- **改进后**：编译时 dead code elimination，生产 bundle 零调试代码，零运行时检查开销

**意义**：调试代码占 bundle 5-10%——生产环境不需要但仍加载和解析。
**缺失后果**：运行时 flag 检查 = 每次调用多一个 if 分支 + 调试模块仍占内存。
**改进收益**：编译时消除 = 零运行时成本——bundle 更小、启动更快、内存更少。

---

<a id="item-29"></a>

### 29. Shell 环境快照与会话级缓存（P2）

**问题**：开发者在终端中习惯了自定义别名（如 `alias ll='ls -la'`、`alias k='kubectl'`）和 shell 函数。但 Agent 每次执行 shell 命令都 spawn 一个干净的新进程——不继承用户的别名和函数。开发者说"在 Agent 里运行 `ll` 报 command not found"。更大的问题是每次 spawn 都重新解析 .bashrc/.zshrc，额外增加 200-500ms。

**Claude Code 的解决方案**：会话启动时一次性捕获用户 shell 环境（functions/aliases/options/PATH）存储为 snapshot 脚本文件。后续每次 shell 命令执行时 `source snapshot.sh` 获得完整环境。Shell 配置通过 `memoize()` 缓存——整个会话只发现一次。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/bash/ShellSnapshot.ts` (L388-582) | 一次性捕获 functions/aliases/options/PATH，10s 超时 |
| `utils/Shell.ts` (L145-146) | `getShellConfig = memoize()` 会话级缓存 |

**Qwen Code 现状**：每次 shell 命令通过 `spawn` 创建新进程——不继承用户别名和函数，每次重新初始化 shell 环境。

**Qwen Code 修改方向**：① 会话启动时执行 `source ~/.bashrc && declare -f > snapshot.sh`；② 后续命令前 `source snapshot.sh`；③ Shell 类型/路径检测结果 `memoize()` 缓存。

**实现成本评估**：
- 涉及文件：~3 个
- 新增代码：~200 行
- 开发周期：~2 天（1 人）
- 难点：跨 shell 兼容（bash 用 `declare -f`，zsh 用 `functions`，fish 完全不同）

**改进前后对比**：
- **改进前**：每次 spawn 干净环境，用户别名/函数不可用，每次 200-500ms shell 初始化
- **改进后**：启动时一次性快照用户环境，后续 `source snapshot.sh` = 完整环境 + 省去重复初始化

**意义**：用户的 shell 别名（如 `alias ll='ls -la'`）在 Agent 中不可用——命令行为不一致。
**缺失后果**：每次 spawn = 干净环境 = 用户别名/函数不可用 + 200-500ms 初始化。
**改进收益**：快照 = 一次捕获 + 每次 source = 完整用户环境 + 省去重复初始化。

---

<a id="item-30"></a>

### 30. Shell 输出文件直写绕过 JS（P2）

**问题**：开发者执行 `npm install` 或 `make` 等输出数万行的命令，Agent 用 PTY + xterm.js 处理全部输出——每一行都经过 xterm.js 终端仿真解析 + JSON.stringify 比较。这是 CPU 密集操作，导致 Agent 在命令执行期间卡顿，其他操作无法响应。

**Claude Code 的解决方案**：非交互命令的 stdout/stderr 直接写入文件描述符（`stdio[1] = fd`），完全绕过 JS 事件循环。进度信息通过定期轮询文件尾部（1s 间隔，读取尾部 4096 字节）提取。5GB 磁盘上限 watchdog 防止磁盘填满。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/Shell.ts` (L302-358) | `O_APPEND + O_CREAT + O_NOFOLLOW` 文件直写——child 持有 fd |
| `utils/task/TaskOutput.ts` (L32-390) | `POLL_INTERVAL_MS = 1000` 文件尾部轮询、`MAX_TASK_OUTPUT_BYTES = 5GB` watchdog |

**Qwen Code 现状**：`shellExecutionService.ts` 通过 PTY + headless terminal 处理所有 shell 输出——数据经 xterm.js 解析 + 每事件 JSON.stringify 比较（L699），无论命令是否需要交互。

**Qwen Code 修改方向**：① 非交互命令改用文件直写模式（stdin/stdout 直接到 fd）；② 进度通过 1s 文件尾部轮询提取；③ 大输出 watchdog（5GB 上限 + SIGKILL）。

**实现成本评估**：
- 涉及文件：~3 个
- 新增代码：~200 行
- 开发周期：~3 天（1 人）
- 难点：区分交互/非交互命令（需要 shell AST 分析或启发式判断）

**改进前后对比**：
- **改进前**：所有命令输出经 PTY + xterm.js 解析 + JSON.stringify 比较 = CPU 密集 + 内存膨胀
- **改进后**：非交互命令直写文件 = 零 JS 开销，1s 轮询文件尾部仅读 4KB 获取进度

**意义**：`npm install` 输出数万行——全部经 xterm.js 解析 + JSON.stringify 对比 = 巨大开销。
**缺失后果**：PTY 处理全部输出 = CPU 密集 + 内存膨胀（xterm buffer）。
**改进收益**：文件直写 = 零 JS 开销；文件轮询 = 仅读最后 4KB 获取进度。

---

<a id="item-31"></a>

### 31. 增量文件索引签名检测（P2）

**问题**：开发者输入文件路径时 Agent 提供补全建议。但每次击键都需要判断"文件列表是否需要刷新"。当前实现用 `crypto.createHash('sha256')` 对完整 ignore 内容 + 目录字符串计算 hash——大仓库（34.6 万文件）每次击键消耗 10-50ms。这导致补全建议出现明显延迟。

**Claude Code 的解决方案**：两个低成本检测——① `stat('.git/index')` 的 mtime 变化检测 git 操作（未变化则跳过刷新，5s 节流）；② FNV-1a hash 对路径列表进行**采样签名**（每 500 个路径取 1 个样本），<1ms 检测 34.6 万文件列表是否变化。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `hooks/fileSuggestions.ts` (L60-150) | `getGitIndexMtime()` + `REFRESH_THROTTLE_MS = 5000` |
| `hooks/fileSuggestions.ts` (L111-131) | `pathListSignature()` FNV-1a 采样签名 |

**Qwen Code 现状**：`crawlCache.ts` 每次搜索用 `crypto.createHash('sha256')` 对完整 ignore 内容 + 目录字符串计算 hash，大仓库开销显著。

**Qwen Code 修改方向**：① 用文件 mtime 替代内容 hash 作为缓存 key（避免读文件内容）；② 路径列表用采样签名（每 N 个取 1 个）检测变化；③ 5s 节流避免频繁 stat。

**实现成本评估**：
- 涉及文件：~2 个
- 新增代码：~80 行
- 开发周期：~1 天（1 人）
- 难点：采样签名的采样率选择（太稀疏可能漏检变化，太密集失去性能优势）

**改进前后对比**：
- **改进前**：每次击键 SHA256 全量 hash = 10-50ms 延迟，补全建议卡顿
- **改进后**：mtime stat = 0.1ms + FNV-1a 采样签名 = <1ms，击键零感知延迟

**意义**：文件补全每次击键触发——全量 SHA256 = 每次 10-50ms。
**缺失后果**：SHA256(ignore 内容 + 目录) × 每次击键 = 累积延迟。
**改进收益**：mtime stat = 0.1ms + 采样签名 = <1ms——击键零延迟。

---

<a id="item-32"></a>

### 32. Shell AST 解析缓存（P2）

**问题**：Agent 执行 shell 命令前需要权限检查——先调用 `getDefaultPermission()` 做 AST 解析判断是否安全，再调用 `getConfirmationDetails()` 做一次相同的 AST 解析生成确认信息。同一条命令被解析了 2 次。复合命令（`foo && bar || baz`）更贵——每个子命令都被解析 2 次。

**Claude Code 的解决方案**：AST 解析结果缓存到 Map 中，同一命令字符串第二次直接命中缓存。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/bash/treeSitterAnalysis.ts` (506行) | AST 解析 + 读写分类——结果可缓存 |

**Qwen Code 现状**：`shell.ts` (L98-108, L126-138) `isShellCommandReadOnlyAST()` 在同一命令上调用 2 次——`getDefaultPermission()` 和 `getConfirmationDetails()` 各一次，无缓存。

**Qwen Code 修改方向**：① `astCache: Map<string, ASTResult>` 缓存解析结果；② 第二次调用直接命中缓存；③ 可选 LRU 上限防止长会话内存增长。

**实现成本评估**：
- 涉及文件：~1 个
- 新增代码：~30 行
- 开发周期：~0.5 天（1 人）
- 难点：几乎无难点，纯缓存添加

**改进前后对比**：
- **改进前**：同一命令 AST 解析 2 次（`getDefaultPermission` + `getConfirmationDetails`），复合命令更多
- **改进后**：首次解析后缓存到 Map，第二次 O(1) 查找，权限检查速度翻倍

**意义**：AST 解析是 shell 权限检查的 hot path——复合命令解析尤其昂贵。
**缺失后果**：同一命令 2× AST 解析 = 2× CPU 开销。
**改进收益**：缓存 = 第二次 O(1) 查找——权限检查速度翻倍。

---

<a id="item-33"></a>

### 33. 终端输出 JSON.stringify 比较替换（P2）

**问题**：开发者执行 `npm install`（输出 10 万行），Agent 终端卡死。原因是 `shellExecutionService.ts` 每收到一行输出就用 `JSON.stringify(output) !== JSON.stringify(finalOutput)` 比较全部输出是否变化——这是 O(n) 序列化操作。10 万行 × 每行 O(n) = O(n^2) 总开销。

**Claude Code 的解决方案**：用浅比较（数组长度 + 最后一行变化检测 = O(1)）替代 JSON.stringify 深比较。结合脏位标记（xterm.js `onRender` 回调标记变化行范围），仅处理实际变化的行。

**Qwen Code 现状**：`shellExecutionService.ts` (L699) `JSON.stringify` 深比较 + (L654-676) 全缓冲区逐行迭代 + (L768) Promise chain 串行处理。

**Qwen Code 修改方向**：① 输出比较改为 `output.length !== finalOutput.length || output[output.length-1] !== finalOutput[finalOutput.length-1]` 浅比较；② 缓冲区序列化仅处理脏行范围；③ Promise chain 改为批量处理（累积 chunks 后一次 write）。

**实现成本评估**：
- 涉及文件：~1 个
- 新增代码：~50 行
- 开发周期：~1 天（1 人）
- 难点：确保浅比较不遗漏中间行的变化（xterm.js 可能在中间插入/删除行）

**改进前后对比**：
- **改进前**：每行输出触发 O(n) JSON.stringify 比较，10 万行 = O(n^2) 总开销，终端卡死
- **改进后**：浅比较 O(1) + 脏行范围 O(dirty) = 线性时间处理，大输出不卡

**意义**：大输出（npm install 10 万行）× 每行 JSON.stringify = 性能灾难。
**缺失后果**：O(n) 序列化 × 每行 = O(n^2) 总开销——终端卡死。
**改进收益**：浅比较 O(1) + 脏行范围 O(dirty) = 线性时间处理。

---

<a id="item-34"></a>

### 34. Diff 渲染 useMemo 与 Regex 预编译（P2）

**问题**：Agent 编辑文件后显示 diff 对比。Diff 渲染组件是最频繁渲染的组件——每次 React render 都重新执行 `parseDiffWithLineNumbers()`（包括正则编译和行迭代），即使 diff 内容根本没变。10KB diff × 每帧解析 = 每帧 5-10ms，60fps 渲染预算仅 16ms——光 diff 解析就占了一半。

**Claude Code 的解决方案**：用 `useMemo(fn, [diffContent])` 包裹 diff 解析，仅在 diff 内容变化时重新计算。正则在模块作用域预编译。大文件 diff（>1MB）异步分块处理避免阻塞主线程。

**Qwen Code 现状**：`DiffRenderer.tsx` (L23-81) `parseDiffWithLineNumbers()` 每次 render 调用，内部 `new RegExp(...)` (L29) 每次编译，无 useMemo 缓存。

**Qwen Code 修改方向**：① `useMemo(() => parseDiffWithLineNumbers(diff), [diff])`；② 正则提取到模块作用域预编译；③ 大 diff（>5000 行）分块渲染（先显示首 200 行 + "展开更多"）。

**实现成本评估**：
- 涉及文件：~1 个
- 新增代码：~30 行
- 开发周期：~0.5 天（1 人）
- 难点：大 diff 分块渲染的交互设计（"展开更多"按钮 + 虚拟滚动）

**改进前后对比**：
- **改进前**：每帧重新解析 diff + 重新编译正则 = 5-10ms/帧，渲染预算紧张
- **改进后**：useMemo 缓存 = 内容不变时 0ms，预编译正则省去 compile 开销

**意义**：Diff 是最频繁渲染的组件——文件编辑后每帧重渲染。
**缺失后果**：10KB diff × 每帧解析 = 每帧 5-10ms（60fps 预算仅 16ms）。
**改进收益**：useMemo = 内容不变时 0ms；预编译正则 = 省去每次 compile 开销。

---
