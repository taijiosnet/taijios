canvas .c -width 240 -height 45
.c cget -width
.c configure -height 75
.c cget -height
.c create rectangle 20 24 80 28 -fill red -outline {}
.c coords 1
.c bbox 1
.c coords 1 20 24 110 28
.c coords 1
.c bbox 1
.c create text 50 12 -anchor e -text 32M
.c coords 2
.c itemconfigure 2 -text 4096K
.c itemcget 2 -text
.c create text 60 22 -anchor w -fill red -text 42
.c itemcget 3 -text
update
