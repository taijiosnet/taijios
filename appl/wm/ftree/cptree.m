Cptree: module {
	PATH: con "/zx/lib/ftree/cptree.dis";
	init: fn();
	copyproc: fn(f, d: string, progressch: chan of string,
		warningch: chan of (string, chan of int),
		finishedch: chan of string);
};

