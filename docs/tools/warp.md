# Warp

**开发者：** Warp
**许可证：** 专有（提供免费层级）
**仓库：** [github.com/warpdotdev/Warp](https://github.com/warpdotdev/Warp)（Issue tracker）
**网站：** [warp.dev](https://www.warp.dev/)
**Stars：** 约 30k+

## 概述

Warp 是一个用 Rust 构建的现代终端应用，内置 AI 代理能力。与其他工具不同，Warp 不是 CLI 工具，而是**终端替代品**——用 Warp 替换你的 Terminal.app / iTerm2。AI 是终端的原生部分，不是附加组件。

## 核心功能

### 基础能力
- **GPU 加速终端**：Rust + Metal/Vulkan 渲染
- **块式输出**：命令输出按块组织，可复制/分享
- **Warp Agents**：AI 代理直接在终端中运行
- **命令搜索**：自然语言搜索和补全
- **MCP 支持**：模型上下文协议扩展

### 独特功能
- **终端原生 AI**：AI 集成在终端渲染层，不是外部进程
- **并行代理**：多个 AI 代理同时工作
- **保存的提示**：可重用代理配置
- **Warp Drive**：团队共享命令和工作流

## 安装

```bash
# macOS
brew install --cask warp

# Linux
# 从 warp.dev/linux 下载

# Windows
# 目前不支持
```

## 架构

- **语言**：Rust
- **平台**：macOS（主要）、Linux
- **模型**：支持多个提供商

## 优势

1. **终端体验最佳**：GPU 加速，现代 UI
2. **AI 原生**：不是附加的，是内置的
3. **块式输出**：命令输出结构化
4. **Rust 性能**：快速渲染

## 劣势

1. **平台限制**：无 Windows 原生支持
2. **闭源**：非开源（仓库仅是 Issue tracker）
3. **需要替换终端**：不能作为现有终端的插件
4. **资源占用**：比传统终端更重

## 使用场景

- **最适合**：想要现代终端 + AI 的 macOS/Linux 用户
- **适合**：团队共享工作流（Warp Drive）
- **不太适合**：Windows 用户、极简终端用户、SSH 服务器

## 资源链接

- [网站](https://www.warp.dev/)
- [GitHub](https://github.com/warpdotdev/Warp)
- [文档](https://docs.warp.dev/)
