# Qwen Code 改进建议 — P2 工具与命令扩展

> 中等优先级改进项。每项包含：思路概述、Claude Code 源码索引、Qwen Code 修改方向。
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md)

---

<a id="item-1"></a>

### 1. Conditional Hooks（P2）

**思路**：Hook 支持 `if` 字段——使用权限规则语法过滤何时执行（如 `Bash(git:*)` 仅在 git 命令时触发）。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/hooks/hookRunner.ts` | `if` 字段匹配逻辑 |
| `types/hooks.ts` | `HookConfig.if` 字段定义 |

**Qwen Code 修改方向**：`hookRunner.ts` 执行前检查 `hook.if` 条件；复用权限规则匹配器（`permission-manager.ts`）。

**意义**：Hook 需要按场景过滤——不是所有工具调用都应触发所有 hook。
**缺失后果**：所有匹配事件都触发——无法精细控制。
**改进收益**：if 条件过滤——'仅在 git 命令时运行 pre-commit 检查'。

---

<a id="item-2"></a>

### 2. Transcript Search（P2）

**思路**：transcript 模式下按 `/` 进入搜索，输入关键词后 `n`/`N` 在匹配项间导航。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `components/Messages/` | transcript 搜索 UI + 高亮 |

**Qwen Code 修改方向**：`HistoryItemDisplay.tsx` 新增搜索状态；`KeypressContext` 拦截 `/` 键进入搜索模式。

**意义**：长会话中回忆之前的讨论是常见需求。
**缺失后果**：需手动滚动查找——'刚才说的那个 API 是什么？'
**改进收益**：/ 搜索 + n/N 导航——快速定位历史讨论。

---

<a id="item-3"></a>

### 3. Bash File Watcher（P2）

**思路**：检测 formatter/linter 在 Agent 读取文件后修改了该文件——Agent 基于旧内容编辑会冲突。发出警告并建议重新 Read。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `tools/BashTool/` | 文件 mtime 比对逻辑 |
| `utils/fileStateCache.ts` | 已读文件状态缓存 |

**Qwen Code 修改方向**：`edit.ts` 编辑前比对文件 mtime 与上次 read 时的 mtime；不一致时警告并建议 re-read。

**意义**：formatter/linter 在 Agent 读取文件后可能自动修改——导致编辑冲突。
**缺失后果**：Agent 基于旧内容编辑 → 覆盖 formatter 的修改 → 格式丢失。
**改进收益**：自动检测文件被外部修改 → 提醒 re-read——避免 stale-edit。

---

<a id="item-4"></a>

### 4. /batch 并行操作（P2）

**思路**：编排大规模并行变更——将任务拆分为多个子任务，fork 多个 Agent 并行执行，汇总结果。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `skills/bundled/batch.ts` | /batch bundled skill |

**Qwen Code 修改方向**：新建 `skills/bundled/batch/SKILL.md`；核心逻辑是解析用户输入 → 拆分 → fork 多个 Agent → 汇总。

**意义**：大规模重构（如'所有 class 组件迁移到 hooks'）需要并行处理多文件。
**缺失后果**：只能逐文件处理——大规模重构耗时长。
**改进收益**：并行拆分执行——多文件同时处理，速度倍增。

---

<a id="item-5"></a>

### 5. Chrome Extension 浏览器调试（P2）

**思路**：Chrome 扩展通过 MCP 协议桥接——提供 `read_page`（DOM）、`read_console_messages`（Console）、`read_network_requests`（Network）、`navigate`、`switch_browser` 工具。通过 `/web-setup` 配置。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/claudeInChrome/mcpServer.ts` | Chrome MCP Server |
| `utils/claudeInChrome/chromeNativeHost.ts` | Native Messaging Host |

**Qwen Code 修改方向**：开发 Chrome 扩展 + Native Messaging Host；注册为 MCP Server（tools: read_page/read_console/navigate）。

**意义**：前端调试需要 Agent 看到浏览器渲染结果和错误日志。
**缺失后果**：Agent 无法'看到'浏览器——前端 bug 只能靠描述。
**改进收益**：直接读取 DOM/Console/Network——前端调试效率大幅提升。

---

<a id="item-6"></a>

### 6. /effort 命令（P2）

**思路**：动态设置模型 effort 级别（低 ○ / 中 ◐ / 高 ●）——影响推理深度和 token 消耗。显示在 prompt bar 和 spinner 上。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `commands/effort/effort.tsx` | /effort 命令 UI |
| `utils/effort.ts` | `parseEffortValue()`、`getInitialEffortSetting()` |

**Qwen Code 修改方向**：`settingsSchema.ts` 新增 `effort` 设置；新建 `/effort` 命令；`contentGenerator.ts` 按 effort 调整 `reasoning` 参数。

**意义**：不同任务需要不同推理深度——简单任务浪费 token，复杂任务推理不够。
**缺失后果**：固定推理深度——无法灵活调整。
**改进收益**：动态 effort 级别——简单任务省 token，复杂任务深度思考。

---

<a id="item-7"></a>

### 7. Status Line 自定义（P2）

**思路**：用户配置 shell 脚本在状态栏展示自定义信息（如 rate limit 用量、git branch、构建状态）。脚本定期执行，输出显示在 footer。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `components/StatusLine.tsx` | shell 脚本执行 + 输出渲染 |
| settings: `statusLine` | 配置项 |

**Qwen Code 修改方向**：`settingsSchema.ts` 新增 `statusLine` 配置（shell 命令字符串）；`Footer.tsx` 定期执行并显示输出。

**意义**：状态栏是实时信息展示的最佳位置——rate limit、git branch 等。
**缺失后果**：状态栏内容固定——无法展示用户关心的自定义信息。
**改进收益**：shell 脚本自定义——展示 rate limit 用量、构建状态等。

---

<a id="item-8"></a>

### 8. 终端渲染优化（P2）

**思路**：Claude Code 定制了 Ink 渲染引擎（`ink/` 目录 ~7,000 行），实现 8 层防闪烁机制。Qwen Code 使用标准 Ink 库仅有消息拆分一种防闪烁手段。核心技术：DEC 2026 同步输出（BSU/ESU 包裹所有输出，终端原子渲染）+ cell-level 差分（仅写变化的 cell）+ 双缓冲（frontFrame/backFrame swap）。

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

**Qwen Code 修改方向**：短期——对 Ink 的 `render()` 包裹 BSU/ESU 序列实现同步输出（最高性价比）；中期——引入 cell-level diff（参考 `ink/log-update.ts`）替代 Ink 默认的全量 rewrite。

**意义**：终端渲染质量直接决定用户对工具的第一感受——闪烁 = 不专业。
**缺失后果**：流式输出和工具执行时终端闪烁——尤其在 tmux/低性能终端上明显。
**改进收益**：8 层防闪烁机制——从"能用"到"丝滑"的 UX 跨越。

**相关文章**：[终端渲染与防闪烁](../tools/claude-code/11-terminal-rendering.md)

---

<a id="item-9"></a>

### 9. Image [Image #N] Chips（P2）

**思路**：粘贴图片后在输入框生成 `[Image #1]`、`[Image #2]` 位置标记——用户可在 prompt 中引用特定图片（"修复 [Image #1] 中的 bug"）。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `components/PromptInput/PromptInput.tsx` (L581) | `parseReferences()` + `[Image` filter |

**Qwen Code 修改方向**：`InputPrompt.tsx` 粘贴图片时插入 `[Image #N]` 文本标记；发送时将标记替换为实际图片引用。

**意义**：多图场景需要精确引用特定图片。
**缺失后果**：粘贴多张图片后无法区分——'哪张图的 bug？'
**改进收益**：[Image #1] 标记——'修复 [Image #1] 中的 bug'精确引用。

---

<a id="item-10"></a>

### 10. --max-turns 限制（P2）

**思路**：headless 模式 `--max-turns N` 限制最大 agentic turn 数——防止无限循环，CI 精确控制执行范围。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `main.tsx` | `--max-turns` CLI 参数 |
| `query.ts` | turn 计数 + 超限退出 |

**Qwen Code 修改方向**：`nonInteractiveCli.ts` 新增 `--max-turns` 参数；`agent-core.ts` 的 `runReasoningLoop` 中按 turn 计数退出。

**意义**：headless 模式需要防止无限循环——CI 不应无限运行。
**缺失后果**：Agent 可能陷入循环无限重试——CI 超时才会停。
**改进收益**：--max-turns N 精确控制——最多 N 轮后自动停止。

---

<a id="item-11"></a>

### 11. --max-budget-usd 花费上限（P2）

**思路**：headless 模式 `--max-budget-usd N` 限制 USD 花费——累计超过阈值自动停止。防止意外高消耗。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `main.tsx` | `--max-budget-usd` CLI 参数 |
| `cost-tracker.ts` | 累计成本检查 |

**Qwen Code 修改方向**：`nonInteractiveCli.ts` 新增 `--max-budget` 参数；每次 API 响应后检查累计 token 成本。

**意义**：headless 模式需要花费上限——防止意外高消耗。
**缺失后果**：无花费保护——一次运行可能消耗大量 token。
**改进收益**：--max-budget-usd 5 限制——超过自动停止。

---

<a id="item-12"></a>

### 12. Connectors 托管式 MCP（P2）

**思路**：托管式 MCP 连接——OAuth 认证的 GitHub/Slack/Linear/Google Drive 等连接器。处理 token 刷新、401 重试、连接器去重（本地优先）。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `services/mcp/client.ts` | OAuth token 管理 + 401 重试 + 连接器去重 |

**Qwen Code 修改方向**：`mcp-client.ts` 扩展 OAuth 连接管理；新增托管连接器配置 UI（类似 `/mcp` 对话框）。

**意义**：与外部服务（GitHub/Slack/Linear）的集成需要 OAuth 管理。
**缺失后果**：手动配置 token + 手动刷新——容易过期。
**改进收益**：托管式 OAuth——一键连接，自动刷新，401 自动重试。

---

<a id="item-13"></a>

### 13. MCP Auto-Reconnect（P2）

**思路**：MCP 服务器连接不稳定（网络抖动、服务重启）时自动重连——连续 3 次错误后关闭连接并重建。SSE 传输层内置重连（maxRetries: 2），session 过期（404）时自动刷新。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `services/mcp/client.ts` (L1225-L1357) | `MAX_ERRORS_BEFORE_RECONNECT = 3`、`consecutiveConnectionErrors` 计数、SSE reconnection exhausted 检测 |
| `services/mcp/types.ts` (L211) | `reconnectAttempt?: number` |

**Qwen Code 修改方向**：`mcp-client.ts` 的 `McpClient` 类新增 `consecutiveErrors` 计数；`onError` 回调中累计错误数，达到 3 次时 `close()` + 重新 `connect()`。

**意义**：MCP 工具是 Agent 扩展能力的核心——连接中断会导致 Agent 丧失关键工具能力。
**缺失后果**：MCP 服务器短暂不可用 → Agent 整个 session 的 MCP 工具失效——需手动重启。
**改进收益**：瞬态故障自动恢复——用户无感知，Agent 持续使用 MCP 工具。

---

<a id="item-14"></a>

### 14. Tool Result 大小限制（P2）

**思路**：每个工具定义 `maxResultSizeChars`（如 100K 字符）。超限结果持久化到磁盘文件，模型收到预览 + 文件路径而非完整内容——防止单个巨大工具结果占满上下文。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `Tool.ts` | `maxResultSizeChars` 工具属性 |
| 各工具（TaskStopTool/NotebookEditTool/SkillTool 等） | `maxResultSizeChars: 100_000` |

**Qwen Code 修改方向**：`BaseDeclarativeTool` 新增 `maxResultSizeChars` 属性；工具执行后检查结果字符数，超限时写入 temp 文件 + 返回预览。

**意义**：单个大文件 Read 或长命令输出可能超过 100K 字符——直接塞入上下文会溢出。
**缺失后果**：大结果直接注入 → 上下文溢出或挤占其他内容空间。
**改进收益**：大结果自动persist to disk + 预览——模型需要时可 Read 完整文件，不浪费上下文。

---

<a id="item-15"></a>

### 15. Output Token 升级重试（P2）

**思路**：首次请求用保守的 `max_output_tokens = 8_000`（BQ p99 仅 4911 tokens）。如果 `stop_reason === 'max_tokens'`，自动用 `64_000` 重试一次——避免默认预留过多槽位。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/context.ts` | `CAPPED_DEFAULT_MAX_TOKENS = 8_000`、`ESCALATED_MAX_TOKENS = 64_000` |
| `query.ts` (L1205) | `max_output_tokens_escalate` 重试逻辑 |

**Qwen Code 修改方向**：`contentGenerator.ts` 首次请求用较小 `maxOutputTokens`；`agent-core.ts` 检测截断后自动升级重试。

**意义**：默认 32K/64K max_output_tokens 过度预留——浪费 API 槽位容量，增加延迟。
**缺失后果**：每次请求都预留 32K+ 输出槽位——即使大多数响应 <5K tokens。
**改进收益**：8K 首次 + 64K 重试——99% 请求用 8K 就够，<1% 需要重试，总体延迟降低。

---

<a id="item-16"></a>

### 16. Ripgrep 三级回退（P2）

**思路**：Grep 工具解析 `rg` 二进制通过三级回退：系统安装 → Bun 内嵌 → 平台特定 vendored 二进制。EAGAIN 错误（资源不足）时自动用 `-j 1`（单线程）重试。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/ripgrep.ts` | `isEagainError()`（L83）、`-j 1` 单线程重试（L390-391） |

**Qwen Code 修改方向**：`ripgrepUtils.ts` 新增 EAGAIN 检测 + `-j 1` 重试；增加 rg 二进制回退链。

**意义**：CI 容器和资源受限环境中 rg 可能 EAGAIN 失败——静默失败导致搜索不全。
**缺失后果**：rg EAGAIN → 搜索失败 → Agent 误认为无匹配结果。
**改进收益**：EAGAIN 自动单线程重试——资源受限环境下仍能完成搜索。

---

<a id="item-17"></a>

### 17. MAGIC DOC 自更新文档（P2）

**思路**：标记 `# MAGIC DOC: [title]` 的 markdown 文件在 Agent 空闲时自动更新。后台 forked subagent 读取文件 + 项目上下文 → 更新内容。单文件范围限制防止越界。支持自定义 prompt（`~/.claude/magic-docs/prompt.md`）。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `services/MagicDocs/prompts.ts` | 更新 Prompt 模板（保留 header、实质性变更才更新） |
| `services/MagicDocs/` | 触发逻辑 + forked agent 调度 |

**Qwen Code 修改方向**：新建 `services/magicDocs/`；检测 `# MAGIC DOC:` header 的文件；空闲时 fork agent 执行更新。

**意义**：项目文档（API 参考、架构说明）容易过时——Agent 修改代码后文档不同步。
**缺失后果**：代码改了但文档没更新——新成员读到过时文档。
**改进收益**：标记的文档自动保持最新——Agent 改代码后自动更新相关文档。

---

<a id="item-18"></a>

### 18. 目录/文件路径补全（P2）

**思路**：输入含 `/` 或 `./` 时触发文件路径补全——扫描目录 + LRU 缓存避免重复 I/O。结合 `.gitignore` 过滤不相关文件。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/suggestions/directoryCompletion.ts` | 路径扫描 + LRU 缓存 |

**Qwen Code 修改方向**：`InputPrompt.tsx` 检测输入中的路径模式；新建 `utils/suggestions/directoryCompletion.ts` 扫描并缓存结果。

**意义**：文件路径是 Agent 交互中最常输入的内容——补全直接提升效率。
**缺失后果**：用户需完整输入文件路径——深层目录路径打字量大。
**改进收益**：Tab 补全路径——减少打字量，避免路径拼写错误。

---

<a id="item-19"></a>

### 19. 上下文 Tips 系统（P2）

**思路**：基于当前配置、IDE 类型、插件状态、session 历史等条件动态显示提示（如"检测到 VS Code，推荐安装 Claude Code 扩展"）。Tips 注册表管理所有提示及其触发条件。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `services/tips/tipRegistry.ts` | `getActiveNotices()` + 条件过滤 |

**Qwen Code 修改方向**：新建 `services/tips/`；定义 tips 数组（条件 + 消息）；启动和 session 中检查条件并显示。

**意义**：新用户不知道可用功能——提示系统引导功能发现。
**缺失后果**：用户不知道 `/compress`、`/review` 等功能存在——使用率低。
**改进收益**：上下文提示引导——"你的上下文已用 80%，试试 /compress"。

---

<a id="item-20"></a>

### 20. 权限对话框文件预览（P2）

**思路**：权限审批对话框中显示将被操作的文件内容预览 + 语法高亮——用户看到具体变更内容再决定是否批准。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `components/permissions/` | 文件预览 + 语法高亮 + 上下文说明 |

**Qwen Code 修改方向**：`PermissionsDialog.tsx` 的 tool confirmation 中增加文件内容预览区域。

**意义**：盲目批准权限是安全隐患——用户需看到变更内容才能做出知情决策。
**缺失后果**：用户只看到"Edit file.ts?"无法判断变更是否安全——倾向于全部批准。
**改进收益**：预览 diff 后再批准——安全审批变得有意义。

---

<a id="item-21"></a>

### 21. Token 使用实时警告（P2）

**思路**：在 UI 中实时显示 token 使用量、压缩进度、错误计数。不是在 `/stats` 命令中查看，而是在操作过程中自动浮现警告。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `components/TokenWarning.tsx` | 实时 token 警告 + 压缩状态 |

**Qwen Code 修改方向**：在 `Footer.tsx` 的 `ContextUsageDisplay` 中增加警告阈值——超过 80% 时高亮显示。

**意义**：用户不应该被上下文溢出"突袭"——应提前可视化预警。
**缺失后果**：用户无感知地用完上下文 → 突然报错中断工作流。
**改进收益**：80% 时黄色警告 → 90% 红色警告——用户提前 /compress。

---

<a id="item-22"></a>

### 22. 快捷键提示组件（P2）

**思路**：统一的 `KeyboardShortcutHint` 组件在 UI 各处显示当前操作的快捷方式（如 "(Ctrl+O to expand)"），且会根据用户自定义 keybindings 动态更新显示。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `components/design-system/KeyboardShortcutHint.tsx` | 统一快捷键提示渲染 |
| `keybindings/useShortcutDisplay.ts` | `useShortcutDisplay()` 读取实际绑定 |

**Qwen Code 修改方向**：新建 `KeyboardShortcutHint` 组件；各对话框/footer 使用统一提示；读取 keybindings 配置动态更新文本。

**意义**：用户记不住所有快捷键——UI 中随处可见的提示降低学习成本。
**缺失后果**：用户不知道 Escape 可以取消、Ctrl+O 可以展开——功能可发现性差。
**改进收益**：操作旁边即显示快捷键——"边用边学"。

---

<a id="item-23"></a>

### 23. 终端完成通知（P2）

**思路**：后台任务完成时通过 OSC 转义序列通知终端——iTerm2 notification、Kitty notification、Ghostty notification 各有专用 OSC。同时上报进度百分比，终端标签可显示进度。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `ink/useTerminalNotification.ts` | iTerm2/Kitty/Ghostty OSC 序列 + 进度状态 |

**Qwen Code 修改方向**：`attentionNotification.ts` 从仅 bell 扩展为终端类型检测 + 对应 OSC 通知序列。

**意义**：用户切换到其他窗口后不知道 Agent 何时完成——需反复切回查看。
**缺失后果**：Agent 完成后用户不知道——浪费等待时间。
**改进收益**：终端标签显示 ✓ 或弹出通知——无需切回即知完成。

---

<a id="item-24"></a>

### 24. Spinner 工具名 + 计时（P2）

**思路**：Spinner 不再只显示"Responding"，而是显示当前执行的工具名 + 已用时间——如"Bash(npm test) · 15s"。工具名从 `spinnerVerbs.ts` 的动词表中选择友好显示。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `constants/spinnerVerbs.ts` | 工具→动词映射（"Accomplishing"/"Architecting"等） |
| `components/Spinner/SpinnerAnimationRow.tsx` | `elapsedTimeMs` 实时显示 |

**Qwen Code 修改方向**：`SpinnerLabel.tsx` 从当前执行的工具调用中提取工具名；新增 `startTime` 计时并格式化显示。

**意义**：用户不知道 Agent 在做什么、要等多久——焦虑感强。
**缺失后果**：只看到通用 spinner——"它卡了吗？还在跑吗？"
**改进收益**：看到"Bash(npm test) · 15s"——知道在做什么、花了多久。

---

<a id="item-25"></a>

### 25. /rewind 检查点回退（P2）

**思路**：`/rewind` 命令恢复代码和对话到之前的检查点——结合 file history snapshots 和 git 状态。交互式检查点选择器展示每个点的变更摘要。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `commands/rewind/index.ts` | /rewind（别名 checkpoint）命令 |
| `utils/fileHistory.ts` | snapshot 恢复逻辑 |

**Qwen Code 修改方向**：新建 `/rewind` 命令；结合已有 checkpointing（git worktree）实现交互式回退。

**意义**：Agent 执行到第 5 步发现第 3 步就错了——需要精确回退。
**缺失后果**：只能 git checkout 回退全部——无法保留第 4-5 步的部分有用工作。
**改进收益**：选择检查点精确回退——保留有用变更，撤销错误变更。

---

<a id="item-26"></a>

### 26. /copy OSC 52 剪贴板（P2）

**思路**：`/copy` 命令通过 OSC 52 转义序列将内容写入系统剪贴板——SSH 远程环境也能工作。终端不支持 OSC 52 时自动回退到 temp 文件 + 提示路径。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `commands/copy/copy.tsx` | OSC 52 剪贴板 + temp 文件回退 |

**Qwen Code 修改方向**：新建 `/copy` 命令；`process.stdout.write('\x1b]52;c;' + base64(content) + '\x07')` 实现 OSC 52。

**意义**：SSH 远程环境中无法 Ctrl+C 复制终端内容——/copy 是唯一途径。
**缺失后果**：远程用户无法复制 Agent 输出——需手动选择文本。
**改进收益**：`/copy` 一键复制到本地剪贴板——SSH 环境无障碍。

---

<a id="item-27"></a>

### 27. 首次运行引导向导（P2）

**思路**：首次运行显示多步引导——主题选择 → 认证（OAuth/API Key）→ 安全设置 → 终端优化建议。每步有分析追踪确保完成率。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `components/Onboarding.tsx` | 多步引导 UI |
| `utils/config.ts` | `checkHasTrustDialogAccepted()` |

**Qwen Code 修改方向**：`gemini.tsx` 首次运行检测 → 新建 `Onboarding.tsx` 多步向导组件。

**意义**：第一印象决定工具留存率——无引导的首次体验让新用户迷茫。
**缺失后果**：新用户不知道如何认证、不知道有 QWEN.md、不知道权限模式——流失。
**改进收益**：3 分钟引导完成所有设置——新用户即刻高效使用。

---

<a id="item-28"></a>

### 28. /doctor 诊断工具（P2）

**思路**：`/doctor` 检查系统环境健康——git 版本、Node.js/Bun 版本、shell 类型、权限配置、代理设置、MCP 服务器状态。输出可操作的修复建议。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/doctorDiagnostic.ts` | 环境检查 + 修复建议 |

**Qwen Code 修改方向**：新建 `/doctor` 命令；检查 git/node/shell/rg 版本 + MCP 连接 + 权限配置。

**意义**：用户遇到问题时不知如何诊断——/doctor 一键定位。
**缺失后果**：环境问题导致 Agent 异常——用户需手动逐项排查。
**改进收益**：`/doctor` 5 秒列出所有问题 + 修复建议——自助排障。

---

<a id="item-29"></a>

### 29. 结构化 Diff 渲染（P2）

**思路**：文件编辑后展示结构化 diff——Rust NAPI 快速着色 + 行号 gutter 列 + 语法高亮。比基础 inline diff 更易读。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `components/StructuredDiff.tsx` | diff 渲染 UI |
| `native-ts/color-diff/` | Rust NAPI 着色 |

**Qwen Code 修改方向**：`ToolMessage.tsx` 中编辑结果展示替换为结构化 diff 组件（可用 JS diff 库替代 Rust NAPI）。

**意义**：Diff 是用户审查 Agent 变更的核心界面——可读性直接影响审查质量。
**缺失后果**：基础 inline diff 在大变更时难以阅读——用户可能遗漏关键修改。
**改进收益**：行号 + 着色 + gutter——变更一目了然，审查效率提升。

---
