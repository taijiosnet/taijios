// Boots the TaijiOS hosted emulator (emu/Web) on a canvas.
//
// startTaiji(canvas, {onProgress, onStatus}) downloads the emulator and its
// root bundle (both gzip, listed with sizes in emu/manifest.json), writes the
// root files into the emulator's in-memory filesystem at /taiji and runs
// `emu -g WxH wm/wm`, which starts the Rill desktop. The emulator draws into
// shared wasm memory; this module copies changed pixels to the canvas once
// per animation frame and forwards pointer and keyboard input.

const BASE = new URL('../emu/', import.meta.url);

// Word offsets in the WebShared block of emu/Web/win-web.c.
const W = {
  width: 0, height: 1, pixels: 2, dirtylock: 3, dirty: 4, frame: 8, head: 9, tail: 10,
  cursor: 11, cursorw: 12, cursorh: 13, hotx: 14, hoty: 15, cursorpixels: 16,
  snarflock: 17, snarf: 18, snarflen: 19, ring: 20
};
const RING = 512;
const EVENT_WORDS = 5;
const CURSOR_SIDE = 32;
const EV = { pointer: 1, key: 2, text: 3, focusout: 4 };
const DOUBLE_CLICK_MS = 300;

// Key numbers the guest's /dev/keyevent uses (see the X11 table in win-x11a.c).
const NAMED_KEYS = {
  Escape: 256, Enter: 257, Tab: 258, Backspace: 259, Insert: 260, Delete: 261,
  ArrowRight: 262, ArrowLeft: 263, ArrowDown: 264, ArrowUp: 265, PageUp: 266,
  PageDown: 267, Home: 268, End: 269, ShiftLeft: 340, ControlLeft: 341,
  AltLeft: 342, ShiftRight: 344, ControlRight: 345, AltRight: 346
};
// Runes for keys without text (include/keyboard.h).
const SPEC = 0xe000, VIEW = SPEC | 0x10;
const KEY_RUNES = {
  Escape: 0x1b, Enter: 0x0a, Tab: 0x09, Backspace: 0x08, Delete: 0x7f,
  Home: VIEW | 0, End: VIEW | 1, ArrowUp: VIEW | 2, ArrowDown: VIEW | 3,
  ArrowLeft: VIEW | 4, ArrowRight: VIEW | 5, PageUp: VIEW | 6, PageDown: VIEW | 7,
  Insert: SPEC | 0x63
};

function keyNumber(event) {
  if (NAMED_KEYS[event.code] !== undefined) return NAMED_KEYS[event.code];
  if (NAMED_KEYS[event.key] !== undefined) return NAMED_KEYS[event.key];
  if (/^Key[A-Z]$/.test(event.code)) return event.code.charCodeAt(3);
  if (/^Digit[0-9]$/.test(event.code)) return event.code.charCodeAt(5);
  if (/^F([1-9]|1[0-9]|2[0-5])$/.test(event.key)) return 289 + Number(event.key.slice(1));
  if (event.key.length === 1) {
    const code = event.key.toUpperCase().codePointAt(0);
    if (code >= 0x20 && code <= 0x7e) return code;
  }
  return 0;
}

function keyRune(event) {
  if (KEY_RUNES[event.key] !== undefined) return KEY_RUNES[event.key];
  if ([...event.key].length !== 1) return 0;
  let rune = event.key.codePointAt(0);
  if (event.ctrlKey && !event.altKey && rune < 0x80) rune &= 0x9f;
  return rune;
}

function modifiers(event) {
  return (event.shiftKey ? 1 : 0) | (event.ctrlKey ? 2 : 0) | (event.altKey ? 4 : 0);
}

async function fetchBytes(url, size, report) {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`${url.pathname} answered ${response.status}`);
  const reader = response.body.getReader();
  const parts = [];
  let received = 0;
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    parts.push(value);
    received += value.length;
    report(Math.min(received, size));
  }
  let bytes = new Uint8Array(received);
  let at = 0;
  for (const part of parts) { bytes.set(part, at); at += part.length; }
  // A server may already have removed the gzip layer.
  if (bytes[0] === 0x1f && bytes[1] === 0x8b) {
    const stream = new Blob([bytes]).stream().pipeThrough(new DecompressionStream('gzip'));
    bytes = new Uint8Array(await new Response(stream).arrayBuffer());
  }
  return bytes;
}

// The root bundle: "TJR1", a u32 entry count, then per entry a u8 kind
// (0 file, 1 directory), u16 path length, path, u32 size and the bytes.
// WASMFS queues files and directories created before the runtime starts and
// adds them to its in-memory tree as it initialises.
function unpackRoot(FS, bytes, top) {
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  const magic = String.fromCharCode(...bytes.subarray(0, 4));
  if (magic !== 'TJR1') throw new Error('bad root bundle');
  const count = view.getUint32(4, true);
  const decoder = new TextDecoder();
  const made = new Set(['/']);
  const mkdir = (path) => {
    if (made.has(path)) return;
    const cut = path.lastIndexOf('/');
    const parent = cut > 0 ? path.slice(0, cut) : '/';
    mkdir(parent);
    FS.createPath(parent, path.slice(cut + 1), true, true);
    made.add(path);
  };
  mkdir(top);
  let at = 8;
  for (let index = 0; index < count; index++) {
    const kind = bytes[at];
    const length = view.getUint16(at + 1, true);
    const path = top + '/' + decoder.decode(bytes.subarray(at + 3, at + 3 + length));
    at += 3 + length;
    const size = view.getUint32(at, true);
    at += 4;
    if (kind === 1) {
      mkdir(path);
    } else {
      const cut = path.lastIndexOf('/');
      mkdir(path.slice(0, cut));
      FS.createDataFile(path.slice(0, cut), path.slice(cut + 1), bytes.subarray(at, at + size), true, true, true);
    }
    at += size;
  }
}

function screenSize(canvas) {
  const box = canvas.parentElement.getBoundingClientRect();
  let width = Math.round(box.width) || 1024;
  let height = Math.round(box.height) || 640;
  width = Math.max(800, Math.min(1600, width)) & ~3;
  height = Math.max(560, Math.min(1000, height));
  return { width, height };
}

class Screen {
  constructor(module, canvas, block) {
    this.module = module;
    this.canvas = canvas;
    this.base = block >> 2;
    this.context = canvas.getContext('2d', { alpha: false });
    this.lastFrame = -1;
    this.lastCursor = -1;
    this.lastButton = 0;
    this.lastPress = 0;
    this.buttons = 0;
    const i32 = this.words();
    this.width = i32[this.base + W.width];
    this.height = i32[this.base + W.height];
    canvas.width = this.width;
    canvas.height = this.height;
    this.image = this.context.createImageData(this.width, this.height);
    this.rgba = new Uint32Array(this.image.data.buffer);
    this.draw = this.draw.bind(this);
    requestAnimationFrame(this.draw);
    this.listen();
  }

  // Views over the shared memory, renewed whenever a worker grew it.
  words() {
    const buffer = this.module.wasmMemory.buffer;
    if (!this.i32 || this.i32.byteLength !== buffer.byteLength) {
      this.i32 = new Int32Array(buffer);
      this.u8 = new Uint8Array(buffer);
    }
    return this.i32;
  }

  bytes() { this.words(); return this.u8; }

  draw() {
    const i32 = this.words();
    const b = this.base;
    const frame = Atomics.load(i32, b + W.frame);
    if (frame !== this.lastFrame && Atomics.compareExchange(i32, b + W.dirtylock, 0, 1) === 0) {
      const x0 = i32[b + W.dirty], y0 = i32[b + W.dirty + 1];
      const x1 = i32[b + W.dirty + 2], y1 = i32[b + W.dirty + 3];
      i32[b + W.dirty] = 0; i32[b + W.dirty + 1] = 0; i32[b + W.dirty + 2] = 0; i32[b + W.dirty + 3] = 0;
      this.lastFrame = frame;
      if (x1 > x0 && y1 > y0) this.copy(i32, x0, y0, x1, y1);
      Atomics.store(i32, b + W.dirtylock, 0);
      if (x1 > x0 && y1 > y0)
        this.context.putImageData(this.image, 0, 0, x0, y0, x1 - x0, y1 - y0);
      if (this.onFirstFrame) { const first = this.onFirstFrame; this.onFirstFrame = null; first(); }
    }
    const cursor = Atomics.load(i32, b + W.cursor);
    if (cursor !== this.lastCursor) { this.lastCursor = cursor; this.setCursor(i32); }
    requestAnimationFrame(this.draw);
  }

  // XRGB32 little-endian words to opaque RGBA words.
  copy(i32, x0, y0, x1, y1) {
    const pixels = i32[this.base + W.pixels] >> 2;
    const width = this.width, rgba = this.rgba;
    for (let y = y0; y < y1; y++) {
      let from = pixels + y * width + x0;
      let to = y * width + x0;
      for (let x = x0; x < x1; x++) {
        const v = i32[from++];
        rgba[to++] = 0xff000000 | (v & 0xff00) | ((v >> 16) & 0xff) | ((v & 0xff) << 16);
      }
    }
  }

  setCursor(i32) {
    const b = this.base;
    const w = i32[b + W.cursorw], h = i32[b + W.cursorh];
    if (w === 0 || h === 0) { this.canvas.style.cursor = 'default'; return; }
    const from = i32[b + W.cursorpixels];
    const art = document.createElement('canvas');
    art.width = w; art.height = h;
    const picture = art.getContext('2d').createImageData(w, h);
    const heap = this.bytes();
    for (let y = 0; y < h; y++)
      picture.data.set(heap.subarray(from + y * CURSOR_SIDE * 4, from + (y * CURSOR_SIDE + w) * 4), y * w * 4);
    art.getContext('2d').putImageData(picture, 0, 0);
    const hx = Math.max(0, Math.min(w - 1, -i32[b + W.hotx]));
    const hy = Math.max(0, Math.min(h - 1, -i32[b + W.hoty]));
    this.canvas.style.cursor = `url(${art.toDataURL()}) ${hx} ${hy}, default`;
  }

  push(type, a = 0, b = 0, c = 0, d = 0) {
    const i32 = this.words();
    const base = this.base;
    const head = Atomics.load(i32, base + W.head);
    const tail = Atomics.load(i32, base + W.tail);
    if (head - tail >= RING) return;
    const slot = base + W.ring + (head & (RING - 1)) * EVENT_WORDS;
    i32[slot] = type; i32[slot + 1] = a; i32[slot + 2] = b; i32[slot + 3] = c; i32[slot + 4] = d;
    Atomics.store(i32, base + W.head, head + 1);
    Atomics.notify(i32, base + W.head);
  }

  point(event) {
    const box = this.canvas.getBoundingClientRect();
    const x = Math.floor((event.clientX - box.left) * this.width / box.width);
    const y = Math.floor((event.clientY - box.top) * this.height / box.height);
    return [Math.max(0, Math.min(this.width - 1, x)), Math.max(0, Math.min(this.height - 1, y))];
  }

  listen() {
    const canvas = this.canvas;
    canvas.tabIndex = 0;
    const pointerBits = (event) => (event.buttons & 1) | ((event.buttons & 4) ? 2 : 0) | ((event.buttons & 2) ? 4 : 0);
    canvas.addEventListener('contextmenu', (event) => event.preventDefault());
    canvas.addEventListener('pointerdown', (event) => {
      canvas.focus();
      canvas.setPointerCapture(event.pointerId);
      event.preventDefault();
      const [x, y] = this.point(event);
      let bits = pointerBits(event);
      const now = performance.now();
      if (event.button === this.lastButton && now - this.lastPress < DOUBLE_CLICK_MS) bits |= 1 << 8;
      this.lastButton = event.button;
      this.lastPress = now;
      this.push(EV.pointer, bits, x, y);
    });
    const move = (event) => {
      const [x, y] = this.point(event);
      this.push(EV.pointer, pointerBits(event), x, y);
    };
    canvas.addEventListener('pointermove', move);
    canvas.addEventListener('pointerup', move);
    canvas.addEventListener('wheel', (event) => {
      event.preventDefault();
      const [x, y] = this.point(event);
      const bit = event.deltaY < 0 ? 8 : 16;
      this.push(EV.pointer, bit, x, y);
      this.push(EV.pointer, 0, x, y);
    }, { passive: false });
    canvas.addEventListener('keydown', (event) => {
      if (event.isComposing) return;
      event.preventDefault();
      this.push(EV.key, 1, keyNumber(event), modifiers(event), keyRune(event));
    });
    canvas.addEventListener('keyup', (event) => {
      event.preventDefault();
      this.push(EV.key, 0, keyNumber(event), modifiers(event), 0);
    });
    canvas.addEventListener('compositionend', (event) => {
      for (const ch of event.data || '') this.push(EV.text, ch.codePointAt(0));
    });
    canvas.addEventListener('blur', () => this.push(EV.focusout));
    canvas.addEventListener('paste', (event) => {
      const text = event.clipboardData.getData('text/plain');
      if (text) this.module._taiji_web_paste(this.module.stringToNewUTF8(text));
    });
  }

  // The guest wrote its snarf buffer: offer it to the page's clipboard.
  snarfed() {
    const i32 = this.words();
    const address = i32[this.base + W.snarf];
    const length = i32[this.base + W.snarflen];
    if (!address || !navigator.clipboard) return;
    const text = new TextDecoder().decode(this.bytes().slice(address, address + length));
    navigator.clipboard.writeText(text).catch(() => {});
  }
}

export async function startTaiji(canvas, { onProgress = () => {}, onStatus = () => {} } = {}) {
  if (!globalThis.crossOriginIsolated)
    throw new Error('This page needs cross-origin isolation (COOP/COEP) for shared memory.');
  onStatus('loading');
  const manifest = await (await fetch(new URL('manifest.json', BASE))).json();
  const total = manifest.files.reduce((sum, file) => sum + file.size, 0);
  const done = {};
  const report = (name) => (bytes) => {
    done[name] = bytes;
    onProgress(Object.values(done).reduce((a, b) => a + b, 0), total);
  };
  const entry = (name) => manifest.files.find((file) => file.name === name);
  const wasmFile = entry('taijios.wasm.gz'), rootFile = entry('root.tjr.gz');
  const [wasmBytes, rootBytes, factory] = await Promise.all([
    fetchBytes(new URL(wasmFile.name, BASE), wasmFile.size, report(wasmFile.name)),
    fetchBytes(new URL(rootFile.name, BASE), rootFile.size, report(rootFile.name)),
    import(new URL('taijios.js', BASE).href).then((module) => module.default)
  ]);
  onStatus('starting');
  const { width, height } = screenSize(canvas);
  let screen = null;
  let firstFrame, failed;
  const painted = new Promise((resolve, reject) => { firstFrame = resolve; failed = reject; });
  const wasmModule = await WebAssembly.compile(wasmBytes);
  const config = {
    arguments: ['-g', `${width}x${height}`, 'wm/wm'],
    instantiateWasm(imports, receive) {
      WebAssembly.instantiate(wasmModule, imports).then((instance) => receive(instance, wasmModule));
      return {};
    },
    preRun: [(m) => {
      unpackRoot(m.FS, rootBytes, '/taiji');
      // Applications left on the server: emu/Web/lazy.c fetches them on first open.
      const lines = [new URL('lazy', BASE).href, ...(manifest.lazy || []).map((file) => `${file.size} ${file.path}`)];
      m.FS.createDataFile('/', 'lazy.list', new TextEncoder().encode(lines.join('\n') + '\n'), true, false, true);
    }],
    print: (text) => console.log(text),
    printErr: (text) => console.warn(text),
    taijiScreen(block) {
      screen = new Screen(config, canvas, block);
      screen.onFirstFrame = firstFrame;
    },
    taijiSnarf() { if (screen) screen.snarfed(); },
    taijiExit(code) { onStatus(`stopped (${code})`); },
    onAbort(what) { failed(new Error(`the emulator stopped: ${what}`)); }
  };
  const module = await factory(config);
  await painted;
  onStatus('running');
  canvas.focus();
  return { module, get screen() { return screen; } };
}
