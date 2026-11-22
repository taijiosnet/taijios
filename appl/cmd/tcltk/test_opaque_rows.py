"""Drive the row-upload protocol on a private X11 display."""
import argparse
from pathlib import Path

from test_logwindow import private_display
import test_tcltk as tk

def exercise(x, y, click, _keys, _text, capture, transcript):
    box = (x, y, x+300, y+96)
    click(x+20, y+10)
    tk.until(lambda: b'partial' in transcript(), 'strip upload did not start')
    assert capture().crop(box).getcolors() == [(300*96, (244, 246, 247))]
    click(x+20, y+10)
    tk.until(lambda: b'complete' in transcript(), 'complete frame was never acknowledged')
    shown = capture().crop(box)
    for index, color in enumerate(((90, 50, 20), (20, 90, 50), (50, 20, 90))):
        assert shown.crop((0, 32*index, 300, 32*(index+1))).getcolors() == [(300*32, color)]
    click(x+20, y+10)
    tk.until(lambda: b'rgb' in transcript(), 'packed RGB strip was not acknowledged')
    shown = capture().crop(box)
    for index, color in enumerate(((90, 50, 20), (17, 34, 51), (50, 20, 90))):
        assert shown.crop((0, 32*index, 300, 32*(index+1))).getcolors() == [(300*32, color)]
    click(x+20, y+10)
    return ['partial', 'complete', 'rgb']


def main():
    args = argparse.ArgumentParser()
    args.add_argument('--emulator', type=Path, default=tk.EMU)
    tk.EMU = args.parse_args().emulator.resolve()
    tk.BUILD.mkdir(parents=True, exist_ok=True)
    image = tk.BUILD / 'opaque_rows_test.zx'
    tk.compile_image('opaque_rows_test', image, '--bind-host', 'zx_surface', '--bind-host', 'taijios_clock')
    with private_display() as display:
        tk.interaction(display, image, None, exercise, size=(300, 96))
    print('ZX row uploads rejected malformed rows; RGBA and packed RGB pixels match, including untouched rows')


if __name__ == '__main__':
    main()
