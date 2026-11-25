#!/usr/bin/env python3
"""Private-display Xvfb tests for grid GUI ZX apps (query.zx, find.zx, blurdemo.zx)."""
import io
import os
from pathlib import Path
import subprocess
import sys
import time
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'build/dis-app-families'
sys.path.insert(0, str(ROOT / 'appl/cmd/tcltk'))
from test_logwindow import private_display
from test_tcltk import launch, stop, until


def run_app(name: str, guest_cmd: str):
    OUT.mkdir(parents=True, exist_ok=True)
    emu = ROOT / 'emu/Linux/o.emu'
    if not emu.exists():
        emu = ROOT / 'Linux/386/bin/emu'
    for key in ('WAYLAND_SOCKET', 'SESSION_MANAGER', 'ICEAUTHORITY', 'XDG_RUNTIME_DIR'):
        os.environ.pop(key, None)
    command = f"wm/wm /zx/sh.dis -c '{guest_cmd}; echo APP_DONE; sleep 60'"
    log_path = OUT / f'{name}-window.log'
    with private_display() as env, log_path.open('w+b') as log:
        child = launch(env, emu, '-p', 'main=128M', '-r', ROOT,
                       '-g', '800x600', '/zx/sh.dis', '-c', command,
                       stdin=subprocess.DEVNULL, stdout=log, stderr=log)
        try:
            window = until(
                lambda: subprocess.run(
                    ['xdotool', 'search', '--onlyvisible', '--class', 'inferno'],
                    env=env, capture_output=True
                ).stdout.strip(),
                f'{name} private display window missing',
                timeout=20,
            ).decode().splitlines()[0]

            def grab():
                raw = subprocess.check_output(
                    ['import', '-window', window, 'png:-'],
                    env=env, stderr=subprocess.DEVNULL, timeout=10,
                )
                return Image.open(io.BytesIO(raw)).convert('RGB')

            img = until(
                lambda: (lambda im: im if len(im.getcolors(maxcolors=256) or [0]*5) > 4 else None)(grab()),
                f'{name} window did not paint UI',
                timeout=20,
            )
            img.save(OUT / f'{name}-window.png')
            assert child.poll() is None, log_path.read_text(errors='replace')
            subprocess.run(['xdotool', 'windowfocus', '--sync', window], env=env, check=False, timeout=10)
            time.sleep(1)
            assert child.poll() is None, log_path.read_text(errors='replace')
        finally:
            stop(child)
    text = log_path.read_text(errors='replace')
    assert 'tcltk:' not in text.lower() and 'panic' not in text.lower() and 'APP_DONE' not in text, text
    print(f'{name}_window_test: PASS')


def main():
    apps = sys.argv[1:] or ['query', 'find']
    specs = {
        'query': 'zxrun -w /zx/grid/query.zx',
        'find': 'zxrun -w /zx/grid/find.zx -a resource demo Open echo',
        'blurdemo': 'zxrun -w /zx/grid/blurdemo.zx /icons/inferno.bit',
        'fbrowse': 'zxrun -w /zx/grid/lib/fbrowse.zx Files / /icons',
    }
    for app in apps:
        run_app(app, specs[app])


if __name__ == '__main__':
    main()
