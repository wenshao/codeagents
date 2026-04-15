# AgentScope — 关键模块详解

## 1. Memory 系统（4 后端）

源码：`src/agentscope/memory/`

### Memory 层级

```
MemoryBase (StateModule)
├── InMemoryMemory              # 进程内存
├── RedisMemory                 # Redis
├── SQLAlchemyMemory            # 任意 SQL 数据库
└── TablestoreMemory            # 阿里 TableStore
```

源码：`src/agentscope/memory/_working_memory/_base.py:11`

```python
class MemoryBase(StateModule):
    """The base class for memory in agentscope."""
```

### 长期记忆

源码：`src/agentscope/memory/`

- `Mem0Integration` —— 集成 Mem0（第三方长期记忆服务）
- `ReMe` —— Retrieval-based Memory（检索式记忆）
- 用户可自定义 backend

### 向量检索

通过 `embedding/` + `rag/` 模块：

```python
# src/agentscope/embedding/
_openai_embedding.py
_dashscope_embedding.py
_gemini_embedding.py
# ...

# src/agentscope/rag/
# 支持 Qdrant / Milvus / OceanBase / MongoDB
```

### Memory 压缩

源码：`src/agentscope/agent/_react_agent.py:107-162`

```python
class CompressionConfig(BaseModel):
    """The compression related configuration in AgentScope"""
    enable: bool
    agent_token_counter: TokenCounterBase
    trigger_threshold: int
    keep_recent: int = 3
```

**机制**：
- 每次 reasoning 前 `_compress_memory_if_needed()` 检查 token 数
- 超过 `trigger_threshold` → 压缩旧消息
- 保留最近 `keep_recent=3` 条原样

**对标**：Claude Code 多层上下文压缩（qwen-code-improvement-report item-1）。AgentScope 是单层阈值触发，相对简单。

---

## 2. Plan 模块（First-Class 计划原语）

源码：`src/agentscope/plan/`

### PlanNotebook

源码：`src/agentscope/plan/_plan_notebook.py:172`

```python
"""The plan notebook to manage the plan, providing hints and plan related
tool functions to the agent."""
```

**定位**：Plan 是 Agent 可以调用的**工具**（而不是外部编排）——Agent 自己决定什么时候制定计划、何时开始执行。

### 数据模型

源码：`src/agentscope/plan/_plan_model.py`

```python
class SubTask(BaseModel):
    index: int
    name: str
    state: Literal["todo", "in_progress", "done", "abandoned"]
    details: str
    # ...

class Plan(BaseModel):
    subtasks: list[SubTask]
    overall_goal: str
    # ...
```

### 状态机

源码：`src/agentscope/plan/_plan_notebook.py:119-133`

```python
if subtask.state == "todo":
    n_todo += 1
elif subtask.state == "in_progress":
    n_in_progress += 1
    in_progress_subtask_idx = idx
elif subtask.state == "done":
    n_done += 1
elif subtask.state == "abandoned":
    n_abandoned += 1
```

每个 subtask 有 4 个状态：`todo` / `in_progress` / `done` / `abandoned`。

### Hint 注入

源码：`src/agentscope/plan/_plan_notebook.py:50-68`

```python
when_a_subtask_in_progress: str = (
    "The current plan:\n"
    "```\n"
    "{plan}\n"
    "```\n"
    "Now the subtask at index {subtask_idx}, named '{subtask_name}', is "
    "'in_progress'. Its details are as follows:\n"
    "```\n"
    "{subtask}\n"
    "```\n"
    ...
)
```

每次 reasoning 开始时，PlanNotebook 把"当前计划 + 活跃 subtask"作为 hint 注入 prompt。

**对标**：
- **Claude Code `/plan`** —— 手工触发的 plan 模式
- **Qwen Code PR#2921** —— `/plan` 命令
- **AgentScope PlanNotebook** —— Agent **自主管理**计划，无需用户触发

---

## 3. A2A 协议（Agent-to-Agent）

源码：`src/agentscope/a2a/`

### 依赖

`pyproject.toml:50`

```python
a2a = [
    "a2a-sdk",                      # 官方 A2A 协议 SDK
    "httpx",
    "nacos-sdk-python>=3.0.0",      # 阿里 Nacos 服务发现
]
```

**AgentScope 是目前 6 款 framework 中唯一原生集成 A2A 协议的**。

### AgentCard Resolver

源码：`src/agentscope/a2a/_base.py:18-25`

```python
@abstractmethod
async def get_agent_card(self, *args: Any, **kwargs: Any) -> AgentCard:
    """Get Agent Card from the configured source.

    Returns:
        `AgentCard`:
            The resolved agent card object.
    """
```

**3 种 Resolver**：
1. **Well-known**（标准 A2A 注册表）
2. **File-based**（本地 JSON）
3. **Nacos**（阿里服务网格）

### 使用场景

假设你有 10 个独立运行的 Agent（可能在不同服务器上）：

```python
# Agent A 查询 Agent B 的能力
card = await resolver.get_agent_card("agent_b_id")
# 根据 card 中的 schema 调用 agent_b 的能力
response = await a2a_client.invoke(card, "帮我分析这段代码")
```

**对标**：
- **MCP**：工具/资源级别的协议（一个 agent 调用**工具**）
- **A2A**：agent 级别的协议（一个 agent 调用**另一个 agent**）
- 二者互补，不冲突

---

## 4. Tracing（OTel 13 个 extractor）

源码：`src/agentscope/tracing/`

### OTel 依赖

`pyproject.toml:34-37`

```python
opentelemetry-api>=1.39.0,
opentelemetry-sdk>=1.39.0,
opentelemetry-exporter-otlp>=1.39.0,
opentelemetry-semantic-conventions>=0.60b0,
```

### 13 个 Span Extractor

源码：`src/agentscope/tracing/_trace.py:24-45`

```python
from ._extractor import (
    _get_agent_request_attributes,
    _get_agent_span_name,
    _get_agent_response_attributes,
    _get_llm_request_attributes,
    _get_llm_span_name,
    _get_llm_response_attributes,
    _get_tool_request_attributes,
    _get_tool_span_name,
    _get_tool_response_attributes,
    _get_formatter_request_attributes,
    _get_formatter_span_name,
    _get_formatter_response_attributes,
    _get_generic_function_request_attributes,
    _get_generic_function_span_name,
    _get_generic_function_response_attributes,
    _get_embedding_request_attributes,
    _get_embedding_span_name,
    _get_embedding_response_attributes,
)
```

**覆盖 5 类操作**：
1. **Agent** 调用（主 reply）
2. **LLM** 调用
3. **Tool** 调用
4. **Formatter** 调用（消息格式化）
5. **Embedding** 调用

每类都有 `span_name` / `request_attributes` / `response_attributes` 三个 extractor。

### 自动注入

Tracing 不需要用户手写 —— AgentScope 在 Agent/Model/Tool/Formatter/Embedding 的调用点自动注入 span。

**对比**：
- **Qwen Code**：仅阿里云 RUM 遥测，无 OTel
- **Goose**：PostHog + OTel + Langfuse
- **AgentScope**：OTel 原生，production-grade

---

## 5. Tune / Tuner（Agentic RL 微调）

源码：`src/agentscope/tune/_tune.py:16-97`

### tune() 接口

```python
def tune(
    *,
    workflow_func: WorkflowType,
    judge_func: JudgeType | None = None,
    train_dataset: DatasetConfig | None = None,
    eval_dataset: DatasetConfig | None = None,
    model: TunerModelConfig | None = None,
    ...
) -> None:
    """Train the agent workflow with the specific configuration."""
```

**思路**：
1. 用户提供一个 **agent workflow**（Python 函数）
2. AgentScope 在训练集上运行 workflow，收集 agent **trajectories**（reasoning + acting 序列）
3. `judge_func` 对 trajectory 打分
4. 用打分反馈训练/微调底层 LLM

### Trinity-RFT 集成

源码：`src/agentscope/tune/_tune.py:61-68`

```python
try:
    from trinity.cli.launcher import run_stage
    from trinity.utils.dlc_utils import setup_ray_cluster, stop_ray_cluster
except ImportError as e:
    raise ImportError(
        "Trinity-RFT is not installed. Please install it with "
        "`pip install trinity-rft`.",
    ) from e
```

**Trinity-RFT** 是阿里的 Reinforcement Fine-Tuning 框架，支持：
- 从 agent trajectories 反哺训练
- 分布式 GPU 训练（Ray cluster）
- 奖励模型（通过 `judge_func`）

### 在 6 款 framework 中的独特性

**AgentScope 是当前 6 款 framework 中唯一支持 "agentic RL fine-tuning" 的**。LangGraph/CrewAI/AG2/MAF/LangChain 都没有类似的一等公民抽象。

**潜在应用**：
- 用 /review agent 的 trajectory 微调 reviewer 能力
- 用多个 coding agent 的成功/失败 trajectory 改进 coder
- 构建**持续进化**的 agent（这接近 Hermes Agent 的"闭环学习"但走向不同：Hermes 是 in-context 学习，AgentScope 是 model weight 学习）

---

## 6. Realtime + TTS（实时语音 Agent）

源码：`src/agentscope/realtime/` + `src/agentscope/tts/`

### TTS 提供商

`src/agentscope/tts/__init__.py:1-9`

| Provider | 流式 | 说明 |
|---|---|---|
| **OpenAI TTS** | 否 | GPT-4o voice |
| **DashScope** | 是 | 阿里 |
| **Google Gemini** | 是 | Gemini audio |
| **DashScope CosyVoice** | 是 | 阿里自研 CosyVoice（中文最佳） |

### Realtime WebSocket

源码：`src/agentscope/realtime/_base.py:68-93`

```python
async def connect(
    self,
    outgoing_queue: Queue,
    instructions: str,
    tools: list[dict] | None = None,
) -> None:
    """Establish a connection to the realtime model."""
    import websockets

    self._websocket = await websockets.connect(
        self.websocket_url,
        additional_headers=self.websocket_headers,
    )
```

**支持的 Realtime 模型**：
- **OpenAI Realtime API**（GPT-4o Realtime）
- **DashScope Realtime**
- **Google Gemini Realtime**

### 完整 Voice Agent 数据流

```
用户语音 (microphone)
    │
    ▼
STT（realtime 模型内置，无独立 STT 模块）
    │
    ▼
ReActAgent.reply() 主循环
    │    ├─ reasoning → model（可能是 voice model）
    │    └─ acting → tool calls（响应 tool 结果）
    ▼
TTS 流式输出
    │
    ▼
Speaker（音频播放）
```

**对标**：
- **Kimi CLI** 有 voice 但只是 offline TTS
- **Hermes Agent** 有 `voice_mode` + faster-whisper 本地 STT + Edge TTS
- **AgentScope** 是**streaming realtime WebSocket**，延迟最低

---

## 7. Formatter（Per-Provider 格式化）

源码：`src/agentscope/formatter/`

每个 LLM Provider 一个 formatter，继承自 `FormatterBase`：

```python
class FormatterBase:
    @abstractmethod
    async def format(self, *args, **kwargs) -> list[dict[str, Any]]:
        """Format the Msg objects to a list of dictionaries that satisfy
        the API requirements."""
```

**7 个 formatter**：

| Formatter | Provider | 特殊处理 |
|---|---|---|
| `_openai_formatter.py` | OpenAI / Compatible | function calling |
| `_anthropic_formatter.py` | Anthropic | Claude tool use blocks |
| `_dashscope_formatter.py` | 阿里 | Qwen 特殊 schema |
| `_gemini_formatter.py` | Google | Gemini 格式 |
| `_deepseek_formatter.py` | DeepSeek | Reasoning model |
| `_ollama_formatter.py` | 本地 | 本地模型 |
| `_a2a_formatter.py` | Agent-to-Agent | 跨 Agent 消息格式 |

**对比**：
- **OpenCode** 有 100+ provider 通过 models.dev 动态加载
- **AgentScope** 7 个写死但覆盖主流

---

## 8. Session（持久化）

源码：`src/agentscope/session/_session_base.py:8`

```python
class SessionBase:
    """The base class for session in agentscope."""

    @abstractmethod
    async def save_session_state(
        self,
        session_id: str,
        user_id: str = "",
        **state_modules_mapping: StateModule,
    ) -> None:
        """Save the session state"""
```

**3 种 Backend**：
- **JSON 文件**（默认）
- **Redis**
- **TableStore**（阿里）

**用法**：

```python
session = JsonSession(save_dir="./sessions/")
await session.save_session_state(
    session_id="chat-42",
    agent=agent,
    toolkit=toolkit,
    memory=memory,
)
# 进程重启后
await session.load_session_state(session_id="chat-42", ...)
```

所有 `StateModule` 都自动可持久化。

---

## 9. Evaluate（任务评估）

源码：`src/agentscope/evaluate/`

### EvaluatorBase

源码：`src/agentscope/evaluate/_evaluator/_evaluator_base.py:18`

```python
class EvaluatorBase:
    """The class that runs the evaluation process."""

    def __init__(
        self,
        name: str,
        benchmark: BenchmarkBase,
        n_repeat: int,
        storage: EvaluatorStorageBase,
    ) -> None:
```

### Ray 并行

`pyproject.toml:145`

```python
evaluate = ["ray"]
```

用 Ray 分布式跑评估任务，支持大规模 benchmark（如 SWE-bench）。

### 架构

```
BenchmarkBase               # 定义任务集 + groundtruth
    │
    ▼
EvaluatorBase               # 运行 agent workflow × n_repeat
    │
    ├── 并行执行（Ray）
    ├── 指标聚合
    └── 持久化结果（EvaluatorStorageBase）
        │
        ▼
    SWE-bench / HumanEval / 自定义
```

**对标**：
- **SWE-agent** 内置 SWE-bench evaluation
- **AgentScope** 提供通用 evaluation 框架，可跑任何 benchmark

---

## 10. Pipeline（MsgHub 多 Agent）

源码：`src/agentscope/pipeline/_msghub.py:14`

```python
class MsgHub:
    """MsgHub class that controls the subscription of the participated agents."""
```

**唯一的多 Agent 原语**。没有像 LangGraph 那样的状态图，没有 CrewAI 的 role-based 结构——**就是一个广播消息总线**。

### 使用模式

```python
async with MsgHub(
    participants=[planner, coder, tester],
    announcement=Msg(name="user", content="让我们构建一个 TODO app"),
) as hub:
    # 每个 agent 回复都会自动广播给其他 agents
    reply1 = await planner()          # planner 产生计划
    reply2 = await coder()             # coder 看到计划，写代码
    reply3 = await tester()            # tester 看到代码，写测试
    reply4 = await coder()             # coder 看到测试结果，调整代码
```

**对比**：

| Framework | 多 Agent 风格 | 适用场景 |
|---|---|---|
| **AgentScope MsgHub** | 广播 | 松耦合讨论（头脑风暴、review） |
| **LangGraph** | 状态图 | 严格编排（已知流程） |
| **CrewAI** | Role hierarchy | 业务角色（策划→开发→测试） |
| **AG2 GroupChat** | Conversation | 自然对话模拟 |

---

## 其他模块（速览）

| 模块 | 作用 |
|---|---|
| `message/` | `Msg` 对象：content blocks + role + metadata |
| `module/` | `StateModule` 基类（可持久化） |
| `token/` | TokenCounterBase + 各 provider 实现 |
| `types/` | Pydantic 类型定义 |
| `hooks/` | Studio 集成 hook（连接到 AgentScope Studio GUI） |
| `exception/` | 异常类型 |
| `_utils/` | 内部工具 |

## 下一步

- 技术声明的源码引用 → [EVIDENCE.md](./EVIDENCE.md)
- 与其他 framework 对比 → [`../comparison.md`](../comparison.md)
