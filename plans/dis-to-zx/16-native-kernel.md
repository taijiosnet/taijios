# 16. Native kernel configurations - open item, no `.dis` rows

Owner: Native kernel configurations (unassigned)

Index: [plans/dis-to-zx.md](../dis-to-zx.md)

The `os/*/` kernel configuration files and `os/init/*.b` still name Dis files that are gone. Point each entry at its `.zx` replacement or drop it; the hosted tests do not build these kernels.

- `/dis/cat.dis`, `/dis/echo.dis`, `/dis/ls.dis`: `os/cerf1110/cerf`, `os/cerf250/cerf`, `os/cerf405/cerf`, `os/gum/gum`, `os/ipaq1110/ipaq`, `os/manga/manga`, `os/pc/pc`, `os/pc/pc4e`, `os/pc/pcdisk`, `os/pc/pix`.
- `/dis/cp.dis`, `/dis/mkdir.dis`, `/dis/pcmcia.dis`: `os/cerf1110/cerf`, `os/cerf250/cerf`, `os/gum/gum`, `os/ipaq1110/ipaq`.
- `/dis/disk/kfscmd.dis`: `os/ipaq1110/ipaq`.
- `/dis/tiny/sh.dis` (their root `/dis/sh.dis`; `/dis/tiny/sh.zx` replaces it): `os/cerf1110/cerf`, `os/cerf250/cerf`, `os/gum/gum`, `os/ipaq1110/ipaq`.
- `/dis/lib/srv.dis`: `os/init/reminit.b`. `/dis/mux/mux.dis`: `os/init/init.b`.
