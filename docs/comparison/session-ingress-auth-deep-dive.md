# Qwen Code 改进建议 — Session Ingress Auth 远程安全认证 (Session Ingress Authentication)

> 核心洞察：当我们把 AI CLI Agent 作为一个简单的本地脚本运行（例如敲击 `qwen-code` 弹出终端界面）时，安全性是由操作系统本身登录的用户隔离保证的。但随着架构升级，很多时候团队会将 Agent 部署到一台具有高算力的公用 GPU 服务器或 CI 跑批机上，通过 `--headless` 或后台守护进程模式，让多个开发者通过浏览器或者手机端远程连接并指挥它。在这种“远程暴露端口”的场景下，如果没有极严密的身份鉴权拦截，任何内网用户（甚至公网黑客）扫描到该端口，都能通过发包命令 Agent 随意窃取或删除你的代码。Claude Code 通过 `Session Ingress Auth` 提供了一套精妙的、甚至可以规避在 `ps aux` 进程列表中泄露 Token 的认证防线；而 Qwen Code 目前在 headless 模式下缺乏这种工业级的准入防御。
>
> 返回 [改进建议总览](./qwen-code-improvement-report.md)

## 一、裸奔的后台进程带来的毁灭性威胁

### 1. Qwen Code 现状：门户大开的 Headless
如果 Qwen Code 提供了一个暴露 WebSocket 或 HTTP 接口的 `--headless` 后台模式：
- **痛点一（零认证越权）**：默认情况下，只要知道这台机器的 IP 和对应端口，内网里的任何人都能像操作自己电脑一样操作你的项目工作区。他们可以下达类似 `bash: "cat .env"` 或者 `bash: "rm -rf ./"` 的指令，实现极其轻易的提权（Privilege Escalation）。
- **痛点二（命令行传参的安全隐患）**：如果我们只是粗暴地加上一个参数 `qwen-code --headless --token=my_secret_123`，懂行的黑客甚至不需要连接端口。只要你俩在一台共享 Linux 服务器上，他只要敲一下 `ps aux | grep qwen`，你的高权限明文密码就会直接在他的控制台上暴露无遗。

### 2. Claude Code 解决方案：隐形令牌与 Bearer 铁闸
在 Claude Code 的网络和会话准入层，他们采用了企业级的防线设计。

#### 机制一：安全传递的 Ingress Token (File Descriptor Bypass)
为了解决 `ps aux` 导致的命令行参数泄露，Claude Code 支持一种黑客极客常用的高级技巧——**通过文件描述符（FD）传递机密**。
启动时，父进程并不把密码写在字符串里，而是：
```bash
# Token 通过文件描述符 3 秘密传入
qwen-code --headless --ingress-token-fd 3 3<<<"my_super_secret_token"
```
Node.js 进程启动后，会在内部悄无声息地读取文件描述符 3 里的字符串，作为验证所有外部请求的终极密码。除了启动者自己，任何外人都无法从进程表里窥探到这个密码的蛛丝马迹。

#### 机制二：全链路 Bearer Token 拦截
在底层的 HTTP / WebSocket 监听器上，挂载了一道死板的中间件（Middleware）。
每一个从外部打进来的请求，都必须在其请求头（Headers）中包含：
`Authorization: Bearer <token>`
只要字符串对不上启动时传入的那把钥匙，系统在第一微秒就会丢弃该包，甚至不让它触碰到任何解析逻辑，直接返回 `401 Unauthorized`，保证沙盒绝对的纯洁性。

#### 机制三：Well-known Token 文件兜底
对于那些搞不懂文件描述符的高级看客，系统也提供了一种基于物理硬盘权限的退阶方案：将 Token 自动生成并写入一个受到 `chmod 600` 强保护的临时隐藏文件（如 `.qwen/.session_token`）。只有拥有文件读取权限的同一登录用户才能通过读取这个文件来获得连接资格。

## 二、Qwen Code 的改进路径 (P2 优先级)

随着 Agent 向服务端和云原生演进，建立连接准入机制是不可逾越的安全合规红线。

### 阶段 1：开发鉴权中间件 (Ingress Middleware)
1. 在 `packages/cli/src/server/`（或负责 headless 端口监听的网络层模块）中。
2. 增加对传入请求 HTTP Headers 的 `Authorization` 字段拦截与比对。

### 阶段 2：支持安全的 Token 注入方式
修改 CLI 的启动参数解析（如使用 `commander` 或 `yargs`）：
- 增加 `--ingress-token-fd <number>` 参数，通过 `fs.readFileSync(Number(fd), 'utf8')` 提取密码。
- 增加 `--ingress-token-file <path>` 参数。
如果用户使用了极度危险的 `--ingress-token <string>`，在终端打出红色警告，提示其尽快更换为更安全的传入方式以防被 `ps` 抓取。

### 阶段 3：跨端客户端（Remote Bridge）适配
当我们未来开发了手机端或者浏览器端的 [Remote Control Bridge](./remote-control-bridge-deep-dive.md) 配合连接后台时，在这个 Client 工具的初始化配置里，必须加上 Token 字段的填写支持，使其能在每次握手中合法携带通行证。

## 三、改进收益评估
- **实现成本**：小到中等。属于经典的 Web 后端鉴权拦截逻辑，结合特殊的 Node.js 进程间参数传递技巧，代码量 200 行以内。
- **直接收益**：
  1. **填补高危的内网安全漏洞**：让“公用服务器挂后台 Agent”从一个极高风险的黑客实验，变成了完全符合企业合规要求、防旁路窃听的标准部署方案。
  2. **为多人协作基建铺路**：一旦有了可靠的 Token 隔离机制，未来甚至可以进化为“多 Token 多租户”，让一个高配 GPU 上的 Agent 为整个开发团队的不同人员安全地服务。