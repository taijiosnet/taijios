#!/usr/bin/env python3
"""Check the ZX Sam protocol/rasp rules and live #C (/cmd/clone) sam -R session."""
import os
import time

from wm_app_test import BUILD, Guest, arguments, private_display, run_model, until

GREY = (221, 221, 221)
WIN_W, WIN_H = 720, 540

MOCK_HOST = r'''#!/usr/bin/env python3
import struct
import sys

trace_path = sys.argv[1]
inp = sys.stdin.buffer
out = sys.stdout.buffer

def log(line):
    with open(trace_path, 'a', encoding='utf-8') as f:
        f.write(line + '\n')
        f.flush()

def read_exact(n):
    buf = bytearray()
    while len(buf) < n:
        chunk = inp.read(n - len(buf))
        if not chunk:
            return None
        buf.extend(chunk)
    return bytes(buf)

def send(mtype, payload=b''):
    out.write(struct.pack('<BH', mtype, len(payload)) + payload)
    out.flush()

# Message IDs matching samstub.m
Tversion, Tstartcmdfile, Tcheck, Trequest = 0, 1, 2, 3
Tstartfile, Tworkfile, Ttype = 5, 6, 7
Twrite, Tclose, Texit = 12, 13, 21

Hversion, Hbindname, Hcurrent, Hnewname, Hmovname = 0, 1, 2, 3, 4
Hgrow, Hcheck0, Hcheck, Hunlock, Hdata = 5, 6, 7, 8, 9
Hclean, Hdirty, Hexit = 15, 16, 24

doc = b'Hello Sam!\n\n'
while True:
    hdr = read_exact(3)
    if hdr is None:
        break
    mtype, mcount = struct.unpack('<BH', hdr)
    data = read_exact(mcount) if mcount else b''
    if data is None:
        break
    if mtype == Tversion:
        ver = struct.unpack('<H', data[:2])[0]
        log(f'Tversion:{ver}')
        send(Hversion, struct.pack('<H', 0))
    elif mtype == Tstartcmdfile:
        tag = struct.unpack('<Q', data[:8])[0]
        log(f'Tstartcmdfile:{tag}')
        send(Hnewname, struct.pack('<H', 0))
        send(Hbindname, struct.pack('<HQ', 0, tag))
        send(Hmovname, struct.pack('<H', 0) + b'~~sam~~')
        send(Hnewname, struct.pack('<H', 1))
        send(Hmovname, struct.pack('<H', 1) + b'notes.txt')
        send(Hcurrent, struct.pack('<H', 1))
        send(Hunlock)
    elif mtype == Tstartfile:
        tag = struct.unpack('<Q', data[:8])[0]
        log(f'Tstartfile:{tag}')
        send(Hgrow, struct.pack('<HII', 1, 0, len(doc)))
        send(Hcheck0, struct.pack('<H', 1))
    elif mtype == Tcheck:
        m = struct.unpack('<H', data[:2])[0]
        log(f'Tcheck:{m}')
        send(Hcheck, struct.pack('<H', m))
    elif mtype == Trequest:
        m, pos, cnt = struct.unpack('<HIH', data[:8])
        log(f'Trequest:{m}:{pos}:{cnt}')
        send(Hdata, struct.pack('<HI', m, pos) + doc[pos:pos + cnt])
        send(Hunlock)
    elif mtype == Ttype:
        m, pos = struct.unpack('<HI', data[:6])
        txt = data[6:].decode('utf-8', errors='replace')
        log(f'Ttype:{m}:{pos}:{txt!r}')
        send(Hdirty, struct.pack('<H', m))
        send(Hunlock)
    elif mtype == Twrite:
        m = struct.unpack('<H', data[:2])[0]
        log(f'Twrite:{m}')
        send(Hclean, struct.pack('<H', m))
        send(Hunlock)
    elif mtype == Tworkfile:
        m = struct.unpack('<H', data[:2])[0]
        log(f'Tworkfile:{m}')
    elif mtype == Texit:
        log('Texit')
        send(Hexit)
        break
'''


def check_model(env):
    message = run_model('sam', 'sam_states.expected', env)
    assert message == 'Sam matched wire protocol, rasp sections, sorted menus, zerox, dirty/modified titles, and typing rules', message
    print('Sam model matched wire protocol, rasp sections, sorted menus, zerox, dirty/modified titles, and typing rules')


def window_origin(image):
    pixels = image.load()
    for y in range(10, image.height - WIN_H + 1):
        for x in range(0, image.width - WIN_W + 1):
            if pixels[x, y] == GREY and pixels[x + WIN_W - 1, y] == GREY \
                    and pixels[x, y + WIN_H - 1] == GREY and pixels[x + WIN_W - 1, y + WIN_H - 1] == GREY:
                return x, y
    return None


def check_window(env, args):
    BUILD.mkdir(parents=True, exist_ok=True)
    host_py = BUILD / 'mock_sam_host.py'
    trace = BUILD / 'sam_trace.log'
    host_py.write_text(MOCK_HOST, encoding='utf-8')
    host_py.chmod(0o755)
    trace.unlink(missing_ok=True)
    try:
        cmd = f'python3 {host_py} {trace}'
        with Guest(env, args, ['-c', cmd], size='800x620') as guest:
            ox, oy = until(lambda: window_origin(guest.capture()), 'SamTerm did not open its window')

            until(lambda: trace.exists() and 'Trequest:1:0:12' in trace.read_text(encoding='utf-8'),
                  'SamTerm did not complete initial sam -R handshake and Trequest')

            # Focus work TextArea (below work header at y ~ 217), move to end, type " ZX\n", click Write (x=481, y=14).
            guest.click(ox + 120, oy + 260)
            time.sleep(0.15)
            guest.run('xdotool', 'key', '--window', guest.window, 'End')
            time.sleep(0.1)
            guest.run('xdotool', 'type', '--window', guest.window, '--delay', '50', ' ZX')
            time.sleep(0.1)
            guest.run('xdotool', 'key', '--window', guest.window, 'Return')
            time.sleep(0.2)
            guest.click(ox + 481, oy + 14)

            log = until(
                lambda: trace.read_text(encoding='utf-8')
                if trace.exists() and 'Twrite:1' in trace.read_text(encoding='utf-8') else None,
                'SamTerm did not send Ttype and Twrite to sam -R host',
            )
            assert 'Tversion:0' in log and 'Tstartcmdfile:1000' in log, log
            assert 'Tstartfile:1' in log and 'Tcheck:1' in log and 'Trequest:1:0:12' in log, log
            assert 'Ttype:1:' in log and 'ZX' in log and 'Twrite:1' in log, log
            print('SamTerm completed live #C sam -R handshake, rasp fill, Ttype edit, and Twrite')
    finally:
        host_py.unlink(missing_ok=True)
        trace.unlink(missing_ok=True)


def main():
    args = arguments(__doc__, 'sam.zx')
    check_model(os.environ.copy())
    with private_display() as env:
        check_window(env, args)


if __name__ == '__main__':
    main()
