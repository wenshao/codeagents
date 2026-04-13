# 闭环学习系统深度对比（Closed Learning Loop Deep-Dive）

> "经验 → 存储 → 召回 → 改进" —— 代理是否能**自主地、持续地**从对话中学习，而不需要用户明确指示？

**比较对象**：Hermes Agent、Claude Code（Auto-Memory + Kairos）、Qwen Code（PR #3087/#3006）、Codex CLI、Cursor、Aider、Gemini CLI、OpenCode

---

## 为什么需要"闭环"？

传统 Code Agent 的"记忆"通常是被动的：

- 用户手写 `CLAUDE.md` / `AGENTS.md` / `.cursorrules`
- Agent 只读不写
- 或者 Agent 可以写，但**必须用户明确说"记住这个"**
- 跨会话回忆依赖 `/resume` 或最近一次会话的状态

这些都是**半闭环**：经验可以被存储，但不能被**主动发现**和**主动沉淀**。

**完整闭环**的要求：

1. **经验**：从正常对话中识别"值得学习"的瞬间（不依赖用户指示）
2. **存储**：把经验持久化到本地 / 云 / 外部 provider
3. **召回**：在未来对话中自动找到相关的过去经验
4. **改进**：发现存储的经验过时 / 错误时主动修补

当前 19 款 Code Agent 中，**只有 Hermes Agent 在所有 4 个环节都具备原生实现**。

---

## 横向对比矩阵

| Agent | 经验识别 | 存储机制 | 召回机制 | 自主改进 | 闭环等级 |
|---|---|---|---|---|---|
| **Hermes Agent** | ✅ 双计数器 Nudge | ✅ `~/.hermes/memories/` + `~/.hermes/skills/` | ✅ SQLite FTS5 全文搜索 + Gemini Flash 摘要 | ✅ `skill_manage(patch)` 自动修补 | 🟢 **完整闭环** |
| **Claude Code v2.1+** | ⚠️ Auto-Memory（被动：看到显式偏好就存） | ✅ `~/.claude/projects/<hash>/memory/*.md` | ⚠️ 仅加载当前项目 memory | ❌ 用户手工编辑 | 🟡 半闭环 |
| **Claude Code Kairos** | ⚠️ Always-On 周期性运行 | ✅ Anthropic 服务器侧 session | ⚠️ 跨会话需用户手工拉取 | ❌ 用户手工 | 🟡 半闭环 |
| **Codex CLI** | ✅ `generate_memories` + `consolidation_model` | ✅ `AGENTS.md` 分层 | ⚠️ 仅当前项目 | ⚠️ 去重但不修补 | 🟡 半闭环 |
| **Qwen Code PR #3087** | 🚧 `managed auto-memory` 开发中 | 🚧 `~/.qwen/memories/` | 🚧 未定 | ❌ 未实现 | 🔴 开发中 |
| **Qwen Code PR #3006** | 🚧 `microcompaction` 空闲时清理 | - | - | - | 🔴 仅清理 |
| **Qwen Code 现状** | ⚠️ `save_memory` 工具（被动） | ✅ `QWEN.md` | ⚠️ 仅项目内 | ❌ | 🔴 开环 |
| **Gemini CLI** | ⚠️ `memory_manager` 子代理（手工触发） | ✅ `GEMINI.md` | ⚠️ 仅项目内 | ❌ | 🔴 开环 |
| **Qoder CLI** | ⚠️ LLM 驱动记忆更新（session 级） | ✅ `AGENTS.md` + `CLAUDE.md` | ⚠️ 项目内 | ❌ | 🟡 半闭环 |
| **Cursor** | ⚠️ Cursor Memories（不开源） | ⚠️ 服务器侧 | ⚠️ 未知 | ❌ | 🟡 半闭环 |
| **Aider** | ❌ | ✅ `.aider.chat.history.md` + RepoMap PageRank | ⚠️ 仅仓库内 | ❌ | 🔴 无学习 |
| **OpenCode** | ❌ | ✅ `AGENTS.md` + `CLAUDE.md` + `CONTEXT.md` | ⚠️ 项目内 | ❌ | 🔴 开环 |
| **Kimi CLI** | ❌ | ⚠️ `AGENTS.md` 1 层 | ❌ | ❌ | 🔴 无记忆 |

**图例**：
- 🟢 完整闭环
- 🟡 半闭环（缺一到两个环节）
- 🔴 开环（被动记忆）
- ✅ 完整实现 / ⚠️ 部分实现 / 🚧 开发中 / ❌ 未实现

---

## 一、经验识别：什么触发了"学习"

### Hermes：双计数器 Nudge（主动）

源码：`run_agent.py:1114-1117`、`run_agent.py:1214`

```python
self._memory_nudge_interval = 10     # 用户回合数
self._iters_since_skill = 0           # 工具调用次数
self._skill_nudge_interval = 10
```

**触发逻辑**：
- 用户回合数 ≥ 10 → 触发 **memory review**（审查对话、提取用户偏好/事实）
- 工具调用次数 ≥ 10 → 触发 **skill review**（审查对话、决定是否创建/修补 skill）
- **独立计数**：memory 和 skill 两个计数器独立递增、独立重置

**主动性**：代理在后台定期**自发**审视对话，用户无需明确指示"记住这个"。

### Claude Code Auto-Memory：基于系统提示的启发式

Claude Code 的 auto-memory 系统在 system prompt 中定义了 4 种记忆类型（user / feedback / project / reference），代理在正常对话中**如果识别到匹配的信号**就触发 memory 写入：

```
# auto memory
You have a persistent, file-based memory system...
When you learn any details about the user's role, preferences, ...
```

**被动性**：没有计数器驱动的"周期性自我审视"，依赖代理在每个 turn 中自发判断是否有值得记录的内容。这意味着长对话里容易漏掉重要的学习机会。

### Codex CLI：`generate_memories` + `consolidation_model`

Codex CLI 使用双模型：
- `extract_model` 从对话中抽取 memory 候选
- `consolidation_model` 把候选合并去重

**触发时机**：会话结束时（或用户主动触发 `/memory` 命令）。

**对比**：Codex 的抽取是**会话末端**一次性的，而 Hermes 是**会话中定期**的（每 10 轮/10 次）。

### Qwen Code（当前）：`save_memory` 工具

Qwen Code 继承 Gemini CLI 的 `save_memory` 工具，代理可以在对话中主动调用它写 memory。但：

- 没有计数器驱动的 nudge
- 没有后台 review
- 只能被动触发

PR #3087（`managed auto-memory + auto-dream`）正在试图引入**类似 Hermes 的 managed 机制**——LaZzyMan 在 2026-04-10 提交，社区正在 review。

---

## 二、存储机制：本地 vs. 服务器 vs. 外部 Provider

### Hermes：纯本地，双重存储

**层级 1：持久文件**

```
~/.hermes/
├── memories/
│   ├── MEMORY.md        # 代理观察
│   └── USER.md          # 用户画像
├── skills/
│   └── <skill-name>/
│       ├── SKILL.md
│       ├── references/
│       ├── templates/
│       ├── scripts/
│       └── assets/
└── state.db             # SQLite + FTS5 全文索引
```

**层级 2：SQLite FTS5**（`hermes_state.py:93-110`）

```sql
CREATE VIRTUAL TABLE messages_fts USING fts5(
    content,
    content=messages,
    content_rowid=id
);
```

**所有历史消息都进入 FTS5 索引**，成为可被"模糊召回"的资产。

**优势**：
- 完全本地化，无隐私顾虑
- FTS5 是 SQLite 内置，零依赖
- 纯 SQL 可以跨工具查询

### Claude Code：本地 + Anthropic 服务器

```
~/.claude/projects/<project-hash>/memory/
├── user_role.md
├── feedback_testing.md
├── project_freeze.md
└── MEMORY.md              # 索引（<200 行）
```

**每个记忆文件有 frontmatter**：

```yaml
---
name: user-role
description: 用户是高级后端工程师
type: user
---
用户是高级后端工程师...
```

**Session 和对话**则存储在 **Anthropic 服务器**（通过 `/resume` 拉取），v2.1.101 的 `showAllProjects` 默认值回归导致的跨项目污染问题，暴露了服务器侧 session 管理的一些粗糙之处。

### Codex CLI：AGENTS.md 多层继承

```
~/.codex/AGENTS.md        # 全局
<project-root>/AGENTS.md  # 项目
<subdirectory>/AGENTS.md  # 子目录
```

**特点**：AGENTS.md 本质是人类可读的 Markdown，不是结构化存储。`consolidation_model` 会去重，但没有像 Hermes 那样的"分隔符 + 条目管理"。

### Qwen Code：QWEN.md 单层

Qwen Code 继承 Gemini CLI 的 `GEMINI.md` 并重命名为 `QWEN.md`。**有 `~/.qwen/QWEN.md` 和 `<project>/QWEN.md` 两层**，但没有更细粒度的条目管理。

---

## 三、召回机制：关键词搜索 vs. 全局加载

### Hermes：FTS5 模糊搜索 + LLM 摘要

```
用户说："上次那个 CSV 解析脚本"
     │
     ▼
FTS5 BM25 排序 → 找到相关消息
     │
     ▼
按 session 分组 → top 3 去重
     │
     ▼
以匹配点为中心截取 ~100K 字符
     │
     ▼
发给 Gemini Flash 做聚焦摘要
     │
     ▼
返回精简摘要（不是原始 transcript）
```

**关键优势**：
1. **无需用户记得精确关键词** —— FTS5 支持模糊匹配
2. **跨会话** —— 不限于当前 session
3. **context 友好** —— 返回摘要而非原文，保护主代理的 context window
4. **便宜** —— Gemini Flash 摘要成本极低

源码：`tools/session_search_tool.py:1-16`

### Claude Code：Memory 全量加载 + /resume

Claude Code 的 `MEMORY.md` 索引文件被整体注入 system prompt（最多 200 行），然后按需展开对应的 memory 文件。

**限制**：
- 只能加载**当前项目**的 memory
- 跨项目必须手工切换
- 无模糊搜索，必须"名字对"才能找到

### Codex CLI：AGENTS.md 整体加载

Codex CLI 把所有 `AGENTS.md` 层级内容合并后注入 system prompt。**无搜索**，完全靠提示词 length budget。

### Qwen Code：类似 Gemini CLI

继承 Gemini CLI 的加载逻辑，`QWEN.md` 被整体注入。

---

## 四、自主改进：存储的内容会变化吗？

**这是最能体现"闭环"与"开环"差异的一环。**

### Hermes：`skill_manage(patch)` 原地修补

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

**核心句**：
- "**patch it immediately ... don't wait to be asked**"
- "**Skills that aren't maintained become liabilities**"

代理在使用 skill 时如果发现内容过时 / 错误 / 不完整，**立即原地修补**。`patch` 动作支持精确的 find-and-replace，不需要重写整个 skill。

### Claude Code / Qwen Code / Codex / 其他：无自修补

其他 agent 的 memory/skill 文件都需要**用户手工编辑**。即使代理发现 memory 里写着"用户是 Python 工程师"但对话中用户说"我现在主要写 Rust"，代理也不会主动更新 memory —— 它只会在下次 nudge 时**添加一条新 memory**（导致冗余）。

### Codex CLI：有 consolidation 但无 patch

Codex CLI 有 `consolidation_model` 负责去重和合并，但这是**批量处理**，不是"代理在使用时发现错误就立即修补"的闭环。

---

## 五、关键设计差异：Prompt Cache 保护

这是 Hermes 最讲究、也最容易被忽视的设计细节。

### Hermes：冻结快照模式

源码：`tools/memory_tool.py:11-14`

```python
"""
Both are injected into the system prompt as a frozen snapshot at session start.
Mid-session writes update files on disk immediately (durable) but do NOT change
the system prompt -- this preserves the prefix cache for the entire session.
The snapshot refreshes on the next session start.
"""
```

**机制**：
- 会话开始时拍快照 → 注入 system prompt → 缓存
- 会话中的 memory 写入：**立即落盘**，但**不改 system prompt**
- 下次会话才加载新快照

**为什么这样做**：
- Anthropic / OpenAI 的 **prefix prompt cache** 对"前缀完全一致"极度敏感
- 任何一次 system prompt 改动 → 整个 cache 失效
- Cache read 只要 cache write 价格的 **1/10**
- 一次会话如果有 20 个 turn，cache 命中可以省 90% 的 input token 费用

**代价**：本次会话**不能立即召回**刚写的 memory。但：
- 刚写的东西代理自己还记得（在 conversation history 里）
- 真正需要"跨对话召回"的内容下次会话就能生效
- 代价极小，收益极大

### Claude Code / Qwen Code / 其他：无此设计

多数 agent 在写 memory 后会立即刷新 system prompt（或者根本不考虑 prompt cache 的影响），导致长对话的 cache 命中率低下。

**Qwen Code 的风险**：PR #3087 如果没有引入类似"冻结快照"机制，接入后可能会让长对话的 cache 成本意外升高。建议 qwen-code 团队 review 这个 PR 时重点关注 prompt cache 保护策略。

---

## 六、Review 子代理：防止注意力竞争

### Hermes：后台、隔离、有限

源码：`run_agent.py:2112-2128`

```python
review_agent = AIAgent(
    model=self.model,
    max_iterations=8,
    quiet_mode=True,
    _memory_nudge_interval=0,   # 防递归
    _skill_nudge_interval=0,
)
```

**关键约束**：
- `max_iterations=8` —— 严格限制，不会无限递归
- `quiet_mode=True` —— 不污染用户输出
- `nudge_interval=0` —— review 子代理自己**不**触发新的 review（防止递归 nudge 爆炸）
- **post-response 派发**：`run_agent.py:10183-10191`
  > "runs AFTER the response is delivered so it never competes with the user's task for model attention"

这 4 个约束合起来保证了 review 子代理**不会影响主任务的延迟和成本**。

### Claude Code Kairos：周期性独立 Agent

Kairos 模式是 "Always-On Agent"，独立于主对话运行，周期性地执行任务（定时 / 事件触发）。

**对比**：
- Kairos 是**独立调度的 agent**，不属于"会话内的 review"
- Hermes review 是**会话内触发的后台子代理**
- 两者是互补的：Kairos 适合"每天早上检查一次"，Hermes review 适合"对话中学习"

### Qwen Code / 其他：无后台 review

Qwen Code 的 PR #3087（auto-memory + auto-dream）可能引入类似机制，但目前还在 review 中。

---

## 七、数据流对比

### Hermes 闭环

```
用户对话 ──► API调用(cache命中) ──► 工具执行 ──► 响应
    ▲                                            │
    │                                            ▼
    │                                      Nudge 检查
    │                                            │
    │                                            ▼ 达标
    │                                      后台 Review 子代理
    │                                            │
    │                                            ▼
    │                                  memory.add / skill.create
    │                                  skill.patch(自修补)
    │                                            │
    │                                            ▼
    │                                      disk 持久化 ──┐
    │                                                    │
    │                                                    │
    └────── 下次会话从 disk 拉取新快照 ◄─────────────────┘
    
跨会话召回：FTS5 搜索 ──► Gemini Flash 摘要 ──► 注入当前对话
```

### Claude Code（半闭环）

```
用户对话 ──► API调用 ──► 工具执行 ──► 响应
                │
                ▼ (被动识别)
          Auto-Memory 写盘
                │
                ▼
      ~/.claude/projects/<hash>/memory/*.md
                │
                ▼ 下次会话
          MEMORY.md 整体注入
          
跨会话召回：/resume 或用户手工指定
无主动 review，无自修补
```

### Qwen Code 现状（开环）

```
用户对话 ──► API调用 ──► 工具执行 ──► 响应
                │
                ▼ (用户或代理主动调用)
          save_memory 工具
                │
                ▼
          ~/.qwen/QWEN.md
          
无计数器，无 review，无自修补
```

---

## 八、可借鉴点：给 Qwen Code / 其他 Agent

Hermes Agent 闭环学习的 **7 个可落地的设计模式**：

### 1. 冻结快照模式保护 Prompt Cache

**适用于所有**有 memory / auto-memory 功能的 Agent。

**实现**：
- 会话开始拍 memory snapshot → 注入 system prompt → 缓存
- 会话中的 memory 写入只落盘，不改 system prompt
- 下次会话再加载

**收益**：长对话场景下 90% 的 input token 节省。

### 2. 双独立计数器触发学习

**适用于** 想要"主动学习"的 Agent。

**实现**：
- `_turns_since_memory` 记用户回合数
- `_iters_since_skill` 记工具调用次数
- 两个计数器独立递增、独立重置
- 达到阈值 → 标记需要 review，但不立即执行

### 3. Post-Response 后台 Review

**核心原则**：review 子代理**绝不和主任务抢注意力**。

**实现**：
- 只在响应送出后启动
- 子代理自身 `nudge_interval=0` 防递归
- `max_iterations=8` 严格上限
- `quiet_mode=True` 不污染主输出

### 4. 保守的 Review Prompt

**关键句**：
- "non-trivial approach"
- "trial and error"
- "Only act if there's something genuinely worth saving"
- "Nothing to save." —— 允许空手而归

**为什么重要**：防止 skill 库被垃圾填满。

### 5. `patch` 动作：原地修补而非重写

**适用于** 有 skill / memory 系统的 Agent。

**实现**：
- 提供 `action='patch'` 操作
- 支持精确 find-and-replace
- 在 guidance 中明确指示"发现过时立即修补"

### 6. 本地 FTS5 做跨会话搜索

**适用于** 想支持"模糊召回历史对话"的 Agent。

**实现**：
- SQLite 存消息
- FTS5 虚拟表自动索引
- 查询时 BM25 排序 top-N session
- 用便宜模型（Gemini Flash / Haiku）做摘要
- 返回摘要而非原文

### 7. Tool-Aware Guidance 条件注入

**通用优化**：

```python
tool_guidance = []
if "memory" in self.valid_tool_names:
    tool_guidance.append(MEMORY_GUIDANCE)
if "session_search" in self.valid_tool_names:
    tool_guidance.append(SESSION_SEARCH_GUIDANCE)
if "skill_manage" in self.valid_tool_names:
    tool_guidance.append(SKILLS_GUIDANCE)
```

**目的**：只在对应工具加载时才注入对应的 guidance 文本，避免无关指令污染 context。

---

## 九、对应 PR 追踪

### Qwen Code 正在跟进的相关 PR

| PR | 主题 | 状态 | 对应 Hermes 机制 | 备注 |
|---|---|---|---|---|
| [#3087](https://github.com/QwenLM/qwen-code/pull/3087) | `managed auto-memory + auto-dream` | 开发中（LaZzyMan） | 持久 Memory + Review 子代理 | 建议 review 时关注 prompt cache 保护 |
| [#3006](https://github.com/QwenLM/qwen-code/pull/3006) | `microcompaction for idle context cleanup` | 开发中（tanzhenxin） | 部分对应"空闲时工作" | 仅清理不学习 |
| [#2864](https://github.com/QwenLM/qwen-code/pull/2864) | `intelligent tool parallelism` | 已合并 | - | 和闭环无关 |
| [#3085](https://github.com/QwenLM/qwen-code/pull/3085) | `startup optimization` | 开发中 | - | 启动性能 |

---

## 十、小结

**完整的闭环学习系统**需要 4 个环节全部具备：

1. **经验识别**（主动触发而非被动记录）
2. **存储机制**（考虑隐私 / 成本 / 可搜索性）
3. **召回机制**（跨会话 + 模糊匹配）
4. **自主改进**（发现过时自动修补）

**Hermes Agent 是当前 19 款 Code Agent 中唯一在所有 4 个环节都具备原生实现的产品**。

其核心创新不是"做了一个 memory 系统"——很多 agent 都有 memory——而是：

- **把"学习"作为一个系统性工程来设计**
- **保护 prompt cache**（冻结快照）
- **保护主任务注意力**（post-response review）
- **保守的学习政策**（宁可不学也不乱学）
- **自主改进**（skill 过时立即 patch）

**这 5 个原则比任何单独的功能都更值得 Qwen Code / 其他 agent 借鉴。**

---

## 相关阅读

- [`docs/tools/hermes-agent/`](../tools/hermes-agent/) — Hermes Agent 完整文档
- [`docs/tools/hermes-agent/03-closed-learning-loop.md`](../tools/hermes-agent/03-closed-learning-loop.md) — 闭环系统技术细节
- [`docs/tools/hermes-agent/EVIDENCE.md`](../tools/hermes-agent/EVIDENCE.md) — 源码引用
- [`memory-system-deep-dive.md`](./memory-system-deep-dive.md) — 长期记忆系统对比（非闭环视角）
- [`skill-system-deep-dive.md`](./skill-system-deep-dive.md) — Skill 系统对比
- [`kairos-always-on-agent-deep-dive.md`](./kairos-always-on-agent-deep-dive.md) — Claude Code Kairos 模式
- [`agent-memory-persistence-deep-dive.md`](./agent-memory-persistence-deep-dive.md) — 跨会话持久化对比
- [Qwen Code PR #3087](https://github.com/QwenLM/qwen-code/pull/3087) — `managed auto-memory + auto-dream`（开发中）
- [Qwen Code Issue #129 (codeagents)](https://github.com/wenshao/codeagents/issues/129) — 原始建议：增加 Hermes Agent 研究

---

**版本**：基于 Hermes Agent 0.8.0 源码分析
**日期**：2026-04-13
