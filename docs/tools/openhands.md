# OpenHands (OpenDevin)

**开发者：** OpenHands
**许可证：** MIT
**仓库：** [github.com/All-Hands-AI/OpenHands](https://github.com/All-Hands-AI/OpenHands)
**文档：** [docs.all-hands.dev](https://docs.all-hands.dev/)
**Stars：** 约 70k+
**最后更新：** 2026-03

## 概述

OpenHands（前身 OpenDevin）是一个复合型 AI 代理框架，目标是实现完全自主的软件工程。基于 Python 构建，采用事件驱动架构，支持 Docker/K8s 沙箱执行。内置多种专用代理（CodeAct、BrowsingAgent 等），支持多代理委托，并提供 GitHub/GitLab Issue 自动修复能力。

## 核心功能

### 基础能力
- **复合代理系统**：CodeAct（主力）+ BrowsingAgent + ReadOnlyAgent 等
- **Docker/K8s 沙箱**：每个会话独立容器，完全隔离
- **事件驱动**：EventStream 发布/订阅架构
- **100+ 模型**：通过 LiteLLM 统一接入
- **Web UI**：FastAPI + React 前端
- **Issue 自动修复**：GitHub/GitLab/Bitbucket/Azure DevOps 集成

### 独特功能
- **视觉浏览器**：Playwright + BrowserGym + SOM（语义对象遮罩）
- **多代理委托**：CodeAct 可委托 BrowsingAgent 处理网页任务
- **三层安全框架**：LLM 风险分析 + Invariant 策略 + GraySwan 监控
- **Microagent**：仓库级自定义指令（`.openhands/microagents/`）
- **对话压缩**：递归摘要，维持长会话连续性
- **MCP 集成**：Model Context Protocol 工具扩展

## 技术架构（源码分析）

### 项目结构

```
openhands/
├── agenthub/           # 代理实现
│   ├── codeact_agent/  # 主力代理
│   ├── browsing_agent/ # 文本网页浏览
│   ├── visualbrowsing_agent/  # 视觉网页浏览
│   └── readonly_agent/ # 只读分析
├── controller/         # 代理控制器 + 状态机
├── events/             # 事件系统（Action + Observation）
├── runtime/impl/       # 沙箱运行时
│   ├── docker/         # Docker
│   ├── local/          # 本地
│   ├── remote/         # 远程
│   └── kubernetes/     # K8s
├── llm/                # LLM 集成（LiteLLM）
├── server/             # FastAPI WebSocket 服务器
├── memory/             # 对话记忆 + 压缩
├── security/           # 安全分析器
├── resolver/           # Issue 自动修复
└── integrations/       # GitHub/GitLab/Bitbucket/Azure
```

### 核心架构

```
用户 → WebSocket → FastAPI
    │
AgentController (主循环)
    ├── State 状态机
    ├── SecurityAnalyzer
    └── 代理委托管理
    │
Agent.step(state) → Action
    │
EventStream (发布/订阅)
    │
Runtime.execute(action) → Observation
    ├── Docker ActionExecutor
    └── 插件系统 (Jupyter, AgentSkills)
```

### CodeAct 代理工具

| Agent | 说明 |
|------|------|
| BashTool | 执行 bash 命令 |
| IPythonTool | 交互式 Python |
| StrReplaceEditorTool | 无 LLM 文件编辑 |
| LLMBasedFileEditTool | LLM 驱动文件编辑 |
| BrowserTool | Web 浏览（Playwright） |
| ThinkTool | 内部推理 |
| TaskTrackerTool | 子任务管理 |
| FinishTool | 完成任务 |

### 安全框架

```
Action → LLM 风险分析 (LOW/MEDIUM/HIGH)
       → Invariant 策略检查 (密钥泄露/恶意命令)
       → GraySwan 外部监控
       → HIGH → 暂停 + 用户确认
```

## 安装

```bash
# Docker（推荐）
docker pull ghcr.io/all-hands-ai/openhands:latest
docker run -p 3000:3000 ghcr.io/all-hands-ai/openhands

# 从源码
git clone https://github.com/All-Hands-AI/OpenHands.git
cd OpenHands && pip install -e .
```

## 优势

1. **完全自主**：端到端 Issue→PR 自动化
2. **Docker 隔离**：安全沙箱执行
3. **浏览器能力**：视觉浏览 + SOM + 截图
4. **多代理委托**：专用代理分工协作
5. **三层安全**：LLM + Invariant + GraySwan
6. **Issue 自动修复**：GitHub/GitLab Actions 集成

## 劣势

1. **资源消耗**：Docker + Python + 浏览器，内存大
2. **执行较慢**：容器启动 + 多层抽象
3. **部署复杂**：Docker/K8s 环境要求
4. **非交互式**：主要面向自动化

## 基准测试

| 基准 | 得分 |
|------|------|
| SWE-bench Verified | ~77.6% |
| SWE-bench Lite | ~50% |

## 使用场景

- **最适合**：自动化 Issue 修复、批量 PR 生成
- **适合**：需要浏览器操作的全栈任务
- **不太适合**：日常交互式编码、资源受限环境

## 资源链接

- [GitHub](https://github.com/All-Hands-AI/OpenHands)
- [文档](https://docs.all-hands.dev/)
- [论文](https://arxiv.org/abs/2407.16741)
