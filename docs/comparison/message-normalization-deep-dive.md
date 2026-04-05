# Qwen Code 改进建议 — 消息规范化与配对修复 (Message Normalization & Pairing Repair)

> 核心洞察：各大语言模型的 API（如 Anthropic, OpenAI, 阿里云）都有极其严苛的角色排序规则（通常要求 `user` 和 `assistant` 交替出现，而且如果出现了 `tool_use`，则后续紧跟的消息必须是带有匹配 ID 的 `tool_result`）。在一个持续几小时、包含人工干预、崩溃恢复或上下文压缩的深度交互 Session 中，这些规则很容易被意外破坏。一旦数组非法，后续的整条会话会被云端永久拒收（抛出 HTTP 400 Bad Request）。Claude Code 构建了变态级别的发送前体检机制（`ensureToolResultPairing` 和连续回合合并）；而 Qwen Code 的历史修复逻辑还不足以应对所有边缘车祸。
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md)

## 一、导致会话“猝死”的暗礁

### 1. Qwen Code 现状：缺乏结构自愈
在处理长对话历史时，Qwen Code 缺乏对即将发送到 LLM 的 API Payload 进行“拓扑结构”修复的最后一道防线。
- **痛点一（Tool Use 孤岛）**：Agent 调用了某个超大的工具，执行到一半时发生网络断开或者用户强行按了 `Ctrl+C` 取消。在内存里，留下了一条大模型发出的 `tool_calls`。当用户再次打字时，如果直接带着这个没有回答（没有 `tool_result`）的“孤岛”发给 API，立刻触发 400 报错。
- **痛点二（同角色堆叠）**：由于上下文压缩或者特殊事件 Hook 注入系统消息，最终发往 API 的 Payload 偶尔会出现连续两条 `role: "user"`。这对某些大模型是致命的违规格式。
- **痛点三（媒体爆炸）**：用户疯狂上传报错截图，直到超过了 API 对多模态图片的上限（比如单次请求不得超过 100 张图片或 PDF），导致全盘拒收。

### 2. Claude Code 解决方案：API 发送前的清洗池
在调用底层 API 的最后一厘米处（`services/api/claude.ts` 结合 `utils/messages.ts`），Claude Code 会让原始对话数组通过一条“深层净化流水线 (`normalizeMessagesForAPI`)”。

#### 修复机制一：工具调用配对修复 (`ensureToolResultPairing`)
它会使用栈（Stack）来扫描整个消息树中所有的 `tool_use_id`。
- 如果发现了一个大模型发起的要求，但后面紧跟着的却不是对应该工具的解答：
  系统会**强行捏造一条幻影结果（Synthetic Result）**塞入数组：
  ```json
  {
    "role": "user",
    "content": [
      {
        "type": "tool_result",
        "tool_use_id": "call_12345",
        "content": "System Note: The tool execution was interrupted or failed to complete."
      }
    ]
  }
  ```
  这直接堵死了格式报错的漏洞！并且给模型传达了“上一次没跑完”的信息。

#### 修复机制二：同角色折叠 (Role Compaction)
遍历整个数组，如果有连续的两条 `role: "user"`，它会将第二条的 `content` 数组完全取出，平铺塞进第一条的 `content` 数组中。从而把多条连续对话优雅地压缩成一个单轮回合。

#### 修复机制三：媒体过载剥离 (Media Eviction)
如果它在遍历时检测到多模态区块（图片 base64）总数超过了 `100` 个，它会启动垃圾回收：从最老的对话开始，把图片区块替换成一段纯文本 `[Image removed to save context]`，从而确保最新的截图总能被 API 接受。

## 二、Qwen Code 的改进路径 (P2 优先级)

为了确保用户“永远不会看到 API 400 这种晦涩的代码级报错”。

### 阶段 1：构建 `normalizeMessagesForAPI` 纯函数
在 `packages/core/src/utils/` 下创建一个纯粹的数据清洗管道。
入参是未检查的 `Message[]`，出参是符合 API 严格规范的 `Message[]`。

### 阶段 2：实现 Tool Pairing 栈检查
1. 提取数组中所有的 `tool_calls`。
2. 将其 ID 压入哈希集合。
3. 检查随后的消息中是否存在 `role: "tool"` 且 ID 一致的响应。
4. 对缺失的对象，通过构造虚拟函数返回对象：`{ id: missingId, result: 'Tool execution unexpectedly aborted.' }` 来打上补丁。

### 阶段 3：在生成器入口应用该管道
在 `core/client.ts` 准备拼装 `GenerateContentRequest` 时，先对深拷贝后的 `messages` 数组执行上述清理。

## 三、改进收益评估
- **实现成本**：中等。核心是 AST/数组级别的遍历和变换，代码量 200 行。
- **直接收益**：
  1. **极强的会话鲁棒性**：彻底消灭了由异常中断、网络重连、终端报错引起的连锁上下文崩坏。
  2. **化解长对话隐患**：再也不用担心用户滥用图片附件导致会话寿命提前终结，极大地延伸了 Agent 的生存周期。