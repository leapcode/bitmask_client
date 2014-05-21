============
bitmask-root
============

------------------------------------------------------------------------
privileged helper for bitmask, the encrypted internet access toolkit.
------------------------------------------------------------------------

:Author: LEAP Encryption Access Project https://leap.se
:Date:   2014-05-19
:Copyright: GPLv3+
:Version: 0.5.1
:Manual section: 1
:Manual group: General Commands Manual

SYNOPSIS
========

bitmask-root [openvpn | firewall | isup ] [start | stop] [ARGS]

DESCRIPTION
===========

*bitmask-root* is a privileged helper for bitmask.

It is used to start or stop openvpn and the bitmask firewall.


OPTIONS
=======

openvpn
--------

**start** [ARGS]       Starts openvpn. All args are passed to openvpn, and
                       filtered against a list of allowed args.

**stop**               Stops openvpn.


firewall
---------

**start** [GATEWAYS]   Starts the firewall. GATEWAYS is a list of EIP
                       gateways to allow in the firewall.

**stop**               Stops the firewall.



BUGS
====

Please report any bugs to https://leap.se/code
