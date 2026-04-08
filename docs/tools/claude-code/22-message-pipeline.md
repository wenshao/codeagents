# 22. 消息与提示管线——开发者参考

> 系统提示只是模型输入的一部分。完整的输入是由**多个来源**经过标准化、排序、注入后拼装的**管线**。本文分析 Claude Code 的消息变换全流程。
>
> **Qwen Code 对标**：Qwen Code 的消息构建相对简单（系统提示 + 消息历史 + 工具 Schema）。Claude Code 的管线包含 6 层变换——其中 `<system-reminder>` 注入和 Prompt Cache 分区是 Qwen Code 缺失的关键环节。
>
> **致谢**：概念框架参考 [learn-claude-code](https://github.com/shareAI-lab/learn-claude-code) s10a 章节。

## 一、为什么系统提示不是全部

### 问题定义

模型接收的完整输入不只是"系统提示 + 用户消息"，而是多个来源的组合：

```
模型实际接收的输入：

┌─────────────────────────────────────────────┐
│ 1. 系统提示（多个 block 拼装）               │
│    ├─ 角色定义                               │
│    ├─ 行为规则                               │
│    ├─ 工具使用指南                            │
│    ├─ 语气风格                               │
│    ├─ 环境信息（平台/shell/日期）             │
│    ├─ 记忆（MEMORY.md）                      │
│    └─ MCP 指令                               │
├─────────────────────────────────────────────┤
│ 2. 第一条用户消息（系统注入）                 │
│    └─ <system-reminder> 标签                 │
│        ├─ CLAUDE.md 项目指令                  │
│        ├─ Git 状态（分支/提交/变更）           │
│        └─ 当前日期                            │
├─────────────────────────────────────────────┤
│ 3. 对话历史                                  │
│    ├─ 用户消息                               │
│    ├─ 助手回复                               │
│    ├─ 工具调用 + 结果                        │
│    └─ isMeta 消息（UI 不可见但模型可见）      │
├─────────────────────────────────────────────┤
│ 4. 工具 Schema（独立传输，非在系统提示中）    │
│    ├─ 核心工具（始终加载）                    │
│    ├─ 延迟工具（ToolSearch 激活后加载）        │
│    └─ MCP 工具（动态发现）                    │
└─────────────────────────────────────────────┘
```

## 二、管线变换流程

```
来源                          变换                      输出
─────                        ─────                    ─────

系统提示段落[]  ──── 段落缓存 + Feature Flag ────→  SystemPromptBlock[]
                                                        │
                     SYSTEM_PROMPT_DYNAMIC_BOUNDARY      │
                     (静态/动态分区标记)                   │
                                                        ▼
                                                  splitSysPromptPrefix()
                                                  (分配 Cache Scope)
                                                        │
                                                        ▼
                                                  buildSystemPromptBlocks()
                                                  (添加 cache_control)
                                                        │
CLAUDE.md ────── loadClaudeMds() ─────→                 │
Git 状态 ────── getGitStatus() ──────→  getUserContext() │
日期 ──────────────────────────────→     │              │
                                         ▼              │
                                   prependUserContext()  │
                                   (<system-reminder>)   │
                                         │              │
消息历史 ──── 标准化 ──── 压缩检查 ──→    │              │
                                         ▼              ▼
                                    ┌─────────────────────┐
                                    │   API 请求           │
                                    │  system: Block[]     │
                                    │  messages: Message[] │
                                    │  tools: ToolSpec[]   │
                                    └─────────────────────┘
```

## 三、关键设计——`<system-reminder>` 注入

Claude Code 把 CLAUDE.md 内容放在**第一条用户消息**中（而非系统提示），用 `<system-reminder>` 标签包裹：

```typescript
createUserMessage({
  content: `<system-reminder>
As you answer the user's questions, you can use the following context:
# claudeMd
${claudeMdContent}
# currentDate
Today's date is ${date}.

IMPORTANT: this context may or may not be relevant...
</system-reminder>`,
  isMeta: true,  // UI 不显示，但模型可见
})
```

**为什么不放在系统提示中？**
1. 系统提示的静态前缀需要跨用户共享 Prompt Cache——CLAUDE.md 是项目特定的，会打破缓存
2. 用户消息的缓存粒度更细（org-level），不影响全局缓存
3. `isMeta: true` 确保 UI 不显示这条"注入的"消息

**Qwen Code 对标**：Qwen Code 的 QWEN.md 内容直接拼入系统提示——会打破 Prompt Cache 的前缀匹配。建议迁移到 `<system-reminder>` 注入模式。

## 四、消息标准化

原始消息来自多个来源（用户输入、工具结果、Hook 注入），格式各异。标准化确保所有消息满足同一结构契约：

| 原始来源 | 标准化处理 |
|---------|-----------|
| 用户文本输入 | 包裹为 `{role: "user", content: [{type: "text"}]}` |
| 工具结果 | 包裹为 `{role: "user", content: [{type: "tool_result"}]}` |
| 图片粘贴 | 转换为 `{type: "image", source: {type: "base64"}}` |
| `<system-reminder>` | 作为 `isMeta: true` 的用户消息前置 |
| 压缩摘要 | 替换被压缩的消息段 |

## 五、Prompt Cache 分区的管线位置

Cache 分区不是在系统提示构建时做的，而是在**管线最后一步**（`buildSystemPromptBlocks`）做的：

```
系统提示段落[]
  │
  ├─ 段落 1: 角色定义      ← 静态（不变）
  ├─ 段落 2: 行为规则      ← 静态
  ├─ 段落 3: 工具指南      ← 静态
  ├─ ── BOUNDARY ──
  ├─ 段落 4: 环境信息      ← 动态（每轮变）
  ├─ 段落 5: 记忆          ← 动态（会话间变）
  └─ 段落 6: MCP 指令      ← 动态（MCP 连接变）
        │
        ▼
  splitSysPromptPrefix()
        │
        ├─ 静态 → cache_control: {scope: "global"}
        └─ 动态 → cache_control: null（不缓存）
```

## 六、Qwen Code 改进建议

| 改进 | 描述 | 优先级 |
|------|------|--------|
| **QWEN.md → system-reminder 注入** | 项目指令从系统提示移到第一条用户消息 | P1 |
| **Prompt Cache 静态/动态分区** | 不变的行为指令放在前缀，确保缓存命中 | P1 |
| **显式消息标准化** | 所有来源的消息经过统一的 normalize 函数 | P2 |
| **isMeta 消息** | 支持 UI 不可见但模型可见的系统注入消息 | P2 |
