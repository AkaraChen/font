// One entry per released product. Everything on a family page comes from here,
// and the facts are the ones the family's own README states — the site is not
// allowed to invent a second story about how a font was built.

export interface Bilingual {
  zh: string
  en: string
}

export interface SpecRow {
  label: Bilingual
  value: Bilingual
}

export interface Family {
  /** URL slug, and the id the font manifest is keyed on. */
  id: string
  /** Full product name as it appears in the font's name table. */
  product: string
  /** Directory in the monorepo that builds it. */
  dir: string
  name: Bilingual
  /** One line, used as the meta description seed and the card subtitle. */
  tagline: Bilingual
  /** Two or three sentences of real detail — this is the page's substance. */
  intro: Bilingual
  latin: string
  cjk: string
  /** Latin cell / CJK cell in font units. */
  grid: string
  weights: string[]
  nerd: boolean
  /** Upstream slugs whose landing pages should link here. */
  upstreams: string[]
  spec: SpecRow[]
  /** Sample line for the specimen strip. */
  sample: string
  faq: { q: Bilingual, a: Bilingual }[]
}

const OFL: SpecRow = {
  label: { zh: '许可', en: 'License' },
  value: { zh: 'SIL OFL 1.1（与上游一致）', en: 'SIL OFL 1.1, same as upstream' },
}

export const families: Family[] = [
  {
    id: 'slab',
    product: 'AKR Slab SC NFM',
    dir: 'serif',
    name: { zh: 'AKR Slab 宋', en: 'AKR Slab' },
    tagline: {
      zh: 'Slab 拉丁配霞鹜新致宋，衬线感最强的一套编程字体',
      en: 'A slab Latin married to LXGW NeoZhiSong — the most bookish of the eight',
    },
    intro: {
      zh: 'AKR Slab SC NFM 把 Sarasa 的 IosevkaNSlab 拉丁与霞鹜新致宋 Opt 汉字合到严格 2:1 网格上。宋体在编程字体里少见，笔画的起收让长时间读代码时的字形辨识度更高；Latin 侧保留了 Iosevka 的 calt 连字并把 dlig 折了进来。CJK 侧按测得的竖笔宽度加粗（Regular s=7.5、Bold s=24）来跟 Latin 对齐视觉重量。',
      en: 'AKR Slab SC NFM merges Sarasa\'s IosevkaNSlab Latin with LXGW NeoZhiSong Opt on a strict 2:1 grid. A Song/serif CJK face is unusual in a coding font: the stroke entries and exits make glyphs easier to tell apart over a long reading session. The Latin side keeps Iosevka\'s calt ligatures with dlig folded in, and the CJK side is emboldened by measured stem width (s=7.5 Regular, s=24 Bold) so both halves carry the same optical weight.',
    },
    latin: 'Sarasa IosevkaNSlab (MonoSlab)',
    cjk: '霞鹜新致宋 Opt · LXGW NeoZhiSong v1.066',
    grid: '500 / 1000',
    weights: ['Regular', 'Bold'],
    nerd: true,
    upstreams: ['lxgw-neozhisong', 'iosevka'],
    sample: 'const 宽度对齐 = "字体 font"; // != === <= >=',
    spec: [
      { label: { zh: '拉丁', en: 'Latin' }, value: { zh: 'Sarasa IosevkaNSlab（MonoSlab）', en: 'Sarasa IosevkaNSlab (MonoSlab)' } },
      { label: { zh: '汉字', en: 'CJK' }, value: { zh: '霞鹜新致宋 Opt v1.066', en: 'LXGW NeoZhiSong Plus v1.066' } },
      { label: { zh: '网格', en: 'Grid' }, value: { zh: '严格 2:1（A=500 / 中=1000）', en: 'Strict 2:1 (A=500 / 中=1000)' } },
      { label: { zh: '连字', en: 'Ligatures' }, value: { zh: 'calt + Iosevka dlig 折入', en: 'calt plus Iosevka dlig, folded in' } },
      { label: { zh: '符号宽度', en: 'Symbol widths' }, value: { zh: 'EAW 正确，半宽来自 Sarasa TermSlab', en: 'EAW-correct, half-width donors from Sarasa TermSlab' } },
      OFL,
    ],
    faq: [
      {
        q: { zh: '和霞鹜新致宋有什么区别？', en: 'How is this different from LXGW NeoZhiSong?' },
        a: {
          zh: '新致宋是一套正文宋体，不是等宽字体，也没有西文编程字形和 Nerd 图标。AKR Slab 取它的汉字，配 IosevkaNSlab 的拉丁，锁在 2:1 网格上并补齐图标，是给终端和编辑器用的。',
          en: 'NeoZhiSong is a text Song face: not monospaced, no programming Latin, no icons. AKR Slab takes its CJK, pairs it with IosevkaNSlab Latin, locks both onto a 2:1 grid and patches in Nerd icons — for terminals and editors.',
        },
      },
      {
        q: { zh: '能商用吗？', en: 'Can I use it commercially?' },
        a: {
          zh: '可以。字体按 SIL OFL 1.1 发布，与上游一致；OFL 允许商用，但不允许单独售卖字体本身，衍生版本也要继续用 OFL。',
          en: 'Yes. The fonts ship under SIL OFL 1.1, the same license as upstream. OFL permits commercial use; it does not permit selling the fonts on their own, and derivatives stay under OFL.',
        },
      },
    ],
  },
  {
    id: 'sans',
    product: 'AKR Sans SC NFM',
    dir: 'sans',
    name: { zh: 'AKR Sans 黑', en: 'AKR Sans' },
    tagline: {
      zh: 'Lilex 配 IBM Plex Sans SC，观感最"正常"的一套',
      en: 'Lilex with IBM Plex Sans SC — the most unremarkable one, in a good way',
    },
    intro: {
      zh: 'AKR Sans SC NFM 用 Lilex（IBM Plex Mono 的扩展面，带编程连字）做拉丁，IBM Plex Sans SC 做汉字，网格是 550 / 1100。合并保留了 Lilex 的 GSUB / GPOS / GDEF，所以 calt 连字、stylistic set、character variant 都还在；拉丁单元从原生 600 横向缩到 550，SC 满格轮廓按实测加粗（Regular s=5、Bold s=4）。八套里最不挑人的一套，团队统一字体时通常选它。',
      en: 'AKR Sans SC NFM uses Lilex — IBM Plex Mono extended with programming ligatures — for Latin and IBM Plex Sans SC for CJK, on a 550 / 1100 grid. The merge preserves Lilex\'s GSUB/GPOS/GDEF, so calt ligatures, stylistic sets and character variants all survive; the Latin cell is scaled from a native 600 down to 550, and the SC outlines are emboldened by measurement (s=5 Regular, s=4 Bold). This is the least opinionated of the eight, and usually the one a team standardises on.',
    },
    latin: 'Lilex 2.700',
    cjk: 'IBM Plex Sans SC v1.000',
    grid: '550 / 1100',
    weights: ['Regular', 'Bold'],
    nerd: true,
    upstreams: ['ibm-plex-sans-sc', 'lilex'],
    sample: 'const 宽度对齐 = "字体 font"; // != === <= >=',
    spec: [
      { label: { zh: '拉丁', en: 'Latin' }, value: { zh: 'Lilex 2.700（静态 TTF）', en: 'Lilex 2.700 static TTF' } },
      { label: { zh: '汉字', en: 'CJK' }, value: { zh: 'IBM Plex Sans SC v1.000（hinted）', en: 'IBM Plex Sans SC v1.000, hinted' } },
      { label: { zh: '网格', en: 'Grid' }, value: { zh: '550 / 1100', en: '550 / 1100' } },
      { label: { zh: '图标', en: 'Icons' }, value: { zh: 'Nerd Fonts v3.4.0（--complete）', en: 'Nerd Fonts v3.4.0 (--complete)' } },
      { label: { zh: 'OpenType', en: 'OpenType' }, value: { zh: 'Lilex 的 calt / ss / cv 全部保留', en: 'Lilex calt / ss / cv all preserved' } },
      OFL,
    ],
    faq: [
      {
        q: { zh: '和 IBM Plex Sans SC 有什么区别？', en: 'How is this different from IBM Plex Sans SC?' },
        a: {
          zh: 'Plex Sans SC 是比例字体，西文也不是编程面。AKR Sans 只取它的汉字，拉丁换成带连字的 Lilex，整体锁在 550/1100 的双宽网格上，并补了 Nerd 图标。',
          en: 'Plex Sans SC is proportional and its Latin is not a coding face. AKR Sans keeps only its CJK, swaps in Lilex for Latin, locks everything to a 550/1100 dual-width grid, and patches in Nerd icons.',
        },
      },
      {
        q: { zh: '终端里图标不显示？', en: 'Icons not showing in my terminal?' },
        a: {
          zh: '确认装的是 NFM（Nerd Font Mono）版本，并在终端里把字体名写成 `AKR Sans SC NFM`。部分终端需要重启才会重新扫描字体缓存。',
          en: 'Make sure you installed the NFM (Nerd Font Mono) build and that your terminal\'s font is set to `AKR Sans SC NFM`. Some terminals need a restart before they rescan the font cache.',
        },
      },
    ],
  },
  {
    id: 'round',
    product: 'AKR Round SC NFM',
    dir: 'rounded',
    name: { zh: 'AKR Round 圆体', en: 'AKR Round' },
    tagline: {
      zh: 'Iosevka Curly 配资源圆体，圆角端点一路到底',
      en: 'Iosevka Curly with Resource Han Rounded — soft terminals on both sides',
    },
    intro: {
      zh: 'AKR Round SC NFM 是 Iosevka Curly（ss20 Curly Style，sans 包而非 Slab）配 Resource Han Rounded SC，网格 500 / 1000。选 Curly 的理由很具体：圆体汉字要的是圆角端点和软转角，Iosevka 的其它 stylistic inherit 要么偏 slab 要么偏 DIN 的硬，只有 Curly 这条线跟资源圆体是同一种手感。',
      en: 'AKR Round SC NFM pairs Iosevka Curly (ss20 Curly Style, from the sans package rather than Slab) with Resource Han Rounded SC on a 500 / 1000 grid. The choice of Curly is specific: a rounded CJK face wants rounded terminals and soft corners, and Iosevka\'s other stylistic inherits lean either slab or DIN-hard. Curly is the only one that shares a hand with Resource Han Rounded.',
    },
    latin: 'Iosevka Curly v34.8.0 (ss20)',
    cjk: 'Resource Han Rounded CN v0.990',
    grid: '500 / 1000',
    weights: ['Regular', 'Bold'],
    nerd: true,
    upstreams: ['iosevka', 'resource-han-rounded'],
    sample: 'const 宽度对齐 = "字体 font"; // != === <= >=',
    spec: [
      { label: { zh: '拉丁', en: 'Latin' }, value: { zh: 'Iosevka Curly v34.8.0（ss20 Curly Style）', en: 'Iosevka Curly v34.8.0 (ss20 Curly Style)' } },
      { label: { zh: '汉字', en: 'CJK' }, value: { zh: '资源圆体 Resource Han Rounded CN v0.990', en: 'Resource Han Rounded CN v0.990' } },
      { label: { zh: '网格', en: 'Grid' }, value: { zh: '500 / 1000', en: '500 / 1000' } },
      { label: { zh: '图标', en: 'Icons' }, value: { zh: 'Nerd Fonts v3.4.0', en: 'Nerd Fonts v3.4.0' } },
      OFL,
    ],
    faq: [
      {
        q: { zh: '这就是 Iosevka 的中文版吗？', en: 'Is this "Iosevka with Chinese"?' },
        a: {
          zh: '可以这么理解，但更准确的说法是：拉丁取自 Iosevka Curly，汉字来自资源圆体，两边在 2:1 网格上重新对齐并统一了视觉重量。它不是 Iosevka 官方发布，也不使用 Iosevka 的保留字体名。',
          en: 'Close enough as a mental model, but precisely: the Latin comes from Iosevka Curly, the CJK from Resource Han Rounded, and the two are re-aligned on a 2:1 grid with matched optical weight. It is not an official Iosevka release and does not use Iosevka\'s reserved font name.',
        },
      },
    ],
  },
  {
    id: 'type',
    product: 'AKR Type SC NFM',
    dir: 'typewriter',
    name: { zh: 'AKR Type 打字机', en: 'AKR Type' },
    tagline: {
      zh: 'Courier Prime 配朱雀仿宋，打字机质感的中英混排',
      en: 'Courier Prime with Zhuque Fangsong — typewriter texture, both scripts',
    },
    intro: {
      zh: 'AKR Type SC NFM 用 Courier Prime 的 slab 等宽拉丁配朱雀仿宋，网格 600 / 1200。Courier Prime 原生 UPM 2048、单元 1228，合并时归一到 UPM 1000。朱雀内嵌的 Alegreya 拉丁被整个丢掉，只导入 CJK 范围；朱雀是单一字重，两个产品字重都靠 embolden（Regular 8、Bold 32）去跟 Latin 的竖笔对齐。v1 没有编程连字——Courier Prime 本身就没有。',
      en: 'AKR Type SC NFM pairs Courier Prime\'s slab monospace Latin with Zhuque Fangsong on a 600 / 1200 grid. Courier Prime ships at UPM 2048 with a 1228 cell; the merge normalises it to UPM 1000. Zhuque\'s embedded Alegreya Latin is dropped entirely — only CJK ranges are imported — and since Zhuque is single-weight, both product weights are emboldened (s=8 Regular, s=32 Bold) to match the Latin stems. There are no programming ligatures in v1, because Courier Prime has none.',
    },
    latin: 'Courier Prime v3.018',
    cjk: '朱雀仿宋 Zhuque v0.212',
    grid: '600 / 1200',
    weights: ['Regular', 'Bold'],
    nerd: true,
    upstreams: ['zhuque-fangsong'],
    sample: 'const 宽度对齐 = "字体 font"; // 打字机 typewriter',
    spec: [
      { label: { zh: '拉丁', en: 'Latin' }, value: { zh: 'Courier Prime v3.018（slab，非 Code / Sans）', en: 'Courier Prime v3.018 (slab, not Code or Sans)' } },
      { label: { zh: '汉字', en: 'CJK' }, value: { zh: '朱雀仿宋 v0.212（technical preview）', en: 'Zhuque Fangsong v0.212 (technical preview)' } },
      { label: { zh: '网格', en: 'Grid' }, value: { zh: '600 / 1200', en: '600 / 1200' } },
      { label: { zh: '连字', en: 'Ligatures' }, value: { zh: 'v1 无（上游没有）', en: 'None in v1 — upstream has none' } },
      OFL,
    ],
    faq: [
      {
        q: { zh: '为什么没有连字？', en: 'Why no ligatures?' },
        a: {
          zh: 'Courier Prime 本身不带编程连字，硬加会破坏它的打字机比例。以后可能加的是斜杠零、`1`/`l`/`I`/`|` 的区分度调整，而不是 `=>` 这类合字。',
          en: 'Courier Prime has no programming ligatures, and bolting them on would break its typewriter proportions. What may come later is a slashed zero and better separation between `1`/`l`/`I`/`|` — not `=>`-style ligatures.',
        },
      },
    ],
  },
  {
    id: 'pixel',
    product: 'AKR Pixel SC NFM',
    dir: 'pixel',
    name: { zh: 'AKR Pixel 像素', en: 'AKR Pixel' },
    tagline: {
      zh: '缝合像素字体 12px，连字是手画的',
      en: 'Fusion Pixel 12px, with hand-drawn pixel ligatures',
    },
    intro: {
      zh: 'AKR Pixel SC NFM 基于缝合像素字体 12px 等宽，双宽 600 / 1200（1px = 100 单位）。它的编程连字是手画的像素图，走 calt type-4 GSUB——不是把矢量连字缩下来，那样在 12px 下会糊。Nerd 图标按原样单格贴入。四个区域（SC / TC / JP / KR）是同一份归档里的四个成员，区域轴在这套字体上不额外花成本。',
      en: 'AKR Pixel SC NFM is built on Fusion Pixel 12px monospaced, dual width 600 / 1200 (1px = 100 units). Its programming ligatures are hand-drawn pixel art wired through calt type-4 GSUB — not vector ligatures scaled down, which would smear at 12px. Nerd icons are patched in as-is, one cell each. The four regional flavours (SC / TC / JP / KR) are four members of one pinned archive, so the region axis costs this family nothing.',
    },
    latin: 'Fusion Pixel 12px',
    cjk: 'Fusion Pixel 12px zh_hans',
    grid: '600 / 1200',
    weights: ['Regular'],
    nerd: true,
    upstreams: ['fusion-pixel'],
    sample: 'const 宽度对齐 = "字体 font"; // 像素 pixel',
    spec: [
      { label: { zh: '基底', en: 'Base' }, value: { zh: '缝合像素字体 12px 等宽', en: 'Fusion Pixel Font 12px monospaced' } },
      { label: { zh: '网格', en: 'Grid' }, value: { zh: '600 / 1200（1px = 100 单位）', en: '600 / 1200 (1px = 100 units)' } },
      { label: { zh: '连字', en: 'Ligatures' }, value: { zh: '手画像素连字，calt type-4', en: 'Hand-drawn pixel ligatures, calt type-4' } },
      { label: { zh: '区域', en: 'Regions' }, value: { zh: 'SC / TC / JP / KR', en: 'SC / TC / JP / KR' } },
      OFL,
    ],
    faq: [
      {
        q: { zh: '要在多大字号下用？', en: 'What size should I use it at?' },
        a: {
          zh: '它是 12px 设计的点阵字体，用 12 的整数倍（12 / 24 / 36）最锐利，非整数倍会出现像素不齐。',
          en: 'It is a 12px bitmap-derived design: integer multiples of 12 (12 / 24 / 36) stay sharp, anything in between will show uneven pixels.',
        },
      },
    ],
  },
  {
    id: 'hand',
    product: 'AKR Hand SC NFM',
    dir: 'handwriting',
    name: { zh: 'AKR Hand 楷', en: 'AKR Hand' },
    tagline: {
      zh: '霞鹜文楷配 Monaspace Radon，手写骨架做成等宽编程面',
      en: 'LXGW WenKai with Monaspace Radon — a handwriting skeleton, made monospace',
    },
    intro: {
      zh: 'AKR Hand SC NFM 把霞鹜文楷的汉字和 Monaspace Radon 的拉丁合成编程面：严格 2:1、Nerd 图标、连字默认开。关键的一步是汉字按 Radon 自己的倾角剪切 7.5°——这个角度是从 Radon 的竖笔上量出来的，不是拍脑袋定的；字重配对同样是量出来的（Light 配文楷 Regular，Regular 配 Medium）。这是八套里"最不像代码"的一套，也是最多人第一眼记住的一套。',
      en: 'AKR Hand SC NFM merges LXGW WenKai\'s CJK with Monaspace Radon\'s Latin into a coding face: strict 2:1, Nerd icons, ligatures on by default. The load-bearing step is shearing the CJK by 7.5° to match Radon\'s own lean — an angle measured off Radon\'s stems rather than guessed — and the weight pairing is measured too (Light against WenKai Regular, Regular against Medium). This is the least code-like of the eight, and the one most people remember.',
    },
    latin: 'Monaspace Radon NF v1.400',
    cjk: '霞鹜文楷 LXGW WenKai v1.522',
    grid: '500 / 1000',
    weights: ['Regular', 'Bold'],
    nerd: true,
    upstreams: ['lxgw-wenkai', 'monaspace'],
    sample: 'const 宽度对齐 = "字体 font"; // 文楷 wenkai',
    spec: [
      { label: { zh: '拉丁', en: 'Latin' }, value: { zh: 'Monaspace Radon NF v1.400（预打补丁）', en: 'Monaspace Radon NF v1.400 (pre-patched)' } },
      { label: { zh: '汉字', en: 'CJK' }, value: { zh: '霞鹜文楷 LXGW WenKai v1.522', en: 'LXGW WenKai v1.522' } },
      { label: { zh: '网格', en: 'Grid' }, value: { zh: '严格 2:1（500 / 1000）', en: 'Strict 2:1 (500 / 1000)' } },
      { label: { zh: '汉字倾角', en: 'CJK slant' }, value: { zh: '7.5°，量自 Radon 竖笔', en: '7.5°, measured from Radon stems' } },
      { label: { zh: '连字', en: 'Ligatures' }, value: { zh: 'liga + calt，ss01–ss10 折入 calt', en: 'liga + calt, ss01–ss10 folded into calt' } },
      OFL,
    ],
    faq: [
      {
        q: { zh: '和霞鹜文楷有什么区别？', en: 'How is this different from LXGW WenKai?' },
        a: {
          zh: '文楷是比例排版字体，西文用的是它自带的一套，没有等宽、没有 2:1、没有 Nerd 图标。AKR Hand 取它的汉字，拉丁换成 Monaspace Radon，把汉字剪切 7.5° 对上 Radon 的倾角，再锁进 2:1 网格。它是文楷的衍生产品，不是文楷的重新发布。',
          en: 'WenKai is a proportional text face with its own Latin: no monospacing, no 2:1, no icons. AKR Hand takes its CJK, swaps in Monaspace Radon for Latin, shears the CJK 7.5° to match Radon\'s lean, and locks it to a 2:1 grid. It is a derivative of WenKai, not a re-release of it.',
        },
      },
      {
        q: { zh: '要读正文，不写代码，用哪个？', en: 'I want to read prose, not code — which one?' },
        a: {
          zh: '用 AKR Hand SC Text。它去掉了 2:1 声明和 Nerd 图标，保留上游 hinting，行框按排版而不是终端来设，还多一个 Light。',
          en: 'Use AKR Hand SC Text. It drops the 2:1 declaration and the icons, keeps upstream hinting, uses a typographic line box instead of a terminal-tight one, and adds a Light weight.',
        },
      },
    ],
  },
  {
    id: 'hand-text',
    product: 'AKR Hand SC Text',
    dir: 'handwriting',
    name: { zh: 'AKR Hand Text 楷·正文', en: 'AKR Hand Text' },
    tagline: {
      zh: '同一副文楷骨架，但这套是拿来读的',
      en: 'The same WenKai skeleton, tuned for reading instead of terminals',
    },
    intro: {
      zh: 'AKR Hand SC Text 和 AKR Hand SC NFM 共享汉字剪切和光学字重匹配，其余全部相反：不声明 2:1，主动清掉 isFixedPitch 和 PANOSE 的等宽标记（不然 macOS Core Text、Chromium、VS Code 的"仅等宽"字体列表会把它当终端字体列出来），不打 Nerd 补丁，不动 East_Asian_Width，保留上游 hinting，行框按排版给（gap 200、1.30 em），并且多一个 Light。',
      en: 'AKR Hand SC Text shares the CJK shear and the optical weight matching with AKR Hand SC NFM, and reverses everything else: no 2:1 declaration; isFixedPitch and the PANOSE monospace flag are actively cleared (otherwise macOS Core Text, Chromium and VS Code would list it in their monospace-only pickers as a terminal font it is not); no Nerd patch; East_Asian_Width left alone; upstream hinting kept; a typographic line box (gap 200, 1.30 em); and a Light weight.',
    },
    latin: 'Monaspace Radon v1.400 (plain)',
    cjk: '霞鹜文楷 LXGW WenKai v1.522',
    grid: '比例（非等宽）',
    weights: ['Light', 'Regular', 'Bold'],
    nerd: false,
    upstreams: ['lxgw-wenkai', 'monaspace'],
    sample: '正文阅读用的一套，中英混排 reading face',
    spec: [
      { label: { zh: '拉丁', en: 'Latin' }, value: { zh: 'Monaspace Radon v1.400（无 Nerd 的普通静态版）', en: 'Monaspace Radon v1.400, plain static build' } },
      { label: { zh: '汉字', en: 'CJK' }, value: { zh: '霞鹜文楷 LXGW WenKai v1.522', en: 'LXGW WenKai v1.522' } },
      { label: { zh: '等宽标记', en: 'Mono flags' }, value: { zh: '主动清除（isFixedPitch / PANOSE）', en: 'Actively cleared (isFixedPitch / PANOSE)' } },
      { label: { zh: '行框', en: 'Line box' }, value: { zh: '排版式：gap 200，1.30 em', en: 'Typographic: gap 200, 1.30 em' } },
      { label: { zh: '格式', en: 'Formats' }, value: { zh: 'ttf · woff2 · otf', en: 'ttf · woff2 · otf' } },
      OFL,
    ],
    faq: [
      {
        q: { zh: '能拿来当终端字体吗？', en: 'Can I use it as a terminal font?' },
        a: {
          zh: '不建议。它没有 2:1 声明，也没有 Nerd 图标，终端里会错位。终端请用 AKR Hand SC NFM。',
          en: 'Not recommended: no 2:1 declaration and no icons, so terminal columns will drift. Use AKR Hand SC NFM there.',
        },
      },
    ],
  },
  {
    id: 'casual',
    product: 'AKR Casual SC Dual',
    dir: 'casual',
    name: { zh: 'AKR Casual 随手', en: 'AKR Casual' },
    tagline: {
      zh: 'Recursive Mono Casual 配悠哉，不打 Nerd 补丁的双宽面',
      en: 'Recursive Mono Casual with Yozai — dual width, no Nerd patch',
    },
    intro: {
      zh: 'AKR Casual SC Dual 是 Recursive Mono Casual 拉丁配悠哉 Yozai 汉字，严格 2:1，倾角 0°（Recursive Casual 本身就是直立的）。字重按实测竖笔配：Regular 用悠哉 Regular 加 s=10，Bold 用 Medium 加 s=20。v0.1 不打 Nerd 补丁——所以产品名末尾是 Dual 不是 NFM。',
      en: 'AKR Casual SC Dual pairs Recursive Mono Casual Latin with Yozai CJK on a strict 2:1 grid, at 0° slant (Recursive Casual is upright). Weights are matched by measured stems: Regular uses Yozai Regular with s=10, Bold uses Medium with s=20. There is no Nerd patch in v0.1 — which is why the product name ends in Dual rather than NFM.',
    },
    latin: 'Recursive Mono Casual v1.085',
    cjk: '悠哉 Yozai v0.868',
    grid: '500 / 1000',
    weights: ['Regular', 'Bold'],
    nerd: false,
    upstreams: ['yozai', 'recursive'],
    sample: 'const 宽度对齐 = "字体 font"; // 悠哉 yozai',
    spec: [
      { label: { zh: '拉丁', en: 'Latin' }, value: { zh: 'Recursive Mono Casual v1.085', en: 'Recursive Mono Casual v1.085' } },
      { label: { zh: '汉字', en: 'CJK' }, value: { zh: '悠哉 Yozai v0.868', en: 'Yozai v0.868' } },
      { label: { zh: '网格', en: 'Grid' }, value: { zh: '严格 2:1（500 / 1000）', en: 'Strict 2:1 (500 / 1000)' } },
      { label: { zh: '图标', en: 'Icons' }, value: { zh: 'v0.1 不含 Nerd 图标', en: 'No Nerd icons in v0.1' } },
      OFL,
    ],
    faq: [
      {
        q: { zh: '为什么叫 Dual 不叫 NFM？', en: 'Why "Dual" and not "NFM"?' },
        a: {
          zh: '产品名按 `AKR <Style> <Region> <Variant>` 来编码事实：NFM 表示打过 Nerd 补丁的编程面，Dual 表示双宽但不含图标。这一套目前是后者。',
          en: 'Product names encode facts as `AKR <Style> <Region> <Variant>`: NFM means a Nerd-patched coding face, Dual means dual-width without icons. This one is currently the latter.',
        },
      },
    ],
  },
]

export function familyById(id: string): Family | undefined {
  return families.find(f => f.id === id)
}
