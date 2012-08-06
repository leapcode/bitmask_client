========================================
=               LEAP                   =
=  The LEAP Encryption Access Project  =
=   your internet encryption toolkit   =
========================================

Install
=======
python setup.py install

Running
=======

You need to set up a provider in your eip.cfg file:

cd ~/.config/leap
vim eip.cfg

[provider]
remote_ip = XXX.XXX.XXX.XXX

and then run:

leap --debug

(or python app.py --debug if you run it from the src/leap folder).

Running tests
=============
nosetests -v
[ currently broken ]

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
