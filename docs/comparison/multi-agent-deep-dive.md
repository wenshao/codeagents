# 30. 子代理与多代理架构深度对比

> 从"单代理做一切"到"多代理分工协作"，AI 编程代理正在从个体工具进化为代理团队。

## 总览

| 工具 | 多代理模式 | 内置代理数 | 并行能力 | 委托方式 | 独特设计 |
|------|-----------|-----------|---------|---------|---------|
| **Claude Code** | Teammates 协作 | 子代理按需 | ✓（worktree + tmux） | Agent 工具 | **AI-AI 团队分工** |
| **Gemini CLI** | 5 内置子代理 | **5** | ✓ | AgentRegistry | **A2A 远程代理** |
| **Copilot CLI** | 3 内置代理 | **3** | — | YAML 定义 | **"$20 in jeans" 审查标准** |
| **Qwen Code** | Arena 竞争 | 继承 + Arena | ✓（Tmux/iTerm2） | ArenaManager | **多模型竞争选优** |
| **Kimi CLI** | 5 代理类型 | **5** | ✓（前台/后台） | Wire 协议 | **D-Mail 时间回溯** |
| **OpenHands** | 4 复合代理 | **4** | ✓ | AgentDelegate | **EventStream 解耦** |
| **Aider** | 双模型流水线 | 1（双阶段） | — | 内部委托 | **架构师→编辑器** |
| **Codex CLI** | Guardian 审批 | 实验性 | — | 功能标志 | **安全审查子代理** |
| **Goose** | MCP 工具委托 | — | — | Recipe | **纯 MCP 工作流** |

---

## 一、Claude Code：Teammates 团队协作

> 来源：02-commands.md（/agents 命令）、二进制分析

### Teammates 架构

```
Leader Agent（主终端）
  │
  ├── claude --teammates "reviewer:审查 PR" "implementer:修复 Bug"
  │
  ├── Teammate 1（tmux pane / iTerm2 tab）
  │   ├── 独立 Git worktree
  │   ├── 可分配不同模型和角色
  │   └── 独立工具集和上下文
  │
  └── Teammate 2（tmux pane / iTerm2 tab）
      ├── 独立 Git worktree
      └── 独立上下文
```

### Agent 工具（子代理）

```typescript
// 子代理启动参数
{
  prompt: "分析这个模块的性能瓶颈",
  model: "haiku",        // 可指定不同模型
  isolation: "worktree"  // 可选 worktree 隔离
}
```

- 子代理继承父代理工具集，但有独立对话历史
- TaskCreate/TaskGet/TaskList/TaskUpdate 支持后台并行任务
- EnterWorktree/ExitWorktree 支持动态 Git worktree 切换

### /review 插件的多代理编排

```
Step 1: 前置检查（Haiku）
Step 2: 收集 CLAUDE.md（Haiku）
Step 3: 变更摘要（Sonnet）
Step 4: 并行审查（4 代理同时启动）
  ├── Agent 1-2（Sonnet）：CLAUDE.md 合规审计
  ├── Agent 3（Opus）：Bug 扫描
  └── Agent 4（Opus）：安全/逻辑分析
Step 5: 并行验证（子代理确认每个问题）
Step 6-9: 过滤 → 输出 → PR 评论
```

---

## 二、Gemini CLI：5 内置子代理 + A2A 远程

> 源码：`packages/core/src/agents/`，AgentRegistry

### 5 个内置子代理

| 子代理 | 工具权限 | 模型 | 轮次/超时 | 条件 |
|--------|---------|------|----------|------|
| **generalist** | 全部工具 | 继承主模型 | 20 轮 / 10 分钟 | 始终注册 |
| **codebase_investigator** | 只读（glob/grep/ls/read_file） | Flash | 10 轮 / 3 分钟 | 始终注册 |
| **memory_manager** | 读写 GEMINI.md | Flash | 10 轮 / 5 分钟 | 需设置启用 |
| **cli_help** | 内部文档查询 | Flash | 10 轮 / 3 分钟 | 始终注册 |
| **browser** | Puppeteer Web 自动化 | Flash | 50 轮 / 10 分钟 | 需设置启用 |

### 子代理终止模式

`GOAL`（完成目标）、`MAX_TURNS`（达到轮次上限）、`TIMEOUT`（超时）、`ERROR`（错误）、`ABORTED`（中止）、`ERROR_NO_COMPLETE_TASK_CALL`

### A2A 远程代理（v0.33.0+）

```markdown
<!-- .gemini/agents/remote-reviewer.md -->
---
name: remote-reviewer
agentCardUrl: https://reviewer.example.com/.well-known/agent.json
---
远程代码审查代理，通过 A2A 协议通信。
```

- `@a2a` 工具允许模型向远程 Agent 发送消息
- HTTP 认证 + Agent Card 自动发现
- A2A 协议 v0.3（gRPC、安全签名）

---

## 三、Copilot CLI：3 内置代理（YAML 定义）

> 来源：03-architecture.md、EVIDENCE.md

### 三个专用代理

| 代理 | 模型 | 工具权限 | 核心职责 |
|------|------|---------|---------|
| **code-review** | Claude Sonnet 4.5 | `["*"]`（全部工具） | 8 维度审查 + 可编译运行测试 |
| **explore** | Claude Haiku 4.5 | 仅 grep/glob/view/lsp | 只读代码探索，300 字符限制 |
| **task** | Claude Haiku 4.5 | `["*"]`（全部工具） | 后台任务执行，最小输出 |

### code-review 代理审查标准

Prompt 中的核心指令：

> "Finding a review feedback should feel like finding a $20 bill in the pocket of jeans you are about to throw in the washing machine."

8 个审查维度：bugs、security、race conditions、memory leaks、error handling、assumptions、breaking changes、performance。

**明确排除假阳性**：代码风格、格式化、主观建议一律不报。

---

## 四、Qwen Code：Arena 竞争模式

> 来源：EVIDENCE.md（ArenaManager.ts）

### Arena 架构

```
用户任务
  │
  ArenaManager
  ├── Agent 1（Model A）── 独立 Git worktree ── iTerm2 pane
  ├── Agent 2（Model B）── 独立 Git worktree ── Tmux pane
  └── Agent 3（Model C）── 独立 Git worktree ── InProcess
  │
  所有完成后 → 用户选择最佳方案
```

### 终端后端

| 后端 | 适用 | 特点 |
|------|------|------|
| iTerm2 | macOS | 原生分屏 |
| Tmux | Linux/macOS | 通用 |
| InProcess | 所有平台 | 无 UI，纯后台 |

### Arena vs Teammates

| 维度 | Qwen Arena | Claude Teammates |
|------|-----------|-----------------|
| 模式 | **竞争**（选最优） | **协作**（分工） |
| 任务 | 同一任务多模型执行 | 不同子任务分配 |
| 模型 | 必须不同 | 可以相同或不同 |
| 输出 | 用户选择胜者 | 合并所有结果 |

---

## 五、Kimi CLI：5 代理类型 + D-Mail

> 源码：`soul/slash.py`、Wire v1.6 协议

### 5 种代理类型

| 类型 | 工具权限 | 用途 |
|------|---------|------|
| **default** | 全部 | 主代理 |
| **coder** | 读/写/执行 | 软件工程任务 |
| **explore** | 只读 | 代码探索 |
| **plan** | 纯分析（无 shell） | 架构规划 |
| **okabe** | 全部 + SendDMail | 实验性时间回溯 |

### Agent 工具委托

```python
# 参数
description: str       # 任务描述
prompt: str            # 详细提示
subagent_type: str     # 代理类型
model: str             # 可选模型覆盖
run_in_background: bool  # 前台/后台
```

- 前台代理：等待结果后返回
- 后台代理：立即返回，通过 `agent_id` 后续查询
- 会话持久化：通过 `agent_id` 恢复

### D-Mail（时间回溯，实验性）

`okabe` 代理中的 `SendDMail` 工具，向过去检查点发送消息，回滚上下文。灵感来自 Steins;Gate 的 D-Mail 概念。

---

## 六、OpenHands：4 复合代理 + EventStream

> 来源：openhands.md

### 4 种代理

| 代理 | 核心能力 |
|------|---------|
| **CodeAct** | 主代理，代码执行 |
| **BrowsingAgent** | 文本 Web 导航 |
| **VisualBrowsingAgent** | 视觉 Web（Playwright + BrowserGym + SOM） |
| **ReadOnlyAgent** | 只读分析 |

### AgentDelegate 委托

```
CodeAct
  ├── 代码任务 → 直接执行
  ├── Web 任务 → AgentDelegate → BrowsingAgent
  └── 分析任务 → AgentDelegate → ReadOnlyAgent
```

### EventStream 架构

```
Action → EventStream（发布/订阅总线）→ Runtime → Observation → 订阅者通知
```

完全解耦的事件模型，支持异步多代理协作。

---

## 七、Aider：双模型流水线（非多代理）

> 源码：`aider/coders/architect_coder.py`

```
用户请求 → [架构师模型（主模型）] → 生成方案（自然语言）
                    ↓
             [编辑器模型] → 执行修改（diff）
```

- `ArchitectCoder` 继承自 `AskCoder`（只读）
- 编辑器 Coder 的 `map_tokens=0`（不重复加载仓库地图）
- 不是真正的多代理，而是**同一代理内的双模型管道**

---

## 设计模式对比

### 协作 vs 竞争 vs 委托

| 模式 | 代表 | 优势 | 劣势 |
|------|------|------|------|
| **协作分工** | Claude Teammates | 任务并行，效率高 | 协调复杂 |
| **竞争选优** | Qwen Arena | 多视角，质量高 | 资源浪费（N 倍成本） |
| **专用委托** | Gemini 5 子代理 | 职责清晰，资源可控 | 灵活性有限 |
| **事件解耦** | OpenHands EventStream | 最灵活，异步 | 架构最复杂 |
| **流水线** | Aider Architect | 简单高效 | 非并行 |

### 隔离策略

| 工具 | 隔离方式 | 上下文共享 |
|------|---------|-----------|
| Claude Code | Git worktree | 独立上下文 |
| Qwen Code | Git worktree（Arena） | 独立上下文 |
| Gemini CLI | AgentSession | 独立上下文 + 轮次限制 |
| Kimi CLI | Wire 协议 | 独立上下文 + 会话持久化 |
| OpenHands | Docker/K8s | EventStream 共享 |

---

## 证据来源

| 工具 | 来源 | 获取方式 |
|------|------|---------|
| Claude Code | 02-commands.md + 05-skills.md | 二进制分析 |
| Gemini CLI | 04-tools.md + 03-architecture.md | 开源 |
| Copilot CLI | 03-architecture.md + EVIDENCE.md | SEA 反编译 |
| Qwen Code | EVIDENCE.md（ArenaManager.ts） | 开源 |
| Kimi CLI | 03-architecture.md + EVIDENCE.md | 开源 |
| OpenHands | openhands.md | 开源 |
| Aider | 03-architecture.md | 开源 |
