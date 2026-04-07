# 3. 技术架构——开发者参考

> Gemini CLI 和 Qwen Code 共享同一个架构基础（fork 关系），但上游在 2025-10 之后做了大量改进：事件驱动调度器、模型路由器（7 种策略）、VirtualizedList、SlicingMaxSizedBox、自定义 Ink fork 等。
>
> **Qwen Code 对标**：核心循环（AgentSession → GeminiChat → Scheduler）与 Qwen Code 的 CoreToolScheduler 类似但更精细。上游新增的 SlicingMaxSizedBox、toolLayoutUtils、LRU 缓存是 P0-P1 backport 目标。

## 核心架构

```
CLI (Ink + React 19)
    │
    ▼
AgentSession (AsyncIterable 事件流, 会话编排)
    │
    ▼
GeminiClient → GeminiChat (@google/genai SDK, 流式, 主循环最多 100 轮)
    │
    ▼
Scheduler (事件驱动调度器)
    │  Validating → Scheduled → AwaitingApproval → Executing → Success/Error/Cancelled
    │
    ├── PolicyEngine (TOML 策略, 多源优先级: Runtime > Project > User > System > Extensions)
    │   ├── 通配符匹配（*、mcp_*、mcp_serverName_*）
    │   ├── 正则参数匹配（argsPattern）
    │   ├── 工具注解匹配（toolAnnotations: readOnlyHint 等）
    │   └── SafetyChecker（InProcess: allowed-path/conseca + External: 子进程）
    │
    ├── HookSystem (11 种 Hook 事件)
    │   ├── Command Hooks（外部子进程）
    │   ├── Runtime Hooks（TypeScript 函数）
    │   └── Hook 决策：ask / block / deny / approve / allow
    │
    ├── ToolExecutor (工具执行)
    │   ├── 23 内置工具（ToolRegistry）
    │   ├── MCP 动态工具（mcp_{server}_{tool} 命名）
    │   ├── Discovered 工具（discovered_tool_ 前缀）
    │   └── 排序：Built-in (0) > Discovered (1) > MCP (2)
    │
    ├── ModelRouter (模型路由, 7 种策略)
    │   ├── OverrideStrategy（显式模型请求）
    │   ├── FallbackStrategy（错误自动回退）
    │   ├── ApprovalModeStrategy（按审批模式选模型）
    │   ├── ClassifierStrategy（ML Gemma 分类器）
    │   ├── NumericalClassifierStrategy（数值评分）
    │   ├── CompositeStrategy（组合链式策略）
    │   └── DefaultStrategy（最终兜底）
    │
    └── AgentRegistry (5 内置代理 + 自定义代理)
        ├── generalist（通用，全工具访问，继承主模型，20 轮）
        ├── codebase_investigator（代码分析，只读工具，Flash 模型）
        ├── memory_manager（记忆管理，读写 GEMINI.md，Flash 模型）
        ├── cli_help（CLI 帮助，查询内部文档，10 轮/3 分钟）
        └── browser（浏览器自动化，Puppeteer MCP，域名限制）
```

## 技术栈

- **语言**：TypeScript（ES2022 target）
- **运行时**：Node.js ≥20.0.0
- **CLI 框架**：Ink 6.4 + React 19
- **API SDK**：@google/genai@1.30.0（Gemini 官方）
- **MCP SDK**：@modelcontextprotocol/sdk@^1.23.0（Stdio/SSE）
- **A2A SDK**：@a2a-js/sdk@0.3.11
- **策略格式**：TOML（@iarna/toml）
- **Schema 验证**：Zod@^3.25.76
- **遥测**：OpenTelemetry 全套（Traces + Metrics + Logs，OTLP/GCP 导出）
- **AST 解析**：web-tree-sitter@^0.25.10 + tree-sitter-bash@^0.25.0
- **浏览器自动化**：puppeteer-core@^24.0.0
- **终端模拟**：@xterm/headless@5.5.0 + @lydell/node-pty
- **凭证存储**：keytar@^7.9.0（系统 Keychain）
- **构建**：esbuild@^0.25.0
- **测试**：Vitest@^3.2.4
- **Lint**：ESLint 9.x（零警告策略）

## 模型路由器

```
请求 → OverrideStrategy（显式模型指定）
      → FallbackStrategy（错误自动回退）
      → ApprovalModeStrategy（按审批模式选型）
      → ClassifierStrategy（ML Gemma 分类器）
      → NumericalClassifierStrategy（数值评分路由）
      → CompositeStrategy（组合多策略链）
      → DefaultStrategy（最终兜底）
```

**路由决策结构**：
```typescript
{
  model: string           // 选中的模型 ID
  metadata: {
    source: string        // 决策来源策略名
    latencyMs: number     // 路由延迟
    reasoning: string     // 选择理由
    error?: string        // 错误信息（可选）
  }
}
```

## 配置系统

```
~/.gemini/                    # 全局配置
├── settings.json             # 全局设置
├── policies/                 # 全局策略目录（含 *.toml 文件，auto-saved.toml 为自动保存）
├── GEMINI.md                 # 全局记忆/系统提示
├── sessions/                 # 会话存储
├── history/                  # 检查点历史
├── skills/                   # 用户技能
├── agents/                   # 用户代理定义
└── extensions/               # 已安装扩展

.gemini/                      # 项目级配置
├── settings.json             # 项目设置
├── policies/                 # 项目策略目录（含 *.toml 文件）
├── GEMINI.md                 # 项目自定义系统提示
├── skills/                   # 项目技能
└── agents/                   # 项目代理定义

.geminiignore                 # 项目根目录，文件过滤（类 .gitignore）
```

**设置结构**：
```jsonc
// settings.json
{
  "auth": {
    "defaultAuth": "oauth-personal",
    "apiKey": "YOUR_GEMINI_API_KEY"
  },
  "model": "gemini-3-pro",
  "approvalMode": "default",  // default | autoEdit | yolo | plan
  "agents": {
    "overrides": {
      "generalist": { "model": "gemini-3-flash" }
    },
    "browser": { /* 浏览器代理自定义配置 */ }
  },
  "mcp": {
    "server-name": {
      "command": "npx",
      "args": ["-y", "mcp-server"],
      "env": {},
      "autoStart": true
    }
  },
  "hooks": {
    "BeforeTool": [{ "matcher": "...", "hooks": [...] }]
  },
  "telemetry": { /* OpenTelemetry 配置 */ },
  "accessibility": { /* 无障碍设置 */ },
  "plan": { /* 规划模式设置 */ },
  "extensions": [ /* 扩展列表 */ ],
  "general": {
    "checkpointing": { "enabled": true }
  }
}
```

**配置优先级**（从高到低）：
1. 远程管理员设置（Remote Admin）
2. CLI 标志 / 环境变量
3. 系统设置（平台系统配置路径，如 `/etc/gemini-cli/settings.json`）
4. 项目/工作区设置（`.gemini/settings.json`）
5. 用户设置（`~/.gemini/settings.json`）
6. 系统默认值（内置 Schema 默认值）
7. 扩展设置

## 沙箱系统

通过 `GEMINI_SANDBOX` 环境变量或 `--sandbox` 标志配置，支持 7 种沙箱后端：

| 后端 | 命令 | 平台 | 说明 |
|------|------|------|------|
| **macOS Seatbelt** | `sandbox-exec` | macOS | 6 种配置文件（permissive-open/proxied、restrictive-open/proxied、strict-open/proxied） |
| **Bubblewrap** | `bwrap` | Linux | 用户命名空间 + Seccomp 系统调用过滤，原生轻量隔离 |
| **Docker** | `docker` | 跨平台 | 容器化隔离 |
| **Podman** | `podman` | 跨平台 | 无 daemon 容器化隔离（Docker 替代） |
| **gVisor** | `runsc` | Linux | 用户空间内核级隔离（最强安全性） |
| **LXC** | `lxc` | Linux | 完整系统容器隔离 |
| **Windows Sandbox** | — | Windows | C# 集成，原生隔离 |

**沙箱权限**：
```typescript
{
  fileSystem: { read: string[], write: string[] }  // 文件系统读写路径
  network: boolean                                  // 网络访问
  allowedPaths: string[]                           // 允许的路径
  forbiddenPaths: string[]                         // 禁止的路径
}
```

- macOS 支持动态扩展沙箱和 Worktree
- 默认不启用沙箱（带红色警告），推荐在生产环境启用
- v0.24.0 起默认文件夹信任设为 untrusted

## 认证方式

| 方式 | 类型标识 | 说明 |
|------|----------|------|
| **Google OAuth** | `oauth-personal` | OAuth 2.0 设备码流程，Token 存储在系统 Keychain |
| **Gemini API Key** | `gemini-api-key` | `GEMINI_API_KEY` 环境变量，免费层 250 req/day |
| **Vertex AI** | `vertex-ai` | GCP 项目 + 区域，使用 ADC 凭证 |
| **计算默认凭证** | `compute-default-credentials` | 服务账号 JSON Key |
| **企业网关** | `gateway` | 企业级 API 网关 |
| **Cloud Shell** | `cloud-shell` | Legacy，已弃用 |

## 企业功能

- **Headless 模式**：CI/GitHub Actions 自动激活，支持脚本化工作流
- **多种沙箱**：Seatbelt / Bubblewrap / Docker / Podman / gVisor / LXC / Windows Sandbox
- **策略引擎**：项目级 TOML 策略文件，精细控制工具执行权限
- **可信文件夹**：按目录控制执行策略（v0.24.0+ 默认 untrusted）
- **Shell 命令白名单**：粒度化 Shell 命令许可（v0.24.0+）
- **遥测 & 监控**：OpenTelemetry GenAI 标准指标，OTLP/GCP 导出
- **Vertex AI 集成**：企业认证（ADC、服务账号）、SLA、区域数据驻留
- **Code Assist 许可**：Standard（1500 req/day）/ Enterprise（2000 req/day）层级
- **远程子代理**：A2A 协议 + HTTP 认证，跨服务代理通信
- **扩展系统**：企业可开发内部扩展，统一分发
- **安全扩展**：官方 `gemini-cli-extensions/security`，代码漏洞扫描（`/security:analyze`）

## 评估框架

25 个行为评估套件（`/evals/`）：

| 评估 | 用途 |
|------|------|
| automated-tool-use | 工具执行准确性 |
| generalist_agent | 通用代理能力 |
| generalist_delegation | 通用代理委派 |
| subagents | 子代理集成 |
| model_steering | 模型选择路由 |
| save_memory | 记忆持久化 |
| hierarchical_memory | 分层记忆 |
| tool_output_masking | 输出保护 |
| validation_fidelity | Schema 验证 |
| validation_fidelity_pre_existing_errors | 已有错误下的验证 |
| grep_search_functionality | 搜索工具 |
| ask_user | 用户交互 |
| cli_help_delegation | 命令帮助 |
| answer-vs-act | 响应类型选择 |
| interactive-hang | 挂起预防 |
| concurrency-safety | 并行安全 |
| plan_mode | 规划模式 |
| edit-locations-eval | 编辑位置准确性 |
| shell-efficiency | Shell 效率 |
| frugalReads | 读取节约 |
| frugalSearch | 搜索节约 |
| gitRepo | Git 仓库操作 |
| sandbox_recovery | 沙箱恢复 |
| tracker | 任务追踪 |
| redundant_casts | 冗余转换检测 |

集成测试支持三种沙箱模式：无沙箱、Docker、Podman。
