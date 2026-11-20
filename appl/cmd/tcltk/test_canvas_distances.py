"""Compare Canvas screen distances with stock Tk commands and window geometry."""
import argparse
import io
from itertools import zip_longest
from pathlib import Path
from tempfile import TemporaryDirectory

from PIL import Image, ImageChops
from test_about import guest, transcript
from test_logwindow import private_display, read_output
from test_memory import desktop
from test_menu import inferno_window, pointer
from test_tcltk import BACKGROUND, BUILD, ROOT, RUNNER_FLAGS, SOURCES, color_bounds, command, compile_image, until

RED = (255, 0, 0)
BLACK = (0, 0, 0)


def check_commands(env, folder, runner):
    fixture = SOURCES / "canvas_distance_commands.tcl"
    stock = transcript(env, f"tkcmd < {guest(fixture)}")
    assert stock[:4] == [b"#.c", b"#390", b"#60", b"#3"], stock
    assert stock.count(b"#!bad value") == 2, stock
    assert all(line.startswith(b"#") for line in stock), stock
    hosted_script = folder / "commands.tcl"
    hosted_script.write_text("".join(
        f"set status [catch {{{line}}} answer]\n"
        f"if {{$status}} {{puts !$answer}} elseif {{[string length $answer]}} {{puts $answer}}\n"
        for line in fixture.read_text().splitlines()
    ) + "destroy .\n")
    hosted = transcript(env, f"zxrun -w {guest(runner)} < {guest(hosted_script)}")
    for number, (want, got) in enumerate(zip_longest([*(line[1:] for line in stock), b"0"], hosted), 1):
        assert want == got, (number, want, got)
    print(f"Hosted runner matched {len(stock)} stock Canvas distance results, including 10c = 390 pixels")


def exercise(env, invocation, *, stock):
    with desktop(env, invocation) as app:
        window = inferno_window(env)
        output = bytearray()

        def events():
            read_output(app, output)
            lines = output.decode().splitlines()
            assert not any(line.startswith(("#!", "tcltk:", "tk: ")) for line in lines), lines
            return [line for line in lines if not line.startswith("#")] if stock else lines

        def snapshot():
            png = command("import", "-window", window, "png:-", env=env, check=True, capture_output=True).stdout
            return Image.open(io.BytesIO(png)).convert("RGB")

        def capture(size):
            image = snapshot()
            bounds = color_bounds(image, RED)
            if bounds:
                canvas = image.crop(bounds)
                if canvas.size == size:
                    return canvas, bounds[:2]
            return None

        until(lambda: events() == ["390"], "Canvas did not report the 10c width")
        command("xdotool", "windowfocus", window, env=env, check=True)
        if not stock:
            # The general runner starts on a 300-pixel surface. Enlarge its
            # guest window so it can allocate the full 390-pixel Canvas.
            def initial_surface():
                box = color_bounds(snapshot(), BACKGROUND)
                if box and (box[2]-box[0], box[3]-box[1]) == (300, 208):
                    return box
                return None

            _, surface_top, right, bottom = until(initial_surface, "Initial hosted surface did not paint")
            pointer(env, window, right-22, surface_top-9, "mousedown", "1", "sleep", "0.15", "mouseup", "1")
            x, y = right-3, bottom-4
            pointer(env, window, x, y, "sleep", "0.15", "mousedown", "1", "sleep", "0.15",
                    "mousemove", "--window", window, str(x+170), str(y+100), "sleep", "0.2", "mouseup", "1")
        before, (left, top) = until(lambda: capture((390, 60)), "Initial Canvas was not 390 by 60 pixels")
        assert color_bounds(before.crop((39, 25, 190, 39)), BLACK), "Canvas label is missing"
        pointer(env, window, left+45, top+30, "sleep", "0.06", "mousedown", "1", "sleep", "0.09", "mouseup", "1")
        until(lambda: events() == ["390", "50.2777"], "Text hit did not change the Canvas height to 36.2p")
        after, _ = until(lambda: capture((312, 50)), "Reconfigured Canvas was not 312 by 50 pixels")
        return before, after


def main():
    cli = argparse.ArgumentParser()
    cli.add_argument("--installed", action="store_true")
    args = cli.parse_args()
    BUILD.mkdir(parents=True, exist_ok=True)
    runner = ROOT / "dis/tcltk.zx" if args.installed else BUILD / "tcltk-distances.zx"
    if not args.installed:
        compile_image("tcltk", runner, *RUNNER_FLAGS)
    fixture = guest(SOURCES / "canvas_distance_window.tcl")
    with TemporaryDirectory(dir=BUILD) as scratch, private_display() as env:
        check_commands(env, Path(scratch), runner)
        stock = exercise(env, f"{{cat {fixture}; sleep 45}} | tkcmd", stock=True)
        hosted = exercise(env, f"zxrun -w {guest(runner)} < {fixture}", stock=False)
        for expected, actual in zip(stock, hosted, strict=True):
            delta = ImageChops.difference(expected, actual).getbbox()
            assert delta is None, ("Canvas screen-distance pixels differ from stock", delta)
    print("Stock and hosted Canvas matched all 39,000 pixels before and after pointer-driven reconfiguration")


if __name__ == "__main__":
    main()
