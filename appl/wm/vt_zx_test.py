#!/usr/bin/env python3
"""Check the ZX VT100 model rules and live interactive /zx/sh.zx terminal window."""
import os
import time

from wm_app_test import Guest, arguments, ocr, private_display, run_model, until

GREY = (221, 221, 221)
WIN_W, WIN_H = 648, 420


def check_model(env):
    message = run_model('vt', 'vt_states.expected', env)
    assert message == 'VT matched VT100 CSI/SGR, cursor, DSR/DA, scrolling and resize rules', message
    print('VT model matched VT100 CSI/SGR, cursor, DSR/DA, scrolling and resize rules')


def window_origin(image):
    pixels = image.load()
    for y in range(10, image.height - WIN_H + 1):
        for x in range(0, image.width - WIN_W + 1):
            if pixels[x, y] == GREY and pixels[x + WIN_W - 1, y] == GREY \
                    and pixels[x, y + WIN_H - 1] == GREY and pixels[x + WIN_W - 1, y + WIN_H - 1] == GREY:
                return x, y
    return None


def screen_bg_pixel(image, ox, oy):
    # Sample inside the VT100 screen canvas (below the 28px toolbar).
    return image.getpixel((ox + 500, oy + 200))


def check_window(env, args):
    with Guest(env, args, [], size='720x520') as guest:
        ox, oy = until(lambda: window_origin(guest.capture()), 'VT did not open its window')
        # Initially black background (0, 0, 0).
        bg0 = until(
            lambda: screen_bg_pixel(guest.capture(), ox, oy)
            if screen_bg_pixel(guest.capture(), ox, oy) == (0, 0, 0) else None,
            'VT canvas did not render with black background',
        )
        assert bg0 == (0, 0, 0), bg0

        # Click Reverse button (x=220, y=14) -> background becomes light grey (192, 192, 192).
        guest.click(ox + 220, oy + 14)
        bg1 = until(
            lambda: screen_bg_pixel(guest.capture(), ox, oy)
            if screen_bg_pixel(guest.capture(), ox, oy) == (192, 192, 192) else None,
            'VT Reverse toggle did not invert screen background',
        )
        assert bg1 == (192, 192, 192), bg1
        print('VT rendered 80x24 framebuffer and toggled Reverse video')

        # Type a shell command into /zx/sh.zx and verify its output on row 1 (y = oy + 32 + 16).
        guest.click(ox + 200, oy + 200)
        time.sleep(0.15)
        guest.run('xdotool', 'type', '--window', guest.window, '--delay', '120', 'echo HELLO_ZX_VT')
        time.sleep(0.2)
        guest.run('xdotool', 'key', '--window', guest.window, 'Return')

        # Row 0 (oy+32..oy+48) has echoed command; Row 1 (oy+48..oy+64) has shell output HELLO_ZX_VT.
        found = until(
            lambda: 'HELLO' in ocr(guest.capture(), (ox + 2, oy + 46, ox + 220, oy + 66)).upper() or None,
            'VT did not render shell command output on row 1',
        )
        assert found
        print('VT ran interactive /zx/sh.zx command and rendered output')


def main():
    args = arguments(__doc__, 'vt.zx')
    check_model(os.environ.copy())
    with private_display() as env:
        check_window(env, args)


if __name__ == '__main__':
    main()
