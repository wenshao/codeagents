# Continue

**开发者：** Continue Dev
**许可证：** Apache-2.0
**仓库：** [github.com/continuedev/continue](https://github.com/continuedev/continue)
**文档：** [docs.continue.dev](https://docs.continue.dev/)
**Stars：** 约 32k+
**最后更新：** 2026-03

## 概述

Continue 是一个开源的 AI 代码助手框架，同时支持 IDE 扩展（VS Code、JetBrains）和独立 CLI（`cn` 命令）。基于 TypeScript 构建，以 68+ LLM 提供商、37+ 上下文提供器和语义代码库索引为核心特色。独特的 PR Checks 系统（现已更名为 `cn review`）允许将代码审查规则作为 Markdown 文件纳入源码管控，并可作为 GitHub Status Check 强制执行。

## 核心功能

### 基础能力
- **多 IDE 支持**：VS Code、JetBrains、独立 CLI（`cn` 命令）
- **68+ LLM 提供商**：OpenAI、Anthropic、Gemini、Bedrock、Ollama、DeepSeek、Groq 等
- **37+ 上下文提供器**：当前文件、代码库、Git、Jira、数据库等
- **语义索引**：Tree-sitter AST + LanceDB 向量搜索
- **Tab 自动补全**：InlineCompletion 实时代码建议
- **MCP 支持**：Model Context Protocol 工具扩展
- **PR Checks / Review**：Markdown 定义的 CI/CD 代码审查规则（`cn review`）

### 独特功能
- **PR Checks 系统**：`.continue/checks/` 目录下的 Markdown 文件定义代码审查规则，可作为 GitHub Status Check 执行
- **NextEdit**：智能预测光标位置的下一步编辑
- **CodebaseRepoMap**：AST 级别代码库地图
- **角色模型选择**：default / fast / smart 三种角色分别配置模型
- **30+ 上下文提供器**：从文件、Git、Jira、数据库等注入上下文

## 技术架构（源码分析）

### 项目结构

```
continue/
├── core/              # 核心 TypeScript 库
│   ├── core.ts        # Core 类（索引、补全、配置）
│   ├── llm/llms/      # 68+ LLM 提供商实现
│   ├── tools/         # 内置工具
│   ├── context/       # 37+ 上下文提供器
│   ├── indexing/      # 语义索引系统
│   └── config/        # 配置加载
├── extensions/
│   ├── vscode/        # VS Code 扩展
│   ├── cli/           # CLI 工具（cn 命令）
│   └── intellij/      # JetBrains 扩展
├── gui/               # React WebView UI（Vite + Tailwind）
├── packages/
│   ├── config-yaml/   # YAML 配置解析
│   ├── config-types/       # 配置类型定义
│   ├── terminal-security/  # 终端安全策略
│   └── openai-adapters/    # OpenAI 格式转换
└── .continue/         # 示例配置
    ├── checks/        # PR 审查规则
    ├── agents/        # 代理定义
    └── rules/         # 编码规则
```

### 核心架构

```
IDE (VS Code / JetBrains) 或 CLI
    │
    ▼
Core 类（协议驱动的 IPC）
    ├── ConfigHandler（YAML/JSON/TS 配置）
    ├── CompletionProvider（Tab 补全）
    ├── CodebaseIndexer（语义索引）
    │   ├── CodeSnippetsIndex (Tree-sitter AST)
    │   ├── FullTextSearchIndex (SQLite FTS5)
    │   └── LanceDbIndex (向量嵌入)
    ├── 上下文提供器（37+）
    └── MCPManagerSingleton
    │
    ▼
BaseLLM（68+ 提供商）
    → streamChat() / complete()
    → Token 计数 + 成本追踪
```

### 索引系统

```
文件系统遍历
  → SHA 哈希内容寻址
  → Tree-sitter AST 提取（函数/类）
  → SQLite FTS5 全文索引
  → 向量嵌入（本地 ONNX 或云端）
  → LanceDB 向量存储
  → 增量更新（修改追踪）
```

### PR Checks 系统

```markdown
<!-- .continue/checks/security-audit.md -->
---
name: Security Audit
---

Review the code for security vulnerabilities...
Check for: SQL injection, XSS, sensitive data exposure...
```

- 作为 GitHub Status Check 运行
- CLI 命令：`cn review <pr-url>`（原 `cn checks`，已更名）
- Markdown 格式，纳入版本控制
- 可在 CI/CD 管线中强制执行

### 内置工具

| 类别 | 工具 |
|------|------|
| 文件 | readFile, readFileRange, readCurrentlyOpenFile, createNewFile, editFile, multiEdit, singleFindAndReplace |
| 搜索 | globSearch, grepSearch, searchCodebase (codebaseTool), searchWeb |
| 导航 | viewDiff, viewRepoMap, viewSubdirectory, ls |
| 终端 | runTerminalCommand（带 terminal-security 策略） |
| Web | fetchUrlContent, searchWeb |
| 配置 | createRuleBlock, requestRule, readSkill |

## 安装

```bash
# VS Code 扩展
# VS Code → 扩展 → 搜索 "Continue" → 安装

# CLI（cn 命令）
npm install -g @continuedev/cli

# CLI 命令
cn chat              # 交互式聊天
cn review <pr-url>   # 运行 PR 审查检查（原 cn checks）
cn serve             # 启动 HTTP 服务器
```

## 配置

```yaml
# ~/.continue/config.yaml
models:
  - name: claude-sonnet-4
    provider: anthropic
    apiKey: ${ANTHROPIC_API_KEY}
    roles: [default, smart]
  - name: claude-haiku-4-5
    provider: anthropic
    roles: [fast]

contextProviders:
  - name: codebase
  - name: terminal
  - name: docs

embeddingsProvider:
  provider: transformers.js  # 本地 ONNX 嵌入

tools:
  - name: runTerminalCommand
  - name: editFile
```

## 优势

1. **PR Review / Checks**：源码控制的代码审查规则，可集成 CI/CD
2. **语义索引**：AST + 向量搜索，精准上下文
3. **68+ 提供商**：最广泛的模型支持之一
4. **多 IDE 支持**：VS Code + JetBrains + CLI
5. **上下文提供器**：37+ 来源注入上下文
6. **本地嵌入**：ONNX 模型，无需云端

## 劣势

1. **复杂性高**：配置选项众多，学习曲线陡
2. **非终端原生**：CLI 是辅助，IDE 为主
3. **索引开销**：大型项目初始索引耗时
4. **文档与功能不同步**：功能迭代快，文档滞后

## 使用场景

- **最适合**：CI/CD 代码审查自动化、需要语义搜索的大型项目
- **适合**：多 IDE 团队、自定义上下文需求
- **不太适合**：简单终端工作流、快速任务

## 资源链接

- [GitHub](https://github.com/continuedev/continue)
- [文档](https://docs.continue.dev/)
- [Hub](https://hub.continue.dev/)
