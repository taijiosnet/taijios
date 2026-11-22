implement Wm;
include "sys.m";
	sys: Sys;
include "draw.m";
	draw: Draw;
	Screen, Display, Image, Rect, Point, Wmcontext, Pointer: import draw;
include "wmsrv.m";
	wmsrv: Wmsrv;
	Window, Client: import wmsrv;
include "tk.m";
include "wmclient.m";
	wmclient: Wmclient;
include "string.m";
	str: String;
include "sh.m";
include "winplace.m";
	winplace: Winplace;
include "zx.m";
	zx: ZX;
include "toolbar.m";

Wm: module {
	init:	fn(ctxt: ref Draw->Context, argv: list of string);
};

Ptrstarted, Kbdstarted, Controlstarted, Controller, Fixedorigin, Keyeventstarted: con 1<<iota;
Bdwidth: con 3;
Resizecorner: con 8;
Doubleclick: con 16r100;
Minwidth: con 120;
Minheight: con 80;
Sminx, Sminy, Smaxx, Smaxy: con iota;
Minx, Miny, Maxx, Maxy: con 1<<iota;
Background: con int 16r777777FF;

screen: ref Screen;
display: ref Display;
ptrfocus: ref Client;
kbdfocus: ref Client;
controller: ref Client;
allowcontrol := 1;
fakekbd: chan of string;
fakekbdin: chan of string;
keyevents := 0;
buttons := 0;

RillImage: con "/dis/wm/rill.zx";
Defaultworkspaces: con 4;
Maxworkspaces: con 32;
# Raw key protocol shared with /dev/keyevent and zxrun.
Rawright: con 262;
Rawleft: con 263;
Rawshift: con 1;
Rawctrlalt: con 6;
DesktopClient: adt {
	client: ref Client;
	id, workspace: int;
	title: string;
	rect, saved: Rect;
	haswindow, minimized, maximized, restorefocus: int;
};
desk: ref ZX->Desktop;
desktopclients: list of ref DesktopClient;
desktoplayer: ref Client;
desktopgen, desktopid: int;
workspacefocus: array of ref Client;
workspacekeys: array of int;
discardpointer: int;

badmodule(p: string)
{
	sys->fprint(sys->fildes(2), "wm: cannot load %s: %r\n", p);
	raise "fail:bad module";
}

init(ctxt: ref Draw->Context, argv: list of string)
{
	sys  = load Sys Sys->PATH;
	draw = load Draw Draw->PATH;
	if(draw == nil)
		badmodule(Draw->PATH);

	str = load String String->PATH;
	if(str == nil)
		badmodule(String->PATH);

	wmsrv = load Wmsrv Wmsrv->PATH;
	if(wmsrv == nil)
		badmodule(Wmsrv->PATH);

	wmclient = load Wmclient Wmclient->PATH;
	if(wmclient == nil)
		badmodule(Wmclient->PATH);
	wmclient->init();

	winplace = load Winplace Winplace->PATH;
	if(winplace == nil)
		badmodule(Winplace->PATH);
	winplace->init();
	zx = load ZX ZX->PATH;

	sys->pctl(Sys->NEWPGRP|Sys->FORKNS, nil);
	if (ctxt == nil)
		ctxt = wmclient->makedrawcontext();
	display = ctxt.display;

	buts := Wmclient->Appl;
	if(ctxt.wm == nil)
		buts = Wmclient->Plain;
	win := wmclient->window(ctxt, "Wm", buts);
	wmclient->win.reshape(((0, 0), (100, 100)));
	wmclient->win.onscreen("place");
	if(win.image == nil){
		sys->fprint(sys->fildes(2), "wm: cannot get image to draw on\n");
		raise "fail:no image";
	}
	wmclient->win.startinput("kbd" :: "ptr" :: nil);
	rawkeys := chan of string;
	if(ctxt.wm == nil){
		fd := sys->open("/dev/keyevent", Sys->OREAD);
		if(fd != nil){
			spawn keyproc(fd, rawkeys);
			keyevents = 1;
		}
	}else
		keyevents = wmclient->win.wmctl("start keyevent") == nil;

	wmctxt := win.ctxt;
	screen = makescreen(win.image);

	(clientwm, join, req) := wmsrv->init();
	clientctxt := ref Draw->Context(ctxt.display, nil, clientwm);

	wmrectIO := sys->file2chan("/chan", "wmrect");
	if(wmrectIO == nil)
		fatal(sys->sprint("cannot make /chan/wmrect: %r"));

	sync := chan of string;
	argv = tl argv;
	if(argv == nil && sys->stat(RillImage).t0 >= 0)
		argv = "-rill" :: nil;
	desktopreq := chan of (ref ZX->Window, int, chan of int);
	if(argv != nil && hd argv == "-rill"){
		argv = tl argv;
		path := RillImage;
		if(argv != nil)
			path = hd argv;
		desk = ref ZX->Desktop;
		desk.request = desktopreq;
		desk.changed = chan[1] of int;
		desk.regions = array[32] of int;
		desk.workspacecount = Defaultworkspaces;
		workspacefocus = array[Maxworkspaces] of ref Client;
		workspacekeys = array[] of {0, 0};
		spawn desktopcommand(clientctxt, desk, path, sync);
	}else{
		if(argv == nil)
			argv = "wm/toolbar" :: nil;
		spawn command(clientctxt, argv, sync);
	}
	if((e := <-sync) != nil)
		fatal("cannot run command: " + e);

	fakekbd = chan of string;
	for(;;) alt {
	c := <-win.ctl or
	c = <-wmctxt.ctl =>
		if(len c >= 9 && c[:9] == "keyevent "){
			sendkeyevent(win, c);
			break;
		}
		# XXX could implement "pleaseexit" in order that
		# applications can raise a warning message before
		# they're unceremoniously dumped.
		if(c == "exit")
			for(z := wmsrv->top(); z != nil; z = z.znext)
				z.ctl <-= "exit";

		wmclient->win.wmctl(c);
		if(win.image != screen.image)
			reshaped(win);
	c := <-wmctxt.kbd or
	c = int <-fakekbd =>
		if(kbdfocus != nil && desktopvisible(kbdfocus))
			kbdfocus.kbd <-= c;
	c := <-rawkeys =>
		sendkeyevent(win, c);
	p := <-wmctxt.ptr =>
		if(wmclient->win.pointer(*p))
			break;
		if(discardpointer){
			discardpointer = p.buttons != 0;
			break;
		}
		if(p.buttons && (ptrfocus == nil || buttons == 0)){
			c := desktophit(p.xy);
			if(c != nil){
				ptrfocus = c;
				if(c != desktoplayer)
					c.ctl <-= "raise";
				setfocus(win, c);
				if((p.buttons & ~Doubleclick) == 1 && cornerresize(wmctxt.ptr, c, p.xy)){
					buttons = 0;
					break;
				}
			}
		}
		if(desktoplayer != nil && !buttons && !p.buttons && desktophit(p.xy) == desktoplayer)
			ptrfocus = desktoplayer;
		if(ptrfocus != nil && desktopvisible(ptrfocus) && (ptrfocus.flags & Ptrstarted) != 0){
			# inside currently selected client or it had button down last time (might have come up)
			buttons = p.buttons;
			ptrfocus.ptr <-= p;
			break;
		}
		buttons = 0;
	(c, rc) := <-join =>
		rc <-= nil;
		# new client; inform it of the available screen rectangle.
		# XXX do we need to do this now we've got wmrect?
		c.ctl <-= "rect " + r2s(screen.image.r);
		if(allowcontrol){
			controller = c;
			c.flags |= Controller;
			allowcontrol = 0;
		}else
			controlevent("newclient " + string c.id);
		c.cursor = "cursor";
		if(desk != nil){
			noarea := Rect((0, 0), (0, 0));
			d := ref DesktopClient(c, ++desktopid, desk.currentworkspace, "Window", noarea, noarea, 0, 0, 0, 0);
			desktopclients = d :: desktopclients;
		}
	(io, op, reply) := <-desktopreq =>
		reply <-= desktoprequest(win, io, op);
	(c, data, rc) := <-req =>
		# if client leaving
		if(rc == nil){
			c.remove();
			if(c.stop == nil)
				break;
			if(c == ptrfocus)
				clearptrfocus();
			wasfocused := c == kbdfocus;
			if(wasfocused)
				kbdfocus = nil;
			if(c == controller)
				controller = nil;
			if(desk != nil){
				desktopremove(c);
				forgetworkspacefocus(c);
				if(c == desktoplayer){
					desktoplayer = nil;
					desk.chrome = nil;
				}
				desktopchanged();
			}
			controlevent("delclient " + string c.id);
			if(desk == nil || wasfocused)
				restoreworkspacefocus(win);
			c.stop <-= 1;
			break;
		}
		err := handlerequest(win, wmctxt, c, string data);
		n := len data;
		if(err != nil)
			n = -1;
		alt{
		rc <-= (n, err) =>;
		* =>;
		}
	(nil, nil, nil, wc) := <-wmrectIO.write =>
		if(wc == nil)
			break;
		alt{
		wc <-= (0, "cannot write") =>;
		* =>;
		}
	(off, nil, nil, rc) := <-wmrectIO.read =>
		if(rc == nil)
			break;
		d := array of byte r2s(screen.image.r);
		if(off > len d)
			off = len d;
		alt{
		rc <-= (d[off:], nil) =>;
		* =>;
		}
	}
}

handlerequest(win: ref Wmclient->Window, wmctxt: ref Wmcontext, c: ref Client, req: string): string
{
#sys->print("%d: %s\n", c.id, req);
	args := str->unquoted(req);
	if(args == nil)
		return "no request";
	n := len args;
	if(req[0] == '!' && n < 3)
		return "bad arg count";
	case hd args {
	"key" =>
		# XXX should we restrict this capability to certain clients only?
		if(n != 2)
			return "bad arg count";
		if(fakekbdin == nil){
			fakekbdin = chan of string;
			spawn bufferproc(fakekbdin, fakekbd);
		}
		fakekbdin <-= hd tl args;
	"ptr" =>
		# ptr x y
		if(n != 3)
			return "bad arg count";
		if(ptrfocus != c)
			return "cannot move pointer";
		e := wmclient->win.wmctl(req);
		if(e == nil){
			c.ptr <-= nil;		# flush queue
			c.ptr <-= ref Pointer(buttons, (int hd tl args, int hd tl tl args), sys->millisec());
		}
	"cursor" =>
		# cursor hotx hoty dx dy data
		if(n != 6 && n != 1)
			return "bad arg count";
		c.cursor = req;
		if(ptrfocus == c || kbdfocus == c)
			return wmclient->win.wmctl(c.cursor);
	"start" =>
		if(n != 2)
			return "bad arg count";
		case hd tl args {
		"mouse" or
		"ptr" =>
			c.flags |= Ptrstarted;
		"kbd" =>
			c.flags |= Kbdstarted;
			# XXX this means that any new window grabs the focus from the current
			# application, but usually you want this to happen... how can we distinguish
			# the two cases?
			setfocus(win, c);
		"keyevent" =>
			if(!keyevents)
				return "key events not available";
			c.flags |= Kbdstarted | Keyeventstarted;
			setfocus(win, c);
		"control" =>
			if((c.flags & Controller) == 0)
				return "control not available";
			c.flags |= Controlstarted;
		* =>
			return "unknown input source";
		}
	"!reshape" =>
		# reshape tag reqid rect [how]
		# XXX allow "how" to specify that the origin of the window is never
		# changed - a new window will be created instead.
		if(n < 7)
			return "bad arg count";
		args = tl args;
		tag := hd args; args = tl args;
		args = tl args;		# skip reqid
		r: Rect;
		r.min.x = int hd args; args = tl args;
		r.min.y = int hd args; args = tl args;
		r.max.x = int hd args; args = tl args;
		r.max.y = int hd args; args = tl args;
		if(args != nil){
			area := desktopworkarea();
			case hd args{
			"onscreen" =>
				r = fitrect(r, area);
			"place" =>
				r = fitrect(r, area);
				r = newrect(r, area);
			"exact" =>
				;
			"max" =>
				r = area;
			* =>
				return "unkown placement method";
			}
		}
		if(c == desktoplayer && tag == ".")
			r = screen.image.r;
		err := reshape(c, tag, r);
		if(err == nil && desk != nil && c != desktoplayer && tag == "."){
			d := desktopfind(c);
			if(d != nil && !d.minimized && d.restorefocus){
				d.restorefocus = 0;
				setfocus(win, c);
			}
		}
		return err;
	"desktop" =>
		if(desk == nil || c != controller || n != 2 || hd tl args != "layer" || desktoplayer != nil)
			return "desktop layer not available";
		desktoplayer = c;
	"title" =>
		if(n != 2)
			return "bad arg count";
		if(desk != nil){
			d := desktopfind(c);
			if(d != nil && d.title != hd tl args){
				d.title = hd tl args;
				desktopchanged();
			}
		}
	"delete" =>
		# delete tag
		if(tl args == nil)
			return "tag required";
		c.setimage(hd tl args, nil);
		if(desk != nil && hd tl args == "."){
			d := desktopfind(c);
			if(d != nil && !d.minimized){
				d.haswindow = 0;
				forgetworkspacefocus(c);
				desktopchanged();
			}
		}
		if(c.wins == nil && c == ptrfocus)
			clearptrfocus();
		if(c.wins == nil && c == kbdfocus)
			if(desk != nil)
				restoreworkspacefocus(win);
			else
				setfocus(win, nil);
	"raise" =>
		if(c != desktoplayer && desktopvisible(c))
			c.top();
		desktopfront();
	"lower" =>
		c.bottom();
		if(desktoplayer != nil)
			desktoprestack();
	"resizable" =>
		if(n != 3)
			return "bad arg count";
		minsz := Point(int hd tl args, int hd tl tl args);
		if(minsz.x < 0 || minsz.y < 0 || minsz.x > screen.image.r.dx() || minsz.y > screen.image.r.dy())
			return "invalid minimum size";
		if(minsz.x < Minwidth)
			minsz.x = Minwidth;
		if(minsz.y < Minheight)
			minsz.y = Minheight;
		c.resizemin = minsz;
	"!move" or
	"!size" =>
		if(!desktopvisible(c))
			return "window is hidden";
		# !move tag reqid startx starty
		# !size tag reqid mindx mindy
		ismove := hd args == "!move";
		if(n < 3)
			return "bad arg count";
		args = tl args;
		tag := hd args; args = tl args;
		args = tl args;			# skip reqid
		w := c.window(tag);
		if(w == nil)
			return "no such tag";
		if(ismove){
			if(n != 5)
				return "bad arg count";
			return dragwin(wmctxt.ptr, c, w, Point(int hd args, int hd tl args).sub(w.r.min));
		}else{
			if(n != 5)
				return "bad arg count";
			sizewin(wmctxt.ptr, c, w, Point(int hd args, int hd tl args));
		}
	"fixedorigin" =>
		c.flags |= Fixedorigin;
	"rect" =>
		;
	"kbdfocus" =>
		if(n != 2)
			return "bad arg count";
		if(int hd tl args)
			setfocus(win, c);
		else if(c == kbdfocus)
			setfocus(win, nil);
	# controller specific messages:
	"request" =>		# can be used to test for control.
		if((c.flags & Controller) == 0)
			return "you are not in control";
	"ctl" =>
		# ctl id msg
		if((c.flags & Controlstarted) == 0)
			return "invalid request";
		if(n < 3)
			return "bad arg count";
		id := int hd tl args;
		for(z := wmsrv->top(); z != nil; z = z.znext)
			if(z.id == id)
				break;
		if(z == nil)
			return "no such client";
		z.ctl <-= str->quoted(tl tl args);
	"endcontrol" =>
		if(c != controller)
			return "invalid request";
		controller = nil;
		allowcontrol = 1;
		c.flags &= ~(Controlstarted | Controller);
	"task" or "untask" or "unhide" =>
		if(desk == nil){
			if(c == controller || controller == nil || (controller.flags & Controlstarted) == 0)
				return "unknown control request";
			controller.ctl <-= "request " + string c.id + " " + req;
			return nil;
		}
		d := desktopfind(c);
		if(d == nil || !d.haswindow || c == desktoplayer)
			return "window cannot be tasked";
		d.minimized = hd args == "task";
		if(d.minimized && c == ptrfocus)
			clearptrfocus();
		if(!d.minimized && d.restorefocus){
			d.restorefocus = 0;
			setfocus(win, c);
		}
		if(d.minimized && kbdfocus == c)
			restoreworkspacefocus(win);
		desktoprestack();
		desktopchanged();
	* =>
		if(c == controller || controller == nil || (controller.flags & Controlstarted) == 0)
			return "unknown control request";
		controller.ctl <-= "request " + string c.id + " " + req;
	}
	return nil;
}

Fix: con 1000;
# the window manager window has been reshaped;
# allocate a new screen, and move all the 
reshaped(win: ref Wmclient->Window)
{
	oldr := screen.image.r;
	newr := win.image.r;
	mx := Fix;
	if(oldr.dx() > 0)
		mx = newr.dx() * Fix / oldr.dx();
	my := Fix;
	if(oldr.dy() > 0)
		my = newr.dy() * Fix / oldr.dy();
	if(desk != nil)
		desk.chrome = nil;
	screen = makescreen(win.image);
	for(z := wmsrv->top(); z != nil; z = z.znext){
		for(wl := z.wins; wl != nil; wl = tl wl){
			w := hd wl;
			w.img = nil;
			nr := w.r.subpt(oldr.min);
			nr.min.x = nr.min.x * mx / Fix;
			nr.min.y = nr.min.y * my / Fix;
			nr.max.x = nr.max.x * mx / Fix;
			nr.max.y = nr.max.y * my / Fix;
			nr = nr.addpt(newr.min);
			w.img = screen.newwindow(nr, Draw->Refbackup, Draw->Nofill);
			# XXX check for creation failure
			w.r = nr;
			z.ctl <-= sys->sprint("!reshape %q -1 %s", w.tag, r2s(nr));
			z.ctl <-= "rect " + r2s(newr);
		}
	}
	if(desktoplayer != nil){
		desktoplayer.top();
		desktoprestack();
	}
	desktopchanged();
}

controlevent(e: string)
{
	if(controller != nil && (controller.flags & Controlstarted))
		controller.ctl <-= e;
}

dragwin(ptr: chan of ref Pointer, c: ref Client, w: ref Window, off: Point): string
{
	if(buttons == 0)
		return "too late";
	p: ref Pointer;
	org: Point;
	scr := desktopworkarea();
	Margin: con 10;
	do{
		p = <-ptr;
		org = p.xy.sub(off);
		if(org.y < scr.min.y)
			org.y = scr.min.y;
		else if(org.y > scr.max.y - Margin)
			org.y = scr.max.y - Margin;
		if(org.x < scr.min.x && org.x + w.r.dx() < scr.min.x + Margin)
			org.x = scr.min.x + Margin - w.r.dx();
		else if(org.x > scr.max.x - Margin)
			org.x = scr.max.x - Margin;
		w.img.origin(w.img.r.min, org);
	} while (p.buttons != 0);
	c.ptr <-= p;
	buttons = 0;
	r: Rect;
	r.min = p.xy.sub(off);
	if(desk != nil)
		r.min = org;
	r.max = r.min.add(w.r.size());
	if(r.eq(w.r))
		return "not moved";
	reshape(c, w.tag, r);
	return nil;
}

cornerresize(ptr: chan of ref Pointer, c: ref Client, press: Point): int
{
	if(c.resizemin.x == 0 || c.wins == nil)
		return 0;
	w := hd c.wins;
	if(w.tag != "." || !press.in(w.r) || press.x < w.r.max.x - Resizecorner ||
	    press.y < w.r.max.y - Resizecorner)
		return 0;
	lo := w.r.min.add(c.resizemin);
	hi := desktopworkarea().max;
	if(lo.x > hi.x || lo.y > hi.y)
		return 0;
	borders := array[4] of ref Image;
	r := w.r;
	do {
		p := <-ptr;
		r.max = w.r.max.add(p.xy.sub(press));
		if(r.max.x < lo.x)
			r.max.x = lo.x;
		if(r.max.y < lo.y)
			r.max.y = lo.y;
		if(r.max.x > hi.x)
			r.max.x = hi.x;
		if(r.max.y > hi.y)
			r.max.y = hi.y;
		if((p.buttons & 1) == 0){
			if(p.xy.eq(press))
				r = w.r;
			break;
		}
		showborders(borders, r, Minx|Miny|Maxx|Maxy);
		screen.image.flush(Draw->Flushnow);
	} while(1);
	borders = nil;
	screen.image.flush(Draw->Flushnow);
	# Let the client request its replacement image through the usual protocol.
	if(!r.eq(w.r))
		c.ctl <-= sys->sprint("!reshape %q -1 %s", w.tag, r2s(r));
	return 1;
}

sizewin(ptrc: chan of ref Pointer, c: ref Client, w: ref Window, minsize: Point): string
{
	borders := array[4] of ref Image;
	showborders(borders, w.r, Minx|Maxx|Miny|Maxy);
	screen.image.flush(Draw->Flushnow);
	while((ptr := <-ptrc).buttons == 0)
		;
	xy := ptr.xy;
	move, show: int;
	offset := Point(0, 0);
	r := w.r;
	show = Minx|Miny|Maxx|Maxy;
	if(xy.in(w.r) == 0){
		r = (xy, xy);
		move = Maxx|Maxy;
	}else {
		if(xy.x < (r.min.x+r.max.x)/2){
			move=Minx;
			offset.x = xy.x - r.min.x;
		}else{
			move=Maxx;
			offset.x = xy.x - r.max.x;
		}
		if(xy.y < (r.min.y+r.max.y)/2){
			move |= Miny;
			offset.y = xy.y - r.min.y;
		}else{
			move |= Maxy;
			offset.y = xy.y - r.max.y;
		}
	}
	return reshape(c, w.tag, sweep(ptrc, r, offset, borders, move, show, minsize));
}

reshape(c: ref Client, tag: string, r: Rect): string
{
	w := c.window(tag);
	same := w != nil && w.r.size().eq(r.size());
	# The asynchronous Draw origin change also raises the image. Guest windows
	# need their new image positioned before we can restack the workspaces.
	if(desk == nil && (c.flags & Fixedorigin) == 0 && same){
		c.setorigin(tag, r.min);
	} else {
		img := screen.newwindow(r, Draw->Refbackup, Draw->Nofill);
		if(img == nil)
			return sys->sprint("window creation failed: %r");
		if(desk != nil && same && w.img != nil)
			img.draw(r, w.img, nil, w.img.r.min);
		if(c.setimage(tag, img) == -1)
			return "can't do two at once";
	}
	if(c != desktoplayer && desk != nil && tag == "."){
		d := desktopfind(c);
		if(d != nil && !d.minimized){
			if(!d.haswindow)
				d.workspace = desk.currentworkspace;
			d.rect = r;
			d.haswindow = 1;
			desktopchanged();
		}
	}
	c.top();
	if(desk != nil)
		desktoprestack();
	return nil;
}

sweep(ptr: chan of ref Pointer, r: Rect, offset: Point, borders: array of ref Image, move, show: int, min: Point): Rect
{
	while((p := <-ptr).buttons != 0){
		xy := p.xy.sub(offset);
		if(move&Minx)
			r.min.x = xy.x;
		if(move&Miny)
			r.min.y = xy.y;
		if(move&Maxx)
			r.max.x = xy.x;
		if(move&Maxy)
			r.max.y = xy.y;
		showborders(borders, r, show);
	}
	r = r.canon();
	if(r.min.y < screen.image.r.min.y){
		r.min.y = screen.image.r.min.y;
		r = r.canon();
	}
	if(r.dx() < min.x){
		if(move & Maxx)
			r.max.x = r.min.x + min.x;
		else
			r.min.x = r.max.x - min.x;
	}
	if(r.dy() < min.y){
		if(move & Maxy)
			r.max.y = r.min.y + min.y;
		else {
			r.min.y = r.max.y - min.y;
			if(r.min.y < screen.image.r.min.y){
				r.min.y = screen.image.r.min.y;
				r.max.y = r.min.y + min.y;
			}
		}
	}
	return r;
}

showborders(b: array of ref Image, r: Rect, show: int)
{
	r = r.canon();
	b[Sminx] = showborder(b[Sminx], show&Minx,
		(r.min, (r.min.x+Bdwidth, r.max.y)));
	b[Sminy] = showborder(b[Sminy], show&Miny,
		((r.min.x+Bdwidth, r.min.y), (r.max.x-Bdwidth, r.min.y+Bdwidth)));
	b[Smaxx] = showborder(b[Smaxx], show&Maxx,
		((r.max.x-Bdwidth, r.min.y), (r.max.x, r.max.y)));
	b[Smaxy] = showborder(b[Smaxy], show&Maxy,
		((r.min.x+Bdwidth, r.max.y-Bdwidth), (r.max.x-Bdwidth, r.max.y)));
}

showborder(b: ref Image, show: int, r: Rect): ref Image
{
	if(!show)
		return nil;
	if(b != nil && b.r.size().eq(r.size()))
		b.origin(r.min, r.min);
	else
		b = screen.newwindow(r, Draw->Refbackup, Draw->Red);
	return b;
}

r2s(r: Rect): string
{
	return string r.min.x + " " + string r.min.y + " " +
			string r.max.x + " " + string r.max.y;
}

# XXX for consideration:
# do not allow applications to grab the keyboard focus
# unless there is currently no keyboard focus...
# but what about launching a new app from the taskbar:
# surely we should allow that to grab the focus?
setfocus(win: ref Wmclient->Window, new: ref Client)
{
	if(new != nil && (!desktopvisible(new) || !(new.flags & Kbdstarted)))
		return;
	old := kbdfocus;
	if(old == new)
		return;
	if(new == nil)
		wmclient->win.wmctl("cursor");
	else if(old == nil || old.cursor != new.cursor)
		wmclient->win.wmctl(new.cursor);
	if(old != nil)
		old.ctl <-= "haskbdfocus 0";
	
	if(new != nil){
		if(new != desktoplayer)
			new.ctl <-= "raise";
		new.ctl <-= "haskbdfocus 1";
		kbdfocus = new;
		if(desk != nil && new != desktoplayer)
			workspacefocus[desk.currentworkspace] = new;
	} else
		kbdfocus = nil;
	desktopchanged();
}

sendkeyevent(win: ref Wmclient->Window, message: string)
{
	if(desk != nil && workspacekey(win, message))
		return;
	if(kbdfocus != nil && desktopvisible(kbdfocus) && (kbdfocus.flags & Keyeventstarted))
		kbdfocus.ctl <-= message;
}

keyproc(fd: ref Sys->FD, messages: chan of string)
{
	buf := array[40] of byte;
	while((n := sys->read(fd, buf, len buf)) > 0)
		messages <-= string buf[:n];
}

makescreen(img: ref Image): ref Screen
{
	screen = Screen.allocate(img, img.display.color(Background), 0);
	img.draw(img.r, screen.fill, nil, screen.fill.r.min);
	return screen;
}

kill(pid: int, note: string): int
{
	fd := sys->open("/prog/"+string pid+"/ctl", Sys->OWRITE);
	if(fd == nil || sys->fprint(fd, "%s", note) < 0)
		return -1;
	return 0;
}

fatal(s: string)
{
	sys->fprint(sys->fildes(2), "wm: %s\n", s);
	kill(sys->pctl(0, nil), "killgrp");
	raise "fail:error";
}

# fit a window rectangle to the available space.
# try to preserve requested location if possible.
# make sure that the window is no bigger than
# the screen, and that its top and left-hand edges
# will be visible at least.
fitrect(w, r: Rect): Rect
{
	if(zx != nil){
		request := array[] of {ZX->WmFit, w.min.x, w.min.y, w.max.x, w.max.y,
			r.min.x, r.min.y, r.max.x, r.max.y};
		reply := array[4] of int;
		if(zx->wmcall(ZX->WindowPolicy, request, reply))
			return ((reply[0], reply[1]), (reply[2], reply[3]));
	}
	if(w.dx() > r.dx())
		w.max.x = w.min.x + r.dx();
	if(w.dy() > r.dy())
		w.max.y = w.min.y + r.dy();
	size := w.size();
	if (w.max.x > r.max.x)
		(w.min.x, w.max.x) = (r.min.x - size.x, r.max.x - size.x);
	if (w.max.y > r.max.y)
		(w.min.y, w.max.y) = (r.min.y - size.y, r.max.y - size.y);
	if (w.min.x < r.min.x)
		(w.min.x, w.max.x) = (r.min.x, r.min.x + size.x);
	if (w.min.y < r.min.y)
		(w.min.y, w.max.y) = (r.min.y, r.min.y + size.y);
	return w;
}

lastrect: Rect;
# find an suitable area for a window
newrect(w, r: Rect): Rect
{
	rl: list of Rect;
	for(z := wmsrv->top(); z != nil; z = z.znext){
		if(z == desktoplayer || !desktopvisible(z))
			continue;
		for(wl := z.wins; wl != nil; wl = tl wl)
			rl = (hd wl).r :: rl;
	}
	lastrect = placewindow(rl, r, lastrect, w.size());
	return lastrect;
}

placewindow(wins: list of Rect, screenrect, last: Rect, size: Point): Rect
{
	if(zx == nil)
		return winplace->place(wins, screenrect, last, size);
	request := array[11+4*len wins] of int;
	request[0:] = array[] of {len wins, screenrect.min.x, screenrect.min.y, screenrect.max.x, screenrect.max.y,
		last.min.x, last.min.y, last.max.x, last.max.y, size.x, size.y};
	original := wins;
	for(i := 11; wins != nil; i += 4){
		r := hd wins;
		(request[i], request[i+1], request[i+2], request[i+3]) = (r.min.x, r.min.y, r.max.x, r.max.y);
		wins = tl wins;
	}
	reply := array[4] of int;
	if(zx->wmcall(ZX->PlacePolicy, request, reply))
		return ((reply[0], reply[1]), (reply[2], reply[3]));
	return winplace->place(original, screenrect, last, size);
}

bufferproc(in, out: chan of string)
{
	h, t: list of string;
	dummyout := chan of string;
	for(;;){
		outc := dummyout;
		s: string;
		if(h != nil || t != nil){
			outc = out;
			if(h == nil)
				for(; t != nil; t = tl t)
					h = hd t :: h;
			s = hd h;
		}
		alt{
		x := <-in =>
			t = x :: t;
		outc <-= s =>
			h = tl h;
		}
	}
}

command(ctxt: ref Draw->Context, args: list of string, sync: chan of string)
{
	if((sh := load Sh Sh->PATH) != nil){
		sh->run(ctxt, "{$*&}" :: args);
		sync <-= nil;
		return;
	}
	fds := list of {0, 1, 2};
	sys->pctl(sys->NEWFD, fds);

	cmd := hd args;
	file := cmd;

	if(len file<4 || file[len file-4:]!=".dis")
		file += ".dis";

	c := load Wm file;
	if(c == nil) {
		err := sys->sprint("%r");
		if(err != "permission denied" && err != "access permission denied" && file[0]!='/' && file[0:2]!="./"){
			c = load Wm "/dis/"+file;
			if(c == nil)
				err = sys->sprint("%r");
		}
		if(c == nil){
			sync <-= sys->sprint("%s: %s\n", cmd, err);
			exit;
		}
	}
	sync <-= nil;
	c->init(ctxt, args);
}

desktopcommand(ctxt: ref Draw->Context, service: ref ZX->Desktop, path: string, sync: chan of string)
{
	broker := load Toolbar Toolbar->PATH;
	if(broker == nil){
		sync <-= sys->sprint("%s: %r", Toolbar->PATH);
		return;
	}
	sync <-= nil;
	broker->desktop(ctxt, service, path);
}

desktopchanged()
{
	if(desk == nil)
		return;
	desktopgen++;
	alt { desk.changed <-= 1 =>; * =>; }
}

desktopfind(c: ref Client): ref DesktopClient
{
	for(rows := desktopclients; rows != nil; rows = tl rows)
		if((hd rows).client == c)
			return hd rows;
	return nil;
}

desktopremove(c: ref Client)
{
	before: list of ref DesktopClient;
	rows := desktopclients;
	for(; rows != nil; rows = tl rows){
		if((hd rows).client == c){
			rows = tl rows;
			break;
		}
		before = hd rows :: before;
	}
	for(; before != nil; before = tl before)
		rows = hd before :: rows;
	desktopclients = rows;
}

desktopvisible(c: ref Client): int
{
	if(desk == nil || c == desktoplayer)
		return 1;
	d := desktopfind(c);
	return d != nil && d.workspace == desk.currentworkspace && !d.minimized;
}

clearptrfocus()
{
	if(ptrfocus != nil && (ptrfocus.flags & Ptrstarted))
		ptrfocus.ptr <-= nil;
	ptrfocus = nil;
	discardpointer = buttons != 0;
	buttons = 0;
}

forgetworkspacefocus(c: ref Client)
{
	for(i := 0; i < len workspacefocus; i++)
		if(workspacefocus[i] == c)
			workspacefocus[i] = nil;
}

restoreworkspacefocus(win: ref Wmclient->Window)
{
	if(desk != nil){
		c := workspacefocus[desk.currentworkspace];
		if(c != nil && c.wins != nil && desktopvisible(c)){
			setfocus(win, c);
			return;
		}
	}
	for(z := wmsrv->top(); z != nil; z = z.znext){
		if(z != desktoplayer && (z.flags & Kbdstarted) && desktopvisible(z) && (desk == nil || z.wins != nil)){
			setfocus(win, z);
			return;
		}
	}
	if(desktoplayer != nil && (desktoplayer.flags & Kbdstarted))
		setfocus(win, desktoplayer);
	else
		setfocus(win, nil);
}

switchworkspace(win: ref Wmclient->Window, index: int): int
{
	if(index < 0 || index >= desk.workspacecount)
		return 0;
	if(index == desk.currentworkspace){
		restoreworkspacefocus(win);
		return 1;
	}
	clearptrfocus();
	desk.currentworkspace = index;
	desktoprestack();
	restoreworkspacefocus(win);
	desktopchanged();
	return 1;
}

configureworkspaces(win: ref Wmclient->Window, count: int): int
{
	if(count < 1 || count > Maxworkspaces)
		return 0;
	if(count == desk.workspacecount)
		return 1;
	for(rows := desktopclients; rows != nil; rows = tl rows){
		d := hd rows;
		if(d.workspace >= count)
			d.workspace = count - 1;
	}
	for(i := count; i < desk.workspacecount; i++)
		workspacefocus[i] = nil;
	desk.workspacecount = count;
	if(desk.currentworkspace >= count)
		return switchworkspace(win, count - 1);
	desktoprestack();
	desktopchanged();
	return 1;
}

movetoworkspace(win: ref Wmclient->Window, d: ref DesktopClient, index: int): int
{
	if(index < 0 || index >= desk.workspacecount)
		return 0;
	if(index == d.workspace)
		return 1;
	c := d.client;
	forgetworkspacefocus(c);
	d.workspace = index;
	if(c == ptrfocus)
		clearptrfocus();
	desktoprestack();
	if(c == kbdfocus)
		restoreworkspacefocus(win);
	desktopchanged();
	return 1;
}

workspacekey(win: ref Wmclient->Window, message: string): int
{
	(n, args) := sys->tokenize(message, " ");
	if(n != 4 || hd args != "keyevent")
		return 0;
	args = tl args;
	kind := hd args;
	if(kind == "r"){
		workspacekeys[0] = workspacekeys[1] = 0;
		return 0;
	}
	key := int hd tl args;
	if(key != Rawleft && key != Rawright)
		return 0;
	slot := key - Rawright;
	if(kind == "u"){
		wasdown := workspacekeys[slot];
		workspacekeys[slot] = 0;
		return wasdown;
	}
	if(workspacekeys[slot])
		return 1;
	modifiers := int hd tl tl args;
	if(kind != "d" || (modifiers & Rawctrlalt) != Rawctrlalt)
		return 0;
	workspacekeys[slot] = 1;
	direction := 1;
	if(key == Rawleft)
		direction = -1;
	index := (desk.currentworkspace + desk.workspacecount + direction) % desk.workspacecount;
	if(modifiers & Rawshift){
		if(kbdfocus != nil && kbdfocus != desktoplayer){
			d := desktopfind(kbdfocus);
			if(d != nil && d.haswindow)
				movetoworkspace(win, d, index);
		}
	}else
		switchworkspace(win, index);
	return 1;
}

desktoprequest(win: ref Wmclient->Window, io: ref ZX->Window, op: int): int
{
	area := screen.image.r;
	if(op == ZX->DesktopChrome)
		return desktopchrome(area);
	if(op == ZX->DesktopCapture){
		desk.generation = desktopgen;
		desk.width = area.dx();
		desk.height = area.dy();
		desk.focused = 0;
		count := 0;
		for(rows := desktopclients; rows != nil; rows = tl rows){
			d := hd rows;
			if(d.client != desktoplayer && d.haswindow)
				count++;
		}
		windows := array[count] of ZX->DesktopWindow;
		i := 0;
		for(rows = desktopclients; rows != nil; rows = tl rows){
			d := hd rows;
			if(d.client == desktoplayer || !d.haswindow)
				continue;
			r := d.rect.subpt(area.min);
			focused := kbdfocus == d.client && desktopvisible(d.client);
			if(focused)
				desk.focused = d.id;
			windows[i++] = (d.id, r.min.x, r.min.y, r.dx(), r.dy(), d.workspace, focused,
				d.minimized, d.maximized, d.title, nil);
		}
		desk.windows = windows;
		return 1;
	}
	if(op == ZX->DesktopAction){
		if(io.input.text == "switch_workspace")
			return switchworkspace(win, io.input.button);
		if(io.input.text == "configure_workspaces")
			return configureworkspaces(win, io.input.button);
		if(io.input.text != "show_desktop")
			return 0;
		for(rows := desktopclients; rows != nil; rows = tl rows){
			d := hd rows;
			if(d.client != desktoplayer && d.haswindow && desktopvisible(d.client))
				d.client.ctl <-= "task";
		}
		return 1;
	}
	for(rows := desktopclients; rows != nil; rows = tl rows){
		d := hd rows;
		if(d.client != desktoplayer && d.haswindow && d.id == io.input.button)
			return desktopaction(win, d, io.input);
	}
	return 0;
}

desktopaction(win: ref Wmclient->Window, d: ref DesktopClient, req: ZX->Input): int
{
	c := d.client;
	area := desktopworkarea();
	r := d.rect;
	action := req.text;
	if(action == "move_to_workspace")
		return movetoworkspace(win, d, req.x);
	if(d.workspace != desk.currentworkspace)
		return 0;
	case action {
	"focus" =>
		if(d.minimized){
			c.ctl <-= "untask";
			d.restorefocus = 1;
		}else{
			c.top();
			desktopfront();
			setfocus(win, c);
		}
		return 1;
	"minimize" =>
		if(!d.minimized)
			c.ctl <-= "task";
		return 1;
	"restore" =>
		if(d.minimized){
			c.ctl <-= "untask";
			d.restorefocus = 1;
			return 1;
		}
		if(!d.maximized)
			return 1;
		r = fitrect(d.saved, area);
	"close" =>
		c.ctl <-= "exit";
		return 1;
	"maximize" =>
		if(d.minimized || c.resizemin.x == 0)
			return 0;
		if(d.maximized)
			return 1;
		d.saved = r;
		r = area;
	"move" or "resize" =>
		if(d.minimized || d.maximized || (action == "resize" && c.resizemin.x == 0))
			return 0;
		scr := screen.image.r;
		if(!Point(req.x, req.y).in(((0, 0), scr.size())))
			return 0;
		origin := scr.min.add((req.x, req.y));
		size := r.size();
		if(action == "resize"){
			if(req.width < c.resizemin.x || req.height < c.resizemin.y ||
			   req.width > area.dx() || req.height > area.dy())
				return 0;
			size = (req.width, req.height);
		}
		r = fitrect((origin, origin.add(size)), area);
	* =>
		return 0;
	}
	c.ctl <-= "!reshape . -1 " + r2s(r);
	d.maximized = action == "maximize";
	desktopchanged();
	return 1;
}


# The first desktop chrome region is the persistent panel. Popups may cover
# windows, but must not affect their placement or maximized size.
desktopworkarea(): Rect
{
	area := screen.image.r;
	if(desk == nil || len desk.chrome == 0)
		return area;
	panel := desk.chrome[0].r;
	if(panel.dx() >= panel.dy() && panel.dy() < area.dy()){
		if(panel.min.y == area.min.y)
			area.min.y = panel.max.y;
		else if(panel.max.y == area.max.y)
			area.max.y = panel.min.y;
	}else if(panel.dx() < panel.dy() && panel.dx() < area.dx()){
		if(panel.min.x == area.min.x)
			area.min.x = panel.max.x;
		else if(panel.max.x == area.max.x)
			area.max.x = panel.min.x;
	}
	return area;
}

# Shell chrome is drawn from the desktop frame into separate Draw layers.
# The window manager owns the layers and routes their input to the shell.
desktopchrome(area: Rect): int
{
	if(desktoplayer == nil)
		return 0;
	count := desk.regioncount / 4;
	if(count == 0){
		if(len desk.chrome != 0){
			desk.chrome = nil;
			screen.image.flush(Draw->Flushnow);
		}
		return 1;
	}
	rects := array[count] of Rect;
	same := count == len desk.chrome;
	for(i := 0; i < count; i++){
		p := Point(desk.regions[4*i], desk.regions[4*i+1]);
		size := Point(desk.regions[4*i+2], desk.regions[4*i+3]);
		if(p.x < 0 || p.y < 0 || p.x >= area.dx() || p.y >= area.dy() ||
		   size.x <= 0 || size.y <= 0 || size.x > area.dx()-p.x || size.y > area.dy()-p.y)
			return 0;
		p = p.add(area.min);
		rects[i] = (p, p.add(size));
		if(same && !rects[i].eq(desk.chrome[i].r))
			same = 0;
	}
	if(same)
		return 1;
	images := array[count] of ref Draw->Image;
	for(i = 0; i < count; i++){
		images[i] = screen.newwindow(rects[i], Draw->Refbackup, Draw->Nofill);
		if(images[i] == nil)
			return 0;
	}
	desk.chrome = images;
	desktopfront();
	return 2; # new layers need the retained pixels before the next draw
}

desktopfront()
{
	if(desk != nil && len desk.chrome != 0)
		screen.top(desk.chrome);
}

# The opaque desktop layer covers retained Draw windows from inactive spaces.
# Rebuild the display stack without changing the clients' logical stacking.
desktoprestack()
{
	if(desktoplayer == nil)
		return;
	background := desktoplayer.image(".");
	if(background == nil)
		return;
	count := 1;
	for(z := wmsrv->top(); z != nil; z = z.znext)
		if(z != desktoplayer && desktopvisible(z))
			count += len z.wins;
	images := array[count] of ref Image;
	i := 0;
	for(z = wmsrv->top(); z != nil; z = z.znext)
		if(z != desktoplayer && desktopvisible(z))
			for(wl := z.wins; wl != nil; wl = tl wl)
				if((hd wl).img != nil)
					images[i++] = (hd wl).img;
	images[i++] = background;
	screen.top(images[:i]);
	desktopfront();
}

desktophit(p: Point): ref Client
{
	if(desktoplayer != nil){
		for(i := 0; i < len desk.chrome; i++)
			if(desk.chrome[i].r.contains(p))
				return desktoplayer;
		for(z := wmsrv->top(); z != nil; z = z.znext)
			if(z != desktoplayer && desktopvisible(z) && z.contains(p))
				return z;
		return desktoplayer;
	}
	return wmsrv->find(p);
}
