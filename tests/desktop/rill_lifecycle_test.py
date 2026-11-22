"""Exercise the canonical Rill composition on a private guest display."""
import argparse
import csv
from hashlib import file_digest
from io import BytesIO, StringIO
from itertools import islice
import os
from pathlib import Path
from shutil import copyfile
import subprocess
import sys
from tempfile import TemporaryDirectory, TemporaryFile

from PIL import Image, ImageChops

PROJECT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT / 'appl/cmd/tcltk'))
sys.path.insert(0, str(PROJECT / 'appl/wm'))

from kryon_apps_test import guest_overlay
from test_logwindow import private_display
from test_tcltk import ROOT, color_bounds, launch, stop, until


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('bundle', type=Path)
    parser.add_argument('sha256')
    parser.add_argument('--emu', type=Path, default=ROOT / 'Linux/386/bin/emu')
    parser.add_argument('--guest-overlay', type=Path)
    parser.add_argument('--icon-atlas', type=Path)
    parser.add_argument('--report-memory', action='store_true')
    parser.add_argument('--failure-frame', type=Path)
    parser.add_argument('--pool', default='128M')
    parser.add_argument('--default-desktop', action='store_true')
    parser.add_argument('--desktop-extras', action='store_true')
    parser.add_argument('--compact-panel', action='store_true')
    parser.add_argument('--favorites', action='store_true')
    parser.add_argument('--workspace-tiles', action='store_true')
    parser.add_argument('--workspace-count', type=int, default=4)
    parser.add_argument('--geometry', default='800x600')
    parser.add_argument('--panel-only', action='store_true')
    parser.add_argument('--capture-dir', type=Path)
    args = parser.parse_args()
    bundle = args.bundle.resolve()
    with bundle.open('rb') as stream:
        assert file_digest(stream, 'sha256').hexdigest() == args.sha256
    guest_bundle = '/' + bundle.relative_to(ROOT).as_posix()

    with TemporaryDirectory(dir=ROOT / 'build/zx-smoke', prefix='rill-home-') as directory, private_display() as env, TemporaryFile(dir=ROOT / 'build/zx-smoke') as log:
        scratch = Path(directory)
        for key in ('WAYLAND_SOCKET', 'SESSION_MANAGER', 'ICEAUTHORITY', 'XDG_RUNTIME_DIR'):
            env.pop(key, None)
        env['HOME'] = str(scratch)
        env['XDG_CONFIG_HOME'] = str(scratch / 'config')
        env['XDG_CACHE_HOME'] = str(scratch / 'cache')
        env['XDG_DATA_HOME'] = str(scratch / 'data')
        (scratch / 'lib').mkdir()
        if args.workspace_tiles:
            settings = scratch / 'lib/rill'
            settings.mkdir()
            (settings / 'settings').write_text(f'workspace-count = {args.workspace_count}\n')
        home = '/' + scratch.relative_to(ROOT).as_posix()
        overlay = guest_overlay(args.guest_overlay)
        if args.icon_atlas is not None:
            icons = scratch / 'lib/rill/icons'
            icons.mkdir(parents=True)
            copyfile(args.icon_atlas, icons / 'ui.rgba')
            overlay += f'bind -b {home}/lib /lib; '
        memory = ''
        if args.report_memory:
            memory = "sh -c 'sleep 2; echo RILL_POOLS_AFTER_START; cat /dev/memory; sleep 6; echo RILL_POOLS_AFTER_INTERACTION; cat /dev/memory' &; "
        desktop = 'wm/wm' if args.default_desktop else f'wm/wm -rill {guest_bundle}'
        watcher = ('load std; while {ftest -d .} {if {ftest -f wm-check} '
                   '{cat /prog/1/status > wm-status; rm -f wm-check}; sleep 1}')
        command = f'{overlay}home={home}; cd {home}; {memory}sh -c {watcher!r} &; {desktop}'

        def wm_alive():
            request = scratch / 'wm-check'
            status = scratch / 'wm-status'
            status.unlink(missing_ok=True)
            request.touch()
            def replied():
                if request.exists() or not status.is_file():
                    return False
                fields = status.read_text().split()
                return fields and fields[:2] == ['1', '1'] and fields[-1].split('[')[0] == 'Wm'
            until(replied, 'Window manager PID 1 did not answer its guest status probe', timeout=6)

        pool_override = ('-p', f'main={args.pool}') if args.pool else ()
        app = launch(env, args.emu.resolve(), *pool_override, '-r', ROOT, '-g', args.geometry,
                     '/dis/sh.dis', '-c', command, stdin=subprocess.DEVNULL, stdout=log, stderr=log)

        def tail():
            size = os.fstat(log.fileno()).st_size
            return os.pread(log.fileno(), 4096, max(0, size - 4096))

        def call(*command, data=None, check=True):
            return subprocess.run(command, input=data, env=env, capture_output=True, check=check, timeout=6).stdout

        def frame(check_desktop=True):
            guest_log = tail()
            if check_desktop and any(marker in guest_log for marker in (b'desktop exited', b'desktop panel exited',
                                                                         b'Rill desktop launcher unavailable')):
                raise AssertionError(guest_log.decode(errors='replace'))
            return Image.open(BytesIO(call('import', '-window', window, 'png:-'))).convert('RGB')

        def words(image, bounds=None, *, scale=3, psm='11'):
            if bounds is None:
                bounds = (0, 0, image.width, image.height)
            crop = image.crop(bounds)
            png = BytesIO()
            crop.resize((crop.width * scale, crop.height * scale)).save(png, 'PNG')
            table = call('tesseract', 'stdin', 'stdout', '--psm', psm, 'tsv', data=png.getvalue()).decode()
            for row in csv.DictReader(StringIO(table), delimiter='\t', quoting=csv.QUOTE_NONE):
                if row['text']:
                    yield (row['text'].casefold(), bounds[0] + (2 * int(row['left']) + int(row['width'])) // (2 * scale),
                           bounds[1] + (2 * int(row['top']) + int(row['height'])) // (2 * scale))

        def mouse(x, y):
            return ('mousemove', '--window', window, str(x), str(y))

        def click(x, y):
            call('xdotool', *mouse(x, y), 'sleep', '.05', 'mousedown', '1', 'sleep', '.75', 'mouseup', '1')

        def visible_word(label, bounds=None, *, psm='11'):
            image = frame()
            found = next(((x, y) for word, x, y in words(image, bounds, psm=psm) if word == label), None)
            if found is None and label == 'favorites':
                found = next(((x, y) for word, x, y in words(image, bounds, scale=1, psm=psm)
                              if word == label), None)
            return found

        task_icons = {}

        def task_icon(label):
            template = task_icons.get(label)
            if template is None:
                return None
            image = frame()
            for y in range(4, 16):
                for x in range(92, image.width - 120):
                    patch = image.crop((x, y, x + template.width, y + template.height))
                    if max(high for _, high in ImageChops.difference(patch, template).getextrema()) <= 24:
                        return x + template.width // 2, y + template.height // 2
            return None

        def task_label(label):
            return (visible_word(label, (0, 0, 800, 40), psm='6' if label == 'explorer' else '11')
                    or task_icon(label))

        def task_action(label, action):
            task = until(lambda: task_label(label), f'Rill {label} task missing')
            call('xdotool', *mouse(*task), 'mousedown', '3', 'sleep', '.12', 'mouseup', '3')
            item = until(lambda: visible_word(action, (0, 40, 800, 300)),
                         'Rill task action missing: ' + action)
            click(*item)
            until(lambda: not visible_word('window', (0, 35, 800, 300)),
                  'Task action did not close its context menu: ' + action)
            if action == 'close':
                until(lambda: not task_label(label), f'Rill {label} task pixels remained after Close')
                wm_alive()

        def counter():
            return color_bounds(frame(), (248, 250, 252))

        def right_clock():
            image = frame()
            center = image.width - 44
            points = [x for y in range(17, 30) for x in range(int(center - 35), int(center + 35))
                      if min(image.getpixel((x, y))) > 90]
            return points and abs((min(points) + max(points) + 1) / 2 - center) <= 2

        def active_tile(region=None):
            image = frame()
            left, top, right, bottom = region or (max(0, image.width - 220), 0, image.width - 84, 32)
            points = [(x, y) for y in range(top, bottom) for x in range(left, right)
                      if image.getpixel((x, y)) == (197, 14, 210)]
            if not points:
                return None
            return min(x for x, _ in points), min(y for _, y in points), max(x for x, _ in points) + 1, max(y for _, y in points) + 1

        def workspace_checks():
            until(right_clock, 'Clock text is not at the padded right edge')
            first = until(active_tile, 'Active workspace tile did not paint')
            left, top, right, bottom = first
            step_x, step_y = right - left + 1, bottom - top + 1
            rows = min(2, args.workspace_count)
            columns = (args.workspace_count + rows - 1) // rows
            region = (left, top, left + columns * step_x, top + rows * step_y)
            assert abs(region[2] - (frame().width - 84)) <= 5, 'Workspace tiles do not sit immediately left of clock'
            for index in range(args.workspace_count):
                x = left + (index % columns) * step_x
                y = top + (index // columns) * step_y
                click(x + (right - left) // 2, y + (bottom - top) // 2)
                until(lambda: (box := active_tile(region)) and abs(box[0] - x) <= 1 and abs(box[1] - y) <= 1,
                      f'Workspace {index + 1} did not become active')
                if index:
                    until(lambda: not counter(), 'Window appeared on the wrong workspace')
                else:
                    until(counter, 'Workspace zero did not restore its application')
                until(right_clock, 'Workspace switching moved the clock')
            click(left + (right - left) // 2, top + (bottom - top) // 2)
            until(counter, 'Returning to workspace zero lost its application')
            until(lambda: (box := active_tile(region)) and abs(box[0] - left) <= 1 and abs(box[1] - top) <= 1,
                  'Returning to workspace zero did not update its tile')
            until(right_clock, 'Returning to workspace zero moved the clock')
            if args.capture_dir:
                frame().save(args.capture_dir / 'workspace-tiles.png')
            print(f'RILL_WORKSPACE_TILES_SWITCH_MEMBERSHIP_OK count={args.workspace_count}', flush=True)

        try:
            window = until(lambda: call('xdotool', 'search', '--onlyvisible', '--name', '^inferno$',
                                        check=False).strip(), 'Rill guest X window missing').decode()
            call('xdotool', 'windowfocus', window)
            def find_panel():
                image = frame()
                if args.compact_panel and b'Rill: first frame composed' in tail():
                    if image.getpixel((image.width // 2, 0)) == (16, 18, 26):
                        return 16, 16
                for bounds in ((0, 0, 800, 90), (0, 510, 800, 600)):
                    for word, x, y in words(image, bounds):
                        if word in ('applications', 'apps'):
                            return x, y
                return None

            menu = until(find_panel, 'Rill did not paint the Applications control', timeout=40)
            print('RILL_FIRST_PAINT_OK', menu, flush=True)
            if args.capture_dir:
                args.capture_dir.mkdir(parents=True, exist_ok=True)
                frame().save(args.capture_dir / 'empty-desktop.png')
            click(*menu)
            until(lambda: visible_word('search') or visible_word('favorites'), 'Applications menu did not paint')
            print('RILL_APPLICATIONS_PAINT_OK', flush=True)
            call('xdotool', 'key', 'Escape')
            until(lambda: not (visible_word('search') or visible_word('favorites')), 'Escape did not dismiss menu')

            def search_app(name):
                click(*menu)
                x, y = until(lambda: visible_word('favorites'), 'Applications menu did not reopen')
                call('xdotool', 'type', '--delay', '90', name)
                search_box = (4, y - 54, x - 45, y - 17)
                result_row = (0, y - 13, x - 50, y + 214)

                def find_result():
                    image = frame()
                    query = ''.join(word for word, _, _ in words(image, search_box, scale=3, psm='7'))
                    if query.strip("'‘’\"|") != name.casefold():
                        return None
                    return next(((px, py) for word, px, py in words(image, result_row)
                                 if word == name.casefold()), None)

                button = until(find_result, f'Guest {name} missing from Applications search')
                print('RILL_SEARCH_RESULT_OK', name, button, flush=True)
                click(*button)

            if args.favorites:
                task_icons['counter'] = frame().crop((74, 10, 86, 22))
                click(80, 16)
                until(counter, 'Panel favorite did not launch Counter', timeout=20)
                task_action('counter', 'close')
                until(lambda: not counter(), 'Favorite-launched Counter did not close')
                call('xdotool', *mouse(80, 16), 'mousedown', '3', 'sleep', '.12', 'mouseup', '3')
                remove = until(lambda: visible_word('remove', (0, 25, 400, 200)), 'Favorite unpin menu missing')
                if args.capture_dir:
                    frame().save(args.capture_dir / 'favorite-unpin.png')
                click(*remove)
                favorite_file = scratch / 'lib/rill/favorites'
                until(lambda: favorite_file.exists() and 'favorites-count = 1' in favorite_file.read_text(),
                      'Unpin did not persist the favorites list')
                click(*menu)
                x, y = until(lambda: visible_word('favorites'), 'Applications menu missing for repin')
                call('xdotool', 'type', '--delay', '90', 'Counter')
                result = until(lambda: visible_word('counter', (0, y - 13, x - 50, y + 214)),
                               'Counter result missing for repin')
                call('xdotool', *mouse(*result), 'mousedown', '3', 'sleep', '.12', 'mouseup', '3')
                add = until(lambda: visible_word('add'), 'Favorite pin menu missing')
                click(*add)
                until(lambda: 'favorites-count = 2' in favorite_file.read_text(), 'Pin did not persist')
                call('xdotool', 'key', 'Escape')
                until(lambda: not visible_word('favorites'), 'Applications menu did not close after pin')
                click(80, 16)
                until(counter, 'Repinned favorite did not launch Counter', timeout=20)
                task_action('counter', 'close')
                until(lambda: not counter(), 'Repinned Counter did not close')
                if args.workspace_tiles:
                    until(right_clock, 'Changing favorites moved the clock')
                print('RILL_FAVORITES_LAUNCH_UNPIN_PIN_PERSIST_OK', flush=True)

            search_app('Counter')
            initial = until(counter, 'Rill catalog did not launch Counter', timeout=20)
            print('RILL_CATALOG_LAUNCH_OK', initial, flush=True)
            if args.capture_dir:
                frame().save(args.capture_dir / 'open-application.png')
            if args.workspace_tiles:
                workspace_checks()
                if args.panel_only:
                    print('RILL_RIGHT_CLOCK_PANEL_OK', args.geometry, flush=True)
                    return

            left, top, right, bottom = initial
            click(right - 42, top + 76)
            region = (left + 8, top + 4, right - 8, top + 58)
            increased = frame().crop(region)
            click(left + 45, top + 76)
            until(lambda: ImageChops.difference(increased, frame().crop(region)).getbbox(),
                  'Counter content did not acknowledge mouse input')

            call('xdotool', *mouse(left + 95, top - 10), 'mousedown', '1', 'sleep', '.16',
                 *mouse(left + 185, top + 64), 'sleep', '.16', 'mouseup', '1')
            moved = until(lambda: (box := counter()) and box[0] != left and box, 'Rill guest window did not move')
            left, top, right, bottom = moved
            call('xdotool', *mouse(right - 3, bottom - 3), 'mousedown', '1', 'sleep', '.16',
                 *mouse(right + 59, bottom + 43), 'sleep', '.16', 'mouseup', '1')
            size = (right - left + 62, bottom - top + 46)
            resized = until(lambda: (box := counter()) and (box[2] - box[0], box[3] - box[1]) == size and box,
                            'Rill guest window did not resize')
            print('RILL_WINDOW_MOVE_RESIZE_OK', moved, resized, flush=True)
            left, top, right, bottom = resized
            task_action('counter', 'minimize')
            until(lambda: not counter(), 'Rill guest window did not minimize')
            task = until(lambda: visible_word('counter', (0, 0, 800, 40)), 'Minimized Counter task missing from Rill panel')
            click(*task)
            until(lambda: counter() == resized, 'Rill task did not restore Counter')
            print('RILL_TASK_RESTORE_OK', flush=True)

            if args.desktop_extras:
                search_app('Files')

                def files_window():
                    image = frame()
                    bounds = color_bounds(image, (232, 236, 241))
                    if not bounds or bounds[2] - bounds[0] < 300 or bounds[3] - bounds[1] < 230:
                        return None
                    labels = {word for word, _, _ in words(image, bounds)}
                    return bounds if 'back' in labels and 'actions' in labels else None

                files = until(files_window, 'Rill Files did not paint Explorer', timeout=24)
                print('RILL_EXPLORER_PAINT_OK', files, flush=True)
                until(lambda: visible_word('explorer', (0, 0, 800, 40), psm='6'),
                      'Explorer task missing from Rill panel')
                task = until(lambda: visible_word('counter', (0, 0, 800, 40)), 'Counter task missing with Explorer open')
                click(*task)
                until(lambda: counter() == resized, 'Rill task did not refocus Counter with Explorer open')
                print('RILL_MULTIPLE_APPS_OK', flush=True)

                for cycle in range(1, 4):
                    click(*menu)
                    settings = until(lambda: visible_word('settings', (0, 40, 800, 80)), 'Settings launcher missing')
                    click(*settings)
                    tabs = (35, 48, 765, 102)
                    until(lambda: visible_word('panels', tabs) and visible_word('desktop', tabs),
                          'Rill Settings did not paint Desktop and Panels tabs', timeout=24)
                    image = frame()
                    close_bounds = (image.width - 150, image.height - 75, image.width - 20, image.height - 20)
                    close = until(lambda: visible_word('close', close_bounds), 'Rill Settings close button missing')
                    click(*close)
                    until(lambda: not visible_word('panels', tabs), 'Rill Settings did not close')
                    wm_alive()
                    print(f'RILL_SETTINGS_OK cycle={cycle}', flush=True)

            task_action('counter', 'close')
            until(lambda: not counter(), 'Rill guest window did not close')
            print('RILL_WINDOW_LIFECYCLE_OK', flush=True)
            if args.desktop_extras:
                until(files_window, 'Explorer disappeared after closing Counter')
                for cycle in range(1, 4):
                    click(80, 16)
                    until(counter, 'Favorite did not reopen Counter', timeout=20)
                    task_action('counter', 'close')
                    until(lambda: not counter(), 'Counter window pixels remained after Close')
                    task_action('explorer', 'close')
                    until(lambda: not files_window(), 'Explorer window pixels remained after Close')
                    if cycle < 3:
                        search_app('Files')
                        until(files_window, 'Explorer did not reopen', timeout=20)
                    print(f'RILL_CLOSE_BOTH_WM_ALIVE cycle={cycle}', flush=True)
                click(80, 16)
                bounds = until(counter, 'Favorites stopped launching Counter after close/reopen cycles', timeout=20)
                if args.workspace_tiles:
                    workspace_checks()
                left, top, right, _ = bounds
                region = (left + 8, top + 4, right - 8, top + 58)
                before = frame().crop(region)
                click(right - 42, top + 76)
                until(lambda: ImageChops.difference(before, frame().crop(region)).getbbox(),
                      'Counter input stopped after close/reopen cycles')
                task_action('counter', 'close')
                until(lambda: not counter(), 'Final Counter close left window pixels')
                print('RILL_CLOSE_RECOVERY_INPUT_FAVORITES_WORKSPACES_OK', flush=True)
            assert app.poll() is None
            if args.favorites:
                stop(app)
                app = launch(env, args.emu.resolve(), *pool_override, '-r', ROOT, '-g', args.geometry,
                             '/dis/sh.dis', '-c', command, stdin=subprocess.DEVNULL, stdout=log, stderr=log)
                window = until(lambda: call('xdotool', 'search', '--onlyvisible', '--name', '^inferno$',
                                            check=False).strip(), 'Reloaded guest window missing').decode()
                call('xdotool', 'windowfocus', window)
                until(find_panel, 'Reloaded panel did not paint', timeout=40)
                assert 'favorites-count = 2' in favorite_file.read_text()
                click(80, 16)
                until(counter, 'Saved favorite did not launch after desktop restart', timeout=20)
                if args.capture_dir:
                    frame().save(args.capture_dir / 'favorite-reloaded.png')
                task_action('counter', 'close')
                until(lambda: not counter(), 'Reloaded favorite app did not close')
                print('RILL_FAVORITES_RELOAD_OK', flush=True)
        except AssertionError:
            if args.failure_frame and 'window' in locals() and app.poll() is None:
                frame(check_desktop=False).save(args.failure_frame)
            raise
        finally:
            stop(app)
            if args.report_memory:
                log.seek(0)
                for line in islice((line for line in log if b'ZXHEAP' in line), 4):
                    print(line.decode(errors='replace'), end='')
            print(tail().decode(errors='replace'), end='')


if __name__ == '__main__':
    main()
