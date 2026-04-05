# Qwen Code 改进建议 — P2 界面与 UX

> 中等优先级改进项。每项包含：问题分析、源码索引、现状评估、改进方向、实现成本、前后对比。
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md)

<a id="item-1"></a>

### 1. Token 使用实时警告（P2）

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

<a id="item-2"></a>

### 2. 快捷键提示组件（P2）

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

<a id="item-3"></a>

### 3. 终端完成通知（P2）

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

<a id="item-4"></a>

### 4. Spinner 工具名 + 计时（P2）

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

<a id="item-5"></a>

### 5. /rewind 检查点回退（P2）

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

<a id="item-6"></a>

### 6. /copy OSC 52 剪贴板（P2）

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

<a id="item-7"></a>

### 7. 首次运行引导向导（P2）

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

<a id="item-8"></a>

### 8. /doctor 诊断工具（P2）

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

<a id="item-9"></a>

### 9. 结构化 Diff 渲染（P2）

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

<a id="item-10"></a>

### 10. Slash Command 命名空间治理（P2）

**问题**：Qwen Code 的 slash command 已进入"平台化"阶段——至少 4 类来源会注入命令名：built-in commands、文件命令（user/project）、extension commands、MCP prompt commands。当来源越来越多时，问题不再是"怎么加载命令"，而是**谁能占用顶级命令名**：

- 用户输入 `/deploy`——它来自 project file command？MCP server prompt？还是 extension？
- MCP prompt 与 user 命令都占用了 `/review`——谁赢？
- 企业管理员想禁用某些 extension 命令——怎么做？

**Claude Code 的方案**：保守的合并策略——`uniqBy([...initialCommands, ...mcpCommands], 'name')` 保持命令名唯一（先注册的赢），插件命令走独立管理路径。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `hooks/useMergedCommands.ts` | `uniqBy()` 命令名去重 |
| `services/plugins/pluginCliCommands.ts` | 插件命令独立管理入口 |

**Qwen Code 现状**：`CommandService.ts` 并行加载所有 loader 的命令放入 `Map<string, SlashCommand>`。extension 命令冲突时自动改名为 `extensionName.commandName`，非 extension 命令按 loader 顺序"后者覆盖前者"。`McpPromptLoader.ts` 把 MCP prompt 直接暴露为 slash command 名，不带 server namespace。

**Qwen Code 修改方向**：① 引入显式 source namespace（built-in → `/model`、extension → `/ext.foo.bar`、MCP prompt → `/mcp.github.review`）；② 常用命令保留短别名，由治理层决定而非"最后加载的赢"；③ 补全列表显示命令来源（built-in / extension / MCP / local）；④ reserved name 策略防止扩展抢占关键命令名。

**实现成本评估**：
- 涉及文件：~4 个
- 新增代码：~300 行
- 开发周期：~3 天（1 人）
- 难点：命名空间前缀策略——太长影响易用性，太短不够隔离

**改进前后对比**：
- **改进前**：`/review` 来源不明——可能是 built-in，也可能是某个 MCP server 的 prompt
- **改进后**：`/review`（built-in）vs `/mcp.github.review`（MCP）——来源一目了然

**意义**：命令空间是用户与 Agent 交互的主入口——命名冲突导致不可预测行为。
**缺失后果**：MCP prompt 抢占 `/deploy` → 用户以为执行 built-in deploy，实际执行了 MCP prompt。
**改进收益**：命名空间治理 = 来源透明 + 冲突可控 + 企业可管理。

---

<a id="item-11"></a>

### 11. /plan 计划模式（P2）

**问题**：复杂任务（如"重构整个认证模块"）直接让 Agent 动手可能走偏。开发者想先看 Agent 的计划——要改哪些文件、分几步、有什么风险——确认后再执行。

**Claude Code 的方案**：`/plan` 命令进入计划模式——Agent 只分析不动手，输出结构化计划（步骤/文件/风险/依赖）。用户审阅后 `/plan execute` 开始执行，或修改计划后再执行。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `commands/plan/plan.ts` | `/plan` 命令入口、计划模式切换 |

**Qwen Code 现状**：无 `/plan` 命令。Agent 收到复杂指令后直接开始执行——用户只能事后检查结果。

**Qwen Code 修改方向**：① 新增 `/plan` 命令切换到计划模式；② 计划模式下 Agent 只输出分析不执行工具；③ `/plan execute` 确认后开始执行。

**实现成本评估**：
- 涉及文件：~3 个
- 新增代码：~200 行
- 开发周期：~2 天（1 人）
- 难点：计划模式下工具调用的拦截与过滤

**改进前后对比**：
- **改进前**：用户说"重构认证" → Agent 直接改代码 → 方向不对需要撤销
- **改进后**：`/plan` → Agent 输出计划 → 用户确认/修改 → 按计划执行

**进展**：[PR#2921](https://github.com/QwenLM/qwen-code/pull/2921)（open）— 实现了 `/plan` 命令切换计划模式，支持非交互环境（ACP/Headless），含完整单测和 6 语言 i18n。

**意义**：复杂任务需要"先想后做"——计划模式降低风险。
**缺失后果**：Agent 直接执行 → 方向错误时需大量撤销 → 浪费时间和 token。
**改进收益**：先计划后执行 = 用户掌控方向，Agent 高效执行。

---

<a id="item-12"></a>

### 12. /rename 重命名会话（P2）

**问题**：Agent 自动生成的会话标题往往不够准确——"New Session" 或过于冗长。用户想给会话起个有意义的名字（如"auth-refactor-v2"）方便后续查找。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `commands/rename/rename.ts` | `/rename` 命令 + Bridge 同步 |

**Qwen Code 现状**：无 `/rename` 命令。会话标题由 AI 自动生成，用户无法修改。

**Qwen Code 修改方向**：① 新增 `/rename <new-name>` 命令；② 更新 session JSONL 中的 `custom-title` 条目；③ 如果有 Bridge 连接则同步到云端。

**实现成本评估**：
- 涉及文件：~2 个
- 新增代码：~50 行
- 开发周期：~0.5 天（1 人）
- 难点：无（最简单的命令之一）

**改进前后对比**：
- **改进前**：50 个会话全叫 "New Session" 或自动标题 → 找不到目标
- **改进后**：`/rename auth-v2` → 精确命名 → 配合 `/tag` 快速定位

**意义**：会话命名是信息管理基础。
**缺失后果**：自动标题不准确 → 回溯历史困难。
**改进收益**：手动重命名 = 会话标题有意义 → 搜索效率提升。

---

<a id="item-13"></a>

### 13. /upgrade 版本升级（P2）

**问题**：用户不知道当前版本是否最新、有哪些新功能。需要手动去 npm 查版本号、手动 `npm update`。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `commands/upgrade/upgrade.ts` | 版本检查 + 自动升级 |
| `utils/releaseNotes.ts` | changelog 获取与展示 |

**Qwen Code 现状**：无 `/upgrade` 命令。用户需手动 `npm update -g @anthropic-ai/claude-code` 升级。

**Qwen Code 修改方向**：① 新增 `/upgrade` 命令；② 比较当前版本与 npm latest；③ 有新版本时展示 changelog + 一键升级。

**实现成本评估**：
- 涉及文件：~2 个
- 新增代码：~100 行
- 开发周期：~1 天（1 人）
- 难点：跨平台包管理器检测（npm/pnpm/yarn/bun）

**改进前后对比**：
- **改进前**：用户不知道有新版本 → 错过重要修复和新功能
- **改进后**：`/upgrade` → 显示 changelog + 一键更新

**意义**：版本管理自动化是 CLI 工具基本能力。
**缺失后果**：用户使用旧版本 → 错过修复 → 可能遇到已修复的 bug。
**改进收益**：一键升级 = 始终使用最新版本。

---

<a id="item-14"></a>

### 14. Plugin 系统增强（P2）

**问题**：Qwen Code 的 extension 系统支持加载 MCP servers/skills/subagents/hooks，但缺少统一的 Plugin 容器概念——将 commands + skills + hooks + MCP 打包为一个可安装/可卸载的插件单元。

**Claude Code 的方案**：Plugin 是一个聚合容器——一个 Plugin 目录下可以包含 `commands/`、`skills/`、`hooks/`、`agents/`，还有 `manifest.json` 描述元数据。通过 `pluginLoader.ts` 统一加载，支持 marketplace 安装、版本管理、热重载。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/plugins/pluginLoader.ts` (3302行) | Plugin 加载 + marketplace 同步 |
| `utils/plugins/pluginInstaller.ts` | 安装 + 版本管理 |

**Qwen Code 现状**：`extensionManager.ts` 支持加载 MCP/skills/subagents/hooks，但没有"Plugin"作为聚合容器的概念——每种资源独立管理，无法一键安装/卸载整个功能包。

**Qwen Code 修改方向**：① 定义 Plugin manifest 格式（name/version/commands/skills/hooks/mcp）；② Plugin 目录扫描与统一加载；③ `/plugin install/uninstall/list` 命令；④ 插件间依赖管理。

**实现成本评估**：
- 涉及文件：~6 个
- 新增代码：~500 行
- 开发周期：~5 天（1 人）
- 难点：Plugin 间依赖解析与版本兼容性

**改进前后对比**：
- **改进前**：安装一个功能需要分别配置 MCP server + skill + hook → 繁琐且易出错
- **改进后**：`/plugin install code-review` → 一键安装包含 MCP+skill+hook 的功能包

**意义**：Plugin 是平台化的基础——社区可以打包分发完整功能。
**缺失后果**：资源分散管理 → 安装/卸载/更新不原子 → 状态不一致。
**改进收益**：Plugin 聚合 = 一键安装/卸载完整功能包 → 生态可持续增长。

---

<a id="item-15"></a>

### 15. 文件编辑引号风格保留（P2）

**问题**：Agent 修改 JSON/YAML/JS 文件时，可能把单引号改成双引号（或反过来），导致代码风格不一致——`git diff` 出现大量无意义的引号变更，污染真正的逻辑变更。

**Claude Code 的方案**：`preserveQuoteStyle()` 函数检测原文件的引号风格（单引号/双引号），编辑时保持一致。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `tools/FileEditTool/utils.ts` | `preserveQuoteStyle()` |

**Qwen Code 现状**：Edit 工具直接替换文本，不检测也不保留引号风格。

**Qwen Code 修改方向**：① Edit 工具的 `old_string`/`new_string` 替换前检测原文件引号风格；② 如果新文本使用了不同引号风格，自动转换为原文件风格。

**实现成本评估**：
- 涉及文件：~1 个
- 新增代码：~50 行
- 开发周期：~0.5 天（1 人）
- 难点：混合引号风格文件的处理策略

**改进前后对比**：
- **改进前**：Agent 把 `'hello'` 改成 `"hello"` → git diff 显示大量引号变更
- **改进后**：保留原风格 → git diff 只显示逻辑变更

**意义**：代码风格一致性是代码审查的基本要求。
**缺失后果**：引号变更污染 diff → reviewer 需要逐行确认是否只是风格变化。
**改进收益**：引号保留 = 干净 diff → 审查效率提升。

---

<a id="item-16"></a>

### 16. 文件编辑等价性判断（P2）

**问题**：Agent 可能对同一文件发起多次编辑请求——如果两次编辑的 `old_string`/`new_string` 在语义上等价（如仅空白差异），应跳过重复编辑避免权限对话框弹出。

**Claude Code 的方案**：`areFileEditsInputsEquivalent()` 函数比较两次编辑请求是否语义等价——归一化空白后比较。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `tools/FileEditTool/utils.ts` | `areFileEditsInputsEquivalent()` |
| `tools/FileEditTool/FileEditTool.ts` | 调用等价性判断跳过重复 |

**Qwen Code 现状**：无编辑等价性判断——完全相同的编辑也会重新执行和弹出权限确认。

**Qwen Code 修改方向**：① 新增 `areEditsEquivalent()` 函数；② Edit 工具执行前检查是否与上次编辑等价；③ 等价时跳过执行返回 "no changes needed"。

**实现成本评估**：
- 涉及文件：~2 个
- 新增代码：~80 行
- 开发周期：~1 天（1 人）
- 难点：语义等价的定义——仅空白？还是包括注释差异？

**改进前后对比**：
- **改进前**：相同编辑重复执行 → 弹两次权限对话框 → 用户困惑
- **改进后**：检测等价 → 跳过 → "no changes needed"

**意义**：减少不必要的权限弹窗和重复操作。
**缺失后果**：重复编辑 → 重复弹窗 → 用户被无意义操作打断。
**改进收益**：等价跳过 = 减少弹窗 + 提升交互流畅度。

---

<a id="item-17"></a>

### 17. MCP 通道权限管理（P2）

**问题**：当多个 MCP server 通过 channel plugin 注册时，需要控制哪些 channel plugin 可以注册——防止未经审核的 plugin 注入恶意 MCP 工具。

**Claude Code 的方案**：`channelAllowlist.ts` 通过 GrowthBook feature gate 管理 channel plugin allowlist，只有白名单中的 plugin 可以注册 MCP 工具。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `services/mcp/channelAllowlist.ts` | Plugin-level allowlist, GrowthBook gate |

**Qwen Code 现状**：Channel 系统（DingTalk/Telegram/WeChat）无 plugin allowlist——任何 channel 都可以注册 MCP 工具。

**Qwen Code 修改方向**：① 配置文件新增 `channels.allowlist` 字段；② Channel plugin 注册时检查 allowlist；③ 未授权 plugin 的 MCP 工具注册被拒绝并记录日志。

**实现成本评估**：
- 涉及文件：~2 个
- 新增代码：~80 行
- 开发周期：~1 天（1 人）
- 难点：allowlist 的粒度——按 marketplace + plugin tuple 还是按 plugin name

**改进前后对比**：
- **改进前**：任何 channel plugin 可注册 MCP 工具 → 潜在安全风险
- **改进后**：allowlist 控制 → 只有审核通过的 plugin 可注册

**意义**：MCP 工具直接影响 Agent 能力——未审核的工具是安全漏洞。
**缺失后果**：恶意 plugin 注入工具 → Agent 可能执行不安全操作。
**改进收益**：allowlist = 只有可信 plugin 的工具可用 → 安全可控。

---

<a id="item-18"></a>

### 18. 消息类型丰富化（P2）

**问题**：Agent 对话中不同类型的消息（用户输入、助手回复、工具调用、系统通知、压缩边界、进度更新等）需要不同的处理和渲染。类型越丰富，SDK 消费者和 UI 就能越精确地处理每种消息。

**Claude Code 的方案**：30+ 种 SDK 消息类型——SDKUserMessage、SDKAssistantMessage、SDKPartialAssistantMessage、SDKToolProgressMessage、SDKResultMessage、SDKCompactBoundaryMessage、SDKStatusMessage、SDKControlRequest、SDKControlResponse、SDKKeepAliveMessage 等。

**Qwen Code 现状**：消息类型较少（~11 种），SDK 消费者需要通过内容猜测消息语义。

**Qwen Code 修改方向**：① 扩展消息类型枚举（新增 CompactBoundary、ToolProgress、Status、KeepAlive 等）；② SDK 输出格式区分每种消息类型；③ UI 层按类型差异化渲染。

**实现成本评估**：
- 涉及文件：~4 个
- 新增代码：~200 行
- 开发周期：~2 天（1 人）
- 难点：新增类型不破坏现有 SDK 消费者的兼容性

**改进前后对比**：
- **改进前**：SDK 消费者收到消息 → 需要解析内容猜测类型 → 脆弱
- **改进后**：每条消息有明确 type 字段 → SDK 消费者 switch(type) 精确处理

**意义**：消息类型是 SDK 协议的基础——类型越精确，集成越可靠。
**缺失后果**：类型不够 → SDK 消费者猜测语义 → 集成脆弱。
**改进收益**：30+ 类型 = 每种消息精确标识 → SDK 集成稳健可靠。

---

<a id="item-19"></a>

### 19. /clear 多模式增强（P2）

**问题**：长会话聊了 50 轮后，用户想"重新开始"但不想退出重启 CLI。当前 `/clear` 只是清屏——对话历史、上下文、记忆全部保留。用户真正需要的是 3 种清除力度。

**Claude Code 的方案**：`/clear` 支持多模式：

| 模式 | 命令 | 清除内容 | 保留内容 |
|------|------|----------|----------|
| 清屏 | `/clear` | 终端显示 | 对话历史 + 记忆 + 上下文 |
| 清对话 | `/clear --history` | 对话历史 | 系统提示 + 记忆 + 附件 |
| 完全重置 | `/clear --all` | 一切 | 无（如同新 session） |

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `commands/clear/clear.ts` | `/clear` 多模式实现 |

**Qwen Code 现状**：`/clear` 仅清屏（清除终端显示），不清除对话历史。想"重新开始"只能退出并重启 CLI。

**Qwen Code 修改方向**：① `/clear` 保持清屏；② 新增 `--history` 标志清空 messages 数组（保留 system prompt + memory）；③ 新增 `--all` 标志完全重置（重新初始化）；④ `--history` 和 `--all` 需交互确认防止误操作。

**实现成本评估**：
- 涉及文件：~2 个
- 新增代码：~100 行
- 开发周期：~0.5 天（1 人）
- 难点：`--all` 模式下需要正确重新初始化系统提示和工具注册

**改进前后对比**：
- **改进前**：想重新开始 → 退出 CLI → 重新启动 → 重新加载项目 → 浪费时间
- **改进后**：`/clear --all` → 原地重置 → 立即开始新对话

**进展**：[PR#2915](https://github.com/QwenLM/qwen-code/pull/2915)（open）— 实现了 `/clear --history` 和 `/clear --all` 两种模式，带确认提示。

**意义**：长会话经常需要"软重启"——不想退出但想清除上下文。
**缺失后果**：只能退出重启 → 丢失终端状态和环境变量。
**改进收益**：3 种清除力度 = 用户精确控制保留什么、丢弃什么。

---

<a id="item-20"></a>

### 20. /thinkback 会话回忆（P2）

**问题**：长会话（50+ 轮）后，开发者经常想不起来"之前那个 API 设计决策是什么时候做的"或"哪一步引入了那个 bug"。当前只能手动向上滚动逐条查看——在几百条消息中定位目标极其低效。`/thinkback` 不同于搜索（关键词匹配）——它是**时间线式的关键事件回顾**。

**Claude Code 的方案**：`/thinkback` 分析完整 transcript，提取关键决策点（文件修改、错误修复、架构决策），生成时间线式回顾报告：

```
/thinkback
# 输出：
# 10:30 — 重构了 auth middleware（修改 3 个文件）
# 10:45 — 修复 3 个测试失败（TypeError in login.test.ts）
# 11:00 — 决定使用 JWT 替换 Session（用户确认）
# 11:15 — 添加 token refresh 逻辑
```

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `commands/thinkback/thinkback.tsx` | `/thinkback` 命令——transcript 分析 + 关键事件提取 |

**Qwen Code 现状**：有 `/summary` 命令（即时摘要当前状态），但没有时间线式的事件回顾能力。也有 Transcript Search（[p2-tools-commands #2](./qwen-code-improvement-report-p2-tools-commands.md#item-2)，关键词搜索），但搜索是"找特定内容"，thinkback 是"回顾做了什么"。

**Qwen Code 修改方向**：① 新建 `/thinkback` 命令；② 分析 session transcript 提取关键事件（文件修改、错误修复、决策点）；③ 按时间线排序输出；④ 支持 `--from` 时间范围和 `--topic` 主题过滤。

**实现成本评估**：
- 涉及文件：~3 个
- 新增代码：~300 行
- 开发周期：~2 天（1 人）
- 难点：从 transcript 中识别"关键事件"（文件修改容易，决策点需要 LLM 辅助）

**改进前后对比**：
- **改进前**：想回忆 1 小时前的决策 → 手动滚动几百条消息 → 5 分钟找不到
- **改进后**：`/thinkback --from "1h ago"` → 时间线列出所有关键事件 → 5 秒定位

**进展**：[PR#2917](https://github.com/QwenLM/qwen-code/pull/2917)（open）— 实现了 `/thinkback` 命令，利用 LLM 分析 transcript 生成结构化时间线。

**意义**：长会话中回忆是核心需求——Agent 做了 20 步操作，用户需要快速了解"做了什么"。
**缺失后果**：无回忆能力 → 长会话后用户"失忆" → 可能重复之前的错误决策。
**改进收益**：时间线式回忆 = 长会话透明可追溯——"做了什么、什么时候、为什么"一目了然。

---

<a id="item-21"></a>

### 21. /context 非交互输出与自动化诊断（P2）

**问题**：Qwen Code 的 `/context` 命令可以在终端中查看上下文 token 分布（system prompt / tools / memory / 消息历史各占多少），但这个能力只在交互式 TUI 中可用。CI 脚本、基准测试、IDE 插件和外部控制器无法程序化获取同样的诊断数据。

**Claude Code 的方案**：将 `/context` 拆为两层——交互式（`context.tsx`）和非交互式（`context-noninteractive.ts`），共享 `collectContextData()` 数据采集路径。非交互输出为结构化文本（Markdown 表格或 JSON），可被脚本解析。SDK 控制协议也通过 `get_context_usage` 请求暴露同一套数据。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `commands/context/context-noninteractive.ts` | `collectContextData()` 共享采集路径 |
| `commands/context/context.tsx` | 交互式 TUI 渲染 |

**Qwen Code 现状**：`contextCommand.ts` 仅在交互式 TUI 中渲染 token 分布。`nonInteractiveCliCommands.ts` 中未包含 `/context`。

**Qwen Code 修改方向**：① `contextCommand.ts` 抽取 `collectContextData()` 共享函数；② `nonInteractiveCliCommands.ts` 注册 `/context` 输出结构化文本；③ SDK 控制协议新增 `get_context_usage` 请求类型。

**实现成本评估**：
- 涉及文件：~3 个
- 新增代码：~150 行
- 开发周期：~1 天（1 人）
- 难点：确保交互和非交互路径的数据采集逻辑完全一致

**相关文章**：[/context 非交互输出 Deep-Dive](./context-usage-noninteractive-deep-dive.md)

**改进前后对比**：
- **改进前**：CI 想知道 prompt 体积变化 → 无法获取 → 版本发布后才发现 token 膨胀
- **改进后**：`qwen -p --context-usage --output-format json` → CI 自动比较 → 回归立即报警

**进展**：[PR#2916](https://github.com/QwenLM/qwen-code/pull/2916)（open）— 非交互模式支持 `/context`，新增 `getContextUsage()` SDK API。

**意义**：上下文诊断是平台能力而非 UI 功能——脚本/CI/IDE 都需要访问。
**缺失后果**：只有交互式入口 → 自动化场景无法获取上下文健康数据。
**改进收益**：非交互输出 = CI 可观测 + IDE 可集成 + 基准可比较。

---
