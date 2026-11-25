Script: module {
	PATH:	con "/zx/ip/ppp/script.dis";

	ScriptInfo: adt {
		path:			string;
		content:		list of string;
		timeout:		int;
		username:		string;
		password:		string;
	};
	
	execute:	fn( modem: Modem, m: ref Modem->Device, 
						scriptinfo: ref ScriptInfo );
};
