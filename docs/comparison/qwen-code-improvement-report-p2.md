# Qwen Code 改进建议 — P2 详细说明

> 中等优先级改进项。每项包含：思路概述、Claude Code 源码索引、Qwen Code 修改方向。
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md)

---

<a id="item-42"></a>

### 42. Shell 安全增强（P2）

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

<a id="item-43"></a>

### 43. MDM 企业策略（P2）

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

<a id="item-44"></a>

### 44. API 实时 Token 计数（P2）

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

<a id="item-45"></a>

### 45. Output Styles（P2）

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

<a id="item-46"></a>

### 46. Fast Mode（P2）

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

<a id="item-47"></a>

### 47. Computer Use 桌面自动化（P2）

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

<a id="item-48"></a>

### 48. Denial Tracking（P2）

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

<a id="item-49"></a>

### 49. 并发 Session 管理（P2）

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

<a id="item-50"></a>

### 50. Git Diff 统计（P2）

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

<a id="item-51"></a>

### 51. 文件历史快照（P2）

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

<a id="item-52"></a>

### 52. Deep Link 协议（P2）

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

<a id="item-53"></a>

### 53. Plan 模式 Interview（P2）

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

<a id="item-54"></a>

### 54. BriefTool（P2）

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

<a id="item-55"></a>

### 55. SendMessageTool（P2）

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

<a id="item-56"></a>

### 56. FileIndex（P2）

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

<a id="item-57"></a>

### 57. Notebook Edit（P2）

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

<a id="item-58"></a>

### 58. 自定义快捷键（P2）

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

<a id="item-59"></a>

### 59. Session Ingress Auth（P2）

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

<a id="item-60"></a>

### 60. 企业代理支持（P2）

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

<a id="item-61"></a>

### 61. ConfigTool（P2）

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

<a id="item-62"></a>

### 62. 终端主题检测（P2）

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

<a id="item-63"></a>

### 63. 自动后台化 Agent（P2）

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

<a id="item-64"></a>

### 64. 队列输入编辑（P2）

**思路**：排队中的命令在 prompt 下方可见。按 Escape 可将可编辑命令弹出到输入框重新编辑（过滤 task-notification、isMeta 等不可编辑项）。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/messageQueueManager.ts` | `popAllEditable()`、`isQueuedCommandEditable()` |

**Qwen Code 修改方向**：`AsyncMessageQueue` 新增 `popEditable()` 方法；`InputPrompt.tsx` 渲染队列内容并处理 Escape。

**进展**：[QwenLM/qwen-code#2871](https://github.com/QwenLM/qwen-code/pull/2871)（open）— 实现了 Up 方向键弹出队列消息到输入框编辑。

**相关文章**：[输入队列与中断机制](./input-queue-deep-dive.md)

**意义**：发现排队输入有误需要修改——但已入队无法撤回。
**缺失后果**：错误输入已排队 → Agent 处理错误指令 → 需要额外一轮纠正。
**改进收益**：Escape 弹出排队命令到输入框——修改后重新提交。

---

<a id="item-65"></a>

### 65. 状态栏紧凑布局（P2）

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

<a id="item-66"></a>

### 66. Conditional Hooks（P2）

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

<a id="item-67"></a>

### 67. Transcript Search（P2）

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

<a id="item-68"></a>

### 68. Bash File Watcher（P2）

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

<a id="item-69"></a>

### 69. /batch 并行操作（P2）

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

<a id="item-70"></a>

### 70. Chrome Extension 浏览器调试（P2）

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

<a id="item-71"></a>

### 71. /effort 命令（P2）

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

<a id="item-72"></a>

### 72. Status Line 自定义（P2）

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

<a id="item-73"></a>

### 73. 终端渲染优化（P2）

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

<a id="item-74"></a>

### 74. Image [Image #N] Chips（P2）

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

<a id="item-75"></a>

### 75. --max-turns 限制（P2）

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

<a id="item-76"></a>

### 76. --max-budget-usd 花费上限（P2）

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

<a id="item-77"></a>

### 77. Connectors 托管式 MCP（P2）

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

<a id="item-78"></a>

### 78. MCP Auto-Reconnect（P2）

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

<a id="item-79"></a>

### 79. Tool Result 大小限制（P2）

**思路**：每个工具定义 `maxResultSizeChars`（如 100K 字符）。超限结果持久化到磁盘文件，模型收到预览 + 文件路径而非完整内容——防止单个巨大工具结果占满上下文。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `Tool.ts` | `maxResultSizeChars` 工具属性 |
| 各工具（TaskStopTool/NotebookEditTool/SkillTool 等） | `maxResultSizeChars: 100_000` |

**Qwen Code 修改方向**：`BaseDeclarativeTool` 新增 `maxResultSizeChars` 属性；工具执行后检查结果字符数，超限时写入 temp 文件 + 返回预览。

**意义**：单个大文件 Read 或长命令输出可能超过 100K 字符——直接塞入上下文会溢出。
**缺失后果**：大结果直接注入 → 上下文溢出或挤占其他内容空间。
**改进收益**：大结果自动落盘 + 预览——模型需要时可 Read 完整文件，不浪费上下文。

---

<a id="item-80"></a>

### 80. Output Token 升级重试（P2）

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

<a id="item-81"></a>

### 81. Ripgrep 三级回退（P2）

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

<a id="item-82"></a>

### 82. MAGIC DOC 自更新文档（P2）

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

<a id="item-83"></a>

### 83. 目录/文件路径补全（P2）

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

<a id="item-84"></a>

### 84. 上下文 Tips 系统（P2）

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

<a id="item-85"></a>

### 85. 权限对话框文件预览（P2）

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

<a id="item-86"></a>

### 86. Token 使用实时警告（P2）

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

<a id="item-87"></a>

### 87. 快捷键提示组件（P2）

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

<a id="item-88"></a>

### 88. 终端完成通知（P2）

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

<a id="item-89"></a>

### 89. Spinner 工具名 + 计时（P2）

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

<a id="item-90"></a>

### 90. /rewind 检查点回退（P2）

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

<a id="item-91"></a>

### 91. /copy OSC 52 剪贴板（P2）

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

<a id="item-92"></a>

### 92. 首次运行引导向导（P2）

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

<a id="item-93"></a>

### 93. /doctor 诊断工具（P2）

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

<a id="item-94"></a>

### 94. 结构化 Diff 渲染（P2）

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

<a id="item-95"></a>

### 95. MCP 并行连接 — 动态插槽调度 + 双层并发（P2）

**思路**：MCP 服务器分两组并行初始化——本地（stdio/sdk，并发 3）和远程（sse/http/ws，并发 20），`Promise.all()` 同时启动两组。关键优化：用 `pMap` 动态插槽调度替代固定批次——一个慢服务器只占一个插槽，不阻塞整批。工具/命令/资源获取也并行（`Promise.all([fetchTools, fetchCommands, fetchResources])`）。LRU 缓存（20 条）避免重复获取。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `services/mcp/client.ts` (L2226-2403) | `getMcpToolsCommandsAndResources()` 双组并行、`processBatched()` pMap 动态调度 |
| `services/mcp/client.ts` (L552-560) | `getMcpServerConnectionBatchSize() = 3`、`getRemoteMcpServerConnectionBatchSize() = 20` |
| `services/mcp/client.ts` (L2171-2178) | `Promise.all([fetchTools, fetchCommands, fetchSkills, fetchResources])` |
| `services/mcp/client.ts` (L1726) | `MCP_FETCH_CACHE_SIZE = 20` LRU 缓存 |
| `services/mcp/client.ts` (L595) | `connectToServer = memoize(...)` 连接记忆化 |

**Qwen Code 修改方向**：`mcp-client-manager.ts` 已用 `Promise.all(discoveryPromises)` 并行初始化，但无并发上限控制——10 个 stdio 服务器同时 spawn 可能耗尽进程资源。无工具/资源并行获取，无 LRU 缓存。改进方向：① `McpClientManager.initializeAllClients()` 分 local/remote 两组，用 `p-limit` 控制并发上限（local:3, remote:20）；② `McpClient.discover()` 内部用 `Promise.all([tools, commands, resources])` 并行获取；③ 工具列表加 LRU 缓存，reconnect 时清除。

**意义**：企业环境配置 10+ MCP 服务器——启动时全部 spawn 可能 fork bomb。
**缺失后果**：无并发限制 = 进程资源争抢；固定批次 = 一个慢服务器阻塞整批。
**改进收益**：动态插槽 + 双层并发——启动快且资源可控；LRU 缓存避免重复获取。

---

<a id="item-96"></a>

### 96. 插件/Skill 并行加载与启动缓存（P2）

**思路**：3 层并行——① marketplace 插件 + session 插件 `Promise.all()` 并行加载；② 每个插件内部 commands/agents/hooks 目录存在检查 `Promise.all([pathExists(commandsDir), pathExists(agentsDir), pathExists(hooksDir)])`；③ 加载结果缓存，热重载时仅增量更新变更的插件。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/plugins/pluginLoader.ts` (L3165) | `Promise.all([marketplaceResult, sessionResult])` 双源并行 |
| `utils/plugins/pluginLoader.ts` (L1374-1386) | `Promise.all([commandsDirExists, agentsDirExists, skillsDirExists, outputStylesDirExists])` 4 目录检查并行 |
| `utils/plugins/pluginLoader.ts` (L1962) | `Promise.allSettled(plugins.map(...))` marketplace 并行加载 |

**Qwen Code 修改方向**：`skill-manager.ts` 用 `for` 循环顺序扫描 skill 目录 + 顺序读取 manifest 文件；`extensionManager.ts` 顺序加载 MCP/skills/subagents/hooks。改进方向：① `loadSkillsFromDir()` 改为 `Promise.all(entries.map(readManifest))`；② `extensionManager.ts` 中 MCP 初始化与 skill/hook 加载 `Promise.all()` 并行（无依赖关系）；③ 加载结果存入 Map 缓存，`/reload` 时仅重新加载变更的插件。

**意义**：用户安装 10+ 插件后启动时间线性增长——并行加载控制在常数时间。
**缺失后果**：10 个插件 × 50ms/插件 = 500ms 启动延迟（顺序加载）。
**改进收益**：并行加载 = ~50ms（最慢的一个）；缓存 = 热重载几乎免费。

---

<a id="item-97"></a>

### 97. Speculation 流水线建议（Pipelined Suggestions）（P2）

**思路**：当前 speculation 执行完成后，**立即并行生成下一个建议**（pipelined suggestion）。用户接受当前建议时，下一个建议已经准备好——连续 Tab 接受零延迟。投机结果作为上下文传给下一轮建议生成，确保连贯性。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `services/PromptSuggestion/speculation.ts` (L345-400) | `generatePipelinedSuggestion()` 并行生成下一建议 |
| `services/PromptSuggestion/speculation.ts` (L672-679) | speculation 完成后触发 pipelined generation |
| `services/PromptSuggestion/speculation.ts` (L928-955) | 接受建议时提升 pipelined suggestion |

**Qwen Code 修改方向**：speculation 已实现（PR#2525），但每次接受建议后需重新生成下一建议——间有 1-2 秒空白等待。改进方向：speculation 完成回调中立即调用 `generateNextSuggestion()`，将投机结果 + 新消息传入作为上下文；`state.pipelinedSuggestion` 存储预生成的建议；接受时直接提升，无需等待。

**意义**：Speculation 的价值在于连续流——中间有停顿会打破用户"心流"。
**缺失后果**：每次 Tab 接受后等 1-2 秒才出现下一建议——体验不够连贯。
**改进收益**：流水线预生成——连续 Tab 零延迟，真正的"自动驾驶"体验。

---

<a id="item-98"></a>

### 98. 写穿缓存与 TTL 后台刷新（P2）

**思路**：`memoizeWithTTL` 实现 stale-while-revalidate 模式——缓存过期后**立即返回旧值**，同时后台异步刷新。防止多个并发请求同时触发刷新（`refreshing` 标志位）。用于 MCP 工具列表、Git 状态、环境检测等频繁访问但变化慢的数据。`memoizeWithLRU` 提供有界缓存（默认 100 条），防止内存无限增长。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/memoize.ts` (L40-100) | `memoizeWithTTL()` write-through + background refresh、`cacheLifetimeMs = 5min` |
| `utils/memoize.ts` (L234-269) | `memoizeWithLRU()` LRU 有界缓存、`LRUCache` 封装 |
| `services/mcp/client.ts` (L595) | `connectToServer = memoize(...)` 连接缓存 |
| `services/mcp/client.ts` (L1743) | `fetchToolsForClient = memoizeWithLRU(...)` 工具列表 LRU |

**Qwen Code 修改方向**：`filesearch/result-cache.ts` 有搜索结果缓存；`crawlCache.ts` 有爬取缓存；但无通用 stale-while-revalidate 模式。MCP 工具列表每次重新获取。改进方向：① 新建 `utils/memoize.ts` 实现 `memoizeWithTTL`（过期返旧值 + 后台刷新）+ `memoizeWithLRU`（有界缓存）；② MCP 工具列表包装为 `memoizeWithLRU`；③ Git 状态检测包装为 `memoizeWithTTL(5min)`。

**意义**：MCP 工具列表、Git 状态等热点数据——每次 fetch 浪费 10-50ms。
**缺失后果**：每次查询触发完整 fetch——高频路径累积延迟显著。
**改进收益**：缓存命中 = 0ms + 后台静默刷新——用户永远不等待过期数据。

---

<a id="item-99"></a>

### 99. 上下文收集并行化（P2）

**思路**：每轮对话前需收集多种上下文附件（文件内容、图片、MCP 资源、诊断信息、LSP 数据等）。Claude Code 分两阶段并行：① 用户输入附件先完成（可能触发嵌套记忆加载）；② 线程附件 + 主线程附件 `Promise.all()` 并行处理，~20+ 并发计算。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/attachments.ts` (L819) | `Promise.all(userInputAttachments)` 用户附件并行 |
| `utils/attachments.ts` (L990-994) | `Promise.all([Promise.all(threadAttachments), Promise.all(mainThreadAttachments)])` 双阶段并行 |

**Qwen Code 修改方向**：上下文通过 `appendAdditionalContext()` 串行追加；hook 输出通过 `hookRunner.ts` 可并行但上下文收集本身是顺序的。改进方向：抽取上下文收集为独立函数；文件内容、MCP 资源、诊断信息等无依赖项用 `Promise.all()` 并行获取；有依赖项（如记忆触发嵌套加载）按拓扑顺序处理。

**意义**：每轮对话的上下文收集涉及 5-10 种来源——串行 = 延迟叠加。
**缺失后果**：10 种上下文来源 × 20ms = 200ms 串行等待。
**改进收益**：并行收集 = ~20ms（最慢的一个来源）——每轮省 150-180ms。

---

<a id="item-100"></a>

### 100. 输出缓冲与防阻塞渲染（P2）

**思路**：`createBufferedWriter` 在写入目标（如日志文件 appendFileSync）可能阻塞时，将输出缓冲到内存队列。溢出时用 `setImmediate` 延迟写入——当前 tick 不阻塞，保证键盘响应和渲染帧率。参数可调：`flushIntervalMs`（默认 1s）、`maxBufferSize`（默认 100 条）、`maxBufferBytes`。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/bufferedWriter.ts` | `createBufferedWriter()`、`flushDeferred()` setImmediate 延迟、`pendingOverflow` 排序保证 |

**Qwen Code 修改方向**：`pidfile.ts` 用 `writeFileSync` 写 PID 文件；`trustedFolders.ts` 用 `readFileSync`/`writeFileSync`（已在 item-28 中列出）；`shellExecutionService.ts` 输出直接推送——长输出可能阻塞渲染。改进方向：① 新建 `utils/bufferedWriter.ts`——内存缓冲 + 定时 flush + 溢出 `setImmediate`；② 同步写入热路径改用 `bufferedWriter.write()`；③ shell 输出推送改用 buffered writer（`maxBufferBytes` 限制内存占用）。

**意义**：同步写入和大量输出推送可能阻塞 Node.js 事件循环——导致 UI 卡顿和键盘无响应。
**缺失后果**：同步 I/O 在磁盘慢时阻塞主线程——用户输入延迟。
**改进收益**：缓冲 + 延迟写入——主线程永不阻塞，UI 始终流畅。

---

<a id="item-101"></a>

### 101. LSP 服务器并行启动/关闭（P2）

**思路**：多个 LSP 服务器（TypeScript、Python、Go 等）相互独立，启动和关闭可以 `Promise.all()` 并行。端口探测也可用 `Promise.race()` 并行尝试——首个成功连接即返回。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `services/lsp/` (7 文件) | LSP 客户端管理——多服务器独立启动 |

**Qwen Code 修改方向**：`LspServerManager.ts` 的 `startAll()` 和 `stopAll()` 用 `for` 循环顺序启动/关闭每个服务器（L81-92）。`LspConfigLoader.ts` 用 `readFileSync` 顺序读取配置文件。改进方向：① `startAll()` 改为 `Promise.all(servers.map(s => this.startServer(s)))` 并行启动；② `stopAll()` 改为 `Promise.allSettled()` 确保全部关闭（一个失败不影响其他）；③ 端口探测用 `Promise.race()` 并行尝试多个端口。

**意义**：多语言项目配置 3-5 个 LSP——顺序启动延迟线性叠加。
**缺失后果**：3 个 LSP × 500ms/个 = 1.5s 启动延迟（顺序）。
**改进收益**：并行启动 = ~500ms（最慢的一个）；端口探测首个成功即返回。

---

<a id="item-102"></a>

### 102. 请求合并与去重（Request Coalescing）（P2）

**思路**：高频请求场景——多个组件同时触发相同操作（如 MCP 工具列表刷新、认证检查、状态上报），合并为一次实际执行。3 种模式：① PUT 合并（1 in-flight + 1 pending，新请求合并到 pending）；② 401 去重（同 token 的多个 401 只触发一次 keychain 读取）；③ UUID 去重（BoundedUUIDSet 环形缓冲区 O(1) 查重）。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `cli/transports/WorkerStateUploader.ts` (131行) | 1 in-flight + 1 pending slot、RFC 7396 patch 合并 |
| `utils/auth.ts` (L1343) | `pending401Handlers: Map<token, Promise>` 防止 N 个 401 并发读 keychain（省 800ms+） |
| `bridge/bridgeMessaging.ts` (L429-459) | `BoundedUUIDSet` 环形缓冲区（cap=2000）O(1) 去重 |
| `utils/memoize.ts` (L125-162) | `inFlight` Map 防止 N 个 cold-miss 并发调用同一函数 |

**Qwen Code 修改方向**：无通用请求合并机制；MCP 工具列表每次 reconnect 全量重新获取；无认证去重。改进方向：① 新建 `utils/requestCoalescer.ts`——通用 1-in-flight + 1-pending 合并器；② MCP 工具刷新包装为 coalescer（多个 reconnect 事件合并）；③ API 认证失败处理加 inFlight 去重。

**意义**：高频事件（文件保存触发 lint + format + refresh）产生重复请求——合并后只执行一次。
**缺失后果**：10 个文件保存 → 10 次 MCP 工具列表刷新 → 10× 不必要 I/O。
**改进收益**：请求合并 = 1 次实际执行——消除 90% 重复操作。

---

<a id="item-103"></a>

### 103. 延迟初始化与按需加载（Lazy Init）（P2）

**思路**：3 层延迟策略——① `lazySchema()`：Zod schema 定义推迟到首次使用时构建（启动不触发 Zod）；② 延迟模块导入：大模块（如 113KB insights.ts）在命令执行时 `import()` 而非启动时 `require`；③ 延迟预取（`startDeferredPrefetches`）：AWS/GCP 凭证、MCP 官方 URL 等在首帧渲染后才开始。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/lazySchema.ts` (8行) | `lazySchema(factory)` 缓存式惰构建 |
| `commands.ts` (L188) | 113KB insights.ts 延迟导入 |
| `main.tsx` (L383-418) | `startDeferredPrefetches()` 首帧后预取 |
| `Tool.ts` (L439-442) | `shouldDefer` 属性（对应 `defer_loading`）工具延迟加载到 prompt |

**Qwen Code 修改方向**：所有模块启动时同步加载；Zod schema 在模块求值时构建；所有工具定义启动时全量生成。改进方向：① 大型命令模块改为 `await import()` 动态导入；② 工具 Zod schema 包装为 `lazySchema()`——首次调用时才构建；③ 非关键预取（凭证、远程配置）推迟到首帧渲染后。

**意义**：启动时间 = 所有模块加载时间之和——延迟非关键模块直接缩短启动。
**缺失后果**：启动加载全量模块 + 全量 schema 构建——冷启动慢 200-500ms。
**改进收益**：惰加载 = 仅加载核心模块——启动时间缩短 30-50%。

---

<a id="item-104"></a>

### 104. 流式超时检测与级联取消（P2）

**思路**：API 流式响应设置 90 秒空闲看门狗——收到 chunk 时重置计时器，超时则 abort stream 触发重试。工具执行层面：子 AbortController 实现级联取消——Bash 工具出错时 `siblingAbortController.abort()` 立即终止同批次的其他子进程（不终止整轮查询）。`createChildAbortController()` 用 WeakRef 防止 GC 泄漏。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `services/api/claude.ts` (L1868-1954) | 90s 流式空闲看门狗、stall 计数 + 时间统计 |
| `utils/abortController.ts` | `createChildAbortController()` WeakRef 子控制器 |
| `services/tools/StreamingToolExecutor.ts` (L45-48) | `siblingAbortController` Bash 错误级联 |
| `hooks/useTypeahead.tsx` (L206-217) | 每次击键取消上一次 shell 补全 |

**Qwen Code 修改方向**：API 流式超时使用全局固定超时（无空闲检测）；工具执行无级联取消——一个工具失败其他继续运行。改进方向：① API stream 处理添加空闲检测（每个 chunk 重置 timer，超时 abort + 重试）；② `coreToolScheduler.ts` 添加 `siblingAbortController`——写工具（Bash）失败时取消同批次其他工具；③ 输入补全/搜索添加 AbortController——新输入取消旧搜索。

**意义**：API 偶尔 hang——无超时检测则用户永远等待；工具失败不级联取消则浪费资源。
**缺失后果**：API hang = 用户手动 Ctrl+C；Bash 报错后 Grep 继续白跑。
**改进收益**：空闲看门狗自动重试 + 级联取消——异常恢复自动化，资源零浪费。

---

<a id="item-105"></a>

### 105. Git 文件系统直读避免进程 Spawn（P2）

**思路**：频繁的 git 状态查询（当前分支、HEAD 指向、ref 解析）不 spawn `git` 子进程，而是直接读取 `.git/HEAD` 和 `.git/refs/` 文件。`git check-ignore` 用批量路径参数代替逐文件调用。减少进程 fork 开销（每次 ~5-10ms）。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/git/gitFilesystem.ts` | 文件系统级 git 状态读取——避免 spawn git 子进程 |
| `tools/LSPTool/LSPTool.ts` (L554) | `git check-ignore` 批量路径参数 |
| `utils/git.ts` | `findGitRoot` LRU 记忆化（max 50）、`gitExe` 单例查找 |

**Qwen Code 修改方向**：`gitService.ts` 通过 `simple-git` 库调用 git 命令（每次 spawn 子进程）；无文件系统直读优化；无 git 操作 LRU 缓存。改进方向：① 高频查询（当前分支、HEAD 解析）直接读取 `.git/HEAD` + `.git/refs/`（async readFile，无 spawn）；② `git check-ignore` 合并为批量调用（一次传多个路径）；③ `findGitRoot` 结果 LRU 缓存（防止每次 stat 向上遍历）。

**意义**：git 状态查询是热路径——每次工具执行前后都需检查。
**缺失后果**：10 次工具调用 × 2 次 git 查询 × 5ms/spawn = 100ms 开销。
**改进收益**：直读 .git/HEAD = 0.1ms（无 fork）；批量 check-ignore = 1 次 spawn 替代 N 次。

---

<a id="item-106"></a>

### 106. 设置/Schema 缓存与 Parse 去重（P2）

**思路**：3 层设置缓存——① `sessionSettingsCache`：每 session 合并后的设置（避免重复合并）；② `perSourceCache`：按来源缓存（用户/项目/本地）；③ `parseFileCache`：路径级去重（同一文件只读一次 + Zod parse 一次）。Schema 缓存在首次渲染时锁定快照，防止 GrowthBook 特性开关翻转导致工具定义变化（~11K tokens）。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/settings/settingsCache.ts` | 3 层缓存：session/perSource/parseFile |
| `utils/toolSchemaCache.ts` (26行) | 首次渲染锁定 tool schema，防止 mid-session 抖动 |
| `utils/fileStateCache.ts` | `FileStateCache` LRU（max 100 条/25MB） |

**Qwen Code 修改方向**：`settings.ts` 每次调用重新读取 + 解析配置文件（`readFileSync` + JSON.parse）；工具 schema 每轮重新生成；无文件状态缓存。改进方向：① 设置加载结果缓存——文件 mtime 变化时才重新读取/解析；② 工具 schema 首次生成后缓存，MCP 工具变化时增量更新；③ 文件状态（内容 + 编码）LRU 缓存。

**意义**：设置文件和工具 schema 在会话中变化极少，但每轮都重新读取/生成。
**缺失后果**：每轮读配置 + parse + schema 生成 = 10-50ms 重复工作。
**改进收益**：缓存命中 = 0ms——消除 90%+ 的重复解析和生成。

---

<a id="item-107"></a>

### 107. Bash 交互提示卡顿检测（P2）

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

<a id="item-108"></a>

### 108. TTY 孤儿进程检测（P2）

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

<a id="item-109"></a>

### 109. MCP 服务器优雅关闭升级（P2）

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

<a id="item-110"></a>

### 110. 事件循环卡顿检测（P2）

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

<a id="item-111"></a>

### 111. 会话活动心跳与空闲检测（P2）

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

<a id="item-112"></a>

### 112. Markdown 渲染缓存与纯文本快速路径（P2）

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

<a id="item-113"></a>

### 113. OSC 8 终端超链接（P2）

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

<a id="item-114"></a>

### 114. 模糊搜索选择器（FuzzyPicker）（P2）

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

<a id="item-115"></a>

### 115. 统一设计系统组件库（P2）

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

<a id="item-116"></a>

### 116. Markdown 表格终端渲染（P2）

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

<a id="item-117"></a>

### 117. 屏幕阅读器无障碍支持（P2）

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

<a id="item-118"></a>

### 118. 色觉无障碍主题（Daltonized）（P2）

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

<a id="item-119"></a>

### 119. 动画系统与卡顿状态检测（P2）

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

<a id="item-120"></a>

### 120. 代理权限冒泡与审批路由（P2）

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

<a id="item-121"></a>

### 121. 代理专属 MCP 服务器（P2）

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

<a id="item-122"></a>

### 122. 代理创建向导（P2）

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

<a id="item-123"></a>

### 123. 代理进度追踪与实时状态（P2）

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

<a id="item-124"></a>

### 124. 代理邮箱系统（Teammate Mailbox）（P2）

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
