# Oh My OpenAgent

**开发者：** code-yeongyu（韩国）
**许可证：** SUL-1.0（Sustainable Use License）
**仓库：** [github.com/code-yeongyu/oh-my-openagent](https://github.com/code-yeongyu/oh-my-openagent)
**官网：** [ohmyopenagent.com](https://ohmyopenagent.com/)
**Stars：** ~44K（2026-03）
**语言：** TypeScript
**基座：** 基于 OpenCode 的 Harness/扩展层
**最后更新：** 2026-03-28（多次日更）

## 概述

Oh My OpenAgent（原 oh-my-opencode）是一个基于 OpenCode 的 **Agent Harness 层**，不是独立的 Agent——它在 OpenCode 之上添加了多代理编排、多模型路由和增强工具链。自称 "the best agent harness"，~44K Stars（2025-12 创建至 2026-03，基于 GitHub 数据）。

与本项目收录的其他 Agent 的关键区别：**它不是从零构建的 Agent，而是 Harness Engineering 的实践案例**——在成品 Agent（OpenCode）之上设计环境、编排和反馈循环。

## 核心架构

### Discipline Agent 系统（多代理编排）

```
用户输入 → IntentGate（意图分析）
  │
  └── Sisyphus（编排者/CTO）
      ├── 任务分解 + 路由到专用代理
      ├── Hephaestus（深度工作者）
      ├── Prometheus（规划者/Metis）
      ├── Oracle（架构/调试专家）
      ├── Librarian（文档搜索专家）
      ├── Explore（代码搜索专家）
      └── Multimodal Looker（视觉代理）
```

7~10 个代理以希腊神话（Sisyphus/Prometheus/Hephaestus/Atlas/Metis/Momus）和英文职能（Oracle/Librarian/Explore/Multimodal Looker）混合命名，由 Sisyphus 作为 CTO 统一调度。

> **注**：GitHub README 和官网列出的代理数量不一致（GitHub 列出 7 个，官网列出 10 个含 Atlas/Momus/Dynamic Agent）。以上为两处来源的合集。

### 分类模型路由

| 任务类别 | 路由模型 | 说明 |
|---------|---------|------|
| visual-engineering | Claude Opus | 视觉/前端相关 |
| deep | GPT-5.4 / Kimi K2.5 | 深度推理任务 |
| quick | GLM-5 / Gemini | 轻量级快速任务 |
| ultrabrain | 最强可用模型 | 极难推理任务 |

> **注**：以上模型名称为 Oh My OpenAgent 项目自述的路由配置，部分模型名称（如 GPT-5.4、GLM-5）未经独立验证，实际可用模型可能有所不同。

### Hash-Anchored Edit Tool

使用 `LINE#ID` 内容哈希验证每次编辑，声称零过期行错误——解决了 LLM 编辑时行号偏移导致的错乱问题。

### ultrawork 命令

一个自迭代执行循环（GitHub README 称 "Ralph Loop"，官网称 "Self-Correction Loops"），激活所有代理持续工作直到任务 100% 完成。可同时启动 5+ 个后台专用代理并行执行。

## 独特功能

| 功能 | 说明 |
|------|------|
| **IntentGate** | 分析用户意图后再分类/执行，避免字面误解 |
| **Skill-Embedded MCPs** | Skill 携带自己的 MCP 服务器，避免上下文膨胀 |
| **内置 MCPs** | Exa Web 搜索、Context7、Grep.app |
| **LSP 集成** | 语言服务器协议集成（诊断/补全） |
| **AST-Grep** | 基于 AST 的代码搜索（比正则更精确） |
| **Tmux 集成** | 多窗格并行代理执行 |
| **Claude Code 兼容** | 声称兼容 Claude Code hooks、commands、skills、MCPs、plugins |

## 与其他 Agent 的定位对比

| 维度 | Oh My OpenAgent | Claude Code | Codex CLI | OpenCode |
|------|----------------|-------------|-----------|----------|
| **本质** | Harness 层（扩展 OpenCode） | 独立 Agent | 独立 Agent | 独立 Agent |
| **模型支持** | 多模型路由（6+ 提供商） | Claude 专属 | OpenAI 专属 | 多模型 |
| **多代理** | 7~10 Discipline Agent | Teammates | 实验性 | 无 |
| **模型路由** | 按任务类别自动路由 | 手动选择 | 无 | 手动选择 |
| **编辑精度** | Hash-Anchored（LINE#ID） | Edit/MultiEdit | apply_patch | 继承 |
| **Stars** | ~44K | N/A（闭源） | ~68K | ~12K（已归档） |
| **许可证** | SUL-1.0（自定义） | 专有 | Apache-2.0 | MIT |

## Harness Engineering 视角

Oh My OpenAgent 是 [Harness Engineering](../guides/build-your-own-agent.md) 概念的典型实践：

| Harness 支柱 | 实现方式 |
|-------------|---------|
| **文档即系统** | 继承 OpenCode 的 AGENTS.md + CLAUDE.md 读取 |
| **架构约束** | Discipline Agent 强制分工——编排/深度/规划分离 |
| **反馈循环** | Ralph Loop 自迭代 + LSP 诊断反馈 |
| **熵管理** | Hash-Anchored Edit 防止编辑漂移 |
| **渐进自治** | ultrawork 一键全自动 + IntentGate 意图理解 |

> **核心洞察**：Oh My OpenAgent 证明了 Harness 层可以在不修改底层 Agent（OpenCode）的情况下，通过编排、路由和工具增强带来显著的体验提升。这与 OpenAI Harness Engineering 文章的核心论点一致——"改进 Harness 可以在不更换模型的情况下带来显著性能提升"。

## 安装

```bash
bunx oh-my-opencode install
```

安装后提供独立二进制（macOS/Linux/Windows），无需 Bun/Node 运行时。依赖 OpenCode 作为基座运行。

## 优势

1. **多代理编排**——7~10 个 Discipline Agent 按职能自动分工，Sisyphus 统一调度
2. **多模型路由**——按任务类别自动选择最优模型（visual/deep/quick/ultrabrain）
3. **Hash-Anchored Edit**——内容哈希验证编辑精确性，防止行号偏移
4. **快速迭代**——多次日更，社区活跃（~44K Stars，4 个月）
5. **Claude Code 兼容**——声称兼容 Claude Code hooks/commands/skills/MCPs/plugins

## 劣势

1. **基座已归档**——OpenCode（opencode-ai/opencode）于 2025 年 9 月归档，长期可持续性存在风险
2. **非标准许可证**——SUL-1.0（Sustainable Use License），使用前需审查条款
4. **宣传语气较强**——技术声明（如"零过期行错误"）为项目自述，未经独立验证
5. **AI 参与开发**——项目有 AI 贡献者账号（sisyphus-dev-ai），代码质量需额外关注

## 使用场景

- **最适合**：需要多模型路由 + 多代理编排的复杂项目，团队已熟悉 OpenCode
- **适合**：想在不锁定单一模型的情况下使用 Claude/GPT/Gemini 等多种模型
- **不太适合**：需要长期稳定维护的企业项目（基座已归档），对许可证有严格要求的场景

## 资源链接

- [GitHub 仓库](https://github.com/code-yeongyu/oh-my-openagent)
- [官方文档](https://ohmyopenagent.com/)

> **免责声明**：以上数据基于 2026 年 3 月分析，Stars/功能等数据可能已过时。技术声明（如"零过期行错误"）为项目自述，未经独立验证。
