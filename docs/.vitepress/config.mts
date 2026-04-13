import { defineConfig } from 'vitepress'
import escapeXmlPlugin from './markdown-it-escape-xml'

// https://vitepress.dev/reference/site-config
export default defineConfig({
  base: '/codeagents/',
  lang: 'zh-CN',
  title: 'AI 编程 Code Agent 对比',
  description: '基于源码分析和二进制反编译的 19 款 AI 编程 Code Agent 全面对比',

  rewrites: {
    'tools/README.md': 'tools/index.md',
    'tools/claude-code/README.md': 'tools/claude-code/index.md',
    'tools/copilot-cli/README.md': 'tools/copilot-cli/index.md',
    'tools/codex-cli/README.md': 'tools/codex-cli/index.md',
    'tools/gemini-cli/README.md': 'tools/gemini-cli/index.md',
    'tools/qwen-code/README.md': 'tools/qwen-code/index.md',
    'tools/kimi-cli/README.md': 'tools/kimi-cli/index.md',
    'tools/aider/README.md': 'tools/aider/index.md',
    'tools/opencode/README.md': 'tools/opencode/index.md',
    'tools/goose/README.md': 'tools/goose/index.md',
    'tools/qoder-cli/README.md': 'tools/qoder-cli/index.md',
    'data/README.md': 'data/index.md',
  },

  markdown: {
    html: true,
    config: (md) => {
      md.use(escapeXmlPlugin)
    },
  },

  head: [
    ['link', { rel: 'icon', type: 'image/svg+xml', href: '/logo.svg' }],
  ],

  themeConfig: {
    logo: '/logo.svg',

    nav: [
      { text: '首页', link: '/' },
      { text: '选型速查', link: '/SUMMARY' },
      { text: 'Agent 详情', link: '/tools/' },
      { text: '功能对比', link: '/comparison/features' },
      { text: '使用指南', link: '/guides/getting-started' },
      { text: '外部资源', link: '/resources' },
    ],

    sidebar: {
      '/tools/': [
        {
          text: 'Agent 索引',
          items: [
            { text: '全部 Agent 总览', link: '/tools/' },
          ]
        },
        {
          text: '深度分析',
          collapsed: false,
          items: [
            {
              text: 'Claude Code',
              collapsed: false,
              items: [
                { text: '概览', link: '/tools/claude-code/01-overview' },
                { text: '命令', link: '/tools/claude-code/02-commands' },
                { text: '架构', link: '/tools/claude-code/03-architecture' },
                { text: '工具', link: '/tools/claude-code/04-tools' },
                { text: '技能系统', link: '/tools/claude-code/05-skills' },
                { text: '设置', link: '/tools/claude-code/06-settings' },
                { text: '会话管理', link: '/tools/claude-code/07-session' },
                { text: '远程控制', link: '/tools/claude-code/08-remote-control' },
                { text: '多代理', link: '/tools/claude-code/09-multi-agent' },
                { text: 'Prompt 建议', link: '/tools/claude-code/10-prompt-suggestions' },
                { text: '终端渲染', link: '/tools/claude-code/11-terminal-rendering' },
              ]
            },
            {
              text: 'Copilot CLI',
              collapsed: false,
              items: [
                { text: '概览', link: '/tools/copilot-cli/01-overview' },
                { text: '命令', link: '/tools/copilot-cli/02-commands' },
                { text: '架构', link: '/tools/copilot-cli/03-architecture' },
              ]
            },
            {
              text: 'Codex CLI',
              collapsed: false,
              items: [
                { text: '概览', link: '/tools/codex-cli/01-overview' },
                { text: '命令', link: '/tools/codex-cli/02-commands' },
                { text: '架构', link: '/tools/codex-cli/03-architecture' },
              ]
            },
            {
              text: 'Gemini CLI',
              collapsed: false,
              items: [
                { text: '概览', link: '/tools/gemini-cli/01-overview' },
                { text: '命令', link: '/tools/gemini-cli/02-commands' },
                { text: '架构', link: '/tools/gemini-cli/03-architecture' },
                { text: '工具', link: '/tools/gemini-cli/04-tools' },
                { text: '策略引擎', link: '/tools/gemini-cli/05-policies' },
              ]
            },
            {
              text: 'Qwen Code',
              collapsed: false,
              items: [
                { text: '概览', link: '/tools/qwen-code/01-overview' },
                { text: '命令', link: '/tools/qwen-code/02-commands' },
                { text: '架构', link: '/tools/qwen-code/03-architecture' },
                { text: '工具', link: '/tools/qwen-code/04-tools' },
                { text: '设置', link: '/tools/qwen-code/05-settings' },
                { text: '扩展系统', link: '/tools/qwen-code/06-extensions' },
              ]
            },
            {
              text: 'Kimi CLI',
              collapsed: false,
              items: [
                { text: '概览', link: '/tools/kimi-cli/01-overview' },
                { text: '命令', link: '/tools/kimi-cli/02-commands' },
                { text: '架构', link: '/tools/kimi-cli/03-architecture' },
              ]
            },
            {
              text: 'Aider',
              collapsed: false,
              items: [
                { text: '概览', link: '/tools/aider/01-overview' },
                { text: '命令', link: '/tools/aider/02-commands' },
                { text: '架构', link: '/tools/aider/03-architecture' },
              ]
            },
            {
              text: 'OpenCode',
              collapsed: false,
              items: [
                { text: '概览', link: '/tools/opencode/01-overview' },
                { text: '命令', link: '/tools/opencode/02-commands' },
                { text: '架构', link: '/tools/opencode/03-architecture' },
              ]
            },
            {
              text: 'Goose',
              collapsed: false,
              items: [
                { text: '概览', link: '/tools/goose/01-overview' },
                { text: '命令', link: '/tools/goose/02-commands' },
                { text: '架构', link: '/tools/goose/03-architecture' },
                { text: '扩展', link: '/tools/goose/04-extensions' },
              ]
            },
            {
              text: 'Qoder CLI',
              collapsed: false,
              items: [
                { text: '概览', link: '/tools/qoder-cli/01-overview' },
                { text: '架构', link: '/tools/qoder-cli/02-architecture' },
              ]
            },
          ]
        },
        {
          text: '单文件 Agent',
          collapsed: false,
          items: [
            { text: 'Cline', link: '/tools/cline' },
            { text: 'Continue', link: '/tools/continue' },
            { text: 'Cursor', link: '/tools/cursor-cli' },
            { text: 'Warp', link: '/tools/warp' },
            { text: 'OpenHands', link: '/tools/openhands' },
            { text: 'SWE-agent', link: '/tools/swe-agent' },
            { text: 'mini-swe-agent', link: '/tools/mini-swe-agent' },
            { text: 'Oh My OpenAgent', link: '/tools/oh-my-openagent' },
            { text: 'Everything Claude Code', link: '/tools/everything-claude-code' },
          ]
        },
      ],

      '/comparison/': [
        {
          text: '功能对比',
          items: [
            { text: '功能对比矩阵', link: '/comparison/features' },
            { text: '架构深度对比', link: '/comparison/architecture-deep-dive' },
            { text: '命令深度对比', link: '/comparison/slash-commands-deep-dive' },
            { text: '功能性内部机制', link: '/comparison/functional-internals' },
            { text: 'Deep-Dive 索引', link: '/comparison/deep-dive-index' },
          ]
        },
        {
          text: '选型参考',
          collapsed: false,
          items: [
            { text: '隐私与遥测', link: '/comparison/privacy-telemetry' },
            { text: '定价与成本', link: '/comparison/pricing' },
            { text: '系统要求', link: '/comparison/system-requirements' },
            { text: '版本迭代与社区', link: '/comparison/evolution-community' },
            { text: 'CLI vs IDE Agent', link: '/comparison/cli-vs-ide-agents' },
          ]
        },
        {
          text: '命令详解',
          collapsed: false,
          items: [
            { text: '/review 对比', link: '/comparison/review-command' },
            { text: '/security-review', link: '/comparison/security-review-command-deep-dive' },
            { text: '/compact /plan /init', link: '/comparison/key-commands-deep-dive' },
            { text: '/loop /schedule', link: '/comparison/loop-schedule' },
            { text: '/simplify', link: '/comparison/simplify-command' },
            { text: '/hooks /model /mcp', link: '/comparison/infra-commands' },
            { text: '/btw /rewind', link: '/comparison/btw-rewind' },
          ]
        },
        {
          text: '核心架构 Deep-Dive',
          collapsed: false,
          items: [
            { text: '模型路由', link: '/comparison/model-routing' },
            { text: '上下文压缩', link: '/comparison/context-compression-deep-dive' },
            { text: 'MCP 集成', link: '/comparison/mcp-integration-deep-dive' },
            { text: '沙箱安全', link: '/comparison/sandbox-security-deep-dive' },
            { text: '多代理', link: '/comparison/multi-agent-deep-dive' },
            { text: '系统提示', link: '/comparison/system-prompt-deep-dive' },
          ]
        },
        {
          text: '扩展系统 Deep-Dive',
          collapsed: false,
          items: [
            { text: 'Hook/插件', link: '/comparison/hook-plugin-extension-deep-dive' },
            { text: 'Skill 技能系统', link: '/comparison/skill-system-deep-dive' },
            { text: '长期记忆', link: '/comparison/memory-system-deep-dive' },
          ]
        },
        {
          text: '工程实践 Deep-Dive',
          collapsed: false,
          items: [
            { text: '终端 UI', link: '/comparison/terminal-ui-deep-dive' },
            { text: 'Git 集成', link: '/comparison/git-integration-deep-dive' },
            { text: '测试反射', link: '/comparison/test-reflection-deep-dive' },
            { text: 'CI 模式', link: '/comparison/ci-scripting-deep-dive' },
            { text: '遥测隐私', link: '/comparison/telemetry-privacy-deep-dive' },
            { text: 'API 参数', link: '/comparison/api-params-deep-dive' },
          ]
        },
        {
          text: 'Agent 1v1 对比',
          collapsed: false,
          items: [
            { text: 'Claude Code vs Cursor', link: '/comparison/claude-code-vs-cursor' },
            { text: 'Claude Code vs Copilot CLI', link: '/comparison/claude-code-vs-copilot-cli' },
            { text: 'Aider vs Goose', link: '/comparison/aider-vs-goose' },
            { text: 'Qwen vs Claude Code', link: '/comparison/qwen-vs-claude-code' },
            { text: 'Qwen vs Gemini vs Kimi', link: '/comparison/qwen-vs-gemini-vs-kimi' },
            { text: 'OpenCode vs Qwen', link: '/comparison/opencode-vs-qwen-source' },
          ]
        },
        {
          text: 'Qwen 功能补全',
          collapsed: false,
          items: [
            { text: '性能差距+改进路线图', link: '/comparison/claude-code-speed-qwen-improvements' },
            { text: '改进总报告', link: '/comparison/qwen-code-improvement-report' },
            { text: 'Gemini 上游报告', link: '/comparison/qwen-code-gemini-upstream-report' },
            { text: 'Gemini 上游详情', link: '/comparison/qwen-code-gemini-upstream-report-details' },
            { text: 'Review 改进', link: '/comparison/qwen-code-review-improvements' },
            {
              text: '对标分析',
              collapsed: false,
              items: [
                { text: '对标 Claude Code', link: '/comparison/qwen-code-feature-gaps' },
                { text: '对标 Gemini CLI', link: '/comparison/qwen-code-vs-gemini-feature-gaps' },
                { text: '对标 OpenCode', link: '/comparison/qwen-code-vs-opencode-feature-gaps' },
                { text: '对标 Kimi CLI', link: '/comparison/qwen-code-vs-kimi-feature-gaps' },
              ]
            },
            {
              text: 'P0/P1 改进',
              collapsed: false,
              items: [
                { text: '核心功能', link: '/comparison/qwen-code-improvement-report-p0-p1-core' },
                { text: '引擎', link: '/comparison/qwen-code-improvement-report-p0-p1-engine' },
                { text: '平台', link: '/comparison/qwen-code-improvement-report-p0-p1-platform' },
              ]
            },
            {
              text: 'P2 改进',
              collapsed: false,
              items: [
                { text: '核心功能', link: '/comparison/qwen-code-improvement-report-p2-core' },
                { text: '性能', link: '/comparison/qwen-code-improvement-report-p2-perf' },
                { text: '稳定性', link: '/comparison/qwen-code-improvement-report-p2-stability' },
                { text: '工具/命令', link: '/comparison/qwen-code-improvement-report-p2-tools-commands' },
                { text: '工具/UI', link: '/comparison/qwen-code-improvement-report-p2-tools-ui' },
              ]
            },
            {
              text: 'P3 改进',
              collapsed: false,
              items: [
                { text: '功能', link: '/comparison/qwen-code-improvement-report-p3-features' },
                { text: 'Hooks', link: '/comparison/qwen-code-improvement-report-p3-hooks' },
                { text: 'UX', link: '/comparison/qwen-code-improvement-report-p3-ux' },
              ]
            },
          ]
        },
        {
          text: '更多 Deep-Dive',
          collapsed: true,
          items: [
            { text: 'Plan 模式 Interview', link: '/comparison/plan-mode-interview-deep-dive' },
            { text: 'BriefTool 异步消息', link: '/comparison/brieftool-async-user-messages-deep-dive' },
            { text: 'Prompt Suggestion', link: '/comparison/prompt-suggestion-deep-dive' },
            { text: '命令队列编排', link: '/comparison/command-queue-orchestration-deep-dive' },
            { text: '自动后台化 Agent', link: '/comparison/session-backgrounding-deep-dive' },
            { text: '/context 自动化诊断', link: '/comparison/context-usage-noninteractive-deep-dive' },
            { text: '插件 Marketplace', link: '/comparison/plugin-marketplace-lifecycle-deep-dive' },
            { text: 'Advisor 模型', link: '/comparison/advisor-model-deep-dive' },
            { text: 'Agent SDK Python', link: '/comparison/agent-sdk-python-deep-dive' },
            { text: 'Attachment 协议', link: '/comparison/attachment-protocol-budget-deep-dive' },
            { text: 'Batch 并行执行', link: '/comparison/batch-parallel-execution-deep-dive' },
            { text: 'Computer Use', link: '/comparison/computer-use-deep-dive' },
            { text: 'Coordinator Swarm', link: '/comparison/coordinator-swarm-orchestration-deep-dive' },
            { text: 'Fork Subagent', link: '/comparison/fork-subagent-deep-dive' },
            { text: 'In-Process Agent Isolation', link: '/comparison/in-process-agent-isolation-deep-dive' },
            { text: 'Structured Output', link: '/comparison/structured-output-deep-dive' },
          ]
        },
      ],

      '/guides/': [
        {
          text: '使用指南',
          items: [
            { text: '入门指南', link: '/guides/getting-started' },
            { text: '工作流', link: '/guides/workflows' },
            { text: '配置示例', link: '/guides/config-examples' },
            { text: '迁移指南', link: '/guides/migration' },
            { text: '故障排查', link: '/guides/troubleshooting' },
            { text: '高效提示词', link: '/guides/effective-prompts' },
          ]
        },
        {
          text: '深度配置',
          collapsed: false,
          items: [
            { text: 'CLAUDE.md 写作', link: '/guides/writing-claude-md' },
            { text: 'AGENTS.md', link: '/guides/agents-md' },
            { text: '长期记忆与个性化', link: '/guides/long-term-memory' },
            { text: 'Skill 设计', link: '/guides/skill-design' },
            { text: 'Hooks 配置', link: '/guides/hooks-config' },
            { text: '上下文管理', link: '/guides/context-management' },
            { text: '安全加固', link: '/guides/security-hardening' },
          ]
        },
        {
          text: '用户指南',
          collapsed: false,
          items: [
            { text: 'Claude Code 用户指南', link: '/guides/claude-code-user-guide' },
            { text: 'Copilot CLI 用户指南', link: '/guides/copilot-cli-user-guide' },
            { text: 'Qwen Code 用户指南', link: '/guides/qwen-code-user-guide' },
          ]
        },
        {
          text: '架构选型',
          collapsed: false,
          items: [
            { text: '构建自己的 Agent', link: '/guides/build-your-own-agent' },
          ]
        },
      ],

      '/architecture/': [
        {
          text: '架构原理',
          items: [
            { text: '架构原理概述', link: '/architecture/overview' },
          ]
        },
      ],

      '/benchmarks/': [
        {
          text: '基准测试',
          items: [
            { text: '基准测试概述', link: '/benchmarks/overview' },
          ]
        },
      ],
    },

    search: {
      provider: 'local',
      options: {
        locales: {
          root: {
            translations: {
              button: { buttonText: '搜索', buttonAriaLabel: '搜索' },
              modal: {
                noResultsText: '无法找到相关结果',
                resetButtonTitle: '清除查询条件',
                footer: { selectText: '选择', navigateText: '切换', closeText: '关闭' },
              },
            },
          },
        },
      },
    },

    editLink: {
      pattern: 'https://github.com/wenshao/codeagents/edit/main/docs/:path',
      text: '在 GitHub 上编辑此页',
    },

    footer: {
      message: '基于 MIT 许可发布。本项目与上述任何 Agent 无关联，信息基于源码分析，仅供参考。',
    },

    docFooter: {
      prev: '上一页',
      next: '下一页',
    },

    outline: {
      label: '页面导航',
      level: [2, 3],
    },

    lastUpdated: {
      text: '最后更新于',
    },

    returnToTopLabel: '回到顶部',
    sidebarMenuLabel: '菜单',
    darkModeSwitchLabel: '主题',
    lightModeSwitchTitle: '切换到浅色模式',
    darkModeSwitchTitle: '切换到深色模式',
  },

  srcExclude: [
    'data/agents-metadata.json',
    'data/schema.json',
    '**/EVIDENCE.md',
  ],

  // 白名单模式忽略已知的死链接
  ignoreDeadLinks: [
    /EVIDENCE/,
    /index/,
  ],
})
