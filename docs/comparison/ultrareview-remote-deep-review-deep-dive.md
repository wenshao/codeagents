# Qwen Code 改进建议 — UltraReview 远程深度审查 (Remote Deep Review)

> 核心洞察：现在的开发者越来越倾向于使用大模型来审查 Pull Request (PR)。但是在本地终端运行 `/review` 面临着不可逾越的物理限制：如果你面对的是一个包含了 100+ 文件变更、涉及数万行代码变动的核心模块大重构，要在本地机器上完成深度、全方位的逻辑与安全审计，不仅 API 耗时极长，中途断网甚至电脑休眠都会让前功尽弃。Claude Code 针对这种大型重型任务，设计了 `/ultrareview` 命令。它通过跨越物理边界，将巨大的审查任务及其所有相关的 Token 计算开销全权“传送 (Teleport)”到了云端的持久化容器 (CCR) 中去慢慢咀嚼，完成后回传；而 Qwen Code 的审查能力仍然被死死绑定在本地终端单次的同步调用上。
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md)

## 一、大型 PR 审查遭遇的算力与时间瓶颈

### 1. Qwen Code 的现状：本地挂机苦等
如果在 Qwen Code 里执行一个涉及庞大变更树的代码审查：
- **痛点一（覆盖极不完整）**：受限于大模型单次交互的上限，如果本地的脚本试图在 3 分钟内给出一个大架构的结论，大模型必然只能“走马观花”地泛读。它可能会看漏极其关键但深藏在一个辅助函数中的逻辑谬误。
- **痛点二（本地计算资源的死锁）**：为了进行深度审查，本地的 Node.js 进程必须维持着一个持续活跃的 HTTP 连接。在这十几二十分钟内，这台本地电脑的终端是被死死霸占的。你不能关闭电脑，也不能断开 VPN，哪怕中间遭遇极微小的网络抖动，整个几十块钱 API 费用的计算成果也会瞬间化为乌有。

### 2. Claude Code 的星际之门：云边算力迁移
在 Claude Code 的 `commands/review/reviewRemote.ts` 源码中，作者开辟了“把重型分析甩到云端计算集群”的降维打击模式。

#### 机制一：CCR 会话的降生 (Teleport to Cloud)
当你敲下 `/ultrareview`：
系统完全不打算动用本地的大模型算力！它会把当前项目的变更 diff，需求目标，以及项目的上下文环境，打包成一个包裹。
调用 `teleportToRemote()`，将这一切发射到云端的 CCR (Cloud Compute Runtime) 隔离实例中。

#### 机制二：独立的配额体系与深度漫游
云端的旗舰模型（如 Claude Opus）收到了这个包含 100 个文件变更的包后，它有充裕的时间（比如长达 30 分钟）在这个虚拟环境里“慢慢看”。
在源码 `services/api/ultrareviewQuota.ts` 中，甚至可以看到为这种烧算力的重型任务设立的独立追踪体系（`reviews_used / remaining`）。
云端的大模型可以对关键模块进行多次自我发问、反复生成测试用例在沙箱里跑来验证它的猜测。

#### 机制三：轻巧的远程心跳同步
那本地终端在干嘛？
本地终端只跑了一个 `setInterval`。它每隔 10 秒向云端发一个心跳（Heartbeat），拉取一个叫做 `<remote-review-progress>` 的极小标签。
在本地屏幕上，你看到的是优雅的实时进度播报：
> ☁️ Remote Review in progress...
> \> Analyzing authentication middleware (12:45 elapsed)
> \> Checking for SQL injection vectors (15:20 elapsed)

当云端彻底把所有的代码都扒干摸透后，它会把总结成的高浓度（去伪存真后的）安全和逻辑警告发回本地。

## 二、Qwen Code 的改进路径 (P2 优先级)

要想进入“企业级代码卫士”的行列，就必须打通后台异步算力的经脉。

### 阶段 1：构建任务打包与解包机制
1. 在 `packages/core/src/utils/` 下创建一个 `taskPackager.ts`。
2. 针对大型 Review 任务，提前收集好 `git diff`，并在本地进行必要的敏感词脱敏（Sanitization）或者忽略规则应用。
3. 将其序列化为一个可传输的状态块。

### 阶段 2：定义远程异步 Worker 端点
这需要通义千问后台团队（或相关的云平台）提供 API 支持：
1. 本地调用 `POST /api/v1/jobs/ultra-review` 发送任务状态块。
2. 后端接收后，利用最高等级的模型池，挂起一个长期异步 Worker 慢慢啃这份代码（不需要立刻保持 HTTP 阻塞返回）。
3. 后端生成结果后存储。

### 阶段 3：本地终端的长轮询对接
1. 在 CLI 添加全新的命令 `/deep-review` 或 `/ultra-review`。
2. 提交任务后，挂起一个带超时机制（如 `Timeout 30 minutes`）的轮询组件 `<RemoteReviewProgressTracker />`。
3. 此时，甚至可以允许开发者输入 `Ctrl+C` 退回 Shell，只保留一行字告诉开发者：`Job #123 is running in the cloud. We will notify you via DingTalk/Email when done.`（我们会在云端完成后通知你）。

## 三、改进收益评估
- **实现成本**：极高。它突破了传统开源前端项目的范畴，需要大模型底座供应商（比如阿里云端）从基础设施层面对长期任务提供异步接口支持。
- **直接收益**：
  1. **彻底解决大项目的深度痛点**：对于数以万计甚至十万计的遗留代码，提供了唯一可行的、能防丢防断网的真正深度分析手段。
  2. **解放本地生产力**：让高级开发者可以下达命令后立刻合上电脑去开会，将最繁重的心智负担彻底丢向云端。