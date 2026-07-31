// All UI copy, both languages, in one place.
//
// Wording note: the editable font demo is 「在线预览」/「预览」, never 「试打」.
// A static, non-editable showing is 「字样」. English uses "preview" and
// "specimen" respectively; the route stays /preview in both.

export const locales = ['zh', 'en'] as const
export type Locale = (typeof locales)[number]
export const defaultLocale: Locale = 'zh'

export const ui = {
  zh: {
    'site.title': 'AKR 字体',
    'site.tagline': '八套中英混排编程字体，从源码可复现构建',
    'site.description': '霞鹜文楷、Iosevka、IBM Plex Sans SC、朱雀仿宋等上游字体合并而成的中英等宽编程字体，严格 2:1 网格、Nerd 图标、Nix 可复现构建。免费下载，SIL OFL 1.1。',

    'nav.families': '字体家族',
    'nav.preview': '在线预览',
    'nav.upstream': '上游字体',
    'nav.docs': '文档',
    'nav.blog': '博客',
    'nav.license': '许可与致谢',
    'nav.github': 'GitHub',

    'home.eyebrow': '八套家族 · 2:1 网格 · Nerd 图标 · Nix 构建',
    'home.heading': '八套中英混排编程字体，从源码构建。',
    'home.intro': '拉丁设计与中日韩字体在严格 2:1 网格上合并，补 Nerd 图标、加 hinting、逐项校验。每个家族都是一个 Nix derivation，一条命令就能复现发布产物。',
    'home.cta.download': '下载字体',
    'home.cta.preview': '在线预览',
    'home.specimen': '字样',
    'home.specimen.note': '下面的字样由本次发布的字体直接渲染，不是图片。',
    'home.families.heading': '八套家族',
    'home.upstream.heading': '按上游字体查找',
    'home.upstream.intro': '每个上游一页：它本来是什么、AKR 把它做成了什么、和原版差在哪。原版链接都在页面最前面。',
    'home.why.heading': '为什么是这八套',
    'home.why.body': '中文编程字体的难点不在字形，在网格：拉丁和汉字必须严格 2:1，符号宽度要跟 East_Asian_Width 对上，Nerd 图标不能占两格，字重要在两种笔法之间对齐。这些都是量出来的，不是调出来的——倾角量自竖笔，字重量自笔画宽度，每次构建都过一遍闸。',

    'family.upstream': '上游',
    'family.spec': '规格',
    'family.preview': '预览',
    'family.download': '下载',
    'family.faq': '常见问题',
    'family.weights': '字重',
    'family.grid': '网格',
    'family.nerd': 'Nerd 图标',
    'family.source': '构建源码',
    'family.related': '相关家族',
    'family.derived': '本页说明的是衍生产品。上游字体的著作权归上游作者，AKR 不是上游的官方发布。',

    'preview.title': '在线预览',
    'preview.intro': '选一套字体，输入文字，实时看效果。字体在你选中之后才下载。',
    'preview.family': '字体',
    'preview.size': '字号',
    'preview.lineHeight': '行高',
    'preview.theme': '主题',
    'preview.theme.light': '浅色',
    'preview.theme.dark': '深色',
    'preview.ligatures': '连字',
    'preview.sample': '示例',
    'preview.sample.code': '代码',
    'preview.sample.prose': '正文',
    'preview.sample.mixed': '中英混排',
    'preview.loading': '正在加载字体…',
    'preview.loaded': '已加载',
    'preview.size.note': '完整字体包含全部汉字，首次加载需要几秒。',
    'preview.loadFull': '加载完整字体',
    'preview.copyLink': '复制链接',
    'preview.copied': '已复制',
    'preview.reset': '恢复默认',

    'upstream.title': '上游字体',
    'upstream.what': '它是什么',
    'upstream.akr': 'AKR 做了什么',
    'upstream.original': '原版项目',
    'upstream.families': '用到它的 AKR 家族',
    'upstream.notOfficial': '本页不是 {name} 的官方页面。{name} 的著作权归其作者所有，AKR 是按 SIL OFL 1.1 制作的衍生产品。',

    'license.title': '许可与致谢',
    'license.fonts': '字体按 SIL OFL 1.1 发布，与全部上游一致。构建脚本按 MIT 发布。',
    'license.thanks': '致谢',
    'license.rfn': 'AKR 产品名不使用任何上游的保留字体名（Reserved Font Name）。',

    'blog.title': '博客',
    'blog.empty': '还没有文章。',
    'blog.readMore': '继续读',

    'common.back': '返回',
    'common.download': '下载',
    'common.releases': 'GitHub Releases',
    'common.release': '当前发布',
    'common.viewSource': '查看源码',
    'common.otherLang': 'English',
    'footer.derived': 'AKR 为衍生产品，非上游官方发布。字体 SIL OFL 1.1，构建脚本 MIT。',
  },
  en: {
    'site.title': 'AKR Fonts',
    'site.tagline': 'Eight CJK coding fonts, built from source, reproducibly',
    'site.description': 'CJK coding fonts merging LXGW WenKai, Iosevka, IBM Plex Sans SC, Zhuque Fangsong and more with programming Latin: strict 2:1 grid, Nerd icons, reproducible Nix builds. Free, SIL OFL 1.1.',

    'nav.families': 'Families',
    'nav.preview': 'Preview',
    'nav.upstream': 'Upstream',
    'nav.docs': 'Docs',
    'nav.blog': 'Blog',
    'nav.license': 'License',
    'nav.github': 'GitHub',

    'home.eyebrow': 'Eight families · 2:1 grid · Nerd icons · Nix builds',
    'home.heading': 'Eight CJK coding fonts, built from source.',
    'home.intro': 'Latin designs married to CJK masters on a strict 2:1 grid, patched with Nerd icons, hinted and gated. Every family is a Nix derivation, and one command reproduces the release.',
    'home.cta.download': 'Download',
    'home.cta.preview': 'Preview',
    'home.specimen': 'Specimen',
    'home.specimen.note': 'Rendered from the fonts in this release — not images.',
    'home.families.heading': 'The families',
    'home.upstream.heading': 'Find it by upstream',
    'home.upstream.intro': 'One page per upstream: what it is on its own, what AKR made of it, and how the two differ. The original project is linked first on every page.',
    'home.why.heading': 'Why these eight',
    'home.why.body': 'The hard part of a CJK coding font is not the glyphs, it is the grid: Latin and CJK must sit at a strict 2:1, symbol widths must agree with East_Asian_Width, Nerd icons must not eat two cells, and weight must match across two different ways of drawing a stroke. Those are measured, not eyeballed — slant off the stems, weight off stroke width — and every build runs the gate again.',

    'family.upstream': 'Upstream',
    'family.spec': 'Spec',
    'family.preview': 'Preview',
    'family.download': 'Download',
    'family.faq': 'FAQ',
    'family.weights': 'Weights',
    'family.grid': 'Grid',
    'family.nerd': 'Nerd icons',
    'family.source': 'Build source',
    'family.related': 'Related families',
    'family.derived': 'This page describes a derivative product. Upstream fonts remain the work of their authors; AKR is not an official upstream release.',

    'preview.title': 'Preview',
    'preview.intro': 'Pick a font, type something, see it live. The font downloads only once you select it.',
    'preview.family': 'Font',
    'preview.size': 'Size',
    'preview.lineHeight': 'Line height',
    'preview.theme': 'Theme',
    'preview.theme.light': 'Light',
    'preview.theme.dark': 'Dark',
    'preview.ligatures': 'Ligatures',
    'preview.sample': 'Sample',
    'preview.sample.code': 'Code',
    'preview.sample.prose': 'Prose',
    'preview.sample.mixed': 'Mixed',
    'preview.loading': 'Loading font…',
    'preview.loaded': 'Loaded',
    'preview.size.note': 'The full font covers every CJK glyph, so the first load takes a few seconds.',
    'preview.loadFull': 'Load full font',
    'preview.copyLink': 'Copy link',
    'preview.copied': 'Copied',
    'preview.reset': 'Reset',

    'upstream.title': 'Upstream fonts',
    'upstream.what': 'What it is',
    'upstream.akr': 'What AKR does with it',
    'upstream.original': 'Original project',
    'upstream.families': 'AKR families using it',
    'upstream.notOfficial': 'This is not an official {name} page. {name} remains the work of its authors; AKR is a derivative made under SIL OFL 1.1.',

    'license.title': 'License & credits',
    'license.fonts': 'Fonts ship under SIL OFL 1.1, the same license as every upstream. Build recipes are MIT.',
    'license.thanks': 'Credits',
    'license.rfn': 'No AKR product name uses any upstream Reserved Font Name.',

    'blog.title': 'Blog',
    'blog.empty': 'Nothing here yet.',
    'blog.readMore': 'Read on',

    'common.back': 'Back',
    'common.download': 'Download',
    'common.releases': 'GitHub Releases',
    'common.release': 'Release',
    'common.viewSource': 'View source',
    'common.otherLang': '中文',
    'footer.derived': 'AKR is a derivative, not an official upstream release. Fonts SIL OFL 1.1, recipes MIT.',
  },
} as const satisfies Record<Locale, Record<string, string>>

export type UiKey = keyof (typeof ui)['zh']

export function useTranslations(locale: Locale) {
  return function t(key: UiKey): string {
    return ui[locale][key] ?? ui[defaultLocale][key]
  }
}

/** Prefixes a path with the locale segment, leaving the default locale bare. */
export function localePath(locale: Locale, path: string): string {
  const clean = path.startsWith('/') ? path : `/${path}`
  return locale === defaultLocale ? clean : `/${locale}${clean === '/' ? '' : clean}`
}

/** The same page in the other language. */
export function otherLocale(locale: Locale): Locale {
  return locale === 'zh' ? 'en' : 'zh'
}
