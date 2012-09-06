========================================
=               LEAP                   =
=  The LEAP Encryption Access Project  =
=   your internet encryption toolkit   =
========================================

Installation
=============

Dependencies
--------------

* python <= 2.7
* python setuptools
* qt4 libraries
* python-qt4
* python-nose, python-mock, python-coverage (if you want to run tests)

If you are on a debian-based system, you can run:

apt-get install python-qt4 python-qt4-doc pyqt4-dev-tools python-setuptools python-nose

Install
---------------

Global install:
sudo python setup.py install

If using virtualenv:
python setup.py install

Install PyQt
------------
pip install PyQt will fail because PyQt4 does not use the standard setup.py mechanism.
Instead, they use configure.py which generates a Makefile.

python configure.py
make && make install

You can:

* install PyQt globally and make a virtualenv with --site-packages
* run pkg/install_pyqt.sh inside your virtualenv (with --no-site-packages)
* run pkg/postmkvenv.sh after creating your virtualenv, for making symlinks to your global PyQt installation.


Running the App
-----------------

leap --debug --logfile /tmp/leap.log

(or python app.py --debug if you run it from the src/leap folder).

Development
==============

Running tests
-------------

./run_tests.sh

force no virtualenv and create coverage reports:
./run_tests.sh -N -c

if you want to run specific tests, pass the (sub)module to nose:

nosetests leap.util

or

nosetests leap.util.test_leap_argparse

Tox
---
For running testsuite against all the supported python versions (currently 2.6 and 2.7), run:

tox -v

Test-deps
---------

have a look at setup/test-requires

Hack
--------------

(recommended)
virtualenv .  # ensure your .gitignore knows about it
bin/activate
pkg/postmkvenv.sh
python setup.py develop  


Compiling resource/ui files
-----------------------------

You should refresh resource/ui files every time you
change an image or a resource/ui (.ui / .qc). From
the root folder:

make ui
make resources
