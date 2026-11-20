canvas .c -width 160 -height 130 -background white -borderwidth 2 -relief flat
pack .c
.c create rectangle 12 12 95 95 -fill red -outline red -tags {base group}
.c create rectangle 60 42 121 91 -fill blue -outline blue -tags {top group}
.c create text 12 112 -anchor w -text Leaf -tags {leaf}
.c bind base <Enter> {EMIT {enter base %b}}
.c bind base <Leave> {EMIT {leave base %b}}
.c bind top <Enter> {EMIT {enter top %b}}
.c bind top <Leave> {EMIT {leave top %b}}
.c bind all <Button-3> {EMIT {all right %b %x %y %W %%}}
.c bind all <Motion-Button-3> {}
.c bind group <Button-3> {EMIT {group right %b}}
.c bind group <Motion-Button-3> {}
.c bind 2 <Button-3> {EMIT {top right %b}}
.c bind 2 <Motion-Button-3> {}
.c bind 1 <Button-3> {EMIT {base right %b}}
.c bind 1 <Motion-Button-3> {}
.c bind 1 <Motion-Button-2> {EMIT {base drag %b}}
.c bind 2 <Button-1> {EMIT {top single %b}}
.c bind 2 <Double-Button-1> {EMIT {top double %b}}
.c bind 1 <Button-1> {EMIT {base single %b}}
.c bind 1 <Double-Button-1> {EMIT {base double %b}}
.c bind 2 <ButtonRelease-1> {EMIT {top release %b}}
.c bind 2 <Button-2> {EMIT {delete top %b}; .c delete 2}
.c bind leaf <Button-2> {EMIT {text %b}}
EMIT ready
