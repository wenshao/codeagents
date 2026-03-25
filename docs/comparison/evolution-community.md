# 版本迭代与社区数据

> 采集时间: 2026-03-25。数据来源: GitHub API (`gh api repos/X`)。

## 项目概览

| 工具 | Stars | Forks | 贡献者 | 创建时间 | 语言 | 许可证 |
|------|-------|-------|--------|---------|------|--------|
| **Gemini CLI** | 99,025 | 12,601 | 447 | 2025-04 | TypeScript | Apache-2.0 |
| **Claude Code** | 82,456 | 6,901 | 47 | 2025-02 | Shell/Bun | 专有 |
| **Codex CLI** | 67,475 | 9,029 | 386 | 2025-04 | Rust | Apache-2.0 |
| **Aider** | 42,362 | 4,065 | 170 | 2023-05 | Python | Apache-2.0 |
| **Goose** | 33,552 | 3,124 | 398 | 2024-08 | Rust | Apache-2.0 |
| **Qwen Code** | 21,039 | 1,877 | 350 | 2025-06 | TypeScript | Apache-2.0 |
| **OpenCode** | 11,578 | — | — | 2025-03 | Go | MIT |
| **Copilot CLI** | 9,559 | 1,298 | 19 | 2023-01 | Shell | 专有 |
| **Kimi CLI** | 7,364 | 760 | 53 | 2025-10 | Python | Apache-2.0 |

## 发布节奏

| 工具 | 总发布数 | 最新版本 | 发布频率 | 近 5 版间隔 |
|------|---------|---------|---------|-----------|
| **Codex CLI** | 649 | v0.117.0-alpha.17 | **每日多次**（alpha） | 2-6 小时 |
| **Gemini CLI** | 430 | v0.36.0-preview.0 | **每日**（含 nightly） | 4-24 小时 |
| **Qwen Code** | 353 | v0.13.0-nightly | **每日**（含 nightly） | 12-24 小时 |
| **Copilot CLI** | 197 | v1.0.11 | 每周 | — |
| **Goose** | 124 | v1.28.0 | 每 1-5 天 | 1-12 天 |
| **Aider** | 93 | v0.86.0 | 每 2-4 周 | 14-30 天 |
| **Kimi CLI** | 78 | v1.25.0 | 每 2-5 天 | 1-5 天 |
| **Claude Code** | 67 | v2.1.83 | **每天**（最近） | 1-2 天 |

> **洞察：** Codex CLI 发布最频繁（649 版，含大量 alpha），Gemini CLI 次之（430 版）。Aider 是最稳定的（93 版，每月发布）。Claude Code 近期加速（v2.1.78→2.1.83，5 天 5 版）。

## 开发活跃度（近 30 天提交数）

| 工具 | 30 天提交 | 日均 | 活跃度 |
|------|----------|------|--------|
| **Codex CLI** | 882 | 29.4 | ★★★★★ |
| **Qwen Code** | 757 | 25.2 | ★★★★★ |
| **Gemini CLI** | 708 | 23.6 | ★★★★★ |
| **Goose** | 304 | 10.1 | ★★★★☆ |
| **Kimi CLI** | 100 | 3.3 | ★★★☆☆ |
| **Claude Code** | 49 | 1.6 | ★★☆☆☆ |
| **Aider** | 25 | 0.8 | ★★☆☆☆ |

> **洞察：** Codex/Qwen/Gemini 三强日均 20+ 提交，处于高速迭代期。Claude Code 和 Aider 提交数较少但每次发布质量高（Claude Code 是闭源，内部提交不可见）。

## 核心贡献者

### Claude Code（Anthropic 内部）
| 贡献者 | 提交数 | 角色 |
|--------|--------|------|
| actions-user | 268 | CI 自动化 |
| bcherny (Boris Cherny) | 70 | code-review 插件作者 |
| ant-kurt | 31 | 核心开发 |
| fvolcic | 20 | 核心开发 |
| ashwin-ant | 19 | 核心开发 |

### Aider（个人项目为主）
| 贡献者 | 提交数 | 角色 |
|--------|--------|------|
| **paul-gauthier** | **12,633** | 创始人（占 99%+） |
| ei-grad | 47 | 社区贡献 |
| joshuavial | 32 | 社区贡献 |

> **洞察：** Aider 几乎是 Paul Gauthier 一人项目（12,633/12,758 = 99%），这是风险也是效率。

### Gemini CLI（Google 团队）
| 贡献者 | 提交数 | 角色 |
|--------|--------|------|
| scidomino | 356 | 核心开发 |
| NTaylorMullen | 330 | 核心开发 |
| abhipatel12 | 253 | 核心开发 |
| jacob314 | 248 | 核心开发 |

> **洞察：** 多名核心贡献者均衡分布，团队健康。

### Codex CLI（OpenAI 团队）
| 贡献者 | 提交数 | 角色 |
|--------|--------|------|
| bolinfest | 674 | 核心开发 |
| jif-oai | 632 | 核心开发 |
| aibrahim-oai | 452 | 核心开发 |

> **洞察：** 386 位贡献者，最开放的闭源公司项目。

### Qwen Code（阿里云团队）
| 贡献者 | 提交数 | 角色 |
|--------|--------|------|
| tanzhenxin | 764 | 核心开发 |
| yiliang114 | 399 | 核心开发 |
| Mingholy | 345 | 核心开发 |

> **洞察：** 350 位贡献者，分叉 Gemini CLI 后快速发展。

### Kimi CLI（月之暗面团队）
| 贡献者 | 提交数 | 角色 |
|--------|--------|------|
| **stdrc** | **879** | 核心开发（占 80%+） |
| RealKai42 | 106 | 核心开发 |

> **洞察：** stdrc 为主要开发者，与 Aider 类似的单核心开发者模式。

### Goose（Block 团队）
| 贡献者 | 提交数 | 角色 |
|--------|--------|------|
| zanesq | 255 | 核心开发 |
| alexhancock | 201 | 核心开发 |
| michaelneale | 197 | 核心开发 |
| DOsinga | 197 | 核心开发 |
| angiejones | 193 | 核心开发 |

> **洞察：** 398 位贡献者，5 名核心开发者均衡（最健康的团队结构）。已捐赠给 Linux Foundation AAIF。

## Feature Flags 揭示的未来方向

| 工具 | Flag | 推测功能 | 状态 |
|------|------|---------|------|
| **Claude Code** | `tengu_turtle_carbon` | Ultrathink 超深度推理 | 内部测试 |
| **Codex CLI** | `voice_transcription` | 语音输入转录 | under dev |
| **Codex CLI** | `realtime_conversation` | 实时语音对话 | under dev |
| **Codex CLI** | `image_generation` | 图片生成 | under dev |
| **Codex CLI** | `multi_agent` | 多代理并行 | **stable, 已上线** |
| **Codex CLI** | `guardian_approval` | AI 安全审查子代理 | experimental |
| **Codex CLI** | `memories` | 跨会话记忆 | under dev |
| **Codex CLI** | `plugins` | 插件系统 | under dev |
| **Copilot CLI** | `AUTOPILOT_MODE` | 全自动持续执行 | experimental |
| **Copilot CLI** | `CCA_DELEGATE` | 远程委派 PR | on |
| **Goose** | 无 feature flag 系统 | — | — |
| **Qwen Code** | Arena 模式已上线 | 多模型竞争执行 | 已实现 |

## 项目成熟度评估

| 工具 | 创建至今 | 版本阶段 | 贡献者分布 | 综合成熟度 |
|------|---------|---------|-----------|-----------|
| **Aider** | 2 年 10 月 | v0.86（稳定迭代） | 单核心（风险） | ★★★★☆ |
| **Copilot CLI** | 3 年 2 月 | v1.0（GA） | 小团队（19人） | ★★★★☆ |
| **Goose** | 1 年 7 月 | v1.28（GA） | 大团队（398人，均衡） | ★★★★☆ |
| **Claude Code** | 1 年 1 月 | v2.1（快速迭代） | Anthropic 内部 | ★★★★★ |
| **Codex CLI** | 11 月 | v0.117（alpha 密集） | 大团队（386人） | ★★★☆☆ |
| **Gemini CLI** | 11 月 | v0.36（preview） | 大团队（447人） | ★★★☆☆ |
| **Qwen Code** | 9 月 | v0.13（nightly） | 大团队（350人） | ★★★☆☆ |
| **Kimi CLI** | 5 月 | v1.25（快速迭代） | 小核心（53人） | ★★☆☆☆ |
