# 1. Desktop core - wm, zxrun, toolbar/panel (winplace closed; stale untracked file removed from scope) - 3 rows

Owner: Desktop core (`agy-taijios-zx-graphical-dis-port-2`, switched from `cmd-taijios-zx-graphical-dis-port`)

Index: [plans/dis-to-zx.md](../dis-to-zx.md)

| Path | Limbo source | Interface | Boot | Notes |
|---|---|---|---|---|
| zx/wm/wm.dis | appl/wm/wm.b |  | P0 | Tracked legacy Dis WM (kept while legacy Dis WM apps remain). ZX replacement `zx/wm/wm.zx` (`appl/wm/native_wm.zi`) runs the Dis-free desktop; `c2f89a15` + `07495a97` closed and verified the 64-event queue overflow recovery on private Xvfb (`tests/desktop/zx_boot_test.py --graphics`); `35ad6ebe` updated `appl/wm` Kryon pin (`d0effa16`) and verified middle-button press/hold/release via `TertiaryPointerSample` on private Xvfb. |
| zx/wm/toolbar.dis | appl/wm/toolbar.b | module/toolbar.m | P2 | Tracked legacy Dis WM panel/toolbar (kept while legacy `wm/wm` runs). ZX desktop uses Rill shell and `zx/wm/desktop_panel.zx`. |
| zx/zxrun.dis | appl/cmd/zxrun.b | module/zxrun.m | P2 | Gitignored local build of tracked `appl/cmd/zxrun.b` (bridges legacy Dis `wm/wm` to ZX windows). Dis-free CLI runner is `zx/zxrun.zx` (`appl/cmd/zxrun.zi`). |

Note on `zx/lib/winplace.dis`: not a tracked row (`git ls-files zx/lib/winplace.dis` is empty; its Limbo source was already removed and replaced by `zx/lib/winplace.zx` from `appl/lib/winplace_service.zi`). The file on disk is only a stale untracked local build artifact, so it is dropped from the active row count above (3 rows remain).
