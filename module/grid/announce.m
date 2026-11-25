Announce: module {
	PATH:	con "/zx/grid/lib/announce.dis";
	init:		fn();
	announce:	fn(): (string, ref Sys->Connection);	# find a local address, any port, and return its name and an announced connection.
};
