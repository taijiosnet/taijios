"""Compare the installed About Inferno and bitmap commands with shipped Tk."""

import argparse
import io
from pathlib import Path
from tempfile import TemporaryDirectory

from PIL import Image, ImageChops
from test_logwindow import private_display, read_output
from test_memory import desktop
from test_menu import inferno_window, pointer
from test_tcltk import BUILD, ROOT, RUNNER_FLAGS, SOURCES, color_bounds, command, compile_image, interaction, until

DESKTOP = (119, 119, 119)
VERSION_INK = (255, 85, 0)
ART_SIZE = 300, 207
STOCK_ORIGIN = 7, 25
FIXTURE = SOURCES / "about_bitmap_commands.tcl"
END = b"ABOUT-RETURNED"
BITMAP_FLAGS = ("--define", "TAIJI_TK_BITMAP", "--define", "TAIJI_TK_NO_CANVAS",
                "--bind-host", "zx_surface", "--bind-host", "taijios_files")


def guest(path):
    return f"/{path.relative_to(ROOT)}"


def transcript(env, invocation):
    with desktop(env, f"{invocation}; echo ABOUT-RETURNED") as app:
        output = bytearray()

        def complete():
            read_output(app, output)
            lines = output.splitlines()
            return lines[:lines.index(END)] if END in lines else None

        return until(complete, "About command transcript was incomplete")


def capture_window(env, invocation, locate):
    with desktop(env, f"{invocation}; echo ABOUT-RETURNED") as app:
        window = inferno_window(env)
        output = bytearray()

        def capture():
            png = command("import", "-window", window, "png:-", env=env, capture_output=True, check=True).stdout
            return Image.open(io.BytesIO(png)).convert("RGB")

        def visible():
            image = capture()
            origin = locate(image)
            if origin is None:
                return None
            x, y = origin
            art = image.crop((x, y, x+ART_SIZE[0], y+ART_SIZE[1]))
            label = image.crop((1, y+ART_SIZE[1], image.width-1, y+ART_SIZE[1]+28))
            bounds = color_bounds(label, VERSION_INK)
            return (image, art, label, bounds) if bounds else None

        image, art, label, bounds = until(visible, "About did not render its logo and orange version label", timeout=20)
        title_right = max(x for x in range(image.width-1) if image.getpixel((x, 12)) != DESKTOP)
        pointer(env, window, title_right-10, 12, "mousedown", "1", "sleep", "0.12", "mouseup", "1")
        until(lambda: capture().getpixel((150, 186)) == DESKTOP, "About did not close through the window manager")

        def returned():
            read_output(app, output)
            return END in output.splitlines()

        until(returned, "About did not return control after closing")
        if "zxrun -w " in invocation:
            assert b"0" in output.splitlines(), output
        return art, label.crop(bounds)


def stock_origin(image):
    return STOCK_ORIGIN if image.getpixel((162, 100)) == (85, 0, 0) else None


def locate_art(art):
    # This asymmetric section of the shipped logo identifies its origin without
    # requiring the legacy and hosted window decorations or fonts to match.
    offset_x, offset_y = 147, 170
    sample = art.crop((offset_x, offset_y, offset_x+25, offset_y+6))
    first_row = sample.crop((0, 0, sample.width, 1)).tobytes()

    def locate(image):
        for y in range(offset_y, image.height-ART_SIZE[1]+offset_y+1):
            row = image.crop((0, y, image.width, y+1)).tobytes()
            at = row.find(first_row)
            if at < 0 or at % 3:
                continue
            x = at//3
            if x >= offset_x and image.crop((x, y, x+sample.width, y+sample.height)).tobytes() == sample.tobytes():
                return x-offset_x, y-offset_y
        return None

    return locate


def named_mask(env, runner, folder):
    # The k1 image starts three bits into each stored row. Padding bits in the
    # file are deliberately set so they cannot silently enter the visible crop.
    mask = folder / "mask.bit"
    header = "".join(f"{field:>11} " for field in ("k1", 3, -2, 10, 1))
    mask.write_bytes(header.encode() + bytes((0xF0, 0x7F, 0xE4, 0x3F, 0xE0, 0x7F)))
    script = folder / "named_mask.tcl"
    script.write_text(f"""image create bitmap swatch -file @{guest(mask)}
frame .f -background black
label .mask -foreground red -background black -image swatch
image delete swatch
pack .mask -in .f -ipadx 5 -ipady 3 -padx 0 -pady 0
pack .f
button .quit -text Close -command {{destroy .}}
pack .quit
""")
    red = (255, 0, 0)
    black = (0, 0, 0)
    expected = ("1000001", "0010000", "0000001")

    def exercise(x, y, click, _keys, _type, capture, _transcript):
        image = capture()
        bounds = color_bounds(image, red)
        assert bounds and (bounds[2]-bounds[0], bounds[3]-bounds[1]) == (7, 3), bounds
        pixels = image.crop(bounds)
        expected_pixels = [red if bit == "1" else black for row in expected for bit in row]
        assert pixels.tobytes() == b"".join(bytes(pixel) for pixel in expected_pixels)
        click(x+150, y+55)
        return []

    interaction(env, runner, script, exercise)


def main():
    cli = argparse.ArgumentParser()
    cli.add_argument("--installed", action="store_true", help="exercise the installed About guest application")
    args = cli.parse_args()
    BUILD.mkdir(parents=True, exist_ok=True)
    about = ROOT / "dis/wm/about.zx" if args.installed else BUILD / "about.zx"
    runner = (ROOT / "dis" if args.installed else BUILD) / "tcltk.zx"
    if not args.installed:
        compile_image("about_app", about, *BITMAP_FLAGS)
        compile_image("tcltk", runner, *RUNNER_FLAGS)
    (BUILD / "about_bitmap_fixture.zi").write_text(f"Commands :: #string ABOUT_END\n{FIXTURE.read_text()}ABOUT_END;\n")
    model = BUILD / "about_bitmap_test.zx"
    compile_image("about_bitmap_test", model, *BITMAP_FLAGS)
    with private_display() as env:
        reference = transcript(env, f"tkcmd < {guest(FIXTURE)}")
        assert reference and all(line.startswith(b"#") for line in reference), reference
        hosted = transcript(env, f"zxrun {guest(model)}")
        assert hosted == [*(line[1:] for line in reference), b"0"], (reference, hosted)
        print(f"Inferno tkcmd and Ziran matched {len(reference)} label, bitmap, frame and packing results")
        stock, version = capture_window(env, "wm/about", stock_origin)
        assert version.width > 200 and len(stock.getcolors(62101)) > 30
        print("Stock About Inferno displayed the original artwork, live version and closed")
        run = f"zxrun -w {guest(about)}"
        find_art = locate_art(stock)
        pixels, version = capture_window(env, run, find_art)
        assert not ImageChops.difference(stock, pixels).getbbox(), "Hosted bitmap pixels differ from Inferno Tk"
        assert version.width > 250
        with TemporaryDirectory(dir=BUILD) as folder:
            folder = Path(folder)
            sysctl = folder / "sysctl"
            sysctl.write_text("About namespace [TEST] 9876")
            fixture = f"bind -b {guest(sysctl.parent)} /dev; {run}"
            changed_pixels, changed_version = capture_window(env, fixture, find_art)
            assert not ImageChops.difference(pixels, changed_pixels).getbbox()
            assert changed_version.tobytes() != version.tobytes(), "Hosted About ignored the guest namespace's sysctl"
            print("Hosted About matched all 62,100 artwork pixels, rendered the live and replaced guest sysctl, and closed")
            named_mask(env, runner, folder)
        print("The generic runner rendered a retained 1-bit image with its configured foreground")


if __name__ == "__main__":
    main()
