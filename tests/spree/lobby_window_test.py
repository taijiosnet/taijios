#!/usr/bin/env python3
"""Private-display Xvfb test for zx/spree/clients/lobby.zx with live stdin updates."""
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
    feed = OUT / 'lobby-feed.txt'
    feed.write_text(
        "name Alice\n"
        "create 1 0 1 sessiontype\n"
        "set 1 start othello\n"
        "set 1 title Othello\n"
        "create 2 0 1 session\n"
        "set 2 filename 1\n"
        "set 2 owner Alice\n"
        "set 2 title Othello Table\n"
        "create 3 2 1 invite\n"
        "set 3 name all\n"
        "chat Bob welcome to the lobby\n"
    )
    command = (
        "wm/wm /zx/sh.dis -c "
        "'{cat /build/dis-app-families/lobby-feed.txt; sleep 60} | "
        "zxrun -w /zx/spree/clients/lobby.zx; echo LOBBY_DONE; sleep 60'"
    )
    log_path = OUT / 'lobby-window.log'
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
                'lobby private display window missing',
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
                'lobby window did not paint UI',
                timeout=20,
            )
            img.save(OUT / 'lobby-window.png')
            assert child.poll() is None, log_path.read_text(errors='replace')
            subprocess.run(['xdotool', 'windowfocus', '--sync', window], env=env, check=False, timeout=10)
            time.sleep(1)
            assert child.poll() is None, log_path.read_text(errors='replace')
        finally:
            stop(child)
    text = log_path.read_text(errors='replace')
    assert 'tcltk:' not in text.lower() and 'panic' not in text.lower() and 'LOBBY_DONE' not in text, text
    print('lobby_window_test: PASS')


if __name__ == '__main__':
    main()
