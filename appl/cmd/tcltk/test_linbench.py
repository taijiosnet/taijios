"""Compare Inferno Tk listbox commands and exercise the real LINPACK windows."""

import argparse
from dataclasses import dataclass
import io

from PIL import Image

from test_logwindow import private_display, read_output
from test_memory import desktop
from test_tcltk import BUILD, ROOT, SOURCES, command, compile_image, until, write_fixture


FIXTURE = SOURCES / "linbench_listbox_commands.tcl"
LISTBOX = ("--define", "TK_LISTBOX")
LINBENCH = (*LISTBOX, "--define", "TK_NO_CANVAS")


@dataclass(frozen=True)
class Window:
    run: tuple
    entry: tuple
    list_box: tuple
    ink: tuple
    scrollbar: int
    close: int


STOCK = Window((14, 32), (70, 32), (22, 43, 291, 192), (0, 0, 0), 8, 294)
HOSTED = Window((52, 63), (120, 62), (46, 104, 451, 250), (25, 47, 67), 30, 474)


def model_results():
    write_fixture(
        "linbench_listbox_input.zi",
        "Script :: #string LISTBOX_END\n" + FIXTURE.read_text() + "LISTBOX_END;\n"
    )
    model = BUILD / "linbench_model_test.zx"
    compile_image("linbench_model_test", model, *LINBENCH)
    run = command("zi2zx", "run", "--backend", "engine", model, capture_output=True, text=True, check=True)
    lines = run.stdout.splitlines()
    assert lines[-2:] == ["LINPACK solver and listbox input verified", "0"] and not run.stderr, (lines, run.stderr)
    return lines[:-2]


def oracle(env, expected):
    fixture = FIXTURE.relative_to(ROOT)
    with desktop(env, f"tkcmd < /{fixture}") as app:
        output = bytearray()

        def compare():
            read_output(app, output)
            lines = output.decode().splitlines()
            assert lines == expected[:len(lines)] or not output.endswith(b"\n"), lines
            return lines == expected

        until(compare, "Inferno tkcmd listbox transcript was incomplete")
    print(f"Inferno tkcmd and Ziran matched {len(expected)} listbox results")


def runner(env, image):
    fixture = BUILD / "linbench_generic.tcl"
    fixture.write_text("listbox .rows\n.rows insert end {first result} second\nputs [.rows get 0]\ndestroy .\n")
    with desktop(env, f"zxrun -w /{image.relative_to(ROOT)} < /{fixture.relative_to(ROOT)}") as app:
        output = bytearray()

        def finished():
            read_output(app, output)
            assert b"tcltk:" not in output, output
            return b"first result" in output.splitlines()

        until(finished, "generic Tk runner did not execute listbox commands from stdin")


def row_bands(image, geometry):
    left, top, right, bottom = geometry.list_box
    rows = []
    for y in range(top, bottom):
        if sum(image.getpixel((x, y)) == geometry.ink for x in range(left, right)) < 5:
            continue
        if rows and y - rows[-1][1] < 4:
            rows[-1] = (rows[-1][0], y)
        else:
            rows.append((y, y))
    return rows


def exercise(env, invocation, *, hosted):
    geometry = HOSTED if hosted else STOCK
    with desktop(env, invocation) as app:
        output = bytearray()
        win = until(lambda: command("xdotool", "search", "--onlyvisible", "--name", "^inferno$",
                                    env=env, text=True, capture_output=True).stdout.strip(), "emulator did not map")

        def capture():
            read_output(app, output)
            assert not any(line.startswith((b"tcltk:", b"linbench:", b"zxrun:", b"arena ", b"LINPACK residual"))
                           for line in output.splitlines()), output
            result = command("import", "-window", win, "png:-", env=env, capture_output=True, check=True)
            return Image.open(io.BytesIO(result.stdout)).convert("RGB")

        def mouse(x, y, *action):
            command("xdotool", "mousemove", "--window", win, str(x), str(y), *action, env=env, check=True)

        def click(x, y):
            mouse(x, y, "mousedown", "1", "sleep", "0.11", "mouseup", "1")

        def order(value):
            click(*geometry.entry)
            command("xdotool", "key", "End", "BackSpace", "BackSpace", "BackSpace", env=env, check=True)
            command("xdotool", "type", value, env=env, check=True)

        def running(image):
            return image.getpixel((100, 47)) == (224, 234, 242)

        def thumb(image):
            left = geometry.scrollbar - 2
            return image.crop((left, top+17, left+5, bottom-17)).tobytes()

        def rows(count, previous_thumb=None):
            def displayed():
                image = capture()
                if hosted and running(image):
                    return None
                if previous_thumb is not None and thumb(image) == previous_thumb:
                    return None
                bands = row_bands(image, geometry)
                return (image, bands) if len(bands) >= count else None

            return until(displayed, f"LINPACK did not display {count} results", timeout=30)

        left, top, right, bottom = geometry.list_box
        empty_color = (255, 255, 255) if hosted else (221, 221, 221)
        until(lambda: capture().getpixel((right - 5, top+8)) == empty_color, "LINPACK window did not load")
        click(*geometry.run)
        original, first_bands = rows(1)
        first_y = sum(first_bands[0]) // 2
        first_text = original.crop((left, first_bands[0][0], right, first_bands[0][1]+1)).tobytes()
        assert first_bands[0][1] - first_bands[0][0] >= 8, "default benchmark result did not render"

        if hosted:
            order("0")
            click(*geometry.run)
            rows(2)
            order("320")
            click(*geometry.run)
            until(lambda: running(capture()), "LINPACK did not start the order 320 run")
            rows(3)
            added = 3
        else:
            added = 1

        order("32")
        # Fill beyond the viewport and force the app to follow the newest results.
        visible = 7 if hosted else 8
        at_tail = capture()
        for index in range(added+1, visible+5):
            # Once the viewport fills, a row count alone can match the previous frame.
            previous_thumb = thumb(at_tail) if index > visible else None
            click(*geometry.run)
            at_tail, _ = rows(min(index, visible), previous_thumb)

        assert at_tail.crop((left, first_bands[0][0], right, first_bands[0][1]+1)).tobytes() != first_text
        click(geometry.scrollbar, top+5)
        until(lambda: thumb(capture()) != thumb(at_tail), "scrollbar did not move by a row")
        thumb_y = bottom-39
        mouse(geometry.scrollbar, thumb_y, "mousedown", "1", "sleep", "0.1", "mousemove", "--window", win,
              str(geometry.scrollbar), str(top+22), "sleep", "0.1", "mouseup", "1")
        until(lambda: capture().crop((left, first_bands[0][0], right, first_bands[0][1]+1)).tobytes() == first_text,
              "scrollbar drag did not return to the first result")
        click(right-15, first_y)
        until(lambda: capture().getpixel((right-15, first_y)) != empty_color, "result row did not select")

        click(geometry.close, 12)
        until(lambda: capture().getpixel((35, 36)) == (119, 119, 119), "LINPACK window did not close")
        if hosted:
            def returned():
                read_output(app, output)
                return b"0" in output.splitlines()

            until(returned, "hosted LINPACK did not return cleanly")
    print(f"{'Hosted ZX' if hosted else 'Inferno Dis'} LINPACK ran, followed new results, scrolled, selected, and closed")


def main():
    cli = argparse.ArgumentParser()
    cli.add_argument("--installed", action="store_true", help="exercise /dis/math/linbench.zx and /dis/tcltk.zx")
    args = cli.parse_args()
    BUILD.mkdir(parents=True, exist_ok=True)
    expected = model_results()
    image = ROOT / "dis/math/linbench.zx" if args.installed else BUILD / "linbench.zx"
    generic = ROOT / "dis/tcltk.zx" if args.installed else BUILD / "tcltk.zx"
    if not args.installed:
        compile_image("linbench_app", image, *LINBENCH, "--module-path", ROOT / "appl/wm", "--bind-host", "zx_surface",
                      "--bind-host", "taijios_files", "--bind-host", "taijios_clock")
        compile_image("tcltk", generic, *LISTBOX, "--bind-host", "zx_surface", "--bind-host", "taijios_stdin")
    with private_display() as env:
        oracle(env, expected)
        runner(env, generic)
        exercise(env, "/dis/math/linbench.dis", hosted=False)
        exercise(env, f"zxrun -p -w /{image.relative_to(ROOT)}", hosted=True)


if __name__ == "__main__":
    main()
