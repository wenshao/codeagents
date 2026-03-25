# 功能对比矩阵

本文档提供 Code Agent CLI 工具的详细横向对比。

## 快速参考表

| 功能 | Claude Code | Aider | Copilot CLI | SWE-agent | Cline | Goose | OpenCode | Continue | Warp | Gemini CLI | OpenHands | Cursor | Qwen Code | Kimi CLI |
|---------|------------|-------|-------------|-----------|-------|-------|----------|----------|------|------------|----------|--------|-----------|----------|
| **开源** | | ✓ | | ✓ | ✓ | ✓ | ✓ | ✓ | | ✓ | ✓ | | ✓ | ✓ |
| **免费层级** | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| **多模型** | | ✓ | | ✓ | | ✓ | ✓ | ✓ | ✓ | | ✓ | ✓ | ✓ | ✓ |
| **Git 集成** | ✓ | ✓ | ✓ | | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | | ✓ | ✓ | ✓ |
| **MCP 支持** | ✓ | | | | ✓ | ✓ | ✓ | | ✓ | ✓ | | ✓ | ✓ | ✓ |
| **IDE 集成** | ✓ | | | ✓ | ✓ | | ✓ | ✓ | | | | ✓ | ✓ | ✓ |
| **CLI 优先** | ✓ | ✓ | ✓ | ✓ | | ✓ | ✓ | | ✓ | ✓ | | | ✓ | ✓ |
| **终端原生** | ✓ | ✓ | ✓ | | | ✓ | ✓ | | | ✓ | | | ✓ | ✓ |

## 详细对比

### 模型支持

| 工具 | Claude | GPT-4 | Gemini | 本地模型 | 说明 |
|------|--------|-------|--------|----------|------|
| Claude Code | ✓ | | | | 仅 Claude |
| Aider | ✓ | ✓ | | ✓ | 通过 Ollama |
| Copilot CLI | ✓ | ✓ | | | Claude Sonnet 4.5 默认，可选 GPT-5 |
| Cursor | ✓ | ✓ | ✓ | | 多提供商 |
| SWE-agent | ✓ | ✓ | | ✓ | 灵活 |
| Cline | ✓ | | | | 仅 Claude |
| Goose | ✓ | ✓ | ✓ | | 多提供商 |
| OpenCode | ✓ | ✓ | ✓ | | 100+ 提供商（models.dev 动态加载） |
| Continue | ✓ | ✓ | | ✓ | 灵活 |
| Warp | ✓ | ✓ | | | 多个 |
| Gemini CLI | | | ✓ | | 仅 Gemini |
| OpenHands | ✓ | ✓ | ✓ | ✓ | 灵活 |
| Qwen Code | ✓ | ✓ | ✓ | | 5 提供商（Qwen/OpenAI/Anthropic/Gemini/自定义） |
| Kimi CLI | ✓ | ✓ | ✓ | | 6 种 provider type（Kimi/OpenAI Legacy/OpenAI Responses/Anthropic/Gemini/Vertex AI） |

### 架构与设计

| 工具 | 语言 | 架构 | 主要设计目标 |
|------|----------|--------------|-------------------|
| Claude Code | Rust | 原生 CLI | 代理式编程工具 |
| Aider | Python | Git 原生 | 结对编程 |
| Copilot CLI | Shell | 独立二进制 | 终端原生代理，GitHub 集成 |
| Cursor | TypeScript | IDE (VS Code) | AI 原生编辑器 |
| SWE-agent | Python | Agent-Computer Interface | 基准性能 |
| Cline | TypeScript | IDE 扩展 | 自主编码 |
| Goose | Rust | MCP 原生 | 模型灵活性 |
| OpenCode | TypeScript | 多代理（7 内置） | 多客户端 AI 平台（TUI + Web + 桌面） |
| Continue | TypeScript | IDE + CLI + CI/CD | PR Checks + 语义索引 |
| Warp | Rust | 终端替代品 | 现代终端 + AI |
| Gemini CLI | TypeScript | ReAct 循环 | Google 生态 |
| OpenHands | Python | 复合 AI | 完全自主 |
| Qwen Code | TypeScript | ReAct 循环（Gemini CLI 分叉） | 中文开发者生态 |
| Kimi CLI | Python | 多代理（4 内置）+ Wire 协议 | 双模式交互 + 多客户端（TUI + Web + IDE） |

### 核心功能对比

#### Git 集成

| 工具 | 自动提交 | 分支管理 | PR 创建 | 说明 |
|------|-------------|-------------------|-------------|-------|
| Claude Code | ✓ | ✓ | ✓ | 强大的 Git 支持 |
| Aider | ✓ | ✓ | | **同类最佳** |
| Copilot CLI | | ✓ | ✓ | GitHub 专注 |
| Cursor | | ✓ | | IDE 内置 |
| SWE-agent | | | | 问题专注 |
| Cline | ✓ | ✓ | | 良好支持 |
| Goose | | | | 基础 |
| OpenCode | | ✓ | | Git snapshot review + worktree 隔离 |
| Continue | | | ✓ | CI/CD 专注 |
| Warp | | ✓ | | 终端内置 |
| Gemini CLI | | | | 通过 bash 工具 |
| Qwen Code | | | | 通过 bash 工具 |
| Kimi CLI | | | | 通过 bash 工具 |

#### 上下文管理

| 工具 | 最大上下文 | 仓库映射 | 压缩 | 说明 |
|------|-------------|----------|------|-------|
| Claude Code | 100 万 token | | ✓ | 最大上下文 |
| Aider | 20 万 token | ✓ | | 优秀的映射 |
| Copilot CLI | ~12.8 万 token | | | 标准 |
| Cursor | ~20 万 token | | | 多模型 |
| SWE-agent | 可变 | ✓ | | 研究专注 |
| Cline | ~20 万 token | | ✓ | 良好上下文 |
| OpenCode | 可变 | | ✓ | 会话 auto-compact + 可配置 compaction hook |
| Gemini CLI | ~100 万 token | | | Gemini 原生 |
| OpenHands | 可变 | | | 全项目 |
| Qwen Code | ~100 万 token | | ✓ | 聊天压缩服务 |
| Kimi CLI | ~25.6 万 token | | ✓ | 自动压缩（85% 触发比例），可配置保留空间 |

#### 执行与安全

| 工具 | 沙箱 | 权限系统 | 试运行 | 说明 |
|------|---------|-------------|---------|-------|
| Claude Code | ✓ | ✓ | ✓ | 精细权限 |
| Aider | | ✓ | | 透明 |
| Copilot CLI | | ✓ | | 操作需确认，企业合规 |
| Cursor | | ✓ | | IDE 内权限 |
| SWE-agent | ✓ | | | Docker |
| Cline | ✓ | ✓ | | 基于权限 |
| OpenCode | | ✓ | | Tree-sitter AST 分析 + Doom Loop 保护 + 文件时间锁 + Worktree 隔离 |
| Gemini CLI | | ✓ | | 基于权限 |
| OpenHands | ✓ | | ✓ | Docker 隔离 |
| Qwen Code | ✓ | ✓ | | deny>ask>allow + Hook |
| Kimi CLI | | ✓ | | YOLO / 会话级审批 / 逐次确认 + feedback |

### 多模态能力

| 工具 | 图片输入 | 截图分析 | PDF | 说明 |
|------|----------|----------|-----|------|
| Claude Code | ✓ | ✓ | ✓ | 原生多模态（通过 Read 工具） |
| Aider | ✓ | | | 通过 --image 参数 |
| Copilot CLI | | | | 暂不支持 |
| Cursor | ✓ | ✓ | | 拖拽图片到 Chat |
| SWE-agent | | | | 不支持 |
| Cline | ✓ | ✓ | | 拖拽图片 |
| Goose | ✓ | | | 取决于模型 |
| OpenCode | | | | 不支持 |
| Continue | ✓ | | | 多模态模型支持 |
| Warp | | | | 不支持 |
| Gemini CLI | ✓ | ✓ | | Gemini 原生多模态 |
| OpenHands | ✓ | ✓ | | 浏览器截图 |
| Qwen Code | ✓ | | | 通义千问多模态 |
| Kimi CLI | | | | 暂不支持 |

### 平台支持

| 工具 | macOS | Linux | Windows | 说明 |
|------|-------|-------|---------|------|
| Claude Code | ✓ | ✓ | WSL | 原生 macOS/Linux |
| Aider | ✓ | ✓ | ✓ | Python 跨平台 |
| Copilot CLI | ✓ | ✓ | ✓ | 全平台原生 |
| Cursor | ✓ | ✓ | ✓ | Electron 跨平台 |
| SWE-agent | ✓ | ✓ | Docker | 需要 Docker |
| Cline | ✓ | ✓ | ✓ | VS Code 扩展 |
| Goose | ✓ | ✓ | WSL | Rust 原生 |
| OpenCode | ✓ | ✓ | ✓ | 多客户端跨平台 |
| Continue | ✓ | ✓ | ✓ | VS Code/JetBrains |
| Warp | ✓ | ✓ | 预览版 | 终端应用 |
| Gemini CLI | ✓ | ✓ | ✓ | Node.js 跨平台 |
| OpenHands | ✓ | ✓ | Docker | Docker 部署 |
| Qwen Code | ✓ | ✓ | ✓ | Node.js 跨平台 |
| Kimi CLI | ✓ | ✓ | WSL | Python 原生 |

### 断点恢复能力

| 工具 | 会话恢复 | 检查点 | 撤销/回退 | 说明 |
|------|----------|--------|-----------|------|
| Claude Code | ✓ | ✓ | ✓ | 会话恢复 + worktree |
| Aider | | | ✓ | Git undo (/undo) |
| Copilot CLI | | | | 基础会话 |
| Cursor | | | ✓ | IDE 撤销 |
| SWE-agent | | ✓ | | Docker 快照 |
| Cline | ✓ | ✓ | ✓ | Git Checkpoint |
| Goose | ✓ | | | 会话保存 |
| OpenCode | ✓ | ✓ | ✓ | Git snapshot + worktree |
| Continue | | | | VS Code 撤销 |
| Warp | | | | 无 |
| Gemini CLI | ✓ | ✓ | ✓ | 会话恢复 + rewind |
| OpenHands | ✓ | ✓ | | Docker 检查点 |
| Qwen Code | ✓ | ✓ | ✓ | 会话恢复（继承 Gemini CLI） |
| Kimi CLI | ✓ | | | 会话保存 |

### 成本参考（单次典型任务）

> 以下为估算值，实际成本取决于任务复杂度和 token 用量

| 工具 | 定价模式 | 简单任务 | 复杂任务 | 说明 |
|------|----------|----------|----------|------|
| Claude Code | API 按量 / 订阅 | ~$0.05-0.20 | ~$1-5 | Max 订阅 $100/月 或 API |
| Aider | API 按量 | ~$0.02-0.10 | ~$0.50-3 | 取决于所选模型 |
| Copilot CLI | 订阅制 | 1 premium request | 1 premium request | Copilot 订阅含配额 |
| Cursor | 订阅制 | 1 fast request | 多个 request | Pro $20/月 500 次 |
| Goose | API 按量 | ~$0.02-0.10 | ~$0.50-3 | 多提供商 |
| Gemini CLI | API 按量/免费 | 免费 | ~$0.10-1 | 有免费层级 |
| OpenHands | API 按量 | ~$0.05-0.20 | ~$2-10 | 多代理消耗更高 |
| Qwen Code | 免费/API | 免费 | 免费 | 每日 1000 次 |
| Kimi CLI | API 按量 | ~$0.01-0.05 | ~$0.20-1 | 国内模型成本低 |

### 内置命令能力对比

> 对比各工具的交互式斜杠命令/内置命令体系。Cline（VS Code 扩展）和 Warp（终端应用）使用 GUI 交互而非斜杠命令。

| 能力 | Claude Code | Aider | Gemini CLI | Kimi CLI | Qwen Code | Copilot CLI | Codex CLI | Goose | OpenCode |
|------|-------------|-------|-----------|----------|-----------|-------------|-----------|-------|---------|
| **命令总数** | ~60（含 Skill） | ~42 | ~41 | ~20 | ~23 | ~32 | ~20 | CLI 子命令 | Ctrl+P 面板 |
| **代码审查** | `/review` 插件 | — | `/code-review`（扩展） | — | — | `/review` | `@codex review` | — | — |
| **模式切换** | — | `/code` `/architect` `/ask` | `/plan` | `/plan` `/yolo` | `/plan` | — | `--approval-mode` | — | `--agent` |
| **模型切换** | `/model` | `/model` `/editor-model` `/weak-model` | `/model` | `/model` | `/model` | `/model` | `--model` | `--model` | — |
| **上下文压缩** | `/compact` | `/clear` `/reset` | `/compress` | `/compact` | `/compact` | — | — | — | — |
| **文件管理** | 自动 | `/add` `/drop` `/read-only` `/ls` | 自动 | `/add-dir` | 自动 | 自动 | 自动 | 自动 | 自动 |
| **Git 操作** | 内置工具 | `/commit` `/undo` `/diff` `/git` | 内置工具 | — | 内置工具 | 内置 GitHub MCP | — | — | 内置工具 |
| **仓库地图** | — | `/map` `/map-refresh` | — | — | — | — | — | — | — |
| **MCP 状态** | `/mcp` | — | `/mcp` | `/mcp` | `/mcp` | — | — | — | `mcp list` |
| **权限管理** | `/permissions` | — | `/permissions` `/policies` | — | `/permissions` | — | — | — | — |
| **记忆系统** | `/memory` | — | `/memory` | — | `/memory` | — | — | — | — |
| **会话恢复** | `--resume` | — | `/restore` `/resume` `/rewind` | `/sessions` `/resume` | `/restore` `/resume` `/rewind` | — | — | — | `session list` |
| **语音输入** | 内置 Voice | `/voice` | — | — | — | — | — | — | — |
| **远程控制** | `/remote-control` | — | — | — | — | — | — | — | — |
| **Web 抓取** | WebFetch 工具 | `/web` | — | `/web` | — | — | — | — | — |
| **LSP 集成** | — | — | — | — | — | `/lsp` | — | — | — |
| **费用查看** | `/cost` | `/tokens` | `/stats` | — | `/stats` | — | — | — | `stats` |
| **反馈报告** | `/bug` | `/report` | `/bug` | `/feedback` | `/bug` | `/feedback` | — | — | — |
| **Vim 模式** | `/vim` | — | `/vim` | — | — | — | — | — | — |

**关键发现：**
- **Aider** 命令最多（~42），文件/上下文管理和模式切换最细粒度
- **Gemini CLI / Qwen Code / Kimi CLI** 命令体系接近（Gemini CLI 分叉谱系）
- **Claude Code** 独有 `/review`（代码审查）和 `/remote-control`（远程控制）
- **Copilot CLI** 命令最少（5 个），侧重简洁
- **Codex CLI** 无斜杠命令，完全通过 CLI 参数控制
- **OpenCode** 使用 Ctrl+P 命令面板而非斜杠命令

## 使用场景推荐

### 最适合复杂重构
1. **Claude Code** - 卓越的推理、大上下文
2. **SWE-agent** - 基准验证
3. **Aider** - Git 纪律

### 最适合快速编辑
1. **Copilot CLI** - 终端原生代理
2. **Gemini CLI** - 轻量级
3. **Aider** - 专注编辑

### 最适合 Git 工作流
1. **Aider** - Git 原生设计
2. **Claude Code** - 强大的 Git 集成
3. **Copilot CLI** - GitHub 生态

### 最适合学习
1. **mini-swe-agent** - 100 行参考
2. **SWE-agent** - 学术方法
3. **Aider** - 透明操作

### 最适合隐私
1. **TabbyML** - 自托管
2. **OpenHands** - Docker 隔离
3. **Aider** - 本地模型支持

### 最适合团队
1. **Claude Code** - 企业功能
2. **Copilot CLI** - GitHub 集成
3. **Continue** - CI/CD 集成

### 最适合中文开发者
1. **Qwen Code** - 每日 1000 次免费，阿里云生态
2. **Kimi CLI** - 双模式交互，Ctrl-X 快捷键，多提供商
3. **Claude Code** - 中文理解能力强

## 性能总结

| 工具 | SWE-bench | 速度 | 复杂性 | 说明 |
|------|-----------|-------|------------|-------|
| Claude Code | ~60% | 中等 | 高 | 最佳推理 |
| Cursor | N/A | 快 | 中等 | IDE 集成 |
| Aider | ~45% | 快 | 低 | 良好平衡 |
| Copilot CLI | N/A | 快 | 中等 | 终端代理 |
| SWE-agent | 74% | 慢 | 高 | 基准之王 |
| Cline | ~40% | 中等 | 中等 | IDE 原生 |
| OpenHands | ~55% | 慢 | 很高 | 完全自主 |
| Qwen Code | N/A | 快 | 低 | 免费额度高 |
| Kimi CLI | N/A | 中等 | 中等 | 双模式 + 子代理 + 插件 |
