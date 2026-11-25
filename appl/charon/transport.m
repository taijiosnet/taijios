Transport: module
{
	HTTPPATH: con "/zx/charon/http.dis";
	FTPPATH: con "/zx/charon/ftp.dis";
	FILEPATH: con "/zx/charon/file.dis";

	init:		fn(cu: CharonUtils);
	connect:	fn(nc: ref CharonUtils->Netconn, bs: ref CharonUtils->ByteSource);
	writereq:	fn(nc: ref CharonUtils->Netconn, bs: ref CharonUtils->ByteSource);
	gethdr:	fn(nc: ref CharonUtils->Netconn, bs: ref CharonUtils->ByteSource);
	getdata:	fn(nc: ref CharonUtils->Netconn, bs: ref CharonUtils->ByteSource): int;
	defaultport:	fn(scheme: string) : int;
};
