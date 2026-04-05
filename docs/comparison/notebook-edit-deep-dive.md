# Qwen Code 改进建议 — Notebook Edit 工具 (Jupyter Notebook Atomic Editing)

> 核心洞察：数据科学家和 AI 研究员在日常开发中高度依赖 Jupyter Notebook (`.ipynb` 文件)。在 AI Agent 的眼中，一个 Notebook 文件仅仅是一个巨大的 JSON 字符串。当大模型试图修改其中的某一行代码时，如果直接使用通用的文本编辑工具（如 `FileEditTool` 进行字符串替换或行号覆盖），极易破坏原本的 JSON 括号结构，或意外抹除 Cell 的元数据（Metadata 和 Execution ID），导致 Notebook 无法再被 Jupyter 前端正确渲染。Claude Code 专门为此开发了原子级的 `NotebookEditTool`，而 Qwen Code 目前对 Notebook 文件缺乏结构化的尊重与保护。
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md)

## 一、通用文本编辑面对 JSON 的破坏性

### 1. Qwen Code 的现状：暴力文本替换
假设一个 `.ipynb` 文件中有这样一个 Cell：
```json
{
  "cell_type": "code",
  "execution_count": 42,
  "id": "e8d3a1f4",
  "metadata": {},
  "source": [
    "import pandas as pd\n",
    "df = pd.read_csv('data.csv')\n",
    "df.head()"
  ],
  "outputs": [...]
}
```
当用户告诉 Qwen Code：“帮我把这段代码的 `df.head()` 换成 `df.describe()`”。
Qwen Code 的基础 `edit` 工具会直接尝试在整个庞大的 JSON 文件里寻找 `"df.head()"` 这个字符串并替换它。
- **痛点一（转义车祸）**：如果在 Python 代码里包含了双引号 `"` 或换行符 `\n`，大模型很难精确掌握底层 JSON 必须加反斜杠 `\` 的转义规则，经常替换后导致整个文件触发 `JSON.parse` 报错，文件彻底报废。
- **痛点二（上下文污染）**：Agent 往往会把冗长的 `outputs` 节点（如图表的 base64 数据）也读取进上下文，瞬间挤爆 Token。

### 2. Claude Code 解决方案：结构化的读写手术刀
Claude Code 在 `tools/NotebookEditTool/NotebookEditTool.ts` 中完全绕开了“文本匹配”的陷阱。

#### 机制一：专有工具拦截
当大模型被分配了修改 Notebook 的任务时，它会自动选用这个专门的工具。该工具不要求大模型提供“原字符串”和“替换字符串”，而是让大模型提供确切的 `Cell Index` 或是 `Cell ID`，以及**未经转义的、纯净的新 Python 代码块**。

#### 机制二：JSON 解析与原子操作
`NotebookEditTool` 在底层做了以下工作：
1. `JSON.parse()` 读取目标 `.ipynb` 文件。
2. 找到指定的 Cell（如 `cells[3]`）。
3. 仅仅将该 Cell 的 `source` 字段替换为大模型传来的新代码（在底层自动处理 `\n` 数组的切分和双引号转义）。
4. **严格保留**该 Cell 原有的 `execution_count`、`id`、`metadata` 乃至下方的 `outputs`。
5. `JSON.stringify()` 安全写回。

这样，无论大模型生成的代码有多么复杂，也绝对不可能破坏整个 Notebook 文件的外层结构。

## 二、Qwen Code 的改进路径 (P2 优先级)

如果希望 Qwen Code 能够顺利打入 Python 算法和数据开发工程师的工作流，针对 Notebook 的原生支持不可或缺。

### 阶段 1：开发专有 `NotebookEditTool`
1. 新建 `packages/core/src/tools/notebookEdit.ts`。
2. 设计该工具的 Schema，参数包含 `filepath`, `cell_index` (可选), `cell_id` (可选), `new_source`。

### 阶段 2：拦截 `FileReadTool` 优化读取 (Notebook Read)
除了编辑，读取阶段也需要优化：
1. 修改现有的 `read_file` 工具，检测到后缀名为 `.ipynb` 时，走专用解析分支。
2. 在组装给大模型看的内容时，**剥离所有 `outputs` 和繁琐的 `metadata`**，只将 `cell_index`、`cell_type` 和 `source` 转化为易读的 Markdown 格式发给大模型（甚至可以渲染为 `Cell [3] (code): ...`）。
3. 这将为大模型节省 90% 甚至更多的无用 Token 浪费！

## 三、改进收益评估
- **实现成本**：低。无需引入外部库，只需要处理 Node.js 原生的 JSON 操作，代码量约 150 行。
- **直接收益**：
  1. **零损坏风险**：彻底终结 Agent 编辑 Jupyter Notebook 导致文件损坏的悲剧。
  2. **大幅降低 Token 花费**：在读取时清洗掉庞大的输出图表数据，让 Agent 只专注于核心代码的逻辑分析。