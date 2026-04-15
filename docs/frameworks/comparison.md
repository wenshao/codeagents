# Agent Framework 横向对比

> 6 款主流 Agent Framework 的源码/文档级对比。仅 AgentScope 是本地源码级分析，其他 5 款基于官方文档和 README。

## 开发者 / 许可证 / 语言

| Framework | 开发者 | 许可证 | 语言 | 主版本 | 论文 |
|---|---|---|---|---|---|
| **AgentScope** | 阿里 Tongyi Lab | Apache-2.0 | Python ≥3.10 | 0.x | [arXiv:2402.14034](https://arxiv.org/abs/2402.14034) |
| **LangGraph** | LangChain | MIT | Python + TypeScript | 0.2.x | — |
| **CrewAI** | CrewAI Inc | MIT | Python | 0.x | — |
| **AG2 (AutoGen)** | AG2 社区（原 Microsoft AutoGen 分叉） | Apache-2.0 | Python | 0.x | [arXiv:2308.08155](https://arxiv.org/abs/2308.08155) |
| **Microsoft Agent Framework** | Microsoft | MIT | C# + Python | 预览 | — |
| **LangChain** | LangChain | MIT | Python + TypeScript | 0.3.x | — |

## 核心抽象风格

| Framework | 主抽象 | 适合场景 |
|---|---|---|
| **AgentScope** | 显式 ReAct loop + hooks + MsgHub 广播 | 需要细粒度控制 + 生态完整 |
| **LangGraph** | `StateGraph` 状态图 + 节点 + 条件边 | 复杂工作流 + 可视化 + checkpoint |
| **CrewAI** | `Crew` + `Agent (role)` + `Task` + `Process` | Role-based 业务场景 |
| **AG2** | `GroupChat` conversation + Agent 角色 | 模拟对话 + 多 Agent 讨论 |
| **MAF** | `ChatHandler` + `FunctionInvocation` + .NET 生态 | 微软技术栈集成 |
| **LangChain** | `Chain` + `Runnable` + `LCEL` 管道 | LLM 管线 + 大量 provider |

## 主循环模型

| Framework | 主循环结构 | 退出条件 |
|---|---|---|
| **AgentScope** | `for _ in range(max_iters)` 显式循环，`_reasoning()` → `_acting()` | 无 tool_use block |
| **LangGraph** | 状态图遍历，节点返回下一状态 | 到达 `END` 节点 |
| **CrewAI** | Task 依次执行（Sequential / Hierarchical Process） | 所有 task 完成 |
| **AG2** | `GroupChat.run()` 轮询下一发言人 | 终止条件或 `max_round` |
| **MAF** | `ChatHandler.Invoke()` 循环 | 模型输出无 tool call |
| **LangChain** | `AgentExecutor._call()` | `AgentFinish` 输出 |

## 多 Agent 支持

| Framework | 多 Agent 模式 | 特点 |
|---|---|---|
| **AgentScope** | MsgHub 广播 | 简单、灵活、无结构化状态 |
| **LangGraph** | StateGraph 节点 = agent | 强结构、可 checkpoint 恢复 |
| **CrewAI** | Crew + Role 分工 | **业务层面最直观** |
| **AG2** | GroupChat + Selector | 自然对话流 |
| **MAF** | Connected Agents API | 微软风格 |
| **LangChain** | 通过 LangGraph 扩展 | 本体无原生支持 |

## MCP 支持

| Framework | MCP Client | MCP Server | 备注 |
|---|---|---|---|
| **AgentScope** | ✓ 官方 `mcp>=1.13` | ✗ | `tools/_toolkit.py:23` 直接 import mcp |
| **LangGraph** | ✗ 本体无 | ✗ | 需第三方包 |
| **CrewAI** | 通过 `crewai-tools` 插件 | ✗ | |
| **AG2** | ✗ | ✗ | |
| **MAF** | 预览支持 | ✗ | |
| **LangChain** | 通过 `langchain-mcp-adapters` | ✗ | |

## A2A (Agent-to-Agent) 协议

| Framework | A2A 支持 | 实现方式 |
|---|---|---|
| **AgentScope** | ✓ 原生 | 集成官方 `a2a-sdk` + Nacos 服务发现 |
| **LangGraph** | ✗ | 无 |
| **CrewAI** | ✗ | 无 |
| **AG2** | ✗ | 无 |
| **MAF** | 概念提及 | 无源码实现 |
| **LangChain** | ✗ | 无 |

**AgentScope 是 6 款 framework 中唯一原生集成 A2A 的。**

## Memory 系统

| Framework | Working Memory | Long-Term Memory | 后端 |
|---|---|---|---|
| **AgentScope** | ✓ InMemory/Redis/SQLAlchemy/TableStore | ✓ Mem0 + ReMe | **4 种** |
| **LangGraph** | ✓ Checkpointer (Memory / Postgres / Redis / SQLite) | ⚠️ 需自建 | 4 种 |
| **CrewAI** | ✓ ShortTerm / LongTerm / Entity | ✓ mem0 集成 | RAG + SQLite |
| **AG2** | 会话内 | ⚠️ 手工 | — |
| **MAF** | ChatHistory | ⚠️ | 自定义 |
| **LangChain** | `ConversationBufferMemory` 等 | ⚠️ | — |

## 微调 / 学习支持

| Framework | Agentic RL | Fine-tune 接口 |
|---|---|---|
| **AgentScope** | ✓ Trinity-RFT | `tune()` 函数，trajectory 反哺训练 |
| **LangGraph** | ✗ | ✗ |
| **CrewAI** | ✗ | ✗ |
| **AG2** | ✗ | ✗ |
| **MAF** | ✗ | ✗ |
| **LangChain** | ✗ | ✗ |

**AgentScope 独有**。

## 实时语音 Agent

| Framework | Realtime WebSocket | TTS Provider 数 |
|---|---|---|
| **AgentScope** | ✓ OpenAI / DashScope / Gemini Realtime | 4 |
| **LangGraph** | ⚠️ 需自建 | — |
| **CrewAI** | ✗ | — |
| **AG2** | ✗ | — |
| **MAF** | ✗ | — |
| **LangChain** | 通过 LangChain-experimental | — |

**AgentScope 独有**。

## 可观测性 (Tracing)

| Framework | OTel 原生 | Tracing 粒度 |
|---|---|---|
| **AgentScope** | ✓ 5 类 × 3 extractor | Agent / LLM / Tool / Formatter / Embedding |
| **LangGraph** | ✓ LangSmith 集成 | 节点级 |
| **CrewAI** | ✓ Langtrace / OpenLLMetry | Task 级 |
| **AG2** | ⚠️ 手工 | — |
| **MAF** | ✓ Application Insights | — |
| **LangChain** | ✓ LangSmith | Chain 级 |

## Hook / 扩展

| Framework | Hook 类型 | 数量 |
|---|---|---|
| **AgentScope** | Python callable（class + instance level） | 10 个 hook 点（pre/post × reply/print/observe/reasoning/acting） |
| **LangGraph** | `interrupt_before` / `interrupt_after` + checkpointer | 节点级 |
| **CrewAI** | Task callback | 任务级 |
| **AG2** | `register_hook` | 有限 |
| **MAF** | `IFilter` | C# 风格 |
| **LangChain** | `CallbackHandler` | 细粒度 |

## Plan 模块

| Framework | 计划原语 | 实现 |
|---|---|---|
| **AgentScope** | **First-class `PlanNotebook` + `Plan` + `SubTask`** | 源码 `src/agentscope/plan/` |
| **LangGraph** | 隐式（状态图即计划） | — |
| **CrewAI** | `Task` 自动分解（可选） | — |
| **AG2** | ✗ | — |
| **MAF** | ✗ | — |
| **LangChain** | `Plan-and-Execute` experimental | 实验性 |

## 代码规模（估算）

| Framework | 代码量（Python） | 依赖数 |
|---|---|---|
| **AgentScope** | **43K 行 / 215 文件** | 中 |
| **LangGraph** | ~15-20K 行 | 少 |
| **CrewAI** | ~25K 行 | 中 |
| **AG2** | 60-80K 行 | 多 |
| **MAF** | - (C# 为主) | - |
| **LangChain core** | 100K+ 行 | 极多 |

## 生态活跃度（2026-04 观察）

| Framework | GitHub Stars | 增长速度 |
|---|---|---|
| **LangChain** | ~100k+ | 放缓 |
| **LangGraph** | ~10k | 快速增长 |
| **AutoGen/AG2** | ~35k | 稳定（AG2 是 fork） |
| **AgentScope** | 23.7k | 快速增长 |
| **CrewAI** | ~30k | 稳定 |
| **MAF** | 预览中 | — |

## 决策指南：什么时候选哪款？

### 选 **AgentScope**，如果你：
- 想要**完整生态**（MCP + A2A + 微调 + 实时语音）
- 需要 production-grade OTel tracing
- 构建**中文场景 agent**（DashScope + CosyVoice）
- 研究 **agentic RL**（Trinity-RFT）
- 要跨多个 agent 做**松耦合广播**（MsgHub）

### 选 **LangGraph**，如果你：
- 需要**可恢复的长流程**（checkpointer）
- 流程结构**已知且复杂**（可绘图）
- 要做多 agent 编排 + **状态机风格**
- 已经在用 LangChain 生态

### 选 **CrewAI**，如果你：
- 场景是**业务角色分工**（产品 → 设计 → 开发 → 测试）
- 想要**直观的 role-based API**
- 不想写太多底层逻辑

### 选 **AG2 (AutoGen)**，如果你:
- 想做**多 Agent 对话模拟**
- 研究**讨论/辩论**场景
- 需要学术一致性（参考 AutoGen 论文）

### 选 **Microsoft Agent Framework**，如果你:
- 团队是 **.NET / C# 栈**
- 需要 Azure 深度集成
- 在**企业 Azure 环境**部署

### 选 **LangChain**，如果你:
- 需要**最大的 provider 覆盖**
- 构建**简单的 LLM 管道**（非复杂 agent）
- 已有 LangChain 代码库

## 一个都不选的理由

**如果你的目标是构建一个 Code Agent（编程助手）**，这 6 款 framework **都不合适** —— Claude Code / Qwen Code / Codex CLI 都是**自研**的，因为：

1. **UX 要求高**：TUI、流式渲染、快捷键、实时 diff —— framework 提供的抽象无法直接实现
2. **启动速度**：framework 都有几百 ms 的 import 延迟
3. **定制深度**：code agent 需要改 prompt cache 策略、compaction 算法、tool schema —— framework 的抽象是负担
4. **性能**：Rust / Bun 实现比 Python framework 快 10 倍

**结论**：framework 适合**"我要构建一个特定业务场景的 agent"**，不适合**"我要构建下一个 Claude Code"**。

---

## 延伸阅读

- [AgentScope 深度分析](./agentscope/) —— 本章节唯一的源码级 deep-dive
- [构建你自己的 Agent 指南](../guides/build-your-own-agent.md) —— 6 款 framework 的选型建议
- [Code Agent 对比矩阵](../comparison/features.md) —— 19 款用户侧 Code Agent 横向对比
