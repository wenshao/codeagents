# 1. Qwen Code 概述——贡献者视角

> **核心定位**：Gemini CLI fork + 阿里云增强。了解我们做了什么、还差什么、下一步怎么做。
>
> **改进路线**：[240 项 Claude Code 对比](../../comparison/qwen-code-improvement-report.md) | [42 项上游 backport](../../comparison/qwen-code-gemini-upstream-report.md)

## 项目信息

- **开发者**：阿里云（Qwen 团队）
- **许可证**：Apache-2.0
- **仓库**：[github.com/QwenLM/qwen-code](https://github.com/QwenLM/qwen-code)
- **文档**：[qwenlm.github.io/qwen-code-docs](https://qwenlm.github.io/qwen-code-docs/zh/)
- **版本**：v0.14.1
- **上游**：Gemini CLI v0.8.2（2025-10-23 fork）

## 一、我们做对了什么（独有优势）

这些是 Qwen Code 独立发展后新增的、竞品没有的能力：

| 能力 | 实现 | 竞品状态 |
|------|------|---------|
| **多 Provider 内容生成** | Anthropic / OpenAI / DashScope / DeepSeek / OpenRouter / ModelScope | Claude Code 仅 Claude，Gemini CLI 仅 Gemini |
| **免费 OAuth 额度** | 通义账号 1000 次/天免费 | 竞品均需付费或自带 API Key |
| **Arena 多模型竞赛** | 多模型在隔离 worktree 中竞争执行 | 竞品无 |
| **CoreToolScheduler** | Agent/Task 工具并行 + 其他工具串行 | Claude Code 全量 StreamingToolExecutor；Gemini CLI 全串行 |
| **规则权限系统** | L3→L4→L5 多层权限评估 | Claude Code 内置权限；Gemini CLI 仅 IDE 层 |
| **分离重试预算** | 内容/流异常/速率限制分别计数 | 竞品统一重试 |
| **三格式扩展兼容** | Qwen 原生 + Claude 插件转换 + Gemini 扩展转换 | 竞品不互通 |
| **6 语言国际化** | 中/英/日/德/俄/葡 | Claude Code 仅英文 |
| **Java SDK** | TypeScript + Java 双 SDK | 竞品仅 TS/Python |

## 二、已知差距

### vs Claude Code（差距最大的领域）

| 领域 | 差距 | 优先级 | 进展 |
|------|------|--------|------|
| 上下文压缩 | 单一 70% vs 5 层递增 | P0 | — |
| Fork Subagent | 从零开始 vs 继承上下文 | P0 | PR#2936 open |
| 崩溃恢复 | 无 vs 3 种检测 + 合成续行 | P0 | — |
| Mid-Turn Queue Drain | 无 vs 工具间检查输入 | P0 | **PR#2854 ✓ 已合并** |
| 记忆系统 | 简单笔记 vs CLAUDE.md + Auto Dream | P1 | — |
| ToolSearch 延迟加载 | 全量加载 vs 按需搜索 | P1 | — |
| 工具并行 | Agent 工具并行 vs 全部并行 | P1 | PR#2864 open |
| Hook 事件 | ~12 种 vs 27 种 | P2 | — |

### vs 上游 Gemini CLI（fork 后新增）

| 领域 | 差距 | 优先级 | 上游版本 |
|------|------|--------|---------|
| 渲染防闪烁 | 无 SlicingMaxSizedBox | P0 | v0.34 (2026-03) |
| Shell buffer 上限 | 无 10MB 截断 | P0 | v0.34 |
| 环境变量净化 | 无 | P0 | v0.35 |
| LRU 文本缓存 | 无 | P1 | v0.34 |
| Edit 模糊匹配 | 仅精确 | P1 | v0.35 |
| OS 级 sandbox | 无 | P1 | v0.30-v0.36 |
| /rewind 回退 | 无 | P1 | v0.27 |

> 完整列表见 [上游 backport 报告](../../comparison/qwen-code-gemini-upstream-report.md)

## 三、核心功能

### 基础能力
- **终端 UI**：Ink 6.2 + React 19
- **16 个内置工具**：Edit、WriteFile、ReadFile、Grep、Glob、Shell、TodoWrite、SaveMemory、Agent、Skill、ExitPlanMode、WebFetch、WebSearch、ListFiles、LSP、AskUserQuestion
- **MCP 支持**：Stdio/SSE/Streamable-HTTP + OAuth
- **LSP 集成**：实验性（`--experimental-lsp`）
- **6 语言 UI**：中/英/日/德/俄/葡
- **IDE 集成**：VS Code + Zed 扩展

### 独特功能
- **Arena 模式**：多模型竞争执行
- **免费 OAuth**：通义账号 1000 次/天
- **三格式扩展兼容**：Qwen + Claude + Gemini
- **/btw 旁问**：不中断主对话的快速提问
- **/insight 代码洞察**：分析代码库生成洞察
- **Compact/Verbose 模式**：PR#2770 工具输出显示控制

### 与 Gemini CLI 上游的差异

| 类别 | Qwen Code 新增 | 移除/替换 |
|------|---------------|----------|
| 认证 | Qwen OAuth2 + PKCE | — |
| 模型 | DashScope/DeepSeek/OpenRouter/Anthropic | — |
| 功能 | Arena 竞赛、Agent Team (PR#2886)、Fork Subagent (PR#2936) | — |
| 扩展 | Claude 插件转换器 | — |
| SDK | Java SDK + Web UI | — |
| UI | 6 语言国际化、Compact/Verbose | Google 品牌 |
| 遥测 | 阿里云 RUM | Google Clearcut |

## 四、安装

```bash
# 一键安装（推荐）
curl -fsSL https://qwen-code-assets.oss-cn-hangzhou.aliyuncs.com/installation/install-qwen.sh | bash

# npm
npm install -g @qwen-code/qwen-code@latest

# Homebrew
brew install qwen-code

# 验证
qwen --version
```

## 五、模型支持

| 提供商 | 默认模型 | 认证方式 | 免费额度 |
|--------|---------|---------|---------|
| **Qwen OAuth** | qwen3.5-plus | 浏览器 OAuth | 1000 次/天 |
| DashScope | qwen3-coder-plus | API Key | 按量 |
| Anthropic | Claude 系列 | API Key | 无 |
| Google | Gemini 系列 | API Key | 有限 |
| 自定义 | OpenAI 兼容 | API Key | 取决于 Provider |

## 六、资源链接

- [GitHub](https://github.com/QwenLM/qwen-code) | [文档](https://qwenlm.github.io/qwen-code-docs/zh/) | [官网](https://qwen.ai/qwencode) | [用户指南](../../guides/qwen-code-user-guide.md)
