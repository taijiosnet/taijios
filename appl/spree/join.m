Join: module {
	PATH: con "/zx/spree/join.dis";
	join: fn(ctxt: ref Draw->Context, mnt: string, dir: string, joinstr: string): string;
	init:   fn(ctxt: ref Draw->Context, argv: list of string);
};
