# Cline

**开发者：** Cline
**许可证：** Apache-2.0
**仓库：** [github.com/cline/cline](https://github.com/cline/cline)
**Stars：** 约 60k
**最后更新：** 2026-03

## 概述

Cline 是最受欢迎的 AI 编程 VS Code 扩展（5M+ 开发者），同时提供独立 CLI。基于 TypeScript 构建，核心 Task 循环实现了完整的代理工作流。支持 43+ LLM 提供商，内置 Git Checkpoint 系统实现操作回滚，通过 MCP、Hook 系统和原生 Subagent 提供强大的扩展能力。

## 核心功能

### 基础能力
- **VS Code 深度集成**：WebView UI + 编辑器 API
- **24+ 种内置工具**：文件读写、Bash 执行、浏览器操作、MCP 工具、Subagent 等
- **43+ LLM 提供商**：Anthropic、OpenAI、Google、AWS、Azure、DeepSeek、xAI 等
- **Plan/Act 双模式**：规划阶段探索，执行阶段修改
- **Checkpoint 系统**：基于 Git 的操作回滚
- **MCP 支持**：外部 MCP 服务器集成（McpHub + OAuth 支持）
- **独立 CLI**：可脱离 VS Code 运行

### 独特功能
- **Git Checkpoint**：每步操作自动保存 Git 快照，可回滚到任意步骤
- **Subagent 系统**：原生并行子代理，独立上下文窗口，可并发执行只读任务
- **new_task 工具**：跨会话上下文传递，解决长任务上下文窗口限制
- **Strict Plan Mode**：强制先规划再执行
- **Focus Chain**：交互式任务清单
- **扩展思维**：Claude/O1/Gemini 思维链可视化
- **命令权限控制器**：正则匹配 + 重定向/子 shell 检测
- **Skills/Workflows**：Markdown 定义的可复用技能
- **Headless 浏览器**：内置 browser_action 工具

## 技术架构（源码分析）

### 项目结构

```
cline/
├── src/
│   ├── extension.ts          # VS Code 扩展入口
│   ├── core/
│   │   ├── controller/       # 主控制器（1000+ 行）
│   │   ├── task/             # 代理循环 + 工具处理器
│   │   ├── api/              # LLM 提供商工厂（43+）
│   │   ├── prompts/          # 系统提示组件
│   │   ├── permissions/      # 命令权限
│   │   ├── slash-commands/    # Slash 命令
│   │   └── hooks/            # Hook 系统
│   ├── integrations/
│   │   ├── checkpoints/      # Git Checkpoint（多文件模块化）
│   │   ├── claude-code/      # Claude Code 集成
│   │   └── openai-codex/     # OpenAI Codex 集成
│   └── services/
│       └── mcp/              # MCP 集成（McpHub + OAuth）
├── webview-ui/               # React WebView UI
├── cli/                      # 独立 CLI
└── proto/                    # Protocol Buffers 定义
```

### 核心代理循环

```
用户提交任务 (WebView)
  → Controller.initTask()
  → Task (代理循环)
    → createMessage(systemPrompt, messages, tools) [流式]
    → 解析响应（文本 / 工具调用 / 思维链）
    → ToolExecutor 执行工具
      → CommandPermissionController (正则 + 重定向检测)
      → AutoApprove 检查
      → 用户确认（如需要）
      → 执行 + 收集结果
    → Checkpoint 保存 (Git commit)
    → 循环直到 attempt_completion
```

### 工具系统（24+ 种）

| 类别 | 工具 |
|------|------|
| 文件 | read_file, write_to_file, replace_in_file, list_files, list_code_definition_names |
| 搜索 | search_files, web_search, web_fetch |
| 执行 | execute_command |
| 浏览器 | browser_action（Headless Chrome） |
| MCP | use_mcp_tool, access_mcp_resource, load_mcp_documentation |
| 交互 | ask_followup_question, attempt_completion |
| 规划 | plan_mode_respond, act_mode_respond |
| 任务 | focus_chain, new_task |
| 子代理 | use_subagents（并行只读子代理） |
| 其他 | condense, summarize_task, report_bug, generate_explanation, apply_patch |

### Checkpoint 系统

每步操作自动 Git commit，用户可视化 diff，一键回滚到任意步骤。自动排除 node_modules/.git 等，支持多根工作区。

### 权限系统

```
命令执行
  → CommandPermissionController
    → 正则匹配（allow/deny 列表）
    → 重定向检测（>, >>, |, &&）
    → 子 shell/反引号检测
  → AutoApprove 设置
  → .cline-ignore 文件过滤
  → 用户确认
```

## 安装

```bash
# VS Code 扩展（主要方式）
# 1. VS Code → 扩展 → 搜索 "Cline" → 安装

# 独立 CLI
npm install -g @cline/cli
```

## 支持的提供商（48+）

Anthropic, OpenRouter, OpenAI, Google Gemini, AWS Bedrock, Azure, GCP Vertex, SAP AI Core, Cerebras, Groq, DeepSeek, Qwen, Mistral, xAI, Ollama, LM Studio, HuggingFace, LiteLLM, Fireworks, SambaNova, Together, Doubao, AiHubMix, Requesty 等（43+ 提供商文件）。

## 优势

1. **VS Code 原生**：最佳 IDE 集成体验
2. **Checkpoint 回滚**：Git 快照保证安全
3. **提供商丰富**：43+ 提供商支持
4. **Plan/Act 模式**：规划和执行分离
5. **社区庞大**：60k+ Stars，5M+ 用户，活跃开发
6. **MCP + Hook**：强大的扩展能力

## 劣势

1. **VS Code 依赖**：主要功能绑定 VS Code
2. **非终端原生**：CLI 是辅助，非主力
3. **内存占用**：Electron + WebView 较重
4. **无 Git 原生工作流**：不像 Aider 自动提交

## 使用场景

- **最适合**：VS Code 用户、需要可视化操作回滚
- **适合**：前端开发、全栈项目、浏览器测试
- **不太适合**：纯终端工作流、服务器端开发

## 资源链接

- [GitHub](https://github.com/cline/cline)
- [VS Code Marketplace](https://marketplace.visualstudio.com/items?itemName=saoudrizwan.claude-dev)
- [文档](https://docs.cline.bot/)
