CCI: module
{
	PATH:	con "/zx/lib/cci.dis";

	# Common Client Interface, for external control of Charon

	init: fn(smod: String, hctl: chan of string);
	view: fn(url, ctype: string, data: array of byte);
};
