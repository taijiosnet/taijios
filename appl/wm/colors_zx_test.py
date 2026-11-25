#!/usr/bin/env python3
"""Compare the ZX palette with Draw's CMAP8 in a private TaijiOS guest."""
import argparse
import ctypes
import io
import os
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory

from PIL import Image

from kryon_apps_test import guest_overlay, wait_start
from test_logwindow import private_display
from test_tcltk import EMU, ROOT, launch, stop, until


def color_map(directory):
    library = Path(directory) / 'cmap.so'
    subprocess.run(['cc', '-shared', '-fPIC', '-Iinclude', '-ILinux/386/include',
                    'libdraw/rgb.c', '-o', library], cwd=ROOT, check=True)
    draw = ctypes.CDLL(str(library))
    packed = [draw.cmap2rgb(i) for i in range(256)]
    return draw, [(rgb >> 16, (rgb >> 8) & 255, rgb & 255) for rgb in packed]


def origin(screen, colors):
    pixels = screen.load()
    for y in range(1, screen.height - 255):
        for x in range(1, screen.width - 255):
            if pixels[x, y] != colors[0] or pixels[x - 1, y] == colors[0] or pixels[x, y - 1] == colors[0]:
                continue
            if all(pixels[x + 8 + 16 * c, y + 8] == colors[c] for c in range(16)):
                if all(pixels[x + 8, y + 8 + 16 * r] == colors[r * 16] for r in range(16)):
                    return x, y
    return None


def exercise(env, args, draw, colors):
    bundle = '/' + args.bundle.resolve().relative_to(ROOT).as_posix()
    command = f'wm/wm zxrun -w {bundle}'
    if args.menu:
        command = 'wm/wm wm/toolbar'
    elif args.compat:
        command = 'wm/wm wm/colors'
    guest = guest_overlay(args.guest_overlay) + command
    app = launch(env, args.emu, '-p', 'main=128M', '-r', ROOT, '-g', '800x600',
                 '/zx/sh.dis', '-c', guest, stdin=subprocess.DEVNULL)
    try:
        def run(*command, check=True):
            return subprocess.run(command, env=env, capture_output=True, check=check, timeout=5).stdout

        window = until(lambda: run('xdotool', 'search', '--onlyvisible', '--name', '^inferno$', check=False).strip(),
                       'private guest did not open').decode()

        def capture():
            return Image.open(io.BytesIO(run('import', '-window', window, 'png:-'))).convert('RGB')

        def mouse(x, y):
            return ('mousemove', '--window', window, str(x), str(y))

        if args.menu:
            wait_start(capture, False)
            run('xdotool', *mouse(36, 584), 'sleep', '.04', 'mousedown', '1', 'sleep', '.22',
                *mouse(45, 430), 'sleep', '.18', *mouse(230, 505), 'sleep', '.12', 'mouseup', '1')

        x, y = until(lambda: origin(capture(), colors), 'Colors did not paint the CMAP8 grid')

        def matches(width, height):
            pixels = capture().load()
            return all(pixels[x + i, y + j] == colors[(j * 16 // height) * 16 + i * 16 // width]
                       for j in range(height) for i in range(width))

        assert matches(256, 256), 'initial ZX palette differs from Draw'
        run('xdotool', *mouse(x + 248, y + 248), 'click', '1')

        def label():
            crop = capture().crop((x, y - 24, x + 256, y)).resize((1024, 96))
            png = io.BytesIO()
            crop.save(png, format='PNG')
            return subprocess.run(['tesseract', 'stdin', 'stdout', '--psm', '7'], input=png.getvalue(),
                                  capture_output=True, check=True, timeout=5).stdout.decode().strip()

        def expect_label(index, rgb):
            red, green, blue = rgb
            index_text = str(index) if colors[index] == rgb else f'~{index}'
            expected = f'col:{index_text} #{red:02X}{green:02X}{blue:02X} r{red} g{green} b{blue}'
            try:
                until(lambda: label().replace(' ', '') == expected.replace(' ', ''), f'Colors did not report {expected}')
            except AssertionError as failure:
                raise AssertionError(f'{failure}, saw {label()!r}') from failure

        expect_label(255, colors[255])
        screen = capture()
        candidates = ((18, 550), (780, 550), (780, 65))
        outside = next(point for point in candidates if screen.getpixel(point) != colors[255]
                       and not (x - 4 <= point[0] < x + 260 and y - 60 <= point[1] < y + 260))
        outside_color = screen.getpixel(outside)
        run('xdotool', *mouse(x + 248, y + 248), 'mousedown', '1', 'sleep', '.18',
            *mouse(*outside), 'sleep', '.20', 'mouseup', '1')
        expect_label(draw.rgb2cmap(*outside_color), outside_color)
        print('Colors sampled and described a pixel outside the palette within the guest')
        run('xdotool', *mouse(x + 253, y + 253), 'sleep', '.12', 'mousedown', '1', 'sleep', '.18',
            *mouse(x + 276, y + 294), 'sleep', '.20', 'mouseup', '1')
        until(lambda: matches(279, 297), 'resized ZX palette differs from Draw')
        run('xdotool', *mouse(x + 18, y + 19), 'click', '1')
        expect_label(17, colors[17])
        print('Colors rendered all 256 entries and kept cell selection aligned after resize')
    finally:
        stop(app)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('bundle', type=Path)
    parser.add_argument('--emu', type=Path, default=EMU)
    parser.add_argument('--guest-overlay', type=Path)
    launch_mode = parser.add_mutually_exclusive_group()
    launch_mode.add_argument('--menu', action='store_true', help='open the installed Colors bundle from Utilities')
    launch_mode.add_argument('--compat', action='store_true', help='launch through an existing Dis catalog entry')
    args = parser.parse_args()
    for name in ('XDG_RUNTIME_DIR', 'XDG_SESSION_ID', 'SESSION_MANAGER', 'HARMONY_GUEST_DISPLAY'):
        os.environ.pop(name, None)
    scratch = ROOT / 'build/desktop-registry'
    scratch.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=scratch) as directory, private_display() as env:
        exercise(env, args, *color_map(directory))


if __name__ == '__main__':
    main()
