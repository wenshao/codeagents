# SWE-agent

**开发者：** Princeton NLP
**许可证：** MIT
**仓库：** [github.com/princeton-nlp/SWE-agent](https://github.com/princeton-nlp/SWE-agent)
**论文：** [SWE-agent: Agent-Computer Interfaces Enable Automated Software Engineering](https://arxiv.org/abs/2405.15793)
**Stars：** 约 19k+
**最后更新：** 2026-03

## 概述

SWE-agent 是 Princeton NLP 实验室开发的学术级 AI 编程代理，提出了 Agent-Computer Interface (ACI) 概念。基于 Python + Pydantic 构建，通过 SWE-ReX 实现 Docker 沙箱化执行，在 SWE-bench 上取得领先成绩。支持通过 LiteLLM 接入 100+ 模型。

## 核心功能

### 基础能力
- **ACI（Agent-Computer Interface）**：定义代理与计算机交互的标准接口
- **Docker 沙箱**：通过 SWE-ReX 在隔离容器中执行
- **工具 Bundle 系统**：YAML 定义的可组合工具集
- **批量评估**：并行运行 SWE-bench 基准测试
- **RetryAgent**：多次尝试 + 代码审查循环
- **成本控制**：每实例 $3 上限 + 全局预算

### 独特功能
- **SWE-bench 评估框架**：内置完整的基准测试管线
- **Action Sampler**：多模型投票，集成决策
- **History Processor**：上下文窗口优化（LastN、缓存控制）
- **Trajectory Inspector**：Web 可视化回放执行过程
- **多种解析器**：FunctionCalling / ThoughtAction / ActionOnly / JSON

## 技术架构（源码分析）

### 项目结构

```
sweagent/
├── agent/
│   ├── agents.py           # DefaultAgent, RetryAgent, ShellAgent
│   ├── models.py           # LLM 抽象（LiteLLM）
│   ├── history_processors.py  # 上下文优化
│   ├── action_sampler.py   # 多模型投票
│   ├── reviewer.py         # 代码审查循环
│   └── problem_statement.py # 问题描述类型
├── environment/
│   └── swe_env.py          # SWE-ReX 环境包装
├── tools/
│   ├── tools.py            # ToolHandler 工具管理
│   ├── bundle.py           # Bundle 加载系统
│   └── parsing.py          # 输出解析器
├── run/
│   ├── run.py              # CLI 入口
│   └── run_batch.py        # 批量评估
├── inspector/              # Web 轨迹查看器
└── config/                 # YAML 配置模板
```

### 核心代理循环

```
问题描述 (GitHub Issue / 文本)
  → SWEEnv 创建 Docker 容器
  → 仓库检出 + 环境初始化
  → DefaultAgent.run()
    → step(): LLM 推理 → 解析动作 → 执行命令
    → 观察结果 → 更新历史
    → 重复直到完成或超时
  → 收集 patch → 生成 trajectory
  → RetryAgent: 审查 → 评分 → 选择最佳方案
```

### 工具 Bundle 系统

工具通过 YAML 配置定义，可组合使用：

```yaml
# tools/edit_anthropic/config.yaml
tools:
  - name: str_replace_editor
    description: "File viewing and editing"
    parameters:
      - name: command
        type: string
        enum: [view, create, str_replace, insert, undo_edit]
      - name: path
        type: string
```

### 解析器

| 解析器 | 格式 | 适用场景 |
|--------|------|---------|
| FunctionCallingParser | 原生函数调用 | 默认，支持函数调用的模型 |
| ThoughtActionParser | 思考 + 反引号动作 | 不支持函数调用的模型 |
| ActionOnlyParser | 仅命令 | 简单场景 |
| JsonParser | JSON 格式 | 结构化输出 |

### 特殊控制 Token

- `###SWE-AGENT-RETRY-WITH-OUTPUT###` — 重试并保留观察
- `###SWE-AGENT-RETRY-WITHOUT-OUTPUT###` — 重试不保留
- `###SWE-AGENT-EXIT-FORFEIT###` — 放弃当前任务

## 安装

```bash
# pip 安装
pip install sweagent

# 或从源码
git clone https://github.com/princeton-nlp/SWE-agent.git
cd SWE-agent && pip install -e .
```

## 支持的模型

通过 LiteLLM 支持 100+ 模型，可配置多 API Key 负载均衡（`key1:::key2`）。

## 优势

1. **基准测试之王**：SWE-bench Verified 74%（增强版）
2. **学术严谨**：Princeton NLP 维护，有论文支撑
3. **Docker 隔离**：安全沙箱执行
4. **批量评估**：并行基准测试 + 自动合并预测
5. **灵活架构**：Bundle 系统 + 可插拔解析器
6. **成本控制**：每实例预算上限

## 劣势

1. **面向研究**：不适合日常编码使用
2. **设置复杂**：需要 Docker + Python 环境
3. **执行较慢**：容器启动 + 评估开销
4. **非交互式**：主要用于自动化评估

## CLI 命令

```bash
# 解决单个 GitHub Issue
sweagent run \
  --agent.model.name claude-sonnet-4 \
  --problem_statement.github_url https://github.com/user/repo/issues/42

# 批量评估 SWE-bench
sweagent run-batch \
  --instances swe-bench:lite \
  --agent.model.name gpt-4o

# 交互式 Shell 模式
sweagent run --agent.type shell

# 启动 Inspector（Web 查看器）
sweagent inspector
```

## 基准测试

| 基准 | 得分 | 说明 |
|------|------|------|
| SWE-bench Verified | 74% | 增强版（RetryAgent + 审查） |
| SWE-bench Lite | 62% | 标准评估 |
| SWE-bench Pro | 45.9% | 生产级任务 |

## 使用场景

- **最适合**：SWE-bench 评估、自动 Bug 修复研究
- **适合**：批量 Issue 修复、CI/CD 集成
- **不太适合**：日常交互式编码、快速原型

## 相关项目

- [SWE-bench](https://www.swebench.com/) — 基准测试框架
- [SWE-ReX](https://github.com/princeton-nlp/SWE-ReX) — 运行时执行环境
- [mini-swe-agent](./mini-swe-agent.md) — 100 行教学实现

## 资源链接

- [GitHub](https://github.com/princeton-nlp/SWE-agent)
- [论文](https://arxiv.org/abs/2405.15793)
- [文档](https://princeton-nlp.github.io/SWE-agent/)
