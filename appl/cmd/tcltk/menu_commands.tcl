label .state -text Idle
menubutton .options -text Options -menu .options.popup
.options cget -text
.options cget -menu
.options configure -text {Game options} -state disabled
.options cget -text
.options cget -state
.options configure -state normal
menu .options.popup
.options.popup index end
.options.popup add command -label Restart -command {.state configure -text Restarted}
.options.popup add separator
.options.popup add command -text Quit -state disabled -command {.state configure -text Quit}
.options.popup index end
.options.popup index last
.options.popup index @0
.options.popup index @1
.options.popup index active
.options.popup index none
.options.popup index 20
.options.popup type 0
.options.popup type 1
.options.popup type 2
.options.popup entrycget 0 -text
.options.popup entrycget 2 -state
.options.popup yposition 0
.options.popup yposition 1
.options.popup yposition 2
.options.popup activate 0
.options.popup index active
.options.popup activate 2
.options.popup index active
.options.popup invoke 2
.state cget -text
.options.popup invoke 0
.state cget -text
.options.popup entryconfigure 2 -label Exit -state normal
.options.popup entrycget 2 -label
.options.popup invoke end
.state cget -text
.options.popup insert 1 command -label Help
.options.popup entrycget 1 -label
.options.popup delete 0 1
.options.popup type 0
.options.popup index end
.options.popup configure -borderwidth 3
.options.popup cget -bd
.options.popup post 40 60
.options.popup unpost
