# agents-metadata.json Schema 说明

> 本文档说明 `docs/data/agents-metadata.json` 的字段结构、用途和维护约定。
>
> 目标：让维护者知道每个字段的含义、哪些属于动态数据、哪些属于静态事实，以及何时应该更新。

## 顶层结构

```json
{
  "schema_version": 1,
  "last_updated": "2026-03-30",
  "maintainer_note": "...",
  "agents": [
    {
      "id": "claude-code",
      "name": "Claude Code",
      "category": "deep-analysis",
      "license": "专有",
      "developer": "Anthropic",
      "implementation_language": "Rust",
      "runtime": "Bun（内嵌）/ 原生二进制",
      "package_ecosystem": "npm",
      "stars": "83k",
      "downloads": {
        "type": "npm_weekly",
        "value": "1020万",
        "as_of": "2026-03-26"
      },
      "pricing_summary": "$20-200 / API 按量",
      "free_tier": "无",
      "evidence": {
        "status": "complete",
        "source_type": "binary-analysis",
        "evidence_path": "docs/tools/claude-code/EVIDENCE.md",
        "last_verified": "2026-03-26"
      }
    }
  ]
}
```

## 顶层字段

| 字段 | 类型 | 必填 | 含义 |
|------|------|------|------|
| `schema_version` | number | 是 | schema 版本号，用于后续字段演进 |
| `last_updated` | string (`YYYY-MM-DD`) | 是 | 数据文件最后一次整体更新日期 |
| `maintainer_note` | string | 否 | 给维护者的说明 |
| `agents` | array | 是 | Agent 元数据列表 |

## Agent 对象字段

| 字段 | 类型 | 必填 | 动态/静态 | 含义 |
|------|------|------|-----------|------|
| `id` | string | 是 | 静态 | 稳定标识符，建议 kebab-case |
| `name` | string | 是 | 静态 | 面向文档显示的 Agent 名称 |
| `category` | string | 是 | 半静态 | 当前文档覆盖层级，如 `deep-analysis` / `single-file` |
| `license` | string | 是 | 半静态 | 许可证类型 |
| `developer` | string | 是 | 静态 | 开发者/组织 |
| `implementation_language` | string | 是 | 静态 | 主要实现语言 |
| `runtime` | string | 是 | 半静态 | 运行时或分发形态 |
| `package_ecosystem` | string | 是 | 半静态 | npm / pypi / desktop / none 等 |
| `stars` | string | 否 | 动态 | 社区热度指标，建议保持与外部来源一致 |
| `downloads` | object | 否 | 动态 | 下载量信息 |
| `pricing_summary` | string | 否 | 动态 | 定价摘要，适合汇总页使用 |
| `free_tier` | string | 否 | 动态 | 免费层摘要 |
| `evidence` | object | 是 | 半静态 | 证据完备度与入口 |

## downloads 对象

| 字段 | 类型 | 必填 | 含义 |
|------|------|------|------|
| `type` | string | 是 | 指标类型，如 `npm_weekly` / `pypi_monthly` / `none` / `unknown` |
| `value` | string | 是 | 下载量展示值，如 `1020万`、`—` |
| `as_of` | string (`YYYY-MM-DD`) | 是 | 该下载量的统计时间 |

## evidence 对象

| 字段 | 类型 | 必填 | 含义 |
|------|------|------|------|
| `status` | string | 是 | `complete` / `partial` / `single-file-only` |
| `source_type` | string | 是 | `source-analysis` / `binary-analysis` / `summary-analysis` / `official-docs` |
| `evidence_path` | string | 是 | 对应证据文档路径 |
| `last_verified` | string (`YYYY-MM-DD`) | 是 | 最近一次证据验证日期 |

## 推荐取值

### `category`

- `deep-analysis`：已有目录级多文件分析
- `single-file`：目前只有单文件综述

### `downloads.type`

- `npm_weekly`
- `pypi_monthly`
- `none`
- `unknown`

### `evidence.status`

- `complete`
- `partial`
- `single-file-only`

### `evidence.source_type`

- `source-analysis`
- `binary-analysis`
- `summary-analysis`
- `official-docs`

## 维护约定

### 1. 哪些情况需要更新 `last_updated`

以下任一情况都应更新顶层 `last_updated`：
- 批量更新 Stars / 下载量 / 免费层 / 定价摘要
- 新增 Agent
- 修改 evidence 状态或最后验证日期

### 2. 哪些情况需要更新 `docs/data/CHANGELOG.md`

以下情况建议同步记录：
- 动态数据变化
- 字段结构变化
- 批量文档收敛到数据层

### 3. 哪些情况需要同步检查其他文档

当下列字段变化时，应同步检查：

| 字段 | 建议同步检查 |
|------|-------------|
| `stars` / `downloads` | `README.md`, `docs/SUMMARY.md`, `docs/comparison/features.md` |
| `pricing_summary` / `free_tier` | `docs/comparison/pricing.md`, `README.md`, `docs/SUMMARY.md` |
| `runtime` / `implementation_language` | `docs/comparison/system-requirements.md`, `README.md` |
| `evidence.*` | `docs/evidence-index.md`, `docs/comparison/privacy-telemetry.md` |

## 校验建议

提交前运行：

```bash
python3 scripts/check_all.py
```

如需单独排查：

```bash
python3 scripts/check_data_schema.py
python3 scripts/check_repo_consistency.py
python3 scripts/check_stale_data.py
```

> `check_stale_data.py` 目前为告警型检查，主要用于提示潜在漂移，不默认作为阻断条件。
