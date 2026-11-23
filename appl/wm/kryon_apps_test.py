#!/usr/bin/env python3
"""Launch each installed Kryon app through the real TaijiOS start menu."""
import argparse
import io
import os
from pathlib import Path
import pwd
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory
import time

from PIL import Image, ImageChops

from clock_zx_test import close_point, face_center
from test_logwindow import private_display
from test_tcltk import EMU, ROOT, color_bounds, launch, stop, until

SURFACE = (248, 250, 252)
CAPTION_BACKGROUND = (12, 14, 20)
CAPTION_TEXT = ((146, 155, 168), (119, 128, 133))


def guest_overlay(path):
    if path is None:
        return ''
    mount = '/' + path.resolve().relative_to(ROOT).as_posix()
    return f'bind -b {mount} /dis; bind -b {mount} /dis/wm; bind -b {mount} /dis/lib; '


def wait_start(capture, legacy):
    if legacy:
        return until(lambda: capture().getpixel((2, 580)) != (119, 119, 119), 'guest toolbar missing')
    # Require the ZX panel's light Start face. A legacy Tk fallback fails here.
    return until(lambda: capture().getpixel((11, 574)) == (255, 255, 255), 'ZX panel missing')


def exercise_desktop(env, emu, overlay, legacy, chrome, resize):
    toolbar = 'wm/toolbar -l' if legacy else 'wm/toolbar'
    child = launch(env, emu, '-p', 'main=32M', '-r', ROOT, '-g', '800x600', '/dis/sh.dis', '-c',
                   f'{overlay}wm/wm {toolbar}', stdin=subprocess.DEVNULL,
                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def command(*args, check=True):
        return subprocess.run(args, env=env, capture_output=True, check=check, timeout=5).stdout

    def capture():
        return Image.open(io.BytesIO(command('import', '-window', window, 'png:-'))).convert('RGB')

    def mouse(x, y):
        return ('mousemove', '--window', window, str(x), str(y))

    def click(x, y):
        command('xdotool', *mouse(x, y), 'sleep', '.03', 'mousedown', '1', 'sleep', '.15', 'mouseup', '1')

    def open_app(row):
        start = (13, 582) if legacy else (36, 584)
        utilities = (42, 489) if legacy else (45, 430)
        column = 150 if legacy else 230
        command('xdotool', *mouse(*start), 'sleep', '.04', 'mousedown', '1', 'sleep', '.22',
                *mouse(*utilities), 'sleep', '.18', *mouse(column, row), 'sleep', '.12', 'mouseup', '1')

    def open_surface(row, name, size):
        open_app(row)

        def ready():
            image = capture()
            box = color_bounds(image, SURFACE)
            if box and (box[2] - box[0], box[3] - box[1]) == size:
                return image, box
            return None

        return until(ready, f'{name} did not draw from the Utilities menu')

    def chrome_caption(bounds, name):
        def painted():
            strip = capture().crop(bounds)
            colors = {color: count for count, color in strip.getcolors(strip.width * strip.height)}
            return colors.get(CAPTION_BACKGROUND, 0) > 60 and any(colors.get(color, 0) for color in CAPTION_TEXT)

        until(painted, f'{name} is missing the Kryon caption')

    def close_surface(box, name):
        point = (box[2] - 16, box[1] - 16) if chrome else (box[2] - 7, box[1] - 10)
        click(*point)
        until(lambda: color_bounds(capture(), SURFACE) is None, f'{name} did not close')

    def resize_corner(box, dx, dy, bounds, name):
        x, y = box[2] - 3, box[3] - 3
        command('xdotool', *mouse(x, y), 'sleep', '.10', 'mousedown', '1', 'sleep', '.16',
                *mouse(x + dx, y + dy), 'sleep', '.20', 'mouseup', '1')
        expected = (box[0], box[1], box[2] + dx, box[3] + dy)
        try:
            until(lambda: bounds() == expected, f'{name} did not resize to {expected}')
        except AssertionError as error:
            raise AssertionError(f'{error}, last bounds {bounds()}') from error
        return expected

    def exercise_log():
        area = (0, 0, 800, 560)
        until(lambda: capture().getpixel((89, 574)) == (255, 255, 255), 'Log task button missing')
        desktop = capture().crop(area)

        def log_window():
            return ImageChops.difference(desktop, capture().crop(area)).getbbox()

        click(118, 584)
        box = until(log_window, 'ZX panel did not restore the legacy Log window')
        if resize:
            box = resize_corner(box, 32, 24, log_window, 'legacy Log')
            box = resize_corner(box, -18, -16, log_window, 'legacy Log')
            print('Legacy Tk Log grew, shrank, and repainted', flush=True)
        left, top, right, _ = box
        assert right - left > 100
        if chrome:
            chrome_caption((left + 32, top + 2, right - 96, top + 29), 'legacy Log')
        close = (right - 16, top + 16) if chrome else (right - 8, top + 9)
        click(*close)
        until(lambda: log_window() is None, 'Log did not minimize through its title bar')
        click(118, 584)
        until(log_window, 'ZX panel did not restore Log a second time')
        click(*close)
        until(lambda: log_window() is None, 'Log did not minimize a second time')
        print('ZX task button restored the legacy Log window after title-bar minimize', flush=True)

    try:
        window = until(lambda: command('xdotool', 'search', '--onlyvisible', '--name',
                                       '^inferno$', check=False).strip(), 'TaijiOS window missing').decode()
        wait_start(capture, legacy)
        if not legacy:
            exercise_log()

        open_app(521 if legacy else 455)
        center = until(lambda: face_center(capture()), 'Clock face missing after Utilities menu launch')
        click(*close_point(capture(), center))
        until(lambda: face_center(capture()) is None, 'Clock did not dismiss')
        print('Utilities Clock: drew the clock face and dismissed', flush=True)

        before, box = open_surface(506 if legacy else 430, 'Stopwatch', (272, 210))
        x, y, right, _ = box
        elapsed = (x + 10, y + 53, right - 10, y + 85)
        initial = before.crop(elapsed).tobytes()
        click(x + 45, y + 27)
        until(lambda: capture().crop(elapsed).tobytes() != initial, 'Stopwatch did not tick')
        click(x + 135, y + 27)
        stopped = capture().crop(elapsed).tobytes()
        time.sleep(1.2)
        assert capture().crop(elapsed).tobytes() == stopped, 'Stopwatch kept ticking after Stop'
        click(x + 224, y + 27)
        until(lambda: capture().crop(elapsed).tobytes() == initial, 'Stopwatch did not reset')
        close_surface(box, 'Stopwatch')
        print('Utilities Stopwatch: ticked, stopped, reset, and closed', flush=True)

        if legacy:
            before, box = open_surface(489, 'Counter', (300, 110))
        else:
            click(36, 584)
            until(lambda: capture().getpixel((11, 402)) == (255, 255, 255), 'ZX Start menu did not draw')
            command('xdotool', 'key', '--clearmodifiers', 'Escape')
            until(lambda: capture().getpixel((11, 402)) == (119, 119, 119), 'Escape did not dismiss Start')
            click(36, 584)
            command('xdotool', 'key', '--clearmodifiers', '--delay', '120', 'Down', 'Down', 'Right', 'Return')
            box = until(lambda: color_bounds(capture(), SURFACE), 'Keyboard did not launch Counter')
            assert (box[2] - box[0], box[3] - box[1]) == (300, 110), box
            before = capture()
            print('ZX Start menu dismissed with Escape and launched Counter with arrow keys and Enter', flush=True)
        x, y, _, _ = box
        readout = (x + 12, y + 10, x + 180, y + 56)
        zero = before.crop(readout).tobytes()

        def count():
            return capture().crop(readout).tobytes()

        def changed(previous, message):
            def observed():
                pixels = count()
                return pixels if pixels != previous else None
            return until(observed, message)

        click(x + 241, y + 80)
        one = changed(zero, 'Counter did not increase')
        click(x + 241, y + 80)
        two = changed(one, 'Counter did not increase a second time')
        assert two != zero, 'Counter returned to zero on its second increase'
        click(x + 55, y + 80)
        until(lambda: count() == one, 'Counter did not decrease back to one')
        click(x + 150, y + 80)
        until(lambda: count() == zero, 'Counter did not reset to zero')
        click(x + 55, y + 80)
        negative = changed(zero, 'Counter did not decrease below zero')
        assert negative not in (one, two), 'Counter below zero displayed a positive count'
        click(x + 150, y + 80)
        until(lambda: count() == zero, 'Counter did not reset from below zero')
        if chrome:
            chrome_caption((x + 30, y - 30, x + 190, y - 2), 'Counter')
            close = (box[2] - 16, y - 16)
            command('xdotool', *mouse(*close), 'mousedown', '1', 'sleep', '.15',
                    *mouse(x + 100, y + 15), 'sleep', '.15', 'mouseup', '1')
            assert color_bounds(capture(), SURFACE) == box, 'Close activated after releasing outside its control'

            start = (x + 115, y - 16)
            end = (start[0] + 38, start[1] + 32)
            command('xdotool', *mouse(*start), 'mousedown', '1', 'sleep', '.20',
                    *mouse(*end), 'sleep', '.20', 'mouseup', '1')
            moved = tuple(value + (38, 32)[index % 2] for index, value in enumerate(box))
            until(lambda: color_bounds(capture(), SURFACE) == moved, 'Kryon caption did not move Counter')
            box = moved
            print('Kryon caption painted, dragged, and cancelled Close outside its control', flush=True)
        if resize:
            bounds = lambda: color_bounds(capture(), SURFACE)
            box = resize_corner(box, 40, 30, bounds, 'ZX Counter')
            box = resize_corner(box, -26, -20, bounds, 'ZX Counter')
            x, y, right, _ = box
            readout = (x + 12, y + 10, x + 180, y + 56)
            zero = count()
            click(x + 28 + int(2.5 * (right - x - 40) / 3), y + 80)
            changed(zero, 'Counter did not handle input after resize')
            print('ZX Counter grew, shrank, and accepted input in the resized layout', flush=True)
        close_surface(box, 'Counter')
        print('Utilities Counter: increased, decreased, reset, and closed', flush=True)
    finally:
        stop(child)
        diagnostics = child.stderr.read(8192).decode('utf-8', 'replace')
        if diagnostics:
            print(diagnostics, file=sys.stderr, end='')
        child.stdout.close()
        child.stderr.close()


def exercise_catalog(env, emu, runtime_overlay, legacy, overlay_path):
    # Keep the shipped shell script and menu registrations. Record launches
    # instead of opening browsers or a series of unrelated heavyweight apps.
    setup = (ROOT / 'lib/wmsetup').read_text()
    first = setup.index('fn wmrun {')
    last = setup.index('\nfn cd {', first)
    scratch = ROOT / 'build/zx-smoke'
    scratch.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=scratch) as dirname:
        overlay = Path(dirname)
        guest_path = '/' + str(overlay.relative_to(ROOT))
        trace = overlay / 'launch'
        (overlay / 'wmsetup').write_text(setup[:first] +
                                       f'fn wmrun {{echo MENU_COMMAND $* > {guest_path}/launch}}\n' + setup[last:])
        guest = launch(env, emu, '-p', 'main=32M', '-r', ROOT, '-g', '800x600', '/dis/sh.dis', '-c',
                       f'{runtime_overlay}bind -b {guest_path} /lib; wm/wm wm/toolbar' + (' -l' if legacy else ''),
                       stdin=subprocess.DEVNULL,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        def x(*args, check=True):
            return subprocess.run(args, env=env, capture_output=True, check=check, timeout=5).stdout

        def mouse(xpos, ypos):
            return ('mousemove', '--window', window, str(xpos), str(ypos))

        def wait_command(launch_command):
            expected = 'MENU_COMMAND ' + launch_command
            actual = until(lambda: trace.read_text().strip() if trace.is_file() else None,
                           f'No launch for {launch_command}', timeout=4)
            assert actual == expected, (actual, expected)
            trace.unlink()

        def select_entry(category, target, command):
            args = [*mouse(*((13, 582) if legacy else (36, 584))), 'sleep', '.04', 'mousedown', '1', 'sleep', '.16']
            if category is not None:
                args += [*mouse(*category), 'sleep', '.16']
            x('xdotool', *args, *mouse(*target), 'sleep', '.10', 'mouseup', '1')
            wait_command(command)

        try:
            window = until(lambda: x('xdotool', 'search', '--onlyvisible', '--name',
                                     '^inferno$', check=False).strip(), 'TaijiOS window missing').decode()

            def capture():
                return Image.open(io.BytesIO(x('import', '-window', window, 'png:-'))).convert('RGB')

            wait_start(capture, legacy)
            legacy_catalog = (
                ((26, 473), (138, 473), 'wm/bounce'),
                ((26, 473), (138, 490), 'wm/tetris'),
                ((42, 489), (142, 489), 'zxrun -w /dis/wm/counter.zx'),
                ((42, 489), (150, 506), 'zxrun -w /dis/wm/stopwatch.zx'),
                ((42, 489), (134, 522), 'zxrun -w /dis/wm/clock.zx'),
                ((42, 489), (166, 538), 'wm/date'),
                ((42, 489), (142, 554), 'wm/colors'),
                ((42, 489), (138, 570), 'wm/coffee'),
                ((42, 489), (138, 585), 'wm/man'),
                ((30, 507), (134, 505), 'wm/about'),
                ((30, 507), (138, 522), 'wm/memory'),
                ((30, 507), (150, 538), 'zxrun -w /dis/wm/taskmgr.zx'),
                ((30, 507), (138, 554), 'wm/rt'),
                ((30, 507), (134, 570), 'wm/sh'),
                ((50, 522), (146, 522), 'wm/deb'),
                ((50, 522), (130, 538), 'wm/edit'),
                ((50, 522), (137, 554), 'acme'),
                (None, (54, 543), 'charon'),
                (None, (26, 562), 'wm/ftree'),
            )
            positions = (
                ((45, 405), (230, 405)), ((45, 405), (230, 430)),
                ((45, 430), (230, 405)), ((45, 430), (230, 430)), ((45, 430), (230, 455)),
                ((45, 430), (230, 480)), ((45, 430), (230, 505)), ((45, 430), (230, 530)),
                ((45, 430), (230, 555)), ((45, 455), (230, 405)), ((45, 455), (230, 430)),
                ((45, 455), (230, 455)), ((45, 455), (230, 480)), ((45, 455), (230, 505)),
                ((45, 480), (230, 405)), ((45, 480), (230, 430)), ((45, 480), (230, 455)),
                (None, (60, 530)), (None, (60, 555)),
            )
            catalog = legacy_catalog if legacy else tuple((*coords, item[2]) for coords, item in
                                                          zip(positions, legacy_catalog, strict=True))
            def has_bundle(name):
                local = overlay_path / name if overlay_path else None
                if local and local.exists():
                    return local.is_file()
                return (ROOT / 'dis/wm' / name).is_file()

            guest_apps = (
                ('wm/colors', 'colors.zx', '-w'),
                ('wm/about', 'about.zx', '-w'),
                ('wm/memory', 'memory.zx', '-p -w'),
                ('wm/date', 'date.zx', '-w'),
            )
            zx_routes = {entry: f'zxrun {options} /dis/wm/{bundle}' for entry, bundle, options in guest_apps
                         if has_bundle(bundle)}
            for category, point, command in catalog:
                command = zx_routes.get(command, command)
                if command == 'wm/ftree':
                    if (ROOT / 'dis/wm/explorer.zx').is_file():
                        command = 'zxrun -w /dis/wm/explorer.zx'
                    else:
                        home = '/usr/' + os.environ.get('USER', '')
                        command = 'wm/ftree ' + (home if (ROOT / home.lstrip('/')).is_dir() else '/')
                select_entry(category, point, command)
            print(f'Start menu dispatched all {len(catalog)} entries with their guest arguments', flush=True)
        finally:
            stop(guest)
            diagnostics = guest.stderr.read(8192)
            guest.stdout.close()
            guest.stderr.close()
            assert not diagnostics, diagnostics


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('emu', type=Path, nargs='?', default=EMU)
    parser.add_argument('--guest-overlay', type=Path, help='use built guest artifacts from this directory')
    parser.add_argument('--legacy-menu', action='store_true', help='exercise the Dis toolbar fallback')
    parser.add_argument('--require-window-chrome', action='store_true', help='require and exercise the Kryon title bar')
    parser.add_argument('--require-window-resize', action='store_true', help='exercise lower-right window resizing')
    args = parser.parse_args()
    overlay = guest_overlay(args.guest_overlay)
    for name in ('XDG_RUNTIME_DIR', 'XDG_SESSION_ID', 'SESSION_MANAGER', 'HARMONY_GUEST_DISPLAY'):
        os.environ.pop(name, None)
    scratch = ROOT / 'build/zx-smoke'
    scratch.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=scratch) as directory, private_display() as env:
        users = Path(directory) / 'usr'
        user = pwd.getpwuid(os.getuid()).pw_name
        guest_lib = users / user / 'lib'
        guest_lib.mkdir(parents=True)
        shutil.copyfile(ROOT / 'usr/inferno/lib/plumbing', guest_lib / 'plumbing')
        overlay += f'bind -b /{users.relative_to(ROOT).as_posix()} /usr; '
        exercise_catalog(env, args.emu.resolve(), overlay, args.legacy_menu, args.guest_overlay)
        exercise_desktop(env, args.emu.resolve(), overlay, args.legacy_menu,
                         args.require_window_chrome, args.require_window_resize)


if __name__ == '__main__':
    main()
