# Qwen Code 改进建议——对标 Codex CLI

> 基于 Codex CLI (openai/codex) 完整 Rust 源码（70+ crate，**651,174 行**）与 Qwen Code 源码（**281,954 行 TS**）的系统对比，识别 **28 项**可借鉴的能力（其中 **1 项已实现**——item-13 Hook 系统）。Codex CLI 是唯一采用 Rust 原生构建 + 沙箱默认启用的主流 CLI Code Agent。
>
> **最后核对日期**：2026-04-24（两侧源码均已 `git pull` 刷新，新增 item-26/27/28）
>
> **相关报告**：
> - [Claude Code 改进建议报告（256 项）](./qwen-code-improvement-report.md)——行业领先者对比
> - [Gemini CLI 上游 backport 报告（53 项）](./qwen-code-gemini-upstream-report.md)——上游可 backport 改进
> - [OpenCode 对标改进报告（27 项）](./qwen-code-opencode-improvements.md)——多 Provider、Plugin 系统等

## 一、改进项索引

| # | 功能 | 优先级 | 来源 crate | 规模 |
|:-:|------|:------:|-----------|:----:|
| [1](#item-1) | 默认启用沙箱 + Linux 原生隔离 | **P0** | `sandboxing/` + `linux-sandbox/` + `windows-sandbox-rs/` | 17,315 行 |
| [2](#item-2) | Apply Patch 批量文件修改 | **P1** | `apply-patch/` | 3,264 行 |
| [3](#item-3) | Feature Flag 生命周期管理 | **P1** | `features/` | 1,452 行 |
| [4](#item-4) | 会话 Resume & Fork | **P1** | `rollout/` + `state/` | 19,030 行 |
| [5](#item-5) | Shell 命令安全分析 | **P1** | `shell-command/` | 5,781 行 |
| [6](#item-6) | Shell 权限升级检测 | **P1** | `shell-escalation/` | 2,215 行 |
| [7](#item-7) | 网络代理 + MITM 策略 | **P1** | `network-proxy/` | 8,711 行 |
| [8](#item-8) | App-Server JSON-RPC 协议 | **P2** | `app-server/` + `app-server-protocol/` | 48,136 行 |
| [9](#item-9) | 多 Agent 协作框架 | **P2** | `core/` multi_agents_v2 | ~5,000 行 |
| [10](#item-10) | Models Manager 模型目录 | **P2** | `models-manager/` | 2,072 行 |
| [11](#item-11) | Git Ghost Commit 快照 | **P2** | `git-utils/` | 4,024 行 |
| [12](#item-12) | Secrets Manager 密钥管理 | **P2** | `secrets/` | ~682 行 |
| [13](#item-13) | Hook 系统（5 种事件）✅ | **P2** | `hooks/` | 5,373 行 → Qwen Code **17,443 行已反超** |
| [14](#item-14) | Core Skills 环境依赖发现 | **P2** | `core-skills/` | 5,243 行 |
| [15](#item-15) | 执行策略引擎 | **P2** | `execpolicy/` | 1,790 行 |
| [16](#item-16) | Code Review 独立子命令 | **P2** | `exec/` review 部分 | ~2,000 行 |
| [17](#item-17) | Cloud Tasks 云端执行 | **P2** | `cloud-tasks/` | 4,801 行 |
| [18](#item-18) | MCP Server 模式 | **P2** | `mcp-server/` | 2,487 行 |
| [19](#item-19) | 多层配置栈 | **P2** | `config/` | 6,879 行 |
| [20](#item-20) | 终端检测与主题适配 | **P3** | `terminal-detection/` | 1,353 行 |
| [21](#item-21) | 实时语音对话 | **P3** | `realtime-webrtc/` + core | ~8,000 行 |
| [22](#item-22) | Personality 人格选择 | **P3** | `features/` personality | ~200 行 |
| [23](#item-23) | Code Mode 轻量沙箱 | **P3** | `code-mode/` | 2,746 行 |
| [24](#item-24) | 请求压缩（Zstd） | **P3** | `features/` | ~100 行 |
| [25](#item-25) | Exec Server 远程执行 | **P3** | `exec-server/` | 5,150 行 |
| [26](#item-26) | Sticky Environment 会话级环境变量选择 🆕 | **P2** | `app-server/` v2 thread state | ~500 行（PR#18897）|
| [27](#item-27) | Permission Profiles 统一权限档位 🆕 | **P2** | `core/` + `app-server/` + `tui/` + `mcp/` + `exec-server/` | ~1,500 行（6 PR）|
| [28](#item-28) | `excludeTurns` 分页加载 Thread 🆕 | **P3** | `app-server/` v2 thread_fork/resume | ~420 行（PR#19014）|

---

<a id="item-1"></a>

### 1. 默认启用沙箱 + Linux 原生隔离（P0）

**问题**：Qwen Code 已有沙箱支持（macOS Seatbelt + Docker/Podman，984 行），但存在两个差距：① **默认不启用**——用户需要手动 `--sandbox` 或设置 `QWEN_SANDBOX=true`，大多数用户不会主动开启；② **Linux 无原生沙箱**——只有 Docker/Podman 容器沙箱，缺少 Bubblewrap/Landlock 等轻量级进程隔离（不需要容器运行时）。Codex CLI 的沙箱默认启用且网络默认阻断。

**Codex CLI 的解决方案**：3 平台原生沙箱，**默认启用，网络默认阻断**：

| 平台 | 实现 | 规模 | 隔离级别 |
|------|------|:----:|---------|
| macOS | Seatbelt（`sandbox-exec`） | ~1,600 行 | read-only / restricted-read / workspace-write / danger-full-access |
| Linux | Bubblewrap + Landlock 回退 | ~4,000 行 | 命名空间隔离 + 内核级文件控制 |
| Windows | 受限令牌（restricted token） | ~9,757 行 | 实验性 |
| 通用 | `sandboxing/` 管理器 + 测试 | ~2,000 行 | 平台适配层 |

**Qwen Code 现状**：已有 macOS Seatbelt（6 种 profile）+ Docker/Podman 容器沙箱（`sandbox.ts` 984 行），但默认不启用。

**Qwen Code 修改方向**：① 添加 Linux Bubblewrap/Landlock 原生沙箱（不需要 Docker）；② 考虑在 `--full-auto` 或 CI 模式下默认启用沙箱；③ 网络默认阻断（当前 Seatbelt 默认 `permissive-open` 允许网络）。

**实现成本**：~1 周（Linux Landlock），参考 Claude Code 改进报告 [stability#30](./qwen-code-improvement-report-p2-stability.md#item-30)。

---

<a id="item-2"></a>

### 2. Apply Patch 批量文件修改（P1）

**问题**：重命名一个接口需要修改 10 个文件——Agent 调用 10 次 Edit 工具，每次都需要用户审批。如果中途失败（第 6 个文件报错），前 5 个文件已修改但后 4 个未修改，代码处于不一致状态。需要一个批量原子修改工具。

**Codex CLI 的解决方案**：`apply-patch/`（3,264 行）——unified diff 解析 + 批量应用：
- Hunk 验证 + Seek Sequence 模糊匹配
- 文件级 Add/Delete/Update + Move 检测
- Heredoc 提取多行 patch
- 独立可执行文件模式

**Qwen Code 修改方向**：新增 `apply_patch` 工具，解析 unified diff 格式，原子应用到多文件。OpenCode 也有类似实现（[item-2](./qwen-code-opencode-improvements.md#item-2)）。

**实现成本**：~3 天

---

<a id="item-3"></a>

### 3. Feature Flag 生命周期管理（P1）

**问题**：开发者想体验新功能（如语音输入、多 Agent 并行），但这些功能要么全量发布要么不发布——没有"实验性"中间态。如果新功能有 bug，影响所有用户。反过来，如果因为不够稳定而不发布，社区无法提前试用和反馈。

**Codex CLI 的解决方案**：52 个 Flag，5 种生命周期状态：

| 状态 | 数量 | 说明 |
|------|:----:|------|
| Stable | 10 | 默认启用 |
| Experimental | 4 | 用户可手动启用 |
| Under Dev | 18 | 开发中，默认关闭 |
| Removed | 8 | 已移除 |
| Deprecated | 2 | 已弃用 |

管理命令：`codex features list/enable/disable`。

**Qwen Code 修改方向**：实现运行时 Feature Flag 注册表 + `/experimental` 菜单。

**实现成本**：~3 天

---

<a id="item-4"></a>

### 4. 会话 Resume & Fork（P1）

**问题**：Agent 在第 15 轮走错了方向，用户想回到第 10 轮重新开始——但 `--resume` 只能恢复最近会话的最后状态，无法回到中间节点。用户想"如果第 10 轮换一种方案会怎样"（fork），也没有办法做到，只能开新会话从头开始。

**Codex CLI 的解决方案**：`rollout/`（6,807 行）+ `state/`（12,223 行）：
- UUID 会话标识 + JSONL 增量持久化
- 从任意 turn 恢复（continuation）
- 从 turn 分叉（branch exploration）
- 会话元数据索引（排序、搜索）
- SQLite schema v5 存储

**Qwen Code 修改方向**：参考 OpenCode 的 [Snapshot 系统](./qwen-code-opencode-improvements.md#item-11) + Codex 的 rollout 模式。

**实现成本**：~1 周

---

<a id="item-5"></a>

### 5. Shell 命令安全分析（P1）

**问题**：`rm -rf /` 和 `ls` 在 Qwen Code 的权限系统中都被分类为"写操作"——系统知道命令会修改文件系统，但不知道**危险程度**差异。`git push --force` 被分类为"读操作"（因为不修改本地文件），但实际上会覆盖远程分支。需要比"读/写"更细粒度的命令风险分析。

**Codex CLI 的解决方案**：`shell-command/`（5,781 行）：
- Bash + PowerShell 命令解析器
- 危险命令模式检测（`rm -rf`、`format /dev/sda`、`DROP TABLE` 等）
- 安全命令分类
- 子命令结构化解析

**Qwen Code 修改方向**：参考 Gemini CLI 的危险命令黑名单（[item-20](./qwen-code-gemini-upstream-report-details.md#item-20)），结合 Codex 的解析器实现更深度的命令分析。

**实现成本**：~3 天

---

<a id="item-6"></a>

### 6. Shell 权限升级检测（P1）

**问题**：Agent 生成 `sudo apt-get install libfoo-dev` 来安装依赖——看似合理，但用户批准后 Agent 获得了 root 权限，后续可以执行任何特权操作。更隐蔽的情况：`sudo bash -c "curl ... | sh"` 用 root 执行远程脚本。当前无机制检测命令中是否包含权限升级。

**Codex CLI 的解决方案**：`shell-escalation/`（2,215 行）：
- 执行时策略强制检查
- Socket 协议协调 sudo/doas 提示
- 每命令权限追踪
- 执行计时度量

**实现成本**：~3 天

---

<a id="item-7"></a>

### 7. 网络代理 + MITM 策略（P1）

**问题**：Agent 执行 `npm install` 时，postinstall 脚本可以向 `evil.com` 发送 HTTP 请求携带环境变量。Agent 执行 `curl` 下载文件时，URL 可能指向恶意地址。当前 Qwen Code 不拦截也不审计任何子进程的网络请求——即使启用了权限系统，网络访问仍然完全透明。

**Codex CLI 的解决方案**：`network-proxy/`（8,711 行）：
- HTTP/HTTPS 代理 + MITM 证书注入
- SOCKS5 支持
- 域名白名单/黑名单 + 模式匹配
- 策略热重载
- 阻断请求审计日志

**实现成本**：~2 周（高复杂度，TLS 证书生成 + 代理协议）

---

<a id="item-8"></a>

### 8. App-Server JSON-RPC 协议（P2）

**问题**：VS Code 扩展通过 companion 模式与 Qwen Code 通信，但没有标准化的 JSON-RPC 协议——其他 IDE（JetBrains、Neovim、Emacs）想集成 Qwen Code 时，需要从零实现私有协议。每个 IDE 插件作者都在重复发明轮子。

**Codex CLI 的解决方案**：`app-server/`（48,136 行）——90+ JSON-RPC 2.0 方法：

| 命名空间 | 方法数 | 功能 |
|----------|:-----:|------|
| `thread/*` | 20+ | 会话管理（start/resume/fork/rollback） |
| `turn/*` | 5+ | 回合管理（start/interrupt/steer） |
| `config/*` | 10+ | 配置读写 + MCP 服务器管理 |
| `command/*` | 5+ | 命令执行 + 终端交互 |
| `fs/*` | 5+ | 文件系统操作 |

支持 stdio + WebSocket 两种传输。

**实现成本**：~3 周

---

<a id="item-9"></a>

### 9. 多 Agent 协作框架（P2）

**问题**：用户要求"同时重构 3 个模块"——Agent 只能串行执行：先重构模块 A（5 分钟），再重构模块 B（5 分钟），再重构模块 C（5 分钟），总计 15 分钟。如果能并行执行，只需 5 分钟。当前 Agent 工具没有 spawn/wait 并行原语，Subagent 之间也无法通信。

**Codex CLI 的解决方案**：`multi_agents_v2`——
- spawn/close/send_message/wait_agent 工具
- Agent Job CSV 状态追踪
- 广度优先 vs 深度优先执行策略
- Agent 生命周期事件

**参考实现**：[Multica](https://github.com/multica-ai/multica)（`server/pkg/agent/`，4,201 行 Go）提供了统一的 Agent Backend 抽象——同一 `Backend` 接口驱动 Claude Code（stream-json）、Codex CLI（JSON-RPC）、OpenClaw、OpenCode 四种 Agent。Qwen Code 如果要编排外部 Agent（如调用 Claude Code 做 /ultrareview），可参考此模式。

**实现成本**：~2 周，参考 Claude Code 改进报告 [engine#14](./qwen-code-improvement-report-p0-p1-engine.md#item-14)。

---

<a id="item-10"></a>

### 10. Models Manager 模型目录（P2）

**问题**：用户执行 `/model` 切换模型时，不知道哪个模型支持 100K 上下文、哪个更便宜、哪个即将弃用。模型能力信息散落在代码各处，没有一个统一的 `models.json` 让用户和 Agent 查询。

**Codex CLI 的解决方案**：`models-manager/`（2,072 行）——内置 `models.json` 目录 + 模型预设 + 协作模式配置 + 弃用状态跟踪。

**参考实现**：[Hermes Agent](https://github.com/nousresearch/hermes-agent) 额外实现了 **Credential Pool**（`agent/credential_pool.py`）——同一 Provider 配置多个 API Key，自动轮换 + 速率限制追踪 + 失败自动切换。解决单 Key 被限流时 Agent 无法继续工作的问题。

**实现成本**：~2 天

---

<a id="item-11"></a>

### 11. Git Ghost Commit 快照（P2）

**问题**：Agent 修改了 20 个文件后发现方向错误——用户只能 `git checkout .` 丢弃全部修改或手动 `git stash`。如果修改跨越多次 commit，回退更复杂。需要一种不污染 git 历史的快照机制，让用户随时"拍照"并回滚到任意快照。

**Codex CLI 的解决方案**：`git-utils/`（4,024 行）——Ghost commit 不进入 git 历史，支持快照/恢复/diff 报告 + 大未追踪目录检测。

**实现成本**：~3 天，与 OpenCode [Snapshot](./qwen-code-opencode-improvements.md#item-11) 互补。

---

<a id="item-12"></a>

### 12. Secrets Manager 密钥管理（P2）

**问题**：项目 A 用 OpenAI API Key，项目 B 用 Anthropic API Key——用户只能通过 `export` 切换环境变量，容易混淆。更危险的是，环境变量对所有子进程可见（Agent 执行的 `npm install` 也能读取）。Qwen Code 有 `KeychainTokenStorage` 但仅用于 MCP OAuth 凭据，不支持用户自定义密钥的项目级隔离。

**Codex CLI 的解决方案**：`secrets/`（~682 行）——通用密钥管理：OS 密钥环后端 + Global/Environment（基于 cwd）双作用域 + 安全路径哈希 + list/get/set/delete 操作。

**实现成本**：~2 天（可复用现有 `KeychainTokenStorage` 基础设施）

---

<a id="item-13"></a>

### 13. Hook 系统——5 种事件（P2）✅ 已实现（已反超）

**状态**：**Qwen Code 已通过 [PR#2827](https://github.com/QwenLM/qwen-code/pull/2827) 全面实现**（2026-04-15 合并）。当前 Qwen Code hook 系统 **17,443 行**，远超 Codex CLI 的 5,584 行。

**2026-04-16 核对对比**：

| 维度 | Codex CLI | Qwen Code（2026-04-15 后） |
|---|---|---|
| **代码量** | ~5,584 行 | **~17,443 行** |
| **事件类型** | 5 种（SessionStart / UserPromptSubmit / PreToolUse / PostToolUse / Stop） | **12+ 种**（SessionStart / SessionEnd / UserPromptSubmit / PreToolUse / PostToolUse / PostToolUseFailure / **StopFailure** / **PostCompact** / Notification + 更多） |
| **Hook 类型** | command 脚本 | **command + HTTP POST + Function（JS 函数引用）+ Async Hook** |
| **响应模式** | abort / modify / continue | abort / modify / continue + **异步非阻塞** |
| **安全** | — | **SSRF 防护**（`ssrfGuard.ts` / `urlValidator.ts`），HTTP Hook URL 验证 |

**原文描述**（"Qwen Code 覆盖面不足"）已**过时**——PR#2827 新增 HTTP Hook + Function Hook + Async Hook + SSRF 防护后，Qwen Code 的 hook 能力**已超过** Codex CLI。

**实现成本**：✅ 已实现（0 天）

---

<a id="item-14"></a>

### 14. Core Skills 环境依赖发现（P2）

**问题**：用户运行 `/review` Skill，Agent 执行到第 3 步才发现需要 `GITHUB_TOKEN` 环境变量——前面 2 步的 token 消耗白费了。Skill 依赖的环境变量（API Key、PATH 中的工具）应该在加载时就检测，而不是执行中途才报错。

**Codex CLI 的解决方案**：`core-skills/`（5,243 行）——Skill 加载时检测环境变量依赖，缺失时提示用户设置。

**实现成本**：~2 天

---

<a id="item-15"></a>

### 15. 执行策略引擎（P2）

**问题**：团队希望 Agent 可以自由运行 `cargo test` 但禁止 `cargo publish`，允许 `git commit` 但禁止 `git push --force`——但当前权限规则只区分"读/写"，无法按命令模式细粒度配置。

**Codex CLI 的解决方案**：`execpolicy/`（1,790 行）——基于模式（regex）的前缀规则：`^cargo` → allow、`^rm` → deny、`^git.*--force` → deny。

**实现成本**：~2 天

---

<a id="item-16"></a>

### 16. Code Review 独立子命令（P2）

**问题**：在 GitHub Actions 中运行 `qwen-code /review` 需要 TUI 交互——CI 环境无终端，无法使用。想在 PR 自动审查中集成 Qwen Code，必须有一个无需 TUI 的 CLI 子命令，直接输出审查结果到 stdout 或 PR 评论。

**Codex CLI 的解决方案**：`codex review` 独立 CLI 子命令——支持 `--uncommitted`/`--base`/`--commit` 参数，无需 TUI，直接输出到 stdout/PR 评论。

**实现成本**：~3 天

---

<a id="item-17"></a>

### 17. Cloud Tasks 云端执行（P2）

**问题**：修复 50 个测试用例需要反复运行整个测试套件——在本地笔记本上每轮 10 分钟，来回 5 轮需要 50 分钟且阻塞本地工作。如果能把任务提交到云端隔离环境执行（best-of-N 多次尝试选最优），用户可以继续做其他事。

**Codex CLI 的解决方案**：`cloud-tasks/`（4,801 行）——提交任务到云端隔离环境执行，best-of-N 多次尝试，完成后 diff 拉回本地。

**实现成本**：~3 周（需要云端基础设施）

---

<a id="item-18"></a>

### 18. MCP Server 模式（P2）

**问题**：用户在 Claude Code 中工作时想调用 Qwen Code 的某个 Skill——但 Qwen Code 只能作为 MCP **客户端**调用别人，不能作为 MCP **服务器**被调用。无法成为多 Agent 协作生态中的一个节点。

**Codex CLI 的解决方案**：`mcp-server/`（2,487 行）——`codex mcp-server` 以 stdio 模式启动，暴露 tools/resources/prompts 能力，支持 MCP 协议 `2024-11-05`。

**实现成本**：~3 天

---

<a id="item-19"></a>

### 19. 多层配置栈（P2）

**问题**：团队 lead 想设定统一的 linter 规则和模型选择，但每个开发者需要覆盖主题和快捷键——当前只有单层配置，要么全局统一（限制个人偏好），要么各自独立（无法团队管控）。需要 global → user → project → workspace 多层合并。

**Codex CLI 的解决方案**：`config/`（6,879 行）——5 层配置合并（global → user → project → workspace → workspace-local）+ TOML 解析 + 配置迁移 + Profile 支持。

**实现成本**：~1 周

---

<a id="item-20"></a>

### 20. 终端检测与主题适配（P3）

**问题**：用户在 SSH 远程连接中使用 Qwen Code，Kitty 键盘协议和 256 色主题不工作——输出乱码或快捷键失效。在 VS Code 内嵌终端和原生 iTerm2 中体验也不一致。当前不检测终端能力，所有终端用相同渲染策略。

**Codex CLI 的解决方案**：`terminal-detection/`（1,353 行）——自动检测 Kitty 键盘协议、bracketed paste、色彩深度，适配不同终端。

---

<a id="item-21"></a>

### 21. 实时语音对话（P3）

**问题**：手在键盘上打字时无法同时看代码——语音输入可以让开发者一边阅读代码一边口述指令。对于行动不便的开发者，语音是唯一的输入方式。

**Codex CLI 的解决方案**：GPT-4 Realtime 双向流式语音（WebSocket + WebRTC），~8,000 行实现。需要模型支持实时音频 API。

---

<a id="item-22"></a>

### 22. Personality 人格选择（P3）

**问题**：有的开发者喜欢简洁回复（"改好了"），有的喜欢详细解释（"我修改了 X 因为 Y，这样做的好处是 Z"）——当前 Agent 用固定风格回复所有人。

**Codex CLI 的解决方案**：TUI 中可选 Agent 人格/风格（`codex features enable personality`），通过 prompt 注入不同交互风格。

---

<a id="item-23"></a>

### 23. Code Mode 轻量沙箱（P3）

**问题**：Agent 想计算 `2 + 2` 或验证一个正则表达式——需要启动完整 Shell 进程、等待 PTY 输出、解析结果。对于简单表达式求值，Shell 工具的进程创建开销（~50ms）和权限审批流程远超实际计算时间。

**Codex CLI 的解决方案**：`code-mode/`（2,746 行）——统一 exec + wait 工具接口，运行时约束（yield 时间、输出 token 上限），嵌套工具检测防止循环。

---

<a id="item-24"></a>

### 24. 请求压缩（Zstd）（P3）

**问题**：100K token 的上下文以 JSON 明文发送到 API——在慢速网络（如中国到海外 API 的跨境链路）上，传输时间显著增加 TTFT（Time To First Token）。

**Codex CLI 的解决方案**：可选 Zstd 压缩，减少 30-50% 传输体积。

---

<a id="item-25"></a>

### 25. Exec Server 远程执行（P3）

**问题**：Agent 需要在 Linux 环境编译 C++ 项目，但用户在 macOS 上——只能手动 SSH 到远程服务器。如果能通过统一 API 把命令发送到远程容器执行（和本地命令用相同接口），Agent 就不受本地环境限制。

**Codex CLI 的解决方案**：`exec-server/`（5,150 行）——RPC 进程管理（start/read/write/terminate），支持远程容器/CI 系统中执行，与本地使用同一 API。

**参考实现**：[Hermes Agent](https://github.com/nousresearch/hermes-agent)（`tools/environments/`）实现了 6 种终端后端——Local/Docker/SSH/Daytona/Singularity/Modal，统一 `BaseEnvironment` 接口。Daytona 和 Modal 支持 **serverless 休眠**——Agent 环境空闲时自动暂停，按需唤醒，几乎零成本。

---

<a id="item-26"></a>

### 26. Sticky Environment 会话级环境变量选择 🆕（P2）

**问题**：用户有多套环境配置（`staging` / `prod` / `dev`），每次启动会话都要手动 export 一堆 env var，或者 `.env.staging` 然后 source。切换环境麻烦、易错。MCP 工具和内部工具分别读各自的 env 状态，容易不一致。

**Codex 的解决方案**（[PR#18897](https://github.com/openai/codex/pull/18897)，2026-04-23 合并）——**sticky environment selections**：

- `v2 thread/start` + `turn/start` 新增 sticky env 选项参数
- env 选择"粘在"整个 thread 生命周期上，每轮 turn 自动继承，无需重复传递
- 后续 PR 栈（#18898 config.toml 命名环境加载 + #18899 下游工具/runtime 消费者）让内部工具 + MCP + exec-server 都看到相同的 env 上下文
- Turn 级 override：某一轮可以临时覆盖 sticky 值，不影响后续

**核心设计**：
```
ThreadStartParams {
  env_selections: { name: "staging", overrides: { API_KEY: "..." } }
  //               ↑ named env from config.toml
}
TurnStartParams {
  env_overrides: { ... }  // 本轮临时覆盖
}
```

**Qwen Code 现状**：env 完全由进程继承（`process.env`），没有会话/thread 级概念。多 tab 切环境 = 每个 tab 重新 export。

**Qwen Code 修改方向**：
1. `ChatRecordingService` 增加 `stickyEnv: Record<string, string>` session state
2. `config.yaml` / settings.json 支持 `envProfiles: { staging: {...}, prod: {...} }` 命名环境
3. `/env` slash command 切换当前 sticky env
4. 工具调用（bash / mcp）注入 `{...process.env, ...session.stickyEnv, ...turn.envOverrides}`
5. turn-level `env:` 字段用于一次性覆盖（prompt 里写 `env:FOO=bar` 之类语法）

**实现成本**：~2 周（2 人）——新增 session state + config schema + 工具执行路径的 env 注入。

**意义**：多环境工作流（dev/staging/prod）的原生支持；避免用户手动维护 `.env` 文件。
**改进收益**：切环境从"开新终端 + source .env" 变为 `/env staging`。

---

<a id="item-27"></a>

### 27. Permission Profiles 统一权限档位 🆕（P2）

**问题**：Qwen Code 权限规则是**全局 flat 列表**（`permissions: [...]`），无法区分"当前这次 turn 的审批档位"——比如想"这轮只读、下一轮允许 edit、再下一轮完全 YOLO"，只能手动改 config。Codex 做了**档位化 + 跨层传播**。

**Codex 的解决方案**（6 PR 协同，均 2026-04-22~23 合并）：

| PR | 方向 |
|---|---|
| [#18282](https://github.com/openai/codex/pull/18282) | `protocol: report session permission profiles` —— 协议层声明 |
| [#18283](https://github.com/openai/codex/pull/18283) | `app-server: accept command permission profiles` —— app-server 消费 |
| [#18284](https://github.com/openai/codex/pull/18284) | `tui: sync session permission profiles` —— TUI 同步 |
| [#18285](https://github.com/openai/codex/pull/18285) | `tui: carry permission profiles on user turns` —— 每轮携带 |
| [#18286](https://github.com/openai/codex/pull/18286) | `mcp: include permission profiles in sandbox state` —— MCP 感知 |
| [#18287](https://github.com/openai/codex/pull/18287) | `shell-escalation: carry resolved permission profiles` —— 升级路径携带 |
| [#18924](https://github.com/openai/codex/pull/18924) | `TUI: preserve permission state after side conversations` —— 侧边会话穿透 |
| [#19050](https://github.com/openai/codex/pull/19050) | `feat(request-permissions) approve with strict review` —— Strict review 模式 |

**核心设计**：
- **Profile 是一个命名组合**：`readonly` / `exec-allowed` / `yolo` / 用户自定义
- **跨层传播**：TUI 用户 turn → core session → app-server → MCP servers → exec-server；一次切换档位，所有层都感知
- **Side conversation 穿透**：子对话（如 /review 子 agent）开启时权限档位被保留，子对话结束后自动恢复，不会"忘记"
- **Strict review 模式**：PR#19050 新增——approve 时可选 "strict" 模式，要求模型提供更完整的 before/after diff 说明

**Qwen Code 现状**：`permissions` 静态规则，无档位切换，无子对话穿透。`--yolo` / `--auto-edit` 是 CLI 启动参数，运行时无法切换。

**Qwen Code 修改方向**：
1. 定义 `permissionProfiles: { readonly, editAllowed, yolo }` 配置 schema
2. Session state 记录当前 active profile
3. `/perms <profile>` slash command 切换
4. Subagent 启动时**继承**父 profile（可限制不能升档）
5. Strict review 模式：审批弹窗 "approve" 按钮旁加 "approve with strict review"，触发模型补全 diff 注释后再执行

**实现成本**：~3 周（1 人）——跨 config + session + permission engine + UI 多处改动。

**意义**：审批体验从"二元 ask/allow/deny" → "档位化 YOLO/Edit/Readonly 三档可切"。
**改进收益**：信任度渐进——用户可以从 readonly 开始，看到 agent 表现良好后升档到 editAllowed，高信任场景开 yolo。

---

<a id="item-28"></a>

### 28. `excludeTurns` 分页加载 Thread 🆕（P3）

**问题**：长 session（1000+ turns）恢复时一次性全量加载 JSONL 会卡 UI 几秒。UI 其实只需要最新几屏的内容，老 turn 按需翻页。

**Codex 的解决方案**（[PR#19014](https://github.com/openai/codex/pull/19014)，2026-04-23 合并）：

```
thread/resume { excludeTurns: true }   ← 只建立 subscription，不加载历史
thread/fork   { excludeTurns: true }   ← fork 时同理
  ↓ 随后
thread/turns/list { page: 0, size: 50 }  ← UI 按需翻页
```

**设计精妙**：**订阅建立 vs 历史加载解耦**。调用方（UI / SDK）拿到 thread handle 后可以立即显示"加载中…"占位，并发 turns/list 请求按屏幕可视区域懒加载；旧的一次性加载模式下 resume 必须阻塞到所有 turn 都读完才能开始订阅新事件。

**Qwen Code 现状**：`ChatRecordingService.resume()` 一次性读完整 JSONL 到内存，大 session 慢启动。

**Qwen Code 修改方向**：
1. `session.resume()` 增加 `{ lazyLoad: true }` 选项 —— 只读 session metadata + 最近 N turn
2. 新 API `session.loadTurns({ offset, limit })` 按需拉取
3. UI 的 `ChatView` 改为虚拟滚动，滚到顶部触发 loadTurns 上一页

**实现成本**：~1 周（1 人）。

**意义**：长 session resume 从"卡 2-5 秒"降到 <200ms。
**改进收益**：`--resume` 默认即时响应，大 session 用户体验显著改善。

---

## 二、竞品对比矩阵

| 能力 | Codex CLI | Claude Code | Gemini CLI | Qwen Code |
|------|----------|-------------|-----------|-----------|
| **技术栈** | Rust 原生 | TypeScript/Rust | TypeScript | TypeScript |
| **代码规模** | 619,458 行 | ~512,000 行 | ~550,000 行 | ~439,000 行 |
| **默认沙箱** | ✅ 3 平台原生 | 可选 | 可选 | 可选（Docker/Podman/Seatbelt） |
| **网络隔离** | ✅ 默认阻断 | 可选 | 无 | ❌ |
| **Feature Flag** | 52 运行时 | 22 编译时 | 无 | ❌ |
| **IDE 协议** | 90+ JSON-RPC | WebSocket Bridge | VS Code Companion | VS Code Companion |
| **会话 Fork** | ✅ | ✅ | ✅ | ❌ |
| **Cloud 执行** | ✅ best-of-N | Kairos | 无 | ❌ |
| **MCP 双向** | ✅ 客户端+服务器 | 客户端 | 客户端 | 客户端 |
| **语音** | ✅ WebRTC | ✅ 内置 | 无 | ❌ |
| **多 Agent** | ✅ V2 并行 | Coordinator/Swarm | 无 | Arena（竞赛） |
| **Apply Patch** | ✅ unified diff | Edit 逐文件 | Edit | Edit |
| **密钥管理** | ✅ OS 密钥环 | 无 | 无 | ❌ |
| **Ghost Commit** | ✅ | 检查点 | 无 | ❌ |

## 三、实施路线图

| 阶段 | 时间 | 内容 | 预期效果 |
|------|------|------|---------|
| **第 1 周** | 3 天 | Feature Flag (#3) + Apply Patch (#2) | 功能渐进交付 + 多文件原子编辑 |
| **第 2-3 周** | 2 周 | 默认沙箱 Linux (#1) + Shell 安全 (#5/#6) | 安全模型完善 |
| **第 4 周** | 1 周 | 会话 Resume & Fork (#4) + Ghost Commit (#11) | 跨会话工作流 |
| **第 5-6 周** | 2 周 | 网络代理 (#7) + 执行策略 (#15) + Secrets (#12) | 网络安全 + 密钥管理 |
| **第 7-8 周** | 2 周 | 多 Agent V2 (#9) + MCP Server (#18) | 并行 Agent + 双向 MCP |
| **后续** | 按需 | App-Server (#8) + Cloud Tasks (#17) + 语音 (#21) | IDE 集成 + 云端 |

## 四、Qwen Code 独有优势（Codex CLI 无）

| 能力 | 说明 |
|------|------|
| **多 Provider** | Anthropic/OpenAI/DashScope/DeepSeek 等 10+ Provider |
| **Agent Arena** | 多模型并行竞赛评估 |
| **免费 OAuth** | 1000 次/天 |
| **多渠道部署** | DingTalk/Telegram/WeChat/Web |
| **国际化** | 6 语言 i18n |
| **Gemini CLI 兼容** | fork 自 Gemini CLI，共享上游改进 |
| **多格式扩展** | Claude + Gemini + Qwen 三格式兼容 |

## 五、更新日志

### 2026-04-24（Codex 上游 `git pull` · 新增 3 项）

**Codex 源码扫描**：`2026-04-10 → 2026-04-24` 间 60+ commit，识别出 **3 项新可借鉴能力**。主要方向是 thread/session 控制面的精细化。

#### 新增 3 项

| # | 功能 | 关键 PR | 合并日期 |
|---|---|---|---|
| [item-26](#item-26) | Sticky Environment 会话级环境变量选择 | [#18897](https://github.com/openai/codex/pull/18897) + stack (#18898/#18899) | 2026-04-23 |
| [item-27](#item-27) | Permission Profiles 统一权限档位（跨 TUI/MCP/exec/core 传播）| [#18282](https://github.com/openai/codex/pull/18282) ~ [#18287](https://github.com/openai/codex/pull/18287) + [#18924](https://github.com/openai/codex/pull/18924) + [#19050](https://github.com/openai/codex/pull/19050) | 2026-04-22~23 |
| [item-28](#item-28) | `excludeTurns` 分页加载 Thread | [#19014](https://github.com/openai/codex/pull/19014) | 2026-04-23 |

#### 值得提及但未单列 item 的 Codex 变更

| PR | 方向 | 为什么不单列 |
|---|---|---|
| [#18385](https://github.com/openai/codex/pull/18385) `Support MCP tools in hooks` | hook schema 支持 MCP 工具名（非 Bash-only）| 已在 item-13 覆盖范围内，Qwen 的 Hook 系统（17K 行）已反超，理论可做等价扩展，作为 item-13 内部 refinement |
| [#19063](https://github.com/openai/codex/pull/19063) + [#19056](https://github.com/openai/codex/pull/19056) auto-review stable + rename "reviewer" → "auto-review" | /review 子命令稳定化 | 已在 item-16 覆盖；Qwen 走不同的 /review 路线（参考 `docs/comparison/review-command.md`）|
| [#19129](https://github.com/openai/codex/pull/19129) `Reject agents.max_threads with multi_agent_v2` | 多 Agent V2 thread 上限约束 | 已在 item-9（多 Agent 框架）覆盖 |
| [#19071](https://github.com/openai/codex/pull/19071) `Add computer_use feature requirement key` | Computer use 特性请求 | 已被 Claude Code 改进报告 p2-core item-6 Computer Use 覆盖（⚠️ 实验性） |
| [#18255](https://github.com/openai/codex/pull/18255) `app-server: add Unix socket transport` | IPC 传输 | 已在 item-8 App-Server JSON-RPC 覆盖（传输层 refinement）|
| [#19008](https://github.com/openai/codex/pull/19008) + [#18908](https://github.com/openai/codex/pull/18908) Remote thread store + thread config endpoint | 远程 thread 存储 | 更多是 codex 内部服务化方向，Qwen 对标价值不高（已有本地 JSONL）|
| `codex-rs/windows-sandbox-rs/` 系列提交 | Windows 原生沙箱（unified_exec）| 已在 item-1 默认沙箱覆盖，Windows 扩展只是路径完善 |

---

### 2026-04-16

**全量核对**：`git pull` 刷新两侧源码后逐项验证 25 项。Codex CLI 651,174 行（+31,716），Qwen Code 281,954 行。

- **item-13 Hook 系统 标记 ✅ 已实现**：[PR#2827](https://github.com/QwenLM/qwen-code/pull/2827) 于 2026-04-15 合并，添加 HTTP Hook + Function Hook + Async Hook + SSRF 防护。Qwen Code hook 系统 17,443 行 vs Codex CLI 5,584 行——**已反超**。
- **修正代码量**：报告头 619,458 行 → **651,174 行**（Codex 增长），Qwen Code **281,954 行**。
- **修正 Claude Code 改进报告引用**：253 项 → 251 项。
- **其他 24 项状态确认为"准确"**——通过 crate 目录存在性 + `wc -l` 验证 + Qwen Code 等价功能搜索逐一确认。差距项无变化（沙箱/apply-patch/feature-flag/shell 分析/网络代理/多 Agent V2/MCP server 等）。
- **接近对齐的 5 项**（已有部分实现但仍有差距）：item-10（Models Manager，Qwen 5,180 LOC 但无统一目录 JSON）、item-11（Git Snapshot，gitWorktreeService 1,063 LOC 但无 ghost commit）、item-14（Skills，2,673 LOC 但无环境依赖预检）、item-19（Config，2,366 LOC 但无多层栈合并）、item-20（Terminal Detection，仅 Kitty 溢出追踪）。

### 2026-04-10

- 初始版本：25 项改进建议，基于 Codex CLI 完整 Rust 源码（619,458 行）分析

---

*分析基于 Codex CLI (openai/codex, Apache-2.0, 70+ Rust crate, **651K 行**) 和 Qwen Code 源码 (**282K 行**)。最后核对：2026-04-16。*
