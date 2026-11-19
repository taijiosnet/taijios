"""Build the Tcl/Tk port and compare behavior on a private Taiji desktop."""

import argparse
import io
import os
from pathlib import Path
import select
import signal
import subprocess
import time

from PIL import Image, ImageChops


SOURCES = Path(__file__).resolve().parent
ROOT = SOURCES.parents[2]
BUILD = ROOT / "build/tcltk"
EMU = ROOT / "Linux/386/bin/emu"
BACKGROUND = (244, 246, 247)


def command(*args, **options):
    return subprocess.run(args, cwd=ROOT, timeout=30, **options)


def compile_image(module, image, *flags):
    command("zi2zx", "--root", SOURCES, "--module-path", ROOT / "appl/lib", "--module-path", ROOT / "appl/cmd",
            "--module-path", BUILD,
            *flags, "--entry", f"{module}:main", "-o", image, SOURCES / f"{module}.zi", check=True)


def until(probe, description):
    deadline = time.monotonic() + 12
    while time.monotonic() < deadline:
        value = probe()
        if value:
            return value
        time.sleep(0.06)
    raise AssertionError(description)


def stop(process):
    if process.poll() is None:
        os.killpg(process.pid, signal.SIGKILL)
    process.wait(timeout=5)


def color_bounds(image, color):
    red, green, blue = ImageChops.difference(image, Image.new("RGB", image.size, color)).split()
    mask = ImageChops.lighter(ImageChops.lighter(red, green), blue).point(lambda n: 0 if n else 255)
    return mask.getbbox()


def launch(env, *args, **options):
    return subprocess.Popen(args, cwd=ROOT, env=env, start_new_session=True, **options)


def reference(env):
    app = launch(env, EMU, "-r", ROOT, "-g", "800x600", "wm/wm", "/dis/sh.dis", "-c",
                 "tkcmd < /appl/cmd/tcltk/tk_commands.tcl", stdin=subprocess.DEVNULL,
                 stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output = bytearray()

    def matched():
        readable, _, _ = select.select([app.stdout, app.stderr], [], [], 0)
        for stream in readable:
            data = os.read(stream.fileno(), 2048)
            assert stream is app.stdout or not data, data.decode(errors="replace")
            output.extend(data)
        assert len(output) < 8192, "unexpected Inferno Tk transcript size"
        values = output.splitlines()
        return all(f"#{expected}".encode() in values for expected in
                   ("9 balls", "4", "2", "aßéz", ".f.input.e", "1.11", "1.0"))

    try:
        until(matched, "Inferno tkcmd results differ from the portable model fixture")
    except AssertionError as failure:
        raise AssertionError(f"{failure}: {output!r}") from failure
    finally:
        stop(app)
        app.stdout.close()
        app.stderr.close()
    print("Inferno Tk and the portable model agree on buttons, UTF-8 entry indexes, focus, and two-way text search")


def interaction(env, image, script, exercise, *, size=(300, 208)):
    path = "/" + str(image.relative_to(ROOT))
    run = f"zxrun -w {path}"
    if script is not None:
        run += f" < /{script.relative_to(ROOT)}"
    app = launch(env, EMU, "-r", ROOT, "-g", "800x600", "wm/wm", "/dis/sh.dis", "-c",
                 run,
                 stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output = bytearray()
    errors = bytearray()

    def transcript():
        readable, _, _ = select.select([app.stdout, app.stderr], [], [], 0)
        for stream in readable:
            data = os.read(stream.fileno(), 2048)
            (output if stream is app.stdout else errors).extend(data)
        assert len(output) + len(errors) < 8192, "unexpected Tcl/Tk transcript size"
        assert not errors, errors.decode(errors="replace")
        return output.splitlines()

    def window_id():
        result = command("xdotool", "search", "--onlyvisible", "--name", "^inferno$",
                         env=env, capture_output=True, text=True)
        windows = result.stdout.splitlines()
        return windows[0] if len(windows) == 1 else None

    try:
        window = until(window_id, "emulator did not map its private X11 window")

        def capture():
            transcript()
            pixels = command("import", "-window", window, "png:-", env=env,
                             capture_output=True, check=True)
            return Image.open(io.BytesIO(pixels.stdout)).convert("RGB")

        def canvas():
            return color_bounds(capture(), BACKGROUND)

        def click(x, y):
            command("xdotool", "mousemove", "--sync", "--window", window, str(x), str(y),
                    "mousedown", "1", "sleep", "0.15", "mouseup", "1", env=env, check=True)

        box = until(canvas, "Tk surface did not present its canvas")
        assert (box[2] - box[0], box[3] - box[1]) == size, box
        command("xdotool", "windowfocus", window, env=env, check=True)

        def keys(*names):
            command("xdotool", "key", "--delay", "80", *names, env=env, check=True)

        def type_text(value):
            command("xdotool", "type", "--delay", "80", value, env=env, check=True)

        expected = exercise(box[0], box[1], click, keys, type_text, capture, transcript)
        until(lambda: b"0" in transcript(), "Close button callback did not return success")
        until(lambda: canvas() is None, "destroy . did not remove the canvas")
        assert transcript() == [line.encode() for line in expected] + [b"0"], output
    except AssertionError as failure:
        name = image.name if script is None else script.name
        raise AssertionError(f"{name}: {failure} (guest output {output!r})") from failure
    finally:
        stop(app)
        app.stdout.close()
        app.stderr.close()


def bounce(x, y, click, _keys, _type_text, capture, transcript):
    label = (x + 85, y + 12, x + 215, y + 48)
    starting = capture().crop(label)
    assert len(starting.getcolors()) > 1, "label rendered no visible text"
    click(x + 150, y + 116)
    until(lambda: b"9 balls" in transcript(), "+1 callback did not run")
    until(lambda: ImageChops.difference(starting, capture().crop(label)).getbbox(),
          "callback did not change the displayed label")
    click(x + 150, y + 71)
    until(lambda: b"8 balls" in transcript(), "-1 callback did not run")
    until(lambda: ImageChops.difference(starting, capture().crop(label)).getbbox() is None,
          "label did not return to its initial pixels")
    click(x + 150, y + 161)
    return ["9 balls", "8 balls"]


def entry_widget(x, y, click, keys, _type_text, capture, transcript):
    entry = (x + 20, y + 20, x + 178, y + 47)
    label = (x + 50, y + 60, x + 250, y + 130)
    blank = capture().crop(entry)
    starting = capture().crop(label)
    keys("eacute", "x")
    until(lambda: ImageChops.difference(blank, capture().crop(entry)).getbbox(),
          "focused entry did not render text")
    keys("Left", "BackSpace", "Return")
    until(lambda: b"x" in transcript(), "Backspace did not remove the whole UTF-8 character")
    until(lambda: ImageChops.difference(starting, capture().crop(label)).getbbox(),
          "Return callback did not update the result label")
    keys("Home", "eacute", "End", "BackSpace", "Return")
    until(lambda: "é".encode() in transcript(), "Home/End did not preserve UTF-8 input")
    keys("Home", "Delete", "a", "Return")
    until(lambda: b"a" in transcript(), "Delete did not remove the whole UTF-8 character")
    click(x + 24, y + 34)
    keys("b")
    click(x + 235, y + 34)
    until(lambda: b"ba" in transcript(), "Click did not move the cursor or invoke Search")
    click(x + 150, y + 173)
    return ["x", "é", "a", "ba"]


def manual_browser(x, y, click, keys, type_text, capture, _transcript):
    heading = (x + 75, y + 59, x + 425, y + 86)
    body = (x + 29, y + 103, x + 470, y + 336)
    text_box = (x + 18, y + 86, x + 482, y + 366)
    status_box = (x + 246, y + 374, x + 394, y + 400)
    selection = (255, 228, 145)
    underline = (30, 98, 145)

    def current():
        image = capture()
        return image.crop(heading), image.crop(body)

    def equals(a, b):
        return ImageChops.difference(a[0], b[0]).getbbox() is None and ImageChops.difference(a[1], b[1]).getbbox() is None

    def changed(before, description):
        def poll():
            now = current()
            return now if not equals(now, before) else None

        return until(poll, description)

    def query(previous, value, enter):
        click(x + 250, y + 35)
        keys("End", *(["BackSpace"] * len(previous)))
        type_text(value)
        if enter:
            keys("Return")
        else:
            click(x + 430, y + 35)

    def match_box():
        return color_bounds(capture().crop(text_box), selection)

    def selected_link():
        image = capture().crop(text_box)
        pixels = image.load()
        for row in range(4, image.height):
            for column in range(image.width):
                if pixels[column, row] == underline and pixels[column, row - 4] == selection:
                    return text_box[0] + column, text_box[1] + row - 4
        return None

    first = current()
    assert min(len(part.getcolors()) for part in first) > 1, "manual did not render heading and content"
    click(x + 190, y + 386)
    scrolled = changed(first, "Page Down did not scroll the actual manual")
    assert ImageChops.difference(first[0], scrolled[0]).getbbox() is None

    query("man(1)", "lc(1)", enter=False)
    listing = changed(scrolled, "Search did not load the ls alias")
    assert ImageChops.difference(scrolled[0], listing[0]).getbbox()
    click(x + 60, y + 35)
    until(lambda: equals(current(), scrolled), "Back did not restore the original scroll position")
    click(x + 140, y + 35)
    until(lambda: equals(current(), listing), "Next did not restore the ls page")

    query("lc(1)", "absent-manual", enter=True)
    missing = changed(listing, "a missing manual did not display a result")
    query("absent-manual", "2 sys-open", enter=True)
    recovered = changed(missing, "a section-qualified query did not recover after a missing manual")
    assert not equals(recovered, listing)
    click(x + 275, y + 186)
    keys("Next")
    scrolled_second = changed(recovered, "the focused text viewport did not accept Page Down")
    keys("Home")
    until(lambda: equals(current(), recovered), "Home did not reset scrolling")
    assert not equals(scrolled_second, recovered)

    click(x + 60, y + 35)
    until(lambda: equals(current(), missing), "Back did not restore the missing result")
    query("absent-manual", "man(1)", enter=True)
    until(lambda: equals(current(), first), "a new search did not open a fresh view")
    click(x + 140, y + 35)
    assert equals(current(), first), "a new search did not discard the forward history"

    query("man(1)", "plumber(1)", enter=True)
    plumber = changed(first, "plumber(1) did not open by topic")
    click(x + 60, y + 35)
    until(lambda: equals(current(), first), "Back did not return to man(1)")
    query("man(1)", "/man", enter=True)
    match = until(match_box, "forward search did not highlight a match in man(1)")
    keys("Return")

    def next_match():
        found = match_box()
        return found if found != match else None

    until(next_match, "repeating the search did not find the next occurrence")
    query("/man", "?man", enter=True)
    until(lambda: match_box() == match, "backward search did not return to the previous occurrence")
    found = current()
    blank_status = capture().crop(status_box)
    query("?man", "/no-such-text-here", enter=True)
    until(lambda: ImageChops.difference(blank_status, capture().crop(status_box)).getbbox(),
          "a missing term did not show feedback")
    assert equals(current(), found), "a missing term moved the viewport or cleared the match"

    query("/no-such-text-here", "/plumber(1)", enter=False)
    link = until(selected_link, "the real plumber(1) reference was not underlined and highlighted")
    before_link = current()
    match_before_link = match_box()
    click(*link)
    until(lambda: equals(current(), plumber), "clicking the reference did not open the same plumber(1) page")
    click(x + 60, y + 35)
    until(lambda: equals(current(), before_link) and match_box() == match_before_link,
          "Back after following a reference did not restore the previous viewport and match")
    click(x + 140, y + 35)
    until(lambda: equals(current(), plumber), "Next did not reopen the followed reference")
    click(x + 60, y + 35)
    until(lambda: equals(current(), before_link), "Back from the reference did not restore man(1)")

    query("man(1)", "canvas(9)", enter=True)
    long_page = changed(first, "the largest installed manual page did not render")
    click(x + 275, y + 186)
    keys("End")
    changed(long_page, "End did not reach the bottom of the long manual")
    click(x + 430, y + 386)
    return []


def file_and_manual_probe(env):
    image = BUILD / "man_probe.zx"
    compile_image("man_probe", image, "--bind-host", "taijios_files")
    (BUILD / "man-mount").mkdir(exist_ok=True)
    script = "bind /man/1 /build/tcltk/man-mount; zxrun /build/tcltk/man_probe.zx"
    result = command(EMU, "-r", ROOT, "/dis/sh.dis", "-c", script, env=env, stdin=subprocess.DEVNULL,
                     capture_output=True, text=True)
    expected = "Guest namespace offsets, mount, errors, real manual lookup and formatting verified\n0\n"
    assert result.returncode in (0, -9) and result.stdout == expected and not result.stderr, result
    print(expected.splitlines()[0])


def main():
    cli = argparse.ArgumentParser()
    cli.add_argument("--installed", action="store_true", help="exercise /dis/tcltk.zx and /dis/man.zx")
    args = cli.parse_args()
    BUILD.mkdir(parents=True, exist_ok=True)
    model = BUILD / "tcltk_model_test.zx"
    fixture = (SOURCES / "tk_commands.tcl").read_text()
    (BUILD / "tcltk_input.zi").write_text(f"Script :: #string TCLTK_SCRIPT_END\n{fixture}TCLTK_SCRIPT_END;\n")
    compile_image("tcltk_model_test", model)
    portable = command("zi2zx", "run", "--backend", "engine", model, capture_output=True, text=True, check=True)
    assert portable.stdout == ".f.input.e\naßéz\n0\n" and portable.stderr == "", (portable.stdout, portable.stderr)
    if args.installed:
        image = ROOT / "dis/tcltk.zx"
        manual = ROOT / "dis/man.zx"
    else:
        image = BUILD / "tcltk.zx"
        compile_image("tcltk", image, "--bind-host", "zx_surface", "--bind-host", "taijios_stdin")
        manual = BUILD / "man.zx"
        compile_image("man_app", manual, "--bind-host", "zx_surface", "--bind-host", "taijios_files")

    env = os.environ.copy()
    for key in ("DISPLAY", "WAYLAND_DISPLAY", "XAUTHORITY", "DBUS_SESSION_BUS_ADDRESS"):
        env.pop(key, None)
    env["HARMONY_DESKTOP_RECOVERY"] = "0"
    file_and_manual_probe(env)
    read_fd, write_fd = os.pipe()
    server = launch(env, "Xvfb", "-displayfd", str(write_fd), "-screen", "0", "1024x768x24",
                    "-nolisten", "tcp", pass_fds=(write_fd,))
    os.close(write_fd)
    try:
        ready, _, _ = select.select([read_fd], [], [], 6)
        assert ready, "private Xvfb did not return a display number"
        display = os.read(read_fd, 32).decode().strip()
        assert display.isdecimal(), f"invalid Xvfb display {display!r}"
        env["DISPLAY"] = f":{display}"
        reference(env)
        interaction(env, image, SOURCES / "bounce_controls.tcl", bounce)
        print("Hosted Tk loaded Bounce from guest stdin and verified clicks, redraw and closure")
        interaction(env, image, SOURCES / "entry_test.tcl", entry_widget)
        print("Hosted Tk verified nested layout, UTF-8 editing and submission")
        interaction(env, manual, None, manual_browser, size=(500, 420))
        print("Hosted Man verified manual references, text search, missing-result recovery, history and scroll restoration")
    finally:
        os.close(read_fd)
        stop(server)


if __name__ == "__main__":
    main()
