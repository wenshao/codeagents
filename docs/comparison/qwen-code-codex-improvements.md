# Qwen Code 改进建议——对标 Codex CLI

> 基于 Codex CLI (openai/codex) 完整 Rust 源码（70+ crate，619,458 行）与 Qwen Code 源码的系统对比，识别 **25 项**可借鉴的能力。Codex CLI 是唯一采用 Rust 原生构建 + 默认沙箱的主流 CLI Code Agent。
>
> **相关报告**：
> - [Claude Code 改进建议报告（248 项）](./qwen-code-improvement-report.md)——行业领先者对比
> - [Gemini CLI 上游 backport 报告（53 项）](./qwen-code-gemini-upstream-report.md)——上游可 backport 改进
> - [OpenCode 对标改进报告（27 项）](./qwen-code-opencode-improvements.md)——多 Provider、Plugin 系统等

## 一、改进项索引

| # | 功能 | 优先级 | 来源 crate | 规模 |
|:-:|------|:------:|-----------|:----:|
| [1](#item-1) | 默认沙箱安全模型（3 平台） | **P0** | `sandboxing/` + `linux-sandbox/` + `windows-sandbox-rs/` | 17,315 行 |
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
| [13](#item-13) | Hook 系统（5 种事件） | **P2** | `hooks/` | 5,373 行 |
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

---

<a id="item-1"></a>

### 1. 默认沙箱安全模型（P0）

**问题**：Qwen Code 执行 shell 命令时无进程隔离——Agent 可以访问全部文件系统和网络，secrets 可能泄漏。

**Codex CLI 的解决方案**：3 平台原生沙箱，**默认启用，网络默认阻断**：

| 平台 | 实现 | 规模 | 隔离级别 |
|------|------|:----:|---------|
| macOS | Seatbelt（`sandbox-exec`） | ~1,600 行 | read-only / restricted-read / workspace-write / danger-full-access |
| Linux | Bubblewrap + Landlock 回退 | ~4,000 行 | 命名空间隔离 + 内核级文件控制 |
| Windows | 受限令牌（restricted token） | ~9,757 行 | 实验性 |
| 通用 | `sandboxing/` 管理器 + 测试 | ~2,000 行 | 平台适配层 |

**Qwen Code 修改方向**：先实现 Linux Landlock（最简单，内核 5.13+），再扩展 macOS Seatbelt。

**实现成本**：~2 周（Linux 优先），参考 Claude Code 改进报告 [stability#30](./qwen-code-improvement-report-p2-stability.md#item-30)。

---

<a id="item-2"></a>

### 2. Apply Patch 批量文件修改（P1）

**问题**：Qwen Code 的 Edit 工具逐文件修改，多文件原子变更需要多次工具调用。GPT 系列模型原生输出 unified diff 格式。

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

**问题**：Qwen Code 缺少统一的 Feature Flag 系统，实验性功能无法安全地渐进交付。

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

**问题**：Qwen Code 的 `--resume` 仅恢复最近会话，不支持从任意 turn 恢复或分叉探索。

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

**问题**：Qwen Code 仅做 AST 级读写分类，无法检测 `rm -rf /`、`git push --force` 等危险命令的具体风险。

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

**问题**：Agent 可能在命令中嵌入 `sudo`/`doas` 提升权限，当前无检测机制。

**Codex CLI 的解决方案**：`shell-escalation/`（2,215 行）：
- 执行时策略强制检查
- Socket 协议协调 sudo/doas 提示
- 每命令权限追踪
- 执行计时度量

**实现成本**：~3 天

---

<a id="item-7"></a>

### 7. 网络代理 + MITM 策略（P1）

**问题**：Agent 执行 `curl`/`npm install` 时的网络请求不受控制，可能泄漏数据。

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

**问题**：Qwen Code 无标准化 IDE 集成协议。

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

**问题**：Qwen Code 的 Agent 工具仅支持串行 Subagent，无真正的并行执行和状态同步。

**Codex CLI 的解决方案**：`multi_agents_v2`——
- spawn/close/send_message/wait_agent 工具
- Agent Job CSV 状态追踪
- 广度优先 vs 深度优先执行策略
- Agent 生命周期事件

**实现成本**：~2 周，参考 Claude Code 改进报告 [engine#14](./qwen-code-improvement-report-p0-p1-engine.md#item-14)。

---

<a id="item-10"></a>

### 10. Models Manager 模型目录（P2）

**问题**：模型能力信息（上下文窗口、推理能力、成本）散落在代码中，无统一目录。

**Codex CLI 的解决方案**：`models-manager/`（2,072 行）——内置 `models.json` 目录 + 模型预设 + 协作模式配置 + 弃用状态跟踪。

**实现成本**：~2 天

---

<a id="item-11"></a>

### 11. Git Ghost Commit 快照（P2）

**问题**：Agent 修改代码后难以无侵入地创建快照回滚点。

**Codex CLI 的解决方案**：`git-utils/`（4,024 行）——Ghost commit 不进入 git 历史，支持快照/恢复/diff 报告 + 大未追踪目录检测。

**实现成本**：~3 天，与 OpenCode [Snapshot](./qwen-code-opencode-improvements.md#item-11) 互补。

---

<a id="item-12"></a>

### 12. Secrets Manager 密钥管理（P2）

**问题**：API 密钥通过环境变量传递，无作用域隔离。

**Codex CLI 的解决方案**：`secrets/`（~682 行）——OS 密钥环后端 + Global/Environment 双作用域 + 安全路径哈希。

**实现成本**：~2 天

---

<a id="item-13"></a>

### 13. Hook 系统——5 种事件（P2）

**问题**：Qwen Code 的 Hook 系统与 Claude Code（27 种事件）差距较大。

**Codex CLI 的解决方案**：`hooks/`（5,373 行）——5 种事件：SessionStart、UserPromptSubmit、PreToolUse、PostToolUse、Stop。支持 abort/modify/continue 响应。

**实现成本**：~3 天（扩展现有 Hook 系统）

---

<a id="item-14"></a>

### 14. Core Skills 环境依赖发现（P2）

**问题**：Skill 运行时缺少的环境变量（API Key 等）没有提前检测，执行中途才失败。

**Codex CLI 的解决方案**：`core-skills/`（5,243 行）——Skill 加载时检测环境变量依赖，缺失时提示用户设置。

**实现成本**：~2 天

---

<a id="item-15"></a>

### 15. 执行策略引擎（P2）

**问题**：命令执行限制是硬编码的，缺少用户可配置的执行策略。

**Codex CLI 的解决方案**：`execpolicy/`（1,790 行）——基于模式（regex）的前缀规则：`^cargo` → allow、`^rm` → deny、`^git.*--force` → deny。

**实现成本**：~2 天

---

<a id="item-16"></a>

### 16. Code Review 独立子命令（P2）

**问题**：`/review` 作为 Skill 运行，不适合 CI/CD 集成（需要交互式 TUI）。

**Codex CLI 的解决方案**：`codex review` 独立 CLI 子命令——支持 `--uncommitted`/`--base`/`--commit` 参数，无需 TUI，直接输出到 stdout/PR 评论。

**实现成本**：~3 天

---

<a id="item-17"></a>

### 17. Cloud Tasks 云端执行（P2）

**问题**：复杂任务受限于本地资源和单次会话。

**Codex CLI 的解决方案**：`cloud-tasks/`（4,801 行）——提交任务到云端隔离环境执行，best-of-N 多次尝试，完成后 diff 拉回本地。

**实现成本**：~3 周（需要云端基础设施）

---

<a id="item-18"></a>

### 18. MCP Server 模式（P2）

**问题**：Qwen Code 只能调用 MCP 服务器的工具，不能被其他 Agent 以 MCP 协议调用。

**Codex CLI 的解决方案**：`mcp-server/`（2,487 行）——`codex mcp-server` 以 stdio 模式启动，暴露 tools/resources/prompts 能力，支持 MCP 协议 `2024-11-05`。

**实现成本**：~3 天

---

<a id="item-19"></a>

### 19. 多层配置栈（P2）

**问题**：Qwen Code 配置层次扁平，缺少团队级和工作区级覆盖。

**Codex CLI 的解决方案**：`config/`（6,879 行）——5 层配置合并（global → user → project → workspace → workspace-local）+ TOML 解析 + 配置迁移 + Profile 支持。

**实现成本**：~1 周

---

<a id="item-20"></a>

### 20. 终端检测与主题适配（P3）

**问题**：不同终端（SSH、容器、IDE 嵌入）能力差异大，当前无适配。

**Codex CLI 的解决方案**：`terminal-detection/`（1,353 行）——自动检测 Kitty 键盘协议、bracketed paste、色彩深度，适配不同终端。

---

<a id="item-21"></a>

### 21. 实时语音对话（P3）

**问题**：CLI 交互仅限键盘输入，无语音能力。

**Codex CLI 的解决方案**：GPT-4 Realtime 双向流式语音（WebSocket + WebRTC），~8,000 行实现。需要模型支持实时音频 API。

---

<a id="item-22"></a>

### 22. Personality 人格选择（P3）

**问题**：Agent 交互风格固定，无法按用户偏好调整。

**Codex CLI 的解决方案**：TUI 中可选 Agent 人格/风格（`codex features enable personality`），通过 prompt 注入不同交互风格。

---

<a id="item-23"></a>

### 23. Code Mode 轻量沙箱（P3）

**问题**：简单代码执行也需要走完整 Shell 工具流程，开销大。

**Codex CLI 的解决方案**：`code-mode/`（2,746 行）——统一 exec + wait 工具接口，运行时约束（yield 时间、输出 token 上限），嵌套工具检测防止循环。

---

<a id="item-24"></a>

### 24. 请求压缩（Zstd）（P3）

**问题**：大上下文请求传输慢。

**Codex CLI 的解决方案**：可选 Zstd 压缩，减少 30-50% 传输体积。

---

<a id="item-25"></a>

### 25. Exec Server 远程执行（P3）

**问题**：所有代码执行限于本地环境。

**Codex CLI 的解决方案**：`exec-server/`（5,150 行）——RPC 进程管理（start/read/write/terminate），支持远程容器/CI 系统中执行，与本地使用同一 API。

---

## 二、竞品对比矩阵

| 能力 | Codex CLI | Claude Code | Gemini CLI | Qwen Code |
|------|----------|-------------|-----------|-----------|
| **技术栈** | Rust 原生 | TypeScript/Rust | TypeScript | TypeScript |
| **代码规模** | 619,458 行 | ~100,000 行（估） | ~50,000 行 | ~50,000 行 |
| **默认沙箱** | ✅ 3 平台 | 可选 | 可选 | ❌ |
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

### 2026-04-10

- 初始版本：25 项改进建议，基于 Codex CLI 完整 Rust 源码（619,458 行）分析

---

*分析基于 Codex CLI (openai/codex, Apache-2.0, 70+ Rust crate) 和 Qwen Code 源码，截至 2026 年 4 月。*
