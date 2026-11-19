# Tk for Ziran Tcl

Import `tcl_tk` and call `Attach` with a Tcl interpreter to enable Tk commands.
The package manages one root `.` and up to 32 direct children. The separate
renderer draws the widgets into an RGBA pixel buffer. The Taiji launcher
uses `zx_surface` to open the window, present those pixels and receive events.
The Tcl core runs headless on its own.

The [Bounce toolbar script](bounce_controls.tcl) adapts the label and count
controls from Inferno's [Bounce demo](../../wm/bounce.b). The buttons run Tcl
scripts that change the count and reconfigure the label. Close runs
`destroy .`. This port uses the Inferno [MIT notice](../../../NOTICE).

## Run in Taiji

From the TaijiOS root, with `zi2zx`, Xvfb, `xdotool`, ImageMagick `import`,
Python Pillow, and the existing Linux/386 emulator available:

```sh
python3 appl/cmd/tcltk/test_tcltk.py
install -m 0644 build/tcltk/tcltk.zx dis/tcltk.zx
python3 appl/cmd/tcltk/test_tcltk.py --installed
```

In the Taiji graphical shell, run `zxrun -w /dis/tcltk.zx`. The executable
launch command from the project root is:

```sh
Linux/386/bin/emu -r "$PWD" -g 800x600 wm/wm zxrun -w /dis/tcltk.zx
```

The test feeds the same widget commands to Inferno `tkcmd` and the pure Ziran
model. The display test uses a private Xvfb to check the plus and minus
buttons, label pixel changes, and closure via the Tcl callback.

## Supported commands

| Command | Options and behavior |
| --- | --- |
| `label .path` | `-text text` |
| `button .path` | `-text text` and `-command script` |
| `pack .path ?path ...?` | `-side top`, `bottom`, `left` or `right`, `-padx pixels`, `-pady pixels` |
| `.path configure option value` | Set one or more of that widget's supported options |
| `.path cget option` | Read text or a button's script |
| `.button invoke` | Evaluate the button's script and return its Tcl result |
| `destroy .path ?path ...?` | Remove widgets. `destroy .` closes the root |

Left-button press and release inside the same button invoke its script.
The small stroke font displays English letters, digits, spaces, `+`, `-`,
and `.`. Lowercase shares the uppercase glyphs. Unknown bytes display `?`.
The renderer uses fixed colors and clips text to the available width.
Nested widgets, other widget types, keyboard bindings, fonts, themes,
Tk's full option system and pack geometry, and additional toplevels are
outside this subset.
