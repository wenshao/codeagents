# Qwen Code 改进建议 — `/security-review` 安全专项审查命令 (Security Review Command)

> 核心洞察：Qwen Code 已经有通用 `/review` 能力，能够同时覆盖 correctness、security、code quality、performance 四个维度；但 Claude Code 进一步把“安全审查”单独产品化为 `/security-review`。这不是简单换一个 prompt 名字，而是把安全审查从“通用 code review 的一个子维度”提升为“有独立目标、独立排除规则、独立信号质量标准的专项工作流”。
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md)

## 一、为什么通用 `/review` 不能完全替代 `/security-review`

代码审查里的“安全问题”与“普通代码问题”在方法论上并不一样。

| 维度 | 通用 `/review` | 专项 `/security-review` |
|------|----------------|-------------------------|
| 目标 | 找出 correctness / style / performance / security 各类问题 | 只关注新增安全漏洞 |
| 容忍噪音 | 可接受一定 Suggestion / Nice to have | 必须极低误报 |
| 分析范围 | 全面代码质量 | exploit path、攻击面、可利用性 |
| 输出标准 | 一般性 review finding | 漏洞类别、影响、攻击场景、修复建议 |
| 排除规则 | 相对宽泛 | 需要明确过滤大量伪阳性 |

例如：
- SQL injection
- XSS
- path traversal
- auth bypass
- deserialization / eval injection
- crypto misuse

这些问题往往需要与以下内容一起判断：
- 输入是否真的来自不可信边界
- 是否存在明确 exploit path
- 是否只是理论风险而不是实际漏洞
- 是否属于已有风险而非本 PR 新引入的问题

如果继续把安全检查塞进通用 `/review`，常见结果就是两种极端：
1. **报得太少**：安全类问题被 correctness / style / perf 信息淹没
2. **报得太多**：出现大量“像安全问题，但其实没有明确攻击路径”的噪音

所以 Claude Code 把安全审查拆成单独命令，本质上是在做 **review workflow specialization（审查工作流专项化）**。

---

## 二、Claude Code 的做法：把安全审查做成独立命令，而不是附带能力

Claude Code 在 `commands/security-review.ts` 中直接定义了一个独立的 `/security-review` 命令。

### 1. 命令层就是“安全专项”而不是通用 review 变体

文件头部的 frontmatter 已经非常明确：

```md
allowed-tools: Bash(git diff:*), Bash(git status:*), Bash(git log:*), Bash(git show:*), Bash(git remote show:*), Read, Glob, Grep, LS, Task
description: Complete a security review of the pending changes on the current branch
```

这里有两个关键信号：

- **工具权限是收窄的**：只给安全审查真正需要的 git/read/search 能力
- **命令目标是单一的**：`security review`，不是 generic review

这意味着 Claude 并没有把安全审查当成 `/review --security` 这种轻量参数，而是直接承认它是另一种不同的审查任务。

### 2. Prompt 明确要求只关注“高置信度安全漏洞”

Claude 的命令提示词里有几条非常关键的约束：

- `Perform a security-focused code review`
- `focus ONLY on security implications newly added by this PR`
- `Only flag issues where you're >80% confident of actual exploitability`
- `Better to miss some theoretical issues than flood the report with false positives`

这套约束实际上定义了 `/security-review` 的产品哲学：

> **宁可漏掉边缘案例，也不要用大量理论性安全问题污染 PR 讨论。**

这是安全审查命令与通用 `/review` 最本质的区别之一。

### 3. 漏洞类型被显式结构化

Claude 不是简单说一句“请找安全问题”，而是把检查重点拆成了明确类别：

- Input Validation Vulnerabilities
  - SQL injection
  - Command injection
  - XXE
  - Template injection
  - NoSQL injection
  - Path traversal
- Authentication & Authorization Issues
- Crypto & Secrets Management
- Injection & Code Execution
- Data Exposure

这带来两个直接收益：

1. 审查模型不会把注意力浪费在 style / architecture 上
2. 输出结果更容易被安全团队消费与归档

### 4. 有一整套“伪阳性过滤规则”

`commands/security-review.ts` 最有价值的部分，不只是漏洞类别，而是它内置了非常长的一组 **FALSE POSITIVE FILTERING** 规则。

它会明确排除诸如：
- DoS / 资源耗尽
- 磁盘上 secrets（由其他流程处理）
- rate limiting
- 理论 race condition
- 旧三方依赖漏洞
- Rust 中的 memory safety 问题
- 仅测试文件中的问题
- log spoofing
- 只能控制 path 的 SSRF
- 将用户内容拼进 AI prompt
- regex injection / regex DoS
- 文档文件中的不安全写法
- 缺少 audit log

这说明 Claude 已经意识到：

> **一个可用的安全审查命令，关键不是“能想到多少漏洞名词”，而是能否系统性地去噪。**

### 5. 输出格式也是面向安全审查消费的

Claude 要求输出里包含：
- file / line
- severity
- category
- description
- exploit scenario
- recommendation

这比普通 review finding 更接近安全团队真正会使用的漏洞报告格式。

**Claude Code 关键源码**：
- `commands/security-review.ts`

---

## 三、Qwen Code 现状：有 `/review`，但没有“安全专项产品面”

Qwen Code 并不是没有审查能力。

### 1. Qwen 已有通用 `/review`

Qwen 的 bundled skill `packages/core/dist/src/skills/bundled/review/SKILL.md` 明确把 `/review` 定义为：

> `Review changed code for correctness, security, code quality, and performance.`

并在 Step 2 中拆成四个并行 Agent：
- Agent 1: Correctness & Security
- Agent 2: Code Quality
- Agent 3: Performance & Efficiency
- Agent 4: Undirected Audit

这说明 Qwen 的 `/review` 并不弱，甚至已经有不错的多维并行设计。

### 2. 但“security”只是 `/review` 的一个子维度

问题在于，Qwen 目前的 security review 逻辑仍然嵌在通用 code review 工作流里：
- 它要同时平衡 correctness、quality、performance
- security 只是 Agent 1 的一部分
- 没有单独的漏洞类别框架
- 没有一整套高信号过滤规则
- 没有专门的 exploitability 置信度门槛

换句话说，Qwen 当前更像是：

> **带有安全维度的通用审查命令**

而不是：

> **面向安全漏洞检测的专项审查命令**

### 3. Built-in commands 中也没有 `/security-review`

`packages/cli/src/services/BuiltinCommandLoader.ts` 列出了所有 built-in slash commands，当前并没有 `security-review`。

因此在产品入口层，Qwen 用户能直接发现的只有：
- `/review`
- `/skills`
- 其他 built-in command

而没有一个清晰的“现在我要做安全专项审查”的一等入口。

### 4. 文档层也缺少安全专项命令说明

Qwen 当前用户文档与命令文档里，没有发现与 Claude `/security-review` 对应的独立命令说明。对用户而言，这会形成一个很现实的使用差异：

- 在 Claude Code 中，用户会自然想到：`/security-review`
- 在 Qwen Code 中，用户需要自己推断：也许用 `/review`，也许要手工写 prompt，或者自己额外写 skill

这种差异本质上是 **discoverability（可发现性）** 与 **workflow packaging（工作流封装）** 的差异。

**Qwen Code 关键证据**：
- `packages/core/dist/src/skills/bundled/review/SKILL.md`
- `packages/cli/src/services/BuiltinCommandLoader.ts`

---

## 四、两者差距的本质：安全审查是否被“专项化”

| 维度 | Claude Code | Qwen Code |
|------|-------------|-----------|
| 通用 `/review` | 有 | 有 |
| 独立 `/security-review` | 有 | 无 |
| 专项漏洞类别 | 有 | 无独立层 |
| 大规模伪阳性排除规则 | 有 | 无同等级独立规则 |
| exploitability 置信度门槛 | 明确 >80% | 通用 review 中未单独强化 |
| 输出格式面向安全报告 | 是 | 通用 review finding 格式 |

因此这个差距不应被描述为“Qwen 没有安全审查能力”，更准确的说法是：

> **Qwen 已有安全维度审查，但尚未像 Claude 那样把安全审查独立封装成高信号、低噪音、可直接调用的专项工作流。**

这也是为什么这个点值得单独写文档：它不是“命令数量对比”，而是 **review 产品层级的设计差异**。

---

## 五、Qwen Code 的改进路径

### 路径 1：最小版本 —— 新增 `security-review` bundled skill

最低成本的做法，是直接新增：

- `packages/core/src/skills/bundled/security-review/SKILL.md`

然后复用 Qwen 现有 skill 分发与 slash command 入口体系，让用户可以直接调用：

- `/security-review`

这一步不要求先改 built-in loader，只要确保 skill 被正常发现和展示即可。

### 路径 2：把 Claude 的“去噪设计”移植过来

真正关键的不只是新增一个名字，而是把安全专项逻辑做扎实：

1. **限定分析目标**：仅审查当前 diff / 当前 PR 新引入的安全风险
2. **定义漏洞分类**：SQL injection、XSS、auth bypass、path traversal、deserialization 等
3. **引入明确排除规则**：过滤掉大量理论性、低价值、安全边缘问题
4. **定义置信度门槛**：如“低于 0.8 不报告”
5. **要求 exploit scenario**：每个 finding 必须说明实际攻击路径

只要缺了第 3、4、5 项，`/security-review` 就很容易退化成“把安全 buzzword 再喊一遍”的噪音命令。

### 路径 3：与现有 `/review` 协同，而不是互相取代

最合理的产品关系应该是：

- `/review`：默认通用代码审查
- `/security-review`：发布前 / 合并前的安全专项扫描

这两个命令可以互补：
- 通用 review 负责正确性、代码质量、性能
- security-review 专注高信号漏洞

而不是试图让一个命令覆盖一切。

### 路径 4：未来可增加安全特化输出与 PR 集成

如果继续向前演进，Qwen 还可以补上：
- `--comment` 风格的 PR inline security comments
- SARIF / JSON 输出
- 与 CI / GitHub Actions 集成
- 与规则库（OWASP ASVS / Top 10）映射

但这些都应该建立在“先把安全专项审查命令产品化”之上。

---

## 六、优先级判断

从实现成本看，这项能力不算很高：

- **最小可用版本**：新增安全专项 skill，成本较小
- **高质量版本**：补上 false-positive filtering 与高置信输出模板，成本中等
- **平台化版本**：再接 PR comment / CI / SARIF，成本继续上升

因此它很适合放在 **P3→P2 候选提升项**：
- 从纯工程实现难度看不高
- 但对用户价值和产品认知价值很高
- 尤其适合面向企业、开源维护者、需要做 PR gate 的用户

如果 Qwen 后续继续强化 `/review` 生态，那么 `/security-review` 是非常自然的下一步。

---

## 七、对用户的直接收益

如果 Qwen Code 补上 `/security-review`，最直接的收益包括：

1. **更明确的工作流入口**  
   用户不需要再自己思考“该用 `/review` 还是自己写 prompt 做安全扫描”。

2. **更低噪音的安全审查**  
   专项命令可以明确牺牲覆盖面，换取更高置信度。

3. **更符合 DevSecOps 流程**  
   在 merge 前、release 前、CI 阶段，都更容易把安全审查接进标准流程。

4. **与通用 review 形成分层**  
   `/review` 负责全面质量，`/security-review` 负责高风险漏洞，两者定位清晰。

---

## 八、结论

Claude Code 与 Qwen Code 在 review 能力上的差距，已经不只是“有没有 `/review`”。

Qwen Code 目前已经有不错的通用 `/review`，甚至覆盖了 security 维度；但 Claude Code 更进一步，把安全审查独立封装成：
- 单独命令
- 单独目标
- 单独漏洞分类
- 单独排除规则
- 单独信号质量门槛

这让 `/security-review` 不再只是“换个 prompt 做 review”，而成为一条真正可以进工程流程的安全专项工作流。

对于 Qwen Code 来说，这正是一个很典型、很值得补齐的产品差距：

> **不是从 0 到 1 补“安全审查能力”，而是把现有 review 中的 security 维度升级成独立、可发现、低噪音的专项命令。**

---

## 关键源码索引

### Claude Code
- `commands/security-review.ts`

### Qwen Code
- `packages/core/dist/src/skills/bundled/review/SKILL.md`
- `packages/cli/src/services/BuiltinCommandLoader.ts`

> **免责声明**：以上结论基于 2026-04 本地源码与当前仓库文档对比，后续版本可能已变更。