.. _quickstart:

Quickstart
==========

**Assumptions:** These instructions were made on a clean Ubuntu 12.04.3
system.

**Goal:** With minimal effort or reading install the necessary packages
to build the latest development code for ``bitmask_client``

**Outcome:** At the end of these instructions, you should be able to run
the latest development branch for bitmask client, getting the GUI in debug
mode and connect to a LEAP provider (bitmask.net)

If you want to know what each step is for, check
:ref:`this other section <environment>`.


Prerequisites
-------------

.. begin-debian-deps
::

    $ sudo apt-get install git python-dev python-setuptools
    python-virtualenv python-pip python-openssl libsqlite3-dev g++ openvpn
    pyside-tools python-pyside libffi-dev

.. python-qt4  ??? (for translations)
.. TODO I'm pretty sure python-qt4 shoudln't be there...
   Nor libsqlite-dev, that's a bug in python-sqlcipher/soledad.


.. XXX any change HERE ^^^^ should be reflected also in README.rst.
   From any other place in the documentation, it should be just included.

.. end-debian-deps

Clone the repo into your working directory, and checkout development branch::

    $ git clone https://github.com/leapcode/bitmask_client bitmask
    $ cd bitmask
    $ git checkout develop


Create and activate the virtualenv, and symlink to your gloabal PySide install::

    $ virtualenv .
    $ source bin/activate
    (bitmask)$ pkg/postmkvenv.sh


Python libraries
----------------

Install the bitmask package in development mode inside the virtualenv. This will
also install the needed dependencies::

    (bitmask)$ python2 setup.py develop

Compile the resource files::

    (bitmask)$ make

Copy necessary files into system folders, with root privileges::

    (bitmask)$ sudo mkdir -p /etc/leap
    (bitmask)$ sudo cp pkg/linux/resolv-update /etc/leap
    (bitmask)$ sudo cp pkg/linux/polkit/net.openvpn.gui.leap.policy /usr/share/polkit-1/actions/


Running
--------

Run ``bitmask_client`` in debug mode::

    (bitmask)$ bitmask --debug

You should see the ``bitmask_client`` window prompting to connect to an
existing node or add a new one. If not, something went wrong, maybe ask
on #leap-dev at irc.freenode.net
