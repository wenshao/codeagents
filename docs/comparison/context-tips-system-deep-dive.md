# Qwen Code 改进建议 — 上下文 Tips 系统 (Context-Aware Tips System)

> 核心洞察：随着现代 AI CLI Agent 功能的快速膨胀（如支持 `/compress`, `/review`, `QWEN.md` 配置、MCP 挂载），一个很现实的困境出现了：开发者往往只会用最简单的指令跟大模型聊天，大量耗费心血开发的高级极客功能由于没有图形化界面的按钮，完全处于“隐身”状态。传统的做法是让用户自己去看长篇大论的 README，但这反人性。Claude Code 建立了一个隐蔽但极其聪明的 `Tips Registry`（上下文感知提示引擎）。它不烦人，只会在特定的边缘场景（如 Context 快满了、检测到了特定错误时）跳出轻微的“One-liner”建议词；而 Qwen Code 目前完全缺乏这种主动的、基于上下文的“新手引导”机制。
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md)

## 一、被掩埋的黑科技与使用疲劳

### 1. Qwen Code 现状：缺乏发现机制
如果在 Qwen Code 里，大模型的上下文已经被历史会话塞到了 95%（即将触发致命报错或者截断丢档）：
- **痛点一（事后诸葛亮）**：系统通常一言不发，直到最后一根稻草压垮骆驼，直接抛出一个 `Error: Max tokens exceeded`，用户不得不手足无措地新建会话。
- **痛点二（隐藏功能的埋没）**：Qwen Code 可能开发了一个极其强大的基于 Git Diff 的审查命令 `/security-review`，但小白用户根本不知道它的存在。除了硬着头皮啃完 10 页的 Markdown 文档，没有其他途径能让他们在开发中“恰好”被告知这个命令的存在。

### 2. Claude Code 解决方案：恰到好处的“你知道吗？”
在 Claude Code 的 `services/tips/tipRegistry.ts` 中，作者为了让这些极客命令能被“无痛发现”，设计了一套被称为“被动教育（Passive Onboarding）”的柔性系统。

#### 机制一：基于上下文的事件嗅探 (Condition Matching)
Tips 不是完全随机播放的，每个 Tip 在注册表里都带着一段极其严格的触发条件。
例如：
- **Context 预警**：当监视器发现当前对话轮次的 Token 占用突破了 80% 的警戒线时，系统会在下方的状态栏极轻微地弹出一句：`💡 Tip: Your context is getting full. Try running /compress to free up space.`。
- **环境嗅探**：如果在启动时探测到用户环境变量里有 `VSCODE_CWD`（正在用 VS Code 的内置终端跑 Agent），它会恰如其分地推销一句：`💡 Tip: Did you know we have a dedicated VS Code Extension? Run /install-ide to get it.`。

#### 机制二：低噪展示与频率控制 (Frequency Capping)
大厂工具的操守在于“绝不烦人”。
这套系统会在本地的 `.claude/config` 里记录某条 Tip 是否已经被推送过。
如果用户已经看过并使用过了 `/compress`，这条提示将**永远不会再出现**（Marked as seen）。
而且整个界面的渲染极其克制，往往只是用暗色字体（Dim Color）附着在正常输出之后，绝对不会阻断正常命令的输入与执行流。

## 二、Qwen Code 的改进路径 (P2 优先级)

让工具长出一张“智能的新手指引”嘴巴，是突破增长瓶颈的关键。

### 阶段 1：开发全局提示注册表
1. 在 `packages/core/src/services/tips/` 新建 `tipRegistry.ts`。
2. 定义强类型的提示接口，包含：`id`, `message`, `condition()`: boolean, `priority`。
3. 把各种冷门但强大的命令（如未来加入的 `/branch`, `/teleport` 等）写进注册表中。

### 阶段 2：挂钩核心生命周期
在 `agent-core.ts` 或底层的 `geminiChat.ts` 的关键事件点插入触发器：
- `onRoundEnd` (每个推理回合结束时)。
- `onStartup` (初始化首屏渲染完成时)。
遍历注册表，过滤出 `condition() === true` 且未被记录为 `seen` 的最高优先级提示。

### 阶段 3：UI 渲染与持久化记录
1. 抛出选中的 Tip 到 TUI 渲染树，在消息列表最下方用暗色（或带有 `💡` Emoji 的特定样式）打印出该提示。
2. 随后立即调用底层的配置存储（如 `globalConfig.set('tips.seen.compress_cmd', true)`），确保对单个用户不进行骚扰式轰炸。

## 三、改进收益评估
- **实现成本**：小到中等。实现注册表很容易，难点在于挖掘和编写恰到好处的 `condition` 探测逻辑。代码量 300 行左右。
- **直接收益**：
  1. **极 致 的 新 手 上 手 率**：无需冗长的教程，小白也能在潜移默化中被培养为熟练使用各种斜杠（Slash）命令的高端玩家。
  2. **化解边界情况报错**：将硬核的超载报错（如 Token 不够）转化为温和的命令引导，大幅降低了崩溃带来的负面情绪反馈。