# AgentScope

> 阿里通义千问 Lab 的 Agent Framework。当前 codeagents 对比矩阵中唯一**本地有完整源码**的 Agent Framework，做源码级分析。

**仓库**：https://github.com/agentscope-ai/agentscope
**开发者**：Alibaba Tongyi Lab（SysML team）
**许可证**：Apache-2.0
**版本**：0.x（2026 年 4 月当前）
**论文**：[arXiv:2402.14034](https://arxiv.org/abs/2402.14034)
**Stars**：23.7k / Forks: 2.5k
**语言**：Python >= 3.10，**215 文件 / 43,574 行**
**本地源码**：`/root/git/agentscope`

## 文件结构

| 文件 | 内容 |
|---|---|
| [01-overview.md](./01-overview.md) | 产品定位、安装、依赖、与 LangGraph/CrewAI/AG2 的差异 |
| [02-architecture.md](./02-architecture.md) | `ReActAgentBase` 主循环、Toolkit、多 Agent MsgHub、状态模型 |
| [03-key-modules.md](./03-key-modules.md) | 20 个顶层模块详解：memory / plan / a2a / mcp / hooks / tracing / realtime / tune |
| [EVIDENCE.md](./EVIDENCE.md) | 全部声明的 `path:line` 源码引用 |

## 一句话

**"Production-ready multi-agent framework"** —— 显式 ReAct loop + 内置 A2A 协议 + 官方 MCP 支持 + OTel tracing + Trinity-RFT 微调 + 实时语音 Agent。设计哲学："**leverages the models' reasoning and tool use abilities rather than constraining them with strict prompts and opinionated orchestrations**"（源码 `README.md:61`）。

## 核心差异化

| 能力 | AgentScope 独特性 | 对标 |
|---|---|---|
| **显式 ReAct loop** | `reasoning()` + `acting()` 明确分离，4 个 hook 点（pre/post × reasoning/acting） | LangGraph 是状态图抽象；CrewAI 是任务路由 |
| **Agentic RL（Trinity-RFT）** | `tune()` 接口 —— **从 agent trajectories 反哺训练** | 其他 framework 都不支持 |
| **Realtime 语音 Agent** | OpenAI Realtime + DashScope + Gemini Realtime WebSocket | AG2 / LangGraph 无 |
| **A2A 协议原生** | 集成 `a2a-sdk` + Nacos 服务发现 | 仅 MAF 提过 A2A，无源码实现 |
| **MsgHub 消息总线** | 多 Agent 自动广播 + async context manager | vs LangGraph 状态图 vs CrewAI role-based |
| **Tuner/Tune 模块** | 用 agent workflow 输出做 RL 训练数据 | 仅 AgentScope 有此定位 |

## 与 codeagents Code Agent 的关系

**AgentScope 是 Framework，不是 Code Agent**——你不能 `agentscope` 命令启动一个编程助手。它是 SDK。如果要用 AgentScope 构建一个 Code Agent，你需要：

```python
from agentscope.agent import ReActAgent
from agentscope.tool import Toolkit
# 自己加工具、loop、UI...
```

这和 Claude Code（开箱即用的编程终端）是**两个层次的产品**。

## 下一步

- 技术定位和安装 → [01-overview.md](./01-overview.md)
- 核心架构和 ReAct loop → [02-architecture.md](./02-architecture.md)
- 20 个模块详解 → [03-key-modules.md](./03-key-modules.md)
- 源码引用 → [EVIDENCE.md](./EVIDENCE.md)
- 与其他 framework 对比 → [`../comparison.md`](../comparison.md)
