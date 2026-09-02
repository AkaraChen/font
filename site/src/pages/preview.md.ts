import type { APIRoute } from 'astro'
import { textResponse } from '../data/geo'
import { ui } from '../i18n/ui'

const SITE = (process.env.SITE_URL || 'https://font.akr.moe').replace(/\/+$/, '')

export const GET: APIRoute = () => textResponse(`# ${ui.zh['preview.title']}

${ui.zh['preview.intro']}

- HTML 预览页：${SITE}/preview
- 英文：${SITE}/en/preview
- 字体家族 Markdown：${SITE}/families.md
- 下载：https://github.com/AkaraChen/font/releases

在线预览是浏览器 UI（按需加载完整字体），没有单独的 API。选字体、字号、行高、连字与主题后即可输入文字实时看效果。
`, 'text/markdown')
