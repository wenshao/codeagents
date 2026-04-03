# Shell 安全模型 Deep-Dive

> AI Agent 执行 Shell 命令时，如何防止注入攻击、越权操作和恶意代码执行？本文基于 Claude Code（v2.1.89 反编译）和 Qwen Code（v0.15.0 开源）的源码分析，对比两者在命令验证、AST 分析和权限决策方面的安全哲学差异。

---

## 1. 安全哲学对比

| 维度 | Claude Code | Qwen Code |
|------|------------|-----------|
| **核心策略** | 多重检测器 + 模式匹配 + AST 辅助 | AST-first 读写分类 |
| **检查数量** | 20+ 项枚举检查 | 1 项核心判定（read-only?） |
| **决策模型** | 3 态（allow / ask / deny） | 2 态（allow / ask） |
| **失败方向** | fail-closed（解析失败 → ask） | fail-closed（AST 失败 → ask） |
| **验证位置** | 命令执行前（内联） | 工具权限评估时 |
| **引用分析** | 3 种引用提取变体 | AST 原生（无需引用提取） |
| **子命令图谱** | 最小化（git/find/sed/awk） | 全面（10+ 工具，52 个 git 子命令） |

---

## 2. Claude Code：多层检测器管线

### 2.1 验证管线架构

验证分三个阶段执行（源码: `bashSecurity.ts#L2518-L2586`）：

```
命令输入
  ↓
阶段 1: Early Validators（4 个，可 early-return 'allow'）
  ├── validateEmpty           → 空命令 allow
  ├── validateIncompleteCommands → 不完整命令检测
  ├── validateSafeCommandSubstitution → 安全 heredoc allow
  └── validateGitCommit       → 安全 git commit allow
  ↓
阶段 2: Main Validators（19 个，顺序执行）
  ├── validateJqCommand       → jq 注入
  ├── validateObfuscatedFlags → Unicode/编码混淆
  ├── validateShellMetacharacters → 危险元字符
  ├── validateDangerousVariables → 变量重定向攻击
  ├── validateCommentQuoteDesync → 注释/引号不同步
  ├── validateQuotedNewline   → 引号内换行
  ├── validateCarriageReturn  → CR 注入
  ├── validateNewlines        → 命令换行
  ├── validateIFSInjection    → IFS 环境变量操控
  ├── validateProcEnvironAccess → /proc/environ 读取
  ├── validateDangerousPatterns → 命令替换 + heredoc + 反引号
  ├── validateRedirections    → 写重定向（> >>）
  ├── validateBackslashEscapedWhitespace → 转义空白
  ├── validateBackslashEscapedOperators → 转义运算符
  ├── validateUnicodeWhitespace → Unicode 空白字符
  ├── validateMidWordHash     → 词中 # 号
  ├── validateBraceExpansion  → 花括号展开
  ├── validateZshDangerousCommands → 18 个 Zsh 命令
  └── validateMalformedTokenInjection → 畸形 token
  ↓
阶段 3: Deferred Non-Misparsing Validators（2 个）
  ├── validateNewlines (non-misparsing)
  └── validateRedirections (non-misparsing)
  ↓
结果: { behavior: 'allow' | 'ask', checkId, isBashSecurityCheckForMisparsing }
```

> 源码: `tools/BashTool/bashSecurity.ts`（2,592 行）

### 2.2 引用提取系统

Claude Code 在正则分析前先提取三种引用变体（源码: `bashSecurity.ts#L119-L174`）：

| 变体 | 说明 | 用途 |
|------|------|------|
| `withDoubleQuotes` | 移除 `'...'` 保留 `"..."` 内容 | Shell 变量跟踪 |
| `fullyUnquoted` | 移除所有引号内容 | 大多数安全检查 |
| `unquotedKeepQuoteChars` | 引号内容替换为引号标记（`''`/`""`） | 词中 # 检测（需要引号邻接信息） |

**引用状态机**：逐字符扫描，跟踪单引号/双引号状态，处理反斜杠转义。单引号内反斜杠为字面量（Bash 语义正确）。

### 2.3 Tree-Sitter AST 辅助

```typescript
// 源码: utils/bash/treeSitterAnalysis.ts（506 行）
type TreeSitterAnalysis = {
  quoteContext: QuoteContext              // AST 级引用分析
  compoundStructure: CompoundStructure    // &&, ||, ;, pipeline 检测
  hasActualOperatorNodes: boolean         // 区分 \; (参数) 和 ; (运算符)
  dangerousPatterns: DangerousPatterns    // $(), 反引号, ${}, heredoc, 注释
}
```

**关键价值**：消除 `find -exec \;` 的误报。Tree-sitter 将 `\;` 解析为 word 节点（参数），而非 `;` 运算符。正则无法区分这两者。

### 2.4 Heredoc 安全判定

安全 Heredoc 模式（源码: `bashSecurity.ts#L317-L513`）：

```bash
# 允许的模式（单引号/转义定界符 = 无展开）
$(cat <<'EOF'
文件内容（字面量，无变量展开）
EOF
)

# 拒绝的模式（无引号定界符 = 有展开）
$(cat <<EOF
$VARIABLE  ← 危险：变量展开
EOF
)
```

验证要求：
- 定界符必须单引号或转义（`<<'EOF'` 或 `<<\EOF`）
- 闭合定界符必须独占一行
- 第一个匹配行即闭合（防止隐藏命令）
- 定界符前必须有非空白（确认在参数位置）
- 闭合后的剩余文本必须通过所有 validator

### 2.5 Zsh 特殊防护

18 个 Zsh 特定危险命令（源码: `bashSecurity.ts#L45-L74`）：

```
zmodload   → 模块加载入口（通往 mapfile/sysopen/ztcp）
emulate    → -c 标志是 eval 等价物
sysopen, sysread, syswrite, sysseek → zsh/system 文件 I/O
zpty       → 伪终端命令执行
ztcp       → TCP 网络连接
zsocket    → Unix/TCP socket
mapfile    → 不可见文件 I/O
zf_rm, zf_mv, zf_ln, zf_chmod, zf_chown, zf_mkdir, zf_rmdir, zf_chgrp
           → zsh/files 内建命令（绕过 binary 检查）
```

### 2.6 检查结果处理

```
behavior: 'allow' → 直接执行
behavior: 'ask' + isBashSecurityCheckForMisparsing: true → 严格阻断
behavior: 'ask' + isBashSecurityCheckForMisparsing: false → 标准权限对话框
```

---

## 3. Qwen Code：AST-First 读写分类

### 3.1 核心决策逻辑

```typescript
// 源码: qwen-code/packages/core/src/tools/shell.ts#L97-L111
override async getDefaultPermission(): Promise<PermissionDecision> {
  const command = stripShellWrapper(this.params.command)
  try {
    const isReadOnly = await isShellCommandReadOnlyAST(command)
    if (isReadOnly) return 'allow'     // 只读 → 自动允许
  } catch (e) {
    debugLogger.warn('AST read-only check failed, falling back to ask:', e)
  }
  return 'ask'                          // 非只读或 AST 失败 → 询问
}
```

**设计哲学**：不枚举危险模式，而是判断"是否只读"。只读 = 安全，非只读 = 询问。

### 3.2 AST 解析器

```typescript
// 源码: qwen-code/packages/core/src/utils/shellAstParser.ts（1,248 行）
// 使用 web-tree-sitter + tree-sitter-bash.wasm
await Parser.init({ locateFile: () => resolveWasmPath('tree-sitter.wasm') })
parserInstance.setLanguage(await Parser.Language.load(
  resolveWasmPath('tree-sitter-bash.wasm')
))
```

**WASM 路径解析**（源码: `shellAstParser.ts#L590-L668`）：处理多种部署场景（源码/转译/打包），探测多个候选目录。

**容错**：WASM 初始化失败时回退到 regex checker（`shellReadOnlyChecker.ts`，364 行）。

### 3.3 只读命令白名单（41 个）

```typescript
// 源码: shellAstParser.ts#L41-L76
// 只读根命令：
awk, basename, cat, cd, column, cut, df, dirname, du, echo, env, find, git,
grep, head, less, ls, more, printenv, printf, ps, pwd, rg, ripgrep, sed,
sort, stat, tail, tree, uniq, wc, which, where, whoami
```

### 3.4 子命令级分析（深度图谱）

| 工具 | 只读子命令 | 阻止的操作 |
|------|-----------|-----------|
| **git**（52 个子命令映射） | blame, branch, cat-file, diff, grep, log, ls-files, remote, rev-parse, show, status, describe | `remote add/remove/rename`, `branch -d/-D/--delete` |
| **find** | 默认只读 | `-delete`, `-exec`, `-execdir`, `-ok`, `-okdir`, `-fprint*` |
| **sed** | 默认只读 | `-i`, `--in-place`, `e` 命令（execute）, `w` 命令（write） |
| **awk** | 默认只读 | `system()`, 文件写入, 管道输出, `getline`, `close()` |
| **npm/yarn/pnpm** | `list`, `outdated`, `view`, `info` | `install`, `publish`, `run` |
| **docker** | `ps`, `images`, `inspect` | `run`, `exec`, `rm`, `stop` |
| **kubectl** | `get`, `describe`, `logs` | `apply`, `delete`, `edit` |

> 源码: `shellAstParser.ts#L161-L531`（完整子命令映射，10+ 工具）

### 3.5 AST 节点级分析

递归遍历 AST 节点（源码: `shellAstParser.ts#L914-L991`）：

| AST 节点类型 | 判定 |
|-------------|------|
| `command` | 检查根命令 + 命令替换 |
| `pipeline` | 所有命令都只读 → 只读 |
| `list` (&&, &#124;&#124;) | 所有命令都只读 → 只读 |
| `redirected_statement` | 阻止写重定向（>, >>, &>, &>>, >&#124;） |
| `subshell` | 所有内部命令都只读 → 只读 |
| `variable_assignment` | 纯赋值 → 安全 |
| `negated_command` | 分析内部命令 |
| `if` / `while` / `for` / `case` | **保守拒绝**（控制流不视为只读） |
| `function_definition` | **拒绝** |
| `declaration_command` | **拒绝**（可修改环境） |

### 3.6 权限规则提取

用户批准命令后，Qwen Code 提取**最小范围**的权限规则（源码: `shellAstParser.ts#L1050-L1202`）：

```
extractCommandRules('git clone https://github.com/foo/bar.git')
  → ['git clone *']          // 通配子命令参数

extractCommandRules('npm outdated')
  → ['npm outdated']          // 无参数不加通配符

extractCommandRules('git clone foo && npm install')
  → ['git clone *', 'npm install']  // 复合命令分拆为多条规则
```

### 3.7 PTY 执行模型

Qwen Code 使用 PTY（伪终端）执行命令（源码: `shellExecutionService.ts`，1,032 行）：

```typescript
// 源码: shellExecutionService.ts#L596-L609
const ptyProcess = ptyInfo.module.spawn(executable, args, {
  name: 'xterm',
  cols: 80, rows: 30,
  env: { TERM: 'xterm-256color', PAGER: 'cat', GIT_PAGER: 'cat', QWEN_CODE: '1' },
  handleFlowControl: true,
})
```

| 维度 | 详情 |
|------|------|
| 渲染节流 | 100ms 间隔 |
| 二进制检测 | 前 4096 字节嗅探 |
| 信号处理 | SIGTERM → 200ms → SIGKILL（POSIX）/ `taskkill /f /t`（Windows） |
| 回退 | PTY 不可用时降级为 `child_process.spawn` |

---

## 4. 逐维度对比

### 4.1 检测方法

| 维度 | Claude Code | Qwen Code |
|------|------------|-----------|
| 主要方法 | 正则模式匹配 + AST 辅助 | AST-first 读写分类 |
| 检查器数量 | 25+（Early + Main + Deferred） | 1（`isShellCommandReadOnlyAST`） |
| AST 角色 | 辅助（消除误报） | 核心（主决策路径） |
| 回退 | 无（双路并行） | regex checker（WASM 失败时） |
| 误报处理 | Tree-sitter 消除 `find -exec \;` 等误报 | AST 原生解析，无此问题 |

### 4.2 安全覆盖

| 攻击类型 | Claude Code | Qwen Code |
|----------|------------|-----------|
| 命令替换（$()、${}） | ✅ 12 种模式检测 | ✅ AST 检测 |
| IFS 注入 | ✅ 专项检查 | ❌ 不检测（非只读判定范畴） |
| Unicode 空白 | ✅ 专项检查 | ❌ 不检测 |
| 控制字符 | ✅ 专项检查 | ❌ 不检测 |
| Zsh 特定命令 | ✅ 18 个命令阻止 | ❌ 不检测 |
| 花括号展开 | ✅ 专项检查 | ❌ 不检测 |
| 混淆标志 | ✅ 专项检查 | ❌ 不检测 |
| 写重定向 | ✅ 专项检查 | ✅ AST 检测 |
| 管道/复合命令 | ✅ 元字符检查 | ✅ AST 递归分析 |
| git 危险操作 | ✅ 最小检查 | ✅ 52 个子命令映射 |

### 4.3 权限决策

| 维度 | Claude Code | Qwen Code |
|------|------------|-----------|
| 决策输出 | allow / ask / deny(via misparsing flag) | allow / ask |
| 权限持久化 | 多层规则来源（8 级） | 权限规则提取（最小范围通配） |
| 学习机制 | 用户可实时更新 session/project/user 规则 | 用户批准后提取规则建议 |
| 子命令粒度 | 基础（git/find/sed/awk） | 全面（10+ 工具，52+ git 子命令） |

### 4.4 执行模型

| 维度 | Claude Code | Qwen Code |
|------|------------|-----------|
| 执行方式 | `child_process.spawn` + 可选 sandbox | PTY（node-pty）+ xterm 渲染 |
| 输出捕获 | stdout/stderr 分离 | headless terminal 缓冲区重放 |
| 超时 | 120s 默认（可配置） | 120s 默认（`DEFAULT_FOREGROUND_TIMEOUT_MS`） |
| 沙箱 | 可选（`shouldUseSandbox()`） | 无独立沙箱 |
| ANSI 处理 | strip-ansi 后处理 | xterm Terminal 原生解析 |

---

## 5. 安全哲学分析

### Claude Code：枚举已知威胁

**优势**：
- 覆盖面广——每种已知攻击类型有专项检测
- IFS 注入、Unicode 空白、Zsh 命令等边缘攻击均有防护
- Tree-sitter 辅助消除正则误报

**风险**：
- 正则模式可能遗漏新型攻击模式
- 25+ 检查器的维护成本高
- 引用提取状态机的边缘 case 复杂

### Qwen Code：分类已知安全

**优势**：
- AST 分析精确——不存在正则误报
- 代码简洁——核心判定仅 1 个函数
- 子命令图谱全面——git 52 个子命令逐一分类

**风险**：
- 不检测 IFS 注入、Unicode 空白等非"读写分类"维度的攻击
- 控制流（`if`/`while`/`for`）保守拒绝——可能误拒安全的循环命令
- 只读白名单需持续维护——新工具（如 `jq`）需手动添加

### 对比总结

```
Claude Code: "这些模式是危险的" → 枚举危险 → 未匹配则允许
Qwen Code:   "这些模式是安全的" → 枚举安全 → 未匹配则询问
```

两者都是 fail-closed（不确定时拒绝/询问），但枚举方向相反。

---

## 6. 关键源码文件

### Claude Code

| 文件 | 行数 | 职责 |
|------|------|------|
| `tools/BashTool/bashSecurity.ts` | 2,592 | 多层验证管线（25+ 检查器） |
| `utils/bash/treeSitterAnalysis.ts` | 506 | Tree-sitter AST 辅助分析 |
| `utils/bash/heredoc.ts` | — | Heredoc 提取与验证 |
| `utils/bash/shellQuote.ts` | — | Shell 引用解析 |
| `tools/BashTool/shouldUseSandbox.ts` | 154 | 沙箱决策逻辑 |

### Qwen Code

| 文件 | 行数 | 职责 |
|------|------|------|
| `packages/core/src/utils/shellAstParser.ts` | 1,248 | AST 解析 + 只读判定 + 子命令映射 + 规则提取 |
| `packages/core/src/utils/shellReadOnlyChecker.ts` | 364 | 正则回退（WASM 失败时） |
| `packages/core/src/tools/shell.ts` | 706 | Shell 工具入口 + 权限决策 |
| `packages/core/src/services/shellExecutionService.ts` | 1,032 | PTY 执行 + 输出捕获 |
| `packages/core/src/permissions/shell-semantics.ts` | 1,686 | 语义分析（命令 → 虚拟文件/网络操作） |

---

## 7. 设计启示

1. **AST-first 更精确但覆盖面有限**：Qwen Code 的 AST 分析消除了正则误报，但不覆盖 IFS/Unicode/Zsh 等维度——理想方案是 AST 为主 + 专项检查为补充
2. **子命令映射是高杠杆投入**：Qwen Code 的 52 个 git 子命令映射让用户几乎无需为 git 操作确认权限——这是 Claude Code 可借鉴的
3. **权限规则提取降低审批疲劳**：Qwen Code 的 `extractCommandRules()` 自动建议最小范围规则（如 `git clone *`），而非让用户手动配置
4. **枚举方向决定维护成本**：枚举"安全"（Qwen Code）更易维护（新工具默认拒绝），枚举"危险"（Claude Code）覆盖面更广但需持续更新

> **免责声明**: 以上分析基于 2026 年 Q1 源码（Claude Code v2.1.89、Qwen Code v0.15.0），后续版本可能已变更。
