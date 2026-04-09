# 2. Kimi CLI 命令系统——开发者参考

> Kimi CLI 共有 28 个斜杠命令（Soul 级 8 个 + Shell 级 20 个），以及 Agent ↔ Shell 双模式切换。本文分析其命令注册机制、异常驱动流程、双级命令架构，为 Code Agent 开发者提供命令系统设计参考。
>
> **Qwen Code 对标**：双注册表设计（Soul 级 vs Shell 级）、异常作为控制流信号、Plan 模式命令、Agent ↔ Shell 模式切换

## 为什么需要双级命令注册表

### 问题定义

Code Agent 的命令在执行上下文上有本质差异：

| 需求 | 例子 | 需要代理引擎？ | 需要 UI？ | 执行方式 |
|------|------|--------------|---------|---------|
| "压缩上下文" | `/compact` | ✓ 需要 KimiSoul | — | 在代理循环内执行 |
| "切换模型" | `/model` | — | ✓ 选择对话框 | Shell 主循环执行 |
| "进入规划模式" | `/plan on` | ✓ 需要上下文 | — | 在代理循环内执行 |
| "退出程序" | `/exit` | — | — | 抛异常由 Shell 捕获 |

Soul 级命令需要直接访问 `KimiSoul`、`Context`、`Runtime` 等核心对象；Shell 级命令只需要 Shell 状态和 UI 组件。将两者混在一个注册表中会导致依赖混乱。Kimi CLI 用双注册表隔离这两种执行上下文。

### 竞品命令系统对比

| Agent | 命令数 | 命令层级 | 控制流机制 | 扩展机制 |
|-------|--------|---------|-----------|---------|
| **Kimi CLI** | 28 | 2 级（Soul + Shell） | 异常驱动（Reload/SwitchToWeb） | Skill + Plugin |
| **Claude Code** | ~79 | 4 种类型（prompt/local-jsx/local/skill） | React 组件状态 | Skill + Plugin |
| **Gemini CLI** | ~30 | 2 种（内置 + TOML） | 回调函数 | TOML + Skill |
| **Qwen Code** | ~40 | 2 种（内置 + Skill） | 回调函数 | BundledSkillLoader |

**Qwen Code 对标**：Kimi CLI 的异常驱动模式（`raise Reload`、`raise SwitchToWeb`、`raise NotImplementedError`）比回调函数更简洁——命令处理器只管 `raise`，状态转换逻辑统一在 Shell 主循环中处理。这种模式值得在需要"命令触发全局状态重置"的场景中借鉴。

---

## 命令注册基础设施

### SlashCommandRegistry\[F\]

```python
# 源码: soul/slash.py / ui/shell/slash.py
class SlashCommandRegistry(Generic[F]):
    """泛型注册表，F 为回调签名类型参数。"""
    commands: dict[str, SlashCommand]

    @registry.command(name="/xxx", description="...", aliases=["/yyy"])
    async def handler(args: str, ...) -> ...:
        ...
```

**开发者启示**：泛型参数 `F` 让 Soul 级和 Shell 级注册表的回调签名类型安全地不同——Soul 级接收 `(args, soul, context, runtime)` 四元组，Shell 级接收 Shell 状态。这比用 `**kwargs` 传递任意参数更可靠。

### SlashCommand 数据类

```python
@dataclass
class SlashCommand:
    name: str          # 主命令名（含 / 前缀）
    description: str   # 帮助文本描述
    func: F            # 异步回调
    aliases: list[str] # 别名列表
```

别名（aliases）在注册时展开为独立键指向同一 `SlashCommand` 实例。

### 异常驱动流程

| 异常 | 含义 | 触发命令 |
|------|------|----------|
| `Reload` | 重新初始化 Shell（可携带 session_id） | `/model`、`/clear`、`/new`、`/sessions`、`/login`、`/logout`、`/reload` |
| `SwitchToWeb` | 从 Shell 模式切换到 Web UI | `/web` |
| `NotImplementedError` | 退出信号（被主循环捕获） | `/exit` |

**Qwen Code 对标**：7 个命令使用 `Reload` 异常——这意味着 Kimi CLI 中约 25% 的命令需要"推倒重来"式的状态重置。这反映了一个设计选择：与其小心翼翼地局部更新状态（容易遗漏），不如直接重建整个 Shell 会话。对于配置类命令（切换模型、登录/登出），这种"全量重建"策略更安全。

---

## Soul 级命令（8 个）

Soul 级命令在代理推理循环内执行，可直接访问 `KimiSoul`、`Context`、`Runtime`。

### `/init` — 自动生成 AGENTS.md

| 属性 | 值 |
|------|-----|
| 参数 | 无 |
| 调用 LLM | 是（临时实例） |

**执行流程**：创建临时 `KimiSoul` 实例和临时 `Context`（避免污染当前会话），运行内置 `prompts.INIT` 提示词对代码库进行结构分析，生成 `AGENTS.md` 文件，最后通过 `load_agents_md()` 加载到当前运行时。

**Qwen Code 对标**：Claude Code 和 Gemini CLI 都需要用户手动创建 `CLAUDE.md` / `GEMINI.md`。Kimi CLI 的 `/init` 自动生成降低了入门门槛——这对首次使用 Code Agent 的开发者尤为重要。Qwen Code 可以考虑类似的自动化：扫描项目结构后生成初始 `QWEN.md`。

### `/compact [FOCUS]` — 上下文压缩

| 属性 | 值 |
|------|-----|
| 参数 | 可选，自然语言保留重点 |
| 调用 LLM | 是（用于摘要） |

调用 `soul.compact_context(custom_instruction=args)` 将历史对话压缩为摘要。`FOCUS` 参数允许指定保留重点（如 `/compact 保留认证模块的修改细节`）。

**Qwen Code 对标**：`FOCUS` 参数是一个有价值的细节——用户可以引导压缩过程保留关键信息，而非全凭 LLM 判断什么重要。Claude Code 的 `/compact` 也支持类似参数。Qwen Code 的压缩如果没有此能力，容易在长会话中丢失关键上下文。

### `/clear`（别名 `/reset`）— 清空上下文

调用 `soul.context.clear()` 清空所有对话历史和 checkpoint，重写系统提示词恢复初始状态。

> Shell 级也有同名 `/clear`，Shell 版本额外触发 `raise Reload` 完全重建 TUI。

### `/yolo` — 切换自动审批

Toggle `soul.runtime.approval.set_yolo(True/False)`。开启时输出 `"You only live once!"`，关闭时输出 `"You only die once!"`。YOLO 模式下所有工具调用自动审批。

### `/plan [on|off|view|clear]` — 规划模式管理

| 子命令 | 行为 |
|--------|------|
| `on` | 使用 `EnterPlanMode` 工具进入只读规划模式 |
| `off` | 使用 `ExitPlanMode` 工具退出，提交方案供用户选择 |
| `view` | 显示当前 plan 内容 |
| `clear` | 清除当前 plan |

每个 plan 会话使用独立 UUID 跟踪。无参数时 toggle `on`/`off`。

**Qwen Code 对标**：Plan 模式的核心价值在于**读写分离**——规划阶段禁用 WriteFile/Shell 等修改工具，确保 AI 不会在分析阶段就改代码。`ExitPlanMode` 支持 2-3 个方案供用户选择，这比"AI 直接执行最优方案"给了用户更多控制权。

### `/add-dir [PATH]` — 添加工作目录

验证路径合法性 → 防重复 → 添加到 `runtime.additional_dirs` → 注入系统消息（含目录文件列表）。添加后代理工具可访问该目录。

### `/export` / `/import` — 会话导入导出

将对话历史序列化为 Wire 格式文件（JSON），或从 Wire 文件恢复会话。

---

## Shell 级命令（20 个）

Shell 级命令在 TUI Shell 主循环中执行，通过异常机制触发全局状态转换。

### 会话管理组（5 个）

| 命令 | 别名 | 实现要点 |
|------|------|---------|
| `/new` | — | 创建新 Session → `raise Reload(session_id=new_id)` |
| `/sessions` | `/resume` | 列出历史会话 → ChoiceInput 选择 → `raise Reload(session_id)` |
| `/clear` | `/reset` | 委托 Soul 级 `/clear` → `raise Reload` 完全重建 |
| `/reload` | — | 直接 `raise Reload`，强制重新初始化 |
| `/web` | — | `raise SwitchToWeb(session_id)` 转到 Web UI |

### 配置管理组（4 个）

| 命令 | 别名 | 实现要点 |
|------|------|---------|
| `/model` | — | 刷新模型列表 → ChoiceInput 选模型 + 思维模式 → 保存 → `raise Reload` |
| `/editor` | — | ChoiceInput (`code --wait`/`vim`/`nano`/`auto`) → PATH 验证 → 保存 |
| `/login` | `/setup` | 选择平台 → OAuth 或 API Key → 保存 → `raise Reload` |
| `/logout` | — | 清除认证 → `raise Reload` |

### 信息查看组（5 个）

| 命令 | 别名 | 实现要点 |
|------|------|---------|
| `/help` | `/h`、`/?` | 快捷键列表 + 命令列表 + Skills 列表（Rich pager） |
| `/version` | — | 打印 `kimi_cli.constant.VERSION` |
| `/changelog` | `/release-notes` | 遍历内置 CHANGELOG 字典，Rich 分页 |
| `/debug` | — | 上下文调试：消息列表 + token 统计 + checkpoint + 轨迹 |
| `/usage` | `/status` | API 用量：向 `{base_url}/usages` 请求，Rich 进度条（绿/黄/红） |

### 其他（3 个）

| 命令 | 实现要点 |
|------|---------|
| `/exit`（别名 `/quit`） | `raise NotImplementedError`——信号机制，由 Shell 主循环捕获执行退出 |
| `/feedback` | `webbrowser.open()` 打开 GitHub Issues |
| `/task` | 打开 `TaskBrowserApp(soul)` TUI（Textual 框架），仅 root agent 可用 |
| `/mcp` | `Live` 显示（8fps 刷新）配合 `render_mcp_console()` 渲染 MCP 服务器状态 |
| `/export`/`/import`（Shell 级） | 与 Soul 级相同逻辑，额外处理 Wire 文件 I/O 和事件标记 |

---

## 键盘快捷键

| 快捷键 | 功能 | Qwen Code 对标 |
|--------|------|---------------|
| `Ctrl-X` | Agent ↔ Shell 模式切换 | Qwen Code 无此功能，参见 [01-overview](./01-overview.md) 4.1 节 |
| `Ctrl-C` | 中断当前操作 | 通用 |
| `Ctrl-D` | 退出 | 通用 |
| `Ctrl-O` | 在外部编辑器中打开输入 | Claude Code 也有此功能 |
| `Ctrl-V` | 粘贴文本/图片/视频 | 多模态输入 |
| `Ctrl-E` | 展开审批预览详情 | — |
| `Shift-Tab` | 切换 Plan 模式 | 等效 `/plan` toggle |
| `1/2/3/4` | 审批面板快捷键 | 审批/会话审批/拒绝/拒绝+反馈 |

**Qwen Code 对标**：审批面板的数字快捷键（1=审批，2=会话审批，3=拒绝，4=拒绝+反馈）是一个高效的交互设计——在频繁需要审批的工作流中，单键操作比 y/n 确认更快。`Ctrl-E` 展开预览详情也优于"全量显示或不显示"的二元选择。

---

## 命令系统设计总结

### Kimi CLI vs Claude Code 命令架构

| 维度 | Kimi CLI | Claude Code |
|------|----------|-------------|
| 命令总数 | 28 | ~79 |
| 分类策略 | 2 级（Soul + Shell） | 4 种类型（prompt/local-jsx/local/skill） |
| 注册机制 | `@registry.command` 装饰器 | 多种 Loader + BuiltinCommand |
| 控制流 | 异常驱动（Reload/SwitchToWeb） | React 状态 + 回调 |
| 扩展机制 | Skill + Plugin | Skill + Plugin |
| Plan 模式 | 独立命令（`/plan on\|off\|view\|clear`） | 无 |
| 双模式切换 | Ctrl-X（Agent ↔ Shell） | 无 |

**开发者启示**：Kimi CLI 以 28 个命令覆盖了 Claude Code 79 个命令中的大部分核心场景。差距主要在 prompt 类型命令（如 `/review`、`/commit` 等需要 LLM 参与的高级命令）和 local-jsx 类型命令（如配置管理 UI 组件）。对于新的 Code Agent 项目，28 个是一个合理的起步数量——先覆盖核心场景，再通过 Skill/Plugin 扩展。
