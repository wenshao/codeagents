# 证据索引（Evidence Index）

> 本页用于汇总每个 Agent 的证据完备度、分析方式、对应文档入口，以及建议的更新频率。
>
> **目标**：把“这条结论来自哪里、验证到什么程度、何时需要复核”显式化，降低仓库维护成本。

## 证据状态定义

| 状态 | 含义 | 维护要求 |
|------|------|---------|
| `complete` | 已有目录级分析，且存在 `EVIDENCE.md` 或等价证据文档 | 核心结论需可回溯到源码、反编译结果或官方文档 |
| `partial` | 有多文件分析，但关键结论仍部分依赖外部材料、二进制侧信号或待补证据 | 应补足缺失证据，避免长期停留 |
| `single-file-only` | 当前仅有单文件综述，缺少目录级深挖与证据索引 | 若该 Agent 重要性提升，应优先升级为目录级分析 |

## 证据来源类型

| 类型 | 说明 |
|------|------|
| `source-analysis` | 直接基于开源仓库源码分析 |
| `binary-analysis` | 基于二进制、反编译、strings、CLI 帮助输出等证据 |
| `official-docs` | 主要基于官方文档、定价页、产品文档 |
| `summary-analysis` | 综述级整理，证据粒度较粗 |

## Agent 证据矩阵

| Agent | 分析深度 | 证据状态 | 证据来源 | 证据入口 | 最后验证 | 建议复核频率 |
|------|---------|---------|---------|---------|---------|-------------|
| Claude Code | 多文件 | `complete` | `binary-analysis` | `docs/tools/claude-code/EVIDENCE.md` | 2026-03-26 | 月度 |
| Copilot CLI | 多文件 | `complete` | `binary-analysis` | `docs/tools/copilot-cli/EVIDENCE.md` | 2026-03-26 | 月度 |
| Codex CLI | 多文件 | `complete` | `binary-analysis` | `docs/tools/codex-cli/EVIDENCE.md` | 2026-03-26 | 月度 |
| Gemini CLI | 多文件 | `complete` | `source-analysis` | `docs/tools/gemini-cli/EVIDENCE.md` | 2026-03-26 | 月度 |
| Qwen Code | 多文件 | `complete` | `source-analysis` | `docs/tools/qwen-code/EVIDENCE.md` | 2026-03-26 | 月度 |
| Aider | 多文件 | `complete` | `source-analysis` | `docs/tools/aider/EVIDENCE.md` | 2026-03-26 | 月度 |
| Kimi CLI | 多文件 | `complete` | `source-analysis` | `docs/tools/kimi-cli/EVIDENCE.md` | 2026-03-26 | 月度 |
| OpenCode | 多文件 | `complete` | `source-analysis` | `docs/tools/opencode/EVIDENCE.md` | 2026-03-26 | 月度 |
| Goose | 多文件 | `complete` | `source-analysis` | `docs/tools/goose/EVIDENCE.md` | 2026-03-26 | 月度 |
| Qoder CLI | 多文件 | `partial` | `binary-analysis` | `docs/tools/qoder-cli/EVIDENCE.md` | 2026-03-26 | 双周 |
| Cline | 单文件 | `single-file-only` | `summary-analysis` | `docs/tools/cline.md` | 2026-03-26 | 季度 |
| Continue | 单文件 | `single-file-only` | `summary-analysis` | `docs/tools/continue.md` | 2026-03-26 | 季度 |
| Cursor CLI | 单文件 | `single-file-only` | `summary-analysis` | `docs/tools/cursor-cli.md` | 2026-03-26 | 季度 |
| OpenHands | 单文件 | `single-file-only` | `summary-analysis` | `docs/tools/openhands.md` | 2026-03-26 | 季度 |
| SWE-agent | 单文件 | `single-file-only` | `summary-analysis` | `docs/tools/swe-agent.md` | 2026-03-26 | 季度 |
| Warp | 单文件 | `single-file-only` | `summary-analysis` | `docs/tools/warp.md` | 2026-03-26 | 季度 |
| mini-swe-agent | 单文件 | `single-file-only` | `summary-analysis` | `docs/tools/mini-swe-agent.md` | 2026-03-26 | 低优先级 |

## 优先补强建议

### 第一优先级

1. **Qoder CLI**
   - 已有目录级分析，但证据完备度仍弱于主要开源 Agent
   - 建议补更多 CLI 参数、配置格式、遥测/安全、命令行为证据

2. **Continue / Cline / OpenHands**
   - 影响力较大，但目前仍以单文件综述为主
   - 建议至少升级为“概述 + 架构 + 命令/工具 + EVIDENCE.md”四件套

### 第二优先级

3. **Cursor CLI / Warp**
   - 用户关注度高，但闭源成分多
   - 建议补官方文档证据与行为验证边界，明确哪些结论来自源码、哪些来自官方表述

## 维护工作流建议

每次新增或更新 Agent 文档时，建议同步完成以下动作：

1. 更新 `docs/data/agents-metadata.json`
2. 更新本页中的证据状态、最后验证日期、复核频率
3. 如涉及关键结论变动，同步检查：
   - `README.md`
   - `docs/SUMMARY.md`
   - `docs/tools/README.md`
   - `docs/comparison/features.md`
   - `docs/comparison/privacy-telemetry.md`
   - `docs/comparison/pricing.md`
   - `docs/comparison/system-requirements.md`

## 读者说明

> `single-file-only` 不代表内容错误，只表示证据粒度和可审计性弱于目录级分析。
>
> 对闭源 Agent，应尽量明确“可验证边界”：哪些是通过行为、CLI 帮助、二进制分析得出，哪些仅来自官方文档。
