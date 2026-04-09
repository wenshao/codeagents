# 4. Goose 扩展与工具系统——开发者参考

> Goose 的工具系统完全基于 MCP 协议——~20 个 Platform Extension 工具 + ~18 个 MCP Builtin 工具。与 Claude Code 的内嵌工具不同，Goose 证明了"所有工具走 MCP"的可行性和工程权衡。
>
> **Qwen Code 对标**：Platform Extension 模式（零开销 MCP 兼容）、工具执行管线（Inspector 管道 vs 工具内安全检查）、MCP 服务器动态发现（扩展即命令）、developer 工具设计（write/edit/shell/tree）

## 为什么工具架构是 Goose 最独特的设计决策

### 问题定义

传统 Code Agent 的工具是内嵌函数——`BashTool.execute()` 直接在 Agent 进程中运行。这简单高效，但带来两个问题：

| 问题 | 影响 |
|------|------|
| 工具扩展需修改 Agent 代码 | 每次添加工具都要发版 |
| 工具生态不互通 | Claude Code 的工具不能用在 Qwen Code 中 |

Goose 的解决方案：**所有工具都是 MCP 服务器的 tool**。安装一个 MCP 服务器 = 获得一组工具，无需修改 Agent。任何 MCP 兼容的 Agent 都能使用同一个服务器。

### 竞品工具系统对比

| Agent | 内置工具数 | 工具架构 | 扩展方式 | 延迟加载 |
|-------|----------|---------|---------|---------|
| **Goose** | ~38（20 Platform + 18 MCP） | MCP 原生 | 任何 MCP 服务器 | 无 |
| **Claude Code** | 42 | 内嵌 + MCP | ToolSearch 延迟加载 + MCP | ToolSearch |
| **Qwen Code** | ~30 | 内嵌 + MCP | MCP + 转换器 | 无 |
| **Gemini CLI** | ~25 | 内嵌 + MCP | MCP + TOML | 无 |

> **注意**：Goose 的工具计数包含 Platform Extension（进程内）和 MCP Builtin Server（进程内 DuplexStream）两类。两者都在 Agent 进程内运行，但传输机制不同。

---

## Platform Extension（进程内，11 个）

源码: `crates/goose/src/agents/platform_extensions/mod.rs`（`PLATFORM_EXTENSIONS` HashMap）

Platform Extension 是 Goose 在 MCP 原生架构中保留性能的关键——它们通过直接函数调用运行在 Agent 进程内，**零 MCP 传输开销**，但对外暴露 MCP 兼容接口。

### 开发工具

| 扩展 | 默认启用 | 工具 | 用途 | Qwen Code 对标 | 源码 |
|------|---------|------|------|---------------|------|
| **developer** | ✅ | `write`, `edit`, `shell`, `tree` | 文件操作 + Shell 执行 + 目录浏览 | Write, Edit, Bash, — | `platform_extensions/developer/` |
| **analyze** | ✅ | `analyze` | 代码分析（tree-sitter AST） | Read（部分） | `platform_extensions/analyze/` |
| **todo** | ✅ | `todo_write` | 待办列表管理 | TodoWrite | `platform_extensions/todo.rs` |
| **apps** | ✅ | `create_app`, `iterate_app`, `delete_app`, `list_apps` | 应用创建/迭代/管理 | 无 | `platform_extensions/apps.rs` |

### 代理与编排

| 扩展 | 默认启用 | 工具 | 用途 | Qwen Code 对标 | 源码 |
|------|---------|------|------|---------------|------|
| **summon** | ✅ | `load`, `delegate` | 加载扩展/Recipe + 委派子任务 | Agent 工具 | `platform_extensions/summon.rs` |
| **orchestrator** | ❌（隐藏） | Agent 管理工具 | 多代理编排（实验性） | Agent Team | `platform_extensions/orchestrator.rs` |

### 辅助工具

| 扩展 | 默认启用 | 工具 | 用途 | Qwen Code 对标 | 源码 |
|------|---------|------|------|---------------|------|
| **extensionmanager** | ✅ | `manage_extensions`, `search_available_extensions`, `read_resource`, `list_resources` | 扩展的运行时管理 | 无 | `platform_extensions/ext_manager.rs` |
| **chatrecall** | ❌ | `search_sessions` | 搜索历史会话 | 无 | `platform_extensions/chatrecall.rs` |
| **summarize** | ❌ | `summarize` | 摘要生成 | 无 | `platform_extensions/summarize.rs` |
| **code_execution** | ❌（feature-gated） | 代码执行工具 | 代码沙箱执行 | 无 | `platform_extensions/code_execution.rs` |
| **tom**（Top Of Mind） | ✅ | （无工具，注入上下文） | 注入最近上下文到对话 | 无 | `platform_extensions/tom.rs` |

### developer 工具详解

源码: `crates/goose/src/agents/platform_extensions/developer/`

| 工具 | 参数 | 功能 | 与 Claude Code 对比 |
|------|------|------|-------------------|
| `write` | `path`, `content` | 写入文件（全量覆盖） | 对标 Write 工具；Claude Code 的 Write 有 23 项安全检查，Goose 依赖 Inspector 管道 |
| `edit` | `path`, `old`, `new` | 精确文本替换（old → new） | 对标 Edit 工具；Claude Code 还支持 `replace_all` 批量模式 |
| `shell` | `command`, `workdir?`, `timeout?` | 执行 Shell 命令 | 对标 Bash 工具；Claude Code 有 tree-sitter AST 命令安全校验，Goose 用 SecurityInspector |
| `tree` | `path?`, `depth?` | 目录树显示 | Claude Code 无独立 tree 工具（通过 Bash `find` 实现） |

**开发者启示**：Goose 的 developer 工具只有 4 个，而 Claude Code 有 10 个核心工具。关键缺失：
- **无 Read 工具**：Goose 通过 `shell`（`cat` 命令）读取文件，缺少 Claude Code Read 的行号范围读取能力
- **无 Grep/Glob**：代码搜索依赖 `shell`（`grep`/`find` 命令），缺少专门优化的搜索工具
- **无 Agent 工具**：子任务委派通过 `summon.delegate`，非独立 Agent 工具

这意味着 Goose 的 LLM 需要更多的 shell 命令知识来完成文件操作，而 Claude Code 通过专用工具降低了 LLM 的推理负担。

### tom（Top Of Mind）——无工具上下文注入

源码: `crates/goose/src/agents/platform_extensions/tom.rs`

tom 是一个特殊的 Platform Extension——它**没有任何工具**，只在会话开始时注入最近的上下文信息（最近文件、最近命令等）。这类似于 Claude Code 的 CLAUDE.md 自动加载，但更动态。

**Qwen Code 对标**：tom 的"无工具上下文注入"模式值得参考——不是所有 Extension 都需要提供工具，有些只需要在系统提示中注入上下文。这可以用来实现项目级知识注入、团队规范注入等功能。

---

## MCP 内置服务器（4 个）

源码: `crates/goose-mcp/src/`（`BUILTIN_EXTENSIONS` HashMap）

这些服务器通过 `Builtin` 传输（`tokio::io::DuplexStream`）运行在 Agent 进程内，延迟约 ~1ms。

### autovisualiser——数据可视化

源码: `crates/goose-mcp/src/autovisualiser/mod.rs`

| 工具 | 用途 |
|------|------|
| `show_chart` | 通用图表可视化 |
| `render_sankey` | Sankey 流向图 |
| `render_radar` | 雷达图（多维对比） |
| `render_donut` | 环形图 |
| `render_treemap` | 树图（层级数据） |
| `render_chord` | 弦图（关系数据） |
| `render_map` | 地图可视化 |
| `render_mermaid` | Mermaid 图表 |

**独特价值**：autovisualiser 是其他 CLI Code Agent 没有的功能——它让 Agent 可以在对话中生成数据可视化图表。对桌面端用户（Electron）尤其有用。

### computercontroller——系统控制

源码: `crates/goose-mcp/src/computercontroller/mod.rs`

| 工具 | 用途 |
|------|------|
| `web_scrape` | Web 页面抓取 |
| `automation_script` | 自动化脚本执行（AppleScript/Shell） |
| `computer_control` | 计算机控制（鼠标/键盘模拟） |
| `xlsx_tool` | Excel 文件解析 |
| `docx_tool` | Word 文件解析 |
| `pdf_tool` | PDF 文件解析 |

**Qwen Code 对标**：computercontroller 的文件解析工具（xlsx/docx/pdf）是实用功能。Claude Code 通过 Read 工具读取文本文件，但不支持二进制文档格式。Goose 的这些工具扩展了 Agent 可处理的文件类型。

### memory——跨会话记忆

源码: `crates/goose-mcp/src/memory/mod.rs`

| 工具 | 用途 |
|------|------|
| `remember_memory` | 存储记忆（分类+内容） |
| `retrieve_memories` | 按分类检索记忆 |
| `remove_memory_category` | 删除整个分类 |
| `remove_specific_memory` | 删除特定记忆 |

**与 Claude Code 记忆系统对比**：

| 维度 | Goose Memory | Claude Code CLAUDE.md |
|------|-------------|----------------------|
| 存储 | MCP 服务器管理（结构化分类） | Markdown 文件（用户手动编辑） |
| 检索 | 工具调用 `retrieve_memories` | 启动时自动加载 |
| 写入 | Agent 主动调用 `remember_memory` | `/memory` 命令或 Auto Dream |
| 粒度 | 分类 + 条目 | 文件级 |
| 跨项目 | 全局 | 目录级（项目/用户/团队） |

### tutorial——新用户引导

源码: `crates/goose-mcp/src/tutorial/mod.rs`

教程引导工具，帮助新用户学习 Goose。通过 `goose mcp Tutorial` 可独立运行。

---

## 工具执行管线

源码: `crates/goose/src/tool_inspection.rs`（`ToolInspector` trait）

```
LLM 返回工具调用
    │
    ▼
解析工具名前缀 → 确定目标扩展
    │
    ▼
SecurityInspector
    │ Pattern + ML 注入检测（仅 shell 工具）
    │ 超过 0.8 阈值 → RequireApproval
    ▼
AdversaryInspector
    │ LLM 对抗审查（opt-in，需 adversary.md）
    │ 审查 shell + computercontroller 工具
    ▼
PermissionInspector
    │ GooseMode → 用户权限 → SmartApprove
    │ denied → 阻止 / needs_approval → 等待确认
    ▼
RepetitionInspector
    │ 连续相同调用检测
    │ 超过 max_repetitions → 阻止
    ▼
ExtensionManager.call_tool()
    │ 按工具名前缀分发到对应 MCP 客户端
    ▼
结果返回 LLM
```

**与 Claude Code 工具执行对比**：

| 维度 | Goose | Claude Code |
|------|-------|-------------|
| **执行模式** | 顺序执行 | StreamingToolExecutor（流式解析+执行） |
| **安全检查** | 统一 Inspector 管道（4 层） | 工具内部检查（BashTool 23 项） |
| **权限** | Inspector 管道中的 PermissionInspector | 每个工具独立权限检查 |
| **工具分发** | 按名称前缀路由到 MCP 客户端 | 直接函数调用 |
| **批量执行** | 无 | 支持并行工具批次 |

**Qwen Code 对标**：Goose 的 Inspector 管道将安全检查**与工具实现解耦**——添加新安全层只需实现 `ToolInspector` trait 并注册到管道，无需修改任何工具代码。这比 Claude Code 的"每个工具内部检查"更易维护。建议 Qwen Code 参考此模式，将安全检查从工具内部抽取到统一管道。

---

## 工具总数汇总

| 类别 | 数量 | 传输方式 | 默认启用 |
|------|------|---------|---------|
| Platform Extension 工具 | ~20 | 直接函数调用 | ~15 |
| MCP Builtin 工具 | ~18 | DuplexStream | ~18 |
| 用户 MCP 扩展 | 无上限 | Stdio/StreamableHttp/InlinePython | — |
| **默认启用总计** | **~33** | — | — |

---

## MCP 原生 vs 内嵌工具——最终权衡

| 维度 | MCP 原生（Goose） | 内嵌工具（Claude Code） | 建议 |
|------|------------------|----------------------|------|
| **性能** | Platform ~0ms，Builtin ~1ms，Stdio ~10ms | 全部 ~0ms | 核心工具用 Platform，其余影响不大 |
| **扩展性** | 安装 MCP 服务器即可 | 需要 Plugin/修改代码 | MCP 显著优于内嵌 |
| **生态互通** | 跨 Agent 复用 | 专有格式 | MCP 显著优于内嵌 |
| **调试** | 每个服务器独立调试 | 需要 Agent 调试器 | MCP 更容易隔离问题 |
| **专用优化** | 受 MCP 协议限制 | 可做任意优化 | 内嵌更灵活 |
| **token 占用** | 全量注册 | ToolSearch 延迟加载 | 内嵌可优化更多 |

**结论**：Goose 的 MCP 原生架构在**扩展性和生态互通**上有结构性优势。Qwen Code 可以采取折中方案——保持核心工具内嵌（性能+专用优化），同时为所有工具暴露 MCP 兼容接口（生态互通），并参考 Goose 的 `Platform` 传输模式实现零开销 MCP 兼容层。
