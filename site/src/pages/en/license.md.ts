import type { APIRoute } from 'astro'
import { licenseMarkdown, textResponse } from '../../data/geo'

export const GET: APIRoute = () => textResponse(licenseMarkdown('en'), 'text/markdown')
