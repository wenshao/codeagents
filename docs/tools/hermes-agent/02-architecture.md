# Hermes Agent — 架构

## 源码规模

```
822 个 .py 文件 / 369,014 行 Python
```

相比：

| Agent | 语言 | 代码量 |
|---|---|---|
| Claude Code | Rust | ~512K 行 |
| Qwen Code | TypeScript | ~439K 行 |
| Gemini CLI | TypeScript | ~191K 行 |
| **Hermes Agent** | **Python** | **369K 行** |
| OpenHands | Python | ~60K 行 |
| Aider | Python | ~30K 行 |
| Kimi CLI | Python | ~20K 行 |

Hermes 是 codeagents 矩阵中**最大的 Python 代码库**。

## 顶层目录

```
hermes-agent/
├── agent/                 # 核心代理逻辑（prompt_builder、credential_pool、auxiliary_client）
├── hermes/                # 消息渠道路由、会话状态机
├── hermes_cli/            # CLI 入口
├── gateway/               # 外部渠道适配器
├── tools/                 # 28+ 内置工具
│   └── environments/      # 6 种执行环境后端
├── acp_adapter/           # Agent Client Protocol 适配器
├── acp_registry/          # ACP 注册表
├── cron/                  # 定时任务系统
├── docker/                # Docker 镜像配置
├── mcp_serve.py           # MCP Server 入口（将 Hermes 暴露为 MCP）
├── run_agent.py           # ⭐ 主代理循环（~10000 行）
├── hermes_state.py        # SQLite + FTS5 状态存储
├── model_tools.py         # 模型元数据工具
├── batch_runner.py        # 批量运行器
└── mini_swe_runner.py     # SWE-bench 评估适配器
```

## 核心主循环：`run_agent.py`

Hermes 的核心代理循环集中在 **`run_agent.py`**（超过 10000 行），包含 `AIAgent` 类。关键方法：

| 方法 | 行号范围 | 职责 |
|---|---|---|
| `_build_system_prompt` | 3034-3115 | 装配多层 System Prompt（一次性，会话缓存） |
| `run_conversation` | — | 主对话循环 |
| `_spawn_background_review` | 2100-2160 | 启动后台 review 子代理（Memory/Skill 闭环核心） |
| 计数器增量 | 7885-7889 | `_iters_since_skill` 每次工具调用 +1 |
| Memory Nudge 触发 | 7642-7646 | 用户回合数达到阈值 → 标记需要 review |
| Skill Nudge 触发 | 10165-10169 | 工具调用数达到阈值 → 标记需要 review |
| 后台 review 派发 | 10183-10191 | 响应送出后异步启动 review 子代理 |

## System Prompt 分层架构

源码：`run_agent.py:3034-3115`

**7 层装配顺序**：

```
1. Agent 身份       SOUL.md（如有）否则 DEFAULT_AGENT_IDENTITY
2. 用户/渠道 Prompt  来自调用方（gateway）
3. 持久 Memory      MEMORY.md + USER.md 冻结快照 🔒
4. Skills Guidance  SKILLS_GUIDANCE 文本（若 skill_manage 工具加载）
5. 上下文文件       AGENTS.md / .cursorrules（SOUL.md 排除）
6. 当前日期时间     构建时冻结
7. 平台格式提示     针对当前渠道（Telegram/CLI/Slack）的输出约定
```

### 关键设计：一次构建、会话缓存

```python
"""
Assemble the full system prompt from all layers.

Called once per session (cached on self._cached_system_prompt) and only
rebuilt after context compression events. This ensures the system prompt
is stable across all turns in a session, maximizing prefix cache hits.
"""
```

**目的**：最大化 Anthropic/OpenAI 的 **prefix prompt cache**。System Prompt 稳定 → 每次 API 调用的前缀都命中缓存 → 既省钱又快。

### Tool-Aware Guidance 注入

```python
# Tool-aware behavioral guidance: only inject when the tools are loaded
tool_guidance = []
if "memory" in self.valid_tool_names:
    tool_guidance.append(MEMORY_GUIDANCE)
if "session_search" in self.valid_tool_names:
    tool_guidance.append(SESSION_SEARCH_GUIDANCE)
if "skill_manage" in self.valid_tool_names:
    tool_guidance.append(SKILLS_GUIDANCE)
```

**只在对应工具加载时才注入对应的 guidance 文本** —— 避免无关指令污染 context。这是许多 Agent 都缺失的节约手段。

### Ephemeral vs. Persistent Prompt 分离

```python
# Note: ephemeral_system_prompt is NOT included here. It's injected at
# API-call time only so it stays out of the cached/stored system prompt.
if system_message is not None:
    prompt_parts.append(system_message)
```

**Ephemeral Prompt**（实时上下文、运行时状态）在 **API 调用时才注入**，不会进入会话缓存。这种分离避免了"一次实时变化就让整个 prompt cache 失效"的昂贵问题。

## Review 子代理：后台异步隔离

源码：`run_agent.py:2112-2128`

```python
review_agent = AIAgent(
    model=self.model,
    max_iterations=8,
    quiet_mode=True,
    platform=self.platform,
    provider=self.provider,
)
review_agent._memory_store = self._memory_store
review_agent._memory_enabled = self._memory_enabled
review_agent._user_profile_enabled = self._user_profile_enabled
review_agent._memory_nudge_interval = 0  # 关键：review 子代理不递归触发 nudge
review_agent._skill_nudge_interval = 0

review_agent.run_conversation(
    user_message=prompt,
    conversation_history=messages_snapshot,
)
```

**关键点**：

1. **共享 memory store** — review 子代理和主代理操作同一份 memory/skill 存储
2. **max_iterations=8** — 严格限制，不会无限递归
3. **quiet_mode=True** — 不污染用户的输出窗口
4. **nudge_interval=0** — review 子代理自己不触发新的 review（防递归）
5. **post-turn 派发** — 只在主响应送出后才启动（`run_agent.py:10183-10191`）：
   ```python
   # Background memory/skill review — runs AFTER the response is delivered
   # so it never competes with the user's task for model attention.
   if final_response and not interrupted and (_should_review_memory or _should_review_skills):
       self._spawn_background_review(...)
   ```

## 数据流全景

```
┌─────────────────────────────────────────────────────────────────────┐
│  用户输入 (CLI / Telegram / Discord / ... 14 个渠道)                │
└──────────────────────┬──────────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Pre-turn                                                            │
│   ├─ 从 memory store 预取上下文（冻结快照已在 system prompt 里）   │
│   └─ 从 Honcho 等外部 provider 拉取动态 context（ephemeral prompt）│
└──────────────────────┬──────────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────────┐
│  API 调用 (OpenAI / Anthropic / OpenRouter / ...)                    │
│   System prompt 前缀命中 cache ⚡                                     │
└──────────────────────┬──────────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────────┐
│  工具执行                                                            │
│   ├─ _iters_since_skill += 1                                         │
│   └─ 若调用 memory / skill_manage → 重置计数器                       │
└──────────────────────┬──────────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Post-turn Nudge 检查                                                │
│   ├─ turns_since_memory ≥ 10  → should_review_memory = True          │
│   └─ iters_since_skill ≥ 10   → should_review_skills = True          │
└──────────────────────┬──────────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────────┐
│  响应送回用户                                                        │
└──────────────────────┬──────────────────────────────────────────────┘
                       │
                       ▼ (异步，不阻塞用户)
┌─────────────────────────────────────────────────────────────────────┐
│  后台 Review 子代理 (max_iter=8, quiet=True)                         │
│   ├─ 审查对话                                                        │
│   ├─ memory.add / skill_manage.create / skill_manage.patch           │
│   └─ 用户侧输出一行 "💾 Skill 'parse-csv' created · Memory updated" │
└─────────────────────────────────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────────┐
│  会话结束                                                            │
│   消息写入 SQLite + FTS5 索引 → 下次可跨会话搜索                     │
└─────────────────────────────────────────────────────────────────────┘
```

## 关键技术选型对照

| 维度 | Hermes | Claude Code | Qwen Code |
|---|---|---|---|
| **语言** | Python >=3.11 | Rust | TypeScript |
| **核心依赖** | OpenAI SDK + Anthropic SDK 双栈 | 自研 Rust | @google/genai SDK |
| **状态存储** | SQLite + FTS5（本地） | Anthropic 服务器侧 session | 本地 JSONL |
| **异步模式** | asyncio + threads（后台 review） | Tokio（Rust） | Node.js EventLoop |
| **UI** | `prompt_toolkit` + `rich` | Ink/React TUI（Rust） | Ink/React TUI |
| **多渠道** | 14 个 gateway 适配器 | CLI + IDE | CLI + VS Code |

## 下一步

- 闭环学习的详细机制 → [03-closed-learning-loop.md](./03-closed-learning-loop.md)
- 所有工具和渠道 → [04-tools-channels.md](./04-tools-channels.md)
- 技术声明的源码引用 → [EVIDENCE.md](./EVIDENCE.md)
