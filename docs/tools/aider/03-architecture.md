# 3. 技术架构

基于源码分析的 Aider 内部架构详解。

## 项目结构

```
aider/
├── main.py              # 入口，参数解析，编排
├── coders/              # 13+ 编辑格式实现
│   ├── base_coder.py    # 核心代理循环（2485 行）
│   ├── editblock_coder.py   # search/replace 格式
│   ├── wholefile_coder.py   # 整文件替换
│   ├── udiff_coder.py       # unified diff
│   ├── patch_coder.py       # patch 格式
│   ├── architect_coder.py   # 两阶段模式
│   └── *_prompts.py         # 各格式的提示模板
├── models.py            # LLM 集成（1000+ 行）
├── repo.py              # Git 集成，自动提交
├── repomap.py           # AST 仓库映射（600+ 行）
├── commands.py          # 用户命令（/add, /test 等）
├── io.py                # Rich 终端 UI（1000+ 行）
└── resources/
    └── model-settings.yml  # 每个模型的最优配置
```

## 核心代理循环

```
用户输入
  → format_messages() (系统提示 + 示例 + 仓库映射 + 文件 + 历史)
  → send() → litellm.completion() (流式)
  → parse response → apply_updates()
  → apply_edits() (干运行检查 → 实际修改)
  → auto_commit() (Git 提交 + 归因)
  → auto_lint() / auto_test()
  → 反思循环（最多 3 次，修复失败）
```

## Git 集成（源码：`repo.py`、`commands.py`）

### 自动提交机制（`repo.py:commit()`）

- 每次 AI 编辑后自动调用 `auto_commit()`，生成描述性提交消息
- `aider_edits=True` 时标记为 AI 生成的更改，影响归因逻辑
- **归因系统**：三个独立标志控制 Git 元数据
  - `--attribute-author`：修改 Author 名为 `"User Name (aider)"`
  - `--attribute-committer`：修改 Committer 名为 `"User Name (aider)"`
  - `--attribute-co-authored-by`（默认开启）：添加 `Co-authored-by: aider (<model>) <aider@aider.chat>` 尾部
  - 当 `co-authored-by=True` 时，author/committer 默认不修改（co-authored-by 优先）；当 `co-authored-by=False` 时，author/committer 默认修改

### `/commit [msg]` 命令（`commands.py:cmd_commit()`）

- 手动提交外部更改（非 AI 编辑），`aider_edits=False`
- 若提供 `msg` 参数则用作提交消息，否则由 LLM 生成

### `/undo` 命令（`commands.py:raw_cmd_undo()`）

- 仅撤销当前会话中由 Aider 创建的提交（检查 `aider_commit_hashes` 集合）
- 安全检查：不可撤销非 Aider 提交、合并提交、已推送到远程的提交
- 实现方式：对每个受影响文件执行 `git checkout HEAD~1 <file>`，然后 `git reset --soft HEAD~1`
- 若受影响文件有未提交更改，则拒绝操作

### `/diff` 命令（`commands.py:raw_cmd_diff()`）

- 显示自上次消息以来的 diff
- 追踪 `commit_before_message` 列表确定 diff 起点

### `/git <cmd>` 命令

直接执行 Git 命令（通过 `subprocess`，设置 `GIT_EDITOR=true` 避免交互）

## 仓库映射（RepoMap，源码：`repomap.py`）

```
Tree-sitter AST 解析
  → 提取函数/类定义 tags（def/ref）
  → 磁盘缓存（diskcache + SQLite，版本化 CACHE_VERSION=4）
  → NetworkX PageRank 排名
  → TreeContext 输出（文件 + 符号）
  → Token 预算截断（可配置 --map-tokens，默认 1024）
```

### PageRank 排名算法（`get_ranked_tags()`）

1. 使用 Tree-sitter 解析每个文件，提取定义（def）和引用（ref）标签
2. 构建 NetworkX MultiDiGraph：引用者 → 定义者 的有向边，权重为引用次数
3. 边权重加成：
   - 引用者在聊天文件中：权重 ×50
   - 标识符被用户提及：权重 ×10
   - 标识符是 snake_case/kebab-case/camelCase 且长度 ≥8：权重 ×10
   - 标识符以 `_` 开头（私有）：权重 ×0.1
   - 标识符定义超过 5 处（过于通用）：权重 ×0.1
4. 个性化（Personalization）向量：聊天文件和提及文件获得额外权重
5. 运行 `nx.pagerank()` 得到节点排名，将排名分配到具体定义
6. 按排名排序输出，排除已在聊天中的文件

### RepoMap 特性

- 支持 30+ 编程语言（通过 `grep_ast` 的 `filename_to_lang`）
- 智能上下文选择：PageRank 确保与当前工作最相关的符号和文件优先展示
- 增量更新：基于文件 mtime 的缓存机制，仅重新解析变更文件
- 刷新模式：`auto`（按需）或 `always`（每次强制刷新）

## 编辑格式（14 种）

| 格式 | 类 | 说明 | 适用模型 |
|------|---|------|---------|
| **diff** | EditBlockCoder | ORIG/UPD search/replace | Claude Sonnet（默认） |
| **whole** | WholeFileCoder | 整文件替换 | 上下文窗口小的模型 |
| **udiff** | UnifiedDiffCoder | @@ hunk @@ 格式 | GPT-4 |
| **patch** | PatchCoder | 模糊匹配 patch | 通用 |
| **architect** | ArchitectCoder | 规划→编辑两阶段 | 最佳质量 |
| **ask** | AskCoder | 仅问答，不编辑 | 代码审查 |

## 架构师模式（Architect）

两阶段双模型管道：
- **规划模型**（如 Claude Opus）：分析需求，生成修改方案
- **编辑模型**（如 Claude Sonnet）：根据方案执行实际代码修改
- 15 种 Coder 类型支持不同编辑策略

## 消息分块（ChatChunks）

```
系统提示 → 示例 → 只读文件 → 仓库映射 → 历史 → 可编辑文件 → 当前消息 → 提醒
```

- 每个分块独立管理缓存控制
- 昂贵部分（仓库映射）优先缓存

## 后台压缩

递归分割-摘要（recursive split-and-summarize）机制：
- 使用弱模型对历史消息进行摘要压缩
- 当上下文接近 token 限制时自动触发
- 保留最近的完整消息，压缩较早的历史
