# 6. Acme - editor family - 24 rows

Owner: Acme (acme lane)

Index: [plans/dis-to-zx.md](../dis-to-zx.md)

Note: `zx/acme/guiwm.dis` was removed as a stale orphan (no `.b` source on disk, absent from `appl/acme/mkfile` `TARG`, and `gui.m`'s `WMPATH` constant is unreferenced).

Blocker for the 24-module (16,424-line) editor core below: `appl/acme/gui.b`, `graph.b` and `frame.b` are direct `Draw`/`Wmclient` clients (not Tk widgets) requiring Ziran `Draw->Font` metrics (`Font.width`), `Image.text`/`Image.draw`, `Wmclient` `reshape`/`wmctl("ptr ...")`/`wmctl("cursor ...")`, plus a concurrent multi-fid 9P `/mnt/acme` server (`fsys.b`/`xfid.b`/`styxaux.b`) running alongside the UI loop, `plumbmsg` (`zx/lib/plumbmsg.dis`), and process-group control (`#p/<pid>/ctl`).

| Path | Limbo source | Interface | Boot | Notes |
|---|---|---|---|---|
| zx/acme/acme.dis | appl/acme/acme.b |  | - | blocked: Draw font metrics + Wmclient cursor/ptr + concurrent 9P/UI + plumbmsg |
| zx/acme/buff.dis | appl/acme/buff.b |  | - | blocked with acme editor core |
| zx/acme/col.dis | appl/acme/col.b |  | - | blocked with acme editor core |
| zx/acme/dat.dis | appl/acme/dat.b |  | - | blocked with acme editor core |
| zx/acme/disk.dis | appl/acme/disk.b |  | - | blocked with acme editor core |
| zx/acme/ecmd.dis | appl/acme/ecmd.b |  | - | blocked with acme editor core |
| zx/acme/edit.dis | appl/acme/edit.b |  | - | blocked with acme editor core |
| zx/acme/elog.dis | appl/acme/elog.b |  | - | blocked with acme editor core |
| zx/acme/exec.dis | appl/acme/exec.b |  | - | blocked with acme editor core |
| zx/acme/file.dis | appl/acme/file.b |  | - | blocked with acme editor core |
| zx/acme/frame.dis | appl/acme/frame.b |  | - | blocked: Draw font metrics (`Font.width`, `Image.text`) |
| zx/acme/fsys.dis | appl/acme/fsys.b |  | - | blocked: concurrent multi-fid 9P `/mnt/acme` server alongside UI |
| zx/acme/graph.dis | appl/acme/graph.b |  | - | blocked: Draw font metrics + `Image.draw`/`Image.text` |
| zx/acme/gui.dis | appl/acme/gui.b |  | - | blocked: Wmclient `reshape`/`onscreen`/`wmctl` cursor & ptr warping |
| zx/acme/look.dis | appl/acme/look.b |  | - | blocked: `plumbmsg` (`zx/lib/plumbmsg.dis`) + acme editor core |
| zx/acme/regx.dis | appl/acme/regx.b |  | - | blocked with acme editor core |
| zx/acme/row.dis | appl/acme/row.b |  | - | blocked with acme editor core |
| zx/acme/scrl.dis | appl/acme/scrl.b |  | - | blocked with acme editor core |
| zx/acme/styxaux.dis | appl/acme/styxaux.b |  | - | blocked with acme editor core |
| zx/acme/text.dis | appl/acme/text.b |  | - | blocked with acme editor core |
| zx/acme/time.dis | appl/acme/time.b |  | - | blocked with acme editor core |
| zx/acme/util.dis | appl/acme/util.b |  | - | blocked with acme editor core |
| zx/acme/wind.dis | appl/acme/wind.b |  | - | blocked with acme editor core |
| zx/acme/xfid.dis | appl/acme/xfid.b |  | - | blocked: concurrent multi-fid 9P `/mnt/acme` server |

