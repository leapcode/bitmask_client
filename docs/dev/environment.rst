.. _environment:

Setting up a development environment
====================================

This document covers how to get an enviroment ready to contribute code to Bitmask, with some explanations of what are we doing in each step along the way. For just the meat, check the :ref:`quickstart <quickstart>` `section`.

Cloning the repo
----------------
.. note::
   Stable releases are in *master* branch.
   Development code lives in *develop* branch.

::

    git clone https://leap.se/git/?p=bitmask_client.git
    git checkout develop

.. XXX change this when repo changes.

Base Dependencies
------------------
Bitmask depends on these base libraries:

* `python 2.6 or 2.7`
* `qt4` libraries (see also :ref:`Troubleshooting PySide install <pysidevirtualenv>` about how to install inside your virtualenv)
* `openssl`
* `openvpn <http://openvpn.net/index.php/open-source/345-openvpn-project.html>`_

Debian
^^^^^^
In debian-based systems, you can get everything you need:

.. include:: quickstart.rst
   :start-after: begin-debian-deps
   :end-before: end-debian-deps

.. _virtualenv:

Working with virtualenv
-----------------------

Intro
^^^^^^^^^^^^^^^^^^^

*Virtualenv* is the *Virtual Python Environment builder*.

It is a tool to create isolated Python environments.

The basic problem being addressed is one of dependencies and versions, and indirectly permissions. Imagine you have an application that needs version 1 of LibFoo, but another application requires version 2. How can you use both these applications? If you install everything into /usr/lib/python2.7/site-packages (or whatever your platform's standard location is), it's easy to end up in a situation where you unintentionally upgrade an application that shouldn't be upgraded.

Read more about it in the `project documentation page <http://pypi.python.org/pypi/virtualenv/>`_. 

.. note::
   this section could be completed with useful options that can be passed to the virtualenv command (e.g., to make portable paths, site-packages, ...). We also should document how to use virtualenvwrapper.



Create and activate your dev environment
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

You first create a virtualenv in any directory that you like::

    $ mkdir ~/Virtualenvs
    $ virtualenv ~/Virtualenvs/bitmask
    $ source ~/Virtualenvs/bitmask/bin/activate

.. TODO use virtualenvwrapper + isis non-sudo recipe here 

.. _pysidevirtualenv:

Avoid compiling PySide inside a virtualenv
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you attempt to install PySide inside a virtualenv as part of the rest of the dependencies using pip, basically it will take ages to compile.

As a workaround, you can run the following script after creating your virtualenv. It will symlink to your global PySide installation (*this is the recommended way if you are running a debian-based system*)::

    $ pkg/postmkvenv.sh

A second option if that does not work for you would be to install PySide globally and pass the ``--system-site-packages`` option when you are creating your virtualenv::

    $ sudo apt-get install python-pyside
    $ virtualenv --system-site-packages .

And now you are ready to proceed with the next section.

.. _pydepinstall:

Install python dependencies
^^^^^^^^^^^^^^^^^^^^^^^^^^^

You can install python dependencies with ``pip``. If you do it inside your working environment, they will be installed avoiding the need for administrative permissions::

    $ (bitmask) pip install -r pkg/requirements.pip

.. _makeresources:

Install Bitmask
---------------

We will be using setuptools **development mode** inside the virtualenv. It will
creaate a link from the local site-packages to your working directory. In this
way, your changes will always be in the installation path without need to
install the package you are working on.::

    $ (bitmask) python2 setup.py develop

After this step, your Bitmask launcher will be located at
``~/Virtualenvs/bitmask/bin/bitmask``, and it will be in the path as long as you
have sourced your virtualenv.

Make resources
--------------

We also need to compile the resource files::

    $ (bitmask) make resources

.. TODO need to make translations too?

.. _copyscriptfiles:

Copy script files
-----------------

The openvpn invocation expects some files to be in place. If you have not installed `bitmask` from a debian package, you must copy these files manually by now::

    $ sudo mkdir -p /etc/leap
    $ sudo cp pkg/linux/resolv-update /etc/leap

.. _policykit:

Running openvpn without root privileges
---------------------------------------

In linux, we are using ``policykit`` to be able to run openvpn without root privileges, and a policy file is needed to be installed for that to be possible.
The setup script tries to install the policy file when installing bitmask system-wide, so if you have installed bitmask in your global site-packages at least once it should have copied this file for you.

If you *only* are running bitmask from inside a virtualenv, you will need to copy this file by hand::

    $ sudo cp pkg/linux/polkit/net.openvpn.gui.leap.policy /usr/share/polkit-1/actions/


Missing Authentication agent
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. TODO I think we could be safely removing this section by now.

If you are using linux and running a desktop other than unity or gnome, you might get an error saying that you are not running the authentication agent. For systems with gnome libraries installed you can launch it like this::

    /usr/lib/policykit-1-gnome/polkit-gnome-authentication-agent-1 &

or if you are a kde user::

   /usr/lib/kde4/libexec/polkit-kde-authentication-agent-1 &

Running!
--------

If everything went well, you should be able to run your client by invoking
``bitmask``. If it does not get launched, or you just want to see more verbose
output, try the debug mode::

   $ (bitmask) bitmask --debug
