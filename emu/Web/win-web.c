/*
 * Draw screen and input for the browser.
 *
 * The screen is an XRGB32 image in wasm memory. flushmemscreen only grows
 * a dirty rectangle in the shared WebShared block; the page's animation
 * loop (emu/Web/taiji-screen.js) copies that rectangle to the canvas.
 * The page writes pointer, key and text events into the same block's ring
 * and wakes the "webinput" kproc, which hands them to the guest exactly
 * as the X11 event threads do.
 */
#include	"dat.h"
#include	"fns.h"
#include	"error.h"

#include	<draw.h>
#include	<memdraw.h>
#include	<cursor.h>
#include	"keyboard.h"

#include	<emscripten.h>
#include	<emscripten/threading.h>

enum {
	Ring = 512,		/* input events, a power of two */
	EventWords = 5,
	CursorSide = 32,

	EvPointer = 1,
	EvKey = 2,
	EvText = 3,
	EvFocusOut = 4,

	/* key codes shared with the X11 key event path */
	KeyLeft = 263,
	KeyRight = 262,
	KeyAltL = 342,
	KeyAltR = 346,
};

typedef struct WebShared WebShared;
struct WebShared
{
	int	width;
	int	height;
	int	pixels;		/* address of the XRGB32 screen */
	int	dirtylock;
	int	dirty[4];	/* min.x min.y max.x max.y; empty when min.x >= max.x */
	int	frame;		/* bumped by every flush */
	int	head;		/* next event slot the page writes */
	int	tail;		/* next event slot webinput reads */
	int	cursor;		/* bumped when the cursor image changes */
	int	cursorw;
	int	cursorh;
	int	hotx;
	int	hoty;
	int	cursorpixels;	/* address of CursorSide*CursorSide RGBA */
	int	snarflock;
	int	snarf;		/* address of the guest's last snarf, UTF-8 */
	int	snarflen;
	int	ring[Ring*EventWords];
};

extern	int	Xsize;
extern	int	Ysize;

char	*gkscanid = nil;	/* no raw scan codes in the browser */

static WebShared shared;
static uchar *screendata;
static uchar cursorrgba[CursorSide*CursorSide*4];
static char *snarf;
static int triedscreen;

static void
spinlock(int *l)
{
	while(__atomic_exchange_n(l, 1, __ATOMIC_ACQUIRE) != 0)
		sched_yield();
}

static void
spinunlock(int *l)
{
	__atomic_store_n(l, 0, __ATOMIC_RELEASE);
}

/* The page calls this once the module is ready; it gives the block's address. */
EMSCRIPTEN_KEEPALIVE int
taiji_web_shared(void)
{
	return (int)&shared;
}

/* Text pasted into the page becomes the guest's snarf buffer. */
EMSCRIPTEN_KEEPALIVE void
taiji_web_paste(char *text)
{
	spinlock(&shared.snarflock);
	free(snarf);
	snarf = text;
	shared.snarf = (int)snarf;
	shared.snarflen = text != nil ? strlen(text) : 0;
	spinunlock(&shared.snarflock);
}

static int
keyswallowed(int down, int key, int modifiers, int queued)
{
	/* As in X11: Ctrl+Alt chords belong to the guest window manager. */
	if(!queued || (modifiers & 6) != 6)
		return 0;
	if(key == KeyAltL || key == KeyAltR)
		return 1;
	if(key == KeyLeft || key == KeyRight){
		if(down)
			gkbdcancelcompose();
		return 1;
	}
	return 0;
}

static void
webevent(int *e)
{
	int queued;

	switch(e[0]){
	case EvPointer:
		mousetrack(e[1], e[2], e[3], 0);
		break;
	case EvKey:
		queued = gkeyevent(e[1] ? 'd' : 'u', e[2], e[3]);
		if(e[1] && e[4] != 0 && !keyswallowed(e[1], e[2], e[3], queued))
			gkbdputc(gkbdq, e[4]);
		break;
	case EvText:
		gkbdputc(gkbdq, e[1]);
		break;
	case EvFocusOut:
		gkeyevent('r', 0, 0);
		break;
	}
}

static void
webinput(void *arg)
{
	int tail, head, e[EventWords], *slot;

	USED(arg);
	for(;;){
		tail = __atomic_load_n(&shared.tail, __ATOMIC_ACQUIRE);
		head = __atomic_load_n(&shared.head, __ATOMIC_ACQUIRE);
		if(head == tail){
			emscripten_futex_wait(&shared.head, head, 1000);
			continue;
		}
		slot = &shared.ring[(tail & (Ring-1))*EventWords];
		memmove(e, slot, sizeof e);
		__atomic_store_n(&shared.tail, tail+1, __ATOMIC_RELEASE);
		webevent(e);
	}
}

uchar*
attachscreen(Rectangle *r, ulong *chan, int *d, int *width, int *softscreen)
{
	Xsize &= ~0x3;
	r->min.x = 0;
	r->min.y = 0;
	r->max.x = Xsize;
	r->max.y = Ysize;
	*chan = XRGB32;
	*d = 32;
	*width = Xsize;
	*softscreen = 1;

	if(!triedscreen){
		screendata = mallocz(Xsize*Ysize*4, 1);
		if(screendata == nil){
			fprint(2, "emu: cannot allocate the %dx%d screen\n", Xsize, Ysize);
			return nil;
		}
		shared.width = Xsize;
		shared.height = Ysize;
		shared.pixels = (int)screendata;
		shared.dirty[0] = 0;
		shared.dirty[1] = 0;
		shared.dirty[2] = Xsize;
		shared.dirty[3] = Ysize;
		shared.cursorpixels = (int)cursorrgba;
		triedscreen = 1;
		gkeyinit();
		kproc("webinput", webinput, nil, 0);
		MAIN_THREAD_ASYNC_EM_ASM({ if(Module.taijiScreen) Module.taijiScreen($0); }, &shared);
	}
	return screendata;
}

void
flushmemscreen(Rectangle r)
{
	if(r.min.x < 0)
		r.min.x = 0;
	if(r.min.y < 0)
		r.min.y = 0;
	if(r.max.x > Xsize)
		r.max.x = Xsize;
	if(r.max.y > Ysize)
		r.max.y = Ysize;
	if(r.max.x <= r.min.x || r.max.y <= r.min.y)
		return;

	spinlock(&shared.dirtylock);
	if(shared.dirty[0] >= shared.dirty[2]){
		shared.dirty[0] = r.min.x;
		shared.dirty[1] = r.min.y;
		shared.dirty[2] = r.max.x;
		shared.dirty[3] = r.max.y;
	}else{
		if(r.min.x < shared.dirty[0])
			shared.dirty[0] = r.min.x;
		if(r.min.y < shared.dirty[1])
			shared.dirty[1] = r.min.y;
		if(r.max.x > shared.dirty[2])
			shared.dirty[2] = r.max.x;
		if(r.max.y > shared.dirty[3])
			shared.dirty[3] = r.max.y;
	}
	__atomic_add_fetch(&shared.frame, 1, __ATOMIC_RELEASE);
	spinunlock(&shared.dirtylock);
}

/* The browser cannot move the pointer. */
void
setpointer(int x, int y)
{
	USED(x);
	USED(y);
}

/*
 * Cursor data holds h rows of clear bits, then h rows of set bits.
 * Set pixels are black, clear-only pixels white, the rest transparent.
 */
void
drawcursor(Drawcursor *c)
{
	int h, w, bpl, x, y, set, clr;
	uchar *bc, *bs, *p;

	if(c->data == nil){
		shared.cursorw = 0;
		shared.cursorh = 0;
		__atomic_add_fetch(&shared.cursor, 1, __ATOMIC_RELEASE);
		return;
	}
	h = (c->maxy-c->miny)/2;
	if(h > CursorSide)
		h = CursorSide;
	bpl = bytesperline(Rect(c->minx, c->miny, c->maxx, c->maxy), 1);
	w = bpl*8;
	if(w > CursorSide)
		w = CursorSide;
	memset(cursorrgba, 0, sizeof cursorrgba);
	bc = c->data;
	bs = c->data + h*bpl;
	for(y = 0; y < h; y++){
		for(x = 0; x < w; x++){
			set = bs[x/8] & (0x80>>(x%8));
			clr = bc[x/8] & (0x80>>(x%8));
			p = &cursorrgba[(y*CursorSide + x)*4];
			if(set){
				p[0] = p[1] = p[2] = 0;
				p[3] = 255;
			}else if(clr){
				p[0] = p[1] = p[2] = 255;
				p[3] = 255;
			}
		}
		bs += bpl;
		bc += bpl;
	}
	shared.cursorw = w;
	shared.cursorh = h;
	shared.hotx = c->hotx;
	shared.hoty = c->hoty;
	__atomic_add_fetch(&shared.cursor, 1, __ATOMIC_RELEASE);
}

char*
clipread(void)
{
	char *p;

	spinlock(&shared.snarflock);
	p = snarf != nil ? strdup(snarf) : nil;
	spinunlock(&shared.snarflock);
	return p;
}

int
clipwrite(char *buf)
{
	char *p;

	p = strdup(buf);
	if(p == nil)
		return 0;
	spinlock(&shared.snarflock);
	free(snarf);
	snarf = p;
	shared.snarf = (int)snarf;
	shared.snarflen = strlen(snarf);
	spinunlock(&shared.snarflock);
	MAIN_THREAD_ASYNC_EM_ASM({ if(Module.taijiSnarf) Module.taijiSnarf(); });
	return 0;
}
