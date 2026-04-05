# Qwen Code 改进建议 — 远程环境设置 (Remote CCR Environment Setup)

> 核心洞察：在前文我们探讨了利用 `/ultraplan` 将极其沉重的架构推理任务发射到云端的 [CCR (Cloud Compute Runtime)](./ultraplan-remote-planning-deep-dive.md) 以实现端云协同。但这种重量级特性绝非一蹴而就——它需要一套复杂的环境搭建和鉴权机制。Claude Code 专门为此开发了交互式的 `/remote-setup` 向导，负责连接本地终端与企业 VPC 内的远程执行池；而 Qwen Code 的相关配置（如果有的话）通常只能通过极其硬核的环境变量手动注入，这对推广进阶用法是极大的阻碍。
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md)

## 一、为什么远程环境需要向导？

### 1. Qwen Code 现状：复杂的底层配置墙
如果我们为 Qwen Code 设计了连接远程“阿里云算力节点”或“企业自建 Agent Worker 池”的能力：
- **痛点**：对于普通开发者，配置远程端点需要填写 `REMOTE_HOST`, `WS_PORT`, `TLS_CERT`, `AUTH_TOKEN` 等七八个环境变量，或者在一个深层 JSON 配置文件里手打。如果中间漏配了一个证书路径，连接直接超时失败。极高的部署门槛将这一企业级能力变成了只有核心开发者才懂的“隐藏特性”。

### 2. Claude Code 解决方案：保姆式的 TUI Setup
在 Claude Code 的 `commands/remote-setup/remote-setup.tsx` 中，他们针对连接企业级的 CCR 环境做了一个保姆级别的交互面板。

#### 机制一：多维度探测与指引
输入 `/remote-setup` 后，向导会：
1. 先检查当前账号的企业组织（Org/Team）权限，判定是否拥有 CCR 远程沙箱使用资格。
2. 让你选择远程计算群集的区域（Region）。
3. 如果是私有化部署，提供文本框安全地录入凭证 Token（并进行掩码显示 `*****`）。

#### 机制二：自动握手验证 (Connection Doctor)
最精妙的是，配完环境后，向导不会直接丢给你一句“配置成功”。
它会在后台立刻发起一次隐形的 Dummy 任务（探活）：
```typescript
try {
  await testRemoteConnection({ host, token });
  print("✅ Successfully established bi-directional channel with Cloud Sandbox!");
} catch (e) {
  print("❌ Connection failed. Check your firewall settings at port 443.");
}
```
这种立刻获得正向反馈（Instant Feedback）的设计，极大地降低了部署实施的挫败感。

## 二、Qwen Code 的改进路径 (P3 优先级)

作为将来推广通义千问企业版算力和云端 IDE 协同的必备前置基建。

### 阶段 1：确立 Remote 核心配置模型
在 `packages/core/src/config/` 定义一套 `RemoteEnvironmentConfig` 接口，包含 `endpointUrl`, `region`, `accessToken`, `sandboxType` 等字段。

### 阶段 2：开发交互式向导命令
1. 新建 `commands/remote-setup.ts`。
2. 利用 React Ink 的表单组件（如 `ink-text-input`），分步收集上述配置。
3. 增加鉴权校验拦截：收集完配置后，调用平台提供的 `/api/ping`。

### 阶段 3：深度整合主干逻辑
将这套配置持久化到 `.qwen/config.json` 中。
如果探测到了有效的 `remote` 配置，在启动 Qwen Code 时可以在 ASCII Logo 下方亮起一行绿色标签：`[Connected to Qwen Cloud Sandbox]`。

## 三、改进收益评估
- **实现成本**：低到中等。属于周边配套设施，工作量集中在 TUI 表单的绘制和测试联通性上。
- **直接收益**：
  1. **打通商业化变现入口**：有了极其丝滑的连接体验，能让更多的开源用户轻松地转变为使用付费云端算力的高净值客户。
  2. **消除联调噩梦**：降低了将 AI 助手深度整合到企业内部复杂网络环境中的技术成本。