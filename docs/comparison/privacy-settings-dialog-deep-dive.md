# Qwen Code 改进建议 — 交互式隐私设置与数据控制 (Interactive Privacy Dialog)

> 核心洞察：现代 AI 工具最大的信任危机往往来自于对用户数据（如本地代码、遥测分析数据、崩溃堆栈）被不知情上传的恐慌。很多开发者一旦看到某个 AI 助手在后台发送网络请求，第一反应就是寻找 `disable telemetry` 的开关。传统的做法是让用户自己去查文档，并手动在 JSON 里修改隐秘的配置项。Claude Code 选择将安全感拉满：它不仅在产品文档里对数据去向做了详尽声明，更内置了直观的 `/privacy-settings` 面板，让开发者可以在一个所见即所得的 TUI 菜单里随时开启或关闭不同级别的数据共享；而 Qwen Code 目前在隐私管理的交互上存在留白。
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md)

## 一、开发者对数据隐私的深度焦虑

### 1. Qwen Code 现状：被动的隐私控制
虽然 Qwen Code 在底层可能有控制错误上报或 Telemetry 的配置，但暴露给用户的触点很浅。
- **痛点**：当企业安全工程师审查这套工具时，如果他们无法在一个集中的界面中清晰地看到“该工具到底收集了哪些数据，又该如何关闭”，他们通常会直接将这个工具拉入企业的黑名单。
- **痛点**：对于普通开发者，去 `.qwen/config.json` 里猜字段名（是叫 `enableTelemetry` 还是叫 `allowDataCollection`？）是一种极度不友好的体验。

### 2. Claude Code 解决方案：高透明度隐私控制面板
在 Claude Code 的 `commands/privacy-settings/privacy-settings.tsx` 和 `utils/privacyLevel.ts` 中，作者用一种极具诚意的方式打消了用户的顾虑。

#### 机制一：直观的 Slash 命令面板
当你输入 `/privacy-settings` 后，终端会清空当前视图，弹出一个高度定制的复选框面板，每一项都用大白话解释得清清楚楚：
```text
Privacy & Telemetry Settings:

[x] Error Reporting
    Sends anonymized crash traces to help us fix bugs.
[ ] Usage Analytics
    Sends metadata (command counts, OS version) to improve features.
[ ] Prompt Feedback
    Allows sending transcripts when you manually submit a /feedback survey.
```

#### 机制二：隐私级别的严格定义
底层的 `privacyLevel.ts` 并不是简单的布尔值开关，而是构建了严格的数据分类体系。所有的网络请求（无论是发往 Sentry、Datadog 还是自建服务器）都会在最终的出网点被一个全局的拦截器包裹。
只有当拦截器确认当前的 Data Payload 类型命中了用户在面板里放行的级别时，数据才会被真实地放出。

#### 机制三：启动时的显式声明
Claude Code 在用户首次运行工具时，会非常骄傲且醒目地打印出当前数据收集的政策简述，并在末尾附上一句：`You can run /privacy-settings at any time to opt-out.`
这不仅是功能，更是极佳的 PR 手段（Public Relations）。

## 二、Qwen Code 的改进路径 (P3 优先级)

对于有志于出海或进入金融、政企大厂的开源框架，隐私透明是核心卖点。

### 阶段 1：抽象全局隐私护栏 (Privacy Guard)
1. 新建 `packages/core/src/config/privacyManager.ts`。
2. 定义 `PrivacyOptions` 接口：`allowErrorReporting` (默认 true), `allowUsageAnalytics` (默认 true), `allowCodeSnippetUpload` (默认 false)。
3. 在现存所有的 Telemetry SDK 调用前，加上对该 Manager 状态的预检（Early Return）。

### 阶段 2：开发 TUI 控制面板
1. 在 `packages/cli` 新增 `commands/privacy.tsx`。
2. 借用 Ink 的 `SelectInput` 组件，构建一个支持上下键高亮、回车键切换选中状态的动态菜单。
3. 确保用户退出菜单时，将变更瞬间回写（Atomic File Write）至本地配置文件。

### 阶段 3：合规化启动提示
修改 `cli.ts` 启动序列，当检测到是新环境的首次执行（First Run）时，在渲染 ASCII Logo 之后，追加一段简短且真诚的遥测政策免责声明，并将这个功能的开关方法明确告知用户。

## 三、改进收益评估
- **实现成本**：低。无需涉及大模型逻辑，主要工作量在前端表单的绘制和几处日志拦截。
- **直接收益**：
  1. **破除企业落地障碍**：透明的隐私控制是打消企业安全团队疑虑的定海神针，帮助产品跨越合规门槛。
  2. **大幅增强产品信任感**：把选择权交给用户，往往能换来用户更高的宽容度和忠诚度。