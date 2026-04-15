# Microsoft Agent Framework (MAF)

> 微软官方 Agent framework，MIT，C# + Python，Azure 深度集成。

**仓库**：https://github.com/microsoft/agent-framework
**开发者**：Microsoft
**许可证**：MIT
**语言**：C#（主）+ Python（预览）
**定位**：**"Production-ready framework for building AI agents at scale"**

## 核心定位

Microsoft Agent Framework 是**微软推出的 AutoGen 继任者**，目标是提供 production-grade agent 构建能力，特别强调：

1. **多语言**（C# 为主，Python 次之）
2. **Azure 深度集成**（Application Insights / Azure OpenAI / Azure AI Search）
3. **企业级**（RBAC / 合规 / 审计）

## 核心抽象：ChatHandler + FunctionInvocation

```csharp
using Microsoft.AgentFramework;

var agent = new ChatAgent(
    name: "Assistant",
    instructions: "You are a helpful assistant",
    chatClient: new AzureOpenAIChatClient(...),
    functions: new[] { GetWeatherFunction, SearchFunction }
);

var response = await agent.SendAsync("What's the weather in Seattle?");
```

Python 接口（预览）类似：

```python
from microsoft.agent_framework import ChatAgent, AzureOpenAIChatClient

agent = ChatAgent(
    name="Assistant",
    instructions="...",
    chat_client=AzureOpenAIChatClient(...),
    functions=[...],
)
response = await agent.send_async("...")
```

## 核心特性

| 能力 | 说明 |
|---|---|
| **Connected Agents** | 多 agent 通过 API 互相调用 |
| **Function Invocation** | 原生 function calling 抽象 |
| **Filters** | 中间件式拦截器（类似 hooks） |
| **Memory** | IMemoryProvider 接口 |
| **Tools** | 通过 Semantic Kernel 插件 |
| **Vector Store** | Azure AI Search / Qdrant / Weaviate |
| **OTel** | Application Insights 原生 |

## 和 Semantic Kernel / AutoGen 的关系

微软的 agent 产品线正在整合：

- **Semantic Kernel**（旧）→ LLM orchestration 管线
- **AutoGen**（旧）→ 多 agent 研究框架
- **Microsoft Agent Framework**（新）→ 两者合并的 production 继任者

**MAF 吸收了 Semantic Kernel 的 plugin 系统和 AutoGen 的 multi-agent 概念**，但 API 重新设计，更简洁。

## 与 AgentScope 对比

| 维度 | MAF | AgentScope |
|---|---|---|
| 主语言 | **C#** | Python |
| Azure 集成 | **深度** | 无 |
| 跨平台 | 需 .NET Core | 纯 Python |
| 多 Agent | Connected Agents | MsgHub |
| MCP 支持 | 预览 | **官方 `mcp>=1.13`** |
| A2A | 概念 | **原生 `a2a-sdk`** |
| 微调 | ✗ | ✓ Trinity-RFT |
| OTel | **Application Insights** | OTel 通用 |

## 何时选它

- 团队是**.NET / C# 栈**
- 在 **Azure 云环境**部署
- 需要 Application Insights / Azure Monitor 可观测性
- 企业合规要求（RBAC / 审计）

## 何时不选

- Python 纯技术栈（换 AgentScope / LangGraph）
- 需要 AgentScope 独有的微调 / 实时语音
- 跨云部署（MAF 的 Azure 集成是双刃剑）

---

> **注**：本页基于官方文档和 GitHub README。MAF 本身处于预览阶段，API 可能变动。本地无源码。
