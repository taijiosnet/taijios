canvas .c -width 158 -height 116 -borderwidth 2 -relief sunken -background red
pack .c
image create bitmap dir -file dir.bit -maskfile dir.mask
.c create image 45 35 -image dir -tags icon
.c create image 90 65 -anchor nw -image dir
image delete dir
image create bitmap dir -file file.bit -maskfile file.mask
.c create image 95 15 -anchor nw -image dir
image create bitmap glyph -maskfile file.mask
.c create image 15 70 -anchor nw -image glyph
image create bitmap offset -file SOURCE -maskfile MASK
.c create image 10 5 -anchor nw -image offset
.c bind 1 <Button-3> {EMIT {dir right}}
.c bind 1 <Button-2> {EMIT {dir removed}; .c delete 1}
EMIT ready
