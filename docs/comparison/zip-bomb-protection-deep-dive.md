# Qwen Code 改进建议 — 插件包与 Zip Bomb 防护 (Secure Plugin Bundles)

> 核心洞察：当 AI Agent 生态走向开放，允许用户或社区互相分享 MCP 服务器配置、自定义 Skill 或 Hook 钩子时，分发格式的统一与安全性便成为了核心问题。如果你仅仅要求用户分享一堆松散的代码文件，会导致极差的跨机器兼容性（Node 版本不一致、npm 依赖冲突）。Claude Code 创造了 `.dxt` 和 `.mcpb` 单文件封装格式，但为了防止恶意用户在插件分享中投毒（如构造解压后占用 50GB 的 ZIP 炸弹导致硬盘撑爆），它在底层的解压流处理上构建了教科书级别的安全门控；而 Qwen Code 目前在此领域缺乏标准与防范。
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md)

## 一、开放生态面临的供应链攻击

### 1. Qwen Code 的现状：松散与脆弱
如果 Qwen Code 的用户希望分享一个“数据库表结构审查插件”，目前他只能发给你一个 GitHub 链接，让你自己 `git clone`，然后手动敲 `npm install`。
- **痛点一（碎片化）**：非常容易遇到“在我的机器上能跑，在你的机器上跑不通”的环境问题。
- **痛点二（安全黑洞）**：如果 Qwen Code 未来支持导入压缩包，且不加防护地调用 `unzip`。黑客只需构造一个包含嵌套压缩、大小只有 42KB 但解压后高达 4.5PB 的恶意文件（如经典的 `42.zip`），就能瞬间瘫痪所有的开发者工作站或 CI 容器，酿成严重的生产事故。

### 2. Claude Code 解决方案：安全沙盒打包
Claude Code 在 `utils/dxt/zip.ts` 中设计了一套极其严谨的单文件封装分发规范。

#### 机制一：单文件格式规范 (.dxt / .mcpb)
这并不是什么神秘的新技术，它本质上就是一个包含了源代码、`manifest.json` 元数据和所有底层依赖项（Vendor dependencies）的 Zip 压缩包。
因为所有依赖都被预先打包，接收方下载后开箱即用，真正实现了“一次编写，到处运行”的极速分发体验。

#### 机制二：流式边解压边校验 (Zip Bomb Protection)
当你向 Claude Code 导入一个插件包时，它绝对不会直接调用系统的 `unzip` 工具，而是使用纯 JS 的 `fflate` 库并绑定了极其苛刻的流式守门员（Stream Guard）：

```typescript
const LIMITS = {
  MAX_FILE_SIZE: 512 * 1024 * 1024,   // 单个文件解压不能超过 512MB
  MAX_TOTAL_SIZE: 1024 * 1024 * 1024, // 整个包解压不能超过 1GB
  MAX_FILE_COUNT: 100000,             // 最多只允许 10 万个文件
  MAX_COMPRESSION_RATIO: 50,          // 【核心】压缩比超过 50:1 立即熔断
};
```
最精妙的设计是 **动态压缩比检测（Dynamic Compression Ratio Check）**：
在解压的 Stream 管道中，它会实时计算已读取的压缩字节和已吐出的明文字节。只要发现这个比例飙升超过了 `50:1`（正常的文本代码压缩比通常在 3:1 到 10:1），它会立刻抛出异常：
> `Suspicious compression ratio detected... This may be a zip bomb.`
并瞬间关闭解压管道、销毁临时目录，将黑客攻击掐死在摇篮里。

## 二、Qwen Code 的改进路径 (P3 优先级)

建立生态需要护城河，安全的包管理协议是基石。

### 阶段 1：定义 Qwen 的插件包标准
1. 定义一种新的打包后缀名，例如 `.qwp` (Qwen Web/Workspace Plugin)。
2. 规定内部必须包含一个 `manifest.json`，其中必须包含 `version`, `entrypoint`, `permissions_required` 等核心元数据。

### 阶段 2：开发安全的解压流水线
在 `packages/core/src/utils/` 下开发安全的防爆解压模块：
1. 引入 `fflate` 或同级的高性能流式压缩库。
2. 注入类似于上文的四大阈值。
3. 在解压过程中顺带检测路径穿越攻击（Path Traversal Attack），如果压缩包里的文件名试图写 `../../../etc/passwd`，必须立刻熔断报错。

### 阶段 3：建立生态分享社区（远期）
配合这套安全的基建，可以像 VS Code 插件市场一样，在云端建立一个可信赖的插件注册表。

## 三、改进收益评估
- **实现成本**：中等。安全解压模块的编写需要一定的底层流控能力，代码大约 300 行。
- **直接收益**：
  1. **开启生态闭环**：使非官方的高质量 MCP 插件或 Prompt Skill 可以在企业内部安全且极速地流转分发。
  2. **消除严重的零日漏洞**：防范了最臭名昭著的 ZIP Bomb 和目录穿越攻击，让这款 AI 工具能放心地进入安全红线极高的企业内网。