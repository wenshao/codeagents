# 33. 长期记忆与项目指令系统深度对比

> 长期记忆决定了 AI 编程代理能否"记住"项目偏好和上下文。从"无记忆"到"AI 子代理自动去重分类"，实现差距跨越了三代架构。

## 总览

| 工具 | 指令文件 | 层级数 | 自动学习 | AI 管理 | 跨项目 | 跨格式读取 |
|------|---------|--------|---------|---------|--------|-----------|
| **Claude Code** | CLAUDE.md | **4 层** | **✓** | ✗（用户编辑） | ✓ | ✗ |
| **Gemini CLI** | GEMINI.md | **4 层** | **✓** | **✓（memory_manager）** | ✓ | ✗ |
| **Copilot CLI** | copilot-instructions.md | 1 层 | ✗ | ✗ | ✗ | **✓（读 3 种格式）** |
| **Qwen Code** | QWEN.md | 继承 Gemini | ✓ | ✓（继承） | ✓ | ✗ |
| **Kimi CLI** | AGENTS.md | 1 层 | ✗（一次性） | ✗ | ✗ | ✗ |
| **Codex CLI** | CODEX.md | 2 层 | ✗ | ✗ | ✓ | ✗ |
| **Aider** | .aider.conf.yml | 2 层 | ✗ | ✗ | ✓ | ✗ |
| **Goose** | config.yaml | 1 层 | ✗ | ✗ | ✓ | ✗ |
| **OpenCode** | opencode.json | 3 层 | ✗ | ✗ | ✓ | ✗ |
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

Copilot CLI 是唯一读取多种指令文件格式的工具：

| 优先级 | 文件 | 说明 |
|--------|------|------|
| 1 | `.github/copilot-instructions.md` | 原生格式 |
| 2 | `CLAUDE.md` | 读取 Claude Code 指令 |
| 3 | `GEMINI.md` | 读取 Gemini CLI 指令 |
| 4 | `AGENTS.md` | 读取 Codex/Kimi 指令 |

**设计理念**：团队中不同成员使用不同工具时，Copilot CLI 自动适配，无需维护额外指令文件。

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

## 五、Codex CLI：双层指令

> 来源：01-overview.md、02-commands.md

```
~/.codex/instructions.md    ← 全局用户级（最低优先级）
CODEX.md 或 AGENTS.md       ← 项目级（同等优先级）
```

支持 `/init` 生成 CODEX.md。

---

## 六、Aider：配置文件 + --read

> 来源：01-overview.md

```
~/.aider.conf.yml    ← 全局配置
.aider.conf.yml      ← 项目级配置
--read <file>        ← 显式添加上下文文件
```

**无 AI 记忆系统**。Aider 的"记忆"是 Git 历史——每次修改自动提交，提交消息由弱模型生成。

---

## 七、OpenCode：SQLite + 3 层配置

> 来源：03-architecture.md

```
~/.config/opencode/opencode.json    ← 全局
.opencode/opencode.json             ← 项目级
远程 .well-known/opencode           ← 企业级
```

**唯一使用 SQLite 的工具**：3 张表（sessions/messages/files），但用于会话持久化，非 AI 记忆。

---

## 项目指令文件生态图

```
┌─────────────────────────────────────────────────┐
│               Copilot CLI（读取 4 种格式）          │
│  ┌──────────┐ ┌──────────┐ ┌────────┐ ┌───────┐ │
│  │CLAUDE.md │ │GEMINI.md │ │AGENTS.md│ │copilot│ │
│  └────┬─────┘ └────┬─────┘ └───┬────┘ └───────┘ │
│       │             │           │                 │
│  Claude Code   Gemini CLI   Codex CLI             │
│                Qwen Code    Kimi CLI              │
│                             Goose                 │
└─────────────────────────────────────────────────┘

独立文件：
  OpenCode → opencode.json
  Aider    → .aider.conf.yml
  Cline    → .cline/instructions
```

---

## 记忆系统演进三代

### 第一代：静态配置

**代表**：Aider、Codex CLI、Cline

- 用户手动编写配置文件
- 不会自动学习或更新
- 需要用户主动维护

### 第二代：一次性生成 + 手动维护

**代表**：Kimi CLI、Qwen Code（/init）

- `/init` 命令 LLM 分析项目，生成指令文件
- 生成后不自动更新
- 项目变化需手动重新生成

### 第三代：AI 自动学习 + 持续更新

**代表**：Claude Code（auto-memory）、Gemini CLI（memory_manager）

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

## 证据来源

| 工具 | 来源 | 获取方式 |
|------|------|---------|
| Claude Code | 03-architecture.md + 07-session.md + EVIDENCE.md | 二进制分析 |
| Gemini CLI | 04-tools.md + 05-policies.md + 03-architecture.md | 开源 |
| Copilot CLI | EVIDENCE.md + 03-architecture.md | SEA 反编译 |
| Kimi CLI | 03-architecture.md（init 实现） | 开源 |
| Qwen Code | qwen-code.md | 开源 |
| Codex CLI | 01-overview.md + 02-commands.md | 二进制 + 官方文档 |
| Aider | 01-overview.md | 开源 |
| OpenCode | 03-architecture.md | 开源 |
