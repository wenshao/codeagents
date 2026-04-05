# Qwen Code 改进建议 — 读后修改检测防冲突 (Bash File Watcher & Stale Edit Prevention)

> 核心洞察：现代前端/后端工程往往配置了自动化流水线，比如当你按下 `Ctrl+S` 时，编辑器或者本地的 `watch` 进程会自动跑一遍 `Prettier`、`ESLint --fix` 或 `gofmt` 来格式化代码。在 AI 编程的生命周期中，Agent 经常会先 `FileRead`（获取代码），在脑子里思考几秒钟后，再发起 `FileEdit/FileWrite`。如果在这“思考”的几秒钟内，代码由于外部格式化器被改变了，Agent 发出的编辑请求极有可能因为“找不到旧代码（String 匹配失败）”而中断，甚至产生破坏性的替换。Claude Code 通过一套极简但致命有效的“文件状态快照缓存（File State Cache）”和 Mtime 校验，彻底防范了此类 Stale-Edit（过期编辑）；而 Qwen Code 目前没有任何此类防线。
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md)

## 一、自动化工程下的“幽灵冲突”

### 1. Qwen Code 现状：盲目的信任
Qwen Code 的替换逻辑（通常是找寻原字符串，替换为新字符串），完全依赖它上次读取的上下文。
- **痛点（频发的替换失败）**：
  Agent 读取了 `index.ts`（当时代码风格是用了双引号）。它经过推理决定修改这一行。
  在此期间，IDE 刚好自动触发了保存，`Prettier` 把所有的双引号全部换成了单引号。
  于是 Agent 试图执行 `replace("return \"hello\";", "return \"new\";")` 时，大面积报错找不到该内容，然后它只能反复重试，浪费大量 Token 和时间。
- **痛点（强制覆盖的毁灭）**：如果是全量 `FileWrite`，Agent 的旧代码就会覆盖掉 `Prettier` 或用户刚刚做出的最新变更，导致极其隐蔽的代码倒退甚至丢失。

### 2. Claude Code 的解决方案：Mtime 状态快照
在 Claude Code 的 `utils/fileStateCache.ts` 和所有涉及到写盘的工具入口处，它埋下了一层防御网。

#### 机制一：记录文件“读取瞬间”的快照
当 `FileReadTool` 或者 `GrepTool` 碰到任意一个文件时，它会将该文件此刻在操作系统层面的**修改时间戳 (mtimeMs)** 以及自身的读取时间记录在一张全局哈希表中：
```typescript
// 伪代码：在每次 Read 发生时记录
fileStateCache.set(filepath, { lastReadMtime: fs.statSync(filepath).mtimeMs });
```

#### 机制二：写入前的绝对拦截
当 Agent 的大模型决定调用 `FileEditTool` 修改该文件时，工具执行的第一步是：
1. 再次调用 `fs.statSync(filepath)` 获取最新的真实磁盘 mtime。
2. 与缓存中 `lastReadMtime` 比对。如果发现 `real_mtime > lastReadMtime`，说明在“读取”和“准备写入”的间隙中，有第三方进程（或用户自己）偷偷修改了文件。
3. **拦截操作并直接对模型报错**：
   ```text
   <tool_error>
   Error: The file /src/index.ts has been modified externally since you last read it.
   Your cached knowledge of the file is stale.
   Please re-read the file content before attempting to edit it again.
   </tool_error>
   ```

收到这条错误后，大模型会极其顺从地先重新 `read_file`，获取格式化后的新代码，再安全地提交修改补丁。

## 二、Qwen Code 的改进路径 (P2 优先级)

对于代码工具而言，不要去盲猜冲突，而是从底层防患于未然。

### 阶段 1：构建全局文件状态追踪表
1. 在 `packages/core/src/utils/` 创建 `fileStateTracker.ts`。
2. 暴露出两个方法：`markFileAsRead(filepath: string)`（内部调用 fs.stat 记录 mtime） 和 `checkIfFileIsStale(filepath: string)`。

### 阶段 2：拦截读写生命周期
1. 拦截输入端：在 `read-file.ts`，`grep_search` 或任何读取工具输出给大模型之前，通过 tracker 打上标签。
2. 拦截输出端：在 `write-file.ts` 或 `modifiable-tool.ts` (基于块编辑) 的前置检查阶段，优先调用 `checkIfFileIsStale`。

### 阶段 3：构建标准的 Tool Error 兜底话术
当检测到过期时，向大模型抛出一个 `AgentTerminateMode.TOOL_ERROR`，并确保这个报错信息清晰且具有指导意义（让它重读，而不是让它无脑重试刚才的写操作）。

## 三、改进收益评估
- **实现成本**：极低。只需通过一个全局 Map 管理少量几十个文件的 Timestamp 即可，代码量在 100 行内。
- **直接收益**：
  1. **彻底消除幽灵报错**：让模型在现代 Web 前端重度工程化（Linter, Watcher, Hot-Reload）环境下的成功率显著提升，减少无效纠缠。
  2. **用户代码保护**：绝对禁止大模型基于旧上下文对用户正在编辑的文件进行毁灭性覆盖，保障核心体验。