#!/usr/bin/env python3
"""Private-display Xvfb test for dis/spree/clients/gather.zx with live stdin updates."""
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
    feed = OUT / 'gather-feed.txt'
    feed.write_text(
        "title Othello Table\n"
        "join Alice\n"
        "chat Alice ready to play!\n"
    )
    command = (
        "wm/wm /dis/sh.dis -c "
        "'{cat /build/dis-app-families/gather-feed.txt; sleep 60} | "
        "zxrun -w /dis/spree/clients/gather.zx /n/remote 0; echo GATHER_DONE; sleep 60'"
    )
    log_path = OUT / 'gather-window.log'
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
                'gather private display window missing',
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
                'gather window did not paint UI',
                timeout=20,
            )
            img.save(OUT / 'gather-window.png')
            assert child.poll() is None, log_path.read_text(errors='replace')
            subprocess.run(['xdotool', 'windowfocus', '--sync', window], env=env, check=False, timeout=10)
            time.sleep(1)
            assert child.poll() is None, log_path.read_text(errors='replace')
        finally:
            stop(child)
    text = log_path.read_text(errors='replace')
    assert 'tcltk:' not in text.lower() and 'panic' not in text.lower() and 'GATHER_DONE' not in text, text
    print('gather_window_test: PASS')


if __name__ == '__main__':
    main()
