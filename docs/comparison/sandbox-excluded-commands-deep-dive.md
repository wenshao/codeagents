# Qwen Code 改进建议 — sandbox excludedCommands 排除机制 (Sandbox Exclusion)

> 核心洞察：现代 AI Code Agent 在本地执行 Bash 命令时往往需要受到 Sandbox（沙盒）或严格权限审查的控制，以防止诸如 `rm -rf /` 之类的毁灭性操作。然而，很多时候开发者需要让 Agent 运行如 `npm install`、`pip install` 等安全但需要网络访问并产生大量文件读写的命令。在全盘开启沙盒的情况下，这些命令要么被拦截，要么需要开发者每次都手动确认（非常打断自动化的连贯性）。Claude Code 在其 Sandbox 架构中设计了 `excludedCommands` 白名单排除机制；而 Qwen Code 目前对待沙盒命令是“一刀切”的。
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md)

## 一、一刀切沙盒带来的可用性灾难

### 1. Qwen Code 的现状：生硬的沙盒边界
如果 Qwen Code 在未来全面启用了类似于容器隔离或严格权限阻断的 Sandbox 模式：
- **痛点一（频繁拦截干扰）**：当大模型说：“我改好了依赖配置，现在需要运行 `npm install`”，如果处于 Sandbox 环境，该命令可能会因为涉及大量的网络和文件写权限被直接拒绝，或者频繁弹出需要人工 `y/n` 确认的对话框。
- **痛点二（缺乏妥协手段）**：用户面临两难选择：要么为了执行 `npm install` 彻底关闭整个沙盒（承担模型乱删文件的巨大风险）；要么忍受每次构建都需要人工介入的折磨。

### 2. Claude Code 解决方案：精确的 Bypass 豁免名单
在 Claude Code 的 `tools/BashTool/shouldUseSandbox.ts` 中，作者明确表示：白名单排除机制不是安全漏洞，而是用户为了效率所做出的授权妥协。

#### 机制一：灵活的 `excludedCommands` 配置
系统允许用户（或通过内部的 GrowthBook 动态下发）配置一个 `commands` 数组（例如 `['npm', 'yarn', 'pytest']`）和一个 `substrings` 数组（例如 `['install']`）。

#### 机制二：智能的命令前缀匹配
当大模型试图执行命令时，引擎会通过一个专门的 `splitCommand` 函数，提取出真实运行的基础命令（Base Command）。
如果发现命令以 `npm install` 起手，它会动态返回 `shouldUseSandbox: false`。
此时这个特定的命令被安全放行至真实的物理机环境或放宽权限的命名空间执行，而下一条如果是 `rm -rf src` 则依然被死死关在沙盒内。

## 二、Qwen Code 的改进路径 (P3 优先级)

给安全防线开一道受控的“单向小门”，是提升高级用户体验的关键。

### 阶段 1：配置文件支持白名单声明
在 Qwen Code 的 `.qwen/settings.json` 中引入 `sandbox.excludedCommands` 数组：
```json
{
  "sandbox": {
    "enabled": true,
    "excludedCommands": ["npm run", "yarn", "pytest", "cargo build"]
  }
}
```

### 阶段 2：命令执行器的预检分流
在 `packages/core/src/tools/shell.ts` 内部：
1. 拦截大模型传过来的 Raw Command。
2. 进行简单的前缀匹配（StartsWith）或正则检测。
3. 如果命中了 `excludedCommands`，则在执行该命令时跳过权限审批对话框（即使用户没开 `yolo` 模式），或者在 Docker 沙盒挂载时赋予该单次进程更高特权。

### 阶段 3：明显的审计轨迹
为了防止白名单被滥用，即使命令被豁免了沙盒检查，也必须在终端打印一条明显的黄色警告：
`[Sandbox Bypassed] Executing trusted command: npm install`。

## 三、改进收益评估
- **实现成本**：低。无需更改复杂的权限底层框架，只是一层针对字符串前缀的提前放行（Early Return）逻辑，代码约 50 行。
- **直接收益**：
  1. **极 致的自动化体验**：消除常见构建、测试命令在安全模式下引发的审批地狱（Approval Hell）。
  2. **避免因噎废食**：鼓励开发者长期开启最严格的沙盒模式，因为他们知道可以用极小的配置代价放行合法脚本。