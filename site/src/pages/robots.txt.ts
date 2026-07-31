import type { APIRoute } from 'astro'
import { absolute } from '../i18n/urls'

// Generated rather than static so the sitemap URL follows SITE_URL.
export const GET: APIRoute = ({ site }) => {
  const body = [
    'User-agent: *',
    'Allow: /',
    '',
    `Sitemap: ${absolute(site, '/sitemap-index.xml')}`,
    '',
  ].join('\n')

  return new Response(body, { headers: { 'Content-Type': 'text/plain; charset=utf-8' } })
}
