# 1. OpenCode 概述——Code Agent 开发者视角

> **阅读对象**：正在开发 Qwen Code / Gemini CLI 等 CLI Code Agent 的工程师
>
> **核心问题**：OpenCode 做对了什么？哪些设计值得借鉴？哪些是其独有路线不适合复制？

## 一、为什么要研究 OpenCode

OpenCode 是当前开源 Code Agent 中**架构最激进**的项目——19 个包的 monorepo、TUI + Web + Desktop 三客户端、37 种 LSP + 26 种 Formatter、100+ Provider 动态加载。它选择了一条与 Claude Code/Qwen Code 完全不同的路线：不是"做好一个终端 Agent"，而是"构建一个多客户端 AI 编程平台"。

对于 Qwen Code 开发者，OpenCode 的价值在于：
1. **18 种 Hook 类型**——比 Claude Code 的 Hook 更细粒度（工具定义修改、系统提示变换、会话压缩拦截）
2. **37 种 LSP 集成**——展示了如何在 Agent 中深度集成语言服务器
3. **models.dev 动态 Provider**——100+ Provider 零代码接入的统一接口
4. **SQLite 持久化**——Drizzle ORM + WAL 模式，比 JSONL 文件更适合复杂查询

## 二、能力矩阵速查

| 能力领域 | OpenCode | Qwen Code | 差距 | 参考价值 |
|---------|---------|-----------|------|---------|
| **多客户端** | TUI + Web + Desktop | TUI + WebUI + VSCode | 小 | 共享后端架构 |
| **Provider 数量** | 100+（models.dev 动态） | 10+（手动配置） | 大 | 动态 Provider 发现 |
| **LSP 集成** | 37 种语言 | 实验性（--experimental-lsp） | 大 | LSP 诊断自动注入 |
| **Formatter** | 26 种 | 无 | 大 | PostToolUse 自动格式化 |
| **Hook 系统** | 18 种类型（npm 插件） | ~12 事件（command） | 中 | 工具定义修改 Hook |
| **会话存储** | SQLite (Drizzle ORM) | JSONL 文件 | 中 | 结构化查询 |
| **主题** | 37 种 | ~25 种 | 小 | — |
| **权限系统** | Tree-sitter AST + Doom Loop | AST 只读检测 | 小 | Doom Loop 保护 |
| **上下文压缩** | auto-compact + hook | 单一 70% 压缩 | 中 | 压缩 Hook 拦截 |
| **会话管理** | Fork + Restore + Share + Review | 基础历史 | 大 | Session Fork/Restore |

## 三、项目信息

- **原作者**：Kujtim Hoxha（2025-03 起，Go + Bubble Tea TUI 单人项目）
- **现任 maintainer**：**Anomaly Innovations / SST 团队**（2025-04-30 接手，[anoma.ly](https://anoma.ly) / [sst.dev](https://sst.dev)），Dax Raad 主导（1,845 commits）
- **许可证**：MIT
- **仓库**：[github.com/anomalyco/opencode](https://github.com/anomalyco/opencode)
- **GitHub 仓库创建**：2025-04-30
- **Stars**：149,294（2026-04-25 实测，gh API）
- **Forks**：17,128
- **总 commits**：11,750
- **当前版本**：**v1.14.24**（2026-04-24 "full opentui release"）

> 完整演进历史（个人 → 公司接手 → 双重重写 Go→TS + Bubble Tea→OpenTUI）见 [00-history.md](./00-history.md)

## 四、核心功能

### 基础能力
- **多客户端**：TUI（终端）、Web 控制台（SolidJS）、桌面应用（Tauri + Electron 双平台）
- **多代理**：7 个内置代理（build、plan、general、explore 等），支持自定义
- **18 种内置工具**：Read、Write、Edit、Bash、Grep、Glob、WebFetch、WebSearch、CodeSearch、Skill、Task、Todo、apply_patch 等
- **100+ LLM 提供商**：通过 [models.dev](https://models.dev) + Vercel AI SDK 动态加载
- **MCP 支持**：StreamableHTTP / SSE / Stdio 三种传输 + OAuth
- **37 种 LSP 服务器**：覆盖 TypeScript、Python、Go、Rust、Java、C/C++、Ruby 等主流和小众语言
- **26 种 Formatter**：Prettier、Biome、gofmt、rustfmt、ruff 等
- **SQLite 持久化**：Drizzle ORM，WAL 模式

### 独特功能
- **18 种 Hook 类型**：event、config、auth、provider（Provider 发现）、tool（工具注册）、tool.definition（修改描述/参数）、tool.execute.before/after、chat.message、chat.params、chat.headers、permission.ask、command.execute.before、shell.env、experimental.chat.messages.transform/system.transform/session.compacting/text.complete
- **Doom Loop 保护**：连续 3 次权限拒绝自动中断
- **Session Fork & Restore**：从任意消息点分叉会话或回退
- **Session Share**：同步到云端生成公开链接
- **Git-backed Session Review**：基于 git 快照的 diff 可视化

## 五、可借鉴 vs 不适合复制

### 可借鉴的设计模式

| 模式 | 核心价值 | Qwen Code 适用性 |
|------|---------|-----------------|
| models.dev 动态 Provider | 零代码接入新 Provider | 高——Qwen Code 当前手动配置 Provider |
| 37 种 LSP 集成 | 编译器级代码理解 | 高——诊断自动注入到 /review 和编辑流程 |
| 18 种 Hook 类型 | 细粒度扩展性 | 中——`tool.definition` 修改工具描述是独特创新 |
| SQLite 持久化 | 复杂会话查询 | 中——比 JSONL 适合大规模会话管理 |
| Session Fork/Restore | 会话分叉和回退 | 中——类似 Claude Code 的 /rewind |
| Doom Loop 保护 | 防止 Agent 陷入权限拒绝循环 | 高——简单有效，~30 行代码 |
| 26 种 Formatter | 编辑后自动格式化 | 中——可通过 PostToolUse Hook 实现 |

### 不适合复制的设计

| 设计 | 为什么不适合 |
|------|------------|
| 19 包 monorepo | 架构复杂度过高，Qwen Code 作为 Gemini CLI fork 不适合重构为 monorepo |
| Tauri + Electron 双平台桌面 | 维护成本高，Qwen Code 专注 CLI + VSCode |
| Bun 运行时 | Qwen Code 基于 Node.js，切换运行时风险大 |
| Effect 框架 | 学习曲线陡峭，与现有 Qwen Code 代码风格差异大 |

## 六、付费计划

| 计划 | 价格 | 包含内容 |
|------|------|---------|
| **免费 / 开源** | $0 | 自带 API Key 使用任意 provider |
| **OpenCode Zen** | 按量付费 | 编码优化模型，月度限额 |
| **OpenCode Go** | $5 首月 → $10/月 | GLM-5、Kimi K2.5、MiniMax M2.5/M2.7 |

## 七、资源链接

- [网站](https://opencode.ai/) | [GitHub](https://github.com/anomalyco/opencode) | [Changelog](https://opencode.ai/changelog) | [models.dev](https://models.dev)
