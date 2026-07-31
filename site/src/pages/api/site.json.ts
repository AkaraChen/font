import type { APIRoute } from 'astro'
import { jsonResponse, siteJson } from '../../data/geo'

export const GET: APIRoute = () => jsonResponse(siteJson())
