# Qwen Code 改进建议 — Agent 工具细粒度访问控制 (Fine-grained Tool Access Control)

> 核心洞察：随着智能体系统（Agent System）支持后台执行（Async Agents）和多智能体协同（In-process Teammates），并非所有 Agent 都应该拥有相同的工具权限。如果后台执行的“只读代码探索” Agent 能够调用 `AskUserQuestionTool`，它将永远阻塞并在后台挂起等待用户回复；如果它能调用 `ExitPlanModeTool`，甚至会意外破坏主流程的状态机。Claude Code 实现了多层、白名单与黑名单组合的细粒度工具权限控制；而 Qwen Code 目前只能做到“全量赋予”或粗粒度的硬编码列表。
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md)

## 一、为什么需要多层工具访问控制？

在单体（Single Agent）架构下，主干交互 Agent 拥有全部工具权限是没有问题的。但是一旦引入后台子代理（Subagent）或多 Agent 协作网络（Swarm），权限隔离就变得生死攸关。

**Qwen Code 现状与潜在风险**：
假设你想衍生一个子 Agent 在后台自动整理和归纳过去一周的代码修改。
在当前架构下，如果它获得了所有的基础工具：
1. **死锁风险**：它错误地调用了 `ask_user` 或 `agent_tool` (尝试再衍生子 Agent)，会导致后台任务挂起或递归爆炸。
2. **状态越权**：它调用了 `exit_plan_mode`，破坏了当前主进程（Coordinator）原本的阶段控制逻辑。
3. **破坏最小权限原则**：本来只用搜索（grep）的 Agent，被赋予了修改文件（edit/write）或跑高危命令（shell）的能力。

## 二、Claude Code 的解决方案：三层门控 (Triple-Gate Control)

Claude Code 在 `constants/tools.ts` 中精心设计了三层基于集合（Sets）的隔离墙。这决定了在运行时，底层 `filterToolsForAgent` 函数会给 Agent 装配何种能力：

### 第一层：全局禁止名单 (ALL_AGENT_DISALLOWED_TOOLS)
这是不可逾越的红线。任何脱离主交互循环被独立 `spawn` 出来运行的 Agent（不论前后台），都**绝对禁止**使用这些工具：
- `TaskOutputTool`：它只能由调度主脑使用。
- `ExitPlanModeTool` / `EnterPlanModeTool`：状态机专有。
- `AskUserQuestionTool`：交互界面专有（后台无标准输入）。
- `AgentTool` (spawn subagent)：防止产生失控的递归子代理。

### 第二层：异步白名单 (ASYNC_AGENT_ALLOWED_TOOLS)
对于普通的后台异步任务，它实行的是**白名单制（Allowlist）**，只允许严格安全的、用于完成基本开发闭环的工具集：
- `FileReadTool`, `WebSearchTool`, `GrepTool`, `GlobTool` (只读搜集)
- `FileEditTool`, `FileWriteTool`, `BashTool` (操作执行)

### 第三层：同进程协作增权 (IN_PROCESS_TEAMMATE_ALLOWED_TOOLS)
当后台 Agent 不是一个孤独的异步任务，而是通过 `AsyncLocalStorage` 拉起的“同进程协作队友 (Teammate)”时，它需要与其他 Agent 交流或分配任务。系统会为它**额外开放**特定协同工具：
- `TaskCreateTool`, `TaskGetTool`, `TaskListTool`, `TaskUpdateTool` (操作共享任务树)
- `SendMessageTool` (向调度主脑或其他队友发消息)

不仅如此，Claude Code 还支持在 Agent 的配置文件（Frontmatter）中使用 `tools:` 列表手动缩小权限，或使用 `disallowedTools:` 显式排除某工具，实现了动态与静态结合的极强可配性。

## 三、Qwen Code 的改进路径 (P1 优先级)

为了迎接真正安全的多 Agent 协作时代，Qwen Code 必须重写其工具下发逻辑。

### 阶段 1：定义常量约束层
1. 新建 `packages/core/src/tools/toolAccessPolicies.ts`。
2. 定义三个不可变的权限集：`GLOBAL_DISALLOWED_TOOLS`, `BACKGROUND_AGENT_ALLOWLIST`, `SWARM_AGENT_ALLOWLIST_EXTENSION`。

### 阶段 2：改造动态装配逻辑
1. 在 `agent-core.ts` 初始化 `toolsList` 的阶段，引入一个类似 `filterToolsForAgent(agentConfig)` 的流水线：
   ```typescript
   let availableTools = allRegisteredTools;
   
   // 如果是后台 Agent，仅保留在 白名单 中的工具
   if (agentConfig.isBackground) {
       availableTools = availableTools.filter(t => BACKGROUND_AGENT_ALLOWLIST.has(t.name));
   }
   
   // 全局剔除绝对禁止的工具
   availableTools = availableTools.filter(t => !GLOBAL_DISALLOWED_TOOLS.has(t.name));
   
   // 叠加自定义配置排除 (Denylist)
   if (agentConfig.disallowedTools) {
       availableTools = availableTools.filter(t => !agentConfig.disallowedTools.includes(t.name));
   }
   ```

### 阶段 3：工具层感知 (Context-Aware Tools)
1. 对于特定的交互工具（比如 `ask_user` 工具本身），它可以在其内部 `execute` 时，额外检查 `getCurrentAgentContext().role`，如果发现是后台角色则直接抛错，提供双保险。

## 四、改进收益评估
- **实现成本**：低。无需引入新的库，只需要理顺工具注册表的分发逻辑，几百行代码即可实现。
- **直接收益**：
  1. **避免后台假死**：根绝了后台异步代理滥用交互工具导致任务卡住的问题。
  2. **多 Agent 状态解耦**：彻底分清“调度者（Manager）”与“执行者（Worker）”的工具边界。
  3. **增强防御编程**：对开发者暴露了更清晰、更最小权限的插件/Agent 定义 Schema（通过开放 `disallowedTools`）。