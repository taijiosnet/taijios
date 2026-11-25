Gui: module {
	PATH: con "/zx/acme/gui.dis";
	WMPATH: con "/zx/acme/guiwm.dis";

	display : ref Draw->Display;
	mainwin : ref Draw->Image;
	yellow, green, red, blue, black, white : ref Draw->Image;

	init : fn(mods : ref Dat->Mods);
	spawnprocs : fn();
	cursorset : fn(p : Draw->Point);
	cursorswitch: fn(c : ref Dat->Cursor);

	killwins : fn();
};