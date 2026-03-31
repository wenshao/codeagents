# 33. 长期记忆与项目指令系统深度对比

> 长期记忆决定了 AI 编程代理能否"记住"项目偏好和上下文。从"无记忆"到"AI 子代理自动去重分类"，实现差距跨越了三代架构。

## 总览

| Agent | 指令文件 | 层级数 | 自动学习 | AI 管理 | 跨项目 | 跨格式读取 |
|------|---------|--------|---------|---------|--------|-----------|
| **Claude Code** | CLAUDE.md | **4 层** | **✓** | ✗（用户编辑） | ✓ | ✗ |
| **Gemini CLI** | GEMINI.md | **4 层** | **✓** | **✓（memory_manager）** | ✓ | ✗ |
| **Copilot CLI** | copilot-instructions.md | 多层（全局+项目+.github） | ✗ | ✗ | ✓ | **✓（读 7 种来源）** |
| **Qwen Code** | QWEN.md + AGENTS.md | 继承 Gemini | ✓（save_memory 工具） | ✗（无 memory_manager 子代理） | ✓（`~/.qwen/QWEN.md`） | ✗ |
| **Kimi CLI** | AGENTS.md | 1 层 | ✗（一次性） | ✗ | ✗ | ✗ |
| **Codex CLI** | AGENTS.md | 多层递归 | **✓**（generate_memories） | **✓**（extract_model + consolidation_model） | ✓ | ✗ |
| **Qoder CLI** | AGENTS.md + CLAUDE.md | 双层（用户级+项目级） | **✓**（Session Memory Update） | **✓**（LLM 驱动记忆更新） | ✓ | **✓（读 CLAUDE.md）** |
| **Goose** | .goosehints + AGENTS.md | 多层 + JIT 子目录 | ✗ | ✗ | ✓ | **✓（可配置读 CLAUDE.md）** |
| **OpenCode** | AGENTS.md + CLAUDE.md + CONTEXT.md | 3 文件 | ✗ | ✗ | ✓ | **✓（读 3 种文件）** |
| **Cursor** | .cursor/rules/*.mdc | 4 种规则类型 | ✗ | ✗ | ✓ | ✗ |
| **Aider** | .aider.conf.yml | 2 层 | ✗ | ✗ | ✓ | ✗ |
| **Cline** | .cline/instructions | 1 层 | ✗ | ✗ | ✗ | ✗ |

---

## 一、Claude Code：4 层 CLAUDE.md + Auto-Memory（最成熟）

> 来源：03-architecture.md、07-session.md、EVIDENCE.md

### 4 层指令文件

```
~/.claude/CLAUDE.md                 ← 全局（所有项目通用偏好）
<project-root>/CLAUDE.md            ← 项目级（Git 提交，团队共享）
<subdirectory>/CLAUDE.md            ← 模块级（子目录特定规则）
~/.claude/projects/<hash>/CLAUDE.md ← 用户私有项目级（不提交 Git）
```

### Auto-Memory 系统

系统提示中的 `# auto memory` 模块识别 4 种记忆类型：

| 类型 | 触发条件 | 存储内容 |
|------|---------|---------|
| **user** | 识别用户角色/偏好 | 角色、目标、知识水平 |
| **feedback** | 用户纠正或确认 | "不要这样做"、"对，就这样" |
| **project** | 了解到项目上下文 | 截止日期、技术决策、团队分工 |
| **reference** | 发现外部资源 | Linear 项目、Grafana 仪表板 URL |

### 记忆存储结构

```
~/.claude/projects/<project-hash>/memory/
  ├── user_role.md           # 用户角色记忆
  ├── feedback_testing.md    # 测试偏好记忆
  ├── project_freeze.md      # 项目状态记忆
  └── MEMORY.md              # 索引文件（<200 行）
```

每个记忆文件有 frontmatter：
```yaml
---
name: user-role
description: 用户是高级后端工程师
type: user
---
用户是高级后端工程师，专注 Go 和 PostgreSQL...
```

### 自定义记忆目录（v2.1.83 新增）

```json
// settings.json
{
  "autoMemoryDirectory": "/path/to/custom/memory"
}
```

默认存储在 `~/.claude/projects/<hash>/memory/`，通过 `autoMemoryDirectory` 可指定自定义路径。

### Team Memory API

```
claude.ai/api/claude_code/team_memory
```

仓库级别共享记忆，团队成员可共享项目知识。

### `/memory` 命令

打开外部编辑器编辑 CLAUDE.md 记忆文件。

---

## 二、Gemini CLI：AI memory_manager 子代理（最智能）

> 源码：`packages/core/src/agents/memory-manager/`

### 4 层指令文件

```
~/.gemini/GEMINI.md                  ← 全局
.gemini/GEMINI.md                    ← 项目级
<subdirectory>/.gemini/GEMINI.md     ← 子目录（BFS 加载）
扩展级 GEMINI.md                      ← 扩展定义
```

**@import 语法**（Gemini CLI 独有）：GEMINI.md 中可导入其他文件。

### memory_manager 子代理

| 属性 | 值 |
|------|-----|
| 模型 | Flash（轻量） |
| 轮次上限 | 10 轮 |
| 超时 | 5 分钟 |
| 注册条件 | 需在设置中启用 |

**自动化能力**：
- **去重**：新记忆与已有记忆语义对比，合并重复项
- **分类组织**：按主题自动整理
- **存储格式**：Markdown 项目符号，写入 `## Gemini Added Memories` 章节

### save_memory 内置工具

代理在对话中发现有价值的信息时，通过 `save_memory` 工具主动保存：

```
对话中发现项目使用 pnpm
  → memory_manager 子代理
  → 去重检查（是否已记录？）
  → 分类（构建工具类）
  → 写入 GEMINI.md ## Gemini Added Memories
```

### `/memory` 命令

```bash
/memory              # 查看所有记忆
/memory add 这个项目使用 pnpm
/memory clear        # 清除记忆
```

---

## 三、Copilot CLI：跨格式读取（最兼容）

> 来源：EVIDENCE.md、03-architecture.md

### 多格式读取

Copilot CLI 读取 **7 种来源**的指令文件（与 OpenCode 并列最多跨格式读取）：

| 优先级 | 文件 | 说明 |
|--------|------|------|
| 1 | `CLAUDE.md`（项目根+父目录） | Claude Code 兼容 |
| 2 | `GEMINI.md` | Gemini CLI 兼容 |
| 3 | `AGENTS.md` | Codex/Kimi/OpenCode 兼容 |
| 4 | `.github/instructions/**/*.instructions.md` | GitHub 标准路径 |
| 5 | `.github/copilot-instructions.md` | 原生格式 |
| 6 | `~/.copilot/copilot-instructions.md` | 全局（所有项目） |
| 7 | `COPILOT_CUSTOM_INSTRUCTIONS_DIRS` 环境变量 | 自定义目录 |

可通过 `--no-custom-instructions` 禁用所有指令加载。

---

## 四、Kimi CLI：AGENTS.md 一次性生成

> 源码：`soul/slash.py:init()`

### `/init` 隔离执行

```python
async def init(soul, args):
    # 1. 创建临时目录和临时 KimiSoul（隔离上下文）
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_soul = KimiSoul(temp_context, agent=soul.agent)
        # 2. 在隔离环境中运行分析
        await temp_soul.run(prompts.INIT)
    # 3. 加载生成的 AGENTS.md 到主会话
    agents_md = load_agents_md(work_dir)
    soul.context.inject_system_message(agents_md)
```

**为什么隔离？** 防止 /init 的分析过程（可能读取大量文件）污染当前会话的上下文窗口。

### AGENTS.md 内容

项目类型、技术栈、目录结构、关键文件、构建命令、编码规范。

**局限**：一次性生成，不自动更新。项目变化后需手动重新 `/init`。

---

## 五、Codex CLI：两阶段记忆提取 + 合并（最接近 MemGPT）

> 来源：Rust 二进制 strings 分析（43 处 AGENTS.md 引用，0 处 CODEX.md 引用）

### 两阶段记忆工作流

```
Stage 1: 提取（extract_model）
  ├── 从 assistant messages 中提取"durable memory"
  └── 输出：原始记忆条目

Stage 2: 合并（consolidation_model，后台子代理）
  ├── 合并原始记忆与 rollout 摘要
  ├── thread_id 追踪去重
  ├── 引用合并：将新信号路由到 MEMORY.md 已有 block 或创建新 block
  └── 更新 memory_summary.md（最后写入，信号密度最高）
```

### 记忆存储结构

```
.codex/
  ├── MEMORY.md              ← 可搜索的记忆注册表（主查询文件）
  ├── memory_summary.md      ← 概要摘要（避免重复打开 MEMORY.md）
  ├── rollout_summaries/     ← 每个 rollout 的回顾和证据片段
  ├── skills/<skill-name>/   ← 技能级指令
  └── codex.db               ← SQLite（thread 元数据 + rollout 路径）
```

MEMORY.md 格式：
```xml
## My request for Codex:
<rollout_ids>...</rollout_ids>
<thread_ids>...</thread_ids>
<citation_entries>...</citation_entries>
```

### 配置键（`~/.codex/config.toml` `[persistence]` 段）

| 配置键 | 说明 |
|--------|------|
| `generate_memories` | 是否启用记忆生成 |
| `use_memories` | 是否在会话中使用已有记忆 |
| `max_raw_memories_for_consolidation` | 单次合并的最大原始记忆数 |
| `max_unused_days` | 记忆最大未使用天数（过期清理） |
| `extract_model` | Stage-1 提取模型 |
| `consolidation_model` | Stage-2 合并模型 |

### 触发与去重

- 会话结束时自动触发（`drop_memories` / `update_memories` API）
- `memory_consolidation` 作为 `SubAgentSource` 变体，后台子代理执行合并
- 启动时根据 `max_rollouts_per_startup` 处理历史 rollout
- 去重：维护 thread_id 追踪，对新增/移除的 thread_id 做"外科手术式"删除或重写

### 与 Claude Code 的互操作性

二进制中检测到 `~/.claude` 和 `~/.codex` 路径并存的逻辑：*"If true, include detection under the user's home (~/.claude, ~/.codex, etc.)"*——支持从 Claude Code 导入外部代理配置。

---

## 六、Goose：.goosehints + MOIM 持久化指令 + MCP Memory 服务器

> 来源：`crates/goose/src/hints/`、`crates/goose-mcp/src/memory/`

### .goosehints 层级加载

```
~/.config/goose/.goosehints      ← 全局
<project-root>/.goosehints       ← 项目级（git 仓库内层级加载）
<subdirectory>/.goosehints       ← JIT 子目录加载（SubdirectoryHintTracker）
```

Goose 默认查找 `["AGENTS.md", ".goosehints"]`，可通过 `CONTEXT_FILE_NAMES` 环境变量配置（如加入 `CLAUDE.md`）。hints 文件中可用 `@filename.md` 自动内联其他文件。

### MOIM（Model-Observed Internal Memory）

每轮对话注入的持久化指令，无需重启 session 即可生效：

| 环境变量 | 说明 | 限制 |
|---------|------|------|
| `GOOSE_MOIM_MESSAGE_TEXT` | 直接注入文本 | 64KB |
| `GOOSE_MOIM_MESSAGE_FILE` | 注入文件内容 | 64KB |

### MCP Memory 服务器

Goose 内置 MCP Memory 服务器（Rust 实现，758 行），提供 4 个工具：

| 工具 | 参数 | 说明 |
|------|------|------|
| `remember_memory` | category, data, tags?, is_global | 追加记忆到分类文件 |
| `retrieve_memories` | category（`"*"` 全部）, is_global | 检索记忆 |
| `remove_memory_category` | category（`"*"` 全部）, is_global | 删除整个分类 |
| `remove_specific_memory` | category, memory_content, is_global | 删除指定条目 |

**存储后端**：纯文件系统（无 SQLite）。每个分类一个 `.txt` 文件：
- 全局：`~/.config/goose/memory/<category>.txt`
- 本地：`<project-root>/.goose/memory/<category>.txt`

条目以 `\n\n` 分隔，可选标签行 `# tag1 tag2`。`remember()` 使用 append 模式，**无自动去重**。

**会话加载**：服务器初始化时自动加载所有全局记忆并注入到 system instructions 中。

---

## 六-B、Aider：.aider.conf.yml（无自动记忆）

> 来源：01-overview.md

```
~/.aider.conf.yml    ← 全局配置
.aider.conf.yml      ← 项目级配置
--read <file>        ← 显式添加上下文文件
```

**无 AI 记忆系统**。Aider 的"记忆"是 Git 历史——每次修改自动提交，提交消息由弱模型生成。

---

## 七、OpenCode：AGENTS.md + CLAUDE.md + CONTEXT.md

> 来源：Go ELF 二进制 strings 分析（v1.2.15，152MB）

```javascript
// 从二进制提取的默认指令文件列表
FILES = ["AGENTS.md", "CLAUDE.md", "CONTEXT.md"]

// 加载路径
files.push(path.join(OPENCODE_CONFIG_DIR, "AGENTS.md"));
files.push(path.join(Global.Path.config, "AGENTS.md"));

// 还读取 Claude Code 全局记忆（可禁用）
// ~/.claude/CLAUDE.md（除非 OPENCODE_DISABLE_CLAUDE_CODE_PROMPT）
```

**三文件同时读取**：OpenCode 是除 Copilot CLI 外另一个跨格式读取的 Agent——同时读取 AGENTS.md、CLAUDE.md 和 CONTEXT.md。

**SQLite 存储**：3 张表（sessions/messages/files）用于会话持久化，非 AI 记忆。

---

## 八、Qoder CLI：双层记忆 + 会话内实时更新

> 来源：Go 二进制 strings 分析（43MB）

### 双层记忆架构

Qoder CLI 实现了**两套独立的记忆系统**：

**A. 持久化记忆（state/memory 包）**

| 函数 | 说明 |
|------|------|
| `GetProjectMemoryFilePath()` | 项目级记忆文件路径 |
| `GetUserMemoryFilePath()` | 用户级记忆文件路径 |
| `AppendMemory()` | 追加记忆条目 |
| `appendRuleMemory()` | 追加规则型记忆 |

- 使用 ACP SDK（`acp-sdk-go/api.MemoryReference`）与外部平台集成
- 系统提示中明确引用 `CLAUDE.md`：*"Consider any project-specific context from CLAUDE.md files"*

**B. 会话内记忆（state/session_memory 包）**

会话记忆在每个 turn 结束时通过 LLM 驱动更新：

```
Turn 完成
  → TriggerUpdate() / WaitForUpdate()
  → SessionMemoryUpdatePrompt（LLM 生成更新）
  → FormatSessionMemoryForCompact()
  → 压缩超限部分："Truncate compact history until tokens below capacity"
```

使用 `<user-memory-input>` XML 标签包裹用户输入。会话记忆还提供 `memory_overview`（摘要）和 `search_memory`（检索额外记忆）两种访问方式。

**TUI 交互**：`MemoryCommand` / `MemorySelector` 支持键盘交互选择记忆。

---

## 九、Cursor：Rules 文件系统（无自动记忆）

> 来源：docs/tools/cursor-cli.md

### .cursor/rules/*.mdc 规则

Cursor 通过 `.cursor/rules/` 目录下的 `.mdc` 文件管理项目指令，每条规则包含 YAML frontmatter（`description`、`globs`、`alwaysApply`）：

| 规则类型 | 触发方式 | 说明 |
|---------|---------|------|
| **Always** | 每次对话自动加载 | 等效于 CLAUDE.md |
| **Auto Attached** | 基于 glob 模式匹配 | 文件路径匹配时自动附加 |
| **Agent Requested** | AI 自主决定是否使用 | AI 根据描述判断相关性 |
| **Manual** | 用户 `@rules` 手动引用 | 显式选择 |

> **注意**：`.cursorrules`（旧格式）已废弃，被 `.cursor/rules/*.mdc` 取代。

**本质差异**：Cursor 没有自动记忆提取功能。所有"记忆"依赖用户手动创建和维护 Rules 文件，AI 不会将对话中的信息自动保存为记忆。这与 Codex CLI、Goose MCP Memory、Qoder CLI 的自动记忆形成鲜明对比。

---

## 项目指令文件生态图

```
┌──────────────────────────────────────────────────────┐
│           Copilot CLI（读取 7 种来源）                   │
│  ┌──────────┐ ┌──────────┐ ┌────────┐ ┌───────────┐ │
│  │CLAUDE.md │ │GEMINI.md │ │AGENTS.md│ │copilot-*  │ │
│  └────┬─────┘ └────┬─────┘ └───┬────┘ └───────────┘ │
│       │             │           │                     │
│  Claude Code   Gemini CLI   Codex CLI（43 refs）      │
│                             Kimi CLI                  │
│                             OpenCode（21 refs）        │
│                             Qwen Code v0.13+          │
└──────────────────────────────────────────────────────┘

独立文件：
  Aider    → .aider.conf.yml
  Cline    → .cline/instructions
  Cursor   → .cursor/rules/*.mdc
  Goose    → .goosehints + AGENTS.md
  Qoder CLI → AGENTS.md + CLAUDE.md
```

---

## 记忆系统演进三代

### 第一代：静态配置

**代表**：Aider、Cline

- 用户手动编写配置文件
- 不会自动学习或更新
- 需要用户主动维护

### 第二代：LLM 生成 + 手动维护 / MCP 工具调用

**代表**：Kimi CLI（/init）、OpenCode、Goose（MCP Memory 服务器）、Qoder CLI（Session Memory Update）

- `/init` 命令 LLM 分析项目，生成指令文件（AGENTS.md）
- OpenCode 同时读取 3 种文件格式（AGENTS.md + CLAUDE.md + CONTEXT.md）
- Goose 提供 MCP Memory 服务器（4 工具），LLM 可调用但无 AI 自动管理
- Qoder CLI 在每个 turn 结束时通过 LLM 更新会话记忆（Session Memory Update）
- 生成后大多不自动更新，项目变化需手动重新生成

### 第三代：AI 自动学习 + 持续更新

**代表**：Claude Code（auto-memory）、Gemini CLI（memory_manager）、**Codex CLI（generate_memories + consolidation_model）**

- 对话中自动识别有价值的信息
- AI 管理去重、分类、存储
- 跨会话持久化，无需用户干预

---

## 自动学习深度对比

| 维度 | Claude Code | Gemini CLI |
|------|------------|-----------|
| 触发方式 | 系统提示指令识别 | save_memory 工具 + 子代理 |
| 去重 | 内容哈希 | **AI 语义去重** |
| 分类 | 4 类型（user/feedback/project/reference） | **AI 自动分类** |
| 存储 | 独立 .md 文件 + MEMORY.md 索引 | GEMINI.md 内 `## Added Memories` |
| 编辑 | `/memory` 打开编辑器 | `/memory add/clear` |
| 团队共享 | **✓（team_memory API）** | ✗ |
| 索引限制 | MEMORY.md < 200 行 | 无显式限制 |

---

## Contextual Retrieval：检索失败率降低 67%（来源：[Anthropic Engineering Blog](https://www.anthropic.com/engineering/contextual-retrieval)，2024-09-19）

Agent 记忆系统的底层技术——如何让检索更准确：

> "Traditional RAG solutions remove context when encoding information, which often results in the system failing to retrieve the relevant information from the knowledge base."

**解决方案**：在嵌入前为每个 chunk 添加上下文前缀：

> "Contextual Retrieval solves this problem by prepending chunk-specific explanatory context to each chunk before embedding ('Contextual Embeddings') and creating the BM25 index ('Contextual BM25')."

| 方案 | 检索失败率 | 降低幅度 |
|------|-----------|---------|
| 传统 RAG | 5.7% | — |
| Contextual Embeddings + BM25 | 2.9% | -49% |
| + Reranking | **1.9%** | **-67%** |

**小知识库可以跳过 RAG**：

> "If your knowledge base is smaller than 200,000 tokens (about 500 pages of material), you can just include the entire knowledge base in the prompt."

**对 Agent 记忆系统的启示**：Claude Code 的 auto-memory（MEMORY.md < 200 行）和 Gemini CLI 的 GEMINI.md 本质上都是"小知识库直接注入 prompt"的策略——当记忆量小于 200K tokens 时，这比 RAG 更有效。

---

## 证据来源

| Agent | 来源 | 获取方式 |
|------|------|---------|
| Claude Code | 03-architecture.md + 07-session.md + EVIDENCE.md | 二进制分析 |
| Gemini CLI | 04-tools.md + 05-policies.md + 03-architecture.md | 开源 |
| Copilot CLI | EVIDENCE.md + 03-architecture.md | SEA 反编译 |
| Kimi CLI | 03-architecture.md（init 实现） | 开源 |
| Qwen Code | cli.js 二进制 strings（v0.13.0）：save_memory 11 refs, memory_manager 0 refs, GEMINI.md 0 refs | 二进制分析 |
| Codex CLI | Rust 二进制 strings（43 AGENTS.md refs, memories/control.rs, generate_memories/consolidation_model） | 二进制分析 |
| Aider | 01-overview.md | 开源 |
| OpenCode | Go ELF 二进制 strings（v1.2.15） | 二进制分析 |
