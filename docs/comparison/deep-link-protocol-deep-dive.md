# Qwen Code 改进建议 — Deep Link 协议与端外唤起 (Deep Link URI Routing)

> 核心洞察：现代开发流极其碎片化。当你正在浏览器里看着一个 GitHub 上的 Bug 报告，或者在 Jira 里看着一张需求工单，要让 CLI Agent 介入，你必须：打开终端 -> `cd` 到项目 -> 输入启动命令 -> 复制粘贴网页上的需求描述。这套跨应用切换（Context Switching）极其拖沓。Claude Code 实现了系统底层的 `claude-cli://` Deep Link URI 协议，支持直接点击网页链接，瞬间拉起本地终端、定位项目并填好 Prompt；而 Qwen Code 目前只能依靠完全的纯手工命令行启动。
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md)

## 一、跨应用信息断层的摩擦力

### 1. Qwen Code 的现状：孤立的命令行
作为一个纯正的 CLI 工具，Qwen Code 的入口被死死锁在了终端窗口里。
- **痛点**：假设团队做了一个飞书/钉钉内部的工单面板。工单上写着“请将登录页按钮的红色改为蓝色”。如果想让 Qwen 帮我干活，我必须手工充当“人肉搬运工”，将工单信息粘进终端，有时候甚至还要把附件图片下载到本地再传给它。这与“高度自动化”的愿景背道而驰。

### 2. Claude Code 解决方案：打通 OS 协议层的任意门
Claude Code 在 `utils/deepLink/registerProtocol.ts` 中，硬核地将自己注册到了操作系统的协议栈中。

#### 机制一：系统级 URI Scheme 注册
当用户首次安装或运行带有类似 `/install-deep-link` 的指令时，Claude Code 会通过极其硬核的 OS API 调用：
- **macOS**: 创建一个微型的 AppleScript 或 App Wrapper (`Claude Code.app`) 注册到 LaunchServices。
- **Windows**: 在注册表中写入 `HKEY_CURRENT_USER\Software\Classes\claude-cli`。
- **Linux**: 写入 `~/.local/share/applications/claude-cli.desktop` 并绑定 x-scheme-handler。

一旦注册成功，操作系统就认识了 `claude-cli://` 这个协议。

#### 机制二：智能的路由解析与预填充
当你在网页中点击了一个类似：
`claude-cli://open?cwd=/Users/dev/my-app&q=Fix+the+login+button+color` 的链接。

浏览器会弹出一个小提示框，确认后：
1. 操作系统会自动唤醒或聚焦你设置的默认终端模拟器（如 iTerm2, Kitty 或 Windows Terminal）。
2. 在这个新建的终端 Tab 里，Agent 启动时读取传递过来的参数。
3. 它自动将工作目录切换到 `/Users/dev/my-app`。
4. 它自动将 `Fix the login button color` 这段文本预填充到屏幕最下方的 Prompt 输入框里，甚至可能还会自动附加一层悬浮的来源 Banner：`[Request from Jira Ticket #1024]`。
5. 处于安全考虑，它**不会**立刻自动按下回车，而是等待用户的最后一眼审阅和确认。

## 二、Qwen Code 的改进路径 (P2 优先级)

让 Qwen Code 的触角延伸出终端沙盒，嵌入企业的每一个 Web 面板。

### 阶段 1：开发参数解析与引导拦截
1. 在 `packages/cli` 增加 CLI 启动参数 `--uri` 或捕获深链接的 Payload。
2. 编写 `parseDeepLink.ts`，解析 URI Query 中的 `q` (Prompt), `cwd` (目录), 和 `context` (额外的只读文件路径)。
3. 在 `InputPrompt` 中将其填入初始 `value` 状态。

### 阶段 2：OS 协议注册机
1. 借助现成的开源包（如 `appdmg` 或手动写 Registry/Desktop 文件工具类），为 Qwen Code 编写跨平台的协议注册代码 `register-protocol.ts`。
2. 将协议名定为 `qwen-code://`。

### 阶段 3：构建安全的承接 UI
为了防止跨站脚本请求伪造（CSRF 变种，比如黑客在网页放一个 `qwen-code://open?q=rm -rf /`），必须设计严苛的确认屏障。
1. 深链接带进来的 Prompt 必须以明显不同的高亮颜色显示（比如虚线框）。
2. 弹出 `[Security Warning] An external application wants to populate your prompt. Press Enter to accept.`

## 三、改进收益评估
- **实现成本**：中偏高。协议注册在三大 OS（尤其是带有严格沙盒的 macOS）上适配需要耗费一定的踩坑时间。
- **直接收益**：
  1. **极 致 的 Web 联动体验**：彻底盘活企业内部工具生态。可以在 GitHub PR 的 Web 页面上加个书签插件，一点就让 Qwen 在本地终端里自动 Review 那个代码分支。
  2. **破圈效应**：使得网页文档中能直接带有“运行示例”的超级链接，用户点一下就能在本地跑起来。