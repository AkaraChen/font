# 构建管线现代化方案（KIT-263）

> 状态：**方案（proposal）**，尚未实施。目的是先把边界和目标形态定下来，再分阶段落地。

## 1. 现状盘点

7 个字体家族（`serif` `sans` `rounded` `typewriter` `pixel` `handwriting` `casual`），
共 **3820 行 shell + 10260 行 Python**，没有任何共享代码单元 —— 复用完全靠**复制**和**跨目录裸路径引用**。

### 1.1 字节级完全相同的文件

| 文件 | 份数 | 位置 |
| --- | --- | --- |
| `fix-nerd-widths.py` | 4 | pixel / rounded / sans / typewriter |
| `fix-terminal-metrics.py` | 4 | pixel / rounded / sans / typewriter（serif 已漂移） |
| `verify-2to1.py` | 3 | rounded / sans / typewriter（serif 已漂移 604 行） |
| `narrow-symbol-widths.py` | 3 | rounded / sans / typewriter（serif 已漂移） |
| `rename_nerd_family.py` | 3 | rounded / sans / typewriter（serif / pixel 已漂移） |

**17 份文件可以直接删到 5 份。**

### 1.2 结构相同、只差名字的文件

- `common.sh` × 7：唯一实质差异是 `SANS_ROOT` / `TYPEWRITER_ROOT` / … 这个变量名。
  其余差异全是**漂移**：`download_zip` vs `download_file`、venv 里装不装 `pathops`、装不装 `Pillow`、
  报错文案。sans 的 `01-fetch-sources.sh` 甚至在脚本里**重新定义了一遍** `download_file`，
  因为它那份 `common.sh` 里没有 —— 而 typewriter 那份有。
- `build.sh` × 7：完全是"依次调用 `01-` … `0N-`"，只有步骤列表不同。
- `nerd-patch.sh` × 4：sans / rounded / typewriter / pixel 之间的 diff **只有产品 stem 字符串和路径前缀**。
- `package-release.sh` × 7 / `NN-verify.sh` × 5：同上，差异集中在 stem、license 文件名、README 文案。
- `merge_*.py` × 4（484–614 行）：共享 15 个同名同签名函数（`scale_glyph_x` `scale_gpos_x`
  `copy_glyph_deep` `rebuild_cmap` `rename_family` `unify_metrics` `center_advance`
  `ensure_glyph_slot` `set_cjk_metrics` `is_cjk_side` …）。sans↔rounded 的 diff 里绝大部分是注释和
  一个 `sc.` / `cjk.` 前缀。

### 1.3 跨家族耦合（最危险的一类）

6 个家族通过**硬编码相对路径**依赖 `serif/`：

```
sans/scripts/02-merge.sh:35        → ${REPO_ROOT}/serif/tools/embolden_cjk.py
rounded/scripts/02-prepare-cjk.sh  → ${REPO_ROOT}/serif/tools/embolden_cjk.py
typewriter/scripts/02-prepare-cjk.sh → 同上
handwriting/scripts/06-verify.sh   → ${REPO_ROOT}/serif/scripts/verify-2to1.py
handwriting/scripts/05-expand-ligatures.sh → ${REPO_ROOT}/serif/scripts/expand-default-ligatures.py
casual/scripts/common.sh           → SERIF_TOOLS + HANDWRITING_SCRIPTS
sans/scripts/04-verify.sh:48       → sys.path.insert(0, os.environ["SERIF_TOOLS"])
```

最典型的是 `casual/scripts/05-verify.sh`：

```bash
if   [[ -f "${REPO_ROOT}/serif/scripts/verify-2to1.py"   ]]; then ...
elif [[ -f "${REPO_ROOT}/rounded/scripts/verify-2to1.py" ]]; then ...
else die "no verify-2to1.py found under serif/ or rounded/"
```

在运行时靠文件系统考古来找共享库。`serif/` 已经**事实上是公共库**了，只是没有被承认，
也没有接口约定 —— 所以任何人改 serif 都可能在不知情的情况下弄坏另外 6 个家族。

### 1.4 其他

- **CI 几乎不存在**：只有一个 `release-nfm.yml`，serif 专用，而且不是从源码构建，
  是"下载上一个 tag 的产物 → 后处理 → 重新发布"。其余 6 个家族**没有任何自动化验证**。
- **区域变体为零**：全部只有 SC。没有 TC / HK / JP 路径。
- **`pins.env` 其实已经是个不错的清单**，但是扁平 shell KV，把 5 类语义混在一起：
  上游 pin、产品度量、命名、垂直度量、校准常数。

---

## 2. 目标形态

```
justfile                    # 顶层入口
pyproject.toml              # 单一 uv workspace，锁定 fonttools / skia-pathops 版本
uv.lock

lib/fontkit/                # ★ 唯一的共享构建库（Python 包）
  manifest.py               # 读 + 校验 font.toml（pydantic）
  fetch.py                  # 下载 / sha256 / zip 成员抽取（含 HTTP range，来自 handwriting）
  scale.py                  # scale_glyph_x / scale_gpos_x / scale_latin_font / scale_upem
  merge.py                  # copy_glyph_deep / rebuild_cmap / ensure_glyph_slot / center_advance
  naming.py                 # rename_family / rename_nerd_family
  metrics.py                # unify_metrics / fix-terminal-metrics / mono flags
  eaw.py                    # narrow-symbol-widths / narrow_ambiguous
  nerd.py                   # patcher driver（docker|fontforge）+ fix-nerd-widths
  ligatures.py              # ss** → calt 折叠 / dlig → calt 展开
  measure.py                # measure_stroke_width / embolden_cjk / measure-slant
  verify/                   # 可组合的检查规则
  package.py                # zip + README + license
  cli.py                    # `fontkit <verb>`

fonts/<family>/
  font.toml                 # ★ 取代 pins.env，声明式清单
  steps/                    # ★ 只放本家族真正独有的变换
  patches/ licenses/ samples/
```

`serif/tools/` 里那些被 6 个家族偷偷 import 的东西，正式升格为 `lib/fontkit/measure.py`。

### 2.1 边界规则（需求 2 的答案）

**必须共享，任何家族不得复制**：

- 源获取、哈希校验、zip 成员抽取
- 工具链/venv 供给
- 字形拷贝、cmap 重建、advance 居中数学、GPOS 横向缩放
- 家族命名 / name table 改写
- 垂直度量应用、mono 标志（`post.isFixedPitch`、PANOSE `bProportion`）
- Nerd patch + PUA 宽度修复
- EAW 宽度修正
- 校验规则**的实现**（阈值是数据，可以按家族给）
- 打包 / release notes / license 装配 / 样张渲染

**允许家族自持**（在 `font.toml` 里显式声明为 `steps.custom`）：

- 上游特有的获取方式：serif 的 Sarasa git clone + quilt 补丁栈（唯一真正特殊的家族，
  它跑的是上游完整构建工具链）
- 源特有的形状级变换：pixel 的像素化连字绘制、handwriting 的 CJK 倾斜 7.5°、
  typewriter 的 hinting 剥离
- 所有**校准常数**：永远是 `font.toml` 里的数据，永远不是代码

**四条硬规则**：

1. 家族本地步骤**不得重新实现**共享能力。需要变体就通过 `font.toml` 参数扩展共享实现。
2. 家族本地步骤是 `fonts/<f>/steps/` 下的一个 Python 模块，import `fontkit`；
   bash 只存在于 `just` recipe 里。
3. **任何家族不得引用另一个家族的路径。** 违反即 CI 失败（一条 grep 就能守住）。
4. **Rule of two**：同一个本地步骤出现第二次，就必须上移进 `fontkit`。不等第三次。

---

## 3. coding / 非 coding 拆分（需求 3）

引入与家族正交的**构建 profile**。核心判断依据是：**这条约束服务于终端的等宽单元格，
还是服务于阅读？** 前者只属于 coding，后者两边都要。

| 约束 | `coding` | `text` | 理由 |
| --- | --- | --- | --- |
| 严格 2:1 EN:CJK | **硬性 gate** | 不适用 | 终端按格子排版；正文里强行 2:1 会让拉丁文过宽、字距难看 |
| `post.isFixedPitch` / PANOSE mono | 是 | 否 | 正文场景不应该被宿主当成等宽字体 |
| EAW 驱动的半宽/全宽 | 是 | 否 | Ambiguous（`…` `“ ”` `·`）在正文里应保持 CJK 全宽 |
| Nerd Font patch | 是（NFM） | 否 | 图标是终端需求 |
| 连字默认开（`calt` 折叠） | 是 | 否 | 正文只保留 `liga` / `kern` |
| 拉丁侧 GPOS / kern | 被等宽格子压平 | **保留** | 正文的字距质量来自 kern |
| 上游 hinting | 丢弃 | 尽量保留 | |
| 行度量 | 终端紧排（如 hhea 950/-250） | 排版型（typo asc/desc + line gap） | |
| **光学笔画粗细对齐（中英）** | **是** | **是** | 与场景无关，是"中文比英文细"这个缺陷本身 |
| **中英基线 / 视觉重心对齐** | **是** | **是** | 同上 |
| 源 pin / 可复现性 / 命名 / 授权装配 | 是 | 是 | 与场景无关 |

关键点正是需求里写的那条：**严格 2:1 是 coding-only 的，光学笔画对齐是两者都要的。**
所以这两件事必须在代码里就是两个独立的步骤，不能像现在这样都埋在 `merge_*.py` 的
`unify_metrics` 里。

并非所有家族在两个 profile 下都成立，在 `font.toml` 里显式声明：

| 家族 | coding | text | 说明 |
| --- | --- | --- | --- |
| pixel | ✅ | ❌ | 12px 点阵，正文无意义 |
| serif / sans / rounded / typewriter | ✅ | 🟡 待定 | 技术上可行，先确认有没有实际用户 |
| handwriting / casual | ✅ | ✅ | 文楷 / 悠哉本来就是正文向 CJK，text 版最有价值 |

> ⚠️ **需要你拍板**：`text` profile 目前没有已知消费者。如果只是"技术上做得到"，
> 它就是纯负债。建议**先只给 handwriting 落一个 text 版**验证需求，再决定是否铺开。

---

## 4. 语言 / 地区变体（需求 4）

加入 `region` 轴：`sc` / `tc` / `hk` / `jp` / `kr`。它选择的是**不同的 CJK 供体资源**
（外加可能不同的 `locl` / cmap），拉丁侧和所有度量逻辑完全复用。

上游可得性决定了每个家族能支持到哪：

| 家族 | CJK 源 | sc | tc | hk | jp | kr | 备注 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| sans | IBM Plex Sans SC/TC/JP/KR | ✅ | ✅ | ❌ | ✅ | ✅ | 上游齐全，**首个落地对象** |
| pixel | fusion-pixel `zh_hans`/`zh_hant`/`ja`/`ko` | ✅ | ✅ | ❌ | ✅ | ✅ | **同一个 zip 里的不同成员，成本最低** |
| rounded | Resource Han Rounded CN/TW/HK/JP/KR | ✅ | ✅ | ✅ | ✅ | ✅ | |
| handwriting | LXGW WenKai / WenKai TC | ✅ | ✅ | ❌ | ❌ | ❌ | |
| serif | LXGW Neo ZhiSong（仅 SC） | ✅ | ❌ | ❌ | ❌ | ❌ | 拉丁侧 Sarasa 本身有 SC/TC/HC/J/K，但 CJK 供体卡住了；要 TC 得换供体 |
| typewriter | 朱雀仿宋（仅 SC） | ✅ | ❌ | ❌ | ❌ | ❌ | 上游未提供，明确声明不支持 |
| casual | Yozai（仅 SC） | ✅ | ❌ | ❌ | ❌ | ❌ | 同上 |

构建矩阵 = **家族 × profile × region × 字重**。用命令控制基数：

- `just build sans` → 默认（`coding` × `sc`），日常开发用
- `just build sans coding tc` → 单点
- `just build-all` → 只构建 `font.toml` 中 `[build.matrix]` **显式声明**的组合

> ⚠️ **需要你拍板**：加了 region 轴之后的**命名方案**。现在的家族名把地区烤死在里面了
> （`LilexSansSC NFM`），加 TC 就得改名。而且 `pins.env` 里已经记了两条约束：
> Windows name ID 1 ≤ 31 字符、以及多处 OFL RFN（保留字体名）警告。
> 建议 `<Latin><CJK> <REGION> <PROFILE>` 形式，但这属于产品决策，**Phase 6 之前必须定**。

---

## 5. `just` 接口

用 `just`（≥1.31，用 `mod` 做家族子模块），不用 make。

```
just                          # 列出所有 recipe
just doctor                   # 工具预检：uv / curl / unzip / 7z / fontforge|docker
just matrix                   # 打印声明的构建矩阵

just fetch    FAMILY [REGION]
just build    FAMILY [PROFILE=coding] [REGION=sc]
just build-all
just verify   FAMILY [PROFILE] [REGION]
just calibrate FAMILY         # 笔画测量 → 输出建议值（人工写回 font.toml）
just sample   FAMILY          # 渲染样张 PNG
just package  FAMILY VERSION
just release  FAMILY VERSION  # package + gh release
just clean    [FAMILY]
just fmt / just lint          # ruff + shellcheck
```

**增量性**：`work/` 按 `(family, region)` 分目录；每一步幂等；`fetch` 以 pin 的哈希作为
缓存键，pin 不变就跳过。现在 7 份 `common.sh` 里的 `download_zip` 缓存逻辑已经做对了这件事，
只是抄了 7 遍。

---

## 6. 分阶段落地

每个阶段独立可合并、可回滚。**Phase 0 先建回归网，再动任何重构。**

### Phase 0 — 地基（零行为变更）

- `pyproject.toml`（uv workspace）+ `uv.lock`，锁死 fonttools / skia-pathops 版本
- 顶层 `justfile`，recipe **直接转调现有的 `<family>/scripts/build.sh`**
  —— 立刻拿到新 UX，零风险
- CI：矩阵 workflow，对 7 个家族跑 `just build <family>`
- **指纹基线**：为每个家族的当前产物记录一份*归一化指纹*（advance 表 + name 表 +
  feature list dump，而不是 TTF 的 sha256 —— 后者会被时间戳/工具版本搅乱）。
  这是后面所有重构的判定标准。

> 这一阶段最重要。现在 6 个家族没有任何自动验证，在这种状态下重构 14k 行是在裸奔。

### Phase 1 — 抽走字节相同的文件

- 建 `lib/fontkit/`，把 5 个完全重复的模块搬进去，删掉 17 份拷贝
- 处理 serif 那份漂移了 604 行的 `verify-2to1.py`：把它多出来的检查收进共享实现，用 flag 控制
- Gate：指纹不变

### Phase 2 — 收掉 shell 编排

- `common.sh` × 7 / `build.sh` × 7 / `package-release.sh` × 7 / `nerd-patch` × 4 /
  `verify` × 5 → just recipe + `fontkit` CLI
- **消灭所有跨家族路径引用**，加上守卫这条规则的 CI 检查

### Phase 3 — 清单化

- `pins.env` → `font.toml`，pydantic 校验。分区：
  `[source.latin]` / `[source.cjk.<region>]` / `[grid]` / `[naming]` /
  `[metrics.coding]` / `[metrics.text]` / `[calibration]` / `[nerd]` / `[build.matrix]`

### Phase 4 — 合并引擎统一（风险最高）

- 4 份 `merge_*.py` → 一个由清单驱动的 `fontkit.merge`
- 家族独有部分（handwriting 的 shear/widen、typewriter 的 hint drop、rounded 的 upem scale）
  变成声明式选项或 `steps/` 钩子
- **逐家族一个 PR**，每个都用指纹卡住。不要一次性替换。

### Phase 5 — profile

- 引入 `text` profile 及其 gate；**先只做 handwriting 一个家族**验证需求

### Phase 6 — region

- region 轴 + 矩阵构建；从 sans（Plex 齐全）和 pixel（同 zip 内不同成员）开始
- 前置条件：命名方案已拍板

### Phase 7 — 发布自动化

- 用通用 `release.yml`（输入：family / version / profiles / regions）替换 serif 专用 workflow
- 改成**从源码构建**，而不是现在这种"下载上个 tag 的产物再后处理"

---

## 7. 风险与待决事项

| # | 事项 | 影响 |
| --- | --- | --- |
| 1 | **命名方案**（region 轴 + 31 字符上限 + OFL RFN） | 阻塞 Phase 6，是产品决策不是技术决策 |
| 2 | **`text` profile 有没有真实消费者** | 没有的话就是纯负债，建议先做一个验证 |
| 3 | **可复现性**：fontTools / skia-pathops 版本必须锁死 | 不锁的话指纹会自己漂移，Phase 0 的回归网直接失效 |
| 4 | **Nerd patch 需要 fontforge/docker** | CI 时间成本；考虑缓存已 patch 的产物 |
| 5 | **serif 是唯一真正特殊的家族** | 它跑上游完整构建工具链（node/otfcc + quilt 补丁栈），比其余 6 个重得多。不要为了统一而强行把它塞进通用引擎 —— 它值得一个正式的 `steps.custom` 逃生口 |
| 6 | 重构期间 serif 的既有 release 流程不能断 | Phase 7 之前保留旧 workflow |
