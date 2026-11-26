"""Launch the Linux emulator on a guest filesystem containing only ZX programs."""

import argparse
import io
import os
import select
import shutil
import subprocess
import sys
import time
from pathlib import Path
from tempfile import TemporaryDirectory


ROOT = Path(__file__).resolve().parents[2]
PROBE = '''
using Args :: #import "taijios_args";
using Io :: #import "taijios_io";
using Process :: #import "taijios_process";
Tasks :: #import "taijios_tasks";

// Start a spinning and a blocked child and wait until both reached their loops.
StartPair :: (spinning: *Process.Launch, blocked: *Process.Launch) -> bool {
    unused Io.Remove("/spin-ready");
    unused Io.Remove("/block-ready");
    spin_arg: [1]string = .{"spin"};
    block_arg: [1]string = .{"block"};
    spinning.* = Process.Start("/probe.zx", spin_arg[:]);
    blocked.* = Process.Start("/probe.zx", block_arg[:]);
    if spinning.id <= 0 || blocked.id <= spinning.id { return false }
    for attempt: 0 .. 200000 {
        spin_ready := Io.OpenFile("/spin-ready", 0);
        block_ready := Io.OpenFile("/block-ready", 0);
        if spin_ready >= 0 { unused Io.CloseFile(spin_ready) }
        if block_ready >= 0 { unused Io.CloseFile(block_ready) }
        if spin_ready >= 0 && block_ready >= 0 { return true }
    }
    return false;
}

Named :: (bytes: []u8, name: string) -> bool {
    for i: 0 .. name.count - 1 {
        if bytes[i] != name[i] { return false }
    }
    return bytes[name.count] == 0;
}

main :: () -> s64 {
    input_bytes: [8]u8;
    if Args.Operand(0) == "async" {
        noargs: [0]string;
        rejected := Process.Start("", noargs[:]);
        if rejected.id != 0 || rejected.error == "" { return 34 }
        private_fd := Io.OpenFile("/input", 0);
        if private_fd < 0 { return 40 }
        defer Io.CloseFile(private_fd);
        duplicate := Io.OpenFile("#d/3", 0);
        if duplicate < 0 || Io.CloseFile(duplicate) != 0 { return 41 }
        stream_arg: [1]string = .{"async streams"};
        reading := Process.Start("/probe.zx", stream_arg[:]);
        failed := Process.Start("/missing.zx", noargs[:]);
        if reading.id <= 0 || failed.id <= reading.id || Process.Poll(reading.id).status != -2 { return 35 }
        load_error := Process.Wait(failed.id);
        if load_error.status != -1 || load_error.error == "" { return 36 }
        if Process.Poll(failed.id).error != "unknown ZX process" { return 37 }
        other := Process.Start("/plain.zx", noargs[:]);
        if other.id <= failed.id || Process.Wait(other.id).status != 0 { return 38 }
        print("ZX_ASYNC_READY\\n");
        if Process.Wait(reading.id).status != 1 || Process.Wait(reading.id).error != "unknown ZX process" {
            return 39;
        }
        print("ZX_ASYNC_OK\\n");
        return 0;
    }
    if Args.Operand(0) == "kill" {
        sibling_arg: [1]string = .{"sibling"};
        spinning: Process.Launch;
        blocked: Process.Launch;
        if !StartPair(*spinning, *blocked) { return 51 }
        sibling := Process.Start("/probe.zx", sibling_arg[:]);
        if sibling.id <= blocked.id { return 50 }
        // Give the blocked child time to sleep in its pipe read.
        for settle: 0 .. 50000 {
            if Process.Poll(blocked.id).status != -2 { return 56 }
        }
        if !Process.Kill(spinning.id) || !Process.Kill(blocked.id) { return 52 }
        spun := Process.Wait(spinning.id);
        read := Process.Wait(blocked.id);
        if spun.status != -1 || spun.error != "killed" || read.status != -1 || read.error != "killed" { return 53 }
        if Process.Kill(spinning.id) || Process.Poll(sibling.id).status != -2 { return 54 }
        print("ZX_KILLED\\n");
        survivor := Process.Wait(sibling.id);
        if survivor.status != 1 || survivor.value != 7 { return 55 }
        print("ZX_KILL_OK\\n");
        return 0;
    }
    if Args.Operand(0) == "tasks" {
        spinning: Process.Launch;
        blocked: Process.Launch;
        if !StartPair(*spinning, *blocked) { return 70 }
        count := Tasks.Capture();
        if count != 2 || Tasks.SampleNanos() <= 0 { return 71 }
        fields: [7]s64;
        module: [64]u8;
        user: [64]u8;
        pids: [2]s64;
        for i: 0 .. 1 {
            if Tasks.TaskAt(cast(s32)i, fields[:], module[:], user[:]) != 0 || !Named(module[:], "probe") ||
               fields[0] <= 0 || fields[2] != 4 || fields[5] != fields[0] || fields[4] < 0 || fields[6] < 0 { return 72 }
            pids[i] = fields[0];
        }
        pool: [3]s64;
        if pids[0] >= pids[1] || Tasks.PoolAt(0, pool[:]) != 0 || pool[1] <= 0 { return 73 }
        if Tasks.Terminate(cast(s32)pids[0]) != 0 { return 74 }
        spun := Process.Wait(spinning.id);
        if spun.status != -1 || spun.error != "killed" || Tasks.Terminate(cast(s32)pids[0]) != -2 { return 75 }
        if Tasks.Capture() != 1 || Tasks.Terminate(12345) != -1 { return 76 }
        if !Process.Kill(blocked.id) || Process.Wait(blocked.id).error != "killed" || Tasks.Capture() != 0 { return 77 }
        print("ZX_TASKS_OK\\n");
        return 0;
    }
    if Args.Operand(0) == "spin" {
        input := Io.OpenFile("/input", 0);
        marker := Io.CreateFile("/spin-ready", 1, 438);
        if input < 0 || marker < 0 || Io.CloseFile(marker) != 0 { return 60 }
        byte: [1]u8;
        total: s64 = 0;
        // Each successful read renews the step budget, so only a kill ends this loop.
        while total >= 0 {
            for i: 0 .. 100000 { total += i & 1 }
            unused Io.SeekFile(input, 0, 0);
            if Io.ReadBytes(input, byte[:]) != 1 { return 61 }
        }
        return 62;
    }
    if Args.Operand(0) == "block" {
        pipe := Io.OpenFile("#|/data", 2);
        marker := Io.CreateFile("/block-ready", 1, 438);
        if pipe < 0 || marker < 0 || Io.CloseFile(marker) != 0 { return 63 }
        byte: [1]u8;
        unused Io.ReadBytes(pipe, byte[:]);
        return 64;
    }
    if Args.Operand(0) == "sibling" {
        if Io.ReadBytes(0, input_bytes[:]) != 2 || input_bytes[0] != 83 { return 65 }
        return 7;
    }
    if Args.Operand(0) == "children" {
        noargs: [0]string;
        outcome := Process.Run("/missing.zx", noargs[:]);
        if outcome.status != -1 || outcome.error == "" { return 31 }
        operands: [1]string = .{"fail"};
        child := Process.Run("/probe.zx", operands[:]);
        if child.status != 1 || child.value != 23 || child.error != "requested failure" { return 32 }
        if Process.Run("/plain.zx", noargs[:]).status != 0 { return 33 }
        return 0;
    }
    if Args.Operand(0) == "streams" || Args.Operand(0) == "async streams" {
        if Args.Operand(0) == "async streams" && Io.OpenFile("#d/3", 0) >= 0 { return 42 }
        if Io.ReadBytes(0, input_bytes[:]) != 2 || input_bytes[0] != 88 ||
           input_bytes[1] != 10 || Io.ReadBytes(0, input_bytes[:]) != 0 { return 18 }
        if Io.WriteBytes(1, "out\\n") != 4 || Io.WriteBytes(2, "err\\n") != 4 { return 19 }
        return 0;
    }
    if Args.Operand(0) == "fail" {
        unused Args.SetFailure("requested failure");
        return 23;
    }
    if Args.Operand(0) == "negative" { return -1 }
    if Args.Operand(0) == "out of range" { return 256 }
    if Args.Operand(0) == "wide" { return 1099511627783 }
    if Args.OperandCount() != 3 || Args.Operand(0) != "-test" ||
       Args.Operand(1) != "café 猫" || Args.Operand(2) != "" { return 12 }
    input := Io.OpenFile("/input", 0);
    if input < 0 { return 13 }
    bytes: [8]u8;
    count := Io.ReadBytes(input, bytes[:]);
    if Io.CloseFile(input) != 0 || count != 2 || bytes[0] != 90 || bytes[1] != 88 { return 14 }
    if Io.OpenFile("/env/emuroot", 0) < 0 { return 15 }
    if Io.OpenFile("#p", 0) >= 0 || Io.OpenFile("#P", 0) >= 0 ||
       Io.OpenFile("#s", 0) >= 0 || Io.OpenFile("/prog/1/status", 0) >= 0 { return 17 }
    if Io.WriteBytes(1, "ZX_BOOT_OK\\n") != 11 { return 16 }
    return 0;
}
'''


def check_async(emulator, root, env):
    with subprocess.Popen([emulator, '-v', '-r', root, '/probe.zx', 'async'], env=env,
                          stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          start_new_session=True) as app:
        transcript = bytearray()
        deadline = time.monotonic() + 10
        try:
            while b'ZX_ASYNC_READY\n' not in transcript:
                assert select.select([app.stdout], [], [], max(0, deadline - time.monotonic()))[0], transcript
                data = os.read(app.stdout.fileno(), 1024)
                assert data and len(transcript) < 8192, transcript
                transcript.extend(data)
            assert b'ZX_VOID_OK\n' in transcript and b'out\n' not in transcript, transcript
            stdout, stderr = app.communicate(b'X\n', timeout=10)
            assert app.returncode == 0 and b'out\nZX_ASYNC_OK\n' in stdout, (stdout, stderr)
            assert stderr == b'err\n', stderr
        finally:
            if app.poll() is None:
                app.kill()
    print('Concurrent ZX children retained separate outcomes while one waited on inherited input')


def check_kill(emulator, root, env):
    with subprocess.Popen([emulator, '-v', '-r', root, '/probe.zx', 'kill'], env=env,
                          stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          start_new_session=True) as app:
        transcript = bytearray()
        deadline = time.monotonic() + 20
        try:
            while b'ZX_KILLED\n' not in transcript:
                assert select.select([app.stdout], [], [], max(0, deadline - time.monotonic()))[0], transcript
                data = os.read(app.stdout.fileno(), 1024)
                assert data and len(transcript) < 8192, transcript
                transcript.extend(data)
            stdout, stderr = app.communicate(b'S\n', timeout=10)
            assert app.returncode == 0 and b'ZX_KILL_OK\n' in stdout, (transcript, stdout, stderr)
            assert not stderr, stderr
        finally:
            if app.poll() is None:
                app.kill()
    print('A spinning ZX child and one blocked in a device read were killed while a sibling and the host kept running')


def check_draw(emulator, root, env):
    from PIL import Image

    sys.path.insert(0, str(ROOT / 'appl/cmd/tcltk'))
    from test_logwindow import private_display
    from test_tcltk import launch, stop, until

    probe = Path(__file__).with_name('zx_boot_draw.zi')
    subprocess.run([
        'ziran', 'bundle', '--root', probe.parent, '--module-path', ROOT / 'appl/cmd',
        '--module-path', ROOT / 'appl/lib', '--module-path', ROOT / 'appl/wm',
        '--bind-host', 'taijios_args', '--bind-host', 'taijios_io',
        '--entry', 'zx_boot_draw:main', '-o', root / 'draw.zx', probe,
    ], env=env, check=True, timeout=60)

    with private_display() as display:
        env = env | {'DISPLAY': display['DISPLAY']}
        app = launch(env, emulator, '-v', '-r', root, '-g', '640x480', '/draw.zx',
                     stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        transcript = bytearray()

        def received(line):
            if select.select([app.stdout], [], [], 0)[0]:
                transcript.extend(app.stdout.read1(1024))
            assert len(transcript) <= 8192, 'unexpected guest output'
            return line in transcript

        def desktop(*args, check=True):
            return subprocess.run(args, env=env, capture_output=True, check=check, timeout=5).stdout

        try:
            until(lambda: received(b'ZX_DRAW_READY 640x480'), 'ZX Draw did not paint')
            assert b'Initial ZX: "/draw.zx"' in transcript and b'Initial Dis:' not in transcript
            window = until(lambda: desktop('xdotool', 'search', '--onlyvisible', '--name',
                                           '^inferno$', check=False).decode().strip(), 'guest window missing')
            frame = Image.open(io.BytesIO(desktop('import', '-window', window, 'png:-'))).convert('RGB')
            assert frame.size == (640, 480) and frame.getpixel((320, 240)) == (24, 56, 88)
            assert frame.getpixel((10, 10)) == (24, 56, 88)
            assert frame.getpixel((11, 10)) == (230, 30, 10)
            assert frame.getpixel((12, 10)) == (10, 30, 230)
            assert frame.getpixel((12, 11)) == (250, 205, 20)
            assert frame.getpixel((12, 12)) == (10, 80, 230)
            assert frame.getpixel((32, 32)) == (180, 40, 40)
            assert frame.getpixel((44, 44)) == (180, 40, 40)
            assert frame.getpixel((48, 48)) == (250, 205, 20)
            assert frame.getpixel((56, 56)) == (40, 180, 40)
            assert frame.getpixel((66, 66)) == (24, 56, 88)
            desktop('xdotool', 'windowfocus', window)
            desktop('xdotool', 'mousemove', '--window', window, '120', '160', 'click', '1')
            desktop('xdotool', 'key', 'a')
            desktop('xdotool', 'key', 'ctrl+alt+Right')
            until(lambda: received(b'ZX_DRAW_INPUT_OK'), 'guest did not receive pointer and keyboard events')
            assert app.wait(timeout=5) == 0
        except (AssertionError, subprocess.SubprocessError) as error:
            raise AssertionError(f'{error}\n{transcript.decode(errors="replace")}') from error
        finally:
            stop(app)
            app.stdout.close()
    print('Private ZX-only guest composited its workspace and received pointer and keyboard events')


def check_window_manager(emulator, root, env):
    from PIL import Image
    from test_logwindow import private_display
    from test_tcltk import launch, stop, until

    wm = ROOT / 'appl/wm'
    surfaces = ROOT / 'appl/cmd/tcltk'
    subprocess.run([
        'ziran', 'bundle', '--project', '--module-path', ROOT / 'appl/cmd',
        '--module-path', ROOT / 'appl/lib', '--module-path', surfaces,
        '--bind-host', 'taijios_args', '--bind-host', 'taijios_io',
        '--bind-host', 'taijios_process', '--bind-host', 'taijios_native_wm',
        '--entry', 'native_wm:main', '-o', root / 'wm.zx', wm / 'native_wm.zi',
    ], cwd=wm, env=env, check=True, timeout=60)
    fixture = Path(__file__).with_name('zx_window_app.zi').read_text(encoding='utf-8')
    for red in (37, 108):
        source = root / 'zx_window_app.zi'
        source.write_text(fixture.replace('Color :: 37;', f'Color :: {red};'), encoding='utf-8')
        subprocess.run([
            'ziran', 'bundle', '--root', root, '--module-path', surfaces, '--module-path', ROOT / 'appl/cmd',
            '--bind-host', 'zx_surface', '--bind-host', 'taijios_args', '--bind-host', 'taijios_wm',
            '--bind-host', 'taijios_draw', '--bind-host', 'taijios_stdin',
            '--entry', 'zx_window_app:main', '-o', root / f'window{red}.zx', source,
        ], env=env, check=True, timeout=60)
    assert not any(root.rglob('*.dis'))

    with private_display() as display:
        env = env | {'DISPLAY': display['DISPLAY']}
        app = launch(env, emulator, '-v', '-r', root, '-g', '640x480', '/wm.zx',
                     '/window37.zx', '/window108.zx', stdin=subprocess.PIPE,
                     stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        app.stdin.write(b'LOG\n')
        app.stdin.close()

        def desktop(*args, check=True):
            return subprocess.run(args, env=env, capture_output=True, check=check, timeout=5).stdout

        try:
            window = until(lambda: desktop('xdotool', 'search', '--onlyvisible', '--name',
                                           '^inferno$', check=False).decode().strip(), 'native WM window missing')

            def samples():
                assert app.poll() is None, f'native WM exited with {app.returncode}'
                frame = Image.open(io.BytesIO(desktop('import', '-window', window, 'png:-'))).convert('RGB')
                return tuple(frame.getpixel((x + 16, y)) for x in (0, 48) for y in (17, 31))

            frames = {((37, 90, 170), (37, 90, 170)), ((108, 90, 170), (108, 90, 200))}
            background = (24, 56, 88)

            def both_visible():
                pixels = samples()
                return {pixels[:2], pixels[2:]} == frames

            until(both_visible, 'both ZX application frames were not visible')
            desktop('xdotool', 'windowfocus', window)
            desktop('xdotool', 'key', 'ctrl+alt+Right')
            until(lambda: set(samples()) == {background}, 'inactive workspace left its windows visible')
            desktop('xdotool', 'key', 'ctrl+alt+Left')
            until(both_visible, 'returning workspace lost its windows')

            def close(x):
                desktop('xdotool', 'mousemove', '--window', window, str(x), '17', 'click', '1')
                desktop('xdotool', 'key', 'a')

            close(16)
            def first_closed():
                pixels = samples()
                return pixels[:2] == (background, background) and pixels[2:] in frames

            until(first_closed, 'first child did not close independently')
            close(64)
            assert app.wait(timeout=8) == 0
            transcript = app.stdout.read(4096)
            assert b'Initial ZX: "/wm.zx"' in transcript and b'Initial Dis:' not in transcript, transcript
            assert b'ZX_WINDOW_DONE 37' in transcript and b'ZX_WINDOW_DONE 108' in transcript, transcript
        except (AssertionError, subprocess.SubprocessError) as error:
            stop(app)
            raise AssertionError(f'{error}\n{app.stdout.read(4096).decode(errors="replace")}') from error
        finally:
            stop(app)
            app.stdout.close()
    print('Native ZX WM placed, composited, switched and routed input to two real ZX windows')


def check_tertiary_pointer(emulator, root, env):
    from PIL import Image
    from test_logwindow import private_display
    from test_tcltk import launch, stop, until

    wm = ROOT / 'appl/wm'
    subprocess.run([
        'ziran', 'bundle', '--project', '--bind-host', 'kryon/pixmap',
        '--entry', 'tertiary_probe_test:main', '-o', root / 'tertiary.zx', 'tertiary_probe_test.zi',
    ], cwd=wm, env=env, check=True, timeout=120)

    with private_display() as display:
        private_env = env | {'DISPLAY': display['DISPLAY']}
        app = launch(private_env, emulator, '-v', '-r', root, '-g', '640x480', '/wm.zx',
                     '/tertiary.zx', stdin=subprocess.DEVNULL,
                     stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        transcript = bytearray()

        def desktop(*args, check=True):
            return subprocess.run(args, env=private_env, capture_output=True, check=check, timeout=5).stdout

        def wait_marker(label):
            def seen():
                assert app.poll() is None, f'tertiary probe exited early with {app.returncode}'
                while select.select([app.stdout], [], [], 0)[0]:
                    chunk = app.stdout.read1(1024)
                    if not chunk:
                        break
                    transcript.extend(chunk)
                assert b'ZX_TERTIARY_FAIL' not in transcript, transcript.decode(errors='replace')
                return label.encode() + b'\n' in transcript
            until(seen, f'missing {label}', timeout=10)

        try:
            window = until(lambda: desktop('xdotool', 'search', '--onlyvisible', '--name',
                                           '^inferno$', check=False).decode().strip(), 'tertiary WM window missing')

            def visible():
                assert app.poll() is None, f'tertiary WM exited with {app.returncode}'
                frame = Image.open(io.BytesIO(desktop('import', '-window', window, 'png:-'))).convert('RGB')
                return frame.getpixel((24, 20)) == (48, 128, 84)

            until(visible, 'tertiary probe window was not painted')
            desktop('xdotool', 'windowfocus', window)
            desktop('xdotool', 'mousemove', '--window', window, '24', '20', 'mousedown', '2')
            wait_marker('ZX_TERTIARY_PRESS 24 20')
            desktop('xdotool', 'mousemove', '--window', window, '52', '36')
            wait_marker('ZX_TERTIARY_HOLD 52 36')
            desktop('xdotool', 'mouseup', '2')
            wait_marker('ZX_TERTIARY_RELEASE 52 36')
            desktop('xdotool', 'mousemove', '--window', window, '30', '30', 'click', '1')
            desktop('xdotool', 'mousemove', '--window', window, '34', '30', 'click', '3')
            wait_marker('ZX_TERTIARY_OK')
        except (AssertionError, subprocess.SubprocessError) as error:
            stop(app)
            while len(transcript) < 65536 and select.select([app.stdout], [], [], 0)[0]:
                chunk = app.stdout.read1(4096)
                if not chunk:
                    break
                transcript.extend(chunk)
            raise AssertionError(f'{error}\n{transcript.decode(errors="replace")}') from error
        finally:
            stop(app)
            app.stdout.close()
    print('Native ZX WM delivered middle-button press, hold and release at the right position without changing buttons 1 and 3')


def check_event_queue_overflow(emulator, root, env):
    from PIL import Image
    from test_logwindow import private_display
    from test_tcltk import launch, stop, until

    surfaces = ROOT / 'appl/cmd/tcltk'
    source = Path(__file__).with_name('zx_overflow_probe.zi')
    subprocess.run([
        'ziran', 'bundle', '--root', source.parent, '--module-path', surfaces, '--module-path', ROOT / 'appl/cmd',
        '--bind-host', 'zx_surface', '--bind-host', 'taijios_io',
        '--entry', 'zx_overflow_probe:main', '-o', root / 'overflow.zx', source,
    ], env=env, check=True, timeout=60)
    release = root / 'release'
    release.unlink(missing_ok=True)

    with private_display() as display:
        private_env = env | {'DISPLAY': display['DISPLAY']}
        app = launch(private_env, emulator, '-v', '-r', root, '-g', '640x480', '/wm.zx',
                     '/overflow.zx', stdin=subprocess.DEVNULL,
                     stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        transcript = bytearray()

        def desktop(*args, check=True):
            return subprocess.run(args, env=private_env, capture_output=True, check=check, timeout=10).stdout

        def wait_marker(label):
            def seen():
                while select.select([app.stdout], [], [], 0)[0]:
                    chunk = app.stdout.read1(1024)
                    if not chunk:
                        break
                    transcript.extend(chunk)
                return label.encode() in transcript
            until(seen, f'missing {label}', timeout=10)

        try:
            window = until(lambda: desktop('xdotool', 'search', '--onlyvisible', '--name',
                                           '^inferno$', check=False).decode().strip(), 'overflow WM window missing')

            def visible():
                assert app.poll() is None, f'overflow WM exited with {app.returncode}'
                frame = Image.open(io.BytesIO(desktop('import', '-window', window, 'png:-'))).convert('RGB')
                return frame.getpixel((16, 16)) == (40, 160, 80)

            until(visible, 'overflow probe window was not painted')
            wait_marker('ZX_OVERFLOW_READY\n')
            desktop('xdotool', 'windowfocus', window)
            desktop('xdotool', 'mousemove', '--window', window, '16', '16', 'click', '1')
            # Send 35 'a' keystrokes (> 64 non-Move events: KeyDown + Text + KeyUp each) while the app is busy.
            desktop('xdotool', 'type', '--delay', '5', 'a' * 35)
            time.sleep(0.2)
            release.write_bytes(b'go')
            time.sleep(0.3)
            desktop('xdotool', 'key', 'z')
            assert app.wait(timeout=10) == 0, f'overflow WM exited with {app.returncode}'
            transcript.extend(app.stdout.read(4096))
            assert b'ZX_OVERFLOW_OK ' in transcript, transcript.decode(errors='replace')
            assert b'ZX_OVERFLOW_CLOSED' not in transcript, transcript.decode(errors='replace')
        except (AssertionError, subprocess.SubprocessError) as error:
            stop(app)
            raise AssertionError(f'{error}\n{transcript.decode(errors="replace")}') from error
        finally:
            release.unlink(missing_ok=True)
            stop(app)
            app.stdout.close()
    print('Native ZX WM kept a busy application connected across a 64-event ring overflow and delivered retried events')


def check_desktop_shell(emulator, root, env):
    from PIL import Image
    from test_logwindow import private_display
    from test_tcltk import launch, stop, until

    source = Path(__file__).with_name('zx_desktop_shell.zi')
    (root / 'locale').mkdir()
    (root / 'locale/timezone').write_text('TST 5400 TST 5400\n', encoding='ascii')
    subprocess.run([
        'ziran', 'bundle', '--root', source.parent, '--module-path', ROOT / 'appl/cmd',
        '--module-path', ROOT / 'appl/cmd/tcltk', '--bind-host', 'taijios_desktop',
        '--bind-host', 'taijios_wm', '--bind-host', 'taijios_args', '--bind-host', 'zx_surface',
        '--entry', 'zx_desktop_shell:main', '-o', root / 'shell.zx', source,
    ], env=env, check=True, timeout=60)

    with private_display() as display:
        app = [emulator, '-v', '-r', root, '-g', '640x480', '/wm.zx']
        private_env = env | {'DISPLAY': display['DISPLAY']}
        ordinary = subprocess.run(app + ['/shell.zx'], env=private_env, stdin=subprocess.DEVNULL,
                                  capture_output=True, text=True, start_new_session=True, timeout=10)
        assert ordinary.returncode == 1 and 'ZX_DESKTOP_PROTOCOL_OK' not in ordinary.stdout, ordinary
        shell = launch(private_env, *app, '--desktop', '/shell.zx', stdin=subprocess.DEVNULL,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        transcript = bytearray()

        def desktop(*args, check=True):
            return subprocess.run(args, env=private_env, capture_output=True, check=check, timeout=5).stdout

        def marker(label):
            def received():
                if select.select([shell.stdout], [], [], 0)[0]:
                    transcript.extend(shell.stdout.read1(1024))
                assert len(transcript) <= 8192, 'unexpected desktop output'
                return label.encode() + b'\n' in transcript

            until(received, label, timeout=8)

        try:
            marker('ZX_TITLE_READY')
            window = until(lambda: desktop('xdotool', 'search', '--onlyvisible', '--name',
                                           '^inferno$', check=False).decode().strip(), 'ZX desktop window missing')

            def title_visible(x, y):
                frame = Image.open(io.BytesIO(desktop('import', '-window', window, 'png:-'))).convert('RGB')
                caption = frame.crop((x + 34, y - 32, x + 146, y))
                colors = caption.getcolors(caption.width * caption.height)
                return sum(count for count, rgb in colors if min(rgb) > 80) > 18

            def move(x, y):
                return ('mousemove', '--window', window, str(x), str(y))

            def drag(x, y, end_x, end_y):
                desktop('xdotool', *move(x, y), 'mousedown', '1', 'sleep', '.10',
                        *move(end_x, end_y), 'sleep', '.10', 'mouseup', '1')

            def click(x, y, label):
                desktop('xdotool', *move(x, y), 'click', '1')
                marker(label)

            until(lambda: title_visible(100, 110), 'ZX title glyphs were missing')
            drag(145, 94, 195, 134)
            marker('ZX_TITLE_MOVED')
            until(lambda: title_visible(150, 150), 'ZX title did not move with its window')
            drag(352, 134, 392, 154)
            marker('ZX_TITLE_RESIZED')
            click(392, 134, 'ZX_TITLE_MAXIMIZED')
            until(lambda: title_visible(246, 56), 'maximized title missing')
            click(592, 40, 'ZX_TITLE_RESTORED')
            click(360, 134, 'ZX_TITLE_MINIMIZED')
            until(lambda: title_visible(150, 150), 'restored title bar did not return')
            click(424, 134, 'ZX_DESKTOP_PROTOCOL_OK')
            assert shell.wait(timeout=8) == 0 and not shell.stderr.read(1024)
            assert b'Initial Dis:' not in transcript
            assert transcript.count(b'ZX_DESKTOP_CHILD_CLOSED\n') == 2
            assert b'ZX_DESKTOP_CHILD_RESIZED\n' in transcript
        except (AssertionError, subprocess.SubprocessError) as error:
            stop(shell)
            transcript.extend(shell.stdout.read(1024))
            raise AssertionError((str(error), transcript, shell.stderr.read(1024))) from error
        finally:
            stop(shell)
            shell.stdout.close()
            shell.stderr.close()
    print('Private ZX desktop launched windows and used native title bars to move, resize, maximize, restore, minimize and close')


def check_command_names(emulator, root, env, boot, operands):
    """A command name starts its installed ZX bundle unless a Dis module has that name."""
    (root / 'zx').mkdir()
    shutil.copy2(root / 'probe.zx', root / 'zx/probe.zx')
    result = boot('probe', *operands)
    assert result.returncode == 0 and not result.stderr, result
    assert 'Initial ZX: "/zx/probe.zx"' in result.stdout and 'ZX_BOOT_OK' in result.stdout, result
    assert 'Initial Dis:' not in result.stdout, result

    legacy = root / 'legacy'
    (legacy / 'zx').mkdir(parents=True)
    shutil.copy2(root / 'plain.zx', legacy / 'zx/twin.zx')
    (legacy / 'zx/twin.dis').write_bytes(b'not a Dis module')
    # This root has no Dis runtime files, so the emulator stops after naming its choice.
    with subprocess.Popen([emulator, '-v', '-r', legacy, 'twin'], env=env, stdin=subprocess.DEVNULL,
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT, start_new_session=True) as legacy_boot:
        output = bytearray()
        deadline = time.monotonic() + 10
        try:
            while b'Initial ' not in output or not output.endswith(b'\n'):
                assert time.monotonic() < deadline, bytes(output)
                if select.select([legacy_boot.stdout], [], [], 0.2)[0]:
                    data = legacy_boot.stdout.read1(1024)
                    assert data, bytes(output)
                    output.extend(data)
        finally:
            legacy_boot.kill()
    assert b'Initial Dis:' in output and b'Initial ZX:' not in output and b'ZX_VOID_OK' not in output, bytes(output)
    shutil.rmtree(legacy)
    print('A command name started its ZX bundle without Dis, and a Dis module of the same name kept priority')


def check_namespace(root, env, boot):
    """One ZX process serves a 9P tree over a pipe; its parent mounts and reads it."""
    source = Path(__file__).with_name('zx_namespace_probe.zi')
    subprocess.run([
        'ziran', 'bundle', '--root', source.parent, '--module-path', ROOT / 'appl/cmd',
        '--bind-host', 'taijios_args', '--bind-host', 'taijios_io', '--bind-host', 'taijios_namespace',
        '--bind-host', 'taijios_process', '--entry', 'zx_namespace_probe:main',
        '-o', root / 'namespace.zx', source,
    ], env=env, check=True, timeout=60)
    for name in ('served', 'alias', 'shared', 'private'):
        (root / 'n' / name).mkdir(parents=True)
    result = boot('/namespace.zx')
    assert result.returncode == 0 and 'ZX_NAMESPACE_OK' in result.stdout and not result.stderr, result
    assert 'Initial Dis:' not in result.stdout, result
    (root / 'cdtest').mkdir()
    (root / 'cdtest/hello').write_text('hello from ZX\n', encoding='ascii')
    result = boot('/namespace.zx', 'cd', '/cdtest')
    assert result.returncode == 0 and 'ZX_CHDIR_OK' in result.stdout and not result.stderr, result
    (root / 'pctltest').mkdir()
    (root / 'pctltest/inner').write_text('inner\n', encoding='ascii')
    result = boot('/namespace.zx', 'pctl')
    assert result.returncode == 0 and 'ZX_PCTL_OK' in result.stdout and not result.stderr, result
    print('Without Dis, a ZX child served a 9P tree on a pipe given as its standard streams; its parent mounted, '
          'read, bound and unmounted the tree, forked a namespace, and polled a pipe; children forked their '
          'environment, rooted a new namespace and gave up devices, as pctl does')


def check_hosted_process(emulator, root, env):
    """ZX commands run by the Dis shell start, kill and detach children too."""
    zxrun = ROOT / 'zx/zxrun.dis'
    assert zxrun.exists(), 'install the Dis zxrun command first: (cd appl/cmd && mk zxrun.install)'
    probe = '/' + (root / 'namespace.zx').relative_to(ROOT).as_posix()
    mount = root / 'hosted-mount'
    mount.mkdir()
    guest_mount = '/' + mount.relative_to(ROOT).as_posix()
    script = (f'zxrun -s {probe} hosted {probe}; zxrun -s {probe} mountout {probe} {guest_mount}; '
              f'cat {guest_mount}/hello; unmount {guest_mount}; echo HOSTED_DONE')
    # The mounted server outlives the script; -x ends the emulator with the shell
    # anyway. The emulator ends by killing its own process group.
    result = subprocess.run([emulator, '-x', '-r', ROOT, '/zx/sh.dis', '-c', script], env=env,
                            stdin=subprocess.DEVNULL, capture_output=True, timeout=30, start_new_session=True)
    lines = result.stdout.decode().splitlines()
    assert lines == ['ZX_HOSTED_PROCESS_OK', 'hello from ZX', 'HOSTED_DONE'], result
    print('Under the Dis shell, a ZX command started children on chosen streams, killed a blocked one, and left a '
          'mounted server running after it exited; with -x the emulator still ended with the script')


def check_services(root, env, boot):
    """Export a directory, serve a file2chan file to a child, and carry a TCP call."""
    source = Path(__file__).with_name('zx_services_probe.zi')
    subprocess.run([
        'ziran', 'bundle', '--root', source.parent, '--module-path', ROOT / 'appl/cmd',
        '--bind-host', 'taijios_args', '--bind-host', 'taijios_io', '--bind-host', 'taijios_namespace',
        '--bind-host', 'taijios_process', '--bind-host', 'taijios_dial', '--entry', 'zx_services_probe:main',
        '-o', root / 'services.zx', source,
    ], env=env, check=True, timeout=60)
    for name in ('n/source', 'n/exported', 'n/chan', 'net'):
        (root / name).mkdir(parents=True, exist_ok=True)
    (root / 'n/source/note').write_text('exported note\n', encoding='ascii')
    (root / 'n/chan/plain').write_text('plain\n', encoding='ascii')
    result = boot('/services.zx')
    assert result.returncode == 0 and 'ZX_SERVICES_OK' in result.stdout and not result.stderr, result
    assert 'Initial Dis:' not in result.stdout, result
    print('Without Dis, a ZX process read a directory it exported over a pipe, answered a child through a '
          'file2chan file, and took a TCP call from another child')


def check_keyring(root, env, boot):
    """Compare taijios_keyring with values the Limbo Keyring module printed, and sign with new keys."""
    source = Path(__file__).with_name('zx_keyring_probe.zi')
    subprocess.run([
        'ziran', 'bundle', '--root', source.parent, '--module-path', ROOT / 'appl/cmd',
        '--bind-host', 'taijios_args', '--bind-host', 'taijios_keyring', '--entry', 'zx_keyring_probe:main',
        '-o', root / 'keyring.zx', source,
    ], env=env, check=True, timeout=60)
    result = boot('/keyring.zx', timeout=120)
    assert result.returncode == 0 and 'ZX_KEYRING_OK' in result.stdout and not result.stderr, result
    print('Without Dis, digests, HMAC, AES-CBC and big integer arithmetic matched the Limbo Keyring module, '
          'and new RSA, DSA and ElGamal keys encrypted, signed and verified')


def check_image_viewer(emulator, root, env):
    """The image viewer animates a GIF, opens further files in their own windows, and shows plumbed files."""
    from PIL import Image, ImageChops
    from test_logwindow import private_display
    from test_tcltk import launch, stop, until

    viewer = ROOT / 'appl/wm/view.zx'
    assert viewer.exists(), 'build the image viewer first: (cd appl/wm && mk view.zx)'
    (root / 'zx/wm').mkdir(parents=True, exist_ok=True)
    shutil.copy2(viewer, root / 'zx/wm/view.zx')
    for name in ('frames.gif', 'sample.xbm'):
        shutil.copy2(Path(__file__).with_name(name), root / name)
    (root / 'chan').mkdir(exist_ok=True)
    source = Path(__file__).with_name('zx_viewer_probe.zi')
    subprocess.run([
        'ziran', 'bundle', '--root', source.parent, '--module-path', ROOT / 'appl/cmd',
        '--module-path', ROOT / 'appl/cmd/tcltk', '--bind-host', 'taijios_desktop', '--bind-host', 'taijios_wm',
        '--bind-host', 'taijios_args', '--bind-host', 'zx_surface', '--bind-host', 'taijios_io',
        '--bind-host', 'taijios_namespace', '--entry', 'zx_viewer_probe:main', '-o', root / 'viewer.zx', source,
    ], env=env, check=True, timeout=60)

    with private_display() as display:
        private_env = env | {'DISPLAY': display['DISPLAY']}
        shell = launch(private_env, emulator, '-r', root, '-g', '1024x768', '/wm.zx', '--desktop', '/viewer.zx',
                       stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        transcript = bytearray()

        def desktop(*args, check=True):
            return subprocess.run(args, env=private_env, capture_output=True, check=check, timeout=5).stdout

        def marker(label):
            def seen():
                if select.select([shell.stdout], [], [], 0)[0]:
                    transcript.extend(shell.stdout.read1(1024))
                lines = [line for line in transcript.split(b'\n') if line.startswith(label.encode())]
                return lines[0].decode().split()[1:] if lines else None
            rects = until(seen, label, timeout=30)
            return [tuple(map(int, rect.split(','))) for rect in rects]

        def picture(window, rect):
            x, y, w, h = rect
            frame = Image.open(io.BytesIO(desktop('import', '-window', window, 'png:-'))).convert('RGB')
            return frame.crop((x + 8, y + 84, x + w - 8, y + h - 36))

        def colours(image):
            return {colour for _, colour in image.getcolors(image.width * image.height) or []}

        def black_and_white(image):
            return {(0, 0, 0), (255, 255, 255)} <= colours(image)

        window = 'root'
        try:
            window = until(lambda: desktop('xdotool', 'search', '--onlyvisible', '--name',
                                           '^inferno$', check=False).decode().strip(), 'viewer desktop window missing')
            rects = marker('ZX_VIEWER_FILES')
            assert len(rects) == 2, rects
            # The second file opened in its own viewer, on top.
            top = max(rects, key=lambda rect: rect[1])
            until(lambda: black_and_white(picture(window, top)), 'X bitmap not shown')
            (root / 'ack').write_bytes(b'')
            gif = marker('ZX_VIEWER_GIF')
            assert len(gif) == 1, gif

            # Frames advance every 250 ms, but a frame can take seconds to
            # render on a busy machine, so wait for the picture to change.
            def gif_shown():
                image = picture(window, gif[0])
                return image if (0, 128, 0) in colours(image) else None

            shown = until(gif_shown, 'frames.gif not shown', timeout=30)
            until(lambda: ImageChops.difference(shown, picture(window, gif[0])).getbbox(), 'the GIF did not animate',
                  timeout=30)
            (root / 'ack').write_bytes(b'')
            plumbed = marker('ZX_VIEWER_PLUMBED')
            assert len(plumbed) == 1, plumbed
            until(lambda: black_and_white(picture(window, plumbed[0])), 'plumbed X bitmap not shown')
            # Save: end the path with a new letter, then press Save. Each input
            # event costs the viewer a frame, so keep them few.
            x, y, w, h = plumbed[0]
            desktop('xdotool', 'windowfocus', window)
            desktop('xdotool', 'mousemove', '--sync', '--window', window, str(x + w - 120), str(y + 24),
                    'mousedown', '1', 'sleep', '0.15', 'mouseup', '1')
            desktop('xdotool', 'type', '--delay', '200', 'x')
            time.sleep(2)
            desktop('xdotool', 'mousemove', '--sync', '--window', window, str(x + w - 46), str(y + 61),
                    'mousedown', '1', 'sleep', '0.15', 'mouseup', '1')
            saved = root / 'sample.xbmx'
            until(lambda: saved.exists() and saved.stat().st_size == 60 + 13 * 7 * 3, 'Save wrote no Inferno image',
                  timeout=60)
            data = saved.read_bytes()
            assert data[:60] == b'%11s %11d %11d %11d %11d ' % (b'r8g8b8', 0, 0, 13, 7), data[:60]
            pixels = {data[i:i + 3] for i in range(60, len(data), 3)}
            assert pixels == {b'\0\0\0', b'\xff\xff\xff'}, pixels
            (root / 'ack').write_bytes(b'')
            both = marker('ZX_VIEWER_PLUMBED_NEW')
            assert len(both) == 2, both
            (root / 'ack').write_bytes(b'')
            until(lambda: b'ZX_VIEWER_OK' in transcript or (select.select([shell.stdout], [], [], 0)[0] and
                  transcript.extend(shell.stdout.read1(1024))), 'viewer probe did not finish', timeout=20)
        except (AssertionError, subprocess.SubprocessError) as error:
            failure = ROOT / 'build/zx-smoke/viewer-failure.png'
            shot = desktop('import', '-window', window, 'png:-', check=False)
            if shot:
                failure.write_bytes(shot)
            stop(shell)
            transcript.extend(shell.stdout.read(4096))
            raise AssertionError((str(error), bytes(transcript[-2048:]), str(failure))) from error
        finally:
            stop(shell)
            shell.stdout.close()
    print('The ZX image viewer animated a GIF, opened a second file in its own window, showed a file '
          'plumbed to the view port and the next in a new window, and saved an Inferno image')


def catalog_programs(catalog):
    """Map each graphical entry the menu shows to the guest program it starts."""
    programs = {}
    for entry in sorted(catalog.glob('*.desktop')):
        lines = entry.read_text(encoding='utf-8').splitlines()
        fields = dict(line.split('=', 1) for line in lines if '=' in line)
        if fields.get('NoDisplay') != 'true' and fields.get('Terminal') != 'true':
            programs[entry.name] = fields['Exec'].split()[0]
    return programs


def check_catalog_apps(emulator, root, env):
    from PIL import Image
    from test_logwindow import private_display
    from test_tcltk import launch, stop, until

    catalog = ROOT / 'lib/apps'
    assert any(catalog.glob('*.desktop')), 'run tools/generate-app-catalog.py --guest-assets first'
    wm = ROOT / 'appl/wm'
    bundles = root / 'zx/wm'
    bundles.mkdir(parents=True)
    for bundle in sorted((ROOT / 'zx/wm').glob('*.zx')):
        if bundle.stem not in ('rill', 'desktop_panel', 'wm'):
            shutil.copy2(bundle, bundles / bundle.name)
    # Coffee and Man are Tcl/Tk apps installed under /zx, not /zx/wm.
    for name in ('coffee', 'man'):
        if (ROOT / 'zx' / f'{name}.zx').exists():
            shutil.copy2(ROOT / 'zx' / f'{name}.zx', root / 'zx' / f'{name}.zx')
    # Colours and Date are built here until the installer ships them.
    for name, module, hosts in (('colors', 'colors', ('taijios_draw',)), ('date', 'date_window', ('taijios_files',))):
        if not (bundles / f'{name}.zx').exists():
            subprocess.run([
                'ziran', 'bundle', '--project', '--module-path', '../cmd', '--bind-host', 'kryon/pixmap',
                *(word for host in hosts for word in ('--bind-host', host)),
                '--entry', f'{module}:main', '-o', bundles / f'{name}.zx', f'{module}.zi',
            ], cwd=wm, env=env, check=True, timeout=120)
    # The generator names the ZX bundle once it is installed; do the same for the staged ones.
    (root / 'lib/apps').mkdir(parents=True)
    for entry in sorted(catalog.glob('*.desktop')):
        text = entry.read_text(encoding='utf-8')
        program = next((line[5:].split()[0] for line in text.splitlines() if line.startswith('Exec=')), '')
        if program.endswith('.dis') and (root / program[1:]).with_suffix('.zx').exists():
            text = text.replace(program, program[:-4] + '.zx')
        (root / 'lib/apps' / entry.name).write_text(text, encoding='utf-8')
    for name in ('fonts', 'icons', 'lib/rill', 'man'):
        if (ROOT / name).exists():
            (root / name).symlink_to(ROOT / name, target_is_directory=True)
    # Polyhedra reads its solid database from /lib, so the minimal guest root ships it too.
    shutil.copy2(ROOT / 'lib/polyhedra.all', root / 'lib/polyhedra.all')
    (root / 'appl/cmd/tcltk').mkdir(parents=True)
    for script in (ROOT / 'appl/cmd/tcltk').glob('*.tcl'):
        shutil.copy2(script, root / 'appl/cmd/tcltk' / script.name)
    for name in ('tmp', 'usr/inferno'):
        (root / name).mkdir(parents=True, exist_ok=True)
    source = Path(__file__).with_name('zx_app_compat.zi')
    subprocess.run([
        'ziran', 'bundle', '--root', source.parent, '--module-path', ROOT / 'appl/cmd',
        '--module-path', ROOT / 'appl/cmd/tcltk', '--bind-host', 'taijios_desktop',
        '--bind-host', 'taijios_wm', '--bind-host', 'taijios_args', '--bind-host', 'zx_surface',
        '--bind-host', 'taijios_io', '--entry', 'zx_app_compat:main', '-o', bundles / 'rill.zx', source,
    ], env=env, check=True, timeout=60)
    # Installed like this, the window manager and its desktop are the session the emulator starts.
    shutil.copy2(root / 'wm.zx', bundles / 'wm.zx')
    assert not any(path.suffix == '.dis' for path in root.rglob('*') if not path.is_symlink())

    programs = catalog_programs(root / 'lib/apps')
    # No Dis module can start here, so the menu must not offer one even when its file exists.
    (bundles / 'legacy.dis').write_bytes(b'not a Dis module')
    (root / 'lib/apps/org.taijiosnet.wm-legacy.desktop').write_text(
        '[Desktop Entry]\nType=Application\nName=Legacy\nExec=/zx/wm/legacy.dis\n'
        'TryExec=/zx/wm/legacy.dis\nTerminal=false\n', encoding='utf-8')
    expected = sorted(Path(program).stem for program in programs.values()
                      if program.endswith('.zx') and (root / program[1:]).exists())
    need_dis = sorted(Path(program).stem for program in programs.values() if program.endswith('.dis'))
    assert expected, 'no ZX application bundles are installed in zx/wm'

    with private_display() as display:
        private_env = env | {'DISPLAY': display['DISPLAY']}
        shell = launch(private_env, emulator, '-v', '-r', root, '-g', '1024x768',
                       stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        transcript = bytearray()
        handled = 0
        seen = {'ZX_APP_OPEN': [], 'ZX_APP_RESIZED': []}

        def desktop(*args, check=True):
            return subprocess.run(args, env=private_env, capture_output=True, check=check, timeout=5).stdout

        def painted(window, x, y, width, height):
            frame = Image.open(io.BytesIO(desktop('import', '-window', window, 'png:-'))).convert('RGB')
            content = frame.crop((x, y, x + width, y + height))
            # The desktop background shows wherever the application has not drawn its current size.
            colors = [(count, rgb) for count, rgb in content.getcolors(width * height) or []
                      if rgb != (24, 56, 88)]
            return len(colors) >= 2 and sum(count for count, _ in colors) >= 0.98 * width * height

        try:
            window = until(lambda: desktop('xdotool', 'search', '--onlyvisible', '--name',
                                           '^inferno$', check=False).decode().strip(), 'ZX desktop window missing')
            deadline = time.monotonic() + 40 * len(expected)
            while b'ZX_APPS_OK' not in transcript:
                assert time.monotonic() < deadline, 'catalog applications took too long'
                if select.select([shell.stdout], [], [], 0.2)[0]:
                    data = shell.stdout.read1(4096)
                    assert data, 'the desktop exited early'
                    transcript.extend(data)
                lines = transcript.split(b'\n')[:-1]
                for line in lines[handled:]:
                    words = line.decode(errors='replace').split()
                    if len(words) == 6 and words[0] in seen:
                        name, bounds = words[1], tuple(map(int, words[2:]))
                        until(lambda: painted(window, *bounds), f'{name} did not paint its window ({words[0]})',
                              timeout=20)
                        seen[words[0]].append(name)
                        (root / 'ack').write_bytes(b'')
                handled = len(lines)
            status = shell.wait(timeout=10)
            transcript.extend(shell.stdout.read(4096))
            assert status == 0, f'the desktop exited with status {status}'
            assert b'Initial ZX: "/zx/wm/wm.zx"' in transcript and b'Initial Dis:' not in transcript
            assert sorted(seen['ZX_APP_OPEN']) == sorted(seen['ZX_APP_RESIZED']) == expected, (seen, expected)
            assert f'ZX_APPS_OK {len(expected)}\n'.encode() in transcript
        except (AssertionError, subprocess.SubprocessError) as error:
            stop(shell)
            transcript.extend(shell.stdout.read(4096))
            raise AssertionError((str(error), bytes(transcript[-2048:]))) from error
        finally:
            stop(shell)
            shell.stdout.close()
    print(f'Started without a command, the emulator opened the ZX desktop, which opened, focused, moved, resized '
          f'and closed {len(expected)} catalog applications without Dis: {" ".join(expected)}')
    print(f'{len(need_dis)} catalog applications still need Dis: {" ".join(need_dis)}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--emu', type=Path, default=ROOT / 'emu/Linux/o.emu')
    parser.add_argument('--graphics', action='store_true', help='exercise Draw and input in a private Xvfb')
    args = parser.parse_args()
    emulator = args.emu.resolve()
    env = os.environ.copy()
    for name in ('DISPLAY', 'WAYLAND_DISPLAY', 'XAUTHORITY', 'DBUS_SESSION_BUS_ADDRESS',
                 'XDG_RUNTIME_DIR', 'XDG_SESSION_ID', 'WAYLAND_SOCKET', 'SESSION_MANAGER',
                 'ICEAUTHORITY', 'HARMONY_GUEST_DISPLAY', 'EMU'):
        env.pop(name, None)
    env['HARMONY_DESKTOP_RECOVERY'] = '0'

    build = ROOT / 'build/zx-smoke'
    build.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=build, prefix='zx-boot-') as folder:
        root = Path(folder)
        probe = root / 'probe.zi'
        probe.write_text(PROBE, encoding='utf-8')
        (root / 'input').write_bytes(b'ZX')
        (root / 'damaged.zx').write_bytes(b'not a bundle')
        subprocess.run([
            'ziran', 'bundle', '--root', root, '--module-path', ROOT / 'appl/cmd',
            '--bind-host', 'taijios_args', '--bind-host', 'taijios_io',
            '--bind-host', 'taijios_process', '--bind-host', 'taijios_tasks',
            '--entry', 'probe:main', '-o', root / 'probe.zx', probe,
        ], env=env, check=True, timeout=60)
        plain = root / 'plain.zi'
        plain.write_text('main :: () { print("ZX_VOID_OK\\n"); }\n', encoding='ascii')
        subprocess.run([
            'ziran', 'bundle', '--root', root, '--entry', 'plain:main',
            '-o', root / 'plain.zx', plain,
        ], env=env, check=True, timeout=60)
        commands = ROOT / 'appl/cmd'
        subprocess.run([
            'ziran', 'bundle', '--root', commands, '--bind-host', 'taijios_args',
            '--bind-host', 'taijios_io', '--bind-host', 'taijios_process',
            '--entry', 'zxrun:main', '-o', root / 'zxrun.zx', commands / 'zxrun.zi',
        ], env=env, check=True, timeout=60)
        assert not any(root.rglob('*.dis'))

        def boot(*args, stdin='', timeout=15, **overrides):
            return subprocess.run(
                [emulator, '-v', '-r', root, *args], env=env | overrides,
                input=stdin, capture_output=True, text=True,
                start_new_session=True, timeout=timeout,
            )

        operands = ('-test', 'café 猫', '')
        for result in (boot('--', '/probe.zx', *operands), boot('-d', '/probe.zx', '--', *operands),
                       boot('--', *operands, EMU='-d /probe.zx')):
            assert result.returncode == 0 and not result.stderr, result
            assert 'Initial ZX: "/probe.zx"' in result.stdout and 'ZX_BOOT_OK' in result.stdout, result
            assert 'Initial Dis:' not in result.stdout, result

        result = boot('/plain.zx')
        assert result.returncode == 0 and 'ZX_VOID_OK' in result.stdout and not result.stderr, result
        result = boot('/probe.zx', 'streams', stdin='X\n')
        assert result.returncode == 0 and result.stdout.splitlines()[-1] == 'out', result
        assert result.stderr == 'err\n', result
        failed = boot('/probe.zx', 'fail')
        assert failed.returncode == 23 and 'requested failure' in failed.stderr, failed
        for operand in ('negative', 'out of range'):
            failed = boot('/probe.zx', operand)
            assert failed.returncode == 1, failed
        for path in ('/missing.zx', '/damaged.zx'):
            failed = boot(path)
            assert failed.returncode == 1 and f'emu: {path}:' in failed.stderr, failed
            assert 'Initial Dis:' not in failed.stdout, failed
        print('Direct ZX boot, arguments, namespace, standard streams, exit statuses and loader errors passed')
        check_command_names(emulator, root, env, boot, operands)

        children = boot('/zxrun.zx', '-c', '/probe.zx', 'children')
        assert children.returncode == 0 and 'ZX_VOID_OK' in children.stdout and not children.stderr, children
        command = boot('/zxrun.zx', '-c', '/probe.zx', *operands)
        assert command.returncode == 0 and 'ZX_BOOT_OK' in command.stdout and not command.stderr, command
        command = boot('/zxrun.zx', '-c', '/probe.zx', 'streams', stdin='X\n')
        assert command.returncode == 0 and command.stdout.splitlines()[-1] == 'out', command
        assert command.stderr == 'err\n', command
        command = boot('/zxrun.zx', '/probe.zx', 'fail')
        assert command.returncode == 0 and command.stdout.splitlines()[-1] == '23' and not command.stderr, command
        command = boot('/zxrun.zx', '/probe.zx', 'wide')
        assert command.returncode == 0 and command.stdout.splitlines()[-1] == '1099511627783' and not command.stderr, command
        command = boot('/zxrun.zx', '-c', '/probe.zx', 'fail')
        assert command.returncode == 23 and not command.stderr, command
        command = boot('/zxrun.zx', '-s', '/probe.zx', 'fail')
        assert command.returncode == 23 and 'requested failure' in command.stderr, command
        command = boot('/zxrun.zx', '/missing.zx')
        assert command.returncode == 1 and 'zxrun: /missing.zx:' in command.stderr, command
        print('Direct ZX runner launched child bundles with inherited streams and preserved scalar and named results')
        check_async(emulator, root, env)
        check_kill(emulator, root, env)
        tasks = boot('/probe.zx', 'tasks')
        assert tasks.returncode == 0 and 'ZX_TASKS_OK' in tasks.stdout and not tasks.stderr, tasks
        print('Without Dis, the task list showed running ZX processes and terminated one through the kill path')
        check_namespace(root, env, boot)
        check_hosted_process(emulator, root, env)
        check_services(root, env, boot)
        check_keyring(root, env, boot)
        if args.graphics:
            check_draw(emulator, root, env)
            check_window_manager(emulator, root, env)
            check_tertiary_pointer(emulator, root, env)
            check_event_queue_overflow(emulator, root, env)
            check_desktop_shell(emulator, root, env)
            check_catalog_apps(emulator, root, env)
            check_image_viewer(emulator, root, env)


if __name__ == '__main__':
    main()
