# Aider

**开发者：** Paul Gauthier
**许可证：** GPL-3.0
**仓库：** [github.com/Aider-AI/aider](https://github.com/Aider-AI/aider)
**文档：** [aider.chat/docs](https://aider.chat/docs/)
**Stars：** 约 40k+

## 概述

Aider 是一个运行在终端中的 AI 结对编程工具。它是最成熟、经过实战测试的开源编码代理之一，具有出色的 Git 集成。

## 核心功能

### 基础能力
- **Git 原生**：每次更改都被跟踪为 Git 提交
- **自动测试**：每次更改后运行测试/linter
- **多文件编辑**：一次会话中可编辑多个文件
- **仓库映射**：为上下文构建代码库映射
- **可脚本化**：可通过 CLI 或 Python API 脚本化
- **Web 聊天复制粘贴**：易于从 Web 聊天体验迁移

### 独特功能
- **智能上下文管理**：使用仓库映射给 LLM 提供正确的上下文
- **自动提交**：用描述性消息提交更改
- **测试驱动开发**：可自动编写/运行测试
- **多 LLM 支持**：适用于 Claude、GPT-4 和本地模型

## 安装

```bash
# 使用 pip
pip install aider-chat

# 使用 Homebrew
brew install aider

# 使用 pipx（推荐用于隔离）
pipx install aider-chat
```

## 架构

- **语言：** Python
- **支持的模型：**
  - Claude 3.5 Sonnet, Claude Opus
  - GPT-4, GPT-4-turbo
  - 通过 Ollama 的本地模型
  - DeepSeek, OpenAI 兼容端点

## 优势

1. **Git 集成**：同类最佳的 Git 工作流支持
2. **实战验证**：每天被数千开发者使用
3. **优秀文档**：全面的文档和示例
4. **自动修复**：可自动修复测试失败
5. **透明**：显示正在进行的更改
6. **开源**：完全 GPL-3.0 许可

## 劣势

1. **终端专注**：UI 不如商业工具精致
2. **设置复杂度**：需要更多初始配置
3. **Python 生态**：主要关注 Python 项目
4. **GPL 许可证**：可能不适合企业使用

## CLI 命令

```bash
# 在当前目录启动 aider
aider

# 添加特定文件到上下文
aider file1.py file2.py

# 使用特定模型
aider --model claude-3-5-sonnet

# 带 Git 提交消息运行
aider --message "添加错误处理"

# 自动提交模式
aider --auto-commit

# 编辑后运行测试
aider --run-test "pytest tests/"
```

## 配置

```bash
# ~/.aider.conf.yml
model: claude-3-5-sonnet
auto-commit: true
auto-test: true
test-cmd: pytest tests/
```

## 使用场景

- **最适合**：需要 Git 纪律的项目、测试驱动开发
- **适合**：Python 项目、自动重构
- **不太适合**：快速原型开发、非 Git 项目

## 生态系统

- **aider-service**：Web 服务分支
- **aider.el**：Emacs 集成
- **aider-acp**：Zed 编辑器的 Agent Client Protocol 桥接

## 基准测试

- **SWE-bench**：验证集约 45%
- **擅长**：需求明确的专注代码编辑

## 资源链接

- [文档](https://aider.chat/docs/)
- [示例](https://aider.chat/docs/examples.html)
- [GitHub Issues](https://github.com/Aider-AI/aider/issues)
