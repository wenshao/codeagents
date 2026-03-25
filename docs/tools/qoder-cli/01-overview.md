# 1. Qoder CLI 概述

**开发者：** QoderAI（阿里巴巴通义灵码团队）
**许可证：** 专有（商业条款 qoder.com/product-service）
**官网：** [qoder.com/cli](https://qoder.com/cli)
**npm 包：** `@qoder-ai/qodercli`
**最后更新：** 2026-03

## 概述

Qoder CLI 是阿里巴巴通义灵码团队推出的**闭源**终端 AI 编程代理。与同公司的 Qwen Code（开源，Gemini CLI 分叉）不同，Qoder CLI 是独立的商业产品，使用 Go 语言编写，以原生二进制分发。支持信用制定价，内置 Quest 模式（规格驱动自主执行）。

主要特点：
- **Go 原生二进制**：43MB，静态链接，启动声称 <70ms
- **信用制定价**：Free 300/月，Pro $10 2000/月，Ultra $100 20000/月
- **Quest 模式**：规格驱动自主任务执行
- **Claude Code 兼容**：`--with-claude-config` 读取 .claude 目录配置
- **AGENTS.md 支持**：项目级指令文件
- **MCP 集成**：支持 MCP 服务器扩展
- **Worktree 并行**：Git worktree 隔离并行任务

## 技术架构（二进制分析 v0.1.35）

| 项目 | 详情 |
|------|------|
| **二进制** | ELF 64-bit LSB executable, x86-64, 静态链接, stripped |
| **大小** | 43 MB |
| **语言** | **Go**（从 runtime.go 确认） |
| **内部包路径** | `code.alibaba-inc.com/qoder-core/qodercli/` |
| **分发** | npm `@qoder-ai/qodercli`（Shell 启动脚本 + Go 二进制） |

## CLI 命令

### 子命令（9 个，`qodercli --help` 确认）

| 命令 | 用途 |
|------|------|
| `jobs` | 列出并发 worktree 任务 |
| `rm` | 删除并发任务 |
| `commit` | 提交 AI 生成的代码，记录 AI 贡献统计 |
| `completion` | 生成 Shell 自动补全脚本 |
| `feedback` | 提交反馈（支持附加图片） |
| `mcp` | MCP 服务器管理（add/remove/list/get/auth） |
| `status` | 显示账户和 CLI 状态 |
| `update` | 自更新到最新版本 |
| `install` | 安装到标准位置 |

### CLI 参数（`--help` 提取，24 个）

| 参数 | 说明 |
|------|------|
| `-p, --print` | 非交互模式（管道/脚本） |
| `-c, --continue` | 继续最近会话 |
| `-r, --resume <id>` | 恢复指定会话 |
| `-w, --workspace` | 指定工作目录 |
| `-f, --output-format` | 输出格式（text/json/stream-json） |
| `--input-format` | 输入格式（text/stream-json） |
| `--model` | 模型级别（auto/efficient/lite/performance/ultimate 等） |
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
| `-q, --quiet` | 静默模式 |
| `-v, --version` | 版本号 |
| `-h, --help` | 帮助 |

## 斜杠命令（二进制 strings 提取）

从二进制中提取到的命令注册：

| 命令 | 来源 |
|------|------|
| `/quest` | 二进制 strings |
| `/review-code` | 二进制 strings |
| `/review-pr` | 二进制 strings |
| `/commit` | 二进制 strings + CLI 子命令 |
| `/compact` | 二进制 strings |
| `/clear` | 二进制 strings |
| `/login` | 二进制 strings + CLI 子命令 |
| `/model` | 二进制 strings |
| `/feedback` | 二进制 strings + CLI 子命令 |
| `/help` | 二进制 strings |
| `/vim` | 二进制 strings |
| `/review` | 二进制 strings |
| `/agents` | 二进制 strings |
| `/bashes` | 二进制 strings |
| `/quit` / `/exit` | 二进制 strings |
| `/status` | 二进制 strings |
| `/memory` | 二进制 strings（AGENTS.md） |
| `/init` | 二进制 strings |
| `/config` | 二进制 strings |

> 注：Go 编译的二进制中命令以字符串片段存储，部分可能遗漏。

## 模型级别

| 模型 | 含义 | 推测 |
|------|------|------|
| `auto` | 自动选择 | 默认 |
| `lite` | 轻量 | 低成本 |
| `efficient` | 高效 | 平衡 |
| `performance` | 高性能 | 强推理 |
| `ultimate` | 旗舰 | 最强模型 |
| `gmodel` | G 模型 | 可能是 GPT 系列 |
| `kmodel` | K 模型 | 可能是 Kimi/K2 |
| `qmodel` | Q 模型 | 可能是 Qwen 系列 |
| `q35model` | Q3.5 模型 | Qwen 3.5 |
| `mmodel` | M 模型 | 未知 |

## 定价（信用制）

| 计划 | 月费 | 月信用 | 信用单价 |
|------|------|--------|---------|
| Free | $0 | 300 | — |
| Pro | $10（50% off） | 2,000 | $0.005 |
| Pro+ | $30（50% off） | 6,000 | $0.005 |
| Ultra | $100（50% off） | 20,000 | $0.005 |
| 附加信用 | — | 按需 | $0.01/信用 |

## Claude Code 兼容模式

```bash
qodercli --with-claude-config
```

此参数启用后，Qoder CLI 会读取：
- `.claude/` 目录配置
- Claude Code Skills
- Claude Code Commands
- Claude Code Subagents

这意味着已有 Claude Code 配置的项目可以无缝使用 Qoder CLI。

## 与 Qwen Code 的区别

| 维度 | Qoder CLI | Qwen Code |
|------|-----------|-----------|
| **开源** | ✗（闭源） | ✓（Apache-2.0） |
| **语言** | Go | TypeScript |
| **来源** | 独立开发 | Gemini CLI 分叉 |
| **定价** | 信用制（Free 300/月） | 免费 OAuth 1000 次/天 |
| **模型** | 多级别抽象（auto/lite/ultimate） | 直接选择模型名 |
| **Claude 兼容** | `--with-claude-config` | Claude 插件转换器 |
| **特色** | Quest 模式、commit AI 统计 | Arena 模式、7 语言 UI |

## 优势

1. **Go 原生性能**：43MB 二进制，启动 <70ms
2. **Claude Code 兼容**：直接读取 .claude 配置
3. **Quest 模式**：规格驱动自主执行
4. **Worktree 并行**：Git worktree 隔离并发任务
5. **AI 贡献统计**：`commit` 子命令记录 AI 代码占比

## 劣势

1. **闭源**：无法审计内部实现
2. **低社区采用**：GitHub 仅 28 stars（qoder-action）
3. **与 Qwen Code 定位重叠**：同公司两个类似产品
4. **信用制**：免费层仅 300/月（Qwen Code 1000/天）
5. **文档有限**：相比 Claude Code/Copilot CLI 文档不够完善

## 证据来源

- 二进制分析：`/usr/local/lib/node_modules/@qoder-ai/qodercli/bin/qodercli`（43MB, Go, ELF 64-bit static）
- `qodercli --help` 完整输出
- `qodercli status` 输出
- `qodercli mcp --help` 输出
- strings 二进制提取斜杠命令
- 内部包路径：`code.alibaba-inc.com/qoder-core/qodercli/`
