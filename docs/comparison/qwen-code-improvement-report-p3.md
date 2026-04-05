# Qwen Code 改进建议 — P3 详细说明

> 低优先级改进项。每项包含：问题场景、现状分析、改进前后对比、实现成本评估、Claude Code 源码索引、Qwen Code 修改方向。
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md)

---

<a id="item-1"></a>

### 1. 动态状态栏（P3）

**问题**：用户让 Agent 分析一个大型项目时，终端只显示一个旋转的 spinner——不知道 Agent 正在做什么、已经处理了多少文件、还要等多久。尤其是 30 秒以上的长时间执行（如全项目 grep、多文件重构），用户只能盯着 spinner 焦虑等待，甚至怀疑 Agent 是否卡住了。

Claude Code 的解决方案：`AppState.statusLineText` 允许模型和工具在执行过程中实时更新状态文本（如"正在分析 5 个文件..."、"正在执行测试套件..."），让用户始终知道当前进度。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `state/AppStateStore.ts` | `statusLineText: string` |
| `components/StatusLine.tsx` | 条件渲染 |

**Qwen Code 现状**：工具执行期间仅显示静态 spinner，无具体进度信息。用户无法区分"正在分析"和"已卡住"。

**Qwen Code 修改方向**：`UIStateContext` 新增 `statusText` 状态；工具执行时通过 `setUIState()` 更新；`Footer.tsx` 渲染。

**实现成本评估**：
- 涉及文件：~4 个
- 新增代码：~100 行
- 开发周期：~1 天（1 人）
- 难点：各工具需逐个接入状态更新回调

**改进前后对比**：
- **改进前**：长时间执行时只有 spinner——"Agent 在干嘛？卡住了吗？"
- **改进后**：动态状态文本实时更新——"正在分析 5/12 个文件..."、"正在运行测试 3/8..."

**意义**：用户不知道 Agent 当前在做什么——长时间执行时焦虑等待。
**缺失后果**：仅有 spinner 无具体信息——'还要等多久？在做什么？'
**改进收益**：动态状态文本——'正在分析 5 个文件...'——减少等待焦虑。

---

<a id="item-2"></a>

### 2. 上下文折叠 History Snip（P3）

**问题**：开发者在一个长会话中做了 20 次 `read_file` 和 15 次 `grep`——这些早期的工具调用结果已经过时（文件可能已被修改），但仍然占据大量上下文空间，增加视觉噪音。用户在滚动查看对话历史时，被大量已过时的文件内容淹没，找不到关键信息。

Claude Code 的方案（**注意：仅 scaffolding，无完整实现**）：`feature('HISTORY_SNIP')` 门控的 SnipTool 有 lazy require 占位但无完整实现。已有的是 `collapseReadSearch.ts` 的 UI 级消息折叠——连续的 read/search 工具调用在 UI 上合并显示为一条，减少视觉干扰（不改变 API 发送的实际内容）。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/collapseReadSearch.ts` | UI 级连续 read/search 折叠 |

**Qwen Code 现状**：所有工具调用结果在 UI 中逐条平铺显示，无折叠能力。20 次连续 read 占据大量屏幕空间。

**Qwen Code 修改方向**：参考方向——连续工具调用的 UI 折叠显示（不改变 API 发送内容）。

**实现成本评估**：
- 涉及文件：~3 个
- 新增代码：~150 行
- 开发周期：~2 天（1 人）
- 难点：识别"连续同类工具调用"的边界条件

**改进前后对比**：
- **改进前**：20 次 read_file 结果逐条平铺——滚动 3 屏才能找到关键对话
- **改进后**：连续 read/search 合并为"已读取 20 个文件"折叠条——点击可展开

**意义**：早期对话占满上下文但内容已过时——比全量压缩更精细的方案。
**缺失后果**：注意：Claude Code 自身仅 scaffolding，无完整实现。参考方向。
**改进收益**：UI 级折叠——连续 read/search 合并显示，减少视觉噪音。

---

<a id="item-3"></a>

### 3. 内存诊断（P3）

**问题**：开发者用 Agent 做长时间重构（50+ 轮对话、大量文件读写），Node.js 进程内存持续增长。到第 40 轮时突然 OOM 崩溃——整个 session 丢失，之前的对话上下文、修改进度全部消失。更糟的是没有任何诊断信息，无法判断是哪个操作导致了内存泄漏。

Claude Code 的解决方案：设定 1.5GB 内存阈值，超限时自动触发 V8 heap snapshot + Linux `smaps_rollup` 解析 + 内存增长率分析，生成泄漏诊断报告。在 OOM 发生前就预警并提供可操作的诊断信息。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/heapDumpService.ts` | 阈值触发 + heap snapshot |

**Qwen Code 现状**：无内存监控机制。进程内存超限时直接 OOM 崩溃，无预警、无诊断信息、无 heap dump。

**Qwen Code 修改方向**：`process.memoryUsage()` 定期检查；超限时 `v8.writeHeapSnapshot()`。

**实现成本评估**：
- 涉及文件：~3 个
- 新增代码：~200 行
- 开发周期：~2 天（1 人）
- 难点：heap snapshot 文件管理（避免磁盘写满）+ 增长率分析算法

**改进前后对比**：
- **改进前**：长会话到第 40 轮突然 OOM 崩溃——session 丢失，无法定位原因
- **改进后**：1.5GB 阈值预警 + 自动 heap snapshot——"内存 1.6GB，疑似 toolResults 数组泄漏"

**意义**：长会话可能内存泄漏——Agent 进程 OOM 导致 session 丢失。
**缺失后果**：无内存监控——OOM 时直接崩溃，无诊断信息。
**改进收益**：1.5GB 阈值预警 + heap snapshot——提前发现并诊断泄漏。

---

<a id="item-4"></a>

### 4. Feature Gates（P3）

**问题**：团队开发了一个新的上下文压缩算法，在内部测试中表现良好。但直接全量发布给所有用户，如果出现边缘 bug（如特定语言项目压缩后丢失关键上下文），影响面是 100% 用户。回滚需要发新版本，期间用户持续受影响。缺乏灰度发布能力，每次新功能上线都是"要么全量成功、要么全量失败"。

Claude Code 的解决方案：集成 GrowthBook 远程特性开关——新功能可按百分比灰度（先 1% 用户验证），支持 A/B 测试和按事件动态采样。出问题时远程关闭 feature flag，无需发版。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `services/analytics/growthbook.ts` | `initializeGrowthBook()`、`getFeatureValue_CACHED_MAY_BE_STALE()` |

**Qwen Code 现状**：无 feature flag 系统。新功能通过代码分支控制，发布即全量上线，无灰度和 A/B 测试能力。

**Qwen Code 修改方向**：集成 GrowthBook SDK 或自建 feature flag 服务。

**实现成本评估**：
- 涉及文件：~5 个
- 新增代码：~300 行
- 开发周期：~3 天（1 人）
- 难点：feature flag 服务端基础设施搭建 + 客户端缓存与刷新策略

**改进前后对比**：
- **改进前**：新功能全量发布——出 bug 影响所有用户，回滚需发新版
- **改进后**：灰度 1% → 10% → 100%——出问题远程关闭 flag，零发版回滚

**意义**：新功能灰度发布降低全量上线风险——A/B 测试数据驱动决策。
**缺失后果**：新功能只能全量发布——出问题影响所有用户。
**改进收益**：渐进式灰度——先 1% 用户验证，确认无问题后全量。

---

<a id="item-5"></a>

### 5. DXT/MCPB 插件包（P3）

**问题**：开发者写了一个 MCP 服务器插件并分享给团队。但插件依赖 3 个 npm 包和 2 个系统库——有人 `npm install` 失败（版本冲突），有人系统库版本不对，有人 Node.js 版本不兼容。松散文件分发导致"在我机器上能跑"问题反复出现。更严重的是，恶意插件可能打包一个 zip bomb（解压后 50GB），耗尽用户磁盘。

Claude Code 的解决方案：`.dxt`/`.mcpb` 单文件打包格式——MCP 服务器 + 所有依赖打包为一个文件，安装时自动解压。内置 zip bomb 防护（512MB/文件、1GB 总量、50:1 压缩比限制）。

**Qwen Code 现状**：MCP 插件以松散文件形式分发，依赖用户自行安装运行环境和依赖包。无打包格式标准，无安全校验。

**Qwen Code 修改方向**：定义包格式（zip + manifest.json）；安装时验证大小/压缩比。

**实现成本评估**：
- 涉及文件：~6 个
- 新增代码：~500 行
- 开发周期：~4 天（1 人）
- 难点：包格式设计（manifest schema）+ zip bomb 检测算法

**改进前后对比**：
- **改进前**：松散文件分发——"npm install 失败了"、"缺少 libxxx.so"
- **改进后**：`qwen install plugin.dxt` 一键安装——依赖全部打包，zip bomb 自动拦截

**意义**：MCP 插件分发需要打包依赖——避免安装环境不一致。
**缺失后果**：松散文件分发——依赖缺失导致安装失败。
**改进收益**：单文件安装 + zip bomb 防护——安全可靠的插件分发。

---

<a id="item-6"></a>

### 6. /security-review（P3）

**问题**：开发者提交了一个 PR，其中包含用户输入直接拼接到 SQL 查询的代码。Code review 时同事没发现（SQL 注入不总是显而易见），合并后上线导致安全事故。Agent 有 `/review` 命令审查代码质量，但没有专门聚焦安全漏洞的审查模式——通用 review 关注的是逻辑正确性和代码风格，容易遗漏 OWASP Top 10 类型的安全问题。

Claude Code 的解决方案：基于 git diff 的安全审查命令，prompt 模板专门聚焦 OWASP Top 10 漏洞检测（SQL 注入、XSS、SSRF、路径遍历等）。

**Qwen Code 现状**：有 `/review` 通用代码审查命令，但无安全专项审查。安全漏洞检测依赖通用 review 的"顺便发现"。

**Qwen Code 修改方向**：新建 `skills/bundled/security-review/SKILL.md`，prompt 模板聚焦安全。

**实现成本评估**：
- 涉及文件：~3 个
- 新增代码：~150 行
- 开发周期：~2 天（1 人）
- 难点：OWASP Top 10 检测 prompt 的准确率调优（减少误报）

**改进前后对比**：
- **改进前**：`/review` 关注代码质量——SQL 注入、XSS 等安全漏洞容易漏检
- **改进后**：`/security-review` 专项扫描——"发现 2 处 SQL 注入风险：line 45, line 89"

**意义**：代码提交前的安全扫描是 DevSecOps 的基本要求。
**缺失后果**：无内置安全审查——安全漏洞可能被合并到代码库。
**改进收益**：基于 diff 的安全审查——聚焦新增代码的 OWASP Top 10。

---

<a id="item-7"></a>

### 7. Ultraplan 远程计划探索（P3）

**问题**：开发者要重构一个 10 万行的微服务架构——涉及 20+ 个服务的 API 变更、数据库迁移、向后兼容性处理。本地 Agent 使用的模型推理能力有限，生成的重构计划遗漏了 3 个关键的跨服务依赖。开发者按照不完整的计划执行到一半才发现问题，不得不回退重来。复杂项目规划需要更强模型的深度推理，但本地 CLI 只能用配置的模型。

Claude Code 的解决方案：启动远程 CCR 会话，用更强的模型（如 Opus）进行深度规划，完成后将结构化计划回传到本地 Agent 执行。

**Qwen Code 现状**：规划仅能使用当前配置的模型，无远程调用更强模型的能力。复杂项目的规划质量受限于本地模型的推理深度。

**Qwen Code 修改方向**：需先有 Web 版本；`--remote` flag 创建云端 session。

**实现成本评估**：
- 涉及文件：~8 个
- 新增代码：~1000 行
- 开发周期：~10 天（1 人）
- 难点：云端执行基础设施搭建 + 本地/远程 session 同步协议

**改进前后对比**：
- **改进前**：本地模型规划复杂重构——遗漏跨服务依赖，执行到一半才发现
- **改进后**：远程调用更强模型深度规划——结构化计划回传本地，覆盖所有依赖

**意义**：复杂项目规划需要更强模型的深度推理——本地模型可能不够。
**缺失后果**：规划仅能用当前模型——深度思考能力受限。
**改进收益**：远程调用更强模型规划——结果回传到本地执行。

---

<a id="item-8"></a>

### 8. Advisor 顾问模型（P3）

**问题**：Agent 使用主模型生成了一段数据库迁移代码，但遗漏了事务回滚处理。代码直接被执行——如果迁移中途失败，数据库处于不一致状态。问题在于主模型输出没有任何审查机制，错误输出直接进入执行流程。对于高风险操作（数据库迁移、生产环境部署脚本、安全相关代码），单一模型的可靠性不够。

Claude Code 的解决方案：`/advisor` 配置副模型（如更强的模型）自动审查主模型输出。通过 `server_tool_use` 方式在主模型响应后自动调用审查模型，无需用户手动触发。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/advisor.ts` | `isAdvisorEnabled()`、GrowthBook `tengu_sage_compass` |

**Qwen Code 现状**：单模型架构，无副模型审查机制。主模型输出直接进入执行流程，错误无法被自动拦截。

**Qwen Code 修改方向**：需多模型同时调用能力；response 后追加审查模型调用。

**实现成本评估**：
- 涉及文件：~5 个
- 新增代码：~400 行
- 开发周期：~4 天（1 人）
- 难点：多模型并行调用架构 + 审查结果与主流程的集成逻辑

**改进前后对比**：
- **改进前**：主模型生成迁移代码直接执行——遗漏事务回滚，失败后数据不一致
- **改进后**：副模型自动审查——"警告：缺少事务回滚处理，建议添加 ROLLBACK"

**意义**：主模型输出质量不稳定——副模型审查可提升可靠性。
**缺失后果**：无审查机制——错误输出可能被直接执行。
**改进收益**：副模型自动审查——发现主模型遗漏的问题。

---

<a id="item-9"></a>

### 9. Vim 完整实现（P3）

**问题**：Vim 用户习惯用 `ciw`（change inner word）、`da"`（delete around quotes）、`yi(`（yank inner parens）等组合快速编辑文本。切换到 Agent CLI 后发现只有基础的 `hjkl` 移动和 `i`/`a` 进入插入模式——text objects 和 operators 都缺失。每次想用 `ciw` 时被迫退回到移动光标 → 选中 → 删除 → 输入的低效流程，手指肌肉记忆不断碰壁。

Claude Code 的解决方案：完整 modal editing 实现——motions（hjkl/w/b/e/0/$）+ operators（d/c/y）+ text objects（iw/aw/i"/a"），4 文件结构，覆盖 Vim 用户的核心编辑习惯。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `keybindings/motions.ts` | hjkl/w/b/e/0/$ |
| `keybindings/operators.ts` | d/c/y |
| `keybindings/textObjects.ts` | iw/aw/i"/a" |

**Qwen Code 现状**：基础 vim 模式——支持 hjkl 移动和模式切换，但缺少 text objects（iw/aw/i"/a"）和 operators（d/c/y 组合）。

**Qwen Code 修改方向**：扩展现有 `vim.ts`——补充 text objects 和 operators。

**实现成本评估**：
- 涉及文件：~4 个
- 新增代码：~600 行
- 开发周期：~4 天（1 人）
- 难点：operator + motion/text-object 组合解析（如 `d2w`、`ci"`）

**改进前后对比**：
- **改进前**：`ciw` 无效——被迫手动移动光标、选中、删除、输入，肌肉记忆碰壁
- **改进后**：`ciw`/`da"`/`yi(` 等组合正常工作——Vim 用户的编辑效率完整保留

**意义**：Vim 用户群体庞大——完整 modal editing 是差异化竞争力。
**缺失后果**：基础 vim 模式缺少 text objects 和 operators——Vim 用户体验不完整。
**改进收益**：完整 Vim 体验——motions + operators + text objects 全覆盖。

---

<a id="item-10"></a>

### 10. 语音模式（P3）

**问题**：开发者正在 review 同事的 PR，双手在键盘上对照代码，想同时让 Agent 查一个函数的历史修改记录。但打字意味着要中断当前的代码阅读流程——切换到 Agent 输入框、打字描述需求、再切回代码。另一个场景：开发者手腕受伤（RSI），长时间打字疼痛，但仍需与 Agent 交互完成工作。键盘是唯一的输入方式，没有替代方案。

Claude Code 的解决方案：push-to-talk 语音输入 + 流式 STT 转录。按住快捷键说话，松开后自动转为文字发送给 Agent。快捷键可通过 `keybindings.json` 重绑。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `commands/voice/` | push-to-talk + STT |
| keybindings: `voice:pushToTalk` | 绑定配置 |

**Qwen Code 现状**：仅支持键盘文字输入，无语音输入能力。

**Qwen Code 修改方向**：需音频捕获 NAPI + STT API（如阿里云 ASR）。

**实现成本评估**：
- 涉及文件：~6 个
- 新增代码：~500 行
- 开发周期：~5 天（1 人）
- 难点：跨平台音频捕获（NAPI 原生模块）+ STT 服务集成与延迟优化

**改进前后对比**：
- **改进前**：只能键盘输入——review 代码时要中断去打字，RSI 用户长时间使用疼痛
- **改进后**：按住快捷键说话即可——"帮我查一下这个函数的 git log"，松开自动发送

**意义**：语音输入解放双手——适合代码审查讨论、快速口述需求。
**缺失后果**：只能键盘输入——手不方便时无法使用。
**改进收益**：push-to-talk 语音输入——说完自动转文字。

---

<a id="item-11"></a>

### 11. 插件市场（P3）

**问题**：开发者写了一个 Python linting 的 hook 插件，想分享给社区。但没有统一的发布渠道——只能发 GitHub 链接让别人手动 clone、手动配置。另一边，用户想找"有没有 Django 专用的 Agent skill"，但无处搜索——只能在论坛帖子和 GitHub 上碰运气。没有插件市场，功能扩展完全依赖官方开发，社区的创造力无法释放。

Claude Code 的解决方案：官方 marketplace——支持插件发布、搜索、安装（hooks/commands/agents/MCP），自动追踪安装状态和版本更新。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/plugins/pluginLoader.ts` | 加载 + marketplace 同步 |
| `utils/plugins/pluginInstaller.ts` | 安装 + 版本管理 |

**Qwen Code 现状**：已有 extension 系统支持本地加载插件，但无集中发现和分发渠道。插件分享依赖手动传播。

**Qwen Code 修改方向**：已有 extension 系统；新增 marketplace 发现 + git-based 安装。

**实现成本评估**：
- 涉及文件：~8 个
- 新增代码：~800 行
- 开发周期：~7 天（1 人）
- 难点：marketplace 后端服务 + 插件审核/安全扫描机制

**改进前后对比**：
- **改进前**：想找 Django skill？论坛搜、GitHub 搜、问人——找到了还要手动 clone 配置
- **改进后**：`qwen marketplace search django` → 一键安装，自动更新

**意义**：插件生态是工具平台化的关键——用户和社区可扩展功能。
**缺失后果**：功能扩展依赖官方开发——社区无法贡献。
**改进收益**：插件市场——社区可发布和发现插件，生态自增长。

**相关文章**：[Hook 与插件扩展](./hook-plugin-extension-deep-dive.md)

---

<a id="item-12"></a>

### 12. sandbox excludedCommands 排除机制（P3）

**问题**：sandbox 模式下所有 shell 命令受限，但某些命令（如 `npm install`）需要网络访问。用户需要逐次审批或全局禁用 sandbox，没有"sandbox 默认开但某些命令排除"的选项。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `tools/BashTool/shouldUseSandbox.ts` | excludedCommands 配置 + GrowthBook 动态列表 |

**Qwen Code 现状**：sandbox 有 984 行实现，但无 excludedCommands 排除机制。

**Qwen Code 修改方向**：设置中新增 `sandbox.excludedCommands` 列表，匹配时跳过 sandbox。

**实现成本评估**：涉及 ~2 个文件，~50 行，~0.5 天。难点：命令匹配粒度（完整命令 vs 前缀）。

**意义**：sandbox 排除 = 安全与便利兼得。
**缺失后果**：要么全 sandbox（`npm install` 每次审批）要么全不 sandbox（无保护）。
**改进收益**：excludedCommands = 安全命令自动放行，危险命令仍受限。

---

<a id="item-13"></a>

### 13. /privacy-settings 交互式隐私对话框（P3）

**问题**：用户想控制哪些数据被收集（遥测/错误报告/使用统计），但只能手动编辑配置文件——不知道有哪些选项、每个选项控制什么。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `commands/privacy-settings/privacy-settings.tsx` | 交互式隐私设置 UI |
| `utils/privacyLevel.ts` | 隐私级别定义 |

**Qwen Code 现状**：有 privacy schema 但无交互式 UI。

**Qwen Code 修改方向**：新增 `/privacy-settings` 命令，展示各隐私选项的开关 + 说明。

**实现成本评估**：涉及 ~2 个文件，~100 行，~1 天。

**意义**：隐私控制透明化——用户知道收集了什么、如何关闭。
**缺失后果**：用户不知道隐私选项 → 要么全开（隐私风险）要么全关（影响改进数据）。
**改进收益**：交互式 UI = 精确控制每项数据收集。

---

<a id="item-14"></a>

### 14. /extra-usage 企业用量管理（P3）

**问题**：企业用户需要查看和管理 API 用量配额——当前用量、剩余额度、历史趋势。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `commands/extra-usage/extra-usage.tsx` | 用量查看 UI |
| `commands/extra-usage/extra-usage-core.ts` | 用量数据获取 |

**Qwen Code 现状**：有 `/cost` 显示当前 session 花费，但无企业级用量管理。

**Qwen Code 修改方向**：新增 `/usage` 命令，对接 DashScope 用量 API 展示配额和历史。

**实现成本评估**：涉及 ~3 个文件，~200 行，~2 天。难点：对接各 API 提供商的用量接口。

**意义**：企业成本管控的基础——看得到才管得住。
**缺失后果**：不知道用了多少配额 → 突然限速 → 任务中断。
**改进收益**：用量可视化 = 提前发现配额不足，主动调整。

---

<a id="item-15"></a>

### 15. /rate-limit-options 限速选项菜单（P3）

**问题**：API 限速时用户只看到错误消息，不知道有什么选项——等待？切换模型？升级套餐？

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `services/rateLimitMessages.ts` | 限速消息格式化 + 选项建议 |
| `hooks/notifs/useRateLimitWarningNotification.tsx` | 限速预警通知 |

**Qwen Code 现状**：限速时显示错误消息，无交互选项。

**Qwen Code 修改方向**：限速时展示选项菜单（等待/切换模型/查看用量）。

**实现成本评估**：涉及 ~2 个文件，~100 行，~1 天。

**意义**：限速是常见场景——给用户选择比让用户困惑好。
**缺失后果**：限速 → 红色错误 → 用户不知道怎么办。
**改进收益**：选项菜单 = 限速时也有行动路径。

---

<a id="item-16"></a>

### 16. /remote-setup CCR 远程环境设置（P3）

**问题**：企业用户需要配置远程执行环境（CCR）——注册 worker、配置认证、测试连接。当前只能手动配置环境变量。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `commands/remote-setup/remote-setup.tsx` | 远程环境配置向导 |

**Qwen Code 现状**：无远程执行环境配置功能。

**Qwen Code 修改方向**：新增 `/remote-setup` 向导——引导用户配置远程执行端点。

**实现成本评估**：涉及 ~3 个文件，~200 行，~2 天。难点：需要先有远程执行基础设施。

**意义**：远程执行是企业级功能的前提。
**缺失后果**：无引导 → 配置复杂 → 企业用户放弃。
**改进收益**：向导引导 = 3 分钟完成远程配置。

---

<a id="item-17"></a>

### 17. Virtual Scrolling 虚拟滚动（P3）

**问题**：长会话（1000+ 轮）时终端滚动卡顿——所有消息节点都在 DOM 中渲染。

**Claude Code 源码索引**：`components/VirtualMessageList.tsx`、`hooks/useVirtualScroll.ts`

**Qwen Code 现状**：无虚拟滚动——所有消息全量渲染。

**Qwen Code 修改方向**：仅渲染可视区域 ± buffer 的消息节点。

**实现成本评估**：~3 文件，~300 行，~3 天。难点：滚动位置精确计算（消息高度不等）。

**意义**：1000+ 轮长会话不卡顿。
**缺失后果**：长会话滚动帧率下降。
**改进收益**：O(visible) 渲染替代 O(total)。

---

<a id="item-18"></a>

### 18. Feedback Survey 用户反馈调查（P3）

**问题**：产品改进需要用户反馈，但没有内置收集机制——用户只能去 GitHub 提 issue。

**Claude Code 源码索引**：`commands/feedback/feedback.tsx`、`components/FeedbackSurvey/`

**Qwen Code 现状**：无内置反馈机制。

**Qwen Code 修改方向**：新增 `/feedback` 命令，展示评分 + 文字反馈表单，提交到后端 API。

**实现成本评估**：~3 文件，~200 行，~2 天。

**意义**：直接从用户处收集结构化反馈。
**缺失后果**：只有 power user 会去 GitHub 提 issue——沉默的大多数无法反馈。
**改进收益**：内置反馈 = 降低反馈门槛 → 收集更多改进意见。

---

<a id="item-19"></a>

### 19. Turn Diffs 轮次差异统计（P3）

**问题**：Agent 执行了多轮编辑后，用户想看"这一轮改了什么"的汇总——而非逐个文件查看 diff。

**Claude Code 源码索引**：`utils/gitDiff.ts`、`components/diff/DiffDialog.tsx`

**Qwen Code 现状**：有 per-file diff 展示，但无按轮次汇总的差异统计（哪些文件改了、增删多少行）。

**Qwen Code 修改方向**：每轮工具执行后用 `git diff --numstat` 生成变更统计，展示在轮次结束时。

**实现成本评估**：~2 文件，~100 行，~1 天。

**意义**：每轮变更一目了然——快速审查 Agent 做了什么。
**缺失后果**：需要逐个文件查看 diff → 大变更时容易遗漏。
**改进收益**：轮次统计 = "改了 5 个文件，+120/-30 行" → 快速评估变更规模。

---

<a id="item-20"></a>

### 20. LogoV2 品牌标识与启动动画（P3）

**问题**：CLI 启动时只显示版本号——缺少品牌辨识度和功能引导。

**Claude Code 源码索引**：`components/LogoV2/`

**Qwen Code 现状**：启动显示基础文本信息。

**Qwen Code 修改方向**：设计 ASCII art logo + 启动时显示"新功能提示"（如"试试 /plan 命令"）。

**实现成本评估**：~2 文件，~100 行，~0.5 天。

**意义**：品牌辨识 + 功能引导——低成本高感知。
**缺失后果**：纯文本启动 → 缺少品牌感 → 新用户不知道有什么功能。
**改进收益**：Logo + tips = 品牌辨识 + 功能发现率提升。

---

<a id="item-21"></a>

### 21. Buddy 伴侣精灵系统（P3）

**问题**：Agent 在后台执行长任务时，用户不知道它在做什么——只有 spinner 转圈。缺少一个"可见的助手"让交互更有温度。

**Claude Code 源码索引**：`buddy/companion.ts`、`buddy/CompanionSprite.tsx`、`buddy/useBuddyNotification.tsx`

**Qwen Code 现状**：无 Buddy/Companion 概念。

**Qwen Code 修改方向**：可选的伴侣精灵——在空闲时展示提示、执行时显示状态动画、完成时播放反馈。通过 `feature('BUDDY')` 门控。

**实现成本评估**：~4 文件，~300 行，~3 天。难点：动画不干扰正常输出。

**意义**：交互温度——让 CLI 从"冷冰冰的工具"变成"有温度的助手"。
**缺失后果**：纯文本界面 → 长时间等待无反馈 → 用户焦虑。
**改进收益**：伴侣精灵 = 状态可视 + 空闲引导 + 情感连接。

---

<a id="item-22"></a>

### 22. useMoreRight 右面板扩展（P3）

**问题**：终端宽度有限，Agent 输出和用户输入共用同一列。想同时看文件内容和 Agent 回复，只能开两个终端窗口。

**Claude Code 源码索引**：`moreright/useMoreRight.tsx`

**Qwen Code 现状**：单列布局，无侧面板概念。

**Qwen Code 修改方向**：在支持宽终端的环境中，右侧面板展示文件预览/diff/任务列表——主区域保持对话。

**实现成本评估**：~3 文件，~300 行，~3 天。难点：终端宽度检测 + 响应式布局。

**意义**：信息密度提升——同时看对话和文件内容。
**缺失后果**：单列 → 频繁切换上下文 → 效率低。
**改进收益**：右面板 = 对话 + 预览并排 → 无需切换窗口。

---

<a id="item-23"></a>

### 23. iTerm/Apple Terminal 状态备份与恢复（P3）

**问题**：Agent 运行时接管了终端（alt-screen、鼠标追踪、键盘模式等）。如果异常退出（OOM/SIGKILL），终端状态残留——光标消失、鼠标滚轮失效、键盘回显丢失。用户只能输入 `reset` 修复。

**Claude Code 源码索引**：`utils/gracefulShutdown.ts` 中的 `cleanupTerminalModes()` 同步恢复 + iTerm2/Apple Terminal 特有的状态保存/恢复序列。

**Qwen Code 现状**：`process.on('exit')` 中有基础清理，但无 iTerm2/Apple Terminal 特有的状态备份机制。

**Qwen Code 修改方向**：① 启动时保存终端状态快照（iTerm2 用 DECSC/DECRC，Apple Terminal 用 CSI 序列）；② 退出时（包括 SIGINT/SIGTERM）同步恢复；③ 异常退出后下次启动时检测并修复残留状态。

**实现成本评估**：~2 文件，~100 行，~1 天。难点：不同终端模拟器的转义序列差异。

**意义**：终端状态是用户工作环境的一部分——Agent 不应破坏它。
**缺失后果**：异常退出 → 终端状态残留 → 用户需手动 `reset`。
**改进收益**：状态备份/恢复 = 无论如何退出，终端始终健康。

---

<a id="item-24"></a>

### 24. 设置同步服务 settingsSync（P3）

**问题**：用户在多台机器上使用 Agent（公司电脑 + 家里笔记本），每台都要重新配置主题/模型/权限/快捷键。没有跨设备设置同步机制。

**Claude Code 源码索引**：`services/settingsSync/`（index.ts + types.ts）

**Qwen Code 现状**：设置存储在本地 `~/.qwen/` 目录，无跨设备同步。

**Qwen Code 修改方向**：① 设置序列化为 JSON + 版本号；② 可选同步到云端（DashScope 账号关联）或 git repo；③ 冲突合并策略（时间戳优先或手动选择）。

**实现成本评估**：~4 文件，~300 行，~3 天。难点：设置合并冲突解决。

**意义**：多设备用户体验一致。
**缺失后果**：每台机器重新配置 → 体验不一致。
**改进收益**：设置同步 = 任何设备拿起即用。

---

<a id="item-25"></a>

### 25. Auto Mode 子命令管理（P3）

**问题**：Auto mode（自动批准模式）的分类规则对用户不透明——哪些工具自动批准？规则从哪里来？用户自定义规则写对了吗？

**Claude Code 源码索引**：`cli/handlers/autoMode.ts`（170 行）——提供 3 个子命令：
- `defaults`：dump 默认分类规则
- `config`：查看当前有效配置
- `critique`：让模型审查用户自定义规则是否合理

**Qwen Code 现状**：有 auto mode 但无子命令管理——用户不知道默认规则是什么，自定义规则是否生效。

**Qwen Code 修改方向**：① 新增 `auto defaults` 展示默认规则；② `auto config` 显示合并后的有效配置；③ `auto critique` 审查用户规则。

**实现成本评估**：~2 文件，~150 行，~1 天。

**意义**：Auto mode 规则透明化——用户知道什么被自动批准了。
**缺失后果**：规则不透明 → 用户不敢用 auto mode → 回退到手动批准。
**改进收益**：子命令 = 规则可查可审 → 用户放心启用 auto mode。

---

<a id="item-26"></a>

### 26. useInboxPoller 收件箱轮询（P3）

**问题**：多 Agent（Swarm/Teammate）协作时，Agent 需要定期检查是否有来自其他 Agent 或用户的新消息——但当前没有统一的收件箱轮询机制。

**Claude Code 源码索引**：`hooks/useInboxPoller.ts`

**Qwen Code 现状**：Arena 系统用文件 IPC 但无统一的收件箱轮询 hook。

**Qwen Code 修改方向**：新增 `useInboxPoller` hook——定期检查邮箱文件变更，有新消息时触发回调。

**实现成本评估**：~2 文件，~100 行，~1 天。

**意义**：多 Agent 通信的基础设施——没有轮询就无法及时响应消息。
**缺失后果**：Agent 间消息延迟 → 协作效率低。
**改进收益**：定期轮询 = 及时响应 → 多 Agent 协作流畅。

---

<a id="item-27"></a>

### 27. useRemoteSession 远程会话 Hook（P3）

**Claude Code 源码**：`hooks/useRemoteSession.ts` — Remote Control Bridge 的 React hook 封装，管理远程会话连接/断开/重连状态。

**Qwen Code 现状**：无远程会话 hook。**实现成本**：~1 文件，~100 行，~1 天。

---

<a id="item-28"></a>

### 28. useDiffInIDE IDE 差异查看（P3）

**Claude Code 源码**：`hooks/useDiffInIDE.ts` — 将 Agent 的文件编辑 diff 发送到 IDE（VS Code）中以原生 diff view 打开，比终端内 diff 更易读。

**Qwen Code 现状**：diff 仅在终端显示。**实现成本**：~2 文件，~100 行，~1 天。

---

<a id="item-29"></a>

### 29. useCancelRequest 取消请求 Hook（P3）

**Claude Code 源码**：`hooks/useCancelRequest.ts` — 统一的取消请求处理（Escape 键 / Ctrl+C），区分"取消当前工具"和"取消整个轮次"。

**Qwen Code 现状**：取消处理分散在各处。**实现成本**：~1 文件，~80 行，~0.5 天。

---

<a id="item-30"></a>

### 30. AgentSummary 代理摘要服务（P3）

**Claude Code 源码**：`services/AgentSummary/agentSummary.ts` — Agent 完成任务后生成结构化摘要（修改了哪些文件、关键决策、遇到的问题）。

**Qwen Code 现状**：无 Agent 完成后的结构化摘要。**实现成本**：~2 文件，~200 行，~2 天。

---

<a id="item-31"></a>

### 31. useBackgroundTaskNavigation 后台任务导航（P3）

**Claude Code 源码**：`components/tasks/BackgroundTasksDialog.tsx` — 在多个后台 Agent 间快速切换，查看各自进度和输出。

**Qwen Code 现状**：后台任务无导航 UI。**实现成本**：~2 文件，~150 行，~1 天。

---

<a id="item-32"></a>

### 32. useTaskListWatcher 任务列表监控（P3）

**Claude Code 源码**：`hooks/useTaskListWatcher.ts` — 监控共享任务文件变更，任务状态变化时自动刷新 UI。

**Qwen Code 现状**：无任务文件监控。**实现成本**：~1 文件，~80 行，~0.5 天。

---

<a id="item-33"></a>

### 33. useDirectConnect 直连 Hook（P3）

**Claude Code 源码**：`server/createDirectConnectSession.ts`、`server/directConnectManager.ts` — 无需中继服务器的直连模式，适用于本地 IDE 与 CLI 同机通信。

**Qwen Code 现状**：无直连模式。**实现成本**：~3 文件，~200 行，~2 天。

---

<a id="item-34"></a>

### 34. useAssistantHistory 代理历史 Hook（P3）

**Claude Code 源码**：`hooks/useAssistantHistory.ts` — 追踪当前 session 中所有 assistant 消息的历史，支持快速定位和回溯。

**Qwen Code 现状**：无独立的 assistant 历史追踪 hook。**实现成本**：~1 文件，~80 行，~0.5 天。

---

<a id="item-35"></a>

### 35. useSSHSession SSH 会话 Hook（P3）

**Claude Code 源码**：`hooks/useSSHSession.ts` — SSH 连接会话管理，支持本地 terminal 通过 SSH 连接到远程机器上的 Agent。

**Qwen Code 现状**：无 SSH 会话支持。**实现成本**：~2 文件，~150 行，~2 天。

---

<a id="item-36"></a>

### 36. useSwarmPermissionPoller Swarm 权限轮询（P3）

**Claude Code 源码**：`hooks/useSwarmPermissionPoller.ts` — 多 Agent Swarm 模式下定期检查是否有来自 Teammate 的权限请求需要 Leader 审批。

**Qwen Code 现状**：无 Swarm 权限轮询。**实现成本**：~1 文件，~100 行，~1 天。

---

<a id="item-37"></a>

### 37. useTasksV2 任务 V2 Hook（P3）

**Claude Code 源码**：`hooks/useTasksV2.ts` — Task 框架的 React hook 封装，提供任务增删改查 + 实时刷新。

**Qwen Code 现状**：无 Task hook。**实现成本**：~1 文件，~100 行，~1 天。

---

<a id="item-38"></a>

### 38. useArrowKeyHistory 箭头键历史导航（P3）

**Claude Code 源码**：`hooks/useArrowKeyHistory.ts` — 用 ↑/↓ 箭头键浏览之前的输入命令（类似 shell history），无需重新输入。

**Qwen Code 现状**：无命令历史导航。**实现成本**：~1 文件，~80 行，~0.5 天。

---

<a id="item-39"></a>

### 39. useCanUseTool 工具可用性 Hook（P3）

**Claude Code 源码**：`hooks/useCanUseTool.ts` — 检查指定工具在当前权限模式下是否可用，用于 UI 条件渲染（灰显不可用工具）。

**Qwen Code 现状**：权限检查在工具执行时才做，无预检 hook。**实现成本**：~1 文件，~80 行，~0.5 天。

---

<a id="item-40"></a>

### 40. useSearchInput 输入搜索 Hook（P3）

**Claude Code 源码**：`hooks/useSearchInput.ts` — Transcript Search 的输入层 hook，处理搜索框激活/去激活、关键词状态、匹配导航。

**Qwen Code 现状**：无搜索输入 hook。**实现成本**：~1 文件，~80 行，~0.5 天。

---

<a id="item-41"></a>

### 41. usePasteHandler 粘贴处理 Hook（P3）

**Claude Code 源码**：`hooks/usePasteHandler.ts` — 统一的粘贴事件处理——检测粘贴内容类型（文本/图片/文件路径），图片自动转为 base64 附件，文件路径转为 @引用。

**Qwen Code 现状**：有图片粘贴支持但处理逻辑分散。**实现成本**：~1 文件，~100 行，~1 天。

---

<a id="item-42"></a>

### 42. useScheduledTasks 定时任务 Hook（P3）

**Claude Code 源码**：`hooks/useScheduledTasks.ts` — Cron 定时任务的 React hook 封装，提供任务列表渲染 + 状态更新 + 到期检测。

**Qwen Code 现状**：有 CronScheduler 但无 UI hook。**实现成本**：~1 文件，~80 行，~0.5 天。

---

<a id="item-43"></a>

### 43. useVimInput Vim 输入 Hook（P3）

**Claude Code 源码**：`hooks/useVimInput.ts` — Vim 模式的输入处理 hook，管理 normal/insert/visual 模式切换和按键映射。

**Qwen Code 现状**：有基础 vim.ts 但无独立 hook。**实现成本**：~1 文件，~100 行，~1 天。

---

<a id="item-44"></a>

### 44. useLspPluginRecommendation LSP 插件推荐（P3）

**Claude Code 源码**：`hooks/useLspPluginRecommendation.tsx` — 根据项目语言自动推荐安装对应 LSP 插件（如检测到 .py 推荐 Python LSP）。

**Qwen Code 现状**：无 LSP 插件推荐。**实现成本**：~1 文件，~80 行，~1 天。

---

<a id="item-45"></a>

### 45. unifiedSuggestions 统一建议服务（P3）

**Claude Code 源码**：`utils/suggestions/unifiedSuggestions.ts` — 合并 command/path/history 三层补全建议为统一排序列表。

**Qwen Code 现状**：补全建议分散在各处。**实现成本**：~1 文件，~100 行，~1 天。

---

<a id="item-46"></a>

### 46. useInputBuffer 输入缓冲 Hook（P3）

**Claude Code 源码**：`hooks/useInputBuffer.ts` — 管理用户输入的缓冲区（多行编辑、composition 事件、粘贴合并），防止快速输入丢字。

**Qwen Code 现状**：输入直接处理无缓冲。**实现成本**：~1 文件，~80 行，~0.5 天。

---

<a id="item-47"></a>

### 47. useIssueFlagBanner 问题标志 Banner（P3）

**Claude Code 源码**：`hooks/useIssueFlagBanner.ts` — 检测已知问题（如 API 降级、版本过旧）并在终端顶部显示 banner 通知。

**Qwen Code 现状**：无问题 banner 机制。**实现成本**：~1 文件，~80 行，~0.5 天。

---

<a id="item-48"></a>

### 48. useDiffData 差异数据 Hook（P3）

**Claude Code 源码**：`hooks/useDiffData.ts` — 文件编辑的 diff 数据管理 hook，提供 before/after 内容对比 + 行级差异计算。

**Qwen Code 现状**：diff 计算在组件内部。**实现成本**：~1 文件，~80 行，~0.5 天。

---

<a id="item-49"></a>

### 49. toolUseSummary 工具使用摘要（P3）

**Claude Code 源码**：`services/toolUseSummary/` — 每轮对话结束后生成工具使用摘要（调用了哪些工具、结果如何、耗时多久）。

**Qwen Code 现状**：无工具使用摘要。**实现成本**：~2 文件，~150 行，~1 天。

---

<a id="item-50"></a>

### 50. useAwaySummary 离开摘要 Hook（P3）

**Claude Code 源码**：`hooks/useAwaySummary.ts` — 用户离开后返回时，自动生成"你离开期间发生了什么"的摘要。

**Qwen Code 现状**：无离开摘要。**实现成本**：~1 文件，~100 行，~1 天。

---

<a id="item-51"></a>

### 51. useCommandKeybindings 命令快捷键 Hook（P3）

**Claude Code 源码**：`hooks/useCommandKeybindings.tsx` — 将 slash command 与快捷键绑定的 React hook。

**Qwen Code 现状**：快捷键与命令分离管理。**实现成本**：~1 文件，~80 行，~0.5 天。

---

<a id="item-52"></a>

### 52. usePluginRecommendationBase 插件推荐基础 Hook（P3）

**Claude Code 源码**：`hooks/usePluginRecommendationBase.tsx` — 插件推荐的基础逻辑（检测项目类型→匹配可用插件→展示推荐）。

**Qwen Code 现状**：无插件推荐。**实现成本**：~1 文件，~100 行，~1 天。

---

<a id="item-53"></a>

### 53. useSkillImprovementSurvey 技能改进调查 Hook（P3）

**Claude Code 源码**：`hooks/useSkillImprovementSurvey.ts` — 在用户使用 skill 后收集"这个 skill 好用吗"的反馈。

**Qwen Code 现状**：无 skill 反馈收集。**实现成本**：~1 文件，~80 行，~0.5 天。

---

<a id="item-54"></a>

### 54. usePrStatus PR 状态 Hook（P3）

**Claude Code 源码**：`hooks/usePrStatus.ts` — 追踪当前 session 关联的 PR 状态（open/merged/closed/CI status）。

**Qwen Code 现状**：无 PR 状态追踪。**实现成本**：~1 文件，~100 行，~1 天。

---

<a id="item-55"></a>

### 55. useLogMessages 日志消息 Hook（P3）

**Claude Code 源码**：`hooks/useLogMessages.ts` — 统一的日志消息管理 hook，收集各组件的调试/信息/警告消息用于诊断。

**Qwen Code 现状**：日志分散在各处。**实现成本**：~1 文件，~80 行，~0.5 天。

---

<a id="item-56"></a>

### 56. useVoice 语音输入 Hook（P3）

**做什么**：Claude Code 的 useVoice Hook——按住快捷键说话，自动 STT 转文字：

**关键源码**：

| 文件 | 行数 | 职责 |
|------|------|------|
| `hooks/useVoice.ts` | 1144 | 语音输入——录音、STT 流式转录、多语言 |

**Qwen Code 现状**：Qwen Code **完全没有语音输入功能**。

**Qwen Code 修改方向**：新建 `hooks/useVoice.ts`。

**实现成本评估**：
- 涉及文件：~3 个
- 新增代码：~800 行
- 开发周期：~5 天（1 人）

---

<a id="item-57"></a>

### 57. useVoiceIntegration 语音集成 Hook（P3）

**做什么**：Claude Code 的 useVoiceIntegration Hook——语音输入与主 UI 集成：

**关键源码**：

| 文件 | 行数 | 职责 |
|------|------|------|
| `hooks/useVoiceIntegration.ts` | 676 | 语音输入集成 |

**Qwen Code 现状**：Qwen Code **完全没有语音输入功能**。

**Qwen Code 修改方向**：新建 `hooks/useVoiceIntegration.ts`。

**实现成本评估**：
- 涉及文件：~2 个
- 新增代码：~500 行
- 开发周期：~3 天（1 人）

---

<a id="item-58"></a>

### 58. useIdeSelection IDE 选择 Hook（P3）

**做什么**：Claude Code 的 useIdeSelection Hook——IDE 代码选择集成：

**关键源码**：

| 文件 | 行数 | 职责 |
|------|------|------|
| `hooks/useIdeSelection.ts` | 150 | IDE 代码选择 |

**Qwen Code 现状**：Qwen Code 有 IDE 集成，但**没有 useIdeSelection Hook**。

**Qwen Code 修改方向**：新建 `hooks/useIdeSelection.ts`。

**实现成本评估**：
- 涉及文件：~1 个
- 新增代码：~100 行
- 开发周期：~1 天（1 人）

---

<a id="item-59"></a>

### 59. useSessionBackgrounding 会话后台化 Hook（P3）

**做什么**：Claude Code 的 useSessionBackgrounding Hook——会话后台化/前台化切换：

**关键源码**：

| 文件 | 行数 | 职责 |
|------|------|------|
| `hooks/useSessionBackgrounding.ts` | 158 | 会话后台化 |

**Qwen Code 现状**：Qwen Code 有 `--background` 启动，但**没有交互式会话后台化 Hook**。

**Qwen Code 修改方向**：新建 `hooks/useSessionBackgrounding.ts`。

**实现成本评估**：
- 涉及文件：~1 个
- 新增代码：~100 行
- 开发周期：~1 天（1 人）

---

<a id="item-60"></a>

### 60. useClaudeCodeHintRecommendation 提示推荐 Hook（P3）

**做什么**：Claude Code 的 useClaudeCodeHintRecommendation Hook——显示提示推荐：

**关键源码**：

| 文件 | 行数 | 职责 |
|------|------|------|
| `hooks/useClaudeCodeHintRecommendation.ts` | 128 | 提示推荐 |

**Qwen Code 现状**：Qwen Code **没有提示推荐功能**。

**Qwen Code 修改方向**：新建 `hooks/useClaudeCodeHintRecommendation.ts`。

**实现成本评估**：
- 涉及文件：~1 个
- 新增代码：~80 行
- 开发周期：~0.5 天（1 人）

---

<a id="item-61"></a>

### 61. /sandbox-toggle 沙箱切换命令（P3）

**做什么**：Claude Code 的 /sandbox-toggle 命令——交互式切换沙箱模式：

**关键源码**：

| 文件 | 行数 | 职责 |
|------|------|------|
| `commands/sandbox-toggle/sandbox-toggle.tsx` | 132 | 沙箱切换 UI |

**Qwen Code 现状**：Qwen Code 有沙箱支持，但**没有交互式切换命令**。

**Qwen Code 修改方向**：新建 `/sandbox-toggle` 命令。

**实现成本评估**：
- 涉及文件：~2 个
- 新增代码：~100 行
- 开发周期：~1 天（1 人）

---

<a id="item-62"></a>

### 62. /thinkback-play 回忆回放命令（P3）

**做什么**：Claude Code 的 /thinkback-play 命令——播放 Thinkback 动画：

**关键源码**：

| 文件 | 行数 | 职责 |
|------|------|------|
| `commands/thinkback-play/thinkback-play.ts` | 60 | 回忆动画播放 |

**Qwen Code 现状**：Qwen Code **没有回忆回放功能**。

**Qwen Code 修改方向**：新建 `/thinkback-play` 命令。

**实现成本评估**：
- 涉及文件：~1 个
- 新增代码：~40 行
- 开发周期：~0.5 天（1 人）
