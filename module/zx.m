ZX: module
{
	PATH:	con "$ZX";

	# The integer is 1 for a returned value, 0 for void and -1 on error.
	# The string holds a runtime error or an optional name for a nonzero result.
	run:	fn(path: string): (big, int, string);
	runargs:	fn(path: string, args: list of string): (big, int, string);

	# Window-manager policy requests use bounded integer buffers.
	PlacePolicy, WindowPolicy: con 1+iota;
	WmHit, WmRaise, WmLower, WmRemove, WmPanelLookup, WmPanelRetain, WmFit: con iota;
	wmcall:	fn(service: int, request, reply: array of int): int;

	# Requests from the engine to the window process.
	Open, Event, Buffer, Present, Close, Poll, SetTasked, OpaqueBuffer, SetTitle, Launch, ResizeWindow, SetCursor, PanelPopup, PanelChoose, PanelPaint, PanelFlush: con iota;
	DesktopBind, DesktopCapture, DesktopLaunch, DesktopWindowAction, DesktopAction, DesktopTimezone, DesktopChrome: con PanelFlush+1+iota;
	StripBuffer, PresentStrip: con DesktopChrome+1+iota;
	# Events returned to the program.
	Idle, Closed, Redraw, Resize, Move, Down, Up, Key, Keyup, Text, Visibility, Wheel: con iota;
	Maxside: con 4096;
	Maxpixels: con 4194304;
	StdinChunk: con 4096;

	Input: adt {
		kind, x, y, button, key, modifiers, width, height: int;
		text: string;
	};
	# Shell data is shared only with the panel engine. Commands stay in the
	# shell; the renderer receives display labels and sends opaque IDs.
	PanelMenu, PanelTask: con 1+iota;
	PanelEntry: adt {
		kind, id: int;
		group, label: string;
	};
	Panel: adt {
		rows: array of PanelEntry;
		generation, count, focused, width, height: int;
		changed: chan of int;
		action: chan of (int, int);
		control: chan of string;
		ready: chan of int;
	};

	DesktopWindow: adt {
		id, x, y, width, height, workspace, focused, minimized, maximized: int;
		title, appid: string;
	};
	Desktop: adt {
		# The window manager answers synchronously, using Window.input for arguments.
		request: chan of (ref Window, int, chan of int);
		changed: chan of int;
		generation, width, height, focused: int;
		windows: array of DesktopWindow;
		launchers: array of PanelEntry;
		regions: array of int;
		regioncount: int;
		chrome: array of ref Draw->Image;
		workspacecount, currentworkspace: int;
	};

	# Only one request can be active. The channels synchronize the shared fields.
	Window: adt {
		request, reply: chan of int;
		title: string;
		width, height, wait, message: int;
		image: ref Draw->Image;
		input: Input;
		hide, tasked: int;
		stdinlen, reader: int;
		stdin: array of byte;
		panel: ref Panel;
		desktop: ref Desktop;
	};

	runwindow:	fn(path: string, win: ref Window): (big, int, string);
	runwindowargs:	fn(path: string, args: list of string, win: ref Window): (big, int, string);
};
