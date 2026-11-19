"""Exercise the Tcl scripts and API on the native, portable and Taiji runners."""

import argparse
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
    args = ["zi2zx", "--root", source.parent, "--module-path", "appl/lib"]
    for path in module_paths:
        args.extend(["--module-path", path])
    subprocess.run([*args, "--entry", entry, "-o", output, source], cwd=ROOT,
                   env=ENV, check=True)


def guest(command):
    return capture([EMU, "-r", ROOT, "/dis/sh.dis", "-c", command], "")


def stdin_suite(image):
    # The prefix forces several guest fd 0 reads before the first Tcl command.
    script = (FIXTURES / "core.tcl").read_text()
    (BUILD / "stdin.tcl").write_text(("# stdin read boundary test\n" * 400) + script)
    expected = (FIXTURES / "core.out").read_text()
    expect(guest(f"zxrun {image} < /build/tcl/stdin.tcl"), expected + "0\n", codes=(0, -9))
    expect(guest(f"echo 'puts from-pipe' | zxrun {image}"), "from-pipe\n0\n", codes=(0, -9))
    expect(guest(f"zxrun {image} < /dev/null"), "0\n", codes=(0, -9))
    expect(guest(f"echo 'error intentional' | zxrun {image}"), "tclsh: intentional\n1\n", codes=(0, -9))
    print("Hosted Tcl stdin passed file redirection, multiple reads, pipes, EOF and error status")


def main():
    cli = argparse.ArgumentParser()
    cli.add_argument("--stdin", metavar="GUEST_IMAGE", help="test a ZX-enabled guest stdin image")
    args = cli.parse_args()
    BUILD.mkdir(parents=True, exist_ok=True)
    native = BUILD / "native"
    subprocess.run(["ziran", "build", "--target=c", "--exe", "--root", "appl/cmd",
                    "--module-path", "appl/lib", "--entry", "tclsh_native:main",
                    "-o", native, "appl/cmd/tclsh_native.zi"], cwd=ROOT, env=ENV, check=True)
    shell = native / "tclsh_native"

    for name in ("core", "reference"):
        fixture = FIXTURES / f"{name}.tcl"
        script = fixture.read_text()
        expected = fixture.with_suffix(".out").read_text()
        expect(capture([shell, fixture]), expected)
        (BUILD / "tcl_input.zi").write_text("Script :: #string TCL_SCRIPT_END\n" +
                                            script + "TCL_SCRIPT_END;\n")
        image = BUILD / ("tclsh.zx" if name == "reference" else "core.zx")
        compile_zx(ROOT / "appl/cmd/tclsh.zi", "tclsh:main", image, BUILD)
        expect(capture(["zi2zx", "run", "--backend", "engine", image]), expected + "0\n")
        expect(guest(f"zxrun /build/tcl/{image.name}"), expected + "0\n", codes=(0, -9))
        print(f"{name}.tcl matched on native Ziran, ZX engine and hosted Taiji")

    script = (FIXTURES / "reference.tcl").read_text()
    (BUILD / "legacy-reference.tcl").write_text(script + "exit\n")
    reference = (FIXTURES / "reference.out").read_text()
    legacy = guest("tclsh /build/tcl/legacy-reference.tcl")
    # Inferno Tcl adds this call-site annotation around the same error.
    dis_error = 'In function noSuchCommand.....\n\tinvalid command name "noSuchCommand"'
    expect(legacy, reference.replace('invalid command name "noSuchCommand"', dis_error), codes=(0, -9))
    print("reference.tcl matched Limbo Dis, including its extra error annotation")

    for script, diagnostic in (
        ('puts before; set v "unfinished', "missing close-quote"),
        ('puts before; set v "bad"suffix', "extra characters after close-quote"),
        ('puts before; set v {bad}suffix', "extra characters after close-brace"),
        ('puts before; break', 'invoked "break" outside of a loop'),
        ('puts before; set x $array(key)', "array variables are unsupported"),
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


if __name__ == "__main__":
    main()
