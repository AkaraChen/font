import type { APIRoute } from 'astro'
import { families } from '../../../data/families'
import { familyMarkdown, textResponse } from '../../../data/geo'

export function getStaticPaths() {
  return families.map(family => ({ params: { id: family.id } }))
}

export const GET: APIRoute = ({ params }) => {
  const family = families.find(f => f.id === params.id)
  if (!family) return new Response('Not found', { status: 404 })
  return textResponse(familyMarkdown('en', family), 'text/markdown')
}
