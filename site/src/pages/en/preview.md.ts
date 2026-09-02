import type { APIRoute } from 'astro'
import { textResponse } from '../../data/geo'
import { ui } from '../../i18n/ui'

const SITE = (process.env.SITE_URL || 'https://font.akr.moe').replace(/\/+$/, '')

export const GET: APIRoute = () => textResponse(`# ${ui.en['preview.title']}

${ui.en['preview.intro']}

- HTML preview: ${SITE}/en/preview
- Chinese: ${SITE}/preview
- Family Markdown index: ${SITE}/en/families.md
- Downloads: https://github.com/AkaraChen/font/releases

The live preview is a browser UI that loads full fonts on demand. There is no separate API — pick family, size, line height, ligatures and theme, then type.
`, 'text/markdown')
