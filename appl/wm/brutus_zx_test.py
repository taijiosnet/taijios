#!/usr/bin/env python3
"""Check the ZX Brutus SGML rich-text rules and live SGML load/format/save round-trip."""
import os
import time

from wm_app_test import BUILD, Guest, arguments, private_display, run_model, until

GREY = (221, 221, 221)
WIN_W, WIN_H = 720, 540


def check_model(env):
    message = run_model('brutus', 'brutus_states.expected', env)
    assert message == 'Brutus matched SGML round-trip, 33 tags, Hebrew remap, search and excerpt rules', message
    print('Brutus model matched SGML round-trip, 33 tags, Hebrew remap, search and excerpt rules')


def window_origin(image):
    pixels = image.load()
    for y in range(10, image.height - WIN_H + 1):
        for x in range(0, image.width - WIN_W + 1):
            if pixels[x, y] == GREY and pixels[x + WIN_W - 1, y] == GREY \
                    and pixels[x, y + WIN_H - 1] == GREY and pixels[x + WIN_W - 1, y + WIN_H - 1] == GREY:
                return x, y
    return None


def check_window(env, args):
    BUILD.mkdir(parents=True, exist_ok=True)
    doc = BUILD / 'brutus_sample.sgml'
    doc.write_text('<SGML>\n<Roman.10>Hello <Bold.12>Brutus</Bold.12></Roman.10>', encoding='utf-8')
    try:
        guest_path = '/build/wm-apps/brutus_sample.sgml'
        with Guest(env, args, [guest_path], size='800x620') as guest:
            ox, oy = until(lambda: window_origin(guest.capture()), 'Brutus did not open its window')

            # Focus main TextArea, jump to end, append " ZX", and click Put (x=197, y=14).
            guest.click(ox + 120, oy + 90)
            time.sleep(0.15)
            guest.run('xdotool', 'key', '--window', guest.window, 'End')
            time.sleep(0.1)
            guest.run('xdotool', 'type', '--window', guest.window, '--delay', '50', ' ZX')
            time.sleep(0.2)
            guest.click(ox + 197, oy + 14)

            saved = until(
                lambda: doc.read_text(encoding='utf-8')
                if 'ZX' in doc.read_text(encoding='utf-8') else None,
                'Brutus Put did not save updated SGML document',
            )
            assert saved.startswith('<SGML>\n'), saved
            assert '<Bold.12>' in saved and 'Brutus' in saved and 'ZX' in saved, saved
            print('Brutus loaded SGML, edited text, and saved SGML via Put')
    finally:
        doc.unlink(missing_ok=True)


def main():
    args = arguments(__doc__, 'brutus.zx')
    check_model(os.environ.copy())
    with private_display() as env:
        check_window(env, args)


if __name__ == '__main__':
    main()
