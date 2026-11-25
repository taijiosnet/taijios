Objstore: module {
	PATH: con "/zx/spree/lib/objstore.dis";

	init:			fn(mod: Spree, g: ref Clique);
	unarchive:	fn();
	setname:		fn(o: ref Object, name: string);
	get:			fn(name: string): ref Object;
};
