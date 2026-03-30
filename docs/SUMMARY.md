# 0. 一页总结：AI 编程 Code Agent 选型

> 给没时间看 34,600+ 行文档的人。2026 年 3 月。
>
> **维护说明**：本页包含若干动态数据摘要。更新时请先核对 [`docs/data/agents-metadata.json`](./data/agents-metadata.json) 与 [`docs/evidence-index.md`](./evidence-index.md)。

## 一句话定位

| Agent | 一句话 | 适合谁 |
|------|--------|--------|
| **Claude Code** | Anthropic 官方终端代理，安全最严格（28 条阻止规则），插件生态最丰富（14 个官方插件） | 需要企业级安全和深度推理的团队 |
| **Copilot CLI** | GitHub 原生集成，读取所有主流指令文件（CLAUDE.md/GEMINI.md/AGENTS.md），67 个内置工具 | GitHub 重度用户和企业团队 |
| **Codex CLI** | OpenAI 官方，三平台 OS 级沙箱（Seatbelt/Bubblewrap/Windows Tokens），Rust 核心 | 安全敏感场景和 OpenAI 生态用户 |
| **Aider** | Git 原生老牌工具，14 种编辑格式，PageRank 仓库地图，99% 一人开发 | Git 重度用户和喜欢细粒度控制的开发者 |
| **Gemini CLI** | Google 官方，TOML 策略引擎，四阶段压缩算法 | Google Cloud 用户和大团队 |
| **Qwen Code** | Gemini CLI 分叉 + 阿里云生态，提供免费层，Arena 多模型竞争模式 | 中文开发者和成本敏感用户 |
| **Kimi CLI** | 月之暗面出品，零遥测（隐私最佳），双模式交互（TUI + Shell） | 隐私敏感用户和国内开发者 |
| **Goose** | Block 出品后捐赠 Linux 基金会，MCP 原生架构，398 个贡献者 | MCP 生态和开源社区 |
| **OpenCode** | 多客户端（TUI+Web+桌面），37 个 LSP，100+ 模型提供商 | 需要多客户端和 IDE 集成的团队 |
| **Qoder CLI** | 阿里通义灵码闭源代理，Go 原生 43MB，Quest 模式，`--with-claude-config` 兼容 Claude Code | 阿里云生态和 Quest 自主执行场景 |

## 30 秒决策树

```
你的首要需求是什么？

├── 企业安全合规 → Claude Code（28 条 BLOCK + 5 层设置 + 沙箱）
├── GitHub 深度集成 → Copilot CLI（35 GitHub 工具 + Actions/PR/Issues）
├── 完全免费 → Qwen Code 或 Gemini CLI（具体额度见 docs/data/agents-metadata.json）
├── 隐私零遥测 → Kimi CLI（零分析）或 OpenCode（零分析）
├── Git 工作流控制 → Aider（/commit /undo /diff /git + 自动提交归因）
├── 最大模型灵活性 → Goose（58+ 提供商）或 Aider（100+ via LiteLLM）
├── 沙箱隔离执行 → Codex CLI（3 平台原生沙箱）或 Claude Code
└── 最活跃开发 → Codex CLI（882 commits/月）或 Gemini CLI（708/月）
```

## 关键数字对比

> 动态数字（Stars、免费层、验证日期）请以 [`docs/data/agents-metadata.json`](./data/agents-metadata.json) 为准。

| | Claude Code | Copilot CLI | Codex CLI | Aider | Gemini CLI | Qwen Code | Kimi CLI |
|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| **命令数** | ~79 | 34 | 28 | 42 | 39 | 40+ | 28 |
| **工具数** | 20+ | 67 | 9 | — | 23 | 18 | 18 |
| **沙箱** | ✓ | ✗ | ✓ | ✗ | ✓ | ✓ | ✗ |
| **遥测** | 782 事件 | 有 | 有 | opt-in 10% | 194 键 | 阿里 RUM | **零** |

## 安全等级

```
最严格 ←————————————————————————————→ 最宽松

Claude Code   Codex CLI   Gemini CLI   Goose   Copilot   Kimi   Aider
(28 BLOCK     (3平台沙箱   (Conseca     (ML     (审批)    (审批)  (无)
+LLM分类器    +Guardian)   +seccomp)    检测)
+Prompt Hook)
```

## 隐私等级

```
最隐私 ←————————————————————————————→ 最多采集

Kimi CLI   OpenCode   Aider      Goose     Claude Code   Copilot   Gemini CLI
(零遥测)   (零遥测)   (opt-in    (opt-in   (782事件      (内部)    (CPU/GPU/RAM
                      10%采样)   UUID)     +MachineID)             +194键+email)
```

## 技术栈快览

| Agent | 语言 | 运行时 | 二进制大小 | 最低要求 |
|------|------|--------|-----------|---------|
| Claude Code | TS/Bun | Bun（内嵌） | 227 MB | 无 |
| Copilot CLI | TS/Node | Node ≥ 24 | 133 MB | Node 24 |
| Codex CLI | Rust | 无（原生） | 137 MB | Node 16（仅启动器） |
| Aider | Python | Python ≥ 3.10 | 20 MB | Python 3.10 |
| Gemini CLI | TypeScript | Node ≥ 20 | 50 MB | Node 20 |
| Qwen Code | TypeScript | Node ≥ 20 | 55 MB | Node 20 |
| Kimi CLI | Python | Python ≥ 3.12 | 15 MB | Python 3.12 |

## 完整文档导航

- **深度分析**：[claude-code/](./tools/claude-code/) | [copilot-cli/](./tools/copilot-cli/) | [codex-cli/](./tools/codex-cli/) | [gemini-cli/](./tools/gemini-cli/) | [更多...](./tools/)
- **对比文档**：[功能矩阵](./comparison/features.md) | [命令深度](./comparison/slash-commands-deep-dive.md) | [隐私遥测](./comparison/privacy-telemetry.md) | [定价](./comparison/pricing.md) | [系统要求](./comparison/system-requirements.md)
- **实用指南**：[入门](./guides/getting-started.md) | [长期记忆](./guides/long-term-memory.md) | [配置示例](./guides/config-examples.md) | [迁移](./guides/migration.md) | [故障排查](./guides/troubleshooting.md)
