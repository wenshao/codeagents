# Cursor CLI

**开发者：** Cursor
**许可证：** 专有
**官网：** [cursor.com](https://www.cursor.com/)
**文档：** [docs.cursor.com](https://docs.cursor.com/)

## 概述

Cursor 是一款基于 VS Code 的 AI 原生代码编辑器，内置 AI 编程助手。其 CLI 模式允许从终端启动和控制 Cursor，同时提供 Background Agent 功能实现完全自主的代码任务执行。

## 核心功能

### 基础能力
- **AI 原生编辑器**：基于 VS Code 的深度 AI 集成
- **Tab 补全**：智能代码补全，超越单行建议
- **内联编辑 (Cmd+K)**：选中代码后直接用自然语言修改
- **Chat 面板**：对话式编程助手
- **多文件编辑**：跨文件理解和修改代码
- **Composer**：多文件协同编辑的高级功能
- **Agent 模式**：自主规划和执行复杂任务

### 独特功能
- **Background Agent**：云端异步执行任务，无需保持编辑器打开
- **Bug Finder**：AI 驱动的代码缺陷检测
- **@符号引用**：通过 @file、@web、@docs 等精确控制上下文
- **Rules 系统**：项目级 AI 行为配置（.cursor/rules）
- **MCP 支持**：模型上下文协议集成，扩展工具能力
- **Privacy Mode**：代码不存储、不用于训练

## 安装

```bash
# macOS
brew install --cask cursor

# 或从官网下载
# https://www.cursor.com/downloads

# CLI 命令（安装后自动可用）
cursor .                    # 在当前目录打开 Cursor
cursor --diff file1 file2   # 比较文件
```

## 架构

- **基础：** VS Code (Electron)
- **支持的模型：**
  - Claude 3.5 Sonnet, Claude Opus
  - GPT-4, GPT-4o
  - Gemini
  - 自定义 API 端点

## 优势

1. **VS Code 兼容**：继承所有 VS Code 扩展和配置
2. **多模型支持**：可灵活切换不同 AI 提供商
3. **UI/UX 精良**：最佳的 AI 编辑器交互体验
4. **Background Agent**：异步执行任务，适合长时间运行的工作
5. **低迁移成本**：VS Code 用户可无缝迁移

## 劣势

1. **非纯 CLI**：主要是 IDE，CLI 功能有限
2. **专有软件**：非开源，代码不可审计
3. **订阅费用**：Pro 版 $20/月，Business $40/月
4. **依赖 Electron**：比原生终端工具更重

## CLI 命令

```bash
# 打开项目
cursor /path/to/project

# 打开文件到指定行
cursor file.py:42

# 对比两个文件
cursor --diff file1.py file2.py

# 安装 CLI 命令（如果未自动安装）
# Cursor > Command Palette > "Install 'cursor' command"
```

## 定价

| 计划 | 价格 | 说明 |
|------|------|------|
| Hobby | 免费 | 有限的 AI 请求 |
| Pro | $20/月 | 无限补全，500 次高级请求 |
| Business | $40/月 | 团队管理，隐私模式 |

## 使用场景

- **最适合**：需要 IDE 级体验的开发者、VS Code 用户
- **适合**：前端开发、全栈项目、团队协作
- **不太适合**：纯终端工作流、服务器端开发、CLI 自动化

## 与其他工具对比

| 特性 | Cursor | Claude Code | Aider |
|------|--------|-------------|-------|
| 界面 | IDE | CLI | CLI |
| 多模型 | ✓ | | ✓ |
| Background Agent | ✓ | | |
| Git 集成 | 基础 | 强大 | 最佳 |
| 开源 | | | ✓ |
| 终端原生 | | ✓ | ✓ |

## 资源链接

- [官方文档](https://docs.cursor.com/)
- [Changelog](https://www.cursor.com/changelog)
- [社区论坛](https://forum.cursor.com/)
