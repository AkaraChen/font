import type { APIRoute } from 'astro'
import { llmsFullTxt, textResponse } from '../data/geo'

export const GET: APIRoute = () => textResponse(llmsFullTxt(), 'text/plain')
