# Qwen Code 改进建议 — Agent 创建向导 (Interactive Agent Creation Wizard)

> 核心洞察：随着大模型提示工程（Prompt Engineering）越来越复杂，让用户去手写一段包含十几项配置（模型选择、工具白名单、挂载的外部知识库、MCP 服务列表等）的 YAML 格式配置文件，简直是劝退新手和普通开发者的最大障碍。Claude Code 为了降低门槛，用 React Ink 构建了长达 11 个步骤的沉浸式“图形化终端向导 (`CreateAgentWizard`)”；而 Qwen Code 目前在新建专属 Agent（例如 `/agents create`）时，交互流程较为薄弱。
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md)

## 一、让极客产品变得开箱即用

### 1. Qwen Code 现状：陡峭的学习曲线
如果目前我们想在 Qwen 中配置一个专门用来写单元测试的 Agent，流程通常是这样的：
- 查阅文档。
- 自己创建一个隐藏目录和 `.md` 或者 `.yaml` 文件。
- 小心翼翼地按照格式拼写 `tools: ["read_file", "write_file"]`。如果不小心把 `write_file` 拼成了 `write-file`，可能在跑的时候就会抛出诡异的异常。
**痛点**：高摩擦力的配置过程将绝大多数轻度使用者挡在了“打造私人助理生态”的大门之外。

### 2. Claude Code 的解决方案：傻瓜化的 11 步沉浸式向导
在 Claude Code 的 `components/agents/new-agent-creation/CreateAgentWizard.tsx` 中，作者用极致的 TUI 体验把这件繁琐的事变得极其解压。

当用户输入 `/agents create` 时，终端瞬间切换到一个带有高亮指引和动画的全屏向导：

#### 机制一：全方位的选择器 (Selection TUI)
它并没有要求用户打字，而是通过方向键驱动：
1. **Location**：按左右键选择这个 Agent 是放在全局（Home 目录，对所有项目可见）还是本项目内共享。
2. **Tools**：把系统中所有的工具罗列成一张复选框（Checkboxes）列表！用户只需按空格键（Space）勾选，彻底告别了手打字符串带来的拼写错误。
3. **Model & Color**：支持下拉列表选择基础模型（如 Opus / Sonnet / Haiku），甚至让用户为这个 Agent 选一个代表色的十六进制代码用于终端区分。

#### 机制二：AI 生成 AI (AI-Generated Prompts)
这也是向导中最聪明的一步：
在让用户写大段 System Prompt（系统提示词）时，用户可以选择“人工手写”或“AI 生成”。
如果选了后者，用户只需一句话描述：“我想要一个极度严苛的 Rust 内存安全审计员”。向导会在后台偷偷调一下当前的主模型，用主模型将这句话扩写为极其专业、包含思维链（Chain of Thought）指导的 500 字巨无霸 Prompt，然后自动填入配置。

#### 机制三：所见即所得的确认与序列化
在最后一步 `Confirm`，向导会在屏幕上打印出刚才组装好的完整的、带有排版的 Markdown / YAML 源码，征求用户最后的同意。确认后，调用底层的 `saveAgentToFile()` 安全落地。

## 二、Qwen Code 的改进路径 (P2 优先级)

把配置能力图形化，是做强生态的第一入口。

### 阶段 1：开发多阶段状态机 (Multi-step State Machine)
1. 在 `packages/cli/` 中创建 `components/Wizard/CreateAgentWizard.tsx`。
2. 定义一个严谨的 Typescript 类型 `DraftAgentConfig` 来持有中间步骤的状态。
3. 利用 React 的 `useState` 维护一个 `currentStep` 索引，在回车时推进，在 `ESC` 时回退。

### 阶段 2：引入 TUI 的多选框组件
实现 `Ink` 中的 `MultiSelect` 交互组件（如果不使用现成的包）。渲染出类似于：
```text
[x] shell       - Execute local scripts
[ ] mcp_github  - GitHub issue integration
[x] grep_search - Fast code search
```
强类型确保配置出的 YAML 绝对合法。

### 阶段 3：打通“用模型写模型”的闭环
复用底层的 `contentGenerator.ts`。在向导中，如果是 AI 生成模式：
弹出 Loading Spinner，用一个预设的 Prompt（“你是一个 Prompt 工程师，请将用户的这句短需求转化为详细的 Agent System Instruction...”）去请求 Qwen API，把得到的高级提示词塞回向导状态机。

## 三、改进收益评估
- **实现成本**：中等。核心难点在利用 React Ink 处理复杂的多页表单（Form）流转及校验，代码量在 500 行左右。
- **直接收益**：
  1. **极大地降低使用门槛**：让小白用户也能在 1 分钟内顺滑地创建自己的“前端大师 Agent”或“文档校对 Agent”，享受高阶功能。
  2. **减少配置相关的 Issue**：通过强类型的选项钩选代替手写，根除绝大部分因 YAML 缩进错误或拼写错误导致的工单报错。