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

Man and Coffee define `TAIJI_TK_NO_CANVAS` to omit the Canvas widget and its
renderer, leaving more of the default Linux/386 guest memory pool available
for manual pages and Coffee artwork. The general Tk launcher, Memory, and
Graph0 builds include Canvas.
The general Tk launcher and LINPACK builds define `TAIJI_TK_LISTBOX` to add
listboxes and entry `-width` support. LINPACK omits Canvas. The general launcher
also defines `TAIJI_TK_MENU` for menus and menubuttons and `TAIJI_TK_PACKAGES`
for the optional Tcl package registry. The launcher registers this Tk subset as
`Tk 0.1`, so a script can use `package require Tk`. Other Tcl script packages
can register via `package ifneeded` or use `pkgIndex.tcl` in a guest directory
added to `auto_path`. The launcher reads these scripts through the guest file
service.

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

Memory shows the guest's `main`, `heap`, and `image` arenas. It reads
`/dev/memory` on launch and every second. Each row shows used capacity and
the arena limit, the allocation count in the original display units, a red usage
bar, and the high-water mark. The graph uses the shared Ziran Canvas
widget. [ZX source](memory_app.zi) · [Inferno source](../../wm/memory.b)

LINPACK opens with matrix order 200. Edit the order and press Run to generate
the original deterministic matrix, factor it with partial pivoting, solve it,
and check the normalized residual. The benchmark times factorization and the
solve, then adds Mflops and elapsed seconds to the selectable results list.
The scrollbar gives access to earlier results. The button shows Running while
the app works in batches and accepts orders from 1 to 320. Timing depends on
the execution engine and clock resolution.
[ZX source](linbench_app.zi) · [Inferno source](../../math/linbench.b)

Graph0 reads whitespace-separated X and Y coordinates from a guest file. It
scales the axes to the data, draws ticks and circular markers, and connects
the points in file order. Click inside the plot to read the data coordinates
at the pointer. The port accepts up to 3,072 pairs in a 32 KiB file and uses
the shared stroke font and plain-text scientific tick labels. It scales the
plot area to 480×384 to fit full-frame uploads in the default 32 MiB guest.
Its connected stroke and markers share one Canvas path. The app computes
data bounds while reading the file and fills the allocated path directly.
[ZX source](graph0_app.zi) · [Inferno source](../../math/graph0.b)

## Run in Taiji

From the TaijiOS root, with `zi2zx`, `mk`, Xvfb, `xdotool`, ImageMagick `import`,
Python Pillow, and a ZX-enabled Linux/386 emulator built from this checkout:

```sh
python3 appl/cmd/tcltk/test_tcltk.py
target="$PWD/dis/tcltk.zx"
(cd appl/cmd && mk "$target")
(cd appl/cmd && mk install-coffee-zx install-man-zx)
python3 appl/cmd/tcltk/test_tcltk.py --installed
python3 appl/cmd/tcltk/test_menu.py --installed
python3 appl/cmd/tcltk/test_logwindow.py
(cd appl/cmd && mk install-logwindow-zx)
python3 appl/cmd/tcltk/test_logwindow.py --installed
python3 appl/cmd/tcltk/test_memory.py
install -m 0644 build/tcltk/memory.zx dis/wm/memory.zx
python3 appl/cmd/tcltk/test_memory.py --installed
python3 appl/cmd/tcltk/test_linbench.py
install -m 0644 build/tcltk/linbench.zx dis/math/linbench.zx
python3 appl/cmd/tcltk/test_linbench.py --installed
python3 appl/cmd/tcltk/test_graph0.py
(cd appl/cmd && mk install-graph0-zx)
python3 appl/cmd/tcltk/test_graph0.py --installed
```

The general Tk launcher reads guest stdin until EOF and accepts scripts up to
1 MiB. It uses `taijios_stdin.Read` and `zx_surface` from the emulator. In the
Taiji graphical shell run:

```sh
zxrun -w /dis/tcltk.zx < /appl/cmd/tcltk/bounce_controls.tcl
zxrun -w /dis/man.zx
zxrun -w /dis/coffee.zx
zxrun -p -w /dis/wm/logwindow.zx 'System log' < /path/to/log
zxrun -p -w /dis/wm/memory.zx
zxrun -p -w /dis/math/linbench.zx
zxrun -w /dis/math/graph0.zx /path/to/coordinates.xy
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

`test_memory.py` compares Canvas command results with Inferno `tkcmd`. It
launches the original and ZX Memory apps under private Xvfb, swaps in a new
arena snapshot through the guest namespace, and checks usage bar and
high-water mark positions, refreshed size labels, and window close. It also
launches the ZX app against the guest's real `/dev/memory`.

`test_linbench.py` compares the listbox command transcript with `tkcmd`
including UTF-8 rows, selection ranges, and scrollbar callbacks. It checks
the solution and residual for several matrix orders directly in the Ziran
engine. Under private Xvfb it drives the original Dis benchmark and the ZX
benchmark through runs, new results, scrollbar arrows and dragging, row
selection, and close. The hosted test also covers invalid order recovery
and reruns at the upper supported order.

`test_graph0.py` compares decimal Canvas commands with `tkcmd` and runs the
original Dis plotter and the ZX port in private Xvfb. It checks axis positions,
tick labels, connected data points, circular markers, click readouts and close.
It also runs the hosted plot at its supported point limit and checks that an
oversized dataset exits with an error.

`test_menu.py` compares menu and menubutton results with `tkcmd`. It marks the
first cell in the shipped Sweeper and resets it through Options → restart. The
hosted test exercises the same press, drag, and release sequence, including the
callback redraw, disabled items, separators, outside dismissal, and direct
posting. It also loads `Tk 0.1` and discovers a separate Tcl script package from
the guest namespace through `auto_path`. Run without `--installed` to build the launcher first.

## Supported commands

| Command | Options and behavior |
| --- | --- |
| `label .path` | `-text text` |
| `button .path` | `-text text`, `-command script`, and `-state normal` or `disabled` |
| `menubutton .path` | `-text`, `-menu`, and `-state normal` or `disabled`. Press to post, drag to a row, and release to invoke it |
| `menu .path` | `-bd` or `-borderwidth`. A popup may be a child of its menubutton |
| `.menu add type ?options?`, `insert index type ?options?`, `delete first ?last?` | Edit command and separator rows. Command options include `-label` or `-text`, `-command`, and `-state` |
| `.menu entryconfigure index option value`, `entrycget index option` | Change or query a command row |
| `.menu index index`, `type index`, `yposition index`, `activate index`, `invoke index` | Query or act on rows by number, `end`, `last`, `active`, `none`, or `@y` |
| `.menu post x y`, `unpost` | Show a popup at application-surface coordinates or dismiss it. An outside press dismisses a posted popup |
| `checkbutton .path` | Button options plus `-variable`, `-onvalue`, and `-offvalue`. A left press toggles the value and runs the callback |
| `variable name ?value?` | Read or write the Tk variable associated with one or more checkbuttons |
| `frame .path` | Container for nested widgets |
| `entry .path` | Single-line UTF-8 text with `-bg white` and `-width` |
| `text .path` | Wrapped, scrollable text. `-height` sets the requested height. `-yscrollcommand` receives the first and last visible fractions |
| `listbox .path` | Configurable `-width`, `-height`, `-selectmode single` or `browse`, and `-yscrollcommand`. A click selects a row. Up and Down move the active row. Enter or Space selects it |
| `.listbox insert index element ?element ...?`, `delete first ?last?`, `get first ?last?`, `size`, `index index` | Edit or read rows by numeric index, `end`, `active`, `anchor`, or `@x,y` |
| `.listbox activate index`, `curselection`, `selection anchor index`, `selection includes index`, `selection set first ?last?`, `selection clear first ?last?` | Move the active row or read and change selection and its anchor |
| `.listbox see index`, `yview ?index\|moveto fraction\|scroll count units/pages?` | Reveal a row or read and set the vertical viewport |
| `canvas .path` | Integer-pixel `-width`, `-height`, `-borderwidth` or `-bd`, `-background` or `-bg`, and `-relief flat` or `sunken` |
| `.canvas create rectangle x0 y0 x1 y1 ?options?` | Add a rectangle with `-fill` and `-outline`. Return its numeric item ID |
| `.canvas create text x y ?options?` | Add a single-line stroke-font label with `-anchor`, `-text`, and `-fill`. Return its numeric item ID |
| `.canvas create line x0 y0 x1 y1 ?x y ...? ?options?` | Add a polyline with `-fill` and `-width`. Return its numeric item ID |
| `.canvas create oval x0 y0 x1 y1 ?options?` | Add an oval with `-fill`, `-outline`, and `-width`. Return its numeric item ID |
| `.canvas coords id ?coordinates?`, `.canvas bbox id` | Read or set an item's coordinates with up to four decimal places, or read its pixel bounds using Ziran font metrics for text |
| `.canvas itemconfigure id option value`, `.canvas itemcget id -text`, `.canvas itemcget id -width` | Set supported item options or read a text item's label or a line or oval's stroke width |
| `bind .canvas <ButtonPress-1> script` | Run a left-press callback. `<Button-1>` is an alias. `%x` and `%y` give coordinates inside the Canvas border |
| `scrollbar .path` | `-orient vertical` or `horizontal`, and `-command`. Arrows and troughs call `scroll` by units and pages. A held thumb drag calls `moveto` |
| `.scrollbar set first last`, `.scrollbar get`, `.scrollbar identify x y` | Update or read clamped viewport fractions and identify the part under local coordinates |
| `scale .path` | `-from`, `-to`, `-resolution`, `-bigincrement`, pixel `-length`, `-orient horizontal` or `vertical`, `-showvalue 0` or `1`, and `-command script` |
| `.scale set value`, `.scale get` | Set or read a fixed-point value with up to three decimal places. `set` quantizes and clamps silently. Pointer drags and trough or arrow-key steps append the changed value to the callback |
| `panel .path` | `-bd` or `-borderwidth` in pixels and `-relief flat`. `Tk.PanelImage` allocates a writable RGBA8 backing image centered and clipped to the panel |
| `.panel dirty ?x0 y0 x1 y1?` | Accept a redraw request for the panel. The surface presents the current pixels on refresh |
| `update` | Request the regular surface refresh after the Tcl evaluation |
| `pack .path ?path ...?` | `-side top`, `bottom`, `left` or `right`, `-padx pixels`, `-pady pixels`, `-fill none`, `x`, `y` or `both`, `-expand 0` or `1`, and `-anchor center`, `n`, `ne`, `e`, `se`, `s`, `sw`, `w` or `nw` |
| `focus ?path?` | Read or set the focused entry, text view, scale, or listbox |
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
Canvas item colors accept black, white, red, green, blue, `#RRGGBB`, and the
empty string for transparency.

### Comparison with shipped Inferno Tk

The port implements a subset of 18 of the 25 commands advertised by the
[Limbo Tcl/Tk bridge](../../lib/tcl_tk.b). The remaining seven are `bitmap`,
`grab`, `image`, `lower`, `radiobutton`, `raise`, and `toplevel`.
The [Inferno Tk engine](../../../libtk/utils.c) also supplies `panel`, now
available in Ziran with the backing-image and redraw subset above. Its other
commands include `choicebutton`, `cursor`, `grid`, `send`, and `winfo`.

Menus still need cascade, checkbutton and radiobutton entries, `-postcommand`,
keyboard navigation, autoscroll, and the wider visual options. Graphical
menus currently share the root's pixel buffer when posted. Separate windows
and screen-relative posting depend on addressable guest surfaces.
The remaining scale API includes coordinate-based `get`, `coords`,
`identify`, `-jump`, `-label`, tick marks, slider size and relief, and trough
autorepeat. The remaining panel API includes `-anchor`, `origin`,
`panelx`/`panely`, `screenx`/`screeny`, mattes, and partial damage tracking.
`pack forget` and `pack propagate`, case-insensitive text search, marks,
embedded windows, editable selections, and the wider tag API remain open.
Checkbutton indicator customization and keyboard activation, scrollbar
`activate`, `delta`, `fraction`, `-jump`, and hold autorepeat remain open.
Canvas still needs tags, item bindings and hit testing, item deletion and
stacking, scrolling, polygon and arc items, images, embedded windows,
physical-unit coordinates, more font, color, join and cap options, and
additional pointer bindings. Canvas background can be configured, and
`cget -background` remains open.
The text widget still needs horizontal scrolling and `-xscrollcommand`.
The Tk variable command still needs Inferno's `lasterror` query.
The remaining listbox API includes `nearest`, `xview`, `-xscrollcommand`,
`-selectborderwidth`, multiple and extended selection, and drag autoscroll.
Unicode Browser uses the supported listbox commands and also needs separate
windows, clipboard access, and bitmap font rendering. [Inferno source](../../wm/unibrowse.b)
See the [Tcl command comparison](../../lib/tcl.md#comparison-with-shipped-inferno-tcl)
for the headless interpreter.
