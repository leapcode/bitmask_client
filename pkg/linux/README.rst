Files 
=====

In GNU/Linux, we expect these files to be in place::

 bitmask-root -> /usr/sbin/bitmask-root
 polkit/se.leap.bitmask.policy -> /usr/share/polkit-1/actions/se.leap.bitmask.policy

Bundle
======

The bundle will ask for permission to install to a different path. This search
path will be used if the flag ``--standalone`` is set::

 bitmask-root -> /usr/local/sbin/bitmask-root
 polkit/se.leap.bitmask.bundle.policy -> /usr/share/polkit-1/actions/se.leap.bitmask.bundle.policy

When running with ``--standalone`` flag, the openvpn binary is  expected in the following path::

 leap-openvpn -> /usr/local/sbin/leap-openvpn

The bundle will use the script ``leap-install-helper.sh`` to copy the needed
files. If you ever want to use it manually to update the helpers or bins, it
needs a ``--from-path`` parameter to be passed to it. This points to a folder
from where all the needed binaries and scripts can be found.


Binary hashing
==============

To be able to update the binaries when needed, the bundles distribute with the
sha256 hash of the packaged binaries for each release. This info can be found
in::

  src/leap/bitmask/_binaries.py

That file is generated during the bundling process, by issuing the following
command from the root folder::

  python setup.py hash_binaries
