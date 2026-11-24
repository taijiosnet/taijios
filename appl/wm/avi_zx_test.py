#!/usr/bin/env python3
"""Check the ZX AVI Player decoder rules and live playback window in a private TaijiOS guest."""
import os
from pathlib import Path
import time

from wm_app_test import Guest, arguments, private_display, run_model, until

FACE = (221, 221, 221)
LIGHT = (255, 255, 255)
DARK = (173, 173, 173)
WIN_W, WIN_H = 360, 302
BAND_Y = 14


def check_model(env):
    message = run_model('avi', 'avi_sample.hex', env)
    assert message == 'AVI model matched 3 RLE8 frames of 32x24', message
    print('AVI model matched 3 RLE8 frames of 32x24')


def window_origin(image):
    pixels = image.load()
    for y in range(10, image.height - WIN_H + 1):
        for x in range(0, image.width - WIN_W + 1):
            if pixels[x, y] != FACE or pixels[x + WIN_W - 1, y] != FACE:
                continue
            # Top-left of "File" button bevel at (0, BAND_Y).
            if pixels[x, y + BAND_Y] == LIGHT and pixels[x + 41, y + BAND_Y + 17] == DARK \
                    and pixels[x + 175, y + BAND_Y + 17] == DARK:
                return x, y
    return None


def has_vivid_frame(image, origin):
    ox, oy = origin
    # The 32x24 sample is centered in the 360x270 canvas (y=32..302).
    cx = ox + (WIN_W - 32) // 2
    cy = oy + 32 + (270 - 24) // 2
    crop = image.crop((cx, cy, cx + 32, cy + 24))
    reds = greens = blues = 0
    for r, g, b in crop.get_flattened_data():
        if r > 200 and g < 50 and b < 50:
            reds += 1
        elif g > 200 and r < 50 and b < 50:
            greens += 1
        elif b > 200 and r < 50 and g < 50:
            blues += 1
    return reds, greens, blues


def check_window(env, args):
    here = Path(__file__).resolve().parent
    tmp_dir = here.parents[1] / 'build/wm-apps'
    tmp_dir.mkdir(parents=True, exist_ok=True)
    avi_path = tmp_dir / 'avi_live_sample.avi'
    hex_text = ''.join(
        ch for ch in (here / 'avi_sample.hex').read_text(encoding='utf-8')
        if ch in '0123456789abcdefABCDEF'
    )
    avi_path.write_bytes(bytes.fromhex(hex_text))
    try:
        with Guest(env, args, ['/build/wm-apps/avi_live_sample.avi'], size='520x420') as guest:
            origin = until(lambda: window_origin(guest.capture()), 'AVI Player did not open its window')
            ox, oy = origin
            # Click Play button at x in [134..176], y in [14..32].
            guest.click(ox + 155, oy + 23)

            def played():
                r, g, b = has_vivid_frame(guest.capture(), origin)
                return (r, g, b) if (r + g + b) >= 100 else None

            rgb = until(played, 'AVI Player did not render decoded RLE8 frames on Play')
            print(f'AVI Player opened sample and rendered RLE8 frames (R={rgb[0]}, G={rgb[1]}, B={rgb[2]})')
    finally:
        avi_path.unlink(missing_ok=True)


def main():
    args = arguments(__doc__, 'avi.zx')
    check_model(os.environ.copy())
    with private_display() as env:
        check_window(env, args)


if __name__ == '__main__':
    main()
