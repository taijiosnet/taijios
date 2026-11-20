ZX: module
{
	PATH:	con "$ZX";

	# The integer is 1 for a returned value, 0 for void and -1 on error.
	# The string holds a runtime error or an optional name for a nonzero result.
	run:	fn(path: string): (big, int, string);
	runargs:	fn(path: string, args: list of string): (big, int, string);

	# Requests from the engine to the window process.
	Open, Event, Buffer, Present, Close, Poll, SetTasked, OpaqueBuffer, SetTitle, Launch, ResizeWindow, SetCursor: con iota;
	# Events returned to the program.
	Idle, Closed, Redraw, Resize, Move, Down, Up, Key, Keyup, Text, Visibility: con iota;
	Maxside: con 4096;
	Maxpixels: con 4194304;
	StdinChunk: con 4096;

	Input: adt {
		kind, x, y, button, key, modifiers, width, height: int;
		text: string;
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
	};

	runwindow:	fn(path: string, win: ref Window): (big, int, string);
	runwindowargs:	fn(path: string, args: list of string, win: ref Window): (big, int, string);
};
