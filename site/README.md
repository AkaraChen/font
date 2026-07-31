# site — the AKR font website

An Astro static site: eight family pages, eleven upstream pages, an editable
preview, a blog, in Chinese and English. It lives in this monorepo so the copy
and the fonts can never drift from the recipes that build them.

```bash
cd site
pnpm install
pnpm fonts     # pull the latest release into public/fonts/ (needed once)
pnpm dev
pnpm build     # runs pnpm fonts, then astro build
pnpm check     # astro check (needs typescript 6.x; 7.x has no check API yet)
```

## Fonts are never committed

`scripts/fetch-fonts.mjs` downloads one GitHub release and writes two things
into `public/fonts/`, both gitignored:

| | what | size | used by |
| --- | --- | --- | --- |
| `subset/` | every product, subsetted to the characters the site itself uses | 25–230 KB each | specimens, headings, family pages |
| `full/` | Regular weights, unsubsetted | 1.8–9.6 MB each | the preview, fetched on demand |

The subset charset is derived from the source tree at build time — every CJK
character in `src/` goes in — so adding copy never requires touching a
character list. `src/data/fonts.generated.json` records what was produced and is
what the pages read; the site still renders (with system fonts) if it is absent.

```bash
FONT_RELEASE_TAG=v1.0.0-beta.1 pnpm fonts   # pin a release instead of latest
GITHUB_TOKEN=…                              # only needed if you hit rate limits
```

## Content lives in data, not in markup

- `src/data/families.ts` — one entry per released product. The facts must match
  that family's own `README.md`; the site does not get to tell a second story
  about how a font was built.
- `src/data/upstreams.ts` — one entry per upstream font. Two rules hold on every
  upstream page: it never presents itself as the upstream's official site, and
  it links the original project before it links to us. No upstream Reserved Font
  Name is ever used as an AKR product name.
- `src/i18n/ui.ts` — all UI copy, both languages. The editable demo is
  「在线预览」/「预览」, never 「试打」; a static showing is 「字样」.
- `src/content/blog/` — long-form posts, each tagged with its own `lang`. Posts
  are not machine mirrors: a language shows only what was written in it. Two
  posts with the same `pair` are the same article in both languages.

## Routing

Chinese is the default and sits at the root; English is under `/en/`. Each route
is a thin file that hands off to a shared component in `src/components/pages/`,
so a page exists once and is rendered twice.

```
/                     /en/
/families             /en/families
/family/<id>          /en/family/<id>
/upstream/<slug>      /en/upstream/<slug>
/preview              /en/preview
/blog, /blog/<slug>   /en/blog, /en/blog/<slug>
/license              /en/license
```

`hreflang` pairs are emitted from the same path on both trees, so the language
switch always lands on the equivalent page.

## Deployment

Not wired up yet — the domain is still undecided, and the right host depends on
it. What the build needs when it is:

```bash
SITE_URL=https://your-domain pnpm build
```

`SITE_URL` feeds canonical URLs, `hreflang`, `robots.txt` and the sitemap. The
default points at a GitHub Pages URL so nothing is broken locally, but internal
links are root-absolute, so a real deploy wants the site at the domain root
(custom domain, or a user/organisation Pages site) rather than under a project
sub-path.
