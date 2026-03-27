# 2. Goose 命令系统

Goose CLI 使用 `clap` derive 宏定义命令。交互式会话中还有额外的斜杠命令。

> 源码: `crates/goose-cli/src/cli.rs`（clap 命令定义）
> 交互式命令: `crates/goose-cli/src/session/input.rs`（`handle_slash_command()`）

## CLI 命令

### 顶层命令

| 命令 | 别名 | 用途 | 源码 |
|------|------|------|------|
| `configure` | — | 配置 goose 设置 | `commands/configure.rs` |
| `info` | — | 显示信息（`--verbose` 详情） | `commands/info.rs` |
| `mcp` | — | 运行内置 MCP 服务器 | — |
| `acp` | — | 以 ACP 代理服务器模式运行（stdio） | — |
| `session` | `s` | 管理会话 | `commands/session.rs` |
| `project` | `p` | 打开最近项目目录 | `commands/project.rs` |
| `projects` | `ps` | 列出最近项目目录 | 同上 |
| `run` | — | 从指令文件或 stdin 执行 | — |
| `recipe` | — | Recipe 工具（validate/deeplink/open/list） | `commands/recipe.rs` |
| `schedule` | `sched` | 管理定时任务 | `commands/schedule.rs` |
| `gateway` | `gw` | 管理外部网关 | `commands/gateway.rs` |
| `update` | — | 更新 CLI 版本（`--canary`） | `commands/update.rs` |
| `term` | — | 终端集成会话 | `commands/term.rs` |
| `local-models` | `lm` | 管理本地推理模型 | — |
| `completion` | — | 生成 Shell 自动补全 | — |

### Session 子命令

| 子命令 | 用途 | 选项 |
|--------|------|------|
| `list` | 列出所有会话 | `--format`, `--ascending`, `--working_dir`, `--limit` |
| `remove` | 删除会话 | `--regex` |
| `export` | 导出会话 | `--output`, `--format`（markdown/json/yaml） |
| `diagnostics` | 生成诊断 zip | — |

### Run 命令选项

| 选项组 | 参数 | 用途 |
|--------|------|------|
| Input | `--instructions`/`-i`, `--text`/`-t`, `--recipe`, `--system`, `--params` | 输入来源 |
| Extension | `--with-extension`, `--with-streamable-http-extension`, `--with-builtin`, `--no-profile` | 扩展控制 |
| Session | `--debug`, `--max-tool-repetitions`, `--max-turns`, `--container` | 会话控制 |
| Output | `--quiet`/`-q`, `--output-format`（text/json/stream-json） | 输出控制 |
| Model | `--provider`, `--model` | 模型选择 |
| Behavior | `--interactive`/`-s`, `--no-session`, `--resume`, `--scheduled-job-id` | 运行行为 |

### Recipe 子命令

| 子命令 | 用途 |
|--------|------|
| `validate` | 验证 Recipe 文件结构 |
| `deeplink` | 生成 deeplink（`goose://`） |
| `open` | 在 Goose Desktop 打开 |
| `list` | 列出可用 Recipe |

### Schedule 子命令

| 子命令 | 用途 |
|--------|------|
| `add` | 添加定时任务 |
| `list` | 列出定时任务 |
| `remove` | 删除定时任务 |
| `sessions` | 查看定时任务会话 |
| `run_now` | 立即运行定时任务 |
| `services_status` | 查看服务状态 |
| `services_stop` | 停止服务 |
| `cron_help` | Cron 表达式帮助 |

### Gateway 子命令

| 子命令 | 用途 |
|--------|------|
| `status` | 查看网关状态 |
| `start` | 启动网关 |
| `stop` | 停止网关 |
| `pair` | 配对外部平台 |

## 交互式斜杠命令（16 个）

> 源码: `crates/goose-cli/src/session/input.rs`（`handle_slash_command()` + `print_help()`）

| 命令 | 用途 |
|------|------|
| `/help`, `/?` | 显示帮助信息 |
| `/exit`, `/quit` | 退出会话 |
| `/t` | 切换主题（Light/Dark/Ansi 循环） |
| `/t <name>` | 设置指定主题（light/dark/ansi） |
| `/r` | 切换完整工具输出（显示未截断的工具参数） |
| `/mode <name>` | 设置模式（Auto/Approve/SmartApprove/Chat） |
| `/plan <message>` | 进入规划模式，创建执行计划 |
| `/endplan` | 退出规划模式 |
| `/compact` | 压缩对话上下文 |
| `/clear` | 清除聊天历史 |
| `/extension <command>` | 添加 stdio 扩展 |
| `/builtin <names>` | 添加内置扩展 |
| `/prompts [--extension <name>]` | 列出可用提示模板 |
| `/prompt <n> [--info] [key=value...]` | 执行或查看提示模板 |
| `/recipe [filepath]` | 从当前对话生成 Recipe |
| `/summarize` | 压缩上下文（已弃用，用 `/compact`） |

## MCP 内置服务器

通过 `goose mcp` 命令可独立运行内置 MCP 服务器：

| 服务器 | 用途 |
|--------|------|
| `AutoVisualiser` | 图表可视化（Chart、Sankey、Radar 等） |
| `ComputerController` | 计算机控制、Web 抓取、文件解析（DOCX/PDF/XLSX） |
| `Memory` | 记忆管理（存储/检索/删除） |
| `Tutorial` | 教程引导 |
