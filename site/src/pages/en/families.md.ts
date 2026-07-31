import type { APIRoute } from 'astro'
import { familiesIndexMarkdown, textResponse } from '../../data/geo'

export const GET: APIRoute = () => textResponse(familiesIndexMarkdown('en'), 'text/markdown')
