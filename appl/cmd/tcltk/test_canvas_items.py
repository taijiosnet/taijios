"""Compare Canvas item commands and pointer events with Inferno tkcmd."""

import argparse
import io
import time
from pathlib import Path
from tempfile import TemporaryDirectory

from PIL import Image
from test_about import transcript
from test_logwindow import private_display, read_output
from test_memory import desktop
from test_menu import inferno_window, pointer
from test_tcltk import BUILD, ROOT, RUNNER_FLAGS, SOURCES, color_bounds, command, compile_image, until, write_fixture


def check_commands(env):
    fixture = SOURCES / "canvas_item_commands.tcl"
    stock = transcript(env, f"tkcmd < /{fixture.relative_to(ROOT)}")
    assert stock[-1] == b"#END" and all(line.startswith(b"#") for line in stock), stock
    write_fixture("canvas_item_fixture.zi", f"Commands :: #string CANVAS_END\n{fixture.read_text()}CANVAS_END;\n")
    model = BUILD / "canvas_item_command_test.zx"
    compile_image("canvas_item_command_test", model)
    hosted = command("zi2zx", "run", "--backend", "engine", model, capture_output=True, check=True)
    expected = [*(line[1:] for line in stock), b"0"]
    assert hosted.stdout.splitlines() == expected and not hosted.stderr, (expected, hosted)
    print(f"Ziran matched all {len(stock)} stock Canvas command results")


def exercise(env, invocation, *, stock):
    with desktop(env, invocation) as app:
        window = inferno_window(env)
        output = bytearray()

        def capture():
            png = command("import", "-window", window, "png:-", env=env, check=True, capture_output=True).stdout
            return Image.open(io.BytesIO(png)).convert("RGB")

        def events():
            read_output(app, output)
            lines = output.decode().splitlines()
            assert not any(line.startswith("#!") or line.startswith("tcltk:") for line in lines), lines
            if stock:
                messages = (line.removeprefix("#<stdout>") for line in lines if line.startswith("#<stdout>"))
                return [line.removeprefix("{").removesuffix("}") for line in messages]
            return lines

        try:
            until(lambda: events() == ["ready"], "Canvas fixture did not initialize")
            left, top, _, _ = until(lambda: color_bounds(capture(), (255, 0, 0)), "red item did not paint")
            base = left+18, top+18
            overlap = left+65, top+45
            blue = (0, 0, 204) if stock else (0, 0, 255)
            red = (255, 0, 0)
            assert capture().getpixel(overlap) == blue, "blue item did not cover red item"
            expected = ["ready"]

            def expect(*lines):
                expected.extend(lines)
                until(lambda: events() == expected, f"expected {expected}", timeout=4)

            command("xdotool", "windowfocus", window, env=env, check=True)
            pointer(env, window, *base, "mousedown", "3", "sleep", "0.12", "mouseup", "3")
            expect("enter base 0", "all right 3 30 30 .c %", "group right 3", "base right 3")
            pointer(env, window, *overlap)
            expect("leave base 0", "enter top 0")

            time.sleep(0.35)
            pointer(env, window, *overlap, "mousedown", "3")
            expect("all right 3 77 57 .c %", "group right 3", "top right 3")
            pointer(env, window, overlap[0]+7, overlap[1]+5, "sleep", "0.15", "mouseup", "3")
            assert events() == expected, "empty held-motion bindings did not suppress press callbacks"

            pointer(env, window, *overlap, "mousedown", "1", "sleep", "0.08", "mouseup", "1",
                    "sleep", "0.08", "mousedown", "1", "sleep", "0.08", "mouseup", "1")
            expect("top single 1", "top release 1", "top double 1", "top release 1")
            time.sleep(0.35)
            pointer(env, window, *overlap, "mousedown", "1")
            expect("top single 1")
            pointer(env, window, *overlap, "mouseup", "1")
            expect("top release 1")

            pointer(env, window, *overlap, "mousedown", "2")
            expect("delete top 2")
            until(lambda: capture().getpixel(overlap) == red, "deleted item still painted over the lower item")
            pointer(env, window, *overlap, "mouseup", "2")
            pointer(env, window, overlap[0]+2, overlap[1]+2)
            expect("enter base 0")
            pointer(env, window, *overlap, "mousedown", "2")
            pointer(env, window, overlap[0]+6, overlap[1]+6)
            expect("base drag 2")
            # Release at the current position without injecting a second drag sample.
            command("xdotool", "mouseup", "2", env=env, check=True)
            pointer(env, window, *overlap, "mousedown", "3", "sleep", "0.12", "mouseup", "3")
            expect("all right 3 77 57 .c %", "group right 3", "base right 3")
            pointer(env, window, left+9, top+100, "mousedown", "2")
            expect("leave base 0", "text 2")
            command("xdotool", "mouseup", "2", env=env, check=True)
            return events()
        except AssertionError as failure:
            raise AssertionError(f"{failure}: {output!r}") from failure


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--installed", action="store_true")
    args = parser.parse_args()
    BUILD.mkdir(parents=True, exist_ok=True)
    image = (ROOT / "dis" if args.installed else BUILD) / "tcltk.zx"
    if not args.installed:
        compile_image("tcltk", image, *RUNNER_FLAGS)
    template = (SOURCES / "canvas_item_window.tcl").read_text()
    with TemporaryDirectory(dir=BUILD) as folder, private_display() as env:
        check_commands(env)
        stock_script = Path(folder) / "stock.tcl"
        stock_script.write_text(template.replace("EMIT ", "send stdout "))
        stock = exercise(env, f"{{cat /{stock_script.relative_to(ROOT)}; sleep 45}} | tkcmd", stock=True)
        native_script = Path(folder) / "native.tcl"
        native_script.write_text(template.replace("EMIT ", "puts "))
        hosted = exercise(env, f"zxrun -w /{image.relative_to(ROOT)} < /{native_script.relative_to(ROOT)}", stock=False)
        assert hosted == stock
    print(f"Stock and hosted Canvas matched {len(stock)-1} pointer callbacks and the pixels after deletion")


if __name__ == "__main__":
    main()
