# Continued comments hide the next physical line. \
noSuchCommand
set name {a b}; set label "before:${name}:[lindex [list first {last item}] end]"
puts $label
puts prefix-[lindex [list a b] 1]-${name}
puts {one\
      two}
puts "\[not a command\] \$name"
puts [llength [list {} {a b} {$name} {x{y}}]]
set saved [list {} "a\"b" "{unbalanced" "trail\\" {a;b} {$name}]
puts [join $saved |]
puts [lrange $saved end-1 end]
puts [lindex {} 0]
puts [llength [list]]
puts [string equal {} {}]
puts [string range abcdef 1 end-1]
proc formatItem {item {prefix ID} args} {
    return [list "$prefix:$item" [llength $args]]
}
puts [formatItem {a b}]
puts [formatItem x Y more even-more]
proc down {n} {
    if {$n <= 0} {return base}
    return "[down [expr {$n - 1}]]:$n"
}
puts [down 3]
proc redefine {} {proc redefine {} {return new}; return old}
puts [redefine]
puts [redefine]
set outer outside
proc local {} {set outer inside; return $outer}
puts [local]
puts $outer
set i 0; set gathered {}
while {1} {
    incr i
    if {$i == 2} {continue} elseif {$i == 4} {break}
    lappend gathered $i
}
foreach {letter number} {a 1 b 2 c} {lappend gathered "$letter$number"}
puts $gathered
set total 0
for {set i 0} {$i < 4} {incr i} {
    if {$i == 2} {continue}
    incr total $i
}
puts $total
puts [expr {2 + 3 * (7 - 5)}]
puts [expr {-7 / 3}]
puts [expr {-7 % 3}]
puts [expr {-2147483648}]
puts [catch {expr {2147483647 + 1}} message]
puts $message
puts [catch {expr {1 / 0}} message]
puts $message
puts [catch {set missing} message]
puts $message
puts [catch {lindex "\{" 0} message]
puts $message
puts [catch {eval "set x \[list \[list a\]"} message]
puts $message
puts [catch {error intentional} message]
puts $message
puts [catch {return retained} message]
puts $message
set expressionText {1 + 2}
puts [catch {expr {$expressionText}} message]
puts $message
