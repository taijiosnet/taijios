# Tk for Ziran Tcl

Import `tcl_tk` and call `Attach` with a Tcl interpreter to enable Tk commands.
The package manages one root `.` and up to 32 widgets under it. The separate
renderer draws the widgets into an RGBA pixel buffer. The Taiji launcher
uses `zx_surface` to open the window, present those pixels and receive events.
The Tcl core runs headless on its own.

The [Bounce toolbar script](bounce_controls.tcl) adapts the label and count
controls from Inferno's [Bounce demo](../../wm/bounce.b). The buttons run Tcl
scripts that change the count and reconfigure the label. Close runs
`destroy .`. The [Man query script](man_query.tcl) adapts the input panel from
Inferno's [manual browser](../../wm/man.b). Enter submits the query, and Search
runs the same Tcl callback. The demo displays the submitted query. Manual file
lookup, browsing history, and the text viewer are outside this slice. This port
uses the Inferno [MIT notice](../../../NOTICE).

## Run in Taiji

From the TaijiOS root, with `zi2zx`, Xvfb, `xdotool`, ImageMagick `import`,
Python Pillow, and the existing Linux/386 emulator available:

```sh
python3 appl/cmd/tcltk/test_tcltk.py
install -m 0644 build/tcltk/tcltk.zx dis/tcltk.zx
python3 appl/cmd/tcltk/test_tcltk.py --installed
```

The launcher reads guest stdin until EOF and accepts scripts up to 1 MiB.
It uses `taijios_stdin.Read` and `zx_surface` from the ZX-enabled Taiji emulator.
Run either script from the Taiji graphical shell.

```sh
zxrun -w /dis/tcltk.zx < /appl/cmd/tcltk/man_query.tcl
zxrun -w /dis/tcltk.zx < /appl/cmd/tcltk/bounce_controls.tcl
```

To start the Man panel directly from the project root:

```sh
Linux/386/bin/emu -r "$PWD" -g 800x600 wm/wm /dis/sh.dis -c \
    'zxrun -w /dis/tcltk.zx < /appl/cmd/tcltk/man_query.tcl'
```

The test feeds the same widget commands to Inferno `tkcmd` and the pure Ziran
model. A private Xvfb session runs both scripts through guest stdin and checks
callbacks, pixel changes, nested layout, keyboard focus, UTF-8 character
deletion, cursor motion, and closure.

## Supported commands

| Command | Options and behavior |
| --- | --- |
| `label .path` | `-text text` |
| `button .path` | `-text text` and `-command script` |
| `frame .path` | Container for nested widgets |
| `entry .path` | Single-line UTF-8 text, with `-bg white` |
| `pack .path ?path ...?` | `-side top`, `bottom`, `left` or `right`, `-padx pixels`, `-pady pixels`, `-fill none`, `x`, `y` or `both`, and `-expand 0` or `1` |
| `focus ?entry?` | Read or set the focused entry |
| `bind .entry <Return> script` | Set an entry's Enter callback. Inferno's `<Key-\n>` spelling also works |
| `.path configure option value` | Set one or more of that widget's supported options |
| `.path cget option` | Read text, an entry's background, or a button's script |
| `.entry get`, `insert index text`, `delete first ?last?`, `index index`, `icursor index` | Read or edit an entry using decimal character indexes, `insert`, or `end` |
| `.button invoke` | Evaluate the button's script and return its Tcl result |
| `destroy .path ?path ...?` | Remove widgets and their descendants. `destroy .` closes the root |

Click an entry to focus it and position the cursor. Left, Right, Home, End,
Backspace, and Delete work on Unicode code points. Entries hold up to 16 KiB
of text and scroll horizontally as needed to keep the cursor visible. A
left-button press and release inside the same button invokes its script.

The fixed stroke font displays English letters, digits, spaces, `É`, `+`,
`-`, and `.`. Lowercase shares the uppercase glyphs. Other code points display
as `?` and retain their original value in Tcl. Selection, clipboard, grapheme
navigation, broader bindings, themes, additional toplevels, and geometry
managers beyond the listed pack options are outside this subset.
