#!/usr/bin/env python3
"""Check the ZX Bounce against the bounces recorded from the Dis rules, in a private TaijiOS guest."""
import os
import time

from wm_app_test import Guest, arguments, ocr, private_display, run_model, stop, until

GREY, LIGHT, DARK = (221, 221, 221), (255, 255, 255), (173, 173, 173)
BAR = 24
CANVAS = 400


def check_model(env):
    message = run_model('bounce', 'bounce_bounces.expected', env)
    assert message == 'Bounce followed 10 recorded Dis bounces to the same hits and directions', message
    print('Bounce rules matched 10 recorded Dis bounces with the same hits and directions')


def canvas_origin(image):
    """The interior corner of the canvas, inside its 2-pixel ridge."""
    pixels = image.load()
    for y in range(BAR + 2, image.height - CANVAS):
        for x in range(2, image.width - CANVAS - 1):
            if pixels[x - 1, y - 1] == DARK and pixels[x - 2, y - 2] == LIGHT and pixels[x - 1, y] == DARK \
                    and pixels[x + 399, y - 1] == DARK and pixels[x + 400, y] == LIGHT \
                    and pixels[x + 400, y + 399] == LIGHT:
                return x, y
    return None


def label_text(guest, origin):
    ox, oy = origin
    return ocr(guest.capture(), (ox + 50, oy - BAR, ox + 250, oy - 2)).replace(' ', '').lower()


def vivid(image, origin):
    """Distinct saturated colour clusters in the canvas: the flying balls."""
    ox, oy = origin
    crop = image.crop((ox + 2, oy + 2, ox + CANVAS - 2, oy + CANVAS - 2))
    counts = {}
    for pixel in crop.getdata():
        if max(pixel) - min(pixel) > 60:
            key = (pixel[0] // 32, pixel[1] // 32, pixel[2] // 32)
            counts[key] = counts.get(key, 0) + 1
    return sum(1 for count in counts.values() if count >= 6)


def has_line(image, origin, x1, y1, x2, y2):
    """Black drawn along the segment, sampled inside the canvas."""
    ox, oy = origin
    pixels = image.load()
    for t in (0.2, 0.35, 0.5, 0.65, 0.8):
        x = int(ox + x1 + (x2 - x1) * t)
        y = int(oy + y1 + (y2 - y1) * t)
        if not any(pixels[x + dx, y + dy] == (0, 0, 0)
                   for dx in range(-2, 3) for dy in range(-2, 3)):
            return False
    return True


def drag(guest, origin, x1, y1, x2, y2, button):
    ox, oy = origin
    guest.run('xdotool', 'mousemove', '--window', guest.window, str(ox + x1), str(oy + y1), 'sleep', '.05',
              'mousedown', str(button), 'sleep', '.2',
              'mousemove', '--window', guest.window, str(ox + x2), str(oy + y2), 'sleep', '.2',
              'mouseup', str(button), 'sleep', '.2', check=False)


def check_window(env, args):
    guest = Guest(env, args, [])
    try:
        origin = until(lambda: canvas_origin(guest.capture()), 'Bounce did not open its canvas')
        ox, oy = origin
        until(lambda: label_text(guest, origin) == '8balls', 'the label did not read 8 balls')
        until(lambda: vivid(guest.capture(), origin) >= 4, 'the balls did not appear on the canvas')
        first = guest.capture().crop((ox + 2, oy + 2, ox + CANVAS - 2, oy + CANVAS - 2))
        time.sleep(0.4)
        second = guest.capture().crop((ox + 2, oy + 2, ox + CANVAS - 2, oy + CANVAS - 2))
        assert first.tobytes() != second.tobytes(), 'the balls did not move'

        drag(guest, origin, 50, 50, 350, 300, 1)
        until(lambda: has_line(guest.capture(), origin, 50, 50, 350, 300), 'a left drag drew no line')
        drag(guest, origin, 120, 330, 330, 120, 2)
        until(lambda: has_line(guest.capture(), origin, 120, 330, 330, 120), 'a middle drag drew no line')
        print('Bounce drew lines from both pointer buttons across its canvas')

        guest.click(ox + 10, oy - 14)
        until(lambda: label_text(guest, origin) == '7balls', 'the left button did not drop a ball')
        guest.click(ox + 34, oy - 14)
        until(lambda: label_text(guest, origin) == '8balls', 'the right button did not add a ball')
        print('Bounce counted its balls through the toolbar buttons')
    finally:
        stop(guest.app)


def main():
    args = arguments(__doc__, 'bounce.zx')
    check_model(os.environ.copy())
    with private_display() as env:
        check_window(env, args)


if __name__ == '__main__':
    main()
