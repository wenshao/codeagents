# Qwen Code 改进建议 — P0/P1 详细说明

> 最高优先级改进项。每项包含：思路概述、Claude Code 源码索引（方便查找参考）、Qwen Code 修改方向。
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md)

---

<a id="item-1"></a>

### 1. 多层上下文压缩（P0）

**思路**：不做一次性全量摘要，而是分层递进——先清旧工具结果（MicroCompact），再自动触发全量摘要（~93% 阈值），最后记忆感知压缩。大多数场景 MicroCompact 就够。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `services/compact/microCompact.ts` (531行) | `COMPACTABLE_TOOLS` Set（8 种可清除工具）、`consumePendingCacheEdits()` |
| `services/compact/autoCompact.ts` | `AUTOCOMPACT_BUFFER_TOKENS = 13_000`（~93% 触发） |
| `services/compact/compact.ts` (1705行) | `compactConversation()`、`POST_COMPACT_MAX_FILES_TO_RESTORE = 5` |
| `services/compact/prompt.ts` | 9 章节摘要 Prompt 模板 |

**Qwen Code 修改方向**：在 `chatCompressionService.ts` 新增 `microCompact()` 方法，在 `agent-core.ts` 的 `processFunctionCalls()` 后调用；`tryCompressChat()` 改为 93% 自动触发。

**相关文章**：[上下文压缩深度对比](./context-compression-deep-dive.md)

---

<a id="item-2"></a>

### 2. Fork 子代理（P0）

**思路**：省略 `subagent_type` 时自动 fork——子代理继承完整对话历史 + 系统提示 + 工具集。所有 fork 使用相同占位 tool_result 文本，确保 API 请求前缀字节一致 → prompt cache 共享（5 个子代理省 80%+ token）。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `tools/AgentTool/forkSubagent.ts` (210行) | `isForkSubagentEnabled()`、`FORK_AGENT` 定义、`buildForkedMessages()`、`buildChildMessage()`（10 条铁律） |
| `tools/AgentTool/AgentTool.tsx` (1397行) | fork vs 常规决策树（L318-L356）、`override.systemPrompt` 传递 |
| `tools/AgentTool/runAgent.ts` (973行) | `useExactTools: true`（跳过工具过滤）、thinking config 继承 |
| `utils/forkedAgent.ts` (689行) | `CacheSafeParams` 类型、`saveCacheSafeParams()` |

**Qwen Code 修改方向**：`agent.ts` 中将 `subagent_type` 改为可选；新增 `forkSubagent.ts` 实现消息构建（克隆 assistant message + 统一占位 tool_result + 指令注入）。

**相关文章**：[Fork 子代理 Deep-Dive](./fork-subagent-deep-dive.md)

---

<a id="item-3"></a>

### 3. Speculation 默认启用（P1）

**思路**：Qwen Code v0.15.0 已实现完整 speculation 系统，但 `enableSpeculation` 默认关闭。核心工作是评估安全性后默认开启，并扩大 `speculationToolGate` 的 safe 工具覆盖。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `services/PromptSuggestion/speculation.ts` (991行) | `startSpeculation()`、`acceptSpeculation()`、overlay 文件系统 |
| `services/PromptSuggestion/promptSuggestion.ts` | `shouldFilterSuggestion()`（12 条过滤规则） |

**Qwen Code 修改方向**：`settingsSchema.ts` 中 `enableSpeculation` 默认值 `false` → `true`；`speculationToolGate.ts` 扩大 safe 工具列表。

**相关文章**：[Prompt Suggestions](../tools/claude-code/10-prompt-suggestions.md)、[输入队列](./input-queue-deep-dive.md)

---

<a id="item-4"></a>

### 4. 会话记忆 SessionMemory（P1）

**思路**：session 结束时自动提取关键决策/文件结构/技术栈信息，持久化到 `.qwen/memory/`。新 session 启动时检索相关记忆并注入系统提示。与 compact 协同——压缩时保留已提取记忆。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `services/SessionMemory/sessionMemory.ts` | 会话记忆提取 + 存储 |
| `services/SessionMemory/prompts.ts` | 记忆提取 Prompt |
| `memdir/findRelevantMemories.ts` | 相关性检索 |
| `memdir/memdir.ts` | `loadMemoryPrompt()`（200 行 / 25KB 截断） |

**Qwen Code 修改方向**：新建 `services/sessionMemoryService.ts`；在 session 结束的 hook 中调用提取逻辑；`prompts.ts` 的 `getCustomSystemPrompt()` 注入检索结果。

**相关文章**：[记忆系统深度对比](./memory-system-deep-dive.md)

---

<a id="item-5"></a>

### 5. Auto Dream 自动记忆整理（P1）

**思路**：双门控（24h + 5 session）满足时，后台 fork 只读 agent 整理记忆——合并重复、删除过时、解决矛盾。文件锁防止多进程并发。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `services/autoDream/autoDream.ts` (324行) | 门控逻辑、forked agent 调度 |
| `services/autoDream/consolidationPrompt.ts` | 整理 Prompt 模板 |
| `services/autoDream/consolidationLock.ts` | 文件锁防并发 |

**Qwen Code 修改方向**：新建 `services/autoDream/`；在 `SessionStart` hook 中检查门控条件；满足时 fork 后台 agent 执行整理。

**相关文章**：[记忆系统深度对比](./memory-system-deep-dive.md)

---

<a id="item-6"></a>

### 6. Mid-Turn Queue Drain（P0）

**思路**：在推理循环中每个工具批次执行完后、下一次 API 调用前，检查命令队列并将用户输入注入 toolResults——模型在当前 turn 的下一个 step 即可看到新指令，无需等整轮结束。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `query.ts` (L1550-L1643) | `getCommandsByMaxPriority()`、`getAttachmentMessages()`、`removeFromQueue()` |
| `utils/messageQueueManager.ts` | 优先级队列（`now`/`next`/`later`）、`dequeue()` 带 filter |

**Qwen Code 修改方向**：在 `agent-core.ts` 的 `processFunctionCalls()` 返回后、下一轮 `while` 迭代前，调用 `queue.dequeue()` 并将消息注入到下一次 API 调用的 history 中。

**相关文章**：[输入队列与中断机制](./input-queue-deep-dive.md) | **进展**：[PR#2854](https://github.com/QwenLM/qwen-code/pull/2854)

---

<a id="item-7"></a>

### 7. 智能工具并行（P1）

**思路**：每个工具实现 `isConcurrencySafe(input)` 方法。连续的并发安全工具合并为一个并行批次（上限 10），遇到写工具则独立串行。并行时上下文修改队列化，批次结束后串行应用。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `services/tools/toolOrchestration.ts` (188行) | `partitionToolCalls()`、`runToolsConcurrently()`、`runToolsSerially()` |
| `services/tools/StreamingToolExecutor.ts` (530行) | `canExecuteTool()`、Bash 错误级联（`siblingAbortController`） |
| `Tool.ts` (L402) | `isConcurrencySafe()` 接口 |

**Qwen Code 修改方向**：`coreToolScheduler.ts` 中将 `otherCalls` 的顺序执行改为按 `kind` 分批并行；在 `tools.ts` 基类新增 `isConcurrencySafe` 属性（read 工具默认 true）。

**相关文章**：[工具并行执行](./tool-parallelism-deep-dive.md) | **进展**：[PR#2864](https://github.com/QwenLM/qwen-code/pull/2864)

---

<a id="item-8"></a>

### 8. 启动优化（P1）

**思路**：两个独立优化——① API Preconnect：启动时 fire-and-forget HEAD 请求预热 TCP+TLS（省 100-200ms）；② Early Input：REPL 未就绪时 raw mode 捕获键盘输入，就绪后预填充。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/apiPreconnect.ts` (71行) | `preconnectAnthropicApi()`（fire-and-forget HEAD） |
| `utils/earlyInput.ts` (191行) | `startCapturingEarlyInput()`、`consumeEarlyInput()`、`processChunk()` |

**Qwen Code 修改方向**：`gemini.tsx` 入口最早处调用 preconnect（DashScope/Gemini 端点）；新增 `earlyInput.ts` 在 `process.stdin.setRawMode(true)` 下捕获，`AppContainer` mount 时 consume。

**相关文章**：[启动阶段优化](./startup-optimization-deep-dive.md)

---

<a id="item-9"></a>

### 9. 指令条件规则（P1）

**思路**：`.qwen/rules/*.md` 支持 YAML frontmatter `paths:` glob 模式——有 `paths:` 的规则仅在操作匹配文件时惰加载，其余急加载。支持 HTML 注释剥离（作者注释不进 token 预算）。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/claudemd.ts` (1479行) | `processMdRules()`、`@include` 指令解析、HTML 注释剥离 |
| `utils/frontmatterParser.ts` | `paths:` glob 解析（`ignore` 库 picomatch） |

**Qwen Code 修改方向**：`memoryImportProcessor.ts` 新增 frontmatter 解析；`memoryDiscovery.ts` 区分急/惰加载；文件操作时触发条件规则检查。

**相关文章**：[指令文件加载](./instruction-loading-deep-dive.md)

---

<a id="item-10"></a>

### 10. Team Memory 组织级记忆（P2→Top20）

**思路**：per-repo 级别团队记忆同步——API pull/push（ETag + SHA256 per-key 校验和）、Delta 上传（仅变更 key）、fs.watch 2s debounce 实时推送。上传前 29 条 gitleaks 规则密钥扫描。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `services/teamMemorySync/index.ts` | delta sync 编排、`MAX_PUT_BODY_BYTES = 200KB` 批次 |
| `services/teamMemorySync/secretScanner.ts` | 29 条 gitleaks 规则 |
| `services/teamMemorySync/watcher.ts` | fs.watch + 2s debounce |
| `memdir/teamMemPrompts.ts` | private + team 双目录提示构建 |

**Qwen Code 修改方向**：新建 `services/teamMemorySync/`；API 端点对接阿里云/自建后端；`memoryTool.ts` 扩展为 private/team 双目录。

**相关文章**：[Team Memory 深度对比](./team-memory-deep-dive.md)

---

<a id="item-11"></a>

### 11. 工具动态发现 ToolSearchTool（P1）

**思路**：系统提示仅注入核心工具（~10 个），其余标记为 deferred。模型需要时调用 ToolSearch（keyword 或 `select:` 模式）按需加载——省 50%+ 系统提示 token。MCP 工具始终 deferred。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `tools/ToolSearchTool/ToolSearchTool.ts` (472行) | keyword 评分（MCP 12/6分, 普通 10/5分）、`select:` 直接选择 |
| `tools/ToolSearchTool/prompt.ts` | `isDeferredTool()` 分类逻辑、`alwaysLoad` 豁免 |

**Qwen Code 修改方向**：工具注册表新增 `deferred: boolean` 属性；新建 `tools/toolSearch.ts`；`coreToolScheduler.ts` 在工具 schema 注入时过滤 deferred 工具。

**相关文章**：[工具搜索与延迟加载](./tool-search-deep-dive.md)

---

<a id="item-12"></a>

### 12. Commit Attribution（P1）

**思路**：跟踪每个文件的 AI vs 人类字符贡献比例（diff 前缀/后缀匹配），commit 消息自动追加 `Co-Authored-By`，attribution 元数据存 git notes。内部模型名在外部仓库自动清理为公开名。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/commitAttribution.ts` (961行) | 按文件字符归因、`INTERNAL_MODEL_REPOS` 清理 |
| `utils/attributionTrailer.ts` | Co-Authored-By 注入 |

**Qwen Code 修改方向**：新建 `utils/commitAttribution.ts`；在 `shell.ts` 检测到 `git commit` 时注入 trailer。

**相关文章**：[Git 工作流与会话管理](./git-workflow-session-deep-dive.md)

---

<a id="item-13"></a>

### 13. 会话分支 /branch（P1）

**思路**：fork 当前 transcript JSONL 为新 session——保留完整历史 + `forkedFrom: { sessionId, messageUuid }` 溯源。自动命名 "(Branch)"，分支成为活跃 session，原始可 `--resume`。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `commands/branch/branch.ts` (296行) | `getUniqueForkName()`、transcript 复制 + `forkedFrom` 元数据 |

**Qwen Code 修改方向**：新建 `/branch` 命令；`sessionService.ts` 新增 `forkSession()` 方法（复制 JSONL + 写入 forkedFrom）。

**相关文章**：[Git 工作流与会话管理](./git-workflow-session-deep-dive.md)

---

<a id="item-49"></a>

### 49. Channels 消息推送（P1）

**思路**：通过 MCP 协议的 channel 插件接收外部消息（Telegram/Discord/iMessage/webhook）。channel 插件注册 `--channels` 参数，sender allowlist 控制谁能推送。双向——Claude 回复通过同一 channel 返回。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| 插件: `claude-plugins-official/external_plugins/telegram/` | Telegram bot 轮询 + 配对码 + allowlist |
| `services/mcp/client.ts` | channel 注册 + 消息路由 |

**Qwen Code 修改方向**：扩展现有 MCP plugin 框架支持 `channel` 类型；新增 `--channels` CLI 参数；`AppContainer.tsx` 处理入站 channel 消息。

---

<a id="item-50"></a>

### 50. GitHub Actions CI（P1）

**思路**：官方 GitHub Action 封装 `claude -p` headless 模式——PR 创建时自动触发 review、issue 创建时自动分类。支持 `--allowedTools` 白名单和 `--permission-mode dontAsk`。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| 外部: `anthropics/claude-code-action` | GitHub Action YAML + headless 调用 |
| `cli/print.ts` (5594行) | `runHeadless()` — headless 执行入口 |

**Qwen Code 修改方向**：创建 `qwenlm/qwen-code-action` GitHub Action；核心是调用 `qwen-code -p --allowedTools "Read,Bash" --output-format json`。

---

<a id="item-51"></a>

### 51. GitHub Code Review 多代理审查（P1）

**思路**：多 Agent 并行审查 PR 不同文件——每个 Agent 检查一类问题（逻辑错误/安全漏洞/边界情况），验证步骤过滤误报，结果去重排序后发 inline 评论。可配合 `REVIEW.md` 定制审查规则。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| 托管服务（非本地源码） | 多 Agent 并行 + 验证 + 去重 |
| `code-review.md` 官方文档 | severity: 🔴 Important / 🟡 Nit / 🟣 Pre-existing |

**Qwen Code 修改方向**：基于已有 `/review` Skill 扩展——fork 多个 Agent 各审查一组文件；`gh api` 发 inline 评论；新增 `REVIEW.md` 支持。

---

<a id="item-52"></a>

### 52. HTTP Hooks（P1）

**思路**：Hook 除了 `type: "command"`（shell）外，支持 `type: "http"` —— POST JSON 到 URL 并接收 JSON 响应。适合与 CI、审批系统、消息平台直接集成，无需 shell 中转。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/hooks/hookRunner.ts` | HTTP hook 执行（fetch POST + JSON parse） |
| `types/hooks.ts` | `HookConfig.type` 支持 `'command'` 和 `'http'` |

**Qwen Code 修改方向**：`hookRunner.ts` 新增 HTTP 分支——`type === 'http'` 时 fetch POST body（hook input JSON），解析 response JSON 作为 hook output。

---

<a id="item-58"></a>

### 58. Structured Output --json-schema（P1）

**思路**：headless 模式 `--json-schema` 参数注入 SyntheticOutputTool——强制模型调用该工具输出结构化数据，Ajv 运行时验证 schema。不通过则重试。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `tools/SyntheticOutputTool/SyntheticOutputTool.ts` | Ajv 验证 + WeakMap schema 缓存 |
| `main.tsx` | `--json-schema` CLI 参数解析 + `--output-format json` |

**Qwen Code 修改方向**：新建 `tools/structuredOutput.ts`；`nonInteractiveCli.ts` 新增 `--json-schema` 参数；headless 模式注入该工具到工具列表。

---

<a id="item-59"></a>

### 59. Agent SDK Python（P1）

**思路**：Qwen Code 已有 TypeScript SDK（`@qwen-code/sdk`），缺 Python SDK。Claude Code 提供 Python + TS 双语言 SDK，支持流式回调和工具审批回调。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `entrypoints/sdk/` | SDK 类型定义、消息映射 |
| 外部: `anthropics/claude-code-sdk-python` | Python 包 |

**Qwen Code 修改方向**：新建 `packages/sdk-python/`；封装 subprocess 调用 `qwen-code -p --output-format stream-json`；提供 `QwenCodeAgent` class + async generator API。

---

<a id="item-60"></a>

### 60. Bare Mode --bare（P1）

**思路**：`--bare` 跳过所有自动发现（hooks/LSP/plugins/auto-memory/CLAUDE.md/OAuth/keychain），仅通过 CLI 显式参数传入上下文。CI 确定性执行——每台机器同样结果。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `entrypoints/cli.tsx` (L283) | `CLAUDE_CODE_SIMPLE=1` 设置 |
| `main.tsx` (L394) | 跳过所有 prefetch |

**Qwen Code 修改方向**：`gemini.tsx` 新增 `--bare` flag；设置 `QWEN_CODE_SIMPLE=1` 环境变量；各模块在 `SIMPLE` 模式下跳过自动发现。

---

<a id="item-61"></a>

### 61. Remote Control Bridge（P1）

**思路**：终端 Agent 注册到服务端（WebSocket），用户通过 Web/手机驱动本地 session。Outbound-only 模式——终端主动推事件，不接受入站连接。支持权限审批远程转发。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `bridge/bridgeMain.ts` | WebSocket 连接 + 事件转发 |
| `bridge/bridgeApi.ts` | API 端点交互 |
| `bridge/bridgeConfig.ts` | 配置 + 环境注册 |

**Qwen Code 修改方向**：新建 `packages/core/src/bridge/`；对接阿里云/自建 WebSocket 服务；`/remote-control` 命令启动桥接。

---

<a id="item-62"></a>

### 62. /teleport 跨平台迁移（P1）

**思路**：Web session 完成后 `/teleport` 到终端——fetch 远程分支 + checkout + 加载完整会话历史。前提：同 repo、clean git state、同账号。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/teleport.tsx` | 交互式 session picker |
| `utils/teleport/api.ts` | 远程 session 列表 API |
| `utils/teleport/gitBundle.ts` | git fetch + checkout |

**Qwen Code 修改方向**：需先有 Web 版本；新增 `/teleport` 命令；调用 API 获取 session 列表 → fetch branch → 加载历史。

---

<a id="item-63"></a>

### 63. GitLab CI/CD 集成（P1）

**思路**：官方 GitLab pipeline 集成——MR 创建时自动触发 review。核心是在 `.gitlab-ci.yml` 中调用 `qwen-code -p` headless 模式 + `glab` CLI 发评论。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| 外部: 官方文档 `gitlab-ci-cd.md` | pipeline YAML 配置示例 |
| `cli/print.ts` | headless 执行入口 |

**Qwen Code 修改方向**：创建 `qwenlm/qwen-code-gitlab` CI 模板；核心调用 `qwen-code -p --output-format json` + `glab mr note`。
