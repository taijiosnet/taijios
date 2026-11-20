# LINPACK controls adapted from Inferno appl/math/linbench.b. See NOTICE.
frame .b
button .b.Run -text Run -command linbench_run
entry .b.N -width 10w
.b.N insert 0 200
pack .b.Run .b.N -side left
pack .b -anchor w
frame .d
listbox .d.f -width 35w -height 150 -selectmode single -yscrollcommand {.d.fscr set}
scrollbar .d.fscr -command {.d.f yview}
pack .d.f .d.fscr -expand 1 -fill y -side right -padx 0
pack .d -side top
focus .b.N
update
