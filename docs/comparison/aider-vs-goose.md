# 17. Aider vs Goose：开源代理双雄对比

> Aider（Python，Git 原生，编辑格式之王）vs Goose（Rust，MCP 原生，企业级代理框架）——两个最具影响力的开源 CLI 编程代理的全面对比

## 定位对比

| 维度 | Aider | Goose |
|------|-------|-------|
| **开发者** | Paul Gauthier | Block（原 Square） |
| **许可证** | GPL-3.0 | Apache-2.0 |
| **Stars** | ~42k | ~33k |
| **语言** | Python | Rust |
| **核心代码量** | base_coder.py 2485 行 + 模块 | ~55k 行 Rust |
| **模型支持** | 100+ 模型（LiteLLM） | 58+ 提供商 |
| **架构理念** | 编辑优先，Git 原生 | 工具调用优先，MCP 原生 |
| **客户端** | CLI 单客户端 | CLI + Web + Electron 桌面 |
| **扩展机制** | Linter/测试集成 | MCP 服务器 + Recipe |
| **首次发布** | 2023 年 | 2024 年 |

---

## 1. 架构模式

### Aider：编辑优先架构

Aider 的核心设计围绕**代码编辑**展开。所有交互最终归结为"如何最高效地修改代码文件"。

```
用户输入
  → format_messages()（系统提示 + 示例 + 仓库映射 + 文件 + 历史）
  → send() → litellm.completion()（流式）
  → parse response → apply_updates()
  → apply_edits()（干运行检查 → 实际修改）
  → auto_commit()（Git 提交 + 归因）
  → auto_lint() / auto_test()
  → 反思循环（最多 3 次，修复失败）
```

关键特征：
- **14 种编辑格式**：diff、whole、udiff、patch、architect 等，针对不同模型优化
- **反思循环**：编辑后自动运行 linter/测试，失败则自动修复（最多 3 轮）
- **Architect 模式**：双模型协作——规划模型设计方案，编辑模型执行修改
- **ChatChunks 分块**：系统提示 → 示例 → 只读文件 → 仓库映射 → 历史 → 可编辑文件 → 当前消息

### Goose：MCP 原生工具调用架构

Goose 的核心设计围绕**工具调用**展开。代码编辑只是众多工具能力之一。

```
客户端 (CLI / Desktop / Web)
    │
    ▼
goosed (Axum HTTP 服务器)
    │
    ▼
AgentManager (LRU 缓存, 最多 100 会话)
    │
    ▼
Agent (会话级代理)
    ├── Provider (58+ LLM 提供商)
    ├── ExtensionManager (MCP 客户端管理)
    │   ├── Stdio 传输（子进程）
    │   ├── StreamableHttp 传输
    │   └── Builtin 传输（进程内）
    ├── ToolExecution (权限检查 + 执行)
    └── Scheduler (Cron 定时任务)
```

关键特征：
- **MCP 协议**：所有工具（包括文件编辑）通过 MCP 服务器提供
- **多客户端**：CLI、HTTP 服务器、Electron 桌面三种访问方式
- **Agent Communication Protocol (ACP)**：自研代理通信协议
- **四种运行模式**：Auto、Approve、SmartApprove（默认）、Chat

### 架构差异总结

| 维度 | Aider | Goose |
|------|-------|-------|
| 核心抽象 | Coder（编辑器） | Agent（代理） |
| 编辑方式 | 14 种专用编辑格式 | MCP 工具调用 |
| 服务模式 | 单进程 CLI | 客户端-服务器（goosed） |
| 会话管理 | 基于 Git 历史 | AgentManager（LRU，100 会话） |
| 异步模型 | 同步 Python | Tokio 异步运行时 |
| 进程架构 | 单进程 | 多进程（MCP 子进程） |

---

## 2. 模型灵活性

### Aider：LiteLLM 统一接入 100+ 模型

Aider 通过 LiteLLM 库统一接入所有主流 LLM 提供商，并为每个模型维护**最优配置**。

```yaml
# model-settings.yml 示例
- name: claude-sonnet-4
  edit_format: diff
  weak_model: claude-haiku
  cache_control: true

- name: gpt-4o
  edit_format: udiff
  weak_model: gpt-4o-mini
```

独特能力：
- **弱模型/编辑模型分离**：历史摘要用便宜模型，代码编辑用强模型
- **Prompt 缓存**：Anthropic 缓存控制 + 后台保活 ping，大幅降低成本
- **Lazy/Overeager 修饰符**：控制模型输出完整度和修改范围
- **每模型最优编辑格式**：自动选择最适合该模型的编辑格式

| 模型 | 默认编辑格式 | 弱模型 | 缓存支持 |
|------|-------------|--------|---------|
| Claude Sonnet 4 | diff | Haiku | ✓ |
| Claude Opus | diff | Sonnet | ✓ |
| GPT-4o | udiff | GPT-4o-mini | ✗ |
| Gemini 2.5 | diff | Flash | ✗ |
| DeepSeek | diff | - | ✗ |
| 本地模型 (Ollama) | whole | - | ✗ |

### Goose：多提供商原生集成 58+ 提供商

Goose 直接集成各提供商 API，无需中间抽象层。

| 类别 | 提供商 |
|------|--------|
| **主要** | Anthropic, OpenAI, Google Gemini |
| **云服务** | AWS Bedrock, Azure, GCP Vertex AI, Databricks |
| **推理** | Groq, Cerebras, Together, DeepInfra |
| **兼容** | OpenRouter, LiteLLM, Ollama |
| **其他** | GitHub Copilot, xAI, Venice, Snowflake |

独特能力：
- **本地 AI 推理**：内置 Whisper 语音识别、llama.cpp 本地模型
- **密钥管理**：keyring 系统密钥链集成
- **Token 计算**：tiktoken-rs 精确计算

### 模型灵活性对比

| 维度 | Aider | Goose |
|------|-------|-------|
| 模型数量 | 100+（通过 LiteLLM） | 58+ 提供商 |
| 接入方式 | LiteLLM 统一抽象层 | 各提供商原生 SDK |
| 模型配置 | model-settings.yml 精细调优 | config.yaml 基础配置 |
| 多模型协作 | Architect（规划+编辑）+ 弱模型 | 单模型 |
| 本地模型 | 通过 Ollama | Ollama + 内置 llama.cpp |
| 缓存优化 | Anthropic Prompt 缓存 | 无专用缓存 |

---

## 3. Git 集成

### Aider：业界最佳 Git 集成

Git 是 Aider 的**一等公民**。每次代码修改都自动产生 Git 提交，这是 Aider 最具辨识度的特性。

核心能力：
- **自动提交**：每次编辑自动生成描述性 Git commit
- **归因标记**：提交消息中标注 AI 辅助（`co-authored-by`）
- **一键撤销**：`/undo` 命令回退上次 AI 修改
- **仓库映射**：Tree-sitter AST 解析，理解项目结构
- **脏文件检测**：编辑前检查未提交更改
- **Git 历史感知**：利用 Git 历史上下文理解代码演进

```bash
# Aider 的 Git 工作流
aider file.py
> 修改 file.py 中的函数

# 自动生成：
# git commit -m "feat: 重构处理函数以支持异步"
# co-authored-by: aider
```

### Goose：基础 Git 支持

Goose 的 Git 支持依赖内置 developer 扩展中的 shell 命令，而非原生集成。

- 可通过 MCP 工具执行 `git` 命令
- 无自动提交机制
- 无仓库结构感知
- 无 Git 历史利用

### Git 集成对比

| 维度 | Aider | Goose |
|------|-------|-------|
| 自动提交 | ✓（每次编辑） | ✗ |
| 归因标记 | ✓（co-authored-by） | ✗ |
| 一键撤销 | ✓（/undo） | ✗（需手动 git revert） |
| 仓库映射 | ✓（Tree-sitter AST） | ✗ |
| 脏文件检测 | ✓ | ✗ |
| Git 历史感知 | ✓ | ✗ |
| 集成深度 | 原生内置 | Shell 命令调用 |

**结论**：Git 集成是 Aider 的**绝对优势领域**，Goose 在这方面差距明显。

---

## 4. MCP 支持

### Aider：无原生 MCP 支持

Aider 的设计早于 MCP 协议，其扩展能力基于传统的命令集成（linter、测试命令）和文件操作。

- 不支持 MCP 服务器连接
- 不支持 MCP 工具发现
- 扩展依赖命令行集成（`--lint-cmd`、`--test-cmd`）
- 无标准化的第三方工具接入方式

### Goose：MCP 原生架构

Goose **从底层基于 MCP 构建**，所有工具能力都是 MCP 服务器。

```yaml
# Goose 扩展配置
extensions:
  - name: developer    # 内置 MCP 服务器
    type: builtin
  - name: memory       # 内置 MCP 服务器
    type: builtin
  - name: custom-tool  # 外部 MCP 服务器
    type: stdio
    cmd: npx
    args: ["-y", "@example/mcp-server"]
```

MCP 能力：
- **三种传输**：Stdio（子进程）、StreamableHttp、Builtin（进程内）
- **动态工具发现**：运行时加载 MCP 服务器提供的工具列表
- **rmcp SDK**：Rust 原生 MCP 实现，高性能
- **扩展管理**：`goose extension list/add` 命令行管理

### MCP 支持对比

| 维度 | Aider | Goose |
|------|-------|-------|
| MCP 支持 | ✗ 无 | ✓ 原生架构 |
| 工具发现 | 静态内置 | 动态 MCP 发现 |
| 第三方扩展 | 命令行集成 | MCP 服务器生态 |
| 传输协议 | N/A | Stdio + HTTP + Builtin |
| 扩展开发 | Python 脚本 | 任何语言（MCP 标准） |

**结论**：MCP 支持是 Goose 的**绝对优势领域**，Aider 在这方面完全空白。

---

## 5. 扩展系统

### Aider：Linter/测试集成

Aider 的扩展方式聚焦于**代码质量保证流程**的集成。

```bash
# Aider 的扩展点
aider --lint-cmd "ruff check" --test-cmd "pytest tests/"
```

- **Linter 集成**：编辑后自动运行，失败则自动修复
- **测试集成**：编辑后自动运行测试套件
- **反思循环**：lint/test 失败时自动修复（最多 3 轮）
- **Web 抓取**：`/web` 命令抓取 URL 内容作为上下文
- **命令系统**：`/add`、`/drop`、`/test`、`/undo` 等内置命令

### Goose：Recipe + Extension 系统

Goose 提供两套互补的扩展机制。

**Recipe 系统**（任务模板）：
```yaml
# recipe.yaml
name: 代码审查
description: 自动审查 PR
steps:
  - prompt: "审查以下 PR 的代码质量..."
    params:
      pr_url:
        type: string
        description: "PR 链接"
```

- YAML/JSON 定义可复用任务模板
- 参数化支持（JSON Schema 验证）
- Cron 定时调度执行

**Extension 系统**（MCP 工具）：
```bash
goose extension list          # 列出已安装扩展
goose extension add <name>    # 安装新扩展
```

- 内置扩展：developer、memory 等
- 外部 MCP 服务器：任何语言开发
- 多格式文件解析：DOCX、PDF、XLSX

### 扩展系统对比

| 维度 | Aider | Goose |
|------|-------|-------|
| 扩展理念 | 代码质量流程集成 | 通用工具平台 |
| Linter 集成 | ✓ 原生 + 自动修复 | 通过 MCP 工具 |
| 测试集成 | ✓ 原生 + 反思循环 | 通过 MCP 工具 |
| 任务模板 | ✗ | ✓ Recipe 系统 |
| 定时调度 | ✗ | ✓ Cron 调度 |
| 第三方工具 | 有限 | MCP 生态（丰富） |
| 开发门槛 | 低（命令行配置） | 中（MCP 服务器开发） |

---

## 6. 上下文管理

### Aider：RepoMap（Tree-sitter 索引）

Aider 的上下文管理以**仓库映射**为核心，是其最重要的技术创新之一。

```
Tree-sitter AST 解析
  → 提取函数/类定义（tags）
  → 磁盘缓存（diskcache + SQLite）
  → 按提及标识符排名
  → 树形结构输出（文件 + 符号）
  → Token 预算截断（可配置 --map-tokens）
```

- **30+ 语言支持**：覆盖主流编程语言的 AST 解析
- **智能排名**：根据当前对话引用的标识符，优先展示相关文件
- **增量更新**：文件变化时自动刷新缓存
- **Token 预算**：`--map-tokens` 参数控制仓库映射的 token 消耗
- **ChatChunks 分块**：按优先级分层管理上下文各部分的缓存

### Goose：会话管理

Goose 的上下文管理基于**会话状态**和**工具调用结果**。

- **AgentManager**：LRU 缓存，最多 100 并发会话
- **Tree-sitter 支持**：Go/Java/JS/Kotlin/Python/Ruby/Rust/Swift/TS 的 AST 解析
- **Memory 扩展**：跨会话记忆持久化
- **多格式解析**：DOCX、PDF、XLSX 文件内容提取
- **Token 计算**：tiktoken-rs 精确计算上下文用量

### 上下文管理对比

| 维度 | Aider | Goose |
|------|-------|-------|
| 仓库映射 | ✓ 核心功能（RepoMap） | ✗ 无等效功能 |
| AST 解析 | Tree-sitter（30+ 语言） | Tree-sitter（9 语言） |
| 缓存策略 | diskcache + SQLite | LRU 会话缓存 |
| 智能排名 | ✓ 按标识符引用排名 | ✗ |
| Token 预算 | ✓ 可配置 | tiktoken-rs 计算 |
| 文件格式 | 代码文件 | 代码 + DOCX/PDF/XLSX |
| 跨会话记忆 | ✗ | ✓ Memory 扩展 |

---

## 7. 安装与易用性

### Aider

```bash
# 三种安装方式
pip install aider-chat        # pip
pipx install aider-chat       # pipx（推荐）
brew install aider             # Homebrew

# 启动
aider                          # 交互式
aider file1.py file2.py       # 指定文件
aider --model claude-sonnet-4  # 指定模型
aider --architect              # Architect 模式
aider --message "修复 bug"     # 非交互式
```

配置：
```yaml
# ~/.aider.conf.yml
model: claude-sonnet-4
edit-format: diff
auto-commits: yes
auto-test: yes
test-cmd: pytest tests/
```

### Goose

```bash
# 两种安装方式
brew install block/tap/goose   # Homebrew（推荐）
# 或从 GitHub Release 下载二进制

# 启动
goose                          # 交互式
goose --model claude-opus-4    # 指定模型
goose run recipe.yaml          # 执行 Recipe
goose config                   # 配置向导
```

配置：
```yaml
# ~/.config/goose/config.yaml
provider: anthropic
model: claude-sonnet-4
mode: smart_approve
extensions:
  - name: developer
    type: builtin
```

### 安装与易用性对比

| 维度 | Aider | Goose |
|------|-------|-------|
| 安装方式 | pip/pipx/brew | brew/二进制下载 |
| 依赖 | Python 运行时 | 无（单二进制） |
| 启动速度 | 较慢（Python 启动） | 快（Rust 原生） |
| 配置复杂度 | 低（YAML 配置） | 中（YAML + 扩展配置） |
| 学习曲线 | 平缓（专注编辑） | 较陡（概念多） |
| 文档质量 | 优秀（aider.chat） | 一般（文档覆盖有限） |
| 上手难度 | 低 | 中 |

---

## 8. 性能

### SWE-bench 评测

Aider 在 SWE-bench 评测中表现突出，长期维护自己的排行榜。

| 指标 | Aider | Goose |
|------|-------|-------|
| SWE-bench 公开成绩 | ✓ 定期发布 | 有限公开数据 |
| 排行榜 | 自建排行榜（aider.chat） | 无 |
| 代码编辑准确率 | 高（14 种格式优化） | 一般（通用工具调用） |

### 运行时性能

| 指标 | Aider | Goose |
|------|-------|-------|
| 启动时间 | 较慢（Python，~2-3s） | 快（Rust，<1s） |
| 内存占用 | 较高（Python 运行时） | 低（Rust 原生） |
| 并发能力 | 单会话 | 多会话（最多 100） |
| 二进制大小 | N/A（解释型） | 单二进制分发 |

### Token 效率

| 指标 | Aider | Goose |
|------|-------|-------|
| Prompt 缓存 | ✓ Anthropic 缓存优化 | ✗ |
| 弱模型分离 | ✓ 节省 token 成本 | ✗ |
| 仓库映射预算 | ✓ 可配置 token 预算 | ✗ |
| Token 优化程度 | 高 | 一般 |

---

## 选型建议

| 使用场景 | 推荐工具 | 原因 |
|----------|----------|------|
| **Git 密集型项目** | Aider | 自动提交、归因、撤销，Git 集成业界最佳 |
| **测试驱动开发** | Aider | 原生 linter/test 集成 + 反思循环 |
| **多模型切换** | Aider | 100+ 模型 + 每模型最优编辑格式 |
| **成本敏感** | Aider | Prompt 缓存 + 弱模型分离 |
| **MCP 生态集成** | Goose | MCP 原生架构，无缝对接生态 |
| **企业部署** | Goose | Apache-2.0 许可 + Rust 性能 + 安全设计 |
| **自动化流水线** | Goose | Recipe + Cron 调度 |
| **多客户端需求** | Goose | CLI + Web + Desktop |
| **文档处理** | Goose | 内置 DOCX/PDF/XLSX 解析 |
| **简单代码修改** | Aider | 上手简单，专注编辑 |
| **复杂工作流编排** | Goose | Recipe 模板 + 扩展系统 |

### 一句话总结

| Agent | 一句话定位 |
|------|-----------|
| **Aider** | 最好的 AI 结对编程工具——专注代码编辑，Git 集成无人能及 |
| **Goose** | 最灵活的 AI 代理框架——MCP 原生，企业级，可扩展性强 |

---

## 结论

Aider 和 Goose 代表了开源 AI 编程代理的两种截然不同的设计哲学：

**Aider 是"编辑器"**——它的全部设计都围绕"如何最高效地修改代码"。14 种编辑格式、Tree-sitter 仓库映射、自动 Git 提交、反思循环，每个特性都服务于代码编辑这个核心目标。如果你的工作主要是写代码、改代码、提交代码，Aider 是无可争议的最佳选择。

**Goose 是"代理框架"**——它的设计目标是"通用 AI 代理平台"。MCP 原生架构意味着代码编辑只是众多能力之一，Recipe 系统支持复杂工作流编排，多客户端架构适合团队协作。如果你需要一个能做很多事情的 AI 代理，而不仅仅是编辑代码，Goose 提供了更大的可能性。

两者并非互相替代，而是互补关系。在实际开发中，完全可以在代码编辑场景用 Aider，在复杂自动化场景用 Goose，各取所长。

| 最终对比 | Aider | Goose |
|----------|-------|-------|
| 代码编辑能力 | ★★★★★ | ★★★☆☆ |
| Git 集成 | ★★★★★ | ★★☆☆☆ |
| 模型灵活性 | ★★★★★ | ★★★★☆ |
| MCP 生态 | ☆☆☆☆☆ | ★★★★★ |
| 扩展性 | ★★★☆☆ | ★★★★★ |
| 性能 | ★★★☆☆ | ★★★★★ |
| 易用性 | ★★★★☆ | ★★★☆☆ |
| 企业友好度 | ★★☆☆☆ | ★★★★★ |
