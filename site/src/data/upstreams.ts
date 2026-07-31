// Upstream landing pages.
//
// These exist to be found by people searching for the upstream font, and they
// have exactly one job: say what AKR did with that font, how it differs, and
// where the original lives. Two rules hold everywhere on these pages:
//
//   1. The page never presents itself as the upstream's official site, and the
//      upstream's own name is never used as an AKR product name (OFL reserved
//      font names, and plain honesty).
//   2. Every page links to the upstream project first, before it links to us.

import type { Bilingual } from './families'

export interface Upstream {
  slug: string
  /** The name people actually search for. */
  name: Bilingual
  /** Other spellings worth having in the copy — not a keyword dump. */
  aliases: string[]
  url: string
  /** Whose work this is, credited by name where the project states one. */
  author: string
  license: string
  /** What the upstream font is, in its own right. */
  what: Bilingual
  /** What AKR does with it, and what that changes. */
  what_akr_does: Bilingual
  /** Family ids that use this upstream. */
  families: string[]
}

export const upstreams: Upstream[] = [
  {
    slug: 'lxgw-wenkai',
    name: { zh: '霞鹜文楷', en: 'LXGW WenKai' },
    aliases: ['LXGW WenKai', '文楷', 'lxgw wenkai mono', '霞鹜文楷等宽'],
    url: 'https://github.com/lxgw/LxgwWenKai',
    author: 'lxgw (落霞与孤鹜)',
    license: 'SIL OFL 1.1',
    what: {
      zh: '霞鹜文楷是基于 Klee One 的开源楷体，笔锋保留了手写的起收，是中文开源字体里最常被用于正文和电子书的一套。它是比例字体，自带一套西文。',
      en: 'LXGW WenKai is an open-source Kai (regular script) face derived from Klee One, keeping the entry and exit strokes of handwriting. It is one of the most widely used Chinese open-source faces for body text and e-books. It is proportional, and ships its own Latin.',
    },
    what_akr_does: {
      zh: '文楷本身不是等宽字体，直接拿去写代码会错位、也没有 Nerd 图标。AKR 取它的汉字，配 Monaspace Radon 的拉丁，把汉字按 Radon 的倾角剪切 7.5°，锁进严格 2:1 网格，打上 Nerd 图标，做成 AKR Hand SC NFM；另有一套 AKR Hand SC Text 保留排版行框、去掉等宽标记，专门拿来读。',
      en: 'WenKai is not monospaced: used directly for code, columns drift, and there are no Nerd icons. AKR takes its CJK, pairs it with Monaspace Radon Latin, shears the CJK 7.5° to match Radon\'s lean, locks it onto a strict 2:1 grid and patches in Nerd icons — that is AKR Hand SC NFM. A second product, AKR Hand SC Text, keeps a typographic line box and drops the monospace flags, for reading.',
    },
    families: ['hand', 'hand-text'],
  },
  {
    slug: 'lxgw-neozhisong',
    name: { zh: '霞鹜新致宋', en: 'LXGW NeoZhiSong' },
    aliases: ['LXGW NeoZhiSong', '新致宋', '霞鹜新致宋 Plus'],
    url: 'https://github.com/lxgw/LxgwNeoZhiSong',
    author: 'lxgw (落霞与孤鹜)',
    license: 'SIL OFL 1.1',
    what: {
      zh: '霞鹜新致宋是基于 IPAmj 明朝体衍生的开源宋体，字面偏方正，笔画起收明确，适合长文阅读。',
      en: 'LXGW NeoZhiSong is an open-source Song/Ming face derived from IPAmj Mincho: squarer counters, clearly articulated stroke ends, made for long-form reading.',
    },
    what_akr_does: {
      zh: 'AKR 用它的 Opt 版汉字配 Sarasa 的 IosevkaNSlab 拉丁，按实测竖笔加粗对齐视觉重量，锁进 2:1 网格并补 Nerd 图标，得到 AKR Slab SC NFM——宋体在编程字体里少见，长时间读代码时字形辨识度反而更高。',
      en: 'AKR pairs its Opt CJK with Sarasa\'s IosevkaNSlab Latin, emboldens by measured stem width to match optical weight, locks it to a 2:1 grid and patches in Nerd icons, producing AKR Slab SC NFM. A Song face is unusual in a coding font, and turns out to be easier to disambiguate over a long session.',
    },
    families: ['slab'],
  },
  {
    slug: 'iosevka',
    name: { zh: 'Iosevka', en: 'Iosevka' },
    aliases: ['Iosevka CJK', 'Iosevka 中文', 'Iosevka Curly', 'Sarasa Gothic 更纱黑体'],
    url: 'https://github.com/be5invis/Iosevka',
    author: 'Renzhi Li (be5invis)',
    license: 'SIL OFL 1.1',
    what: {
      zh: 'Iosevka 是窄身等宽编程字体，以极高的可配置性著称（stylistic set、character variant、各种 inherit 预设）。更纱黑体 Sarasa Gothic 是它与思源系汉字的官方合并版。',
      en: 'Iosevka is a narrow monospace coding typeface known for how configurable it is (stylistic sets, character variants, a library of inherit presets). Sarasa Gothic is its official merge with Source Han-derived CJK.',
    },
    what_akr_does: {
      zh: 'AKR 有两套用到 Iosevka 线：AKR Round SC NFM 用 Iosevka Curly（ss20）配资源圆体——选 Curly 是因为圆体汉字要的是圆角端点，其它 inherit 要么偏 slab 要么偏 DIN 的硬；AKR Slab SC NFM 用 Sarasa 的 IosevkaNSlab 配新致宋。两套都不是 Iosevka 官方发布，也不使用它的保留字体名。',
      en: 'Two AKR products sit on the Iosevka line. AKR Round SC NFM uses Iosevka Curly (ss20) with Resource Han Rounded — Curly because a rounded CJK face wants rounded terminals, where the other inherits lean slab or DIN-hard. AKR Slab SC NFM uses Sarasa\'s IosevkaNSlab with NeoZhiSong. Neither is an official Iosevka release, and neither uses its reserved font name.',
    },
    families: ['round', 'slab'],
  },
  {
    slug: 'ibm-plex-sans-sc',
    name: { zh: 'IBM Plex Sans SC', en: 'IBM Plex Sans SC' },
    aliases: ['IBM Plex Sans SC', 'Plex Sans SC 等宽', 'IBM Plex 中文'],
    url: 'https://github.com/IBM/plex',
    author: 'IBM',
    license: 'SIL OFL 1.1',
    what: {
      zh: 'IBM Plex Sans SC 是 IBM 企业字体家族的简体中文成员，字面开阔、结构中性，是少数带完整 hinting 的开源中文黑体。它是比例字体。',
      en: 'IBM Plex Sans SC is the Simplified Chinese member of IBM\'s corporate type family: open counters, neutral construction, and one of the few open Chinese sans faces shipping complete hinting. It is proportional.',
    },
    what_akr_does: {
      zh: 'AKR Sans SC NFM 只取它的汉字，拉丁换成 Lilex（IBM Plex Mono 的扩展面，带编程连字），拉丁单元从 600 缩到 550、汉字 1100，SC 满格轮廓按实测加粗，再补 Nerd 图标。Lilex 的 GSUB/GPOS/GDEF 整套保留，所以连字和 stylistic set 都还能用。',
      en: 'AKR Sans SC NFM keeps only its CJK, swapping in Lilex — IBM Plex Mono extended with programming ligatures — for Latin. The Latin cell scales 600 → 550 against a 1100 CJK cell, the SC outlines are emboldened by measurement, and Nerd icons are patched in. Lilex\'s GSUB/GPOS/GDEF survive intact, so ligatures and stylistic sets still work.',
    },
    families: ['sans'],
  },
  {
    slug: 'lilex',
    name: { zh: 'Lilex', en: 'Lilex' },
    aliases: ['Lilex 中文', 'Lilex Nerd Font', 'IBM Plex Mono 连字'],
    url: 'https://github.com/mishamyrt/Lilex',
    author: 'Misha Myrt',
    license: 'SIL OFL 1.1',
    what: {
      zh: 'Lilex 是在 IBM Plex Mono 基础上扩展的编程字体，加了成套的编程连字和 OpenType 特性，保持了 Plex 的骨架。',
      en: 'Lilex extends IBM Plex Mono into a programming face: a full set of coding ligatures and OpenType features, on Plex\'s skeleton.',
    },
    what_akr_does: {
      zh: 'AKR Sans SC NFM 用它做拉丁侧，配 IBM Plex Sans SC 的汉字——两边同源于 Plex，骨架本来就合。合并保留 Lilex 的全部 OpenType 表，网格 550 / 1100。',
      en: 'AKR Sans SC NFM uses it for the Latin side against IBM Plex Sans SC — both descend from Plex, so the skeletons already agree. The merge preserves all of Lilex\'s OpenType tables on a 550 / 1100 grid.',
    },
    families: ['sans'],
  },
  {
    slug: 'resource-han-rounded',
    name: { zh: '资源圆体', en: 'Resource Han Rounded' },
    aliases: ['Resource Han Rounded', '资源圆体', '圆体 等宽', '思源圆体'],
    url: 'https://github.com/CyanoHao/Resource-Han-Rounded',
    author: 'CyanoHao',
    license: 'SIL OFL 1.1',
    what: {
      zh: '资源圆体是把思源黑体的转角圆角化得到的开源圆体，是中文开源圆体里完成度最高的一套之一。',
      en: 'Resource Han Rounded is an open rounded face produced by rounding the corners of Source Han Sans — one of the most complete open Chinese rounded faces available.',
    },
    what_akr_does: {
      zh: 'AKR Round SC NFM 用它做汉字，配 Iosevka Curly（ss20）的拉丁，网格 500 / 1000，打 Nerd 图标。选 Curly 就是为了让拉丁的圆角端点跟它对得上。',
      en: 'AKR Round SC NFM uses it for CJK against Iosevka Curly (ss20) Latin, on a 500 / 1000 grid with Nerd icons. Curly was chosen precisely so the Latin terminals round the same way.',
    },
    families: ['round'],
  },
  {
    slug: 'zhuque-fangsong',
    name: { zh: '朱雀仿宋', en: 'Zhuque Fangsong' },
    aliases: ['朱雀仿宋', 'Zhuque Fangsong', '仿宋 编程字体'],
    url: 'https://github.com/TrionesType/zhuque',
    author: 'Triones Type (朱雀 / 三体字库)',
    license: 'SIL OFL 1.1',
    what: {
      zh: '朱雀仿宋是开源仿宋体，笔画细、斜度明显，公文与排版里的仿宋在开源领域长期缺位，它填的是这个空。目前是 technical preview。',
      en: 'Zhuque Fangsong is an open-source Fangsong face — thin strokes, a pronounced slant. Fangsong has long been missing from open type, and this fills that gap. It is currently a technical preview.',
    },
    what_akr_does: {
      zh: 'AKR Type SC NFM 用它做汉字，配 Courier Prime 的 slab 等宽拉丁，网格 600 / 1200。朱雀内嵌的 Alegreya 拉丁被整个丢掉；朱雀是单一字重，两个产品字重靠 embolden 去对 Latin 的竖笔。',
      en: 'AKR Type SC NFM uses it for CJK against Courier Prime\'s slab monospace Latin on a 600 / 1200 grid. Zhuque\'s embedded Alegreya Latin is dropped entirely, and since Zhuque is single-weight, both product weights are emboldened to match the Latin stems.',
    },
    families: ['type'],
  },
  {
    slug: 'fusion-pixel',
    name: { zh: '缝合像素字体', en: 'Fusion Pixel Font' },
    aliases: ['Fusion Pixel', '缝合像素字体', '像素字体 中文', '12px 点阵'],
    url: 'https://github.com/TakWolf/fusion-pixel-font',
    author: 'TakWolf',
    license: 'SIL OFL 1.1',
    what: {
      zh: '缝合像素字体是把多套开源像素字体拼合成的泛中日韩点阵字体，12px 一档覆盖简繁日韩，是中文像素字体里覆盖最全的一套。',
      en: 'Fusion Pixel Font stitches several open pixel fonts into a pan-CJK bitmap-derived family; at 12px it covers Simplified, Traditional, Japanese and Korean — the broadest coverage of any Chinese pixel font.',
    },
    what_akr_does: {
      zh: 'AKR Pixel SC NFM 基于它的 12px 等宽档，双宽 600 / 1200，加了手画的像素编程连字（calt type-4，不是把矢量连字缩下来），并贴入单格 Nerd 图标。SC / TC / JP / KR 四个区域都有。',
      en: 'AKR Pixel SC NFM builds on its 12px monospaced tier at 600 / 1200 dual width, adds hand-drawn pixel programming ligatures (calt type-4, not scaled-down vector ligatures), and patches in single-cell Nerd icons. All four regions — SC / TC / JP / KR — are released.',
    },
    families: ['pixel'],
  },
  {
    slug: 'yozai',
    name: { zh: '悠哉字体', en: 'Yozai' },
    aliases: ['悠哉', 'Yozai', '悠哉字体', '手写 等宽'],
    url: 'https://github.com/lxgw/yozai-font',
    author: 'lxgw (落霞与孤鹜)',
    license: 'SIL OFL 1.1',
    what: {
      zh: '悠哉是基于 Yasashisa Gothic 的开源中文字体，圆润、随手，介于黑体和手写之间。',
      en: 'Yozai is an open Chinese face derived from Yasashisa Gothic: soft, casual, sitting between a gothic and handwriting.',
    },
    what_akr_does: {
      zh: 'AKR Casual SC Dual 用它做汉字，配 Recursive Mono Casual 的拉丁，严格 2:1、倾角 0°，字重按实测竖笔配（Regular 加 s=10，Bold 用 Medium 加 s=20）。v0.1 不打 Nerd 补丁。',
      en: 'AKR Casual SC Dual uses it for CJK against Recursive Mono Casual Latin: strict 2:1, 0° slant, weights matched by measured stems (Regular +s=10, Bold from Medium +s=20). No Nerd patch in v0.1.',
    },
    families: ['casual'],
  },
  {
    slug: 'monaspace',
    name: { zh: 'Monaspace', en: 'Monaspace' },
    aliases: ['Monaspace Radon', 'Monaspace 中文', 'GitHub Monaspace CJK'],
    url: 'https://github.com/githubnext/monaspace',
    author: 'GitHub Next',
    license: 'SIL OFL 1.1',
    what: {
      zh: 'Monaspace 是 GitHub Next 做的编程字体超家族，五种风格共享度量。其中 Radon 是手写风格的一支，带轻微倾斜。',
      en: 'Monaspace is GitHub Next\'s coding superfamily — five styles sharing metrics. Radon is its handwriting-flavoured member, with a slight lean.',
    },
    what_akr_does: {
      zh: 'AKR Hand 用 Radon 做拉丁，配霞鹜文楷的汉字，并把汉字按 Radon 竖笔量出的 7.5° 剪切，让两种手写感朝同一个方向倒。编程面用预打 Nerd 补丁的 NF 版，正文面用普通静态版。',
      en: 'AKR Hand uses Radon for Latin against LXGW WenKai CJK, shearing the CJK by 7.5° — an angle measured off Radon\'s own stems — so both handwriting styles lean the same way. The coding face uses the pre-patched NF build; the reading face uses the plain static one.',
    },
    families: ['hand', 'hand-text'],
  },
  {
    slug: 'recursive',
    name: { zh: 'Recursive', en: 'Recursive' },
    aliases: ['Recursive Mono', 'Recursive Casual', 'Recursive 中文'],
    url: 'https://github.com/arrowtype/recursive',
    author: 'Stephen Nixon / ArrowType',
    license: 'SIL OFL 1.1',
    what: {
      zh: 'Recursive 是一套可变字体，从 Linear 到 Casual、从 Sans 到 Mono 连续可调，Mono Casual 是其中偏随手的等宽一支。',
      en: 'Recursive is a variable family that moves continuously from Linear to Casual and Sans to Mono. Mono Casual is its loose, handwritten-leaning monospace corner.',
    },
    what_akr_does: {
      zh: 'AKR Casual SC Dual 用 Recursive Mono Casual 的静态实例做拉丁，配悠哉的汉字，2:1、0° 倾角、实测字重匹配。',
      en: 'AKR Casual SC Dual uses a static instance of Recursive Mono Casual for Latin against Yozai CJK: 2:1, 0° slant, weights matched by measurement.',
    },
    families: ['casual'],
  },
]

export function upstreamBySlug(slug: string): Upstream | undefined {
  return upstreams.find(u => u.slug === slug)
}
