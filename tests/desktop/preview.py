#!/usr/bin/env python3
import argparse
import os
from pathlib import Path
import select
import shutil
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
RILL = ROOT.parents[1] / 'kryonlabs/rill'
OUTPUT = ROOT / 'build/desktop-registry'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--guest', action='store_true')
    args = parser.parse_args()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    for key in ('DISPLAY', 'WAYLAND_DISPLAY', 'WAYLAND_SOCKET', 'XAUTHORITY',
                'DBUS_SESSION_BUS_ADDRESS', 'SESSION_MANAGER', 'ICEAUTHORITY',
                'RILL_XFCE_BUS_ADDRESS', 'RILL_XFCE_CONFIG_HOME', 'RILL_CONTAINED_X11'):
        env.pop(key, None)
    env.update(HARMONY_DESKTOP_RECOVERY='0', YUE_DESKTOP_RECOVERY='0')
    reader, writer = os.pipe()
    server = subprocess.Popen(['Xvfb', '-displayfd', str(writer), '-screen', '0',
                               '1024x768x24', '-nolisten', 'tcp'], env=env, pass_fds=(writer,))
    os.close(writer)
    child = None
    try:
        assert select.select([reader], [], [], 8)[0], 'private Xvfb failed'
        display = os.read(reader, 32).decode().strip()
        assert display.isdecimal()
        env['DISPLAY'] = ':' + display
        if args.guest:
            bundle = OUTPUT / 'rill.zx'
            shutil.copyfile(RILL / 'build/rill.zx', bundle)
            command = [str(ROOT / 'emu/Linux/o.emu'), '-p', 'main=128M', '-r', str(ROOT),
                       '-g', '1024x768', '/zx/sh.dis', '-c',
                       'bind /build/desktop-registry/rill.zx /zx/wm/rill.zx; wm/wm']
            output = OUTPUT / 'guest-applications.png'
        else:
            applications = OUTPUT / 'applications'
            applications.mkdir(exist_ok=True)
            selected = ('wm-clock', 'wm-edit', 'wm-explorer', 'wm-counter', 'wm-tetris',
                        'wm-view', 'wm-calendar', 'wm-taskmgr', 'wm-stopwatch', 'wm-man', 'charon')
            for ident in selected:
                source = ROOT / f'lib/apps/org.taijiosnet.{ident}.desktop'
                if not source.exists():
                    continue
                lines = source.read_text().splitlines()
                for i, line in enumerate(lines):
                    if line.startswith(('Exec=', 'TryExec=')):
                        lines[i] = line.split('=')[0] + '=/bin/true'
                    if line.startswith('Icon='):
                        lines[i] = 'Icon=' + str(ROOT / 'lib/icons/hicolor/48x48/apps' / (line[5:] + '.png'))
                (applications / source.name).write_text('\n'.join(lines) + '\n')
            env.update(RILL_APPLICATION_DIRS=str(applications), HOME=str(OUTPUT),
                       XDG_CONFIG_HOME=str(OUTPUT / 'config'), winsize='720x600')
            command = [str(RILL / 'build/rill-applications')]
            output = OUTPUT / 'native-applications.png'
        with (OUTPUT / ('guest.log' if args.guest else 'native.log')).open('w') as log:
            child = subprocess.Popen(command, env=env, cwd=RILL if not args.guest else ROOT,
                                     stdout=log, stderr=subprocess.STDOUT)
            time.sleep(2)
            query = ['xdotool', 'search', '--onlyvisible', '--pid', str(child.pid)]
            if args.guest:
                query = ['xdotool', 'search', '--onlyvisible', '--class', 'inferno']
            window = ''
            deadline = time.monotonic() + 70
            while time.monotonic() < deadline and child.poll() is None:
                found = subprocess.run(query, env=env, capture_output=True, text=True).stdout.splitlines()
                if found:
                    window = found[0]
                    if not args.guest:
                        break
                if args.guest and window:
                    time.sleep(15)
                    break
                time.sleep(.5)
            assert window and child.poll() is None, 'application failed; inspect bounded log'
            if args.guest:
                property_text = subprocess.check_output(['xprop', '-id', window, '-f', '_NET_WM_ICON', '32c', '_NET_WM_ICON'], env=env, text=True)
                assert '_NET_WM_ICON(CARDINAL)' in property_text and '= 32, 32,' in property_text, 'X11 window icon missing'
                subprocess.run(['xdotool', 'mousemove', '--window', window, '40', '20', 'mousedown', '1', 'sleep', '.2', 'mouseup', '1'],
                               env=env, check=True)
                time.sleep(3)
                subprocess.run(['xdotool', 'mousemove', '--window', window, '400', '190', 'mousedown', '1', 'sleep', '1', 'mouseup', '1'],
                               env=env, check=True)
            else:
                subprocess.run(['xdotool', 'windowsize', window, '720', '600', 'windowmove', window, '0', '0', 'windowfocus', window], env=env, check=True)
                time.sleep(1)
                subprocess.run(['xdotool', 'mousemove', '--window', window, '640', '146', 'mousedown', '1', 'sleep', '.2', 'mouseup', '1'],
                               env=env, check=True)
            time.sleep(4)
            subprocess.run(['import', '-window', window, str(output)], env=env, check=True)
            print(output)
            if args.guest:
                subprocess.run(['xdotool', 'mousemove', '--window', window, '150', '102', 'mousedown', '1', 'sleep', '1', 'mouseup', '1',
                                'type', '--delay', '1000', 'Clock'], env=env, check=True)
                time.sleep(4)
                subprocess.run(['xdotool', 'mousemove', '--window', window, '150', '146', 'mousedown', '1', 'sleep', '1', 'mouseup', '1'],
                               env=env, check=True)
                time.sleep(8)
                launched = OUTPUT / 'guest-clock.png'
                subprocess.run(['import', '-window', window, str(launched)], env=env, check=True)
                print(launched)
    finally:
        os.close(reader)
        for process in (child, server):
            if process is not None and process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=8)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)


if __name__ == '__main__':
    main()
