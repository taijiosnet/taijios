Drawmux: module {
	PATH: con "/zx/lib/drawmux.dis";

	init: fn(): (string, ref Draw->Display);
	newviewer: fn(fd: ref Sys->FD);
};
