.. _testhowto:

Howto for Testers
=================

This document covers a how-to guide to:

#. Quickly fetching latest development code, and
#. Reporting bugs.

Let's go!

.. _fetchinglatest:

Fetching latest development code
---------------------------------

To allow rapid testing in different platforms, we have put together a quick script that is able to fetch latest development code. It more or less does all the steps covered in the :ref:`Setting up a Work Enviroment <environment>` section, only that in a more compact way suitable (ahem) also for non developers. 

Install dependencies
^^^^^^^^^^^^^^^^^^^^
First, install all the base dependencies plus git, virtualenv and development files needed to compile several extensions::

   apt-get install openvpn git-core libgnutls-dev python-dev python-qt4 python-setuptools python-virtualenv


Bootstrap script
^^^^^^^^^^^^^^^^
.. note::
   This will fetch the *develop* branch. If you want to test another branch, just change it in the line starting with *pip install...*. Alternatively, bug kali so she add an option branch to a decent script.

.. note::
   This script could make use of the after_install hook. Read http://pypi.python.org/pypi/virtualenv/ 

Download and source the following script in the parent folder where you want your testing build to be downloaded. For instance, to `/tmp/`:

.. code-block:: bash

   cd /tmp
   wget https://raw.github.com/leapcode/leap_client/develop/pkg/scripts/leap_client_bootstrap.sh
   source leap_client_bootstrap.sh

Tada! If everything went well, you should be able to run the client by typing::

    bin/leap-client

Noticed that your prompt changed? That was *virtualenv*. Keep reading...

Activating the virtualenv
^^^^^^^^^^^^^^^^^^^^^^^^^
The above bootstrap script has fetched latest code inside a virtualenv, which is an isolated, *virtual* python local environment that avoids messing with your global paths. You will notice you are *inside* a virtualenv because you will see a modified prompt reminding it to you (*leap-client-testbuild* in this case).

Thus, if you forget to *activate your virtualenv*, the client will not run from the local path, and it will be looking for something else in your global path. So, **you have to remember to activate your virtualenv** each time that you open a new shell and want to execute the code you are testing. You can do this by typing::

    $ source bin/activate

from the directory where you *sourced* the bootstrap script.

Refer to :ref:`Working with virtualenv <virtualenv>` to learn more about virtualenv.

Policy files
^^^^^^^^^^^^

If you have never installed the ``leap-client`` globally, **you need to copy a policykit file to its proper path before running it for the first time** (you only need to do this once). This, unless the virtualenv-based operations, will need root permissions. See :ref:`running openvpn without root privileges <policykit>` section for more info on this.

Config files
^^^^^^^^^^^^

If you want to start fresh without config files, just move them. In linux::

    mv ~/.config/leap ~/.config/leap.old

Pulling latest changes
^^^^^^^^^^^^^^^^^^^^^^

You should be able to cd into the downloaded repo and pull latest changes::

    (leap-client-testbuild)$ cd src/leap-client
    (leap-client-testbuild)$ git pull origin develop

However, as a tester you are encouraged to run the whole bootstrap process from time to time to help us catching install and versioniing bugs too.

Testing the packages
^^^^^^^^^^^^^^^^^^^^
When we have a release candidate for the supported platforms (Debian stable, Ubuntu 12.04 by now), we will announce also the URI where you can download the rc for testing in your system. Stay tuned!

Testing the status of translations
----------------------------------

We need translators! You can go to `transifex <https://www.transifex.com/projects/p/leap-client/>`_, get an account and start contributing.

If you want to check the current status of the client localization in a language other than the one set in your machine, you can do it with a simple trick (under linux). For instance, do::

    $ lang=es_ES leap-client

for running  LEAP Client with the spanish locales.

Reporting bugs
--------------

.. admonition:: Reporting better bugs

   There is a great text on the art of bug reporting, that can be found `online <http://www.chiark.greenend.org.uk/~sgtatham/bugs.html>`_.

.. TODO add a line with ref. to running the client in debug mode...

We use the `LEAP Client Bug Tracker <https://leap.se/code/projects/eip-client>`_, although you can also use `Github issues <https://github.com/leapcode/leap_client/issues>`_.
