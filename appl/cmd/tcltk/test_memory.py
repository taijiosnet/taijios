"""Check the Ziran Memory Monitor graph, and its canvas commands against recorded Inferno tkcmd results.

memory_canvas_commands.expected was recorded from Inferno tkcmd. The Dis
Memory Monitor is removed; the hosted port is checked against the same
fixture records and geometry the Dis version passed.
"""

import argparse
from contextlib import contextmanager
import io
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory

from PIL import Image

from test_logwindow import private_display, read_output
from test_tcltk import BUILD, EMU, ROOT, SOURCES, command, compile_image, launch, stop, until, write_fixture


@contextmanager
def desktop(env, script):
    app = launch(env, EMU, "-r", ROOT, "-g", "800x600", "wm/wm", "/dis/sh.dis", "-c", script,
                 stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        yield app
    finally:
        stop(app)
        app.stdout.close()
        app.stderr.close()


def tkcmd_reference():
    lines = (SOURCES / "memory_canvas_commands.expected").read_text().splitlines()
    assert lines and lines[-1] == "#42" and not any(line.startswith("#!") for line in lines), lines
    return [line[1:] for line in lines]


def fixture(used, high):
    mib = 1024 * 1024
    return b"".join(
        ("".join(f"{field:11d} " for field in (size*mib, 32*mib, peak*mib, 90, 30, 1, 4096)) + f"{name}\n").encode()
        for name, size, peak in zip(("main", "heap", "image"), used, high)
    )


def save_snapshot(path, data):
    # The application keeps one descriptor open. Rewrite this fixed-size record in place.
    with path.open("r+b", buffering=0) as stream:
        assert stream.write(data) == len(data), "short memory fixture write"


def red_tracks(image):
    rows = []
    for y in range(30, 160):
        run = 0
        left = width = 0
        for x in range(0, 290):
            run = run + 1 if image.getpixel((x, y)) == (255, 0, 0) else 0
            if run > width:
                left, width = x - run + 1, run
        rows.append((y, left, width))

    tracks = []
    run = []
    for row in rows + [(0, 0, 0)]:
        if row[2] >= 8:
            run.append(row)
        elif run:
            if len(run) >= 3:
                tracks.append(run[len(run) // 2])
            run = []
    return tracks


def graph_geometry(image, tracks, used, peak):
    labels = []
    for (y, start, width), size, high in zip(tracks, used, peak, strict=True):
        black = (0, 0, 0)
        ends = [x for x in range(start + width, 290) if image.getpixel((x, y)) == black]
        assert len(ends) == 3 and ends[0] == start + width, (y, start, width, ends)
        left = start - 1
        span = ends[-1] - left
        assert abs(ends[0] - left - span * size // 32) <= 1, (y, span, size, ends)
        assert abs(ends[1] - left - span * high // 32) <= 1, (y, span, high, ends)
        name = image.crop((4, y-17, left-2, y-2))
        limit = image.crop((ends[-1]-44, y-17, ends[-1]+1, y-2))
        assert name.getcolors() and black in {color for _, color in name.getcolors()}, "missing arena name"
        assert limit.getcolors() and black in {color for _, color in limit.getcolors()}, "missing arena limit"
        labels.append(image.crop((left+1, y-17, left+42, y-2)).tobytes())
    return labels


def exercise(env, invocation, *, device_fixture, hosted=False):
    with TemporaryDirectory(dir=BUILD) as folder:
        memory = Path(folder) / "memory"
        if device_fixture:
            memory.write_bytes(fixture((8, 12, 16), (12, 16, 20)))
            invocation = f"bind -b /{Path(folder).relative_to(ROOT)} /dev; {invocation}"
        with desktop(env, invocation) as app:
            output = bytearray()
            window = until(lambda: command("xdotool", "search", "--onlyvisible", "--name", "^inferno$",
                                           env=env, text=True, capture_output=True).stdout.strip(),
                           "Memory emulator did not map")

            def capture():
                read_output(app, output)
                assert not any(line.startswith((b"memory:", b"zxrun:", b"arena ")) for line in output.splitlines()), output
                shot = command("import", "-window", window, "png:-", env=env, capture_output=True, check=True)
                return Image.open(io.BytesIO(shot.stdout)).convert("RGB")

            def graph(descending):
                image = capture()
                tracks = red_tracks(image)
                widths = [width for _, _, width in tracks]
                if len(widths) == 3 and len(set(widths)) == 3 and widths == sorted(widths, reverse=descending):
                    return image, tracks

            if not device_fixture:
                until(lambda: red_tracks(capture()), "Memory did not render live /dev/memory usage")
            else:
                initial_image, initial = until(lambda: graph(False), "Memory did not show three initial arena bars")
                labels = graph_geometry(initial_image, initial, (8, 12, 16), (12, 16, 20))
                save_snapshot(memory, fixture((16, 12, 8), (20, 16, 20)))
                final_image, final = until(lambda: graph(True), "Memory did not refresh changed /dev/memory records")
                refreshed = graph_geometry(final_image, final, (16, 12, 8), (20, 16, 20))
                assert labels[0] != refreshed[0] and labels[2] != refreshed[2], "size labels did not refresh"
                assert labels[1] == refreshed[1], "unchanged arena size label moved"

            close_x = 270 if hosted else 230
            command("xdotool", "mousemove", "--sync", "--window", window, str(close_x), "12",
                    "mousedown", "1", "sleep", "0.10", "mouseup", "1", env=env, check=True)
            until(lambda: capture().getpixel((4, 30)) == (119, 119, 119), "Memory window did not close")
            if hosted:
                def returned():
                    read_output(app, output)
                    return b"0" in output.splitlines()

                until(returned, "hosted Memory did not return cleanly")


def main():
    cli = argparse.ArgumentParser()
    cli.add_argument("--installed", action="store_true", help="exercise /dis/wm/memory.zx")
    args = cli.parse_args()
    BUILD.mkdir(parents=True, exist_ok=True)
    model = BUILD / "memory_model_test.zx"
    compile_image("memory_model_test", model)
    result = command("zi2zx", "run", "--backend", "engine", model, capture_output=True, text=True, check=True)
    assert result.stdout.splitlines() == [
        "Memory verified Inferno arena records, used and high-water bar widths, and count and size formatting", "0",
    ] and not result.stderr, result

    oracle = tkcmd_reference()
    commands = (SOURCES / "memory_canvas_commands.tcl").read_text()
    write_fixture("memory_canvas_fixture.zi", f"Commands :: #string CANVAS_END\n{commands}CANVAS_END;\n")
    canvas = BUILD / "memory_canvas_test.zx"
    compile_image("memory_canvas_test", canvas)
    portable = command("zi2zx", "run", "--backend", "engine", canvas, capture_output=True, text=True, check=True)
    assert portable.stdout.splitlines() == [*oracle, "0"] and not portable.stderr, portable
    print("Ziran Tk matched the recorded Inferno canvas creation, sizes, coordinates, bounds and item text")
    image = ROOT / "dis/wm/memory.zx" if args.installed else BUILD / "memory.zx"
    if not args.installed:
        compile_image("memory_app", image, "--module-path", ROOT / "appl/wm", "--bind-host", "zx_surface",
                      "--bind-host", "taijios_files", "--bind-host", "taijios_clock")
    invocation = f"zxrun -p -w /{image.relative_to(ROOT)}"
    with private_display() as env:
        exercise(env, invocation, device_fixture=True, hosted=True)
        exercise(env, invocation, device_fixture=False, hosted=True)
    print("Hosted Memory showed three usage bars, high-water marks, refreshed size labels and a clean close, "
          "and read the real /dev/memory device")


if __name__ == "__main__":
    main()
