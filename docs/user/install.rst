.. _install:

Installation
============

This part of the documentation covers the installation of the LEAP Client.
We assume that you want to get it properly installed before being able to use it.

Debian package
--------------

If you are lucky enough to be using a debian system... well, you are lucky enough :)

To be able to install ``leap-client``, you need to add the leap repo to your software sources. First you add the leap keys to your keyring::

  gpg --recv-key 0x1E34A1828E207901 0x485B12FA218E81EB
  gpg -a --export 0x1E34A1828E207901  | sudo apt-key add - 

Now you edit :file:`/etc/apt/sources.list` and add the leap repository::

  deb http://deb.leap.se/debian unstable main

Get the package ``leap-keyring``, so you can install the packages in a trusted way and get key updates automatically::

  apt-get update
  apt-get install leap-keyring

And, finally, install the client::

  apt-get install leap-client


Distribute & Pip
----------------

Install the dependencies::

    apt-get install openvpn python-qt4 python-dev python-openssl


And then installing the client with `pip <http://www.pip-installer.org/>`_ is as simple as::

    pip install leap-client

Show me the code!
-----------------

You can get the latest tarball ::

    wget https://leap.se/downloads/leap-client/tarball/latest

Or the zipball::

    wget http://leap.se/downloads/leap-client/zipball/latest

Or, if you prefer, you can also get the code from LEAP public git repository ::

    git clone git://leap.se/leap_client

Or from the github mirror ::

    git clone git://github.com/leapcode/leap_client.git

Once you have grabbed a copy of the sources for whatever mean, you can install it into your site-packages::

   $ pyton setup.py install
