# 14. Legacy misc - installer, disk, fs, avr, lego, mpc, mpeg, palm, dbm and orphans - 2 rows

Owner: Legacy misc (`agy-taijios-dis-legacy-math`)

Index: [plans/dis-to-zx.md](../dis-to-zx.md)

| Path | Limbo source | Interface | Boot | Notes |
|---|---|---|---|---|
| zx/disk/kfs.dis | appl/cmd/disk/kfs.b |  | - | blocked: 3,844-line 9P file server. Ziran has no Styx codec (module/styx.m has no `.zi`; Tmsg/Rmsg pack and unpack live in libinterp/styx.c). `taijios_file2chan.zi` serves one file: Step handles version, attach, one-name walk, open, read, write, clunk, stat and a no-op wstat, and refuses create, remove, flush and multi-name walk, so it cannot serve a disk tree. kfs also starts a console server and a sync flow and calls pctl/fildes; there is no in-bundle spawn and taijios_io has no pread/pwrite |
| zx/lego/clock.dis | appl/cmd/lego/clock.b |  | - | blocked: Tk. At the pinned tk package (4e79275) Canvas has Rectangle, Label, Line, Oval and Image items only; the face's twelve tick arcs and its hour and minute indicators use `create arc -start -extent` and `itemconfigure -start`. The widget-level binds are bare `<ButtonPress>` and `<ButtonRelease>` (only `<ButtonPress-1>` is recognized), and the app wires events through `send`/`namechan`, which the launcher lacks. The /chan/clockface reader fits PollRead |

