# 3. Shell and commands - sh module, sh builtins, tiny, top-level commands - 111 rows

Owner: Commands A–L / M–Z (`glm-taijios-dis-commands-a-l`, `cmd-taijios-dis-commands-m-z`); shell (`cmd-taijios-zx-shell-port`)

Index: [plans/dis-to-zx.md](../dis-to-zx.md)

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
| dis/mash.dis | appl/cmd/mash/mash.b |  | - | zx-twin /dis/mash.zx (appl/cmd/mash/mash.zi and its eight modules, `mk install-zx`): mash's own grammar through the yacc tables of mashparse.b, the builtins modules compiled in (env, eval, exit, load, prompt, quote, run, status, time, whatis, and make with depends, match and rules), the make builder, and threads as guest processes. tests/mash: 32 of 33 cases match /dis/mash.dis, 1 known gap (the line number the parser reports after a failed command). Still open here: dis/lib/mash/tk.dis needs a Ziran Tk that answers Tk->cmd on a toplevel, which nothing provides today (module/tk.m has no ZX consumer and the ZX Tk lives inside a Tcl interpreter, not behind a callable binding); dis/lib/mash/history.dis needs a served file fed while the parser runs, which ZX has no threads for; the <{} and >{} pipes are served but the words of the block still reach the generator's argument list, so a command taking one as a non-final operand misreads it (the parse's item pool needs per-nested-parse scoping). Limbo loaders of Mashlib/Mashparse stay while dis/mash.dis exists. |
| dis/mc.dis | appl/cmd/mc.b |  | - |  |
| dis/mdb.dis | appl/cmd/mdb.b |  | - |  |
| dis/metamorph.dis | appl/cmd/metamorph.b |  | - |  |
| dis/mk.dis | appl/cmd/mk/mk.b |  | - |  |
| dis/mount.dis | appl/cmd/mount.b |  | - |  |
| dis/mouse.dis | appl/cmd/mouse.b |  | - |  |
| dis/mprof.dis | appl/cmd/mprof.b |  | - |  |
| dis/netkey.dis | appl/cmd/netkey.b |  | - |  |
| dis/ns.dis | appl/cmd/ns.b |  | - |  |
| dis/nsbuild.dis | appl/cmd/nsbuild.b |  | - |  |
| dis/os.dis | appl/cmd/os.b |  | - |  |
| dis/plumb.dis | appl/cmd/plumb.b |  | - |  |
| dis/prof.dis | appl/cmd/prof.b |  | - |  |
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
| dis/tkcmd.dis | appl/cmd/tkcmd.b |  | - |  |
| dis/touchcal.dis | appl/cmd/touchcal.b |  | - |  |
| dis/units.dis | appl/cmd/units.b |  | - |  |
| dis/vacget.dis | appl/cmd/vacget.b |  | - |  |
| dis/vacput.dis | appl/cmd/vacput.b |  | - |  |
| dis/wav2iaf.dis | appl/cmd/wav2iaf.b |  | - |  |
| dis/webgrab.dis | appl/cmd/webgrab.b |  | - |  |
| dis/wish.dis | appl/cmd/wish.b |  | - |  |
| dis/wmexport.dis | appl/cmd/wmexport.b |  | - |  |
| dis/wmimport.dis | appl/cmd/wmimport.b |  | - |  |
| dis/xd.dis | appl/cmd/xd.b |  | - |  |
| dis/yacc.dis | appl/cmd/yacc.b |  | - |  |

