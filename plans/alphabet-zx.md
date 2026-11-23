# Alphabet in Ziran (open work)

Owner: `claude-taijios-zx-alphabet-port`. Rows: section 8 of `plans/dis-to-zx.md` and `dis/sh/alphabet.dis`.

Done and pushed: the core, the root typeset `/` (`appl/alphabet/main/`), the abc typeset (`appl/alphabet/abc/`), all 28 fs modules (`appl/alphabet/fs/`) and the working part of the grid typeset (`appl/alphabet/grid/`: endpoints, local, line2rec, gridtypes), all served by `/dis/alphabet.zx` (`cd appl/alphabet && mk install-zx`). Tests: `tests/alphabet/alphabet_test.zi` (guest, 226 cases against recorded Dis results), `tests/alphabet/shcmd_test.zi` and `tests/alphabet/grid_test.sh`.

## Remaining

1. The ZX shell's `load alphabet` builtin (owned by the shell port) runs `alpha_builtins.zi`. Then, in one commit: delete every `dis/alphabet/**` row, `dis/sh/alphabet.dis`, `appl/alphabet/**/*.b`, `module/alphabet*.m`, with the plan rows.
2. grid typeset, the rest: `remote`, `rexec`, `farm` and `rexecsrv` need a Ziran host call that starts a procedure of the same bundle while the caller keeps running, plus the fd/handle passing a copy needs.
3. `/auth` needs a ZX Inferno Auth client (dis/lib lane); today it reads the key and reports that the protocol is missing.
4. `dis/alphabet/mktypeset.dis` has no source; port or drop with the owner's word.
5. Ziran bundler: two modules with a file-private record of the same name break `ziran bundle` ("record member has no lowered field identity"); reported. Keep private record names unique until it is fixed.
6. Merge `appl/alphabet/shcmd.zi` with the shell port's `appl/cmd/sh/shell_parse.zi` (same grammar).

## Decisions

- Values are pull streams in one process (a ZX guest has no threads); producers are rows with read/run/handle/dup/free procedures.
- A typeset is registered Ziran code (`alpha_types.RegisterTypeset`, `alpha_eval.RegisterModule`) in place of Dis `load`; error texts for missing modules keep the Dis paths.
- Dis bugs not kept: readall of a /read, seq -a/-o and mount hung; seq printed debug lines; mount -a/-b were ignored. par runs its statuses one after another.
- `/fs/match -r` reuses the ZX shell's regexp module (`appl/cmd/sh/shell_regexp.zi`, a port of `appl/lib/regex.b`) through the bundle's module path; its 12 cases match the Dis original, failures and their two error texts included.
- Recording harness: per-case emulator runs under `build/tests/alphabet/rec*` (scratch, not committed).
