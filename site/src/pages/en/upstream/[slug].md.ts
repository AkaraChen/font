import type { APIRoute } from 'astro'
import { upstreamMarkdown, textResponse } from '../../../data/geo'
import { upstreams } from '../../../data/upstreams'

export function getStaticPaths() {
  return upstreams.map(u => ({ params: { slug: u.slug } }))
}

export const GET: APIRoute = ({ params }) => {
  if (!params.slug || !upstreams.some(u => u.slug === params.slug)) {
    return new Response('Not found', { status: 404 })
  }
  return textResponse(upstreamMarkdown('en', params.slug), 'text/markdown')
}
