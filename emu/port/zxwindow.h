typedef struct ZxNativeWindow ZxNativeWindow;

enum {
	ZxnOpen = 1,
	ZxnFrame,
	ZxnClose,
	ZxnTitle,
	ZxnTask,
	ZxnCapture,
	ZxnChrome,
	ZxnDesktopAction,
	ZxnWindowAction,
	ZxnLaunch,
	ZxnResize,
	ZxnCursor,
	ZxnSample,
};

enum { ZxnPublish = 1, ZxnStaged = 2 };
enum { ZxnNoWindow, ZxnApplication, ZxnDesktop };
enum { ZxnChromeFields = 32, ZxnSnapshotFields = 7, ZxnWindowFields = 9 };

typedef struct ZxNativeRequest ZxNativeRequest;
struct ZxNativeRequest {
	int kind, width, height, first, rows, flag;
	const uchar *data;
	size_t length;
	const int *regions;
};

ZxNativeWindow *zxwindownew(int);
int zxwindowdesktop(ZxNativeWindow *);
void zxwindowdisconnect(ZxNativeWindow *);
void zxwindowfree(ZxNativeWindow *);
int zxwindowrequest(ZxNativeWindow *, ZxNativeRequest *);
int zxwindowreply(ZxNativeWindow *, int);
int zxwindowinput(ZxNativeWindow *, int *, vlong);
int zxnativesurface(void *, const char *, const char *, const HostValue *, int, HostValue *);
int zxnativeshelldesktop(void *, const char *, const char *, const HostValue *, int, HostValue *);
int zxwindowsnapshot(ZxNativeWindow *, const HostValue *);
int zxwindowsubmit(ZxNativeWindow *, ZxNativeRequest);
