# Qwen Code 改进建议 — Bare Mode 无自动发现模式 (Deterministic Bootstrapping)

> 核心洞察：现代 AI 编程代理通常都带有非常“聪明”的自动发现机制：启动时自动扫描 `.git` 获取分支信息，自动加载当前和用户目录下的全部插件（Hooks/Plugins），自动提取持久化的记忆片段和 `CLAUDE.md` 配置。这在交互使用时很方便，但当 Agent 作为基础自动化组件被植入到 CI/CD 脚本流水线时，这种“过度聪明”会导致灾难——不同机器上执行同样的脚本结果不一致。Claude Code 提供了 `--bare`（裸模式）配置，彻底切断所有的隐式状态加载，保证脚本执行的绝对确定性。
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md)

## 一、自动发现带来的“薛定谔的 CI”

### 1. Qwen Code 现状：默认隐式全量加载
Qwen Code 在启动时，会执行诸如 `skill-manager` 的全量加载、项目目录规范读取等。
- **痛点一（不确定性）**：当你的自动化流水线运行 `qwen-code "Generate test cases"` 时，如果机器 A 的根目录下不小心残留了一个开发者的个性化规则文件，或者挂载了一个实验性的 Hook 插件，模型就会生成跟机器 B 完全不同的代码风格。你很难复现 CI 里的失败。
- **痛点二（冷启动延迟）**：在无状态的 Docker 容器中跑 CI，为了执行一条最简单的单次对话，也要强行跑一遍全盘的文件树自动发现和状态解析。
- **痛点三（认证冲突）**：有些环境可能会自动去读取系统的 Keychain 来试图激活某些 MCP 连接或者登录凭证，这在无头（Headless）服务器上通常会直接触发致命报错挂起。

### 2. Claude Code 的解决方案：CLAUDE_CODE_SIMPLE
在 `entrypoints/cli.tsx` 中，Claude Code 提供了一个极其好用的隐藏杀手锏 —— `--bare`（或通过环境变量 `CLAUDE_CODE_SIMPLE=1` 激活）。

一旦开启这个模式：
- **跳过预取 (Skip Prefetching)**：立刻禁用 `main.tsx` 中的 `startDeferredPrefetches()`。
- **跳过状态恢复**：无视历史会话记忆和跨 Session 状态，Agent 如同拥有“出厂重置般”纯净的记忆。
- **冻结隐式加载**：不再自动读取本地杂乱的 Hook 和部分不必要的 MCP 工具，**除非在 CLI 参数中被显式指定**。

这样，你向它输入什么，它就绝对基于什么执行。在千台机器构成的集群流水线里，它的表现完全是一个纯净的数学函数：`f(输入) = 确定输出`。

## 二、Qwen Code 的改进路径 (P1 优先级)

为了满足严苛的生产环境要求，Qwen Code 的启动阶段必须具备“手术刀级别的状态控制”能力。

### 阶段 1：定义并贯穿 SIMPLE 环境变量
1. 在 `packages/core/src/config/` 等初始化入口处，增加 `QWEN_CODE_SIMPLE` 环境变量探测，或者通过 `qwen-code --bare` 命令行 Flag 激活。
2. 封装一个全局的 `isBareMode()` 检查函数供各个模块使用。

### 阶段 2：阻断所有的隐式 I/O 与发现
梳理全项目的启动调用链，在以下节点加入拦截：
```typescript
// 1. 阻断本地插件和 Skill 挂载
if (!isBareMode()) {
    await extensionManager.loadLocalPlugins();
}

// 2. 阻断非必需的环境探测 (如 Git 状态探测)
if (!isBareMode()) {
    injectGitContextToSystemPrompt();
}

// 3. 阻断记忆系统的自动合并
if (isBareMode()) {
    memoryService.disableAutoRecall();
}
```

### 阶段 3：建立显式声明机制
在 Bare 模式下，允许通过命令行参数显式弥补所需的依赖。比如：
`qwen-code --bare --include-skill "code-review" --prompt "..."`
如此，哪怕是在极度恶劣的容器环境内，程序也能在瞬间以极低的内存印迹（Footprint）和绝对透明的上下文启动。

## 三、改进收益评估
- **实现成本**：极低。不需要引入新功能，仅仅是在若干启动阶段套上一层 `if (!isBareMode)` 的控制逻辑，代码量 50 行左右。
- **直接收益**：
  1. **CI 黄金标准**：消除环境污染引起的代码生成差异，使自动化工作流 100% 稳定可复现。
  2. **极速冷启动**：将容器内单次调用的初始化延迟从几百毫秒压缩到极限，特别适合高并发的脚本群控。