import type { APIRoute } from 'astro'
import { familiesJson, jsonResponse } from '../../data/geo'

export const GET: APIRoute = () => jsonResponse(familiesJson())
