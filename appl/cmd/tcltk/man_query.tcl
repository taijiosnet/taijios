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
.view.t tag configure reference -underline 1
.view.t tag bind reference <ButtonRelease-1> {follow %x %y}
button .controls.up -text {Page Up} -command {.view.t yview scroll -1 pages}
button .controls.down -text {Page Down} -command {.view.t yview scroll 1 pages}
button .controls.close -text Close -command {destroy .}
label .controls.status -text {}

# Keep the interface usable by installed Man images that predate native page transfer.
if {[lsearch [info commands] manual_display] < 0} {
    proc manual_display {widget} {
        $widget delete 1.0 end
        $widget insert end [manual body]
        manual decorate $widget
    }
}

proc show {} {
    .heading configure -text [manual title]
    manual_display .view.t
    set match [manual matchfirst]
    if {![string equal $match {}]} { .view.t tag add sel $match [manual matchlast] }
    .view.t yview moveto [manual top]
    .controls.status configure -text {}
    .input.e delete 0 end
    .input.e insert 0 [manual query]
    .input.back configure -state [manual backstate]
    .input.forward configure -state [manual forwardstate]
}

proc follow {x y} {
    set target [manual reference .view.t "@$x,$y"]
    if {[string equal $target {}]} { return }
    manual open $target [lindex [.view.t yview] 0]
    show
}

proc find {query prefix} {
    set pattern [string range $query 1 end]
    if {[string equal $pattern {}]} { return }
    if {[string equal $prefix /]} {
        set direction -forwards
        set start [manual matchlast]
    } else {
        set direction -backwards
        set start [manual matchfirst]
    }
    if {[string equal $start {}]} { set start 1.0 }
    set match [.view.t search $direction -- $pattern $start]
    if {[string equal $match {}]} {
        .controls.status configure -text {No match}
        return
    }
    set end "$match+[manual length $pattern]c"
    manual remember $match $end
    .view.t tag remove sel 1.0 end
    .view.t tag add sel $match $end
    .view.t see $match
    .controls.status configure -text {}
}

proc navigate {direction} {
    set top [lindex [.view.t yview] 0]
    if {[string equal $direction open]} {
        set query [.input.e get]
        if {[string equal $query {}]} { return }
        set prefix [string index $query 0]
        if {[string equal $prefix /]} { find $query $prefix; return }
        if {[string equal $prefix ?]} { find $query $prefix; return }
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
pack .controls.status -fill x -pady 0 -padx 0
pack .input -fill x
pack .heading -fill x -pady 0
pack .controls -side bottom -fill x
pack .view -fill both -expand 1
bind .input.e <Key-\n> {navigate open}
focus .input.e
manual open man(1) 0
show
