#!/usr/bin/env python3
"""Private-display Xvfb test for dis/grid/blurdemo.zx."""
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
    command = "wm/wm /dis/sh.dis -c 'zxrun -w /dis/grid/blurdemo.zx /icons/inferno.bit; echo BLURDEMO_DONE; sleep 60'"
    log_path = OUT / 'blurdemo-window.log'
    with private_display() as env, log_path.open('w+b') as log:
        child = launch(env, emu, '-p', 'main=128M', '-r', ROOT,
                       '-g', '800x600', '/dis/sh.dis', '-c', command,
                       stdin=subprocess.DEVNULL, stdout=log, stderr=log)
        try:
            window = until(
                lambda: subprocess.run(
                    ['xdotool', 'search', '--onlyvisible', '--class', 'inferno'],
                    env=env, capture_output=True
                ).stdout.strip(),
                'blurdemo private display window missing',
                timeout=20,
            ).decode().splitlines()[0]

            def grab():
                raw = subprocess.check_output(
                    ['import', '-window', window, 'png:-'],
                    env=env, stderr=subprocess.DEVNULL, timeout=10,
                )
                return Image.open(io.BytesIO(raw)).convert('RGB')

            # Wait until BlurDemo paints its widgets (more than 4 distinct colors in the frame).
            img = until(
                lambda: (lambda im: im if len(im.getcolors(maxcolors=256) or [0]*5) > 4 else None)(grab()),
                'blurdemo window did not paint UI',
                timeout=20,
            )
            img.save(OUT / 'blurdemo-window.png')
            assert child.poll() is None, log_path.read_text(errors='replace')
            # Exercise keyboard/focus input on the live window.
            subprocess.run(['xdotool', 'windowfocus', '--sync', window], env=env, check=False, timeout=10)
            subprocess.run(['xdotool', 'mousemove', '--window', window, '120', '40', 'click', '1'], env=env, check=False, timeout=10)
            time.sleep(1)
            assert child.poll() is None, log_path.read_text(errors='replace')
        finally:
            stop(child)
    text = log_path.read_text(errors='replace')
    assert 'syntax error' not in text.lower() and 'panic' not in text.lower() and 'fatal' not in text.lower() and 'BLURDEMO_DONE' not in text, text
    print('blurdemo_window_test: PASS')


if __name__ == '__main__':
    main()
