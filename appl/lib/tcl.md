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
- `format` supports `%%`, `%s`, `%d` and `%x`, with width, left alignment,
  zero padding and precision. Literal text is preserved between fields.
- `expr` and the Inferno `calc` alias accept signed 32-bit decimal integers,
  `true`/`false`, `yes`/`no`, `on`/`off`, parentheses, unary `+ - !`, binary
  `+ - * / %`, and numeric comparisons `== != < <= > >=`. Substitutions
  inside an expression must yield a single integer or boolean. Overflow and
  division by zero return errors.
- `puts string` and `puts -nonewline string` write to the output buffer.
- `source fileName` evaluates the loaded script in the current frame and
  shares the command and nesting budgets. Library callers can supply the
  reader with `SetSourceLoader`. The callback receives its context ID,
  the path and a pointer to a `Result`. It sets the result's owned value
  to the script on success or returns an error with `code = .Error`.
  The native and Taiji stdin shells provide file loaders with a 1 MiB limit.
  The Taiji loader resolves paths in the invoking guest namespace.

Namespaces, `{*}` word expansion, numeric and Unicode backslash escapes, wide
integers, floating-point and lazy expression operators, Tcl packages and channels
are unsupported. The headless library can be imported by itself or used with
the optional Tk module below.

### Comparison with shipped Inferno Tcl

The shipped Limbo interpreter additionally registers `dumpstack`, `exit`,
`load`, `time`, `close`, `eof`, `file`, `flush`, `gets`, `open`, `read`,
`seek` and `tell`, and accepts channel arguments for `puts`. Limbo `load`
requires a Dis module. The shipped calculator supports floating-point math
and named functions. These commands, options and arithmetic features still
need a port. `string match`, `wordstart` and `wordend` are empty stubs in
the shipped interpreter and are unsupported here. The Ziran implementation
also handles ASCII `string toupper`, string search and trim, and `format`
literal text where the Limbo implementation has stubs or bugs.

## Build, test and run

From the TaijiOS root, with `ziran` and `zi2zx` on PATH and the existing
ZX-enabled Linux emulator installed:

```sh
python3 appl/cmd/tclsh_tests/run.py
build/tcl/native/tclsh_native appl/cmd/tclsh_tests/core.tcl
```

The native shell also reads stdin with `-` or when given no filename. The
test runner compares the reference and compatibility scripts with the existing
Limbo `tclsh`, runs the scripts under ZX and hosted Taiji, and tests the library
API separately. `zxrun` prints a final scalar `0` on success and `1` on a Tcl
error.

With a Taiji emulator that provides `taijios_stdin.Read` and
`taijios_files.ReadAt`, build the shell that
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
and `tcl_string.b`. These files carry the Inferno distribution attribution and
MIT terms in [NOTICE](../../NOTICE).
