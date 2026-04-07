# 7. 权限系统——开发者参考

> OpenCode 的权限系统有三个独特设计：Tree-sitter Bash AST 分析（精确到参数级的命令权限判断）、Doom Loop 保护（连续拒绝自动中断）、文件时间锁（检测编辑期间外部修改）。
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
| **OpenCode** | Tree-sitter AST（参数级） | ✓ Doom Loop（连续 3 次拒绝中断） | ✓ 文件时间锁 |
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

**问题**：Agent 被拒绝后换个措辞再试，用户再拒绝，Agent 再试——无限循环浪费 token。

**解决方案**：连续 N 次权限拒绝后自动中断 Agent 执行。

```
拒绝计数 = 0

工具请求权限 → 用户拒绝 → 拒绝计数 += 1
                         → 拒绝计数 ≥ 3 → 自动中断，提示"检测到循环拒绝"
                         
工具请求权限 → 用户允许 → 拒绝计数 = 0（重置）
```

**开发者启示**：~30 行代码实现，高 ROI。Qwen Code 应该立即实现——防止 yolo 模式之外的 Agent 陷入权限拒绝循环。

## 四、Tree-sitter Bash AST 分析

源码: `packages/opencode/src/permission/arity.ts`

使用 Tree-sitter 解析 bash 命令的 AST，提取：
- 根命令（`git`、`npm`、`rm`）
- 子命令（`push`、`install`）
- 关键参数（`--force`、`-rf`）

```
"git push --force origin main"
  → AST 分析
  → permission pattern: "git.push.--force"
  → 匹配规则: deny("git.push.--force")
```

**vs 正则匹配**：正则 `rm -rf` 会误匹配 `echo "rm -rf"`（字符串中的 rm）。AST 分析只匹配实际命令，不匹配字符串内容。

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

### P3：Tree-sitter Bash AST

Qwen Code 已有 `shellAstParser.ts`，可以扩展到参数级权限匹配（如区分 `git push` vs `git push --force`）。
