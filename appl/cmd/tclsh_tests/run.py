"""Exercise the Tcl scripts and API on the native, portable and Taiji runners."""

import argparse
import math
import os
from pathlib import Path
import subprocess


FIXTURES = Path(__file__).resolve().parent
ROOT = FIXTURES.parents[2]
BUILD = ROOT / "build/tcl"
EMU = ROOT / "Linux/386/bin/emu"
ENV = os.environ.copy()
for name in ("DISPLAY", "WAYLAND_DISPLAY", "XAUTHORITY", "DBUS_SESSION_BUS_ADDRESS"):
    ENV.pop(name, None)
ENV["HARMONY_DESKTOP_RECOVERY"] = "0"


def capture(args, source=None):
    return subprocess.run(args, cwd=ROOT, env=ENV, input=source, text=True,
                          capture_output=True, start_new_session=True, timeout=30)


def expect(run, expected, *, codes=(0,), error=""):
    actual = run.returncode, run.stdout, run.stderr
    if run.returncode not in codes or run.stdout != expected or run.stderr != error:
        raise AssertionError(f"{run.args}\nreturned {actual!r}\n"
                             f"expected {codes!r}, {expected!r}, {error!r}")


def compile_zx(source, entry, output, *module_paths):
    args = ["ziran", "bundle", "--project", "--root", source.parent]
    for path in module_paths:
        args.extend(["--module-path", path])
    subprocess.run([*args, "--entry", entry, "-o", output, source], cwd=ROOT,
                   env=ENV, check=True)


def guest(command):
    return capture([EMU, "-r", ROOT, "/zx/sh.dis", "-c", command], "")


PROMPT = "tcl% "


def run_file(image, path, *, status=False):
    # The shell evaluates its file operand, then prompts once before end of input.
    if status:
        return guest(f"zxrun -c {image} {path} < /dev/null; echo $status")
    return guest(f"zxrun {image} {path} < /dev/null")


def stdin_suite(image):
    # The prefix forces several guest fd 0 reads before the first Tcl command.
    (BUILD / "stdin.tcl").write_text(("# stdin read boundary test\n" * 400) + "set x 5\n")
    expect(guest(f"zxrun {image} < /build/tcl/stdin.tcl"), PROMPT * 401 + "5\n" + PROMPT + "0\n", codes=(0, -9))
    script = (FIXTURES / "core.tcl").read_text()
    expected = (FIXTURES / "core.out").read_text()
    expect(run_file(image, "/appl/cmd/tclsh_tests/core.tcl"), expected + PROMPT + "0\n", codes=(0, -9))
    expect(guest(f"echo 'puts from-pipe' | zxrun {image}"), PROMPT + "from-pipe\n" + PROMPT + "0\n", codes=(0, -9))
    expect(guest(f"zxrun {image} < /dev/null"), PROMPT + "0\n", codes=(0, -9))
    expect(guest(f"echo 'error intentional' | zxrun {image}"),
           PROMPT + "In function error intentional.....\n\tintentional\n" + PROMPT + "0\n", codes=(0, -9))
    path = "/appl/cmd/tclsh_tests/sourced.tcl"
    (BUILD / "source-script.tcl").write_text(source_script(path))
    expect(run_file(image, "/build/tcl/source-script.tcl"), "sourced=8\n" + PROMPT + "0\n", codes=(0, -9))
    expect(guest(f"echo 'source {path}.missing' | zxrun {image}"),
           PROMPT + f'In function source {path}.missing.....\n\tcould not read Tcl script "{path}.missing"\n'
           + PROMPT + "0\n", codes=(0, -9))
    print("Hosted Tcl shell passed file operands, multiple stdin reads, pipes, EOF, source and error reports")
    precision = "puts [expr {1.0000000009313225746 > 1.0}]\nputs [expr {sqrt(2)}]\n"
    (BUILD / "expression-installed-precision.tcl").write_text(precision)
    expect(run_file(image, "/build/tcl/expression-installed-precision.tcl"),
           "1\n1.4142135623730951\n" + PROMPT + "0\n", codes=(0, -9))
    print("Hosted Tcl preserves binary64 precision")


def fixed_format_edges(shell, image):
    cases = [("0.1", 60), ("1.7976931348623157e308", 0), ("5e-324", 1074),
             ("2.225073858507201e-308", 1074), ("-1e-999", 3)]
    lines = [f"puts [format %.{precision}f {value}]" for value, precision in cases]
    outputs = [f"{float(value):.{precision}f}" for value, precision in cases]
    lines += ["puts [string length [format %.4096f 1.0]]",
              "puts [format {left=[%08.2f] %% %s} -1.25 value]",
              "puts [format {%f %f %f} Infinity -Infinity NaN]",
              "puts [format {[%4.1s]|[%07.2f]|[%-4d]|[%4.1s]} éz -1.25 21 βγ]"]
    outputs += ["4098", "left=[-0001.25] % value", "Inf -Inf NaN",
                "[   é]|[-001.25]|[21  ]|[   β]"]
    script = "\n".join(lines) + "\n"
    expected = "\n".join(outputs) + "\n"
    expect(capture([shell, "-"], script), expected)
    (BUILD / "tcl_input.zi").write_text("Script :: #string TCL_SCRIPT_END\n" +
                                      script + "TCL_SCRIPT_END;\n")
    bundled = BUILD / "format-edges.zx"
    compile_zx(ROOT / "appl/cmd/tclsh.zi", "tclsh:main", bundled, BUILD)
    expect(capture(["zi2zx", "run", "--backend", "engine", bundled]), expected + "0\n")
    if image:
        (BUILD / "format-edges.tcl").write_text(script)
        expect(run_file(image, "/appl/cmd/tclsh_tests/format.tcl"),
               (FIXTURES / "format.out").read_text() + PROMPT + "0\n", codes=(0, -9))
        expect(run_file(image, "/build/tcl/format-edges.tcl"),
               expected + PROMPT + "0\n", codes=(0, -9))
    print("Fixed-point formatting covered maximum and subnormal binary64 values, signed zero and limits")


def headless_output(output):
    normalized = []
    variables = []
    for line in output.splitlines():
        content = line.lstrip()
        if content.startswith("H_link at "):
            continue
        if content.startswith("name ["):
            variables.append(line)
            continue
        normalized.extend(sorted(variables))
        variables.clear()
        if line.startswith("duration="):
            duration, _, unit = line.removeprefix("duration=").partition(" ")
            value = float(duration)
            assert math.isfinite(value) and value >= 0 and unit == "milliseconds per iteration", line
            line = "duration=<milliseconds>"
        normalized.append(line)
    normalized.extend(sorted(variables))
    return "\n".join(normalized) + "\n"


def headless_suite(shell, image):
    fixture = FIXTURES / "headless.tcl"
    script = fixture.read_text()
    expected = fixture.with_suffix(".out").read_text()
    (BUILD / "legacy-headless.tcl").write_text(script + "exit\n")
    (BUILD / "tcl_headless_input.zi").write_text("Script :: #string TCL_HEADLESS\n" + script + "TCL_HEADLESS;\n")
    model = BUILD / "tcl_headless_api.zx"
    compile_zx(FIXTURES / "tcl_headless_api.zi", "tcl_headless_api:main", model, BUILD)
    workloads = [
        (capture([shell, fixture]), expected, (0,)),
        (guest("tclsh /build/tcl/legacy-headless.tcl"), expected, (0, -9)),
        (capture(["zi2zx", "run", "--backend", "engine", model]), expected + "0\n", (0,)),
        (guest("zxrun /build/tcl/tcl_headless_api.zx"), expected + "0\n", (0, -9)),
    ]
    if image:
        workloads.append((run_file(image, "/appl/cmd/tclsh_tests/headless.tcl"), expected + PROMPT + "0\n", (0, -9)))
    for result, output, codes in workloads:
        result.stdout = headless_output(result.stdout)
        expect(result, output, codes=codes)
    print("Timing, stack frames and library load matched Limbo and the native, ZX and Taiji runners")
    print("Injected clocks, command libraries and atomic activation verified on ZX and Taiji")


def prepare_channel_files():
    directory = BUILD / "channel-suite"
    directory.mkdir(exist_ok=True)
    (directory / "input").write_bytes(b"first\nsecond\nzebra")
    (directory / "existing").write_bytes(b"ABCDE")
    (directory / "created").unlink(missing_ok=True)
    return directory


def channel_suite(image):
    contract = {"Channels": "channels.tcl", "ChannelsExpected": "channels.out",
                "File": "channel_file.tcl", "FileExpected": "channel_file.out"}
    (BUILD / "tcl_channel_input.zi").write_text("".join(
        f"{name} :: #string TCL_FIXTURE\n{(FIXTURES / path).read_text()}TCL_FIXTURE;\n"
        for name, path in contract.items()))

    model = BUILD / "tcl_channels_api.zx"
    compile_zx(FIXTURES / "tcl_channels_api.zi", "tcl_channels_api:main", model, BUILD)
    expect(capture(["zi2zx", "run", "--backend", "engine", model]), "Tcl channels API OK\n0\n")
    expect(guest("zxrun /build/tcl/tcl_channels_api.zx"), "Tcl channels API OK\n0\n", codes=(0, -9))
    print("Injected channel backend verified on ZX and Taiji")

    directory = prepare_channel_files()
    expected = (FIXTURES / "channels.out").read_text()
    (BUILD / "legacy-channels.tcl").write_text((FIXTURES / "channels.tcl").read_text() + "exit\n")
    expect(guest("tclsh /build/tcl/legacy-channels.tcl"), expected, codes=(0, -9))
    assert (directory / "existing").read_bytes() == b"xyq\nE"
    print("Channel compatibility fixture matched the shipped Limbo output")

    if image:
        directory = prepare_channel_files()
        expect(run_file(image, "/appl/cmd/tclsh_tests/channels.tcl"), expected + PROMPT + "0\n", codes=(0, -9))
        assert (directory / "existing").read_bytes() == b"xyq\nE"
        expected = (FIXTURES / "channel_file.out").read_text()
        expect(run_file(image, "/appl/cmd/tclsh_tests/channel_file.tcl"), expected + PROMPT + "0\n", codes=(0, -9))
        assert (directory / "created").read_bytes() == b"ok"
        print("Hosted Tcl matched Limbo channels and passed guest create, seek, tell and file metadata")

        payload = "Tcl channel bytes\n" * 900
        (BUILD / "large-channel.tcl").write_text(
            "set path {/build/tcl/channel-suite/large file}\n"
            "set out [open $path w+]\n"
            f"puts -nonewline $out {{{payload}}}\n"
            "seek $out 0\nputs \"[string length [read $out 10000]]:[string length [read $out 10000]]:[eof $out]\"\n"
            "read $out 1\nputs [eof $out]\nclose $out\n")
        length = len(payload)
        expect(run_file(image, "/build/tcl/large-channel.tcl"),
               f"10000:{length - 10000}:0\n1\n" + PROMPT + "0\n", codes=(0, -9))
        assert (directory / "large file").read_bytes() == payload.encode()

    script = "puts before\nproc stop {} {exit 7; puts after-exit}\ncatch {stop}; puts after-catch\n"
    (BUILD / "channel-exit.tcl").write_text(script)
    expect(guest("tclsh /build/tcl/channel-exit.tcl"), "before\n", codes=(0, -9))
    if image:
        expect(run_file(image, "/build/tcl/channel-exit.tcl", status=True), "before\n\n", codes=(0, -9))
        expect(guest(f"echo 'read missing 1' | zxrun -c {image}; echo $status"),
               PROMPT + 'In function read missing.....\n\tbad file identifier "missing"\n' + PROMPT + "\n",
               codes=(0, -9))
        print("Hosted Tcl passed oversized transfers, noncatchable exit and shell status")


def source_script(path):
    return f"proc loadScript {{value}} {{source {{{path}}}; return $value}}\nputs sourced=[loadScript 5]\n"


def package_suite(shell, image):
    # Look up both versions from within a procedure with its own dir and
    # counter. The index should see its package directory and the initializer
    # should run once in the global frame.
    def script(path):
        return f"""set auto_path [list {{{path}/missing}} {{{path}/arithmetic library}}]
set initializations 0
set dir caller
proc usePackage {{value}} {{
    set dir local
    set initializations -1
    puts [list [package require demo::offset 2] [offset $value] $dir $initializations]
}}
usePackage 18
puts [list [package require demo::twice 1] [twice 21] $dir $initializations]
puts [list [catch {{package require demo::missing}}] [package provide Tk]]
package forget demo::twice
puts [list [package require demo::twice] $initializations]
"""

    expected = "2.0 37 local -1\n1.0 42 caller 1\n1 {}\n1.0 2\n"
    expect(capture([shell, "-"], script(FIXTURES / "packages")), expected)
    if image:
        (BUILD / "package-discovery.tcl").write_text(script("/appl/cmd/tclsh_tests/packages"))
        expect(run_file(image, "/build/tcl/package-discovery.tcl"), expected + PROMPT + "0\n", codes=(0, -9))
        expected_registry = (FIXTURES / "packages.out").read_text()
        expect(run_file(image, "/appl/cmd/tclsh_tests/packages.tcl"),
               expected_registry + PROMPT + "0\n", codes=(0, -9))
    print("Tcl package discovery loaded indexed scripts, resolved dependencies and initialized once")


def main():
    cli = argparse.ArgumentParser()
    cli.add_argument("--stdin", metavar="GUEST_IMAGE", help="test hosted Tcl stdin and guest I/O")
    args = cli.parse_args()
    BUILD.mkdir(parents=True, exist_ok=True)
    native = BUILD / "native"
    subprocess.run(["ziran", "build", "--project", "--target=c", "--exe", "--root", "appl/cmd",
                    "--entry", "tclsh_native:main",
                    "-o", native, "appl/cmd/tclsh_native.zi"], cwd=ROOT, env=ENV, check=True)
    shell = native / "tclsh_native"

    for name in ("core", "reference", "compatibility", "expression", "format", "packages"):
        fixture = FIXTURES / f"{name}.tcl"
        script = fixture.read_text()
        expected = fixture.with_suffix(".out").read_text()
        expect(capture([shell, fixture]), expected)
        (BUILD / "tcl_input.zi").write_text("Script :: #string TCL_SCRIPT_END\n" +
                                            script + "TCL_SCRIPT_END;\n")
        image = BUILD / ("tclsh.zx" if name == "reference" else f"{name}.zx")
        compile_zx(ROOT / "appl/cmd/tclsh.zi", "tclsh:main", image, BUILD)
        expect(capture(["zi2zx", "run", "--backend", "engine", image]), expected + "0\n")
        expect(guest(f"zxrun /build/tcl/{image.name}"), expected + "0\n", codes=(0, -9))
        print(f"{name}.tcl matched on native Ziran, ZX engine and hosted Taiji")

    script = (FIXTURES / "reference.tcl").read_text()
    (BUILD / "legacy-reference.tcl").write_text(script + "exit\n")
    reference = (FIXTURES / "reference.out").read_text()
    # The Limbo shell also put its "In function noSuchCommand....." report into caught messages.
    expect(guest("tclsh /build/tcl/legacy-reference.tcl"), reference, codes=(0, -9))
    print("tclsh reference.tcl matched the Limbo output apart from its caught-error annotation")

    script = (FIXTURES / "compatibility.tcl").read_text()
    (BUILD / "legacy-compatibility.tcl").write_text(script + "exit\n")
    expect(guest("tclsh /build/tcl/legacy-compatibility.tcl"),
           (FIXTURES / "compatibility.out").read_text(), codes=(0, -9))
    print("tclsh compatibility.tcl matched the Limbo output for arrays, global, info, switch, lists and strings")

    expression = (FIXTURES / "expression.out").read_text()
    script = (FIXTURES / "expression.tcl").read_text()
    (BUILD / "legacy-expression.tcl").write_text(script + "exit\n")
    expect(guest("tclsh /build/tcl/legacy-expression.tcl"), expression, codes=(0, -9))
    print("tclsh expression.tcl matched the Limbo output for numeric operations and all 20 math functions")
    fixture = FIXTURES / "format.tcl"
    (BUILD / "legacy-format.tcl").write_text(fixture.read_text() + "exit\n")
    expect(guest("tclsh /build/tcl/legacy-format.tcl"),
           fixture.with_suffix(".out").read_text(), codes=(0, -9))
    print("tclsh format.tcl matched the Limbo output for fixed-point precision, rounding and alignment")
    fixed_format_edges(shell, args.stdin)

    expect(capture([shell, "-"], "puts [calc {sqrt(81)}]; puts [expr {2+1.0+1}]"), "9\n4\n")
    expect(capture([shell, "-"], "set wide [expr {abs(-2147483648)}]; puts [expr {$wide/2.0}]"),
           "1073741824\n")

    expression_api = BUILD / "tcl_expression_api.zx"
    compile_zx(FIXTURES / "tcl_expression_api.zi", "tcl_expression_api:main", expression_api)
    expected_api = "Tcl expression API OK\n0\n"
    expect(capture(["zi2zx", "run", "--backend", "engine", expression_api]), expected_api)
    expect(guest("zxrun /build/tcl/tcl_expression_api.zx"), expected_api, codes=(0, -9))
    print("Expression results and deterministic errors verified on ZX and Taiji")

    expect(capture([shell, "-"], source_script(FIXTURES / "sourced.tcl")), "sourced=8\n")
    (BUILD / "source-script.tcl").write_text(source_script("/appl/cmd/tclsh_tests/sourced.tcl") + "exit\n")
    expect(guest("tclsh /build/tcl/source-script.tcl"), "sourced=8\n", codes=(0, -9))
    print("source evaluated in the calling procedure on native Ziran and the guest tclsh")

    for script, diagnostic in (
        ('puts before; set v "unfinished', "missing close-quote"),
        ('puts before; set v "bad"suffix', "extra characters after close-quote"),
        ('puts before; set v {bad}suffix', "extra characters after close-brace"),
        ('puts before; break', 'invoked "break" outside of a loop'),
        ('puts before; set x $array(key', "missing close-parenthesis for variable name"),
        ('puts before; set x $' + 'a($' * 50 + 'leaf' + ')' * 50, "script nesting limit exceeded"),
        ('puts before; switch a {a -}', "switch fallthrough has no body"),
        ('puts before; uplevel 1 {set x}', "bad stack level"),
        ('puts before; set operand {1+2}; expr {$operand}', "expected numeric or boolean expression operand"),
        ('puts before; expr {1.5 % 2}', "expected integer operands"),
        ('puts before; expr {abs(1,2)}', "wrong number of function arguments or missing close-parenthesis"),
        ('puts before; format %f {1+2}', 'expected real format argument'),
        ('puts before; format %.4097f 1.0', 'format precision exceeds limit'),
        ('puts before; dumpstack extra', 'wrong # args: should be "dumpstack"'),
        ('puts before; time {} wrong', 'expected integer but got "wrong"'),
        ('puts before; load notRegistered', "Cannot load /zx/lib/tcl_notRegistered.dis"),
    ):
        expect(capture([shell, "-"], script), "before\n", codes=(1,), error=diagnostic + "\n")
    print("Malformed and unsupported scripts returned the expected errors")

    api = BUILD / "tclsh_api.zx"
    compile_zx(FIXTURES / "tclsh_api.zi", "tclsh_api:main", api)
    expect(capture(["zi2zx", "run", "--backend", "engine", api]), "Tcl API OK\n0\n")
    expect(guest("zxrun /build/tcl/tclsh_api.zx"), "Tcl API OK\n0\n", codes=(0, -9))
    print("Extension dispatch, interpreter isolation and recovery verified on ZX and Taiji")
    if args.stdin:
        stdin_suite(args.stdin)
        expect(run_file(args.stdin, "/appl/cmd/tclsh_tests/expression.tcl"),
               expression + PROMPT + "0\n", codes=(0, -9))
        print("Hosted Tcl shell matched the Limbo numeric script")
    headless_suite(shell, args.stdin)
    channel_suite(args.stdin)
    package_suite(shell, args.stdin)


if __name__ == "__main__":
    main()
