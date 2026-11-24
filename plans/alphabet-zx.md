# Alphabet in Ziran (open work)

Owner: `claude-taijios-zx-alphabet-port`. Open rows: [plans/dis-to-zx/08-alphabet.md](dis-to-zx/08-alphabet.md) (6 rows) and `dis/sh/alphabet.dis` (shell lane).

## Still missing

1. **`grid` remote execution (4 `.dis` rows):** `dis/alphabet/grid/farm.dis`, `dis/alphabet/grid/remote.dis`, `dis/alphabet/grid/rexec.dis`, and `dis/alphabet/rexecsrv.dis` need a Ziran host call that starts a procedure of the same bundle while the caller keeps running, plus fd/handle passing.
2. **`/auth` (1 `.dis` row):** `dis/alphabet/main/auth.dis` needs a ZX Inferno Auth client (dis/lib lane); `appl/alphabet/main/auth.zi` currently only reads the key file and reports the missing protocol.
3. **Orphan generator (1 `.dis` row):** `dis/alphabet/mktypeset.dis` has no Limbo source on disk; needs an owner decision to port or drop.
4. **Shell-lane & Limbo headers:** `dis/sh/alphabet.dis` (`plans/dis-to-zx/03-shell-commands.md`, shell lane) and `module/alphabet*.m` (still included by the 5 remaining `.b` files) remain until the blocked rows and shell lane retire them.
5. **Ziran bundler workaround:** two modules with a file-private record of the same name still break `ziran bundle` (`record member has no lowered field identity`); private record names must stay unique until fixed upstream.
6. **Parser deduplication:** merge `appl/alphabet/shcmd.zi` with `appl/cmd/sh/shell_parse.zi` (same grammar).
