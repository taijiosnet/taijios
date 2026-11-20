# Timing, load errors and frame inspection shared with shipped Inferno Tcl.
proc repetitions {} {
    set count 0
    set report [time {incr count} 3]
    puts "count=$count"
    puts "duration=$report"
    set code [catch {time {incr count; missingTimedCommand} 2} reason]
    puts "time-error=$code count=$count"
    set report [time {incr count} 0]
    puts "zero=$report count=$count"
    set report [time {incr count} -2]
    puts "negative=$report count=$count"
    set code [catch {time {} wrong} reason]
    puts "bad-count=$code"
}
proc libraryCheck {} {
    set loaded [load list]
    puts "load=<$loaded> words=[llength {a b}]"
    set code [catch {load missingFixture} reason]
    puts "missing-library=$code"
}
repetitions
libraryCheck
set shared global
set rows(first) root
proc inner {message} {
    global shared
    set rows(second) leaf
    set marker right
    dumpstack
}
proc outer {message} {
    set marker left
    inner $message
}
outer {two words}
puts done
