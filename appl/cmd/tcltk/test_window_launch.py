"""Verify application dispatch and window controls across the graphical ZX bridge."""

import argparse
from pathlib import Path
from tempfile import TemporaryDirectory
import subprocess

from test_logwindow import private_display, read_output
from test_tcltk import BUILD, EMU, ROOT, SOURCES, command, launch, stop, until


PARENT = r'''
using Surface :: #import "zx_surface";
using Wm :: #import "taijios_wm";
using Args :: #import "taijios_args";

main :: () -> s32 {
    words := "an alias\x00café file\x00\x00line\nnext; {x}\x00";
    if Wm.Launch("child.dis", words) != -1 { return 1 }
    if !Surface.Open("Launch parent", 160, 100) { return 2 }
    legacy := Args.OperandCount() == 2;
    expected: s32 = 0;
    if legacy { expected = -1; }
    if Wm.Launch("child.dis", words) != expected { return 3 }
    if Wm.Launch("-child.zx", words) != expected { return 4 }
    if Wm.Launch(Args.Operand(0), "device\x00café file\x00\x00line\nnext; {x}\x00") != expected { return 11 }
    if Wm.Launch("missing.dis", words) != -1 { return 5 }
    if Wm.Launch("missing.zx", words) != -1 { return 6 }
    if Wm.Launch("child.dis", "unfinished") != -1 { return 7 }
    if Wm.Launch("child.dis", "\x00") != -1 { return 8 }
    if Wm.Launch("child.dis\x00", words) != -1 { return 9 }
    Surface.Close();
    if Wm.Launch("child.dis", words) != -1 { return 10 }
    print("LAUNCH PARENT OK\n");
    return 0;
}
'''

ZX_CHILD = r'''
using Surface :: #import "zx_surface";
using Args :: #import "taijios_args";

main :: () -> s32 {
    if Args.OperandCount() != 3 || Args.Operand(0) != "café file" ||
       Args.Operand(1) != "" || Args.Operand(2) != "line\nnext; {x}" { return 1 }
    if !Surface.Open("ZX child", 160, 100) { return 2 }
    Surface.Close();
    print("LAUNCH ZX CHILD OK\n");
    return 0;
}
'''

DIS_CHILD = r'''
implement Child;
include "sys.m";
include "draw.m";
Child: module { init: fn(ctxt: ref Draw->Context, args: list of string); };

init(ctxt: ref Draw->Context, args: list of string)
{
    sys := load Sys Sys->PATH;
    (ok, nil) := sys->stat("./child.dis");
    if(ctxt == nil || ctxt.wm == nil || ok < 0 || len args != 4 ||
       hd tl args != "café file" ||
       hd tl tl args != "" || hd tl tl tl args != "line\nnext; {x}")
        raise "launch: invalid Dis context or arguments";
    case hd args {
        "an alias" => sys->print("LAUNCH DIS CHILD OK\n");
        "device" => sys->print("LAUNCH DEVICE CHILD OK\n");
        * => raise "launch: invalid Dis argv[0]";
    }
}
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--emulator", type=Path, default=EMU)
    parser.add_argument("--launcher", default="/dis/zxrun.dis")
    parser.add_argument("--legacy", action="store_true")
    parser.add_argument("--legacy-controls", action="store_true")
    options = parser.parse_args()
    BUILD.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=BUILD) as directory:
        fixture = Path(directory)
        for module, name, source, capabilities in (("parent", "parent.zx", PARENT, ("--bind-host", "taijios_wm")),
                                                   ("child", "-child.zx", ZX_CHILD, ())):
            code = fixture / f"{module}.zi"
            code.write_text(source, encoding="utf-8")
            command("ziran", "bundle", "--project", "--root", fixture, "--module-path", SOURCES, "--module-path", ROOT / "appl/cmd",
                    "--bind-host", "zx_surface", "--bind-host", "taijios_args", *capabilities,
                    "--entry", f"{module}:main", "-o", fixture / name, code, check=True)
        code = fixture / "child.b"
        code.write_text(DIS_CHILD, encoding="utf-8")
        command(ROOT / "Linux/386/bin/limbo", "-I", ROOT / "module", "-o", fixture / "child.dis", code, check=True)
        command("ziran", "bundle", "--project", "--root", SOURCES, "--module-path", SOURCES,
                "--module-path", ROOT / "appl/cmd",
                "--bind-host", "zx_surface", "--bind-host", "taijios_args", "--bind-host", "taijios_wm",
                "--entry", "wm_controls_test:main", "-o", fixture / "controls.zx",
                SOURCES / "wm_controls_test.zi", check=True)

        guest = "/" + str(fixture.relative_to(ROOT))
        (fixture / "alias").mkdir()
        legacy = " legacy" if options.legacy else ""
        legacy_controls = " legacy" if options.legacy or options.legacy_controls else ""
        shell = (f"bind {guest} {guest}/alias; cd {guest}/alias; "
                 f"{options.launcher} -c -w ./parent.zx '#U{guest}/child.dis'{legacy}; echo LAUNCH $status; "
                 f"{options.launcher} -c -w ./controls.zx{legacy_controls}; echo CONTROLS $status")
        output = bytearray()
        expected = {b"LAUNCH PARENT OK", b"LAUNCH ", b"WINDOW CONTROLS OK", b"CONTROLS "}
        if not options.legacy:
            expected |= {b"LAUNCH DIS CHILD OK", b"LAUNCH ZX CHILD OK", b"LAUNCH DEVICE CHILD OK"}

        with private_display() as env, launch(env, options.emulator.resolve(), "-r", ROOT, "-g", "800x600", "wm/wm", "/dis/sh.dis", "-c",
                    shell, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as app:
            def matched():
                read_output(app, output)
                lines = bytes(output).split(b"\n")[:-1]
                assert all(line in expected for line in lines), output.decode(errors="replace")
                return expected.issubset(lines)

            try:
                until(matched, "application launch did not finish")
            except AssertionError as failure:
                raise AssertionError(f"{failure}\n{output.decode(errors='replace')}") from failure
            finally:
                stop(app)
    print("Legacy launch rejected" if options.legacy else "Dis and ZX children received the guest context and exact arguments")
    print("Legacy launcher rejected resize and cursor" if legacy_controls else "Window resize, stale frames, and cursor requests passed")


if __name__ == "__main__":
    main()
