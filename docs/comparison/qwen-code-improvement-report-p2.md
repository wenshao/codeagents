# Qwen Code 改进建议 — P2 详细说明

> 中等优先级改进项的详细说明。
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md)

<a id="item-10"></a>

### 10. Team Memory Sync 组织级记忆同步（P2）

**Claude Code 实现**：`services/teamMemorySync/` 实现 per-repo 级别的组织记忆同步。API 端点 `/api/claude_code/team_memory`，使用 ETag + SHA256 per-key 校验和进行 delta 上传。`fs.watch` 2 秒 debounce 实时推送。29 条 gitleaks 规则在上传前扫描密钥。

**Qwen Code 现状**：缺失。仅有用户私有的简单笔记工具。

**缺失后果**：
- 团队成员各自维护独立记忆——项目知识无法共享，新成员需从零积累
- 同一项目的编码规范、架构决策、已知坑点散落在各人本地——知识孤岛

**改进收益**：
- **团队知识共享**：一人学到的项目知识自动同步给全团队——新成员 session 自动注入团队积累
- **密钥安全**：29 条 gitleaks 规则客户端扫描——敏感凭据永不上传到服务端
- **冲突安全**：ETag + 412 重试机制——多人同时编辑不会丢失数据

**相关文章**：[Team Memory 组织级记忆同步](./team-memory-deep-dive.md)

---

<a id="item-14"></a>

### 14. Shell 安全增强（P2）

**Claude Code 实现**：`tools/BashTool/bashSecurity.ts`（2,592 行）25+ 安全检查管线 + tree-sitter AST 辅助消除误报。覆盖 IFS 注入、Unicode 空白、Zsh 命令、花括号展开等。

**Qwen Code 现状**：AST-only 读写分类（`shellAstParser.ts` 1,248 行）。不覆盖 IFS、Unicode、Zsh 等维度。

**缺失后果**：IFS 注入、Unicode 空白字符等边缘攻击可能绕过只读检测。

**改进收益**：AST 主路径（精确）+ 专项检查补充（IFS/Unicode/Zsh）——覆盖面与精确度兼得。

**相关文章**：[Shell 安全模型](./shell-security-deep-dive.md)

---

<a id="item-15"></a>

### 15. MDM 企业配置（P2）

**Claude Code 实现**：macOS plist（`com.anthropic.claudecode`）+ Windows Registry（`HKLM\SOFTWARE\Policies\ClaudeCode`）+ `managed-settings.d/` drop-in 目录 + 远程 API 策略。5 级 First-Source-Wins 优先级。

**Qwen Code 现状**：无 OS 级策略管理，仅文件配置。

**缺失后果**：企业 IT 无法通过 Jamf/Intune/SCCM 集中管控 AI Agent 配置。

**改进收益**：管理员可锁定权限模式、限制模型选择、强制遥测——满足 SOC 2 / HIPAA 合规。

**相关文章**：[MDM 企业配置管理](./mdm-enterprise-deep-dive.md)

---

<a id="item-16"></a>

### 16. API 实时 Token 计数（P2）

**Claude Code 实现**：`services/tokenEstimation.ts`（495 行）3 层回退：`countTokensWithAPI()` → Haiku fallback → 粗估（4 bytes/token）。支持 4 Provider（Direct/Bedrock/Vertex/Foundry）。VCR fixture 缓存避免重复计数。

**Qwen Code 现状**：静态模式匹配（`tokenLimits.ts` 82 种模型模式）。配置时确定，非运行时计数。

**缺失后果**：上下文窗口占用率估算不准确——可能过早或过晚触发压缩。

**改进收益**：精确 token 计数——压缩触发更准确，避免不必要的压缩或溢出。

**相关文章**：[Token 估算与 Thinking](./token-estimation-deep-dive.md)

---

<a id="item-17"></a>

### 17. Output Styles Learning / Explanatory（P2）

**Claude Code 实现**：`constants/outputStyles.ts`（216 行）内置 Explanatory（"Insight" 教育块）和 Learning（暂停要求用户写代码，`TODO(human)` 占位符）两种模式。

**Qwen Code 现状**：缺失。

**缺失后果**：无法为教学/培训场景定制输出——新人无法通过动手实践学习。

**改进收益**：Learning 模式让 Agent 成为教练——暂停、出题、等待用户实现——适合编程教学。

**相关文章**：[Git 工作流与会话管理](./git-workflow-session-deep-dive.md)

---

<a id="item-18"></a>

### 18. Fast Mode 速度/成本分级（P2）

**Claude Code 实现**：`utils/fastMode.ts`（532 行）同一模型（Opus 4.6）的标准/快速切换。快速模式 $30/$150/Mtok（标准 $5/$25），含冷却机制和重试集成。

**Qwen Code 现状**：`/model --fast` 指定备用快速模型（不是同模型速度切换）。

**缺失后果**：无法在同一模型上灵活切换延迟/成本——时间敏感任务仍用标准速度。

**改进收益**：一键切换推理速度——紧急任务用 Fast，日常用 Standard，两者共享同一上下文。

**相关文章**：[成本追踪与 Fast Mode](./cost-fastmode-deep-dive.md)

---

<a id="item-19"></a>

### 19. Computer Use 桌面自动化（P2）

**Claude Code 实现**：macOS-native Swift 实现（NSWorkspace + TCC + SCContentFilter），支持截图捕获、鼠标/键盘控制、前台应用检测、剪贴板操作。通过 MCP 协议桥接。

**Qwen Code 现状**：缺失。

**缺失后果**：无法跨应用自动化——Agent 只能操作文件和终端，不能操作浏览器/IDE/桌面应用。

**改进收益**：解锁跨应用工作流——如自动在浏览器中验证 UI、从 Figma 提取设计规范、操作数据库 GUI。

---

<a id="item-20"></a>

### 20. Denial Tracking 权限拒绝学习（P2）

**Claude Code 实现**：`utils/permissions/denialTracking.ts`（45 行）记录权限分类器的拒绝/成功次数。连续拒绝超过阈值（`DENIAL_LIMITS`）时自动回退到 prompting 模式——避免分类器陷入"全拒绝"死循环。

**Qwen Code 现状**：缺失。权限拒绝后无学习机制。

**缺失后果**：如果自动审批模式（auto-edit/yolo）连续拒绝某类操作，用户无感知——分类器可能永久阻塞合法操作。

**改进收益**：连续拒绝自动检测 → 回退到手动确认模式——用户看到被拒绝的操作并可手动批准，避免"静默失败"。

---

<a id="item-21"></a>

### 21. 并发 Session 管理（P2）

**Claude Code**：`utils/concurrentSessions.ts` 通过 PID 文件（`~/.claude/sessions/{pid}.json`）追踪多终端会话，支持 `bg`/`daemon` 后台脱附。`countConcurrentSessions()` 扫描并过滤已退出进程。

**Qwen Code**：缺失。无跨终端会话追踪。

**改进收益**：用户可在多终端并行使用 Agent，追踪后台任务状态，脱附/重附会话。

---

<a id="item-22"></a>

### 22. Git Diff 统计（P2）

**Claude Code**：`utils/gitDiff.ts` 两阶段 diff——`git diff --numstat` 快速探测 + 完整 hunks。限制：50 文件、1MB/文件、400 行/文件。merge/rebase 期间跳过。

**Qwen Code**：依赖 `simple-git` npm 包，无结构化 diff 统计。

**改进收益**：编辑后展示清晰的按文件行数统计——用户在 commit 前了解变更影响范围。

---

<a id="item-23"></a>

### 23. 文件历史快照（P2）

**Claude Code**：`utils/fileHistory.ts` 编辑前自动备份（SHA256 哈希 + mtime），按消息 ID 创建快照（上限 100 个/session）。支持按消息粒度恢复。

**Qwen Code**：Git worktree checkpoint（整体快照），粒度更粗。

**改进收益**：比 git-level 更细粒度的恢复——可回滚到任意消息时刻，而非仅 checkpoint 时刻。

---

<a id="item-24"></a>

### 24. Deep Link 协议（P2）

**Claude Code**：`utils/deepLink/` 实现 `claude-cli://` URI scheme，支持 `q`（prompt）、`cwd`（目录）、`repo`（GitHub slug）参数。自动检测 10+ 终端（iTerm/Ghostty/Kitty 等），3 平台协议注册。

**Qwen Code**：缺失。

**改进收益**：从浏览器/IDE/Slack 一键启动 Agent 并预填充 prompt——大幅降低上下文切换成本。

**相关文章**：[Deep Link 协议](./deep-link-protocol-deep-dive.md)

---

<a id="item-25"></a>

### 25. Plan 模式 Interview（P2）

**Claude Code**：`EnterPlanMode` 支持 interview 阶段——先通过提问收集需求，再制定实施计划。分离"探索"和"执行"。

**Qwen Code**：有 `exitPlanMode` 工具但无 interview 阶段。

**改进收益**：复杂任务前先充分理解需求——减少返工。

---

<a id="item-26"></a>

### 26. BriefTool（P2）

**Claude Code**：`tools/BriefTool/` 允许 Agent 向用户发送异步消息（含附件），不中断工具执行。用于 proactive status 更新。

**Qwen Code**：缺失。Agent 只能通过工具结果与用户通信。

**改进收益**：长时间任务中用户可收到进度更新——"已完成 3/5 个文件修改"。

---

<a id="item-27"></a>

### 27. SendMessageTool（P2）

**Claude Code**：`tools/SendMessageTool/` 支持队友间通信（单播/广播）、shutdown 请求、plan approval。路由支持 name/UDS/bridge。

**Qwen Code**：缺失。Arena 模式下无跨代理通信。

**改进收益**：多代理协作时可协调任务——Leader 分配工作后 Worker 通过消息报告进度。

**相关文章**：[多代理系统](./multi-agent-deep-dive.md)

---

<a id="item-28"></a>

### 28. FileIndex（P2）

**Claude Code**：`native-ts/file-index/` 实现 fzf 风格模糊文件搜索，支持异步增量索引。

**Qwen Code**：依赖 `rg`/`glob`，无模糊搜索。

**改进收益**：大型仓库中快速定位文件——不需要精确文件名。

---

<a id="item-29"></a>

### 29. Notebook Edit（P2）

**Claude Code**：`tools/NotebookEditTool/` 支持 Jupyter notebook cell 编辑——插入/修改 code/markdown cell，自动追踪 cell ID，集成文件历史快照。

**Qwen Code**：缺失。

**改进收益**：数据科学工作流原生支持——直接操作 `.ipynb` 文件。

---

<a id="item-30"></a>

### 30. 自定义快捷键（P2）

**Claude Code**：`keybindings/` 支持 multi-chord 组合键（如 `Ctrl+K Ctrl+S`）、平台适配（Windows VT mode 检测）、`~/.claude/keybindings.json` 自定义。

**Qwen Code**：缺失。仅有 IDE keybindings.json 终端集成配置。

**改进收益**：高级用户自定义操作快捷方式——提升重复操作效率。

---

<a id="item-31"></a>

### 31. Session Ingress Auth（P2）

**Claude Code**：`utils/sessionIngressAuth.ts` 提供 bearer token 远程会话认证，支持文件描述符和 well-known 文件方式。

**Qwen Code**：缺失。

**改进收益**：企业多用户环境下安全的远程 Agent 访问——支持 CCR 式部署。

---

<a id="item-32"></a>

### 32. 企业代理支持（P2）

**Claude Code**：`upstreamproxy/` 提供 CONNECT-to-WebSocket relay，CA cert 链注入，NO_PROXY 白名单（覆盖 RFC1918、Anthropic API、GitHub、包注册表）。失败时 fail-open。

**Qwen Code**：缺失。

**改进收益**：企业网络（代理/VPN/防火墙）环境下正常使用——无需手动配置代理。

---

<a id="item-33"></a>

### 33. ConfigTool（P2）

**Claude Code**：`tools/ConfigTool/` 允许模型通过工具 get/set 设置（主题、模型、权限等），带 schema 验证。

**Qwen Code**：设置通过 `/settings` 命令，模型无法程序化修改。

**改进收益**：模型可根据任务自动调整设置——如切换到适合当前任务的模型。

---

<a id="item-34"></a>

### 34. 终端主题检测（P2）

**Claude Code**：`utils/systemTheme.ts` 通过 OSC 11 查询终端背景色 + `$COLORFGBG` 环境变量回退，解析 `auto` 主题为具体 dark/light。

**Qwen Code**：缺失。

**改进收益**：终端 dark/light 模式自动适配——代码高亮和 UI 颜色与终端背景匹配。

---

<a id="item-35"></a>

### 35. 自动后台化 Agent（P2）

**Claude Code**：`getAutoBackgroundMs()` 基于 GrowthBook 门控，超过阈值的 Agent 自动转后台执行。

**Qwen Code**：需显式指定 `run_in_background`。

**改进收益**：长时间 Agent 任务自动后台化——不阻塞用户交互。

---

<a id="item-36"></a>

### 36. 队列输入编辑（P2）

**Claude Code**：`utils/messageQueueManager.ts` 的 `popAllEditable()` 允许用户按 Escape 将队列中的可编辑命令弹出到输入框重新编辑。队列在 prompt 下方实时可见。

**Qwen Code**：缺失。排队输入后无法修改。

**缺失后果**：用户在 Agent 执行中输入了错误指令但无法撤回——只能等 Agent 处理完错误指令后再纠正。

**改进收益**：排队中的输入可重新编辑——发现输入错误时按 Escape 弹回修改，避免浪费一轮执行。

**相关文章**：[输入队列与中断机制](./input-queue-deep-dive.md)

---

<a id="item-48"></a>

### 48. 状态栏紧凑布局（P2）

**Claude Code**：`PromptInputFooterLeftSide.tsx` 注释明确"height so the footer never grows/shrinks and shifts scroll content"——状态栏固定高度，不随内容伸缩。`StatusLine` 组件仅在需要时显示，默认隐藏。

**Qwen Code**：Footer 始终显示多项信息（exit 提示 / 模式指示 / sandbox / debug / context usage），占用终端空间偏高。

**缺失后果**：终端高度有限时（如笔记本 + 分屏），Footer 挤压内容区域——Agent 输出和用户输入可见行数减少。

**改进收益**：紧凑 Footer 最大化内容区域——在小终端上也能舒适工作。

---

<a id="item-53"></a>

### 53. Conditional Hooks（P2）

**Claude Code**：Hooks 支持 `if` 字段，使用权限规则语法（如 `Bash(git:*)` 或 `Edit(src/**)`）过滤何时执行。

**Qwen Code**：Hooks 无条件过滤——注册后所有匹配事件都触发。

**改进收益**：精细控制 Hook 触发范围——如"仅在 git 命令时运行 pre-commit 检查"。

---

<a id="item-54"></a>

### 54. Transcript Search（P2）

**Claude Code**：按 `/` 进入搜索模式，`n`/`N` 在匹配项间导航。支持 transcript 模式下的会话内搜索。

**Qwen Code**：缺失。

**改进收益**：长会话中快速定位之前的讨论——"刚才说的那个 API 端点是什么来着？"

---

<a id="item-55"></a>

### 55. Bash File Watcher（P2）

**Claude Code**：检测 formatter/linter 在 Agent 读取文件后修改了该文件（如 prettier 自动格式化），发出警告防止 stale-edit 错误。

**Qwen Code**：缺失。

**缺失后果**：Agent 读取文件后 formatter 自动修改 → Agent 基于旧内容编辑 → 冲突或丢失格式化。

**改进收益**：自动检测文件被外部修改 → 提醒 Agent 重新读取——避免 stale-edit 导致的编辑冲突。

---

<a id="item-56"></a>

### 56. /batch 并行操作（P2）

**Claude Code**：`/batch` bundled 命令，编排大规模并行变更——多文件/多任务同时处理。

**Qwen Code**：缺失。

**改进收益**：批量重构场景（如 "将所有 class 组件迁移到 hooks"）可并行处理——速度倍增。

---

<a id="item-57"></a>

### 57. Chrome Extension 浏览器调试（P2）

**Claude Code**：Chrome 扩展通过 MCP 协议桥接，提供 `read_page`（DOM）、`read_console_messages`（Console）、`read_network_requests`（Network）、`navigate`、`switch_browser` 等工具。通过 `/web-setup` 配置。

**Qwen Code**：缺失。

**缺失后果**：前端调试时 Agent 无法"看到"浏览器中的实际渲染结果/错误日志。

**改进收益**：Agent 可直接读取浏览器 DOM 和控制台错误——前端调试效率大幅提升。

---

<a id="item-64"></a>

### 64. /effort 命令（P2）

**Claude Code**：`commands/effort/effort.tsx`。设置模型 effort 级别（低 ○ / 中 ◐ / 高 ●），显示在 prompt bar 和 spinner 上。影响推理深度和 token 消耗。

**Qwen Code**：缺失。用户无法动态调整推理深度。

**改进收益**：简单任务用低 effort（省 token），复杂任务用高 effort——灵活控制质量/成本平衡。

---


<a id="item-66"></a>

### 66. Status Line 自定义（P2）

**Claude Code**：`components/StatusLine.tsx` + `settings.statusLine` 配置。用户配置 shell 脚本在状态栏展示自定义信息（如 rate limit 用量、git branch、自定义指标）。

**Qwen Code**：缺失。

**改进收益**：状态栏展示用户关心的信息——如"Rate limit: 45% used, resets in 2h"。

---

<a id="item-67"></a>

### 67. Fullscreen Rendering（P2）

**Claude Code**：`utils/fullscreen.ts` + `CLAUDE_CODE_NO_FLICKER=1`。Alt-screen 渲染 + 虚拟滚动缓冲区——完全消除终端闪烁。

**Qwen Code**：缺失。

**改进收益**：长输出不再闪烁——视觉体验提升，尤其在低性能终端上。

---

<a id="item-68"></a>

### 68. Image [Image #N] Chips（P2）

**Claude Code**：`components/PromptInput/PromptInput.tsx#L581`。粘贴图片后在输入框生成 `[Image #1]`、`[Image #2]` 位置标记，用户可通过标记在 prompt 中引用特定图片。

**Qwen Code**：缺失。

**改进收益**："修复 [Image #1] 中的 bug，参考 [Image #2] 的设计"——多图场景更精确。

---

<a id="item-69"></a>

### 69. --max-turns 限制（P2）

**Claude Code**：`main.tsx` CLI 参数 `--max-turns <N>`。headless 模式下限制最大 agentic turn 数——防止无限循环。

**Qwen Code**：有 `maxTurnsPerMessage` 配置，但非 CLI 参数。

**改进收益**：CI 脚本精确控制 Agent 执行范围——`qwen-code -p --max-turns 10 "fix bug"` 最多 10 轮。

---

<a id="item-70"></a>

### 70. --max-budget-usd 花费上限（P2）

**Claude Code**：`main.tsx` CLI 参数 `--max-budget-usd <amount>`。headless 模式下限制 USD 花费——自动停止。

**Qwen Code**：缺失。

**改进收益**：CI 防止意外高消耗——`--max-budget-usd 5` 限制单次运行最多 $5。

---

<a id="item-71"></a>

### 71. Connectors 托管式 MCP（P2）

**Claude Code**：`services/mcp/client.ts` 管理 OAuth 认证的 MCP 连接——GitHub、Slack、Linear、Google Drive 等。连接器处理 token 刷新和 401 重试。

**Qwen Code**：MCP 仅支持手动配置。

**改进收益**：一键连接 GitHub/Slack/Linear——无需手动配 token、刷新、重试。

---



