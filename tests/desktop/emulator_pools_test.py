import argparse
import os
import signal
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MIB = 1024 * 1024


def run_guest(emulator, *options, emu_options=None):
    env = os.environ.copy()
    for name in ('DISPLAY', 'WAYLAND_DISPLAY', 'XAUTHORITY',
                 'DBUS_SESSION_BUS_ADDRESS', 'EMU'):
        env.pop(name, None)
    env['HARMONY_DESKTOP_RECOVERY'] = '0'
    if emu_options is not None:
        env['EMU'] = emu_options
    return subprocess.run(
        [str(emulator), *options, '-r', str(ROOT), '/zx/sh.dis', '-c', 'cat /dev/memory'],
        env=env, capture_output=True, text=True, start_new_session=True, timeout=15,
    )


def expect_pools(emulator, expected_main, expected_heap, *options, emu_options=None):
    result = run_guest(emulator, *options, emu_options=emu_options)
    # The hosted shell can terminate its own process group after writing its output.
    assert result.returncode in (0, -signal.SIGKILL), (options, result.stderr)
    pools = {}
    for line in result.stdout.splitlines():
        fields = line.split()
        if len(fields) == 8 and fields[-1] in ('main', 'heap', 'image'):
            pools[fields[-1]] = int(fields[1])
    assert pools == {'main': expected_main, 'heap': expected_heap, 'image': 64 * MIB + 256}, (
        options, emu_options, result.stdout, result.stderr,
    )


def main():
    parser = argparse.ArgumentParser(description='Verify hosted emulator memory pool options')
    parser.add_argument('--emu', type=Path, default=ROOT / 'emu/Linux/o.emu')
    emulator = parser.parse_args().emu.resolve()

    expect_pools(emulator, 128 * MIB, 32 * MIB)
    expect_pools(emulator, 64 * MIB, 32 * MIB, '-p', 'main=64M')
    expect_pools(emulator, 32 * MIB, 32 * MIB, '-p', 'main=32768k')
    expect_pools(emulator, 64 * MIB, 32 * MIB, emu_options='-p main=64m')
    expect_pools(emulator, 32 * MIB, 32 * MIB, '-p', 'main=33554432',
                 emu_options='-p main=64m')
    expect_pools(emulator, 128 * MIB, 64 * MIB, '-p', 'heap=64M')

    for value in ('main', '=64M', 'main=', 'main=-64M', 'main=64MB', 'main=1',
                  'main=2147483648', 'main=2097152K', 'main=2048M', 'unknown=64M'):
        result = run_guest(emulator, '-p', value)
        assert result.returncode == 1 and 'Usage: emu' in result.stderr, (value, result)
    result = run_guest(emulator, emu_options='-p main=64MB')
    assert result.returncode == 1 and 'bad option in EMU environment variable' in result.stderr, result
    print('128 MiB default, pool overrides, and invalid pool options passed')


if __name__ == '__main__':
    main()
