#!/usr/bin/env python3
"""Private-display Xvfb test for zx/spree/clients/cards.zx with live stdin updates."""
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
    feed = OUT / 'cards-feed.txt'
    feed.write_text(
        "create 1 0 1 stack\n"
        "set 1 style display\n"
        "set 1 title Tableau\n"
        "create 2 1 1 card\n"
        "set 2 face 1\n"
        "set 2 number 50\n"
        "create 3 1 1 card\n"
        "set 3 face 0\n"
        "create 4 0 1 widget button\n"
        "set 4 command redeal\n"
        "set 4 text Redeal\n"
        "remark Your turn\n"
    )
    command = (
        "wm/wm /zx/sh.dis -c "
        "'{cat /build/dis-app-families/cards-feed.txt; sleep 60} | "
        "zxrun -w /zx/spree/clients/cards.zx; echo CARDS_DONE; sleep 60'"
    )
    log_path = OUT / 'cards-window.log'
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
                'cards private display window missing',
                timeout=20,
            ).decode().splitlines()[0]

            def grab():
                raw = subprocess.check_output(
                    ['import', '-window', window, 'png:-'],
                    env=env, stderr=subprocess.DEVNULL, timeout=10,
                )
                return Image.open(io.BytesIO(raw)).convert('RGB')

            img = until(
                lambda: (lambda im: im if (0, 136, 0) in set(im.getdata()) else None)(grab()),
                'cards green table did not render',
                timeout=20,
            )
            img.save(OUT / 'cards-window.png')
            assert child.poll() is None, log_path.read_text(errors='replace')
            subprocess.run(['xdotool', 'windowfocus', '--sync', window], env=env, check=False, timeout=10)
            time.sleep(1)
            assert child.poll() is None, log_path.read_text(errors='replace')
        finally:
            stop(child)
    text = log_path.read_text(errors='replace')
    assert 'tcltk:' not in text.lower() and 'panic' not in text.lower() and 'CARDS_DONE' not in text, text
    print('cards_window_test: PASS')


if __name__ == '__main__':
    main()
