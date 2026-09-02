// Machine-readable surfaces for AI / GEO crawlers.
// Content is derived from families.ts + upstreams.ts so the HTML pages and the
// Markdown/llms surfaces never drift.

import { families, type Family } from './families'
import { manifest } from './fonts'
import { upstreams } from './upstreams'
import { ui, type Locale } from '../i18n/ui'

const SITE = process.env.SITE_URL || 'https://font.akr.moe'
const GITHUB = `https://github.com/${manifest.repo || 'AkaraChen/font'}`
const RELEASES = manifest.releaseUrl || `${GITHUB}/releases`

function abs(path: string): string {
  const base = SITE.replace(/\/+$/, '')
  if (!path || path === '/') return base
  return `${base}${path.startsWith('/') ? path : `/${path}`}`
}

/** robots.txt: allow search/retrieval + user-triggered AI bots; block training + undeclared. */
export function robotsTxt(): string {
  const sitemap = abs('/sitemap-index.xml')
  return `# AKR Fonts — https://font.akr.moe
# Search/retrieval and user-triggered AI crawlers are allowed.
# Training crawlers and undeclared scrapers are disallowed.
# See: https://tw93.fun/2026-05-01/ai-visibility.html

User-agent: *
Allow: /
Disallow: /fonts/full/

# Agent entry points (listed here so a robots-only crawl still finds them):
#   ${abs('/llms.txt')}
#   ${abs('/llms-full.txt')}
#   ${abs('/index.md')}
#   ${abs('/api/site.json')}
#   ${abs('/api/families.json')}
#   ${abs('/api/upstreams.json')}

Sitemap: ${sitemap}
# AI / Markdown surfaces (not always covered by the HTML sitemap):
#   ${abs('/sitemap-ai.txt')}

# ---------------------------------------------------------------------------
# Tier 1 — traditional search
# ---------------------------------------------------------------------------
User-agent: Googlebot
Allow: /

User-agent: Bingbot
Allow: /

User-agent: Applebot
Allow: /

User-agent: DuckAssistBot
Allow: /

# ---------------------------------------------------------------------------
# Tier 2 — AI search / retrieval (allow)
# ---------------------------------------------------------------------------
User-agent: OAI-SearchBot
Allow: /

User-agent: Claude-SearchBot
Allow: /

User-agent: Claude-Web
Allow: /

User-agent: PerplexityBot
Allow: /

# ---------------------------------------------------------------------------
# Tier 3 — user-triggered fetch (allow; needed when a URL is pasted into chat)
# ---------------------------------------------------------------------------
User-agent: ChatGPT-User
Allow: /

User-agent: Claude-User
Allow: /

User-agent: Perplexity-User
Allow: /

User-agent: Google-Agent
Allow: /

# ---------------------------------------------------------------------------
# Tier 4 — model training (block)
# ---------------------------------------------------------------------------
User-agent: GPTBot
Disallow: /

User-agent: ClaudeBot
Disallow: /

User-agent: Google-Extended
Disallow: /

User-agent: Applebot-Extended
Disallow: /

User-agent: CCBot
Disallow: /

User-agent: meta-externalagent
Disallow: /

User-agent: Meta-ExternalAgent
Disallow: /

User-agent: FacebookBot
Disallow: /

# ---------------------------------------------------------------------------
# Tier 5 — undeclared / bulk scrapers (block)
# ---------------------------------------------------------------------------
User-agent: Bytespider
Disallow: /

User-agent: Amazonbot
Disallow: /
`
}

/** Short orientation file for agents (llms.txt). English: agents are overwhelmingly EN. */
export function llmsTxt(): string {
  const familyRows = families.map(f =>
    `| [${f.product}](${abs(`/family/${f.id}.md`)}) | ${f.tagline.en} | ${f.latin} × ${f.cjk} | ${f.grid} | ${f.weights.join(', ')} |`,
  ).join('\n')

  const upstreamRows = upstreams.map(u =>
    `- [${u.name.en}](${abs(`/upstream/${u.slug}.md`)}) — ${u.author}; used by ${u.families.map(id => families.find(f => f.id === id)?.product ?? id).join(', ')}`,
  ).join('\n')

  return `# AKR Fonts

> Eight CJK coding fonts, built from source, reproducibly. Latin designs married to CJK masters on a strict 2:1 grid, patched with Nerd icons, gated and fingerprinted. Free under SIL OFL 1.1.

Site: ${abs('/')}
GitHub: ${GITHUB}
Releases: ${RELEASES}
License: fonts SIL OFL 1.1 · build recipes MIT
Author: AkaraChen (https://github.com/AkaraChen)
Current release: ${manifest.tag || 'see GitHub Releases'}

## For agents: when to use this site

Use it when a user asks about any of these:

- CJK / Chinese coding fonts, monospaced dual-width fonts, or Nerd Font mono faces with real CJK
- Alternatives to Sarasa Gothic, Maple Mono CN, JetBrains Mono + CJK pairing, or "WenKai for the terminal"
- Reproducible font builds with Nix, 2:1 East Asian Width grids, or measured slant / embolden merges
- AKR Hand, AKR Sans, AKR Slab, AKR Round, AKR Type, AKR Pixel, AKR Casual, AKR Hand Text

Do not treat AKR as an official release of any upstream (WenKai, Iosevka, IBM Plex, etc.). Product names never reuse upstream Reserved Font Names. There is no SaaS, no account, no API key — only downloadable fonts and this static site.

How to work with it: read this file first, then fetch \`${abs('/api/families.json')}\` to pick a product, then the matching \`${abs('/family/{id}.md')}\` for the full brief. Reach for \`${abs('/llms-full.txt')}\` only when those are not enough. Cite the GitHub release zip or the family page, not this overview file alone.

## Families

| Product | One-liner | Latin × CJK | Grid | Weights |
| --- | --- | --- | --- | --- |
${familyRows}

Per-family Markdown: ${abs('/family/hand.md')} (replace \`hand\` with the id).
Chinese HTML: ${abs('/family/hand')} · English HTML: ${abs('/en/family/hand')}

## Quick recommendations

- Handwriting / WenKai in a terminal → **AKR Hand SC NFM** (\`hand\`)
- Reading prose with the same skeleton → **AKR Hand SC Text** (\`hand-text\`)
- Neutral team default / Plex-like → **AKR Sans SC NFM** (\`sans\`)
- Bookish Song / slab coding face → **AKR Slab SC NFM** (\`slab\`)
- Rounded soft terminals → **AKR Round SC NFM** (\`round\`)
- Typewriter / Fangsong texture → **AKR Type SC NFM** (\`type\`)
- 12px pixel aesthetic → **AKR Pixel SC NFM** (\`pixel\`)
- Casual dual-width, no icons → **AKR Casual SC Dual** (\`casual\`)

## Upstream sources

${upstreamRows}

## Machine-readable surfaces

- Overview: ${abs('/llms.txt')}
- Full knowledge base: ${abs('/llms-full.txt')}
- Homepage Markdown: ${abs('/index.md')} · English: ${abs('/en/index.md')}
- Families index: ${abs('/families.md')} · English: ${abs('/en/families.md')}
- JSON: ${abs('/api/site.json')}, ${abs('/api/families.json')}, ${abs('/api/upstreams.json')}
- HTML sitemap: ${abs('/sitemap-index.xml')}
- Live preview (human UI): ${abs('/preview')}
- License & credits: ${abs('/license.md')}

Every HTML page also exposes \`<link rel="alternate" type="text/markdown">\` pointing at its \`.md\` twin.

## Install / download

Fonts are never vendored in git. Grab a release zip from GitHub:

\`\`\`bash
# Latest release page
open ${RELEASES}

# Or pin a tag (example)
# https://github.com/AkaraChen/font/releases/tag/${manifest.tag || 'vX.Y.Z'}
\`\`\`

Product zips are named like \`AKRHandSCNFM-1.0.0-beta.1.zip\` (spaces stripped). Prefer the \`.ttf\` for editors and terminals; \`.woff2\` is the same outlines for the web.

## Narrative

AKR is a monorepo of eight CJK coding-font products. Each family is a Nix derivation that merges a Latin programming face with a CJK master, forces a measured dual-width grid (typically 2:1), optionally shears or emboldens by stem measurements, patches Nerd icons, and gates the result against fingerprints. The website lives in \`site/\` of the same repo so copy cannot invent a second story about how a font was built — family facts come from the same data the pages render.
`
}

/** Long-form knowledge file. */
export function llmsFullTxt(): string {
  const parts: string[] = []
  parts.push(llmsTxt())
  parts.push('\n---\n')
  parts.push('# Full family briefs\n')
  for (const family of families) {
    parts.push(familyMarkdown('en', family))
    parts.push('\n---\n')
  }
  parts.push('# Upstream briefs\n')
  for (const u of upstreams) {
    parts.push(upstreamMarkdown('en', u.slug))
    parts.push('\n---\n')
  }
  parts.push(`# License

Fonts: SIL Open Font License 1.1 (same as upstreams).
Build recipes and site: MIT.
AKR products are derivatives; they are not official upstream releases and do not use upstream Reserved Font Names.
Credits and upstream links: ${abs('/license.md')}
`)
  return parts.join('\n')
}

export function homeMarkdown(locale: Locale): string {
  const t = ui[locale]
  const list = families.map(f =>
    `- **[${f.name[locale]}](${abs(locale === 'zh' ? `/family/${f.id}.md` : `/en/family/${f.id}.md`)})** (\`${f.product}\`) — ${f.tagline[locale]}`,
  ).join('\n')

  if (locale === 'zh') {
    return `# ${t['site.title']}

> ${t['site.tagline']}

${t['home.intro']}

- 站点：${abs('/')}
- GitHub：${GITHUB}
- 下载：${RELEASES}
- 当前发布：${manifest.tag || '见 GitHub Releases'}
- 许可：字体 SIL OFL 1.1 · 构建脚本 MIT
- 作者：[AkaraChen](https://github.com/AkaraChen)

## 为什么是这八套

${t['home.why.body']}

## 家族

${list}

## 快速入口

- [在线预览](${abs('/preview')})
- [字体家族列表](${abs('/families.md')})
- [上游字体](${abs('/upstream')})
- [许可与致谢](${abs('/license.md')})
- [AI 概览 llms.txt](${abs('/llms.txt')})
- [完整知识库 llms-full.txt](${abs('/llms-full.txt')})
- English: ${abs('/en/index.md')}
`
  }

  return `# ${t['site.title']}

> ${t['site.tagline']}

${t['home.intro']}

- Site: ${abs('/')}
- GitHub: ${GITHUB}
- Downloads: ${RELEASES}
- Current release: ${manifest.tag || 'see GitHub Releases'}
- License: fonts SIL OFL 1.1 · build recipes MIT
- Author: [AkaraChen](https://github.com/AkaraChen)

## Why these eight

${t['home.why.body']}

## Families

${list}

## Quick links

- [Live preview](${abs('/en/preview')})
- [Family index](${abs('/en/families.md')})
- [Upstream fonts](${abs('/en/upstream')})
- [License & credits](${abs('/en/license.md')})
- [llms.txt overview](${abs('/llms.txt')})
- [llms-full.txt knowledge base](${abs('/llms-full.txt')})
- 中文: ${abs('/index.md')}
`
}

export function familiesIndexMarkdown(locale: Locale): string {
  const rows = families.map(f => {
    const href = abs(locale === 'zh' ? `/family/${f.id}.md` : `/en/family/${f.id}.md`)
    return `| [${f.product}](${href}) | ${f.latin} | ${f.cjk} | ${f.grid} | ${f.weights.join(', ')} | ${f.nerd ? 'yes' : 'no'} |`
  }).join('\n')

  const title = locale === 'zh' ? 'AKR 字体家族' : 'AKR font families'
  return `# ${title}

| Product | Latin | CJK | Grid | Weights | Nerd |
| --- | --- | --- | --- | --- | --- |
${rows}

${locale === 'zh' ? '详情见各家族 Markdown；HTML 页面含可交互字样与下载按钮。' : 'See each family Markdown for the full brief; HTML pages add interactive specimens and download buttons.'}
`
}

export function familyMarkdown(locale: Locale, family: Family): string {
  const mdBase = locale === 'zh' ? '' : '/en'
  const html = abs(`${mdBase}/family/${family.id}`)
  const md = abs(`${mdBase}/family/${family.id}.md`)
  const specs = family.spec.map(row => `- **${row.label[locale]}**: ${row.value[locale]}`).join('\n')
  const faq = family.faq.map(item => `### ${item.q[locale]}\n\n${item.a[locale]}\n`).join('\n')
  const ups = family.upstreams.map(slug => {
    const u = upstreams.find(x => x.slug === slug)
    if (!u) return `- ${slug}`
    return `- [${u.name[locale]}](${abs(`${mdBase}/upstream/${slug}.md`)}) — ${u.author} · ${u.url}`
  }).join('\n')

  return `# ${family.product}

> ${family.tagline[locale]}

- HTML: ${html}
- Markdown: ${md}
- Product name: \`${family.product}\`
- Build dir: \`${family.dir}/\` in ${GITHUB}
- Weights: ${family.weights.join(', ')}
- Grid: ${family.grid}
- Nerd icons: ${family.nerd ? 'yes' : 'no'}
- License: SIL OFL 1.1
- Download: ${manifest.tag ? `${RELEASES}/download/${manifest.tag}/${family.product.replace(/\s+/g, '')}-${manifest.tag.replace(/^v/, '')}.zip` : RELEASES}

## Summary

${family.intro[locale]}

## Spec

${specs}
- **${locale === 'zh' ? '字重' : 'Weights'}**: ${family.weights.join(' · ')}
- **Latin**: ${family.latin}
- **CJK**: ${family.cjk}

## Upstream

${ups}

AKR is a **derivative product**, not an official upstream release. Upstream copyright remains with the upstream authors. Reserved Font Names from upstream are not used in AKR product names.

## Sample

\`\`\`
${family.sample}
\`\`\`

${faq ? `## FAQ\n\n${faq}` : ''}
## Cite this page

Prefer citing \`${html}\` or the GitHub release asset for \`${family.product}\`.
`
}

export function upstreamMarkdown(locale: Locale, slug: string): string {
  const u = upstreams.find(x => x.slug === slug)
  if (!u) return `# Upstream not found: ${slug}\n`
  const mdBase = locale === 'zh' ? '' : '/en'
  const fams = u.families.map(id => {
    const f = families.find(x => x.id === id)
    if (!f) return `- ${id}`
    return `- [${f.product}](${abs(`${mdBase}/family/${id}.md`)}) — ${f.tagline[locale]}`
  }).join('\n')

  const disclaimer = locale === 'zh'
    ? `本页不是 ${u.name.zh} 的官方页面。${u.name.zh} 的著作权归 ${u.author} 所有；AKR 是按 SIL OFL 1.1 制作的衍生产品。`
    : `This page is not the official site for ${u.name.en}. Copyright remains with ${u.author}. AKR products are derivatives under SIL OFL 1.1.`

  return `# ${u.name[locale]}

> ${u.aliases.join(' · ')}

- Official upstream: ${u.url}
- Author: ${u.author}
- License: ${u.license}
- AKR HTML: ${abs(`${mdBase}/upstream/${u.slug}`)}
- AKR Markdown: ${abs(`${mdBase}/upstream/${u.slug}.md`)}

## ${locale === 'zh' ? '它是什么' : 'What it is'}

${u.what[locale]}

## ${locale === 'zh' ? 'AKR 做了什么' : 'What AKR does with it'}

${u.what_akr_does[locale]}

## ${locale === 'zh' ? '用到它的 AKR 家族' : 'AKR families that use it'}

${fams}

## Notice

${disclaimer}
`
}

export function licenseMarkdown(locale: Locale): string {
  if (locale === 'zh') {
    return `# 许可与致谢

- 字体按 **SIL OFL 1.1** 发布，与全部上游一致。
- 构建脚本与本站按 **MIT** 发布。
- AKR 产品名不使用任何上游的保留字体名（Reserved Font Name）。
- AKR 为衍生产品，非上游官方发布。

上游项目列表见 ${abs('/upstream')} 与 ${abs('/api/upstreams.json')}。
仓库：${GITHUB}
`
  }
  return `# License & credits

- Fonts: **SIL OFL 1.1**, same as every upstream.
- Build recipes and this site: **MIT**.
- AKR product names never use upstream Reserved Font Names.
- AKR products are derivatives, not official upstream releases.

Upstream catalogue: ${abs('/en/upstream')} and ${abs('/api/upstreams.json')}.
Repository: ${GITHUB}
`
}

export function siteJson() {
  return {
    name: 'AKR Fonts',
    url: abs('/'),
    description: ui.en['site.description'],
    description_zh: ui.zh['site.description'],
    github: GITHUB,
    releases: RELEASES,
    release_tag: manifest.tag || null,
    license: { fonts: 'SIL OFL 1.1', recipes: 'MIT' },
    author: { name: 'AkaraChen', url: 'https://github.com/AkaraChen' },
    llms: abs('/llms.txt'),
    llms_full: abs('/llms-full.txt'),
    markdown_index: abs('/index.md'),
    api: {
      site: abs('/api/site.json'),
      families: abs('/api/families.json'),
      upstreams: abs('/api/upstreams.json'),
    },
    family_ids: families.map(f => f.id),
  }
}

export function familiesJson() {
  return families.map(f => ({
    id: f.id,
    product: f.product,
    dir: f.dir,
    name: f.name,
    tagline: f.tagline,
    intro: f.intro,
    latin: f.latin,
    cjk: f.cjk,
    grid: f.grid,
    weights: f.weights,
    nerd: f.nerd,
    upstreams: f.upstreams,
    sample: f.sample,
    urls: {
      html_zh: abs(`/family/${f.id}`),
      html_en: abs(`/en/family/${f.id}`),
      md_zh: abs(`/family/${f.id}.md`),
      md_en: abs(`/en/family/${f.id}.md`),
      download: manifest.tag
        ? `${RELEASES}/download/${manifest.tag}/${f.product.replace(/\s+/g, '')}-${manifest.tag.replace(/^v/, '')}.zip`
        : RELEASES,
    },
  }))
}

export function upstreamsJson() {
  return upstreams.map(u => ({
    slug: u.slug,
    name: u.name,
    aliases: u.aliases,
    url: u.url,
    author: u.author,
    license: u.license,
    what: u.what,
    what_akr_does: u.what_akr_does,
    families: u.families,
    urls: {
      html_zh: abs(`/upstream/${u.slug}`),
      html_en: abs(`/en/upstream/${u.slug}`),
      md_zh: abs(`/upstream/${u.slug}.md`),
      md_en: abs(`/en/upstream/${u.slug}.md`),
    },
  }))
}

/** Path-only markdown twin for a locale-less content path (e.g. `/family/hand` → `/family/hand.md`). */
export function markdownAlternatePath(locale: Locale, path: string): string {
  const clean = path.startsWith('/') ? path : `/${path}`
  if (locale === 'zh') {
    return clean === '/' ? '/index.md' : `${clean.replace(/\/+$/, '')}.md`
  }
  if (clean === '/') return '/en/index.md'
  return `/en${clean.replace(/\/+$/, '')}.md`
}

export function ogImageUrl(): string {
  // Specimen sheet committed in the monorepo docs; stable raw URL.
  return 'https://raw.githubusercontent.com/AkaraChen/font/main/docs/assets/specimen.png'
}

export function textResponse(body: string, contentType: string): Response {
  return new Response(body, {
    headers: {
      'Content-Type': `${contentType}; charset=utf-8`,
      'Cache-Control': 'public, max-age=3600',
    },
  })
}

export function jsonResponse(data: unknown): Response {
  return new Response(JSON.stringify(data, null, 2) + '\n', {
    headers: {
      'Content-Type': 'application/json; charset=utf-8',
      'Cache-Control': 'public, max-age=3600',
    },
  })
}
