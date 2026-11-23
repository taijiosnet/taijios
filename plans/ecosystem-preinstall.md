# Ecosystem preinstall: every app, game and module as ZX on TaijiOS and on the web

Owner direction (2026-11-23, verbatim, typos kept): "taij isi the ultimate showacse of our entire eycosyset mit should come prenitsall with full izran and kr yon modules all apsp we ever maed in woezi games etc.. all must work on taiki everyhting as zx as modulera as psosibel worknig on the web as well"

Reading: TaijiOS ships preinstalled with the full Ziran std and Kryon module sets, plus every app and game in the waozixyz and kryonlabs repositories, all running on TaijiOS as ZX, as modular as possible (shared code installed once, not copied into every bundle), on the hosted desktop and at taijios.net in the browser. This file is open work only; the Dis-to-ZX port continues in `plans/dis-to-zx.md` and is not planned here.

Evidence rules used below: a cell names its source. "unknown" means no evidence was found in the repository and the cell says what would establish it. Nothing here is a completion claim.

## Measurement basis

Read 2026-11-23 on these working trees, with `git status --porcelain`, `git log origin/master..HEAD`, `ziran.toml`, `ziran.lock`, `Makefile`/`GNUmakefile`/`mkfile`, and each repository's `AGENTS.md` where one exists. No build was run; existing artifacts were inspected in place (first 8 bytes for the ZX revision, `strings` for the declared capability modules).

TaijiOS tree: `1b084b4501f2`, equal to `origin/master`, 350 dirty paths (mostly untracked `build/`), `git ls-files plans` = alphabet-zx.md, dis-to-zx.md, site-deploy.md.

Artifact facts that bound the rest of this document:

- ZX format revision is 28 (`ziranlang/ziran/docs/IMPLEMENTATION_STATUS.md`, `cmd/zx_runner_header.zi: ZX_FORMAT_REVISION :: 28`). A revision-26 artifact is stale and must be rebuilt before any claim: `waozixyz/games/apple/build/*.zx`, `waozixyz/apps/photos/build/photos-portable.zx`, `kryonlabs/workbook/build/workbook.zib`.
- TaijiOS loads the Ziran runtime from `ZX_LIB=/mnt/storage/Projects/taijiosnet/taijios/build/host32/libziran.a` and `ZX_INC=.../ziran/include` (`mkconfig:35-38`), compiled into `emu` only when `ZX_LIB` is set (`emu/Linux/mkfile:45`, `-DTAIJI_ZX`).
- A guest bundle's capability list is matched by leaf name or by a `p<16 hex>_name` package qualification (`emu/port/zx.c:3214-3226`, `zxmodule`).

---

## Section A. Per-repository inventory

Column meanings: **builds as .zx** = a target or command in the tree that writes a `.zx` (revision noted), and the bundle size if an artifact exists today. **on TaijiOS** = there is a TaijiOS target or a guest test, and the host capabilities the bundle declares versus what `emu/port/zx.c` grants. **pin** = `origin/master` commit on Gitea (`git rev-parse`), plus unpushed/uncommitted state. **next step** = the smallest change that makes it run on TaijiOS as ZX.

Guest capability set granted by TaijiOS today (`emu/port/zx.c:3319-3489`, module names as matched):

| Module | Functions | Available where |
|---|---|---|
| `taijios_stdin` | Read, Poll | always (Poll needs a window) |
| `taijios_files` | ReadAt | always |
| `taijios_draw` | SampleGuestPointer | window |
| `taijios_image` | Begin, Step, End, Cancel | always |
| `taijios_tasks` | Capture, TaskAt, PoolAt, Terminate, SampleNanos | hosted or Dis-free |
| `taijios_clock`, `clock` | MonotonicMillis, UnixMillis / ClockMillisecondsHost | always |
| `taijios_args` | Count, At, SetFailure | always |
| `taijios_process` | Run, Start, Poll, Wait, Kill, StartWith, Pid, NewPgrp | Linux only (`#ifdef __linux__`, 3377-3426) |
| `taijios_native_wm` | StartWindow, StartDesktop, WaitActivity, LaunchWindow, Request, Text, Snapshot, ChromeRegions, Payload, ApplyCursor, Reply, ReplySample, Disconnect, Dispatch | ZX-booted session, depth 0 |
| `taijios_desktop` | BindDesktop, Capture, LauncherAt, WindowAt, Launch, WindowAction, DesktopAction, UnixSeconds, TimezoneOffsetSeconds, SetChromeRegions | window with a guest desktop |
| `taijios_wm` | Launch, Resize, SetCursor | window |
| `zx_surface` | Open, Event, Present, PresentOpaqueRows/Strip, PresentRGBStrip, Close, SetTasked, SetTitle, PointerMillis | window |
| `taijios_panel` | Snapshot, Row, Popup, Choose, Paint, Flush | window with a panel |
| `taijios_namespace` | Pipe, Mount, Bind, Unmount, Fork, ForkEnv, NewNs, NoDevs, MountAsync, MountDone, Export, Error | always |
| `taijios_keyring` | all declared | always |
| `taijios_dial` | Dial, Announce, Listen | always |
| `taijios_io` | Open, Create, CreateNew, Read, Write, Seek, Stat(Packed), FstatPacked, WstatPacked, FdPath, Remove, Cwd, Home, Sync, RenameSameDir, PollRead, Chdir, Close, Error | always |
| `taijios_wm_call` | Read, Reply | WM policy libraries |

**Not granted anywhere in TaijiOS** (grep of `emu/port/zx.c`): the standard guest modules `guest_assets`, `guest_clock`, `guest_files`, `guest_process`, `guest_window` (`ziranlang/ziran/std/*`, `docs/ZX.md:291-304`); audio; clipboard/snarf; touch; OpenGL; TLS; child-bundle hosting (`std/bundle_guest`). That list is the width of the gap for every Kryon-hosted app.

### A.1 waozixyz/games

| Repo | Builds as .zx today | Bundle size (artifact, revision) | On TaijiOS | Pin / tree state | Smallest next step |
|---|---|---|---|---|---|
| apple | `Makefile:12-19`: `make portable` (`ziran build portable`, `ziran.toml:23-25 codegen="zx"`) and `make hosted` (`ziran bundle --define KRYON_HOSTED_UI --entry hosted:main`) | `build/AppleRunner-portable.zx` 2,751,806 rev 26; `build/AppleRunner-hosted.zx` 769,476 rev 26 | No taiji target, no guest test (`grep -c taiji` over build/test sources = 0). Declares Kryon hosted-app UI; TaijiOS grants none of that ABI | No `origin` remote (3 local commits, `git remote -v` empty), tree clean → published pin **none** | Add a `taiji` profile/entry that uses `kryon/host/surface` + `zx_surface`; needs Kryon upstream K1/K2 first |
| arcade | `make all` → `scripts/build-desktop.py`, `scripts/build-apps.py`, `scripts/build-entity.py` | `build/entity.zx` 5,000,711 rev 28; `build/apps.zx` 1,853,587 rev 28; `build/shovey.zx` 38,678,292 rev 28; `build/arcade.zx` 10,156 rev 28 (launcher-sized) | No taiji target. Hosted-app ABI | `be276f3931ac`, ahead 1 (`Move native players to Kryon desktop host and Ziran audio`), 43 dirty / 5 untracked | Same as apple; the collection host (`modules/apps`) is the real porting surface, see A.5 |
| choano | `make portable` → `scripts/build.py bundle`, `choose PORTABLE` `ziran bundle --define CHOANO_PORTABLE --asset-dir ...` | `build/choano.zx` 5,370,511 rev 28; `build/entity.zx` 7,020,012 rev 28 | No taiji target; hosted-app ABI | `106be8ab7e91` = origin, 2 dirty / 2 untracked | Same as apple |
| garden | None. `Makefile:30-49` compiles `garden.zi` to `bin/Garden` against raylib (`garden.zi:12-15` `#system_library "raylib"`) | No bundle | No. Needs raylib, which the guest lacks (no GL) | No `origin` remote, 495 dirty paths → published pin **none** | Port the port/*.zi surface layer to `kryon/host/surface`; that is a game rewrite, not a packaging step |
| kasaival | None (`GNUmakefile` has web/android/headless only); `Game2D` + SDL2 | No bundle | No. Needs SDL2 surface + audio + GL | `a07dcc6ab01b`, behind 1, 6 dirty | Same as garden; largest rewrite in the games group |
| katalis | None for ZX. `Makefile:16-23` → `ziran build` (native) and `ziran tool kryon build --profile web` | No bundle | No. Raylib desktop backend, web canvas profile (`ziran.toml:39-50`) | `15f49045562b` = origin, 1 dirty | Add `[tool.kryon.profiles.taiji] backend="desktop" codegen="zx"` plus a `zx_surface` entry |
| neon | None. `Makefile:22-29` builds `bin/NeonTim` from generated C + Game2D | No bundle | No | `c4451b908e5f` = origin, 2 dirty | Same as garden |
| shark | None. `Makefile:1-5` `native: ziran build` | No bundle | No | **Not a git repository** (`git rev-parse` fails); no pin at all | Decide whether it is tracked before planning a port |
| shovey | `make web-zx` and `make bundles` → `scripts/build-bundles.py` (`KRYON_HOSTED_UI`) | `build/player/linux/shovey.zx` 14,605,963 rev 28; `build/games/shovey.zx` 18,130,323 rev 28; `build/player/linux/entity.zx` 5,328,354 rev 28 | No taiji target (19 taiji mentions are all Play/Dew policy, none a guest host) | `cc41196527f0` = origin, 1 dirty | Same as apple; the web-zx recipe is the closest existing model |
| voyki | Target not in a Makefile; `ziran.toml:28-30` declares `profiles.portable codegen="zx"`, README documents `kryon build portable` | No `.zx` in `build/` today; only `Voyki-desktop`, `Voyki-web.html` | No | `eb5f5c262710` = origin, clean | Run `kryon build portable` once and record the artifact (it is the smallest possible port) |
| wurm | `python3 tools/build_portable.py` → `ziran bundle --project --define KRYON_HOSTED_UI` (`tools/build_portable.py:132-147`) | `build/downloads/wurm.zx` 29,772,830 rev 28 | No taiji target | `921801756d75` = origin, clean | Same as apple |
| zoombinis | None for ZX; `ziran.toml:23-25 codegen="c99"` | No bundle | No | No `origin` remote, clean → published pin **none** | Add a `codegen="zx"` profile |
| learning/jungle | `make all` → 15 game bundles + scene bundles (`Makefile:60,118-122,161`), `KRYON_HOSTED_UI` | `build/app/games/dino-paint.zx` 12,139,757 rev 28 (largest); 15 game bundles plus `scenes/*` | No taiji target | `5f0025a956d8` = origin, 149 dirty / 139 untracked | Same as apple; 15 bundles is the largest single port surface |

### A.2 waozixyz/apps

| Repo | Builds as .zx today | Bundle size (artifact, revision) | On TaijiOS | Pin / tree state | Smallest next step |
|---|---|---|---|---|---|
| breeze (Inbe) | Yes: `APP_BUNDLES` + `INBE_BUNDLE` (`Makefile:444-446`), `KRYON_HOSTED_UI` | `build/inbe.zx` 129,288,375 rev 28 — 129 MB, the largest artifact in scope | No | `1039893c51cf`, ahead 1, 18 dirty / 6 untracked | Port it as a *host* (apps controller) rather than a single bundle; see A.5 |
| photos | Yes: `make bundle`/`portable` → `ziran tool kryon build portable` (`Makefile:323-324`) | `build/photos-portable.zx` 9,414,949 rev 26 (**stale**); `build/photos.zx` 1,655,012 rev 28 | No | `b8e640f148d5` = origin, 5 dirty | Rebuild portable at rev 28, then port the host entry |
| relay | No ZX target; `Makefile:13-14 build/install/test` only | No bundle | No | `a930247630aa` = origin, clean | Add a bundle target (Kryon hosted UI) |
| werk | Yes: `PORTABLE_BUNDLES` (`Makefile:64-100`), per-tool bundles + host | `build/apps/entity.zx` 7,484,358 rev 28; `build/apps/apps.zx` 1,748,278 rev 28; other tools per `apps/*` | No | `48bfea6ee562` = origin, 15 dirty / 5 untracked | Port the host (`src/apps.zi`) to a Taiji surface; tools follow for free |

### A.3 waozixyz/modules

| Repo | Builds as .zx today | Bundle size (artifact, revision) | On TaijiOS | Pin / tree state | Smallest next step |
|---|---|---|---|---|---|
| apps | No Makefile. Produces bundles only as fixtures (`build/native-test/root.zx`, `build/slim-test/root.zx`) | `build/native-test/root.zx` 15,498,333; `build/slim-test/root.zx` 3,929,087 (rev not checked → unknown) | No. Needs `ReadAppHost`/`WriteAppHost` (`src/node_app.zi:8-10`), which no TaijiOS host binds | `a3308e7cff7a` = origin, 18 dirty | This is the collection host; make its `host_api` mapping selectable so it can sit on `app_registry` + `zx_surface` |
| auth | `ziran bundle --define KRYON_HOSTED_UI --entry auth:Main` (`Makefile:21`) | `build/auth.zx` 840,225 rev 28 | No | `c7cc170c20c8` = origin, clean | Port `Main` to a Taiji host entry |
| dew | No ZX target; depends on `entity` (`ziran.toml:11-13`) | No bundle | No | `18bdfcb7bead` = origin, 1 dirty | None of its own: it ships inside entity/apps bundles |
| entity | Yes: `build/entity.zx` (`Makefile:47-50`), `KRYON_HOSTED_UI`, `--asset-dir assets=assets` | `build/entity.zx` 7,404,938 rev 28 | No | `97482cf6dc07` = origin, clean | Port `Main` to a Taiji host entry; this unblocks dew, werk, breeze, arcade |
| gamekit | `ziran tool gamekit pack` writes checked `.zx` apps (`Makefile:50-63`); `make fixture-test` opens them with the runtime's bundle loader | No retained artifact | No | `b033476f5d33` = origin, clean | Emit Taiji-host packages (`gamekit pack --host taiji`) |
| practices | No Makefile; exports only (`ziran.toml` links = EGL/GLESv2/GLX/X11) | No bundle | No, and GL is unavailable | `2d3ef6e4fd2d` = origin, **2011 dirty paths** / 131 untracked | Unknown until the checkout is reconciled; the GL link list alone blocks a guest port |

### A.4 kryonlabs

| Repo | Builds as .zx today | Bundle size (artifact, revision) | On TaijiOS | Pin / tree state | Smallest next step |
|---|---|---|---|---|---|
| agentlab | No build (static sites, `AGENTS.md`) | None | No | `dc3f572c0ba3` = origin, clean | Either publish the sites as assets in a viewer bundle or declare out of scope |
| browser | Yes: `make zx` → `scripts/build-zx.sh` (`KRYON_ZX` frame host) | `build/Browser.zx` 4,121,731 rev 28 | No. Declares Kryon `zx_run` capabilities (`ReadBundleInput`, `TakeBundleCodepoint`, `Bundle*Host`), which TaijiOS does not bind | `c4a94801d38b` = origin, 40 dirty / 23 untracked | Add a `zx_surface` host entry beside the `zx_run` one |
| explorer | Yes: `make taiji` → `ziran bundle --define EXPLORER_TAIJI --bind-host kryon/pixmap --entry taiji_host:main` (`Makefile:207-215`) | `build/explorer.zx` 8,751,776 rev 28, **byte-identical** to `taijiosnet/taijios/dis/wm/explorer.zx` (sha256 `bb92f817…`) | **Yes.** Guest tests: `make test-taiji-model`, `make test-taiji-desktop`, `make test-guest-files` (`docs/TAIJI.md`). Declares `zx_surface`, `taijios_io`, `taijios_stat`, `taijios_wm`, `app_registry`, and source module `guest_files`; all granted | `f6a067a74c26` = origin, clean | Keep it as the reference port; add it to the preinstall set (T1/T4) |
| github | No ZX target | None | No | `4f25ead6c6d3`, ahead 1, 2 dirty | Superseded by gitnex (`AGENTS.md`); no port |
| gitnex | No ZX target | None | No | `1aed4e7b267a` = origin, clean | Add a Taiji host entry (it is the maintained Git client) |
| rill | Yes: `sh scripts/package-taiji.sh` (`--define RILL_TAIJI`, `--bind-host taijios_desktop|taijios_wm|taijios_clock|taijios_io|kryon/pixmap`) | `build/rill.zx` 11,205,643 rev 28. Installed `dis/wm/rill.zx` is 11,138,532, sha256 differs (not byte-identical) | **Yes.** Installed as the session desktop; `site` boot reaches it; no saved guest test receipt was found (→ unknown whether the repo build and the installed build were both verified) | `f24217576e1e` = origin, clean | Reproduce the installed bundle from the repo commit and record the receipt |
| showcase | Data/scripts only (`projects/*/project.json`) | None | No | `12b0e8e2cfdf` = origin, 1 dirty | Put entries in a catalog viewer; it is not an app |
| taskmgr | Yes: `make taiji` → `scripts/package-taiji.sh` (`Makefile:63-68`; binds `taijios_tasks` + `kryon/pixmap`) | `build/taskmgr.zx` 7,573,271 rev 28; installed `dis/wm/taskmgr.zx` 7,550,378 (sha256 differs) | **Yes.** Guest tests: `make taiji-test` (fixture), `scripts/guest-cpu-test.py`, `scripts/guest-lifecycle-test.py`; README requires `/prog` + `taijios_tasks` + surface/pixmap + monotonic clock | `79e477c960ab` = origin, 5 dirty | Reproduce the installed bundle and record the receipt |
| telegram | `default_profile="portable"`, `codegen="zx"` (`ziran.toml:17-25`) | `build/telegram-portable.zx` 5,282,165 rev 28 | No (declares `zx_run` capabilities) | `c1ab498375bf` = origin, clean | Add a surface host entry |
| terminal | Yes: `make zx` → `scripts/build-zx.sh` (`KRYON_ZX`, `--bind <pkg>_frame_entry:ProjectFrame=app_zx_frame:Frame`) | `build/linux-x86_64/Terminal.zx` 2,141,788 rev 28 | **No standalone.** TaijiOS gets the terminal by compiling `terminal/app_host` *into* `rill.zx` (`app/terminal_windows.zi:20`), not by running `Terminal.zx` | `8fcdc78b9ce7` = origin, 13 dirty | Add a `zx_surface`-only host entry so the standalone bundle can run |
| workbook | Yes: `make bundle` → `ziran bundle --define KRYON_HOSTED_UI` (`Makefile:158-162`) | `build/workbook.zib` 424,729 **revision 26, old `.zib` name** | No | `1d4ec6f512c9` = origin, 3 dirty | Rebuild as `.zx` (the target still names `.zib`), then port the host |
| kryon | Library plus the `zx` player: `make zx-player`, `make zx-window-host`, `make zx-test|zx-linked-test|zx-nested-test|zx-reload-test` (`Makefile:45,227-303`, `mk/zx-player.mk`) | `build/bin/zx` is an ELF (not a bundle); test bundles under `build/test/`, `build/scratch/` | Partly: the `zx_surface` ABI TaijiOS binds **is** Kryon's `host/surface` (`ziran.toml:212`, `src/backend/zx_surface.zi`) | `c4b79335b0b0` = origin, 41 dirty / 9 untracked | Publish `kryon/pixmap`, `kryon/session`, `kryon/tree`, `kryon/text` as ZX libraries (K1) |
| ziranlang/ziran | Toolchain and std; `std/zx_module.zi`, `include/ziran_zx_module.h`; ship `.zx` only as tests | `build/bin/{ziran,zi2zx,zx}` are ELF (4.2 MB, 605 KB, 3.4 MB) | The runtime is linked into `emu`; the toolchain is not in the guest | `4787a8d35c98` = origin, 458 dirty paths | See Section D |

### A.5 ziranlang/packages (21)

All are `origin/master`-clean and in sync except these dirty trees: `browser-automation` (2), `crypto` (2), `image-codec` (2), `lua` (2), `mermaid` (2), `syntax` (2), `tcl` (3), `tk` (3), `telegram` (2), `oqs` (2), `qrcode` (2), `noise` (2). None is ahead or behind `origin/master`. HEADs: audio `b5c6b56b7117`, av1 `5d3656c8be3b`, avif `6ff696d436b6`, browser-automation `376518b3e877`, clip-tokenizer `96ef3ac6e342`, compression `c42011e3af31`, crypto `4916cd4b750e`, image-codec `5182c32ce2e2`, lua `6dbe706342b8`, mermaid `1d39d40f152f`, mesh-client `17f9e49a271c`, noise `d36b76b1fb6f`, oqs `79aff5fc96c5`, qrcode `6ab80d226988`, sqlite `b15b52413148`, syntax `b4188db5ad2b`, tcl `42f9e6d43449`, telegram `f07eeab0b814`, tk `1a2c1f6f4e04`, webp `4b9a61d32460`. (`ziranlang/packages/build/` is not a repository.)

13 of 21 produce `.zx` **test** bundles today (audio `build/tests/portable.zx` 601,659; compression `build/zstd-wasm/encode.zx` 604,488; crypto `build/portable.zx` 142,537; mermaid `build/zx-provider-verification/build/mermaid-test.zx` 1,356,931; noise `build/tests/fast_noise_test.zx` 266,764; qrcode `build/qrcode-test.zx` 184,769; syntax `build/zx-provider-verification/build/syntax-test.zx` 88,211; tcl `build/tcl-test.zx` 4,580,757; tk `build/widgets_test.zx` 5,056,838; webp `build/scratch/authored-portable/source.zx` 514,518; av1 `build/scratch/av1-deblock/source.zx` 17,732,008; avif `build/scratch/av1-grain-noise/source.zx` 56,687,800; image-codec `build/scratch/contracts/source.zx` 227,307 — revisions not checked → unknown). Only `noise` and `qrcode` have `pack-ir` targets; **no package has a `--library` target**, and no repository in scope has a `ziran.zx.lock`.

Counts for the coordinator's report:

- Repositories that build a `.zx` today: **30** — 6/12 games (apple, arcade, choano, shovey, wurm, jungle), 3/4 apps (breeze, photos, werk), 2/6 modules (auth, entity), 6/11 kryonlabs `.zx` producers (browser, explorer, rill, taskmgr, telegram, terminal) plus workbook as a stale `.zib`, and 13/21 packages producing test bundles. `voyki` has a `codegen="zx"` profile but no artifact (unknown); `gamekit` packs `.zx` through its own tool with no retained artifact.
- Repositories that have run on TaijiOS: **3** — explorer, rill, taskmgr — each with a TaijiOS install plus a documented guest test; only explorer's installed bundle is byte-identical to its repo build.

---

## Section B. How TaijiOS installs apps today

**Catalog.** `lib/apps/*.desktop` holds 363 tracked entries. `tools/generate-app-catalog.py` generates them: `generate_catalog` (`:159-203`) walks `appl/wm/*.b` and `appl/cmd/**/*.b`, applies an exclude set (`wm`, `toolbar`, `desktop_panel`, `window_chrome_service`, `smenu`, `debdata`, `debsrc`, `samstub`, `samtk`), then chooses `Exec=/dis/<relative>.dis` **unless** `dis/<relative>.zx` exists or the entry is `wm/view` (`:180-183`). `--guest-assets` stages the catalog, icons, MIME defaults and hard-links only files that do not already exist (`:207-225`), so a local catalog edit survives an add-only install. The install is driven from `appl/wm/mkfile:192` (`install-rill-zx`), which also requires `RILL_ZX`, a 1 MiB `RILL_ICON_ATLAS` and Sweet-Dark `chrome.rgba` (28224 bytes).

**What the catalog covers today.** 26 of 363 entries name a `.zx` `Exec` (`grep -h '^Exec=' lib/apps/*.desktop | grep -c zx`): twelve commands (`basename`, `cat`, `cleanname`, `cp`, `echo`, `ls`, `mkdir`, `tclsh`, `tee`, `test`, `tr`, `uniq`, `wc`), and the `dis/wm` bundles `about`, `clock`, `counter`, `dir`, `explorer`, `logwindow`, `memory`, `snake`, `stopwatch`, `sweeper`, `taskmgr`, `tetris`, `view`. `lib/apps` has **no** entry for `rill`, no entry for a Kryon Terminal, and no entry for any waozixyz/kryonlabs app.

**Window-manager side.** `dis/wm/` holds 15 `.zx` (about, clock, counter, desktop_panel, dir, explorer, logwindow, memory, rill, snake, stopwatch, sweeper, taskmgr, tetris, view; sizes 119,448-11,138,532). The session chain is `emu` → `/dis/wm/wm.zx` (`appl/wm/native_wm.zi`) → `/dis/wm/rill.zx`; `wm.zx` is **not installed** today (`ls dis/wm/wm.zx` absent), so the emulator still starts `emuinit.dis` unless `install-wm-zx` ran. The ZX manager's window manager uses `taijios_native_wm` plus `zx_surface`, and draws through `guest_draw`/`guest_input` (`appl/wm/native_wm.zi:1-11`).

**Rill's pins.** `kryonlabs/rill/ziran.toml` pins the toolchain `1b7608b8`, `kryon` `39f7540d`, `terminal` `dba7d4ef`, `explorer` `eb8aaca0` and `taiji_sdk` `7ae191a3` (source). `ziran.lock` resolves `explorer` with `data_views` `62603bdb` and `taiji_sdk` `80248ef8`. Consequences: (1) Terminal is embedded from source (`app/terminal_windows.zi:20` imports `terminal/app_host`), so the standalone `Terminal.zx` is not what runs; (2) Explorer is launched by path in the guest (`src/platform_taiji.zi:160` `WM.Launch("/dis/wm/explorer.zx", …)`), so Rill and `dis/wm/explorer.zx` can drift (they do: `dis/wm/rill.zx` differs from the repo's `build/rill.zx`); (3) DataViews reaches Rill only through Explorer's lock entry, not through a direct Rill pin. Rill's own Taiji build lists its unavailable services (`src/platform_taiji.zi:203`: "Audio, tray, notifications and clipboard: unavailable").

**How the same root reaches the web.** `site/Makefile` builds `build/web/emu` with `emu/Web/mkweb.zi`, then `tools/sitebuild.zi` packs `site/root.list` into `build/site/emu/root.tjr.gz` and copies each `lazy` entry to `build/site/emu/lazy/<path>.gz`. `emu/Web/lazy.c` reads `/lazy.list` (a base URL line, then `SIZE PATH` lines), creates an empty placeholder with the real size, and on first open does a synchronous XHR, inflates it and fills the file (`:1-10,96-139,204-230`); `emu/Web/devfs.c:12-36` routes stat/open through `weblazysize`/`weblazyfetch`.

Measured `build/site` (manifest `build/site/emu/manifest.json`):

| Item | Bytes |
|---|---|
| `emu/taijios.wasm.gz` | 799,476 |
| `emu/taijios.js` | 53,271 |
| `emu/root.tjr.gz` | 6,552,375 (unpacks to 22,818,904 in 2,415 files) |
| `index.html` + `css/` + `js/` + `assets/` + `emu/manifest.json` | 269,516 |
| **First download (site + emulator + root)** | **≈7.41 MB** |
| `emu/lazy/` (16 bundles) | 16 MB on the server, fetched per app |

Root contents relevant here: `dis/wm/rill.zx` (11,205,643) and `dis/wm/wm.dis` (21,617) are **in** the first download; `dis/wm/explorer.zx`, `taskmgr.zx`, `view.zx`, `about`, `clock`, `counter`, `stopwatch`, `memory`, `logwindow`, `dir`, `tclsh`, `tcltk`, `coffee`, `man`, and the two `dis/math` bundles are **lazy**. Boot is `emu -g WxH wm/wm` (`site/js/taiji-emu.js:327`), i.e. the Dis manager, which is why `wm.dis` is in the root. `dis/lib/{window_chrome,winplace,wm_policy}.zx` are in the root (they are the three ZX libraries the emulator installs today).

The consequence for the owner's goal: the browser downloads a legacy Dis desktop plus Rill before showing anything, and every app after Rill is a one-off 2-8 MB fetch with its own copy of Kryon and std.

---

## Section C. "As modular as possible": what Ziran offers today, and the gap

**What exists (evidence).**

1. A ZX library artifact: `zi2zx --library NAME --export module:function` (`cmd/zi2zx/main.c:27-28,341-346,409-412`), stored as `LOGICAL_NAME.zx` under a module root.
2. Guest-side loading: `std/zx_module.zi` exposes `Load`, `Release`, `ExportCount`, `ExportName`, `ParameterCount`, `ParameterType`, `ResultType`, `Replace`, `Problem`; a module import is declared as a `u64` handle plus typed parameters and bound with `--require-module IFACE=NAME` and `--import caller:fn=IFACE:Export` (`docs/ZX.md:11-61`). The loader verifies dependency graphs and import signatures before any initializer runs, and each `Load` creates independent state.
3. Embedding-side loading: `include/ziran_zx_module.h` offers roots, a resolver, `library_bindings`, `ZxModuleProgramOpen/Run`, `ZxModuleLoad/Release/Call/Replace`, export inspection and controlled runs. Library host calls are refused unless the loader was given an explicit grant: `OpenImage` fails with "ZX module %s needs one loader host binding for %s:%s" (`cmd/compiler_host_api_linkage.zi:734-741`, `LibraryBinding` `:697-712`).
4. Pinned distribution: `ziran pkg zx pack-ir/publish-ir/fetch-ir/inspect-ir` for checked libraries and `ziran pkg zx publish/fetch` for runtime `.zx` libraries, addressed by repository, commit, profile and SHA-256 (`docs/PACKAGES.md:480-700`). `ziran.zx.lock` pins interfaces, names, commits, profiles and digests, and injects `--require-module`/`--import` at build time (`cmd/package_zx.zi:630-704`).
5. What was removed and must not be assumed: commit `cb0a762f` ("Migrate to one ZX format and delete the old route", 2026-11-14) deleted *bundle libraries* together with the portable VM, `BundleInstantiatePortable`, `libziran-vm.a` and the ZIR-based Wasm lowering. The current library route is the revision-28 one described above; there is no second route.

**The gap, precisely.**

- G1. **The project-level build cannot emit a library.** Every repository in scope uses `ziran bundle --project`. `ziran bundle` requires `--entry module:function` and has no `--library` form (`PkgUsage`, `cmd/package.zi:817`); the `--library` route exists only in `zi2zx` (`cmd/zi2zx/main.c:27-28`), which rejects `--library` together with `--entry` (`:409-412`). (`ziran build` infers `--entry` for native/Wasm output only — `cmd/package.zi:420-464` — so it does not help either.) `ziran bundle --library` is therefore not a supported invocation, and no repository can produce a shareable library through its normal build tool.
- G2. **`std` and Kryon are source-linked, not installed-once.** `#import "std/NAME"` resolves through the compiler's std tree at build time; there is no std `.zx` library, no per-module packaging of std, and no repo-level pin. The same holds for Kryon: `kryonlabs/kryon/ziran.toml:212` exports `host/surface` as **source**, and every app links the Kryon modules it reaches. That is why `rill.zx` is 11 MB, `inbe.zx` 129 MB, and each `dis/wm/*.zx` is 3-11 MB.
- G3. **A shared library cannot use host capabilities without a grant, and TaijiOS grants none.** `emu/port/zx.c:3686-3693` opens the loader with roots fixed to `/dis/lib`, a resolver `zxread`, and a write callback, but **no** `library_bindings`. Any library that calls a host function is therefore refused at open. So a shared UI library (the only kind that would shrink the bundles) cannot be installed today even if it were built.
- G4. **Nothing validates library/toolchain agreement at runtime.** A library built by another toolchain revision is only caught by the bundle's own revision check; nothing in TaijiOS compares the library's declared package/toolchain identity with the app's, and no repo uses `ziran.zx.lock`.
- G5. **The ZX subset still excludes the constructs the libraries would need for anything but pure computation.** `isize`/`usize` and functions outside the verifier subset are rejected, and `#c_call` is native-only (`ASSEMBLY/feature-matrix.md:36,72`). Std modules used by every app (`std/file_linux`, `std/parallel_linux`, `std/timer_linux`, `std/c_string`, the HTTP/curl paths) cannot be ZX libraries as written.

**Owner of each gap.** G1, G2, G3 (policy and API), G4 (metadata) and G5 are **Ziran upstream** work (`ziranlang/ziran`, and `kryonlabs/kryon` for the Kryon split). TaijiOS owns only the guest-side half of G3 — passing grants and extra roots in `emu/port/zx.c` — and that file is owned by the existing porting tasks, so it is not assignable here (see X1 in Section E).

---

## Section D. Can the Ziran toolchain run inside TaijiOS as ZX?

**What exists.** (1) The runtime that would execute it is already inside `emu`: `build/host32/libziran.a` linked into the emulator (`mkconfig:36-37`, `emu/Linux/mkfile:45,52-54`). (2) The compiler's middle and back ends are Ziran source: `cmd/compiler_*.zi` (`compiler_zir_lower`, `compiler_lowered_*`, `compiler_exec*`, `compiler_opt*`, `compiler_zx_run`, `compiler_host_api*`), generated to C by `zi2c` and compiled by `assembly.mk`. (3) The ZX command runner exists as a Ziran module (`cmd/compiler_zx_run.zi`), and `std/bundle_guest.zi` declares child-bundle hosting (`Open`, `Restart`, `Close`, asset reads) for a host that grants it. (4) `zx_runner.zi` is a complete `.zi` program that hosts bundles; it is built as a native ELF (`Makefile:703-708`), not as a `.zx`.

**What is missing.**

- M1. The front end, parser, drivers and host I/O are still C: `cmd/zir/` (68k lines per `plans/2026-11-14-self-hosting.md:88-95`), `cmd/zi2zx/main.c` (841 lines), `cmd/zi2c`, `cmd/zi2go`, `cmd/zi2zir`, `cmd/zx2wasm`, `cmd/zx2native`. `plans/open-work.md:33` tracks S16-S18 as open; no `--target=zx` build of any tool exists (`grep 'target=zx' Makefile` → none).
- M2. The ZX subset rejects what the compiler is written in: 29 `cmd/*.zi` files use `#c_call` and 39 use `isize`, both rejected for the ZX target (`ASSEMBLY/feature-matrix.md:36,72`).
- M3. The toolchain needs services the guest does not offer a bundle: `libc` via `#system_library "libc"` (`cmd/zx_runner_capabilities.zi`), POSIX files, process spawn, wall clock with sub-millisecond needs, and a working set far above the 32 MiB default guest pool (`plans/dis-to-zx.md:22`; `README.md:116-119` documents the 128 MiB default and 32 MiB option). `zi2zx` is 4.2 MB of code before any allocation.
- M4. Child-bundle hosting is not granted: `std/bundle_guest` requires a host that answers `OpenChildBundleHost` and friends, and `emu/port/zx.c` binds no such module, so even a hypothetical `zi2zx.zx` could not run the bundle it just wrote.

**Answer.** Not today. What exists is the *runtime* half (engine, bundle reader/writer, ZX command runner module) and a `.zi` runner that is compiled natively. What is missing is the *front end and drivers* in Ziran (Ziran upstream, M1-M2), plus two TaijiOS-side grants: a `libc`-equivalent capability set over `taijios_io`/`taijios_clock`/`taijios_process`, and child-bundle hosting (M3-M4). Both of the latter live in `emu/port/zx.c`, so they belong to the existing porting tasks.

---

## Section E. Implementation contracts, dependency ordered

Rules for every contract: work in the repository's own checkout on `master` with the shared index; add only your own paths; do not create clones or worktrees. Put temporary output in `$COMMANDCODE_SCRATCHPAD`, never in a shared `build/` (use `--output-root`, `-o $SCRATCH/...`, or the project's documented scratch target). Contracts marked **[upstream]** must land before any contract that lists them. Contracts marked **[not assignable]** touch files owned by the existing TaijiOS porting tasks (`appl/wm/**`, `appl/cmd/**`, `appl/lib/**`, `emu/port/zx.c`, `dis/**`, `plans/dis-to-zx.md`) and are listed only so the dependency is visible.

Parallel groups: **U** (Ziran upstream; one lane, ordered), **K** (Kryon upstream; after U1), **P1-P6** (one repository each; parallel with each other after U1/K1), **T** (TaijiOS-owned free files: `tools/`, `lib/apps/`, `site/`, `emu/Web/`, `tests/`; parallel with P groups after T1).

### U — Ziran upstream (do these first; everything else depends on the first two)

**U1. [upstream] A project can build a ZX library.**
- Behaviour: `ziran bundle --library NAME --export module:function ... -o FILE.zx` works in a project, forwards `--require-module`/`--import`, and does not inject `--entry`. A library build with an entry is refused with one diagnostic naming both flags.
- Files: `ziranlang/ziran/cmd/package.zi` (usage and entry injection at `:436-461`, `:817`), `cmd/package_zx.zi` (forwarding), `docs/ZX.md`, `docs/PACKAGES.md`.
- Add: accept the library form in the `bundle` command path; keep `zi2zx` as the single implementation.
- Test: `make -C /mnt/storage/Projects/ziranlang/ziran check CHECK_FILTER=zx` and a new `tests/zx_module_build.sh` that builds `counter.zx`, loads it from a consumer with `ziran run --module-root`, and checks the refusal case.
- Done: a repository with a `ziran.toml` can emit a library with no hand-written `zi2zx` line, and the new test passes.

**U2. [upstream] `std` modules can be shipped as pinned ZX libraries.**
- Behaviour: a documented choice — either `ziran pkg zx` can pack selected `std` modules as libraries, or `docs/PACKAGES.md` states that `std` stays source-linked — with the build flags and pins for the portable subset modules (`std/vec`, `std/text*`, `std/json*`, `std/base64`, `std/crc`, `std/png`, `std/jpeg`, `std/crypto`-adjacent).
- Files: `cmd/package_zx.zi`, `docs/PACKAGES.md`, `docs/ZX.md`, `Makefile`.
- Test: `make -C ... check CHECK_FILTER=package`, plus a consumer bundle built with the packed std and run with `--module-root`.
- Done: the decision is written, and if libraries are chosen, one std module round-trips through pack/fetch/load in a test.
- Blocks: P1-P6 only if the decision is "libraries". G2 is otherwise closed as "declared out of scope".

**U3. [upstream] The ZX subset covers the compiler's own constructs.**
- Behaviour: `isize`/`usize` (pointer-sized scalars) are accepted and verified on the ZX target, or a named diagnostic states the supported substitute; `#c_call` keeps its named rejection.
- Files: `cmd/compiler_check_s12_types.zi`, `cmd/compiler_lowered_verify.zi`, `cmd/compiler_zir_lower.zi`, `docs/ZX.md`, `tests/`.
- Test: `make -C ... check CHECK_FILTER=lowered` and the verifier cases that list the rejected subset.
- Done: the feature table row for pointer-sized scalars changes with a fixture that exercises it.
- Blocks: U4.

**U4. [upstream] Self-hosting S16-S18: the toolchain can be built as ZX.**
- Behaviour: the remaining compiler C and drivers move to Ziran, and `make zx-toolchain` writes `zi2zx.zx` (and `ziran`'s command surface) that builds and runs a bundle inside a ZX host.
- Files: `cmd/zir/*.c`, `cmd/zi2zx/main.c` → `cmd/zi2zx/main.zi`, `cmd/compiler_host_api*.zi`, `Makefile`, `plans/2026-11-14-self-hosting.md`, `plans/open-work.md:33`.
- Test: `make -C ... check-bootstrap` plus a new `make zx-toolchain-test` that builds `hello.zx` with `zi2zx.zx` under the engine and compares bytes with the native `zi2zx`.
- Done: the fixed-point check passes and `zi2zx.zx` builds and runs one bundle. Needs U3 and X2 (child-bundle hosting) to run a produced bundle in a guest.
- Blocks: Section D's answer changes from "not today" to "yes"; no app contract depends on it.

**U5. [upstream] Library host grants are a documented, testable policy.**
- Behaviour: a host states, per library, which `module:function` grants it gives; the loader refuses anything else with the existing message; the docs show a host granting one capability and refusing a second.
- Files: `include/ziran_zx_module.h`, `cmd/compiler_host_api_linkage.zi`, `docs/ZX.md`, `tests/bundle_*`.
- Test: `make -C ... check CHECK_FILTER=host` and the module-grant fixture.
- Done: the grant path has a positive and a negative test, and the docs name the API. Blocks: X1 and T-side enablement of shared UI libraries.

### K — Kryon upstream (after U1)

**K1. Kryon ships portable halves as ZX libraries.**
- Behaviour: `make zx-libraries` writes `kryon-pixmap.zx`, `kryon-session.zx`, `kryon-tree.zx`, `kryon-text.zx` with explicit export roots, loadable from a module root; the UI widgets keep one implementation.
- Files: `kryonlabs/kryon/Makefile`, `mk/zx-player.mk`, `ziran.toml` (`[exports]`, `[tool.kryon]`), `docs/BACKENDS.md`.
- Test: `make -C /mnt/storage/Projects/kryonlabs/kryon zx-test` plus a new consumer example under `examples/` loaded with `ziran run --module-root`.
- Done: an example app links the four libraries at run time and its frame hash matches the statically linked build.

**K2. One portable surface contract, no duplicate ABI.**
- Behaviour: the `zx_surface` module TaijiOS already binds (`emu/port/zx.c:3418,3478`) stays the only surface ABI; Kryon's `host/surface` export is documented as the same four capabilities plus the retained strip entries, and the Kryon `zx_run` frame host becomes an optional module rather than the default.
- Files: `kryonlabs/kryon/src/backend/zx_surface.zi`, `docs/BACKENDS.md`, `ziran.toml`.
- Test: `make -C ... zx-test zx-window-test`.
- Done: a bundle built with only `RunRetainedRows` runs unmodified on TaijiOS and on Kryon's `zx` player against the same host bindings. Blocks: P1-P6 (they target this ABI).

### T — TaijiOS-owned free files (parallel with P after T1)

**T1. A preinstall manifest the catalog and the web build both read.**
- Behaviour: one tracked file, `lib/preinstall.list`, lists every app to preinstall with `repo`, `bundle path`, `desktop id`, `Name`, `Icon`, `Categories`, `size`, `sha256`, and `first-run` (`root` or `lazy`). `tools/generate-app-catalog.py` gains `--preinstall lib/preinstall.list` and emits an entry only when the named bundle exists in the output root, leaving every other entry untouched.
- Files: `lib/preinstall.list` (new), `tools/generate-app-catalog.py` (`generate_catalog`, `:159-203`; `main`, `:228-248`), `lib/apps/*.desktop`, `tests/desktop/README.md`.
- Add: `generate_preinstall_catalog(output, manifest)`; `--preinstall` mode.
- Test: `PYTHONDONTWRITEBYTECODE=1 python3 tools/generate-app-catalog.py --preinstall lib/preinstall.list --output-root $COMMANDCODE_SCRATCHPAD/catalog && python3 tests/desktop/catalog_preinstall_test.py $COMMANDCODE_SCRATCHPAD/catalog` (new test: every row's `Exec` exists, ids are stable, a second run is byte-identical, a missing bundle emits nothing).
- Done: the manifest drives the catalog, the test passes, and no existing entry changes.

**T2. The web root and the lazy set follow the manifest.**
- Behaviour: `site/root.list` admits apps only through the manifest's `first-run` column; a new `site/tools/rootlist.zi` (or an added mode in `site/tools/rootpack.zi`) generates the `dis/…` lines so the list cannot drift from `lib/preinstall.list`. Rill stays in the root; every other app bundle is `lazy`.
- Files: `site/root.list`, `site/tools/rootpack.zi`, `site/tools/sitebuild.zi`, `site/Makefile`.
- Test: `make -C /mnt/storage/Projects/taijiosnet/taijios/site test` (writes `build/site`; run it only when the shared build directory is yours, otherwise stop at `tools/sitebuild` into a scratch output).
- Done: `make -C site site` writes a root whose `lazy` set matches the manifest, and the first download shrinks or stays flat while the manifest grows.

**T3. A first-download budget with a measured check.**
- Behaviour: `site/tools/sitebuild.zi` fails when `root.tjr.gz` exceeds a stated budget (start at 6.5 MB) or when the sum of root + wasm + js + page exceeds 8 MB, and prints both numbers.
- Files: `site/tools/sitebuild.zi`, `site/README.md`.
- Test: `make -C site site` on a scratch output plus a deliberately oversized fixture that must fail.
- Done: the build refuses a larger root with a message naming the file that grew.

**T4. Preinstall verification: every listed bundle exists, is revision 28, and declares only granted capabilities.**
- Behaviour: a test walks `lib/preinstall.list`, reads each bundle's header and capability list through `zi2zx --emit`/the bundle metadata, and fails on a revision mismatch or on any capability outside the granted set (Section A table).
- Files: `tests/desktop/preinstall_test.py` (new), `tests/desktop/README.md`, `lib/preinstall.list`.
- Test: `PYTHONDONTWRITEBYTECODE=1 python3 tests/desktop/preinstall_test.py lib/preinstall.list` (and a fixture bundle with a `guest_window` capability that must fail).
- Done: the test passes on the three bundles that do run (explorer, rill, taskmgr) and fails on a Kryon `zx_run` bundle, which is the current truth.

**T5. `P` contract index and ownership note in the repo.**
- Behaviour: `plans/ecosystem-preinstall.md` (this file) keeps the manifest format and the granted-capability set as the single reference; `tests/desktop/README.md` links it.
- Files: `tests/desktop/README.md`.
- Test: `git diff --check`.
- Done: the link exists; no other change.

### P — one repository per contract, all parallel after U1/K1/K2

Shared shape for every P contract: add a `taiji` make target that builds an entry using `kryon/host/surface` (`RunRetainedRows` or `RunRetainedPixels`) and `--bind-host taijios_*` only for modules in the Section A granted table; write `build/taiji/<name>.zx` (not into a shared directory); run it in a private guest with a scrubbed display; record size and sha256 in the repository's `CHANGELOG.md` under `Unreleased`. Test command shape: `make taiji` then `TAIJIOS_ROOT=... TAIJIOS_EMULATOR=... python3 <repo test>`. Done: the bundle runs, the window draws, input reaches it, and the size is recorded.

| # | Repo | Files | Target/entry to add | Test | Depends on |
|---|---|---|---|---|---|
| P1 | kryonlabs/explorer | already done; add the preinstall row only | — | `make test-taiji-model test-taiji-desktop` | T1 |
| P2 | kryonlabs/rill | `scripts/package-taiji.sh`, `build/rill.zx` receipt | record the installed bundle's sha256 and reproduce it | `TAIJIOS_MODULES=.../appl/cmd sh scripts/package-taiji.sh`, then guest boot | U1 (library), T1 |
| P3 | kryonlabs/terminal | `src/app/terminal_zx_player.zi` + a new `src/app/taiji_surface.zi`, `Makefile` `taiji:` | `taiji_host:main` on `zx_surface` | `make taiji zx-window-test` then guest run | K2 |
| P4 | kryonlabs/browser, kryonlabs/telegram | `src/app.zi` Taiji host entry per repo, `Makefile` | `taiji_host:main` | `make zx zx-window-test` then guest run | K2 |
| P5 | kryonlabs/gitnex, kryonlabs/workbook | `src/app.zi`, `Makefile` | `taiji_host:main`; workbook must first stop writing `.zib` | `make build test` then guest run | K2 |
| P6 | waozixyz/modules/entity, waozixyz/modules/auth | `src/entity.zi`, `src/auth.zi`, `Makefile` | `Main` on `app_registry` + `zx_surface` for the shell | `make test` then guest run | P1, K2 |
| P7 | waozixyz/apps/werk, waozixyz/apps/photos, waozixyz/apps/relay, waozixyz/apps/breeze | per-app `Makefile`, `src` | host entry per app; breeze port targets the apps controller, not one 129 MB bundle | `make test` per app then guest run | P6 |
| P8 | waozixyz/modules/apps (collection host) | `src/node_app.zi`, `src/host.zi`, `Makefile` | an `app_registry`-backed `ReadAppHost`/`WriteAppHost` host | `make fixture-test` then one game launched from the host | P6 |
| P9 | waozixyz/games/apple, choano, wurm, shovey | `Makefile`, `ziran.toml` | `[tool.kryon.profiles.taiji] backend="desktop" codegen="zx"` + `taiji` target | `make portable` then guest run | K2, P8 |
| P10 | waozixyz/learning/jungle | `Makefile:118-122,161` | `taiji` target for the 15 game bundles, one scene first | `make all` then one bundle in a guest | K2, P8 |
| P11 | waozixyz/games/voyki, katalis, zoombinis | `ziran.toml`, `Makefile` | `codegen="zx"` Taiji profile | `kryon build portable` then guest run | K2 |
| P12 | waozixyz/games/arcade | `Makefile`, `scripts/build-desktop.py` | Taiji collection entry | `make all` then guest run | P8 |
| P13 | waozixyz/games/garden, neon, kasaival | `port/*.zi` or `src/` surface layer | replace raylib/Game2D host with `kryon/host/surface` | `make test` then guest run | K2; these are rewrites, size accordingly |
| P14 | waozixyz/games/shark | none until it is a repository | — | — | **unknown**: decide whether shark is tracked |
| P15 | waozixyz/modules/practices | `figure/*` GL link list | remove the GL dependency or provide a portable renderer | `make test` after reconciling 2011 dirty paths | **unknown** until the checkout is reconciled |
| P16 | ziranlang/packages (21) | `Makefile` per package | a `--library` target for the portable packages | `make portable`/`test` per package | U1, U2 |
| P17 | kryonlabs/showcase, kryonlabs/agentlab, kryonlabs/github | — | a catalog/viewer entry instead of a bundle (showcase is JSON; agentlab is static sites; github is superseded) | `python3 scripts/validate.py` (showcase) | T1 |

### X — visible but not assignable here (owned by the existing TaijiOS porting tasks)

**X1. Guest-side library grants and extra module roots.**
- Behaviour: before opening a program, the guest builds `ZxModuleLoaderConfig.library_bindings` from a table of `(module, function, capability)` grants and accepts additional `-m` roots beside `/dis/lib`, so an installed shared UI library can draw.
- Files: `emu/port/zx.c` (owner: desktop core / porting tasks), `appl/cmd/**` for any `-m` parsing.
- Test: extend `tests/desktop/zx_boot_test.py` with a library that draws and one that asks for an ungranted function.
- Done: a shared library draws and an ungranted call is refused. **Needed by** U5's consumers and any "install Kryon once" claim.

**X2. Child-bundle hosting for a ZX host.**
- Behaviour: the guest answers `std/bundle_guest` (`OpenChildBundleHost`, `RestartChildBundleHost`, `CloseChildBundleHost`, asset reads) so a bundle can run a produced bundle.
- Files: `emu/port/zx.c` (owner: porting tasks), plus `appl/cmd` if a module file is needed.
- Test: a bundle that opens `hello.zx` and reports its exit value, in `zx_boot_test.py`.
- Done: the nested run works under the engine with a step budget. **Needed by** U4.

**X3. `wm.zx` install and the catalog entries the generator cannot see.**
- Behaviour: `install-wm-zx` runs so the session is ZX-native, and the catalog gains `rill` and a Terminal entry.
- Files: `appl/wm/mkfile` (owner: desktop core), `lib/apps/*.desktop` (free, via T1).
- Test: `python3 tests/desktop/zx_boot_test.py --graphics`.
- Done: the boot log reports `Initial ZX: "/wm.zx"`. **Not assignable** because `appl/wm/mkfile` belongs to the desktop-core owner; the catalog half is T1.

### Ordering summary

1. **U1** (library build) — nothing else can be "installed once" without it.
2. **U2, U3, U5** in parallel with **K1**; **K2** after K1; **U4** after U3 and X2.
3. **T1** (manifest) first among T; then **T4** (verification) and **T2/T3** (web) in parallel.
4. **P1, P2** immediately (they already work; they only need the manifest and a receipt); **P6, P8** next; **P9-P12** after P8; **P13, P15-P17** last or after an explicit decision; **P14** blocked on a repository decision.
5. **X1** gates the modularity goal at run time; **X2** gates U4; **X3** gates the ZX-native session. None of the three is assignable from this plan.

### Explicit unknowns

- Whether `dis/wm/rill.zx` and `dis/wm/taskmgr.zx` were built from the current repo commits (sha256 differs; no saved receipt in either repository). Establishing it: rebuild each with its `taiji` script at the pinned commit and compare sha256.
- Whether the three guest tests (explorer, rill, taskmgr) last passed. Establishing it: rerun `make test-taiji-model`, `scripts/guest-lifecycle-test.py`, and a Rill guest boot on a private Xvfb and keep the log.
- `waozixyz/games/shark`: not a git repository; its provenance and therefore its pin are unknown.
- `waozixyz/modules/practices`: 2011 dirty paths make its current source state unknown; a port cannot be planned until the checkout is reconciled.
- Revisions of the package test bundles (av1, avif, image-codec, compression, crypto, mermaid, noise, qrcode, syntax, tcl, tk, webp, audio): first 8 bytes were not read, so whether each is rev 28 is unknown. Establishing it: read `ZX\0\0` + revision for each artifact listed in Section A.5.
