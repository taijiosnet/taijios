"""Shared steps for the tests of the desktop apps rewritten from Limbo."""
import io
from pathlib import Path
import subprocess
import sys
import time

from PIL import Image, ImageOps

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'cmd/tcltk'))
from kryon_apps_test import guest_overlay  # noqa: E402
from test_logwindow import private_display  # noqa: E402,F401
from test_tcltk import ROOT, launch, stop, until  # noqa: E402,F401

HERE = Path(__file__).resolve().parent
BUILD = ROOT / 'build/wm-apps'
EMU = ROOT / 'emu/Linux/o.emu'


def run_model(name, fixture, env):
    """Bundle <name>_model_test.zi with the fixture as the module <fixture stem>_fixture and run it.

    Ziran source lines stay under 4096 bytes, so long fixture lines continue after a
    trailing backslash; the model tests join them again.
    """
    BUILD.mkdir(parents=True, exist_ok=True)
    folder = BUILD / f'{name}-fixture'
    folder.mkdir(exist_ok=True)
    wrapped = []
    for line in (HERE / fixture).read_text(encoding='utf-8').splitlines():
        while len(line) > 500:
            wrapped.append(line[:500] + '\\')
            line = line[500:]
        wrapped.append(line)
    text = ''.join(line + '\n' for line in wrapped)
    module = Path(fixture).stem + '_fixture'
    (folder / f'{module}.zi').write_text(f'Games :: #string GAMES_END\n{text}GAMES_END;\n', encoding='utf-8')
    bundle = BUILD / f'{name}_model_test.zx'
    subprocess.run(['ziran', 'bundle', '--project', '--module-path', folder, '--entry', f'{name}_model_test:main',
                    '-o', bundle, f'{name}_model_test.zi'], cwd=HERE, env=env, check=True, timeout=180)
    result = subprocess.run(['zi2zx', 'run', '--backend', 'engine', bundle], env=env,
                            capture_output=True, text=True, check=True, timeout=180)
    lines = result.stdout.splitlines()
    assert len(lines) == 2 and lines[1] == '0' and not result.stderr, result
    return lines[0]


def ocr(image, box, scale=4, digits=False):
    """Read one line of text; digits=True reads a number on a plain background."""
    crop = image.crop(box)
    options = []
    if digits:
        crop = crop.convert('L').resize((crop.width * 5, crop.height * 5), Image.LANCZOS)
        crop = ImageOps.expand(crop, border=30, fill=221)
        options = ['-c', 'tessedit_char_whitelist=0123456789']
    else:
        crop = crop.resize((crop.width * scale, crop.height * scale))
    png = io.BytesIO()
    crop.save(png, format='PNG')
    return subprocess.run(['tesseract', 'stdin', 'stdout', '--psm', '7', *options], input=png.getvalue(),
                          capture_output=True, check=True, timeout=5).stdout.decode().strip()


class Guest:
    """One ZX app in the legacy desktop of a private guest, rooted at this checkout."""

    def __init__(self, env, args, operands=(), setup='', size='640x480'):
        bundle = '/' + args.bundle.resolve().relative_to(ROOT).as_posix()
        command = setup + f'wm/wm zxrun -w {bundle}' + ''.join(f" '{word}'" for word in operands)
        self.env = env
        self.app = launch(env, args.emu, '-p', 'main=128M', '-r', ROOT, '-g', size, '/dis/sh.dis', '-c',
                          guest_overlay(getattr(args, 'guest_overlay', None)) + command, stdin=subprocess.DEVNULL)
        self.window = until(lambda: self.run('xdotool', 'search', '--onlyvisible', '--name', '^inferno$',
                                             check=False).strip(), 'private guest did not open').decode().split()[0]

    def __enter__(self):
        return self

    def __exit__(self, *failure):
        stop(self.app)

    def run(self, *command, check=True):
        return subprocess.run(command, env=self.env, capture_output=True, check=check, timeout=10).stdout

    def capture(self):
        return Image.open(io.BytesIO(self.run('import', '-window', self.window, 'png:-'))).convert('RGB')

    def settled(self, ready, description, timeout=60, name='failure'):
        """Two identical captures 0.6 s apart for which ready(image) holds."""
        def still():
            first = self.capture()
            if not ready(first):
                return None
            time.sleep(0.6)
            second = self.capture()
            return second if first.tobytes() == second.tobytes() else None
        try:
            return until(still, description, timeout=timeout)
        except AssertionError:
            self.capture().save(BUILD / f'{name}.png')
            raise

    def key(self, *names):
        self.run('xdotool', 'key', '--window', self.window, *names)
        time.sleep(0.15)

    def move(self, x, y):
        self.run('xdotool', 'mousemove', '--window', self.window, str(x), str(y), 'sleep', '0.1')

    def click(self, x, y, button=1):
        self.run('xdotool', 'mousemove', '--window', self.window, str(x), str(y), 'sleep', '0.05',
                 'mousedown', str(button), 'sleep', '0.08', 'mouseup', str(button), 'sleep', '0.1')


def arguments(description, bundle):
    import argparse
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('bundle', type=Path, nargs='?', default=ROOT / 'dis/wm' / bundle)
    parser.add_argument('--emu', type=Path, default=EMU)
    parser.add_argument('--guest-overlay', type=Path)
    args = parser.parse_args()
    import os
    for name in ('XDG_RUNTIME_DIR', 'XDG_SESSION_ID', 'SESSION_MANAGER', 'HARMONY_GUEST_DISPLAY'):
        os.environ.pop(name, None)
    return args
