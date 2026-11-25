Multistyx: module {
	PATH: con "/zx/lib/multistyx.dis";
	init: fn(): Styxlib;
	srv: fn(addr, mntpath: string, doauth: int, algs: list of string):
			(chan of (int, ref Styxlib->Styxserver, string),
			chan of (int, ref Styxlib->Styxserver, ref Styxlib->Tmsg),
			string);
};
