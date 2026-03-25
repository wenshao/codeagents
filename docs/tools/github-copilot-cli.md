# GitHub Copilot CLI

**开发者：** GitHub (Microsoft)
**许可证：** 专有
**仓库：** [github.com/github/copilot-cli](https://github.com/github/copilot-cli)
**文档：** [docs.github.com/copilot/concepts/agents/about-copilot-cli](https://docs.github.com/copilot/concepts/agents/about-copilot-cli)
**源码版本：** v0.0.403（npm `@github/copilot`）
**最后更新：** 2026-03

## 概述

GitHub Copilot CLI 是 GitHub 推出的终端原生 AI 编程代理。基于与 GitHub Copilot coding agent 相同的代理框架，提供代码构建、调试、重构等智能辅助能力，并深度集成 GitHub 工作流。以独立二进制形式运行（`copilot` 命令），支持 macOS、Linux 和 Windows。内置 12 个核心工具、21 个浏览器工具、48 个 GitHub 平台工具、3 个内置代理和 14 个模型。

## 安装

```bash
# 方式一：安装脚本（macOS / Linux）
curl -fsSL https://gh.io/copilot-install | bash

# 方式二：Homebrew（macOS / Linux）
brew install copilot-cli

# 方式三：WinGet（Windows）
winget install GitHub.Copilot

# 方式四：npm（全平台）
npm install -g @github/copilot

# 启动
copilot
```

支持 PAT 认证：创建带 "Copilot Requests" 权限的 fine-grained PAT，通过 `GH_TOKEN` 或 `GITHUB_TOKEN` 环境变量传入。

## 斜杠命令（32 个）

| 命令 | 别名 | 用途 |
|------|------|------|
| `/add-dir` | | 添加工作目录 |
| `/agent` | | 与内置代理交互 |
| `/allow-all` | `/yolo` | 允许所有工具执行，跳过确认 |
| `/clear` | | 清除对话历史 |
| `/compact` | | 压缩上下文窗口 |
| `/context` | | 查看/管理上下文 |
| `/cwd` | `/cd` | 切换当前工作目录 |
| `/delegate` | | 委派任务给子代理（需 CCA_DELEGATE 功能标志） |
| `/diff` | | 查看差异（实验性） |
| `/exit` | `/quit` | 退出程序 |
| `/experimental` | | 启用/查看实验性功能 |
| `/feedback` | | 提交保密反馈调查 |
| `/help` | | 显示帮助信息 |
| `/ide` | | IDE 集成（实验性） |
| `/init` | | 初始化项目配置 |
| `/list-dirs` | | 列出已添加的工作目录 |
| `/login` | | GitHub 账户认证登录 |
| `/logout` | | 退出 GitHub 账户 |
| `/lsp` | | 查看已配置的 LSP 服务器状态 |
| `/mcp` | | 管理 MCP 服务器 |
| `/model` | `/models` | 切换或列出可用模型 |
| `/plan` | | 创建执行计划（需 PLAN_COMMAND 功能标志） |
| `/plugin` | | 管理插件（需 PLUGIN_COMMAND 功能标志） |
| `/rename` | | 重命名当前会话 |
| `/reset-allowed-tools` | | 重置工具允许列表 |
| `/resume` | | 恢复之前的会话 |
| `/review` | | 调用 code-review 代理审查代码 |
| `/session` | | 管理会话 |
| `/share` | | 分享对话 |
| `/skills` | | 查看可用技能/工具 |
| `/terminal-setup` | | 配置终端集成 |
| `/theme` | | 切换颜色主题 |
| `/usage` | | 查看使用量/配额 |
| `/user` | | 查看当前用户信息 |

## 核心工具（11 个）

| 工具 | 用途 |
|------|------|
| `bash` | 执行 shell 命令 |
| `create` | 创建新文件 |
| `edit` | 编辑文件（基于差异） |
| `replace` | 替换文件内容 |
| `view` | 查看文件内容 |
| `glob` | 按模式匹配搜索文件名 |
| `grep` | 按正则表达式搜索文件内容 |
| `search` | 语义搜索 |
| `fetch` | 获取 URL 内容 |
| `git_apply_patch` | 应用 Git 补丁 |
| `search_code_subagent` | 代码搜索子代理 |

## 浏览器工具（19 个，基于 Playwright）

| 工具 | 用途 |
|------|------|
| `browser_click` | 点击页面元素 |
| `browser_close` | 关闭浏览器 |
| `browser_console_messages` | 获取控制台消息 |
| `browser_drag` | 拖拽元素 |
| `browser_evaluate` | 执行 JavaScript |
| `browser_fill_form` | 填写表单 |
| `browser_handle_dialog` | 处理对话框 |
| `browser_hover` | 悬停元素 |
| `browser_install` | 安装浏览器 |
| `browser_navigate` | 导航到 URL |
| `browser_navigate_back` | 后退导航 |
| `browser_network_requests` | 获取网络请求 |
| `browser_press_key` | 按键操作 |
| `browser_resize` | 调整浏览器窗口大小 |
| `browser_select_option` | 选择下拉选项 |
| `browser_snapshot` | 获取页面快照（可访问性树） |
| `browser_tabs` | 管理浏览器标签页 |
| `browser_take_screenshot` | 截取页面截图 |
| `browser_type` | 输入文本 |

## GitHub 平台工具（35 个）

### Actions（12 个）

| 工具 | 用途 |
|------|------|
| `actions_get` | 获取 Action 详情 |
| `actions_list` | 列出可用 Actions |
| `actions_run_trigger` | 触发 Action 运行 |
| `get_job_logs` | 获取作业日志 |
| `get_workflow` | 获取工作流详情 |
| `get_workflow_run` | 获取工作流运行详情 |
| `get_workflow_logs` | 获取工作流日志 |
| `list_workflow_jobs` | 列出工作流作业 |
| `list_workflow_run_artifacts` | 列出工作流运行产物 |
| `list_workflow_runs` | 列出工作流运行 |
| `list_workflows` | 列出仓库工作流 |
| `summarize_job_log_failures` | 汇总作业日志失败 |

### Pull Requests（6 个）

| 工具 | 用途 |
|------|------|
| `get_pull_request` | 获取 PR 详情 |
| `get_pull_request_comments` | 获取 PR 评论 |
| `get_pull_request_files` | 获取 PR 文件变更 |
| `get_pull_request_reviews` | 获取 PR 审查 |
| `get_pull_request_status` | 获取 PR 状态 |
| `list_pull_requests` | 列出 PR |

### Issues（3 个）

| 工具 | 用途 |
|------|------|
| `issue_read` | 读取 Issue 详情 |
| `list_issues` | 列出 Issues |
| `search_issues` | 搜索 Issues |

### 代码与仓库（9 个）

| 工具 | 用途 |
|------|------|
| `get_commit` | 获取提交详情 |
| `get_file_contents` | 获取文件内容 |
| `list_branches` | 列出分支 |
| `list_commits` | 列出提交 |
| `list_tags` | 列出标签 |
| `get_tag` | 获取标签详情 |
| `search_code` | 搜索代码 |
| `search_repositories` | 搜索仓库 |
| `search_users` | 搜索用户 |

### 安全（4 个）

| 工具 | 用途 |
|------|------|
| `get_code_scanning_alert` | 获取代码扫描告警 |
| `list_code_scanning_alerts` | 列出代码扫描告警 |
| `get_secret_scanning_alert` | 获取密钥扫描告警 |
| `list_secret_scanning_alerts` | 列出密钥扫描告警 |

## 内置代理（3 个 YAML 定义）

内置代理定义位于安装目录的 `definitions/` 下，以 `.agent.yaml` 格式定义。

### code-review

- **模型：** claude-sonnet-4.5
- **工具：** 全部（`*`）
- **用途：** 审查代码变更，仅报告真正重要的问题（Bug、安全漏洞、逻辑错误），不评论风格或格式
- **触发：** `/review` 命令

### explore

- **模型：** claude-haiku-4.5
- **工具：** grep、glob、view、lsp
- **用途：** 快速代码库探索和问题回答，300 字以内的简洁响应，可并行调用
- **触发：** `/agent explore`

### task

- **模型：** claude-haiku-4.5
- **工具：** 全部（`*`）
- **用途：** 执行测试、构建、lint 等开发命令，成功时返回简要摘要，失败时返回完整输出
- **触发：** `/agent task`

## 模型（14 个）

| 模型 | Premium 倍率 | 说明 |
|------|-------------|------|
| claude-sonnet-4.5 | 1x | 默认模型 |
| claude-haiku-4.5 | 0.33x | 轻量快速 |
| claude-opus-4.5 | 3x | 高性能 |
| claude-sonnet-4 | 1x | |
| gemini-3-pro-preview | 1x | Google Gemini |
| gpt-5.2-codex | 1x | |
| gpt-5.2 | 1x | |
| gpt-5.1-codex-max | 1x | |
| gpt-5.1-codex | 1x | |
| gpt-5.1 | 1x | |
| gpt-5 | 1x | |
| gpt-5.1-codex-mini | 0.33x | 轻量 |
| gpt-5-mini | 0x | 免费 |
| gpt-4.1 | 0x | 免费 |

通过 `/model` 命令或 `COPILOT_MODEL` 环境变量切换模型。

## 自定义指令

Copilot CLI 按以下顺序搜索自定义指令文件：

| 文件路径 | 作用域 |
|----------|--------|
| `CLAUDE.md` | 项目级（兼容 Claude Code 格式） |
| `GEMINI.md` | 项目级（兼容 Gemini CLI 格式） |
| `AGENTS.md` | 项目级 |
| `.github/instructions/**/*.instructions.md` | 仓库级指令 |
| `.github/copilot-instructions.md` | 仓库级 Copilot 专用指令 |
| `~/.copilot/copilot-instructions.md` | 用户级全局指令 |

### 自定义代理

- `.github/*.agent.md` -- 仓库级自定义代理
- `.claude/agents/*.agent.md` -- 兼容 Claude Code 代理格式

需启用 `CUSTOM_AGENTS` 功能标志。

## 权限系统

### 执行模式

| 模式 | 说明 |
|------|------|
| suggest（默认） | 每次工具调用需用户确认 |
| yolo / allow-all | 允许所有工具执行，跳过确认（`/allow-all` 或 `/yolo`） |
| AUTOPILOT_MODE | 实验性，代理持续工作直到任务完成（`Shift+Tab` 切换） |

### 文件访问控制

- 支持按目录（per-directory）文件访问控制
- `/add-dir` 添加允许访问的目录
- `/list-dirs` 查看已添加目录

### 工具权限

- 工具允许列表（allowlist）机制
- `/reset-allowed-tools` 重置已授权的工具列表
- `/skills` 查看当前可用工具

## 功能标志

通过 `/experimental` 命令启用或查看：

| 标志 | 说明 |
|------|------|
| `CUSTOM_AGENTS` | 自定义代理支持 |
| `CCA_DELEGATE` | 委派子代理功能 |
| `CONTINUITY` | 会话持续性 |
| `PLAN_COMMAND` | `/plan` 命令 |
| `PLUGIN_COMMAND` | `/plugin` 命令 |
| `LSP_TOOLS` | LSP 工具集成 |
| `AUTOPILOT_MODE` | 自动驾驶模式（实验性） |

## 环境变量

| 变量 | 用途 |
|------|------|
| `COPILOT_MODEL` | 指定默认模型 |
| `COPILOT_AGENT_MODEL` | 指定子代理模型 |
| `COPILOT_MCP_JSON` | MCP 服务器配置 JSON 路径 |
| `COPILOT_FIREWALL_ENABLED` | 启用防火墙 |
| `COPILOT_ENABLE_ALT_PROVIDERS` | 启用第三方模型提供商 |
| `GH_TOKEN` / `GITHUB_TOKEN` | GitHub PAT 认证 |

## LSP 配置

支持用户级（`~/.copilot/lsp-config.json`）和仓库级（`.github/lsp.json`）配置：

```json
{
  "lspServers": {
    "typescript": {
      "command": "typescript-language-server",
      "args": ["--stdio"],
      "fileExtensions": {
        ".ts": "typescript",
        ".tsx": "typescript"
      }
    }
  }
}
```

## MCP 配置

通过 `/mcp` 命令或 `COPILOT_MCP_JSON` 环境变量配置 MCP 服务器，支持 stdio 和 SSE 传输。

## 技术架构（npm 源码分析）

> 以下基于 v0.0.403（`@github/copilot`）npm 包源码分析。

### 运行时

| 项目 | 详情 |
|------|------|
| **包结构** | `npm-loader.js` → 尝试原生二进制 → 回退到 `index.js`（Node.js v24+） |
| **JS Bundle** | `index.js`（15MB）+ `sdk/index.js`（11MB），minified 单文件 |
| **原生二进制** | `@github/copilot-{platform}-{arch}` 平台包（优先使用） |
| **UI 框架** | **Ink（React for CLI）**+ Yoga 布局（index.js 中 211 处引用） |
| **原生模块** | `keytar.node`（凭据/钥匙串访问）、`pty.node`（伪终端） |

### 双模式加载器

```javascript
// npm-loader.js 简化流程
try {
  const binary = require(`@github/copilot-${platform}-${arch}/copilot`);
  spawnSync(binary, args);  // 优先使用原生二进制
} catch {
  require('./index.js');     // 回退到 Node.js
}
```

### 代理系统（YAML 定义）

三个内置代理在 `definitions/` 目录中以 YAML 定义：

**code-review.agent.yaml**（代码审查专用）：
- 模型：`claude-sonnet-4.5`，工具：`*`（全部）
- 只报告 Bug、安全问题、逻辑错误（高信噪比）
- **明确禁止修改代码**
- 输出带严重级别的结构化问题报告

**explore.agent.yaml**（快速探索）：
- 模型：`claude-haiku-4.5`，工具：仅 `grep, glob, view, lsp`（只读）
- 回答控制在 300 字以内
- 强调并行工具调用以提速

**task.agent.yaml**（命令执行）：
- 模型：`claude-haiku-4.5`，工具：`*`（全部）
- 运行测试、构建、lint、格式化
- 成功时简短输出，失败时完整输出

### API 层

- `api.github.com` — 标准 GitHub API
- `api.githubcopilot.com` — Copilot 专用 API
- `api.githubcopilot.com/mcp/readonly` — MCP 只读端点

### 安全机制

- SDK 模块加载限制：`require()` 解析到应用目录外时抛出安全错误
- `keytar.node` 使用系统钥匙串存储凭据（macOS Keychain、Linux Secret Service）
- 工具协议：原生工具 + MCP（Model Context Protocol）
- 浏览器自动化：基于 Playwright
- 搜索引擎：内置 ripgrep
- 代理定义：YAML 格式（`.agent.yaml`）

## 优势

1. **完整代理能力**：12 个核心工具 + 21 个浏览器工具 + 48 个 GitHub 工具
2. **GitHub 生态深度集成**：Actions、PR、Issues、代码扫描、密钥扫描原生联动
3. **多模型选择**：14 个模型，涵盖 Claude、GPT、Gemini 系列
4. **内置代理系统**：code-review、explore、task 三个专用代理
5. **浏览器自动化**：基于 Playwright 的完整浏览器控制能力
6. **MCP + LSP 可扩展**：支持自定义 MCP 服务器和语言服务器
7. **多格式指令兼容**：同时读取 CLAUDE.md、GEMINI.md、AGENTS.md
8. **企业支持**：SSO、审计日志、合规、安全扫描集成
9. **免费模型可用**：gpt-5-mini 和 gpt-4.1 为 0x 免费模型

## 劣势

1. **需要 Copilot 订阅**：依赖付费的 GitHub Copilot 订阅（免费模型除外）
2. **消耗 premium requests 配额**：高倍率模型（如 claude-opus-4.5 为 3x）消耗较快
3. **需要 GitHub 账户**：依赖 GitHub 认证
4. **部分功能需功能标志**：CUSTOM_AGENTS、PLAN_COMMAND 等需手动启用
5. **较新产品**：仍在快速迭代中，实验性功能较多

## 使用场景

- **最适合**：GitHub 重度用户、企业团队、需要 GitHub Actions/PR/Issues 集成的开发工作流
- **适合**：日常编码、调试、代码审查、浏览器测试自动化、代码库探索
- **不太适合**：非 GitHub 用户、无 Copilot 订阅的用户

## 定价

- 包含在 GitHub Copilot 订阅中（每次提交消耗 premium request 配额，倍率因模型而异）
- gpt-5-mini 和 gpt-4.1 为免费模型（0x 倍率）
- 详见 [Copilot 计划](https://github.com/features/copilot/plans)

## 资源链接

- [GitHub 仓库](https://github.com/github/copilot-cli)
- [官方文档](https://docs.github.com/copilot/concepts/agents/about-copilot-cli)
- [Premium Requests 说明](https://docs.github.com/copilot/managing-copilot/monitoring-usage-and-entitlements/about-premium-requests)
