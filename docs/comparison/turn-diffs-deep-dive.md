# Qwen Code 改进建议 — 轮次差异统计 (Turn Diffs Summary)

> 核心洞察：AI Agent 的一个显著特征是“全自动连招”。在一个复杂的指令（如“重构此目录的路由逻辑”）下，大模型可能会自己闷头探索、连续调用数十次 `read_file` 和 `replace`，修改散落在多个子文件夹中的 8 个不同文件。当 Agent 停下来宣布“任务完成”时，开发者往往一脸茫然：“你到底背着我改了什么？”。虽然有零散的文件级 Diff，但缺乏全局观。Claude Code 利用 Git 引擎的 `--numstat` 机制，在每一轮回合结束时向开发者呈上一份极其清晰、汇总式的“轮次增删统计（Turn Diffs）”；而 Qwen Code 目前只能让开发者自己敲 `git status` 去查验。
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md)

## 一、黑盒修改带来的信任危机

### 1. Qwen Code 的现状：碎片化的差异日志
虽然 Qwen Code 在调用特定工具（如 Edit）时会打印出当前文件的替换情况，但它缺乏**聚合视野 (Aggregated View)**。
- **痛点**：当大模型在一个回合（Turn，从用户敲下命令到模型完全停机）内大刀阔斧地改了前端样式、后端的 DTO 定义以及两张测试表时，屏幕上滑过了上百行的零碎日志。用户极度缺乏安全感，不得不另开一个终端窗口跑一遍 `git diff --stat` 才能确信大模型没有不小心删掉核心文件。

### 2. Claude Code 解决方案：回合终点的战报
在 Claude Code 的 `utils/gitDiff.ts` 及终端的 `DiffDialog` 体系中，它实现了一个无缝的结算机制。

#### 机制一：回合级的差异快照
大模型开始执行前，系统会隐式标记当前的 Git HEAD 或者建立一个暂存锚点。
当这轮回合（可能包含了 5 步自主推演和代码修改）终于结束后，系统会静默执行类似 `git diff --numstat` 的轻量操作。

#### 机制二：直观的统计组件
它会将计算结果（提取 `linesAdded` 和 `linesRemoved`）转换成一个美观的、带有红绿底色的总结块：
```text
✨ Task Complete!
Changes made in this turn:
  + 42 lines, - 15 lines across 3 files.
  > src/auth/login.tsx    +20 -2
  > src/auth/utils.ts     +22 -0
  > tests/login.spec.ts   +0  -13
```
开发者只需瞥一眼这块小面板，就能瞬间评估大模型这顿操作的影响范围（Blast Radius），从而决定是直接打出 `/commit`，还是进行仔细的人工 Review。

## 二、Qwen Code 的改进路径 (P3 优先级)

给“自动化黑盒”增加一扇高透明度的防盗窗。

### 阶段 1：开发 Diff 统计收集器
1. 在 `packages/core/src/utils/` 下新增 `turnDiffStats.ts`。
2. 封装子进程调用 `git diff --numstat`，并解析其输出（因为 numstat 极其轻量且解析稳定）。如果仓库未受 Git 追踪，可以先优雅退化为不显示。

### 阶段 2：挂载回合生命周期
1. 拦截 `agent-core.ts` 中的 `ROUND_END` 或者用户级流转的 `TURN_COMPLETE` 事件。
2. 在大模型输出最终答复之前，或者紧随最终答复之后，调用统计收集器。

### 阶段 3：TUI 组件渲染
在 React Ink 渲染层开发一个极简的 `<TurnSummary />` 组件，利用 ANSI 转义符渲染出带有 `+` 绿色和 `-` 红色的简明表格，追加在消息列表的末尾。

## 三、改进收益评估
- **实现成本**：低。无需复杂的 AST 分析，借助成熟的 Git CLI 能力，几十行代码就能拿到极高价值的统计数据。
- **直接收益**：
  1. **极 致 的 掌 控 感**：大幅降低开发者对 Agent 自主乱改代码的恐慌，建立长期的机器信任。
  2. **审查效率飙升**：用户不再需要手动切出终端跑差异命令，所有决策依据（改了哪些文件，改了多大面积）均直接呈现于眼前。