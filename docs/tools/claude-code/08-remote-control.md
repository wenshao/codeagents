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

**数据流**：
1. **本地 → Anthropic API**：本地进程启动时用 full-scope OAuth token 注册会话，随后以 polling 方式持续获取待处理消息
2. **Anthropic API → 本地**：服务器有消息时通过 streaming connection 下发（长轮询或 SSE over HTTPS）
3. **Anthropic API ↔ 浏览器/手机**：远程客户端通过 WebSocket 连接到 Anthropic 基础设施（GitHub Issues 中观察到 stale WebSocket 连接行为）

| 方面 | 细节 |
|------|------|
| **本地→服务器** | 出站 HTTPS polling（非 WebSocket）。本地不开放入站端口 |
| **远程客户端→服务器** | WebSocket 连接到 Anthropic 基础设施（`WEBSOCKET_AUTH_*` 凭证认证） |
| **消息路由** | Anthropic 服务器在远程客户端和本地会话之间双向中继 |
| **传输安全** | 全程 TLS 加密，与普通 Claude Code 会话相同 |
| **凭证体系** | 多个短期凭证，每个限定单一用途，独立过期 |

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

| 路径 | 内容 | 来源 |
|------|------|------|
| `~/.claude/sessions/{pid}.json` | 会话元数据：`name`、`status`、`updatedAt`、`bridgeSessionId`、`messagingSocketPath` | GitHub Issues |
| `/tmp/cc-socks/*.sock` | 本地进程间通信的 Unix domain socket | GitHub Issues |
| `~/.claude/projects/<project-hash>/` | 会话对话历史（`.jsonl` 格式），`cleanupPeriodDays`（默认 30 天）后自动清理 | [EVIDENCE.md](./EVIDENCE.md) |

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
| **4. 网络隔离** | 仅出站 HTTPS，零入站端口 | 本地机器不暴露任何攻击面 |
| **5. 传输加密** | 全程 TLS | 与普通 Claude Code 会话相同 |
| **6. 可选沙箱** | `--sandbox` 启用文件系统+网络隔离 | 默认关闭，Server 模式可启用 |
| **7. 安全分类器** | auto mode 双层防御（服务端 probe + 客户端分类器） | [工程博客](https://anthropic.com/engineering/claude-code-auto-mode)，Sonnet 4.6 驱动 |

**遥测耦合问题**：`DISABLE_TELEMETRY=1` 会阻止 Remote Control 注册（[GitHub #41189](https://github.com/anthropics/claude-code/issues/41189)），因为资格检查依赖遥测通道。这是一个已知的架构耦合问题。

### 相关 API 端点（反编译提取）

| 端点 | 用途 | 来源 |
|------|------|------|
| `claude.ai/api/claude_code/settings` | 远程设置获取 | [EVIDENCE.md](./EVIDENCE.md) |
| `claude.ai/api/claude_code/policy_limits` | 策略限制查询 | [EVIDENCE.md](./EVIDENCE.md) |
| `claude.ai/api/oauth/authorize` | OAuth 认证 | [EVIDENCE.md](./EVIDENCE.md) |
| `api.anthropic.com/api/claude_code/metrics` | 遥测上报（资格检查依赖此通道） | [EVIDENCE.md](./EVIDENCE.md) |
| `claude.ai/api/ws/speech_to_text/voice_stream` | 语音转文字（非 Remote Control，但共用 WebSocket 基础设施） | [EVIDENCE.md](./EVIDENCE.md) |

> **注意**：Remote Control 专用的会话注册和消息中继端点 URL 未在 v2.1.81 二进制的 `--help` 输出或 rodata 段中明文暴露。上述端点为反编译中确认的基础设施端点，可能被 Remote Control 复用。

### 相关环境变量

前 6 项来自 [Anthropic 官方文档](https://docs.anthropic.com/en/docs/claude-code/remote-control)；后 4 项为反编译提取的变量名（[EVIDENCE.md](./EVIDENCE.md)），具体用途为推断。

| 变量 | 影响 | 来源 |
|------|------|------|
| `ANTHROPIC_API_KEY` | 阻止 Remote Control；需清除并使用 OAuth 登录 | 官方文档 |
| `CLAUDE_CODE_OAUTH_TOKEN` | 提供有限范围 token；与 Remote Control 不兼容 | 官方文档 |
| `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC` | 可能破坏资格检查 | 官方文档 |
| `DISABLE_TELEMETRY` | 阻止 Remote Control 注册（架构耦合 bug） | 官方文档 + GitHub #41189 |
| `CLAUDE_CODE_USE_BEDROCK` | 不兼容——Remote Control 要求 claude.ai 认证 | 官方文档 |
| `CLAUDE_CODE_USE_VERTEX` | 不兼容——Remote Control 要求 claude.ai 认证 | 官方文档 |
| `CLAUDE_CODE_USE_FOUNDRY` | 不兼容——Remote Control 要求 claude.ai 认证 | 官方文档 |
| `SESSION_ACCESS_TOKEN` | 会话访问凭证（反编译提取） | EVIDENCE.md |
| `WEBSOCKET_AUTH_*` | WebSocket 认证凭证（反编译提取） | EVIDENCE.md |
| `SSE_PORT` | SSE 本地端口（反编译提取，可能用于 Remote Control 或 MCP SSE 传输） | EVIDENCE.md |

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

## 已知架构问题（社区反馈）

以下问题来自 GitHub Issues，反映了 Remote Control 当前实现的架构缺陷：

| 问题 | 根因 | 影响 | 来源 |
|------|------|------|------|
| **Pidfile 竞态** | `concurrentSessions.ts` 中 `updatePidFile()` 非原子 read-modify-write（缺少 tmp+rename） | 并发会话时 JSON 文件损坏，Bun `fallocate` 可产生 null 字节截断 | [#41195](https://github.com/anthropics/claude-code/issues/41195) |
| **遥测耦合** | `DISABLE_TELEMETRY=1` 阻止 RC 注册（资格检查走遥测通道） | RC 失败但报错信息误导为"未启用" | [#41189](https://github.com/anthropics/claude-code/issues/41189) |
| **僵尸进程** | 无 TCP read timeout、无 `CLOSE_WAIT` 检测、无空闲看门狗 | 服务端关闭连接后客户端进程不退出，占用 1+ GB 内存无限期 | [#41024](https://github.com/anthropics/claude-code/issues/41024) |
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

> **免责声明**：以上数据基于 2026 年 Q1 源码分析和官方文档，可能已过时。Qwen Code 的 Remote Control 功能缺口已被标记为 P2 优先级。
