# Qwen Code 源码深度分析证据

## 基本信息
- 仓库: QwenLM/qwen-code, Apache-2.0, TypeScript, ~21k stars
- 基于: Google Gemini CLI 分叉
- AGENTS.md: "This project is based on Google Gemini CLI with adaptations to better support Qwen-Coder models."

## 遥测系统（双管道，源码确认）

### A. OpenTelemetry（继承 Gemini CLI，重品牌）
- 源码: packages/core/src/telemetry/sdk.ts
- 事件前缀: `gemini-cli.*` → `qwen-code.*`
- 环境变量: `QWEN_TELEMETRY_ENABLED`, `QWEN_TELEMETRY_TARGET`, `QWEN_TELEMETRY_OTLP_ENDPOINT`
- **Clearcut 已移除** — 无 play.googleapis.com 引用

### B. 阿里云 RUM（全新，Qwen 添加）
- 源码: packages/core/src/telemetry/qwen-logger/qwen-logger.ts
- 端点: `gb4w8c3ygj-default-sea.rum.aliyuncs.com`
- App ID: `gb4w8c3ygj@851d5d500f08f92`
- 事件类型: RumViewEvent, RumActionEvent, RumExceptionEvent, RumResourceEvent
- 40+ 个事件: session, prompts, tool calls, API, arena, auth, subagent, skills, feedback

## 认证系统（全新，Qwen 添加）
- OAuth2 设备码流程 + PKCE (RFC 7636)
- OAuth 基础 URL: https://chat.qwen.ai
- Client ID: f0304373b74a44d2b584a3fb70ca9e56
- Scope: openid profile email model.completion
- 凭据存储: ~/.qwen/oauth_creds.json
- 跨进程令牌管理: 文件锁 ~/.qwen/oauth_creds.lock

## 模型/提供商
- 默认模型: coder-model (= qwen3.5-plus)
- 嵌入模型: text-embedding-v4
- 5 个认证类型: openai, qwen-oauth, gemini, vertex-ai, anthropic
- 5 个后端: DashScope (阿里), DeepSeek, OpenRouter, ModelScope (阿里), Default OpenAI
- DashScope 端点: https://dashscope.aliyuncs.com/compatible-mode/v1
- DeepSeek 端点: https://api.deepseek.com/v1
- OpenRouter 端点: https://openrouter.ai/api/v1

## 命令系统（41 命令，v0.13.0）
继承 Gemini CLI + 新增: /arena, /language, /insight, /extensions, /loop

## Arena 模式（全新，Qwen 添加）
- 多模型竞争执行，每个模型在隔离 git worktree 中运行
- ArenaManager → ArenaAgentClient → PTY 子进程
- 后端: iTerm, Tmux, InProcess
- 遥测: arena_session_started/ended, arena_agent_completed

## 扩展系统（增强）
- 三格式兼容: Qwen 原生 + **Claude Code 插件转换器** + Gemini 扩展转换器
- claude-converter.ts: 将 Claude Code 插件转为 Qwen 格式
- marketplace.ts: GitHub 仓库安装

## 安全系统（继承 Gemini CLI）
- 权限: allow/ask/deny + glob 模式 + shell 语义分析
- 审批模式: plan/default/auto-edit/yolo
- Hook 系统: 14 事件 (PreToolUse, PostToolUse, PostToolUseFailure, Notification, UserPromptSubmit, SessionStart, SessionEnd, Stop, SubagentStart, SubagentStop, PreCompact, PermissionRequest 等)
- 沙箱: 继承 Gemini 实现

## 与 Gemini CLI 的差异
### 新增
1. 阿里云 RUM 遥测
2. Qwen OAuth2 + PKCE
3. DashScope/DeepSeek/OpenRouter/ModelScope 提供商
4. Anthropic Claude 提供商
5. Arena 多模型竞争模式
6. Claude Code 插件兼容
7. Java SDK + Web UI
8. 多语言文档 (6 种语言)

### 移除
1. Google Clearcut 分析
2. Google 品牌标识

### 保留
OpenTelemetry, Gemini/Vertex AI, MCP, 权限系统, Hook 系统(14事件), Skill 系统, 工具系统(16核心), IDE 集成, LSP
