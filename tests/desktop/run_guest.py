#!/usr/bin/env python3
import argparse
from pathlib import Path
import subprocess

root = Path(__file__).resolve().parents[2]
fixtures = root / 'build/desktop-registry'
parser = argparse.ArgumentParser()
parser.add_argument('--images', action='store_true')
parser.add_argument('--large', action='store_true')
parser.add_argument('--budget', action='store_true')
parser.add_argument('--emu', type=Path, default=root / 'emu/Linux/o.emu')
parser.add_argument('--guest-overlay', type=Path, default=fixtures / 'image-overlay')
parser.add_argument('--bundle', type=Path)
args = parser.parse_args()
bundle = args.bundle or fixtures / ('image-test.zx' if args.images or args.budget else 'registry-test.zx')
command = 'zxrun /' + bundle.resolve().relative_to(root).as_posix()
marker = 'TAIJI_DESKTOP_REGISTRY_PNG_OK '
if args.images or args.budget:
    if args.large: command += ' large'
    if args.budget: command += ' spin'
    marker = 'TAIJI_IMAGE_GUEST_OK\n'
if (args.guest_overlay / 'zxrun.dis').exists():
    overlay = '/' + args.guest_overlay.resolve().relative_to(root).as_posix()
    command = f'bind -b {overlay} /dis; bind -b {overlay} /dis/wm; ' + command
result = subprocess.run([str(args.emu.resolve()), '-p', 'main=128M', '-r', str(root),
                         '/dis/sh.dis', '-c', command],
                        capture_output=True, text=True, timeout=90)
print(result.stdout, end='')
if result.stderr:
    print(result.stderr, end='')
assert result.returncode in (0, -9), result.returncode
if args.budget:
    assert 'TAIJI_IMAGE_SPIN_BEGIN\n' in result.stdout
    assert 'stopped after 16000000 steps' in result.stdout+result.stderr
    assert 'TAIJI_IMAGE_SPIN_UNBOUNDED' not in result.stdout
else:
    assert marker in result.stdout, 'guest test did not pass'
    assert result.stdout.endswith('\n0\n') and not result.stderr, 'guest failed'
