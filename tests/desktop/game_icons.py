#!/usr/bin/env python3
import argparse
from hashlib import file_digest
import os
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory
import tomllib

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / 'build/desktop-registry'
FIXTURE = OUTPUT / 'game-icons'
GENERATOR = ROOT / 'tools/generate-app-catalog.py'
SIZES = (16, 22, 24, 32, 48, 64, 128, 256, 512)
STEMS = ('bounce', 'brutus', 'c4', 'collide', 'polyhedra', 'reversi', 'snake', 'sweeper', 'tetris')


def digest(path):
    with path.open('rb') as stream:
        return file_digest(stream, 'sha256').hexdigest()


def manifest(root):
    return {path.relative_to(root): digest(path) for path in root.rglob('*') if path.is_file()}


def prepare():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    if FIXTURE.exists():
        assert (FIXTURE / '.game-icons-fixture').exists(), 'unrecognized fixture directory'
        shutil.rmtree(FIXTURE)
    FIXTURE.mkdir()
    (FIXTURE / '.game-icons-fixture').touch()
    subprocess.run(['python3', str(GENERATOR), '--guest-assets', '--output-root', str(FIXTURE)], check=True)
    first = manifest(FIXTURE)
    first.pop(Path('.game-icons-fixture'))
    with TemporaryDirectory(prefix='game-icons-regenerated-', dir=OUTPUT) as directory:
        second = Path(directory)
        subprocess.run(['python3', str(GENERATOR), '--guest-assets', '--output-root', str(second)], check=True)
        assert first == manifest(second), 'fresh regeneration differs'
    pngs = []
    for stem in STEMS:
        icon = 'taiji-' + ('brutus' if stem == 'brutus' else 'game-' + stem)
        assert (ROOT / f'icons/apps/{icon}.svg').is_file()
        for size in SIZES:
            path = FIXTURE / f'lib/icons/hicolor/{size}x{size}/apps/{icon}.png'
            pngs.append(path)
            if size <= 256:
                assert path.with_suffix('.rgba').stat().st_size == size * size * 4
    dimensions = subprocess.check_output(['magick', 'identify', '-format', '%w %h\n', *map(str, pngs)], text=True)
    assert dimensions.splitlines() == [f'{size} {size}' for _ in STEMS for size in SIZES]
    files = sorted(path.name for path in (FIXTURE / 'lib/apps').glob('*.desktop'))
    (FIXTURE / 'catalog-files').write_text(''.join(name + '\n' for name in files))
    selected = FIXTURE / 'lib/apps/org.taijiosnet.wm-snake.desktop'
    selected.write_text(selected.read_text() + 'X-Local-Preservation=keep\n')
    previous = digest(selected)
    subprocess.run(['python3', str(GENERATOR), '--guest-assets', '--output-root', str(FIXTURE)], check=True)
    assert digest(selected) == previous, 'add-only installer replaced a local catalog edit'
    print(f'GAME_ICON_REGENERATION_OK files={len(first)} pngs={len(pngs)} sizes={len(SIZES)}', flush=True)


def test():
    env = os.environ.copy()
    for key in ('DISPLAY', 'WAYLAND_DISPLAY', 'WAYLAND_SOCKET', 'XAUTHORITY',
                'DBUS_SESSION_BUS_ADDRESS', 'SESSION_MANAGER', 'ICEAUTHORITY'):
        env.pop(key, None)
    env.update(HARMONY_DESKTOP_RECOVERY='0', YUE_DESKTOP_RECOVERY='0',
               ZIRAN_STD=str(ROOT.parents[1] / 'ziranlang/ziran/std'))
    source = ROOT / 'tests/desktop/game_icons_test.zi'
    bundle = OUTPUT / 'game-icons-test.zx'
    native_result = subprocess.run(['ziran', 'run', '--target=c', '--root', str(source.parent),
                                    '--module-path', str(ROOT / 'appl/cmd'), str(source)],
                                   cwd=ROOT, env=env, text=True, capture_output=True, timeout=120)
    print(native_result.stdout, end='', flush=True)
    print(native_result.stderr, end='', flush=True)
    native_result.check_returncode()
    kryon = ROOT.parents[1] / 'kryonlabs/kryon'
    package = tomllib.loads((kryon / 'ziran.toml').read_text())
    modules = []
    for directory in package['package']['module_roots']:
        modules.extend(['--module-path', str(kryon / directory)])
    subprocess.run(['ziran', 'bundle', '--root', str(source.parent),
                    '--define', 'GAME_ICONS_GUEST', '--module-path', str(ROOT / 'appl/cmd'),
                    '--module-path', str(ROOT.parents[1] / 'kryonlabs/rill/app'),
                    '--module-path', 'kryon=' + str(ROOT.parents[1] / 'kryonlabs/kryon/src/ui'),
                    *modules,
                    '--bind-host', 'taijios_io', '--bind-host', 'taijios_wm',
                    '--entry', 'game_icons_test:main', '-o', str(bundle), str(source)],
                   cwd=ROOT, env=env, check=True)
    home = FIXTURE / 'home'
    home.mkdir(exist_ok=True)
    command = ('home=/build/desktop-registry/game-icons/home; '
               'bind /build/desktop-registry/game-icons/lib/apps /lib/apps; '
               'bind /build/desktop-registry/game-icons/lib/icons /lib/icons; '
               'zxrun /build/desktop-registry/game-icons-test.zx')
    guest = subprocess.run([str(ROOT / 'emu/Linux/o.emu'), '-p', 'main=128M', '-r', str(ROOT),
                            '/dis/sh.dis', '-c', command], env=env, cwd=ROOT,
                           text=True, capture_output=True, timeout=180)
    print(guest.stdout, end='', flush=True)
    print(guest.stderr, end='', flush=True)
    assert guest.returncode in (0, -9) and not guest.stderr and guest.stdout.endswith('\n0\n'), 'guest failed'
    native_rows = [line for line in native_result.stdout.splitlines() if line.startswith('GAME_ICON_PIXELS ')]
    guest_rows = [line for line in guest.stdout.splitlines() if line.startswith('GAME_ICON_PIXELS ')]
    assert len(native_rows) == 63 and native_rows == guest_rows, 'native/ZX decoded pixels differ'
    assert 'GAME_ICONS_COVERAGE_OK games=8 ' in native_result.stdout
    assert 'GAME_ICONS_COVERAGE_OK games=8 ' in guest.stdout
    print('GAME_ICON_NATIVE_ZX_PARITY_OK cases=63', flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--prepare', action='store_true')
    parser.add_argument('--test', action='store_true')
    args = parser.parse_args()
    protected = [ROOT / 'emu/Linux/o.emu', ROOT / 'dis/wm/rill.zx', ROOT / 'dis/lib/window_chrome.zx']
    before = [digest(path) for path in protected]
    if args.prepare:
        prepare()
    if args.test:
        test()
    assert [digest(path) for path in protected] == before, 'installed executable pair changed'


if __name__ == '__main__':
    main()
