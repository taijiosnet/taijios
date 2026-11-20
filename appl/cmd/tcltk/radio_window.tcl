package require -exact Tk 0.1
frame .top
menubutton .top.options -text Options -menu .choices
button .top.live -text Sync -command {variable direction south; puts synced}
button .top.close -text Close -command {destroy .}
pack .top.options -side left -padx 0 -pady 0
pack .top.close .top.live -side right -padx 0 -pady 0
radiobutton .north -text North -variable direction -value north -command {puts [variable direction]}
radiobutton .south -text South -variable direction -value south -command {puts [variable direction]}
radiobutton .locked -text Disabled -variable direction -value locked -state disabled -command {puts disabled-button}
radiobutton .flat -text Flat -variable direction -value flat -indicatoron 0 -command {puts [variable direction]}
menu .choices
.choices add radiobutton -text North -variable direction -value north -command {puts [format menu-%s [variable direction]]}
.choices add radiobutton -text Locked -variable direction -value locked -state disabled -command {puts disabled-entry}
.choices add checkbutton -text Walk -variable walk -onvalue on -offvalue off -command {puts [variable walk]}
.choices add command -text Done -command {puts done}
pack .top -fill x -padx 0 -pady 0
pack .north .south .locked .flat -anchor w -padx 0 -pady 0
puts ready
