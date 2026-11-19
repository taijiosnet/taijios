# Manual browser interface adapted from appl/wm/man.b. See NOTICE.
frame .input
frame .view
frame .controls
entry .input.e -bg white
button .input.back -text Back -command {navigate back}
button .input.forward -text Next -command {navigate forward}
button .input.search -text Search -command {navigate open}
label .heading -text Manual
text .view.t
button .controls.up -text {Page Up} -command {.view.t yview scroll -1 pages}
button .controls.down -text {Page Down} -command {.view.t yview scroll 1 pages}
button .controls.close -text Close -command {destroy .}

proc show {} {
    .heading configure -text [manual title]
    .view.t delete 1.0 end
    .view.t insert end [manual body]
    .view.t yview moveto [manual top]
    .input.e delete 0 end
    .input.e insert 0 [manual query]
    .input.back configure -state [manual backstate]
    .input.forward configure -state [manual forwardstate]
}

proc navigate {direction} {
    set top [lindex [.view.t yview] 0]
    if {[string equal $direction open]} {
        set query [.input.e get]
        if {[string equal $query {}]} { return }
        manual open $query $top
    } else {
        manual $direction $top
    }
    show
}

pack .input.back .input.forward -side left -padx 2 -pady 0
pack .input.search -side right -padx 0 -pady 0
pack .input.e -expand 1 -fill x -padx 0 -pady 0
pack .view.t -padx 0 -pady 0 -fill both -expand 1
pack .controls.up .controls.down -side left -pady 0 -padx 2
pack .controls.close -side right -pady 0 -padx 2
pack .input -fill x
pack .heading -fill x -pady 0
pack .controls -side bottom -fill x
pack .view -fill both -expand 1
bind .input.e <Key-\n> {navigate open}
focus .input.e
manual open man(1) 0
show
