#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
data=${XDG_DATA_HOME:-"$HOME/.local/share"}
emulator="$root/Linux/386/bin/emu"
test -x "$emulator"
mkdir -p "$data/applications"
for size in 16 22 24 32 48 64 128 256 512; do
    directory="$data/icons/hicolor/${size}x${size}/apps"
    mkdir -p "$directory"
    install -m 644 "$root/icons/taijios/${size}.png" "$directory/org.taijiosnet.TaijiOS.png"
done
python3 - "$root" "$emulator" "$data/applications/org.taijiosnet.TaijiOS.desktop" <<'PY'
import sys
from pathlib import Path
root, emulator, destination = sys.argv[1:]
def string(value):
    return value.replace('\\', '\\\\').replace('\n', '\\n')
def argument(value):
    escaped = ''.join('\\' + c if c in '\\"`$' else c for c in value)
    return string('"' + escaped + '"')
launch = ' '.join(map(argument, (emulator, '-r', root, '-g', '1024x768', 'wm/wm')))
Path(destination).write_text('[Desktop Entry]\nType=Application\nVersion=1.5\n'
    'Name=TaijiOS\nGenericName=TaijiOS Desktop\nComment=Run the TaijiOS guest desktop\n'
    'Icon=org.taijiosnet.TaijiOS\nExec=' + launch + '\nTryExec=' + string(emulator) + '\n'
    'Path=' + string(root) + '\nTerminal=false\nStartupNotify=false\nStartupWMClass=inferno\n'
    'Categories=System;Emulator;\nKeywords=Taiji;Inferno;Desktop;Virtual Machine;\nActions=Open;\n'
    '\n[Desktop Action Open]\nName=Open TaijiOS\nExec=' + launch + '\n')
PY
desktop-file-validate "$data/applications/org.taijiosnet.TaijiOS.desktop"
update-desktop-database "$data/applications"
if ! gtk-update-icon-cache -f -t "$data/icons/hicolor"; then
    printf '%s\n' 'TaijiOS icons are installed; the existing user icon theme could not rebuild its cache.' >&2
fi
printf '%s\n' 'Installed TaijiOS desktop entry and icons.'
