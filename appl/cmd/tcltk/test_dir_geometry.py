"""Compare a wide icon label with the recorded Dis Directory Browser and exercise widening during Walk.

dir_long_label.json holds the label mask the Dis Directory Browser drew, recorded
before it was removed.
"""

import argparse
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from PIL import Image

from test_dir import BLACK, CANVAS_COLOR, FLAGS, Browser, desktop, glyphs, guest, mask_value
from test_logwindow import private_display, read_output
from test_menu import inferno_window
from test_tcltk import BUILD, EMU, SOURCES, command, compile_image, until

LONG_NAME = "n" * 55 + "é-file.txt"
WIDE_CANVAS = 530
STOCK_LABEL = SOURCES / "dir_long_label.json"


def wide_grid(capture):
    image = capture()
    color = bytes(CANVAS_COLOR)
    for y in range(43, 82):
        scan = image.crop((0, y, image.width, y+1)).tobytes()
        left = next((x for x in range(1, 24) if scan[3*x:3*x+3] == color), None)
        if left is None or scan[3*left:3*(left+WIDE_CANVAS)] != color*WIDE_CANVAS:
            continue
        right = left+WIDE_CANVAS
        if scan[3*right:3*right+3] == color:
            continue
        label = glyphs(image.crop((left, y+85, right, y+100)), BLACK)
        if label and label[0][0] >= 8*len(LONG_NAME)-8:
            return left, y, label
    return None


def startup(env, emulator, launch):
    with desktop(env, emulator, launch) as process:
        window = inferno_window(env)
        output = bytearray()

        def capture():
            read_output(process, output)
            assert not output, output
            png = command("import", "-window", window, "png:-", env=env,
                          capture_output=True, check=True).stdout
            return Image.open(io.BytesIO(png)).convert("RGB")

        return until(lambda: wide_grid(capture), "startup did not show the complete long label")[2]


def walk(env, emulator, launch, label):
    with desktop(env, emulator, launch) as process:
        browser = Browser(env, process, stock=False)
        original = until(browser.title, "Directory Browser did not draw its title")
        browser.walk()
        browser.double_at(*browser.tile_center(1))
        left, top, actual = until(lambda: wide_grid(browser.capture), "Walk did not widen the open window")
        assert actual == label, "Walk clipped or changed the long label"
        assert (left, top) == browser.canvas, "Walk moved the window"
        until(lambda: browser.title() not in (None, original), "Walk did not change the current directory")
        browser.double_at(left + (len(LONG_NAME) + 2) * 4, top + 20)
        until(lambda: browser.title() == original, "Walk did not return through '..'")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--installed", action="store_true")
    parser.add_argument("--emulator", type=Path, default=EMU)
    parser.add_argument("--launcher", default="zxrun")
    args = parser.parse_args()
    BUILD.mkdir(parents=True, exist_ok=True)
    image = BUILD / "dir.zx"
    if not args.installed:
        compile_image("dir_app", image, *FLAGS)
    with TemporaryDirectory(prefix="d", dir=BUILD) as name, private_display() as env:
        directory = Path(name)
        child = directory / "child"
        child.mkdir()
        (child / LONG_NAME).touch()
        (directory / "zzzzzzzzzzzz").touch()
        expected = mask_value(json.loads(STOCK_LABEL.read_text()))
        path = "/dis/wm/dir.zx" if args.installed else guest(image)
        launcher = f"{args.launcher} -w {path}"
        actual = startup(env, args.emulator, f"{launcher} {guest(child)}")
        assert actual == expected, "the Ziran long label pixels differ from the recorded Dis label"
        print(f"Ziran draws the full {len(LONG_NAME)}-rune label on a {WIDE_CANVAS}-pixel Canvas as Dis did")
        walk(env, args.emulator, f"{launcher} {guest(directory)}", expected)
        print("Ziran widens during Walk and the same window can return through '..'")


if __name__ == "__main__":
    main()
