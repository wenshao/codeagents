# Kimi CLI 遥测与安全分析证据

## 遥测系统
- **无遥测** — 递归搜索零结果
- 无 PostHog/Sentry/Mixpanel/任何分析 SDK

## 数据采集
- **不采集**: Machine ID、MAC 地址、主机名、硬件信息
- `metadata.py` 使用 MD5(工作目录路径) 仅用于本地会话目录命名
- `environment.py` 检测 OS/arch/shell 仅用于本地环境适配

## 外发请求
- 仅 LLM API 调用（用户配置的 provider）
- 无任何分析端点

## 安全系统
- `soul/approval.py`: 工具审批系统（approve/reject/approve-for-session）
- `ApprovalState`: YOLO 模式 + 按操作自动审批集合
- 子代理拒绝有专门的严格消息防止重试绕过

来源: src/kimi_cli/ (GitHub 源码分析)

## 深度补充（源码级分析）

### 命令系统（源码: soul/slash.py + ui/shell/slash.py）
- 双注册表: Soul 级 8 个 + Shell 级 20 个 = 28 个命令
- SlashCommandRegistry[F]: 泛型注册表，@registry.command 装饰器
- SlashCommand dataclass: name, description, func, aliases
- parse_slash_command_call(): 正则解析 /command args

### Soul 级命令实现（async）
| 命令 | 实现 | 关键逻辑 |
|------|------|----------|
| /init | 创建临时 KimiSoul + Context | 运行 prompts.INIT 生成 AGENTS.md |
| /compact | soul.compact_context() | 支持 custom_instruction 参数 |
| /clear | soul.context.clear() | 重写系统提示 |
| /yolo | approval.set_yolo() | "You only live/die once!" |
| /plan | toggle_plan_mode_from_manual() | on/off/view/clear 子命令，UUID 会话 |
| /add-dir | runtime.additional_dirs | 验证存在/防重复/注入系统消息 |
| /export | perform_export() | 含 wire 文件写入 |
| /import | perform_import() | 敏感文件警告 |

### Shell 级命令实现
| 命令 | 关键实现 |
|------|----------|
| /model | ChoiceInput 选择 → 保存配置 → Reload |
| /editor | ChoiceInput: code --wait/vim/nano → PATH 验证 |
| /sessions | 列出 + ChoiceInput → Reload(session_id) |
| /task | TaskBrowserApp(soul) TUI |
| /mcp | Live 显示(8fps) render_mcp_console |
| /debug | 全量上下文 dump（消息/token/轨迹）|
| /usage | {base_url}/usages API → 进度条（绿/黄/红）|
| /login | OAuth 浏览器流程 |

### 压缩系统（源码: soul/compaction.py）
- SimpleCompaction(max_preserved_messages=2)
- 自动触发: token_count >= max_context * 0.85 或 + 50000 >= max
- 输出结构: <current_focus> <environment> <completed_tasks> <active_issues> <code_state> <important_context>
- 优先级: 当前任务 > 错误解决 > 代码演化 > 系统上下文 > 设计决策 > TODO
- 自定义焦点: "用户特别要求以下压缩焦点。你必须将此指令优先于默认优先级"
- 重试: tenacity 指数退避（0.3s→5s），最多 3 次

### 审批系统（源码: soul/approval.py）
- ApprovalState: yolo bool + auto_approve_actions set
- ApprovalResult: approved bool + feedback str
- approve_for_session: 添加到 auto set + 解析所有同操作 pending
- 子代理拒绝: 特殊消息防止重试死循环

### Wire 协议（源码: wire/）
- JSONL 格式事件流
- 30+ 事件类型: control flow, content, tools, status, interaction, compression
- 支持会话导出/导入和跨客户端回放

### 多代理系统（源码: soul/agent.py）
5 个代理:
| 代理 | 类型 | 用途 |
|------|------|------|
| default | 主代理 | 通用任务 |
| coder | 编码 | 代码生成 |
| explore | 只读 | 代码库探索 |
| plan | 规划 | EnterPlanMode/ExitPlanMode |
| okabe | 实验 | D-Mail 时间回溯 |

### 工具系统（18 个）
ReadFile, WriteFile, EditFile, RunBash, ListDir, SearchContent, GlobPattern, Fetch, AskUser, RunPython, EnterPlanMode, ExitPlanMode, SendDMail, plus MCP 工具

### 模型支持
- 多提供商: Kimi(Moonshot), OpenAI, Anthropic, Gemini, Vertex AI
- 思维模式: always_thinking（强制开启）, thinking（可选）, off

来源: GitHub 源码 soul/slash.py, soul/compaction.py, soul/approval.py, soul/agent.py
