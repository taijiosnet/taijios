#include "dat.h"
#include "fns.h"

#ifdef TAIJI_ZX
#include "interp.h"
#include "isa.h"
#include "kernel.h"
#include "ziran_host.h"
#include "ziran_zx_module.h"
#include <time.h>
#if defined(__linux__) && defined(__i386__)
#include <fenv.h>
#endif
#include "draw.h"
#include "tk.h"
#include "zxrunt.h"
#include "drawif.h"
#include "zxmod.h"
#ifdef __linux__
#include <pthread.h>
#include "zxwindow.h"
#endif

enum {
	ZxMaxImage = 32 * 1024 * 1024,
	ZxStreamMinImage = 256 * 1024,
	ZxSteps = 16000000,
	ZxTitleBytes = 512,
	ZxGuestPathBytes = 1024,
	ZxLaunchArgBytes = 4096,
	ZxCursorSide = 32,
	ZxIoBytes = 8192,
	ZxInitialFiles = 32,
	ZxProcessDepth = 32,
	ZxProcessLimit = 32,
	ZxTaskLimit = 1024,
	ZxTaskNameBytes = 64,
	ZxPanelLabelBytes = 160,
	ZxImageBytes = 8 * 1024 * 1024,
	ZxImagePixels = 2 * 1024 * 1024,
	ZxImageWorkChunk = 262144,
	ZxImageMillis = 60000,
};

static int
zxwrite(void *context, int fd, const void *data, size_t size)
{
	const uchar *bytes = data;
	long count;

	USED(context);
	while(size != 0){
		count = kwrite(fd, (void *)bytes, size > ZxIoBytes ? ZxIoBytes : size);
		if(count <= 0)
			return 0;
		bytes += count;
		size -= count;
	}
	return 1;
}

static void
zxfree(void *context, const uchar *data, size_t size)
{
	USED(context);
	USED(size);
	free((void *)data);
}

static vlong
zximagesize(int fd)
{
	Dir *dir;
	vlong length = 0;

	dir = kdirfstat(fd);
	if(dir != nil){
		if((dir->mode & DMDIR) == 0)
			length = dir->length;
		free(dir);
	}
	return length;
}

static ZxModuleResolveResult
zxreadfd(int fd, vlong advertised, char *err, ZxModuleImage *image)
{
	uchar *bytes, *grown, extra;
	int length, capacity, initial;
	long count;

	initial = ZxIoBytes;
	/* Leave room to read EOF without growing the buffer for a regular image. */
	if(advertised > 0 && advertised < ZxMaxImage)
		initial = advertised + 1;
	bytes = nil;
	length = capacity = 0;
	for(;;){
		if(length == capacity){
			if(capacity == ZxMaxImage){
				count = kread(fd, &extra, 1);
				if(count > 0)
					strecpy(err, err+ERRMAX, "ZX image exceeds 32 MiB");
				break;
			}
			if(capacity == 0)
				capacity = initial;
			else if(capacity < ZxMaxImage/2)
				capacity *= 2;
			else
				capacity = ZxMaxImage;
			grown = realloc(bytes, capacity);
			if(grown == nil){
				strecpy(err, err+ERRMAX, "out of memory reading ZX");
				count = -1;
				break;
			}
			bytes = grown;
		}
		count = kread(fd, bytes+length, capacity-length);
		if(count <= 0)
			break;
		length += count;
	}
	if(count < 0 && err[0] == '\0')
		kgerrstr(err, ERRMAX);
	if(count == 0){
		*image = (ZxModuleImage){bytes, length, zxfree};
		return ZX_MODULE_IMAGE_FOUND;
	}
	free(bytes);
	return ZX_MODULE_IMAGE_ERROR;
}

static ZxModuleResolveResult
zxread(void *context, const char *path, ZxModuleImage *image)
{
	char *err = context;
	int fd;
	ZxModuleResolveResult result;

	err[0] = '\0';
	fd = kopen((char *)path, OREAD);
	if(fd < 0){
		kgerrstr(err, ERRMAX);
		if(strstr(err, "does not exist") != nil || strstr(err, "No such file") != nil)
			return ZX_MODULE_IMAGE_MISSING;
		return ZX_MODULE_IMAGE_ERROR;
	}
	result = zxreadfd(fd, zximagesize(fd), err, image);
	kclose(fd);
	return result;
}

#ifdef ZIRAN_HOST_HAS_BUNDLE_READ_AT
typedef struct ZxImageReader ZxImageReader;
struct ZxImageReader {
	int fd;
	char *error;
};

static size_t
zximageat(void *context, uint64_t offset, void *output, size_t size)
{
	ZxImageReader *reader = context;
	uchar *bytes = output;
	size_t read = 0;
	long count;

	while(read < size){
		count = kpread(reader->fd, bytes+read, size-read, offset+read);
		if(count < 0){
			kgerrstr(reader->error, ERRMAX);
			return 0;
		}
		if(count == 0){
			strecpy(reader->error, reader->error+ERRMAX, "short read loading ZX image");
			return 0;
		}
		read += count;
	}
	return read;
}
#endif

static Bundle*
zxopen(const char *path, char *err)
{
	Bundle *bundle;
	ZxModuleImage image;
	ZxModuleResolveResult result;
	int fd;
	vlong length;

	err[0] = '\0';
	fd = kopen((char *)path, OREAD);
	if(fd < 0){
		kgerrstr(err, ERRMAX);
		return nil;
	}
	length = zximagesize(fd);
#ifdef ZIRAN_HOST_HAS_BUNDLE_READ_AT
	if(length >= ZxStreamMinImage && length <= ZxMaxImage && kseek(fd, 0, 0) == 0){
		ZxImageReader reader = {fd, err};
		int unsupported;
		uchar extra;
		long count;

#ifdef ZIRAN_HOST_HAS_BUNDLE_ENGINE_READ_AT
		bundle = BundleOpenEngineReadAt(length, zximageat, &reader, &unsupported, mallocshrink);
#else
		bundle = BundleOpenReadAt(length, zximageat, &reader, &unsupported);
#endif
		if(bundle != nil){
			/* An appended tail would otherwise be outside the verified image. */
			count = kpread(fd, &extra, 1, length);
			if(count < 0)
				kgerrstr(err, ERRMAX);
			else if(count > 0)
				strecpy(err, err+ERRMAX, "ZX image grew while loading");
			kclose(fd);
			if(count == 0)
				return bundle;
			BundleClose(bundle);
			return nil;
		}
		if(!unsupported || err[0] != '\0' || kseek(fd, 0, 0) != 0){
			if(err[0] == '\0'){
				if(unsupported)
					kgerrstr(err, ERRMAX);
				else
					strecpy(err, err+ERRMAX, "invalid ZX image");
			}
			kclose(fd);
			return nil;
		}
	}
#endif
	result = zxreadfd(fd, length, err, &image);
	kclose(fd);
	if(result != ZX_MODULE_IMAGE_FOUND)
		return nil;
	bundle = BundleOpenOwnedBytes(image.data, image.size, image.release, err);
	if(bundle == nil)
		strecpy(err, err+ERRMAX, "invalid ZX image");
	return bundle;
}

typedef struct ZxSurface ZxSurface;
typedef struct ZxResult ZxResult;
struct ZxSurface {
	ZX_Window *win;
	HostField event[9];
	uchar text[UTFmax];
	int nextrow, framewidth, frameheight;
	vlong pointermillis, pointerepoch;
	uint pointertick;
	int opened, imageactive, imagecancelled, imagepermit, pendingresize, resizewidth, resizeheight;
	vlong imagework, imagelimit, imagestart, imagepoll;
};

/* Requests use scalar channels. Keep Limbo references on the managed Window. */
static int
zxrequest(ZX_Window *win, int operation)
{
	win->message = operation;
	csend(win->request, &win->message);
	crecv(win->reply, &win->message);
	return win->message;
}

static void
zxinteger(HostField *field, const char *name, int value)
{
	field->name = name;
	field->value.kind = HOST_INTEGER;
	field->value.type = "s32";
	field->value.integer = value;
}

static int
zxevent(ZxSurface *surface, const HostValue *args, int n, HostValue *result)
{
	ZX_Window *win = surface->win;
	ZX_Input *input;
	HostField *event = surface->event;
	String *s;
	Rune rune;
	uint tick;
	int pointer;

	if(n != 1 || args[0].kind != HOST_INTEGER || args[0].integer > INT32_MAX)
		return 0;
	win->wait = args[0].integer < 0 ? 0 : args[0].integer;
	if(surface->pendingresize){
		surface->pendingresize = 0;
		destroy(win->input.text);
		win->input = (ZX_Input){.kind = ZX_Resize, .width = surface->resizewidth,
			.height = surface->resizeheight, .text = H};
	}else if(!zxrequest(win, ZX_Event))
		return 0;
	input = &win->input;
	if(input->kind != ZX_Closed && (win->wait > 0 || input->kind != ZX_Idle))
		BundleHostRenewSteps();
	pointer = input->kind == ZX_Move || input->kind == ZX_Down || input->kind == ZX_Up;
	surface->pointermillis = -1;
	if(pointer && input->key != 0){
		tick = (uint)input->key;
		if(tick < surface->pointertick && surface->pointertick - tick > 0x80000000U)
			surface->pointerepoch += (vlong)1 << 32;
		surface->pointertick = tick;
		surface->pointermillis = surface->pointerepoch + tick;
	}
	zxinteger(&event[0], "kind", input->kind);
	zxinteger(&event[1], "x", input->x);
	zxinteger(&event[2], "y", input->y);
	zxinteger(&event[3], "button", input->button);
	zxinteger(&event[4], "key", pointer ? 0 : input->key);
	zxinteger(&event[5], "modifiers", input->modifiers);
	zxinteger(&event[6], "width", input->width);
	zxinteger(&event[7], "height", input->height);
	event[8].name = "text";
	event[8].value.kind = HOST_STRING;
	event[8].value.type = "string";
	event[8].value.data = surface->text;
	event[8].value.length = 0;
	s = input->text;
	if(s != H && s->len != 0){
		rune = s->len < 0 ? s->Srune[0] : (uchar)s->Sascii[0];
		event[8].value.length = runetochar((char *)surface->text, &rune);
	}
	result->kind = HOST_RECORD;
	result->fields = event;
	result->field_count = nelem(surface->event);
	return 1;
}

static int
zxsize(const HostValue *args)
{
	return args[0].kind == HOST_INTEGER && args[1].kind == HOST_INTEGER &&
		args[0].integer > 0 && args[0].integer <= ZX_Maxside &&
		args[1].integer > 0 && args[1].integer <= ZX_Maxside &&
		args[0].integer * args[1].integer <= ZX_Maxpixels;
}

static void
zxbool(HostValue *result, int value)
{
	result->kind = HOST_INTEGER;
	result->type = "bool";
	result->integer = value != 0;
}

static int
zxtitle(ZX_Window *win, const HostValue *title)
{
	String *s;

	if(title->kind != HOST_STRING ||
	   title->length > ZxTitleBytes || (title->length != 0 &&
	   (title->data == nil || memchr(title->data, 0, title->length) != nil)))
		return 0;
	s = title->length == 0 ? H : c2string((char *)title->data, title->length);
	destroy(win->title);
	win->title = s;
	if(s != H)
		Setmark(D2H(s));
	return 1;
}

static int
zxopenwindow(ZX_Window *win, const HostValue *args, int n, HostValue *result)
{
	if(n != 3 || !zxsize(args + 1) || !zxtitle(win, args)){
		zxbool(result, 0);
		return 1;
	}
	win->width = args[1].integer;
	win->height = args[2].integer;
	/* The launcher reuses the pointer event's internal key slot for the timestamp. */
	win->input.key = 1;
	zxbool(result, zxrequest(win, ZX_Open));
	return 1;
}

static int
zxupload(Image *image, const uchar *data, int width, int height)
{
	int maxwidth, x, y, count;

	/* Draw channels are stored least significant byte first. ABGR32 is RGBA8 in memory. */
	maxwidth = (image->display->bufsize - 64) / 4;
	if(maxwidth <= 0 || image->chan != ABGR32 || Dx(image->r) != width || Dy(image->r) != height)
		return 0;
	if(width <= maxwidth)
		return loadimage(image, image->r, (uchar *)data, width*height*4) == width*height*4;
	for(y = 0; y < height; y++)
		for(x = 0; x < width; x += count){
			count = width-x < maxwidth ? width-x : maxwidth;
			if(loadimage(image, Rect(x, y, x+count, y+1),
			   (uchar *)data + (y*width + x)*4, count*4) != count*4)
				return 0;
		}
	return 1;
}

static int
zxopaque(const uchar *data, size_t size)
{
	size_t i;

	for(i = 3; i < size; i += 4)
		if(data[i] != 255)
			return 0;
	return 1;
}

static int
zxuploadopaque(Image *image, const uchar *data, int width, int first, int height, const HostValue *words, const uchar *borrowed)
{
	enum { Chunk = 8192 / 3 };
	uchar packed[Chunk*3];
	const uchar *source;
	int maxpixels, x, y, i, columns, rows, count, offset;

	/* BGR24's bytes are ordered R, G, B in Draw. */
	maxpixels = (image->display->bufsize - 64) / 3;
	if(maxpixels <= 0 || image->chan != BGR24 || Dx(image->r) != width || first+height > Dy(image->r))
		return 0;
	if(maxpixels > Chunk)
		maxpixels = Chunk;
	for(y = 0; y < height; y += rows){
		/* Pack full rows when possible, or split a wide row horizontally. */
		rows = width <= maxpixels ? maxpixels / width : 1;
		if(rows > height-y)
			rows = height-y;
		for(x = 0; x < width; x += columns){
			columns = width-x < maxpixels ? width-x : maxpixels;
			count = columns * rows;
			offset = y*width + x;
			if(words != nil){
				for(i = 0; i < count; i++){
					packed[3*i] = words[offset+i].bits >> 16;
					packed[3*i+1] = words[offset+i].bits >> 8;
					packed[3*i+2] = words[offset+i].bits;
				}
			}else if(borrowed != nil){
				source = borrowed + offset*4;
				for(i = 0; i < count; i++){
					packed[3*i] = source[4*i+2];
					packed[3*i+1] = source[4*i+1];
					packed[3*i+2] = source[4*i];
				}
			}else{
				source = data + offset*4;
				for(i = 0; i < count; i++){
					packed[3*i] = source[4*i];
					packed[3*i+1] = source[4*i+1];
					packed[3*i+2] = source[4*i+2];
				}
			}
			if(loadimage(image, Rect(x, first+y, x+columns, first+y+rows), packed, count*3) != count*3)
				return 0;
		}
	}
	return 1;
}

static int
zxpresent(ZX_Window *win, const HostValue *args, int n, HostValue *result)
{
	const HostValue *pixels;
	Image *image;
	int ok = 0, prepared, locked, opaque;

	if(n != 3 || !zxsize(args)){
		zxbool(result, 0);
		return 1;
	}
	pixels = args + 2;
	if(pixels->kind == HOST_STRING && pixels->data != nil &&
	   pixels->length == (size_t)args[0].integer * args[1].integer * 4){
		win->width = args[0].integer;
		win->height = args[1].integer;
		opaque = zxopaque(pixels->data, pixels->length);
		prepared = zxrequest(win, opaque ? ZX_OpaqueBuffer : ZX_Buffer);
		if(opaque && prepared != 2 && (prepared != 1 ||
		   (image = lookupimage(win->image)) == nil || image->chan != BGR24)){
			/* A guest can still be running an older zxrun.dis. */
			opaque = 0;
			prepared = zxrequest(win, ZX_Buffer);
		}
		if(prepared == 2)
			ok = 1; /* Close is queued. */
		else if(prepared == 1 && (image = lookupimage(win->image)) != nil){
			locked = lockdisplay(image->display);
			if(opaque)
				ok = zxuploadopaque(image, pixels->data, win->width, 0, win->height, nil, nil);
			else
				ok = zxupload(image, pixels->data, win->width, win->height);
			if(locked)
				unlockdisplay(image->display);
			if(ok)
				ok = zxrequest(win, ZX_Present);
		}
	}
	zxbool(result, ok);
	return 1;
}

static int
zxpresentrows(ZxSurface *surface, const HostValue *args, int n, int strip, int packed)
{
	ZX_Window *win = surface->win;
	const HostValue *pixels;
	Image *image;
	int first, width, height, rows, stride, prepared, locked, ok;
	size_t i;
	int next = surface->nextrow;

	if(!strip)
		surface->nextrow = 0;
	if(n != 4 || !zxsize(args) || args[2].kind != HOST_INTEGER ||
	   args[2].integer < 0 || args[2].integer >= args[1].integer)
		return 0;
	width = args[0].integer;
	height = args[1].integer;
	first = args[2].integer;
	if(!strip && first != 0 && (first != next || width != surface->framewidth || height != surface->frameheight))
		return 0;
	pixels = args + 3;
	stride = width;
	if(packed){
		if((pixels->kind != HOST_SLICE && pixels->kind != HOST_BORROWED_SLICE) ||
		   pixels->type == nil || strcmp(pixels->type, "[]u32") != 0 ||
		   (pixels->kind == HOST_SLICE ? pixels->elements == nil : pixels->data == nil))
			return 0;
	}else{
		stride *= 4;
		if(pixels->kind != HOST_STRING || pixels->data == nil)
			return 0;
	}
	if(pixels->length == 0 || pixels->length > (size_t)(height-first)*stride || pixels->length % stride != 0)
		return 0;
	if(!packed && !zxopaque(pixels->data, pixels->length))
		return 0;
	if(packed && pixels->kind == HOST_SLICE)
		for(i = 0; i < pixels->length; i++)
			if(pixels->elements[i].kind != HOST_UNSIGNED || pixels->elements[i].bits > UINT32_MAX)
				return 0;
	rows = pixels->length / stride;
	win->width = width;
	win->height = height;
	if(strip){
		win->input.y = first;
		win->input.height = rows;
	}
	prepared = zxrequest(win, strip ? ZX_StripBuffer : ZX_OpaqueBuffer);
	if(prepared == 2)
		ok = 1; /* Close is queued. */
	else if(prepared != 1 || (image = lookupimage(win->image)) == nil)
		return 0;
	else{
		locked = lockdisplay(image->display);
		ok = zxuploadopaque(image, pixels->data, width, first, rows,
			packed && pixels->kind == HOST_SLICE ? pixels->elements : nil,
			packed && pixels->kind == HOST_BORROWED_SLICE ? pixels->data : nil);
		if(locked)
			unlockdisplay(image->display);
		if(ok && (strip || first+rows == height))
			ok = zxrequest(win, strip ? ZX_PresentStrip : ZX_Present);
	}
	if(ok && !strip && first+rows < height){
		surface->nextrow = first + rows;
		surface->framewidth = width;
		surface->frameheight = height;
	}
	return ok;
}

static int
zxsurface(void *context, const char *module, const char *function,
	const HostValue *args, int n, HostValue *result)
{
	ZxSurface *surface = context;
	int ok;

	USED(module);
	acquire();
	if(waserror()){
		release();
		return 0;
	}
	if(strcmp(function, "Open") == 0){
		ok = zxopenwindow(surface->win, args, n, result);
		surface->opened = ok && result->integer != 0;
	}else if(strcmp(function, "Event") == 0)
		ok = zxevent(surface, args, n, result);
	else if(strcmp(function, "PointerMillis") == 0){
		ok = n == 0;
		result->kind = HOST_INTEGER;
		result->type = "s64";
		result->integer = surface->pointermillis;
	}else if(strcmp(function, "Present") == 0){
		surface->nextrow = 0;
		ok = zxpresent(surface->win, args, n, result);
	}else if(strcmp(function, "PresentOpaqueRows") == 0){
		zxbool(result, zxpresentrows(surface, args, n, 0, 0));
		ok = 1;
	}else if(strcmp(function, "PresentOpaqueStrip") == 0){
		zxbool(result, zxpresentrows(surface, args, n, 1, 0));
		ok = 1;
	}else if(strcmp(function, "PresentRGBStrip") == 0){
		zxbool(result, zxpresentrows(surface, args, n, 1, 1));
		ok = 1;
	}else if(strcmp(function, "SetTitle") == 0){
		zxbool(result, n == 1 && zxtitle(surface->win, args) && zxrequest(surface->win, ZX_SetTitle));
		ok = 1;
	}else if(strcmp(function, "SetTasked") == 0){
		ok = n == 1 && args[0].kind == HOST_INTEGER && args[0].type != nil &&
			strcmp(args[0].type, "bool") == 0;
		if(ok){
			surface->win->tasked = args[0].integer != 0;
			zxbool(result, zxrequest(surface->win, ZX_SetTasked));
		}
	}else{
		surface->nextrow = 0;
		ok = n == 0 && zxrequest(surface->win, ZX_Close);
		result->kind = HOST_VOID;
	}
	poperror();
	release();
	return ok;
}

/* Call with the interpreter acquired. Older launchers leave the payload intact. */
static int
zxtextrequest(ZX_Window *win, int operation, const char *text, int length)
{
	String *payload;
	int ok;

	payload = c2string((char *)text, length);
	destroy(win->input.text);
	win->input.text = payload;
	Setmark(D2H(payload));
	ok = zxrequest(win, operation) && win->input.text == H;
	destroy(win->input.text);
	win->input.text = H;
	return ok;
}

static int
zxwmlaunch(void *context, const char *module, const char *function,
	const HostValue *args, int n, HostValue *result)
{
	ZxSurface *surface = context;
	ZX_Window *win = surface->win;
	const HostValue *program, *argv;
	char request[ZxGuestPathBytes + 1 + ZxLaunchArgBytes];

	USED(module);
	USED(function);
	result->kind = HOST_INTEGER;
	result->type = "s32";
	result->integer = -1;
	if(n != 2)
		return 0;
	program = args;
	argv = args + 1;
	if(program->kind != HOST_STRING || program->length == 0 ||
	   program->length > ZxGuestPathBytes || program->data == nil ||
	   memchr(program->data, 0, program->length) != nil ||
	   argv->kind != HOST_STRING || argv->length == 0 || argv->length > ZxLaunchArgBytes ||
	   argv->data == nil || argv->data[argv->length-1] != 0)
		return 1;
	memmove(request, program->data, program->length);
	request[program->length] = '\0';
	memmove(request+program->length+1, argv->data, argv->length);
	acquire();
	if(waserror()){
		release();
		return 0;
	}
	if(zxtextrequest(win, ZX_Launch, request, program->length+1+argv->length))
		result->integer = 0;
	poperror();
	release();
	return 1;
}

static int
zxresize(ZX_Window *win, const HostValue *args, int n)
{
	if(n != 2 || !zxsize(args))
		return 0;
	win->width = args[0].integer;
	win->height = args[1].integer;
	/* The launcher clears this on receipt, including if the window is closed. */
	win->input.kind = 1;
	return zxrequest(win, ZX_ResizeWindow) && win->input.kind == 0;
}

static int
zxcursorvalid(vlong x, vlong y, vlong width, vlong height, size_t length)
{
	return width > 0 && width <= ZxCursorSide && width % 8 == 0 &&
		height > 0 && height <= 2 * ZxCursorSide && height % 2 == 0 &&
		x <= 0 && x > -width && y <= 0 && y > -(height/2) && length == (size_t)(width/8*height);
}

static int
zxcursor(ZX_Window *win, const HostValue *args, int n)
{
	static const char hex[] = "0123456789abcdef";
	const uchar *bytes;
	vlong x, y, width, height;
	char request[64 + 4 * ZxCursorSide * ZxCursorSide / 8];
	int i, length;

	if(n != 5 || args[0].kind != HOST_INTEGER || args[1].kind != HOST_INTEGER ||
	   args[2].kind != HOST_INTEGER || args[3].kind != HOST_INTEGER || args[4].kind != HOST_STRING)
		return 0;
	x = args[0].integer;
	y = args[1].integer;
	width = args[2].integer;
	height = args[3].integer;
	if(width == 0 && height == 0 && args[4].length == 0)
		return zxtextrequest(win, ZX_SetCursor, "cursor", sizeof("cursor")-1);
	if(args[4].data == nil || !zxcursorvalid(x, y, width, height, args[4].length))
		return 0;
	length = snprint(request, sizeof request, "cursor %d %d %d %d ", (int)x, (int)y, (int)width, (int)height);
	bytes = args[4].data;
	for(i = 0; i < (int)args[4].length; i++){
		request[length++] = hex[bytes[i] >> 4];
		request[length++] = hex[bytes[i] & 15];
	}
	return zxtextrequest(win, ZX_SetCursor, request, length);
}

static int
zxwmwindow(void *context, const char *module, const char *function,
	const HostValue *args, int n, HostValue *result)
{
	ZxSurface *surface = context;
	int ok;

	USED(module);
	acquire();
	if(waserror()){
		release();
		return 0;
	}
	if(strcmp(function, "Resize") == 0)
		ok = zxresize(surface->win, args, n);
	else
		ok = zxcursor(surface->win, args, n);
	zxbool(result, ok);
	poperror();
	release();
	return 1;
}

static int
zxstdin(void *context, const char *module, const char *function,
	const HostValue *args, int n, HostValue *result)
{
	ZxSurface *surface = context;
	ZX_Window *win;
	uchar bytes[ZX_StdinChunk];
	size_t length;
	long count, i;

	USED(module);
	if(n != 1 || args[0].kind != HOST_SLICE || args[0].type == nil ||
	   strcmp(args[0].type, "[]u8") != 0 || (args[0].length != 0 && args[0].elements == nil))
		return 0;
	length = args[0].length;
	if(length > sizeof(bytes))
		length = sizeof(bytes);
	count = 0;
	if(length != 0 && strcmp(function, "Poll") == 0){
		win = surface->win;
		acquire();
		if(waserror()){
			release();
			return 0;
		}
		win->stdinlen = length;
		count = zxrequest(win, ZX_Poll) ? win->stdinlen : -1;
		if(count > 0){
			if(count > (long)length || win->stdin == H || count > win->stdin->len)
				count = -1;
			else
				memmove(bytes, win->stdin->data, count);
		}
		poperror();
		release();
	}else if(length != 0)
		count = kread(0, bytes, length);
	for(i = 0; i < count; i++)
		args[0].elements[i].bits = bytes[i];
	result->kind = HOST_INTEGER;
	result->type = "s32";
	result->integer = count;
	return 1;
}

static int
zxclock(void *context, const char *module, const char *function,
	const HostValue *args, int n, HostValue *result)
{
	struct timespec now;

	USED(context);
	USED(module);
	USED(args);
	if(n != 0)
		return 0;
	result->kind = HOST_INTEGER;
	result->type = "s64";
	if(strcmp(function, "UnixMillis") == 0){
		extern vlong timeoffset;
		result->integer = (timeoffset + osusectime()) / 1000;
	}else{
		if(clock_gettime(CLOCK_MONOTONIC, &now) < 0)
			return 0;
		result->integer = (int64_t)now.tv_sec * 1000 + now.tv_nsec / 1000000;
	}
	return 1;
}

/* Read from the caller's Inferno namespace, including its mounts. */
static int
zxfilereadat(void *context, const char *module, const char *function,
	const HostValue *args, int n, HostValue *result)
{
	char path[ZxGuestPathBytes + 1], err[ERRMAX];
	uchar bytes[4096];
	const HostValue *name, *offset, *buffer;
	size_t length;
	long count, i;
	int fd;

	USED(context);
	USED(module);
	USED(function);
	if(n != 3)
		return 0;
	name = args;
	offset = args + 1;
	buffer = args + 2;
	if(name->kind != HOST_STRING || offset->kind != HOST_INTEGER ||
	   offset->type == nil || strcmp(offset->type, "s64") != 0 ||
	   buffer->kind != HOST_SLICE || buffer->type == nil ||
	   strcmp(buffer->type, "[]u8") != 0 || (buffer->length != 0 && buffer->elements == nil))
		return 0;

	count = -1;
	if(name->length != 0 && name->length <= ZxGuestPathBytes && name->data != nil &&
	   memchr(name->data, 0, name->length) == nil && offset->integer >= 0 &&
	   offset->integer <= INT64_MAX - sizeof(bytes)){
		memmove(path, name->data, name->length);
		path[name->length] = 0;
		fd = kopen(path, OREAD);
		if(fd < 0){
			kgerrstr(err, sizeof(err));
			if(strstr(err, "does not exist") != nil || strstr(err, "No such file") != nil)
				count = -2;
		}else{
			length = buffer->length > sizeof(bytes) ? sizeof(bytes) : buffer->length;
			count = length == 0 ? 0 : kpread(fd, bytes, length, offset->integer);
			kclose(fd);
			for(i = 0; i < count; i++)
				buffer->elements[i].bits = bytes[i];
		}
	}
	result->kind = HOST_INTEGER;
	result->type = "s32";
	result->integer = count;
	return 1;
}

typedef struct ZxTask ZxTask;
struct ZxTask {
	int pid;
	int group;
	int state;
	int kib;
	vlong cpunanos;
	char module[ZxTaskNameBytes];
	char user[ZxTaskNameBytes];
};

typedef struct ZxCommand ZxCommand;
typedef struct ZxProcess ZxProcess;
typedef struct ZxStdinPump ZxStdinPump;
struct ZxResult {
	long long value;
	int status;
	char problem[ERRMAX];
};

struct ZxCommand {
	ZxSurface *surface;
	int hosted;
	int depth;
	HostValue *args;
	int argc;
	int *fd;
	int nfd;
	char *fdpath;
	char err[ERRMAX];
	char failure[ERRMAX];
	ZxTask *tasks;
	int ntask;
	int taskcap;
	int tasksvalid;
	vlong tasksample;
	vlong taskskew;
	uvlong pools[3][3];
	ZxResult outcome;
	HostField outfields[3];
	/* A child's stop request and the kproc running its guest code. The runner
	 * is set only while zxexecute owns the program, under runlock. */
	ZxRunControl *control;
	Lock runlock;
	Proc *runner;
#ifdef __linux__
	ZxProcess *children;
	ZxNativeWindow *window;
	ZxStdinPump *stdinpump;
	int childid, nchild;
#endif
};

static ZxResult zxexecute(const char *, ZxSurface *, ZxCommand *);

static int zxs32(HostValue *, int);

#ifdef __linux__
/* A windowed ZX process without Dis polls fd 0 through a reader kproc that
 * holds one chunk at a time. count is the bytes held, -2 while a read is
 * pending, 0 at end of input, and -1 after an error. */
struct ZxStdinPump {
	Ref ref;
	Lock l;
	Rendez taken;
	Proc *reader;
	int closed, offset;
	long count;
	uchar data[ZX_StdinChunk];
};

static void
zxstdinrelease(ZxStdinPump *pump)
{
	if(decref(&pump->ref) == 0)
		free(pump);
}

static int
zxstdintaken(void *arg)
{
	ZxStdinPump *pump = arg;

	return pump->count == -2 || pump->closed;
}

static void
zxstdinreader(void *arg)
{
	ZxStdinPump *pump = arg;
	uchar bytes[ZX_StdinChunk];
	long n;
	int closed;

	lock(&pump->l);
	pump->reader = up;
	closed = pump->closed;
	unlock(&pump->l);
	while(!closed){
		n = kread(0, bytes, sizeof(bytes));
		lock(&pump->l);
		closed = pump->closed;
		if(!closed){
			if(n > 0)
				memmove(pump->data, bytes, n);
			pump->offset = 0;
			pump->count = n < 0 ? -1 : n;
		}
		unlock(&pump->l);
		if(closed || n <= 0)
			break;
		if(waserror())
			break;
		Sleep(&pump->taken, zxstdintaken, pump);
		poperror();
		lock(&pump->l);
		closed = pump->closed;
		unlock(&pump->l);
	}
	lock(&pump->l);
	pump->reader = nil;
	unlock(&pump->l);
	zxstdinrelease(pump);
}

static int
zxnativestdin(void *context, const char *module, const char *function,
	const HostValue *args, int n, HostValue *result)
{
	ZxCommand *command = context;
	ZxStdinPump *pump;
	size_t length;
	long count, i;
	int taken;

	USED(module);
	USED(function);
	if(n != 1 || args[0].kind != HOST_SLICE || args[0].type == nil ||
	   strcmp(args[0].type, "[]u8") != 0 || (args[0].length != 0 && args[0].elements == nil))
		return 0;
	length = args[0].length;
	if(length > ZX_StdinChunk)
		length = ZX_StdinChunk;
	if(length == 0)
		return zxs32(result, 0);
	pump = command->stdinpump;
	if(pump == nil){
		pump = calloc(1, sizeof(*pump));
		if(pump == nil)
			return zxs32(result, -1);
		pump->ref.ref = 2;
		pump->count = -2;
		if(waserror()){
			free(pump);
			return zxs32(result, -1);
		}
		kproc("ZX stdin", zxstdinreader, pump, KPDUPPG|KPDUPFDG|KPDUPENVG);
		poperror();
		command->stdinpump = pump;
	}
	taken = 0;
	lock(&pump->l);
	count = pump->count;
	if(count > 0){
		if(count - pump->offset < (long)length)
			length = count - pump->offset;
		for(i = 0; i < (long)length; i++)
			args[0].elements[i].bits = pump->data[pump->offset+i];
		pump->offset += length;
		if(pump->offset == count){
			pump->count = -2;
			taken = 1;
		}
		count = length;
	}
	unlock(&pump->l);
	if(taken)
		Wakeup(&pump->taken);
	return zxs32(result, count);
}

/* Interrupt a pending read and drop the command's reference. */
static void
zxstdinclose(ZxCommand *command)
{
	ZxStdinPump *pump = command->stdinpump;

	if(pump == nil)
		return;
	command->stdinpump = nil;
	lock(&pump->l);
	pump->closed = 1;
	if(pump->reader != nil)
		swiproc(pump->reader, 0);
	unlock(&pump->l);
	Wakeup(&pump->taken);
	zxstdinrelease(pump);
}
#endif

static int
zxcopyargs(ZxCommand *command, List *args)
{
	List *arg;
	String *s;
	HostValue *value;
	char *bytes, *end;
	size_t length;
	int count, i;

	for(arg = args, count = 0; arg != H; arg = arg->tail)
		count++;
	if(count == 0)
		return 1;
	command->args = calloc(count, sizeof(*command->args));
	if(command->args == nil)
		return 0;
	command->argc = count;
	for(arg = args, value = command->args; arg != H; arg = arg->tail, value++){
		s = *(String **)arg->data;
		value->kind = HOST_STRING;
		value->type = "string";
		if(s == H)
			continue;
		length = s->len >= 0 ? s->len : runenlen(s->Srune, -s->len);
		bytes = malloc(length + 1);
		if(bytes == nil)
			return 0;
		if(s->len >= 0)
			memmove(bytes, s->Sascii, length);
		else
			for(i = 0, end = bytes; i < -s->len; i++)
				end += runetochar(end, &s->Srune[i]);
		bytes[length] = 0;
		value->data = (uchar *)bytes;
		value->length = length;
	}
	return 1;
}

static void
zxfreeargs(ZxCommand *command)
{
	int i;

	for(i = 0; i < command->argc; i++)
		free((void *)command->args[i].data);
	free(command->args);
}

static int
zxs32(HostValue *result, int value)
{
	result->kind = HOST_INTEGER;
	result->type = "s32";
	result->integer = value;
	return 1;
}

static int
zxdraw(void *context, const char *module, const char *function,
	const HostValue *args, int n, HostValue *result)
{
	ZxSurface *surface = context;
	ZX_Window *win = surface->win;
	int rgb = -1;

	USED(module);
	USED(function);
	USED(args);
	if(n != 0)
		return 0;
	if(!surface->opened)
		return zxs32(result, -1);
	acquire();
	if(waserror()){
		release();
		return 0;
	}
	win->input.key = -1;
	if(zxrequest(win, ZX_SampleGuestPointer))
		rgb = win->input.key;
	poperror();
	release();
	return zxs32(result, rgb);
}

static int
zxisindex(const HostValue *value)
{
	return value->kind == HOST_INTEGER && value->type != nil &&
		strcmp(value->type, "s32") == 0 &&
		value->integer >= INT32_MIN && value->integer <= INT32_MAX;
}

static int
zxargs(void *context, const char *module, const char *function,
	const HostValue *args, int n, HostValue *result)
{
	ZxCommand *command = context;
	int i;

	USED(module);
	if(strcmp(function, "Count") == 0)
		return n == 0 && zxs32(result, command->argc);
	if(strcmp(function, "SetFailure") == 0){
		if(n != 1 || args[0].kind != HOST_STRING)
			return 0;
		if(args[0].length >= sizeof(command->failure) || (args[0].length != 0 &&
		   (args[0].data == nil || memchr(args[0].data, 0, args[0].length) != nil)))
			return zxs32(result, -1);
		if(args[0].length != 0)
			memmove(command->failure, args[0].data, args[0].length);
		command->failure[args[0].length] = 0;
		return zxs32(result, 0);
	}
	if(n != 1 || !zxisindex(args))
		return 0;
	i = args[0].integer;
	*result = (i >= 0 && i < command->argc) ? command->args[i] :
		(HostValue){.kind = HOST_STRING, .type = "string"};
	return 1;
}

static void
zxioerrstr(ZxCommand *command, const char *message)
{
	if(message == nil)
		kgerrstr(command->err, sizeof(command->err));
	else
		snprint(command->err, sizeof(command->err), "%s", message);
}

static int
zxioerror(ZxCommand *command, HostValue *result, const char *message)
{
	zxioerrstr(command, message);
	return zxs32(result, -1);
}

static int
zxiopath(const HostValue *name, char *path)
{
	if(name->length > ZxGuestPathBytes || (name->length != 0 &&
	   (name->data == nil || memchr(name->data, 0, name->length) != nil)))
		return 0;
	if(name->length != 0)
		memmove(path, name->data, name->length);
	path[name->length] = 0;
	return 1;
}

#ifdef __linux__
struct ZxProcess {
	Ref ref;
	Rendez wait;
	int done, id;
	ZxProcess *next;
	Fgrp *files;
	ZxCommand command;
	ZxResult result;
	char path[ZxGuestPathBytes + 1];
	/* Task list entry while the worker runs, under zxprocesslock. */
	ZxProcess *listed;
	int pid, hasclock;
	clockid_t cpuclock;
	char user[ZxTaskNameBytes];
};

static Lock zxprocesslock;
static int zxprocessactive, zxprocesspid;
static ZxProcess *zxprocesslist;
static Rendez zxactivity;

void
zxnotifyactivity(void)
{
	Wakeup(&zxactivity);
}

static int
zxprocessadmit(void)
{
	int ok;

	lock(&zxprocesslock);
	ok = zxprocessactive < ZxProcessLimit;
	if(ok)
		zxprocessactive++;
	unlock(&zxprocesslock);
	return ok;
}

static void
zxprocessretire(void)
{
	lock(&zxprocesslock);
	zxprocessactive--;
	unlock(&zxprocesslock);
}

static void
zxprocessrelease(ZxProcess *process)
{
	if(decref(&process->ref) != 0)
		return;
	closefgrp(process->files);
	zxfreeargs(&process->command);
	zxwindowfree(process->command.window);
	if(process->command.control != nil)
		ZxRunControlFree(process->command.control);
	free(process);
}

static void
zxprocessworker(void *arg)
{
	ZxProcess *process = arg;
	ZxSurface surface = {.win = H, .pointermillis = -1};
	ZxProcess **link;

	up->env->fgrp = process->files;
	process->files = nil;
	lock(&zxprocesslock);
	process->pid = ++zxprocesspid;
	process->hasclock = pthread_getcpuclockid(pthread_self(), &process->cpuclock) == 0;
	for(link = &zxprocesslist; *link != nil; link = &(*link)->listed)
		;
	*link = process;
	unlock(&zxprocesslock);
	process->result = zxexecute(process->path, &surface, &process->command);
	lock(&zxprocesslock);
	for(link = &zxprocesslist; *link != process; link = &(*link)->listed)
		;
	*link = process->listed;
	unlock(&zxprocesslock);
	closefgrp(up->env->fgrp);
	up->env->fgrp = nil;
	zxprocessretire();
	lock(&process->wait.l);
	process->done = 1;
	unlock(&process->wait.l);
	Wakeup(&process->wait);
	if(process->command.window != nil)
		zxnotifyactivity();
	zxprocessrelease(process);
}

static int
zxprocessdone(void *arg)
{
	ZxProcess *process = arg;
	return process->done;
}

static int
zxprocessargs(ZxCommand *command, const HostValue *operands)
{
	const HostValue *arg;
	HostValue *copy;
	uchar *data;
	int i;

	if(operands->length == 0)
		return 1;
	if(operands->length > INT32_MAX || operands->length > SIZE_MAX / sizeof(*copy) || operands->elements == nil)
		return 0;
	command->args = calloc(operands->length, sizeof(*copy));
	if(command->args == nil)
		return 0;
	command->argc = operands->length;
	for(i = 0; i < command->argc; i++){
		arg = operands->elements + i;
		copy = command->args + i;
		if(arg->kind != HOST_STRING || (arg->length != 0 && arg->data == nil))
			return 0;
		*copy = (HostValue){.kind = HOST_STRING, .type = "string", .length = arg->length};
		if(arg->length != 0){
			data = malloc(arg->length);
			if(data == nil)
				return 0;
			memmove(data, arg->data, arg->length);
			copy->data = data;
		}
	}
	return 1;
}

static ZxProcess *
zxprocessstart(ZxCommand *command, const HostValue *args, ZxResult *result, int windowed)
{
	ZxProcess *process;
	Fgrp *parent;
	const char *problem = nil;
	int i;

	if(command->depth >= ZxProcessDepth){
		snprint(result->problem, sizeof(result->problem), "ZX command nesting limit reached");
		return nil;
	}
	process = calloc(1, sizeof(*process));
	if(process == nil){
		snprint(result->problem, sizeof(result->problem), "cannot allocate ZX process");
		return nil;
	}
	process->ref.ref = 1;
	process->command.depth = command->depth + 1;
	utfecpy(process->user, process->user+sizeof(process->user), up->env->user);
	if(!zxiopath(args, process->path) || process->path[0] == 0)
		problem = "invalid ZX program path";
	else if(!zxprocessargs(&process->command, args+1))
		problem = "cannot copy ZX process arguments";
	else if(windowed != ZxnNoWindow && (process->command.window = zxwindownew(windowed)) == nil)
		problem = "cannot create ZX window channel";
	else if((process->command.control = ZxRunControlCreate()) == nil)
		problem = "cannot create ZX run control";
	else if(!zxprocessadmit())
		problem = "too many active ZX processes";
	if(problem != nil){
		snprint(result->problem, sizeof(result->problem), "%s", problem);
		zxprocessrelease(process);
		return nil;
	}
	if(waserror()){
		kgerrstr(result->problem, sizeof(result->problem));
		poperror();
		zxprocessretire();
		zxprocessrelease(process);
		return nil;
	}
	/* A child inherits the standard streams, without retaining the manager's
	 * Draw connection, exclusive input channel, or other private descriptors. */
	process->files = newfgrp(nil);
	parent = up->env->fgrp;
	lock(&parent->l);
	for(i = 0; i < 3 && i <= parent->maxfd; i++){
		if(parent->fd[i] == nil)
			continue;
		incref(&parent->fd[i]->r);
		process->files->fd[i] = parent->fd[i];
		process->files->maxfd = i;
	}
	unlock(&parent->l);
	incref(&process->ref);
	kproc("ZX command", zxprocessworker, process, KPDUPPG|KPDUPENVG);
	poperror();
	return process;
}

static int
zxprocessresult(ZxProcess *process, int wait, ZxResult *result)
{
	int done;

	if(wait){
		if(waserror()){
			*result = (ZxResult){0, -1, ""};
			kgerrstr(result->problem, sizeof(result->problem));
			poperror();
			return 0;
		}
		Sleep(&process->wait, zxprocessdone, process);
		poperror();
	}
	lock(&process->wait.l);
	done = process->done;
	unlock(&process->wait.l);
	*result = done ? process->result : (ZxResult){0, -2, ""};
	return done;
}

static ZxResult
zxprocessrun(ZxCommand *command, const HostValue *args)
{
	ZxProcess *process;
	ZxResult result = {0, -1, ""};

	process = zxprocessstart(command, args, &result, 0);
	if(process != nil){
		zxprocessresult(process, 1, &result);
		zxprocessrelease(process);
	}
	return result;
}

static ZxResult
zxprocesscollect(ZxCommand *command, int id, int wait)
{
	ZxProcess **link, *process;
	ZxResult result;

	for(link = &command->children; (process = *link) != nil; link = &process->next){
		if(process->id != id)
			continue;
		if(zxprocessresult(process, wait, &result)){
			*link = process->next;
			command->nchild--;
			zxprocessrelease(process);
		}
		return result;
	}
	return (ZxResult){0, -1, "unknown ZX process"};
}

/* The child stops at its next engine checkpoint. Waking its kproc makes a
 * blocked device read or Sleep return, and disconnecting its window ends a
 * wait for window events. The child's outcome then reports "killed". */
static int
zxprocessstop(ZxProcess *process)
{
	int done;

	lock(&process->wait.l);
	done = process->done;
	unlock(&process->wait.l);
	if(done)
		return 0;
	ZxRunControlRequest(process->command.control);
	zxwindowdisconnect(process->command.window);
	lock(&process->command.runlock);
	if(process->command.runner != nil)
		swiproc(process->command.runner, 0);
	unlock(&process->command.runlock);
	return 1;
}

static int
zxprocesskill(ZxCommand *command, int id)
{
	ZxProcess *process;

	for(process = command->children; process != nil; process = process->next)
		if(process->id == id)
			return zxprocessstop(process);
	return 0;
}

static vlong zxmonotonicnanos(void);

/* Without Dis, the task list is the running ZX processes in start order. */
static int
zxnativetaskcapture(ZxCommand *command)
{
	ZxProcess *process;
	ZxTask *row, *rows;
	struct timespec cpu;
	char *leaf, *end;
	int count, index;
	vlong before, after;

	for(;;){
		lock(&zxprocesslock);
		count = 0;
		for(process = zxprocesslist; process != nil; process = process->listed)
			count++;
		if(count > ZxTaskLimit || count <= command->taskcap)
			break;
		unlock(&zxprocesslock);
		rows = realloc(command->tasks, count * sizeof(*rows));
		if(rows == nil)
			return -1;
		command->tasks = rows;
		command->taskcap = count;
	}
	if(count > ZxTaskLimit){
		unlock(&zxprocesslock);
		return -2;
	}
	before = zxmonotonicnanos();
	for(index = 0, process = zxprocesslist; process != nil; index++, process = process->listed){
		row = &command->tasks[index];
		row->pid = process->pid;
		row->group = 0;
		row->state = Pready;
		row->kib = -1;
		row->cpunanos = -1;
		if(process->hasclock && clock_gettime(process->cpuclock, &cpu) == 0)
			row->cpunanos = (vlong)cpu.tv_sec * 1000000000LL + cpu.tv_nsec;
		leaf = utfrrune(process->path, '/');
		leaf = leaf == nil ? process->path : leaf+1;
		utfecpy(row->module, row->module+sizeof(row->module), leaf);
		end = strrchr(row->module, '.');
		if(end != nil && strcmp(end, ".zx") == 0)
			*end = 0;
		utfecpy(row->user, row->user+sizeof(row->user), process->user);
	}
	after = zxmonotonicnanos();
	unlock(&zxprocesslock);
	command->tasksample = -1;
	command->taskskew = -1;
	if(before >= 0 && after >= before){
		command->tasksample = before + (after - before)/2;
		command->taskskew = after - command->tasksample;
	}
	for(index = 0; index < nelem(command->pools); index++)
		poolusage(index, command->pools[index]);
	command->ntask = count;
	command->tasksvalid = 1;
	return count;
}

static int
zxnativeterminate(ZxCommand *command, int pid)
{
	ZxProcess *process;
	int i, status;

	status = -1;
	for(i = 0; i < command->ntask; i++)
		if(command->tasks[i].pid == pid)
			status = -2;
	if(status == -1)
		return -1;
	lock(&zxprocesslock);
	for(process = zxprocesslist; process != nil; process = process->listed){
		if(process->pid != pid)
			continue;
		if(&process->command == command)
			status = -1;
		else if(zxprocessstop(process))
			status = 0;
		break;
	}
	unlock(&zxprocesslock);
	return status;
}

static void
zxprocessforget(ZxCommand *command)
{
	ZxProcess *process;

	while((process = command->children) != nil){
		command->children = process->next;
		zxwindowdisconnect(process->command.window);
		zxprocessrelease(process);
	}
}

static int
zxprocessregister(ZxCommand *command, const HostValue *args, ZxResult *result, int windowed)
{
	ZxProcess *process;

	if(command->nchild >= ZxProcessLimit || command->childid == INT32_MAX){
		snprint(result->problem, sizeof(result->problem), "too many outstanding ZX processes");
		return 0;
	}
	process = zxprocessstart(command, args, result, windowed);
	if(process == nil)
		return 0;
	process->id = ++command->childid;
	process->next = command->children;
	command->children = process;
	command->nchild++;
	return process->id;
}

static int
zxprocess(void *context, const char *module, const char *function,
	const HostValue *args, int n, HostValue *result)
{
	ZxCommand *command = context;
	ZxResult *outcome = &command->outcome;
	HostField *fields = command->outfields;
	int id;

	USED(module);
	if(strcmp(function, "Run") == 0 || strcmp(function, "Start") == 0){
		if(n != 2 || args[0].kind != HOST_STRING || args[1].kind != HOST_SLICE)
			return 0;
		if(strcmp(function, "Start") == 0){
			*outcome = (ZxResult){0, -1, ""};
			id = zxprocessregister(command, args, outcome, 0);
			fields[0] = (HostField){"id", {.kind = HOST_INTEGER, .type = "s32", .integer = id}};
			fields[1] = (HostField){"error", {.kind = HOST_STRING, .type = "string",
				.data = (uchar*)outcome->problem, .length = strlen(outcome->problem)}};
			*result = (HostValue){.kind = HOST_RECORD, .type = "taijios_process.Launch", .fields = fields,
				.field_count = 2};
			return 1;
		}
		*outcome = zxprocessrun(command, args);
	}else if(strcmp(function, "Kill") == 0){
		if(n != 1 || !zxisindex(args))
			return 0;
		zxbool(result, zxprocesskill(command, args[0].integer));
		return 1;
	}else{
		if(n != 1 || !zxisindex(args))
			return 0;
		*outcome = zxprocesscollect(command, args[0].integer, strcmp(function, "Wait") == 0);
	}
	fields[0] = (HostField){"status", {.kind = HOST_INTEGER, .type = "s32", .integer = outcome->status}};
	fields[1] = (HostField){"value", {.kind = HOST_INTEGER, .type = "s64", .integer = outcome->value}};
	fields[2] = (HostField){"error", {.kind = HOST_STRING, .type = "string", .data = (uchar*)outcome->problem,
		.length = strlen(outcome->problem)}};
	*result = (HostValue){.kind = HOST_RECORD, .type = "taijios_process.Outcome", .fields = fields,
		.field_count = nelem(command->outfields)};
	return 1;
}
#endif

static int
zxioslot(ZxCommand *command)
{
	int slot, count, *fds;

	for(slot = 0; slot < command->nfd && command->fd[slot] >= 0; slot++)
		;
	if(slot < command->nfd)
		return slot;
	if(slot == MAXNFD)
		return -1;
	count = slot == 0 ? ZxInitialFiles : slot * 2;
	if(count > MAXNFD)
		count = MAXNFD;
	fds = realloc(command->fd, count * sizeof(*fds));
	if(fds == nil)
		return -1;
	command->fd = fds;
	while(command->nfd < count)
		fds[command->nfd++] = -1;
	return slot;
}

static int
zxioopen(ZxCommand *command, const HostValue *args, int n, int create, int flags, HostValue *result)
{
	static const int modes[] = {OREAD, OWRITE, ORDWR};
	char path[ZxGuestPathBytes + 1];
	int slot, mode, fd;

	if(n != (create ? 3 : 2) || args[0].kind != HOST_STRING || !zxisindex(args + 1) ||
	   (create && !zxisindex(args + 2)))
		return 0;
	if(!zxiopath(args, path))
		return zxioerror(command, result, "invalid file name");
	mode = args[1].integer;
	if(create && flags == OEXCL && (mode & ORCLOSE) != 0){
		flags |= ORCLOSE;
		mode &= ~ORCLOSE;
	}
	if(mode < 0 || mode >= nelem(modes))
		return zxioerror(command, result, "invalid open mode");
	slot = zxioslot(command);
	if(slot < 0)
		return zxioerror(command, result, "too many open ZX files");
	fd = create ? kcreate(path, modes[mode] | flags, (uint32_t)args[2].integer) : kopen(path, modes[mode]);
	if(fd < 0)
		return zxioerror(command, result, nil);
	command->fd[slot] = fd;
	return zxs32(result, slot + 3);
}

static int
zxioslice(const HostValue *buffer)
{
	return buffer->kind == HOST_SLICE && buffer->type != nil &&
		strcmp(buffer->type, "[]u8") == 0 && (buffer->length == 0 || buffer->elements != nil);
}

static int
zxstatrecord(ZxCommand *command, Dir *dir, const HostValue *buffer, uchar *bytes, HostValue *result)
{
	int count, i;

	if(dir == nil)
		return zxioerror(command, result, nil);
	count = sizeD2M(dir);
	if(count <= ZxIoBytes && count <= buffer->length)
		count = convD2M(dir, bytes, count);
	else
		count = 0;
	free(dir);
	if(count <= BIT16SZ)
		return zxioerror(command, result, "stat record does not fit");
	for(i = 0; i < count; i++)
		buffer->elements[i].bits = bytes[i];
	return zxs32(result, count);
}

static int
zxiostat(ZxCommand *command, const HostValue *args, int n, uchar *packed, HostValue *result)
{
	char path[ZxGuestPathBytes + 1];
	const HostValue *buffer;
	Dir *dir;
	int i;

	if(n != 2 || args[0].kind != HOST_STRING)
		return 0;
	buffer = args + 1;
	if(!zxioslice(buffer))
		return 0;
	if(packed == nil && buffer->length < 12)
		return zxioerror(command, result, "stat needs a 12-byte buffer");
	if(!zxiopath(args, path))
		return zxioerror(command, result, "invalid file name");
	if(packed != nil)
		return zxstatrecord(command, kdirstat(path), buffer, packed, result);
	dir = kdirstat(path);
	if(dir == nil)
		return zxioerror(command, result, nil);
	for(i = 0; i < 8; i++)
		buffer->elements[i].bits = (uchar)((uint64_t)dir->length >> (8*i));
	for(i = 0; i < 4; i++)
		buffer->elements[8+i].bits = (uchar)((uint32_t)dir->mode >> (8*i));
	free(dir);
	return zxs32(result, 0);
}

static int
zxioseek(ZxCommand *command, int fd, const HostValue *args, int n, HostValue *result)
{
	vlong offset;
	int origin;

	if(n != 3 || args[1].kind != HOST_INTEGER || args[1].type == nil ||
	   strcmp(args[1].type, "s64") != 0 || !zxisindex(args + 2))
		return 0;
	origin = args[2].integer;
	offset = -1;
	if(fd < 0)
		zxioerrstr(command, "invalid ZX file handle");
	else if(origin < 0 || origin > 2)
		zxioerrstr(command, "invalid seek origin");
	else if((offset = kseek(fd, args[1].integer, origin)) < 0)
		zxioerrstr(command, nil);
	result->kind = HOST_INTEGER;
	result->type = "s64";
	result->integer = offset;
	return 1;
}

static int
zxiolocation(ZxCommand *command, int home, HostValue *result)
{
	char path[ZxGuestPathBytes + 1];
	int fd, count;

	free(command->fdpath);
	command->fdpath = nil;
	fd = kopen(home ? "#e/home" : ".", OREAD);
	if(fd < 0)
		zxioerrstr(command, nil);
	else{
		if(home){
			count = kread(fd, path, sizeof(path));
			if(count < 0)
				zxioerrstr(command, nil);
			else if(count > 0 && count < sizeof(path) && path[0] == '/' &&
			    memchr(path, 0, count) == nil){
				path[count] = 0;
				command->fdpath = strdup(path);
				if(command->fdpath == nil)
					zxioerrstr(command, "out of memory copying guest home");
			}else
				zxioerrstr(command, "invalid guest home path");
		}else{
			command->fdpath = kfd2path(fd);
			if(command->fdpath == nil)
				zxioerrstr(command, nil);
		}
		kclose(fd);
	}
	*result = (HostValue){.kind = HOST_STRING, .type = "string", .data = (uchar *)command->fdpath,
		.length = command->fdpath == nil ? 0 : strlen(command->fdpath)};
	return 1;
}

static int
zxio(void *context, const char *module, const char *function,
	const HostValue *args, int n, HostValue *result)
{
	ZxCommand *command = context;
	const HostValue *buffer;
	uchar bytes[ZxIoBytes];
	size_t length;
	long count, i;
	int handle, fd;

	USED(module);
	if(strcmp(function, "Error") == 0){
		if(n != 0)
			return 0;
		*result = (HostValue){.kind = HOST_STRING, .type = "string",
			.data = (uchar *)command->err, .length = strlen(command->err)};
		return 1;
	}
	if(strcmp(function, "Open") == 0)
		return zxioopen(command, args, n, 0, 0, result);
	if(strcmp(function, "Create") == 0)
		return zxioopen(command, args, n, 1, 0, result);
	if(strcmp(function, "CreateNew") == 0)
		return zxioopen(command, args, n, 1, OEXCL, result);
	if(strcmp(function, "Remove") == 0){
		char path[ZxGuestPathBytes + 1];

		if(n != 1 || args[0].kind != HOST_STRING)
			return 0;
		if(!zxiopath(args, path) || path[0] == 0)
			return zxioerror(command, result, "invalid file name");
		return kremove(path) < 0 ? zxioerror(command, result, nil) : zxs32(result, 0);
	}
	if(strcmp(function, "Cwd") == 0 || strcmp(function, "Home") == 0){
		if(n != 0)
			return 0;
		return zxiolocation(command, strcmp(function, "Home") == 0, result);
	}
	if(strcmp(function, "Stat") == 0)
		return zxiostat(command, args, n, nil, result);
	if(strcmp(function, "StatPacked") == 0)
		return zxiostat(command, args, n, bytes, result);
	if(n < 1 || !zxisindex(args))
		return 0;
	handle = args[0].integer;
	if(strcmp(function, "FdPath") == 0){
		if(n != 1)
			return 0;
		free(command->fdpath);
		command->fdpath = kfd2path(handle);
		*result = (HostValue){.kind = HOST_STRING, .type = "string",
			.data = (uchar *)command->fdpath,
			.length = command->fdpath == nil ? 0 : strlen(command->fdpath)};
		return 1;
	}
	if(handle >= 0 && handle < 3)
		fd = handle;
	else if(handle >= 3 && handle - 3 < command->nfd)
		fd = command->fd[handle - 3];
	else
		fd = -1;
	if(strcmp(function, "Seek") == 0)
		return zxioseek(command, fd, args, n, result);
	if(fd < 0)
		return zxioerror(command, result, "invalid ZX file handle");
	if(strcmp(function, "Close") == 0){
		if(n != 1)
			return 0;
		if(handle < 3)
			return zxioerror(command, result, "cannot close a standard stream");
		command->fd[handle - 3] = -1;
		return kclose(fd) < 0 ? zxioerror(command, result, nil) : zxs32(result, 0);
	}
	if(strcmp(function, "Sync") == 0 || strcmp(function, "RenameSameDir") == 0){
		int renamefile = strcmp(function, "RenameSameDir") == 0;
		char name[ZxGuestPathBytes + 1];
		Dir dir;

		if(n != (renamefile ? 2 : 1))
			return 0;
		if(handle < 3)
			return zxioerror(command, result, "cannot update a standard stream");
		nulldir(&dir);
		if(renamefile){
			if(!zxiopath(args+1, name) || name[0] == 0 || strchr(name, '/') != nil ||
			   strcmp(name, ".") == 0 || strcmp(name, "..") == 0)
				return zxioerror(command, result, "rename needs a basename");
			dir.name = name;
		}
		count = convD2M(&dir, bytes, sizeof(bytes));
		if(count < STATFIXLEN || kfwstat(fd, bytes, count) < 0)
			return zxioerror(command, result, nil);
		return zxs32(result, 0);
	}
	if(n != 2)
		return 0;
	buffer = args + 1;
	length = buffer->length > sizeof(bytes) ? sizeof(bytes) : buffer->length;
	if(strcmp(function, "FstatPacked") == 0){
		if(!zxioslice(buffer))
			return 0;
		return zxstatrecord(command, kdirfstat(fd), buffer, bytes, result);
	}
	if(strcmp(function, "WstatPacked") == 0){
		if(buffer->kind != HOST_STRING || (length != 0 && buffer->data == nil))
			return 0;
		if(length != buffer->length || length < STATFIXLEN)
			return zxioerror(command, result, "invalid stat record size");
		memmove(bytes, buffer->data, length);
		count = kfwstat(fd, bytes, length);
	}else if(strcmp(function, "Read") == 0){
		if(!zxioslice(buffer))
			return 0;
		count = length == 0 ? 0 : kread(fd, bytes, length);
		if(count > 0){
			BundleHostRenewSteps();
			if(command->surface != nil && !command->surface->imageactive)
				command->surface->imagepermit = 1;
		}
		for(i = 0; i < count; i++)
			buffer->elements[i].bits = bytes[i];
	}else{
		if(buffer->kind != HOST_STRING || (length != 0 && buffer->data == nil))
			return 0;
		count = length == 0 ? 0 : kwrite(fd, (void *)buffer->data, length);
	}
	return count < 0 ? zxioerror(command, result, nil) : zxs32(result, count);
}

static vlong
zxmonotonicnanos(void)
{
	struct timespec now;

	if(clock_gettime(CLOCK_MONOTONIC, &now) < 0)
		return -1;
	return (vlong)now.tv_sec * 1000000000LL + now.tv_nsec;
}

static int
zxtaskcapture(ZxCommand *command)
{
	ZxTask *row, *rows;
	Prog *p;
	Frame *frame;
	char *name;
	int count, index;
	vlong before, after;

	command->tasksvalid = 0;
#ifdef __linux__
	if(!command->hosted)
		return zxnativetaskcapture(command);
#endif
	if(!progdevbound())
		return -1;
	acquire();
	count = nprog();
	if(count > ZxTaskLimit){
		release();
		return -2;
	}
	if(count > command->taskcap){
		rows = realloc(command->tasks, count * sizeof(*rows));
		if(rows == nil){
			release();
			return -1;
		}
		command->tasks = rows;
		command->taskcap = count;
	}
	before = zxmonotonicnanos();
	for(index = 0, p = progn(0); p != nil; index++, p = p->next)
		command->tasks[index].cpunanos = progcpunanos(p);
	after = zxmonotonicnanos();
	command->tasksample = -1;
	command->taskskew = -1;
	if(before >= 0 && after >= before){
		command->tasksample = before + (after - before)/2;
		command->taskskew = after - command->tasksample;
	}
	for(index = 0, p = progn(0); p != nil; index++, p = p->next){
		row = &command->tasks[index];
		row->pid = p->pid;
		row->state = p->state;
		row->group = p->group == nil ? 0 : p->group->id;
		row->kib = -1;
		name = "";
		if(p->state != Pexiting && p->R.M != H){
			name = p->R.M->m->name;
			frame = (Frame*)p->R.FP;
			if(name[0] == '$' && frame != nil && frame->mr != nil)
				name = frame->mr->m->name;
			row->kib = progsize(p);
		}
		utfecpy(row->module, row->module+sizeof(row->module), name);
		utfecpy(row->user, row->user+sizeof(row->user), ((Osenv*)p->osenv)->user);
	}
	for(index = 0; index < nelem(command->pools); index++)
		poolusage(index, command->pools[index]);
	release();
	command->ntask = count;
	command->tasksvalid = 1;
	return count;
}

static int
zxtaskslice(const HostValue *value, const char *type, size_t count)
{
	return value->kind == HOST_SLICE && value->type != nil &&
		strcmp(value->type, type) == 0 && value->length >= count && value->elements != nil;
}

#ifdef __linux__
static int
zxnativeready(void *arg)
{
	ZxCommand *command = arg;
	ZxProcess *process;
	int done;

	if(ginputready())
		return 1;
	for(process = command->children; process != nil; process = process->next){
		lock(&process->wait.l);
		done = process->done;
		unlock(&process->wait.l);
		if(done || zxwindowrequest(process->command.window, nil))
			return 1;
	}
	return 0;
}

static int
zxnativelaunch(void *context, const char *module, const char *function,
	const HostValue *args, int n, HostValue *result)
{
	char path[ZxGuestPathBytes + 1];
	char payload[ZxGuestPathBytes + 1 + ZxLaunchArgBytes];
	const HostValue *argv = args+1;
	int length;

	USED(module);
	USED(function);
	if(n != 2 || args[0].kind != HOST_STRING || argv->kind != HOST_STRING)
		return 0;
	if(!zxiopath(args, path) || path[0] == 0 || argv->length == 0 || argv->length > ZxLaunchArgBytes ||
	   argv->data == nil || argv->data[0] == 0 || argv->data[argv->length-1] != 0)
		return zxs32(result, -1);
	length = args[0].length + 1;
	memmove(payload, path, length);
	memmove(payload + length, argv->data, argv->length);
	return zxs32(result, zxwindowsubmit(context, (ZxNativeRequest){.kind = ZxnLaunch, .data = (uchar*)payload,
		.length = length + argv->length}) ? 0 : -1);
}

static int
zxnativelaunchrequest(ZxCommand *command, ZxNativeRequest *request)
{
	HostValue argv[63], args[2];
	const char *path, *word, *end, *next;
	int length, argc = 0;
	Dir *info;

	path = (const char*)request->data;
	end = path + request->length;
	length = strlen(path);
	if(length < 4 || strcmp(path+length-3, ".zx") != 0)
		return 0;
	info = kdirstat((char*)path);
	if(info == nil)
		return 0;
	if(info->mode & DMDIR){
		free(info);
		return 0;
	}
	free(info);
	word = path + length + 1;
	word += strlen(word) + 1; /* Match the console ABI: omit argv[0]. */
	for(; word < end; word = next + 1){
		next = memchr(word, 0, end-word);
		if(next == nil || argc == nelem(argv))
			return 0;
		argv[argc++] = (HostValue){.kind = HOST_STRING, .type = "string", .data = (const uchar*)word,
			.length = next-word};
	}
	args[0] = (HostValue){.kind = HOST_STRING, .type = "string", .data = (const uchar*)path, .length = length};
	args[1] = (HostValue){.kind = HOST_SLICE, .type = "[]string", .elements = argv, .length = argc};
	return zxprocessregister(command, args, &command->outcome, ZxnApplication);
}

enum { ZxCursorHeader = 16, ZxCursorBytes = ZxCursorHeader + 2*ZxCursorSide*ZxCursorSide/8 };

static int
zxnativetools(void *context, const char *module, const char *function,
	const HostValue *args, int n, HostValue *result)
{
	ZxNativeRequest request;
	uchar buffer[ZxCursorBytes];
	vlong width, height, x, y;
	unsigned int i;

	USED(module);
	if(strcmp(function, "Resize") == 0){
		request = (ZxNativeRequest){.kind = ZxnResize};
		if(n != 2 || !zxsize(args)){
			zxbool(result, 0);
			return 1;
		}
		request.width = args[0].integer;
		request.height = args[1].integer;
	}else{
		if(n != 5 || !zxisindex(args) || !zxisindex(args+1) || !zxisindex(args+2) || !zxisindex(args+3) ||
		   args[4].kind != HOST_STRING)
			return 0;
		request = (ZxNativeRequest){.kind = ZxnCursor};
		x = args[0].integer;
		y = args[1].integer;
		width = args[2].integer;
		height = args[3].integer;
		if(width != 0 || height != 0 || args[4].length != 0){
			if(args[4].data == nil || !zxcursorvalid(x, y, width, height, args[4].length)){
				zxbool(result, 0);
				return 1;
			}
			for(i = 0; i < 4; i++){
				uint v = args[i].integer;
				uchar *p = buffer + i*4;
				BPLONG(p, v);
			}
			memmove(buffer + ZxCursorHeader, args[4].data, args[4].length);
			request.data = buffer;
			request.length = ZxCursorHeader + args[4].length;
		}
	}
	zxbool(result, zxwindowsubmit(context, request));
	return 1;
}

static int
zxnativesetcursor(const HostValue *value)
{
	uchar buffer[ZxCursorBytes];
	size_t i;
	int fd, written;

	if(!zxioslice(value) || value->length > sizeof(buffer))
		return 0;
	for(i = 0; i < value->length; i++)
		buffer[i] = value->elements[i].bits;
	if(value->length != 0 && (value->length < ZxCursorHeader ||
	   !zxcursorvalid((int)BGLONG(buffer), (int)BGLONG(buffer+4), (int)BGLONG(buffer+8),
		(int)BGLONG(buffer+12), value->length - ZxCursorHeader)))
		return 0;
	fd = kopen("#m/cursor", OWRITE);
	if(fd < 0)
		return 0;
	written = kwrite(fd, buffer, value->length);
	kclose(fd);
	return written == (int)value->length;
}

static int
zxnativesample(void *context, const char *module, const char *function,
	const HostValue *args, int n, HostValue *result)
{
	USED(module);
	USED(function);
	USED(args);
	if(n != 0)
		return 0;
	return zxs32(result, zxwindowsubmit(context, (ZxNativeRequest){.kind = ZxnSample}) - 1);
}

static int
zxnativemanager(void *context, const char *module, const char *function,
	const HostValue *args, int n, HostValue *result)
{
	ZxCommand *command = context;
	ZxProcess *process;
	ZxNativeRequest request;
	ZxNativeWindow *window;
	int i, kind, fields[9];

	USED(module);
	if(strcmp(function, "StartWindow") == 0 || strcmp(function, "StartDesktop") == 0){
		if(n != 2 || args[0].kind != HOST_STRING || args[1].kind != HOST_SLICE)
			return 0;
		kind = strcmp(function, "StartDesktop") == 0 ? ZxnDesktop : ZxnApplication;
		if(kind == ZxnDesktop)
			for(process = command->children; process != nil; process = process->next)
				if(zxwindowdesktop(process->command.window))
					return zxs32(result, 0);
		return zxs32(result, zxprocessregister(command, args, &command->outcome, kind));
	}
	if(strcmp(function, "WaitActivity") == 0){
		if(n != 0)
			return 0;
		if(waserror()){
			poperror();
			zxbool(result, 0);
			return 1;
		}
		Sleep(&zxactivity, zxnativeready, command);
		poperror();
		BundleHostRenewSteps();
		zxbool(result, 1);
		return 1;
	}
	if(strcmp(function, "ApplyCursor") == 0){
		if(n != 1)
			return 0;
		zxbool(result, zxnativesetcursor(args));
		return 1;
	}
	if(strcmp(function, "Request") == 0){
		if(n != 2 || !zxisindex(args) || !zxtaskslice(args+1, "[]s32", 7))
			return 0;
		for(process = command->children; process != nil; process = process->next){
			if(args[0].integer != 0 && process->id >= args[0].integer)
				continue;
			if(!zxwindowrequest(process->command.window, &request))
				continue;
			args[1].elements[0].integer = request.kind;
			args[1].elements[1].integer = request.width;
			args[1].elements[2].integer = request.height;
			args[1].elements[3].integer = request.first;
			args[1].elements[4].integer = request.rows;
			args[1].elements[5].integer = request.flag;
			args[1].elements[6].integer = request.length;
			return zxs32(result, process->id);
		}
		return zxs32(result, 0);
	}
	if(n < 1 || !zxisindex(args))
		return 0;
	for(process = command->children; process != nil && process->id != args[0].integer; process = process->next)
		;
	window = process == nil ? nil : process->command.window;
	if(strcmp(function, "Text") == 0){
		*result = (HostValue){.kind = HOST_STRING, .type = "string"};
		if(n != 1)
			return 0;
		kind = zxwindowrequest(window, &request);
		if(kind == ZxnOpen || kind == ZxnTitle || kind == ZxnWindowAction || kind == ZxnDesktopAction || kind == ZxnLaunch){
			result->data = request.data;
			result->length = request.length;
		}
		return 1;
	}
	if(strcmp(function, "Snapshot") == 0){
		if(n != 4)
			return 0;
		zxbool(result, zxwindowsnapshot(window, args+1));
		return 1;
	}
	if(strcmp(function, "ChromeRegions") == 0){
		if(n != 2 || !zxtaskslice(args+1, "[]s32", ZxnChromeFields))
			return 0;
		if(zxwindowrequest(window, &request) != ZxnChrome || request.length > ZxnChromeFields)
			return zxs32(result, -1);
		for(i = 0; i < request.length; i++)
			args[1].elements[i].integer = request.regions[i];
		return zxs32(result, i);
	}
	if(strcmp(function, "LaunchWindow") == 0){
		if(n != 1)
			return 0;
		return zxs32(result, zxwindowrequest(window, &request) == ZxnLaunch ? zxnativelaunchrequest(command, &request) : 0);
	}
	if(strcmp(function, "Payload") == 0){
		if(n != 3 || !zxisindex(args+1) || !zxioslice(args+2) || args[1].integer < 0)
			return 0;
		kind = zxwindowrequest(window, &request);
		if((kind != ZxnFrame && kind != ZxnCursor) ||
		   args[1].integer > request.length || args[2].length > request.length - args[1].integer ||
		   args[2].length > ZxIoBytes)
			return zxs32(result, 0);
		for(i = 0; i < args[2].length; i++)
			args[2].elements[i].bits = request.data[args[1].integer+i];
		return zxs32(result, i);
	}
	if(strcmp(function, "Reply") == 0){
		if(n != 2 || args[1].kind != HOST_INTEGER || args[1].type == nil || strcmp(args[1].type, "bool") != 0)
			return 0;
		zxbool(result, zxwindowreply(window, args[1].integer != 0));
		return 1;
	}
	if(strcmp(function, "ReplySample") == 0){
		if(n != 2 || !zxisindex(args+1) || args[1].integer < -1 || args[1].integer > 0xffffff)
			return 0;
		zxbool(result, zxwindowrequest(window, nil) == ZxnSample && zxwindowreply(window, args[1].integer + 1));
		return 1;
	}
	if(strcmp(function, "Disconnect") == 0){
		if(n != 1)
			return 0;
		zxwindowdisconnect(window);
		result->kind = HOST_VOID;
		return 1;
	}
	if(n != 3 || !zxtaskslice(args+1, "[]s32", nelem(fields)) || args[2].kind != HOST_INTEGER ||
	   args[2].type == nil || strcmp(args[2].type, "s64") != 0)
		return 0;
	for(i = 0; i < nelem(fields); i++){
		if(!zxisindex(&args[1].elements[i]))
			return 0;
		fields[i] = args[1].elements[i].integer;
	}
	if(fields[0] == ZX_Closed)
		zxwindowdisconnect(window);
	zxbool(result, fields[0] == ZX_Closed ? window != nil : zxwindowinput(window, fields, args[2].integer));
	return 1;
}
#endif

static void
zxtaskname(const HostValue *value, const char *name)
{
	int i;

	for(i = 0; name[i] != 0; i++)
		value->elements[i].bits = (uchar)name[i];
	value->elements[i].bits = 0;
}

static int
zxpanel(void *context, const char *module, const char *function,
	const HostValue *args, int n, HostValue *result)
{
	ZxSurface *surface = context;
	ZX_Window *win = surface->win;
	ZX_Panel *panel;
	ZX_PanelEntry *entry;
	char group[ZxPanelLabelBytes], label[ZxPanelLabelBytes];
	int i, width, index, ok, snapshot, row, popup, paint, flush;

	USED(module);
	snapshot = strcmp(function, "Snapshot") == 0;
	row = strcmp(function, "Row") == 0;
	popup = strcmp(function, "Popup") == 0;
	paint = strcmp(function, "Paint") == 0;
	flush = strcmp(function, "Flush") == 0;
	if(snapshot){
		if(n != 1 || !zxtaskslice(args, "[]s32", 4))
			return 0;
	}else if(row){
		if(n != 4 || !zxisindex(args) || !zxtaskslice(args+1, "[]s32", 2) ||
		   !zxtaskslice(args+2, "[]u8", ZxPanelLabelBytes) ||
		   !zxtaskslice(args+3, "[]u8", ZxPanelLabelBytes))
			return 0;
	}else if(paint){
		if(n != 6 || args[5].kind != HOST_STRING || args[5].length >= ZxPanelLabelBytes)
			return 0;
		for(i = 0; i < 5; i++)
			if(!zxisindex(args+i))
				return 0;
	}else if(flush){
		if(n != 0)
			return 0;
	}else if(n != 2 || !zxisindex(args) || !zxisindex(args+1))
		return 0;

	acquire();
	if(waserror()){
		release();
		return 0;
	}
	panel = win->panel;
	width = 0;
	ok = 0;
	if(panel != H){
		if(snapshot){
			args->elements[0].integer = panel->generation;
			args->elements[1].integer = panel->count;
			args->elements[2].integer = panel->focused;
			args->elements[3].integer = panel->height;
			width = panel->width;
		}else if(row){
			index = args[0].integer;
			if(index >= 0 && index < panel->count){
				entry = (ZX_PanelEntry*)panel->rows->data + index;
				utfecpy(group, group+sizeof(group), string2c(entry->group));
				utfecpy(label, label+sizeof(label), string2c(entry->label));
				args[1].elements[0].integer = entry->kind;
				args[1].elements[1].integer = entry->id;
				zxtaskname(args+2, group);
				zxtaskname(args+3, label);
				ok = 1;
			}
		}else if(flush){
			ok = zxrequest(win, ZX_PanelFlush);
		}else if(paint){
			win->input.x = args[0].integer;
			win->input.y = args[1].integer;
			win->input.width = args[2].integer;
			win->input.height = args[3].integer;
			win->input.key = args[4].integer;
			if(args[5].length == 0)
				ok = zxrequest(win, ZX_PanelPaint);
			else
				ok = zxtextrequest(win, ZX_PanelPaint, args[5].data, args[5].length);
		}else{
			win->input.x = args[0].integer;
			win->input.y = args[1].integer;
			ok = zxrequest(win, popup ? ZX_PanelPopup : ZX_PanelChoose);
		}
	}
	poperror();
	release();
	if(snapshot)
		return zxs32(result, width);
	zxbool(result, ok);
	return 1;
}

static void
zxdesktopname(const HostValue *value, String *text)
{
	char buffer[ZxPanelLabelBytes];
	size_t limit = value->length < sizeof(buffer) ? value->length : sizeof(buffer);

	utfecpy(buffer, buffer+limit, string2c(text));
	zxtaskname(value, buffer);
}

static int
zxdesktoprow(ZX_Desktop *desktop, const HostValue *args, int launcher)
{
	int index = args[0].integer;
	ZX_PanelEntry *entry;
	ZX_DesktopWindow *window;
	Array *rows = launcher ? desktop->launchers : desktop->windows;

	if(rows == H || index < 0 || index >= rows->len)
		return 0;
	if(launcher){
		entry = (ZX_PanelEntry*)rows->data + index;
		args[1].elements[0].integer = entry->id;
		zxdesktopname(args+2, entry->label);
		zxdesktopname(args+3, entry->group);
		zxdesktopname(args+4, H);
	}else{
		window = (ZX_DesktopWindow*)rows->data + index;
		args[1].elements[0].integer = window->id;
		args[1].elements[1].integer = window->x;
		args[1].elements[2].integer = window->y;
		args[1].elements[3].integer = window->width;
		args[1].elements[4].integer = window->height;
		args[1].elements[5].integer = window->workspace;
		args[1].elements[6].integer = window->focused;
		args[1].elements[7].integer = window->minimized;
		args[1].elements[8].integer = window->maximized;
		zxdesktopname(args+2, window->title);
		zxdesktopname(args+3, window->appid);
	}
	return 1;
}

static int
zxdesktop(void *context, const char *module, const char *function,
	const HostValue *args, int n, HostValue *result)
{
	ZxSurface *surface = context;
	ZX_Window *win = surface->win;
	ZX_Desktop *desktop;
	const HostValue *action = nil;
	int op, count, ok, i;

	USED(module);
	if(strcmp(function, "UnixSeconds") == 0){
		extern vlong timeoffset;
		if(n != 0)
			return 0;
		result->kind = HOST_INTEGER;
		result->type = "s64";
		result->integer = (timeoffset + osusectime()) / 1000000;
		return 1;
	}
	if(strcmp(function, "BindDesktop") == 0 || strcmp(function, "TimezoneOffsetSeconds") == 0){
		if(n != 0)
			return 0;
		op = strcmp(function, "BindDesktop") == 0 ? ZX_DesktopBind : ZX_DesktopTimezone;
	}else if(strcmp(function, "Capture") == 0){
		if(n != 1 || !zxtaskslice(args, "[]s32", 7))
			return 0;
		op = ZX_DesktopCapture;
	}else if(strcmp(function, "LauncherAt") == 0 || strcmp(function, "WindowAt") == 0){
		op = strcmp(function, "LauncherAt") == 0 ? -1 : -2;
		if(n != (op == -1 ? 5 : 4) || !zxisindex(args) ||
		   !zxtaskslice(args+1, "[]s32", op == -1 ? 1 : 9))
			return 0;
		for(i = 2; i < n; i++)
			if(!zxtaskslice(args+i, "[]u8", 1))
				return 0;
	}else if(strcmp(function, "SetChromeRegions") == 0){
		if(n != 1 || args[0].kind != HOST_SLICE || args[0].type == nil ||
		   strcmp(args[0].type, "[]s32") != 0 || args[0].length > 32 ||
		   args[0].length % 4 != 0 || (args[0].length > 0 && args[0].elements == nil))
			return 0;
		op = ZX_DesktopChrome;
	}else if(strcmp(function, "Launch") == 0){
		if(n != 1 || !zxisindex(args))
			return 0;
		op = ZX_DesktopLaunch;
	}else if(strcmp(function, "WindowAction") == 0){
		if(n != 6 || !zxisindex(args))
			return 0;
		for(i = 2; i < n; i++)
			if(!zxisindex(args+i))
				return 0;
		action = args+1;
		op = ZX_DesktopWindowAction;
	}else{
		if(n != 2 || !zxisindex(args+1))
			return 0;
		action = args;
		op = ZX_DesktopAction;
	}
	if(action != nil && (action->kind != HOST_STRING || action->length == 0 ||
	   action->length > 32 || action->data == nil || memchr(action->data, 0, action->length) != nil)){
		zxbool(result, 0);
		return 1;
	}

	acquire();
	if(waserror()){
		release();
		return 0;
	}
	desktop = win->desktop;
	count = -1;
	ok = 0;
	if(desktop != H){
		if(op < 0)
			ok = zxdesktoprow(desktop, args, op == -1);
		else if(op == ZX_DesktopCapture){
			if(zxrequest(win, op)){
				args[0].elements[0].integer = desktop->generation;
				args[0].elements[1].integer = desktop->windows == H ? 0 : desktop->windows->len;
				args[0].elements[2].integer = desktop->focused;
				args[0].elements[3].integer = desktop->width;
				args[0].elements[4].integer = desktop->height;
				args[0].elements[5].integer = desktop->workspacecount;
				args[0].elements[6].integer = desktop->currentworkspace;
				count = desktop->launchers == H ? 0 : desktop->launchers->len;
			}
		}else if(op == ZX_DesktopChrome){
			if(desktop->regions != H && args[0].length <= desktop->regions->len){
				desktop->regioncount = args[0].length;
				for(i = 0; i < desktop->regioncount; i++)
					((int*)desktop->regions->data)[i] = args[0].elements[i].integer;
				ok = zxrequest(win, op);
			}
		}else if(action == nil){
			if(op == ZX_DesktopLaunch)
				win->input.button = args[0].integer;
			ok = zxrequest(win, op);
			if(op == ZX_DesktopTimezone)
				count = ok ? win->input.key : 0;
		}else{
			if(op == ZX_DesktopWindowAction){
				win->input.button = args[0].integer;
				win->input.x = args[2].integer;
				win->input.y = args[3].integer;
				win->input.width = args[4].integer;
				win->input.height = args[5].integer;
			}else
				win->input.button = args[1].integer;
			ok = zxtextrequest(win, op, action->data, action->length);
		}
	}
	poperror();
	release();
	if(op == ZX_DesktopCapture || op == ZX_DesktopTimezone)
		return zxs32(result, count);
	zxbool(result, ok);
	return 1;
}

static int
zxtaskterminate(ZxCommand *command, int pid)
{
	int i;

	Prog *self = up->iprog;

#ifdef __linux__
	if(!command->hosted)
		return pid <= 0 ? -1 : zxnativeterminate(command, pid);
#endif
	if(pid <= 0 || (self != nil && self->pid == pid))
		return -1;
	for(i = 0; i < command->ntask; i++)
		if(command->tasks[i].pid == pid)
			return progdevkill(pid);
	return -1;
}

static int
zxtasks(void *context, const char *module, const char *function,
	const HostValue *args, int n, HostValue *result)
{
	ZxCommand *command = context;
	const ZxTask *row;
	int index, i;

	USED(module);
	if(strcmp(function, "Capture") == 0)
		return n == 0 && zxs32(result, zxtaskcapture(command));
	if(strcmp(function, "SampleNanos") == 0){
		if(n != 0)
			return 0;
		result->kind = HOST_INTEGER;
		result->type = "s64";
		result->integer = command->tasksvalid ? command->tasksample : -1;
		return 1;
	}
	if(n < 1 || !zxisindex(args))
		return 0;
	index = args[0].integer;
	if(!command->tasksvalid || index < 0)
		return zxs32(result, -1);
	if(strcmp(function, "Terminate") == 0)
		return n == 1 && zxs32(result, zxtaskterminate(command, index));
	if(strcmp(function, "PoolAt") == 0){
		if(n != 2 || index >= nelem(command->pools) || !zxtaskslice(args+1, "[]s64", 3))
			return zxs32(result, -1);
		for(i = 0; i < 3; i++)
			args[1].elements[i].integer = command->pools[index][i];
		return zxs32(result, 0);
	}
	if(n != 4 || index >= command->ntask || !zxtaskslice(args+1, "[]s64", 4) ||
	   !zxtaskslice(args+2, "[]u8", ZxTaskNameBytes) || !zxtaskslice(args+3, "[]u8", ZxTaskNameBytes))
		return zxs32(result, -1);
	row = &command->tasks[index];
	args[1].elements[0].integer = row->pid;
	args[1].elements[1].integer = row->group;
	args[1].elements[2].integer = row->state;
	args[1].elements[3].integer = row->kib;
	if(args[1].length >= 6){
		args[1].elements[4].integer = row->cpunanos;
		/* newprog never recycles a PID within an emulator instance. */
		args[1].elements[5].integer = row->pid;
	}
	if(args[1].length >= 7)
		args[1].elements[6].integer = command->taskskew;
	zxtaskname(args+2, row->module);
	zxtaskname(args+3, row->user);
	return zxs32(result, 0);
}

/* Package builds prefix the module leaf with p and 16 hexadecimal digits. */
static int
zxmodule(const char *actual, const char *leaf)
{
	int i;

	if(strcmp(actual, leaf) == 0)
		return 1;
	if(actual[0] != 'p')
		return 0;
	for(i = 1; i <= 16; i++)
		if(actual[i] == 0 || strchr("0123456789abcdef", actual[i]) == nil)
			return 0;
	return actual[17] == '_' && strcmp(actual + 18, leaf) == 0;
}

static int
zximagepoll(ZxSurface *surface)
{
	ZX_Window *win = surface->win;
	int i, cancelled = 0;

	if(win == H || !surface->opened)
		return 1;
	acquire();
	if(waserror()){
		release();
		return 0;
	}
	for(i = 0; i < 16; i++){
		win->wait = 0;
		if(!zxrequest(win, ZX_Event) || win->input.kind == ZX_Closed ||
		   (win->input.kind == ZX_Key && win->input.key == 256)){
			cancelled = 1;
			break;
		}
		if(win->input.kind == ZX_Idle)
			break;
		if(win->input.kind == ZX_Resize){
			surface->pendingresize = 1;
			surface->resizewidth = win->input.width;
			surface->resizeheight = win->input.height;
		}
	}
	poperror();
	release();
	return !cancelled;
}

static int
zximage(void *context, const char *module, const char *function,
	const HostValue *args, int n, HostValue *result)
{
	ZxSurface *surface = context;
	vlong now = zxmonotonicnanos();
	int status = -2;

	USED(module);
	if(strcmp(function, "Begin") == 0){
		if(n != 1 || args[0].kind != HOST_INTEGER || args[0].type == nil ||
		   strcmp(args[0].type, "s64") != 0)
			return 0;
		if(!surface->imageactive && surface->imagepermit && args[0].integer > 0 && args[0].integer <= ZxImageBytes && now >= 0){
			surface->imageactive = 1;
			surface->imagepermit = 0;
			surface->imagecancelled = 0;
			surface->imagework = 0;
			surface->imagelimit = (vlong)ZxImagePixels*64 + args[0].integer*4;
			surface->imagestart = surface->imagepoll = now;
			status = 1;
		}
	}else if(strcmp(function, "End") == 0 || strcmp(function, "Cancel") == 0){
		if(n != 0)
			return 0;
		surface->imageactive = 0;
		surface->imagecancelled = strcmp(function, "Cancel") == 0;
		status = 1;
	}else{
		if(n != 1 || args[0].kind != HOST_INTEGER || args[0].type == nil ||
		   strcmp(args[0].type, "s64") != 0)
			return 0;
		if(surface->imagecancelled)
			status = 0;
		else if(surface->imageactive){
			if(args[0].integer <= surface->imagework ||
			   args[0].integer - surface->imagework > ZxImageWorkChunk ||
			   args[0].integer > surface->imagelimit || now < surface->imagestart ||
			   now - surface->imagestart > (vlong)ZxImageMillis*1000000){
				surface->imageactive = 0;
				status = -1;
			}else{
				surface->imagework = args[0].integer;
				if(now-surface->imagepoll >= 16000000){
					surface->imagepoll = now;
					if(!zximagepoll(surface)){
						surface->imageactive = 0;
						surface->imagecancelled = 1;
					}
				}
				status = surface->imagecancelled ? 0 : BundleHostRenewSteps();
			}
		}
	}
	return zxs32(result, status);
}

static size_t
zxbindings(Bundle *bundle, ZxSurface *surface, ZxCommand *command, HostBinding *bindings)
{
	static const char *names[] = {"Open", "Event", "Present", "Close", "SetTasked", "SetTitle",
		"PresentOpaqueRows", "PresentOpaqueStrip", "PresentRGBStrip", "PointerMillis"};
	static const char *io[] = {"Open", "Create", "Read", "Write", "Seek", "Stat", "Close", "Error",
		"StatPacked", "FstatPacked", "WstatPacked", "FdPath", "CreateNew", "Remove", "Cwd", "Home",
		"Sync", "RenameSameDir"};
	static const char *desktop[] = {"BindDesktop", "Capture", "LauncherAt", "WindowAt", "Launch", "WindowAction",
		"DesktopAction", "UnixSeconds", "TimezoneOffsetSeconds", "SetChromeRegions"};
	BundleCapabilityAbi abi;
	size_t i, count = 0;
	int j;

	for(i = 0; i < BundleCapabilityCount(bundle); i++){
		if(!BundleCapabilityAbiAt(bundle, i, &abi))
			continue;
		if(zxmodule(abi.module, "taijios_stdin")){
			if(strcmp(abi.function, "Read") == 0 || (surface->win != H && strcmp(abi.function, "Poll") == 0))
				bindings[count++] = (HostBinding){abi.module, abi.function, zxstdin, surface};
#ifdef __linux__
			else if(command->window != nil && strcmp(abi.function, "Poll") == 0)
				bindings[count++] = (HostBinding){abi.module, abi.function, zxnativestdin, command};
#endif
			continue;
		}
		if(zxmodule(abi.module, "taijios_files") && strcmp(abi.function, "ReadAt") == 0){
			bindings[count++] = (HostBinding){abi.module, abi.function, zxfilereadat, nil};
			continue;
		}
		if(surface->win != H && zxmodule(abi.module, "taijios_draw") && strcmp(abi.function, "SampleGuestPointer") == 0){
			bindings[count++] = (HostBinding){abi.module, abi.function, zxdraw, surface};
			continue;
		}
		if(zxmodule(abi.module, "taijios_image")){
			if(strcmp(abi.function, "Begin") == 0 || strcmp(abi.function, "Step") == 0 ||
			   strcmp(abi.function, "End") == 0 || strcmp(abi.function, "Cancel") == 0)
				bindings[count++] = (HostBinding){abi.module, abi.function, zximage, surface};
			continue;
		}
		if((command->hosted || !usesdis()) && zxmodule(abi.module, "taijios_tasks")){
			if(strcmp(abi.function, "Capture") == 0 || strcmp(abi.function, "TaskAt") == 0 ||
			   strcmp(abi.function, "PoolAt") == 0 || strcmp(abi.function, "Terminate") == 0 ||
		   strcmp(abi.function, "SampleNanos") == 0)
				bindings[count++] = (HostBinding){abi.module, abi.function, zxtasks, command};
			continue;
		}
		if((zxmodule(abi.module, "taijios_clock") &&
		   (strcmp(abi.function, "MonotonicMillis") == 0 || strcmp(abi.function, "UnixMillis") == 0)) ||
		   (zxmodule(abi.module, "clock") && strcmp(abi.function, "ClockMillisecondsHost") == 0)){
			bindings[count++] = (HostBinding){abi.module, abi.function, zxclock, nil};
			continue;
		}
		if(zxmodule(abi.module, "taijios_args")){
			if(strcmp(abi.function, "Count") == 0 || strcmp(abi.function, "At") == 0 ||
			   strcmp(abi.function, "SetFailure") == 0)
				bindings[count++] = (HostBinding){abi.module, abi.function, zxargs, command};
			continue;
		}
#ifdef __linux__
		if(!usesdis() && zxmodule(abi.module, "taijios_process")){
			if(strcmp(abi.function, "Run") == 0 || strcmp(abi.function, "Start") == 0 ||
			   strcmp(abi.function, "Poll") == 0 || strcmp(abi.function, "Wait") == 0 ||
			   strcmp(abi.function, "Kill") == 0)
				bindings[count++] = (HostBinding){abi.module, abi.function, zxprocess, command};
			continue;
		}
		if(!usesdis() && command->depth == 0 && zxmodule(abi.module, "taijios_native_wm")){
			if(strcmp(abi.function, "StartWindow") == 0 || strcmp(abi.function, "StartDesktop") == 0 ||
			   strcmp(abi.function, "WaitActivity") == 0 || strcmp(abi.function, "LaunchWindow") == 0 ||
			   strcmp(abi.function, "Request") == 0 || strcmp(abi.function, "Text") == 0 ||
			   strcmp(abi.function, "Snapshot") == 0 || strcmp(abi.function, "ChromeRegions") == 0 ||
			   strcmp(abi.function, "Payload") == 0 || strcmp(abi.function, "ApplyCursor") == 0 ||
			   strcmp(abi.function, "Reply") == 0 || strcmp(abi.function, "ReplySample") == 0 ||
			   strcmp(abi.function, "Disconnect") == 0 ||
			   strcmp(abi.function, "Dispatch") == 0)
				bindings[count++] = (HostBinding){abi.module, abi.function, zxnativemanager, command};
			continue;
		}
		if(zxwindowdesktop(command->window) && zxmodule(abi.module, "taijios_desktop")){
			for(j = 0; j < nelem(desktop); j++)
				if(strcmp(abi.function, desktop[j]) == 0){
					bindings[count++] = (HostBinding){abi.module, abi.function, zxnativeshelldesktop, command->window};
					break;
				}
			continue;
		}
		if(command->window != nil && zxmodule(abi.module, "taijios_wm")){
			if(strcmp(abi.function, "Launch") == 0)
				bindings[count++] = (HostBinding){abi.module, abi.function, zxnativelaunch, command->window};
			else if(strcmp(abi.function, "Resize") == 0 || strcmp(abi.function, "SetCursor") == 0)
				bindings[count++] = (HostBinding){abi.module, abi.function, zxnativetools, command->window};
			continue;
		}
		if(command->window != nil && zxmodule(abi.module, "taijios_draw") && strcmp(abi.function, "SampleGuestPointer") == 0){
			bindings[count++] = (HostBinding){abi.module, abi.function, zxnativesample, command->window};
			continue;
		}
		if(command->window != nil && zxmodule(abi.module, "zx_surface")){
			for(j = 0; j < nelem(names); j++)
				if(strcmp(abi.function, names[j]) == 0){
					bindings[count++] = (HostBinding){abi.module, abi.function, zxnativesurface, command->window};
					break;
				}
			continue;
		}
#endif
		if(zxmodule(abi.module, "taijios_io")){
			for(j = 0; j < nelem(io); j++)
				if(strcmp(abi.function, io[j]) == 0){
					bindings[count++] = (HostBinding){abi.module, abi.function, zxio, command};
					break;
				}
			continue;
		}
		if(surface->win != H && surface->win->panel != H && zxmodule(abi.module, "taijios_panel")){
			if(strcmp(abi.function, "Snapshot") == 0 || strcmp(abi.function, "Row") == 0 ||
			   strcmp(abi.function, "Popup") == 0 || strcmp(abi.function, "Choose") == 0 ||
			   strcmp(abi.function, "Paint") == 0 || strcmp(abi.function, "Flush") == 0)
				bindings[count++] = (HostBinding){abi.module, abi.function, zxpanel, surface};
			continue;
		}
		if(surface->win != H && surface->win->desktop != H && zxmodule(abi.module, "taijios_desktop")){
			for(j = 0; j < nelem(desktop); j++)
				if(strcmp(abi.function, desktop[j]) == 0){
					bindings[count++] = (HostBinding){abi.module, abi.function, zxdesktop, surface};
					break;
				}
			continue;
		}
		if(surface->win != H && zxmodule(abi.module, "taijios_wm")){
			if(strcmp(abi.function, "Launch") == 0)
				bindings[count++] = (HostBinding){abi.module, abi.function, zxwmlaunch, surface};
			else if(strcmp(abi.function, "Resize") == 0 || strcmp(abi.function, "SetCursor") == 0)
				bindings[count++] = (HostBinding){abi.module, abi.function, zxwmwindow, surface};
			continue;
		}
		if(surface->win == H || !zxmodule(abi.module, "zx_surface"))
			continue;
		for(j = 0; j < nelem(names); j++)
			if(strcmp(abi.function, names[j]) == 0){
				bindings[count++] = (HostBinding){abi.module, abi.function, zxsurface, surface};
				if(strcmp(abi.function, "SetTasked") == 0)
					surface->win->hide = 1;
				break;
			}
	}
	return count;
}

#if defined(__linux__) && defined(__i386__)
static int
zxfpbegin(fenv_t *saved)
{
	unsigned short control;

	if(feholdexcept(saved) != 0)
		return 0;
	if(fesetround(FE_TONEAREST) != 0){
		fesetenv(saved);
		return 0;
	}
	/* The Dis worker can enter with a different x87 precision setting. */
	__asm__ volatile("fnstcw %0" : "=m"(control));
	control = (control & ~0x0300) | 0x0200;
	__asm__ volatile("fldcw %0" : : "m"(control));
	return 1;
}
#endif

/* Pure shell helpers share one engine instance per bundle. Calls run while
 * the interpreter is acquired and never enter the draw, channel or file APIs.
 * Bundle loading alone releases the interpreter because it reads guest files.
 */
typedef struct ZxWmPolicy ZxWmPolicy;
struct ZxWmPolicy {
	const char *path;
	Bundle *bundle;
	BundleInstance *engine;
	const int *request;
	int *reply;
	size_t nrequest, nreply;
	int opening;
};

static ZxWmPolicy zxwmpolicies[] = {
	{.path = "/dis/lib/window_chrome.zx"},
	{.path = "/dis/lib/winplace.zx"},
	{.path = "/dis/lib/wm_policy.zx"},
};

static int
zxwmbuffer(void *context, const char *module, const char *function,
	const HostValue *args, int n, HostValue *result)
{
	ZxWmPolicy *policy = context;
	const HostValue *slice;
	size_t offset, len, i, capacity;
	int input;

	USED(module);
	if(n != 2 || !zxisindex(args) || args[0].integer < 0 ||
	   args[1].kind != HOST_SLICE || args[1].type == nil ||
	   strcmp(args[1].type, "[]s32") != 0)
		return 0;
	slice = args + 1;
	len = slice->length;
	if(len != 0 && slice->elements == nil)
		return 0;
	input = strcmp(function, "Read") == 0;
	offset = args[0].integer;
	capacity = input ? policy->nrequest : policy->nreply;
	if(offset > capacity || len > capacity - offset){
		zxbool(result, 0);
		return 1;
	}
	for(i = 0; i < len; i++){
		if(input)
			slice->elements[i].integer = policy->request[offset+i];
		else
			policy->reply[offset+i] = slice->elements[i].integer;
	}
	zxbool(result, 1);
	return 1;
}

static int
zxwmpolicyopen(ZxWmPolicy *policy)
{
	BundleInstanceOptions options = {.backend = BUNDLE_BACKEND_ENGINE, .max_steps = ZxSteps};
	BundleCapabilityAbi abi;
	HostBinding bindings[2];
	Bundle *bundle;
	char err[ERRMAX];
	size_t count, i;

	if(policy->engine != nil)
		return 1;
	if(policy->opening)
		return 0;
	policy->opening = 1;
	release();
	bundle = zxopen(policy->path, err);
	acquire();
	policy->opening = 0;
	if(bundle == nil)
		return 0;
	count = BundleCapabilityCount(bundle);
	if(count > nelem(bindings))
		goto Fail;
	for(i = 0; i < count; i++){
		if(!BundleCapabilityAbiAt(bundle, i, &abi) ||
		   !zxmodule(abi.module, "taijios_wm_call") ||
		   (strcmp(abi.function, "Read") != 0 && strcmp(abi.function, "Reply") != 0))
			goto Fail;
		bindings[i] = (HostBinding){abi.module, abi.function, zxwmbuffer, policy};
	}
	policy->engine = BundleInstantiateWithOptions(bundle, bindings, count, &options);
	if(policy->engine == nil)
		goto Fail;
	policy->bundle = bundle;
	return 1;
Fail:
	BundleClose(bundle);
	return 0;
}

static int
zxwmpolicycall(int service, const int *request, size_t nrequest, int *reply, size_t nreply)
{
	ZxWmPolicy *policy;
	long long value;
	int has_result, ran;
#if defined(__linux__) && defined(__i386__)
	fenv_t saved;
#endif

	if(service < 0 || service >= nelem(zxwmpolicies))
		return 0;
	policy = zxwmpolicies + service;
	if(!zxwmpolicyopen(policy))
		return 0;
#if defined(__linux__) && defined(__i386__)
	if(!zxfpbegin(&saved))
		return 0;
#endif
	policy->request = request;
	policy->nrequest = nrequest;
	policy->reply = reply;
	policy->nreply = nreply;
	ran = BundleInstanceRun(policy->engine, &value, &has_result);
	policy->request = nil;
	policy->nrequest = 0;
	policy->reply = nil;
	policy->nreply = 0;
#if defined(__linux__) && defined(__i386__)
	fesetenv(&saved);
#endif
	return ran && has_result && value == 0;
}

static int
zxwmchrome(int *request, size_t nrequest, int *reply, size_t nreply)
{
	if(nrequest != 15)
		return 0;
	request[7] = (int)osmillisec();
	return zxwmpolicycall(0, request, nrequest, reply, nreply);
}

void
ZX_wmcall(void *fp)
{
	F_ZX_wmcall *f = fp;
	Array *request = f->request, *reply = f->reply;

	*f->ret = 0;
	if(f->service != ZX_PlacePolicy && f->service != ZX_WindowPolicy)
		return;
	if(request != H && reply != H)
		*f->ret = zxwmpolicycall(f->service, (int*)request->data, request->len,
		    (int*)reply->data, reply->len);
}

static void
zxrunner(ZxCommand *command, Proc *runner)
{
	lock(&command->runlock);
	command->runner = runner;
	unlock(&command->runlock);
}

static ZxResult
zxexecute(const char *path, ZxSurface *surface, ZxCommand *command)
{
	static const char *const roots[] = {"/dis/lib"};
	HostBinding *bindings;
	size_t count;
	int i, ran;
	ZxRunStatus status = ZX_RUN_ERROR;
	ZxResult result = {0, -1, ""};
	Bundle *bundle;
	ZxModuleLoader *loader;
	ZxModuleProgram *program;
	const char *problem;
	ZxModuleLoaderConfig config = {
		.roots = roots,
		.root_count = nelem(roots),
		.options = {.backend = BUNDLE_BACKEND_ENGINE, .max_steps = ZxSteps},
		.resolve = zxread,
		.resolve_context = result.problem,
		.write = zxwrite,
	};

	command->surface = surface;
	zxrunner(command, up);
	bundle = zxopen(path, result.problem);
	if(bundle != nil){
		count = BundleCapabilityCount(bundle);
		bindings = nil;
		program = nil;
		ran = 0;
		loader = ZxModuleLoaderOpenConfigured(&config);
		if(count != 0 && count <= SIZE_MAX / sizeof(*bindings))
			bindings = malloc(count * sizeof(*bindings));
		if(loader != nil && (count == 0 || bindings != nil)){
			int ready = 1;
#if defined(__linux__) && defined(__i386__)
			fenv_t saved;
#endif
			count = zxbindings(bundle, surface, command, bindings);
#if defined(__linux__) && defined(__i386__)
			ready = zxfpbegin(&saved);
#endif
			if(ready){
				program = ZxModuleProgramOpenControlled(loader, bundle, bindings, count,
				    command->control, &status);
				if(program != nil){
					/* Present consumes the pixels within the host call. */
					for(size_t i = 0; i < count; i++){
						if(bindings[i].call != zxsurface
#ifdef __linux__
						   && bindings[i].call != zxnativesurface
#endif
						  )
							continue;
						if(strcmp(bindings[i].function, "Present") == 0)
							ZxModuleProgramBorrowHostString(program, bindings[i].module,
								    bindings[i].function, 2);
						else if(strcmp(bindings[i].function, "PresentOpaqueRows") == 0 ||
						    strcmp(bindings[i].function, "PresentOpaqueStrip") == 0)
							ZxModuleProgramBorrowHostString(program, bindings[i].module,
							    bindings[i].function, 3);
						else if(strcmp(bindings[i].function, "PresentRGBStrip") == 0)
							ZxModuleProgramBorrowHostSlice(program, bindings[i].module,
							    bindings[i].function, 3);
					}
					status = ZxModuleProgramRunControlled(program, &result.value,
					    &result.status, command->control);
					ran = status == ZX_RUN_OK;
				}
#if defined(__linux__) && defined(__i386__)
				fesetenv(&saved);
#endif
			}else
				strecpy(result.problem, result.problem+sizeof(result.problem),
					"cannot initialize ZX floating-point environment");
		}
		if(!ran){
			problem = loader == nil ? nil : ZxModuleLoaderError(loader);
			if(problem != nil && problem[0] != '\0')
				snprint(result.problem, sizeof(result.problem), "%s", problem);
			else if(result.problem[0] == '\0')
				strecpy(result.problem, result.problem+sizeof(result.problem),
					program == nil ? "cannot initialize ZX program" : "ZX execution failed");
			result.status = -1;
		}else if(result.status > 0 && result.value != 0)
			strecpy(result.problem, result.problem+sizeof(result.problem), command->failure);
		else
			result.problem[0] = '\0';
		if(program != nil)
			ZxModuleProgramClose(program);
		if(loader != nil)
			ZxModuleLoaderClose(loader);
		free(bindings);
		BundleClose(bundle);
	}
	/* After this no kill can interrupt the kproc, so clear any interrupt
	 * that arrived while the guest was not blocked. */
	zxrunner(command, nil);
	if(command->control != nil && ZxRunControlRequested(command->control)){
		notkilled();
		if(status == ZX_RUN_CANCELLED || result.status < 0){
			result = (ZxResult){0, -1, ""};
			strecpy(result.problem, result.problem+sizeof(result.problem), "killed");
		}
	}
	for(i = 0; i < command->nfd; i++)
		if(command->fd[i] >= 0)
			kclose(command->fd[i]);
	free(command->fd);
	free(command->fdpath);
	free(command->tasks);
#ifdef __linux__
	zxstdinclose(command);
	zxprocessforget(command);
#endif
	return result;
}

static ZxResult
zxrun(String *s, List *args, ZX_Window *win)
{
	ZxSurface surface = {.win = win, .pointermillis = -1};
	ZxCommand command = {.hosted = 1};
	ZxResult result;
	char *path;

	path = strdup(string2c(s));
	if(path == nil)
		error("out of memory copying ZX path");
	if(!zxcopyargs(&command, args)){
		free(path);
		zxfreeargs(&command);
		error("out of memory copying ZX arguments");
	}
	release();
	result = zxexecute(path, &surface, &command);
	free(path);
	zxfreeargs(&command);
	acquire();
	return result;
}

void
ZX_run(void *fp)
{
	F_ZX_run *f = fp;
	ZxResult result = zxrun(f->path, H, H);
	f->ret->t0 = result.value;
	f->ret->t1 = result.status;
	retstr(result.problem, &f->ret->t2);
}

void
ZX_runargs(void *fp)
{
	F_ZX_runargs *f = fp;
	ZxResult result = zxrun(f->path, f->args, H);

	f->ret->t0 = result.value;
	f->ret->t1 = result.status;
	retstr(result.problem, &f->ret->t2);
}

void
ZX_runwindow(void *fp)
{
	F_ZX_runwindow *f = fp;
	ZxResult result;

	if(f->win == H || f->win->request == H || f->win->reply == H)
		error("invalid ZX window channels");
	result = zxrun(f->path, H, f->win);
	f->ret->t0 = result.value;
	f->ret->t1 = result.status;
	retstr(result.problem, &f->ret->t2);
}

void
ZX_runwindowargs(void *fp)
{
	F_ZX_runwindowargs *f = fp;
	ZxResult result;
	if(f->win == H || f->win->request == H || f->win->reply == H)
		error("invalid ZX window channels");
	result = zxrun(f->path, f->args, f->win);
	f->ret->t0 = result.value;
	f->ret->t1 = result.status;
	retstr(result.problem, &f->ret->t2);
}

#endif

#ifdef __linux__
#ifndef TAIJI_ZX
void
zxnotifyactivity(void)
{
}
#endif

int
zxbootable(const char *path)
{
#ifdef TAIJI_ZX
	size_t length = strlen(path);
	return path[0] == '/' && length >= 4 && strcmp(path+length-3, ".zx") == 0;
#else
	USED(path);
	return 0;
#endif
}

int
zxboot(const char *path, int argc, char **argv)
{
#ifdef TAIJI_ZX
	extern int vflag;
	ZxSurface surface = {.win = H, .pointermillis = -1};
	ZxCommand command = {.argc = argc};
	ZxResult result;
	int i;

	if(vflag)
		print("Initial ZX: \"%s\"\n", path);
	if(argc != 0){
		command.args = calloc(argc, sizeof(*command.args));
		if(command.args == nil){
			fprint(2, "emu: out of memory copying ZX arguments\n");
			return 1;
		}
		for(i = 0; i < argc; i++)
			command.args[i] = (HostValue){.kind = HOST_STRING, .type = "string",
				.data = (uchar*)argv[i], .length = strlen(argv[i])};
	}
	kbind("#e", "/env", MREPL|MCREATE);
	result = zxexecute(path, &surface, &command);
	free(command.args);
	if(result.problem[0] != '\0')
		fprint(2, "emu: %s: %s\n", path, result.problem);
	if(result.status < 0)
		return 1;
	if(result.status == 0 || result.value == 0)
		return 0;
	return result.value > 0 && result.value <= 255 ? result.value : 1;
#else
	USED(path);
	USED(argc);
	USED(argv);
	return 1;
#endif
}
#endif

void
zxmodinit(void)
{
#ifdef TAIJI_ZX
	builtinmod("$ZX", ZXmodtab, ZXmodlen);
	tkwmchromecall = zxwmchrome;
#endif
}
