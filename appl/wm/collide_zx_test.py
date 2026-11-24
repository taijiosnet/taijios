#!/usr/bin/env python3
"""Check the ZX Collide rules and live 3D scene in a private TaijiOS guest."""
import os
import time

from wm_app_test import Guest, arguments, private_display, run_model, stop, until

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GREY = (221, 221, 221)
PANEL_W, PANEL_H = 512, 512
BAR_H = 48


def check_model(env):
    message = run_model('collide', 'collide_states.expected', env)
    assert message == 'Collide reflected at cube, sphere and ellipsoid shells and transferred momentum on impact', message
    print('Collide rules matched cube, sphere and ellipsoid reflections, momentum transfer and retiming')


def panel_origin(image):
    """Locate the top-left corner of the 512x512 black panel beneath the grey toolbar."""
    pixels = image.load()
    for y in range(BAR_H, image.height - PANEL_H + 1):
        for x in range(0, image.width - PANEL_W + 1):
            if pixels[x, y] != BLACK or pixels[x + PANEL_W - 1, y] != BLACK:
                continue
            if pixels[x, y + PANEL_H - 1] != BLACK or pixels[x + PANEL_W - 1, y + PANEL_H - 1] != BLACK:
                continue
            if pixels[x + 120, y - 10] == GREY:
                return x, y
    return None


def white_span(image, origin):
    """Horizontal span of white wireframe pixels inside the black panel."""
    ox, oy = origin
    crop = image.crop((ox, oy, ox + PANEL_W, oy + PANEL_H))
    pixels = crop.load()
    xs = []
    for y in range(0, PANEL_H, 2):
        for x in range(0, PANEL_W, 2):
            r, g, b = pixels[x, y]
            if r > 230 and g > 230 and b > 230:
                xs.append(x)
    return (max(xs) - min(xs)) if len(xs) >= 20 else 0


def bright_ball_pixels(image, origin):
    """Count colourful pixels (flying spheres) inside the black panel."""
    ox, oy = origin
    crop = image.crop((ox, oy, ox + PANEL_W, oy + PANEL_H))
    count = 0
    for r, g, b in crop.get_flattened_data():
        if max(r, g, b) - min(r, g, b) > 30 and r + g + b >= 300:
            count += 1
    return count


def check_window(env, args):
    with Guest(env, args, ['-b', '12'], size='640x640') as guest:
        origin = until(lambda: panel_origin(guest.capture()), 'Collide did not open its 512x512 panel')
        ox, oy = origin

        span0 = until(lambda: white_span(guest.capture(), origin) or None, 'cube wireframe did not appear')
        assert span0 >= 200, f'unexpected wireframe span: {span0}'
        balls0 = until(lambda: bright_ball_pixels(guest.capture(), origin) or None, 'flying balls did not appear')
        assert balls0 >= 80, f'too few coloured ball pixels: {balls0}'

        first = guest.capture().crop((ox, oy, ox + PANEL_W, oy + PANEL_H))
        time.sleep(0.5)
        second = guest.capture().crop((ox, oy, ox + PANEL_W, oy + PANEL_H))
        assert first.tobytes() != second.tobytes(), 'objects did not animate'
        print(f'Collide opened with cube wireframe (span={span0}px) and animated objects ({balls0} coloured px)')

        # Click zoomin (top-left button), let the cube grow, then stop (top-center button).
        guest.click(ox + 44, oy - BAR_H + 12)

        def zoomed_span():
            span = white_span(guest.capture(), origin)
            return span if span > span0 + 25 else None

        span_zoomed = until(zoomed_span, 'zoomin button did not enlarge the surround')
        guest.click(ox + 256, oy - BAR_H + 12)
        time.sleep(0.25)
        span_stopped = white_span(guest.capture(), origin)
        time.sleep(0.4)
        assert abs(white_span(guest.capture(), origin) - span_stopped) <= 4, 'stop button did not halt zoom'
        print(f'Collide zoomed in ({span0}px -> {span_zoomed}px) and stopped cleanly')

        # Click objects button (bottom-center) twice to add more coloured objects.
        before_objs = bright_ball_pixels(guest.capture(), origin)
        guest.click(ox + 256, oy - BAR_H + 36)
        guest.click(ox + 256, oy - BAR_H + 36)

        def more_objects():
            count = bright_ball_pixels(guest.capture(), origin)
            return count if count > before_objs + 30 else None

        after_objs = until(more_objects, 'objects button did not add new objects')
        print(f'Collide added more objects ({before_objs} -> {after_objs} coloured px)')


def main():
    args = arguments(__doc__, 'collide.zx')
    check_model(os.environ.copy())
    with private_display() as env:
        check_window(env, args)


if __name__ == '__main__':
    main()
