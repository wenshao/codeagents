# Qwen Code (通义灵码 CLI)

**开发者：** 阿里云
**许可证：** Apache-2.0
**仓库：** [github.com/QwenLM/qwen-code](https://github.com/QwenLM/qwen-code)
**文档：** [qwenlm.github.io/qwen-code-docs](https://qwenlm.github.io/qwen-code-docs/zh/)
**Stars：** 约 20k+
**最后更新：** 2026-03

## 概述

Qwen Code 是阿里云推出的开源 AI 编程代理，运行在终端中。基于 Google Gemini CLI 分叉并大幅增强，针对 Qwen3-Coder 系列模型优化，是中国首款由大模型厂商发布的终端编程工具。支持多提供商（Qwen/OpenAI/Anthropic/Gemini），提供免费 OAuth 额度和完整的多语言国际化。

## 核心功能

### 基础能力
- **终端原生**：基于 Ink + React 的终端 UI
- **16 个内置工具**：文件编辑、Bash 执行、Grep 搜索、Web 抓取等
- **多提供商**：Qwen OAuth（免费）、DashScope、ModelScope、Anthropic、Google、自定义端点（6+）
- **MCP 支持**：模型上下文协议（SSE + Stdio）
- **LSP 集成**：语言服务器协议支持
- **多语言 UI**：中/英/日/德/俄/葡 6 种语言

### 独特功能
- **免费 OAuth 额度**：通义账号每天 1000 次免费请求
- **基于 Gemini CLI**：继承 Gemini CLI 架构并大幅增强
- **Plan 模式**：显式规划阶段，执行前需审批
- **多代理终端**：Tmux/iTerm2 后端支持并行代理
- **扩展系统**：支持 Qwen、Claude、Gemini 三种格式的扩展转换
- **Loop 检测**：Levenshtein 距离检测重复工具调用
- **聊天压缩**：基于 token 阈值的上下文压缩

## 技术架构（源码分析）

### Monorepo 结构

```
qwen-code/
├── packages/cli/           # CLI 界面（Ink/React）
├── packages/core/          # 核心引擎和工具
├── packages/sdk-typescript/ # TypeScript SDK
├── packages/sdk-java/      # Java SDK
├── packages/test-utils/    # 测试工具
├── packages/vscode-ide-companion/  # VS Code 扩展
├── packages/webui/         # Web UI
└── packages/zed-extension/ # Zed 编辑器扩展
```

### 核心架构

```
CLI (Ink/React)
    ↓
GeminiClient (会话编排)
    ↓
ContentGenerator (多提供商抽象)
    ├── GeminiContentGenerator
    ├── OpenAiContentGenerator
    └── AnthropicContentGenerator
    ↓
CoreToolScheduler (工具调度)
    ↓
PermissionManager (权限管理)
    ↓
工具执行 → 文件系统/Shell
```

### 技术栈
- **语言**：TypeScript 5.3+（严格模式）
- **运行时**：Node.js 20+
- **CLI 框架**：Ink 6.2 + React 19（终端渲染）
- **构建**：esbuild
- **模型 SDK**：Google Genai SDK + OpenAI SDK + Anthropic SDK
- **MCP SDK**：@modelcontextprotocol/sdk v1.25

### 工具调度器

核心文件 `coreToolScheduler.ts`（60KB+）实现完整的工具执行管线：

```
LLM 工具调用
  → 参数校验 (validating)
  → 权限检查 (getDefaultPermission)
  → 用户确认 (awaiting_approval)
  → 工具执行 (executing)
  → 结果返回 (success/error)
```

支持实时输出流、自动重试、Hook 触发（PreToolUse/PostToolUse）。

### 权限系统

```
优先级：deny > ask > allow > default
配置源：settings.json > 代理默认 > SDK 参数
```

- Shell 命令语义解析（extractShellOperations）
- 路径/命令模式匹配
- 会话级和持久化规则

## 安装

```bash
# npm（推荐，需要 Node.js 20+）
npm install -g @qwen-code/qwen-code@latest

# bun
bun add -g @qwen-code/qwen-code

# Homebrew（macOS、Linux）
brew install qwen-code

# 验证安装
qwen --version
```

## 模型支持

| 提供商 | 模型 | 认证方式 | 免费额度 |
|--------|------|---------|---------|
| **Qwen OAuth** | coder-model (qwen3.5-plus) | 浏览器 OAuth | 1000 次/天 |
| DashScope | qwen3-coder-plus, turbo | API Key | 按量付费 |
| ModelScope | qwen3-coder 系列 | API Key | 按量付费 |
| Anthropic | Claude 3.5 Sonnet, Opus | API Key | 无 |
| Google | Gemini 2.0 Flash 等 | API Key | 有限免费 |
| 自定义 | OpenAI 兼容端点 | API Key | 取决于提供商 |

## 斜杠命令（39 个 + 1 Skill，源码：`packages/cli/src/ui/commands/`）

> 从源码逐文件验证。Qwen Code 基于 Gemini CLI 分叉，继承核心命令并新增 Arena/语言/洞察等。

### 核心命令
| 命令 | 用途 | 来源 |
|------|------|------|
| `/help` | 显示帮助信息 | 继承 Gemini |
| `/auth` | 管理认证与登录（Qwen OAuth / API Key） | 继承+增强 |
| `/model` | 切换模型 | 继承 |
| `/clear` | 清除对话历史 | 继承 |
| `/compress` | 压缩上下文（别名 `/compact`） | 继承 |
| `/memory` | 查看/编辑记忆 | 继承 |
| `/tools` | 查看可用工具列表 | 继承 |
| `/mcp` | 查看/管理 MCP 服务器 | 继承 |
| `/settings` | 查看/修改设置 | 继承 |
| `/permissions` | 管理权限（allow/ask/deny） | 继承 |
| `/context` | 查看上下文 token 用量 | 继承 |
| `/copy` | 复制上次回复到剪贴板 | 继承 |

### 会话与导航
| 命令 | 用途 | 来源 |
|------|------|------|
| `/restore` | 恢复历史会话 | 继承 |
| `/resume` | 继续上次会话 | 继承 |
| `/export` | 导出当前会话 | 继承 |
| `/quit` | 退出（别名 `/exit`） | 继承 |

### 开发辅助
| 命令 | 用途 | 来源 |
|------|------|------|
| `/agents` | 查看/管理代理 | 继承 |
| `/skills` | 查看可用技能 | 继承 |
| `/approval-mode` | 切换审批模式（plan/default/auto-edit/yolo） | 继承（Gemini 的 `/plan`） |
| `/stats` | 显示统计信息 | 继承 |
| `/editor` | 在外部编辑器中编辑 | 继承 |
| `/hooks` | 查看 Hook 配置 | 继承 |
| `/init` | 初始化项目配置（生成 QWEN.md） | 继承 |
| `/btw` | **快速旁问**——不中断主对话，开启独立侧边提问 | **Qwen 自行添加** |
| `/trust` | 管理信任设置 | 继承 |
| `/summary` | 生成对话摘要 | 继承 |

### 终端与 UI
| 命令 | 用途 | 来源 |
|------|------|------|
| `/theme` | 切换颜色主题 | 继承 |
| `/vim` | 切换 Vim 编辑模式 | 继承 |
| `/terminal-setup` | 配置终端集成 | 继承 |
| `/ide` | IDE 集成管理 | 继承 |
| `/directory` | 目录管理 | 继承 |
| `/setup-github` | 设置 GitHub 集成 | 继承 |

### 信息与反馈
| 命令 | 用途 | 来源 |
|------|------|------|
| `/about` | 显示版本信息 | 继承 |
| `/bug` | 报告 Bug | 继承 |
| `/docs` | 打开文档 | 继承 |

### Qwen Code 新增命令
| 命令 | 用途 | 来源 |
|------|------|------|
| `/arena` | **Arena 模式**——多模型在隔离 Git worktree 中竞争执行同一任务 | **Qwen 新增** |
| `/language` | **切换 UI 语言**（中/英/日/德/俄/葡） | **Qwen 新增** |
| `/insight` | **代码洞察**——分析代码库并生成洞察报告 | **Qwen 新增** |
| `/extensions` | **扩展管理**——安装/卸载/列表（兼容 Claude Code + Gemini 扩展） | **Qwen 新增** |

### Skill 命令
| 命令 | 用途 | 实现 |
|------|------|------|
| `/review` | **代码审查**——四代理并行审查（正确性+安全/代码质量/性能/自由审计） | Skill（`skills/bundled/review/SKILL.md`） |

> `/review` 的四个审查代理维度（源码：`SKILL.md`）：
> 1. **Agent 1: Correctness & Security** — 逻辑错误、空值处理、竞态条件、注入漏洞、类型安全
> 2. **Agent 2: Code Quality** — 代码风格一致性、命名规范、重复代码、过度工程
> 3. **Agent 3: Performance & Efficiency** — N+1 查询、内存泄漏、不必要重渲染、包大小影响
> 4. **Agent 4: Undirected Audit** — 无预设维度，全新视角捕获其他代理遗漏的问题
>
> 输出格式：Summary → Findings（Critical/Suggestion/Nice to have）→ Verdict（Approve/Request changes/Comment）

## 优势

1. **免费额度**：OAuth 登录即享每天 1000 次免费请求
2. **多语言 UI**：6 种语言本地化，对中文开发者极友好
3. **多提供商**：不锁定单一模型，灵活切换
4. **完整 SDK**：TypeScript + Java SDK，支持编程式集成
5. **大厂支持**：阿里云官方维护，持续更新
6. **扩展兼容**：可转换 Claude/Gemini 扩展格式

## 劣势

1. **基于 Gemini CLI 分叉**：部分变量名/结构仍带 Gemini 痕迹
2. **较新项目**：生态系统不如成熟工具
3. **文档较少**：英文资源有限
4. **社区较小**：相比 Claude Code/Aider 用户较少

## CLI 命令

```bash
# 启动交互式会话
qwen

# 直接提问
qwen "解释这段代码的作用"

# 非交互模式（适合 CI/CD）
qwen --non-interactive --prompt "重构 auth 模块"

# 使用特定模型
qwen --model qwen3-coder-plus

# 指定提供商
qwen --api-key $DASHSCOPE_API_KEY

# 沙箱模式
QWEN_SANDBOX=docker qwen
```

## 配置

```json
// ~/.qwen/settings.json
{
  "modelProviders": {
    "openai": [{
      "id": "qwen3-coder-plus",
      "name": "Qwen3-Coder Plus",
      "baseUrl": "https://dashscope.aliyuncs.com/compatible-mode/v1",
      "envKey": "DASHSCOPE_API_KEY"
    }]
  },
  "security": {
    "auth": { "selectedType": "openai" }
  },
  "permissions": {
    "allow": ["Bash"],
    "ask": ["Edit"]
  }
}
```

### 存储结构

```
~/.qwen/
├── settings.json          # 全局配置
├── locales/               # 自定义语言包
├── skills/                # 用户技能
├── agents/                # 用户子代理
├── commands/              # 自定义斜杠命令
└── tmp/<project_hash>/
    ├── chats/             # 会话 JSONL 文件
    └── memory/            # 记忆文件

.qwen/                     # 项目级（可选）
├── settings.json
├── system.md              # 自定义系统提示
├── skills/
└── agents/
```

## Hook 系统

支持的事件：

| 事件 | 触发时机 |
|------|---------|
| PreToolUse | 工具执行前 |
| PostToolUse | 工具执行后 |
| PostToolUseFailure | 工具执行失败后 |
| Notification | 通知事件 |
| UserPromptSubmit | 用户提交输入时 |
| SessionStart | 会话开始 |
| SessionEnd | 会话结束 |
| Stop | 代理停止时 |
| SubagentStart | 子代理启动 |
| SubagentStop | 子代理停止 |
| PreCompact | 上下文压缩前 |
| PermissionRequest | 权限请求时 |

## 使用场景

- **最适合**：中文开发者、需要免费额度的用户、阿里云生态用户
- **适合**：日常编码、多提供商切换、SDK 集成
- **不太适合**：需要极强推理能力的复杂任务（受限于模型能力）

## 与通义灵码的关系

- **通义灵码**：IDE 插件，类似 GitHub Copilot，实时补全
- **Qwen Code**：CLI 工具，类似 Claude Code，代理式编程
- 两者互补，可同时使用

## 资源链接

- [GitHub](https://github.com/QwenLM/qwen-code)
- [文档](https://qwenlm.github.io/qwen-code-docs/zh/)
- [官网](https://qwen.ai/qwencode)
- [阿里云文档](https://help.aliyun.com/zh/model-studio/qwen-code)
- [Qwen3-Coder 博客](https://qwenlm.github.io/zh/blog/qwen3-coder/)

## 相关项目

- [Qwen](https://github.com/QwenLM/Qwen) - 主模型仓库
- [Google Gemini CLI](https://github.com/google-gemini/gemini-cli) - 上游项目
