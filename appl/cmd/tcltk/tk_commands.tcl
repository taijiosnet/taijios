label .count -text {8 balls}
button .more -text {+1} -command {.count configure -text {9 balls}}
pack .count .more -side top -padx 8 -pady 5
.more invoke
.count cget -text
frame .f
frame .f.input
entry .f.input.e -bg white
.f.input.e insert 0 {aé中z}
.f.input.e delete 2
.f.input.e icursor 1
.f.input.e insert insert {ß}
.f.input.e index end
.f.input.e index insert
.f.input.e get
pack .f.input.e -fill x -expand 1
pack .f.input -fill x
pack .f -side bottom -fill x
text .sample
.sample insert end {café naïve café}
.sample search -forwards -- café 1.1
.sample search -backwards -- café 1.11
focus .f.input.e
focus
