"""Compare the hosted Ziran menu with shipped Inferno tkcmd and Sweeper."""

import argparse
import io

from PIL import Image, ImageChops

from test_logwindow import private_display, read_output
from test_memory import desktop
from test_tcltk import BUILD, ROOT, RUNNER_FLAGS, SOURCES, color_bounds, command, compile_image, interaction, until, write_fixture


MENU_SCRIPT = SOURCES / "menu_commands.tcl"
END_MARKER = "#MENU-READY"
MENU_FLAGS = ("--define", "TK_MENU")
BORDER = (119, 149, 173)
PRESSED = (188, 213, 231)
DESKTOP = (119, 119, 119)


def oracle_transcript(env):
    invocation = f"tkcmd < /{MENU_SCRIPT.relative_to(ROOT)}; echo '{END_MARKER}'"
    with desktop(env, invocation) as app:
        output = bytearray()

        def transcript():
            read_output(app, output)
            lines = output.decode().splitlines()
            if END_MARKER not in lines:
                return None
            body = lines[:lines.index(END_MARKER)]
            assert all(line.startswith("#") for line in body), body
            return [line[1:] for line in body]

        return until(transcript, "Inferno tkcmd did not finish the menu fixture")


def inferno_window(env):
    return until(lambda: command("xdotool", "search", "--onlyvisible", "--name", "^inferno$",
                                 env=env, text=True, capture_output=True).stdout.strip(),
                 "Inferno did not map its private window")


def pointer(env, window, x, y, *actions):
    command("xdotool", "mousemove", "--window", window, str(x), str(y), *actions, env=env, check=True)


def sweeper(env):
    with desktop(env, "wm/sweeper"):
        window = inferno_window(env)

        def capture():
            png = command("import", "-window", window, "png:-", env=env, capture_output=True, check=True).stdout
            return Image.open(io.BytesIO(png)).convert("RGB")

        def board():
            image = capture()
            return image.crop((2, 74, 17, 91)) if image.getpixel((10, 75)) != DESKTOP else None

        initial = until(board, "Sweeper did not draw the board")
        pointer(env, window, 10, 75, "mousedown", "3", "sleep", "0.15", "mouseup", "3")
        pointer(env, window, 31, 32)
        until(lambda: ImageChops.difference(initial, board()).getbbox(), "Sweeper did not mark the first cell")
        menu_strip = (1, 41, 68, 59)
        closed = capture().crop(menu_strip)
        pointer(env, window, 31, 32, "mousedown", "1")
        until(lambda: ImageChops.difference(closed, capture().crop(menu_strip)).getbbox(),
              "Sweeper did not post the Options menu")
        pointer(env, window, 31, 52, "sleep", "0.10", "mouseup", "1")
        until(lambda: not ImageChops.difference(initial, board()).getbbox(),
              "Sweeper Options → restart did not clear the marked cell")


def exercise_menu(env):
    def exercise(x, y, click, _keys, _type, capture, transcript):
        window = inferno_window(env)
        opener = color_bounds(capture().crop((x, y+12, x+300, y+49)), BORDER)
        assert opener, "Options button border did not render"
        left, top, right, bottom = opener
        open_x = x+(left+right)//2
        open_y = y+12+(top+bottom)//2
        menu_x = x+left
        menu_y = y+12+bottom
        label = (x+100, y+53, x+200, y+86)
        initial = capture().crop(label)
        assert transcript() == [b"0.1", b"1.0"], "Tk and the Tcl script package did not load"

        def open_menu():
            pointer(env, window, open_x, open_y, "mousedown", "1")
            until(lambda: capture().getpixel((menu_x+1, menu_y)) == BORDER, "Options did not post a menu")

        def release_at(px, py):
            pointer(env, window, px, py, "mouseup", "1")

        def menu_dismissed():
            return capture().getpixel((menu_x+1, menu_y)) != BORDER

        open_menu()
        pointer(env, window, menu_x+8, menu_y+8)
        until(lambda: capture().getpixel((menu_x+4, menu_y+8)) == PRESSED,
              "Pointer did not highlight the Restart row")
        release_at(menu_x+8, menu_y+8)
        until(lambda: b"Restarted" in transcript(), "Restart callback did not run")
        until(menu_dismissed, "Menu stayed open after invoking Restart")
        until(lambda: ImageChops.difference(initial, capture().crop(label)).getbbox(),
              "Restart did not redraw the label")

        open_menu()
        release_at(menu_x+8, menu_y+29)
        until(menu_dismissed, "Menu stayed open after releasing on a disabled command")
        assert b"disabled-called" not in transcript(), "Disabled command ran"

        open_menu()
        release_at(menu_x+8, menu_y+19)
        assert not menu_dismissed(), "Separator release closed the menu"
        click(x+264, y+72)
        until(menu_dismissed, "Outside click did not dismiss the menu")

        click(x+150, y+111)
        until(lambda: capture().getpixel((x+97, y+30)) == BORDER, "Explicit post did not honor coordinates")
        click(x+264, y+72)
        until(lambda: capture().getpixel((x+97, y+30)) != BORDER, "Posted menu did not dismiss")
        click(x+150, y+155)
        return ["0.1", "1.0", "Restarted"]

    return exercise


def main():
    cli = argparse.ArgumentParser()
    mode = cli.add_mutually_exclusive_group()
    mode.add_argument("--oracle-only", action="store_true", help="exercise the shipped Inferno Tk only")
    mode.add_argument("--installed", action="store_true", help="exercise the installed guest launcher")
    args = cli.parse_args()
    image = (ROOT / "dis" if args.installed else BUILD) / "tcltk.zx"
    if not args.oracle_only:
        BUILD.mkdir(parents=True, exist_ok=True)
        commands = MENU_SCRIPT.read_text()
        write_fixture("menu_fixture.zi", f"Commands :: #string MENU_END\n{commands}MENU_END;\n")
        model = BUILD / "menu_command_test.zx"
        compile_image("menu_command_test", model, *MENU_FLAGS, "--define", "TK_NO_CANVAS")
        portable = command("zi2zx", "run", "--backend", "engine", model, capture_output=True, text=True, check=True)
        if not args.installed:
            compile_image("tcltk", image, *RUNNER_FLAGS)
    with private_display() as env:
        reference = oracle_transcript(env)
        print(f"Inferno tkcmd produced {len(reference)} menu and menubutton results")
        sweeper(env)
        print("Inferno Sweeper marked a real board cell and cleared it through Options → restart")
        if not args.oracle_only:
            assert portable.stdout.splitlines() == [*reference, "0"] and not portable.stderr, portable
            print("Portable Ziran menu matches the full Inferno tkcmd transcript")
            interaction(env, image, SOURCES / "menu_window.tcl", exercise_menu(env))
            print("Hosted Tk verified file-backed Tcl package loading, menu post, drag, callback redraw, disabled row, separator, outside dismissal and closure")


if __name__ == "__main__":
    main()
