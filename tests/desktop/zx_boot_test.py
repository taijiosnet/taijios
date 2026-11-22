"""Launch the Linux emulator on a guest filesystem containing only ZX programs."""

import argparse
import io
import os
import select
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory


ROOT = Path(__file__).resolve().parents[2]
PROBE = '''
using Args :: #import "taijios_args";
using Io :: #import "taijios_io";

main :: () -> s32 {
    input_bytes: [8]u8;
    if Args.Operand(0) == "streams" {
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


def check_draw(emulator, root, env):
    from PIL import Image

    sys.path.insert(0, str(ROOT / 'appl/cmd/tcltk'))
    from test_logwindow import private_display
    from test_tcltk import launch, stop, until

    probe = Path(__file__).with_name('zx_boot_draw.zi')
    subprocess.run([
        'ziran', 'bundle', '--root', probe.parent, '--module-path', ROOT / 'appl/cmd',
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
            desktop('xdotool', 'windowfocus', window)
            desktop('xdotool', 'key', 'a')
            until(lambda: received(b'ZX_DRAW_KEY_OK'), 'guest keyboard did not deliver input')
            assert app.wait(timeout=5) == 0
        except (AssertionError, subprocess.SubprocessError) as error:
            raise AssertionError(f'{error}\n{transcript.decode(errors="replace")}') from error
        finally:
            stop(app)
            app.stdout.close()
    print('Private ZX-only guest drew a frame and received a key through its guest devices')


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
            '--entry', 'probe:main', '-o', root / 'probe.zx', probe,
        ], env=env, check=True, timeout=60)
        plain = root / 'plain.zi'
        plain.write_text('main :: () { print("ZX_VOID_OK\\n"); }\n', encoding='ascii')
        subprocess.run([
            'ziran', 'bundle', '--root', root, '--entry', 'plain:main',
            '-o', root / 'plain.zx', plain,
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
        if args.graphics:
            check_draw(emulator, root, env)


if __name__ == '__main__':
    main()
