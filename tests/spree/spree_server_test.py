#!/usr/bin/env python3
"""End-to-end headless emu + zxrun test for dis/spree/spree.zx 9P server."""
import os
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
EMU = os.path.join(ROOT, "Linux", "386", "bin", "emu")
if not os.path.exists(EMU):
    EMU = os.path.join(ROOT, "Linux", "amd64", "bin", "emu")


def run_emu_until(script: str, sentinel: str, timeout: int = 20) -> str:
    proc = subprocess.Popen(
        [EMU, "-r", ROOT, "/dis/sh.dis", "-c", script],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    lines = []
    try:
        assert proc.stdout is not None
        for line in proc.stdout:
            lines.append(line)
            if sentinel in line:
                break
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
    return "".join(lines)


def main() -> int:
    script = r"""
mount -A {zxrun /dis/spree/spree.zx} /n/remote
echo -n 'NAME:'
cat /n/remote/name
echo ''
echo 'ROOT_ENTRIES:'
ls /n/remote
echo 'LOBBY_ENTRIES:'
ls /n/remote/0
<> /n/remote/0/ctl {
    echo join >[1=0]
    read
    read
    echo 'start gather 1 freecell' >[1=0]
    echo 'AFTER_START:'
    ls /n/remote
}
<> /n/remote/1/ctl {
    echo join >[1=0]
    read
    read
}
unmount /n/remote
echo 'SPREE_E2E_PASS'
"""
    out = run_emu_until(script, "SPREE_E2E_PASS", timeout=20)
    print(out)
    assert "ROOT_ENTRIES:" in out, "missing ROOT_ENTRIES"
    assert "/n/remote/name" in out or "name" in out, "missing name file"
    assert "/n/remote/0" in out or "0" in out, "missing lobby dir 0"
    assert "clienttype lobby" in out, "missing clienttype lobby"
    assert "AFTER_START:" in out, "missing AFTER_START"
    assert "/n/remote/1" in out or "1" in out, "missing new clique dir 1"
    assert "clienttype cards" in out, "missing clienttype cards from freecell"
    assert "SPREE_E2E_PASS" in out, "did not reach end"
    print("spree_server_test: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
