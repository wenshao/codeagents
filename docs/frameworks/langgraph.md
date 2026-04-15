# LangGraph

> LangChain 团队的状态图 Agent framework，MIT，Python + TypeScript。

**仓库**：https://github.com/langchain-ai/langgraph
**开发者**：LangChain Inc
**许可证**：MIT
**语言**：Python + TypeScript
**定位**：**"Low-level orchestration framework for building controllable agents"**

## 核心抽象：StateGraph

LangGraph 的核心是 **`StateGraph`** —— 一个有状态的有向图：

- **节点（Node）** = Python 函数，接收 state，返回更新后的 state
- **边（Edge）** = 状态转移规则（常量边 / 条件边）
- **状态（State）** = TypedDict，全局共享

```python
from langgraph.graph import StateGraph, END
from typing_extensions import TypedDict

class AgentState(TypedDict):
    messages: list
    count: int

def agent_node(state: AgentState):
    return {"messages": [...], "count": state["count"] + 1}

def should_continue(state: AgentState):
    return END if state["count"] >= 5 else "agent"

graph = StateGraph(AgentState)
graph.add_node("agent", agent_node)
graph.add_conditional_edges("agent", should_continue)
graph.set_entry_point("agent")
app = graph.compile()
```

## 杀手级特性：Checkpointer

LangGraph 最独特的能力是**可恢复的长流程**：

- `MemorySaver` / `PostgresSaver` / `RedisSaver` / `SqliteSaver`
- 每次状态转移自动保存
- 进程崩溃后可从任意 checkpoint 恢复

这对需要**人类审批 / 长耗时任务 / 容错**的场景极其重要。

## 多 Agent 支持

通过状态图节点实现：

- 每个节点是一个 agent
- 用 `add_conditional_edges` 实现 **supervisor 路由**
- 或用 `Command` 对象让节点主动指定下一个 node

## 与 AgentScope 对比

| 维度 | LangGraph | AgentScope |
|---|---|---|
| 核心抽象 | 状态图（显式） | ReAct loop（显式） |
| 多 Agent | 节点 + 边 | MsgHub 广播 |
| 可恢复 | ✓ Checkpointer | ⚠️ Session 手动 |
| 可视化 | ✓ | ⚠️ Studio |
| 学习曲线 | 陡（需理解状态图） | 平（熟悉 ReAct 即可） |
| 微调支持 | ✗ | ✓ Trinity-RFT |
| 实时语音 | ✗ | ✓ |

## 何时选它

- 需要**可恢复的长流程**（人类审批、日级任务）
- 流程结构**已知且复杂**（绘图清晰）
- 已在 LangChain 生态中

## 何时不选

- 只是想快速搭一个 ReAct agent（过度设计）
- 需要**多语言**（其他 framework 更简单）
- 需要实时语音 / agentic RL / MCP 原生（换 AgentScope）

---

> **注**：本页基于官方文档和 README。本地无源码，无法做 source-level EVIDENCE 引用。如需升级到 deep-dive，可 `git clone https://github.com/langchain-ai/langgraph ~/git/langgraph` 后再做源码级分析。
