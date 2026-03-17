# mini-swe-agent

**开发者：** Princeton NLP (SWE-agent 团队)
**许可证：** MIT
**仓库：** [github.com/SWE-agent/mini-swe-agent](https://github.com/SWE-agent/mini-swe-agent)
**父项目**：[SWE-agent](https://github.com/princeton-nlp/SWE-agent)

## 概述

mini-swe-agent 是一个最小的 100 行 AI 软件工程代理实现。它专为教育目的设计，是了解编码代理如何工作的起点。

## 核心功能

### 基础能力
- **100 行**：整个代理约 100 行 Python 代码
- **无花哨依赖**：最小要求
- **教育性**：学习 AI 代理如何工作
- **高性能**：对于其大小来说出奇地有能力

### 独特功能
- **极简主义**：剥离到 essentials
- **透明**：易于理解和修改
- **快速**：轻量级执行

## 安装

```bash
# 克隆仓库
git clone https://github.com/SWE-agent/mini-swe-agent.git
cd mini-swe-agent

# 直接运行
python mini_swe_agent.py
```

## 架构

- **语言：** Python
- **设计**：简单 ReAct 循环
- **依赖**：最小（OpenAI API、基本 Python）

## 代码结构

```python
# 100 行代理类包含：
# - 环境管理
# - 模型接口
# - 运行脚本
# - 简单 ReAct 循环
```

## 优势

1. **教育性**：最适合学习代理如何工作
2. **简单**：易于理解和修改
3. **轻量级**：最小依赖
4. **可黑客**：构建自定义代理的完美起点

## 劣势

1. **有限**：非生产就绪
2. **基础功能**：无高级功能
3. **无 Git 集成**：手动文件操作
4. **仅研究**：为学习设计，而非工作

## CLI 命令

```bash
# 运行迷你代理
python mini_swe_agent.py

# 指定任务
python mini_swe_agent.py --prompt "修复 main.py 中的 bug"

# 指定模型
python mini_swe_agent.py --model gpt-4
```

## 使用场景

- **最适合**：学习 AI 代理架构
- **适合**：构建自定义代理
- **不太适合**：生产使用

## 教育价值

mini-swe-agent 非常适合：
- 理解 ReAct 循环
- 学习代理设计模式
- 构建自己的代理
- 教学 AI 概念

## 资源链接

- [GitHub](https://github.com/SWE-agent/mini-swe-agent)
- [父项目：SWE-agent](https://github.com/princeton-nlp/SWE-agent)
