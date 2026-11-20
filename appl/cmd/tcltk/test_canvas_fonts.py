"""Compare Tk's guest bitmap fonts and Canvas text layout with stock Inferno."""
import argparse
import io
from itertools import zip_longest
from pathlib import Path
from shutil import copyfile
from tempfile import TemporaryDirectory

from PIL import Image, ImageChops
from test_about import guest, transcript
from test_logwindow import private_display, read_output
from test_memory import desktop
from test_menu import inferno_window, pointer
from test_tcltk import BUILD, ROOT, RUNNER_FLAGS, SOURCES, color_bounds, command, compile_image, until

RED = (255, 0, 0)
WHITE = (255, 255, 255)


def check_commands(env, folder, runner):
    commands = (SOURCES / "canvas_font_commands.tcl").read_text()
    # Reuse the same slots after changing inherited and explicit faces.
    cycle = """.c configure -font /fonts/misc/latin1.6x13.font
.c itemconfigure 1 -font /fonts/misc/latin1.6x10.font
.c bbox 1
.c itemconfigure 1 -font /fonts/misc/latin1.8x13.font
.c bbox 1
"""
    suffixed = folder / "suffixed.font"
    suffixed.write_text("13 10\n0x00 0xff atlas\n")
    copyfile(ROOT / "fonts/misc/latin1.8x13", folder / "atlas.0")
    commands += cycle*24 + f".c itemconfigure 1 -font {guest(suffixed)}\n.c bbox 1\n"
    stock_script = folder / "stock.tcl"
    stock_script.write_text(commands)
    stock = transcript(env, f"tkcmd < {guest(stock_script)}")
    assert b"#!failed to open font" in stock, stock
    assert all(line.startswith(b"#") for line in stock), stock
    hosted_script = folder / "commands.tcl"
    hosted_script.write_text("".join(
        f"set status [catch {{{line}}} answer]\n"
        f"if {{$status}} {{puts !$answer}} elseif {{[string length $answer]}} {{puts $answer}}\n"
        for line in commands.splitlines()
    ) + "destroy .\n")
    hosted = transcript(env, f"zxrun -w {guest(runner)} < {guest(hosted_script)}")
    expected = [*(line[1:] for line in stock), b"0"]
    for number, (want, got) in enumerate(zip_longest(expected, hosted), 1):
        assert want == got, (number, want, got)
    print(f"Hosted runner matched {len(stock)} stock Canvas font results, including 24 face replacement cycles")


def exercise(env, invocation, *, stock):
    with desktop(env, invocation) as app:
        window = inferno_window(env)
        output = bytearray()

        def events():
            read_output(app, output)
            lines = output.decode().splitlines()
            assert not any(line.startswith(("#!", "tcltk:", "tk: ")) for line in lines), lines
            return [line for line in lines if not line.startswith("#")] if stock else lines

        bounds = None

        def capture():
            nonlocal bounds
            png = command("import", "-window", window, "png:-", env=env, check=True, capture_output=True).stdout
            image = Image.open(io.BytesIO(png)).convert("RGB")
            bounds = color_bounds(image, RED)
            if bounds and (bounds[2]-bounds[0], bounds[3]-bounds[1]) == (180, 102):
                return image.crop(bounds), bounds[:2]
            return None

        until(lambda: events() == ["ready"], "Canvas font fixture did not initialize")
        try:
            canvas, (left, top) = until(capture, "Canvas text did not paint at its requested size")
        except AssertionError as failure:
            raise AssertionError(f"{failure}: stock={stock}, red bounds={bounds}") from failure
        assert color_bounds(canvas.crop((0, 0, 180, 28)), WHITE), "Inherited font text is missing"
        assert color_bounds(canvas.crop((0, 88, 180, 102)), WHITE), "Clipped text is missing"
        command("xdotool", "windowfocus", window, env=env, check=True)
        pointer(env, window, left+9, top+14, "sleep", "0.06", "mousedown", "1", "sleep", "0.09", "mouseup", "1")
        until(lambda: events() == ["ready", "8 8 116 27"], "Canvas text bounds did not receive the press")
        return canvas


def main():
    cli = argparse.ArgumentParser()
    cli.add_argument("--installed", action="store_true")
    args = cli.parse_args()
    BUILD.mkdir(parents=True, exist_ok=True)
    runner = ROOT / "dis/tcltk.zx" if args.installed else BUILD / "tcltk-fonts.zx"
    if not args.installed:
        compile_image("tcltk", runner, *RUNNER_FLAGS)
    fixture = guest(SOURCES / "canvas_font_window.tcl")
    with TemporaryDirectory(dir=BUILD) as scratch, private_display() as env:
        check_commands(env, Path(scratch), runner)
        stock = exercise(env, f"{{cat {fixture}; sleep 45}} | tkcmd", stock=True)
        hosted = exercise(env, f"zxrun -w {guest(runner)} < {fixture}", stock=False)
        delta = ImageChops.difference(stock, hosted)
        assert not delta.getbbox(), ("Canvas font pixels differ from stock", delta.getbbox())
    print("Stock and hosted Canvas matched all 18,360 pixels, including UTF-8 glyphs, multiline text and clipping")


if __name__ == "__main__":
    main()
