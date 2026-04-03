# 15. Claude Code vs Cursor：终端代理 vs AI IDE

> Claude Code（Anthropic 终端原生代理）vs Cursor（AI 原生 IDE）——两大商业 AI 编程工具的全面对比。一个扎根终端，一个重塑编辑器，代表了 AI 辅助开发的两条路径。

## 定位对比

| 维度 | Claude Code | Cursor |
|------|------------|--------|
| **开发者** | Anthropic | Anysphere |
| **许可证** | 专有（闭源） | 专有（闭源） |
| **形态** | 终端 CLI 代理 | VS Code 分叉 IDE |
| **定价** | API token 按量计费 / Max 订阅 | 订阅制（Free / Pro / Business） |
| **核心模型** | Claude 系列（锁定） | 多模型（Claude / GPT / Gemini） |
| **架构** | Rust 原生 CLI | Electron + VS Code 扩展架构 |
| **实现语言** | Rust | TypeScript |
| **操作系统** | macOS / Linux（终端） | macOS / Linux / Windows |
| **上下文窗口** | 100 万 token（Opus 4.6） | 依模型而定，最大 20 万 token |
| **目标用户** | 终端重度用户、高级开发者 | 全谱系开发者、团队 |

---

## 1. 交互模式

### Claude Code：终端 CLI

```
$ claude "重构 auth 模块"
> 分析项目结构...
> 读取 src/auth/*.ts（12 个文件）
> 创建重构计划...
> 执行文件修改...
> 运行测试验证...
✓ 重构完成，已修改 8 个文件
```

- **REPL 交互**：在终端中与 AI 实时对话，流式输出
- **管道集成**：可与 `git`、`grep`、`jq` 等 Unix 工具无缝配合
- **无头模式**：`claude -p` 支持脚本化调用和 CI/CD 集成
- **SSH 友好**：远程服务器上直接使用，无需 GUI

### Cursor：AI 原生 IDE

```
Cursor 编辑器界面
├── 代码编辑区（实时内联建议）
├── Chat 面板（侧边对话）
├── Composer（多文件编辑代理）
└── 终端（内置 + AI 辅助）
```

- **内联补全**：Tab 键接受 AI 代码建议，体验接近 Copilot
- **可视化差异**：直接在编辑器中预览 AI 修改，逐块接受/拒绝
- **Cmd+K 编辑**：选中代码后用自然语言指令修改
- **GUI 交互**：所有操作可通过鼠标/快捷键完成

### 关键差异

| 维度 | Claude Code | Cursor |
|------|------------|--------|
| 交互方式 | 纯文本终端 | 图形化 IDE |
| 学习曲线 | 需要终端经验 | VS Code 用户零成本 |
| 远程开发 | SSH 原生支持 | 需要 Remote SSH 扩展 |
| 代码预览 | 文本差异输出 | 可视化 diff 面板 |
| 自动化 | 管道/脚本原生 | 需要额外配置 |
| 启动速度 | 毫秒级 | 秒级（Electron） |

---

## 2. 代理能力

### Claude Code

```
用户输入
  → 系统提示 + CLAUDE.md 项目指令
  → Claude LLM（流式）
  → 工具调用（Bash / Read / Edit / Write / Grep / Glob）
  → 权限检查（allow / ask / deny）
  → 工具执行（可能沙箱）
  → 结果回传 LLM
  → 重复直到完成
```

- **Agent 工具**：通过 `Task` 生成子代理，并行处理子任务
- **计划模式**：先规划再执行，用户可审批每一步
- **自动记忆**：跨会话学习项目偏好，写入 CLAUDE.md
- **工具链**：Bash / Read / Edit / Write / Grep / Glob / Agent / WebFetch 等

### Cursor

```
用户输入（Chat / Composer / Cmd+K）
  → 上下文收集（@-引用 + 代码库索引）
  → LLM 调用（用户选择模型）
  → 代码生成 / 修改建议
  → 用户审查（可视化 diff）
  → 应用修改
```

- **Composer**：多文件编辑代理，支持跨文件重构
- **Background Agent**：云端沙箱中自主执行任务（类似 Claude Code 的无头模式）
- **Bug Finder**：自动扫描代码库发现潜在问题
- **内联编辑**：Cmd+K 选中代码直接用自然语言修改

### 关键差异

| 维度 | Claude Code | Cursor |
|------|------------|--------|
| 代理自主性 | 高度自主，可连续执行数十步 | Composer 自主，Chat 需确认 |
| 子代理 | Task 工具生成并行子代理 | Background Agent（云端沙箱） |
| 工具调用 | 直接调用系统命令 | 通过 IDE API 间接调用 |
| 文件修改 | 直接写入文件系统 | 编辑器缓冲区，需用户确认 |
| 测试执行 | Bash 直接运行 | 内置终端运行 |
| 多任务 | 多个终端窗口 | 多个 Composer 会话 |

---

## 3. 上下文管理

### Claude Code

- **100 万 token 上下文**：Opus 4.6 支持超长上下文窗口
- **自动压缩**：上下文接近上限时自动压缩历史对话
- **CLAUDE.md 层级**：项目根目录 → 子目录 → 用户级，逐级加载
- **文件读取**：按需读取文件内容，精确控制上下文消耗
- **`--resume`**：恢复之前的会话上下文

```
上下文来源优先级：
1. 系统提示（内置）
2. CLAUDE.md（项目/目录/用户级）
3. 用户输入
4. 工具执行结果（文件内容、命令输出）
5. 自动记忆（跨会话学习）
```

### Cursor

- **@-引用系统**：`@file`、`@folder`、`@code`、`@web`、`@docs` 精确引用
- **代码库索引**：自动构建全项目语义索引，支持模糊搜索
- **.cursorrules**：项目级指令文件，类似 CLAUDE.md
- **自动上下文**：编辑器自动附加当前文件、选中代码、终端输出
- **文档索引**：`@docs` 可索引外部文档作为上下文

```
上下文来源：
1. 系统提示 + .cursorrules
2. @-引用（用户显式指定）
3. 当前文件 / 选中代码
4. 代码库索引（语义检索）
5. 终端输出 / lint 错误
```

### 关键差异

| 维度 | Claude Code | Cursor |
|------|------------|--------|
| 上下文窗口 | 100 万 token | 依模型，最大约 20 万 |
| 上下文获取 | 主动读取（按需） | 被动索引 + @-引用 |
| 项目理解 | 运行时动态探索 | 预建索引 + 语义搜索 |
| 压缩策略 | 自动对话压缩 | 截断 / 新会话 |
| 项目指令 | CLAUDE.md（多级） | .cursorrules |
| 跨会话记忆 | 自动记忆 + CLAUDE.md | 无持久记忆 |

---

## 4. 模型支持

### Claude Code

- **锁定 Claude 系列**：Sonnet 4 / Opus 4.6 / Haiku
- **模型切换**：会话内 `/model` 命令切换
- **自动路由**：简单任务用 Haiku，复杂任务用 Opus
- **第三方接入**：不支持非 Claude 模型

### Cursor

- **多模型支持**：
  - Claude 系列（Sonnet / Opus）
  - GPT 系列（GPT-4o / o1 / o3）
  - Gemini 系列（2.5 Pro）
  - 自定义模型（通过 API key）
- **模型选择器**：每次对话可选择不同模型
- **自带配额**：订阅包含一定量的快速请求

### 关键差异

| 维度 | Claude Code | Cursor |
|------|------------|--------|
| 模型锁定 | 仅 Claude | 多提供商 |
| 最强模型 | Opus 4.6（100 万上下文） | 取决于用户选择 |
| 模型切换 | `/model` 命令 | 下拉菜单 |
| 自定义模型 | 不支持 | 支持 API key 接入 |
| 计费方式 | 按 token 消耗 | 订阅内含快速请求 |

---

## 5. 扩展性

### Claude Code

```toml
# MCP 服务器配置（~/.claude/settings.json）
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"]
    }
  }
}
```

- **MCP 协议**：标准化工具扩展，支持 GitHub / Jira / 数据库等
- **Prompt Hooks（钩子 (Hook)）**：PreToolUse / PostToolUse / Stop 钩子 (Hook)，自定义工作流
- **自定义斜杠命令**：`.claude/commands/` 目录下定义项目命令
- **13 个官方插件 (Plugin)**：GitHub / Linear / Sentry 等

### Cursor

```
Cursor 扩展体系：
├── VS Code 扩展市场（完全兼容）
├── .cursorrules（项目指令）
├── MCP 服务器（工具扩展）
├── @-引用自定义文档
└── 自定义 AI 规则
```

- **VS Code 扩展**：继承整个 VS Code 扩展生态
- **MCP 支持**：同样支持 MCP 协议接入外部工具
- **Rules 系统**：项目级 / 用户级规则文件
- **文档索引**：`@docs` 添加自定义文档源

### 关键差异

| 维度 | Claude Code | Cursor |
|------|------------|--------|
| 插件生态 | MCP + 13 个官方插件 | VS Code 市场 + MCP |
| 扩展规模 | 有限但精准 | 海量（VS Code 生态） |
| 工作流定制 | Prompt Hooks（代码级） | Rules（声明式） |
| 项目指令 | CLAUDE.md + 自定义命令 | .cursorrules + Rules |
| 协议标准 | MCP 原生支持 | MCP 支持 + 扩展 API |

---

## 6. Git 集成

### Claude Code

```bash
# 原生 Git 操作
$ claude "提交当前更改"
> 运行 git status...
> 分析变更内容...
> 生成 commit message...
> 执行 git add + git commit
✓ 已提交：fix: resolve auth token refresh race condition

# PR 工作流
$ claude "创建 PR"
> 分析分支差异...
> 生成 PR 标题和描述...
> 执行 gh pr create
✓ PR #142 已创建
```

- **直接调用 git**：通过 Bash 工具执行所有 git 命令
- **智能 commit**：自动分析变更生成提交信息
- **PR 创建**：集成 `gh` CLI，自动生成 PR 描述
- **冲突解决**：理解 merge conflict 标记并自动解决

### Cursor

- **GUI Git 面板**：继承 VS Code 的 Source Control 面板
- **AI Commit Message**：一键生成提交信息
- **可视化 diff**：图形化差异比较
- **分支管理**：图形界面操作分支

### 关键差异

| 维度 | Claude Code | Cursor |
|------|------------|--------|
| Git 操作 | 命令行直接执行 | GUI 面板 + 命令行 |
| Commit 生成 | 深度分析 + 自动执行 | 一键生成消息 |
| PR 工作流 | 端到端自动化 | 需手动操作 |
| 冲突解决 | AI 自动解决 | 可视化手动解决 |
| CI/CD 集成 | 原生脚本集成 | 需额外配置 |

---

## 7. 团队与企业

### Claude Code

```
设置优先级（5 层）：
1. 系统级设置（Anthropic 内置）
2. 企业策略（管理员）
3. 工作区设置（项目级）
4. 用户设置（个人）
5. 项目 CLAUDE.md
6. 目录级 CLAUDE.md
7. 用户级 CLAUDE.md
```

- **Teammates**：共享代理实例，团队协作
- **企业策略**：管理员控制权限、工具访问、模型选择
- **Max 订阅**：团队级别的使用量管理
- **SSO/SCIM**：企业身份管理集成

### Cursor

- **Business 计划**：团队管理 + 集中计费
- **管理控制台**：成员管理、使用量监控
- **Privacy Mode**：企业级隐私模式，代码不用于训练
- **集中规则**：团队共享 .cursorrules

### 关键差异

| 维度 | Claude Code | Cursor |
|------|------------|--------|
| 设置层级 | 5 层优先级体系 | 项目级 + 用户级 |
| 团队协作 | Teammates 共享代理 | Business 计划团队管理 |
| 管理粒度 | 企业策略精细控制 | 管理控制台 |
| 身份管理 | SSO / SCIM | SSO |
| 审计日志 | 会话级别追踪 | 使用量统计 |

---

## 8. 安全模型

### Claude Code

```
权限三级体系：
┌─────────────────────────────────────┐
│  allow  — 自动允许（白名单工具）     │
│  ask    — 每次询问用户（默认）       │
│  deny   — 禁止执行（黑名单）        │
└─────────────────────────────────────┘

沙箱机制：
├── macOS：Seatbelt sandbox-exec
├── Linux：Docker 容器隔离
└── 网络：默认允许，可配置限制
```

- **文件系统沙箱 (Sandbox)**：限制代理访问的目录范围
- **命令白名单**：精确控制可执行的 shell 命令
- **Prompt Hooks（钩子 (Hook)）**：PreToolUse 钩子 (Hook) 可拦截危险操作
- **网络控制**：可限制代理的网络访问范围

### Cursor

- **Privacy Mode**：开启后代码不存储在 Cursor 服务器
- **SOC 2 认证**：企业级安全合规
- **本地处理**：代码索引在本地构建
- **代码不训练**：明确承诺不使用用户代码训练模型

### 关键差异

| 维度 | Claude Code | Cursor |
|------|------------|--------|
| 执行沙箱 | OS 级沙箱（Seatbelt/Docker） | IDE 进程隔离 |
| 权限控制 | 三级权限 + 工具粒度 | Privacy Mode 开关 |
| 数据隐私 | 本地执行，API 传输对话 | Privacy Mode 控制 |
| 网络限制 | 可配置网络白名单 | 无细粒度网络控制 |
| 代码访问 | 按需读取，用户可控 | 索引全项目 |
| 合规认证 | 依赖 Anthropic API 政策 | SOC 2 |

---

## 9. 定价对比

### Claude Code

| 方案 | 价格 | 说明 |
|------|------|------|
| **API 直接计费** | 按 token 计费 | Sonnet ~$3/$15 per 1M token（输入/输出） |
| **Claude Pro** | $20/月 | 包含有限 Claude Code 使用量 |
| **Claude Max** | $100-200/月 | 大量 Claude Code 使用量 |
| **企业 API** | 按量协商 | 批量折扣 + SLA |

### Cursor

| 方案 | 价格 | 说明 |
|------|------|------|
| **Hobby** | 免费 | 2000 次补全 + 50 次慢速请求 |
| **Pro** | $20/月 | 无限补全 + 500 次快速请求 |
| **Business** | $40/月/人 | 团队管理 + 管理控制台 |
| **Enterprise** | 定制 | SSO + 审计 + 自定义部署 |

### 成本分析

| 使用场景 | Claude Code 估算 | Cursor 估算 |
|----------|------------------|-------------|
| 轻度使用（每天 10 次对话） | ~$20/月（Pro） | $0（Hobby 够用） |
| 中度使用（每天 30 次对话） | ~$100/月（Max） | $20/月（Pro） |
| 重度使用（每天 100+ 次对话） | ~$200/月（Max） | $20/月（Pro，含慢速） |
| 团队（10 人） | ~$2000/月 | $400/月（Business） |

---

## 选型建议

| 用户画像 | 推荐工具 | 理由 |
|----------|----------|------|
| **终端重度用户** | Claude Code | 原生终端体验，管道集成，SSH 友好 |
| **VS Code 用户** | Cursor | 零成本迁移，熟悉的 IDE 体验 |
| **全栈独立开发者** | Claude Code | 端到端自动化，代理自主性强 |
| **前端开发者** | Cursor | 可视化预览，内联补全体验好 |
| **DevOps / SRE** | Claude Code | 脚本集成，CI/CD 自动化 |
| **团队协作（预算敏感）** | Cursor | 订阅制可预测成本 |
| **大型代码库** | 两者结合 | Claude Code 深度分析 + Cursor 日常编辑 |
| **远程服务器开发** | Claude Code | SSH 直连，无需 GUI |
| **多语言/多模型需求** | Cursor | 多模型选择灵活 |
| **安全敏感环境** | Claude Code | 细粒度权限控制 + OS 级沙箱 |

---

## 结论

Claude Code 和 Cursor 代表了 AI 辅助编程的两条不同路径：

**Claude Code 的核心优势**：
- 终端原生，与 Unix 工具链深度集成
- 100 万 token 超长上下文，适合理解大型代码库
- 高度自主的代理能力，端到端完成复杂任务
- 细粒度安全控制（沙箱 + 三级权限）
- 5 层设置体系，企业管理灵活

**Cursor 的核心优势**：
- GUI 可视化体验，学习成本低
- 多模型支持，不锁定单一供应商
- VS Code 扩展生态，海量插件可用
- 订阅制定价可预测，有免费层
- 内联补全体验流畅，适合日常编码

**最佳实践**：两者并非互斥。许多开发者采用组合策略——用 Cursor 处理日常编码和小范围修改，用 Claude Code 执行大型重构、代码审查和自动化任务。终端与 IDE 的互补，往往能发挥 AI 编程工具的最大价值。
