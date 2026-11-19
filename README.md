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

The ZX runner accepts application images up to 32 MiB and allows 16 million
execution steps including initialization. This integration covers standalone
applications and console output. Dynamic ZX libraries and other Inferno
services require guest-side bindings.
