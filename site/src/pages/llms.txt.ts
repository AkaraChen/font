import type { APIRoute } from 'astro'
import { llmsTxt, textResponse } from '../data/geo'

export const GET: APIRoute = () => textResponse(llmsTxt(), 'text/plain')
