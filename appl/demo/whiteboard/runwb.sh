#!/zx/sh.dis
load std
pctl forkns
memfs /tmp
cp /zx/demo/whiteboard/whiteboard.dis /tmp
/zx/auxi/wbsrv /tmp $2
grid/register -a resource Whiteboard -a size 600x400 -a name $1 {export /tmp}
