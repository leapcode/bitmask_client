.. _install:

Installation
============

This part of the documentation covers the installation of the LEAP Client.
We assume that you want to get it properly installed before being able to use it.

.. note::

   The recommended way of installing in the near future will be the standalone bundles, but those are not quite ready yet. Methods described in this page assume you are familiar with python code, and you can find your way through the process of dependencies install. You can refer to the sections :ref:`setting up a working environment <environment>` or :ref:`fetching latest code for testing <fetchinglatest>`.


Distribute & Pip
----------------

.. warning:: The package in the cheese shop is from the stable, `0.2.0` release, which is now outdated. You are encouraged to install the development version instead.

Installing LEAP Client is as simple as using `pip <http://www.pip-installer.org/>`_ for the already released versions ::

    $ pip install leap-client

Debian package
--------------

.. warning::

   The debian package in the leap repositories is from the stable, `0.2.0` release, which is now outdated. You are encouraged to install the development version instead,

First, you need to bootstrap your apt-key::

   # gpg --recv-key 0x1E34A1828E207901 0x485B12FA218E81EB
   # gpg --list-sigs 0x1E34A1828E207901
   # gpg --list-sigs 0x485B12FA218E81EB
   # gpg -a --export 0x1E34A1828E207901  | sudo apt-key add - 

Add the archive to your sources.list::

   # echo "deb http://deb.leap.se/debian unstable main" >> /etc/apt/sources.list
   # apt-get update
   # apt-get install leap-keyring

And  then you can happily install leap-client::

   apt-get install leap-client

Show me the code!
-----------------

You can get the code from LEAP public git repository ::

   $ git clone git://leap.se/leap_client

Or from the github mirror ::

   $ git clone git://github.com/leapcode/leap_client.git

Once you have grabbed a copy of the sources, you can install it into your site-packages easily ::

   $ pyton setup.py install

