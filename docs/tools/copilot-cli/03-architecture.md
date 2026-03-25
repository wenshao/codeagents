# 3. 技术架构（源码分析）

> 以下基于 v0.0.403（`@github/copilot`）npm 包源码分析。

## 运行时

| 项目 | 详情 |
|------|------|
| **包结构** | `npm-loader.js` → 尝试原生二进制 → 回退到 `index.js`（Node.js v24+） |
| **JS Bundle** | `index.js`（15MB）+ `sdk/index.js`（11MB），minified 单文件 |
| **原生二进制** | `@github/copilot-{platform}-{arch}` 平台包（优先使用） |
| **UI 框架** | **Ink（React for CLI）**+ Yoga 布局（index.js 中 211 处引用） |
| **原生模块** | `keytar.node`（凭据/钥匙串访问）、`pty.node`（伪终端） |

## 双模式加载器

```javascript
// npm-loader.js 简化流程
try {
  const binary = require(`@github/copilot-${platform}-${arch}/copilot`);
  spawnSync(binary, args);  // 优先使用原生二进制
} catch {
  require('./index.js');     // 回退到 Node.js
}
```

## 代理系统（YAML 定义）

三个内置代理在 `definitions/` 目录中以 YAML 定义：

### code-review 代理（完整 YAML 提取）

> 源码：`definitions/code-review.agent.yaml`，完整内容见 [EVIDENCE.md](./EVIDENCE.md)

| 项目 | 值 |
|------|-----|
| **模型** | `claude-sonnet-4.5` |
| **工具** | `*`（全部，但 prompt 禁止使用 edit/create） |
| **promptParts** | includeAISafety ✓, includeToolInstructions ✓, includeParallelToolCalling ✓ |

**审查维度（prompt 明确定义的 8 个）：**

| 维度 | 说明 |
|------|------|
| Bugs and logic errors | 代码逻辑缺陷 |
| Security vulnerabilities | 安全漏洞 |
| Race conditions or concurrency issues | 竞态条件和并发问题 |
| Memory leaks or resource management | 内存泄漏和资源管理 |
| Missing error handling that could cause crashes | 缺失的错误处理 |
| Incorrect assumptions about data or state | 对数据或状态的错误假设 |
| Breaking changes to public APIs | 公共 API 的破坏性变更 |
| Performance issues with measurable impact | 可衡量的性能问题 |

**显式排除的假阳性（prompt 明确禁止评论的 8 类）：**

| 禁止评论 | 原因 |
|----------|------|
| Style, formatting, naming conventions | 代码风格不是 bug |
| Grammar/spelling in comments/strings | 拼写不影响功能 |
| "Consider doing X" suggestions | 建议不是 bug |
| Minor refactoring opportunities | 微重构不紧急 |
| Code organization preferences | 主观偏好 |
| Missing documentation or comments | 文档缺失不是 bug |
| "Best practices" without actual problems | 不防止实际问题的最佳实践 |
| Anything uncertain | **不确定就不报告** |

**核心原则（prompt 原文）：**
> "Your guiding principle: finding your feedback should feel like finding a $20 bill in your jeans after doing laundry - a genuine, delightful surprise. Not noise to wade through."

**审查流程（prompt 定义的 4 步）：**
1. **理解变更范围** — `git status` → staged diff / unstaged diff / branch diff against main
2. **理解上下文** — 读取周围代码，理解意图、系统集成、不变量
3. **验证** — 尝试编译、运行测试、检查是否在其他地方处理
4. **仅报告高置信度问题** — 不确定就不报告

**输出格式：**
```markdown
## Issue: [Brief title]
**File:** path/to/file.ts:123
**Severity:** Critical | High | Medium
**Problem:** Clear explanation
**Evidence:** How you verified this
**Suggested fix:** Brief description (不实现)
```

**关键约束：** `You Must NEVER Modify Code` — 所有工具仅用于调查，禁止使用 edit/create。

### explore 代理（完整 YAML 提取）

> 源码：`definitions/explore.agent.yaml`

| 项目 | 值 |
|------|-----|
| **模型** | `claude-haiku-4.5`（轻量快速） |
| **工具** | 仅 `grep, glob, view, lsp`（4 个只读工具） |
| **回答限制** | **300 字以内** |

**设计原则（prompt 关键指令）：**
- 目标 1-3 次工具调用完成回答
- **最大化并行工具调用** — 多个 grep/glob/view 必须在单次响应中并行调用
- 使用 `{{cwd}}` 前缀确保绝对路径
- 使用项目符号而非表格（可读性）
- 只读取与问题直接相关的文件

### task 代理（完整 YAML 提取）

> 源码：`definitions/task.agent.yaml`

| 项目 | 值 |
|------|-----|
| **模型** | `claude-haiku-4.5` |
| **工具** | `*`（全部） |

**输出策略（最小化上下文污染）：**
- **成功时**：单行摘要（如 "All 247 tests passed"、"Build succeeded in 45s"）
- **失败时**：完整错误输出（堆栈跟踪、编译错误、lint 问题）
- **禁止**：不尝试修复错误、不分析问题、不提建议、不重试
- **超时**：测试/构建 200-300 秒，lint 60 秒

## API 层

- `api.github.com` — 标准 GitHub API
- `api.githubcopilot.com` — Copilot 专用 API
- `api.githubcopilot.com/mcp/readonly` — MCP 只读端点

## 安全机制

- SDK 模块加载限制：`require()` 解析到应用目录外时抛出安全错误
- `keytar.node` 使用系统钥匙串存储凭据（macOS Keychain、Linux Secret Service）
- 工具协议：原生工具 + MCP（Model Context Protocol）
- 浏览器自动化：基于 Playwright
- 搜索引擎：内置 ripgrep
- 代理定义：YAML 格式（`.agent.yaml`）
