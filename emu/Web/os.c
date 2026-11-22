/*
 * Host interface for the Web build. The emulator runs in Web Workers
 * that share one wasm memory: main() runs on a proxied pthread, every
 * kproc is another pthread, and the page's main thread only draws and
 * collects input. There are no host signals, terminal or processes.
 */
#include	<sys/types.h>
#include	<sys/time.h>
#include	<time.h>
#include	<sched.h>
#include	<signal.h>
#include	<emscripten.h>

#include	"dat.h"
#include	"fns.h"
#include	"error.h"

#include	<raise.h>

char *hosttype = "Web";

void (*coherence)(void) = nofence;

int	gidnobody = -1;
int	uidnobody = -1;

/* oshostintr signals a kproc blocked on the host; the call then returns early. */
static void
trapUSR1(int signo)
{
	USED(signo);
	if(up != nil)
		up->intwait = 0;
}

/*
 * emu/port/main.c declares a void main, compiled here as emumain; the
 * Emscripten start-up code calls an int main.
 */
extern void emumain(int, char**);
extern void weblazyinit(char*);

int
main(int argc, char **argv)
{
	emumain(argc, argv);
	return 0;
}

void
oslongjmp(void *regs, osjmpbuf env, int val)
{
	USED(regs);
	longjmp(env, val);
}

void
cleanexit(int x)
{
	if(up != nil && up->intwait){
		up->intwait = 0;
		return;
	}
	MAIN_THREAD_ASYNC_EM_ASM({ if(Module.taijiExit) Module.taijiExit($0); }, x);
	emscripten_force_exit(x);
}

void
osreboot(char *file, char **argv)
{
	USED(file);
	USED(argv);
	error("reboot is not supported in the browser");
}

void
libinit(char *imod)
{
	struct sigaction act;
	Proc *p;

	kstrdup(&ossysname, "taijios-web");

	memset(&act, 0, sizeof(act));
	act.sa_handler = trapUSR1;
	sigaction(SIGUSR1, &act, nil);
	signal(SIGPIPE, SIG_IGN);

	p = newproc();
	kprocinit(p);
	kstrdup(&eve, "taiji");

	p->env->uid = 0;
	p->env->gid = 0;

	weblazyinit(rootdir);
	emuinit(imod);
}

/* The browser has no console keyboard; input reaches the guest through Draw. */
int
readkbd(void)
{
	pexit("keyboard thread", 0);
	return 0;
}

long
osmillisec(void)
{
	static double t0;
	double now;

	now = emscripten_get_now();
	if(t0 == 0)
		t0 = now;
	return (long)(now - t0 + 0.5);
}

vlong
osnsec(void)
{
	struct timeval t;

	gettimeofday(&t, nil);
	return (vlong)t.tv_sec*1000000000LL + (vlong)t.tv_usec*1000;
}

vlong
osusectime(void)
{
	struct timeval t;

	gettimeofday(&t, nil);
	return (vlong)t.tv_sec*1000000 + t.tv_usec;
}

int
osmillisleep(ulong milsec)
{
	struct timespec time;

	time.tv_sec = milsec/1000;
	time.tv_nsec = (milsec%1000)*1000000;
	nanosleep(&time, nil);
	return 0;
}

int
limbosleep(ulong milsec)
{
	return osmillisleep(milsec);
}
