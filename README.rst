The LEAP Encryption Access Project Client
=========================================

*your internet encryption toolkit*

.. image:: https://pypip.in/v/leap-client/badge.png
        :target: https://crate.io/packages/leap.client

Dependencies
------------------

LEAP Client depends on these libraries:

* ``python 2.6`` or ``2.7``
* ``qt4 libraries``
* ``libopenssl``
* ``openvpn``

Python packages are listed in ``pkg/requirements.pip`` and ``pkg/test-requirements.pip``

Debian
^^^^^^

With a Debian based system, to be able to run leap-client you need to run the following command::

  $ sudo apt-get install openvpn python-pyside pyside-tools python-setuptools python-all-dev python-pip python-dev python-openssl

Installing
-----------

After getting the source and installing all the dependencies, proceed to install ``leap-client`` package::

  $ make
  $ sudo LEAP_VENV_SKIP_PYSIDE=1 python setup.py install

Running
-------

After a successful installation, there should be a launcher called ``leap-client`` somewhere in your path::

  $ leap-client

If you are testing a new provider and do not have a CA certificate chain tied to your SSL certificate, you should execute leap-client in the following way::

  $ leap-client --danger

But **DO NOT use it on a regular bases**.

**WARNING**: If you use the --danger flag you may be victim to a MITM_ attack without noticing. Use at your own risk.

.. _MITM: http://en.wikipedia.org/wiki/Man-in-the-middle_attack

Hacking
=======

The LEAP client git repository is available at::

  git://leap.se/leap_client

Some steps need to be run when setting a development environment for the first time.

Enable a **virtualenv** to isolate your libraries. (Current *.gitignore* knows about a virtualenv in the root tree. If you do not like that place, just change ``.`` for *<path.to.environment>*)::

  $ virtualenv .
  $ source bin/activate

Make sure you are in the development branch::

  (leap_client)$ git checkout develop

Symlink your global pyside libraries::

  (leap_client)$ pkg/postmkvenv.sh

And make your working tree available to your pythonpath::

  (leap_client)$ python setup.py develop

Run the client::

  (leap_client)$ python src/leap/app.py -d


If you are testing a new provider that doesn't have the proper certificates yet, you can use --danger flag, but **DO NOT use it on a regular bases**.

**WARNING**: If you use the --danger flag you may be victim to a MITM_ attack without noticing. Use at your own risk.

.. _MITM: http://en.wikipedia.org/wiki/Man-in-the-middle_attack

Testing
=======

Have a look at ``pkg/test-requirements.pip`` for the tests dependencies.

To run the test suite::

    $ ./run_tests.sh

which the first time should automagically install all the needed dependencies in your virtualenv for you.

License
=======

.. image:: https://raw.github.com/leapcode/leap_client/develop/docs/user/gpl.png

The LEAP Client is released under the terms of the `GNU GPL version 3`_ or later.

.. _`GNU GPL version 3`: http://www.gnu.org/licenses/gpl.txt
