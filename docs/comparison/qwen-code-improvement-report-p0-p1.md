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

**意义**：长会话是 AI Agent 的核心使用场景，压缩质量直接决定长会话的可用性。
**缺失后果**：用户需手动 /compress，压缩后模型'失忆'需重新描述上下文。
**改进收益**：长会话无限延续无需干预，压缩后自动恢复最近文件和记忆。

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

**意义**：大型任务需拆分给多个子代理并行处理，上下文传递效率决定成本和准确率。
**缺失后果**：每个子代理独立上下文 = N× 完整 prompt 费用，且需重复描述背景。
**改进收益**：N 个子代理共享一份 cache（省 80%+ token），继承完整对话零丢失。

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

**意义**：用户接受建议后的等待时间是交互体验的关键瓶颈。
**缺失后果**：每次 Tab 接受后等 2-10 秒完整 API + 工具执行。
**改进收益**：Tab 接受零延迟——建议展示时预执行已完成，支持连续 Tab-Tab-Tab。

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

**意义**：开发者在同一项目上反复使用 Agent，跨 session 知识断层导致效率低下。
**缺失后果**：每次新 session 从零开始——反复告知项目背景、编码规范、已知坑点。
**改进收益**：新 session 自动注入相关记忆——Agent'记住'项目上下文，无需反复说明。

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

**意义**：记忆文件随使用膨胀，陈旧/矛盾记忆导致模型行为异常。
**缺失后果**：记忆无限增长占满 token 预算，旧决策与新决策矛盾共存。
**改进收益**：后台自动整理——合并重复、删除过时、解决矛盾，记忆始终精简。

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

**意义**：用户在 Agent 执行多步操作时发现方向错误，无法及时纠正。
**缺失后果**：必须等所有步骤完成后才能发送新指令——已完成的错误工作需撤销。
**改进收益**：用户输入在当前 turn 的下一个 step 即被模型看到——避免无用工作。

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

**意义**：代码探索场景（多个 Read + Grep + Glob）是最常见的 Agent 操作之一。
**缺失后果**：7 个只读工具串行执行 = 7× 延迟。
**改进收益**：只读工具并行 = 1× 延迟，I/O 密集任务快 5-10×。

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

**意义**：启动体验是用户对工具的第一印象。
**缺失后果**：首次 API 需完整 TCP+TLS 握手（+100-200ms），启动打字丢失。
**改进收益**：预连接省 150ms + 启动打字不丢失——感知启动更快。

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

**意义**：大型项目不同目录有不同编码规范（TS/Python/Docs），全部加载浪费 token。
**缺失后果**：所有规则塞在一个 QWEN.md 中——系统提示膨胀，规则互相干扰。
**改进收益**：按文件路径匹配加载规则——操作 TS 文件时只注入 TS 规范，精准且省 token。

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

**意义**：团队协作项目中，个人发现的项目知识无法共享是效率瓶颈。
**缺失后果**：团队成员各自维护独立记忆——项目知识孤岛，新成员从零积累。
**改进收益**：一人学到的知识自动同步全团队 + 29 条规则防止密钥泄露。

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

**意义**：39+ 工具 schema 全部注入系统提示占用大量 token——尤其 MCP 工具。
**缺失后果**：系统提示 ~15K+ tokens 被工具 schema 占满，留给用户内容的空间减少。
**改进收益**：仅加载核心工具（~10 个），其余按需搜索——系统提示 token 减少 50%+。

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

**意义**：AI 生成代码的透明度和可追溯性是开源社区和企业合规的核心关注。
**缺失后果**：git 历史无法区分 AI 和人类代码——合规审计困难。
**改进收益**：commit 自动标注 AI 贡献比例——满足开源 AI 披露和企业审计要求。

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

**意义**：探索替代方案是软件开发的常见需求——A/B 对比架构决策。
**缺失后果**：探索替代方案必须丢弃当前进度，或手动复制上下文。
**改进收益**：从任意节点创建分支——原始 session 保留，分支独立探索。

---


<a id="item-14"></a>

### 14. GitHub Actions CI（P1）

**思路**：官方 GitHub Action 封装 `claude -p` headless 模式——PR 创建时自动触发 review、issue 创建时自动分类。支持 `--allowedTools` 白名单和 `--permission-mode dontAsk`。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| 外部: `anthropics/claude-code-action` | GitHub Action YAML + headless 调用 |
| `cli/print.ts` (5594行) | `runHeadless()` — headless 执行入口 |

**Qwen Code 修改方向**：创建 `qwenlm/qwen-code-action` GitHub Action；核心是调用 `qwen-code -p --allowedTools "Read,Bash" --output-format json`。

**意义**：CI 自动化是开发工作流的核心——每个 PR 都应被审查。
**缺失后果**：PR 审查需手动触发 Agent——无法自动化。
**改进收益**：PR 创建自动触发 Agent 审查——减少人工审查负担。

---

<a id="item-15"></a>

### 15. GitHub Code Review 多代理审查（P1）

**思路**：多 Agent 并行审查 PR 不同文件——每个 Agent 检查一类问题（逻辑错误/安全漏洞/边界情况），验证步骤过滤误报，结果去重排序后发 inline 评论。可配合 `REVIEW.md` 定制审查规则。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| 托管服务（非本地源码） | 多 Agent 并行 + 验证 + 去重 |
| `code-review.md` 官方文档 | severity: 🔴 Important / 🟡 Nit / 🟣 Pre-existing |

**Qwen Code 修改方向**：基于已有 `/review` Skill 扩展——fork 多个 Agent 各审查一组文件；`gh api` 发 inline 评论；新增 `REVIEW.md` 支持。

**意义**：大 PR 单 Agent 逐文件审查慢——多代理并行可大幅提速。
**缺失后果**：单 Agent 审查大 PR 需 N 分钟。
**改进收益**：多 Agent 并行审查——大 PR 审查时间缩短到 ~1 分钟。

---

<a id="item-16"></a>

### 16. HTTP Hooks（P1）

**思路**：Hook 除了 `type: "command"`（shell）外，支持 `type: "http"` —— POST JSON 到 URL 并接收 JSON 响应。适合与 CI、审批系统、消息平台直接集成，无需 shell 中转。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/hooks/hookRunner.ts` | HTTP hook 执行（fetch POST + JSON parse） |
| `types/hooks.ts` | `HookConfig.type` 支持 `'command'` 和 `'http'` |

**Qwen Code 修改方向**：`hookRunner.ts` 新增 HTTP 分支——`type === 'http'` 时 fetch POST body（hook input JSON），解析 response JSON 作为 hook output。

**意义**：与外部服务（CI/审批/消息平台）集成需要 HTTP 而非 shell。
**缺失后果**：通过 shell curl 间接集成——脆弱且难以处理 JSON 响应。
**改进收益**：Hook 原生 HTTP——直接与 API 交互，响应结构化解析。

---

<a id="item-17"></a>

### 17. Structured Output --json-schema（P1）

**思路**：headless 模式 `--json-schema` 参数注入 SyntheticOutputTool——强制模型调用该工具输出结构化数据，Ajv 运行时验证 schema。不通过则重试。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `tools/SyntheticOutputTool/SyntheticOutputTool.ts` | Ajv 验证 + WeakMap schema 缓存 |
| `main.tsx` | `--json-schema` CLI 参数解析 + `--output-format json` |

**Qwen Code 修改方向**：新建 `tools/structuredOutput.ts`；`nonInteractiveCli.ts` 新增 `--json-schema` 参数；headless 模式注入该工具到工具列表。

**意义**：CI 脚本需要结构化输出——解析纯文本不可靠。
**缺失后果**：CI 脚本自行 parse 纯文本——脆弱且不可靠。
**改进收益**：--json-schema 保证输出符合 schema——CI 集成可靠。

---

<a id="item-18"></a>

### 18. Agent SDK Python（P1）

**思路**：Qwen Code 已有 TypeScript SDK（`@qwen-code/sdk`），缺 Python SDK。Claude Code 提供 Python + TS 双语言 SDK，支持流式回调和工具审批回调。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `entrypoints/sdk/` | SDK 类型定义、消息映射 |
| 外部: `anthropics/claude-code-sdk-python` | Python 包 |

**Qwen Code 修改方向**：新建 `packages/sdk-python/`；封装 subprocess 调用 `qwen-code -p --output-format stream-json`；提供 `QwenCodeAgent` class + async generator API。

**意义**：Python 生态开发者（数据科学、后端）需要原生 SDK。
**缺失后果**：Python 开发者需通过 shell 调用 CLI——不优雅。
**改进收益**：Python SDK `from qwen_code import Agent`——原生集成。

---

<a id="item-19"></a>

### 19. Bare Mode --bare（P1）

**思路**：`--bare` 跳过所有自动发现（hooks/LSP/plugins/auto-memory/CLAUDE.md/OAuth/keychain），仅通过 CLI 显式参数传入上下文。CI 确定性执行——每台机器同样结果。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `entrypoints/cli.tsx` (L283) | `CLAUDE_CODE_SIMPLE=1` 设置 |
| `main.tsx` (L394) | 跳过所有 prefetch |

**Qwen Code 修改方向**：`gemini.tsx` 新增 `--bare` flag；设置 `QWEN_CODE_SIMPLE=1` 环境变量；各模块在 `SIMPLE` 模式下跳过自动发现。

**意义**：CI 环境需要确定性执行——不同机器的 hooks/plugins 不应影响结果。
**缺失后果**：CI 启动慢 + 加载不需要的 hooks/plugins + 结果不可复现。
**改进收益**：--bare 确定性执行——跳过所有自动发现，每台机器同样结果。

---

<a id="item-20"></a>

### 20. Remote Control Bridge（P1）

**思路**：终端 Agent 注册到服务端（WebSocket），用户通过 Web/手机驱动本地 session。Outbound-only 模式——终端主动推事件，不接受入站连接。支持权限审批远程转发。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `bridge/bridgeMain.ts` | WebSocket 连接 + 事件转发 |
| `bridge/bridgeApi.ts` | API 端点交互 |
| `bridge/bridgeConfig.ts` | 配置 + 环境注册 |

**Qwen Code 修改方向**：新建 `packages/core/src/bridge/`；对接阿里云/自建 WebSocket 服务；`/remote-control` 命令启动桥接。

**意义**：离开电脑后 Agent 需要人类审批权限——当前无法远程操作。
**缺失后果**：需要人在电脑前审批——离开后 Agent 暂停。
**改进收益**：手机/浏览器远程驱动——外出时继续审批和补充上下文。

---

<a id="item-21"></a>

### 21. /teleport 跨平台迁移（P1）

**思路**：Web session 完成后 `/teleport` 到终端——fetch 远程分支 + checkout + 加载完整会话历史。前提：同 repo、clean git state、同账号。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/teleport.tsx` | 交互式 session picker |
| `utils/teleport/api.ts` | 远程 session 列表 API |
| `utils/teleport/gitBundle.ts` | git fetch + checkout |

**Qwen Code 修改方向**：需先有 Web 版本；新增 `/teleport` 命令；调用 API 获取 session 列表 → fetch branch → 加载历史。

**意义**：Web 上启动的长任务完成后需要在终端继续调试。
**缺失后果**：Web 和终端是独立的——无法衔接。
**改进收益**：/teleport 拉取 Web session 到终端——跨平台无缝切换。

---

<a id="item-22"></a>

### 22. GitLab CI/CD 集成（P1）

**思路**：官方 GitLab pipeline 集成——MR 创建时自动触发 review。核心是在 `.gitlab-ci.yml` 中调用 `qwen-code -p` headless 模式 + `glab` CLI 发评论。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| 外部: 官方文档 `gitlab-ci-cd.md` | pipeline YAML 配置示例 |
| `cli/print.ts` | headless 执行入口 |

**Qwen Code 修改方向**：创建 `qwenlm/qwen-code-gitlab` CI 模板；核心调用 `qwen-code -p --output-format json` + `glab mr note`。

**意义**：GitLab 在企业用户中占比显著——仅支持 GitHub 覆盖面不够。
**缺失后果**：GitLab 用户无法在 CI 中集成 Agent。
**改进收益**：覆盖 GitLab 用户群——企业级 CI 集成。

---

<a id="item-23"></a>

### 23. Ghost Text 输入补全（P1）

**思路**：用户输入时在光标后显示灰色建议文字（ghost text）——命令名、文件路径、shell history 三层。Tab/Right Arrow 接受。建议仅在光标位于正确插入点时显示。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `types/textInputTypes.ts` | `InlineGhostText` 类型定义 |
| `hooks/useTextInput.ts` | ghost text 渲染 + `insertPosition === offset` 检查 |
| `utils/suggestions/commandSuggestions.ts` | 命令名模糊匹配 |
| `utils/suggestions/directoryCompletion.ts` | 路径补全 + LRU 缓存 |
| `utils/suggestions/shellHistoryCompletion.ts` | `~/.bash_history` 缓存 |

**Qwen Code 修改方向**：`InputPrompt.tsx` 新增 ghost text 渲染层（Ink `<Text dimColor>`）；新建 `utils/suggestions/` 目录实现命令/路径/历史三层补全。

**意义**：命令补全是 CLI 工具最基础的 UX 期待——无补全等于每次都手打全名。
**缺失后果**：用户需完整输入 `/compress`、文件路径等——效率低且易出错。
**改进收益**：输入 `/com` 即显示 `/compress` 灰字，Tab 接受——打字量减半。

---

<a id="item-24"></a>

### 24. 流式工具执行流水线（P1）

**思路**：API 流式返回 tool_use block 时，**不等完整响应结束**就立即开始执行已完成解析的工具。StreamingToolExecutor 维护有序队列：工具按到达顺序入队，并发安全的立即启动，结果按入队顺序出队。进度消息（pendingProgress）实时流出，不等工具完成。与 item-7（智能工具并行）互补——item-7 解决"哪些工具可以并行"，本项解决"何时开始执行"。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `services/tools/StreamingToolExecutor.ts` (530行) | `addTool()` 入队即触发 `processQueue()`、`getCompletedResults()` 非阻塞出队、`getRemainingResults()` 异步等待 |
| `query.ts` (L561-567, L838-862) | `config.gates.streamingToolExecution` 特性门控、流式回调中调用 `addTool()` |
| `utils/generators.ts` (L32-72) | `all()` 并发异步生成器——`Promise.race()` 等待任意完成 |

**Qwen Code 修改方向**：`coreToolScheduler.ts` 等待模型完整响应后才开始工具执行；`streamingToolCallParser.ts` 仅解析流式 JSON，不触发提前执行。改进方向：在 `streamingToolCallParser.ts` 中 tool_call 解析完成时立即通知 `coreToolScheduler`；调度器维护 `TrackedTool[]` 队列，并发安全工具立即启动，非安全工具排队等待。结果按顺序 yield 给渲染层。

**意义**：模型生成 5 个工具调用需 2-3 秒——流式执行让前面的工具在后面的还在生成时就开始执行。
**缺失后果**：等完整响应 = 工具延迟 = 模型生成时间 + 工具执行时间（串行叠加）。
**改进收益**：流式流水线 = 模型生成与工具执行重叠——端到端延迟减少 30-50%。

---

<a id="item-25"></a>

### 25. 文件读取缓存 + 批量并行 I/O（P1）

**思路**：3 层优化——① FileReadCache：1000 条 LRU 缓存，mtime 自动失效，Edit 后立即命中缓存无需重新读取；② 批量并行读取：32 个文件一批 `Promise.all(batch.map(readFile))`；③ 并行 stat：`Promise.all(filePaths.map(lstat))` 同时检测多文件修改时间。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/fileReadCache.ts` | `FileReadCache` 类、`maxCacheSize = 1000`、mtime 自动失效 |
| `utils/listSessionsImpl.ts` (L255) | `READ_BATCH_SIZE = 32`、`Promise.all(batch.map(readCandidate))` |
| `utils/filePersistence/outputsScanner.ts` (L97) | `Promise.all(filePaths.map(lstat))` 并行 stat |
| `utils/ide.ts` (L312, L684) | 并行 lockfile stat + 并行 lockfile 读取 |

**Qwen Code 修改方向**：`readManyFiles.ts` 顺序 `for` 循环逐个读取文件；无文件内容缓存；`atomicFileWrite.ts` 仅写入端有优化。改进方向：① 新建 `utils/fileReadCache.ts`——Map + mtime 校验 + 1000 条上限 LRU 淘汰；② `readManyFiles.ts` 中独立文件用 `Promise.all()` 并行读取（保留目录递归的顺序逻辑）；③ 文件扫描场景用 `Promise.all(paths.map(stat))` 并行获取元信息。

**意义**：文件 I/O 是 Agent 最频繁的操作——Read + Edit 循环中同一文件反复读取。
**缺失后果**：每次 Edit 后 re-read 全量磁盘 I/O；多文件探索时逐个串行读取。
**改进收益**：缓存命中 = 0ms 读取；32 并行 = 延迟降至 1/32（I/O 密集场景）。

---

<a id="item-26"></a>

### 26. 记忆/附件异步预取（P1）

**思路**：用户消息到达时，**不等工具执行完**就立即启动相关记忆搜索（异步 prefetch handle）。工具执行期间记忆搜索并行进行，工具完成后如果搜索已 settle 则注入结果，否则下一轮重试。Skill 发现同理——检测到"写操作转折点"时异步预取相关 skill。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/attachments.ts` (L2361-2415) | `startRelevantMemoryPrefetch()` 返回 handle、~20KB/turn 预算上限 |
| `query.ts` (L301, L1592) | 每轮 `using prefetch = startRelevantMemoryPrefetch()`、工具后 `if settled → inject` |
| `query.ts` (L66-67, L331, L1620) | `skillPrefetch?.startSkillDiscoveryPrefetch()` skill 发现预取、write-pivot 触发（feature gate `EXPERIMENTAL_SKILL_SEARCH`） |

**Qwen Code 修改方向**：无记忆预取机制；技能加载在启动时一次性完成（`skill-manager.ts`）；上下文附件在工具执行前同步收集。改进方向：① `chatCompressionService.ts` 旁新建 `memoryPrefetch.ts`——用户消息处理时 fire-and-forget 启动记忆搜索；② `coreToolScheduler.ts` 工具执行完成后检查 prefetch 是否 settled；③ skill 发现改为惰性——首次需要时搜索 + 结果缓存。

**意义**：记忆搜索需 50-200ms（涉及文件扫描或向量匹配）——与工具执行重叠则用户零感知。
**缺失后果**：记忆/上下文收集阻塞工具执行——每轮额外 100-200ms 串行等待。
**改进收益**：异步预取——记忆搜索与工具执行并行，延迟完全隐藏。

---

<a id="item-27"></a>

### 27. Token Budget 续行与自动交接（P1）

**思路**：长任务不因 `max_tokens` 截断而丢失进度。BudgetTracker 追踪每轮 token 增量：① 未达 90% 预算 → 注入续行提示让模型继续；② 连续 3 次增量 < 500 tokens → 检测为"收益递减"，停止续行；③ 停止后触发 auto-compact 链（microcompact → session memory compact → full compact）。整个过程用户无感知。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `query/tokenBudget.ts` (93行) | `COMPLETION_THRESHOLD = 0.9`、`DIMINISHING_THRESHOLD = 500`、`checkTokenBudget()` |
| `services/compact/autoCompact.ts` (L72-145) | `AUTOCOMPACT_BUFFER_TOKENS = 13_000`、3 次失败断路器 |
| `services/compact/microCompact.ts` | 旧工具结果清理（8 种可清除工具） |
| `services/compact/sessionMemoryCompact.ts` | 先尝试清理记忆附件，再触发全量压缩 |

**Qwen Code 修改方向**：`chatCompressionService.ts` 仅在 token 超 70% 阈值时触发一次性全量压缩（`COMPRESSION_TOKEN_THRESHOLD = 0.7`）。无 token 预算续行，无递减检测，无分层压缩回退。改进方向：① 新建 `tokenBudget.ts`——追踪续行次数 + delta + 递减检测；② 推理循环中检查 budget → continue 时注入续行提示、stop 时正常结束；③ 压缩改为分层：先清旧工具结果 → 再清记忆附件 → 最后全量摘要。

**意义**：复杂任务（重构、多文件变更）经常超出单次 max_tokens——截断等于前功尽弃。
**缺失后果**：达到 token 上限直接停止——用户需手动"继续"或重新开始。
**改进收益**：自动续行 + 递减检测——复杂任务自动完成，收益递减时自动停止，避免浪费。

---

<a id="item-28"></a>

### 28. 同步 I/O 异步化 — 事件循环解阻塞（P1）

**思路**：将热路径上的 `readFileSync`/`statSync`/`writeFileSync` 替换为 async 版本，防止阻塞 Node.js 事件循环。同步 I/O 在主线程执行时会冻结 UI 渲染和键盘输入处理——文件越大、磁盘越慢影响越大。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/fileReadCache.ts` | 唯一允许 sync 的地方——FileEditTool 内部热路径（有 mtime 缓存保护） |
| 其他文件 | 绝大多数文件操作使用 async `fs.promises` API |

**Qwen Code 修改方向**：多处热路径使用同步 I/O：
- `packages/cli/src/config/settings.ts` (L462, L498, L575) — 配置加载 `readFileSync`
- `packages/cli/src/config/trustedFolders.ts` (L142, L182) — 信任目录 `readFileSync`/`writeFileSync`
- `packages/core/src/utils/readManyFiles.ts` (L99) — 多文件读取 `statSync`
- `packages/core/src/lsp/LspConfigLoader.ts` — LSP 配置 `readFileSync`
- `packages/core/src/utils/workspaceContext.ts` (L98) — 工作区上下文 `statSync`

改进方向：① 全局搜索 `readFileSync`/`statSync`/`writeFileSync`，逐个替换为 async 版本；② 启动路径允许 sync（模块初始化阶段事件循环未运行）；③ 运行时路径（用户交互后）强制使用 async。

**意义**：同步 I/O 是 Node.js 性能杀手——10ms 的 readFileSync 意味着 10ms 的 UI 冻结。
**缺失后果**：大配置文件或慢磁盘上 readFileSync 阻塞事件循环——键盘无响应、渲染卡顿。
**改进收益**：async I/O = 事件循环不阻塞——UI 始终流畅，文件操作在后台完成。

---

<a id="item-29"></a>

### 29. Prompt Cache 分段与工具稳定排序（P1）

**思路**：系统提示拆分为 static（全局缓存）+ dynamic（每次重算）两段，用 `SYSTEM_PROMPT_DYNAMIC_BOUNDARY` 标记分界。内置工具保持稳定的连续前缀排序（MCP/动态工具追加在后），服务端在前缀后插入 cache breakpoint。工具 schema 锁定在首次渲染时（`toolSchemaCache`），防止 GrowthBook 特性开关翻转导致 11K-token schema 变化破坏缓存。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/api.ts` (L321-435) | `splitSysPromptPrefix()` 3 种缓存策略（global/org/tool-based） |
| `services/api/promptCacheBreakDetection.ts` | per-tool hash 追踪——77% 缓存失效由单个工具 schema 变化引起 |
| `utils/toolSchemaCache.ts` | 首次渲染锁定 schema，防止 mid-session 抖动 |
| `utils/toolPool.ts` (L64) | built-in 工具保持连续前缀，MCP 工具追加在后 |
| `services/api/claude.ts` (L358-434) | `getCacheControl()` 1h vs 5m TTL 决策 |
| `constants/systemPromptSections.ts` | `DANGEROUS_uncachedSystemPromptSection()` 显式标记易变段 |

**Qwen Code 修改方向**：系统提示作为整体发送，无分段缓存策略；工具列表无稳定排序；无缓存失效检测。每次 API 调用可能因工具顺序变化或系统提示微调导致缓存完全失效。改进方向：① 系统提示拆分 static/dynamic 段，static 段标记 `cache_control: { type: 'ephemeral' }`；② 工具排序：内置工具固定顺序在前，MCP 工具追加在后；③ 新建 `toolSchemaCache.ts` 锁定首次渲染的 schema 快照；④ 跟踪 `cache_read_input_tokens` 下降来检测意外缓存失效。

**意义**：Prompt cache 命中率直接影响成本和延迟——缓存命中省 90% token 费用 + 首 token 延迟减半。
**缺失后果**：每次调用重新编码完整系统提示 + 工具 schema = ~20K-50K tokens 浪费。
**改进收益**：分段缓存 + 稳定排序 = 80%+ 缓存命中率——成本降低 50%+，首 token 快 2×。

---

<a id="item-30"></a>

### 30. 会话崩溃恢复与中断检测（P0）

**思路**：进程异常退出（OOM、SIGKILL、断电）后，下次启动自动检测上次会话中断状态。3 种中断类型：① `none`——正常完成；② `interrupted_prompt`——用户消息未得到响应；③ `interrupted_turn`——助手响应中有未完成的工具调用。检测到中断后注入合成续行消息（synthetic continuation），模型自动恢复未完成的操作。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/conversationRecovery.ts` (598行) | `detectTurnInterruption()` 3 种中断状态检测、`deserializeMessagesWithInterruptDetection()` |
| `utils/sessionRestore.ts` (552行) | `processResumedConversation()` 全量恢复（文件快照 + attribution + worktree + todo） |
| `utils/sessionStorage.ts` (L447-464) | `registerCleanup()` 退出时 flush + 元数据重追加 |

**Qwen Code 修改方向**：`SessionService` 有 JSONL 存储但无中断检测。改进方向：① 新增 `conversationRecovery.ts`——加载 JSONL 后检测最后一条消息是否有未完成 tool_use；② 检测到中断时注入 `[上次会话在此处中断，请继续未完成的操作]` 合成消息；③ `--resume` 时自动恢复文件快照和工作目录。

**意义**：长任务最大风险是进程中途死亡——所有上下文和进度丢失。
**缺失后果**：进程崩溃 = 从零开始——用户需手动描述"刚才做到哪了"。
**改进收益**：自动中断检测 + 合成续行——崩溃后 `--resume` 即可无缝继续。

---

<a id="item-31"></a>

### 31. API 指数退避与降级重试（P1）

**思路**：10 次重试 + 指数退避（500ms base, 32s cap, 25% jitter）。特殊处理：① 429 rate-limit——读取 `retry-after` header 等待；② 529 overloaded——连续 3 次后降级到备用模型（`FallbackTriggeredError`）；③ 401/403——触发 token 刷新后重试；④ 网络错误（ECONNRESET/EPIPE）——禁用 keep-alive 后重试。环境变量 `CLAUDE_CODE_MAX_RETRIES` 可覆盖默认值。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `services/api/withRetry.ts` (823行) | `withRetry()` 主重试逻辑、`DEFAULT_MAX_RETRIES = 10`、`MAX_529_RETRIES = 3` |
| `services/api/withRetry.ts` (L530-548) | `getRetryDelay()` 指数退避 `BASE_DELAY_MS * 2^(attempt-1)` + 25% jitter |
| `services/api/withRetry.ts` (L326-365) | 529 连续 3 次后 `FallbackTriggeredError` 降级到备用模型 |
| `services/api/withRetry.ts` (L696-787) | `shouldRetry()` 错误分类（可重试 vs 不可重试） |

**Qwen Code 修改方向**：`generationConfig.maxRetries` 仅配置重试次数，无退避策略和降级逻辑。改进方向：① 新建 `utils/withRetry.ts`——指数退避 + jitter；② 429 读取 `retry-after` header；③ 连续 N 次服务端错误后降级到备用模型（如 qwen-plus → qwen-turbo）；④ 网络错误自动禁用 keep-alive 重建连接。

**意义**：长任务需数十次 API 调用——任意一次失败不应终止整个任务。
**缺失后果**：首次 429/500 = 任务立即失败——用户需手动重试。
**改进收益**：10 次退避重试 + 模型降级——99.9% 瞬态故障自动恢复。

---

<a id="item-32"></a>

### 32. 优雅关闭序列与信号处理（P1）

**思路**：SIGINT/SIGTERM/SIGHUP 各有专用 handler。关闭顺序：① 同步恢复终端模式（alt-screen、鼠标、光标）；② 打印 resume 命令提示；③ 并行执行清理函数（2s 超时）；④ 执行 SessionEnd hooks（1.5s 超时）；⑤ flush 分析数据（500ms）；⑥ 5s failsafe timer 兜底——超时强制 `process.exit()`，失败则 SIGKILL。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/gracefulShutdown.ts` (530行) | `setupGracefulShutdown()` 信号注册、`gracefulShutdown()` 关闭序列 |
| `utils/gracefulShutdown.ts` (L59-136) | `cleanupTerminalModes()` 同步终端恢复（alt-screen/mouse/cursor） |
| `utils/gracefulShutdown.ts` (L414-426) | failsafe timer = `max(5s, hookTimeout + 3.5s)` |
| `utils/cleanupRegistry.ts` | `registerCleanup()` / `runCleanupFunctions()` 全局清理注册 |

**Qwen Code 修改方向**：无 SIGINT/SIGTERM handler；`/quit` 命令仅触发 `SessionEnd` hook。改进方向：① `process.on('SIGINT/SIGTERM/SIGHUP')` 注册 handler；② 新建 `cleanupRegistry.ts`——全局注册 cleanup 函数；③ 关闭序列：终端恢复 → 清理 → hooks → flush → exit；④ failsafe timer 防止挂起。

**意义**：Ctrl+C 是最常见的中断方式——不优雅处理会导致终端状态残留、数据丢失。
**缺失后果**：Ctrl+C 后终端光标消失、alt-screen 残留、会话未保存。
**改进收益**：优雅关闭 = 终端恢复 + 会话保存 + 提示 resume 命令——中断零副作用。

---

<a id="item-33"></a>

### 33. 反应式压缩（prompt_too_long 恢复）（P1）

**思路**：API 返回 `prompt_too_long` 错误时，不直接报错，而是自动修复：① 解析错误消息中的 actual/limit token 数；② 按 token gap 裁剪最早的消息组（user+assistant 对）；③ 最多重试 3 次，每次裁剪后重发；④ 裁剪后注入 `[earlier conversation truncated]` 标记防止循环。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `services/compact/compact.ts` (L450-491) | 反应式重试循环（最多 3 次） |
| `services/compact/compact.ts` (L243-291) | `truncateHeadForPTLRetry()` 按 token gap 或 20% 裁剪最早组 |
| `services/api/errors.ts` (L62-118) | `parsePromptTooLongTokenCounts()` 解析 actual/limit |

**Qwen Code 修改方向**：`chatCompressionService.ts` 仅主动压缩（70% 阈值），无被动恢复。改进方向：① API 调用捕获 `prompt_too_long` 错误；② 解析 token 超限量；③ 裁剪最早消息组后重试（最多 3 次）；④ 注入截断标记防止重复裁剪。

**意义**：主动压缩可能因 token 估算不准而遗漏——被动恢复是最后防线。
**缺失后果**：token 估算偏差 + 未及时压缩 = API 报错 = 任务中断。
**改进收益**：prompt_too_long → 自动裁剪 → 重试——用户零感知，任务不中断。

---

<a id="item-34"></a>

### 34. 持久化重试模式（无人值守/CI）（P1）

**思路**：`--bg` 或 CI 模式下，API 失败不终止而是无限重试。退避上限 5 分钟（`PERSISTENT_MAX_BACKOFF_MS`），6 小时后重置退避（`PERSISTENT_RESET_CAP_MS`）。每 30 秒 yield 心跳消息保持会话活跃。读取 rate-limit `reset` header 精确等待配额恢复。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `services/api/withRetry.ts` (L368-412) | `PERSISTENT_MAX_BACKOFF_MS = 5min`、`PERSISTENT_RESET_CAP_MS = 6h`、`HEARTBEAT_INTERVAL_MS = 30s` |
| `services/api/withRetry.ts` (L96-104) | `persistentAttempt` 独立计数器、rate-limit reset header 读取 |

**Qwen Code 修改方向**：headless 模式下 API 失败直接退出。改进方向：① 检测 `--headless`/`--bg` 模式时启用 persistent retry；② 退避上限 5 分钟，6 小时后重置；③ 心跳消息保持远程会话存活；④ 读取 `x-ratelimit-reset` header 精确等待。

**意义**：CI/CD 和后台任务运行数小时——瞬态 API 故障不应终止整个流水线。
**缺失后果**：CI 中 API 偶发 500 = 整个 pipeline 失败 = 重新排队。
**改进收益**：无限重试 + 5min 退避上限——CI 任务在 API 恢复后自动继续。

---

<a id="item-35"></a>

### 35. 原子文件写入与事务回滚（P1）

**思路**：文件写入先写临时文件再 `rename()`——rename 是 POSIX 原子操作，断电时要么旧文件要么新文件，不会出现半写状态。大结果（>50K chars）自动持久化到 `tool-results/{SHA256}` 文件，消息中保留 `<persisted-output>` 标签 + 2KB 预览。模型需要完整内容时通过 Read 工具回读。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/statsCache.ts` (L219-249) | 原子写入：temp file + rename + unlink on error |
| `utils/toolResultStorage.ts` (L137-184) | 大结果落盘：`<persisted-output>` 标签 + 2KB preview + SHA256 hash |
| `utils/toolResultStorage.ts` (L55-78) | `getPersistenceThreshold()` 默认 50K chars |

**Qwen Code 修改方向**：`atomicFileWrite.ts` 已有 temp+rename 模式（仅用于用户文件编辑），但 session 存储和配置写入使用 `writeFileSync` 直接覆盖。改进方向：① session JSONL 追加使用 atomic append（write + fsync）；② 配置文件写入统一使用 temp+rename；③ 大工具结果（>25K chars，已有 `truncateToolOutputThreshold`）自动落盘 + 引用标签。

**意义**：长任务运行数小时——中途断电不应导致文件损坏或数据丢失。
**缺失后果**：`writeFileSync` 写到一半断电 = 配置文件损坏 = 下次启动失败。
**改进收益**：原子写入 = 零损坏风险；大结果落盘 = 上下文不膨胀。

---

<a id="item-36"></a>

### 36. 自动检查点默认启用（P1）

**思路**：每轮工具执行后自动创建 git checkpoint（`git stash` 或 shadow commit），用户可通过 `/restore` 回退到任意检查点。检查点包含：文件 diff 快照、对话消息 UUID、时间戳。默认启用而非需要用户手动开启。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/fileHistory.ts` | `fileHistoryTrackEdit()`、`makeSnapshot()`、max 100 snapshots |
| `utils/sessionStorage.ts` (L1085-1098) | `file-history-snapshot` 条目类型 |

**Qwen Code 修改方向**：`general.checkpointing.enabled` 存在但**默认关闭**。改进方向：① 将 `checkpointing.enabled` 默认值改为 `true`；② 每轮工具执行后自动创建快照（path + content hash + mtime）；③ `/restore` 命令展示检查点列表 + diff 预览 + 一键恢复。

**意义**：长任务中 Agent 可能在第 N 步犯错——需要回退到第 N-1 步而非从头开始。
**缺失后果**：检查点关闭 = Agent 改错文件后只能手动 `git checkout` 恢复。
**改进收益**：自动检查点 = `/restore` 选择任意步骤回退——精确撤销错误变更。
