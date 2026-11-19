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

## Run in Taiji

From the TaijiOS root, with `zi2zx`, Xvfb, `xdotool`, ImageMagick `import`,
Python Pillow, and a ZX-enabled Linux/386 emulator built from this checkout:

```sh
python3 appl/cmd/tcltk/test_tcltk.py
install -m 0644 build/tcltk/tcltk.zx dis/tcltk.zx
install -m 0644 build/tcltk/man.zx dis/man.zx
python3 appl/cmd/tcltk/test_tcltk.py --installed
```

The general Tk launcher reads guest stdin until EOF and accepts scripts up to
1 MiB. It uses `taijios_stdin.Read` and `zx_surface` from the emulator. In the
Taiji graphical shell run:

```sh
zxrun -w /dis/tcltk.zx < /appl/cmd/tcltk/bounce_controls.tcl
zxrun -w /dis/man.zx
```

To start the manual browser directly from the project root:

```sh
Linux/386/bin/emu -r "$PWD" -g 800x600 wm/wm zxrun -w /dis/man.zx
```

Man opens `man(1)` on startup. Enter a topic such as `ls`, `lc(1)`, or `2 sys-open`.
Search and Enter both use the guest's actual `/man/1/INDEX` through
`/man/10/INDEX`. The viewer opens aliases and literal page filenames, lists
ambiguous matches by page and section, and displays a message for invalid,
missing, or unreadable results. Enter one of the listed page names to open it.
Back and Next restore the query and scroll position. Use the Page Up and Page
Down buttons, or click the document and use those keys, Up/Down, Home, and End.

The browser reads its Tcl UI from `/appl/cmd/tcltk/man_query.tcl` and formats
the installed manual sources as wrapped plain text. It handles the common
Inferno man macros for headings, paragraphs, inline styles, and examples.
Clickable cross-references, in-page text search, plumbing, and full roff layout
are outside this port.

### Guest file service

The browser uses `taijios_files.ReadAt(path: string, offset: s64, buffer: []u8)
-> s32`. Each call opens the path for reading in the caller's guest namespace,
reads up to 4096 bytes at the given offset, and closes it. The result is the
byte count, `0` at EOF or for a zero-length buffer, `-2` for a missing path,
or `-1` for another error.
Negative results leave the caller's buffer intact. The service requires the
emulator build containing `emu/port/zx.c`'s `taijios_files` binding.

The tests compare the same widget commands with Inferno `tkcmd`. On private
Xvfb they exercise Bounce, the UTF-8 entry, and manual lookup, missing-result
recovery, history and scrolling. A hosted probe checks namespace mounts,
file offsets and errors, and representative content from the real manuals.

## Supported commands

| Command | Options and behavior |
| --- | --- |
| `label .path` | `-text text` |
| `button .path` | `-text text`, `-command script`, and `-state normal` or `disabled` |
| `frame .path` | Container for nested widgets |
| `entry .path` | Single-line UTF-8 text, with `-bg white` |
| `text .path` | Wrapped, scrollable text. Tcl scripts supply the text |
| `pack .path ?path ...?` | `-side top`, `bottom`, `left` or `right`, `-padx pixels`, `-pady pixels`, `-fill none`, `x`, `y` or `both`, and `-expand 0` or `1` |
| `focus ?path?` | Read or set the focused entry or text view |
| `bind .entry <Return> script` | Set an entry's Enter callback. Inferno's `<Key-\n>` spelling also works |
| `.path configure option value` | Set one or more of that widget's supported options |
| `.path cget option` | Read text, an entry's background, or a button's script |
| `.entry get`, `insert index text`, `delete first ?last?`, `index index`, `icursor index` | Read or edit an entry using decimal character indexes, `insert`, or `end` |
| `.text get 1.0 end`, `insert end text`, `delete 1.0 end` | Read, append to, or clear the text |
| `.text yview ?moveto fraction\|scroll count units\|pages?` | Read viewport fractions or scroll by a fraction, lines, or pages |
| `.button invoke` | Evaluate the button's script and return its Tcl result |
| `destroy .path ?path ...?` | Remove widgets and their descendants. `destroy .` closes the root |

Click an entry to focus it and position the cursor. Left, Right, Home, End,
Backspace, and Delete work on Unicode code points. Entries hold up to 16 KiB
of text and scroll horizontally as needed to keep the cursor visible. A
left-button press and release inside the same button invokes its script.

The fixed stroke font displays English letters, digits, spaces, `É`, and
common punctuation. Lowercase shares the uppercase glyphs. Other code points display
as `?` and retain their original value in Tcl. Selection, clipboard, grapheme
navigation, broader bindings, themes, additional toplevels, and geometry
managers beyond the listed pack options are outside this subset.
