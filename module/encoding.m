Encoding: module
{
	BASE64PATH:	con "/zx/lib/encoding/base64.dis";
	BASE32PATH:	con "/zx/lib/encoding/base32.dis";
	BASE32APATH:	con "/zx/lib/encoding/base32a.dis";
	BASE16PATH:	con "/zx/lib/encoding/base16.dis";

	enc:	fn(a: array of byte): string;
	dec:	fn(s: string): array of byte;
#	deca:	fn(a: array of byte): array of byte;
};
