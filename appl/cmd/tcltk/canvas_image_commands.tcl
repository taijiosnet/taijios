image create bitmap dir -file dir.bit -maskfile dir.mask
image width dir
image height dir
image create bitmap glyph -maskfile file.mask
image width glyph
image height glyph
image create bitmap broken -file missing-canvas-bitmap.bit
image create bitmap broken -file dir.bit -maskfile missing-canvas-bitmap.mask
canvas .c
.c create image 30 45 -image dir -tags {folder listing}
.c bbox 1
.c coords 1
.c itemcget 1 -image
.c itemcget 1 -anchor
.c gettags 1
.c itemconfigure 1 -anchor ne
.c bbox 1
.c coords 1 50 65
.c bbox 1
image delete dir
.c itemcget 1 -image
.c bbox 1
image create bitmap dir -file @/icons/inferno.bit
.c bbox 1
.c itemconfigure 1 -image dir
.c bbox 1
.c itemconfigure 1 -image gone
.c itemcget 1 -image
.c bbox 1
.c itemconfigure 1 -image {}
.c itemcget 1 -image
.c bbox 1
.c create image 30 45 -image dir -anchor sw
.c bbox 2
.c create image 30 45
.c bbox 3
.c delete all
.c find all
