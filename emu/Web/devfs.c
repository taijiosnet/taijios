/*
 * The POSIX file device over WASMFS. Files listed in /lazy.list stay on the
 * server until first opened (lazy.c): stat reports their real size and
 * open fetches them first.
 */
#include	<sys/types.h>
#include	<sys/stat.h>
#include	<fcntl.h>
#include	<errno.h>
#include	<stdarg.h>

extern long long	weblazysize(const char*);
extern int	weblazyfetch(const char*);

static int
webstat(const char *path, struct stat *st)
{
	long long size;
	int r;

	r = (stat)(path, st);
	if(r == 0 && (size = weblazysize(path)) >= 0)
		st->st_size = size;
	return r;
}

static int
webopen(const char *path, int flags, ...)
{
	va_list arg;
	int mode;

	va_start(arg, flags);
	mode = (flags & O_CREAT) ? va_arg(arg, int) : 0;
	va_end(arg);
	if(weblazyfetch(path) < 0){
		errno = EIO;
		return -1;
	}
	return (open)(path, flags, mode);
}

#define	stat(path, st)	webstat(path, st)
#define	open(...)	webopen(__VA_ARGS__)

#include "devfs-posix.c"

/* WASMFS holds only regular files and directories: no block devices. */
static vlong
osdisksize(int fd)
{
	USED(fd);
	return 0;
}
