# Cursor CLI

**开发者：** Cursor (Anysphere Inc.)
**许可证：** 专有
**官网：** [cursor.com](https://www.cursor.com/)
**文档：** [docs.cursor.com](https://docs.cursor.com/)
**源码：** 闭源
**最后更新：** 2026-03

## 概述

Cursor 是一款基于 VS Code 深度分支（fork）的 AI 原生代码编辑器。与简单的插件集成不同，Cursor 在编辑器核心层面重新设计了 AI 交互体验，将大语言模型能力融入代码编写、编辑、调试的全流程。其 CLI 模式允许从终端启动和控制 Cursor 编辑器，同时提供 Background Agent 功能实现完全自主的云端代码任务执行。

Cursor 继承了 VS Code 的完整生态系统，包括扩展市场、主题、快捷键绑定和设置同步，使得 VS Code 用户可以零成本迁移。同时在此基础上增加了 Tab 智能补全、Cmd+K 内联编辑、Chat 面板、Agent 模式、Composer 多文件编辑等 AI 原生功能。

## 核心功能

### Tab 智能补全

Cursor 的 Tab 补全远超传统的单行代码建议。它能够：

- **多行补全**：预测并生成完整的代码块，包括函数体、条件分支等
- **上下文感知**：理解当前文件及项目中其他文件的代码上下文
- **光标预测**：补全后自动将光标移动到下一个可能需要编辑的位置
- **差异预测**：在编辑已有代码时，预测你接下来要做的修改

按 `Tab` 接受建议，按 `Esc` 拒绝。补全模型针对低延迟进行了优化，通常在 200ms 以内返回结果。

### 内联编辑 (Cmd+K / Ctrl+K)

选中代码后按 `Cmd+K`（macOS）或 `Ctrl+K`（Windows/Linux），在内联输入框中用自然语言描述修改意图：

```
# 示例操作
1. 选中一个函数
2. 按 Cmd+K
3. 输入："添加错误处理和日志记录"
4. AI 直接在编辑器内修改代码
```

也可以不选中代码直接按 `Cmd+K`，AI 会在光标位置生成新代码。内联编辑适合小范围的精确修改。

### Chat 面板 (Cmd+L / Ctrl+L)

按 `Cmd+L` 打开右侧 Chat 面板，支持对话式编程：

- 提问代码相关问题，获取解释
- 请求生成代码片段
- 使用 `@` 引用系统精确指定上下文
- 点击 "Apply" 将 Chat 中生成的代码应用到编辑器

### Agent 模式 (Cmd+I / Ctrl+I)

Agent 模式是 Cursor 最强大的交互方式，AI 可以自主执行多步骤任务：

- 自主规划和执行复杂任务
- 搜索和阅读项目文件
- 跨多个文件进行编辑
- 运行终端命令（需用户确认）
- 自动修复 linter 错误和测试失败
- 创建新文件和目录

### Composer（多文件协同编辑）

Composer 允许在一次交互中修改多个文件，适合需要跨文件重构的场景。Agent 模式中已内置 Composer 能力。

## Background Agent

Background Agent 是 Cursor 的远程异步代码执行功能，允许将编程任务委托给云端 AI 代理。

### 工作原理

1. **启动任务**：在 Cursor 中描述任务，或从 GitHub Issue 触发
2. **云端执行**：任务在 Cursor 托管的云端虚拟机（VM）中运行
3. **环境克隆**：自动克隆仓库、安装依赖、配置环境
4. **自主工作**：AI 代理自主编写代码、运行测试、修复问题
5. **创建 PR**：完成后自动创建 GitHub Pull Request

### 特性

- **异步工作流**：无需保持编辑器打开，任务在后台持续运行
- **GitHub 集成**：可从 GitHub Issue 直接触发，完成后自动创建 PR
- **环境隔离**：每个任务运行在独立的安全沙箱中
- **实时日志**：可在 Cursor 中查看任务执行进度和日志
- **自动安装依赖**：根据项目配置自动设置开发环境

### 使用场景

- 修复简单 Bug（从 Issue 描述自动修复）
- 添加测试用例
- 代码重构和迁移
- 文档生成
- 依赖升级

### 配置

在项目根目录创建 `.cursor/agent.json` 配置 Background Agent 环境：

```json
{
  "setup": [
    "npm install",
    "npm run build"
  ],
  "lint": "npm run lint",
  "test": "npm run test"
}
```

## Rules 系统

Rules 系统允许为 AI 提供项目特定的指令和上下文，类似于其他工具的 system prompt 定制。

### 规则类型

| 类型 | 说明 | 触发方式 |
|------|------|----------|
| **Always** | 始终包含在上下文中 | 每次对话自动加载 |
| **Auto Attached** | 当匹配的文件被引用时自动附加 | 基于 glob 模式匹配 |
| **Agent Requested** | AI 根据任务描述自主决定是否使用 | AI 按需读取 |
| **Manual** | 需要用户通过 `@rules` 手动引用 | 用户显式引用 |

### 项目级规则

在项目中创建 `.cursor/rules/` 目录，每个规则为一个 `.mdc` 文件：

```
.cursor/
└── rules/
    ├── general.mdc        # 通用项目规则
    ├── frontend.mdc       # 前端代码规则
    ├── testing.mdc        # 测试规范
    └── api-design.mdc     # API 设计规范
```

规则文件格式（`.mdc`）：

```markdown
---
description: 前端 React 组件开发规范
globs: ["src/components/**/*.tsx", "src/components/**/*.ts"]
alwaysApply: false
---

- 使用函数组件和 React Hooks，不使用 class 组件
- 组件文件使用 PascalCase 命名
- 每个组件必须导出 Props 类型定义
- 使用 Tailwind CSS 进行样式处理
```

### 用户级规则

在 Cursor 设置中配置全局规则，适用于所有项目：

```
Cursor Settings > General > Rules for AI
```

用户级规则优先级低于项目级规则。

## @ 引用系统

Cursor 提供丰富的 `@` 引用语法，用于在 Chat 和 Agent 模式中精确控制上下文：

| 引用语法 | 说明 | 示例 |
|----------|------|------|
| `@file` | 引用项目中的特定文件 | `@src/utils/auth.ts` |
| `@folder` | 引用整个文件夹的结构和内容 | `@src/components` |
| `@code` | 引用特定的代码符号（函数、类等） | `@handleSubmit` |
| `@web` | 搜索网络获取最新信息 | `@web React 19 新特性` |
| `@docs` | 引用已索引的第三方文档 | `@docs Next.js` |
| `@codebase` | 搜索整个代码库 | `@codebase 用户认证逻辑` |
| `@git` | 引用 Git 历史和差异 | `@git 最近的修改` |
| `@definitions` | 引用符号定义 | `@definitions UserType` |
| `@chat` | 引用之前的对话 | `@chat 上一轮讨论` |

### 使用示例

```
# 在 Chat 中引用文件并提问
@src/api/users.ts 这个文件中的错误处理逻辑有什么问题？

# 引用文档辅助开发
@docs Prisma 如何定义一对多关系？

# 搜索整个代码库
@codebase 找到所有处理用户认证的代码

# 引用文件夹
@src/components 这些组件的命名是否一致？
```

## MCP 支持

Cursor 支持模型上下文协议（Model Context Protocol），允许接入外部工具和数据源。

### 配置方式

在 Cursor 设置中配置 MCP 服务器，或在项目根目录创建 `.cursor/mcp.json`：

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/dir"]
    },
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_TOKEN": "your-token"
      }
    },
    "database": {
      "url": "http://localhost:8080/sse"
    }
  }
}
```

### MCP 工具在 Agent 中的使用

配置 MCP 服务器后，其提供的工具会自动出现在 Agent 模式中。AI 可以自主调用这些工具完成任务，例如：

- 通过 GitHub MCP 服务器查询 Issue 和 PR
- 通过数据库 MCP 服务器查询数据结构
- 通过文件系统 MCP 服务器访问受限目录

MCP 支持两种传输协议：**stdio**（本地进程）和 **SSE**（远程服务器）。

## 模型支持

Cursor 支持多种 AI 模型，可在不同场景下灵活切换：

| 模型 | 提供商 | 用途 | 说明 |
|------|--------|------|------|
| Claude 4 Sonnet | Anthropic | Chat、Agent、内联编辑 | 默认推荐模型 |
| Claude 3.5 Sonnet | Anthropic | Chat、Agent、内联编辑 | 高性价比选择 |
| Claude 3.5 Haiku | Anthropic | Tab 补全、轻量任务 | 低延迟 |
| GPT-4o | OpenAI | Chat、Agent | 多模态能力 |
| GPT-4o mini | OpenAI | 轻量任务 | 快速响应 |
| Gemini 2.5 Pro | Google | Chat、Agent | 长上下文 |
| cursor-small | Cursor | Tab 补全 | 专为补全优化 |

### 自定义 API 端点

支持接入自定义模型 API（兼容 OpenAI API 格式）：

```
Cursor Settings > Models > Add Model
```

配置项：
- **API Base URL**：自定义端点地址
- **API Key**：认证密钥
- **Model Name**：模型标识符

## 安装与配置

### macOS

```bash
# 通过 Homebrew 安装
brew install --cask cursor

# 或从官网下载 .dmg 安装包
# https://www.cursor.com/downloads
```

### Windows

```bash
# 通过 winget 安装
winget install Cursor.Cursor

# 或从官网下载 .exe 安装程序
```

### Linux

```bash
# 下载 AppImage
# https://www.cursor.com/downloads

# 赋予执行权限
chmod +x cursor-*.AppImage

# 运行
./cursor-*.AppImage
```

### CLI 安装

Cursor CLI 通常随编辑器自动安装。如果 `cursor` 命令不可用，可手动安装：

```
Cursor > Command Palette (Cmd+Shift+P) > "Install 'cursor' command in PATH"
```

安装后验证：

```bash
cursor --version
```

## CLI 命令详情

```bash
# 在当前目录打开 Cursor
cursor .

# 打开指定项目目录
cursor /path/to/project

# 打开文件
cursor file.py

# 打开文件并跳转到指定行
cursor file.py:42

# 打开文件并跳转到指定行和列
cursor file.py:42:10

# 对比两个文件
cursor --diff file1.py file2.py

# 以新窗口打开
cursor --new-window /path/to/project

# 复用已有窗口
cursor --reuse-window /path/to/project

# 在当前窗口打开文件
cursor --goto file.py:42

# 等待文件关闭（用于 git editor 等场景）
cursor --wait file.py

# 查看版本
cursor --version

# 查看帮助
cursor --help

# 列出已安装的扩展
cursor --list-extensions

# 安装扩展
cursor --install-extension <extension-id>

# 卸载扩展
cursor --uninstall-extension <extension-id>
```

### 作为 Git 编辑器使用

```bash
# 设置 Cursor 为默认 Git 编辑器
git config --global core.editor "cursor --wait"

# 设置为 Git diff 工具
git config --global diff.tool cursor
git config --global difftool.cursor.cmd "cursor --diff \$LOCAL \$REMOTE"
```

## Privacy Mode

Privacy Mode 确保代码隐私安全，适用于处理敏感代码的企业用户。

### 工作方式

| 项目 | Privacy Mode 开启 | Privacy Mode 关闭 |
|------|-------------------|-------------------|
| 代码存储 | 不存储在 Cursor 服务器 | 可能缓存用于改善服务 |
| 模型训练 | 代码不用于训练 | 代码不用于训练 |
| 遥测数据 | 仅发送基本使用统计 | 发送使用统计和匿名数据 |
| 代码片段 | 仅发送给 AI 提供商处理 | 仅发送给 AI 提供商处理 |

### 启用方式

```
Cursor Settings > General > Privacy Mode > Enable
```

Business 和 Enterprise 计划默认强制开启 Privacy Mode。

## 定价

| 计划 | 价格 | 补全次数 | 高级请求 | 主要功能 |
|------|------|----------|----------|----------|
| **Hobby** | 免费 | 2000 次 | 50 次 | 基础 AI 功能，社区支持 |
| **Pro** | $20/月 | 无限 | 500 次/月 | 无限补全，高级模型，Background Agent |
| **Business** | $40/月/人 | 无限 | 500 次/月 | 团队管理，强制 Privacy Mode，管理员控制，SAML SSO |
| **Enterprise** | 联系销售 | 自定义 | 自定义 | 自托管选项，专属支持，自定义安全策略 |

**说明：**
- 补全次数指 Tab 自动补全的使用次数
- 高级请求指使用 Claude 4 Sonnet、GPT-4o 等高级模型的 Chat/Agent 请求
- 高级请求用尽后自动切换到较慢的模型（仍可继续使用）
- Pro 计划可按需购买额外的高级请求包

## 快捷键

### 核心 AI 快捷键

| 功能 | macOS | Windows/Linux |
|------|-------|---------------|
| 打开 Chat 面板 | `Cmd+L` | `Ctrl+L` |
| 打开 Agent/Composer | `Cmd+I` | `Ctrl+I` |
| 内联编辑 | `Cmd+K` | `Ctrl+K` |
| 接受 Tab 补全 | `Tab` | `Tab` |
| 拒绝补全 | `Esc` | `Esc` |
| 接受部分补全（逐词） | `Cmd+→` | `Ctrl+→` |
| 终端内联编辑 | `Cmd+K`（终端中） | `Ctrl+K`（终端中） |

### 编辑器快捷键（继承自 VS Code）

| 功能 | macOS | Windows/Linux |
|------|-------|---------------|
| 命令面板 | `Cmd+Shift+P` | `Ctrl+Shift+P` |
| 快速打开文件 | `Cmd+P` | `Ctrl+P` |
| 打开终端 | `` Cmd+` `` | `` Ctrl+` `` |
| 全局搜索 | `Cmd+Shift+F` | `Ctrl+Shift+F` |
| 跳转到定义 | `F12` | `F12` |
| 重命名符号 | `F2` | `F2` |

## 使用场景

- **最适合**：需要 IDE 级体验的开发者、VS Code 用户、前端/全栈开发
- **适合**：团队协作、需要多模型切换、希望异步委托任务（Background Agent）
- **不太适合**：纯终端工作流、服务器端开发、CI/CD 自动化、需要开源审计

## 与其他工具对比

| 特性 | Cursor | Claude Code | Aider | Windsurf | GitHub Copilot |
|------|--------|-------------|-------|----------|----------------|
| 界面 | IDE | CLI | CLI | IDE | IDE 插件 |
| 多模型支持 | ✓ | ✗ | ✓ | ✓ | ✗ |
| Background Agent | ✓ | ✗ | ✗ | ✗ | ✗ |
| Agent 模式 | ✓ | ✓ | ✗ | ✓ | ✓ |
| Git 集成 | 基础 | 强大 | 最佳 | 基础 | 基础 |
| MCP 支持 | ✓ | ✓ | ✗ | ✓ | ✗ |
| Rules 系统 | ✓ | ✓ | ✓ | ✓ | ✓ |
| 开源 | ✗ | ✗ | ✓ | ✗ | ✗ |
| 终端原生 | ✗ | ✓ | ✓ | ✗ | ✗ |
| Tab 补全 | ✓ | ✗ | ✗ | ✓ | ✓ |
| Privacy Mode | ✓ | ✗ | N/A | ✓ | ✓ |
| 免费版 | ✓ | ✗ | ✓ | ✓ | ✓ |

## 优势

1. **VS Code 完全兼容**：继承所有 VS Code 扩展、主题和配置，迁移成本为零
2. **多模型灵活切换**：支持 Anthropic、OpenAI、Google 等多家模型提供商
3. **UI/UX 精良**：AI 交互体验流畅，内联编辑、Chat、Agent 模式各有侧重
4. **Background Agent**：云端异步执行任务，适合长时间运行或批量工作
5. **丰富的上下文控制**：通过 `@` 引用系统和 Rules 精确控制 AI 行为
6. **MCP 生态扩展**：通过 MCP 协议接入外部工具和数据源

## 劣势

1. **非纯 CLI 工具**：主要是 IDE，CLI 功能仅限于启动和基本操作
2. **专有闭源软件**：代码不可审计，无法自行修改或验证安全性
3. **订阅费用**：Pro 版 $20/月，Business $40/月，长期使用成本较高
4. **依赖 Electron**：内存占用较高，比原生终端工具更重
5. **网络依赖**：AI 功能需要联网，离线时退化为普通编辑器
6. **供应商锁定**：Rules 和配置格式为 Cursor 专有，不可迁移

## 资源链接

- [官方文档](https://docs.cursor.com/)
- [Changelog](https://www.cursor.com/changelog)
- [社区论坛](https://forum.cursor.com/)
- [GitHub 集成文档](https://docs.cursor.com/background-agent)
- [Rules 文档](https://docs.cursor.com/context/rules)
- [MCP 配置文档](https://docs.cursor.com/context/model-context-protocol)
