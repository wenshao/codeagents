# 4. Goose 扩展与工具系统

Goose 的工具系统完全基于 MCP 协议。工具分两类：**Platform Extension**（进程内直接调用）和 **MCP Builtin Server**（子进程 MCP 通信）。

> 源码: `crates/goose/src/agents/platform_extensions/`（Platform Extension）
> 源码: `crates/goose-mcp/src/`（MCP 内置服务器）

## Platform Extension（进程内，11 个）

源码: `crates/goose/src/agents/platform_extensions/mod.rs`（`PLATFORM_EXTENSIONS` HashMap）

### 开发工具

| 扩展 | 默认启用 | 工具 | 用途 | 源码 |
|------|---------|------|------|------|
| **developer** | ✅ | `write`, `edit`, `shell`, `tree` | 文件读写编辑、Shell 执行 | `platform_extensions/developer/` |
| **analyze** | ✅ | `analyze` | 代码分析 | `platform_extensions/analyze/` |
| **todo** | ✅ | `todo_write` | 待办列表管理 | `platform_extensions/todo.rs` |
| **apps** | ✅ | `create_app`, `iterate_app`, `delete_app`, `list_apps` | 应用创建与管理 | `platform_extensions/apps.rs` |

### 代理与编排

| 扩展 | 默认启用 | 工具 | 用途 | 源码 |
|------|---------|------|------|------|
| **summon** | ✅ | `load`, `delegate` | 加载扩展/Recipe，委派任务 | `platform_extensions/summon.rs` |
| **orchestrator** | ❌（隐藏） | Agent 管理工具 | 多代理编排 | `platform_extensions/orchestrator.rs` |

### 辅助工具

| 扩展 | 默认启用 | 工具 | 用途 | 源码 |
|------|---------|------|------|------|
| **extensionmanager** | ✅ | `manage_extensions`, `search_available_extensions`, `read_resource`, `list_resources` | 扩展管理 | `platform_extensions/ext_manager.rs` |
| **chatrecall** | ❌ | `search_sessions` | 搜索历史会话 | `platform_extensions/chatrecall.rs` |
| **summarize** | ❌ | `summarize` | 摘要生成 | `platform_extensions/summarize.rs` |
| **code_execution** | ❌（feature-gated） | 代码执行工具 | 代码执行沙箱 | `platform_extensions/code_execution.rs` |
| **tom**（Top Of Mind） | ✅ | （无工具，注入上下文） | 注入最近上下文到对话 | `platform_extensions/tom.rs` |

### developer 工具详情

源码: `crates/goose/src/agents/platform_extensions/developer/`

| 工具 | 参数 | 用途 |
|------|------|------|
| `write` | `path`, `content` | 写入文件 |
| `edit` | `path`, `old`, `new` | 精确文本替换 |
| `shell` | `command`, `workdir?`, `timeout?` | 执行 Shell 命令 |
| `tree` | `path?`, `depth?` | 目录树显示 |

## MCP 内置服务器（4 个）

源码: `crates/goose-mcp/src/`（`BUILTIN_EXTENSIONS` HashMap）

### autovisualiser

源码: `crates/goose-mcp/src/autovisualiser/mod.rs`

| 工具 | 用途 |
|------|------|
| `show_chart` | 图表可视化 |
| `render_sankey` | Sankey 图 |
| `render_radar` | 雷达图 |
| `render_donut` | 环形图 |
| `render_treemap` | 树图 |
| `render_chord` | 弦图 |
| `render_map` | 地图 |
| `render_mermaid` | Mermaid 图 |

### computercontroller

源码: `crates/goose-mcp/src/computercontroller/mod.rs`

| 工具 | 用途 |
|------|------|
| `web_scrape` | Web 页面抓取 |
| `automation_script` | 自动化脚本执行 |
| `computer_control` | 计算机控制（鼠标/键盘） |
| `xlsx_tool` | Excel 文件处理 |
| `docx_tool` | Word 文件处理 |
| `pdf_tool` | PDF 文件处理 |

### memory

源码: `crates/goose-mcp/src/memory/mod.rs`

| 工具 | 用途 |
|------|------|
| `remember_memory` | 存储记忆 |
| `retrieve_memories` | 检索记忆 |
| `remove_memory_category` | 删除分类记忆 |
| `remove_specific_memory` | 删除特定记忆 |

### tutorial

源码: `crates/goose-mcp/src/tutorial/mod.rs`

教程引导工具，帮助新用户学习 Goose。

## 工具总数汇总

| 类别 | 数量 | 来源 |
|------|------|------|
| Platform Extension 工具 | ~20 | 进程内直接调用 |
| MCP Builtin 工具 | ~18 | 子进程 MCP 通信 |
| 用户 MCP 扩展 | 无上限 | Stdio/StreamableHttp/InlinePython |
| **总计（默认启用）** | **~25** | developer + analyze + todo + apps + summon + extensionmanager + tom |

## 工具执行管线

源码: `crates/goose/src/tool_inspection.rs`（`ToolInspector` trait）

```
LLM 工具调用请求
    │
    ▼
SecurityInspector → PromptInjectionScanner（Pattern + ML 检测）
    │  超过阈值 → RequireApproval
    ▼
AdversaryInspector → LLM 对抗性审查（opt-in）
    │  检测到对抗性 → 阻止
    ▼
PermissionInspector → 模式 + 用户规则 + SmartApprove
    │  denied → 阻止 / needs_approval → 等待确认
    ▼
RepetitionInspector → 重复检测
    │  超过 max_repetitions → 阻止
    ▼
ExtensionManager.call_tool() → 按工具名前缀分发
    │
    ▼
结果返回 LLM
```

## 与其他 Agent 的对比

| 特性 | Goose | Claude Code | Qwen Code |
|------|-------|-------------|-----------|
| 工具架构 | MCP 原生（所有工具通过 MCP） | 内置工具 + MCP 扩展 | 内置工具 + MCP 扩展 |
| 内置工具数 | ~20（Platform） + ~18（MCP） | 20+ | 16 |
| 扩展格式 | MCP 标准 | 插件系统 | MCP + Claude/Gemini 转换器 |
| 权限模式 | 4 种（含 SmartApprove） | 4 种 | 4 种 |
| 安全检查 | 4 层 Inspector 管道 | 沙箱 + 权限 | 权限 + 审批模式 |
