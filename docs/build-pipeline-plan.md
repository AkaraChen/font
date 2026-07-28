# 构建管线现代化方案（KIT-263）

> 状态：**方案（proposal）**，尚未实施。
>
> 修订记录：
> - v1 — just + 自建内容寻址缓存
> - **v2（当前）** — 改用 **Nix flake** 作为构建引擎，`just` 退化为 UX 薄层。
>   region 破坏性改名已获批；`text` profile 需求已确认。

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
- `package-release.sh` × 7 / `NN-verify.sh` × 5：同上。
- `merge_*.py` × 4（484–614 行）：共享 15 个同名同签名函数（`scale_glyph_x` `scale_gpos_x`
  `copy_glyph_deep` `rebuild_cmap` `rename_family` `unify_metrics` `center_advance`
  `ensure_glyph_slot` `set_cjk_metrics` `is_cjk_side` …）。sans↔rounded 的 diff 里绝大部分是注释和
  一个 `sc.` / `cjk.` 前缀。

### 1.3 跨家族耦合

6 个家族通过**硬编码相对路径**依赖 `serif/`：

```
sans/scripts/02-merge.sh            → ${REPO_ROOT}/serif/tools/embolden_cjk.py
rounded/scripts/02-prepare-cjk.sh   → 同上
typewriter/scripts/02-prepare-cjk.sh → 同上
handwriting/scripts/06-verify.sh    → ${REPO_ROOT}/serif/scripts/verify-2to1.py
handwriting/scripts/05-expand-ligatures.sh → serif/scripts/expand-default-ligatures.py
casual/scripts/common.sh            → SERIF_TOOLS + HANDWRITING_SCRIPTS
sans/scripts/04-verify.sh:48        → sys.path.insert(0, os.environ["SERIF_TOOLS"])
```

`casual/scripts/05-verify.sh` 在运行时靠文件系统考古找共享库：

```bash
if   [[ -f "${REPO_ROOT}/serif/scripts/verify-2to1.py"   ]]; then ...
elif [[ -f "${REPO_ROOT}/rounded/scripts/verify-2to1.py" ]]; then ...
else die "no verify-2to1.py found under serif/ or rounded/"
```

`serif/` 已经**事实上是公共库**了，只是没有被承认，也没有接口约定。

### 1.4 工具链：全靠"这台机器上碰巧装了什么"

这是选 Nix 的**首要理由**。当前构建对宿主环境的依赖完全没有被管理：

**系统工具**（`need_cmd` 或裸调用）：
`curl` `git` `quilt` `unzip` `zip` `7z`/`7zz` `fontforge` `ttfautohint` `node` `npm` `docker` `hb-view`

**Python 依赖**（散落在 8 处不同的 `pip install` 命令里，版本约束互不一致）：
`fonttools>=4.50` `brotli` `skia-pathops` `Pillow` `freetype-py` `numpy` `uharfbuzz` `wcwidth` `py7zr`

到处是"看看有没有装"的降级分支：

- 7z：`7zz` → `7z` → `pip install py7zr` 三级回退
- Nerd patch：`docker` → 本地 `fontforge`（`NERD_PATCH_METHOD=auto`），**全仓库 61 处 docker 引用**
- venv：`uv` → `python -m venv`
- `ttfautohint` 不在 PATH 上时**只打一句 warning 然后继续**（`serif/scripts/04-build.sh`）——
  这是最典型的一颗雷：构建"成功"了，产物却不对
- Pillow 装不上时静默跳过样张渲染

**没有任何一处锁定版本。** 换台机器、或者 upstream 发个新版 fontTools，产物就可能变，
而且没人会发现。

### 1.5 缓存现状

- `DOWNLOADS_DIR="${WORK_DIR}/downloads"` 是**每个家族一份**。而 serif / sans / rounded /
  typewriter / pixel 这 5 个家族 pin 的是**同一个** URL
  （`nerd-fonts/releases/download/v3.4.0/FontPatcher.zip`）—— 同一个 zip 下载 5 遍
- `serif/scripts/01-clone-sarasa.sh` 每次 `rm -rf` 重新 clone Sarasa，
  再手工把 `node_modules` 备份出去又搬回来当提速手段
- 加上 profile × region 矩阵后会更糟：拉丁侧在所有 region 之间**完全相同**，
  但当前结构会为每个 region 重算一遍

### 1.6 CI

只有一个 `release-nfm.yml`，serif 专用，而且不是从源码构建 ——
是"下载上一个 tag 的产物 → 后处理 → 重新发布"。其余 6 个家族**没有任何自动化验证**。

---

## 2. 为什么是 Nix

先记录一下被否掉的两个选项，免得以后重新讨论：

**bazel（含 just 调 bazel 的混合方案）—— 否。**
这个仓库的 DAG 是「少而重」（按声明矩阵算，7 个家族撑死两三百个粗粒度节点，
bazel 的设计点是 10^5 量级细粒度节点）；而最贵的步骤（fontforge patch、Sarasa 的 npm 构建、
网络取源）恰好是最不 hermetic 的那些，塞进 bazel 要么包不动、要么只能标成不可远程缓存 ——
**最想缓存的步骤恰好缓存不了**，bazel 最后只管到纯 Python 那几步便宜的。混合方案是两套心智负担换一半收益。

**自建内容寻址缓存 —— 否（被 Nix 取代）。**
v1 方案里那套 `hash(step_id, params, input_hashes)` 的步骤缓存，正是 Nix 已经做好的事。
既然维护者本来就熟 Nix，没有理由再手搓一遍。

**Nix 恰好命中这个仓库的三个真实痛点**：

| 痛点 | Nix 的答案 |
| --- | --- |
| §1.4 工具链靠碰运气 | `devShell` / `buildInputs` 精确锁定 fontforge、ttfautohint、node、7z、harfbuzz 和全部 Python 依赖；所有"看看装没装"的回退分支直接删掉 |
| §1.5 缓存各家族互不相通 | Nix store 本身就是内容寻址缓存。FontPatcher.zip 变成**一个** store path，5 个家族自动共享；拉丁侧在 region 间自动复用；binary cache 直接就是远程缓存 |
| §1.3 跨家族裸路径引用 | derivation 只能看到**声明过的**输入。`casual` 从物理上就够不到 `serif/scripts/` —— 这条规则从"CI 加条 grep 守着"变成"结构上不可能" |

还有一个额外收益：`pins.env` 里每个资源都已经是 **URL + sha256**，
这正是 `fetchurl` 的原生形态，几乎可以逐行翻译（现有 hex 摘要直接可用，
要 SRI 的话 `nix hash to-sri --type sha256 <hex>`）。

**关于可复现性的一个关键点**：fontforge 的 patch 输出**不是字节可复现的**（内嵌时间戳）。
这在 Nix 下不是问题 —— Nix 按**输入哈希**（`.drv`）缓存，不按输出哈希。
所以：构建时设 `SOURCE_DATE_EPOCH`（fontTools 认这个变量，能消掉 `head.modified` 的噪声），
但**不要**对这些包启用 content-addressed derivations。
同理，回归指纹继续用「归一化的 advance / name / feature dump」，不要用 TTF 的 sha256。

---

## 3. 目标形态

```
flake.nix                   # 入口：packages / devShells / checks / apps
flake.lock                  # nixpkgs 固定
nix/
  fontkit.nix               # buildPythonPackage
  lib/
    mkFamily.nix            # 读 font.toml → 展开 profile × region × weight 矩阵
    fetch.nix               # fetchurl / fetchzip / fetchZipMember(FOD)
    steps.nix               # prepare-latin / prepare-cjk / merge / nerd / verify / package
  overlays/                 # 需要自打包的 Python 依赖（见 §8 风险 1）

justfile                    # UX 薄层，转调 nix build
lib/fontkit/                # 共享 Python 库（内容同 v1 方案）
fonts/<family>/
  font.toml                 # 唯一事实源，Nix 与 Python 共同消费
  steps/                    # 仅本家族独有的变换
  patches/ licenses/ samples/
```

### 3.1 `font.toml` 是唯一事实源

Nix 有 `builtins.fromTOML`，所以**同一份清单同时驱动 derivation 图和 Python 代码** ——
不需要生成器，也不会出现两边不同步。这是选 TOML 而不是别的格式的决定性理由。

```toml
[source.latin]        # url + sha256 (+ zip 成员)
[source.cjk.sc]       # 按 region 分组
[source.cjk.tc]
[grid]                # EN_ADV / CJK_ADV / UPM / scale
[naming]              # family / PS name / 31 字符约束 / RFN 备注
[metrics.coding]      # 终端紧排行度量
[metrics.text]        # 排版型行度量
[calibration]         # embolden 强度 / slant —— 永远是数据，不是代码
[nerd]
[build.matrix]        # 显式声明要构建哪些 (profile, region) 组合
```

### 3.2 derivation 粒度 —— 缓存收益的**唯一**决定因素

这是整个方案最容易做错的地方。**必须一步一个 derivation，绝不能一个家族一个 derivation**，
否则所有共享全部失效：

```
src-latin-<family>                        ← fetchurl，跨 profile × region 共享
src-cjk-<family>-<region>                 ← fetchurl
latin-prepared-<family>-<profile>         ← ★ 跨全部 region 共享（sc/tc/jp/kr 只算一次）
cjk-prepared-<family>-<region>            ← ★ 跨 profile 共享（光学 embolden 与场景无关）
merged-<family>-<profile>-<region>-<weight>
nerd-<family>-<region>-<weight>           ← 仅 coding
verified-… / packaged-…
```

以 sans 出 sc/tc/jp/kr 四个 region 为例：`latin-prepared` 应该命中 1 次而不是算 4 次。
这个共享是免费的，前提是粒度切对。

### 3.3 取源的两个特例

- **Monaspace 315 MiB zip**（handwriting）：现有 `fetch_zip_member.py` 用 HTTP range 请求
  只取需要的两个成员。Nix 的标准 fetcher 不做部分下载，但**固定输出 derivation（FOD）
  在沙箱里是有网络的** —— 把这个脚本包成一个 `outputHash` 固定的 FOD 即可，
  现有优化原样保留。（退路：直接 `fetchurl` 整个 zip，反正只下一次且进 binary cache；
  但既然脚本已经写好了，没必要退。）
- **Sarasa git 仓库**（serif）：`fetchFromGitHub { rev = SARASA_COMMIT; }`。
  它后面的 `npm install` 是本方案最硬的一块，见 §8 风险 2。

### 3.4 `just` 的定位

`just` **不是**构建系统，只是一张别名表 —— 这正是它和 bazel 混用会出问题、
和 Nix 搭配却很干净的原因：

```
just build sans coding tc   → nix build .#sans-coding-tc
just build-all              → nix build .#all
just dev                    → nix develop
just verify sans            → nix flake check
just matrix                 → 打印 font.toml 里声明的组合
just calibrate sans         → nix develop -c fontkit calibrate sans   （见下）
just sample sans            → nix build .#sans-sample && 拷回 samples/rendered/
just release sans 0.2.0     → nix build + gh release
```

**留在 devShell 里的不纯操作**：`calibrate`（测量笔画后打印建议值，供人工写回 `font.toml`，
本质上不是构建产物）、样张渲染回写仓库。其余全部是 derivation。

---

## 4. 边界规则（需求 2）

**必须共享**：取源/校验、字形拷贝、cmap 重建、advance 居中数学、GPOS 横向缩放、
家族命名、垂直度量、mono 标志、Nerd patch、EAW 修正、校验规则实现、打包、样张渲染。

**允许家族自持**（`font.toml` 里显式声明为 `steps.custom`）：
上游特有的获取方式与形状级变换 —— serif 的 Sarasa 上游工具链 + quilt 补丁栈、
pixel 的像素化连字绘制、handwriting 的 CJK 倾斜 7.5°、typewriter 的 hinting 剥离。
**所有校准常数永远是 `font.toml` 里的数据，永远不是代码。**

三条硬规则：

1. 家族本地步骤**不得重新实现**共享能力，要变体就通过 `font.toml` 参数扩展共享实现。
2. 家族本地步骤是 `fonts/<f>/steps/` 下的 Python 模块，import `fontkit`。
3. **Rule of two**：同一个本地步骤出现第二次就上移进 `fontkit`，不等第三次。

> v1 里的第 4 条「不得引用其他家族路径」已经**不需要写成规则** —— Nix 的输入隔离让它成为结构性保证。

---

## 5. coding / text profile（需求 3 —— **需求已确认**）

判据：这条约束服务于**终端格子**，还是服务于**阅读**？

| 约束 | `coding` | `text` | 理由 |
| --- | --- | --- | --- |
| 严格 2:1 EN:CJK | **硬性 gate** | 不适用 | 终端按格子排版；正文强行 2:1 会让拉丁过宽 |
| `post.isFixedPitch` / PANOSE mono | 是 | 否 | 正文不该被宿主当成等宽 |
| EAW 驱动的半宽/全宽 | 是 | 否 | `…` `“ ”` `·` 在正文里应保持 CJK 全宽 |
| Nerd Font patch | 是（NFM） | 否 | 图标是终端需求 |
| 连字默认开（`calt` 折叠） | 是 | 否 | 正文只保留 `liga` / `kern` |
| 拉丁侧 GPOS / kern | 被等宽格子压平 | **保留** | 正文字距质量来自 kern |
| 上游 hinting | 丢弃 | 尽量保留 | |
| 行度量 | 终端紧排（hhea 950/-250） | 排版型（typo asc/desc + line gap） | |
| **中英光学笔画对齐** | **是** | **是** | 与场景无关，是"中文比英文细"这个缺陷本身 |
| **中英基线 / 视觉重心对齐** | **是** | **是** | 同上 |
| 源 pin / 可复现 / 命名 / 授权装配 | 是 | 是 | 与场景无关 |

**因此「严格 2:1」和「光学笔画对齐」在代码里必须是两个独立步骤**，
不能像现在这样都埋在 `merge_*.py` 的 `unify_metrics` 里。

`font.toml` 里显式声明每个家族支持哪些 profile。pixel 是 coding-only（12px 点阵正文无意义）。
**首个落地对象：handwriting**（文楷本来就是正文向 CJK）。

---

## 6. region 轴（需求 4 —— **破坏性改名已获批**）

构建矩阵 = 家族 × profile × region × 字重。region 只决定 **CJK 供体**
（外加可能不同的 `locl`/cmap），拉丁侧与全部度量逻辑复用（见 §3.2）。

| 家族 | CJK 源 | sc | tc | hk | jp | kr |
| --- | --- | --- | --- | --- | --- | --- |
| sans | IBM Plex Sans SC/TC/JP/KR | ✅ | ✅ | ❌ | ✅ | ✅ |
| pixel | fusion-pixel `zh_hans`/`zh_hant`/`ja`/`ko` | ✅ | ✅ | ❌ | ✅ | ✅ |
| rounded | Resource Han Rounded CN/TW/HK/JP/KR | ✅ | ✅ | ✅ | ✅ | ✅ |
| handwriting | LXGW WenKai / WenKai TC | ✅ | ✅ | ❌ | ❌ | ❌ |
| serif | LXGW Neo ZhiSong（仅 SC） | ✅ | ❌ | ❌ | ❌ | ❌ |
| typewriter | 朱雀仿宋（仅 SC） | ✅ | ❌ | ❌ | ❌ | ❌ |
| casual | Yozai（仅 SC） | ✅ | ❌ | ❌ | ❌ | ❌ |

**先做 sans 和 pixel**：Plex 上游齐全；fusion-pixel 四个 flavor 在同一个 zip 里，成本最低。
不支持的组合在清单里显式声明，不留坑。

**命名**：现有家族名把地区烤死在里面（`LilexSansSC NFM`）。新方案须同时满足
Windows name ID 1 ≤ 31 字符、以及 `pins.env` 里已记录的多处 OFL RFN 警告。
改名需附迁移说明（已安装用户的字体名会变）。

---

## 7. 分阶段落地

每阶段独立可合并、可回滚。**Phase 0 先建回归网，再动任何重构。**

| Phase | 内容 | 对应 issue |
| --- | --- | --- |
| **0** | flake 骨架 + `devShell` + `just` 薄层 + 指纹回归网 + CI 矩阵。**构建逻辑一行不动** —— recipe 仍在 `nix develop` 里调现有 `scripts/build.sh`。光是把工具链钉死就解决了 §1.4 一整类问题 | KIT-264 |
| **1** | 取源全部 Nix 化：`pins.env` 的 URL+sha256 → `fetchurl`；Monaspace 走 FOD；FontPatcher 变成单一 store path。同时定 derivation 粒度与 binary cache | KIT-265 |
| **2** | 抽走 17 份字节级重复模块 → `lib/fontkit`（`buildPythonPackage`）；`serif/tools/` 正式升格 | KIT-266 |
| **3** | 每步一个 derivation，删掉 shell 编排（`common.sh`×7 / `build.sh`×7 / `package-release.sh`×7 / `nerd-patch`×4 / `verify`×5）。**docker 路径整体删除**（fontforge 由 Nix 提供），61 处引用清零 | KIT-267 |
| **4** | `pins.env` → `font.toml`，`builtins.fromTOML` + pydantic 双向消费 | KIT-268 |
| **5** | 4 份 `merge_*.py` → 清单驱动的 `fontkit.merge`。**逐家族一个 PR，指纹卡住** | KIT-269 |
| **5** | serif 的 Sarasa 上游构建进 Nix（`buildNpmPackage` + `npmDepsHash`），quilt 补丁栈改用 `patches` 属性 | **KIT-273（新）** |
| **6** | `text` profile + 其 gate，先落 handwriting | KIT-270 |
| **7** | region 轴 + 破坏性改名，先做 sans / pixel | KIT-271 |
| **8** | 通用 `release.yml`（从源码构建）+ binary cache 推送，删掉 serif 专用 workflow | KIT-272 |

**迁移期共存策略**：Phase 3 之前 `nix develop` 里跑的还是老脚本，产物不变；
Phase 3 起逐家族切换到 derivation。serif 因为 §8 风险 2 最后切 —— 在 KIT-273 落地前它一直走老路径。

---

## 8. 风险与待决事项

| # | 事项 | 影响 / 处置 |
| --- | --- | --- |
| **1** | **`skia-pathops` 是否在 nixpkgs 里** —— 未经核实（写方案的机器上没有 Nix）。它绑着 Skia 的 C++ 扩展，自打包可能不轻松 | **在关键路径上**：`embolden_cjk.py` 依赖它，而光学配重是**每个家族、两个 profile 都要**的步骤。**Phase 0 第一件事就是核实**；不在的话要么走 overlay 自打包，要么从 PyPI sdist 起 `buildPythonPackage`。同批要核的还有 `uharfbuzz` / `freetype-py` / `py7zr`（`py7zr` 可直接用 `p7zip` 替掉） |
| **2** | **Sarasa 的 `npm install` + `npm run build`**（serif）| 全仓库最硬的一块。`buildNpmPackage` + `npmDepsHash`，但 Sarasa 构建期可能还会拉别的东西。**单独一个 issue（KIT-273）隔离**，落地前 serif 走老路径，不阻塞其余 6 个家族 |
| **3** | **darwin 支持** —— 维护者在 macOS 上 | fontforge / ttfautohint 在 nixpkgs-darwin 上需实测。真有问题就把 serif 这类重家族丢到 CI 的 linux 上跑，或上 `linux-builder` |
| **4** | **binary cache 的搭建与成本** | cachix（开源项目有免费额度）或自建 attic / `nix-serve`。Phase 1 决定，Phase 8 接进 CI |
| **5** | **命名方案**（region 轴 + 31 字符 + OFL RFN） | 破坏性已获批，但**具体名字仍待定**，阻塞 Phase 7 |
| **6** | serif 是唯一真正特殊的家族 | 它跑上游完整工具链，不要为了统一硬塞进通用引擎 —— 给它正式的 `steps.custom` 逃生口 |
| **7** | 重构期间 serif 既有 release 流程不能断 | 旧 workflow 保留到 Phase 8 完成再删 |
| **8** | 全仓库无实测墙钟数据 | 本方案只读了脚本、没跑过构建。Phase 0 的 CI 应顺手记录每步耗时，作为后续决策依据 |
