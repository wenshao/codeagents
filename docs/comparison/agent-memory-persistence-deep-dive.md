# Qwen Code 改进建议 — Agent 记忆持久化 (Agent Memory Persistence)

> 核心洞察：当开发者在复杂项目中多次调用特定的代码助手（比如一个被配置为 `Code Reviewer` 或 `DB Expert` 的特定子 Agent）时，往往需要一遍遍地告诉它：“本项目缩进为 4 空格”、“不要使用 any”、“数据库用的是 Postgres 不是 MySQL”。一旦终端会话结束，Agent 刚刚学到的宝贵经验瞬间灰飞烟灭。Claude Code 为衍生 Agent 独创了 3 级（User / Project / Local）分离式持久化记忆体系，让 Agent 拥有了跨会话的记忆进化能力；而 Qwen Code 目前所有的 Agent 每次启动均是“失忆”状态。
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md)

## 一、为什么 Agent 会“反复失忆”？

### 1. Qwen Code 现状：短暂的上下文生命周期
Qwen Code 的所有上下文状态（除了用户硬编码的 System Prompt 字符串外）都只存在于当前的 `Session` 内存或长对话历史中。
- **痛点**：对于通用 Agent，你可以每次手动传入一条长长的 Prompt。但如果你创建了十个特定职能的 Agent，它们在执行不同任务时踩了坑（比如发现某个库的版本不兼容，或者某种编译参数在这个项目跑不通），这些用 Token 和时间换来的血泪教训，在 `AgentTerminateMode.SUCCESS` 后就被丢弃了。

### 2. Claude Code 解决方案：3 级独立挂载体系
在 Claude Code 的 `tools/AgentTool/agentMemory.ts` 中，为 Agent 引入了独立于核心历史文件的“独立脑区”。

如果在创建一个 Agent 时，在它的配置中指定了 `memory` 级别，系统会自动在磁盘上为它开辟存储区，并默认为它**授权一组针对该存储区的 Read/Write/Edit 工具**，让大模型可以通过操作工具自己写笔记！

#### 级别 1：User Memory (全局通用)
存储在操作系统的 Home 目录下（例如 `~/.claude/agent-memory/[agent-id].md`）。
Agent 在任何项目下启动，都会自动包含这份记忆。适合记录开发者个人的通用偏好。

#### 级别 2：Project Memory (项目通用)
存储在项目代码库中（例如 `.claude/agent-memory/[agent-id].md`）。
设计用于团队共享。这部分记忆会被提交进 `git` 仓库。比如“前端代码审查 Agent”在里面记下了整个团队约定的 React Hooks 闭坑指南，所有 pull 代码的新人都能直接享受到一个“老练”的 Agent。

#### 级别 3：Local Memory (项目私有)
存储在项目的忽略目录下（例如 `.claude/agent-memory-local/`），并自动加入 `.gitignore`。
用于记录只针对当前环境的机器差异（比如这个开发者的本地 MySQL 端口是 3307）。

## 二、Qwen Code 的改进路径 (P1 优先级)

赋予多 Agent 真正自我进化的知识积累能力。

### 阶段 1：设计 Memory 层级与生命周期
1. 在 `packages/core/src/agents/` 下新增 `agentMemoryService.ts`。
2. 定义 3 级路径解析逻辑，根据当前执行的 `agentId` (如果是子代理) 或者是 `Main` (主交互代理)，定位到对应的三个 `.md` 记忆文件。

### 阶段 2：系统提示注入 (Context Injection)
在 `agent-core.ts` 组装 System Prompt 时：
1. 提取上述 3 级文件内容。
2. 附加一段明确的系统指令：
   > "Here are your persisted memories from previous sessions. These are critical rules and past learnings. You MUST abide by them."
3. （为节省 Token，可配合 Token Budget 拦截，截断超过 4KB 的部分）。

### 阶段 3：赋予 Agent 自我编辑能力
针对带有记忆能力启动的 Agent，向它的工具列表中动态注入一套“记忆读写微型工具集”：
- `WriteMemoryTool`: 追加一行新学习到的规则。
- `EditMemoryTool`: 清除或修改过时的规则。
这样大模型就能在执行任务结束前（或者发现踩坑时），自己把知识沉淀到硬盘中，留给明天的自己！

## 三、改进收益评估
- **实现成本**：中等。核心是管理文件路径注入，并提供安全受限的配套改写工具。
- **直接收益**：
  1. **复用增效**：彻底消灭“重复调教 AI”的挫败感，极大提升高频用户的黏性。
  2. **知识资产化**：将资深员工在大模型交互中纠正的经验固化到了 `Project Memory` 中，实现代码库与“大模型审查规则库”同生同长。