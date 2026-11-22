typedef struct ZxNativeWindow ZxNativeWindow;

enum {
	ZxnOpen = 1,
	ZxnFrame,
	ZxnClose,
	ZxnTitle,
	ZxnTask,
};

enum { ZxnPublish = 1, ZxnStaged = 2 };

typedef struct ZxNativeRequest ZxNativeRequest;
struct ZxNativeRequest {
	int kind, width, height, first, rows, flag;
	const uchar *data;
	size_t length;
};

ZxNativeWindow *zxwindownew(void);
void zxwindowdisconnect(ZxNativeWindow *);
void zxwindowfree(ZxNativeWindow *);
int zxwindowrequest(ZxNativeWindow *, ZxNativeRequest *);
int zxwindowreply(ZxNativeWindow *, int);
int zxwindowinput(ZxNativeWindow *, int *, vlong);
int zxnativesurface(void *, const char *, const char *, const HostValue *, int, HostValue *);
