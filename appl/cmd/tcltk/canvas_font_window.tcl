canvas .c -width 180 -height 102 -borderwidth 2 -relief sunken -background red -font /fonts/misc/latin1.8x13.font
.c create text 10 11 -anchor nw -fill white -text {file  café Àg}
.c create text 100 46 -font /fonts/misc/latin1.6x13.font -fill black -text {Café β}
.c configure -font /fonts/misc/latin1.6x10.font
.c create text 100 73 -anchor w -fill #0000cc -text {gyp Café
Árbol j}
.c create text 16 96 -anchor nw -fill white -text {continued below}
.c bind 1 <ButtonPress-1> {puts [%W bbox 1]}
pack .c -padx 0 -pady 0
update
puts ready
