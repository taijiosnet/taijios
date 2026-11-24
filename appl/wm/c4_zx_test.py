#!/usr/bin/env python3
"""Check the ZX Connect against the game the Dis version printed, in a private TaijiOS guest."""
import os

from wm_app_test import Guest, arguments, private_display, run_model, stop, until

YELLOW = (255, 255, 0)
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
CELL_W, CELL_H = 57, 66
BOARD = 400


def check_model(env):
    message = run_model('c4', 'c4_games.expected', env)
    assert message == 'Connect replayed a recorded Dis game and took its winning and blocking moves', message
    print('Connect rules matched a recorded Dis game and took its winning and blocking moves')


def board_origin(image):
    pixels = image.load()
    for y in range(20, image.height - BOARD):
        for x in range(0, image.width - BOARD + 1):
            if pixels[x, y] != YELLOW or pixels[x + BOARD - 1, y] != YELLOW:
                continue
            if pixels[x, y + BOARD - 1] != YELLOW or pixels[x + 200, y + 200] != YELLOW:
                continue
            return x, y
    return None


def center(origin, column, row):
    ox, oy = origin
    return ox + column * CELL_W + CELL_W // 2, oy + (5 - row) * CELL_H + CELL_H // 2


def kind_at(image, origin, column, row):
    """The piece colour at a cell centre, or None over the empty yellow."""
    x, y = center(origin, column, row)
    pixels = image.load()
    patch = [pixels[x + dx, y + dy] for dx in (-1, 0, 1) for dy in (-1, 0, 1)]
    if all(pixel == BLACK for pixel in patch):
        return 'black'
    if all(pixel == WHITE for pixel in patch):
        return 'white'
    return None


def pieces(image, origin):
    seen = []
    for column in range(7):
        for row in range(6):
            piece = kind_at(image, origin, column, row)
            if piece:
                seen.append((piece, column, row))
    return seen


def check_window(env, args):
    guest = Guest(env, args, [], size='640x600')
    try:
        origin = until(lambda: board_origin(guest.capture()), 'Connect did not open its board')
        ox, oy = origin

        def machine_opened():
            seen = pieces(guest.capture(), origin)
            return seen if len(seen) == 1 and seen[0][0] == 'black' else None

        first = until(machine_opened, 'the machine black did not open the game')
        assert first[0][1] in range(7) and first[0][2] == 0, first
        print('Connect opened and the machine black played the first piece')

        # The human white drops a piece in column 2.
        guest.click(*center(origin, 2, 0))
        until(lambda: kind_at(guest.capture(), origin, 2, 0) == 'white', 'the clicked column dropped no white piece')

        def black_answered():
            seen = pieces(guest.capture(), origin)
            return seen if sum(1 for piece in seen if piece[0] == 'black') >= 2 else None

        until(black_answered, 'the machine black did not answer')
        print('Connect took the human click in its column and the machine answered')

        # The White menu turns white into a machine, and both sides play on.
        guest.click(ox + 368, oy - 65)
        until(lambda: guest.capture().load()[ox + 368, oy - 21] != YELLOW, 'the White menu did not open')
        guest.click(ox + 368, oy - 21)

        def both_playing():
            seen = pieces(guest.capture(), origin)
            return seen if len(seen) >= 6 else None

        until(both_playing, 'two machines did not keep playing')
        print('Connect played on with both sides as machines')
    finally:
        stop(guest.app)


def main():
    args = arguments(__doc__, 'c4.zx')
    check_model(os.environ.copy())
    with private_display() as env:
        check_window(env, args)


if __name__ == '__main__':
    main()
