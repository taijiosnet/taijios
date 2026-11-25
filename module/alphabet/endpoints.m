Endpoints: module {
	PATH: con "/zx/alphabet/endpoints.dis";
	Endpoint: adt {
		addr: string;
		id: string;
		about: string;
		text: fn(e: self Endpoint): string;
		mk: fn(s: string): Endpoint;
	};
	init: fn();
	new: fn(net, addr: string, force: int): string;
	create: fn(addr: string): (ref Sys->FD, Endpoint);
	open: fn(net: string, ep: Endpoint): (ref Sys->FD, string);
};
