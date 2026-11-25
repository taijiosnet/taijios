Strcache: module {
	PATH: con "/zx/ebook/./strcache.dis";
	init:		fn(n: int);
	cache:	fn(s: string): string;
	flush:	fn(): string;
};
