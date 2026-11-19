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
        return all(f"#{expected}".encode() in values for expected in ("9 balls", "4", "2", "aßéz", ".f.input.e"))

    try:
        until(matched, "Inferno tkcmd results differ from the portable model fixture")
    except AssertionError as failure:
        raise AssertionError(f"{failure}: {output!r}") from failure
    finally:
        stop(app)
        app.stdout.close()
        app.stderr.close()
    print("Inferno Tk and the portable model agree on button, entry text, character indexes and focus")


def interaction(env, image, script, exercise):
    path = "/" + str(image.relative_to(ROOT))
    source = "/" + str(script.relative_to(ROOT))
    app = launch(env, EMU, "-r", ROOT, "-g", "800x600", "wm/wm", "/dis/sh.dis", "-c",
                 f"zxrun -w {path} < {source}",
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
            img = capture()
            delta = ImageChops.difference(img, Image.new("RGB", img.size, BACKGROUND))
            red, green, blue = delta.split()
            mask = ImageChops.lighter(ImageChops.lighter(red, green), blue).point(lambda n: 0 if n else 255)
            return mask.getbbox()

        def click(x, y):
            command("xdotool", "mousemove", "--sync", "--window", window, str(x), str(y),
                    "mousedown", "1", "sleep", "0.15", "mouseup", "1", env=env, check=True)

        box = until(canvas, "Tk surface did not present its canvas")
        assert (box[2] - box[0], box[3] - box[1]) == (300, 208), box
        command("xdotool", "windowfocus", window, env=env, check=True)

        def keys(*names):
            command("xdotool", "key", "--delay", "80", *names, env=env, check=True)

        expected = exercise(box[0], box[1], click, keys, capture, transcript)
        until(lambda: b"0" in transcript(), "Close button callback did not return success")
        until(lambda: canvas() is None, "destroy . did not remove the canvas")
        assert transcript() == [line.encode() for line in expected] + [b"0"], output
    except AssertionError as failure:
        raise AssertionError(f"{script.name}: {failure} (guest output {output!r})") from failure
    finally:
        stop(app)
        app.stdout.close()
        app.stderr.close()


def bounce(x, y, click, _keys, capture, transcript):
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


def man_query(x, y, click, keys, capture, transcript):
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


def main():
    cli = argparse.ArgumentParser()
    cli.add_argument("--installed", action="store_true", help="exercise /dis/tcltk.zx instead of the build image")
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
    else:
        image = BUILD / "tcltk.zx"
        compile_image("tcltk", image, "--bind-host", "zx_surface", "--bind-host", "taijios_stdin")

    env = os.environ.copy()
    for key in ("DISPLAY", "WAYLAND_DISPLAY", "XAUTHORITY", "DBUS_SESSION_BUS_ADDRESS"):
        env.pop(key, None)
    env["HARMONY_DESKTOP_RECOVERY"] = "0"
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
        interaction(env, image, SOURCES / "man_query.tcl", man_query)
        print("Hosted Tk loaded Man from guest stdin and verified nested layout, UTF-8 editing and submission")
    finally:
        os.close(read_fd)
        stop(server)


if __name__ == "__main__":
    main()
