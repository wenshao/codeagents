# Qwen Code /review 使用指南

> 用一个命令完成代码审查——5 个 AI Agent 并行审查 + linter 自动检测 + 一键修复。

## 快速开始

```bash
# 审查本地未提交的修改
/review

# 审查一个 PR
/review 123

# 审查 PR 并发布 inline 评论
/review 123 --comment

# 审查跨仓库 PR（自动进入轻量模式）
/review https://github.com/other-org/repo/pull/456

# 审查单个文件
/review src/utils/auth.ts
```

## 它做了什么

输入 `/review` 后，Qwen Code 自动执行以下流程：

```
1. 确定范围     — 解析参数，创建临时 worktree（不影响你的工作区）
2. 加载规则     — 读取项目审查规范（.qwen/review-rules.md 等）
3. 运行 linter  — TypeScript/Python/Rust/Go/Java/C++ 自动检测，零 AI 成本
4. 5 个 Agent   — 并行审查正确性、安全、质量、性能、构建测试
5. 验证 + 去重  — 批量确认每个发现是否真实
6. 反向审计     — 扫描是否有遗漏
7. 输出结果     — 分 Critical / Suggestion / Nice to have 三级
```

整个过程固定 7 次 AI 调用，不管发现多少问题。

## 使用场景

### 场景一：提交前自查

```bash
# 写完代码后
/review
```

审查你所有未提交的修改。如果没有改动，会直接告诉你不需要审查。

### 场景二：审查 PR

```bash
/review 42
```

自动创建临时 worktree，在隔离环境中审查 PR 的 diff——你当前正在编辑的文件不受影响。

审查完成后 Qwen Code 会提示：

- `fix these issues` — 自动修复发现的问题
- `post comments` — 发布 inline 评论到 PR

按 Tab 接受建议即可。

### 场景三：审查并直接评论 PR

```bash
/review 42 --comment
```

审查完成后自动在 PR 上发布 inline 评论。只有高置信度的 Critical 和 Suggestion 会被发布——linter 警告和不确定的发现只显示在终端，不发到 PR。

### 场景四：审查别人仓库的 PR

```bash
/review https://github.com/openai/codex/pull/789
```

自动检测这是跨仓库 PR，进入轻量模式——通过 `gh pr diff` 获取 diff 进行 AI 审查，但跳过 linter、构建测试和 autofix（本地没有代码）。

### 场景五：审查单个文件

```bash
/review src/services/auth.ts
```

如果文件有未提交的修改，审查 diff；没有修改则审查当前状态。

## 自定义审查规则

在项目根目录创建 `.qwen/review-rules.md`：

```markdown
## 项目审查规范

- 所有公开 API 必须有 JSDoc 注释
- 禁止使用 any 类型
- 数据库查询必须使用参数化 SQL
- React 组件必须使用 memo 包裹
```

也兼容 `copilot-instructions.md` 和 `AGENTS.md` 中的 `## Code Review` 章节。

> 安全说明：审查 PR 时，规则从 base branch 读取（不是 PR 分支），防止恶意 PR 篡改审查标准。

## 增量审查

第二次审查同一个 PR 时：

- **有新 commit** → 自动执行全量审查
- **没有新 commit + 同一模型** → 跳过，显示 "No new changes since last review"
- **没有新 commit + 切换了模型** → 执行全量审查（"second opinion"）
- **没有新 commit + `--comment`** → 强制执行（你要发评论）

缓存存储在 `.qwen/review-cache/`。

## Autofix

审查发现问题后，终端会提示 `fix these issues`（按 Tab）：

1. Agent 逐个修复每个 Critical/Suggestion 级别的问题
2. 每个修复自动验证（重新运行 linter/typecheck）
3. 修复后 commit 到 PR 分支并 push

**注意**：即使所有问题都修复了，Qwen Code 也不会自动 approve PR——远程代码可能还没更新。

## 审查报告

每次审查自动保存为 Markdown：

```
.qwen/reviews/2026-04-10-pr-42.md
.qwen/reviews/2026-04-10-local.md
```

终端关掉也不会丢失审查结论。

## 发现级别

| 级别 | 含义 | PR 评论？ |
|------|------|:---------:|
| **Critical** | 有 bug、安全漏洞、数据丢失风险 | ✅ 高置信度才发 |
| **Suggestion** | 可改进但不是错误 | ✅ 高置信度才发 |
| **Nice to have** | 锦上添花 | ❌ 仅终端 |
| **Needs Human Review** | Agent 不确定 | ❌ 仅终端 |

设计原则：**宁可少报，不误报**。不确定的问题不发到 PR，避免开发者对 AI 评论产生疲劳。

## 支持的 linter

Step 3 自动检测项目使用的工具：

| 语言 | 检测方式 |
|------|---------|
| TypeScript/JavaScript | `package.json` 的 lint script / `tsconfig.json` / `.eslintrc*` |
| Python | `pyproject.toml` / `ruff.toml` / `setup.cfg` |
| Rust | `Cargo.toml`（`cargo clippy`） |
| Go | `go.mod`（`go vet`） |
| Java | `pom.xml` / `build.gradle` |
| C++ | `CMakeLists.txt`（`clang-tidy`） |

也可以从 `.github/workflows/ci.yml` 自动发现项目的 lint/test 命令——零配置。

## 常见问题

**Q: 审查一次要多少 token？**

固定 7 次 LLM 调用，与发现数量无关。典型的 PR 审查消耗 ~50K-100K input token。

**Q: 可以用不同模型审查同一个 PR 吗？**

可以。切换模型后再次 `/review 42`，系统检测到 model 不同会自动执行全量审查。

**Q: worktree 没清理怎么办？**

下次审查同一个 PR 时会自动清理上次残留的 worktree。也可以手动：`git worktree remove .qwen/tmp/review-pr-42 --force`。

**Q: 怎么跳过 linter？**

目前不支持跳过。如果 linter 执行失败（如依赖未安装），系统会自动跳过并继续 LLM 审查。

---

*适用于 Qwen Code v0.14.3+。*
