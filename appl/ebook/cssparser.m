CSSparser: module {
	PATH: con "/zx/ebook/cssparser.dis";
	Decl: adt {
		name:		string;
		important:	int;
		val:			string;
	};
	init:		fn();
	parse:	fn(s: string): list of (string, list of Decl);
	parsedecl:	fn(s: string): list of Decl;
};
