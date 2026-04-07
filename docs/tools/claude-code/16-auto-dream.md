# 16. Auto Dream 记忆整合——开发者参考

> Auto Dream 是 Claude Code 的后台记忆整合系统——当用户空闲时，自动 fork 一个隐藏 Subagent 对 MEMORY.md 进行整理、去重、更新。名称来源于人类的 REM 睡眠记忆整合过程。
>
> **Qwen Code 对标**：Qwen Code 无等价机制。记忆文件只增不减，长期使用后会积累大量过时/冲突/重复条目。

## 一、为什么需要自动记忆整合

### 问题定义

Code Agent 的记忆系统（CLAUDE.md / MEMORY.md）是**只增不减**的——用户偏好、项目约定、工作进展不断追加。但：

| 问题 | 后果 |
|------|------|
| 同一事实被记录 3 次（不同措辞） | 浪费 token、信息噪音 |
| 过时信息没删除（"项目用 webpack"但已迁移到 vite） | Agent 基于错误假设行动 |
| 矛盾条目共存（"用 tabs 缩进" + "用 spaces 缩进"） | Agent 行为不一致 |
| MEMORY.md 超过 200 行 | 启动时加载过多无效上下文 |

### Auto Dream 的解决方案

当用户空闲时（至少 24 小时 + 5 次会话后），自动 fork 一个后台 Agent 执行四阶段记忆整合：

```
三门触发条件（全部满足才触发）：
  1. 距上次 dream ≥ 24 小时
  2. 距上次 dream ≥ 5 次会话
  3. 获得整合锁（防止并发 dream）
```

## 二、四阶段整合流程

| 阶段 | 名称 | 动作 |
|------|------|------|
| 1 | **Orient** | `ls` memory 目录，读 MEMORY.md，浏览现有 topic 文件 |
| 2 | **Gather Signal** | 从三个来源收集新信息：daily logs → 漂移的记忆 → transcript 搜索 |
| 3 | **Consolidate** | 写入/更新 memory 文件：合并重叠条目、删除矛盾事实、相对日期→绝对日期 |
| 4 | **Prune & Index** | 保持 MEMORY.md < 200 行 AND ~25KB；删除过时指针；解决索引与文件内容的矛盾 |

源码: `services/autoDream/consolidationPrompt.ts`

### 关键约束

- 整合过程约 **8-10 分钟**
- 完全在后台执行，不中断用户
- 使用 fork Subagent，继承当前上下文
- **与 Kairos 互斥**——Kairos 模式有自己的 disk-skill dream 机制

## 三、竞品记忆整合对比

| Agent | 记忆系统 | 自动整合 | 冲突处理 |
|-------|---------|---------|---------|
| **Claude Code** | MEMORY.md + topic 文件 | ✓ Auto Dream（4 阶段） | 删除矛盾、合并重叠 |
| **Gemini CLI** | GEMINI.md | — | — |
| **Qwen Code** | QWEN.md + 简单笔记 | — | — |
| **Copilot CLI** | copilot-instructions.md | — | — |

## 四、Qwen Code 改进建议

实现简化版 Auto Dream：
1. 会话结束时检查 QWEN.md 行数是否超过 200 行
2. 如果超过，fork Subagent 执行整理（合并重复、删除过时、压缩到 200 行内）
3. 不需要完整的 4 阶段——先做"去重 + 删除过时"就能解决 80% 问题
