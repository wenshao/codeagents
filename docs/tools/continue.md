# Continue

**开发者：** Continue Dev
**许可证：** Apache-2.0
**仓库：** [github.com/continuedev/continue](https://github.com/continuedev/continue)
**文档：** [docs.continue.dev](https://docs.continue.dev)
**Stars：** 约 27k+

## 概述

Continue 是一个开源 AI 编程助手，最初作为 IDE 扩展，现在提供 CLI 功能。以其可扩展性和 CI/CD 集成而闻名。

## 核心功能

### 基础能力
- **IDE 扩展**：VS Code、JetBrains 支持
- **CLI 访问**：自动化命令行界面
- **源码控制的 AI 检查**：CI 流水线中可强制执行
- **代码审查机器人**：AI 驱动的 PR 审查
- **可定制代理**：为特定任务配置代理
- **多模型**：支持各种 AI 提供商

### 独特功能
- **CI/CD 集成**：在 GitHub Actions 中使用 AI
- **文档代理**：自动生成/更新文档
- **可配置**：基于 YAML 的配置
- **gh/glab 集成**：与 GitHub/GitLab CLI 配合工作

## 安装

```bash
# VS Code 扩展
code --install-extension Continue.continue

# Python 包用于 CLI
pip install continue-cli

# 或使用桌面应用
# 从 continue.dev 下载
```

## 架构

- **语言：** TypeScript
- **支持的模型：**
  - OpenAI (GPT-4)
  - Anthropic (Claude)
  - 本地模型 (Ollama)
  - 自定义提供商

## 优势

1. **CI/CD 集成**：在编码代理中独一无二
2. **源码控制配置**：AI 提示在 git 中
3. **多模型**：灵活的提供商支持
4. **大社区**：23k+ GitHub stars
5. **可扩展**：插件系统

## 劣势

1. **IDE 优先**：CLI 是 IDE 扩展的补充
2. **配置复杂性**：需要更多设置
3. **专注较少**：试图做所有事情

## CLI 命令

```bash
# Continue CLI
continue-cli

# 运行特定任务
continue-cli --task "重构这个文件"

# CI/CD 模式
continue-ci --pr-number 123

# 启用 GitHub CLI 访问
continue-config enable-gh
```

## 配置

```yaml
# ~/.continue/config.yaml
models:
  - name: claude-opus-4
    provider: anthropic

slackBotToken: ${SLACK_TOKEN}
github:
  enabled: true
```

## 使用场景

- **最适合**：CI/CD 自动化、PR 审查
- **适合**：想要 CLI 自动化的 IDE 用户
- **不太适合**：纯终端工作流

## 资源链接

- [CLI 指南](https://docs.continue.dev/guides/cli)
- [GitHub](https://github.com/continuedev/continue)
- [文档](https://docs.continue.dev)
