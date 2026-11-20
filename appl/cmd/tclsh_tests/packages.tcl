package ifneeded sample 1.2 {package provide sample 1.2}
package ifneeded sample 1.10 {package provide sample 1.10}
package ifneeded sample 1.11b2 {package provide sample 1.11b2}
package ifneeded sample 2.0 {package provide sample 2.0}
puts [list versions [lsort [package versions sample]]]
puts [list stable [package require sample 1.1] [package present -exact sample 1.10.0]]
puts [list conflict [catch {package require sample 2.0} reason] $reason]
puts [list vcompare [package vcompare 1.9 1.10] [package vcompare 1.9.0 01.09] [package vcompare 1.0a2 1.0b1]]
puts [list ranges [package vsatisfies 1.0a1 1.0] [package vsatisfies 1.0a1 1.0-1.0] [package vsatisfies 2.0 1.5-] [package vsatisfies 2.0b1 1.5-2.0] [package vsatisfies 3.0 1.5-2.0 3.0]]
package forget sample
puts [list forgotten [package versions sample] [package provide sample] [catch {package present sample}]]

package ifneeded prerelease 1.2 {package provide prerelease 1.2}
package ifneeded prerelease 1.9b1 {package provide prerelease 1.9b1}
package prefer latest
puts [list latest [package prefer] [package require prerelease]]
package ifneeded retry 1.0 {package provide retry 1.0; error broken}
puts [list rollback [catch {package require retry} reason] $reason [package provide retry]]
package ifneeded retry 1.0 {package provide retry 1.0}
puts [list retry [package require retry]]
package ifneeded wrong 1.0 {package provide wrong 2.0}
puts [list wrong-version [catch {package require wrong}] [package provide wrong]]

package ifneeded one 1.0 {package require two; package provide one 1.0}
package ifneeded two 1.0 {package require one; package provide two 1.0}
puts [list cycle [catch {package require one}] [package provide one] [package provide two]]
package ifneeded two 1.0 {package provide two 1.0}
puts [list recovered [package require one] [package present two]]

proc resolve {name requirement} {
    puts [list unknown $name $requirement]
    package ifneeded $name 2.5 [list package provide $name 2.5]
}
package unknown resolve
puts [list resolved [package require -exact {spaced package} 2.5]]
puts [list quoted-path [file join ignored /tmp// {library dir} package.tcl]]
