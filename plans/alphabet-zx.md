# Alphabet in Ziran (open work)

Owner: `claude-taijios-zx-alphabet-port`. Rows: section 8 of `plans/dis-to-zx.md` and `dis/sh/alphabet.dis`.

Done and pushed: the core, the root typeset `/` (`appl/alphabet/main/`) and the abc typeset (`appl/alphabet/abc/`), all served by `/dis/alphabet.zx` (`cd appl/alphabet && mk install-zx`). Test: `tests/alphabet/alphabet_test.zi` (guest, against recorded Dis results) and `tests/alphabet/shcmd_test.zi`.

## Remaining

1. fs typeset (`appl/alphabet/fs/*.b`, `typesets/fs*.b`, `auxi/fsfilter.b`): 28 modules. Types: fs (x, tree stream), entries (t), gate (p), selector (m), plus r d c f s. Port each module as a pull state machine on the value arena: an fs value gives an item (entry, data block or end of directory) and takes the consumer's reply (Next, Down, Skip, Quit) for it. exec, run, pipe and query run shell commands: they wait for `/dis/sh.zx`.
2. grid typeset (`appl/alphabet/grid/*.b`, `typesets/grid*.b`, `auxi/endpoints.b`, `endpointsrv.b`, `rexecsrv.b`): remote, local, rexec, farm, line2rec. rexec and farm run shell commands.
3. The ZX shell's `load alphabet` builtin (owned by the shell port) runs `alpha_builtins.zi`. Then, in one commit: delete every `dis/alphabet/**` row, `dis/sh/alphabet.dis`, `appl/alphabet/**/*.b`, `module/alphabet*.m`, with the plan rows.
4. `/auth` needs a ZX Inferno Auth client (dis/lib lane): today it reads the key and reports that the protocol is missing.
5. `dis/alphabet/mktypeset.dis` has no source; it generated Limbo typesets. Port or drop with the owner's word.
6. Merge `appl/alphabet/shcmd.zi` with the shell port's `appl/cmd/sh/shell_parse.zi` (same grammar).

## Decisions

- Values are pull streams in one process (a ZX guest has no threads); producers are rows with read/run/handle/dup/free procedures.
- A typeset is registered Ziran code (`alpha_types.RegisterTypeset`, `alpha_eval.RegisterModule`) in place of Dis `load`; error texts for missing modules keep the Dis paths.
- Dis bugs not kept: readall of a /read, seq -a/-o and mount hung; seq printed debug lines; mount -a/-b were ignored. par runs its statuses one after another.
- Recording harness: per-case emulator runs under `build/tests/alphabet/rec*` (scratch, not committed).
