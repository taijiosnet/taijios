checkbutton .follow -text Scroll -variable follow -onvalue enabled -offvalue paused -command {variable follow}
variable follow
.follow select
variable follow
.follow toggle
variable follow
.follow deselect
variable follow
checkbutton .same -text {Follow log} -variable follow -onvalue enabled -offvalue paused
.same cget -variable
.same select
.follow toggle
variable follow
variable follow enabled
.same toggle
variable follow
.follow invoke
variable follow
scrollbar .bar -command {.log yview}
.bar cget -orient
.bar cget -command
.bar set 0.125 0.875
.bar get
.bar set -0.5 1.5
.bar get
text .log -height 7c -yscrollcommand {.bar set}
.log cget -yscrollcommand
.log insert end {hello from Log Window}
.log get 1.0 1.5
.log delete 1.0 end
pack .follow .same -anchor w
pack .bar -side left -fill y
pack .log -fill both -expand 1
update
.bar get
