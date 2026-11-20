# Log Window controls adapted from appl/wm/logwindow.b. See NOTICE.
frame .bf
checkbutton .bf.scroll -text Scroll -variable scroll
.bf.scroll select
checkbutton .bf.popup -text {Pop up} -variable popup
.bf.popup select
pack .bf.scroll .bf.popup -side left
frame .t
scrollbar .t.scroll -command {.t.t yview}
text .t.t -height 7c -yscrollcommand {.t.scroll set}
pack .t.scroll -side left -fill y
pack .t.t -fill both -expand 1
pack .bf -anchor w
pack .t -fill both -expand 1
