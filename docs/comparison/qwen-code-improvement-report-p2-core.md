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

### 5. Fast Mode（P2）⚠️ 部分实现（不同方案）

你在修复线上紧急 bug 时需要 Agent 尽快响应，但日常编码时更关心成本。目前只能通过切换不同模型来平衡速度和成本，但这意味着切换上下文和模型能力。Fast Mode 的核心是同一模型的速度分级——比如同一个 Opus 4.6 模型提供标准模式（$5/$25/Mtok）和快速模式（$30/$150/Mtok），用户一键切换而不丢失上下文。关键设计包括冷却机制：429 限流后自动回退到标准模式，冷却结束恢复。

**Qwen Code 现状**：**已实现 `fastModel`（走不同方案）**。Qwen Code 的 `fastModel` 是**另一个**（通常更小/更快/更便宜的）模型——例如 `qwen-turbo` 作为主 `qwen-plus` 的 fastModel——用于 speculation / followup suggestions / 快响应操作。通过 `/model --fast` 命令或 `/settings` 配置。**不是**同一模型的速度分级（依赖 provider 支持 priority tier 定价，仅 Anthropic 提供）。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/fastMode.ts` (532行) | `isFastModeAvailable()`、`triggerFastModeCooldown()`、`FastModeState` |
| `commands/fast/fast.tsx` | /fast 命令 UI + 定价显示 |

**Qwen Code 实现历程**（commit + PR 时间线）：

| Commit / PR | 说明 |
|---|---|
| `49702ce26` refactor(followup) | 合并 `suggestionModel + speculationModel` → 统一 `fastModel` |
| `e9bc686f0` refactor(settings) | `fastModel` 移到顶层（和 `model` 并列） |
| `fea1739d2` feat(cli) | **`/model --fast` 命令** 设置 fast model |
| `c06276799` feat(cli) | `/model --fast` 打开模型选择对话框 |
| `2348093fb` fix(cli) | `/model --fast` 默认选中当前 fast model |
| [PR#3077](https://github.com/QwenLM/qwen-code/pull/3077) ✓ | improve /model --fast description clarity + prevent accidental activation |
| [PR#3086](https://github.com/QwenLM/qwen-code/pull/3086) ✓ | add --fast hint to /model description for discoverability |
| [PR#3120](https://github.com/QwenLM/qwen-code/pull/3120) ✓ | replace text input with **model picker** for Fast Model in /settings |

**两种方案对比**：

| 维度 | Claude Code Fast Mode | Qwen Code fastModel |
|---|---|---|
| **核心思路** | **同一模型**的速度分级（Opus 4.6 standard vs Opus 4.6 fast） | **另一个**更快/更便宜的模型（如 qwen-turbo） |
| **前提** | Anthropic "priority tier" 定价（2-5× 价格，同模型更快） | 任意 provider 的多模型选择 |
| **触发方式** | 用户手动或自动切换速度档位 | 用于 speculation / followup suggestions 等 fast-response 操作 |
| **冷却机制** | 429 → 回退 standard → 冷却后恢复 | 无冷却（两个模型互相独立） |
| **上下文切换** | ❌（同模型同上下文） | ⚠️（不同模型，需重新载入 context） |
| **适用场景** | 紧急 bug 修复时全 session 加速 | 局部 fast path（补全、推测、followup） |

**为什么走不同方案**：Qwen Code 支持多 provider（DashScope / ModelScope / Anthropic / Google / OpenAI 兼容），但**只有 Anthropic 提供 priority tier 定价**——同一模型不同速度档位。DashScope 和 OpenAI 都没有此定价。所以 Qwen Code 采用"**换用更快的备用模型**"的替代方案，通过 `fastModel` 配置。

**改进前后对比（以 qwen-code 当前实现为基准）**：
- **改进前**：`suggestionModel` 和 `speculationModel` 是两个独立配置，概念混乱
- **改进后（2026-04 合并）**：统一为 `fastModel`，用 `/model --fast` 或 `/settings` 设置，UI 提供模型 picker 而非文本输入

**相关文章**：[成本追踪与 Fast Mode](./cost-fastmode-deep-dive.md)

**意义**：时间敏感任务（紧急 bug 修复、speculation、followup suggestions）需要更快推理。
**缺失后果（此前）**：`suggestionModel` + `speculationModel` 两个概念混乱，用户不知道怎么配置。
**改进收益**：统一的 `fastModel` 配置 + `/model --fast` 命令 + `/settings` picker——一处配置，多处复用。
**仍存差距**：没有**同模型 speed-tier** 能力（受限于非 Anthropic provider），但通过不同模型达到相似效果。

> **小结**：本 item 的"同一模型速度分级"目标在 Qwen Code 下**无法完全对齐**（provider 定价机制限制），但 Qwen Code 用 **"fastModel 配置 + 换用更快模型"** 达到了**相似的 fast-response 效果**，应视为**已部分实现**。如果 Anthropic priority tier 被 DashScope/其他 provider 引入，再考虑补齐"同模型速度分级"的剩余能力。

---

<a id="item-6"></a>

### 6. Computer Use 桌面自动化（P2）⚠️ 实验性功能

> **⚠️ 实验性功能警告**：Computer Use 在 Claude Code 中**默认禁用**，受 GrowthBook feature gate `tengu_malort_pedway`（源码 `utils/computerUse/gates.ts:30`）控制，**且**还需要 Max/Pro 订阅等级双重门控。实际 Claude Code 用户中极少有人能体验到此功能。本 item 保留用于记录能力方向，但**不建议 P2 优先级实现**——优先做真正的核心能力，桌面自动化可降级到 P3 或单独评估需求后再决定。

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

### 11. Deep Link 协议（P2）⚠️ 实验性功能

> **⚠️ 实验性功能警告**：Deep Link 协议在 Claude Code 中**默认禁用**，受 GrowthBook feature gate `tengu_lodestone_enabled` 控制（源码 `utils/deepLink/registerProtocol.ts:302`：`if (!getFeatureValue_CACHED_MAY_BE_STALE('tengu_lodestone_enabled', false))`）。这意味着即使 Claude Code 安装了，`claude-cli://` 协议也不会自动注册到 OS——除非 gate 被启用。本 item 描述的"点击链接一键启动"流程在实际 Claude Code 上不可用。建议**降级为 P3**，或标注"待 Claude Code 自身将此功能从实验升级为默认后再实现"。

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

**进展**：[PR#3214](https://github.com/QwenLM/qwen-code/pull/3214)（open，tanzhenxin）— **替换 fdir 爬虫为 `git ls-files + ripgrep` 两级回退**。Closes [Issue#3137](https://github.com/QwenLM/qwen-code/issues/3137)。修改动机：原 fdir 在每次按键都重新扫描目录树，大仓库响应缓慢且不遵循 `.gitignore`。新策略：① git 仓库优先用 `git ls-files`（秒级返回，天然遵循 .gitignore）；② 非 git 目录 fallback 到 ripgrep 扫描。本 PR 直接解决了 `@` 文件补全在大项目里卡顿的问题。

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

### 20. 终端主题检测（P2）

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

<a id="item-21"></a>

### 21. 队列输入编辑（P2）

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

**进展**：[QwenLM/qwen-code#2871](https://github.com/QwenLM/qwen-code/pull/2871) ✓ 已合并 — 实现了 Up 方向键弹出队列消息到输入框编辑。

**相关文章**：[输入队列与中断机制](./input-queue-deep-dive.md)

**意义**：发现排队输入有误需要修改——但已入队无法撤回。
**缺失后果**：错误输入已排队 → Agent 处理错误指令 → 需要额外一轮纠正。
**改进收益**：Escape 弹出排队命令到输入框——修改后重新提交。

---

<a id="item-22"></a>

### 22. 状态栏紧凑布局（P2）

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

<a id="item-23"></a>

### 23. 会话标签与搜索（P2）

**问题**：用户长期使用 Agent 积累数十甚至上百个会话，只能按时间顺序浏览。想找之前"重构认证模块"或"修复登录 bug"的会话，需要逐条翻看标题——效率极低。

**Claude Code 的方案**：`/tag` 命令为会话打标签，支持按标签/仓库/标题搜索：

```
/tag add refactor        # 给当前会话加标签
/tag add auth-module     # 可加多个标签
/tag search refactor     # 搜索所有带 refactor 标签的会话
/tag list                # 列出当前会话的所有标签
/tag remove refactor     # 移除标签
```

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `commands/tag/tag.tsx` (189行) | `/tag add`、`/tag remove`、`/tag list`、`/tag search` |
| `utils/sessionStorage.ts` | `saveTag()`、`loadTags()`、`searchSessionsByTag()` |

**Qwen Code 现状**：`sessionService.ts` 仅有 `listSessions()`（按 mtime 排序）和 `loadLastSession()`，无标签系统，无搜索能力。

**Qwen Code 修改方向**：① `ChatSession` 接口新增 `tags: string[]` 字段；② JSONL transcript 中新增 `tag` 条目类型；③ 新建 `/tag` 命令（add/remove/list/search）；④ `listSessions()` 支持按标签过滤。

**实现成本评估**：
- 涉及文件：~3 个
- 新增代码：~150 行
- 开发周期：~1 天（1 人）
- 难点：标签持久化格式——建议 JSONL 追加而非修改文件头

**改进前后对比**：
- **改进前**：50 个历史会话 → 只能按时间逐条翻看 → 找不到上周的重构会话
- **改进后**：`/tag search refactor` → 立即列出所有带"refactor"标签的会话

**意义**：长期项目积累大量会话，按标签快速定位是基本的信息管理能力。
**缺失后果**：只能按时间排序——上周的会话被今天的覆盖，无法快速回溯。
**改进收益**：标签 + 搜索 = 秒级定位历史会话——比逐条浏览快 10×。

---

<a id="item-24"></a>

### 24. Plan 状态机化 + Hint 注入(P2，AgentScope 参考)

**思路**：当前 qwen-code `/plan` 命令（PR#2921）是"一次性生成计划 + 进入 plan mode"。但没有**持续跟踪 subtask 执行状态**的能力——一旦退出 plan mode，哪个 subtask 完成、哪个还没做、哪个被放弃的信息就丢了。

**AgentScope 的做法**——`PlanNotebook`（源码 `src/agentscope/plan/_plan_notebook.py`）：

1. **4 种 subtask 状态机**：`todo` / `in_progress` / `done` / `abandoned`（`_plan_notebook.py:119-133`）
2. **每轮 reasoning 前自动注入 hint**：把"当前计划 + 活跃 subtask 详情"塞进 prompt（`_plan_notebook.py:50-68`）
3. **Plan 是 Agent 的工具**（不是外部编排）——Agent 自己决定何时 `create_plan` / `update_subtask_state` / `abandon_subtask`

**关键设计——Hint 模板**（源码 `_plan_notebook.py:50-68`）：

```python
when_a_subtask_in_progress: str = (
    "The current plan:\n"
    "```\n"
    "{plan}\n"
    "```\n"
    "Now the subtask at index {subtask_idx}, named '{subtask_name}', is "
    "'in_progress'. Its details are as follows:\n"
    "```\n"
    "{subtask}\n"
    "```\n"
    ...
)
```

每次 reasoning 开始时都把 plan 状态作为 hint 注入——即使模型"忘记"，plan 也会在下一轮 prompt 中重新出现。

**AgentScope 源码索引**：

| 文件 | 关键内容 |
|---|---|
| `src/agentscope/plan/_plan_notebook.py:172` | `PlanNotebook` 类 —— 管理 plan 作为 agent 工具 |
| `src/agentscope/plan/_plan_notebook.py:119-133` | 4 状态计数和筛选 `in_progress` subtask |
| `src/agentscope/plan/_plan_notebook.py:50-68` | Hint 注入模板 |
| `src/agentscope/plan/_plan_model.py` | `Plan` + `SubTask` Pydantic 数据模型 |

**Qwen Code 现状**：PR#2921 `/plan` 命令实现了 plan mode，但：
- 计划本身不是**持久状态**（退出 plan mode 就丢）
- 没有 subtask 状态机
- 没有每轮自动注入的 hint 机制
- Plan 不是 Agent 可以调用的工具

**Qwen Code 修改方向**：

1. **新建 `packages/core/src/plan/planNotebook.ts`**，定义 `Plan` / `SubTask` 数据模型（对标 Pydantic 版本）
2. 4 种 subtask 状态：`todo` / `in_progress` / `done` / `abandoned`
3. 注册 4 个新工具：`create_plan` / `update_subtask_state` / `finish_subtask` / `abandon_subtask`
4. 每轮 reasoning 前，如果当前有活跃 plan，自动把 `in_progress` subtask 作为 `<system-reminder>` 注入 prompt
5. Session 持久化 plan 状态（进程重启后恢复）

**实现成本评估**：
- 涉及文件：~5 个（plan/ 目录新建 + systemPromptBuilder 改动 + session persistence）
- 新增代码：~400 行
- 开发周期：~4 天（1 人）
- 难点：何时 prompt 注入？全部 or 仅 in_progress？如何避免 hint 重复？

**意义**：让 plan 从"一次性生成的文档"升级为"Agent 持续跟踪的状态机"——这是从 toy plan mode 到 production-grade planning 的关键升级。

**缺失后果**：当前 `/plan` 只是"生成一个漂亮的计划"，Agent 执行到一半就忘记。

**改进收益**：Plan 持久化 + 每轮 hint 注入 = Agent 不再"忘记"计划——即使经过 compaction，下一轮 prompt 也会重新看到活跃 subtask。

**相关参考**：
- [AgentScope Plan 模块分析](../frameworks/agentscope/03-key-modules.md#2-plan-模块first-class-计划原语)
- 现有 [/plan 模式 Interview](#item-12) item-12（互补方向）
- [PR#2921](https://github.com/QwenLM/qwen-code/pull/2921) ✓（已合并，基础能力）

---

<a id="item-25"></a>

### 25. A2A 协议集成（P2，AgentScope 参考）

**思路**：**Agent-to-Agent（A2A）协议**是 2025 年出现的 agent 间通信标准——不是工具调用（MCP 级别），而是**一个 agent 调用另一个独立运行的 agent**。场景：

- qwen-code 在项目 A 需要查询项目 B 的 Agent 了解接口细节
- 跨团队 agent 协作（Team A 的 reviewer agent 审查 Team B 的 PR）
- 企业内部 agent 目录（类似"服务发现"，但发现的是 agent 能力）

**AgentScope 的做法**——集成官方 **`a2a-sdk`** + **Nacos 服务发现**（源码 `pyproject.toml:50`）：

```python
a2a = [
    "a2a-sdk",                      # 官方 A2A 协议 SDK
    "httpx",
    "nacos-sdk-python>=3.0.0",      # 服务发现
]
```

**核心抽象**——`AgentCard`（源码 `src/agentscope/a2a/_base.py:18-25`）：

```python
@abstractmethod
async def get_agent_card(self, *args: Any, **kwargs: Any) -> AgentCard:
    """Get Agent Card from the configured source."""
```

**3 种 Resolver**：
1. **Well-known**（标准 A2A 注册表）
2. **File-based**（本地 JSON）
3. **Nacos**（阿里服务网格）

**AgentScope 是目前 6 款 Agent Framework 中唯一原生集成 A2A 协议的**。

**Qwen Code 现状**：Qwen Code 有 MCP Client（可以**调用工具**），但没有 A2A Client（无法**调用其他 agent**）。跨 agent 协作只能通过"让 MCP 包一层"的 workaround。

**Qwen Code 修改方向**：

1. 添加 `@a2a/sdk` 依赖（TypeScript 版本，若无则自行实现协议）
2. 新建 `packages/core/src/a2a/`：
   - `agentCard.ts`（AgentCard 数据模型）
   - `a2aClient.ts`（协议客户端）
   - `resolvers/{wellKnown,file,http}.ts`（3 种 resolver）
3. `/agents` 命令扩展：不仅列出本地定义的 subagent，也通过 A2A resolver 列出可达的远程 agent
4. 注入 `call_remote_agent` 工具到主代理

**实现成本评估**：
- 涉及文件：~6 个
- 新增代码：~500 行
- 开发周期：~5 天（1 人）
- 难点：
  - A2A 协议标准尚不稳定（2026 Q1-Q2 持续演进）
  - 远程调用的超时 / 重试 / 安全边界
  - AgentCard 与本地 agent 定义的 schema 映射

**意义**：A2A 是多 agent 系统的"HTTP 协议"——没有 A2A，agent 只能在单进程内通信，无法形成**跨组织、跨工具、跨语言**的 agent 网络。

**缺失后果**：qwen-code 无法参与跨组织 agent 协作场景，只能作为"**孤立的编程助手**"。

**改进收益**：A2A Client + 服务发现 = qwen-code 可以**作为网络中的 agent 节点**，被其他 agent 发现和调用，也可以发现和调用其他 agent。

**相关参考**：
- [AgentScope A2A 模块分析](../frameworks/agentscope/03-key-modules.md#3-a2a-协议agent-to-agent)
- [AgentScope EVIDENCE §7](../frameworks/agentscope/EVIDENCE.md#7-a2a-协议)
- [Google A2A Spec](https://github.com/google/agent-to-agent)

---

<a id="item-26"></a>

### 26. OTel 原生 Tracing + 5 类 Span Extractor（P2，AgentScope 参考）

**思路**：当前 qwen-code 的可观测性仅有阿里云 RUM（`gb4w8c3ygj-default-sea.rum.aliyuncs.com`），**没有 OpenTelemetry 支持**。这意味着：

- 无法接入企业 OTel 栈（Datadog / New Relic / Honeycomb / Jaeger / Grafana Tempo）
- 无法做细粒度 span 分析（哪个工具慢？哪个 LLM 调用慢？哪个 embedding 慢？）
- 无法跨服务 trace（qwen-code → MCP server → 数据库的完整调用链）

**AgentScope 的做法**——在主循环**每个关键操作点**自动发射 OTel span（源码 `src/agentscope/tracing/_trace.py:24-45`）：

```python
from ._extractor import (
    _get_agent_request_attributes,
    _get_agent_span_name,
    _get_agent_response_attributes,
    _get_llm_request_attributes,
    _get_llm_span_name,
    _get_llm_response_attributes,
    _get_tool_request_attributes,
    _get_tool_span_name,
    _get_tool_response_attributes,
    _get_formatter_request_attributes,
    _get_formatter_span_name,
    _get_formatter_response_attributes,
    _get_embedding_request_attributes,
    _get_embedding_span_name,
    _get_embedding_response_attributes,
    ...
)
```

**5 类 span extractor**：`Agent` / `LLM` / `Tool` / `Formatter` / `Embedding`，每类 3 个函数（`span_name` + `request_attrs` + `response_attrs`）。

**依赖**（`pyproject.toml:34-37`）：

```python
opentelemetry-api>=1.39.0,
opentelemetry-sdk>=1.39.0,
opentelemetry-exporter-otlp>=1.39.0,
opentelemetry-semantic-conventions>=0.60b0,
```

**Qwen Code 现状**：仅阿里云 RUM（移动端风格的 `useCursor` 事件），无 OTel。详见 [privacy-telemetry.md](./privacy-telemetry.md)。

**Qwen Code 修改方向**：

1. 添加 `@opentelemetry/api` + `@opentelemetry/sdk-node` + `@opentelemetry/exporter-trace-otlp-http` 依赖
2. 新建 `packages/core/src/tracing/`，参考 AgentScope 的 5 类 extractor 结构：
   - `agentTracer.ts`（Agent reply span）
   - `llmTracer.ts`（API 调用 span）
   - `toolTracer.ts`（工具执行 span）
   - `formatterTracer.ts`（消息格式化 span）
   - `embeddingTracer.ts`（embedding 计算 span）
3. 在 `query.ts` 主循环的每个关键点 wrap `tracer.startSpan(...)` + 属性记录
4. 通过 `OTEL_EXPORTER_OTLP_ENDPOINT` 环境变量配置 collector
5. 兼容现有阿里云 RUM（保留，不替换）

**实现成本评估**：
- 涉及文件：~8 个
- 新增代码：~800 行
- 开发周期：~6 天（1 人）
- 难点：
  - 所有异步调用点插桩的代码量大
  - 如何避免 span 泄漏（未 `end()`）
  - Privacy：确保 prompt / tool input 不被写入 span 属性（除非用户 opt-in）

**意义**：OTel 是**企业可观测性的标准协议**——没有 OTel 就无法进入大多数企业的监控体系。对 qwen-code 的企业化推广至关重要。

**缺失后果**：企业用户无法做 qwen-code 的性能分析、成本追踪、故障定位。CI/CD 流水线中无法跨服务 trace。

**改进收益**：OTel 原生支持 → qwen-code 可接入 Datadog / New Relic / Jaeger / Grafana Tempo，做**细粒度性能分析**、**跨服务 trace**、**企业级监控**。

**相关参考**：
- [AgentScope Tracing 模块](../frameworks/agentscope/03-key-modules.md#4-tracingotel-13-个-extractor)
- [AgentScope EVIDENCE §8](../frameworks/agentscope/EVIDENCE.md#8-tracing)
- 现有 [privacy-telemetry.md](./privacy-telemetry.md) 对比了 9 款 agent 的遥测方案
- OTel 语义约定：[GenAI spans](https://opentelemetry.io/docs/specs/semconv/gen-ai/)

---
