# Hermes Agent — 闭环学习系统（Closed Learning Loop）

> 这是 Hermes Agent 的**核心创新**，也是它和另外 18 款 Code Agent 最本质的差异。

闭环学习由**四个子系统**构成，每一个都可以独立存在，但组合起来才形成真正的"经验 → 存储 → 召回 → 改进"循环：

1. **持久 Memory（事实记忆）** — 冻结快照模式保护 prompt cache
2. **自主 Skill 创建与自我改进** — 计数器驱动的后台 review 子代理
3. **跨会话搜索** — SQLite FTS5 + Gemini Flash 摘要
4. **主动 Nudge 机制** — 两个独立计数器作为闭环"引擎"

---

## 1. 持久 Memory：冻结快照模式

### 存储位置

源码：`tools/memory_tool.py:39-50`

```python
def get_memory_dir() -> Path:
    """Return the profile-scoped memories directory."""
    return get_hermes_home() / "memories"
```

实际路径：**`~/.hermes/memories/`**，包含两个 Markdown 文件：

- **`MEMORY.md`** — 代理自己的观察（环境/技术发现、工具怪癖、学到的约定）
- **`USER.md`** — 用户画像（偏好、沟通风格、工作习惯、个人事实）

### 条目分隔符

源码：`tools/memory_tool.py:52`

```python
ENTRY_DELIMITER = "\n§\n"
```

使用 **§**（章节符）作为分隔符，避免与普通 Markdown 标题冲突。

### 字符上限（模型无关）

源码：`tools/skill_manager_tool.py:84-86`

```python
MAX_MEMORY_CONTENT_CHARS = 2_200_000  # Will be reduced in config validation
MAX_USER_CONTENT_CHARS = 1_375_000    # Will be reduced in config validation
```

以 **字符数**（非 token 数）设上限，避免不同 tokenizer 的差异。

### ⭐ 冻结快照模式：保护 Prompt Cache

这是 Hermes 最讲究的一个设计细节，**直接引用源码注释**（`tools/memory_tool.py:11-14`）：

```python
"""
Both are injected into the system prompt as a frozen snapshot at session start.
Mid-session writes update files on disk immediately (durable) but do NOT change
the system prompt -- this preserves the prefix cache for the entire session.
The snapshot refreshes on the next session start.
"""
```

**分层含义**：

| 阶段 | 行为 |
|---|---|
| 会话开始 | 读 `~/.hermes/memories/MEMORY.md` + `USER.md` → 注入 system prompt → 缓存为 `self._cached_system_prompt` |
| 会话中（每次工具调用） | `memory.add` / `memory.update` 立刻写盘（durable） |
| 会话中（system prompt） | **完全不变** —— 即使刚写了新 memory |
| 下次会话开始 | 重新读取 → 新 snapshot → 下次会话才生效 |

**为什么要这么做**：Anthropic 的 prefix prompt cache 对"前缀完全一致"极度敏感。任何一次 system prompt 改动都会让整个 cache 失效，下一次 API 调用要按**未缓存的完整前缀价格**重新计费（Anthropic 的 cache write 比普通 input token 贵，但后续 cache read 只要 1/10 价格）。

Hermes 选择**牺牲"本次会话立即召回新 memory"**以换取**整个会话 cache 命中率 100%**。

### System Prompt 注入位置

源码：`run_agent.py:3117-3126`

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

这段代码在 `_build_system_prompt` 内部，该方法有明确注释：

```python
"""
Assemble the full system prompt from all layers.

Called once per session (cached on self._cached_system_prompt) and only
rebuilt after context compression events.
"""
```

---

## 2. 自主 Skill 创建与自我改进

### Skill 是什么

Skill = **`~/.hermes/skills/<name>/SKILL.md`** 文件，包含 YAML frontmatter + Markdown 指令，本质是**可复用的程序性知识**。

源码：`tools/skill_manager_tool.py:14-32`

```
Directory layout for user skills:
    ~/.hermes/skills/
    ├── my-skill/
    │   ├── SKILL.md
    │   ├── references/
    │   ├── templates/
    │   ├── scripts/
    │   └── assets/
```

### 工具操作

同文件：

```
Actions:
  create     -- Create a new skill (SKILL.md + directory structure)
  edit       -- Replace the SKILL.md content of a user skill (full rewrite)
  patch      -- Targeted find-and-replace within SKILL.md or any supporting file
  delete     -- Remove a user skill entirely
  write_file -- Add/overwrite a supporting file (reference, template, script, asset)
  remove_file -- Remove a supporting file from a user skill
```

**关键**：`patch` 动作支持精确的 find-and-replace，让代理可以**原地修补 skill** 而不重写整个文件。

### ⭐ 迭代计数器：`_iters_since_skill`

源码：`run_agent.py:1117`

```python
self._iters_since_skill = 0
```

阈值配置：`run_agent.py:1214-1217`

```python
# Skills config: nudge interval for skill creation reminders
self._skill_nudge_interval = 10
try:
    skills_config = _agent_cfg.get("skills", {})
    self._skill_nudge_interval = int(skills_config.get("creation_nudge_interval", 10))
```

**默认阈值 = 10 次工具调用**（可通过 `skills.creation_nudge_interval` 配置项覆盖）。

> **注意**：这和社区讨论（包括 Issue #129）中常说的 "15 次" 不同——源码实际默认是 **10**。本文档以源码为准。

### 计数器递增

源码：`run_agent.py:7885-7889`

```python
# Track tool-calling iterations for skill nudge.
# Counter resets whenever skill_manage is actually used.
if (self._skill_nudge_interval > 0
        and "skill_manage" in self.valid_tool_names):
    self._iters_since_skill += 1
```

每次工具调用都 `+1`，但如果这次工具调用本身就是 `skill_manage`，计数器会**立即重置**（"我刚管理过技能，不需要再 nudge 我"）。

### 触发条件

源码：`run_agent.py:10165-10169`

```python
if (self._skill_nudge_interval > 0
        and self._iters_since_skill >= self._skill_nudge_interval
        and "skill_manage" in self.valid_tool_names):
    _should_review_skills = True
    self._iters_since_skill = 0
```

### Review 子代理的审查 Prompt

源码：`run_agent.py:2074-2079`

```python
"**Skills**: Was a non-trivial approach used to complete a task that required trial "
"and error, or changing course due to experiential findings along the way, or did "
"the user expect or desire a different method or outcome? If a relevant skill "
"already exists, update it. Otherwise, create a new one if the approach is reusable.\n\n"
"Only act if there's something genuinely worth saving. "
"If nothing stands out, just say 'Nothing to save.' and stop."
```

**关键词**：
- `non-trivial approach` — 平凡的操作不值得沉淀
- `trial and error` — 有试错痕迹才算经验
- `changing course due to experiential findings` — 中途调整才算学习
- `Only act if there's something genuinely worth saving` — **保守原则**，防止 skill 库被垃圾填满
- `Nothing to save.` — 允许 review 子代理"空手而归"

### Skills Guidance：注入给主代理的自我改进指令

源码：`agent/prompt_builder.py:164-171`

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

**闭环的关键句**："**patch it immediately with skill_manage(action='patch') — don't wait to be asked.**"

—— 代理在使用 skill 时如果发现它过时 / 错误 / 不完整，**立即就地修补**，不等用户说。

这是 **Skill 自改进** 的核心机制，也是"闭环"的"改进"环节。

---

## 3. 跨会话搜索：SQLite FTS5 + LLM 摘要

### SQLite 架构

源码：`hermes_state.py:36-110`

主表 `messages`：

```sql
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL REFERENCES sessions(id),
    role TEXT NOT NULL,
    content TEXT,
    ...
);
```

FTS5 虚拟表和触发器（`hermes_state.py:93-110`）：

```sql
CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts USING fts5(
    content,
    content=messages,
    content_rowid=id
);

CREATE TRIGGER IF NOT EXISTS messages_fts_insert AFTER INSERT ON messages BEGIN
    INSERT INTO messages_fts(rowid, content) VALUES (new.id, new.content);
END;
```

**这是本地 FTS5 全文索引，不依赖任何外部服务**。每条消息插入 `messages` 表时，触发器自动同步到 `messages_fts`。

### 搜索和摘要流程

源码：`tools/session_search_tool.py:1-16`

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

**5 步流程**：

1. FTS5 BM25 排序找到相关消息
2. 按 session 分组，取 top-N 去重会话（默认 3）
3. 加载每个会话的完整对话，**以匹配点为中心**截断到约 100K 字符
4. 发给 **Gemini Flash**（便宜快速）做聚焦摘要
5. 返回精简摘要而非原始 transcript —— 保护主代理的 context window

### 为什么用 Gemini Flash 摘要？

- **便宜**：Gemini Flash 是当前价格最低的一档模型（~$0.075/1M tokens input）
- **快速**：延迟极低
- **足够**：摘要是"从海量文本里提取相关段落"，不需要 frontier 模型的推理

源码：`tools/session_search_tool.py:257`

```python
"""Uses FTS5 to find matches, then summarizes the top sessions with Gemini Flash."""
```

---

## 4. 主动 Nudge 机制：闭环的"引擎"

**这是整个闭环的驱动力**：代理不需要用户指示"记住这个"或"保存为技能"，它会定期自我审视对话。

### 两个独立计数器

源码：`run_agent.py:1114-1116`

```python
self._memory_nudge_interval = 10
self._memory_flush_min_turns = 6
self._turns_since_memory = 0
```

| 触发器 | 计数单位 | 默认阈值 | 触发后行为 |
|--------|---------|---------|-----------|
| **Memory Nudge** | 用户回合数 | **10 轮** | 后台子代理审查对话，提取用户偏好/事实 → `memory.add` |
| **Skill Nudge** | 工具调用次数 | **10 次** | 后台子代理审查对话，决定是否 `skill_manage(create/edit/patch)` |

### 配置项

源码：`run_agent.py:1120-1124`

```python
mem_config = _agent_cfg.get("memory", {})
self._memory_enabled = mem_config.get("memory_enabled", False)
self._user_profile_enabled = mem_config.get("user_profile_enabled", False)
self._memory_nudge_interval = int(mem_config.get("nudge_interval", 10))
self._memory_flush_min_turns = int(mem_config.get("flush_min_turns", 6))
```

**可通过配置文件自定义**：
- `memory.memory_enabled` — 是否开启 memory 系统
- `memory.user_profile_enabled` — 是否维护 USER.md
- `memory.nudge_interval` — memory nudge 间隔（默认 10 轮）
- `memory.flush_min_turns` — 最小 flush 回合数（默认 6）
- `skills.creation_nudge_interval` — skill nudge 间隔（默认 10）

### Nudge 后的派发（关键：post-response）

源码：`run_agent.py:10183-10191`

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

**核心原则**："**runs AFTER the response is delivered so it never competes with the user's task for model attention.**"

即：review 子代理**绝不和主代理抢注意力**。用户的任务永远优先，review 永远后台。

### 用户侧反馈

源码：`run_agent.py:2160`

```python
self._safe_print(f"  💾 {summary}")
```

典型输出：

```
  💾 Skill 'parse-csv' created · Memory updated
```

**简洁到一行**，不打断用户的工作流，但让用户知道"学习在发生"。

---

## 数据流全景（闭环版）

```
 ┌───────────────────────────────────────────────────────────────────┐
 │  用户输入                                                         │
 └────────────────┬──────────────────────────────────────────────────┘
                  │
         ┌────────┴────────┐
         │                 │
         ▼                 ▼
  ┌──────────────┐   ┌──────────────┐
  │ Memory 快照  │   │ Session 消息 │  
  │ 已在 system  │   │ 存入 SQLite  │◀───┐
  │ prompt 里 🔒 │   │ + FTS5 索引  │    │
  └──────┬───────┘   └──────────────┘    │
         │                               │
         ▼                               │
  ┌──────────────────────────────┐       │
  │  API 调用                     │       │
  │  System Prompt Cache 命中 ⚡   │       │
  └──────────────┬───────────────┘       │
                 │                       │
                 ▼                       │
  ┌──────────────────────────────┐       │
  │  工具执行                     │       │
  │  ├─ _iters_since_skill += 1   │       │
  │  └─ _turns_since_memory += 1  │       │
  └──────────────┬───────────────┘       │
                 │                       │
                 ▼                       │
  ┌──────────────────────────────┐       │
  │  响应送回用户 ✅               │       │
  └──────────────┬───────────────┘       │
                 │                       │
                 ▼                       │
  ┌──────────────────────────────┐       │
  │  检查 Nudge 阈值              │       │
  │  ≥10 轮 or ≥10 次？           │       │
  └──────┬───────────────────────┘       │
         │ 达标                          │
         ▼                               │
  ┌──────────────────────────────┐       │
  │  后台 Review 子代理 (异步)    │       │
  │  max_iter=8, quiet=True      │       │
  │  ├─ 审查对话                  │       │
  │  ├─ memory.add ───────┐       │       │
  │  └─ skill_manage      │       │       │
  │     .create/.patch ───┤       │       │
  └─────────────────┬─────┘       │       │
                    │             │       │
                    │       ┌─────┘       │
                    │       │             │
                    ▼       ▼             │
              ┌────────────────┐          │
              │ MEMORY.md      │          │
              │ USER.md        │          │
              │ SKILL.md       │          │
              │ (disk persist) │          │
              └────────┬───────┘          │
                       │                  │
                       │    下次会话      │
                       │    重新 snapshot │
                       └──────────────────┘
```

---

## 和其他 Agent 的"类似概念"比对

| Agent | 类似机制 | 是否"闭环" |
|---|---|---|
| **Claude Code** Kairos（Always-On） | 周期性运行 agent，能记忆对话，但 memory 是 Anthropic 服务器管理 | ⚠️ 部分（无本地 FTS5 搜索） |
| **Claude Code** Auto-Memory | v2.1+ 的 auto-memory 系统，自动写 memory | ⚠️ 部分（无主动 nudge 机制，依赖 Anthropic 后端） |
| **Qwen Code PR #3087** | `managed auto-memory + auto-dream`（LaZzyMan 提交，正在 review） | ⚠️ 开发中 |
| **Qwen Code PR #3006** | `microcompaction for idle context cleanup`（tanzhenxin 提交） | ⚠️ 仅清理不学习 |
| **Cursor Memories** | Cursor IDE 的 memory 功能 | ⚠️ 部分（不开源，无 nudge） |
| **Aider** | `.aider.chat.history.md` + RepoMap PageRank | ❌ 是 "记住历史"，不是 "自主学习" |
| **OpenCode Skills** | 用户手动定义 skill | ❌ 手工管理 |
| **Hermes** | **4 个子系统完整闭环 + 后台 review + patch 自改进** | ✅ **原生完整闭环** |

详细对比见 [`closed-learning-loop-deep-dive.md`](../../comparison/closed-learning-loop-deep-dive.md)。

## 可借鉴点（给 Qwen Code / 其他 Agent）

1. **Prompt Cache 保护的冻结快照模式** —— 即使实现了 auto-memory，也要注意不要每次 memory 变动就重建 system prompt
2. **Post-response 后台 review** —— 不和主任务抢模型注意力
3. **双计数器驱动** —— 用户回合数和工具调用数分开计数，分别管理 memory 和 skill
4. **保守的审查 prompt** —— "Nothing to save." 允许空手而归，防止 skill 库被垃圾填满
5. **`patch` 动作** —— Skill 发现过时立即自修补，不等用户
6. **FTS5 本地全文索引** —— 不依赖外部服务、无隐私顾虑、延迟极低
7. **Gemini Flash 做摘要** —— 便宜快速，把 frontier 模型留给主任务

## 下一步

- 横向对比 Claude Code / Qwen Code / Cursor → [`closed-learning-loop-deep-dive.md`](../../comparison/closed-learning-loop-deep-dive.md)
- 技术声明的源码引用 → [EVIDENCE.md](./EVIDENCE.md)
