# Qwen Code 改进建议 — Ripgrep 三级回退与降级 (Ripgrep Fallback Strategies)

> 核心洞察：`grep` 搜索是代码 Agent 探索庞大仓库的基石。在大型项目中，原生的 grep 工具极其缓慢，因此各大项目普遍采用 Rust 编写的 `ripgrep (rg)` 作为搜索内核。但问题在于，Node.js 应用直接 spawn 子进程调用 `rg` 时，运行环境千奇百怪。有些机器上没有全局安装 `rg`，有些无头容器（Headless Container）内资源吃紧，频繁产生 `EAGAIN` 报错。Claude Code 构建了“System -> Embedded -> Builtin”的三级回退策略，并针对 `EAGAIN` 实现了智能的单线程重试降级；而 Qwen Code 目前对外部搜索工具的依赖十分脆弱，一旦失败就会产生“代码库为空”的致命错觉。
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md)

## 一、搜索工具在边缘环境的脆弱性

### 1. Qwen Code 的现状：单一依赖
Qwen Code 中通常会尝试直接调用全局安装的 `rg`。如果失败，它可能会简单地报错或直接返回空数组 `[]`。
- **痛点一（依赖缺失）**：很多企业级 CI 机器或精简版 Alpine Docker 镜像中，并没有预装 `ripgrep`。
- **痛点二（EAGAIN 资源耗尽）**：`rg` 默认会尽可能占满 CPU 所有的核心去并发搜索。在被严格分配资源限制（如 cgroups 限制只能用 0.5 核）的 Kubernetes Pod 内，同时 Spawn 多个线程会导致内核拒绝分配资源，抛出底层的 `EAGAIN` (Resource temporarily unavailable) 错误。
- **致命后果**：如果搜索报错或静默返回空，Agent 会误以为“这个工程里没有对应的函数”，进而开始胡编乱造，引发长链幻觉。

### 2. Claude Code 解决方案：高弹性搜索网关
Claude Code 在其 `utils/ripgrep.ts` 中，为全局代码搜索工具铸造了一道坚不可摧的安全网。

#### 机制一：三级可执行文件回退 (Binary Fallback Chain)
它不会盲目相信系统环境，而是实现了一套按优先级探索的可执行文件定位器：
1. **System Binary**：优先尝试执行环境变量中的 `rg`。
2. **Embedded Binary**：如果系统没有，尝试去读取 Claude Code 自身 npm 包（通过 `vendor/` 或可选依赖 `@vscode/ripgrep`）中携带的预编译二进制版本。
3. **Builtin Fallback**：如果所有的原生进程都无法执行，作为最后的兜底，它内部实现了一套纯 Node.js 的软检索逻辑（哪怕速度慢一点，也绝对不能报错）。

#### 机制二：EAGAIN 智能单线程降级
这是极具深度的工程细节。当它捕获到 `rg` 返回错误，并且 stderr 中包含了 `EAGAIN` 字样（`isEagainError`）时：
```typescript
// Claude Code 处理逻辑：
if (!isRetry && isEagainError(stderr)) {
   // 如果因为并发太高导致系统不分配资源
   // 给 rg 加上 "-j 1" 参数 (强制单线程执行)，并重启搜索！
   return await executeRgWithArgs([...args, '-j', '1'], true);
}
```
通过让出并发度，在资源极度紧缺的廉价服务器上也能成功完成代码检索。

## 二、Qwen Code 的改进路径 (P2 优先级)

保证 Agent 拥有“看穿代码库”的眼睛，是防止幻觉的前提。

### 阶段 1：引入 @vscode/ripgrep 依赖
1. 在 `packages/core` 中添加 `@vscode/ripgrep` 依赖。这是一个极其稳健的跨平台预编译 rg 包，由微软维护。
2. 封装 `rg` 的执行入口，优先使用系统 `$PATH`，如果失败，退推到 `@vscode/ripgrep` 的 bin 路径。

### 阶段 2：错误重试与降级包裹
在执行 `child_process.spawn` 的包装函数中：
1. 捕获 `stderr` 缓冲。
2. 增加正则表达式 `/EAGAIN|Resource temporarily unavailable/i`。
3. 捕获该错误后，自动向命令行数组推入 `--threads=1`（或 `-j 1`），等待 500ms 后重新发起单线程的纯净搜索请求。

### 阶段 3：保护 Agent 的空结果
当一切手段都失败时（例如磁盘权限受限）：
必须显式向 Agent 抛出一段文字错误（`ToolError: Ripgrep crashed with message: XXX. The search did not complete.`），而绝对不能返回一个成功的空数组。大模型只有看到报错，才知道要改用其他工具（如 `find` 或 `grep`）去曲线救国。

## 三、改进收益评估
- **实现成本**：小。改造命令行的生成与错误捕获拦截逻辑即可，代码量不足百行。
- **直接收益**：
  1. **消灭 CI/CD 水土不服**：不管在多么恶劣或精简的容器中，大模型总能搜索代码，不会意外宕机。
  2. **消除严重的静默幻觉**：避免了由于底层命令崩溃返回空数组，导致大模型产生“查无此文”的离谱幻觉。