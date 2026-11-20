# Tcl in Ziran

`tcl.zi` is a headless Ziran library. Add `appl/lib` to the Ziran module
search path and import `tcl`. A zero-initialized `Interpreter` is ready to use.

```zi
#import "std/vec"
using Tcl :: #import "tcl"

main :: () -> s32 {
    interpreter: Tcl.Interpreter;
    result := Tcl.Eval(*interpreter, "set width 6; expr {$width * 7}");
    print("%\n", TextView(result.value));
    return ifx result.code == .OK then 0 else 1;
}
```

`Eval` retains variables and procedure definitions on each interpreter.
Procedure calls have independent local variables and can link to other frames.
Results own their text.
`TakeOutput` takes and clears the text accumulated by `puts`, including
output written before an error. An evaluation has a 10,000-command budget
that also charges loop iterations, and permits 48 nested script levels.

## Supported Tcl

- Command separators, comments, nested braces, quoted and empty words,
  basic backslash escapes and line continuations, variable substitution with
  `$name`, `${name}` and `$array(key)`, and nested command substitution with
  `[script]`. Array keys support substitution inside parentheses.
- `set`, `unset`, `incr`, `append`, `lappend`, `proc`, `return`, `if`,
  `while`, `for`, `foreach`, `break`, `continue`, `catch`, `error` and `eval`.
  Procedures accept defaults and a trailing `args`. `foreach` accepts a
  variable list and one value list. `catch` accepts an optional result variable.
- `array names` and `array size`, `global`, `upvar` for one linked variable,
  `uplevel`, `level`, `switch` with exact patterns, `-` fallthrough and a
  final `default`, and `info args`, `body`, `commands`, `exists` and `procs`.
  Frame selection accepts absolute levels such as `#0` or relative levels
  such as `-1` and `1` for the caller. `info commands` and `info procs` accept
  the optional Limbo pattern argument without filtering. Prefix extensions
  supply command names dynamically and cannot be enumerated.
- `list`, `llength`, `lindex`, `lrange`, `join`, `concat`, `linsert`,
  `lreplace`, exact `lsearch`, `lsort` with optional `-decreasing`, and
  `split`. One-argument `split` preserves the string, following Limbo.
- `string compare`, `equal`, `length`, `index`, `range`, `first`, `last`,
  `tolower`, `toupper`, `trim`, `trimleft` and `trimright`. Lengths and
  indexes count UTF-8 characters. Case conversion and trim use ASCII rules.
  List and string indexes accept decimal integers, `end` and `end-N`.
  A numeric last index in `string range` is exclusive, following Limbo.
  `end` and `end-N` are inclusive.
- `format` supports `%%`, `%s`, `%d`, `%x` and `%f`, with width, left
  alignment, zero padding and precision. Literal text is preserved between
  fields. Following Limbo, `%f` defaults to one decimal place and `%Nf`
  specifies precision. Use `%W.Nf` to set both width and precision. Fixed
  formatting rounds binary64 values to nearest with ties to even. Precision
  and width are limited to 4096. Invalid real arguments return Tcl errors.
  Nonfinite real arguments format as `Inf`, `-Inf` and `NaN`.
- `expr` and `calc` accept signed 32-bit decimal, leading-zero octal and `0x`
  hexadecimal integers, decimal and scientific real literals, and the boolean
  words `true`/`false`, `yes`/`no` and `on`/`off`. They support parentheses,
  unary `+ - ! ~`, binary `+ - * / %`, the numeric comparisons `== != < <= > >=`,
  and `<< >> & ^ | && || ?:`. Remainder, bitwise and logical operators take
  integers. Logical and conditional operands are evaluated eagerly. A
  substitution inside braces must yield one numeric or boolean literal.
  Integer overflow and division by zero return errors. Real arithmetic can
  return `NaN` or `Infinity`.
- The real functions are `abs`, `acos`, `asin`, `atan`, `atan2`, `ceil`, `cos`,
  `cosh`, `exp`, `floor`, `fmod`, `hypot`, `log`, `log10`, `pow`, `sin`, `sinh`,
  `sqrt`, `tan` and `tanh`.
- `time script ?count?` runs the script repeatedly in the calling frame and
  reports milliseconds per iteration. It shares the script command limit.
  Script errors are reported after the requested repetitions and control flow
  such as `return` or `exit` propagates immediately. Native and hosted shells
  provide a monotonic clock. Embedders can inject one with `SetClock`. The
  callback receives a context ID and returns milliseconds or a negative value
  on failure.
- `dumpstack` writes the scalar, array and alias tables for frames visible from
  the current frame to the Tcl output buffer. The entries use variable insertion
  order, with no Limbo hash slot numbers.
- `load libname` activates a command bundle registered with `RegisterLibrary`.
  The embedder passes a slice of `LibraryCommand` descriptors and one context ID.
  Commands are visible to `info commands` and callable after activation. Loads
  are idempotent and a command conflict rejects the entire bundle. `calc`,
  `io`, `list` and `string` are available by default. Dis binary loading and
  guest discovery of external Ziran Tcl modules require separate integration.
- `puts string` and `puts -nonewline string` write to the output buffer.
- `exit` stops the current evaluation, including from a procedure, source
  file or `catch` body. `Eval` returns `.Exit` to the embedding application.
  The shell entry points finish successfully. As in Limbo, arguments to
  `exit` are ignored.
- `source ?-encoding utf-8? fileName` evaluates the loaded script in the current frame and
  shares the command and nesting budgets. Library callers can supply the
  reader with `SetSourceLoader`. The callback receives its context ID,
  the path and a pointer to a `Result`. It sets the result's owned value
  to the script on success or returns an error with `code = .Error`.
  The native and Taiji stdin shells provide file loaders with a 1 MiB limit.
  The Taiji loader resolves paths in the invoking guest namespace.

Namespaces, `{*}` word expansion, numeric and Unicode backslash escapes, wide
expression integers, expression string operands and lazy expression operators
are unsupported. The headless library can be imported by itself or used with
the optional Tk module below.

### Tcl script libraries

All Tcl shell entry points enable the optional `tcl_packages` module. A Ziran
embedder can import it and call `Packages.Attach(*interpreter)` to enable the
same `package` command. A package is registered in one interpreter. `provide`,
`require`, `present`, `ifneeded`, `names`, `versions`, `forget`, `vcompare`,
`vsatisfies`, `prefer` and `unknown` are available. `require` executes the chosen
initialization script in the global frame, uses the same command budget as the
caller, and detects circular loads. Version checks include `-exact`, multiple
requirements, ranges and alpha and beta versions.

Use `auto_path` to list directories containing `pkgIndex.tcl` files. The native
and Taiji stdin shells read those files through their normal script loaders.
An index sees its own directory in the local variable `dir`. For example:

```tcl
# /path/to/sample/pkgIndex.tcl
package ifneeded sample 1.0 [list source [file join $dir sample.tcl]]
```

Put `package provide sample 1.0` in `sample.tcl`, then load it with:

```tcl
lappend auto_path /path/to/sample
package require sample 1.0
```

Discovery checks the directories listed in `auto_path` directly. Scripts use
the interpreter's supported Tcl commands. Tcl's standard library and Tcllib
are separate dependencies, and C extension loading and `.tm` discovery are
unsupported. `package unknown` can supply a custom discovery command. The
in-memory shell can use script registrations but has no file loader.

An embedder can call `Packages.Provide(*interpreter, name, version)` after
initializing a Ziran extension and check the returned `Result`. An `ifneeded`
script can also call `load name` for a bundle supplied by `RegisterLibrary`.
The headless shells only advertise packages explicitly provided to them.

### Channels and files

- `open` supports Limbo `OREAD` (the default), `OWRITE` and `ORDWR` on
  existing files. `r` and `r+` are aliases. `w` and `w+` create or truncate
  a file, with optional octal or decimal permissions (default `0666`).
  `OWRITE` preserves unwritten bytes. Append modes are unsupported.
- `close`, `eof`, `flush`, `gets`, `read`, `seek`, `tell` and channel
  `puts ?-nonewline? fileId string` are available. `seek` accepts
  `SEEKSTART`, `SEEKRELA` and `SEEKEND`, as well as `start`, `current`
  and `end`. Offsets and file sizes are signed 64-bit integers. Failed
  seeks return Tcl errors.
- Counted `read` returns up to the requested number of bytes. The Limbo
  line forms read one line. Bare `read` appends a newline and
  `read -nonewline` returns the original line. `gets` strips the last
  character and accepts the legacy optional variable name without setting
  it. EOF becomes sticky after an empty read. Reads and lines are bounded
  to 1 MiB per command.
- `file join name ?name ...?` joins POSIX paths without a file backend.
  `file exists`, `file size`, `file isfile` and `file isdirectory` query
  the guest path. Writes take effect immediately, so `flush` validates
  the channel and returns success without sending another write.

The Taiji stdin shell configures the guest I/O backend. Its script is read
to EOF before evaluation, which leaves stdin at EOF for channel reads.
The native shell supplies `source` file loading. Embedders can install
their own channel backend via `SetChannelBackend` with a `tcl_io.Backend`.
Callbacks receive the backend's context ID and use the typed guest I/O
conventions. File channels persist between `Eval` calls. `CloseChannels`
releases them, including after `.Exit`. Explicit `stdout` and implicit
`puts` share `TakeOutput`.

### Comparison with shipped Inferno Tcl

Limbo `load` resolves `/dis/lib/tcl_<name>.dis` and calls the module’s `TclLib`
interface. The five libraries shipped here are `calc`, `io`, `list`, `string`
and `tk`. The first four are built into the port, and the optional Tcl/Tk
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
test runner compares the reference, compatibility, expression, format,
headless and channel scripts with the existing Limbo `tclsh` and runs the scripts under ZX
and hosted Taiji. API tests exercise injected channels, clocks and command
libraries. `zxrun` prints a
final scalar `0` on success and `1` on a Tcl error. `zxrun -c` reports the
result as a guest command status.

With a Taiji emulator that provides `taijios_stdin`, `taijios_files` and
`taijios_clock` and `taijios_io` including `Create`, `Seek` and `Stat`, build the shell that
reads a script from the guest's standard input. It evaluates after EOF and
accepts scripts up to 1 MiB.

```sh
(cd appl/cmd && mk zxrun.install install-tclsh-zx)
python3 appl/cmd/tclsh_tests/run.py --stdin /dis/tclsh.zx
```

At the Taiji shell, run `zxrun /dis/tclsh.zx < /appl/cmd/tclsh_tests/reference.tcl`
or pipe a script from a Dis command. For emulators with only console output,
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
zi2zx --root appl/cmd --module-path appl/lib --module-path build/tcl \
    --entry tclsh:main -o build/tcl/tclsh.zx appl/cmd/tclsh.zi
```

## Optional Tk module

`RegisterCommand` binds a name to a Ziran procedure and an optional `s64`
context ID. The procedure receives that ID, the substituted argument words,
and a pointer to `tcl_types.Result` for its owned result or error. Each
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
