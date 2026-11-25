Styxpersist: module {
	PATH: con "/zx/lib/styxpersist.dis";
	init: fn(clientfd: ref Sys->FD, usefac: int, keyspec: string): (chan of chan of ref Sys->FD, string);
};
