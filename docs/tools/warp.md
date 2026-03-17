# Warp

**开发者：** Warp Dot Dev
**许可证：** 专有（提供免费层级）
**仓库：** [github.com/warpdotdev/Warp](https://github.com/warpdotdev/Warp)
**网站：** [warp.dev](https://www.warp.dev/)
**Stars：** 约 30k+

## 概述

Warp 是一个为 AI 代理编码而构建的现代终端。它不仅仅是一个 CLI 工具——它是一个完整的终端替代品，内置了 AI 功能。

## 核心功能

### 基础能力
- **现代终端**：GPU 加速、基于块的输出
- **Warp Agents 3.0**：并行运行多个 AI 代理
- **Agent 模式**：AI 跟随你的终端会话
- **代码审查**：AI 驱动的代码审查集成
- **命令搜索**：自然语言搜索命令

### 独特功能
- **终端原生 AI**：AI 是终端的一部分，不是附加组件
- **块**：更好的可读性结构化输出
- **并行代理**：独特的多代理能力
- **保存的提示**：可重用的代理配置文件
- **MCP 支持**：模型上下文协议服务器

## 安装

```bash
# macOS
brew install --cask warp

# Linux
# 从 warp.dev 下载

# 或将 Warp CLI 与任何终端一起使用
npm install -g @warpdev/cli
```

## 架构

- **语言：** Rust
- **平台**：macOS（主要）、Linux（测试版）
- **模型**：支持多个提供商

## 优势

1. **现代 UX**：最好的终端体验
2. **集成 AI**：AI 是原生的，不是附加的
3. **并行代理**：独特的多代理能力
4. **性能**：GPU 加速渲染
5. **活跃开发**：定期更新和改进

## 劣势

1. **macOS 专注**：Linux 支持是测试版，无 Windows
2. **专有**：非开源
3. **终端替代品**：需要更改终端
4. **资源占用**：比标准终端占用更多系统资源

## CLI 命令

```bash
# Warp CLI（适用于任何终端）
warp ai "解释这个命令"
warp agent "部署到生产环境"

# 在 Warp 终端中
# 按 Ctrl-Space 调用 AI
# 使用 Cmd-P 调用保存的提示
```

## Warp AI 功能

- **命令解释**：`Cmd-Shift-R` 解释
- **Agent 模式**：让 AI 执行命令
- **自然语言搜索**：通过描述命令来查找
- **代码审查**：集成 PR 审查

## 集成

- **Claude Code 集成**：[warpdotdev/claude-code-warp](https://github.com/warpdotdev/claude-code-warp)
- **MCP 服务器**：通过模型上下文协议扩展

## 使用场景

- **最适合**：想要现代终端 + AI 的 macOS 用户
- **适合**：想要一致终端体验的团队
- **不太适合**：Windows 用户、最小终端用户

## 资源链接

- [网站](https://www.warp.dev/)
- [GitHub](https://github.com/warpdotdev/Warp)
- [文档](https://docs.warp.dev/)
