scrollbar .bar -command {.rows yview}
listbox .rows -width 180 -height 65 -selectmode single -yscrollcommand {.bar set}
.rows cget -selectmode
.rows cget -yscrollcommand
pack .bar -side left -fill y
pack .rows -side left
.rows insert end zero one two three four five six seven
update
.rows size
.rows index end
.rows get 1 3
.rows yview
.bar get
.rows selection set 1 3
.rows selection clear 2
.rows curselection
.rows selection includes 2
.rows selection includes 3
.rows selection anchor 3
.rows activate 4
.rows insert 1 {café à la carte}
.rows get 1
.rows index anchor
.rows index active
.rows curselection
.rows delete 1 2
.rows size
.rows index anchor
.rows index active
.rows curselection
.rows yview moveto 1
.rows yview
.bar get
.rows yview scroll -1 units
.rows yview
.rows yview scroll -1 pages
.rows yview
.rows see end
.rows yview
.rows yview 1
.rows yview
.rows index @0,0
.rows delete 0 end
update
.rows yview
.bar get
.rows size
