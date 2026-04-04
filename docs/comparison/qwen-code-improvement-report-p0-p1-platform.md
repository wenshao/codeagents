# Qwen Code 改进建议 — P0/P1 平台集成

> 平台集成改进项：GitHub Actions CI、Code Review、SDK、Remote Control Bridge、GitLab 等
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md)

---


<a id="item-1"></a>

### 1. GitHub Actions CI（P1）

**思路**：官方 GitHub Action（`anthropics/claude-code-action@v1`）封装 `claude -p` headless 模式，实现 CI/CD 全自动化。两个工作流模板：

① **claude.yml**（@claude mention 触发）：用户在 issue/PR 评论中 @claude，自动运行 Agent 响应。触发条件：
- `issue_comment.created` + body 包含 `@claude`
- `pull_request_review_comment.created` + body 包含 `@claude`
- `pull_request_review.submitted` + body 包含 `@claude`
- `issues.opened/assigned` + title/body 包含 `@claude`

② **claude-code-review.yml**（PR 自动审查）：PR 创建/更新时自动触发代码审查，通过 plugin marketplace 加载 `code-review` 插件，调用 `/code-review:code-review {repo}/pull/{number}`。

**一键安装**：`/install-github-app` 命令自动化整个配置流程——检查仓库权限 → 生成 workflow YAML → 创建分支 → 配置 API Key secret（`gh secret set`）→ 打开 PR 模板让用户审批合并。

**headless 模式**（`-p`/`--print`）支持 CI 场景的关键 flag：
- `--output-format json|stream-json|text` — CI 解析结构化输出
- `--permission-mode dontAsk` — 非预批准的工具直接拒绝（不阻塞 CI）
- `--allowed-tools "Read,Bash(git:*)"` — 工具 allowlist
- `--disallowed-tools "Bash(rm:*)"` — 工具 denylist
- `--max-turns N` — 限制最大轮次防止无限循环
- `--max-budget-usd N` — 限制 API 花费
- `--json-schema <schema>` — 强制输出符合指定 JSON Schema

**安全**：CI 环境自动检测（`GITHUB_ACTIONS` 环境变量），子进程环境变量清洗（剥离 `ACTIONS_ID_TOKEN_REQUEST_*`/`ACTIONS_RUNTIME_*`/`SSH_SIGNING_KEY` 等敏感变量），防止 Agent 执行的 shell 命令泄露 CI 凭证。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `constants/github-app.ts` (145行) | 两个 workflow YAML 模板（`claude.yml` + `claude-code-review.yml`） |
| `commands/install-github-app/setupGitHubActions.ts` (326行) | 一键安装：检查权限→创建分支→写 YAML→配 secret→开 PR |
| `cli/print.ts` (5594行) | `runHeadless()` headless 执行入口 |
| `main.tsx` (L976-1006) | CLI flag 定义：`-p`/`--output-format`/`--permission-mode`/`--allowed-tools` |
| `utils/subprocessEnv.ts` (99行) | CI 环境变量清洗（30+ 敏感变量） |
| `utils/env.ts` (L285) | `GITHUB_ACTIONS`/`CIRCLECI`/`CI` 平台检测 |

**Qwen Code 修改方向**：已有 `.github/workflows/qwen-code-pr-review.yml` 工作流和 `QwenLM/qwen-code-action`，但缺少一键安装命令和 mention 触发。改进方向：① 新增 `/install-github-app` 一键安装命令（自动生成 YAML + 配置 secret + 创建 PR）；② 新增 @qwen mention 触发工作流（issue/PR 评论中 @qwen 自动响应）；③ headless 模式补充 `--json-schema`（强制结构化输出）和 `--max-budget-usd`（花费限制）。

**实现成本评估**：
- 涉及文件：~4 个
- 新增代码：~300 行
- 开发周期：~3 天（1 人）
- 难点：工作流模板的跨仓库兼容性

**意义**：CI 自动化是开发工作流的核心——每个 PR 都应被 Agent 自动审查。
**缺失后果**：工作流需手动配置 YAML + secret——每个仓库重复劳动且易出错。
**改进收益**：一键安装 = 3 分钟完成 CI 集成；@mention = issue/PR 评论中随时召唤 Agent。

---

<a id="item-2"></a>

### 2. GitHub Code Review 多 Agent审查（P1）

**思路**：多 Agent 并行审查 PR 不同文件——每个 Agent 检查一类问题（逻辑错误/安全漏洞/边界情况），验证步骤过滤误报，结果去重排序后发 inline 评论。可配合 `REVIEW.md` 定制审查规则。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| 托管服务（非本地源码） | 多 Agent 并行 + 验证 + 去重 |
| `code-review.md` 官方文档 | severity: 🔴 Important / 🟡 Nit / 🟣 Pre-existing |

**Qwen Code 修改方向**：基于已有 `/review` Skill 扩展——fork 多个 Agent 各审查一组文件；`gh api` 发 inline 评论；新增 `REVIEW.md` 支持。

**实现成本评估**：
- 涉及文件：~2 个
- 新增代码：~100 行
- 开发周期：~2 天（1 人）
- 难点：审查结果的去重与排序

**意义**：大 PR 单 Agent 逐文件审查慢——多 Agent并行可大幅提速。
**缺失后果**：单 Agent 审查大 PR 需 N 分钟。
**改进收益**：多 Agent 并行审查——大 PR 审查时间缩短到 ~1 分钟。

---

<a id="item-3"></a>

### 3. HTTP Hooks（P1）

**思路**：Hook 除了 `type: "command"`（shell）外，支持 `type: "http"` —— POST JSON 到 URL 并接收 JSON 响应。适合与 CI、审批系统、消息平台直接集成，无需 shell 中转。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/hooks/hookRunner.ts` | HTTP hook 执行（fetch POST + JSON parse） |
| `types/hooks.ts` | `HookConfig.type` 支持 `'command'` 和 `'http'` |

**Qwen Code 修改方向**：`hookRunner.ts` 新增 HTTP 分支——`type === 'http'` 时 fetch POST body（hook input JSON），解析 response JSON 作为 hook output。

**实现成本评估**：
- 涉及文件：~2 个
- 新增代码：~150 行
- 开发周期：~2 天（1 人）
- 难点：SSRF 防护（私有 IP 阻断）

**意义**：与外部服务（CI/审批/消息平台）集成需要 HTTP 而非 shell。
**缺失后果**：通过 shell curl 间接集成——脆弱且难以处理 JSON 响应。
**改进收益**：Hook 原生 HTTP——直接与 API 交互，响应结构化解析。

---

<a id="item-4"></a>

### 4. Structured Output --json-schema（P1）

**思路**：headless 模式 `--json-schema` 参数注入 SyntheticOutputTool——强制模型调用该工具输出结构化数据，Ajv 运行时验证 schema。不通过则重试。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `tools/SyntheticOutputTool/SyntheticOutputTool.ts` | Ajv 验证 + WeakMap schema 缓存 |
| `main.tsx` | `--json-schema` CLI 参数解析 + `--output-format json` |

**Qwen Code 修改方向**：新建 `tools/structuredOutput.ts`；`nonInteractiveCli.ts` 新增 `--json-schema` 参数；headless 模式注入该工具到工具列表。

**实现成本评估**：
- 涉及文件：~2 个
- 新增代码：~80 行
- 开发周期：~1 天（1 人）
- 难点：JSON Schema 验证与模型输出的兼容性

**意义**：CI 脚本需要结构化输出——解析纯文本不可靠。
**缺失后果**：CI 脚本自行 parse 纯文本——脆弱且不可靠。
**改进收益**：--json-schema 保证输出符合 schema——CI 集成可靠。

---

<a id="item-5"></a>

### 5. Agent SDK Python（P1）

**思路**：Qwen Code 已有 TypeScript SDK（`@qwen-code/sdk`），缺 Python SDK。Claude Code 提供 Python + TS 双语言 SDK，支持流式回调和工具审批回调。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `entrypoints/sdk/` | SDK 类型定义、消息映射 |
| 外部: `anthropics/claude-code-sdk-python` | Python 包 |

**Qwen Code 修改方向**：新建 `packages/sdk-python/`；封装 subprocess 调用 `qwen-code -p --output-format stream-json`；提供 `QwenCodeAgent` class + async generator API。

**实现成本评估**：
- 涉及文件：~8 个
- 新增代码：~1500 行
- 开发周期：~10 天（1 人）
- 难点：Python 异步生态与 Node 子进程 IPC 的桥接

**意义**：Python 生态开发者（数据科学、后端）需要原生 SDK。
**缺失后果**：Python 开发者需通过 shell 调用 CLI——不优雅。
**改进收益**：Python SDK `from qwen_code import Agent`——原生集成。

---

<a id="item-6"></a>

### 6. Bare Mode --bare（P1）

**思路**：`--bare` 跳过所有自动发现（hooks/LSP/plugins/auto-memory/CLAUDE.md/OAuth/keychain），仅通过 CLI 显式参数传入上下文。CI 确定性执行——每台机器同样结果。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `entrypoints/cli.tsx` (L283) | `CLAUDE_CODE_SIMPLE=1` 设置 |
| `main.tsx` (L394) | 跳过所有 prefetch |

**Qwen Code 修改方向**：`gemini.tsx` 新增 `--bare` flag；设置 `QWEN_CODE_SIMPLE=1` 环境变量；各模块在 `SIMPLE` 模式下跳过自动发现。

**实现成本评估**：
- 涉及文件：~3 个
- 新增代码：~50 行
- 开发周期：~1 天（1 人）
- 难点：确保跳过的初始化不影响核心功能

**意义**：CI 环境需要确定性执行——不同机器的 hooks/plugins 不应影响结果。
**缺失后果**：CI 启动慢 + 加载不需要的 hooks/plugins + 结果不可复现。
**改进收益**：--bare 确定性执行——跳过所有自动发现，每台机器同样结果。

---

<a id="item-7"></a>

### 7. Remote Control Bridge（P1）

**思路**：终端 Agent 注册到服务端（WebSocket），用户通过 Web/手机驱动本地 session。Outbound-only 模式——终端主动推事件，不接受入站连接。支持权限审批远程转发。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `bridge/bridgeMain.ts` | WebSocket 连接 + 事件转发 |
| `bridge/bridgeApi.ts` | API 端点交互 |
| `bridge/bridgeConfig.ts` | 配置 + 环境注册 |

**Qwen Code 修改方向**：新建 `packages/core/src/bridge/`；对接阿里云/自建 WebSocket 服务；`/remote-control` 命令启动桥接。

**实现成本评估**：
- 涉及文件：~10 个
- 新增代码：~1500 行
- 开发周期：~15 天（1 人）
- 难点：WebSocket 重连与消息去重

**相关文章**：[Remote Control Bridge Deep-Dive](./remote-control-bridge-deep-dive.md)

**意义**：离开电脑后 Agent 需要人类审批权限——当前无法远程操作。
**缺失后果**：需要人在电脑前审批——离开后 Agent 暂停。
**改进收益**：手机/浏览器远程驱动——外出时继续审批和补充上下文。

---

<a id="item-8"></a>

### 8. /teleport 跨平台迁移（P1）

**思路**：Web session 完成后 `/teleport` 到终端——fetch 远程分支 + checkout + 加载完整会话历史。前提：同 repo、clean git state、同账号。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| `utils/teleport.tsx` | 交互式 session picker |
| `utils/teleport/api.ts` | 远程 session 列表 API |
| `utils/teleport/gitBundle.ts` | git fetch + checkout |

**Qwen Code 修改方向**：需先有 Web 版本；新增 `/teleport` 命令；调用 API 获取 session 列表 → fetch branch → 加载历史。

**实现成本评估**：
- 涉及文件：~4 个
- 新增代码：~300 行
- 开发周期：~3 天（1 人）
- 难点：跨设备 session 状态一致性验证

**意义**：Web 上启动的长任务完成后需要在终端继续调试。
**缺失后果**：Web 和终端是独立的——无法衔接。
**改进收益**：/teleport 拉取 Web session 到终端——跨平台无缝切换。

---

<a id="item-9"></a>

### 9. GitLab CI/CD 集成（P1）

**思路**：官方 GitLab pipeline 集成——MR 创建时自动触发 review。核心是在 `.gitlab-ci.yml` 中调用 `qwen-code -p` headless 模式 + `glab` CLI 发评论。

**Claude Code 源码索引**：

| 文件 | 关键函数/常量 |
|------|-------------|
| 外部: 官方文档 `gitlab-ci-cd.md` | pipeline YAML 配置示例 |
| `cli/print.ts` | headless 执行入口 |

**Qwen Code 修改方向**：创建 `qwenlm/qwen-code-gitlab` CI 模板；核心调用 `qwen-code -p --output-format json` + `glab mr note`。

**实现成本评估**：
- 涉及文件：~3 个
- 新增代码：~200 行
- 开发周期：~3 天（1 人）
- 难点：GitLab API 与 GitHub API 的差异适配

**意义**：GitLab 在企业用户中占比显著——仅支持 GitHub 覆盖面不够。
**缺失后果**：GitLab 用户无法在 CI 中集成 Agent。
**改进收益**：覆盖 GitLab 用户群——企业级 CI 集成。

---

<a id="item-10"></a>

### 10. Ghost Text 输入补全（P1）

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

**实现成本评估**：
- 涉及文件：~5 个
- 新增代码：~400 行
- 开发周期：~4 天（1 人）
- 难点：输入法 composition 事件与 ghost text 的冲突处理

**意义**：命令补全是 CLI 工具最基础的 UX 期待——无补全等于每次都手打全名。
**缺失后果**：用户需完整输入 `/compress`、文件路径等——效率低且易出错。
**改进收益**：输入 `/com` 即显示 `/compress` 灰字，Tab 接受——打字量减半。

---
