# File plot window from Inferno appl/math/gr.b. See NOTICE.
frame .fc
frame .fc.b
label .fc.b.xy -text {0 0}
pack .fc.b.xy -side right -padx 0 -pady 0
pack .fc.b -fill x -padx 0 -pady 0
canvas .fc.c -relief sunken -bd 2 -width 480 -height 384 -bg white
pack .fc.c -fill both -expand 1 -padx 0 -pady 0
pack .fc -fill both -expand 1 -padx 0 -pady 0
bind .fc.c <ButtonPress-1> {.fc.b.xy configure -text [graph0_at %x %y]}
