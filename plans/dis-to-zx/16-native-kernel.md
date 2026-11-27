# 16. Native kernel configurations - open item, no `.dis` rows

Owner: Native kernel configurations (unassigned)

Index: [plans/dis-to-zx.md](../dis-to-zx.md)

The `os/*/` kernel configuration files and `os/init/*.b` still name Dis files that are gone. Point each entry at its `.zx` replacement or drop it; the hosted tests do not build these kernels.

- `/zx/cat.dis`, `/zx/echo.dis`, `/zx/ls.dis`, `/zx/cd.dis`, `/zx/bind.dis`: `os/cerf1110/cerf`, `os/cerf250/cerf`, `os/cerf405/cerf`, `os/gum/gum`, `os/ipaq1110/ipaq`, `os/manga/manga`, `os/pc/pc`, `os/pc/pc4e`, `os/pc/pcdisk`, `os/pc/pix`.
- `/zx/cp.dis`, `/zx/mkdir.dis`, `/zx/pcmcia.dis`: `os/cerf1110/cerf`, `os/cerf250/cerf`, `os/gum/gum`, `os/ipaq1110/ipaq`.
- `/zx/dd.dis`: `os/cerf405/cerf`, `os/manga/manga`.
- `/zx/xd.dis`: `os/cerf1110/cerf`, `os/cerf250/cerf`, `os/cerf405/cerf`, `os/gum/gum`, `os/ipaq1110/ipaq`, `os/manga/manga`.
- `/zx/disk/kfscmd.dis`: `os/ipaq1110/ipaq`.
- `/zx/tiny/sh.dis` (their root `/zx/sh.dis`; `/zx/tiny/sh.zx` replaces it): `os/cerf1110/cerf`, `os/cerf250/cerf`, `os/gum/gum`, `os/ipaq1110/ipaq`.
- `/zx/lib/srv.dis`: `os/init/reminit.b`. `/zx/mux/mux.dis`: `os/init/init.b`.
