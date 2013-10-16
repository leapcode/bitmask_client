Bitmask
=======

*your internet encryption toolkit*

.. image:: https://pypip.in/v/leap.bitmask/badge.png
        :target: https://crate.io/packages/leap.bitmask

**Bitmask** is the multiplatform desktop client for the services offered by
`the LEAP Platform`_.

It is written in python using `PySide`_ and licensed under the GPL3.
Currently we distribute pre-compiled `bundles`_ for Linux, OSX and Windows.

.. _`PySide`: http://qt-project.org/wiki/PySide
.. _`the LEAP Platform`: https://github.com/leapcode/leap_platform
.. _`bundles`: https://downloads.leap.se/client/


Read the Docs!
------------------

The latest documentation is available at `Read The Docs`_.

.. _`Read The Docs`: http://bitmask.rtfd.org

Dependencies
------------------

Bitmask depends on these libraries:

* ``python 2.6`` or ``2.7``
* ``qt4 libraries``
* ``libopenssl``
* ``openvpn``

Python packages are listed in ``pkg/requirements.pip`` and ``pkg/test-requirements.pip``

Getting dependencies under debian
++++++++++++++++++++++++++++++++++

With a Debian based system, to be able to run Bitmask you need to run the following command::

    $ sudo apt-get install git python-dev python-setuptools
    python-virtualenv python-pip python-openssl libsqlite3-dev g++ openvpn
    pyside-tools python-pyside 

Installing
-----------

After getting the source and installing all the dependencies, proceed to install ``bitmask`` package::

  $ make
  $ sudo python2 setup.py install

Running
-------

After a successful installation, there should be a launcher called ``bitmask`` somewhere in your path::

  $ bitmask

If you are testing a new provider and do not have a CA certificate chain tied to your SSL certificate, you should execute Bitmask in the following way::

  $ bitmask --danger

But **DO NOT use it on a regular basis**.

**WARNING**: If you use the --danger flag you may be victim to a MITM_ attack without noticing. Use at your own risk.

.. _MITM: http://en.wikipedia.org/wiki/Man-in-the-middle_attack

Hacking
=======

Get the source from the main Bitmask repo::

    git clone https://leap.se/git/bitmask_client

The code is also browsable online at::

    https://leap.se/git/?p=bitmask_client.git

Some steps need to be run when setting a development environment for the first time.

Enable a **virtualenv** to isolate your libraries. (Current *.gitignore* knows about a virtualenv in the root tree. If you do not like that place, just change ``.`` for *<path.to.environment>*)::

  $ virtualenv .
  $ source bin/activate

Make sure you are in the development branch::

  (bitmask)$ git checkout develop

Symlink your global pyside libraries::

  (bitmask)$ pkg/postmkvenv.sh

And make your working tree available to your pythonpath::

  (bitmask)$ python2 setup.py develop

Run Bitmask::

  (bitmask)$ bitmask --debug

Testing
=======

Have a look at ``pkg/test-requirements.pip`` for the tests dependencies.

To run the test suite::

    $ ./run_tests.sh

which the first time should automagically install all the needed dependencies in your virtualenv for you.

License
=======

.. image:: https://raw.github.com/leapcode/bitmask_client/develop/docs/user/gpl.png

Bitmask is released under the terms of the `GNU GPL version 3`_ or later.

.. _`GNU GPL version 3`: http://www.gnu.org/licenses/gpl.txt
