#!/usr/bin/env python3
"""Check the ZX Mand fractal browser rules and live window in a private TaijiOS guest."""
import os
import time

from wm_app_test import Guest, arguments, private_display, run_model, until

DARK = (136, 136, 136)
LIGHT = (255, 255, 255)
GREY = (221, 221, 221)
CANVAS_W, CANVAS_H = 400, 400
BAR_H = 28
BORDER = 3
# Exact Dis 6x6x6 palette entries:
# index 254 (interior Mandelbrot/Julia) -> (51, 0, 102)
# index 2 (corner (0,0) Mandelbrot) -> (0, 0, 102)
INTERIOR = (51, 0, 102)
CORNER_MAND = (0, 0, 102)


def check_model(env):
    message = run_model('mand', 'mand_states.expected', env)
    assert message == 'Mand matched fixed-point Mandelbrot, Julia, palette and contour-crawl fill rules', message
    print('Mand model matched fixed-point Mandelbrot, Julia, palette and contour-crawl fill rules')


def canvas_origin(image):
    """Locate the top-left interior pixel of the 400x400 canvas inside its 3px sunken border."""
    pixels = image.load()
    for y in range(BAR_H + BORDER, image.height - CANVAS_H - BORDER + 1):
        for x in range(BORDER, image.width - CANVAS_W - BORDER + 1):
            if pixels[x - 1, y - 1] == DARK and pixels[x - 3, y - 3] == DARK \
                    and pixels[x + CANVAS_W, y + CANVAS_H] == LIGHT \
                    and pixels[x + CANVAS_W + 2, y + CANVAS_H + 2] == LIGHT \
                    and pixels[x, y - BORDER - 2] == GREY:
                return x, y
    return None


def drag(guest, origin, x1, y1, x2, y2):
    ox, oy = origin
    guest.run('xdotool', 'mousemove', '--window', guest.window, str(ox + x1), str(oy + y1), 'sleep', '.05',
              'mousedown', '1', 'sleep', '.15',
              'mousemove', '--window', guest.window, str(ox + x2), str(oy + y2), 'sleep', '.15',
              'mouseup', '1', 'sleep', '.15', check=False)


def check_window(env, args):
    with Guest(env, args, [], size='640x560') as guest:
        origin = until(lambda: canvas_origin(guest.capture()), 'Mand did not open its 400x400 canvas')
        ox, oy = origin

        def mandel_done():
            im = guest.capture()
            px = im.load()
            if px[ox + 0, oy + 0] == CORNER_MAND and px[ox + 250, oy + 200] == INTERIOR \
                    and px[ox + 350, oy + 350] != LIGHT:
                return im
            return None

        base_img = until(mandel_done, 'Mandelbrot set did not finish rendering with exact Dis colours')
        base_bytes = base_img.crop((ox, oy, ox + CANVAS_W, oy + CANVAS_H)).tobytes()
        print('Mand rendered initial Mandelbrot set with exact Dis 6x6x6 palette colours')

        # Button 2 (middle click) switches to Julia at clicked point.
        guest.click(ox + 167, oy + 187, button=2)

        def julia_rendered():
            im = guest.capture()
            px = im.load()
            # In Julia mode, top-left (0,0) has index 1 -> (0, 0, 51), different from Mandelbrot's (0, 0, 102).
            if px[ox + 0, oy + 0] == (0, 0, 51) and px[ox + 350, oy + 350] != LIGHT:
                return im
            return None

        until(julia_rendered, 'middle click did not switch from Mandelbrot to Julia')
        print('Mand switched to Julia set on middle click')

        # Button 3 (right click) pops back to Mandelbrot.
        guest.click(ox + 200, oy + 200, button=3)
        until(
            lambda: guest.capture().crop((ox, oy, ox + CANVAS_W, oy + CANVAS_H)).tobytes() == base_bytes or None,
            'right click did not restore the previous Mandelbrot view',
        )
        print('Mand zoomed back out to Mandelbrot on right click')

        # Button 1 drag zooms into a sub-rectangle, then right click restores.
        drag(guest, origin, 100, 100, 260, 260)

        def zoomed_rendered():
            im = guest.capture()
            px = im.load()
            crop = im.crop((ox, oy, ox + CANVAS_W, oy + CANVAS_H)).tobytes()
            return crop if crop != base_bytes and px[ox + 350, oy + 350] != LIGHT else None

        until(zoomed_rendered, 'left drag did not zoom into the selected rectangle')
        guest.click(ox + 200, oy + 200, button=3)
        until(
            lambda: guest.capture().crop((ox, oy, ox + CANVAS_W, oy + CANVAS_H)).tobytes() == base_bytes or None,
            'right click did not restore Mandelbrot after zoom',
        )
        print('Mand zoomed into dragged rectangle and restored on right click')


def main():
    args = arguments(__doc__, 'mand.zx')
    check_model(os.environ.copy())
    with private_display() as env:
        check_window(env, args)


if __name__ == '__main__':
    main()
