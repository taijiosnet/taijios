#!/usr/bin/env python3
"""Compare Winplace results with the captured Dis oracle."""

from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
import os
import random
import shutil
import signal
import subprocess


ROOT = Path(__file__).resolve().parents[2]
BUILD = ROOT / 'build/zx-smoke'
EMU = ROOT / 'Linux/386/bin/emu'
# Ordered output from the stock Dis module before its removal (184 cases).
EXPECTED = Path(__file__).with_name('winplace_expected.txt')
SEED = 0x715ACE

Rect = tuple[int, int, int, int]


@dataclass(frozen=True)
class Case:
    name: str
    wins: tuple[Rect, ...] = ()
    screen: Rect = (0, 0, 300, 200)
    last: Rect = (16, 24, 88, 70)
    size: tuple[int, int] = (50, 32)
    placement: Rect | None = None


def cases():
    full = ((0, 0, 300, 200),)
    rows = [
        Case('empty', placement=(0, 0, 50, 32)),
        Case('offset screen', screen=(-120, -40, 180, 160), placement=(-120, -40, -70, -8)),
        Case('empty auto width', size=(0, 0), placement=(0, 0, 300, 200)),
        Case('empty auto width too tall', size=(0, 201), placement=(0, 0, 150, 100)),
        Case('zero height request', size=(50, 0), placement=(0, 0, 50, 0)),
        Case('one interior', ((60, 30, 190, 140),)),
        Case('overlapping', ((30, 20, 120, 140), (85, 45, 230, 170), (150, 5, 290, 90))),
        Case('offscreen', ((-80, -90, -20, 330), (-40, -10, 48, 40), (260, 170, 340, 250))),
        Case('offscreen both axes', ((-80, -90, -20, -30), (320, 250, 480, 310))),
        Case('adjacent', ((10, 10, 140, 120), (140, 10, 260, 120), (10, 120, 260, 180))),
        Case('coincident endpoints', ((0, 0, 100, 100), (0, 0, 100, 100), (100, 100, 240, 170))),
        Case('coincident endpoints reversed', ((100, 100, 240, 170), (0, 0, 100, 100), (0, 0, 100, 100))),
        Case('zero width obstacle', ((105, 60, 105, 150),)),
        Case('top-left tie', ((110, 0, 190, 200),), size=(90, 190), placement=(0, 0, 90, 190)),
        Case('titlebar avoidance below', full, size=(290, 40), placement=(0, 20, 290, 60)),
        Case('titlebar avoidance left', full, size=(170, 200), placement=(0, 0, 170, 200)),
        Case('small titlebar clipped', ((90, 32, 110, 42),), size=(290, 180)),
        Case('partial largest entrance', ((0, 0, 135, 150), (135, 0, 300, 70)), size=(175, 190)),
        Case('partial largest exceeds screen', ((15, 40, 155, 165),), size=(340, 235), placement=(0, 0, 340, 235)),
        Case('cascade', full, last=(0, 0, 10, 10), size=(290, 190), placement=(0, 0, 290, 190)),
        Case('cascade offset', full, last=(-20, -20, 10, 10), size=(290, 190), placement=(0, 0, 290, 190)),
        Case('cascade preserves offscreen origin', full, last=(-40, -50, 10, 10), size=(290, 190),
             placement=(-20, -30, 270, 160)),
        Case('full cover zero width too tall', full, last=(-40, -50, 10, 10), size=(0, 201),
             placement=(-20, -30, -20, 171)),
        Case('signed area wrap', ((1000, 0, 30000, 60000), (40000, 0, 80000, 14000)),
             screen=(0, 0, 80000, 60000), size=(80001, 60001)),
    ]
    rng = random.Random(SEED)
    for i in range(160):
        x, y = rng.randrange(-80, 81), rng.randrange(-80, 81)
        w, h = rng.randrange(1, 50), rng.randrange(1, 50)
        xs = sorted({x - 4, x, x + w, x + w + 4, x + w // 2, x + w // 3})
        ys = sorted({y - 4, y, y + h, y + h + 4, y + h // 2, y + h // 3})
        windows = []
        for _ in range(rng.randrange(9)):
            x0, x1 = sorted(rng.sample(xs, 2))
            y0, y1 = sorted(rng.sample(ys, 2))
            windows.append((x0, y0, x1, y1))
        size = (rng.choice((0, w, rng.randrange(w * 2))), rng.choice((0, h, rng.randrange(h * 2))))
        rows.append(Case(f'seeded {i}', tuple(windows), (x, y, x + w, y + h), windows[0] if windows else (0, 0, 0, 0), size))
    return rows


ZI_PROBE = r'''
#import "winplace"

RectAt :: (data: []s32, i: s64) -> Rect {
    return .{data[i], data[i+1], data[i+2], data[i+3]}
}

main :: () -> s32 {
    data := s32.[ @DATA@ ];
    windows: [@MAX_WINS@]Rect
    index: s64
    id: s64
    while index < data.count {
        screen := RectAt(data[:], index)
        last := RectAt(data[:], index + 4)
        width := data[index + 8]
        height := data[index + 9]
        n := cast(s64)data[index + 10]
        index += 11
        for i: 0..n - 1 { windows[i] = RectAt(data[:], index + 4*i) }
        found := Find(windows[:n], screen)
        p := Place(windows[:n], screen, last, width, height)
        for i: 0..n - 1 {
            r := windows[i]
            original := RectAt(data[:], index + 4*i)
            if r.min_x != original.min_x || r.min_y != original.min_y ||
               r.max_x != original.max_x || r.max_y != original.max_y { return 1 }
        }
        print("C % %\n", id, found.count)
        for r: found { print("R % % % %\n", r.min_x, r.min_y, r.max_x, r.max_y) }
        print("P % % % %\n", p.min_x, p.min_y, p.max_x, p.max_y)
        index += 4*n
        id += 1
    }
    print("WINPLACE_DONE\n")
    return 0
}
'''


def run(argv, *, guest=False):
    env = os.environ.copy()
    for name in ('DISPLAY', 'WAYLAND_DISPLAY', 'XAUTHORITY', 'DBUS_SESSION_BUS_ADDRESS',
                 'XDG_RUNTIME_DIR', 'SESSION_MANAGER'):
        env.pop(name, None)
    env['HARMONY_DESKTOP_RECOVERY'] = '0'
    with subprocess.Popen(argv, cwd=ROOT, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, text=True, start_new_session=True) as process:
        try:
            stdout, stderr = process.communicate(timeout=15 if guest else 45)
        except subprocess.TimeoutExpired as error:
            with suppress(ProcessLookupError):
                os.killpg(process.pid, signal.SIGKILL)
            diagnostic = ((error.stderr or b'')[-3500:] + b'\n' + (error.stdout or b'')[-1600:])
            raise AssertionError(f'{argv[0]} timed out\n{diagnostic.decode(errors="replace")}') from None
    # Inferno can signal its own process group during normal shutdown.
    if process.returncode not in ((0, -9) if guest else (0,)) or stderr:
        raise AssertionError(f'{argv[0]} exited {process.returncode}\n{stderr[:3500]}\n{stdout[-1600:]}')
    return stdout


def guest_run(command):
    output = run([EMU, '-r', ROOT, '/dis/sh.dis', '-c',
                  f'{command}; echo WINPLACE_EMU_DONE'], guest=True)
    assert output.endswith('WINPLACE_EMU_DONE\n'), output[-600:]
    return output.removesuffix('WINPLACE_EMU_DONE\n')


def parse(output, inputs, target):
    output = output.removesuffix('0\n')  # ZX CLI prints the entry result.
    lines = output.splitlines()
    assert lines and lines[-1] == 'WINPLACE_DONE', (target, lines[-10:])
    at = 0
    results = []
    for i, case in enumerate(inputs):
        _, index, count = lines[at].split()
        count = int(count)
        assert lines[at] == f'C {i} {count}' and int(index) == i and count >= 0, (target, case.name)
        rows = []
        for line in lines[at+1:at+1+count]:
            marker, *coords = line.split()
            assert marker == 'R' and len(coords) == 4, (target, case.name, line)
            rows.append(tuple(map(int, coords)))
        marker, *coords = lines[at+1+count].split()
        assert marker == 'P' and len(coords) == 4, (target, case.name)
        results.append((tuple(rows), tuple(map(int, coords))))
        at += count + 2
    assert at == len(lines) - 1, (target, lines[at:at+5])
    return results


def compare(expected, actual, inputs, target):
    for case, (rows, place), (actual_rows, actual_place) in zip(inputs, expected, actual, strict=True):
        assert actual_rows == rows, (target, case, 'ordered Find', rows, actual_rows)
        assert actual_place == place, (target, case, 'Place', place, actual_place)
    print(f'{target} matched {len(inputs)} cases and {sum(len(rows) for rows, _ in expected)} ordered Find rows')


def main():
    inputs = cases()
    data = '\n'.join('        ' + ', '.join(map(str, (*c.screen, *c.last, *c.size, len(c.wins),
                                                     *(v for r in c.wins for v in r)))) + ',' for c in inputs)
    zi2zx = shutil.which('zi2zx') or Path.home() / '.local/bin/zi2zx'
    BUILD.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=BUILD, prefix='winplace-') as folder:
        folder = Path(folder)
        guest_path = '/' + folder.relative_to(ROOT).as_posix()
        expected = parse(EXPECTED.read_text(encoding='ascii'), inputs, 'stock Dis')
        assert expected[0][0] == (inputs[0].screen,) * 2, expected[0]
        for case, (_, placed) in zip(inputs, expected, strict=True):
            if case.placement is not None:
                assert placed == case.placement, (case.name, case.placement, placed)

        source = folder / 'probe.zi'
        source.write_text(ZI_PROBE.replace('@DATA@', data.rstrip(',')).replace(
            '@MAX_WINS@', str(max(len(c.wins) for c in inputs))), encoding='utf-8')
        options = ['--checks', '--root', folder, '--module-path', ROOT / 'appl/lib', '--entry', 'probe:main']
        image = folder / 'probe.zx'
        run([zi2zx, *options, '-o', image, source])
        for target, argv in (
            ('Direct native', [zi2zx, 'run', '--backend', 'native', image]),
            ('Portable ZX engine', [zi2zx, 'run', '--backend', 'engine', image]),
        ):
            compare(expected, parse(run(argv), inputs, target), inputs, target)
        hosted = guest_run(f'/dis/zxrun.dis {guest_path}/probe.zx')
        compare(expected, parse(hosted, inputs, 'TaijiOS hosted ZX'), inputs, 'TaijiOS hosted ZX')


if __name__ == '__main__':
    main()
