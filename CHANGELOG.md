# Changelog

## Unreleased

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
