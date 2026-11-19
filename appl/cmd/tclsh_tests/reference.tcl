# These commands run in both the Limbo and Ziran interpreters.
set who world
puts "hello $who"
puts {literal $who [set who]}
set words [list alpha {two words} omega]
puts [llength $words]
puts [lindex $words 1]
puts [string length $who]
proc add {a b} {return [expr {$a + $b}]}
puts [add 19 23]
set i 0
while {$i < 3} {incr i}
if {$i == 3} {puts loop-done} else {puts wrong-branch}
set failed [catch {noSuchCommand} problem]
puts $failed
puts $problem
puts reference-done
