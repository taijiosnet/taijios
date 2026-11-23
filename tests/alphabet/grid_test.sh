#!/bin/sh
# The grid typeset's functional test: build its bundle and run it in the
# guest. Run from the TaijiOS root after "(cd appl/alphabet && mk install-zx)".
set -e
cd "$(dirname "$0")/../.."
zi2zx --root . --module-path appl/alphabet --module-path grid=appl/alphabet/grid --module-path appl/cmd --module-path appl/lib \
	--bind-host taijios_io --bind-host taijios_namespace --bind-host taijios_process \
	--bind-host taijios_dial --entry grid_test:main \
	-o build/tests/alphabet/grid_test.zx tests/alphabet/grid_test.zi
env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u DBUS_SESSION_BUS_ADDRESS \
	timeout 60 emu/Linux/o.emu -r "$PWD" /build/tests/alphabet/grid_test.zx
