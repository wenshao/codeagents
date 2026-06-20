# 7. 权限系统——开发者参考

> OpenCode 的权限系统有三个特色设计：命令前缀/参数级权限判断（`arity.ts` token 解析；tree-sitter AST 仍是源码 TODO）、Doom Loop 保护（重复循环自动中断）、文件时间锁（检测编辑期间外部修改）。
>
> **Qwen Code 对标**：Qwen Code 有 AST 只读检测和 `permission-helpers.ts` 多层评估。OpenCode 的 Doom Loop 保护（~30 行代码，高 ROI）和 Semaphore 文件锁是主要参考。

## 一、为什么权限系统需要这些机制

### 问题定义

| 场景 | 无该机制的后果 |
|------|--------------|
| Agent 执行 `git push --force` | 用户拒绝 → Agent 换个参数再试 → 用户再拒绝 → 无限循环 |
| Agent 执行 `rm -rf node_modules && npm install` | 只检查第一个命令 `rm`（危险），忽略上下文 |
| Agent 写入 `config.json`，用户同时在编辑器修改同一文件 | 互相覆盖，丢失修改 |

### 竞品权限对比

| Agent | 命令分析 | 循环保护 | 文件冲突检测 |
|-------|---------|---------|-------------|
| **OpenCode** | token/arity 解析（命令前缀级；tree-sitter 为 TODO） | ✓ Doom Loop（3 步重复循环触发） | ✓ 文件时间锁 |
| **Claude Code** | 23 项安全检查 + 正则 | — | — |
| **Gemini CLI** | commandSafety.ts 黑名单 | — | — |
| **Qwen Code** | AST 只读检测 | — | — |

## 二、权限评估引擎

源码: `packages/opencode/src/permission/index.ts`

### 评估流程

```
工具请求权限
  │
  ├─ Permission.evaluate(permission, pattern, ...rulesets)
  │     ├─ Wildcard 匹配（~/→home, $HOME 展开）
  │     ├─ 多规则集合并（最后匹配的规则生效 per 规则集）
  │     └─ 跨规则集合并（deny > ask > allow）
  │
  ├─ 匹配结果
  │     ├─ allow → 直接执行
  │     ├─ deny → 抛出 DeniedError
  │     └─ ask → 发布 Permission.Event.Asked → 等待用户回复
  │
  └─ 用户回复
        ├─ "once" → 本次允许
        ├─ "always" → 保存到 approved 规则集 + 自动通过相同 pattern
        └─ "reject" → 抛出 RejectedError 或 CorrectedError（带反馈）
```

### 三种拒绝类型

| 类型 | 含义 | Agent 行为 |
|------|------|-----------|
| `DeniedError` | 规则显式禁止 | 不重试 |
| `RejectedError` | 用户拒绝（无反馈） | 可能换方式重试 |
| `CorrectedError` | 用户拒绝 + 提供反馈 | 根据反馈调整 |

## 三、Doom Loop 保护

**问题**：Agent 陷入重复循环（反复调用相同工具，或反复被拒后换措辞再试），无限循环浪费 token。

**解决方案**：检测到连续重复的步骤后，触发 `doom_loop` 权限（默认 `ask`），交由用户决定是否继续，从而打断循环。

源码: `packages/opencode/src/session/processor.ts`（`DOOM_LOOP_THRESHOLD = 3`）

```
监控最近 N 条消息 part（N = DOOM_LOOP_THRESHOLD = 3）
  → 若最近 3 步构成重复循环
  → 触发 permission "doom_loop"（默认 ask）
  → 用户允许则继续，拒绝则中断
```

**开发者启示**：实现简洁、ROI 高。Qwen Code 可在调度器中加入类似的重复检测（参见 Qwen 自身的多维 Loop 检测）。

## 四、命令前缀/参数级权限（arity 解析）

源码: `packages/opencode/src/permission/arity.ts`（`BashArity`，token 级解析）

对 bash 命令做 token 解析，提取命令前缀用于权限匹配与可复用审批：
- 根命令（`git`、`npm`、`rm`）
- 子命令（`push`、`install`）
- 关键参数（`--force`、`-rf`）

```
"git push --force origin main"
  → token / arity 解析
  → permission pattern: "git push --force"
  → 匹配规则: deny / ask / allow
```

外部目录检测同样基于 token 解析（`packages/core/src/tool/bash.ts` 的 `shellTokens` / `externalCommandDirectories`）。

> **现状**：更深入的 tree-sitter / parser-based AST 解析在 `bash.ts` 中以 TODO 形式标记（"Port tree-sitter bash parser"、"Replace token-based … with parser-based detection"），**尚未实装**。当前权限判断为 token / 前缀级，而非完整 AST。

## 五、文件时间锁

**问题**：Agent 读取 `config.json` → 用户在编辑器中修改 → Agent 基于旧内容写入 → 用户的修改丢失。

**解决方案**：
1. Agent 读取文件时记录 mtime
2. Agent 写入前检查 mtime 是否变化
3. 如果变化，提示用户"文件已被外部修改，是否覆盖？"

源码: snapshot 系统使用 `Semaphore` per git directory 防止并发 git 操作。

## 六、Qwen Code 改进建议

### P1：Doom Loop 保护

最高 ROI 的改进——~30 行代码。在 `CoreToolScheduler` 中添加连续拒绝计数器，超过 3 次自动中断。

### P2：文件时间锁

在 Write/Edit 工具中检查目标文件的 mtime 是否在上次读取后变化。简单但能防止数据丢失。

### P3：命令参数级权限匹配

Qwen Code 已有 `shellAstParser.ts`，可以扩展到参数级权限匹配（如区分 `git push` vs `git push --force`）——这一点已领先 OpenCode（后者的 tree-sitter AST 仍是 TODO，当前为 token/前缀级）。
