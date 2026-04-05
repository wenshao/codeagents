# Qwen Code 改进建议 — P3 用户体验

> 低优先级用户体验改进项（9 项）。每项包含：问题场景、现状分析、改进前后对比、实现成本评估、Claude Code 源码索引、Qwen Code 修改方向。
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md)

---

<a id="item-1"></a>

### 1. Virtual Scrolling 虚拟滚动（P3）

**问题**：长会话（1000+ 轮）时终端滚动卡顿——所有消息节点都在 DOM 中渲染。

**Claude Code 源码索引**：`components/VirtualMessageList.tsx`、`hooks/useVirtualScroll.ts`

**Qwen Code 现状**：无虚拟滚动——所有消息全量渲染。

**Qwen Code 修改方向**：仅渲染可视区域 ± buffer 的消息节点。

**实现成本评估**：~3 文件，~300 行，~3 天。难点：滚动位置精确计算（消息高度不等）。

**意义**：1000+ 轮长会话不卡顿。
**缺失后果**：长会话滚动帧率下降。
**改进收益**：O(visible) 渲染替代 O(total)。

---

<a id="item-2"></a>

### 2. Feedback Survey 用户反馈调查（P3）

**问题**：产品改进需要用户反馈，但没有内置收集机制——用户只能去 GitHub 提 issue。

**Claude Code 源码索引**：`commands/feedback/feedback.tsx`、`components/FeedbackSurvey/`

**Qwen Code 现状**：无内置反馈机制。

**Qwen Code 修改方向**：新增 `/feedback` 命令，展示评分 + 文字反馈表单，提交到后端 API。

**实现成本评估**：~3 文件，~200 行，~2 天。

**意义**：直接从用户处收集结构化反馈。
**缺失后果**：只有 power user 会去 GitHub 提 issue——沉默的大多数无法反馈。
**改进收益**：内置反馈 = 降低反馈门槛 → 收集更多改进意见。

---

<a id="item-3"></a>

### 3. Turn Diffs 轮次差异统计（P3）

**问题**：Agent 执行了多轮编辑后，用户想看"这一轮改了什么"的汇总——而非逐个文件查看 diff。

**Claude Code 源码索引**：`utils/gitDiff.ts`、`components/diff/DiffDialog.tsx`

**Qwen Code 现状**：有 per-file diff 展示，但无按轮次汇总的差异统计（哪些文件改了、增删多少行）。

**Qwen Code 修改方向**：每轮工具执行后用 `git diff --numstat` 生成变更统计，展示在轮次结束时。

**实现成本评估**：~2 文件，~100 行，~1 天。

**意义**：每轮变更一目了然——快速审查 Agent 做了什么。
**缺失后果**：需要逐个文件查看 diff → 大变更时容易遗漏。
**改进收益**：轮次统计 = "改了 5 个文件，+120/-30 行" → 快速评估变更规模。

---

<a id="item-4"></a>

### 4. LogoV2 品牌标识与启动动画（P3）

**问题**：CLI 启动时只显示版本号——缺少品牌辨识度和功能引导。

**Claude Code 源码索引**：`components/LogoV2/`

**Qwen Code 现状**：启动显示基础文本信息。

**Qwen Code 修改方向**：设计 ASCII art logo + 启动时显示"新功能提示"（如"试试 /plan 命令"）。

**实现成本评估**：~2 文件，~100 行，~0.5 天。

**意义**：品牌辨识 + 功能引导——低成本高感知。
**缺失后果**：纯文本启动 → 缺少品牌感 → 新用户不知道有什么功能。
**改进收益**：Logo + tips = 品牌辨识 + 功能发现率提升。

---

<a id="item-5"></a>

### 5. Buddy 伴侣精灵系统（P3）

**问题**：Agent 在后台执行长任务时，用户不知道它在做什么——只有 spinner 转圈。缺少一个"可见的助手"让交互更有温度。

**Claude Code 源码索引**：`buddy/companion.ts`、`buddy/CompanionSprite.tsx`、`buddy/useBuddyNotification.tsx`

**Qwen Code 现状**：无 Buddy/Companion 概念。

**Qwen Code 修改方向**：可选的伴侣精灵——在空闲时展示提示、执行时显示状态动画、完成时播放反馈。通过 `feature('BUDDY')` 门控。

**实现成本评估**：~4 文件，~300 行，~3 天。难点：动画不干扰正常输出。

**意义**：交互温度——让 CLI 从"冷冰冰的工具"变成"有温度的助手"。
**缺失后果**：纯文本界面 → 长时间等待无反馈 → 用户焦虑。
**改进收益**：伴侣精灵 = 状态可视 + 空闲引导 + 情感连接。

---

<a id="item-6"></a>

### 6. useMoreRight 右面板扩展（P3）

**问题**：终端宽度有限，Agent 输出和用户输入共用同一列。想同时看文件内容和 Agent 回复，只能开两个终端窗口。

**Claude Code 源码索引**：`moreright/useMoreRight.tsx`

**Qwen Code 现状**：单列布局，无侧面板概念。

**Qwen Code 修改方向**：在支持宽终端的环境中，右侧面板展示文件预览/diff/任务列表——主区域保持对话。

**实现成本评估**：~3 文件，~300 行，~3 天。难点：终端宽度检测 + 响应式布局。

**意义**：信息密度提升——同时看对话和文件内容。
**缺失后果**：单列 → 频繁切换上下文 → 效率低。
**改进收益**：右面板 = 对话 + 预览并排 → 无需切换窗口。

---

<a id="item-7"></a>

### 7. iTerm/Apple Terminal 状态备份与恢复（P3）

**问题**：Agent 运行时接管了终端（alt-screen、鼠标追踪、键盘模式等）。如果异常退出（OOM/SIGKILL），终端状态残留——光标消失、鼠标滚轮失效、键盘回显丢失。用户只能输入 `reset` 修复。

**Claude Code 源码索引**：`utils/gracefulShutdown.ts` 中的 `cleanupTerminalModes()` 同步恢复 + iTerm2/Apple Terminal 特有的状态保存/恢复序列。

**Qwen Code 现状**：`process.on('exit')` 中有基础清理，但无 iTerm2/Apple Terminal 特有的状态备份机制。

**Qwen Code 修改方向**：① 启动时保存终端状态快照（iTerm2 用 DECSC/DECRC，Apple Terminal 用 CSI 序列）；② 退出时（包括 SIGINT/SIGTERM）同步恢复；③ 异常退出后下次启动时检测并修复残留状态。

**实现成本评估**：~2 文件，~100 行，~1 天。难点：不同终端模拟器的转义序列差异。

**意义**：终端状态是用户工作环境的一部分——Agent 不应破坏它。
**缺失后果**：异常退出 → 终端状态残留 → 用户需手动 `reset`。
**改进收益**：状态备份/恢复 = 无论如何退出，终端始终健康。

---

<a id="item-8"></a>

### 8. 设置同步服务 settingsSync（P3）

**问题**：用户在多台机器上使用 Agent（公司电脑 + 家里笔记本），每台都要重新配置主题/模型/权限/快捷键。没有跨设备设置同步机制。

**Claude Code 源码索引**：`services/settingsSync/`（index.ts + types.ts）

**Qwen Code 现状**：设置存储在本地 `~/.qwen/` 目录，无跨设备同步。

**Qwen Code 修改方向**：① 设置序列化为 JSON + 版本号；② 可选同步到云端（DashScope 账号关联）或 git repo；③ 冲突合并策略（时间戳优先或手动选择）。

**实现成本评估**：~4 文件，~300 行，~3 天。难点：设置合并冲突解决。

**意义**：多设备用户体验一致。
**缺失后果**：每台机器重新配置 → 体验不一致。
**改进收益**：设置同步 = 任何设备拿起即用。

---

<a id="item-9"></a>

### 9. Auto Mode 子命令管理（P3）

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
