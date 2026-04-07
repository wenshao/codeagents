# 4. Hook 与插件系统——开发者参考

> OpenCode 的 Hook 系统有 18 种类型，通过 npm 包分发插件。其中 `tool.definition` Hook（运行时修改工具 Schema）和 `experimental.chat.system.transform`（修改系统提示）是竞品中独有的能力。
>
> **Qwen Code 对标**：Qwen Code 有 ~12 种 Hook 事件（command 类型）。OpenCode 的 npm 插件加载、工具定义修改 Hook、系统提示变换 Hook 是主要参考。

## 一、为什么 OpenCode 的 Hook 设计值得研究

### 竞品 Hook 对比

| Agent | Hook 数量 | 处理器类型 | 插件分发 | 独有能力 |
|-------|----------|-----------|---------|---------|
| **Claude Code** | 27 事件 | 6 种（含 prompt/agent） | Plugin marketplace | LLM 推理决策 |
| **OpenCode** | 18 种 | npm 插件 + 回调 | npm registry | 工具定义修改、系统提示变换 |
| **Gemini CLI** | 11 事件 | command + runtime | Extension | 模型层拦截 |
| **Qwen Code** | ~12 事件 | command | — | MessageBus 集成 |

**OpenCode 独有创新**：Claude Code 的 Hook 能拦截工具执行，但**不能修改工具本身的定义**。OpenCode 的 `tool.definition` Hook 允许插件在运行时改变工具的描述和参数 Schema——这意味着插件可以扩展或限制内置工具的能力，而不需要 fork 源码。

## 二、18 种 Hook 类型详解

### 核心 Hook

| Hook | 触发时机 | 返回值 | 用途 |
|------|---------|--------|------|
| `event` | 自定义事件触发 | void | 事件总线订阅 |
| `config` | 配置生命周期 | 配置修改 | 动态配置 |
| `auth` | 认证请求 | 认证 provider | 自定义认证（GitHub Copilot、GitLab、Poe） |
| `provider` | Provider 发现 | 模型列表 | 动态注册 Provider |

### 工具生命周期 Hook

| Hook | 触发时机 | 返回值 | 独特性 |
|------|---------|--------|--------|
| `tool` | 工具注册 | 工具定义 | 动态注册新工具 |
| **`tool.definition`** | 工具定义加载 | 修改后的定义 | **竞品唯一**——修改工具描述/参数 |
| `tool.execute.before` | 工具执行前 | 拦截/修改 | 类似 Claude Code 的 PreToolUse |
| `tool.execute.after` | 工具执行后 | 修改输出 | 类似 Claude Code 的 PostToolUse |

### LLM 通信 Hook

| Hook | 触发时机 | 返回值 | 用途 |
|------|---------|--------|------|
| `chat.message` | 消息生命周期 | 修改消息 | 消息预处理 |
| `chat.params` | LLM 参数构建 | 修改参数 | 调整 temperature/maxTokens |
| `chat.headers` | HTTP 请求头构建 | 自定义 headers | API 认证、追踪 |
| `experimental.chat.messages.transform` | 消息批量变换 | 修改消息列表 | 消息重排/过滤 |
| **`experimental.chat.system.transform`** | 系统提示构建 | 修改系统提示 | **竞品唯一**——插件可修改系统提示 |

### 其他 Hook

| Hook | 触发时机 | 用途 |
|------|---------|------|
| `permission.ask` | 权限请求 | 自定义权限决策 |
| `command.execute.before` | 命令执行前 | 命令拦截 |
| `shell.env` | Shell 环境变量 | 环境定制 |
| `experimental.session.compacting` | 会话压缩 | 注入上下文或替换压缩 prompt |
| `experimental.text.complete` | 文本补全 | 自定义补全逻辑 |

## 三、插件加载机制

### npm 插件

```bash
# 安装
opencode plugin install opencode-helicone-session

# 使用（自动加载）
# 插件在 config 中注册后，启动时通过 require() 加载
```

### 内置插件（6 个）

| 插件 | 功能 | 源码 |
|------|------|------|
| CodexAuth | GitHub Codex 认证 | 内置 |
| CopilotAuth | GitHub Copilot 认证 | 内置 |
| GitLab | GitLab Agent Platform 集成 | 内置 |
| Poe | Poe 平台认证 | 内置 |
| CloudflareWorkers | Cloudflare Workers AI | 内置 |
| CloudflareGateway | Cloudflare AI Gateway | 内置 |

### 加载顺序

```
启动 → 加载内置插件（6 个）
     → 加载 npm 外部插件
     → 顺序执行（非并行，确保确定性顺序）
     → 注册 Hook 回调
```

## 四、Qwen Code 改进建议

### P2：tool.definition Hook

允许插件修改内置工具的描述和参数——例如安全插件可以给 Bash 工具添加额外的参数约束，或 CI 插件可以修改 Write 工具的描述来提示 Agent 遵循项目规范。

### P2：experimental.chat.system.transform

允许插件修改系统提示——例如企业插件可以注入合规要求，或语言插件可以追加本地化指令。比 CLAUDE.md/QWEN.md 更灵活（代码级修改 vs 文件级追加）。

### P3：npm 插件分发

当前 Qwen Code 的扩展通过 extension 命令管理。OpenCode 的 npm 插件模式更符合 Node.js 生态习惯。
