.. _running:

Running
==================

This document covers how to launch Bitmask.

Launching Bitmask
-----------------
After a successful installation, there should be a launcher called `bitmask` somewhere in your path::

  % bitmask

The first time you launch it, it should launch the first run wizard that will guide you through the setup of the LEAP Services.

.. note::

   You will need to enter a valid test provider running the LEAP Platform. You can use the LEAP test service, *https://bitmask.net*

.. _debugmode:

Debug mode
----------
If you are happy having lots of output in your terminal, you will like to know that you can run bitmask in debug mode::

  $ bitmask --debug
  
If you ask for it, you can also have all that debug info in a beautiful file ready to be attached to your bug reports::

  $ bitmask --debug --logfile /tmp/leap.log

.. warning 
.. the following is broken since it will clutter your stdout with all the commands sent to the management interface.
   See bug #1232

.. not working...
.. If you want to increment the level of verbosity passed to openvpn, you can do::
.. $ bitmask --openvpn-verbosity 4

Options
------------
To see all the available command line options::

  $ bitmask --help
