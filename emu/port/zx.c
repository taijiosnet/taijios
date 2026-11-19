#include "dat.h"
#include "fns.h"

#ifdef TAIJI_ZX
#include "interp.h"
#include "isa.h"
#include "kernel.h"
#include "ziran_host.h"
#include "zxrunt.h"
#include "zxmod.h"

enum {
	ZxMaxImage = 32 * 1024 * 1024,
	ZxSteps = 16000000,
};

static int
zxwrite(void *context, int fd, const void *data, size_t size)
{
	const uchar *bytes = data;
	long count;

	USED(context);
	while(size != 0){
		count = kwrite(fd, (void *)bytes, size > 8192 ? 8192 : size);
		if(count <= 0)
			return 0;
		bytes += count;
		size -= count;
	}
	return 1;
}

static Bundle*
zxopen(char *path, char *err)
{
	Bundle *bundle;
	uchar *bytes, *grown, extra;
	int fd, length, capacity;
	long count;

	fd = kopen(path, OREAD);
	if(fd < 0){
		kgerrstr(err, ERRMAX);
		return nil;
	}
	bytes = nil;
	bundle = nil;
	length = capacity = 0;
	for(;;){
		if(length == capacity){
			if(capacity == ZxMaxImage){
				count = kread(fd, &extra, 1);
				if(count > 0)
					strecpy(err, err+ERRMAX, "ZX image exceeds 32 MiB");
				break;
			}
			capacity = capacity == 0 ? 8192 : capacity * 2;
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
	if(count == 0){
		bundle = BundleOpenBytes(bytes, length);
		if(bundle == nil)
			strecpy(err, err+ERRMAX, "invalid ZX image");
	}else if(count < 0 && err[0] == '\0')
		kgerrstr(err, ERRMAX);
	kclose(fd);
	free(bytes);
	return bundle;
}

void
ZX_run(void *fp)
{
	F_ZX_run *f = fp;
	Bundle *bundle;
	BundleInstance *instance;
	char *path, err[ERRMAX] = "";
	long long result = 0;
	int hasresult = -1;

	path = strdup(string2c(f->path));
	if(path == nil)
		error("out of memory copying ZX path");
	release();
	bundle = zxopen(path, err);
	free(path);
	if(bundle != nil){
		instance = BundleInstantiateWithConsole(bundle, nil, 0, ZxSteps, zxwrite, nil);
		if(instance == nil)
			strecpy(err, err+sizeof(err), "cannot initialize ZX program");
		else{
			if(!BundleInstanceRun(instance, &result, &hasresult)){
				strecpy(err, err+sizeof(err), "ZX execution failed");
				hasresult = -1;
			}
			BundleInstanceClose(instance);
		}
		BundleClose(bundle);
	}
	acquire();
	f->ret->t0 = result;
	f->ret->t1 = hasresult;
	destroy(f->ret->t2);
	f->ret->t2 = H;
	if(err[0] != '\0')
		f->ret->t2 = c2string(err, strlen(err));
}
#endif

void
zxmodinit(void)
{
#ifdef TAIJI_ZX
	builtinmod("$ZX", ZXmodtab, ZXmodlen);
#endif
}
