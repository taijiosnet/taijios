#!/usr/bin/env python3
"""End-to-end test for dis/demo/camera/camera.zx (9P server) and tkinterface.zx (Tk GUI)."""
import io
import os
from pathlib import Path
import subprocess
import sys
import time
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "build/dis-app-families"
sys.path.insert(0, str(ROOT / "appl/cmd/tcltk"))
from test_logwindow import private_display
from test_tcltk import launch, stop, until

EMU = ROOT / "emu/Linux/o.emu"
if not EMU.exists():
    EMU = ROOT / "Linux/386/bin/emu"


def test_camera_9p_server() -> None:
    script = r"""
mount -A {zxrun /dis/demo/camera/camera.zx -S} /n/remote
echo 'CAM_LS:'
ls /n/remote
echo 'STORAGE:'
cat /n/remote/storage
echo 'POWER:'
cat /n/remote/power
echo 'DATE:'
cat /n/remote/date
echo 'JPG_BEFORE:'
ls /n/remote/jpg
echo snap > /n/remote/ctl
echo 'JPG_AFTER:'
ls /n/remote/jpg
echo zpos > /n/remote/state
echo 'STATE:'
cat /n/remote/state
echo 'zpos 50' > /n/remote/ctl
echo zpos > /n/remote/state
echo 'STATE2:'
cat /n/remote/state
rm /n/remote/jpg/p0000001.jpg
echo 'JPG_REMOVED:'
ls /n/remote/jpg
unmount /n/remote
echo 'CAMERA_9P_PASS'
"""
    proc = subprocess.Popen(
        [str(EMU), "-r", str(ROOT), "/dis/sh.dis", "-c", script],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    lines = []
    try:
        assert proc.stdout is not None
        for line in proc.stdout:
            lines.append(line)
            if "CAMERA_9P_PASS" in line:
                break
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
    out = "".join(lines)
    print(out)
    assert "Picture Memory" in out, "missing storage output"
    assert "Power Mode = 1" in out, "missing power mode"
    assert "date is 01/01/26 12:00:00" in out, "missing date"
    assert "p0000001.jpg" in out, "missing initial photo"
    assert "p0000002.jpg" in out, "missing snapped photo"
    assert "zpos: 50" in out, "missing updated state"
    assert "CAMERA_9P_PASS" in out, "did not complete"
    print("camera_9p_test: PASS")


def test_tkinterface_window() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for key in ("WAYLAND_SOCKET", "SESSION_MANAGER", "ICEAUTHORITY", "XDG_RUNTIME_DIR"):
        os.environ.pop(key, None)
    command = (
        "wm/wm /dis/sh.dis -c "
        "'mount -A {zxrun /dis/demo/camera/camera.zx -S} /n/remote; "
        "zxrun -w /dis/demo/camera/tkinterface.zx /n/remote; echo CAM_DONE; sleep 60'"
    )
    log_path = OUT / "camera-window.log"
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
                "camera private display window missing",
                timeout=20,
            ).decode().splitlines()[0]

            def grab():
                raw = subprocess.check_output(
                    ["import", "-window", window, "png:-"],
                    env=env, stderr=subprocess.DEVNULL, timeout=10,
                )
                return Image.open(io.BytesIO(raw)).convert("RGB")

            img = until(
                lambda: (lambda im: im if (255, 204, 0) in set(im.getdata()) else None)(grab()),
                "camera thumbnail tile did not render",
                timeout=20,
            )
            img.save(OUT / "camera-window.png")
            assert child.poll() is None, log_path.read_text(errors="replace")
            time.sleep(0.5)
            assert child.poll() is None, log_path.read_text(errors="replace")
        finally:
            stop(child)
    text = log_path.read_text(errors="replace")
    assert "tcltk:" not in text.lower() and "panic" not in text.lower() and "CAM_DONE" not in text, text
    print("tkinterface_window_test: PASS")


if __name__ == "__main__":
    test_camera_9p_server()
    test_tkinterface_window()
