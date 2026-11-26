# 3. Shell and commands - sh module, sh builtins, tiny, top-level commands - 108 rows

Owner: Commands A–L / M–Z (`glm-taijios-dis-commands-a-l`, `cmd-taijios-dis-commands-m-z`); shell (`cmd-taijios-zx-shell-port`)

Index: [plans/dis-to-zx.md](../dis-to-zx.md)

| Path | Limbo source | Interface | Boot | Notes |
|---|---|---|---|---|
| zx/sh.dis | appl/cmd/sh/sh.b | module/sh.m | P1 | zx-twin /zx/sh.zx (appl/cmd/sh/sh.zi, `mk install-zx`), the shell of a Dis-free guest; tests/sh: all cases match sh.dis; open: the tk, mload, mk and alphabet builtin modules, and the step budget (a long CPU-bound script ends a ZX program). A Dis guest keeps sh.dis for `sh`. Limbo loaders of Sh left: 9srvfs 9win auxi/rstyxd dial ed fs/{eval,exec,pipe,query,run} iostats itest listen m4 mk mount p rawdbfs rioimport runas styxlisten styxmon time wmimport xargs (appl/cmd), alphabet/{alphabet,eval,auxi/endpoints,auxi/rexecsrv,fs/exec,fs/pipe,fs/query,fs/run,grid/farm,grid/rexec,main/filter,main/parse,main/pretty,main/rewrite,main/unparse}, grid/{cpupool,reglisten,regstyxlisten,remotelogon}, wm/{ftree/ftree,remotelogon,sh,toolbar,vt,wm}, sh/mload |
| zx/9win.dis | appl/cmd/9win.b |  | - |  |
| zx/B.dis | appl/cmd/B.b |  | - |  |
| zx/acme.dis | appl/acme/acme.b |  | - |  |
| zx/ar.dis | appl/cmd/ar.b |  | - |  |
| zx/asm.dis | appl/cmd/asm/asm.b|appl/cmd/limbo/asm.b |  | - |  |
| zx/auhdr.dis | appl/cmd/auplay.b (copy rule) |  | - |  |
| zx/auplay.dis | appl/cmd/auplay.b |  | - |  |
| zx/bind.dis | appl/cmd/bind.b |  | - |  |
| zx/bytes.dis | appl/cmd/bytes.b |  | - |  |
| zx/cal.dis | appl/cmd/cal.b |  | - |  |
| zx/calc.dis | appl/cmd/calc.b |  | - |  |
| zx/cd.dis | appl/cmd/cd.b |  | - |  |
| zx/cddb.dis | appl/cmd/cddb.b |  | - |  |
| zx/charon.dis | appl/charon/charon.b |  | - |  |
| zx/cook.dis | appl/cmd/cook.b |  | - |  |
| zx/cprof.dis | appl/cmd/cprof.b |  | - |  |
| zx/cpu.dis | appl/cmd/cpu.b |  | - |  |
| zx/crypt.dis | appl/cmd/crypt.b | module/crypt.m | - |  |
| zx/dd.dis | appl/cmd/dd.b |  | - |  |
| zx/dial.dis | appl/cmd/dial.b | module/dial.m | - |  |
| zx/diff.dis | appl/cmd/diff.b |  | - |  |
| zx/disdep.dis | appl/cmd/disdep.b |  | - |  |
| zx/disdump.dis | appl/cmd/disdump.b |  | - |  |
| zx/du.dis | appl/cmd/du.b |  | - |  |
| zx/ed.dis | appl/cmd/ed.b |  | - |  |
| zx/emuinit.dis | appl/cmd/emuinit.b |  | - |  |
| zx/fc.dis | appl/cmd/fc.b |  | - |  |
| zx/fcp.dis | appl/cmd/fcp.b |  | - |  |
| zx/fmt.dis | appl/cmd/fmt.b |  | - |  |
| zx/fortune.dis | appl/cmd/fortune.b |  | - |  |
| zx/ftest.dis | appl/cmd/ftest.b |  | - |  |
| zx/getauthinfo.dis | appl/cmd/getauthinfo.b |  | - |  |
| zx/gettar.dis | appl/cmd/gettar.b |  | - |  |
| zx/grep.dis | appl/cmd/grep.b |  | - |  |
| zx/gunzip.dis | appl/cmd/gunzip.b |  | - |  |
| zx/gzip.dis | appl/cmd/gzip.b |  | - |  |
| zx/idea.dis | appl/cmd/idea.b |  | - |  |
| zx/import.dis | appl/cmd/import.b |  | - |  |
| zx/iostats.dis | appl/cmd/iostats.b |  | - |  |
| zx/itest.dis | appl/cmd/itest.b |  | - |  |
| zx/itreplay.dis | appl/cmd/itreplay.b |  | - |  |
| zx/kill.dis | appl/cmd/kill.b |  | - |  |
| zx/limbo.dis | appl/cmd/limbo/limbo.b |  | - |  |
| zx/logfile.dis | appl/cmd/logfile.b |  | - |  |
| zx/look.dis | appl/cmd/look.b |  | - |  |
| zx/lstar.dis | appl/cmd/lstar.b |  | - |  |
| zx/m4.dis | appl/cmd/m4.b |  | - |  |
| zx/man2html.dis | appl/cmd/man2html.b |  | - |  |
| zx/man2txt.dis | appl/cmd/man2txt.b |  | - |  |
| zx/mash.dis | appl/cmd/mash/mash.b |  | - | zx-twin /zx/mash.zx (appl/cmd/mash/mash.zi and its eight modules, `mk install-zx`): mash's own grammar through the yacc tables of mashparse.b, the builtins modules compiled in (env, eval, exit, load, prompt, quote, run, status, time, whatis, and make with depends, match and rules), the make builder, and threads as guest processes. <{} and >{} generators: each value's items are a range of their own in the parse's pool (mash_parse.zi PoolWiden), so the generator's word takes its place among the operands and the block's own words stay in the block; the child mash.zx that runs a block (`-i`) registers the builtins and holds the pipe on its output (<{}) or input (>{}), served from /tmp/pipes. tests/mash: 34 of 35 cases match /zx/mash.dis (pipe names compared as $pipe), 1 known gap (the line number the parser reports after a failed command). Still open here: the `run` builtin is a stub (mash.dis prints a script's output, mash.zx prints nothing); a >{} consumer's own output is lost when the shell exits at once, since it is a child process where mash.dis had a thread that ran first; zx/lib/mash/tk.dis and zx/lib/mash/history.dis stay blocked (see Blockers below). Limbo loaders of Mashlib/Mashparse stay while zx/mash.dis exists. |
| zx/mc.dis | appl/cmd/mc.b |  | - |  |
| zx/mdb.dis | appl/cmd/mdb.b |  | - |  |
| zx/metamorph.dis | appl/cmd/metamorph.b |  | - |  |
| zx/mk.dis | appl/cmd/mk/mk.b |  | - |  |
| zx/mount.dis | appl/cmd/mount.b |  | - |  |
| zx/mouse.dis | appl/cmd/mouse.b |  | - |  |
| zx/mprof.dis | appl/cmd/mprof.b |  | - |  |
| zx/netkey.dis | appl/cmd/netkey.b |  | - |  |
| zx/ns.dis | appl/cmd/ns.b |  | - |  |
| zx/nsbuild.dis | appl/cmd/nsbuild.b |  | - |  |
| zx/os.dis | appl/cmd/os.b |  | - |  |
| zx/plumb.dis | appl/cmd/plumb.b |  | - |  |
| zx/prof.dis | appl/cmd/prof.b |  | - |  |
| zx/raw2iaf.dis | appl/cmd/raw2iaf.b |  | - |  |
| zx/rcmd.dis | appl/cmd/rcmd.b |  | - |  |
| zx/rdp.dis | appl/cmd/rdp.b |  | - |  |
| zx/rioimport.dis | appl/cmd/rioimport.b |  | - |  |
| zx/sed.dis | appl/cmd/sed.b |  | - |  |
| zx/sendmail.dis | appl/cmd/sendmail.b |  | - |  |
| zx/sh/alphabet.dis | appl/alphabet/alphabet.b | module/alphabet.m | - |  |
| zx/sh/arg.dis | appl/cmd/sh/arg.b | module/arg.m | - | ported into /zx/sh.zx (appl/cmd/sh/shell_small.zi); loaded only by sh.dis |
| zx/sh/csv.dis | appl/cmd/sh/csv.b | module/csv.m | - | ported into /zx/sh.zx (appl/cmd/sh/shell_csv.zi); loaded only by sh.dis |
| zx/sh/echo.dis | appl/cmd/sh/echo.b |  | - | ported into /zx/sh.zx (appl/cmd/sh/shell_small.zi); loaded only by sh.dis |
| zx/sh/expr.dis | appl/cmd/sh/expr.b |  | - | ported into /zx/sh.zx (appl/cmd/sh/shell_expr.zi); loaded only by sh.dis |
| zx/sh/file2chan.dis | appl/cmd/sh/file2chan.b |  | - | ported into /zx/sh.zx (appl/cmd/sh/shell_file2chan.zi); loaded only by sh.dis |
| zx/sh/mk.dis | appl/cmd/mk/mk.b |  | - | open: needs a Ziran mk (appl/cmd/mk/mk.b), the shell builtin form included |
| zx/sh/mload.dis | appl/cmd/sh/mload.b |  | - | open: loads Dis modules as builtin namespaces; ZX has no loading of modules while running |
| zx/sh/mpexpr.dis | appl/cmd/sh/mpexpr.b |  | - | ported into /zx/sh.zx (appl/cmd/sh/shell_mpexpr.zi, over taijios_keyring Big); loaded only by sh.dis |
| zx/sh/regex.dis | appl/cmd/sh/regex.b | module/regex.m | - | ported into /zx/sh.zx (appl/cmd/sh/shell_regex.zi); loaded only by sh.dis |
| zx/sh/sexprs.dis | appl/cmd/sh/sexprs.b | module/sexprs.m | - | ported into /zx/sh.zx (appl/cmd/sh/shell_sexprs.zi); loaded only by sh.dis |
| zx/sh/sh.dis | appl/cmd/sh/sh.b | module/sh.m | - |  |
| zx/sh/std.dis | appl/cmd/sh/std.b |  | - | ported into /zx/sh.zx (appl/cmd/sh/shell_std.zi); loaded only by sh.dis |
| zx/sh/string.dis | appl/cmd/sh/string.b | module/string.m | - | ported into /zx/sh.zx (appl/cmd/sh/shell_string.zi); loaded only by sh.dis |
| zx/sh/test.dis | appl/cmd/sh/test.b |  | - | ported into /zx/sh.zx (appl/cmd/sh/shell_small.zi); loaded only by sh.dis |
| zx/sh/tk.dis | appl/cmd/sh/tk.b | module/tk.m | - | blocked: module/tk.m is a Limbo interface with no ZX consumer, nothing lets a Ziran program call Tk->cmd on a toplevel (the ZX Tk lives inside the Tcl interpreter); no port and no second tk binding for sh.zx |
| zx/src.dis | appl/cmd/src.b |  | - |  |
| zx/stack.dis | appl/cmd/stack.b |  | - |  |
| zx/stackv.dis | appl/cmd/stackv.b |  | - |  |
| zx/stream.dis | appl/cmd/stream.b |  | - |  |
| zx/styxchat.dis | appl/cmd/styxchat.b |  | - |  |
| zx/styxlisten.dis | appl/cmd/styxlisten.b |  | - |  |
| zx/styxmon.dis | appl/cmd/styxmon.b |  | - |  |
| zx/tail.dis | appl/cmd/tail.b |  | - |  |
| zx/tcs.dis | appl/cmd/tcs.b |  | - |  |
| zx/telnet.dis | appl/cmd/telnet.b |  | - |  |
| zx/tkcmd.dis | appl/cmd/tkcmd.b |  | - |  |
| zx/touchcal.dis | appl/cmd/touchcal.b |  | - |  |
| zx/units.dis | appl/cmd/units.b |  | - |  |
| zx/vacget.dis | appl/cmd/vacget.b |  | - |  |
| zx/vacput.dis | appl/cmd/vacput.b |  | - |  |
| zx/wav2iaf.dis | appl/cmd/wav2iaf.b |  | - |  |
| zx/webgrab.dis | appl/cmd/webgrab.b |  | - |  |
| zx/wish.dis | appl/cmd/wish.b |  | - |  |
| zx/wmexport.dis | appl/cmd/wmexport.b |  | - |  |
| zx/wmimport.dis | appl/cmd/wmimport.b |  | - |  |
| zx/xd.dis | appl/cmd/xd.b |  | - |  |
| zx/yacc.dis | appl/cmd/yacc.b |  | - |  |


## Blockers

- `zx/sh/tk.dis` (row above): `module/tk.m` is a Limbo interface with no ZX consumer. Decision: no port; sh.zx gets no second tk binding.
- `zx/lib/mash/tk.dis` (row in [02-libraries.md](02-libraries.md)): the same `module/tk.m` interface behind mash's tk builtin. Decision: no port.
- `zx/lib/mash/history.dis` (row in [02-libraries.md](02-libraries.md)): the Limbo module serves a file that is fed while the parser runs; ZX has no threads for a served file beside the parse. Decision: no port.
