# Kimi CLI (月之暗面)

**开发者：** Moonshot AI (月之暗面)
**许可证：** 开源
**仓库：** [github.com/MoonshotAI/kimi-cli](https://github.com/MoonshotAI/kimi-cli)
**文档：** [moonshotai.github.io/kimi-cli](https://moonshotai.github.io/kimi-cli/zh/)
**状态：** 技术预览版

## 概述

Kimi CLI 是月之暗面推出的终端 AI 编程代理，可帮助完成软件开发任务和终端操作。在 1024 程序员节期间开源，代表了中国国产编程工具生态的升级。

## 核心功能

### 基础能力
- **终端原生**：在命令行中运行
- **代码编辑**：读取和编辑代码
- **命令执行**：执行 shell 命令
- **网页搜索**：搜索和爬取网页内容
- **智能补全**：命令行智能补全

### 独特功能
- **双模式交互**：Shell 风格界面 + AI 助手
- **Ctrl-K 快捷键**：快速切换到智能模式
- **通用命令行代理**：支持各种编程任务
- **文件处理**：强大的文件操作能力

## 安装

```bash
# 1. 先安装 uv 包管理器（如果未安装）
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. 使用 uv 安装 Kimi CLI
uv tool install kimi-cli

# 3. 验证安装
kimi --version

# 首次运行会引导配置
kimi
# 推荐 Kimi Code（自动 OAuth 授权）
# 或输入 API Key
```

## 架构

- **语言**：TypeScript
- **主要模型**：Kimi (Moonshot AI)
- **平台**：macOS、Linux
- **状态**：技术预览版

## 优势

1. **双模式设计**：Shell + AI 智能模式
2. **快捷键支持**：Ctrl-K 快速调用
3. **网页能力**：内置网页搜索和爬取
4. **中文优化**：对中文开发友好
5. **月之暗面支持**：Kimi 模型能力强

## 劣势

1. **预览版本**：功能可能不稳定
2. **仅 macOS/Linux**：暂不支持 Windows
3. **需要会员**：需要 Kimi 会员或 API Key
4. **较新项目**：生态和文档有限

## CLI 命令

```bash
# 启动交互式会话
kimi-cli

# 直接提问
kimi-cli "帮我分析这个项目的结构"

# 生成代码
kimi-cli "创建一个 Python 脚本处理 CSV 文件"

# 使用 Ctrl-K（在 shell 中）
# 按下 Ctrl-K 进入智能模式，输入自然语言命令

# 网页搜索
kimi-cli "搜索最新的 Python 版本信息"
```

## 双模式交互

```
普通 Shell 模式:
$ ls -la
(正常 shell 输出)

按 Ctrl-K 进入智能模式:
> 列出所有 Python 文件并统计行数
(AI 处理并返回结果)

ESC 退出智能模式，返回普通 shell
```

## 配置

```bash
# ~/.kimi-cli/config.json
{
  "model": "moonshot-v1-128k",
  "apiKey": "your-api-key",
  "temperature": 0.7,
  "maxTokens": 4096
}
```

## 使用场景

- **最适合**：中文开发者、Kimi 用户
- **适合**：日常开发、命令行操作
- **不太适合**：生产环境（预览版）

## 系统要求

- **操作系统**：macOS、Linux
- **Node.js**：v16 或更高版本
- **账户**：Kimi 会员或 API Key

## Kimi 模型

| 模型 | 上下文 | 推荐场景 |
|------|--------|----------|
| moonshot-v1-8k | 8K | 简单任务 |
| moonshot-v1-32k | 32K | 中等复杂度 |
| moonshot-v1-128k | 128K | 大文件分析 |

## 资源链接

- [GitHub](https://github.com/MoonshotAI/kimi-cli)
- [中文文档](https://moonshotai.github.io/kimi-cli/zh/)
- [入门指南](https://moonshotai.github.io/kimi-cli/zh/guides/getting-started.html)
- [平台文档](https://platform.moonshot.cn/docs/guide/kimi-cli-support)

## 社区

- [GitHub Issues](https://github.com/MoonshotAI/kimi-cli/issues)
- [GitHub Discussions](https://github.com/MoonshotAI/kimi-cli/discussions)

## 相关项目

- [Kimi API](https://platform.moonshot.cn/) - Kimi API 平台
- [Moonshot AI](https://www.moonshot.cn/) - 月之暗面官网
