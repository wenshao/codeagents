# 4. Qwen Code 用户使用指南

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

### 3. 6+ 模型提供商

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
| 初始化项目 | `/init`（生成 QWEN.md） |
| 回退 | `/restore`（恢复检查点） |
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

### QWEN.md（项目指令）

> Qwen Code 使用 `QWEN.md` 作为项目指令文件（也兼容 `GEMINI.md`）。

在项目根目录创建 `QWEN.md`：

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

### modelProviders 配置（自定义模型提供商）

> 源码：`packages/core/src/models/types.ts`（ModelConfig 接口）

`modelProviders` 是 Qwen Code 最强大的配置项——可以接入任何 OpenAI 兼容 API、Anthropic、Gemini 以及本地模型。配置后通过 `/model` 切换。

**配置位置**：`~/.qwen/settings.json`（用户级）或 `.qwen/settings.json`（项目级）

**顶层结构**：

```json
{
  "modelProviders": {
    "openai": [ /* OpenAI 兼容的模型列表 */ ],
    "anthropic": [ /* Anthropic 模型列表 */ ],
    "gemini": [ /* Google Gemini 模型列表 */ ]
  }
}
```

三个 `authType` 键决定使用哪个 SDK：`openai`（OpenAI SDK）、`anthropic`（Anthropic SDK）、`gemini`（Google GenAI SDK）。DeepSeek、OpenRouter、Ollama 等 OpenAI 兼容服务都使用 `openai` 键。

**ModelConfig 字段**：

| 字段 | 类型 | 必须 | 说明 |
|------|------|------|------|
| `id` | string | **是** | 发送给 API 的模型 ID（如 `"gpt-4o"`、`"deepseek-chat"`） |
| `name` | string | 否 | UI 显示名称（默认为 id） |
| `description` | string | 否 | 模型描述 |
| `envKey` | string | **是** | 存放 API Key 的**环境变量名**（如 `"OPENAI_API_KEY"`） |
| `baseUrl` | string | 否 | API 端点覆盖（自定义提供商必须） |
| `generationConfig` | object | 否 | 生成参数（见下方） |

**generationConfig 常用字段**：

| 字段 | 说明 |
|------|------|
| `timeout` | 请求超时（毫秒） |
| `maxRetries` | 速率限制重试次数 |
| `contextWindowSize` | 覆盖自动检测的上下文窗口大小 |
| `enableCacheControl` | 启用缓存控制（DashScope 提供商） |
| `reasoning` | 推理模式：`false` 或 `{ effort: "low"\|"medium"\|"high" }` |
| `customHeaders` | 自定义 HTTP 头 |
| `samplingParams` | 采样参数：`temperature`、`top_p`、`top_k`、`max_tokens` 等 |

#### 常见提供商配置示例

**DashScope（阿里云百炼编码计划）**：

```json
{
  "modelProviders": {
    "openai": [{
      "id": "qwen3-coder-plus",
      "name": "Qwen3-Coder-Plus（百炼）",
      "envKey": "BAILIAN_CODING_PLAN_API_KEY",
      "baseUrl": "https://coding.dashscope.aliyuncs.com/v1"
    }]
  }
}
```

**DeepSeek（OpenAI 兼容）**：

```json
{
  "modelProviders": {
    "openai": [{
      "id": "deepseek-chat",
      "name": "DeepSeek Chat",
      "envKey": "DEEPSEEK_API_KEY",
      "baseUrl": "https://api.deepseek.com/v1"
    }]
  }
}
```

**OpenRouter（100+ 模型聚合）**：

```json
{
  "modelProviders": {
    "openai": [{
      "id": "openai/gpt-4o",
      "name": "GPT-4o（OpenRouter）",
      "envKey": "OPENROUTER_API_KEY",
      "baseUrl": "https://openrouter.ai/api/v1"
    }]
  }
}
```

**Ollama（本地模型，无需付费）**：

```json
{
  "modelProviders": {
    "openai": [{
      "id": "qwen2.5-7b",
      "name": "Qwen2.5 7B（本地）",
      "envKey": "OLLAMA_API_KEY",
      "baseUrl": "http://localhost:11434/v1",
      "generationConfig": {
        "timeout": 300000,
        "contextWindowSize": 32768
      }
    }]
  }
}
```

> Ollama 不需要真实 API Key，设置任意占位值即可：`export OLLAMA_API_KEY="ollama"`

**Anthropic（Claude 系列）**：

```json
{
  "modelProviders": {
    "anthropic": [{
      "id": "claude-sonnet-4-5",
      "name": "Claude Sonnet 4.5",
      "envKey": "ANTHROPIC_API_KEY",
      "generationConfig": {
        "contextWindowSize": 200000
      }
    }]
  }
}
```

**Google Gemini**：

```json
{
  "modelProviders": {
    "gemini": [{
      "id": "gemini-2.5-flash",
      "name": "Gemini 2.5 Flash",
      "envKey": "GEMINI_API_KEY",
      "generationConfig": {
        "contextWindowSize": 1000000
      }
    }]
  }
}
```

#### 多提供商组合配置

```json
{
  "modelProviders": {
    "openai": [
      { "id": "gpt-4o", "name": "GPT-4o", "envKey": "OPENAI_API_KEY" },
      { "id": "deepseek-chat", "name": "DeepSeek", "envKey": "DEEPSEEK_API_KEY", "baseUrl": "https://api.deepseek.com/v1" },
      { "id": "qwen2.5-7b", "name": "Qwen 本地", "envKey": "OLLAMA_API_KEY", "baseUrl": "http://localhost:11434/v1" }
    ],
    "anthropic": [
      { "id": "claude-sonnet-4-5", "name": "Claude Sonnet 4.5", "envKey": "ANTHROPIC_API_KEY" }
    ],
    "gemini": [
      { "id": "gemini-2.5-flash", "name": "Gemini Flash", "envKey": "GEMINI_API_KEY" }
    ]
  }
}
```

配置完成后通过 `/model` 命令切换，所有配置的模型都会出现在选择列表中。

#### 注意事项

- **API Key 不存储在配置中**——`envKey` 引用的是环境变量名，运行时从 `process.env` 读取
- **同一 authType 内不支持重复 id**——首个生效，后续重复跳过并发出警告
- **项目级覆盖用户级**——`.qwen/settings.json` 的 `modelProviders` **完全替换**（非合并）`~/.qwen/settings.json` 的同名配置
- **无效 authType 键静默忽略**——拼写错误（如 `"openai-custom"`）不会报错也不会生效
- **`qwen-oauth` 不可覆盖**——内置的 OAuth 免费层无法通过 modelProviders 自定义

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

- `GEMINI.md` → Qwen Code 兼容读取，也可重命名为 `QWEN.md`
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

## 与其他 Agent 对比

| 维度 | Qwen Code | Claude Code | Copilot CLI |
|------|-----------|-------------|-------------|
| **免费层** | **1000 次/天** | 无 | 有限 |
| **中文支持** | **原生 7 语言** | 英文为主 | 英文为主 |
| **开源** | **✓ Apache-2.0** | ✗ | ✗ |
| **Arena 模式** | **✓ 独有** | ✗ | ✗ |
| **/review 代理数** | 4 | 4-6 | 1 |
| **模型提供商** | 6+（Qwen/DashScope/OpenAI/Anthropic/DeepSeek/OpenRouter） | 1 (Anthropic) | 多个 |
| **指令文件** | QWEN.md（兼容 GEMINI.md） | CLAUDE.md | AGENTS.md |
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
/restore       # 恢复检查点
# 或 /resume 恢复之前的会话
```

### 项目分析不准确

```bash
/init          # 重新分析项目，更新 QWEN.md
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
