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

if '--runtime' in sys.argv[2:]:
    unbound = run('zxrun /build/zx-smoke/linked.zx >[2] /build/zx-smoke/module.stderr; echo $status')
    assert unbound.stdout == 'zx\n' and unbound.stderr == ''
    assert 'ZX module not found: guest_counter' in (files / 'module.stderr').read_text()
    linked = run('bind -b /build/zx-smoke/modules /dis/lib; '
                 'zxrun /build/zx-smoke/linked.zx | cat; echo GUEST_MODULE_OK')
    assert linked.stdout == 'Guest module received 41\n42\nGUEST_MODULE_OK\n'
    assert linked.stderr == ''

if '--stdin' in sys.argv[2:]:
    (files / 'stdin.in').write_text('first line\nsecond line\n')
    stdin_image = '/build/zx-smoke/stdin.zx'
    redirected = run(f'zxrun {stdin_image} < /build/zx-smoke/stdin.in')
    assert redirected.stdout == 'first line\nsecond line\n0\n' and not redirected.stderr
    piped = run(f'cat /build/zx-smoke/stdin.in | zxrun {stdin_image} | cat')
    assert piped.stdout == redirected.stdout and not piped.stderr
    empty = run(f'zxrun {stdin_image} < /dev/null')
    assert empty.stdout == '0\n' and not empty.stderr
    read_error = run(f'zxrun {stdin_image} >[0] /build/zx-smoke/stdin.writeonly')
    assert read_error.stdout == 'read error\n1\n' and not read_error.stderr

if '--cat' in sys.argv[2:]:
    binary = bytes(range(256)) * 96
    (files / 'cat input.bin').write_bytes(binary)
    (files / 'cat café.txt').write_bytes(b'UTF-8 path\n')
    (files / 'cat empty').write_bytes(b'')
    zx_cat = 'zxrun -c /dis/cat.zx'
    prefix = 'bind -c /build/zx-smoke /chan; cd /chan; '
    for command in ('cat', zx_cat):
        files_and_stdin = run(prefix + f"{command} 'cat café.txt' 'cat empty' - 'cat input.bin' "
                              "- < 'cat input.bin' > cat.out; echo $status; echo CAT_OK")
        assert files_and_stdin.stdout == '\nCAT_OK\n' and not files_and_stdin.stderr
        assert (files / 'cat.out').read_bytes() == b'UTF-8 path\n' + binary * 2
        piped = run(prefix + f"cat 'cat input.bin' | {command} | cat > cat.pipe; echo $status; echo PIPE_OK")
        assert piped.stdout == '\nPIPE_OK\n' and not piped.stderr
        assert (files / 'cat.pipe').read_bytes() == binary

    for args, legacy_status, expected in (
            ("'cat missing' 'cat input.bin'", 'bad open', 'cat: cannot open cat missing: '),
            ("''", 'bad open', 'cat: cannot open : '),
            ('>[0] cat.writeonly', 'read error', 'cat: error reading <stdin>: '),
            ("'cat input.bin' <[1] 'cat empty'", 'write error', 'cat: write error: ')):
        legacy = run(prefix + f'cat {args} >[2] cat.dis.err; echo $status')
        converted = run(prefix + f'{zx_cat} {args} >[2] cat.zx.err; echo $status')
        assert legacy.stdout == legacy_status + '\n' and not legacy.stderr
        assert converted.stdout == '1\n' and not converted.stderr
        legacy_error = (files / 'cat.dis.err').read_text()
        assert legacy_error.startswith(expected)
        assert (files / 'cat.zx.err').read_text() == legacy_error


def graphics():
    import io
    import os
    import select
    import signal
    import time
    from collections import deque
    from PIL import Image, ImageChops

    env = {k: v for k, v in os.environ.items() if k not in (
        'DISPLAY', 'WAYLAND_DISPLAY', 'XAUTHORITY', 'DBUS_SESSION_BUS_ADDRESS',
        'XDG_RUNTIME_DIR', 'SESSION_MANAGER')}
    env['HARMONY_DESKTOP_RECOVERY'] = '0'
    reader, writer = os.pipe()
    xvfb = subprocess.Popen(['Xvfb', '-displayfd', str(writer), '-screen', '0',
                            '1024x768x24', '-nolisten', 'tcp', '-noreset'],
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

    def windowed_stdin():
        proc = launch('sh', '-c', f'zxrun -w {stdin_image} < /build/zx-smoke/stdin.in')
        transcript = bytearray()

        def read():
            for error, block in output(proc):
                assert not error, block
                transcript.extend(block)
            return b'first line\nsecond line\n0\n' in transcript

        try:
            until(read, 'windowed ZX did not read guest stdin')
            print('ZX stdin: windowed runner honored guest fd 0 redirection')
        finally:
            stop(proc)

    def fuel():
        proc = launch('zxrun', '-w', '/build/zx-smoke/budget.zx')
        stdout, stderr = bytearray(), bytearray()

        def exhausted():
            for error, block in output(proc):
                (stderr if error else stdout).extend(block)
            return b'stopped after' in stderr or b'zxrun:' in stdout or b'zxrun:' in stderr

        try:
            until(exhausted, 'ZX budget test did not stop', timeout=40)
            assert b'renewed 4 ' in stdout, (stdout, stderr)
            assert b'polled 1 ' in stdout and b'polled 4 ' not in stdout, stdout
            assert b'stopped after' in stderr, stderr
            print('ZX budget: four waited frames completed, empty polls exhausted fuel')
        except AssertionError:
            print('ZX budget output:', repr(stdout), repr(stderr))
            raise
        finally:
            stop(proc)

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
            label = (x, y, right, y + 35)
            until(lambda: ImageChops.difference(before.crop(label),
                                                capture(window).crop(label)).getbbox(),
                  'Kryon click did not redraw the counter')
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
        if '--runtime' in sys.argv[2:]:
            fuel()
        if '--stdin' in sys.argv[2:]:
            windowed_stdin()
    finally:
        os.close(reader)
        xvfb.terminate()
        xvfb.wait(timeout=5)


if '--graphics' in sys.argv[2:]:
    graphics()
