# Tk for Ziran Tcl

Import `tcl_tk` and call `Attach` with a Tcl interpreter to enable Tk commands.
The package manages one root `.` and up to 32 widgets under it. The separate
renderer draws the widgets into an RGBA pixel buffer. The Taiji launcher
uses `zx_surface` to open the window, present those pixels and receive events.
The Tcl core runs headless on its own.

The [Bounce toolbar script](bounce_controls.tcl) adapts the label and count
controls from Inferno's [Bounce demo](../../wm/bounce.b). The buttons run Tcl
scripts that change the count and reconfigure the label. Close runs
`destroy .`. The [Man browser](man_query.tcl) ports the query panel, manual
display, and history from Inferno's [manual browser](../../wm/man.b) and
[lookup library](../../lib/man.b). This port uses the Inferno
[MIT notice](../../../NOTICE).

Infernal Coffee keeps all six masked cups, the original background, Stop/Go,
and Rate, Jitter, and Skip sliders. It reads the shipped
`/icons/bigdelight.bit` and `/icons/coffee*` artwork through the same guest file
service as Man. Ziran decodes the compressed images, composites each frame,
and renders the Tk widgets. The guest surface supplies window events and
presents the resulting pixels. [ZX source](coffee_app.zi) · [Inferno source](../../wm/coffee.b)

Log Window reads a live guest pipe. It starts as a toolbar task and pops up
when a message arrives. Scroll follows the newest lines when checked. Clear it
to keep the current view while new lines arrive, or drag the scrollbar to read
earlier lines. Clear Pop up to keep a tasked window hidden until you restore it
from the toolbar. [ZX source](logwindow_app.zi) · [Inferno source](../../wm/logwindow.b)

## Run in Taiji

From the TaijiOS root, with `zi2zx`, `mk`, Xvfb, `xdotool`, ImageMagick `import`,
Python Pillow, and a ZX-enabled Linux/386 emulator built from this checkout:

```sh
python3 appl/cmd/tcltk/test_tcltk.py
install -m 0644 build/tcltk/tcltk.zx dis/tcltk.zx
install -m 0644 build/tcltk/man.zx dis/man.zx
(cd appl/cmd && mk install-coffee-zx)
python3 appl/cmd/tcltk/test_tcltk.py --installed
python3 appl/cmd/tcltk/test_logwindow.py
(cd appl/cmd && mk install-logwindow-zx)
python3 appl/cmd/tcltk/test_logwindow.py --installed
```

The general Tk launcher reads guest stdin until EOF and accepts scripts up to
1 MiB. It uses `taijios_stdin.Read` and `zx_surface` from the emulator. In the
Taiji graphical shell run:

```sh
zxrun -w /dis/tcltk.zx < /appl/cmd/tcltk/bounce_controls.tcl
zxrun -w /dis/man.zx
zxrun -w /dis/coffee.zx
zxrun -p -w /dis/wm/logwindow.zx 'System log' < /path/to/log
```

Log Window accepts `-e` to close when input ends. By default it prints `Got EOF`
and keeps the log open. For the original standalone process group, launch with
`zxrun -p -w`. To retain the caller's group, use `zxrun -w` and pass `-g` after
the image path. Both forms accept an optional title.

To start the manual browser directly from the project root:

```sh
Linux/386/bin/emu -r "$PWD" -g 800x600 wm/wm zxrun -w /dis/man.zx
```

Man opens `man(1)` on startup. Enter a topic such as `ls`, `lc(1)`, or `2 sys-open`.
Search and Enter both use the guest's actual `/man/1/INDEX` through
`/man/10/INDEX`. The viewer opens aliases and literal page filenames, lists
ambiguous matches by page and section, and displays a message for invalid,
missing, or unreadable results. Enter one of the listed page names to open it.
Click an underlined `topic(section)` reference to open that manual. Back and
Next restore the query, scroll position, and last highlighted match. Use the
Page Up and Page Down buttons, or click the document and use those keys,
Up/Down, Home, and End.

Enter `/term` to search forward in the current page or `?term` to search
backward. Enter or Search continues from the last match and wraps at the end
of the page. Search matches literal, case-sensitive text. A missing term shows
`No match` and preserves the current position and highlight.

The browser reads its Tcl UI from `/appl/cmd/tcltk/man_query.tcl` and formats
the installed manual sources as wrapped plain text. It handles the common
Inferno man macros for headings, paragraphs, inline styles, and examples.
Cross-references use the `.IR` macro as in Inferno Man. Plumbing and full
roff layout are outside this port.

### Guest file service

Man and Coffee use `taijios_files.ReadAt(path: string, offset: s64, buffer: []u8)
-> s32`. Each call opens the path for reading in the caller's guest namespace,
reads up to 4096 bytes at the given offset, and closes it. The result is the
byte count, `0` at EOF or for a zero-length buffer, `-2` for a missing path,
or `-1` for another error.
Negative results leave the caller's buffer intact. The service requires the
emulator build containing `emu/port/zx.c`'s `taijios_files` binding.

The tests compare the same widget commands with Inferno `tkcmd`. On private
Xvfb they exercise Bounce, the UTF-8 entry, manual lookup, a real manual link,
forward and backward text search, missing results, and history and scroll
restoration. A hosted probe checks namespace mounts, file offsets and errors,
and representative content from the real manuals. For Coffee, the tests compare
scale values and panel commands against `tkcmd`, run the original `wm/coffee`
alongside separate ZX runs, and verify motion, Stop/Go, and matching artwork.
The ZX run also verifies that each slider tracks a held drag, retains its value,
and leaves the paused frame frozen. To run the Coffee tests alone, use
`python3 appl/cmd/tcltk/test_tcltk.py --coffee-only` and add `--installed` to
exercise `/dis/coffee.zx`.

`test_logwindow.py` compares the Tk model with Inferno `tkcmd` and runs the
original and hosted Log Window against a live guest pipe in a private WM
session. It checks the two toggles while the stream is idle, dragging the
scrollbar, toolbar task and restore, the title operand, and both EOF modes.
The hosted run verifies continued display after more than 256 KiB of input.
The stream model checks split UTF-8, idle and failed reads, and passes log
text directly to the Tk text buffer. Run `--oracle-only` to compare the model and the
original Dis app without the windowed ZX host bindings.

## Supported commands

| Command | Options and behavior |
| --- | --- |
| `label .path` | `-text text` |
| `button .path` | `-text text`, `-command script`, and `-state normal` or `disabled` |
| `checkbutton .path` | Button options plus `-variable`, `-onvalue`, and `-offvalue`. A left press toggles the value and runs the callback |
| `variable name ?value?` | Read or write the Tk variable associated with one or more checkbuttons |
| `frame .path` | Container for nested widgets |
| `entry .path` | Single-line UTF-8 text, with `-bg white` |
| `text .path` | Wrapped, scrollable text. `-height` sets the requested height. `-yscrollcommand` receives the first and last visible fractions |
| `scrollbar .path` | `-orient vertical` or `horizontal`, and `-command`. Arrows and troughs call `scroll` by units and pages. A held thumb drag calls `moveto` |
| `.scrollbar set first last`, `.scrollbar get`, `.scrollbar identify x y` | Update or read clamped viewport fractions and identify the part under local coordinates |
| `scale .path` | `-from`, `-to`, `-resolution`, `-bigincrement`, pixel `-length`, `-orient horizontal` or `vertical`, `-showvalue 0` or `1`, and `-command script` |
| `.scale set value`, `.scale get` | Set or read a fixed-point value with up to three decimal places. `set` quantizes and clamps silently. Pointer drags and trough or arrow-key steps append the changed value to the callback |
| `panel .path` | `-bd` or `-borderwidth` in pixels and `-relief flat`. `Tk.PanelImage` allocates a writable RGBA8 backing image centered and clipped to the panel |
| `.panel dirty ?x0 y0 x1 y1?` | Accept a redraw request for the panel. The surface presents the current pixels on refresh |
| `update` | Request the regular surface refresh after the Tcl evaluation |
| `pack .path ?path ...?` | `-side top`, `bottom`, `left` or `right`, `-padx pixels`, `-pady pixels`, `-fill none`, `x`, `y` or `both`, `-expand 0` or `1`, and `-anchor center`, `n`, `ne`, `e`, `se`, `s`, `sw`, `w` or `nw` |
| `focus ?path?` | Read or set the focused entry, text view, or scale |
| `bind .entry <Return> script` | Set an entry's Enter callback. Inferno's `<Key-\n>` spelling also works |
| `.path configure option value` | Set one or more of that widget's supported options |
| `.path cget option` | Read a supported option from the widget |
| `.entry get`, `insert index text`, `delete first ?last?`, `index index`, `icursor index` | Read or edit an entry using decimal character indexes, `insert`, or `end` |
| `.text get first ?last?`, `insert end text`, `delete 1.0 end` | Read one character or a range, append text, or clear the document |
| `.text index index`, `see index` | Normalize an index or scroll to reveal it. Indexes are `line.column`, `end`, or `@x,y` relative to the widget. Logical indexes accept `+Nc` and `-Nc`. Columns count Unicode code points |
| `.text search ?-forwards\|-backwards? ?-exact? ?--? pattern start ?stop?` | Return the first matching index or an empty string. Literal search wraps unless given a stop index |
| `.text tag add name first last`, `tag remove name 1.0 end` | Mark a range or clear a tag's ranges. `sel` highlights its ranges |
| `.text tag configure name -underline 0\|1`, `tag bind name <ButtonRelease-1> script` | Underline tagged ranges or bind a click to them. `%x` and `%y` give widget-relative coordinates |
| `.text yview ?moveto fraction\|scroll count units\|pages?` | Read viewport fractions or scroll by a fraction, lines, or pages |
| `.button invoke` | Evaluate the button's script and return its Tcl result |
| `.checkbutton select`, `deselect`, `toggle`, `invoke` | Change selection. `invoke` also evaluates the callback after updating the variable |
| `destroy .path ?path ...?` | Remove widgets and their descendants. `destroy .` closes the root |

Click an entry to focus it and position the cursor. Left, Right, Home, End,
Backspace, and Delete work on Unicode code points. Entries hold up to 16 KiB
of text and scroll horizontally as needed to keep the cursor visible. A
left-button press and release inside the same button invokes its script.

The fixed stroke font displays English letters, digits, spaces, `É`, and
common punctuation. Lowercase shares the uppercase glyphs. Other code points display
as `?` and retain their original value in Tcl. Mouse selection, clipboard,
grapheme navigation, and broader bindings are outside this subset.

### Comparison with shipped Inferno Tk

The port implements a subset of 14 of the 25 commands advertised by the
[Limbo Tcl/Tk bridge](../../lib/tcl_tk.b). The remaining 11 are `bitmap`,
`canvas`, `grab`, `image`, `listbox`, `lower`, `menu`, `menubutton`,
`radiobutton`, `raise`, and `toplevel`.
The [Inferno Tk engine](../../../libtk/utils.c) also supplies `panel`, now
available in Ziran with the backing-image and redraw subset above. Its other
commands include `choicebutton`, `cursor`, `grid`, `send`, and `winfo`.

The remaining scale API includes coordinate-based `get`, `coords`,
`identify`, `-jump`, `-label`, tick marks, slider size and relief, and trough
autorepeat. The remaining panel API includes `-anchor`, `origin`,
`panelx`/`panely`, `screenx`/`screeny`, mattes, and partial damage tracking.
`pack forget` and `pack propagate`, case-insensitive text search, marks,
embedded windows, editable selections, and the wider tag API remain open.
Checkbutton indicator customization and keyboard activation, scrollbar
`activate`, `delta`, `fraction`, `-jump`, and hold autorepeat remain open.
The text widget still needs horizontal scrolling and `-xscrollcommand`.
The Tk variable command still needs Inferno's `lasterror` query.
`listbox` with `curselection`, `get`, `yview`, and its scroll callback is used
by [Unicode Browser](../../wm/unibrowse.b).
See the [Tcl command comparison](../../lib/tcl.md#comparison-with-shipped-inferno-tcl)
for the headless interpreter.
