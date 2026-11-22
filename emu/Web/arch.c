/*
 * Machine primitives for wasm32. Wasm has no floating-point control or
 * status state (always round-to-nearest, no traps), no caller frames to
 * inspect and coherent instruction memory, so those are constant here.
 * The Dis interpreter runs uncompiled: compile() declines every module.
 */
#include	"dat.h"
#include	"fns.h"
#include	"interp.h"

void	(*comvec)(void);

int
compile(Module *m, int size, Modlink *ml)
{
	USED(m);
	USED(size);
	USED(ml);
	return 0;
}

ulong
umult(ulong m1, ulong m2, ulong *hi)
{
	uvlong p;

	p = (uvlong)m1 * m2;
	*hi = p >> 32;
	return p;
}

int
_tas(int *v)
{
	return __atomic_exchange_n(v, 1, __ATOMIC_SEQ_CST);
}

void
FPsave(void *f)
{
	USED(f);
}

void
FPrestore(void *f)
{
	USED(f);
}

int
segflush(void *a, ulong n)
{
	USED(a);
	USED(n);
	return 0;
}

uintptr
getcallerpc(void *x)
{
	USED(x);
	return 0;
}

static ulong fcr = FPPDBL|FPRNR|FPINVAL|FPZDIV|FPOVFL;

void
setfcr(ulong v)
{
	fcr = v;
}

ulong
getfcr(void)
{
	return fcr;
}

void
setfsr(ulong v)
{
	USED(v);
}

ulong
getfsr(void)
{
	return 0;
}
