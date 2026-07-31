import type { APIRoute } from 'astro'
import { textResponse } from '../../data/geo'
import { upstreams } from '../../data/upstreams'

const SITE = (process.env.SITE_URL || 'https://font.akr.moe').replace(/\/+$/, '')

export const GET: APIRoute = () => {
  const list = upstreams.map(u =>
    `- [${u.name.en}](${SITE}/en/upstream/${u.slug}.md) — ${u.author} · [upstream](${u.url})`,
  ).join('\n')
  return textResponse(`# Upstream fonts

One page per upstream: what it is on its own, what AKR made of it, and how the two differ. The original project is linked first.

${list}

JSON index: ${SITE}/api/upstreams.json
`, 'text/markdown')
}
