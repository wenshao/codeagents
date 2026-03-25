# 4. Claude Code 工具系统

Claude Code 内置 20+ 工具，分为核心工具、延迟加载工具和内部工具三类。

## 核心工具（始终可用）

| 工具 | 用途 | 说明 |
|------|------|------|
| **Read** | 读取文件内容 | 支持行范围读取、图片/PDF 查看、Jupyter Notebook 解析 |
| **Write** | 创建/覆写文件 | 整文件写入，要求先读后写 |
| **Edit** | 精确编辑文件 | 基于 old_string/new_string 的精确替换，支持 replace_all |
| **MultiEdit** | 批量编辑文件 | 对同一文件执行多次编辑操作，减少工具调用次数 |
| **Bash** | 执行 Shell 命令 | 支持后台运行、超时控制、工作目录保持 |
| **Glob** | 文件模式搜索 | 支持 `**/*.ts` 等 glob 模式，按修改时间排序 |
| **Grep** | 内容正则搜索 | 基于 ripgrep，支持多行匹配、文件类型过滤、上下文显示 |
| **Agent** | 启动子代理 | 创建独立上下文的子代理执行复杂子任务 |
| **TodoWrite** | 创建待办列表 | 管理任务规划和进度追踪 |

## 延迟加载工具（通过 ToolSearch 按需激活）

| 工具 | 用途 | 说明 |
|------|------|------|
| **WebFetch** | 抓取网页内容 | 获取 URL 内容，HTML 转文本 |
| **WebSearch** | Web 搜索 | 搜索互联网获取最新信息 |
| **NotebookEdit** | 编辑 Jupyter Notebook | 操作 .ipynb 文件的单元格 |
| **TaskCreate** | 创建后台任务 | 启动并行子代理任务，不阻塞主对话 |
| **TaskGet** | 获取任务详情 | 读取后台任务结果 |
| **TaskList** | 列出所有任务 | 查看所有后台任务状态 |
| **TaskUpdate** | 更新任务状态 | 向运行中的任务发送更新 |
| **CronCreate** | 创建定时任务 | 设置定时执行的自动化任务 |
| **CronDelete** | 删除定时任务 | 移除已创建的定时任务 |
| **CronList** | 列出定时任务 | 查看所有定时任务列表 |
| **EnterWorktree** | 进入 Worktree | 切换到独立的 Git worktree 工作区 |
| **ExitWorktree** | 退出 Worktree | 返回主工作区 |
| **RemoteTrigger** | 远程触发 | 触发远程操作或工作流 |
| **ToolSearch** | 搜索延迟工具 | 查找并加载按需注册的工具 Schema |

## 内部工具

| 工具 | 用途 | 说明 |
|------|------|------|
| **KillShell** | 终止 Shell | 终止正在运行的后台 Shell 进程 |
| **Brief** | 简洁模式 | 控制响应的详细程度 |
| **Skill** | 激活技能 | 调用已注册的自定义技能/斜杠命令 |

此外，MCP 工具以 `mcp__serverName__toolName` 格式动态注册（注意双下划线），可通过策略规则统一管控。

## 多代理系统

Claude Code 支持通过 Agent 工具和 Task 工具创建子代理，实现多代理并行协作：

### Agent 工具
Agent 工具创建一个独立上下文的子代理，继承主代理的工具集但拥有独立的对话历史。适用于：
- 探索性任务：调查代码库结构、搜索相关文件
- 独立子任务：不影响主对话上下文的操作
- 并行执行：多个子代理同时处理不同任务

### Task 工具（后台任务）
TaskCreate/TaskUpdate/TaskGet/TaskList 提供后台并行执行能力：
- **TaskCreate**：启动后台子代理，主对话不阻塞
- **TaskGet**：查询任务结果
- **TaskList**：列出所有活跃/已完成任务
- **TaskUpdate**：向运行中的任务发送更新

### Teammates（团队协作）
通过 tmux 或 iTerm2 分屏，多个 Claude Code 实例协作：
- 每个代理运行在独立的 Git worktree 中
- 支持代理间消息传递
- 适合大规模重构：一个代理负责规划，多个代理并行实现
