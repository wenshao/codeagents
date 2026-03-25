# 2. Kimi CLI 命令详解（28 个命令，源码验证）

Kimi CLI 的斜杠命令分布在两个独立的注册表中：**Soul 级**（`soul/slash.py`，8 个）和 **Shell 级**（`ui/shell/slash.py` + 子模块，20 个）。两者共享同一套 `SlashCommandRegistry` 基础设施，但生命周期和可用上下文不同。

---

## 一、命令基础设施

### SlashCommandRegistry\[F\]

```python
class SlashCommandRegistry(Generic[F]):
    """泛型注册表，F 为回调签名类型参数。"""
    commands: dict[str, SlashCommand]

    @registry.command(name="/xxx", description="...", aliases=["/yyy"])
    async def handler(args: str, ...) -> ...:
        ...
```

- 使用 `@registry.command` 装饰器注册命令，内部创建 `SlashCommand` 数据类实例
- 别名（aliases）在注册时展开为独立键指向同一 `SlashCommand`

### SlashCommand 数据类

```python
@dataclass
class SlashCommand:
    name: str          # 主命令名，含 / 前缀
    description: str   # 帮助文本中显示的描述
    func: F            # 异步回调函数
    aliases: list[str] # 别名列表
```

### parse_slash_command_call()

使用正则表达式从用户输入中解析命令名和参数：
- 匹配 `/command [args]` 格式
- 返回 `(command_name, args_string)` 元组
- 未匹配返回 `None`

### shell_mode_registry

Shell 模式下 `Ctrl-X` 切换后可用的命令子集，单独注册，回调签名与主 registry 不同。

---

## 二、Soul 级命令（8 个，soul/slash.py）

Soul 级命令在 Agent 推理循环内执行，可直接访问 `KimiSoul`、`Context`、`Runtime` 等核心对象。

### 2.1 `/init`

| 属性 | 值 |
|------|-----|
| 异步 | 是 |
| 参数 | 无 |

**执行流程：**

1. 创建临时 `KimiSoul` 实例和临时 `Context`
2. 运行 `prompts.INIT` 提示词，对当前代码库进行结构分析
3. 生成 `AGENTS.md` 文件（项目根目录），描述代码库结构与 Agent 指令
4. 调用 `load_agents_md()` 将生成的内容加载到当前运行时

> 详见 [03-architecture.md](03-architecture.md) 中 AGENTS.md 部分。

### 2.2 `/compact [FOCUS]`

| 属性 | 值 |
|------|-----|
| 异步 | 是 |
| 参数 | 可选，自然语言描述的保留重点 |

**执行流程：**

1. 检查当前 checkpoint 数量，若为 0 则直接返回（无内容可压缩）
2. 调用 `soul.compact_context(custom_instruction=args)`，将历史对话压缩为摘要
3. 发送 `StatusUpdate` 通知 UI 层压缩完成

`FOCUS` 参数允许用户指定压缩时应保留的关键信息，例如 `/compact 保留认证模块的修改细节`。

### 2.3 `/clear`（别名 `/reset`）

| 属性 | 值 |
|------|-----|
| 异步 | 是 |
| 参数 | 无 |
| 别名 | `/reset` |

**执行流程：**

1. 调用 `soul.context.clear()` 清空所有对话历史和 checkpoint
2. 重写系统提示词（system prompt），恢复到初始状态

> Shell 级也有同名 `/clear`，Shell 版本会先委托给 Soul 级执行，然后额外 `raise Reload` 重置整个 Shell 会话。

### 2.4 `/yolo`

| 属性 | 值 |
|------|-----|
| 异步 | 是 |
| 参数 | 无 |

**执行流程：**

1. 切换 `soul.runtime.approval.set_yolo(True/False)`（toggle 逻辑）
2. 开启时输出 `"You only live once!"`
3. 关闭时输出 `"You only die once!"`

YOLO 模式下所有工具调用（文件写入、命令执行等）自动审批，跳过用户确认。

### 2.5 `/plan [on|off|view|clear]`

| 属性 | 值 |
|------|-----|
| 异步 | 是 |
| 参数 | 子命令：`on`、`off`、`view`、`clear` |

**子命令详解：**

| 子命令 | 行为 |
|--------|------|
| `on` | 发送 `StatusUpdate(plan_mode=True)`，使用 `EnterPlanMode` 工具进入规划模式 |
| `off` | 发送 `StatusUpdate(plan_mode=False)`，使用 `ExitPlanMode` 工具退出规划模式 |
| `view` | 显示当前 plan 内容 |
| `clear` | 清除当前 plan |

每个 plan 会话使用独立的 UUID 作为 session ID，用于跟踪和关联规划与执行阶段。无参数时默认 toggle `on`/`off`。

### 2.6 `/add-dir [PATH]`

| 属性 | 值 |
|------|-----|
| 异步 | 是 |
| 参数 | 必填，目录路径 |

**执行流程：**

1. 验证路径为合法目录（存在且为目录类型）
2. 检查 `runtime.additional_dirs` 防止重复添加
3. 将路径添加到 `runtime.additional_dirs` 并持久化到配置
4. 注入系统消息（system message），包含新目录的文件列表（listing）

添加后，Agent 的工具（文件读写、搜索等）可以访问该目录。

### 2.7 `/export`

| 属性 | 值 |
|------|-----|
| 异步 | 是 |
| 参数 | 无 |

**执行流程：**

1. 调用 `perform_export()` 并传入当前 `context`
2. 将对话历史序列化为 wire 格式文件（JSON）
3. 输出保存路径

### 2.8 `/import`

| 属性 | 值 |
|------|-----|
| 异步 | 是 |
| 参数 | 文件路径 |

**执行流程：**

1. 对输入路径进行安全检查（sanitize）
2. 调用 `perform_import()` 加载 wire 文件内容
3. 对可能包含敏感信息的文件发出警告

---

## 三、Shell 级命令（20 个，ui/shell/slash.py + 子模块）

Shell 级命令在 TUI Shell 主循环中执行，可访问 Shell 状态和 UI 组件。许多命令通过 `raise Reload` 或其他异常来触发 Shell 状态转换。

### 3.1 `/exit`（别名 `/quit`）

| 属性 | 值 |
|------|-----|
| 别名 | `/quit` |

**实现：** `raise NotImplementedError` — 该异常由 Shell 主循环（main loop）捕获并执行退出流程。这是一种信号机制而非真正的错误。

### 3.2 `/help`（别名 `/h`、`/?`）

| 属性 | 值 |
|------|-----|
| 别名 | `/h`、`/?` |

**执行流程：**

1. 显示键盘快捷键列表
2. 显示所有已注册命令及其描述
3. 显示可用 Skills 列表
4. 使用 Rich pager 分页展示
5. 末尾附带 Beatles 名言（彩蛋）

### 3.3 `/version`

**实现：** 直接打印 `kimi_cli.constant.VERSION` 常量值。

### 3.4 `/model`

| 属性 | 值 |
|------|-----|
| 异步 | 是 |

**执行流程：**

1. 刷新可用模型列表（从 API 获取最新）
2. 弹出 `ChoiceInput` 让用户选择模型
3. 弹出 `ChoiceInput` 让用户选择思维模式（thinking mode）
4. 保存选择到配置文件
5. `raise Reload` 以新模型重新初始化 Soul

### 3.5 `/editor [COMMAND]`

| 属性 | 值 |
|------|-----|
| 异步 | 是 |
| 参数 | 可选，编辑器命令 |

**执行流程：**

1. 无参数时弹出 `ChoiceInput`，候选项为 `"code --wait"`、`vim`、`nano`、`auto`
2. 有参数时直接使用指定命令
3. 验证编辑器二进制文件是否存在于 `PATH` 中
4. 保存到配置，后续 `Ctrl-O` 将使用此编辑器

### 3.6 `/changelog`（别名 `/release-notes`）

| 属性 | 值 |
|------|-----|
| 别名 | `/release-notes` |

**执行流程：**

1. 遍历内置 `CHANGELOG` 字典（按版本号组织）
2. 使用 Rich 格式化输出每个版本的变更内容
3. 通过 pager 分页显示

### 3.7 `/feedback`

**实现：** 调用 `webbrowser.open("https://github.com/MoonshotAI/kimi-cli/issues")` 在默认浏览器中打开 Issue 页面。

### 3.8 `/clear`（别名 `/reset`，Shell 级）

| 属性 | 值 |
|------|-----|
| 别名 | `/reset` |

**执行流程：**

1. 委托给 Soul 级 `/clear` 执行上下文清理
2. `raise Reload` 重置 Shell 会话状态

与 Soul 级 `/clear` 的区别：Shell 级额外触发 Reload，完全重新初始化 TUI。

### 3.9 `/new`

**执行流程：**

1. 创建新的 `Session` 对象（新的 session ID）
2. `raise Reload(session_id=new_id)` 切换到新会话

### 3.10 `/sessions`（别名 `/resume`）

| 属性 | 值 |
|------|-----|
| 别名 | `/resume` |

**执行流程：**

1. 列出所有已保存的会话，显示时间戳等元数据
2. 弹出 `ChoiceInput` 让用户选择要恢复的会话
3. `raise Reload(session_id=selected_id)` 切换到选定会话

### 3.11 `/task`

**执行流程：**

1. 打开 `TaskBrowserApp(soul)` TUI 界面（基于 Textual 框架）
2. 仅在 root agent 下可用，显示后台任务列表及状态

### 3.12 `/web`

**实现：** `raise SwitchToWeb(session_id=current_id)`，触发从 Shell 模式到 Web UI 模式的转换。当前会话数据保持不变。

### 3.13 `/mcp`

**执行流程：**

1. 触发 MCP 服务器列表的后台加载
2. 使用 `Live` 显示（8fps 刷新率）配合 `render_mcp_console()` 渲染
3. 展示所有已配置 MCP 服务器的连接状态、可用工具等信息

### 3.14 `/debug`

**执行流程：**

显示完整的上下文调试信息，使用 Rich panels 格式化：

- 消息列表（messages）及各消息 token 数
- 总 token 用量统计
- Checkpoint 列表及内容摘要
- 完整轨迹（trajectory）记录

### 3.15 `/export`（Shell 级）

**执行流程：**

1. 与 Soul 级 `/export` 相同的导出逻辑
2. 额外将 wire 格式文件写入磁盘并显示路径

### 3.16 `/import`（Shell 级）

**执行流程：**

1. 与 Soul 级 `/import` 相同的导入逻辑
2. 额外在 wire 数据中追加 `TurnBegin`/`TurnEnd` 事件标记

### 3.17 `/login`（别名 `/setup`）

| 属性 | 值 |
|------|-----|
| 别名 | `/setup` |

**执行流程：**

1. 调用 `select_platform()` 让用户选择 AI 平台（Moonshot、OpenAI 等）
2. 根据平台类型执行认证：
   - **OAuth 流程：** 打开浏览器完成授权回调
   - **API Key：** 提示用户输入 API key
3. 保存认证信息到配置
4. `raise Reload` 以新认证重新初始化

### 3.18 `/logout`

**执行流程：**

1. 从配置中移除当前 provider 及其关联的 models 配置
2. `raise Reload` 重新初始化（回到未认证状态）

### 3.19 `/reload`

**实现：** 直接 `raise Reload`，强制 Shell 完整重新初始化。用于排查问题或手动刷新状态。

### 3.20 `/usage`（别名 `/status`）

| 属性 | 值 |
|------|-----|
| 别名 | `/status` |

**执行流程：**

1. 向 `{base_url}/usages` API 发送请求获取用量数据
2. 使用 Rich 进度条渲染用量：
   - **绿色：** 用量低于 50%
   - **黄色：** 用量 50%–80%
   - **红色：** 用量超过 80%
3. 显示各资源（tokens、请求数等）的使用量和配额

---

## 四、命令生命周期与异常驱动流程

Kimi CLI 大量使用**异常作为控制流信号**：

| 异常 | 含义 | 触发命令 |
|------|------|----------|
| `Reload` | 重新初始化 Shell（可携带 session_id） | `/model`、`/clear`、`/new`、`/sessions`、`/login`、`/logout`、`/reload` |
| `SwitchToWeb` | 从 Shell 模式切换到 Web UI | `/web` |
| `NotImplementedError` | 退出信号（被主循环捕获） | `/exit` |

这种设计让命令处理器保持简洁——只需 raise 对应异常，由 Shell 主循环统一处理状态转换。

---

## 五、键盘快捷键

| 快捷键 | 功能 |
|--------|------|
| `Ctrl-X` | 切换 Agent ↔ Shell 模式（shell_mode_registry） |
| `Ctrl-C` | 中断当前操作 |
| `Ctrl-D` | 退出 |
| `Ctrl-O` | 在外部编辑器中打开输入（使用 `/editor` 配置的编辑器） |
| `Ctrl-V` | 粘贴文本/图片/视频 |
| `Ctrl-E` | 展开审批预览详情 |
| `Shift-Tab` | 切换 Plan 模式（等效 `/plan`） |
| `1/2/3/4` | 审批面板快捷键：审批 / 会话审批 / 拒绝 / 拒绝+反馈 |

---

## 六、命令速查表

### Soul 级（8 个）

| 命令 | 别名 | 参数 | 一句话说明 |
|------|------|------|-----------|
| `/init` | — | 无 | 分析代码库，生成 AGENTS.md |
| `/compact` | — | `[FOCUS]` | 压缩上下文，可指定保留重点 |
| `/clear` | `/reset` | 无 | 清空上下文与对话历史 |
| `/yolo` | — | 无 | 切换自动审批模式 |
| `/plan` | — | `[on\|off\|view\|clear]` | 管理规划模式 |
| `/add-dir` | — | `PATH` | 添加额外工作目录 |
| `/export` | — | 无 | 导出会话为 wire 文件 |
| `/import` | — | 文件路径 | 导入 wire 文件到上下文 |

### Shell 级（20 个）

| 命令 | 别名 | 参数 | 一句话说明 |
|------|------|------|-----------|
| `/exit` | `/quit` | 无 | 退出 CLI |
| `/help` | `/h`、`/?` | 无 | 显示帮助信息 |
| `/version` | — | 无 | 显示版本号 |
| `/model` | — | 无 | 切换模型和思维模式 |
| `/editor` | — | `[COMMAND]` | 配置外部编辑器 |
| `/changelog` | `/release-notes` | 无 | 显示更新日志 |
| `/feedback` | — | 无 | 打开 GitHub Issues |
| `/clear` | `/reset` | 无 | 清空上下文并重载 Shell |
| `/new` | — | 无 | 创建新会话 |
| `/sessions` | `/resume` | 无 | 列出并恢复历史会话 |
| `/task` | — | 无 | 打开任务浏览器 TUI |
| `/web` | — | 无 | 切换到 Web UI 模式 |
| `/mcp` | — | 无 | 显示 MCP 服务器状态 |
| `/debug` | — | 无 | 显示上下文调试信息 |
| `/export` | — | 无 | 导出会话（含 wire 写入） |
| `/import` | — | 文件路径 | 导入会话（含 TurnBegin/TurnEnd） |
| `/login` | `/setup` | 无 | 登录/配置 AI 平台 |
| `/logout` | — | 无 | 登出并清除认证 |
| `/reload` | — | 无 | 强制重新初始化 Shell |
| `/usage` | `/status` | 无 | 查看 API 用量与配额 |
