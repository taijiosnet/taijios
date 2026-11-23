#!/usr/bin/env python3
"""Check the ZX Mine Sweeper against the squares the Dis version showed, in a private guest."""
import os
import time

from wm_app_test import BUILD, HERE, Guest, arguments, ocr, private_display, run_model, until

LIGHT, DARK = (255, 255, 255), (173, 173, 173)
FACES = {(221, 221, 221): '.', (238, 238, 238): '.', (128, 128, 0): 'o', (255, 0, 0): 'r', (255, 170, 0): 'y'}


def recorded():
    seed, steps = None, []
    for line in (HERE / 'sweeper_games.expected').read_text(encoding='utf-8').splitlines():
        if not line or line.startswith('#'):
            continue
        words = line.split(' ')
        if words[0] == 'seed':
            seed = words[1]
        else:
            steps.append((words[0], int(words[1]), int(words[2]), words[3], words[4]))
    return seed, steps


def grid_origin(image):
    """The top-left corner of the first square: each square has a 1-pixel bevel."""
    px = image.load()
    for y in range(image.height - 180):
        for x in range(image.width - 160):
            if px[x, y + 5] == LIGHT and px[x + 15, y + 5] == DARK and px[x + 16, y + 5] == LIGHT \
                    and px[x + 5, y] == LIGHT and px[x + 5, y + 17] == DARK and px[x + 5, y + 18] == LIGHT \
                    and px[x + 159, y + 175] == DARK and px[x + 144, y + 162] == LIGHT:
                return x, y
    return None


def faces(image, origin):
    gx, gy = origin
    return ''.join(FACES.get(image.getpixel((gx + 16 * c + 2, gy + 18 * r + 3)), '?')
                   for r in range(10) for c in range(10))


def main():
    args = arguments(__doc__, 'sweeper.zx')
    seed, steps = recorded()
    message = run_model('sweeper', 'sweeper_games.expected', os.environ.copy())
    assert message == f'Mine Sweeper matched {len(steps)} actions recorded from the Dis version', message
    print(message)
    with private_display() as env, Guest(env, args, [seed]) as guest:
        image = until(lambda: (lambda shot: shot if grid_origin(shot) else None)(guest.capture()),
                      'Mine Sweeper did not open')
        gx, gy = grid_origin(image)
        ox, oy = gx, gy - 32
        assert faces(image, (gx, gy)) == '.' * 100

        def square(row, column):
            return gx + 16 * (column - 1) + 8, gy + 18 * (row - 1) + 9

        for number, (action, row, column, expected, label) in enumerate(steps, 1):
            if action == 'click':
                guest.click(*square(row, column))
            elif action == 'mark':
                guest.click(*square(row, column), 3)
            else:
                guest.run('xdotool', 'mousemove', '--window', guest.window, str(ox + 30), str(oy + 8),
                          'sleep', '0.1', 'mousedown', '1', 'sleep', '0.3')
                # Options highlights and its menu opens below it, as in the Dis version.
                until(lambda: (lambda menu: menu.getpixel((ox + 3, oy + 3)) == (237, 237, 237)
                               and menu.getpixel((ox + 5, oy + 18)) == LIGHT
                               and menu.getpixel((ox + 5, oy + 35)) == DARK)(guest.capture()),
                      'the Options menu did not open below the button', timeout=5)
                guest.run('xdotool', 'mousemove', '--window', guest.window, str(ox + 30), str(oy + 27),
                          'sleep', '0.2', 'mouseup', '1')
            guest.move(ox + 200, oy + 8)
            try:
                shot = until(lambda: (lambda shot: shot if faces(shot, (gx, gy)) == expected else None)(
                    guest.capture()), f'step {number} ({action} {row} {column}) differs', timeout=5)
            except AssertionError:
                guest.capture().save(BUILD / 'sweeper-failure.png')
                raise
            if label in ('lost', 'won'):
                text = ocr(shot, (ox + 70, oy, ox + 230, oy + 18))
                assert ('Lost' if label == 'lost' else 'Won') in text, (number, text)
        time.sleep(0.2)
    print(f'Mine Sweeper showed the same squares as the Dis version for {len(steps)} clicks, marks and a restart, '
          'losing on a marked mine and winning the next board')


if __name__ == '__main__':
    main()
