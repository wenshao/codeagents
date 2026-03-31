# 1. Qwen Code 概述

**开发者：** 阿里云（Qwen 团队）
**许可证：** Apache-2.0
**仓库：** [github.com/QwenLM/qwen-code](https://github.com/QwenLM/qwen-code)
**文档：** [qwenlm.github.io/qwen-code-docs](https://qwenlm.github.io/qwen-code-docs/zh/)
**版本：** v0.13.0（源码: `packages/cli/package.json`）
**最后更新：** 2026-03

> **免责声明**: 以下数据基于 2026-03-28 源码分析（commit `0b8ff03f8`），可能已过时。

## 概述

Qwen Code 是阿里云推出的开源 AI 编程代理，运行在终端中。基于 Google Gemini CLI 分叉并大幅增强，针对 Qwen3-Coder 系列模型优化，是中国首款由大模型厂商发布的终端编程工具。支持 6+ 提供商（Qwen OAuth/DashScope/ModelScope/Anthropic/Google/自定义 OpenAI 兼容端点），提供免费 OAuth 额度和完整的多语言国际化（6 种语言）。

AGENTS.md 声明：*"This project is based on Google Gemini CLI with adaptations to better support Qwen-Coder models."*

主要特点：
- **Gemini CLI 分叉**：继承 Gemini CLI 核心架构，新增 Arena/扩展系统/多提供商等能力
- **免费 OAuth 额度**：通义账号每天 1000 次免费请求，零门槛入门
- **16 个内置工具**：文件编辑、Shell 执行、Grep 搜索、Web 抓取/搜索、LSP 等
- **41 斜杠命令**：覆盖会话管理、Arena 模式、扩展管理、多语言切换等
- **多提供商**：Qwen OAuth（免费）、DashScope、ModelScope、Anthropic、Gemini、Vertex AI、自定义
- **完整 SDK**：TypeScript SDK + Java SDK，支持编程式集成
- **扩展兼容**：可转换 Claude Code 插件和 Gemini CLI 扩展格式

## 核心功能

### 基础能力
- **终端原生 UI**：基于 Ink 6.2 + React 19 的终端渲染（源码: `packages/cli/src/gemini.tsx`）
- **16 个内置工具**：Edit、WriteFile、ReadFile、Grep、Glob、Shell、TodoWrite、SaveMemory、Agent、Skill、ExitPlanMode、WebFetch、WebSearch、ListFiles、LSP、AskUserQuestion
- **MCP 集成**：Stdio/SSE/Streamable-HTTP 三种传输协议 + MCP OAuth 认证（源码: `packages/core/src/tools/mcp-client.ts`）
- **LSP 集成**：语言服务器协议支持代码智能
- **多语言 UI**：中/英/日/德/俄/葡 6 种语言（源码: `packages/cli/src/i18n/`）
- **IDE 集成**：VS Code 扩展 + Zed 编辑器扩展

### 独特功能
- **Arena 模式**：多模型在隔离 Git worktree 中竞争执行同一任务，用户选择最佳结果（源码: `packages/core/src/agents/arena/ArenaManager.ts`）
- **三格式扩展兼容**：Qwen 原生 + Claude Code 插件转换器 + Gemini CLI 扩展转换器
- **免费 OAuth 额度**：通义账号 OAuth2 设备码流程 + PKCE 认证，每天 1000 次免费
- **多语言国际化**：6 种 UI 语言，对中文开发者极友好
- **/btw 旁问**：不中断主对话的快速侧边提问
- **/insight 代码洞察**：分析代码库生成个性化编程洞察
- **Hook 系统**：14 种事件类型，支持命令式 Hook
- **Skill 系统**：bundled/project/user/extension 四级技能

### 与 Gemini CLI 的差异

| 类别 | 新增 | 移除 |
|------|------|------|
| 遥测 | 阿里云 RUM 管道 | Google Clearcut 分析 |
| 认证 | Qwen OAuth2 + PKCE | — |
| 模型 | DashScope/DeepSeek/OpenRouter/ModelScope + Anthropic | — |
| 功能 | Arena 多模型竞争 | — |
| 扩展 | Claude Code 插件转换器 | — |
| SDK | Java SDK + Web UI | — |
| UI | 6 种语言国际化 | Google 品牌标识 |

## 安装

```bash
# 一键安装脚本（推荐，Linux/macOS）
curl -fsSL https://qwen-code-assets.oss-cn-hangzhou.aliyuncs.com/installation/install-qwen.sh | bash

# Windows（以管理员身份运行 CMD）
curl -fsSL -o %TEMP%\install-qwen.bat https://qwen-code-assets.oss-cn-hangzhou.aliyuncs.com/installation/install-qwen.bat && %TEMP%\install-qwen.bat

# npm（需要 Node.js 20+）
npm install -g @qwen-code/qwen-code@latest

# bun
bun add -g @qwen-code/qwen-code

# Homebrew（macOS、Linux）
brew install qwen-code

# 验证安装
qwen --version
```

> **VS Code 扩展（Beta）**：Qwen Code Companion 提供图形化 IDE 体验，从 VS Code Marketplace 安装即可在侧边栏中使用。

## 模型支持

| 提供商 | 默认模型 | 认证方式 | 免费额度 |
|--------|---------|---------|---------|
| **Qwen OAuth** | coder-model (qwen3.5-plus) | 浏览器 OAuth | 1000 次/天 |
| DashScope | qwen3-coder-plus | API Key | 按量付费 |
| ModelScope | qwen3-coder 系列 | API Key | 按量付费 |
| Anthropic | Claude 系列 | API Key | 无 |
| Google | Gemini 2.0 Flash 等 | API Key | 有限免费 |
| Vertex AI | Gemini 系列 | Service Account | 无 |
| 自定义 | OpenAI 兼容端点 | API Key | 取决于提供商 |

> 源码: `packages/core/src/core/contentGenerator.ts`（AuthType 枚举: openai, qwen-oauth, gemini, vertex-ai, anthropic）

## 优势

1. **免费额度**：OAuth 登录即享每天 1000 次免费请求
2. **多语言 UI**：6 种语言本地化，对中文开发者极友好
3. **多提供商**：不锁定单一模型，灵活切换
4. **完整 SDK**：TypeScript + Java SDK，支持编程式集成
5. **大厂支持**：阿里云官方维护，持续更新
6. **扩展兼容**：可转换 Claude/Gemini 扩展格式
7. **Arena 创新**：多模型竞争执行，提升输出质量

## 劣势

1. **基于分叉**：部分变量名/结构仍带 Gemini 痕迹
2. **较新项目**：生态系统不如 Claude Code/Aider 成熟
3. **文档较少**：英文资源有限
4. **社区较小**：相比 Claude Code/Aider 用户较少

## 使用场景

- **最适合**：中文开发者、需要免费额度的用户、阿里云生态用户
- **适合**：日常编码、多提供商切换、SDK 集成
- **不太适合**：需要极强推理能力的复杂任务（受限于模型能力）

## 相关项目

- **通义灵码**：IDE 插件，类似 GitHub Copilot，实时补全。与 Qwen Code CLI 互补
- [Google Gemini CLI](https://github.com/google-gemini/gemini-cli)：上游项目

## 资源链接

- [GitHub](https://github.com/QwenLM/qwen-code)
- [文档](https://qwenlm.github.io/qwen-code-docs/zh/)
- [官网](https://qwen.ai/qwencode)
- [阿里云文档](https://help.aliyun.com/zh/model-studio/qwen-code)
