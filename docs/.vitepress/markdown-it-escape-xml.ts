/**
 * markdown-it 插件：在 markdown 解析之前，将非代码块中的 XML-like 占位符转义
 * 避免 Vue 模板编译器将 <file>、<number> 等占位符解析为 HTML 标签
 */
import type MarkdownIt from 'markdown-it'

const HTML_TAGS = new Set([
  'html','head','body','div','span','a','p','h1','h2','h3','h4','h5','h6',
  'ul','ol','li','dl','dt','dd','table','thead','tbody','tfoot','tr','th','td',
  'pre','code','blockquote','hr','br','img','em','strong','del','sup','sub',
  'details','summary','figure','figcaption','form','input','button','select',
  'option','textarea','label','fieldset','legend','iframe','script','style',
  'link','meta','title','base','noscript','template','slot',
  'svg','path','circle','rect','line','polyline','polygon','text','g',
  'defs','clippath','lineargradient','radialgradient','stop','use','symbol',
  'col','colgroup','caption','abbr','address','article','aside','audio',
  'b','bdi','bdo','canvas','cite','data','datalist','dfn','dialog',
  'embed','footer','header','hgroup','ins','kbd','main','map','mark',
  'menu','meter','nav','object','output','picture','progress','q','rp',
  'rt','ruby','s','samp','section','small','source','time','track',
  'u','var','video','wbr',
])

// 匹配 XML-like 标签：<tag>, </tag>, <tag/>, <tag attr="val">
const TAG_RE = /<\/?([a-zA-Z][a-zA-Z0-9_-]*)(\s[^>]*)?\/?>/g

function escapeNonHtmlTags(content: string): string {
  return content.replace(TAG_RE, (match, tagName: string) => {
    if (HTML_TAGS.has(tagName.toLowerCase())) {
      return match
    }
    // 转义 < > 为 HTML 实体
    return match.replace(/</g, '&lt;').replace(/>/g, '&gt;')
  })
}

export default function escapeXmlPlugin(md: MarkdownIt): void {
  // 在 markdown-it 解析前预处理原始内容
  // 只处理非代码块的部分
  const originalParse = md.parse.bind(md)
  md.parse = (src, env) => {
    // 分离代码块，只转义非代码块部分
    const parts: string[] = []
    let lastEnd = 0
    let inCode = false

    // 匹配 ```...``` 代码块
    const codeBlockRe = /```[\s\S]*?```/g
    let match: RegExpExecArray | null
    while ((match = codeBlockRe.exec(src)) !== null) {
      // 处理代码块之前的文本
      if (match.index > lastEnd) {
        parts.push(escapeNonHtmlTags(src.slice(lastEnd, match.index)))
      }
      // 保留代码块原样
      parts.push(match[0])
      lastEnd = match.index + match[0].length
    }
    // 处理剩余文本
    if (lastEnd < src.length) {
      parts.push(escapeNonHtmlTags(src.slice(lastEnd)))
    }

    const processedSrc = parts.join('')
    return originalParse(processedSrc, env)
  }
}
