implement Toolbar;
include "sys.m";
	sys: Sys;
include "draw.m";
	draw: Draw;
	Screen, Display, Image, Rect, Point, Wmcontext, Pointer: import draw;
include "tk.m";
	tk: Tk;
include "tkclient.m";
	tkclient: Tkclient;
include "sh.m";
	shell: Sh;
	Listnode, Context: import shell;
include "string.m";
	str: String;
include "arg.m";
include "zx.m";
	zx: ZX;
include "zxrun.m";

myselfbuiltin: Shellbuiltin;

include "toolbar.m";

MAXCONSOLELINES:	con 1024;
PanelCapacity: con 192;
PanelImage: con "/dis/wm/desktop_panel.zx";

panelstate: ref ZX->Panel;
menucommands: array of string;
menuserial: int;

# execute this if no menu items have been created
# by the init script.
defaultscript :=
	"{menu shell " +
		"{{autoload=std; load $autoload; pctl newpgrp; wm/sh}&}}";

tbtop: ref Tk->Toplevel;
screenr: Rect;

badmodule(p: string)
{
	sys->fprint(stderr(), "toolbar: cannot load %s: %r\n", p);
	raise "fail:bad module";
}

init(ctxt: ref Draw->Context, argv: list of string)
{
	run(ctxt, argv, nil, PanelImage);
}

desktop(ctxt: ref Draw->Context, service: ref ZX->Desktop, path: string)
{
	run(ctxt, "toolbar" :: nil, service, path);
}

run(ctxt: ref Draw->Context, argv: list of string, service: ref ZX->Desktop, path: string)
{
	sys  = load Sys Sys->PATH;
	zx = load ZX ZX->PATH;
	draw = load Draw Draw->PATH;
	if(draw == nil)
		badmodule(Draw->PATH);
	tk   = load Tk Tk->PATH;
	if(tk == nil)
		badmodule(Tk->PATH);

	str = load String String->PATH;
	if(str == nil)
		badmodule(String->PATH);

	tkclient = load Tkclient Tkclient->PATH;
	if(tkclient == nil)
		badmodule(Tkclient->PATH);
	tkclient->init();

	shell = load Sh Sh->PATH;
	if (shell == nil)
		badmodule(Sh->PATH);
	arg := load Arg Arg->PATH;
	if (arg == nil)
		badmodule(Arg->PATH);

	myselfbuiltin = load Shellbuiltin "$self";
	if (myselfbuiltin == nil)
		badmodule("$self(Shellbuiltin)");

	sys->pctl(Sys->NEWPGRP|Sys->FORKNS, nil);

	sys->bind("#p", "/prog", sys->MREPL);
	sys->bind("#s", "/chan", sys->MBEFORE);

	arg->init(argv);
	arg->setusage("toolbar [-s] [-p] [-l]");
	legacy := 0;
	startmenu := 1;
#	ownsnarf := (sys->open("/chan/snarf", Sys->ORDWR) == nil);
	ownsnarf := sys->stat("/chan/snarf").t0 < 0;
	while((c := arg->opt()) != 0){
		case c {
		's' =>
			startmenu = 0;
		'l' =>
			legacy = 1;
		'p' =>
			ownsnarf = 1;
		* =>
			arg->usage();
		}
	}
	argv = arg->argv();
	arg = nil;

	if (ctxt == nil){
		sys->fprint(sys->fildes(2), "toolbar: must run under a window manager\n");
		raise "fail:no wm";
	}

	exec := chan of string;
	task := chan of string;

	paneldone := chan of string;
	panelcontrol := chan of string;
	panelaction := chan of (int, int);
	kinput := chan of int;
	pinput := chan of ref Pointer;
	wcontrol := chan of string;
	wrequest := chan of string;
	if(startmenu && !legacy && (service != nil || sys->stat(path).t0 >= 0)){
		zxrun := load Zxrun Zxrun->PATH;
		if(zxrun != nil){
			state := ref ZX->Panel(array[PanelCapacity] of ZX->PanelEntry, 0, 0, 0, 0, 0,
				chan[1] of int, chan[16] of (int, int), chan[32] of string, chan[1] of int);
			if(service != nil)
				state.changed = service.changed;
			spawn renderpanel(zxrun, ctxt, state, service, path, paneldone);
			alt {
			<-state.ready =>
				panelstate = state;
				menucommands = array[PanelCapacity] of string;
				panelcontrol = state.control;
				panelaction = state.action;
			e := <-paneldone =>
				if(service != nil)
					fatal("Rill desktop exited before drawing: " + e);
				sys->fprint(stderr(), "toolbar: desktop panel: %s\n", e);
			}
		}
	}
	if(panelstate == nil){
		if(service != nil)
			fatal("Rill desktop launcher unavailable");
		tbtop = toolbar(ctxt, startmenu, exec, task);
		tkclient->startinput(tbtop, "ptr" :: "control" :: nil);
		layout(tbtop);
		kinput = tbtop.ctxt.kbd;
		pinput = tbtop.ctxt.ptr;
		wcontrol = tbtop.ctxt.ctl;
		wrequest = tbtop.wreq;
	}

	shctxt := Context.new(ctxt);
	shctxt.addmodule("wm", myselfbuiltin);

	snarfIO: ref Sys->FileIO;
	if(ownsnarf){
		snarfIO = sys->file2chan("/chan", "snarf");
		if(snarfIO == nil)
			fatal(sys->sprint("cannot make /chan/snarf: %r"));
	}else
		snarfIO = ref Sys->FileIO(chan of (int, int, int, Sys->Rread), chan of (int, array of byte, int, Sys->Rwrite));
	sync := chan of string;
	spawn consoleproc(ctxt, sync, service != nil);
	if ((err := <-sync) != nil)
		fatal(err);

	setupfinished := chan of int;
	donesetup := 0;
	spawn setup(shctxt, setupfinished);

	snarf: array of byte;
#	write("/prog/"+string sys->pctl(0, nil)+"/ctl", "restricted"); # for testing
	for(;;) alt{
	k := <-kinput =>
		tk->keyboard(tbtop, k);
	m := <-pinput =>
		tk->pointer(tbtop, *m);
	s := <-wcontrol or s = <-wrequest or s = <-panelcontrol =>
		wmctl(tbtop, s);
	e := <-paneldone =>
		fatal("desktop panel exited: " + e);
	(kind, id) := <-panelaction =>
		if(donesetup && kind == ZX->PanelMenu){
			i := panellookup(kind, id);
			if(i >= 0 && menucommands[i] != nil){
				{ shctxt.run(ref Listnode(nil, menucommands[i]) :: nil, 0); }
				exception { "fail:*" => ; }
			}
		}
	s := <-exec =>
		# guard against parallel access to the shctxt environment
		if (donesetup){
			{
 				shctxt.run(ref Listnode(nil, s) :: nil, 0);
			} exception {
			"fail:*" =>	;
			}
		}
	detask := <-task =>
		deiconify(detask);
	(off, data, nil, wc) := <-snarfIO.write =>
		if(wc == nil)
			break;
		if (off == 0)			# write at zero truncates
			snarf = data;
		else {
			if (off + len data > len snarf) {
				nsnarf := array[off + len data] of byte;
				nsnarf[0:] = snarf;
				snarf = nsnarf;
			}
			snarf[off:] = data;
		}
		wc <-= (len data, "");
	(off, nbytes, nil, rc) := <-snarfIO.read =>
		if(rc == nil)
			break;
		if (off >= len snarf) {
			rc <-= (nil, "");		# XXX alt
			break;
		}
		e := off + nbytes;
		if (e > len snarf)
			e = len snarf;
		rc <-= (snarf[off:e], "");	# XXX alt
	donesetup = <-setupfinished =>
		;	
	}
}

renderpanel(zxrun: Zxrun, ctxt: ref Draw->Context, state: ref ZX->Panel, service: ref ZX->Desktop, path: string, done: chan of string)
{
	(value, status, problem) := zxrun->desktop(ctxt, path, state, service);
	if(problem == nil && status > 0)
		problem = sys->sprint("exit %bd", value);
	done <-= problem;
}

panelchange()
{
	panelstate.generation++;
	alt { panelstate.changed <-= 1 =>; * =>; }
}

paneladd(kind, id: int, group, label, command: string): int
{
	if(panelstate.count == len panelstate.rows)
		return 0;
	i := panelstate.count++;
	panelstate.rows[i] = (kind, id, group, label);
	menucommands[i] = command;
	panelchange();
	return 1;
}

panelrequest(op, kind, id: int, reply: array of int): int
{
	if(zx == nil)
		return 0;
	request := array[4+2*panelstate.count] of int;
	request[0:] = array[] of {op, panelstate.count, kind, id};
	for(i := 0; i < panelstate.count; i++){
		e := panelstate.rows[i];
		(request[4+2*i], request[5+2*i]) = (e.kind, e.id);
	}
	return zx->wmcall(ZX->WindowPolicy, request, reply);
}

panellookup(kind, id: int): int
{
	reply := array[1] of int;
	if(panelrequest(ZX->WmPanelLookup, kind, id, reply)){
		i := reply[0];
		if(i == -1 || (i >= 0 && i < panelstate.count && panelstate.rows[i].kind == kind && panelstate.rows[i].id == id))
			return i;
	}
	for(i := 0; i < panelstate.count; i++)
		if(panelstate.rows[i].kind == kind && panelstate.rows[i].id == id)
			return i;
	return -1;
}

panelremove(kind, id: int)
{
	if(panelstate.count == 0)
		return;
	keep := array[panelstate.count] of int;
	ported := panelrequest(ZX->WmPanelRetain, kind, id, keep);
	at := 0;
	for(i := 0; i < panelstate.count; i++){
		e := panelstate.rows[i];
		if((ported && !keep[i]) || (!ported && e.kind == kind && (id == 0 || id == e.id)))
			continue;
		if(i != at){
			panelstate.rows[at] = e;
			menucommands[at] = menucommands[i];
		}
		at++;
	}
	if(at == panelstate.count)
		return;
	for(i = at; i < panelstate.count; i++){
		panelstate.rows[i] = (0, 0, nil, nil);
		menucommands[i] = nil;
	}
	panelstate.count = at;
	panelchange();
}

wmctl(top: ref Tk->Toplevel, c: string)
{
	args := str->unquoted(c);
	if(args == nil)
		return;
	n := len args;

	case hd args{
	"request" =>
		# request clientid args...
		if(n < 3)
			return;
		args = tl args;
		clientid := hd args;
		args = tl args;
		err := handlerequest(clientid, args);
		if(err != nil)
			sys->fprint(sys->fildes(2), "toolbar: bad wmctl request %#q: %s\n", c, err);
	"newclient" =>
		# newclient id
		;
	"delclient" =>
		# delclient id
		deiconify(hd tl args);
	"rect" =>
		if(top != nil){
			tkclient->wmctl(top, c);
			layout(top);
		}
	* =>
		if(top != nil)
			tkclient->wmctl(top, c);
	}
}

handlerequest(clientid: string, args: list of string): string
{
	n := len args;
	case hd args {
	"task" =>
		# task name
		if(n != 2)
			return "no task label given";
		iconify(clientid, hd tl args);
	"untask" or
	"unhide" =>
		deiconify(clientid);
	* =>
		return "unknown request";
	}
	return nil;
}

iconify(id, label: string)
{
	label = condenselabel(label);
	if(panelstate != nil){
		panelremove(ZX->PanelTask, int id);
		paneladd(ZX->PanelTask, int id, nil, label, nil);
		return;
	}
	e := tk->cmd(tbtop, "button .toolbar." +id+" -command {send task "+id+"} -takefocus 0");
	cmd(tbtop, ".toolbar." +id+" configure -text '" + label);
	if(e[0] != '!')
		cmd(tbtop, "pack .toolbar."+id+" -side left -fill y");
	cmd(tbtop, "update");
}

deiconify(id: string)
{
	if(panelstate != nil){
		panelremove(ZX->PanelTask, int id);
		return;
	}
	e := tk->cmd(tbtop, "destroy .toolbar."+id);
	if(e == nil){
		tkclient->wmctl(tbtop, sys->sprint("ctl %q untask", id));
		tkclient->wmctl(tbtop, sys->sprint("ctl %q kbdfocus 1", id));
	}
	cmd(tbtop, "update");
}

layout(top: ref Tk->Toplevel)
{
	r := top.screenr;
	h := 32;
	if(r.dy() < 480)
		h = tk->rect(top, ".b", Tk->Border|Tk->Required).dy();
	cmd(top, ". configure -x " + string r.min.x +
			" -y " + string (r.max.y - h) +
			" -width " + string r.dx() +
			" -height " + string h);
	cmd(top, "update");
	tkclient->onscreen(tbtop, "exact");
}

toolbar(ctxt: ref Draw->Context, startmenu: int,
		exec, task: chan of string): ref Tk->Toplevel
{
	(tbtop, nil) = tkclient->toplevel(ctxt, nil, nil, Tkclient->Plain);
	screenr = tbtop.screenr;

	cmd(tbtop, "button .b -text {XXX}");
	cmd(tbtop, "pack propagate . 0");

	tk->namechan(tbtop, exec, "exec");
	tk->namechan(tbtop, task, "task");
	cmd(tbtop, "frame .toolbar");
	if (startmenu) {
		cmd(tbtop, "menubutton .toolbar.start -menu .m -borderwidth 0 -bitmap vitasmall.bit");
		cmd(tbtop, "pack .toolbar.start -side left");
	}
	cmd(tbtop, "pack .toolbar -fill x");
	cmd(tbtop, "menu .m");
	return tbtop;
}

setup(shctxt: ref Context, finished: chan of int)
{
	ctxt := shctxt.copy(0);
	ctxt.run(shell->stringlist2list("run"::"/lib/wmsetup"::nil), 0);
	# if no items in menu, then create some.
	if(panelstate == nil){
		if(tk->cmd(tbtop, ".m type 0")[0] == '!')
			ctxt.run(shell->stringlist2list(defaultscript::nil), 0);
		cmd(tbtop, "update");
	}else if(menuserial == 0)
		ctxt.run(shell->stringlist2list(defaultscript::nil), 0);
	finished <-= 1;
}

condenselabel(label: string): string
{
	if(len label > 15){
		new := "";
		l := 0;
		while(len label > 15 && l < 3) {
			new += label[0:15]+"\n";
			label = label[15:];
			for(v := 0; v < len label; v++)
				if(label[v] != ' ')
					break;
			label = label[v:];
			l++;
		}
		label = new + label;
	}
	return label;
}

initbuiltin(ctxt: ref Context, nil: Sh): string
{
	if (tbtop == nil && panelstate == nil) {
		sys = load Sys Sys->PATH;
		sys->fprint(sys->fildes(2), "wm: cannot load wm as a builtin\n");
		raise "fail:usage";
	}
	ctxt.addbuiltin("menu", myselfbuiltin);
	ctxt.addbuiltin("delmenu", myselfbuiltin);
	ctxt.addbuiltin("error", myselfbuiltin);
	return nil;
}

whatis(nil: ref Sh->Context, nil: Sh, nil: string, nil: int): string
{
	return nil;
}

runbuiltin(c: ref Context, sh: Sh,
			cmd: list of ref Listnode, nil: int): string
{
	case (hd cmd).word {
	"menu" =>	return builtin_menu(c, sh, cmd);
	"delmenu" =>	return builtin_delmenu(c, sh, cmd);
	}
	return nil;
}

runsbuiltin(nil: ref Context, nil: Sh,
			nil: list of ref Listnode): list of ref Listnode
{
	return nil;
}

stderr(): ref Sys->FD
{
	return sys->fildes(2);
}

word(ln: ref Listnode): string
{
	if (ln.word != nil)
		return ln.word;
	if (ln.cmd != nil)
		return shell->cmd2string(ln.cmd);
	return nil;
}

menupath(title: string): string
{
	mpath := ".m."+title;
	for(j := 0; j < len mpath; j++)
		if(mpath[j] == ' ')
			mpath[j] = '_';
	return mpath;
}

builtin_menu(nil: ref Context, nil: Sh, argv: list of ref Listnode): string
{
	n := len argv;
	if (n < 3 || n > 4) {
		sys->fprint(stderr(), "usage: menu topmenu [ secondmenu ] command\n");
		raise "fail:usage";
	}
	primary := (hd tl argv).word;
	argv = tl tl argv;
	if(panelstate != nil){
		group: string;
		label := primary;
		if(n == 4){
			group = primary;
			label = (hd argv).word;
			argv = tl argv;
		}
		command := word(hd argv);
		if(command == nil)
			label = nil;
		if(!paneladd(ZX->PanelMenu, ++menuserial, group, label, command))
			return "desktop panel menu is full";
		return nil;
	}

	if (n == 3) {
		w := word(hd argv);
		if (len w == 0)
			cmd(tbtop, ".m insert 0 separator");
		else
			cmd(tbtop, ".m insert 0 command -label " + tk->quote(primary) +
				" -command {send exec " + w + "}");
	} else {
		secondary := (hd argv).word;
		argv = tl argv;

		mpath := menupath(primary);
		e := tk->cmd(tbtop, mpath+" cget -width");
		if(e[0] == '!') {
			cmd(tbtop, "menu "+mpath);
			cmd(tbtop, ".m insert 0 cascade -label "+tk->quote(primary)+" -menu "+mpath);
		}
		w := word(hd argv);
		if (len w == 0)
			cmd(tbtop, mpath + " insert 0 separator");
		else
			cmd(tbtop, mpath+" insert 0 command -label "+tk->quote(secondary)+
				" -command {send exec "+w+"}");
	}
	return nil;
}

builtin_delmenu(nil: ref Context, nil: Sh, nil: list of ref Listnode): string
{
	if(panelstate != nil){
		panelremove(ZX->PanelMenu, 0);
		return nil;
	}
	delmenu(".m");
	cmd(tbtop, "menu .m");
	return nil;
}

delmenu(m: string)
{
	for (i := int cmd(tbtop, m + " index end"); i >= 0; i--)
		if (cmd(tbtop, m + " type " + string i) == "cascade")
			delmenu(cmd(tbtop, m + " entrycget " + string i + " -menu"));
	cmd(tbtop, "destroy " + m);
}

getself(): Shellbuiltin
{
	return myselfbuiltin;
}

cmd(top: ref Tk->Toplevel, c: string): string
{
	s := tk->cmd(top, c);
	if (s != nil && s[0] == '!')
		sys->fprint(stderr(), "tk error on %#q: %s\n", c, s);
	return s;
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

con_cfg := array[] of
{
	"frame .cons",
	"scrollbar .cons.scroll -command {.cons.t yview}",
	"text .cons.t -width 60w -height 15w -bg white "+
		"-fg black -font /fonts/misc/latin1.6x13.font "+
		"-yscrollcommand {.cons.scroll set}",
	"pack .cons.scroll -side left -fill y",
	"pack .cons.t -fill both -expand 1",
	"pack .cons -expand 1 -fill both",
	"pack propagate . 0",
	"update"
};
nlines := 0;		# transcript length

consoleforward(data: array of byte, wc: Sys->Rwrite, fd: ref Sys->FD)
{
    if(wc == nil)
        return;
    n := sys->write(fd, data, len data);
    err: string;
    if(n < 0){
        n = 0;
        err = sys->sprint("%r");
    }
    wc <-= (n, err);
}

consolehost(out, err: ref Sys->FileIO)
{
    stdout := sys->fildes(1);
    stderr := sys->fildes(2);
    for(;;) alt {
    (nil, nil, nil, rc) := <-out.read or
    (nil, nil, nil, rc) = <-err.read =>
        if(rc != nil)
            rc <-= (nil, "inappropriate use of file");
    (nil, data, nil, wc) := <-out.write =>
        consoleforward(data, wc, stdout);
    (nil, data, nil, wc) := <-err.write =>
        consoleforward(data, wc, stderr);
    }
}

consoleproc(ctxt: ref Draw->Context, sync: chan of string, hostonly: int)
{
	iostdout := sys->file2chan("/chan", "wmstdout");
	if(iostdout == nil){
		sync <-= sys->sprint("cannot make /chan/wmstdout: %r");
		return;
	}
	iostderr := sys->file2chan("/chan", "wmstderr");
	if(iostderr == nil){
		sync <-= sys->sprint("cannot make /chan/wmstdout: %r");
		return;
	}

	sync <-= nil;
	if(hostonly){
		consolehost(iostdout, iostderr);
		return;
	}

	(top, titlectl) := tkclient->toplevel(ctxt, "", "Log", tkclient->Appl); 
	for(i := 0; i < len con_cfg; i++)
		cmd(top, con_cfg[i]);

	r := tk->rect(top, ".", Tk->Border|Tk->Required);
	cmd(top, ". configure -x " + string ((top.screenr.dx() - r.dx()) / 2 + top.screenr.min.x) +
				" -y " + string (r.dy() / 3 + top.screenr.min.y));

	tkclient->startinput(top, "ptr"::"kbd"::nil);
	tkclient->onscreen(top, "onscreen");
	tkclient->wmctl(top, "task");

	for(;;) alt {
	c := <-titlectl or
	c = <-top.wreq or
	c = <-top.ctxt.ctl =>
		if(c == "exit")
			c = "task";
		tkclient->wmctl(top, c);
	c := <-top.ctxt.kbd =>
		tk->keyboard(top, c);
	p := <-top.ctxt.ptr =>
		tk->pointer(top, *p);
	(nil, nil, nil, rc) := <-iostdout.read =>
		if(rc != nil)
			rc <-= (nil, "inappropriate use of file");
	(nil, nil, nil, rc) := <-iostderr.read =>
		if(rc != nil)
			rc <-= (nil, "inappropriate use of file");
	(nil, data, nil, wc) := <-iostdout.write =>
		conout(top, data, wc);
	(nil, data, nil, wc) := <-iostderr.write =>
		conout(top, data, wc);
		if(wc != nil)
			tkclient->wmctl(top, "untask");
	}
}

conout(top: ref Tk->Toplevel, data: array of byte, wc: Sys->Rwrite)
{
	if(wc == nil)
		return;

	s := string data;
	tk->cmd(top, ".cons.t insert end '"+ s);
	alt{
	wc <-= (len data, nil) =>;
	* =>;
	}

	for(i := 0; i < len s; i++)
		if(s[i] == '\n')
			nlines++;
	if(nlines > MAXCONSOLELINES){
		cmd(top, ".cons.t delete 1.0 " + string (nlines/4) + ".0; update");
		nlines -= nlines / 4;
	}

	tk->cmd(top, ".cons.t see end; update");
}
