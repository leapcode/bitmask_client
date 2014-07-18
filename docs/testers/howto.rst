.. _testhowto:

Howto for Testers
=================

This document covers a how-to guide to:

#. :ref:`Where and how report bugs for Bitmask <reporting_bugs>`, and
#. :ref:`Quickly fetching latest development code <fetchinglatest>`.

Let's go!

.. _reporting_bugs:

Reporting bugs
--------------

Report all the bugs you can find to us! If something is not quite working yet,
we really want to know. Reporting a bug to us is the best way to get it fixed
quickly, and get our unconditional gratitude.

It is quick, easy, and probably the best way to contribute to Bitmask
development, other than submitting patches.

.. admonition:: Reporting better bugs

   New to bug reporting? Here you have a `great document about this noble art
   <http://www.chiark.greenend.org.uk/~sgtatham/bugs.html>`_.

Where to report bugs
^^^^^^^^^^^^^^^^^^^^

We use the `Bitmask Bug Tracker <https://leap.se/code/projects/eip-client>`_,
although you can also use `Github issues
<https://github.com/leapcode/bitmask_client/issues>`_. But we reaaaally prefer if you
sign up in the former to send your bugs our way.

What to include in your bug report
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

* The symptoms of the bug itself: what went wrong? What items appear broken, or
  do not work as expected? Maybe an UI element that appears to freeze?
* The Bitmask version you are running. You can get it by doing `bitmask
  --version`, or you can go to `Help -> About Bitmask` menu.
* The installation method you used: bundle? from source code? debian package?
* Your platform version and other details: Ubuntu 12.04? Debian unstable?
  Windows 8? OSX 10.8.4? If relevant, your desktop system also (gnome, kde...)
* When does the bug appear? What actions trigger it? Does it always
  happen, or is it sporadic?
* The exact error message, if any.
* Attachments of the log files, if possible (see section below).

Also, try not to mix several issues in your bug report. If you are finding
several problems, it's better to issue a separate bug report for each one of
them.

Attaching log files
^^^^^^^^^^^^^^^^^^^

If you can spend a little time getting them, please add some logs to the bug
report. They are **really** useful when it comes to debug a problem. To do it:

Launch Bitmask in debug mode. Logs are way more verbose that way::

  bitmask --debug

Get your hand on the logs. You can achieve that either by clicking on the "Show
log" button, and saving to file, or directly by specifying the path to the
logfile in the command line invocation::

  bitmask --debug --logfile /tmp/bitmask.log

Attach the logfile to your bug report.

Need human interaction?
^^^^^^^^^^^^^^^^^^^^^^^

You can also find us in the ``#leap-dev`` channel on the `freenode network
<https://freenode.net>`_. If you do not have a IRC client at hand, you can
`enter the channel via web
<http://webchat.freenode.net/?nick=leaper....&channels=%23leap-dev&uio=d4>`_.


.. _fetchinglatest:

Fetching latest development code
---------------------------------

Normally, testing the latest :ref:`client bundles <standalone-bundle>` should be
enough. We are engaged in a two-week release cycle with minor releases that are
as stable as possible.

However, if you want to test that some issue has *really* been fixed before the
next release is out (if you are testing a new provider, for instance), you are
encouraged to try out the latest in the development branch. If you do not know
how to do that, or you prefer an automated script, keep reading for a way to
painlessly fetch the latest development code.

We have put together a script to allow rapid testing in different platforms for
the brave souls like you. It more or less does all the steps covered in the
:ref:`Setting up a Work Enviroment <environment>` section, only that in a more
compact way suitable (ahem) also for non developers.

.. note::

   At some point in the near future, we will be using :ref:`standalone bundles
   <standalone-bundle>` with the ability to self-update.

Install dependencies
^^^^^^^^^^^^^^^^^^^^
First, install all the development files and dependencies needed to compile:

.. include:: ../dev/quickstart.rst
   :start-after: begin-debian-deps
   :end-before: end-debian-deps


Bootstrap script
^^^^^^^^^^^^^^^^
.. note::
   This will fetch the *develop* branch. If you want to test another branch, just change it in the line starting with *pip install...*. Alternatively, bug kali so she add an option branch to an improved script.

.. note::
   This script could make use of the after_install hook. Read http://pypi.python.org/pypi/virtualenv/

Download and source the following script in the parent folder where you want your testing build to be downloaded. For instance, to `/tmp/`:

.. code-block:: bash

   cd /tmp
   wget https://raw.github.com/leapcode/bitmask_client/develop/pkg/scripts/bitmask_bootstrap.sh
   source bitmask_bootstrap.sh

Tada! If everything went well, you should be able to run bitmask by typing::

    bitmask --debug

Noticed that your prompt changed? That was *virtualenv*. Keep reading...

Activating the virtualenv
^^^^^^^^^^^^^^^^^^^^^^^^^
The above bootstrap script has fetched latest code inside a virtualenv, which is
an isolated, *virtual* python local environment that avoids messing with your
global paths. You will notice you are *inside* a virtualenv because you will see
a modified prompt reminding it to you (*bitmask-testbuild* in this case).

Thus, if you forget to *activate your virtualenv*, bitmask will not run from the
local path, and it will be looking for something else in your global path. So,
**you have to remember to activate your virtualenv** each time that you open a
new shell and want to execute the code you are testing. You can do this by
typing::

    $ source bin/activate

from the directory where you *sourced* the bootstrap script.

Refer to :ref:`Working with virtualenv <virtualenv>` to learn more about virtualenv.

Copying config files
^^^^^^^^^^^^^^^^^^^^

If you have never installed ``bitmask`` globally, **you need to copy some files to its proper path before running it for the first time** (you only need to do this once). This, unless the virtualenv-based operations, will need root permissions. See :ref:`copy script files <copyscriptfiles>` and :ref:`running openvpn without root privileges <policykit>` sections for more info on this. In short::

    $ sudo cp pkg/linux/polkit/net.openvpn.gui.leap.policy /usr/share/polkit-1/actions/

Local config files
^^^^^^^^^^^^^^^^^^^

If you want to start fresh without config files, just move them. In linux::

    mv ~/.config/leap ~/.config/leap.old

Pulling latest changes
^^^^^^^^^^^^^^^^^^^^^^

You should be able to cd into the downloaded repo and pull latest changes::

    (bitmask-testbuild)$ cd src/bitmask
    (bitmask-testbuild)$ git pull origin develop

However, you are encouraged to run the whole bootstrapping process from time to time to help us catching install and versioning bugs too.

Testing the packages
^^^^^^^^^^^^^^^^^^^^
When we have a release candidate for the supported platforms, we will announce also the URI where you can download the rc for testing in your system. Stay tuned!

Testing the status of translations
----------------------------------

We need translators! You can go to `transifex <https://www.transifex.com/projects/p/bitmask/>`_, get an account and start contributing.

If you want to check the current status of bitmask localization in a language other than the one set in your machine, you can do it with a simple trick (under linux). For instance, do::

    $ lang=es_ES bitmask

for running Bitmask with the spanish locales.

