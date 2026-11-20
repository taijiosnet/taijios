"""Exercise Directory Browser file actions and launch an actual native ZX application."""

import argparse
import io
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory

from PIL import Image

from test_dir import BLACK, FLAGS, SELECTED, Browser, desktop, glyphs, guest
from test_logwindow import private_display
from test_menu import inferno_window
from test_tcltk import BUILD, EMU, ROOT, command, compile_image, until

DOCUMENT = "paper é.txt"
PICTURE = "sample.bit"
MODULE = "start.dis"
NATIVE_IMAGE = "trace é.zx"
MARKER = "Taiji opened this fixture safely."
WHITE = (255, 255, 255)
ABOUT_ORANGE = (255, 85, 0)


def fixture(root):
    directory = root / "files"
    child = directory / "child"
    child.mkdir(parents=True)
    (child / "inside").touch()
    (directory / DOCUMENT).write_text(MARKER + "\n")
    shutil.copyfile(ROOT / "icons/tk/file.bit", directory / PICTURE)
    shutil.copyfile(ROOT / "dis/wm/about.dis", directory / MODULE)
    (root / "chan").mkdir()
    return directory, root / "chan/plumb.input"


def title_band(image):
    """Locate a focused guest title by the rows of its blue background."""
    color = bytes(SELECTED)
    regions = []
    for y in range(image.height):
        strip = image.crop((0, y, image.width, y + 1)).tobytes()
        if strip.count(color) < 30:
            continue
        pixels = [x // 3 for x in range(0, len(strip), 3) if strip[x:x+3] == color]
        if len(pixels) < 30:
            continue
        left, right = pixels[0], pixels[-1] + 1
        if regions and regions[-1][3] == y:
            prev = regions[-1]
            regions[-1] = (min(left, prev[0]), prev[1], max(right, prev[2]), y+1)
        else:
            regions.append((left, y, right, y+1))
    # A selected icon label can share the same blue, but is shorter than the title bar.
    regions = [box for box in regions if box[3]-box[1] >= 12]
    if not regions:
        return None
    return max(regions, key=lambda box: (box[3]-box[1], box[1], box[0]))


def focused_window(browser, previous=None):
    image = browser.capture()
    band = title_band(image)
    if band:
        left, top, right, _ = band
        # Exclude the window menu and the controls at the right edge.
        text = image.crop((left+27, top+3, min(left+345, right-24), top+19))
        title = glyphs(text, WHITE)
        if title and title != previous:
            return image, band, title
    return None


def begin_action(browser, index):
    previous = until(lambda: focused_window(browser), "Directory Browser did not receive focus")[2]
    browser.double_at(*browser.tile_center(index))
    return previous


def open_folder(browser):
    original = begin_action(browser, 1)
    _, (_, top, right, _), child = until(lambda: focused_window(browser, original),
                                      "Walk off did not open a child Directory Browser")
    browser.click(right-9, top+10)

    def parent_visible():
        current = focused_window(browser)
        return current and current[2] == original

    until(parent_visible, "closing the child did not reveal the original browser")
    return child


def capture_file(browser, index):
    previous = begin_action(browser, index)

    def rendered():
        window = focused_window(browser, previous)
        if window:
            image, (left, top, right, bottom), title = window
            if index == 2:
                # The editor's first line begins under the menu row.
                box = (left+10, top+40, left+278, top+59)
            else:
                center = (left+right)//2
                box = (center-19, bottom, center+19, bottom+30)
            ink = glyphs(image.crop(box), BLACK)
            if ink:
                return title, ink
        return None

    return until(rendered, "the launched window did not render the fixture")


def about_content(image):
    return glyphs(image, ABOUT_ORANGE)


def direct_about(env, emulator, invocation="wm/about"):
    with desktop(env, emulator, invocation):
        window = inferno_window(env)

        def content():
            png = command("import", "-window", window, "png:-", env=env,
                          capture_output=True, check=True).stdout
            return about_content(Image.open(io.BytesIO(png)).convert("RGB"))

        return until(content, "standalone About Inferno did not render its logo")


def run_actions(env, emulator, launch_browser, directory, sink, *, stock):
    def start(setup=""):
        return desktop(env, emulator, setup + f"{launch_browser} {guest(directory)}")

    with start() as process:
        folder = open_folder(Browser(env, process, stock=stock))
    with start() as process:
        editor = capture_file(Browser(env, process, stock=stock), 2)
    with start() as process:
        picture = capture_file(Browser(env, process, stock=stock), 3)
    with start() as process:
        browser = Browser(env, process, stock=stock)
        previous = begin_action(browser, 4)
        if stock:
            # Stock presents a load-error dialog because it appends '/' to the module name.
            until(lambda: focused_window(browser, previous), "stock did not show its Dis load dialog")
            module = None
        else:
            module = until(lambda: about_content(browser.capture()), "the Dis file did not open About Inferno")
    sink.write_bytes(b"")
    with start(f"bind -b {guest(sink.parent)} /chan; ") as process:
        browser = Browser(env, process, stock=stock)
        browser.pointer(*browser.tile_center(2), "mousedown", "3", "sleep", "0.12", "mouseup", "3")
        message = until(sink.read_bytes, "right-click sent no message to the guest plumber")
        data = DOCUMENT.encode()
        expected = f"WmDir\n\n{guest(directory)}/\ntext\n\n{len(data)}\n".encode() + data
        assert message == expected, (message, expected)
    return folder, editor, picture, module


def open_native_image(browser):
    dis_index = 4
    zx_index = 5
    image = browser.capture()

    def icon(index):
        x, y = browser.tile_center(index)
        return image.crop((x-14, y-14, x+14, y+14))

    original_icon = icon(dis_index)
    assert len(original_icon.getcolors()) > 1, "the Dis executable icon was blank"
    assert icon(zx_index).tobytes() == original_icon.tobytes(), "the ZX image did not use the executable icon"
    browser.mode(False)
    image = browser.capture()

    def kind(index):
        x = browser.canvas[0] + 10
        y = browser.first + 15 * index
        return glyphs(image.crop((x, y, x+32, y+13)), BLACK)

    assert kind(dis_index) and kind(zx_index) == kind(dis_index), "the ZX row did not show the executable kind"
    browser.mode(True)
    previous = begin_action(browser, zx_index)

    def opened():
        window = focused_window(browser, previous)
        return window and about_content(window[0])

    return until(opened, "double-click did not launch the ZX image")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--installed", action="store_true")
    parser.add_argument("--stock-only", action="store_true")
    parser.add_argument("--emulator", type=Path, default=EMU)
    parser.add_argument("--launcher", help="guest path of the matching launcher candidate")
    args = parser.parse_args()
    BUILD.mkdir(parents=True, exist_ok=True)
    image = BUILD / "dir.zx"
    if not args.installed and not args.stock_only:
        compile_image("dir_app", image, *FLAGS)
    with TemporaryDirectory(prefix="d", dir=BUILD) as fixture_dir, private_display() as env:
        root = Path(fixture_dir)
        directory, sink = fixture(root)
        expected = run_actions(env, args.emulator, "wm/dir", directory, sink, stock=True)
        print("Stock Directory Browser opened a second directory, editor and viewer and sent the exact WmDir message")
        if args.stock_only:
            return
        setup = f"bind {args.launcher} /dis/zxrun.dis; " if args.launcher else ""
        launcher = setup
        if not args.installed:
            overlay = root / "wm"
            overlay.mkdir()
            shutil.copyfile(image, overlay / "dir.zx")
            launcher += f"bind -b {guest(overlay)} /dis/wm; "
        launcher += "zxrun -w /dis/wm/dir.zx"
        actual = run_actions(env, args.emulator, launcher, directory, sink, stock=False)
        assert actual[:3] == expected[:3], "stock and Ziran file action windows differ"
        assert actual[3] == direct_about(env, args.emulator), "the launched About Inferno logo differs"
        print("Ziran matched stock child window, editor contents, viewer and plumbing, and launched a valid .dis directly")
        native = directory / NATIVE_IMAGE
        shutil.copyfile(ROOT / "dis/wm/about.zx", native)
        native.chmod(0o644)
        with desktop(env, args.emulator, f"{launcher} {guest(directory)}") as process:
            logo = open_native_image(Browser(env, process, stock=False))
        launched_directly = direct_about(env, args.emulator, f"{setup}zxrun -w /dis/wm/about.zx")
        assert logo == launched_directly, "the launched ZX child differed from the directly opened About window"
        print("ZX images show the executable icon and text kind and double-click launches a guest window without execute bits")


if __name__ == "__main__":
    main()
