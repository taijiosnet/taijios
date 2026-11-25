#!/usr/bin/env python3
"""Exercise the Date menu's guest-time conversion and idle refresh."""
import argparse
from datetime import datetime, timezone
import io
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory

from PIL import Image

from kryon_apps_test import SURFACE, guest_overlay, wait_start
from test_logwindow import private_display
from test_tcltk import BUILD, EMU, ROOT, color_bounds, launch, stop, until


def set_clock(path, instant):
    seconds = int(datetime.fromisoformat(instant).replace(tzinfo=timezone.utc).timestamp())
    staged = path.with_suffix('.next')
    staged.write_text(str(seconds * 1_000_000))
    staged.replace(path)


def exercise(env, emu, overlay, device):
    set_clock(device / 'time', '2024-02-28T21:00:01')
    prefix = guest_overlay(overlay)
    prefix += f'bind -b /{device.relative_to(ROOT)} /dev; '
    prefix += "echo 'EET 7200 EEST 10800 0 2000000000' > /env/timezone; "
    child = launch(env, emu, '-r', ROOT, '-g', '800x600', '/zx/sh.dis', '-c',
                   prefix + 'wm/wm wm/toolbar', stdin=subprocess.DEVNULL)
    try:
        def x(*command, check=True):
            return subprocess.run(command, env=env, capture_output=True, check=check, timeout=5).stdout

        found = lambda: x('xdotool', 'search', '--onlyvisible', '--name', '^inferno$', check=False).strip()
        window = until(found, 'private guest did not open').decode()

        def capture():
            return Image.open(io.BytesIO(x('import', '-window', window, 'png:-'))).convert('RGB')

        def mouse(xpos, ypos):
            return ('mousemove', '--window', window, str(xpos), str(ypos))

        def displayed_time():
            screen = capture()
            bounds = color_bounds(screen, SURFACE)
            if not bounds or bounds[2] - bounds[0] < 176 or bounds[3] - bounds[1] != 26:
                return None, bounds
            label = screen.crop(bounds)
            caption = io.BytesIO()
            label.resize((4 * label.width, 4 * label.height)).save(caption, format='PNG')
            text = subprocess.run(['tesseract', 'stdin', 'stdout', '--psm', '7'], input=caption.getvalue(),
                                  capture_output=True, check=True, timeout=5).stdout.decode()
            return text.strip(), bounds

        def expect(text):
            observed = None
            bounds = None

            def matches():
                nonlocal observed, bounds
                observed, bounds = displayed_time()
                return observed is not None and ''.join(observed.split()) == ''.join(text.split())

            try:
                until(matches, f'ZX Date did not show {text}')
            except AssertionError as error:
                raise AssertionError(f'{error}. Last reading {observed!r} at {bounds}') from None

        wait_start(capture, False)
        desktop = capture()
        menu_origin = (11, 402)
        date_row = (215, 473, 275, 488)
        x('xdotool', *mouse(36, 584), 'mousedown', '1')
        until(lambda: capture().getpixel(menu_origin) != desktop.getpixel(menu_origin),
              'ZX Start menu did not paint')
        x('xdotool', *mouse(45, 430))
        until(lambda: capture().crop(date_row).tobytes() != desktop.crop(date_row).tobytes(),
              'Utilities submenu did not paint the Date and Time row')
        x('xdotool', *mouse(230, 480), 'sleep', '.12', 'mouseup', '1')
        expect('Thu Feb 29 00:00:01')
        set_clock(device / 'time', '1969-12-31T21:59:58')
        expect('Wed Dec 31 23:59:58')
        print('ZX Date applied guest daylight and standard offsets across midnight and refreshed without input')
    finally:
        stop(child)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--emu', type=Path, default=EMU)
    parser.add_argument('--guest-overlay', type=Path)
    args = parser.parse_args()
    BUILD.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=BUILD) as directory, private_display() as env:
        exercise(env, args.emu, args.guest_overlay, Path(directory))


if __name__ == '__main__':
    main()
