"""Compare Canvas scrolling with stock Inferno Tk on a private desktop."""
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
from test_tcltk import BUILD, ROOT, RUNNER_FLAGS, SOURCES, color_bounds, command, compile_image, until

RED = (255, 0, 0)


def check_commands(env, folder, runner):
    fixture = SOURCES / "canvas_viewport_commands.tcl"
    stock = transcript(env, f"tkcmd < {guest(fixture)}")
    diagnostics = [line for line in stock if line.startswith(b"tk: yscrollcommand ")]
    assert len(diagnostics) == 2, stock
    expected = [line for line in stock if line not in diagnostics]
    assert all(line.startswith(b"#") for line in expected), expected
    hosted_script = folder / "commands.tcl"
    hosted_script.write_text("".join(
        f"set answer [{line}]\nif {{[string length $answer]}} {{puts $answer}}\n"
        for line in fixture.read_text().splitlines()
    ) + "destroy .\n")
    hosted = transcript(env, f"zxrun -w {guest(runner)} < {guest(hosted_script)}")
    results = [*(line[1:] for line in expected), b"0"]
    for number, (want, got) in enumerate(zip_longest(results, hosted), 1):
        assert want == got, (number, want, got)
    print(f"Hosted runner matched {len(expected)} stock Canvas results, including callback and query fractions")


def exercise(env, invocation, *, stock):
    with desktop(env, invocation) as app:
        window = inferno_window(env)
        output = bytearray()

        def events():
            read_output(app, output)
            lines = output.decode().splitlines()
            assert not any(line.startswith(("#!", "tcltk:", "tk: ")) for line in lines), lines
            return [line for line in lines if not line.startswith("#")] if stock else lines

        def canvas_pixels():
            png = command("import", "-window", window, "png:-", env=env, check=True, capture_output=True).stdout
            image = Image.open(io.BytesIO(png)).convert("RGB")
            bounds = color_bounds(image, RED)
            if bounds and (bounds[2]-bounds[0], bounds[3]-bounds[1]) == (120, 80):
                return image.crop(bounds), bounds
            return None

        def click(x, y, button="1"):
            pointer(env, window, x, y, "sleep", "0.06", "mousedown", button, "sleep", "0.09", "mouseup", button, "sleep", "0.12")

        def after_events(count, message):
            def complete():
                lines = events()
                return lines if len(lines) >= count else None
            return until(complete, message)

        until(lambda: events() == ["ready"], "Canvas viewport fixture did not initialize")
        initial, (left, top, right, bottom) = until(canvas_pixels, "Canvas viewport did not paint")
        blank = Image.new("RGB", initial.size, RED)
        icon = ImageChops.difference(initial, blank).getbbox()
        assert icon is not None and icon[0] >= 25 and icon[1] >= 67 and icon[3] == 80, icon
        command("xdotool", "windowfocus", window, env=env, check=True)

        click(left+30, top+75)
        before = after_events(8, "Canvas item did not receive its first press")
        assert before[:-1] == ["ready", "item 30 75", "75", "0 0.2", "0 0.2", "80", "120"], before
        scrollbar_width = int(before[-1])
        assert scrollbar_width > 0, before
        arrow = right + 2 + (scrollbar_width + (2 if stock else 0))//2

        for step in range(1, 4):
            click(arrow, bottom-3)

            def advanced():
                snapshot = canvas_pixels()
                if snapshot is not None:
                    image, bounds = snapshot
                    delta = ImageChops.difference(image, blank).getbbox()
                    if delta and delta[1] == max(0, icon[1]-25*step):
                        assert bounds == (left, top, right, bottom), bounds
                        return image
                return None
            scrolled = until(advanced, f"Scrollbar arrow {step} did not scroll by 25 pixels")

        click(left+30, top+7)
        after = after_events(15, "Translated Canvas item did not receive the press")
        moved = ["item 30 7", "82", "0.1875 0.3875", "0.1875 0.3875", "80", "120", str(scrollbar_width)]
        assert after == before + moved, after

        click(left+30, top+7, "3")
        assert after_events(16, "Canvas increment did not reset") == after + ["fallback increment"]
        click(arrow, bottom-3)

        clipped_bottom = ImageChops.difference(scrolled, blank).getbbox()[3]

        def fallback():
            snapshot = canvas_pixels()
            if snapshot is not None:
                image = snapshot[0]
                box = ImageChops.difference(image, blank).getbbox()
                if box and box[3] == clipped_bottom-8:
                    return image
            return None

        pixels = until(fallback, "Scrollbar arrow did not use one tenth of the viewport")
        click(arrow, top+57)

        def paged():
            snapshot = canvas_pixels()
            if snapshot is not None:
                image = snapshot[0]
                box = ImageChops.difference(image, blank).getbbox()
                # The second icon starts at world (90, 168). The origin is now (10, 155).
                if box and box[0] >= 80 and box[1] == 13 + icon[1]-67:
                    return image
            return None

        page = until(paged, "Scrollbar trough did not scroll by 90% of the viewport")
        click(left+30, top+7)
        assert events() == after + ["fallback increment"], "An offscreen item received a press"
        return (initial, scrolled, pixels, page), scrollbar_width


def main():
    cli = argparse.ArgumentParser()
    cli.add_argument("--installed", action="store_true")
    args = cli.parse_args()
    BUILD.mkdir(parents=True, exist_ok=True)
    runner = ROOT / "dis/tcltk.zx" if args.installed else BUILD / "tcltk-viewport.zx"
    if not args.installed:
        compile_image("tcltk", runner, *RUNNER_FLAGS)
    fixture = guest(SOURCES / "canvas_viewport_window.tcl")
    with TemporaryDirectory(dir=BUILD) as scratch, private_display() as env:
        folder = Path(scratch)
        check_commands(env, folder, runner)
        stock, stock_width = exercise(env, f"{{cat {fixture}; sleep 45}} | tkcmd", stock=True)
        hosted, hosted_width = exercise(env, f"zxrun -w {guest(runner)} < {fixture}", stock=False)
        for expected, actual in zip(stock, hosted, strict=True):
            assert not ImageChops.difference(expected, actual).getbbox(), "Canvas viewport pixels differ from stock"
    print("Stock and hosted Canvas matched 38,400 pixels, translated item coordinates, and scrollbar unit and page presses")
    print(f"Allocated scrollbar widths were {stock_width} and {hosted_width} pixels")


if __name__ == "__main__":
    main()
