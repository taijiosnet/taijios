Redirect: module
{
	PATH: con "/zx/svc/httpd/redirect.dis";

	redirect_init: fn(file : string);
	redirect: fn(path : string): string;
};
