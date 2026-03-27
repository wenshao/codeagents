# 41. CLI Agent vs IDE Agent：两种范式的深度对比

> 终端原生 Agent 和 IDE 内嵌 Agent 是 AI 编程代理的两大范式。它们不是"谁取代谁"，而是各有不可替代的优势场景。

## 范式总览

| 维度 | CLI Agent（终端原生） | IDE Agent（编辑器内嵌） | 混合型 |
|------|---------------------|----------------------|--------|
| **代表** | Claude Code、Aider、Codex CLI、Gemini CLI、Qwen Code、Kimi CLI、Copilot CLI | Cursor、Cline、Continue | Warp（终端替代）、Qoder CLI（ACP 协议） |
| **运行环境** | 终端进程 | IDE 扩展/内嵌 | 终端 + IDE 桥接 |
| **交互模式** | 对话式（prompt → response） | 内联式（补全 + diff 预览 + 侧边栏） | 混合 |
| **上下文来源** | 显式工具调用（Read/Grep/Glob） | IDE 自动提供（打开文件、光标、诊断） | 两者兼有 |
| **自主性** | **高**（长链自主操作） | 中（需用户确认每步） | 高 |
| **启动速度** | 50ms~1.5s | 3~10s（Electron） | 亚秒级（Rust） |
| **CI/CD** | **原生支持** | 通常不支持 | 部分支持 |

---

## 一、上下文获取：显式 vs 隐式

这是两种范式最根本的差异。

### CLI Agent：通过工具调用主动获取

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

### 实际影响

| 场景 | CLI Agent 效率 | IDE Agent 效率 |
|------|-------------|--------------|
| 修复**当前文件**的 Bug | 低（需 Read 整个文件） | **高**（IDE 已加载） |
| 跨 10 个文件的重构 | **高**（自主导航） | 低（需手动打开文件） |
| 理解**未知代码库** | **高**（Grep/Glob 搜索） | 低（依赖用户导航） |
| 根据**光标位置**补全 | 不支持 | **极高**（Tab 补全） |

---

## 二、交互模式：对话 vs 内联

### CLI Agent：对话驱动

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

### CLI Agent

| Agent | 语言 | 启动 | 自主链长度 | CI 支持 | 独特能力 |
|-------|------|------|----------|---------|---------|
| **Claude Code** | Rust | **50ms** | 长（maxTurns 可配） | **`--bare` + stream-json** | 24 Hook + Prompt Hook + Channels |
| **Aider** | Python | ~1s | 3 次反射 | `--message` | 14 编辑格式 + Git 自动提交 |
| **Codex CLI** | Rust | 76ms | 可配置 | 5 级审批 + Cloud | 三平台 OS 沙箱 |
| **Gemini CLI** | TS | 1.5s | 100 轮 | TTY 自动检测 | 8 策略模型路由 |
| **Qwen Code** | TS | 608ms | 100 轮 | `--non-interactive` | Arena 多模型竞争 |
| **Copilot CLI** | Shell | 72ms | 可配置 | `-p` + Autopilot | 67 GitHub 工具 |
| **Kimi CLI** | Python | ~1s | 100 步 | — | Wire 协议 + D-Mail |

### IDE Agent

| Agent | 平台 | 代码补全 | 内联编辑 | 多文件编排 | 后台执行 | 独特能力 |
|-------|------|---------|---------|-----------|---------|---------|
| **Cursor** | VS Code 深度分叉 | **Tab**（最强） | **Cmd+K** | Composer | **Background Agent（云端）** | Rules(.mdc) + @ 引用 |
| **Cline** | VS Code 扩展 | ✗ | WebView UI | ✓（subagent） | ✗ | **Git Checkpoint** + 24+ 工具 |
| **Continue** | VS Code + JetBrains | **Tab** | ✗ | ✓ | ✗ | **PR Checks**（CI 审查规则） |

### 混合型

| Agent | 类型 | 终端能力 | IDE 集成 | 独特定位 |
|-------|------|---------|---------|---------|
| **Warp** | 终端替代品 | GPU 渲染 + 块结构 | — | Oz Agent + Warp Drive 团队协作 |
| **Qoder CLI** | CLI + ACP | Go 原生 43MB | **ACP 协议**（Zed/VS Code/JetBrains） | Quest 模式 + Experts 团队 |

---

## 四、安全模型差异

| 维度 | CLI Agent | IDE Agent |
|------|-----------|-----------|
| **文件访问** | 工具权限控制（deny/ask/allow） | IDE workspace 范围 |
| **命令执行** | 沙箱隔离（Codex CLI 三平台 OS 沙箱） | 通常无沙箱 |
| **网络访问** | 可禁止（`--bare`、沙箱） | IDE 环境不限制 |
| **审批流程** | 24 Hook 事件 + TOML 策略 | 弹窗确认（简单） |
| **企业管控** | managed-settings 远程下发 | Cursor Business 管理面板 |

> CLI Agent 的安全模型显著更成熟——沙箱隔离、28 BLOCK 规则、策略引擎是 IDE Agent 没有的。

---

## 五、Git 集成差异

| 能力 | CLI Agent | IDE Agent |
|------|-----------|-----------|
| **自动提交** | Aider（每次编辑自动 commit） | ✗（需手动） |
| **检查点回退** | Claude Code（Esc）、Gemini CLI（/rewind 三选项） | Cline（Git Checkpoint 每步快照） |
| **Worktree 隔离** | Claude Code Teammates（独立 worktree） | Cursor Background Agent（云端隔离） |
| **归因系统** | Aider（Co-authored-by 三标志） | ✗ |
| **Git 命令** | Aider（/commit /undo /diff /git） | IDE Git 面板 |

---

## 六、远程开发

| 场景 | CLI Agent | IDE Agent |
|------|-----------|-----------|
| **SSH 到服务器** | 原生（直接 `ssh server && claude`） | 需 Remote SSH 扩展 |
| **Docker 容器** | 原生（`docker exec -it container claude`） | 需 Dev Containers 扩展 |
| **CI/CD 管道** | **原生**（`claude --bare -p "..."`） | 不支持（需要 GUI） |
| **GitHub Actions** | ✓（Codex Cloud、SWE-agent） | ✗ |
| **无头服务器** | ✓ | ✗（需要显示服务器） |

> **关键差异**：CLI Agent 在无 GUI 环境中完全可用，IDE Agent 本质上依赖图形界面。

---

## 七、选型决策

### 选 CLI Agent 的场景

- **大规模代码库探索**——Agent 自主搜索，无需手动打开文件
- **CI/CD 自动化**——管道中无头运行
- **远程服务器开发**——SSH 直接使用
- **多文件批量重构**——一次 prompt 修改数十个文件
- **安全敏感场景**——需要沙箱隔离、策略引擎
- **团队工作流**——Teammates 多代理协作、Hook 自动化

### 选 IDE Agent 的场景

- **日常编码补全**——Tab 逐行补全是最高频需求
- **当前文件快速修复**——Cmd+K 内联编辑，即时 diff
- **可视化 diff 审查**——IDE 原生彩色 diff 体验
- **初学者友好**——图形界面门槛低
- **单文件精细编辑**——光标精确定位

### 两者结合（推荐）

```
日常编码（IDE Agent）
  └── Cursor Tab 补全 + Cmd+K 内联编辑

复杂任务（CLI Agent）
  └── Claude Code / Qwen Code 大规模重构 + 自动化

CI/CD（CLI Agent 独占）
  └── claude --bare -p "..." / codex --full-auto "..."
```

> 多数专业开发者会同时使用两者——IDE Agent 用于高频小操作（补全、单文件修复），CLI Agent 用于低频大操作（重构、审查、自动化）。

---

## 八、未来趋势

1. **融合加速**：Cursor 的 Background Agent（云端 CLI 能力）和 Cline（VS Code + CLI 双模式）正在模糊边界
2. **ACP 协议**：Qoder CLI 的 Agent Communication Protocol 试图标准化 CLI↔IDE 通信
3. **MCP 桥接**：CLI Agent 通过 MCP 服务器接入 IDE 能力（LSP 诊断、符号索引）
4. **Terminal in IDE**：VS Code 集成终端让 CLI Agent 在 IDE 内运行，获得两者优势
5. **远程 Agent**：Cursor Background Agent 和 Claude Code Channels 都朝"Agent 不在本机运行"方向发展

---

## 证据来源

| Agent | 来源 | 获取方式 |
|------|------|---------|
| Claude Code | 二进制分析 v2.1.84 + `claude --help` | 本地二进制 |
| Cursor | docs/tools/cursor-cli.md（476 行） | 官方文档 |
| Cline | docs/tools/cline.md（151 行） | 开源 |
| Continue | docs/tools/continue.md（190 行） | 开源 |
| Warp | docs/tools/warp.md（382 行） | 官方文档 |
| Qoder CLI | docs/tools/qoder-cli/01-overview.md | Go 二进制分析 |
| Aider | docs/tools/aider/ | 开源 |
| Qwen Code | cli.js 二进制 strings v0.13.0 | npm 包分析 |
