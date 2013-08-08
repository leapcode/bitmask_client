=======
bitmask
=======

------------------------------------------------------------------------
graphical client to control LEAP, the encrypted internet access toolkit.
------------------------------------------------------------------------

:Author: LEAP Encryption Access Project https://leap.se
:Date:   2013-01-30
:Copyright: GPLv3+
:Version: 0.2
:Manual section: 1
:Manual group: General Commands Manual

SYNOPSIS
========

bitmask [-h] [-d] [-l [LOG FILE]] [--openvpn-verbosity [OPENVPN_VERB]]

DESCRIPTION
===========

*bitmask* is a graphical client to control LEAP, the encrypted internet access toolkit.

When launched, it places an icon in the system tray from where the LEAP services can be controlled.


OPTIONS
=======

general options
---------------

**-h, --help**                  Print a help message and exit.

**-d, --debug**                 Launches client in debug mode, writing debug info to stdout.

**---logfile=<file>**           Writes log to file. 

openvpn options
---------------

**--openvpn-verbosity** [0-5]       Verbosity level for openvpn logs.


WARNING
=======

This software is still in early alfa testing. So don't trust your life to it! 

At the current time, Bitmask is not compatible with ``openresolv``, but it works with ``resolvconf``.

FILES
=====

/etc/leap/resolv-update
-----------------------
Post up/down script passed to openvpn. It writes /etc/resolv.conf to avoid dns leaks, and restores the original resolv.conf on exit.

/etc/leap/resolv-head
---------------------
/etc/leap/resolv-tail
---------------------

Custom entries that will appear in the written resolv.conf

/usr/share/polkit-1/actions/net.openvpn.gui.leap.policy
-------------------------------------------------------

PolicyKit policy file, used for granting access to openvpn without the need of entering a password each time.

~/.config/leap/
---------------

Main config folder

~/.config/leap/leap.conf
------------------------

GUI options

BUGS
====

Please report any bugs to https://leap.se/code
