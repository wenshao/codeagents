# Qwen Code 改进建议 — @include 指令与嵌套记忆自动发现 (Modular Memory & Auto-Discovery)

> 核心洞察：在一个大型的 Monorepo（单体仓库）中，前端（React/TypeScript）、后端（Go/Python）和文档目录通常有着截然不同的代码风格和最佳实践。如果将所有规则全挤在一个根目录的 `QWEN.md` 里，不仅浪费 Token，还会因为规则冲突导致大模型产生幻觉（例如在 Go 代码里错误应用了 React 的规范）。Claude Code 通过引入 `@include` 指令与“递归向上遍历查找”的嵌套记忆自动发现机制，完美解决了这个痛点，而 Qwen Code 目前欠缺这一精细化的规则挂载能力。
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md)

## 一、架构缺陷与使用痛点

### 1. Qwen Code 的现状：单体配置困境
Qwen Code 目前通常只读取项目根目录下的少量特定配置文件。
- **配置割裂与臃肿**：假设你在维护一个全栈项目。你需要告诉 Agent：“前端要使用 `camelCase`，并使用 TailwindCSS；后端要使用 `snake_case`，不要使用 ORM，手写 SQL”。在现有的单文件配置模式下，这些冲突的指令只能揉在一起，导致 System Prompt 急剧膨胀。
- **无模块化能力**：开发者不能像写代码 `import` 那样复用规范，多项目之间共享的通用规范（如安全准则）必须复制粘贴多次。

### 2. Claude Code 的解决方案：多级挂载与引用
在 `utils/claudemd.ts` 中，Claude Code 实现了一套灵活的文档加载器系统：

#### 机制一：目录级别的记忆自动发现 (Directory Traversal)
当你让 Agent 编辑 `src/frontend/components/Button.tsx` 时，Claude Code 不仅会读取全局配置，还会沿着目标文件所在的路径“**逐级向上爬**”：
1. 查找全局系统配置 (`/etc/claude-code/CLAUDE.md`)
2. 查找用户根目录 (`~/.claude/CLAUDE.md`)
3. 查找项目根目录 (`/project/CLAUDE.md`)
4. 查找沿途的特定目录 (`/project/src/frontend/CLAUDE.md`, `.claude/rules/*.md` 等)

并且，优先级是**越具体的越近（后加载覆盖前加载）**。这意味着在处理前端组件时，Agent 会优先看到针对前端的专项定制化指令，不会被后端的指令干扰。

#### 机制二：@include 指令的动态引入
如果不想依赖隐式的目录查找，Claude Code 还提供显式的 `@include` 指令。
开发者可以在 `CLAUDE.md` 的任何文本节点（不在代码块内）写下：
```markdown
# 我们的全栈项目规范
@./src/frontend/frontend_rules.md
@~/global_security_rules.md
```
加载器会拦截这些指令（利用 `marked` 进行 Lex 解析提取 Tokens），并将引用的文件内容平铺（Inline）注入到上下文中。系统还硬编码了 `MAX_INCLUDE_DEPTH = 5` 防止循环引用死锁。

## 二、Qwen Code 的改进路径 (P1 优先级)

要实现智能体的工业级落地，Qwen Code 必须支持配置的去中心化与模块化。

### 阶段 1：支持目录爬升自动加载 (Directory Climbing)
1. 拦截文件修改操作（如在 Tool 层或更底层的 Context 组装阶段）。
2. 每当涉及某个具体文件路径时，计算该路径的祖先目录数组。
3. 从上到下，依次读取 `.qwen.md` 或 `.qwen/rules/*.md` 并注入系统提示。

### 阶段 2：解析与支持 @include (Include Directive)
1. 编写或引入一个小型的 Markdown 解析器/正则表达式层，在读取 `QWEN.md` 时拦截以 `@` 开头的独立行。
2. 支持 `@./` (相对当前配置文件) 和 `@~/` (相对用户 Home 目录) 两种路径。
3. 递归解析这些文件，并拼接最终的纯文本 System Prompt。

### 阶段 3：缓存去重与安全防御
1. 引入解析树去重机制（避免被包含的文件内部出现交叉包含引发栈溢出）。
2. 只允许包含纯文本后缀的文件（如 `.txt`, `.md`），拒绝 `.bin`, `.exe` 等二进制文件读取以防止奇怪的文件系统错误。

## 三、改进收益评估
- **实现成本**：中。需要改造配置加载阶段的逻辑。
- **直接收益**：
  1. **巨幅节省 Token 成本**：按需加载让大模型的系统上下文变得精简、相关，消除不必要的输入计费。
  2. **消除规则冲突**：Monorepo 下前后端协作再也不用担心大模型混淆命名规范或架构约定。
  3. **增强企业级复用能力**：团队可以通过 `@~/` 引入全局的安全指南，真正做到架构规范的“代码化（Config as Code）”。