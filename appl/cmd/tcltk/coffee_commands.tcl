scale .range -orient horizontal -from -1.5 -to 3.5 -resolution 0.5 -showvalue 0 -command {send stdout changed}
.range get
.range set 2.875
.range get
.range set -9
.range get
.range cget -orient
.range cget -resolution
.range configure -from 5 -to -4 -bigincrement 1
.range set -7
.range get
.range set 18
.range get
panel .image -bd 3 -relief flat
.image cget -bd
.image cget -relief
.image dirty
.image dirty 0 0 400 300
pack .range .image -side top -anchor w
update
