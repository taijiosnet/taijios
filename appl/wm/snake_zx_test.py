#!/usr/bin/env python3
"""Check the ZX Snake against the boards the Dis Snake drew, in a private TaijiOS guest."""
import argparse
import io
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'cmd/tcltk'))
from kryon_apps_test import guest_overlay
from test_logwindow import private_display
from test_tcltk import EMU, ROOT, launch, stop, until

HERE = Path(__file__).resolve().parent
BUILD = ROOT / 'build/wm-apps'
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
    BUILD.mkdir(parents=True, exist_ok=True)
    fixtures = BUILD / 'snake-fixture'
    fixtures.mkdir(exist_ok=True)
    # Ziran source lines stay under 4096 bytes: long lines continue after a trailing backslash.
    wrapped = []
    for line in (HERE / 'snake_games.expected').read_text(encoding='utf-8').splitlines():
        while len(line) > 500:
            wrapped.append(line[:500] + '\\')
            line = line[500:]
        wrapped.append(line)
    games = ''.join(line + '\n' for line in wrapped)
    (fixtures / 'snake_games_fixture.zi').write_text(f'Games :: #string GAMES_END\n{games}GAMES_END;\n',
                                                     encoding='utf-8')
    model = BUILD / 'snake_model_test.zx'
    subprocess.run(['ziran', 'bundle', '--project', '--module-path', fixtures, '--entry',
                    'snake_model_test:main', '-o', model, 'snake_model_test.zi'],
                   cwd=HERE, env=env, check=True, timeout=120)
    result = subprocess.run(['zi2zx', 'run', '--backend', 'engine', model], env=env,
                            capture_output=True, text=True, check=True, timeout=120)
    replays = sum(1 for _, replay, _ in recorded() if replay != '12.0p')
    assert result.stdout.splitlines() == [
        f'Snake replayed {replays + 1} recorded Dis games to the same boards and scores', '0'] \
        and not result.stderr, result
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
    crop = image.crop(box)
    crop = crop.resize((crop.width * 4, crop.height * 4))
    png = io.BytesIO()
    crop.save(png, format='PNG')
    return subprocess.run(['tesseract', 'stdin', 'stdout', '--psm', '7'], input=png.getvalue(),
                          capture_output=True, check=True, timeout=5).stdout.decode().strip()


class Guest:
    def __init__(self, env, args, operands, setup=''):
        bundle = '/' + args.bundle.resolve().relative_to(ROOT).as_posix()
        command = setup + f'wm/wm zxrun -w {bundle}' + ''.join(f" '{word}'" for word in operands)
        self.env = env
        self.app = launch(env, args.emu, '-p', 'main=128M', '-r', ROOT, '-g', '640x480', '/dis/sh.dis', '-c',
                          guest_overlay(args.guest_overlay) + command, stdin=subprocess.DEVNULL)
        self.window = until(lambda: self.run('xdotool', 'search', '--onlyvisible', '--name', '^inferno$',
                                             check=False).strip(), 'private guest did not open').decode().split()[0]

    def run(self, *command, check=True):
        return subprocess.run(command, env=self.env, capture_output=True, check=check, timeout=5).stdout

    def capture(self):
        return Image.open(io.BytesIO(self.run('import', '-window', self.window, 'png:-'))).convert('RGB')

    def settled(self, description, timeout=60):
        def still():
            first = self.capture()
            if canvas_origin(first) is None:
                return None
            time.sleep(0.6)
            second = self.capture()
            return second if first.tobytes() == second.tobytes() else None
        try:
            return until(still, description, timeout=timeout)
        except AssertionError:
            self.capture().save(BUILD / 'snake-failure.png')
            raise

    def key(self, name):
        self.run('xdotool', 'key', '--window', self.window, name)
        time.sleep(0.15)


def check_replays(env, args):
    for score, replay, expected in recorded():
        guest = Guest(env, args, [replay])
        try:
            image = guest.settled(f'Snake replay {replay[:12]} did not finish')
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
        paused = guest.settled('Snake did not pause on p', timeout=10)
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
        crashed = guest.settled('Snake did not crash')
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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('bundle', type=Path, nargs='?', default=ROOT / 'dis/wm/snake.zx')
    parser.add_argument('--emu', type=Path, default=ROOT / 'emu/Linux/o.emu')
    parser.add_argument('--guest-overlay', type=Path)
    args = parser.parse_args()
    for name in ('XDG_RUNTIME_DIR', 'XDG_SESSION_ID', 'SESSION_MANAGER', 'HARMONY_GUEST_DISPLAY'):
        os.environ.pop(name, None)
    check_model(os.environ.copy())
    with private_display() as env:
        check_replays(env, args)
        check_keys(env, args)
        check_crash_record(env, args)


if __name__ == '__main__':
    main()
