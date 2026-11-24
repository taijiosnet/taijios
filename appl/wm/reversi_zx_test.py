#!/usr/bin/env python3
"""Check the ZX Reversi against the game the Dis version printed, in a private TaijiOS guest."""
import os
import time

from wm_app_test import Guest, arguments, private_display, run_model, until

GREEN = (0, 255, 0)
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
CELL = 50
BOARD = 400


def check_model(env):
    message = run_model('reversi', 'reversi_games.expected', env)
    assert message == 'Reversi replayed a complete Dis game to 63-1 and matched Dis minimax evaluations', message
    print('Reversi rules replayed a complete Dis game to 63-1 and matched Dis minimax evaluations')


def board_origin(image):
    pixels = image.load()
    for y in range(20, image.height - BOARD):
        for x in range(0, image.width - BOARD + 1):
            if pixels[x, y] != GREEN or pixels[x + BOARD - 1, y] != GREEN:
                continue
            if pixels[x, y + BOARD - 1] != GREEN or pixels[x + 10, y + 10] != GREEN:
                continue
            return x, y
    return None


def center(origin, m, n):
    ox, oy = origin
    return ox + (m - 1) * CELL + CELL // 2, oy + (n - 1) * CELL + CELL // 2


def kind_at(image, origin, m, n):
    x, y = center(origin, m, n)
    pixels = image.load()
    patch = [pixels[x + dx, y + dy] for dx in (-1, 0, 1) for dy in (-1, 0, 1)]
    if all(p == BLACK for p in patch):
        return 'black'
    if all(p == WHITE for p in patch):
        return 'white'
    return None


def pieces(image, origin):
    seen = []
    for m in range(1, 9):
        for n in range(1, 9):
            piece = kind_at(image, origin, m, n)
            if piece:
                seen.append((piece, m, n))
    return seen


def legal_white_target(seen):
    """Pick any legal white move on the current board (after Black's opening move)."""
    grid = {(m, n): color for color, m, n in seen}
    for m in range(1, 9):
        for n in range(1, 9):
            if (m, n) in grid:
                continue
            for dm in (-1, 0, 1):
                for dn in (-1, 0, 1):
                    if dm == 0 and dn == 0:
                        continue
                    cm, cn = m + dm, n + dn
                    flips = 0
                    while grid.get((cm, cn)) == 'black':
                        cm += dm
                        cn += dn
                        flips += 1
                    if flips > 0 and grid.get((cm, cn)) == 'white':
                        return m, n
    return None


def check_window(env, args):
    with Guest(env, args, [], size='640x600') as guest:
        origin = until(lambda: board_origin(guest.capture()), 'Reversi did not open its 8x8 green board')
        ox, oy = origin

        def black_opened():
            seen = pieces(guest.capture(), origin)
            return seen if len(seen) == 5 else None

        opened = until(black_opened, 'machine black did not play the opening move')
        assert sum(1 for c, _, _ in opened if c == 'black') == 4, opened
        assert sum(1 for c, _, _ in opened if c == 'white') == 1, opened
        print('Reversi opened and machine black played its level-6 opening move')

        # Human white plays a legal move and machine black answers.
        target = legal_white_target(opened)
        assert target is not None, opened
        guest.click(*center(origin, *target))
        until(lambda: kind_at(guest.capture(), origin, *target) == 'white', 'clicked square did not place white disc')

        def black_answered():
            seen = pieces(guest.capture(), origin)
            return seen if len(seen) >= 7 else None

        until(black_answered, 'machine black did not answer white')
        print('Reversi accepted human white click, flipped discs and machine black answered')

        # Click "last move" button in center of top bar to verify replay completes cleanly.
        guest.click(ox + 200, oy - 65)
        time.sleep(0.5)
        until(lambda: len(pieces(guest.capture(), origin)) >= 7, 'last move replay did not restore board')
        print('Reversi replayed the last move cleanly')

        # Open White menu and switch White to Machine so both sides play on.
        guest.click(ox + 368, oy - 65)
        until(lambda: guest.capture().load()[ox + 368, oy - 21] != GREEN, 'White menu did not open')
        guest.click(ox + 368, oy - 21)
        until(lambda: len(pieces(guest.capture(), origin)) >= 9, 'two machines did not keep playing')
        print('Reversi continued automatically with both sides as machines')


def main():
    args = arguments(__doc__, 'reversi.zx')
    check_model(os.environ.copy())
    with private_display() as env:
        check_window(env, args)


if __name__ == '__main__':
    main()
