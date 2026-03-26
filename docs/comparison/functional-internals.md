# 4. 功能性内部机制对比

> 从源码和二进制中提取的各工具 API 参数、代理循环、编辑格式、上下文管理等核心功能性实现对比。

## 1. API 调用参数

| Agent | Temperature | Max Tokens | Top-P | 重试策略 | 请求超时 |
|------|------------|-----------|-------|----------|----------|
| **Claude Code** | 0（分类器/安全），1（对话） | 4096（分类器），默认由模型决定 | — | 指数退避（`maxRetries` 125 refs） | — |
| **Copilot CLI** | 0（工具调用），1（对话） | 1024（某些场景） | — | — | — |
| **Codex CLI** | 可配置（config.toml `temperature`） | 可配置（`max_output_tokens`） | — | — | — |
| **Aider** | **0**（默认），推理模型禁用 | 模型默认 | — | 指数退避 0.125s→60s | 600s |
| **Gemini CLI** | 0（base/分类器），1（chat），0.2-0.3（辅助） | 1,048,576（Gemini 模型上限） | 1（base），0.95（chat） | 10 次，5s→30s 指数退避 | — |
| **Kimi CLI** | 可配置（`KIMI_MODEL_TEMPERATURE`） | 50,000（Anthropic 默认） | 可配置 | tenacity 指数抖动 0.3s→5s，3 次 | — |
| **Goose** | None（默认），可配置（`GOOSE_TEMPERATURE`） | None（默认），可配置 | — | `RetryManager` 可配置 | 300s（recipe） |
| **Qwen Code** | 继承 Gemini（0/1） | 继承 Gemini | 继承 | 继承 Gemini（10 次退避） | — |
| **OpenCode** | 可配置 | 可配置 | — | — | — |

> **关键发现：** Temperature=0 是 Claude Code、Copilot CLI、Aider、Gemini CLI 的默认值（确保确定性输出）。对话模式通常切换到 Temperature=1。

## 2. 代理循环控制

| Agent | 最大迭代 | 反射/重试 | 停止条件 | 循环架构 |
|------|---------|-----------|---------|----------|
| **Claude Code** | `maxTurns`（74 refs，值可配置） | 安全分类器双阶段检查 | `end_turn` / `stop_sequence` | 工具调用循环，直到模型停止 |
| **Copilot CLI** | 可配置（`max-autopilot-continues`） | — | `end_turn` / `stop_reason` | Agent → Tool → Response 循环 |
| **Codex CLI** | 可配置 | Guardian Approval 检查 | 模型决定 | 响应式循环 |
| **Aider** | **无固定上限** | **3 次反射**（lint/test 失败→反馈→重试） | 模型不再调用工具 | `run()→run_one()→send_message()` |
| **Gemini CLI** | **100 轮**（`MAX_TURNS = 100` 硬编码） | 工具失败重试 | 轮次耗尽或模型停止 | `generateContent()→processTurn()→handleToolCalls()` |
| **Kimi CLI** | **100 步/轮**（`max_steps_per_turn=100`） | **3 次/步**（tenacity 指数退避） | 步数耗尽或模型停止 | `KimiSoul.step()` 循环 |
| **Goose** | **无固定上限** | `RetryManager` 可配置 | 模型决定 | Rust async 循环 |
| **Qwen Code** | **100 轮**（继承 Gemini） | 继承 Gemini | 继承 Gemini | 继承 Gemini + Loop 检测（Levenshtein） |
| **OpenCode** | 可配置 | SQLite 追踪 + Doom Loop 保护（3 次拒绝中断） | 模型决定 | Go async 循环 |

> **关键发现：** Aider 独有的"反射循环"机制（`max_reflections=3`）——lint/test 失败后自动将错误反馈给模型重试，是其自动修复能力的核心。

## 3. 编辑格式

### Aider（14 种，业界最多）

| 格式 | 文件 | 说明 |
|------|------|------|
| `diff` | `editblock_coder.py` | 搜索/替换块 |
| `diff-fenced` | `editblock_fenced_coder.py` | 带围栏的搜索/替换 |
| `whole` | `wholefile_coder.py` | 输出完整文件内容 |
| `udiff` | `udiff_coder.py` | Unified diff 格式 |
| `udiff-simple` | `udiff_simple_coder.py` | 简化 unified diff |
| `patch` | `patch_coder.py` | Git patch 格式 |
| `architect` | `architect_coder.py` | 架构师模式（规划→编辑双模型） |
| `ask` | `ask_coder.py` | 只读问答（不编辑） |
| `context` | — | 上下文查看 |
| `help` | `help_coder.py` | 帮助系统 |
| `editor-diff` | `editor_editblock_coder.py` | 编辑器模式的搜索/替换 |
| `editor-whole` | `editor_wholefile_coder.py` | 编辑器模式的完整文件 |
| `editor-diff-fenced` | `editor_diff_fenced_coder.py` | 编辑器模式的围栏搜索/替换 |
| function-calling | 通过 API function calling | 结构化工具调用 |

### 其他工具

| Agent | 格式 | 说明 |
|------|------|------|
| **Claude Code** | `Edit`（old_string→new_string） + `Write`（完整文件） + `MultiEdit`（多处编辑） | 3 种互补工具，模型自行选择 |
| **Copilot CLI** | `edit`（差异） + `replace`（替换） + `create`（创建） + `apply_patch`（补丁） | 4 种工具 |
| **Codex CLI** | `apply_patch`（主要） + `LocalShellCall` | Codex 模型使用 apply-patch 专用格式 |
| **Gemini CLI** | `edit`（搜索/替换） + `write_file`（创建/覆写） | 2 种工具 |
| **Kimi CLI** | `EditFile` + `WriteFile` | 2 种工具 |
| **Goose** | 通过 MCP 工具（无内置编辑格式） | 完全依赖 MCP 服务器 |
| **Qwen Code** | 继承 Gemini `edit` + `write_file` | 2 种工具（继承） |
| **OpenCode** | `edit` + `apply_patch`（GPT 专用）+ `write` | 按模型切换编辑策略 |

## 4. 上下文管理

| Agent | 上下文窗口 | 压缩触发 | 压缩算法 | 仓库索引 |
|------|-----------|---------|---------|---------|
| **Claude Code** | 1M（Opus 4.6[1m]） | ~95% 容量 | 三层（微压缩+自动+手动），`<summary>` 标签 | `file-index.node`（原生索引） |
| **Copilot CLI** | 模型依赖 | `backgroundCompactionThreshold` | 无限会话 + 后台压缩，保留检查点标题 | ripgrep 搜索 |
| **Codex CLI** | 模型依赖 | `auto_compact_token_limit` | 可配置 `compact_prompt` | ripgrep |
| **Aider** | 模型依赖 | `done_messages > 1024 tokens` | 递归分割摘要（3 层深度，后台线程） | **Tree-sitter PageRank**（867 行算法） |
| **Gemini CLI** | 1M（Gemini） | **50% 容量** | 四阶段（截断+分割+摘要+验证），专用压缩模型 | `codebase_investigator` 子代理 |
| **Kimi CLI** | 模型依赖 | **85% 容量**或剩余 <50K | 结构化摘要（6 个 XML 章节），自定义焦点 | `/init` 生成 AGENTS.md |
| **Goose** | 模型依赖 | **80%**（`GOOSE_AUTO_COMPACT_THRESHOLD`，[官方文档](https://block.github.io/goose/docs/guides/sessions/smart-context-management/)） | 工具调用摘要（每 10 个批量） | 无 |
| **Qwen Code** | ~1M（继承 Gemini） | **50%**（继承） | 四阶段（继承 Gemini）+ 简单断路器（布尔标志） | 继承 Gemini |
| **OpenCode** | 模型依赖 | 可配置 | 会话压缩 | Tree-sitter（实验性 LSP） |

> **关键发现：** Gemini CLI 的四阶段压缩最复杂（含独立验证步骤），但 Aider 的 Tree-sitter PageRank 仓库地图是理解代码结构最深的方案。

## 5. Prompt Caching（提示缓存）

| Agent | 缓存机制 | 证据 |
|------|---------|------|
| **Claude Code** | Anthropic `cache_control: ephemeral` | 二进制中 `cache_control` 引用数因版本而异（v2.1.81=47，v2.1.83=83） |
| **Copilot CLI** | 未确认 | — |
| **Codex CLI** | OpenAI 服务端缓存 | `enable_request_compression` flag |
| **Aider** | Anthropic prompt caching（通过 litellm） | 源码 `send_message` 中设置 cache headers |
| **Gemini CLI** | Google `cachedContent` API | 源码中 `cacheControl` 配置 |
| **Kimi CLI** | 未确认 | — |
| **Goose** | 未确认 | — |
| **Qwen Code** | DashScope 缓存（`enableCacheControl`） | 继承 Gemini |
| **OpenCode** | 未确认 | — |

## 6. 工具调用策略

| Agent | 并行调用 | 调用上限 | 工具选择 |
|------|---------|---------|---------|
| **Claude Code** | ✓（Agent 工具支持并行子代理） | 无固定上限 | 模型自行选择 |
| **Copilot CLI** | ✓（`multi_tool_use.parallel`） | 无固定上限 | 模型选择，Codex 模型用 apply-patch |
| **Codex CLI** | ✓（`supports_parallel_tool_calls` flag） | 无固定上限 | 模型选择 |
| **Aider** | ✗（串行） | 无 | 模型选择编辑格式 |
| **Gemini CLI** | ✓ | 无固定上限 | 模型选择 |
| **Kimi CLI** | ✗（串行，但有后台任务） | `max_steps_per_turn=100` | 模型选择 |
| **Goose** | ✓ | 无固定上限 | 模型选择（toolshim 兼容层） |
| **Qwen Code** | ✓（继承 Gemini） | 继承 | 继承 Gemini |
| **OpenCode** | ✓ | — | 模型选择 |

## 证据来源

| Agent | 分析方法 |
|------|---------|
| Claude Code | `strings` 二进制提取 API 参数常量 |
| Copilot CLI | `grep` index.js minified 源码 |
| Codex CLI | `strings` Rust 二进制 + `codex --help` |
| Aider | `gh api` GitHub 源码（base_coder.py, models.py, history.py） |
| Gemini CLI | `gh api` GitHub 源码（client.ts, defaultModelConfigs.ts） |
| Kimi CLI | `gh api` GitHub 源码（kimisoul.py, config.py） |
| Goose | `gh api` GitHub 源码（agent.rs, model.rs） |
| Qwen Code | cli.js 二进制 strings（v0.13.0） |
| OpenCode | Go ELF 二进制 strings（v1.2.15） |
