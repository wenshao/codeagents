# Qwen Code 改进建议 — FileIndex 模糊文件搜索 (Fuzzy File Search & Async Indexing)

> 核心洞察：在一个包含了 5000+ 文件的大型企业级代码库中工作时，大模型（Agent）常常需要根据模糊的线索寻找特定的文件（例如：“帮我找到那个处理鉴权中间件的 TS 文件”）。人类开发者在 IDE 中通常按 `Ctrl+P`，输入 `authmid` 就能瞬间匹配到 `src/middleware/authMiddleware.ts`。但目前绝大多数 CLI Agent 只能使用笨重的 `find` 或 `grep` 进行极其低效的路径和内容盲搜，不仅速度慢，而且极容易被大写、破折号等格式差异阻断。Claude Code 利用纯 TypeScript 原生手写了一套媲美 `fzf` 的异步模糊文件索引器（FileIndex）；而 Qwen Code 目前完全缺乏这种路径级的模糊定点爆破能力。
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md)

## 一、为什么 Agent 找文件这么慢？

### 1. Qwen Code 现状：精确路径与深度遍历的折磨
目前如果大模型要在 Qwen Code 里找文件，通常有两种做法：
- **精确读取**：使用 `read_file`，但这要求大模型极其准确地知道目标文件的绝对或相对路径。一旦拼错一个字母（比如 `Auth-Handler.ts` 拼成了 `auth_handler.ts`），直接返回 404，模型只能重试。
- **深度盲搜**：使用 `glob` 或 `grep_search`。这会触发底层的磁盘 IO。在一个包含巨大 `node_modules` 或 `build` 产物的工程里，如果没有配好 `.gitignore`，一次搜索甚至会消耗好几秒，且结果多达上百个，挤爆 Token。

### 2. Claude Code 的极客级外挂：Nucleo 风格的文件索引引擎
在 Claude Code 的 `native-ts/file-index/` 目录深处，藏着一个极其惊艳的组件。它没有调用外部二进制的 `fzf`，而是纯手写了一个文件检索引擎。

#### 机制一：后台异步增量建立索引 (Async Incremental Indexing)
当 Agent 一启动，系统就会在主线程的事件循环间隙（Idle 阶段），启动一个不阻塞 UI 的后台遍历任务。
它会读取整个工作区的文件树，并将其加载到内存中形成一棵紧凑的字典树。
如果有文件被修改或新建，底层的 Watcher 会进行**增量更新**，这保证了 Agent 在需要找文件时，面对的是一个永远 `0 ms` 延迟的内存索引！

#### 机制二：非连续字符匹配与路径感知 (Fuzzy & Path-aware Scoring)
它复刻了著名检索器 `Nucleo / FZF` 的打分算法（Scoring Algorithm）：
当大模型（或者开发者）输入模糊关键词 `authmid` 时：
1. 引擎支持跳跃匹配（Non-contiguous matching）。
2. **打分权重**：命中大写字母（CamelCase 边界）、命中路径分隔符 `/` 后面的第一个字母，会获得极高的加分。
3. 它能在千分之一秒内，把最可能的目标文件 `src/middleware/authMiddleware.ts` 排在结果数组的最顶端。

有了这个能力，大模型再也不需要在漫长的文件树里摸黑找路了，直接把人类模糊的需求喂给 FileIndex，拿到最精确的路径去阅读！

## 二、Qwen Code 的改进路径 (P2 优先级)

让大模型和开发者在终端里拥有 IDE 级别的“文件穿越”能力。

### 阶段 1：引入或开发内存模糊搜索引擎
1. 可以在 `packages/core/src/utils/` 引入业界成熟的 `fzf-for-js` 或者 `fuse.js` 库，避免从头手写复杂打分算法。
2. 编写 `fileIndex.ts`，在启动时调用类似 `fast-glob` 的异步方法，收集所有被 Git 追踪的文件路径，存入内存。

### 阶段 2：将其封装为大模型的原生工具
在提供给 Qwen 的 Tool 列表中增加 `fuzzy_find_file` 工具：
```json
{
  "name": "fuzzy_find_file",
  "description": "Fuzzy search for a file path by providing fragments of its name (e.g. 'usrcont' for 'UserController.ts'). Use this before read_file if you are unsure of the exact path."
}
```

### 阶段 3：与交互层融合 (用户体验扩展)
既然底层有了这套引擎，那么我们在之前提到的 [Ghost Text 补全](./ghost-text-completion-deep-dive.md) 或者对话历史搜索中，都可以直接复用这个引擎，让用户在输入文件路径时享受极速的补全提示。

## 三、改进收益评估
- **实现成本**：中等。核心在于利用现成的模糊搜索包，结合文件树的后台遍历与刷新管理，代码量约 200-300 行。
- **直接收益**：
  1. **极 致 的 降 本 增 效**：大模型找文件不再需要“瞎猜路径 -> 报错 -> 使用耗时的 ls 挨个查看目录 -> 终于找到”，一发 `fuzzy_find` 直接命中，缩减 3 轮以上无意义的对话交互，节省大量时间和 Token 费用。
  2. **应对超大型工程**：使 Agent 在 10万级文件的大型单体仓库（Monorepo）中依然健步如飞。