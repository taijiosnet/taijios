ZX: module
{
	PATH:	con "$ZX";

	# The integer is 1 for a returned value, 0 for void and -1 on error.
	run:	fn(path: string): (big, int, string);
};
