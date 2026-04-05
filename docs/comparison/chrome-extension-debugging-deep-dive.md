# Qwen Code 改进建议 — Chrome Extension 浏览器桥接 (Browser Debugging)

> 核心洞察：在前端开发和全栈调试中，AI Agent 如果只懂代码库里的 `.ts` 和 `.css` 文本文件是远远不够的。当开发者说“帮我看看为什么网页上的登录按钮点击没反应”时，如果 Agent 看不到浏览器里活生生的 DOM 树、Console 报错日志和 Network 请求流，它就只能闭着眼睛盲猜。Claude Code 前瞻性地开发了配套的 Chrome 扩展程序，并结合 `Native Messaging Host` 技术在本地搭建了无缝的 MCP Server 代理，让 Agent 拥有了直接读取 Chrome 运行状态的“眼睛”；而 Qwen Code 目前只能依赖开发者自己充当“传话筒”。
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md)

## 一、前端与 UI 调试的“失明”痛点

### 1. Qwen Code 现状：纯文本的禁锢
作为一个本地 CLI 运行的 Agent，Qwen Code 的所有视野受限于当前目录的文件系统和执行的 Bash 命令输出。
- **痛点一（Console 报错盲区）**：React 应用由于某个 Hooks 写错导致页面白屏，错误信息全打在了 Chrome DevTools 的 Console 里。用户必须手动截图或复制这段又长又臭的报错信息贴回终端给 Qwen。
- **痛点二（DOM 状态盲区）**：CSS 没对齐或者某个元素被 `display: none` 意外隐藏，Agent 读源码也看不出运行时的计算样式（Computed Style）。

### 2. Claude Code 解决方案：Native Messaging 浏览器直连
Claude Code 在 `utils/claudeInChrome/` 下设计了一套惊艳的跨进程桥接架构：

#### 机制一：Chrome 扩展 + Native Host
1. **浏览器扩展**：Claude 提供了一个专属的 Chrome Extension，利用 Chrome 的 `chrome.debugger` 和 `chrome.tabs` API 实时获取网页的 DOM 结构、Console 错误以及 Network 抓包数据。
2. **Native Messaging**：因为 Chrome 扩展无法直接向本地磁盘写文件或与 Node.js CLI 通信，系统利用了浏览器的 Native Messaging 协议，拉起了一个轻量的后台守护进程（Native Host）。

#### 机制二：化身为标准 MCP Server
1. 这个 Native Host 守护进程在本地暴露出了一套标准的 MCP (Model Context Protocol) 接口。
2. 对于 Claude Code 而言，这个 Chrome 浏览器就变成了一个普通的 MCP 资源！它向上提供了类似 `read_dom`, `read_console`, `navigate_to` 等工具。

#### 工作流体验
当你在终端告诉 Agent：“去 `localhost:3000` 看看为啥报错了”，Agent 会直接调用 `navigate_to` 打开网页，然后通过 `read_console` 瞬间拉取到那段红色的 React 错误栈，并在 10 秒内帮你自动修改本地的 TypeScript 代码修复 Bug。整个过程行云流水，开发者完全不用复制粘贴报错！

## 二、Qwen Code 的改进路径 (P2 优先级)

如果 Qwen 想通吃全栈工程师的日常流，打通浏览器运行时是必然的一步。

### 阶段 1：开发基础版浏览器 MCP 服务
1. 不需要立刻开发复杂的 Chrome 扩展，可以先利用现有的如 `Puppeteer` 或 `Playwright` 库。
2. 在 `packages/core/src/mcp/` 下编写一个内置的浏览器 MCP Server，当用户请求网页调试时，在后台启动一个无头或带界面的 Chrome 实例。
3. 暴露 `page.content()`, `page.on('console')` 等 API 为大模型可调用的 Tool。

### 阶段 2：演进至 Chrome Extension 桥接（类似 Claude）
1. 为了能调试用户**正在使用**的浏览器（包含了用户的登陆态 Cookie、React DevTools 状态等），编写一套基于 Native Messaging 的 Chrome 扩展。
2. 让扩展在本地的 9000 端口暴露出 WebSocket 代理。
3. Qwen Code 只要检测到该端口连通，就自动挂载这批强大的“Live Web 调试工具”。

### 阶段 3：多模态截图加持
浏览器扩展可以直接调用 `chrome.tabs.captureVisibleTab` 获取页面高清截图。结合 Qwen VL（视觉大模型）的能力，甚至可以让 Agent 直接帮你核对网页布局与 Figma 设计稿的视觉差异！

## 三、改进收益评估
- **实现成本**：中偏高。跨越了 Node.js 与 Chrome Extension 两个生态，需要解决权限授权和 Native Messaging 繁琐的安装配置。
- **直接收益**：
  1. **前端调试的降维打击**：补齐了 CLI Agent 在前端和 Web 应用调试领域的最后一块短板。
  2. **从写代码升级为跑验收**：Agent 不仅能把代码改了，还能自己去浏览器里刷新看看改对了没，真正实现了“代码编写 -> 运行时验证”的闭环。