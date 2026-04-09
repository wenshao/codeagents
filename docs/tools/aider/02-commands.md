# 2. Aider 命令系统——开发者参考

> Aider 共 42 个斜杠命令——与 Qwen Code 的 ~40 个持平，但注册机制截然不同。本文分析其命令分发、补全、模式切换设计，为 Code Agent 开发者提供轻量级命令系统参考。
>
> **Qwen Code 对标**：命令注册机制（cmd_ 反射 vs BuiltinCommandLoader）、SwitchCoder 异常切换 vs 直接状态修改、Tab 补全实现

## 为什么 Aider 的命令架构值得研究

### 问题定义

Code Agent 的命令系统面临一个核心权衡：**注册便捷性 vs 类型安全**。

| 方案 | 代表 | 新增命令成本 | 类型安全 | 补全支持 |
|------|------|-------------|---------|---------|
| 反射自动发现（cmd_ 前缀） | Aider | 极低（加一个方法） | 弱 | 需手动实现 |
| 注册表 + Schema | Claude Code | 中（定义 Schema + 注册） | 强 | 自动生成 |
| 装饰器 + 元数据 | Click/Typer | 中 | 中 | 自动生成 |
| BuiltinCommandLoader | Qwen Code | 中 | 中 | 框架提供 |

Aider 选择了最轻量的方案——零注册表，纯反射。这在小型代码库中极其高效，但在 42 个命令的规模下开始暴露缺陷（无法做权限控制、无法自动生成帮助文档）。

### 竞品命令系统对比

| Agent | 命令数 | 注册方式 | 模式切换 | 扩展机制 |
|-------|--------|---------|---------|---------|
| **Aider** | 42 | cmd_ 反射 | SwitchCoder 异常 | 无 |
| **Claude Code** | ~79 | 4 种类型分类注册 | 状态修改 | Skill + Plugin |
| **Gemini CLI** | ~30 | 内置 + TOML | 无等效 | TOML + Skill |
| **Qwen Code** | ~40 | BuiltinCommandLoader | 直接切换 | BundledSkillLoader |

---

## 一、命令分发机制

### cmd_ 前缀自动发现

Aider 的命令分发是 Python 中最经典的反射模式：

```python
# 源码: aider/commands.py — run() 方法
def run(self, inp):
    cmd_name = inp.split()[0].lstrip("/")        # 提取命令名
    cmd_name = cmd_name.replace("-", "_")         # /chat-mode → cmd_chat_mode
    method = getattr(self, f"cmd_{cmd_name}")     # 反射查找
    method(args)                                  # 直接调用
```

**与 Claude Code 的对比**：Claude Code 用四种类型（prompt/local-jsx/local/skill）分类注册命令，每种类型有独立的执行管道。Aider 的所有命令共享同一个执行路径——都是 `Commands` 类的方法调用。这意味着：
- 优势：新增命令只需添加一个 `cmd_xxx` 方法，零配置
- 劣势：无法按类型做权限控制（prompt 类命令调 LLM，local 类不调）、无法做延迟加载

### Tab 补全：completions_ 方法

```python
# 对应命令 /add 的补全
def completions_add(self):
    return self.coder.get_all_relative_files()    # 仓库中所有文件

# 对应命令 /drop 的补全
def completions_drop(self):
    return self.coder.get_inchat_relative_files()  # 当前聊天中的文件
```

与 `prompt_toolkit` 集成，用户按 Tab 时调用 `completions_<cmd>()` 获取候选项。非必须实现——没有 `completions_xxx` 方法的命令不提供补全。

**Qwen Code 对标**：Qwen Code 使用框架级别的补全支持（Ink 组件内建），Aider 的手动方式更灵活但需要更多代码。

### `!` 前缀快捷方式

命令解析器对 `!` 前缀做特殊处理：`!pytest` 自动转换为 `/run pytest`。这是高频 Shell 命令场景的便捷入口。

---

## 二、文件与上下文管理（8 个命令）

这组命令管理"哪些文件参与对话"——Aider 的上下文管理核心。

| 命令 | 实现规模 | 功能 | 关键细节 |
|------|---------|------|---------|
| `/add <file\|glob\|url>` | ~105 行 | 添加文件到聊天（可编辑） | 支持 glob、URL 委托 /web、不存在则确认创建 |
| `/drop [file\|glob]` | ~55 行 | 移除文件释放上下文 | 无参数移除全部，支持子串匹配 |
| `/read-only [file\|glob]` | ~89 行 | 添加只读参考文件 | 无参数将全部可编辑文件转只读，支持目录递归 |
| `/ls` | ~38 行 | 列出所有文件状态 | 三组显示：未加入/只读/可编辑 |
| `/map` | ~7 行 | 打印当前 Repo Map | 展示 Tree-sitter + PageRank 生成的结构摘要 |
| `/map-refresh` | ~5 行 | 强制刷新 Repo Map | 外部修改文件后需要手动触发 |
| `/context` | ~2 行 | 切换到上下文查看模式 | 通过 SwitchCoder 异常触发 |
| `/tokens` | ~107 行 | 报告 token 用量明细 | 逐项：系统提示/历史/Repo Map/文件，含成本估算 |

### `/add` 实现分析

`/add` 是使用频率最高的命令，其实现覆盖了多种输入类型：

- **文件路径**：绝对/相对路径，支持引号包裹（处理空格）
- **Glob 模式**：`*.py`、`src/**/*.js` 等标准 glob
- **URL**：自动委托给 `/web` 命令（Playwright 抓取 → Markdown 转换）
- **不存在的文件**：交互确认后 `touch` 创建
- **已在只读列表的文件**：自动提升为可编辑

**Qwen Code 对标**：Qwen Code 的文件添加通常通过模型调用 Read/Glob 工具实现，没有显式的 `/add` 命令。Aider 的显式文件管理让用户对上下文有完全控制权，但也增加了手动操作负担。Repo Map 机制是两种方案的折中——自动发现相关文件，减少手动 `/add` 的需求。

### `/tokens` 实现分析

`/tokens` 是 Aider 中最实用的调试命令，逐项展示 token 分布：

```
系统消息:         ~1,200 tokens
聊天历史:         ~3,400 tokens
仓库地图:         ~1,024 tokens（受 --map-tokens 限制）
可编辑文件:
  src/main.py      ~800 tokens
  src/utils.py     ~400 tokens
只读文件:
  README.md        ~200 tokens
──────────────────────────────
总计:             ~7,024 tokens（模型限制: 200k）
预估成本:         $0.021
```

**Qwen Code 对标**：Qwen Code 没有等效命令。了解 token 分布对上下文优化至关重要——用户可以据此决定 drop 哪些文件或调整 `--map-tokens` 预算。建议 Qwen Code 实现类似功能。

---

## 三、模式切换（5 个命令）

Aider 的模式切换基于 `SwitchCoder` 异常——一种值得深入分析的架构模式。

| 命令 | 功能 | 触发的 SwitchCoder 参数 |
|------|------|----------------------|
| `/chat-mode <mode>` | 切换到任意编辑模式 | `edit_format=<mode>` |
| `/code [message]` | 切换到代码编辑模式 | `edit_format=main_model.edit_format` |
| `/architect [message]` | 切换到 Architect 两阶段 | `edit_format="architect"` |
| `/ask [question]` | 切换到问答模式（不编辑） | `edit_format="ask"` |
| `/ok` | 确认建议，执行修改 | 发送确认消息，不切换模式 |

### SwitchCoder 异常模式切换

这是 Aider 最有特色的架构设计：

```python
# 模式切换不直接修改 Coder 状态，而是抛异常
class SwitchCoder(Exception):
    def __init__(self, **kwargs):
        self.kwargs = kwargs  # 携带新配置参数

# 命令层：抛出异常
def cmd_architect(self, args):
    raise SwitchCoder(edit_format="architect")

# 主循环：捕获异常，重建 Coder 实例
# 源码: aider/main.py — run() 方法
while True:
    try:
        coder.run()
    except SwitchCoder as e:
        coder = Coder.create(main_model, **e.kwargs)  # 全新实例
```

**设计优势**：
- 状态隔离彻底——新 Coder 实例不继承旧实例的任何脏状态
- 支持一次切换中同时修改多个参数（模型 + 格式 + 编辑器模型）
- 主循环逻辑极简，只需 try/except

**设计劣势**：
- 切换成本高——每次切换重建整个代理实例
- 状态传递依赖 `SwitchCoder` 的 kwargs，易遗漏

**Qwen Code 对标**：Qwen Code 的模式切换是在现有实例上修改状态，不重建。这更高效但有脏状态风险。SwitchCoder 模式适合模式间差异大（如 diff vs architect vs ask）的场景，值得在需要强隔离的切换中参考。

---

## 四、模型管理（4 个命令）

Aider 的多模型架构（主模型 / 编辑模型 / 弱模型）是其核心竞争力之一。

| 命令 | 功能 | 对应模型角色 |
|------|------|------------|
| `/model <name>` | 切换主模型 | main_model（代码生成） |
| `/editor-model <name>` | 切换编辑模型 | editor_model（Architect 模式执行层） |
| `/weak-model <name>` | 切换弱模型 | weak_model（提交消息/摘要） |
| `/models <query>` | 搜索可用模型 | 子串匹配，显示全名+提供商 |

### 三模型架构

```
用户请求
  │
  ├─ main_model（Claude Opus / GPT-4o）      ← 代码生成和推理
  │
  ├─ editor_model（Claude Sonnet）            ← Architect 模式下执行编辑
  │     仅在 /architect 模式激活
  │
  └─ weak_model（Haiku / GPT-4o-mini）        ← 提交消息、历史摘要
        辅助任务，成本降低 60%+
```

**Qwen Code 对标**：Claude Code 和 Qwen Code 目前使用单模型处理所有任务。Aider 的弱模型分离证明：提交消息生成和历史摘要这类"低智力"任务完全可以用便宜模型处理，且用户感知差异极小。这是一个投入产出比极高的优化方向。

---

## 五、Git 与工作流（8 个命令）

Git 集成是 Aider 的核心差异化能力。

| 命令 | 实现规模 | 功能 | 关键细节 |
|------|---------|------|---------|
| `/commit [msg]` | ~18 行 | 提交外部更改 | 无 msg 则 LLM 生成提交消息 |
| `/undo` | ~103 行 | 撤销上一个 aider 提交 | 5 层安全检查链 |
| `/diff` | ~39 行 | 显示上次消息以来的 diff | 使用 `commit_before_message` 定位基准 |
| `/git <cmd>` | ~25 行 | 执行任意 git 命令 | 设置 `GIT_EDITOR=true` 阻止交互 |
| `/lint [file]` | ~54 行 | Lint 检查 + 自动修复 | 克隆 Coder 实例修复，修复后自动提交 |
| `/test [cmd]` | ~19 行 | 运行测试 | 失败时输出加入聊天，触发修复 |
| `/run <cmd>` | ~41 行 | 执行 Shell 命令 | 非零退出码时提示是否加入聊天 |
| `/web <url>` | ~35 行 | 抓取网页转 Markdown | Playwright 渲染，支持动态页面 |

### `/undo` 安全检查链

`/undo` 的 103 行实现中大部分是安全检查——这是 Aider 以 Git 作安全网的核心体现：

```
1. 验证目标提交在 aider_commit_hashes 集合中（仅撤销 aider 创建的提交）
2. 检查提交未推送到远程（防止撤销已共享的提交）
3. 确认不是 merge commit
4. 确认工作区无未提交更改（防止数据丢失）
5. 执行撤销：git checkout HEAD~1 -- <files> + git reset --soft HEAD~1
```

**Qwen Code 对标**：Qwen Code 没有等效的 undo 安全链。Aider 的 Git 归因系统让它能精确区分"哪些提交是 AI 做的"，从而安全地只撤销 AI 的更改。这种设计在需要 AI 代码审计的企业场景中非常有价值。

### `/lint` 的 Coder 克隆修复

```python
# 源码: aider/commands.py — cmd_lint()
# 发现 lint 错误后，克隆当前 Coder 实例专门修复
fix_coder = self.coder.clone(cur_messages=[lint_errors])
fix_coder.run()  # 用独立 Coder 修复，不污染主对话
self.coder.auto_commit()  # 修复后自动提交
```

这种"克隆实例做修复"的模式避免了 lint 错误信息污染主对话历史——修复完成后，主 Coder 的聊天记录保持干净。

---

## 六、会话管理（5 个命令）

| 命令 | 功能 | 关键细节 |
|------|------|---------|
| `/clear` | 清空聊天历史 | 保留已添加的文件列表 |
| `/reset` | 清空全部（历史+文件） | 等价于 `/drop` + `/clear` |
| `/settings` | 显示当前配置 | 含模型元数据、编辑格式、Git 设置 |
| `/save <file>` | 保存会话状态到文件 | 生成 /drop + /add + /read-only 命令序列 |
| `/load <file>` | 从文件恢复会话 | 逐行执行命令，支持嵌套 |

### `/save` + `/load` 会话恢复

Aider 的会话恢复是命令级别的——保存的不是对话历史，而是一系列重建上下文的命令：

```
# saved-session.txt
/drop
/add src/main.py
/add src/utils.py
/read-only README.md
```

**Qwen Code 对标**：Claude Code 的会话恢复是通过崩溃检测 + 合成续行实现的（自动恢复完整上下文），Qwen Code 无等效机制。Aider 的命令级恢复是一种低成本替代方案——不保留对话历史，但能快速重建文件上下文。

---

## 七、输入输出（6 个命令）

| 命令 | 功能 | 依赖 |
|------|------|------|
| `/paste` | 粘贴图片/文本 | PIL（图片）、pyperclip（文本） |
| `/copy` | 复制最后一条 AI 回复 | pyperclip |
| `/voice` | 语音输入 | OpenAI Whisper API + sounddevice |
| `/editor` | 打开外部编辑器写消息 | `$EDITOR` 环境变量 |
| `/edit` | `/editor` 的别名 | — |
| `/multiline-mode` | 切换多行输入 | Enter 换行，Meta+Enter 提交 |

### `/voice` 实现

Aider 是少数支持语音输入的 CLI Agent：`sounddevice` 录音 → OpenAI Whisper 转文字 → 设置为下一轮输入。需要 `OPENAI_API_KEY`，与主模型提供商无关。

---

## 八、推理控制（2 个命令）

| 命令 | 功能 | 适用模型 |
|------|------|---------|
| `/think-tokens <value>` | 设置思维 token 预算 | Claude extended thinking |
| `/reasoning-effort <value>` | 设置推理努力级别 | OpenAI（low/medium/high）、其他（1-100） |

这两个命令反映了 Aider 对新模型能力的快速适配——extended thinking 和 reasoning effort 都是 2024-2025 年出现的 API 特性。

---

## 九、辅助命令（5 个）

| 命令 | 功能 | 关键细节 |
|------|------|---------|
| `/help [question]` | 查询 aider 使用帮助 | 无参数列表格，有参数用 LLM 回答 |
| `/report [title]` | 创建 GitHub Issue | 自动填充环境信息 |
| `/copy-context` | 复制完整聊天上下文 | 用于粘贴到其他 LLM 界面 |
| `/exit` | 退出 | 发送遥测事件后 sys.exit() |
| `/quit` | `/exit` 的别名 | — |

---

## 十、命令系统架构总结

### Aider vs Claude Code 命令架构对比

| 维度 | Aider | Claude Code |
|------|-------|-------------|
| 命令总数 | 42 | ~79 |
| 注册机制 | cmd_ 反射（零配置） | 4 种类型分类注册 |
| 代码位置 | 单文件 commands.py（1712 行） | 101 个目录（每命令一文件） |
| 模式切换 | SwitchCoder 异常重建实例 | 状态修改 |
| 权限控制 | 无 | 按命令类型 + 用户设置 |
| Tab 补全 | completions_ 手动方法 | 自动生成 |
| 扩展机制 | 无（需修改源码） | Skill + Plugin |
| LLM 调用 | 混在命令方法中 | prompt 类型独立管道 |

**开发者结论**：Aider 的命令系统是"小而美"的典范——42 个命令压缩在 1712 行中，反射分发零配置，SwitchCoder 异常优雅地解决了模式切换的状态一致性问题。但在扩展性（无插件机制）、安全性（无权限控制）、类型安全（无 Schema 校验）上存在明显短板。Qwen Code 在这些维度已经领先，但 Aider 的 SwitchCoder 模式和弱模型分离策略值得参考。
