# Qwen Code 改进建议 — useMoreRight 右面板扩展 (Right Panel UI)

> 核心洞察：现代开发者的显示器通常是超宽屏（如 27寸或曲面屏），终端全屏展开时动辄有 150-200 列（Columns）的宽度。然而，大多数 CLI Agent 仍采用了传统的“从上到下全量铺满”的单列布局（Single Column Layout）。当大模型输出一段 100 列宽的代码片段时，剩下的空间全部变成了白白浪费的留白。Claude Code 试图在其定制引擎中引入前沿的 `useMoreRight` 侧边栏布局；在宽屏环境下，将终端一分为二，左侧保持持续的问答流，右侧用于驻留文件预览、Diff 对比或大纲地图；而 Qwen Code 尚未涉足复杂的多区域布局机制。
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md)

## 一、单列终端排版的空间浪费与视野丢失

### 1. Qwen Code 的现状：单向卷轴
目前，如果你在 Qwen Code 里让模型修改一个文件，并让它展示修改前后的差异（Diff）：
- **痛点一（信息密度极低）**：大模型的寒暄（“好的，我现在帮你修改文件...”）、思考过程、以及长长的代码 Diff，是一行一行挨着往下推的。
- **痛点二（上下文无法同框）**：当你看到最底下的代码变动时，你上面提出的原始需求（Prompt）已经被滚出屏幕之外了。你无法在同一个视野里对着“需求”来审视“代码修改”，只能不停地用鼠标滚轮上下翻飞，极其割裂。

### 2. Claude Code 的极客尝试：IDE 化的空间分割
在 Claude Code 的源码 `moreright/useMoreRight.tsx` 和主入口 `REPL.tsx` 中，它埋藏了一个极具野心的终端多栏布局逻辑。

#### 机制一：动态宽度检测 (Responsive Terminal)
系统不仅会通过 `process.stdout.columns` 实时读取终端的宽度，还会监听终端窗口 `resize` 事件。
当探测到终端宽度大于特定的临界值（比如 120 列）时，系统底层的排版引擎会将原本独占 100% 宽度的对话框，压缩到左侧的 60% 区域。

#### 机制二：右侧持久化画中画 (Persistent Sidebar)
腾出的右侧 40% 区域被划分给了 `MoreRight` 面板。这个面板就像 VS Code 的右侧代码小窗一样，可以用来实现：
- **静态驻留**：当 Agent 正在一轮中连续读取和修改文件时，左侧依旧在疯狂滚动日志，而右侧则静静地固定展示着目标文件的最新状态树或者 Diff 高亮。
- **视觉分离**：甚至可以把那些臃肿的 MCP Server 返回的结构化 JSON 数据独立渲染在右侧面板，让人眼不再被混合在自然语言流里的乱码所干扰。

## 二、Qwen Code 的改进路径 (P3 优先级)

把 CLI 工具做成一个真正的 Terminal IDE。

### 阶段 1：引入 Flexbox 布局
利用目前 Qwen Code 已有的 `React Ink` 框架优势：
1. 重构最外层的 `<App>` 组件容器。
2. 引入动态判定：
```tsx
const { columns } = useStdout();
const isWideMode = columns > 140;

return (
  <Box flexDirection="row">
     <Box width={isWideMode ? '60%' : '100%'} flexDirection="column">
        <MessageList />
        <InputPrompt />
     </Box>
     {isWideMode && (
        <Box width="40%" flexDirection="column" borderStyle="single" marginLeft={1}>
           <ActiveFilePreview />
        </Box>
     )}
  </Box>
);
```

### 阶段 2：构建全局面板上下文 (Panel Context)
大模型在对话时，需要有能力控制右侧面板的内容。
1. 在全局 `AppState` 中新增一个 `rightPanelState`（比如 `type: 'diff' | 'tree' | 'none', payload: any`）。
2. 开发特定的 TUI 组件 `<DiffViewer>`。当大模型调用 `FileEditTool` 时，除了修改文件，顺手把修改前后的 AST 投递给 `rightPanelState`，右侧就会自动渲染出如同 GitHub 一样的双列差异高亮。

### 阶段 3：响应式退化 (Graceful Degradation)
由于用户随时可能把终端窗口缩小（拖拽边缘），系统必须具备极强的响应式退化能力：
一旦 `columns` 小于阈值，必须瞬间销毁右侧面板，将右侧面板中最重要的信息作为普通的 `Message` 重新插入回左侧的主对话流的最末尾，确保信息绝对不会凭空消失。

## 三、改进收益评估
- **实现成本**：高。React Ink 在处理多栏复杂布局特别是涉及文本换行和 Flex 比例时，极易出现高度崩塌或换行错乱，需要反复打磨 CSS-like 的布局代码。
- **直接收益**：
  1. **生产力工具的质变**：让它从一个高级的“聊天框”，正式迈入“终端级集成开发环境”的门槛。
  2. **最高级的信息密度**：充分压榨宽屏显示器的物理价值，让顶级开发者的眼睛能在同一瞬间捕获并对齐更多的有效数据。