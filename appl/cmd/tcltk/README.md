# Tk applications on TaijiOS

The standalone [Tk package](https://git.waozi.xyz/ziranlang/tk) provides
`tk/widgets` and `tk/paint`. The launcher calls `Attach` with a
[`tcl/interpreter`](https://git.waozi.xyz/ziranlang/tcl) instance and uses
TaijiOS's `zx_surface` binding to present the RGBA render buffer and receive
window events. The root TaijiOS package manifest selects both packages.

The [Bounce toolbar script](bounce_controls.tcl) adapts the label and count
controls from Inferno's [Bounce demo](../../wm/bounce.b). The buttons run Tcl
scripts that change the count and reconfigure the label. Close runs
`destroy .`. The [Man browser](man_query.tcl) ports the query panel, manual
display, and history from Inferno's manual browser and its lookup library.
This port uses the Inferno [MIT notice](../../../NOTICE).

Man, Coffee and About define `TK_NO_CANVAS` to omit the Canvas widget and its
renderer, leaving more of the default Linux/386 guest memory pool available
for manual pages and Coffee artwork. The general Tk launcher, Memory, and
Graph0 and Directory Browser builds include Canvas.
The general Tk launcher and LINPACK builds define `TK_LISTBOX` to add
listboxes and entry `-width` support. LINPACK omits Canvas. The general
launcher and Directory Browser define `TK_MENU` for menus and menubuttons. The general launcher also
defines `TK_PACKAGES` for the optional Tcl package registry. About,
Directory Browser, and the general launcher define `TK_BITMAP` for image
labels, named images, frame and label appearance, and extended packing options. The launcher registers this Tk subset as
`Tk 0.1`, so a script can use `package require Tk`. Other Tcl script packages
can register via `package ifneeded` or use `pkgIndex.tcl` in a guest directory
added to `auto_path`. The launcher reads these scripts through the guest file
service.

Infernal Coffee keeps all six masked cups, the original background, Stop/Go,
and Rate, Jitter, and Skip sliders. It reads the shipped
`/icons/bigdelight.bit` and `/icons/coffee*` artwork through the same guest file
service as Man. Ziran decodes the compressed images, composites each frame,
and renders the Tk widgets. The guest surface supplies window events and
presents the resulting pixels. [ZX source](coffee_app.zi). The Dis version is
removed; the test compares its paused artwork corner in `coffee_dis_corner.png`.

About Inferno displays the shipped 300×207 `/icons/inferno.bit` and reads up to
128 bytes from the live guest `/dev/sysctl`. The window uses the stock bitmap,
black ridge frame, and orange version label. The version uses the shared stroke
font and the window closes through the guest window manager.
[ZX source](about_app.zi). The Dis version is removed; `test_about.py` compares
the window with the artwork and tkcmd results recorded from it.

Log Window reads a live guest pipe. It starts as a toolbar task and pops up
when a message arrives. Scroll follows the newest lines when checked. Clear it
to keep the current view while new lines arrive, or drag the scrollbar to read
earlier lines. Clear Pop up to keep a tasked window hidden until you restore it
from the toolbar. [ZX source](logwindow_app.zi). The Dis version is removed.

Memory shows the guest's `main`, `heap`, and `image` arenas. It reads
`/dev/memory` on launch and every second. Each row shows used capacity and
the arena limit, the allocation count in the original display units, a red usage
bar, and the high-water mark. The graph uses the shared Ziran Canvas
widget. [ZX source](memory_app.zi). The Dis version is removed; `test_memory.py`
compares the canvas commands with results recorded from Inferno tkcmd.

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
the shared stroke font and plain-text scientific tick labels. The plot area
is 480×384. Graph0 paints and uploads 128 rows at a time in the default
32 MiB guest.
Its connected stroke and markers share one Canvas path. The app computes
data bounds while reading the file and fills the allocated path directly.
[ZX source](graph0_app.zi) · [Inferno source](../../math/graph0.b)

Directory Browser opens a guest directory in the stock icon grid, with the
shipped folder, file, executable and picture bitmaps. Use Options → use
text for file kind, size, modification time and name. The `exe` row kind and
executable icon identify `.dis` modules and `.zx` images. Options also sorts by
name, access or modification time, or size. Click an icon, label or row to
select the entry. Changing views preserves sort order, Walk and selection.
Double-click a directory to open a second Directory Browser. With Walk enabled,
the same action navigates in place, and `..` returns to the parent. The title
follows the current path. Double-click an ordinary file to edit it, a recognized
picture to view it, or a `.dis` or `.zx` file to run it in the guest. ZX images
can launch without filesystem execute bits. The port passes the resolved `.dis`
path directly, avoiding stock Directory Browser's trailing slash load error.
Right-click sends the clicked entry's name and directory to
the guest plumber when available. The status line reports directory and launch
failures. [ZX source](dir_app.zi). The Dis version is removed; its tests compare
with results recorded from it.

## Run in Taiji

From the TaijiOS root, with `ziran`, `zi2zx`, `mk`, Xvfb, `xdotool`, ImageMagick `import`,
Python Pillow, and a matching ZX-enabled Linux/386 emulator and `zxrun`
built from this checkout:

```sh
python3 appl/cmd/tcltk/test_tcltk.py
target="$PWD/zx/tcltk.zx"
(cd appl/cmd && mk "$target")
(cd appl/cmd && mk install-coffee-zx install-man-zx)
python3 appl/cmd/tcltk/test_tcltk.py --installed
python3 appl/cmd/tcltk/test_menu.py --installed
python3 appl/cmd/tcltk/test_radio.py --installed
python3 appl/cmd/tcltk/test_canvas_items.py --installed
python3 appl/cmd/tcltk/test_canvas_images.py --installed
(cd appl/cmd && mk install-about-zx)
python3 appl/cmd/tcltk/test_about.py --installed
python3 appl/cmd/tcltk/test_logwindow.py
(cd appl/cmd && mk install-logwindow-zx)
python3 appl/cmd/tcltk/test_logwindow.py --installed
python3 appl/cmd/tcltk/test_memory.py
install -m 0644 build/tcltk/memory.zx zx/wm/memory.zx
python3 appl/cmd/tcltk/test_memory.py --installed
python3 appl/cmd/tcltk/test_linbench.py
install -m 0644 build/tcltk/linbench.zx zx/math/linbench.zx
python3 appl/cmd/tcltk/test_linbench.py --installed
python3 appl/cmd/tcltk/test_graph0.py
(cd appl/cmd && mk install-graph0-zx)
python3 appl/cmd/tcltk/test_graph0.py --installed
python3 appl/cmd/tcltk/test_dir.py
python3 appl/cmd/tcltk/test_dir_actions.py
(cd appl/cmd && mk install-dir-zx)
python3 appl/cmd/tcltk/test_dir.py --installed
python3 appl/cmd/tcltk/test_dir_actions.py --installed
python3 appl/cmd/tcltk/test_dir_geometry.py --installed
python3 appl/cmd/tcltk/test_cursor.py
```

The general Tk launcher reads guest stdin until EOF and accepts scripts up to
1 MiB. It uses `taijios_stdin.Read` and `zx_surface` from the emulator. In the
Taiji graphical shell run:

```sh
zxrun -w /zx/tcltk.zx < /appl/cmd/tcltk/bounce_controls.tcl
zxrun -w /zx/man.zx
zxrun -w /zx/coffee.zx
zxrun -p -w /zx/wm/logwindow.zx 'System log' < /path/to/log
zxrun -p -w /zx/wm/memory.zx
zxrun -p -w /zx/math/linbench.zx
zxrun -w /zx/math/graph0.zx /path/to/coordinates.xy
zxrun -w /zx/wm/dir.zx /path/to/directory
```

Log Window accepts `-e` to close when input ends. By default it prints `Got EOF`
and keeps the log open. For the original standalone process group, launch with
`zxrun -p -w`. To retain the caller's group, use `zxrun -w` and pass `-g` after
the image path. Both forms accept an optional title.

To start the manual browser directly from the project root:

```sh
Linux/386/bin/emu -r "$PWD" -g 800x600 wm/wm zxrun -w /zx/man.zx
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
scale values and panel commands against `tkcmd`, and verify motion, Stop/Go,
and the artwork corner recorded from the Dis version.
The ZX run also verifies that each slider tracks a held drag, retains its value,
and leaves the paused frame frozen. To run the Coffee tests alone, use
`python3 appl/cmd/tcltk/test_tcltk.py --coffee-only` and add `--installed` to
exercise `/zx/coffee.zx`.

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

`test_radio.py` compares radio buttons and radio and check menu entries with
`tkcmd`. It switches the stock Directory Browser to text, sorts by size, and
toggles Walk while Options stays posted. The hosted test checks that pointer
presses and direct variable writes move the visible selection, that disabled
controls ignore pointer input, and that menu entries and standalone buttons
share one Tk variable. Run without `--installed` to build the launcher first.

`test_dir.py` runs the stock Dis Directory Browser and the Ziran port in
private Xvfb. It compares the default grid pixels, including the four bitmap
types and their labels, then exercises the sort and view commands and Walk
from the icon grid. It compares text rows, all four sort orders, and live
window titles, and checks selection, scrolling and recovery when a directory
in the listing disappears. Run with `--installed` to exercise
`/zx/wm/dir.zx`.

`test_dir_geometry.py` compares the startup Canvas width and the full glyphs
of a 65-character UTF-8 filename with the Dis Directory Browser in private Xvfb.
It also checks that Walk widens the existing window without moving it, and
that the same window can navigate back through `..`. Run with `--installed`
to test `/zx/wm/dir.zx`.

`test_cursor.py` compares `cursor -image` and `cursor -default` with stock
`tkcmd`. It reads the cursor pixels and hotspot from private Xvfb and checks
missing-image and invalid-bitmap errors. The test application attaches the
same optional Ziran cursor adapter as Directory Browser.

`test_dir_actions.py` compares the child Directory Browser, the editor contents,
the picture viewer, and the raw UTF-8 `WmDir` plumbing message in private Xvfb.
It opens copies of the installed About Inferno Dis and ZX apps through
Directory Browser and compares each rendered logo with a direct launch of the
same app. The ZX copy has a UTF-8 filename with a space and mode `0644`. The
test checks that it shares the executable icon and text kind with the Dis
module. Launches use the guest window service. Directory Browser chooses what
to open and formats the plumbing message in Ziran. Run with `--installed` to
test `/zx/wm/dir.zx`.

`test_canvas_items.py` compares tag and item command results with `tkcmd`. It
drives overlapping Canvas items on both the stock and hosted desktops in
private Xvfb and checks shared tag and numeric item callbacks, press and
release, double-click, held-button motion, and the pixels exposed after
deletion. Run without `--installed` to build the runner first.

`test_canvas_images.py` compares image and Canvas geometry commands with
`tkcmd` and checks that deletion releases retained images. It draws the shipped
Directory Browser folder and file icons in private Xvfb and compares their
pixels, mask-only and offset masks, and clicking the transparent part of an item.
Run without `--installed` to build and use a runner in `build/tcltk`.

`test_canvas_viewport.py` compares vertical Canvas commands with `tkcmd` and
uses the Directory Browser's masked folder bitmap and scrollbar wiring in
private Xvfb. It checks pixel clipping, scrollbar arrow and trough presses,
allocated widths, and item hits and coordinates after scrolling. Use
`python3 appl/cmd/tcltk/test_canvas_viewport.py --installed` to test
`/zx/tcltk.zx`.

`test_canvas_distances.py` compares Canvas dimensions, item coordinates, stroke
widths, and scroll distances with `tkcmd`. In private Xvfb it verifies the
Directory Browser's `10c` requested width and compares rendered pixels before
and after a click reconfigures the Canvas. Run without `--installed` to build
and use a runner in `build/tcltk`.

`test_canvas_fonts.py` compares Canvas font selection, metrics, and item
bounds with `tkcmd`. It also compares the pixels and hit area of the shipped
Directory Browser font in private Xvfb. Run without `--installed` to build
and use a runner in `build/tcltk`.

`test_about.py` compares label, bitmap, frame, and packing commands with
`tkcmd`. It opens and closes the stock and ZX About windows, compares all
62,100 logo pixels, and checks that the ZX app updates its version label when the
guest namespace supplies a different `/dev/sysctl`. It also opens a script in
the generic runner and compares the exact foreground pixels of a 1-bit bitmap
after deleting its name. Run without `--installed` to build both ZX apps first.
In the Taiji graphical shell, launch About with `zxrun -w /zx/wm/about.zx`.

## Supported commands

| Command | Options and behavior |
| --- | --- |
| `label .path` | `-text`; with bitmap support, `-label` as an alias, `-bitmap @path` or a name under `/icons/tk`, `-image name`, `-bg` or `-background`, `-fg` or `-foreground`, `-bd` or `-borderwidth`, and `-relief flat`, `raised`, `sunken`, `ridge` or `groove`. `cget -bitmap` and `cget -image` return `0` or `1` |
| `button .path` | `-text text`, `-command script`, and `-state normal` or `disabled` |
| `menubutton .path` | `-text`, `-menu`, and `-state normal` or `disabled`. Press to post, drag to a row, and release to invoke it |
| `menu .path` | `-bd` or `-borderwidth`. A popup may be a child of its menubutton |
| `.menu add type ?options?`, `insert index type ?options?`, `delete first ?last?` | Edit `command`, `separator`, `checkbutton`, and `radiobutton` rows. Selection entries support the options of their widget counterparts and leave the menu posted when invoked with the pointer |
| `.menu entryconfigure index option value`, `entrycget index option` | Change or query options of a command or selection row |
| `.menu index index`, `type index`, `yposition index`, `activate index`, `invoke index` | Query or act on rows by number, `end`, `last`, `active`, `none`, or `@y` |
| `.menu post x y`, `unpost` | Show a popup at application-surface coordinates or dismiss it. An outside press dismisses a posted popup |
| `checkbutton .path` | Button options plus `-label`, `-variable`, `-onvalue`, `-offvalue`, and `-indicatoron`. A left press toggles the value and runs the callback. The default stored values are `1` and `0` |
| `radiobutton .path` | Button options plus `-label`, `-variable`, `-value`, and `-indicatoron`. A left press selects the value and runs the callback. The default variable is `selectedButton`; a standalone button bound to it uses its path by default. A menu radio entry defaults to an empty value |
| `variable name ?value?` | Read or write a Tk root variable shared by standalone buttons and menu entries |
| `frame .path` | Container for nested widgets. With bitmap support, accepts the same color, border width, and relief options as labels |
| `image create bitmap ?name? ?-file bitmap? ?-maskfile mask?`, `image names`, `image width name`, `image height name`, `image type name`, `image delete name ?name ...?` | Create and query named bitmaps. A `k1` mask can accompany the bitmap or supply the shape of a black bitmap. Labels and Canvas items retain their bitmaps when a name is deleted or replaced |
| `entry .path` | Single-line UTF-8 text with `-bg white` and `-width` |
| `text .path` | Wrapped, scrollable text. `-height` sets the requested height. `-yscrollcommand` receives the first and last visible fractions |
| `listbox .path` | Configurable `-width`, `-height`, `-selectmode single` or `browse`, and `-yscrollcommand`. A click selects a row. Up and Down move the active row. Enter or Space selects it |
| `.listbox insert index element ?element ...?`, `delete first ?last?`, `get first ?last?`, `size`, `index index` | Edit or read rows by numeric index, `end`, `active`, `anchor`, or `@x,y` |
| `.listbox activate index`, `curselection`, `selection anchor index`, `selection includes index`, `selection set first ?last?`, `selection clear first ?last?` | Move the active row or read and change selection and its anchor |
| `.listbox see index`, `yview ?index\|moveto fraction\|scroll count units/pages?` | Reveal a row or read and set the vertical viewport |
| `canvas .path` | `-width`, `-height`, `-borderwidth` or `-bd` in screen units, `-background` or `-bg`, `-relief flat` or `sunken`, four-coordinate `-scrollregion`, `-yscrollincrement`, and `-yscrollcommand` |
| `.canvas yview`, `.canvas yview moveto fraction`, `.canvas yview scroll count units\|pages` | Query or move the vertical viewport. A nonpositive rounded increment uses one tenth of the visible height. Page moves use nine tenths of that height. The viewport clips drawing and translates item hit testing |
| `.canvas canvasy screenY ?grid?`, `.canvas cget actwidth`, `.scrollbar cget actwidth` | Convert an absolute Y coordinate to Canvas space, optionally snapping to a pixel grid. Read each widget's allocated interior width |
| `.canvas create rectangle x0 y0 x1 y1 ?options?` | Add a rectangle with `-fill` and `-outline`. Return its numeric item ID |
| `.canvas create text x y ?options?` | Add a label with `-anchor`, `-text`, and `-fill`. With bitmap support, the item inherits the current Canvas font or accepts its own `-font` guest path, with line breaks, bitmap glyph metrics, and viewport clipping. Return its numeric item ID |
| `.canvas configure -font path`, `.canvas cget -font`, `.canvas itemconfigure id -font path`, `.canvas itemcget id -font` | Set or query a packed 1-bit Inferno font. Existing items keep their face when the Canvas font changes. Shared faces stay loaded while any item uses them |
| `.canvas create image x y ?-image name? ?-anchor anchor?` | Add a named bitmap with a center anchor by default. `coords` and `bbox` report its position and bounds. `itemconfigure` changes its anchor or bitmap. `itemcget -image` reports `1` for an attached image or `0` otherwise. Pointer bindings use the full image rectangle, including transparent pixels |
| `.canvas create line x0 y0 x1 y1 ?x y ...? ?options?` | Add a polyline with `-fill` and `-width`. Return its numeric item ID |
| `.canvas create oval x0 y0 x1 y1 ?options?` | Add an oval with `-fill`, `-outline`, and `-width`. Return its numeric item ID |
| `.canvas coords id ?coordinates?`, `.canvas bbox id` | Read or set an item's coordinates with up to four decimal places, or read its pixel bounds using the text item’s font metrics |
| `.canvas itemconfigure id option value`, `.canvas itemcget id -text`, `.canvas itemcget id -width` | Set supported item options or read a text item's label or a line or oval's stroke width |
| `.canvas create type ... -tags list` | Attach named tags to a new item. Item IDs increase within each Canvas, including after deletion. Use `addtag` to attach tags to existing items |
| `.canvas find all`, `.canvas find withtag tagOrId`, `.canvas gettags tagOrId` | List items in stack order or tag membership order. `gettags` reads the topmost match and includes its numeric ID. `find withtag current` returns the item under the pointer |
| `.canvas addtag tag all`, `.canvas addtag tag withtag tagOrId`, `.canvas dtag tagOrId ?tag?`, `.canvas delete ?tagOrId ...?` | Add or remove named tags and delete items by ID, tag, or `all` |
| `.canvas bind tagOrId event ?script?` | Install or query Canvas item bindings for buttons 1 through 3, release, double-click, motion with or without held buttons, and item enter and leave. Dispatch to the topmost hit item's `all`, named-tag, and numeric-ID bindings. `%b`, `%x` and `%y`, `%X` and `%Y`, `%W`, and `%%` supply the button, local and absolute pointer coordinates, widget path, and literal percent sign |
| `bind .canvas <ButtonPress-1> script` | Run a left-press callback. `<Button-1>` is an alias. `%x` and `%y` give coordinates inside the Canvas border |
| `scrollbar .path` | `-orient vertical` or `horizontal`, and `-command`. Arrows and troughs call `scroll` by units and pages. A held thumb drag calls `moveto` |
| `.scrollbar set first last`, `.scrollbar get`, `.scrollbar identify x y` | Update or read clamped viewport fractions and identify the part under local coordinates |
| `scale .path` | `-from`, `-to`, `-resolution`, `-bigincrement`, pixel `-length`, `-orient horizontal` or `vertical`, `-showvalue 0` or `1`, and `-command script` |
| `.scale set value`, `.scale get` | Set or read a fixed-point value with up to three decimal places. `set` quantizes and clamps silently. Pointer drags and trough or arrow-key steps append the changed value to the callback |
| `panel .path` | `-bd` or `-borderwidth` in pixels and `-relief flat`. `Tk.PanelImage` allocates a writable RGBA8 backing image centered and clipped to the panel |
| `.panel dirty ?x0 y0 x1 y1?` | Accept a redraw request for the panel. The surface presents the current pixels on refresh |
| `update` | Request the regular surface refresh after the Tcl evaluation |
| `pack .path ?path ...?` | `-side top`, `bottom`, `left` or `right`, `-padx pixels`, `-pady pixels`, `-fill none`, `x`, `y` or `both`, `-expand 0` or `1`, and `-anchor center`, `n`, `ne`, `e`, `se`, `s`, `sw`, `w` or `nw` |
| `pack .path ... -in frame -ipadx pixels -ipady pixels`, `pack propagate . 0` | With bitmap support, choose a packing container and add internal space. The launcher supplies the root viewport |
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
| `.checkbutton select`, `deselect`, `toggle`, `invoke` | Change selection. `invoke` evaluates the callback after toggling the variable |
| `.radiobutton select`, `deselect`, `invoke` | Store the radio value or clear the variable. `invoke` stores the value and evaluates the callback. Disabled buttons still accept explicit `select` and `deselect` |
| `destroy .path ?path ...?` | Remove widgets and their descendants. `destroy .` closes the root |

Canvas width, height, border, item coordinates, stroke width, scroll region,
and scroll increment accept decimals in pixels or with `c` (centimeters), `m`
(millimeters), `i` (inches), or `p` (points). Inferno uses a fixed 100 pixels per
inch and whole-pixel conversion factors for centimeters and millimeters, so
`10c` is 390 pixels. Layout rounds width, height, and border to whole pixels.
`cget -width` and `cget -height` retain the requested precision.

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

The port implements a subset of 20 of the 25 commands advertised by the
[Limbo Tcl/Tk bridge](../../lib/tcl_tk.b). The remaining five are `bitmap`,
`grab`, `lower`, `raise`, and `toplevel`. The shipped engine
exposes bitmap loading through widget options and the `image` command.
The [Inferno Tk engine](../../../libtk/utils.c) also supplies `panel`, now
available in Ziran with the backing-image and redraw subset above. Its other
commands include `choicebutton`, `grid`, `send`, and `winfo`. Directory Browser
attaches an optional `cursor` command for `-image name` and `-default`. The
hosted bridge supports byte-aligned, 1-bit cursor shapes up to 32 by 32 pixels
with a negative or zero hotspot offset. The other stock cursor options are
still outside this subset.

Menus still need cascade entries, `-postcommand`, keyboard navigation,
autoscroll, and the wider visual options. Posted menus share the root's pixel
buffer. Separate windows
and screen-relative posting depend on addressable guest surfaces.
The remaining scale API includes coordinate-based `get`, `coords`,
`identify`, `-jump`, `-label`, tick marks, slider size and relief, and trough
autorepeat. The remaining panel API includes `-anchor`, `origin`,
`panelx`/`panely`, `screenx`/`screeny`, mattes, and partial damage tracking.
Frame propagation, `pack forget`, case-insensitive text search, marks,
embedded windows, editable selections, and the wider tag API remain open.
The bitmap reader supports compressed and uncompressed Inferno `m8` and `k1`
files with up to 262,144 pixels each. The registry holds up to 32 live bitmaps
across file-backed labels and named references, including Canvas items retaining
a deleted name. Other channels, masks with more than one bit per pixel, legacy
bitmap headers outside 1-bit subfonts, and the `<fd` form remain open.
Label and frame colors use the Canvas color subset. Bitmap fonts currently
apply to Canvas text. Subfonts with more than one bit per pixel and font
options on other widget types remain open.
Selection buttons still need keyboard activation and wider style options.
Scrollbars still need `activate`, `delta`, `fraction`, `-jump`, and hold autorepeat.
Canvas still needs stacking commands, geometric `find` and `addtag` selectors,
group item configuration by tag, key bindings, additive and subtractive
bindings, item grab and focus, `xview`, `canvasx`, `see`, polygon and arc items,
embedded windows, richer font, color, join and cap options,
and `cget -background`.
Directory Browser widens its icon view to fit the longest filename at
startup and during Walk, within the space available on the guest desktop.
The stock browser matches startup geometry. The stock Walk probe into the
same long-name directory hit a nil dereference during reconfiguration.
Directory Browser uses the shipped `cursor.wait` bitmap while opening a
selection and restores the default cursor when the action returns.

The text widget still needs horizontal scrolling and `-xscrollcommand`.
The Tk variable command still needs Inferno's `lasterror` query.
The remaining listbox API includes `nearest`, `xview`, `-xscrollcommand`,
`-selectborderwidth`, multiple and extended selection, and drag autoscroll.
Unicode Browser uses the supported listbox commands and also needs separate
windows, clipboard access, and bitmap font rendering. [Inferno source](../../wm/unibrowse.b)
See the [Tcl command comparison](../../lib/tcl.md#comparison-with-shipped-inferno-tcl)
for the headless interpreter.
