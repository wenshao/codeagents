# 2. Goose 命令系统——开发者参考

> Goose 共有 14 个 CLI 命令 + 16 个交互式斜杠命令——远少于 Claude Code 的 ~79 个。但 Goose 通过 Recipe 系统和 Schedule 调度弥补了命令数量的不足，将复杂任务编排从"命令"层面提升到"工作流"层面。
>
> **Qwen Code 对标**：命令架构（clap derive vs 手写注册）、Recipe 可复用任务（Qwen Code 无对标）、Schedule 定时调度（Qwen Code 无对标）、斜杠命令扩展机制

## 为什么命令架构设计值得关注

### 问题定义

CLI Code Agent 的命令系统面临两个设计选择：

| 选择 | Goose 方案 | Claude Code 方案 | 影响 |
|------|-----------|-----------------|------|
| 命令定义方式 | Rust clap derive 宏（编译期校验） | TypeScript 运行时注册 | 错误发现时机 |
| 命令扩展方式 | Recipe + MCP prompt template | Skill + Plugin 系统 | 用户自定义能力 |
| 任务自动化 | Recipe YAML + Cron Schedule | 无原生调度 | 无人值守执行 |

Goose 的命令更少，但每个命令的参数设计更丰富（`run` 命令有 16+ 个参数），且 Recipe 系统让"命令组合"成为一等公民。

### 竞品命令系统对比

| Agent | CLI 命令数 | 斜杠命令数 | 任务模板 | 定时调度 | 命令框架 |
|-------|----------|----------|---------|---------|---------|
| **Goose** | 14 | 16 | Recipe YAML | Cron Schedule | clap (Rust) |
| **Claude Code** | ~10 | ~79 | Skill 文件 | 无 | 内置解析 |
| **Gemini CLI** | ~8 | ~30 | TOML command | 无 | 内置解析 |
| **Qwen Code** | ~10 | ~40 | Skill | 无 | 内置解析 |

---

## CLI 命令（14 个）

源码: `crates/goose-cli/src/cli.rs`（clap derive 宏定义）

### 顶层命令

| 命令 | 别名 | 用途 | Qwen Code 对标 | 源码 |
|------|------|------|---------------|------|
| `goose` | — | 启动交互式会话 | `qwen-code` | `cli.rs` |
| `configure` | — | 配置设置（provider/model/extensions） | `/config` | `commands/configure.rs` |
| `info` | — | 显示系统信息（`--verbose` 详细） | `/status` | `commands/info.rs` |
| `run` | — | 从指令/Recipe/stdin 执行任务 | 无 | — |
| `session` | `s` | 管理会话（list/remove/export/diagnostics） | `/sessions` | `commands/session.rs` |
| `project` | `p` | 打开最近项目 | 无 | `commands/project.rs` |
| `projects` | `ps` | 列出最近项目 | 无 | 同上 |
| `recipe` | — | Recipe 工具（validate/deeplink/open/list） | 无 | `commands/recipe.rs` |
| `schedule` | `sched` | 管理定时任务 | 无 | `commands/schedule.rs` |
| `gateway` | `gw` | 管理外部网关（pair 配对） | 无 | `commands/gateway.rs` |
| `mcp` | — | 运行内置 MCP 服务器 | 无 | — |
| `acp` | — | 以 ACP 代理模式运行（stdio） | 无 | — |
| `update` | — | 更新 CLI 版本（`--canary`） | `/update` | `commands/update.rs` |
| `term` | — | 终端集成会话 | 无 | `commands/term.rs` |
| `local-models` | `lm` | 管理本地推理模型 | 无 | — |
| `completion` | — | 生成 Shell 自动补全 | 无 | — |

**开发者启示**：Goose 用 clap derive 宏定义命令，所有参数在编译期校验——拼写错误、类型不匹配在 `cargo build` 阶段就会报错。相比 TypeScript Agent 在运行时才发现命令参数问题，这降低了回归风险。代价是添加新命令需要重新编译。

### `run` 命令——最复杂的入口

`run` 命令是 Goose 的核心执行入口，支持 16+ 个参数，覆盖输入、扩展、会话、输出、模型、行为六个维度：

| 参数组 | 关键参数 | 用途 |
|--------|---------|------|
| **Input** | `--instructions`/`-i`, `--text`/`-t`, `--recipe`, `--system`, `--params` | 输入来源（文件/文本/Recipe/系统提示/参数） |
| **Extension** | `--with-extension`, `--with-builtin`, `--no-profile` | 动态添加扩展，跳过配置文件 |
| **Session** | `--debug`, `--max-tool-repetitions`, `--max-turns`, `--container` | 调试/安全限制/容器化 |
| **Output** | `--quiet`/`-q`, `--output-format`（text/json/stream-json） | 静默模式、结构化输出 |
| **Model** | `--provider`, `--model` | 覆盖默认 LLM 提供商和模型 |
| **Behavior** | `--interactive`/`-s`, `--no-session`, `--resume` | 交互/无状态/恢复模式 |

**Qwen Code 对标**：`run` 命令的 `--output-format stream-json` 模式对标 Claude Code 的 `--output-format stream-json`，都实现了结构化输出流。但 Goose 的 `--container` 参数（容器化执行）是独有的——它允许在隔离环境中运行 Agent 任务，这对 CI/CD 集成非常有价值。

### Session 子命令

| 子命令 | 用途 | 独特之处 |
|--------|------|---------|
| `list` | 列出会话 | 支持 `--working_dir` 按目录过滤、`--format` 结构化输出 |
| `remove` | 删除会话 | 支持 `--regex` 正则匹配批量删除 |
| `export` | 导出会话 | 支持 markdown/json/yaml 三种格式 |
| `diagnostics` | 生成诊断 zip | 打包日志/配置/环境信息 |

### Recipe 子命令

| 子命令 | 用途 |
|--------|------|
| `validate` | 验证 Recipe YAML 结构 |
| `deeplink` | 生成 `goose://` deeplink URL |
| `open` | 在 Goose Desktop 打开 Recipe |
| `list` | 列出本地可用 Recipe |

### Schedule 子命令

| 子命令 | 用途 |
|--------|------|
| `add` | 添加 Cron 定时任务 |
| `list` | 列出所有定时任务 |
| `remove` | 删除定时任务 |
| `sessions` | 查看定时任务的执行历史 |
| `run_now` | 立即执行指定任务 |
| `services_status` | 查看调度服务状态 |
| `services_stop` | 停止调度服务 |
| `cron_help` | Cron 表达式帮助 |

**Qwen Code 对标**：Schedule 系统是 Goose 的差异化功能之一。Claude Code 通过 Kairos（Always-On）实现持续自治，但需要 Anthropic 基础设施支持。Goose 的 Cron Schedule 更轻量——本地 Cron 调度 + Recipe YAML 模板，任何用户都能实现定时代码审查、日报生成等自动化任务。

### Gateway 子命令

| 子命令 | 用途 |
|--------|------|
| `status` | 查看网关连接状态 |
| `start` | 启动网关 |
| `stop` | 停止网关 |
| `pair` | 配对外部平台 |

---

## 交互式斜杠命令（16 个）

源码: `crates/goose-cli/src/session/input.rs`（`handle_slash_command()` + `print_help()`）

### 按功能分类

#### 会话控制

| 命令 | 用途 | Qwen Code 对标 |
|------|------|---------------|
| `/exit`, `/quit` | 退出会话 | `/exit` |
| `/clear` | 清除聊天历史 | `/clear` |
| `/compact` | 压缩对话上下文 | `/compact` |
| `/summarize` | 压缩上下文（已弃用，用 `/compact`） | — |

#### 模式与显示

| 命令 | 用途 | Qwen Code 对标 |
|------|------|---------------|
| `/mode <name>` | 设置模式（Auto/Approve/SmartApprove/Chat） | `/mode` |
| `/t` | 切换主题（Light/Dark/Ansi） | `/theme` |
| `/t <name>` | 设置指定主题 | 同上 |
| `/r` | 切换完整工具输出（显示未截断参数） | `/verbose` |
| `/help`, `/?` | 显示帮助信息 | `/help` |

#### 规划

| 命令 | 用途 | Qwen Code 对标 |
|------|------|---------------|
| `/plan <message>` | 进入规划模式，创建执行计划 | `/plan` |
| `/endplan` | 退出规划模式 | — |

#### 扩展管理

| 命令 | 用途 | Qwen Code 对标 |
|------|------|---------------|
| `/extension <command>` | 添加 stdio MCP 扩展 | `/mcp` |
| `/builtin <names>` | 添加内置扩展 | — |

#### Prompt 模板与 Recipe

| 命令 | 用途 | Qwen Code 对标 |
|------|------|---------------|
| `/prompts [--extension <name>]` | 列出 MCP 服务器提供的 prompt 模板 | 无 |
| `/prompt <n> [--info] [key=value...]` | 执行或查看 prompt 模板 | 无 |
| `/recipe [filepath]` | 从当前对话生成 Recipe 模板 | 无 |

**开发者启示**：Goose 的斜杠命令数量（16 个）远少于 Claude Code（~79 个），但它通过两个机制补偿：

1. **MCP Prompt Template**：`/prompts` 和 `/prompt` 命令让 MCP 服务器动态提供命令——安装新的 MCP 扩展就自动获得新命令，无需修改 Agent 代码。
2. **Recipe 生成**：`/recipe` 命令将当前对话转化为可复用的 YAML 模板，实现"一次对话，多次执行"。

这两个机制让 Goose 的"有效命令数"随 MCP 生态扩展而增长，无需 Agent 开发者逐个实现。

---

## 命令架构对比

| 维度 | Goose | Claude Code | Qwen Code |
|------|-------|-------------|-----------|
| **定义方式** | clap derive 宏（编译期） | TypeScript 运行时注册 | TypeScript 运行时注册 |
| **命令类型** | CLI 命令 + 斜杠命令 | 4 种（prompt/local-jsx/local/skill） | 2 种（内置 + Skill） |
| **扩展机制** | MCP prompt + Recipe | Skill + Plugin | Skill |
| **参数校验** | 编译期（Rust 类型系统） | 运行时 | 运行时 |
| **自动化** | Recipe YAML + Cron Schedule | 无原生调度 | 无 |
| **DeepLink** | `goose://` 协议 | 无 | 无 |
