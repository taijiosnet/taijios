"""Verify /dis/wm/wish.zx on a private display: stdin REPL, -f script, and GUI prompt."""

import io
import os
from pathlib import Path
import subprocess
import sys

from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
from test_logwindow import private_display  # noqa: E402
from test_tcltk import launch, stop, until  # noqa: E402


def clean_env():
    env = os.environ.copy()
    for name in ('DISPLAY', 'WAYLAND_DISPLAY', 'XAUTHORITY', 'DBUS_SESSION_BUS_ADDRESS',
                 'XDG_RUNTIME_DIR', 'XDG_SESSION_ID', 'WAYLAND_SOCKET', 'SESSION_MANAGER',
                 'ICEAUTHORITY', 'HARMONY_GUEST_DISPLAY', 'EMU'):
        env.pop(name, None)
    env['HARMONY_DESKTOP_RECOVERY'] = '0'
    return env


def test_stdin_and_file(emu, env):
    with private_display() as display:
        private_env = env | {'DISPLAY': display['DISPLAY']}
        # 1. Piped stdin evaluates multi-line Tcl and exits cleanly.
        script = 'set x 40\nif {$x == 40} {\n    puts [expr {$x + 2}]\n}\nexit\n'
        proc = subprocess.run(
            [emu, '-r', ROOT, '-g', '640x480', '/dis/wm/wm.zx', '/dis/wm/wish.zx'],
            env=private_env, input=script, capture_output=True, text=True,
            start_new_session=True, timeout=20,
        )
        assert proc.returncode == 0, (proc.returncode, proc.stdout, proc.stderr)
        assert '42\n' in proc.stdout, (proc.stdout, proc.stderr)

        # 2. -k -f loads and paints a Tk script file.
        app = launch(private_env, emu, '-r', ROOT, '-g', '640x480', '/dis/wm/wm.zx',
                     '/dis/wm/wish.zx', '-k', '-f', '/appl/cmd/tcltk/bounce_controls.tcl',
                     stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

        def desktop(*args, check=True):
            return subprocess.run(args, env=private_env, capture_output=True, check=check, timeout=5).stdout

        try:
            window = until(lambda: desktop('xdotool', 'search', '--onlyvisible', '--name',
                                           '^inferno$', check=False).decode().strip(), 'wish -f window missing')

            def painted():
                assert app.poll() is None, f'wish -f exited with {app.returncode}'
                frame = Image.open(io.BytesIO(desktop('import', '-window', window, 'png:-'))).convert('RGB')
                colors = [(c, rgb) for c, rgb in frame.crop((0, 0, 200, 100)).getcolors(20000) or []
                          if rgb != (24, 56, 88)]
                return len(colors) >= 3

            until(painted, 'wish -f did not paint bounce_controls.tcl')
        finally:
            stop(app)
            app.stdout.close()
    print('wish.zx evaluated multi-line stdin commands and painted -k -f bounce_controls.tcl')


def main():
    emu = ROOT / 'emu/Linux/o.emu'
    test_stdin_and_file(emu, clean_env())


if __name__ == '__main__':
    main()
