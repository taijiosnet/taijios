"""Compare Tk selection widgets with Inferno tkcmd and the stock Directory Browser."""

import argparse
import io
from pathlib import Path
from tempfile import TemporaryDirectory

from PIL import Image, ImageChops
from test_about import transcript
from test_logwindow import private_display
from test_memory import desktop
from test_menu import BORDER, PRESSED, inferno_window, pointer
from test_tcltk import BUILD, ROOT, RUNNER_FLAGS, SOURCES, color_bounds, command, compile_image, interaction, until


def stock_directory(env):
    with TemporaryDirectory(dir=BUILD) as folder:
        directory = Path(folder)
        (directory / "subdir").mkdir()
        (directory / "alpha").write_bytes(b"a\n")
        (directory / "zulu").write_bytes(b"z" * 257)
        with desktop(env, f"wm/dir /{directory.relative_to(ROOT)}"):
            window = inferno_window(env)

            def capture():
                png = command("import", "-window", window, "png:-", env=env,
                              capture_output=True, check=True).stdout
                return Image.open(io.BytesIO(png)).convert("RGB")

            def showing_directory():
                image = capture()
                return image if image.getpixel((10, 75)) != (119, 119, 119) else None

            icons = until(showing_directory, "Inferno Directory Browser did not map")
            pointer(env, window, 31, 32, "mousedown", "1")
            probe = (1, 41, 104, 46)
            until(lambda: ImageChops.difference(icons.crop(probe), capture().crop(probe)).getbbox(),
                  "Directory Browser did not post Options")
            listing = (110, 48, 289, 142)

            def choose(y, *, held=False):
                if not held:
                    pointer(env, window, 31, y, "mousedown", "1")
                pointer(env, window, 31, y, "sleep", "0.15", "mouseup", "1")

            def changed_from(previous):
                after = capture()
                return after if ImageChops.difference(previous.crop(listing), after.crop(listing)).getbbox() else None

            choose(177, held=True)
            text = until(lambda: changed_from(icons), "Directory Browser did not switch to the text listing")
            assert ImageChops.difference(icons.crop(probe), text.crop(probe)).getbbox(), "radio release dismissed Options"
            choose(117)
            sorted_text = until(lambda: changed_from(text), "Directory Browser did not sort the text listing by size")
            assert ImageChops.difference(icons.crop(probe), sorted_text.crop(probe)).getbbox(), "sort dismissed Options"

            pointer(env, window, 31, 198)
            walk_indicator = (7, 189, 26, 206)
            unchecked = until(lambda: (im if im.getpixel((27, 198)) == (237, 237, 237) else None)
                              if (im := capture()) else None, "Walk did not highlight").crop(walk_indicator)
            choose(198)
            until(lambda: ImageChops.difference(unchecked, capture().crop(walk_indicator)).getbbox(),
                  "Directory Browser Walk entry did not toggle its check indicator")
            assert ImageChops.difference(icons.crop(probe), capture().crop(probe)).getbbox(), "check release dismissed Options"
            pointer(env, window, 325, 290, "click", "1")
            until(lambda: not ImageChops.difference(icons.crop(probe), capture().crop(probe)).getbbox(),
                  "Click outside did not dismiss the Directory Browser Options")


LETTER = (25, 47, 67)
WHITE = (255, 255, 255)


def hosted_selection(env):
    def exercise(x, y, click, _keys, _type, capture, output):
        window = inferno_window(env)
        until(lambda: output() == [b"ready"], "selection fixture did not load")

        def selection(north, south):
            image = capture()
            return (image.getpixel((x+26, y+62)), image.getpixel((x+26, y+90))) == (north, south)

        assert selection(WHITE, WHITE), "radio buttons selected themselves before a variable write"
        pointer(env, window, x+26, y+62, "mousedown", "1")
        until(lambda: b"north" in output(), "standalone radio did not invoke on press")
        until(lambda: selection(LETTER, WHITE), "North did not draw a selected circle")
        pointer(env, window, x+26, y+62, "mouseup", "1")
        click(x+26, y+118)
        assert output() == [b"ready", b"north"] and selection(LETTER, WHITE), "disabled radio changed the selection"
        click(x+194, y+30)
        until(lambda: b"synced" in output(), "live variable callback did not run")
        until(lambda: selection(WHITE, LETTER), "a variable write did not transfer the visible selection")
        click(x+38, y+146)
        until(lambda: b"flat" in output() and selection(WHITE, WHITE), "indicator-off radio did not change the shared value")
        assert capture().getpixel((x+15, y+136)) == PRESSED, "indicator-off radio did not draw a selected button"

        opener = color_bounds(capture().crop((x, y+12, x+110, y+49)), BORDER)
        assert opener, "no visible Options button"
        left, top, right, bottom = opener
        open_x, open_y = x+(left+right)//2, y+12+(top+bottom)//2
        menu_x, menu_y = x+left, y+12+bottom

        def posted():
            return capture().getpixel((menu_x+1, menu_y)) == BORDER

        pointer(env, window, open_x, open_y, "mousedown", "1")
        until(posted, "Options did not post")
        pointer(env, window, menu_x+14, menu_y+12, "sleep", "0.15", "mouseup", "1")
        until(lambda: b"menu-north" in output(), "menu radio did not set its shared variable before the callback")
        until(lambda: capture().getpixel((menu_x+14, menu_y+12)) == LETTER, "menu radio did not draw its selected circle")
        assert posted(), "radio selection dismissed Options"
        click(menu_x+14, menu_y+34)
        assert b"disabled-entry" not in output() and posted(), "disabled radio entry activated or dismissed Options"
        mark = (menu_x+7, menu_y+48, menu_x+20, menu_y+62)
        walk_off = capture().crop(mark)
        click(menu_x+14, menu_y+55)
        until(lambda: b"on" in output(), "Walk did not propagate its on value to the callback")
        until(lambda: ImageChops.difference(walk_off, capture().crop(mark)).getbbox(), "Walk did not draw its check mark")
        assert posted(), "check selection dismissed Options"
        click(menu_x+14, menu_y+55)
        until(lambda: b"off" in output(), "Walk did not propagate its off value to the callback")
        until(lambda: not ImageChops.difference(walk_off, capture().crop(mark)).getbbox(), "Walk did not clear its check mark")
        click(menu_x+14, menu_y+75)
        until(lambda: b"done" in output() and not posted(), "command row did not invoke and close Options")
        until(lambda: selection(LETTER, WHITE), "menu radio did not redraw the standalone radio for the same variable")
        click(x+254, y+30)
        return ["ready", "north", "synced", "flat", "menu-north", "on", "off", "done"]

    return exercise


def main():
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--oracle-only", action="store_true")
    mode.add_argument("--installed", action="store_true")
    args = parser.parse_args()
    BUILD.mkdir(parents=True, exist_ok=True)
    fixture = SOURCES / "radio_commands.tcl"
    if not args.oracle_only:
        (BUILD / "radio_fixture.zi").write_text(f"Commands :: #string RADIO_END\n{fixture.read_text()}RADIO_END;\n")
        model = BUILD / "radio_command_test.zx"
        compile_image("radio_command_test", model, "--define", "TAIJI_TK_MENU", "--define", "TAIJI_TK_NO_CANVAS")
        portable = command("zi2zx", "run", "--backend", "engine", model, capture_output=True, text=True, check=True)
        image = (ROOT / "dis" if args.installed else BUILD) / "tcltk.zx"
        if not args.installed:
            compile_image("tcltk", image, *RUNNER_FLAGS)
    with private_display() as env:
        lines = transcript(env, f"tkcmd < /{fixture.relative_to(ROOT)}")
        assert lines[-1] == b"#END" and all(line.startswith(b"#") and not line.startswith(b"#!") for line in lines), lines
        print(f"Inferno tkcmd returned {len(lines)} selection widget results")
        stock_directory(env)
        print("Inferno Directory Browser Options switched to text, sorted by size, and toggled Walk while posted")
        if not args.oracle_only:
            assert portable.stdout.splitlines() == [*(line[1:].decode() for line in lines), "0"] and not portable.stderr, portable
            print("Ziran matched the full Inferno tkcmd selection transcript")
            interaction(env, image, SOURCES / "radio_window.tcl", hosted_selection(env))
            print("Hosted Tk verified press, disabled controls, live variable redraw, and radio and check menu selection")


if __name__ == "__main__":
    main()
