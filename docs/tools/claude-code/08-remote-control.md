# 8. Claude Code Remote Control（远程控制）

> Remote Control 允许从手机、平板或任意浏览器远程操控本地运行的 Claude Code 终端会话。会话**始终在本地执行**，远程端仅作为交互窗口。
>
> **数据来源**：CLI 子命令/参数（`claude remote-control`、`--remote-control`/`--rc`、`--spawn`、`--capacity`）和故障排查指南来自 [Anthropic 官方文档](https://docs.anthropic.com/en/docs/claude-code/remote-control)（2026-03）；`/remote-control` 斜杠命令类型来自 v2.1.81 二进制反编译；环境变量名来自 [EVIDENCE.md](./EVIDENCE.md) 反编译提取。

## 概述

Remote Control 是 Claude Code 的跨设备会话桥接功能，在 18 款主流 AI 编程 Agent 中**为 Claude Code 独有**（[功能矩阵](../../comparison/features.md)）。它解决了开发者的一个核心痛点：启动了一个长时间的终端代理任务后，需要离开工位继续监控或干预。

核心特性：

- **本地执行，远程操控**：会话运行在本地机器上，完整的文件系统、MCP 服务器、工具链、项目配置均可使用
- **实时双向同步**：所有连接设备的对话保持同步，可在任意设备上发送消息
- **自动重连**：笔记本电脑睡眠或网络短暂中断后自动恢复连接
- **零入站端口**：所有通信通过出站 HTTPS 完成，无需开放防火墙端口

## 前置条件

| 要求 | 详情 |
|------|------|
| **版本** | Claude Code v2.1.51+（`claude --version` 检查） |
| **订阅** | Pro / Max / Team / Enterprise 计划。**API Key 不支持** |
| **认证方式** | 必须通过 claude.ai OAuth 登录（`/login`），不支持 API Key 或 `claude setup-token` |
| **工作区信任** | 需在项目目录中至少运行一次 `claude` 以接受工作区信任对话框 |
| **Team/Enterprise** | 管理员需在 `claude.ai/admin-settings/claude-code` 中启用 Remote Control 开关 |

## 三种启动方式

### 方式一：Server 模式（专用服务）

```bash
claude remote-control
claude remote-control --name "My Project"
```

运行一个专用的 Remote Control 服务器，等待远程连接。终端显示会话 URL，按 **空格键** 可显示 QR 码。

**可用参数：**

| 参数 | 说明 |
|------|------|
| `--name <名称>` | 自定义会话标题，在会话列表中可见 |
| `--spawn <模式>` | `same-dir`（默认）：所有会话共享 CWD；`worktree`：每个会话获得独立 Git worktree |
| `--capacity <N>` | 最大并发会话数（默认：32） |
| `--verbose` | 详细连接/会话日志 |
| `--sandbox` / `--no-sandbox` | 启用/禁用文件系统和网络沙箱（默认关闭） |

### 方式二：交互式会话 + Remote Control

```bash
claude --remote-control              # 或 --rc
claude --remote-control "My Project" # 带名称
```

在终端中启动一个完整的交互式会话，同时可通过远程设备操控。可以本地输入，远程客户端也可以同时连接。

### 方式三：从已有会话启用

```
/remote-control          # 或 /rc
/remote-control My Project
```

在当前对话中启用 Remote Control。此方式不支持 `--verbose`、`--sandbox`、`--no-sandbox` 参数。

> **命令类型**：`/remote-control` 斜杠命令类型为 `local-jsx`（[命令详解](./02-commands.md)），渲染远程控制配置 UI 并启动到 claude.ai/code 的连接。

## 从其他设备连接

三种连接方式：

| 方式 | 操作 |
|------|------|
| **会话 URL** | 在任意浏览器中打开，跳转到 `claude.ai/code` |
| **QR 码** | 用 Claude App 扫描（Server 模式下按空格键切换显示） |
| **会话列表** | 在 `claude.ai/code` 或 Claude App 中按名称查找；在线的 Remote Control 会话显示**带绿点的电脑图标** |

**会话标题优先级**（依次递减）：
1. `--name` / `--remote-control` / `/remote-control` 参数指定的名称
2. 通过 `/rename` 设置的标题
3. 对话历史中最后一条有意义消息的内容
4. 用户发送的第一条 prompt

## 全局默认启用

在 Claude Code 中运行 `/config` → 将 **"Enable Remote Control for all sessions"** 设为 `true`。此后每个交互式进程自动注册一个远程会话。如需一个进程中多个并发会话，使用 **Server 模式** 加 `--spawn`。

## 技术架构

> 以下综合 [Anthropic 官方文档](https://docs.anthropic.com/en/docs/claude-code/remote-control)、v2.1.81 二进制反编译（[EVIDENCE.md](./EVIDENCE.md)）、GitHub Issues 社区反馈和 Anthropic 工程博客分析。

### 三方中继架构

Remote Control 采用 **三方中继**（Three-Party Relay）架构，Anthropic API 充当消息代理：

```
┌──────────────┐     ① 出站 HTTPS (polling)    ┌───────────────────────┐
│   本地终端    │ ────────────────────────────→   │    Anthropic API      │
│  (Claude Code)│ ←──────────────────────────── │    (消息中继/代理)     │
│              │     ② 流式响应 (streaming)      │                       │
└──────────────┘                                │  claude.ai/code       │
                                                │  会话注册 + 消息路由    │
                                                └───────────┬───────────┘
                                                            │
                                                 ③ WebSocket/HTTPS │
                                                            │
                                                ┌───────────▼───────────┐
                                                │  浏览器 / 手机 App     │
                                                │  (claude.ai/code)     │
                                                └───────────────────────┘
```

**数据流**（官方确认部分）：
1. **本地 → Anthropic API**：本地进程启动时用 full-scope OAuth token 注册会话，随后以 polling 方式持续获取待处理消息 ✅ 官方确认
2. **Anthropic API → 本地**：服务器有消息时通过 streaming connection 下发 ✅ 官方确认
3. **Anthropic API ↔ 浏览器/手机**：远程客户端连接到 Anthropic 基础设施（具体传输协议未公开确认） ⚠️ 社区观察到 stale WebSocket 连接行为

| 方面 | 细节 | 确认度 |
|------|------|--------|
| **本地→服务器** | 出站 HTTPS polling。本地不开放入站端口 | ✅ 官方确认 |
| **远程客户端→服务器** | 推测为 WebSocket 或 HTTPS 长连接（`WEBSOCKET_AUTH_*` 变量名暗示 WebSocket 使用） | ⚠️ 推断 |
| **消息路由** | Anthropic 服务器在远程客户端和本地会话之间双向中继 | ✅ 官方确认 |
| **传输安全** | 全程 TLS 加密，与普通 Claude Code 会话相同 | ✅ 官方确认 |
| **凭证体系** | 多个短期凭证，每个限定单一用途，独立过期 | ✅ 官方确认 |

#### 三层架构拆分：控制面 / 数据面 / 本地状态面

从实现者视角，Remote Control 可拆分为三个职责清晰的子系统：

**控制面（Control Plane）**——会话注册、资格检查、凭证管理、策略执行：

| 组件 | 职责 | 证据来源 |
|------|------|----------|
| 会话注册 | 用 full-scope OAuth token 向中继服务器注册会话，获取 `SESSION_ACCESS_TOKEN` | 官方文档 + 反编译 |
| 资格检查 | `admin_requests/eligibility` 端点判定用户是否可使用 RC（受订阅类型、管理员策略、组织策略影响） | v2.1.87 反编译 |
| 凭证刷新 | JWT expiry 驱动的定时刷新（过期前 5 分钟触发，最多失败 3 次） | v2.1.87 反编译 |
| 策略执行 | `policy_limits` 端点查询组织级 RC 开关；Team/Enterprise 管理员门控 | EVIDENCE.md |
| 配置下发 | `tengu_bridge_poll_interval_config` 动态下发 polling 参数（TTL 5 分钟） | v2.1.87 反编译 |
| PID 文件管理 | `~/.claude/sessions/{pid}.json` 跟踪并发会话 | v2.1.87 反编译 |

**数据面（Data Plane）**——消息传输、双向同步、流式响应：

| 组件 | 职责 | 证据来源 |
|------|------|----------|
| 出站轮询 | 2s（未满容量）或 10min（满容量）HTTPS poll 获取待处理消息 | 官方文档 + 反编译 |
| 流式响应 | 服务端通过 streaming connection 下发 agent 输出到远程客户端 | 官方文档 |
| 消息协议 | JSON-lines 格式，8+ 消息类型（`user`/`assistant`/`control_request`/`keep_alive` 等） | v2.1.87 反编译 |
| 本地 IPC | Unix domain socket (`/tmp/cc-socks/*.sock`) 用于进程内消息传递 | GitHub Issues |
| 对话持久化 | `~/.claude/projects/<hash>/*.jsonl` 存储完整对话流 | EVIDENCE.md |
| WebSocket ping/pong | `session_keepalive_interval_v2_ms: 120000`（2 分钟）维持连接活性 | v2.1.87 反编译 |

**本地状态面（Local State Plane）**——Redux 状态机、环境变量、运行时状态：

| 组件 | 职责 | 证据来源 |
|------|------|----------|
| Redux 状态机 | 13 个 `replBridge*` 字段管理桥接生命周期（enabled/connected/active/reconnecting 等） | v2.1.87 反编译 |
| 客户端类型检测 | `CLAUDE_CODE_SESSION_ACCESS_TOKEN` / `WEBSOCKET_AUTH_FILE_DESCRIPTOR` / `ENTRYPOINT` 判定客户端类型 | v2.1.87 反编译 |
| 环境变量配置 | 14+ 环境变量控制 RC 行为（认证模式、网络代理、沙箱、远程环境等） | 官方文档 + 反编译 |
| initReplBridge | 核心桥接层，通过 7 个回调函数连接远程端和本地会话 | v2.1.87 反编译 |

> **设计启示**：三层分离使得**控制面变更不影响消息传输**（如修改 polling 策略无需改消息格式），**本地状态面独立于网络**（进程崩溃后可从 PID 文件和对话历史重建部分状态）。实现者可参考此拆分设计自己的子系统边界。

### 会话生命周期

```
┌─────────┐     ┌───────────┐     ┌──────────┐     ┌───────────┐     ┌──────────┐
│ 注册     │ ──→ │ 等待连接   │ ──→ │ 活跃     │ ──→ │ 空闲/断连  │ ──→ │ 过期/退出  │
│Register  │     │ Waiting   │     │ Active   │     │ Idle      │     │ Expired  │
└─────────┘     └───────────┘     └──────────┘     └───────────┘     └──────────┘
  - OAuth认证      - 显示URL/QR      - 双向消息同步     - 自动重连尝试     - 进程退出
  - API注册        - 轮询等待客户端    - 工具调用可远程审批  - ~10min网络断连   - 清理会话文件
                  - Server模式可                                    后超时
                    接受多个客户端
```

**各阶段详情**：

| 阶段 | 触发 | 行为 |
|------|------|------|
| **注册** | 启动 `claude remote-control` 或 `/rc` | 使用 full-scope OAuth token 向 Anthropic API 注册会话，获取 `SESSION_ACCESS_TOKEN` |
| **等待连接** | 注册成功后 | 终端显示会话 URL 和 QR 码。本地进程持续 polling 等待远程客户端 |
| **活跃** | 远程客户端连接 | 双向消息同步：远程发送的指令路由到本地执行，本地输出实时推送到远程 |
| **空闲/断连** | 网络中断、笔记本睡眠 | 自动尝试重连。若网络断连超过 ~10 分钟，会话超时 |
| **过期/退出** | 超时或进程终止 | 清理会话文件。Server 端约 20+ 分钟无活动后关闭连接（观察到 `CLOSE_WAIT` TCP 状态） |

### 会话文件与本地存储

| 路径 | 内容 | 所属面 | 生命周期 | 可恢复性 | 来源 |
|------|------|--------|----------|----------|------|
| `~/.claude/sessions/{pid}.json` | 会话元数据：`pid`、`sessionId`、`cwd`、`startedAt`、`kind`、`entrypoint`、`name`、`status`、`updatedAt`、`bridgeSessionId`、`messagingSocketPath` | 控制面 + 本地状态面 | 每个 interactive process 一个文件；进程退出后残留但无意义 | ⚠️ 推断：进程退出后文件残留，但 `reclaim_older_than_ms: 5000` 意味着服务端 5 秒后即视为废弃。**进程重启不会自动恢复** | GitHub Issues + v2.1.87 反编译 |
| `/tmp/cc-socks/*.sock` | Unix domain socket，用于本地进程间消息传递（如 UI bridge、多客户端复用） | 数据面（本地 IPC） | 随进程创建/销毁；进程退出即失效 | ❌ 不可恢复：Unix socket 文件随进程退出失效，重新连接需建立新 socket | GitHub Issues |
| `~/.claude/projects/<project-hash>/` | 会话对话历史（`.jsonl` 格式），包含完整对话流；`cleanupPeriodDays`（默认 30 天）后自动清理 | 数据面（持久化） | 独立于 Remote Control 生命周期；与普通会话共享存储 | ✅ 可恢复：对话历史在磁盘上持久化，可用于 `/continue` 或 `/teleport` 恢复上下文 | [EVIDENCE.md](./EVIDENCE.md) |

> **实现者注意事项**：
> - PID 文件命名（`{pid}.json`）意味着**每个 OS 进程一个远程会话**，而非每个 bridge session 一个 state file。Server 模式 `--spawn` 创建的子进程各自有独立的 PID 文件
> - `messagingSocketPath` 字段存储在 PID 文件中，表明 Unix socket 路径是**服务端/客户端协商结果**，而非硬编码
> - `bridgeSessionId` 与 `sessionId` 是不同概念：`sessionId` 是本地会话 ID，`bridgeSessionId` 是中继服务器分配的桥接 ID

### `--spawn` 多会话架构

Server 模式支持通过 `--spawn` 参数管理多个并发远程会话：

| 模式 | 行为 | 适用场景 |
|------|------|----------|
| `same-dir`（默认） | 所有会话共享当前工作目录 | 多人远程操控同一项目不同任务 |
| `worktree` | 每个按需会话获得独立 Git worktree | 需要文件隔离的并行开发任务 |

**运行时切换**：在 Server 模式中按 `w` 键可动态切换 spawn 模式。

**容量控制**：`--capacity <N>` 限制最大并发会话数（默认 32），防止资源耗尽。

> **与 CCR（Claude Code Remote）的区别**：`--spawn` 创建的是**本地多会话**（通过 worktree 隔离），而 `/schedule` 使用的 `RemoteTrigger` 工具创建的是**云端隔离会话**（CCR），在 Anthropic 基础设施上独立运行（[命令详解](./02-commands.md)）。

### 安全模型纵深

Remote Control 的安全架构采用多层防护：

| 层级 | 机制 | 说明 |
|------|------|------|
| **1. 认证门槛** | claude.ai OAuth full-scope token | API Key、`setup-token`、Bedrock/Vertex/Foundry 均被拒绝 |
| **2. 管理员门控** | `claude.ai/admin-settings/claude-code` 开关 | Team/Enterprise 默认关闭；合规配置可阻止启用 |
| **3. 凭证隔离** | 多短期凭证、单用途作用域、独立过期 | 防止凭证泄露后横向移动 |
| **4. 网络隔离** | 仅出站 HTTPS，零入站端口 | 显著降低网络暴露面（本地 IPC、会话文件、OAuth flow 仍属攻击面） |
| **5. 传输加密** | 全程 TLS | 与普通 Claude Code 会话相同 |
| **6. 可选沙箱** | `--sandbox` 启用文件系统+网络隔离 | 默认关闭，Server 模式可启用 |
| **7. 安全分类器** | auto mode 双层防御（服务端 probe + 客户端分类器） | [工程博客](https://anthropic.com/engineering/claude-code-auto-mode)，Sonnet 4.6 驱动 |

**遥测耦合现象**：设置 `DISABLE_TELEMETRY=1` 后 Remote Control 注册失败（[GitHub #41189](https://github.com/anthropics/claude-code/issues/41189)），表现为 eligibility check 不通过。当前证据不足以确认根因是"资格检查走遥测通道"，标记为**疑似实现耦合**。

### 相关 API 端点（反编译提取）

| 端点 | 用途 | 来源 |
|------|------|------|
| `claude.ai/api/claude_code/settings` | 远程设置获取 | [EVIDENCE.md](./EVIDENCE.md) |
| `claude.ai/api/claude_code/policy_limits` | 策略限制查询（RC 管理员门控检查） | [EVIDENCE.md](./EVIDENCE.md) |
| `claude.ai/api/oauth/authorize` | OAuth 认证（RC 注册需 full-scope token） | [EVIDENCE.md](./EVIDENCE.md) |
| `api.anthropic.com/api/claude_code/metrics` | 遥测上报（资格检查依赖此通道） | [EVIDENCE.md](./EVIDENCE.md) |
| `claude.ai/api/ws/speech_to_text/voice_stream` | 语音转文字（共用 WebSocket 基础设施） | [EVIDENCE.md](./EVIDENCE.md) |
| `api.anthropic.com/admin_requests/eligibility` | 资格检查端点（RC 启用前的资格判定） | v2.1.87 反编译 |
| `api.anthropic.com/api/claude_code_grove` | Grove 端点（用途待确认） | v2.1.87 反编译 |
| `api.anthropic.com/api/claude_code_penguin_mode` | 快速模式端点 | v2.1.87 反编译 |
| `api.anthropic.com/api/claude_code_shared_session_transcripts` | 共享会话转录 | v2.1.87 反编译 |
| `api.anthropic.com/api/claude_code/team_memory` | 团队记忆 | v2.1.87 反编译 |

> **注意**：Remote Control 专用的会话注册和消息中继端点 URL 未在 v2.1.87 二进制中明文暴露（可能通过拼接构造或从服务端动态获取）。上述端点为反编译中确认的基础设施端点。

### 相关环境变量

前 7 项来自 [Anthropic 官方文档](https://docs.anthropic.com/en/docs/claude-code/remote-control)；其余为 v2.1.87 反编译提取。

| 变量 | 影响 | 来源 |
|------|------|------|
| `ANTHROPIC_API_KEY` | 阻止 Remote Control；需清除并使用 OAuth 登录 | 官方文档 |
| `CLAUDE_CODE_OAUTH_TOKEN` | 提供有限范围 token；与 Remote Control 不兼容 | 官方文档 |
| `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC` | 可能破坏资格检查 | 官方文档 |
| `DISABLE_TELEMETRY` | 阻止 Remote Control 注册（疑似实现耦合，[GitHub #41189](https://github.com/anthropics/claude-code/issues/41189)） | 官方文档 + 社区观察 |
| `CLAUDE_CODE_USE_BEDROCK` | 不兼容——Remote Control 要求 claude.ai 认证 | 官方文档 |
| `CLAUDE_CODE_USE_VERTEX` | 不兼容——Remote Control 要求 claude.ai 认证 | 官方文档 |
| `CLAUDE_CODE_USE_FOUNDRY` | 不兼容——Remote Control 要求 claude.ai 认证 | 官方文档 |
| `CLAUDE_CODE_SESSION_ACCESS_TOKEN` | 会话访问凭证；存在时客户端类型被判定为 "remote" | v2.1.87 反编译 |
| `CLAUDE_CODE_WEBSOCKET_AUTH_FILE_DESCRIPTOR` | WebSocket 认证（文件描述符传递）；存在时客户端类型被判定为 "remote" | v2.1.87 反编译 |
| `CLAUDE_CODE_ENTRYPOINT` | 值为 `"remote"` 时标记为远程入口，改变客户端类型行为 | v2.1.87 反编译 |
| `CLAUDE_CODE_REMOTE` | 存在时影响 auto-memory 行为；传递给 teammate spawn 环境 | v2.1.87 反编译 |
| `CLAUDE_CODE_ENVIRONMENT_KIND` | 值为 `"bridge"` 时标识为桥接子进程 | v2.1.87 反编译 |
| `CLAUDE_CODE_POST_FOR_SESSION_INGRESS_V2` | 值为 `"1"` 时启用 V2 会话入口协议 | v2.1.87 反编译 |
| `SSE_PORT` | SSE 本地端口（反编译提取，可能用于 Remote Control 或 MCP SSE 传输） | EVIDENCE.md |

### 实现者 Checklist：设计决策表

> 以下清单提炼自反编译分析和官方文档。每个条目对应实现一个 Remote Control 类功能时**必须做出的设计决策**，Claude Code 的选择作为参考标注。

| # | 设计决策 | Claude Code 的选择 | 实现考量 |
|---|----------|-------------------|----------|
| **1** | **本地与云端谁持有会话状态（source of truth）？** | **云端是控制面 source of truth**（资格检查、策略执行、配置下发均在服务端）；本地持有数据面状态（对话历史 `.jsonl`、PID 文件） | 云端控制面允许运行时调整（如 poll 间隔）无需客户端升级；但需要网络可用才能启动 |
| **2** | **资格检查是否复用遥测通道？** | **疑似耦合**：`DISABLE_TELEMETRY=1` 阻止 RC 注册（[#41189](https://github.com/anthropics/claude-code/issues/41189)），根因未确认 | 解耦更安全——遥测开关不应影响功能可用性；但共享通道可简化实现 |
| **3** | **多客户端鉴权是共享 token 还是分 scope token？** | **分 scope token**：`SESSION_ACCESS_TOKEN`（会话访问）、`WEBSOCKET_AUTH_FILE_DESCRIPTOR`（WebSocket 认证），各独立过期 | 多 token 增加管理复杂度，但降低凭证泄露影响面 |
| **4** | **Poll 间隔是硬编码还是服务端可调？** | **服务端下发，Zod schema 校验**，TTL 5 分钟缓存 | 服务端可调允许根据负载动态调整（满容量时从 2s 切到 10min），但需考虑配置服务可用性 |
| **5** | **网络/代理环境是否一等公民支持？** | **部分支持**：`HOST_HTTP_PROXY_PORT`、`HOST_SOCKS_PROXY_PORT` 存在于二进制中，但 RC 在代理环境下的连接问题仍被报告（[#41324](https://github.com/anthropics/claude-code/issues/41324)） | 企业代理是常见障碍；出站 HTTPS 需正确处理 CONNECT 方法、证书链、认证代理 |
| **6** | **进程崩溃后状态可恢复吗？** | **部分可恢复**：对话历史 `.jsonl` 可通过 `/continue` 恢复；但桥接状态（`replBridge*`）纯内存，进程退出即丢失；PID 文件残留但服务端 5s 后视为废弃 | 需区分「对话上下文恢复」（容易）和「桥接会话恢复」（需要云端配合） |
| **7** | **并发会话如何隔离？** | `--spawn same-dir`（共享 CWD）或 `--spawn worktree`（独立 Git worktree），`--capacity` 上限 32 | 文件隔离是基本需求；worktree 方案允许并行修改不同分支但增加磁盘占用 |
| **8** | **诊断日志写到哪里？** | `--debug-file <path>` 参数指定调试输出文件；`--verbose` 控制连接/会话日志详细度 | 生产环境中需要可开关的详细日志，用于排查连接循环、凭证刷新失败等问题 |

## Remote Control vs Claude Code on the Web

两者经常混淆，但本质不同：

| | Remote Control | Claude Code on the Web |
|---|---|---|
| **执行位置** | 你的本地机器 | Anthropic 云端基础设施 |
| **本地工具/MCP** | ✅ 可用（文件系统、MCP 服务器等） | ❌ 不可用 |
| **安装要求** | 需要本地运行 Claude Code 进程 | 无需本地安装 |
| **适合场景** | 在其他设备上继续进行中的工作 | 无本地环境时启动新任务，并行任务 |
| **启动方式** | `claude remote-control` / `--rc` / `/rc` | `claude --remote "任务描述"` |
| **反向操作** | — | `claude --teleport`（拉回 Web 会话到终端） |

### 跨设备工作流全景

Claude Code 提供了多种跨设备工作方式，各有侧重：

| 方式 | 触发方式 | 运行位置 | 适用场景 |
|------|----------|----------|----------|
| **Dispatch** | 从 Claude Mobile App 发送消息 | 本地机器（Desktop） | 离开工位时委派任务 |
| **Remote Control** | 从浏览器/Mobile 操控运行中的会话 | 本地机器（CLI/VS Code） | 远程操控进行中的工作 |
| **Channels** | 从 Telegram/Discord 推送事件 | 本地机器（CLI） | 响应外部事件 |
| **Slack** | 团队频道中 `@Claude` 提及 | Anthropic 云端 | 从团队聊天处理 PR/审查 |
| **Scheduled Tasks** | 设置定时计划 | CLI / Desktop / 云端 | 周期性自动化 |
| **`--remote`** | CLI 推送任务到 Web | Anthropic 云端 | 启动 Web 会话 |
| **`/teleport`** | 在 Web 端启动长任务后拉入终端 | 本地机器 | 将云端会话拉到本地继续（CLI 等价：`claude --teleport`） |

## 限制

| 限制 | 说明 |
|------|------|
| **单远程会话/进程** | 交互模式（非 Server 模式）下每个进程仅一个远程会话。需多会话时用 `--spawn` |
| **终端必须保持打开** | 关闭终端或终止进程会结束会话 |
| **网络超时** | 若机器在线但网络不可达持续约 10 分钟，会话超时并退出进程 |
| **不支持 API Key** | 必须使用 claude.ai OAuth 认证 |
| **不支持第三方提供商** | Bedrock / Vertex / Foundry 用户无法使用 |

## 已知问题（社区反馈）

以下问题来自 GitHub Issues，为社区观察到的现象，**根因未经官方确认**：

| 问题 | 观察到的现象 / 推测原因 | 影响 | 来源 |
|------|------|------|------|
| **Pidfile 竞态** | `concurrentSessions.ts` 中 `updatePidFile()` 非原子 read-modify-write（缺少 tmp+rename） | 并发会话时 JSON 文件损坏，Bun `fallocate` 可产生 null 字节截断 | [#41195](https://github.com/anthropics/claude-code/issues/41195) |
| **遥测耦合** | 设置 `DISABLE_TELEMETRY=1` 后 RC 注册失败（疑似 eligibility check 与遥测共享代码路径） | RC 失败但报错信息误导为"未启用" | [#41189](https://github.com/anthropics/claude-code/issues/41189) |
| **僵尸进程** | 服务端关闭连接后客户端进程不退出（观察到 `CLOSE_WAIT` TCP 状态，推测可能缺少 TCP read timeout 或 `CLOSE_WAIT` 检测） | 服务端关闭后客户端仍占用 1+ GB 内存，无自动退出 | [#41024](https://github.com/anthropics/claude-code/issues/41024) |
| **连接循环** | Connecting/Disconnected 循环，可能与凭证刷新或网络代理有关 | 远程客户端无法稳定连接 | [#41324](https://github.com/anthropics/claude-code/issues/41324) |
| **移动端 stale 连接** | Mobile App 复用过期的 WebSocket/session token | 空闲会话在移动端不可恢复，但 CLI 端正常 | [#41128](https://github.com/anthropics/claude-code/issues/41128) |
| **VS Code 配置缺口** | 扩展未读取 `remoteControlAtStartup` 设置 | `/config` 全局启用在 VS Code 扩展中不生效 | [#41036](https://github.com/anthropics/claude-code/issues/41036) |
| **Windows MCP 兼容** | Cloud MCP + RC 在 Windows 上加载失败 | Windows 用户无法同时使用 MCP 和 Remote Control | [#41044](https://github.com/anthropics/claude-code/issues/41044) |
| **活跃 turn 丢消息** | Agent 正在执行 turn 时，stdin 消息可能丢失 | 远程发送的指令在 agent 忙碌时可能不被处理 | [#41230](https://github.com/anthropics/claude-code/issues/41230) |

## 故障排查

| 错误信息 | 原因与解决 |
|----------|-----------|
| *"Requires a claude.ai subscription"* | 未通过 claude.ai 认证。运行 `claude auth login`，选择 claude.ai。如设置了 `ANTHROPIC_API_KEY` 需先清除 |
| *"Requires a full-scope login token"* | 使用了 `claude setup-token` 或 `CLAUDE_CODE_OAUTH_TOKEN` 产生的有限 token。运行 `claude auth login` 获取完整 session token |
| *"Unable to determine your organization"* | 缓存的账户信息过期。运行 `claude auth login` 刷新 |
| *"Not yet enabled for your account"* | 检查是否设置了 `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC`、`DISABLE_TELEMETRY`、`CLAUDE_CODE_USE_BEDROCK` 等——清除它们。否则 `/logout` 后重新 `/login` |
| *"Disabled by your organization's policy"* | 三种原因：(1) 使用 API Key → 切换为 claude.ai OAuth；(2) Team/Enterprise 管理员未启用 `claude.ai/admin-settings/claude-code` 的开关；(3) 管理员开关灰色 → 数据保留/合规配置阻止，联系 Anthropic 支持 |
| *"Remote credentials fetch failed"* | 使用 `--verbose` 查看详情。常见：未登录、防火墙/代理阻止出站 HTTPS 443 端口、订阅不活跃 |

## 与 `/session` 命令的关系

`/session`（别名 `/remote`）是另一个与远程相关的命令，但功能不同于 Remote Control：

| 命令 | 功能 |
|------|------|
| `/remote-control` `/rc` | 启用双向远程控制——从浏览器/Mobile 实时操控终端会话 |
| `/session` `/remote` | 显示远程会话 URL 和 QR 码——用于在其他设备上查看/连接会话 |
| `/remote-env` | 配置远程环境设置（远程服务器上的 Claude Code 实例） |
| `/desktop` `/app` | 将当前会话转交到 Claude Desktop 应用继续 |
| `/mobile` `/ios` `/android` | 显示下载 Claude Mobile 应用的 QR 码 |

## 行业对比

在 18 款对比的 AI 编程 Agent 中，Remote Control 为 **Claude Code 独有**功能：

| Agent | 远程控制能力 |
|-------|-------------|
| **Claude Code** | ✅ `/remote-control` + Server 模式 + `--spawn` 多会话 |
| **Copilot CLI** | ❌ 无（有 VS Code 集成但无终端远程操控） |
| **Codex CLI** | ❌ 无 |
| **Gemini CLI** | ❌ 无 |
| **Qwen Code** | ❌ 无（[功能缺口分析](../../comparison/qwen-code-feature-gaps.md)，需从零构建） |
| **Kimi CLI** | ❌ 无（有 Wire 协议但未实现远程控制） |
| **其他 Agent** | ❌ 无 |

## 实现参考：面向 Code Agent 开发者

> 以下数据来自 v2.1.87 ELF 二进制（SEA，228MB，2026-03-29 构建）中嵌入的 JavaScript 代码反编译提取。变量名经过 minification 处理（如 `Z6H`、`Cl7`、`Ra`），但字符串常量、对象键名、Zod schema 定义保持可读。
>
> **适用场景**：其他 Code Agent 开发者实现类似"远程控制"功能时，可将本节作为架构参考。Claude Code 的实现是经过生产验证的方案，但并非唯一可行路径。

### 内部状态机（Redux Store）

Remote Control 在 Redux AppState 中维护 13 个桥接状态字段（反编译提取自 `Z6H` 初始状态对象）：

```javascript
// v2.1.87 二进制反编译：AppState 初始状态
replBridgeEnabled: false,          // 是否启用桥接（旧字段，已迁移至 remoteControlAtStartup）
replBridgeExplicit: false,         // 用户是否主动启用（vs 自动启用）
replBridgeOutboundOnly: false,     // 仅出站模式：可推送消息但不接受远程控制指令
replBridgeConnected: false,        // 与中继服务器的连接状态
replBridgeSessionActive: false,    // 是否有活跃的远程客户端会话
replBridgeReconnecting: false,     // 是否正在重连中
replBridgeConnectUrl: undefined,   // 远程客户端连接 URL（供 QR 码/链接使用）
replBridgeSessionUrl: undefined,   // 会话管理 URL
replBridgeEnvironmentId: undefined,// 运行环境标识（用于 spawn 多会话路由）
replBridgeSessionId: undefined,    // 当前桥接会话 ID
replBridgeError: undefined,        // 最近错误信息
replBridgeInitialName: undefined,  // 初始会话名称（--name 参数值）
showRemoteCallout: false           // UI 标志：是否显示远程控制提示
```

**状态迁移逻辑**（反编译 `Cl7` 函数）：

```javascript
// 旧版迁移：replBridgeEnabled → remoteControlAtStartup
function migrateBridgeConfig(state) {
  if (state.replBridgeEnabled === undefined) return state;
  if (state.remoteControlAtStartup !== undefined) return state;
  let next = {...state, remoteControlAtStartup: Boolean(state.replBridgeEnabled)};
  delete next.replBridgeEnabled;
  return next;
}
```

**实现要点**：
- `replBridgeEnabled` 是旧字段名，当前版本使用 `remoteControlAtStartup`（选项：`"true"` / `"false"` / `"default"`）
- `replBridgeOutboundOnly` 为 `true` 时，用户界面显示 "This session is outbound-only. Enable Remote Control locally to allow inbound control."
- `replBridgeReconnecting` 用于 UI 展示重连状态（Connecting/Disconnected 循环问题与此状态相关）

### Polling 配置参数（服务端可调）

服务端下发 polling 配置，客户端通过 Zod schema 校验后使用。以下为反编译提取的默认值和校验规则：

```javascript
// v2.1.87 二进制反编译：默认 polling 配置
const DEFAULT_POLL_CONFIG = {
  poll_interval_ms_not_at_capacity: 2000,           // 未满容量时：2 秒轮询
  poll_interval_ms_at_capacity: 600000,              // 满容量时：10 分钟心跳（或 0=禁用）
  non_exclusive_heartbeat_interval_ms: 0,             // 非独占心跳：默认关闭
  multisession_poll_interval_ms_not_at_capacity: 2000, // 多会话未满：2 秒
  multisession_poll_interval_ms_partial_capacity: 2000, // 多会话部分满：2 秒
  multisession_poll_interval_ms_at_capacity: 600000,    // 多会话满：10 分钟
  reclaim_older_than_ms: 5000,                        // 回收阈值：5 秒后回收废弃会话
  session_keepalive_interval_v2_ms: 120000            // WebSocket ping/pong：2 分钟
};
```

**Zod 校验 schema**（`hM9`）：

| 参数 | 类型 | 约束 | 默认值 |
|------|------|------|--------|
| `poll_interval_ms_not_at_capacity` | `int` | `≥ 100` | `2000` |
| `poll_interval_ms_at_capacity` | `int` | `= 0 或 ≥ 100` | `600000` |
| `non_exclusive_heartbeat_interval_ms` | `int` | `≥ 0` | `0` |
| `reclaim_older_than_ms` | `int` | `≥ 1` | `5000` |
| `session_keepalive_interval_v2_ms` | `int` | `≥ 0` | `120000` |

**配置加载机制**：

```javascript
// 通过远程配置服务加载，TTL 5 分钟
loadConfig("tengu_bridge_poll_interval_config", DEFAULT_POLL_CONFIG, 300000);
```

**实现要点**：
- Poll 间隔是**服务端可调**的，客户端不应硬编码——通过远程配置服务动态下发
- 满容量时（`at_capacity`）poll 间隔从 2s 切换到 10min，实质进入"心跳保活"模式
- `reclaim_older_than_ms: 5000` 意味着服务器 5 秒无响应即可判定会话废弃——实现者需注意网络抖动场景
- `session_keepalive_interval_v2_ms` 是 WebSocket 层的 ping/pong，与 HTTP 层的 poll 互补

### 消息协议（Wire Format）

Remote Control 使用 JSON-lines 格式进行消息传输。以下消息类型来自反编译提取：

| 消息类型 | 方向 | 用途 | Zod Schema |
|----------|------|------|------------|
| `user` | 远程→本地 | 用户输入消息 | `y.object({type: "user", content: [...]})` |
| `assistant` | 本地→远程 | Agent 响应 | — |
| `system` | 本地→远程 | 系统消息 | — |
| `control_request` | 远程→本地 | 权限/模式/模型变更请求 | — |
| `control_response` | 本地→远程 | 对 control_request 的响应 | — |
| `control_cancel_request` | 本地→远程 | 取消未决的 control_request | — |
| `keep_alive` | 双向 | 心跳保活（收到时跳过处理） | `y.object({type: y.literal("keep_alive")})` |
| `update_environment_variables` | 本地→本地 | 运行时环境变量更新（如 token 刷新） | — |
| `bridge_state` | 双向 | 桥接状态变更通知 | — |

**keep_alive 处理逻辑**：

```javascript
// 收到 keep_alive 消息时直接跳过，不做任何处理
if (message.type === "keep_alive") continue;
```

**token 动态更新机制**：

```javascript
// 通过 stdin 注入更新后的 access token
function updateAccessToken(newToken) {
  this.accessToken = newToken;
  this.writeStdin(JSON.stringify({
    type: "update_environment_variables",
    variables: { CLAUDE_CODE_SESSION_ACCESS_TOKEN: newToken }
  }) + "\n");
}
```

### Token 刷新系统

反编译提取的 token 刷新参数（`dn$` 函数）：

| 参数 | 值 | 说明 |
|------|-----|------|
| `refreshBufferMs` | `300000`（5 分钟） | Token 过期前提前刷新的缓冲时间 |
| `followUpRefreshMs` | `1800000`（30 分钟） | 刷新后的 follow-up 刷新间隔 |
| `maxFailures` | `3` | 最大刷新失败次数 |
| `retryDelayMs` | `60000`（1 分钟） | 刷新失败后的重试延迟 |

**刷新策略**：基于 JWT expiry 的定时调度——在 token 过期前 5 分钟触发刷新，最多失败 3 次后放弃。

### Bridge 初始化接口（initReplBridge）

反编译提取的 `initReplBridge` 回调接口，这是 Remote Control 的核心桥接层：

```javascript
// initReplBridge 调用签名
const bridge = await initReplBridge({
  // 远程端发来的用户消息
  onInboundMessage(message) { /* 注入到本地对话流 */ },

  // 远程端的权限审批响应
  onPermissionResponse(response) { /* 注入 control_response */ },

  // 远程端请求中断当前操作
  onInterrupt() { abortController?.abort() },

  // 远程端切换模型
  onSetModel(model) { /* 更新当前模型 */ },

  // 远程端调整 thinking token 预算
  onSetMaxThinkingTokens(tokens) { /* 更新配置 */ },

  // 桥接状态变更通知
  onStateChange(state, metadata) { /* 更新 Redux store */ },

  // 初始消息（用于恢复断连前的上下文）
  initialMessages: previousMessages.length > 0 ? previousMessages : undefined
});
```

**返回值**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `bridgeSessionId` | `string` | 桥接会话唯一标识 |
| `sessionIngressUrl` | `string` | 会话入口 URL |
| `environmentId` | `string` | 运行环境标识 |
| `sendControlRequest()` | `function` | 向远程端发送控制请求 |
| `sendControlCancelRequest()` | `function` | 取消未决的控制请求 |
| `writeMessages()` | `function` | 向远程端写入消息流 |
| `teardown()` | `function` | 关闭桥接、清理资源 |

**会话注册响应格式**（反编译 `ZH` 函数）：

```javascript
// initReplBridge 成功后，构造响应数据
{
  session_url: buildSessionUrl(bridgeSessionId, sessionIngressUrl),
  connect_url: buildConnectUrl(environmentId, sessionIngressUrl),
  environment_id: environmentId
}
```

### Bridge 子进程环境变量

Server 模式下 `--spawn` 创建的子进程继承以下环境变量（反编译提取）：

```javascript
// spawn 子进程的环境变量设置
{
  CLAUDE_CODE_OAUTH_TOKEN: undefined,              // 显式清除，防止子进程用 OAuth token 重新注册
  CLAUDE_CODE_ENVIRONMENT_KIND: "bridge",          // 标识为桥接子进程
  CLAUDE_CODE_SESSION_ACCESS_TOKEN: accessToken,   // 传递会话访问凭证
  CLAUDE_CODE_POST_FOR_SESSION_INGRESS_V2: "1",    // 启用 V2 会话入口协议
  CLAUDE_CODE_USE_CCR_V2: "1",                     // 使用 CCR V2（如果 useCcrV2=true）
  CLAUDE_CODE_WORKER_EPOCH: String(workerEpoch),    // Worker epoch（如果 useCcrV2=true）
  CLAUDE_CODE_FORCE_SANDBOX: "1"                    // 强制沙箱（如果 --sandbox）
}
```

**实现要点**：
- `CLAUDE_CODE_OAUTH_TOKEN` 被显式设为 `undefined`——子进程不应使用父进程的 OAuth 凭证重新注册，而应通过 `SESSION_ACCESS_TOKEN` 接管会话
- `CLAUDE_CODE_ENVIRONMENT_KIND: "bridge"` 让子进程知道自己在桥接模式下运行，调整行为（如不启动自己的 polling）
- `CLAUDE_CODE_POST_FOR_SESSION_INGRESS_V2: "1"` 启用更新的会话入口协议

### 并发会话管理（PID File）

反编译提取的会话注册文件格式和更新逻辑：

**PID 文件路径**：`$CONFIG_DIR/sessions/{process.pid}.json`

**注册时写入**：

```javascript
// 会话注册：写入 PID 文件
await fs.writeFile(pidFilePath, JSON.stringify({
  pid: process.pid,
  sessionId: getSessionId(),
  cwd: getCurrentWorkingDir(),
  startedAt: Date.now(),
  kind: sessionKind,                              // "interactive" | "server" | ...
  entrypoint: process.env.CLAUDE_CODE_ENTRYPOINT,  // "cli" | "remote" | ...
  name: sessionName                                // 可选
}));
```

**更新逻辑**（`gv7` 函数）：

```javascript
// 非原子更新：read → merge → write（存在竞态条件）
async function updatePidFile(updates) {
  const path = join(configDir(), `${process.pid}.json`);
  try {
    const existing = JSON.parse(await fs.readFile(path, "utf8"));
    await fs.writeFile(path, JSON.stringify({...existing, ...updates}));
  } catch (err) {
    log(`[concurrentSessions] updatePidFile failed: ${formatError(err)}`);
  }
}
```

**已知问题**：此 read-modify-write 操作**非原子**（缺少 tmp+rename），在并发场景下可能导致 JSON 文件损坏（[GitHub #41195](https://github.com/anthropics/claude-code/issues/41195)）。实现者应使用 `writeFileSync(tmp, data)` + `renameSync(tmp, path)` 的原子写入模式。

### Bridge 会话注册 Schema

反编译提取的 Zod schema（`pN9`），用于注册桥接会话：

```javascript
// 会话注册请求体 schema
const bridgeSessionSchema = z.object({
  session_id: z.string(),         // 会话唯一标识
  ws_url: z.string(),             // WebSocket 连接 URL
  work_dir: z.string().optional() // 工作目录（可选）
});
```

### CLI 完整参数（remote-control 子命令）

反编译提取的 `claude remote-control` 完整参数列表：

```
claude remote-control [options]
  --spawn <mode>                      Spawn 模式：same-dir | worktree | session
  --capacity <N>                      最大并发会话数
  --create-session-in-dir <path>      在指定目录创建会话
  --session-id <id>                  恢复指定会话 ID
  --continue                          继续上次会话
  --permission-mode <mode>            权限模式
  --name <name>                       会话名称
  --verbose                           详细日志
  --sandbox                           启用沙箱
  --debug-file <path>                 调试输出文件
  --session-timeout-ms <ms>           会话超时（毫秒）
```

**新增发现**（相比官方文档）：

| 参数 | 官方文档 | 反编译发现 |
|------|----------|-----------|
| `--spawn session` | 未提及 | 第三种 spawn 模式 |
| `--create-session-in-dir` | 未提及 | 在指定目录创建会话 |
| `--session-id` | 未提及 | 恢复特定会话 ID |
| `--session-timeout-ms` | 未提及 | 精确控制会话超时时间 |
| `--debug-file` | 未提及 | 调试输出到文件 |

### 遥测事件

Remote Control 相关的遥测事件前缀为 `tengu_bridge_*`，反编译提取到以下事件名：

| 事件名 | 用途 |
|--------|------|
| `tengu_bridge_token_refreshed` | Token 刷新成功/失败追踪 |
| `tengu_bridge_multi_session_denied` | 多会话访问被拒绝（capacity 已满） |
| `tengu_bridge_poll_interval_config` | Polling 配置加载追踪 |
| `tengu_concurrent_sessions` | 并发会话状态追踪 |

### 客户端类型检测

反编译提取的客户端类型判定逻辑：

```javascript
// 客户端类型检测
function detectClientType() {
  const hasSessionToken = process.env.CLAUDE_CODE_SESSION_ACCESS_TOKEN
                       || process.env.CLAUDE_CODE_WEBSOCKET_AUTH_FILE_DESCRIPTOR;
  if (process.env.CLAUDE_CODE_ENTRYPOINT === "remote" || hasSessionToken) {
    return "remote";  // Remote Control 桥接客户端
  }
  // ... 其他类型判断
}
```

**关键环境变量**：

| 变量 | 说明 | 来源 |
|------|------|------|
| `CLAUDE_CODE_SESSION_ACCESS_TOKEN` | 存在时标记为 "remote" 客户端类型 | 反编译 |
| `CLAUDE_CODE_WEBSOCKET_AUTH_FILE_DESCRIPTOR` | 存在时标记为 "remote" 客户端类型（文件描述符方式传递 WebSocket 认证） | 反编译 |
| `CLAUDE_CODE_ENTRYPOINT` | 值为 `"remote"` 时标记为远程入口 | 反编译 |
| `CLAUDE_CODE_REMOTE` | 存在时影响 auto-memory 行为；传递给 teammate spawn 环境 | 反编译 |

### 实现建议：架构模式总结

基于以上反编译分析，实现类似 Remote Control 功能的推荐架构模式：

```
┌──────────────────────────────────────────────────────────────────┐
│                      推荐架构模式                                 │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────┐    ① Register       ┌──────────────┐               │
│  │  Local   │ ──────────────────→ │              │               │
│  │  Agent   │ ←────────────────── │   Relay      │               │
│  │  Process │    ② Token + URL    │   Server     │               │
│  │          │                     │              │               │
│  │          │    ③ HTTPS Poll     │  - 消息路由   │               │
│  │          │ ──────────────────→ │  - 凭证管理   │               │
│  │          │ ←────────────────── │  - 会话追踪   │               │
│  │          │    ④ Stream Msgs    │  - 配置下发   │               │
│  └─────────┘                     └──────┬───────┘               │
│                                         │                        │
│                                    ⑤ WebSocket/HTTPS            │
│                                         │                        │
│                                  ┌──────▼───────┐               │
│                                  │   Remote      │               │
│                                  │   Client      │               │
│                                  │  (Web/Mobile) │               │
│                                  └──────────────┘               │
│                                                                  │
│  关键设计决策：                                                    │
│  1. 本地仅出站 HTTPS → 企业防火墙穿透                              │
│  2. 服务端下发 poll 配置 → 运行时可调                              │
│  3. JWT + 短期凭证 → 定时刷新 (过期前 5min)                        │
│  4. JSON-lines 消息协议 → 简单可扩展                               │
│  5. PID file 并发注册 → 需原子写入（tmp+rename）                    │
│  6. 子进程显式清除 OAuth token → 防止重复注册                       │
│  7. keep_alive 空操作 → 降低无用处理开销                            │
│  8. 客户端类型检测 → 区分 local/remote/bridge 行为                  │
└──────────────────────────────────────────────────────────────────┘
```

### 与 Gemini CLI 的对比参考

Qwen Code 基于 Gemini CLI 分叉（[Qwen Code EVIDENCE](../qwen-code/EVIDENCE.md)），Gemini CLI 使用 Google Cloud relay 实现 `--remote` 功能。两者实现路径对比：

| 维度 | Claude Code | Gemini CLI / Qwen Code |
|------|-------------|----------------------|
| **中继架构** | Anthropic API 中继 | Google Cloud relay |
| **本地传输** | HTTPS polling（服务端可调） | SSE (Server-Sent Events) |
| **认证** | claude.ai OAuth full-scope | Google OAuth |
| **消息格式** | JSON-lines（8+ 消息类型） | SSE stream |
| **状态管理** | Redux 13 字段状态机 | — |
| **Token 刷新** | JWT expiry - 5min 提前刷新 | — |
| **多会话** | `--spawn` + `--capacity` + PID file | — |

> **注意**：Gemini CLI 的 `--remote` 实现细节未公开源码，对比数据来自 CLI help 输出和行为观察，标注 `⚠️` 的条目为推断。

## 评价与优缺点分析

### 核心优势

**1. 唯一实现"终端会话远程操控"的 Agent**

Claude Code 的 Remote Control 在所有 18 款 Agent 中独树一帜——它不是简单的 Web UI 或 API 暴露，而是将一个**正在运行的终端交互会话**双向桥接到浏览器/手机。这意味着远程端可以完整使用本地文件系统、MCP 服务器、项目配置，实现真正的"离开工位不中断工作"。

**2. 安全架构设计审慎**

- 仅出站 HTTPS，零入站端口——企业防火墙友好
- 强制 claude.ai OAuth full-scope token——排除 API Key / 第三方提供商
- Team/Enterprise 管理员门控——组织级管控
- 多短期凭证隔离——防止凭证泄露横向移动

**3. 多模式灵活适配**

三种启动方式（Server 模式 / 交互式 / 会话内）覆盖不同场景：长时间无人值守用 Server 模式，日常开发用交互式，临时需要用会话内。`--spawn worktree` 支持多会话文件隔离，`--capacity` 防止资源耗尽。

**4. 跨设备生态完整**

Remote Control 不是孤立功能，而是 Claude Code 跨设备矩阵的一部分——配合 `--remote`（推到 Web）、`/teleport`（拉回终端）、Dispatch（手机委派）、Channels（Telegram/Discord 推送）、`/schedule`（定时任务），形成从"实时远程操控"到"异步事件驱动"的完整工作流覆盖。

### 核心短板

**1. 强绑定 claude.ai 生态**

- 不支持 API Key、Bedrock、Vertex、Foundry——企业私有化部署场景被排除
- `DISABLE_TELEMETRY` 会意外阻止注册——隐私敏感用户被迫在遥测和远程控制之间二选一
- Team/Enterprise 默认关闭，部分合规配置不可覆盖

**2. 稳定性问题**

截至 v2.1.81，社区反馈了 8 个已知问题（见上文），其中几个影响实际使用：
- 僵尸进程：服务端关闭后客户端不退出，内存不释放
- 连接循环：Connecting/Disconnected 反复，无法稳定工作
- 移动端 stale 连接：WebSocket/session token 过期后不可恢复
- VS Code 扩展忽略 `remoteControlAtStartup` 配置

**3. 本地进程强依赖**

- 终端必须保持打开，关闭即断
- 网络断连 ~10 分钟后超时退出
- 不如 `/schedule`（CCR 云端执行）那样能"关机后继续跑"

**4. 闭源且证据有限**

通信协议细节（polling 间隔、消息格式、端点 URL）未公开，二进制反编译也未完整暴露 Remote Control 专用端点。安全审计只能基于官方文档描述，无法独立验证实现。

### 设计权衡总结

| 设计决策 | 收益 | 代价 |
|----------|------|------|
| 本地执行 + 远程操控 | 完整本地环境可用 | 终端必须在线 |
| HTTPS polling 中继 | 零入站端口，企业友好 | 可能带来更高交互延迟 ⚠️ 推断 |
| claude.ai OAuth 强绑定 | 统一认证、管理员管控 | 排除 API Key / 第三方用户 |
| 多短期凭证 | 凭证泄露影响面小 | 增加注册失败点 |
| 遥测与资格检查耦合 | — | 会导致隐私用户被意外阻断 |

## 竞品对比：远程访问能力全景

Claude Code Remote Control 在"跨设备远程操控终端会话"维度上独有，但"远程访问"本身在其他 Agent 中有不同形态的实现：

### 功能对比矩阵

> **维度说明**：本表统一按「是否具备该能力」横向对比。各能力定义如下——
> - **终端会话远程操控**：从其他设备实时操控一个正在运行的 CLI 会话
> - **Web/浏览器 UI**：提供可通过浏览器访问的图形界面
> - **多客户端同时连接**：同一会话可被多种客户端（TUI/Web/Desktop/Mobile）同时连接
> - **原生移动端 App**：iOS/Android 原生应用（非移动浏览器访问 Web UI）
> - **零入站端口**：无需在本地开放任何监听端口

| 能力 | Claude Code | Kimi CLI | OpenCode | Goose | Codex CLI | Copilot CLI | Aider |
|------|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| **终端会话远程操控** | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Web/浏览器 UI** | ❌ | ✅ FastAPI+React | ✅ SolidJS（实验） | ❌（仅 Desktop App，见 [说明](../goose.md)） | ❌ | ❌ | ❌ |
| **多客户端同时连接** | ✅ TUI+浏览器+Mobile | ✅ Wire 四客户端 | ✅ TUI+Web+Desktop | ✅ CLI+Desktop | ❌ | ❌ | ❌ |
| **原生移动端 App** | ✅ iOS/Android | ❌（移动浏览器可访问 Web UI） | ❌ | ❌ | ❌ | ❌ | ❌ |
| **零入站端口** | ✅（outbound-only 中继） | ❌（开端口） | ❌（开端口） | ❌（开端口） | ❌ | N/A | N/A |
| **远程 IDE 集成** | ✅ VS Code | ✅ ACP | ❌ | ❌ | ✅ app-server | ✅ 原生 | ❌ |
| **协议** | HTTPS polling + 中继 | Wire v1.6 (WS) | Hono HTTP+WS+SSE | REST (Axum) | JSON-RPC (WS) | CLI only | CLI only |

### 竞品关键差异

**Kimi CLI**（最完整的 Web UI）：
- `kimi web` 启动 FastAPI + React Web UI（默认 `localhost:5494`），支持多会话管理、实时 diff 预览、审批对话框
  （来源：[Kimi CLI 架构文档](../kimi-cli/03-architecture.md)）
- Wire v1.6 协议统一 TUI / Web / IDE / 自定义 UI 四种客户端
  （来源：[Kimi CLI 架构文档](../kimi-cli/03-architecture.md)）
- 支持 `--network`、`--lan-only`、`--public` 三种网络模式，token 认证
- **劣势**：需要在本地开放端口（不像 Claude Code 的 outbound-only），无原生移动 App

**OpenCode**（多客户端架构）：
- TUI + Web Console（SolidJS）+ Desktop（Tauri v2 / Electron）三客户端共享 Hono HTTP 后端
  （来源：[OpenCode 架构文档](../opencode/03-architecture.md)）
- MDNS 本地网络设备发现
- **劣势**：远程 workspace 仍为实验性功能，稳定性待验证

**Goose**（REST API 驱动）：
- `goose-server`（Axum HTTP）提供 REST API，Electron Desktop App 作为 GUI 客户端
  （来源：[Goose 架构文档](../goose/03-architecture.md)、[EVIDENCE](../goose/EVIDENCE.md)）
- 仓库文档宣称支持 CLI/Web/Desktop 三种客户端（[Goose 概述](../goose.md)），但实际源码中仅有 CLI (`goose-cli`) 和 Desktop (`ui/desktop/`) 两个具体客户端实现；"Web" 标签指 `goose-server` 的 HTTP API 可供 Web 客户端连接，但无独立浏览器前端
- **劣势**：无独立浏览器 Web UI（仅有 HTTP API）、无移动端

**Codex CLI**（IDE 集成导向）：
- `codex app-server` 提供 JSON-RPC 2.0 over stdio/WebSocket，`--remote` 连接远程实例
  （来源：[Codex CLI 命令文档](../codex-cli/02-commands.md)、[EVIDENCE](../codex-cli/EVIDENCE.md)）
- **劣势**：面向 IDE 插件设计，非通用远程访问

### 为什么没有其他 Agent 复制 Remote Control？（作者分析，非源码验证结论）

> ⚠️ 以下为基于公开信息的分析推测，未经源码或官方声明验证。

| 可能原因 | 说明 |
|----------|------|
| **需要云基础设施** ⚠️ 推断 | Anthropic 的中继服务器和 claude.ai/code 平台是 Remote Control 的必要前提。开源 Agent 缺乏同等规模的云中继设施 |
| **认证体系强绑定** ⚠️ 推断 | 强制 OAuth + 短期凭证 + 管理员门控依赖中心化身份系统，自托管 Agent 难以复制 |
| **产品定位差异** ⚠️ 推断 | Claude Code 定位"企业级 AI 编程平台"（含 Web/Desktop/Mobile 多端），大多数 Agent 定位"开发者本地工具" |
| **替代方案成本更低** ⚠️ 推断 | Kimi CLI/OpenCode 等通过本地 Web UI + 开端口的方式提供了基本的远程访问能力，对多数场景已够用 |

> **免责声明**：以上数据基于 2026 年 Q1 源码分析和官方文档，可能已过时。
