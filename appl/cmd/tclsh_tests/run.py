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
    path = "/appl/cmd/tclsh_tests/sourced.tcl"
    (BUILD / "source-script.tcl").write_text(source_script(path))
    expect(guest(f"zxrun {image} < /build/tcl/source-script.tcl"), "sourced=8\n0\n", codes=(0, -9))
    expect(guest(f"echo 'source {path}.missing' | zxrun {image}"),
           f'tclsh: could not read Tcl script "{path}.missing"\n1\n', codes=(0, -9))
    print("Hosted Tcl stdin passed file redirection, multiple reads, pipes, EOF, source and error status")


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
    print("Channel compatibility fixture matched shipped Limbo Dis")

    if image:
        directory = prepare_channel_files()
        expect(guest(f"zxrun {image} < /appl/cmd/tclsh_tests/channels.tcl"), expected + "0\n", codes=(0, -9))
        assert (directory / "existing").read_bytes() == b"xyq\nE"
        expected = (FIXTURES / "channel_file.out").read_text()
        expect(guest(f"zxrun {image} < /appl/cmd/tclsh_tests/channel_file.tcl"), expected + "0\n", codes=(0, -9))
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
        expect(guest(f"zxrun {image} < /build/tcl/large-channel.tcl"),
               f"10000:{length - 10000}:0\n1\n0\n", codes=(0, -9))
        assert (directory / "large file").read_bytes() == payload.encode()

    script = "puts before\nproc stop {} {exit 7; puts after-exit}\ncatch {stop}; puts after-catch\n"
    (BUILD / "channel-exit.tcl").write_text(script)
    expect(guest("tclsh /build/tcl/channel-exit.tcl"), "before\n", codes=(0, -9))
    if image:
        expect(guest(f"zxrun -c {image} < /build/tcl/channel-exit.tcl; echo $status"),
               "before\n\n", codes=(0, -9))
        expect(guest(f"echo 'read missing 1' | zxrun -c {image}; echo $status"),
               'tclsh: bad file identifier "missing"\n|1\n', codes=(0, -9))
        print("Hosted Tcl passed oversized transfers, noncatchable exit and shell status")


def source_script(path):
    return f"proc loadScript {{value}} {{source {{{path}}}; return $value}}\nputs sourced=[loadScript 5]\n"


def main():
    cli = argparse.ArgumentParser()
    cli.add_argument("--stdin", metavar="GUEST_IMAGE", help="test hosted Tcl stdin and guest I/O")
    args = cli.parse_args()
    BUILD.mkdir(parents=True, exist_ok=True)
    native = BUILD / "native"
    subprocess.run(["ziran", "build", "--target=c", "--exe", "--root", "appl/cmd",
                    "--module-path", "appl/lib", "--entry", "tclsh_native:main",
                    "-o", native, "appl/cmd/tclsh_native.zi"], cwd=ROOT, env=ENV, check=True)
    shell = native / "tclsh_native"

    for name in ("core", "reference", "compatibility"):
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
    legacy = guest("tclsh /build/tcl/legacy-reference.tcl")
    # Inferno Tcl adds this call-site annotation around the same error.
    dis_error = 'In function noSuchCommand.....\n\tinvalid command name "noSuchCommand"'
    expect(legacy, reference.replace('invalid command name "noSuchCommand"', dis_error), codes=(0, -9))
    print("reference.tcl matched Limbo Dis, including its extra error annotation")

    script = (FIXTURES / "compatibility.tcl").read_text()
    (BUILD / "legacy-compatibility.tcl").write_text(script + "exit\n")
    expect(guest("tclsh /build/tcl/legacy-compatibility.tcl"),
           (FIXTURES / "compatibility.out").read_text(), codes=(0, -9))
    print("compatibility.tcl matched Limbo Dis for arrays, global, info, switch, lists and strings")

    expect(capture([shell, "-"], source_script(FIXTURES / "sourced.tcl")), "sourced=8\n")
    (BUILD / "source-script.tcl").write_text(source_script("/appl/cmd/tclsh_tests/sourced.tcl") + "exit\n")
    expect(guest("tclsh /build/tcl/source-script.tcl"), "sourced=8\n", codes=(0, -9))
    print("source evaluated in the calling procedure on native Ziran and Limbo Dis")

    for script, diagnostic in (
        ('puts before; set v "unfinished', "missing close-quote"),
        ('puts before; set v "bad"suffix', "extra characters after close-quote"),
        ('puts before; set v {bad}suffix', "extra characters after close-brace"),
        ('puts before; break', 'invoked "break" outside of a loop'),
        ('puts before; set x $array(key', "missing close-parenthesis for variable name"),
        ('puts before; set x $' + 'a($' * 50 + 'leaf' + ')' * 50, "script nesting limit exceeded"),
        ('puts before; switch a {a -}', "switch fallthrough has no body"),
        ('puts before; uplevel 1 {set x}', "bad stack level"),
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
    channel_suite(args.stdin)


if __name__ == "__main__":
    main()
