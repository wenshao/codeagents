# Qwen Code 改进建议——对标 Codex CLI

> 基于 Codex CLI (openai/codex) 完整 Rust 源码（121 crate，**1,043,805 行** `codex-rs/**/*.rs`）与 Qwen Code 源码（**1,381,340 行** `packages/**/*.ts(x)`，daemon/web-shell/desktop 合入 main 后激增）的系统对比，识别 **30 项**可借鉴的能力（其中 **1 项已实现**——item-13 Hook 系统）。Codex CLI 是唯一采用 Rust 原生构建 + 沙箱默认启用的主流 CLI Code Agent。
>
> **最后核对日期**：2026-06-20（Codex `git pull`：`56c97e3b5c → 64bdeed9f7`，7 天 231 commits，`codex-rs` +51k 行；**本窗口 0 个新增 crate / 0 个新 item**，refinement-heavy；crate 数 baseline 修正为 **121**（cargo workspace members）；refresh item-8/9/12/18/25/26/29/30 状态）
>
> **相关报告**：
> - [Claude Code 改进建议报告（256 项）](./qwen-code-improvement-report.md)——行业领先者对比
> - [Gemini CLI 上游 backport 报告（53 项）](./qwen-code-gemini-upstream-report.md)——上游可 backport 改进
> - [OpenCode 对标改进报告（35 项）](./qwen-code-opencode-improvements.md)——多 Provider、Plugin 系统等
> - [Reasoning Effort Deep-Dive](./reasoning-effort-deep-dive.md)——Codex `reasoning_effort` (6 档 + plan-mode 专用) vs Claude `/effort` (4 档) 设计对比

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
| [26](#item-26) | Sticky Environment 会话级环境变量选择 | **P2** | `app-server/` v2 thread state | ~500 行（PR#18897）|
| [27](#item-27) | Permission Profiles 统一权限档位 | **P2** | `core/` + `app-server/` + `tui/` + `mcp/` + `exec-server/` | ~1,500 行（6 PR）|
| [28](#item-28) | `excludeTurns` 分页加载 Thread | **P3** | `app-server/` v2 thread_fork/resume | ~420 行（PR#19014）|
| [29](#item-29) | External Agent Config + Session 迁移导入 | **P2** | `external-agent-migration/` + `external-agent-sessions/` | ~3,607 行 |
| [30](#item-30) | Plugin 系统 + Marketplace 🆕 | **P2** | `core-plugins/` + `plugin/` | 23,565 行 |

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

**2026-05-24 状态更新**：Codex 2026-05 新增 `codex-rs/bwrap/` 独立 crate（45 行 wrapper + build.rs，引入 PR `26f355b67b`）—— **Linux Bubblewrap 二进制现 bundled 进发行**，开箱即用，用户不需要预装 `bwrap`。这降低了 Linux 沙箱的部署门槛，Qwen Code 若做 Bubblewrap 集成，应同样考虑 bundled 路径。

**2026-06-13 状态更新**：Windows 沙箱前进一步——v0.136.0 新增 `codex sandbox setup --elevated` 管理员预配路径（alpha，#24831）+ Windows 沙箱实现的 requirements 声明（#23766）；沙箱内**强制 proxy-only 联网**更一致（#27035，与 item-7 网络代理联动）；macOS/Linux 发行随包 bundled patched zsh helper（#23756/#24171）。

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

**2026-06-13 状态更新**：Feature flag 进入**云端管控**阶段——新 crate `cloud-config/`（2,376 行，由 `cloud-requirements` 重构而来）支持企业下发 **cloud-managed config bundles**（含 feature flags + requirements + EDU workspace，v0.137.0 #24617~#24622）；`/new` `/clear` `/fork` 等 thread reset 不再丢失云端管控的 flags（#25177）。企业管理面同时获得 monthly credit limits 展示（#24812）。Qwen Code 若做企业版，flag 注册表应预留"远端 source"一层。

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

**2026-06-13 状态更新**：会话生命周期管理继续完善——**`/archive` + `codex archive/unarchive` 会话归档**（归档后防 resume/fork，可恢复，v0.136.0 #25027/#25021）；`resume --last` 先查 state DB 大幅提速大历史恢复（#26462）；**本地会话历史全文搜索**（大小写不敏感 + 结果预览，v0.134.0 #23519/#23921）。注：Qwen Code 在 fork（`/branch`/`/fork`，PR#3539）与 resume 搜索（PR#3880）上已达成 parity，差距收窄到 archive 与 turn 级 fork。

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

**2026-05-24 状态更新**：Codex 2026-05 新增 `codex-rs/app-server-transport/`（9,150 行，PR `51bfb5f3b1`）—— 把 transport 层抽到独立 crate，含 websocket + stdio + auth guard + connection management；同时新增 `codex-rs/app-server-daemon/`（3,015 行，PR `1752f374a8`）为远端 SSH Codex 实例提供 app-server lifecycle 管理（`codex daemon start/stop/status`）。Qwen Code 借鉴 IDE 协议时可参考这套 transport 分层 + remote lifecycle 设计。

**2026-06-13 状态更新**：控制面继续扩张——`codex app-server --stdio` 启动模式（#24940）、账户 token usage 查询（#25344）、auth v2 Personal Access Token（#25731）；**remote-control 走 app-server v2 RPC**：配对发起 + controller grants 列举/撤销（v0.137.0 #25675/#25785）、websocket 用短时 server token 取代 ChatGPT access token（#24141）、desired state 持久化（#27445）。这套"远程控制配对 + 授权可审计可撤销"的安全模型，可对照 Qwen Code daemon 的 bearer token 体系（参见 [daemon 安全](./qwen-code-daemon-design/05-permission-auth.md)——pair token / per-client 撤销正在 backlog）。

**2026-06-20 状态更新**：remote environment 连接生命周期成形——core 侧连接 lifecycle + 启动中 environment 入 snapshot 追踪 + app-server 侧连接超时配置三连（#28674/#28683/#29025）。配合 exec-server 的远端环境（item-25），app-server 正从"本地 IDE 协议"扩展为"多主机远程环境控制面"。

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

**2026-05-24 状态更新**：Codex 2026-05 新增 `codex-rs/agent-graph-store/`（454 行，PR `782191547c`）—— 存储与查询 thread-spawn 的父子拓扑关系，为多 agent 协作提供结构化存储边界。Qwen Code 做多 agent 编排时可参考这种"先建图存关系再 spawn"的模式，便于事后追踪和调试。

**2026-06-13 状态更新**：multi-agent v2 进入资源治理阶段——agent **residency LRU**（限制驻留 agent 数，#26632）、并发额度按"活跃执行"而非 spawn 数计量（#26969）、`close_agent` 改名 `interrupt_agent` 语义更准确（#26994）、resume 时不自动复活 v2 后代 agent（#26997）、runtime 选择随 thread 保持 + spawned agent 的 follow-up/metadata 默认值清理（v0.137.0）。Qwen Code 的 Agent Team（实验中）做并发治理时可借鉴 LRU + 活跃执行计量。

**2026-06-20 状态更新**：从"能并行"到"可控何时并行"——新增 **per-turn multi-agent mode**（#28685，`turn/start.multiAgentMode` = `explicitRequestOnly` / `proactive`，受 `features.multi_agent_mode` gate）+ **thread 级 mode**（#28792，`thread/start`/`resume`/`fork` 返回并保持 mode）。Qwen Code 的 Agent Team 可借鉴这种"按 turn/会话声明并行策略"的开关粒度。

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

**2026-06-13 状态更新**：0.140.0-alpha 三连 PR 把 secrets 升级为 **CLI auth 的存储底座**——secret auth 存储配置（#27504）→ auth 专用加密 namespace（#27535）→ **CLI auth 凭据改用加密本地 secrets 存储**（#27539）。即从"可选的密钥管理工具"变成"认证链路的默认基础设施"，无 OS 密钥环的环境（容器/CI）也有加密落盘路径。Qwen Code 的 Qwen OAuth creds 目前明文 JSON 落盘（`~/.qwen/oauth_creds.json`，仅 `0o600` 权限保护，源码: `packages/core/src/qwen/sharedTokenManager.ts#L634`；MCP token 已有 keychain/hybrid 存储但 OAuth 链路未复用），此项优先级建议上调。

**2026-06-20 状态更新**：MCP OAuth 凭据也改用加密本地 secrets 存储（#27541）——secrets 作为认证底座的覆盖面从 CLI auth 扩展到 MCP OAuth。Qwen Code 的 MCP token 已有 keychain，但 Qwen OAuth 链路仍明文，差距不变。

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

**2026-06-20 状态更新**：MCP 表面按环境作用域化——MCP sandbox metadata 按 server environment 作用域（#28914）、MCP 文件上传走 environment filesystem（#27923）、默认工具超时升到 300s（#28234）、marketplace plugin manifest fallback（#28789，与 item-30 联动）。

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

**2026-06-13 状态更新**：Code Mode 从"轻量沙箱"升级为**主要执行范式之一**——拆出 `code-mode-protocol/`（1,452 行）+ `code-mode-host/` 独立 crate（协议与宿主分层）；code mode 内可调用 hosted web/image 工具、**独立 web search 可并行执行 + 从嵌套 JS 工具调用发起**（v0.137.0 #25176/#25702/#25890、v0.139.0 #26719）。底层 V8 随 `rusty_v8` 149.2.0 更新。其定位已接近 Cloudflare "Code Mode"（用 JS 执行环境替代逐次工具调用），与 Qwen Code 的 Workflow 工具（脚本编排多 agent）属相邻方向，可互为参照。

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

**2026-06-20 状态更新**：exec-server 远程执行密集打磨——**Noise 协议成默认传输**（#26245，取代 legacy）+ Noise rendezvous 环境（#28774）、分块流式传文件（#28354）、honor 远端 environment 的 cwd/shell（#28122）、重连刷新签名 URL（#28374）、暴露 environment registry payload（#28651）。远程执行从"能跑"走向"安全默认 + 环境一致"。

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

**2026-06-20 状态更新**：environment 上下文进一步原生化——app-server 保留 target-native environment cwd（#28146）、core 侧 native 渲染 remote environment cwd（#28152）。env 选择从"会话级粘性"延伸到"远端环境路径一致性"。

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

**2026-06-13 状态更新**：Permission Profiles **已全面产品化**——v0.134.0 用八连 PR（#23708~#24110）把 `--profile` 升级为 CLI/TUI/沙箱流程的**主选择器**（旧式 profile 配置直接拒绝 + 迁移指引）；v0.135.0 `/permissions` 识别并展示命名 profile（#21559）；v0.139.0 新增 `-P` 短参数 alias（#27054）。该项从"6 PR 协同的新机制"进入"默认交互路径"，Qwen Code 对标价值进一步上升。

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

<a id="item-29"></a>

### 29. External Agent Config + Session 迁移导入（P2）

**问题**：用户已经在 Claude Desktop / Cursor / 其他 AI 工具上配了一堆 MCP server / hooks / custom commands / subagents，迁到 Qwen Code 要全手动重配；旧工具的会话历史也带不过来。社区里"迁移友好度"是 AI agent 工具增长的重要变量。

**Codex 的解决方案**（2026-05 引入两个独立 crate，**total ~3,607 行**）：

| Crate | 行数 | 引入 PR | 用途 |
|---|---|---|---|
| `external-agent-migration` | 2,141 | `cb8b1bbcd6` | 检测并转换外部 agent 的 MCP servers / hooks / commands / subagents 配置 |
| `external-agent-sessions` | 1,466 | `4c68bd728f` | 从外部 agent 的会话文件检测并导入到 Codex rollout 历史 |

**核心设计**：

```
~/.claude / ~/.config/cursor / ~/.config/<other-agent>
   ↓ detect (auto-scan known agent paths)
保守转换管道（仅导入安全可表示的配置）
   ↓
Codex config + rollout/sessions（带 import ledger 追踪来源）
```

- **保守转换** —— 不是 1:1 复制，对每类配置（MCP / hooks / custom commands / subagents）单独写 mapper，无法可靠表达的 silently skip + 报告给用户
- **Import ledger** —— 记录每条 imported entry 的源 agent + 源 path + 时间戳，让用户可以审计 / 撤销
- **Session 导入** —— 检测外部 agent 的会话文件（YAML/JSON 各种格式），解析后生成 Codex 标准 rollout 记录；大 session 会自动 compaction 后再 resume，不会一次性吞掉 1000+ turn

**Qwen Code 现状**：完全没有外部 agent 迁移机制。Qwen 用户从 Claude Code / Cursor / 其他工具切过来都是手动重新配。

**Qwen Code 修改方向**：
1. 定义 `external_agent_detector` 接口：扫描 `~/.claude` / `~/.config/cursor` / `~/.config/aider` 等，识别 agent + version
2. 为每个支持的外部 agent 写 `<source-agent>_mapper`：MCP / hooks / slash commands / subagents 各一个 mapper
3. 新 slash command `/import` 或 CLI 子命令 `qwen import --from claude-code` 触发
4. Import ledger 存到 `~/.qwen/imports.jsonl`，每条带 source-agent / source-path / import-time / status
5. Session 导入需 compaction —— 调用 `ChatRecordingService` 的 summarize 流程把 1000+ turn 压成 1 个 summary turn 再 resume
6. UI: 首次启动 detect 到外部 agent 时给一次性 prompt "检测到 Claude Desktop 配置，是否导入？(y/n)"

**实现成本**：~2-3 周（1 人）—— detect + 多 agent mapper 矩阵 + compaction 集成 + import ledger + UI prompt

**意义**：用户迁移友好度从"清零重配"变成"一行命令导入"，是用户增长的关键变量。

**改进收益**：Claude Code / Cursor / Aider 用户切换 Qwen Code 的摩擦从"花 30 分钟重配"降到"5 秒导入 +  几分钟核对"。

**2026-06-13 状态更新**：本窗口持续打磨——session 导入提速（#26637）、source-specific import copy 恢复（#27703）、`AGENTS.md` 从所有 bound environment 加载（#27696）。

**2026-06-20 状态更新**：导入可审计性补齐——**记录导入结果**（#28396）：按 config / AGENTS.md / skills / plugins / MCP / subagents / hooks / commands / sessions 分组记录成败，并新增 `externalAgentConfig/import/readHistories` 恢复 API。正好对应 Qwen 修改方向第 4 点（import ledger）——可直接参照这套"分组件成败 + 可回读"结构。

---

<a id="item-30"></a>

### 30. Plugin 系统 + Marketplace 🆕（P2）

**问题**：Qwen Code 的 extensions 系统有三格式兼容（Claude / Gemini / Qwen 转换器）和 `/extensions explore` 市场，但**分发与运营形态薄**：没有 bundle 归档分发（插件 = git repo / 本地目录）、没有 marketplace 多源管理（用户不能 add/remove 市场源）、没有 cached remote catalog（每次浏览都要现拉网络）、没有插件详情面（看不到插件带的 prompts / MCP servers / 模板）、没有分享 URL。生态运营基建落后于 Claude Code 与 Codex。

**Codex 的解决方案**：`core-plugins/`（**22,721 行**）+ `plugin/`（844 行）——完整的插件分发运营体系：

- **CLI 全家桶**：`codex plugin add / remove / list / marketplace ...`，全部支持 `--json` 机器可读输出（#26631/#26417/#25330）
- **Marketplace 多源**：用户可注册多个市场源；`marketplace list --json` 暴露每个插件的来源（#27009）
- **Cached remote catalog**：插件列表先回本地缓存、后台刷新（#26932），curated cache 自动清理过期项（#26934）
- **Plugin bundle 归档**：插件打包上传/安装（#23983）
- **插件详情面**：暴露 default prompts、remote MCP servers、app templates（#25887/#26453/#26317）
- **Remote plugin share URL**：一个 URL 分享插件（#27890）
- **启动性能**：TUI 关键路径只加载 hook metadata，复用 discovery 结果（#26469/#26272）

> **补录说明**：`core-plugins` 于 **2026-03-25** 引入（`9dbe098349`），早于上次审计窗口，但 2026-05-24 审计只扫描了"新增 crate 增量"而漏判了它；本窗口该方向被密集打磨（0.137–0.140 每个版本都有 plugin PR），故补录为独立 item。

**Qwen Code 现状**：extensions 三格式转换器 + `/extensions explore/install/manage` + `qwen extensions new` 脚手架；无 bundle、无市场源管理、无缓存目录、无 share URL、无 `--json`。

**Qwen Code 修改方向**：
1. `qwen extensions` 子命令支持 `--json` 输出（CI / 脚本自动化）
2. marketplace 多源：`qwen extensions marketplace add <url>`，源信息进 settings
3. cached catalog：`~/.qwen/extensions-catalog.json` 先回缓存后台刷新
4. extension bundle：`qwen extensions pack` 打包归档分发（不依赖 git clone）
5. 详情面：`/extensions` 详情页展示扩展携带的 commands / MCP servers / skills

**实现成本**：~2 周

**2026-06-20 状态更新**：本窗口最密集方向（~19 PR）——marketplace manifest fallback（#28789）、root 本地 marketplace 源（#28771）、auth 门控的 remote catalog（#28625）、从选中插件发现 stdio MCP server（#27870）、recommended-plugin endpoint 四连栈（#28399~#28403）、plugin metadata 缓存供工具建议（#27812）、namespace 感知的 skill 加载（#28608）。生态运营基建持续拉开与 Qwen extensions 的差距，item-30 对标价值进一步上升。

---

## 二、竞品对比矩阵

| 能力 | Codex CLI | Claude Code | Gemini CLI | Qwen Code |
|------|----------|-------------|-----------|-----------|
| **技术栈** | Rust 原生 | TypeScript/Rust | TypeScript | TypeScript |
| **代码规模** | 1,043,805 行（.rs） | ~512,000 行 | ~550,000 行 | 1,381,340 行（packages .ts/.tsx，含 daemon/web-shell/desktop） |
| **默认沙箱** | ✅ 3 平台原生 | 可选 | 可选 | 可选（Docker/Podman/Seatbelt） |
| **网络隔离** | ✅ 默认阻断 | 可选 | 无 | ❌ |
| **Feature Flag** | 52 运行时 + 云端管控（cloud-config） | 22 编译时 | 无 | ❌ |
| **IDE 协议** | 90+ JSON-RPC | WebSocket Bridge | VS Code Companion | daemon REST+SSE / ACP HTTP+WS（29 method parity） |
| **会话 Fork** | ✅（+ /archive 归档） | ✅ | ✅ | ✅（/branch /fork，v0.18） |
| **Cloud 执行** | ✅ best-of-N | Kairos | 无 | ❌ |
| **MCP 双向** | ✅ 客户端+服务器 | 客户端 | 客户端 | ✅ 客户端+服务器（qwen-serve-bridge） |
| **语音** | ✅ WebRTC | ✅ 内置 | 无 | ❌ |
| **多 Agent** | ✅ V2 并行（residency LRU + per-turn/thread 模式选择） | Coordinator/Swarm | 无 | Arena（竞赛）+ Agent Team（实验） |
| **Apply Patch** | ✅ unified diff | Edit 逐文件 | Edit | Edit |
| **密钥管理** | ✅ OS 密钥环 + 加密本地（0.140α） | 无 | 无 | ❌（MCP token 有 keychain，OAuth 明文） |
| **Ghost Commit** | ✅ | 检查点 | 无 | /rewind 跨会话文件快照（#4897） |
| **插件市场** | ✅ 多源 + bundle + share URL | ✅ 官方市场 | 扩展 | 扩展市场（explore） |

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
| **开源 + BYOK 任意 provider** | Apache-2.0，可接 OpenAI/Anthropic/Gemini 兼容端点（含 DeepSeek 等低价选项）；Qwen OAuth 免费层 2026-04-15 已停，现需订阅/BYOK |
| **多渠道部署** | DingTalk/Telegram/WeChat/Web |
| **国际化** | 6 语言 i18n |
| **Gemini CLI 兼容** | fork 自 Gemini CLI，共享上游改进 |
| **多格式扩展** | Claude + Gemini + Qwen 三格式兼容 |

## 五、更新日志

### 2026-06-20（Codex 上游 `git pull` · 0 新增 item · refinement-heavy 窗口）

**Codex 源码扫描**：`2026-06-12 → 2026-06-19` 间 **231 commits**，HEAD `64bdeed9f7`。`codex-rs/**/*.rs` LOC **992,581 → 1,043,805**（+51,224，+5.2%）。**本窗口 0 个 crate 新增/移除**——+51k 行全部来自既有 crate 内部演进（plugin / multi-agent / remote-env / exec-server 等）；源码内无新 release tag（仍在 v0.140 线推进，workspace 版本号 `0.0.0`）。

**crate 计数口径修正（baseline）**：本报告此前沿用的 "97 crate" 系旧口径（漏计 `ext/*` 等嵌套 crate）；现按 cargo workspace `members` 实测 baseline 到 **121**（无 glob；`codex-rs` 下 127 个 `Cargo.toml` 中 6 个为 example/排除的非 member crate）。该值在 2026-06-13（`56c97e3b5c`）当时即已成立——**本窗口 crate 数零变动**，baseline 修正仅为口径对齐，不代表新增。

**Qwen Code 侧口径说明**：`packages/**/*.ts(x)` origin/main **1,292,728 → 1,381,340**（+88,612，channel/web-shell 等持续并入，非同口径可比）。

**本窗口主题**（无新 item，全部归入既有 30 项）：

1. **Plugin / Marketplace 生态**（[item-30](#item-30)，~19 PR，最密集方向）：marketplace manifest fallback（#28789）、root 本地 marketplace 源（#28771）、auth 门控 remote catalog（#28625）、从选中插件发现 stdio MCP server（#27870）、recommended-plugin endpoint 四连栈（#28399~#28403）、plugin metadata 缓存（#27812）、namespace 感知 skill 加载（#28608）。
2. **Multi-Agent V2 模式选择**（[item-9](#item-9)）：**per-turn mode**（#28685，`explicitRequestOnly` / `proactive` + `features.multi_agent_mode` gate）+ **thread 级 mode**（#28792）——从"能并行"到"可控何时并行"。
3. **Remote Environments 基础设施**（[item-8](#item-8) / [item-25](#item-25) / [item-26](#item-26)）：remote env 连接生命周期三连（#28674/#28683/#29025）、exec-server **Noise transport 成默认**（#26245）+ rendezvous（#28774）、env-aware cwd/shell（#28122）、native env cwd 渲染（#28146/#28152）。
4. **External Agent 导入可审计**（[item-29](#item-29)）：记录导入结果（#28396，按组件分组记成败 + `import/readHistories` 恢复 API）。
5. **Secrets 认证底座延续**（[item-12](#item-12)）：MCP OAuth 凭据改用加密本地 secrets（#27541）——延续 0.140α "secrets 成认证底座"方向。
6. **MCP / 审批按环境作用域**（[item-5](#item-5) / [item-18](#item-18)）：命令与网络审批按 execution environment 作用域化（#28738/#28899）、MCP sandbox metadata 按 server environment 作用域（#28914）、默认工具超时升到 300s（#28234）。

#### 值得提及但未单列 item

| 方向 | PR | 为何不单列 |
|---|---|---|
| **Rollout/Token Budget 跨线程硬上限**（耗尽即 abort 新 turn）| #28746/#28494/#28707 | Qwen Code 的 Workflow `budget`（`budget.total` 硬上限、耗尽即 `agent()` throw）已是相邻能力，属两侧趋同 |
| **System Clock 工具**（`current-time` 工具 + time reminders）| #28822/#28824/#28835/#29011 | 新增系统工具，Qwen 可低成本等价实现（已有 `loop_wakeup`/`cron` 时间类工具）|
| Response item ID / UUIDv7 context window IDs | #28953/#28812/#28814/#29012 | resume/fork/compaction 的内部可追踪性基建，无独立用户能力 |
| PathUri / ApiPathString 路径迁移 | #28854/#28780/#28165 等 | 跨平台路径处理硬化（remote env / Windows exec-server），架构重构 |
| Windows 沙箱 ACL 刷新修复（[item-1](#item-1)）| #28943 | 工程修复 |
| 移除实验性 child `AGENTS.md` 注入 | #28993 | 实验清理 |

#### Item refinement（8 项刷新，详见各 item 内联"2026-06-20 状态更新"）

| Item | 刷新内容 |
|---|---|
| [item-8](#item-8) | remote environment 连接生命周期三连（#28674/#28683/#29025）|
| [item-9](#item-9) | per-turn / thread 级 multi-agent mode 选择（#28685/#28792）|
| [item-12](#item-12) | MCP OAuth 凭据改用加密本地 secrets（#27541）|
| [item-18](#item-18) | MCP sandbox metadata 按环境作用域（#28914）；默认工具超时 300s（#28234）|
| [item-25](#item-25) | Noise transport 成默认（#26245）+ rendezvous + 分块传文件 + env-aware cwd/shell |
| [item-26](#item-26) | native environment cwd 跨 turn 保留（#28146/#28152）|
| [item-29](#item-29) | 记录导入结果 + `import/readHistories` 恢复 API（#28396）|
| [item-30](#item-30) | marketplace 多源/本地源/auth 门控/plugin-MCP 发现 等 ~19 PR |

---

### 2026-06-13（Codex 上游 `git pull` + release notes 对照 · 补录 1 项 + 11 项 refinement）

**Codex 源码扫描**：`2026-05-22 → 2026-06-12` 间 **616 commits**，HEAD `56c97e3b5c`。Codex `codex-rs/**/*.rs` LOC **909,950 → 992,581**（+82,631，+9.1%），crate 数 → **97**（旧口径；2026-06-20 已 baseline 到 121 workspace members）。本次同时对照 **release notes v0.134.0 → v0.139.0（stable）+ 0.140.0-alpha 线**逐版核对（此前仅源码扫描）。

**Qwen Code 侧口径说明**：daemon / web-shell / desktop / SDK 合入 main 后，`packages/**/*.ts(x)` 从 631,020 → **1,292,728 行**——增长主要来自新包并入，非同口径可比。

**新增 6 个 crate**（移除 2 个：`cloud-requirements`→重构为 `cloud-config`、`debug-client`）：

| Crate | 行数 | 关系 |
|---|---|---|
| `cloud-config` | 2,376 | item-3 refinement（云端管控 config bundles + credit limits）|
| `code-mode-protocol` + `code-mode-host` | 1,452 + 19 | item-23 refinement（协议/宿主分层）|
| `prompts` | 1,848 | 内部重构（系统提示集中化：agents/apply_patch/compact/goals/permissions）|
| `codex-home` | 265 | 内部重构 |
| `context-fragments` | 253 | 内部重构 |

**补录 1 项 item**（[item-30](#item-30) Plugin 系统 + Marketplace）——`core-plugins`（22,721 行）2026-03-25 已引入，上次审计只扫"新增 crate 增量"而漏判；本窗口 0.137~0.140 每版都有 plugin PR（marketplace 多源 `--json` / cached catalog / bundle 归档 / share URL），故补录。

#### Item refinement（11 项刷新）

| Item | 刷新内容 |
|---|---|
| [item-1](#item-1) | Windows `codex sandbox setup --elevated`（alpha，#24831）；沙箱内强制 proxy-only 联网（#27035）；bundled patched zsh |
| [item-3](#item-3) | `cloud-config` crate：企业 cloud-managed config bundles + monthly credit limits + EDU（v0.137.0）|
| [item-4](#item-4) | `/archive` 会话归档（v0.136.0）；`resume --last` 走 state DB；本地会话历史全文搜索（v0.134.0）|
| [item-8](#item-8) | `app-server --stdio`；账户 token usage；auth v2 PAT；remote-control 配对/grant 撤销走 v2 RPC + 短时 server token |
| [item-9](#item-9) | residency LRU；并发按活跃执行计量；`close_agent`→`interrupt_agent`；resume 不复活 v2 后代 |
| [item-12](#item-12) | **0.140α：CLI auth 改用加密本地 secrets**（#27504/#27535/#27539）——从可选工具升级为认证底座 |
| [item-16](#item-16) | auto review 跨 config/delegation 保持（#26230）|
| [item-23](#item-23) | code-mode-protocol/host 分层；code mode 内 hosted web/image 工具 + 独立 web search 并行/嵌套调用 |
| [item-27](#item-27) | **产品化完成**：`--profile` 成为主选择器（v0.134.0 八连 PR）+ `/permissions` 显示命名 profile + `-P` alias |
| [item-28](#item-28) | app-server resume 可带首页 turns（#23534）——excludeTurns 模式产品化 |
| [item-29](#item-29) | session 导入提速（#26637）；AGENTS.md 从所有 bound environment 加载（#27696）|

#### 上次排除的 4 个 feature 复查

review-story / next-prompt suggestion / usage attribution / prompt hooks——616 commits 内按名称 grep **零命中，仍未 merge 到 main**，继续不计入。

#### 两侧趋同（不单列 item）

| Codex 侧 | Qwen Code 对应 |
|---|---|
| `ext/goal` 4,418 行 + `/goal edit` 工作流（0.138 修 idle auto-turn / 终态停续）| `/goal`（"keep working until the condition is met"）+ MAX_GOAL_ITERATIONS（#5000）|
| `ext/memories` 2,565 行（外部工具输出排除出 memories，#26821）| 托管自动记忆（`/remember` `/forget` `/dream`）|
| `/app` 把 CLI thread 移交 Codex Desktop（macOS/Windows，0.138）| 官方桌面 app（#3778，Electron + ACP）|
| 本地会话历史全文搜索（0.134）| `/resume` free-text 搜索（PR#3880）|
| `.codex/skills/babysit-pr`（仓库内 dogfood skill，PR 自动盯梢）| —（属 skill 用法非产品能力，不计 item）|

---

### 2026-05-24（Codex 上游 `git pull` · 新增 1 项 + 4 项 refinement）

**Codex 源码扫描**：`2026-04-24 → 2026-05-22` 间 **1043 commits**，HEAD `7d47056ea4`。Codex LOC **651,174 → 909,950**（+258K，+40%）。

**新增 13 个 crate**（核心方向）：

| Crate | 行数 | 关系 |
|---|---|---|
| `external-agent-migration` / `external-agent-sessions` | 2,141 + 1,466 | **新方向 item-29** |
| `agent-graph-store` | 454 | item-9 refinement |
| `app-server-transport` | 9,150 | item-8 refinement (transport 分层) |
| `app-server-daemon` | 3,015 | item-8 / item-25 overlap (remote lifecycle) |
| `bwrap` | 45 | item-1 refinement (bundled binary) |
| `file-watcher` | 1,393 | 内部重构 |
| `message-history` | 633 | 内部重构 |
| `file-system` | 192 | 内部重构 |
| `core-api` | 79 | SDK 文档 / API stability surface |
| `thread-manager-sample` | 385 | 官方 ThreadManager 示例 |
| `ext/{memories,guardian,extension-api,goal}` | ~2,500 | 扩展生态模块化（早期，未独立 item） |

**只新增 1 项 item**（item-29 External Agent 迁移）—— 其他 12 个新 crate 均为已有 item 的 refinement 或内部重构。

#### 重要排除：本次审计排除了 4 个看似新的方向

源码审计严格按 "**只算 merge 到 `origin/main` 的代码**" 标准过滤。以下 4 个 feature commit 出现在 1043 commits 列表里但**不在 main 分支**（PR/feature branch only），不计入 Codex 已发布能力：

| Feature 名 | 引入 commit | 在 main? | 备注 |
|---|---|---|---|
| review-story（model-backed code review narrative） | `5e8a5b2c7c` | ❌ | 2026-05-23 PR 分支，未合，可能仍在改 |
| next-prompt suggestion engine | `a0d7b8e4cd` / `78e459feb8` / `f00ebd615c` | ❌ | 2026-05-22 PR 分支，未合 |
| usage attribution（token usage breakdown）| `b79ed47409` / `357d7118ac` / `138376e6e1` | ❌ | 2026-05-22 PR 分支，未合 |
| prompt hooks（动态 prompt 注入）| `1a3f6444e3` | ❌ | PR 分支，未合 |

这 4 项若未来 merge 到 main，可在下次 review 时再单列 item。

#### Item refinement（已有 28 项里需刷新数字 / 状态）

| Item | 刷新内容 |
|---|---|
| [item-1](#item-1) | 新增 `bwrap` crate (bundled Linux Bubblewrap binary) — PR `26f355b67b` |
| [item-8](#item-8) | 新增 `app-server-transport` (9,150 行) + `app-server-daemon` (3,015 行) — PR `51bfb5f3b1` / `1752f374a8` |
| [item-9](#item-9) | 新增 `agent-graph-store` (454 行) thread-spawn 父子拓扑存储 — PR `782191547c` |
| [item-25](#item-25) | `app-server-daemon` 提供 SSH 远端 lifecycle 管理（与 item-8 共享）|

#### 次要变更不单列 item

| commit | 方向 | 不单列原因 |
|---|---|---|
| `c579da41b1` / `2004173cd7` | `file-watcher` / `message-history` 从 core 提取 | 架构重构，无新用户能力 |
| `26f355b67b` | bwrap binary bundle | item-1 工程改进 |
| `51bfb5f3b1` | app-server-transport restore | item-8 传输细节 |
| `1752f374a8` | app-server-daemon | item-8 / item-25 lifecycle 细化 |
| `9dcc4130cf` | code-mode durable session interface | item-23 深化，未公开特性 |
| `5bc43bd551` | experimental turn additional context | item-26 (Sticky Environment) 上下文扩展 |
| `3094e2b6b0`+ | agent task identity + ChatGPT opt-in | item-27 身份细化 |

---

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

*分析基于 Codex CLI (openai/codex, Apache-2.0, 121 Rust crate, **1,043,805 行** `codex-rs/**/*.rs`) 和 Qwen Code 源码 (**1,381,340 行** `packages/**/*.ts(x)`)。最后核对：2026-06-20（Codex `56c97e3b5c → 64bdeed9f7`，231 commits，refinement-heavy 窗口，0 新增 crate / item）。审计标准：仅算 merge 到 `origin/main` 的代码，PR/branch 上未合 feature 不算 Codex 已发布能力。*
