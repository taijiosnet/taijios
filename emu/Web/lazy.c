/*
 * Guest files fetched on first open.
 *
 * The page writes /lazy.list before the emulator starts: a base URL line,
 * then "SIZE PATH" lines for files the root bundle leaves on the server as
 * BASE/PATH.gz. Each gets an empty placeholder under the root so it lists
 * and stats with its real size; the first open downloads it with a
 * synchronous request on the opening thread (always a Web Worker),
 * inflates it and fills the placeholder.
 */
#include	"dat.h"
#include	"fns.h"

#include	<pthread.h>
#include	<zlib.h>
#include	<emscripten.h>

typedef struct Lazy Lazy;
struct Lazy
{
	char	*path;		/* host path under the root */
	char	*url;
	vlong	size;
	int	fetched;
};

static Lazy *lazy;
static int nlazy;
static pthread_mutex_t lazylock = PTHREAD_MUTEX_INITIALIZER;

EM_JS(int, webfetchsync, (const char *url, char **data, int *len), {
	try {
		var request = new XMLHttpRequest();
		request.open('GET', UTF8ToString(url), false);
		request.responseType = 'arraybuffer';
		request.send(null);
		if (request.status !== 200 || !request.response)
			return -1;
		var bytes = new Uint8Array(request.response);
		var at = _malloc(bytes.length + 1);
		if (!at)
			return -1;
		new Uint8Array(wasmMemory.buffer).set(bytes, at);
		var words = new Int32Array(wasmMemory.buffer);
		words[data >> 2] = at;
		words[len >> 2] = bytes.length;
		return 0;
	} catch (error) {
		return -1;
	}
});

static void
makeparents(char *path)
{
	char *p;

	for(p = strchr(path+1, '/'); p != nil; p = strchr(p+1, '/')){
		*p = 0;
		mkdir(path, 0777);
		*p = '/';
	}
}

static char*
readlist(int *n)
{
	char *buf, *p;
	int fd, r, have, cap;

	fd = open("/lazy.list", O_RDONLY);
	if(fd < 0)
		return nil;
	have = 0;
	cap = 8192;
	buf = malloc(cap+1);
	while(buf != nil && (r = read(fd, buf+have, cap-have)) > 0){
		have += r;
		if(have == cap){
			cap *= 2;
			p = realloc(buf, cap+1);
			if(p == nil){
				free(buf);
				buf = nil;
			}else
				buf = p;
		}
	}
	close(fd);
	if(buf != nil)
		buf[have] = 0;
	*n = have;
	return buf;
}

void
weblazyinit(char *root)
{
	char *list, *line, *next, *base, *p;
	long long size;
	int fd, n;
	Lazy *l;

	list = readlist(&n);
	if(list == nil)
		return;
	base = nil;
	for(line = list; line != nil && *line != 0; line = next){
		next = strchr(line, '\n');
		if(next != nil)
			*next++ = 0;
		if(base == nil){
			base = line;
			continue;
		}
		size = strtoll(line, &p, 10);
		if(p == line || *p != ' ' || size < 0)
			continue;
		p++;
		l = realloc(lazy, (nlazy+1)*sizeof *lazy);
		if(l == nil)
			break;
		lazy = l;
		l = &lazy[nlazy];
		l->path = smprint("%s/%s", root, p);
		l->url = smprint("%s/%s.gz", base, p);
		l->size = size;
		l->fetched = 0;
		if(l->path == nil || l->url == nil)
			break;
		makeparents(l->path);
		fd = open(l->path, O_CREAT|O_WRONLY|O_TRUNC, 0755);
		if(fd < 0)
			continue;
		close(fd);
		nlazy++;
	}
	free(list);
}

static Lazy*
pending(const char *path)
{
	int i;

	for(i = 0; i < nlazy; i++)
		if(!lazy[i].fetched && strcmp(lazy[i].path, path) == 0)
			return &lazy[i];
	return nil;
}

/* The recorded size of a file not yet fetched, or -1. */
vlong
weblazysize(const char *path)
{
	Lazy *l;
	vlong size;

	if(nlazy == 0)
		return -1;
	pthread_mutex_lock(&lazylock);
	l = pending(path);
	size = l != nil ? l->size : -1;
	pthread_mutex_unlock(&lazylock);
	return size;
}

static int
inflatefile(Lazy *l, uchar *packed, int npacked)
{
	z_stream z;
	uchar *out;
	int fd, ok;
	vlong n, w;

	out = malloc(l->size > 0 ? l->size : 1);
	if(out == nil)
		return -1;
	memset(&z, 0, sizeof z);
	if(inflateInit2(&z, 16+MAX_WBITS) != Z_OK){
		free(out);
		return -1;
	}
	z.next_in = packed;
	z.avail_in = npacked;
	z.next_out = out;
	z.avail_out = l->size;
	ok = inflate(&z, Z_FINISH) == Z_STREAM_END && z.total_out == l->size;
	inflateEnd(&z);
	fd = ok ? open(l->path, O_WRONLY|O_TRUNC) : -1;
	for(n = 0; fd >= 0 && n < l->size; n += w){
		w = write(fd, out+n, l->size-n);
		if(w <= 0){
			ok = 0;
			break;
		}
	}
	if(fd >= 0)
		close(fd);
	free(out);
	return ok && fd >= 0 ? 0 : -1;
}

/* Downloads PATH if it is still a placeholder; -1 when that fails. */
int
weblazyfetch(const char *path)
{
	Lazy *l;
	char *packed;
	int npacked, r;

	if(nlazy == 0)
		return 0;
	pthread_mutex_lock(&lazylock);
	l = pending(path);
	r = 0;
	if(l != nil){
		packed = nil;
		r = webfetchsync(l->url, &packed, &npacked);
		if(r == 0)
			r = inflatefile(l, (uchar*)packed, npacked);
		free(packed);
		if(r == 0)
			l->fetched = 1;
		else
			fprint(2, "emu: cannot fetch %s\n", l->url);
	}
	pthread_mutex_unlock(&lazylock);
	return r;
}
