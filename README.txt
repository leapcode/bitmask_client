========================================
=               LEAP                   =
=   The Internet Encryption Toolkit    =
========================================

Install
=======
python setup.py install

Running tests
=============
nosetests -v

Deps
====
apt-get install python-qt4 python-qt4-doc pyqt4-dev-tools

Hack
====

(recommended)
virtualenv .  # ensure your .gitignore knows about it
bin/activate

# you should probably simlink sip.so and PyQt4 to your system-wide
# install, there are some issues with it.

python setup.py develop  # ... TBD: finish develop howto.

Compiling resource/ui files
===========================
You should refresh resource/ui files every time you
change an image or a resource/ui (.ui / .qc). From
the root folder:

make ui
make resources
