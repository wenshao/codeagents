# Qwen Code 改进建议 — P2 详细说明

> 中等优先级改进项。每项包含：思路概述、Claude Code 源码索引、Qwen Code 修改方向。
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md)

---

<a id="item-23"></a>

### 23. Shell 安全增强（P2）

**思路**：在 AST 读写分类基础上，补充专项检查——IFS 注入、Unicode 空白、Zsh 危险命令、花括号展开等。AST 是主路径（精确），专项检查是补充（覆盖面）。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `tools/BashTool/bashSecurity.ts` (2592行) | 25+ validators 管线、`COMMAND_SUBSTITUTION_PATTERNS`（12 种）、`ZSH_DANGEROUS_COMMANDS`（18 个） |
| `utils/bash/treeSitterAnalysis.ts` (506行) | AST 辅助消除 `find -exec \;` 误报 |

**Qwen Code 修改方向**：`shellAstParser.ts` 保持 AST 主路径不变；新增 `shellSecurityChecks.ts` 补充 IFS/Unicode/Zsh 检查，AST 判定 read-only 后仍过一遍专项检查。

**相关文章**：[Shell 安全模型](./shell-security-deep-dive.md)

**意义**：Shell 命令是 Agent 最危险的工具——注入攻击可能造成系统损害。
**缺失后果**：AST-only 不覆盖 IFS 注入、Unicode 空白、Zsh 命令等边缘攻击。
**改进收益**：AST 主路径 + 专项检查补充——覆盖面与精确度兼得。

---

<a id="item-24"></a>

### 24. MDM 企业策略（P2）

**思路**：通过 OS-native 方式读取企业策略——macOS plist、Windows Registry、Linux 文件。5 级 First-Source-Wins 优先级（Remote > HKLM > file > drop-in > HKCU）。启动时子进程并行读取避免阻塞。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/settings/mdm/constants.ts` | `com.anthropic.claudecode` domain、Registry keys |
| `utils/settings/mdm/rawRead.ts` | 子进程 plutil/reg query（5s 超时） |
| `utils/settings/mdm/settings.ts` | First-Source-Wins 合并逻辑 |

**Qwen Code 修改方向**：新建 `utils/settings/mdm/`；在 `config.ts` 初始化时并行读取 plist/Registry；settings 合并时 MDM 优先级最高。

**相关文章**：[MDM 企业配置管理](./mdm-enterprise-deep-dive.md)

**意义**：企业 IT 需集中管控 AI Agent 配置——禁用危险模式、限制模型、强制遥测。
**缺失后果**：用户可自行覆盖所有配置——无管理员锁定能力。
**改进收益**：通过 MDM 策略锁定关键配置——满足 SOC 2 / HIPAA 合规。

---

<a id="item-25"></a>

### 25. API 实时 Token 计数（P2）

**思路**：3 层回退——API `countTokens()` → Haiku 小模型回退 → 粗估（4 bytes/token）。每次 API 调用前精确计数，比静态模式匹配更准确。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `services/tokenEstimation.ts` (495行) | `countTokensWithAPI()`、`roughTokenCountEstimation()`、`TOKEN_COUNT_THINKING_BUDGET = 1024` |
| `services/vcr.ts` | `withTokenCountVCR()`（SHA1 hash 缓存） |

**Qwen Code 修改方向**：调用 DashScope/Gemini 的 token 计数 API 替代 `tokenLimits.ts` 的静态模式匹配；加缓存层避免重复计数。

**相关文章**：[Token 估算与 Thinking](./token-estimation-deep-dive.md)

**意义**：上下文窗口占用率是触发压缩和防溢出的关键指标——估算不准会导致过早或过晚压缩。
**缺失后果**：静态模式匹配估算不精确——可能触发不必要压缩或溢出。
**改进收益**：API 实时计数——压缩触发更准确，避免浪费和溢出。

---

<a id="item-26"></a>

### 26. Output Styles（P2）

**思路**：内置 Learning（暂停要求用户写代码，插入 `TODO(human)` 占位符）和 Explanatory（添加 "Insight" 教育块）两种模式。通过 settings 或 plugin 可扩展自定义 style。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `constants/outputStyles.ts` (216行) | `Explanatory`、`Learning`（20+ 行函数触发、2-10 行贡献请求） |
| `utils/outputStyles.ts` | `getAllOutputStyles()`（built-in + plugin + settings 合并） |

**Qwen Code 修改方向**：新建 `core/outputStyles.ts`；系统提示中根据 `settings.outputStyle` 注入 style 指令。

**相关文章**：[Git 工作流与会话管理](./git-workflow-session-deep-dive.md)

**意义**：教学和培训场景需要 Agent 引导用户动手实践，而非直接给出答案。
**缺失后果**：Agent 只有一种输出风格——无法适应教学需求。
**改进收益**：Learning 模式让 Agent 变教练——暂停、出题、等用户实现后继续。

---

<a id="item-27"></a>

### 27. Fast Mode（P2）

**思路**：同一模型（如 Opus 4.6）的标准/快速推理切换。快速模式 $30/$150/Mtok（标准 $5/$25）。含冷却机制——429 后自动回退到标准，冷却结束恢复。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/fastMode.ts` (532行) | `isFastModeAvailable()`、`triggerFastModeCooldown()`、`FastModeState` |
| `commands/fast/fast.tsx` | /fast 命令 UI + 定价显示 |

**Qwen Code 修改方向**：需后端支持速度分级；`modelCommand.ts` 新增 `--fast` toggle（非指定备用模型）；UI 显示当前速度档位。

**相关文章**：[成本追踪与 Fast Mode](./cost-fastmode-deep-dive.md)

**意义**：时间敏感任务（紧急 bug 修复）需要更快推理，日常任务需要更低成本。
**缺失后果**：用户无法灵活平衡速度和成本——始终使用同一速度。
**改进收益**：一键切换推理速度——紧急用 Fast，日常用 Standard，同一模型同一上下文。

---

<a id="item-28"></a>

### 28. Computer Use 桌面自动化（P2）

**思路**：通过 MCP Server 桥接原生模块——截图（SCContentFilter）、鼠标/键盘（Rust enigo NAPI）、剪贴板操作。TCC 权限门控 + GrowthBook 特性开关 + 订阅检查。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/computerUse/executor.ts` | `moveMouse()`、`click()`、`type()`、截图 JPEG 0.75 |
| `utils/computerUse/mcpServer.ts` | 进程内 MCP Server（stdio） |
| `utils/computerUse/gates.ts` | GrowthBook `tengu_malort_pedway` |

**Qwen Code 修改方向**：新建 `packages/computer-use/` 原生模块；注册为 MCP Server；`settingsSchema.ts` 新增门控。

**相关文章**：[Computer Use 桌面自动化](./computer-use-deep-dive.md)

**意义**：前端调试和跨应用自动化需要 Agent '看到' 桌面——截图、点击、打字。
**缺失后果**：Agent 只能操作文件和终端——无法操作浏览器/IDE/桌面应用。
**改进收益**：解锁跨应用工作流——自动验证 UI、提取设计稿、操作数据库 GUI。

---

<a id="item-29"></a>

### 29. Denial Tracking（P2）

**思路**：记录权限分类器的连续拒绝/成功次数（`maxConsecutive: 3`, `maxTotal: 20`）。超限时自动回退到 prompting 模式，避免分类器陷入"全拒绝"死循环。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/permissions/denialTracking.ts` (45行) | `DENIAL_LIMITS`、`recordDenial()`、`shouldFallbackToPrompting()` |

**Qwen Code 修改方向**：`permission-manager.ts` 新增 `DenialTrackingState`；auto-edit/yolo 模式拒绝时累计；超限回退到 default 模式。

**意义**：权限分类器可能陷入连续拒绝的死循环——用户完全无感知。
**缺失后果**：分类器可能永久阻塞合法操作——'静默失败'。
**改进收益**：连续拒绝自动检测 → 回退到手动确认——用户看到被拒操作并可批准。

---

<a id="item-30"></a>

### 30. 并发 Session 管理（P2）

**思路**：PID 文件（`~/.claude/sessions/{pid}.json`）追踪多终端会话——记录 kind（interactive/bg/daemon）、cwd、startedAt。`countConcurrentSessions()` 扫描并过滤已退出进程。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/concurrentSessions.ts` (204行) | `registerSession()`、`countConcurrentSessions()`、退出时 `registerCleanup()` |

**Qwen Code 修改方向**：新建 `utils/concurrentSessions.ts`；`gemini.tsx` 启动时注册 PID 文件；退出时自动清理。

**相关文章**：[成本追踪与 Fast Mode](./cost-fastmode-deep-dive.md)

**意义**：开发者常在多终端运行多个 Agent 实例——需要追踪和管理。
**缺失后果**：无法了解其他终端的 Agent 状态——可能重复执行相同任务。
**改进收益**：PID 追踪 + 后台脱附——多终端并行工作不冲突。

---

<a id="item-31"></a>

### 31. Git Diff 统计（P2）

**思路**：两阶段 diff——`git diff --numstat` 快速探测（文件数 + 行数），再 `git diff` 完整 hunks。限制：50 文件、1MB/文件、400 行/文件。merge/rebase 期间跳过。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/gitDiff.ts` (532行) | `MAX_FILES = 50`、`MAX_DIFF_SIZE_BYTES = 1_000_000`、hunks 解析 |

**Qwen Code 修改方向**：`gitWorktreeService.ts` 的 simple-git 调用替换为原生 `git diff --numstat` 解析；添加文件数/大小限制。

**相关文章**：[Git 工作流与会话管理](./git-workflow-session-deep-dive.md)

**意义**：编辑后的 diff 统计帮助用户在 commit 前了解变更影响范围。
**缺失后果**：无 git-aware diff——用户需手动 git diff 检查变更。
**改进收益**：编辑后自动展示按文件统计的 diff——变更一目了然。

---

<a id="item-32"></a>

### 32. 文件历史快照（P2）

**思路**：编辑前自动备份（SHA256 + mtime），按消息粒度创建快照（上限 100 个/session）。支持回滚到任意消息时刻——比 git checkpoint 更细粒度。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/fileHistory.ts` (1115行) | `fileHistoryTrackEdit()`、`fileHistoryMakeSnapshot()`、`MAX_SNAPSHOTS = 100` |

**Qwen Code 修改方向**：`edit.ts` 和 `write-file.ts` 编辑前调用 snapshot；新建 `fileHistory.ts` 管理备份目录。

**相关文章**：[Git 工作流与会话管理](./git-workflow-session-deep-dive.md)

**意义**：细粒度文件恢复比 git checkout 更灵活——可回滚到任意消息时刻。
**缺失后果**：恢复粒度粗（git 级）——只能回到 checkpoint，不能回到特定消息。
**改进收益**：按消息粒度恢复——Agent 第 3 步改错了可直接回到第 2 步。

---

<a id="item-33"></a>

### 33. Deep Link 协议（P2）

**思路**：`claude-cli://open?q=&cwd=&repo=` URI scheme——OS 协议注册（macOS .app / Linux .desktop / Windows Registry）→ 终端自动检测（10+ 终端优先级链）→ 预填充 prompt。安全：来源 banner + 手动 Enter 确认。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/deepLink/parseDeepLink.ts` | URI 解析 + 参数验证（≤5000 字符） |
| `utils/deepLink/terminalLauncher.ts` | 10+ 终端检测（iTerm/Ghostty/Kitty/...） |
| `utils/deepLink/registerProtocol.ts` | macOS/Linux/Windows 协议注册 |

**Qwen Code 修改方向**：新建 `utils/deepLink/`；注册 `qwen-code://` scheme；`gemini.tsx` 新增 `--handle-uri` 参数。

**相关文章**：[Deep Link 协议](./deep-link-protocol-deep-dive.md)

**意义**：从浏览器/IDE/Slack 一键启动 Agent 减少上下文切换成本。
**缺失后果**：每次都需打开终端 + cd 到项目目录 + 输入命令——切换成本高。
**改进收益**：点击链接即启动——预填充 prompt + 自动定位项目目录。

---

<a id="item-34"></a>

### 34. Plan 模式 Interview（P2）

**思路**：`EnterPlanMode` 支持 interview 阶段——先通过提问收集需求信息，再制定实施计划。分离"探索"和"执行"，减少返工。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `tools/EnterPlanModeTool/EnterPlanModeTool.ts` | interview 阶段状态管理 |
| `tools/ExitPlanModeTool/ExitPlanModeV2Tool.ts` | 计划确认 + 执行过渡 |

**Qwen Code 修改方向**：已有 `exitPlanMode` 工具；新增 `enterPlanMode` 工具支持 interview 阶段的附件系统。

**意义**：复杂任务先收集需求再动手——减少因理解不全导致的返工。
**缺失后果**：Agent 直接开始执行——可能方向偏差后大量返工。
**改进收益**：先 interview 收集完整需求 → 再制定计划 → 用户确认后执行。

---

<a id="item-35"></a>

### 35. BriefTool（P2）

**思路**：Agent 向用户发送异步状态消息（含附件），不中断工具执行。用于 proactive status 更新——"已完成 3/5 个文件修改"。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `tools/BriefTool/BriefTool.ts` | 异步消息发送 + 附件支持 |

**Qwen Code 修改方向**：新建 `tools/brief.ts`；通过事件系统（`AgentEventEmitter`）向 UI 推送进度消息。

**意义**：长时间后台任务中用户需要了解进度——否则只能盲等。
**缺失后果**：用户不知道 Agent 在做什么——只能等最终结果。
**改进收益**：Agent 可异步推送进度消息——'已完成 3/5 个文件修改'。

---

<a id="item-36"></a>

### 36. SendMessageTool（P2）

**思路**：多代理间消息传递——单播（name）、广播（`*`）、UDS Socket、Remote Control bridge。支持结构化消息（shutdown_request、plan_approval）。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `tools/SendMessageTool/SendMessageTool.ts` (917行) | 路由逻辑（name → agentNameRegistry → tasks → mailbox）、broadcast |
| `utils/teammateMailbox.ts` (1183行) | 文件邮箱 + proper-lockfile |

**Qwen Code 修改方向**：Arena 模式下新增消息传递工具；基于文件或 IPC 实现 agent 间通信。

**相关文章**：[多代理系统](./multi-agent-deep-dive.md)

**意义**：多代理协作需要代理间通信——分配任务、报告进度、协调行动。
**缺失后果**：Arena 模式下代理间无法通信——只能各自独立执行。
**改进收益**：Leader 分配任务后 Worker 通过消息报告进度——真正的团队协作。

---

<a id="item-37"></a>

### 37. FileIndex（P2）

**思路**：fzf 风格模糊文件搜索——异步增量索引 + nucleo 风格匹配。不需精确文件名即可定位。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `native-ts/file-index/` | 原生 TS 文件索引器 |

**Qwen Code 修改方向**：新建 `tools/fileIndex.ts`；基于 `glob` + 模糊匹配库（如 fzf-for-js）实现。

**意义**：大型仓库中精确文件名难以记住——模糊搜索是刚需。
**缺失后果**：需要精确文件名才能定位——'那个 auth 相关的文件叫什么来着？'
**改进收益**：fzf 风格模糊搜索——输入部分关键词即可定位。

---

<a id="item-38"></a>

### 38. Notebook Edit（P2）

**思路**：Jupyter `.ipynb` 文件的 cell 级编辑——插入/修改 code/markdown cell，自动追踪 cell ID，集成文件历史快照。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `tools/NotebookEditTool/NotebookEditTool.ts` | cell 编辑 + ID 追踪 |

**Qwen Code 修改方向**：新建 `tools/notebookEdit.ts`；解析 ipynb JSON → 定位 cell → 修改 → 写回。

**意义**：数据科学工作流大量使用 Jupyter notebook——原生支持是差异化能力。
**缺失后果**：Agent 无法直接操作 .ipynb 文件——数据科学家需手动编辑。
**改进收益**：原生 cell 级编辑——Agent 可直接修改 notebook 代码和 markdown。

---

<a id="item-39"></a>

### 39. 自定义快捷键（P2）

**思路**：支持 multi-chord 组合键（如 `Ctrl+K Ctrl+S`）+ 跨平台适配（Windows VT mode 检测）+ `~/.claude/keybindings.json` 自定义。Reserved keys（Ctrl+C/D）不可重绑。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `keybindings/` | `defaultBindings.ts`、multi-chord 状态机 |

**Qwen Code 修改方向**：`KeypressContext.tsx` 扩展支持 chord 序列；新增 `~/.qwen/keybindings.json` 配置加载。

**意义**：高级用户对快捷键有强烈自定义需求——尤其 Vim 用户。
**缺失后果**：固定快捷键无法满足不同用户习惯。
**改进收益**：multi-chord + 自定义 keybindings.json——每个用户定制最顺手的操作方式。

---

<a id="item-40"></a>

### 40. Session Ingress Auth（P2）

**思路**：远程会话 bearer token 认证——通过文件描述符或 well-known 文件传递 token。支持企业多用户环境下的安全 Agent 访问。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/sessionIngressAuth.ts` | bearer token 验证 |

**Qwen Code 修改方向**：新建 `utils/sessionIngressAuth.ts`；headless 模式下验证 `--ingress-token` 参数。

**意义**：企业多用户环境需要安全的远程 Agent 访问控制。
**缺失后果**：无认证机制——任何能访问端口的人都能操控 Agent。
**改进收益**：bearer token 认证——仅授权用户可远程访问。

---

<a id="item-41"></a>

### 41. 企业代理支持（P2）

**思路**：CONNECT-to-WebSocket relay 处理企业代理环境——CA cert 链注入、NO_PROXY 白名单（RFC1918 + API + GitHub + 包注册表）。失败时 fail-open 不阻断。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `upstreamproxy/upstreamproxy.ts` | CONNECT relay + CA cert 注入 |
| `utils/proxy.ts` | `configureGlobalAgents()`、`getProxyFetchOptions()` |

**Qwen Code 修改方向**：`config.ts` 扩展代理配置；Node.js `https.Agent` 注入自定义 CA cert。

**意义**：企业网络（代理/VPN/防火墙）是 Agent 部署的常见环境。
**缺失后果**：企业代理环境下 API 调用失败——Agent 不可用。
**改进收益**：CONNECT relay + CA cert 注入——企业网络环境下正常工作。

---

<a id="item-42"></a>

### 42. ConfigTool（P2）

**思路**：模型通过工具 get/set 设置（主题、模型、权限等），带 schema 验证。模型可根据任务自动调整配置。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `tools/ConfigTool/ConfigTool.ts` | get/set 操作 + schema 验证 |

**Qwen Code 修改方向**：新建 `tools/config.ts`；通过 `config.ts` API 读写设置并验证。

**意义**：模型根据任务自动调整配置——如切换到更适合当前任务的模型。
**缺失后果**：模型无法程序化修改设置——用户需手动 /settings。
**改进收益**：Agent 可自主切换模型/主题/权限——根据任务需求自适应。

---

<a id="item-43"></a>

### 43. 终端主题检测（P2）

**思路**：通过 OSC 11 查询终端背景色 + `$COLORFGBG` 环境变量回退——解析 `auto` 主题为具体 dark/light。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/systemTheme.ts` | `resolveThemeSetting()`（OSC 11 + COLORFGBG） |

**Qwen Code 修改方向**：`semantic-colors.ts` 新增 `detectTheme()` 函数；启动时探测并设置默认主题。

**意义**：终端 dark/light 模式不一致会导致代码高亮和 UI 不可读。
**缺失后果**：硬编码主题可能在浅色终端上不可见。
**改进收益**：自动检测终端背景色——UI 始终可读。

---

<a id="item-44"></a>

### 44. 自动后台化 Agent（P2）

**思路**：超过阈值（GrowthBook 配置的 ms 数）的 Agent 自动转后台——不阻塞用户交互。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `tools/AgentTool/AgentTool.tsx` | `getAutoBackgroundMs()` |

**Qwen Code 修改方向**：`agent.ts` 执行时启动 timer；超时将任务标记为 background 并释放前台。

**意义**：长时间 Agent 任务阻塞用户交互——用户只能等待。
**缺失后果**：用户等 Agent 执行完才能继续输入——浪费时间。
**改进收益**：超时自动转后台——用户继续交互，Agent 后台完成。

---

<a id="item-45"></a>

### 45. 队列输入编辑（P2）

**思路**：排队中的命令在 prompt 下方可见。按 Escape 可将可编辑命令弹出到输入框重新编辑（过滤 task-notification、isMeta 等不可编辑项）。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/messageQueueManager.ts` | `popAllEditable()`、`isQueuedCommandEditable()` |

**Qwen Code 修改方向**：`AsyncMessageQueue` 新增 `popEditable()` 方法；`InputPrompt.tsx` 渲染队列内容并处理 Escape。

**相关文章**：[输入队列与中断机制](./input-queue-deep-dive.md)

**意义**：发现排队输入有误需要修改——但已入队无法撤回。
**缺失后果**：错误输入已排队 → Agent 处理错误指令 → 需要额外一轮纠正。
**改进收益**：Escape 弹出排队命令到输入框——修改后重新提交。

---

<a id="item-46"></a>

### 46. 状态栏紧凑布局（P2）

**思路**：状态栏固定高度不随内容伸缩——"height so the footer never grows/shrinks and shifts scroll content"。最大化终端内容区域。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `components/PromptInput/PromptInputFooterLeftSide.tsx` | 固定高度约束 |
| `components/StatusLine.tsx` | 条件显示（`statusLineShouldDisplay`） |

**Qwen Code 修改方向**：`Footer.tsx` 添加 `height: 1`（或 Ink `<Box height={1}>`）固定行高；条件显示非关键信息。

**意义**：终端空间有限（笔记本 + 分屏），Footer 挤压内容区域。
**缺失后果**：Footer 占用偏高——Agent 输出和用户输入可见行数减少。
**改进收益**：固定高度 Footer——最大化内容区域，小终端也舒适。

---

<a id="item-47"></a>

### 47. Conditional Hooks（P2）

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

<a id="item-48"></a>

### 48. Transcript Search（P2）

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

<a id="item-49"></a>

### 49. Bash File Watcher（P2）

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

<a id="item-50"></a>

### 50. /batch 并行操作（P2）

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

<a id="item-51"></a>

### 51. Chrome Extension 浏览器调试（P2）

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

<a id="item-52"></a>

### 52. /effort 命令（P2）

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

<a id="item-53"></a>

### 53. Status Line 自定义（P2）

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

<a id="item-54"></a>

### 54. Fullscreen Rendering（P2）

**思路**：Alt-screen 渲染 + 虚拟滚动缓冲区——完全消除终端闪烁。通过 `CLAUDE_CODE_NO_FLICKER=1` 启用。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/fullscreen.ts` | alt-screen 切换 + 虚拟化 |

**Qwen Code 修改方向**：`AppContainer.tsx` 新增 fullscreen 模式；通过 ANSI alt-screen sequences 切换；Ink `<ScrollBox>` 虚拟化长内容。

**意义**：终端闪烁是低性能终端上的常见 UX 问题。
**缺失后果**：长输出时终端闪烁——视觉体验差。
**改进收益**：alt-screen 无闪烁渲染——视觉稳定。

---

<a id="item-55"></a>

### 55. Image [Image #N] Chips（P2）

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

<a id="item-56"></a>

### 56. --max-turns 限制（P2）

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

<a id="item-57"></a>

### 57. --max-budget-usd 花费上限（P2）

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

<a id="item-58"></a>

### 58. Connectors 托管式 MCP（P2）

**思路**：托管式 MCP 连接——OAuth 认证的 GitHub/Slack/Linear/Google Drive 等连接器。处理 token 刷新、401 重试、连接器去重（本地优先）。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `services/mcp/client.ts` | OAuth token 管理 + 401 重试 + 连接器去重 |

**Qwen Code 修改方向**：`mcp-client.ts` 扩展 OAuth 连接管理；新增托管连接器配置 UI（类似 `/mcp` 对话框）。

**意义**：与外部服务（GitHub/Slack/Linear）的集成需要 OAuth 管理。
**缺失后果**：手动配置 token + 手动刷新——容易过期。
**改进收益**：托管式 OAuth——一键连接，自动刷新，401 自动重试。
