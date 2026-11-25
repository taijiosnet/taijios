Rand: module
{
	PATH:	con "/zx/lib/rand.dis";
	init:	fn(seed: int);
	rand:       fn(modulus: int): int;
	bigrand:    fn(modulus: big): big;
};
