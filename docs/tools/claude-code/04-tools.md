# 4. Claude Code 工具系统：架构与实现参考

> 工具系统是 Claude Code 与外部世界交互的核心接口。本文基于源码分析（`Tool.ts` 基类 + `tools/` 目录 ~163 文件、~50,000 行 TypeScript），覆盖 39 个显式工具 + MCP 动态工具的架构设计、权限模型、安全机制和实现细节。
>
> **适用场景**：其他 Code Agent 开发者设计工具系统时，可将本文作为架构参考。每个工具的 Zod schema、执行流程、安全检查都经过生产验证。
>
> **计数规则**：39 = 10 核心（始终加载）+ 25 延迟（ToolSearch 按需加载）+ 3 内部 + 1 条件（Windows PowerShell）。不含 MCP 动态工具（数量由 MCP 服务器决定）。其中 TaskStop 含 KillShell 别名，Edit 含 replace_all 批量编辑模式，均非独立工具。用户常见/常驻工具约 10 个（核心工具），其余按功能需求动态激活。

## 4.1 架构总览

### 4.1.1 工具分类

> 以下按**加载方式**分类。同一工具可能同时受 Feature gate 限制（如 TaskCreate 受 `isTodoV2Enabled` 门控），但加载方式和门控是独立维度。

| 类别 | 工具数 | 加载方式 | 说明 |
|------|--------|----------|------|
| **核心工具** | 10 | 始终加载（`alwaysLoad`） | Read, Write, Edit, Bash, Glob, Grep, Agent, TodoWrite, ToolSearch, StructuredOutput |
| **延迟工具** | 25 | ToolSearch 按需加载（`shouldDefer`） | WebFetch, WebSearch, NotebookEdit, Task\*, Cron\*, Worktree\*, RemoteTrigger, Brief, AskUserQuestion, Skill, PlanMode\*, LSP, MCP 相关, Config |
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
type Tool<
  Input extends AnyObject = AnyObject,
  Output = unknown,
  P extends ToolProgressData = ToolProgressData,
> = {
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
  prompt(options: {
    getToolPermissionContext: () => Promise<ToolPermissionContext>
    tools: Tools
    agents: AgentDefinition[]
    allowedAgentTypes?: string[]
  }): Promise<string>

  // 安全分类
  isEnabled(): boolean                     // Feature gate（默认 true）
  isReadOnly(input): boolean               // 只读操作（默认 false）
  isConcurrencySafe(input): boolean        // 可并行执行（默认 false）
  isDestructive?(input): boolean           // 不可逆操作（默认 false）
  isSearchOrReadCommand?(input): boolean   // 搜索/读取命令标记
  isOpenWorld?(): boolean                  // 开放世界工具标记

  // 验证与权限
  validateInput?(input, context): Promise<ValidationResult>
  checkPermissions(input, context): Promise<PermissionResult>
  preparePermissionMatcher?(input): Promise<(pattern) => boolean>

  // 中断行为
  interruptBehavior?(): 'cancel' | 'block' // 新用户输入时的行为

  // 辅助方法
  userFacingName?(input): string           // 用户可见的工具名
  getToolUseSummary?(input, result): string // 工具调用摘要
  backfillObservableInput?(input): void    // 回填可观察输入
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
| `description` | `z.string().optional()` | 命令用途描述（主动语态，简洁） |
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

**安全环境变量白名单**（~32 个）：Go/Rust/Node/Python/Locale/Terminal/Color 变量在权限匹配前可安全剥离。

**显式排除**：`PATH`、`LD_PRELOAD`、`LD_LIBRARY_PATH`、`DYLD_*`、`PYTHONPATH`、`NODE_PATH`、`NODE_OPTIONS`、`HOME`、`SHELL`、`BASH_ENV` 等。

**禁止作为规则前缀的 shell 名**：`sh`、`bash`、`zsh`、`fish`、`sudo`、`env`、`xargs`、`doas`、`pkexec` 等 ~21 个（`bash:*` 会自动批准任意代码执行）。

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

> **注**：源码中无独立 MultiEditTool。`MultiEdit` 仅是 `bridge/sessionRunner.ts:74` 中的 UI verb 映射，实际实现为 Edit 工具的 `replace_all: true` 参数（源码: `tools/FileEditTool/`）。

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

### 4.3.6 Agent 工具（源码: `tools/AgentTool/`，6,782 LOC）

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
2. **递归防护**：扫描消息中的 `<fork-boilerplate>` 标签或 `querySource === 'agent:builtin:fork'`
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

## 4.4 BashTool 安全管道详解（源码: `tools/BashTool/bashSecurity.ts`，2,593 LOC）

> BashTool 的安全验证是 Claude Code 工具系统中最复杂的子系统之一。本节按源码分析详解 23 层验证器的完整执行流程，供其他 Agent 开发者设计 shell 安全机制时参考。

### 4.4.1 验证器执行顺序

验证器分为三个阶段：预检门控 → 早期验证器（可短路 allow） → 主验证器（仅 ask/passthrough）。

#### 预检门控（Phase 0）

在验证器运行前执行，直接拒绝：

| # | 检查 | 说明 |
|---|------|------|
| 0 | **CONTROL_CHARACTERS** (ID 17) | 拒绝 `\x00-\x08`, `\x0B`, `\x0C`, `\x0E-\x1F`, `\x7F` 控制字符 |
| 0b | **shell-quote 引号漏洞** | 检测 `'\''` 模式，利用 shell-quote 库对单引号内反斜杠的错误处理 |

#### 早期验证器（可返回 allow，短路后续所有检查）

| # | 验证器 | ID | 短路条件 |
|---|--------|-----|----------|
| 1 | `validateEmpty` | — | 空白命令 → allow |
| 2 | `validateIncompleteCommands` | 1 | 以 `-`、tab、`&&`/`||`/`;`/`>>`/`<` 开头的命令 → ask |
| 3 | `validateSafeCommandSubstitution` | 8 | `$(cat <<'DELIM'...DELIM)` 安全 heredoc 模式 → allow |
| 4 | `validateGitCommit` | 12 | `git commit -m "简单消息"`（无反斜杠、无元字符）→ allow |

#### 主验证器（按顺序执行，仅可返回 ask/passthrough）

| # | 验证器 | ID | 防御目标 |
|---|--------|-----|----------|
| 5 | `validateJqCommand` | 2/3 | 阻止 `jq` 的 `system()` 调用和危险标志（`-f`, `--from-file`, `--slurpfile`, `-L`） |
| 6 | `validateObfuscatedFlags` | 4 | 捕获标志混淆：ANSI-C 引用 `$'...'`、locale 引用 `$"..."`、空引号前缀 `''-`、3+ 连续引号 |
| 7 | `validateShellMetacharacters` | 5 | 检测引号参数内的 `;`、`|`、`&`（如 `find -name "foo;bar"`） |
| 8 | `validateDangerousVariables` | 6 | 阻止重定向/管道上下文中的 `$VAR` |
| 9 | `validateCommentQuoteDesync` | 22 | `#` 注释内的引号导致引号追踪器失同步 |
| 10 | `validateQuotedNewline` | 23 | 引号字符串内换行且下一行以 `#` 开头（绕过 stripCommentLines） |
| 11 | `validateCarriageReturn` | 7 | 引号外的 `\r`（shell-quote/bash 分词差异） |
| 12 | `validateNewlines` | 7 | 非引号内容中的换行（隐藏的第二命令） |
| 13 | `validateIFSInjection` | 11 | 任何 `$IFS` 或 `${...IFS...}` 使用 |
| 14 | `validateProcEnvironAccess` | 13 | `/proc/*/environ` 路径访问 |
| 15 | `validateDangerousPatterns` | 8 | 反引号、进程替换 `<()`/`>()`、`$()`、`${}`、zsh glob 限定符 |
| 16 | `validateRedirections` | 9/10 | `<` 和 `>` 操作符 |
| 17 | `validateBackslashEscapedWhitespace` | 15 | 引号外的 `\ ` 和 `\<tab>` |
| 18 | `validateBackslashEscapedOperators` | 21 | 引号外的 `\;`、`\|`、`\&`、`\<`、`\>` |
| 19 | `validateUnicodeWhitespace` | 18 | 10 种 Unicode 空白字符（`\u00A0`、`\uFEFF` 等） |
| 20 | `validateMidWordHash` | 19 | 非空白后的 `#`（shell-quote vs bash 解析差异） |
| 21 | `validateBraceExpansion` | 16 | `{a,b}` 和 `{1..5}` 展开（逗号或 `..` 深度 0） |
| 22 | `validateZshDangerousCommands` | 20 | `zmodload`、`emulate`、`sysopen/read/write`、`zpty`、`mapfile`、`zf_rm` 等 |
| 23 | `validateMalformedTokenInjection` | 14 | 不平衡分隔符 + 命令分隔符组合 |

> **设计要点**：`validateNewlines` 和 `validateRedirections` 标记为 `nonMisparsingValidators`——它们的 `ask` 结果被延迟处理，避免在更严重的错误检测之前短路。

### 4.4.2 命令语义分类

BashTool 对命令进行语义分类，影响权限提示和结果显示：

| 分类 | 命令 | 用途 |
|------|------|------|
| **搜索** | `find`, `grep`, `rg`, `ag`, `ack`, `locate`, `which`, `whereis` | UI 标记为搜索操作 |
| **读取** | `cat`, `head`, `tail`, `less`, `more`, `wc`, `stat`, `file`, `strings`, `jq`, `awk`, `cut`, `sort`, `uniq`, `tr` | 只读操作 |
| **列表** | `ls`, `tree`, `du` | 目录查看 |
| **静默** | `mv`, `cp`, `rm`, `mkdir`, `rmdir`, `chmod`, `chown`, `touch`, `ln`, `cd`, `export`, `unset`, `wait` | 无输出的文件操作 |
| **中性** | `echo`, `printf`, `true`, `false`, `:` | 无副作用 |

### 4.4.3 退出码语义解释

`interpretCommandResult()` 对特定命令的退出码进行语义转换（源码: `tools/BashTool/commandSemantics.ts`）：

| 命令 | Exit 0 | Exit 1 | Exit 2+ |
|------|--------|--------|---------|
| `grep` / `rg` | 找到匹配 | **未找到匹配（非错误）** | 错误 |
| `diff` | 无差异 | **有差异（非错误）** | 错误 |
| `test` / `[` | 条件为真 | **条件为假（非错误）** | 错误 |
| `find` | 成功 | 部分成功（某些目录不可访问） | 错误 |

> **实现者注意**：对 grep/diff/test 的 exit 1 进行语义转换是关键 UX 决策——避免模型将「未找到匹配」误判为执行失败。

### 4.4.4 超时配置

| 常量 | 默认值 | 来源 |
|------|--------|------|
| `DEFAULT_TIMEOUT_MS` | 120,000 (2 分钟) | `BASH_DEFAULT_TIMEOUT_MS` 环境变量可覆盖 |
| `MAX_TIMEOUT_MS` | 600,000 (10 分钟) | `BASH_MAX_TIMEOUT_MS` 环境变量可覆盖 |
| 不变式 | `MAX >= DEFAULT` | `Math.max(maxEnv, defaultTimeout)` |

### 4.4.5 沙箱机制

沙箱基于 `@anthropic-ai/sandbox-runtime`（Linux 使用 `bubblewrap`/`bwrap`，macOS 使用沙箱 profile）：

```
沙箱文件系统隔离配置：
├── 允许写入: ['.', getClaudeTempDir()] + Edit 权限路径 + worktree 路径
├── 拒绝写入: .claude/settings.json, .claude/settings.local.json, bare git repo 文件
├── 拒绝读取: Read 权限拒绝路径
└── 网络隔离: 从 WebFetch 权限规则和 sandbox.network.* 设置提取域名白名单
```

### 4.4.6 环境变量安全

**安全变量**（~32 个，自动从命令前缀中剥离后再做权限匹配）：Go、Rust、Node、Python、pytest 相关、`ANTHROPIC_API_KEY`、locale、终端、颜色配置等。

**永不安全**（显式禁止）：`PATH`, `LD_PRELOAD`, `LD_LIBRARY_PATH`, `DYLD_*`, `PYTHONPATH`, `NODE_PATH`, `CLASSPATH`, `RUBYLIB`, `GOFLAGS`, `RUSTFLAGS`, `NODE_OPTIONS`, `HOME`, `TMPDIR`, `SHELL`, `BASH_ENV`。

### 4.4.7 后台进程管理

后台执行不是通过检测 `&` 实现的，而是通过显式参数：

1. **用户指定**：`run_in_background: true`
2. **超时自动后台**：命令在 `COMMON_BACKGROUND_COMMANDS` 列表中（`npm`, `node`, `python`, `cargo`, `make`, `docker`, `webpack`, `vite`, `jest`, `pytest` 等），超时时自动转为后台
3. **前台阻塞预算**：assistant 模式下前台执行超过 15 秒（`ASSISTANT_BLOCKING_BUDGET_MS`）自动后台化

输出上限：磁盘 5 GB（`MAX_TASK_OUTPUT_BYTES`），超限发送 SIGKILL。

---

## 4.5 查询主循环架构（源码: `query.ts` + `QueryEngine.ts` + `toolExecution.ts`）

> 本节描述 LLM 响应与工具执行之间的核心循环，其他 Agent 开发者可参考此架构设计自己的 agent loop。

### 4.5.1 三层架构

| 层 | 源码 | 职责 |
|----|------|------|
| **QueryEngine** | `QueryEngine.ts`（1,296 LOC） | 会话级编排：拥有 `mutableMessages`、usage 累积、`submitMessage()` async generator |
| **query()** | `query.ts`（1,730 LOC） | 核心 agent 循环：`while(true)` 的 `AsyncGenerator`，每轮产出 `StreamEvent` |
| **Tool 执行层** | `toolExecution.ts`（1,746 LOC） + `StreamingToolExecutor.ts`（366 LOC） | 单工具执行（权限检查 → 调用 → 结果）+ 流式并行执行 |

### 4.5.2 单次迭代流程

```
┌─────────────────────────────────────────────────────────────┐
│  while(true) 每次迭代                                       │
│                                                             │
│  1. 预处理: 工具结果预算 → snip compact → microcompact →     │
│     context collapse → autocompact                          │
│  2. Token 限制检查（超限且无恢复手段 → 终止）                 │
│  3. deps.callModel() [流式调用 Anthropic API]                │
│     │                                                       │
│     ├─ 每个流式 chunk:                                      │
│     │   ├─ assistant message with tool_use → 加入执行器      │
│     │   └─ StreamingToolExecutor 立即启动并发安全工具         │
│     │                                                       │
│  4. [流结束]                                                 │
│     │                                                       │
│     ├─ 无 tool_use:                                         │
│     │   ├─ Stop hooks                                       │
│     │   ├─ max_output_tokens 恢复（最多 3 次）               │
│     │   └─ return { reason: 'completed' }                   │
│     │                                                       │
│     └─ 有 tool_use:                                         │
│         ├─ 执行剩余工具（getRemainingResults / runTools）     │
│         ├─ 收集 attachments（记忆、排队命令、技能发现）      │
│         ├─ 检查 maxTurns / budget / abort                   │
│         └─ state = { messages: [...query, ...assistant,      │
│                      ...toolResults] } → continue           │
└─────────────────────────────────────────────────────────────┘
```

### 4.5.3 流式工具执行

当 `tengu_streaming_tool_execution2` feature gate 启用时，工具在 LLM 流式响应期间就开始执行：

- **并发安全工具**（`isConcurrencySafe=true`）可并行启动
- **非安全工具**串行执行（必须等前一个完成）
- Bash 错误通过 `siblingAbortController` 取消所有兄弟工具
- 流结束后通过 `getRemainingResults()` 排水未完成工具

### 4.5.4 ToolResult 类型

```typescript
type ToolResult<T> = {
  data: T                                           // 工具的强类型输出
  newMessages?: (UserMessage | AssistantMessage     // 向对话注入额外消息
    | AttachmentMessage | SystemMessage)[]
  contextModifier?: (ctx) => ToolUseContext          // 修改后续工具的执行上下文
  mcpMeta?: { _meta?, structuredContent? }           // MCP 协议元数据
}
```

### 4.5.5 Attachment 机制

Attachment 是 Claude Code 向对话注入**工具结果之外**的上下文的机制（源码: `utils/attachments.ts`，3,998 LOC），支持约 60 种类型：

| 类别 | Attachment 类型 |
|------|----------------|
| **文件** | `file`, `edited_text_file`, `edited_image_file` |
| **记忆** | `nested_memory`, `relevant_memories` |
| **技能** | `skill_discovery`, `skill_listing` |
| **任务** | `todo_reminder`, `task_reminder` |
| **模式** | `plan_mode`, `auto_mode` |
| **增量** | `deferred_tools_delta`, `mcp_instructions_delta` |
| **预算** | `token_usage`, `budget_usd`, `output_token_usage` |
| **其他** | `queued_command`, `diagnostics`, `date_change`, `hook_*` |

Attachment 通过 `createAttachmentMessage()` 包装为 `<system-reminder>` XML 标签，以用户消息形式注入对话。

### 4.5.6 终止条件

| 条件 | 信号 |
|------|------|
| 无 tool_use + stop hooks 通过 | `{ reason: 'completed' }` |
| maxTurns 超限 | `{ reason: 'max_turns' }` |
| 预算 USD 超限 | `error_max_budget_usd` |
| 用户中断 (Ctrl+C) | `{ reason: 'aborted_streaming' }` |
| prompt_too_long (413) | 上下文压缩 → 重试，不可恢复则终止 |
| max_output_tokens | 注入「继续思考」消息，最多重试 3 次 |

### 4.5.7 上下文管理策略（按优先级执行）

| 策略 | 说明 |
|------|------|
| **工具结果预算** | 持久化超大工具结果到磁盘，替换为 `<persisted-output>` 引用 |
| **Snip compact** | 移除超过阈值的旧消息，生成摘要 |
| **Microcompact** | 原地改写工具结果内容（缓存编辑） |
| **Context collapse** | REPL 历史的折叠视图 |
| **Autocompact** | token 数超过上下文窗口时完整摘要化 |
| **Reactive compact** | 413 错误触发，作为主动压缩的后备 |

---

## 4.6 权限系统完整流程（源码: `utils/permissions/`）

> 权限系统是工具执行的安全门卫。本节详解从 `hasPermissionsToUseTool()` 入口到最终决策的完整路径。

### 4.6.1 权限检查流程（Phase 1: 核心决策）

```
hasPermissionsToUseToolInner()
    │
    ├─ Step 1a: deny 规则匹配（整个工具级别）
    │   └─ 扫描所有 PERMISSION_RULE_SOURCES 的 alwaysDenyRules
    │
    ├─ Step 1b: ask 规则匹配（整个工具级别）
    │   └─ 扫描 alwaysAskRules
    │   └─ 例外: BashTool + 沙箱启用 + autoAllowBashIfSandboxed → 跳过 ask
    │
    ├─ Step 1c: tool.checkPermissions(parsedInput, context)
    │   └─ 每个工具自定义（BashTool: 解析命令 → 前缀规则 → 子命令规则 → 操作符检查）
    │
    ├─ Step 1d: 工具返回 deny → 立即拒绝
    ├─ Step 1e: 工具要求用户交互 → 强制弹出提示
    ├─ Step 1f: 内容级 ask 规则 → 强制弹出提示
    ├─ Step 1g: 安全检查（bypass-immune）→ 强制弹出提示
    │
    ├─ Step 2a: bypassPermissions 模式 → allow
    ├─ Step 2b: alwaysAllow 规则匹配 → allow
    │
    └─ Step 3: passthrough 转换为 ask
```

> **bypass-immune 步骤**（1d/1e/1f/1g）：即使在 bypassPermissions 模式下也必须执行。保护 `.git/`、`.claude/`、`.vscode/`、shell 配置文件、Windows 路径绕过、跨机器桥接消息。

### 4.6.2 PermissionMode 完整枚举

| 模式 | 图标 | 对外暴露 | 行为 |
|------|------|----------|------|
| `default` | `''` | ✓ | 未匹配 allow 规则的工具需用户确认 |
| `acceptEdits` | `⏵⏵` | ✓ | 工作目录内的文件编辑自动允许，其他需确认 |
| `plan` | `PAUSE_ICON` | ✓ | 只读 + 计划文件写入 |
| `bypassPermissions` | `⏵⏵` | ✓ | 允许所有工具（bypass-immune 步骤除外），需 `--dangerously-skip-permissions` |
| `dontAsk` | `⏵⏵` | ✓ | 将所有 ask 决策转为 deny |
| `auto` | `⏵⏵` | ✗ (Ant-only) | AI 分类器决定 allow/deny，危险权限规则被剥离 |

Shift+Tab 循环顺序：对外用户 `default → acceptEdits → plan → bypassPermissions`；Ant 用户 `default → bypassPermissions → auto`。

### 4.6.3 Auto 模式分类器管道

当结果为 `ask` 且模式为 `auto` 时，执行三层快速路径：

1. **acceptEdits 快速路径**：重新以 `acceptEdits` 模式运行 `tool.checkPermissions()`，如果自动允许则跳过分类器（排除 Agent 和 REPL 工具）
2. **安全工具白名单**：`SAFE_YOLO_ALLOWLISTED_TOOLS` 包含约 25 个工具（Read, Grep, Glob, LSP, ToolSearch, TodoWrite, Task*, PlanMode 等）
3. **AI 分类器**：`classifyYoloAction()` 使用两阶段 XML 分类：
   - Stage 1（快速）：追加 "Err on the side of blocking"，解析 `<block>yes/no</block>`
   - Stage 2（思考）：含 `<thinking>` 标签的深度分析
   - 分类器不可用时：取决于 `tengu_iron_gate_closed`（fail-closed = deny，fail-open = 弹出提示）
4. **拒绝上限**：连续拒绝 ≥3 次或总拒绝 ≥20 次 → 回退到用户提示

### 4.6.4 Circuit Breaker

自动模式的断路器：

- GrowthBook 门控 `tengu_auto_mode_config.enabled`：`enabled`/`disabled`/`opt-in`
- 触发后：停用分类器 → 恢复危险权限 → 切换到 `default` 模式
- `bypassPermissions` 独立断路器：`tengu_disable_bypass_permissions_mode` 触发时直接退出

### 4.6.5 权限规则格式与来源

**规则格式**：
```
ToolName                      # 工具级规则（如 "Bash"）
ToolName(content)             # 内容规则（如 "Bash(npm install)"）
ToolName(prefix:*)            # 前缀规则（如 "Bash(git commit:*)"）
```

**规则来源**（优先级递减）：

| 来源 | 说明 |
|------|------|
| CLI 参数 | `--allowed-tools "Bash(git commit:*),Read,Edit"` |
| 用户设置 | `~/.claude/settings.json` 的 `permissions.allow/deny/ask` |
| 项目设置 | `.claude/settings.json` |
| 本地设置 | `.claude/settings.local.json`（gitignored） |
| 企业策略 | managed/enterprise policy |
| 会话规则 | 用户交互中生成的规则 |

### 4.6.6 用户决策生成持久规则

用户点击「Yes, and don't ask again for [X]」时：

1. 创建 `PermissionUpdate`（如 `Bash(npm install:*)` 的 allow 规则）
2. `persistPermissionUpdates()` 写入对应 settings 文件的 `permissions.allow` 数组
3. 内存中的 `ToolPermissionContext` 实时更新
4. 规则去重：通过规范化字符串比较

---

## 4.7 延迟加载工具详解

### 4.7.1 WebFetch 工具（源码: `tools/WebFetchTool/`，1,131 LOC）

| 字段 | 类型 | 说明 |
|------|------|------|
| `url` | `z.string().url()` | 目标 URL |
| `prompt` | `z.string()` | 对获取内容的处理 prompt |

- **预批准域名**：自动允许，无需用户确认
- **跨域重定向**：不自动跟随，返回新 URL 让用户批准
- Markdown 且小于 `MAX_MARKDOWN_LENGTH` → 跳过 LLM 处理，直接返回原文
- `isConcurrencySafe: true`，`isReadOnly: true`

### 4.7.2 WebSearch 工具（源码: `tools/WebSearchTool/`，569 LOC）

| 字段 | 类型 | 说明 |
|------|------|------|
| `query` | `z.string().min(2)` | 搜索查询 |
| `allowed_domains` | `z.array(z.string()).optional()` | 域名白名单 |
| `blocked_domains` | `z.array(z.string()).optional()` | 域名黑名单 |

- 使用 Anthropic API 的 `web_search_20250305` 工具（每调用最多 8 次搜索）
- `isEnabled()` 取决于提供商：FirstParty/Foundry 始终启用；Vertex 仅 Claude 4.0+

### 4.7.3 NotebookEdit 工具（源码: `tools/NotebookEditTool/`，587 LOC）

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

### 4.7.4 Task 工具组（V2）

| 工具 | 输入 | 说明 |
|------|------|------|
| **TaskCreate** | `subject`, `description`, `activeForm?`, `metadata?` | 创建任务（支持 blocks/blockedBy 依赖） |
| **TaskGet** | `taskId` | 获取任务详情 |
| **TaskUpdate** | `taskId`, `status?`, `subject?`, `description?`, `addBlocks?`, `addBlockedBy?`, `owner?`, `metadata?` | 更新任务（`status: 'deleted'` 删除） |
| **TaskList** | — | 列出所有任务 |

- Feature gate：`isTodoV2Enabled()`
- **与 TodoWrite 互斥**：当 `isTodoV2Enabled()` 为 true（交互式 CLI 会话）时，TodoWrite 被禁用，TaskCreate/TaskGet/TaskUpdate/TaskList 启用。非交互模式（SDK）下相反。两者不可共存（源码: `tools.ts` + 各工具 `isEnabled()` 守卫）。
- **验证提醒**：主线程完成 3+ 任务后，自动建议生成验证代理
- 团队集成：teammate 标记 `in_progress` 时自动设置 owner；owner 变更通知

### 4.7.5 Cron 工具（源码: `tools/ScheduleCronTool/`）

| 字段 | 类型 | 说明 |
|------|------|------|
| `cron` | `z.string()` | 5 字段 cron 表达式（本地时间） |
| `prompt` | `z.string()` | 要执行的 prompt |
| `recurring` | `z.boolean()` | 默认 true；false = 一次性 |
| `durable` | `z.boolean()` | 默认 false；true = 持久化到 `.claude/scheduled_tasks.json` |

- 上限：50 个定时任务/会话
- Teammate 不能创建 durable cron（验证拒绝 error code 4）
- Feature gate：`isKairosCronEnabled()`

### 4.7.6 Worktree 工具

**EnterWorktree**：创建 Git worktree，`process.chdir()` 切换目录，清除缓存。

**ExitWorktree**：`action: 'keep' | 'remove'`。remove 时统计变更文件数和提交数，kill tmux session，`cleanupWorktree()`。

### 4.7.7 Brief 工具（源码: `tools/BriefTool/`，610 LOC）

Kairos 模式下的用户消息工具：

| 字段 | 类型 | 说明 |
|------|------|------|
| `message` | `z.string()` | Markdown 消息 |
| `attachments` | `z.array(z.string()).optional()` | 附件路径 |
| `status` | `z.enum(['normal','proactive'])` | proactive = 主动更新 |

双层 Feature gate：`isBriefEntitled()`（构建时 + 运行时 + GB）→ `isBriefEnabled()`（opt-in 来源：`--brief`、settings、`/brief`、env var）。

### 4.7.8 AskUserQuestion 工具（源码: `tools/AskUserQuestionTool/`，309 LOC）

| 字段 | 类型 | 约束 |
|------|------|------|
| `questions` | `z.array(questionSchema)` | 1-4 个问题 |
| `metadata` | `z.object({source}).optional()` | 分析来源 |

每个问题：`{ question, header(≤12字符), options(2-4个), multiSelect }`。始终 `behavior: 'ask'`。

### 4.7.9 SendMessage 工具（源码: `tools/SendMessageTool/`，997 LOC）

| 字段 | 类型 | 说明 |
|------|------|------|
| `to` | `z.string()` | Teammate 名 / `*`(广播) / `uds:<socket>` / `bridge:<session-id>` |
| `message` | `z.string() | StructuredMessage` | 消息内容 |
| `summary` | `z.string().optional()` | 5-10 词预览（纯文本消息必需） |

结构化消息类型：`shutdown_request`、`shutdown_response`、`plan_approval_response`。

跨会话消息（`bridge:` 前缀）：通过 Remote Control 的 `postInterClaudeMessage()` 传递，始终要求用户确认（跨机器 prompt 注入风险）。

### 4.7.10 Team 工具

**TeamCreate**：`team_name`, `description?`, `agent_type?`。创建 `TeamFile`，注册 lead 为首个成员。

**TeamDelete**：清理团队文件、任务列表、tmux session。

Feature gate：`isAgentSwarmsEnabled()`。

### 4.7.11 LSP 工具（源码: `tools/LSPTool/`，2,005 LOC）

9 种操作：`goToDefinition`、`findReferences`、`hover`、`documentSymbol`、`workspaceSymbol`、`goToImplementation`、`prepareCallHierarchy`、`incomingCalls`、`outgoingCalls`。

`isEnabled()` = `isLspConnected()`。最大文件：10 MB。

### 4.7.12 RemoteTrigger 工具

| 字段 | 类型 | 说明 |
|------|------|------|
| `action` | `z.enum(['list','get','create','update','run'])` | CRUD + 执行 |
| `trigger_id` | `z.string()` | 操作对象 ID |
| `body` | `z.record(z.string(), z.unknown())` | 请求体 |

Feature gate：`tengu_surreal_dali` + `isPolicyAllowed('allow_remote_sessions')`。OAuth 认证，API 路径 `/v1/code/triggers`。

### 4.7.13 Config 工具

| 字段 | 类型 | 说明 |
|------|------|------|
| `setting` | `z.string()` | 设置键 |
| `value` | `z.string() | z.boolean() | z.number()` | 省略 = 获取当前值 |

GET 自动允许；SET 需要用户确认。`remoteControlAtStartup` 特殊处理："default" 清除键值。

### 4.7.14 Plan 模式工具

**EnterPlanMode**：无参数。切换到 plan 权限模式（只读 + 计划文件写入）。分面试阶段（最小指令）和传统阶段（6 步探索/规划/设计）。

**ExitPlanMode**：`allowedPrompts?`（Bash prompt 规则）。Teammate 需 team lead 审批计划后才可退出。自动模式门控：circuit breaker 触发时回退到 default 模式。

### 4.7.15 Skill 工具（源码: `tools/SkillTool/`，1,477 LOC）

| 字段 | 类型 | 说明 |
|------|------|------|
| `skill` | `z.string()` | 技能名 |
| `args` | `z.string().optional()` | 参数 |

两种执行模式：
- **Inline**：注入消息到当前对话
- **Forked**：在隔离子代理中执行（`command.context === 'fork'`）

权限检查管道：deny 规则 → 远程 canonical 技能自动允许 → allow 规则 → 安全属性自动允许（`SAFE_SKILL_PROPERTIES` 白名单 ~30 个键）→ 默认 ask。

---

## 4.8 MCP 工具集成（源码: `tools/MCPTool/`）

### 4.8.1 动态注册

MCP 工具以 `mcp__serverName__toolName` 格式动态注册（注意**双下划线**）。每个 MCP 服务器启动时，其工具 schema 被解析为 `Tool` 实例。

### 4.8.2 MCPTool 基类

MCPTool 是模板/桩：`z.object({}).passthrough()` 接受任意输入，`z.string()` 输出。实际行为在 `mcpClient.ts` 中为每个工具单独创建。

关键属性：`isMcp: true`，`checkPermissions` 始终 `behavior: 'passthrough'`。

### 4.8.3 MCP 认证工具

**McpAuthTool**：处理 MCP 服务器的 OAuth 认证流程。

### 4.8.4 MCP 资源工具

**ReadMcpResourceTool** + **ListMcpResourcesTool**：读取和列举 MCP 服务器暴露的资源。

---

## 4.9 跨工具安全架构

### 4.9.1 权限系统

> 权限系统的完整描述见 4.6 节。以下为跨工具安全视角的摘要。

**PermissionMode 枚举**（完整 6 种见 4.6.2）：

| 模式 | 行为 |
|------|------|
| `default` | 每次操作需用户确认 |
| `acceptEdits` | 文件编辑自动允许，其他需确认 |
| `plan` | 只读 + 计划文件写入 |
| `auto` | 基于分类器的自动允许（circuit breaker 保护） |
| `bypassPermissions` | 跳过所有权限检查（需 `--dangerously-skip-permissions`） |
| `dontAsk` | 将 ask 转为 deny（静默拒绝） |

**权限规则来源**（完整 6 层优先级见 4.6.5）：

1. CLI 参数（`--allowed-tools`）
2. 用户设置（`~/.claude/settings.json`）
3. 项目设置（`.claude/settings.json`）
4. 本地设置（`.claude/settings.local.json`）
5. 企业策略
6. 会话规则（用户交互生成）

### 4.9.2 Read-Before-Write 保护

Edit 和 Write 工具共享 `readFileState`（LRU 缓存，Map<path, { content, timestamp, offset, limit }>）：

1. **写入前必须读取**：文件必须在本次会话中通过 Read 工具读取过
2. **mtime 校验**：写入时检查文件 mtime，与读取时记录对比
3. **同步临界区**：mtime 检查和写入之间不允许 async 操作（防并发编辑交错）
4. **Windows 回退**：mtime 不可靠时使用内容比较（防云同步/杀毒软件误报）

### 4.9.3 大输出持久化

所有工具共享的大输出处理模式：

1. 工具结果超过 `maxResultSizeChars` → 写入 `tool-results/` 目录
2. 返回 `<persisted-output>` 标签 + 预览片段
3. 超过 `MAX_PERSISTED_SIZE`（64 MB）截断
4. 路径格式：`tool-results/<tool-name>-<timestamp>.txt`

> **例外**：Read 工具设 `maxResultSizeChars: Infinity`（源码: `FileReadTool.ts:342`），因为其输出已通过行数/文件类型自行限制大小，再设上限会导致循环读取（Read → 持久化 → 需再 Read）。

### 4.9.4 文件历史追踪

Edit 和 Write 调用 `fileHistoryTrackEdit()` 进行幂等备份，支持撤销操作。

### 4.9.5 UNC 路径安全

Windows SMB 路径（`\\server\share`）在 Edit、Write、NotebookEdit、LSPTool 中被拦截，防止 NTLM 凭据泄露。

### 4.9.6 Team Memory 机密扫描

Edit、Write、TodoWrite 在内容中检测 Team Memory 机密（error code 0），阻止意外泄露。

---

## 4.10 工具完整清单

| # | 工具名 | LOC | 加载 | 只读 | 并发安全 | Feature Gate |
|---|--------|-----|------|------|----------|-------------|
| 1 | **Bash** | 12,411 | 核心 | ✗ | ✗ | — |
| 2 | **Edit** | 1,812 | 核心 | ✗ | ✗ | — |
| 3 | **Read** | 1,602 | 核心 | ✓ | ✓ | — |
| 4 | **Write** | 856 | 核心 | ✗ | ✗ | — |
| 5 | **Grep** | 795 | 核心 | ✓ | ✓ | — |
| 6 | **Glob** | 267 | 核心 | ✓ | ✓ | — |
| 7 | **Agent** | 6,782 | 核心 | ✗ | ✗ | — |
| 8 | **TodoWrite** | 300 | 核心 | ✗ | ✗ | `!isTodoV2Enabled` |
| 9 | **ToolSearch** | 593 | 核心 | ✓ | ✓ | — |
| 10 | **StructuredOutput** | 163 | 核心 | ✗ | ✗ | `isNonInteractiveSession`；仅非交互模式，每次响应末尾调用一次 |
| 11 | **PowerShell** | 8,959 | 条件 | ✗ | ✗ | Windows；独立安全验证管道（与 BashTool 同等级别） |
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

> **总计**：39 个显式工具 + MCP 动态工具（∞）。其中 TaskStop 含 KillShell 别名；Edit 工具同时处理单次编辑和 replace_all 批量编辑（无需独立 MultiEdit 工具）。
>
> **注**：`tools/` 目录实际有 40 个子目录，但 `WorkflowTool` 受 `feature('WORKFLOW_SCRIPTS')` 门控且源码未随当前版本发布，不计入 39；其余 39 个目录对应本文列出的 39 个工具 + 1 个 `shared/` 工具集。
>
> **交叉文档同步 TODO**：本 PR 仅更新本文档。`docs/comparison/features.md`（内置工具数 20+）、`docs/comparison/architecture-deep-dive.md`（工具分类）、`docs/tools/claude-code/01-overview.md` 中的相关数据将在后续 PR 中同步更新。

---

## 4.11 设计哲学与架构权衡

> 本节分析 Claude Code 工具系统的设计决策背后的思考逻辑。每个决策点对比两种常见方案，说明 Claude Code 的选择及其工程理由。信息来源为源码注释和代码结构推断（⚠️ 推断部分已标注）。

### 4.11.1 Fail-Closed 安全默认值：为什么 `buildTool()` 工厂是必需的

**设计选择**：`buildTool()` 工厂函数集中管理安全默认值，而非由各工具自行实现。

**源码依据**：`Tool.ts:753-767` 中 `TOOL_DEFAULTS` 显式标注注释：

> Defaults (fail-closed where it matters):
> - `isConcurrencySafe` -> `false` (**assume not safe**)
> - `isReadOnly` -> `false` (**assume writes**)

**对比分析**：

| 方案 | 优点 | 缺点 |
|------|------|------|
| **A: 集中工厂 + fail-closed**（Claude Code 选择） | 新增工具不会遗漏安全方法；`isConcurrencySafe`/`isReadOnly` 默认最保守 | 需维护 `TOOL_DEFAULTS` 与 `Tool` 类型同步 |
| **B: 各工具自行声明** | 灵活度高 | 新工具作者可能遗忘 `isReadOnly()`，导致工具被错误标记为"安全"并发执行 |
| **C: `Object.assign` 手动展开** | 无额外抽象层 | 无类型级保证；不同工具可能使用不同的 defaults 对象导致不一致 |

⚠️ 推断：Claude Code 选择方案 A 的关键动因是**工具数量多**（39 个显式 + MCP 动态），手动管理不可靠。`buildTool` 注释（`Tool.ts:778`）明确写道：

> The type semantics are proven by the 0-error typecheck across all 60+ tools.

### 4.11.2 延迟加载 + ToolSearch：Token 经济学

**设计选择**：~10 个核心工具始终加载，其余 28+ 个延迟加载，由 ToolSearch 按需发现。

**源码依据**：`utils/toolSearch.ts` 定义三种模式（`tst` / `tst-auto` / `standard`），`tst-auto` 的阈值为上下文窗口的 **10%**（`DEFAULT_AUTO_TOOL_SEARCH_PERCENTAGE = 10`）。

**对比分析**：

| 方案 | Token 开销 | 延迟 | 复杂度 |
|------|-----------|------|--------|
| **A: 延迟加载 + 搜索引擎**（Claude Code 选择） | ~10 工具 schema 始终在 prompt；MCP 工具仅列名称 | 首次使用需 ToolSearch 调用（~1 轮 API） | 高（需 ToolSearchTool + 评分算法 + 6 级权重） |
| **B: 全量加载** | 所有工具 schema 占用 prompt token（MCP 可能数十个工具） | 零延迟 | 低 |
| **C: 按场景预加载** | 中等 | 低 | 中（需维护场景→工具映射） |

⚠️ 推断：方案 A 的核心动机是** MCP 生态的不可预测性**。一个项目可能配置 3 个 MCP 服务器（提供 50+ 工具），全量加载会消耗大量上下文窗口。`tst-auto` 模式的 10% 阈值是一个经验平衡点。

ToolSearch 评分算法（源码: `ToolSearchTool.ts:155-260`）使用 6 级权重（+12/+10/+6/+5/+4/+3/+2），MCP 工具名匹配得分高于原生工具名（+12 vs +10），这反映了 MCP 工具名称包含服务器前缀（如 `mcp__github`），信号强度更高。

### 4.11.3 Fork vs Subagent：Prompt Cache 驱动的架构

**设计选择**：Agent 工具支持两种子代理模式——Fork（共享上下文）和 Subagent（独立上下文）。

**源码依据**：`utils/forkedAgent.ts` 的 JSDoc 显式说明设计动机：

> Parameters that must be identical between the fork and parent API requests to share the parent's prompt cache. The Anthropic API cache key is composed of: system prompt, tools, model, messages (prefix), and thinking config.

**对比分析**：

| 维度 | Fork（共享上下文） | Subagent（独立上下文） |
|------|-------------------|----------------------|
| **Prompt cache** | ✅ 共享父级缓存（API 请求前缀完全一致） | ❌ 独立请求，无缓存共享 |
| **上下文** | 克隆父级完整对话历史 | 空白对话开始 |
| **工具集** | 使用父级精确工具池（`useExactTools: true`） | 重新组装（可能不同权限模式） |
| **System prompt** | 直接传递已渲染字节（不重新生成） | 调用 agent 的 `getSystemPrompt()` |
| **权限** | `'bubble'` 模式（提示回传到父终端） | Agent 自定义或隔离 |
| **Token 开销** | 低（共享前缀 ≈ 免费重放） | 高（完整 system prompt + CLAUDE.md + gitStatus） |
| **隔离性** | 低（子代理可看到父级对话） | 高（完全隔离） |

⚠️ 推断：Fork 模式的所有设计细节——threaded rendered bytes（避免 GrowthBook 冷→热状态变化）、`useExactTools`（避免工具序列化差异）、继承 thinking config（避免缓存 key 变化）——都是为了实现**字节级一致的 API 请求前缀**。这不仅是优化，而是将 Anthropic prompt cache 机制作为架构约束来设计。

源码注释（`forkSubagent.ts`）写道：

> Reconstructing by re-calling getSystemPrompt() can diverge (GrowthBook cold→warm) and bust the prompt cache; threading the rendered bytes is byte-exact.

递归防护采用**双层守卫**：`querySource` 标记（存活于 autocompact）+ `<fork-boilerplate>` 标签扫描（存活于消息历史），确保即使 autocompact 重写消息也不会丢失防护。

### 4.11.4 三阶段权限管道：为什么验证和权限必须分离

**设计选择**：`hasPermissionsToUseTool` 分为 10 步，核心分为三阶段：`validate`（步骤 1a-1g，不可旁路）→ `check`（步骤 2a-2b，可旁路）→ `call`。

**源码依据**：步骤 1a-1g 的注释（`permissions.ts`）：

> Safety checks (.git/, .claude/, .vscode/, shell configs) are bypass-immune — they must prompt even in bypassPermissions mode.

**对比分析**：

| 方案 | 安全性 | 灵活性 | 复杂度 |
|------|--------|--------|--------|
| **A: 统一管道** | 低（bypass 模式可能跳过关键安全检查） | 高 | 低 |
| **B: 分离管道（Claude Code 选择）** | 高（bypass-immune 检查始终执行） | 中 | 高（需维护两个独立的 hook 路径） |

Claude Code 选择方案 B 的关键原因是 `bypassPermissions` 模式的存在。如果所有检查在同一个管道中执行，`--dangerously-skip-permissions` 会跳过所有安全检查，包括对 `.git/` 目录的保护。分离管道确保**即使 bypass 模式也无法绕过核心安全规则**。

`checkRuleBasedPermissions` 函数（用于 PreToolUse hooks）只复制步骤 1a-1g，不走步骤 2a-2b，进一步说明这种分离是有意为之的。

### 4.11.5 Auto 模式三层分类器：延迟 vs 安全的平衡

**设计选择**：Auto 模式（`--dangerously-skip-permissions`）使用 3 层级联决策：acceptEdits 快速路径 → 安全工具白名单 → AI 分类器。

**源码依据**：

- **Layer 1** 注释（`permissions.ts`）：> This avoids expensive classifier API calls for safe operations like file edits in the working directory.

- **Layer 2** 注释（`classifierDecision.ts`）：> Does NOT include write/edit tools — those are handled by the acceptEdits fast path.

- **Layer 3** 防护：只发送 `tool_use` 块给分类器，不发送 assistant 文本——> assistant text is model-authored and could be crafted to influence the classifier's decision.

**对比分析**：

| 方案 | 延迟/次 | 安全覆盖 | Token 开销/次 |
|------|---------|----------|--------------|
| **A: 全量 AI 分类** | ~500ms | 高 | ~200 tokens |
| **B: 静态白名单** | <1ms | 中（无法判断语义安全） | 0 |
| **C: 三层级联**（Claude Code 选择） | ~50ms（平均） | 高（AI 分类器兜底） | ~50 tokens（平均） |

⚠️ 推断：三层级联是一个**延迟优化**——大多数文件编辑操作被 Layer 1 拦截（acceptEdits 判断是同步的），只读操作被 Layer 2 拦截（白名单匹配），只有真正不确定的操作才进入 Layer 3 的 AI 分类器。

**Circuit Breaker**（3 次连续拒绝或 20 次总拒绝 → 回退到交互模式）是额外的安全网。对 headless agent，超限直接抛出 `AbortError`，防止自动模式陷入"拒绝→重试"循环。

### 4.11.6 Bash 23 层验证器：防御 Shell 解析差异

**设计选择**：Bash 安全管道使用 23 层验证器，而非白名单或沙箱唯一防御。

**源码依据**：每个验证器都防御一种特定的攻击模式，核心设计原则来自 `bashSecurity.ts` 的注释：

> This is an EARLY-ALLOW path: returning `true` causes bashCommandIsSafe to return `passthrough`, bypassing ALL subsequent validators. Given this authority, the check must be PROVABLY safe, not "probably safe".

验证器 #13（回车符注入）注释解释了根本原因：

> Parser differential: shell-quote's BAREWORD regex uses `[^\s...]` — JS `\s` INCLUDES `\r`, so shell-quote treats CR as a token boundary. bash's default IFS = `$' \t\n'` — CR is NOT in IFS. bash sees `TZ=UTC\recho` as ONE word.

**对比分析**：

| 方案 | 防御范围 | 误报率 | 维护成本 |
|------|----------|--------|----------|
| **A: 命令白名单** | 窄（只能允许已知安全命令） | 高（任何新命令都需要审查） | 低 |
| **B: 沙箱唯一防御** | 宽（内核级隔离） | 低 | 中（沙箱逃逸风险） |
| **C: 多层验证 + 沙箱**（Claude Code 选择） | 最广（覆盖解析差异 + 沙箱兜底） | 中 | 高（23 层验证器 + 4 个沙箱后端） |

⚠️ 推断：Claude Code 选择方案 C 的根本原因是 **JavaScript `shell-quote` 库与 bash/zsh 解析器之间的语义差异**。这不是已知攻击模式的防御问题，而是两个解析器对同一字符串产生不同分词结果的问题。白名单无法防御"在 JS 看来安全但 bash 看来不同"的命令。

验证器 #4（混淆标志）的注释（~300 行代码）记录了最复杂的攻击面：

> In bash, `"""-f"` = empty string + string `"-f"` = `-f`. This bypass works for ANY dangerous-flag check with a matching prefix permission.

防御原则（`bashSecurity.ts`）：> Defense in depth: Block PowerShell comment syntax even though we don't execute in PowerShell. Added as protection against future changes that might introduce PowerShell execution.

### 4.11.7 mtime 临界区：为什么 TOCTOU 防护必须是同步的

**设计选择**：FileEditTool 的"读取→检查→写入"必须在同步临界区内完成，不允许 async yield。

**源码依据**：`FileEditTool.ts` 的注释：

> Please avoid async operations between here and writing to disk to preserve atomicity

**对比分析**：

| 方案 | 并发安全 | 性能 | 实现复杂度 |
|------|----------|------|-----------|
| **A: 文件锁** | 安全 | 阻塞其他进程 | 高（需跨平台锁机制） |
| **B: 乐观并发 + 异步 mtime 检查** | 不安全（TOCTOU 窗口） | 高 | 低 |
| **C: 同步临界区 + mtime**（Claude Code 选择） | 安全（无 yield 窗口） | 中（阻塞 Node 事件循环 ~ms 级） | 中 |

TOCTOU（Time-of-Check-Time-of-Use）漏洞的根本原因：如果 `readFile` 和 `writeFile` 之间有 async yield，另一个工具调用（或并发 agent）可能在 yield 期间修改文件，导致写入基于过期内容。

Claude Code 选择方案 C 的理由（⚠️ 推断）：文件锁（方案 A）在跨平台（Windows/macOS/Linux）和跨进程（agent 子进程）场景下实现复杂。同步临界区虽然阻塞事件循环，但文件编辑操作本身是 CPU-bound 的字符串匹配 + 文件写入，耗时在 ms 级别，对用户体验影响可忽略。

Windows 特殊处理：由于云同步和杀毒软件会改变文件 mtime 但不改变内容，对完整读取的文件使用**内容比较**作为二级检查，避免误报。

---

## 4.12 实现者 Checklist

> 其他 Code Agent 开发者设计工具系统时的关键决策参考。

| # | 设计决策 | Claude Code 的选择 | 实现考量 |
|---|----------|-------------------|----------|
| **1** | **工具注册方式？** | `buildTool()` 工厂 + 安全默认值（fail-closed） | 工厂模式确保新增工具不会遗漏安全方法 |
| **2** | **延迟加载策略？** | `shouldDefer` 标记 + `ToolSearch` 搜索引擎 | 核心 ~10 个工具始终加载，其余按需发现，减少 prompt token 开销 |
| **3** | **权限检查放在哪？** | 三阶段：`validateInput` → `checkPermissions` → `call()` | 验证和权限解耦；验证可短路返回错误码（telemetry 用） |
| **4** | **如何防 shell 注入？** | 23 层验证器管道（bashSecurity.ts） | 核心：防御 shell-quote/bash 解析差异，不只是已知攻击模式 |
| **5** | **如何防并发编辑冲突？** | readFileState LRU 缓存 + mtime 临界区 | mtime 检查和写入之间不允许 async（同步临界区） |
| **6** | **大工具输出如何处理？** | `maxResultSizeChars` 阈值 → 磁盘溢出 + 预览片段 | 统一的持久化模式，64 MB 截断上限 |
| **7** | **子代理上下文隔离？** | Fork 继承完整上下文（通常更有利于 prompt cache 命中）；Subagent 独立上下文 | Fork 的共享前缀设计减少了因 Agent 列表变动导致的 cache 失效 |
| **8** | **Agent 工具如何选模型？** | `getAgentModel()` 解析：agentDef.model → mainLoopModel → paramOverride | 读取/探索类代理可用更便宜模型（Haiku） |
| **9** | **MCP 工具如何安全？** | `mcp__` 命名空间 + 每工具独立 schema + passthrough 权限 | MCP 工具的权限由 MCP 服务器自行定义 |
| **10** | **工具 prompt 如何管理 token？** | 动态组装：按需注入沙箱指令、Agent 列表（attachment 优化） | Agent 列表用 attachment 避免因 Agent 列表变动导致的 cache 失效 |

---

> **数据来源**：本文全部技术细节来自源码分析（`Tool.ts` + `tools/` 目录 ~163 文件、~50,000 行 TypeScript），经 [EVIDENCE.md](./EVIDENCE.md) 交叉验证。
