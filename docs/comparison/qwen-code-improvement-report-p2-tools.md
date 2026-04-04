# Qwen Code 改进建议 — P2 工具与命令扩展

> 中等优先级改进项。每项包含：问题分析、源码索引、现状评估、改进方向、实现成本、前后对比。
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md)

---

<a id="item-1"></a>

### 1. Conditional Hooks（P2）

开发者配置了多个 Hook（如 pre-commit 检查、代码格式化、安全扫描），但这些 Hook 在每次工具调用时都会全部触发——即使当前操作与某些 Hook 完全无关。例如，执行 `ls` 命令时也会触发 pre-commit 检查，白白浪费时间。需要一种条件过滤机制，让 Hook 只在匹配的场景下执行。

Claude Code 的方案是在 Hook 配置中支持 `if` 字段，复用权限规则语法（如 `Bash(git:*)` 仅在 git 命令时触发），实现精确的场景过滤。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/hooks/hookRunner.ts` | `if` 字段匹配逻辑 |
| `types/hooks.ts` | `HookConfig.if` 字段定义 |

**Qwen Code 现状**：Hook 系统无条件过滤——所有注册的 Hook 在匹配事件触发时全部执行，无法按工具类型或参数精细控制。

**Qwen Code 修改方向**：`hookRunner.ts` 执行前检查 `hook.if` 条件；复用权限规则匹配器（`permission-manager.ts`）。

**实现成本评估**：
- 涉及文件：~3 个
- 新增代码：~150 行
- 开发周期：~2 天（1 人）
- 难点：复用权限规则匹配器的模式语法解析

**改进前后对比**：
- **改进前**：所有匹配事件都触发全部 Hook——执行 `ls` 也跑 pre-commit 检查
- **改进后**：`if: "Bash(git:*)"` 条件过滤——仅在 git 命令时运行 pre-commit 检查

**意义**：Hook 需要按场景过滤——不是所有工具调用都应触发所有 hook。
**缺失后果**：所有匹配事件都触发——无法精细控制。
**改进收益**：if 条件过滤——'仅在 git 命令时运行 pre-commit 检查'。

---

<a id="item-2"></a>

### 2. Transcript Search（P2）

长会话进行到 50+ 轮后，开发者经常需要回忆之前讨论的某个 API 设计决策或报错信息。当前只能手动向上滚动逐条查找，在几百条消息中定位目标内容极其低效。需要类似 Vim 的搜索体验——按 `/` 进入搜索模式，输入关键词后 `n`/`N` 在匹配项间快速导航。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `components/Messages/` | transcript 搜索 UI + 高亮 |

**Qwen Code 现状**：transcript 模式无搜索功能——只能手动滚动浏览历史消息。

**Qwen Code 修改方向**：`HistoryItemDisplay.tsx` 新增搜索状态；`KeypressContext` 拦截 `/` 键进入搜索模式。

**实现成本评估**：
- 涉及文件：~3 个
- 新增代码：~200 行
- 开发周期：~2 天（1 人）
- 难点：搜索高亮渲染与现有消息组件的集成

**改进前后对比**：
- **改进前**：手动滚动查找——在几百条消息中逐条翻阅
- **改进后**：按 `/` 搜索 + `n`/`N` 导航——秒级定位历史讨论

**意义**：长会话中回忆之前的讨论是常见需求。
**缺失后果**：需手动滚动查找——'刚才说的那个 API 是什么？'
**改进收益**：/ 搜索 + n/N 导航——快速定位历史讨论。

---

<a id="item-3"></a>

### 3. Bash File Watcher（P2）

开发者在项目中配置了 Prettier、ESLint 等自动格式化工具（通过 IDE 保存触发或 watch 模式）。Agent 读取文件后，formatter 可能在后台自动修改了该文件。此时 Agent 基于旧内容执行编辑，会覆盖 formatter 的修改——导致格式化丢失或产生冲突。需要在编辑前检测文件是否已被外部修改，及时提醒 Agent 重新读取。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `tools/BashTool/` | 文件 mtime 比对逻辑 |
| `utils/fileStateCache.ts` | 已读文件状态缓存 |

**Qwen Code 现状**：无文件变更检测机制——Agent 编辑文件时不检查文件是否在读取后被外部修改。

**Qwen Code 修改方向**：`edit.ts` 编辑前比对文件 mtime 与上次 read 时的 mtime；不一致时警告并建议 re-read。

**实现成本评估**：
- 涉及文件：~3 个
- 新增代码：~120 行
- 开发周期：~1 天（1 人）
- 难点：mtime 精度在不同文件系统上的差异处理

**改进前后对比**：
- **改进前**：Agent 基于旧内容编辑 → 覆盖 formatter 的修改 → 格式丢失
- **改进后**：编辑前自动检测 mtime 变化 → 警告"文件已被外部修改" → 建议 re-read

**意义**：formatter/linter 在 Agent 读取文件后可能自动修改——导致编辑冲突。
**缺失后果**：Agent 基于旧内容编辑 → 覆盖 formatter 的修改 → 格式丢失。
**改进收益**：自动检测文件被外部修改 → 提醒 re-read——避免 stale-edit。

---

<a id="item-4"></a>

### 4. /batch 并行操作（P2）

大规模重构场景（如"将所有 class 组件迁移到 hooks"、"给 50 个文件添加 TypeScript 类型"）中，Agent 只能逐文件串行处理，一个 200 文件的重构可能需要等待数小时。需要一种并行编排机制——将任务拆分为多个子任务，fork 多个 Agent 并行执行，最后汇总结果。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `skills/bundled/batch.ts` | /batch bundled skill |

**Qwen Code 现状**：无并行任务编排能力——所有文件操作串行执行，大规模重构效率低。

**Qwen Code 修改方向**：新建 `skills/bundled/batch/SKILL.md`；核心逻辑是解析用户输入 → 拆分 → fork 多个 Agent → 汇总。

**实现成本评估**：
- 涉及文件：~5 个
- 新增代码：~400 行
- 开发周期：~5 天（1 人）
- 难点：多 Subagent 并发控制与结果合并冲突处理

**改进前后对比**：
- **改进前**：逐文件串行处理——50 个文件的重构需要 Agent 一个个执行
- **改进后**：`/batch "迁移到 hooks"` → 自动拆分为 10 组 → 5 个 Subagent 并行执行

**意义**：大规模重构（如'所有 class 组件迁移到 hooks'）需要并行处理多文件。
**缺失后果**：只能逐文件处理——大规模重构耗时长。
**改进收益**：并行拆分执行——多文件同时处理，速度倍增。

---

<a id="item-5"></a>

### 5. Chrome Extension 浏览器调试（P2）

前端开发者调试 UI bug 时，需要 Agent 能"看到"浏览器中的实际渲染结果、Console 错误日志和 Network 请求。当前 Agent 只能根据开发者的文字描述来理解问题，无法直接访问浏览器状态——这导致前端调试效率远低于后端。需要通过 Chrome 扩展 + MCP 协议桥接，让 Agent 直接读取 DOM、Console、Network 数据。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/claudeInChrome/mcpServer.ts` | Chrome MCP Server |
| `utils/claudeInChrome/chromeNativeHost.ts` | Native Messaging Host |

**Qwen Code 现状**：无浏览器集成能力——前端调试完全依赖开发者文字描述或截图。

**Qwen Code 修改方向**：开发 Chrome 扩展 + Native Messaging Host；注册为 MCP Server（tools: read_page/read_console/navigate）。

**实现成本评估**：
- 涉及文件：~10 个（Chrome 扩展 + Native Host + MCP Server）
- 新增代码：~1500 行
- 开发周期：~10 天（1 人）
- 难点：Chrome Extension manifest V3 限制、Native Messaging 跨平台兼容

**改进前后对比**：
- **改进前**：Agent 无法访问浏览器——开发者需手动复制 Console 错误、描述 UI 状态
- **改进后**：Agent 直接调用 `read_page()`/`read_console_messages()` 获取浏览器实时状态

**意义**：前端调试需要 Agent 看到浏览器渲染结果和错误日志。
**缺失后果**：Agent 无法'看到'浏览器——前端 bug 只能靠描述。
**改进收益**：直接读取 DOM/Console/Network——前端调试效率大幅提升。

---

<a id="item-6"></a>

### 6. /effort 命令（P2）

不同任务对推理深度的需求差异很大：简单的变量重命名不需要深度思考，而复杂的架构重构需要模型充分推理。当前模型使用固定的推理深度——简单任务浪费 token 和时间，复杂任务推理又不够充分。需要一个动态调节机制，让开发者按需设置推理深度级别。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `commands/effort/effort.tsx` | /effort 命令 UI |
| `utils/effort.ts` | `parseEffortValue()`、`getInitialEffortSetting()` |

**Qwen Code 现状**：无 effort 调节能力——所有任务使用相同的推理深度参数。

**Qwen Code 修改方向**：`settingsSchema.ts` 新增 `effort` 设置；新建 `/effort` 命令；`contentGenerator.ts` 按 effort 调整 `reasoning` 参数。

**实现成本评估**：
- 涉及文件：~4 个
- 新增代码：~200 行
- 开发周期：~2 天（1 人）
- 难点：effort 级别与模型 reasoning 参数的映射关系

**改进前后对比**：
- **改进前**：固定推理深度——简单任务也深度思考，浪费 token
- **改进后**：`/effort low` 快速回答简单问题，`/effort high` 深度推理复杂架构

**意义**：不同任务需要不同推理深度——简单任务浪费 token，复杂任务推理不够。
**缺失后果**：固定推理深度——无法灵活调整。
**改进收益**：动态 effort 级别——简单任务省 token，复杂任务深度思考。

---

<a id="item-7"></a>

### 7. Status Line 自定义（P2）

开发者在使用 Agent 时经常需要关注一些实时信息——API rate limit 剩余量、当前 git branch、CI 构建状态等。这些信息分散在不同工具中，需要手动切换窗口查看。状态栏是展示这类实时信息的最佳位置，但当前状态栏内容固定不可定制。需要支持用户配置 shell 脚本，定期执行并在状态栏展示输出。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `components/StatusLine.tsx` | shell 脚本执行 + 输出渲染 |
| settings: `statusLine` | 配置项 |

**Qwen Code 现状**：状态栏内容固定——无法展示用户自定义信息。

**Qwen Code 修改方向**：`settingsSchema.ts` 新增 `statusLine` 配置（shell 命令字符串）；`Footer.tsx` 定期执行并显示输出。

**实现成本评估**：
- 涉及文件：~3 个
- 新增代码：~150 行
- 开发周期：~2 天（1 人）
- 难点：shell 脚本执行的超时控制与安全沙箱

**改进前后对比**：
- **改进前**：状态栏固定显示——查看 rate limit 需要手动执行命令
- **改进后**：配置 `statusLine: "curl -s api/rate-limit | jq .remaining"` → 状态栏实时显示剩余额度

**意义**：状态栏是实时信息展示的最佳位置——rate limit、git branch 等。
**缺失后果**：状态栏内容固定——无法展示用户关心的自定义信息。
**改进收益**：shell 脚本自定义——展示 rate limit 用量、构建状态等。

---

<a id="item-8"></a>

### 8. 终端渲染优化（P2）

在 tmux、低性能终端或流式输出场景中，终端画面频繁闪烁——Agent 每输出一行文字，整个屏幕都重绘一次。这种闪烁不仅视觉上不舒适，还给人"工具不成熟"的印象。Claude Code 为此定制了 Ink 渲染引擎（`ink/` 目录 ~7,000 行），实现了 8 层防闪烁机制。核心技术：DEC 2026 同步输出（BSU/ESU 包裹所有输出，终端原子渲染）+ cell-level 差分（仅写变化的 cell）+ 双缓冲（frontFrame/backFrame swap）。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `ink/terminal.ts` (248行) | DEC 2026 检测（`CSI ?2026h/l`）、`writeDiffToTerminal()` |
| `ink/log-update.ts` (773行) | cell-level diff 引擎、DECSTBM 硬件滚动 |
| `ink/renderer.ts` (178行) | `frontFrame`/`backFrame` 双缓冲、`prevFrameContaminated` |
| `ink/output.ts` (797行) | Damage Tracking（dirty rectangle）、CharCache（16K cap） |
| `ink/screen.ts` (1486行) | StylePool、CharPool、HyperlinkPool |
| `ink/ink.tsx` (1722行) | 渲染节流（~60fps via `queueMicrotask`）、pool 管理 |
| `utils/fullscreen.ts` | alt-screen 切换（`CLAUDE_CODE_NO_FLICKER=1`） |

**Qwen Code 现状**：使用标准 Ink 库仅有消息拆分一种防闪烁手段——流式输出和工具执行时终端闪烁明显，尤其在 tmux/低性能终端上。

**Qwen Code 修改方向**：短期——对 Ink 的 `render()` 包裹 BSU/ESU 序列实现同步输出（最高性价比）；中期——引入 cell-level diff（参考 `ink/log-update.ts`）替代 Ink 默认的全量 rewrite。

**实现成本评估**：
- 涉及文件：~5 个（短期）/ ~15 个（中期）
- 新增代码：~200 行（短期）/ ~2000 行（中期）
- 开发周期：~3 天（短期）/ ~15 天（中期）（1 人）
- 难点：cell-level diff 算法实现、终端转义序列兼容性

**改进前后对比**：
- **改进前**：流式输出时整个屏幕频繁重绘——tmux 中闪烁明显
- **改进后**：BSU/ESU 原子渲染 + cell-level diff——仅更新变化的字符，丝滑无闪烁

**意义**：终端渲染质量直接决定用户对工具的第一感受——闪烁 = 不专业。
**缺失后果**：流式输出和工具执行时终端闪烁——尤其在 tmux/低性能终端上明显。
**改进收益**：8 层防闪烁机制——从"能用"到"丝滑"的 UX 跨越。

**相关文章**：[终端渲染与防闪烁](../tools/claude-code/11-terminal-rendering.md)

---

<a id="item-9"></a>

### 9. Image [Image #N] Chips（P2）

开发者在调试 UI 问题时可能粘贴多张截图（如登录页、注册页、设置页），然后想针对其中一张提问——"修复 [Image #1] 中的对齐问题"。当前粘贴多张图片后没有编号标记，无法在 prompt 中精确引用特定图片，Agent 无法知道开发者指的是哪一张。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `components/PromptInput/PromptInput.tsx` (L581) | `parseReferences()` + `[Image` filter |

**Qwen Code 现状**：粘贴图片后无编号标记——多张图片无法区分引用。

**Qwen Code 修改方向**：`InputPrompt.tsx` 粘贴图片时插入 `[Image #N]` 文本标记；发送时将标记替换为实际图片引用。

**实现成本评估**：
- 涉及文件：~2 个
- 新增代码：~80 行
- 开发周期：~1 天（1 人）
- 难点：图片标记与实际图片数据的映射维护

**改进前后对比**：
- **改进前**：粘贴 3 张截图后——"修复那个 bug"→ Agent 不知道指哪张图
- **改进后**：粘贴后显示 `[Image #1]` `[Image #2]` `[Image #3]`——"修复 [Image #1] 中的 bug" 精确引用

**意义**：多图场景需要精确引用特定图片。
**缺失后果**：粘贴多张图片后无法区分——'哪张图的 bug？'
**改进收益**：[Image #1] 标记——'修复 [Image #1] 中的 bug'精确引用。

---

<a id="item-10"></a>

### 10. --max-turns 限制（P2）

在 CI/CD 管道中运行 Agent 的 headless 模式时，Agent 可能陷入"修复→失败→再修复"的无限循环——CI 只能等到全局超时（通常 30 分钟）才会强制终止，期间浪费大量 token 和计算资源。需要一个精确的 turn 数限制，让 Agent 在执行 N 轮后自动停止。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `main.tsx` | `--max-turns` CLI 参数 |
| `query.ts` | turn 计数 + 超限退出 |

**Qwen Code 现状**：headless 模式无 turn 数限制——Agent 可能无限循环直到 CI 超时。

**Qwen Code 修改方向**：`nonInteractiveCli.ts` 新增 `--max-turns` 参数；`agent-core.ts` 的 `runReasoningLoop` 中按 turn 计数退出。

**实现成本评估**：
- 涉及文件：~2 个
- 新增代码：~50 行
- 开发周期：~1 天（1 人）
- 难点：turn 的精确定义（用户消息轮次 vs 工具调用轮次）

**改进前后对比**：
- **改进前**：CI 中 Agent 陷入循环 → 等待 30 分钟全局超时才停止
- **改进后**：`--max-turns 10` → Agent 最多执行 10 轮后自动停止并输出当前状态

**意义**：headless 模式需要防止无限循环——CI 不应无限运行。
**缺失后果**：Agent 可能陷入循环无限重试——CI 超时才会停。
**改进收益**：--max-turns N 精确控制——最多 N 轮后自动停止。

---

<a id="item-11"></a>

### 11. --max-budget-usd 花费上限（P2）

团队在 CI 中批量运行 Agent 任务时，某个任务可能因为反复重试或复杂推理消耗远超预期的 token 费用。没有花费上限保护意味着一次失控的运行可能花掉整个月的预算。需要在 headless 模式中设置 USD 花费上限——累计成本超过阈值时自动停止。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `main.tsx` | `--max-budget-usd` CLI 参数 |
| `cost-tracker.ts` | 累计成本检查 |

**Qwen Code 现状**：无花费上限控制——headless 模式下 token 消耗没有自动限制。

**Qwen Code 修改方向**：`nonInteractiveCli.ts` 新增 `--max-budget` 参数；每次 API 响应后检查累计 token 成本。

**实现成本评估**：
- 涉及文件：~3 个
- 新增代码：~100 行
- 开发周期：~1 天（1 人）
- 难点：实时 token 成本计算（需维护各模型的单价表）

**改进前后对比**：
- **改进前**：CI 任务失控重试 → 单次运行消耗 $50+ token 费用 → 月底账单超预算
- **改进后**：`--max-budget-usd 5` → 累计花费达 $5 时自动停止并报告已完成的工作

**意义**：headless 模式需要花费上限——防止意外高消耗。
**缺失后果**：无花费保护——一次运行可能消耗大量 token。
**改进收益**：--max-budget-usd 5 限制——超过自动停止。

---

<a id="item-12"></a>

### 12. Connectors 托管式 MCP（P2）

开发者想让 Agent 访问 GitHub Issues、Slack 消息、Linear 任务或 Google Drive 文档，需要手动配置 OAuth token、处理 token 过期刷新、解决 401 错误重试。这些配置工作繁琐且容易出错——token 过期后 Agent 静默失败，开发者不知道为什么 MCP 工具突然不工作了。需要托管式的 OAuth 连接管理，一键授权、自动刷新。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `services/mcp/client.ts` | OAuth token 管理 + 401 重试 + 连接器去重 |

**Qwen Code 现状**：MCP 连接需手动配置认证——无 OAuth 托管、无自动 token 刷新。

**Qwen Code 修改方向**：`mcp-client.ts` 扩展 OAuth 连接管理；新增托管连接器配置 UI（类似 `/mcp` 对话框）。

**实现成本评估**：
- 涉及文件：~6 个
- 新增代码：~500 行
- 开发周期：~5 天（1 人）
- 难点：多 OAuth provider 的授权流程差异、token 安全存储

**改进前后对比**：
- **改进前**：手动配置 GitHub token → token 过期 → MCP 工具静默失败 → 手动刷新
- **改进后**：`/mcp connect github` → OAuth 授权 → 自动刷新 token → 401 自动重试

**意义**：与外部服务（GitHub/Slack/Linear）的集成需要 OAuth 管理。
**缺失后果**：手动配置 token + 手动刷新——容易过期。
**改进收益**：托管式 OAuth——一键连接，自动刷新，401 自动重试。

---

<a id="item-13"></a>

### 13. MCP Auto-Reconnect（P2）

MCP 服务器在长时间运行中可能因网络抖动、服务重启或资源回收而断开连接。当前连接断开后 Agent 整个 session 的 MCP 工具都会失效——开发者需要手动重启 Agent 才能恢复。对于依赖 MCP 工具（如数据库查询、外部 API）的工作流，一次短暂的网络抖动就会中断整个工作流程。

Claude Code 的方案是连续 3 次错误后自动关闭连接并重建，SSE 传输层内置重连（maxRetries: 2），session 过期（404）时自动刷新。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `services/mcp/client.ts` (L1225-L1357) | `MAX_ERRORS_BEFORE_RECONNECT = 3`、`consecutiveConnectionErrors` 计数、SSE reconnection exhausted 检测 |
| `services/mcp/types.ts` (L211) | `reconnectAttempt?: number` |

**Qwen Code 现状**：MCP 连接断开后不会自动重连——需要手动重启 Agent 恢复 MCP 工具。

**Qwen Code 修改方向**：`mcp-client.ts` 的 `McpClient` 类新增 `consecutiveErrors` 计数；`onError` 回调中累计错误数，达到 3 次时 `close()` + 重新 `connect()`。

**实现成本评估**：
- 涉及文件：~2 个
- 新增代码：~100 行
- 开发周期：~2 天（1 人）
- 难点：重连时序控制（避免重连风暴）、session 状态恢复

**改进前后对比**：
- **改进前**：MCP 服务器短暂重启 → 连接断开 → 整个 session 的 MCP 工具失效 → 手动重启 Agent
- **改进后**：网络抖动 → 自动检测 → 3 次错误后重建连接 → 用户无感知地继续使用

**意义**：MCP 工具是 Agent 扩展能力的核心——连接中断会导致 Agent 丧失关键工具能力。
**缺失后果**：MCP 服务器短暂不可用 → Agent 整个 session 的 MCP 工具失效——需手动重启。
**改进收益**：瞬态故障自动恢复——用户无感知，Agent 持续使用 MCP 工具。

---

<a id="item-14"></a>

### 14. Tool Result 大小限制（P2）

Agent 执行 `cat` 命令读取一个 500KB 的日志文件，或者 `grep` 匹配到几千行结果——这些巨大的工具输出直接注入上下文会占满大部分窗口空间，挤占后续对话和推理的空间。更严重的是，模型可能因为上下文溢出直接报错。需要对每个工具的输出设置大小上限，超限结果持久化到磁盘，模型只收到预览和文件路径。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `Tool.ts` | `maxResultSizeChars` 工具属性 |
| 各工具（TaskStopTool/NotebookEditTool/SkillTool 等） | `maxResultSizeChars: 100_000` |

**Qwen Code 现状**：工具输出无大小限制——大结果直接注入上下文，可能导致上下文溢出。

**Qwen Code 修改方向**：`BaseDeclarativeTool` 新增 `maxResultSizeChars` 属性；工具执行后检查结果字符数，超限时写入 temp 文件 + 返回预览。

**实现成本评估**：
- 涉及文件：~4 个
- 新增代码：~150 行
- 开发周期：~2 天（1 人）
- 难点：预览内容的智能截取（头部 + 尾部 vs 头部截断）

**改进前后对比**：
- **改进前**：`cat large.log` 输出 500KB → 直接注入上下文 → 挤占后续推理空间
- **改进后**：超过 100K 字符自动写入 temp 文件 → 模型收到前 1000 行预览 + 文件路径

**意义**：单个大文件 Read 或长命令输出可能超过 100K 字符——直接塞入上下文会溢出。
**缺失后果**：大结果直接注入 → 上下文溢出或挤占其他内容空间。
**改进收益**：大结果自动persist to disk + 预览——模型需要时可 Read 完整文件，不浪费上下文。

---

<a id="item-15"></a>

### 15. Output Token 升级重试（P2）

API 请求中 `max_output_tokens` 参数决定了模型最大输出长度——设得太大会预留过多槽位增加延迟和成本，设得太小又可能截断复杂回答。实际上 99% 的响应不超过 5K tokens（BQ p99 仅 4911 tokens），但为了防截断通常默认设 32K+。需要一种"先保守后升级"的策略——首次用 8K，截断时自动用 64K 重试。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/context.ts` | `CAPPED_DEFAULT_MAX_TOKENS = 8_000`、`ESCALATED_MAX_TOKENS = 64_000` |
| `query.ts` (L1205) | `max_output_tokens_escalate` 重试逻辑 |

**Qwen Code 现状**：使用固定的 `maxOutputTokens`——每次请求都预留大量输出槽位。

**Qwen Code 修改方向**：`contentGenerator.ts` 首次请求用较小 `maxOutputTokens`；`agent-core.ts` 检测截断后自动升级重试。

**实现成本评估**：
- 涉及文件：~2 个
- 新增代码：~80 行
- 开发周期：~1 天（1 人）
- 难点：截断检测逻辑（`stop_reason === 'max_tokens'` vs 其他截断原因）

**改进前后对比**：
- **改进前**：每次请求预留 32K 输出槽位——99% 的请求实际只用 <5K，浪费延迟
- **改进后**：首次 8K → 截断时自动 64K 重试——99% 请求无额外延迟，<1% 需要一次重试

**意义**：默认 32K/64K max_output_tokens 过度预留——浪费 API 槽位容量，增加延迟。
**缺失后果**：每次请求都预留 32K+ 输出槽位——即使大多数响应 <5K tokens。
**改进收益**：8K 首次 + 64K 重试——99% 请求用 8K 就够，<1% 需要重试，总体延迟降低。

---

<a id="item-16"></a>

### 16. Ripgrep 三级回退（P2）

Agent 在 CI 容器、Docker 环境或资源受限的服务器上运行时，`rg`（ripgrep）可能未安装或因资源不足报 EAGAIN 错误。当前 `rg` 失败时搜索直接返回空结果——Agent 误认为没有匹配内容，基于错误前提继续推理。需要多级回退机制：系统 `rg` → 内嵌 `rg` → vendored 二进制，以及 EAGAIN 时自动降级为单线程重试。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/ripgrep.ts` | `isEagainError()`（L83）、`-j 1` 单线程重试（L390-391） |

**Qwen Code 现状**：依赖系统安装的 `rg`——未安装或 EAGAIN 失败时搜索直接返回空结果。

**Qwen Code 修改方向**：`ripgrepUtils.ts` 新增 EAGAIN 检测 + `-j 1` 重试；增加 rg 二进制回退链。

**实现成本评估**：
- 涉及文件：~2 个
- 新增代码：~100 行
- 开发周期：~1 天（1 人）
- 难点：vendored 二进制的多平台打包（linux-x64/arm64/darwin）

**改进前后对比**：
- **改进前**：CI 容器中 `rg` EAGAIN → 搜索返回空 → Agent 误判"代码中没有相关引用"
- **改进后**：EAGAIN → 自动 `-j 1` 单线程重试 → 搜索正常返回结果

**意义**：CI 容器和资源受限环境中 rg 可能 EAGAIN 失败——静默失败导致搜索不全。
**缺失后果**：rg EAGAIN → 搜索失败 → Agent 误认为无匹配结果。
**改进收益**：EAGAIN 自动单线程重试——资源受限环境下仍能完成搜索。

---

<a id="item-17"></a>

### 17. MAGIC DOC 自更新文档（P2）

项目文档（API 参考、架构说明、变更日志）在代码修改后容易过时——Agent 重构了一个模块的接口，但对应的 API 文档没有同步更新，新成员读到过时文档会产生误解。需要一种"标记即自动维护"的机制——在文档头部标记 `# MAGIC DOC: [title]` 后，Agent 空闲时自动检测代码变更并更新文档内容。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `services/MagicDocs/prompts.ts` | 更新 Prompt 模板（保留 header、实质性变更才更新） |
| `services/MagicDocs/` | 触发逻辑 + forked agent 调度 |

**Qwen Code 现状**：无文档自动更新机制——代码修改后文档需手动同步。

**Qwen Code 修改方向**：新建 `services/magicDocs/`；检测 `# MAGIC DOC:` header 的文件；空闲时 fork agent 执行更新。

**实现成本评估**：
- 涉及文件：~5 个
- 新增代码：~400 行
- 开发周期：~4 天（1 人）
- 难点：变更检测粒度（避免无实质变更的文档也触发更新）、forked agent 的上下文控制

**改进前后对比**：
- **改进前**：重构 UserService 接口 → API 文档仍描述旧接口 → 新成员按过时文档调用失败
- **改进后**：API 文档标记 `# MAGIC DOC: UserService API` → Agent 修改代码后自动更新文档

**意义**：项目文档（API 参考、架构说明）容易过时——Agent 修改代码后文档不同步。
**缺失后果**：代码改了但文档没更新——新成员读到过时文档。
**改进收益**：标记的文档自动保持最新——Agent 改代码后自动更新相关文档。

---

<a id="item-18"></a>

### 18. 目录/文件路径补全（P2）

开发者在 prompt 中引用文件路径时需要完整输入——像 `src/components/auth/LoginForm.tsx` 这样的深层路径打字量大且容易拼错。大型项目中文件数以千计，记住精确路径几乎不可能。需要类似 shell 的 Tab 补全——输入 `src/comp` 后按 Tab 自动补全为 `src/components/`，结合 `.gitignore` 过滤不相关文件。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/suggestions/directoryCompletion.ts` | 路径扫描 + LRU 缓存 |

**Qwen Code 现状**：无文件路径补全——用户需完整输入路径，深层目录打字量大且易出错。

**Qwen Code 修改方向**：`InputPrompt.tsx` 检测输入中的路径模式；新建 `utils/suggestions/directoryCompletion.ts` 扫描并缓存结果。

**实现成本评估**：
- 涉及文件：~3 个
- 新增代码：~250 行
- 开发周期：~2 天（1 人）
- 难点：LRU 缓存策略、大目录扫描性能、.gitignore 规则解析

**改进前后对比**：
- **改进前**：手动输入 `src/components/auth/LoginForm.tsx`——打字 40+ 个字符
- **改进后**：输入 `src/comp` + Tab → 补全为 `src/components/` → 继续 Tab 导航子目录

**意义**：文件路径是 Agent 交互中最常输入的内容——补全直接提升效率。
**缺失后果**：用户需完整输入文件路径——深层目录路径打字量大。
**改进收益**：Tab 补全路径——减少打字量，避免路径拼写错误。

---

<a id="item-19"></a>

### 19. 上下文 Tips 系统（P2）

新用户不知道 `/compress` 可以压缩上下文、`/review` 可以审查代码、`QWEN.md` 可以配置项目指令——这些功能的使用率远低于预期。需要一套上下文感知的提示系统，在合适的时机主动引导——如上下文用到 80% 时提示"试试 /compress"，检测到 VS Code 环境时推荐安装扩展。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `services/tips/tipRegistry.ts` | `getActiveNotices()` + 条件过滤 |

**Qwen Code 现状**：无上下文提示系统——功能发现完全依赖用户主动查阅文档。

**Qwen Code 修改方向**：新建 `services/tips/`；定义 tips 数组（条件 + 消息）；启动和 session 中检查条件并显示。

**实现成本评估**：
- 涉及文件：~4 个
- 新增代码：~300 行
- 开发周期：~3 天（1 人）
- 难点：提示时机的精准控制（避免过度打扰）、提示去重和频率限制

**改进前后对比**：
- **改进前**：上下文用到 95% → 突然报错"上下文溢出" → 用户不知道有 `/compress`
- **改进后**：上下文 80% 时自动提示"上下文已用 80%，试试 /compress 释放空间"

**意义**：新用户不知道可用功能——提示系统引导功能发现。
**缺失后果**：用户不知道 `/compress`、`/review` 等功能存在——使用率低。
**改进收益**：上下文提示引导——"你的上下文已用 80%，试试 /compress"。

---

<a id="item-20"></a>

### 20. 权限对话框文件预览（P2）

Agent 请求编辑文件时，权限对话框只显示"Edit file.ts?"——开发者无法看到具体要做什么修改。面对这种不透明的确认框，大多数人会选择盲目批准，这违背了权限系统的安全设计初衷。需要在权限审批对话框中显示具体的变更内容预览（diff + 语法高亮），让开发者做出知情决策。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `components/permissions/` | 文件预览 + 语法高亮 + 上下文说明 |

**Qwen Code 现状**：权限对话框仅显示工具名和文件路径——不展示变更内容预览。

**Qwen Code 修改方向**：`PermissionsDialog.tsx` 的 tool confirmation 中增加文件内容预览区域。

**实现成本评估**：
- 涉及文件：~3 个
- 新增代码：~200 行
- 开发周期：~2 天（1 人）
- 难点：diff 预览的终端渲染（行数限制、语法高亮）

**改进前后对比**：
- **改进前**：弹出"Edit file.ts?" → 看不到改什么 → 盲目批准
- **改进后**：弹出 diff 预览（删除 3 行 / 新增 5 行 + 语法高亮）→ 审查后再批准

**意义**：盲目批准权限是安全隐患——用户需看到变更内容才能做出知情决策。
**缺失后果**：用户只看到"Edit file.ts?"无法判断变更是否安全——倾向于全部批准。
**改进收益**：预览 diff 后再批准——安全审批变得有意义。

---

<a id="item-21"></a>

### 21. Token 使用实时警告（P2）

开发者在长会话中专注于对话内容，完全不知道上下文窗口已经快用完了——直到突然收到"上下文溢出"错误，之前的工作流被中断。这种"毫无预警的突然中断"体验很差。需要在 UI 中实时显示 token 使用进度，并在接近上限时分级预警（80% 黄色、90% 红色）。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `components/TokenWarning.tsx` | 实时 token 警告 + 压缩状态 |

**Qwen Code 现状**：有基础的 `ContextUsageDisplay` 显示 token 用量百分比，但无主动警告机制——用户需主动关注状态栏。

**Qwen Code 修改方向**：在 `Footer.tsx` 的 `ContextUsageDisplay` 中增加警告阈值——超过 80% 时高亮显示。

**实现成本评估**：
- 涉及文件：~2 个
- 新增代码：~80 行
- 开发周期：~1 天（1 人）
- 难点：警告样式与现有 UI 的融合、避免警告过于频繁干扰工作

**改进前后对比**：
- **改进前**：上下文默默用到 100% → 突然报错"上下文溢出" → 工作流中断
- **改进后**：80% 时黄色提示 → 90% 时红色警告 → 用户提前 `/compress`

**意义**：用户不应该被上下文溢出"突袭"——应提前可视化预警。
**缺失后果**：用户无感知地用完上下文 → 突然报错中断工作流。
**改进收益**：80% 时黄色警告 → 90% 红色警告——用户提前 /compress。

---

<a id="item-22"></a>

### 22. 快捷键提示组件（P2）

开发者使用 Agent 时不知道当前操作有哪些快捷键可用——不知道 Escape 可以取消操作、Ctrl+O 可以展开内容、Tab 可以切换选项。快捷键文档通常只在初始 `/help` 中出现一次，之后就被遗忘。需要一个统一的 `KeyboardShortcutHint` 组件，在 UI 各处的操作旁边显示对应的快捷键提示，并根据用户自定义 keybindings 动态更新。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `components/design-system/KeyboardShortcutHint.tsx` | 统一快捷键提示渲染 |
| `keybindings/useShortcutDisplay.ts` | `useShortcutDisplay()` 读取实际绑定 |

**Qwen Code 现状**：无统一快捷键提示组件——快捷键信息仅在帮助命令中显示。

**Qwen Code 修改方向**：新建 `KeyboardShortcutHint` 组件；各对话框/footer 使用统一提示；读取 keybindings 配置动态更新文本。

**实现成本评估**：
- 涉及文件：~5 个
- 新增代码：~200 行
- 开发周期：~2 天（1 人）
- 难点：提示文本与自定义 keybindings 的实时同步

**改进前后对比**：
- **改进前**：权限对话框弹出 → 不知道 Escape 可取消 → 手动输入"n"拒绝
- **改进后**：对话框底部显示"(Esc to cancel · Enter to approve)" → 一眼可见

**意义**：用户记不住所有快捷键——UI 中随处可见的提示降低学习成本。
**缺失后果**：用户不知道 Escape 可以取消、Ctrl+O 可以展开——功能可发现性差。
**改进收益**：操作旁边即显示快捷键——"边用边学"。

---

<a id="item-23"></a>

### 23. 终端完成通知（P2）

开发者让 Agent 执行耗时任务（如运行测试、大规模重构）后切换到其他窗口工作。任务完成时 Agent 只是静默停止——开发者需要反复切换回来查看是否完成，浪费大量注意力。需要通过终端原生通知机制（iTerm2/Kitty/Ghostty 各有专用 OSC 转义序列）在任务完成时主动通知开发者。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `ink/useTerminalNotification.ts` | iTerm2/Kitty/Ghostty OSC 序列 + 进度状态 |

**Qwen Code 现状**：任务完成时仅发出 bell 声音——无终端原生通知，用户需手动切回查看。

**Qwen Code 修改方向**：`attentionNotification.ts` 从仅 bell 扩展为终端类型检测 + 对应 OSC 通知序列。

**实现成本评估**：
- 涉及文件：~2 个
- 新增代码：~100 行
- 开发周期：~1 天（1 人）
- 难点：多终端模拟器的 OSC 序列差异检测

**改进前后对比**：
- **改进前**：Agent 完成任务后静默停止 → 开发者每隔几分钟切回查看 → 浪费注意力
- **改进后**：任务完成 → iTerm2 标签显示 ✓ / Kitty 弹出通知 → 无需切回即知完成

**意义**：用户切换到其他窗口后不知道 Agent 何时完成——需反复切回查看。
**缺失后果**：Agent 完成后用户不知道——浪费等待时间。
**改进收益**：终端标签显示 ✓ 或弹出通知——无需切回即知完成。

---

<a id="item-24"></a>

### 24. Spinner 工具名 + 计时（P2）

Agent 执行工具调用时，spinner 只显示通用的"Responding..."——开发者不知道 Agent 当前在做什么、已经花了多长时间。当等待超过 10 秒时，焦虑感明显——"它卡了吗？在做什么？还要等多久？"。需要 spinner 显示当前工具名和已用时间，如"Bash(npm test) · 15s"，让开发者了解执行进度。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `constants/spinnerVerbs.ts` | 工具→动词映射（"Accomplishing"/"Architecting"等） |
| `components/Spinner/SpinnerAnimationRow.tsx` | `elapsedTimeMs` 实时显示 |

**Qwen Code 现状**：spinner 显示通用的"Thinking..."——不显示当前工具名和已用时间。

**Qwen Code 修改方向**：`SpinnerLabel.tsx` 从当前执行的工具调用中提取工具名；新增 `startTime` 计时并格式化显示。

**实现成本评估**：
- 涉及文件：~2 个
- 新增代码：~100 行
- 开发周期：~1 天（1 人）
- 难点：工具名的友好显示映射（避免暴露内部工具 ID）

**改进前后对比**：
- **改进前**：spinner 显示"Thinking..."持续 30 秒 → 不知道在做什么 → 焦虑
- **改进后**：spinner 显示"Bash(npm test) · 15s" → 知道在跑测试、已经 15 秒了

**意义**：用户不知道 Agent 在做什么、要等多久——焦虑感强。
**缺失后果**：只看到通用 spinner——"它卡了吗？还在跑吗？"
**改进收益**：看到"Bash(npm test) · 15s"——知道在做什么、花了多久。

---

<a id="item-25"></a>

### 25. /rewind 检查点回退（P2）

Agent 执行了 5 步操作后，开发者发现第 3 步的方向就错了。用 `git checkout` 只能回退所有文件到某个 commit——无法保留第 4-5 步中部分有用的修改（比如新增的测试文件）。需要一个精确的检查点回退机制——展示每个检查点的变更摘要，开发者选择回退到特定点，同时可以选择性保留后续有用的变更。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `commands/rewind/index.ts` | /rewind（别名 checkpoint）命令 |
| `utils/fileHistory.ts` | snapshot 恢复逻辑 |

**Qwen Code 现状**：有基础的 checkpointing（git worktree）但无交互式回退命令——回退需手动操作 git。

**Qwen Code 修改方向**：新建 `/rewind` 命令；结合已有 checkpointing（git worktree）实现交互式回退。

**实现成本评估**：
- 涉及文件：~4 个
- 新增代码：~300 行
- 开发周期：~3 天（1 人）
- 难点：检查点选择器 UI、选择性保留后续变更的 merge 逻辑

**改进前后对比**：
- **改进前**：第 3 步错了 → `git checkout` 回退全部 → 第 4-5 步的有用修改也丢了
- **改进后**：`/rewind` → 选择检查点 3 → 回退代码 → 可选保留第 4-5 步的测试文件

**意义**：Agent 执行到第 5 步发现第 3 步就错了——需要精确回退。
**缺失后果**：只能 git checkout 回退全部——无法保留第 4-5 步的部分有用工作。
**改进收益**：选择检查点精确回退——保留有用变更，撤销错误变更。

---

<a id="item-26"></a>

### 26. /copy OSC 52 剪贴板（P2）

通过 SSH 连接远程服务器使用 Agent 时，终端的 Ctrl+C 复制功能无法跨网络工作——Agent 输出的代码片段、配置示例等内容无法直接复制到本地剪贴板。开发者只能手动选择文本并依赖终端模拟器的复制功能，长文本经常选不全。OSC 52 转义序列可以解决这个问题——它允许终端程序直接写入客户端剪贴板。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `commands/copy/copy.tsx` | OSC 52 剪贴板 + temp 文件回退 |

**Qwen Code 现状**：无 `/copy` 命令——远程环境中复制 Agent 输出需要手动选择文本。

**Qwen Code 修改方向**：新建 `/copy` 命令；`process.stdout.write('\x1b]52;c;' + base64(content) + '\x07')` 实现 OSC 52。

**实现成本评估**：
- 涉及文件：~2 个
- 新增代码：~80 行
- 开发周期：~1 天（1 人）
- 难点：终端 OSC 52 支持检测、不支持时的 temp 文件回退

**改进前后对比**：
- **改进前**：SSH 远程环境 → Agent 输出 200 行代码 → 手动选择文本复制 → 选不全或多选
- **改进后**：`/copy` → 一键写入本地剪贴板 → 不支持 OSC 52 时自动保存到 temp 文件

**意义**：SSH 远程环境中无法 Ctrl+C 复制终端内容——/copy 是唯一途径。
**缺失后果**：远程用户无法复制 Agent 输出——需手动选择文本。
**改进收益**：`/copy` 一键复制到本地剪贴板——SSH 环境无障碍。

---

<a id="item-27"></a>

### 27. 首次运行引导向导（P2）

新用户首次运行 Agent 时面对一个空白的终端界面——不知道如何认证、不知道有 QWEN.md 配置文件、不知道权限模式的含义。大部分新用户在前 5 分钟内决定是否继续使用——糟糕的首次体验直接导致用户流失。需要一个多步引导向导，在首次运行时引导用户完成主题选择、认证配置、安全设置等关键步骤。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `components/Onboarding.tsx` | 多步引导 UI |
| `utils/config.ts` | `checkHasTrustDialogAccepted()` |

**Qwen Code 现状**：首次运行无引导——新用户直接进入空白交互界面，需自行探索功能。

**Qwen Code 修改方向**：`gemini.tsx` 首次运行检测 → 新建 `Onboarding.tsx` 多步向导组件。

**实现成本评估**：
- 涉及文件：~4 个
- 新增代码：~350 行
- 开发周期：~3 天（1 人）
- 难点：向导步骤的流程控制、各步骤完成状态的持久化

**改进前后对比**：
- **改进前**：首次运行 → 空白终端 → 不知道如何认证 → 不知道有 QWEN.md → 流失
- **改进后**：首次运行 → 3 步引导（认证 → 安全设置 → 项目配置提示）→ 3 分钟上手

**意义**：第一印象决定工具留存率——无引导的首次体验让新用户迷茫。
**缺失后果**：新用户不知道如何认证、不知道有 QWEN.md、不知道权限模式——流失。
**改进收益**：3 分钟引导完成所有设置——新用户即刻高效使用。

---

<a id="item-28"></a>

### 28. /doctor 诊断工具（P2）

开发者遇到 Agent 异常行为时（如命令执行失败、MCP 连接不上、权限配置无效），不知道从哪里开始排查。问题可能出在 git 版本太旧、Node.js 不兼容、shell 配置冲突、代理设置错误等任何环节。需要一个一键诊断工具，自动检查所有环境依赖并输出可操作的修复建议。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/doctorDiagnostic.ts` | 环境检查 + 修复建议 |

**Qwen Code 现状**：无环境诊断工具——异常排查需手动逐项检查系统依赖。

**Qwen Code 修改方向**：新建 `/doctor` 命令；检查 git/node/shell/rg 版本 + MCP 连接 + 权限配置。

**实现成本评估**：
- 涉及文件：~3 个
- 新增代码：~250 行
- 开发周期：~2 天（1 人）
- 难点：各检查项的版本兼容性判断规则、修复建议的准确性

**改进前后对比**：
- **改进前**：Agent 异常 → 手动检查 git 版本 → 检查 Node.js → 检查代理 → 逐项排查
- **改进后**：`/doctor` → 5 秒扫描全部依赖 → 输出"git 2.30+ required, current: 2.25 → brew upgrade git"

**意义**：用户遇到问题时不知如何诊断——/doctor 一键定位。
**缺失后果**：环境问题导致 Agent 异常——用户需手动逐项排查。
**改进收益**：`/doctor` 5 秒列出所有问题 + 修复建议——自助排障。

---

<a id="item-29"></a>

### 29. 结构化 Diff 渲染（P2）

Agent 编辑文件后展示的 diff 是基础的 inline 格式——没有行号、没有语法高亮、没有 gutter 列区分增删。在大变更（50+ 行修改）时，这种基础 diff 难以快速定位关键修改，开发者可能遗漏重要的逻辑变更。需要类似 GitHub PR 的结构化 diff 渲染——行号 gutter + 语法高亮 + 颜色区分增删。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `components/StructuredDiff.tsx` | diff 渲染 UI |
| `native-ts/color-diff/` | Rust NAPI 着色 |

**Qwen Code 现状**：文件编辑后展示基础 inline diff——无行号、无语法高亮、大变更时可读性差。

**Qwen Code 修改方向**：`ToolMessage.tsx` 中编辑结果展示替换为结构化 diff 组件（可用 JS diff 库替代 Rust NAPI）。

**实现成本评估**：
- 涉及文件：~3 个
- 新增代码：~300 行
- 开发周期：~3 天（1 人）
- 难点：终端中的语法高亮渲染性能、多语言 tokenizer 集成

**改进前后对比**：
- **改进前**：50 行修改的 inline diff → 红绿交替的纯文本 → 关键修改容易遗漏
- **改进后**：行号 gutter + 语法高亮 + 增删颜色 → 类似 GitHub PR 的阅读体验

**意义**：Diff 是用户审查 Agent 变更的核心界面——可读性直接影响审查质量。
**缺失后果**：基础 inline diff 在大变更时难以阅读——用户可能遗漏关键修改。
**改进收益**：行号 + 着色 + gutter——变更一目了然，审查效率提升。

---
