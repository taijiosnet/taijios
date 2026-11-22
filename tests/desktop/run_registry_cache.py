#!/usr/bin/env python3
import argparse
from pathlib import Path
import subprocess

root = Path(__file__).resolve().parents[2]
output = root / 'build/desktop-registry'
parser = argparse.ArgumentParser()
parser.add_argument('--benchmark', action='store_true')
args = parser.parse_args()
home = output / 'cache-home'
system = output / 'cache-system'
user = home / 'lib/apps'
user.mkdir(parents=True, exist_ok=True)
system.mkdir(parents=True, exist_ok=True)
for directory in (user, system):
    for entry in directory.glob('*.desktop'):
        entry.unlink()
(home / 'probe.dis').unlink(missing_ok=True)
def entry(directory, name, fields):
    command = '' if any(line.startswith('Exec=') for line in fields.splitlines()) else 'Exec=p\n'
    (directory / name).write_text('[Desktop Entry]\nType=Application\n' + command + fields)
entry(user, 'a.desktop', 'Name=Hidden override\nHidden=true\n')
entry(user, 'z.desktop', 'Name=User\nX-Taiji-MenuName=Old alias\n')
entry(system, 'a.desktop', 'Name=System masked\n')
entry(system, 'b.desktop', 'Name=Default\nName[sr]=Language\nName[sr_RS]=Country\nName[sr@latin]=Modifier\nName[sr_RS@latin]=Full\n')
entry(system, 'c.desktop', 'Name=Not shown\nNoDisplay=true\n')
entry(system, 'd.desktop', 'Name=Other desktop\nOnlyShowIn=KDE;\n')
entry(system, 'e.desktop', 'Name=Excluded\nNotShowIn=Rill;\n')
entry(system, 'f.desktop', 'Name=Conditional\nTryExec=/build/desktop-registry/cache-home/probe.dis\n')
entry(system, 'g.desktop', 'Name=Invalid exec\nExec=p %Z\n')
(system / 'h.desktop').write_text('[Desktop Entry]\nType=Link\nName=Link\nExec=p\n')
entry(system, 'i.desktop', 'Name=Keep\nMimeType=image/png;\n')
entry(system, 'costarring.desktop', 'Name=costarring\nMimeType=image/png;\n')
entry(system, 'liquid.desktop', 'Name=liquid\nMimeType=image/png;\n')
(home / 'lib/mimeapps.list').write_text('[Default Applications]\nimage/png=missing.desktop;liquid.desktop;costarring.desktop;\n')
setup = 'REGISTRY_TICK=x; LC_ALL=sr_RS.UTF-8@latin; LC_MESSAGES=; LANG=; '
if not args.benchmark:
    setup += 'home=/build/desktop-registry/cache-home; bind /build/desktop-registry/cache-system /lib/apps; '
command = setup + 'zxrun /build/desktop-registry/registry-cache-test.zx' + (' benchmark' if args.benchmark else '')
result = subprocess.run([str(root / 'emu/Linux/o.emu'), '-p', 'main=128M', '-r', str(root), '/dis/sh.dis', '-c', command], capture_output=True, text=True, timeout=120)
print(result.stdout, end='')
print(result.stderr, end='')
assert result.returncode in (0, -9), result.returncode
assert not result.stderr and result.stdout.endswith('\n0\n'), 'guest failed'
assert ('REGISTRY_CACHE_BENCH ' if args.benchmark else 'REGISTRY_CACHE_RELOAD_PARITY_OK\n') in result.stdout
