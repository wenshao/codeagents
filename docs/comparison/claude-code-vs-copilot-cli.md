# Claude Code vs Copilot CLI：终端代理双雄对比

> Claude Code（Anthropic 官方终端代理）vs GitHub Copilot CLI（GitHub 原生终端代理）——两大平台级终端 AI 编程助手的全面对比。Claude Code 以深度代理能力见长，Copilot CLI 凭借 GitHub 生态一体化取胜。

## 定位对比

| 维度 | Claude Code | GitHub Copilot CLI |
|------|------------|-------------------|
| **开发者** | Anthropic | GitHub（Microsoft） |
| **定位** | Anthropic 官方终端代理 | GitHub 生态终端代理 |
| **许可证** | 专有（闭源） | 专有（闭源） |
| **定价模型** | API 按 token 计费 / Max 订阅 | Copilot 订阅 + 高级请求 |
| **默认模型** | Claude Sonnet 4（可切换 Opus 4.6） | Claude Sonnet 4.5（可切换 GPT-5） |
| **架构** | Rust 原生 CLI | Node.js CLI |
| **实现语言** | Rust | TypeScript |
| **MCP 支持** | 完整支持（stdio + SSE） | 支持（GitHub MCP Server 原生集成） |
| **LSP 集成** | 无原生 LSP | 支持 LSP 诊断 |
| **GitHub 集成** | 通过 git 工具 + gh CLI | 原生深度集成（Issues、PRs、Actions） |

---

## 1. 代理框架

### Claude Code

```
用户输入
  → 系统提示 + CLAUDE.md 项目指令
  → Claude LLM（流式）
  → 工具调用解析
  → PreToolUse Hook（验证/修改）
  → 权限检查（7 层权限系统）
  → 工具执行（沙箱隔离）
  → PostToolUse Hook（反馈）
  → 结果回传 LLM
  → 重复直到完成
  → Stop Hook（验证完成合理性）
```

- **REPL 模式**：交互式会话，流式响应，支持 `/compact` 压缩上下文
- **子代理**：通过 `Task` 工具生成自主子代理，并行处理任务
- **计划模式**：`--plan` 标志触发，先规划后执行
- **自动记忆**：跨会话学习用户偏好，写入 `~/.claude/CLAUDE.md`
- **无头模式**：`--print` 标志支持 CI/CD 管道集成

### GitHub Copilot CLI

```
用户输入
  → 系统提示 + 仓库上下文
  → Coding Agent 框架调度
  → 模型选择（Sonnet 4.5 / GPT-5）
  → 工具调用解析
  → 操作确认（敏感操作需用户批准）
  → 工具执行
  → 结果回传 LLM
  → 重复直到完成
```

- **Coding Agent**：GitHub 原生 coding agent 框架，与 GitHub 平台深度绑定
- **多模型调度**：可根据任务复杂度切换模型
- **GitHub MCP Server**：原生集成 Issues、PRs、Actions 等 GitHub 资源
- **Workspace 代理**：通过 `@workspace` 引用整个项目上下文

### 关键差异

| 维度 | Claude Code | Copilot CLI |
|------|------------|-------------|
| 代理循环 | Tool-calling loop + Hooks | Coding agent harness |
| 子代理 | Task 工具生成自主代理 | 无独立子代理机制 |
| 计划模式 | `--plan` 显式触发 | 隐式规划 |
| 项目指令 | CLAUDE.md（多层级） | 仓库上下文自动推断 |
| CI/CD 集成 | `--print` 无头模式 | GitHub Actions 原生触发 |
| 会话恢复 | `--resume` 标志 | 有限的会话持久化 |

---

## 2. 模型选择

### Claude Code：Claude 系列锁定

| 模型 | 用途 | 上下文窗口 |
|------|------|-----------|
| Claude Sonnet 4 | 默认模型，日常编码 | 200K |
| Claude Opus 4.6 | 1M 上下文旗舰模型 | 1M |
| Claude Haiku | 快速响应，子代理 | 200K |

- 仅支持 Anthropic Claude 系列模型
- 通过 `--model` 参数切换
- 第三方提供商（Bedrock、Vertex）可代理访问同系列模型
- 模型能力与工具深度绑定优化

### Copilot CLI：多模型策略

| 模型 | 来源 | 用途 |
|------|------|------|
| Claude Sonnet 4.5 | Anthropic | 默认 coding agent 模型 |
| GPT-5 | OpenAI | 可选切换 |
| o3 | OpenAI | 推理密集型任务 |
| Gemini 2.5 Pro | Google | 可选切换 |

- 支持多家模型提供商
- 根据任务类型智能选择模型
- 高级模型消耗更多"高级请求"配额
- 模型切换对用户透明

### 关键差异

| 维度 | Claude Code | Copilot CLI |
|------|------------|-------------|
| 模型锁定 | Claude 系列独占 | 多提供商多模型 |
| 默认模型 | Claude Sonnet 4 | Claude Sonnet 4.5 |
| 最强模型 | Opus 4.6（1M 上下文） | GPT-5 / Sonnet 4.5 |
| 模型切换 | `--model` 参数 | UI 选择或自动调度 |
| 优化深度 | 工具与模型深度协同 | 通用适配层 |

---

## 3. GitHub 集成

### Claude Code

- **git 工具**：内置 `Bash` 工具执行 git 命令（commit、push、branch）
- **gh CLI 集成**：通过 `Bash` 调用 `gh` 命令操作 Issues、PRs
- **间接集成**：无原生 GitHub API，依赖外部 CLI 工具
- **GitHub Actions**：可在 Actions 中以 `--print` 模式运行
- **代码审查**：通过 `/review-pr` 技能审查 PR

```bash
# Claude Code 中操作 GitHub
claude --print "创建一个修复 bug 的 PR"
# 内部调用: git commit → git push → gh pr create
```

### Copilot CLI

- **原生 GitHub MCP Server**：直接访问 GitHub API
- **Issues 管理**：创建、查询、更新、关闭 Issues
- **PR 工作流**：创建 PR、审查代码、合并
- **Actions 集成**：查看工作流状态、触发运行、读取日志
- **仓库搜索**：跨仓库代码搜索和引用

```bash
# Copilot CLI 中操作 GitHub
copilot "查看最近失败的 CI 并修复"
# 直接通过 GitHub MCP Server 访问 API
```

### 关键差异

| 维度 | Claude Code | Copilot CLI |
|------|------------|-------------|
| GitHub API | 间接（通过 gh CLI） | 原生 MCP Server |
| Issues 操作 | 需 gh CLI 安装 | 内置支持 |
| PR 工作流 | 工具链组合 | 一等公民 |
| Actions 集成 | 有限支持 | 深度集成 |
| 代码搜索 | 本地仓库搜索 | 跨仓库搜索 |
| 仓库上下文 | 手动提供 | 自动获取 |

---

## 4. 扩展性

### Claude Code

**三重扩展机制：**

1. **MCP（Model Context Protocol）**
   - 支持 stdio 和 SSE 传输
   - 项目级（`.mcp.json`）和用户级（`~/.claude.json`）配置
   - 社区 MCP 服务器生态丰富

2. **Prompt Hooks**
   - `PreToolUse`：工具调用前拦截/修改
   - `PostToolUse`：工具调用后处理
   - `Stop`：代理停止前验证
   - 支持任意脚本语言实现

3. **CLAUDE.md 项目指令**
   - 多层级：项目根目录 > 子目录 > 用户级 > 企业级
   - 动态加载，支持条件指令
   - 跨项目共享通用规则

### Copilot CLI

**双重扩展机制：**

1. **MCP（Model Context Protocol）**
   - 支持 MCP 服务器集成
   - GitHub 官方 MCP Server 预装
   - VS Code 设置同步 MCP 配置

2. **LSP（Language Server Protocol）**
   - 利用 LSP 获取代码诊断信息
   - 智能感知类型信息和符号引用
   - 比纯文本搜索更精确的代码理解

### 关键差异

| 维度 | Claude Code | Copilot CLI |
|------|------------|-------------|
| MCP 支持 | 完整（stdio + SSE） | 支持（GitHub MCP 预装） |
| Hook 系统 | 三阶段 Prompt Hooks | 无 Hook 机制 |
| 项目指令 | CLAUDE.md 多层级 | 无等价机制 |
| LSP 集成 | 无 | 原生支持 |
| 代码理解 | 基于 Grep/Glob 文本搜索 | LSP 语义理解 + 文本搜索 |
| 扩展生态 | MCP 社区生态 | GitHub 生态 + VS Code 扩展 |

---

## 5. 安全与权限

### Claude Code：7 层权限体系

```
第 1 层：系统设置（企业管理员强制策略）
第 2 层：企业 CLAUDE.md（organizationwide 规则）
第 3 层：工作区设置（项目级权限）
第 4 层：用户设置（个人偏好）
第 5 层：CLAUDE.md 指令（项目级指令）
第 6 层：Prompt Hooks（运行时拦截）
第 7 层：沙箱执行（macOS Seatbelt / Linux 命名空间）
```

- **沙箱**：文件系统隔离 + 网络限制
- **权限规则**：`allow`（自动通过）/ `deny`（自动拒绝）
- **工具级控制**：可针对单个工具设置权限
- **会话级权限**：`--allowedTools` 参数限制可用工具
- **审计日志**：所有操作可追溯

### Copilot CLI：操作确认机制

- **交互式确认**：敏感操作（文件修改、命令执行）需用户确认
- **GitHub 权限**：继承 GitHub token 权限范围
- **沙箱环境**：GitHub Actions 中运行于隔离容器
- **速率限制**：API 调用频率限制防止滥用

### 关键差异

| 维度 | Claude Code | Copilot CLI |
|------|------------|-------------|
| 权限层级 | 7 层精细控制 | 操作确认 + GitHub 权限 |
| 沙箱 | 原生 OS 级沙箱 | Actions 容器隔离 |
| 企业策略 | 系统设置强制策略 | GitHub Enterprise 策略 |
| 工具级权限 | 支持（allow/deny 规则） | 不支持 |
| Hook 拦截 | PreToolUse 可阻止操作 | 无 |
| 网络控制 | 沙箱网络隔离 | GitHub 权限范围限制 |

---

## 6. 上下文管理

### Claude Code

- **1M token 上下文**：Opus 4.6 模型支持 100 万 token 窗口
- **上下文压缩**：`/compact` 命令或自动触发，将对话历史压缩
- **自定义压缩提示**：`/compact [自定义指令]` 指定压缩策略
- **记忆系统**：
  - 项目级：`.claude/CLAUDE.md` 自动学习项目偏好
  - 用户级：`~/.claude/CLAUDE.md` 跨项目通用偏好
- **会话恢复**：`--resume` / `--continue` 恢复历史会话
- **多文件并行读取**：工具调用可并行读取多个文件
- **智能搜索**：Glob + Grep 工具快速定位代码

### Copilot CLI

- **标准上下文窗口**：依赖所选模型的上下文窗口大小
- **仓库索引**：GitHub 后端建立仓库语义索引
- **@workspace 引用**：通过指令引用整个项目上下文
- **LSP 上下文**：利用语言服务器提供类型和引用信息
- **对话历史**：有限的会话历史保持

### 关键差异

| 维度 | Claude Code | Copilot CLI |
|------|------------|-------------|
| 最大上下文 | 1M token（Opus 4.6） | 取决于所选模型 |
| 上下文压缩 | `/compact` 智能压缩 | 无显式压缩机制 |
| 记忆系统 | 多层级自动记忆 | 无跨会话记忆 |
| 代码索引 | 运行时 Grep/Glob | 后端语义索引 |
| 会话恢复 | 完整支持 | 有限支持 |
| 语义理解 | 基于 LLM 推理 | LSP + LLM 混合 |

---

## 7. 定价模型

### Claude Code

| 方案 | 价格 | 说明 |
|------|------|------|
| API 直接计费 | 按 token 计费 | Sonnet 4：$3/$15 每百万 token |
| Claude Pro | $20/月 | 包含一定用量 |
| Claude Max（5x） | $100/月 | 5 倍用量 |
| Claude Max（20x） | $200/月 | 20 倍用量 |
| Bedrock/Vertex | 按 token 计费 | 通过云平台代理 |

- 重度使用者按 token 计费更灵活
- 无硬性请求次数限制（受 token 预算约束）
- 企业可通过 Bedrock/Vertex 统一账单

### Copilot CLI

| 方案 | 价格 | 高级请求 |
|------|------|---------|
| Copilot Free | $0 | 有限次数 |
| Copilot Pro | $10/月 | 包含一定高级请求 |
| Copilot Pro+ | $39/月 | 更多高级请求 |
| Copilot Business | $19/用户/月 | 团队管理 |
| Copilot Enterprise | $39/用户/月 | 企业功能 |

- "高级请求"模型：高级模型（GPT-5、Opus）消耗更多配额
- 订阅制，成本可预测
- 免费层降低入门门槛

### 关键差异

| 维度 | Claude Code | Copilot CLI |
|------|------------|-------------|
| 计费方式 | 按 token / 订阅混合 | 纯订阅 + 高级请求配额 |
| 免费层 | 无独立免费层 | Copilot Free 可用 |
| 成本可预测性 | API 模式波动较大 | 订阅制成本稳定 |
| 企业计费 | Bedrock/Vertex 统一 | GitHub Enterprise 统一 |
| 重度用户 | Max 20x（$200/月）封顶 | 高级请求可能耗尽 |

---

## 8. 企业支持

### Claude Code

- **企业系统设置**：管理员强制策略，优先级最高
- **设置优先级**：系统设置 > 工作区设置 > 用户设置
- **权限策略**：企业级 `allow`/`deny` 规则，用户不可覆盖
- **MCP 管控**：企业统一配置 MCP 服务器白名单
- **审计**：完整操作日志
- **部署**：支持 Bedrock/Vertex 私有部署

### Copilot CLI

- **GitHub Enterprise**：与 GitHub Enterprise Cloud/Server 深度集成
- **组织策略**：组织级别启用/禁用 Copilot 功能
- **内容排除**：指定仓库或文件排除 Copilot 访问
- **审计日志**：GitHub 审计日志集成
- **IP 策略**：企业 IP 保护和知识产权管控
- **SSO/SAML**：企业身份认证集成

### 关键差异

| 维度 | Claude Code | Copilot CLI |
|------|------------|-------------|
| 策略管理 | 系统设置强制策略 | GitHub 组织策略 |
| 身份认证 | API Key / OAuth | GitHub SSO/SAML |
| 私有部署 | Bedrock/Vertex | GitHub Enterprise Server |
| 审计 | 操作日志 | GitHub 审计日志 |
| 内容管控 | CLAUDE.md + 权限规则 | 内容排除规则 |
| 合规性 | SOC 2 | SOC 2 + GitHub 合规框架 |

---

## 选型建议

### 选择 Claude Code 的场景

| 场景 | 理由 |
|------|------|
| **深度代码重构** | 1M 上下文窗口可容纳大型代码库 |
| **复杂多步骤任务** | 子代理 + Hook 系统提供精细控制 |
| **非 GitHub 项目** | 不依赖 GitHub 生态 |
| **安全敏感环境** | 7 层权限 + OS 级沙箱 |
| **自定义工作流** | Prompt Hooks + CLAUDE.md 高度可定制 |
| **API 集成场景** | `--print` 无头模式适合自动化管道 |

### 选择 Copilot CLI 的场景

| 场景 | 理由 |
|------|------|
| **GitHub 重度用户** | 原生 Issues/PRs/Actions 集成 |
| **多模型需求** | 可切换 GPT-5、Sonnet 4.5、Gemini |
| **团队协作** | GitHub 组织管理 + 权限继承 |
| **成本敏感** | 免费层可用，订阅成本可预测 |
| **LSP 需求** | 原生语言服务器集成提供语义理解 |
| **已有 Copilot 订阅** | 边际成本为零 |

### 混合使用策略

两者并非互斥，可以根据任务类型混合使用：

```
日常编码 + GitHub 工作流 → Copilot CLI
  ↓
深度重构 + 复杂调试 → Claude Code
  ↓
CI/CD 自动化 → Claude Code（--print）+ GitHub Actions
  ↓
代码审查 + PR 管理 → Copilot CLI
```

---

## 结论

Claude Code 和 Copilot CLI 代表了终端 AI 编程代理的两条不同路径：

- **Claude Code** 走的是"深度代理"路线——通过 1M 上下文、7 层权限、Prompt Hooks 和子代理系统，提供最精细的控制和最强的单次任务处理能力。它更像一个可以完全信任的高级工程师，适合需要深度思考和复杂操作的场景。

- **Copilot CLI** 走的是"平台集成"路线——通过与 GitHub 生态的原生深度绑定，提供从代码编写到 Issues 管理到 CI/CD 的全流程覆盖。它更像一个熟悉团队所有工具的协作伙伴，适合以 GitHub 为中心的开发工作流。

**核心取舍**：选择 Claude Code 意味着获得更强的代理能力和自主性，但锁定在 Claude 模型生态；选择 Copilot CLI 意味着获得更好的平台集成和模型多样性，但代理深度不如 Claude Code。对于重度终端用户，两者配合使用是最优策略。
