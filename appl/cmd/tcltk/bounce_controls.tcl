# Adapted from the toolbar of appl/wm/bounce.b. See ../../../NOTICE.
set balls 8
label .count -text "$balls balls"
button .less -text {-1} -command {
    if {$balls > 0} {incr balls -1}
    .count configure -text "$balls balls"
    puts [.count cget -text]
}
button .more -text {+1} -command {
    incr balls
    .count configure -text "$balls balls"
    puts [.count cget -text]
}
button .close -text Close -command {destroy .}
pack .count .less .more .close -side top
