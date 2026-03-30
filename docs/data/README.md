# docs/data

本目录存放需要跨多个文档复用、且容易过时的数据源。

## 文件说明

- `agents-metadata.json`
  - 统一维护 Agent 的动态指标和基础元数据
  - 包括：Stars、下载量、免费层、定价摘要、证据状态、最后验证日期
- `SCHEMA.md`
  - 说明 `agents-metadata.json` 的字段定义、推荐取值和维护约定
- `agents-metadata.schema.json`
  - 机器可校验的 JSON Schema，用于脚本校验字段结构
- `CHANGELOG.md`
  - 记录动态数据层的更新时间、来源、调整范围和维护备注

## 使用原则

### 1. 区分静态事实与动态事实

- **静态事实**：实现语言、架构模式、是否为分叉、证据路径
- **动态事实**：Stars、下载量、价格、版本数、启动时间、趋势

### 2. 先看 schema，再改数据

修改 `agents-metadata.json` 前，建议先阅读 [`SCHEMA.md`](./SCHEMA.md)。结构校验由 [`agents-metadata.schema.json`](./agents-metadata.schema.json) 和 `python3 scripts/check_data_schema.py` 提供。

### 3. 动态事实必须带时间戳

所有动态数据都应有明确时间基准：
- 优先使用字段内的 `as_of` 或 `last_verified`
- 对于 `stars` 这类紧凑展示字段，统一以顶层 `last_updated` 作为批次时间基准

```json
{
  "stars": "83k",
  "downloads": {
    "type": "npm_weekly",
    "value": "1020万",
    "as_of": "2026-03-26"
  }
}
```

### 4. 汇总页尽量引用数据源，而不是手工散落维护

以下页面应优先从本目录读取或至少手动同步校验：

- `README.md`
- `docs/SUMMARY.md`
- `docs/comparison/features.md`
- `docs/comparison/pricing.md`
- `docs/comparison/privacy-telemetry.md`
- `docs/comparison/system-requirements.md`
- `docs/tools/README.md`

### 5. 证据状态标准

- `complete`：有完整多文件分析，且存在 `EVIDENCE.md`
- `partial`：有目录级分析，但证据仍不完整或主要来自二进制/外部线索
- `single-file-only`：目前只有单文件综述，没有目录级深挖

## 维护建议

- 每次批量更新 Stars / 下载量 / 定价后，同步更新 `last_updated`
- 每次发生动态数据变更时，同时更新 `docs/data/CHANGELOG.md`
- 每次新增 Agent 后，同时补充此数据文件
- 提交前运行：

```bash
python3 scripts/check_all.py
```

如需单独执行，也可以使用：

```bash
python3 scripts/check_data_schema.py
python3 scripts/check_repo_consistency.py
python3 scripts/check_stale_data.py
```

> **说明**：`check_stale_data.py` 当前为“告警型检查”，用于提示可能的漂移或过期信息；是否阻断提交应由维护者结合上下文判断。
