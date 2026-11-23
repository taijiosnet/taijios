#!/usr/bin/env python3
"""Check the ZX Tetris against the game recorded from the Dis version, in a private guest."""
import os
import shutil
import time

from wm_app_test import BUILD, HERE, ROOT, Guest, arguments, ocr, private_display, run_model, until

GREY, LIGHT, DARK = (221, 221, 221), (255, 255, 255), (173, 173, 173)
COLOURS = {(255, 0, 0): '1', (255, 170, 0): '2', (255, 255, 0): '3', (0, 128, 0): '4', (0, 0, 204): '5',
           (147, 221, 241): '6', (255, 170, 255): '7', GREY: '0', LIGHT: '0'}
W, H, SIZE = 10, 22, 17


def recorded():
    seed, pieces = None, []
    for line in (HERE / 'tetris_games.expected').read_text(encoding='utf-8').splitlines():
        if not line or line.startswith('#'):
            continue
        words = line.split(' ')
        if words[0] == 'random':
            seed = bytes.fromhex(words[1])
        else:
            pieces.append((words[1], words[2], words[3:6]))
    return seed, pieces


def board_origin(image):
    """The top-left corner of the board's sunken border."""
    px = image.load()
    for y in range(image.height - 379):
        for x in range(image.width - 175):
            if px[x, y] == DARK and px[x + 1, y + 1] == DARK and px[x + 2, y + 2] in (GREY, LIGHT) \
                    and px[x + 174, y + 378] == LIGHT and px[x + 173, y + 377] == LIGHT \
                    and px[x + 100, y] == DARK and px[x + 100, y + 378] == LIGHT:
                return x, y
    return None


def board(image, origin):
    ox, oy = origin
    return ''.join(COLOURS.get(image.getpixel((ox + 2 + SIZE * c + 8, oy + 2 + SIZE * r + 8)), '?')
                   for r in range(H) for c in range(W))


def same(seen, expected, first):
    return all(e == '?' or s == '?' or s == e for s, e in zip(seen[first:], expected[first:]))


def counters(image, origin):
    ox, oy = origin
    return [ocr(image, (ox + 223, oy + 67 + 18 * i, ox + 260, oy + 81 + 18 * i), digits=True) for i in range(3)]


def main():
    args = arguments(__doc__, 'tetris.zx')
    seed, pieces = recorded()
    message = run_model('tetris', 'tetris_games.expected', os.environ.copy())
    assert message == f'Tetris matched {len(pieces)} pieces recorded from the Dis version, to its game over', message
    print(message)

    guest_dir = BUILD / 'tetris-guest'
    shutil.rmtree(guest_dir, ignore_errors=True)
    (guest_dir / 'scores').mkdir(parents=True)
    (guest_dir / 'random').write_bytes(seed)
    # Two recorded scores, so the new one ranks third.
    best = (ROOT / 'lib/scores/tetris').read_text(encoding='utf-8').splitlines()[:2]
    (guest_dir / 'scores/tetris').write_text(''.join(line + '\n' for line in best), encoding='utf-8')
    mount = '/' + guest_dir.relative_to(ROOT).as_posix()
    setup = f'bind {mount}/random /dev/random; bind -c {mount}/scores /lib/scores; '
    try:
        with private_display() as env, Guest(env, args, setup=setup, size='800x600') as guest:
            image = until(lambda: (lambda shot: shot if board_origin(shot) else None)(guest.capture()),
                          'Tetris did not open')
            origin = board_origin(image)
            ox, oy = origin
            time.sleep(1.2)
            guest.key('p')
            start = guest.capture()
            if counters(start, origin) != ['0', '0', '0']:
                start.save(BUILD / 'tetris-failure.png')
                raise AssertionError(('start counters', counters(start, origin)))
            for number, (keys, expected, values) in enumerate(pieces, 1):
                names = {'x': 'x', 'c': 'c', 'z': 'z'}
                guest.run('xdotool', 'key', '--window', guest.window, '--delay', '30', 'a',
                          *[names[k] for k in keys if k in names], 'space')
                last = number == len(pieces)
                # While the game runs the next piece may already show in the top four rows.
                first = 0 if last else 4 * W
                try:
                    shot = until(lambda: (lambda shot: shot if same(board(shot, origin), expected, first) else None)(
                        guest.capture()), f'piece {number} differs', timeout=6)
                except AssertionError:
                    guest.capture().save(BUILD / 'tetris-failure.png')
                    raise AssertionError((number, keys, board(guest.capture(), origin), expected))
                if not last:
                    # A dropped piece looks landed before its landing tick: let one tick pass first.
                    time.sleep(0.4)
                    guest.key('p')
            assert counters(shot, origin) == pieces[-1][2], counters(shot, origin)
            shot = until(lambda: (lambda shot: shot if 'Game over' in ocr(shot, (ox + 50, oy + 120, ox + 132, oy + 140))
                                  else None)(guest.capture()), 'no Game over label', timeout=5)
            print(f'Tetris drew the same boards as the Dis version for {len(pieces)} pieces and ended the game '
                  f'at score {pieces[-1][2][0]}, level {pieces[-1][2][1]}, {pieces[-1][2][2]} rows')

            guest.key('a')
            scores = until(lambda: (lambda shot: shot if 'High' in ocr(shot, (ox + 14, oy, ox + 250, oy + 18))
                                    else None)(guest.capture()), 'the high scores did not open')
            table = (guest_dir / 'scores/tetris').read_text(encoding='utf-8').splitlines()
            assert [line.split(' ')[1:3] for line in table] == [best[0].split(' ')[1:3], best[1].split(' ')[1:3],
                                                                ['444', '22']], table
            # The new third score is on a white row.
            assert scores.getpixel((ox + 20, oy + 36 + 2 * 18 + 8)) == LIGHT, 'the new score is not highlighted'
            assert scores.getpixel((ox + 20, oy + 36 + 1 * 18 + 8)) == GREY
            print('Tetris recorded the score with its rows and level and showed it third in the high scores')

            guest.click(ox + 132, oy + 36 + 3 * 18 + 9)
            fresh = until(lambda: (lambda shot: shot if board_origin(shot) else None)(guest.capture()),
                          'New game did not start a game')
            # The generator carries on: the next game starts with a red bar and an orange square next.
            assert fresh.getpixel((ox + 175 + 12 + 17 + 8, oy + 17 + 8)) == (255, 170, 0), 'wrong next piece'

            def columns():
                cells = board(guest.capture(), origin)
                return sorted({i % W for i, c in enumerate(cells) if c == '1'})

            first = until(columns, 'the first piece did not appear')
            guest.click(ox + 20, oy + 40)
            until(lambda: columns() and min(columns()) == min(first) - 1, 'a click on the left third did not move left')
            guest.click(ox + 150, oy + 40)
            guest.click(ox + 150, oy + 40)
            until(lambda: columns() and min(columns()) == min(first) + 1, 'clicks on the right third did not move right')
            guest.click(ox + 80, oy + 300)
            until(lambda: '1' in board(guest.capture(), origin)[18 * W:], 'a click below the line did not drop')
            print('Tetris moved and dropped the piece with clicks on the board')
            guest.key('p')
            guest.key('q')
            until(lambda: board_origin(guest.capture()) is None, 'q did not close Tetris')
            print('Tetris paused on p and closed on q')
    finally:
        shutil.rmtree(guest_dir, ignore_errors=True)


if __name__ == '__main__':
    main()
