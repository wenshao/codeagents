# CrewAI

> Role-based 多 Agent framework，MIT，Python。

**仓库**：https://github.com/crewAIInc/crewAI
**开发者**：CrewAI Inc
**许可证**：MIT
**语言**：Python
**定位**：**"Framework for orchestrating role-playing, autonomous AI agents"**

## 核心抽象：Role → Task → Crew

CrewAI 最直观的设计是**把 agent 类比为真实员工**：

```python
from crewai import Agent, Task, Crew, Process

researcher = Agent(
    role="Senior Research Analyst",
    goal="Uncover cutting-edge developments in AI",
    backstory="You are an expert analyst who...",
    tools=[search_tool],
)

writer = Agent(
    role="Tech Content Strategist",
    goal="Craft compelling content on tech advancements",
    backstory="...",
)

task1 = Task(
    description="Conduct a comprehensive analysis of the latest AI advancements",
    agent=researcher,
    expected_output="A full analysis report",
)

task2 = Task(
    description="Write a blog post based on the research",
    agent=writer,
    expected_output="A 2000-word blog post",
    context=[task1],  # 依赖 task1 的输出
)

crew = Crew(
    agents=[researcher, writer],
    tasks=[task1, task2],
    process=Process.sequential,  # 或 Process.hierarchical
)
result = crew.kickoff()
```

## 核心特性

| 能力 | 说明 |
|---|---|
| **Role-based** | 每个 agent 有 role / goal / backstory（注入 prompt） |
| **Task 依赖** | `context=[task1]` 表示 task2 需要 task1 的输出 |
| **Process** | `sequential`（顺序）/ `hierarchical`（Manager agent 分派） |
| **Memory** | ShortTerm / LongTerm / Entity 三种 memory |
| **Delegation** | agent 之间可以互相委派 |
| **Knowledge Sources** | 预注入文档 / URL 作为 agent 的"背景知识" |

## 与 AgentScope 对比

| 维度 | CrewAI | AgentScope |
|---|---|---|
| 核心抽象 | Role + Task + Crew | ReAct loop + MsgHub |
| 适合场景 | **业务角色分工** | 松耦合多 agent 讨论 |
| 学习曲线 | **最平**（业务员工类比） | 中等 |
| Role prompt | 自动注入 | 手工 |
| Task 依赖图 | ✓ | ⚠️ 手工 MsgHub |
| 微调支持 | ✗ | ✓ |
| MCP 原生 | ✗（通过插件） | ✓ |

## 何时选它

- 场景是**业务角色分工**（产品 → 设计 → 开发 → 测试）
- 团队里有非技术同事要理解 agent 架构
- 需要**直观的 API**
- 流程是 sequential / hierarchical 的标准模板

## 何时不选

- 需要**复杂的非线性编排**（换 LangGraph）
- 需要 role 之外的**自定义 loop**（过度约束）
- 需要**实时语音 / agentic RL**（换 AgentScope）

---

> **注**：本页基于官方文档和 README。本地无源码。
