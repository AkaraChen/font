// Pulls the released fonts into the site.
//
// The site never vendors fonts in git: this script downloads the zips of one
// release (the latest, unless FONT_RELEASE_TAG says otherwise), then writes two
// kinds of file into public/fonts/:
//
//   subset/  — every product, subsetted to the characters the site itself uses.
//              A few tens of KB each, so a content page can show all eight
//              specimens without a megabyte-scale download.
//   full/    — Regular only, unsubsetted. The preview page fetches these on
//              demand, one at a time, when the reader picks a family.
//
// It also writes src/data/fonts.generated.json, which is what the pages read.

import { execFile } from 'node:child_process'
import { createHash } from 'node:crypto'
import { mkdir, readFile, readdir, rm, stat, writeFile } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { promisify } from 'node:util'
import subsetFont from 'subset-font'

const run = promisify(execFile)
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')

const REPO = process.env.FONT_REPO ?? 'AkaraChen/font'
const TAG = process.env.FONT_RELEASE_TAG
const CACHE = path.join(root, '.cache/fonts')
const OUT = path.join(root, 'public/fonts')
const MANIFEST = path.join(root, 'src/data/fonts.generated.json')

/** Products the site ships, in display order. Keyed by the release zip name. */
const PRODUCTS = [
  { id: 'slab', product: 'AKRSlabSCNFM', weights: ['Regular', 'Bold'] },
  { id: 'sans', product: 'AKRSansSCNFM', weights: ['Regular', 'Bold'] },
  { id: 'round', product: 'AKRRoundSCNFM', weights: ['Regular', 'Bold'] },
  { id: 'type', product: 'AKRTypeSCNFM', weights: ['Regular', 'Bold'] },
  { id: 'pixel', product: 'AKRPixelSCNFM', weights: ['Regular'] },
  { id: 'hand', product: 'AKRHandSCNFM', weights: ['Regular', 'Bold'] },
  { id: 'hand-text', product: 'AKRHandSCText', weights: ['Light', 'Regular', 'Bold'] },
  { id: 'casual', product: 'AKRCasualSCDual', weights: ['Regular', 'Bold'] },
]

/**
 * Characters every subset keeps regardless of what the source happens to use:
 * ASCII, the ligature operators a coding specimen is judged on, and the CJK
 * punctuation that shows the 2:1 cell.
 */
const BASE_CHARS = [
  ...' !"#$%&\'()*+,-./0123456789:;<=>?@',
  ...'ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`',
  ...'abcdefghijklmnopqrstuvwxyz{|}~',
  ...'←→↑↓⇒⇐≠≤≥…—–·、。，；：？！“”‘’（）《》【】',
  ...'ÀÁÂÄÈÉÊËÌÍÎÏÒÓÔÖÙÚÛÜàáâäèéêëìíîïòóôöùúûüñçß',
].join('')

async function fetchJson(url) {
  const res = await fetch(url, {
    headers: {
      'accept': 'application/vnd.github+json',
      'user-agent': 'akr-font-site',
      ...(process.env.GITHUB_TOKEN ? { authorization: `Bearer ${process.env.GITHUB_TOKEN}` } : {}),
    },
  })
  if (!res.ok) throw new Error(`${url} → ${res.status} ${res.statusText}`)
  return res.json()
}

async function resolveRelease() {
  if (TAG) return fetchJson(`https://api.github.com/repos/${REPO}/releases/tags/${TAG}`)
  return fetchJson(`https://api.github.com/repos/${REPO}/releases/latest`)
}

async function exists(p) {
  try {
    await stat(p)
    return true
  }
  catch {
    return false
  }
}

async function download(url, dest) {
  if (await exists(dest)) return dest
  const res = await fetch(url, {
    headers: {
      'accept': 'application/octet-stream',
      'user-agent': 'akr-font-site',
      ...(process.env.GITHUB_TOKEN ? { authorization: `Bearer ${process.env.GITHUB_TOKEN}` } : {}),
    },
  })
  if (!res.ok) throw new Error(`${url} → ${res.status} ${res.statusText}`)
  await mkdir(path.dirname(dest), { recursive: true })
  await writeFile(dest, Buffer.from(await res.arrayBuffer()))
  return dest
}

/**
 * Every CJK codepoint that appears anywhere in the site source, so a subset can
 * render the whole site without anyone maintaining a character list by hand.
 */
async function charsUsedInSource() {
  const roots = ['src', 'public/robots.txt'].map(p => path.join(root, p))
  const chars = new Set(BASE_CHARS)
  const walk = async (target) => {
    const info = await stat(target).catch(() => null)
    if (!info) return
    if (info.isDirectory()) {
      for (const entry of await readdir(target)) await walk(path.join(target, entry))
      return
    }
    if (!/\.(?:astro|ts|tsx|js|mjs|md|mdx|json|css|txt)$/.test(target)) return
    if (target.endsWith('fonts.generated.json')) return
    for (const ch of await readFile(target, 'utf8')) {
      // Keep CJK, kana, and fullwidth forms; ASCII is already in BASE_CHARS.
      if (/[⺀-鿿豈-﫿＀-￯　-〿]/.test(ch)) chars.add(ch)
    }
  }
  await walk(roots[0])
  return [...chars].join('')
}

async function main() {
  const release = await resolveRelease()
  const tag = release.tag_name
  console.log(`release ${tag} (${REPO})`)

  const text = await charsUsedInSource()
  console.log(`subset charset: ${[...new Set(text)].length} characters`)

  await rm(OUT, { recursive: true, force: true })
  await mkdir(path.join(OUT, 'subset'), { recursive: true })
  await mkdir(path.join(OUT, 'full'), { recursive: true })

  const manifest = { repo: REPO, tag, releaseUrl: release.html_url, products: [] }

  for (const { id, product, weights } of PRODUCTS) {
    const asset = release.assets.find(a => a.name.startsWith(`${product}-`) && a.name.endsWith('.zip'))
    if (!asset) {
      console.warn(`  ! ${product}: no zip in ${tag}, skipped`)
      continue
    }

    const zip = path.join(CACHE, tag, asset.name)
    await download(asset.browser_download_url, zip)
    const unpacked = path.join(CACHE, tag, asset.name.replace(/\.zip$/, ''))
    if (!(await exists(unpacked))) await run('unzip', ['-o', '-q', '-j', zip, '-d', unpacked])

    const files = []
    for (const weight of weights) {
      const ttf = path.join(unpacked, `${product}-${weight}.ttf`)
      if (!(await exists(ttf))) {
        console.warn(`  ! ${product}-${weight}.ttf missing, skipped`)
        continue
      }
      const source = await readFile(ttf)

      const subsetName = `${product}-${weight}.subset.woff2`
      const subset = await subsetFont(source, text, { targetFormat: 'woff2' })
      await writeFile(path.join(OUT, 'subset', subsetName), subset)

      const entry = {
        weight,
        subset: `/fonts/subset/${subsetName}`,
        subsetBytes: subset.length,
      }

      // Only Regular goes out unsubsetted — that is all the preview needs, and
      // each of these is several megabytes.
      if (weight === 'Regular') {
        const woff2 = path.join(unpacked, `${product}-${weight}.woff2`)
        if (await exists(woff2)) {
          const full = await readFile(woff2)
          const fullName = `${product}-${weight}.woff2`
          await writeFile(path.join(OUT, 'full', fullName), full)
          entry.full = `/fonts/full/${fullName}`
          entry.fullBytes = full.length
        }
      }

      files.push(entry)
      console.log(`  ${product}-${weight}: subset ${(subset.length / 1024).toFixed(0)} KB${entry.fullBytes ? `, full ${(entry.fullBytes / 1024 / 1024).toFixed(1)} MB` : ''}`)
    }

    if (files.length) manifest.products.push({ id, product, files })
  }

  manifest.hash = createHash('sha256').update(JSON.stringify(manifest)).digest('hex').slice(0, 12)
  await mkdir(path.dirname(MANIFEST), { recursive: true })
  await writeFile(MANIFEST, `${JSON.stringify(manifest, null, 2)}\n`)
  console.log(`wrote ${path.relative(root, MANIFEST)}`)
}

await main()
