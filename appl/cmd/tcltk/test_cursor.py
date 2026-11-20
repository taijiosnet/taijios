"""Compare the Tk cursor commands and visible cursor shapes with stock tkcmd."""

import argparse
from contextlib import contextmanager
import ctypes as C
import ctypes.util
import errno
import io
import os
from pathlib import Path
from tempfile import TemporaryDirectory

from PIL import Image

from test_dir import desktop, guest
from test_logwindow import private_display, read_output
from test_menu import inferno_window, pointer
from test_tcltk import BUILD, EMU, command, compile_image, until

FRAME = (50, 100, 150)
BUTTON = (224, 234, 242)


class CursorImage(C.Structure):
    _fields_ = [
        ("x", C.c_short), ("y", C.c_short), ("width", C.c_ushort), ("height", C.c_ushort),
        ("hot_x", C.c_ushort), ("hot_y", C.c_ushort), ("serial", C.c_ulong),
        ("pixels", C.POINTER(C.c_ulong)),
    ]


@contextmanager
def cursor_reader(env):
    x11 = C.CDLL(C.util.find_library("X11"))
    xfixes = C.CDLL(C.util.find_library("Xfixes"))
    x11.XOpenDisplay.argtypes = [C.c_char_p]
    x11.XOpenDisplay.restype = C.c_void_p
    x11.XFree.argtypes = [C.c_void_p]
    x11.XCloseDisplay.argtypes = [C.c_void_p]
    xfixes.XFixesGetCursorImage.argtypes = [C.c_void_p]
    xfixes.XFixesGetCursorImage.restype = C.POINTER(CursorImage)
    display = x11.XOpenDisplay(env["DISPLAY"].encode())
    assert display, "could not read the private display's cursor"

    def snapshot():
        image = xfixes.XFixesGetCursorImage(display)
        assert image, "the private display returned no cursor image"
        try:
            cursor = image.contents
            return (cursor.width, cursor.height, cursor.hot_x, cursor.hot_y,
                    tuple(cursor.pixels[:cursor.width * cursor.height]))
        finally:
            x11.XFree(image)

    try:
        yield snapshot
    finally:
        x11.XCloseDisplay(display)


def pixel_location(env, window, color):
    png = command("import", "-window", window, "png:-", env=env, capture_output=True, check=True).stdout
    image = Image.open(io.BytesIO(png)).convert("RGB")
    pixels = [(x, y) for x in range(1, 220) for y in range(25, 150) if image.getpixel((x, y)) == color]
    if not pixels:
        return None
    return tuple((min(values) + max(values)) // 2 for values in zip(*pixels))

def changed(snapshot, before):
    current = snapshot()
    return current if current != before else None


def reference(env, emulator, directory):
    fifo = directory / "commands"
    os.mkfifo(fifo)

    def connect():
        try:
            return os.open(fifo, os.O_WRONLY | os.O_NONBLOCK)
        except OSError as error:
            if error.errno != errno.ENXIO:
                raise
            return None

    with desktop(env, emulator, f"tkcmd < {guest(fifo)}") as process, cursor_reader(env) as snapshot:
        fd = until(connect, "tkcmd did not open its command stream")
        try:
            os.write(fd, b"frame .f -width 180 -height 100 -bg #326496\npack .f\nupdate\n")
            window = inferno_window(env)
            at = until(lambda: pixel_location(env, window, FRAME), "stock cursor window did not map")
            pointer(env, window, *at, "sleep", ".2")
            default = snapshot()
            os.write(fd, b"cursor -image waiting\nimage create bitmap invalid -file dir.bit\ncursor -image invalid\n"
                         b"image create bitmap waiting -file cursor.wait\ncursor -image waiting\n")
            waiting = until(lambda: changed(snapshot, default), "stock cursor did not change")
            os.write(fd, b"cursor -default\n")
            until(lambda: snapshot() == default, "stock cursor did not reset")
            output = bytearray()
            read_output(process, output)
            errors = [line[2:] for line in output.splitlines() if line.startswith(b"#!")]
            assert errors == [b"bad value", b"bad cursor image"], output
            return default, waiting, errors
        finally:
            os.close(fd)


def hosted(env, emulator, launcher, image, expected):
    default, waiting, errors = expected
    with desktop(env, emulator, f"{launcher} -w {guest(image)}") as process, cursor_reader(env) as snapshot:
        window = inferno_window(env)
        output = bytearray()

        def ready():
            read_output(process, output)
            assert len(output.splitlines()) <= len(errors), output
            return pixel_location(env, window, BUTTON)

        def transcript():
            read_output(process, output)
            return output.splitlines()

        toggle = until(ready, "the cursor toggle did not map")

        def click():
            pointer(env, window, *toggle, "mousedown", "1", "sleep", ".12", "mouseup", "1")
        pointer(env, window, *toggle)
        until(lambda: snapshot() == default, "the hosted default cursor differs from stock")
        click()
        until(lambda: b"waiting" in transcript(), f"Waiting callback did not finish at {toggle}")
        until(lambda: snapshot() == waiting, "the hosted waiting cursor differs from stock")
        click()
        try:
            until(lambda: b"default" in transcript(), f"Default callback did not finish at {toggle}")
            until(lambda: snapshot() == default, "the hosted cursor did not restore the stock default shape")
        except AssertionError as error:
            raise AssertionError(f"{error}. Guest output {output!r}, hotspot and size {snapshot()[:4]}") from error
        assert transcript() == [*errors, b"waiting", b"default"], output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--emulator", type=Path, default=EMU)
    parser.add_argument("--launcher", default="zxrun")
    args = parser.parse_args()
    BUILD.mkdir(parents=True, exist_ok=True)
    image = BUILD / "cursor_window_test.zx"
    compile_image("cursor_window_test", image, "--define", "TK_BITMAP", "--define", "TK_NO_CANVAS",
                  "--bind-host", "zx_surface", "--bind-host", "taijios_files", "--bind-host", "taijios_wm")
    with TemporaryDirectory(prefix="cursor", dir=BUILD) as name, private_display() as env:
        expected = reference(env, args.emulator, Path(name))
        hosted(env, args.emulator, args.launcher, image, expected)
    print("Tk cursor errors, waiting bitmap pixels and hotspot, and restored default match stock")


if __name__ == "__main__":
    main()
