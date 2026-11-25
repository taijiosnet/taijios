Toolbar: module
{
	PATH: con "/zx/wm/toolbar.dis";
	init: fn(ctxt: ref Draw->Context, argv: list of string);
	desktop: fn(ctxt: ref Draw->Context, service: ref ZX->Desktop, path: string);
	initbuiltin: fn(c: ref Sh->Context, sh: Sh): string;
	runbuiltin: fn(c: ref Sh->Context, sh: Sh,
			cmd: list of ref Sh->Listnode, last: int): string;
	runsbuiltin: fn(c: ref Sh->Context, sh: Sh,
			cmd: list of ref Sh->Listnode): list of ref Sh->Listnode;
	whatis: fn(c: ref Sh->Context, sh: Sh, name: string, wtype: int): string;
	getself: fn(): Shellbuiltin;
};
