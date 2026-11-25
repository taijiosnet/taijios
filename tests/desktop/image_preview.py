#!/usr/bin/env python3
import argparse
from contextlib import suppress
import fcntl
import io
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / 'build/desktop-registry'
RILL = ROOT.parents[1] / 'kryonlabs/rill'
sys.path.insert(0, str(ROOT / 'appl/cmd/tcltk'))
from test_logwindow import private_display
from test_tcltk import launch, stop, until


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=('viewer', 'explorer', 'desktop'), default='viewer')
    parser.add_argument('--file', default='reference.png', choices=('reference.png', 'reference.jpg', 'progressive.jpg', 'large.png', 'broken.png'))
    parser.add_argument('--activate', nargs=2, type=int)
    parser.add_argument('--zoom', action='store_true')
    parser.add_argument('--resize', action='store_true')
    parser.add_argument('--cancel', action='store_true')
    args = parser.parse_args()
    if args.cancel: assert args.mode == "viewer" and args.file == "large.png"
    overlay = OUTPUT / 'image-overlay'
    overlay.mkdir(parents=True, exist_ok=True)
    home = OUTPUT / 'image-home'
    desktop = home / 'Desktop'
    desktop.mkdir(parents=True, exist_ok=True)
    for name in ('reference.png', 'reference.jpg', 'large.png'):
        shutil.copyfile(OUTPUT / 'images' / name, desktop / name)
    (OUTPUT / 'images/broken.png').write_bytes(b'\x89PNG\r\n\x1a\ntruncated')
    for name in ('wm.dis', 'toolbar.dis', 'zxrun.dis'):
        shutil.copyfile(ROOT / 'build/tests/guest-workspaces' / name, overlay / name)
    shutil.copyfile(ROOT / 'appl/wm/view.zx', overlay / 'view.zx')
    shutil.copyfile(ROOT.parents[1] / 'kryonlabs/explorer/build/explorer.zx', overlay / 'explorer.zx')
    if args.mode == 'desktop':
        with (RILL / 'build/taiji-package.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            shutil.copyfile(RILL / 'build/rill.zx', overlay / 'rill.zx')
    guest = '/build/desktop-registry/image-overlay'
    home_suffix = '/Desktop' if args.mode == 'explorer' else ''
    setup = f'home=/build/desktop-registry/image-home{home_suffix}; bind -b {guest} /zx; bind -b {guest} /zx/wm; '
    if args.mode == 'desktop':
        command = setup + f'wm/wm -rill {guest}/rill.zx'
    else:
        operand = f'/build/desktop-registry/images/{args.file}' if args.mode == 'viewer' else ''
        app = 'view' if args.mode == 'viewer' else 'explorer'
        command = setup + f"wm/wm /zx/sh.dis -c 'wm/toolbar &; zxrun -w {guest}/{app}.zx {operand}; sleep 90'"
    for key in ('WAYLAND_SOCKET', 'SESSION_MANAGER', 'ICEAUTHORITY', 'XDG_RUNTIME_DIR'):
        os.environ.pop(key, None)
    with private_display() as env, (OUTPUT / f'image-{args.mode}.log').open('w+b') as log:
        child = launch(env, ROOT / 'emu/Linux/o.emu', '-p', 'main=128M', '-r', ROOT,
                       '-g', '1024x768', '/zx/sh.dis', '-c', command,
                       stdin=subprocess.DEVNULL, stdout=log, stderr=log)
        def query(*values):
            return subprocess.check_output(values, env=env, stderr=subprocess.DEVNULL, timeout=10)
        def tail():
            size = os.fstat(log.fileno()).st_size
            return os.pread(log.fileno(), 4096, max(0, size-4096)).decode(errors='replace')
        try:
            window = until(lambda: subprocess.run(['xdotool', 'search', '--onlyvisible', '--class', 'inferno'], env=env, capture_output=True).stdout.strip(), 'private image guest window missing', timeout=20).decode().splitlines()[0]
            def screenshot():
                return Image.open(io.BytesIO(query('import', '-window', window, 'png:-'))).convert('RGB')
            if args.cancel:
                until(lambda: screenshot().getpixel((100, 200)) == (80, 86, 90), 'loading frame missing', timeout=30)
                loading = screenshot().crop((8, 520, 650, 548)).tobytes()
                query('xdotool', 'windowfocus', '--sync', window)
                query('xdotool', 'mousemove', '--window', window, '200', '200', 'mousedown', '1', 'sleep', '1', 'mouseup', '1')
                query('xdotool', 'key', 'Escape')
                until(lambda: screenshot().crop((8, 520, 650, 548)).tobytes() != loading, 'Escape did not cancel decoding', timeout=8)
                assert screenshot().getpixel((100, 200)) == (80, 86, 90), 'cancelled image was displayed'
                query('import', '-window', window, str(OUTPUT / 'image-viewer-cancelled.png'))
                query('xdotool', 'mousemove', '--window', window, '200', '60', 'mousedown', '1', 'sleep', '1', 'mouseup', '1', 'key', 'End')
                query('xdotool', 'key', '--repeat', str(len('/build/desktop-registry/images/large.png')), '--repeat-delay', '120', 'BackSpace')
                query('xdotool', 'type', '--clearmodifiers', '--delay', '120', '/build/desktop-registry/images/reference.png')
                query('xdotool', 'key', 'Return')
                until(lambda: screenshot().getpixel((100, 200))[0] > 180 and screenshot().getpixel((100, 200))[1] < 80, 'viewer did not recover after cancellation', timeout=25)
            else:
                time.sleep(18)
            assert child.poll() is None, tail()
            if args.activate:
                query('import', '-window', window, str(OUTPUT / f'image-{args.mode}-before.png'))
                query('xdotool', 'mousemove', '--window', window, *map(str, args.activate), 'mousedown', '1', 'sleep', '1', 'mouseup', '1')
                time.sleep(1)
                query('xdotool', 'key', 'Return')
                time.sleep(12)
                until(lambda: screenshot().getpixel((100, 200))[0] > 180 and screenshot().getpixel((100, 200))[1] < 80, 'activated image did not display', timeout=25)
            if args.mode == 'viewer' and args.file != 'broken.png' and not args.cancel:
                if args.file == 'large.png':
                    until(lambda: screenshot().getpixel((350, 300)) == (20, 80, 200), 'large image did not display', timeout=75)
                else:
                    until(lambda: screenshot().getpixel((100, 200))[0] > 180 and screenshot().getpixel((100, 200))[1] < 80, 'image did not display', timeout=25)
            if args.resize:
                query('xdotool', 'mousemove', '--window', window, '719', '553', 'mousedown', '1', 'sleep', '.5', 'mousemove', '--window', window, '900', '680', 'sleep', '1', 'mouseup', '1')
                until(lambda: Image.open(io.BytesIO(query('import', '-window', window, 'png:-'))).convert('RGB').getpixel((800, 200))[1] > 200 and Image.open(io.BytesIO(query('import', '-window', window, 'png:-'))).convert('RGB').getpixel((800, 200))[0] < 40, 'image contents did not resize', timeout=45)
            if args.zoom:
                query('xdotool', 'mousemove', '--window', window, '108', '95', 'mousedown', '1', 'sleep', '1', 'mouseup', '1')
                until(lambda: Image.open(io.BytesIO(query('import', '-window', window, 'png:-'))).convert('RGB').getpixel((100, 200)) == (80, 86, 90), '100% did not restore native image size', timeout=45)
            output = OUTPUT / ('image-viewer-cancel-recovery.png' if args.cancel else f'image-{args.mode}-{args.file}.png')
            query('import', '-window', window, str(output))
            print(output, flush=True)
            text = tail()
            if text: print(text, end='', flush=True)
            assert 'ZX execution failed' not in text and 'out of memory' not in text, text
        except Exception:
            with suppress(Exception):
                query('import', '-window', window, str(OUTPUT / f'image-{args.mode}-failure.png'))
            print(tail(), flush=True)
            raise
        finally:
            stop(child)


if __name__ == '__main__':
    main()
