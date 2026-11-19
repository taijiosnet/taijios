label .count -text {8 balls}
button .more -text {+1} -command {.count configure -text {9 balls}}
pack .count .more -side top -padx 8 -pady 5
.more invoke
.count cget -text
