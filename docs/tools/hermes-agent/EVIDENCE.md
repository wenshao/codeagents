# Hermes Agent — EVIDENCE

> 本文档为本目录所有技术声明提供源码引用证据。所有引用基于 **`/root/git/hermes-agent`**（Hermes Agent 0.8.0，2026 年 4 月）。

## 证据组织

1. [代码规模与元数据](#1-代码规模与元数据)
2. [闭环学习系统 #1：持久 Memory](#2-闭环学习系统-1-持久-memory)
3. [闭环学习系统 #2：自主 Skill](#3-闭环学习系统-2-自主-skill)
4. [闭环学习系统 #3：跨会话 FTS5 搜索](#4-闭环学习系统-3-跨会话-fts5-搜索)
5. [闭环学习系统 #4：Nudge 计数器](#5-闭环学习系统-4-nudge-计数器)
6. [System Prompt 分层](#6-system-prompt-分层)
7. [Review 子代理](#7-review-子代理)
8. [Credential Pool](#8-credential-pool)
9. [6 种执行环境后端](#9-6-种执行环境后端)
10. [MCP 双向集成](#10-mcp-双向集成)
11. [消息渠道](#11-消息渠道)

---

## 1. 代码规模与元数据

### 1.1 Python 代码量

```bash
$ find /root/git/hermes-agent -name "*.py" | wc -l
822
$ find /root/git/hermes-agent -name "*.py" | xargs wc -l | tail -1
  369014 total
```

**声明**：Hermes Agent 共 **822 个 Python 文件 / 369,014 行代码**。

### 1.2 许可证与 Python 版本

`pyproject.toml:1-12`

```python
[project]
name = "hermes-agent"
version = "0.8.0"
description = "The self-improving AI agent — creates skills from experience, improves them during use, and runs anywhere"
readme = "README.md"
requires-python = ">=3.11"
authors = [{ name = "Nous Research" }]
license = { text = "MIT" }
```

**声明**：
- 版本：**0.8.0**
- 许可证：**MIT**
- Python：**>=3.11**
- 作者：**Nous Research**

### 1.3 核心依赖

`pyproject.toml:13-37`

```python
dependencies = [
  "openai>=2.21.0,<3",
  "anthropic>=0.39.0,<1",
  "python-dotenv>=1.2.1,<2",
  "fire>=0.7.1,<1",
  "httpx[socks]>=0.28.1,<1",
  "rich>=14.3.3,<15",
  "tenacity>=9.1.4,<10",
  "pyyaml>=6.0.2,<7",
  "requests>=2.33.0,<3",
  "jinja2>=3.1.5,<4",
  "pydantic>=2.12.5,<3",
  "prompt_toolkit>=3.0.52,<4",
  "exa-py>=2.9.0,<3",
  "firecrawl-py>=4.16.0,<5",
  ...
]
```

**声明**：Hermes 同时使用 **OpenAI SDK + Anthropic SDK 双栈**，UI 使用 `prompt_toolkit` + `rich`。

---

## 2. 闭环学习系统 #1：持久 Memory

### 2.1 Memory 目录

`tools/memory_tool.py:39-50`

```python
def get_memory_dir() -> Path:
    """Return the profile-scoped memories directory."""
    return get_hermes_home() / "memories"

# Backward-compatible alias — gateway/run.py imports this at runtime inside
# a function body, so it gets the correct snapshot for that process.
MEMORY_DIR = get_memory_dir()
```

**声明**：Memory 存储在 **`~/.hermes/memories/`** 目录。

### 2.2 条目分隔符

`tools/memory_tool.py:52`

```python
ENTRY_DELIMITER = "\n§\n"
```

**声明**：使用 **`§`**（章节符）作为条目分隔符。

### 2.3 ⭐ 冻结快照模式（核心设计）

`tools/memory_tool.py:1-24`

```python
"""
Both are injected into the system prompt as a frozen snapshot at session start.
Mid-session writes update files on disk immediately (durable) but do NOT change
the system prompt -- this preserves the prefix cache for the entire session.
The snapshot refreshes on the next session start.
"""
```

**声明**：
1. 会话开始时拍快照注入 system prompt
2. 会话中的 memory 写入**立刻落盘**（durable）
3. 会话中的 system prompt **完全不变**
4. **目的是保护整个会话的 prefix cache 命中率**
5. 下次会话才生效新快照

### 2.4 字符上限

`tools/skill_manager_tool.py:84-86`

```python
MAX_MEMORY_CONTENT_CHARS = 2_200_000  # Will be reduced in config validation
MAX_USER_CONTENT_CHARS = 1_375_000    # Will be reduced in config validation
```

**声明**：
- MEMORY.md 最大 **2,200,000 字符**
- USER.md 最大 **1,375,000 字符**
- 以字符数（非 token 数）作为上限

### 2.5 System Prompt 注入位置

`run_agent.py:3117-3126`

```python
if self._memory_store:
    if self._memory_enabled:
        mem_block = self._memory_store.format_for_system_prompt("memory")
        if mem_block:
            prompt_parts.append(mem_block)
    # USER.md is always included when enabled.
    if self._user_profile_enabled:
        user_block = self._memory_store.format_for_system_prompt("user")
        if user_block:
            prompt_parts.append(user_block)
```

**声明**：Memory 和 User Profile 分别独立注入。

---

## 3. 闭环学习系统 #2：自主 Skill

### 3.1 Skill 目录结构

`tools/skill_manager_tool.py:14-32`

```
Actions:
  create     -- Create a new skill (SKILL.md + directory structure)
  edit       -- Replace the SKILL.md content of a user skill (full rewrite)
  patch      -- Targeted find-and-replace within SKILL.md or any supporting file
  delete     -- Remove a user skill entirely
  write_file -- Add/overwrite a supporting file (reference, template, script, asset)
  remove_file-- Remove a supporting file from a user skill

Directory layout for user skills:
    ~/.hermes/skills/
    ├── my-skill/
    │   ├── SKILL.md
    │   ├── references/
    │   ├── templates/
    │   ├── scripts/
    │   └── assets/
```

**声明**：Skill 存储在 `~/.hermes/skills/<name>/` 目录，包含 SKILL.md + 4 个子目录。支持 6 种操作：create/edit/patch/delete/write_file/remove_file。

### 3.2 Skills Guidance（自改进指令）

`agent/prompt_builder.py:164-171`

```python
SKILLS_GUIDANCE = (
    "After completing a complex task (5+ tool calls), fixing a tricky error, "
    "or discovering a non-trivial workflow, save the approach as a "
    "skill with skill_manage so you can reuse it next time.\n"
    "When using a skill and finding it outdated, incomplete, or wrong, "
    "patch it immediately with skill_manage(action='patch') — don't wait to be asked. "
    "Skills that aren't maintained become liabilities."
)
```

**声明**：代理被明确指示"发现 skill 过时立即用 `patch` 动作修补，不等被要求"。

### 3.3 Review 子代理的审查 Prompt

`run_agent.py:2074-2079`

```python
"**Skills**: Was a non-trivial approach used to complete a task that required trial "
"and error, or changing course due to experiential findings along the way, or did "
"the user expect or desire a different method or outcome? If a relevant skill "
"already exists, update it. Otherwise, create a new one if the approach is reusable.\n\n"
"Only act if there's something genuinely worth saving. "
"If nothing stands out, just say 'Nothing to save.' and stop."
```

**声明**：Review 子代理只在"非平凡试错过程"出现时才沉淀 skill。保守原则。

---

## 4. 闭环学习系统 #3：跨会话 FTS5 搜索

### 4.1 SQLite 主表

`hermes_state.py:41-85`

```python
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    user_id TEXT,
    model TEXT,
    ...
);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL REFERENCES sessions(id),
    role TEXT NOT NULL,
    content TEXT,
    ...
);
```

### 4.2 FTS5 虚拟表

`hermes_state.py:93-110`

```python
FTS_SQL = """
CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts USING fts5(
    content,
    content=messages,
    content_rowid=id
);

CREATE TRIGGER IF NOT EXISTS messages_fts_insert AFTER INSERT ON messages BEGIN
    INSERT INTO messages_fts(rowid, content) VALUES (new.id, new.content);
END;
"""
```

**声明**：使用 SQLite 内建 FTS5 做本地全文索引，不依赖外部搜索服务。

### 4.3 搜索 + 摘要流程

`tools/session_search_tool.py:1-16`

```python
"""
Session Search Tool - Long-Term Conversation Recall

Searches past session transcripts in SQLite via FTS5, then summarizes the top
matching sessions using a cheap/fast model (same pattern as web_extract).
Returns focused summaries of past conversations rather than raw transcripts,
keeping the main model's context window clean.

Flow:
  1. FTS5 search finds matching messages ranked by relevance
  2. Groups by session, takes the top N unique sessions (default 3)
  3. Loads each session's conversation, truncates to ~100k chars centered on matches
  4. Sends to Gemini Flash with a focused summarization prompt
  5. Returns per-session summaries with metadata
"""
```

### 4.4 Gemini Flash 用于摘要

`tools/session_search_tool.py:257`

```python
"""Uses FTS5 to find matches, then summarizes the top sessions with Gemini Flash."""
```

**声明**：Summarization 使用 Gemini Flash（便宜快速的模型）。

---

## 5. 闭环学习系统 #4：Nudge 计数器

### 5.1 Memory Nudge 初始化

`run_agent.py:1114-1116`

```python
self._memory_nudge_interval = 10
self._memory_flush_min_turns = 6
self._turns_since_memory = 0
```

**声明**：默认 memory nudge 间隔 **10 轮用户回合**，最小 flush 回合数 6。

### 5.2 Skill Nudge 初始化

`run_agent.py:1117`

```python
self._iters_since_skill = 0
```

`run_agent.py:1214-1217`

```python
# Skills config: nudge interval for skill creation reminders
self._skill_nudge_interval = 10
try:
    skills_config = _agent_cfg.get("skills", {})
    self._skill_nudge_interval = int(skills_config.get("creation_nudge_interval", 10))
```

**声明**：
- Skill nudge 默认阈值 = **10 次工具调用**
- 可通过 `skills.creation_nudge_interval` 配置项覆盖

> **⚠️ 修正**：Issue #129 中写"15 次"是错的，源码实际是 **10**。

### 5.3 Skill 计数器递增

`run_agent.py:7885-7889`

```python
# Track tool-calling iterations for skill nudge.
# Counter resets whenever skill_manage is actually used.
if (self._skill_nudge_interval > 0
        and "skill_manage" in self.valid_tool_names):
    self._iters_since_skill += 1
```

### 5.4 Memory Nudge 触发

`run_agent.py:7642-7646`

```python
# Track memory nudge trigger (turn-based, checked here).
if (self._memory_nudge_interval > 0
    and self._turns_since_memory >= self._memory_nudge_interval
    and "memory" in self.valid_tool_names):
    _should_review_memory = True
```

### 5.5 Skill Nudge 触发

`run_agent.py:10165-10169`

```python
if (self._skill_nudge_interval > 0
        and self._iters_since_skill >= self._skill_nudge_interval
        and "skill_manage" in self.valid_tool_names):
    _should_review_skills = True
    self._iters_since_skill = 0
```

### 5.6 Memory 配置项

`run_agent.py:1120-1124`

```python
mem_config = _agent_cfg.get("memory", {})
self._memory_enabled = mem_config.get("memory_enabled", False)
self._user_profile_enabled = mem_config.get("user_profile_enabled", False)
self._memory_nudge_interval = int(mem_config.get("nudge_interval", 10))
self._memory_flush_min_turns = int(mem_config.get("flush_min_turns", 6))
```

**声明**：Memory 默认**未开启**（`memory_enabled: False`），需要用户主动在配置中启用。

---

## 6. System Prompt 分层

### 6.1 方法注释

`run_agent.py:3034-3050`

```python
def _build_system_prompt(self, system_message: str = None) -> str:
    """
    Assemble the full system prompt from all layers.
    
    Called once per session (cached on self._cached_system_prompt) and only
    rebuilt after context compression events. This ensures the system prompt
    is stable across all turns in a session, maximizing prefix cache hits.
    """
    # Layers (in order):
    #   1. Agent identity — SOUL.md when available, else DEFAULT_AGENT_IDENTITY
    #   2. User / gateway system prompt (if provided)
    #   3. Persistent memory (frozen snapshot)
    #   4. Skills guidance (if skills tools are loaded)
    #   5. Context files (AGENTS.md, .cursorrules — SOUL.md excluded here when used as identity)
    #   6. Current date & time (frozen at build time)
    #   7. Platform-specific formatting hint
```

**声明**：System Prompt 有 **7 层**装配顺序，一次构建、会话缓存。

### 6.2 Tool-Aware Guidance 条件注入

`run_agent.py:3063-3072`

```python
# Tool-aware behavioral guidance: only inject when the tools are loaded
tool_guidance = []
if "memory" in self.valid_tool_names:
    tool_guidance.append(MEMORY_GUIDANCE)
if "session_search" in self.valid_tool_names:
    tool_guidance.append(SESSION_SEARCH_GUIDANCE)
if "skill_manage" in self.valid_tool_names:
    tool_guidance.append(SKILLS_GUIDANCE)
if tool_guidance:
    prompt_parts.append(" ".join(tool_guidance))
```

**声明**：Guidance 文本只在对应工具加载时才注入，避免污染。

### 6.3 Ephemeral Prompt 分离

`run_agent.py:3112-3115`

```python
# Note: ephemeral_system_prompt is NOT included here. It's injected at
# API-call time only so it stays out of the cached/stored system prompt.
if system_message is not None:
    prompt_parts.append(system_message)
```

**声明**：Ephemeral prompt（实时动态上下文）不进入 cached system prompt。

---

## 7. Review 子代理

### 7.1 子代理创建

`run_agent.py:2112-2128`

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
review_agent._memory_nudge_interval = 0
review_agent._skill_nudge_interval = 0

review_agent.run_conversation(
    user_message=prompt,
    conversation_history=messages_snapshot,
)
```

**声明**：
- `max_iterations=8`
- `quiet_mode=True`
- 共享主代理的 memory_store
- `nudge_interval=0` 防止 review 子代理递归触发新 nudge

### 7.2 Post-Response 派发

`run_agent.py:10183-10191`

```python
# Background memory/skill review — runs AFTER the response is delivered
# so it never competes with the user's task for model attention.
if final_response and not interrupted and (_should_review_memory or _should_review_skills):
    try:
        self._spawn_background_review(
            messages_snapshot=list(messages),
            review_memory=_should_review_memory,
            review_skills=_should_review_skills,
        )
```

**声明**：Review 只在响应送出后启动，不与主任务竞争模型注意力。

### 7.3 用户侧消息

`run_agent.py:2160`

```python
self._safe_print(f"  💾 {summary}")
```

**声明**：用户侧看到的是一行简短 `💾` 消息。

---

## 8. Credential Pool

### 8.1 4 种选择策略

`agent/credential_pool.py:1-70`

```python
"""Persistent multi-credential pool for same-provider failover."""

STATUS_OK = "ok"
STATUS_EXHAUSTED = "exhausted"

STRATEGY_FILL_FIRST = "fill_first"
STRATEGY_ROUND_ROBIN = "round_robin"
STRATEGY_RANDOM = "random"
STRATEGY_LEAST_USED = "least_used"
SUPPORTED_POOL_STRATEGIES = {
    STRATEGY_FILL_FIRST,
    STRATEGY_ROUND_ROBIN,
    STRATEGY_RANDOM,
    STRATEGY_LEAST_USED,
}

# Cooldown before retrying an exhausted credential.
# 429 (rate-limited) and 402 (billing/quota) both cool down after 1 hour.
EXHAUSTED_TTL_429_SECONDS = 60 * 60          # 1 hour
EXHAUSTED_TTL_DEFAULT_SECONDS = 60 * 60      # 1 hour
```

**声明**：
- 4 种策略：fill_first / round_robin / random / least_used
- 429 / 402 错误冷却 **1 小时**

### 8.2 凭证数据结构

`agent/credential_pool.py:91-138`

```python
@dataclass
class PooledCredential:
    provider: str
    id: str
    label: str
    auth_type: str
    priority: int
    source: str
    access_token: str
    refresh_token: Optional[str] = None
    last_status: Optional[str] = None
    last_status_at: Optional[float] = None
    last_error_code: Optional[int] = None
    ...
    request_count: int = 0
```

---

## 9. 6 种执行环境后端

### 9.1 Base 接口

`tools/environments/base.py:1-80`

```python
"""Base class for all Hermes execution environment backends.

Unified spawn-per-call model: every command spawns a fresh ``bash -c`` process.
A session snapshot (env vars, functions, aliases) is captured once at init and
re-sourced before each command. CWD persists via in-band stdout markers (remote)
or a temp file (local).
"""
```

### 9.2 Daytona 持久 Sandbox

`tools/environments/daytona.py:75-87`

```python
if self._persistent:
    try:
        self._sandbox = self._daytona.get(sandbox_name)
        self._sandbox.start()
        logger.info("Daytona: resumed sandbox %s for task %s",
                    self._sandbox.id, task_id)
    except DaytonaError:
        self._sandbox = None
```

### 9.3 Modal 快照

`tools/environments/modal.py:25-72`

```python
_SNAPSHOT_STORE = get_hermes_home() / "modal_snapshots.json"

def _load_snapshots() -> dict:
    return _load_json_store(_SNAPSHOT_STORE)

def _save_snapshots(data: dict) -> None:
    _save_json_store(_SNAPSHOT_STORE, data)
```

**6 个后端文件清单**（`tools/environments/`）：

1. `local.py`
2. `docker.py`
3. `ssh.py`
4. `daytona.py`
5. `modal.py`
6. `singularity.py`

---

## 10. MCP 双向集成

### 10.1 MCP Client

`tools/mcp_tool.py:1-60`

```python
"""
MCP (Model Context Protocol) Client Support

Connects to external MCP servers via stdio or HTTP/StreamableHTTP transport,
discovers their tools, and registers them into the hermes-agent tool registry
so the agent can call them like any built-in tool.
"""
```

### 10.2 MCP Server

`mcp_serve.py:1-28`

```python
"""
Hermes MCP Server — expose messaging conversations as MCP tools.

Starts a stdio MCP server that lets any MCP client (Claude Code, Cursor, Codex,
etc.) list conversations, read message history, send messages, poll for live
events, and manage approval requests across all connected platforms.

Matches OpenClaw's 9-tool MCP channel bridge surface:
  conversations_list, conversation_get, messages_read, attachments_fetch,
  events_poll, events_wait, messages_send, permissions_list_open,
  permissions_respond

Plus: channels_list (Hermes-specific extra)
"""
```

**声明**：
- 9 个 OpenClaw 兼容工具 + 1 个 channels_list
- 支持 stdio transport

---

## 11. 消息渠道

`gateway/` 目录文件列表（14 个）：

1. `cli.py`（CLI）
2. `telegram.py`
3. `discord.py`
4. `slack.py`
5. `whatsapp.py`
6. `signal.py`
7. `matrix.py`
8. `email.py`
9. `sms.py`
10. `weixin.py`
11. `wecom.py`
12. `dingtalk.py`
13. `feishu.py`
14. `mattermost.py`
15. `bluebubbles.py`
16. `homeassistant.py`

**总计**：至少 **14 个主要渠道** + 部分辅助（homeassistant / bluebubbles 较小众）。

README 官方列表（`README.md:20`）：

```
Telegram, Discord, Slack, WhatsApp, Signal, and CLI
```

（README 只列了 6 个主要渠道，源码中还有更多）。

---

## 版本信息

**分析版本**：Hermes Agent 0.8.0（2026 年 4 月）
**源码位置**：`/root/git/hermes-agent`
**分析日期**：2026-04-13
