# OpenCode

**开发者：** OpenCode AI (SST)
**许可证：** MIT
**仓库：** [github.com/opencode-ai/opencode](https://github.com/opencode-ai/opencode)
**网站：** [opencode.ai](https://opencode.ai/)
**Stars：** 约 3k+

## 概述

OpenCode 是一个功能丰富的终端 AI 编程助手。尽管最初以 Go 项目知名，当前版本已重写为 TypeScript monorepo 架构，提供 TUI、Web 控制台和桌面应用三种客户端。其核心特色是多代理系统、插件架构和对 20+ LLM 提供商的统一支持。

## 核心功能

### 基础能力
- **多客户端**：TUI（终端）、Web 控制台、Tauri 桌面应用
- **多代理系统**：build、plan、general、explore 等专用代理
- **40+ 内置工具**：文件编辑、Bash 执行、Grep 搜索、Web 抓取等
- **20+ LLM 提供商**：Anthropic、OpenAI、Google、Amazon Bedrock、Mistral 等
- **MCP 支持**：完整的模型上下文协议集成（HTTP/SSE/Stdio/WebSocket）
- **LSP 集成**：语言服务器协议，支持 Python、TypeScript 等
- **SQLite 持久化**：Drizzle ORM，会话/消息完整存储

### 独特功能
- **插件系统**：基于 Hook 的可扩展架构，支持 npm 包和文件插件
- **Tree-sitter Bash 分析**：AST 解析 bash 命令，智能权限判断
- **Doom Loop 保护**：检测连续 3 次权限拒绝，自动中断无限循环
- **文件时间锁**：检测编辑期间文件被外部修改，防止冲突
- **会话压缩**：长对话自动压缩，保留关键上下文
- **Git Worktree 隔离**：每个会话可使用独立 worktree

## 技术架构（源码分析）

### Monorepo 结构

```
opencode/
├── packages/opencode/    # 核心 CLI/TUI 应用 + 代理后端
├── packages/console/     # Web 控制台（SolidJS Start）
├── packages/sdk/js/      # JavaScript SDK
├── packages/ui/          # 共享 UI 组件库
├── packages/plugin/      # 插件系统
├── packages/desktop/     # Tauri 桌面应用
└── packages/script/      # 构建和工具脚本
```

### 核心架构

```
客户端 (TUI/Web/Desktop)
    ↓
Hono HTTP 服务器 (localhost:4096) + WebSocket
    ↓
代理系统 (Agent Layer)
    ↓
Vercel AI SDK → LLM 提供商
    ↓
工具系统 → 文件系统/Shell
    ↓
SQLite (Drizzle ORM)
```

### 技术栈
- **语言**：TypeScript 5.8
- **运行时**：Bun 1.3（主要）/ Node.js 22（兼容）
- **TUI 框架**：OpenTUI + Solid.js（响应式信号驱动）
- **HTTP 框架**：Hono（轻量级，Cloudflare Workers 兼容）
- **数据库**：SQLite + Drizzle ORM（WAL 模式）
- **AI SDK**：Vercel AI SDK v5（统一 LLM 接口）
- **MCP SDK**：@modelcontextprotocol/sdk v1.25

### 多代理系统

| 代理 | 类型 | 权限 | 用途 |
|------|------|------|------|
| **build** | 主代理 | 完全访问 | 代码开发、文件编辑 |
| **plan** | 主代理 | 只读 | 代码分析、规划 |
| **general** | 子代理 | 受限 | 复杂多步骤研究 |
| **explore** | 子代理 | 只读 | 快速代码库搜索 |
| **compaction** | 隐藏 | 内部 | 会话压缩 |
| **title/summary** | 隐藏 | 内部 | 自动标题/摘要 |

### 权限系统

```
规则优先级：远程 → 全局 → 项目 → .opencode → 内联
权限类型：edit, write, read, bash, question, external_directory
操作：allow / deny / ask
```

- 基于 Tree-sitter 的 bash 命令解析，自动提取目录和操作
- `.env*` 文件默认需要确认
- 外部目录默认需要确认

## 安装

```bash
# npm
npm install -g opencode-ai

# Homebrew
brew install opencode

# Scoop (Windows)
scoop install opencode

# Arch Linux
pacman -S opencode

# 或使用安装脚本
curl -fsSL https://opencode.ai/install.sh | sh
```

## 支持的模型

| 提供商 | 模型示例 | 说明 |
|--------|---------|------|
| Anthropic | Claude 4.5 Sonnet, Opus | 专有 beta 头支持 |
| OpenAI | GPT-4, GPT-5, o1 | 完整支持 |
| Google | Gemini, Vertex AI | 双通道 |
| Amazon | Bedrock | 企业级 |
| Mistral, Groq, Cohere | 各类模型 | 通过统一接口 |
| GitHub Copilot, GitLab | 集成模型 | 插件认证 |
| 自定义 | OpenAI 兼容端点 | 本地部署 |

## 优势

1. **真正的多提供商**：20+ LLM 提供商通过 Vercel AI SDK 统一接入
2. **多客户端架构**：TUI + Web + 桌面，共享同一后端
3. **插件生态**：Hook 系统 + npm 插件 + MCP 服务器
4. **智能权限**：Tree-sitter bash 分析，精准权限控制
5. **TypeScript 全栈**：类型安全，Zod 验证贯穿全栈
6. **开源 MIT**：企业友好许可

## 劣势

1. **较新项目**：社区和文档不如成熟工具
2. **架构复杂**：Monorepo + 多客户端，学习曲线较陡
3. **Bun 依赖**：主要运行时非 Node.js 主流
4. **桌面/Web 不成熟**：TUI 之外的客户端还在早期

## CLI 命令

```bash
# 启动 TUI
opencode

# 非交互模式执行
opencode run "重构这个函数"

# 仅启动 HTTP 服务器
opencode serve

# 管理认证
opencode auth login anthropic

# 列出可用模型
opencode models

# 管理 MCP 服务器
opencode mcp list

# 导出/导入会话
opencode export --session <id>
```

## 配置

```jsonc
// opencode.json 或 .opencode/opencode.json
{
  "agent": {
    "build": {
      "model": { "provider": "anthropic", "id": "claude-sonnet-4" }
    }
  },
  "provider": {
    "anthropic": { "apiKey": "${ANTHROPIC_API_KEY}" }
  },
  "plugin": ["opencode-plugin-example"],
  "permission": {
    "allow": [{ "tool": "read", "path": "**" }],
    "deny": [{ "tool": "bash", "command": "rm -rf /" }]
  }
}
```

## 使用场景

- **最适合**：需要多 LLM 提供商切换、插件扩展的开发者
- **适合**：终端原生工作流、多客户端需求
- **不太适合**：追求简单开箱即用、IDE 重度用户

## 资源链接

- [网站](https://opencode.ai/)
- [GitHub](https://github.com/opencode-ai/opencode)
- [freeCodeCamp 指南](https://www.freecodecamp.org/news/integrate-ai-into-your-terminal-using-opencode/)
