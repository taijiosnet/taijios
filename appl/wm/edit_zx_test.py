#!/usr/bin/env python3
"""Check the ZX Edit text editor rules and live window in a private TaijiOS guest."""
import os
from pathlib import Path
import tempfile
import time

from wm_app_test import Guest, arguments, ocr, private_display, run_model, until

GREY = (221, 221, 221)
DARK = (150, 150, 150)
WIN_W, WIN_H = 560, 440
BAR_H = 24


def check_model(env):
    message = run_model('edit', 'edit_states.expected', env)
    assert message == 'Edit matched Limbo highlighting, search, replace-all and indent rules', message
    print('Edit model matched Limbo highlighting, search, replace-all and indent rules')


def window_origin(image):
    """Locate the top-left corner of Edit's 560x24 top menu bar."""
    pixels = image.load()
    for y in range(10, image.height - WIN_H + 1):
        for x in range(0, image.width - WIN_W + 1):
            if pixels[x, y] != GREY or pixels[x + WIN_W - 1, y] != GREY:
                continue
            if pixels[x, y + BAR_H - 1] != DARK or pixels[x + WIN_W - 1, y + BAR_H - 1] != DARK:
                continue
            return x, y
    return None


def has_blue_or_green(image, origin):
    ox, oy = origin
    crop = image.crop((ox + 4, oy + BAR_H + 4, ox + WIN_W - 4, oy + 140))
    blue = 0
    green = 0
    for r, g, b in crop.get_flattened_data():
        if b > 180 and r < 80 and g < 80:
            blue += 1
        elif g > 90 and r < 60 and b < 60:
            green += 1
    return blue, green


def check_window(env, args):
    # Create a temporary Limbo file inside build/wm-apps/ (visible inside guest root).
    tmp_dir = Path(__file__).resolve().parents[2] / 'build/wm-apps'
    tmp_dir.mkdir(parents=True, exist_ok=True)
    sample = tmp_dir / 'edit_live_sample.b'
    sample.write_text('implement Demo;\n# comment line\nreturn nil;\n', encoding='utf-8')
    guest_path = '/build/wm-apps/edit_live_sample.b'
    try:
        with Guest(env, args, [guest_path], size='640x560') as guest:
            origin = until(lambda: window_origin(guest.capture()), 'Edit did not open its window')
            ox, oy = origin

            def header_loaded():
                text = ocr(guest.capture(), (ox + 252, oy + 1, ox + WIN_W - 4, oy + BAR_H - 2)).lower()
                return text if 'edit_live_sample' in text else None

            until(header_loaded, 'Edit did not display the opened filename in the top bar')
            print('Edit opened and loaded the Limbo source file')

            # Toggle Options -> Limbo and verify blue keyword + green comment pixels appear.
            guest.click(ox + 205, oy + 12)
            time.sleep(0.15)
            guest.click(ox + 220, oy + BAR_H + 12)

            def highlighted():
                blue, green = has_blue_or_green(guest.capture(), origin)
                return (blue, green) if blue >= 10 and green >= 10 else None

            counts = until(highlighted, 'Options -> Limbo did not highlight keywords in blue and comments in green')
            print(f'Edit highlighted Limbo keywords and comments (blue={counts[0]}px, green={counts[1]}px)')

            # Click inside editor, type text, verify (dirty), then File -> Save and check disk.
            guest.click(ox + 20, oy + BAR_H + 80)
            time.sleep(0.15)
            guest.run('xdotool', 'type', '--window', guest.window, '--delay', '20', 'ADDED')
            time.sleep(0.2)
            until(
                lambda: 'dirty' in ocr(guest.capture(), (ox + 252, oy + 1, ox + WIN_W - 4, oy + BAR_H - 2)).lower() or None,
                'typing did not mark the buffer dirty',
            )
            # File -> Save
            guest.click(ox + 24, oy + 12)
            time.sleep(0.15)
            guest.click(ox + 40, oy + BAR_H + 56)

            def saved_to_disk():
                content = sample.read_text(encoding='utf-8')
                return content if 'ADDED' in content else None

            saved = until(saved_to_disk, 'File -> Save did not write edited content to disk')
            assert 'implement Demo;' in saved and 'ADDED' in saved, saved
            print('Edit edited the file, marked dirty, and saved changes back to disk')
    finally:
        sample.unlink(missing_ok=True)


def main():
    args = arguments(__doc__, 'edit.zx')
    check_model(os.environ.copy())
    with private_display() as env:
        check_window(env, args)


if __name__ == '__main__':
    main()
