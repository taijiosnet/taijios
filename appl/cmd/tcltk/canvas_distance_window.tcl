canvas .c -width 10c -height .6i -borderwidth 1m -relief sunken -background red -font /fonts/misc/latin1.8x13.font
.c create text 1c .25i -anchor nw -text {Directory Browser}
.c bind 1 <ButtonPress-1> {.c configure -width 7.999c -height 36.2p; puts [%W cget -height]}
pack .c
update
puts [.c cget -width]
