# Qwen Code 改进建议 — P2 核心功能与企业特性

> 中等优先级改进项。每项包含：问题场景、现状分析、改进前后对比、实现成本评估、Claude Code 源码索引、Qwen Code 修改方向。
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md)

---

<a id="item-1"></a>

### 1. Shell 安全增强（P2）

你在使用 Agent 执行 Shell 命令时，可能遭遇 prompt injection 攻击——恶意用户通过 IFS 变量注入、Unicode 零宽空白字符、Zsh 特有危险命令等手段绕过 AST 解析器的安全检测。AST 读写分类只能识别命令结构层面的危险操作，但这些边缘攻击发生在字符/环境变量层面，AST 无法感知。解决思路是在 AST 主路径之外增加一层专项检查管线，覆盖 12+ 种命令替换模式和 18 种 Zsh 危险命令。

**Qwen Code 现状**：`shellAstParser.ts` 实现了 AST 级别的读写分类，但缺少字符级/环境变量级的安全检查。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `tools/BashTool/bashSecurity.ts` (2592行) | 25+ validators 管线、`COMMAND_SUBSTITUTION_PATTERNS`（12 种）、`ZSH_DANGEROUS_COMMANDS`（18 个） |
| `utils/bash/treeSitterAnalysis.ts` (506行) | AST 辅助消除 `find -exec \;` 误报 |

**Qwen Code 修改方向**：`shellAstParser.ts` 保持 AST 主路径不变；新增 `shellSecurityChecks.ts` 补充 IFS/Unicode/Zsh 检查，AST 判定 read-only 后仍过一遍专项检查。

**实现成本评估**：
- 涉及文件：~3 个
- 新增代码：~400 行
- 开发周期：~3 天（1 人）
- 难点：收集和验证所有已知的 Shell 注入模式，确保专项检查不产生误报

**改进前后对比**：
- **改进前**：AST 判定 `echo $IFS` 为 read-only 安全操作，攻击者通过 IFS 注入执行任意命令
- **改进后**：AST 判定后，专项检查拦截 IFS 注入/Unicode 零宽字符/Zsh 危险命令，双层过滤

**相关文章**：[Shell 安全模型](./shell-security-deep-dive.md)

**意义**：Shell 命令是 Agent 最危险的工具——注入攻击可能造成系统损害。
**缺失后果**：AST-only 不覆盖 IFS 注入、Unicode 空白、Zsh 命令等边缘攻击。
**改进收益**：AST 主路径 + 专项检查补充——覆盖面与精确度兼得。

---

<a id="item-2"></a>

### 2. MDM 企业策略（P2）

你在企业环境中部署 AI Agent 时，IT 管理员需要集中管控配置——比如禁用 yolo 模式、限制可用模型列表、强制开启遥测。但如果 Agent 只支持用户级配置文件，任何开发者都能自行覆盖管理员的策略，导致安全合规形同虚设。解决方案是通过 OS 原生机制（macOS plist、Windows Registry、Linux 配置文件）读取企业策略，并采用 5 级 First-Source-Wins 优先级确保管理员策略不可被用户覆盖：

```
Remote MDM > HKLM/plist > 配置文件 > drop-in 目录 > HKCU/用户配置
```

**Qwen Code 现状**：仅支持用户级 `~/.qwen/` 配置文件，无企业策略读取能力，无配置锁定机制。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/settings/mdm/constants.ts` | `com.anthropic.claudecode` domain、Registry keys |
| `utils/settings/mdm/rawRead.ts` | 子进程 plutil/reg query（5s 超时） |
| `utils/settings/mdm/settings.ts` | First-Source-Wins 合并逻辑 |

**Qwen Code 修改方向**：新建 `utils/settings/mdm/`；在 `config.ts` 初始化时并行读取 plist/Registry；settings 合并时 MDM 优先级最高。

**实现成本评估**：
- 涉及文件：~5 个
- 新增代码：~500 行
- 开发周期：~4 天（1 人）
- 难点：跨平台 plist/Registry/文件读取的兼容性测试，优先级合并逻辑的正确性

**改进前后对比**：
- **改进前**：管理员无法锁定配置，开发者在 `~/.qwen/settings.json` 中开启 yolo 模式绕过安全策略
- **改进后**：管理员通过 MDM 下发 `"disableYoloMode": true`，用户配置无法覆盖，合规审计可验证

**相关文章**：[MDM 企业配置管理](./mdm-enterprise-deep-dive.md)

**意义**：企业 IT 需集中管控 AI Agent 配置——禁用危险模式、限制模型、强制遥测。
**缺失后果**：用户可自行覆盖所有配置——无管理员锁定能力。
**改进收益**：通过 MDM 策略锁定关键配置——满足 SOC 2 / HIPAA 合规。

---

<a id="item-3"></a>

### 3. API 实时 Token 计数（P2）

你在长对话中遇到上下文突然被压缩、丢失重要信息，或者反过来——对话溢出报错。根源在于 Token 计数不准确。静态模式匹配（如按 4 bytes/token 粗估）在中文、代码混合、特殊字符场景下误差可达 30%+，导致压缩触发时机错误。解决方案是 3 层回退策略：

```
API countTokens()（精确） → 小模型回退（较准） → 粗估 4 bytes/token（兜底）
```

每次 API 调用前精确计数，并用 SHA1 hash 缓存避免重复请求。

**Qwen Code 现状**：`tokenLimits.ts` 使用静态模式匹配估算 Token 数，无 API 级精确计数，无缓存层。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `services/tokenEstimation.ts` (495行) | `countTokensWithAPI()`、`roughTokenCountEstimation()`、`TOKEN_COUNT_THINKING_BUDGET = 1024` |
| `services/vcr.ts` | `withTokenCountVCR()`（SHA1 hash 缓存） |

**Qwen Code 修改方向**：调用 DashScope/Gemini 的 token 计数 API 替代 `tokenLimits.ts` 的静态模式匹配；加缓存层避免重复计数。

**实现成本评估**：
- 涉及文件：~3 个
- 新增代码：~300 行
- 开发周期：~2 天（1 人）
- 难点：DashScope/Gemini Token 计数 API 的可用性和延迟，缓存失效策略

**改进前后对比**：
- **改进前**：静态估算上下文占用 70%（实际 90%），继续追加消息导致溢出报错
- **改进后**：API 精确计数显示 90%，及时触发压缩保留关键上下文，对话不中断

**相关文章**：[Token 估算与 Thinking](./token-estimation-deep-dive.md)

**意义**：上下文窗口占用率是触发压缩和防溢出的关键指标——估算不准会导致过早或过晚压缩。
**缺失后果**：静态模式匹配估算不精确——可能触发不必要压缩或溢出。
**改进收益**：API 实时计数——压缩触发更准确，避免浪费和溢出。

---

<a id="item-4"></a>

### 4. Output Styles（P2）

你在用 Agent 辅导新人学习代码时，希望 Agent 不直接给出答案而是引导新人动手实践。或者你在做代码审查培训时，希望 Agent 在关键函数处添加 "Insight" 教育说明块。但目前 Agent 只有一种输出风格——直接给出完整实现。解决方案是内置多种 Output Style：

- **Learning 模式**：Agent 在 20+ 行函数处暂停，插入 `TODO(human)` 占位符，要求用户自己写 2-10 行关键代码
- **Explanatory 模式**：Agent 在复杂逻辑处添加 "Insight" 教育块解释原理
- **自定义模式**：通过 settings 或 plugin 扩展

**Qwen Code 现状**：无 Output Style 概念，Agent 始终以同一种风格（直接给出完整代码）输出。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `constants/outputStyles.ts` (216行) | `Explanatory`、`Learning`（20+ 行函数触发、2-10 行贡献请求） |
| `utils/outputStyles.ts` | `getAllOutputStyles()`（built-in + plugin + settings 合并） |

**Qwen Code 修改方向**：新建 `core/outputStyles.ts`；系统提示中根据 `settings.outputStyle` 注入 style 指令。

**实现成本评估**：
- 涉及文件：~3 个
- 新增代码：~250 行
- 开发周期：~2 天（1 人）
- 难点：Style 指令的 Prompt 工程——确保模型稳定遵循不同风格的输出规则

**改进前后对比**：
- **改进前**：新人请求 "实现一个排序算法"，Agent 直接给出完整代码，新人复制粘贴学不到东西
- **改进后**：Learning 模式下 Agent 给出框架 + `TODO(human)` 占位符，新人填写关键逻辑，Agent 检查并指导

**相关文章**：[Git 工作流与会话管理](./git-workflow-session-deep-dive.md)

**意义**：教学和培训场景需要 Agent 引导用户动手实践，而非直接给出答案。
**缺失后果**：Agent 只有一种输出风格——无法适应教学需求。
**改进收益**：Learning 模式让 Agent 变教练——暂停、出题、等用户实现后继续。

---

<a id="item-5"></a>

### 5. Fast Mode（P2）

你在修复线上紧急 bug 时需要 Agent 尽快响应，但日常编码时更关心成本。目前只能通过切换不同模型来平衡速度和成本，但这意味着切换上下文和模型能力。Fast Mode 的核心是同一模型的速度分级——比如同一个 Opus 4.6 模型提供标准模式（$5/$25/Mtok）和快速模式（$30/$150/Mtok），用户一键切换而不丢失上下文。关键设计包括冷却机制：429 限流后自动回退到标准模式，冷却结束恢复。

**Qwen Code 现状**：支持通过 `/model` 切换不同模型，但无同一模型的速度分级能力，无冷却/回退机制。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/fastMode.ts` (532行) | `isFastModeAvailable()`、`triggerFastModeCooldown()`、`FastModeState` |
| `commands/fast/fast.tsx` | /fast 命令 UI + 定价显示 |

**Qwen Code 修改方向**：需后端支持速度分级；`modelCommand.ts` 新增 `--fast` toggle（非指定备用模型）；UI 显示当前速度档位。

**实现成本评估**：
- 涉及文件：~4 个
- 新增代码：~350 行
- 开发周期：~3 天（1 人）
- 难点：依赖后端 API 支持速度分级，前端实现相对简单但需等后端就绪

**改进前后对比**：
- **改进前**：紧急 bug → 切换到更快的模型 → 丢失当前上下文 → 重新描述问题
- **改进后**：紧急 bug → `/fast` 一键切换 → 同一模型同一上下文加速推理 → 修完后 `/fast` 切回标准

**相关文章**：[成本追踪与 Fast Mode](./cost-fastmode-deep-dive.md)

**意义**：时间敏感任务（紧急 bug 修复）需要更快推理，日常任务需要更低成本。
**缺失后果**：用户无法灵活平衡速度和成本——始终使用同一速度。
**改进收益**：一键切换推理速度——紧急用 Fast，日常用 Standard，同一模型同一上下文。

---

<a id="item-6"></a>

### 6. Computer Use 桌面自动化（P2）

你在调试前端页面时，希望 Agent 能"看到"浏览器渲染结果并点击按钮验证交互。或者你需要从 Figma 设计稿中提取参数，再在代码中实现。但目前 Agent 只能操作文件和终端，对桌面应用完全"失明"。解决方案是通过 MCP Server 桥接原生模块实现桌面自动化：

| 能力 | 实现方式 |
|------|---------|
| 截图 | SCContentFilter（macOS）/ JPEG 0.75 压缩 |
| 鼠标/键盘 | Rust enigo NAPI 原生绑定 |
| 剪贴板 | OS 原生 API |
| 安全门控 | TCC 权限 + 特性开关 + 订阅检查 |

**Qwen Code 现状**：无桌面自动化能力，Agent 只能通过文件读写和 Shell 命令与系统交互。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/computerUse/executor.ts` | `moveMouse()`、`click()`、`type()`、截图 JPEG 0.75 |
| `utils/computerUse/mcpServer.ts` | 进程内 MCP Server（stdio） |
| `utils/computerUse/gates.ts` | GrowthBook `tengu_malort_pedway` |

**Qwen Code 修改方向**：新建 `packages/computer-use/` 原生模块；注册为 MCP Server；`settingsSchema.ts` 新增门控。

**实现成本评估**：
- 涉及文件：~8 个
- 新增代码：~1200 行
- 开发周期：~8 天（1 人）
- 难点：跨平台原生模块编译（macOS/Linux/Windows），TCC 权限处理，截图性能优化

**改进前后对比**：
- **改进前**：调试 CSS 布局问题 → 用户手动截图 → 粘贴给 Agent 描述问题 → 来回多轮
- **改进后**：Agent 自动截图浏览器 → 识别布局偏差 → 修改 CSS → 再次截图验证 → 一轮完成

**相关文章**：[Computer Use 桌面自动化](./computer-use-deep-dive.md)

**意义**：前端调试和跨应用自动化需要 Agent '看到' 桌面——截图、点击、打字。
**缺失后果**：Agent 只能操作文件和终端——无法操作浏览器/IDE/桌面应用。
**改进收益**：解锁跨应用工作流——自动验证 UI、提取设计稿、操作数据库 GUI。

---

<a id="item-7"></a>

### 7. Denial Tracking（P2）

你开启了 auto-edit 或 yolo 模式让 Agent 自动执行操作，但权限分类器突然开始连续拒绝合法操作——Agent 看起来在"思考"但实际什么都没做。这种"静默失败"很难被发现，因为用户不知道操作被拒绝了。根源是权限分类器可能因为某些模式匹配规则陷入"全拒绝"死循环。解决方案是追踪连续拒绝次数，超过阈值（连续 3 次 / 累计 20 次）自动回退到手动确认模式，让用户看到被拒操作并决定是否批准。

**Qwen Code 现状**：`permission-manager.ts` 处理权限判定，但不追踪拒绝次数，无回退机制。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/permissions/denialTracking.ts` (45行) | `DENIAL_LIMITS`、`recordDenial()`、`shouldFallbackToPrompting()` |

**Qwen Code 修改方向**：`permission-manager.ts` 新增 `DenialTrackingState`；auto-edit/yolo 模式拒绝时累计；超限回退到 default 模式。

**实现成本评估**：
- 涉及文件：~2 个
- 新增代码：~60 行
- 开发周期：~0.5 天（1 人）
- 难点：确定合理的阈值（连续拒绝次数、累计拒绝次数），避免正常拒绝被误判

**改进前后对比**：
- **改进前**：分类器连续拒绝文件写入 → Agent 静默跳过 → 用户等 10 分钟发现任务没完成
- **改进后**：连续 3 次拒绝后自动回退 → 弹出手动确认 → 用户批准后继续执行

**意义**：权限分类器可能陷入连续拒绝的死循环——用户完全无感知。
**缺失后果**：分类器可能永久阻塞合法操作——'静默失败'。
**改进收益**：连续拒绝自动检测 → 回退到手动确认——用户看到被拒操作并可批准。

---

<a id="item-8"></a>

### 8. 并发 Session 管理（P2）

你在多个终端窗口同时运行 Agent 处理不同任务（一个修 bug、一个写测试、一个做重构），但各实例之间互不感知——可能两个 Agent 同时修改同一个文件导致冲突，或者你忘记某个终端还有 Agent 在后台运行消耗 Token。解决方案是通过 PID 文件追踪所有活跃 Session：

```
~/.claude/sessions/
├── 12345.json  # { kind: "interactive", cwd: "/project-a", startedAt: "..." }
├── 12346.json  # { kind: "background", cwd: "/project-b", startedAt: "..." }
```

启动时注册、退出时清理、`countConcurrentSessions()` 扫描时自动过滤已退出的 orphan process。

**Qwen Code 现状**：每个 Session 独立运行，无法感知其他终端的 Agent 实例，无并发追踪。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/concurrentSessions.ts` (204行) | `registerSession()`、`countConcurrentSessions()`、退出时 `registerCleanup()` |

**Qwen Code 修改方向**：新建 `utils/concurrentSessions.ts`；`gemini.tsx` 启动时注册 PID 文件；退出时自动清理。

**实现成本评估**：
- 涉及文件：~3 个
- 新增代码：~200 行
- 开发周期：~1.5 天（1 人）
- 难点：orphan process 的可靠检测（进程异常退出未清理 PID 文件），跨平台进程状态查询

**改进前后对比**：
- **改进前**：3 个终端各跑一个 Agent → 不知道彼此存在 → 两个 Agent 同时 `git commit` 导致冲突
- **改进后**：启动时显示 "检测到 2 个活跃 Session" → 可查看各 Session 的工作目录和状态 → 避免冲突

**相关文章**：[成本追踪与 Fast Mode](./cost-fastmode-deep-dive.md)

**意义**：开发者常在多终端运行多个 Agent 实例——需要追踪和管理。
**缺失后果**：无法了解其他终端的 Agent 状态——可能重复执行相同任务。
**改进收益**：PID 追踪 + 后台脱附——多终端并行工作不冲突。

---

<a id="item-9"></a>

### 9. Git Diff 统计（P2）

你让 Agent 批量修改了多个文件后，想在 commit 前快速了解变更范围——改了哪些文件、各增删了多少行。但目前需要手动切到另一个终端执行 `git diff --stat`。更麻烦的是，如果 Agent 修改了大量文件（比如全局重命名），完整 diff 可能非常大导致输出卡顿。解决方案是两阶段 diff 策略：

1. **快速探测**：`git diff --numstat` 获取文件数和行数统计
2. **按需详情**：对关注的文件再取完整 hunks，限制 50 文件、1MB/文件、400 行/文件

merge/rebase 期间自动跳过避免干扰。

**Qwen Code 现状**：`gitWorktreeService.ts` 通过 simple-git 库执行 git 操作，但编辑后不自动展示 diff 统计。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/gitDiff.ts` (532行) | `MAX_FILES = 50`、`MAX_DIFF_SIZE_BYTES = 1_000_000`、hunks 解析 |

**Qwen Code 修改方向**：`gitWorktreeService.ts` 的 simple-git 调用替换为原生 `git diff --numstat` 解析；添加文件数/大小限制。

**实现成本评估**：
- 涉及文件：~2 个
- 新增代码：~300 行
- 开发周期：~2 天（1 人）
- 难点：hunks 解析逻辑，大 diff 的截断策略，merge/rebase 状态检测

**改进前后对比**：
- **改进前**：Agent 修改了 15 个文件 → 用户不知道改了什么 → 手动 `git diff --stat` → 切换终端上下文
- **改进后**：Agent 修改完自动展示 `+120 -45 across 15 files` 统计 → 用户一眼掌握变更范围

**相关文章**：[Git 工作流与会话管理](./git-workflow-session-deep-dive.md)

**意义**：编辑后的 diff 统计帮助用户在 commit 前了解变更影响范围。
**缺失后果**：无 git-aware diff——用户需手动 git diff 检查变更。
**改进收益**：编辑后自动展示按文件统计的 diff——变更一目了然。

---

<a id="item-10"></a>

### 10. 文件历史快照（P2）

你让 Agent 连续执行了 5 步修改，发现第 3 步改错了。如果只有 git checkpoint，你只能回滚到上一个 commit，丢失第 4、5 步的正确修改。你真正需要的是回滚到"第 2 步完成后"的状态，只撤销第 3 步。解决方案是按消息粒度创建文件快照——每次编辑前自动备份文件（SHA256 + mtime 校验），每条消息处理完创建一个快照点，上限 100 个/session：

```
Session 快照链：
  msg-1 → [file-a.v1] → msg-2 → [file-a.v2, file-b.v1] → msg-3 → [file-a.v3]
  用户可回滚到 msg-2 → file-a 恢复 v2，file-b 恢复 v1
```

**Qwen Code 现状**：依赖 git checkpoint 进行恢复，粒度为 commit 级别，无消息级快照。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/fileHistory.ts` (1115行) | `fileHistoryTrackEdit()`、`fileHistoryMakeSnapshot()`、`MAX_SNAPSHOTS = 100` |

**Qwen Code 修改方向**：`edit.ts` 和 `write-file.ts` 编辑前调用 snapshot；新建 `fileHistory.ts` 管理备份目录。

**实现成本评估**：
- 涉及文件：~4 个
- 新增代码：~500 行
- 开发周期：~3 天（1 人）
- 难点：快照存储空间管理（大文件频繁修改），SHA256 校验避免重复备份，过期快照清理

**改进前后对比**：
- **改进前**：5 步修改后发现第 3 步有误 → `git checkout` 回到 commit → 丢失第 4、5 步正确修改
- **改进后**：5 步修改后发现第 3 步有误 → 回滚到 msg-2 快照 → 只撤销第 3 步 → 第 4、5 步可重做

**相关文章**：[Git 工作流与会话管理](./git-workflow-session-deep-dive.md)

**意义**：细粒度文件恢复比 git checkout 更灵活——可回滚到任意消息时刻。
**缺失后果**：恢复粒度粗（git 级）——只能回到 checkpoint，不能回到特定消息。
**改进收益**：按消息粒度恢复——Agent 第 3 步改错了可直接回到第 2 步。

---

<a id="item-11"></a>

### 11. Deep Link 协议（P2）

你在浏览器里看到一个 GitHub Issue，想让 Agent 立刻处理这个问题。目前的流程是：打开终端 → cd 到项目目录 → 输入 `qwen-code` → 复制 Issue 内容 → 粘贴为 Prompt。通过 Deep Link 协议，只需点击一个链接（如 `qwen-code://open?q=Fix+issue+123&cwd=/my-project`），Agent 就能自动在正确的项目目录中启动并预填充 Prompt。实现流程：

```
点击链接 → OS 协议路由 → 终端自动检测（10+ 终端优先级链）→ 预填充 prompt → 来源 banner + Enter 确认
```

安全设计：显示来源 banner、参数限制 ≤5000 字符、需手动按 Enter 确认执行。

**Qwen Code 现状**：无 URI scheme 注册，只能通过终端命令行手动启动。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/deepLink/parseDeepLink.ts` | URI 解析 + 参数验证（≤5000 字符） |
| `utils/deepLink/terminalLauncher.ts` | 10+ 终端检测（iTerm/Ghostty/Kitty/...） |
| `utils/deepLink/registerProtocol.ts` | macOS/Linux/Windows 协议注册 |

**Qwen Code 修改方向**：新建 `utils/deepLink/`；注册 `qwen-code://` scheme；`gemini.tsx` 新增 `--handle-uri` 参数。

**实现成本评估**：
- 涉及文件：~5 个
- 新增代码：~600 行
- 开发周期：~4 天（1 人）
- 难点：跨平台协议注册（macOS .app / Linux .desktop / Windows Registry），终端检测优先级链

**改进前后对比**：
- **改进前**：看到 Issue → 打开终端 → cd 项目 → 启动 Agent → 粘贴 Issue 内容（~30 秒）
- **改进后**：看到 Issue → 点击 Deep Link → Agent 自动启动在正确目录 + 预填充 Prompt（~3 秒）

**相关文章**：[Deep Link 协议](./deep-link-protocol-deep-dive.md)

**意义**：从浏览器/IDE/Slack 一键启动 Agent 减少上下文切换成本。
**缺失后果**：每次都需打开终端 + cd 到项目目录 + 输入命令——切换成本高。
**改进收益**：点击链接即启动——预填充 prompt + 自动定位项目目录。

---

<a id="item-12"></a>

### 12. Plan 模式 Interview（P2）

你让 Agent "重构认证模块"，Agent 立刻开始改代码——但它理解的"重构"是提取公共方法，而你想的是从 JWT 迁移到 OAuth2。等 Agent 改了 20 个文件后你才发现方向错了，不得不全部撤销重来。根源是 Agent 跳过了"需求澄清"直接进入"执行"。Plan 模式的 Interview 阶段解决这个问题——Agent 先通过提问收集关键信息（"你说的重构具体指什么？涉及哪些接口？"），确认需求后制定计划，用户审批计划后才开始执行：

```
interview（提问收集需求） → plan（制定实施计划） → 用户确认 → execute（执行）
```

**Qwen Code 现状**：已有 `exitPlanMode` 工具支持计划到执行的过渡，但缺少 `enterPlanMode` 的 interview 阶段，Agent 直接开始执行。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `tools/EnterPlanModeTool/EnterPlanModeTool.ts` | interview 阶段状态管理 |
| `tools/ExitPlanModeTool/ExitPlanModeV2Tool.ts` | 计划确认 + 执行过渡 |

**Qwen Code 修改方向**：已有 `exitPlanMode` 工具；新增 `enterPlanMode` 工具支持 interview 阶段的附件系统。

**实现成本评估**：
- 涉及文件：~3 个
- 新增代码：~250 行
- 开发周期：~2 天（1 人）
- 难点：interview 阶段的状态管理（何时结束提问进入计划），附件系统集成

**改进前后对比**：
- **改进前**："重构认证模块" → Agent 立刻改 20 个文件 → 方向错误 → 全部撤销返工
- **改进后**："重构认证模块" → Agent 提问 "JWT→OAuth2 还是提取公共方法？" → 确认后制定计划 → 用户批准 → 精准执行

**意义**：复杂任务先收集需求再动手——减少因理解不全导致的返工。
**缺失后果**：Agent 直接开始执行——可能方向偏差后大量返工。
**改进收益**：先 interview 收集完整需求 → 再制定计划 → 用户确认后执行。

---

<a id="item-13"></a>

### 13. BriefTool（P2）

你让 Agent 重构 10 个文件的测试用例，预计需要 3 分钟。在这 3 分钟里你完全不知道 Agent 做到了哪一步——是刚开始还是快完成了？是顺利还是卡住了？只能盯着终端等最终结果。BriefTool 让 Agent 在执行过程中异步推送状态消息而不中断工具执行：

```
[进度] 已完成 3/10 个文件的测试重构
[进度] 第 4 个文件 auth.test.ts 结构复杂，预计需要额外 30 秒
[进度] 已完成 8/10，发现 2 个文件的测试需要更新 mock 数据
```

消息可包含附件（如 diff 预览），通过事件系统推送到 UI，不阻塞工具执行流水线。

**Qwen Code 现状**：Agent 执行过程中只在最终完成时输出结果，无中间进度通知能力。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `tools/BriefTool/BriefTool.ts` | 异步消息发送 + 附件支持 |

**Qwen Code 修改方向**：新建 `tools/brief.ts`；通过事件系统（`AgentEventEmitter`）向 UI 推送进度消息。

**实现成本评估**：
- 涉及文件：~3 个
- 新增代码：~150 行
- 开发周期：~1 天（1 人）
- 难点：与现有事件系统的集成，UI 端进度消息的渲染位置和格式

**改进前后对比**：
- **改进前**：10 个文件重构 → 3 分钟黑箱等待 → 不知道是卡住还是正常运行
- **改进后**：10 个文件重构 → 实时看到 "3/10 完成" → 知道进度正常 → 安心做其他事

**意义**：长时间后台任务中用户需要了解进度——否则只能盲等。
**缺失后果**：用户不知道 Agent 在做什么——只能等最终结果。
**改进收益**：Agent 可异步推送进度消息——'已完成 3/5 个文件修改'。

---

<a id="item-14"></a>

### 14. SendMessageTool（P2）

你在 Arena 模式下启动了多个 Agent（一个负责前端、一个负责后端、一个负责测试），但它们各自独立执行、互不知晓——前端 Agent 修改了 API 接口格式但后端 Agent 不知道，导致接口不匹配。多 Agent 协作的核心是消息传递。SendMessageTool 提供：

| 通信方式 | 用途 |
|---------|------|
| 单播（name） | Leader → 指定 Worker |
| 广播（`*`） | 通知所有 Agent |
| 结构化消息 | `shutdown_request`、`plan_approval` 等协议 |
| 传输层 | UDS Socket / 文件邮箱（proper-lockfile） |

**Qwen Code 现状**：Arena 模式支持多 Agent 并行执行，但 Agent 间无通信通道，只能各自独立工作。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `tools/SendMessageTool/SendMessageTool.ts` (917行) | 路由逻辑（name → agentNameRegistry → tasks → mailbox）、broadcast |
| `utils/teammateMailbox.ts` (1183行) | 文件邮箱 + proper-lockfile |

**Qwen Code 修改方向**：Arena 模式下新增消息传递工具；基于文件或 IPC 实现 agent 间通信。

**实现成本评估**：
- 涉及文件：~5 个
- 新增代码：~800 行
- 开发周期：~5 天（1 人）
- 难点：消息路由可靠性（Agent 退出后的消息处理），文件邮箱的并发锁机制，广播的 exactly-once 语义

**改进前后对比**：
- **改进前**：前端 Agent 改了 API 接口 → 后端 Agent 不知道 → 生成不兼容的代码 → 手动修复
- **改进后**：前端 Agent 改了 API 接口 → 发消息通知后端 Agent → 后端 Agent 同步更新 → 接口一致

**相关文章**：[多 Agent系统](./multi-agent-deep-dive.md)

**意义**：多 Agent 协作需要 Agent 间通信——分配任务、报告进度、协调行动。
**缺失后果**：Arena 模式下 Agent 间无法通信——只能各自独立执行。
**改进收益**：Leader 分配任务后 Worker 通过消息报告进度——真正的团队协作。

---

<a id="item-15"></a>

### 15. FileIndex（P2）

你在一个有 5000+ 文件的大型仓库中工作，想找到"那个处理用户认证的中间件文件"——但记不清文件名是 `authMiddleware.ts` 还是 `auth-handler.ts` 还是 `middleware/authenticate.js`。目前只能用 `grep` 搜索文件内容或猜测路径，效率低下。FileIndex 提供 fzf 风格的模糊文件搜索——输入 `authmid` 就能匹配到 `src/middleware/authMiddleware.ts`。实现方式：

- **异步增量索引**：启动时后台构建文件索引，不阻塞用户交互
- **nucleo 风格匹配**：支持非连续字符匹配、路径感知排序
- **实时更新**：文件变更时增量更新索引

**Qwen Code 现状**：文件定位依赖精确路径或 `grep` 内容搜索，无模糊文件名搜索能力。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `native-ts/file-index/` | 原生 TS 文件索引器 |

**Qwen Code 修改方向**：新建 `tools/fileIndex.ts`；基于 `glob` + 模糊匹配库（如 fzf-for-js）实现。

**实现成本评估**：
- 涉及文件：~3 个
- 新增代码：~400 行
- 开发周期：~3 天（1 人）
- 难点：大仓库（10 万+ 文件）的索引性能，增量更新策略，模糊匹配算法的排序质量

**改进前后对比**：
- **改进前**："找那个 auth 中间件" → `find . -name "*auth*"` 返回 30 个结果 → 逐个检查
- **改进后**：输入 `authmid` → 模糊匹配排序后第一个就是 `src/middleware/authMiddleware.ts`

**意义**：大型仓库中精确文件名难以记住——模糊搜索是刚需。
**缺失后果**：需要精确文件名才能定位——'那个 auth 相关的文件叫什么来着？'
**改进收益**：fzf 风格模糊搜索——输入部分关键词即可定位。

---

<a id="item-16"></a>

### 16. Notebook Edit（P2）

你是数据科学家，日常工作大量使用 Jupyter Notebook。你想让 Agent "修改第 3 个 cell 的数据预处理逻辑"，但 `.ipynb` 文件本质是 JSON 格式——直接用文本编辑工具修改极易破坏 JSON 结构（漏掉逗号、破坏 cell metadata）。更重要的是，Notebook 的 cell 有 ID 追踪机制，暴力修改会导致 Jupyter 前端状态异常。Notebook Edit 提供 cell 级原子操作：

```
解析 ipynb JSON → 定位目标 cell（by index/ID） → 修改 source → 保留 metadata/outputs → 写回
```

支持 code cell 和 markdown cell，集成文件历史快照实现撤销。

**Qwen Code 现状**：Agent 将 `.ipynb` 视为普通文本文件，用通用编辑工具修改，容易破坏 JSON 结构和 cell metadata。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `tools/NotebookEditTool/NotebookEditTool.ts` | cell 编辑 + ID 追踪 |

**Qwen Code 修改方向**：新建 `tools/notebookEdit.ts`；解析 ipynb JSON → 定位 cell → 修改 → 写回。

**实现成本评估**：
- 涉及文件：~2 个
- 新增代码：~300 行
- 开发周期：~2 天（1 人）
- 难点：ipynb JSON schema 的完整性保持（cell metadata、outputs、nbformat 版本兼容）

**改进前后对比**：
- **改进前**："修改第 3 个 cell" → Agent 用文本替换修改 JSON → 破坏 cell metadata → Jupyter 报错
- **改进后**："修改第 3 个 cell" → Agent 解析 JSON 定位 cell → 只修改 source 字段 → 结构完整

**意义**：数据科学工作流大量使用 Jupyter notebook——原生支持是差异化能力。
**缺失后果**：Agent 无法直接操作 .ipynb 文件——数据科学家需手动编辑。
**改进收益**：原生 cell 级编辑——Agent 可直接修改 notebook 代码和 markdown。

---

<a id="item-17"></a>

### 17. 自定义快捷键（P2）

你习惯了 VS Code 的 `Ctrl+K Ctrl+S` 打开快捷键设置，或者你是 Vim 用户习惯用 `Ctrl+[` 代替 Escape。但 Agent 的快捷键是硬编码的，无法修改——每次操作都要和肌肉记忆对抗。解决方案是支持 multi-chord 组合键 + 自定义配置：

```json
// ~/.qwen/keybindings.json
{
  "ctrl+k ctrl+s": "openSettings",
  "ctrl+k ctrl+p": "switchProject",
  "ctrl+shift+enter": "submitAndContinue"
}
```

关键设计：multi-chord 状态机（第一个键触发后等待第二个键）、跨平台适配（Windows VT mode 检测）、Reserved keys（Ctrl+C/D）不可重绑避免破坏终端基础功能。

**Qwen Code 现状**：`KeypressContext.tsx` 处理按键事件，但快捷键硬编码在代码中，不支持 multi-chord，无用户自定义能力。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `keybindings/` | `defaultBindings.ts`、multi-chord 状态机 |

**Qwen Code 修改方向**：`KeypressContext.tsx` 扩展支持 chord 序列；新增 `~/.qwen/keybindings.json` 配置加载。

**实现成本评估**：
- 涉及文件：~3 个
- 新增代码：~300 行
- 开发周期：~2 天（1 人）
- 难点：multi-chord 状态机的超时处理（第一个键按下后多久取消等待），Windows VT mode 兼容性

**改进前后对比**：
- **改进前**：Vim 用户按 `Ctrl+[` → 无反应 → 只能用固定快捷键 → 效率降低
- **改进后**：编辑 `keybindings.json` 绑定 `Ctrl+[` → 按下即触发预期操作 → 符合肌肉记忆

**意义**：高级用户对快捷键有强烈自定义需求——尤其 Vim 用户。
**缺失后果**：固定快捷键无法满足不同用户习惯。
**改进收益**：multi-chord + 自定义 keybindings.json——每个用户定制最顺手的操作方式。

---

<a id="item-18"></a>

### 18. Session Ingress Auth（P2）

你在企业服务器上以 headless 模式运行 Agent 供团队远程调用。但如果没有认证机制，任何能访问该端口的人都能向 Agent 发送指令——这在共享服务器环境中是严重的安全漏洞（其他用户可以让你的 Agent 读取/修改你的代码）。Session Ingress Auth 通过 bearer token 保护远程 Session：

```
启动：qwen-code --headless --ingress-token-fd 3  （token 通过文件描述符传入，不出现在命令行）
访问：Authorization: Bearer <token>              （每次请求携带 token）
```

Token 传递方式支持文件描述符（安全，不暴露在 ps 输出中）和 well-known 文件两种。

**Qwen Code 现状**：headless 模式无认证机制，监听端口后任何人可直接访问。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/sessionIngressAuth.ts` | bearer token 验证 |

**Qwen Code 修改方向**：新建 `utils/sessionIngressAuth.ts`；headless 模式下验证 `--ingress-token` 参数。

**实现成本评估**：
- 涉及文件：~2 个
- 新增代码：~120 行
- 开发周期：~1 天（1 人）
- 难点：文件描述符传递 token 的跨平台兼容性，token 的安全存储和轮换

**改进前后对比**：
- **改进前**：headless Agent 监听端口 → 同事/脚本可直接发送恶意指令 → 代码被篡改
- **改进后**：headless Agent 要求 bearer token → 无 token 的请求被拒绝 → 仅授权用户可操控

**意义**：企业多用户环境需要安全的远程 Agent 访问控制。
**缺失后果**：无认证机制——任何能访问端口的人都能操控 Agent。
**改进收益**：bearer token 认证——仅授权用户可远程访问。

---

<a id="item-19"></a>

### 19. 企业代理支持（P2）

你在企业网络中使用 Agent，公司网络要求所有 HTTPS 流量经过代理服务器并使用企业自签 CA 证书。Agent 发起 API 调用时因为 SSL 证书验证失败而报错——`UNABLE_TO_VERIFY_LEAF_SIGNATURE`。即使设置了 `HTTPS_PROXY` 环境变量，WebSocket 连接（用于 streaming）仍然绕过代理失败。解决方案是完整的企业代理支持：

| 场景 | 处理方式 |
|------|---------|
| HTTPS 代理 | CONNECT-to-WebSocket relay |
| 企业 CA 证书 | 自动注入 CA cert 链到 TLS 验证 |
| 内网资源 | NO_PROXY allowlist（RFC1918 + API + GitHub + 包注册表）|
| 代理故障 | fail-open 降级，不阻断 Agent 使用 |

**Qwen Code 现状**：依赖 Node.js 默认的 `HTTPS_PROXY` 环境变量处理，不支持 CA cert 注入，WebSocket 不走代理。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `upstreamproxy/upstreamproxy.ts` | CONNECT relay + CA cert 注入 |
| `utils/proxy.ts` | `configureGlobalAgents()`、`getProxyFetchOptions()` |

**Qwen Code 修改方向**：`config.ts` 扩展代理配置；Node.js `https.Agent` 注入自定义 CA cert。

**实现成本评估**：
- 涉及文件：~3 个
- 新增代码：~400 行
- 开发周期：~3 天（1 人）
- 难点：CONNECT tunnel 上的 WebSocket 升级，CA cert 链的正确拼接，NO_PROXY 匹配逻辑

**改进前后对比**：
- **改进前**：企业网络中启动 Agent → `UNABLE_TO_VERIFY_LEAF_SIGNATURE` → 完全无法使用
- **改进后**：Agent 自动检测代理 + 注入企业 CA cert → API 调用和 WebSocket 正常工作

**意义**：企业网络（代理/VPN/防火墙）是 Agent 部署的常见环境。
**缺失后果**：企业代理环境下 API 调用失败——Agent 不可用。
**改进收益**：CONNECT relay + CA cert 注入——企业网络环境下正常工作。

---

<a id="item-20"></a>

### 20. ConfigTool（P2）

你让 Agent 做一个复杂任务：先分析代码架构（需要大上下文模型），再生成大量模板代码（小模型更快更便宜），最后审查关键逻辑（又需要大模型）。但目前 Agent 无法自动切换模型——你需要在每个阶段手动执行 `/model` 命令。ConfigTool 让 Agent 通过工具自主读写配置：

```
Agent 内部调用：
  config.set("model", "qwen-max")      // 分析阶段用大模型
  config.set("model", "qwen-turbo")    // 生成模板用小模型
  config.set("theme", "light")          // 根据终端自动调整
```

所有 set 操作经过 schema 验证，防止 Agent 设置无效值。

**Qwen Code 现状**：配置只能通过 `/settings` 命令手动修改，Agent 无法程序化读写配置。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `tools/ConfigTool/ConfigTool.ts` | get/set 操作 + schema 验证 |

**Qwen Code 修改方向**：新建 `tools/config.ts`；通过 `config.ts` API 读写设置并验证。

**实现成本评估**：
- 涉及文件：~2 个
- 新增代码：~200 行
- 开发周期：~1.5 天（1 人）
- 难点：确定哪些配置项允许 Agent 修改（安全边界），schema 验证的完整性

**改进前后对比**：
- **改进前**：复杂任务的不同阶段需要不同模型 → 用户手动 `/model` 切换 3 次 → 打断工作流
- **改进后**：Agent 根据任务阶段自动 `config.set("model", ...)` → 无缝切换 → 用户无感知

**意义**：模型根据任务自动调整配置——如切换到更适合当前任务的模型。
**缺失后果**：模型无法程序化修改设置——用户需手动 /settings。
**改进收益**：Agent 可自主切换模型/主题/权限——根据任务需求自适应。

---

<a id="item-21"></a>

### 21. 终端主题检测（P2）

你在浅色终端（如 macOS Terminal 默认主题）中使用 Agent，但 Agent 的代码高亮和 UI 颜色是为深色终端设计的——浅黄色文字在白色背景上几乎不可见，语法高亮的颜色对比度极低。你不得不手动执行 `/theme light` 切换。更糟糕的是，如果你在不同终端之间切换（比如 iTerm 深色 + VS Code 终端浅色），每次都要手动调整。解决方案是自动检测终端背景色：

```
检测链：OSC 11 查询（精确） → $COLORFGBG 环境变量（回退） → 默认 dark（兜底）
```

启动时自动探测，将 `auto` 主题解析为具体的 dark/light。

**Qwen Code 现状**：`semantic-colors.ts` 使用硬编码主题或依赖用户手动配置，无自动检测。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/systemTheme.ts` | `resolveThemeSetting()`（OSC 11 + COLORFGBG） |

**Qwen Code 修改方向**：`semantic-colors.ts` 新增 `detectTheme()` 函数；启动时探测并设置默认主题。

**实现成本评估**：
- 涉及文件：~2 个
- 新增代码：~80 行
- 开发周期：~0.5 天（1 人）
- 难点：OSC 11 查询在不同终端（iTerm/Kitty/Alacritty/Windows Terminal）的兼容性

**改进前后对比**：
- **改进前**：浅色终端启动 Agent → 浅黄色文字在白色背景上不可见 → 手动 `/theme light`
- **改进后**：浅色终端启动 Agent → 自动检测背景色 → 使用浅色主题 → 颜色对比度正常

**意义**：终端 dark/light 模式不一致会导致代码高亮和 UI 不可读。
**缺失后果**：硬编码主题可能在浅色终端上不可见。
**改进收益**：自动检测终端背景色——UI 始终可读。

---

<a id="item-22"></a>

### 22. 自动后台化 Agent（P2）

你让 Subagent 执行一个耗时任务（比如在 10 个文件中添加单元测试），Subagent 执行了 2 分钟还没完成——这期间你的主 Agent 被阻塞，无法输入新指令，只能干等。你真正想要的是 Subagent 超过一定时间后自动转入后台，释放前台让你继续与主 Agent 交互，Subagent 完成后再通知你。解决方案很简单——启动 timer，超过阈值（可配置的 ms 数）自动将任务标记为 background：

```
Subagent 启动 → 计时器开始 → 超过阈值 → 自动转后台 → 释放前台
                                         ↓
                              完成后通知用户 "测试添加完成，共 10 个文件"
```

**Qwen Code 现状**：Subagent 执行期间始终占用前台，用户必须等待执行完成才能继续交互。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `tools/AgentTool/AgentTool.tsx` | `getAutoBackgroundMs()` |

**Qwen Code 修改方向**：`agent.ts` 执行时启动 timer；超时将任务标记为 background 并释放前台。

**实现成本评估**：
- 涉及文件：~2 个
- 新增代码：~100 行
- 开发周期：~1 天（1 人）
- 难点：后台任务完成后的通知机制，后台任务的输出缓冲区管理

**改进前后对比**：
- **改进前**：Subagent 执行 3 分钟 → 用户被阻塞 3 分钟 → 无法做其他事
- **改进后**：Subagent 执行 30 秒后自动转后台 → 用户继续与主 Agent 交互 → 完成后收到通知

**意义**：长时间 Agent 任务阻塞用户交互——用户只能等待。
**缺失后果**：用户等 Agent 执行完才能继续输入——浪费时间。
**改进收益**：超时自动转后台——用户继续交互，Agent 后台完成。

---

<a id="item-23"></a>

### 23. 队列输入编辑（P2）

你在 Agent 处理当前任务时提前输入了下一条指令（排队），但刚按完回车就发现打了个错别字或者指令有误。指令已经入队了，无法撤回——你只能等 Agent 处理到这条错误指令后，再花一轮对话纠正。更糟的情况是：你排了 3 条指令，第 2 条有误，但无法单独修改它。解决方案是让排队中的命令可见可编辑：

```
当前执行：正在修改 auth.ts...
排队中 [1]：修改 user.ts 的登录逻辑     ← 可见
排队中 [2]：运行测试                     ← 可见
按 Escape：弹出可编辑命令到输入框修改
```

关键设计：区分可编辑命令（用户输入）和不可编辑命令（task-notification、isMeta 等系统消息），只弹出可编辑项。

**Qwen Code 现状**：`AsyncMessageQueue` 支持消息排队，但队列内容不可见、不可编辑。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/messageQueueManager.ts` | `popAllEditable()`、`isQueuedCommandEditable()` |

**Qwen Code 修改方向**：`AsyncMessageQueue` 新增 `popEditable()` 方法；`InputPrompt.tsx` 渲染队列内容并处理 Escape。

**实现成本评估**：
- 涉及文件：~3 个
- 新增代码：~150 行
- 开发周期：~1.5 天（1 人）
- 难点：UI 中队列内容的实时渲染，可编辑/不可编辑消息的分类逻辑

**改进前后对比**：
- **改进前**：排队指令有误 → 无法撤回 → Agent 执行错误指令 → 额外一轮纠正
- **改进后**：排队指令有误 → 按 Escape 弹出到输入框 → 修改后重新提交 → 零浪费

**进展**：[QwenLM/qwen-code#2871](https://github.com/QwenLM/qwen-code/pull/2871)（open）— 实现了 Up 方向键弹出队列消息到输入框编辑。

**相关文章**：[输入队列与中断机制](./input-queue-deep-dive.md)

**意义**：发现排队输入有误需要修改——但已入队无法撤回。
**缺失后果**：错误输入已排队 → Agent 处理错误指令 → 需要额外一轮纠正。
**改进收益**：Escape 弹出排队命令到输入框——修改后重新提交。

---

<a id="item-24"></a>

### 24. 状态栏紧凑布局（P2）

你在 13 寸笔记本上分屏工作——左边代码编辑器、右边 Agent 终端。Agent 终端只有约 30 行高度，但状态栏（Footer）在显示不同信息时会伸缩——有时 1 行、有时 3 行。每次 Footer 高度变化，上方的 Agent 输出内容会跳动（scroll content shift），阅读体验很差。更关键的是，非关键信息（如模型名称、Token 用量）占用了宝贵的终端空间。解决方案是 Footer 固定高度 + 条件显示：

```
固定 1 行高度 → 非关键信息（模型名/Token）按需显示 → 内容区域最大化
```

**Qwen Code 现状**：`Footer.tsx` 的高度随内容变化，显示信息较多时占用 2-3 行。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `components/PromptInput/PromptInputFooterLeftSide.tsx` | 固定高度约束 |
| `components/StatusLine.tsx` | 条件显示（`statusLineShouldDisplay`） |

**Qwen Code 修改方向**：`Footer.tsx` 添加 `height: 1`（或 Ink `<Box height={1}>`）固定行高；条件显示非关键信息。

**实现成本评估**：
- 涉及文件：~2 个
- 新增代码：~50 行
- 开发周期：~0.5 天（1 人）
- 难点：确定哪些信息优先显示、哪些条件隐藏，固定高度下的内容截断策略

**改进前后对比**：
- **改进前**：Footer 在 1-3 行之间跳动 → 上方内容不断移位 → 阅读体验差 → 小终端可用空间少
- **改进后**：Footer 固定 1 行 → 内容区域稳定不跳动 → 小终端多出 2 行可用空间

**意义**：终端空间有限（笔记本 + 分屏），Footer 挤压内容区域。
**缺失后果**：Footer 占用偏高——Agent 输出和用户输入可见行数减少。
**改进收益**：固定高度 Footer——最大化内容区域，小终端也舒适。

---

---

<a id="item-25"></a>

### 25. 会话标签与搜索（P2）

**问题**：用户长期使用 Agent 会积累大量会话（几十甚至上百个），只能按时间顺序浏览。想找之前某个功能（如"重构"、"登录 bug"）的会话，需要逐条翻看标题。Claude Code 的 `/tag` 命令支持为会话打标签，按标签/repo/标题搜索。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `commands/tag/tag.tsx` (189行) | `/tag add`、`/tag remove`、`/tag list`、`/tag search` |
| `utils/sessionStorage.ts` | `saveTag()`、`loadTags()`、`searchSessionsByTag()` |

**Qwen Code 现状**：`sessionService.ts` 仅有 `listSessions()`（按 mtime 排序）和 `loadLastSession()`，无标签系统。

**Qwen Code 修改方向**：① `ChatSession` 接口新增 `tags: string[]` 字段；② 新增 `searchByTags()` 方法；③ 新建 `/tag` 命令。

**实现成本评估**：
- 涉及文件：~3 个
- 新增代码：~150 行
- 开发周期：~1 天（1 人）
- 难点：标签持久化存储格式（建议 JSONL 每行追加）

**意义**：长期项目积累大量会话，按标签快速定位。
**缺失后果**：只能按时间排序，无法按主题/功能分类。
**改进收益**：标签搜索 = 快速定位历史会话。

---

<a id="item-26"></a>

### 26. @include 指令（P2）

**问题**：团队规范（CLAUDE.md/AGENTS.md）随着项目增长可能变成巨型单文件（500+ 行），难以维护。Claude Code 支持 `@path` 递归引用其他文件，最大深度 5 层，外部文件需用户审批。

**关键设计细节**：

- **正则匹配**：`/(?:^|\s)@((?:[^\s\\]|\\ )+)/g` — 支持 `@path`、`@./path`、`@~/path`
- **最大深度**：`MAX_INCLUDE_DEPTH = 5` — 防止循环引用
- **外部文件审批**：不在原始 cwd 目录下的文件需弹窗审批
- **文本类型白名单**：40+ 种扩展名（`.md`、`.txt`、`.js`、`.ts` 等）
- **循环引用防护**：`processedPaths` Set 去重

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/claudemd.ts` (1480行) | `processMemoryFile()`、`extractIncludePathsFromTokens()`、`MAX_INCLUDE_DEPTH` |

**Qwen Code 现状**：指令加载器直接读取 CLAUDE.md/AGENTS.md 全文，无 `@include` 解析。

**Qwen Code 修改方向**：① 指令加载器新增 `@path` 正则解析；② 递归加载（深度限制 5）；③ 外部文件审批对话框；④ 文本类型白名单过滤。

**实现成本评估**：
- 涉及文件：~3 个
- 新增代码：~200 行
- 开发周期：~2 天（1 人）
- 难点：外部文件审批流程与现有权限系统集成

**意义**：团队规范可模块化复用，避免巨型单文件。
**缺失后果**：所有指令堆在一个文件中，难以维护。
**改进收益**：模块化指令 = 可复用 + 可组合。

---

<a id="item-27"></a>

### 27. 附件协议（P2）

**问题**：Agent 每轮对话会注入大量附件（IDE 选区、诊断信息、记忆、Hook 输出等），如果不加控制可能撑爆上下文窗口。Claude Code 定义 60+ 附件类型，每类独立 token 预算，3 阶段有序执行。

**关键设计细节**：

- **60+ 附件类型**：文件（file/compact_file_reference/pdf_reference）、IDE（selected_lines_in_ide/opened_file_in_ide）、内存（nested_memory/relevant_memories）、Hook（hook_blocking_error/hook_success）、Agent（agent_mention/teammate_mailbox）等
- **Per-type 预算**：`MAX_MEMORY_LINES = 200`、`MAX_MEMORY_BYTES = 4096`、`RELEVANT_MEMORIES_CONFIG.MAX_SESSION_BYTES = 60KB`
- **3 阶段有序执行**：① userInput 附件 → ② thread 附件 → ③ queuedCommand 附件
- **媒体上限**：`API_MAX_MEDIA_PER_REQUEST = 100`

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/attachments.ts` (3998行) | 60+ AttachmentType 定义、`getAttachments()` 3 阶段流程 |
| `constants/apiLimits.ts` | `API_MAX_MEDIA_PER_REQUEST = 100` |
| `utils/tokenBudget.ts` | per-type 预算配置 |

**Qwen Code 现状**：无附件类型注册表，所有附件统一处理，无 per-type 预算控制。

**Qwen Code 修改方向**：① 新增 `AttachmentType` 枚举；② 新增预算配置；③ 收集附件时按预算截断；④ 3 阶段有序执行。

**实现成本评估**：
- 涉及文件：~4 个
- 新增代码：~300 行
- 开发周期：~3 天（1 人）
- 难点：预算配置与实际 token 计算的精确对齐

**意义**：精细控制各类附件的 token 消耗，防止单一类型溢出。
**缺失后果**：无预算控制 = 附件可能撑爆上下文窗口。
**改进收益**：per-type 预算 = 可控 token 用量。

---

<a id="item-28"></a>

### 28. Git 状态自动注入（P2）

**问题**：模型不知道自己在哪个分支、项目规模多大，可能给错命令（如在 feature 分支上执行 merge）。Claude Code 每轮自动注入 gitBranch/cwd/platform/fileCount 到系统提示。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/api.ts` | `countFilesRoundedRg()` — rg 扫描项目返回约数 |
| `constants/prompts.ts` | uncached section 中注入 git 状态 |

**Qwen Code 现状**：`getGitBranch()` 和 `geminiMdFileCount` 仅用于统计，不注入到系统提示。模型需自行执行 `git status` 获取。

**Qwen Code 修改方向**：`prompts.ts` 系统提示中新增动态段注入 git 状态（每轮重新计算）。

**实现成本评估**：
- 涉及文件：~2 个
- 新增代码：~50 行
- 开发周期：~0.5 天（1 人）
- 难点：fileCount 计算性能（建议复用 rg 结果）

**意义**：模型始终知道当前分支和项目规模。
**缺失后果**：模型不知道自己在哪个分支，可能给错命令。
**改进收益**：每轮自动注入 = 模型感知上下文。

---

<a id="item-29"></a>

### 29. IDE 诊断注入（P2）

**问题**：用户让模型修复编译错误，需要先手动粘贴错误信息——多一轮交互。Claude Code 通过 `diagnosticTracker` 服务自动收集 LSP 诊断，每轮注入到系统提示。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `services/diagnosticTracking.ts` | `LSPDiagnosticRegistry` — 收集/存储诊断 |
| `utils/attachments.ts` | `diagnostics` 附件类型注入 |

**Qwen Code 现状**：LSP 服务（`lsp.ts`）存在，但诊断仅依赖 IDE 插件主动推送，不自动收集注入。

**Qwen Code 修改方向**：① `lsp.ts` 新增诊断收集（`onDiagnostics` 回调）；② 获取活跃诊断（最近 10 个 error/warning）；③ `prompts.ts` 注入诊断到系统提示。

**实现成本评估**：
- 涉及文件：~3 个
- 新增代码：~100 行
- 开发周期：~1 天（1 人）
- 难点：诊断去重和时效性（只注入最新的）

**意义**：模型自动看到编译错误/警告，无需用户手动报告。
**缺失后果**：用户需要手动粘贴错误信息 = 多一轮交互。
**改进收益**：自动诊断注入 = 模型即时修复编译错误。

---

<a id="item-30"></a>

### 30. 终端主题检测（P2）

**问题**：浅色终端启动 Agent 后，浅黄色文字在白色背景上不可见——用户需要手动 `/theme light`。Claude Code 自动通过 OSC 11 查询终端背景色，`COLORFGBG` 环境变量回退。

**关键设计细节**：

- **OSC 11 查询**：解析 `rgb:R/G/B` 或 `#RRGGBB` 格式
- **亮度计算**：ITU-R BT.709 — `0.2126*r + 0.7152*g + 0.0722*b`，>0.5 为 light
- **COLORFGBG 回退**：ANSI 色号 0-6/8 为暗，7/9-15 为亮
- **模块级缓存**：`cachedSystemTheme` 避免重复查询

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/systemTheme.ts` | `resolveThemeSetting()`、`detectFromColorFgBg()`、`cachedSystemTheme` |
| `ink/terminal-querier.ts` | OSC 11 查询实现 |

**Qwen Code 现状**：`semantic-colors.ts` 硬编码主题或依赖用户配置，无自动检测。

**Qwen Code 修改方向**：`semantic-colors.ts` 新增 `detectTheme()` 函数，启动时调用。

**实现成本评估**：
- 涉及文件：~2 个
- 新增代码：~80 行
- 开发周期：~0.5 天（1 人）
- 难点：OSC 11 在不同终端（iTerm/Kitty/Alacritty/Windows Terminal）的兼容性

**意义**：自动适配终端背景色 = 颜色对比度始终正常。
**缺失后果**：浅色终端启动 Agent → 浅黄色文字不可见。
**改进收益**：自动检测 = UI 始终可读。

---

<a id="item-31"></a>

### 31. 自动后台化 Agent（P2）

**问题**：Subagent 执行长任务（如批量修改 10 个文件），主 Agent 被阻塞——用户无法输入新指令。Claude Code 超时 15s 自动转后台 + Assistant 模式检测。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `tools/BashTool/BashTool.tsx` | `getAutoBackgroundMs()`、`ASSISTANT_BLOCKING_BUDGET_MS = 15_000`、`onTimeout()` |

**Qwen Code 现状**：需用户显式设置 `isBackground`，无超时自动转后台。

**Qwen Code 修改方向**：`agent.ts` 执行时启动 timer，超时自动将任务标记为 background 并释放前台。

**实现成本评估**：
- 涉及文件：~2 个
- 新增代码：~100 行
- 开发周期：~1 天（1 人）
- 难点：后台任务完成后的通知机制

**意义**：长任务自动不阻塞前台交互。
**缺失后果**：用户被阻塞等待长任务完成。
**改进收益**：超时自动转后台 = 用户继续交互。

---

<a id="item-32"></a>

### 32. 密钥扫描（P2）

**问题**：模型执行工具可能意外输出 API 密钥/密码到对话中。Claude Code 在 Team Memory 上传前用 29 条 gitleaks 规则扫描，防止密钥泄露。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `services/teamMemory/gitleaks.ts` | 29 条 gitleaks 规则（AWS Key、Generic API Key 等） |

**Qwen Code 现状**：无工具输出密钥扫描。

**Qwen Code 修改方向**：① 新建 `secretScanner.ts`，定义 50+ 正则规则；② 工具输出后调用扫描；③ 发现密钥则警告/阻断。

**实现成本评估**：
- 涉及文件：~3 个
- 新增代码：~150 行
- 开发周期：~1 天（1 人）
- 难点：规则覆盖率和误报率平衡

**意义**：防止模型意外输出 API 密钥/密码。
**缺失后果**：工具输出可能包含密钥 → 写入日志/对话。
**改进收益**：自动扫描 = 防意外泄露。

---

<a id="item-33"></a>

### 33. 子进程环境变量清洗（P2）

**问题**：敏感环境变量（如 `AWS_SECRET_ACCESS_KEY`、`GITHUB_TOKEN`）可能泄漏到工具执行的子进程中。Claude Code 自动剥离 30+ 敏感变量后启动子进程。

**Qwen Code 现状**：继承完整环境。

**Qwen Code 修改方向**：① 新建 `envSanitizer.ts`，定义 30+ 敏感变量集合；② 启动子进程前调用 `sanitizeEnv()` 清洗。

**实现成本评估**：
- 涉及文件：~2 个
- 新增代码：~50 行
- 开发周期：~0.5 天（1 人）
- 难点：敏感变量清单的完整性

**意义**：防止敏感变量泄漏到子进程。
**缺失后果**：API 密钥/凭证可能泄漏到工具输出。
**改进收益**：环境变量清洗 = 更安全。

---

<a id="item-34"></a>

### 34. 自定义快捷键（P2）

**问题**：Vim/Emacs 用户无法自定义 Agent 的键盘快捷键——键位固定。Claude Code 支持 multi-chord 组合键 + `keybindings.json` 自定义，341 行默认绑定 + 验证器。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `keybindings/defaultBindings.ts` (341行) | 默认键绑定 |
| `keybindings/parser.ts`、`resolver.ts`、`validate.ts` | 解析/验证框架 |
| `keybindings/loadUserBindings.ts` | 加载 `keybindings.json` |

**Qwen Code 现状**：`keyMatchers.ts` 不可用户配置，无 `keybindings.json` 支持。

**Qwen Code 修改方向**：① 新增 `keybindings.json` schema；② 加载和解析用户配置；③ 与默认绑定合并。

**实现成本评估**：
- 涉及文件：~4 个
- 新增代码：~200 行
- 开发周期：~2 天（1 人）
- 难点：multi-chord 组合键解析

**意义**：Vim/Emacs 用户自定义习惯键位。
**缺失后果**：键位固定，无法自定义。
**改进收益**：自定义快捷键 = 个人效率提升。

---

<a id="item-35"></a>

### 35. Thinking 块保留（P2）

**问题**：复杂任务需要多轮推理，模型每轮的思考过程（thinking block）不应丢失。Claude Code 跨轮保留 thinking 块 + 1h 空闲自动清理 + latch 防缓存破坏。

**Qwen Code 现状**：thinking 块仅限当前轮。

**Qwen Code 修改方向**：`client.ts` 新增 `thinkingBlocks` 持久化 + 空闲清理（1h 阈值）。

**实现成本评估**：
- 涉及文件：~2 个
- 新增代码：~100 行
- 开发周期：~1 天（1 人）
- 难点：仅 Anthropic 模型适用，需 feature flag 控制

**意义**：推理思考跨轮保留 = 复杂任务连续性。
**缺失后果**：每轮思考丢失 = 重复推理。
**改进收益**：Thinking 块保留 = 模型推理连贯性。

---
