"""Compare stock and hosted Graph0 windows and the Canvas command transcript."""

import argparse
import io

from PIL import Image, ImageChops

from test_logwindow import private_display, read_output
from test_memory import desktop
from test_tcltk import BUILD, ROOT, SOURCES, color_bounds, command, compile_image, until


POINTS = ((0, 0), (1, 2), (2, -1), (3, 3), (4, 1))
MAX_POINTS = 3072
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
DESKTOP = (119, 119, 119)
FLAGS = ("--bind-host", "taijios_args", "--bind-host", "taijios_files", "--bind-host", "zx_surface")


def oracle_commands(env):
    with desktop(env, "tkcmd < /appl/cmd/tcltk/graph0_canvas_commands.tcl") as app:
        output = bytearray()

        def results():
            read_output(app, output)
            lines = output.decode().splitlines()
            assert all(line.startswith("#") and not line.startswith("#!") for line in lines), lines
            return [line[1:] for line in lines] if lines and lines[-1] == "#42" else None

        return until(results, "incomplete canvas command transcript")


def model_commands():
    fixture = (SOURCES / "graph0_canvas_commands.tcl").read_text()
    (BUILD / "graph0_canvas_input.zi").write_text(f"Commands :: #string GRAPH_COMMANDS_END\n{fixture}GRAPH_COMMANDS_END;\n")
    model = BUILD / "graph0_canvas_test.zx"
    compile_image("graph0_canvas_test", model)
    result = command("zi2zx", "run", "--backend", "engine", model, capture_output=True, text=True, check=True)
    assert not result.stderr and result.stdout.splitlines()[-1:] == ["0"], result
    return result.stdout.splitlines()[:-1]


def window_plot(env, invocation, *, hosted, zoom=None):
    with desktop(env, invocation) as app:
        output = bytearray()
        if zoom is None:
            zoom = 0.8 if hosted else 1.0
        width, height = round(600*zoom), round(480*zoom)
        window = until(lambda: command("xdotool", "search", "--onlyvisible", "--name", "^inferno$",
                                       env=env, capture_output=True, text=True).stdout.strip(), "Inferno did not map")

        def capture():
            read_output(app, output)
            assert not any(line.startswith((b"arena ", b"tcltk:", b"graph0:", b"tk->cmd("))
                           for line in output.splitlines()), output
            shot = command("import", "-window", window, "png:-", env=env, capture_output=True, check=True)
            return Image.open(io.BytesIO(shot.stdout)).convert("RGB")

        def canvas():
            image = capture()
            bounds = color_bounds(image.crop((1, 25, image.width-1, image.height)), WHITE)
            if bounds and bounds[2]-bounds[0] == width and bounds[3]-bounds[1] == height:
                x, y = bounds[0]+1, bounds[1]+25
                # Inferno maps the white canvas before it has read and plotted large files.
                if image.getpixel((x+round(300*zoom), y+round(34*zoom))) == BLACK:
                    return image, (x, y, x+width, y+height)

        image, (x, y, right, bottom) = until(canvas, f"Graph0 did not render a {width}×{height} plot area")
        plot = image.crop((x, y, right, bottom))
        plot_pixels = plot.load()

        def scaled(*coordinates):
            return tuple(round(value*zoom) for value in coordinates)

        for row in scaled(34, 403):
            assert sum(plot_pixels[column, row] == BLACK for column in range(*scaled(138, 506))) >= round(360*zoom), "missing horizontal axis"
        for column in scaled(137, 506):
            assert sum(plot_pixels[column, row] == BLACK for row in range(*scaled(35, 403))) >= round(360*zoom), "missing vertical axis"
        assert color_bounds(plot.crop(scaled(75, 35, 128, 400)), BLACK), "missing vertical tick labels"
        assert color_bounds(plot.crop(scaled(150, 411, 506, 448)), BLACK), "missing horizontal tick labels"

        def pixel(first, second):
            scale = 384.0 / (1.04 * 4.6)
            return scaled(506 + (first-4.3)*scale, 34 - (second-3.3)*scale)

        def ink_at(px, py):
            return any(plot_pixels[px+dx, py+dy] == BLACK for dx in (-1, 0, 1) for dy in (-1, 0, 1))

        for (ax, ay), (bx, by) in zip(POINTS, POINTS[1:]):
            assert ink_at(*pixel((ax+bx)/2, (ay+by)/2)), "coordinate pairs were not connected"
        endpoint_x, endpoint_y = pixel(*POINTS[0])
        assert ink_at(endpoint_x-3, endpoint_y) and ink_at(endpoint_x, endpoint_y+3), "missing start marker"

        def click(px, py):
            command("xdotool", "mousemove", "--sync", "--window", window, str(px), str(py),
                    "mousedown", "1", "sleep", "0.12", "mouseup", "1", env=env, check=True)

        status = (right-220, max(24, y-30), right, y-2)

        def changed(previous):
            now = capture().crop(status)
            return now if ImageChops.difference(previous, now).getbbox() else None

        click(x+endpoint_x, y+endpoint_y)
        first = until(lambda: changed(image.crop(status)), "first plot click did not show data coordinates")
        px, py = pixel(*POINTS[3])
        click(x+px, y+py)
        until(lambda: changed(first), "second plot click did not update data coordinates")
        assert not ImageChops.difference(capture().crop((x, y, right, bottom)), plot).getbbox()

        title_right = max(column for column in range(image.width-1) if image.getpixel((column, 12)) != DESKTOP)
        click(title_right-10, 12)
        until(lambda: capture().getpixel((x+5, y+5)) == DESKTOP, "graph window did not close")
        if hosted:
            def returned():
                read_output(app, output)
                return b"0" in output.splitlines()

            until(returned, "hosted Graph0 did not return success")


def limits(env, image, data):
    with data.open("a") as stream:
        for i in range(MAX_POINTS-len(POINTS)):
            stream.write(f".{i % 99 + 1:02d} .{i // 99 + 1:02d}\n")
    invocation = f"zxrun -w /{image.relative_to(ROOT)} /{data.relative_to(ROOT)}"
    window_plot(env, invocation, hosted=True)

    with data.open("a") as stream:
        stream.write("0 0\n")
    with desktop(env, invocation) as app:
        output = bytearray()

        def rejected():
            read_output(app, output)
            if b"1" in output.splitlines():
                assert f"graph0: maximum {MAX_POINTS} pairs".encode() in output, output
                return True

        until(rejected, "Graph0 did not reject a file above its point limit")


def main():
    cli = argparse.ArgumentParser()
    cli.add_argument("--installed", action="store_true", help="exercise /dis/math/graph0.zx")
    cli.add_argument("--oracle-only", action="store_true", help="exercise the original Dis app and tkcmd")
    args = cli.parse_args()
    BUILD.mkdir(parents=True, exist_ok=True)
    data = BUILD / "graph0-points.xy"
    data.write_text("".join(f"{x} {y}\n" for x, y in POINTS))
    data_path = f"/{data.relative_to(ROOT)}"
    image = ROOT / "dis/math/graph0.zx" if args.installed else BUILD / "graph0.zx"
    if not args.oracle_only and not args.installed:
        compile_image("graph0_app", image, *FLAGS)
    with private_display() as env:
        expected = oracle_commands(env)
        window_plot(env, f"/dis/math/graph0.dis {data_path}", hosted=False)
        print("Inferno Dis Graph0 plotted real file pairs, reported clicked data coordinates, and closed")
        if not args.oracle_only:
            actual = model_commands()
            assert actual == expected, (actual, expected)
            print(f"Inferno tkcmd and Ziran matched {len(expected)} Canvas command results")
            window_plot(env, f"zxrun -w /{image.relative_to(ROOT)} {data_path}", hosted=True)
            print("Hosted ZX Graph0 matched scaled axes, connected points, markers, click readout, and close")
            limits(env, image, data)
            print(f"Hosted ZX Graph0 plotted {MAX_POINTS} points and rejected an oversized dataset")


if __name__ == "__main__":
    main()
