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
#include "zxrunt.h"
#include "drawif.h"
#include "zxmod.h"

enum {
	ZxMaxImage = 32 * 1024 * 1024,
	ZxSteps = 16000000,
	ZxTitleBytes = 512,
	ZxGuestPathBytes = 1024,
	ZxLaunchArgBytes = 4096,
	ZxCursorSide = 32,
	ZxIoBytes = 8192,
	ZxInitialFiles = 32,
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

static ZxModuleResolveResult
zxread(void *context, const char *path, ZxModuleImage *image)
{
	char *err = context;
	uchar *bytes, *grown, extra;
	Dir *dir;
	int fd, length, capacity, initial;
	long count;

	err[0] = '\0';
	fd = kopen((char *)path, OREAD);
	if(fd < 0){
		kgerrstr(err, ERRMAX);
		if(strstr(err, "does not exist") != nil || strstr(err, "No such file") != nil)
			return ZX_MODULE_IMAGE_MISSING;
		return ZX_MODULE_IMAGE_ERROR;
	}
	initial = ZxIoBytes;
	dir = kdirfstat(fd);
	if(dir != nil){
		/* Leave room to read EOF without growing the buffer for a regular image. */
		if(dir->length > 0 && dir->length < ZxMaxImage && (dir->mode & DMDIR) == 0)
			initial = dir->length + 1;
		free(dir);
	}
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
	kclose(fd);
	if(count == 0){
		*image = (ZxModuleImage){bytes, length, zxfree};
		return ZX_MODULE_IMAGE_FOUND;
	}
	free(bytes);
	return ZX_MODULE_IMAGE_ERROR;
}

static Bundle*
zxopen(const char *path, char *err)
{
	Bundle *bundle;
	ZxModuleImage image;

	if(zxread(err, path, &image) != ZX_MODULE_IMAGE_FOUND)
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
	if(!zxrequest(win, ZX_Event))
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
zxuploadopaque(Image *image, const uchar *data, int width, int first, int height)
{
	enum { Chunk = 8192 / 3 };
	uchar packed[Chunk*3];
	const uchar *source;
	int maxpixels, x, y, i, columns, rows, count;

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
			source = data + (y*width + x)*4;
			for(i = 0; i < count; i++){
				packed[3*i] = source[4*i];
				packed[3*i+1] = source[4*i+1];
				packed[3*i+2] = source[4*i+2];
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
				ok = zxuploadopaque(image, pixels->data, win->width, 0, win->height);
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
zxpresentrows(ZxSurface *surface, const HostValue *args, int n)
{
	ZX_Window *win = surface->win;
	const HostValue *pixels;
	Image *image;
	int first, width, height, rows, stride, prepared, locked, ok;
	int next = surface->nextrow;

	surface->nextrow = 0;
	if(n != 4 || !zxsize(args) || args[2].kind != HOST_INTEGER ||
	   args[2].integer < 0 || args[2].integer >= args[1].integer)
		return 0;
	width = args[0].integer;
	height = args[1].integer;
	first = args[2].integer;
	if(first != 0 && (first != next || width != surface->framewidth || height != surface->frameheight))
		return 0;
	pixels = args + 3;
	stride = width*4;
	if(pixels->kind != HOST_STRING || pixels->data == nil || pixels->length == 0 ||
	   pixels->length > (size_t)(height-first)*stride || pixels->length % stride != 0 ||
	   !zxopaque(pixels->data, pixels->length))
		return 0;
	rows = pixels->length / stride;
	win->width = width;
	win->height = height;
	prepared = zxrequest(win, ZX_OpaqueBuffer);
	if(prepared == 2)
		ok = 1; /* Close is queued. */
	else if(prepared != 1 || (image = lookupimage(win->image)) == nil)
		return 0;
	else{
		locked = lockdisplay(image->display);
		ok = zxuploadopaque(image, pixels->data, width, first, rows);
		if(locked)
			unlockdisplay(image->display);
		if(ok && first+rows == height)
			ok = zxrequest(win, ZX_Present);
	}
	if(ok && first+rows < height){
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
	if(strcmp(function, "Open") == 0)
		ok = zxopenwindow(surface->win, args, n, result);
	else if(strcmp(function, "Event") == 0)
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
		zxbool(result, zxpresentrows(surface, args, n));
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
	if(width <= 0 || width > ZxCursorSide || width % 8 != 0 ||
	   height <= 0 || height > 2 * ZxCursorSide || height % 2 != 0 ||
	   x > 0 || x <= -width || y > 0 || y <= -(height/2) ||
	   args[4].data == nil || args[4].length != (size_t)(width/8*height))
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
	USED(function);
	USED(args);
	if(n != 0 || clock_gettime(CLOCK_MONOTONIC, &now) < 0)
		return 0;
	result->kind = HOST_INTEGER;
	result->type = "s64";
	result->integer = (int64_t)now.tv_sec * 1000 + now.tv_nsec / 1000000;
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

typedef struct ZxCommand ZxCommand;
struct ZxCommand {
	HostValue *args;
	int argc;
	int *fd;
	int nfd;
	char *fdpath;
	char err[ERRMAX];
	char failure[ERRMAX];
};

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
zxioopen(ZxCommand *command, const HostValue *args, int n, int create, HostValue *result)
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
	if(mode < 0 || mode >= nelem(modes))
		return zxioerror(command, result, "invalid open mode");
	slot = zxioslot(command);
	if(slot < 0)
		return zxioerror(command, result, "too many open ZX files");
	fd = create ? kcreate(path, modes[mode], (uint32_t)args[2].integer) : kopen(path, modes[mode]);
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
		return zxioopen(command, args, n, 0, result);
	if(strcmp(function, "Create") == 0)
		return zxioopen(command, args, n, 1, result);
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
		if(count > 0)
			BundleHostRenewSteps();
		for(i = 0; i < count; i++)
			buffer->elements[i].bits = bytes[i];
	}else{
		if(buffer->kind != HOST_STRING || (length != 0 && buffer->data == nil))
			return 0;
		count = length == 0 ? 0 : kwrite(fd, (void *)buffer->data, length);
	}
	return count < 0 ? zxioerror(command, result, nil) : zxs32(result, count);
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

static size_t
zxbindings(Bundle *bundle, ZxSurface *surface, ZxCommand *command, HostBinding *bindings)
{
	static const char *names[] = {"Open", "Event", "Present", "Close", "SetTasked", "SetTitle",
		"PresentOpaqueRows", "PointerMillis"};
	static const char *io[] = {"Open", "Create", "Read", "Write", "Seek", "Stat", "Close", "Error",
		"StatPacked", "FstatPacked", "WstatPacked", "FdPath"};
	BundleCapabilityAbi abi;
	size_t i, count = 0;
	int j;

	for(i = 0; i < BundleCapabilityCount(bundle); i++){
		if(!BundleCapabilityAbiAt(bundle, i, &abi))
			continue;
		if(zxmodule(abi.module, "taijios_stdin")){
			if(strcmp(abi.function, "Read") == 0 || (surface->win != H && strcmp(abi.function, "Poll") == 0))
				bindings[count++] = (HostBinding){abi.module, abi.function, zxstdin, surface};
			continue;
		}
		if(zxmodule(abi.module, "taijios_files") && strcmp(abi.function, "ReadAt") == 0){
			bindings[count++] = (HostBinding){abi.module, abi.function, zxfilereadat, nil};
			continue;
		}
		if(zxmodule(abi.module, "taijios_clock") && strcmp(abi.function, "MonotonicMillis") == 0){
			bindings[count++] = (HostBinding){abi.module, abi.function, zxclock, nil};
			continue;
		}
		if(zxmodule(abi.module, "taijios_args")){
			if(strcmp(abi.function, "Count") == 0 || strcmp(abi.function, "At") == 0 ||
			   strcmp(abi.function, "SetFailure") == 0)
				bindings[count++] = (HostBinding){abi.module, abi.function, zxargs, command};
			continue;
		}
		if(zxmodule(abi.module, "taijios_io")){
			for(j = 0; j < nelem(io); j++)
				if(strcmp(abi.function, io[j]) == 0){
					bindings[count++] = (HostBinding){abi.module, abi.function, zxio, command};
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

struct ZxResult {
	long long value;
	int status;
	char problem[ERRMAX];
};

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

static ZxResult
zxrun(String *s, List *args, ZX_Window *win)
{
	static const char *const roots[] = {"/dis/lib"};
	ZxSurface surface = {.pointermillis = -1};
	ZxCommand command = {0};
	HostBinding *bindings;
	size_t count;
	int i, ran;
	ZxResult result = {0, -1, ""};
	Bundle *bundle;
	ZxModuleLoader *loader;
	ZxModuleProgram *program;
	char *path;
	const char *problem;
	ZxModuleLoaderConfig config = {
		.roots = roots,
		.root_count = nelem(roots),
		.options = {.backend = BUNDLE_BACKEND_ENGINE, .max_steps = ZxSteps},
		.resolve = zxread,
		.resolve_context = result.problem,
		.write = zxwrite,
	};

	path = strdup(string2c(s));
	if(path == nil)
		error("out of memory copying ZX path");
	if(!zxcopyargs(&command, args)){
		free(path);
		zxfreeargs(&command);
		error("out of memory copying ZX arguments");
	}
	surface.win = win;
	release();
	bundle = zxopen(path, result.problem);
	free(path);
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
			count = zxbindings(bundle, &surface, &command, bindings);
#if defined(__linux__) && defined(__i386__)
			ready = zxfpbegin(&saved);
#endif
			if(ready){
				program = ZxModuleProgramOpen(loader, bundle, bindings, count);
				if(program != nil){
					/* Present consumes the pixels within the host call. */
					for(size_t i = 0; i < count; i++){
						if(bindings[i].call != zxsurface)
							continue;
						if(strcmp(bindings[i].function, "Present") == 0)
							ZxModuleProgramBorrowHostString(program, bindings[i].module,
								    bindings[i].function, 2);
						else if(strcmp(bindings[i].function, "PresentOpaqueRows") == 0)
							ZxModuleProgramBorrowHostString(program, bindings[i].module,
							    bindings[i].function, 3);
					}
					ran = ZxModuleProgramRun(program, &result.value, &result.status);
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
			strecpy(result.problem, result.problem+sizeof(result.problem), command.failure);
		else
			result.problem[0] = '\0';
		if(program != nil)
			ZxModuleProgramClose(program);
		if(loader != nil)
			ZxModuleLoaderClose(loader);
		free(bindings);
		BundleClose(bundle);
	}
	for(i = 0; i < command.nfd; i++)
		if(command.fd[i] >= 0)
			kclose(command.fd[i]);
	free(command.fd);
	free(command.fdpath);
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

void
zxmodinit(void)
{
#ifdef TAIJI_ZX
	builtinmod("$ZX", ZXmodtab, ZXmodlen);
#endif
}
