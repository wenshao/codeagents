# AG2 (原 AutoGen)

> Conversation-based 多 Agent framework，社区 fork from Microsoft AutoGen，Apache-2.0，Python。

**仓库**：https://github.com/ag2ai/ag2
**开发者**：AG2 社区（从 Microsoft AutoGen 分叉）
**许可证**：Apache-2.0
**语言**：Python
**定位**：**"Open-source programming framework for agentic AI"**
**论文**：[AutoGen: Enabling Next-Gen LLM Applications via Multi-Agent Conversation (arXiv:2308.08155)](https://arxiv.org/abs/2308.08155)

## 核心抽象：Conversation-based 多 Agent

AG2 的设计哲学是**把多 Agent 交互建模为对话**：

```python
import autogen

config_list = [{"model": "gpt-4", "api_key": "..."}]

user_proxy = autogen.UserProxyAgent(
    name="user",
    human_input_mode="NEVER",
    code_execution_config={"work_dir": "coding"},
)

assistant = autogen.AssistantAgent(
    name="assistant",
    llm_config={"config_list": config_list},
)

# 简单两人对话
user_proxy.initiate_chat(
    assistant,
    message="Plot a chart of NVDA and TESLA stock price YTD.",
)

# 多 Agent GroupChat
group = autogen.GroupChat(agents=[agent1, agent2, agent3], max_round=12)
manager = autogen.GroupChatManager(groupchat=group)
user_proxy.initiate_chat(manager, message="...")
```

## 核心特性

| 能力 | 说明 |
|---|---|
| **AssistantAgent** | 会写代码的 agent |
| **UserProxyAgent** | 代表用户，可执行代码（沙箱） |
| **GroupChat** | 多 Agent 对话，支持 selector 策略 |
| **GroupChatManager** | 管理 GroupChat 的 agent 轮转 |
| **代码执行** | 内置 Docker / 本地 shell 代码执行 |
| **Teachable** | Teachable agent 记住用户偏好（类似 memory） |
| **Captainship** | Captain 模式，一个 agent 监督其他 agents |

## 和 Microsoft AutoGen 的关系

- **Microsoft AutoGen** 原版仍在维护（`microsoft/autogen`）
- **AG2** 是社区分叉（由原 AutoGen 主要贡献者组织），更活跃
- 两者 API 基本兼容，AG2 更侧重**稳定性和社区驱动**

## 与 AgentScope 对比

| 维度 | AG2 | AgentScope |
|---|---|---|
| 多 Agent 抽象 | GroupChat 对话 | MsgHub 广播 |
| 代码执行 | **内置**（Docker / shell） | 手工工具 |
| 场景适合 | **对话模拟、辩论、讨论** | 通用 agent 构建 |
| 学术背书 | **强**（AutoGen 论文） | arXiv:2402.14034 |
| Role 定义 | 通过 `system_message` | ReAct + hook |
| 微调支持 | ✗ | ✓ Trinity-RFT |

## 何时选它

- 场景是**多 Agent 对话模拟**（辩论、头脑风暴、角色扮演）
- 需要**内置代码执行沙箱**（不想自己搭）
- 研究论文、学术工作

## 何时不选

- 需要**严格的工作流**（换 LangGraph）
- 需要**业务角色直观性**（换 CrewAI）
- 需要 MCP / A2A / 微调（换 AgentScope）

---

> **注**：本页基于官方文档和 README。本地无源码。
