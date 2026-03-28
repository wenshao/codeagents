# 41. Everything Code Agent vs IDE Agent：万能终端 Agent 与编辑器 Agent 的范式之争

> 2026 年的 AI 编程 Agent 已不再是"编码助手"——Claude Code 通过 MCP/Channels/Teammates/Schedule 演变为**万能终端 Agent**（Everything Code Agent），而 Cursor 通过 Background Agent 也在向通用化发展。真正的竞争是**"万能 Agent 入口"之争**。

## "Everything Code Agent" 是什么？

Claude Code 在 2026 年已经不只是写代码的工具：

```
Claude Code（Everything Code Agent）
  │
  ├── 编码能力（传统）
  │   └── Read/Edit/MultiEdit/Bash/Grep/Glob + ~79 命令 + 20+ 内置工具
  │
  ├── 外部世界连接（MCP 驱动）
  │   ├── 数据库查询（@modelcontextprotocol/server-postgres）
  │   ├── 项目管理（Jira/Linear MCP 服务器）
  │   ├── 团队通知（Slack/Teams MCP 服务器）
  │   ├── 监控/告警（Grafana/Datadog MCP）
  │   └── 任何 API（自定义 MCP 服务器）
  │
  ├── 自动化（内置）
  │   ├── /loop — 定时轮询（默认间隔 10 分钟）
  │   ├── /schedule — Cron 定时（每天 9 点审查 PR）
  │   └── Channels — 外部消息推送（Telegram/Discord，研究预览）
  │
  └── 团队协作
      ├── Teammates — AI-AI 多代理分工协作
      └── Team Memory API — 仓库级共享知识
```

**这不再是一个"编码 Agent"，而是一个以编码为核心、通过 MCP 连接万物的通用终端 Agent。**

同理，Codex CLI（Cloud 远程执行）、Gemini CLI（A2A 远程代理）、Qwen Code（Arena 多模型竞争）也在各自方向扩展。

## 范式总览

| 维度 | Everything Code Agent（终端原生） | IDE Agent（编辑器内嵌） | 混合型 |
|------|-------------------------------|----------------------|--------|
| **代表** | Claude Code、Codex CLI、Gemini CLI、Qwen Code、Aider、Copilot CLI、Kimi CLI | Cursor、Cline、Continue | Warp（Agentic Dev Env）、Qoder CLI（ACP） |
| **核心定位** | **万能终端 Agent**（编码 + MCP 万物连接） | **编辑器增强**（补全 + 内联 + diff） | 终端 + IDE 桥接 |
| **运行环境** | 终端进程 | IDE 扩展/内嵌 | 终端 + IDE |
| **交互模式** | 对话式（prompt → 自主完成） | 内联式（补全 + diff 预览 + 侧边栏） | 混合 |
| **上下文来源** | 显式工具调用（Read/Grep/Glob） | IDE 自动提供（打开文件、光标、诊断） | 两者兼有 |
| **自主性** | **高**（长链多步自主操作） | 中（需用户确认每步） | 高 |
| **外部集成** | **MCP 协议**（连接任何外部系统） | 有限（IDE 内扩展） | 部分 |
| **CI/CD** | **原生支持** | 通常不支持 | 部分 |
| **启动速度** | ~50ms（原生 Rust）~ ~1.5s（Node.js/Python） | 3~10s（Electron） | 亚秒级~数秒 |

> **免责声明**：启动速度为本机实测数据（2026-03-26，`time <agent> --version`，3 次取中位数，Linux x86-64）。Claude Code v2.1.84、Codex CLI v0.116.0、Gemini CLI v0.34.0、Qwen Code v0.13.0。

---

## 一、上下文获取：显式 vs 隐式

这是两种范式最根本的差异。

### Everything Agent：通过工具调用主动获取

```
用户："修复 auth 模块的 Bug"
  → Agent 调用 Glob("src/auth/**")    # 找到相关文件
  → Agent 调用 Read("src/auth/login.ts")  # 读取文件内容
  → Agent 调用 Grep("validateToken")   # 搜索关键函数
  → Agent 理解代码 → 生成修复
```

**优势**：Agent 自主决定需要什么上下文，可以探索整个代码库
**劣势**：每次工具调用消耗 token + 时间

### IDE Agent：从编辑器状态自动获取

```
用户：在 login.ts 第 42 行选中代码，按 Cmd+K
  → IDE 自动提供：
    ├── 当前文件完整内容
    ├── 光标位置和选中区域
    ├── LSP 诊断信息（错误/警告）
    ├── 导入的依赖关系
    └── 最近编辑历史
  → Agent 直接生成修复（无需工具调用）
```

**优势**：零工具调用开销，上下文精准
**劣势**：Agent 只看到 IDE 提供的内容，无法自主探索

### Everything Agent 的"第三种上下文"：MCP 外部数据

```
用户："修复那个导致 Grafana 告警的 Bug"
  → Agent 调用 MCP: grafana_get_alerts()        # 获取告警详情
  → Agent 调用 MCP: jira_get_issue("BUG-1234")  # 获取 Bug 描述
  → Agent 调用 Grep("error_handler")             # 搜索代码
  → Agent 调用 Read + Edit                        # 修复代码
  → Agent 调用 Bash("npm test")                   # 运行测试
  → Agent 调用 MCP: slack_post("#dev", "已修复")  # 通知团队
```

**这是 IDE Agent 做不到的**——整个链条从外部系统（Grafana → Jira）到代码修复到团队通知，全部在一次对话中完成。

### 实际影响

| 场景 | Everything Agent | IDE Agent |
|------|-----------------|-----------|
| 修复**当前文件**的 Bug | 中（需 Read） | **高**（IDE 已加载） |
| 跨 10 个文件的重构 | **高**（自主导航） | 低（需手动打开文件） |
| 理解**未知代码库** | **高**（Grep/Glob） | 低（依赖用户导航） |
| 根据**光标位置**补全 | 不支持 | **极高**（Tab 补全） |
| **查 Grafana 告警→修 Bug→通知** | **✓（MCP 全链路）** | ✗（无外部系统集成） |
| **每天 9 点自动审查 PR** | **✓（/schedule cron）** | ✗（无定时任务） |
| **Telegram 远程触发任务** | **✓（Channels）** | ✗ |

---

## 二、交互模式：对话 vs 内联

### Everything Agent：对话驱动

```bash
> 把所有 console.log 替换为 structured logger

Claude Code/Aider 会：
1. 搜索所有 console.log 调用
2. 分析每个调用的上下文
3. 生成结构化 logger 替换方案
4. 批量修改所有文件
5. 自动提交（Aider）或展示 diff
```

- 一次 prompt 可触发**多文件批量操作**
- Agent 自主决定修改范围
- 通过 `/rewind` 或 `/undo` 回退

### IDE Agent：内联 + 面板

```
Cursor 的交互方式：
├── Tab 补全（实时、逐行）
├── Cmd+K 内联编辑（选中区域原地修改）
├── Cmd+L 聊天面板（侧边栏对话）
├── Cmd+I Agent 模式（Composer 多文件）
└── Background Agent（云端异步）
```

- **Tab 补全**是最高频交互——写代码时自动推理下一行
- **内联编辑**在当前文件原地修改，即时 diff 预览
- **Composer** 模式最接近 CLI Agent 的自主性

---

## 三、各工具详细对比

### Everything Code Agent

| Agent | 语言 | 启动 | 自主链长度 | CI 支持 | 独特能力 |
|-------|------|------|----------|---------|---------|
| **Claude Code** | Rust | **~50ms** | 长（maxTurns + --max-budget-usd） | **`--bare` + stream-json** | 24 Hook + Prompt Hook + Channels |
| **Aider** | Python | ~1s | 3 次反射 | `--message` | 14 编辑格式 + Git 自动提交 |
| **Codex CLI** | Rust | ~76ms | 4~5 级审批模式 | Cloud 远程执行（实验性） | 三平台 OS 沙箱（Windows 实验性） |
| **Gemini CLI** | TS | ~1.5s | 100 轮 | TTY 自动检测 | 8 策略类（7 用户可见）模型路由 |
| **Qwen Code** | TS | ~608ms | 100 轮（MAX_TURNS） | `--non-interactive` | Arena 多模型竞争 |
| **Copilot CLI** | TS (Node.js SEA) | ~72ms | 可配置 | `-p` + Autopilot | 67 工具（12 核心 + 21 浏览器 + 48 平台） |
| **Kimi CLI** | Python | ~1s | 100 步 | — | Wire 协议 + D-Mail（实验性，okabe 代理） |

### IDE Agent

| Agent | 平台 | 代码补全 | 内联编辑 | 多文件编排 | 后台执行 | 独特能力 |
|-------|------|---------|---------|-----------|---------|---------|
| **Cursor** | VS Code 深度分叉 | **Tab**（最强） | **Cmd+K** | Composer | **Background Agent（云端）** | Rules(.mdc) + @ 引用 |
| **Cline** | VS Code 扩展 | ✗ | WebView UI | ✓（只读子代理） | ✗ | **Git Checkpoint** + 26 工具 |
| **Continue** | VS Code + JetBrains + CLI | **Tab** | ✗ | ✓ | ✗ | **PR Checks**（CI 审查规则） |

### 混合型

| Agent | 类型 | 终端能力 | IDE 集成 | 独特定位 |
|-------|------|---------|---------|---------|
| **Warp** | Agentic Development Environment | GPU 渲染 + 块结构 | — | Oz Agent + Warp Drive 团队协作（Warp 2.0 四合一：Code/Agents/Terminal/Drive） |
| **Qoder CLI** | CLI + ACP | Go 原生 43MB | **ACP 协议**（Zed/VS Code/JetBrains） | Quest 模式 + Experts 团队 |

---

## 四、安全模型差异

| 维度 | Everything Agent | IDE Agent |
|------|-----------|-----------|
| **文件访问** | 工具权限控制（deny/ask/allow） | IDE workspace 范围 |
| **命令执行** | 沙箱隔离（Codex CLI 三平台 OS 沙箱） | 通常无沙箱 |
| **网络访问** | 可禁止（`--bare`、沙箱） | IDE 环境不限制 |
| **审批流程** | Claude 24 Hook + Gemini TOML + Codex 沙箱 | 弹窗确认 |
| **企业管控** | managed-settings 远程下发 | Cursor Business 管理面板 |

> Everything Agent 的安全模型显著更成熟——沙箱隔离、28 BLOCK 规则（Claude Code）、TOML 策略引擎（Gemini CLI）是 IDE Agent 没有的。

---

## 五、Git 集成差异

| 能力 | Everything Agent | IDE Agent |
|------|-----------|-----------|
| **自动提交** | Aider（每次编辑自动 commit） | ✗（需手动） |
| **检查点回退** | Claude Code（Esc）、Gemini CLI（/rewind 三选项） | Cline（Git Checkpoint 每步快照） |
| **Worktree 隔离** | Claude Code Teammates（独立 worktree） | Cursor Background Agent（云端隔离） |
| **归因系统** | Aider（Co-authored-by + 3 种归因选项） | ✗ |
| **Git 命令** | Aider（/commit /undo /diff /git） | IDE Git 面板 |

---

## 六、远程开发

| 场景 | Everything Agent | IDE Agent |
|------|-----------|-----------|
| **SSH 到服务器** | 原生（直接 `ssh server && claude`） | 需 Remote SSH 扩展 |
| **Docker 容器** | 原生（`docker exec -it container claude`） | 需 Dev Containers 扩展 |
| **CI/CD 管道** | **原生**（`claude --bare -p "..."`） | 不支持（需要 GUI） |
| **GitHub Actions** | ✓（Codex Cloud、SWE-agent） | ✗ |
| **无头服务器** | ✓ | ✗（需要显示服务器） |

> **关键差异**：Everything Agent 在无 GUI 环境中完全可用，IDE Agent 本质上依赖图形界面。

---

## 七、选型决策

### 选 Everything Code Agent 的场景

- **大规模代码库探索**——Agent 自主搜索，无需手动打开文件
- **CI/CD 自动化**——管道中无头运行（`--bare` + stream-json）
- **远程服务器开发**——SSH 直接使用
- **多文件批量重构**——一次 prompt 修改数十个文件
- **安全敏感场景**——沙箱隔离、28 BLOCK 规则、TOML 策略引擎
- **跨系统工作流**——查 Grafana → 修 Bug → 跑测试 → 通知 Slack（MCP 全链路）
- **团队协作**——Teammates 多代理分工、Channels 外部消息推送
- **定时自动化**——/schedule cron 定时审查 PR、/loop 持续监控

### 选 IDE Agent 的场景

- **日常编码补全**——Tab 逐行补全是最高频需求
- **当前文件快速修复**——Cmd+K 内联编辑，即时 diff 预览
- **可视化 diff 审查**——IDE 原生彩色 diff 体验
- **初学者友好**——图形界面门槛低
- **单文件精细编辑**——光标精确定位 + LSP 诊断

### 两者结合（推荐：大多数专业开发者的做法）

```
日常编码（IDE Agent）
  └── Cursor Tab 补全 + Cmd+K 内联编辑

复杂任务（Everything Agent）
  └── Claude Code / Qwen Code 大规模重构 + 跨系统工作流

自动化（Everything Agent 独占）
  ├── CI/CD: claude --bare -p "..." / codex --full-auto "..."
  ├── 定时: /schedule cron "0 9 * * 1-5" 每工作日审查 PR
  └── 远程: Channels + Telegram 远程触发
```

> **"Everything" 不是取代 IDE，而是覆盖 IDE 无法触达的场景**——CI/CD、远程服务器、跨系统工作流、定时自动化、多代理协作。IDE Agent 在编辑体验（Tab 补全、内联 diff）上仍不可替代。

---

## 八、未来趋势

1. **Everything Agent 扩展边界**：Claude Code 从编码→MCP 万物连接→Channels 消息推送→Schedule 定时→Teammates 多代理——终端成为**通用 AI 操作中心**
2. **IDE Agent 追赶自主性**：Cursor Background Agent（云端异步）和 Cline subagent（并行只读子代理）试图弥补自主性差距
3. **ACP/MCP 协议融合**：Qoder CLI 的 ACP 试图标准化 CLI↔IDE 通信，MCP 已成为外部工具集成的事实标准
4. **Agent 脱离本机**：Cursor Background Agent（云端 PR）、Claude Code Channels（Telegram 远程触发）、Codex Cloud（远程执行）——Agent 越来越不需要在本机运行
5. **一个终端 = 一个 AI 团队**：Claude Code Teammates 让一个终端窗口同时运行多个 AI 代理协作，这是 IDE 范式难以复制的
6. **Terminal in IDE 是最佳妥协**：VS Code 集成终端运行 Claude Code / Qwen Code，同时享受 IDE 补全和 Agent 自主性

---

## 证据来源

| Agent | 来源 | 获取方式 |
|------|------|---------|
| Claude Code | 二进制分析 v2.1.84 + `claude --help` | 本地二进制 |
| Cursor | docs/tools/cursor-cli.md | 官方文档 |
| Cline | docs/tools/cline.md | 开源 |
| Continue | docs/tools/continue.md | 开源 |
| Warp | docs/tools/warp.md | 官方文档 |
| Qoder CLI | docs/tools/qoder-cli/01-overview.md | Go 二进制分析 |
| Aider | docs/tools/aider/ | 开源 |
| Qwen Code | docs/tools/qwen-code/ | 源码分析（Gemini CLI 分叉） |
| Codex CLI | docs/tools/codex-cli/ | Rust 二进制分析 |
| Gemini CLI | docs/tools/gemini-cli/ | 源码分析 |
| Copilot CLI | docs/tools/copilot-cli/ | SEA 反编译 |
| Kimi CLI | docs/tools/kimi-cli/ | 源码分析 |
