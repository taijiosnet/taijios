set dir /build/tcl/channel-suite
set path $dir/created
puts "before=[file exists $path]"
set h [open $path w+ 0644]
puts $h hello
puts -nonewline $h world
flush $h
puts "length=[file size $path]:[tell $h]"
seek $h 0 start
puts "readline=<[gets $h]>:[tell $h]"
puts -nonewline $h XY
puts "position=[tell $h]"
seek $h 0 current
puts "remaining=<[read $h 10]>"
close $h
puts "types=[file exists $path]:[file isfile $path]:[file isdirectory $dir]"
set h [open $path w]
puts -nonewline $h ok
close $h
puts "truncated=[file size $path]"
puts "missing=[file exists $dir/missing]:[catch {file size $dir/missing}]"
puts "closed=[catch {tell $h}]"
puts "invalid=[catch {open $path w+ 08}]"
