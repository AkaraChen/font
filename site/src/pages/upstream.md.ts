import type { APIRoute } from 'astro'
import { textResponse } from '../data/geo'
import { upstreams } from '../data/upstreams'

const SITE = (process.env.SITE_URL || 'https://font.akr.moe').replace(/\/+$/, '')

export const GET: APIRoute = () => {
  const list = upstreams.map(u =>
    `- [${u.name.zh}](${SITE}/upstream/${u.slug}.md) — ${u.author} · [原版](${u.url})`,
  ).join('\n')
  return textResponse(`# 上游字体

每个上游一页：它本来是什么、AKR 把它做成了什么、和原版差在哪。原版链接都在页面最前面。

${list}

索引 JSON：${SITE}/api/upstreams.json
`, 'text/markdown')
}
