# Qwen Code 改进建议 — P2 稳定性、安全与 CI/CD

> 中等优先级改进项。每项包含：思路概述、Claude Code 源码索引、Qwen Code 修改方向。
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md)

---

<a id="item-1"></a>

### 1. Bash 交互提示卡顿检测（P2）

**思路**：后台每 5 秒检查 shell 输出增长。如果 45 秒内无新输出，读取最后 1024 字节检测交互式提示（`(y/n)`、`Press Enter`、`password:` 等 regex）。检测到卡顿后向用户队列发送 `TASK_NOTIFICATION` 提醒处理。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `tasks/LocalShellTask/LocalShellTask.tsx` (L24-100) | `STALL_CHECK_INTERVAL_MS = 5s`、`STALL_THRESHOLD_MS = 45s`、`STALL_TAIL_BYTES = 1024` |
| `tasks/LocalShellTask/LocalShellTask.tsx` (L32-38) | `looksLikePrompt()` regex 匹配交互式提示 |

**Qwen Code 修改方向**：shell 工具执行后仅等待退出码，无输出监控。改进方向：① 后台 5s 轮询 shell 输出文件大小；② 45s 无增长时读取尾部匹配 prompt 模式；③ 检测到交互提示后通知用户（`stdin` 需要输入或 kill 进程）。

**意义**：`npm install` 弹出 `Do you want to continue? (y/n)` 导致 Agent 永远等待。
**缺失后果**：交互式 prompt 卡住 = 任务永久挂起——用户不知道在等什么。
**改进收益**：45s 检测 + 自动通知——用户立即知道需要手动输入或终止。

---

<a id="item-2"></a>

### 2. TTY 孤儿进程检测（P2）

**思路**：macOS 终端关闭有时不发 SIGHUP。每 30 秒检查 TTY 是否仍可读——如果 `process.stdin` 变为不可读，说明终端已关闭，触发优雅退出。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/gracefulShutdown.ts` (L278-296) | 30s 定时器检查 TTY 有效性、检测到 revoked TTY 时 `gracefulShutdown(0)` |

**Qwen Code 修改方向**：无 TTY 存活检测——终端关闭后进程变成孤儿（消耗 CPU/内存直到被 kill）。改进方向：① `setInterval(30000)` 检查 `process.stdin.isTTY`；② TTY 不可读时触发优雅关闭；③ timer 标记 `.unref()` 不阻止进程退出。

**意义**：终端窗口意外关闭（或 SSH 断开）后进程应自动退出而非变成僵尸。
**缺失后果**：终端关闭 → 进程变孤儿 → 消耗资源直到手动 kill。
**改进收益**：30s 检测 → 自动退出——无孤儿进程，资源自动释放。

---

<a id="item-3"></a>

### 3. MCP 服务器优雅关闭升级（P2）

**思路**：3 阶段升级关闭——100ms 发 SIGINT（给服务器处理清理的机会）→ 400ms 无响应发 SIGTERM → 500ms+ 仍存活发 SIGKILL。通过 `process.kill(pid, 0)` 检测进程是否存活。总超时 600ms。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `services/mcp/client.ts` (L1425-1560) | 3 阶段升级：SIGINT(100ms) → SIGTERM(400ms) → SIGKILL(500ms+) |

**Qwen Code 修改方向**：`McpClient.disconnect()` 直接关闭 transport，无信号升级。改进方向：① stdio 服务器关闭时先发 SIGINT；② 100ms 后检查存活，未退出则 SIGTERM；③ 400ms 后仍存活则 SIGKILL；④ 每阶段检查 `kill(pid, 0)` 确认进程状态。

**意义**：MCP 服务器可能有待保存的状态——直接 kill 可能导致数据损坏。
**缺失后果**：直接断开 → 服务器无法清理 → 临时文件残留 / 数据库锁未释放。
**改进收益**：3 阶段升级——给服务器 100ms 优雅退出的机会，最坏 600ms 强制结束。

---

<a id="item-4"></a>

### 4. 事件循环卡顿检测（P2）

**思路**：定时器检测 Node.js 主线程被阻塞超过 500ms 的情况。阻塞通常由同步 I/O、大量 JSON 解析或 CPU 密集计算引起。检测到卡顿后记录诊断日志（时间戳、阻塞时长、调用栈）。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/eventLoopStallDetector.js` | 主线程阻塞 >500ms 时记录日志 |
| `main.tsx` (L427-429) | feature gate 动态导入（仅内部用户启用） |

**Qwen Code 修改方向**：无事件循环监控。改进方向：① 新建 `utils/eventLoopMonitor.ts`——`setInterval` 检测实际间隔与预期间隔的偏差；② 偏差 >500ms 时记录 warning + 当前执行上下文；③ 开发模式下默认启用，生产模式可通过环境变量启用。

**意义**：主线程阻塞 = UI 冻结 + 键盘无响应——用户以为程序崩溃了。
**缺失后果**：无诊断信息——"为什么卡了？" 无法定位。
**改进收益**：自动检测 + 诊断日志——快速定位同步 I/O 和 CPU 热点。

---

<a id="item-5"></a>

### 5. 会话活动心跳与空闲检测（P2）

**思路**：基于引用计数的活动追踪——API 调用和工具执行 `start()/stop()` 维护 refcount。refcount > 0 时每 30 秒发送心跳（保持远程会话存活）；refcount = 0 后启动空闲计时器。用于远程/后台场景防止会话被服务端超时断开。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/sessionActivity.ts` | `startSessionActivity(reason)`、`stopSessionActivity(reason)`、`SESSION_ACTIVITY_INTERVAL_MS = 30s` |
| `utils/idleTimeout.ts` (54行) | `CLAUDE_CODE_EXIT_AFTER_STOP_DELAY` 空闲退出 |

**Qwen Code 修改方向**：无会话活动追踪——远程 MCP 连接可能因空闲超时断开。改进方向：① 新建 `utils/sessionActivity.ts`——refcount 追踪 API 调用和工具执行；② refcount > 0 时 30s 心跳（向远程端点发送 keepalive）；③ 可配置空闲超时——SDK/daemon 模式下空闲 N 秒后自动退出释放资源。

**意义**：后台/远程会话可能因空闲被服务端断开——心跳保持连接存活。
**缺失后果**：长工具执行期间无心跳 → 远程连接超时 → 结果无法回传。
**改进收益**：30s 心跳 = 连接始终存活；空闲检测 = 资源自动释放。

---

<a id="item-6"></a>

### 6. Markdown 渲染缓存与纯文本快速路径（P2）

**思路**：Markdown 解析开销大（正则 + 递归），但大部分文本在滚动/重绘时不变。500 条 LRU 缓存存储解析后的 token 树，命中时零解析开销。纯文本快速检测（无 `#`/`*`/`` ` ``/`|` 等标记）直接跳过解析器。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `components/Markdown.tsx` | 500-item LRU token cache、`marked` 库解析 |
| `utils/markdown.ts` | 纯文本快速检测（fast path for plain text） |

**Qwen Code 修改方向**：`MarkdownDisplay.tsx` 每次渲染重新解析 markdown。改进方向：① 新增 `markdownCache: LRUCache<string, Token[]>(500)`；② 渲染前检查缓存命中；③ 纯文本快速路径——无 markdown 标记时直接渲染 `<Text>`。

**意义**：滚动回看历史消息时每帧重新解析 markdown——CPU 浪费导致卡顿。
**缺失后果**：100 条消息的历史 × 每帧解析 = 滚动卡顿。
**改进收益**：缓存命中 = 0ms 解析；纯文本快速路径 = 跳过 90% 的简单消息。

---

<a id="item-7"></a>

### 7. OSC 8 终端超链接（P2）

**思路**：文件路径和 URL 渲染为 OSC 8 超链接——用户可直接 Cmd+Click 在 IDE 中打开文件。格式：`\e]8;;file:///path\e\\text\e]8;;\e\\`。支持检测终端是否支持 OSC 8（iTerm2、WezTerm、Ghostty、kitty 等）。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `ink/termio/osc.ts` | OSC 8 超链接序列生成 |
| `ink/components/Text.tsx` | `hyperlink` 属性渲染 OSC 8 |
| `ink/output.ts` | `HyperlinkPool` 超链接池化 + 去重 |

**Qwen Code 修改方向**：文件路径作为纯文本输出，不可点击。改进方向：① 检测终端 OSC 8 支持（通过 `$TERM_PROGRAM`）；② 文件路径渲染时包裹 OSC 8 序列；③ URL 自动检测并包裹超链接。

**意义**：Agent 输出大量文件路径——点击直接跳转 vs 手动复制粘贴。
**缺失后果**：`src/utils/foo.ts:42` 只是文本——需手动复制路径再打开。
**改进收益**：Cmd+Click 直接在 IDE 打开——文件导航效率提升 10×。

---

<a id="item-8"></a>

### 8. 模糊搜索选择器（FuzzyPicker）（P2）

**思路**：通用模糊搜索组件——输入过滤 + 键盘导航 + 异步预览加载。支持方向键上下选择、Tab/Shift+Tab 操作、滚动指示器（↑↓）。用于：会话选择、文件选择、命令选择、MCP 工具选择等所有列表场景。预览面板支持 bottom 和 right 两种布局。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `components/design-system/FuzzyPicker.tsx` | 通用模糊搜索、异步预览、方向键导航、滚动指示器 |
| `components/HistorySearchDialog.tsx` | 会话搜索 + 预览（时间戳、首行、年龄格式化） |
| `utils/highlightMatch.tsx` | 匹配字符高亮渲染 |

**Qwen Code 修改方向**：`RadioButtonSelect.tsx` 和 `BaseSelectionList.tsx` 提供基础列表选择，但无模糊搜索过滤。改进方向：① 新建 `FuzzyPicker.tsx`——输入框 + 过滤列表 + 预览面板；② 集成 fzf-like 模糊匹配算法；③ 匹配字符高亮渲染。

**意义**：50+ 会话历史需要快速搜索定位——逐个浏览效率极低。
**缺失后果**：无搜索过滤的列表 = 用户只能逐项滚动。
**改进收益**：输入 2-3 个字符即过滤到目标——搜索效率提升 10×。

---

<a id="item-9"></a>

### 9. 统一设计系统组件库（P2）

**思路**：12 个语义化 UI 原语组成设计系统——ThemedBox（主题感知边框）、ThemedText（语义颜色文本）、StatusIcon（✓✗⚠ℹ○ 状态图标）、Divider（带标题分割线）、ListItem（焦点/选中态列表项）、Pane（容器组件）、ProgressBar（Unicode 块字符进度条 ▏▎▍▌▋▊▉█）、LoadingState（spinner + 消息 + 副标题）。所有组件通过 ThemeProvider 统一主题。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `components/design-system/` | 12 个设计系统组件 |
| `components/design-system/ThemeProvider.tsx` | React Context 主题管理 |
| `components/design-system/StatusIcon.tsx` | 5 种状态图标 + 颜色映射 |
| `components/design-system/ProgressBar.tsx` | Unicode 块字符精确进度条 |

**Qwen Code 修改方向**：UI 组件分散在 `components/` 各处，无统一设计系统。改进方向：① 新建 `components/design-system/` 目录；② 抽取通用 UI 原语（ThemedBox、StatusIcon、Divider、ProgressBar 等）；③ 通过 ThemeProvider 统一注入主题色。

**意义**：统一设计系统 = UI 一致性 + 新功能开发效率。
**缺失后果**：每个组件自行管理颜色/边框样式——不一致 + 重复代码。
**改进收益**：12 个语义原语 = 新功能直接组合，UI 风格自动一致。

---

<a id="item-10"></a>

### 10. Markdown 表格终端渲染（P2）

**思路**：Markdown 表格在终端中正确渲染——ANSI-aware 列宽计算（处理颜色转义不占宽度）+ 自动换行 + 对齐（左/右/居中）。处理 CJK 字符占 2 列宽度。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `components/MarkdownTable.tsx` | HTML table → 终端渲染、cell 换行、列宽计算 |

**Qwen Code 修改方向**：`MarkdownDisplay.tsx` 的表格渲染在 CJK/ANSI 混合场景列对齐不准确。改进方向：① 列宽计算使用 `stringWidth()`（ANSI-aware + CJK 2-width）；② cell 内容超宽时自动换行而非截断；③ 支持对齐标记（`:---`/`:---:`/`---:`）。

**意义**：Agent 输出对比表格是核心展示方式——对齐错误 = 信息不可读。
**缺失后果**：CJK + ANSI 颜色混合时列错位——表格变成乱码。
**改进收益**：ANSI-aware + CJK-aware 列宽 = 表格在任何语言下都对齐。

---

<a id="item-11"></a>

### 11. 屏幕阅读器无障碍支持（P2）

**思路**：检测环境变量启用无障碍模式。无障碍模式下：① 禁用动画（spinner 改为静态文本）；② Diff 渲染为纯文本格式；③ 进度信息以文本而非进度条显示；④ 颜色信息附带文字标签。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| 多个组件 | `isScreenReaderActive` 条件渲染——Diff/Spinner/Progress 均有无障碍替代 |

**Qwen Code 修改方向**：`useIsScreenReaderEnabled()` hook 已存在但使用有限。改进方向：① Diff 组件添加屏幕阅读器替代渲染（纯文本模式）；② Spinner 改为 `"Processing..."` 静态文本；③ ProgressBar 改为 `"45% complete"` 文本；④ `NoColor` 主题作为无障碍默认。

**意义**：视障开发者依赖屏幕阅读器——动画和颜色对他们是噪音。
**缺失后果**：屏幕阅读器读出 "dots dots dots" 而非 "正在处理"。
**改进收益**：无障碍模式 = 所有信息以文本呈现——屏幕阅读器完美工作。

---

<a id="item-12"></a>

### 12. 色觉无障碍主题（Daltonized）（P2）

**思路**：为色觉障碍用户提供专用主题——红绿色盲（deuteranopia）最常见（男性 8%），diff 的红/绿改为蓝/橙。提供 `light-daltonized` 和 `dark-daltonized` 两个变体。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/theme.ts` | `light-daltonized`、`dark-daltonized` 主题定义 |

**Qwen Code 修改方向**：15 个主题中无色觉无障碍主题。改进方向：① 新增 `qwen-daltonized-dark` 和 `qwen-daltonized-light` 主题；② Diff 颜色从红/绿改为蓝/橙；③ 所有语义颜色（success/error/warning）使用色觉安全色板。

**意义**：8% 男性用户有色觉障碍——红绿 diff 对他们看不出区别。
**缺失后果**：红色删除和绿色新增 = 对色觉障碍用户完全相同。
**改进收益**：蓝/橙 diff = 100% 用户可区分。

---

<a id="item-13"></a>

### 13. 动画系统与卡顿状态检测（P2）

**思路**：统一动画框架——`useAnimationFrame(intervalMs)` 以 60fps 驱动所有动画。共享时钟（ClockContext）确保多个动画同步。卡顿检测：spinner 超过阈值时间（如 30s）自动从蓝色 shimmer 渐变为红色，提示可能卡住。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `components/Spinner/useShimmerAnimation.ts` | shimmer 微光效果（glimmer index 计算） |
| `components/Spinner/useStalledAnimation.ts` | 超时后颜色渐变为红色 |
| `ink/hooks/use-animation-frame.ts` | `useAnimationFrame(intervalMs)` 统一动画驱动 |

**Qwen Code 修改方向**：`GeminiRespondingSpinner.tsx` 使用 `ink-spinner` 库的固定动画，无超时状态检测。改进方向：① spinner 超过 30s 时颜色渐变为黄色/红色提示可能卡住；② shimmer 微光效果替代单调转圈；③ 共享动画时钟确保多组件同步。

**意义**：用户看到同一个 spinner 转 60 秒——不知道是正常还是卡住了。
**缺失后果**：spinner 永远蓝色 = "还在正常工作？还是卡住了？" 无法判断。
**改进收益**：30s 后变红 = 用户立即知道可能需要干预（Escape 或等待）。

---

<a id="item-14"></a>

### 14. 代理权限冒泡与审批路由（P2）

**思路**：Fork 子代理的 `permissionMode: 'bubble'` 将权限请求上浮到父级终端——子代理无需独立 UI，权限对话框在用户可见的父终端弹出。Leader 通过 `leaderPermissionBridge` 桥接——InProcess Teammate 的权限请求路由到 Leader 的 `ToolUseConfirm` 对话框。邮箱回退：桥接不可用时通过文件邮箱异步审批。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/swarm/permissionSync.ts` (928行) | `createPermissionRequest()`、`sendPermissionRequestViaMailbox()` |
| `utils/swarm/leaderPermissionBridge.ts` (54行) | Leader ToolUseConfirm 队列桥接 |
| `tools/AgentTool/forkSubagent.ts` (L60) | `permissionMode: 'bubble'` |

**Qwen Code 修改方向**：子代理继承父级 ApprovalMode，但无冒泡机制——后台代理的权限请求无处显示。改进方向：① 新增 `bubble` 权限模式——子代理请求路由到父级 UI；② Leader 桥接——Teammate 权限请求显示在 Leader 终端；③ 文件邮箱回退——tmux 代理通过 JSON 文件异步审批。

**意义**：后台代理需要权限审批但没有自己的终端——请求必须路由到用户可见处。
**缺失后果**：后台代理权限请求 = 静默阻塞——用户不知道在等什么。
**改进收益**：权限冒泡 = 请求自动出现在父终端——用户审批后代理继续。

---

<a id="item-15"></a>

### 15. 代理专属 MCP 服务器（P2）

**思路**：代理 frontmatter 配置 `mcpServers` 字段——① 字符串引用（如 `"slack"`）复用已连接的服务器；② 内联定义（如 `{ slack: { command: "..." } }`）创建新连接。代理启动时连接，退出时自动清理。安全策略：plugin/built-in 代理可自由使用 MCP，用户自定义代理受 policy 限制。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `tools/AgentTool/runAgent.ts` (L95) | `initializeAgentMcpServers()` 连接代理专属 MCP |
| `tools/AgentTool/loadAgentsDir.ts` (L87) | frontmatter `mcpServers` 字段 |

**Qwen Code 修改方向**：代理共享全局 MCP 配置，无 per-agent MCP。改进方向：① frontmatter 新增 `mcpServers` 字段；② 字符串引用复用已连接服务器（`connectToServer = memoize()` 已支持）；③ 内联定义在代理启动时 `connect()`、退出时 `disconnect()`；④ 安全策略区分 admin-trusted 和 user-controlled 代理。

**意义**：专业代理需要专属工具——Slack 代理需要 Slack MCP，数据库代理需要 DB MCP。
**缺失后果**：所有代理共享全部 MCP = 权限过宽 + 工具列表过长浪费 token。
**改进收益**：per-agent MCP = 精准工具集 + 安全隔离 + 启动时按需连接。

---

<a id="item-16"></a>

### 16. 代理创建向导（P2）

**思路**：多步骤交互式向导引导创建自定义代理——① 选择位置（User/Project）；② 选择方式（手动/AI 生成）；③ 设定类型名；④ 编写系统提示；⑤ 选择工具子集；⑥ 选择模型；⑦ 配置记忆范围；⑧ 确认并保存为 `.claude/agents/name.md`。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `components/agents/new-agent-creation/CreateAgentWizard.tsx` | 11 步向导（Location→Method→Type→Prompt→Tools→Model→Color→Memory→Confirm） |
| `components/agents/agentFileUtils.ts` | `saveAgentToFile()`、`formatAgentAsMarkdown()` |

**Qwen Code 修改方向**：`/agents create` 命令存在但交互流程简单。改进方向：① 多步向导 UI（Ink 组件）引导每个配置项；② 工具选择提供可勾选列表（而非手动输入名称）；③ AI 生成模式——描述需求后 AI 生成 system prompt；④ 保存前预览完整的 YAML frontmatter + markdown。

**意义**：代理定义涉及 10+ 配置项——无向导引导容易遗漏或出错。
**缺失后果**：用户手动编辑 YAML frontmatter——格式错误 = 代理加载失败。
**改进收益**：向导引导 = 3 分钟创建完整代理定义——零格式错误。

---

<a id="item-17"></a>

### 17. 代理进度追踪与实时状态（P2）

**思路**：`ProgressTracker` 追踪后台代理的实时状态——toolUseCount、tokenCount（input/output）、recentActivities（最近 5 条操作描述）。通过 `<task-notification>` XML 格式向 Coordinator 报告完成状态（success/failed/killed + 摘要 + token 用量 + 时长）。UI 组件 `BackgroundTasksDialog` 展示所有后台代理列表 + 进度 + kill 控制。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `tasks/LocalAgentTask/LocalAgentTask.tsx` | `ProgressTracker`、`registerAsyncAgent()`、`updateAsyncAgentProgress()` |
| `utils/sdkEventQueue.ts` | `<task-notification>` XML 格式 |
| `components/tasks/BackgroundTasksDialog.tsx` | 后台代理 UI 列表 + kill 控制 |

**Qwen Code 修改方向**：`AgentResultDisplay` 提供最终结果但无实时进度追踪。改进方向：① 新增 `ProgressTracker`——每轮更新 toolUseCount/tokenCount/activities；② 后台代理面板显示实时进度列表；③ `<task-notification>` 格式标准化代理完成报告；④ kill 按钮一键终止卡住的代理。

**意义**：5 个后台代理并行运行——用户需要知道每个的进度和状态。
**缺失后果**：后台代理 = 黑箱——"做到哪了？卡住了吗？" 无法回答。
**改进收益**：实时进度面板 = 每个代理的 tool 调用数 + token 用量 + 最近操作一目了然。

---

<a id="item-18"></a>

### 18. 代理邮箱系统（Teammate Mailbox）（P2）

**思路**：基于文件的异步消息系统——每个 Teammate 有独立收件箱（`~/.claude/teams/{team}/inboxes/{agent}.json`）。消息包含：sender、text、timestamp、read 标志、color、summary。`proper-lockfile` 确保并发写入安全（10 次重试，5-100ms 退避）。支持单播（指定收件人）和广播（`to: "*"`）。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/teammateMailbox.ts` (400+行) | `readMailbox()`、`writeToMailbox()`、`markMessageAsReadByIndex()` |
| `tools/SendMessageTool/SendMessageTool.ts` | `HandleMessage()` 单播、`HandleBroadcast()` 广播 |

**Qwen Code 修改方向**：Arena 系统用文件 IPC（status/control JSON），但无通用代理间邮箱。改进方向：① 新建 `utils/teammateMailbox.ts`——JSON 文件 + lockfile 并发控制；② SendMessage 工具支持 `to: agentName` 和 `to: "*"` 广播；③ 代理执行循环中定期检查邮箱（500ms 轮询）。

**意义**：多代理协作需要通信——researcher 告诉 tester "结果在 path X"。
**缺失后果**：代理间无通信 = 只能通过共享文件间接协作——脆弱且不可靠。
**改进收益**：邮箱系统 = 结构化消息传递——代理间直接沟通、权限请求路由。

---

<a id="item-19"></a>

### 19. 远程触发器 REST API（P2）

**思路**：通过 REST API 管理定时远程 Agent——CRUD 端点 `/v1/code/triggers`。支持创建、更新、列表、获取、手动运行。触发器在云端 CCR 执行（非本地），适合 CI/CD 定时任务（如每日代码质量扫描、定期安全审查）。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `tools/RemoteTriggerTool/RemoteTriggerTool.ts` (162行) | REST API: `list`/`get`/`create`/`update`/`run` 5 种操作 |
| `skills/bundled/scheduleRemoteAgents.ts` | `/schedule` 技能——创建/管理远程定时 Agent |
| `utils/cronTasks.ts` (L30-70) | `CronTask` 类型：cron 表达式 + prompt + recurring/permanent/durable 标志 |

**Qwen Code 修改方向**：`CronScheduler` 仅支持会话内 cron（进程退出即丢失）。改进方向：① 新增 `/v1/code/triggers` REST 端点（或对接 DashScope 定时任务 API）；② 触发器配置持久化到 `.qwen/scheduled_tasks.json`；③ daemon 模式下 watch 文件变化自动加载新触发器。

**意义**：CI/CD 需要定时触发——每日安全扫描、每周代码质量报告。
**缺失后果**：cron 仅会话内 = 关闭终端即丢失——无法作为 CI 定时任务。
**改进收益**：REST API + 持久化 = 触发器跨会话存活——真正的 CI/CD 定时能力。

---

<a id="item-20"></a>

### 20. SDK 双向控制协议（P2）

**思路**：SDK 消费者与 CLI 之间的双向 NDJSON 控制协议——① SDK→CLI：`can_use_tool` 权限响应、`set_model` 切换模型、`set_permission_mode` 切换权限、`interrupt` 中断、`seed_read_state` 预填缓存；② CLI→SDK：`can_use_tool` 权限请求、`hook_callback` Hook 事件、`mcp_message` MCP 消息路由。26+ Hook 事件类型支持中间件模式。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `entrypoints/sdk/controlSchemas.ts` | 20+ 控制请求类型（`can_use_tool`/`set_model`/`interrupt`/`mcp_message` 等） |
| `entrypoints/sdk/coreSchemas.ts` (L642-655) | Stdout/Stdin 消息联合类型 |
| `bridge/bridgePermissionCallbacks.ts` | 权限回调：`allow`/`deny` + `updatedInput` + `updatedPermissions` |

**Qwen Code 修改方向**：TypeScript SDK 支持 `canUseTool` 回调和 `setModel`/`setPermissionMode`，但无完整控制协议（如 `seed_read_state`/`mcp_message`/`reload_plugins` 等高级操作）。改进方向：① 扩展控制协议覆盖 MCP 管理（`mcp_set_servers`/`mcp_reconnect`）；② 添加 `get_context_usage` 获取 token 分布；③ 添加 `rewind_files` 文件回退控制。

**意义**：IDE 插件和自动化系统需要精细控制 Agent 行为——不仅是发送消息。
**缺失后果**：SDK 只能发消息 + 审批权限——无法控制 MCP/设置/文件回退。
**改进收益**：完整控制协议 = IDE 插件可实现任意集成——模型切换、MCP 管理、文件回退。

---

<a id="item-21"></a>

### 21. CI 环境自动检测与行为适配（P2）

**思路**：检测具体 CI 平台（GitHub Actions/CircleCI/Jenkins/GitLab CI）并自适应行为——① 跳过浏览器认证流程（CI 无桌面）；② 自动启用 headless 输出格式；③ 提取 CI 上下文（PR 号、分支、commit SHA）注入系统提示；④ 调整超时（CI 通常有更长超时预算）。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/env.ts` (L285, L318) | `GITHUB_ACTIONS`/`CIRCLECI`/`CI` 环境变量检测 |
| `services/analytics/metadata.ts` (L617-624) | `isCi`/`isGithubAction` + GitHub 元数据采集 |
| `main.tsx` (L531) | GitHub Actions 入口点标记 `claude-code-github-action` |

**Qwen Code 修改方向**：仅检测通用 `CI` 环境变量（跳过浏览器认证），无具体平台检测。改进方向：① 检测 `GITHUB_ACTIONS`/`GITLAB_CI`/`CIRCLECI`/`JENKINS_HOME`；② 提取平台特定上下文（PR_NUMBER、BRANCH、COMMIT_SHA）；③ CI 模式自动调整：更长超时、JSON 输出、跳过交互提示。

**意义**：不同 CI 平台有不同的环境变量和能力——通用检测不够精准。
**缺失后果**：CI 中缺少 PR 上下文 = Agent 不知道在审查哪个 PR。
**改进收益**：平台感知 = 自动提取 PR/分支/commit 上下文——CI 集成零配置。

---

<a id="item-22"></a>

### 22. PR Webhook 事件实时订阅（P2）

**思路**：Agent 可订阅 GitHub PR 活动事件（review comments、CI 结果、状态变更），事件作为 user message 实时注入对话。Coordinator 代理可持续监控 PR 进展——CI 失败时自动修复，review 评论自动回复。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `coordinator/coordinatorMode.ts` (L133) | `subscribe_pr_activity` / `unsubscribe_pr_activity` |
| `commands/pr_comments/index.ts` | `/pr-comments` 获取 PR 级 + code review 评论 |

**Qwen Code 修改方向**：PR review 是一次性操作（工作流触发 → 评论 → 结束），无持续监控。改进方向：① WebSocket/SSE 订阅 GitHub PR 事件；② 事件转为 user message 注入 Agent 对话；③ Coordinator 模式下自动响应（CI 失败→修复→推送→再评论）。

**意义**：PR 审查是持续过程——reviewer 评论后 Agent 应能自动响应。
**缺失后果**：一次性审查 = reviewer 评论后需手动再次触发 Agent。
**改进收益**：实时订阅 = Agent 持续监控 PR——评论自动回复，CI 失败自动修复。

---

<a id="item-23"></a>

### 23. UltraReview 远程深度代码审查（P2）

**思路**：`/ultrareview` 在远程 CCR 环境中运行 10-20 分钟的深度代码审查（本地 `/review` 仅几分钟）。远程审查有独立配额追踪（`reviews_used/limit/remaining`）。每 10 秒发送 `<remote-review-progress>` 心跳标签。30 分钟超时保护。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `commands/review/reviewRemote.ts` | 远程审查传送（teleport to CCR） |
| `tasks/RemoteAgentTask/RemoteAgentTask.tsx` (L42-45) | `REMOTE_REVIEW_TIMEOUT_MS`、进度心跳标签 |
| `services/api/ultrareviewQuota.ts` | `fetchUltrareviewQuota()` 配额追踪 |

**Qwen Code 修改方向**：PR review 通过 GitHub Actions 工作流在 runner 上执行，无独立远程深度审查。改进方向：① `/ultrareview` 命令将审查任务发送到云端执行；② 进度心跳保持连接；③ 配额追踪防止滥用；④ 结果通过 `<remote-review>` 标签回传。

**意义**：复杂 PR（100+ 文件）需要 10-20 分钟深度分析——本地审查不够深入。
**缺失后果**：本地审查 = 受限于单次 API 调用——大 PR 覆盖不全。
**改进收益**：远程深度审查 = 10-20 分钟全面分析——发现更多隐藏 bug。

---

<a id="item-24"></a>

### 24. GitHub App 自动安装与工作流生成（P2）

**思路**：`/install-github-app` 命令自动化 GitHub Actions 集成——① 检查仓库访问权限（`gh api`）；② 生成 workflow YAML 文件（claude.yml + claude-code-review.yml）；③ 通过 GitHub API 创建分支并提交 workflow；④ 自动配置 `ANTHROPIC_API_KEY` secret；⑤ 打开浏览器创建 PR。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `commands/install-github-app/setupGitHubActions.ts` (325行) | 完整安装流程：检查权限→生成 YAML→创建分支→配置 secret→打开 PR |
| `constants/github-app.ts` | 工作流模板：`claude.yml`（PR 自动审查）+ `claude-code-review.yml`（代码审查） |

**Qwen Code 修改方向**：PR review 工作流手动配置（`.github/workflows/qwen-code-pr-review.yml`）。改进方向：① `/install-github-app` 一键安装命令；② 自动生成 workflow YAML 模板；③ 自动配置 API key secret（`gh secret set`）；④ 自动创建 PR 提交 workflow 文件。

**意义**：CI 集成配置复杂——手动编写 workflow YAML + 配置 secret 容易出错。
**缺失后果**：手动配置 = 每个仓库重复劳动 + 配置错误。
**改进收益**：一键安装 = 3 分钟完成 CI 集成——零手动编辑 YAML。

---

<a id="item-25"></a>

### 25. Headless 性能剖析（TTFT/延迟追踪）（P2）

**思路**：CI/headless 模式下自动收集性能指标——① TTFT（Time To First Token）；② 每轮处理延迟；③ 系统消息 yield 时间；④ 查询开销。100% 内部用户 + 5% 外部用户采样。指标用于优化 CI 场景下的 Agent 响应速度。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/headlessProfiler.ts` | `headlessProfilerStartTurn()`、`headlessProfilerCheckpoint()`、`logHeadlessProfilerTurn()` |

**Qwen Code 修改方向**：headless 模式无性能剖析——不知道 CI 中哪步最慢。改进方向：① 新建 `headlessProfiler.ts`——记录 TTFT/turn latency/overhead；② CI 环境自动启用（采样率可配置）；③ 结果输出到 JSON 或遥测系统。

**意义**：CI 中 Agent 执行时间直接影响 pipeline 总时长——需要知道哪步最慢。
**缺失后果**：无剖析 = "为什么 CI 这么慢？" 无数据可分析。
**改进收益**：TTFT/延迟追踪 = 精确定位瓶颈——优化 CI 执行时间。

---

<a id="item-26"></a>

### 26. 退出码标准化与 Hook 唤醒（P2）

**思路**：标准化 CI 友好的退出码语义——0=成功、1=错误、2=Hook 阻塞错误（唤醒模型重新处理）。后台异步 Hook 返回退出码 2 时唤醒 Agent 处理 Hook 结果——允许 Hook 在后台运行验证（如 lint/test），失败时自动通知 Agent 修复。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `schemas/hooks.ts` (L63) | `"exit code 2 (blocking error)"` 唤醒模型 |
| `interactiveHelpers.tsx` (L67-79) | 退出码 0/1 语义 |

**Qwen Code 修改方向**：有自定义退出码（`FatalTurnLimitedError` 等），但无 Hook 退出码 2 唤醒机制。改进方向：① 标准化退出码文档（0=成功/1=错误/2=hook 阻塞/53=turn 限制）；② 后台 Hook 退出码 2 时注入 `<hook-blocking-error>` 消息唤醒 Agent；③ CI 文档说明各退出码含义。

**意义**：CI pipeline 依赖退出码判断成功/失败——语义不清 = 错误的 pipeline 决策。
**缺失后果**：Hook 验证失败但退出码 0 = CI 误认为成功。
**改进收益**：标准化退出码 + Hook 唤醒 = CI 精确判断 + Agent 自动响应验证失败。

---

<a id="item-27"></a>

### 27. 破坏性命令警告系统（P2）

**思路**：在权限审批对话框中对 8 种高风险 git/shell 操作显示具体风险说明——`git push --force`（"可能覆盖远程历史"）、`git reset --hard`（"丢弃未提交变更"）、`git clean -f`（"永久删除未跟踪文件"）、`git checkout .`/`git restore .`（"丢弃工作树变更"）、`git stash drop/clear`（"永久删除暂存"）、`git branch -D`（"强制删除分支"）、`--no-verify`（"跳过安全钩子"）、`git commit --amend`（"改写最后一次提交"）。用户看到风险说明后做出知情审批决策。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `tools/BashTool/destructiveCommandWarning.ts` | 8 种 regex 模式 + 对应警告文字 |
| `tools/PowerShellTool/destructiveCommandWarning.ts` (L64) | PowerShell 版本（case-insensitive） |
| `components/permissions/BashPermissionRequest/BashPermissionRequest.tsx` (L274) | 警告文字在权限对话框中显示 |

**Qwen Code 修改方向**：`shellReadOnlyChecker.ts` 将 `git push` 归为非 read-only（需审批），但不提供操作级别风险说明。改进方向：① 新建 `destructiveCommandWarning.ts`——8 种 regex 模式匹配危险 flag；② 权限对话框中显示具体警告文字（"Note: may overwrite remote history"）；③ 系统提示中明确列出 force-push 等为"难以逆转的操作"。

**意义**：用户审批"git push --force"时只知道"这是写操作"——不知道具体风险。
**缺失后果**：用户盲目批准 force push = 远程历史被覆盖——无法恢复。
**改进收益**：风险说明 = 用户看到"可能覆盖远程历史"后谨慎决策——避免数据丢失。

---

<a id="item-35"></a>

### 35. 系统提示危险操作行为指导（P2）

**思路**：在系统提示中向模型提供分层的危险操作行为指导——① 总原则："评估可逆性和影响范围，高风险操作必须先确认"；② 4 类危险操作具体列举（破坏性操作/难以逆转操作/影响共享状态操作/第三方上传）；③ 行为准则："不要用破坏性操作作为捷径"、"调查后再删除/覆盖"、"解决冲突而非丢弃变更"、"measure twice, cut once"；④ 审批范围限定："一次审批不等于所有场景的永久授权"。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `constants/prompts.ts` (L255-267) | `getActionsSection()` — "Executing actions with care" 完整行为指导 |

**Qwen Code 修改方向**：`prompts.ts` (L316) 仅 "Never push changes to a remote repository without being asked explicitly by the user"——一条规则，无分层指导。改进方向：① 新增 `getActionsSection()` 系统提示段，列举 4 类危险操作（force-push/reset --hard/rm -rf/DROP TABLE/kubectl delete 等）；② 行为准则：不绕过安全检查（--no-verify）、调查异常状态而非直接删除、解决冲突而非丢弃；③ 审批范围："用户批准一次 git push 不等于批准所有 push"；④ 终端焦点感知："用户不在时更自主，但仍对不可逆操作暂停"。

**意义**：模型行为受系统提示引导——无指导则模型可能选择"最省事"的破坏性路径。
**缺失后果**：模型遇到合并冲突 → 直接 `git checkout --theirs .` 丢弃所有本地变更。
**改进收益**：行为指导 = 模型优先选择安全路径——resolve > discard，investigate > delete。

---

<a id="item-28"></a>

### 28. Unicode 净化与 ASCII 走私防御（P2）

**思路**：对所有外部输入（MCP 工具结果、文件内容、URL 参数）进行 Unicode 净化——① NFKC 规范化；② 移除 Cf/Co/Cn 类别字符；③ 剥离零宽空格、RTL/LTR 标记、BOM。递归处理嵌套数据结构（最大 10 轮防止无限循环）。防御 ASCII Smuggling 和隐藏提示注入。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/sanitization.ts` (92行) | NFKC + Cf/Co/Cn 移除 + 零宽/RTL/BOM 剥离 + 递归净化 |

**Qwen Code 修改方向**：无 Unicode 净化——MCP 工具返回的不可见字符直接传给模型。改进方向：① 新建 `utils/sanitization.ts`——NFKC + 不可见字符剥离；② 所有外部输入过净化函数；③ 递归处理 JSON 对象中的字符串值。

**意义**：攻击者可在 MCP 工具结果中嵌入不可见 Unicode 字符注入指令。
**缺失后果**：不可见字符 = 模型"看到"用户看不到的指令——静默执行恶意操作。
**改进收益**：Unicode 净化 = 不可见字符全部剥离——模型只看到用户能看到的内容。

---

<a id="item-29"></a>

### 29. 沙箱运行时集成（P2）

**思路**：Shell 命令在沙箱中执行——限制文件系统访问（路径模式）、网络访问（域名白名单）、进程能力。3 种后端：macOS seatbelt、Linux bubblewrap、Docker。沙箱策略可配置，特定命令可排除（如 `npm install` 需要网络）。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/sandbox/sandbox-adapter.ts` | 沙箱运行时——路径模式、FS 限制、网络控制、违规事件 |
| `tools/BashTool/shouldUseSandbox.ts` (L130-153) | 沙箱决策——feature gate + 排除命令列表 |

**Qwen Code 修改方向**：Docker/seatbelt 沙箱存在但非默认启用。改进方向：① 默认启用轻量沙箱（文件系统限制为工作目录 + 临时目录）；② 命令排除列表；③ 违规事件记录。

**意义**：Shell 命令是最大攻击面——不受限的 shell 可执行任意代码。
**缺失后果**：无沙箱 = 任何命令无限制执行。
**改进收益**：沙箱 = 文件/网络/进程受限——恶意命令无法越权。

---

<a id="item-30"></a>

### 30. SSRF 防护（HTTP Hook）（P2）

**思路**：HTTP Hook 发送 POST 前验证目标——阻断私有 IP（10.0.0.0/8 等）和 IPv6 私有范围。检测 IPv4-mapped IPv6（`::ffff:10.0.0.1`）防止绕过。DNS 查询结果二次验证——防 DNS rebinding。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/hooks/ssrfGuard.ts` (295行) | 私有 IP 阻断 + IPv6 + IPv4-mapped + DNS 验证 |

**Qwen Code 修改方向**：`isPrivateIp()` 仅基础检查，无 IPv6 和 DNS rebinding 防护。改进方向：① 扩展覆盖 IPv6 和 IPv4-mapped；② DNS 查询结果验证；③ HTTP Hook 必须过 SSRF guard。

**意义**：HTTP Hook 可向任意 URL POST——可能访问内部服务。
**缺失后果**：攻击者通过 Hook 访问 `169.254.169.254` 获取云凭证。
**改进收益**：SSRF guard = 私有 IP 全阻断——内部服务不可达。

---

<a id="item-31"></a>

### 31. WebFetch 域名白名单（P2）

**思路**：130+ 常用域名预批准（文档/包管理/API 参考），匹配时无需审批。路径段边界检查确保 `/anthropic` 不匹配 `/anthropic-evil/`。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `tools/WebFetchTool/preapproved.ts` (167行) | 130+ 域名 + Set 快速匹配 + 路径段边界检查 |

**Qwen Code 修改方向**：WebFetch 通过通用规则系统，无内置白名单。改进方向：① 内置常用域名白名单；② hostname Set 快速匹配；③ 路径段边界检查。

**意义**：频繁访问 npm/PyPI/MDN——每次审批影响效率。
**缺失后果**：每次 fetch 文档站点都弹审批。
**改进收益**：白名单 = 常用文档直接访问。

---

<a id="item-32"></a>

### 32. 子进程环境变量清洗（P2）

**思路**：子进程启动前清洗 30+ 敏感变量——API 密钥、云凭证、GitHub token、OTEL headers。通过 `CLAUDE_CODE_SUBPROCESS_ENV_SCRUB` 控制启用。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/subprocessEnv.ts` (99行) | 30+ 敏感变量清洗——API key + 云凭证 + GitHub + OTEL |

**Qwen Code 修改方向**：子进程继承完整环境含 API 密钥。改进方向：① 从 env 删除敏感变量（`DASHSCOPE_API_KEY` 等）；② 保留代理变量；③ 可配置清洗列表。

**意义**：子进程继承 API 密钥 = 任何 shell 命令能读取。
**缺失后果**：`env | grep KEY` 暴露所有密钥。
**改进收益**：环境清洗 = 子进程无法获取敏感凭证。

---

<a id="item-33"></a>

### 33. 工具输出密钥扫描（P2）

**思路**：工具结果用 50+ gitleaks 规则扫描——AWS/GitHub/Slack/PEM/Stripe 等。正则懒编译。检测到密钥时阻止写入共享记忆。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `services/teamMemorySync/secretScanner.ts` (295行) | 50+ gitleaks 规则 |
| `services/teamMemorySync/teamMemSecretGuard.ts` (44行) | 写入阻断 |

**Qwen Code 修改方向**：无工具输出密钥扫描。改进方向：① 移植 gitleaks 规则；② 写入文件/记忆前扫描；③ 检测到密钥时警告 + 阻止写入共享位置。

**意义**：Agent 读 `.env` 后可能将密钥写入 QWEN.md。
**缺失后果**：密钥泄漏到团队文件。
**改进收益**：密钥扫描 = 阻止密钥写入共享位置。

---

<a id="item-34"></a>

### 34. 权限升级防护（P2）

**思路**：进入自动模式时剥离危险权限规则——代码执行（python/node/ruby/perl）、shell（eval/exec/sudo）、网络（curl/wget/ssh）、云 CLI（aws/gcloud/kubectl）共 60+ 模式。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/permissions/dangerousPatterns.ts` (81行) | 60+ 危险模式自动剥离 |

**Qwen Code 修改方向**：`yolo` 模式批准所有操作，无危险规则剥离。改进方向：① 进入 auto/yolo 时剥离危险权限规则；② 被剥离的规则记录日志；③ `--dangerously-allow-all` 强制保留。

**意义**：auto 模式应减少审批，但不应允许任意代码执行。
**缺失后果**：yolo + `Bash(python *)` = 模型可执行任意脚本。
**改进收益**：危险规则剥离 = auto 仅批准安全操作。

---
