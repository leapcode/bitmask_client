.. _environment:

Setting up a Work Environment
==============================

This document covers how to get an enviroment ready to contribute code to the LEAP Client.

Base Dependencies
------------------
Leap client depends on these libraries:

* `python 2.6 or 2.7`
* `qt4` libraries (see also :ref:`Troubleshooting PyQt install <pyqtvirtualenv>` about how to install inside your virtualenv)
* `libgnutls`
* `openvpn`

.. _virtualenv:

Working with virtualenv
-----------------------

Intro to virtualenv
^^^^^^^^^^^^^^^^^^^
Virtualenv blah blah

Install python dependencies
^^^^^^^^^^^^^^^^^^^^^^^^^^^

You can install python dependencies with pip::

    $ apt-get install python-pip python-dev libgnutls-dev
    $ pip install -r pkg/requirements.pip

.. _pyqtvirtualenv:

Troubleshooting PyQt install inside a virtualenv
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you attempt to install PyQt inside a virtualenv using pip, it will fail because PyQt4 does not use the standard setup.py mechanism.

As a workaround, you can run the following script after creating your virtualenv. It will symlink to your global PyQt installation (`this is the recommended way if you are running a debian-based system`)::

    $ pkg/postmkvenv.sh

A second option if that does not work for you would be to install PyQt globally and pass the `--site-packages` option when you are creating your virtualenv::

    $ apt-get install python-qt4
    $ virtualenv --site-packages .

Or, if you prefer, you can also download the official PyQt tarball and execute `configure.py` in the root folder of their distribution, which generates a `Makefile`::

    $ python configure.py
    $ make && make install


Cloning the repo
----------------

`XXX`
