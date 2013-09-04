.. _install:

Installation
============

This part of the documentation covers the installation of Bitmask.
We assume that you want to get it properly installed before being able to use it.

.. note::

   Methods described in this page assume you are familiar with python code, and you can find your way through the process of dependencies install. You can refer to the sections :ref:`setting up a working environment <environment>` or :ref:`fetching latest code for testing <fetchinglatest>`.

Standalone bundle
-----------------

You can run Bitmask using the standalone bundle, the recommended way to use Bitmask.

For the latest bundles and its signatures in https://downloads.leap.se/client/

Linux 32 bits:
    https://downloads.leap.se/client/linux/Bitmask-linux32-0.3.1.tar.bz2

    https://downloads.leap.se/client/linux/Bitmask-linux32-0.3.1.tar.bz2.asc

Linux 64 bits:
    https://downloads.leap.se/client/linux/Bitmask-linux64-0.3.1.tar.bz2

    https://downloads.leap.se/client/linux/Bitmask-linux64-0.3.1.tar.bz2.asc

OSX:
    https://downloads.leap.se/client/osx/Bitmask-OSX-0.3.1.dmg

    https://downloads.leap.se/client/osx/Bitmask-OSX-0.3.1.dmg.asc

Windows version is delayed right now.

For the signature verification you can use ::

    $ gpg --verify Bitmask-linux64-0.3.1.tar.bz2.asc

Asuming that you downloaded the linux 64 bits bundle.

Distribute & Pip
----------------

Installing Bitmask is as simple as using `pip <http://www.pip-installer.org/>`_ for the already released versions ::

    $ pip install leap.bitmask

Debian package
--------------

.. warning::

   The debian package in the leap repositories is from the stable, `0.2.0` release, which is now outdated. You are encouraged to install the development version instead.

First, you need to bootstrap your apt-key::

   # gpg --recv-key 0x1E34A1828E207901 0x485B12FA218E81EB
   # gpg --list-sigs 0x1E34A1828E207901
   # gpg --list-sigs 0x485B12FA218E81EB
   # gpg -a --export 0x1E34A1828E207901  | sudo apt-key add - 

Add the archive to your sources.list::

   # echo "deb http://deb.leap.se/debian unstable main" >> /etc/apt/sources.list
   # apt-get update
   # apt-get install leap-keyring

And  then you can happily install bitmask::

   apt-get install bitmask

Show me the code!
-----------------

You can get the code from LEAP public git repository ::

   $ git clone git://leap.se/bitmask

Or from the github mirror ::

   $ git clone git://github.com/leapcode/bitmask.git

Once you have grabbed a copy of the sources, you can install it into your site-packages easily ::

   $ pyton setup.py install

