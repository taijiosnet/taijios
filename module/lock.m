Lock: module
{
	PATH:	con "/zx/lib/lock.dis";

	Semaphore: adt {
		c: chan of int;
		obtain:	fn(nil: self ref Semaphore);
		release: fn(nil: self ref Semaphore);
		new: fn(): ref Semaphore;
	};
	
	init: fn();
};
