.. _install:

Installation
============

This part of the documentation covers the installation of the LEAP Client.
We assume that you want to get it properly installed before being able to use it.

Debian package
--------------

.. warning::

   No updated debian package yet.

Once we have a release candidate, probably the easiest way of having the LEAP Client installed will be to install a .deb package under debian or ubuntu systems.


Distribute & Pip
----------------

.. warning::

   This does not work yet, since we have not released an initial version yet to the cheese shop.

Installing LEAP Client will be as simple as using `pip <http://www.pip-installer.org/>`_ once we have a release candidate::

    $ pip install leap-client

Get the code
------------

.. warning::

   This... won't work either, as-is. This should be the third optional way to install stable releases from master branch. Right now that does not work because there is *nothing* updated in the master branch. Leaving this here since this is what we will be doing, but if you really intend to have a working tree, refer to the sections :ref:`setting up a working environment <environment>` or :ref:`fetching latest code <fetchinglatest>`.

You can get the code from LEAP public git repository ::

    git clone git://leap.se/leap_client

Or from the github mirror ::

    git clone git://github.com/leapcode/leap_client.git

Once you have grabbed a copy of the sources, you can install it into your site-packages easily ::

   $ pyton setup.py install
