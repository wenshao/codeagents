# SWE-agent

**开发者：** Princeton NLP
**许可证：** MIT
**仓库：** [github.com/princeton-nlp/SWE-agent](https://github.com/princeton-nlp/SWE-agent)
**文档：** [github.com/princeton-nlp/SWE-agent/tree/main/docs](https://github.com/princeton-nlp/SWE-agent/tree/main/docs)
**Stars：** 约 19k+

## 概述

SWE-agent 是普林斯顿大学的学术项目，使用语言模型修复真实 GitHub 仓库中的问题。它引入了 Agent-Computer Interface (ACI) 设计模式。

## 核心功能

### 基础能力
- **GitHub 问题解决**：接收 GitHub 问题并尝试修复
- **Agent-Computer Interface (ACI)**：代理与计算机之间的新接口
- **多模型支持**：适用于 Claude、GPT-4o 和其他模型
- **可复现**：在 SWE-bench 上完全可复现的实验
- **网络安全**：可处理安全挑战

### 独特功能
- **SWE-bench 领先者**：在 SWE-bench 上达到最先进性能
- **mini-swe-agent**：100 行最小实现
- **研究支持**：已发表的学术研究
- **生产就绪**：被 Meta、NVIDIA、IBM、斯坦福使用

## 安装

```bash
# 克隆仓库
git clone https://github.com/princeton-nlp/SWE-agent.git
cd SWE-agent

# 安装依赖
pip install -e .

# 或使用 Docker
docker pull primls/swe-agent
```

## 架构

- **语言：** Python
- **设计模式：** Agent-Computer Interface (ACI)
- **支持的模型：**
  - Claude Sonnet 4 / Opus 4
  - GPT-4o
  - DeepSeek
  - 本地模型

## 优势

1. **基准领先者**：SWE-bench Verified 达 74%
2. **学术严谨**：同行评审研究
3. **开源**：完全 MIT 许可
4. **可复现**：所有实验都可复现
5. **实战验证**：被主要科技公司使用

## 劣势

1. **学术重点**：为基准测试设计，非日常编码
2. **设置复杂**：比其他工具更难设置
3. **研究导向**：对日常使用不够精致
4. **Python 专注**：主要在 Python 仓库上测试

## CLI 命令

```bash
# 运行 GitHub 问题
python run.py --issue_url https://github.com/user/repo/issues/123

# 运行 SWE-bench
python run.py --problem_type swe-bench --model_name claude

# 使用 mini-swe-agent（100 行版本）
python mini_swe_agent.py

# 使用 Docker 运行
docker run --rm primls/swe-agent --issue_url <url>
```

## mini-swe-agent

100 行 Python 最小实现：

```bash
# 运行迷你版本
python mini_swe_agent.py --prompt "修复 main.py 中的 bug"
```

## 基准测试

| 基准 | 得分 |
|------|------|
| SWE-bench Verified | 74%（专门调优后） |
| SWE-bench Lite | 62% |
| LiveCodeBench | 有竞争力 |

## 使用场景

- **最适合**：研究、基准测试、自动 bug 修复
- **适合**：Python 项目、问题解决
- **不太适合**：交互式编码、快速编辑

## 生态系统

- **mini-swe-agent**：教育性 100 行版本
- **SWE-bench**：它创建的基准
- **生产分支**：几家公司运行修改版本

## 资源链接

- [论文](https://arxiv.org/abs/2401.12345)
- [文档](https://github.com/princeton-nlp/SWE-agent/tree/main/docs)
- [SWE-bench](https://www.swebench.com/)
