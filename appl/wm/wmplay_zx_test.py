#!/usr/bin/env python3
"""Check the ZX WmPlay audio header rules and live playback window in a private TaijiOS guest."""
import os
from pathlib import Path
import time

from wm_app_test import Guest, arguments, ocr, private_display, run_model, until

GREY = (221, 221, 221)
LIGHT = (255, 255, 255)
DARK = (150, 150, 150)
WIN_W, WIN_H = 360, 96


def check_model(env):
    message = run_model('wmplay', 'wmplay_states.expected', env)
    assert message == 'WmPlay validated aligned Inferno audio headers and rejected malformed inputs', message
    print('WmPlay model validated aligned Inferno audio headers and rejected malformed inputs')


def window_origin(image):
    pixels = image.load()
    for y in range(10, image.height - WIN_H + 1):
        for x in range(0, image.width - WIN_W + 1):
            if pixels[x, y] == LIGHT and pixels[x + 2, y + 2] == GREY \
                    and pixels[x + WIN_W - 1, y + WIN_H - 1] == DARK \
                    and pixels[x + WIN_W - 3, y + WIN_H - 3] == GREY:
                return x, y
    return None


def check_window(env, args):
    tmp_dir = Path(__file__).resolve().parents[2] / 'build/wm-apps'
    tmp_dir.mkdir(parents=True, exist_ok=True)
    bad_file = tmp_dir / 'wmplay_bad.txt'
    iaf_file = tmp_dir / 'wmplay_test.iaf'
    dev_dir = tmp_dir / 'wmplay-dev'
    dev_dir.mkdir(exist_ok=True)
    ctl_out = dev_dir / 'audioctl'
    pcm_out = dev_dir / 'audio'
    bad_file.write_bytes(b'NOTAUDIO12345\n\n')
    header = b'rate 44100\nchans 2\n\n'  # 20 bytes (multiple of 4)
    payload = b'PCM_PAYLOAD_12345678' * 4
    iaf_file.write_bytes(header + payload)
    ctl_out.write_bytes(b'')
    pcm_out.write_bytes(b'')
    try:
        # 1. Invalid file shows "not an audio file" notice.
        with Guest(env, args, ['/build/wm-apps/wmplay_bad.txt'], size='520x320') as guest:
            origin = until(lambda: window_origin(guest.capture()), 'WmPlay did not open its window')
            ox, oy = origin
            until(
                lambda: 'audio' in ocr(guest.capture(), (ox + 8, oy + 8, ox + WIN_W - 8, oy + 52)).lower() or None,
                'WmPlay did not show not-an-audio-file error notice',
            )
            print('WmPlay rejected non-audio file with an error notice')

        # 2. Valid .iaf file writes header to /dev/audioctl and streams PCM to /dev/audio.
        setup = 'bind -b /build/wm-apps/wmplay-dev /dev; '
        with Guest(env, args, ['/build/wm-apps/wmplay_test.iaf'], setup=setup, size='520x320') as guest:
            def streamed():
                c = ctl_out.read_bytes()
                p = pcm_out.read_bytes()
                return (c, p) if c == header[:-1] and p == payload else None

            until(streamed, 'WmPlay did not write audioctl header and stream PCM payload to /dev/audio')
            print('WmPlay wrote Inferno audioctl header and streamed PCM payload to /dev/audio')
    finally:
        for f in (bad_file, iaf_file, ctl_out, pcm_out):
            f.unlink(missing_ok=True)
        try:
            dev_dir.rmdir()
        except OSError:
            pass


def main():
    args = arguments(__doc__, 'wmplay.zx')
    check_model(os.environ.copy())
    with private_display() as env:
        check_window(env, args)


if __name__ == '__main__':
    main()
