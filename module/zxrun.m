Zxrun: module {
	PATH: con "/zx/zxrun.dis";
	init: fn(ctxt: ref Draw->Context, args: list of string);
	desktop: fn(ctxt: ref Draw->Context, path: string, state: ref ZX->Panel, desktop: ref ZX->Desktop): (big, int, string);
	panel: fn(ctxt: ref Draw->Context, path: string, state: ref ZX->Panel): (big, int, string);
};
