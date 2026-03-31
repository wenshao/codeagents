# 4. Claude Code 工具系统：架构与实现参考

> 工具系统是 Claude Code 与外部世界交互的核心接口。本文基于源码分析（`Tool.ts` 基类 + `tools/` 目录 ~163 文件、~50,000 行 TypeScript），覆盖 38 个显式工具 + MCP 动态工具的架构设计、权限模型、安全机制和实现细节。
>
> **适用场景**：其他 Code Agent 开发者设计工具系统时，可将本文作为架构参考。每个工具的 Zod schema、执行流程、安全检查都经过生产验证。

## 4.1 架构总览

### 4.1.1 工具分类

| 类别 | 工具数 | 加载方式 | 说明 |
|------|--------|----------|------|
| **核心工具** | 10 | 始终加载（`alwaysLoad`） | Read, Write, Edit, Bash, Glob, Grep, Agent, TodoWrite, ToolSearch, StructuredOutput |
| **延迟工具** | 24 | ToolSearch 按需加载（`shouldDefer`） | WebFetch, WebSearch, NotebookEdit, Task\*, Cron\*, Worktree\*, RemoteTrigger, Brief, AskUserQuestion, Skill, PlanMode\*, LSP, MCP 相关, Config |
| **内部工具** | 3 | 始终加载 | REPLTool, SleepTool, TaskStop（含 KillShell 别名） |
| **条件工具** | 1 | 仅 Windows | PowerShell |
| **MCP 工具** | ∞ | 动态注册 | `mcp__serverName__toolName` 格式，由 MCP 服务器提供 schema |

### 4.1.2 工具生命周期

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  注册阶段     │     │  权限检查     │     │  执行阶段     │     │  结果处理     │
│              │     │              │     │              │     │              │
│ buildTool()  │────→│isEnabled()   │────→│validateInput │────→│call()        │
│ 定义 schema  │     │validateInput │     │checkPerms    │     │返回 ToolResult│
│ 设置默认值   │     │checkPerms    │     │call()        │     │持久化大输出   │
└──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
```

**注册**：`buildTool()` 工厂函数填充安全默认值。所有 40+ 工具通过此工厂创建（核心 + 延迟 + 内部 + 条件，不含 MCP 动态工具）。

**权限检查顺序**：
1. `isEnabled()` — Feature gate 检查
2. `validateInput()` — 参数验证（短路返回错误码）
3. `checkPermissions()` — 权限规则匹配（allow/deny/ask）
4. `call()` — 实际执行

## 4.2 Tool 基类架构（源码: `Tool.ts`）

### 4.2.1 核心接口

```typescript
interface Tool<Input, Output, P> {
  readonly name: string                    // 工具名（如 'Bash', 'Edit'）
  aliases?: string[]                       // 向后兼容别名
  searchHint?: string                      // 3-10 词的 ToolSearch 关键词
  maxResultSizeChars: number               // 磁盘溢出阈值（字符数）
  readonly shouldDefer?: boolean           // true = 延迟加载
  readonly alwaysLoad?: boolean            // true = 始终在初始 prompt 中
  readonly strict?: boolean                // true = 严格 API 参数模式

  // 生命周期方法
  call(args, context, canUseTool, parentMessage, onProgress?): Promise<ToolResult<Output>>
  description(input, options): Promise<string>
  prompt(options): Promise<string>

  // 安全分类
  isEnabled(): boolean                     // Feature gate（默认 true）
  isReadOnly(input): boolean               // 只读操作（默认 false）
  isConcurrencySafe(input): boolean        // 可并行执行（默认 false）
  isDestructive?(input): boolean           // 不可逆操作（默认 false）

  // 验证与权限
  validateInput?(input, context): Promise<ValidationResult>
  checkPermissions(input, context): Promise<PermissionResult>
  preparePermissionMatcher?(input): Promise<(pattern) => boolean>

  // 中断行为
  interruptBehavior?(): 'cancel' | 'block' // 新用户输入时的行为
}
```

### 4.2.2 ToolResult 返回类型

```typescript
type ToolResult<T> = {
  data: T
  newMessages?: (UserMessage | AssistantMessage | AttachmentMessage | SystemMessage)[]
  contextModifier?: (context: ToolUseContext) => ToolUseContext
  mcpMeta?: { _meta?, structuredContent? }
}
```

- `newMessages`：工具可以向对话注入额外消息（如 Bash 检测到 git 操作后注入 git 状态消息）
- `contextModifier`：工具可以修改后续工具的执行上下文（如 SkillTool 注入 `allowedTools`）

### 4.2.3 ToolUseContext 执行上下文

传递给每个工具调用的上下文对象，包含：

| 字段 | 用途 |
|------|------|
| `options.tools` | 当前可用工具集合 |
| `options.mcpClients` | MCP 客户端连接池 |
| `options.agentDefinitions` | 已注册的 Agent 定义 |
| `abortController` | 取消信号 |
| `messages` | 完整对话历史 |
| `getAppState() / setAppState()` | 全局状态存储 |
| `readFileState` | 文件读取状态缓存（LRU，防重复读取 + 写前验证） |
| `agentId` | 子代理 ID（仅子代理设置） |
| `contentReplacementState` | 工具结果预算追踪 |

### 4.2.4 buildTool() 工厂默认值

| 方法 | 默认值 | 设计意图 |
|------|--------|----------|
| `isEnabled` | `() => true` | 默认启用 |
| `isConcurrencySafe` | `() => false` | 默认不可并行（安全侧） |
| `isReadOnly` | `() => false` | 默认为写操作（安全侧） |
| `isDestructive` | `() => false` | 默认非破坏性 |
| `checkPermissions` | `{ behavior: 'allow' }` | 默认允许 |
| `toAutoClassifierInput` | `() => ''` | 空分类输入 |

> **实现者注意**：默认值设计为「安全侧关闭」——不声明 `isConcurrencySafe` 就不允许并行，不声明 `isReadOnly` 就按写操作处理权限。

## 4.3 核心工具详解

### 4.3.1 Bash 工具（源码: `tools/BashTool/`，12,411 LOC）

Bash 是 Claude Code 中最复杂的核心工具，18 个源文件，包含命令执行、安全验证、权限模型三个子系统。

#### Zod 输入 Schema

| 字段 | 类型 | 说明 |
|------|------|------|
| `command` | `z.string()` | 要执行的命令 |
| `timeout` | `z.number().optional()` | 超时毫秒数（最大由 `getMaxTimeoutMs()` 决定） |
| `description` | `z.string().optional()` | 命令用途描述（5-10 词） |
| `run_in_background` | `z.boolean().optional()` | 后台运行（`CLAUDE_CODE_DISABLE_BACKGROUND_TASKS` 时省略） |
| `dangerouslyDisableSandbox` | `z.boolean().optional()` | 跳过沙箱 |
| `_simulatedSedEdit` | 内部字段 | 预计算的 sed 编辑结果（不暴露给模型） |

#### 执行流程

```
command 输入
    │
    ├─ _simulatedSedEdit 存在？ ──→ applySedEdit()（直接文件编辑，不经过 shell）
    │
    └─ Shell 执行路径：
        │
        ├─ run_in_background=true？ ──→ 后台任务 → backgroundTaskId
        │
        └─ 前台执行：
            ├─ 启动 ShellCommand.exec()
            ├─ 2 秒后显示进度（PROGRESS_THRESHOLD_MS）
            ├─ Kairos 模式：15 秒自动后台化（ASSISTANT_BLOCKING_BUDGET_MS）
            ├─ 用户可 Ctrl+B 手动后台化
            └─ 完成 → 后处理
```

#### 后处理管道

1. **Git 操作追踪**：检测命令是否触发了 git 操作
2. **语义结果解释**：`interpretCommandResult()` 将退出码映射为语义描述
3. **`.git/index.lock` 检测**：检测 git 锁文件冲突
4. **沙箱违规注释**：标注沙箱拒绝的操作
5. **大输出持久化**：超过 `maxResultSizeChars`（30,000 字符）→ 写入 `tool-results/` 目录；超过 `MAX_PERSISTED_SIZE`（64 MB）截断
6. **`<claude-code-hint />` 标签提取**：零 token 侧通道（工具输出的隐藏指令）
7. **图片输出检测**：检测二进制图片数据并自动调整大小

#### 命令分类

| 类别 | 命令 | UI 行为 |
|------|------|---------|
| **搜索命令** | `find`, `grep`, `rg`, `ag`, `ack`, `locate`, `which`, `whereis` | 可折叠显示 |
| **读取命令** | `cat`, `head`, `tail`, `less`, `more`, `wc`, `stat`, `file`, `strings`, `jq`, `awk` | 可折叠显示 |
| **列表命令** | `ls`, `tree`, `du` | 可折叠显示 |
| **静默命令** | `mv`, `cp`, `rm`, `mkdir`, `chmod`, `touch`, `ln`, `cd`, `export` | 成功时无输出 |
| **语义中性** | `echo`, `printf`, `true`, `false`, `:` | 无副作用 |
| **禁止后台** | `sleep` | 阻止 `sleep N`（N≥2）作为首命令 |

#### 安全验证管道（源码: `bashSecurity.ts`，2,593 行）

23 层验证器，分为早期验证器（可短路通过）和主验证器（全部必须通过）：

**早期验证器（可返回 allow 短路）**：

| # | 验证器 | 功能 |
|---|--------|------|
| 1 | `validateEmpty` | 空命令安全 |
| 2 | `validateIncompleteCommands` | 阻止以 Tab、`-`、`&&`、`||`、`;`、`>>`、`<` 开头的命令 |
| 3 | `validateSafeCommandSubstitution` | 仅允许 `$(cat <<'DELIM'...DELIM)` 形式的 heredoc |
| 4 | `validateGitCommit` | 允许简单 `git commit -m "..."`，阻止 commit 中的命令替换 |

**主验证器（全部必须通过）**：

| # | 验证器 | 防御目标 |
|---|--------|----------|
| 5 | `validateJqCommand` | 阻止 `jq system()` 和危险标志 |
| 6 | `validateObfuscatedFlags` | 检测 ANSI-C 引用、Locale 引用、空引号对、引号链等混淆技术 |
| 7 | `validateShellMetacharacters` | 引号内的 `;`、`|`、`&` |
| 8 | `validateDangerousVariables` | 重定向/管道旁的变量 |
| 9 | `validateCommentQuoteDesync` | `#` 注释中的引号字符导致下游追踪器失同步 |
| 10 | `validateQuotedNewline` | 引号内换行 + `#` 行利用 |
| 11 | `validateCarriageReturn` | CR 导致 shell-quote/bash 解析差异 |
| 12 | `validateNewlines` | 可分隔命令的换行 |
| 13 | `validateIFSInjection` | `$IFS` 和 `${...IFS...}` |
| 14 | `validateProcEnvironAccess` | `/proc/*/environ` 路径 |
| 15 | `validateDangerousPatterns` | 反引号、进程替换 `<()`、命令替换 `$()`、参数替换 `${}`、Zsh 展开 |
| 16 | `validateRedirections` | 输入/输出重定向 |
| 17 | `validateBackslashEscapedWhitespace` | `\<space>` 解析差异 |
| 18 | `validateBackslashEscapedOperators` | `\;`、`\|`、`\&` 解析差异 |
| 19 | `validateUnicodeWhitespace` | Unicode 空白字符解析不一致 |
| 20 | `validateMidWordHash` | `#` 的注释/字面量歧义 |
| 21 | `validateBraceExpansion` | Bash 大括号展开 `{a,b}` |
| 22 | `validateZshDangerousCommands` | `zmodload`、`emulate`、`sysopen` 等 Zsh 命令 |
| 23 | `validateMalformedTokenInjection` | 不平衡分隔符 + 命令分隔符组合 |

> **实现者注意**：这套安全验证管道是 Claude Code 最核心的安全防线。23 层验证器的设计思路是：**防御 shell-quote 和 bash 之间的解析差异（misparsing）**，而非仅防御已知攻击模式。每个验证器都针对一种特定的解析差异场景。

#### 权限模型（源码: `bashPermissions.ts`，2,622 行）

**安全环境变量白名单**（41 个）：Go/Rust/Node/Python/Locale/Terminal/Color 变量在权限匹配前可安全剥离。

**显式排除**：`PATH`、`LD_PRELOAD`、`LD_LIBRARY_PATH`、`DYLD_*`、`PYTHONPATH`、`NODE_PATH`、`NODE_OPTIONS`、`HOME`、`SHELL`、`BASH_ENV` 等。

**禁止作为规则前缀的 shell 名**：`sh`、`bash`、`zsh`、`fish`、`sudo`、`env`、`xargs` 等 19 个（`bash:*` 会自动批准任意代码执行）。

**权限建议逻辑**：从命令提取 2 词前缀（如 `git commit`、`npm run`）生成 allow/deny 规则建议。heredoc 命令取 `<<` 前的前缀，多行命令取首行。

#### Bash 工具 Prompt（源码: `prompt.ts`）

模型接收的 Bash 工具 prompt 动态组装，包含以下部分：

1. **工具偏好覆盖**：指导模型优先使用专用工具而非 shell 命令（Glob > find，Grep > grep，Edit > sed）
2. **工作目录**：支持持久化但不保持 shell 状态
3. **沙箱指令**：根据沙箱配置动态注入文件系统/网络限制
4. **Git commit/PR 工作流**：详细的并行命令、HEREDOC 格式、安全规则（不 `--no-verify`、不 force push main、不 `git add -A`）

---

### 4.3.2 Edit 工具（源码: `tools/FileEditTool/`，1,812 LOC）

#### Zod 输入 Schema

| 字段 | 类型 | 约束 |
|------|------|------|
| `file_path` | `z.string()` | 绝对路径 |
| `old_string` | `z.string()` | 要替换的文本 |
| `new_string` | `z.string()` | 替换后文本（必须与 old_string 不同） |
| `replace_all` | `z.boolean()` | 默认 false；true = 替换所有匹配 |

#### 字符串匹配管道（三层回退）

| 层级 | 方法 | 说明 |
|------|------|------|
| 1 | 精确匹配 | `fileContent.includes(searchString)` |
| 2 | 引号归一化 | 弯引号 `''""` → 直引号 `'"` 后匹配，返回文件原文（保留弯引号风格） |
| 3 | 反净化映射 | `<fnr>` → `<function_results>` 等 XML 标签还原 |

> **注意**：没有模糊/Levenshtein 匹配。匹配要么精确，要么基于特定的归一化替换。

#### 引号风格保留（`preserveQuoteStyle`）

当通过弯引号归一化匹配时，`new_string` 会自动应用相同的弯引号风格：
- 开闭启发式：引号前为空白/`(`/`[`/`{`/破折号/字符串开头 = 开引号，否则 = 闭引号
- 撇号例外：字母 + `'` + 字母 → 右弯引号（"don't"、"it's" 正确处理）

#### 验证管道（10 个错误码）

| 错误码 | 条件 |
|--------|------|
| 0 | 团队记忆中的机密检测 |
| 1 | `old_string === new_string`（空操作） |
| 2 | 路径在权限拒绝目录中 |
| 3 | 文件已存在（空 old_string = 创建尝试） |
| 4 | 文件不存在（附带相似文件/CWD 建议） |
| 5 | `.ipynb` 文件（必须用 NotebookEditTool） |
| 6 | 文件未被读取过（readFileState 检查） |
| 7 | 文件自上次读取后被修改（mtime 检查；Windows 用内容比较回退） |
| 8 | `old_string` 未找到 |
| 9 | 多个匹配但 `replace_all` 为 false |

#### 写入安全：mtime 临界区

```typescript
// 临界区内（同步）：
const { content, mtimeMs } = readFileSyncWithMetadata(filePath)
if (readFileState.mtimeMs !== mtimeMs) throw staleError  // 过期写入保护
writeTextContent(filePath, newContent)  // 原子写入
// 临界区结束——mtime 检查和写入之间没有 async 操作
```

- 编码检测：字节 `0xFF 0xFE` → `utf16le`，否则 `utf8`
- 行尾始终写 LF（保留 CRLF 曾导致跨平台损坏）
- 最大文件：1 GiB（`MAX_EDIT_FILE_SIZE`）

---

### 4.3.3 Read 工具（源码: `tools/FileReadTool/`，1,602 LOC）

#### Zod 输入 Schema

| 字段 | 类型 | 说明 |
|------|------|------|
| `file_path` | `z.string()` | 绝对路径 |
| `offset` | `z.number().optional()` | 起始行（1-based） |
| `limit` | `z.number().optional()` | 行数 |
| `pages` | `z.string().optional()` | PDF 页范围（如 "1-5"） |

#### 支持的文件类型

| 类型 | 扩展名 | 处理方式 |
|------|--------|----------|
| **文本** | 默认 | 行号格式输出（`cat -n` 风格），默认最多 2,000 行 |
| **图片** | `png/jpg/jpeg/gif/webp` | sharp 压缩管线：调整大小 → token 预算检查 → 激进压缩 → 400×400 JPEG q20 回退 |
| **PDF** | `.pdf` | 小 PDF 内联发送；大 PDF 要求 `pages` 参数提取为 JPEG |
| **Notebook** | `.ipynb` | JSON 序列化，大小 + token 检查 |
| **二进制** | 其他 | 拒绝（除 PDF 和图片） |

#### 读取限制

| 限制 | 默认值 | 来源 |
|------|--------|------|
| `maxSizeBytes` | 256 KB | GrowthBook `tengu_amber_wren` 或硬编码 |
| `maxTokens` | 25,000 | `CLAUDE_CODE_FILE_READ_MAX_OUTPUT_TOKENS` > GrowthBook > 默认 |
| `MAX_LINES_TO_READ` | 2,000 | 硬编码 |

#### 读取去重

相同 `(file_path, offset, limit)` 且 mtime 未变 → 返回 `file_unchanged` 存根。受 GrowthBook killswitch `tengu_read_dedup_killswitch` 控制。

#### 安全限制

阻止读取的设备路径：`/dev/zero`、`/dev/random`、`/dev/urandom`、`/dev/full`、`/dev/stdin`、`/dev/tty`、`/dev/console`、`/dev/fd/0-2`、`/proc/*/fd/0-2`。

---

### 4.3.4 Write 工具（源码: `tools/FileWriteTool/`，856 LOC）

#### Zod 输入 Schema

| 字段 | 类型 | 说明 |
|------|------|------|
| `file_path` | `z.string()` | 绝对路径 |
| `content` | `z.string()` | 完整文件内容 |

#### 验证管道

| 错误码 | 条件 |
|--------|------|
| 0 | 团队记忆中的机密 |
| 1 | 路径被权限设置拒绝 |
| 2 | 已存在文件未被读取（readFileState 检查） |
| 3 | 文件自读取后被修改（mtime 比较） |
| — | **新文件**（ENOENT）：直接允许，无 read-first 要求 |

#### 原子写入模式

```
临界区外（async 安全）：
  mkdir -p 父目录
  fileHistoryTrackEdit()（幂等备份）

临界区内（同步）：
  readFileSyncWithMetadata() → mtime 检查 → writeTextContent()
  └── 无 async 操作在 mtime 检查和写入之间
```

- 行尾：始终 LF（保留 CRLF 曾导致跨平台损坏）
- 编码：保留原文件检测的编码，新文件默认 `utf8`
- Prompt 明确指导模型：Edit 用于修改（只发 diff），Write 仅用于新文件或完全重写

---

### 4.3.5 Grep 工具（源码: `tools/GrepTool/`，795 LOC）

#### Zod 输入 Schema

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `pattern` | `z.string()` | — | 正则表达式 |
| `path` | `z.string()` | cwd | 搜索路径 |
| `glob` | `z.string()` | — | 文件过滤（如 `*.ts`） |
| `output_mode` | `z.enum([...])` | `files_with_matches` | 输出模式：content/files_with_matches/count |
| `-i` | `z.boolean()` | false | 忽略大小写 |
| `type` | `z.string()` | — | ripgrep 类型过滤 |
| `head_limit` | `z.number()` | 250 | 最大结果数 |
| `multiline` | `z.boolean()` | false | 多行模式 |

#### Ripgrep 调用参数

- `--hidden`（包含隐藏文件）
- 排除 VCS 目录：`--glob !{.git,.svn,.hg,.bzr,.jj,.sl}`
- `--max-columns 500`（防止 base64/minified 内容膨胀输出）
- 多行模式：`-U --multiline-dotall`
- 模式以 `-` 开头时使用 `-e` 标志
- 排除模式：来自 `getFileReadIgnorePatterns()` + 孤立插件排除

`files_with_matches` 模式按**修改时间**排序（最新优先），文件名相同则按字母排序。

---

### 4.3.6 Agent 工具（源码: `tools/AgentTool/`，6,072 LOC）

Agent 是 Claude Code 的子代理系统，支持四种生成模式：

#### Zod 输入 Schema

| 字段 | 类型 | 说明 |
|------|------|------|
| `description` | `z.string()` | 任务描述（3-5 词） |
| `prompt` | `z.string()` | 任务内容 |
| `subagent_type` | `z.string().optional()` | Agent 类型（省略 = fork 或通用） |
| `model` | `z.enum(['sonnet','opus','haiku']).optional()` | 模型选择 |
| `run_in_background` | `z.boolean().optional()` | 后台执行 |
| `name` | `z.string().optional()` | Teammate 名称 |
| `team_name` | `z.string().optional()` | 团队上下文 |
| `mode` | `permissionModeSchema().optional()` | 权限模式 |
| `isolation` | `z.enum([...]).optional()` | 隔离模式（worktree/remote） |
| `cwd` | `z.string().optional()` | 工作目录覆盖 |

#### 四种生成模式（优先级递减）

| 模式 | 触发条件 | 隔离性 | 上下文 |
|------|----------|--------|--------|
| **Teammate** | `team_name` + `name` 设置 | tmux 分屏 + worktree | 独立进程，消息传递 |
| **Remote** | `isolation: 'remote'`（仅 Ant） | CCR 远程执行 | 完全隔离 |
| **Fork** | 无 `subagent_type` + `isForkSubagentEnabled()` | 共享进程 | **继承父级完整上下文**（最大 prompt cache 命中） |
| **Subagent** | 其他情况 | 共享进程 | 独立上下文 |

#### Fork 子代理机制

Fork 是最高效的子代理模式：

1. **消息构造**：克隆父级的 assistant message（所有 content blocks），构建占位 `tool_result`（"Fork started -- processing in background"），追加子指令
2. **递归防护**：扫描消息中的 `<fork_boilerplate>` 标签或 `querySource === 'agent:builtin:fork'`
3. **Fork 规则**：不可再 fork、不可对话、直接使用工具、commit 后报告、500 词限制
4. **输出格式**：`Scope:` / `Result:` / `Key files:` / `Files changed:` / `Issues:`

#### 工具过滤

子代理的工具集经过多层过滤：

1. MCP 工具（`mcp__*`）始终允许
2. `ALL_AGENT_DISALLOWED_TOOLS` 对所有代理禁用
3. `CUSTOM_AGENT_DISALLOWED_TOOLS` 对非内置代理禁用
4. `ASYNC_AGENT_ALLOWED_TOOLS` 限制异步代理的工具集
5. Agent 定义中的 `tools`/`disallowedTools` 字段进一步过滤

#### Agent 定义系统

支持三种来源（优先级递减）：

| 来源 | 说明 |
|------|------|
| **内置** | 代码中硬编码（Explore, Plan 等） |
| **插件** | `plugins/` 注册 |
| **用户/项目** | `.claude/agents/*.md` 或 settings.json |

**Markdown Agent 格式**（`.claude/agents/` 目录）：
- Frontmatter：`name`（必需）、`description`（必需）、`color`、`model`、`background`、`memory`、`isolation`、`permissionMode`、`maxTurns`、`tools`、`mcpServers`、`hooks`
- Body：系统 prompt

---

### 4.3.7 ToolSearch 工具（源码: `tools/ToolSearchTool/`，593 LOC）

延迟工具的搜索引擎。

#### Zod Schema

| 字段 | 类型 | 说明 |
|------|------|------|
| `query` | `z.string()` | `"select:ToolName"` 直接选择，或关键词搜索 |
| `max_results` | `z.number()` | 默认 5 |

#### 关键词搜索评分算法

| 匹配类型 | 权重 |
|----------|------|
| 工具名精确匹配（部分） | +10（MCP: +12） |
| 工具名部分匹配 | +5（MCP: +6） |
| 全名回退匹配 | +3 |
| `searchHint` 匹配 | +4 |
| 描述匹配 | +2 |

`select:` 前缀支持逗号分隔的批量选择（如 `select:WebFetch,WebSearch`）。

---

## 4.4 延迟加载工具详解

### 4.4.1 WebFetch 工具（源码: `tools/WebFetchTool/`，1,131 LOC）

| 字段 | 类型 | 说明 |
|------|------|------|
| `url` | `z.string().url()` | 目标 URL |
| `prompt` | `z.string()` | 对获取内容的处理 prompt |

- **预批准域名**：自动允许，无需用户确认
- **跨域重定向**：不自动跟随，返回新 URL 让用户批准
- Markdown 且小于 `MAX_MARKDOWN_LENGTH` → 跳过 LLM 处理，直接返回原文
- `isConcurrencySafe: true`，`isReadOnly: true`

### 4.4.2 WebSearch 工具（源码: `tools/WebSearchTool/`，569 LOC）

| 字段 | 类型 | 说明 |
|------|------|------|
| `query` | `z.string().min(2)` | 搜索查询 |
| `allowed_domains` | `z.array(z.string()).optional()` | 域名白名单 |
| `blocked_domains` | `z.array(z.string()).optional()` | 域名黑名单 |

- 使用 Anthropic API 的 `web_search_20250305` 工具（每调用最多 8 次搜索）
- `isEnabled()` 取决于提供商：FirstParty/Foundry 始终启用；Vertex 仅 Claude 4.0+

### 4.4.3 NotebookEdit 工具（源码: `tools/NotebookEditTool/`，587 LOC）

| 字段 | 类型 | 说明 |
|------|------|------|
| `notebook_path` | `z.string()` | .ipynb 文件绝对路径 |
| `cell_id` | `z.string().optional()` | 单元格 ID（insert 时省略） |
| `new_source` | `z.string()` | 新单元格内容 |
| `cell_type` | `z.enum(['code','markdown']).optional()` | insert 时必需 |
| `edit_mode` | `z.enum(['replace','insert','delete']).optional()` | 默认 replace |

- 强制 read-before-edit（error codes 9, 10）
- replace 自动重置 `execution_count: null` 并清除 `outputs`
- nbformat ≥ 4.5 自动分配随机 cell ID

### 4.4.4 Task 工具组（V2）

| 工具 | 输入 | 说明 |
|------|------|------|
| **TaskCreate** | `subject`, `description`, `activeForm?`, `metadata?` | 创建任务（支持 blocks/blockedBy 依赖） |
| **TaskGet** | `taskId` | 获取任务详情 |
| **TaskUpdate** | `taskId`, `status?`, `subject?`, `description?`, `addBlocks?`, `addBlockedBy?`, `owner?`, `metadata?` | 更新任务（`status: 'deleted'` 删除） |
| **TaskList** | — | 列出所有任务 |

- Feature gate：`isTodoV2Enabled()`
- **验证提醒**：主线程完成 3+ 任务后，自动建议生成验证代理
- 团队集成：teammate 标记 `in_progress` 时自动设置 owner；owner 变更通知

### 4.4.5 Cron 工具（源码: `tools/ScheduleCronTool/`）

| 字段 | 类型 | 说明 |
|------|------|------|
| `cron` | `z.string()` | 5 字段 cron 表达式（本地时间） |
| `prompt` | `z.string()` | 要执行的 prompt |
| `recurring` | `z.boolean()` | 默认 true；false = 一次性 |
| `durable` | `z.boolean()` | 默认 false；true = 持久化到 `.claude/scheduled_tasks.json` |

- 上限：50 个定时任务/会话
- Teammate 不能创建 durable cron（验证拒绝 error code 4）
- Feature gate：`isKairosCronEnabled()`

### 4.4.6 Worktree 工具

**EnterWorktree**：创建 Git worktree，`process.chdir()` 切换目录，清除缓存。

**ExitWorktree**：`action: 'keep' | 'remove'`。remove 时统计变更文件数和提交数，kill tmux session，`cleanupWorktree()`。

### 4.4.7 Brief 工具（源码: `tools/BriefTool/`，610 LOC）

Kairos 模式下的用户消息工具：

| 字段 | 类型 | 说明 |
|------|------|------|
| `message` | `z.string()` | Markdown 消息 |
| `attachments` | `z.array(z.string()).optional()` | 附件路径 |
| `status` | `z.enum(['normal','proactive'])` | proactive = 主动更新 |

双层 Feature gate：`isBriefEntitled()`（构建时 + 运行时 + GB）→ `isBriefEnabled()`（opt-in 来源：`--brief`、settings、`/brief`、env var）。

### 4.4.8 AskUserQuestion 工具（源码: `tools/AskUserQuestionTool/`，309 LOC）

| 字段 | 类型 | 约束 |
|------|------|------|
| `questions` | `z.array(questionSchema)` | 1-4 个问题 |
| `metadata` | `z.object({source}).optional()` | 分析来源 |

每个问题：`{ question, header(≤12字符), options(2-4个), multiSelect }`。始终 `behavior: 'ask'`。

### 4.4.9 SendMessage 工具（源码: `tools/SendMessageTool/`，997 LOC）

| 字段 | 类型 | 说明 |
|------|------|------|
| `to` | `z.string()` | Teammate 名 / `*`(广播) / `uds:<socket>` / `bridge:<session-id>` |
| `message` | `z.string() | StructuredMessage` | 消息内容 |
| `summary` | `z.string().optional()` | 5-10 词预览（纯文本消息必需） |

结构化消息类型：`shutdown_request`、`shutdown_response`、`plan_approval_response`。

跨会话消息（`bridge:` 前缀）：通过 Remote Control 的 `postInterClaudeMessage()` 传递，始终要求用户确认（跨机器 prompt 注入风险）。

### 4.4.10 Team 工具

**TeamCreate**：`team_name`, `description?`, `agent_type?`。创建 `TeamFile`，注册 lead 为首个成员。

**TeamDelete**：清理团队文件、任务列表、tmux session。

Feature gate：`isAgentSwarmsEnabled()`。

### 4.4.11 LSP 工具（源码: `tools/LSPTool/`，2,005 LOC）

9 种操作：`goToDefinition`、`findReferences`、`hover`、`documentSymbol`、`workspaceSymbol`、`goToImplementation`、`prepareCallHierarchy`、`incomingCalls`、`outgoingCalls`。

`isEnabled()` = `isLspConnected()`。最大文件：10 MB。

### 4.4.12 RemoteTrigger 工具

| 字段 | 类型 | 说明 |
|------|------|------|
| `action` | `z.enum(['list','get','create','update','run'])` | CRUD + 执行 |
| `trigger_id` | `z.string()` | 操作对象 ID |
| `body` | `z.record(z.string(), z.unknown())` | 请求体 |

Feature gate：`tengu_surreal_dali` + `isPolicyAllowed('allow_remote_sessions')`。OAuth 认证，API 路径 `/v1/code/triggers`。

### 4.4.13 Config 工具

| 字段 | 类型 | 说明 |
|------|------|------|
| `setting` | `z.string()` | 设置键 |
| `value` | `z.string() | z.boolean() | z.number()` | 省略 = 获取当前值 |

GET 自动允许；SET 需要用户确认。`remoteControlAtStartup` 特殊处理："default" 清除键值。

### 4.4.14 Plan 模式工具

**EnterPlanMode**：无参数。切换到 plan 权限模式（只读 + 计划文件写入）。分面试阶段（最小指令）和传统阶段（6 步探索/规划/设计）。

**ExitPlanMode**：`allowedPrompts?`（Bash prompt 规则）。Teammate 需 team lead 审批计划后才可退出。自动模式门控：circuit breaker 触发时回退到 default 模式。

### 4.4.15 Skill 工具（源码: `tools/SkillTool/`，1,477 LOC）

| 字段 | 类型 | 说明 |
|------|------|------|
| `skill` | `z.string()` | 技能名 |
| `args` | `z.string().optional()` | 参数 |

两种执行模式：
- **Inline**：注入消息到当前对话
- **Forked**：在隔离子代理中执行（`command.context === 'fork'`）

权限检查管道：deny 规则 → 远程 canonical 技能自动允许 → allow 规则 → 安全属性自动允许（`SAFE_SKILL_PROPERTIES` 白名单 ~30 个键）→ 默认 ask。

---

## 4.5 MCP 工具集成（源码: `tools/MCPTool/`）

### 4.5.1 动态注册

MCP 工具以 `mcp__serverName__toolName` 格式动态注册（注意**双下划线**）。每个 MCP 服务器启动时，其工具 schema 被解析为 `Tool` 实例。

### 4.5.2 MCPTool 基类

MCPTool 是模板/桩：`z.object({}).passthrough()` 接受任意输入，`z.string()` 输出。实际行为在 `mcpClient.ts` 中为每个工具单独创建。

关键属性：`isMcp: true`，`checkPermissions` 始终 `behavior: 'passthrough'`。

### 4.5.3 MCP 认证工具

**McpAuthTool**：处理 MCP 服务器的 OAuth 认证流程。

### 4.5.4 MCP 资源工具

**ReadMcpResourceTool** + **ListMcpResourcesTool**：读取和列举 MCP 服务器暴露的资源。

---

## 4.6 跨工具安全架构

### 4.6.1 权限系统

**PermissionMode 枚举**：

| 模式 | 行为 |
|------|------|
| `default` | 每次操作需用户确认 |
| `acceptEdits` | 文件编辑自动允许，其他需确认 |
| `plan` | 只读 + 计划文件写入 |
| `auto` | 基于分类器的自动允许（circuit breaker 保护） |
| `bypassPermissions` | 跳过所有权限检查（需 `--dangerously-skip-permissions`） |

**权限规则来源**（优先级递减）：

1. CLI 参数（`--allowedTools`）
2. 设置文件（`.claude/settings.json`）
3. 项目配置（`.claude/settings.local.json`）
4. 用户交互（允许/拒绝 + 生成规则建议）

### 4.6.2 Read-Before-Write 保护

Edit 和 Write 工具共享 `readFileState`（LRU 缓存，Map<path, { content, timestamp, offset, limit }>）：

1. **写入前必须读取**：文件必须在本次会话中通过 Read 工具读取过
2. **mtime 校验**：写入时检查文件 mtime，与读取时记录对比
3. **同步临界区**：mtime 检查和写入之间不允许 async 操作（防并发编辑交错）
4. **Windows 回退**：mtime 不可靠时使用内容比较（防云同步/杀毒软件误报）

### 4.6.3 大输出持久化

所有工具共享的大输出处理模式：

1. 工具结果超过 `maxResultSizeChars` → 写入 `tool-results/` 目录
2. 返回 `<persisted-output>` 标签 + 预览片段
3. 超过 `MAX_PERSISTED_SIZE`（64 MB）截断
4. 路径格式：`tool-results/<tool-name>-<timestamp>.txt`

### 4.6.4 文件历史追踪

Edit 和 Write 调用 `fileHistoryTrackEdit()` 进行幂等备份，支持撤销操作。

### 4.6.5 UNC 路径安全

Windows SMB 路径（`\\server\share`）在 Edit、Write、NotebookEdit、LSPTool 中被拦截，防止 NTLM 凭据泄露。

### 4.6.6 Team Memory 机密扫描

Edit、Write、TodoWrite 在内容中检测 Team Memory 机密（error code 0），阻止意外泄露。

---

## 4.7 工具完整清单

| # | 工具名 | LOC | 加载 | 只读 | 并发安全 | Feature Gate |
|---|--------|-----|------|------|----------|-------------|
| 1 | **Bash** | 12,411 | 核心 | ✗ | ✗ | — |
| 2 | **Edit** | 1,812 | 核心 | ✗ | ✗ | — |
| 3 | **Read** | 1,602 | 核心 | ✓ | ✓ | — |
| 4 | **Write** | 856 | 核心 | ✗ | ✗ | — |
| 5 | **Grep** | 795 | 核心 | ✓ | ✓ | — |
| 6 | **Glob** | — | 核心 | ✓ | ✓ | — |
| 7 | **Agent** | 6,072 | 核心 | ✗ | ✗ | — |
| 8 | **TodoWrite** | 300 | 核心 | ✗ | ✗ | `!isTodoV2Enabled` |
| 9 | **ToolSearch** | 593 | 核心 | ✓ | ✓ | — |
| 10 | **StructuredOutput** | 163 | 核心 | ✗ | ✗ | `isNonInteractiveSession` |
| 11 | **PowerShell** | 8,959 | 条件 | ✗ | ✗ | Windows |
| 12 | **LSP** | 2,005 | 延迟 | ✓ | ✓ | `isLspConnected` |
| 13 | **Skill** | 1,477 | 延迟 | ✗ | ✗ | — |
| 14 | **MCPTool** | 1,086 | 动态 | varies | varies | — |
| 15 | **WebFetch** | 1,131 | 延迟 | ✓ | ✓ | — |
| 16 | **SendMessage** | 997 | 延迟 | varies | ✗ | `isAgentSwarmsEnabled` |
| 17 | **NotebookEdit** | 587 | 延迟 | ✗ | ✗ | — |
| 18 | **Brief** | 610 | 延迟 | ✗ | ✗ | KAIROS |
| 19 | **ExitPlanMode** | 605 | 延迟 | ✗ | ✗ | — |
| 20 | **ExitWorktree** | 386 | 延迟 | ✗ | ✗ | — |
| 21 | **EnterPlanMode** | 329 | 延迟 | ✓ | ✓ | — |
| 22 | **TeamCreate** | 359 | 延迟 | ✗ | ✗ | `isAgentSwarmsEnabled` |
| 23 | **AskUserQuestion** | 309 | 延迟 | ✓ | ✗ | — |
| 24 | **WebSearch** | 569 | 延迟 | ✓ | ✓ | Provider check |
| 25 | **TaskUpdate** | 484 | 延迟 | ✗ | ✗ | `isTodoV2Enabled` |
| 26 | **ScheduleCron** | 543 | 延迟 | ✗ | ✗ | `isKairosCronEnabled` |
| 27 | **TaskOutput** | 584 | 延迟 | ✓ | ✓ | — |
| 28 | **McpAuth** | 215 | 延迟 | ✗ | ✗ | — |
| 29 | **ReadMcpResource** | 210 | 延迟 | ✓ | ✓ | — |
| 30 | **ListMcpResources** | 171 | 延迟 | ✓ | ✓ | — |
| 31 | **TeamDelete** | 175 | 延迟 | ✗ | ✗ | `isAgentSwarmsEnabled` |
| 32 | **TaskList** | 166 | 延迟 | ✓ | ✓ | `isTodoV2Enabled` |
| 33 | **TaskGet** | 153 | 延迟 | ✓ | ✓ | `isTodoV2Enabled` |
| 34 | **TaskStop** | 179 | 内部 | ✗ | ✗ | — |
| 35 | **TaskCreate** | 195 | 延迟 | ✗ | ✗ | `isTodoV2Enabled` |
| 36 | **RemoteTrigger** | 192 | 延迟 | varies | ✗ | `tengu_surreal_dali` + policy |
| 37 | **EnterWorktree** | 177 | 延迟 | ✗ | ✗ | — |
| 38 | **Config** | 809 | 延迟 | varies | ✗ | — |
| 39 | **REPLTool** | 85 | 内部 | ✗ | ✗ | `isReplModeEnabled` |
| 40 | **SleepTool** | 17 | 内部 | ✓ | ✓ | PROACTIVE/KAIROS |

> **总计**：38 个显式工具 + MCP 动态工具（∞）。其中 TaskStop 含 KillShell 别名；Edit 工具同时处理单次编辑和 replace_all 批量编辑（无需独立 MultiEdit 工具）。

---

## 4.8 实现者 Checklist

> 其他 Code Agent 开发者设计工具系统时的关键决策参考。

| # | 设计决策 | Claude Code 的选择 | 实现考量 |
|---|----------|-------------------|----------|
| **1** | **工具注册方式？** | `buildTool()` 工厂 + 安全默认值（fail-closed） | 工厂模式确保新增工具不会遗漏安全方法 |
| **2** | **延迟加载策略？** | `shouldDefer` 标记 + `ToolSearch` 搜索引擎 | 核心 ~10 个工具始终加载，其余按需发现，减少 prompt token 开销 |
| **3** | **权限检查放在哪？** | 三阶段：`validateInput` → `checkPermissions` → `call()` | 验证和权限解耦；验证可短路返回错误码（telemetry 用） |
| **4** | **如何防 shell 注入？** | 23 层验证器管道（bashSecurity.ts） | 核心：防御 shell-quote/bash 解析差异，不只是已知攻击模式 |
| **5** | **如何防并发编辑冲突？** | readFileState LRU 缓存 + mtime 临界区 | mtime 检查和写入之间不允许 async（同步临界区） |
| **6** | **大工具输出如何处理？** | `maxResultSizeChars` 阈值 → 磁盘溢出 + 预览片段 | 统一的持久化模式，64 MB 截断上限 |
| **7** | **子代理上下文隔离？** | Fork 继承完整上下文（max cache hit）；Subagent 独立上下文 | Fork 的 prompt cache 命中率显著高于独立上下文 |
| **8** | **Agent 工具如何选模型？** | `getAgentModel()` 解析：agentDef.model → mainLoopModel → paramOverride | 读取/探索类代理可用更便宜模型（Haiku） |
| **9** | **MCP 工具如何安全？** | `mcp__` 命名空间 + 每工具独立 schema + passthrough 权限 | MCP 工具的权限由 MCP 服务器自行定义 |
| **10** | **工具 prompt 如何管理 token？** | 动态组装：按需注入沙箱指令、Agent 列表（attachment 优化） | Agent 列表用 attachment 避免缓存失效（~10.2% 舰队 cache_creation token 节省） |

---

> **数据来源**：本文全部技术细节来自源码分析（`Tool.ts` + `tools/` 目录 163 文件、~50,000 行 TypeScript），经 [EVIDENCE.md](./EVIDENCE.md) 交叉验证。
