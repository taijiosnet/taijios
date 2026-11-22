Inferno® is a distributed operating system, originally developed at Bell Labs, but now developed and maintained by Vita Nuova® as Free Software.  Applications written in Inferno's concurrent programming language, Limbo, are compiled to its portable virtual machine code (Dis), to run anywhere on a network in the portable environment that Inferno provides.  Unusually, that environment looks and acts like a complete operating system.

Inferno represents services and resources in a file-like name hierarchy.  Programs access them using only the file operations open, read/write, and close.  `Files' are not just stored data, but represent devices, network and protocol interfaces, dynamic data sources, and services.  The approach unifies and provides basic naming, structuring, and access control mechanisms for all system resources.  A single file-service protocol (the same as Plan 9's 9P) makes all those resources available for import or export throughout the network in a uniform way, independent of location. An application simply attaches the resources it needs to its own per-process name hierarchy ('name space').

Inferno can run 'native' on various ARM, PowerPC, SPARC and x86 platforms but also 'hosted', under an existing operating system (including AIX, FreeBSD, IRIX, Linux, MacOS X, Plan 9, and Solaris), again on various processor types.

This repository includes source code for the basic applications, Inferno itself (hosted and native), all supporting software, including the native compiler suite, essential executables and supporting files.

## Run ZX on hosted TaijiOS

In a ZX-enabled Linux emulator, `zxrun hello.zx` opens a verified ZX application
in the caller's Inferno namespace. The program runs inside `emu` on Ziran's
portable instruction engine. ZX output follows the command's Inferno standard
output and error descriptors, including shell redirections and pipes. A scalar
entry result is printed as a signed Limbo `big`. Dis commands can run alongside
ZX programs.

A ZX-enabled Linux emulator can also start a console bundle directly. Pass its
absolute guest path and operands to `emu`, for example
`Linux/386/bin/emu -r "$PWD" /hello.zx operand`. This starts the bundle in the
emulator's initial guest namespace without loading Dis. The path is also
accepted by `-d` for daemon mode. The guest's standard streams inherit the
host process's standard streams. A void or zero result exits with status 0.
Positive results through 255 are returned as process exit statuses. Other
results and loader errors exit with status 1. A direct bundle can access guest
Draw and input devices. The normal desktop runner provides Rill integration and
Dis task inspection.
Run `python3 tests/desktop/zx_boot_test.py` to verify direct startup in a guest
root containing only ZX programs. Add `--graphics` to test compositing, clipped
updates, workspace and focus policy, pointer input, and keyboard input on a
private Xvfb display. Direct graphical bundles can import `guest_draw` and
`guest_input` from `appl/lib`.
The input module receives pointer motion and buttons, key transitions, and
composed text from one blocking device stream.

Build the direct console runner with `(cd appl/cmd && mk zxrun.zx)`. To run one
ZX command from another in a guest without Dis, start the emulator with
`/appl/cmd/zxrun.zx -c /hello.zx operand`. The child inherits the guest streams
and namespace. A scalar is printed by default. `-c` returns the scalar as
command status, and `-s` also reports the child's named failure when present.
The regular `zxrun` command manages Dis process groups in the normal desktop.
In a direct ZX guest, `taijios_process.Start` launches a concurrent console
child. `Poll` and `Wait` collect its result using the returned ID. Children
inherit the guest namespace and standard streams. Other open descriptors stay
with the caller. `Kill` stops a running child: the Ziran engine ends it at its
next checkpoint, and a device read, sleep or window wait it is blocked in
returns first. Its outcome then has status -1 and the error `killed`.

Build the direct ZX window manager with `(cd appl/wm && mk native_wm.zx)`.
To run an existing ZX GUI app under it with the current Linux build, use
`emu/Linux/o.emu -r "$PWD" -g 960x600 /appl/wm/native_wm.zx /dis/wm/counter.zx`.
Pass multiple app paths to open them concurrently. Switch workspaces with
Ctrl+Alt+Left or Ctrl+Alt+Right. Hold Shift as well to move the focused window.
With Rill installed, pass `--desktop /dis/wm/rill.zx` after the manager path
to start Rill directly in ZX. Rill can launch ZX apps from its guest catalog
and manage them through its task list. Its window actions, workspaces, and
panel regions use the native manager.
Under a desktop, each ZX window gets a native title bar drawn in Ziran with
Kryon's window chrome and the Rill theme's control sprites. Drag it to move the
window, and use its Hide, Maximize and Close controls.
The default desktop continues to start Rill through the regular desktop runner.

The emulator defaults to a 128 MiB `main` pool for native allocations, including
the ZX runtime. Use `-p main=64M` or `-p main=32M` before the guest command to set
a smaller limit. The full Rill desktop uses the 128 MiB default. `/dev/memory`
reports the applied limit in the second column of the `main` row.
Run `python3 tests/desktop/emulator_pools_test.py` from the TaijiOS root to
verify the default and overrides against the built Linux/386 emulator.

Build a ZX application with the Ziran toolchain, then run it from the TaijiOS
shell using its guest pathname.

```sh
zi2zx --root . --entry hello:main -o hello.zx hello.zi
```

For the Linux/386 emulator, use Ziran revision
`c3ef9fb291fc1a4469c60fbbd8b4b888f508ad77` for the hosted runtime. It provides
the borrowed-slice interface used to upload packed Rill pixel rows, the
packed instruction engine used to execute ZX, and the `ZxRunControl` stop
requests behind `taijios_process.Kill`. The GUI package dependencies
are pinned separately in `appl/wm/ziran.lock`.
To get that exact source, run `ziran lock` and `ziran fetch` in a scratch
package whose `[toolchain]` ref is that revision; the package cache then holds
the checkout. Build `libziran.a` there with a Linux/i386 C toolchain, which
needs the i386 C library headers (for example `gcc -m32` with Debian's
`libc6-dev:i386`).
Use a host-built `zi2c` for code generation and keep the target objects in
their own build directory.

```sh
make build/bin/zi2c
make BUILD_DIR=build/linux-386-engine NATIVE_HOST_ENABLED=0 CC='gcc -m32' \
    CFLAGS='-O2 -fno-pie -fno-pic -DZIRAN_COMPACT_EXEC_PLAN -DZIRAN_EXEC_FRAME_RESERVE_BYTES=6291456 -DZIRAN_EXEC_FRAME_RESERVE_MIN=1048576' GEN_ZI2C="$PWD/build/bin/zi2c" \
    build/linux-386-engine/libziran.a
```

Set `ZX_INC` and `ZX_LIB` in TaijiOS's `mkconfig` to the absolute paths to the
headers and archive built from that same revision. Set `ZX_LDFLAGS=-no-pie`
for the archive built above, then build and install from `emu/Linux`. Build
and install the shell command with `mk zxrun.install` from `appl/cmd`.

The ZX runner accepts application and library images up to 32 MiB each.
When the linked Ziran runtime provides `BundleOpenReadAt`, the runner verifies
seekable application images of at least 256 KiB with bounded positional reads.
With `BundleOpenEngineReadAt`, the runner also compacts the decoded instruction
table and returns its unused space to the guest's main memory pool.
Images with assets or module links use the owned-image loader, as do small
images and files without a known seekable length. An I/O or verification error
ends the launch and reports an error to the guest shell.
Use `zi2zx --library` to build a shared ZX module and place its image at
`/dis/lib/<logical-name>.zx` in the application's guest namespace. The runner
honors guest `bind` mounts at `/dis/lib`. Declare module requirements and imports
with `zi2zx --require-module` and `--import`, and open the module with
`std/zx_module`. Module output follows the application's guest console and shell
redirections. The shared loader validates module images and typed imports.

Each ZX instance starts with a 16-million-step budget shared by initialization
and execution. A graphical application renews its budget when `Event` delivers
input or a window event, or completes a nonzero timed wait. A positive
`taijios_io.Read` also renews the budget so a filter can process a long stream
in bounded chunks. Empty reads and polls, read errors, and closed-window events
consume the remaining budget.

On Linux/i386, the ZX engine uses nontrapping, round-to-nearest binary64
arithmetic and restores the calling thread's floating-point environment after
execution.

### Build and run ZX Stopwatch

Stopwatch is a Kryon app. Its widgets, elapsed time, and three lap values are
implemented in `appl/wm/stopwatch.zi`. Build it with Ziran's package CLI and the pinned Kryon
revision in `appl/wm/ziran.lock`. For development, use
`appl/wm/ziran.local.toml` with absolute paths to the canonical checkouts.

```toml
[overrides]
ziran = "/path/to/ziran"
kryon = "/path/to/kryon"
```

From the TaijiOS root, with `ziran`, `mk`, and `limbo` available on `PATH`:

```sh
(cd emu/Linux && mk install)
(cd appl/cmd && mk zxrun.install)
(
    cd appl/wm
    mk wm.install stopwatch.install install-stopwatch-zx
)
Linux/386/bin/emu -r "$PWD" -g 800x600 wm/wm wm/stopwatch -zx
```

The hosted ZX Stopwatch runs with `-p main=32M` when built with
the runtime settings above. `wm/stopwatch` without `-zx` runs the original Dis
app. To launch any compatible bundle in a TaijiOS window manager context, use
`zxrun -w /path/to/app.zx`.

The runner binds Kryon's `zx_surface` calls `Open`, `Event`, `Present`, and
`Close` to the guest window manager and Draw. `Present` accepts packed RGBA8
pixels. It uploads opaque frames to a 24-bit Draw image and uses a 32-bit
image for frames with transparency. The runtime borrows the RGBA bytes
during the synchronous upload, so it can pass the frame without a temporary
frame copy. `PresentOpaqueRows` lets opaque renderers submit a frame in
contiguous rows, starting at row zero. The last upload displays the frame.
`PresentOpaqueStrip` initializes the backing image the same way and then lets
retained renderers update any full-width row range without replacing the other
pixels. The caller can reuse the strip buffer as soon as the call returns.
The Taiji `SetTitle` binding updates the UTF-8 title of an open window and
accepts up to 512 bytes without embedded NULs. `PointerMillis` returns the
original timestamp of the latest pointer event, or `-1` when unavailable.
`Event` supplies pointer buttons and movement, keyboard input, UTF-8 text,
and redraw, resize, and close events. The X11 emulator exposes physical key
presses, releases, and Shift, Control, and Alt through
`/dev/keyevent`. The guest window manager forwards these events to the focused
client that requests them. `/dev/keyboard` still carries Dis runes and supplies
ZX text input. Window managers without the key event path use the rune channel
for both presses and text. Surfaces are limited to 4,194,304 pixels and 4,096
pixels per axis.
The `taijios_clock.MonotonicMillis` capability supplies elapsed time.

Graphical ZX apps with an open window can use `taijios_wm.Launch` to start a
graphical Dis or ZX child in the same guest namespace and working directory.
Build with `--bind-host taijios_wm` and pass the program path and its UTF-8
arguments, including `argv[0]`. End each argument with a NUL byte. The runner
accepts up to 64 arguments in 4,096 bytes and a path up to 1,024 bytes.
`Launch` returns `0` after dispatching the child in its own process group and
`-1` if dispatch fails. The result covers dispatch only. The child runs
independently of the parent window.

`taijios_wm.Resize` changes a visible window's content size. The window manager
may clamp the request to fit the display. Use the next resize event to get the
actual dimensions. `taijios_wm.SetCursor` applies a packed Inferno cursor bitmap
while the app's window has focus. Pass zero dimensions and an empty bitmap to
restore the default cursor.

### Build and run ZX Clock

Use the Kryon revision pinned in `appl/wm/ziran.lock` when building Clock.
If you use a local Kryon override, use that revision so the generated host
binding matches the lockfile. Install and launch Clock with the emulator's
default memory setting.

```sh
(cd appl/wm && mk install-clock-zx)
Linux/386/bin/emu -r "$PWD" -g 800x600 wm/wm zxrun -w /dis/wm/clock.zx
python3 -u appl/wm/clock_zx_test.py
```

Clock draws through Kryon's hosted surface and reads `/dev/time`,
`/env/timezone`, and `/locale/timezone` through `taijios_files.ReadAt`.
The original Clock remains available as `/dis/wm/clock.dis`.

### Build and run the ZX desktop panel

The Start menu, keyboard navigation, and minimized window buttons run in
`/dis/wm/desktop_panel.zx`. The Ziran panel uses Kryon's palette and geometry.
The `kryon/host/surface` binding supplies guest pointer and keyboard events.
The typed `taijios_panel` binding supplies menu and task labels, manages the
popup surface, and draws rectangles and text through the guest Draw service.
It also sends validated menu and task IDs to the window manager. Drawing uses
the guest font and keeps the panel small enough to run with Task Manager in the
32 MiB main pool.

Build and install from the TaijiOS root with the same compiler and Linux/386
configuration used for the other ZX applications.

```sh
(cd emu/Linux && mk install)
(cd appl/cmd && mk zxrun.install)
(cd appl/wm && mk install-desktop-zx)
Linux/386/bin/emu -r "$PWD" -g 800x600 wm/wm
```

`lib/wmsetup` registers the menu commands with the Dis toolbar broker. The
broker also provides the guest console, clipboard, and compatibility with
existing Dis clients and per-user menu scripts. With Rill installed, pass
`wm/wm wm/toolbar` to select the original ZX panel or `wm/wm wm/toolbar -l` to
select the Dis panel. The toolbar uses the Dis panel when its ZX bundle is absent.

### Build and run the Rill guest desktop

Rill runs its desktop, panel, menus, and window controls in a ZX bundle. The
window manager grants the root desktop access to `taijios_desktop` for launcher
and window snapshots, launch and window actions, and panel hit regions.
`kryon/host/surface` and `kryon/pixmap` supply guest Draw and input.
`taijios_clock` supplies monotonic time and `taijios_io` accesses files in the
guest namespace. The installer copies the icon atlas to `/lib/rill/icons/ui.rgba`
and the Sweet-Dark window resources to `/lib/rill/themes/Sweet-Dark`.
Application windows keep their existing Dis or ZX interfaces.

The Rill installer generates missing stock launchers and hicolor icons under
`/lib` using Python 3, ImageMagick (`magick`), and DejaVu Sans. It uses the
installed guest bundles in `dis/` to choose between ZX and Dis launch commands,
so install the guest applications before running `install-rill-zx`. Existing
catalog records, icon files, and MIME defaults are preserved.

The X11 window icon header ships with the source for native builds. Run
`python3 tools/generate-app-catalog.py --host-icons` after changing the logo
or before using `tools/install-desktop.sh` in a fresh checkout.

From the TaijiOS root, set `RILL_ROOT` to the canonical Rill checkout and use
the current Ziran compiler and Linux/386 runtime. Build and install the host
and guest modules from the same tree because they share the `ZX->Window` ABI.

```sh
TAIJIOS_MODULES="$PWD/appl/cmd" "$RILL_ROOT/scripts/package-taiji.sh"
(cd emu/Linux && mk install)
(cd appl/cmd && mk zxrun.install)
(cd appl/wm && mk install-window-chrome-zx install-rill-zx \
    RILL_ZX="$RILL_ROOT/build/rill.zx" RILL_ICON_ATLAS="$RILL_ROOT/assets/icons/ui.rgba" \
    RILL_SWEET_THEME="$RILL_ROOT/assets/themes/Sweet-Dark")
Linux/386/bin/emu -r "$PWD" -g 800x600 wm/wm
```

`wm/wm` starts Rill when `/dis/wm/rill.zx` is installed. Use the default
128 MiB main pool to run Rill and multiple applications together. For a
32 MiB guest, start `wm/wm wm/toolbar` to use the smaller toolbar. Pass
`wm/wm -rill` with an alternate guest bundle path to test another build.

### Build and run ZX window chrome and placement

The shared title bar for ZX Draw windows and legacy Dis Tk windows uses Kryon's
`window_chrome` module for layout, caption colors, control glyphs, hit testing,
and click state. TaijiOS Draw paints the resulting rectangles and text using the
guest font. The window manager uses separate ZX bundles for window placement,
stacking, window hit testing, and toolbar row lookup and removal. Existing Dis
window clients use the same channels and window-control messages.

The GUI lock under `appl/wm` pins the Kryon window chrome dependency. From the
TaijiOS root:

```sh
(cd appl/wm && mk install-window-chrome-zx)
(cd emu/Linux && mk install)
Linux/386/bin/emu -r "$PWD" -g 800x600 wm/wm
```

The target installs `window_chrome.zx`, `winplace.zx`, and `wm_policy.zx` in
`/dis/lib` with their callers. The typed `taijios_wm_call.Read` and `Reply`
bindings pass the current request and its result as bounded `[]s32` slices.
The emulator keeps one instance of each service and caches each caption's paint
commands until its dimensions, focus, or controls change. The window manager
uses `winplace.zx` for placement. `mk wm.install` also builds and installs this
service. Guests without the ZX runtime use bounded placement at the previous
window position and retain the Dis title bar.

Drag the lower-right corner of a resizable window to change its size. The
guest window manager keeps the top-left corner fixed and sends the new bounds
to the app through the same resize messages used for ZX and Dis windows.

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD/appl/cmd/tcltk" \
    python3 -u appl/wm/kryon_apps_test.py --require-window-chrome --require-window-resize
python3 -u appl/lib/winplace_test.py
```

### Open Kryon apps from the guest desktop

Build and install the Kryon apps with `(cd appl/wm && mk install-kryon-zx)`.
Start TaijiOS with `Linux/386/bin/emu -r "$PWD" -g 800x600 wm/wm` and choose
**Clock**, **Stopwatch**, **Counter**, **Colours**, or **Date and Time** under **Utilities** in the toolbar menu.
Counter uses the Kryon buttons and text widgets for decreasing, resetting, and
increasing its value. Its image is `/dis/wm/counter.zx` and can also be launched
with `zxrun -w /dis/wm/counter.zx` from a guest shell.

Colours displays Draw's 256-color palette. Click a cell to read its index and
RGB value. Drag from the palette to sample elsewhere in the TaijiOS guest. The
legacy Colors entry opens the ZX app when available and can still display the
original Dis palette. `mk install-colors-zx` installs both entry points.

The menu smoke test runs the installed Linux/386 emulator with a 32 MiB guest
heap in a private Xvfb display.

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD/appl/cmd/tcltk" python3 -u appl/wm/kryon_apps_test.py
```

### Build and run ZX Task Manager

Build the guest target in the canonical Task Manager repository and install its
bundle alongside the other Kryon apps. Run these commands from the TaijiOS root
with that checkout beside it under `Projects/kryonlabs/taskmgr`.

```sh
TAIJI_ROOT="$PWD"
TASKMGR_ROOT="$(cd ../../kryonlabs/taskmgr && pwd)"
make -C "$TASKMGR_ROOT" taiji TAIJIOS_TASK_MODULES="$TAIJI_ROOT/appl/cmd"
(cd appl/wm && mk install-taskmgr-zx TASKMGR_ZX="$TASKMGR_ROOT/build/taskmgr.zx")
Linux/386/bin/emu -r "$TAIJI_ROOT" -g 800x600 wm/wm
```

Choose **System → Task Manager** or run `zxrun -w /dis/wm/taskmgr.zx` from a guest
shell. The app shares its Ziran UI with the other Task Manager builds and uses
Kryon's hosted surface for guest window drawing and input. `taijios_tasks`
reads guest tasks and the three TaijiOS memory pools. Process memory is a Dis
stack and module estimate. On hosted Linux the guest scheduler measures each
task's cumulative CPU time with the worker thread's CPU clock, which excludes
time spent waiting for I/O or input. Task Manager compares consecutive samples
using monotonic timestamps and a task incarnation ID. CPU percentages use one
core as 100%. Ending a task uses the guest `/prog` device's permissions and
native kill operation. The menu falls back to `wm/task` when the ZX bundle
is absent.

In a guest started directly in ZX, without Dis, `taijios_tasks` lists the
running ZX processes instead, named after their bundles, with CPU time from
each process's thread clock. Process memory is not estimated there. Ending
one uses the same stop request as `taijios_process.Kill`.

The integration test uses Xvfb, `xdotool`, ImageMagick, Pillow, and Tesseract
to read and interact with the private guest display.

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD/appl/cmd/tcltk" python3 -u appl/wm/taskmgr_zx_test.py --cpu --gui --require-window-resize
```

### Build and run ZX Explorer

Build Explorer's guest target from its canonical checkout and install the
bundle in TaijiOS. Use a Linux/386 emulator and guest modules built from the
same TaijiOS tree. Run these commands from the TaijiOS root.

```sh
TAIJI_ROOT="$PWD"
EXPLORER_ROOT="$(cd ../../kryonlabs/explorer && pwd)"
make -C "$EXPLORER_ROOT" taiji TAIJIOS_MODULES="$TAIJI_ROOT/appl/cmd"
(cd appl/wm && mk install-explorer-zx EXPLORER_ZX="$EXPLORER_ROOT/build/explorer.zx")
Linux/386/bin/emu -r "$TAIJI_ROOT" -g 800x600 wm/wm
```

Choose **Files** in Start or run `zxrun -w /dis/wm/explorer.zx` from a guest
shell. Explorer streams Kryon drawing in bounded row groups through
`zx_surface.PresentOpaqueRows` and reads guest input through the same surface.
The typed `taijios_io` binding handles filesystem operations in the current
guest namespace. The Files menu opens `wm/ftree` when the ZX bundle is absent.

### Read guest standard input

Both `zxrun` and `zxrun -w` can bind the typed standard input capability.
Declare it in a module named `taijios_stdin.zi` and bind that module when
building the application with `zi2zx --bind-host taijios_stdin`.

```zi
host_api :: #system_library "host_api";
Read :: (buffer: []u8) -> s32 #foreign host_api;
```

`Read` reads up to 4096 bytes from the caller's guest fd 0 in one call. It
returns the number of bytes copied, including short reads, and preserves the
rest of the buffer. For a nonempty buffer, the call returns `0` at EOF or
`-1` on a read error. An empty buffer returns `0` without reading. Dis pipes and input
redirection supply the stream in both console and windowed runs.

Windowed bundles can use `taijios_stdin.Poll(buffer)` to read guest fd 0
while continuing to process window events. A call copies up to 4096 bytes,
returns `-2` while input is pending, `0` at EOF, or `-1` on error. An empty
buffer returns `0` without starting a read. The runner cancels a pending
read when the window closes or the bundle exits. A windowed app can wait
with `zx_surface.Event` between polls to keep input responsive. Windows of
the native ZX window manager get the same call without Dis: a reader thread
holds one chunk of fd 0 at a time and stops when the app exits.

`zxrun -w file.zx [args ...]` passes operands through `taijios_args`.
`zxrun -c -w file.zx [args ...]` reports the returned value as shell status.
Add `-p` before the bundle path to start the runner and its workers in a
new guest process group while retaining the caller's redirections.

`zx_surface.SetTasked(true)` tasks a presented window through TaijiOS's
window manager. `SetTasked(false)` restores it. Apps that request this
capability get the title bar's Hide control. `Event` delivers kind `10`
for a visibility change, with `button` equal to `1` when tasked and `0`
when restored.

Log Window uses these bindings to follow a live guest pipe with its window
responsive. Install it with `(cd appl/cmd && mk install-logwindow-zx)` and
run `zxrun -p -w /dis/wm/logwindow.zx 'System log' < /path/to/log` from a
graphical guest shell. See the [Tk applications guide](appl/cmd/tcltk/README.md).

Memory reads `/dev/memory` through `taijios_files` and updates the arena graphs
using the `taijios_clock` and `zx_surface` bindings. Install it with
`(cd appl/cmd && mk install-memory-zx)` and run
`zxrun -p -w /dis/wm/memory.zx` from the graphical guest shell.

### Tcl and Tk packages

The hosted Tcl shell and Tk apps use the standalone [Tcl](https://git.waozi.xyz/ziranlang/tcl)
and [Tk](https://git.waozi.xyz/ziranlang/tk) packages selected by the root
`ziran.toml` and `ziran.lock`. Use the Ziran package CLI on `PATH` and run
`ziran pkg path tcl` or `ziran pkg path tk` to see the selected source.
For development, add local package paths to the ignored root `ziran.local.toml`
under `[overrides]`. Source edits use these paths with the existing lock.
Use the checked-in lock for production. It selects Tcl and Tk source commits
so each application can compile the Tk features it needs, such as bitmap
labels or banded Canvas rendering. When changing the dependency revisions,
regenerate the source lock using the canonical Git object stores:

```sh
ZIRAN_LOCK_GIT_OBJECTS=/path/to/tcl:/path/to/tk:/path/to/ziran ziran lock
```

The Kryon applications use the separate manifest and lock under `appl/wm`.

Build and install the guest Tcl shell and Tk applications with
`(cd appl/cmd && mk install-zx)`. See the [Tcl integration guide](appl/lib/tcl.md)
and [Tk applications guide](appl/cmd/tcltk/README.md) for launch and test commands.

### ZX shell commands

`cat`, `echo`, `basename`, `cleanname`, `wc`, `uniq`, `tr`, `tee`, `cp`,
`test`, `ls` and `mkdir` are written in Ziran and installed only as
executable ZX bundles. With `ziran`, `zi2zx`, `mk`, and `limbo` on `PATH`,
build and install the hosted emulator as above, then install the commands.

```sh
(cd appl/cmd && mk install)
Linux/386/bin/emu -r "$PWD" /dis/sh.dis -c 'whatis cat; echo hello | cat'
```

For each directory in `$path`, `sh` tries an executable `.zx` when the ZX
runtime is available, followed by `.dis` and the executable script form.
Built-ins retain first priority. A name ending in `.dis` selects the Dis
module. The shell launches a ZX command with `zxrun -s`, so existing scripts
keep named errors such as `usage` and `bad open`. `xargs` and `time` hand a
command that has no Dis module to the shell, so they start ZX commands too.
`zxrun -c /dis/cat.zx [file ...]` accepts void or zero as success and puts a
nonzero return value in `$status`. `zxrun file.zx [args ...]` prints the
returned value.

ZX commands use two typed capabilities declared in `appl/cmd`.

- `taijios_args.Count()` returns the number of operands and `At(index)`
  returns a zero-based operand as a UTF-8 string. Out-of-range indices return
  an empty string. `SetFailure(message)` supplies a named shell status when
  the program returns a nonzero value. `zxrun -s` uses this message when
  present and uses the numeric return value otherwise.
- `taijios_io.Open(path, mode)` opens an existing file in the caller's guest
  namespace. Modes `0`, `1`, and `2` mean read, write, and read/write.
  `Read(handle, buffer)` and `Write(handle, data)` transfer up to 8192 bytes
  per call. Handles `0`, `1`, and `2` refer to the caller's standard streams.
  `Close(handle)` closes a file opened by `Open`. The runner also closes
  those handles when the bundle exits. Operations return `-1` on error and
  `Error()` returns the last I/O error. A read into a nonempty buffer returns
  zero at EOF.
- `taijios_io.Create(path, mode, permissions)` creates or truncates a guest
  file and returns a handle. `Seek(handle, offset, origin)` sets its position
  and returns the absolute byte offset as `s64`. Origins `0`, `1`, and `2`
  are start, current, and end. `Stat(path, metadata)` writes twelve bytes
  on success and returns `0`. The first eight bytes are the signed file
  length and the next four are the unsigned Inferno mode, both little endian.
- `StatPacked(path, buffer)` and `FstatPacked(handle, buffer)` return the
  standard packed Inferno directory record and its byte count. `WstatPacked`
  applies a packed update using guest permissions. `FdPath(fd)` resolves a
  descriptor number from the calling guest process, as used by `test -t`.
- `CreateNew(path, mode, permissions)` fails if the guest path already exists.
  `Remove(path)` removes a file or empty directory using guest permissions.
  `Cwd()` returns the working directory and `Home()` reads the guest `home`
  variable. Both return an empty string if the path is unavailable.

`basename` and `cleanname` share the Ziran path functions in
`appl/lib/taijios_names.zi`, and `uniq` and `tr` share a buffered rune
reader. `tee` fans out guest stdin and supports `-a` and `--`. `cp` supports
recursive copies and guest owner, group, mode, and timestamp flags. `test`
uses guest file metadata, descriptor paths, and named shell statuses. `ls`
reads packed directory entries through `taijios_io` and keeps union-directory
order, metadata, sorting, and formatting in Ziran. `mkdir` supports `-p`.

The command test runs each command in the hosted emulator and compares its
status, output and diagnostics with what the Limbo version printed.

```sh
ziran run --target=c --root tests/commands tests/commands/commands_test.zi
```

### Dis command migration order

On the hosted tree used for this port, 376 of 845 installed Dis files loaded
with the shell's `Command.init` signature. That includes 160 entries directly
under `/dis` and 52 under `/dis/wm`. This inventory checks the entry
signature without invoking each program.

| Order | Existing commands | Capabilities to exercise or add |
| --- | --- | --- |
| 1 | `echo`, `basename`, `cleanname` (ported) | Argument handling, text output, path-string operations |
| 2 | `wc`, `uniq`, `tr` (ported) | Guest stdin, stdout, and sequential file access |
| 3 | `test`, `tee`, `cp`, `ls` (ported) | File metadata, directory reads, and file creation |
| 4 | `wm/about`, `wm/clock` (ported), `wm/colors` (ported) | Guest surfaces and input, wall-clock time, and guest display sampling |
| 5 | `sh`, `wm/wm`, compiler and service commands | Process control, namespaces, window management, and service-specific APIs |

### Verify the hosted runner

Build the console fixture and put the Kryon hosted surface example bundle at
`build/zx-smoke/hosted_surface.zx` using Kryon's hosted surface build instructions.
Then run the smoke suite from the TaijiOS root. The graphics checks use a private
Xvfb, `xdotool`, ImageMagick's `import`, and Pillow.

```sh
zi2zx --root build/zx-smoke --entry hello:main \
    -o 'build/zx-smoke/hello app.zx' build/zx-smoke/hello.zi
printf 'invalid ZX\n' > build/zx-smoke/bad.zx
zi2zx --root build/zx-smoke/keyevents --entry zx_surface:main \
    -o build/zx-smoke/keyevents.zx build/zx-smoke/keyevents/zx_surface.zi
python3 build/zx-smoke/run.py Linux/386/bin/emu --graphics
```

Build these two fixtures to exercise file descriptors, windowed operands,
pending reads, keyboard input, task and restore, and closing an idle pipe.

```sh
zi2zx --root build/zx-smoke --module-path appl/cmd --bind-host taijios_io \
    --entry filesystem:main -o build/zx-smoke/filesystem.zx build/zx-smoke/filesystem.zi
zi2zx --root build/zx-smoke/keyevents --module-path appl/cmd \
    --bind-host zx_surface --bind-host taijios_args --bind-host taijios_stdin \
    --entry windowio:main -o build/zx-smoke/windowio.zx build/zx-smoke/keyevents/windowio.zi
python3 -u build/zx-smoke/run.py Linux/386/bin/emu --guest-io --graphics
```

To include guest module resolution and graphical step-budget checks, build
these fixtures with `ZIRAN_SRC` pointing to the Ziran source directory:

```sh
zi2zx --root build/zx-smoke/modules --library guest_counter \
    --export guest_counter:Add -o build/zx-smoke/modules/guest_counter.zx \
    build/zx-smoke/modules/guest_counter.zi
zi2zx --root build/zx-smoke/modules --module-path "$ZIRAN_SRC/std" \
    --entry linked:main --require-module GuestCounter=guest_counter \
    --import linked:Add=GuestCounter:Add -o build/zx-smoke/linked.zx \
    build/zx-smoke/modules/linked.zi
zi2zx --root build/zx-smoke/keyevents --entry zx_surface:Budget \
    -o build/zx-smoke/budget.zx build/zx-smoke/keyevents/zx_surface.zi
python3 build/zx-smoke/run.py Linux/386/bin/emu --graphics --runtime
```

To verify binary64 precision in the hosted engine on Linux/i386, build the
standard-library fixture and run it inside the installed emulator.

```sh
zi2zx --root build/zx-smoke --entry float64:main \
    -o build/zx-smoke/float64.zx build/zx-smoke/float64.zi
python3 build/zx-smoke/run.py Linux/386/bin/emu --precision
```

To verify heap reuse at the emulator's default pool size, build the fixture
and run the 64-round test in the installed emulator.

```sh
zi2zx --root build/zx-smoke --entry arena-reuse:main \
    -o build/zx-smoke/arena-reuse.zx build/zx-smoke/arena-reuse.zi
python3 build/zx-smoke/run.py Linux/386/bin/emu --heap
```

To test guest stdin, build the fixture and add `--stdin` to the smoke command:

```sh
zi2zx --root build/zx-smoke --bind-host taijios_stdin \
    --entry taijios_stdin:main -o build/zx-smoke/stdin.zx \
    build/zx-smoke/taijios_stdin.zi
python3 build/zx-smoke/run.py Linux/386/bin/emu --graphics --runtime --stdin
```
