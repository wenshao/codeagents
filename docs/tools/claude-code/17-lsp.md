# 17. LSP 客户端——开发者参考

> Claude Code 内置 LSP（Language Server Protocol）客户端，连接项目的语言服务器获取类型信息、诊断结果、符号定义。这为 Agent 提供了**编译器级别的代码理解**，超越纯文本搜索。
>
> **Qwen Code 对标**：Qwen Code 有实验性 LSP 支持（`--experimental-lsp` 启动参数），但默认关闭。Claude Code 的 LSP 集成更成熟。

## 一、为什么 Code Agent 需要 LSP

### 问题定义

Agent 的 `grep_search` 工具是文本级搜索——它不理解代码语义：

| 任务 | grep_search | LSP |
|------|------------|-----|
| "找到 `getUserById` 的定义" | 搜索字符串"getUserById"——可能匹配注释、字符串、导入 | `textDocument/definition` → 精确跳转到定义 |
| "这个函数的参数类型是什么" | 无法获得 | `textDocument/hover` → 完整类型签名 |
| "这个文件有编译错误吗" | 无法获得 | `textDocument/publishDiagnostics` → 错误列表 |
| "重命名这个变量的所有引用" | grep 可能遗漏（动态引用、别名） | `textDocument/references` → 语义级全量引用 |

### 实际价值

LSP 最大的价值不是让 Agent "更聪明"（LLM 已经能理解代码），而是提供**确定性的编译器诊断**：

- TypeScript 的类型错误
- Python 的导入错误
- Java 的编译错误
- 未使用变量、未解析引用

这些信息如果能自动注入 Agent 的上下文，等价于"Agent 自带编译器"——不需要手动跑 `tsc --noEmit` 就能发现类型错误。

## 二、Claude Code 的 LSP 实现

源码: `services/lsp/`（7 个文件）

### 核心功能

| 能力 | LSP 方法 | Agent 如何使用 |
|------|---------|---------------|
| 诊断（错误/警告） | `textDocument/publishDiagnostics` | 编辑后自动获取编译错误 |
| 跳转定义 | `textDocument/definition` | 理解函数/类的实现位置 |
| 查找引用 | `textDocument/references` | 确定影响范围 |
| 悬停信息 | `textDocument/hover` | 获取类型签名 |
| 符号搜索 | `workspace/symbol` | 按名称搜索项目符号 |

### 竞品 LSP 对比

| Agent | LSP 支持 | 默认启用 | 实现方式 |
|-------|---------|---------|---------|
| **Claude Code** | ✓ | 实验性 | 内置 LSP 客户端 |
| **Gemini CLI** | — | — | — |
| **Qwen Code** | ✓ `--experimental-lsp` | 默认关闭 | 内置 LSP 客户端 |
| **Cursor** | ✓ | ✓ | 继承 VS Code 的完整 LSP 支持 |
| **Copilot CLI** | — | — | — |

## 三、Qwen Code 改进建议

LSP 的核心价值是**诊断自动注入**——编辑文件后自动获取编译错误并注入上下文。建议：

1. 默认启用 LSP（至少对 TypeScript/Python 项目）
2. 将 `publishDiagnostics` 结果自动附加到 `PostToolUse(Edit)` 的工具输出中
3. 长期：结合 `/review` 使用 LSP 诊断替代 LLM 检测类型错误
