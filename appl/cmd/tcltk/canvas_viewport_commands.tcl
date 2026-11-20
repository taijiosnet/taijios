scrollbar .s -command {.c yview}
canvas .c -borderwidth 2
.c cget actwidth
.s cget actwidth
.c cget -actwidth
.s cget -actwidth
.c cget -scrollregion
.c cget -yscrollincrement
.c yview
.c configure -yscrollcommand {.s set}
.s get
.c cget -yscrollcommand
.c configure -scrollregion {0.25 20 120.5 420}
.c cget -scrollregion
.c yview
.s get
.c yview moveto .50009
.c yview
.s get
.c yview scroll 1 unit
.c yview
.s get
.c configure -yscrollincrement 25.5
.c cget -yscrollincrement
.c yview scroll -2 units
.c yview
.c yview scroll 2 pages
.c yview
.c yview moveto 2
.c yview
.s get
.c yview moveto -1
.c yview
.s get
.c configure -scrollregion {10 -100 -10 100}
.c yview moveto .25
.c yview
.s get
.c canvasy 25
.c canvasy 25 10
.c canvasy 25 0
.c configure -scrollregion {0 90 1 50}
.c yview
.s get
.c configure -yscrollincrement -0.25
.c cget -yscrollincrement
.c configure -scrollregion {0 0 120 10000}
.c yview moveto -.0001
.c yview
.c yview moveto 0
.c yview
.c configure -yscrollcommand {}
.s set .4 .7
.c yview moveto .2
.c yview
.s get
.c configure -yscrollcommand {.missing set}
.c yview
