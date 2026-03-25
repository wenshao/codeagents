# 1. Qoder CLI 概述

**开发者：** QoderAI（阿里巴巴通义灵码团队）
**许可证：** 专有（商业条款 qoder.com/product-service）
**官网：** [qoder.com/cli](https://qoder.com/cli)
**文档：** [docs.qoder.com](https://docs.qoder.com/cli/using-cli)
**npm 包：** `@qoder-ai/qodercli` v0.1.35
**最后更新：** 2026-03

## 概述

Qoder CLI 是阿里巴巴通义灵码团队推出的**闭源**终端 AI 编程代理。与同公司的 Qwen Code（开源，Gemini CLI 分叉）不同，Qoder CLI 是独立的商业产品，使用 **Go 语言**编写，以原生 43MB 静态链接二进制分发。

核心特色：
- **Quest 模式**：规格驱动自主执行——先生成 Spec 文档，用户确认后执行，支持本地/Worktree/远程三种环境
- **Go 原生二进制**：43MB，静态链接，启动声称 <70ms，内存比同类工具低 70%
- **Claude Code 兼容**：`--with-claude-config` 读取 .claude 目录的 skills、commands、subagents
- **8+ 模型支持**：Claude、GPT、Gemini、GLM-5、Kimi-K2.5、Minimax-M2.5、DeepSeek，自动选择
- **Experts 模式**（v0.5.1+）：自动组建 AI 专家团队并行工作
- **ACP 协议**：编辑器集成（Zed、VS Code、JetBrains）

## 技术架构（二进制分析 v0.1.35）

| 项目 | 详情 |
|------|------|
| **二进制** | ELF 64-bit LSB executable, x86-64, 静态链接, stripped |
| **大小** | 43 MB |
| **语言** | **Go**（runtime.go 确认，cobra CLI 框架） |
| **TUI** | Bubbletea + Lipgloss + Glamour（Charm 生态） |
| **LLM SDK** | openai-go (11,464 refs) + anthropic-sdk-go (3,901 refs) |
| **MCP SDK** | mcp-go (744 refs) |
| **内部包路径** | `code.alibaba-inc.com/qoder-core/qodercli/` |
| **分发** | npm `@qoder-ai/qodercli`（Shell 启动脚本 + Go 二进制） |
| **平台** | macOS (arm64/amd64)、Linux (arm64/amd64)、Windows |

## CLI 子命令（9 个，`qodercli --help` 确认）

| 命令 | 用途 |
|------|------|
| `jobs` | 列出并发 worktree 任务 |
| `rm` | 删除并发任务 |
| `commit` | 提交 AI 生成的代码，记录 AI 贡献统计 |
| `completion` | 生成 Shell 自动补全脚本 |
| `feedback` | 提交反馈（支持附加图片） |
| `install` | 安装到标准位置 |
| `mcp` | MCP 服务器管理（add/remove/list/get/auth） |
| `status` | 显示账户和 CLI 状态 |
| `update` | 自更新到最新版本 |

## CLI 参数（24 个，`--help` 确认）

| 参数 | 说明 |
|------|------|
| `-p, --print` | 非交互模式（管道/脚本/CI） |
| `-c, --continue` | 继续最近会话 |
| `-r, --resume <id>` | 恢复指定会话 |
| `-w, --workspace` | 指定工作目录 |
| `-f, --output-format` | 输出格式（text/json/stream-json） |
| `--input-format` | 输入格式（text/stream-json） |
| `--model` | 模型级别（auto/efficient/lite/performance/ultimate 等 10 种） |
| `--max-turns` | 最大代理循环次数（仅 --print 模式） |
| `--max-output-tokens` | 最大输出 token（16k/32k） |
| `--agents` | 自定义代理 JSON 定义 |
| `--allowed-tools` | 允许的工具白名单 |
| `--disallowed-tools` | 禁止的工具黑名单 |
| `--attachment` | 附加文件（图片等，可多次指定） |
| `--worktree` | 通过 Git worktree 启动并发任务 |
| `--branch` | worktree 分支名 |
| `--path` | worktree 路径 |
| `--yolo` | 绕过所有权限检查 |
| `--dangerously-skip-permissions` | 同 --yolo |
| `--with-claude-config` | **加载 Claude Code 配置**（.claude 目录、skills、commands、subagents） |
| `--summarize-tool` | 自动摘要超过 200 行/15KB 的工具输出 |
| `--experimental-mcp-load` | 实验性 MCP 动态工具发现 |
| `-q, --quiet` | 静默模式（隐藏 spinner） |
| `-v, --version` | 版本号 |
| `-h, --help` | 帮助 |

## 5 种输入模式

| 前缀 | 模式 | 说明 |
|------|------|------|
| `>` | Dialog | 默认聊天模式 |
| `!` | Bash | 直接执行 Shell 命令 |
| `/` | Slash | 斜杠命令 |
| `#` | Memory | 追加内容到 AGENTS.md |
| `\` + Enter | Multiline | 多行输入 |

## 斜杠命令（19 个，二进制 + 官方文档交叉验证）

| 命令 | 用途 | 验证来源 |
|------|------|---------|
| `/quest` | 启动 Quest 模式（规格驱动自主执行） | 二进制 + 官方文档 |
| `/review` | 代码审查（本地变更） | 二进制 + 官方文档 |
| `/review-code` | 代码审查（文件级） | 二进制 |
| `/review-pr` | PR 审查（仓库+PR 号） | 二进制 + GitHub Action |
| `/init` | 创建 AGENTS.md 项目指令文件 | 二进制 + 官方文档 |
| `/compact` | 压缩/摘要会话上下文 | 二进制 + 官方文档 |
| `/clear` | 清除会话上下文 | 二进制 + 官方文档 |
| `/resume` | 列出并恢复历史会话 | 二进制 + 官方文档 |
| `/login` | 账户登录 | 二进制 + 官方文档 |
| `/logout` | 账户登出 | 官方文档 |
| `/model` | 切换模型级别 | 二进制 |
| `/usage` | 显示账户用量/信用信息 | 官方文档 |
| `/status` | 显示系统状态 | 二进制 + 官方文档 |
| `/config` | 显示系统配置 | 二进制 + 官方文档 |
| `/agents` | 子代理管理（列出/创建） | 二进制 + 官方文档 |
| `/bashes` | 列出后台 Bash 任务 | 二进制 + 官方文档 |
| `/memory` | 选择并编辑 AGENTS.md | 二进制 + 官方文档 |
| `/vim` | 打开外部编辑器 | 二进制 + 官方文档 |
| `/feedback` | 提交用户反馈 | 二进制 + 官方文档 |
| `/quit` | 退出 | 二进制 + 官方文档 |
| `/vercel-deploy` | Vercel 部署自动化（v0.5.1+） | 官方文档 |

## 内置工具（4 个）

| Agent | 用途 |
|------|------|
| **Grep** | 搜索文件内容 |
| **Read** | 读取文件 |
| **Write** | 写入/编辑文件 |
| **Bash** | 执行 Shell 命令 |

## Quest 模式（核心特色）

Quest 模式是 Qoder CLI 的旗舰功能——设计优先的自主编码工作流。

### 三种场景

| 场景 | 说明 | 适用 |
|------|------|------|
| **Code with Spec** | 先生成结构化 Spec，用户确认后执行 | 复杂功能、团队协作 |
| **Build a Website** | 快速原型，跳过 Spec，自动选择技术栈 | 从零建站 |
| **Prototype Ideas** | 快速概念验证，无文档 | 想法验证 |

### Code with Spec 工作流

```
需求输入 → 多选问答澄清意图 → 生成 Spec 文档
  → 用户审查/调整 Spec → 点击 "Run Spec"
  → 实时执行（TODO 列表追踪进度）
  → 接受结果 / 创建 PR / 重新运行
```

### 三种执行环境

| 环境 | 说明 | 适用 |
|------|------|------|
| **Local** | 直接修改主工作区 | 快速修复，零启动成本 |
| **Worktree** | Git worktree 隔离后台执行 | 保持主分支干净 |
| **Remote** | 远程容器执行 | 长时间任务（数小时），需 GitHub 仓库 |

### 关键能力
- 自动中断恢复（长时间任务）
- 持续学习（记住编码风格和项目模式）
- 三列布局 TUI：任务列表（左）、对话（中）、输出标签页（右）

## 模型支持（8+ 模型，v0.5.1+）

| 模型级别 | 含义 | 对应模型 |
|---------|------|---------|
| `auto` | 自动选择 | 根据任务特征自动路由 |
| `lite` | 轻量 | 基础模型 |
| `efficient` | 高效 | 平衡成本和能力 |
| `performance` | 高性能 | 强推理模型 |
| `ultimate` | 旗舰 | 最强模型 |
| `gmodel` | G 模型 | GPT 系列 |
| `kmodel` | K 模型 | Kimi-K2.5 |
| `qmodel` | Q 模型 | Qwen 系列 |
| `q35model` | Q3.5 模型 | Qwen 3.5 |
| `mmodel` | M 模型 | Minimax-M2.5 |

支持的底层模型：Claude、GPT、Gemini、GLM-5（智谱）、Kimi-K2.5、Minimax-M2.5、DeepSeek。

## 权限系统

### 三层策略

| 策略 | 说明 |
|------|------|
| **Allow** | 允许工具执行 |
| **Deny** | 阻止工具执行 |
| **Ask** | 提示用户确认 |

### 配置文件（优先级从低到高）

| 文件 | 范围 | 提交到 Git |
|------|------|-----------|
| `~/.qoder/settings.json` | 用户级 | — |
| `${project}/.qoder/settings.json` | 项目级 | ✓ |
| `${project}/.qoder/settings.local.json` | 本地覆盖 | ✗（gitignore） |

### 权限模式

| 模式 | 说明 |
|------|------|
| **Read & Edit** | gitignore 风格文件路径匹配 |
| **WebFetch** | 域名限制（如 `WebFetch(domain:example.com)`） |
| **Bash** | 命令匹配（如 `Bash(npm run build)`、`Bash(npm run test:*)`） |
| **YOLO** | `--yolo` 跳过所有检查 |

## 记忆系统（AGENTS.md）

| 位置 | 范围 | 说明 |
|------|------|------|
| `~/.qoder/AGENTS.md` | 用户级 | 适用所有项目 |
| `${project}/AGENTS.md` | 项目级 | 项目特定指导 |

- `/init` 自动生成项目级 AGENTS.md
- `#` 前缀模式直接追加内容到 AGENTS.md
- `/memory` 命令选择并编辑
- 跨会话持久化，自动加载到上下文

## MCP 集成

```bash
# 添加 MCP 服务器
qodercli mcp add playwright -- npx -y @playwright/mcp@latest

# 选项
# -t: 传输类型 (stdio/sse/streamable-http)
# -s: 范围 (user/project)
```

配置文件：
- 用户级：`~/.qoder.json`
- 项目级：`${project}/.mcp.json`

## 子代理系统

- 每个子代理有**独立上下文窗口**和**自定义工具权限**
- 通过 Markdown 文件 + Frontmatter 定义（name、description、tools）
- v0.5.1+ 支持 Skills 配置
- `/agents` 命令管理
- 手动创建或交互式创建

## 自定义命令

- `.md` 文件存储在 `~/.qoder/commands/`（用户级）或 `${project}/.qoder/commands/`（项目级）
- 通过 `/` 前缀触发
- 支持调用多个子代理的复杂工作流

## Hooks 系统

- 当前仅支持 **Notification hooks**
- 定义在 `.qoder/settings.json`
- Hook 命令接收 JSON 输入（session ID、消息、工作区路径）
- 更多 Hook 类型计划中（工具调用、会话干预）

## 定价（信用制）

| 计划 | 促销价 | 原价 | 月信用 | 关键功能 |
|------|--------|------|--------|---------|
| **Free** | $0 | $0 | 有限 | 2 周 Pro 试用，基础模型，有限聊天 |
| **Pro** | $10/月 | $20/月 | 2,000 | Quest 模式、Repo Wiki、无限补全 |
| **Pro+** | $30/月 | $60/月 | 6,000 | 同 Pro + 更多信用 |
| **Ultra** | $100/月 | $200/月 | 20,000 | 同 Pro + 最多信用 |

- 附加信用包：$0.01/信用（促销），最少 1,000 个，1 个月有效期
- 信用耗尽后回退到基础模型（每日有限额度）

## .qoder 目录结构

```
${project}/.qoder/
├── settings.json          # 项目级权限 & Hooks
├── settings.local.json    # 本地覆盖（gitignore）
├── commands/              # 自定义命令 .md 文件
├── skills/                # 可安装技能
└── quest/                 # Quest 模式输出（Spec、任务报告）
```

```
~/.qoder/
├── settings.json          # 用户级权限
├── AGENTS.md              # 用户级记忆
├── commands/              # 用户级自定义命令
```

## 与 Qwen Code 的区别

| 维度 | Qoder CLI | Qwen Code |
|------|-----------|-----------|
| **开源** | ✗（闭源） | ✓（Apache-2.0） |
| **语言** | Go | TypeScript |
| **来源** | 独立开发 | Gemini CLI 分叉 |
| **定价** | 信用制（Free 有限 → Pro $10） | 免费 OAuth 1000 次/天 |
| **模型** | 多级别抽象 + 自动路由 | 直接选择模型名 |
| **Quest 模式** | ✓（3 场景 × 3 环境） | ✗ |
| **Claude 兼容** | `--with-claude-config` 读取 .claude | Claude 插件转换器 |
| **Arena 模式** | ✗ | ✓（多模型竞争） |
| **指令文件** | AGENTS.md | QWEN.md（兼容 GEMINI.md） |
| **ACP/IDE** | ✓（Zed/VS Code/JetBrains） | ✓（VS Code/Zed） |

## 优势

1. **Quest 模式**：唯一支持 Spec→确认→执行→PR 完整工作流的工具
2. **Go 原生性能**：43MB 二进制，启动 <70ms，低内存
3. **Claude Code 兼容**：`--with-claude-config` 直接复用 Claude Code 配置
4. **8+ 模型自动路由**：根据任务特征自动选择最佳模型
5. **AI 贡献统计**：`commit` 子命令记录 AI 代码占比
6. **Experts 模式**：自动组建专家团队并行工作
7. **三种执行环境**：本地/Worktree/远程容器

## 劣势

1. **闭源**：无法审计内部实现
2. **低社区采用**：GitHub 仅 28 stars（qoder-action）
3. **与 Qwen Code 定位重叠**：同公司两个类似产品
4. **信用制**：免费层有限（Qwen Code 1000/天更慷慨）
5. **Hooks 不完整**：仅 Notification hooks（其他类型计划中）
6. **文档 404**：部分文档页面不可访问

## 资源链接

- [官网](https://qoder.com/cli)
- [文档](https://docs.qoder.com/cli/using-cli)
- [Quest 模式文档](https://docs.qoder.com/user-guide/quest-mode)
- [定价](https://docs.qoder.com/account/pricing)
- [GitHub Action](https://github.com/QoderAI/qoder-action)
- [npm 包](https://www.npmjs.com/package/@qoder-ai/qodercli)
- [社区论坛](https://forum.qoder.com)
- [Qoder MCP](https://github.com/qoder-official/qoder-mcp)

## 证据来源

| 来源 | 方式 |
|------|------|
| 二进制分析 | `strings qodercli`（43MB Go ELF static） |
| CLI --help | `qodercli --help` 完整输出 |
| MCP --help | `qodercli mcp --help` 输出 |
| status | `qodercli status` 输出 |
| 官方文档 | docs.qoder.com/cli/using-cli |
| Quest 模式 | docs.qoder.com/user-guide/quest-mode |
| v0.5.1 更新 | forum.qoder.com 发布日志 |
| npm | npmjs.com/package/@qoder-ai/qodercli |
| 定价 | docs.qoder.com/account/pricing |
