canvas .c -width 160 -height 130
.c create rectangle 12 12 95 95 -tags {base group base}
.c create rectangle 60 42 121 91 -tags {top group}
.c create text 130 111 -text Leaf -tags {tree}
.c gettags 1
.c gettags group
.c gettags tree
.c itemcget 2 -tags
.c find all
.c find withtag group
.c find withtag 2
.c find withtag current
.c find withtag absent
.c bind group <Button-3> {variable recorded group-%b}
.c bind group <ButtonPress-3>
.c bind 2 <Double-Button-1> {variable recorded exact-%b}
.c bind 2 <Double-Button-1>
.c bind 2 <Motion-Button-3> {}
.c bind 2 <Motion-Button-3>
.c addtag extra withtag group
.c gettags 1
.c find withtag extra
.c dtag 1 extra
.c gettags 1
.c find withtag extra
.c bind future <Button-2> {variable recorded future-%b}
.c bind future <Button-2>
.c itemconfigure 3 -tags {future leaf}
.c gettags 3
.c find withtag future
.c addtag future withtag 3
.c find withtag future
.c bind future <Button-2>
.c delete 2
.c find all
.c find withtag group
.c bind 2 <Double-Button-1>
.c bind group <Button-3>
.c create rectangle 100 95 158 123 -tags {replacement}
.c delete absent replacement
.c find withtag replacement
.c delete group replacement
.c find all
.c delete all
.c find all
.c create text 20 20 -text Rebuilt -tags {new}
.c find all
.c gettags new
variable end END
variable end
