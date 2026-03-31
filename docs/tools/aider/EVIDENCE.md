# Aider 源码深度分析证据

## 基本信息
- 仓库: Aider-AI/aider, GPL-3.0, Python, 43k+ stars
- 版本: latest (源码分析 commands.py 1712 行)

## 遥测系统（源码: aider/analytics.py）

### PostHog（活跃）
- API key: `phc_99T7muzafUMMZX15H8XePbMSreEUzahHbtWjy3l5Qbv`
- 端点: `https://us.i.posthog.com`
- 发送方式: `ph.capture(distinct_id, event, properties)`

### Mixpanel（代码存在但已禁用）
- Token: `6da9a43058a5d1b9f3353153921fb04d`
- 初始化行被注释: `# self.mp = Mixpanel(mixpanel_project_token)`

### 用户标识
- 随机 UUID v4，首次运行生成
- 持久化: `~/.aider/analytics.json`
- 字段: `uuid`, `permanently_disable`, `asked_opt_in`

### 采样率
- `PERCENT = 10` — 仅 10% 用户被询问 opt-in
- `is_uuid_in_percentage()` 检查 UUID 前 6 位 hex 是否在前 10%

### 采集数据（get_system_info() super_properties）
| 字段 | 内容 |
|------|------|
| python_version | Python 版本 |
| os_platform | 操作系统类型 |
| os_release | 内核/OS release |
| machine | CPU 架构 |
| aider_version | Aider 版本 |

### 每事件属性
- main_model, weak_model, editor_model
- 未知模型名自动 redact: `_redact_model_name()` → `provider/REDACTED`

### 不采集
- MAC 地址 ✗
- 主机名 ✗
- IP 地址 ✗
- 文件内容/代码 ✗
- git 数据 ✗
- 环境变量 ✗（analytics.py 中无 os.environ 调用）

### 隐私控制
1. 默认关闭（opt-in）
2. `--analytics false` CLI 参数
3. `permanently_disable: true` 永久禁用
4. 仅 10% 被采样
5. 错误时静默禁用（graceful failure）

## 安全系统
- **无**安全分类器/监控系统
- **无**命令阻止机制
- **无**沙箱
- **无**环境变量清洗
- 所有操作直接执行，依赖 Git undo 作为安全网

## Git 集成（源码: aider/repo.py, 622 行）
- auto_commit: 每次 AI 编辑自动提交
- 归因: Co-authored-by + author/committer 名修改（3 独立标志）
- /undo 安全检查: 仅撤销 aider 创建的提交，检查 aider_commit_hashes

## 仓库地图（源码: aider/repomap.py, 867 行）
- Tree-sitter AST 解析（30+ 语言）
- NetworkX PageRank 排名
- SQLite diskcache 缓存（CACHE_VERSION=4）
- 权重: chat files ×50, mentioned ×10, snake/camelCase ×10, private ×0.1

## 压缩系统（源码: aider/history.py, 143 行）
- ChatSummary: max_tokens=1024
- 递归分割摘要（最多 3 层深度）
- 后台线程执行，不阻塞用户
- 摘要前缀: "I spoke to you previously about a number of things.\n"

## 命令系统（源码: aider/commands.py, 1712 行）
- 42 个斜杠命令，cmd_ 前缀自动发现
- SwitchCoder 异常模式切换
- 15 种 Coder 类型（aider/coders/ 目录）
- ! 前缀别名 → /run

来源: GitHub 源码直接分析 (gh api)
