import type { APIRoute } from 'astro'
import { robotsTxt } from '../data/geo'

// Generated so SITE_URL and crawler policy stay in one place (src/data/geo.ts).
export const GET: APIRoute = () => {
  return new Response(robotsTxt(), {
    headers: { 'Content-Type': 'text/plain; charset=utf-8' },
  })
}
