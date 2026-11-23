#!/usr/bin/env python3
"""Check the ZX Snake against the boards the Dis Snake drew, in a private TaijiOS guest."""
import os
import shutil
import time

from wm_app_test import BUILD, ROOT, Guest, arguments, ocr, private_display, run_model, stop, until

HERE = ROOT / 'appl/wm'
GREY, LIGHT, DARK = (221, 221, 221), (255, 255, 255), (173, 173, 173)
CELL = 9


def recorded():
    games = []
    for line in (HERE / 'snake_games.expected').read_text(encoding='utf-8').splitlines():
        if line and not line.startswith('#'):
            score, replay, board = line.split(' ')
            games.append((int(score), replay, board))
    return games


def check_model(env):
    replays = sum(1 for _, replay, _ in recorded() if replay != '12.0p')
    message = run_model('snake', 'snake_games.expected', env)
    assert message == f'Snake replayed {replays + 1} recorded Dis games to the same boards and scores', message
    print(f'Snake rules matched {replays} recorded Dis games and the paused first game')


def kind(color):
    if color == GREY:
        return '0'
    if color[2] > 150 and color[0] < 60 and color[1] < 60:
        return '1'
    if color[0] > 200 and color[1] > 200 and color[2] < 100:
        return '3'
    if color[0] > 200 and color[1] < 100 and color[2] < 100:
        return '2'
    return '?'


def canvas_origin(image):
    """The interior corner inside the canvas's 2-pixel ridge."""
    pixels = image.load()
    for y in range(2, image.height - 270):
        for x in range(2, image.width - 271):
            if pixels[x - 1, y - 1] == DARK and pixels[x - 2, y - 2] == LIGHT and pixels[x - 1, y] == DARK \
                    and pixels[x, y] not in (LIGHT, DARK) and pixels[x + 269, y - 1] == DARK \
                    and pixels[x + 270, y] == LIGHT and pixels[x + 270, y + 269] == LIGHT:
                return x, y
    return None


def has_canvas(image):
    return canvas_origin(image) is not None


def board(image, origin):
    px = image.load()
    ox, oy = origin
    cells = [[kind(px[ox + CELL * x + 4, oy + CELL * y + 4]) for x in range(30)] for y in range(30)]
    # Each neighbour of the crash is read at its far corner, outside the crash oval's outline.
    for cx, cy in [(x, y) for y in range(30) for x in range(30) if cells[y][x] == '3']:
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dx or dy:
                    x, y = (cx + dx) % 30, (cy + dy) % 30
                    cells[y][x] = kind(px[ox + CELL * x + (8 if dx > 0 else 0 if dx < 0 else 4),
                                          oy + CELL * y + (8 if dy > 0 else 0 if dy < 0 else 4)])
    return '30.30.' + ''.join(cells[y][x] for y in range(30) for x in range(30))


def label(image, box):
    return ocr(image, box)


def check_replays(env, args):
    for score, replay, expected in recorded():
        guest = Guest(env, args, [replay])
        try:
            image = guest.settled(has_canvas, f'Snake replay {replay[:12]} did not finish', name='snake-failure')
            origin = canvas_origin(image)
            seen = board(image, origin)
            assert seen == expected, (replay[:12], [i for i, (a, b) in enumerate(zip(seen, expected)) if a != b][:8])
            ox, oy = origin
            score_text = label(image, (ox + 132, oy - 16, ox + 271, oy - 2)).replace(' ', '')
            assert score_text == f'Score:{score}', score_text
            if replay == '12.0p':
                high = label(image, (ox - 1, oy - 16, ox + 130, oy - 2)).replace(' ', '')
                assert high == 'High:194', high
        finally:
            stop(guest.app)
    print(f'Snake drew the same boards and scores as the Dis Snake for {len(recorded())} recorded replays')


def check_keys(env, args):
    guest = Guest(env, args, [])
    try:
        image = until(lambda: guest.capture() if canvas_origin(guest.capture()) else None, 'Snake did not open')
        origin = canvas_origin(image)
        ox, oy = origin
        guest.run('xdotool', 'mousemove', '--window', guest.window, str(ox + 135), str(oy + 50), 'click', '1')
        guest.key('Up')
        time.sleep(0.6)
        guest.key('p')
        paused = guest.settled(has_canvas, 'Snake did not pause on p', timeout=10, name='snake-failure')
        cells = board(paused, origin)[6:]
        rows = {index // 30 for index, cell in enumerate(cells) if cell == '1'}
        assert len(rows) > 1, 'the snake did not turn up'
        guest.key('q')
        until(lambda: canvas_origin(guest.capture()) is None, 'q did not close Snake')
    finally:
        stop(guest.app)
    print('Snake turned with the arrow keys, paused on p and closed on q')


def check_crash_record(env, args):
    """Crash on purpose with the score table bound to a scratch folder, then start again."""
    scores = BUILD / 'snake-scores'
    shutil.rmtree(scores, ignore_errors=True)
    scores.mkdir(parents=True)
    guest = Guest(env, args, [], setup=f'bind -c /{scores.relative_to(ROOT).as_posix()} /lib/scores; ')
    try:
        image = until(lambda: guest.capture() if canvas_origin(guest.capture()) else None, 'Snake did not open')
        origin = canvas_origin(image)
        ox, oy = origin
        guest.run('xdotool', 'mousemove', '--window', guest.window, str(ox + 135), str(oy + 50), 'click', '1')
        # One key is taken per tick: up, left and down run the head into its own body.
        guest.run('xdotool', 'key', '--window', guest.window, 'Up', 'Left', 'Down')
        crashed = guest.settled(has_canvas, 'Snake did not crash', name='snake-failure')
        seen = board(crashed, origin)
        if seen[6:].count('3') != 1:
            crashed.save(BUILD / 'snake-failure.png')
            raise AssertionError('no crash was drawn')
        record = until(lambda: (scores / 'snake').read_text(encoding='utf-8') if (scores / 'snake').exists()
                       and (scores / 'snake').stat().st_size else None, 'the crash was not recorded')
        user, score, replay, recorded_board = record.rstrip('\n').split(' ')
        assert record.count('\n') == 1 and user and replay.split('.')[0].isdigit(), record
        # The recorded board also marks food under the body as body, as the canvas shows it.
        assert recorded_board == seen, 'the score table board differs from the window'
        assert label(crashed, (ox + 132, oy - 16, ox + 271, oy - 2)).replace(' ', '') == f'Score:{score}'
        time.sleep(1)
        guest.key('space')
        fresh = until(lambda: (lambda image: image if board(image, origin)[6:].count('3') == 0 else None)(
            guest.capture()), 'a key after the crash did not start a new game')
        assert label(fresh, (ox - 1, oy - 16, ox + 130, oy - 2)).replace(' ', '') == f'High:{score}'
        guest.key('q')
        until(lambda: canvas_origin(guest.capture()) is None, 'q did not close Snake')
    finally:
        stop(guest.app)
        shutil.rmtree(scores, ignore_errors=True)
    print('Snake recorded a crash with its replay and board in the score table and started a new game')


def main():
    args = arguments(__doc__, 'snake.zx')
    check_model(os.environ.copy())
    with private_display() as env:
        check_replays(env, args)
        check_keys(env, args)
        check_crash_record(env, args)


if __name__ == '__main__':
    main()
