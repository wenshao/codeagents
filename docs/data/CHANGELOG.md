# docs/data 变更日志

> 用于记录动态数据层的更新时间、更新范围、来源与备注。
>
> 目标：降低“数字改了但没人知道改了什么”的维护成本。

## 记录格式

每次更新建议记录以下内容：

| 日期 | 文件 | 更新范围 | 数据来源 | 备注 |
|------|------|---------|---------|------|
| 2026-03-30 | `agents-metadata.json` | Stars / 下载量 / 证据状态 | npm Registry API / PyPI Stats / `gh api` | 初始化统一数据层 |

## 变更记录

| 日期 | 文件 | 更新范围 | 数据来源 | 备注 |
|------|------|---------|---------|------|
| 2026-03-31 | `agents-metadata.json` | Stars 全量更新（GitHub API）；新增 github_repo 防错字段 | GitHub REST API（17 个 repo） | 回滚 OpenCode 至 133k（anomalyco/opencode）；新增 Cursor/Cline/Oh My OpenAgent/OpenHands/SWE-agent/Warp Stars |
| 2026-03-31 | `README.md` | 快速对比表增加 Stars 列，数据同步 | `agents-metadata.json` | 按 Stars 降序重排 |
| 2026-03-31 | `evolution-community.md` | 项目概览 Stars 更新，新增 7 个 Agent | GitHub REST API | 采集时间更新为 2026-03-31 |
| 2026-03-30 | `agents-metadata.json` | 初始化统一数据层；补充 Agent 元数据、免费层、证据状态、最后验证日期 | npm Registry API / PyPI Stats / `gh api` / 各 Agent 文档与 EVIDENCE.md | 首次建立 `docs/data/` |
| 2026-03-30 | `README.md`, `docs/SUMMARY.md` | 收敛高频变化的 Stars / 下载量 / 免费层引用，改为指向数据层 | `docs/data/agents-metadata.json` | 降低重复维护 |
| 2026-03-30 | `scripts/check_stale_data.py`, `scripts/check_all.py` | 新增动态数据漂移检查与统一检查入口 | 本仓库维护脚本 | 用于提交前校验 |

## 使用建议

- 每次批量更新动态数据时，同时更新本文件
- 如果只是修正文案、不涉及真实数据变更，可在备注中标明“文案收敛”
- 对外引用动态数字时，优先从 `docs/data/agents-metadata.json` 读取，再在本文件记录更新时间
