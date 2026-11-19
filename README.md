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

For the Linux/386 emulator, build `libziran.a` in the canonical Ziran checkout
with a Linux/i386 C toolchain. Use a host-built `zi2c` for code generation and
keep the target objects in their own build directory.

```sh
make build/bin/zi2c
make BUILD_DIR=build/linux-386 CC='gcc -m32' CFLAGS='-O2 -fno-pie -fno-pic' \
    GEN_ZI2C="$PWD/build/bin/zi2c" build/linux-386/libziran.a
```

Set `ZX_INC` and `ZX_LIB` in TaijiOS's `mkconfig` to the absolute paths to that
checkout's `include` directory and the new archive. Set `ZX_LDFLAGS=-no-pie`
for the archive built above, then build and install from `emu/Linux`. Build
and install the shell command with `mk zxrun.install` from `appl/cmd`.

The ZX runner accepts application images up to 32 MiB. Console execution has a
16-million-step budget including initialization. Graphical programs keep their
runtime instance for the lifetime of the window and run without this console
budget. Dynamic ZX libraries and other Inferno services require their own
integration.

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
Linux/386/bin/emu -p main=256M -r "$PWD" -g 800x600 wm/wm wm/stopwatch -zx
```

`wm/stopwatch` without `-zx` runs the original Dis app. To launch any compatible
bundle in a TaijiOS window manager context, use `zxrun -w /path/to/app.zx`.

The runner binds Kryon's `zx_surface` calls `Open`, `Event`, `Present`, and
`Close` to the guest window manager and Draw. `Present` uploads a packed RGBA8
frame to a guest Draw image. `Event` supplies pointer buttons and movement,
keyboard input and UTF-8 text, redraw and resize, and close. The X11 emulator
exposes physical key presses, releases, and Shift, Control, and Alt through
`/dev/keyevent`. The guest window manager forwards these events to the focused
client that requests them. `/dev/keyboard` still carries Dis runes and supplies
ZX text input. Window managers without the key event path use the rune channel
for both presses and text. Surfaces are limited to 4,194,304 pixels and 4,096
pixels per axis.
The `taijios_clock.MonotonicMillis` capability supplies elapsed time.

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
