# Qwen Code (通义灵码 CLI)

**开发者：** 阿里云
**许可证：** Apache-2.0
**仓库：** [github.com/QwenLM/qwen-code](https://github.com/QwenLM/qwen-code)
**文档：** [qwenlm.github.io/qwen-code-docs](https://qwenlm.github.io/qwen-code-docs/zh/)
**Stars：** 约 2k+

## 概述

Qwen Code 是阿里云推出的开源 AI 编程代理，运行在终端中。它针对 Qwen3-Coder 系列模型进行优化，是中国首款由大模型厂商发布的终端编程工具。

## 核心功能

### 基础能力
- **终端原生**：完全在命令行中运行
- **大代码库理解**：能理解复杂的项目结构
- **自动化任务**：自动完成繁琐的开发工作
- **代码生成**：将想法转化为代码
- **代码编辑**：多文件修改能力

### 独特功能
- **基于 Gemini CLI**：修改和增强了 Gemini CLI
- **Qwen3-Coder 优化**：针对 480B 参数 MoE 模型优化
- **免费额度**：每天 2000 次运行
- **中文优化**：对中文开发环境友好
- **阿里云集成**：与阿里云服务深度集成

## 安装

```bash
# 使用 npm（推荐，需要 Node.js 20+）
npm install -g @qwen-code/qwen-code@latest

# 验证安装
qwen --version

# 使用 bun
bun add -g @qwen-code/qwen-code

# 使用 Homebrew（macOS、Linux）
brew install qwen-code

# 配置 API Key
qwen-code --api-key YOUR_API_KEY
```

## 架构

- **语言：** TypeScript
- **主要模型**：Qwen3-Coder (480B MoE)
- **设计模式**：基于 Gemini CLI 改进
- **平台**：macOS、Linux、Windows

## 优势

1. **免费额度高**：每天 2000 次运行
2. **中文友好**：对中文开发环境优化
3. **大厂支持**：阿里云官方支持
4. **开源**：Apache-2.0 许可
5. **本地模型支持**：可运行本地 Qwen 模型

## 劣势

1. **较新项目**：生态系统不如成熟工具
2. **国内限制**：网络访问可能有延迟
3. **文档较少**：中文文档为主，英文资源有限
4. **社区较小**：相比 Claude Code 用户较少

## CLI 命令

```bash
# 启动交互式会话
qwen-code

# 直接提问
qwen-code "解释这段代码的作用"

# 生成代码
qwen-code "创建一个 FastAPI 端点"

# 审查代码
qwen-code "审查 src/ 目录下的代码"

# 使用本地模型
qwen-code --model qwen3-coder-local
```

## 配置

```bash
# ~/.qwen-code/config.json
{
  "model": "qwen3-coder-plus",
  "apiKey": "your-api-key",
  "maxTokens": 4096,
  "temperature": 0.7
}
```

## 使用场景

- **最适合**：中文开发者、阿里云用户
- **适合**：日常编码、代码生成
- **不太适合**：需要极强推理能力的复杂任务

## 模型支持

| 模型 | 说明 | 推荐场景 |
|------|------|----------|
| Qwen3-Coder-Plus | 最新 480B MoE | 复杂任务 |
| Qwen3-Coder-Lite | 轻量级版本 | 快速响应 |
| Qwen3-Coder-Local | 本地运行 | 隐私要求 |

## 与通义灵码的关系

- **通义灵码**：IDE 插件，类似 GitHub Copilot
- **Qwen Code**：CLI 工具，类似 Claude Code
- 两者互补，可同时使用

## 资源链接

- [GitHub](https://github.com/QwenLM/qwen-code)
- [文档](https://qwenlm.github.io/qwen-code-docs/zh/)
- [官网](https://qwen.ai/qwencode)
- [阿里云文档](https://help.aliyun.com/zh/model-studio/qwen-code)
- [示例仓库](https://github.com/QwenLM/qwen-code-examples)

## 相关项目

- [Qwen](https://github.com/QwenLM/Qwen) - 主模型仓库
- [Qwen3-Coder 博客](https://qwenlm.github.io/zh/blog/qwen3-coder/)
