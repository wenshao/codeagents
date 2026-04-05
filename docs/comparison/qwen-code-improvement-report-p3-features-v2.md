# Qwen Code 改进建议 — P3 功能特性深度分析（第二轮）

> 本报告记录**严格去重扫描**后发现的 7 项真正未覆盖功能。每项都经过 Claude Code 源码验证和 Qwen Code 现状确认。
>
> 验证方法：对照 `qwen-code-improvement-report.md` 总览表、所有 deep-dive 文档、所有 P0-P3 分报告、所有 single-file Agent 文档，确认无重复。
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md)

---

<a id="item-1"></a>

### 1. Voice Mode 语音模式（P3）

**做什么**：Claude Code 支持**按住快捷键说话**——通过语音输入指令，Agent 自动转文字并执行：

```
[按住 Ctrl+V 录音] → "帮我跑一下测试" → [松开] → STT 转文字 → 自动执行
```

**关键源码**：

| 文件 | 行数 | 职责 |
|------|------|------|
| `commands/voice/voice.ts` | ~80 | `/voice` 命令——启用/禁用语音模式 |
| `commands/voice/index.ts` | 12 | 命令注册 |
| `hooks/useVoice.tsx` | 1144 | 核心 Hook——录音状态机、语言归一化、STT 连接 |
| `hooks/useVoiceIntegration.tsx` | 676 | 语音与主 UI 集成——消息注入、快捷键绑定 |
| `services/voiceStreamSTT.ts` | ~300 | Anthropic voice_stream WebSocket STT 客户端 |
| `services/voice.ts` | ~150 | 语音服务——音频录制（macOS 原生 / SoX） |
| `services/voiceKeyterms.ts` | ~50 | 语音关键词提取 |
| `components/LogoV2/VoiceModeNotice.tsx` | ~40 | 语音模式提示组件 |
| `context/voice.tsx` | ~80 | 语音上下文管理 |

**总规模**：~2532 行

**为什么 Qwen Code 应该学习**：

Qwen Code **完全没有语音输入能力**。用户在双手占用时（如调试硬件、操作设备）无法与 Agent 交互。

**关键设计细节**：

1. **Hold-to-Talk 录音**：按住快捷键开始录音，松开自动提交
2. **WebSocket STT**：连接 Anthropic `voice_stream` 端点（WebSocket），使用 `conversation_engine` 模型
3. **多语言支持**：支持 15+ 种语言（英语、西班牙语、法语、日语、中文等），自动检测
4. **OAuth 认证**：复用 Claude Code 的 OAuth 凭证，无需额外 API Key
5. **按键防抖**：自动重复按键事件重置计时器，防止误触
6. **KeepAlive**：8 秒心跳保持 WebSocket 连接

**Qwen Code 现状**：Qwen Code 的 `suggestionGenerator.ts` 中有 `ai_voice` 过滤（过滤掉"Let me..."风格的建议），但这是**输出风格过滤**，不是语音输入。Qwen Code 完全没有语音输入能力。

**Qwen Code 修改方向**：
1. （高成本）需要 DashScope 或类似平台的 STT API 支持
2. 新建 `hooks/useVoice.tsx`——录音状态机
3. 新建 `services/voiceStreamSTT.ts`——STT 客户端
4. 新建 `commands/voiceCommand.ts`——`/voice` 命令

**实现成本评估**：
- 涉及文件：~8 个
- 新增代码：~2000 行
- 开发周期：~10 天（1 人）
- 难点：需要 STT API 后端支持、音频录制跨平台兼容

**意义**：语音输入是 hands-free 交互的核心——双手占用时也能使用 Agent。
**缺失后果**：用户无法在双手占用时与 Agent 交互。
**改进收益**：按住快捷键说话——自动转文字执行——hands-free 编程。

---

<a id="item-2"></a>

### 2. CustomSelect 自定义下拉选择（P3）

**做什么**：Claude Code 自定义实现了一套下拉选择组件——支持搜索、键盘导航、多选、过滤：

```
[搜索框: "sandbox"]
 ▼ sandbox-exec          [选中]
   docker
   podman
```

**关键源码**：

| 文件 | 行数 | 职责 |
|------|------|------|
| `components/CustomSelect/select.tsx` | ~400 | 主组件——渲染选项列表、搜索框 |
| `components/CustomSelect/SelectMulti.tsx` | ~300 | 多选组件——支持多选多个选项 |
| `components/CustomSelect/use-select-state.ts` | ~300 | 选择状态管理——高亮、选中、过滤 |
| `components/CustomSelect/use-select-navigation.ts` | ~200 | 键盘导航——上下箭头、PageUp/PageDown |
| `components/CustomSelect/use-select-input.ts` | ~250 | 输入处理——搜索过滤、自动完成 |
| `components/CustomSelect/use-multi-select-state.ts` | ~150 | 多选状态管理 |
| `components/CustomSelect/use-select-input.ts` | ~250 | 输入过滤 |
| `components/CustomSelect/option-map.ts` | ~100 | 选项映射——快速查找 |
| `components/CustomSelect/select-option.tsx` | ~150 | 单个选项渲染 |
| `components/CustomSelect/select-input-option.tsx` | ~100 | 输入选项 |

**总规模**：~2200 行

**为什么 Qwen Code 应该学习**：

Qwen Code 使用 Ink 标准 `<Select>` 组件——功能有限，不支持搜索、多选、自定义过滤。当选项数量较多时（如 50+ 模型、100+ 插件），用户体验差。

**关键设计细节**：

1. **搜索过滤**：输入关键词实时过滤选项
2. **键盘导航**：上下箭头、PageUp/PageDown、Home/End
3. **多选支持**：`SelectMulti` 组件支持多选
4. **选项映射**：`option-map.ts` 快速查找选项
5. **自动完成**：输入自动匹配第一个选项

**Qwen Code 现状**：Qwen Code 使用 Ink `<Select>` 组件——不支持搜索、多选、自定义过滤。

**Qwen Code 修改方向**：
1. 新建 `components/CustomSelect/` 目录
2. 实现搜索过滤、键盘导航、多选功能
3. 替换现有 Ink `<Select>` 为 CustomSelect

**实现成本评估**：
- 涉及文件：~10 个
- 新增代码：~1500 行
- 开发周期：~8 天（1 人）
- 难点：Ink 终端渲染兼容性

**意义**：当选项数量多时，搜索+过滤大幅提升用户体验。
**缺失后果**：选项多时用户需逐个滚动查找——效率低。
**改进收益**：搜索+键盘导航+多选——快速定位目标选项。

---

<a id="item-3"></a>

### 3. Virtual Scrolling 虚拟滚动（P3）

**做什么**：Claude Code 实现了一套**虚拟滚动**——只渲染可视区域内的消息，隐藏区域的消息不渲染——支持超长对话（1000+ 轮）流畅滚动：

```
可视区域：10 条消息
滚动缓冲区：上 40 条 + 下 40 条
总消息数：1000+ 条
实际渲染：~90 条（非 1000+ 条）
```

**关键源码**：

| 文件 | 行数 | 职责 |
|------|------|------|
| `hooks/useVirtualScroll.ts` | 721 | 核心 Hook——滚动计算、项测量、可视区域管理 |
| `ink/components/ScrollBox.tsx` | ~200 | 滚动容器——DOM 滚动事件处理 |

**总规模**：~921 行

**为什么 Qwen Code 应该学习**：

Qwen Code 使用**完整渲染**——所有消息都渲染到终端。当对话超过 200 轮时，渲染延迟明显——滚动卡顿、内存增长。

**关键设计细节**：

1. **滚动量化**：`SCROLL_QUANTUM = 40`——每 40 行触发一次 React 重渲染，防止每像素滚动都触发
2. **默认估计**：`DEFAULT_ESTIMATE = 3` 行——对未测量项的保守估计
3. **过扫描**：`OVERSCAN_ROWS = 80`——可视区域外额外渲染 80 行
4. **冷启动计数**：`COLD_START_COUNT = 30`——布局前渲染 30 项
5. **外部存储同步**：`useSyncExternalStore` 同步滚动位置

**Qwen Code 现状**：Qwen Code 使用 Ink 标准渲染——所有消息都渲染。长对话时性能下降。

**Qwen Code 修改方向**：
1. 新建 `hooks/useVirtualScroll.ts`——虚拟滚动 Hook
2. 新建 `ink/components/ScrollBox.tsx`——滚动容器
3. 消息组件集成虚拟滚动

**实现成本评估**：
- 涉及文件：~3 个
- 新增代码：~500 行
- 开发周期：~3 天（1 人）
- 难点：Ink Yoga 布局兼容性

**意义**：长对话（1000+ 轮）流畅滚动——性能关键。
**缺失后果**：长对话时滚动卡顿、内存增长。
**改进收益**：虚拟滚动——只渲染可视区域——1000+ 轮流畅滚动。

---

<a id="item-4"></a>

### 4. Feedback Survey 用户反馈调查（P3）

**做什么**：Claude Code 在关键操作后自动弹出反馈调查——收集用户对功能满意度、使用体验的反馈：

```
[压缩完成后]
━━━━━━━━━━━━━━━━
How was the compression?
[ ] Great  [ ] OK  [ ] Poor

Would you like to share your transcript?
[Yes] [No]
```

**关键源码**：

| 文件 | 行数 | 职责 |
|------|------|------|
| `components/FeedbackSurvey/FeedbackSurvey.tsx` | ~200 | 主组件——调查 UI |
| `components/FeedbackSurvey/FeedbackSurveyView.tsx` | ~150 | 调查视图 |
| `components/FeedbackSurvey/useFeedbackSurvey.tsx` | ~200 | 调查状态管理 |
| `components/FeedbackSurvey/useMemorySurvey.tsx` | ~150 | 记忆调查 |
| `components/FeedbackSurvey/usePostCompactSurvey.tsx` | ~100 | 压缩后调查 |
| `components/FeedbackSurvey/useSurveyState.tsx` | ~100 | 调查持久化 |
| `components/FeedbackSurvey/TranscriptSharePrompt.tsx` | ~150 | 转录分享提示 |
| `components/FeedbackSurvey/submitTranscriptShare.ts` | ~100 | 提交转录分享 |
| `components/FeedbackSurvey/useDebouncedDigitInput.ts` | ~50 | 防抖数字输入 |

**总规模**：~1200 行

**为什么 Qwen Code 应该学习**：

Qwen Code **没有用户反馈调查功能**。无法收集用户对功能的满意度——改进方向依赖猜测而非数据。

**关键设计细节**：

1. **自动触发**：压缩完成后自动弹出调查
2. **记忆调查**：新 session 启动时询问记忆是否有用
3. **转录分享**：询问用户是否愿意分享转录用于改进
4. **防抖输入**：数字输入防抖——防止误触
5. **状态持久化**：`useSurveyState` 持久化调查状态——不重复弹出

**Qwen Code 现状**：Qwen Code 没有用户反馈调查功能。

**Qwen Code 修改方向**：
1. 新建 `components/FeedbackSurvey/` 目录
2. 实现压缩后调查、记忆调查
3. 集成到关键操作后流程

**实现成本评估**：
- 涉及文件：~8 个
- 新增代码：~800 行
- 开发周期：~5 天（1 人）
- 难点：调查触发时机选择

**意义**：用户反馈驱动改进方向——不依赖猜测。
**缺失后果**：改进方向依赖猜测——无法验证用户需求。
**改进收益**：自动弹出调查——收集满意度——数据驱动改进。

---

<a id="item-5"></a>

### 5. Turn Diffs 轮次差异统计（P3）

**做什么**：Claude Code 为**每个对话轮次**计算差异统计——显示该轮修改了哪些文件、加了多少行、删了多少行：

```
Turn 15: "Refactor auth middleware"
  Files changed: 3
  +120 -45 lines
  • src/auth/middleware.ts (+80 -30)
  • src/auth/utils.ts (+30 -10)
  • tests/auth.test.ts (+10 -5)
```

**关键源码**：

| 文件 | 行数 | 职责 |
|------|------|------|
| `hooks/useTurnDiffs.ts` | 213 | 核心 Hook——计算轮次差异、缓存统计 |

**总规模**：~213 行

**为什么 Qwen Code 应该学习**：

Qwen Code 有 `git diff` 功能，但**没有按轮次的差异统计**。用户无法直观看到"这一轮 Agent 改了什么"。

**关键设计细节**：

1. **结构化补丁解析**：解析 `structuredPatch` 获取 hunk 信息
2. **新增文件检测**：`type === 'create'` 检测新文件
3. **行数统计**：计算每个 hunk 的加行/删行
4. **用户提示预览**：截断用户提示到 ~30 字符
5. **缓存机制**：`TurnDiffCache` 缓存已计算差异

**Qwen Code 现状**：Qwen Code 有 `gitWorktreeService.ts` 提供 git diff，但没有按轮次的差异统计。

**Qwen Code 修改方向**：
1. 新建 `hooks/useTurnDiffs.ts`——轮次差异 Hook
2. 集成到消息组件——显示每轮变更统计

**实现成本评估**：
- 涉及文件：~2 个
- 新增代码：~150 行
- 开发周期：~1 天（1 人）
- 难点：structuredPatch 解析

**意义**：每轮变更一目了然——用户快速了解 Agent 做了什么。
**缺失后果**：无法直观看到每轮修改——需手动 git diff。
**改进收益**：轮次差异统计——每轮改了什么一目了然。

---

<a id="item-6"></a>

### 6. Session Backgrounding Ctrl+B 会话后台化（P3）

**做什么**：Claude Code 支持 **Ctrl+B** 快捷键将当前会话后台化——转为后台任务继续执行，释放前台与用户交互：

```
[前台执行中...]
用户按 Ctrl+B → 会话后台化 → 前台释放 → 用户可输入新指令
后台任务完成后 → 通知用户 "Task completed: 3 files modified"
```

**关键源码**：

| 文件 | 行数 | 职责 |
|------|------|------|
| `hooks/useSessionBackgrounding.ts` | 158 | 核心 Hook——后台化/前台化切换 |

**总规模**：~158 行

**为什么 Qwen Code 应该学习**：

Qwen Code 有 `--background` 标志启动后台任务，但**没有交互式后台化**——用户不能在任务执行中按 Ctrl+B 将其后台化。

**关键设计细节**：

1. **Ctrl+B 快捷键**：一键后台化
2. **前台任务同步**：后台任务消息同步到前台
3. **重新前台化**：可以将后台任务重新前台化
4. **状态管理**：`foregroundedTaskId` 追踪前台任务

**Qwen Code 现状**：Qwen Code 支持 `--background` 启动后台任务，但没有交互式 Ctrl+B 后台化。

**Qwen Code 修改方向**：
1. 新建 `hooks/useSessionBackgrounding.ts`——后台化 Hook
2. 添加 Ctrl+B 快捷键绑定
3. 集成到主 UI 循环

**实现成本评估**：
- 涉及文件：~2 个
- 新增代码：~120 行
- 开发周期：~1 天（1 人）
- 难点：前台/后台状态同步

**意义**：任务执行中可随时后台化——释放前台继续交互。
**缺失后果**：后台任务必须启动时指定——执行中无法切换。
**改进收益**：Ctrl+B 一键后台化——释放前台继续交互。

---

<a id="item-7"></a>

### 7. LogoV2 品牌标识系统（P3）

**做什么**：Claude Code 实现了一套品牌标识系统——启动动画、欢迎信息、功能提示、升级通知：

**关键源码**：

| 文件 | 行数 | 职责 |
|------|------|------|
| `components/LogoV2/LogoV2.tsx` | ~200 | 主标识组件 |
| `components/LogoV2/AnimatedAsterisk.tsx` | ~150 | 动画星号 |
| `components/LogoV2/AnimatedClawd.tsx` | ~200 | 动画 Clawd |
| `components/LogoV2/Clawd.tsx` | ~150 | Clawd 标识 |
| `components/LogoV2/CondensedLogo.tsx` | ~100 | 紧凑标识 |
| `components/LogoV2/WelcomeV2.tsx` | ~150 | 欢迎信息 |
| `components/LogoV2/Feed.tsx` | ~200 | 信息流 |
| `components/LogoV2/FeedColumn.tsx` | ~100 | 信息流列 |
| `components/LogoV2/VoiceModeNotice.tsx` | ~40 | 语音模式提示 |
| `components/LogoV2/OverageCreditUpsell.tsx` | ~100 | 用量提升提示 |
| `components/LogoV2/GuestPassesUpsell.tsx` | ~100 | 访客通行证提示 |
| `components/LogoV2/EmergencyTip.tsx` | ~80 | 紧急提示 |
| `components/LogoV2/Opus1mMergeNotice.tsx` | ~80 | Opus 1M 合并通知 |
| `components/LogoV2/ChannelsNotice.tsx` | ~80 | 渠道通知 |
| `components/LogoV2/feedConfigs.tsx` | ~300 | 信息流配置 |

**总规模**：~2030 行

**为什么 Qwen Code 应该学习**：

Qwen Code 有基础启动信息，但**没有品牌标识系统**——启动动画、欢迎信息、功能提示、升级通知都缺失。

**关键设计细节**：

1. **启动动画**：AnimatedAsterisk、AnimatedClawd 动画效果
2. **欢迎信息**：WelcomeV2 显示欢迎信息和快速入门
3. **信息流**：Feed 组件显示功能提示和新闻
4. **升级通知**：OverageCreditUpsell 提示用户提升用量
5. **紧急提示**：EmergencyTip 显示重要信息

**Qwen Code 现状**：Qwen Code 有基础启动信息，但没有完整的品牌标识系统。

**Qwen Code 修改方向**：
1. 新建 `components/LogoV2/` 目录
2. 实现启动动画、欢迎信息、信息流
3. 集成到主 UI 循环

**实现成本评估**：
- 涉及文件：~15 个
- 新增代码：~1500 行
- 开发周期：~8 天（1 人）
- 难点：动画效果终端兼容性

**意义**：品牌标识提升用户体验——启动更有趣、功能发现更容易。
**缺失后果**：启动信息单调——用户不知道新功能。
**改进收益**：启动动画+欢迎信息+功能提示——用户体验更丰富。

---

## 总结

本文件涵盖 7 项**现有改进总览表完全未提及**的功能：

| # | 改进点 | 源码规模 | 开发周期 | 意义 |
|---|--------|:--------:|:--------:|------|
| 1 | [Voice Mode 语音模式](#item-1) | ~2532 行 | ~10 天 | hands-free 交互 |
| 2 | [CustomSelect 自定义下拉](#item-2) | ~2200 行 | ~8 天 | 选项多时搜索 |
| 3 | [Virtual Scrolling 虚拟滚动](#item-3) | ~921 行 | ~3 天 | 长对话性能 |
| 4 | [Feedback Survey 反馈调查](#item-4) | ~1200 行 | ~5 天 | 数据驱动改进 |
| 5 | [Turn Diffs 轮次差异](#item-5) | ~213 行 | ~1 天 | 变更可视化 |
| 6 | [Session Backgrounding](#item-6) | ~158 行 | ~1 天 | 交互式后台化 |
| 7 | [LogoV2 品牌标识](#item-7) | ~2030 行 | ~8 天 | 用户体验提升 |

**总计**：~36 天（1 人）

> **验证声明**：本文件所有改进点已对照以下文档确认无重复：
> - `qwen-code-improvement-report.md` 总览表（全部 P0-P3 条目）
> - 所有 deep-dive 文档（33 个文件）
> - 所有 P0-P3 分报告（p0-p1-core/engine/platform、p2-core/perf/stability/tools、p3）
> - 所有 single-file Agent 文档（`tools/claude-code/` 目录下 10 个文件）
> - 之前已提交的 P2 uncovered 和 P3 features 报告
