#!/usr/bin/env python3
"""Check every preinstall bundle exists, is ZX revision 28, and is granted.

`lib/preinstall.list` names the apps TaijiOS ships. The web root builder and
`tools/generate-app-catalog.py --preinstall` both read it, so a row that names
a bundle TaijiOS cannot run would ship a desktop entry the guest refuses.

The bundle check reads the ZX container directly. The header revision is the
one the runtime compares before it loads anything, and a bundle's capabilities
are its `abi` lines in the host-interface section (kind 0x80000003), keyed by
LIR function id. The module each capability lives in is the module of that
function in the kind-2 LIR payload, so this test walks the payload's module and
function tables rather than shelling out to the toolchain.

The granted set is `zxbindings` in `emu/port/zx.c`, section A of
`plans/ecosystem-preinstall.md`. A capability module is granted when it equals
a granted module name or carries an `alias__` or legacy `p<16 hex>_` package
prefix. Every other module is refused, which is what `std/guest_window` and the
Kryon `zx_run` bundles declare today.

Usage: preinstall_test.py [MANIFEST] [--root DIR]

Checks:
  1. every bundle the manifest names as present exists and matches its size
  2. every bundle is ZX format revision 28
  3. every declared capability names a granted module and function
  4. a fixture declaring an ungranted capability fails, as does a wrong
     revision and a missing bundle
"""
import argparse
import shutil
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST = ROOT / 'lib/preinstall.list'

ZX_REVISION = 28
ZX_MAGIC = b'ZX\0\0'
ZX_HEADER_SIZE = 64
ZX_RECORD_SIZE = 32

SECTION_MANIFEST = 1
SECTION_PROGRAM = 2
SECTION_HOST_INTERFACE = 0x80000003

# Copied from zxbindings in emu/port/zx.c, plans/ecosystem-preinstall.md §A.
GRANTED = {
    'taijios_stdin': {'Read', 'Poll'},
    'taijios_files': {'ReadAt'},
    'taijios_draw': {'SampleGuestPointer'},
    'taijios_image': {'Begin', 'Step', 'End', 'Cancel'},
    'taijios_tasks': {'Capture', 'TaskAt', 'PoolAt', 'Terminate', 'SampleNanos', 'Native'},
    'taijios_clock': {'MonotonicMillis', 'UnixMillis', 'Yield'},
    'clock': {'ClockMillisecondsHost'},
    'taijios_args': {'Count', 'At', 'SetFailure'},
    'taijios_process': {'Run', 'Start', 'Poll', 'Wait', 'Kill', 'StartWith', 'Pid', 'NewPgrp'},
    'taijios_native_wm': {
        'StartWindow', 'StartDesktop', 'WaitActivity', 'LaunchWindow', 'Request',
        'Text', 'Snapshot', 'ChromeRegions', 'Payload', 'ApplyCursor', 'Reply',
        'ReplySample', 'Disconnect', 'Dispatch'},
    'taijios_desktop': {
        'BindDesktop', 'Capture', 'LauncherAt', 'WindowAt', 'Launch',
        'WindowAction', 'DesktopAction', 'UnixSeconds', 'TimezoneOffsetSeconds',
        'SetChromeRegions'},
    'taijios_wm': {'Launch', 'Resize', 'SetCursor'},
    'zx_surface': {
        'Open', 'Event', 'Present', 'PresentOpaqueRows', 'PresentOpaqueStrip',
        'PresentRGBStrip', 'Close', 'SetTasked', 'SetTitle', 'PointerMillis'},
    'taijios_panel': {'Snapshot', 'Row', 'Popup', 'Choose', 'Paint', 'Flush'},
    'taijios_namespace': {
        'Pipe', 'Mount', 'Bind', 'Unmount', 'Fork', 'ForkEnv', 'NewNs', 'NoDevs',
        'MountAsync', 'MountDone', 'Export', 'Error'},
    'taijios_keyring': None,
    'taijios_dial': {'Dial', 'Announce', 'Listen'},
    'taijios_io': {
        'Open', 'Create', 'CreateNew', 'Read', 'Write', 'Seek', 'Stat',
        'FstatPacked', 'WstatPacked', 'FdPath', 'Remove', 'Cwd', 'Home', 'Sync',
        'RenameSameDir', 'PollRead', 'Chdir', 'Close', 'Error',
        'StatPacked'},
    'taijios_wm_call': {'Read', 'Reply'},
}
PACKAGE_PREFIX_LENGTH = 18


class BundleError(Exception):
    pass


def granted_module(name):
    """The granted module NAME stands for, or None when it is not granted."""
    if name in GRANTED:
        return name
    if '__' in name:
        leaf = name.rsplit('__', 1)[1]
        if leaf in GRANTED:
            return leaf
    if len(name) > PACKAGE_PREFIX_LENGTH and name[0] == 'p':
        digits = name[1:PACKAGE_PREFIX_LENGTH - 1]
        if len(digits) == 16 and all(c in '0123456789abcdef' for c in digits):
            if name[PACKAGE_PREFIX_LENGTH - 1] == '_':
                leaf = name[PACKAGE_PREFIX_LENGTH:]
                if leaf in GRANTED:
                    return leaf
    return None


def read_u32(data, offset):
    return struct.unpack_from('<I', data, offset)[0]


def read_u64(data, offset):
    return struct.unpack_from('<Q', data, offset)[0]


def sections(data):
    """The container's sections by kind, after checking its own header."""
    if len(data) < ZX_HEADER_SIZE or data[0:4] != ZX_MAGIC:
        raise BundleError('not a ZX program')
    total = read_u64(data, 40)
    if total != len(data):
        raise BundleError(f'header names {total} bytes, file is {len(data)}')
    directory = read_u64(data, 48)
    count = read_u32(data, 32)
    result = {}
    for index in range(count):
        record = directory + index * ZX_RECORD_SIZE
        kind = read_u32(data, record)
        offset = read_u64(data, record + 8)
        length = read_u64(data, record + 16)
        if offset + length > len(data):
            raise BundleError(f'section {kind:#x} runs past the file')
        result[kind] = (offset, length)
    return result


def revision(data):
    if len(data) < 8 or data[0:4] != ZX_MAGIC:
        raise BundleError('not a ZX program')
    return read_u32(data, 4)


def read_string(data, offset):
    length = read_u64(data, offset)
    start = offset + 8
    if start + length > len(data):
        raise BundleError('string runs past the section')
    return data[start:start + length].decode('utf-8', 'replace'), start + length


def read_list(data, offset):
    count = read_u32(data, offset)
    offset += 4
    values = []
    for _ in range(count):
        values.append(struct.unpack_from('<i', data, offset)[0])
        offset += 4
    return values, offset


def walk_program(data, offset, length):
    """(module names, function id -> module index) from the LIR payload."""
    end = offset + length
    if length < 64 or read_u32(data, offset) != 0x52494c5a:
        raise BundleError('program section is not a LIR payload')
    records = read_u32(data, offset + 32)
    directory = read_u64(data, offset + 48)
    cursor = offset + directory + records * 24
    if cursor + 8 > end:
        raise BundleError('program payload is truncated')
    cursor += 8  # program.version and program.entry

    count = read_u32(data, cursor)
    cursor += 4 + count * 4  # initializer function ids

    count = read_u32(data, cursor)
    cursor += 4
    modules = []
    for _ in range(count):
        name, cursor = read_string(data, cursor)
        modules.append(name)

    count = read_u32(data, cursor)
    cursor += 4
    for _ in range(count):
        cursor += 4 + 4 + 4 + 4 + 8 + 4
        _, cursor = read_list(data, cursor)
        _, cursor = read_list(data, cursor)

    count = read_u32(data, cursor)
    cursor += 4
    for _ in range(count):
        cursor += 4 + 8  # type, bits
        _, cursor = read_string(data, cursor)  # data

    count = read_u32(data, cursor)
    cursor += 4
    for _ in range(count):
        cursor += 4  # module
        _, cursor = read_string(data, cursor)  # name
        cursor += 4 + 4 + 4  # type, constant, flags

    count = read_u32(data, cursor)
    cursor += 4
    functions = {}
    for index in range(count):
        module = struct.unpack_from('<i', data, cursor)[0]
        cursor += 4
        _, cursor = read_string(data, cursor)
        _, cursor = read_list(data, cursor)
        cursor += 4 + 4 + 4
        flags = read_u32(data, cursor - 4)
        _, cursor = read_list(data, cursor)
        blocks = read_u32(data, cursor)
        cursor += 4
        for _ in range(blocks):
            _, cursor = read_list(data, cursor)
            instructions = read_u32(data, cursor)
            cursor += 4
            for _ in range(instructions):
                cursor += 4  # op
                cursor += 4  # result
                _, cursor = read_list(data, cursor)
                edges = read_u32(data, cursor)
                cursor += 4
                for _ in range(edges):
                    cursor += 4
                    _, cursor = read_list(data, cursor)
                cursor += 8 + 4 + 4 + 4 + 4
                if flags & 4:
                    cursor += 4  # checked
        cursor += 4 + 4  # entry, origin
        if cursor > end:
            raise BundleError('program payload is truncated')
        functions[index] = module
    return modules, functions


def capabilities(data):
    """(module, function) for every capability the bundle declares."""
    found = sections(data)
    interface = found.get(SECTION_HOST_INTERFACE)
    program = found.get(SECTION_PROGRAM)
    if interface is None:
        return []
    if program is None:
        raise BundleError('host interface without an instruction payload')
    modules, functions = walk_program(data, *program)
    text = data[interface[0]:interface[0] + interface[1]].decode('utf-8', 'replace')
    result = []
    for line in text.splitlines():
        fields = line.split('\t')
        if not fields or fields[0] != 'abi':
            continue
        function = int(fields[1])
        signature = fields[4]
        name = signature.split(' ::')[0].strip()
        module = functions.get(function)
        if module is None or module < 0 or module >= len(modules):
            raise BundleError(f'capability {name} has no module at {function}')
        result.append((modules[module], name))
    return result


def read_manifest(path):
    rows = []
    for line in path.read_text(encoding='utf-8').splitlines():
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        columns = line.split('\t')
        if len(columns) != 9:
            raise SystemExit(f'{path}: expected 9 columns, found {len(columns)}: {line!r}')
        rows.append(dict(zip(
            ('repo', 'bundle', 'ident', 'name', 'icon', 'categories', 'size', 'sha256', 'first_run'),
            columns)))
        if rows[-1]['first_run'] not in ('root', 'lazy'):
            raise SystemExit(f'{path}: first-run is {rows[-1]["first_run"]!r}, expected root or lazy: {line!r}')
    return rows


def check_bundle(path):
    """Problems with one bundle: existence, revision, capabilities."""
    if not path.exists():
        return [f'{path}: bundle does not exist']
    data = path.read_bytes()
    try:
        found = revision(data)
    except BundleError as problem:
        return [f'{path}: {problem}']
    if found != ZX_REVISION:
        return [f'{path}: ZX format {found}, expected {ZX_REVISION}']
    try:
        declared = capabilities(data)
    except BundleError as problem:
        return [f'{path}: {problem}']
    problems = []
    for module, name in declared:
        leaf = granted_module(module)
        if leaf is None:
            problems.append(f'{path}: capability {module}:{name} names an ungranted module')
        elif GRANTED[leaf] is not None and name not in GRANTED[leaf]:
            problems.append(f'{path}: capability {module}:{name} is not granted by {leaf}')
    return problems


def check_manifest(manifest, root):
    problems = []
    rows = read_manifest(manifest)
    checked = 0
    for row in rows:
        path = root / row['bundle'].lstrip('/')
        if not row['size'] and not row['sha256'] and not path.exists():
            continue
        checked += 1
        problems.extend(check_bundle(path))
        if path.exists() and row['size'] and path.stat().st_size != int(row['size']):
            problems.append(f'{path}: {path.stat().st_size} bytes, manifest says {row["size"]}')
    return problems, checked, len(rows)


def fixture(directory):
    """A bundle that declares guest_window, and a revision-27 copy."""
    source = directory / 'probe.zi'
    source.write_text(
        'using Win :: #import "std/guest_window";\n\n'
        'main :: () -> s64 {\n'
        '    if Win.WindowOpenHost("probe", 320, 200, false) { return 0 }\n'
        '    return 1\n'
        '}\n',
        encoding='utf-8')
    import subprocess
    bundle = directory / 'probe.zx'
    subprocess.run(['ziran', 'bundle', '--root', str(directory), '--entry', 'probe:main',
                    '--bind-host', 'guest_window', '-o', str(bundle), str(source)],
                   check=True, stdout=subprocess.DEVNULL)
    return bundle


def check_fixtures(directory):
    """The negative cases: ungranted, wrong revision, missing, through a list."""
    problems = []
    bundle = fixture(directory)
    data = bytearray(bundle.read_bytes())
    declared = capabilities(bytes(data))
    if not any(module == 'guest_window' for module, _ in declared):
        problems.append('fixture: built bundle does not declare guest_window')
    found = check_bundle(bundle)
    if not any('ungranted' in problem for problem in found):
        problems.append('fixture: a guest_window bundle was accepted')

    stale = directory / 'stale.zx'
    struct.pack_into('<I', data, 4, ZX_REVISION - 1)
    stale.write_bytes(bytes(data))
    found = check_bundle(stale)
    if not any('ZX format' in problem for problem in found):
        problems.append('fixture: a revision-27 bundle was accepted')

    found = check_bundle(directory / 'absent.zx')
    if not any('does not exist' in problem for problem in found):
        problems.append('fixture: a missing bundle was accepted')

    # The same ungranted bundle through the manifest walk that runs on the
    # real list, so the failure is not only the single-bundle helper.
    listing = directory / 'fixture.list'
    listing.write_text(f'taijios\t{bundle}\torg.taijiosnet.wm-probe\tProbe\tsystem\tSystem'
                       f'\t{bundle.stat().st_size}\t\tlazy\n', encoding='utf-8')
    found, checked, _ = check_manifest(listing, Path('/'))
    if checked != 1 or not any('ungranted' in problem for problem in found):
        problems.append('fixture: the manifest walk accepted an ungranted bundle')

    listing.write_text(f'taijios\t{bundle}\torg.taijiosnet.wm-probe\tProbe\tsystem\tSystem'
                       f'\t{bundle.stat().st_size}\t\thost\n', encoding='utf-8')
    try:
        read_manifest(listing)
    except SystemExit:
        pass
    else:
        problems.append('fixture: a first-run value other than root or lazy was accepted')
    return problems


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('manifest', nargs='?', type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--no-fixtures', action='store_true',
                        help='skip the negative fixtures, which need ziran')
    args = parser.parse_args()

    problems, checked, rows = check_manifest(args.manifest, args.root)
    if not args.no_fixtures:
        from tempfile import TemporaryDirectory
        if shutil.which('ziran') is None:
            print('preinstall_test: ziran is not on PATH; negative fixtures skipped')
        else:
            with TemporaryDirectory() as directory:
                problems.extend(check_fixtures(Path(directory)))

    if problems:
        for problem in problems:
            print(f'FAIL {problem}')
        print(f'preinstall_test: {len(problems)} failure(s)')
        return 1
    print(f'preinstall_test: {checked} of {rows} bundles exist, are ZX format '
          f'{ZX_REVISION} and declare only granted capabilities')
    return 0


if __name__ == '__main__':
    sys.exit(main())
