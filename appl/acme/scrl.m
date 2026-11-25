Scroll : module {
	PATH : con "/zx/acme/scrl.dis";

	init : fn(mods : ref Dat->Mods);
	scrsleep : fn(n : int);
	scrdraw : fn(t : ref Textm->Text);
	scrresize : fn();
	scroll : fn(t : ref Textm->Text, but : int);
};