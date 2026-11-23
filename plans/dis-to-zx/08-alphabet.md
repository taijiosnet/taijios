# 8. Alphabet - gridded documents family - 83 rows

Owner: Alphabet (`cmd-taijios-zx-alphabet-port`)

Index: [plans/dis-to-zx.md](../dis-to-zx.md)

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
| dis/alphabet/endpoints.dis | appl/alphabet/auxi/endpoints.b | module/alphabet/endpoints.m | - | zx-twin: appl/alphabet/grid/endpoints.zi; its new also needs /dis/listen.zx |
| dis/alphabet/endpointsrv.dis | appl/alphabet/auxi/endpointsrv.b |  | - | zx-twin /dis/endpointsrv.zx: appl/alphabet/endpointsrv.zi, `mk install-zx`; tests/alphabet/grid_test.sh |
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
| dis/alphabet/grid/farm.dis | appl/alphabet/grid/farm.b |  | - | blocked: needs a Ziran host call that starts a procedure of the same bundle while the caller keeps running, plus the fd/handle passing a copy needs (it is also the only consumer of records) |
| dis/alphabet/grid/line2rec.dis | appl/alphabet/grid/line2rec.b |  | - | zx-twin: appl/alphabet/grid/line2rec.zi; tests/alphabet/grid_test.sh |
| dis/alphabet/grid/local.dis | appl/alphabet/grid/local.b |  | - | zx-twin: appl/alphabet/grid/local.zi; tests/alphabet/grid_test.sh |
| dis/alphabet/grid/remote.dis | appl/alphabet/grid/remote.b |  | - | blocked: needs a Ziran host call that starts a procedure of the same bundle while the caller keeps running, plus the fd/handle passing a copy needs |
| dis/alphabet/grid/rexec.dis | appl/alphabet/grid/rexec.b |  | - | blocked: needs a Ziran host call that starts a procedure of the same bundle while the caller keeps running, plus the fd/handle passing a copy needs |
| dis/alphabet/gridtypes.dis | appl/alphabet/typesets/gridtypes.b | module/alphabet/gridtypes.m | - | zx-twin: appl/alphabet/grid/gridtypes.zi, serves /grid with local and line2rec |
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
| dis/alphabet/rexecsrv.dis | appl/alphabet/auxi/rexecsrv.b |  | - | blocked: needs a Ziran host call that starts a procedure of the same bundle while the caller keeps running, plus the fd/handle passing a copy needs |

