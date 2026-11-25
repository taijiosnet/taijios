Cvsimages: module {
	PATH: 	con "/zx/lib/cvsimages.dis";
	init:		fn();
	Cvsimage: adt {
		new:		fn(win: ref Tk->Toplevel, w: string): ref Cvsimage;
		fix:		fn(ci: self ref Cvsimage);
		config:	fn(ci: self ref Cvsimage): int;
	
		image:	ref Draw->Image;
		win:		ref Tk->Toplevel;
		w:		string;
		r:		Draw->Rect;
	};
};
