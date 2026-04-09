# 3. Aider 技术架构——开发者参考

> 本文分析 Aider 的核心架构：代理循环、14 种编辑格式、Tree-sitter + PageRank 仓库映射、消息分块、后台压缩、Git 归因系统。这些模式大多与模型无关，可在 Qwen Code 等 Agent 中复现。
>
> **Qwen Code 对标**：Repo Map 自动上下文发现（Qwen Code 无等效机制）、编辑格式多样性（~3 种 vs 14 种）、弱模型分离（成本优化）、Git 归因（企业需求）

## 为什么 Aider 的架构比表面功能更值得研究

Aider 的模型能力取决于后端 LLM（Claude/GPT/Gemini），不是它自身的竞争力。但它的**编辑格式设计**和**仓库映射算法**是经过 43k 用户实战验证的工程方案——这些设计决策背后的 trade-off 分析，对任何 Code Agent 开发者都有参考价值。

### 关键架构差异

| 架构领域 | Aider | Claude Code | Qwen Code | 差距影响 |
|---------|-------|-------------|-----------|---------|
| 代理循环 | 单文件 base_coder.py（2485 行） | QueryEngine + StreamingToolExecutor | CoreToolScheduler | 可维护性 |
| 编辑格式 | 14 种（diff/whole/udiff/patch/architect…） | 1 种（工具调用 Edit） | ~3 种 | 模型适配 |
| 上下文发现 | Repo Map（Tree-sitter + PageRank） | Grep/Glob 工具 | Grep/Glob 工具 | 用户负担 |
| 压缩 | 递归分割摘要（弱模型，后台线程） | 5 层压缩策略 | 单一 70% 压缩 | 会话长度 |
| Git 归因 | 三标志（Author/Committer/Co-authored-by） | Co-authored-by | 基础 | 企业审计 |
| Prompt Cache | Anthropic 缓存控制 + 后台保活 ping | 静态/动态分区 + Schema 锁定 | 基础缓存 | 成本/延迟 |
| 安全 | 无沙箱，依赖 Git undo | 5 层设置 + 沙箱 + 24 种 Hook | 权限 + Hook | 安全性 |

---

## 一、运行时与项目结构

| 项目 | 详情 |
|------|------|
| **语言** | Python 3.9+ |
| **包管理** | pip / pipx / Homebrew |
| **LLM 接入** | LiteLLM（统一 100+ 模型 API） |
| **AST 解析** | Tree-sitter（通过 grep_ast 库） |
| **终端 UI** | Rich（富文本）+ prompt_toolkit（输入/补全） |
| **Git** | GitPython |
| **缓存** | diskcache（SQLite 后端） |
| **源码规模** | ~50 核心文件，~8000 行关键代码 |

### 与 TypeScript 系 Agent 的对比

| 维度 | Aider（Python） | Claude Code（Bun/TS） | Qwen Code（Node/TS） |
|------|----------------|---------------------|---------------------|
| 启动速度 | ~1s | 亚秒（TCP preconnect） | ~1s |
| 单文件打包 | 无（源码直接运行） | esbuild bundle → Rust | esbuild bundle |
| 依赖管理 | pip（可能冲突） | npm（node_modules） | npm |
| 类型安全 | 弱（Python 动态类型） | 强（TypeScript） | 强（TypeScript） |
| 开发速度 | 快（无编译步骤） | 中（需 bundle） | 中（需 bundle） |
| 社区贡献 | 低门槛（Python 普及） | 高门槛（反编译困难） | 低门槛（开源 TS） |

---

## 二、核心代理循环（源码：`base_coder.py`，2485 行）

### 循环流程

```
用户输入
  │
  ├─ [1] format_messages()
  │     ├─ 系统提示（编辑格式专用 Prompt）
  │     ├─ Few-shot 示例（编辑格式示例对）
  │     ├─ 只读文件内容
  │     ├─ Repo Map（Tree-sitter + PageRank 生成）
  │     ├─ 聊天历史（可能已压缩）
  │     ├─ 可编辑文件内容
  │     ├─ 当前用户消息
  │     └─ 提醒消息（reminder）
  │
  ├─ [2] litellm.completion()     ← 流式 API 请求
  │
  ├─ [3] parse response           ← 按当前编辑格式解析
  │     ├─ EditBlockCoder: 解析 <<<<<<< SEARCH / ======= / >>>>>>> REPLACE 块
  │     ├─ WholeFileCoder: 解析完整文件内容
  │     ├─ UnifiedDiffCoder: 解析 @@ hunk @@ 格式
  │     └─ PatchCoder: 解析模糊匹配 patch
  │
  ├─ [4] apply_updates()
  │     ├─ 干运行检查（dry run）
  │     └─ 实际写入文件
  │
  ├─ [5] auto_commit()            ← Git 自动提交 + 归因
  │
  ├─ [6] auto_lint()              ← lint 检查
  │
  ├─ [7] auto_test()              ← 测试运行
  │
  └─ [8] 反思循环
        ├─ lint 失败 → 将错误加入消息，重新请求 LLM 修复
        ├─ test 失败 → 将测试输出加入消息，重新请求 LLM 修复
        └─ 最多重试 3 次
```

### 与 Claude Code 核心循环的关键差异

| 维度 | Aider | Claude Code | 影响 |
|------|-------|-------------|------|
| 工具执行 | 解析完整响应后执行 | StreamingToolExecutor（流式解析+执行） | 延迟 |
| 中途注入 | 不支持 | Mid-Turn Queue Drain | 交互性 |
| 编辑方式 | 文本格式解析（diff/whole/udiff） | 工具调用（Edit tool with JSON） | 可靠性 |
| 反思触发 | lint/test 失败 | 任意工具执行失败 | 覆盖范围 |
| 消息管理 | format_messages() 每次重建 | 增量追加 + 压缩 | 效率 |

**开发者启示**：Aider 的"文本格式解析"方式（让 LLM 输出 diff 文本，然后解析）与 Claude Code 的"工具调用"方式（LLM 调用 Edit tool with JSON 参数）是两种根本不同的编辑范式。文本格式更灵活（14 种格式适配不同模型），但解析失败率更高。工具调用更可靠（JSON Schema 校验），但要求模型支持 function calling。

---

## 三、仓库映射（Repo Map，源码：`repomap.py`，867 行）

Repo Map 是 Aider 最有价值的创新——自动发现与当前任务相关的代码上下文，无需用户手动添加文件。

### 算法流程

```
[1] Tree-sitter AST 解析
    ├─ 扫描仓库所有文件
    ├─ 提取每个文件的定义（def tags）和引用（ref tags）
    └─ 支持 30+ 编程语言

[2] 构建引用图
    ├─ NetworkX MultiDiGraph
    ├─ 节点 = 文件
    ├─ 有向边 = 引用者 → 定义者
    └─ 边权重 = 引用次数

[3] 权重调整
    ├─ 引用者在聊天文件中: 权重 ×50        ← 当前工作最相关
    ├─ 标识符被用户提及: 权重 ×10           ← 用户关注的
    ├─ snake_case/camelCase 且长度 ≥8: ×10  ← 有意义的名称
    ├─ 以 _ 开头（私有）: ×0.1              ← 降低内部实现权重
    └─ 定义超过 5 处（过于通用）: ×0.1       ← 降低通用名称权重

[4] PageRank 排名
    ├─ 个性化向量：聊天文件 + 提及文件
    ├─ nx.pagerank() 计算节点重要度
    └─ 排名分配到具体定义（函数/类/方法）

[5] 输出截断
    ├─ 按排名排序
    ├─ 排除已在聊天中的文件
    └─ 截断到 --map-tokens 预算（默认 1024 tokens）
```

### PageRank 权重设计的工程智慧

| 权重规则 | 倍数 | 设计意图 |
|---------|------|---------|
| 聊天文件引用 | ×50 | 当前正在编辑的文件引用的定义最可能需要 |
| 用户提及的标识符 | ×10 | 用户消息中提到的名称是明确信号 |
| 长名称（≥8 字符） | ×10 | 越具体的名称越有意义（`getUserProfile` vs `get`） |
| 私有标识符 | ×0.1 | 内部实现细节通常不需要暴露给 LLM |
| 过于通用的定义 | ×0.1 | 被定义 5+ 次的名称太泛化，降低噪声 |

### 缓存机制

```
diskcache（SQLite 后端）
  ├─ 键: 文件路径 + mtime
  ├─ 值: 解析后的 tag 列表
  ├─ 版本: CACHE_VERSION=4（版本变更时全部失效）
  └─ 增量更新: 仅重新解析 mtime 变更的文件
```

### Qwen Code 对标：为什么 Repo Map 值得实现

| 场景 | 无 Repo Map（当前 Qwen Code） | 有 Repo Map（Aider） |
|------|------------------------------|---------------------|
| 用户说"修复 login 函数" | 模型需要先 Grep "login"，再 Read 相关文件 | Repo Map 已包含 `auth.py:login()` 的定义和其调用者 |
| 修改一个接口 | 模型不知道谁引用了这个接口 | PageRank 自动排列出引用该接口的文件 |
| 大型仓库导航 | 多轮 Grep/Glob 消耗 token | 1024 token 的 Repo Map 提供结构概览 |

**实现建议**：Qwen Code 可以在启动时或文件变更时运行 Tree-sitter 解析，生成 Repo Map 作为系统提示的一部分。关键参数是 `--map-tokens`（默认 1024）——这是 token 成本和上下文质量的最优平衡点，经过 Aider 社区大量用户验证。

---

## 四、编辑格式系统（14 种）

Aider 的编辑格式系统是对"LLM 应该如何输出代码修改"这个问题的系统性探索。

### 格式分类

| 格式 | Coder 类 | 输出方式 | 适用场景 | 默认模型 |
|------|---------|---------|---------|---------|
| **diff** | EditBlockCoder | SEARCH/REPLACE 块 | 精确局部修改 | Claude Sonnet |
| **whole** | WholeFileCoder | 完整文件内容 | 小文件、弱模型 | Ollama 本地模型 |
| **udiff** | UnifiedDiffCoder | @@ hunk @@ 统一 diff | 大文件修改 | GPT-4 |
| **patch** | PatchCoder | 模糊匹配 patch | 容错性要求高 | 通用 |
| **diff-fenced** | EditBlockFencedCoder | 带 fence 的 SEARCH/REPLACE | 防止格式混乱 | — |
| **architect** | ArchitectCoder | 规划 → 编辑两阶段 | 复杂任务 | 最佳质量 |
| **ask** | AskCoder | 纯文本回答（不编辑） | 代码审查 | — |
| **context** | — | 展示上下文（不编辑） | 调试 | — |
| 其他 6 种 | — | 各种变体 | 特殊场景 | — |

### 编辑格式的工程决策树

```
选择编辑格式
  │
  ├─ 模型支持 function calling?
  │     ├─ 是 → 工具调用方式（Claude Code 路线）
  │     └─ 否 → 文本格式解析（Aider 路线）
  │
  ├─ 使用文本格式时：
  │     ├─ 模型上下文窗口大？ → diff（精确，省 token）
  │     ├─ 模型上下文窗口小？ → whole（整文件，简单但耗 token）
  │     ├─ 模型擅长 diff 格式？ → udiff（GPT-4 偏好）
  │     ├─ 需要容错？ → patch（模糊匹配）
  │     └─ 复杂任务？ → architect（先规划后执行）
  │
  └─ model-settings.yml 为每个模型预设最优格式
```

### Architect 两阶段模式

```
[规划阶段]
  用户请求 → 主模型（如 Claude Opus）
  输出：修改方案（自然语言描述）

[执行阶段]
  修改方案 → 编辑模型（如 Claude Sonnet）
  输出：实际代码修改（按编辑格式）
```

**Qwen Code 对标**：Architect 模式是多 Agent 协作的最简形式——两个模型角色，串行执行。它证明了即使不实现 Claude Code 那种复杂的 Coordinator/Swarm 架构，仅通过"规划与执行分离"也能显著提升复杂任务的质量。Qwen Code 的 Agent Team 可以参考这种轻量方案。

### model-settings.yml

Aider 为每个模型维护最优配置预设：

```yaml
# 源码: aider/resources/model-settings.yml
- name: claude-sonnet-4
  edit_format: diff
  weak_model_name: claude-haiku
  use_repo_map: true
  send_undo_reply: true
  caches_by_default: true
  
- name: gpt-4o
  edit_format: udiff
  weak_model_name: gpt-4o-mini
  use_repo_map: true

- name: ollama/llama3
  edit_format: whole          # 本地模型用 whole 更可靠
  use_repo_map: false         # 本地模型不用 Repo Map（太慢）
```

**Qwen Code 对标**：这种"每个模型一份最优配置"的思路在多模型支持场景下非常有价值。Qwen Code 若支持更多模型，应该建立类似的配置矩阵，而不是让用户自己摸索每个模型的最佳参数。

---

## 五、消息分块（ChatChunks）

Aider 的消息组装不是简单的拼接，而是分块管理，每块有独立的缓存策略：

```
[1] 系统提示               ← 编辑格式专用 Prompt（高缓存命中）
[2] Few-shot 示例           ← 编辑格式示例对（高缓存命中）
[3] 只读文件内容            ← 中频变更
[4] Repo Map               ← 按 PageRank 排名的代码结构（中频变更）
[5] 聊天历史               ← 可能已压缩（高频变更）
[6] 可编辑文件内容          ← 高频变更
[7] 当前用户消息            ← 每次新增
[8] 提醒消息（reminder）    ← 重复关键指令
```

### Prompt Cache 策略

Aider 对 Anthropic 模型使用 `cache_control` 标记：

- 系统提示和示例块标记 `ephemeral` 缓存
- **后台保活 ping**：定期发送空请求维持缓存有效，避免缓存过期导致的 token 重新计算

**与 Claude Code 的对比**：Claude Code 使用静态/动态分区策略——工具 Schema 等不变部分放在静态分区（高缓存命中），对话内容放在动态分区。Aider 的分块粒度更细但管理更手动。

---

## 六、后台压缩（源码：`history.py`，143 行）

### 算法

```
ChatSummary（max_tokens=1024）
  │
  ├─ 检查聊天历史是否接近上下文限制
  │
  ├─ 递归分割摘要：
  │     [1] 将消息列表分成两半
  │     [2] 对前半部分调用弱模型生成摘要
  │     [3] 若摘要仍超 max_tokens，递归分割（最多 3 层深度）
  │
  ├─ 摘要前缀："I spoke to you previously about a number of things.\n"
  │
  └─ 后台线程执行，不阻塞用户输入
```

### 与 Claude Code 5 层压缩的对比

| 维度 | Aider | Claude Code |
|------|-------|-------------|
| 压缩层数 | 1 层（递归摘要） | 5 层（cache_edits → 全量 compact） |
| 执行模型 | 弱模型（便宜） | 主模型 |
| 触发条件 | 接近上下文限制 | 多级阈值 |
| 后台执行 | ✓（独立线程） | ✓ |
| 保留策略 | 最近消息完整，早期压缩 | 逐级升级，从轻到重 |

**Qwen Code 对标**：Aider 的"用弱模型做压缩"是一个高性价比方案。压缩质量不需要最强模型——Haiku/GPT-4o-mini 足以生成合格的历史摘要，且成本降低 90%+。

---

## 七、Git 归因系统（源码：`repo.py`，622 行）

### 三标志归因

```python
# 源码: aider/repo.py — commit() 方法
# 三个独立标志控制 Git 元数据

--attribute-author         # 修改 Author 名为 "User (aider)"
--attribute-committer      # 修改 Committer 名为 "User (aider)"
--attribute-co-authored-by # 添加 Co-authored-by trailer（默认开启）
```

归因优先级逻辑：
- 当 `co-authored-by=True`（默认）时，author/committer 不修改
- 当 `co-authored-by=False` 时，author/committer 默认修改
- 三个标志可独立组合

### Co-authored-by 格式

```
Co-authored-by: aider (claude-sonnet-4) <aider@aider.chat>
```

包含模型名称，这对审计"哪个模型生成了这段代码"至关重要。

### `/undo` 安全链

Aider 以 Git 作为安全网——没有沙箱、没有命令阻止，所有安全依赖于可撤销性：

```python
# aider_commit_hashes: 记录所有 aider 创建的提交 SHA
# /undo 仅允许撤销这个集合中的提交

安全检查:
1. commit in aider_commit_hashes?        → 防止撤销用户自己的提交
2. commit not pushed to remote?           → 防止撤销已共享的提交
3. commit is not merge commit?            → 防止破坏合并历史
4. working tree is clean?                 → 防止丢失未提交的更改
```

**Qwen Code 对标**：Aider 的"Git 即安全网"方案在个人开发场景中是够用的，但在企业场景中不足——误执行 `rm -rf /` 不会被阻止，虽然可以 undo 文件修改但无法恢复 Shell 操作。Qwen Code 的权限规则 + Hook 事件提供了更强的预防性安全。但 Aider 的 Git 归因系统（精确追踪 AI 提交）值得 Qwen Code 参考。

---

## 八、遥测系统（源码：`analytics.py`）

| 维度 | 详情 |
|------|------|
| **平台** | PostHog（活跃），Mixpanel（代码存在但已禁用） |
| **默认** | 关闭（opt-in） |
| **采样率** | 仅 10% 用户被询问是否 opt-in |
| **采集数据** | Python 版本、OS、CPU 架构、aider 版本、模型名称 |
| **不采集** | MAC 地址、主机名、IP、文件内容、代码、git 数据、环境变量 |
| **禁用方式** | `--analytics false` 或 `permanently_disable: true` |

**与 Claude Code 的对比**：Claude Code 的遥测默认开启且数据更丰富（包含 token 使用量、工具调用模式等），用于模型调优。Aider 的遥测最小化，符合开源社区的隐私期望。

---

## 九、架构总结

### Aider 架构的核心设计哲学

| 原则 | 体现 | 权衡 |
|------|------|------|
| **集中优于分散** | base_coder.py 2485 行包含全部核心逻辑 | 易理解但难扩展 |
| **Git 即安全网** | 无沙箱，依赖自动提交 + undo | 简单但不够安全 |
| **多格式适配** | 14 种编辑格式适配 100+ 模型 | 灵活但维护成本高 |
| **弱模型降成本** | 辅助任务用便宜模型 | 省钱但增加复杂度 |
| **自动上下文** | Repo Map 自动发现相关代码 | 智能但消耗 token |

### Qwen Code 可直接参考的 Top 5 设计

| 优先级 | 设计 | 价值 | 实现难度 |
|--------|------|------|---------|
| P0 | Repo Map（Tree-sitter + PageRank） | 自动上下文发现，减少用户手动操作 | 中 |
| P1 | 弱模型分离 | 辅助任务成本降低 60%+ | 小 |
| P1 | model-settings.yml | 多模型场景的最优配置预设 | 小 |
| P2 | Architect 两阶段模式 | 复杂任务质量提升 | 中 |
| P2 | Git 三标志归因 | 企业级 AI 代码溯源 | 小 |
