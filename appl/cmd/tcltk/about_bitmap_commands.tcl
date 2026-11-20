frame .f -bg black -borderwidth 2 -relief ridge
.f cget -background
.f cget -bd
.f cget -relief
label .b -bg black -bitmap @/icons/inferno.bit
.b cget -bitmap
label .version -label {Inferno version} -fg #ff5500 -bg black
.version cget -text
.version cget -foreground
pack .b .version -in .f
pack .f -ipadx 4 -ipady 2
pack propagate . 0
pack propagate .
image create bitmap splash -file @/icons/inferno.bit
image type splash
image width splash
image height splash
image names
label .copy -image splash
.copy cget -image
image delete splash
image width splash
.copy cget -image
label .missing -bitmap @/icons/missing-about-bitmap.bit
label .plain
.plain cget -bitmap
.plain cget -image
.plain cget -relief
.plain cget -borderwidth
.plain cget -foreground
.plain cget -background
.b configure -bitmap {}
.b cget -bitmap
.copy configure -image {}
.copy cget -image
pack .f -in .f
image create bitmap empty
image width empty
image height empty
image names
image delete empty
