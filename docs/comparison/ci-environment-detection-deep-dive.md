# Qwen Code 改进建议 — CI 环境自动检测与行为适配 (CI Environment Detection & Adaptation)

> 核心洞察：随着大模型能力的提升，将 AI Agent 部署到 CI/CD 流水线（如 GitHub Actions、GitLab CI）中执行自动化 Code Review 或端到端测试生成已经成为刚需。然而，CI 环境与本地终端（TTY）有着本质的区别。在 CI 中，Agent 无法打开浏览器进行 OAuth 认证，也没有人类用户可以在死锁时按下 `Ctrl+C`。如果不能聪明地感知并适配其所处的宿主平台，Agent 很容易在流水线中发生永久挂起（Hang）或因格式错乱导致日志无法阅读。Claude Code 实现了一套精细的“平台探针与环境降级”机制，确保在任何无人值守的容器内均能稳健运行；而 Qwen Code 目前对运行环境的判断仍显粗放。
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md)

## 一、在流水线盲目运行的灾难

### 1. Qwen Code 的现状：泛泛的 `CI=true` 检测
目前的大多数 Node.js CLI 工具，仅仅通过检查 `process.env.CI` 来决定是否关闭一些交互式的动画（Spinner）。
- **痛点一（丧失平台上下文）**：当你在 GitHub Actions 里跑 `qwen-code "审查一下现在的代码"`，它虽然能执行，但它不知道这具体是哪个 Repo 的哪个 Pull Request。如果没有这些 Meta 信息，Agent 给出的审查意见只能像盲人摸象，无法准确推断上下文。
- **痛点二（Auth 挂起死锁）**：如果用户的 Token 恰好过期，常规逻辑会尝试拉起系统的默认浏览器去要求用户扫码重新登录（OAuth Flow）。但在一个远端的 Linux 容器里拉浏览器，会导致进程无限期阻塞，浪费极其宝贵的 CI 运行计费时长。

### 2. Claude Code 解决方案：高定版的 CI 嗅探器
在 Claude Code 的 `utils/env.ts` 和遥测网关 `services/analytics/metadata.ts` 中，作者为了兼容各种企业级 CI 环境，可谓做到了极致。

#### 机制一：深度探针与平台提取
系统不只看 `CI` 变量，它通过精确探测特定的环境变量（如 `GITHUB_ACTIONS`, `CIRCLECI`, `GITLAB_CI`, `JENKINS_URL`）来锁定当前的确切运行平台。
如果探测到是 GitHub Actions，它会自动读取 `GITHUB_REPOSITORY` (仓库名), `GITHUB_REF_NAME` (当前分支) 以及 `GITHUB_SHA` (提交的哈希)。
**大模型不仅知道了自己在一台没法交互的机器上，还精确地知道了自己在为哪一段代码的历史片段服务！** 它会将这些信息组装并静默注入到 System Context 中。

#### 机制二：智能防御降级 (Headless Fallback)
一旦探针确认环境是 CI：
1. **彻底阻断 WebAuth**：它会绕过所有企图打开浏览器的逻辑，直接在控制台抛出硬错误：“检测到运行在 CI 环境，必须通过 `QWEN_API_KEY` 环境变量提供凭证，OAuth 已禁用。”
2. **纯净日志输出**：强制切换 TUI 渲染引擎为 `Raw/Plain Text Mode`。彻底剥除那些会让 CI 面板卡死的 `\x1b[31m` 颜色控制符和光标回退控制符（ANSI escape codes）。
3. **全局时延锁**：它会根据侦测到的平台（如 GitHub Actions 的最大 6 小时 Timeout 限制），主动缩短自己内部网络请求或任务拉起的超时阈值，确保在平台暴力 Kill 自己之前，能体面地把错误堆栈写进持久化缓存中。

## 二、Qwen Code 的改进路径 (P2 优先级)

让工具既能在前台与人类谈笑风生，也能在后台流水线里安静搬砖。

### 阶段 1：开发全能环境嗅探模块
1. 在 `packages/core/src/utils/` 下新增 `ciDetector.ts`。
2. 引入对常见 CI 平台标志变量的识别矩阵（Matrix）。

### 阶段 2：提取关键元数据并注入上下文
在组装系统提示词（System Prompt）时，调用探针。
如果处于 CI 环境，主动将如下信息插入对话前缀：
> "You are running headlessly in a [GitHub Actions] CI environment for the repository [wenshao/qwen-code], triggered by branch [feature-xyz]."
让大模型不再做“环境盲人”。

### 阶段 3：保护自动化执行流
修改诸如 `ask_user`, `yolo_confirmation`, `oauth_login` 等具有强交互属性的执行工具。在它们的入口处判断 `isCi()`，如果是，立刻用 `throw new Error()` 阻断挂起，直接向大模型传递一个 `ToolError: Interactive action is prohibited in CI. Try using automated tools.`。

## 三、改进收益评估
- **实现成本**：极低。基本全是纯逻辑的环境变量读取和控制流分支，代码量 150 行以内。
- **直接收益**：
  1. **流水线护城河**：让 Qwen Code 在 GitHub/GitLab CI 中具备即插即用的企业级属性，大大降低 DevOps 工程师编写胶水脚本的痛苦。
  2. **根除资源浪费**：通过精确的防死锁阻断，消灭因未捕获交互请求而在后台静默耗死容器的情况。