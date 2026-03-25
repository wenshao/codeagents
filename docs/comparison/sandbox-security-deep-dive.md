# 29. 沙箱与安全隔离深度对比

> 安全是 AI 编程代理从"玩具"到"生产工具"的关键门槛。从"无权限系统"到"OS 级沙箱 + LLM 安全分类器"，各工具的安全实现差异是所有维度中最大的。

## 总览

| 工具 | 沙箱隔离 | 权限模型 | 安全分类器 | 环境变量保护 | 特殊能力 |
|------|---------|---------|-----------|------------|---------|
| **Codex CLI** | **OS 级三平台** | Guardian 审批 | ✗ | ✓ | Seatbelt/Bwrap/WinToken |
| **Claude Code** | 网络控制 | 5 层 JSON 规则 | **双阶段分类器** | ✓ | 28 BLOCK 规则 + Prompt Hook |
| **Gemini CLI** | 策略引擎 | TOML 5 层优先级 | Conseca（LLM） | **✓（模式匹配）** | 9 策略文件 + 外挂检查器 |
| **OpenHands** | Docker/K8s | 三层安全分析 | **LLM 风险评估** | — | Invariant + GraySwan |
| **OpenCode** | 无 OS 沙箱 | allow/deny/ask | ✗ | — | **Tree-sitter Bash AST** |
| **Goose** | 无 OS 沙箱 | SmartApprove | **对抗检测器** | **✓（31 项）** | AdversaryInspector |
| **Cline** | 无 OS 沙箱 | 正则 + 设置 | ✗ | — | **Git Checkpoint** + 重定向检测 |
| **Qwen Code** | 无 OS 沙箱 | deny > ask > allow | ✗ | — | **Loop 检测**（Levenshtein） |
| **Kimi CLI** | 无 | YOLO 切换 | ✗ | — | 会话级审批 |
| **Aider** | 无 | 信任模式 | ✗ | — | 用户确认 shell |

---

## 一、Codex CLI：三平台 OS 级沙箱（最硬核）

> 源码：`codex-rs/`，[安全文档](https://developers.openai.com/codex/agent-approvals-security)

### macOS — Seatbelt（`sandbox-exec`）

- 运行时动态生成 SBPL（Sandbox Profile Language）策略
- `seatbelt_base_policy.sbpl` 定义核心拒绝和系统权限
- 默认阻止网络；允许回环流量到 `HTTPS_PROXY` 端口
- 环境变量 `CODEX_SANDBOX=seatbelt` 标识沙箱进程

### Linux — 三层防御

| 层 | 技术 | 作用 |
|---|------|------|
| 外层 | **Bubblewrap (bwrap)** | 文件系统命名空间隔离 |
| 内层 | **Landlock** | 可写目录白名单 |
| 最内层 | **Seccomp** | 系统调用过滤，阻止网络 syscall |

- `/usr`、`/bin`、`/lib` 只读挂载
- `.git`、`.agents`、`.codex` 始终只读

### Windows — 受限令牌

- 创建 `CodexSandboxOffline` / `CodexSandboxOnline` 本地用户
- `CreateProcessAsUser` 使用受限令牌，剥离 `SeDebugPrivilege`
- Windows 防火墙规则按 SID 控制网络
- "Preflight Audit" 扫描不安全的 `Everyone:Write` 目录

### 拒绝检测与重试

平台特定错误检测触发 `ToolOrchestrator` 向用户请求提升权限：
- macOS: `sandbox-exec: Operation not permitted`
- Linux: `bwrap: Permission denied`
- Windows: `Access is denied`

---

## 二、Claude Code：28 BLOCK 规则 + 双阶段分类器

> 来源：二进制反编译 v2.1.81，06-settings.md

### 28 条 BLOCK 规则（从二进制逐字提取）

| 类别 | 规则示例 |
|------|---------|
| **Git 破坏** | force push、删除分支、push 到 main/master |
| **远程操作** | kubectl/docker/ssh 写入、生产部署 |
| **数据安全** | 凭证泄露、数据外泄、外泄侦查 |
| **权限提升** | admin/IAM/RBAC 授权、TLS/认证弱化 |
| **本地破坏** | `rm -rf`、日志/审计篡改 |
| **代码安全** | RCE 攻击面（eval/shell 注入）、不受信任的代码集成 |
| **外部系统** | Jira/Linear 写入、真实交易（购买） |
| **自我修改** | 未授权持久化（SSH key/.bashrc）、自我修改 |

### 双阶段安全分类器

```
用户请求 → 快速阶段（256 tokens）
           ├── 无风险 → 放行
           └── 有风险 → 深度阶段（4096 tokens）
                        ├── <block>no</block> → 放行
                        └── <block>yes</block><reason>...</reason> → 阻止
```

**Fail-safe**：分类器出错时默认 "blocking for safety"。

### Prompt Hook（独有）

```json
{
  "hooks": {
    "PreToolUse": [{
      "matcher": "Bash",
      "hook": "prompt-hook: 检查命令是否涉及生产环境"
    }]
  }
}
```

- **Prompt Hook vs 脚本 Hook**：LLM 推理理解语义意图 → 无需穷举规则
- 示例：规则"不允许操作生产环境"，LLM 能理解 `ssh prod-server` 和 `kubectl apply` 都是生产操作

---

## 三、Gemini CLI：TOML 策略引擎 + Conseca

> 源码：`packages/core/src/policy/` + `packages/core/src/safety/`

### 9 个内置策略文件

`conseca.toml`、`discovered.toml`、`memory-manager.toml`、`plan.toml`、`read-only.toml`、`sandbox-default.toml`、`tracker.toml`、`write.toml`、`yolo.toml`

### 双安全检查器

| 检查器 | 类型 | 作用 |
|--------|------|------|
| **allowed-path** | InProcess | 路径白名单验证 |
| **Conseca** | InProcess | LLM 驱动的最小权限策略生成器（默认关闭） |
| **外挂检查器** | External（子进程） | 第三方安全检查器，IPC 通信 |

### 环境变量保护（模式匹配）

| 策略 | 变量 |
|------|------|
| 始终允许 | PATH, HOME, SHELL, TERM, LANG, TMPDIR |
| 始终阻止 | CLIENT_ID, DB_URI, CONNECTION_STRING |
| 模式阻止 | `*TOKEN*`, `*SECRET*`, `*PASSWORD*`, `*KEY*`, `*AUTH*`, `*CREDENTIAL*`, `*PRIVATE*`, `*CERT*` |

---

## 四、OpenHands：三层安全分析

> 来源：openhands.md

```
Agent 动作
  ├── Layer 1: LLM 风险评估
  │   └── 分类：LOW / MEDIUM / HIGH
  │
  ├── Layer 2: Invariant 策略检查
  │   └── 密钥泄露检测 + 恶意命令识别
  │
  └── Layer 3: GraySwan 外部监控
      └── HIGH 风险 → 暂停 + 等待用户确认
```

### Docker/K8s 沙箱

- 代理在 Docker 容器或 K8s Pod 中执行
- 文件系统隔离 + 网络限制
- EventStream 架构支持异步安全审查

---

## 五、创新安全特性对比

| 特性 | 工具 | 原理 | 独特价值 |
|------|------|------|---------|
| **Tree-sitter Bash AST** | OpenCode | AST 级解析命令，提取目录和操作类型 | 比正则更准确的命令理解 |
| **Prompt Hook** | Claude Code | LLM 推理决定允许/拒绝 | 语义理解，无需穷举规则 |
| **Conseca** | Gemini CLI | LLM 生成最小权限策略 | 自适应安全策略 |
| **AdversaryInspector** | Goose | 模式匹配 + 可选 ML + LLM 审查 | 对抗性输入检测 |
| **Loop 检测** | Qwen Code | Levenshtein 距离检测重复调用 | 防止工具调用死循环 |
| **Doom Loop** | OpenCode | 3 次连续拒绝自动中断 | 防止审批疲劳 |
| **Git Checkpoint** | Cline | 每步 Git 快照 | 一键回滚任何操作 |
| **重定向检测** | Cline | 检测 `>`, `>>`, `|`, `&&`, 子 shell | 防止隐蔽命令注入 |
| **三层安全** | OpenHands | LLM + 策略 + 外部监控 | 最全面的纵深防御 |
| **31 变量白名单** | Goose | 阻止 PATH/LD_PRELOAD 等注入 | 防环境变量攻击 |

---

## 安全成熟度评估

| 工具 | OS 沙箱 | 权限粒度 | 智能分析 | 环境保护 | 综合评分 |
|------|--------|---------|---------|---------|---------|
| **Codex CLI** | ★★★★★ | ★★★☆☆ | ★☆☆☆☆ | ★★★☆☆ | **★★★★☆** |
| **Claude Code** | ★★☆☆☆ | ★★★★★ | ★★★★★ | ★★★☆☆ | **★★★★☆** |
| **Gemini CLI** | ★★☆☆☆ | ★★★★★ | ★★★★☆ | ★★★★★ | **★★★★☆** |
| **OpenHands** | ★★★★☆ | ★★★☆☆ | ★★★★★ | ★★☆☆☆ | **★★★★☆** |
| **Goose** | ★☆☆☆☆ | ★★★☆☆ | ★★★☆☆ | ★★★★★ | **★★★☆☆** |
| **OpenCode** | ★☆☆☆☆ | ★★★☆☆ | ★★★☆☆ | ★☆☆☆☆ | **★★★☆☆** |
| **Cline** | ★☆☆☆☆ | ★★★☆☆ | ★☆☆☆☆ | ★☆☆☆☆ | **★★☆☆☆** |
| **Qwen Code** | ★☆☆☆☆ | ★★★☆☆ | ★★☆☆☆ | ★☆☆☆☆ | **★★☆☆☆** |

> **核心洞察**：Codex CLI 在 OS 级隔离最强（三平台原生沙箱），Claude Code 在智能分析最强（28 规则 + 双阶段分类器），Gemini CLI 在策略灵活性最强（TOML + 正则 + 注解），OpenHands 在纵深防御最全面（三层分析）。没有任何一个工具在所有维度都领先。

---

## 证据来源

| 工具 | 来源 | 获取方式 |
|------|------|---------|
| Codex CLI | `codex-rs/` + [安全文档](https://developers.openai.com/codex/agent-approvals-security) | Rust 源码 + 官方文档 |
| Claude Code | EVIDENCE.md（259-309 行）+ 06-settings.md | 二进制反编译 |
| Gemini CLI | 05-policies.md + EVIDENCE.md（67-102 行） | 开源 |
| OpenHands | openhands.md（90-97 行） | 开源 |
| OpenCode | 01-overview.md（30-32 行）| 开源 |
| Goose | EVIDENCE.md（41-59 行）| 开源 |
| Cline | cline.md（94-109 行）| 开源 |
