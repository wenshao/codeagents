# 14. MCP 集成——开发者参考

> MCP (Model Context Protocol) 是 Code Agent 连接外部工具和数据源的通用协议。Claude Code 的 MCP 实现是三个主要 Agent 中最完整的——23 个文件、~12,000 行、6 种传输类型、OAuth + XAA 认证、Channel 消息推送。
>
> **Qwen Code 对标**：Qwen Code 已有 MCP 基础实现（~4,300 行），包括 OAuth token 存储抽象和 Google 认证。差距主要在 Channel 消息推送、资源订阅、断线重连策略。

## 一、为什么 MCP 集成是 Agent 的关键基础设施

### 问题定义

Code Agent 的内置工具（Read/Write/Edit/Bash）覆盖了核心编程操作，但开发者的工作流远不止这些：

| 需求 | 内置工具能做？ | 需要 MCP？ |
|------|-------------|-----------|
| 读写本地文件 | ✓ | — |
| 执行 shell 命令 | ✓ | — |
| 查询 Jira/Linear 任务 | — | ✓ |
| 发 Slack 消息通知团队 | — | ✓ |
| 操作 Docker 容器 | — | ✓ |
| 查询数据库 | — | ✓ |
| 访问 GitHub API | — | ✓ |

MCP 让 Agent 的能力从"本地文件系统"扩展到"任意外部系统"，而不需要为每个系统写内置工具。

### 架构核心：工具命名空间

MCP 工具以 `mcp__<serverName>__<toolName>` 格式注册，与内置工具共享同一个工具注册表：

```
Agent 可用工具：
├─ Read           (内置)
├─ Write          (内置)
├─ Bash           (内置)
├─ mcp__github__get_issue       (MCP: GitHub server)
├─ mcp__github__create_pr       (MCP: GitHub server)
├─ mcp__slack__send_message     (MCP: Slack server)
└─ mcp__postgres__run_query     (MCP: PostgreSQL server)
```

对模型来说，MCP 工具和内置工具没有区别——都是可调用的函数。

## 二、三个 Agent 的 MCP 实现对比

| 维度 | Claude Code | Gemini CLI | Qwen Code |
|------|-------------|-----------|-----------|
| **文件数 / LOC** | 23 文件 / ~12,000 行 | 4 文件 / ~8,400 行 | 21 文件 / ~4,300 行 |
| **传输类型** | 6 种（stdio/sse/http/ws/sdk/sse-ide） | 3 种（stdio/sse/streamableHttp） | 3 种（stdio/sse/streamableHttp） |
| **OAuth** | ✓ + XAA（跨应用认证） | ✓ + Google 认证 | ✓ + Google 认证 + 文件加密存储 |
| **资源 (Resources)** | ✓ 支持订阅 | ✓ 支持 listChanged | — |
| **Prompt (MCP Prompts)** | ✓ 支持 listChanged | ✓ 支持 listChanged | — |
| **进度追踪** | ✓ MCPProgress | ✓ McpProgressReporter | ✓ onprogress 回调 |
| **Channel 消息** | ✓ 完整实现（7 层门控） | — | — |
| **断线重连** | ✓ 缓存清除 + 会话恢复 | — | — |
| **配置格式** | `.mcp.json`（7 种 scope） | mcp-config.json | mcp 配置 |
| **特殊传输** | SdkControlTransport（进程内） | XcodeMcpBridgeFixTransport | SdkControlClientTransport |

### Claude Code 独有能力

**1. Channel 消息推送**：MCP 服务器可以通过 `notifications/claude/channel` 方法向 Agent 会话推送消息（如 Slack 新消息、GitHub PR 评论）。有 7 层门控确保安全：

```
Channel 启用条件（全部满足才激活）：
1. 服务器声明 capabilities.experimental['claude/channel']
2. 运行时 isChannelsEnabled()
3. Claude.ai OAuth 认证（API key 用户不支持）
4. 组织策略 channelsEnabled: true
5. --channels 启动参数包含该服务器
6. Marketplace 来源验证
7. 审批 allowlist
```

**2. XAA（跨应用认证）**：基于 IETF draft Identity Assertion Authorization Grant 的企业级认证，支持 IdP → JWT → Token Exchange 链路。

**3. 6 种传输**：除标准 3 种外，还有 WebSocket（ws）、进程内 SDK（sdk）、IDE 专用 SSE（sse-ide）。

### Qwen Code 独有优势

**Token 存储抽象**：Qwen Code 有最完善的 token 持久化层——FileTokenStorage（AES-256-GCM 加密）、KeychainTokenStorage、HybridTokenStorage 三种实现。Claude Code 和 Gemini CLI 的 token 存储相对简单。

## 三、MCP 配置格式

### Claude Code 的 `.mcp.json`

```json
{
  "mcpServers": {
    "github": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": { "GITHUB_TOKEN": "ghp_..." }
    },
    "slack": {
      "type": "sse",
      "url": "https://mcp.slack.com/sse",
      "oauth": {
        "clientId": "...",
        "callbackPort": 8080,
        "authServerMetadataUrl": "https://slack.com/.well-known/openid-configuration"
      }
    },
    "database": {
      "type": "http",
      "url": "https://db-mcp.internal/api",
      "headers": { "Authorization": "Bearer $DB_TOKEN" }
    }
  }
}
```

**7 种配置作用域**：local → user → project → dynamic → enterprise → claudeai → managed

### 与 Qwen Code/Gemini CLI 的配置差异

| 特性 | Claude Code | Gemini CLI | Qwen Code |
|------|-------------|-----------|-----------|
| 配置文件 | `.mcp.json` | `mcp-config.json` 或 settings | settings.json 中 |
| 作用域 | 7 种 | 3 种（user/project/extension） | 2 种（user/project） |
| 环境变量 | `$VAR` 语法 | env 字段 | env 字段 |
| OAuth 内联 | ✓ | ✓ | ✓ |
| 企业管控 | ✓ managed-mcp.json | ✓ admin policy | — |

## 四、工具注册与执行

### 注册流程

```
MCP 服务器连接
  │
  ├─ transport.connect()        ← 建立通信通道
  │
  ├─ client.initialize()        ← 协商 capabilities
  │
  ├─ tools/list                 ← 获取工具列表
  │     └─ 每个工具 → mcp__server__tool 格式注册
  │
  ├─ prompts/list              ← 获取 prompt 列表（可选）
  │
  ├─ resources/list            ← 获取资源列表（可选）
  │
  └─ 监听 listChanged 通知     ← 工具/资源动态更新
```

### 执行流程

```
模型调用 mcp__github__get_issue({"number": 42})
  │
  ├─ 验证输入（JSON Schema / AJV）
  │
  ├─ client.callTool("get_issue", {"number": 42})
  │     ├─ OAuth 401 → 触发认证流程 → 重试
  │     ├─ 会话过期（404 -32001）→ 重连 → 重试
  │     └─ 成功 → 返回结果
  │
  ├─ 转换结果（text/image/PDF）
  │
  ├─ 截断检查（>8KB → 截断 + 提示）
  │
  └─ 返回给模型
```

## 五、断线重连策略

Claude Code 的重连策略：

| 错误类型 | 检测方式 | 恢复动作 |
|---------|---------|---------|
| 会话过期 | HTTP 404 + JSON-RPC -32001 | 清除 memoization 缓存 + 下次操作自动重连 |
| SSE 连接中断 | SDK 默认：2 次重试 | 指数退避重连 |
| 连续失败 | 失败计数器 | 关闭 transport + 触发显式重连 |
| OAuth token 过期 | 401 响应 | 自动 refresh → 重试原始请求 |

**与 Gemini CLI 的差异**：Gemini CLI 有 `MCP Auto-Reconnect`（连续 3 次错误自动重连），Claude Code 的重连更精细（区分会话过期 vs 连接中断 vs 认证过期）。

## 六、Qwen Code MCP 改进建议

### P1：资源 (Resources) 支持

MCP 资源允许服务器暴露结构化数据（如数据库 schema、API 文档），Agent 可以按需读取。当前 Qwen Code 仅支持工具调用，不支持资源发现和读取。

### P1：断线重连

当前 MCP 服务器断开后需要手动重启。建议参考 Claude Code 的 memoization 缓存清除 + 自动重连模式。

### P2：MCP Prompt 支持

MCP 服务器可以暴露 prompt 模板（如"总结这个 PR"），作为斜杠命令注册。当前 Qwen Code 不支持 MCP prompts。

### P2：Channel 消息推送

允许 MCP 服务器向 Agent 会话推送消息——这是实现 Slack/Discord 集成的基础。但实现复杂度高（7 层门控），建议作为中长期目标。

### P3：WebSocket 传输

当前仅支持 stdio/sse/http。WebSocket 在需要双向实时通信的场景（如实时协作工具）更高效。
