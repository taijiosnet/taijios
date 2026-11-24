# 8. Alphabet - gridded documents family - 6 rows

Owner: Alphabet (`cmd-taijios-zx-alphabet-port`)

Index: [plans/dis-to-zx.md](../dis-to-zx.md)

| Path | Limbo source | Interface | Boot | Notes |
|---|---|---|---|---|
| dis/alphabet/grid/farm.dis | appl/alphabet/grid/farm.b |  | - | blocked: needs a Ziran host call that starts a procedure of the same bundle while the caller keeps running, plus the fd/handle passing a copy needs (it is also the only consumer of records) |
| dis/alphabet/grid/remote.dis | appl/alphabet/grid/remote.b |  | - | blocked: needs a Ziran host call that starts a procedure of the same bundle while the caller keeps running, plus the fd/handle passing a copy needs |
| dis/alphabet/grid/rexec.dis | appl/alphabet/grid/rexec.b |  | - | blocked: needs a Ziran host call that starts a procedure of the same bundle while the caller keeps running, plus the fd/handle passing a copy needs |
| dis/alphabet/main/auth.dis | appl/alphabet/main/auth.b |  | - | blocked: `/auth` needs a ZX Inferno Auth client (`appl/alphabet/main/auth.zi` reads the key file and reports the missing protocol) |
| dis/alphabet/mktypeset.dis | unknown |  | - | blocked/orphan: Limbo code generator with no source on disk; pending owner decision to port or drop |
| dis/alphabet/rexecsrv.dis | appl/alphabet/auxi/rexecsrv.b |  | - | blocked: needs a Ziran host call that starts a procedure of the same bundle while the caller keeps running, plus the fd/handle passing a copy needs |
