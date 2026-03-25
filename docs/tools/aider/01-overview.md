# 1. Aider 概述

**开发者：** Paul Gauthier
**许可证：** GPL-3.0
**仓库：** [github.com/Aider-AI/aider](https://github.com/Aider-AI/aider)
**文档：** [aider.chat/docs](https://aider.chat/docs/)
**Stars：** 约 40k+
**最后更新：** 2026-03

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

## 安装

```bash
# pip
pip install aider-chat

# pipx（推荐，隔离环境）
pipx install aider-chat

# Homebrew
brew install aider
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

# 会话内命令见"命令详解"章节
```

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

## 使用场景

- **最适合**：需要 Git 纪律的项目、测试驱动开发、多模型切换
- **适合**：代码审查（ask 模式）、自动重构、结对编程
- **不太适合**：非 Git 项目、快速原型（开销大）、IDE 集成

## 资源链接

- [文档](https://aider.chat/docs/)
- [示例](https://aider.chat/docs/examples.html)
- [GitHub](https://github.com/Aider-AI/aider)
- [模型排行榜](https://aider.chat/docs/leaderboards/)
