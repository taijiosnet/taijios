# Tcl on TaijiOS

TaijiOS's ZX shell uses the standalone [Tcl package](https://git.waozi.xyz/ziranlang/tcl).
Its package documentation covers the `tcl/interpreter` and `tcl/types` APIs,
channels, and Tcl script libraries. The TaijiOS build uses the root manifest
and lock. The guest shell and test fixtures live under `appl/cmd`.

### Comparison with shipped Inferno Tcl

The Limbo interpreter's `load` resolved `/dis/lib/tcl_<name>.dis` and called
the module’s `TclLib` interface. Its five libraries (`calc`, `io`, `list`,
`string` and `tk`) and legacy `wm/wish` have been removed now that `/dis/tclsh.zx`,
`/dis/tcltk.zx` and `/dis/wm/wish.zx` replace them. The first four libraries are built into the port, and the optional Tcl/Tk
app imports its Tk bridge at startup. Hosted ZX resolves imports at startup.
Loading separately compiled extensions after startup would require a guest API
for named lookup and invocation.

A leading `|` in an `open` filename is treated as an ordinary path
by the shipped Limbo shell. Its `file`, `flush` and `tell` are empty stubs. `string match`, `wordstart` and `wordend` are empty stubs in
the shipped interpreter and are unsupported here. The Ziran implementation
also handles ASCII `string toupper`, string search and trim, and `format`
literal text where the Limbo implementation has stubs or bugs.

Real expressions preserve mixed terms and use Ziran's `float64` values on
native, standalone ZX and the installed Taiji runtime. Decimal formatting and
exceptional-value spelling can differ from Limbo. The shared script compares
approximate function results with a tolerance.

## Build, test and run

From the TaijiOS root, with `ziran` and `zi2zx` on PATH and the existing
ZX-enabled Linux emulator installed:

```sh
python3 appl/cmd/tclsh_tests/run.py
build/tcl/native/tclsh_native appl/cmd/tclsh_tests/core.tcl
```

The native shell also reads stdin with `-` or when given no filename. The
test runner checks the reference, compatibility, expression, format,
headless and channel scripts against the output of the Limbo `tclsh` and runs
them under ZX and hosted Taiji. API tests exercise injected channels, clocks and command
libraries. `zxrun` prints a
final scalar `0` on success and `1` on a Tcl error. `zxrun -c` reports the
result as a guest command status.

The guest `tclsh [file ...]` is `/dis/tclsh.zx`, built from
`appl/cmd/tclsh_shell.zi`. Like the Limbo shell it replaced, it evaluates
each file, then reads commands from standard input. It prompts with `tcl% `,
and with `tcl> ` while a command's braces, brackets or quotes are open. It
prints each nonempty result and reports an error as
`In function NAME ARG.....` followed by a tab and the message. A file that
cannot be read is skipped, and a file stops at its first error without a
report. `exit` or the end of input ends the shell. Unlike the Limbo shell it
prints its prompts in order and exits at the end of input. Its error reports
name only the command typed at the prompt. Scripts are limited to 1 MiB.

```sh
(cd appl/cmd && mk zxrun.install install-tclsh-zx)
python3 appl/cmd/tclsh_tests/run.py --stdin /dis/tclsh.zx
```

At the Taiji shell, run `tclsh /appl/cmd/tclsh_tests/reference.tcl`. For emulators with only console output,
`appl/cmd/tclsh.zi` takes `Script` from an in-memory `tcl_input` module.
Install the tested reference example with
`install -m 0644 build/tcl/tclsh.zx dis/tclsh.zx` and run `zxrun /dis/tclsh.zx`.
To build a different script into an image:

```sh
mkdir -p build/tcl
cat > build/tcl/tcl_input.zi <<'ZI'
Script :: #string TCL_SCRIPT_END
set name Taiji
puts "Hello, $name"
TCL_SCRIPT_END;
ZI
ziran bundle --project --root appl/cmd --module-path build/tcl \
    --entry tclsh:main -o build/tcl/tclsh.zx appl/cmd/tclsh.zi
```

## Optional Tk module

`RegisterCommand` binds a name to a Ziran procedure and an optional `s64`
context ID. The procedure receives that ID, the substituted argument words,
and a pointer to `tcl/types.Result` for its owned result or error. Each
interpreter has its own registered commands. `RegisterPrefix` also accepts a
handler for a family of command names, such as Tk widget paths beginning with
`.`. Its handler can return a script to evaluate in the current Tcl frame.
The legacy `tcl_tk.b` bridges to Inferno Tk. The headless interpreter uses
only Ziran libraries.

The [optional Tk package and Bounce toolbar example](../cmd/tcltk/README.md)
use that API. Their window binds to Taiji's generic surface ABI.

## Attribution

This port follows the Inferno Limbo sources `appl/cmd/tclsh.b`,
`appl/lib/tcl.m`, `tcl_core.b`, `tcl_list.b`, `tcl_utils.b`, `tcl_calc.b`,
`tcl_string.b`, and `tcl_io.b`. These files carry the Inferno distribution attribution and
MIT terms in [NOTICE](../../NOTICE).
