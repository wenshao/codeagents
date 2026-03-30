# 17. Agent 长期记忆与个性化进阶指南

> 传统的 AI 对话是“无状态”的（读完就忘），而现代 Code Agent 支持“长期记忆”（越用越懂你）。本文将教你如何利用静态指令与动态学习，打造一个为你量身定制的“养成系”编程代理。

---

## 为什么你的 Agent 需要长期记忆？

当你第一次使用 Code Agent 时，它是一个知识渊博但对你一无所知的“外包员工”。它不知道你更喜欢 `pnpm` 还是 `npm`，不知道你们团队强制要求将路由逻辑和业务逻辑分离，更不知道你昨天刚因为一个环境配置 Bug 调试了一下午。

**长期记忆（Long-term Memory）** 的核心作用就是降低沟通成本。通过有效管理记忆，你可以让 Agent 从“外包员工”进化为“核心团队成员”。

在主流的 Agent 架构中，长期记忆分为**静态配置**和**动态演进**两部分。

---

## 第一部分：记忆的四个层次

一个成熟的个性化 Code Agent，其记忆体系通常包含四个层级：

### 层级 1：全局偏好（Global Preferences）
**“我是谁，我个人的编程习惯是什么？”**
跨项目通用的规则。例如：“我喜欢函数式编程，请默认使用 `ruff` 进行格式化。”

*   **Claude Code**: `~/.claude/CLAUDE.md`
*   **Gemini CLI / Qwen Code**: `~/.gemini/GEMINI.md` / `~/.qwen/QWEN.md`
*   **Copilot CLI**: `~/.copilot/copilot-instructions.md`（注：仅支持静态配置，无自动学习能力）

### 层级 2：项目约束（Project Context）
**“这个项目是什么，应该怎么运行？”**
包含技术栈、构建命令和测试规范。

*   **项目级**: 根目录下的 `CLAUDE.md`, `GEMINI.md`, `AGENTS.md`。
*   **专属方案**: `AGENTS.md`（配合符号链接支持所有平台，详见 [AGENTS.md 指令指南](./agents-md.md)）。

### 层级 3：子目录/模块级（Subdirectory Rules）
**“这个特定模块有哪些特殊限制？”**
实现细粒度控制的关键层。例如在 `tests/` 目录下强制使用不同的 Mock 策略。其优先级高于项目级指令（层级 2）。

### 层级 4：动态演进（Learned Memories）
**“我们在最近对话中达成了什么新共识？”**
这是第三代 Agent（如 Claude Code, Gemini CLI, Codex CLI）具备的特性。在对话过程中，这些 Agent 会**自动提取**有价值的信息并持久化。Qwen Code 也支持通过 `save_memory` 工具手动保存此类共识。

---

## 第二部分：各 Agent 动态记忆深度实操

了解不同工具管理记忆的底层机制（源码/文档证据），有助于你更好地掌控 Agent。

### Claude Code：基于主题的分类记忆池
*源码/文档依据：Anthropic 官方文档 + EVIDENCE.md*

*   **存储位置**: 用户目录下的 `~/.claude/projects/<project-hash>/memory/`。
*   **机制**: 自动识别 4 种记忆类型（**User**, **Feedback**, **Project**, **Reference**），并按主题存储。
*   **命令**: 
    *   `/memory`：管理 auto-memory 开关，并提供链接打开记忆文件夹。
    *   **限制**: **Claude Code 特有建议**——官方建议将 `MEMORY.md` 索引保持在 **200 行以内**，以确保检索效率。
    *   **深度参考**: 更多细节详见 [长期记忆深度对比](../comparison/memory-system-deep-dive.md#一claude-code4-层-claudemd--auto-memory最成熟)。

### Gemini CLI：实验性 memory_manager
*源码依据：`memoryTool.ts` + `memory-manager-agent.ts` + `config.ts`*

*   **存储位置**: 写入全局或项目级的 `GEMINI.md` 中。
*   **机制**: 默认通过 `MemoryTool` 追加。若启用实验性功能 `experimental.memoryManager: true`，则由专用子代理负责去重和分类。
*   **命令**:
    *   `/memory show`：列出当前已加载的记忆。
    *   `/memory add <text>`：手动注入事实。
    *   `/memory reload`：强制刷新记忆。
    *   **深度参考**: 更多细节详见 [长期记忆深度对比](../comparison/memory-system-deep-dive.md#二gemini-cliai-memory_manager-子代理最智能)。

### Codex CLI：双模型合并机制
*源码依据：Rust 二进制 strings `generate_memories` / `consolidation_model`*

*   **机制**: 运行专门的 `consolidation_model` 周期性地将分散的对话片段合并为结构化的记忆条目，存储在内部 SQLite 或 `.md` 索引中。

### Qwen Code：作用域粒度控制
*源码依据：`tools/memoryTool.ts` + `memoryCommand.ts`*

*   **Global Scope**: 写入 `~/.qwen/QWEN.md`，跨项目生效。
*   **Project Scope**: 写入当前目录的 `QWEN.md`。
*   **命令**: 支持 `/memory show`、`/memory add` 以及 `/memory refresh`。

---

## 结语

不要指望 Agent 在第一天就能完美接手你的项目。把它当成一个初级实习生，在日常交流中多给反馈，利用 `save_memory` 显式总结经验。

---

## 相关资源

*   [长期记忆与项目指令系统深度对比](../comparison/memory-system-deep-dive.md) — 各大主流 Agent 记忆系统的底层架构与参数分析。
*   [AGENTS.md 配置指南](./agents-md.md) — 如何编写一份能兼容 Codex、Copilot、Qwen、Claude 等全家桶的通用指令文件。
*   [CLAUDE.md 写作指南](./writing-claude-md.md) — 官方推荐的项目级指令书写规范。