# ACP（Agent Client Protocol）支持 Deep-Dive —— Claude Code / Codex / Qwen Code / OpenCode / Qoder CLI

> **核心问题**：5 家 Code Agent 对 Zed 推动的 ACP 协议支持情况如何？谁原生、谁靠外部 adapter、库版本、方法覆盖、IDE 端能力、独家形态各是什么？
>
> 返回 [对比文档总览](./README.md)
>
> **配套文章**：[SDK / ACP / Daemon 架构 Deep-Dive](./sdk-acp-daemon-architecture-deep-dive.md)（574 LOC 全景对比，本文是其 §四 ACP 部分的**焦点化 + 时点刷新**——2026-05-17 源码核实）

## 前言 · ACP 协议是什么

**ACP（Agent Client Protocol）** 是 [Zed Industries](https://zed.dev) 推动的**开放标准协议**，规范 **代码编辑器/IDE ↔ AI 编程 agent** 之间的通信。官网 [agentclientprotocol.com](https://agentclientprotocol.com)，2025 年发布，npm 包 `@agentclientprotocol/sdk`。

### 缘起与设计目标

CLI Agent 生态在 2024-2025 年井喷（Claude Code / Cursor / Cline / Aider / Codex / Qwen / OpenCode / Goose ...），但**每个 agent 接每个 IDE 都要写专属插件**：

```
没有 ACP 时（N × M 集成爆炸）：
  Claude → Cursor 插件 + JetBrains 插件 + VSCode 插件 + Vim 插件 + ...
  Qwen   → Cursor 插件 + JetBrains 插件 + VSCode 插件 + Vim 插件 + ...
  ...

有了 ACP 后（N + M 标准化）：
  Claude / Qwen / OpenCode / ... 各自实现 ACP Agent
  Zed / JetBrains / Avante.nvim / CodeCompanion.nvim / ... 各自实现 ACP Client
  任何 Agent 接任何 IDE = 配一行命令
```

类比：ACP 之于 IDE↔Agent ≈ **LSP 之于 IDE↔Language Server**。Zed 团队明确把 ACP 定位为"agent 版的 LSP"。

### 工作机制

ACP 基于 **JSON-RPC 2.0**，传输用 **stdio NDJSON**（每行一个 JSON 对象）：

```
┌──────────────┐  spawn child   ┌──────────────────┐
│ IDE (Client) │───────────────▶│ Agent (CLI 进程)  │
│              │                │                  │
│  ◀── stdin ──│ NDJSON 双向    │ stdin ──────▶    │
│  ──▶ stdout ─│   JSON-RPC     │ stdout ◀──────   │
└──────────────┘                └──────────────────┘
```

启动时 IDE 一次 `spawn` agent 进程，之后**长连接 stdio** 直到 IDE 关闭。期间 IDE 调 agent 的方法（如 `newSession` / `prompt`），agent 通过 notification 反向推流（如 `session/update` / `permission_request`）。

### 协议三层结构

| 层 | 内容 | 例子 |
|---|---|---|
| **握手层** | `initialize` 协商 protocolVersion + capabilities | `protocolVersion: 1` |
| **会话生命周期** | new / load / list / resume / close / fork session | `newSession`, `listSessions`, `closeSession` |
| **对话流** | prompt / cancel / 工具调用 / 权限审批 | `prompt`, `cancel`, `permission_request` |

**`unstable_` prefix 约定**：spec 尚未稳定的方法用 `unstable_` 前缀（如 `unstable_listSessions`、`unstable_forkSession`），允许实验性能力先 ship 再固化命名。这是个**协议演进缓冲机制**——下游可以选择只实现 stable 子集，也可以激进跟进 unstable。

### 当前生态状态

- **协议版本**：`protocolVersion: 1`（截至 2026-05，所有家都报这个）
- **官方 SDK**：仅 TypeScript（`@agentclientprotocol/sdk` 0.x，从 0.14 演进到 0.21+，方法集持续扩展）
- **第三方实现**：Java（Qwen `com.alibaba:acp-sdk`）—— **目前唯一非官方语言实现**
- **已验证 ACP Client**：Zed、JetBrains AI Assistant、Avante.nvim、CodeCompanion.nvim
- **进展跟踪**：[Zed ACP progress report](https://zed.dev/blog/acp-progress-report#available-now)

### 为什么 5 家 Code Agent 选择截然不同？

ACP 的价值是"广度"（接更多 IDE），代价是"被外部 spec 约束 control plane 设计"。**这个 trade-off 在头部厂商和社区厂商之间评估完全不同**——这正是本文 §一·"5 家立场"差异的根本原因，也是 §五 哲学摘要的解释起点。头部厂商（Anthropic/OpenAI）押注自家 MCP、把 ACP 丢给外部 adapter；Gemini 血统（Qwen/Qoder）+ OpenCode 则原生拥抱 ACP——与 [MCP 完整性](./mcp-completeness-deep-dive.md) 排名正好反转。

---

## 零、TL;DR

| 维度 | Claude | Codex | Qwen | OpenCode | Qoder |
|---|:---:|:---:|:---:|:---:|:---:|
| CLI 内**原生 ACP** | ❌ adapter | ❌ adapter | ✅ | ✅ | ✅ |
| ACP Agent | ❌ | ❌ | ✅ `acpAgent` **965→7167 LOC** | ✅ **1968 LOC** | ✅ gemini 继承（闭源）|
| ACP Client | ❌ | ❌ | ✅ VSCode companion | ❌ | ❌ |
| ACP 库版本 | adapter v0.48.0 | adapter v0.16.0 | CLI `^0.14.1`（desktop 包 0.21.0）| `0.21.0` | gemini 继承 |
| 实现方法数（含 unstable_*） | — | — | **11**（+`resumeSession`）| **13** | gemini 基线 |
| 传输 HTTP/WS | ❌ | ❌ | ✅ **独家** daemon 桥接 | ❌ stdio | ❌ stdio-only |
| Java ACP 库 | ❌ | ❌ | ✅ `com.alibaba:acp-sdk` | ❌ | ❌ |
| 替代选择 | 私有 NDJSON | MCP server / app-server | — | HTTP daemon（OpenAPI）| Qoder 云远程 |

**最关键的两个反直觉发现**：
1. **OpenCode 比 Qwen 多 2 个 session lifecycle 方法**（`closeSession` / `unstable_forkSession`）——2026-06-22 复核：Qwen 已补上 `unstable_resumeSession`（方法数 10→**11**），缺口从 3 收窄到 2；仍缺"显式关闭 + fork 分叉"的原生 IDE UX。CLI ACP 库仍 lock 在 `0.14.1`（新 `desktop` 包已用 0.21.0）。
2. **Qwen 独家做了 HTTP↔ACP daemon 桥接**（`httpAcpBridge.ts` 2802 LOC，PR#3889 引入）—— 5 家中唯一把 ACP 从 stdio-only 协议套壳成 HTTP 远端可用，连 Zed 官方都没做这个。

## 零·五、完整性排名 + MCP↔ACP 反转（2026-06-22 增补）

**原生 ACP 完整性排名**：**Qwen Code > OpenCode > Qoder CLI > Claude Code ≈ Codex**（后两家 CLI **无原生 ACP**，仅靠外部 adapter）。

### ⭐ 与 MCP 完整性**完全反转**

| 协议 | 完整性排名 | 谁领先 |
|---|---|---|
| **MCP**（agent↔工具）| Claude > Codex ≈ Qwen > OpenCode > Qoder | **Anthropic/OpenAI**（自家主推）|
| **ACP**（IDE↔agent）| **Qwen > OpenCode > Qoder** > Claude ≈ Codex | **Gemini 血统 + OpenCode**（拥抱 Zed 标准）|

Anthropic/OpenAI 在自家 MCP 上最全，却把 Zed 的 ACP **丢给外部 adapter**——`claude` / `codex` CLI 里都**没有** `--acp`，靠 Zed 维护的桥接器接入（详 [MCP 支持完整性对比](./mcp-completeness-deep-dive.md)）。

### native vs adapter（关键区分）

| Agent | CLI 内**原生 ACP** | 接入机制 |
|---|:--:|---|
| **Qwen Code** | ✅ `--experimental-acp` | 原生被 IDE 拉起 + **独家 HTTP↔ACP daemon 桥接** |
| **OpenCode** | ✅ `opencode acp` | 原生被 IDE 拉起（库最新 0.21.0）|
| **Qoder CLI** | ✅ `--acp`（gemini 继承）| 原生但**仅 stdio**（无 HTTP/WS；二进制 `ACP` 101×）|
| **Claude Code** | ❌ | 外部 adapter [`@agentclientprotocol/claude-agent-acp`](https://github.com/agentclientprotocol/claude-agent-acp) v0.48.0（wrap Claude Agent SDK）|
| **Codex** | ❌ | 外部 adapter [`zed-industries/codex-acp`](https://github.com/zed-industries/codex-acp) v0.16.0；其 `app-server` 是**另一套私有协议**（≠ ACP）|

> **adapter ≠ 原生**：Zed 能在编辑器里用上 Claude/Codex，但靠的是 Zed 自己维护的桥接进程把 Claude Agent SDK / Codex CLI 翻译成 ACP——agent 本体里没有 ACP server。Qwen/OpenCode/Qoder 则是 CLI 自带 `--acp`/`acp` 子命令。

## 一、ACP 是什么 + 谁支持

ACP（Agent Client Protocol）是 Zed Industries 推动的 **IDE↔Agent 标准协议**，2025 年发布，npm 包 `@agentclientprotocol/sdk`。基于 JSON-RPC over stdio NDJSON。设计目标：让 IDE 厂商不再为每个 agent 写专属集成，agent 厂商也不再为每个 IDE 写专属插件。

### 5 家立场

| 角色 | Claude Code | Codex | Qwen Code | OpenCode | Qoder CLI |
|---|:---:|:---:|:---:|:---:|:---:|
| **作为 ACP Agent**（被 IDE 拉起） | ❌（外部 adapter） | ❌（外部 adapter） | ✅ `acpAgent.ts` 965→**7167** LOC | ✅ `acp/agent.ts` 1968 LOC | ✅ `--acp`（gemini 继承，闭源）|
| **作为 ACP Client**（驱动其他 Agent） | ❌ | ❌ | ✅ `vscode-ide-companion` acpConnection 694 LOC | ❌ | ❌ |
| **Java ACP 库** | ❌ | ❌ | ✅ `com.alibaba:acp-sdk` v0.0.1-α | ❌ | ❌ |
| **Zed 原生 extension** | ❌（外部 adapter） | ❌（外部 adapter） | ✅ `packages/zed-extension/` | 🟡 文档教用户配 settings.json | ❌ |
| **daemon-side ACP bridge** 🆕 | ❌ | ❌ | ✅ `httpAcpBridge.ts` 2802 LOC | ❌（直接 HTTP daemon，不走 ACP） | ❌（仅 stdio）|
| **替代协议** | NDJSON 私有 + 外部 adapter | MCP server (`codex-mcp`) + 自家 `app-server-protocol` 17K LOC + 外部 adapter | — | HTTP daemon（与 ACP 并存）| Qoder 云远程控制 |

### Claude / Codex 的替代选择

**Claude Code**：用私有 NDJSON 控制协议——SDK 双向 20+ 控制原语（`set_model` / `seed_read_state` / `interrupt` / `canUseTool` 回调等），自家 IDE 扩展直接对接，**不进 ACP 生态**。哲学："深度集成 > 标准化兼容"。

**Codex**：用 MCP（Model Context Protocol）替代——`mcp-server` crate 让 Codex 自己**作为 MCP server** 暴露给其他 LLM agent 调用，5 家中**独家**。**MCP 是工具调用协议（窄）**，**ACP 是会话协议（全）**。Codex 选 MCP 反映它把自己定位为"被其他 agent 调用的工具"，而不是"被 IDE 嵌入的会话"。详 [Codex MCP Server Deep-Dive](./codex-mcp-server-deep-dive.md)（含 `codex mcp-server` 2 工具形态 / `codex app-server` 私有协议 / 4 个核心用例 / 与 ACP 哲学对比）。

## 二、ACP 库版本 + 方法覆盖（最关键差距）

```json
// Qwen Code (packages/cli/package.json + packages/vscode-ide-companion/package.json)
"@agentclientprotocol/sdk": "^0.14.1"

// OpenCode (packages/opencode/package.json)
"@agentclientprotocol/sdk": "0.21.0"
```

**版本落差 0.14 → 0.21** 直接体现在方法实现数：

| ACP 方法 | Qwen Code | OpenCode | 用途 |
|---|:---:|:---:|---|
| `initialize` | ✅ L248 | ✅ L508 | 协议握手 + capability 协商 |
| `authenticate` | ✅ L280 | ✅ L554 | OAuth / API key 验证 |
| `newSession` | ✅ L310 | ✅ L558 | 新建会话 |
| `loadSession` | ✅ L331 | ✅ L593 | 加载已有会话（按 ID） |
| `unstable_listSessions` | ✅ L364 | ✅ L633 | 列出所有可恢复会话 |
| `unstable_setSessionModel` | ✅ L415 | ✅ L1219 | 切换 session 模型 |
| `setSessionMode` | ✅ L402 | ✅ L1259 | 切换 plan/edit 等模式 |
| `setSessionConfigOption` | ✅ L428 | ✅ L1268 | 改配置项 |
| `prompt` | ✅ L471 | ✅ L1320 | 主对话流（含工具调用流） |
| `cancel` | ✅ L479 | ✅ L1503 | 软中断 |
| **`unstable_resumeSession`** | ✅ **L2802**（2026-06 新增）| ✅ **L732** | **从指定消息恢复对话** |
| **`closeSession`** | ❌ | ✅ **L766** | **显式关闭并清理资源** |
| **`unstable_forkSession`** | ❌ | ✅ **L678** | **从历史点 fork 出新分支** |
| 实现总数 | **11**（2026-06-22 复核）| **13** | — |

### 3 个缺口的 IDE 体验影响

- **`listSessions` + `resumeSession` + `closeSession`** 这三件套是 IDE 端"会话管理 UI"的基础原语。Zed 用户切到另一会话 → IDE 调 `listSessions` → 选一个 → `resumeSession` → 用完 `closeSession` 清理资源。**Qwen 当前 IDE 体验只能"每次开新 session"，关不掉、列不出、恢复不了**。
- **`unstable_forkSession`** 让 IDE 提供"基于历史分支探索"——用户可以在某个时间点"分叉两条路"对比效果。Qwen 主线已有 `/branch` 命令，但**未通过 ACP 暴露**。

> Qwen 的 `listSessions` 通过 `unstable_` prefix 实现说明 ACP 库 0.14.1 已开始有这条 spec，但版本 lock 在低位导致整体覆盖不齐——这是个**单纯升库即可大幅缩小差距**的 P0 项。

### Capability 协商

```rust
// Qwen Code: acpAgent.ts L254
{ protocolVersion: PROTOCOL_VERSION, ... }      // PROTOCOL_VERSION = 1

// OpenCode: acp/agent.ts L528
{ protocolVersion: 1, ... }
```

两家都报 `protocolVersion: 1`——所以 **ACP 协议大版本一致**，差距仅在方法集合的可选 / unstable 部分。

## 三、Qwen 端独家：HTTP↔ACP daemon 桥接

`packages/cli/src/serve/httpAcpBridge.ts` **2802 LOC**——PR#3889 daemon Stage 1（2026-05-13 MERGED `870bdf2a`）引入的全新形态：

```
旧形态（IDE 直接拉 acpAgent）：
  IDE  ──spawn──▶  qwen --acp 子进程  ──stdio NDJSON──▶  in-process core

新形态（PR#3889 daemon + HTTP→ACP 桥接）：
  IDE / Web /     ──HTTP/SSE──▶  qwen serve daemon
  Channel bot                       │
                                    └─spawn─▶ qwen --acp 子进程（1 per workspace）
                                              └─stdio NDJSON──▶ multiplexed session
```

### 5 家中独家形态的意义

1. **ACP 协议层零改动**：daemon 内部仍跑标准 ACP 子进程，所以**所有 ACP 库改进自动受益**——这是协议中性设计的胜利。
2. **远端可用**：原 ACP 是 stdio-only（IDE-bound，只能本机），HTTP 套壳后 Zed 跨网段、web bot、channel 都能连。
3. **N session × 1 ACP child × 1 workspace** 经济性：同 workspace 下 N 个 IDE session 共享 1 个 `qwen --acp` 子进程（内存 60-100MB），不是 N 进程（300-500MB）。详 [§06 Stage 1.5 audit](./qwen-code-daemon-design/06-roadmap.md)。
4. **5 Blockers before channel/web default migration**（[§04 §一·B](./qwen-code-daemon-design/04-deployment-and-client.md)）正在补齐 session lifecycle / 多 client 协调能力。

**Qwen 和 OpenCode 的 daemon 形态对比**（澄清易混点）：两家**都有完整 HTTP daemon**，但选择了不同协议套壳：

| | Qwen Code（PR#3889 MERGED 2026-05-13） | OpenCode（早已存在）|
|---|---|---|
| daemon binary | `qwen serve` | `opencode serve` |
| daemon 主协议 | **ACP-over-HTTP**（httpAcpBridge 桥接 `qwen --acp` 子进程） | **自家 OpenAPI**（13525 行 schema codegen） |
| ACP 体验在 daemon 中 | ✅ 远端 IDE 可走 HTTP 拿 ACP 语义 | ❌ ACP 仍是独立 stdio 路径（`opencode acp`），daemon 不暴露 ACP |
| IDE 形态可达性 | 远端 ACP-aware IDE / web bot / channel 都能连 | 远端必须用 OpenAPI client，IDE 只能本机 stdio ACP |
| 协议设计哲学 | "标准协议 + HTTP 套壳"——下游不感知 daemon | "私有 OpenAPI + ACP 平行"——IDE 走 IDE 路，自动化走 OpenAPI 路 |

**Qwen 独家的不是"有 HTTP daemon"，而是"把 ACP 语义透明扩展到 HTTP 远端"**——OpenCode 也能远端可用，但走的是 OpenAPI 路径而不是 ACP，ACP-aware 的 IDE 跨网段还是连不上。两家殊途同归到"daemon 远端可用"，但 Qwen 选了"协议中性"路线，OpenCode 选了"协议分层"路线。

## 四、IDE 端 UX 能力评分

| 能力维度 | Claude | Codex | Qwen | OpenCode |
|---|---|---|---|---|
| **IDE 厂商接入广度**（开协议 vs 私有）| 🔴 私有 NDJSON | 🔴 不接 IDE | 🟢 ACP + Zed ext + VSCode companion + Java | 🟢 ACP only |
| **ACP 协议方法完整性** | — | — | 🟡 **11/13**（2026-06-22）| 🟢 13/13 |
| **会话生命周期 IDE 体验**（list/resume/close） | — | — | 🟡 已补 resume，仍缺 close/fork（2）| 🟢 齐全 |
| **HTTP daemon 存在** | 🔴 | 🔴 | 🟢 `qwen serve` PR#3889 MERGED 2026-05-13 | 🟢 `opencode serve` OpenAPI 13525 LOC（早已存在）|
| **ACP semantics over HTTP**（远端 ACP-aware IDE 可达） | 🔴 | 🔴 | 🟢 **唯一**（httpAcpBridge 桥接 `qwen --acp` children） | 🔴（HTTP daemon 走 OpenAPI 协议，ACP 仍 stdio-only）|
| **多语言宿主接入** | TS+Py | TS+Py | **TS+Py+Java** | TS only |
| **VSCode / JetBrains 现成集成** | 🟢 私有扩展 | 🔴 | 🟢 ACP via companion + Zed | 🟢 ACP docs 教配置 |
| **Zed 原生体验** | 🔴 | 🔴 | 🟢 自家 `packages/zed-extension/` | 🟡 用户手配 `settings.json` |
| **JetBrains 现成集成** | 🟢 私有 | 🔴 | 🟢 ACP | 🟢 文档教配 `acp.json` |
| **Avante.nvim / CodeCompanion.nvim** | 🔴 | 🔴 | ⚠️ 理论 ACP 兼容 | 🟢 已 doc 验证 |

> **Qoder CLI（闭源）**：原生 ACP 但仅 stdio——可被 Zed/JetBrains 走标准 ACP stdio 拉起（无现成扩展），无 HTTP daemon、无 Java、无 ACP client、无 daemon 桥接；多语言宿主接入仅靠标准 ACP 协议本身。IDE-UX 完整度低于 Qwen/OpenCode，但仍是"原生 ACP"一档，高于 Claude/Codex 的"外部 adapter"。

### 按场景的最佳选择

| 场景 | 最佳选择 | 理由 |
|---|---|---|
| 把 agent 接到 Zed | **Qwen** | 唯一有官方 zed-extension |
| IDE 内做"会话切换/恢复"UX | **OpenCode** | 唯一支持 listSessions/resumeSession/closeSession |
| Java 后端跑 ACP 客户端 | **Qwen** | 唯一提供 `com.alibaba:acp-sdk` |
| 远端 / web 化 ACP 体验 | **Qwen** | 唯一把 ACP 透明扩到 HTTP（OpenCode 有 HTTP daemon 但只暴露 OpenAPI，ACP 走平行 stdio 路径）|
| 避开协议绑定走自家深度集成 | **Claude** | NDJSON 20+ 控制原语，含 `seed_read_state` 等独家能力 |
| 不要 IDE，要被 LLM agent 调用 | **Codex** | 唯一同时是 MCP server |

## 五、5 家选型哲学摘要

| 家 | 一句话 | 标志证据 |
|---|---|---|
| **Claude Code** | "深度 + 私有协议——20+ NDJSON 控制原语让宿主像调试器一样精细操控引擎" | `seed_read_state` / `canUseTool` 回调 / `interrupt` / `set_model` / Anthropic SDK 双向控制 |
| **Codex** | "把自己定位为被调用的工具" | `codex-mcp` crate + 自家 `app-server-protocol` 17K LOC + 不接 IDE |
| **Qwen Code** | "广度优先——4 维全做 + daemon HTTP→ACP 独家" | ACP agent + ACP client + Zed ext + Java ACP + httpAcpBridge 2802 LOC |
| **OpenCode** | "深度优先——ACP 库版本最新、方法覆盖最全（13/13）" | `@agentclientprotocol/sdk@0.21.0` + 实现 13 个方法 + 教 Zed/JetBrains/Avante/CodeCompanion 配置 |
| **Qoder CLI** | "继承即用——gemini 血统自带 ACP，但只做 stdio 最小集" | `--acp` flag + `acpMode` + `acpAuthenticatedType`（闭源二进制 `ACP` 101×）；无 HTTP/WS、无 Java、无 daemon 桥接、无 ACP client |
| **Claude / Codex** | "不进 ACP 本体——交给外部 adapter" | `claude`/`codex` CLI 无 `--acp`；Zed 靠 `claude-agent-acp` v0.48.0 / `codex-acp` v0.16.0 桥接 |

## 六、Qwen Code 借鉴清单

按优先级排序：

| 优先级 | 借鉴项 | 来源 | 工作量 | 关键收益 |
|:------:|---|---|---|---|
| **P0** | **升 `@agentclientprotocol/sdk` 0.14.1 → 0.21.0** | OpenCode 同款 | ~0.5d（升级 + 类型同步） | 解锁 3 个 session lifecycle 方法的可能性 |
| **P0** | **实现 `resumeSession` / `closeSession` / `unstable_forkSession`** | OpenCode L678/L732/L766 | ~2-3d（每方法 1d） | IDE 端会话管理 UX 完整 |
| **P1** | 把 `forkSession` 与已有 `/branch` 命令打通 | 内部能力 | ~1d | ACP 暴露 fork 语义 |
| **P1** | `claude-code` 的 `seed_read_state` 等价物——把 IDE 已打开文件灌入 `FileReadCache` | Claude NDJSON | ~1d | 减少重复 read，深 IDE 绑定 |
| **P2** | 给 OpenCode 推送 `httpAcpBridge` 经验 / spec 草案 | Qwen 独家 → 开源 | ~3-5d 写 RFC | 推动 ACP 加 transport-agnostic 扩展 |
| **P2** | Java SDK 推 ACP RFC 给 Zed | Qwen 独家 | ~2-3d | 让 ACP 不只活在 npm 生态 |

## 七、相关文档

- [SDK / ACP / Daemon 架构 Deep-Dive](./sdk-acp-daemon-architecture-deep-dive.md) —— **全景**对比（本文是其 §四 ACP 部分的焦点化 + 时点刷新）
- [Agent SDK Python Deep-Dive](./agent-sdk-python-deep-dive.md) —— Python SDK 跨语言桥接
- [SDK 双向控制 Deep-Dive](./sdk-bidirectional-control-deep-dive.md) —— Claude NDJSON 控制语义（替代 ACP 的路线）
- [Remote Control Bridge Deep-Dive](./remote-control-bridge-deep-dive.md) —— Qwen Channels 远程驱动
- [Qwen Code Daemon 架构设计](./qwen-code-daemon-design/04-deployment-and-client.md) —— `httpAcpBridge` daemon Stage 1 + Wave 2 channel/web 集成
- [Qwen Code 改进建议总览](./qwen-code-improvement-report.md) —— 含 ACP hooks（PR#3248）等改进项

## 八、相关 PR / Issue

| 编号 | 描述 | 状态 |
|---|---|---|
| [PR#3889](https://github.com/QwenLM/qwen-code/pull/3889) | qwen serve daemon Stage 1（含 httpAcpBridge 2802 LOC） | ✅ MERGED 2026-05-13 |
| [PR#3248](https://github.com/QwenLM/qwen-code/pull/3248) | ACP 完整 hooks 支持 | ✅ MERGED |
| [PR#3463](https://github.com/QwenLM/qwen-code/pull/3463) | ACP 并发处理 | ✅ MERGED |
| [Issue #4175](https://github.com/QwenLM/qwen-code/issues/4175) | 25-PR Wave breakdown（含 ACP/channel/web 集成 5 blockers） | OPEN |

---

> **数据来源**：四家 2026-05-17 源码核实。Qwen Code `packages/cli/src/acp-integration/acpAgent.ts` 965 LOC + `packages/cli/src/serve/httpAcpBridge.ts` 2802 LOC + `packages/vscode-ide-companion/src/services/acpConnection.ts` 694 LOC；OpenCode `packages/opencode/src/acp/agent.ts` 1968 LOC + `acp/session.ts` 122 LOC + `acp/runtime.ts` 22 LOC；ACP 库版本基于各项目 `package.json`。Claude / Codex 无 ACP 代码（grep `agent-client-protocol` / `acp` 在各自源码均为空）。
>
> **2026-06-22 复核增补**：① 加入 **Qoder CLI**（闭源，二进制 EVIDENCE：原生 `--acp` **stdio-only**，gemini 继承，`ACP` 101×；无 HTTP/WS daemon）；② Qwen `acpAgent.ts` 已增长至 **7167 LOC** 并新增 `unstable_resumeSession`（方法数 10→**11**，仍缺 `closeSession`/`forkSession`），CLI ACP 库仍 `^0.14.1`（新 `desktop` 包用 `^0.21.0`）；③ Claude/Codex 确认 CLI **无原生 ACP**——接入靠外部 adapter（[`@agentclientprotocol/claude-agent-acp`](https://github.com/agentclientprotocol/claude-agent-acp) v0.48.0 / [`zed-industries/codex-acp`](https://github.com/zed-industries/codex-acp) v0.16.0），Codex `app-server` 是另一套**私有协议**（≠ ACP）；④ 完整性排名见 [§零·五](#零五完整性排名--mcpacp-反转2026-06-22-增补)，与 [MCP 完整性](./mcp-completeness-deep-dive.md) 呈反转。
