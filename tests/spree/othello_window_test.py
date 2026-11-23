#!/usr/bin/env python3
"""Private-display Xvfb test for dis/spree/clients/othello.zx with live stdin updates."""
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


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    emu = ROOT / 'emu/Linux/o.emu'
    if not emu.exists():
        emu = ROOT / 'Linux/386/bin/emu'
    for key in ('WAYLAND_SOCKET', 'SESSION_MANAGER', 'ICEAUTHORITY', 'XDG_RUNTIME_DIR'):
        os.environ.pop(key, None)
    # Write initial Othello board state to a fixture file and feed on stdin.
    feed = OUT / 'othello-feed.txt'
    feed.write_text(
        "create 0 -1 board\n"
        "set 0 members Alice Bob\n"
        "set 0 turn 0\n"
        "set 0 dd 0\n"
        "set 0 de 1\n"
        "set 0 ed 1\n"
        "set 0 ee 0\n"
    )
    command = (
        "wm/wm /dis/sh.dis -c "
        "'{cat /build/dis-app-families/othello-feed.txt; sleep 60} | "
        "zxrun -w /dis/spree/clients/othello.zx; echo OTHELLO_DONE; sleep 60'"
    )
    log_path = OUT / 'othello-window.log'
    with private_display() as env, log_path.open('w+b') as log:
        child = launch(env, emu, '-p', 'main=128M', '-r', ROOT,
                       '-g', '640x480', '/dis/sh.dis', '-c', command,
                       stdin=subprocess.DEVNULL, stdout=log, stderr=log)
        try:
            window = until(
                lambda: subprocess.run(
                    ['xdotool', 'search', '--onlyvisible', '--class', 'inferno'],
                    env=env, capture_output=True
                ).stdout.strip(),
                'othello private display window missing',
                timeout=20,
            ).decode().splitlines()[0]

            def grab():
                raw = subprocess.check_output(
                    ['import', '-window', window, 'png:-'],
                    env=env, stderr=subprocess.DEVNULL, timeout=10,
                )
                return Image.open(io.BytesIO(raw)).convert('RGB')

            # Wait for green board (#008800) + white/black pieces to render
            img = until(
                lambda: (lambda im: im if (0, 136, 0) in set(im.getdata()) else None)(grab()),
                'othello green board did not render',
                timeout=20,
            )
            img.save(OUT / 'othello-window.png')
            assert child.poll() is None, log_path.read_text(errors='replace')
            subprocess.run(['xdotool', 'windowfocus', '--sync', window], env=env, check=False, timeout=10)
            time.sleep(1)
            assert child.poll() is None, log_path.read_text(errors='replace')
        finally:
            stop(child)
    text = log_path.read_text(errors='replace')
    assert 'tcltk:' not in text.lower() and 'panic' not in text.lower() and 'OTHELLO_DONE' not in text, text
    print('othello_window_test: PASS')


if __name__ == '__main__':
    main()
