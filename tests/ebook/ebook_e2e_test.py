#!/usr/bin/env python3
"""Private-display Xvfb test for dis/ebook/ebook.zx with a real OEB book (OPF + HTML + CSS + table + image + link + annot)."""
import io
import os
from pathlib import Path
import subprocess
import sys
import time
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "build/dis-app-families/ebook-test-book"
sys.path.insert(0, str(ROOT / "appl/cmd/tcltk"))
from test_logwindow import private_display
from test_tcltk import launch, stop, until

EMU = ROOT / "emu/Linux/o.emu"
if not EMU.exists():
    EMU = ROOT / "Linux/386/bin/emu"


def make_test_book() -> Path:
    OUT.mkdir(parents=True, exist_ok=True)
    # Create a real uncompressed 16x16 bright-green Inferno .bit image
    hdr = f"{'r8g8b8':>11} {0:>11} {0:>11} {16:>11} {16:>11} ".encode("ascii")
    pixels = bytes([0, 180, 0] * (16 * 16))
    (OUT / "sample.bit").write_bytes(hdr + pixels)

    (OUT / "ch1.html").write_text(
        "<html><head><title>Chapter One</title>"
        "<style>h1 { color: #cc0000; } p.intro { margin-left: 16px; color: #004400; }</style>"
        "</head><body>"
        "<h1>Test Book Heading</h1>"
        "<p class=\"intro\">Styled paragraph with <a href=\"ch2.html#sec2\">jump to chapter 2</a>.</p>"
        "<hr/>"
        "<table><tr><th>ColA</th><th>ColB</th></tr><tr><td>Val1</td><td>Val2</td></tr></table>"
        "<img src=\"sample.bit\" width=\"32\" height=\"32\" alt=\"Green\"/>"
        "</body></html>"
    )
    (OUT / "ch1.html.annot").write_text("0 'First chapter note'")
    (OUT / "ch2.html").write_text(
        "<html><head><title>Chapter Two</title></head><body>"
        "<h1 id=\"sec2\">Second Chapter</h1><p>Reached via link!</p>"
        "</body></html>"
    )
    opf = OUT / "book.opf"
    opf.write_text(
        '<?xml version="1.0"?>'
        '<package><metadata><dc-metadata><dc:Title>Sample OEB Book</dc:Title></dc-metadata></metadata>'
        '<manifest>'
        '<item id="c1" href="ch1.html" media-type="text/x-oeb1-document"/>'
        '<item id="c2" href="ch2.html" media-type="text/x-oeb1-document"/>'
        '</manifest>'
        '<spine><itemref idref="c1"/><itemref idref="c2"/></spine>'
        '<guide><reference type="toc" title="Chapter 2" href="ch2.html"/></guide>'
        '</package>'
    )
    return opf


def main() -> None:
    opf = make_test_book()
    idx_file = OUT / "ch1.html.i"
    if idx_file.exists():
        idx_file.unlink()
    for key in ("WAYLAND_SOCKET", "SESSION_MANAGER", "ICEAUTHORITY", "XDG_RUNTIME_DIR"):
        os.environ.pop(key, None)
    command = (
        "wm/wm /dis/sh.dis -c "
        "'zxrun -w /dis/ebook/ebook.zx /build/dis-app-families/ebook-test-book/book.opf; echo EBOOK_DONE; sleep 60'"
    )
    log_path = OUT.parent / "ebook-window.log"
    with private_display() as env, log_path.open("w+b") as log:
        child = launch(
            env, EMU, "-p", "main=128M", "-r", ROOT,
            "-g", "800x600", "/dis/sh.dis", "-c", command,
            stdin=subprocess.DEVNULL, stdout=log, stderr=log,
        )
        try:
            window = until(
                lambda: subprocess.run(
                    ["xdotool", "search", "--onlyvisible", "--class", "inferno"],
                    env=env, capture_output=True,
                ).stdout.strip(),
                "ebook private display window missing",
                timeout=20,
            ).decode().splitlines()[0]

            def grab():
                raw = subprocess.check_output(
                    ["import", "-window", window, "png:-"],
                    env=env, stderr=subprocess.DEVNULL, timeout=10,
                )
                return Image.open(io.BytesIO(raw)).convert("RGB")

            # Verify BOTH the decoded green .bit image (0,180,0) AND yellow annotation badge (255,238,136) rendered!
            def rendered():
                im = grab()
                cols = set(im.getdata())
                if (0, 180, 0) in cols and (255, 238, 136) in cols:
                    return im
                return None

            img = until(rendered, "ebook decoded image + yellow annotation badge did not render", timeout=20)
            img.save(OUT.parent / "ebook-window.png")
            assert child.poll() is None, log_path.read_text(errors="replace")
            time.sleep(0.5)
            assert child.poll() is None, log_path.read_text(errors="replace")
        finally:
            stop(child)

    text = log_path.read_text(errors="replace")
    assert "tcltk:" not in text.lower() and "panic" not in text.lower() and "EBOOK_DONE" not in text, text
    assert idx_file.exists(), "expected .i index cache file to be written"
    idx_txt = idx_file.read_text()
    assert "pages\nsize 400 600\nlength " in idx_txt, f"unexpected .i index format:\n{idx_txt}"
    print("ebook_e2e_test: PASS")


if __name__ == "__main__":
    main()
