# These commands run in both the shipped Limbo and Ziran interpreters.
puts "concat=<[concat {one two} {} {three four}]>"
puts "linsert=[linsert {one two three} 1 {four five}]"
puts "lreplace=[lreplace {one two three} 1 1 {four five}]"
puts "lsearch=[lsearch {one {two words} three} {two words}]"
puts "lsort=[lsort -decreasing {one five six three two four}]"
puts "split=<[split {a,,b,} ,]>"
puts "splitdefault=<[split { a  b }]>"
puts "string=<[string length café]>:<[string index café 3]>:<[string range abcde 0 2]>:<[string tolower CaFé]>"
puts "format=<[format %s hi]>:<[format %02x 15]>:<[format %03d 7]>"
set total 5
proc bump {amount} {global total; incr total $amount}
puts "global=[bump 3]:$total"
proc sample {value} {return $value}
puts "info=[info args sample]:[info exists total]:[info exists missing]:[sample yes]"
switch b {a {puts switch=a} b - c {puts switch=bc} default {puts switch=default}}
set data(word) 7
set data(other) 3
puts "array=[array size data]:$data(word):[set data(word)]:[info exists data(other)]:[info exists data(missing)]"
puts "keys=[lsort [array names data]]"
