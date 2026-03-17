# OpenHands (原名 OpenDevin)

**开发者：** OpenHands
**许可证：** MIT
**仓库：** [github.com/OpenHands/openhands-dev](https://github.com/OpenHands/openhands-dev)
**网站：** [openhands.dev](https://www.openhands.dev/)
**Stars：** 约 32k+

## 概述

OpenHands（原名 OpenDevin）是一个开源 AI 软件工程师，可以自主完成编码任务。它旨在以开源包的形式复制 Devin 的能力。

## 核心功能

### 基础能力
- **自主编码**：可完成完整的工程任务
- **全栈**：处理前端、后端、DevOps
- **自我修正**：可修复自己的错误
- **浏览器控制**：可使用浏览器进行研究
- **基于 Docker**：隔离的执行环境

### 独特功能
- **完全自主**：可独立处理复杂任务
- **复合 AI 系统**：多个专门的组件
- **研究起源**：学术基础（Princeton）
- **社区 Fork**：多个维护版本

## 安装

```bash
# 使用 Docker（推荐）
docker pull openhands/dev
docker run -it openhands/dev

# 或使用 Python
pip install openhands

# 启动服务器
openhands
```

## 架构

- **语言：** Python
- **设计**：复合 AI 系统（非单一 LLM）
- **执行**：基于 Docker 的隔离
- **支持的模型**：
  - Claude (Sonnet, Opus)
  - GPT-4
  - Gemini
  - 本地模型

## 优势

1. **完全自主**：可独立处理复杂任务
2. **开源**：完全 MIT 许可
3. **Docker 隔离**：安全的执行环境
4. **大社区**：32k+ GitHub stars
5. **多模型**：灵活的模型支持

## 劣势

1. **繁重设置**：需要 Docker，更复杂
2. **资源密集**：需要大量计算资源
3. **较慢**：不适合快速编辑
4. **较少交互**：设计为自主，而非结对

## 使用方法

```bash
# 启动 OpenHands
openhands

# 给它一个任务
"创建一个使用 React 和 FastAPI 的全栈待办应用"

# 它将：
# 1. 规划架构
# 2. 创建文件
# 3. 编写代码
# 4. 测试
# 5. 修复 bug
# 6. 部署
```

## 基准测试

| 基准 | 得分 |
|------|------|
| SWE-bench Verified | ~55% |
| 全栈任务 | 强 |
| Web 开发 | 优秀 |

## 使用场景

- **最适合**：完全自主开发、研究
- **适合**：完整功能实现
- **不太适合**：快速编辑、交互式编码

## 生态系统

- **多个 Fork**：各种社区维护版本
- **文档**：广泛的指南和教程
- **社区**：活跃的 Discord 和 GitHub 社区

## 资源链接

- [网站](https://www.openhands.dev/)
- [GitHub](https://github.com/OpenHands/openhands-dev)
- [文档](https://docs.openhands.dev/)
