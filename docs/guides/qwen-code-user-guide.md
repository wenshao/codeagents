# Qwen Code 用户使用指南

> 阿里云 Qwen 团队出品的开源 AI 编程代理。每天 1000 次免费，支持中文界面，基于 Gemini CLI 深度定制。

---

## 快速开始（3 分钟）

### 安装

```bash
# npm 安装（需要 Node.js >= 20）
npm install -g @qwen-code/qwen-code@latest

# Homebrew（macOS / Linux）
brew install qwen-code

# 验证
qwen --version
```

### 免费使用（OAuth 登录）

```bash
qwen          # 首次启动
# 选择 "Login with Qwen" → 浏览器打开 → 扫码或登录
# 登录后自动获得每天 1000 次免费额度
```

> **免费额度说明：** OAuth 登录后使用 `qwen3.5-plus` 模型，每天 1000 次请求，无需信用卡。

### 使用自己的 API Key

```bash
# DashScope（阿里云）
export DASHSCOPE_API_KEY="sk-xxx"
qwen --model qwen-max

# OpenAI 兼容
export OPENAI_API_KEY="sk-xxx"
qwen --model gpt-4o

# Anthropic
export ANTHROPIC_API_KEY="sk-xxx"
qwen --model claude-sonnet-4
```

---

## 核心优势

### 1. 每天 1000 次免费

OAuth 登录即用，无需信用卡。对于大部分日常开发任务足够。

### 2. 中文原生支持

```bash
/language       # 切换 UI 语言
# 支持：中文、英文、日文、法文、德文、俄文、葡文
```

界面、命令描述、错误消息全部本地化。

### 3. 5 个模型提供商

| 提供商 | 端点 | 说明 |
|--------|------|------|
| **Qwen OAuth** | chat.qwen.ai | 免费层（qwen3.5-plus） |
| **DashScope** | dashscope.aliyuncs.com | 阿里云付费 |
| **OpenAI** | api.openai.com | GPT 系列 |
| **Anthropic** | api.anthropic.com | Claude 系列 |
| **DeepSeek** | api.deepseek.com | DeepSeek 系列 |
| **OpenRouter** | openrouter.ai | 聚合 100+ 模型 |

### 4. Arena 多模型竞争

```bash
/arena          # 启动 Arena 模式
# 多个模型在隔离的 Git worktree 中并行执行同一任务
# 你选择最好的结果
```

Arena 模式是 Qwen Code 独有功能——让多个模型同时解决问题，你挑最优方案。

### 5. 跨工具扩展兼容

Qwen Code 同时兼容 **Claude Code 插件** 和 **Gemini CLI 扩展**：

```bash
/extensions     # 管理扩展
# 可以安装 Claude Code 的 .claude-plugin 插件
# 也可以安装 Gemini CLI 的扩展
```

---

## 日常使用

### 对话式开发

```
你: 给这个 Express API 加上请求限流

Qwen: [读取 server.ts] → [安装 express-rate-limit] → [编辑代码] → [测试]
      已添加 rate-limiter 中间件，限制每 IP 每分钟 100 次请求。

你: 把限制改成每分钟 50 次，并加上自定义错误消息

Qwen: [编辑 server.ts:23] → 已更新。
```

### 常用命令速查（40 个）

| 操作 | 命令 |
|------|------|
| 审查代码 | `/review`（4 并行代理：正确性+质量+性能+自由审计） |
| 压缩上下文 | `/compress` 或 `/compact` |
| 切换模型 | `/model` |
| 规划模式 | `/approval-mode`（plan/default/auto-edit/yolo） |
| 查看统计 | `/stats` |
| 记忆管理 | `/memory` |
| MCP 管理 | `/mcp` |
| 权限管理 | `/permissions` |
| 会话恢复 | `/restore` 或 `/resume` |
| 导出会话 | `/export` |
| Arena 竞争 | `/arena` |
| 切换语言 | `/language` |
| 代码洞察 | `/insight` |
| 扩展管理 | `/extensions` |
| 旁问（不中断） | `/btw` |
| 初始化项目 | `/init`（生成 GEMINI.md） |
| 回退 | `/rewind`（检查点回退） |
| 退出 | `/quit` |

---

## /review 代码审查（独特的四代理设计）

```bash
# 审查本地未提交更改
/review

# 审查指定 PR
/review 123

# 审查指定文件
/review src/auth.ts
```

### 四个并行审查代理

| 代理 | 维度 | 检查内容 |
|------|------|---------|
| **Agent 1** | 正确性 & 安全 | 逻辑错误、空值、竞态、注入漏洞、类型安全 |
| **Agent 2** | 代码质量 | 风格一致性、命名、重复代码、过度工程、死代码 |
| **Agent 3** | 性能 & 效率 | N+1 查询、内存泄漏、不必要重渲染、包大小 |
| **Agent 4** | **自由审计** | 无预设维度——全新视角捕获遗漏的问题 |

### 审查输出格式

```
### Summary
简短概述变更和总体评估

### Findings
- **Critical** — 必须修复
- **Suggestion** — 建议改进
- **Nice to have** — 可选优化

### Verdict
Approve | Request changes | Comment
```

审查 PR 后会自动恢复原始分支和 stash。

---

## Arena 模式（独有功能）

Arena 让多个模型在隔离环境中竞争解决同一任务：

```bash
/arena
你: 重构这个函数，提升性能

# 模型 A（qwen3.5-plus）在 worktree-A 中工作
# 模型 B（claude-sonnet）在 worktree-B 中工作
# 模型 C（gpt-4o）在 worktree-C 中工作

# 结果展示：每个模型的方案和代码
# 你选择最好的
```

**技术实现：**
- 每个模型在独立的 Git worktree 中运行（完全隔离）
- 使用 PTY 子进程（支持 iTerm、Tmux、InProcess 后端）
- 遥测记录竞争结果（arena_session_started/ended）

---

## 项目配置

### GEMINI.md（项目指令）

在项目根目录创建 `GEMINI.md`：

```markdown
# 项目：我的 API 服务

## 技术栈
Express + TypeScript + PostgreSQL + Prisma

## 构建命令
- pnpm dev: 开发模式
- pnpm test: 运行测试
- pnpm build: 构建生产版本

## 编码规范
- 使用 async/await，不用 callbacks
- 所有 API 端点需要 Zod 验证
- 错误响应使用统一的 AppError 类

## 禁止
- 不要修改数据库迁移文件
- 不要在代码中硬编码 API keys
```

### MCP 配置

```bash
# 通过 /mcp 管理
/mcp

# 或编辑 ~/.gemini/mcp.json
```

```json
{
  "mcpServers": {
    "postgres": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-postgres"],
      "env": {"DATABASE_URL": "postgresql://localhost:5432/mydb"}
    }
  }
}
```

### 权限模式

```bash
/approval-mode           # 查看/切换审批模式

# 四种模式：
# default — 写操作需确认（推荐）
# auto-edit — 自动编辑，Shell 需确认
# yolo — 全部自动（危险）
# plan — 只读规划模式
```

---

## 进阶技巧

### 1. 从 Gemini CLI 迁移

Qwen Code 基于 Gemini CLI 分叉，大部分配置直接兼容：

- `GEMINI.md` → 直接复用
- `~/.gemini/settings.json` → 复制到 `~/.qwen/`（大部分键相同）
- Gemini 扩展 → 直接安装

### 2. 安装 Claude Code 插件

```bash
/extensions
# 选择 "Install from GitHub"
# 输入 Claude Code 插件仓库 URL
# Qwen Code 自动通过 claude-converter 转换格式
```

### 3. 使用免费层做复杂任务

```bash
# 免费层每天 1000 次，充分利用：
/compact                    # 定期压缩，减少 token 消耗
/model qwen3.5-plus         # 确保使用免费模型
/plan                       # 先规划再执行，减少试错
```

### 4. 多提供商切换

```bash
# 免费额度用完后切换到 DeepSeek（便宜）
export DEEPSEEK_API_KEY="sk-xxx"
/model deepseek-chat

# 复杂任务切换到 Claude
export ANTHROPIC_API_KEY="sk-xxx"
/model claude-sonnet-4

# 回到免费
/model qwen3.5-plus
```

### 5. Hook 自定义

继承 Gemini CLI 的 Hook 系统（11 个事件）：

```json
// ~/.qwen/settings.json
{
  "hooks": {
    "PreToolUse": [{
      "command": "bash -c 'echo \"即将执行: $TOOL_NAME\"'"
    }]
  }
}
```

---

## 与其他工具对比

| 维度 | Qwen Code | Claude Code | Copilot CLI |
|------|-----------|-------------|-------------|
| **免费层** | **1000 次/天** | 无 | 有限 |
| **中文支持** | **原生 7 语言** | 英文为主 | 英文为主 |
| **开源** | **✓ Apache-2.0** | ✗ | ✗ |
| **Arena 模式** | **✓ 独有** | ✗ | ✗ |
| **/review 代理数** | 4 | 4-6 | 1 |
| **模型提供商** | 5+ | 1 (Anthropic) | 多个 |
| **指令文件** | GEMINI.md | CLAUDE.md | AGENTS.md |
| **扩展兼容** | Gemini + Claude | Claude 插件 | — |
| **安全监控** | 继承 Gemini 策略 | 28 条 BLOCK | — |
| **沙箱** | 继承 Gemini | Seatbelt/Docker | — |

---

## 常见问题

### 免费额度不够用

```bash
# 1. 压缩上下文减少 token
/compact

# 2. 切换到更便宜的提供商
export DEEPSEEK_API_KEY="sk-xxx"
/model deepseek-chat
```

### 想回到之前的状态

```bash
/rewind        # 选择回退点
# 三种选项：回退对话+代码 / 仅对话 / 仅代码
```

### 项目分析不准确

```bash
/init          # 重新分析项目，更新 GEMINI.md
```

### 扩展安装失败

```bash
/extensions    # 检查已安装扩展状态
# 确认网络连接和 GitHub 访问
```

---

## 延伸阅读

- [Qwen Code 源码分析（EVIDENCE.md）](../tools/qwen-code/EVIDENCE.md)
- [Qwen Code vs Claude Code 对比](../comparison/qwen-vs-claude-code.md)
- [/review 命令深度分析](../comparison/review-command.md)
- [配置示例对比](./config-examples.md)
- [上下文管理指南](./context-management.md)
- [GitHub 仓库](https://github.com/QwenLM/qwen-code)
