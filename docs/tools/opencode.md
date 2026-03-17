# OpenCode

**开发者：** OpenCode AI
**许可证：** MIT
**仓库：** [github.com/opencode-ai/opencode](https://github.com/opencode-ai/opencode)
**网站：** [opencode.ai](https://opencode.ai/)
**Stars：** 约 3k+

## 概述

OpenCode 是一个强大的基于终端的 AI 助手，专为开发者设计。它使用 Go 构建，直接在终端中提供智能编码帮助。

## 核心功能

### 基础能力
- **终端原生**：专为 CLI 使用设计
- **LSP 支持**：自动加载语言服务器以理解代码
- **多模型**：支持 Claude、GPT、Gemini
- **双代理**：
  - **build**：完全访问的代理用于代码更改
  - **plan**：只读代理用于规划
- **Tab 切换**：轻松在代理之间切换

### 独特功能
- **Go 构建**：快速、单二进制分发
- **双代理模式**：规划和执行分离
- **本地优先**：强调在本地机器上运行
- **跨平台**：macOS、Windows、Linux 支持

## 安装

```bash
# 从网站下载
# https://opencode.ai/download

# 或使用 Homebrew（macOS/Linux）
brew install opencode

# 或使用 cargo（如果 Rust 生态系统中可用）
# 查看网站获取最新说明
```

## 架构

- **语言：** Go
- **支持的模型：**
  - Claude (Sonnet, Opus)
  - GPT-4
  - Gemini

## 优势

1. **Go 性能**：快速、单一二进制
2. **双代理**：智能的规划和执行分离
3. **LSP 集成**：正确的代码理解
4. **开源**：MIT 许可
5. **终端优先**：为 CLI 工作流设计

## 劣势

1. **较小项目**：不如主要工具成熟
2. **文档有限**：不如 Aider/Claude Code 全面
3. **新社区**：用户群较小

## CLI 命令

```bash
# 启动 OpenCode
opencode

# 使用 build 代理（完全访问）
opencode agent build

# 使用 plan 代理（只读）
opencode agent plan

# 使用 Tab 切换代理
# （在交互式会话期间）
```

## 使用场景

- **最适合**：Go 用户、终端原生开发者
- **适合**：执行前规划、只读分析
- **不太适合**：IDE 重度工作流

## 替代品/Fork

- [anomalyco/opencode](https://github.com/anomalyco/opencode) - 替代实现

## 资源链接

- [网站](https://opencode.ai/)
- [GitHub](https://github.com/opencode-ai/opencode)
- [freeCodeCamp 指南](https://www.freecodecamp.org/news/integrate-ai-into-your-terminal-using-opencode/)
