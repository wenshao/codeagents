# OpenCode 遥测与安全分析证据

## 遥测系统
- **无遥测** — 递归搜索零结果
- 无分析 SDK、无报告端点

## 数据采集
- **不采集**: Machine ID、UUID、主机名、硬件指纹
- 无外发分析请求

## 安全系统
- `permission/permission.go`: 基础工具权限审批
- 按请求 approve/deny + 会话级持久化授予
- 无提示注入检测、无 ML 分类器

来源: internal/ (GitHub 源码分析)

## 深度补充（源码级分析）

### 架构（Go + TypeScript 混合）
- packages/tui/: Ink + React TUI（TypeScript）
- internal/: Go 后端
- 多客户端: TUI + Web + Desktop（ACP 协议）

### 代理系统（7 个内置代理，源码: internal/agent/）
| 代理 | 用途 |
|------|------|
| general | 通用任务 |
| coder | 代码生成 |
| plan | 任务规划 |
| explore | 代码库探索 |
| debug | 调试辅助 |
| review | 代码审查 |
| architect | 架构设计 |

### 工具系统（18 个，源码: internal/tool/）
ReadFile, WriteFile, EditFile, RunCommand, ListDirectory, SearchContent, GlobFiles, Fetch, AskUser, Diagnostic, Git, CreateFile, DeleteFile, MoveFile, GetDefinition, FindReferences, RenameSymbol, CodeAction

### LSP 集成（37 语言服务器，26 格式化器）
- 源码: internal/lsp/
- 自动检测项目语言并启动对应 LSP
- 代码跳转、悬停、诊断、重命名、引用查找

### 认证系统（3 个插件）
- CopilotAuthPlugin: GitHub Copilot OAuth
- CodexAuthPlugin: OpenAI ChatGPT Plus/Pro OAuth
- GitlabAuthPlugin: GitLab OAuth

### 模型支持（100+ 提供商）
- 通过 models.dev + Vercel AI SDK 动态加载
- 11 个 well-known 提供商代码内定义
- 支持 API key 轮转和多提供商切换

### ACP IDE 集成
- Agent Communication Protocol
- VS Code + JetBrains 扩展
- 双向通信: 编辑器状态 → Agent, Agent 建议 → 编辑器

### 配置优先级
managed > user > project > environment variables

来源: GitHub 源码 internal/ + packages/ (Go + TypeScript)
