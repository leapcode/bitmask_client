=======
bitmask
=======

------------------------------------------------------------------------
graphical client to control LEAP, the encrypted internet access toolkit.
------------------------------------------------------------------------

:Author: LEAP Encryption Access Project https://leap.se
:Date:   2013-08-23
:Copyright: GPLv3+
:Version: 0.3.1
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

**-l, --logfile=<file>**        Writes log to file. 

**-s, --standalone**          Makes Bitmask use standalone directories for configuration and binary searching.

**-V, --version**             Displays Bitmask version and exits.


openvpn options
---------------

**--openvpn-verbosity** [0-5]   Verbosity level for openvpn logs.

debug options
-------------
**-d, --debug**                 Launches client in debug mode, writing debug info to stdout.

**--danger**                    Bypasses the certificate check for bootstrap. This open the possibility of MITM attacks, so use only to debug providers in controlled environments, and never in production.

ENCRYPTED MAIL
==============

Bitmask now (since version 0.3.0) supports the encrypted mail service with providers that offer it.

Mail client configuration
-------------------------

To be able to use the mail services, you should configure your mail client to
talk to the following ports:

**STMP**:                       localhost:2013

**IMAP**:                       localhost:1984

For the time being, we have successfully tested this functionality in thunderbird.

Mail poll period
----------------

If you want to change the default polling time for fetching mail, you can use
a environment variable: BITMASK_MAILCHECK_PERIOD

WARNING
=======

This software is still in its early phases of testing. So don't trust your life to it! 

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
