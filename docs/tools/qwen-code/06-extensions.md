# 6. Qwen Code 扩展系统

> 来源：[官方文档](https://qwenlm.github.io/qwen-code-docs/zh/users/extension/introduction/)

## 概述

Qwen Code 扩展将提示词、MCP 服务器、子智能体、技能和自定义命令打包为统一格式。关键特性：**跨平台兼容**——来自 Gemini CLI 扩展画廊和 Claude Code 应用市场的扩展可直接安装。

## 扩展管理命令

### 交互式（斜杠命令）

| 命令 | 说明 |
|------|------|
| `/extensions` 或 `/extensions manage` | 管理已安装扩展 |
| `/extensions install <source>` | 从 Git URL、本地路径或市场安装 |
| `/extensions explore Gemini` | 打开 Gemini CLI 扩展画廊 |
| `/extensions explore Claude Code` | 打开 Claude Code 应用市场 |

### CLI 命令

```bash
# 安装
qwen extensions install <github-url>
qwen extensions install <owner>/<repo>
qwen extensions install /path/to/local/extension

# Claude Code 市场
qwen extensions install <marketplace-name>
qwen extensions install <marketplace-name>:<plugin-name>

# 卸载
qwen extensions uninstall <extension-name>

# 禁用/启用
qwen extensions disable <name>                    # 用户级
qwen extensions disable <name> --scope=workspace   # 仅当前项目
qwen extensions enable <name>

# 更新
qwen extensions update <name>
qwen extensions update --all

# 设置管理
qwen extensions settings set <ext> <key> [--scope user|workspace]
qwen extensions settings list <ext>
qwen extensions settings show <ext> <key>
qwen extensions settings unset <ext> <key>
```

## 跨平台安装

### Claude Code 插件

```bash
qwen extensions install <marketplace-github-url>
# 例如：
qwen extensions install f/awesome-chatgpt-prompts:prompts.chat
```

安装过程自动转换：
- `claude-plugin.json` → `qwen-extension.json`
- Agent 配置 → Qwen 子 Agent 格式
- Skill 配置 → Qwen Skill 格式
- 工具映射自动处理

### Gemini CLI 扩展

```bash
qwen extensions install <gemini-extension-github-url>
```

安装过程自动转换：
- `gemini-extension.json` → `qwen-extension.json`
- TOML 命令文件 → Markdown 格式
- MCP 服务器、上下文文件、设置均保留

## 扩展结构

```
~/.qwen/extensions/my-extension/
├── qwen-extension.json        # 扩展元数据（必须）
├── QWEN.md                    # 上下文文件（可选，自动加载）
├── commands/                  # 自定义命令（.md 文件）
│   ├── deploy.md
│   └── gcs/
│       └── sync.md            # → 注册为 /gcs:sync
├── skills/                    # 自定义技能
│   └── pdf-processor/
│       └── SKILL.md
└── agents/                    # 自定义子智能体（.yaml 或 .md）
    └── testing-expert.yaml
```

### qwen-extension.json

```json
{
  "name": "my-extension",
  "version": "1.0.0",
  "mcpServers": {
    "my-server": {
      "command": "node",
      "args": ["my-server.js"]
    }
  },
  "contextFileName": "QWEN.md",
  "commands": "commands",
  "skills": "skills",
  "agents": "agents",
  "settings": [
    {
      "name": "API Key",
      "description": "服务所需的 API 密钥",
      "envVar": "MY_API_KEY",
      "sensitive": true
    }
  ]
}
```

### 变量替换

| 变量 | 说明 |
|------|------|
| `${extensionPath}` | 扩展完整路径 |
| `${workspacePath}` | 当前工作区路径 |
| `${/}` 或 `${pathSeparator}` | 路径分隔符 |

## 命令冲突解决

扩展命令优先级最低：
- **无冲突**：使用自然名称（如 `/deploy`）
- **与用户/项目命令冲突**：添加扩展前缀（如 `/gcp.deploy`）

## 设置作用域

扩展设置支持两级：
- **用户级**（默认）：`~/.qwen/.env`，所有项目生效
- **工作区级**：`.qwen/.env`，仅当前项目，优先级更高
