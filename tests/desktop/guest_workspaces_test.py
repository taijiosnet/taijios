#!/usr/bin/env python3
"""Exercise the Rill pager and real guest windows on an owned 128 MiB display."""
import argparse
import csv
from contextlib import suppress
import io
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory

from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "appl/cmd/tcltk"))
from test_logwindow import private_display
from test_tcltk import launch, stop, until

WIDTH = 1024
HEIGHT = 768
CRIMSON = (238, 17, 51)
COBALT = (17, 68, 238)
PROBE = (250, 215)
FAR_PROBE = (700, 400)


def exercise(env, emulator, staging, guest, log):
    command = (f"home={guest}/home; bind -b {guest} /zx; bind -b {guest} /zx/wm; "
               f"bind -b {guest} /lib; wm/wm -rill {guest}/rill.zx")
    child = launch(env, emulator, "-p", "main=128M", "-r", ROOT,
                   "-g", f"{WIDTH}x{HEIGHT}", "/zx/sh.dis", "-c", command,
                   stdin=subprocess.DEVNULL, stdout=log, stderr=log)

    def tail():
        size = os.fstat(log.fileno()).st_size
        return os.pread(log.fileno(), 16384, max(0, size - 16384)).decode(errors="replace")

    def query(*args, check=True):
        return subprocess.run(args, env=env, check=check, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, timeout=10).stdout

    window = None

    def frame():
        return Image.open(io.BytesIO(query("import", "-window", window, "png:-"))).convert("RGB")

    def click(point, button=1):
        query("xdotool", "mousemove", "--window", window, *map(str, point),
              "sleep", ".06", "mousedown", str(button), "sleep", ".12", "mouseup", str(button))

    def key(chord):
        query("xdotool", "key", "--delay", "90", chord)

    def color(expected, point=PROBE):
        until(lambda: frame().getpixel(point) == expected, f"expected {expected} at {point}", timeout=15)

    def empty(point=PROBE):
        until(lambda: frame().getpixel(point) not in (CRIMSON, COBALT),
              f"a window stayed visible at {point}")

    def words(box, crop=None):
        image = frame()
        scale = 1
        left = top = 0
        if crop is not None:
            left, top, right, bottom = crop
            scale = 3
            image = ImageOps.grayscale(image.crop(crop)).resize(
                ((right - left) * scale, (bottom - top) * scale))
            image = image.point(lambda value: 255 if value < 100 else 0)
        packed = io.BytesIO()
        image.save(packed, format="PNG")
        result = subprocess.run(["tesseract", "stdin", "stdout", "--psm", "11", "tsv"],
                                input=packed.getvalue(), env=env, check=True,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=6)
        rows = csv.DictReader(io.StringIO(result.stdout.decode()), delimiter="\t", quoting=csv.QUOTE_NONE)
        found = []
        for row in rows:
            if row["text"].strip():
                x = left + (int(row["left"]) + int(row["width"]) // 2) // scale
                y = top + (int(row["top"]) + int(row["height"]) // 2) // scale
                if box[0] <= x < box[2] and box[1] <= y < box[3]:
                    found.append((row["text"].upper(), (x, y)))
        return found

    panel = (0, 0, WIDTH, 40)
    pager_strip = (430, 0, 620, 40)
    tasks = (95, 0, 450, 40)

    def task(expected, excluded=None):
        def found():
            labels = dict(words(tasks, crop=panel))
            if expected is None:
                return excluded not in labels
            return labels.get(expected) if excluded not in labels else None
        return until(found, f"task list expected {expected}, excluded {excluded}")

    def pager(index):
        def buttons():
            items = sorted((int(text), xy) for text, xy in words(pager_strip, crop=panel)
                           if text in ("1", "2", "3", "4"))
            for cell, (x, y) in items:
                for next_cell, (next_x, next_y) in items:
                    if next_cell == cell + 1 and 28 <= next_x - x <= 34 and abs(y - next_y) <= 3:
                        return x + (index + 1 - cell) * (next_x - x), y
            return None
        click(until(buttons, "the Rill pager buttons did not paint"))

    def task_action(title, verb):
        click(task(title), 3)
        menu = (90, 25, 470, 265)
        point = until(lambda: dict(words(menu)).get(verb) or dict(words(menu, crop=menu)).get(verb),
                      f"{verb} missing from Rill task context menu")
        click(point)

    def routed(title, letter):
        key(letter)
        until(lambda: f"WORKSPACE_KEY {title} {ord(letter)}\n" in tail(),
              f"key {letter} did not reach restored focus {title}")
        names = re.findall(fr"WORKSPACE_KEY (\w+) {ord(letter)}\n", tail())
        assert names == [title], names

    try:
        def find_window():
            matches = query("xdotool", "search", "--pid", str(child.pid), "--onlyvisible", "--name", "^inferno$",
                            check=False).decode().splitlines()
            # This Xvfb contains only the emulator launched by the test.
            return matches or query("xdotool", "search", "--onlyvisible", "--name", "^inferno$",
                                    check=False).decode().splitlines()

        window = until(find_window, "TaijiOS test window missing")[0]
        query("xdotool", "windowfocus", window)
        color(CRIMSON)
        task("CRIMSON", "COBALT")
        pager(1)
        empty()
        task(None, "CRIMSON")
        click(PROBE)
        key("q")
        assert "WORKSPACE_POINTER CRIMSON" not in tail(), tail()
        assert "WORKSPACE_KEY CRIMSON 113\n" not in tail(), tail()
        (staging / "open-second").touch()
        color(COBALT)
        task("COBALT", "CRIMSON")
        routed("COBALT", "b")

        key("ctrl+alt+Left")
        color(CRIMSON)
        task("CRIMSON", "COBALT")
        routed("CRIMSON", "a")
        assert not re.search(r"WORKSPACE_KEY \w+ (15|20|21)\n", tail()), tail()

        task_action("CRIMSON", "MAXIMIZE")
        color(CRIMSON, FAR_PROBE)
        pager(1)
        color(COBALT)
        empty(FAR_PROBE)
        pager(0)
        color(CRIMSON, FAR_PROBE)
        routed("CRIMSON", "c")
        task_action("CRIMSON", "RESTORE")
        empty(FAR_PROBE)
        color(CRIMSON)

        click(PROBE)
        routed("CRIMSON", "d")
        key("ctrl+alt+shift+Right")
        empty()
        task(None, "CRIMSON")
        key("alt+ctrl+Right")
        color(COBALT)
        task("CRIMSON")
        task("COBALT")
        routed("COBALT", "e")

        click(task("CRIMSON"))
        color(CRIMSON)
        task_action("CRIMSON", "MINIMIZE")
        color(COBALT)
        pager(0)
        empty()
        pager(1)
        color(COBALT)
        click(task("CRIMSON"))
        color(CRIMSON)
        routed("CRIMSON", "f")
        task("COBALT")
        assert not re.search(r"WORKSPACE_KEY \w+ (15|20|21|113)\n", tail()), tail()
        print("128 MiB guest workspace lifecycle passed")
    except Exception:
        if window is not None:
            with suppress(OSError, subprocess.SubprocessError):
                frame().save(staging.parent / "failure.png")
        print(tail(), file=sys.stderr)
        raise
    finally:
        stop(child)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--emulator", type=Path, required=True)
    parser.add_argument("--overlay", type=Path, required=True,
                        help="directory with wm.dis, toolbar.dis, zxrun.dis and workspace_window.dis")
    parser.add_argument("--rill", type=Path, required=True)
    args = parser.parse_args()
    overlay = args.overlay.resolve()
    with TemporaryDirectory(dir=overlay, prefix="guest-") as temporary:
        staging = Path(temporary)
        guest = "/" + staging.relative_to(ROOT).as_posix()
        for file in ("wm.dis", "toolbar.dis", "zxrun.dis", "workspace_window.dis"):
            shutil.copyfile(overlay / file, staging / file)
        shutil.copyfile(args.rill, staging / "rill.zx")
        (staging / "home").mkdir()
        (staging / "wmsetup").write_text(
            "load std\nmenu 'Workspace test' {echo 'Workspace test'}\n"
            "workspace_window CRIMSON &\n"
            f"while {{! {{ftest -f {guest}/open-second}}}} {{sleep 1}}\n"
            "workspace_window COBALT &\n")
        for key in ("WAYLAND_SOCKET", "SESSION_MANAGER", "ICEAUTHORITY", "XDG_RUNTIME_DIR"):
            os.environ.pop(key, None)
        with private_display() as env, (staging / "guest.log").open("w+b") as log:
            env["HOME"] = str(staging / "home")
            exercise(env, args.emulator.resolve(), staging, guest, log)


if __name__ == "__main__":
    main()
