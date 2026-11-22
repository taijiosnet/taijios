implement Zxrun;

include "sys.m";
	sys: Sys;
include "draw.m";
	draw: Draw;
	Display, Font, Image, Point, Rect: import draw;
include "tk.m";
include "wmlib.m";
	wmlib: Wmlib;
include "wmclient.m";
	wm: Wmclient;
	Window: import wm;
include "keyboard.m";
include "zx.m";

include "zxrun.m";
include "daytime.m";

Wm: module
{
	init:	fn(ctxt: ref Draw->Context, args: list of string);
};

Zxresult: type (big, int, string);
# Only the runner records process IDs, after each helper reports its PID.
WindowWorkers: adt {
	reader, deadline: int;
};
Stdin: type (int, array of byte);
QueueSize: con 64;
PanelHeight: con 32;
KeyCount: con 350;
WheelUp: con 8;
WheelDown: con 16;
RGBAbytes: con Draw->Chans(16r48281808);
RGBbytes: con Draw->Chans(16r281808);

Events: adt {
	ring: array of ZX->Input;
	head, count, redraw: int;
	push: fn(q: self ref Events, e: ZX->Input);
	pop: fn(q: self ref Events): ZX->Input;
};

init(ctxt: ref Draw->Context, args: list of string)
{
	sys = load Sys Sys->PATH;
	stderr := sys->fildes(2);
	path: string;
	window := 0;
	command := 0;
	namedstatus := 0;
	newgroup := 0;
	if(args != nil)
		args = tl args;
	while(args != nil && (hd args == "-w" || hd args == "-c" || hd args == "-p" || hd args == "-s")){
		case hd args {
		"-w" => window = 1; args = tl args;
		"-c" => command = 1; args = tl args;
		"-s" => command = namedstatus = 1; args = tl args;
		"-p" => newgroup = 1; args = tl args;
		}
	}
	if(args == nil || hd args == nil){
		sys->fprint(stderr, "usage: zxrun [-c|-s] [-w] [-p] file.zx [args ...]\n");
		raise "fail:usage";
	}
	path = hd args;
	args = tl args;

	zx := load ZX ZX->PATH;
	if(zx == nil){
		sys->fprint(stderr, "zxrun: ZX runtime unavailable: %r\n");
		raise "fail:zx";
	}
	if(newgroup && sys->pctl(Sys->NEWPGRP, nil) < 0){
		sys->fprint(stderr, "zxrun: cannot start a process group: %r\n");
		raise "fail:zx";
	}

	value: big;
	status: int;
	problem: string;
	if(window)
		(value, status, problem) = runwindow(zx, ctxt, path, args, nil, nil);
	else if(command || args != nil)
		(value, status, problem) = zx->runargs(path, args);
	else
		(value, status, problem) = zx->run(path);
	if(status < 0){
		sys->fprint(stderr, "zxrun: %s: %s\n", path, problem);
		raise "fail:zx";
	}
	if(command){
		if(status > 0 && value != big 0){
			if(namedstatus && problem != nil)
				raise "fail:" + problem;
			raise sys->sprint("fail:%bd", value);
		}
		return;
	}
	if(status > 0 && sys->print("%bd\n", value) < 0){
		sys->fprint(stderr, "zxrun: write error: %r\n");
		raise "fail:write error";
	}
}

panel(ctxt: ref Draw->Context, path: string, state: ref ZX->Panel): Zxresult
{
	return desktop(ctxt, path, state, nil);
}

desktop(ctxt: ref Draw->Context, path: string, state: ref ZX->Panel, desk: ref ZX->Desktop): Zxresult
{
	sys = load Sys Sys->PATH;
	zx := load ZX ZX->PATH;
	if(zx == nil)
		return (big 0, -1, "ZX runtime unavailable");
	wmlib = load Wmlib Wmlib->PATH;
	if(wmlib == nil)
		return (big 0, -1, "window manager library unavailable");
	wmlib->init();
	return runwindow(zx, ctxt, path, nil, state, desk);
}

runwindow(zx: ZX, ctxt: ref Draw->Context, path: string, args: list of string, state: ref ZX->Panel, desk: ref ZX->Desktop): Zxresult
{
	if(ctxt == nil || ctxt.wm == nil)
		return (big 0, -1, "graphical ZX needs a window manager context");
	draw = load Draw Draw->PATH;
	wm = load Wmclient Wmclient->PATH;
	if(draw == nil || wm == nil)
		return (big 0, -1, "cannot load graphical ZX support");
	wm->init();
	bridge := ref ZX->Window;
	bridge.panel = state;
	bridge.desktop = desk;
	bridge.request = chan[1] of int;
	bridge.reply = chan[1] of int;
	pid := chan of int;
	done := chan[1] of Zxresult;
	spawn engine(zx, path, args, bridge, pid, done);
	worker := <-pid;
	workers := ref WindowWorkers(0, 0);
	{
		result := serve(ctxt, bridge, done, workers);
		stopreader(workers);
		kill(workers.deadline);
		return result;
	} exception e {
	"*" =>
		kill(worker);
		stopreader(workers);
		kill(workers.deadline);
		return (big 0, -1, e);
	}
}

engine(zx: ZX, path: string, args: list of string, bridge: ref ZX->Window, pid: chan of int, done: chan of Zxresult)
{
	pid <-= sys->pctl(0, nil);
	{
		done <-= zx->runwindowargs(path, args, bridge);
	} exception e {
	"*" =>
		done <-= (big 0, -1, e);
	}
}

kill(pid: int)
{
	if(pid <= 0)
		return;
	fd := sys->open("/prog/" + string pid + "/ctl", Sys->OWRITE);
	if(fd != nil)
		sys->fprint(fd, "kill");
}

stopreader(workers: ref WindowWorkers)
{
	pid := workers.reader;
	workers.reader = 0;
	kill(pid);
}

readstdin(out: chan of Stdin, pid: chan of int)
{
	pid <-= sys->pctl(0, nil);
	if(sys->pctl(Sys->NEWFD, 0 :: nil) < 0){
		out <-= (-1, nil);
		return;
	}
	fd := sys->fildes(0);
	for(;;){
		data := array[ZX->StdinChunk] of byte;
		n := sys->read(fd, data, len data);
		out <-= (n, data);
		if(n <= 0)
			return;
	}
}

waitdeadline(delay: int, timeout, pid: chan of int)
{
	pid <-= sys->pctl(0, nil);
	sys->sleep(delay);
	timeout <-= 1;
}

serve(ctxt: ref Draw->Context, bridge: ref ZX->Window, done: chan of Zxresult, workers: ref WindowWorkers): Zxresult
{
	w: ref Wmclient->Window;
	presented, popup, stripimage: ref Draw->Image;
	stripnext := 0;
	panelstate := bridge.panel;
	desk := bridge.desktop;
	bound := 0;
	deskreply := chan of int;
	daytime: Daytime;
	if(desk != nil)
		daytime = load Daytime Daytime->PATH;
	panelfont: ref Font;
	panelready := 0;
	changed := chan of int;
	if(panelstate != nil)
		changed = panelstate.changed;
	nokbd := chan of int;
	noptr := chan of ref Draw->Pointer;
	noctl := chan of string;
	notitle := chan of string;
	notimeout := chan of int;
	nostdin := chan of Stdin;
	stream := chan of Stdin;
	stdin := nostdin;
	data: array of byte;
	offset := 0;
	readcount := -2;
	kbd := nokbd;
	ptr := noptr;
	ctl := noctl;
	title := notitle;
	timeout := notimeout;
	queue := ref Events(array[QueueSize] of ZX->Input, 0, 0, 0);
	bounds: Draw->Rect;
	buttons := 0;
	pointerpos := Point(0, 0);
	pointerknown := 0;
	contentpress := 0;
	contentrelease := 0;
	releasepos: Point;
	sample: ref Image;
	waiting := 0;
	closed := 0;
	tasked := 0;
	timedpointer := 0;
	rawkeys := 0;
	held := array[KeyCount] of { * => 0 };

	for(;;){
		if(waiting && (queue.count != 0 || closed)){
			kill(workers.deadline);
			workers.deadline = 0;
			timeout = notimeout;
			if(closed)
				bridge.input = event(ZX->Closed, bounds);
			else
				bridge.input = queue.pop();
			waiting = 0;
			bridge.reply <-= 1;
		}
		alt {
		r := <-done =>
			forget(w, popup, panelstate != nil);
			return r;
		<-changed =>
			queue.push(event(ZX->Redraw, bounds));
		op := <-bridge.request =>
			ok := !closed;
			case op {
			ZX->DesktopBind =>
				ok = desk != nil && w == nil && !closed;
				bound = ok;
			ZX->DesktopCapture =>
				ok = bound && !closed;
				if(ok){
					desk.request <-= (bridge, op, deskreply);
					ok = <-deskreply;
					if(ok)
						capturelaunchers(desk, panelstate);
				}
			ZX->DesktopLaunch =>
				id := bridge.input.button;
				ok = bound && w != nil && !closed && hasentry(panelstate, ZX->PanelMenu, id);
				if(ok)
					alt { panelstate.action <-= (ZX->PanelMenu, id) =>; * => ok = 0; }
			ZX->DesktopChrome =>
				ok = bound && w != nil && !closed;
				if(ok){
					desk.request <-= (bridge, op, deskreply);
					layers := <-deskreply;
					ok = layers != 0;
					if(layers == 2 && presented != nil){
						paintchrome(desk, bounds, bounds, presented);
						w.image.flush(Draw->Flushnow);
					}
				}
			ZX->DesktopWindowAction or ZX->DesktopAction =>
				ok = bound && w != nil && !closed;
				if(ok){
					desk.request <-= (bridge, op, deskreply);
					ok = <-deskreply;
				}
				bridge.input.text = nil;
			ZX->DesktopTimezone =>
				bridge.input.key = 0;
				if(daytime != nil)
					bridge.input.key = daytime->local(daytime->now()).tzoff;
			ZX->Open =>
				ok = w == nil && !closed && (desk == nil || bound);
				if(ok){
					# New engines request timestamps using the unused input key at Open.
					timedpointer = bridge.input.key != 0;
					controls := Wmclient->Resize;
					if(bridge.hide)
						controls |= Wmclient->Hide;
					if(panelstate != nil)
						controls = Wmclient->Plain;
					w = wm->window(ctxt, bridge.title, controls);
					if(panelstate == nil){
						w.reshape(((0, 0), (bridge.width, bridge.height)));
						bounds = ((0, 0), (bridge.width, bridge.height));
					}else{
						r := w.displayr;
						if(desk == nil)
							r = panelrect(r);
						w.reshape(r);
						panelstate.width = w.displayr.dx();
						panelstate.height = w.displayr.dy();
						ok = w.wmctl("start control") == nil;
						if(ok && desk != nil)
							ok = w.wmctl("desktop layer") == nil;
						if(ok){
							w.onscreen("exact");
							if(desk == nil)
								panelfont = Font.open(w.display, "*default*");
							ok = w.image != nil && (desk != nil || panelfont != nil);
							if(ok){
								w.startinput("kbd" :: "ptr" :: nil);
								rawkeys = w.wmctl("start keyevent") == nil;
								kbd = w.ctxt.kbd;
								ptr = w.ctxt.ptr;
								bounds = w.image.r;
								queue.push(event(ZX->Resize, bounds));
							}
						}
					}
					ctl = w.ctxt.ctl;
					title = w.ctl;
				}
			ZX->Buffer or ZX->OpaqueBuffer =>
				ok = w != nil && !closed;
				if(ok){
					if(stripimage != nil){
						stripimage = bridge.image = nil;
						stripnext = 0;
					}
					size := Draw->Point(bridge.width, bridge.height);
					format := RGBAbytes;
					if(op == ZX->OpaqueBuffer)
						format = RGBbytes;
					if(bridge.image == nil || bridge.image.chans.desc != format.desc || !bridge.image.r.size().eq(size))
						bridge.image = w.display.newimage(((0, 0), size), format, 0, Draw->Nofill);
					ok = bridge.image != nil;
				}else if(closed)
					ok = 2;
			ZX->StripBuffer =>
				ok = w != nil && !closed;
				if(ok){
					size := Draw->Point(bridge.width, bridge.height);
					if(stripimage == nil || !stripimage.r.size().eq(size)){
						stripnext = 0;
						if(bridge.input.y == 0)
							stripimage = w.display.newimage(((0, 0), size), RGBbytes, 0, Draw->Nofill);
						else
							stripimage = nil;
					}
					ok = stripimage != nil && (presented == stripimage || bridge.input.y == stripnext || bridge.input.y == 0);
					if(ok)
						bridge.image = stripimage;
				}else if(closed)
					ok = 2;
			ZX->Present or ZX->PresentStrip =>
				ok = w != nil && !closed;
				if(ok && w.image == nil){
					w.onscreen(nil);
					if(w.image != nil){
						w.startinput("kbd" :: "ptr" :: nil);
						rawkeys = w.wmctl("start keyevent") == nil;
						kbd = w.ctxt.kbd;
						ptr = w.ctxt.ptr;
						kind := ZX->Redraw;
						if(!bounds.size().eq(w.image.r.size()))
							kind = ZX->Resize;
						bounds = w.image.r;
						queue.push(event(kind, bounds));
					}
				}
				if(ok && op == ZX->PresentStrip && presented != stripimage){
					stripnext = bridge.input.y + bridge.input.height;
					if(stripnext < bridge.height){
						bridge.reply <-= 1;
						continue;
					}
				}
				if(ok && w.image != nil && bounds.size().eq(bridge.image.r.size())){
					region := bounds;
					if(op == ZX->PresentStrip && presented == stripimage){
						region.min.y += bridge.input.y;
						region.max.y = region.min.y + bridge.input.height;
					}
					if(desk != nil)
						paintchrome(desk, bounds, region, bridge.image);
					ok = paintregion(w, bridge.image, region);
					if(ok){
						(presented, bridge.image) = (bridge.image, nil);
						if(desk != nil && !panelready){
							panelready = 1;
							panelstate.ready <-= 1;
						}
					}
				}
				else if(closed)
					ok = 1; # deliver close on the next Event
				else if(w.image == nil)
					ok = 0;
			ZX->Event =>
				if(queue.count || closed || bridge.wait > 0){
					waiting = 1;
					if(!queue.count && !closed){
						timeout = chan[1] of int;
						pid := chan of int;
						spawn waitdeadline(bridge.wait, timeout, pid);
						workers.deadline = <-pid;
					}
					continue;
				}
				bridge.input = event(ZX->Idle, bounds);
			ZX->Poll =>
				if(closed){
					bridge.stdinlen = -1;
				}else{
					if(bridge.stdin == nil){
						bridge.stdin = array[ZX->StdinChunk] of byte;
						pid := chan of int;
						spawn readstdin(stream, pid);
						workers.reader = <-pid;
						stdin = stream;
					}
					n := min(bridge.stdinlen, readcount - offset);
					bridge.stdinlen = n;
					if(n > 0){
						bridge.stdin[0:] = data[offset:offset+n];
						offset += n;
						if(offset == readcount){
							stdin = stream;
							readcount = -2;
							offset = 0;
							data = nil;
						}
					}
				}
				ok = 1;
			ZX->SetTasked =>
				ok = !closed && w != nil && w.image != nil;
				if(ok && tasked != bridge.tasked){
					c := "untask";
					if(bridge.tasked)
						c = "task";
					ok = w.wmctl(c) == nil;
					if(ok){
						tasked = visibility(queue, w.image.r, bridge.tasked);
						contentpress = contentrelease = 0;
					}
				}
			ZX->SetTitle =>
				ok = !closed && w != nil;
				if(ok)
					w.settitle(bridge.title);
			ZX->Launch =>
				payload := bridge.input.text;
				bridge.input.text = nil;
				ok = !closed && w != nil && launchwindow(ctxt, payload);
			ZX->ResizeWindow =>
				bridge.input.kind = 0;
				ok = !closed && !tasked && w != nil && w.image != nil;
				if(ok){
					size := Draw->Point(bridge.width, bridge.height);
					if(!bounds.size().eq(size)){
						r := w.screenr((bounds.min, bounds.min.add(size)));
						ok = w.wmctl(sys->sprint("!reshape . -1 %d %d %d %d onscreen", r.min.x, r.min.y, r.max.x, r.max.y)) == nil;
						if(ok)
							bounds = reshapeevent(w, presented, queue, bounds);
					}
				}
			ZX->SetCursor =>
				spec := bridge.input.text;
				bridge.input.text = nil;
				ok = !closed && w != nil && w.image != nil && w.wmctl(spec) == nil;
			ZX->SampleGuestPointer =>
				# A drag must start inside this window. The release sample is consumed once.
				ok = !closed && !tasked && panelstate == nil && w != nil && w.image != nil && (contentpress || contentrelease);
				if(ok){
					screen := w.display.image;
					point := pointerpos;
					if(!contentpress){
						point = releasepos;
						contentrelease = 0;
					}
					ok = screen != nil && point.in(screen.r);
					if(ok){
						if(sample == nil)
							sample = w.display.newimage(((0, 0), (1, 1)), Draw->RGB24, 0, Draw->Nofill);
						if(sample != nil){
							sample.draw(sample.r, screen, nil, point);
							pixel := array[3] of byte;
							if(sample.readpixels(sample.r, pixel) == len pixel)
								bridge.input.key = (int pixel[2] << 16) | (int pixel[1] << 8) | int pixel[0];
						}
					}
				}
			ZX->PanelPopup =>
				ok = !closed && panelstate != nil && w != nil && w.image != nil;
				if(ok){
					dx := bridge.input.x;
					dy := bridge.input.y;
					r := w.image.r;
					if(dx == 0 && dy == 0){
						if(popup != nil)
							w.wmctl("delete shell-popup");
						popup = nil;
					}else if(dx > 0 && dy > 0 && dx <= r.dx() && dy <= r.min.y - w.displayr.min.y){
						q := ((r.min.x, r.min.y - dy), (r.min.x + dx, r.min.y));
						if(popup == nil || !popup.r.eq(q))
							popup = wmlib->reshape(w.ctxt, "shell-popup", q, popup, "exact");
						ok = popup != nil && popup.r.eq(q);
					}else
						ok = 0;
					if(popup != nil)
						r.min.y = popup.r.min.y;
					if(!r.eq(bounds)){
						bounds = r;
						queue.push(event(ZX->Resize, bounds));
					}
				}
			ZX->PanelPaint =>
				label := bridge.input.text;
				bridge.input.text = nil;
				ok = !closed && panelstate != nil && w != nil && w.image != nil;
				if(ok){
					p := bounds.min.add((bridge.input.x, bridge.input.y));
					r := Rect(p, p.add((bridge.input.width, bridge.input.height)));
					color := w.display.color(bridge.input.key);
					ok = color != nil;
					if(ok){
						paintpanel(w.image, panelfont, color, r, label);
						if(popup != nil)
							paintpanel(popup, panelfont, color, r, label);
					}
				}
			ZX->PanelFlush =>
				ok = !closed && panelstate != nil && w != nil && w.image != nil;
				if(ok){
					w.image.flush(Draw->Flushnow);
					if(!panelready){
						panelready = 1;
						panelstate.ready <-= 1;
					}
				}
			ZX->PanelChoose =>
				ok = !closed && panelstate != nil && w != nil;
				if(ok){
					kind := bridge.input.x;
					id := bridge.input.y;
					ok = hasentry(panelstate, kind, id);
					if(ok && kind == ZX->PanelTask){
						ok = w.wmctl(sys->sprint("ctl %d untask", id)) == nil;
						if(ok)
							w.wmctl(sys->sprint("ctl %d kbdfocus 1", id));
					}else if(ok)
						panelstate.action <-= (kind, id);
				}
			ZX->Close =>
				forget(w, popup, panelstate != nil);
				popup = nil;
				w = nil;
				kbd = nokbd;
				ptr = noptr;
				ctl = noctl;
				title = notitle;
				presented = stripimage = bridge.image = nil;
				stdin = nostdin;
				stopreader(workers);
				closed = 1;
				ok = 1;
			}
			bridge.reply <-= ok;
		(readcount, data) = <-stdin =>
			stdin = nostdin;
			if(readcount <= 0)
				workers.reader = 0;
		<-timeout =>
			workers.deadline = 0;
			timeout = notimeout;
			waiting = 0;
			bridge.input = event(ZX->Idle, bounds);
			bridge.reply <-= 1;
		c := <-ctl or c = <-title =>
			if(rawkeys && len c >= 9 && c[:9] == "keyevent "){
				keyevent(queue, held, bounds, c[9:]);
				continue;
			}
			if(rawkeys && c == "haskbdfocus 0")
				releasekeys(queue, held, bounds);
			if(c == "exit"){
				forget(w, popup, panelstate != nil);
				popup = nil;
				w = nil;
				kbd = nokbd;
				ptr = noptr;
				ctl = noctl;
				title = notitle;
				stdin = nostdin;
				stopreader(workers);
				closed = 1;
				continue;
			}
			if(panelstate != nil){
				(n, fields) := sys->tokenize(c, " ");
				if(n == 0)
					continue;
				case hd fields {
				"request" or "delclient" =>
					panelstate.control <-= c;
					continue;
				"newclient" =>
					continue;
				"rect" =>
					w.wmctl(c);
					if(popup != nil)
						w.wmctl("delete shell-popup");
					popup = nil;
					w.reshape(panelrect(w.displayr));
					if(w.image != nil){
						bounds = w.image.r;
						panelstate.width = bounds.dx();
					panelstate.height = w.displayr.dy();
						panelstate.generation++;
						queue.push(event(ZX->Resize, bounds));
					}
					continue;
				"haskbdfocus" =>
					panelstate.focused = n == 2 && hd tl fields == "1";
					queue.push(event(ZX->Redraw, bounds));
					continue;
				}
			}
			w.wmctl(c);
			if(panelstate != nil){
				if(desk != nil && w.image != nil && c != nil && c[0] == '!')
					bounds = reshapeevent(w, presented, queue, bounds);
				continue;
			}
			if(c == "task" && !tasked){
				tasked = visibility(queue, bounds, 1);
				contentpress = contentrelease = 0;
			}else if(c == "untask" && tasked)
				tasked = visibility(queue, bounds, 0);
			if(w.image != nil && (c == "raise" || (c != nil && c[0] == '!')))
				bounds = reshapeevent(w, presented, queue, bounds);
		p := <-ptr =>
			if(!w.pointer(*p)){
				if((p.buttons & 1) == 0 && (buttons & 1) != 0){
					contentrelease = contentpress;
					releasepos = p.xy;
					contentpress = 0;
				}else if((p.buttons & 1) != 0 && (buttons & 1) == 0){
					contentpress = p.xy.in(bounds);
					contentrelease = 0;
				}
				e := event(ZX->Move, bounds);
				e.x = p.xy.x - bounds.min.x;
				e.y = p.xy.y - bounds.min.y;
				if(timedpointer)
					e.key = p.msec;
				wheel := p.buttons & ~buttons & (WheelUp | WheelDown);
				if((!pointerknown || p.xy.x != pointerpos.x || p.xy.y != pointerpos.y) &&
				   ((p.buttons ^ buttons) & (WheelUp | WheelDown)) == 0)
					queue.push(e);
				if(wheel != 0){
					scroll := e;
					scroll.kind = ZX->Wheel;
					scroll.key = 0;
					if(wheel & WheelUp){
						scroll.button = 1000;
						queue.push(scroll);
					}
					if(wheel & WheelDown){
						scroll.button = -1000;
						queue.push(scroll);
					}
				}
				for(i := 0; i < 3; i++){
					bit := 1 << i;
					if((p.buttons ^ buttons) & bit){
						e.kind = ZX->Up;
						if(p.buttons & bit)
							e.kind = ZX->Down;
						e.button = i + 1;
						queue.push(e);
					}
				}
				buttons = p.buttons;
				pointerpos = p.xy;
				pointerknown = 1;
			}
		k := <-kbd =>
			e := event(ZX->Key, bounds);
			if(!rawkeys){
				e.key = keycode(k);
				if(e.key != 0)
					queue.push(e);
			}
			if(k >= ' ' && k != 127 && (k < 16re000 || k > 16rf8ff)){
				e.kind = ZX->Text;
				e.key = 0;
				e.text[0] = k;
				queue.push(e);
			}
		}
	}
}

launchwindow(ctxt: ref Draw->Context, payload: string): int
{
	start := 0;
	program: string;
	args: list of string;
	count := 0;
	for(i := 0; i < len payload; i++){
		if(payload[i] != 0)
			continue;
		word := payload[start:i];
		if(start == 0)
			program = word;
		else{
			if(++count > 64)
				return 0;
			args = word :: args;
		}
		start = i+1;
	}
	if(count == 0 || start != len payload || program == nil)
		return 0;
	argv: list of string;
	for(; args != nil; args = tl args)
		argv = hd args :: argv;
	if(hd argv == nil)
		return 0;
	# Keep relative filenames distinct from built-in modules and zxrun options.
	if(program[0] != '/' && program[0] != '#')
		program = "./" + program;
	file := program;
	if(len program >= 3 && program[len program-3:] == ".zx"){
		fd := sys->open(program, Sys->OREAD);
		if(fd == nil)
			return 0;
		(n, info) := sys->fstat(fd);
		if(n < 0 || info.mode & Sys->DMDIR)
			return 0;
		file = "/dis/zxrun.dis";
		argv = hd argv :: "-c" :: "-w" :: program :: tl argv;
	}
	app := load Wm file;
	if(app == nil)
		return 0;
	started := chan of int;
	spawn launchchild(ctxt, app, argv, started);
	return <-started;
}

launchchild(ctxt: ref Draw->Context, app: Wm, argv: list of string, started: chan of int)
{
	ok := sys->pctl(Sys->NEWPGRP|Sys->FORKFD, nil) >= 0;
	started <-= ok;
	if(ok)
		app->init(ctxt, argv);
}

min(a, b: int): int
{
	if(a < b)
		return a;
	return b;
}

visibility(queue: ref Events, bounds: Draw->Rect, tasked: int): int
{
	e := event(ZX->Visibility, bounds);
	e.button = tasked;
	queue.push(e);
	return tasked;
}

panelrect(screen: Draw->Rect): Draw->Rect
{
	screen.min.y = screen.max.y - PanelHeight;
	return screen;
}

capturelaunchers(desk: ref ZX->Desktop, panelstate: ref ZX->Panel)
{
	count := 0;
	rows := panelstate.rows[:panelstate.count];
	for(i := 0; i < len rows; i++)
		if(rows[i].kind == ZX->PanelMenu && rows[i].label != nil)
			count++;
	catalog := array[count] of ZX->PanelEntry;
	j := 0;
	for(i = 0; i < len rows; i++)
		if(rows[i].kind == ZX->PanelMenu && rows[i].label != nil)
			catalog[j++] = rows[i];
	desk.launchers = catalog;
	desk.generation += panelstate.generation;
}

hasentry(panelstate: ref ZX->Panel, kind, id: int): int
{
	if(id <= 0 || (kind != ZX->PanelMenu && kind != ZX->PanelTask))
		return 0;
	for(i := 0; i < panelstate.count; i++){
		e := panelstate.rows[i];
		if(e.kind == kind && e.id == id)
			return 1;
	}
	return 0;
}

forget(w: ref Wmclient->Window, popup: ref Draw->Image, controller: int)
{
	if(w != nil && controller)
		w.wmctl("endcontrol");
	if(w != nil && popup != nil)
		w.wmctl("delete shell-popup");
	if(w != nil && w.image != nil)
		w.wmctl("delete .");
}

paintpanel(dst: ref Image, font: ref Font, color: ref Image, r: Rect, label: string)
{
	(clip, visible) := r.clip(dst.r);
	if(!visible)
		return;
	if(label == nil){
		dst.draw(clip, color, nil, (0, 0));
		return;
	}
	if(!r.min.in(clip))
		return;
	for(n := len label; n > 0; n--){
		if(font.width(label[:n]) <= clip.dx()){
			p := r.min.add((0, (r.dy() - font.height) / 2));
			dst.text(p, color, (0, 0), font, label[:n]);
			return;
		}
	}
}

paintchrome(desk: ref ZX->Desktop, bounds, region: Draw->Rect, source: ref Draw->Image)
{
	for(i := 0; i < len desk.chrome; i++){
		img := desk.chrome[i];
		if(img != nil){
			(clip, visible) := img.r.clip(region);
			if(visible)
				img.draw(clip, source, nil, source.r.min.add(clip.min.sub(bounds.min)));
		}
	}
}

paint(w: ref Wmclient->Window, source: ref Draw->Image): int
{
	if(w.image == nil || source == nil)
		return 0;
	return paintregion(w, source, w.image.r);
}

paintregion(w: ref Wmclient->Window, source: ref Draw->Image, region: Draw->Rect): int
{
	w.image.draw(region, source, nil, source.r.min.add(region.min.sub(w.image.r.min)));
	w.image.flush(Draw->Flushnow);
	return 1;
}

reshapeevent(w: ref Wmclient->Window, presented: ref Draw->Image, queue: ref Events, bounds: Draw->Rect): Draw->Rect
{
	kind := ZX->Redraw;
	if(!bounds.size().eq(w.image.r.size()))
		kind = ZX->Resize;
	paint(w, presented);
	queue.push(event(kind, w.image.r));
	return w.image.r;
}

event(kind: int, r: Draw->Rect): ZX->Input
{
	return (kind, 0, 0, 0, 0, 0, r.dx(), r.dy(), nil);
}

keyevent(queue: ref Events, held: array of int, bounds: Draw->Rect, message: string)
{
	(n, args) := sys->tokenize(message, " ");
	if(n != 3)
		return;
	if(hd args == "r"){
		releasekeys(queue, held, bounds);
		return;
	}
	key := int hd tl args;
	modifiers := int hd tl tl args;
	if(key <= 0 || key >= len held || modifiers < 0 || modifiers > 7)
		return;
	e := event(ZX->Key, bounds);
	case hd args {
	"d" => held[key] = 1;
	"u" =>
		if(!held[key])
			return;
		held[key] = 0;
		e.kind = ZX->Keyup;
	* => return;
	}
	e.key = key;
	e.modifiers = modifiers;
	queue.push(e);
}

releasekeys(queue: ref Events, held: array of int, bounds: Draw->Rect)
{
	for(key := 1; key < len held; key++){
		if(held[key]){
			held[key] = 0;
			e := event(ZX->Keyup, bounds);
			e.key = key;
			queue.push(e);
		}
	}
}

Events.push(q: self ref Events, e: ZX->Input)
{
	# Redraw uses the latest shell state. Keep a burst of invalidations from
	# delaying pointer and keyboard events behind repeated full repaints.
	if(e.kind == ZX->Redraw && q.redraw)
		return;
	if(e.kind == ZX->Move && q.count != 0){
		last := (q.head + q.count - 1) % QueueSize;
		if(q.ring[last].kind == ZX->Move){
			q.ring[last] = e;
			return;
		}
	}
	if(q.count == QueueSize)
		q.pop();
	q.ring[(q.head+q.count) % QueueSize] = e;
	q.count++;
	if(e.kind == ZX->Redraw)
		q.redraw = 1;
}

Events.pop(q: self ref Events): ZX->Input
{
	e := q.ring[q.head];
	q.head = (q.head+1) % QueueSize;
	q.count--;
	if(e.kind == ZX->Redraw)
		q.redraw = 0;
	return e;
}

keycode(k: int): int
{
	if(k >= 'a' && k <= 'z')
		return k - 'a' + 'A';
	case k {
	' ' to '~' => return k;
	Keyboard->Esc => return 256;
	'\r' or '\n' => return 257;
	'\t' or Keyboard->BackTab => return 258;
	'\b' => return 259;
	Keyboard->Ins => return 260;
	Keyboard->Del or 127 => return 261;
	Keyboard->Right => return 262;
	Keyboard->Left => return 263;
	Keyboard->Down => return 264;
	Keyboard->Up => return 265;
	Keyboard->Pgup => return 266;
	Keyboard->Pgdown => return 267;
	Keyboard->Home => return 268;
	Keyboard->End => return 269;
	(Keyboard->KF|1) to (Keyboard->KF|12) => return 289 + k - Keyboard->KF;
	}
	return 0;
}
