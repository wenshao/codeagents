# AgentScope — 概述

## 产品定位

AgentScope 由**阿里通义千问 Lab（SysML team）**开发，定位是 **"production-ready, easy-to-use agent framework"**。

官方 README 的核心主张（`README.md:61-64`）：

> "AgentScope is a production-ready, easy-to-use agent framework with essential abstractions that work with rising model capability and built-in support for finetuning. We design for increasingly agentic LLMs. Our approach leverages the models' reasoning and tool use abilities rather than constraining them with strict prompts and opinionated orchestrations."

**关键设计哲学**：**"leverage the models' reasoning ... rather than constraining them with strict prompts"** —— 不试图用 hardcoded prompt 束缚 LLM，而是暴露原始的推理能力让开发者自己编排。

## 三大支柱（README.md:68-70）

1. **Simple**: "start building your agents in 5 minutes with built-in ReAct agent, tools, skills, human-in-the-loop steering, memory, planning, realtime voice, evaluation and model finetuning"
2. **Extensible**: "large number of ecosystem integrations for tools, memory and observability; built-in support for MCP and A2A; message hub for flexible multi-agent orchestration and workflows"
3. **Production-ready**: "deploy and serve your agents locally, as serverless in the cloud, or on your K8s cluster with built-in OTel support"

## 安装

```bash
pip install agentscope
```

源码安装（推荐开发者）：

```bash
git clone https://github.com/agentscope-ai/agentscope.git
cd agentscope && pip install -e .
```

## 最小示例

```python
import asyncio
from agentscope.agent import ReActAgent
from agentscope.model import OpenAIChatModel
from agentscope.tool import Toolkit

async def main():
    toolkit = Toolkit()
    # 注册内置或自定义工具
    toolkit.register_tool_function(some_tool_func)

    agent = ReActAgent(
        name="Assistant",
        model=OpenAIChatModel(model_name="gpt-4o"),
        toolkit=toolkit,
        max_iters=10,  # 默认值
    )
    reply = await agent("帮我分析一下 hermes-agent 的架构")
    print(reply)

asyncio.run(main())
```

## 核心依赖（`pyproject.toml:22-45`）

```python
dependencies = [
    "anthropic",
    "openai",
    "dashscope",              # Alibaba DashScope SDK
    "mcp>=1.13",              # Model Context Protocol
    "opentelemetry-api>=1.39.0",      # OTel 可观测性
    "opentelemetry-sdk>=1.39.0",
    "opentelemetry-exporter-otlp>=1.39.0",
    "opentelemetry-semantic-conventions>=0.60b0",
    "python-socketio",        # 实时通信
    "tiktoken",
    ...
]
```

**可选依赖组**（`pyproject.toml:50+`）：
- `a2a = ["a2a-sdk", "httpx", "nacos-sdk-python>=3.0.0"]` —— Agent-to-Agent 协议
- `evaluate = ["ray"]` —— 并行评估框架
- `rag = ...` —— 向量检索
- `tune = ["trinity-rft"]` —— agentic RL 微调

## 支持的 LLM Provider

基于源码 `src/agentscope/formatter/`：

| Provider | 格式化器 | 说明 |
|---|---|---|
| **OpenAI** | `_openai_formatter.py` | GPT-4 / GPT-4o / GPT-5 |
| **Anthropic** | `_anthropic_formatter.py` | Claude 3 / 4 |
| **DashScope** | `_dashscope_formatter.py` | Qwen 全系列 |
| **Gemini** | `_gemini_formatter.py` | Google Gemini |
| **DeepSeek** | `_deepseek_formatter.py` | DeepSeek V3 / R1 |
| **Ollama** | `_ollama_formatter.py` | 本地模型 |
| **A2A** | `_a2a_formatter.py` | 跨 Agent 消息 |

## 代码规模

```bash
$ find src -name "*.py" | wc -l
215
$ find src -name "*.py" | xargs wc -l
43574 total
```

**43K 行 / 215 文件** —— 相比：

| Framework | 代码量（估算） |
|---|---|
| **AgentScope** | 43K 行 |
| LangGraph | ~15-20K 行 |
| CrewAI | ~25K 行 |
| AG2 | ~60-80K 行（AutoGen 遗产） |
| LangChain core | ~100K+ 行 |

**中等规模**——比 LangGraph 厚重（因为包含 memory / plan / a2a / tune 等额外模块），比 LangChain 轻（因为没有 LangChain 那种囊括一切的野心）。

## 与其他 Agent Framework 的核心差异

| 差异点 | AgentScope | LangGraph | CrewAI | AG2 |
|---|---|---|---|---|
| **主抽象** | 显式 ReAct loop + hooks | 状态图（StateGraph） | Role-based Team | Conversation-based |
| **多 Agent 模式** | MsgHub 广播 + async context | Graph 节点 + edge 路由 | Crew 角色分工 | GroupChat 对话 |
| **计划系统** | 第一级（`PlanNotebook`） | 隐式在状态图中 | `Task` + `Process` | 无独立抽象 |
| **A2A 协议** | **原生（官方 SDK）** | ❌ | ❌ | ❌ |
| **MCP 支持** | **官方 `mcp>=1.13`** | ❌ | 仅第三方包 | ❌ |
| **Fine-tune 支持** | **Trinity-RFT agentic RL** | ❌ | ❌ | ❌ |
| **实时语音** | **OpenAI/DashScope/Gemini Realtime WebSocket** | ❌ | ❌ | ❌ |
| **OTel tracing** | **原生（13 个 extractor）** | 基础 | ❌ | ❌ |
| **Memory 后端** | **4 种（InMemory / Redis / SQLAlchemy / TableStore）** | Checkpointer | ShortTerm/LongTerm | 会话内 |
| **论文背书** | arXiv:2402.14034 | ❌ | ❌ | 多篇 AutoGen |
| **学术关注度** | 中 | 高 | 中 | 高 |

**AgentScope 的独特标签**：**"显式 + 可扩展 + 生态完整"**。它不强加架构范式（状态图 / role / conversation），而是给开发者一个**完整的 Agent 工具箱**——ReAct loop 自己改、hook 自己注、工具自己注册、memory 自己选后端、A2A 自己接协议。

## Roadmap（从 `docs/roadmap.md`）

| 阶段 | 主题 | 状态 |
|---|---|---|
| Phase 1 | TTS Models | ✓ 完成（v2025-12） |
| Phase 2 | Multimodal Models（实时语音 Agent） | ~2026 Feb |
| Phase 3 | Real-time Multimodal（streaming / interrupts / concurrent） | 进行中 |

核心方向是**语音 Agent**和**多模态实时交互**，这是当前 6 款 framework 中**最独特**的方向。

## 下一步

- 核心架构和主循环 → [02-architecture.md](./02-architecture.md)
- 20 个模块详解 → [03-key-modules.md](./03-key-modules.md)
- 源码引用 → [EVIDENCE.md](./EVIDENCE.md)
