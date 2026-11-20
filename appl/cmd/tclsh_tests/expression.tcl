# Limbo-compatible numeric expressions. Approximate results use tolerances.
set gain 2.5
set octal 014
set hex 0x20
puts "decimal=[expr {1.5+2}] quotient=[expr {5/2.0}] substituted=[expr {$gain*2}]"
puts "scientific=[expr {1.25e3/2.0}] fraction=[expr {.5*8}] comparison=[expr {17>3.0}]"
puts "radices=[expr {0x20|04}] shift=[expr {4<<3}] complement=[expr {~1&7}] conditional=[expr {0?11:12}]"
puts "substituted-radices=[expr {$octal+$hex}]"
puts "absolute=[expr {abs(-2)}] ceil=[expr {ceil(-2.5)}] floor=[expr {floor(-2.5)}] remainder=[expr {fmod(5.5,2)}]"
puts "power=[expr {pow(2,8)}] root=[expr {sqrt(81)}] norm=[expr {hypot(3,4)}] logarithm=[expr {log10(1000)}]"
puts "inverse=[expr {abs(acos(0)-1.5707963267948966)<0.000001&&abs(asin(.5)-.5235987755982989)<0.000001&&abs(atan(1)-.7853981633974483)<0.000001&&abs(atan2(1,1)-.7853981633974483)<0.000001}]"
puts "trig=[expr {abs(cos(1)-.5403023058681398)<0.000001&&abs(sin(1)-.8414709848078965)<0.000001&&abs(tan(1)-1.5574077246549023)<0.000001}]"
puts "hyperbolic=[expr {abs(cosh(1)-1.5430806348152437)<0.000001&&abs(sinh(1)-1.1752011936438014)<0.000001&&abs(tanh(1)-.7615941559557649)<0.000001}]"
puts "nested=[expr {abs(log(exp(1))-1.0)<0.000001}]"
proc grow {x} {return [expr {$x+0.25}]}
set total 0.25
while {$total<1.0} {set total [grow $total]}
set doubled [expr {[grow 1.25]*2}]
puts "loop=$total nested=$doubled"
