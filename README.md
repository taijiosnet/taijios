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

Build a ZX application with the Ziran toolchain, then run it from the TaijiOS
shell using its guest pathname.

```sh
zi2zx --root . --entry hello:main -o hello.zx hello.zi
```

For the Linux/386 emulator, build the hosted runtime from the Ziran revision
`8e8e53bacd207ad8ed9d9a92a96483893e6788d8`. It includes binary64 fixes for Tcl's fixed-point
formatter and compact execution plans, decoded instructions, and value locations
for the default 32 MiB main pool. The loader releases the guest image buffer
after decoding and before execution planning. The GUI package dependencies are
pinned separately in `appl/wm/ziran.lock`.
Build `libziran.a` in the canonical Ziran checkout with a Linux/i386 C toolchain.
Use a host-built `zi2c` for code generation and keep the target objects in
their own build directory.

```sh
make build/bin/zi2c
make BUILD_DIR=build/linux-386-engine NATIVE_HOST_ENABLED=0 CC='gcc -m32' \
    CFLAGS='-O2 -fno-pie -fno-pic -DZIRAN_COMPACT_EXEC_PLAN -DZIRAN_EXEC_FRAME_RESERVE_BYTES=6291456 -DZIRAN_EXEC_FRAME_RESERVE_MIN=1048576' GEN_ZI2C="$PWD/build/bin/zi2c" \
    build/linux-386-engine/libziran.a
```

Set `ZX_INC` and `ZX_LIB` in TaijiOS's `mkconfig` to the absolute paths to that
checkout's `include` directory and the new archive. Set `ZX_LDFLAGS=-no-pie`
for the archive built above, then build and install from `emu/Linux`. Build
and install the shell command with `mk zxrun.install` from `appl/cmd`.

The ZX runner accepts application and library images up to 32 MiB each.
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
    mk wm.install stopwatch.install
    kryon_id=$(python3 -c 'import json; print(json.load(open("ziran.lock"))["root"]["dependencies"]["kryon"])')
    ziran bundle --project --bind-host "${kryon_id}_pixmap" \
        --entry stopwatch:main -o ../../dis/wm/stopwatch.zx stopwatch.zi
)
Linux/386/bin/emu -r "$PWD" -g 800x600 wm/wm wm/stopwatch -zx
```

The hosted ZX Stopwatch runs in the default 32 MiB main pool when built with
the runtime settings above. `wm/stopwatch` without `-zx` runs the original Dis
app. To launch any compatible bundle in a TaijiOS window manager context, use
`zxrun -w /path/to/app.zx`.

The runner binds Kryon's `zx_surface` calls `Open`, `Event`, `Present`, and
`Close` to the guest window manager and Draw. `Present` uploads a packed RGBA8
frame to a guest Draw image. The runtime borrows the RGBA bytes during the
synchronous upload, so it can pass the frame without a temporary copy.
`Event` supplies pointer buttons and movement, keyboard input, UTF-8 text,
and redraw, resize, and close events. The X11 emulator exposes physical key
presses, releases, and Shift, Control, and Alt through
`/dev/keyevent`. The guest window manager forwards these events to the focused
client that requests them. `/dev/keyboard` still carries Dis runes and supplies
ZX text input. Window managers without the key event path use the rune channel
for both presses and text. Surfaces are limited to 4,194,304 pixels and 4,096
pixels per axis.
The `taijios_clock.MonotonicMillis` capability supplies elapsed time.

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
with `zx_surface.Event` between polls to keep input responsive.

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

### Build and run ZX `cat`

With `zi2zx`, `mk`, and `limbo` on `PATH`, build and install the hosted
emulator as above, then install the ZX commands, launcher, and shell.

```sh
(cd appl/cmd && mk install-zx)
Linux/386/bin/emu -r "$PWD" /dis/sh.dis -c 'whatis cat; echo hello | cat'
```

Each `-` operand reads stdin. With no operands `cat` reads stdin once.
Use `/dis/cat.dis` to run the Dis version. `zxrun -c /dis/cat.zx [file ...]`
accepts void or zero as success and puts a nonzero return value in `$status`.
`zxrun file.zx [args ...]` prints the returned value.

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

Test the command against its Dis counterpart with
`python3 -u build/zx-smoke/run.py Linux/386/bin/emu --cat`.

### Build and run ZX `echo`, `basename`, and `cleanname`

`mk install-zx` installs `cat`, `echo`, `basename`, and `cleanname` as
executable bundles. For each directory in `$path`, `sh` tries an executable
`.zx` when the ZX runtime is available, followed by `.dis` and the executable
script form. Built-ins retain first priority. A name ending in `.dis`
selects the Dis module. The shell launches a ZX command with `zxrun -s`,
so existing scripts keep named errors such as `usage` and `bad open`.
They use `taijios_args` for operands and `taijios_io` for output and diagnostics.
`basename` and `cleanname` share the Ziran path functions in `appl/lib/taijios_names.zi`.

```sh
Linux/386/bin/emu -r "$PWD" /dis/sh.dis -c 'echo hello; basename /a/file.txt .txt; cleanname -d /a b/../c'
python3 -u build/zx-smoke/run.py Linux/386/bin/emu --stock-zx --cat --utilities
```

### Dis command migration order

`mk install-zx` also installs `wc`, `uniq`, and `tr` as shell commands.
All three use `taijios_io` for guest I/O. `uniq` and `tr` share a buffered
rune reader. The stream parity test uses a freshly built Dis `uniq` so it
can compare the `-c` flag from the current Limbo source.

```sh
(cd appl/cmd && mk install-streams-zx uniq.dis)
python3 build/zx-smoke/run.py Linux/386/bin/emu --streams
```

`tee`, `cp`, `test`, and `ls` are installed as executable ZX commands. `tee`
fans out guest stdin and supports `-a` and `--`. `cp` supports recursive
copies and guest owner, group, mode, and timestamp flags. `test` uses guest
file metadata, descriptor paths, and named shell statuses. `ls` reads packed
directory entries through `taijios_io` and keeps union-directory order,
metadata, sorting, and formatting in Ziran. The Dis versions are available
as `/dis/tee.dis`, `/dis/cp.dis`, `/dis/test.dis`, and `/dis/ls.dis`.
`mkdir` creates directories and supports `-p` using the guest namespace.
The original command remains available as `/dis/mkdir.dis`.

```sh
(cd appl/cmd && mk install-file-commands-zx)
python3 -u build/zx-smoke/run.py Linux/386/bin/emu --tee --file-commands --ls
```

On the hosted tree used for this port, 376 of 845 installed Dis files loaded
with the shell's `Command.init` signature. That includes 160 entries directly
under `/dis` and 52 under `/dis/wm`. This inventory checks the entry
signature without invoking each program.

| Order | Existing commands | Capabilities to exercise or add |
| --- | --- | --- |
| 1 | `echo`, `basename`, `cleanname` (ported) | Argument handling, text output, path-string operations |
| 2 | `wc`, `uniq`, `tr` (ported) | Guest stdin, stdout, and sequential file access |
| 3 | `test`, `tee`, `cp`, `ls` (ported) | File metadata, directory reads, and file creation |
| 4 | `wm/about`, `wm/clock`, `wm/colors` | Guest surfaces and input, wall-clock time, and display sampling as needed |
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
