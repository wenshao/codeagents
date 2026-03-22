# Aider

**开发者：** Paul Gauthier
**许可证：** GPL-3.0
**仓库：** [github.com/Aider-AI/aider](https://github.com/Aider-AI/aider)
**文档：** [aider.chat/docs](https://aider.chat/docs/)
**Stars：** 约 40k+

## 概述

Aider 是最成熟的开源 AI 结对编程工具，以 Git 原生设计和丰富的编辑格式著称。基于 Python 构建，通过 LiteLLM 支持 100+ 模型，提供 14 种编辑格式适配不同 LLM 的能力特点。核心代理循环在 `base_coder.py` 中实现（2485 行），是所有编辑器的基类。

## 核心功能

### 基础能力
- **Git 原生**：每次更改自动提交，带描述性消息和归因
- **14 种编辑格式**：whole、diff、udiff、patch、architect 等
- **100+ 模型**：通过 LiteLLM 统一接入
- **仓库映射**：Tree-sitter AST 解析，智能上下文选择
- **自动测试**：编辑后自动运行 linter 和测试
- **反思循环**：最多 3 次自我修正（lint 失败、测试失败时自动修复）

### 独特功能
- **Architect 模式**：两阶段编辑——规划模型生成方案，编辑模型执行修改
- **Prompt 缓存**：Anthropic 缓存控制，后台保活 ping
- **弱模型/编辑模型分离**：用便宜模型做历史摘要，用强模型做代码编辑
- **Lazy/Overeager 修饰符**：控制模型完整度（防止 stub）和范围（防止多余修改）
- **扩展思维支持**：自动处理 `<thinking>` 标签

## 技术架构（源码分析）

### 项目结构

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

### 核心代理循环

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

### 编辑格式

| 格式 | 类 | 说明 | 适用模型 |
|------|---|------|---------|
| **diff** | EditBlockCoder | ORIG/UPD search/replace | Claude Sonnet（默认） |
| **whole** | WholeFileCoder | 整文件替换 | 上下文窗口小的模型 |
| **udiff** | UnifiedDiffCoder | @@ hunk @@ 格式 | GPT-4 |
| **patch** | PatchCoder | 模糊匹配 patch | 通用 |
| **architect** | ArchitectCoder | 规划→编辑两阶段 | 最佳质量 |
| **ask** | AskCoder | 仅问答，不编辑 | 代码审查 |

### 仓库映射（RepoMap）

```
Tree-sitter AST 解析
  → 提取函数/类定义（tags）
  → 磁盘缓存（diskcache + SQLite）
  → 按提及标识符排名
  → 树形结构输出（文件 + 符号）
  → Token 预算截断（可配置 --map-tokens）
```

- 支持 30+ 编程语言
- 智能上下文选择：优先包含被引用的文件
- 增量更新：文件变化时自动刷新

### 消息分块（ChatChunks）

```
系统提示 → 示例 → 只读文件 → 仓库映射 → 历史 → 可编辑文件 → 当前消息 → 提醒
```

- 每个分块独立管理缓存控制
- 昂贵部分（仓库映射）优先缓存

## 安装

```bash
# pip
pip install aider-chat

# pipx（推荐，隔离环境）
pipx install aider-chat

# Homebrew
brew install aider
```

## 支持的模型

通过 LiteLLM 支持 100+ 模型，每个模型在 `model-settings.yml` 中有最优配置：

| 模型 | 默认编辑格式 | 弱模型 | 缓存支持 |
|------|-------------|--------|---------|
| Claude Sonnet 4 | diff | Haiku | ✓ |
| Claude Opus | diff | Sonnet | ✓ |
| GPT-4o | udiff | GPT-4o-mini | |
| GPT-4 | udiff | GPT-3.5-turbo | |
| Gemini 2.5 | diff | Flash | |
| DeepSeek | diff | - | |
| 本地模型 (Ollama) | whole | - | |

## 优势

1. **Git 集成最佳**：自动提交 + 归因 + 描述性消息
2. **编辑格式丰富**：14 种格式适配不同模型特点
3. **仓库映射**：AST 级别的智能上下文选择
4. **反思循环**：自动修复 lint/测试失败
5. **实战验证**：每天数千开发者使用，40k+ Stars
6. **Prompt 缓存**：Anthropic 缓存优化，降低成本

## 劣势

1. **GPL 许可**：企业使用受限
2. **Python 生态**：启动速度不如 Rust/Go 工具
3. **终端 UI**：不如 Ink/React 工具精致
4. **无 MCP 支持**：不支持模型上下文协议扩展

## CLI 命令

```bash
# 启动交互式会话
aider

# 指定文件
aider file1.py file2.py

# 使用特定模型
aider --model claude-sonnet-4

# Architect 模式
aider --architect

# 带消息运行（非交互）
aider --message "添加错误处理"

# 自动提交 + 测试
aider --auto-commit --auto-test --test-cmd "pytest tests/"

# 会话内命令
/add file.py        # 添加文件到上下文
/drop file.py       # 移除文件
/test pytest tests/  # 运行测试
/undo               # 撤销上次提交
/model gpt-4o       # 切换模型
/web https://...     # 抓取 URL 内容
```

## 配置

```yaml
# ~/.aider.conf.yml 或 <git_root>/.aider.conf.yml
model: claude-sonnet-4
edit-format: diff
auto-commits: yes
auto-test: yes
test-cmd: pytest tests/
cache-prompts: yes
map-tokens: 1024
attribute-co-authored-by: yes
```

## 使用场景

- **最适合**：需要 Git 纪律的项目、测试驱动开发、多模型切换
- **适合**：代码审查（ask 模式）、自动重构、结对编程
- **不太适合**：非 Git 项目、快速原型（开销大）、IDE 集成

## 资源链接

- [文档](https://aider.chat/docs/)
- [示例](https://aider.chat/docs/examples.html)
- [GitHub](https://github.com/Aider-AI/aider)
- [模型排行榜](https://aider.chat/docs/leaderboards/)
