import type { APIRoute } from 'astro'
import { families } from '../data/families'
import { textResponse } from '../data/geo'
import { upstreams } from '../data/upstreams'

// Machine-readable URL list (llms surfaces + JSON). Complement to sitemap-index.xml.
export const GET: APIRoute = ({ site }) => {
  const base = (site?.href || process.env.SITE_URL || 'https://font.akr.moe').replace(/\/+$/, '')
  const urls = [
    '/llms.txt',
    '/llms-full.txt',
    '/index.md',
    '/en/index.md',
    '/families.md',
    '/en/families.md',
    '/license.md',
    '/en/license.md',
    '/preview.md',
    '/en/preview.md',
    '/upstream.md',
    '/en/upstream.md',
    '/api/site.json',
    '/api/families.json',
    '/api/upstreams.json',
    ...families.flatMap(f => [`/family/${f.id}.md`, `/en/family/${f.id}.md`]),
    ...upstreams.flatMap(u => [`/upstream/${u.slug}.md`, `/en/upstream/${u.slug}.md`]),
  ]
  return textResponse(urls.map(u => `${base}${u}`).join('\n') + '\n', 'text/plain')
}
