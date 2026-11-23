# Desktop registry local tests

`rill_lifecycle_test.py BUNDLE SHA256 --emu EMULATOR --guest-overlay OVERLAY
--desktop-extras` checks the full Rill desktop, application launch, input,
move/resize, task-menu Minimize, task restore, Explorer and Settings. It uses a
private display and a 128 MiB main pool by default. Its task operations use the
actual Rill context menu so titlebar layout changes cannot turn Minimize into
Close. OCR uses three-times scaling and unquoted TSV fields.

The parser and icon-theme tests are ordinary Ziran:

```sh
ziran run --target=c --module-path appl/cmd tests/desktop/parser_test.zi
```

The registry cache regression compares each visible entry and menu match against
the previous scan algorithm, including user overrides, Hidden/NoDisplay,
OnlyShowIn/NotShowIn, TryExec, invalid Exec, locale fallback and repeated reloads.
The `costarring`/`liquid` FNV-1a collisions exercise full equality for both IDs and
menu labels, including removal of one colliding entry. Long names and small
output buffers retain the parser's behavior.

```sh
ZIRAN_STD=/mnt/storage/Projects/ziranlang/ziran/std \
ziran bundle --root tests/desktop --entry registry_cache_test:main \
  --module-path appl/cmd --bind-host taijios_io --bind-host taijios_wm \
  --bind-host taijios_args --bind-host taijios_clock \
  -o build/desktop-registry/registry-cache-test.zx tests/desktop/registry_cache_test.zi
python3 tests/desktop/run_registry_cache.py
python3 tests/desktop/run_registry_cache.py --benchmark
```

These commands use a headless 128 MiB guest. Fixture writes and removals affect
only `build/desktop-registry/cache-home` and `cache-system`, bound into the
private guest namespace. Benchmark mode uses the real catalog without mutation.
On 2026-11-21, 364 catalog records still produced 50 visible launchers. Thirty
scan-based fallback misses took 1,824 ms and parsed 21,840 name fields; 3,000
cached misses took 41 ms, about 4,449 times less time per query in this local
microbenchmark. Each path includes the same file-read yield per query. This
measures registry misses, not whole-app startup or interaction performance.

`Reload` rebuilds all indexes and localized name views from the new snapshot.
Source edits and locale changes become visible on the next reload. `Count` and
`At` use the visible index; menu matching keeps the original raw, unlocalized
Name and X-Taiji-MenuName semantics, including hidden entries and empty aliases.
Hash collisions always fall back to full text equality. The existing catalog
capacity and field/file limits are unchanged.

The integration test reads the actual catalog and compares the portable PNG
decoder with shipped raw pixels inside a headless 128 MiB TaijiOS guest:

```sh
ziran bundle --root tests/desktop --entry registry_guest_test:main \
  --module-path appl/cmd --module-path /mnt/storage/Projects/kryonlabs/rill/app \
  --bind-host taijios_io --bind-host taijios_wm \
  -o build/desktop-registry/registry-test.zx tests/desktop/registry_guest_test.zi
python3 tests/desktop/run_guest.py
```

The Python file supervises the guest and verifies its success marker and result;
the assertions about the catalog and pixels live in Ziran. The emulator's normal
headless shutdown uses SIGKILL, as in the existing zx-smoke harness.

`preview.py` supervises a scrubbed private Xvfb, creates a native catalog fixture,
and captures the existing Rill Applications executable. `preview.py --guest`
stages the freshly built Rill bundle in `build/desktop-registry`, overlays that
single file in the private guest namespace, checks `_NET_WM_ICON`, and captures
the Applications menu. It never installs a bundle or touches the live desktop.

Generate shipped catalog/icon assets with `tools/generate-app-catalog.py`.
Install only the host desktop entry/icon sizes with `tools/install-desktop.sh`.
Its launcher intentionally has no `%U`: the guest launcher takes guest commands,
not host URLs. Startup notification is disabled because emu does not implement
that protocol. The existing user icon cache can fail independently of the new
icons; the installer reports that failure while preserving its other files.

The image viewer reuses `std/png_linux` and `std/jpeg` for straight RGBA PNG,
baseline JPEG and progressive JPEG. Its document layer checks input size,
dimensions and PNG chunk checksums before decoding. Native image local tests
also create the guest fixtures:

```sh
ZIRAN_STD=/mnt/storage/Projects/ziranlang/ziran/std \
ziran build --target=c --root tests/desktop --module-path appl/wm \
  --entry image_document_test:main -o build/desktop-registry/image-document-c \
  tests/desktop/image_document_test.zi
cc -std=c99 -I/mnt/storage/Projects/ziranlang/ziran/include \
  -Ibuild/desktop-registry/image-document-c \
  build/desktop-registry/image-document-c/*.c -lz -lm \
  -o build/desktop-registry/image-document-test
build/desktop-registry/image-document-test
magick build/desktop-registry/images/reference.jpg -interlace Plane \
  build/desktop-registry/images/progressive.jpg
cp build/desktop-registry/images/reference.png build/desktop-registry/images/no-extension
ZIRAN_STD=/mnt/storage/Projects/ziranlang/ziran/std \
ziran bundle --root tests/desktop --entry image_guest_test:main \
  --module-path appl/wm --module-path appl/cmd --bind-host taijios_io \
  --bind-host taijios_wm --bind-host taijios_args --bind-host taijios_image \
  -o build/desktop-registry/image-test.zx tests/desktop/image_guest_test.zi
python3 tests/desktop/run_guest.py --images --large
python3 tests/desktop/run_guest.py --budget
```

`run_guest.py --images` expects `view.zx` and an ABI-matching `zxrun.dis` in
`build/desktop-registry/image-overlay`. `image_preview.py` stages the matching
workspace-test WM, toolbar and runner there, copies the candidate Rill bundle under the
Rill package lock, and uses a private 128 MiB guest. Its `--mode viewer`,
`--mode explorer` and `--mode desktop` paths support captures and file activation
without installing candidates. `--zoom` and `--resize` exercise native image size
and a larger guest window. `--file broken.png` exercises the visible error state.
`--file large.png --cancel` checks Escape during decoding and then opens a small
PNG in the same window to check recovery.

The guest test checks PNG alpha, baseline and progressive JPEG, the 2048x1024
PNG fixture, malformed input, dimensions and PNG/JPEG default-app selection.
The typed `taijios_image` host API admits one decode after a positive file read.
Progress renews the existing 16-million-step segment only while cumulative work
increases within a finite image quota and a 60-second deadline. Callbacks poll
Escape, close and resize on the private guest window. The budget test checks
invalid/replayed progress, quota exhaustion and cancellation; its deliberate
loop without progress must still stop at the ordinary step limit.

The `appl/wm` package lock selects the Ziran toolchain and standard library for
`view.zx`, including `ReadPNGWithProgress` and `ReadJPEGWithProgress`. Build and
install the viewer with `(cd appl/wm && mk install-view-zx)`. The default decoder
APIs retain their existing signatures and pixel results.

The catalog also ships standard home, folder, drive, trash, clipboard and volume
icon names at every supported size, so these do not fall back to unrelated atlas
glyphs. Generate only those assets with `tools/generate-app-catalog.py --desktop-icons`.

Game icons have editable SVG sources in `icons/apps`. Bounce, Connect Four,
Collision Demo, Polyhedra, Reversi, Snake, Minesweeper and Tetris each have a
distinct icon. Brutus is a rich-text editor in Office, with its own document
icon. Registry IDs, package names and executable paths keep their existing
identities; launcher names and descriptions do not add a constant TaijiOS prefix.

```sh
PYTHONDONTWRITEBYTECODE=1 python3 tests/desktop/game_icons.py --prepare --test
```

This renders an isolated guest asset package, compares two fresh generations,
checks all nine output sizes, and preserves an existing local catalog edit on
an add-only install. Ziran checks every generated entry, complete game coverage,
distinct icons, transparent pixels, stable IDs and the actual PNG decoder at
16, 20, 24, 30, 32, 40 and 48 pixels. The ZX run also checks the guest registry,
Rill's themed row reader and PNG fallback against the native decoded pixels.
The driver compares all 63 native and ZX pixel hashes.

`game_icons_preview.py --bundle VERIFIED_BUNDLE --sha256 SHA256` runs only on a
scrubbed private Xvfb. It overlays the generated assets and eight desktop files,
uses a private favorites file, and verifies actual 20-pixel panel, 30-pixel menu
and 40-pixel desktop icon pixels. Use a verified Rill bundle with the guest
favorites provider. The tests preserve the installed emulator, Rill and chrome
bundles and never restart or control the owner's desktop.

`catalog_preinstall_test.py OUTPUT_ROOT` checks the preinstall manifest. The
shipped application set is described once, in `lib/preinstall.list`, and
`tools/generate-app-catalog.py --preinstall lib/preinstall.list --output-root
OUTPUT_ROOT` emits an entry only for a row whose bundle exists in that root, so
the manifest may name an app before it ships. The test asserts that every
present row's `Exec` and `TryExec` name its bundle, that an absent row emits
nothing, that desktop IDs stay stable, and that a second run is byte-identical.
It never writes outside the output root it is given.
