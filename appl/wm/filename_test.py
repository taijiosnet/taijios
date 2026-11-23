#!/usr/bin/env python3
"""Check the ZX File Chooser's model and its window in a private TaijiOS guest."""
import io
import subprocess
import tempfile
from pathlib import Path

from PIL import Image

from wm_app_test import arguments
from kryon_apps_test import guest_overlay
from test_logwindow import private_display
from test_tcltk import BUILD, ROOT, launch, stop, until

HERE = ROOT / 'appl/wm'
DIRECTORY = 'chooser'
FILE = 'chosen.zi'


def check_model(env):
    """Bundle and run filename_model_test.zi on the engine backend."""
    BUILD.mkdir(parents=True, exist_ok=True)
    bundle = BUILD / 'filename_model_test.zx'
    subprocess.run(['ziran', 'bundle', '--project', '--entry',
                    'filename_model_test:main', '-o', bundle, 'filename_model_test.zi'],
                   cwd=HERE, env=env, check=True, timeout=180)
    result = subprocess.run(['zi2zx', 'run', '--backend', 'engine', bundle], env=env,
                            capture_output=True, text=True, check=True, timeout=180)
    lines = result.stdout.splitlines()
    assert len(lines) == 2 and lines[1] == '0' and not result.stderr, result
    assert lines[0] == 'filename_model_test ok', lines
    print('The File Chooser parsed -d, -t and patterns, matched globs and took paths apart as filename.b did')


TITLE_BACKGROUND = (12, 14, 20)
ACTIVE_TITLE = (146, 155, 168)


def window_rect(image):
    """The focused window's rectangle, from the caption ink on the active title bar."""
    pixels = image.tobytes()
    ink = bytes(ACTIVE_TITLE)
    caption = [i // 3 for i in range(0, len(pixels), 3) if pixels[i:i+3] == ink]
    if not caption:
        return None
    xs = [i % image.width for i in caption]
    ys = [i // image.width for i in caption]
    x, y = (min(xs) + max(xs)) // 2, min(ys)

    def dark(px, py):
        return 0 <= px < image.width and 0 <= py < image.height and image.getpixel((px, py)) == TITLE_BACKGROUND

    top = y
    while dark(x, top - 1):
        top -= 1
    bottom = max(ys)
    while dark(x, bottom + 1):
        bottom += 1
    left = right = x
    while dark(left - 1, top + 1):
        left -= 1
    while dark(right + 1, top + 1):
        right += 1
    return left, top, right + 1, bottom + 1


def exercise(args, env, root):
    directory = root / DIRECTORY
    directory.mkdir(parents=True, exist_ok=True)
    (directory / 'folder').mkdir(exist_ok=True)
    (directory / FILE).write_text('Selected by the ZX File Chooser.\n', encoding='utf-8')
    bundle = '/' + (ROOT / 'dis/wm/filename.zx').relative_to(ROOT).as_posix()
    # The guest is rooted at ROOT, so the fixture is named without the host prefix.
    inside = '/' + directory.relative_to(ROOT).as_posix()
    command = guest_overlay(getattr(args, 'guest_overlay', None))
    command += f"wm/wm zxrun -w {bundle} -d '{inside}'"
    child = launch(env, args.emu, '-p', 'main=128M', '-r', ROOT, '-g', '640x480', '/dis/sh.dis', '-c',
                   command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    try:
        def x(*command, check=True):
            return subprocess.run(command, env=env, capture_output=True, check=check, timeout=5).stdout

        window = until(lambda: x('xdotool', 'search', '--onlyvisible', '--name', '^inferno$', check=False).strip(),
                       'private guest did not open').decode().split()[0]

        def capture():
            return Image.open(io.BytesIO(x('import', '-window', window, 'png:-'))).convert('RGB')

        def click(xpos, ypos):
            x('xdotool', 'mousemove', '--window', window, str(xpos), str(ypos),
              'sleep', '0.05', 'mousedown', '1', 'sleep', '0.08', 'mouseup', '1', 'sleep', '0.15')

        def painted():
            image = capture()
            colors = image.getcolors(image.width * image.height) or []
            light = sum(count for count, rgb in colors if min(rgb) > 200)
            dark = sum(count for count, rgb in colors if max(rgb) < 60)
            return light > 20000 and dark > 2000

        until(painted, 'the ZX File Chooser did not paint its columns')
        left, top, right, bar_bottom = until(lambda: window_rect(capture()),
                                             'the File Chooser title bar did not appear')
        # The client area starts under the title bar. With -d the fixture is already
        # the first column, so the file's row is the first entry under the header.
        body_top = bar_bottom + 1
        image = capture()
        # The chooser's own bottom is the last row painted in its client colours;
        # below it the desktop begins. The path row's buttons are 40 rows above.
        client = (242, 244, 248)
        window_bottom = bar_bottom
        for py in range(bar_bottom + 1, image.height):
            if image.getpixel((left + 4, py)) == client or image.getpixel((right - 4, py)) == client:
                window_bottom = py
        # The first entry under the first column's header is the file.
        click(left + 8 + 90, body_top + 8 + 26 + 12)
        # The selection fills the path row; OK accepts it and ends the program.
        click(right - 8 - 74 - 8 - 37, window_bottom - 16)
        until(lambda: window_rect(capture()) is None, 'OK did not close the File Chooser')
        print('The ZX File Chooser opened on -d, listed the directory, selected the file and accepted with OK')
    finally:
        stop(child)


def main():
    args = arguments(__doc__, 'filename.zx')
    if not args.bundle.exists():
        raise SystemExit(f'{args.bundle} is missing; run mk filename.zx first')
    with tempfile.TemporaryDirectory(dir=BUILD) as directory, private_display() as env:
        check_model(env)
        exercise(args, env, Path(directory))


if __name__ == '__main__':
    main()
