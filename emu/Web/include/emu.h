/*
 * Web (wasm32) declarations for emu: the FPU save area, the per-thread
 * current process and the error-label primitive. Every kproc is a
 * pthread running in a Web Worker that shares the module's memory.
 */

typedef struct FPU FPU;
struct FPU
{
	uchar	env[4];
};

#define KSTACK (256 * 1024)

extern	Proc*	getup(void);

#define	up	(getup())

typedef jmp_buf osjmpbuf;
#define	ossetjmp(buf)	setjmp(buf)
