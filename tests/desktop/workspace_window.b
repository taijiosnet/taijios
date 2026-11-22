implement Workspacewindow;

include "sys.m";
	sys: Sys;
include "draw.m";
	draw: Draw;
	Display, Image: import draw;
include "tk.m";
include "wmclient.m";
	wm: Wmclient;
	Window: import wm;

Workspacewindow: module {
	init: fn(ctxt: ref Draw->Context, argv: list of string);
};

init(ctxt: ref Draw->Context, argv: list of string)
{
	sys = load Sys Sys->PATH;
	draw = load Draw Draw->PATH;
	wm = load Wmclient Wmclient->PATH;
	wm->init();
	name := hd tl argv;
	col := int 16rEE1133FF;
	if(name == "COBALT")
		col = int 16r1144EEFF;
	fill := ctxt.display.color(col);
	w := wm->window(ctxt, name, Wmclient->Appl);
	w.reshape(((120, 120), (360, 290)));
	w.onscreen("exact");
	w.wmctl("title " + name);
	w.wmctl("resizable 120 80");
	w.startinput("kbd" :: "ptr" :: nil);
	paint(w, fill);
	for(;;) alt {
	key := <-w.ctxt.kbd =>
		sys->print("WORKSPACE_KEY %s %d\n", name, key);
	p := <-w.ctxt.ptr =>
		if(p != nil && p.buttons != 0)
			sys->print("WORKSPACE_POINTER %s\n", name);
	cmd := <-w.ctxt.ctl or cmd = <-w.ctl =>
		if(cmd == "exit")
			return;
		w.wmctl(cmd);
		paint(w, fill);
	}
}

paint(w: ref Wmclient->Window, fill: ref Draw->Image)
{
	if(w.image != nil){
		w.image.draw(w.image.r, fill, nil, fill.r.min);
		w.image.flush(Draw->Flushnow);
	}
}
