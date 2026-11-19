frame .input
frame .view
entry .input.e -bg white
button .input.search -text Search -command submit
label .view.result -text {Query}
button .close -text Close -command {destroy .}

proc submit {} {
    set query [.input.e get]
    .view.result configure -text $query
    puts $query
}

pack .input.search -side right -padx 0 -pady 0
pack .input.e -expand 1 -fill x -padx 0 -pady 0
pack .view.result -padx 0 -pady 0
pack .input -fill x
pack .view -fill both -expand 1
pack .close -side bottom
bind .input.e <Key-\n> submit
focus .input.e
