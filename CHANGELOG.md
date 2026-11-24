# Changelog

## Unreleased

- Ship Readmail and Telnet only as ZX and remove their Dis versions. Readmail keeps POP3 over `taijios_dial` with APOP MD5 challenge-response (`taijios_keyring`) and USER/PASS login, `STAT`/`RETR`/`DELE`/`TOP` headers browser, Prev/Next navigation, Reply/Forward launching `/dis/wm/sendmail.zx`, and Save via `/dis/wm/filename.zx`; Telnet keeps TCP dialing, RFC854 IAC option negotiation (`Binary`, `Echo`, `SGA`, `Term` `"dumb"`, `Line Mode`, `AYT`), CR/LF mapping, Hold mode, `^H`/`^W`/`^U`/`^D` editing, and Cut/Paste/Snarf/Send with `/chan/snarf`.

- Ship Sendmail only as ZX and remove its Dis version. It keeps Connect/Disconnect over `taijios_dial` (SMTP `HELO`, `MAIL FROM`, `RCPT TO`, CC list, `DATA`, `Subject`, `QUIT`), No CC, New, Save via `/dis/wm/filename.zx`, reply header prefill from Readmail, and `/usr/<user>/mail/{smtpserver,domain}` defaults.

- Ship AVI Player and WmPlay only as ZX and remove their Dis versions. AVI Player keeps File (via `/dis/wm/filename.zx`), Stop, Pause, Play, and 8-bit uncompressed and BI_RLE8 RIFF/AVI decoding; WmPlay keeps Inferno audio header validation (`rate` magic, `\n\n` terminator, 4-byte alignment), `/dev/audioctl` setup, `/dev/audio` streaming and file selection.

- Ship Unibrowse (Unicode Browser) only as ZX and remove its Dis version. It keeps By Category (`/lib/unidata/blocks.txt`), By number (hex lookup), Symbol wordsearch (`/lib/unidata/index2.txt`), Font information (with font chooser), the 3 by 8 glyph table with Next/Prev paging, and the Character Inspector (`/lib/unidata/unidata2.txt`, 22 category names, Snarf and Paste).

- Ship Edit only as ZX and remove its Dis version. It keeps File (New, Open... via the ZX File Chooser, Save, Save As..., Exit with dirty-discard confirmation), Edit (Cut, Copy, Paste synced with `/chan/snarf` and button-2 popup), Search (Find..., Replace with..., Find Again, Find and Replace, Find and Replace All), and Options (Limbo keyword/comment syntax highlighting with auto-indent, and configurable Indent).

- Ship Reversi only as ZX and remove its Dis version. It keeps the 8 by 8 board, ring-weight and corner-line alpha-beta minimax at full default level 6, Black and White Human/Machine menus, level entries, last move replay, and `-a`, `-p` and `-s` flags; the model replays a complete 63-1 game recorded from the Dis version and matches its minimax evaluations and leaf counts.

- Ship Mand (Fractals) only as ZX and remove its Dis version. It keeps the 60-bit fixed-point Mandelbrot and Julia sets, the 256-entry RGB colour cube (`[R [G [B]]]`), the Green's-theorem contour-crawl Fill toggle, the Depth divisor entry, button-1 drag-rectangle zoom, button-2 Julia selection, and button-3 view-stack zoom-out.

- Ship Collide only as ZX and remove its Dis version. It keeps the cube, sphere and ellipsoid surrounds (`-c`, `-s`, `-e`), flat mode (`-f`), orthographic and perspective projections (`-o`, `-p`), object counts (`-b`, `-v`), pairwise equal-mass elastic collisions, depth-sorted rendering, and the zoomin, stop, zoomout, slow, objects and fast buttons.

- Ship Connect only as ZX and remove its Dis version. It keeps the 7 by 6 board with its incremental line values, the machine's minimax with its alpha-beta and tie-breaks, the Human and Machine menus, the level entries and a click's column. The model replays a game the Dis printed move by move with the same values, and the search runs in slices between frames where the Dis's process thought through one turn. Black's default level is 3, not the Dis's 8, because the ZX host runs the search about seventy times slower than the Dis interpreter; the entry still takes 0 to 10.

- Ship Bounce only as ZX and remove its Dis version. It keeps the toolbar's ball buttons and count label, lines drawn from either pointer button's press to its release, and the random balls with their speeds and colours; the model replays ten bounces recorded from the Dis rules, stopping where the Dis's own int-truncation boundary check turns on the host's last-bit rounding.

- Remove the MPEG Player, a stale pre-4e Dis binary that fails at load and whose source no longer compiles.

- Ship the File Chooser only as ZX and remove its Dis version. It keeps the Miller columns, the glob patterns, the path and filter rows, the Tab expansion to the browsed path, double-click acceptance and the chosen path on standard output.

- Ship Coffee and Man only as ZX and remove their Dis versions. The Tcl/Tk apps keep the six-cup Coffee animation with Stop/Go and the three sliders, and the manual browser's lookup, search and history.

- Ship Calendar only as ZX and remove its Dis version. It keeps the month grid, the coloured marks, the schedule records with Del and Save, the Set Time dialog and the recorded window sizes.

- Ship Polyhedra only as ZX and remove its Dis version. It keeps the solids, the thirteen greys, the z-buffered concave faces and the controls, and turns at about 1 to 2 frames a second under the ZX engine.

- Add emu -x, which ends the emulator when its boot program ends, even while servers it started keep running.

- Give ZX programs pctl's FORKENV, NEWNS, NODEVS and NEWPGRP and the process id, so ZX shells keep their variables apart.

- Remove the QuickTime Player, a stale Dis binary that failed to load and whose source no longer built.

- Ship Mine Sweeper and Tetris only as ZX and remove their Dis versions.

- Bring the ZX image viewer to the Dis viewer's features: animated GIFs, X bitmaps and PIC pictures, several files at once, files plumbed to the view port with -i, Save as an Inferno image, and -f.

- Add /dis/alphabet.zx, Alphabet in Ziran: the typed evaluator, its rewriter and the builtins of "load alphabet", with the modules of the root typeset. The Dis alphabet stays until the ZX shell runs it as its builtin.

- Ship Snake only as ZX and remove its Dis version.

- Open Inferno images and GIF pictures in the ZX image viewer, and remove the Dis viewer.

- Ship the Directory Browser only as ZX and remove its Dis version.

- Report RSA keys from taijios_keyring as the Limbo Keyring does, including a negative private exponent, and accept 0 rounds and key sizes from 8 bits.

- Let ZX commands run from the Dis shell start, wait for and kill children, and let ZX programs change their current directory.

- Ship System Log only as ZX and remove its Dis version.

- Ship Memory Monitor only as ZX and remove its Dis version.

- Ship About Inferno only as ZX and remove its Dis version.

- Give ZX programs the Keyring cryptography: digests, HMAC, AES-CBC, big integers, and RSA, DSA and ElGamal keys and signatures.

- Let ZX programs dial, announce and listen on the guest network, export part of their namespace, and serve a file2chan file.

- Let ZX programs create pipes, mount 9P servers, bind and unmount names, fork their namespace, start children on chosen streams, and poll any handle without waiting.

- Ship Clock and Stopwatch only as ZX and remove their Dis versions.

- Open the Rill desktop without loading Dis when the emulator starts without a command and the ZX window manager is installed, start command names from their ZX bundles, and hide catalog entries that need Dis there.

- Exit the ZX desktop cleanly after closing a window whose application was still drawing.

- Let System Log and other ZX windows poll stdin under the native window manager, so all installed ZX app bundles run without Dis.

- List and end running ZX processes in Task Manager when the guest runs without Dis.

- Let a ZX guest stop a running child with `taijios_process.Kill`, using Ziran's run stop requests, including a child blocked in a device read or window wait.

- Draw native title bars for ZX windows under the Rill desktop, with move, maximize, restore, hide and close, and keep windows below the panel when it changes size.

- Give each game and demo a distinct transparent icon, classify Brutus as an editor, and remove the repeated TaijiOS prefix from catalog descriptions.

- Start the installed Rill desktop by default and give the emulator a 128 MiB main memory pool so multiple guest apps can run together.

- Run the panel, window placement and chrome, Task Manager, Explorer, Clock, Stopwatch, and Counter through ZX while keeping compatible Dis fallbacks.
- Port Colours to ZX with the 256-color Draw palette, resizable cells, and sampling within the guest display.
- Open the existing ZX About Inferno and Memory Monitor from the System menu when installed.
- Port the Date window to ZX with the guest timezone and live second updates.
- Keep the desktop responsive when closing ZX windows that never read stdin.
- Use the Ziran window placement service in the desktop and remove Winplace Dis.
- Let the Linux emulator boot directly into a console ZX bundle without loading Dis.
- Add Ziran layer compositing and a combined pointer and keyboard stream for direct ZX guests.
- Run console ZX child commands with inherited guest streams and no Dis scheduler.
- Launch and collect concurrent native ZX children while keeping guest device descriptors private.
- Add Ziran workspace, focus, window stacking, and pointer capture for the native compositor.
- Add an opt-in Ziran window manager that runs multiple existing ZX GUI apps directly on Linux without Dis.
- Let Rill start under the Ziran window manager, launch ZX catalog entries, and control native windows and workspaces.
- Support app-requested window resizing, custom cursors, and guest pixel sampling during a drag on the native ZX desktop.
- Lock TaijiOS Tcl and Tk to the canonical source packages so each ZX application can select the Tk features it uses.

- Avoid redundant pointer-motion events on stationary ZX button presses and releases.

- Cache registry menu names, localized names and visible entries on reload, and index desktop IDs without changing override order.

- Upload packed RGB strips directly from portable software surfaces without
  converting every pixel to RGBA inside the guest.
- Consume opted-in read-only packed RGB slices synchronously without expanding
  each pixel into a host value, while retaining ordinary slice fallback.
- Expose millisecond Unix time separately from monotonic deadlines so portable
  guests can align visible clock updates with wall-clock boundaries.

- Decode large admitted images in bounded cooperative ZX segments with finite work, time and cancellation limits.

- Add a ZX PNG/JPEG image viewer with transparency, fit/zoom controls, scrolling, bounded input, and catalog MIME associations.

- Forward the Rill desktop console to host output without creating a Log window or task.

- Render guest title bars with built-in Sweet-Dark colors, round theme controls, centered ellipsized titles, and distinct inactive states.

- Add a freedesktop application catalog, desktop-entry parser, locale and action support, command expansion, and icon-theme lookup for Rill.
- Register guest applications with consistent PNG icons, keeping command tools out of the graphical menu, and supply themed home, drive, trash, clipboard and volume icons.
- Provide a user desktop installer and TaijiOS icons at standard hicolor sizes, and publish the logo through the emulator's X11 window icon.
