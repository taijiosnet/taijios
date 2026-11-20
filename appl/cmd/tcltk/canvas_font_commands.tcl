canvas .c -font /fonts/misc/latin1.8x13.font
.c cget -font
.c create text 10 50 -anchor w -text {file  café Àg}
.c bbox 1
.c coords 1
.c itemcget 1 -font
.c create text 75 60 -font /fonts/misc/latin1.6x13.font -text {Café 7}
.c bbox 2
.c itemcget 2 -font
.c configure -font /fonts/misc/latin1.6x10.font
.c cget -font
.c bbox 1
.c itemcget 1 -font
.c create text 20 60 -anchor nw -text {Café}
.c bbox 3
.c itemconfigure 1 -font /fonts/misc/latin1.6x10.font
.c bbox 1
.c itemconfigure 1 -font /absent.font
.c bbox 1
.c itemcget 1 -font
.c itemconfigure 2 -text {Âβ}
.c bbox 2
.c create text 39 41 -text {}
.c bbox 4
.c delete 1
.c delete all
destroy .c
canvas .c -font /fonts/misc/latin1.8x13.font
.c create text 10 20 -anchor nw -text {dir}
.c bbox 1
.c itemcget 1 -font
