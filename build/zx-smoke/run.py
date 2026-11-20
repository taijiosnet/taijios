from pathlib import Path
import subprocess
import sys

root = Path.cwd()
emu = root / (sys.argv[1] if len(sys.argv) > 1 else 'emu/Linux/o.emu')
files = root / 'build/zx-smoke'

def run(command):
    proc = subprocess.run([emu, '-r', root, '/dis/sh.dis', '-c', command],
                          start_new_session=True, capture_output=True, text=True, timeout=25)
    print(repr(proc.stdout), repr(proc.stderr), proc.returncode)
    assert proc.returncode in (0, -9)
    return proc

ok = run("echo TAIJIOS_BOOT_OK; bind -c /build/zx-smoke /chan; cd /chan; "
    "zxrun 'hello app.zx' > guest.stdout; echo ZX_RUN_DONE")
assert ok.stdout == "TAIJIOS_BOOT_OK\nZX_RUN_DONE\n" and ok.stderr == ""
assert (files / 'guest.stdout').read_text() == 'Hello from ZX 42\n4294967338\n'
failed = run('/dis/zxrun.dis /build/zx-smoke/bad.zx >[2] /build/zx-smoke/guest.stderr; echo $status; echo DIS_OK')
assert 'zx\n' in failed.stdout and 'DIS_OK\n' in failed.stdout
assert 'invalid ZX image' in (files / 'guest.stderr').read_text()
pipe = run("zxrun '/build/zx-smoke/hello app.zx' | cat; echo PIPE_OK")
assert pipe.stdout == 'Hello from ZX 42\n4294967338\nPIPE_OK\n' and pipe.stderr == ''
missing = run('zxrun /build/zx-smoke/absent.zx >[2] /build/zx-smoke/missing.stderr; echo $status')
assert missing.stdout == 'zx\n' and missing.stderr == ''
assert 'absent.zx' in (files / 'missing.stderr').read_text()

if '--precision' in sys.argv[2:]:
    precision = run('zxrun /build/zx-smoke/float64.zx; echo $status')
    assert precision.stdout == 'literal true parsed true sum true sqrt(2) 1.4142135623730951\n0\n\n'
    assert not precision.stderr

if '--tee' in sys.argv[2:]:
    from hashlib import file_digest, sha256
    from tempfile import TemporaryDirectory

    assert run('whatis tee /dis/tee.dis').stdout.splitlines() == ['/dis/tee.zx', '/dis/tee.dis']
    with TemporaryDirectory(prefix='tee-', dir=files) as temporary:
        scratch = Path(temporary)
        prefix = f'bind -c /{scratch.relative_to(root)} /chan; cd /chan; '
        data = bytes(range(256)) * 4096
        expected = sha256()
        with (scratch / 'input').open('wb') as input_file:
            for _ in range(16):
                input_file.write(data)
                expected.update(data)
            input_file.write(b'\x00\xff\n')
            expected.update(b'\x00\xff\n')
        (scratch / 'short').write_bytes(b'\x00caf\xc3\xa9\xff\n')
        names = [f'out-{index}' for index in range(65)]
        for tool in ('/dis/tee.dis', 'tee'):
            suffix = 'dis' if tool.endswith('.dis') else 'zx'
            pipeline = run(prefix + f"/dis/cat.dis input | {tool} 'file café' copy | /dis/cat.dis > output; echo $status")
            assert pipeline.stdout == '\n' and not pipeline.stderr
            for path in ('file café', 'copy', 'output'):
                with (scratch / path).open('rb') as output_file:
                    assert file_digest(output_file, 'sha256').digest() == expected.digest(), (tool, path)
            append_to = scratch / '-café'
            append_to.write_bytes(b'prefix\x00')
            (scratch / 'fresh').unlink(missing_ok=True)
            appended = run(prefix + f"{tool} -aa -- '-café' fresh < short > output; echo $status")
            assert appended.stdout == '\n' and not appended.stderr
            short = (scratch / 'short').read_bytes()
            assert append_to.read_bytes() == b'prefix\x00' + short
            assert (scratch / 'fresh').read_bytes() == (scratch / 'output').read_bytes() == short
            many = run(prefix + f"{tool} {' '.join(names)} < short > output; echo $status")
            assert many.stdout == '\n' and not many.stderr
            assert all((scratch / name).read_bytes() == short for name in names)
            plain = run(prefix + f'{tool} < short > output; echo $status')
            assert plain.stdout == '\n' and not plain.stderr and (scratch / 'output').read_bytes() == short
            empty = run(prefix + f'{tool} fresh < /dev/null > output; echo $status')
            assert empty.stdout == '\n' and not empty.stderr and not (scratch / 'fresh').read_bytes()
            for index, (arguments, status, message) in enumerate((
                    ('-q', 'usage', 'Usage: tee [-a] [file ...]'),
                    ("'' < short", 'error', 'tee: cannot open : '),
                    ('fresh missing-dir/file < short', 'error', 'tee: cannot open missing-dir/file: '),
                    ('fresh >[0] writeonly', 'error', 'tee: read error: '),
                    ('fresh < short <[1] short', 'error', 'tee: error writing standard output: '))):
                diagnostic = f'{suffix}-{index}.err'
                attempt = run(prefix + f'{tool} {arguments} >[2] {diagnostic}; echo $status')
                assert attempt.stdout == status + '\n' and not attempt.stderr
                text = (scratch / diagnostic).read_text()
                assert text.startswith(message), text
                if suffix == 'zx':
                    assert text == (scratch / f'dis-{index}.err').read_text(), (arguments, text)
                if 'missing-dir' in arguments or 'writeonly' in arguments:
                    assert (scratch / 'fresh').stat().st_size == 0
    print('ZX tee matched Dis on flags, 65 files, diagnostics, statuses and binary streams beyond 16 MiB')

if '--heap' in sys.argv[2:]:
    heap = run('zxrun -c /build/zx-smoke/arena-reuse.zx; echo $status')
    assert heap.stdout == '64 rounds passed\n\n' and not heap.stderr

if '--runtime' in sys.argv[2:]:
    unbound = run('zxrun /build/zx-smoke/linked.zx >[2] /build/zx-smoke/module.stderr; echo $status')
    assert unbound.stdout == 'zx\n' and unbound.stderr == ''
    assert 'ZX module not found: guest_counter' in (files / 'module.stderr').read_text()
    linked = run('bind -b /build/zx-smoke/modules /dis/lib; '
                 'zxrun /build/zx-smoke/linked.zx | cat; echo GUEST_MODULE_OK')
    assert linked.stdout == 'Guest module received 41\n42\nGUEST_MODULE_OK\n'
    assert linked.stderr == ''

if '--stdin' in sys.argv[2:]:
    (files / 'stdin.in').write_text('first line\nsecond line\n')
    stdin_image = '/build/zx-smoke/stdin.zx'
    redirected = run(f'zxrun {stdin_image} < /build/zx-smoke/stdin.in')
    assert redirected.stdout == 'first line\nsecond line\n0\n' and not redirected.stderr
    piped = run(f'cat /build/zx-smoke/stdin.in | zxrun {stdin_image} | cat')
    assert piped.stdout == redirected.stdout and not piped.stderr
    empty = run(f'zxrun {stdin_image} < /dev/null')
    assert empty.stdout == '0\n' and not empty.stderr
    read_error = run(f'zxrun {stdin_image} >[0] /build/zx-smoke/stdin.writeonly')
    assert read_error.stdout == 'read error\n1\n' and not read_error.stderr

if '--cat' in sys.argv[2:]:
    binary = bytes(range(256)) * 96
    (files / 'cat input.bin').write_bytes(binary)
    (files / 'cat café.txt').write_bytes(b'UTF-8 path\n')
    (files / 'cat empty').write_bytes(b'')
    zx_cat = 'zxrun -c /dis/cat.zx'
    prefix = 'bind -c /build/zx-smoke /chan; cd /chan; '
    for command in ('/dis/cat.dis', zx_cat):
        files_and_stdin = run(prefix + f"{command} 'cat café.txt' 'cat empty' - 'cat input.bin' "
                              "- < 'cat input.bin' > cat.out; echo $status; echo CAT_OK")
        assert files_and_stdin.stdout == '\nCAT_OK\n' and not files_and_stdin.stderr
        assert (files / 'cat.out').read_bytes() == b'UTF-8 path\n' + binary * 2
        piped = run(prefix + f"cat 'cat input.bin' | {command} | cat > cat.pipe; echo $status; echo PIPE_OK")
        assert piped.stdout == '\nPIPE_OK\n' and not piped.stderr
        assert (files / 'cat.pipe').read_bytes() == binary

    for args, legacy_status, expected in (
            ("'cat missing' 'cat input.bin'", 'bad open', 'cat: cannot open cat missing: '),
            ("''", 'bad open', 'cat: cannot open : '),
            ('>[0] cat.writeonly', 'read error', 'cat: error reading <stdin>: '),
            ("'cat input.bin' <[1] 'cat empty'", 'write error', 'cat: write error: ')):
        legacy = run(prefix + f'/dis/cat.dis {args} >[2] cat.dis.err; echo $status')
        converted = run(prefix + f'{zx_cat} {args} >[2] cat.zx.err; echo $status')
        assert legacy.stdout == legacy_status + '\n' and not legacy.stderr
        assert converted.stdout == '1\n' and not converted.stderr
        legacy_error = (files / 'cat.dis.err').read_text()
        assert legacy_error.startswith(expected)
        assert (files / 'cat.zx.err').read_text() == legacy_error


if '--stock-zx' in sys.argv[2:]:
    from shutil import copyfile
    from tempfile import TemporaryDirectory

    lookup = run('whatis cat echo basename cleanname ls /dis/cat.dis /dis/cat.zx')
    assert lookup.stdout.splitlines() == ['/dis/cat.zx', '/dis/echo.zx', '/dis/basename.zx',
                                          '/dis/cleanname.zx', '/dis/ls.dis', '/dis/cat.dis',
                                          '/dis/cat.zx']
    assert not lookup.stderr

    result = run("echo -n 'café' '' x | cat | /dis/cat.dis; echo; "
                 "basename 'é.tar' .tar; cleanname -d /a b/../c")
    assert result.stdout == 'café  x\né\n/a/c\n' and not result.stderr

    result = run("cat /absent-zx-smoke >[2] /dev/null; echo $status; "
                 "cat >[0] /build/zx-smoke/cat.writeonly >[2] /dev/null; echo $status; "
                 "echo hello <[1] /dev/null >[2] /dev/null; echo $status; "
                 "basename -x a >[2] /dev/null; echo $status; "
                 "cleanname -d >[2] /dev/null; echo $status; "
                 "zxrun -c /dis/basename.zx -x a >[2] /dev/null; echo $status")
    assert result.stdout == 'bad open\nread error\nwrite error\nusage\nusage\n1\n' and not result.stderr

    with TemporaryDirectory(dir=files, prefix='stock-') as directory:
        directory = Path(directory)
        guest = '/' + str(directory.relative_to(root))
        copyfile(root / 'dis' / 'echo.dis', directory / 'echo.dis')
        (directory / 'echo.zx').write_bytes(b'not a ZX bundle\n')
        prefix = f'path=({guest} /dis); '
        fallback = run(prefix + 'whatis echo; echo fallback')
        assert fallback.stdout == f'{guest}/echo.dis\nfallback\n' and not fallback.stderr
        (directory / 'echo.zx').chmod(0o755)
        rejected = run(prefix + 'whatis echo; echo rejected >[2] /dev/null; /dis/echo.dis $status')
        assert rejected.stdout == f'{guest}/echo.zx\nzx\n', rejected
        (directory / 'echo.zx').unlink()
        (directory / 'echo.zx').mkdir()
        directory_fallback = run(prefix + 'whatis echo; echo fallback')
        assert directory_fallback.stdout == f'{guest}/echo.dis\nfallback\n' and not directory_fallback.stderr

        copyfile(root / 'dis' / 'echo.zx', directory / 'echo data.zx')
        (directory / 'echo data.zx').chmod(0o755)
        direct = run(f"cd {guest}; whatis './echo data.zx'; './echo data.zx' 'direct €'")
        assert direct.stdout == './echo data.zx\ndirect €\n' and not direct.stderr
    builtin = run('load /dis/sh/echo.dis; whatis echo; echo builtin')
    assert builtin.stdout == 'load /dis/sh/echo.dis; echo\nbuiltin\n' and not builtin.stderr
    print('Stock ZX: lookup, UTF-8 argv, pipeline, named errors, path precedence and Dis fallback')

if '--file-commands' in sys.argv[2:]:
    from hashlib import file_digest
    import os
    from stat import S_IMODE
    from tempfile import TemporaryDirectory

    def digest(path):
        with path.open('rb') as stream:
            return file_digest(stream, 'sha256').digest()

    resolved = run('whatis cp; whatis test')
    assert resolved.stdout == '/dis/cp.zx\n/dis/test.zx\n' and not resolved.stderr
    with TemporaryDirectory(dir=files, prefix='file-commands-') as directory:
        directory = Path(directory)
        src = directory / 'src'
        (src / 'sub').mkdir(parents=True)
        data = src / 'sub' / 'data'
        with data.open('wb') as stream:
            block = bytes(range(256)) * 4096
            for _ in range(17):
                stream.write(block)
            stream.write(b'\0\xff!')
        data.chmod(0o640)
        old = 1000000000
        os.utime(data, (old, old))
        (src / 'empty').touch()
        (src / 'executable').write_bytes(b'x')
        (src / 'executable').chmod(0o755)
        (src / 'sub').chmod(0o750)
        (directory / '-café').write_bytes(b'name')
        os.link(data, directory / 'alias')

        guest = '/' + str(directory.relative_to(root))
        prefix = f'bind -c {guest} /chan; cd /chan; '
        copy_cases = (
            ('src/empty result/empty', ''),
            ("-- '-café' result/name", ''),
            ('src/empty src/executable result', ''),
            ('-rx src result', ''),
            ('-ux src/sub/data result/data', ''),
            ('-g src/empty result/group', ''),
            ('-r src result', 'error'),
            ('src/empty src/empty', 'error'),
            ('src/sub/data alias', 'error'),
            ('src result/no', 'error'),
            ('missing result/no', 'error'),
            ('src/empty src/executable nowhere', 'error'),
            ('-q', 'usage'),
        )
        test_cases = (
            ('', 'usage'), ("-z ''", ''), ("-n ''", 'false'),
            ("'café' '=' 'café'", ''), ("'café' '!=' 'café'", 'false'),
            ('010 -eq 10', ''), ('9 -ge 10', 'false'),
            ('2147483648 -eq 2147483647', ''), ('1 -lt -1', 'bad syntax'),
            ("'(' -f src/empty -a ! -d src/empty ')'", ''),
            ('-e missing -a -f', 'false'), ('-d src -o -f', ''),
            ("'(' -d src", 'bad syntax'), ('-f', 'bad syntax'),
            ('-f src/sub/data', ''), ('-d src', ''), ('-e missing', 'false'),
            ('-s src/empty', 'false'), ('-s src/sub/data', ''),
            ('-r src/sub/data', ''), ('-w src/empty', ''),
            ('-x src/executable', ''), ('-x src/sub/data', 'false'),
            ('-A src/empty', 'false'), ('-L src/empty', 'false'), ('-T src/empty', 'false'),
            ('src/sub/data -ot src/empty', ''), ('src/empty -nt src/sub/data', ''),
            ('src/sub/data -older 1d', ''), ('src/sub/data -older 1q', 'bad syntax'),
            ('-t', ''), ('-t 999', 'false'), ('-t 7 >[7=1]', ''),
        )
        outputs = {}
        for suffix in ('dis', 'zx'):
            (directory / 'result').mkdir()
            for name, cases in (('cp', copy_cases), ('test', test_cases)):
                tool = f'/dis/{name}.dis' if suffix == 'dis' else name
                for arguments, status in cases:
                    result = run(prefix + f'{tool} {arguments} > output >[2] diagnostic; echo $status')
                    output = (directory / 'output').read_bytes()
                    diagnostic = (directory / 'diagnostic').read_bytes()
                    if name == 'test' and arguments == '-t':
                        # Standard output is redirected by the test harness.
                        status = 'false'
                    assert result.stdout == status + '\n' and not result.stderr, (tool, arguments)
                    key = name, arguments
                    if suffix == 'dis':
                        outputs[key] = output, diagnostic
                    else:
                        assert outputs[key] == (output, diagnostic), (tool, arguments, diagnostic)
            (directory / 'result').rename(directory / suffix)

        def tree(path):
            entries = {}
            for entry in path.rglob('*'):
                info = entry.stat()
                entries[entry.relative_to(path)] = (
                    S_IMODE(info.st_mode), info.st_uid, info.st_gid,
                    None if entry.is_dir() else (info.st_size, digest(entry)))
            return entries

        legacy, zx = directory / 'dis', directory / 'zx'
        assert tree(legacy) == tree(zx)
        assert digest(zx / 'data') == digest(zx / 'src/sub/data') == digest(data)
        assert (zx / 'empty').stat().st_size == 0 and (zx / 'name').read_bytes() == b'name'
        for name in ('data', 'src/sub/data'):
            assert (legacy / name).stat().st_mtime == (zx / name).stat().st_mtime == old
        assert S_IMODE((zx / 'src/sub').stat().st_mode) == 0o750
        assert S_IMODE((zx / 'data').stat().st_mode) == 0o640
    print(f'ZX cp and test matched Dis on {len(copy_cases) + len(test_cases)} file and expression cases')

if '--streams' in sys.argv[2:]:
    lookup = run('whatis wc uniq tr')
    assert lookup.stdout == '/dis/wc.zx\n/dis/uniq.zx\n/dis/tr.zx\n' and not lookup.stderr
    plain = 'a\na\n\nκ\nκ\nend'.encode()
    malformed = b'a\x00b\na\x00b\n\xff\n\xff\n\xe2\x82'
    boundary = b'x' * 8191 + '€κ☕🫖'.encode() + b'\n'
    (files / 'stream-other').write_bytes(b'one\t two\n')
    cases = [
        ('wc', '', b''),
        ('wc', '-lwc', boundary),
        ('wc', '-lwcbe', bytes(range(256)) * 120),
        ('wc', 'stream-other stream-input', boundary),
        ('wc', '-q', plain),
        ('wc', 'stream-missing stream-other', plain),
        ('wc', '', b'word\n' * 3355444),
        ('uniq', '-u', plain),
        ('uniq', '-d', plain),
        ('uniq', '-udc -- stream-input', plain),
        ('uniq', '-c', malformed),
        ('uniq', '-c', (boundary * 2 + b'y')),
        ('uniq', '-q', b''),
        ('uniq', 'stream-missing', b''),
        ('tr', 'a-z A-Z', boundary),
        ('tr', '-s a-c z', b'abczz\naabb\n'),
        ('tr', '-ds xy z', b'zzxzyyyyxxzz\n'),
        ('tr', '-c abc d', 'xyzabc☕🫖\n'.encode()),
        ('tr', "'€κ☕🫖' 'é𐀀'", boundary),
        ('tr', "'\\101-\\x43' '!?X'", b'ABCD'),
        ('tr', 'aa xy', b'aa\n'),
        ('tr', 'z-a y', b'd'),
        ('tr', "-d '\\777'", b'd'),
        ('tr', "-d ''", malformed),
        ('tr', "-c '\\000' ''", b'a\x00b\n'),
    ]
    for name, args, payload in cases:
        (files / 'stream-input').write_bytes(payload)
        # The prebuilt uniq.dis can predate the -c option in uniq.b.
        legacy = '/appl/cmd/uniq.dis' if name == 'uniq' else f'/dis/{name}.dis'
        results = []
        for command in (legacy, name):
            result = run(f'cd /build/zx-smoke; {command} {args} < stream-input '
                         '> stream-out >[2] stream-err; echo $status')
            assert not result.stderr
            results.append((result.stdout, (files / 'stream-out').read_bytes(),
                            (files / 'stream-err').read_bytes()))
        assert results[0] == results[1], (name, args, len(payload),
                                         [(status, output[:100], error) for status, output, error in results])
    print(f'Stream ZX: {len(cases)} Dis parity cases, including UTF-8, errors and 16 MiB stdin')

if '--utilities' in sys.argv[2:]:
    cases = [
        ('echo', '', '\n'),
        ('echo', "-n 'café' '' x", 'café  x'),
        ('echo', '-- -n hé', '-n hé\n'),
        ('echo', "-n -- 'a b'", '-- a b'),
        ('basename', '/a/b/', '\n'),
        ('basename', '-ddd /a//', '/a/\n'),
        ('basename', 'é.tar .tar', 'é\n'),
        ('basename', 'foo foo', '\n'),
        ('basename', '-- -n', '-n\n'),
        ('basename', '-d x extra', None),
        ('cleanname', "-d/pwd a/../b / '#é/ref/..' '../x' '' /../../ '#/' '#/a/..'",
         '/pwd/b\n/\n#é\n/x\n.\n/\n#/\n#/a\n'),
        ('cleanname', "a/../../b //a///b/.././ '#x/user/../../..' '#é/../a' '#/../x'",
         '../b\n/a\n#x\n#é/a\n#/../x\n'),
        ('cleanname', '-d -- name', '--/name\n'),
        ('cleanname', '-d', None),
    ]
    usage = {
        'basename': b'usage: basename [-d] string [suffix]\n',
        'cleanname': b'usage: cleanname [-d pwd] name ...\n',
    }
    for name, operands, expected in cases:
        for command, usage_status in ((f'/dis/{name}.dis', 'usage'),
                                      (f'zxrun -c /dis/{name}.zx', '1')):
            result = run(f'{command} {operands} > /build/zx-smoke/util.out '
                         '>[2] /build/zx-smoke/util.err; echo $status; echo UTILITY_OK')
            status = usage_status if expected is None else ''
            assert result.stdout == status + '\nUTILITY_OK\n' and not result.stderr
            actual = (files / 'util.out').read_bytes(), (files / 'util.err').read_bytes()
            wanted = (b'', usage[name]) if expected is None else (expected.encode(), b'')
            assert actual == wanted, (command, operands, actual, wanted)


if '--guest-io' in sys.argv[2:]:
    from tempfile import TemporaryDirectory

    with TemporaryDirectory(dir=files, prefix='filesystem-') as directory:
        directory = Path(directory)
        guest = '/' + str(directory.relative_to(root))
        (directory / 'lifecycle.txt').write_bytes(b'long file to truncate')
        result = run(f'bind -c {guest} /chan; cd /chan; '
                     'zxrun -c /build/zx-smoke/filesystem.zx > io.out >[2] io.err; '
                     'echo $status; echo GUEST_IO_DONE')
        assert result.stdout == '7\nGUEST_IO_DONE\n' and not result.stderr
        assert (directory / 'lifecycle.txt').read_bytes() == b'alpha'
        assert (directory / 'new lifecycle.txt').read_bytes() == b'new'
        assert (directory / 'new lifecycle.txt').stat().st_mode & 0o777 == 0o600
        assert (directory / 'io.out').read_bytes() == b'guest stdout\n'
        assert (directory / 'io.err').read_bytes() == b'guest stderr\n'
        print('ZX guest I/O: create, truncate, stat, s64 seek, independent handles, streams and status')


def graphics():
    import errno
    import io
    import os
    import select
    import signal
    import time
    from collections import deque
    from tempfile import TemporaryDirectory
    from PIL import Image, ImageChops

    env = {k: v for k, v in os.environ.items() if k not in (
        'DISPLAY', 'WAYLAND_DISPLAY', 'XAUTHORITY', 'DBUS_SESSION_BUS_ADDRESS',
        'XDG_RUNTIME_DIR', 'SESSION_MANAGER')}
    env['HARMONY_DESKTOP_RECOVERY'] = '0'
    reader, writer = os.pipe()
    xvfb = subprocess.Popen(['Xvfb', '-displayfd', str(writer), '-screen', '0',
                            '1024x768x24', '-nolisten', 'tcp', '-noreset'],
                           pass_fds=(writer,), env=env)
    os.close(writer)

    def command(*args, **kwargs):
        return subprocess.run(args, env=env, timeout=4, **kwargs)

    def until(probe, description, timeout=10):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            result = probe()
            if result:
                return result
            time.sleep(0.05)
        raise AssertionError(description)

    def launch(app, *args, arena='256M'):
        return subprocess.Popen([emu, '-p', f'main={arena}', '-r', root, '-g', '800x600',
                                 'wm/wm', app, *args], env=env,
                                start_new_session=True, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)

    def owned_window():
        found = command('xdotool', 'search', '--onlyvisible', '--name', '^inferno$',
                        capture_output=True, text=True).stdout.splitlines()
        return found[0] if len(found) == 1 else None

    def capture(window):
        pixels = command('import', '-window', window, 'png:-',
                         check=True, capture_output=True).stdout
        return Image.open(io.BytesIO(pixels)).convert('RGB')

    def surface(window):
        img = capture(window)
        delta = ImageChops.difference(img, Image.new('RGB', img.size, (248, 250, 252)))
        red, green, blue = delta.split()
        mask = ImageChops.lighter(ImageChops.lighter(red, green), blue)
        box = mask.point(lambda v: 255 if v == 0 else 0).getbbox()
        return (img, box) if box else None

    def click(window, x, y):
        command('xdotool', 'mousemove', '--sync', '--window', window, str(x), str(y),
                'mousedown', '1', 'sleep', '0.15', 'mouseup', '1', check=True)

    def close(window, box):
        click(window, box[2] - 7, box[1] - 10)
        until(lambda: surface(window) is None, 'guest window did not close')

    def output(proc):
        ready, _, _ = select.select([proc.stdout, proc.stderr], [], [], 0)
        for fd in ready:
            block = os.read(fd.fileno(), 4096)
            if block:
                yield fd is proc.stderr, block

    def stop(proc):
        if proc.poll() is None:
            os.killpg(proc.pid, signal.SIGKILL)
        proc.wait(timeout=5)
        proc.stdout.close()
        proc.stderr.close()

    def windowed_stdin():
        proc = launch('sh', '-c', f'zxrun -w {stdin_image} < /build/zx-smoke/stdin.in')
        transcript = bytearray()

        def read():
            for error, block in output(proc):
                assert not error, block
                transcript.extend(block)
            return b'first line\nsecond line\n0\n' in transcript

        try:
            until(read, 'windowed ZX did not read guest stdin')
            print('ZX stdin: windowed runner honored guest fd 0 redirection')
        finally:
            stop(proc)

    def windowed_pipe(cancel):
        with TemporaryDirectory(dir=files, prefix='windowio-') as directory:
            setup = Path(directory)
            feed = setup / 'input'
            os.mkfifo(feed)
            guest = '/' + str(setup.relative_to(root))
            # Use a real guest pipe and toolbar in this emulator's namespace.
            (setup / 'wmsetup').write_text(
                f"{{cat {guest}/input | {{zxrun -c -p -w /build/zx-smoke/windowio.zx "
                "mode 'café marker'; echo WINDOWIO_STATUS $status; ps; echo WINDOWIO_DONE}} &\n")
            proc = subprocess.Popen([emu, '-r', root, '-g', '800x600', '/dis/sh.dis', '-c',
                                     f'bind -b {guest} /lib; wm/wm'], env=env,
                                    stdin=subprocess.DEVNULL, start_new_session=True,
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            transcript = bytearray()

            def observed(marker):
                for error, data in output(proc):
                    assert not error, data
                    transcript.extend(data)
                assert len(transcript) < 8192, 'unexpected pipe test output'
                return marker in transcript

            def input_writer():
                try:
                    return (os.open(feed, os.O_WRONLY | os.O_NONBLOCK),)
                except OSError as err:
                    if err.errno != errno.ENXIO:
                        raise

            try:
                window = until(owned_window, 'guest pipe emulator did not map')
                (writer,) = until(input_writer, 'guest pipe producer did not open its input')
                with os.fdopen(writer, 'wb', buffering=0) as stream:
                    until(lambda: observed(b'windowio pending\n'), 'ZX did not observe a pending pipe read')
                    _, box = until(lambda: surface(window), 'ZX pipe test did not draw')
                    command('xdotool', 'mousemove', '700', '400', check=True)
                    click(window, box[0] + 30, box[1] + 30)
                    command('xdotool', 'key', '--window', window, 'a', check=True)
                    until(lambda: observed(b'windowio key 65\n'), 'key input stalled behind guest stdin')
                    if cancel:
                        close(window, box)
                    else:
                        command('xdotool', 'key', '--window', window, 'h', check=True)
                        until(lambda: observed(b'windowio visibility 1\n'), 'ZX did not receive task event')
                        until(lambda: surface(window) is None, 'tasked ZX window is still visible')
                        assert stream.write(b'abcde') == 5
                        until(lambda: observed(b'windowio bytes abc\n'), 'ZX did not read a short slice')
                        until(lambda: observed(b'windowio bytes de\n'), 'ZX discarded unread bytes')
                        until(lambda: observed(b'windowio visibility 0\n'), 'ZX did not receive restore event')
                        until(lambda: surface(window), 'restored ZX window did not draw')
                        stream.close()
                    until(lambda: observed(b'WINDOWIO_DONE\n'), 'ZX did not return to its guest shell')
                    status = 8 if cancel else 7
                    assert f'WINDOWIO_STATUS {status}\n'.encode() in transcript, transcript
                    processes = transcript.split(f'WINDOWIO_STATUS {status}\n'.encode(), 1)[1]
                    assert b'zxrun' not in processes, processes
            except AssertionError:
                print('ZX guest pipe transcript:', repr(transcript))
                raise
            finally:
                stop(proc)

    def fuel():
        proc = launch('zxrun', '-w', '/build/zx-smoke/budget.zx')
        stdout, stderr = bytearray(), bytearray()

        def exhausted():
            for error, block in output(proc):
                (stderr if error else stdout).extend(block)
            return b'stopped after' in stderr or b'zxrun:' in stdout or b'zxrun:' in stderr

        try:
            until(exhausted, 'ZX budget test did not stop', timeout=40)
            assert b'renewed 4 ' in stdout, (stdout, stderr)
            assert b'polled 1 ' in stdout and b'polled 4 ' not in stdout, stdout
            assert b'stopped after' in stderr, stderr
            print('ZX budget: four waited frames completed, empty polls exhausted fuel')
        except AssertionError:
            print('ZX budget output:', repr(stdout), repr(stderr))
            raise
        finally:
            stop(proc)

    def keyevents():
        proc = launch('zxrun', '-w', '/build/zx-smoke/keyevents.zx')
        transcript = bytearray()

        def read():
            for error, block in output(proc):
                assert not error, block.decode('utf-8', 'replace')
                transcript.extend(block)
            return transcript.decode('utf-8', 'replace').splitlines()

        def expect_keys(expected):
            keys = [line for line in read() if line.startswith('key ')]
            return keys[-len(expected):] == expected

        try:
            window = until(owned_window, 'emulator did not map its X window')
            _, box = until(lambda: surface(window), 'ZX key event canvas missing')
            command('xdotool', 'windowfocus', window, check=True)
            for name, key, bit in [('Shift_L', 340, 1), ('Control_L', 341, 2), ('Alt_L', 342, 4)]:
                command('xdotool', 'keydown', name, 'keydown', 'a', 'keyup', 'a',
                        'keyup', name, check=True)
                expected = [f'key 7 {key} {bit}', f'key 7 65 {bit}',
                            f'key 8 65 {bit}', f'key 8 {key} 0']

                until(lambda: expect_keys(expected), f'{name} press or release did not reach the ZX surface')
            command('xdotool', 'keydown', 'Shift_L', 'keydown', 'Shift_R', 'keyup', 'Shift_L',
                    'keyup', 'Shift_R', check=True)
            until(lambda: expect_keys(['key 7 340 1', 'key 7 344 1', 'key 8 340 1', 'key 8 344 0']),
                  'Shift modifier changed before the last Shift key was released')
            until(lambda: 'text A' in read(), 'shifted text did not reach the ZX surface')
            close(window, box)
            until(lambda: '0' in read(), 'ZX key event fixture did not close cleanly')
            print('ZX X11 keys: physical press and release with Shift, Control and Alt masks')
        except AssertionError:
            print('ZX key event output:', read())
            raise
        finally:
            stop(proc)

    def kryon():
        proc = launch('zxrun', '-w', '/build/zx-smoke/hosted_surface.zx')
        transcript = deque(maxlen=80)
        partial = b''

        def seen(want):
            nonlocal partial
            for error, block in output(proc):
                assert not error, block.decode('utf-8', 'replace')
                *lines, partial = (partial + block).split(b'\n')
                transcript.extend(line.decode('utf-8') for line in lines)
            return any(want(line) for line in transcript)

        try:
            window = until(owned_window, 'emulator did not map its X window')
            before, box = until(lambda: surface(window), 'Kryon frame missing')
            x, y, right, bottom = box
            assert (right - x, bottom - y) == (240, 144), box
            command('xdotool', 'windowfocus', window, check=True)
            click(window, x + 40, y + 55)
            until(lambda: seen(lambda s: s == 'click 1'), 'mouse click did not reach Kryon')
            label = (x, y, right, y + 35)
            until(lambda: ImageChops.difference(before.crop(label),
                                                capture(window).crop(label)).getbbox(),
                  'Kryon click did not redraw the counter')
            click(window, x + 40, y + 99)
            command('xdotool', 'key', 'eacute', check=True)
            until(lambda: seen(lambda s: s == 'text é'), 'Unicode text did not reach Kryon')
            command('xdotool', 'key', 'x', check=True)
            until(lambda: seen(lambda s: s == 'text éx'), 'ASCII text did not reach Kryon')
            command('xdotool', 'key', 'BackSpace', check=True)
            until(lambda: seen(lambda s: s == 'text é') and transcript.count('text é') == 2,
                  'Backspace did not reach Kryon')
            click(window, right - 22, y - 9)
            command('xdotool', 'mousemove', '--window', window, str(right - 3), str(bottom - 4),
                    'sleep', '0.15', 'mousedown', '1', 'sleep', '0.15', 'mousemove', '--window',
                    window, str(right + 60), str(bottom + 48), 'sleep', '0.15', 'mouseup', '1',
                    check=True)
            until(lambda: seen(lambda s: s.startswith('surface ') and s != 'surface 240 x 144'),
                  'resize did not reach Kryon')
            def resized_surface():
                current = surface(window)
                return current[1] if current and current[1] != box else None

            resized = until(resized_surface, 'resized frame missing')
            close(window, resized)
            until(lambda: seen(lambda s: s == '0'), 'Kryon did not return success on close')
            print('Kryon:', ', '.join(transcript))
        except AssertionError:
            print('Kryon transcript:', ', '.join(transcript))
            raise
        finally:
            for error, block in output(proc):
                print('Kryon stderr:' if error else 'Kryon stdout:', block.decode('utf-8', 'replace').strip())
            stop(proc)

    def stopwatch():
        proc = launch('wm/stopwatch', '-zx', arena='64M')
        status = bytearray()

        def returned():
            for error, block in output(proc):
                assert not error, block.decode('utf-8', 'replace')
                status.extend(block)
            return status == b'0\n'

        try:
            window = until(owned_window, 'emulator did not map its X window')
            before, box = until(lambda: surface(window), 'ZX Stopwatch frame missing')
            x, y, right, _ = box
            counter = (x + 10, y + 53, right - 10, y + 85)
            lap = (x + 93, y + 94, right - 10, y + 124)
            initial = before.crop(counter)
            click(window, x + 45, y + 27)
            until(lambda: ImageChops.difference(initial, capture(window).crop(counter)).getbbox(),
                  'Stopwatch did not tick while idle', timeout=6)
            click(window, x + 135, y + 27)
            click(window, x + 45, y + 106)
            until(lambda: ImageChops.difference(before.crop(lap), capture(window).crop(lap)).getbbox(),
                  'Stopwatch lap display did not update')
            stopped = capture(window).crop(counter)
            time.sleep(1.2)
            assert not ImageChops.difference(stopped, capture(window).crop(counter)).getbbox()
            click(window, x + 224, y + 27)
            until(lambda: not ImageChops.difference(initial, capture(window).crop(counter)).getbbox(),
                  'Stopwatch did not reset')
            close(window, box)
            until(returned, 'Stopwatch did not return success on close')
            print('Stopwatch ZX: start, idle tick, stop, lap, reset, close')
        finally:
            for error, block in output(proc):
                print('Stopwatch stderr:' if error else 'Stopwatch stdout:', block.decode('utf-8', 'replace').strip())
            stop(proc)

    def legacy_stopwatch():
        proc = launch('wm/stopwatch')
        try:
            window = until(owned_window, 'emulator did not map its X window')

            def legacy_frame():
                img = capture(window)
                # Exclude the emulator's outer border from the guest window bounds.
                margin = 8
                interior = img.crop((margin, margin, img.width - margin, img.height - margin))
                background = Image.new('RGB', interior.size, (119, 119, 119))
                box = ImageChops.difference(interior, background).getbbox()
                return tuple(edge + margin for edge in box) if box else None

            def legacy_window():
                box = legacy_frame()
                if box and 70 < box[2] - box[0] < 300 and 70 < box[3] - box[1] < 250:
                    return box
                return None

            box = until(legacy_window, 'Dis Stopwatch frame missing')
            click(window, box[2] - 8, box[1] + 10)
            until(lambda: legacy_frame() is None, 'Dis Stopwatch did not close')
            print('Stopwatch Dis: drew and closed via the original entry point')
        finally:
            stop(proc)

    try:
        ready, _, _ = select.select([reader], [], [], 6)
        display = os.read(reader, 32).strip() if ready else b''
        assert display.isdigit(), 'private Xvfb startup failed'
        env['DISPLAY'] = ':' + display.decode('ascii')
        keyevents()
        kryon()
        stopwatch()
        legacy_stopwatch()
        if '--runtime' in sys.argv[2:]:
            fuel()
        if '--stdin' in sys.argv[2:]:
            windowed_stdin()
        if '--guest-io' in sys.argv[2:]:
            windowed_pipe(cancel=False)
            windowed_pipe(cancel=True)
            print('ZX window I/O: UTF-8 argv, live guest pipe, keys, task/restore, EOF and cancellation')
    finally:
        os.close(reader)
        xvfb.terminate()
        xvfb.wait(timeout=5)


if '--graphics' in sys.argv[2:]:
    graphics()
