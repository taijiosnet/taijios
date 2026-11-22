"""Check stationary clicks, motion, dragging and wheels through the ZX runner."""
import argparse
import io
import subprocess
from pathlib import Path

from PIL import Image
from test_logwindow import private_display
import test_tcltk as tk


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', type=Path, required=True)
    args = parser.parse_args()
    runner = args.runner.resolve()
    assert runner.name == 'zxrun.dis'
    image = tk.BUILD / 'pointer_events_test.zx'
    tk.compile_image('pointer_events_test', image, '--bind-host', 'zx_surface')
    with private_display() as env:
        prefix = '/' + runner.parent.relative_to(tk.ROOT).as_posix()
        fixture = '/' + image.relative_to(tk.ROOT).as_posix()
        run = f"bind -b {prefix} /dis; wm/wm /dis/sh.dis -c 'zxrun -w {fixture}'"
        app = tk.launch(env, tk.EMU, '-p', 'main=128M', '-r', tk.ROOT, '-g', '800x600',
                        '/dis/sh.dis', '-c', run, stdin=subprocess.DEVNULL,
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output = bytearray()

        def transcript():
            from test_logwindow import read_output
            read_output(app, output)
            return output.decode()

        try:
            window = tk.until(lambda: tk.command('xdotool', 'search', '--onlyvisible', '--name',
                              '^inferno$', env=env, capture_output=True, text=True).stdout.strip(),
                              'private emulator did not map')

            def canvas():
                transcript()
                shot = tk.command('import', '-window', window, 'png:-', env=env,
                                  capture_output=True, check=True)
                bounds = tk.color_bounds(Image.open(io.BytesIO(shot.stdout)).convert('RGB'), tk.BACKGROUND)
                return bounds if bounds and (bounds[2]-bounds[0], bounds[3]-bounds[1]) == (300, 96) else None

            x, y, _, _ = tk.until(canvas, 'pointer fixture did not paint')

            def action(*arguments):
                tk.command('xdotool', *arguments, env=env, check=True)

            def move(dx, dy):
                action('mousemove', '--sync', '--window', window, str(x+dx), str(y+dy))

            action('windowfocus', window)
            move(20, 10)
            action('mousedown', '1', 'sleep', '0.15', 'mouseup', '1')
            tk.until(lambda: 'FOCUSED\n' in transcript(), 'initial click did not focus the guest')
            action('key', 'a')
            tk.until(lambda: 'ARMED\n' in transcript(), 'pointer fixture did not arm')
            action('mousedown', '1', 'sleep', '0.15', 'mouseup', '1')
            tk.until(lambda: 'RELEASED 1\n' in transcript(), 'stationary button release did not arrive')
            action('key', 'b')
            tk.until(lambda: 'STATIONARY_OK\n' in transcript(), 'stationary click added motion or lost a button')
            move(40, 25)
            action('mousedown', '1')
            move(60, 35)
            action('mouseup', '1')
            tk.until(lambda: 'RELEASED 2\n' in transcript(), 'drag release did not arrive')
            action('mousedown', '4', 'sleep', '0.15', 'mouseup', '4')
            tk.until(lambda: 'WHEEL_UP\n' in transcript(), 'upward wheel did not arrive')
            action('mousedown', '5', 'sleep', '0.15', 'mouseup', '5')
            tk.until(lambda: 'WHEEL_DOWN\n' in transcript(), 'downward wheel did not arrive')
            action('key', 'c')
            tk.until(lambda: 'MOTION_DRAG_WHEEL_OK\n' in transcript() and transcript().endswith('\n0\n'),
                     'motion, dragging or wheels were lost')
            print('ZX stationary clicks avoid extra motion; movement, drag coordinates and both wheels passed at 128 MiB')
        except Exception:
            print(transcript())
            raise
        finally:
            tk.stop(app)
            app.stdout.close()
            app.stderr.close()


if __name__ == '__main__':
    main()
