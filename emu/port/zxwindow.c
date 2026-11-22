#include "dat.h"
#include "fns.h"

#if defined(__linux__) && defined(TAIJI_ZX)
#include "interp.h"
#include "isa.h"
#include "ziran_host.h"
#include "zxrunt.h"
#include "zxwindow.h"
#include <pthread.h>
#include <time.h>

enum { NativeEvents = 64, NativeTitleBytes = 512 };

typedef struct ZxNativeEvent ZxNativeEvent;
struct ZxNativeEvent {
	int field[9]; /* kind, x, y, button, key, modifiers, width, height, text rune */
	vlong millis;
};

struct ZxNativeWindow {
	pthread_mutex_t lock;
	pthread_cond_t changed;
	ZxNativeRequest request;
	int closed, accepted;
	int opened, nextrow, width, height;
	ZxNativeEvent events[NativeEvents];
	uint in, out;
	HostField result[9];
	uchar text[UTFmax];
	vlong pointermillis;
};

ZxNativeWindow *
zxwindownew(void)
{
	ZxNativeWindow *window;
	pthread_condattr_t attr;
	int error;

	window = calloc(1, sizeof(*window));
	if(window == nil)
		return nil;
	window->pointermillis = -1;
	if(pthread_mutex_init(&window->lock, nil) != 0){
		free(window);
		return nil;
	}
	if(pthread_condattr_init(&attr) != 0){
		pthread_mutex_destroy(&window->lock);
		free(window);
		return nil;
	}
	error = pthread_condattr_setclock(&attr, CLOCK_MONOTONIC);
	if(error == 0)
		error = pthread_cond_init(&window->changed, &attr);
	pthread_condattr_destroy(&attr);
	if(error != 0){
		pthread_mutex_destroy(&window->lock);
		free(window);
		return nil;
	}
	return window;
}

void
zxwindowdisconnect(ZxNativeWindow *window)
{
	if(window == nil)
		return;
	pthread_mutex_lock(&window->lock);
	window->closed = 1;
	window->request = (ZxNativeRequest){0};
	window->accepted = 0;
	pthread_cond_broadcast(&window->changed);
	pthread_mutex_unlock(&window->lock);
}

void
zxwindowfree(ZxNativeWindow *window)
{
	if(window == nil)
		return;
	pthread_cond_destroy(&window->changed);
	pthread_mutex_destroy(&window->lock);
	free(window);
}

int
zxwindowrequest(ZxNativeWindow *window, ZxNativeRequest *request)
{
	int kind;

	if(window == nil)
		return 0;
	pthread_mutex_lock(&window->lock);
	kind = window->request.kind;
	if(request != nil)
		*request = window->request;
	pthread_mutex_unlock(&window->lock);
	return kind;
}

int
zxwindowreply(ZxNativeWindow *window, int accepted)
{
	int pending;

	if(window == nil)
		return 0;
	pthread_mutex_lock(&window->lock);
	pending = window->request.kind != 0;
	if(pending){
		window->accepted = accepted;
		window->request = (ZxNativeRequest){0};
		pthread_cond_signal(&window->changed);
	}
	pthread_mutex_unlock(&window->lock);
	return pending;
}

int
zxwindowinput(ZxNativeWindow *window, int *fields, vlong millis)
{
	ZxNativeEvent *event;
	int queued = 0;

	if(window == nil)
		return 0;
	pthread_mutex_lock(&window->lock);
	if(!window->closed){
		event = nil;
		if(fields[0] == ZX_Move && window->in != window->out &&
		   window->events[(window->in-1) % NativeEvents].field[0] == ZX_Move)
			event = &window->events[(window->in-1) % NativeEvents];
		else if(window->in - window->out < NativeEvents)
			event = &window->events[window->in++ % NativeEvents];
		if(event != nil){
			memmove(event->field, fields, sizeof(event->field));
			event->millis = millis;
			pthread_cond_signal(&window->changed);
			queued = 1;
		}
	}
	pthread_mutex_unlock(&window->lock);
	return queued;
}

/* The blocked app keeps the borrowed payload alive until the manager replies. */
static int
submit(ZxNativeWindow *window, ZxNativeRequest request)
{
	int accepted;

	pthread_mutex_lock(&window->lock);
	if(window->closed){
		pthread_mutex_unlock(&window->lock);
		return 0;
	}
	window->request = request;
	pthread_mutex_unlock(&window->lock);
	zxnotifyactivity();
	pthread_mutex_lock(&window->lock);
	while(window->request.kind != 0)
		pthread_cond_wait(&window->changed, &window->lock);
	accepted = window->accepted;
	pthread_mutex_unlock(&window->lock);
	return accepted;
}

static int
integer(const HostValue *value)
{
	return value->kind == HOST_INTEGER && value->integer >= INT32_MIN && value->integer <= INT32_MAX;
}

static int
surfaceevent(ZxNativeWindow *window, int wait, HostValue *result)
{
	static const char *names[] = {"kind", "x", "y", "button", "key", "modifiers", "width", "height", "text"};
	ZxNativeEvent event = {.millis = -1};
	struct timespec deadline;
	Rune rune;
	int i, status;

	if(wait > 0){
		if(clock_gettime(CLOCK_MONOTONIC, &deadline) != 0)
			return 0;
		deadline.tv_sec += wait / 1000;
		deadline.tv_nsec += (long)(wait % 1000) * 1000000;
		if(deadline.tv_nsec >= 1000000000){
			deadline.tv_sec++;
			deadline.tv_nsec -= 1000000000;
		}
	}
	pthread_mutex_lock(&window->lock);
	while(wait > 0 && !window->closed && window->in == window->out){
		status = pthread_cond_timedwait(&window->changed, &window->lock, &deadline);
		if(status != 0)
			break;
	}
	if(window->closed)
		event.field[0] = ZX_Closed;
	else if(window->in != window->out)
		event = window->events[window->out++ % NativeEvents];
	pthread_mutex_unlock(&window->lock);
	window->pointermillis = event.millis;
	if(event.field[0] != ZX_Closed && (wait > 0 || event.field[0] != ZX_Idle))
		BundleHostRenewSteps();
	for(i = 0; i < 8; i++)
		window->result[i] = (HostField){names[i], {.kind = HOST_INTEGER, .type = "s32", .integer = event.field[i]}};
	rune = event.field[8];
	window->result[8] = (HostField){names[8], {.kind = HOST_STRING, .type = "string", .data = window->text,
		.length = rune == 0 ? 0 : runetochar((char *)window->text, &rune)}};
	result->kind = HOST_RECORD;
	result->fields = window->result;
	result->field_count = nelem(window->result);
	return 1;
}

static int
dimensions(const HostValue *width, const HostValue *height)
{
	return integer(width) && integer(height) && width->integer > 0 && width->integer <= ZX_Maxside &&
		height->integer > 0 && height->integer <= ZX_Maxside && width->integer * height->integer <= ZX_Maxpixels;
}

static int
title(const HostValue *value)
{
	return value->kind == HOST_STRING && value->length <= NativeTitleBytes &&
		(value->length == 0 || (value->data != nil && memchr(value->data, 0, value->length) == nil));
}

static int
frame(ZxNativeWindow *window, const char *function, const HostValue *args, int n)
{
	ZxNativeRequest request = {.kind = ZxnFrame};
	const HostValue *pixels;
	uchar *rgba = nil;
	int i, pixel, ok, whole, packed, staged, stride, expected;
	uint color;

	whole = strcmp(function, "Present") == 0;
	packed = strcmp(function, "PresentRGBStrip") == 0;
	staged = strcmp(function, "PresentOpaqueRows") == 0;
	if(n != (whole ? 3 : 4) || !dimensions(args, args+1) || (!whole && !integer(args+2)))
		return 0;
	request.width = args[0].integer;
	request.height = args[1].integer;
	request.first = whole ? 0 : args[2].integer;
	if(request.first < 0 || request.first >= request.height)
		return 0;
	stride = request.width * (packed ? 1 : 4);
	pixels = args + n - 1;
	expected = (request.height - request.first) * stride;
	if(pixels->length == 0 || pixels->length > expected || pixels->length % stride != 0 ||
	   (whole && pixels->length != expected))
		return 0;
	if(staged && request.first != 0 && (request.first != window->nextrow ||
	   request.width != window->width || request.height != window->height))
		return 0;
	request.rows = pixels->length / stride;
	request.flag = staged ? ZxnStaged : 0;
	if(!staged || request.first + request.rows == request.height)
		request.flag |= ZxnPublish;
	if(packed){
		if(pixels->type == nil || strcmp(pixels->type, "[]u32") != 0 ||
		   !((pixels->kind == HOST_SLICE && pixels->elements != nil) ||
		     (pixels->kind == HOST_BORROWED_SLICE && pixels->data != nil)))
			return 0;
		rgba = malloc(pixels->length * 4);
		if(rgba == nil)
			return 0;
		for(i = 0; i < pixels->length; i++){
			if(pixels->kind == HOST_BORROWED_SLICE)
				memmove(&color, pixels->data + i*4, sizeof(color));
			else
				color = pixels->elements[i].bits;
			pixel = i*4;
			rgba[pixel] = color >> 16;
			rgba[pixel+1] = color >> 8;
			rgba[pixel+2] = color;
			rgba[pixel+3] = 255;
		}
		request.data = rgba;
		request.length = pixels->length * 4;
	}else{
		if(pixels->kind != HOST_STRING || pixels->data == nil)
			return 0;
		if(!whole)
			for(i = 3; i < pixels->length; i += 4)
				if(pixels->data[i] != 255)
					return 0;
		request.data = pixels->data;
		request.length = pixels->length;
	}
	window->nextrow = 0;
	ok = submit(window, request);
	free(rgba);
	if(ok && (request.flag & ZxnPublish) == 0){
		window->nextrow = request.first + request.rows;
		window->width = request.width;
		window->height = request.height;
	}
	return ok;
}

int
zxnativesurface(void *context, const char *module, const char *function,
	const HostValue *args, int n, HostValue *result)
{
	ZxNativeWindow *window = context;
	int ok;

	USED(module);
	if(strcmp(function, "Event") == 0)
		return n == 1 && integer(args) && surfaceevent(window, args[0].integer, result);
	if(strcmp(function, "PointerMillis") == 0){
		*result = (HostValue){.kind = HOST_INTEGER, .type = "s64", .integer = window->pointermillis};
		return n == 0;
	}
	if(strcmp(function, "Close") == 0){
		if(n != 0)
			return 0;
		if(window->opened)
			submit(window, (ZxNativeRequest){.kind = ZxnClose});
		window->opened = 0;
		window->nextrow = 0;
		result->kind = HOST_VOID;
		return 1;
	}
	if(strcmp(function, "Open") == 0){
		ok = !window->opened && n == 3 && title(args) && dimensions(args+1, args+2) &&
			submit(window, (ZxNativeRequest){.kind = ZxnOpen, .width = args[1].integer, .height = args[2].integer,
				.data = args[0].data, .length = args[0].length});
		if(ok)
			window->opened = 1;
	}else if(strcmp(function, "SetTitle") == 0){
		ok = window->opened && n == 1 && title(args) && submit(window,
			(ZxNativeRequest){.kind = ZxnTitle, .data = args[0].data, .length = args[0].length});
	}else if(strcmp(function, "SetTasked") == 0){
		ok = window->opened && n == 1 && integer(args) && submit(window,
			(ZxNativeRequest){.kind = ZxnTask, .flag = args[0].integer != 0});
	}else
		ok = window->opened && frame(window, function, args, n);
	*result = (HostValue){.kind = HOST_INTEGER, .type = "bool", .integer = ok};
	return 1;
}
#endif
