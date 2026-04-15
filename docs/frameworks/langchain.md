# LangChain

> LLM 应用开发的"**通用工具箱**"，MIT，Python + TypeScript，生态最大。

**仓库**：https://github.com/langchain-ai/langchain
**开发者**：LangChain Inc
**许可证**：MIT
**语言**：Python + TypeScript
**定位**：**"Framework for building LLM-powered applications"**

## 核心定位

LangChain 是当前**生态最大、provider 覆盖最广**的 LLM framework，但**不是专门的 Agent framework**——它是**LLM 应用的通用工具箱**。

**包含的能力**：
- 100+ LLM provider 集成（OpenAI / Anthropic / Azure / AWS / Google / 本地 / ...）
- 100+ Vector store 集成
- 100+ Document loader 集成
- Chain 抽象（LCEL pipe 语法）
- Agent 抽象（`AgentExecutor`）
- Memory 抽象
- Callbacks / Tracing（LangSmith）

Agent 只是 LangChain 的一个子模块，LangChain 本身更关注**LLM 管道**（Chain）。

## 核心抽象：LCEL (LangChain Expression Language)

```python
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

prompt = ChatPromptTemplate.from_template("Tell me a joke about {topic}")
model = ChatOpenAI(model="gpt-4")
parser = StrOutputParser()

# LCEL: 用 | 管道组合
chain = prompt | model | parser
result = chain.invoke({"topic": "programmers"})
```

## Agent 构建（旧 API）

```python
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain import hub

prompt = hub.pull("hwchase17/openai-tools-agent")
agent = create_openai_tools_agent(llm, tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
agent_executor.invoke({"input": "What's the weather in Seattle?"})
```

## LangChain 和 LangGraph 的关系

这是初学者最容易混淆的：

| | LangChain | LangGraph |
|---|---|---|
| 定位 | **LLM 管道工具箱** | **Agent 编排 framework** |
| 核心抽象 | `Runnable` + LCEL | `StateGraph` |
| 适合场景 | RAG / 链式调用 / 单次 LLM 任务 | 多步骤 / 多 agent / 可恢复 |
| 是否包含 | 一个旧的 `AgentExecutor` | **新一代 agent** |
| 维护者 | 都是 LangChain Inc | |

**官方建议**：新项目做 agent 应该用 **LangGraph**，LangChain 的 `AgentExecutor` 是遗留 API。

## 与 AgentScope 对比

| 维度 | LangChain | AgentScope |
|---|---|---|
| 主定位 | **LLM 通用管道** | **Agent 专用 framework** |
| Provider 数 | **100+** | ~7 |
| Vector store | 100+ | 少数 |
| Agent 抽象 | 旧遗留 | ReAct 现代 |
| 依赖大小 | **重**（100K+ 行） | 中（43K 行） |
| 学习曲线 | 陡（抽象多） | 平 |
| 微调支持 | ✗ | ✓ Trinity-RFT |
| MCP 原生 | ✗ | ✓ |

## 何时选它

- 需要**最大的 provider 覆盖**
- 构建**简单的 LLM 管道**（RAG / 问答 / 摘要）
- 已经在使用 LangChain 生态
- 需要**大量文档加载器 / vector store**

## 何时不选

- 你要构建**复杂 Agent**（换 LangGraph / AgentScope）
- 需要**最小依赖**（LangChain 依赖很重）
- 追求**清晰的抽象层次**（LangChain 抽象层次多，学习曲线陡）
- 需要实时语音 / agentic RL / A2A（换 AgentScope）

---

> **注**：本页基于官方文档和 README。本地无源码。
