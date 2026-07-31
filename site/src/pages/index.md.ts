import type { APIRoute } from 'astro'
import { homeMarkdown, textResponse } from '../data/geo'

export const GET: APIRoute = () => textResponse(homeMarkdown('zh'), 'text/markdown')
