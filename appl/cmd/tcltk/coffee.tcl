# Infernal Coffee controls adapted from appl/wm/coffee.b. See NOTICE.
frame .b
button .b.Stop -text Stop -command {coffee_pause}
scale .b.Rate -from 1 -to 10 -orient horizontal -showvalue 0 -command {coffee rate}
scale .b.Jitter -from 0 -to 5 -orient horizontal -showvalue 0 -command {coffee jitter}
scale .b.Skip -from 0 -to 25 -orient horizontal -showvalue 0 -command {coffee skip}
.b.Rate set 3
.b.Jitter set 2
.b.Skip set 5
pack .b.Stop .b.Rate .b.Jitter .b.Skip -side left
pack .b -anchor w -fill x
frame .f
panel .f.p -bd 3 -relief flat
pack .f.p -fill both -expand 1 -padx 0 -pady 0
pack .f -side bottom -fill both -expand 1 -padx 0 -pady 0
proc coffee_pause {} {
    coffee stop
    .b.Stop configure -text { Go } -command {coffee_resume}
}
proc coffee_resume {} {
    coffee go
    .b.Stop configure -text Stop -command {coffee_pause}
}
update
