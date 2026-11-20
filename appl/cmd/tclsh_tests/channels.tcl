set f [open /build/tcl/channel-suite/input]
set other [open /build/tcl/channel-suite/input OREAD]
puts "handles=$f:$other"
puts "line=<[gets $f ignored]>:[info exists ignored]:[eof $f]"
puts "two=<[read $other 2]>"
close $other
puts "closed=[catch {read $other 1}]"
puts "second=<[read $f]>"
puts "partial=<[gets $f]>:[eof $f]"
puts "atend=<[read $f 1]>:[eof $f]"
seek $f -2 SEEKEND
puts "tail=<[read $f 20]>:[eof $f]"
seek $f 0 SEEKSTART
seek $f 1 SEEKRELA
puts "rewound=<[read -nonewline $f]>"
puts "wrong-origin=[catch {seek $f 0 sideways}]"
close $f
set w [open /build/tcl/channel-suite/existing OWRITE]
puts "reused=$w"
puts -nonewline $w xy
puts $w q
close $w
set v [open /build/tcl/channel-suite/existing ORDWR]
puts "written=<[read $v 10]>"
close $v
puts "missing=[catch {open /build/tcl/channel-suite/missing OWRITE}]"
puts "invalid=[catch {open /build/tcl/channel-suite/input bogus}]"
