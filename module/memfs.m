MemFS : module {
	PATH : con "/zx/lib/memfs.dis";
	init : fn() : string;
	newfs : fn (maxsz : int) : ref Sys->FD;
};
