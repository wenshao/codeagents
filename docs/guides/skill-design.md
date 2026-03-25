# Skill 设计指南

> 本文介绍各终端 AI 编程代理的 Skill（技能）系统——什么是 Skill、如何创建、跨工具兼容性以及最佳实践。

## 什么是 Skill

Skill 是终端 AI 编程代理的**命令扩展机制**。用户通过 `/command` 斜杠命令调用 Skill，代理根据 Skill 中定义的提示词和配置执行特定任务。

各工具的 Skill 实现：

| 工具 | Skill 文件 | 加载路径 | 说明 |
|------|-----------|----------|------|
| **Claude Code** | `SKILL.md`（YAML Frontmatter） | `~/.claude/skills/`、`<project>/.claude/skills/` | 最成熟，支持条件激活、插件分发 |
| **Gemini CLI** | `SKILL.md`（TypeScript 接口） | `~/.gemini/skills/`、`.gemini/skills/`、`~/.agents/skills/`、`.agents/skills/` | 支持 `activate_skill` 工具动态激活 |
| **Kimi CLI** | `SKILL.md`（标准 + Flow） | builtin → user → project 三层 | 独特的 Flow Skill：Mermaid/D2 流程图编排 |
| **Codex CLI** | 斜杠命令（内置） | 代码内注册 | 28 个内置命令，暂无用户自定义 Skill 文件 |
| **Copilot CLI** | `.agent.md` / `.agent.yaml` | 项目目录 | 自定义代理，类似 Skill |

## SKILL.md Frontmatter 格式

Claude Code 的 SKILL.md 是最完整的 Skill 定义格式。以下字段基于 v2.1.81 二进制逆向分析确认：

```markdown
---
name: 技能显示名
description: 技能描述（用于模型判断何时调用）
user-invocable: true          # 是否在 / 菜单中显示
disable-model-invocation: false # 是否禁止模型主动调用
allowed-tools: ["Bash", "Edit", "Read"]  # 允许使用的工具白名单
argument-hint: "<参数说明>"    # 参数提示（如 "<文件路径>"）
when_to_use: "当用户要求..."   # 触发条件描述
model: sonnet                  # 使用的模型（可选，默认继承会话模型）
effort: high                   # 推理努力级别
context: fork                  # 执行上下文（fork = 独立上下文，不污染主会话）
shell: bash                    # Shell 类型
paths: ["*.py", "src/**"]      # 条件激活——仅当用户操作匹配文件时激活
---

你的技能提示内容...
可以使用 ${CLAUDE_SKILL_DIR} 引用技能所在目录。
```

### 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `name` | string | 是 | 技能名称，显示在 `/` 菜单中 |
| `description` | string | 是 | 描述文本，LLM 用于判断何时调用 |
| `user-invocable` | boolean | 否 | 默认 `true`，设为 `false` 则不在菜单显示（仅模型可调用） |
| `disable-model-invocation` | boolean | 否 | 默认 `false`，设为 `true` 则仅用户可手动调用 |
| `allowed-tools` | string[] | 否 | 工具白名单，限制技能可使用的工具范围 |
| `argument-hint` | string | 否 | 参数提示文本 |
| `when_to_use` | string | 否 | 触发条件描述 |
| `model` | string | 否 | 模型覆盖（`sonnet`、`opus`、`haiku`） |
| `effort` | string | 否 | 推理努力级别 |
| `context` | string | 否 | `fork` 创建独立上下文执行 |
| `shell` | string | 否 | Shell 类型 |
| `paths` | string[] | 否 | 条件激活的 glob 模式数组 |

## 设计原则：何时创建 Skill

### 适合创建 Skill 的场景

1. **重复性工作流**：每次都需要相同步骤的任务（如代码审查、提交、发布）
2. **需要工具限制**：希望限制 LLM 只使用特定工具（如只读分析不允许写入）
3. **团队共享规范**：项目级 Skill 提交到 Git，团队成员统一使用
4. **复杂多步骤**：需要编排多个步骤的工作流（审查 → 修复 → 测试 → 提交）

### 不适合创建 Skill 的场景

1. **一次性任务**：直接用自然语言描述即可
2. **高度动态**：每次执行逻辑完全不同的任务
3. **简单命令**：一个 Bash 命令就能完成的事情

## 内置 Skill 示例

### /review —— 代码审查

```markdown
---
name: review
description: 审查代码变更，提供改进建议
user-invocable: true
allowed-tools: ["Bash", "Read", "Glob", "Grep"]
context: fork
---

获取当前 diff 或 PR 信息，分析代码变更：
1. 检查代码风格和一致性
2. 发现潜在 bug 和安全问题
3. 评估可读性和可维护性
4. 提出具体改进建议
```

### /simplify —— 代码简化

```markdown
---
name: simplify
description: 审查已修改代码的复用性、质量和效率
user-invocable: true
allowed-tools: ["Bash", "Read", "Glob", "Grep", "Edit"]
---

分析当前变更中的代码，关注：
1. 重复代码提取为共享函数
2. 过度复杂的逻辑简化
3. 性能优化机会
4. 更地道的语言特性使用
```

### /loop —— 周期执行

```markdown
---
name: loop
description: 按间隔重复执行命令
user-invocable: true
argument-hint: "<间隔> <命令>"
---

解析用户参数中的间隔时间和命令，按指定间隔重复执行。
默认间隔 10 分钟。示例：/loop 5m /review
```

### /commit —— 智能提交

```markdown
---
name: commit
description: 分析变更并生成提交消息
user-invocable: true
allowed-tools: ["Bash", "Read"]
---

1. 运行 git diff --staged 获取暂存变更
2. 分析变更的性质和目的
3. 按项目的 Conventional Commits 格式生成提交消息
4. 执行 git commit
```

## 跨工具 Skill 兼容性

### Gemini CLI 技能格式

Gemini CLI 的技能使用 TypeScript 接口定义，加载层级：内置 → 扩展 → 用户（`~/.gemini/skills/`）→ 项目（`.gemini/skills/`）。

```typescript
// Gemini 内部 Skill 接口
{
  name: string,        // 唯一标识
  description: string, // 用户可见描述
  body: string,        // 提示内容
  isBuiltin: boolean,  // 是否内置
  disabled: boolean,   // 管理控制
  location: string     // 文件路径
}
```

### Kimi CLI 技能格式

Kimi CLI 支持两种 Skill：
- **标准 Skill**：类似 Claude Code 的 SKILL.md 指令文件
- **Flow Skill**：使用 Mermaid 或 D2 流程图定义多步骤工作流

### Claude Code 插件到 Qwen Code 的转换

Qwen Code 是 Gemini CLI 的下游分叉项目。通过 `claude-converter` 等社区工具，可以将 Claude Code 的插件结构转换为 Qwen Code 兼容格式：

```
Claude Code 插件结构          Qwen Code 兼容结构
.claude-plugin/               .qwen/skills/ 或 .gemini/skills/
  plugin.json        →        （元数据合并到 SKILL.md frontmatter）
  commands/          →        SKILL.md 文件
  skills/            →        SKILL.md 文件
  hooks/             →        settings.json hooks 配置
```

> 注意：转换不是 100% 等价——Claude Code 的 `context: fork`、`allowed-tools` 白名单等高级特性在 Qwen/Gemini 中可能没有直接对应。

## 最佳实践

### 1. 使用 allowed-tools 白名单

始终为 Skill 指定 `allowed-tools`，限制其可使用的工具范围。这是最重要的安全措施：

```yaml
# 只读分析技能——禁止写入
allowed-tools: ["Read", "Glob", "Grep", "Bash"]

# 代码修改技能——允许编辑
allowed-tools: ["Read", "Edit", "Bash", "Glob", "Grep"]
```

### 2. 合理选择模型

对于简单任务使用轻量模型，复杂任务使用强力模型：

```yaml
# 简单格式化任务
model: haiku

# 复杂代码审查
model: sonnet

# 架构级分析
model: opus
```

### 3. 使用 context: fork 隔离上下文

对于独立的分析任务，使用 `context: fork` 避免污染主会话上下文：

```yaml
context: fork  # 独立上下文，完成后结果返回主会话
```

适用场景：代码审查、安全扫描、依赖分析等不需要修改主会话状态的任务。

### 4. 提供清晰的参数说明

```yaml
argument-hint: "<文件路径或 PR 编号>"
```

### 5. 条件激活（仅在相关文件操作时加载）

```yaml
# 仅在操作 Python 文件时激活
paths: ["*.py", "**/*.py"]
```

这对于项目特定 Skill 很有用——例如 Django 项目的数据库迁移 Skill 只在操作 `models.py` 时激活。

### 6. Skill 放置位置

| 位置 | 路径 | 用途 |
|------|------|------|
| 用户全局 | `~/.claude/skills/my-skill/SKILL.md` | 个人工作流（所有项目通用） |
| 项目共享 | `<project>/.claude/skills/my-skill/SKILL.md` | 团队共享（提交到 Git） |
| 附加目录 | `--add-dir <path>` 指定目录的 `.claude/skills/` | 运行时附加 |

### 7. Skill 提示词编写要点

- **明确步骤**：按编号列出执行步骤，LLM 更容易遵循
- **指定输出格式**：说明期望的输出格式（Markdown、JSON、diff 等）
- **包含约束**：明确说明不应该做什么
- **引用变量**：使用 `${CLAUDE_SKILL_DIR}` 引用技能目录中的辅助文件

```markdown
---
name: api-check
description: 检查 API 端点的安全性
allowed-tools: ["Read", "Grep", "Glob"]
context: fork
paths: ["**/routes/**", "**/api/**"]
---

分析当前项目的 API 端点安全性：

1. 使用 Grep 搜索所有路由定义
2. 检查每个端点是否有认证中间件
3. 检查输入验证是否完整
4. 检查是否有 SQL 注入风险

输出格式：Markdown 表格，列出每个端点的安全状态。
不要修改任何文件。
```

## 相关资源

- Claude Code Skills 文档：`docs/tools/claude-code/05-skills.md`
- Gemini CLI 技能系统：`docs/tools/gemini-cli/05-policies.md`
- Kimi CLI Skill 系统：`docs/tools/kimi-cli/01-overview.md`
- 配置示例对比：`docs/guides/config-examples.md`
