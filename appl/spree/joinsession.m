
Joinsession: module {
	PATH: con "/zx/spree/joinsession.dis";
	join: fn(ctxt: ref Draw->Context, mnt: string, dir: string, join: string): string;
	init:   fn(ctxt: ref Draw->Context, argv: list of string);
};

