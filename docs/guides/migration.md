# 7. 工具迁移指南

## 简介

随着 AI 编程工具生态的快速发展，开发者经常需要在不同工具之间迁移。常见的迁移场景包括：

- **从 IDE 集成迁移到终端工具**：如 Cursor → Claude Code，追求更轻量的工作流
- **从开源工具迁移到商业工具**：如 Aider → Claude Code，获取更强的模型能力
- **从一个终端工具迁移到另一个**：如 Gemini CLI → Claude Code，或反向迁移
- **团队标准化**：统一团队的 AI 编程工具栈，减少维护成本
- **模型偏好变化**：因模型能力升级而切换到对应厂商的原生工具

迁移的核心挑战不在于安装新工具，而在于**配置的转换、工作流的适应和习惯的改变**。本指南提供各工具间的配置映射关系和实操转换示例，帮助你平滑完成迁移。

---

## 配置映射表

### 项目指令文件

项目指令文件是 AI 编程工具的核心配置，定义了 AI 在项目中的行为规范。各工具的对应关系如下：

| 概念 | Claude Code | Codex CLI | Cursor | Gemini CLI | Qwen Code | Aider |
|------|-------------|-----------|--------|------------|-----------|-------|
| **项目指令** | `CLAUDE.md` | `CODEX.md` | `.cursor/rules/*.mdc` | `GEMINI.md` | `.qwen/system.md` | `.aider.conf.yml` |
| **全局指令** | `~/.claude/CLAUDE.md` | `~/.codex/instructions.md` | Cursor Settings > Rules for AI | `~/.gemini/GEMINI.md` | `~/.qwen/settings.json` | `~/.aider.conf.yml` |
| **目录级指令** | 子目录 `CLAUDE.md` | 子目录 `CODEX.md` | `.cursor/rules/*.mdc`（glob 匹配） | 子目录 `.gemini/GEMINI.md` | - | - |

### 设置文件

| 概念 | Claude Code | Codex CLI | Cursor | Gemini CLI | Qwen Code | Aider |
|------|-------------|-----------|--------|------------|-----------|-------|
| **用户设置** | `~/.claude/settings.json` | `~/.codex/config.yaml` | Cursor Settings UI | `~/.gemini/settings.json` | `~/.qwen/settings.json` | `~/.aider.conf.yml` |
| **项目设置** | `.claude/settings.json` | - | `.cursor/agent.json` | `.gemini/settings.json` | `.qwen/settings.json` | `.aider.conf.yml`（项目根） |
| **本地覆盖** | `.claude/settings.local.json` | - | - | - | - | `.aider.env` |

### MCP 配置

| 工具 | MCP 配置位置 | 工具命名格式 |
|------|-------------|-------------|
| **Claude Code** | `~/.claude/settings.json` 或 `.claude/settings.json` 中的 `mcpServers` | `mcp__serverName__toolName`（双下划线） |
| **Cursor** | `.cursor/mcp.json` 或 Cursor Settings | `mcp_serverName_toolName` |
| **Gemini CLI** | `~/.gemini/settings.json` 或 `.gemini/settings.json` 中的 `mcp` | `mcp_{serverName}_{toolName}` |
| **Qwen Code** | `~/.qwen/settings.json` 中的 `mcp` | 同 Gemini CLI |
| **Copilot CLI** | 内置 GitHub MCP，支持自定义 | - |
| **Codex CLI / Aider** | 不支持 MCP | - |

### 忽略文件

| 工具 | 忽略文件 | 格式 |
|------|---------|------|
| **Claude Code** | `.claudeignore` | 类 `.gitignore` |
| **Gemini CLI** | `.geminiignore` | 类 `.gitignore` |
| **Cursor** | `.cursorignore` | 类 `.gitignore` |
| **Aider** | `.aiderignore` | 类 `.gitignore` |
| **Qwen Code** | `.qwenignore` | 类 `.gitignore` |

> **提示**：所有忽略文件的语法都兼容 `.gitignore` 格式，因此迁移时可以直接复制内容。

---

## 迁移路径 1: Cursor → Claude Code

### 概述

从 Cursor 迁移到 Claude Code 是最常见的迁移场景之一。核心变化是从 **IDE 图形界面** 切换到 **终端工作流**。

### 配置转换

#### Rules → CLAUDE.md

Cursor 的 `.cursor/rules/*.mdc` 文件需要合并转换为 `CLAUDE.md`。

**转换前**（`.cursor/rules/frontend.mdc`）：
```markdown
---
description: 前端 React 组件开发规范
globs: ["src/components/**/*.tsx"]
alwaysApply: false
---

- 使用函数组件和 React Hooks
- 组件文件使用 PascalCase 命名
- 使用 Tailwind CSS 样式
```

**转换后**（`CLAUDE.md`）：
```markdown
# 项目规范

## 前端组件（src/components/）
- 使用函数组件和 React Hooks，不使用 class 组件
- 组件文件使用 PascalCase 命名
- 使用 Tailwind CSS 进行样式处理

## 测试规范
- 使用 Vitest 运行测试：`npm test`
- 每个组件必须有对应测试文件

## 构建命令
- 开发：`npm run dev`
- 构建：`npm run build`
- 测试：`npm test`
- Lint：`npm run lint`
```

> **注意**：Cursor 的 `globs` 和 `alwaysApply` 机制在 Claude Code 中没有直接对应。Claude Code 会将整个 `CLAUDE.md` 加载到上下文中，因此建议用清晰的标题区分不同区域的规范。

#### MCP 配置转换

**转换前**（`.cursor/mcp.json`）：
```json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": { "GITHUB_TOKEN": "ghp_xxx" }
    }
  }
}
```

**转换后**（`.claude/settings.json`）：
```json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": { "GITHUB_TOKEN": "ghp_xxx" }
    }
  }
}
```

MCP 配置的 JSON 结构基本一致，注意 Claude Code 中工具命名使用**双下划线**（`mcp__github__create_issue`），而 Cursor 使用单下划线。

#### 忽略文件

```bash
# 直接复制即可，语法完全兼容
cp .cursorignore .claudeignore
```

### 工作流差异

| 维度 | Cursor | Claude Code |
|------|--------|-------------|
| **交互方式** | GUI 面板、内联编辑、Tab 补全 | 终端对话、自然语言指令 |
| **文件编辑** | 编辑器内直接修改 | 通过 Read/Edit/Write 工具 |
| **上下文引用** | `@file`、`@codebase` 语法 | 自动搜索（Glob/Grep），或手动提示 |
| **代码补全** | Tab 智能补全 | 无实时补全（专注代理式交互） |
| **多文件操作** | Composer/Agent 模式 | Agent/Task 子代理并行 |
| **Git 操作** | 编辑器内 Git UI | 原生 Git 命令，深度集成 |

### 适应建议

1. **习惯终端工作流**：Claude Code 在终端中运行，建议搭配 tmux 或分屏终端使用
2. **善用 CLAUDE.md**：将所有项目规范集中到 `CLAUDE.md` 中，这是 Claude Code 理解项目的主要入口
3. **利用 Git 集成**：Claude Code 的 Git 集成非常深度，可以直接让它创建提交、PR、分支
4. **探索子代理**：用 Agent/Task 工具替代 Cursor 的 Composer 多文件编辑

---

## 迁移路径 2: Aider → Claude Code

### 概述

Aider 和 Claude Code 都是终端工具，迁移相对平滑。主要差异在于配置格式和 Git 工作流。

### 配置转换

#### .aider.conf.yml → CLAUDE.md + settings.json

**转换前**（`.aider.conf.yml`）：
```yaml
model: claude-sonnet-4
edit-format: diff
auto-commits: yes
auto-test: yes
test-cmd: pytest tests/
cache-prompts: yes
map-tokens: 1024
```

**转换后**：

`CLAUDE.md`（项目规范部分）：
```markdown
# 项目规范

## 测试
- 运行测试：`pytest tests/`
- 每次修改后必须确保测试通过

## 代码风格
- 遵循 PEP 8 规范
- 使用 type hints
```

`.claude/settings.json`（工具配置部分）：
```json
{
  "permissions": {
    "allow": [
      "Bash(pytest tests/)",
      "Bash(python -m pytest)",
      "Read",
      "Glob",
      "Grep"
    ]
  },
  "model": "claude-sonnet-4-6"
}
```

> **关键差异**：Aider 的 `model` 和 `edit-format` 等选项映射到 Claude Code 的 `settings.json`；而项目规范、测试命令等建议写入 `CLAUDE.md`。

#### 忽略文件

```bash
cp .aiderignore .claudeignore
```

### Git 工作流差异

| 维度 | Aider | Claude Code |
|------|-------|-------------|
| **自动提交** | 每次编辑自动提交（默认开启） | 不自动提交，需用户指示 |
| **提交归因** | `Co-Authored-By: aider` | `Co-Authored-By: Claude` |
| **撤销** | `/undo` 撤销上次提交 | checkpoint/rewind 回退 |
| **文件管理** | `/add` `/drop` 手动管理 | 自动搜索项目文件 |
| **分支管理** | 手动切换 | Worktree 隔离并行分支 |

### 适应建议

1. **不再需要 `/add` 文件**：Claude Code 会自动通过 Glob/Grep 搜索文件，无需手动添加到上下文
2. **主动要求提交**：Claude Code 默认不自动提交，需要在对话中明确要求"提交这些更改"
3. **利用多代理**：Aider 是单代理模式，Claude Code 支持 Agent/Task 子代理并行处理
4. **模型选择**：Aider 通过 LiteLLM 支持 100+ 模型，Claude Code 仅支持 Anthropic 系列模型

---

## 迁移路径 3: Claude Code → Copilot CLI

### 概述

从 Claude Code 迁移到 GitHub Copilot CLI 的主要动机通常是 GitHub 生态深度集成的需求。

### 配置转换

#### CLAUDE.md → GitHub 自定义指令

Copilot CLI 目前没有完全等同于 `CLAUDE.md` 的项目指令文件。可以通过以下方式实现类似效果：

- **仓库级**：在 `.github/copilot-instructions.md` 中定义项目规范（GitHub Copilot coding agent 支持）
- **会话级**：在对话开始时手动提供上下文

**转换前**（`CLAUDE.md`）：
```markdown
# 项目规范
- 使用 TypeScript strict 模式
- 测试命令：npm test
- Lint：npm run lint
```

**转换后**（`.github/copilot-instructions.md`）：
```markdown
# 项目规范
- 使用 TypeScript strict 模式
- 测试命令：npm test
- Lint：npm run lint
```

#### MCP 配置差异

Copilot CLI 内置 GitHub MCP 服务器，无需额外配置即可访问 Issues、PR、仓库信息。自定义 MCP 配置方式与 Claude Code 类似但配置位置不同。

#### 设置文件

| Claude Code | Copilot CLI |
|-------------|-------------|
| `~/.claude/settings.json` | Copilot 订阅设置（Web 管理） |
| `.claude/settings.json` | `.github/copilot-instructions.md` |
| `.claudeignore` | 无直接对应 |

### 需要注意的差异

1. **认证方式**：Claude Code 使用 Anthropic API Key 或 Claude Pro/Max 订阅；Copilot CLI 使用 GitHub 账户认证
2. **模型选择**：Claude Code 锁定 Anthropic 模型；Copilot CLI 默认 Claude Sonnet 4.5，可选 GPT-5
3. **Premium Requests**：Copilot CLI 每次交互消耗 premium request 配额，需关注用量
4. **工具生态**：Claude Code 有 13 个官方插件；Copilot CLI 依赖 GitHub 生态

---

## 迁移路径 4: Gemini CLI / Qwen Code → Claude Code

### 概述

Gemini CLI 和 Qwen Code（基于 Gemini CLI 分叉）的架构相似，迁移到 Claude Code 的路径基本一致。

### Gemini CLI → Claude Code

#### GEMINI.md → CLAUDE.md

两者的项目指令文件功能几乎一致，可以直接复制内容：

```bash
# 全局指令
cp ~/.gemini/GEMINI.md ~/.claude/CLAUDE.md

# 项目指令
cp .gemini/GEMINI.md CLAUDE.md
```

> **注意**：Gemini CLI 的 `GEMINI.md` 中可能包含 `## Gemini Added Memories` 区段（由 memory_manager 代理自动维护），迁移时建议审查并清理这些自动记忆内容。

#### settings.json 转换

**转换前**（`~/.gemini/settings.json`）：
```json
{
  "model": "gemini-3-pro",
  "approvalMode": "autoEdit",
  "mcp": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": { "GITHUB_TOKEN": "ghp_xxx" }
    }
  }
}
```

**转换后**（`~/.claude/settings.json`）：
```json
{
  "model": "claude-sonnet-4-6",
  "permissions": {
    "allow": [
      "Read", "Glob", "Grep",
      "Bash(npm test)",
      "Bash(npm run build)"
    ]
  },
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": { "GITHUB_TOKEN": "ghp_xxx" }
    }
  }
}
```

**关键差异**：
- MCP 配置在 Gemini CLI 中位于 `"mcp"` 键下，Claude Code 中位于 `"mcpServers"` 键下
- Gemini CLI 的 `approvalMode` 对应 Claude Code 的 `permissions` 权限控制
- 策略文件格式不同：Gemini CLI 使用 TOML 策略，Claude Code 使用 JSON 权限规则

#### 忽略文件

```bash
cp .geminiignore .claudeignore
```

### Qwen Code → Claude Code

#### 配置结构映射

| Qwen Code | Claude Code |
|-----------|-------------|
| `~/.qwen/settings.json` | `~/.claude/settings.json` |
| `.qwen/settings.json` | `.claude/settings.json` |
| `.qwen/system.md` | `CLAUDE.md` |
| `.qwenignore` | `.claudeignore` |

**转换前**（`~/.qwen/settings.json`）：
```json
{
  "modelProviders": {
    "openai": [{
      "id": "qwen3-coder-plus",
      "baseUrl": "https://dashscope.aliyuncs.com/compatible-mode/v1",
      "envKey": "DASHSCOPE_API_KEY"
    }]
  },
  "permissions": {
    "allow": ["Bash"],
    "ask": ["Edit"]
  }
}
```

**转换后**（`~/.claude/settings.json`）：
```json
{
  "model": "claude-sonnet-4-6",
  "permissions": {
    "allow": [
      "Bash(npm test)",
      "Bash(npm run build)",
      "Read", "Glob", "Grep"
    ]
  }
}
```

> **注意**：Qwen Code 支持多提供商（Qwen/OpenAI/Anthropic/Gemini），而 Claude Code 仅使用 Anthropic 模型。`modelProviders` 配置在 Claude Code 中无对应项。

---

## 通用迁移清单

无论从哪个工具迁移，建议按以下清单逐步完成：

### 安装与认证

- [ ] 安装目标工具并验证版本
- [ ] 配置 API Key 或完成登录认证
- [ ] 验证基础交互（如 `claude "hello"` 或 `gemini "hello"`）

### 项目指令迁移

- [ ] 识别源工具的项目指令文件（CLAUDE.md / CODEX.md / .cursor/rules / GEMINI.md / .aider.conf.yml）
- [ ] 将项目规范、编码标准、常用命令转换到目标工具的指令文件
- [ ] 检查是否有全局指令需要迁移（`~/` 目录下的配置）
- [ ] 验证子目录级指令是否需要特殊处理

### 设置迁移

- [ ] 迁移模型选择偏好
- [ ] 迁移权限/审批模式设置
- [ ] 迁移 MCP 服务器配置（注意键名差异：`mcp` vs `mcpServers`）
- [ ] 迁移 Hook 配置（事件名称和格式可能不同）
- [ ] 迁移忽略文件（直接复制内容即可）

### 工作流适应

- [ ] 熟悉目标工具的交互方式（GUI vs 终端，对话 vs 命令）
- [ ] 了解 Git 集成差异（自动提交 vs 手动提交，checkpoint vs undo）
- [ ] 测试常用开发流程：编辑代码、运行测试、提交变更
- [ ] 探索目标工具的独有功能（子代理、插件、会话恢复等）

### 团队协作

- [ ] 将项目级配置文件（`CLAUDE.md`、`.claude/settings.json` 等）提交到版本控制
- [ ] 将本地配置文件加入 `.gitignore`（如 `.claude/settings.local.json`）
- [ ] 通知团队成员配置变更
- [ ] 更新 CI/CD 流程中的 AI 工具集成

---

## 常见陷阱

### 1. MCP 配置键名混淆

不同工具的 MCP 配置键名不一致，直接复制粘贴会导致配置无效：

```jsonc
// Claude Code：使用 "mcpServers"
{ "mcpServers": { "github": { ... } } }

// Gemini CLI / Qwen Code：使用 "mcp"
{ "mcp": { "github": { ... } } }

// Cursor：独立文件 .cursor/mcp.json，使用 "mcpServers"
{ "mcpServers": { "github": { ... } } }
```

### 2. 忽略项目指令文件

迁移时只关注设置文件，忘记迁移项目指令文件（如 `CLAUDE.md`），导致 AI 缺少项目上下文，生成不符合规范的代码。

**解决方案**：项目指令文件是迁移的**第一优先级**，应该最先处理。

### 3. Git 工作流差异导致冲突

从 Aider（自动提交）迁移到 Claude Code（手动提交），容易遗忘提交变更，导致工作丢失。

**解决方案**：在 `CLAUDE.md` 中明确要求"每次完成修改后提醒我提交变更"。

### 4. 权限模式理解偏差

各工具的权限/审批模式命名不同但含义类似：

| 自主程度 | Claude Code | Codex CLI | Gemini CLI | Cursor |
|---------|-------------|-----------|------------|--------|
| **最保守** | 默认（逐项确认） | `suggest` | `default` | 需确认 |
| **中等** | 部分 `allow` | `auto-edit` | `autoEdit` | Agent 模式 |
| **最自主** | 全部 `allow` | `full-auto` | `yolo` | Autopilot/Background Agent |

### 5. 路径结构差异

忽略不同工具的配置目录结构差异：

```
Claude Code:  ~/.claude/    .claude/     CLAUDE.md
Gemini CLI:   ~/.gemini/    .gemini/     GEMINI.md        .geminiignore
Qwen Code:    ~/.qwen/      .qwen/       .qwen/system.md
Codex CLI:    ~/.codex/      -           CODEX.md
Cursor:        -            .cursor/      -                .cursorignore
Aider:         -             -            -                .aiderignore
```

### 6. 环境变量冲突

同时安装多个工具时，环境变量可能冲突：

```bash
# 确保各工具的 API Key 变量独立
export ANTHROPIC_API_KEY="sk-ant-..."    # Claude Code
export OPENAI_API_KEY="sk-proj-..."      # Codex CLI / Aider
export GEMINI_API_KEY="AI..."            # Gemini CLI
export DASHSCOPE_API_KEY="sk-..."        # Qwen Code
```

### 7. 模型能力差异

不同工具绑定不同模型，迁移后 AI 的行为表现会发生变化。不要期望同一个提示在不同工具中产生完全一致的结果。

**解决方案**：迁移后花时间调整项目指令文件中的提示词，适配新模型的特点。

### 8. 忽略忽略文件（ignore files）

不迁移忽略文件会导致新工具索引不必要的文件（如 `node_modules`、`dist`、`.env` 等），消耗大量 token 且可能泄露敏感信息。

**解决方案**：
```bash
# 一行命令完成所有忽略文件的迁移
for src in .cursorignore .aiderignore .geminiignore .qwenignore; do
  [ -f "$src" ] && cat "$src" >> .claudeignore && echo "已合并 $src"
done
# 去重
sort -u .claudeignore -o .claudeignore
```

---

## 参考资源

- [Claude Code 完整文档](../tools/claude-code/)
- [Cursor CLI 文档](../tools/cursor-cli.md)
- [Aider 文档](../tools/aider/)
- [Gemini CLI 文档](../tools/gemini-cli/)
- [Qwen Code 文档](../tools/qwen-code.md)
- [Codex CLI 文档](../tools/codex-cli/)
- [GitHub Copilot CLI 文档](../tools/copilot-cli/)
- [功能对比表](../comparison/features.md)
