#!/zx/sh.dis
load std

port=$1
DIR=/zx/demo/lego
pctl forkns newpgrp

cd $DIR
if { firmdl $port /zx/demo/lego/styx.srec } {
	legolink $port
	memfs /tmp
	cd /tmp
	mount -o -A /net/legolink /n/remote
	$DIR/clockface /n/remote
	echo reset > clockface
	grid/register -a resource Robot -a name 'Lego Clock' {export /tmp}
}
