import type { APIRoute } from 'astro'
import { jsonResponse, upstreamsJson } from '../../data/geo'

export const GET: APIRoute = () => jsonResponse(upstreamsJson())
