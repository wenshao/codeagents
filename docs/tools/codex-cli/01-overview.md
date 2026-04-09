# 1. Codex CLI 概述——Code Agent 开发者视角

> **阅读对象**：正在开发 Qwen Code / Gemini CLI 等 CLI Code Agent 的工程师
>
> **核心问题**：Codex CLI 作为 OpenAI 第一方开源 Agent，其 Rust 原生架构、沙箱安全模型、Cloud 执行模式有哪些值得借鉴？哪些依赖 OpenAI 生态无法复制？

## 一、为什么要研究 Codex CLI

Codex CLI 是 OpenAI 官方推出的开源终端编程代理（Apache-2.0），也是当前唯一采用 **Rust 原生二进制 + Node.js 薄启动层**架构的主流 Code Agent。它在 GitHub 获得 ~68k Stars，拥有 28 个斜杠命令、9 个代理工具、52 个 Feature Flag、15 个 CLI 子命令、5 种审批模式、4 级沙箱隔离，以及实验性的 Cloud 执行和 App-Server IDE 集成。

对于 Qwen Code 开发者，Codex CLI 的价值在于三个独特维度：

1. **Rust 原生架构**——证明了 CLI Agent 可以跳过 Node.js/TypeScript 全栈，用 Rust 构建 ~137MB 静态二进制，获得内存安全 + 高性能沙箱。这与 Claude Code（TypeScript + Bun 打包）和 Qwen Code（纯 TypeScript）形成鲜明对比。
2. **默认安全沙箱**——Codex 是唯一默认启用沙箱的主流 Agent（macOS Seatbelt、Linux Bubblewrap/Landlock、Windows 受限令牌），网络访问默认阻断。Claude Code 的沙箱可选，Qwen Code 仅有权限规则。
3. **Cloud 执行模型**——`codex cloud exec` 允许将任务提交到云端隔离环境执行 best-of-N，这是其他开源 Agent 尚未实现的模式。

## 二、能力矩阵速查

| 能力领域 | Codex CLI | Qwen Code | 差距 | 详见 |
|---------|-----------|-----------|------|------|
| **技术栈** | Rust 原生二进制（137MB）+ Node.js 启动层 | TypeScript + Node.js | 架构差异 | [03-架构](./03-architecture.md) |
| **命令系统** | 28 斜杠命令 + 15 CLI 子命令 | ~40 斜杠命令 | 小（Qwen 数量领先） | [02-命令](./02-commands.md) |
| **工具系统** | 9 工具（含 ToolSearchCall） | ~30 工具 | 大（Qwen 领先） | [02-命令](./02-commands.md) |
| **安全模型** | 5 种审批模式 + 4 级沙箱 + 默认网络隔离 | 权限规则 + Hook | 大（Codex 领先） | [03-架构](./03-architecture.md) |
| **MCP 支持** | 客户端 + 服务器双向 | 客户端 | 中 | [02-命令](./02-commands.md) |
| **会话管理** | resume/fork + UUID 持久化 | 无 | 大 | [02-命令](./02-commands.md) |
| **代码审查** | `codex review` 子命令 + `/review` 交互 | 无 | 大 | [02-命令](./02-commands.md) |
| **Cloud 执行** | 实验性 best-of-N | 无 | 大 | [03-架构](./03-architecture.md) |
| **IDE 集成** | App-Server JSON-RPC（90+ 方法） | 无 | 大 | [03-架构](./03-architecture.md) |
| **Feature Flag** | 52 个（含 stable/experimental/under-dev） | 无 Feature Flag 系统 | 大 | [02-命令](./02-commands.md) |
| **上下文压缩** | `/compact` + `enable_request_compression` | 单一 70% 手动压缩 | 中 | [02-命令](./02-commands.md) |
| **记忆系统** | `memories` flag（under-dev） | 简单笔记 | 中 | [02-命令](./02-commands.md) |
| **模型锁定** | 主要 OpenAI 模型（可通过 `--oss` 绕过） | 多模型支持 | 大（Qwen 领先） | — |

## 三、架构概览（开发者视角）

### 3.1 技术栈

| 组件 | Codex CLI | 开发者启示 |
|------|-----------|-----------|
| 核心语言 | Rust（静态编译 musl libc） | 内存安全 + 零 GC 停顿，但开发速度慢于 TypeScript |
| 启动层 | Node.js `codex.js`（~6KB） | 仅负责平台检测和 spawn 二进制，极薄 |
| 二进制体积 | ~137MB（静态链接，含 ripgrep） | 远大于 Claude Code（~227MB 含 Bun 运行时）但架构更纯粹 |
| 分发方式 | npm `@openai/codex` + 平台特定原生包 | 6 个平台包覆盖 x64/arm64 × Linux/macOS/Windows |
| 代码搜索 | 内置 ripgrep | 与 Claude Code 的 `file-index.node` 思路类似 |
| 开源许可 | Apache-2.0 | 可自由修改部署，Qwen Code 同为 Apache-2.0 |

### 3.2 核心循环（推断）

```
用户输入 / codex exec "prompt"
  │
  ├─ 审批模式检查（untrusted/on-request/never/granular）
  │
  ├─ 沙箱环境初始化（Seatbelt/Bubblewrap/Landlock/受限令牌）
  │     └─ 网络默认阻断
  │
  ├─ API 请求（OpenAI Chat Completions）
  │     ├─ 流式响应 → 工具调用解析
  │     ├─ LocalShellCall → 沙箱内执行
  │     ├─ ApplyPatch → 自有 diff 格式应用
  │     ├─ McpToolCall → MCP 服务器调用
  │     └─ 循环直到模型返回 end_turn
  │
  ├─ 上下文压缩检查（enable_request_compression）
  │
  └─ 会话持久化（~/.codex/sessions/UUID）
```

**与 Claude Code 的关键差异**：
1. **沙箱优先**：Codex 的工具执行在沙箱内进行（网络隔离），Claude Code 的沙箱是可选的。这意味着 Codex 的 `never` 审批模式依赖沙箱保护，而 Claude Code 依赖权限规则。
2. **ApplyPatch vs Edit**：Codex 使用自有的补丁格式（`*** Begin Patch`），Claude Code 使用 `Edit` 工具逐文件修改。Codex 的方式更适合批量修改，Claude Code 更精细。
3. **工具数量差距**：Codex 仅 9 个工具（精简路线），Claude Code 42 个工具（全面覆盖）。Codex 通过 `LocalShellCall` 的 `CommandAction` 子操作（Read/Search/ListFiles）弥补部分差距。

### 3.3 审批模式与沙箱交互矩阵

| 审批模式 | 沙箱 = read-only | 沙箱 = workspace-write | 沙箱 = danger-full-access |
|----------|-----------------|----------------------|--------------------------|
| `untrusted`（默认） | 每次询问 | 每次询问 | 每次询问 |
| `on-request` | 模型决定 | 模型决定（`--full-auto` 组合） | 模型决定 |
| `never` | 自动执行（只读） | 自动执行（推荐 CI/CD） | 自动执行（危险） |
| `granular`（未实现） | 按类别策略 | 按类别策略 | 按类别策略 |

**Qwen Code 对标**：Qwen Code 的权限模型是扁平的（允许/拒绝），缺少 Codex 的"审批模式 × 沙箱级别"二维控制。建议参考 Codex 的 `--full-auto`（on-request + workspace-write）组合，为自动化场景提供安全且高效的默认配置。

## 四、可借鉴 vs 不可复制

### 可借鉴的工程模式（与模型无关）

| 模式 | 核心价值 | 实现复杂度 |
|------|---------|-----------|
| 默认沙箱隔离 + 网络阻断 | 安全执行不可信代码，CI/CD 友好 | 大 |
| 审批模式 × 沙箱级别二维控制 | 精细平衡安全性与自动化程度 | 中 |
| MCP 双向支持（客户端 + 服务器） | Agent 既能调用外部工具，也能被其他 Agent 调用 | 中 |
| App-Server JSON-RPC 协议 | IDE 集成标准化，VS Code 扩展可复用 | 大 |
| 会话 resume/fork | 跨时间恢复工作 + 分叉探索 | 中 |
| `codex review` 独立子命令 | 代码审查可脱离交互会话使用，CI 集成友好 | 小 |
| Feature Flag 系统（52 个） | 实验性功能安全管理，灰度发布 | 中 |
| ApplyPatch 自有 diff 格式 | 批量文件修改效率高于逐文件 Edit | 小 |
| Cloud best-of-N 执行 | 关键任务多次尝试选最优 | 大 |
| CODEX.md/AGENTS.md 指令层级 | 4 级指令优先级（全局 → 项目 → 代理 → 技能） | 小 |

### OpenAI 独有优势（不可复制）

| 优势 | 为什么不可复制 |
|------|---------------|
| GPT-5 系列模型 | OpenAI 核心资产 |
| o-系列推理模型 | 依赖 OpenAI 独有的推理训练 |
| Cloud 执行基础设施 | 需要 OpenAI 的云端沙箱环境 |
| ChatGPT Apps/Connectors | 依赖 OpenAI 的应用生态 |
| Guardian 子代理安全审批 | 需要专门训练的安全审查模型 |

## 五、阅读路线推荐

### 如果你想改进安全模型
→ [03-架构](./03-architecture.md)：沙箱实现细节、审批模式与沙箱交互

### 如果你想扩展命令系统
→ [02-命令](./02-commands.md)：28 斜杠命令分类、15 CLI 子命令、工具系统

### 如果你想做 IDE 集成
→ [03-架构](./03-architecture.md)：App-Server 90+ JSON-RPC 方法、WebSocket 传输

### 如果你想做代码审查
→ [02-命令](./02-commands.md)：`codex review` 子命令参数、`/review` 交互命令

### 如果你想做会话管理
→ [02-命令](./02-commands.md)：resume/fork 机制、UUID 持久化

## 六、源码验证

本系列所有技术声明通过以下方式验证：

1. **二进制分析**：v0.116.0 Rust ELF static-pie x86-64 二进制（137MB），通过 `strings`、`codex --help`、`codex features list` 等提取
2. **官方文档**：[developers.openai.com/codex](https://developers.openai.com/codex) 斜杠命令、CLI 参考、审批与安全
3. **源码仓库**：[github.com/openai/codex](https://github.com/openai/codex)（Apache-2.0 开源）

原始证据见 [EVIDENCE.md](./EVIDENCE.md)。
