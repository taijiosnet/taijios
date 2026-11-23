Filter: module
{
	DEFLATEPATH: con "/dis/lib/deflate.dis";
	INFLATEPATH: con "/dis/lib/inflate.dis";

	Rq: adt {
		pick {
		Start =>
			pid: int;
		Fill or Result =>
			buf: array of byte;
			reply: chan of int;
		Info =>
			msg: string;
		Finished =>
			buf: array of byte;
		Error =>
			e: string;
		}
	};

	init: fn();
	start: fn(param: string): chan of ref Rq;
};
