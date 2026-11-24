# Alphabet in Ziran (open work)

Owner: `claude-taijios-zx-alphabet-port`. Rows: section 8 of `plans/dis-to-zx.md` and `dis/sh/alphabet.dis`.

Done and retired: the core (`alphabet`, `alphabet.shmod`, `eval`, `extvalues`, `proxy`, `reports`), the root typeset `/` (`appl/alphabet/main/` except blocked `/auth`), the `abc` typeset (`appl/alphabet/abc/`), all 28 `fs` modules (`appl/alphabet/fs/` plus `fs`, `fstypes`, `fsfilter`), and the working part of the `grid` typeset (`endpoints`, `endpointsrv`, `grid`, `gridtypes`, `local`, `line2rec`) — 77 `dis/alphabet/**` binaries and 80 `appl/alphabet/**` `.b` sources removed once `/dis/sh.zx` `load alphabet` (commit `8bb9cf56`) and `/dis/alphabet.zx` (`cd appl/alphabet && mk install-zx`) verified parity. Tests: `tests/alphabet/alphabet_test.zi` (guest, 229 cases against recorded Dis results), `tests/alphabet/shcmd_test.zi` (24 cases) and `tests/alphabet/grid_test.sh`.

## Remaining

1. `grid` typeset, the rest (4 `.dis` rows): `remote`, `rexec`, `farm` and `rexecsrv` need a Ziran host call that starts a procedure of the same bundle while the caller keeps running, plus the fd/handle passing a copy needs.
2. `/auth` (1 `.dis` row: `dis/alphabet/main/auth.dis`): needs a ZX Inferno Auth client (dis/lib lane); today `appl/alphabet/main/auth.zi` reads the key and reports that the protocol is missing.
3. `dis/alphabet/mktypeset.dis` (1 `.dis` row): orphan binary with no Limbo source on disk; port or drop with the owner's word.
4. `dis/sh/alphabet.dis` (owned by the shell lane in `plans/dis-to-zx/03-shell-commands.md`) and `module/alphabet*.m` (still included by the 5 remaining blocked `.b` files) stay until the remaining blocked rows and shell lane retire them.
5. Ziran bundler: two modules with a file-private record of the same name break `ziran bundle` ("record member has no lowered field identity"); reported. Keep private record names unique until it is fixed.
6. Merge `appl/alphabet/shcmd.zi` with the shell port's `appl/cmd/sh/shell_parse.zi` (same grammar).

## Decisions

- Values are pull streams in one process (a ZX guest has no threads); producers are rows with read/run/handle/dup/free procedures.
- A typeset is registered Ziran code (`alpha_types.RegisterTypeset`, `alpha_eval.RegisterModule`) in place of Dis `load`; error texts for missing modules keep the Dis paths.
- Dis bugs not kept: readall of a /read, seq -a/-o and mount hung; seq printed debug lines; mount -a/-b were ignored. par runs its statuses one after another.
- `/fs/match -r` reuses the ZX shell's regexp module (`appl/cmd/sh/shell_regexp.zi`, a port of `appl/lib/regex.b`) through the bundle's module path; its 12 cases match the Dis original, failures and their two error texts included.
- Recording harness: per-case emulator runs under `build/tests/alphabet/rec*` (scratch, not committed).
