# 贡献指南

感谢你对本项目的关注！本文档提供了贡献指南。

## 贡献方式

### 1. 添加新工具

如果有我们没有涵盖的 Code Agent CLI 工具：

1. 检查是否符合标准：
   - CLI 优先或有显著 CLI 功能
   - AI 驱动的编码辅助
   - 活跃开发或有重要用户群

2. 创建新工具文档：
   ```
   docs/tools/tool-name.md
   ```

3. 遵循[工具模板](#工具模板)

4. 更新 README 和工具索引

### 2. 更新现有文档

- 添加新功能到工具描述
- 用新数据更新基准测试
- 修正不准确之处
- 提高清晰度
- 如果涉及动态指标（Stars、下载量、价格、验证日期），优先更新 `docs/data/agents-metadata.json`
- 修改数据层前，先核对 `docs/data/SCHEMA.md`
- 如果动态数据发生变更，同步更新 `docs/data/CHANGELOG.md`
- 如果涉及证据完备度变化，同步更新 `docs/evidence-index.md`
- 提交前优先运行统一检查：`python3 scripts/check_all.py`
- 如需单独执行，可运行：`python3 scripts/check_data_schema.py`、`python3 scripts/check_repo_consistency.py` 和 `python3 scripts/check_stale_data.py`

### 3. 添加示例

添加基于真实经验的示例：
- 常见工作流
- 配置代码片段
- 问题解决方法

### 4. 分享你的经验

根据你的经验创建指南：
- 迁移指南
- 最佳实践
- 工具组合
- 用例研究

## 工具模板

添加新工具时，使用此模板：

```markdown
# 工具名称

**开发者：** 公司/作者
**许可证：** MIT/Apache/专有
**仓库：** [github.com/user/repo](https://github.com/user/repo)
**文档：** [https://tool.dev/docs](https://tool.dev/docs)
**Stars：** 约 Xk+

## 概述

工具功能的简要描述和主要关注点。

## 核心功能

### 基础能力
- 功能 1
- 功能 2
- 功能 3

### 独特功能
- 独特功能 1
- 独特功能 2

## 安装

```bash
# 安装命令
```

## 架构

- **语言：** Python/Rust/TypeScript/Go
- **主要模型：** Claude/GPT-4/Gemini/等
- **设计模式：** ReAct/Plan-Act/等

## 优势

1. 优势 1
2. 优势 2
3. 优势 3

## 劣势

1. 劣势 1
2. 劣势 2
3. 劣势 3

## CLI 命令

```bash
# 示例命令
```

## 使用场景

- **最适合**：使用场景 1
- **适合**：使用场景 2
- **不太适合**：使用场景 3

## 资源链接

- [文档](链接)
- [GitHub](链接)
```

## 指南原则

### 准确性

- 从官方来源验证信息
- 包含命令前先测试
- 及时更新过时信息
- 为基准数据引用来源

### 中立性

- 客观呈现工具
- 承认优势和劣势
- 避免推销语言
- 不贬低竞争工具

### 完整性

- 包含优势和劣势
- 涵盖安装和基本用法
- 链接到官方资源
- 提供对比上下文

### 清晰性

- 为开发者编写
- 尽可能避免行话
- 解释技术术语
- 使用示例

## 提交流程

1. Fork 仓库
2. 为更改创建分支
3. 进行更改
4. 测试任何命令/示例
5. 提交 Pull Request

## Pull Request 检查清单

- [ ] 遵循模板（如果添加工具）
- [ ] 链接正确且有效
- [ ] 命令已测试
- [ ] 信息准确
- [ ] 写作清晰中立
- [ ] 无不必要的格式更改
- [ ] 动态数据已同步到 `docs/data/agents-metadata.json`（如适用）
- [ ] 已核对 `docs/data/SCHEMA.md`（如适用）
- [ ] 动态数据变更已记录到 `docs/data/CHANGELOG.md`（如适用）
- [ ] 证据状态已同步到 `docs/evidence-index.md`（如适用）
- [ ] 已运行 `python3 scripts/check_all.py`
- [ ] 如有需要，已分别运行 `python3 scripts/check_data_schema.py`、`python3 scripts/check_repo_consistency.py` 和 `python3 scripts/check_stale_data.py`

## 我们希望覆盖的领域

- 更多真实世界示例
- 性能分析
- 集成指南
- 安全考虑
- 企业部署
- 自定义工具开发
- 基准方法论

## 问题？

在进行重大更改之前，请打开 issue 进行讨论。

## 许可证

通过贡献，你同意你的贡献将在 MIT 许可证下授权。
