# Qwen Code 改进建议 — 权限对话框文件预览 (Permission Dialog File Preview)

> 核心洞察：安全沙盒（Sandbox）和人工确认（Human-in-the-loop）是防范 AI 作恶的底线。然而，如果我们只是在终端里弹出一句冷冰冰的 `Agent wants to use FileEditTool on src/utils.ts. Allow? (y/n)`，开发者在没有看到具体改动的情况下，通常会产生“疲劳式点击（Click Fatigue）”——也就是连按 Y 回车盲目批准。这种形同虚设的“免责声明式”确认不仅毫无安全可言，反而容易让用户在翻车后产生挫败感。Claude Code 对此做出了终极改良：在所有的写操作与替换操作被执行前，它会在权限审批对话框中直接渲染出极其精致的“带高亮的内联代码差异（Inline Diff Preview）”；而 Qwen Code 现阶段的审批框仍处于“只知其名，不知其貌”的盲批状态。
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md)

## 一、“盲盒审批”带来的安全降级

### 1. Qwen Code 的现状：缺乏上下文的警报
目前，当配置了较高的交互安全级别，Agent 试图修改文件时：
- **痛点一（信息极度不对称）**：终端仅显示：`[Action Required] Allow modification to /path/to/file.py?`。开发者此时不知道 Agent 到底是要修一个 Bug，还是要删掉整个文件的逻辑。为了做出知情决策，开发者不得不退出当前的 Agent，用 `git diff` 或者打开 VS Code 去看缓存区。
- **痛点二（安全形同虚设）**：因为核实变更的成本太高，人都是有惰性的。在连续弹了五次确认框后，开发者会闭着眼睛狂敲 `Y`。万一其中掺杂了一条 `rm -rf` 或者是覆盖掉了核心密码配置文件的操作，这道防火墙就等同于虚设。

### 2. Claude Code 解决方案：所见即所得的拦截沙盘
在 Claude Code 的 `components/permissions/` 目录下，他们花重金打造了一个全功能的组件，让权限审批不仅透明，甚至成为了一种享受。

#### 机制一：拦截层的深度数据提取
当底层执行工具（比如 `ReplaceTool`）试图发力时，它被挂起了。
但它会把准备发力的“原材料”带出来传给 UI 层：包括**原文件路径、原文件受影响的代码片段、将要替换成的新代码片段**。

#### 机制二：极致的差异高亮渲染 (Diff Highlighting)
React Ink TUI 接管了这批数据，它不会直接打出两坨生肉文字，而是：
1. 提取文件的扩展名，通过轻量级语法高亮库（如基于 Prism 或 Rust NAPI 的解析器）为代码上色。
2. 实时生成一个局部的 `diff` 视图。用红色高亮删除的行，绿色高亮新增的行。
3. 把它包装在一个美观的边框盒子里：
   ```text
   ⚠️ Permission Request: Edit [src/auth.ts]
   -------------------------------------------------
   - if (user.role == "admin") {
   + if (user.role === "admin" && user.isActive) {
   -------------------------------------------------
   Approve [y] / Deny [n]
   ```

#### 机制三：附带的上下文说明
不光是代码！这个对话框有时还会利用大模型的输出意图，在顶部增加一行小字提示：“*Agent 试图在这里修补你之前提到的越权访问漏洞*”。让审查的决策过程变得极具连贯性。

## 二、Qwen Code 的改进路径 (P2 优先级)

让“人工审批”不再流于形式，变成真正意义上的人机共创（Human-AI Co-creation）。

### 阶段 1：重构 `ToolRequest` 的负载结构
修改全局的拦截器协议。在工具触发拦截时，不要仅传递 `toolName`，必须要求特定的危险工具（如 Edit、Replace、Write）携带完整的 `previewData` 对象。
```typescript
interface PermissionRequest {
    toolName: string;
    description: string; // "Modify file.txt"
    diffPreview?: string; // 供直观显示的 Diff 文本
}
```

### 阶段 2：开发 `PermissionDialog` 富媒体组件
1. 废弃掉简单的 `inquirer.prompt` 或基础的 `readLine` 输入。
2. 在 `packages/cli/src/components/` 下新建高级的 React Ink `<PermissionsDialog />` 组件。
3. 引入轻量的 Diff 计算库（如 `diff` npm 包），在内存中将 `Old String` 和 `New String` 转化为行内差异数组。
4. 使用 `chalk` 给差异部分打上红绿高亮背景色。

### 阶段 3：安全建议集成
在弹出高亮修改代码的同时，配合之前探讨的 [破坏性命令警告系统](./qwen-code-improvement-report-p2-stability.md#item-27)，如果发现这段代码变更涉及环境变量配置或核心系统库修改，在对话框下方使用高亮的黄字打印：`⚠️ Warning: This file typically contains sensitive configuration. Review carefully.`。

## 三、改进收益评估
- **实现成本**：中等偏上。在终端中完美渲染带高亮对齐的 Diff 内容有一定的前端绘制难度，代码量大约 300 行。
- **直接收益**：
  1. **彻底消除 Click Fatigue**：让开发者每一次按下 `Y` 都是深思熟虑的，极大地收紧了安全防线。
  2. **高级的交互质感**：直观的红绿代码 Diff 往往是最能体现一款编程类命令行工具“专业度”的触点，瞬间拉开与玩具脚本的差距。