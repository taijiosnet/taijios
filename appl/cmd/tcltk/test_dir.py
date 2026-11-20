"""Exercise the stock and native Directory Browser on a private Xvfb display."""

import argparse
from contextlib import contextmanager
import io
import os
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory

from PIL import Image
from test_logwindow import private_display, read_output
from test_menu import BORDER, inferno_window, pointer
from test_tcltk import BACKGROUND, BUILD, EMU, ROOT, color_bounds, command, compile_image, launch, stop, until

FLAGS = ("--define", "TK_MENU", "--define", "TK_BITMAP",
         "--bind-host", "zx_surface", "--bind-host", "taijios_files",
         "--bind-host", "taijios_args", "--bind-host", "taijios_io", "--bind-host", "taijios_wm")
BLACK = (0, 0, 0)
SELECTED = (0, 0, 204)
RED = (255, 0, 0)
TITLE = (28, 3, 345, 20)
FILES = ("alpha", "café", "omega.dis", "preview.gif", "zulu.GIF")
BY_NAME = ("..", *FILES[:4], "travel", "vanish", FILES[4])
ORDERS = (FILES, ("preview.gif", "alpha", "zulu.GIF", "omega.dis", "café"),
          ("preview.gif", "omega.dis", "café", "zulu.GIF", "alpha"),
          ("café", "alpha", "preview.gif", "zulu.GIF", "omega.dis"))
CANVAS_COLOR = (221, 221, 221)
CANVAS_WIDTH = 390
TILE_WIDTH = 130
TILE_HEIGHT = 50


def guest(path):
    return f"/{path.relative_to(ROOT)}"


@contextmanager
def desktop(env, emulator, script):
    app = launch(env, emulator, "-r", ROOT, "-g", "800x600", "wm/wm", "/dis/sh.dis", "-c", script,
                 stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        yield app
    finally:
        stop(app)
        app.stdout.close()
        app.stderr.close()


def fixture(root):
    day = 86400
    epoch = 1577836800
    for name, size, accessed, modified in zip(FILES, (13, 3, 82, 23, 41), (4, 1, 2, 5, 3), (1, 3, 4, 5, 2)):
        path = root / name
        path.write_bytes(b"x" * size)
        os.utime(path, (epoch + accessed * day, epoch + modified * day))
    (root / "travel").mkdir()
    (root / "vanish").mkdir()
    (root / "travel" / "inside space").write_bytes(b"outside\n")
    for index in range(25):
        (root / "travel" / f"item-{index:02d}").write_bytes(b"a\n")


def glyphs(image, *colors):
    pixels = image.tobytes()
    ink = tuple(bytes(color) for color in colors)
    luminance = bytes(255 if pixels[i:i+3] in ink else 0 for i in range(0, len(pixels), 3))
    mask = Image.frombytes("L", image.size, luminance).convert("1", dither=Image.Dither.NONE)
    bounds = mask.getbbox()
    if bounds is None:
        return None
    mask = mask.crop(bounds)
    return mask.size, mask.tobytes()


def row_mask(image, top):
    return glyphs(image.crop((10, top, 390, top + 13)), BLACK, SELECTED)


class Browser:
    def __init__(self, env, app, *, stock):
        self.env = env
        self.app = app
        self.stock = stock
        self.window = inferno_window(env)
        self.output = bytearray()
        self.open_x = 31
        self.open_y = 32
        self.menu_x = 31
        self.menu_y = 42
        if stock:
            until(lambda: self.capture().getpixel((10, 75)) != (119, 119, 119), "stock Directory Browser did not map")
        else:
            until(lambda: color_bounds(self.capture(), BACKGROUND), "Directory Browser .zx did not map")
            button = color_bounds(self.capture().crop((1, 23, 180, 64)), BORDER)
            assert button, "Options menubutton did not draw"
            left, top, right, bottom = button
            self.open_x = 1 + (left + right) // 2
            self.open_y = 23 + (top + bottom) // 2
            self.menu_x = 1 + left + 14
            self.menu_y = 23 + bottom
        self.canvas = until(self.canvas_origin, "Directory Browser Canvas did not draw at its stock width")

    def canvas_origin(self):
        image = self.capture()
        for y in range(43, 83):
            if image.getpixel((20, y)) != CANVAS_COLOR:
                continue
            left = next(x for x in range(20, 0, -1) if image.getpixel((x-1, y)) != CANVAS_COLOR)
            right = next(x for x in range(20, 446) if image.getpixel((x, y)) != CANVAS_COLOR)
            if right-left == CANVAS_WIDTH:
                return left, y
        return None

    def icon_grid(self):
        x, y = self.canvas
        return self.capture().crop((x, y, x+CANVAS_WIDTH, y+3*TILE_HEIGHT))

    def tile_center(self, index, *, label=False):
        row, column = divmod(index, 3)
        x, y = self.canvas
        return x + column*TILE_WIDTH + TILE_WIDTH//2, y + row*TILE_HEIGHT + (45 if label else 20)

    def tiles(self, *colors):
        grid = self.icon_grid()
        labels = []
        for index in range(len(BY_NAME)):
            row, column = divmod(index, 3)
            left, top = column*TILE_WIDTH, row*TILE_HEIGHT
            labels.append(glyphs(grid.crop((left, top+35, left+TILE_WIDTH, top+TILE_HEIGHT)), *colors))
        return labels

    def capture(self):
        read_output(self.app, self.output)
        assert self.output == b"", self.output
        png = command("import", "-window", self.window, "png:-", env=self.env,
                      capture_output=True, check=True).stdout
        return Image.open(io.BytesIO(png)).convert("RGB")

    def first_row(self):
        def locate():
            image = self.capture()
            for y in range(44, 120):
                if any(image.getpixel((x, y)) == BLACK for x in range(112, 275)):
                    # 8x13 text has two blank scanlines above the tallest glyph.
                    return y - 2
        return until(locate, "Directory Browser did not draw text rows")

    def pointer(self, x, y, *actions):
        pointer(self.env, self.window, x, y, *actions)

    def click(self, x, y):
        self.pointer(x, y, "mousedown", "1", "sleep", "0.12", "mouseup", "1")

    def double(self, index):
        self.double_at(125, self.first + 15 * index + 6)

    def double_at(self, x, y):
        self.pointer(x, y, "sleep", "0.34", "mousedown", "1", "sleep", "0.065",
                     "mouseup", "1", "sleep", "0.08", "mousedown", "1", "sleep", "0.065", "mouseup", "1")

    def choose(self, y):
        menu = (2, self.menu_y, 103, self.menu_y + 5)
        closed = self.capture().crop(menu).tobytes()

        def posted():
            image = self.capture()
            if self.stock:
                return image.crop(menu).tobytes() != closed
            return image.getpixel((self.menu_x + 50, self.menu_y)) == BORDER

        self.pointer(self.open_x, self.open_y, "mousedown", "1")
        until(posted, "Options did not post")
        self.pointer(self.menu_x, y, "sleep", "0.12", "mouseup", "1")
        self.click(345, 32)
        until(lambda: not posted(), "Options stayed posted")

    def sort(self, index):
        self.choose((53, 75, 96, 117)[index] if self.stock else self.menu_y + 12 + 22 * index)

    def mode(self, icons):
        if self.stock:
            y = 155 if icons else 177
        else:
            y = self.menu_y + 12 + 22 * (4 if icons else 5) + 6
        self.choose(y)
        if not icons:
            self.first = self.first_row()

    def walk(self):
        self.choose(198 if self.stock else self.menu_y + 12 + 22 * 6 + 12)

    def rows(self, image=None, count=len(BY_NAME)):
        image = image if image is not None else self.capture()
        return [row_mask(image, self.first + 15 * i) for i in range(count)]

    def title(self):
        # WM title updates can move the glyph origin by a pixel.
        return glyphs(self.capture().crop(TITLE), (255, 255, 255))


def exercise_icons(browser):
    by_name = until(lambda: labels if all(labels := browser.tiles(BLACK)) else None,
                    "Directory Browser did not start in icon view")
    initial = browser.icon_grid()
    known = dict(zip(BY_NAME, by_name))
    assert len(set(known.values())) == len(known), "icon labels did not render distinctly"
    root_title = browser.title()
    if not browser.stock:
        # Clicking the bitmap highlights its own label, rather than a different item in the grid.
        browser.click(*browser.tile_center(BY_NAME.index("travel")))
        until(lambda: known["travel"] in browser.tiles(SELECTED), "icon click did not select its label")
    browser.sort(2)
    expected = [known[name] for name in ORDERS[2]]

    def sorted_icons():
        return [label for label in browser.tiles(BLACK, SELECTED) if label in expected] == expected

    until(sorted_icons, "icon view did not sort by modification time")
    browser.walk()
    browser.mode(False)
    if not browser.stock:
        left, top = browser.canvas
        crop = browser.capture().crop((left, top, left+CANVAS_WIDTH, top+150))
        assert color_bounds(crop, SELECTED), "icon selection disappeared in text view"
    browser.mode(True)
    until(sorted_icons, "changing views reset the icon sort")
    if not browser.stock:
        assert known["travel"] in browser.tiles(SELECTED), "changing views reset the selected icon"
    browser.sort(0)
    until(lambda: browser.tiles(BLACK, SELECTED) == by_name, "icon view did not restore name order")
    browser.double_at(*browser.tile_center(BY_NAME.index("travel")))
    until(lambda: browser.title() not in (None, root_title), "Walk did not open the selected directory icon")
    # The stock application binds the bitmap. The port also makes the label an entry target.
    browser.double_at(*browser.tile_center(0, label=not browser.stock))
    until(lambda: browser.title() == root_title, "Walk did not return through the '..' icon")
    browser.walk()
    browser.mode(False)
    return initial


def compare_sorts(browser):
    by_name = until(lambda: all(rows) and rows if (rows := browser.rows()) else None,
                    "initial Directory Browser listing incomplete")
    known = dict(zip(BY_NAME, by_name))
    assert len(set(known.values())) == len(known), "directory rows did not render distinctly"
    root_title = browser.title()
    assert root_title, "Directory Browser did not draw its title"
    if not browser.stock:
        browser.click(125, browser.first + BY_NAME.index("travel") * 15 + 6)
        until(lambda: color_bounds(browser.capture().crop((10, browser.first, 390, browser.first + len(BY_NAME)*15)), SELECTED),
              "single click did not highlight a directory entry")
        assert browser.title() == root_title
    for index in (1, 2, 3, 0):
        browser.sort(index)
        expected = [known[name] for name in ORDERS[index]]
        until(lambda: [row for row in browser.rows() if row in expected] == expected,
              f"incorrect ordering for sort {index}")
    return by_name, known, root_title


def exercise(browser):
    by_name, known, root_title = compare_sorts(browser)
    browser.walk()
    browser.double(BY_NAME.index("travel"))
    nested = until(lambda: (rows if rows[1] and rows[1] != by_name[1] else None) if (rows := browser.rows()) else None,
                   "double-click did not open the child in the same window")
    child_title = until(lambda: (title if title != root_title else None) if (title := browser.title()) else None,
                        "child opened without changing the live window title")
    if not browser.stock:
        scroll_x, scroll_y = browser.canvas
        scroll_x += CANVAS_WIDTH
        scrollbar = color_bounds(browser.capture().crop((scroll_x, scroll_y, scroll_x+23, 351)), BORDER)
        assert scrollbar, "listing scrollbar did not draw"
        left, _, right, bottom = scrollbar
        browser.click(scroll_x + (left + right)//2, scroll_y + bottom-8)
        until(lambda: browser.rows() != nested, "scrollbar did not move the child listing")
        assert browser.title() == child_title
        # A sort resets scrolling, as the Dis app does.
        browser.sort(0)
        until(lambda: browser.rows() == nested, "sort did not reset the child scroll position")
    browser.double(0)
    until(lambda: browser.rows()[1:] == by_name[1:], "double-clicking '..' did not restore the parent listing")
    until(lambda: browser.title() == root_title, "double-clicking '..' did not restore the parent title")
    return known, nested[1], root_title, child_title


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--installed", action="store_true")
    parser.add_argument("--emulator", type=Path, default=EMU, help="host path of a private emulator candidate")
    parser.add_argument("--launcher", default="zxrun", help="guest command or path of a paired launcher candidate")
    args = parser.parse_args()
    BUILD.mkdir(parents=True, exist_ok=True)
    image = (ROOT / "dis/wm" if args.installed else BUILD) / "dir.zx"
    if not args.installed:
        compile_image("dir_app", image, *FLAGS)
    with TemporaryDirectory(prefix="d", dir=BUILD) as folder, private_display() as env:
        root = Path(folder)
        fixture(root)
        with desktop(env, args.emulator, f"wm/dir {guest(root)}") as app:
            browser = Browser(env, app, stock=True)
            stock_icons = exercise_icons(browser)
            stock, stock_child, root_title, child_title = exercise(browser)
        with desktop(env, args.emulator, f"{args.launcher} -w {guest(image)} {guest(root)}") as app:
            browser = Browser(env, app, stock=False)
            native_icons = exercise_icons(browser)
            assert native_icons.tobytes() == stock_icons.tobytes(), "stock icon grid pixels differ"
            hosted, hosted_child, hosted_root, hosted_title = exercise(browser)
            for name in FILES + ("travel", "vanish"):
                assert hosted[name] == stock[name], f"stock text pixels differ for {name}"
            assert hosted_child == stock_child, "stock text pixels differ for the child listing"
            assert (hosted_root, hosted_title) == (root_title, child_title), "stock WM title pixels differ"
            preceding = browser.rows()
            (root / "vanish").rmdir()
            browser.double(BY_NAME.index("vanish"))
            until(lambda: color_bounds(browser.capture().crop((0, 335, 415, 374)), RED),
                  "failed directory change did not show an error")
            assert browser.title() == hosted_root, "failed directory change changed the title"
            assert browser.rows() == preceding, "failed directory change replaced the visible listing"
            browser.double(BY_NAME.index("travel"))
            until(lambda: browser.title() == hosted_title, "Walk did not recover after the error")
    print("Stock and .zx Directory Browser agree on default icon layout, mask pixels, labels and icon-based Walk")
    print("View changes preserve sort, Walk and selection")
    print("Stock and .zx Directory Browser agree on text glyphs, all four sort orders, live titles, Walk and '..'")
    print("The .zx scrollbar and selection work, and a failed Walk preserves the previous listing and title")


if __name__ == "__main__":
    main()
