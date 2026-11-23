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

Catalog applications that still need the legacy chain (35): avi bounce brutus c4 calendar coffee collide cprof deb edit filename getauthinfo keyboard logon man mand mash mpeg mprof pen polyhedra prof readmail remotelogon reversi rmtdir rt sam sendmail sh telnet unibrowse vt wish wmplay. The boot test prints this list. Terminal entries also need it: they start through `/dis/sh.dis` and `wm/sh`.

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
- Alphabet (section 8, dis/fs.dis aside, and dis/sh/alphabet.dis): `claude-taijios-zx-alphabet-port`. Its rows go in one commit once the ZX shell runs `load alphabet` from the Ziran library in appl/alphabet; until then the Dis builtin needs every row. /filter, /fs/exec, /fs/run, /fs/pipe and the grid rexec modules also need /dis/sh.zx; /auth needs a ZX Inferno Auth client.
- One family per tested commit. Several tasks edit this file: commit only your own rows and counts.

## Next ready order (independent, boot-ordered)

1. `dis/lib/tcl_*.dis` (12 rows): their last user is `wm/wish` (`appl/wm/wish.b`, desktop-core owner). Delete them with `appl/lib/tcl_*.b` and `appl/lib/tcl.m` when wish is replaced; the ZX shell `dis/tclsh.zx` and the Tcl/Tk app `dis/tcltk.zx` already replace their other uses.
2. Non-boot libraries (148 rows in dis/lib outside the boot chain): port subpackage by subpackage (convcs, crypt, encoding, ftree, mash, print, spki, strokes, styxconv, usb, w3c).
3. Services (96 rows): auth, auxi, collab, ip, ndb, spki, svc, usb + top-level storage and network servers.
4. Legacy misc (32 rows): installer, disk, fs, avr, lego, mpc, mpeg, palm, dbm and stale orphans whose sources are gone.
5. App families: acme (25 `dis/` rows + 22 helper binaries outside `dis/`), charon (15), alphabet (83), spree (0), grid (5), demo (6), ebook (0), math (0).
6. WM apps with zx-twins (2 rows) and the rest of dis/wm (54 rows total): delete or port through the desktop-core owner.
7. Desktop core (4 rows): stays with `claude-taijios-zx-graphical-dis-port`; deleted when no catalog application needs the legacy chain.

## Open rows

### 1. Desktop core - wm, zxrun, toolbar/panel (winplace closed by the Ziran winplace service; stale file remains) - 4 rows

| Path | Limbo source | Interface | Boot | Notes |
|---|---|---|---|---|
| dis/wm/wm.dis | appl/wm/wm.b |  | P0 |  |
| dis/wm/toolbar.dis | appl/wm/toolbar.b | module/toolbar.m | P2 |  |
| dis/zxrun.dis | appl/cmd/zxrun.b | module/zxrun.m | P2 | untracked gitignored local build of tracked appl/cmd/zxrun.b |
| dis/lib/winplace.dis | unknown |  | - | zx-twin; Limbo source removed; untracked local artifact (not gitignored) |

### 2. Libraries - dis/lib/** (boot-loaded rows first) - 155 rows

| Path | Limbo source | Interface | Boot | Notes |
|---|---|---|---|---|
| dis/lib/string.dis | appl/lib/string.b | module/string.m | P1 |  |
| dis/lib/titlebar.dis | appl/lib/titlebar.b | module/titlebar.m | P1 |  |
| dis/lib/wmclient.dis | appl/lib/wmclient.b | module/wmclient.m | P1 |  |
| dis/lib/wmlib.dis | appl/lib/wmlib.b | module/wmlib.m | P1 |  |
| dis/lib/wmsrv.dis | appl/lib/wmsrv.b | module/wmsrv.m | P1 |  |
| dis/lib/arg.dis | appl/lib/arg.b | module/arg.m | P2 |  |
| dis/lib/tkclient.dis | appl/lib/tkclient.b | module/tkclient.m | P2 |  |
| dis/lib/asn1.dis | appl/lib/asn1.b | module/asn1.m | - |  |
| dis/lib/attrdb.dis | appl/lib/attrdb.b | module/attrdb.m | - |  |
| dis/lib/auth.dis | appl/lib/auth.b |  | - |  |
| dis/lib/auth9.dis | appl/lib/auth9.b | module/auth9.m | - |  |
| dis/lib/bufio.dis | appl/lib/bufio.b | module/bufio.m | - |  |
| dis/lib/cfg.dis | appl/lib/cfg.b | module/cfg.m | - |  |
| dis/lib/cfgfile.dis | appl/lib/cfgfile.b | module/cfgfile.m | - |  |
| dis/lib/chanfill.dis | appl/lib/chanfill.b |  | - |  |
| dis/lib/convcs/8bit_stob.dis | appl/lib/convcs/8bit_stob.b |  | - |  |
| dis/lib/convcs/big5_btos.dis | appl/lib/convcs/big5_btos.b |  | - |  |
| dis/lib/convcs/big5_stob.dis | appl/lib/convcs/big5_stob.b |  | - |  |
| dis/lib/convcs/convcs.dis | appl/lib/convcs/convcs.b | module/convcs.m | - |  |
| dis/lib/convcs/cp932_btos.dis | appl/lib/convcs/cp932_btos.b |  | - |  |
| dis/lib/convcs/cp_btos.dis | appl/lib/convcs/cp_btos.b |  | - |  |
| dis/lib/convcs/cp_stob.dis | appl/lib/convcs/cp_stob.b |  | - |  |
| dis/lib/convcs/euc-jp_btos.dis | appl/lib/convcs/euc-jp_btos.b |  | - |  |
| dis/lib/convcs/gb2312_btos.dis | appl/lib/convcs/gb2312_btos.b |  | - |  |
| dis/lib/convcs/utf16_btos.dis | appl/lib/convcs/utf16_btos.b |  | - |  |
| dis/lib/convcs/utf16_stob.dis | appl/lib/convcs/utf16_stob.b |  | - |  |
| dis/lib/convcs/utf8_btos.dis | appl/lib/convcs/utf8_btos.b |  | - |  |
| dis/lib/convcs/utf8_stob.dis | appl/lib/convcs/utf8_stob.b |  | - |  |
| dis/lib/crc.dis | appl/lib/crc.b | module/crc.m | - |  |
| dis/lib/crypt/pkcs.dis | appl/lib/crypt/pkcs.b | module/pkcs.m | - |  |
| dis/lib/crypt/ssl3.dis | appl/lib/crypt/ssl3.b | module/ssl3.m | - |  |
| dis/lib/crypt/sslsession.dis | appl/lib/crypt/sslsession.b | module/sslsession.m | - |  |
| dis/lib/crypt/x509.dis | appl/lib/crypt/x509.b | module/x509.m | - |  |
| dis/lib/daytime.dis | appl/lib/daytime.b | module/daytime.m | - |  |
| dis/lib/debug.dis | appl/lib/debug.b | module/debug.m | - |  |
| dis/lib/deflate.dis | appl/lib/deflate.b |  | - |  |
| dis/lib/dhcpclient.dis | appl/lib/dhcpclient.b |  | - |  |
| dis/lib/dial.dis | appl/lib/dial.b | module/dial.m | - |  |
| dis/lib/dialog.dis | appl/lib/dialog.b | module/dialog.m | - |  |
| dis/lib/dis.dis | appl/lib/dis.b | module/dis.m | - |  |
| dis/lib/dividers.dis | appl/lib/dividers.b | module/dividers.m | - |  |
| dis/lib/drawmux.dis | appl/wm/drawmux/drawmux.b |  | - |  |
| dis/lib/ecmascript.dis | appl/lib/ecmascript/ecmascript.b | module/ecmascript.m | - |  |
| dis/lib/encoding/base16.dis | appl/lib/encoding/base16.b |  | - |  |
| dis/lib/encoding/base32.dis | appl/lib/encoding/base32.b |  | - |  |
| dis/lib/encoding/base32a.dis | appl/lib/encoding/base32a.b |  | - |  |
| dis/lib/encoding/base64.dis | appl/lib/encoding/base64.b |  | - |  |
| dis/lib/env.dis | appl/lib/env.b | module/env.m | - |  |
| dis/lib/ether.dis | appl/lib/ether.b | module/ether.m | - |  |
| dis/lib/factotum.dis | appl/lib/factotum.b | module/factotum.m | - |  |
| dis/lib/filepat.dis | appl/lib/filepat.b | module/filepat.m | - |  |
| dis/lib/fsfilter.dis | appl/lib/fsfilter.b |  | - |  |
| dis/lib/fslib.dis | appl/lib/fslib.b | module/fslib.m | - |  |
| dis/lib/fsproto.dis | appl/lib/fsproto.b | module/fsproto.m | - |  |
| dis/lib/ftree/cptree.dis | appl/wm/ftree/cptree.b |  | - |  |
| dis/lib/ftree/ftree.dis | appl/wm/ftree/ftree.b |  | - |  |
| dis/lib/ftree/items.dis | appl/wm/ftree/items.b |  | - |  |
| dis/lib/hash.dis | appl/lib/hash.b | module/hash.m | - |  |
| dis/lib/html.dis | appl/lib/html.b | module/html.m | - |  |
| dis/lib/imageremap.dis | appl/lib/imageremap.b |  | - |  |
| dis/lib/inflate.dis | appl/lib/inflate.b | module/inflate.m | - |  |
| dis/lib/ip.dis | appl/lib/ip.b | module/ip.m | - |  |
| dis/lib/ipattr.dis | appl/lib/ipattr.b | module/ipattr.m | - |  |
| dis/lib/ir.dis | appl/lib/ir.b | module/ir.m | - |  |
| dis/lib/irsim.dis | appl/lib/irsim.b |  | - |  |
| dis/lib/itslib.dis | appl/lib/itslib.b | module/itslib.m | - |  |
| dis/lib/keyset.dis | appl/lib/keyset.b | module/keyset.m | - |  |
| dis/lib/libc0.dis | appl/lib/libc0.b | module/libc0.m | - |  |
| dis/lib/lock.dis | appl/lib/lock.b | module/lock.m | - |  |
| dis/lib/login.dis | appl/lib/login.b |  | - |  |
| dis/lib/man.dis | appl/lib/man.b | module/man.m | - |  |
| dis/lib/mash/builtins.dis | appl/cmd/mash/builtins.b |  | - |  |
| dis/lib/mash/history.dis | appl/cmd/mash/history.b |  | - |  |
| dis/lib/mash/make.dis | appl/cmd/mash/make.b |  | - |  |
| dis/lib/mash/tk.dis | appl/cmd/mash/tk.b | module/tk.m | - |  |
| dis/lib/mashlib.dis | appl/cmd/mash/mashlib.b |  | - |  |
| dis/lib/mashparse.dis | appl/cmd/mash/mashparse.b |  | - |  |
| dis/lib/memfs.dis | appl/lib/memfs.b | module/memfs.m | - |  |
| dis/lib/mpeg.dis | appl/lib/mpeg.b | module/mpeg.m | - |  |
| dis/lib/msgio.dis | appl/lib/msgio.b | module/msgio.m | - |  |
| dis/lib/nametree.dis | appl/lib/nametree.b |  | - |  |
| dis/lib/newns.dis | appl/lib/newns.b | module/newns.m | - |  |
| dis/lib/oldauth.dis | appl/lib/oldauth.b | module/oldauth.m | - |  |
| dis/lib/parseman.dis | appl/lib/parseman.b |  | - |  |
| dis/lib/plumbing.dis | appl/lib/plumbing.b |  | - |  |
| dis/lib/plumbmsg.dis | appl/lib/plumbmsg.b | module/plumbmsg.m | - |  |
| dis/lib/pop3.dis | appl/lib/pop3.b | module/pop3.m | - |  |
| dis/lib/popup.dis | appl/lib/popup.b | module/popup.m | - |  |
| dis/lib/print/hp_driver.dis | appl/lib/print/hp_driver.b |  | - |  |
| dis/lib/print/print.dis | appl/lib/print/print.b | module/print.m | - |  |
| dis/lib/print/scaler.dis | appl/lib/print/scaler.b |  | - |  |
| dis/lib/profile.dis | appl/lib/profile.b | module/profile.m | - |  |
| dis/lib/pslib.dis | appl/lib/pslib.b | module/pslib.m | - |  |
| dis/lib/quicktime.dis | appl/lib/quicktime.b | module/quicktime.m | - |  |
| dis/lib/rand.dis | appl/lib/rand.b | module/rand.m | - |  |
| dis/lib/random.dis | appl/lib/random.b |  | - |  |
| dis/lib/readdir.dis | appl/lib/readdir.b | module/readdir.m | - |  |
| dis/lib/readgif.dis | appl/lib/readgif.b |  | - |  |
| dis/lib/readjpg.dis | appl/lib/readjpg.b | module/grid/readjpg.m | - |  |
| dis/lib/readpicfile.dis | appl/lib/readpicfile.b |  | - |  |
| dis/lib/readpng.dis | appl/lib/readpng.b |  | - |  |
| dis/lib/readxbitmap.dis | appl/lib/readxbitmap.b |  | - |  |
| dis/lib/regex.dis | appl/lib/regex.b | module/regex.m | - |  |
| dis/lib/registries.dis | appl/lib/registries.b | module/registries.m | - |  |
| dis/lib/riff.dis | appl/lib/riff.b | module/riff.m | - |  |
| dis/lib/scoretable.dis | appl/lib/scoretable.b | module/scoretable.m | - |  |
| dis/lib/secstore.dis | appl/lib/secstore.b | module/secstore.m | - |  |
| dis/lib/selectfile.dis | appl/lib/selectfile.b | module/selectfile.m | - |  |
| dis/lib/sets.dis | appl/lib/sets.b | module/sets.m | - |  |
| dis/lib/sets32.dis | appl/lib/sets32.b | module/sets32.m | - |  |
| dis/lib/sexprs.dis | appl/lib/sexprs.b | module/sexprs.m | - |  |
| dis/lib/smtp.dis | appl/lib/smtp.b | module/smtp.m | - |  |
| dis/lib/spki/keyreps.dis | appl/cmd/auth/factotum/proto/keyreps.b |  | - |  |
| dis/lib/spki/spki.dis | appl/lib/spki/spki.b | module/spki.m | - |  |
| dis/lib/spki/verifier.dis | appl/lib/spki/verifier.b |  | - |  |
| dis/lib/ssl.dis | appl/lib/ssl.b |  | - |  |
| dis/lib/strinttab.dis | appl/lib/strinttab.b | module/strinttab.m | - |  |
| dis/lib/strokes/buildstrokes.dis | appl/lib/strokes/buildstrokes.b |  | - |  |
| dis/lib/strokes/readstrokes.dis | appl/lib/strokes/readstrokes.b |  | - |  |
| dis/lib/strokes/strokes.dis | appl/lib/strokes/strokes.b | module/strokes.m | - |  |
| dis/lib/styx.dis | appl/lib/styx.b | module/styx.m | - |  |
| dis/lib/styxconv/new2old.dis | appl/lib/styxconv/new2old.b |  | - |  |
| dis/lib/styxconv/old2new.dis | appl/lib/styxconv/old2new.b |  | - |  |
| dis/lib/styxconv/ostyx.dis | appl/lib/styxconv/ostyx.b |  | - |  |
| dis/lib/styxconv/styxconv.dis | appl/lib/styxconv/styxconv.b | module/styxconv.m | - |  |
| dis/lib/styxlib.dis | appl/lib/styxlib.b | module/styxlib.m | - |  |
| dis/lib/styxpersist.dis | appl/lib/styxpersist.b | module/styxpersist.m | - |  |
| dis/lib/styxservers.dis | appl/lib/styxservers.b | module/styxservers.m | - |  |
| dis/lib/tables.dis | appl/lib/tables.b | module/tables.m | - |  |
| dis/lib/tabs.dis | appl/lib/tabs.b | module/tabs.m | - |  |
| dis/lib/tcl_calc.dis | appl/lib/tcl_calc.b |  | - |  |
| dis/lib/tcl_core.dis | appl/lib/tcl_core.b |  | - |  |
| dis/lib/tcl_inthash.dis | appl/lib/tcl_inthash.b |  | - |  |
| dis/lib/tcl_io.dis | appl/lib/tcl_io.b |  | - |  |
| dis/lib/tcl_list.dis | appl/lib/tcl_list.b |  | - |  |
| dis/lib/tcl_modhash.dis | appl/lib/tcl_modhash.b |  | - |  |
| dis/lib/tcl_stack.dis | appl/lib/tcl_stack.b |  | - |  |
| dis/lib/tcl_strhash.dis | appl/lib/tcl_strhash.b |  | - |  |
| dis/lib/tcl_string.dis | appl/lib/tcl_string.b |  | - |  |
| dis/lib/tcl_symhash.dis | appl/lib/tcl_symhash.b |  | - |  |
| dis/lib/tcl_tk.dis | appl/lib/tcl_tk.b |  | - |  |
| dis/lib/tcl_utils.dis | appl/lib/tcl_utils.b |  | - |  |
| dis/lib/timers.dis | appl/lib/timers.b | module/timers.m | - |  |
| dis/lib/translate.dis | appl/lib/translate.b | module/translate.m | - |  |
| dis/lib/url.dis | appl/lib/url.b | module/url.m | - |  |
| dis/lib/usb/usb.dis | appl/lib/usb/usb.b | module/usb.m | - |  |
| dis/lib/usb/usbmass.dis | appl/lib/usb/usbmass.b |  | - |  |
| dis/lib/usb/usbmct.dis | appl/lib/usb/usbmct.b |  | - |  |
| dis/lib/usb/usbmouse.dis | appl/lib/usb/usbmouse.b |  | - |  |
| dis/lib/vac.dis | appl/lib/vac.b | module/vac.m | - |  |
| dis/lib/venti.dis | appl/lib/venti.b | module/venti.m | - |  |
| dis/lib/w3c/css.dis | appl/lib/w3c/css.b | module/css.m | - |  |
| dis/lib/workdir.dis | appl/lib/workdir.b | module/workdir.m | - |  |
| dis/lib/writegif.dis | appl/lib/writegif.b |  | - |  |
| dis/lib/xml.dis | appl/lib/xml.b | module/xml.m | - |  |

### 3. Shell and commands - sh module, sh builtins, tiny, top-level commands - 119 rows

| Path | Limbo source | Interface | Boot | Notes |
|---|---|---|---|---|
| dis/sh.dis | appl/cmd/sh/sh.b | module/sh.m | P1 | zx-twin /dis/sh.zx (appl/cmd/sh/sh.zi, `mk install-zx`), the shell of a Dis-free guest; tests/sh: all cases match sh.dis; open: the tk, mload, mk and alphabet builtin modules, and the step budget (a long CPU-bound script ends a ZX program). A Dis guest keeps sh.dis for `sh`. Limbo loaders of Sh left: 9srvfs 9win auxi/rstyxd dial ed fs/{eval,exec,pipe,query,run} iostats itest listen m4 mk mount p rawdbfs rioimport runas styxlisten styxmon time wmimport xargs (appl/cmd), alphabet/{alphabet,eval,auxi/endpoints,auxi/rexecsrv,fs/exec,fs/pipe,fs/query,fs/run,grid/farm,grid/rexec,main/filter,main/parse,main/pretty,main/rewrite,main/unparse}, grid/{cpupool,reglisten,regstyxlisten,remotelogon}, wm/{ftree/ftree,remotelogon,sh,toolbar,vt,wm}, sh/mload |
| dis/9win.dis | appl/cmd/9win.b |  | - |  |
| dis/B.dis | appl/cmd/B.b |  | - |  |
| dis/acme.dis | appl/acme/acme.b |  | - |  |
| dis/ar.dis | appl/cmd/ar.b |  | - |  |
| dis/asm.dis | appl/cmd/asm/asm.b|appl/cmd/limbo/asm.b |  | - |  |
| dis/auhdr.dis | appl/cmd/auplay.b (copy rule) |  | - |  |
| dis/auplay.dis | appl/cmd/auplay.b |  | - |  |
| dis/bind.dis | appl/cmd/bind.b |  | - |  |
| dis/bytes.dis | appl/cmd/bytes.b |  | - |  |
| dis/cal.dis | appl/cmd/cal.b |  | - |  |
| dis/calc.dis | appl/cmd/calc.b |  | - |  |
| dis/cd.dis | appl/cmd/cd.b |  | - |  |
| dis/cddb.dis | appl/cmd/cddb.b |  | - |  |
| dis/charon.dis | appl/charon/charon.b |  | - |  |
| dis/cmp.dis | appl/cmd/cmp.b |  | - |  |
| dis/comm.dis | appl/cmd/comm.b |  | - |  |
| dis/cook.dis | appl/cmd/cook.b |  | - |  |
| dis/cprof.dis | appl/cmd/cprof.b |  | - |  |
| dis/cpu.dis | appl/cmd/cpu.b |  | - |  |
| dis/crypt.dis | appl/cmd/crypt.b | module/crypt.m | - |  |
| dis/dd.dis | appl/cmd/dd.b |  | - |  |
| dis/dial.dis | appl/cmd/dial.b | module/dial.m | - |  |
| dis/diff.dis | appl/cmd/diff.b |  | - |  |
| dis/disdep.dis | appl/cmd/disdep.b |  | - |  |
| dis/disdump.dis | appl/cmd/disdump.b |  | - |  |
| dis/du.dis | appl/cmd/du.b |  | - |  |
| dis/ed.dis | appl/cmd/ed.b |  | - |  |
| dis/emuinit.dis | appl/cmd/emuinit.b |  | - |  |
| dis/fc.dis | appl/cmd/fc.b |  | - |  |
| dis/fcp.dis | appl/cmd/fcp.b |  | - |  |
| dis/fmt.dis | appl/cmd/fmt.b |  | - |  |
| dis/fortune.dis | appl/cmd/fortune.b |  | - |  |
| dis/freq.dis | appl/cmd/freq.b |  | - |  |
| dis/fs.dis | appl/cmd/fs.b | module/alphabet/fs.m | - |  |
| dis/ftest.dis | appl/cmd/ftest.b |  | - |  |
| dis/getauthinfo.dis | appl/cmd/getauthinfo.b |  | - |  |
| dis/gettar.dis | appl/cmd/gettar.b |  | - |  |
| dis/grep.dis | appl/cmd/grep.b |  | - |  |
| dis/gunzip.dis | appl/cmd/gunzip.b |  | - |  |
| dis/gzip.dis | appl/cmd/gzip.b |  | - |  |
| dis/idea.dis | appl/cmd/idea.b |  | - |  |
| dis/import.dis | appl/cmd/import.b |  | - |  |
| dis/iostats.dis | appl/cmd/iostats.b |  | - |  |
| dis/itest.dis | appl/cmd/itest.b |  | - |  |
| dis/itreplay.dis | appl/cmd/itreplay.b |  | - |  |
| dis/kill.dis | appl/cmd/kill.b |  | - |  |
| dis/limbo.dis | appl/cmd/limbo/limbo.b |  | - |  |
| dis/logfile.dis | appl/cmd/logfile.b |  | - |  |
| dis/look.dis | appl/cmd/look.b |  | - |  |
| dis/lstar.dis | appl/cmd/lstar.b |  | - |  |
| dis/m4.dis | appl/cmd/m4.b |  | - |  |
| dis/man2html.dis | appl/cmd/man2html.b |  | - |  |
| dis/man2txt.dis | appl/cmd/man2txt.b |  | - |  |
| dis/mash.dis | appl/cmd/mash/mash.b |  | - |  |
| dis/mc.dis | appl/cmd/mc.b |  | - |  |
| dis/mdb.dis | appl/cmd/mdb.b |  | - |  |
| dis/metamorph.dis | appl/cmd/metamorph.b |  | - |  |
| dis/mk.dis | appl/cmd/mk/mk.b |  | - |  |
| dis/mount.dis | appl/cmd/mount.b |  | - |  |
| dis/mouse.dis | appl/cmd/mouse.b |  | - |  |
| dis/mprof.dis | appl/cmd/mprof.b |  | - |  |
| dis/mv.dis | appl/cmd/mv.b |  | - |  |
| dis/netkey.dis | appl/cmd/netkey.b |  | - |  |
| dis/ns.dis | appl/cmd/ns.b |  | - |  |
| dis/nsbuild.dis | appl/cmd/nsbuild.b |  | - |  |
| dis/os.dis | appl/cmd/os.b |  | - |  |
| dis/plumb.dis | appl/cmd/plumb.b |  | - |  |
| dis/prof.dis | appl/cmd/prof.b |  | - |  |
| dis/puttar.dis | appl/cmd/puttar.b |  | - |  |
| dis/raw2iaf.dis | appl/cmd/raw2iaf.b |  | - |  |
| dis/rcmd.dis | appl/cmd/rcmd.b |  | - |  |
| dis/rdp.dis | appl/cmd/rdp.b |  | - |  |
| dis/rioimport.dis | appl/cmd/rioimport.b |  | - |  |
| dis/sed.dis | appl/cmd/sed.b |  | - |  |
| dis/sendmail.dis | appl/cmd/sendmail.b |  | - |  |
| dis/sh/alphabet.dis | appl/alphabet/alphabet.b | module/alphabet.m | - |  |
| dis/sh/arg.dis | appl/cmd/sh/arg.b | module/arg.m | - | ported into /dis/sh.zx (appl/cmd/sh/shell_small.zi); loaded only by sh.dis |
| dis/sh/csv.dis | appl/cmd/sh/csv.b | module/csv.m | - | ported into /dis/sh.zx (appl/cmd/sh/shell_csv.zi); loaded only by sh.dis |
| dis/sh/echo.dis | appl/cmd/sh/echo.b |  | - | ported into /dis/sh.zx (appl/cmd/sh/shell_small.zi); loaded only by sh.dis |
| dis/sh/expr.dis | appl/cmd/sh/expr.b |  | - | ported into /dis/sh.zx (appl/cmd/sh/shell_expr.zi); loaded only by sh.dis |
| dis/sh/file2chan.dis | appl/cmd/sh/file2chan.b |  | - | ported into /dis/sh.zx (appl/cmd/sh/shell_file2chan.zi); loaded only by sh.dis |
| dis/sh/mk.dis | appl/cmd/mk/mk.b |  | - | open: needs a Ziran mk (appl/cmd/mk/mk.b), the shell builtin form included |
| dis/sh/mload.dis | appl/cmd/sh/mload.b |  | - | open: loads Dis modules as builtin namespaces; ZX has no loading of modules while running |
| dis/sh/mpexpr.dis | appl/cmd/sh/mpexpr.b |  | - | ported into /dis/sh.zx (appl/cmd/sh/shell_mpexpr.zi, over taijios_keyring Big); loaded only by sh.dis |
| dis/sh/regex.dis | appl/cmd/sh/regex.b | module/regex.m | - | ported into /dis/sh.zx (appl/cmd/sh/shell_regex.zi); loaded only by sh.dis |
| dis/sh/sexprs.dis | appl/cmd/sh/sexprs.b | module/sexprs.m | - | ported into /dis/sh.zx (appl/cmd/sh/shell_sexprs.zi); loaded only by sh.dis |
| dis/sh/sh.dis | appl/cmd/sh/sh.b | module/sh.m | - |  |
| dis/sh/std.dis | appl/cmd/sh/std.b |  | - | ported into /dis/sh.zx (appl/cmd/sh/shell_std.zi); loaded only by sh.dis |
| dis/sh/string.dis | appl/cmd/sh/string.b | module/string.m | - | ported into /dis/sh.zx (appl/cmd/sh/shell_string.zi); loaded only by sh.dis |
| dis/sh/test.dis | appl/cmd/sh/test.b |  | - | ported into /dis/sh.zx (appl/cmd/sh/shell_small.zi); loaded only by sh.dis |
| dis/sh/tk.dis | appl/cmd/sh/tk.b | module/tk.m | - | open: sh.zx has no Tk; the module needs a ZX Tk window API (lib/sh/win uses it) |
| dis/sort.dis | appl/cmd/sort.b | module/sort.m | - |  |
| dis/src.dis | appl/cmd/src.b |  | - |  |
| dis/stack.dis | appl/cmd/stack.b |  | - |  |
| dis/stackv.dis | appl/cmd/stackv.b |  | - |  |
| dis/stream.dis | appl/cmd/stream.b |  | - |  |
| dis/styxchat.dis | appl/cmd/styxchat.b |  | - |  |
| dis/styxlisten.dis | appl/cmd/styxlisten.b |  | - |  |
| dis/styxmon.dis | appl/cmd/styxmon.b |  | - |  |
| dis/tail.dis | appl/cmd/tail.b |  | - |  |
| dis/tcs.dis | appl/cmd/tcs.b |  | - |  |
| dis/telnet.dis | appl/cmd/telnet.b |  | - |  |
| dis/time.dis | appl/cmd/time.b |  | - |  |
| dis/tkcmd.dis | appl/cmd/tkcmd.b |  | - |  |
| dis/touchcal.dis | appl/cmd/touchcal.b |  | - |  |
| dis/tsort.dis | appl/cmd/tsort.b |  | - |  |
| dis/unicode.dis | appl/cmd/unicode.b |  | - |  |
| dis/units.dis | appl/cmd/units.b |  | - |  |
| dis/vacget.dis | appl/cmd/vacget.b |  | - |  |
| dis/vacput.dis | appl/cmd/vacput.b |  | - |  |
| dis/wav2iaf.dis | appl/cmd/wav2iaf.b |  | - |  |
| dis/webgrab.dis | appl/cmd/webgrab.b |  | - |  |
| dis/wish.dis | appl/cmd/wish.b |  | - |  |
| dis/wmexport.dis | appl/cmd/wmexport.b |  | - |  |
| dis/wmimport.dis | appl/cmd/wmimport.b |  | - |  |
| dis/xargs.dis | appl/cmd/xargs.b |  | - |  |
| dis/xd.dis | appl/cmd/xd.b |  | - |  |
| dis/yacc.dis | appl/cmd/yacc.b |  | - |  |

### 4. Services - storage, network, name, auth, collab, usb and aux daemons - 96 rows

| Path | Limbo source | Interface | Boot | Notes |
|---|---|---|---|---|
| dis/9660srv.dis | appl/cmd/9660srv.b |  | - |  |
| dis/9export.dis | appl/cmd/9export.b |  | - |  |
| dis/9srvfs.dis | appl/cmd/9srvfs.b |  | - |  |
| dis/archfs.dis | appl/cmd/archfs.b |  | - |  |
| dis/auth/changelogin.dis | appl/cmd/auth/changelogin.b |  | - |  |
| dis/auth/convpasswd.dis | appl/cmd/auth/convpasswd.b |  | - |  |
| dis/auth/factotum.dis | appl/cmd/auth/factotum/factotum.b | module/factotum.m | - |  |
| dis/auth/feedkey.dis | appl/cmd/auth/factotum/feedkey.b |  | - |  |
| dis/auth/infauth.dis | appl/cmd/auth/factotum/proto/infauth.b |  | - |  |
| dis/auth/keyfs.dis | appl/cmd/auth/keyfs.b |  | - |  |
| dis/auth/keysrv.dis | appl/cmd/auth/keysrv.b |  | - |  |
| dis/auth/logind.dis | appl/cmd/auth/logind.b |  | - |  |
| dis/auth/mkauthinfo.dis | appl/cmd/auth/mkauthinfo.b |  | - |  |
| dis/auth/passwd.dis | appl/cmd/auth/passwd.b |  | - |  |
| dis/auth/proto/authquery.dis | appl/cmd/auth/factotum/proto/authquery.b |  | - |  |
| dis/auth/proto/infauth.dis | appl/cmd/auth/factotum/proto/infauth.b |  | - |  |
| dis/auth/proto/p9any.dis | appl/cmd/auth/factotum/proto/p9any.b |  | - |  |
| dis/auth/proto/pass.dis | appl/cmd/auth/factotum/proto/pass.b |  | - |  |
| dis/auth/proto/rsa.dis | appl/cmd/auth/factotum/proto/rsa.b |  | - |  |
| dis/auth/rpc.dis | appl/cmd/auth/factotum/rpc.b |  | - |  |
| dis/auth/secstore.dis | appl/cmd/auth/secstore.b | module/secstore.m | - |  |
| dis/auth/signer.dis | appl/cmd/auth/signer.b |  | - |  |
| dis/auxi/camera.dis | appl/demo/camera/camera.b |  | - |  |
| dis/auxi/cpuslave.dis | appl/cmd/auxi/cpuslave.b |  | - |  |
| dis/auxi/fpgaload.dis | appl/cmd/auxi/fpgaload.b |  | - |  |
| dis/auxi/mangaload.dis | appl/cmd/auxi/mangaload.b |  | - |  |
| dis/auxi/odbcmnt.dis | appl/demo/odbc/odbcmnt.b |  | - |  |
| dis/auxi/pcmcia.dis | appl/cmd/auxi/pcmcia.b |  | - |  |
| dis/auxi/rdbgsrv.dis | appl/cmd/auxi/rdbgsrv.b |  | - |  |
| dis/auxi/rstyxd.dis | appl/cmd/auxi/rstyxd.b |  | - |  |
| dis/auxi/wbsrv.dis | unknown |  | - |  |
| dis/collab/clients/chat.dis | appl/collab/clients/chat.b |  | - |  |
| dis/collab/clients/poll.dis | appl/collab/clients/poll.b |  | - |  |
| dis/collab/clients/poller.dis | appl/collab/clients/poller.b |  | - |  |
| dis/collab/clients/whiteboard.dis | appl/collab/clients/whiteboard.b |  | - |  |
| dis/collab/collabsrv.dis | appl/collab/collabsrv.b |  | - |  |
| dis/collab/connect.dis | appl/collab/connect.b |  | - |  |
| dis/collab/lib/messages.dis | appl/collab/lib/messages.b |  | - |  |
| dis/collab/proxy.dis | appl/collab/proxy.b |  | - |  |
| dis/collab/servers/chatsrv.dis | appl/collab/servers/chatsrv.b |  | - |  |
| dis/collab/servers/memfssrv.dis | appl/collab/servers/memfssrv.b |  | - |  |
| dis/collab/servers/mpx.dis | appl/collab/servers/mpx.b |  | - |  |
| dis/collab/servers/wbsrv.dis | appl/collab/servers/wbsrv.b |  | - |  |
| dis/collab/srvmgr.dis | appl/collab/srvmgr.b |  | - |  |
| dis/dbfs.dis | appl/cmd/dbfs.b |  | - |  |
| dis/dossrv.dis | appl/cmd/dossrv.b |  | - |  |
| dis/ftpfs.dis | appl/cmd/ftpfs.b |  | - |  |
| dis/ip/bootpd.dis | appl/cmd/ip/bootpd.b |  | - |  |
| dis/ip/dhcp.dis | appl/cmd/ip/dhcp.b | module/dhcp.m | - |  |
| dis/ip/nppp/modem.dis | appl/cmd/ip/nppp/modem.b |  | - |  |
| dis/ip/nppp/ppplink.dis | appl/cmd/ip/nppp/ppplink.b |  | - |  |
| dis/ip/nppp/script.dis | appl/cmd/ip/nppp/script.b |  | - |  |
| dis/ip/ping.dis | appl/cmd/ip/ping.b |  | - |  |
| dis/ip/ppp/modem.dis | appl/cmd/ip/ppp/modem.b |  | - |  |
| dis/ip/ppp/pppclient.dis | appl/cmd/ip/ppp/pppclient.b |  | - |  |
| dis/ip/ppp/pppdial.dis | appl/cmd/ip/ppp/pppdial.b |  | - |  |
| dis/ip/ppp/pppgui.dis | appl/cmd/ip/ppp/pppgui.b |  | - |  |
| dis/ip/ppp/ppptest.dis | appl/cmd/ip/ppp/ppptest.b |  | - |  |
| dis/ip/ppp/script.dis | appl/cmd/ip/ppp/script.b |  | - |  |
| dis/ip/rip.dis | appl/cmd/ip/rip.b |  | - |  |
| dis/ip/sntp.dis | appl/cmd/ip/sntp.b |  | - |  |
| dis/ip/tftpd.dis | appl/cmd/ip/tftpd.b |  | - |  |
| dis/ip/virgild.dis | appl/cmd/ip/virgild.b |  | - |  |
| dis/listen.dis | appl/cmd/listen.b |  | - |  |
| dis/lockfs.dis | appl/cmd/lockfs.b |  | - |  |
| dis/memfs.dis | appl/cmd/memfs.b | module/memfs.m | - |  |
| dis/ndb/cs.dis | appl/cmd/ndb/cs.b |  | - |  |
| dis/ndb/dns.dis | appl/cmd/ndb/dns.b |  | - |  |
| dis/ndb/registry.dis | appl/cmd/ndb/registry.b |  | - |  |
| dis/plumber.dis | appl/cmd/plumber.b |  | - |  |
| dis/ramfile.dis | appl/cmd/ramfile.b |  | - |  |
| dis/rawdbfs.dis | appl/cmd/rawdbfs.b |  | - |  |
| dis/spki/verify.dis | appl/cmd/spki/verify.b |  | - |  |
| dis/svc/httpd/alarms.dis | appl/svc/httpd/alarms.b |  | - |  |
| dis/svc/httpd/cache.dis | appl/svc/httpd/cache.b |  | - |  |
| dis/svc/httpd/cgiparse.dis | appl/svc/httpd/cgiparse.b |  | - |  |
| dis/svc/httpd/contents.dis | appl/svc/httpd/contents.b |  | - |  |
| dis/svc/httpd/date.dis | appl/svc/httpd/date.b |  | - |  |
| dis/svc/httpd/echo.dis | appl/svc/httpd/echo.b |  | - |  |
| dis/svc/httpd/httpd.dis | appl/svc/httpd/httpd.b |  | - |  |
| dis/svc/httpd/imagemap.dis | appl/svc/httpd/imagemap.b |  | - |  |
| dis/svc/httpd/parser.dis | appl/svc/httpd/parser.b |  | - |  |
| dis/svc/httpd/redirect.dis | appl/svc/httpd/redirect.b |  | - |  |
| dis/svc/httpd/stats.dis | appl/svc/httpd/stats.b |  | - |  |
| dis/svc/webget/date.dis | appl/svc/webget/date.b |  | - |  |
| dis/svc/webget/file.dis | appl/svc/webget/file.b |  | - |  |
| dis/svc/webget/ftp.dis | appl/svc/webget/ftp.b |  | - |  |
| dis/svc/webget/http.dis | appl/svc/webget/http.b |  | - |  |
| dis/svc/webget/image2enc.dis | appl/svc/webget/image2enc.b |  | - |  |
| dis/svc/webget/message.dis | appl/svc/webget/message.b |  | - |  |
| dis/svc/webget/webget.dis | appl/svc/webget/webget.b | module/webget.m | - |  |
| dis/svc/webget/wgutils.dis | appl/svc/webget/wgutils.b |  | - |  |
| dis/tarfs.dis | appl/cmd/tarfs.b |  | - |  |
| dis/trfs.dis | appl/cmd/trfs.b |  | - |  |
| dis/usb/usbd.dis | appl/cmd/usb/usbd.b |  | - |  |
| dis/vacfs.dis | appl/cmd/vacfs.b |  | - |  |

### 5. WM apps - dis/wm/** desktop applications (deletions go through the desktop-core owner) - 48 rows

| Path | Limbo source | Interface | Boot | Notes |
|---|---|---|---|---|
| dis/wm/avi.dis | appl/wm/avi.b |  | - |  |
| dis/wm/bounce.dis | appl/wm/bounce.b |  | - |  |
| dis/wm/brutus.dis | appl/wm/brutus.b | module/brutus.m | - |  |
| dis/wm/brutus/excerpt.dis | appl/wm/brutus/excerpt.b |  | - |  |
| dis/wm/brutus/image.dis | appl/wm/brutus/image.b |  | - |  |
| dis/wm/brutus/mod.dis | appl/wm/brutus/mod.b |  | - |  |
| dis/wm/brutus/table.dis | appl/wm/brutus/table.b |  | - |  |
| dis/wm/c4.dis | appl/wm/c4.b |  | - |  |
| dis/wm/calendar.dis | appl/wm/calendar.b |  | - |  |
| dis/wm/chat.dis | unknown |  | - |  |
| dis/wm/coffee.dis | appl/wm/coffee.b |  | - |  |
| dis/wm/collide.dis | appl/wm/collide.b |  | - |  |
| dis/wm/colors.dis | appl/wm/colors.b |  | - |  |
| dis/wm/cprof.dis | appl/wm/cprof.b |  | - |  |
| dis/wm/date.dis | appl/wm/date.b |  | - |  |
| dis/wm/deb.dis | appl/wm/deb.b |  | - |  |
| dis/wm/debdata.dis | appl/wm/debdata.b |  | - |  |
| dis/wm/debsrc.dis | appl/wm/debsrc.b |  | - |  |
| dis/wm/dmview.dis | appl/wm/drawmux/dmview.b |  | - |  |
| dis/wm/dmwm.dis | appl/wm/drawmux/dmwm.b |  | - |  |
| dis/wm/edit.dis | appl/wm/edit.b |  | - |  |
| dis/wm/filename.dis | appl/wm/filename.b |  | - |  |
| dis/wm/ftree.dis | appl/wm/ftree/ftree.b |  | - |  |
| dis/wm/getauthinfo.dis | appl/wm/getauthinfo.b |  | - |  |
| dis/wm/keyboard.dis | appl/wm/keyboard.b | module/keyboard.m | - |  |
| dis/wm/logon.dis | appl/wm/logon.b |  | - |  |
| dis/wm/man.dis | appl/wm/man.b | module/man.m | - |  |
| dis/wm/mand.dis | appl/wm/mand.b |  | - |  |
| dis/wm/mash.dis | appl/wm/mash.b |  | - |  |
| dis/wm/mpeg.dis | appl/wm/mpeg.b | module/mpeg.m | - |  |
| dis/wm/mprof.dis | appl/wm/mprof.b |  | - |  |
| dis/wm/pen.dis | appl/wm/pen.b |  | - |  |
| dis/wm/polyhedra.dis | appl/wm/polyhedra.b | module/math/polyhedra.m | - |  |
| dis/wm/prof.dis | appl/wm/prof.b |  | - |  |
| dis/wm/readmail.dis | appl/wm/readmail.b |  | - |  |
| dis/wm/remotelogon.dis | appl/wm/remotelogon.b |  | - |  |
| dis/wm/reversi.dis | appl/wm/reversi.b |  | - |  |
| dis/wm/rmtdir.dis | appl/wm/rmtdir.b |  | - |  |
| dis/wm/rt.dis | appl/wm/rt.b |  | - |  |
| dis/wm/sendmail.dis | appl/wm/sendmail.b |  | - |  |
| dis/wm/sh.dis | appl/wm/sh.b | module/sh.m | - |  |
| dis/wm/smenu.dis | appl/wm/smenu.b |  | - |  |
| dis/wm/task.dis | appl/wm/task.b |  | - |  |
| dis/wm/telnet.dis | appl/wm/telnet.b |  | - |  |
| dis/wm/unibrowse.dis | appl/wm/unibrowse.b |  | - |  |
| dis/wm/vt.dis | appl/wm/vt.b |  | - |  |
| dis/wm/wish.dis | appl/wm/wish.b |  | - |  |
| dis/wm/wmplay.dis | appl/wm/wmplay.b |  | - |  |

### 6. Acme - editor family - 25 rows

| Path | Limbo source | Interface | Boot | Notes |
|---|---|---|---|---|
| dis/acme/acme.dis | appl/acme/acme.b |  | - |  |
| dis/acme/buff.dis | appl/acme/buff.b |  | - |  |
| dis/acme/col.dis | appl/acme/col.b |  | - |  |
| dis/acme/dat.dis | appl/acme/dat.b |  | - |  |
| dis/acme/disk.dis | appl/acme/disk.b |  | - |  |
| dis/acme/ecmd.dis | appl/acme/ecmd.b |  | - |  |
| dis/acme/edit.dis | appl/acme/edit.b |  | - |  |
| dis/acme/elog.dis | appl/acme/elog.b |  | - |  |
| dis/acme/exec.dis | appl/acme/exec.b |  | - |  |
| dis/acme/file.dis | appl/acme/file.b |  | - |  |
| dis/acme/frame.dis | appl/acme/frame.b |  | - |  |
| dis/acme/fsys.dis | appl/acme/fsys.b |  | - |  |
| dis/acme/graph.dis | appl/acme/graph.b |  | - |  |
| dis/acme/gui.dis | appl/acme/gui.b |  | - |  |
| dis/acme/guiwm.dis | unknown |  | - |  |
| dis/acme/look.dis | appl/acme/look.b |  | - |  |
| dis/acme/regx.dis | appl/acme/regx.b |  | - |  |
| dis/acme/row.dis | appl/acme/row.b |  | - |  |
| dis/acme/scrl.dis | appl/acme/scrl.b |  | - |  |
| dis/acme/styxaux.dis | appl/acme/styxaux.b |  | - |  |
| dis/acme/text.dis | appl/acme/text.b |  | - |  |
| dis/acme/time.dis | appl/acme/time.b |  | - |  |
| dis/acme/util.dis | appl/acme/util.b |  | - |  |
| dis/acme/wind.dis | appl/acme/wind.b |  | - |  |
| dis/acme/xfid.dis | appl/acme/xfid.b |  | - |  |

### 7. Charon - web browser family - 15 rows

| Path | Limbo source | Interface | Boot | Notes |
|---|---|---|---|---|
| dis/charon/build.dis | appl/charon/build.b |  | - |  |
| dis/charon/chutils.dis | appl/charon/chutils.b |  | - |  |
| dis/charon/cookiesrv.dis | appl/charon/cookiesrv.b |  | - |  |
| dis/charon/ctype.dis | appl/charon/ctype.b |  | - |  |
| dis/charon/date.dis | appl/charon/date.b |  | - |  |
| dis/charon/event.dis | appl/charon/event.b |  | - |  |
| dis/charon/file.dis | appl/charon/file.b |  | - |  |
| dis/charon/ftp.dis | appl/charon/ftp.b |  | - |  |
| dis/charon/gui.dis | appl/charon/gui.b |  | - |  |
| dis/charon/http.dis | appl/charon/http.b |  | - |  |
| dis/charon/img.dis | appl/charon/img.b |  | - |  |
| dis/charon/jscript.dis | appl/charon/jscript.b |  | - |  |
| dis/charon/layout.dis | appl/charon/layout.b |  | - |  |
| dis/charon/lex.dis | appl/charon/lex.b |  | - |  |
| dis/charon/url.dis | appl/charon/url.b | module/url.m | - |  |

### 8. Alphabet - gridded documents family - 83 rows

| Path | Limbo source | Interface | Boot | Notes |
|---|---|---|---|---|
| dis/alphabet/abc.dis | appl/alphabet/abc/abc.b|appl/alphabet/typesets/abc.b | module/alphabet/abc.m | - |  |
| dis/alphabet/abc/abc.dis | appl/alphabet/abc/abc.b | module/alphabet/abc.m | - |  |
| dis/alphabet/abc/autoconvert.dis | appl/alphabet/abc/autoconvert.b |  | - |  |
| dis/alphabet/abc/autodeclare.dis | appl/alphabet/abc/autodeclare.b |  | - |  |
| dis/alphabet/abc/declare.dis | appl/alphabet/abc/declare.b |  | - |  |
| dis/alphabet/abc/declares.dis | appl/alphabet/abc/declares.b |  | - |  |
| dis/alphabet/abc/define.dis | appl/alphabet/abc/define.b |  | - |  |
| dis/alphabet/abc/eval.dis | appl/alphabet/abc/eval.b |  | - |  |
| dis/alphabet/abc/import.dis | appl/alphabet/abc/import.b |  | - |  |
| dis/alphabet/abc/rewrite.dis | appl/alphabet/abc/rewrite.b |  | - |  |
| dis/alphabet/abc/type.dis | appl/alphabet/abc/type.b |  | - |  |
| dis/alphabet/abc/typeset.dis | appl/alphabet/abc/typeset.b |  | - |  |
| dis/alphabet/abc/undeclare.dis | appl/alphabet/abc/undeclare.b |  | - |  |
| dis/alphabet/abctypes.dis | appl/alphabet/typesets/abctypes.b | module/alphabet/abctypes.m | - |  |
| dis/alphabet/alphabet.dis | appl/alphabet/alphabet.b | module/alphabet.m | - |  |
| dis/alphabet/alphabet.shmod.dis | appl/alphabet/alphabet.shmod.b |  | - |  |
| dis/alphabet/endpoints.dis | appl/alphabet/auxi/endpoints.b | module/alphabet/endpoints.m | - |  |
| dis/alphabet/endpointsrv.dis | appl/alphabet/auxi/endpointsrv.b |  | - |  |
| dis/alphabet/eval.dis | appl/alphabet/eval.b |  | - |  |
| dis/alphabet/extvalues.dis | appl/alphabet/extvalues.b | module/alphabet/extvalues.m | - |  |
| dis/alphabet/fs.dis | appl/alphabet/typesets/fs.b | module/alphabet/fs.m | - |  |
| dis/alphabet/fs/and.dis | appl/alphabet/fs/and.b |  | - |  |
| dis/alphabet/fs/bundle.dis | appl/alphabet/fs/bundle.b | module/bundle.m | - |  |
| dis/alphabet/fs/chstat.dis | appl/alphabet/fs/chstat.b |  | - |  |
| dis/alphabet/fs/compose.dis | appl/alphabet/fs/compose.b |  | - |  |
| dis/alphabet/fs/depth.dis | appl/alphabet/fs/depth.b |  | - |  |
| dis/alphabet/fs/entries.dis | appl/alphabet/fs/entries.b |  | - |  |
| dis/alphabet/fs/exec.dis | appl/alphabet/fs/exec.b |  | - |  |
| dis/alphabet/fs/filter.dis | appl/alphabet/fs/filter.b | module/filter.m | - |  |
| dis/alphabet/fs/ls.dis | appl/alphabet/fs/ls.b |  | - |  |
| dis/alphabet/fs/match.dis | appl/alphabet/fs/match.b |  | - |  |
| dis/alphabet/fs/merge.dis | appl/alphabet/fs/merge.b |  | - |  |
| dis/alphabet/fs/mergewrite.dis | appl/alphabet/fs/mergewrite.b |  | - |  |
| dis/alphabet/fs/mode.dis | appl/alphabet/fs/mode.b |  | - |  |
| dis/alphabet/fs/newer.dis | appl/alphabet/fs/newer.b |  | - |  |
| dis/alphabet/fs/not.dis | appl/alphabet/fs/not.b |  | - |  |
| dis/alphabet/fs/or.dis | appl/alphabet/fs/or.b |  | - |  |
| dis/alphabet/fs/path.dis | appl/alphabet/fs/path.b |  | - |  |
| dis/alphabet/fs/pipe.dis | appl/alphabet/fs/pipe.b |  | - |  |
| dis/alphabet/fs/print.dis | appl/alphabet/fs/print.b | module/print.m | - |  |
| dis/alphabet/fs/proto.dis | appl/alphabet/fs/proto.b |  | - |  |
| dis/alphabet/fs/query.dis | appl/alphabet/fs/query.b |  | - |  |
| dis/alphabet/fs/run.dis | appl/alphabet/fs/run.b |  | - |  |
| dis/alphabet/fs/select.dis | appl/alphabet/fs/select.b |  | - |  |
| dis/alphabet/fs/setroot.dis | appl/alphabet/fs/setroot.b |  | - |  |
| dis/alphabet/fs/size.dis | appl/alphabet/fs/size.b |  | - |  |
| dis/alphabet/fs/unbundle.dis | appl/alphabet/fs/unbundle.b | module/unbundle.m | - |  |
| dis/alphabet/fs/walk.dis | appl/alphabet/fs/walk.b |  | - |  |
| dis/alphabet/fs/write.dis | appl/alphabet/fs/write.b |  | - |  |
| dis/alphabet/fsfilter.dis | appl/alphabet/auxi/fsfilter.b |  | - |  |
| dis/alphabet/fstypes.dis | appl/alphabet/typesets/fstypes.b | module/alphabet/fstypes.m | - |  |
| dis/alphabet/grid.dis | appl/alphabet/typesets/grid.b | module/alphabet/grid.m | - |  |
| dis/alphabet/grid/farm.dis | appl/alphabet/grid/farm.b |  | - |  |
| dis/alphabet/grid/line2rec.dis | appl/alphabet/grid/line2rec.b |  | - |  |
| dis/alphabet/grid/local.dis | appl/alphabet/grid/local.b |  | - |  |
| dis/alphabet/grid/remote.dis | appl/alphabet/grid/remote.b |  | - |  |
| dis/alphabet/grid/rexec.dis | appl/alphabet/grid/rexec.b |  | - |  |
| dis/alphabet/gridtypes.dis | appl/alphabet/typesets/gridtypes.b | module/alphabet/gridtypes.m | - |  |
| dis/alphabet/main/auth.dis | appl/alphabet/main/auth.b |  | - |  |
| dis/alphabet/main/cat.dis | appl/alphabet/main/cat.b |  | - |  |
| dis/alphabet/main/create.dis | appl/alphabet/main/create.b |  | - |  |
| dis/alphabet/main/dial.dis | appl/alphabet/main/dial.b | module/dial.m | - |  |
| dis/alphabet/main/echo.dis | appl/alphabet/main/echo.b |  | - |  |
| dis/alphabet/main/env.dis | unknown | module/env.m | - |  |
| dis/alphabet/main/export.dis | appl/alphabet/main/export.b |  | - |  |
| dis/alphabet/main/fd.dis | appl/alphabet/main/fd.b |  | - |  |
| dis/alphabet/main/filter.dis | appl/alphabet/main/filter.b | module/filter.m | - |  |
| dis/alphabet/main/mount.dis | appl/alphabet/main/mount.b |  | - |  |
| dis/alphabet/main/par.dis | appl/alphabet/main/par.b |  | - |  |
| dis/alphabet/main/parse.dis | appl/alphabet/main/parse.b |  | - |  |
| dis/alphabet/main/pretty.dis | appl/alphabet/main/pretty.b |  | - |  |
| dis/alphabet/main/print.dis | appl/alphabet/main/print.b | module/print.m | - |  |
| dis/alphabet/main/read.dis | appl/alphabet/main/read.b |  | - |  |
| dis/alphabet/main/readall.dis | appl/alphabet/main/readall.b |  | - |  |
| dis/alphabet/main/rewrite.dis | appl/alphabet/main/rewrite.b |  | - |  |
| dis/alphabet/main/seq.dis | appl/alphabet/main/seq.b |  | - |  |
| dis/alphabet/main/unparse.dis | appl/alphabet/main/unparse.b |  | - |  |
| dis/alphabet/main/w2fd.dis | appl/alphabet/main/w2fd.b |  | - |  |
| dis/alphabet/main/wait.dis | appl/alphabet/main/wait.b | module/wait.m | - |  |
| dis/alphabet/mktypeset.dis | unknown |  | - |  |
| dis/alphabet/proxy.dis | appl/alphabet/proxy.b |  | - |  |
| dis/alphabet/reports.dis | appl/alphabet/reports.b | module/alphabet/reports.m | - |  |
| dis/alphabet/rexecsrv.dis | appl/alphabet/auxi/rexecsrv.b |  | - |  |

### 9. Spree - multiuser engine family - 0 rows

| Path | Limbo source | Interface | Boot | Notes |
|---|---|---|---|---|

### 10. Grid - computing grid family - 5 rows

| Path | Limbo source | Interface | Boot | Notes |
|---|---|---|---|---|
| dis/grid/cpupool.dis | appl/grid/cpupool.b |  | - | blocked: multi-goroutine shared-state proxy/rcmd/file2chan + sh->run in ZX host API |
| dis/grid/lib/announce.dis | appl/grid/lib/announce.b | module/grid/announce.m | - | ported to appl/grid/lib/announce.zi; kept until cpupool.dis is unblocked |
| dis/grid/reglisten.dis | appl/grid/reglisten.b |  | - | blocked: needs Keyring->auth(fd, ai, setid) and Sh->run {script} with $user/$net |
| dis/grid/regstyxlisten.dis | appl/grid/regstyxlisten.b |  | - | blocked: needs Keyring->auth(fd, ai, setid=1) and Sh->run |
| dis/grid/remotelogon.dis | appl/grid/remotelogon.b |  | - | blocked: needs Login->login (Keyring->auth) and Sh->run |

### 11. Demo - demonstration apps - 6 rows

| Path | Limbo source | Interface | Boot | Notes |
|---|---|---|---|---|
| dis/demo/lego/firmdl.dis | appl/demo/lego/firmdl.b |  | - | restored: ZX port was reduced (packet length/start in decimal, extra zero byte, checksum differed) |
| dis/demo/lego/legolink.dis | appl/demo/lego/legolink.b |  | - | restored: ZX port lost the 250 ms poll empty message, POLLDO, and the 1500 ms re-settle |
| dis/demo/lego/rcxsend.dis | appl/demo/lego/rcxsend.b |  | - | restored with legolink (shared poll loop) |
| dis/demo/lego/timers.dis | appl/demo/lego/timers.b | module/timers.m | - | restored with legolink |
| dis/demo/whiteboard/wbsrv.dis | appl/demo/whiteboard/wbsrv.b |  | - | restored: ZX port inverted CMAP8 (0=black, 255=white) and only saved inside the 9P read loop |
| dis/demo/whiteboard/whiteboard.dis | appl/demo/whiteboard/whiteboard.b |  | - | restored client; runwb.sh now serves /dis/demo/whiteboard/whiteboard.dis |

### 12. Ebook - readers - 0 rows

| Path | Limbo source | Interface | Boot | Notes |
|---|---|---|---|---|

### 13. Math - numeric modules - 0 rows

| Path | Limbo source | Interface | Boot | Notes |
|---|---|---|---|---|

### 14. Legacy misc - installer, disk, fs, avr, lego, mpc, mpeg, palm, dbm and orphans - 32 rows

| Path | Limbo source | Interface | Boot | Notes |
|---|---|---|---|---|
| dis/disk/kfs.dis | appl/cmd/disk/kfs.b |  | - | blocked: 9P server needs file2chan/spawn/channels in ZX host API |
| dis/fs/and.dis | appl/cmd/fs/and.b |  | - |  |
| dis/fs/bundle.dis | appl/cmd/fs/bundle.b | module/bundle.m | - |  |
| dis/fs/chstat.dis | appl/cmd/fs/chstat.b |  | - |  |
| dis/fs/compose.dis | appl/cmd/fs/compose.b |  | - |  |
| dis/fs/depth.dis | appl/cmd/fs/depth.b |  | - |  |
| dis/fs/entries.dis | appl/cmd/fs/entries.b |  | - |  |
| dis/fs/eval.dis | appl/cmd/fs/eval.b |  | - |  |
| dis/fs/exec.dis | appl/cmd/fs/exec.b |  | - |  |
| dis/fs/filter.dis | appl/cmd/fs/filter.b | module/filter.m | - |  |
| dis/fs/join.dis | appl/spree/join.b |  | - |  |
| dis/fs/ls.dis | appl/cmd/fs/ls.b |  | - |  |
| dis/fs/match.dis | appl/cmd/fs/match.b |  | - |  |
| dis/fs/merge.dis | appl/cmd/fs/merge.b |  | - |  |
| dis/fs/mergewrite.dis | appl/cmd/fs/mergewrite.b |  | - |  |
| dis/fs/mode.dis | appl/cmd/fs/mode.b |  | - |  |
| dis/fs/not.dis | appl/cmd/fs/not.b |  | - |  |
| dis/fs/or.dis | appl/cmd/fs/or.b |  | - |  |
| dis/fs/path.dis | appl/cmd/fs/path.b |  | - |  |
| dis/fs/pipe.dis | appl/cmd/fs/pipe.b |  | - |  |
| dis/fs/print.dis | appl/cmd/fs/print.b | module/print.m | - |  |
| dis/fs/proto.dis | appl/cmd/fs/proto.b |  | - |  |
| dis/fs/query.dis | appl/cmd/fs/query.b |  | - |  |
| dis/fs/run.dis | appl/cmd/fs/run.b |  | - |  |
| dis/fs/select.dis | appl/cmd/fs/select.b |  | - |  |
| dis/fs/setroot.dis | appl/cmd/fs/setroot.b |  | - |  |
| dis/fs/size.dis | appl/cmd/fs/size.b |  | - |  |
| dis/fs/unbundle.dis | appl/cmd/fs/unbundle.b | module/unbundle.m | - |  |
| dis/fs/void.dis | appl/cmd/fs/void.b |  | - |  |
| dis/fs/walk.dis | appl/cmd/fs/walk.b |  | - |  |
| dis/fs/write.dis | appl/cmd/fs/write.b |  | - |  |
| dis/lego/clock.dis | appl/cmd/lego/clock.b |  | - | blocked: needs Tk/spawn in ZX |

### 15. Acme helper binaries outside dis/ - 22 rows

Tracked `.dis` helper binaries installed outside `dis/` by the acme build (mkfile targets under `appl/acme/acme/`). Same family and done rule as acme; each is removed via `git rm` in the acme family's tested commit.

| Path | Limbo source | Interface | Boot | Notes |
|---|---|---|---|---|
| acme/acid/Acid.dis | appl/acme/acme/acid/src/Acid.b |  | - |  |
| acme/acid/Acid0.dis | appl/acme/acme/acid/src/Acid0.b |  | - |  |
| acme/dis/adiff.dis | appl/acme/acme/bin/src/adiff.b |  | - |  |
| acme/dis/agrep.dis | appl/acme/acme/bin/src/agrep.b |  | - |  |
| acme/dis/awd.dis | appl/acme/acme/bin/src/awd.b |  | - |  |
| acme/dis/cd.dis | appl/acme/acme/bin/src/cd.b |  | - |  |
| acme/dis/new.dis | appl/acme/acme/bin/src/new.b |  | - |  |
| acme/dis/spout.dis | appl/acme/acme/bin/src/spout.b |  | - |  |
| acme/dis/win.dis | appl/acme/acme/bin/src/win.b |  | - |  |
| acme/dis/winm.dis | appl/acme/acme/bin/src/winm.b |  | - |  |
| acme/edit/a.dis | appl/acme/acme/edit/src/a.b |  | - |  |
| acme/edit/c.dis | appl/acme/acme/edit/src/c.b |  | - |  |
| acme/edit/d.dis | appl/acme/acme/edit/src/d.b |  | - |  |
| acme/edit/e.dis | appl/acme/acme/edit/src/e.b |  | - |  |
| acme/edit/g.dis | appl/acme/acme/edit/src/g.b |  | - |  |
| acme/edit/i.dis | appl/acme/acme/edit/src/i.b |  | - |  |
| acme/edit/p.dis | appl/acme/acme/edit/src/p.b |  | - |  |
| acme/edit/pipe.dis | appl/acme/acme/edit/src/pipe.b |  | - |  |
| acme/edit/x.dis | appl/acme/acme/edit/src/x.b |  | - |  |
| acme/mail/Mail.dis | appl/acme/acme/mail/src/Mail.b |  | - |  |
| acme/mail/Mailpop3.dis | appl/acme/acme/mail/src/Mailpop3.b |  | - |  |
| acme/mail/mkbox.dis | appl/acme/acme/mail/mkbox.b |  | - | mkfile source in appl/acme/acme/mail/, not src/ |

### 16. Native kernel configurations - open item, no `.dis` rows

The `os/*/` kernel configuration files and `os/init/*.b` still name Dis files that are gone. Point each entry at its `.zx` replacement or drop it; the hosted tests do not build these kernels.

- `/dis/cat.dis`, `/dis/echo.dis`, `/dis/ls.dis`: `os/cerf1110/cerf`, `os/cerf250/cerf`, `os/cerf405/cerf`, `os/gum/gum`, `os/ipaq1110/ipaq`, `os/manga/manga`, `os/pc/pc`, `os/pc/pc4e`, `os/pc/pcdisk`, `os/pc/pix`.
- `/dis/cp.dis`, `/dis/mkdir.dis`, `/dis/pcmcia.dis`: `os/cerf1110/cerf`, `os/cerf250/cerf`, `os/gum/gum`, `os/ipaq1110/ipaq`.
- `/dis/disk/kfscmd.dis`: `os/ipaq1110/ipaq`.
- `/dis/tiny/sh.dis` (their root `/dis/sh.dis`; `/dis/tiny/sh.zx` replaces it): `os/cerf1110/cerf`, `os/cerf250/cerf`, `os/gum/gum`, `os/ipaq1110/ipaq`.
- `/dis/lib/srv.dis`: `os/init/reminit.b`. `/dis/mux/mux.dis`: `os/init/init.b`.
