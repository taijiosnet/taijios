#!/usr/bin/env python3
"""Exercise the Task Manager capabilities in a disposable TaijiOS guest."""
import argparse
import os
import re
import select
import subprocess
import sys
import time
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[2]
EMU = ROOT / 'Linux/386/bin/emu'

PROBE = r'''
Tasks :: #import "taijios_tasks";
Args :: #import "taijios_args";

FindSleeper :: (rows: s32) -> s32 {
    fields: [4]s64;
    module: [64]u8;
    user: [64]u8;
    for index: cast(s32)0..rows - 1 {
        if Tasks.TaskAt(index, fields[:], module[:], user[:]) != 0 { return -1 }
        if module[0] == 83 && module[1] == 108 && module[2] == 101 &&
            module[3] == 101 && module[4] == 112 && module[5] == 0 {
            return cast(s32)fields[0];
        }
    }
    return -1;
}

main :: () -> s32 {
    if Args.Count() > 0 {
        if Tasks.Capture() != -1 { return 11 }
        print("TASK_NAMESPACE_OK\n");
        return 0;
    }
    fields: [4]s64;
    module: [64]u8;
    user: [64]u8;
    if Tasks.PoolAt(0, fields[:]) != -1 || Tasks.Terminate(1) != -1 { return 12 }
    rows := Tasks.Capture();
    if rows <= 0 || Tasks.PoolAt(0, fields[:]) != 0 { return 13 }
    if fields[1] != 32 * 1024 * 1024 || fields[0] <= 0 { return 14 }
    for pool: cast(s32)0..2 {
        code := Tasks.PoolAt(pool, fields[:]);
        if code != 0 || fields[0] < 0 || fields[1] <= 0 ||
            fields[2] < fields[0] || fields[2] > fields[1] { return 14 }
    }
    if Tasks.TaskAt(rows, fields[:], module[:], user[:]) != -1 ||
        Tasks.TaskAt(0, fields[:3], module[:], user[:]) != -1 ||
        Tasks.TaskAt(0, fields[:], module[:63], user[:]) != -1 ||
        Tasks.PoolAt(3, fields[:]) != -1 { return 15 }
    last: s64;
    for index: cast(s32)0..rows - 1 {
        if Tasks.TaskAt(index, fields[:], module[:], user[:]) != 0 ||
            fields[0] <= last || fields[2] < 0 || fields[2] > 7 || user[0] == 0 { return 16 }
        last = fields[0];
    }
    sleeper := FindSleeper(rows);
    if sleeper <= 0 { return 17 }
    status := Tasks.Terminate(sleeper);
    if status != 0 { print("terminate status %\n", status); return 18 }
    if FindSleeper(rows) != sleeper || Tasks.Terminate(sleeper) != -2 { return 19 }

    start: s64;
    for pass: 0..127 {
        rows = Tasks.Capture();
        if rows <= 0 || Tasks.PoolAt(0, fields[:]) != 0 { return 20 }
        if pass == 0 { start = fields[0]; }
        if fields[0] > start + 1024 * 1024 || fields[2] > fields[1] { return 21 }
    }
    if FindSleeper(rows) != -1 { return 22 }
    print("TASK_BRIDGE_OK: ordered snapshot, 3 pools, native kill, stale PID, 128 bounded refreshes\n");
    return 0;
}
'''

CPU_PROBE = r'''
Tasks :: #import "taijios_tasks";

main :: () -> s32 {
    rows := Tasks.Capture();
    stamp := Tasks.SampleNanos();
    if rows <= 0 || stamp <= 0 { return 1 }
    fields: [7]s64;
    module: [64]u8;
    user: [64]u8;
    for index: cast(s32)0..rows - 1 {
        if Tasks.TaskAt(index, fields[:], module[:], user[:]) != 0 { return 2 }
        if (module[0] == 67 && module[1] == 112) || (module[0] == 83 && module[1] == 108) {
            print("CPU % % % % % %\n", module[0], fields[0], fields[4], fields[5], stamp, fields[6]);
        }
    }
    return 0;
}
'''

BUSY_DIS = '''implement CpuBusy;
include "sys.m";
include "draw.m";
CpuBusy: module { init: fn(nil: ref Draw->Context, nil: list of string); };
init(nil: ref Draw->Context, nil: list of string)
{
    sys := load Sys Sys->PATH;
    start := sys->millisec();
    while(sys->millisec() - start < 4200) {
        for(i := 0; i < 10000; i++)
            ;
    }
}
'''


def check_bridge(emu, overlay):
    with TemporaryDirectory(dir=ROOT / 'build/zx-smoke', prefix='taskmgr-') as directory:
        directory = Path(directory)
        fixture = directory / 'task_probe.zi'
        fixture.write_text(PROBE, encoding='utf-8')
        image = directory / 'task_probe.zx'
        subprocess.run(['zi2zx', '--root', directory, '--module-path', ROOT / 'appl/cmd',
                        '--bind-host', 'taijios_tasks', '--bind-host', 'taijios_args',
                        '--entry', 'task_probe:main', '-o', image, fixture], check=True)
        guest_image = '/' + str(image.relative_to(ROOT))
        for setup, arguments, expected in (
            ("bind '#p' /prog; sleep 5 &; sleep 1;", '', 'TASK_BRIDGE_OK'),
            ('bind /usr /prog;', 'masked', 'TASK_NAMESPACE_OK'),
        ):
            proc = subprocess.run([emu, '-p', 'main=32M', '-r', ROOT, '/zx/sh.dis', '-c',
                                   f'{overlay}{setup} zxrun {guest_image} {arguments}'],
                                  start_new_session=True, text=True, capture_output=True, timeout=15)
            assert proc.returncode in (0, -9), proc
            assert not proc.stderr, proc.stderr
            assert expected in proc.stdout and proc.stdout.endswith('\n0\n'), proc.stdout
            print(proc.stdout.strip(), flush=True)


def check_cpu(emu, overlay):
    with TemporaryDirectory(dir=ROOT / 'build/zx-smoke', prefix='task-cpu-') as folder:
        scratch = Path(folder)
        source = scratch / 'cpu_busy.b'
        source.write_text(BUSY_DIS, encoding='utf-8')
        busy = scratch / 'cpu_busy.dis'
        subprocess.run([ROOT / 'Linux/386/bin/limbo', '-I', ROOT / 'module', '-o', busy, source], check=True)
        source = scratch / 'cpu_probe.zi'
        source.write_text(CPU_PROBE, encoding='utf-8')
        image = scratch / 'cpu_probe.zx'
        subprocess.run(['zi2zx', '--root', scratch, '--module-path', ROOT / 'appl/cmd',
                        '--bind-host', 'taijios_tasks', '--entry', 'cpu_probe:main', '-o', image, source], check=True)
        guest = '/' + scratch.relative_to(ROOT).as_posix()
        proc = subprocess.run([emu, '-p', 'main=32M', '-r', ROOT, '/zx/sh.dis', '-c',
                               f"{overlay}bind '#p' /prog; {guest}/cpu_busy.dis &; sleep 8 &; sleep 1; "
                               f'zxrun {guest}/cpu_probe.zx; sleep 1; zxrun {guest}/cpu_probe.zx'],
                              start_new_session=True, text=True, capture_output=True, timeout=12)
        assert proc.returncode in (0, -9) and not proc.stderr, proc
        rows = [tuple(map(int, line.split()[1:])) for line in proc.stdout.splitlines() if line.startswith('CPU ')]
        assert len(rows) == 4, proc.stdout
        deltas = []
        for kind in (ord('C'), ord('S')):
            before, after = [row for row in rows if row[0] == kind]
            _, pid, cpu, incarnation, stamp, uncertainty = before
            _, next_pid, next_cpu, next_incarnation, next_stamp, next_uncertainty = after
            assert next_pid == pid and next_incarnation == incarnation and incarnation > 0, rows
            assert cpu >= 0 and next_stamp > stamp > 0 and min(uncertainty, next_uncertainty) >= 0, rows
            delta = next_cpu - cpu
            assert 0 <= delta <= next_stamp - stamp + uncertainty + next_uncertainty, rows
            deltas.append(delta)
        busy_ns, sleep_ns = deltas
        assert busy_ns > 20_000_000 and sleep_ns == 0, rows
        print(f'TASK_CPU_OK: busy Dis used {busy_ns / 1e6:.2f} ms, sleeping Dis used 0 ms')


def check_gui(emu, overlay, legacy, resize):
    from PIL import Image, ImageChops
    from kryon_apps_test import wait_start
    from test_logwindow import private_display
    from test_tcltk import color_bounds, launch, stop, until

    with private_display() as env:
        # The only sleeper this test can select belongs to this disposable guest.
        toolbar = 'wm/toolbar -l' if legacy else 'wm/toolbar'
        guest = launch(env, emu, '-p', 'main=32M', '-r', ROOT, '-g', '800x600', '/zx/sh.dis', '-c',
                       f"{overlay}wm/wm /zx/sh.dis -c 'sleep 90 &; ps; {toolbar}'",
                       stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        def command(*args, data=None, check=True):
            return subprocess.run(args, input=data, env=env, capture_output=True,
                                  check=check, timeout=6).stdout

        def capture():
            data = command('import', '-window', window, 'png:-')
            return Image.open(BytesIO(data)).convert('RGB')

        def words():
            image = capture()
            png = BytesIO()
            image.resize((image.width * 2, image.height * 2)).save(png, 'PNG')
            tsv = command('tesseract', 'stdin', 'stdout', '--psm', '11', 'tsv', data=png.getvalue())
            items = []
            for line in tsv.decode().splitlines()[1:]:
                cells = line.split('\t')
                if len(cells) == 12 and cells[11]:
                    x, y, width, height = (int(value) for value in cells[6:10])
                    items.append((cells[11].lower().strip('.,:'), (x + width // 2) // 2,
                                  (y + height // 2) // 2))
            return items

        def find(items, label, top=0, bottom=600):
            return next(((x, y) for text, x, y in items
                         if text == label and top <= y < bottom), None)

        def mouse(x, y):
            return ('mousemove', '--window', window, str(x), str(y))

        def click(x, y):
            command('xdotool', *mouse(x, y), 'sleep', '.04', 'mousedown', '1',
                    'sleep', '.12', 'mouseup', '1')

        def wait_word(label, top=0, bottom=600):
            return until(lambda: find(words(), label, top, bottom), f'Task Manager missing {label}')

        def visible_pids(items):
            return [int(text) for text, _, _ in sorted(
                (word for word in items if word[0].isdigit() and 163 <= word[1] < 195
                 and 132 <= word[2] < 416), key=lambda word: word[2])]

        def open_taskmgr():
            start, group, item = ((13, 582), (30, 507), (150, 538)) if legacy else ((36, 584), (45, 455), (230, 455))
            command('xdotool', *mouse(*start), 'sleep', '.04', 'mousedown', '1', 'sleep', '.22',
                    *mouse(*group), 'sleep', '.18', *mouse(*item), 'sleep', '.12', 'mouseup', '1')
            wait_word('manager', 0, 23)

        def close_taskmgr():
            click(*wait_word('file', 23, 46))
            click(*wait_word('exit', 45, 170))
            until(lambda: not find(words(), 'manager', 0, 23), 'Task Manager did not close')
            assert guest.poll() is None, 'Closing Task Manager exited the guest desktop'

        def resize_taskmgr(desktop, area):
            def bounds():
                return ImageChops.difference(desktop, capture().crop(area)).getbbox()

            _, end_y = wait_word('end', 420, 480)
            box = bounds()
            assert box and box[2] - box[0] >= 395, box
            for dx, dy in ((28, 24), (-28, -24)):
                x, y = box[2] - 3, box[3] - 3
                command('xdotool', *mouse(x, y), 'sleep', '.10', 'mousedown', '1', 'sleep', '.16',
                        *mouse(x + dx, y + dy), 'sleep', '.20', 'mouseup', '1')
                expected = (box[0], box[1], box[2] + dx, box[3] + dy)
                # The window outline can reach the new bounds before the guest
                # draws again. Check that its bottom controls have reflowed.
                end_y += dy

                def reflowed():
                    return bounds() == expected and find(words(), 'end', end_y - 3, end_y + 4)

                try:
                    until(reflowed, f'Task Manager did not reflow at {expected}')
                except AssertionError as error:
                    raise AssertionError(f'{error}, started at {box}, observed {bounds()}') from None
                wait_word('pid', 103, 132)
                box = expected

        try:
            window = until(lambda: command('xdotool', 'search', '--onlyvisible', '--name',
                                           '^inferno$', check=False).strip(), 'Guest window missing').decode()
            wait_start(capture, legacy)
            ps_output = bytearray()

            def owned_sleeper():
                if select.select([guest.stdout], [], [], 0)[0]:
                    ps_output.extend(os.read(guest.stdout.fileno(), 2048))
                assert len(ps_output) <= 8192, 'Guest ps output exceeded the test bound'
                matches = re.findall(rb'^\s*(\d+)\s+.*Sleep\[\$Sys\]$', ps_output, re.M)
                assert len(matches) <= 1, f'Expected one owned guest sleeper, found {matches}'
                return int(matches[0]) if matches else None

            sleeper = until(owned_sleeper, 'Guest ps did not list the owned sleeper')

            area = (0, 0, 800, 560)
            desktop = capture().crop(area) if resize else None
            open_taskmgr()
            wait_word('sleep', 132, 416)
            before = words()
            assert find(before, 'manager', 0, 23) and find(before, '32', 470, 510), before
            assert sleeper in visible_pids(before), before
            click(*wait_word('pid', 103, 132))

            def sorted_rows():
                items = words()
                pids = visible_pids(items)
                if (len(pids) >= 5 and pids != visible_pids(before) and
                    pids in (sorted(pids), sorted(pids, reverse=True))):
                    return items
                return None

            after = until(sorted_rows, 'Clicking the PID column did not sort guest PIDs')
            row = find(after, 'sleep', 132, 416)
            assert row and find(after, str(sleeper), row[1] - 3, row[1] + 4), after
            click(*row)
            click(*wait_word('end', 428, 461))
            wait_word('warning')
            dialog = words()
            assert find(dialog, 'sleep', 225, 283), dialog
            assert any(text.startswith(f'{sleeper})') and 225 <= y < 283
                       for text, _, y in dialog), dialog
            no_x, no_y = wait_word('no', 280, 335)
            # The danger button's light text is poorly recognized on the red fill.
            # Confirm the modal's exact target, then click that fill beside No.
            red = color_bounds(capture().crop((no_x, no_y - 20, 400, no_y + 20)), (201, 48, 45))
            assert red is not None, 'Task Manager confirmation button missing'
            click(no_x + (red[0] + red[2]) // 2, no_y - 20 + (red[1] + red[3]) // 2)
            until(lambda: not find(words(), 'sleep', 132, 416), 'Owned guest sleeper did not exit')

            click(*wait_word('view', 23, 46))
            click(*wait_word('refresh', 45, 125))
            time.sleep(6)
            refreshed = words()
            assert sleeper not in visible_pids(refreshed) and find(refreshed, '32', 470, 510), refreshed
            if resize:
                resize_taskmgr(desktop, area)
            close_taskmgr()
            if resize:
                open_taskmgr()
                assert 'sleep' not in {text for text, _, y in words() if 132 <= y < 416}
                resize_taskmgr(desktop, area)
                close_taskmgr()
                print('TASK_RESIZE_OK: grew, shrank, repainted, closed, and reopened in the same 32 MiB guest')
            print('TASK_GUI_OK: menu, real guest rows, PID sort, selection, confirmed kill, refresh, close at 32 MiB')
        finally:
            stop(guest)
            diagnostics = guest.stderr.read(8192)
            if diagnostics:
                print(guest.stdout.read(8192).decode(errors='replace'), file=sys.stderr, end='')
            guest.stdout.close()
            guest.stderr.close()
            if diagnostics:
                print(diagnostics.decode(errors='replace'), file=sys.stderr, end='')
        assert not diagnostics, 'Task Manager reported a guest runtime error'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('emu', type=Path, default=EMU, nargs='?')
    parser.add_argument('--gui', action='store_true', help='also test the installed app in private Xvfb')
    parser.add_argument('--cpu', action='store_true', help='also measure CPU for busy and sleeping Dis tasks')
    parser.add_argument('--guest-overlay', type=Path, help='use built guest artifacts from this directory')
    parser.add_argument('--legacy-menu', action='store_true', help='open Task Manager through the Dis toolbar')
    parser.add_argument('--require-window-resize', action='store_true', help='resize, close, and reopen Task Manager')
    args = parser.parse_args()
    for key in ('DISPLAY', 'WAYLAND_DISPLAY', 'XAUTHORITY', 'DBUS_SESSION_BUS_ADDRESS',
                'XDG_RUNTIME_DIR', 'XDG_SESSION_ID', 'SESSION_MANAGER', 'HARMONY_GUEST_DISPLAY'):
        os.environ.pop(key, None)
    os.environ['HARMONY_DESKTOP_RECOVERY'] = '0'
    from kryon_apps_test import guest_overlay
    overlay = guest_overlay(args.guest_overlay)
    check_bridge(args.emu.resolve(), overlay)
    if args.cpu:
        check_cpu(args.emu.resolve(), overlay)
    if args.gui:
        check_gui(args.emu.resolve(), overlay, args.legacy_menu, args.require_window_resize)


if __name__ == '__main__':
    main()
