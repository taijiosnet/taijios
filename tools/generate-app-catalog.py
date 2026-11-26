#!/usr/bin/env python3
import argparse
import os
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
SIZES = (16, 22, 24, 32, 48, 64, 128, 256, 512)
ICONS = {
    'terminal': ('#384653', '>_'), 'files': ('#d29a32', '▰'),
    'web': ('#278798', '◎'), 'development': ('#6654a4', '{}'),
    'system': ('#587184', '⚙'), 'utilities': ('#b76d37', '◆'),
    'graphics': ('#9f5686', '✎'), 'games': ('#49886a', '✚'),
    'office': ('#4f709e', '▤'), 'media': ('#b05d68', '▶'),
    'help': ('#4b859d', '?'), 'clock': ('#757eab', '◷'),
}
GAMES = ('bounce', 'c4', 'collide', 'polyhedra', 'reversi', 'snake', 'sweeper', 'tetris')
DESCRIPTIONS = {
    'bounce': 'Draw paths for bouncing balls',
    'brutus': 'Write and format rich text',
    'c4': 'Connect four counters in a row',
    'collide': 'Explore collisions between moving solids',
    'polyhedra': 'Explore three-dimensional polyhedra',
    'reversi': 'Capture opposing discs on the board',
    'snake': 'Guide the snake to food and avoid its tail',
    'sweeper': 'Find the mines without uncovering them',
    'tetris': 'Stack falling blocks to clear complete rows',
}

def run(*args):
    subprocess.run(args, check=True, stdout=subprocess.DEVNULL)

def render_png(path, *args):
    path.parent.mkdir(parents=True, exist_ok=True)
    run('magick', *args, '-strip', str(path))


def generate_host_icons(output):
    icons = output / 'icons/taijios'
    for size in SIZES:
        render_png(icons / f'{size}.png', str(ROOT / 'icons/taijios/logo.png'),
                   '-resize', f'{size}x{size}')
    values = []
    for size in (32, 64):
        pixels = subprocess.check_output(['magick', str(icons / f'{size}.png'), '-depth', '8', 'rgba:-'])
        values.extend((size, size))
        values.extend((a << 24) | (r << 16) | (g << 8) | b
                      for r, g, b, a in zip(pixels[::4], pixels[1::4], pixels[2::4], pixels[3::4]))
    header = 'static unsigned long taijios_window_icon[] = {\n'
    for offset in range(0, len(values), 8):
        header += '\t' + ', '.join(f'0x{v:08x}UL' for v in values[offset:offset+8]) + ',\n'
    path = output / 'emu/port/taijios-icon.h'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(header + '};\n', encoding='ascii')


def generate_app_icons(output):
    theme = output / 'lib/icons/hicolor'
    for name, (color, glyph) in ICONS.items():
        for size in SIZES:
            directory = theme / f'{size}x{size}/apps'
            path = directory / f'taiji-{name}.png'
            render_png(path, '-size', '128x128', 'xc:none', '-fill', color,
                       '-draw', 'roundrectangle 3,3 124,124 24,24', '-fill', 'white',
                       '-font', 'DejaVu-Sans', '-pointsize', '54', '-gravity', 'center',
                       '-annotate', '+0+0', glyph, '-resize', f'{size}x{size}', '-depth', '8')
            if size <= 256:
                run('magick', str(path), '-depth', '8', 'rgba:' + str(path.with_suffix('.rgba')))
    for source in sorted((ROOT / 'icons/apps').glob('*.svg')):
        for size in SIZES:
            path = theme / f'{size}x{size}/apps/{source.stem}.png'
            render_png(path, '-background', 'none', '-density', '384', 'MSVG:' + str(source),
                       '-resize', f'{size}x{size}', '-depth', '8', '-define', 'png:color-type=6')
            if size <= 256:
                run('magick', str(path), '-depth', '8', 'rgba:' + str(path.with_suffix('.rgba')))
    directories = ','.join(f'{s}x{s}/apps' for s in SIZES)
    text = '[Icon Theme]\nName=TaijiOS\nComment=TaijiOS application icons\nDirectories=' + directories + '\n'
    for size in SIZES:
        text += f'\n[{size}x{size}/apps]\nSize={size}\nType=Fixed\nContext=Applications\n'
    (theme / 'index.theme').write_text(text, encoding='utf-8')

DESKTOP_ICONS = {
    'user-home': ('#4f709e', 'polygon 20,63 64,25 108,63 95,63 95,105 74,105 74,78 54,78 54,105 33,105 33,63'),
    'folder': ('#d29a32', 'roundrectangle 20,39 108,102 7,7 rectangle 22,29 64,47'),
    'drive-harddisk': ('#587184', 'roundrectangle 20,43 108,99 9,9'),
    'user-trash': ('#587184', 'roundrectangle 38,44 90,105 5,5 rectangle 31,32 97,40 rectangle 51,23 77,32'),
    'edit-paste': ('#4f709e', 'roundrectangle 30,30 98,106 6,6'),
    'audio-volume-high': ('#6654a4', 'polygon 23,52 43,52 65,31 65,97 43,76 23,76'),
    'audio-volume-muted': ('#6654a4', 'polygon 23,52 43,52 65,31 65,97 43,76 23,76'),
}

def generate_desktop_icons(output):
    for name, (color, shape) in DESKTOP_ICONS.items():
        for size in SIZES:
            path = output / f'lib/icons/hicolor/{size}x{size}/apps/{name}.png'
            extra = []
            if name == 'drive-harddisk':
                extra = ['-fill', color, '-draw', 'rectangle 27,77 101,81 circle 89,90 94,90']
            elif name == 'user-trash':
                extra = ['-stroke', color, '-strokewidth', '5', '-draw', 'line 52,54 52,94 line 76,54 76,94']
            elif name == 'edit-paste':
                extra = ['-fill', color, '-draw', 'roundrectangle 43,24 85,44 4,4', '-stroke', color, '-strokewidth', '4', '-draw', 'line 44,62 84,62 line 44,77 84,77 line 44,92 75,92']
            elif name == 'audio-volume-high':
                extra = ['-fill', 'none', '-stroke', 'white', '-strokewidth', '7', '-draw', 'path "M 78,45 Q 96,64 78,83" path "M 91,31 Q 120,64 91,97"']
            elif name == 'audio-volume-muted':
                extra = ['-stroke', 'white', '-strokewidth', '7', '-draw', 'line 81,50 105,78 line 105,50 81,78']
            render_png(path, '-size', '128x128', 'xc:none', '-fill', color,
                       '-draw', 'roundrectangle 3,3 124,124 24,24', '-fill', 'white',
                       '-draw', shape, *extra, '-resize', f'{size}x{size}', '-depth', '8')
            if size <= 256:
                run('magick', str(path), '-depth', '8', 'rgba:' + str(path.with_suffix('.rgba')))
    aliases = {'edit-copy': 'edit-paste', 'audio-volume-high-symbolic': 'audio-volume-high',
               'audio-volume-medium-symbolic': 'audio-volume-high', 'audio-volume-low-symbolic': 'audio-volume-high',
               'audio-volume-muted-symbolic': 'audio-volume-muted'}
    for alias, original in aliases.items():
        for size in SIZES:
            directory = output / f'lib/icons/hicolor/{size}x{size}/apps'
            shutil.copyfile(directory / (original+'.png'), directory / (alias+'.png'))
            if size <= 256:
                shutil.copyfile(directory / (original+'.rgba'), directory / (alias+'.rgba'))

COMMAND_APPS = {'wm/coffee': '/zx/coffee.zx', 'wm/man': '/zx/man.zx'}

NAMES = {
    'about': 'About TaijiOS', 'avi': 'AVI Player', 'bounce': 'Bounce', 'brutus': 'Brutus',
    'c4': 'Connect Four', 'calendar': 'Calendar', 'clock': 'Clock', 'coffee': 'Coffee',
    'collide': 'Collision Demo', 'colors': 'Colours', 'counter': 'Counter', 'cprof': 'CPU Profiler',
    'date': 'Date and Time', 'deb': 'Debugger', 'dir': 'Directory Browser', 'edit': 'Edit',
    'filename': 'File Chooser', 'ftree': 'File Tree', 'getauthinfo': 'Authentication',
    'keyboard': 'Keyboard', 'logon': 'Login', 'logwindow': 'System Log', 'man': 'Manual',
    'mand': 'Manual Search', 'mash': 'Mash Shell', 'memory': 'Memory Monitor', 'mpeg': 'MPEG Player',
    'mprof': 'Memory Profiler', 'pen': 'Pen', 'polyhedra': 'Polyhedra', 'prof': 'Profiler',
    'readmail': 'Read Mail', 'remotelogon': 'Remote Login',
    'reversi': 'Reversi', 'rmtdir': 'Remote Files', 'rt': 'Module Manager', 'sendmail': 'Send Mail',
    'sh': 'Shell', 'snake': 'Snake', 'stopwatch': 'Stopwatch', 'sweeper': 'Minesweeper',
    'task': 'Task Manager', 'taskmgr': 'Task Manager', 'telnet': 'Telnet', 'tetris': 'Tetris',
    'unibrowse': 'Unicode Browser', 'view': 'Image Viewer', 'vt': 'Virtual Terminal',
    'wish': 'Tk Shell', 'wmplay': 'Media Player', 'explorer': 'Files', 'acme': 'Acme',
    'charon': 'Web Browser', 'graph0': 'Graph Plotter', 'linbench': 'Linear Algebra Benchmark',
}

def group(name):
    if name in GAMES:
        return 'Game', 'game-' + name
    for names, category, icon in (
        ('avi mpeg wmplay', 'AudioVideo', 'media'),
        ('colors pen view', 'Graphics', 'graphics'),
        ('readmail remotelogon rmtdir sendmail telnet charon', 'Network', 'web'),
        ('acme edit deb cprof mprof prof wish', 'Development', 'development'),
        ('brutus', 'Office', 'brutus'), ('calendar', 'Office', 'office'),
        ('clock date stopwatch counter', 'Utility', 'clock'),
        ('dir ftree explorer filename', 'Utility', 'files'),
        ('sh mash vt', 'System', 'terminal'), ('man mand unibrowse', 'Utility', 'help'),
    ):
        if name in names.split():
            return category, icon
    return 'System', 'system'

def generate_catalog(output):
    catalog = output / 'lib/apps'
    catalog.mkdir(parents=True, exist_ok=True)
    exclude = {'wm', 'toolbar', 'desktop_panel', 'window_chrome_service', 'smenu', 'debdata', 'debsrc', 'samstub', 'samtk'}
    apps = {}
    for source in sorted((ROOT / 'appl/wm').glob('*.b')):
        if source.stem not in exclude:
            apps['wm/' + source.stem] = False
    for name in ('about', 'avi', 'coffee', 'clock', 'counter', 'dir', 'explorer', 'logwindow', 'man', 'memory', 'calendar', 'polyhedra', 'snake', 'stopwatch', 'sweeper', 'taskmgr', 'tetris', 'view', 'wish', 'bounce', 'c4', 'collide', 'mand', 'reversi', 'edit', 'unibrowse', 'wmplay', 'sendmail', 'readmail', 'telnet', 'vt', 'rt', 'brutus', 'sam'):
        apps['wm/' + name] = False
    for source in sorted((ROOT / 'appl/cmd').rglob('*.b')):
        relative = source.relative_to(ROOT / 'appl/cmd').with_suffix('').as_posix()
        if relative in ('emuinit', 'wm', 'zxrun') or relative.startswith(('sh/', 'install/')):
            continue
        apps[relative] = relative not in ('acme', 'charon', 'math/graph0', 'math/linbench')
    for name in ('cat', 'echo', 'basename', 'cleanname', 'wc', 'uniq', 'tr', 'tee', 'cp', 'test', 'ls', 'mkdir', 'tclsh', 'irtest', 'comm'):
        apps.setdefault(name, True)
    for relative, hidden in apps.items():
        name = relative.split('/')[-1]
        title = NAMES.get(name, name.replace('-', ' ').replace('_', ' ').title())
        category, icon = group(name)
        program = '/zx/' + relative + '.dis'
        if relative == 'wm/view' or (ROOT / ('zx/' + relative + '.zx')).exists():
            program = '/zx/' + relative + '.zx'
        program = COMMAND_APPS.get(relative, program)
        if relative == 'wm/task':
            hidden = True
        if relative.startswith('wm/'):
            terminal = False
        else:
            terminal = hidden
        ident = 'org.taijiosnet.' + relative.replace('/', '-')
        text = f'[Desktop Entry]\nType=Application\nVersion=1.5\nName={title}\nGenericName={title}\n'
        arguments = ' %f' if relative == 'wm/view' else ''
        description = DESCRIPTIONS.get(name, title)
        text += f'Comment={description}\nIcon=taiji-{icon}\nExec={program}{arguments}\nTryExec={program}\n'
        if relative == 'wm/view':
            text += 'MimeType=image/png;image/jpeg;image/gif;\n'
        text += f'Terminal={str(terminal).lower()}\nCategories={category};\nKeywords=TaijiOS;{name};\n'
        if hidden:
            text += 'NoDisplay=true\n'
        aliases = {'wm/about': 'About', 'wm/dir': 'Directory Browser', 'wm/taskmgr': 'Task Manager'}
        if relative in aliases:
            text += f'X-Taiji-MenuName={aliases[relative]}\n'
        (catalog / (ident + '.desktop')).write_text(text, encoding='utf-8')
    families = len(ICONS) + len(list((ROOT / 'icons/apps').glob('*.svg')))
    print(f'Generated {len(apps)} desktop entries, {families} app icon families and standard desktop icons.')


def read_preinstall(manifest):
    """Parse the preinstall manifest into rows.

    Returns a list of dicts with repo, bundle, ident, name, icon, categories,
    size, sha256 and first_run. Blank lines and lines starting with # are
    ignored. A malformed row raises ValueError naming its line number, so a
    broken manifest fails the build rather than silently shipping less.
    """
    rows = []
    with open(manifest, encoding='utf-8') as handle:
        for number, line in enumerate(handle, 1):
            line = line.rstrip('\n')
            if not line.strip() or line.lstrip().startswith('#'):
                continue
            columns = line.split('\t')
            if len(columns) != 9:
                raise ValueError(f'{manifest}:{number}: expected 9 tab-separated columns, found {len(columns)}')
            repo, bundle, ident, name, icon, categories, size, digest, first_run = columns
            if not bundle or not ident:
                raise ValueError(f'{manifest}:{number}: bundle and desktop id are required')
            if first_run not in ('root', 'lazy'):
                raise ValueError(f'{manifest}:{number}: first-run must be root or lazy, found {first_run!r}')
            rows.append({
                'repo': repo, 'bundle': bundle, 'ident': ident, 'name': name,
                'icon': icon, 'categories': categories, 'size': size,
                'sha256': digest, 'first_run': first_run,
            })
    return rows


def preinstall_entry(output, row):
    """The .desktop text for one manifest row, or None when its bundle is absent."""
    if not (output / row['bundle'].lstrip('/')).exists():
        return None
    text = '[Desktop Entry]\nType=Application\nVersion=1.5\n'
    text += f"Name={row['name']}\nGenericName={row['name']}\n"
    text += f"Comment={DESCRIPTIONS.get(row['bundle'].rsplit('/', 1)[-1].removesuffix('.zx'), row['name'])}\n"
    text += f"Icon=taiji-{row['icon']}\n"
    text += f"Exec={row['bundle']}\nTryExec={row['bundle']}\n"
    text += f"Terminal=false\nCategories={row['categories']};\n"
    text += f"Keywords=TaijiOS;{row['name']};\nX-Taiji-Preinstall={row['first_run']}\n"
    return text


def generate_preinstall_catalog(output, manifest):
    """Emit catalog entries for the preinstall manifest only.

    Existing entries are left untouched, and a row whose bundle is not present
    in output emits nothing, so the manifest can name apps before they ship.
    """
    catalog = output / 'lib/apps'
    catalog.mkdir(parents=True, exist_ok=True)
    rows = read_preinstall(manifest)
    emitted = 0
    for row in rows:
        text = preinstall_entry(output, row)
        if text is None:
            continue
        (catalog / (row['ident'] + '.desktop')).write_text(text, encoding='utf-8')
        emitted += 1
    print(f'Preinstalled {emitted} of {len(rows)} manifest rows into {catalog}.')


def generate_guest_assets(output):
    # Finish rendering before adding anything to the guest. A hard link publishes
    # each complete file without replacing an existing file, even on concurrent installs.
    output.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix='.taijios-assets-', dir=output) as directory:
        staging = Path(directory)
        generate_desktop_icons(staging)
        generate_app_icons(staging)
        generate_catalog(staging)
        shutil.copyfile(ROOT / 'lib/mimeapps.list', staging / 'lib/mimeapps.list')
        for source in sorted(path for path in staging.rglob('*') if path.is_file()):
            destination = output / source.relative_to(staging)
            destination.parent.mkdir(parents=True, exist_ok=True)
            source.chmod(0o644)
            try:
                os.link(source, destination)
            except FileExistsError:
                pass


def main():
    parser = argparse.ArgumentParser(description='Generate TaijiOS launcher and icon assets.')
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument('--guest-assets', action='store_true',
                       help='add missing guest catalog, icon theme and MIME defaults')
    modes.add_argument('--host-icons', action='store_true',
                       help='render the host icons and the X11 window icon header')
    modes.add_argument('--desktop-icons', action='store_true',
                       help='refresh only the standard guest desktop icons')
    parser.add_argument('--preinstall', type=Path, metavar='MANIFEST',
                        help='emit only the catalog entries named in a preinstall manifest')
    parser.add_argument('--output-root', type=Path, default=ROOT, help='destination tree (default: TaijiOS root)')
    args = parser.parse_args()
    if args.preinstall:
        generate_preinstall_catalog(args.output_root, args.preinstall)
    elif args.guest_assets:
        generate_guest_assets(args.output_root)
    elif args.host_icons:
        generate_host_icons(args.output_root)
    elif args.desktop_icons:
        generate_desktop_icons(args.output_root)
    else:
        generate_host_icons(args.output_root)
        generate_desktop_icons(args.output_root)
        generate_app_icons(args.output_root)
        generate_catalog(args.output_root)


if __name__ == '__main__':
    main()
