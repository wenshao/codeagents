# AGENTS.md — 项目指令文件

> 本文件为所有 AI 编程代理提供项目级上下文。支持 Claude Code（通过符号链接）、Codex CLI、Kimi CLI、Copilot CLI、Qwen Code、OpenCode。

## 项目概述

这是一个中文技术文档项目，对比分析 17 款 AI 编程 Code Agent。所有分析基于源码验证，
确保技术声明的准确性。项目目标是为开发者提供中立、客观、可验证的 Agent 选型参考。

## 项目结构（118 文件，35,000+ 行）

```
docs/
├── tools/                      # Agent 文档（10 目录 + 9 单文件）
│   ├── claude-code/            # 9 文件 + EVIDENCE.md（反编译分析）
│   ├── copilot-cli/            # 5 文件 + EVIDENCE.md（SEA 反编译）
│   ├── codex-cli/              # 5 文件 + EVIDENCE.md（Rust 二进制分析）
│   ├── gemini-cli/             # 7 文件 + EVIDENCE.md（源码分析）
│   ├── kimi-cli/               # 5 文件 + EVIDENCE.md
│   ├── aider/                  # 5 文件 + EVIDENCE.md
│   ├── opencode/               # 5 文件 + EVIDENCE.md
│   ├── qwen-code/              # EVIDENCE.md（Gemini CLI 分叉分析）
│   ├── qoder-cli/              # 4 文件 + EVIDENCE.md（Go 二进制分析）
│   ├── goose/                  # EVIDENCE.md（MCP 原生架构分析）
│   └── *.md                    # 9 个单文件 Agent（Cursor/Warp/Cline 等）
├── comparison/                 # 对比文档（40 篇）
│   ├── features.md             # 功能矩阵
│   ├── architecture-deep-dive.md  # 架构深度对比
│   ├── slash-commands-deep-dive.md  # 命令深度对比
│   ├── model-routing.md        # 模型路由
│   ├── *-deep-dive.md          # 15 篇系统能力 Deep-Dive
│   ├── review-command.md       # /review 对比
│   ├── privacy-telemetry.md    # 隐私/遥测/安全监控对比
│   ├── pricing.md              # 定价/成本
│   ├── system-requirements.md  # 系统要求
│   ├── claude-code-vs-*.md     # 1v1 对比
│   └── qwen-code-*.md          # Qwen 功能补全系列
├── guides/                     # 使用指南（15 篇）
│   ├── getting-started.md
│   ├── workflows.md
│   ├── migration.md
│   ├── troubleshooting.md
│   ├── config-examples.md
│   ├── context-management.md
│   ├── skill-design.md
│   ├── agents-md.md
│   ├── hooks-config.md
│   ├── claude-code-user-guide.md
│   ├── qwen-code-user-guide.md
│   ├── copilot-cli-user-guide.md
│   ├── writing-claude-md.md
│   ├── security-hardening.md
│   └── effective-prompts.md
├── architecture/
├── benchmarks/
└── resources.md
```

## 写作规范

### 语言
- 正文使用中文
- 技术术语保留英文原文（如 CLI、API、token、context window）
- Agent 名称保留英文（如 Claude Code、Cursor、Copilot）

### 风格
- 技术文档风格，中立客观
- 避免营销用语（如"最强"、"革命性"、"碾压"）
- 使用准确的量化描述替代模糊表述

### 数据与来源
- 所有技术声明需标注来源：源码分析、官方文档、或注明为估算
- 估算数据使用 `~` 标记（如 `~200k tokens`）
- 不要编造基准测试数据
- 源码引用格式：`源码: path/to/file.ts#L123`

### 格式
- 大量使用 Markdown 表格进行功能对比
- 使用代码块展示配置示例，标注语言类型
- 用 `> blockquote` 标注免责声明和重要说明

### 示例

```markdown
| 功能 | Agent A | Agent B |
|------|--------|--------|
| 上下文窗口 | 200k tokens | ~128k tokens |

> **免责声明**: 以上数据基于 2026 年 Q1 源码分析，可能已过时。
```

## 注意事项

- 更新文档时，同步检查以下文件中的相关引用：
  - `README.md` 中的 Agent 表格和导航链接
  - `docs/tools/README.md` Agent 索引
  - `docs/comparison/features.md` 功能对比数据（命令数、内置工具数等数字）
  - `docs/comparison/privacy-telemetry.md` 隐私/遥测数据
  - `docs/comparison/pricing.md` 定价信息
  - `docs/comparison/system-requirements.md` 系统要求
  - `docs/guides/getting-started.md` 入门信息
- 闭源 Agent 的声明必须有 EVIDENCE.md 证据支撑（二进制分析或官方文档 URL）
- 开源 Agent 的声明需标注源码文件路径（如 `源码: aider/commands.py`）
- 不要编造基准测试数据，无法验证的数据标注 `~` 表示估算
- 保持各 Agent 文档深度均衡，避免某些 Agent 过于详细而其他过于简略
- 新增文档后务必更新 `README.md` 导航目录

## 常用命令

### 检查过时引用

```bash
# 查找可能过时的版本号引用
grep -r "v[0-9]\+\.[0-9]\+\.[0-9]\+" docs/

# 查找包含具体日期的声明（可能需要更新）
grep -rn "202[0-9]" docs/

# 检查断裂的内部链接引用
grep -rn "\](\./" docs/ | grep -v "node_modules"
```

### 验证链接

```bash
# 检查 Markdown 文件中的链接格式
grep -rn "\[.*\](.*)" docs/ --include="*.md"

# 查找空链接
grep -rn "\[.*\]()" docs/
```
