Webget: module
{
	PATH: con "/zx/svc/webget/webget.dis";

	init: fn(ctxt: ref Draw->Context, argv: list of string);
	start: fn(ctl: chan of int);
};
