# 16. 构建自己的 AI 编程 Agent：框架选型指南

> 基于 17 款 Agent 的源码分析经验，帮你选择正确的构建路径——从零搭建 vs 基于成品扩展。

## 三种路径

### 路径 A：基于 SDK 框架从零搭建

**代表框架**：[AgentScope](https://github.com/agentscope-ai/agentscope)（阿里）、[LangGraph](https://github.com/langchain-ai/langgraph)（LangChain）、[CrewAI](https://github.com/crewAIInc/crewAI)、[AG2](https://github.com/ag2ai/ag2)（原 AutoGen 社区分叉）、[Microsoft Agent Framework](https://learn.microsoft.com/en-us/agent-framework/)（AutoGen 官方继任者）

```
你的代码
  ├── 代理循环（ReAct / 工具调用 / 自定义）
  ├── 工具注册（文件编辑 / Bash / 搜索 / Web）
  ├── 安全系统（权限 / 沙箱 / 审批）
  ├── 上下文管理（压缩 / 缓存 / Token 控制）
  ├── 终端 UI（输入 / 输出 / 交互）
  └── 存储（会话 / 记忆 / 配置）
```

### 路径 B：基于成品 Agent 扩展

**代表 Agent**：QwenCode、Claude Code、Gemini CLI、OpenCode

```
成品 Agent（数万行成熟代码）
  ├── SKILL.md          ← 你写：定义业务逻辑（几十行）
  ├── Hooks             ← 你写：拦截/增强行为（脚本）
  ├── MCP 服务器         ← 你写：接入私有工具（API）
  ├── AGENTS.md         ← 你写：注入项目上下文
  └── 扩展/插件          ← 你写：打包分发
```

### 核心对比

| 维度 | SDK 框架（AgentScope 等） | 成品 Agent（QwenCode 等） |
|------|------------------------|--------------------------|
| **本质** | 构建积木，你造房子 | 住进房子，你装修 |
| **代码量** | 数千~万行 Agent 逻辑 | 几十行 SKILL.md + 配置 |
| **上手时间** | 周~月 | 小时~天 |
| **灵活性** | 完全自定义 | 受限于宿主架构 |
| **维护成本** | 高（自维护全栈） | 低（社区/厂商维护） |
| **安全基础设施** | 需自建 | 继承（沙箱 / BLOCK 规则 / 策略引擎） |
| **编辑工具** | 需自建 | 继承（Edit / Write / MultiEdit / apply_patch） |
| **上下文压缩** | 需自建 | 继承（三层/四阶段/递归分割） |
| **Git 集成** | 需自建 | 继承（checkpoint / rewind / worktree） |
| **MCP 生态** | 需自接 | 内置支持 |

> **Anthropic 的 Harness 洞察**（[来源](https://www.anthropic.com/engineering/harness-design-long-running-apps)）："The space of interesting harness combinations doesn't shrink as models improve. Instead, it moves."——**Harness 的价值不会随模型进步消失，只会迁移**。今天需要的 Sprint 分解，明天可能不再需要；但新的 Harness 组件（如 Evaluator 校准、Context Anxiety 管理）会出现。选择"路径 B 成品扩展"不意味着不需要 Harness 思维——而是用 SKILL.md + Hooks 实现轻量级 Harness。

---

## 选择决策树

```
你要做什么类型的 Agent？
  │
  ├── 编码辅助 Agent（代码生成/审查/重构/测试）
  │   └── → 选路径 B（成品 Agent 扩展）
  │       │
  │       ├── 需要开源可控？ → QwenCode
  │       ├── 需要最强推理？ → Claude Code
  │       ├── 需要模型路由？ → Gemini CLI
  │       └── 需要多客户端？ → OpenCode
  │
  ├── 非编码 Agent（客服/数据分析/业务自动化）
  │   └── → 选路径 A（SDK 框架）
  │       │
  │       ├── Python 生态？ → AgentScope / LangGraph
  │       ├── 多 Agent 编排？ → CrewAI / AG2
  │       ├── 微软生态/企业？ → Microsoft Agent Framework
  │       └── 自训练模型？ → AgentScope（灵活接入）
  │
  ├── 程序化嵌入 Agent 到自己的应用
  │   └── → 选路径 C（Agent SDK）
  │       ├── Claude 生态？ → @anthropic-ai/claude-agent-sdk
  │       └── OpenAI 生态？ → @openai/codex-sdk
  │
  └── 编码 + 非编码混合
      └── → 路径 B 为主 + MCP 桥接非编码能力
```

---

## 路径 B 详解：基于成品 Agent 的 4 层扩展

### 第 1 层：SKILL.md（最简单，5 分钟上手）

**跨 Agent 兼容版**（所有 Agent 都能用）：

```markdown
---
name: security-scan
description: 扫描项目中的安全漏洞
---

分析当前项目的安全风险：

1. 使用 Grep 搜索硬编码密钥（API key、password、secret）
2. 检查依赖中的已知漏洞（package.json / requirements.txt）
3. 检查 SQL 注入风险（字符串拼接 SQL）
4. 检查 XSS 风险（未转义的用户输入）

输出：Markdown 表格，按严重程度排序。
不要修改任何文件。
```

**Claude Code 增强版**（仅 Claude Code 支持的高级字段）：

```yaml
---
name: security-scan
description: 扫描项目中的安全漏洞
allowed-tools: ["Read", "Grep", "Glob"]   # ← Claude Code 独有
context: fork                              # ← Claude Code 独有：独立上下文
paths: ["*.py", "*.js", "*.ts"]            # ← Claude Code 独有：条件激活
model: haiku                               # ← Claude Code 独有：模型覆盖
---
```

放到 `.claude/skills/security-scan/SKILL.md` 或 `.qwen/skills/security-scan/SKILL.md`，通过 `/security-scan` 调用。

> **跨 Agent 兼容要点**：
> - **YAML frontmatter**：Claude Code 可选，其他所有 Agent **必须**
> - **`name` + `description`**：Claude Code 可选，其他 Agent **必须**
> - **`allowed-tools` / `context` / `paths` / `model`**：**仅 Claude Code 支持**，其他 Agent 会忽略或报错
> - 安全做法：始终加 YAML frontmatter + name + description，仅在 Claude Code 环境下加高级字段

### 第 2 层：Hooks（拦截和增强行为）

```json
// settings.json
{
  "hooks": {
    "PreToolUse": [{
      "matcher": "Bash",
      "hook": {
        "type": "command",
        "command": "python3 /path/to/validate-command.py"
      }
    }],
    "PostToolUse": [{
      "matcher": "Edit",
      "hook": {
        "type": "command",
        "command": "node /path/to/auto-format.js"
      }
    }]
  }
}
```

Hook 在**框架层面**运行（不依赖模型），适合：
- 自动格式化（编辑后触发 prettier/ruff）
- 安全检查（命令执行前验证）
- 审计日志（记录所有工具调用）
- 工作流自动化（任务完成后触发 CI）

各 Agent Hook 事件数：Claude Code **24 个**、Qwen Code **12 个**、Gemini CLI **11 个**。

### 第 3 层：MCP 服务器（接入私有工具）

```json
// .mcp.json
{
  "mcpServers": {
    "internal-api": {
      "command": "node",
      "args": ["./mcp-servers/internal-api.js"],
      "env": {
        "API_BASE_URL": "https://internal.company.com/api"
      }
    },
    "database": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-postgres"],
      "env": {
        "POSTGRES_CONNECTION_STRING": "postgresql://..."
      }
    }
  }
}
```

MCP 让 Agent 调用**任何外部工具**——数据库查询、内部 API、监控系统、CI/CD 管道。8/10 个 Agent 支持 MCP。

### 第 4 层：插件/扩展（打包分发）

Claude Code 插件结构：
```
my-plugin/
├── plugin.json          # 元数据
├── skills/
│   └── my-skill/
│       └── SKILL.md     # 业务逻辑
├── hooks/
│   └── auto-format.js   # Hook 脚本
└── agents/
    └── reviewer.md      # 自定义代理
```

通过 Marketplace 分发给团队。Qwen Code 通过 `/extensions` 管理，可自动转换 Claude/Gemini 扩展格式。

---

## 各成品 Agent 扩展能力对比

| 能力 | Claude Code | Qwen Code | Gemini CLI | OpenCode | Codex CLI |
|------|------------|-----------|-----------|----------|-----------|
| **SKILL.md** | ✓（YAML 可选） | ✓（YAML 必须） | ✓（YAML 必须） | ✓（YAML 必须） | ✓（YAML 必须） |
| **Hooks** | **24 事件** + Prompt Hook | 12 事件 | 11 事件 | 17 种 Hook | user prompt hook |
| **MCP** | Stdio/SSE/Streamable-HTTP | Stdio/SSE/HTTP | Stdio/SSE | StreamableHTTP/SSE/Stdio | ✓（config.toml，20 处引用） |
| **插件系统** | 13 官方 + Marketplace | `/extensions` + 格式转换 | 扩展系统 | Hook-based | plugins 配置 |
| **记忆系统** | auto-memory（4 类型） | save_memory 工具 | memory_manager 子代理 | ✗ | generate_memories |
| **多代理** | Teammates（协作） | Arena（竞争） | 5 子代理 + A2A | — | — |
| **CI/脚本** | `--bare` + stream-json | `--non-interactive` | TTY 自动检测 | — | 5 级审批 |
| **开源** | ✗（专有） | **✓ Apache-2.0** | **✓ Apache-2.0** | **✓ MIT** | **✓ Apache-2.0** |

---

## 推荐：基于 QwenCode 构建编码 Agent

QwenCode 是中文场景下的最优基座选择：

**为什么选 QwenCode？**

1. **完全开源**（Apache-2.0）——可审计、可修改、可分发
2. **6+ 提供商**——不锁定单一模型，可接入 Qwen/Claude/GPT/Gemini
3. **免费 OAuth**——1000 次/天，零成本启动
4. **AGENTS.md 原生支持**（v0.13.0+）——跨 Agent 兼容
5. **Arena 模式**——多模型竞争选优，独特差异化
6. **Gemini CLI 分叉**——继承成熟的策略引擎、压缩算法、MCP 集成

**快速开始**：

```bash
# 1. 安装
npm i -g @qwen-code/qwen-code

# 2. 创建项目指令
cat > AGENTS.md << 'EOF'
# Project: my-project
## Development
- Test: npm test
- Lint: npm run lint
## Restrictions
- 不要修改 migrations/
EOF

# 3. 创建自定义 Skill
mkdir -p .qwen/skills/deploy-check
cat > .qwen/skills/deploy-check/SKILL.md << 'EOF'
---
name: deploy-check
description: 部署前检查清单
---
检查以下部署前置条件：
1. 所有测试通过
2. 无 lint 错误
3. 无硬编码密钥
4. CHANGELOG 已更新
EOF

# 4. 使用
qwen
> /deploy-check
```

---

## 什么时候选 AgentScope？

| 场景 | 为什么不用成品 Agent | 为什么用 AgentScope |
|------|-------------------|-------------------|
| **客服/销售 Agent** | 成品 Agent 专为编码设计 | 需要对话管理、知识库、多轮意图 |
| **数据分析 Agent** | 编码 Agent 的工具不适合 | 需要 pandas/SQL/可视化工具 |
| **自定义多 Agent 拓扑** | Teammates/Arena 是固定模式 | 需要星形/链式/层级拓扑 |
| **自训练小模型** | 成品 Agent 对小模型支持有限 | AgentScope 灵活接入任何模型（含本地推理） |
| **纯 Web/移动环境** | 多数成品 Agent 以终端为主（OpenCode/Kimi 有 Web UI） | 需要完全自定义的 Web/移动界面 |

---

## 混合架构：成品 Agent + MCP 桥接

如果你同时需要编码能力和非编码能力，**不需要二选一**：

```
QwenCode / Claude Code（编码 Agent 基座）
  │
  ├── SKILL.md（编码业务逻辑）
  │
  └── MCP 服务器（桥接非编码能力）
      ├── mcp-server-database（SQL 查询）
      ├── mcp-server-jira（项目管理）
      ├── mcp-server-slack（团队通知）
      ├── mcp-server-grafana（监控数据）
      └── mcp-server-custom（自定义业务逻辑）
```

MCP 协议让编码 Agent 可以调用**任何外部工具**，无需修改 Agent 核心代码。

---

## 路径 C：Agent SDK（程序化集成）

除了 SKILL.md 扩展和 SDK 框架，还有一种介于两者之间的方式——**Agent SDK**，在自己的应用中程序化嵌入 Agent 能力。

### Claude Agent SDK

> 包名：`@anthropic-ai/claude-agent-sdk`（[npm](https://www.npmjs.com/package/@anthropic-ai/claude-agent-sdk)、[官方文档](https://platform.claude.com/docs/en/agent-sdk/overview)）

> **注**：以下 TypeScript 示例基于 npm 包导出推断（官方文档目前仅提供 Python 示例），实际 API 可能有差异，使用前请查阅最新官方文档。

```bash
npm install @anthropic-ai/claude-agent-sdk
```

```typescript
import { query, ClaudeAgentOptions } from '@anthropic-ai/claude-agent-sdk';

const options = ClaudeAgentOptions({
  allowed_tools: ["Read", "Edit", "Glob", "Bash"],
  permission_mode: "acceptEdits",
  system_prompt: "你是部署检查助手"
});

// query() 返回 AsyncGenerator，逐步输出结果
for await (const message of query({ prompt: "检查所有服务是否健康", options })) {
  if (message.type === "text") {
    console.log(message.content);
  }
}
```

### Codex Agent SDK

> 包名：`@openai/codex-sdk`（[npm](https://www.npmjs.com/package/@openai/codex-sdk)、[官方文档](https://developers.openai.com/codex/sdk)）

```bash
npm install @openai/codex-sdk
```

```typescript
import { Codex } from "@openai/codex-sdk";

const codex = new Codex({
  apiKey: process.env.OPENAI_API_KEY,
});

// 创建会话线程
const thread = codex.startThread();

// run() 返回单轮结果
const turn = await thread.run("诊断测试失败并提出修复方案");
console.log(turn.finalResponse);

// 同一 Thread 可多轮对话
const nextTurn = await thread.run("实施修复");

// runStreamed() 返回流式事件（工具调用、文件变更等）
for await (const event of thread.runStreamed("运行测试验证")) {
  console.log(event.type, event.data);
}
```

### 适用场景

- 在 Node.js/Python 应用中嵌入 Agent 能力（非终端交互）
- 构建 Web 应用、API 服务、CI 管道中的 Agent 节点
- 需要程序化控制工具权限和输出流

### 与其他路径的区别

| 维度 | SKILL.md 扩展 | Agent SDK | SDK 框架 |
|------|-------------|-----------|---------|
| 代码量 | 几十行 Markdown | 几百行 TS/Python | 几千行 |
| 运行环境 | 终端内 | 任何 Node.js/Python 环境 | 任何环境 |
| 模型限制 | 宿主 Agent 支持的模型 | 对应厂商模型 | 任何模型 |
| 基础设施 | 继承宿主全部 | 继承 Agent 工具集 | 需自建 |
| 代表 SDK | — | `@anthropic-ai/claude-agent-sdk`、`@openai/codex-sdk` | AgentScope、LangGraph |

---

## 工具设计原则（来源：[Anthropic Engineering Blog](https://www.anthropic.com/engineering/writing-tools-for-agents)）

无论选择哪条路径，工具设计都是 Agent 质量的关键。Anthropic 总结了以下经验：

### 合并优于增殖

> "More tools don't always lead to better outcomes."

> "Too many tools or overlapping tools can also distract agents from pursuing efficient strategies."

**反面案例**：为每个 API 端点创建独立工具（`list_users`、`list_events`、`create_event`）。

**推荐做法**：合并为任务导向的高阶工具（`schedule_event` 一个工具封装多个 API 调用）。

```
✗ 工具增殖（7 个低阶工具）          ✓ 工具合并（2 个高阶工具）
├── get_customer_by_id              ├── get_customer_context
├── list_transactions               │   └── 内部调用 3 个 API
├── list_notes                      └── search_logs
├── read_logs                           └── 内部过滤+分页
├── filter_logs
├── get_customer_details
└── get_customer_history
```

### 命名空间策略

> "For example, namespacing tools by service (e.g., `asana_search`, `jira_search`) and by resource (e.g., `asana_projects_search`, `asana_users_search`), can help agents select the right tools at the right time."

**命名前缀 vs 后缀的选择会影响模型性能**：

> "We have found selecting between prefix- and suffix-based namespacing to have non-trivial effects on our tool-use evaluations."

| 命名方式 | 示例 | 适用场景 |
|---------|------|---------|
| 服务前缀 | `github_create_issue` | 同一服务多操作 |
| 资源前缀 | `issues_create`、`issues_list` | 围绕资源 CRUD |
| 动作前缀 | `search_github`、`search_jira` | 跨服务同类操作 |

### 描述即 Prompt 工程

工具描述的微小改动会导致 Agent 行为的显著变化：

- 返回**高信号语义信息**（项目名称），而非低信号技术标识（UUID）
- 实现分页、过滤和截断，附带有意义的错误消息
- 用 2-3 个代表性示例替代穷举所有边界情况

### 对 SKILL.md / MCP 设计的实际指导

| 场景 | 工具增殖 | 工具合并 |
|------|---------|---------|
| MCP 服务器设计 | 每个 API 端点一个 MCP 工具 | 按任务合并，一个工具封装多步 |
| SKILL.md 设计 | 每个子任务一个 Skill | 一个 Skill 编排完整工作流 |
| Hook 设计 | 每个检查一个 Hook | 一个 Hook 脚本执行多项检查 |

> **与 MCP 的关系**：Anthropic 指出 "The Model Context Protocol (MCP) can empower LLM agents with potentially hundreds of tools to solve real-world tasks."——但工具数量多不等于质量高。合并和命名空间策略对 MCP 工具同样适用。关于 MCP 命名约定（双下划线 vs 单下划线）对各 Agent 工具选择的具体影响，参见 [MCP 集成深度对比](../comparison/mcp-integration-deep-dive.md)中的「MCP 命名约定与模型工具选择」章节。

---

## 相关资源

### 扩展开发
- [Skill 设计指南](./skill-design.md) — SKILL.md 编写 + Frontmatter 差异 + 跨 Agent 迁移
- [Hooks 配置指南](./hooks-config.md) — Claude Code 24 事件 + Prompt Hook
- [AGENTS.md 配置指南](./agents-md.md) — 项目指令 + 符号链接策略

### 架构理解
- [架构深度对比](../comparison/architecture-deep-dive.md) — 10 Agent 代理循环 + Mermaid 图
- [Skill/技能系统深度对比](../comparison/skill-system-deep-dive.md) — Frontmatter 加载策略差异
- [Hook/插件/扩展系统对比](../comparison/hook-plugin-extension-deep-dive.md) — 24 事件 vs 17 Hook 类型
- [MCP 集成实现对比](../comparison/mcp-integration-deep-dive.md) — MCP 原生 vs TOML 策略

### Agent 详情
- [QwenCode 概述](../tools/qwen-code.md) — 40 命令 + Arena + 6+ 提供商
- [Claude Code 概述](../tools/claude-code/01-overview.md) — 79 命令 + 24 Hook + Channels
- [Gemini CLI 概述](../tools/gemini-cli/01-overview.md) — 8 策略路由 + A2A 远程
- [OpenCode 概述](../tools/opencode/01-overview.md) — 多客户端 + 37 LSP
