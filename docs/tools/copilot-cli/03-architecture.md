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

**code-review.agent.yaml**（代码审查专用）：
- 模型：`claude-sonnet-4.5`，工具：`*`（全部）
- 只报告 Bug、安全问题、逻辑错误（高信噪比）
- **明确禁止修改代码**
- 输出带严重级别的结构化问题报告

**explore.agent.yaml**（快速探索）：
- 模型：`claude-haiku-4.5`，工具：仅 `grep, glob, view, lsp`（只读）
- 回答控制在 300 字以内
- 强调并行工具调用以提速

**task.agent.yaml**（命令执行）：
- 模型：`claude-haiku-4.5`，工具：`*`（全部）
- 运行测试、构建、lint、格式化
- 成功时简短输出，失败时完整输出

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
