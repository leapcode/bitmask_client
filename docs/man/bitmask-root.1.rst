============
bitmask-root
============

------------------------------------------------------------------------
privileged helper for bitmask, the encrypted internet access toolkit.
------------------------------------------------------------------------

:Author: LEAP Encryption Access Project https://leap.se
:Date:   2014-06-05
:Copyright: GPLv3+
:Version: 0.5.2
:Manual section: 1
:Manual group: General Commands Manual

SYNOPSIS
========

bitmask-root [openvpn | firewall | version] [start | stop | isup] [ARGS]

DESCRIPTION
===========

*bitmask-root* is a privileged helper for bitmask.

It is used to start or stop openvpn and the bitmask firewall. To operate, it
needs to be executed with root privileges.


OPTIONS
=======

openvpn
--------

**start** [ARGS]       Starts openvpn. All args are passed to openvpn, and
                       filtered against a list of allowed args. If the next
                       argument is `restart`, the firewall will not be teared
                       down in the case of errors lauching openvpn.

**stop**               Stops openvpn.


firewall
---------

**start** [GATEWAYS]   Starts the firewall. GATEWAYS is a list of EIP
                       gateways to allow in the firewall.

**stop**               Stops the firewall.

version
--------

**version**             Prints the `bitmask-root` version string.


BUGS
====

Please report any bugs to https://leap.se/code
