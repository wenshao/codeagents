# 2. Aider 命令详解（42 个，源码：commands.py 1712 行）

Aider 提供 42 个斜杠命令，全部定义在 `aider/commands.py` 的 `Commands` 类中。每个命令对应一个 `cmd_<name>` 方法，通过反射自动发现和分发。以下按功能分类详述每个命令的签名、实现规模、文档字符串及关键实现细节。

---

## 一、文件与上下文管理（8 个）

### `/add <file|glob|url> ...`
- **文档字符串**：Add files to the chat so aider can edit them or review them
- **实现规模**：约 105 行
- **关键实现**：
  - 支持带引号的文件名（处理路径含空格的情况）
  - 支持 glob 模式匹配（如 `*.py`、`src/**/*.js`）
  - 若文件不存在，交互确认后创建新文件（`touch` 语义）
  - 若文件已在只读列表（`abs_read_only_fnames`）中，自动提升为可编辑文件
  - 对图片文件进行验证（检查是否为模型支持的图片格式）
  - URL 参数会委托给 `/web` 命令处理
  - 补全方法 `completions_add` 提供仓库内文件的 Tab 补全

### `/drop [file|glob] ...`
- **文档字符串**：Remove files from the chat session to free up context space
- **实现规模**：约 55 行
- **关键实现**：
  - 无参数调用时移除所有文件，但保留启动时指定的原始只读文件
  - 支持子串匹配：输入 `foo` 可匹配 `src/foo.py`
  - 支持 glob 模式匹配
  - 同时从 `abs_fnames`（可编辑）和 `abs_read_only_fnames`（只读）中移除
  - 补全方法提供当前上下文中文件的 Tab 补全

### `/read-only [file|glob] ...`
- **文档字符串**：Add files to the chat that are for reference only, not for editing
- **实现规模**：约 89 行
- **关键实现**：
  - 无参数调用时：将所有可编辑文件转为只读（从 `abs_fnames` 移到 `abs_read_only_fnames`）
  - 支持 glob 模式匹配
  - 支持目录参数：对目录进行递归展开，将目录下所有文件加入只读列表
  - 文件路径做绝对路径规范化处理
  - 若文件已在可编辑列表中，会先移除再加入只读列表

### `/ls`
- **文档字符串**：List all known files and indicate which are included in the chat session
- **实现规模**：约 38 行
- **关键实现**：
  - 分三组显示文件列表：
    1. **仓库中未加入的文件**（repo files not in chat）
    2. **只读文件**（read-only files）
    3. **已加入的可编辑文件**（editable files in chat）
  - 每组使用不同格式化样式便于区分
  - 文件路径显示为相对于仓库根目录的相对路径

### `/map`
- **文档字符串**：Print out the current repository map
- **实现规模**：约 7 行
- **关键实现**：
  - 调用 `coder.get_repo_map()` 获取仓库地图
  - 仓库地图是通过 tree-sitter 解析生成的代码结构摘要
  - 若无仓库地图可用，输出提示信息

### `/map-refresh`
- **文档字符串**：Force a refresh of the repository map
- **实现规模**：约 5 行
- **关键实现**：
  - 调用 `coder.get_repo_map(force_refresh=True)` 强制刷新缓存
  - 用于在外部修改文件后手动更新仓库地图

### `/context`
- **文档字符串**：Enter context mode to see surrounding code context
- **实现规模**：约 2 行
- **关键实现**：
  - 调用 `_generic_chat_command(args, "context")` 切换到上下文查看模式
  - 通过 `SwitchCoder` 异常触发 Coder 实例切换

### `/tokens`
- **文档字符串**：Report on the number of tokens used by the current chat context
- **实现规模**：约 107 行
- **关键实现**：
  - 逐项计算并显示 token 用量：
    - 系统消息（system messages）的 token 数
    - 聊天历史（chat history）的 token 数
    - 仓库地图（repo map）的 token 数
    - 可编辑文件（editable files）的 token 数（逐文件列出）
    - 只读文件（read-only files）的 token 数（逐文件列出）
  - 计算预估成本（基于模型的 token 价格）
  - 若总 token 数接近或超过模型上下文窗口限制，输出警告信息
  - 使用 `token_count()` 方法做精确计数

---

## 二、模式切换（5 个）

### `/chat-mode <mode>`
- **文档字符串**：Switch to a new chat mode
- **实现规模**：约 66 行
- **关键实现**：
  - 验证模式名称，支持 15 种编辑格式（`diff`、`whole`、`udiff`、`diff-fenced` 等）加特殊模式（`ask`、`architect`、`context`、`help`）
  - 通过抛出 `SwitchCoder` 异常实现模式切换，由外层主循环捕获并重建 Coder 实例
  - 无效模式名会列出所有可用模式供用户选择
  - 补全方法提供所有可用模式的 Tab 补全

### `/code [message]`
- **文档字符串**：Ask for changes to your code（在 code 模式下）
- **实现规模**：约 2 行
- **关键实现**：
  - 调用 `_generic_chat_command(args, main_model.edit_format)` 切换到代码编辑模式
  - 使用当前主模型的 `edit_format` 属性决定具体编辑格式
  - 若附带消息参数，切换后立即发送该消息

### `/architect [message]`
- **文档字符串**：Enter architect mode for high-level design discussions
- **实现规模**：约 2 行
- **关键实现**：
  - 调用 `_generic_chat_command(args, "architect")` 切换到架构师模式
  - 架构师模式下 LLM 先生成修改计划，再由 editor model 执行实际编辑
  - 若附带消息参数，切换后立即发送该消息

### `/ask [question]`
- **文档字符串**：Ask questions about the code base without editing any files
- **实现规模**：约 2 行
- **关键实现**：
  - 调用 `_generic_chat_command(args, "ask")` 切换到问答模式
  - 问答模式下不会产生任何文件编辑，仅回答问题
  - 若附带问题参数，切换后立即发送该问题

### `/ok`
- **文档字符串**：Confirm and execute the suggested changes
- **实现规模**：约 5 行
- **关键实现**：
  - 将固定前缀 `"Ok, please go ahead and make those changes."` 加上用户附加的参数作为消息发送
  - 用于确认 `/ask` 或 `/architect` 模式下给出的建议，让 LLM 执行修改

---

## 三、模型管理（4 个）

### `/model <model-name>`
- **文档字符串**：Switch to a new LLM
- **实现规模**：约 26 行
- **关键实现**：
  - 创建新的 `Model` 对象
  - 调用 `sanity_check_model()` 验证模型可用性（API key、网络连接等）
  - 智能保留或更新 `edit_format`：若用户未显式设置过编辑格式，则使用新模型的默认格式
  - 通过 `SwitchCoder` 异常触发 Coder 实例重建，将新模型传入

### `/editor-model <model-name>`
- **文档字符串**：Switch the editor model
- **实现规模**：约 11 行
- **关键实现**：
  - 创建新的 `Model` 对象作为 editor model
  - editor model 在架构师模式下负责执行实际的代码编辑
  - 通过 `SwitchCoder` 异常传递 `editor_model` 参数完成切换

### `/weak-model <model-name>`
- **文档字符串**：Switch the weak model
- **实现规模**：约 11 行
- **关键实现**：
  - 创建新的 `Model` 对象作为 weak model
  - weak model 用于生成提交消息、仓库地图等辅助任务
  - 通过 `SwitchCoder` 异常传递 `weak_model` 参数完成切换

### `/models <search-query>`
- **文档字符串**：Search the list of available models
- **实现规模**：约 9 行
- **关键实现**：
  - 调用 `models.print_matching_models(args)` 搜索并显示匹配的模型列表
  - 搜索基于模型名称的子串匹配
  - 显示结果包括模型全名和提供商信息

---

## 四、Git 与工作流（8 个）

### `/commit [message]`
- **文档字符串**：Commit edits to the repo made outside of aider with a sensible commit message
- **实现规模**：约 18 行
- **关键实现**：
  - 检查工作区是否有未提交的更改（dirty check）
  - 若提供了消息参数，直接使用该消息作为提交信息
  - 若未提供消息，调用 `repo.commit(coder=self.coder)` 让 LLM 自动生成提交信息
  - 提交完成后输出提交哈希

### `/undo`
- **文档字符串**：Undo the last aider commit if possible
- **实现规模**：约 103 行
- **关键实现**：
  - 仅撤销由 aider 创建的提交（通过 `aider_commit_hashes` 集合验证）
  - 安全检查链：
    1. 验证目标提交确实是 aider 生成的
    2. 检查提交未被推送到远程（防止撤销已共享的提交）
    3. 确认不是 merge commit
    4. 确认当前无未提交的更改（防止数据丢失）
  - 撤销操作分两步：`git checkout HEAD~1 -- .` 恢复文件，然后 `git reset --soft HEAD~1` 回退提交指针
  - 使用 `--soft` 保留更改在暂存区，用户可以检查后重新提交

### `/diff`
- **文档字符串**：Display the diff of changes since the last message
- **实现规模**：约 39 行
- **关键实现**：
  - 使用 `commit_before_message[-2]` 作为基准提交（即上一轮对话开始前的状态）
  - 支持 pretty 模式输出（彩色高亮）
  - 同时显示已提交和未提交的差异
  - 若无基准提交可用，显示工作区的完整 diff

### `/git <command>`
- **文档字符串**：Run a git command
- **实现规模**：约 25 行
- **关键实现**：
  - 通过 `subprocess.run("git " + args)` 执行任意 git 命令
  - 设置 `GIT_EDITOR=true` 环境变量，阻止交互式编辑器弹出
  - 命令输出显示给用户但不加入聊天上下文
  - 执行完成后自动检查文件变更状态

### `/lint [file ...]`
- **文档字符串**：Lint and fix in-chat files or all dirty files if none specified
- **实现规模**：约 54 行
- **关键实现**：
  - 若指定了文件，对这些文件执行 lint
  - 若未指定文件，获取聊天中的文件列表，回退到所有 dirty 文件
  - 逐文件执行 lint 检查（使用配置的 lint 命令）
  - 发现问题后克隆当前 coder 实例进行自动修复
  - 修复完成后调用 `auto_commit` 自动提交修复结果

### `/test [command]`
- **文档字符串**：Run a shell command and add the output to the chat on non-zero exit code
- **实现规模**：约 19 行
- **关键实现**：
  - 若未提供命令参数，使用 `coder.test_cmd` 配置的默认测试命令
  - 委托给 `cmd_run()` 执行，传入 `add_on_nonzero_exit=True`
  - 测试失败（非零退出码）时自动将输出加入聊天，触发 LLM 分析和修复

### `/run <command>`
- **文档字符串**：Run a shell command and optionally add the output to the chat
- **实现规模**：约 41 行
- **关键实现**：
  - 通过 `subprocess` 执行 Shell 命令
  - 计算命令输出的 token 数量（用于判断是否适合加入聊天）
  - 命令返回非零退出码时，提示用户是否将输出加入聊天上下文
  - 用户确认后将输出设置为 `placeholder`，在下一轮对话中发送给 LLM
  - `!` 前缀是 `/run` 的快捷别名（如 `!pytest` 等价于 `/run pytest`）

### `/web <url>`
- **文档字符串**：Scrape a webpage, convert to markdown and send in a message
- **实现规模**：约 35 行
- **关键实现**：
  - 使用 `Scraper` 类抓取网页（底层基于 Playwright 浏览器引擎）
  - 将 HTML 内容转换为 Markdown 格式
  - 转换后的内容加入 `cur_messages` 供 LLM 参考
  - 支持 JavaScript 渲染的动态页面

---

## 五、会话管理（5 个）

### `/clear`
- **文档字符串**：Clear the chat history
- **实现规模**：约 4 行
- **关键实现**：
  - 清空 `done_messages`（已完成的对话历史）
  - 清空 `cur_messages`（当前轮对话消息）
  - 不影响已添加的文件列表

### `/reset`
- **文档字符串**：Drop all files and clear the chat history
- **实现规模**：约 4 行
- **关键实现**：
  - 调用 `_drop_all_files()` 移除所有文件
  - 调用 `_clear_chat_history()` 清除聊天历史
  - 相当于 `/drop` + `/clear` 的组合操作

### `/settings`
- **文档字符串**：Print out the current settings
- **实现规模**：约 29 行
- **关键实现**：
  - 调用 `format_settings()` 格式化当前所有配置项
  - 追加显示 announcements（系统公告和警告）
  - 追加显示 model metadata（模型的详细元数据信息）
  - 输出包括编辑格式、模型配置、Git 设置等全部参数

### `/load <file>`
- **文档字符串**：Load and execute commands from a file
- **实现规模**：约 28 行
- **关键实现**：
  - 逐行读取指定文件
  - 跳过 `#` 开头的注释行和空行
  - 对每一行调用 `self.run(cmd)` 执行命令
  - 支持嵌套调用（文件中可以包含 `/load` 命令）
  - 常用于保存和恢复工作会话状态

### `/save <file>`
- **文档字符串**：Save commands to a file that can reproduce the current chat session's files
- **实现规模**：约 26 行
- **关键实现**：
  - 先写入 `/drop` 命令（确保加载时从干净状态开始）
  - 为每个可编辑文件写入 `/add <filename>` 命令
  - 为每个只读文件写入 `/read-only <filename>` 命令
  - 生成的文件可直接通过 `/load` 恢复会话状态

---

## 六、输入输出（6 个）

### `/paste`
- **文档字符串**：Paste image/text from the clipboard into the chat
- **实现规模**：约 49 行
- **关键实现**：
  - 图片粘贴：使用 PIL 的 `ImageGrab.grabclipboard()` 获取剪贴板图片
    - 保存为临时 PNG 或 JPEG 文件
    - 将临时文件路径加入 `abs_fnames` 供 LLM 视觉分析
  - 文本粘贴：使用 `pyperclip.paste()` 获取剪贴板文本内容
  - 优先尝试图片粘贴，失败后回退到文本粘贴

### `/copy`
- **文档字符串**：Copy the last assistant message to the clipboard
- **实现规模**：约 26 行
- **关键实现**：
  - 从聊天历史中查找最后一条 assistant 角色的消息
  - 使用 `pyperclip.copy()` 复制到系统剪贴板
  - 显示前 50 个字符的预览，确认复制成功
  - 若无 assistant 消息可复制，输出提示信息

### `/voice`
- **文档字符串**：Record and transcribe voice input
- **实现规模**：约 25 行
- **关键实现**：
  - 需要设置 `OPENAI_API_KEY` 环境变量
  - 使用 `Voice` 类进行录音（基于 `sounddevice` 库）
  - 调用 OpenAI Whisper API 进行语音转文字
  - 转录结果设置为 `placeholder`，在下一轮用户输入时自动填充

### `/editor`
- **文档字符串**：Open an editor to write a message
- **实现规模**：约 5 行
- **关键实现**：
  - 调用 `pipe_editor(suffix="md")` 打开系统默认外部编辑器（由 `$EDITOR` 环境变量决定）
  - 使用 `.md` 后缀以便编辑器启用 Markdown 语法高亮
  - 编辑器关闭后，内容设置为 `placeholder` 作为下一轮用户输入

### `/edit`
- **文档字符串**：Alias for /editor
- **实现规模**：约 2 行
- **关键实现**：
  - 直接调用 `cmd_editor(args)` 的别名方法
  - 提供更简短的命令名称

### `/multiline-mode`
- **文档字符串**：Toggle multiline mode
- **实现规模**：约 2 行
- **关键实现**：
  - 调用 `io.toggle_multiline_mode()` 切换多行输入模式
  - 多行模式下 Enter 键换行，Meta+Enter 或 Ctrl+D 提交输入
  - 适用于需要输入多行消息的场景

---

## 七、推理控制（2 个）

### `/think-tokens <value>`
- **文档字符串**：Set the thinking token budget
- **实现规模**：约 34 行
- **关键实现**：
  - 无参数调用时显示当前思维 token 预算值
  - 传入 `"0"` 或 `"off"` 时禁用思维 token（关闭扩展思考）
  - 其他值传递给 `model.set_thinking_tokens(value)` 设置新预算
  - 支持数字和带单位的值（如 `"10k"`、`"100000"`）
  - 仅对支持扩展思考的模型生效（如 Claude 3.5 Sonnet extended thinking）

### `/reasoning-effort <value>`
- **文档字符串**：Set the reasoning effort level
- **实现规模**：约 22 行
- **关键实现**：
  - 无参数调用时显示当前推理努力级别
  - 调用 `model.set_reasoning_effort(value)` 设置新值
  - 不同模型对推理努力的解释不同（如 OpenAI 的 `low`/`medium`/`high`，或数值 1-100）
  - 影响模型在回答时投入的计算资源

---

## 八、其他（5 个）

### `/help [question]`
- **文档字符串**：Ask questions about aider
- **实现规模**：约 50 行
- **关键实现**：
  - 无参数调用时显示 `basic_help` 表格，列出所有命令的简要说明
  - 有参数时进入智能帮助模式：
    - 安装 `help_extra` 依赖包（首次使用时）
    - 创建专用的 Help Coder 实例（`map_tokens=512` 限制上下文大小）
    - 加载 aider 文档作为参考资料
    - 使用 LLM 回答关于 aider 的问题

### `/report [title]`
- **文档字符串**：Report a problem by opening a GitHub Issue
- **实现规模**：约 13 行
- **关键实现**：
  - 收集当前 `announcements`（包含版本、模型、配置等环境信息）
  - 调用 `report_github_issue(title=args)` 打开浏览器到 GitHub Issues 页面
  - 自动填充环境信息到 Issue 模板中

### `/copy-context`
- **文档字符串**：Copy the current chat context to the clipboard
- **实现规模**：约 43 行
- **关键实现**：
  - 调用 `format_chat_chunks()` 格式化完整的聊天上下文
  - 从格式化结果中提取 user 角色的消息
  - 使用 `pyperclip.copy()` 复制到系统剪贴板
  - 用于将上下文粘贴到其他工具或 LLM 界面中

### `/exit`
- **文档字符串**：Exit the application
- **实现规模**：约 3 行
- **关键实现**：
  - 发送 `event("exit")` 遥测事件
  - 调用 `sys.exit()` 终止进程

### `/quit`
- **文档字符串**：Exit the application
- **实现规模**：约 2 行
- **关键实现**：
  - 直接调用 `cmd_exit()` 的别名方法

---

## 九、关键基础设施

### SwitchCoder 异常模式

模式切换和模型切换的核心机制是 `SwitchCoder` 异常。当命令需要切换 Coder 实例时（如 `/chat-mode`、`/model`、`/architect` 等），不直接修改当前 Coder，而是抛出一个携带新配置参数的 `SwitchCoder` 异常。外层主循环（`main.py` 的 `run` 方法）捕获该异常，用其中的参数重新构建一个全新的 Coder 实例。

这种设计的优势：
- 避免在 Coder 对象上做复杂的状态变更
- 确保新 Coder 实例的所有内部状态一致性
- 支持在一次切换中同时修改多个参数（模型、格式、编辑器模型等）

### 命令分发：cmd_ 前缀自动发现

`Commands` 类使用 Python 的反射机制实现命令分发：

1. 用户输入 `/foo bar` 后，`run()` 方法提取命令名 `foo`
2. 通过 `getattr(self, "cmd_foo")` 查找对应方法
3. 若找到则调用 `cmd_foo("bar")`，否则报错
4. 命令名中的 `-` 会转换为 `_`（如 `/chat-mode` 对应 `cmd_chat_mode`）

无需注册表或装饰器，新增命令只需添加 `cmd_xxx` 方法即可自动生效。

### Tab 补全：completions_ 方法

每个命令可选地定义 `completions_<cmd>` 方法来提供 Tab 补全候选项：

- `completions_add()`：返回仓库中所有文件路径
- `completions_drop()`：返回当前聊天上下文中的文件路径
- `completions_chat_mode()`：返回所有可用的编辑模式名
- `completions_model()`：返回已知的模型名称列表

补全系统与 `prompt_toolkit` 集成，用户按 Tab 键时自动调用对应方法。

### `!` 前缀快捷方式

命令解析器对 `!` 前缀做了特殊处理：任何以 `!` 开头的输入会被自动转换为 `/run` 命令。例如：

- `!pytest` → `/run pytest`
- `!ls -la` → `/run ls -la`

这为频繁执行 Shell 命令的用户提供了便捷的快捷方式。
