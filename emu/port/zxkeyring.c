#include "dat.h"
#include "fns.h"

#ifdef TAIJI_ZX
#include <mp.h>
#include <libsec.h>
#include "ziran_host.h"
#include "zxkeyring.h"

/*
 * Cryptography for ZX guests over libsec and libmp, the libraries behind
 * the Limbo Keyring module. Big integers cross the boundary as hexadecimal
 * text with an optional minus sign, and results are written into a guest
 * byte slice. A call that produces several numbers separates them with
 * newlines.
 */

enum {
	TextBytes = 8192,	/* longest number: 32768 bits */
	ReplyBytes = 8 * TextBytes,	/* a kernel proc's stack is too small for this */
	Held = 16,
	MinKeyBits = 64,
	MaxKeyBits = 8192,
};

typedef DigestState *(*Hash)(uchar*, ulong, uchar*, DigestState*);

static struct {
	Hash hash;
	int length;
} digests[] = {
	{nil, 0},
	{md4, MD4dlen},
	{md5, MD5dlen},
	{sha1, SHA1dlen},
	{sha224, SHA224dlen},
	{sha256, SHA256dlen},
	{sha384, SHA384dlen},
	{sha512, SHA512dlen},
};

/* Numbers a call allocated, freed together when it returns. */
typedef struct Numbers Numbers;
struct Numbers {
	mpint *held[Held];
	int count;
};

static mpint*
keep(Numbers *numbers, mpint *value)
{
	if(value != nil && numbers->count < Held)
		numbers->held[numbers->count++] = value;
	return value;
}

static void
release(Numbers *numbers)
{
	while(numbers->count > 0)
		mpfree(numbers->held[--numbers->count]);
}

static int
isstring(const HostValue *value)
{
	return value->kind == HOST_STRING && (value->length == 0 || value->data != nil);
}

static int
isbytes(const HostValue *value)
{
	return value->kind == HOST_SLICE && value->type != nil && strcmp(value->type, "[]u8") == 0 &&
		(value->length == 0 || value->elements != nil);
}

static int
isint(const HostValue *value)
{
	return value->kind == HOST_INTEGER && value->integer >= INT32_MIN && value->integer <= INT32_MAX;
}

static int
s32(HostValue *result, int value)
{
	*result = (HostValue){.kind = HOST_INTEGER, .type = "s32", .integer = value};
	return 1;
}

static int
boolean(HostValue *result, int value)
{
	*result = (HostValue){.kind = HOST_INTEGER, .type = "bool", .integer = value != 0};
	return 1;
}

/* Write bytes into a guest slice. Returns the count, or -1 if it does not fit. */
static int
put(const HostValue *out, const uchar *bytes, int count)
{
	int i;

	if(count < 0 || (size_t)count > out->length)
		return -1;
	for(i = 0; i < count; i++)
		out->elements[i].bits = bytes[i];
	return count;
}

/* Parse hexadecimal text in a given base into a kept number, or nil. */
static mpint*
number(Numbers *numbers, const HostValue *text, int base)
{
	char *buffer, *end;
	mpint *value;

	if(text->length == 0 || text->length > TextBytes || memchr(text->data, 0, text->length) != nil)
		return nil;
	buffer = malloc(text->length + 1);
	if(buffer == nil)
		return nil;
	memmove(buffer, text->data, text->length);
	buffer[text->length] = 0;
	value = strtomp(buffer, &end, base, nil);
	/* Base 64 parsing stops before the padding. */
	while(base == 64 && *end == '=')
		end++;
	if(value != nil && *end != 0){
		mpfree(value);
		value = nil;
	}
	free(buffer);
	return keep(numbers, value);
}

/* Append a number as text in a base, after a newline unless it is the first. */
static int
append(char *text, int used, mpint *value, int base)
{
	char *digits;
	int length;

	if(used < 0 || value == nil)
		return -1;
	digits = mptoa(value, base, nil, 0);
	if(digits == nil)
		return -1;
	length = strlen(digits);
	if(used + length + 1 >= ReplyBytes){
		free(digits);
		return -1;
	}
	if(used != 0)
		text[used++] = '\n';
	memmove(text + used, digits, length);
	free(digits);
	return used + length;
}

static int
validbase(int base)
{
	return base == 10 || base == 16 || base == 32 || base == 64;
}

static int
digest(const char *function, const HostValue *args, int n, HostValue *result)
{
	uchar out[SHA512dlen];
	DigestState state;
	Hash hash;
	int length;

	if(n < 1 || !isint(args) || args[0].integer <= 0 || args[0].integer >= nelem(digests))
		return 0;
	hash = digests[args[0].integer].hash;
	length = digests[args[0].integer].length;
	if(strcmp(function, "Digest") == 0){
		if(n != 3 || !isstring(args+1) || !isbytes(args+2))
			return 0;
		hash((uchar*)args[1].data, args[1].length, out, nil);
		return s32(result, put(args+2, out, length));
	}
	if(strcmp(function, "Hmac") == 0){
		if(n != 4 || !isstring(args+1) || !isstring(args+2) || !isbytes(args+3))
			return 0;
		if(hash == md5)
			hmac_md5((uchar*)args[2].data, args[2].length, (uchar*)args[1].data, args[1].length, out, nil);
		else if(hash == sha1)
			hmac_sha1((uchar*)args[2].data, args[2].length, (uchar*)args[1].data, args[1].length, out, nil);
		else
			return s32(result, -1);
		return s32(result, put(args+3, out, length));
	}
	/* The guest keeps the running state between calls. A zeroed state is a fresh one. */
	if(n != (function[6] == 'U' ? 4 : 3) || !isstring(args+1) || args[1].length < sizeof(state))
		return 0;
	memmove(&state, args[1].data, sizeof(state));
	if(state.blen < 0 || state.blen >= Digestbsize || (state.seeded != 0 && state.seeded != 1))
		return s32(result, -1);
	state.malloced = 0;
	if(strcmp(function, "DigestUpdate") == 0){
		if(!isstring(args+2) || !isbytes(args+3) || args[3].length < sizeof(state))
			return 0;
		hash((uchar*)args[2].data, args[2].length, nil, &state);
		return s32(result, put(args+3, (uchar*)&state, sizeof(state)) < 0 ? -1 : 0);
	}
	if(!isbytes(args+2))
		return 0;
	hash(nil, 0, out, &state);
	return s32(result, put(args+2, out, length));
}

static int
aescbc(const HostValue *args, int n, HostValue *result)
{
	AESstate state;
	uchar *data;
	int length;

	if(n != 6 || !isstring(args) || !isstring(args+1) || !isstring(args+2) || args[3].kind != HOST_INTEGER ||
	   !isbytes(args+4) || !isbytes(args+5))
		return 0;
	length = args[2].length;
	if((args[0].length != 16 && args[0].length != 24 && args[0].length != 32) || args[1].length != AESbsize ||
	   args[2].length > INT32_MAX || args[4].length < args[2].length || args[5].length < AESbsize)
		return s32(result, -1);
	data = malloc(length + 1);
	if(data == nil)
		return s32(result, -1);
	memmove(data, args[2].data, length);
	setupAESstate(&state, (uchar*)args[0].data, args[0].length, (uchar*)args[1].data);
	if(args[3].integer != 0)
		aesCBCencrypt(data, length, &state);
	else
		aesCBCdecrypt(data, length, &state);
	put(args+4, data, length);
	put(args+5, state.ivec, AESbsize);
	free(data);
	memset(&state, 0, sizeof(state));
	return s32(result, length);
}

enum { Add = 1, Subtract, Multiply, Divide, Modulo, PowerModulo, Invert, ShiftLeft, ShiftRight, Negate };

static int
big(char *text, const HostValue *args, int n, HostValue *result)
{
	Numbers numbers = {0};
	mpint *a, *b, *c, *out;
	int operation, used = -1;

	if(n != 5 || !isint(args) || !isstring(args+1) || !isstring(args+2) || !isstring(args+3) || !isbytes(args+4))
		return 0;
	operation = args[0].integer;
	a = number(&numbers, args+1, 16);
	b = operation == Negate ? mpzero : number(&numbers, args+2, 16);
	c = operation == PowerModulo && args[3].length != 0 ? number(&numbers, args+3, 16) : nil;
	out = keep(&numbers, mpnew(0));
	if(a != nil && b != nil && out != nil && (operation != PowerModulo || args[3].length == 0 || c != nil)){
		used = 0;
		switch(operation){
		case Add:
			mpadd(a, b, out);
			break;
		case Subtract:
			mpsub(a, b, out);
			break;
		case Multiply:
			mpmul(a, b, out);
			break;
		case Divide:
		case Modulo:
			if(mpcmp(b, mpzero) == 0)
				used = -1;
			else if(operation == Divide)
				mpdiv(a, b, out, nil);
			else
				mpmod(a, b, out);
			break;
		case PowerModulo:
			/* Without a modulus the power itself is computed, so bound its size. */
			if(mpcmp(b, mpzero) < 0 || (c != nil && mpcmp(c, mpzero) <= 0) ||
			   (c == nil && (mpsignif(b) > 16 || (vlong)mpsignif(a) * mptoi(b) > ReplyBytes)))
				used = -1;
			else
				mpexp(a, b, c, out);
			break;
		case Invert:
			if(mpcmp(b, mpzero) <= 0)
				used = -1;
			else
				mpinvert(a, b, out);
			break;
		case ShiftLeft:
		case ShiftRight:
			if(mpcmp(b, mpzero) < 0 || mpsignif(b) > 16)
				used = -1;
			else if(operation == ShiftLeft)
				mpleft(a, mptoi(b), out);
			else
				mpright(a, mptoi(b), out);
			break;
		case Negate:
			mpsub(mpzero, a, out);
			break;
		default:
			used = -1;
		}
		if(used == 0)
			used = append(text, 0, out, 16);
	}
	release(&numbers);
	return s32(result, used < 0 ? -1 : put(args+4, (uchar*)text, used));
}

/* Generate a key or a signature: several numbers written as lines of hexadecimal. */
static int
generate(char *text, const char *function, const HostValue *args, int n, HostValue *result)
{
	Numbers numbers = {0};
	RSApriv *rsa;
	DSApriv *dsa, dsakey;
	DSAsig *dsasig;
	EGpriv *eg, egkey;
	EGsig *egsig;
	mpint *message;
	int used = -1;

	memset(&dsakey, 0, sizeof(dsakey));
	memset(&egkey, 0, sizeof(egkey));
	if(strcmp(function, "RsaGenerate") == 0){
		if(n != 4 || !isint(args) || !isint(args+1) || !isint(args+2) || !isbytes(args+3))
			return 0;
		if(args[0].integer < MinKeyBits || args[0].integer > MaxKeyBits || args[1].integer < 2 ||
		   args[1].integer > args[0].integer || args[2].integer < 1 || args[2].integer > 64)
			return s32(result, -1);
		rsa = rsagen(args[0].integer, args[1].integer, args[2].integer);
		if(rsa != nil && mpcmp(rsa->dk, mpzero) < 0){
			/* rsagen keeps d from the extended gcd, which can be negative. Its own
			 * decryption uses only d mod p-1 and d mod q-1; guests may use d itself. */
			mpint *phi = keep(&numbers, mpnew(0)), *pm = keep(&numbers, mpnew(0)), *qm = keep(&numbers, mpnew(0));

			if(phi != nil && pm != nil && qm != nil){
				mpsub(rsa->p, mpone, pm);
				mpsub(rsa->q, mpone, qm);
				mpmul(pm, qm, phi);
				mpmod(rsa->dk, phi, pm);
				mpassign(pm, rsa->dk);
			}
			release(&numbers);
		}
		if(rsa != nil && mpcmp(rsa->dk, mpzero) > 0){
			used = append(text, 0, rsa->pub.n, 16);
			used = append(text, used, rsa->pub.ek, 16);
			used = append(text, used, rsa->dk, 16);
			used = append(text, used, rsa->p, 16);
			used = append(text, used, rsa->q, 16);
			used = append(text, used, rsa->kp, 16);
			used = append(text, used, rsa->kq, 16);
			used = append(text, used, rsa->c2, 16);
		}
		if(rsa != nil)
			rsaprivfree(rsa);
		return s32(result, used < 0 ? -1 : put(args+3, (uchar*)text, used));
	}
	if(strcmp(function, "DsaGenerate") == 0){
		if(n != 4 || !isstring(args) || !isstring(args+1) || !isstring(args+2) || !isbytes(args+3))
			return 0;
		dsa = nil;
		if(args[0].length == 0)
			dsa = dsagen(nil);
		else{
			dsakey.pub.p = number(&numbers, args, 16);
			dsakey.pub.q = number(&numbers, args+1, 16);
			dsakey.pub.alpha = number(&numbers, args+2, 16);
			if(dsakey.pub.p != nil && dsakey.pub.q != nil && dsakey.pub.alpha != nil &&
			   mpcmp(dsakey.pub.p, mptwo) > 0 && mpcmp(dsakey.pub.q, mptwo) > 0)
				dsa = dsagen(&dsakey.pub);
		}
		if(dsa != nil){
			used = append(text, 0, dsa->pub.p, 16);
			used = append(text, used, dsa->pub.q, 16);
			used = append(text, used, dsa->pub.alpha, 16);
			used = append(text, used, dsa->pub.key, 16);
			used = append(text, used, dsa->secret, 16);
			dsaprivfree(dsa);
		}
		release(&numbers);
		return s32(result, used < 0 ? -1 : put(args+3, (uchar*)text, used));
	}
	if(strcmp(function, "EgGenerate") == 0){
		if(n != 3 || !isint(args) || !isint(args+1) || !isbytes(args+2))
			return 0;
		if(args[0].integer < MinKeyBits || args[0].integer > MaxKeyBits || args[1].integer < 0 || args[1].integer > 64)
			return s32(result, -1);
		eg = eggen(args[0].integer, args[1].integer);
		if(eg != nil){
			used = append(text, 0, eg->pub.p, 16);
			used = append(text, used, eg->pub.alpha, 16);
			used = append(text, used, eg->pub.key, 16);
			used = append(text, used, eg->secret, 16);
			egprivfree(eg);
		}
		return s32(result, used < 0 ? -1 : put(args+2, (uchar*)text, used));
	}
	if(strcmp(function, "DsaSign") == 0){
		if(n != 6 || !isstring(args) || !isstring(args+1) || !isstring(args+2) || !isstring(args+3) ||
		   !isstring(args+4) || !isbytes(args+5))
			return 0;
		dsakey.pub.p = number(&numbers, args, 16);
		dsakey.pub.q = number(&numbers, args+1, 16);
		dsakey.pub.alpha = number(&numbers, args+2, 16);
		dsakey.secret = number(&numbers, args+3, 16);
		message = number(&numbers, args+4, 16);
		if(dsakey.pub.p != nil && dsakey.pub.q != nil && dsakey.pub.alpha != nil && dsakey.secret != nil &&
		   message != nil && mpcmp(dsakey.pub.p, mptwo) > 0 && mpcmp(dsakey.pub.q, mptwo) > 0){
			dsasig = dsasign(&dsakey, message);
			if(dsasig != nil){
				used = append(text, 0, dsasig->r, 16);
				used = append(text, used, dsasig->s, 16);
				dsasigfree(dsasig);
			}
		}
		release(&numbers);
		return s32(result, used < 0 ? -1 : put(args+5, (uchar*)text, used));
	}
	if(strcmp(function, "EgSign") == 0){
		if(n != 5 || !isstring(args) || !isstring(args+1) || !isstring(args+2) || !isstring(args+3) ||
		   !isbytes(args+4))
			return 0;
		egkey.pub.p = number(&numbers, args, 16);
		egkey.pub.alpha = number(&numbers, args+1, 16);
		egkey.secret = number(&numbers, args+2, 16);
		message = number(&numbers, args+3, 16);
		if(egkey.pub.p != nil && egkey.pub.alpha != nil && egkey.secret != nil && message != nil &&
		   mpcmp(egkey.pub.p, mptwo) > 0){
			egsig = egsign(&egkey, message);
			if(egsig != nil){
				used = append(text, 0, egsig->r, 16);
				used = append(text, used, egsig->s, 16);
				egsigfree(egsig);
			}
		}
		release(&numbers);
		return s32(result, used < 0 ? -1 : put(args+4, (uchar*)text, used));
	}
	return 0;
}

static int
verify(const char *function, const HostValue *args, int n, HostValue *result)
{
	Numbers numbers = {0};
	DSApub dsa;
	DSAsig dsasig;
	EGpub eg;
	EGsig egsig;
	mpint *message;
	int i, ok = 0;

	for(i = 0; i < n; i++)
		if(!isstring(args+i))
			return 0;
	if(strcmp(function, "DsaVerify") == 0){
		if(n != 7)
			return 0;
		dsa.p = number(&numbers, args, 16);
		dsa.q = number(&numbers, args+1, 16);
		dsa.alpha = number(&numbers, args+2, 16);
		dsa.key = number(&numbers, args+3, 16);
		dsasig.r = number(&numbers, args+4, 16);
		dsasig.s = number(&numbers, args+5, 16);
		message = number(&numbers, args+6, 16);
		if(dsa.p != nil && dsa.q != nil && dsa.alpha != nil && dsa.key != nil && dsasig.r != nil &&
		   dsasig.s != nil && message != nil && mpcmp(dsa.p, mptwo) > 0 && mpcmp(dsa.q, mptwo) > 0)
			ok = dsaverify(&dsa, &dsasig, message) == 0;
	}else{
		if(n != 6)
			return 0;
		eg.p = number(&numbers, args, 16);
		eg.alpha = number(&numbers, args+1, 16);
		eg.key = number(&numbers, args+2, 16);
		egsig.r = number(&numbers, args+3, 16);
		egsig.s = number(&numbers, args+4, 16);
		message = number(&numbers, args+5, 16);
		if(eg.p != nil && eg.alpha != nil && eg.key != nil && egsig.r != nil && egsig.s != nil &&
		   message != nil && mpcmp(eg.p, mptwo) > 0)
			ok = egverify(&eg, &egsig, message) == 0;
	}
	release(&numbers);
	return boolean(result, ok);
}

/* Calls whose results are numbers written as text. */
static int
arithmetic(char *text, const char *function, const HostValue *args, int n, HostValue *result)
{
	uchar bytes[256];
	Numbers numbers = {0};
	mpint *a, *b;
	int used, count;

	if(strcmp(function, "Big") == 0)
		return big(text, args, n, result);
	if(strcmp(function, "BigCompare") == 0){
		if(n != 2 || !isstring(args) || !isstring(args+1))
			return 0;
		a = number(&numbers, args, 16);
		b = number(&numbers, args+1, 16);
		/* mpcmp gives any sign, not only -1, 0 or 1. */
		count = a == nil || b == nil ? -2 : (mpcmp(a, b) > 0) - (mpcmp(a, b) < 0);
		release(&numbers);
		return s32(result, count);
	}
	if(strcmp(function, "BigBits") == 0){
		if(n != 1 || !isstring(args))
			return 0;
		a = number(&numbers, args, 16);
		count = a == nil ? -1 : mpsignif(a);
		release(&numbers);
		return s32(result, count);
	}
	if(strcmp(function, "BigConvert") == 0){
		if(n != 4 || !isstring(args) || !isint(args+1) || !isint(args+2) || !isbytes(args+3))
			return 0;
		used = -1;
		if(validbase(args[1].integer) && validbase(args[2].integer) &&
		   (a = number(&numbers, args, args[1].integer)) != nil)
			used = append(text, 0, a, args[2].integer);
		release(&numbers);
		return s32(result, used < 0 ? -1 : put(args+3, (uchar*)text, used));
	}
	if(strcmp(function, "BigIsPrime") == 0){
		if(n != 2 || !isstring(args) || !isint(args+1))
			return 0;
		a = number(&numbers, args, 16);
		count = a != nil && mpcmp(a, mpone) > 0 && args[1].integer >= 1 && args[1].integer <= 64 &&
			probably_prime(a, args[1].integer);
		release(&numbers);
		return boolean(result, count);
	}
	if(strcmp(function, "BigRandom") == 0 || strcmp(function, "BigPrime") == 0){
		count = function[3] == 'P';
		if(n != (count ? 3 : 2) || !isint(args) || (count && !isint(args+1)) || !isbytes(args+n-1))
			return 0;
		if(args[0].integer < 2 || args[0].integer > MaxKeyBits ||
		   (count && (args[1].integer < 1 || args[1].integer > 64)))
			return s32(result, -1);
		a = keep(&numbers, mpnew(0));
		if(a != nil){
			if(count)
				genprime(a, args[0].integer, args[1].integer);
			else
				mprand(args[0].integer, genrandom, a);
		}
		used = append(text, 0, a, 16);
		release(&numbers);
		return s32(result, used < 0 ? -1 : put(args+n-1, (uchar*)text, used));
	}
	if(strcmp(function, "Random") == 0){
		if(n != 1 || !isbytes(args))
			return 0;
		count = args[0].length > sizeof(bytes) ? sizeof(bytes) : args[0].length;
		genrandom(bytes, count);
		return s32(result, put(args, bytes, count));
	}
	return generate(text, function, args, n, result);
}

int
zxkeyring(void *context, const char *module, const char *function,
	const HostValue *args, int n, HostValue *result)
{
	char *text;
	int ok;

	USED(context);
	USED(module);
	if(strncmp(function, "Digest", 6) == 0 || strcmp(function, "Hmac") == 0)
		return digest(function, args, n, result);
	if(strcmp(function, "AesCbc") == 0)
		return aescbc(args, n, result);
	if(strcmp(function, "DsaVerify") == 0 || strcmp(function, "EgVerify") == 0)
		return verify(function, args, n, result);
	text = malloc(ReplyBytes);
	if(text == nil)
		return s32(result, -1);
	ok = arithmetic(text, function, args, n, result);
	free(text);
	return ok;
}
#endif
