package require demo::twice 1
proc offset {value} {return [expr {[twice $value] + 1}]}
package provide demo::offset 2.0
