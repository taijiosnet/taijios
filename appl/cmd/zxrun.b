implement Zxrun;

include "sys.m";
	sys: Sys;
include "draw.m";
	draw: Draw;
	Display, Image, Point, Rect: import draw;
include "tk.m";
include "wmclient.m";
	wm: Wmclient;
	Window: import wm;
include "timers.m";
	timers: Timers;
	Timer: import timers;
include "keyboard.m";
include "zx.m";

Zxrun: module
{
	init:	fn(ctxt: ref Draw->Context, args: list of string);
};

Zxresult: type (big, int, string);
QueueSize: con 64;
RGBAbytes: con Draw->Chans(16r48281808);

Events: adt {
	ring: array of ZX->Input;
	head, count: int;
	push: fn(q: self ref Events, e: ZX->Input);
	pop: fn(q: self ref Events): ZX->Input;
};

init(ctxt: ref Draw->Context, args: list of string)
{
	sys = load Sys Sys->PATH;
	stderr := sys->fildes(2);
	path: string;
	window := 0;
	if(args != nil && tl args != nil){
		args = tl args;
		if(hd args == "-w" && tl args != nil){
			window = 1;
			args = tl args;
		}
		if(tl args == nil)
			path = hd args;
	}
	if(path == nil){
		sys->fprint(stderr, "usage: zxrun [-w] file.zx\n");
		raise "fail:usage";
	}

	zx := load ZX ZX->PATH;
	if(zx == nil){
		sys->fprint(stderr, "zxrun: ZX runtime unavailable: %r\n");
		raise "fail:zx";
	}

	value: big;
	status: int;
	problem: string;
	if(window)
		(value, status, problem) = runwindow(zx, ctxt, path);
	else
		(value, status, problem) = zx->run(path);
	if(status < 0){
		sys->fprint(stderr, "zxrun: %s: %s\n", path, problem);
		raise "fail:zx";
	}
	if(status > 0 && sys->print("%bd\n", value) < 0){
		sys->fprint(stderr, "zxrun: write error: %r\n");
		raise "fail:write error";
	}
}

runwindow(zx: ZX, ctxt: ref Draw->Context, path: string): Zxresult
{
	if(ctxt == nil || ctxt.wm == nil)
		return (big 0, -1, "graphical ZX needs a window manager context");
	draw = load Draw Draw->PATH;
	wm = load Wmclient Wmclient->PATH;
	timers = load Timers Timers->PATH;
	if(draw == nil || wm == nil || timers == nil)
		return (big 0, -1, "cannot load graphical ZX support");
	wm->init();
	timers->init(10);
	bridge := ref ZX->Window;
	bridge.request = chan[1] of int;
	bridge.reply = chan[1] of int;
	pid := chan of int;
	done := chan[1] of Zxresult;
	spawn engine(zx, path, bridge, pid, done);
	worker := <-pid;
	{
		result := serve(ctxt, bridge, done);
		timers->shutdown();
		return result;
	} exception e {
	"*" =>
		fd := sys->open("/prog/" + string worker + "/ctl", Sys->OWRITE);
		if(fd != nil)
			sys->fprint(fd, "kill");
		timers->shutdown();
		return (big 0, -1, e);
	}
}

engine(zx: ZX, path: string, bridge: ref ZX->Window, pid: chan of int, done: chan of Zxresult)
{
	pid <-= sys->pctl(0, nil);
	{
		done <-= zx->runwindow(path, bridge);
	} exception e {
	"*" =>
		done <-= (big 0, -1, e);
	}
}

serve(ctxt: ref Draw->Context, bridge: ref ZX->Window, done: chan of Zxresult): Zxresult
{
	w: ref Wmclient->Window;
	presented: ref Draw->Image;
	nokbd := chan of int;
	noptr := chan of ref Draw->Pointer;
	noctl := chan of string;
	notitle := chan of string;
	notimeout := chan of int;
	kbd := nokbd;
	ptr := noptr;
	ctl := noctl;
	title := notitle;
	timeout := notimeout;
	timer: ref Timers->Timer;
	queue := ref Events(array[QueueSize] of ZX->Input, 0, 0);
	bounds: Draw->Rect;
	buttons := 0;
	waiting := 0;
	closed := 0;

	for(;;){
		if(waiting && (queue.count != 0 || closed)){
			if(timer != nil)
				timer.stop();
			timer = nil;
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
			forget(w);
			return r;
		op := <-bridge.request =>
			ok := !closed;
			case op {
			ZX->Open =>
				ok = w == nil && !closed;
				if(ok){
					w = wm->window(ctxt, bridge.title, Wmclient->Resize);
					w.reshape(((0, 0), (bridge.width, bridge.height)));
					bounds = ((0, 0), (bridge.width, bridge.height));
					ctl = w.ctxt.ctl;
					title = w.ctl;
				}
			ZX->Buffer =>
				ok = w != nil && !closed;
				if(ok){
					size := Draw->Point(bridge.width, bridge.height);
					if(bridge.image == nil || !bridge.image.r.size().eq(size))
						bridge.image = w.display.newimage(((0, 0), size), RGBAbytes, 0, Draw->Nofill);
					ok = bridge.image != nil;
				}else if(closed)
					ok = 2;
			ZX->Present =>
				ok = w != nil && !closed;
				if(ok && w.image == nil){
					w.onscreen(nil);
					if(w.image != nil){
						w.startinput("kbd" :: "ptr" :: nil);
						kbd = w.ctxt.kbd;
						ptr = w.ctxt.ptr;
						kind := ZX->Redraw;
						if(!bounds.size().eq(w.image.r.size()))
							kind = ZX->Resize;
						bounds = w.image.r;
						queue.push(event(kind, bounds));
					}
				}
				if(ok && w.image != nil && bounds.size().eq(bridge.image.r.size())){
					ok = paint(w, bridge.image);
					if(ok)
						(presented, bridge.image) = (bridge.image, presented);
				}
				else if(closed)
					ok = 1; # deliver close on the next Event
				else if(w.image == nil)
					ok = 0;
			ZX->Event =>
				if(queue.count || closed || bridge.wait > 0){
					waiting = 1;
					if(!queue.count && !closed){
						timer = timers->Timer.start(bridge.wait);
						timeout = timer.timeout;
					}
					continue;
				}
				bridge.input = event(ZX->Idle, bounds);
			ZX->Close =>
				forget(w);
				w = nil;
				kbd = nokbd;
				ptr = noptr;
				ctl = noctl;
				title = notitle;
				presented = bridge.image = nil;
				closed = 1;
				ok = 1;
			}
			bridge.reply <-= ok;
		<-timeout =>
			timer = nil;
			timeout = notimeout;
			waiting = 0;
			bridge.input = event(ZX->Idle, bounds);
			bridge.reply <-= 1;
		c := <-ctl or c = <-title =>
			if(c == "exit"){
				forget(w);
				w = nil;
				kbd = nokbd;
				ptr = noptr;
				ctl = noctl;
				title = notitle;
				closed = 1;
				continue;
			}
			w.wmctl(c);
			if(w.image != nil && (c == "raise" || (c != nil && c[0] == '!'))){
				kind := ZX->Redraw;
				if(!bounds.size().eq(w.image.r.size()))
					kind = ZX->Resize;
				bounds = w.image.r;
				paint(w, presented);
				queue.push(event(kind, bounds));
			}
		p := <-ptr =>
			if(!w.pointer(*p)){
				e := event(ZX->Move, bounds);
				e.x = p.xy.x - bounds.min.x;
				e.y = p.xy.y - bounds.min.y;
				queue.push(e);
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
			}
		k := <-kbd =>
			e := event(ZX->Key, bounds);
			e.key = keycode(k);
			if(e.key != 0)
				queue.push(e);
			if(k >= ' ' && k != 127 && (k < 16re000 || k > 16rf8ff)){
				e.kind = ZX->Text;
				e.key = 0;
				e.text[0] = k;
				queue.push(e);
			}
		}
	}
}

forget(w: ref Wmclient->Window)
{
	if(w != nil && w.image != nil)
		w.wmctl("delete .");
}

paint(w: ref Wmclient->Window, source: ref Draw->Image): int
{
	if(w.image == nil || source == nil)
		return 0;
	w.image.draw(w.image.r, source, nil, source.r.min);
	w.image.flush(Draw->Flushnow);
	return 1;
}

event(kind: int, r: Draw->Rect): ZX->Input
{
	return (kind, 0, 0, 0, 0, 0, r.dx(), r.dy(), nil);
}

Events.push(q: self ref Events, e: ZX->Input)
{
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
}

Events.pop(q: self ref Events): ZX->Input
{
	e := q.ring[q.head];
	q.head = (q.head+1) % QueueSize;
	q.count--;
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
