# Qwen Code 改进建议 — LogoV2 品牌标识与启动动画 (Brand Identity & Startup Animation)

> 核心洞察：CLI（命令行）工具往往缺乏视觉冲击力。当你第一次安装并启动一个工具时，如果它只干巴巴地打出一行 `v1.0.0 starting...` 然后陷入沉默，用户很难对这个产品产生深刻的品牌印记。优秀的极客工具（如 Neovim、Oh My Zsh 甚至 Redis CLI）都在启动屏（Splash Screen）上做足了文章。Claude Code 专门设计了一个炫酷的 ASCII Art 渐变启动画面（包含精美的色彩渲染和版本提示），并在下方滚动播放核心功能和新版彩蛋引导；而 Qwen Code 目前在品牌视觉输出和新手上路（Onboarding）引导上较为简陋。
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md)

## 一、为什么我们需要在 CLI 里搞视觉？

### 1. Qwen Code 现状：枯燥的初始化
当新用户按照 GitHub 的教程，激动地敲下 `qwen-code` 时，他看到的可能只是一串平淡的加载日志。
- **痛点一（品牌力缺失）**：用户没有一种“启动了强大引擎”的仪式感。很难在推特或者朋友圈发截图去炫耀这个工具。
- **痛点二（功能留存低）**：Qwen Code 即使更新了超级强大的 `/ultraplan` 或者 `/branch` 功能，绝大部分通过 npm 升级版本的用户也不会去翻冗长的 Release Note，根本不知道有了新魔法，导致高级功能的使用率极其惨淡。

### 2. Claude Code 解决方案：高定版的欢迎仪式
在 Claude Code 的 `components/LogoV2/` 目录下，他们实现了一个令人过目难忘的 TUI 组件。

#### 机制一：ASCII Art 与渐变色 (Gradient Text)
它并不是单纯 `console.log` 出几排字符。它利用 `chalk` 或者内部的颜色转换库，对 Claude 的字母做出了非常高级的色阶渐变过渡（从品牌紫色到淡粉色），让整个终端显得极为精致。

#### 机制二：智能的“你知道吗 (Did You Know)”引导
紧贴着 Logo 下方的，并不是无意义的占位符。
系统内置了一个强大的提示引擎（Tips Registry）。它会在每次启动时，随机抽取一条极具价值的高阶用法：
- “💡 Tip: Use `/compact` to save context costs on long sessions.”
- “🚀 New: Try the `/security-review` command to find deep vulnerabilities.”
这相当于把冷启动的等待时间，转化成了最佳的“被动教育（Passive Onboarding）”窗口！

#### 机制三：干扰控制 (Zero-noise in CI)
他们非常清楚开发者的红线：启动画面只在 **交互式模式（Interactive TTY）** 且 **未开启简易模式（--bare）** 时才会渲染。如果在 CI 流水线或者无头模式下，这段炫酷的画面会被彻底屏蔽，保证了日志的绝对纯净。

## 二、Qwen Code 的改进路径 (P3 优先级)

给产品披上一件华丽且专业的外衣，对于开源社区的破圈至关重要。

### 阶段 1：定制 Qwen 专属 ASCII Logo
1. 请设计师或者借助工具，利用 Qwen（通义千问）的标识生成一套极简、辨识度高的大型 ASCII 字符画。
2. 在 `packages/cli/src/components/` 下新建 `WelcomeScreen.tsx` 组件。
3. 利用 React Ink 的 `<Text>` 结合 `gradient-string` 库，赋予其品牌主色调（比如科技紫/千问蓝）的渐变光影。

### 阶段 2：开发 Tip 滚动提示库
1. 梳理出 Qwen Code 最好用、最冷门的 10 条高阶快捷键和斜杠命令。
2. 在 `WelcomeScreen` 下方加入一个由数组驱动的随机轮播栏。每次 `qwen-code` 被唤起时，随机打出一条金句。

### 阶段 3：严格的环境判定拦截
修改 `cli.ts` 顶层：
```typescript
if (process.stdout.isTTY && !isBareMode() && !config.get('hideSplash')) {
   render(<WelcomeScreen version={PKG_VERSION} />);
}
```
允许老手通过配置 `qwen config set hideSplash true` 来永久关闭启动画面，兼顾美观与极客的控制欲。

## 三、改进收益评估
- **实现成本**：极低。纯前端视觉组件的堆砌，代码量在百行左右，不涉及任何底层业务逻辑。
- **直接收益**：
  1. **指数级的品牌曝光率**：精美的启动屏是最容易被开发者截图分享到社交网络的素材，直接拉动项目 Star 数。
  2. **显著提升高阶功能的激活率**：把 Release Note 碎片化地喂给用户，让辛辛苦苦开发出的黑科技不再吃灰。