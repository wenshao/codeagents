# Qwen Code 改进建议 — Git 状态与仓库上下文自动注入 (Git Context Auto Injection)

> 核心洞察：大模型代理（AI Agent）在处理任务时，“它以为的世界”和“真实的世界”常常存在偏差。比如，开发者让 Agent“提交代码”，如果 Agent 不知道当前所处的分支，它可能会建议直接 `git push origin main` 酿成大错。或者开发者让它“清理一下代码”，在拥有 50 万个文件的 Monorepo 中与在只有 10 个文件的微服务中，其搜索策略应该截然不同。Claude Code 在每一轮 API 调用前，都会极速在系统提示中**隐式注入**当前的 Git 状态、平台信息和仓库规模；而 Qwen Code 目前在此类基础环境感知的自动注入上还比较薄弱，模型常常处于“半盲”状态。
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md)

## 一、缺失项目级上下文带来的推理偏差

### 1. Qwen Code 现状：局部的视野
目前，Qwen Code 的 `getEnvironmentContext()` 主要收集的是操作系统类型（Platform）和当前日期。
- **痛点一（版本控制盲区）**：在 CLI 模式下，大模型不知道当前工作区处于哪个 Git 分支，也不知道是否有未提交的改动（Untracked / Modified files）。当用户发出模糊的指令如“检查我刚刚改过的代码”，Agent 往往需要先耗费一轮去调用 `Bash(git status)` 才能明白现状。
- **痛点二（规模认知缺失）**：模型不知道自己面对的是多大的代码库。由于缺乏对仓库文件总数的预估，模型在执行 `grep` 或 `glob` 时，经常采用极其低效的无限制全盘扫描，导致被大量的编译产物（如 `node_modules` 或 `dist`）淹没。

### 2. Claude Code 解决方案：每轮自动注入的 `<system-reminder>`
在 Claude Code 的 `context.ts` 和 `utils/api.ts` 中，作者构建了一套零开销的上下文雷达。

#### 机制一：极速获取 Git 状态（不 Spawn 进程）
传统的 `git status` 极慢。Claude 为了在**每一轮对话**前都更新状态，它放弃了传统的 `child_process.spawn('git', ['status'])`，而是直接读取硬盘底层的 `.git/HEAD` 文件和 `refs/heads/`，瞬间获取当前的分支名。

#### 机制二：文件数粗略估算 (File Count Estimation)
它在启动或切目录时，会快速算一下当前被 Git 追踪的文件数量。为了保护企业代码库的隐私和减小 Prompt 噪音，它**不会传输精确的数字**，而是巧妙地将其向上取整到 10 的幂次方：
> "The user is working in a repository with ~1000 files."

#### 机制三：尾部追加的 System Reminder
这些信息（包括操作系统、当前目录绝对路径、Git 分支、仓库规模）不会被写死在最顶部的 System Prompt 里（那会破坏 Prompt Cache），而是被组装成一段简短的 `<system-reminder>` 块。
在最终向大模型发送请求前，这段 `<system-reminder>` 会被**追加在所有历史消息的最后、最后一次 User 提问之前**。这样能确保大模型在推理时对环境的认知是最强烈且最新的。

## 二、Qwen Code 的改进路径 (P2 优先级)

让大模型在每一次呼吸间都感知到开发环境的全貌。

### 阶段 1：开发环境雷达探测器
1. 新建 `packages/core/src/utils/environmentRadar.ts`。
2. 实现纯 Node.js 的文件读取逻辑，解析 `.git/HEAD` 来极速获取分支名。
3. （可选）使用前几轮提到的 FNV-1a Hash 或 `git ls-files` 构建一个带 LRU 缓存的仓库规模估算器。

### 阶段 2：重构环境上下文的生成
在 `packages/core/src/core/client.ts` 或对应的上下文聚合层：
构建一段极其凝练的 XML 描述：
```xml
<environment_context>
  <os>Linux</os>
  <cwd>/root/my-project</cwd>
  <git_branch>feature/auth-refactor</git_branch>
  <repo_size>~1000 files</repo_size>
</environment_context>
```

### 阶段 3：策略性注入 (Append instead of Prepend)
不要将上述 `<environment_context>` 扔进几万字的静态 System Prompt 中，而是作为最后一条 `Message`（或者夹在最后一个 User Request 的上方）发给模型。

## 三、改进收益评估
- **实现成本**：小。读取几个基础变量并修改组装流，代码量在 100 行左右。
- **直接收益**：
  1. **大幅减少冗余探测轮次**：大模型无需再自己跑 `pwd` 或 `git status` 来认路，首发即精准。
  2. **消除分支操作的危险操作**：当大模型清晰知道自己处于 `main` 分支时，它在执行代码替换或者提交操作时会自觉地多一分谨慎，减少翻车概率。