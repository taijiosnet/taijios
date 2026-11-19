implement Zxrun;

include "sys.m";
include "draw.m";
include "zx.m";

Zxrun: module
{
	init:	fn(nil: ref Draw->Context, args: list of string);
};

init(nil: ref Draw->Context, args: list of string)
{
	sys := load Sys Sys->PATH;
	stderr := sys->fildes(2);
	if(args == nil || tl args == nil || tl tl args != nil){
		sys->fprint(stderr, "usage: zxrun file.zx\n");
		raise "fail:usage";
	}

	zx := load ZX ZX->PATH;
	if(zx == nil){
		sys->fprint(stderr, "zxrun: ZX runtime unavailable: %r\n");
		raise "fail:zx";
	}

	path := hd tl args;
	(value, status, problem) := zx->run(path);
	if(status < 0){
		sys->fprint(stderr, "zxrun: %s: %s\n", path, problem);
		raise "fail:zx";
	}
	if(status > 0 && sys->print("%bd\n", value) < 0){
		sys->fprint(stderr, "zxrun: write error: %r\n");
		raise "fail:write error";
	}
}
