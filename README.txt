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

If not using virtualenv:
sudo python setup.py install

If using virtualenv:
python setup.py install


Running the App
-----------------

You need to set up a provider in your eip.cfg file:

cd ~/.config/leap
vim eip.cfg

[provider]
remote_ip = XXX.XXX.XXX.XXX

and then run:

leap --debug

(or python app.py --debug if you run it from the src/leap folder).

Development
==============

Running tests
-------------

./run_tests.sh

if you want to run specific tests, pass the (sub)module to nose:

nosetests leap.util

or

nosetests leap.util.test_leap_argparse


Test-deps
---------

have a look at setup/test-requires

Hack
--------------

(recommended)
virtualenv .  # ensure your .gitignore knows about it
bin/activate

# you should probably simlink sip.so and PyQt4 to your system-wide
# install, there are some issues with it.

python setup.py develop  

# ... TBD: finish develop howto.
# ... and explain how is python setup develop useful.

Compiling resource/ui files
-----------------------------

You should refresh resource/ui files every time you
change an image or a resource/ui (.ui / .qc). From
the root folder:

make ui
make resources
