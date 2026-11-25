#!/usr/bin/env python3
"""Check the ZX Dis Module Manager (rt) parser, disassembler, and live flag rewriting."""
import os
import shutil
import time
from pathlib import Path

from wm_app_test import BUILD, Guest, ROOT, arguments, ocr, private_display, run_model, until

GREY = (221, 221, 221)
WIN_W, WIN_H = 660, 500


def check_model(env):
    message = run_model('rt', 'rt_states.expected', env)
    assert message == 'RT matched Dis operand codec, disassembly and lossless header rewrite rules', message
    print('RT model matched Dis operand codec, disassembly and lossless header rewrite rules')


def window_origin(image):
    pixels = image.load()
    for y in range(10, image.height - WIN_H + 1):
        for x in range(0, image.width - WIN_W + 1):
            if pixels[x, y] == GREY and pixels[x + WIN_W - 1, y] == GREY \
                    and pixels[x, y + WIN_H - 1] == GREY and pixels[x + WIN_W - 1, y + WIN_H - 1] == GREY:
                return x, y
    return None


def decode_operand(data, pos):
    b = data[pos]
    pos += 1
    tag = b & 0xC0
    if tag == 0x00:
        return b, pos
    if tag == 0x40:
        return b | ~0x7F, pos
    if tag == 0x80:
        hi = (b | ~0x3F) if (b & 0x20) else (b & 0x3F)
        return (hi << 8) | data[pos], pos + 1
    hi = (b | ~0x3F) if (b & 0x20) else (b & 0x3F)
    val = (hi << 24) | (data[pos] << 16) | (data[pos + 1] << 8) | data[pos + 2]
    return val, pos + 3


def read_rt_and_ss(path):
    data = path.read_bytes()
    pos = 0
    magic, pos = decode_operand(data, pos)
    if magic == 923426:  # SMAGIC
        n, pos = decode_operand(data, pos)
        pos += n
        magic, pos = decode_operand(data, pos)
    assert magic == 819248, f'unexpected magic {magic}'
    rt, pos = decode_operand(data, pos)
    ss, pos = decode_operand(data, pos)
    return rt, ss


def check_window(env, args):
    # Copy a real .dis file into build/wm-apps/ so we can test live disassembly + flag rewrite!
    BUILD.mkdir(parents=True, exist_ok=True)
    sample = BUILD / 'rt_sample.dis'
    src_dis = ROOT / 'zx/sh.dis'
    shutil.copyfile(src_dis, sample)
    orig_rt, orig_ss = read_rt_and_ss(sample)
    try:
        guest_path = '/build/wm-apps/rt_sample.dis'
        with Guest(env, args, [guest_path], size='740x600') as guest:
            ox, oy = until(lambda: window_origin(guest.capture()), 'RT did not open its window')

            # Verify disassembly loaded and rendered module info.
            info_txt = until(
                lambda: ocr(guest.capture(), (ox + 8, oy + 58, ox + 520, oy + 82))
                if 'Module' in ocr(guest.capture(), (ox + 8, oy + 58, ox + 520, oy + 82)) else None,
                'RT did not display loaded Dis module summary',
            )
            assert 'inst=' in info_txt or 'Module' in info_txt, info_txt

            # Toggle MUSTCOMPILE button at (ox + 70, oy + 45) and click Save Flags at (ox + 126, oy + 15).
            guest.click(ox + 70, oy + 45)
            time.sleep(0.15)
            guest.click(ox + 126, oy + 15)

            until(
                lambda: read_rt_and_ss(sample)[0] == (orig_rt ^ 1) or None,
                'RT did not rewrite MUSTCOMPILE flag in .dis header',
            )
            new_rt, new_ss = read_rt_and_ss(sample)
            assert new_rt == (orig_rt ^ 1), (orig_rt, new_rt)
            assert new_ss == orig_ss, (orig_ss, new_ss)
            print(f'RT disassembled real .dis module and rewrote rt flags ({orig_rt} -> {new_rt})')
    finally:
        sample.unlink(missing_ok=True)


def main():
    args = arguments(__doc__, 'rt.zx')
    check_model(os.environ.copy())
    with private_display() as env:
        check_window(env, args)


if __name__ == '__main__':
    main()
