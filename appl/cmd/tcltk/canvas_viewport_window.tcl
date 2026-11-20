frame .f
scrollbar .f.s -command {.f.c yview}
canvas .f.c -relief sunken -borderwidth 2 -background red -width 120 -height 80 -scrollregion {10 0 170 400} -yscrollincrement 25 -yscrollcommand {.f.s set}
image create bitmap folder -file dir.bit -maskfile dir.mask
.f.c create image 35 67 -image folder -anchor nw -tags folder
.f.c create image 90 168 -image folder -anchor nw
.f.c bind folder <ButtonPress-1> {puts {item %x %y}; puts [%W canvasy %Y]; puts [%W yview]; puts [.f.s get]}
.f.c bind folder <ButtonRelease-1> {puts [%W canvasy %Y 10]; puts [%W cget actwidth]; puts [.f.s cget actwidth]}
.f.c bind folder <ButtonPress-3> {%W configure -yscrollincrement 0; puts {fallback increment}}
pack .f.c -side left -padx 0 -pady 0
pack .f.s -side right -fill y -padx 0 -pady 0
pack .f
update
puts ready
