Proxy: module
{
	PATH:	con "/zx/collab/proxy.dis";
	init:	fn (root: string, fd: ref Sys->FD, rc: chan of ref Srvmgr->Srvreq, user: string);
};
