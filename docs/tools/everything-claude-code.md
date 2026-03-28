# Everything Claude Code（ECC）—— AI Agent 增强系统

**仓库：** [github.com/affaan-m/everything-claude-code](https://github.com/affaan-m/everything-claude-code)
**许可证：** MIT
**网站：** [ecc.tools](https://ecc.tools)
**版本：** v1.9.0（2026-03-21）
**最后更新：** 2026-03

## 概述

Everything Claude Code（简称 ECC）是一个面向 AI Agent 的**性能优化与增强系统**，通过 28 个专用 Agent、125+ 个 Skill、60 个斜杠命令、34 条规则和 Hook 自动化，将 Claude Code 等工具从编码助手提升为具备持续学习、记忆持久化、安全扫描和研究驱动开发的综合开发平台。

ECC 由 affaanmustafa（Anthropic Hackathon 获胜者，2025 年 9 月）创建，经过 10+ 个月的日常生产使用迭代。截至 2026 年 3 月，GitHub 仓库拥有 ~112k Stars、~14.6k Forks、113 位贡献者、816 次提交和 11 个 Release。

**核心定位：** ECC 不是一个独立的 Agent 工具，而是一套**增强层**——安装到现有 Agent 上，为其提供额外的 Agent、Skill、Command、Rule 和 Hook。

## 支持的 Agent 工具

ECC 是首个跨主流 AI 编码工具的增强插件：

| 工具 | Agent 数 | 命令数 | Skill 数 | Hook 事件 | Rule 数 |
|------|---------|--------|---------|----------|--------|
| **Claude Code** | 28 | 60 | 125+ | 8 种事件类型 | 34 |
| **Cursor IDE** | 共享（AGENTS.md） | 共享 | 共享 | 15 种事件类型 | 34 |
| **Codex CLI/App** | 共享 | 指令式 | 16 | — | 指令式 |
| **OpenCode** | 12 | 31 | 37 | 11 种事件类型 | 13 |

跨工具架构的核心设计：
- **AGENTS.md** 作为通用跨工具文件，所有工具均可读取
- **DRY Adapter 模式**：Cursor 的 stdin JSON 通过 `adapter.js` 转换后，复用 Claude Code 的 Hook 脚本
- **SKILL.md 格式**：跨工具通用的 Skill 定义格式

## 系统要求

- Claude Code CLI v2.1.0+
- Node.js（用于 Hook 脚本运行时）

---

## 核心组件

### 1. 28 个专用 Agent

ECC 的 Agent 是带有 YAML frontmatter 的 Markdown 文件，定义了 `name`、`description`、`tools`（可用工具列表）和 `model`（推荐模型）。Agent 处理委派任务，具有受限的作用域和工具访问权限。

| 类别 | Agent | 说明 |
|------|-------|------|
| **规划** | planner | 创建实现蓝图 |
| **架构** | architect | 系统架构设计 |
| **测试** | tdd-guide, e2e-runner | TDD 工作流引导、E2E 测试 |
| **审查** | code-reviewer, security-reviewer, cpp-reviewer, go-reviewer, python-reviewer, typescript-reviewer, java-reviewer, kotlin-reviewer, rust-reviewer, database-reviewer | 按语言/领域分的代码审查 |
| **构建修复** | build-error-resolver, cpp-build-resolver, go-build-resolver, java-build-resolver, kotlin-build-resolver, rust-build-resolver, pytorch-build-resolver | 按生态分的构建错误解决 |
| **运维** | refactor-cleaner, doc-updater, docs-lookup, chief-of-staff, loop-operator, harness-optimizer | 重构、文档、循环操作、性能优化 |

Agent 文件格式示例：

```markdown
---
name: code-reviewer
description: Reviews code for quality, security, and maintainability
tools: ["Read", "Grep", "Glob", "Bash"]
model: opus
---
You are a senior code reviewer...
```

### 2. 125+ 个 Skill

Skill 是工作流定义和领域知识库，以 SKILL.md 格式存储，通过命令或 Agent 调用。覆盖以下类别：

| 类别 | Skill 示例 |
|------|-----------|
| **编码标准** | TypeScript、Python、Go、C++、Java、Swift、Perl、Rust、PHP 编码规范 |
| **框架模式** | Django、Spring Boot、Laravel、Next.js、PyTorch 最佳实践 |
| **测试** | TDD 工作流、Playwright E2E、验证循环、Eval Harness |
| **安全** | AgentShield 集成、安全审查 |
| **DevOps** | Docker、部署、数据库迁移、API 设计 |
| **AI/ML** | 成本感知 LLM 管道、regex-vs-LLM 决策、端侧基础模型 |
| **运营** | continuous-learning v2、autonomous-loops、strategic-compact |
| **商业/内容** | 文章写作、市场研究、投资人材料、内容引擎 |

### 3. 60 个斜杠命令

| 类别 | 命令 |
|------|------|
| **开发流程** | `/plan`、`/tdd`、`/code-review`、`/build-fix`、`/e2e`、`/refactor-clean` |
| **安全与质量** | `/security-scan`、`/verify`、`/eval`、`/quality-gate` |
| **学习与记忆** | `/learn`、`/checkpoint`、`/instinct-import`、`/instinct-export`、`/instinct-status`、`/evolve`、`/prune`、`/skill-create` |
| **编排** | `/orchestrate`、`/sessions`、`/multi-plan`、`/multi-execute`、`/model-route` |
| **运维** | `/harness-audit`、`/loop-start`、`/pm2`、`/setup-pm` |

### 4. 34 条规则（Rules）

规则是**始终生效的指导原则**，加载到系统提示中，分为：

- `common/`：语言无关规则（始终安装）—— 编码风格、Git 工作流、测试、性能、模式、安全
- 语言特定目录：`typescript/`、`python/`、`golang/`、`swift/`、`php/`、`java/`、`rust/`、`cpp/`、`kotlin/`、`perl/`

安装位置：用户级 `~/.claude/rules/` 或项目级 `.claude/rules/`。

### 5. Hook 自动化

Hook 基于 Claude Code 的 24 种事件类型触发自动化操作：

| Hook 事件 | 用途 |
|----------|------|
| PreToolUse | 工具调用前拦截（如阻止敏感操作） |
| PostToolUse | 工具调用后处理（如 Edit 后自动检查 `console.log`） |
| Stop | 会话结束时保存状态 |
| SessionStart | 会话开始时加载上下文 |
| SessionEnd | 会话结束时保存上下文 |

运行时控制：

```bash
export ECC_HOOK_PROFILE=standard     # minimal | standard | strict
export ECC_DISABLED_HOOKS="pre:bash:tmux-reminder,post:edit:typecheck"
```

---

## 持续学习系统（Instincts v2）

ECC 的 Instinct 系统是核心差异化能力，能够**自动从会话中学习用户模式**：

```
会话中产生的模式
  → /learn 提取模式 → Instinct（带置信度评分）
  → /evolve 聚类相关 Instinct → Skill
  → /skill-create 从 Git 历史生成 Skill
```

| 命令 | 功能 |
|------|------|
| `/instinct-status` | 显示已学 Instinct 及其置信度 |
| `/instinct-import` | 导入他人的 Instinct |
| `/instinct-export` | 导出 Instinct 用于团队共享 |
| `/evolve` | 将相关 Instinct 聚类为可复用 Skill |
| `/prune` | 删除过期的 pending Instinct（30 天 TTL） |
| `/learn` | 会话中提取模式 |
| `/learn-eval` | 提取、评估并保存模式 |

每个 Instinct 包含置信度评分，支持导入/导出以实现团队间共享。

---

## 记忆持久化

通过会话生命周期 Hook 实现跨会话记忆持久化：

| Hook 脚本 | 功能 |
|----------|------|
| `session-start.js` | 会话开始时加载上下文 |
| `session-end.js` | 会话结束时保存状态 |
| `pre-compact.js` | 压缩前保存状态 |
| `suggest-compact.js` | 战略性压缩建议 |
| `evaluate-session.js` | 从会话中提取模式 |

**战略性压缩**（strategic-compact）：在逻辑断点处建议 `/compact`，而非等到 95% 上下文自动压缩。

压缩最佳实践：
- 在研究/探索完成后、里程碑达成后、调试完成后压缩
- **不要**在实现中途压缩（会丢失变量名、文件路径、中间状态）
- 推荐设置：`CLAUDE_AUTOCOMPACT_PCT_OVERRIDE: 50`（更早压缩以保持质量）

---

## 安装

### 方式一：Plugin 安装（推荐）

```bash
# 从 Plugin Marketplace 安装
/plugin marketplace add affaan-m/everything-claude-code
/plugin install everything-claude-code@everything-claude-code
```

> **注意**：Rules 需手动安装（Plugin 系统的限制），安装到 `~/.claude/rules/` 或 `.claude/rules/`。

### 方式二：手动安装

```bash
git clone https://github.com/affaan-m/everything-claude-code.git
cd everything-claude-code
npm install

# 选择语言生态安装
./install.sh typescript   # macOS/Linux
.\install.ps1 typescript   # Windows
# 或
npx ecc-install typescript
```

v1.9.0 支持基于 manifest 的选择性安装——可以只安装所需的组件。

### Token 优化建议

```json
{
  "model": "sonnet",
  "env": {
    "MAX_THINKING_TOKENS": "10000",
    "CLAUDE_AUTOCOMPACT_PCT_OVERRIDE": "50",
    "CLAUDE_CODE_SUBAGENT_MODEL": "haiku"
  }
}
```

| 设置 | 默认值 | 推荐值 | 效果 |
|------|--------|--------|------|
| `model` | opus | sonnet | ~60% 成本降低 |
| `MAX_THINKING_TOKENS` | 31,999 | 10,000 | ~70% thinking 成本降低 |
| `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` | 95 | 50 | 更早压缩，保持质量 |

---

## 工作流示例

### TDD 开发流程

```
/everything-claude-code:plan "Add user authentication with OAuth"
  → planner agent 创建实现蓝图

/tdd
  → tdd-guide agent 强制先写测试

/code-review
  → code-reviewer agent 审查代码质量
```

### 典型交互模式

```
用户命令 → 命令触发 Agent（受限工具+模型）
  → Agent 引用 Skill（领域知识）
  → Hook 在工具事件时自动触发
  → Rules 始终生效作为背景指导
```

---

## 生态工具

### AgentShield

安全审计工具，用于扫描 Claude Code 配置中的安全隐患。

```bash
npx ecc-agentshield scan
```

- 1,282 个测试
- 102 条静态分析规则
- 5 个扫描类别

### Skill Creator

`/skill-create` 命令支持本地分析，也可通过 GitHub App 获取高级功能。

### ECC Tools GitHub App

Marketplace 应用，提供 free/pro/enterprise 三个层级。

---

## 版本历史

| 版本 | 日期 | 亮点 |
|------|------|------|
| **v1.9.0** | 2026-03 | Manifest 选择性安装、6 个新 Agent（TS/Java/Kotlin/PyTorch）、SQLite 状态存储、12 语言生态规则 |
| **v1.8.0** | 2026-03 | "Harness Performance System" 重新定位、Hook 可靠性重构、`ECC_HOOK_PROFILE` 运行时控制、997 测试 |
| **v1.7.0** | 2026-02 | Codex App + CLI 支持、5 个商业/内容 Skill、992 测试 |
| **v1.6.0** | 2026-02 | Codex CLI 支持、AgentShield 集成（1,282 测试/102 规则）、GitHub Marketplace App |
| **v1.4.0** | 2026-02 | 交互式安装向导、PM2 & 多 Agent 编排、多语言规则架构、中文翻译 |
| **v1.3.0** | 2026-02 | OpenCode 完整集成（12 Agent/24 命令/16 Skill/3 原生工具） |
| **v1.2.0** | 2026-02 | Python/Django + Java Spring Boot 支持、会话管理、Continuous Learning v2 |

---

## 项目统计

| 指标 | 数值 |
|------|------|
| Stars | ~112k |
| Forks | ~14.6k |
| 贡献者 | 113 |
| 提交数 | 816 |
| Release | 11 |
| 内部测试 | 997+ |
| 支持语言 | 7（English、Portuguese、简体中文、繁体中文、日语、韩语、Turkish） |
| 代码构成 | JavaScript 81.5%、Python 6.3%、Rust 5.8%、Shell 4.6%、TypeScript 1.8% |

> **免责声明**：以上数据基于 2026 年 3 月 GitHub 仓库快照，可能已过时。

## 局限性

- **依赖宿主工具**：ECC 不是一个独立的 Agent，必须安装在 Claude Code/Cursor/Codex/OpenCode 等工具上
- **Token 开销**：125+ Skill、34 Rule 和 28 Agent 会增加系统提示的 Token 消耗——建议配合 Token 优化设置使用
- **MCP 管理**：建议保持 MCP 服务器 < 10 个、工具 < 80 个，每个 MCP 工具描述都会消耗 Token
- **Plugin 限制**：Rules 需手动安装，Plugin 系统尚不支持自动分发 Rules

## 证据来源

| 数据 | 来源 |
|------|------|
| 项目结构、组件数量 | GitHub README + 仓库目录结构 |
| 版本历史 | CHANGELOG.md + Release 页面 |
| 安装方式 | README.md 安装章节 |
| 跨工具架构 | README.md "Cross-Harness Support" 章节 |
| AgentShield | README.md "Ecosystem Tools" 章节 |
