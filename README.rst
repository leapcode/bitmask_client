=========================================
The LEAP Encryption Access Project Client
=========================================

*your internet encryption toolkit*

Read the docs!
==============

You can read the documentation online at `http://leap-client.readthedocs.org <http://leap-client.readthedocs.org/en/latest/>`_. If you prefer to build it locally, run::

    $ cd docs
    $ make html

Quick Start
==============

At the current development stage we still do not have any versioned release. Instead, you might want to have a look at the `testers guide<http://leap-client.readthedocs.org/en/latest/testers/howto.html>`_ for a quick howto on fetching and testing latest development code.

Dependencies
------------------

Leap client depends on these libraries:

* ``python 2.6`` or ``2.7``
* ``qt4 libraries``
* ``libgnutls``
* ``openvpn``

Python packages are listed in ``pkg/requirements.pip`` and ``pkg/test-requirements.pip``

Debian
^^^^^^

Under a debian-based system, you can run::

  $ apt-get install openvpn python-qt4 python-crypto python-requests python-gnutls

For *testing*::

  $ apt-get install python-nose python-mock python-coverage

For *building* the package you will need to install also::

  $ apt-get install pyqt4-dev-tools libgnutls-dev python-setuptools python-all-dev


pip
^^^

Use pip to install the required python packages::

  $ apt-get install python-pip python-dev libgnutls-dev
  $ pip install -r pkg/requirements.pip


Installing
-----------

After getting the source and installing all the dependencies, proceed to install ``leap-client`` package::

  $ python setup.py install


Running
-------

After a successful installation, there should be a launcher called ``leap-client`` somewhere in your path::

  $ leap-client


Hacking
=======

See the `hackers guide<http://leap-client.readthedocs.org/en/latest/dev/environment.html>`_

The LEAP client git repository is available at::

  git://leap.se/leap_client 

Some steps need to be run when setting a development environment for the first time.

Enable a **virtualenv** to isolate your libraries. (Current *.gitignore* knows about a virtualenv in the root tree. If you do not like that place, just change ``.`` for *<path.to.environment>*)::

  $ virtualenv .
  $ source bin/activate

Make sure you are in the development branch::

  (leap_client)$ git checkout develop

Symlink your global pyqt libraries::

  (leap_client)$ pkg/postmkvenv.sh

And make your working tree available to your pythonpath::

  (leap_client)$ python setup.py develop  


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
