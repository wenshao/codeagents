# Gemini CLI

**开发者：** Google
**许可证：** Apache-2.0
**仓库：** [github.com/google-gemini/gemini-cli](https://github.com/google-gemini/gemini-cli)
**文档：** [geminicli.com](https://geminicli.com)
**Stars：** 约 1k+

## 概述

Gemini CLI 是 Google 官方的 AI 编程代理，运行在终端中。基于 TypeScript + Ink/React 构建，采用 ReAct 模式驱动代理循环。它是 Qwen Code 的上游项目，其架构被广泛借鉴。整体代码量约 19 万行 TypeScript。

## 核心功能

### 基础能力
- **ReAct 代理循环**：推理 + 行动模式，最多 100 轮对话
- **27+ 内置工具**：文件读写、编辑、Bash 执行、Grep 搜索、Web 抓取等
- **MCP 支持**：完整的模型上下文协议（Stdio/SSE/HTTP 传输）
- **事件驱动调度器**：并发工具调用，状态机管理生命周期
- **TOML 策略引擎**：灵活的权限控制，支持通配符和正则匹配
- **流式输出**：实时显示 LLM 推理和工具执行结果
- **会话管理**：UUID 会话、压缩、恢复

### 独特功能
- **策略引擎（Policy Engine）**：TOML 格式的策略文件，支持 NONE/PROMPT/SAFE/SELECTIVE 四种审批模式
- **安全检查器**：可外挂进程级安全检查，带超时控制
- **模型路由器**：可插拔路由策略（Fallback、Override、Classifier 等），动态模型选择
- **思维链显示**：Gemini 2+ 模型的 `<thought>` 部分可见但不回传
- **A2A 服务器**：实验性 Agent-to-Agent 协议支持
- **Qwen Code 上游**：其架构被阿里云 Qwen Code 分叉和扩展

## 技术架构（源码分析）

### Monorepo 结构

```
gemini-cli/
├── packages/cli/        # 终端 UI（Ink + React 19）
├── packages/core/       # 核心引擎（代理、工具、策略）
├── packages/sdk/        # 公共 SDK（编程式使用）
├── packages/a2a-server/ # Agent-to-Agent 实验协议
├── packages/devtools/   # 开发工具
├── packages/vscode-ide-companion/  # VS Code 扩展
└── packages/test-utils/ # 测试工具
```

### 核心架构

```
CLI (Ink + React 19)
    │
    ▼
GeminiClient (会话编排, 100 轮上限)
    │
    ▼
GeminiChat (@google/genai SDK, 流式)
    │
    ▼
Scheduler (事件驱动调度器)
    │  Scheduled → Validating → Waiting → Executing → Success/Error
    │
    ├── PolicyEngine (TOML 策略)
    │   ├── 通配符匹配（*、server__*）
    │   ├── 正则参数匹配
    │   └── SafetyChecker（外挂进程）
    │
    ├── ToolExecutor (工具执行)
    │   └── 27+ 内置工具 + MCP 动态工具
    │
    └── ModelRouter (模型路由)
        ├── FallbackStrategy
        ├── OverrideStrategy
        └── ClassifierStrategy
```

### 技术栈
- **语言**：TypeScript（ES2022 target）
- **运行时**：Node.js
- **CLI 框架**：Ink + React 19
- **API SDK**：@google/genai（Gemini 官方）
- **MCP SDK**：@modelcontextprotocol/sdk
- **策略格式**：TOML（Policy 文件）
- **遥测**：OpenTelemetry
- **AST 解析**：web-tree-sitter

### 内置工具

| 类别 | 工具 |
|------|------|
| 文件操作 | read-file, write-file, edit, ls, glob |
| 搜索 | grep, ripGrep, web-search |
| 执行 | shell |
| 网络 | web-fetch |
| 记忆 | memory（持久会话状态） |
| 交互 | ask-user |
| 规划 | enter-plan-mode, exit-plan-mode |
| 任务 | write-todos, activate-skill |

### 策略/权限系统

```toml
# .gemini/policy.toml
[[rules]]
tool = "shell"
action = "ask"

[[rules]]
tool = "read-file"
action = "allow"

[[rules]]
tool = "*"
approval_modes = ["safe"]
action = "deny"
```

四种审批模式：
- **NONE**：自动批准所有工具
- **PROMPT**：每个工具调用都询问用户
- **SAFE**：安全检查器 + 用户确认
- **SELECTIVE**：仅特定工具需要审批

### 认证方式

| 方式 | 说明 |
|------|------|
| LOGIN_WITH_GOOGLE | OAuth 个人登录 |
| USE_GEMINI | API Key（gemini.google.com） |
| USE_VERTEX_AI | GCP 项目 + 区域 |
| COMPUTE_ADC | 计算默认凭证 |

## 安装

```bash
# npm
npm install -g @google/gemini-cli

# 启动（首次会引导认证）
gemini
```

## 优势

1. **Google 官方**：第一方支持，与 Gemini 模型深度集成
2. **架构优雅**：事件驱动调度器 + 声明式工具 + 可插拔策略引擎
3. **策略系统强大**：TOML 策略文件 + 外挂安全检查器 + 四种审批模式
4. **模型路由**：可插拔策略，支持 Fallback、Classifier 等多种路由方式
5. **开源**：Apache-2.0 许可，代码质量高
6. **生态影响力大**：Qwen Code 基于此分叉

## 劣势

1. **单模型锁定**：仅支持 Gemini 系列模型
2. **较小社区**：比 Claude Code/Aider 用户少
3. **文档不够丰富**：相比实际代码能力，文档覆盖不足
4. **功能迭代快**：API 和功能变化较快，文档可能滞后

## CLI 命令

```bash
# 启动交互式会话
gemini

# 非交互模式
gemini -p "解释这段代码"

# 恢复会话
gemini --resume <session-id>

# 斜杠命令（会话内）
/memory          # 查看/管理记忆
/settings        # 修改设置
/hooks           # 管理 Hook
@tools           # 查看可用工具
```

## 配置

```
~/.gemini/
├── settings.toml     # 全局设置
├── policy.toml       # 全局策略
├── sessions/         # 会话存储
├── memory/           # 持久记忆
└── skills/           # 用户技能

.gemini/              # 项目级
├── settings.toml
├── policy.toml
├── GEMINI.md         # 项目自定义系统提示
└── skills/
```

## 使用场景

- **最适合**：Google Cloud 用户、Gemini 模型使用者
- **适合**：需要策略引擎精细控制的安全敏感场景
- **不太适合**：需要多模型切换、非 Google 生态用户

## 与 Qwen Code 的关系

Qwen Code 是 Gemini CLI 的分叉项目，继承了：
- 代理循环架构（GeminiClient + Scheduler）
- 工具系统（声明式工具 + 注册表）
- 策略/权限模型
- Ink + React 终端 UI
- MCP 集成
- 会话管理

Qwen Code 在此基础上增加了：多提供商支持、免费 OAuth、6 语言国际化、多代理终端等。

## 资源链接

- [GitHub](https://github.com/google-gemini/gemini-cli)
- [官网](https://geminicli.com)
- [安装指南](https://geminicli.com/docs/get-started/installation/)
