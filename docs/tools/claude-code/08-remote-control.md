# 8. Claude Code Remote Control（远程控制）

> Remote Control 允许从手机、平板或任意浏览器远程操控本地运行的 Claude Code 终端会话。会话**始终在本地执行**，远程端仅作为交互窗口。基于 Anthropic 官方文档（2026-03）和 v2.1.81 二进制反编译分析。

## 概述

Remote Control 是 Claude Code 的跨设备会话桥接功能，在 18 款主流 AI 编程 Agent 中**为 Claude Code 独有**（源码: `docs/comparison/features.md`）。它解决了开发者的一个核心痛点：启动了一个长时间的终端代理任务后，需要离开工位继续监控或干预。

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

> **源码位置**：`/remote-control` 命令类型为 `local-jsx`（反编译提取，`源码: docs/tools/claude-code/02-commands.md`），渲染远程控制配置 UI 并启动到 claude.ai/code 的连接。

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

## 连接与安全架构

### 网络拓扑

```
┌─────────────┐         出站 HTTPS          ┌──────────────────┐
│  本地终端    │ ──────────────────────────→  │  Anthropic API   │
│ (Claude Code)│ ←────────────────────────── │  (消息中继)       │
└─────────────┘         流式响应              └───────┬──────────┘
                                                      │
                                              出站 HTTPS │
                                                      │
                                              ┌───────▼──────────┐
                                              │  浏览器/手机 App   │
                                              │ (claude.ai/code)  │
                                              └──────────────────┘
```

| 方面 | 细节 |
|------|------|
| **网络方向** | 仅出站 HTTPS——**本地不开放入站端口** |
| **通信机制** | 本地进程向 Anthropic API 注册并**轮询获取工作**（polling） |
| **消息路由** | Anthropic 服务器在 Web/Mobile 客户端和本地会话之间通过**流式连接**中继消息 |
| **传输安全** | 所有流量经 Anthropic API 传输，全程 **TLS** 加密（与普通 Claude Code 会话相同） |
| **凭证** | 使用**多个短期凭证**，每个凭证限定单一用途且独立过期 |

> **注意**：并非直接向本地机器建立 WebSocket 连接。本地进程通过 polling Anthropic API 获取消息，消息经由 Anthropic 基础设施中继。

### 相关环境变量（反编译提取）

| 变量 | 影响 |
|------|------|
| `ANTHROPIC_API_KEY` | 阻止 Remote Control；需清除并使用 OAuth 登录 |
| `CLAUDE_CODE_OAUTH_TOKEN` | 提供有限范围 token；与 Remote Control 不兼容 |
| `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC` | 可能破坏资格检查 |
| `DISABLE_TELEMETRY` | 可能破坏资格检查 |
| `CLAUDE_CODE_USE_BEDROCK` | 不兼容——Remote Control 要求 claude.ai 认证 |
| `CLAUDE_CODE_USE_VERTEX` | 不兼容——Remote Control 要求 claude.ai 认证 |
| `CLAUDE_CODE_USE_FOUNDRY` | 不兼容——Remote Control 要求 claude.ai 认证 |
| `SESSION_ACCESS_TOKEN` | 会话访问凭证（反编译提取，`源码: EVIDENCE.md`） |
| `WEBSOCKET_AUTH_*` | WebSocket 认证相关凭证（反编译提取） |

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
| **`--teleport`** | CLI 拉回 Web 会话 | 本地机器 | 将云端会话拉到本地继续 |

## 限制

| 限制 | 说明 |
|------|------|
| **单远程会话/进程** | 交互模式（非 Server 模式）下每个进程仅一个远程会话。需多会话时用 `--spawn` |
| **终端必须保持打开** | 关闭终端或终止进程会结束会话 |
| **网络超时** | 若机器在线但网络不可达持续约 10 分钟，会话超时并退出进程 |
| **不支持 API Key** | 必须使用 claude.ai OAuth 认证 |
| **不支持第三方提供商** | Bedrock / Vertex / Foundry 用户无法使用 |

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
| **Qwen Code** | ❌ 无（`源码: docs/comparison/qwen-code-feature-gaps.md`，需从零构建） |
| **Kimi CLI** | ❌ 无（有 Wire 协议但未实现远程控制） |
| **其他 Agent** | ❌ 无 |

> **免责声明**：以上数据基于 2026 年 Q1 源码分析和官方文档，可能已过时。Qwen Code 的 Remote Control 功能缺口已被标记为 P2 优先级。
