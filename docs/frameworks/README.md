# Agent Framework 对比（开发者侧）

> 这一章节对比的是"**用来构建 Agent 的 SDK / Framework**"，与 [`docs/tools/`](../tools/) 中"**19 款 Code Agent（用户侧）**"完全不同：前者是开发者写 Python 代码来构建自己的 Agent，后者是终端用户直接运行的编程助手。
>
> **类比**：`docs/tools/` ≈ VS Code / Cursor，`docs/frameworks/` ≈ React / Vue。

## 为什么分开？

codeagents 项目最初聚焦在 **Code Agent** 对比（Claude Code / Qwen Code / Codex CLI 等——都是**终端编程助手**）。但 2026 年以来，开发者也有**"自己构建 agent"**的需求——这时候要选的不是 Claude Code，而是 **LangGraph / AgentScope / CrewAI** 这类 SDK。

两者解决不同问题，对比维度也不同：

| 维度 | Code Agent（`docs/tools/`） | Agent Framework（本章节） |
|---|---|---|
| **用户** | 开发者直接运行 | 开发者写代码调用 |
| **交付形态** | CLI 二进制 / IDE 扩展 | Python / TypeScript 包 |
| **安装** | `npm install -g @xxx/xxx` | `pip install xxx` |
| **使用方式** | `qwen-code` 启动 REPL | `from xxx import Agent; agent = Agent(...)` |
| **关注点** | 命令、工具、UX、沙箱 | 抽象、可扩展性、生态、调优 |
| **典型代表** | Claude Code、Qwen Code、Codex CLI | LangGraph、AgentScope、CrewAI |

## 覆盖的 Framework（6 款）

| Framework | 开发者 | 许可证 | 语言 | Stars | 本地源码 | 文档状态 |
|---|---|---|---|---|---|---|
| **[AgentScope](./agentscope/)** | 阿里 SysML Lab | Apache-2.0 | Python | 23.7k | ✓ `/root/git/agentscope/` | **源码级 deep-dive** |
| [LangGraph](./langgraph.md) | LangChain | MIT | Python/TS | — | ✗ | 文档级概述 |
| [CrewAI](./crewai.md) | CrewAI Inc | MIT | Python | — | ✗ | 文档级概述 |
| [AG2 (AutoGen)](./ag2.md) | AG2 社区 | Apache-2.0 | Python | — | ✗ | 文档级概述 |
| [Microsoft Agent Framework](./microsoft-agent-framework.md) | 微软 | MIT | C#/Python | — | ✗ | 文档级概述 |
| [LangChain](./langchain.md) | LangChain | MIT | Python/TS | — | ✗ | 文档级概述 |

> **为什么 AgentScope 深度更高？** 因为它是 codeagents 项目目前唯一本地有完整源码（`/root/git/agentscope/`，215 文件 / 43,574 行）的 framework，可以做源码级 EVIDENCE 引用。其他 5 款基于官方文档和 README 概述，深度较浅。未来若获得源码可逐个升级到 deep-dive。

## 横向对比矩阵

见 [`comparison.md`](./comparison.md) —— 按功能维度对比 6 款 framework。

## 如何选择？

详细选型指南见 [`../guides/build-your-own-agent.md`](../guides/build-your-own-agent.md)。

**一句话决策树**：

```
你的目标是什么？

├── 多 Agent 编排 + 状态管理     → LangGraph（状态图）
├── Role-based Team 协作          → CrewAI
├── Conversation-based 多 Agent    → AG2 (AutoGen)
├── 微软 .NET 生态 / 企业集成     → Microsoft Agent Framework
├── 完整生态 + OTel + 国内云      → AgentScope（阿里，有 A2A + MCP + 微调）
└── 通用 LLM 管线 + 大量 Provider  → LangChain
```

## 与 Code Agent 的关系

有些 Code Agent 内部**使用了** Framework：

- **OpenHands** 用自研 EventStream 架构（类似 LangGraph 的状态图）
- **SWE-agent** 用自研 ACI 框架
- **Claude Code / Qwen Code / Codex CLI** 都是**自研**（没用第三方 framework）

这说明：**成熟的 Code Agent 倾向于自研底层**（为了性能、定制、UX 控制），而 Framework 的用户是"**想构建自己 agent 的开发者**"——这两个人群**几乎不重叠**。

因此本章节的主要读者是：

- 想**自己开发 AI Agent 产品**的工程师
- 想为 **Claude Code / Qwen Code 之外的场景构建专用 agent** 的团队
- 研究 agent 架构设计的学术/工业研究者

## 下一步

- 看 AgentScope 的技术细节 → [`agentscope/`](./agentscope/)
- 看 6 款 framework 横向对比 → [`comparison.md`](./comparison.md)
- 看如何从零构建 agent → [`../guides/build-your-own-agent.md`](../guides/build-your-own-agent.md)
