#!/usr/bin/env python3
"""Exercise the installed ZX and Dis clocks in an owned Xvfb display."""

import io
import math
import os
from pathlib import Path
import select
import signal
import subprocess
import time

from PIL import Image, ImageChops


ROOT = Path(__file__).resolve().parents[2]
BLUE = (0, 0, 255)


def wait_for(probe, message, seconds=8):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        result = probe()
        if result:
            return result
        time.sleep(0.1)
    raise AssertionError(message)


def stop(process):
    if process.poll() is None:
        os.killpg(process.pid, signal.SIGTERM)
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
    process.wait(timeout=5)


def face_center(image):
    # Both versions use a 100px face with four cardinal marks 42px from center.
    pix = image.load()
    for y in range(3, image.height - 85):
        for x in range(44, image.width - 44):
            if (pix[x, y] == BLUE and pix[x - 42, y + 42] == BLUE
                    and pix[x + 42, y + 42] == BLUE and pix[x, y + 84] == BLUE):
                return x, y + 42
    return None


def hand_at(image, center, radius, step, blue):
    angle = step * math.tau / 60
    x = round(center[0] + radius * math.sin(angle))
    y = round(center[1] - radius * math.cos(angle))
    return any(
        r <= 6 and g <= 6 and abs(b - blue) <= 8
        for dy in (-1, 0, 1) for dx in (-1, 0, 1)
        for r, g, b in [image.getpixel((x + dx, y + dy))]
    )


def check_clock(env, zx):
    # Set UTC to 02:44:47 and select a daylight offset of +03:00. The
    # namespace and clock offset belong to this single emulator process.
    setup = "echo 9887000000 >/dev/time; echo 'EET 7200 EEST 10800 0 100000000' >/env/timezone"
    app = "zxrun -w /dis/wm/clock.zx" if zx else "/dis/wm/clock.dis"
    child = subprocess.Popen(
        [ROOT / 'Linux/386/bin/emu', '-r', ROOT, '-g', '800x600', 'wm/wm', 'sh',
         '-c', f'{setup}; {app}; echo CLOCK_CLOSED'],
        env=env, start_new_session=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    name = 'ZX' if zx else 'Dis'

    def capture():
        data = subprocess.check_output(['import', '-window', window, 'png:-'], env=env, timeout=5)
        return Image.open(io.BytesIO(data)).convert('RGB')

    try:
        def window_id():
            found = subprocess.run(['xdotool', 'search', '--onlyvisible', '--name', '^inferno$'],
                                   env=env, capture_output=True, text=True, timeout=4).stdout.splitlines()
            return found[0] if len(found) == 1 else None

        window = wait_for(window_id, f'{name} emulator window missing')

        def initial():
            image = capture()
            center = face_center(image)
            if center and hand_at(image, center, 26, 44, 187) and hand_at(image, center, 17, 29, 85):
                return center, image.crop((center[0] - 40, center[1] - 40, center[0] + 40, center[1] + 40))
            return None

        center, before = wait_for(initial, f'{name} face at guest local time 05:44 missing')
        x, y = center
        interior = (x - 40, y - 40, x + 40, y + 40)

        def updated():
            image = capture()
            return (hand_at(image, center, 29, 45, 187)
                    and ImageChops.difference(before, image.crop(interior)).getbbox())

        wait_for(updated, f'{name} Clock never reached 05:45 while idle', seconds=34)
        subprocess.run(['xdotool', 'mousemove', '--sync', '--window', window, str(x + 43), str(y - 60),
                        'mousedown', '1', 'sleep', '0.15', 'mouseup', '1'],
                       env=env, check=True, timeout=4)
        wait_for(lambda: face_center(capture()) is None, f'{name} clock did not close')
        transcript = bytearray()

        def returned():
            ready, _, _ = select.select([child.stdout], [], [], 0)
            if ready:
                transcript.extend(os.read(child.stdout.fileno(), 4096))
            return b'CLOCK_CLOSED\n' in transcript

        wait_for(returned, f'{name} launch did not return to the guest shell')
        if zx:
            assert b'0\n' in transcript.splitlines(keepends=True), transcript[:512]
        print(f'Clock {name}: guest daylight time, idle minute update, and close passed', flush=True)
    finally:
        stop(child)
        errors = child.stderr.read(4096).decode('utf-8', 'replace').strip()
        if errors:
            print(errors)
        child.stdout.close()
        child.stderr.close()


def main():
    env = os.environ.copy()
    for name in ('DISPLAY', 'WAYLAND_DISPLAY', 'XAUTHORITY', 'DBUS_SESSION_BUS_ADDRESS',
                 'XDG_RUNTIME_DIR', 'SESSION_MANAGER'):
        env.pop(name, None)
    env['HARMONY_DESKTOP_RECOVERY'] = '0'
    reader, writer = os.pipe()
    xvfb = subprocess.Popen(['Xvfb', '-displayfd', str(writer), '-screen', '0', '1024x768x24',
                             '-nolisten', 'tcp', '-noreset'],
                            pass_fds=(writer,), env=env, start_new_session=True)
    os.close(writer)
    try:
        ready, _, _ = select.select([reader], [], [], 6)
        display = os.read(reader, 32).strip() if ready else b''
        assert display.isdigit(), 'private Xvfb launch failed'
        env['DISPLAY'] = ':' + display.decode('ascii')
        check_clock(env, zx=True)
        check_clock(env, zx=False)
    finally:
        os.close(reader)
        stop(xvfb)


if __name__ == '__main__':
    main()
