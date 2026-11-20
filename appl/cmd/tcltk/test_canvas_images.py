"""Compare hosted Canvas bitmap lifetimes, geometry, and pixels with stock Inferno Tk."""

import argparse
import io
from itertools import zip_longest
from pathlib import Path
from tempfile import TemporaryDirectory

from PIL import Image, ImageChops
from test_about import guest, transcript
from test_logwindow import private_display, read_output
from test_memory import desktop
from test_menu import inferno_window, pointer
from test_tcltk import BUILD, ROOT, RUNNER_FLAGS, SOURCES, color_bounds, command, compile_image, until, write_fixture

RED = (255, 0, 0)
WHITE = (255, 255, 255)
REGIONS = ((25, 20, 65, 50), (90, 65, 130, 95), (95, 15, 135, 45), (15, 70, 55, 100), (10, 5, 18, 9))


def check_commands(env, folder):
    fixture = SOURCES / "canvas_image_commands.tcl"
    stress = ["canvas .life"]
    for _ in range(10):
        for discard in (".life delete 1", ".life delete icon", ".life delete all", "destroy .life\ncanvas .life"):
            stress += ["image create bitmap life -file file.bit -maskfile file.mask",
                       ".life create image 0 0 -image life -tags icon", "image delete life", discard]
    commands = fixture.read_text() + "\n".join(stress) + "\n"
    stock_script = folder / "commands.tcl"
    stock_script.write_text(commands)
    stock = transcript(env, f"tkcmd < {guest(stock_script)}")
    assert stock and all(line.startswith(b"#") for line in stock), stock
    write_fixture("canvas_image_fixture.zi", f"Commands :: #string CANVAS_END\n{commands}CANVAS_END;\n")
    model = BUILD / "canvas_image_command_test.zx"
    compile_image("canvas_image_command_test", model, *RUNNER_FLAGS)
    hosted = transcript(env, f"zxrun {guest(model)}")
    for line, (expected, actual) in enumerate(zip_longest([*(line[1:] for line in stock), b"0"], hosted), 1):
        assert expected == actual, (line, expected, actual)
    print(f"Ziran matched {len(stock)} stock Canvas image results, including 40 cycles of retained image deletion")


def write_bitmap(path, encoding, rect, data):
    header = "".join(f"{field:>11} " for field in (encoding, *rect))
    path.write_bytes(header.encode() + data)
    return f"@{guest(path)}"


def exercise(env, invocation, *, stock):
    with desktop(env, invocation) as app:
        window = inferno_window(env)
        output = bytearray()

        def capture():
            png = command("import", "-window", window, "png:-", env=env, check=True, capture_output=True).stdout
            return Image.open(io.BytesIO(png)).convert("RGB")

        def events():
            read_output(app, output)
            lines = output.decode().splitlines()
            assert not any(line.startswith(("#!", "tcltk:")) for line in lines), lines
            if stock:
                return [line.removeprefix("#<stdout>").strip("{}") for line in lines if line.startswith("#<stdout>")]
            return lines

        until(lambda: events() == ["ready"], "Canvas image fixture did not initialize")

        def canvas_pixels():
            image = capture()
            bounds = color_bounds(image, RED)
            if bounds and (bounds[2]-bounds[0], bounds[3]-bounds[1]) == (158, 116):
                return image.crop(bounds), bounds[:2]
            return None

        image, (left, top) = until(canvas_pixels, "Canvas with images did not paint at its requested size")
        regions = [image.crop(rect) for rect in REGIONS]
        assert regions[0].tobytes() == regions[1].tobytes(), "redefined name changed a retained folder image"
        assert regions[0].tobytes() != regions[2].tobytes(), "new items still show the deleted folder image"
        assert regions[4].tobytes() == b"".join(bytes(WHITE if (x, y) in {(2, 1), (3, 2)} else RED)
                                                 for y in range(4) for x in range(8)), "bitmap origins shifted the mask"

        hole = next((x, y) for y in range(30) for x in range(40) if regions[0].getpixel((x, y)) == RED)
        x, y = left+REGIONS[0][0]+hole[0], top+REGIONS[0][1]+hole[1]
        command("xdotool", "windowfocus", window, env=env, check=True)
        pointer(env, window, x, y, "mousedown", "3")
        until(lambda: events() == ["ready", "dir right"], "transparent icon pixel did not receive the item binding")
        pointer(env, window, x, y, "mouseup", "3", "sleep", "0.12", "mousedown", "2")
        try:
            until(lambda: events() == ["ready", "dir right", "dir removed"], "icon did not receive the delete action")
        except AssertionError as failure:
            raise AssertionError(f"{failure}: {events()}") from failure
        pointer(env, window, x, y, "mouseup", "2")

        def removed():
            result = canvas_pixels()
            return result and result[0].crop(REGIONS[0]).getcolors() == [(1200, RED)]

        until(removed, "deleted icon still painted on Canvas")
        result, _ = canvas_pixels()
        assert result.crop(REGIONS[1]).tobytes() == regions[1].tobytes(), "deleting one item released a shared image"
        return regions


def main():
    cli = argparse.ArgumentParser()
    cli.add_argument("--installed", action="store_true")
    args = cli.parse_args()
    BUILD.mkdir(parents=True, exist_ok=True)
    runner = ROOT / "dis/tcltk.zx" if args.installed else BUILD / "tcltk-masked-canvas.zx"
    if not args.installed:
        compile_image("tcltk", runner, *RUNNER_FLAGS)
    template = (SOURCES / "canvas_image_window.tcl").read_text()
    with TemporaryDirectory(dir=BUILD) as scratch, private_display() as env:
        folder = Path(scratch)
        check_commands(env, folder)
        source = write_bitmap(folder / "offset.bit", "m8", (2, 3, 10, 7), bytes([255])*32)
        mask = write_bitmap(folder / "offset.mask", "k1", (4, 4, 6, 6), b"\x08\x04")
        template = template.replace("SOURCE", source).replace("MASK", mask)
        stock_path = folder / "stock.tcl"
        stock_path.write_text(template.replace("EMIT ", "send stdout "))
        stock = exercise(env, f"{{cat {guest(stock_path)}; sleep 45}} | tkcmd", stock=True)
        hosted_path = folder / "hosted.tcl"
        hosted_path.write_text(template.replace("EMIT ", "puts "))
        hosted = exercise(env, f"zxrun -w {guest(runner)} < {guest(hosted_path)}", stock=False)
        for index, (expected, actual) in enumerate(zip(stock, hosted, strict=True)):
            assert not ImageChops.difference(expected, actual).getbbox(), f"Canvas image pixels differ in region {index}"
    print("Stock and hosted Canvas matched shipped directory icons, mask-only and offset masks, hit bounds, and deletion")


if __name__ == "__main__":
    main()
