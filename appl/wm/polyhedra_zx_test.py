#!/usr/bin/env python3
"""Check the ZX Polyhedra against the 72 panels recorded from the Dis version."""
import hashlib
import time

from PIL import Image, ImageChops

from wm_app_test import BUILD, HERE, ROOT, Guest, arguments, private_display, until

PANEL = (4, 126, 404, 526)  # the drawing area in a 640x560 guest
COLUMNS, TILE = 8, 400
TIME = b'1700000006000000\n'
TOLERANCE = 4


def recorded():
    lines = (HERE / 'polyhedra_dis.expected').read_text(encoding='utf-8').splitlines()
    digests = [line for line in lines if line and not line.startswith('#')]
    sheet = Image.open(HERE / 'polyhedra_dis.png').convert('RGB')
    assert sheet.size == (COLUMNS * TILE, -(-len(digests) // COLUMNS) * TILE), sheet.size
    panels = []
    for index, digest in enumerate(digests):
        left, top = (index % COLUMNS) * TILE, (index // COLUMNS) * TILE
        panel = sheet.crop((left, top, left + TILE, top + TILE))
        assert hashlib.sha1(panel.tobytes()).hexdigest() == digest, f'fixture tile {index} changed'
        panels.append(panel)
    return panels


def difference(first, second):
    box = ImageChops.difference(first, second).getbbox()
    if box is None:
        return 0
    return sum(1 for pixel in ImageChops.difference(first.crop(box), second.crop(box)).getdata()
               if pixel != (0, 0, 0))


def main():
    args = arguments(__doc__, 'polyhedra.zx')
    references = recorded()
    digests = {hashlib.sha1(panel.tobytes()).hexdigest(): index for index, panel in enumerate(references)}
    BUILD.mkdir(parents=True, exist_ok=True)
    clock = BUILD / 'polyhedra-time'
    clock.write_bytes(TIME)
    setup = f'bind /{clock.relative_to(ROOT).as_posix()} /dev/time; '
    with private_display() as env, Guest(env, args, ['-p', '3'], setup=setup, size='640x560') as guest:
        def drawn(image):
            colors = image.crop(PANEL).getcolors(TILE * TILE)
            return image if colors is None or len(colors) >= 2 else None

        until(lambda: drawn(guest.capture()), 'Polyhedra did not draw the solid')
        matched = set()
        deadline = time.monotonic() + 120
        while len(matched) < len(references) and time.monotonic() < deadline:
            panel = guest.capture().crop(PANEL)
            index = digests.get(hashlib.sha1(panel.tobytes()).hexdigest())
            if index is not None:
                matched.add(index)
                continue
            near = [number for number, reference in enumerate(references)
                    if difference(panel, reference) <= TOLERANCE]
            if not near:
                guest.capture().save(BUILD / 'polyhedra-failure.png')
                raise AssertionError('Polyhedra drew a panel that matches none of the Dis panels')
            matched.update(near)
    assert len(matched) == len(references), f'only {len(matched)} of {len(references)} recorded panels appeared'
    print(f'Polyhedra drew all {len(references)} panels of the Dis version\'s turn '
          f'(a face-boundary pixel may differ by up to {TOLERANCE} pixels)')


if __name__ == '__main__':
    main()
