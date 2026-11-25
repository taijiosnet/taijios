"""Compare Tk selection widgets with recorded Inferno tkcmd results and exercise them hosted.

radio_commands.expected holds what Inferno tkcmd printed for radio_commands.tcl.
"""

import argparse
import io
from pathlib import Path

from PIL import Image, ImageChops
from test_logwindow import private_display
from test_menu import BORDER, PRESSED, inferno_window, pointer
from test_tcltk import BUILD, ROOT, RUNNER_FLAGS, SOURCES, color_bounds, command, compile_image, interaction, until, write_fixture


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
    parser.add_argument("--installed", action="store_true")
    args = parser.parse_args()
    BUILD.mkdir(parents=True, exist_ok=True)
    fixture = SOURCES / "radio_commands.tcl"
    write_fixture("radio_fixture.zi", f"Commands :: #string RADIO_END\n{fixture.read_text()}RADIO_END;\n")
    model = BUILD / "radio_command_test.zx"
    compile_image("radio_command_test", model, "--define", "TK_MENU", "--define", "TK_NO_CANVAS")
    portable = command("zi2zx", "run", "--backend", "engine", model, capture_output=True, text=True, check=True)
    image = (ROOT / "zx" if args.installed else BUILD) / "tcltk.zx"
    if not args.installed:
        compile_image("tcltk", image, *RUNNER_FLAGS)
    lines = (SOURCES / "radio_commands.expected").read_bytes().splitlines()
    assert lines[-1] == b"#END" and all(line.startswith(b"#") and not line.startswith(b"#!") for line in lines), lines
    assert portable.stdout.splitlines() == [*(line[1:].decode() for line in lines), "0"] and not portable.stderr, portable
    print(f"Ziran matched all {len(lines)} recorded Inferno tkcmd selection widget results")
    with private_display() as env:
        interaction(env, image, SOURCES / "radio_window.tcl", hosted_selection(env))
    print("Hosted Tk verified press, disabled controls, live variable redraw, and radio and check menu selection")


if __name__ == "__main__":
    main()
