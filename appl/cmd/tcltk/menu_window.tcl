puts [package require -exact Tk 0.1]
set auto_path [list /appl/cmd/tcltk/menu_package]
puts [package require MenuLabels]
menubutton .options -text Options -menu .options.popup
menu .options.popup
.options.popup add command -label Restart -command {.state configure -text [restart_label]; puts [restart_label]}
.options.popup add separator
.options.popup add command -label Disabled -state disabled -command {puts disabled-called}
label .state -text Idle
button .post -text Post -command {.options.popup post 96 30}
button .close -text Close -command {destroy .}
pack .options .state .post .close
