# Warp

**开发者：** Warp
**许可证：** 专有（提供免费层级 + Build/Business 付费计划）
**仓库：** [github.com/warpdotdev/Warp](https://github.com/warpdotdev/Warp)（Issue tracker，非源码）
**网站：** [warp.dev](https://www.warp.dev/)
**Stars：** 约 26k+
**最后更新：** 2026-03

## 概述

Warp 是一个用 Rust 从零构建的现代**代理开发环境（Agentic Development Environment）**。自 Warp 2.0 起，Warp 不再仅仅是一个终端替代品，而是统一了现代终端、多模型 AI 代理、原生代码编辑器和团队协作平台的四合一产品。与 Claude Code、Codex CLI 等工具不同，Warp **不是一个 CLI 工具**，而是一个完整的开发环境——包含 Code、Agents、Terminal 和 Drive 四大模块。

Warp 使用 Rust 编写核心逻辑，搭配 Metal（macOS）和 Vulkan（Linux/Windows）进行 GPU 加速渲染，提供远超传统终端的性能和视觉体验。它重新设计了终端的交互方式：现代文本编辑器式的输入框、结构化的命令输出块、内置的多 AI 代理管理，以及团队协作功能。支持同时运行 Warp 原生 Oz 代理、Claude Code、Codex、Gemini CLI 等多个代理。

## Warp Agent

Warp Agent（内部代号 Oz）是内置于终端的 AI 代理系统，拥有完整的终端控制能力（Full Terminal Use）和 Computer Use 能力，可以验证更改效果。

### 核心能力

- **自然语言转命令**：输入自然语言描述，Agent 自动生成对应的 shell 命令
- **多步任务执行**：Agent 可以规划并执行包含多个步骤的复杂任务，自动处理中间结果
- **Full Terminal Use**：Oz 代理可运行交互式终端命令，不仅限于简单 shell 命令
- **Computer Use**：代理可以验证更改效果，进行可视化检查
- **上下文感知**：Agent 能感知当前目录、shell 环境、历史命令和输出，提供上下文相关的建议
- **代码库搜索**：支持符号、变量、函数名的精确搜索
- **错误修复**：当命令执行失败时，Agent 可以分析错误输出并建议修复方案
- **文件操作**：Agent 可以读取、创建和编辑文件（支持 10,000+ 行大文件），执行代码审查和重构任务
- **会话恢复**：支持继续之前的 Agent 对话

### 使用方式

```bash
# 在 Warp 终端中按 Ctrl+Shift+Space 或点击 Agent 按钮
# 然后输入自然语言指令：

> 找到当前项目中所有超过 100 行的 Python 文件
> 将 main.go 中的所有 fmt.Println 替换为 log.Info
> 创建一个 Dockerfile 来构建这个 Node.js 项目
> 分析最近 10 次 git commit 的变更统计
```

### Agent 模式

| 模式 | 说明 | 适用场景 |
|------|------|----------|
| 自动执行 | Agent 自动运行命令，无需确认 | 信任度高的重复任务 |
| 确认执行 | 每步命令需要用户确认 | 敏感操作、生产环境 |
| 建议模式 | 仅生成命令建议，不执行 | 学习和探索 |

## MCP 支持

Warp 支持 Model Context Protocol（MCP），允许通过外部工具服务器扩展 Agent 的能力。

### 配置 MCP 服务器

在 Warp 设置中或通过配置文件添加 MCP 服务器：

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
        "GITHUB_TOKEN": "ghp_xxxxxxxxxxxx"
      }
    }
  }
}
```

### 支持的 MCP 能力

- **Tools**：调用外部工具执行操作（如文件系统操作、API 调用）
- **Resources**：访问外部数据源（如数据库、文档）
- **Prompts**：使用预定义的提示模板

## 块式输出（Blocks）

Warp 的标志性功能之一是**块式输出**——每次命令执行的输入和输出被组织为一个独立的"块"。

### 工作原理

1. 每条命令及其输出自动归为一个 Block
2. Block 包含：命令文本、退出码、执行时间、完整输出
3. Block 之间有清晰的视觉分隔

### Block 操作

| 操作 | 快捷键 / 方式 | 说明 |
|------|---------------|------|
| 复制输出 | 点击 Block 右上角复制图标 | 复制该 Block 的完整输出 |
| 分享 Block | Block 菜单 → Share | 生成可分享的链接 |
| 书签 Block | Block 菜单 → Bookmark | 保存重要输出 |
| 向上导航 | `Ctrl+Shift+↑` | 跳转到上一个 Block |
| 向下导航 | `Ctrl+Shift+↓` | 跳转到下一个 Block |
| 搜索 Block | `Cmd+F` / `Ctrl+F` | 在当前 Block 中搜索 |

## Warp Drive

Warp Drive 是知识存储和团队协作平台，可在团队成员和 AI 代理之间共享和复用资源。在 Warp 2.0 中，Warp Drive 还承担了集中配置 MCP 和规则的角色，使代理能够按照团队的约定和规范执行任务。

### 共享内容

- **命令（Commands）**：保存常用命令片段，支持参数化模板
- **工作流（Workflows）**：参数化命令序列，可嵌入 Notebook，支持跨文档同步更新
- **笔记本（Notebooks）**：类似 Runbook 的交互式文档，可嵌入可执行命令和 Workflows，支持 Markdown 导出
- **环境变量（Environment Variables）**：团队共享的环境配置
- **提示（Prompts）**：共享 Agent 提示模板和角色配置
- **MCP 配置**：集中配置和共享 MCP 服务器
- **规则（Rules）**：团队编码规范和代理行为规则

### 使用示例

```bash
# 创建参数化命令模板
# 名称: deploy-service
# 命令: kubectl rollout restart deployment/{{service_name}} -n {{namespace}}
# 参数: service_name (必填), namespace (默认: production)

# 工作流示例：发布检查
# Step 1: git status
# Step 2: npm test
# Step 3: npm run build
# Step 4: git tag v{{version}}
# Step 5: git push --tags
```

## 并行代理（Multi-Agent）

Warp 2.0 的核心特色之一是多代理管理——可同时运行和监控多个 AI Agent。

- **多代理类型**：支持 Warp 原生 Oz 代理、Claude Code、Codex、Gemini CLI 等
- **Agent 管理 UI**：统一界面查看所有运行中代理的状态
- **桌面通知**：代理完成任务或需要帮助时发送通知
- **并发任务**：同时执行代码审查、测试运行、环境搭建等不同任务
- **独立上下文**：每个 Agent 维护自己的上下文，互不干扰
- **自主性控制**：可设置每个代理的自主执行程度

## 保存的提示（Saved Prompts）

保存的提示允许用户创建可重复使用的 Agent 配置，类似于自定义 AI 角色。

```yaml
# 示例：代码审查专家
name: "Code Reviewer"
description: "专注于代码质量和安全性的审查代理"
system_prompt: |
  你是一个严格的代码审查专家。
  重点关注：安全漏洞、性能问题、代码风格一致性。
  对每个发现给出严重程度评级和修复建议。
```

- 支持在团队中通过 Warp Drive 共享 Saved Prompts
- 可以为不同任务场景（调试、重构、文档编写）创建专用提示
- 支持设置默认模型和参数

## Warpify

Warpify 是 Warp 的子 shell 功能，允许在 SSH 远程会话中获得 Warp 的现代终端体验。

### 工作原理

```bash
# SSH 连接到远程服务器后，运行：
warpify

# 这会在远程服务器上启动一个 Warp 子 shell
# 从而在远程会话中也能使用：
# - 块式输出
# - AI Agent
# - 命令搜索和补全
```

### 注意事项

- 需要远程服务器允许安装轻量级组件
- 不改变远程服务器的默认 shell
- 会话结束后自动清理

## 安装

### macOS

```bash
# 通过 Homebrew（推荐）
brew install --cask warp

# 通过官网下载 .dmg
# 访问 https://www.warp.dev/download 下载 macOS 安装包
# 拖拽 Warp.app 到 Applications 文件夹
```

### Linux

```bash
# Debian/Ubuntu (.deb)
sudo apt install ./warp-terminal_*.deb

# Fedora/RHEL (.rpm)
sudo rpm -i warp-terminal-*.rpm

# AppImage（通用）
chmod +x Warp-*.AppImage
./Warp-*.AppImage

# 从官网下载
# 访问 https://www.warp.dev/linux 选择对应发行版
```

### Windows

```powershell
# Windows 版本已正式发布（GA）
# 通过官网下载：https://www.warp.dev/download
# 或使用 winget：
winget install Warp.Warp
```

## 模型支持

Warp Agent 支持多个 AI 模型提供商：

| 模型 | 提供商 | 说明 |
|------|--------|------|
| Claude Sonnet 4 / Claude 4 | Anthropic | 默认推荐，代码能力强 |
| GPT-4o | OpenAI | 通用能力优秀 |
| GPT-4o mini | OpenAI | 轻量快速，适合简单任务 |
| Gemini 2.0 Flash | Google | 快速响应 |
| Gemini 2.5 Pro | Google | 长上下文支持 |
| 自定义模型 | 通过 BYOK API Key | 支持配置自定义模型端点 |

- 免费层级使用 Warp 提供的模型额度（有限）
- Build/Business 用户可通过 BYOK（Bring Your Own Key）配置 OpenAI、Anthropic、Google API Key
- 在设置 → AI → Model 中切换默认模型

## 定价

| 计划 | 价格 | 主要功能 |
|------|------|----------|
| **Free** | $0/月 | 终端功能免费，有限 AI 额度 |
| **Build**（个人） | $20/月 | 1,500 AI credits，BYOK（OpenAI/Anthropic/Google），Reload Credits 附加包 |
| **Business**（团队） | $50/用户/月 | 1,500 credits/用户，共享 Reload Credits，Warp Drive 团队协作，SSO |
| **Enterprise** | 自定义定价 | 私有部署选项，高级安全合规，专属支持，自定义集成 |

注：2025 年 10 月后，原 Pro/Turbo/Lightspeed 计划已统一为 Build 计划。Reload Credits 为预付费附加包，可跨月滚存 12 个月。

## 快捷键

### 终端操作

| 快捷键 | 功能 |
|--------|------|
| `Cmd+T` / `Ctrl+Shift+T` | 新建标签页 |
| `Cmd+N` / `Ctrl+Shift+N` | 新建窗口 |
| `Cmd+D` | 水平分屏 |
| `Cmd+Shift+D` | 垂直分屏 |
| `Cmd+W` / `Ctrl+Shift+W` | 关闭当前面板 |
| `Cmd+K` / `Ctrl+L` | 清屏 |

### AI 与搜索

| 快捷键 | 功能 |
|--------|------|
| `Ctrl+Shift+Space` | 打开 AI Agent |
| `Cmd+P` / `Ctrl+P` | 命令面板 |
| `Ctrl+R` | 搜索历史命令 |
| `Ctrl+Shift+R` | 搜索 Warp Drive 工作流 |
| `#` | 在输入框中输入 # 触发自然语言模式 |

### Block 导航

| 快捷键 | 功能 |
|--------|------|
| `Ctrl+Shift+↑` | 上一个 Block |
| `Ctrl+Shift+↓` | 下一个 Block |
| `Cmd+Shift+C` | 复制 Block 输出 |
| `Cmd+F` / `Ctrl+F` | Block 内搜索 |

## 配置

### 主题与外观

Warp 支持自定义主题，可在设置 → Appearance 中配置：

```yaml
# ~/.warp/themes/custom_theme.yaml
name: "My Custom Theme"
accent: "#FF6B6B"
background: "#1E1E2E"
foreground: "#CDD6F4"
cursor: "#F5E0DC"
terminal_colors:
  normal:
    black: "#45475A"
    red: "#F38BA8"
    green: "#A6E3A1"
    yellow: "#F9E2AF"
    blue: "#89B4FA"
    magenta: "#F5C2E7"
    cyan: "#94E2D5"
    white: "#BAC2DE"
```

### AI 提供商设置

```
设置 → AI → Provider：选择模型提供商
设置 → AI → API Key：配置自定义 API Key
设置 → AI → Default Model：设置默认模型
设置 → AI → Agent Execution Mode：自动/确认/建议
```

### 字体与编辑器

```
设置 → Appearance → Font：选择等宽字体
设置 → Appearance → Font Size：字号（默认 13）
设置 → Editor → Vi Mode：启用 Vi 键绑定
设置 → Editor → Tab Size：缩进宽度
```

## 与传统终端和 AI CLI 工具的对比

| 特性 | Warp | iTerm2 / GNOME Terminal | Claude Code | GitHub Copilot CLI |
|------|------|-------------------------|-------------|-------------------|
| **类型** | 终端应用 | 终端应用 | CLI 工具 | CLI 插件 |
| **AI 集成** | 原生内置 | 无 | 核心功能 | 命令建议 |
| **GPU 加速** | 是（Metal/Vulkan） | 否 | 不适用 | 不适用 |
| **块式输出** | 是 | 否 | 否 | 否 |
| **团队协作** | Warp Drive | 否 | 否 | 否 |
| **MCP 支持** | 是 | 否 | 是 | 否 |
| **多代理并行** | 是 | 不适用 | 否 | 否 |
| **开源** | 否 | 是（iTerm2） | 否 | 否 |
| **平台** | macOS, Linux, Windows | 平台特定 | 跨平台 | 跨平台 |
| **价格** | 免费 + 付费计划 | 免费 | 付费 | 付费 |
| **适用场景** | 日常终端 + AI 辅助 | 日常终端 | 编码代理 | 命令补全 |

### 选择建议

- **选 Warp**：如果你想要一个现代化的终端体验，AI 是锦上添花，且团队需要共享工作流
- **选传统终端**：如果你偏好轻量、开源、高度可定制的终端环境
- **选 Claude Code**：如果你需要深度代码编辑和项目级别的 AI 代理能力
- **选 GitHub Copilot CLI**：如果你只需要快速的命令建议和解释

## 优势

1. **终端体验最佳**：GPU 加速渲染，现代化 UI，媲美代码编辑器的输入体验
2. **AI 原生集成**：不是附加的外部工具，而是终端的内置能力
3. **块式输出结构化**：命令输出清晰组织，易于复制、分享和回溯
4. **Rust 高性能**：启动快、渲染快、资源占用合理
5. **团队协作**：Warp Drive 提供独特的终端级别团队协作能力

## 劣势

1. **闭源**：核心代码不开源（GitHub 仓库仅是 Issue tracker）
2. **需要替换终端**：不能作为现有终端的插件使用，需要切换到 Warp 作为默认终端
3. **新平台适配中**：Windows 版本已 GA，但部分高级功能仍在完善中
4. **依赖云服务**：AI 功能需要网络连接和 Warp 账户
5. **资源占用**：比传统终端（如 alacritty）更重，Electron 级别的内存占用

## 使用场景

- **最适合**：想要现代终端 + AI 辅助的 macOS/Linux 开发者
- **适合**：需要团队共享命令和工作流的开发团队（Warp Drive）
- **适合**：经常需要在终端中执行复杂多步任务的运维工程师
- **不太适合**：极简终端用户、离线环境、需要完全开源的团队

## 资源链接

- [官方网站](https://www.warp.dev/)
- [GitHub Issues](https://github.com/warpdotdev/Warp)
- [官方文档](https://docs.warp.dev/)
- [Warp 博客](https://www.warp.dev/blog)
- [主题市场](https://github.com/warpdotdev/themes)
- [工作流仓库](https://github.com/warpdotdev/workflows)
