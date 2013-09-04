.. _install:

Installation
============

This part of the documentation covers the installation of Bitmask.
We assume that you want to get it properly installed before being able to use it.

Standalone bundle
-----------------

Maybe the quickest way of running Bitmask in your machine is using the standalone bundle. That is the recommended way to use Bitmask for the time being.

You can get the latest bundles, and their matching signatures at `the downloads page <https://downloads.leap.se/client/>`_.

Linux
^^^^^
- `Linux 32 bits bundle`_ (`signature <https://downloads.leap.se/client/linux/Bitmask-linux32-latest.tar.bz2.asc>`_)
- `Linux 64 bits bundle`_ (`signature <https://downloads.leap.se/client/linux/Bitmask-linux64-latest.tar.bz2.asc>`_)

OSX
^^^
- `OSX bundle`_ (`signature <https://downloads.leap.se/client/osx/Bitmask-OSX-latest.dmg.asc>`_)

Windows
^^^^^^^
.. note::

  The release of the bundles for Windows is delayed right now. We should resume
  producing them shortly, keep tuned.

Signature verification
^^^^^^^^^^^^^^^^^^^^^^

For the signature verification you can use ::

    $ gpg --verify Bitmask-linux64-latest.tar.bz2.asc

Asuming that you downloaded the linux 64 bits bundle.

.. _`PySide`: http://qt-project.org/wiki/PySide
.. _`Linux 64 bits bundle`: https://downloads.leap.se/client/linux/Bitmask-linux64-latest.tar.bz2
.. _`Linux 32 bits bundle`: https://downloads.leap.se/client/linux/Bitmask-linux32-latest.tar.bz2
.. _`OSX bundle`: https://downloads.leap.se/client/osx/Bitmask-OSX-latest.dmg
.. _`Windows bundle`: https://downloads.leap.se/client/osx/Bitmask-windows-latest.zip

Debian package
--------------

.. warning::

   The debian package that you can currently find in the leap repositories is from the stable, `0.2.0` release, which is now outdated. You are encouraged to install the development version or the standalone bundles while we upload the newest packages.

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

Distribute & Pip
----------------

.. note::

   The rest of the methods described below in this page assume you are familiar with python code, and you can find your way through the process of dependencies install. For more insight, you can also refer to the sections :ref:`setting up a working environment <environment>` or :ref:`fetching latest code for testing <fetchinglatest>`.


Installing Bitmask is as simple as using `pip <http://www.pip-installer.org/>`_ for the already released versions ::

    $ pip install leap.bitmask


Show me the code!
-----------------

You can get the code from LEAP public git repository ::

   $ git clone git://leap.se/bitmask

Or from the github mirror ::

   $ git clone git://github.com/leapcode/bitmask.git

Once you have grabbed a copy of the sources, you can install it into your site-packages easily ::

   $ pyton setup.py install

