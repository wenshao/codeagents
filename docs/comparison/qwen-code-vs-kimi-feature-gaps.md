# 25. Qwen Code vs Kimi CLI：双向功能缺口分析

> 两个国内 AI 编程 CLI 代理的功能互补分析——Qwen Code（TypeScript，Gemini CLI 分叉）vs Kimi CLI（Python，独立实现）

## 概览

| 维度 | Qwen Code | Kimi CLI |
|------|-----------|----------|
| **语言** | TypeScript | Python |
| **代码量** | ~191k 行（分叉） | ~20k 行 |
| **上游** | Gemini CLI 分叉 | 独立实现 |
| **运行时** | Node.js 20+ | Python 3.12+ |
| **CLI 框架** | Ink + React | Typer + Rich |

---

## 功能全景对比

| 功能 | Qwen Code | Kimi CLI | 状态 |
|------|-----------|----------|------|
| **核心代理循环** | ✅ | ✅ KimiSoul | 对等 |
| 多提供商 LLM | ✅ 5 提供商 | ✅ 5 提供商 | 对等 |
| MCP 集成 | ✅ Stdio/SSE/HTTP | ✅ | 对等 |
| OAuth 认证 | ✅ Qwen OAuth | ✅ 多平台 OAuth | 对等 |
| 工具/技能系统 | ✅ | ✅ | 对等 |
| 会话管理 | ✅ JSONL | ✅ | 对等 |
| 扩展思维/推理 | ✅ `thinkingConfig` | ✅ `thinking_mode` | 对等 |
| 上下文压缩 | ✅ `chatCompressionService` | ✅ `compaction.py` | 对等 |
| Plan 模式 | ✅ | ✅ 多选项审批 | 对等 |
| 交互式 Shell | ✅ `!` 模式切换 | ✅ Ctrl-X 切换 | 对等（交互方式不同） |
| 子代理/Task | ✅ SubagentManager | ✅ multiagent/task | 对等 |
| Todo/任务管理 | ✅ todoWrite | ✅ SetTodoList | 对等 |
| **Arena 竞争模式** | ✅ ArenaManager | ❌ | **Qwen 独有** |
| **6 语言 UI** | ✅ 中/英/日/德/俄/葡 | ❌ | **Qwen 独有** |
| **免费 OAuth 1000/天** | ✅ | ❌ | **Qwen 独有** |
| **扩展市场** | ✅ marketplace.ts | ❌ | **Qwen 独有** |
| **Claude/Gemini 扩展转换** | ✅ | ❌ | **Qwen 独有** |
| **多终端后端** | ✅ Tmux/iTerm2/进程内 | ❌ | **Qwen 独有** |
| **Wire 协议** | ❌ | ✅ SPMC 通道 | **Kimi 独有** |
| **ACP 服务器** | ❌ | ✅ IDE 原生集成 | **Kimi 独有** |
| **后台任务管理 UI** | 部分（shell `is_background` 参数） | ✅ TaskList/TaskOutput/TaskStop | Kimi 管理更完整 |
| **D-Mail 上下文优化** | ❌ | ✅ 向过去检查点发消息 | **Kimi 独有** |
| **FastAPI Web 服务器** | ❌ | ✅ Web + 可视化 | **Kimi 独有** |
| AskUser 多选交互 | ✅ `QuestionOption` + `multiSelect` | ✅ 2-4 选项 + 批量 | 对等 |

---

## Qwen Code 应借鉴的 Kimi CLI 功能

### 1. Wire 协议（多客户端通信基础）

**Kimi CLI 实现**（`src/kimi_cli/wire/`）：
- SPMC（单生产者多消费者）通道
- 消息合并、文件录制、队列管理
- 支持 Raw 和 Merged 消息流
- TUI、Web、IDE 客户端共享同一通信协议

**Qwen Code 缺失影响**：无法实现真正的多客户端架构。Qwen 的 `packages/webui/` 仅是 UI 组件库，不是独立客户端。

**工作量**：高（2-3 周）

---

### 2. ACP 服务器（IDE 原生集成）

**Kimi CLI 实现**（`src/kimi_cli/acp/`）：
- 完整的 Agent Client Protocol 服务器
- 多会话管理 + 协议版本协商
- 终端认证 + 客户端能力检测
- Prompt 能力 + MCP 集成

**Qwen Code 现状**：有 `packages/vscode-ide-companion/`（VS Code 扩展），但无独立 ACP 服务器供多 IDE 接入。

**工作量**：高（2-3 周）

---

### 3. 后台任务管理 UI（增强现有能力）

**Kimi CLI 实现**（`src/kimi_cli/tools/background/`）：
- `TaskList` — 列出所有后台任务及状态
- `TaskOutput` — 获取任务输出（阻塞/非阻塞）
- `TaskStop` — 中断任务
- 支持超时、输出预览、心跳检测

**Qwen Code 现状**：Shell 工具已支持后台执行（`shell.ts:55` `is_background` 参数），但**缺少任务管理界面**——无法列出/查看/停止已启动的后台任务。

**建议增强**：在现有 `is_background` 基础上增加 TaskList/TaskOutput/TaskStop 工具。

**工作量**：中（2-3 天，后台执行已有，仅需管理 UI）

---

### 4. D-Mail（上下文时间旅行）

**Kimi CLI 实现**（`src/kimi_cli/tools/dmail/`）：
- 向过去的检查点发送消息
- 回滚到之前的对话状态，附带摘要数据
- 减少上下文窗口浪费（灵感来自 Steins;Gate）

**Qwen Code 现状**：有检查点系统（`restoreCommand.ts` + `/restore` 命令），但只能恢复，不能向过去注入信息。

**评估**：创意性功能，减少 token 浪费。但实现复杂度高，实际用户价值待验证。

**工作量**：中（3-5 天）

---

### 5. FastAPI Web 服务器

**Kimi CLI 实现**（`src/kimi_cli/web/`, `src/kimi_cli/vis/`）：
- FastAPI + Uvicorn
- 会话管理 API + 统计可视化
- 配合 Wire 协议实现 Web 客户端

**Qwen Code 缺失影响**：无法通过浏览器远程访问。

**工作量**：高（2-3 周，可参考 OpenCode 的 Hono 方案或 Kimi 的 FastAPI 方案）

---

### ~~6. AskUser 增强交互~~ ✅ 已验证存在

Qwen Code 的 `askUserQuestion.ts` 已有完整的结构化选项交互：
- `QuestionOption` 接口（label + description）
- `multiSelect` 多选支持
- `questions: Question[]` 批量问题
- `ToolAskUserQuestionConfirmationDetails` 确认对话框

与 Kimi CLI 的 `ask_user` 功能等价。

---

## Kimi CLI 应借鉴的 Qwen Code 功能

### A. Arena 模式（多模型竞争评估）

**Qwen Code 实现**（`packages/core/src/agents/arena/`）：
- `ArenaManager.ts`：最多 N 个模型并行执行
- Git worktree 隔离每个代理的工作环境
- PTY 子进程并行执行 + 事件流实时更新
- 结果收集和对比

**Kimi CLI 缺失影响**：无法并行比较多个模型在同一任务上的表现。

---

### B. 扩展市场 + 格式转换

**Qwen Code 实现**：
- `marketplace.ts`（280 行）：GitHub 安装源解析
- `claude-converter.ts`：Claude 插件格式转换
- `gemini-converter.ts`：Gemini 扩展格式转换
- 支持 Git clone、GitHub release、本地目录安装

**Kimi CLI 缺失**：无扩展市场，无跨工具扩展兼容。

---

### C. 6 语言国际化

**Qwen Code 实现**：中/英/日/德/俄/葡完整本地化。

**Kimi CLI 缺失**：仅日志级别的语言支持。

---

### D. 多终端后端（并行分屏）

**Qwen Code 实现**：InProcess + iTerm2 + Tmux 三种后端自动检测，用于 Arena 多代理并行分屏显示。

**Kimi CLI 现状**：有 TUI + ACP + Web 三种客户端模式，但无终端分屏并行显示多个代理。

---

## 优先级矩阵（Qwen Code 视角）

| 功能 | 工作量 | 用户价值 | 优先级 |
|------|--------|---------|--------|
| ~~AskUser 增强~~ | — | — | ✅ 已有（`QuestionOption` + `multiSelect`） |
| 后台任务管理 UI（补全 TaskList/Output/Stop） | 低（2-3 天） | **高**（管理后台任务） | **P1** |
| D-Mail 上下文优化 | 中（3-5 天） | 中（创新性） | P2 |
| ACP 服务器 | 高（2-3 周） | 中（多 IDE） | P2 |
| Wire 协议 | 高（2-3 周） | 中（多客户端基础） | P2 |
| FastAPI Web 服务器 | 高（2-3 周） | 中（远程访问） | P2 |

---

## 一句话总结

**Qwen Code 的优势**：Arena 竞争模式、扩展市场 + 格式转换、6 语言 UI、多终端后端——生态更成熟。

**Kimi CLI 的优势**：Wire 协议 + ACP 服务器（多客户端架构基础）、后台任务管理、D-Mail 上下文优化——架构更创新。

**Qwen Code 最值得借鉴的 1 件事**：后台任务管理 UI（TaskList/TaskOutput/TaskStop，后台执行已有但缺管理界面）。

> 注：~~AskUser 多选交互~~ 经 R1 核实，Qwen Code 已有完整实现（`QuestionOption` + `multiSelect`）。

**Kimi CLI 最值得借鉴的 1 件事**：Arena 模式（多模型并行竞争评估）。

---

*分析基于 Qwen Code 和 Kimi CLI 本地源码，截至 2026 年 3 月。*
