# Changelog

## Unreleased

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
