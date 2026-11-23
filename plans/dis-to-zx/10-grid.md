# 10. Grid - computing grid family - 5 rows

Owner: Grid (`agy-taijios-dis-app-families`)

Index: [plans/dis-to-zx.md](../dis-to-zx.md)

| Path | Limbo source | Interface | Boot | Notes |
|---|---|---|---|---|
| dis/grid/cpupool.dis | appl/grid/cpupool.b |  | - | blocked: multi-goroutine shared-state proxy/rcmd/file2chan + sh->run in ZX host API |
| dis/grid/lib/announce.dis | appl/grid/lib/announce.b | module/grid/announce.m | - | ported to appl/grid/lib/announce.zi; kept until cpupool.dis is unblocked |
| dis/grid/reglisten.dis | appl/grid/reglisten.b |  | - | blocked: needs Keyring->auth(fd, ai, setid) and Sh->run {script} with $user/$net |
| dis/grid/regstyxlisten.dis | appl/grid/regstyxlisten.b |  | - | blocked: needs Keyring->auth(fd, ai, setid=1) and Sh->run |
| dis/grid/remotelogon.dis | appl/grid/remotelogon.b |  | - | blocked: needs Login->login (Keyring->auth) and Sh->run |

