# AgentScope — 架构

## 源码规模

```
215 个 .py 文件 / 43,574 行 Python
```

## 顶层目录结构

```
src/agentscope/
├── agent/            # 主代理类（AgentBase + ReActAgentBase + ReActAgent）
├── tool/             # Toolkit + 工具注册 + MCP 集成
├── model/            # LLM 提供商适配（OpenAI/Anthropic/DashScope/Gemini/...）
├── formatter/        # 消息格式化（每个 provider 一个 formatter）
├── memory/           # 4 后端 memory（InMemory/Redis/SQLAlchemy/TableStore）
├── pipeline/         # MsgHub 多 Agent 编排
├── plan/             # PlanNotebook + Plan + SubTask（first-class 计划）
├── a2a/              # Agent-to-Agent 协议（a2a-sdk 集成）
├── mcp/              # Model Context Protocol Client
├── hooks/            # Hook 系统（pre/post × reasoning/acting/reply/print）
├── embedding/        # Embedding 提供商
├── rag/              # 检索增强生成
├── evaluate/         # 任务评估框架（Ray 并行）
├── tune/             # 微调入口（Trinity-RFT 集成）
├── tuner/            # 微调辅助工具
├── realtime/         # 实时语音 Agent（WebSocket）
├── tts/              # 文本转语音（OpenAI / DashScope / Gemini）
├── tracing/          # OTel tracing（13 个 span extractor）
├── session/          # 会话持久化
├── token/            # Token 计数器
├── message/          # Msg 对象（Agent 间通信单元）
├── module/           # StateModule 基类
├── types/            # Pydantic 类型定义
└── hooks/            # Studio 集成 hook
```

## 核心主循环：`ReActAgent.reply()`

源码：`src/agentscope/agent/_react_agent.py:428-520`

```python
async def reply(self, msg, ...):
    # -------------- The reasoning-acting loop --------------
    # Cache the structured output generated in the finish function call
    structured_output = None
    reply_msg = None
    for _ in range(self.max_iters):
        # -------------- Memory compression --------------
        await self._compress_memory_if_needed()

        # -------------- The reasoning process --------------
        msg_reasoning = await self._reasoning(tool_choice)

        # -------------- The acting process --------------
        futures = [
            self._acting(tool_call)
            for tool_call in msg_reasoning.get_content_blocks("tool_use")
        ]
        # Parallel tool calls or not
        if self.parallel_tool_calls:
            structured_outputs = await asyncio.gather(*futures)
        else:
            structured_outputs = [await _ for _ in futures]

        # -------------- Exit condition --------------
        elif not msg_reasoning.has_content_blocks("tool_use"):
            # Exit the loop when no tool calls and only text response
            msg_reasoning.metadata = structured_output
            reply_msg = msg_reasoning
            break
```

**关键特征**：

1. **显式 ReAct**：`_reasoning()` 和 `_acting()` 明确分离，不是"function-calling 隐式 loop"
2. **默认 `max_iters = 10`**（`_react_agent.py:197`）
3. **内置 memory 压缩**：`_compress_memory_if_needed()` 每次 loop 前检查
4. **可选并行工具**：`parallel_tool_calls: bool = False`（默认串行）
5. **退出条件**：模型输出纯文本（无 tool_use block）即退出

## `_reasoning()` 流程

源码：`src/agentscope/agent/_react_agent.py:540-572`

```python
async def _reasoning(
    self,
    tool_choice: Literal["auto", "none", "required"] | None = None,
) -> Msg:
    """Perform the reasoning process."""
    # ...
    res = await self.model(
        prompt,
        tools=self.toolkit.get_json_schemas(),
        tool_choice=tool_choice,
    )
```

**要点**：
- 通过 `self.toolkit.get_json_schemas()` 动态组装工具 schema（无固定工具表）
- `tool_choice` 可以强制 `"required"`（必须调用工具）或 `"none"`（禁用）或 `"auto"`（让模型决定）
- Model 抽象屏蔽各 Provider 差异

## `_acting()` 流程

源码：`src/agentscope/agent/_react_agent.py:657-715`

```python
async def _acting(self, tool_call: ToolUseBlock) -> dict | None:
    """Perform the acting process."""
    # ...
    tool_res = await self.toolkit.call_tool_function(tool_call)

    # Async generator handling
    async for chunk in tool_res:
        # Turn into a tool result block
        tool_res_msg.content[0]["output"] = chunk.content
```

**要点**：
- 工具结果是**流式**（async generator），可以边执行边更新 UI
- `ToolResponse` chunks 累积成最终 result

## Hook 系统

源码：`src/agentscope/agent/_react_agent_base.py:21-32`

```python
supported_hook_types: list[str] = [
    # 继承自 AgentBase:
    "pre_reply",
    "post_reply",
    "pre_print",
    "post_print",
    "pre_observe",
    "post_observe",
    # ReAct 新增:
    "pre_reasoning",
    "post_reasoning",
    "pre_acting",
    "post_acting",
]
```

**10 种 hook 点**，覆盖主循环的每个关键节点。

### Hook 注册示例（`hooks/__init__.py:5-29`）

```python
def _equip_as_studio_hooks(studio_url: str) -> None:
    """Connect to the agentscope studio."""
    AgentBase.register_class_hook(
        "pre_print",
        "as_studio_forward_message_pre_print_hook",
        partial(
            as_studio_forward_message_pre_print_hook,
            studio_url=studio_url,
            run_id=_config.run_id,
        ),
    )
```

**两级 hook**：
- **Class-level**：所有该类实例共享
- **Instance-level**：仅当前 agent 实例

用 `OrderedDict` 存储，保证注册顺序（`_react_agent_base.py:35-62`）。

**对比**：
- **Claude Code hooks**：27 个事件，支持 `command` / `http` / `prompt` 三种类型
- **Qwen Code hooks**：继承 Gemini CLI，12 事件
- **AgentScope hooks**：**10 事件（loop 内部），但仅 Python callable**（无 command/http 类型）

## Toolkit

源码：`src/agentscope/tool/_toolkit.py:117-138`

```python
"""
Toolkit is the core module to register, manage and delete tool functions,
MCP clients, Agent skills in AgentScope.

About tool functions:
- Register and parse JSON schemas from their docstrings automatically.
- Group-wise tools management, and agentic tools activation/deactivation.
- Extend the tool function JSON schema dynamically with Pydantic BaseModel.
- Tool function execution with unified streaming interface.
"""
```

**核心能力**：

1. **自动 JSON Schema 解析**（`_toolkit.py:409-425`）——从 docstring 直接解析，无需 decorator
2. **Group-wise 管理**——工具可以分组启用/禁用
3. **MCP 集成**（`import mcp`）——可直接注册 MCP server 的工具
4. **流式接口**——工具输出作为 async generator
5. **动态 schema 扩展**——用 Pydantic BaseModel 在运行时修改 schema

### 工具注册示例

```python
from agentscope.tool import Toolkit

def get_weather(city: str) -> dict:
    """Get current weather for a city.

    Args:
        city: The city name.

    Returns:
        A dict with weather info.
    """
    ...

toolkit = Toolkit()
toolkit.register_tool_function(get_weather)
# JSON schema 自动从 docstring + type hints 生成
```

**对比 LangChain**：LangChain 需要 `@tool` decorator 或 `Tool.from_function(...)`；AgentScope 直接传函数即可。

## 多 Agent：MsgHub

源码：`src/agentscope/pipeline/_msghub.py:14`

```python
class MsgHub:
    """MsgHub class that controls the subscription of the participated agents.

    Example:
        In the following example, the reply message from `agent1`, `agent2`,
        and `agent3` will be broadcast to all the other agents in the MsgHub.
    """
```

**使用模式**：

```python
async with MsgHub(participants=[agent1, agent2, agent3]) as hub:
    # Agent 1 说话 → 自动广播给 agent2, agent3
    msg = await agent1("让我们讨论这个设计")
    # Agent 2 回复 → 自动广播给 agent1, agent3
    reply = await agent2()
```

**与其他 framework 对比**：

| Framework | 多 Agent 抽象 | 优劣 |
|---|---|---|
| **AgentScope MsgHub** | 广播 + async context | 简单、灵活，无结构化状态 |
| **LangGraph** | StateGraph 节点 + edge | 可视化、可恢复、复杂 |
| **CrewAI** | Role + Task + Process | Role-based，适合业务场景 |
| **AG2 GroupChat** | Conversation-based | 自然，但难追踪状态 |

## State Module

源码：`src/agentscope/module/_state_module.py`

**所有可持久化对象**（Agent、Memory、Toolkit、PlanNotebook 等）都继承 `StateModule`，提供：

- `state_dict()` / `load_state_dict()` —— 序列化/反序列化
- Session 集成 —— 自动保存到 session backend

这是 AgentScope 实现**"production-ready"**的关键：任何 Agent 都可以在进程重启后从 session 恢复。

## 数据流全景

```
用户消息
    │
    ▼
┌──────────────────────────────────────────────┐
│  agent("你好")                               │
│    │                                         │
│    ▼                                         │
│  pre_reply hook                              │
│    │                                         │
│    ▼                                         │
│  reply() 主循环（最多 max_iters=10 次）     │
│    │                                         │
│    ├─ _compress_memory_if_needed()           │
│    ├─ pre_reasoning hook                     │
│    ├─ _reasoning()                           │
│    │    └─ model.call(prompt, tools, ...)   │
│    ├─ post_reasoning hook                    │
│    ├─ pre_acting hook                        │
│    ├─ _acting()（串行 or 并行 asyncio.gather）│
│    │    └─ toolkit.call_tool_function(...)  │
│    ├─ post_acting hook                       │
│    │                                         │
│    └─ 检查退出条件（无 tool_use → break）    │
│                                              │
│  post_reply hook                             │
└──────────────────────────────────────────────┘
    │
    ▼
响应

（并行：tracing 发送 OTel spans，memory 写入 backend，session 持久化）
```

## 下一步

- 20 个模块详解 → [03-key-modules.md](./03-key-modules.md)
- 源码引用 → [EVIDENCE.md](./EVIDENCE.md)
