from pathlib import Path
import subprocess
import sys

root = Path.cwd()
emu = root / (sys.argv[1] if len(sys.argv) > 1 else 'emu/Linux/o.emu')
files = root / 'build/zx-smoke'

def run(command):
    proc = subprocess.run([emu, '-r', root, '/dis/sh.dis', '-c', command],
                          start_new_session=True, capture_output=True, text=True, timeout=25)
    print(repr(proc.stdout), repr(proc.stderr), proc.returncode)
    assert proc.returncode in (0, -9)
    return proc

ok = run("echo TAIJIOS_BOOT_OK; bind -c /build/zx-smoke /chan; cd /chan; "
    "zxrun 'hello app.zx' > guest.stdout; echo ZX_RUN_DONE")
assert ok.stdout == "TAIJIOS_BOOT_OK\nZX_RUN_DONE\n" and ok.stderr == ""
assert (files / 'guest.stdout').read_text() == 'Hello from ZX 42\n4294967338\n'
failed = run('/dis/zxrun.dis /build/zx-smoke/bad.zx >[2] /build/zx-smoke/guest.stderr; echo $status; echo DIS_OK')
assert 'zx\n' in failed.stdout and 'DIS_OK\n' in failed.stdout
assert 'invalid ZX image' in (files / 'guest.stderr').read_text()
pipe = run("zxrun '/build/zx-smoke/hello app.zx' | cat; echo PIPE_OK")
assert pipe.stdout == 'Hello from ZX 42\n4294967338\nPIPE_OK\n' and pipe.stderr == ''
missing = run('zxrun /build/zx-smoke/absent.zx >[2] /build/zx-smoke/missing.stderr; echo $status')
assert missing.stdout == 'zx\n' and missing.stderr == ''
assert 'absent.zx' in (files / 'missing.stderr').read_text()


def graphics():
    import io
    import os
    import select
    import signal
    import time
    from collections import deque
    from PIL import Image, ImageChops

    env = {k: v for k, v in os.environ.items() if k not in (
        'DISPLAY', 'WAYLAND_DISPLAY', 'XAUTHORITY', 'DBUS_SESSION_BUS_ADDRESS')}
    env['HARMONY_DESKTOP_RECOVERY'] = '0'
    reader, writer = os.pipe()
    xvfb = subprocess.Popen(['Xvfb', '-displayfd', str(writer), '-screen', '0',
                            '1024x768x24', '-nolisten', 'tcp'],
                           pass_fds=(writer,), env=env)
    os.close(writer)

    def command(*args, **kwargs):
        return subprocess.run(args, env=env, timeout=4, **kwargs)

    def until(probe, description, timeout=10):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            result = probe()
            if result:
                return result
            time.sleep(0.05)
        raise AssertionError(description)

    def launch(app, *args):
        return subprocess.Popen([emu, '-p', 'main=256M', '-r', root, '-g', '800x600',
                                 'wm/wm', app, *args], env=env,
                                start_new_session=True, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)

    def owned_window():
        found = command('xdotool', 'search', '--onlyvisible', '--name', '^inferno$',
                        capture_output=True, text=True).stdout.splitlines()
        return found[0] if len(found) == 1 else None

    def capture(window):
        pixels = command('import', '-window', window, 'png:-',
                         check=True, capture_output=True).stdout
        return Image.open(io.BytesIO(pixels)).convert('RGB')

    def surface(window):
        img = capture(window)
        delta = ImageChops.difference(img, Image.new('RGB', img.size, (248, 250, 252)))
        red, green, blue = delta.split()
        mask = ImageChops.lighter(ImageChops.lighter(red, green), blue)
        box = mask.point(lambda v: 255 if v == 0 else 0).getbbox()
        return (img, box) if box else None

    def click(window, x, y):
        command('xdotool', 'mousemove', '--sync', '--window', window, str(x), str(y),
                'mousedown', '1', 'sleep', '0.15', 'mouseup', '1', check=True)

    def close(window, box):
        click(window, box[2] - 7, box[1] - 10)
        until(lambda: surface(window) is None, 'guest window did not close')

    def output(proc):
        ready, _, _ = select.select([proc.stdout, proc.stderr], [], [], 0)
        for fd in ready:
            block = os.read(fd.fileno(), 4096)
            if block:
                yield fd is proc.stderr, block

    def stop(proc):
        if proc.poll() is None:
            os.killpg(proc.pid, signal.SIGKILL)
        proc.wait(timeout=5)
        proc.stdout.close()
        proc.stderr.close()

    def keyevents():
        proc = launch('zxrun', '-w', '/build/zx-smoke/keyevents.zx')
        transcript = bytearray()

        def read():
            for error, block in output(proc):
                assert not error, block.decode('utf-8', 'replace')
                transcript.extend(block)
            return transcript.decode('utf-8', 'replace').splitlines()

        def expect_keys(expected):
            keys = [line for line in read() if line.startswith('key ')]
            return keys[-len(expected):] == expected

        try:
            window = until(owned_window, 'emulator did not map its X window')
            _, box = until(lambda: surface(window), 'ZX key event canvas missing')
            command('xdotool', 'windowfocus', window, check=True)
            for name, key, bit in [('Shift_L', 340, 1), ('Control_L', 341, 2), ('Alt_L', 342, 4)]:
                command('xdotool', 'keydown', name, 'keydown', 'a', 'keyup', 'a',
                        'keyup', name, check=True)
                expected = [f'key 7 {key} {bit}', f'key 7 65 {bit}',
                            f'key 8 65 {bit}', f'key 8 {key} 0']

                until(lambda: expect_keys(expected), f'{name} press or release did not reach the ZX surface')
            command('xdotool', 'keydown', 'Shift_L', 'keydown', 'Shift_R', 'keyup', 'Shift_L',
                    'keyup', 'Shift_R', check=True)
            until(lambda: expect_keys(['key 7 340 1', 'key 7 344 1', 'key 8 340 1', 'key 8 344 0']),
                  'Shift modifier changed before the last Shift key was released')
            until(lambda: 'text A' in read(), 'shifted text did not reach the ZX surface')
            close(window, box)
            until(lambda: '0' in read(), 'ZX key event fixture did not close cleanly')
            print('ZX X11 keys: physical press and release with Shift, Control and Alt masks')
        except AssertionError:
            print('ZX key event output:', read())
            raise
        finally:
            stop(proc)

    def kryon():
        proc = launch('zxrun', '-w', '/build/zx-smoke/hosted_surface.zx')
        transcript = deque(maxlen=80)
        partial = b''

        def seen(want):
            nonlocal partial
            for error, block in output(proc):
                assert not error, block.decode('utf-8', 'replace')
                *lines, partial = (partial + block).split(b'\n')
                transcript.extend(line.decode('utf-8') for line in lines)
            return any(want(line) for line in transcript)

        try:
            window = until(owned_window, 'emulator did not map its X window')
            before, box = until(lambda: surface(window), 'Kryon frame missing')
            x, y, right, bottom = box
            assert (right - x, bottom - y) == (240, 144), box
            command('xdotool', 'windowfocus', window, check=True)
            click(window, x + 40, y + 55)
            until(lambda: seen(lambda s: s == 'click 1'), 'mouse click did not reach Kryon')
            changed = capture(window)
            assert ImageChops.difference(before.crop((x, y, right, y+35)),
                                         changed.crop((x, y, right, y+35))).getbbox()
            click(window, x + 40, y + 99)
            command('xdotool', 'key', 'eacute', check=True)
            until(lambda: seen(lambda s: s == 'text é'), 'Unicode text did not reach Kryon')
            command('xdotool', 'key', 'x', check=True)
            until(lambda: seen(lambda s: s == 'text éx'), 'ASCII text did not reach Kryon')
            command('xdotool', 'key', 'BackSpace', check=True)
            until(lambda: seen(lambda s: s == 'text é') and transcript.count('text é') == 2,
                  'Backspace did not reach Kryon')
            click(window, right - 22, y - 9)
            command('xdotool', 'mousemove', '--window', window, str(right - 3), str(bottom - 4),
                    'sleep', '0.15', 'mousedown', '1', 'sleep', '0.15', 'mousemove', '--window',
                    window, str(right + 60), str(bottom + 48), 'sleep', '0.15', 'mouseup', '1',
                    check=True)
            until(lambda: seen(lambda s: s.startswith('surface ') and s != 'surface 240 x 144'),
                  'resize did not reach Kryon')
            def resized_surface():
                current = surface(window)
                return current[1] if current and current[1] != box else None

            resized = until(resized_surface, 'resized frame missing')
            close(window, resized)
            until(lambda: seen(lambda s: s == '0'), 'Kryon did not return success on close')
            print('Kryon:', ', '.join(transcript))
        except AssertionError:
            print('Kryon transcript:', ', '.join(transcript))
            raise
        finally:
            for error, block in output(proc):
                print('Kryon stderr:' if error else 'Kryon stdout:', block.decode('utf-8', 'replace').strip())
            stop(proc)

    def stopwatch():
        proc = launch('wm/stopwatch', '-zx')
        status = bytearray()

        def returned():
            for error, block in output(proc):
                assert not error, block.decode('utf-8', 'replace')
                status.extend(block)
            return status == b'0\n'

        try:
            window = until(owned_window, 'emulator did not map its X window')
            before, box = until(lambda: surface(window), 'ZX Stopwatch frame missing')
            x, y, right, _ = box
            counter = (x + 10, y + 53, right - 10, y + 85)
            lap = (x + 93, y + 94, right - 10, y + 124)
            initial = before.crop(counter)
            click(window, x + 45, y + 27)
            until(lambda: ImageChops.difference(initial, capture(window).crop(counter)).getbbox(),
                  'Stopwatch did not tick while idle', timeout=6)
            click(window, x + 135, y + 27)
            click(window, x + 45, y + 106)
            until(lambda: ImageChops.difference(before.crop(lap), capture(window).crop(lap)).getbbox(),
                  'Stopwatch lap display did not update')
            stopped = capture(window).crop(counter)
            time.sleep(1.2)
            assert not ImageChops.difference(stopped, capture(window).crop(counter)).getbbox()
            click(window, x + 224, y + 27)
            until(lambda: not ImageChops.difference(initial, capture(window).crop(counter)).getbbox(),
                  'Stopwatch did not reset')
            close(window, box)
            until(returned, 'Stopwatch did not return success on close')
            print('Stopwatch ZX: start, idle tick, stop, lap, reset, close')
        finally:
            for error, block in output(proc):
                print('Stopwatch stderr:' if error else 'Stopwatch stdout:', block.decode('utf-8', 'replace').strip())
            stop(proc)

    def legacy_stopwatch():
        proc = launch('wm/stopwatch')
        try:
            window = until(owned_window, 'emulator did not map its X window')

            def legacy_frame():
                img = capture(window)
                # Exclude the emulator's outer border from the guest window bounds.
                margin = 8
                interior = img.crop((margin, margin, img.width - margin, img.height - margin))
                background = Image.new('RGB', interior.size, (119, 119, 119))
                box = ImageChops.difference(interior, background).getbbox()
                return tuple(edge + margin for edge in box) if box else None

            def legacy_window():
                box = legacy_frame()
                if box and 70 < box[2] - box[0] < 300 and 70 < box[3] - box[1] < 250:
                    return box
                return None

            box = until(legacy_window, 'Dis Stopwatch frame missing')
            click(window, box[2] - 8, box[1] + 10)
            until(lambda: legacy_frame() is None, 'Dis Stopwatch did not close')
            print('Stopwatch Dis: drew and closed via the original entry point')
        finally:
            stop(proc)

    try:
        ready, _, _ = select.select([reader], [], [], 6)
        display = os.read(reader, 32).strip() if ready else b''
        assert display.isdigit(), 'private Xvfb startup failed'
        env['DISPLAY'] = ':' + display.decode('ascii')
        keyevents()
        kryon()
        stopwatch()
        legacy_stopwatch()
    finally:
        os.close(reader)
        xvfb.terminate()
        xvfb.wait(timeout=5)


if '--graphics' in sys.argv[2:]:
    graphics()
