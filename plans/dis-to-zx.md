# Dis -> ZX migration inventory (open items)

Measured on this canonical checkout working tree (2026-11-22) at git 36908287c684a30e86c58778e1b382c1cbf9c5ab (47 uncommitted paths at measurement; the commit of this document follows), inventory universe **691** open rows = **669** on-disk `dis/` files (**129** top-level `dis/*.dis` + **540** under `dis/**/`) + **22** tracked acme helper binaries outside `dis/`. Excluded as build artifacts, not rows: `backup/` copies (8), `build/` caches (205), untracked local `appl/` builds (12). Installed Ziran/ZX artifacts for reference: **69** `.zx` files on disk (untracked; the replacement format, not rows). Earlier root counts are superseded by these measurements.

Every `.dis` in the measured universe - on-disk `dis/` plus tracked acme helper binaries outside `dis/` - has exactly one open row below. Rows are removed only when the `.dis` is actually deleted in a tested commit (tracked files via `git rm`). No completed-work log.

## Goal

Rewrite all remaining Limbo/Dis as modular Ziran/ZX so the default desktop boots loading zero `.dis` (the `zero.dis` state).

## Done rule (per family, one tested source commit)

1. Port the family to modular Ziran/ZX: shared Ziran source in the tree (module paths under `appl/`), Ziran regression suite green.
2. Prove actual private-guest/display parity for the replaced surface (private Xvfb/guest harness, never the live desktop).
3. In that same tested commit, remove the replaced `.dis` binaries (tracked ones via `git rm`, including acme helper binaries outside `dis/`) and their Limbo sources. Upstream prerequisites first: pinned Ziran, Tcl and Tk packages in `ziran.toml`. No partial implementation commit.
4. After the last family: full local suite green and the default boot loads no `.dis`.

A family is done only when every one of its `.dis` rows (including acme helper binaries outside `dis/`) is removed via `git rm` in that tested commit and the ZX replacement is the installed default.

## Default desktop load chain (verified in source)

Default, loading no `.dis`: `emu -r root` -> `/dis/wm/wm.zx` (the Ziran window manager, `appl/wm/native_wm.zi`) -> `/dis/wm/rill.zx`. It takes effect in a root once `cd appl/wm && mk install-wm-zx` has installed `wm.zx`; until then the emulator starts `emuinit.dis` as before. `tests/desktop/zx_boot_test.py --graphics` boots this chain in a root with no `.dis`. Neither `wm.zx` nor `wm.dis` overlaps window client content with its 32px Sweet-Dark title bar: `native_wm.zi` places the caption at `[bounds.top - 32, bounds.top)` above the client surface, and the 8-row title-bar strip in `appl/cmd/tcltk/about_stock_art.png` was an artifact of the legacy `STOCK_ORIGIN = (7, 25)` capture offset in `test_about.py`.

Legacy chain, kept while a catalog application exists only as Dis: `emu -r root wm/wm` -> `/dis/emuinit.dis` -> `/dis/wm/wm.dis` (P0) -> `/dis/lib/wmclient.dis` -> `/dis/lib/wmlib.dis` + `/dis/lib/titlebar.dis`, `/dis/lib/wmsrv.dis`, `/dis/lib/string.dis`, `/dis/sh.dis` (P1) -> broker `/dis/wm/toolbar.dis` -> `/dis/lib/arg.dis`, `/dis/lib/tkclient.dis` -> `titlebar` (already loaded), `/dis/zxrun.dis` (P2) -> ZX desktop `/dis/wm/rill.zx` + panel `/dis/wm/desktop_panel.zx` (P3, no `.dis`). Without `rill.zx`, wm falls back to the classic toolbar panel. When `wm.dis` is deleted, `wm/wm` starts `/dis/wm/wm.zx` too.

Catalog applications that still need the legacy chain (30): avi bounce brutus c4 collide cprof deb edit filename getauthinfo keyboard logon mand mash mprof pen prof readmail remotelogon reversi rmtdir rt sam sendmail sh telnet unibrowse vt wish wmplay. The boot test prints this list. Terminal entries also need it: they start through `/dis/sh.dis` and `wm/sh`.

## Column legend

- Path: file on disk under `dis/`. Limbo source: matched implementation under `appl/` (name/path convention, mkfile cross-checks); `unknown` = no matching Limbo source on disk (stale binary or generated). Interface: matching module definition under `module/`. Boot: P0/P1/P2 = loaded in the legacy chain above; `-` = not loaded by it. Notes: `zx-twin` = same-directory `.zx` replacement already installed.

## Ownership

- Desktop core (wm, zxrun, toolbar/panel, winplace) and the dis/wm applications: `claude-taijios-zx-graphical-dis-port`; its sources, defaults, tests and build outputs are not edited elsewhere.
- Live Rill install: owned by `root2498`. Standalone pointer-index prerequisite: handled by the existing e18 compiler.
- Section 3 top-level commands, except sh, dis/sh, dis/tiny, mash, the Limbo developer tools and the window commands: `glm-taijios-dis-commands-a-l` and `glm-taijios-dis-commands-m-z`.
- Sections 13 (math) and 14 (legacy misc): `agy-taijios-dis-legacy-math`.
- Sections 9 (spree), 10 (grid), 11 (demo) and 12 (ebook): `agy-taijios-dis-app-families`.
- Section 2 (dis/lib), section 4 (services) and the mash command with its library: `claude-taijios-taijios-dis-commands-libs`.
- The shell (sh, dis/sh, dis/tiny) is its own milestone. Acme and charon are not assigned yet.
- Alphabet (section 8, 6 rows): `claude-taijios-zx-alphabet-port`. Remaining: `/auth` (needs a ZX Inferno Auth client), `grid/{farm,remote,rexec}` and `rexecsrv` (need a concurrent bundle procedure host call and fd/handle passing), and orphan `mktypeset.dis`.
- One family per tested commit. Several tasks edit this file: commit only your own rows and counts.

## Next ready order (independent, boot-ordered)

1. `dis/lib/tcl_*.dis` (12 rows): their last user is `wm/wish` (`appl/wm/wish.b`, desktop-core owner). Delete them with `appl/lib/tcl_*.b` and `appl/lib/tcl.m` when wish is replaced; the ZX shell `dis/tclsh.zx` and the Tcl/Tk app `dis/tcltk.zx` already replace their other uses.
2. Non-boot libraries (148 rows in dis/lib outside the boot chain): port subpackage by subpackage (convcs, crypt, encoding, ftree, mash, print, spki, strokes, styxconv, usb, w3c).
3. Services (96 rows): auth, auxi, collab, ip, ndb, spki, svc, usb + top-level storage and network servers.
4. Legacy misc (2 rows): installer, disk, fs, avr, lego, mpc, mpeg, palm, dbm and stale orphans whose sources are gone.
5. App families: acme (24 `dis/` rows + 2 helper binaries outside `dis/`), charon (15), alphabet (6), spree (0), grid (5), demo (6), ebook (0), math (0).
6. WM apps with zx-twins (2 rows) and the rest of dis/wm (54 rows total): delete or port through the desktop-core owner.
7. Desktop core (4 rows): stays with `claude-taijios-zx-graphical-dis-port`; deleted when no catalog application needs the legacy chain.

## Open blockers (preserved from lane reports)

- **Alphabet (6 rows):** `grid/{remote,rexec,farm}` and `rexecsrv` need a Ziran host call that starts a procedure of the same bundle while the caller keeps running, plus fd and handle passing; `/auth` needs a ZX Inferno Auth client; `mktypeset.dis` is an orphan without source.
- **`wmplay`:** needs the emulator audio device compiled in with a headless backend.
- **`dis/disk/kfs.dis`:** needs a Ziran Styx (9P) codec (plus multi-name walk/create/remove/flush file server support and pread/pwrite).
- **`dis/lego/clock.dis`:** needs `create arc -start -extent` / `itemconfigure -start` in out-of-tree `ziranlang/tk`, plus bare `<ButtonPress>`/`<ButtonRelease>` binds and `send`/`namechan`.
- **30 remaining M–Z commands:** blocked on 9P unpacking, `convcs`, `Parseman`, Draw font metrics, and dial/keyring libraries (or large/library-dependent ports).
- **Acme editor core (24 `dis/acme/*.dis` rows) & `acme/mail/{Mail,Mailpop3}.dis`:** Acme core needs Ziran `Draw->Font` metrics (`Font.width`, `Image.text`), `Wmclient` cursor/pointer-warp `wmctl`, concurrent multi-fid 9P `/mnt/acme` serving alongside the UI loop, and `plumbmsg`; `Mail`/`Mailpop3` need `taijios_io.Fwstat`, ZX `sendmail`, and Ziran `pop3` library.

## Section files

| # | Section | Owner | Open rows |
|---|---|---|---|
| 1 | [1. Desktop core - wm, zxrun, toolbar/panel (winplace closed by the Ziran winplace service; stale file remains) - 4 rows](dis-to-zx/01-desktop-core.md) | Desktop core (`cmd-taijios-zx-graphical-dis-port`) | 4 |
| 2 | [2. Libraries - dis/lib/** (boot-loaded rows first) - 155 rows](dis-to-zx/02-libraries.md) | Libraries (`glm-taijios-dis-libraries-port`; mash rows owned by shell lane) | 155 |
| 3 | [3. Shell and commands - sh module, sh builtins, tiny, top-level commands - 111 rows](dis-to-zx/03-shell-commands.md) | Commands A–L / M–Z (`glm-taijios-dis-commands-a-l`, `cmd-taijios-dis-commands-m-z`); shell (`cmd-taijios-zx-shell-port`) | 111 |
| 4 | [4. Services - storage, network, name, auth, collab, usb and aux daemons - 96 rows](dis-to-zx/04-services.md) | Services (unassigned after Claude commands-libs lane; next after section 2) | 96 |
| 5 | [5. WM apps - dis/wm/** desktop applications (deletions go through the desktop-core owner) - 43 rows](dis-to-zx/05-wm-apps.md) | WM apps (`cmd-taijios-zx-desktop-apps-port`; deletions through desktop-core owner) | 43 |
| 6 | [6. Acme - editor family - 24 rows](dis-to-zx/06-acme.md) | Acme (acme lane) | 24 |
| 7 | [7. Charon - web browser family - 15 rows](dis-to-zx/07-charon.md) | Charon (unassigned; pending owner decision) | 15 |
| 8 | [8. Alphabet - gridded documents family - 6 rows](dis-to-zx/08-alphabet.md) | Alphabet (`cmd-taijios-zx-alphabet-port`) | 6 |
| 9 | [9. Spree - multiuser engine family - 0 rows](dis-to-zx/09-spree.md) | Spree (`agy-taijios-dis-app-families`) | 0 |
| 10 | [10. Grid - computing grid family - 5 rows](dis-to-zx/10-grid.md) | Grid (`agy-taijios-dis-app-families`) | 5 |
| 11 | [11. Demo - demonstration apps - 6 rows](dis-to-zx/11-demo.md) | Demo (`agy-taijios-dis-app-families`) | 6 |
| 12 | [12. Ebook - readers - 0 rows](dis-to-zx/12-ebook.md) | Ebook (`agy-taijios-dis-app-families`) | 0 |
| 13 | [13. Math - numeric modules - 0 rows](dis-to-zx/13-math.md) | Math (`agy-taijios-dis-legacy-math`) | 0 |
| 14 | [14. Legacy misc - installer, disk, fs, avr, lego, mpc, mpeg, palm, dbm and orphans - 2 rows](dis-to-zx/14-legacy-misc.md) | Legacy misc (`agy-taijios-dis-legacy-math`) | 2 |
| 15 | [15. Acme helper binaries outside dis/ - 2 rows](dis-to-zx/15-acme-helpers.md) | Acme helpers outside dis/ (acme lane) | 2 |
| 16 | [16. Native kernel configurations - open item, no `.dis` rows](dis-to-zx/16-native-kernel.md) | Native kernel configurations (unassigned) | 0 |

Total open table rows across sections 1–16: **469**.
