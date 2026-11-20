"""Exercise Log Window's shipped Tk behavior on a private Taiji desktop."""

import argparse
from contextlib import contextmanager
import errno
import io
import os
from pathlib import Path
import select
import subprocess
from tempfile import TemporaryDirectory
import time

from PIL import Image, ImageChops

from test_tcltk import BACKGROUND, BUILD, EMU, ROOT, SOURCES, color_bounds, command, compile_image, launch, stop, until


TK_RESULT = (
    ".follow", "paused", "enabled", "paused", "paused", ".same", "follow", "paused", "paused", "enabled", "enabled",
    ".bar", "vertical", ".log yview", "0.125 0.875", "0 1", ".log", ".bar set", "hello", "0 1",
)


@contextmanager
def private_display():
    env = os.environ.copy()
    for key in ("DISPLAY", "WAYLAND_DISPLAY", "XAUTHORITY", "DBUS_SESSION_BUS_ADDRESS"):
        env.pop(key, None)
    env["HARMONY_DESKTOP_RECOVERY"] = "0"
    read_fd, write_fd = os.pipe()
    try:
        server = launch(env, "Xvfb", "-displayfd", str(write_fd), "-screen", "0", "1024x768x24",
                        "-nolisten", "tcp", pass_fds=(write_fd,))
    finally:
        os.close(write_fd)
    try:
        assert select.select([read_fd], [], [], 6)[0], "Xvfb returned no private display number"
        display = os.read(read_fd, 32).decode().strip()
        assert display.isdecimal(), display
        env["DISPLAY"] = f":{display}"
        yield env
    finally:
        os.close(read_fd)
        stop(server)


def tkcmd_reference(env):
    app = launch(env, EMU, "-r", ROOT, "-g", "800x600", "wm/wm", "/dis/sh.dis", "-c",
                 "tkcmd < /appl/cmd/tcltk/logwindow_commands.tcl", stdin=subprocess.DEVNULL,
                 stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output = bytearray()

    def matched():
        read_output(app, output)
        lines = output.splitlines()
        assert not any(line.startswith(b"#!") for line in lines), output
        return lines == [f"#{value}".encode() for value in TK_RESULT]

    try:
        until(matched, "Log Window tkcmd transcript did not match")
    except AssertionError as failure:
        raise AssertionError(f"{failure}: {output!r}") from failure
    finally:
        stop(app)
        app.stdout.close()
        app.stderr.close()


def read_output(app, output):
    for stream in select.select([app.stdout, app.stderr], [], [], 0)[0]:
        data = os.read(stream.fileno(), 2048)
        assert stream is app.stdout or not data, data.decode(errors="replace")
        output.extend(data)
    assert len(output) < 8192, "unexpected Log Window transcript size"


@contextmanager
def log_window(env, guest_command):
    with TemporaryDirectory(dir=BUILD) as dirname:
        # The real toolbar owns task/untask. Overlay its script only in this
        # test's guest namespace and feed the app through a real guest pipe.
        setup = Path(dirname)
        feed = setup / "input"
        os.mkfifo(feed)
        (setup / "wmsetup").write_text(f"{{cat /{feed.relative_to(ROOT)} | {guest_command}; echo logwindow-returned}} &\n")
        app = launch(env, EMU, "-r", ROOT, "-g", "800x600", "/dis/sh.dis", "-c",
                     f"bind -b /{setup.relative_to(ROOT)} /lib; wm/wm", stdin=subprocess.DEVNULL,
                     stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            window = until(lambda: command("xdotool", "search", "--onlyvisible", "--name", "^inferno$",
                                           env=env, capture_output=True, text=True).stdout.strip(),
                           "Log Window emulator did not map")
            output = bytearray()

            def input_writer():
                try:
                    return os.open(feed, os.O_WRONLY | os.O_NONBLOCK)
                except OSError as err:
                    if err.errno != errno.ENXIO:
                        raise

            with os.fdopen(until(input_writer, "guest cat did not open its input"), "wb", buffering=0) as writer:
                def capture():
                    read_output(app, output)
                    assert not any(line.startswith((b"logwindow:", b"zxrun:", b"arena "))
                                   for line in output.splitlines()), output.decode(errors="replace")
                    shot = command("import", "-window", window, "png:-", env=env, capture_output=True, check=True)
                    return Image.open(io.BytesIO(shot.stdout)).convert("RGB")

                def pointer(x, y, *actions):
                    command("xdotool", "mousemove", "--sync", "--window", window, str(x), str(y), *actions,
                            env=env, check=True)

                def send(data):
                    pending = memoryview(data)
                    while pending:
                        # The guest drains and repaints between chunks of a long stream.
                        assert select.select([], [writer], [], 20)[1], (
                            f"guest stopped reading the test pipe after {len(data) - len(pending)} of {len(data)} bytes"
                        )
                        written = writer.write(pending)
                        assert written, "guest test input could not be written"
                        pending = pending[written:]

                def returned():
                    read_output(app, output)
                    return b"logwindow-returned" in output

                yield capture, pointer, send, writer.close, returned
        finally:
            stop(app)
            app.stdout.close()
            app.stderr.close()


TASK_LABEL = (80, 575, 174, 595)


def visible(image, hosted):
    if hosted:
        return image.getpixel((150, 60)) == BACKGROUND
    return image.getpixel((150, 120)) == (221, 221, 221)


def is_tasked(image, hosted):
    return not visible(image, hosted) and any(color == (0, 0, 0) for _, color in image.crop(TASK_LABEL).getcolors())


def exercise_window(env, guest_command, *, hosted):
    with log_window(env, guest_command) as (capture, pointer, send, eof, _):
        def tasked():
            image = capture()
            return image if is_tasked(image, hosted) else None

        def click(x, y):
            pointer(x, y, "mousedown", "1", "sleep", "0.12", "mouseup", "1")
            pointer(600, 400)

        def changed(region, before):
            return ImageChops.difference(capture().crop(region), before).getbbox()

        def toggle(position, region, description):
            before = capture().crop(region)
            click(*position)
            until(lambda: changed(region, before), description)

        title = until(tasked, "Log Window did not start as a toolbar task").crop(TASK_LABEL)
        send(b"First log line\n")
        until(lambda: visible(capture(), hosted), "incoming text did not pop up Log Window")
        if hosted:
            left, top, right, bottom = color_bounds(capture(), BACKGROUND)
            assert (right-left, bottom-top) == (408, 374)
            bar = (left+28, top+70, left+46, top+352)
            scroll_button = (left+32, top+24, left+53, top+48)
            popup_button = (left+159, top+24, left+181, top+48)
            log_body = (left+69, top+78, left+376, top+344)
            scroll_click = (left+42, top+36)
            popup_click = (left+170, top+36)
            task_click = (right-28, 12)
            drag_x = left+37
        else:
            bar = (1, 60, 15, 299)
            scroll_button = (5, 25, 65, 43)
            popup_button = (68, 25, 135, 43)
            log_body = (17, 44, 325, 315)
            scroll_click = (14, 34)
            popup_click = (89, 34)
            task_click = (310, 12)
            drag_x = 7
        initial_bar = capture().crop(bar)
        send(b"".join(f"initial {n:02d}\n".encode() for n in range(44)))
        until(lambda: changed(bar, initial_bar), "Log Window did not scroll after receiving a full page of logs")

        toggle(scroll_click, scroll_button, "Scroll did not toggle while stdin was idle")
        bottom = capture().crop(log_body)
        if hosted:
            thumb = color_bounds(capture().crop(bar), (255, 255, 255))
            assert thumb and thumb[1] > 100, "scrollbar did not follow the end of the stream"
            drag_y = bar[1] + (thumb[1]+thumb[3])//2
            target_y = bar[1]+20
        else:
            drag_y = 254
            target_y = 76
        pointer(drag_x, drag_y, "mousedown", "1")
        if hosted:
            # Wait for the guest to paint its pressed thumb before sending motion.
            until(lambda: color_bounds(capture().crop(bar), (188, 213, 231)),
                  "scrollbar thumb did not enter its pressed state")
        pointer(drag_x, target_y)
        until(lambda: changed(log_body, bottom), "dragging the scrollbar did not move Log Window text")
        pointer(drag_x, target_y, "mouseup", "1")
        pointer(600, 400)
        pinned = capture()
        send(b"".join(f"paused {n:02d}\n".encode() for n in range(48)))
        until(lambda: changed(bar, pinned.crop(bar)), "new text did not update the scrollbar thumb")
        assert not changed(log_body, pinned.crop(log_body)), "Scroll off did not preserve the viewport"
        toggle(scroll_click, scroll_button, "Scroll did not turn back on")
        send(b"Follow once more\n")
        until(lambda: changed(log_body, pinned.crop(log_body)), "Scroll on did not resume following input")

        toggle(popup_click, popup_button, "Pop up did not toggle while stdin was idle")
        click(*task_click)
        until(tasked, "task icon did not hide Log Window")
        send(b"Stay hidden\n")
        time.sleep(0.4)
        assert tasked(), "new input raised Log Window while Pop up was off"
        click(100, 583)
        until(lambda: visible(capture(), hosted), "toolbar did not restore Log Window")
        toggle(popup_click, popup_button, "Pop up did not turn back on")
        click(*task_click)
        hidden_since = None

        def settled_task():
            nonlocal hidden_since
            image = tasked()
            now = time.monotonic()
            if image is None or ImageChops.difference(image.crop(TASK_LABEL), title).getbbox():
                hidden_since = None
                return False
            if hidden_since is None:
                hidden_since = now
            # The toolbar draws before the app receives its visibility event.
            return now - hidden_since >= 0.4

        until(settled_task, "Log Window did not settle back into its toolbar task")
        send(b"Pop up now\n")
        until(lambda: visible(capture(), hosted), "enabling Pop up did not restore Log Window on input")
        if hosted:
            white = Image.new("RGB", (log_body[2]-log_body[0], log_body[3]-log_body[1]), (255, 255, 255))
            send((b" " * 55 + b"\n") * 5000)
            until(lambda: not changed(log_body, white), "Log Window did not follow a long stream")
            send(b"Stream continued past 256 KiB\n")
            until(lambda: visible(capture(), hosted) and changed(log_body, white),
                  "Log Window lost the end of a long stream")
        before = capture().crop(log_body)
        eof()
        until(lambda: changed(log_body, before), "EOF marker did not appear")
        assert visible(capture(), hosted), "default EOF closed Log Window"
        return title


def exercise_eof_exit(env, guest_command, *, hosted, other_title):
    with log_window(env, guest_command) as (capture, _, send, eof, returned):
        def task_title():
            image = capture()
            return image.crop(TASK_LABEL) if is_tasked(image, hosted) else None

        title = until(task_title, "Log Window -e did not start as a toolbar task")
        assert ImageChops.difference(title, other_title).getbbox(), "custom title operand did not change the toolbar label"
        send(b"Check EOF exit\n")
        until(lambda: visible(capture(), hosted), "Log Window -e showed no data")
        eof()
        until(lambda: not visible(capture(), hosted) and returned(), "Log Window -e did not exit on EOF")


def main():
    cli = argparse.ArgumentParser()
    cli.add_argument("--installed", action="store_true", help="use the installed Log Window ZX image")
    cli.add_argument("--oracle-only", action="store_true", help="compare the model and original Inferno app")
    args = cli.parse_args()
    BUILD.mkdir(parents=True, exist_ok=True)
    image = BUILD / "logwindow_stream_test.zx"
    compile_image("logwindow_stream_test", image)
    stream = command("zi2zx", "run", "--backend", "engine", image, capture_output=True, text=True, check=True)
    assert stream.stdout.splitlines() == [
        "Log Window verified split UTF-8, idle input, EOF and input errors", "0",
    ] and not stream.stderr, stream
    print(stream.stdout.splitlines()[0])
    fixture = (SOURCES / "logwindow_commands.tcl").read_text()
    (BUILD / "logwindow_fixture.zi").write_text(f"Commands :: #string LOG_COMMANDS_END\n{fixture}LOG_COMMANDS_END;\n")
    model = BUILD / "logwindow_model_test.zx"
    compile_image("logwindow_model_test", model)
    result = command("zi2zx", "run", "--backend", "engine", model, capture_output=True, text=True, check=True)
    assert result.stdout.splitlines() == [*TK_RESULT, "0"] and not result.stderr, result
    hosted_image = ROOT / "dis/wm/logwindow.zx" if args.installed else BUILD / "logwindow.zx"
    if not args.oracle_only and not args.installed:
        compile_image("logwindow_app", hosted_image, "--bind-host", "zx_surface", "--bind-host", "taijios_stdin",
                      "--bind-host", "taijios_args", "--bind-host", "taijios_files")
    with private_display() as env:
        tkcmd_reference(env)
        print("Inferno and Ziran Tk agree on Log Window checkbuttons, scrollbar fractions and text scroll options")
        title = exercise_window(env, "wm/logwindow 'Tk Log Oracle'", hosted=False)
        exercise_eof_exit(env, "wm/logwindow -e 'Tk Log Exit'", hosted=False, other_title=title)
        print("Inferno Log Window verified live input, scrollbar dragging, both checkbuttons and EOF behavior")
        if not args.oracle_only:
            image_path = f"/{hosted_image.relative_to(ROOT)}"
            title = exercise_window(env, f"zxrun -p -w {image_path} 'Tk Log Oracle'", hosted=True)
            exercise_eof_exit(env, f"zxrun -w {image_path} -ge 'Tk Log Exit'", hosted=True, other_title=title)
            print("Hosted Log Window verified a pipe beyond 256 KiB, viewport changes, task and restore, title and EOF modes")


if __name__ == "__main__":
    main()
