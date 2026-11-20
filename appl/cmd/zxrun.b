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
Stdin: type (int, array of byte);
QueueSize: con 64;
KeyCount: con 350;
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
	command := 0;
	newgroup := 0;
	if(args != nil)
		args = tl args;
	while(args != nil && (hd args == "-w" || hd args == "-c" || hd args == "-p")){
		case hd args {
		"-w" => window = 1; args = tl args;
		"-c" => command = 1; args = tl args;
		"-p" => newgroup = 1; args = tl args;
		}
	}
	if(args == nil || hd args == nil){
		sys->fprint(stderr, "usage: zxrun [-c] [-w] [-p] file.zx [args ...]\n");
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
		(value, status, problem) = runwindow(zx, ctxt, path, args);
	else if(command || args != nil)
		(value, status, problem) = zx->runargs(path, args);
	else
		(value, status, problem) = zx->run(path);
	if(status < 0){
		sys->fprint(stderr, "zxrun: %s: %s\n", path, problem);
		raise "fail:zx";
	}
	if(command){
		if(status > 0 && value != big 0)
			raise sys->sprint("fail:%bd", value);
		return;
	}
	if(status > 0 && sys->print("%bd\n", value) < 0){
		sys->fprint(stderr, "zxrun: write error: %r\n");
		raise "fail:write error";
	}
}

runwindow(zx: ZX, ctxt: ref Draw->Context, path: string, args: list of string): Zxresult
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
	spawn engine(zx, path, args, bridge, pid, done);
	worker := <-pid;
	{
		result := serve(ctxt, bridge, done);
		stopreader(bridge);
		timers->shutdown();
		return result;
	} exception e {
	"*" =>
		kill(worker);
		stopreader(bridge);
		timers->shutdown();
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

stopreader(bridge: ref ZX->Window)
{
	kill(bridge.reader);
	bridge.reader = 0;
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

serve(ctxt: ref Draw->Context, bridge: ref ZX->Window, done: chan of Zxresult): Zxresult
{
	w: ref Wmclient->Window;
	presented: ref Draw->Image;
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
	timer: ref Timers->Timer;
	queue := ref Events(array[QueueSize] of ZX->Input, 0, 0);
	bounds: Draw->Rect;
	buttons := 0;
	waiting := 0;
	closed := 0;
	tasked := 0;
	rawkeys := 0;
	held := array[KeyCount] of { * => 0 };

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
					controls := Wmclient->Resize;
					if(bridge.hide)
						controls |= Wmclient->Hide;
					w = wm->window(ctxt, bridge.title, controls);
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
			ZX->Poll =>
				if(closed){
					bridge.stdinlen = -1;
				}else{
					if(bridge.stdin == nil){
						bridge.stdin = array[ZX->StdinChunk] of byte;
						pid := chan of int;
						spawn readstdin(stream, pid);
						bridge.reader = <-pid;
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
					if(ok)
						tasked = visibility(queue, w.image.r, bridge.tasked);
				}
			ZX->Close =>
				forget(w);
				w = nil;
				kbd = nokbd;
				ptr = noptr;
				ctl = noctl;
				title = notitle;
				presented = bridge.image = nil;
				stdin = nostdin;
				stopreader(bridge);
				closed = 1;
				ok = 1;
			}
			bridge.reply <-= ok;
		(readcount, data) = <-stdin =>
			stdin = nostdin;
			if(readcount <= 0)
				bridge.reader = 0;
		<-timeout =>
			timer = nil;
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
				forget(w);
				w = nil;
				kbd = nokbd;
				ptr = noptr;
				ctl = noctl;
				title = notitle;
				stdin = nostdin;
				stopreader(bridge);
				closed = 1;
				continue;
			}
			w.wmctl(c);
			if(c == "task" && !tasked)
				tasked = visibility(queue, bounds, 1);
			else if(c == "untask" && tasked)
				tasked = visibility(queue, bounds, 0);
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
