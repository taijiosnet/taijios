#!/usr/bin/env python3
"""Check the ZX Unibrowse rules and live window in a private TaijiOS guest."""
import os
import time

from wm_app_test import Guest, arguments, ocr, private_display, run_model, until

GREY = (221, 221, 221)
PANEL = (232, 232, 232)
WIN_W, WIN_H = 620, 340


def check_model(env):
    message = run_model('unibrowse', 'unibrowse_states.expected', env)
    assert message == 'Unibrowse matched unidata lookup, blocks, font ranges, wordsearch and UTF-8 rules', message
    print('Unibrowse model matched unidata lookup, blocks, font ranges, wordsearch and UTF-8 rules')


def window_origin(image):
    pixels = image.load()
    for y in range(10, image.height - WIN_H + 1):
        for x in range(0, image.width - WIN_W + 1):
            if pixels[x, y] != GREY or pixels[x + WIN_W - 1, y] != GREY:
                continue
            if pixels[x + 6, y + 6] == PANEL and pixels[x + 6, y + 216] == PANEL:
                return x, y
    return None


def check_window(env, args):
    with Guest(env, args, [], size='640x480') as guest:
        origin = until(lambda: window_origin(guest.capture()), 'Unibrowse did not open its window')
        ox, oy = origin

        # Verify Inspector shows initial 'A' (0041 -> LATIN CAPITAL LETTER A).
        def initial_inspector():
            txt = ocr(guest.capture(), (ox + 8, oy + 252, ox + 360, oy + 274)).upper()
            return txt if 'LATIN' in txt and 'CAPITAL' in txt else None

        until(initial_inspector, 'Inspector did not show initial LATIN CAPITAL LETTER A from unidata2.txt')
        print('Unibrowse loaded /lib/unidata/unidata2.txt and displayed initial character A')

        # Switch to "By number", enter 03B1 (Greek small letter alpha), press Return.
        guest.click(ox + 80, oy + 48)
        time.sleep(0.15)
        guest.click(ox + 340, oy + 27)
        time.sleep(0.15)
        guest.run('xdotool', 'type', '--window', guest.window, '--delay', '20', '03B1')
        guest.key('Return')

        def alpha_shown():
            txt = ocr(guest.capture(), (ox + 8, oy + 252, ox + 400, oy + 274)).upper()
            return txt if 'GREEK' in txt and 'ALPHA' in txt else None

        until(alpha_shown, 'By number 03B1 did not look up GREEK SMALL LETTER ALPHA')
        print('Unibrowse looked up 03B1 -> GREEK SMALL LETTER ALPHA and opened its 3x8 glyph table')

        # Click "Next" in the 3x8 table and verify row hex advances (03B0 -> 03C8).
        guest.click(ox + 256, oy + 173)
        until(
            lambda: '03C8' in ocr(guest.capture(), (ox + 170, oy + 14, ox + 224, oy + 52)).upper() or None,
            'Next button did not page the 3x8 glyph table forward',
        )
        print('Unibrowse paged the 3x8 glyph table forward with Next')

        # Click "Font information" and verify unicode.9.font ranges load.
        guest.click(ox + 80, oy + 104)
        until(
            lambda: 'LATIN1' in ocr(guest.capture(), (ox + 172, oy + 30, ox + 460, oy + 52)).upper() or None,
            'Font information did not list subfont ranges from unicode.9.font',
        )
        print('Unibrowse displayed font subranges from /fonts/lucm/unicode.9.font')


def main():
    args = arguments(__doc__, 'unibrowse.zx')
    check_model(os.environ.copy())
    with private_display() as env:
        check_window(env, args)


if __name__ == '__main__':
    main()
