"""Launch the Linux emulator on a guest filesystem containing only ZX programs."""

import argparse
import io
import os
import select
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
        'ziran', 'bundle', '--root', wm, '--module-path', ROOT / 'appl/cmd',
        '--module-path', ROOT / 'appl/lib', '--module-path', surfaces,
        '--bind-host', 'taijios_args', '--bind-host', 'taijios_io',
        '--bind-host', 'taijios_process', '--bind-host', 'taijios_native_wm',
        '--entry', 'native_wm:main', '-o', root / 'wm.zx', wm / 'native_wm.zi',
    ], env=env, check=True, timeout=60)
    fixture = Path(__file__).with_name('zx_window_app.zi').read_text(encoding='utf-8')
    for red in (37, 108):
        source = root / 'zx_window_app.zi'
        source.write_text(fixture.replace('Color :: 37;', f'Color :: {red};'), encoding='utf-8')
        subprocess.run([
            'ziran', 'bundle', '--root', root, '--module-path', surfaces, '--module-path', ROOT / 'appl/cmd',
            '--bind-host', 'zx_surface', '--bind-host', 'taijios_args',
            '--entry', 'zx_window_app:main', '-o', root / f'window{red}.zx', source,
        ], env=env, check=True, timeout=60)
    assert not any(root.rglob('*.dis'))

    with private_display() as display:
        env = env | {'DISPLAY': display['DISPLAY']}
        app = launch(env, emulator, '-v', '-r', root, '-g', '640x480', '/wm.zx',
                     '/window37.zx', '/window108.zx', stdin=subprocess.DEVNULL,
                     stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

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


def check_desktop_shell(emulator, root, env):
    from test_logwindow import private_display

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
        shell = subprocess.run(app + ['--desktop', '/shell.zx'], env=private_env, stdin=subprocess.DEVNULL,
                               capture_output=True, text=True, start_new_session=True, timeout=10)
        assert shell.returncode == 0 and not shell.stderr and 'Initial Dis:' not in shell.stdout, shell
        for marker in ('ZX_DESKTOP_PROTOCOL_OK', 'ZX_DESKTOP_CHILD_RESIZED', 'ZX_DESKTOP_CHILD_CLOSED'):
            assert marker in shell.stdout, shell
    print('Private ZX shell owned the desktop, launched a window, and controlled its workspace, size and lifecycle')


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
            '--bind-host', 'taijios_process',
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

        def boot(*args, stdin='', **overrides):
            return subprocess.run(
                [emulator, '-v', '-r', root, *args], env=env | overrides,
                input=stdin, capture_output=True, text=True,
                start_new_session=True, timeout=15,
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
        if args.graphics:
            check_draw(emulator, root, env)
            check_window_manager(emulator, root, env)
            check_desktop_shell(emulator, root, env)


if __name__ == '__main__':
    main()
