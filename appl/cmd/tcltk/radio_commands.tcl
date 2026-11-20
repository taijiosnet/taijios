radiobutton .red -text Red -command {variable calls red}
radiobutton .blue -label Blue -command {variable calls blue}
.red cget -variable
.red cget -value
.red cget -indicatoron
.blue cget -text
variable selectedButton
.red select
variable selectedButton
variable calls
.blue invoke
variable selectedButton
variable calls
.blue configure -state disabled -indicatoron 0
.blue cget -state
.blue cget -indicatoron
.red select
.blue invoke
variable selectedButton
variable calls
.blue select
variable selectedButton
.red deselect
variable selectedButton
radiobutton .empty -variable custom
.empty cget -value
.empty select
variable custom
radiobutton .explicit -value {}
.explicit cget -value
menu .options
.options add command -text Command
.options add radiobutton -text Red -variable colors -value R -command {variable calls menu-red}
.options add radiobutton -text Blue -variable colors -value B -command {variable calls menu-blue}
.options add checkbutton -text Walk -variable walk -onvalue on -offvalue off -command {variable calls walk}
.options add radiobutton -text Default
.options add checkbutton -text NoIndicator -indicatoron 0
.options type 1
.options type 3
.options entrycget 1 -variable
.options entrycget 1 -value
.options entrycget 4 -variable
.options entrycget 4 -value
.options entrycget 3 -onvalue
.options entrycget 3 -offvalue
.options entrycget 3 -indicatoron
.options entrycget 5 -indicatoron
.options yposition 0
.options yposition 1
.options yposition 2
.options yposition 3
.options yposition 4
.options yposition 5
variable walk
.options invoke 1
variable colors
variable calls
.options entryconfigure 2 -state disabled
.options invoke 2
variable colors
variable calls
.options invoke 3
variable walk
variable calls
.options invoke 3
variable walk
variable walk on
.options invoke 3
variable walk
variable callback returning
.red configure -command {variable callback}
.red invoke
.red invoke
variable selectedButton
.red configure -variable custom -value R
.blue configure -state normal -variable custom -value B -indicatoron 1
variable custom B
.blue cget -indicatoron
.red deselect
variable custom
.red select
variable custom
.options insert 1 checkbutton -label Extra -variable extra
.options type 1
.options type 2
.options entrycget 1 -onvalue
.options entrycget 1 -offvalue
.options invoke 1
variable extra
.options delete 1
.options type 1
.options entryconfigure 1 -variable alt -value robin
.options entrycget 1 -value
.options invoke 1
variable alt
variable colors
variable done END
variable done
