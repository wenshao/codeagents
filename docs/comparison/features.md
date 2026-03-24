# 功能对比矩阵

本文档提供 Code Agent CLI 工具的详细横向对比。

## 快速参考表

| 功能 | Claude Code | Aider | Copilot CLI | SWE-agent | Cline | Goose | OpenCode | Continue | Warp | Gemini CLI | OpenHands | Cursor | Qwen Code | Kimi CLI |
|---------|------------|-------|-------------|-----------|-------|-------|----------|----------|------|------------|----------|--------|-----------|----------|
| **开源** | | ✓ | | ✓ | ✓ | ✓ | ✓ | ✓ | | ✓ | ✓ | | ✓ | ✓ |
| **免费层级** | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| **多模型** | | ✓ | | ✓ | | ✓ | ✓ | ✓ | ✓ | | ✓ | ✓ | ✓ | |
| **Git 集成** | ✓ | ✓ | ✓ | | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | | ✓ | ✓ | ✓ |
| **MCP 支持** | ✓ | | | | ✓ | ✓ | ✓ | | ✓ | ✓ | | ✓ | ✓ | |
| **IDE 集成** | ✓ | | | ✓ | ✓ | | | ✓ | | | | ✓ | ✓ | |
| **CLI 优先** | ✓ | ✓ | ✓ | ✓ | | ✓ | ✓ | | ✓ | ✓ | | | ✓ | ✓ |
| **终端原生** | ✓ | ✓ | ✓ | | | ✓ | ✓ | | | ✓ | | | ✓ | ✓ |

## 详细对比

### 模型支持

| 工具 | Claude | GPT-4 | Gemini | 本地模型 | 说明 |
|------|--------|-------|--------|----------|------|
| Claude Code | ✓ | | | | 仅 Claude |
| Aider | ✓ | ✓ | | ✓ | 通过 Ollama |
| Copilot CLI | | ✓ | | | 仅 GPT |
| Cursor | ✓ | ✓ | ✓ | | 多提供商 |
| SWE-agent | ✓ | ✓ | | ✓ | 灵活 |
| Cline | ✓ | | | | 仅 Claude |
| Goose | ✓ | ✓ | ✓ | | 多提供商 |
| OpenCode | ✓ | ✓ | ✓ | | 100+ 提供商（models.dev 动态加载） |
| Continue | ✓ | ✓ | | ✓ | 灵活 |
| Warp | ✓ | ✓ | | | 多个 |
| Gemini CLI | | | ✓ | | 仅 Gemini |
| OpenHands | ✓ | ✓ | ✓ | ✓ | 灵活 |
| Qwen Code | ✓ | ✓ | ✓ | | 5 提供商（Qwen/OpenAI/Anthropic/Gemini/自定义） |
| Kimi CLI | | | | | 仅 Kimi |

### 架构与设计

| 工具 | 语言 | 架构 | 主要设计目标 |
|------|----------|--------------|-------------------|
| Claude Code | Rust | 原生 CLI | 代理式编程工具 |
| Aider | Python | Git 原生 | 结对编程 |
| Copilot CLI | TypeScript | CLI 扩展 | GitHub 集成 |
| Cursor | TypeScript | IDE (VS Code) | AI 原生编辑器 |
| SWE-agent | Python | Agent-Computer Interface | 基准性能 |
| Cline | TypeScript | IDE 扩展 | 自主编码 |
| Goose | Rust | MCP 原生 | 模型灵活性 |
| OpenCode | TypeScript | 多代理（7 内置） | 多客户端 AI 平台（TUI + Web + 桌面） |
| Continue | TypeScript | IDE + CLI + CI/CD | PR Checks + 语义索引 |
| Warp | Rust | 终端替代品 | 现代终端 + AI |
| Gemini CLI | TypeScript | ReAct 循环 | Google 生态 |
| OpenHands | Python | 复合 AI | 完全自主 |
| Qwen Code | TypeScript | ReAct 循环（Gemini CLI 分叉） | 中文开发者生态 |
| Kimi CLI | Python | CLI + Web + IDE | 双模式交互（Ctrl-X） |

### 核心功能对比

#### Git 集成

| 工具 | 自动提交 | 分支管理 | PR 创建 | 说明 |
|------|-------------|-------------------|-------------|-------|
| Claude Code | ✓ | ✓ | ✓ | 强大的 Git 支持 |
| Aider | ✓ | ✓ | | **同类最佳** |
| Copilot CLI | | ✓ | ✓ | GitHub 专注 |
| Cursor | | ✓ | | IDE 内置 |
| SWE-agent | | | | 问题专注 |
| Cline | ✓ | ✓ | | 良好支持 |
| Goose | | | | 基础 |
| OpenCode | | ✓ | | Git snapshot review + worktree 隔离 |
| Continue | | | ✓ | CI/CD 专注 |
| Warp | | ✓ | | 终端内置 |
| Gemini CLI | | | | 通过 bash 工具 |
| Qwen Code | | | | 通过 bash 工具 |
| Kimi CLI | | | | 通过 bash 工具 |

#### 上下文管理

| 工具 | 最大上下文 | 仓库映射 | 压缩 | 说明 |
|------|-------------|----------|------|-------|
| Claude Code | 100 万 token | | ✓ | 最大上下文 |
| Aider | 20 万 token | ✓ | | 优秀的映射 |
| Copilot CLI | ~12.8 万 token | | | 标准 |
| Cursor | ~20 万 token | | | 多模型 |
| SWE-agent | 可变 | ✓ | | 研究专注 |
| Cline | ~20 万 token | | ✓ | 良好上下文 |
| OpenCode | 可变 | | ✓ | 会话 auto-compact + 可配置 compaction hook |
| Gemini CLI | ~100 万 token | | | Gemini 原生 |
| OpenHands | 可变 | | | 全项目 |
| Qwen Code | ~100 万 token | | ✓ | 聊天压缩服务 |
| Kimi CLI | ~20 万 token | | | 标准 |

#### 执行与安全

| 工具 | 沙箱 | 权限系统 | 试运行 | 说明 |
|------|---------|-------------|---------|-------|
| Claude Code | ✓ | ✓ | ✓ | 精细权限 |
| Aider | | ✓ | | 透明 |
| Copilot CLI | | | | 企业 |
| Cursor | | ✓ | | IDE 内权限 |
| SWE-agent | ✓ | | | Docker |
| Cline | ✓ | ✓ | | 基于权限 |
| OpenCode | | ✓ | | Tree-sitter AST 分析 + Doom Loop 保护 + 文件时间锁 + Worktree 隔离 |
| Gemini CLI | | ✓ | | 基于权限 |
| OpenHands | ✓ | | ✓ | Docker 隔离 |
| Qwen Code | ✓ | ✓ | | deny>ask>allow + Hook |
| Kimi CLI | | ✓ | | 基础权限 |

## 使用场景推荐

### 最适合复杂重构
1. **Claude Code** - 卓越的推理、大上下文
2. **SWE-agent** - 基准验证
3. **Aider** - Git 纪律

### 最适合快速编辑
1. **Copilot CLI** - 快速命令补全
2. **Gemini CLI** - 轻量级
3. **Aider** - 专注编辑

### 最适合 Git 工作流
1. **Aider** - Git 原生设计
2. **Claude Code** - 强大的 Git 集成
3. **Copilot CLI** - GitHub 生态

### 最适合学习
1. **mini-swe-agent** - 100 行参考
2. **SWE-agent** - 学术方法
3. **Aider** - 透明操作

### 最适合隐私
1. **TabbyML** - 自托管
2. **OpenHands** - Docker 隔离
3. **Aider** - 本地模型支持

### 最适合团队
1. **Claude Code** - 企业功能
2. **Copilot CLI** - GitHub 集成
3. **Continue** - CI/CD 集成

### 最适合中文开发者
1. **Qwen Code** - 每日 1000 次免费，阿里云生态
2. **Kimi CLI** - 双模式交互，Ctrl-X 快捷键
3. **Claude Code** - 中文理解能力强

## 性能总结

| 工具 | SWE-bench | 速度 | 复杂性 | 说明 |
|------|-----------|-------|------------|-------|
| Claude Code | ~60% | 中等 | 高 | 最佳推理 |
| Cursor | N/A | 快 | 中等 | IDE 集成 |
| Aider | ~45% | 快 | 低 | 良好平衡 |
| Copilot CLI | N/A | 快 | 低 | 快速任务 |
| SWE-agent | 74% | 慢 | 高 | 基准之王 |
| Cline | ~40% | 中等 | 中等 | IDE 原生 |
| OpenHands | ~55% | 慢 | 很高 | 完全自主 |
| Qwen Code | N/A | 快 | 低 | 免费额度高 |
| Kimi CLI | N/A | 快 | 低 | 双模式 |
