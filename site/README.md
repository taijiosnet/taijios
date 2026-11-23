# taijios.net

The website, and the browser build of TaijiOS it runs.

`../emu/Web` is the hosted emulator's web platform: the same Inferno kernel,
Dis interpreter and ZX runtime as `emu/Linux`, compiled to wasm32 with
Emscripten. `main` runs on a proxied pthread and every kproc is a Web Worker
sharing one memory, so the page needs cross-origin isolation (`_headers`).
`win-web.c` keeps an XRGB32 screen and an input ring in shared memory;
`js/taiji-emu.js` copies changed pixels to the canvas each frame and writes
pointer and key events into the ring. The guest root is an in-memory WASMFS
tree at `/taiji`, unpacked from `emu/root.tjr.gz` before `main` starts.
`root.list` says what goes in it; its `lazy` entries stay on the server as
`emu/lazy/PATH.gz`, and `emu/Web/lazy.c` fetches each on its first open.

```sh
make -C site          # build/web/emu (the emulator) and build/site (the site)
make -C site test     # boot build/site in private headless Chromium
make -C site deploy   # test, then upload build/site to the Pages project "taiji"
make -C site live     # compare https://taijios.net/ with build/site and boot it
```

Requirements: Emscripten (`EMSDK`, default `~/emsdk`), the Ziran checkout
(`ZIRAN_ROOT`), `ziran`, `gzip`, `chromium` and `tesseract`, and the built
guest in `dis/`, including the ZX bundles the preinstall manifest names.

## What ships in the first download

The apps in the browser root are not listed in `root.list`. `sitebuild` reads
`lib/preinstall.list`, the same manifest `tools/generate-app-catalog.py
--preinstall` uses for the desktop catalog, and packs each app row according to
its `first-run` column: `root` ships in the first download and `lazy` stays on
the server until first open. Rill and the desktop panel are `root`; every other
application is `lazy`. Adding an application to the desktop menu therefore
cannot silently change the web root, and the two cannot name different app sets.
`root.list` keeps only what is not an app: the Dis tree, the three ZX libraries
`emu/port/zx.c` installs, `lib/`, icons, fonts and the directories to create.
Its `- .zx` line keeps the Dis tree walk from packing app bundles into the root
as a side effect; a bundle reaches the root only by being named in the manifest.

`sitebuild` measures the first download on every run and refuses to publish
past a budget: `emu/root.tjr.gz` alone may be at most 6.5 MB (6,815,744 bytes)
and `root.tjr.gz` plus `taijios.wasm.gz`, `taijios.js` and the page at most
8 MB (8,388,608 bytes). It prints both numbers and, when one is over, exits
non-zero naming the largest packed guest file, so the fix goes to the file that
grew rather than to the budget:

```text
sitebuild: root.tjr.gz 5541290 of 6815744 bytes; first download 6705588 of 8388608 bytes (799476 wasm, 53271 script, 311551 page)
sitebuild: 2130 guest files (19871384 bytes) and 22 fetched on demand in build/site
```

Pass `--preinstall MANIFEST` to measure a different manifest, which is how an
oversized fixture is checked:

```sh
tools/sitebuild/sitebuild "$SCRATCH/site" build/web/emu --preinstall "$SCRATCH/big.list"
```

## Deploying

taijios.net is the Cloudflare Pages project `taiji`. `make -C site deploy`
runs the full test and then uploads exactly that `build/site` with
`wrangler pages deploy` from this machine, using its wrangler login (or
`CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID` in the environment).
`make -C site live` then checks every deployed file's SHA-256 against
`build/site` and boots the live page. There is no CI deploy yet: the Pages
credentials exist only as GitHub secrets of the retired `taijiosnet/taiji`
repository, and the ZX bundles the root bundle needs are build outputs that
are not in git (see `plans/site-deploy.md`).

The build tools are Ziran programs: `emu/Web/mkweb.zi` compiles and links the
emulator, `tools/sitebuild.zi` assembles the site, and `tools/sitetest.zi`
serves it, drives Chromium over its DevTools pipe and reads the emulator
screen with tesseract.
