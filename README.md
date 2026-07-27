# font

Personal / project font build recipes.

## serif/

**Slab Latin (IosevkaNSlab) + 霞鹜新致宋** coding mono, 2:1 SC, optical weight match.

- Clones pinned [Sarasa Gothic](https://github.com/be5invis/Sarasa-Gothic) `v1.0.40`
- Applies **quilt** patches for stable, reviewable diffs
- Downloads LXGW Neo ZhiSong Plus and emboldens CJK for Regular/Bold match

See [`serif/README.md`](serif/README.md) and run:

```bash
cd serif && ./scripts/build.sh
```
