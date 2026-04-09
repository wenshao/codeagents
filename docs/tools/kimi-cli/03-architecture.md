# 3. Kimi CLI 技术架构——开发者参考

> 本文分析 Kimi CLI 的核心架构：KimiSoul 代理循环、kosong 多提供商 LLM 抽象、Wire 事件流协议、子代理系统、YAML 代理定义、插件/Skill 双生态。这些模式展示了如何用 Python 生态复现 Claude Code 的架构理念，并在多客户端和声明式配置上做出超越。
>
> **Qwen Code 对标**：Wire 事件流（多客户端架构）、kosong LLM 抽象（多提供商策略）、YAML 代理定义（声明式 vs 硬编码）、插件子进程隔离

## 为什么 Python 重写值得研究

Kimi CLI 证明了 Claude Code 的核心架构模式可以跨语言复现。但更重要的是，Python 生态带来了 Claude Code 的 TypeScript/Bun 栈难以实现的能力：

| 能力 | Python 生态优势 | TypeScript 对应 |
|------|----------------|----------------|
| 类型安全配置 | Pydantic 2（运行时校验 + 序列化） | Zod（仅校验，不含序列化） |
| 模板系统 | Jinja2（成熟的模板引擎） | 字符串拼接或 Handlebars |
| Web 服务 | FastAPI（自动 OpenAPI 文档） | Express/Fastify |
| 内容提取 | trafilatura + lxml | 需要额外依赖 |
| 包管理 | uv（极快的 Python 包管理） | npm/pnpm |

代价是启动速度（Python 解释器 vs Bun compile）和单文件分发（PyInstaller 二进制 > 200MB vs Bun 单文件 ~227MB 但启动更快）。

---

## 1. 技术栈

| 组件 | 技术选型 | Claude Code 对应 | 开发者启示 |
|------|---------|-----------------|-----------|
| **语言** | Python 3.12+（3.14 推荐） | TypeScript (Bun) | Python 的 asyncio 足以支撑代理循环 |
| **CLI 框架** | Typer（懒加载子命令） | 自建 CLI 解析 | Typer 的类型推导减少样板代码 |
| **TUI** | prompt-toolkit + Rich | Ink (React for CLI) | prompt-toolkit 更成熟，Rich 渲染质量极高 |
| **Web** | FastAPI + Uvicorn | 无内置 | 内置 Web UI 是差异化优势 |
| **LLM 抽象** | kosong（自研多提供商） | 直接调用 Anthropic API | 自研抽象层是多提供商必要投资 |
| **MCP SDK** | fastmcp（stdio + HTTP） | 官方 MCP SDK | 两者功能等价 |
| **ACP SDK** | agent-client-protocol 0.8.0 | 无 | ACP 是 IDE 集成的新标准 |
| **配置** | Pydantic 2 + TOML | 5 层 JSON settings | TOML 对人类更友好 |
| **模板** | Jinja2 | 字符串拼接 | Jinja2 提示词模板更可维护 |
| **搜索后端** | ripgrepy | ripgrep (直接调用) | 两者最终都调用 rg 二进制 |
| **打包** | uv + PyInstaller | Bun compile → Rust | uv 极快，PyInstaller 启动慢但可接受 |
| **代码质量** | ruff + pyright + ty | ESLint + TypeScript | ruff 是 Python 生态中最快的 linter |

---

## 2. 核心代理循环（KimiSoul）

```
KimiSoul.step() [单步执行]
    │
    ├── 动态提示注入 (dynamic_injection.py)
    │     └── plan_mode / yolo_mode / 通知 → 系统消息
    │
    ├── LLM 调用 (kosong.step)
    │     ├── 请求构建：系统提示(Jinja2) + 历史消息 + 工具 Schema
    │     ├── 多提供商路由：Kimi / OpenAI / Anthropic / Gemini / Vertex
    │     └── 流式响应接收
    │
    ├── 工具调用解析
    │     └── 从 LLM 响应中提取工具调用
    │
    ├── 审批检查 (approval.py)
    │     ├── YOLO 模式 → 自动通过
    │     ├── 会话级自动审批 → 检查 approve_for_session 集合
    │     └── 逐次确认 → 通过 Wire 协议下发 ApprovalRequest
    │
    ├── 工具执行 (内置 17+ 工具 / MCP / 插件)
    │     └── 结果写入上下文
    │
    ├── 上下文管理 (compaction.py)
    │     └── 使用率 ≥ 85% → LLM 摘要压缩
    │
    ├── Wire 事件广播
    │     └── TurnBegin → StepBegin → ToolCall → ToolResult → TurnEnd
    │
    └── 循环控制
          ├── max_steps_per_turn = 100
          ├── max_retries_per_step = 3
          └── end_turn 信号 → 结束
```

### 与 Claude Code QueryEngine 的对比

| 维度 | Kimi CLI (KimiSoul) | Claude Code (QueryEngine) |
|------|---------------------|---------------------------|
| 工具执行 | 解析完成后顺序执行 | StreamingToolExecutor（流式解析边执行） |
| 上下文压缩 | 单层 LLM 摘要 @ 85% | 5 层渐进压缩（cache_edits → 全量 compact） |
| 提示注入 | dynamic_injection.py 统一入口 | buildSystemPrompt() 硬编码 |
| 步数限制 | max_steps_per_turn=100 | 无硬限制（依赖 token 用量） |
| 事件广播 | Wire 协议统一 | React 状态 + Bridge（后追加） |
| 模型回退 | 无 | 模型 fallback + 529 降级 |

**Qwen Code 对标**：Kimi CLI 的 `dynamic_injection.py` 是一个值得借鉴的模式——所有动态提示注入（plan 状态、yolo 状态、后台任务通知等）通过单一入口管理，避免散落在代码各处。Claude Code 的硬编码注入更高效但更难维护。

---

## 3. kosong — 多提供商 LLM 抽象

kosong 是 Kimi CLI 的自研 LLM 抽象层，作为 monorepo 中的独立包。

### 支持的提供商

| 提供商 | API 模式 | 特殊处理 |
|--------|---------|---------|
| **Kimi** | Moonshot API | 默认，集成搜索/抓取服务 |
| **OpenAI** | Legacy + Responses | 两种 API 模式并存 |
| **Anthropic** | Claude API | session_id 作为 user_id |
| **Google Gemini** | GenAI API | 标准适配 |
| **Vertex AI** | Vertex AI API | 企业级，独立 provider type |

### 模型能力标记

```python
# 源码: config.py (模型配置)
capabilities = ["image_in", "video_in", "thinking", "always_thinking"]
```

- `image_in` / `video_in`：多模态输入支持
- `thinking`：可选深度推理模式
- `always_thinking`：始终启用深度推理

**Qwen Code 对标**：kosong 的能力标记系统让同一套代理逻辑适配不同模型特性——如果模型不支持 `thinking`，代理循环自动跳过思维模式相关逻辑。Qwen Code 如果要支持非 Qwen 模型，需要类似的能力声明机制。

### 环境变量覆盖

```bash
KIMI_BASE_URL, KIMI_API_KEY, KIMI_MODEL_NAME, KIMI_MODEL_MAX_CONTEXT_SIZE
OPENAI_BASE_URL, OPENAI_API_KEY
ANTHROPIC_API_KEY
# 每个提供商都有对应的环境变量
```

---

## 4. Wire 事件流协议（v1.6）

Wire 协议是 Kimi CLI 多客户端架构的核心抽象——所有代理事件通过统一的事件流广播，任何客户端只需实现事件消费者即可。

### 事件类型（30+）

| 分类 | 事件 | 说明 |
|------|------|------|
| **控制流** | TurnBegin, TurnEnd, StepBegin, StepInterrupted, SteerInput | 代理回合和步骤生命周期 |
| **内容** | ContentPart | 文本/思考/图片/音频/视频 |
| **工具** | ToolCall, ToolCallPart, ToolResult | 工具调用和结果 |
| **状态** | StatusUpdate | 上下文使用率、token、plan_mode、MCP |
| **交互** | ApprovalRequest/Response, QuestionRequest/Response | 审批和结构化问题 |
| **压缩/MCP** | CompactionBegin/End, MCPLoadingBegin/End, MCPServerSnapshot | 压缩和 MCP 状态 |
| **子代理** | SubagentEvent | 嵌套子代理事件（含 agent_id, subagent_type） |
| **通知** | Notification | 后台任务完成等通知 |

### 多客户端架构

```
                    ┌─ TUI Shell (prompt-toolkit + Rich)
                    │
KimiSoul ── Wire ──├─ Web UI (FastAPI + React + WebSocket)
  事件流            │
                    ├─ IDE (ACP JSON-RPC over stdio)
                    │
                    └─ Wire stdio (自定义 UI)
```

**Qwen Code 对标**：Wire 协议的核心优势是**关注点分离**——代理逻辑不关心前端是终端、浏览器还是 IDE。Claude Code 的 Bridge 模式（WebSocket/SSE）是后来追加的，架构上不如 Wire 清晰。如果 Qwen Code 计划支持 Web UI 或 IDE 集成，从一开始就设计统一的事件流协议比事后补丁更好。

### Wire JSONL 持久化

会话数据以 Wire JSONL 格式存储，支持：
- 导出/导入（`/export`、`/import` 命令）
- 会话恢复（`/sessions` 列出并恢复）
- 事件重放

---

## 5. 多代理系统

### 代理类型

| 代理 | 类型 | 工具权限 | 用途 |
|------|------|---------|------|
| **default** | 主代理 | 全部工具 + Agent + AskUserQuestion + EnterPlanMode | 完整能力 |
| **coder** | 子代理 | Shell + 文件读写 + 搜索 + Web | 软件工程，读写执行 |
| **explore** | 子代理 | Shell + 文件只读 + 搜索 + Web | 代码探索，不修改文件 |
| **plan** | 子代理 | 文件只读 + 搜索 + Web（无 Shell） | 架构规划，纯分析 |
| **okabe** | 实验代理 | default + SendDMail | D-Mail 时间回溯 |

### YAML 声明式代理定义

```yaml
# 源码: agents/default/coder.yaml（示例结构）
name: coder
description: Software engineering subagent
system_prompt: system.md    # Jinja2 模板
tools:
  - Shell
  - ReadFile
  - WriteFile
  - StrReplaceFile
  - Glob
  - Grep
  - SearchWeb
  - FetchURL
```

**Qwen Code 对标**：YAML 定义 vs 硬编码是 Kimi CLI 相对于 Claude Code 的重要架构改进。用户可以在 YAML 文件中自定义代理——修改工具策略、覆盖系统提示、指定模型——无需修改 Python 代码。这对企业用户（需要定制化代理行为）尤为重要。

### 子代理生命周期

```
Agent 工具调用
    │
    ├── 子代理类型查找 (LaborMarket 注册表)
    │     └── registry.py: AgentTypeDefinition → ToolPolicy
    │
    ├── 实例创建或恢复
    │     └── store.py: 按 agent_id 持久化
    │
    ├── 执行模式
    │     ├── 前台：父代理等待结果
    │     └── 后台：立即返回，完成后通过 Notification 通知
    │
    └── 结果处理
          └── 自动摘要，父代理只看到结果概要
```

### 与 Claude Code 多 Agent 对比

| 维度 | Kimi CLI | Claude Code |
|------|----------|-------------|
| 代理定义 | YAML + Jinja2（声明式） | TypeScript 硬编码 |
| 角色分化 | coder/explore/plan（工具权限递减） | Leader-Worker（统一工具集） |
| 后台执行 | 原生支持 + 任务管理 TUI | Swarm 三后端 |
| 实例持久化 | store.py 按 agent_id | Subagent fork（进程级） |
| 结果汇总 | 自动摘要 | Leader 聚合 |

---

## 6. 权限与审批系统

```
审批模式（优先级递减）：
  ① YOLO 模式 (--yolo / /yolo)     → 自动审批全部操作
  ② 会话级自动审批 (approve_for_session) → 该操作类型不再询问
  ③ 逐次确认 (approve / reject)      → 每次请求用户审批

工具审批策略：
  Shell 工具      → 需要审批（显示命令预览）
  文件写入        → 需要审批（显示 diff 预览）
  文件读取        → 自动允许
  Web 工具        → 自动允许
  MCP 工具        → 需要审批
```

审批请求通过 Wire 协议统一下发，所有客户端（Shell/Web/ACP）共享同一套审批逻辑。拒绝时可附带 feedback 文本引导模型修正。

**Qwen Code 对标**：拒绝+反馈（reject with feedback）是一个精细化设计——用户不仅可以拒绝操作，还可以解释为什么拒绝，引导 AI 下次做出更好的决策。这比简单的 y/n 审批提供了更丰富的人机交互信号。

---

## 7. Skill + 插件双生态

### Skill 系统

**发现路径**（优先级递增）：

1. **内置 Skill**：`src/kimi_cli/skills/`（如 `kimi-cli-help`、`skill-creator`）
2. **用户级 Skill**：`~/.config/agents/skills`、`~/.agents/skills`、`~/.kimi/skills`、`~/.claude/skills`、`~/.codex/skills`
3. **项目级 Skill**：`./.agents/skills`、`./.kimi/skills`、`./.claude/skills`、`./.codex/skills`
4. **插件 Skill**：从已安装插件中发现

**Skill 类型**：
- **标准 Skill**：`SKILL.md` 文件包含指令文本，通过 `/skill:<name>` 加载
- **Flow Skill**：`SKILL.md` 中嵌入 Mermaid/D2 流程图，通过 `/flow:<name>` 执行代理工作流

**Qwen Code 对标**：Kimi CLI 的 Skill 发现路径兼容 Claude Code（`~/.claude/skills`）和 Codex（`~/.codex/skills`），这意味着为 Claude Code 编写的 Skill 可以直接在 Kimi CLI 中使用。这是一个聪明的兼容性策略——利用 Claude Code 的生态为自己引流。

### 插件系统（v1.25.0）

```jsonc
// plugin.json 格式
{
  "name": "my-plugin",
  "version": "1.0.0",
  "tools": [{
    "name": "my-tool",
    "command": ["python", "run.py"],  // 子进程隔离执行
    "parameters": { ... }
  }],
  "inject": {
    "services.moonshot.api_key": "api_key"  // 自动凭证注入
  }
}
```

**关键设计**：
- **子进程隔离**：插件工具在独立子进程中运行，参数通过 stdin JSON 传入，stdout 作为结果
- **凭证注入**：`inject` 声明自动从宿主配置注入 API key 和 base_url（OAuth 令牌实时刷新）
- **monorepo 支持**：`kimi plugin install <git-url> --subpath PATH`

---

## 8. 配置系统

```toml
# ~/.kimi/config.toml

default_model = "kimi-k2.5"
default_thinking = false
default_yolo = false
default_editor = "vim"

[loop_control]
max_steps_per_turn = 100
max_retries_per_step = 3
compaction_trigger_ratio = 0.85
reserved_context_size = 50000

[background]
max_running_tasks = 4
read_max_bytes = 30000
keep_alive_on_exit = false
```

**配置优先级**（低→高）：
1. 默认值
2. 配置文件 `~/.kimi/config.toml`
3. `--config-file PATH` CLI 参数
4. `--config TEXT` CLI 内联 TOML/JSON
5. 环境变量（`KIMI_*`）

**Qwen Code 对标**：5 级配置优先级与 Claude Code 的 5 层 settings 理念一致，但 TOML 格式比 JSON 更适合人工编辑。`loop_control` 中的 `compaction_trigger_ratio`（压缩触发比例）和 `reserved_context_size`（保留上下文大小）可作为 Qwen Code 上下文管理的参考参数。

---

## 9. 多客户端支持

### Web UI

```bash
kimi web                            # 默认 localhost:5494
kimi web --port 8080 --network --auth-token my-secret  # 网络模式 + 认证
```

**功能矩阵**：

| 功能 | 说明 |
|------|------|
| 多会话管理 | 创建/切换/归档/删除/搜索 |
| 实时 WebSocket | Wire 协议事件推送 |
| 审批对话框 | Diff 预览 + approve/reject + feedback |
| 会话 Fork | 从任意回复分叉新会话 |
| @ 文件提及 | 自动补全引用工作区文件 |
| 数学公式 | `$...$` 行内和 `$$...$$` 块级 |
| 安全 | Token 认证、CORS、Origin 验证 |

### ACP IDE 集成

| 编辑器 | 集成方式 |
|--------|---------|
| **VS Code** | 原生扩展（自动安装） |
| **Zed** | 原生 ACP（实时编辑 + agent following） |
| **JetBrains** | ACP Registry (acp.json) |
| **Neovim** | Avante.nvim / CodeCompanion.nvim |

**Qwen Code 对标**：Kimi CLI 在多客户端支持上超越了 Claude Code——内置 Web UI、原生 IDE 集成（4 个编辑器）、Wire 自定义客户端。这是 Wire 事件流架构的直接收益。Qwen Code 如果要做类似的多端覆盖，首先需要定义统一的事件流协议。

---

## 10. 项目演进（2025.09 — 2026.03）

| 阶段 | 时间 | 版本 | 关键里程碑 |
|------|------|------|-----------|
| 早期开发 | 2025-09~11 | v0.8~0.50 | 基础代理循环、TUI Shell、ACP 原型 |
| 基础稳定 | 2025-11~12 | v0.51~0.70 | Shell/CMD 工具、MCP、Wire 重实现 |
| 功能扩展 | 2026-01 | v0.71~0.86 | ACP 文件路由、Skill、Flow Skill、跨平台二进制 |
| **1.0 发布** | 2026-01-27 | **v1.0** | 正式发布、Web UI 首发、login/logout |
| 快速迭代 | 2026-02 | v1.6~1.16 | Web UI 大升级、认证、多目录、外部编辑器 |
| 深度功能 | 2026-03 | v1.19~1.24 | Plan 模式、Steer Input、后台任务、可视化仪表板 |
| **当前** | 2026-03-23 | **v1.25.0** | 插件系统、Agent 工具、统一审批、Wire v1.6 |

六个月内从 v0.8 到 v1.25.0，~110 个版本发布。平均每 1.6 天一个版本——这个迭代速度接近 Claude Code 的发布节奏。

**Qwen Code 对标**：Kimi CLI 的版本演进路径值得作为参考——先做核心循环（3 个月），再做多端支持（2 个月），最后做扩展生态（1 个月）。这个优先级排序（核心 → 多端 → 生态）比试图一次性做完所有功能更务实。
