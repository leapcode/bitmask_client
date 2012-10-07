LEAP                   
The LEAP Encryption Access Project
your internet encryption toolkit

Installation
=============

Dependencies
--------------
Listed in pkg/requirements.pip and pkg/test-requirements.pip

* python 2.6 or 2.7
* python setuptools
* qt4 libraries
* python-qt4
* python-gnutls == 1.1.9
* python-keyring
* python-nose, python-mock, python-coverage (if you want to run tests)

If you are on a debian-based system, you can run:

  apt-get install python-qt4 python-qt4-doc pyqt4-dev-tools python-gnutls libgnutls-dev python-setuptools python-nose

# **note**: I think setuptools is needed for build process only.
# we should separate what's needed as a lib dependency, and what's a dependency that has been debianized but
# still can be retrieved using pip.

If you are installing in a virtualenv:

  pip install -r pkg/requirements.pip

# **note**: I _think_ setuptools is needed for build process only.                     
# we should separate what's needed as a global lib dependency, and what's a dependency that
# still can be retrieved using pip.                                                  
                                                        
If you are installing in a virtualenv:                                               
  pip install -r pkg/requirements.pip


Install PyQt
------------
pip install PyQt will fail because PyQt4 does not use the standard setup.py mechanism.
Instead, they use configure.py which generates a Makefile.

python configure.py
make && make install

You can:

* (recommended) run pkg/postmkvenv.sh after creating your virtualenv. It will symlink to your global PyQt installation.
* install PyQt globally and make a virtualenv with --site-packages
* run pkg/install_pyqt.sh inside your virtualenv (with --no-site-packages)


Install
---------------

# need to run this if you are installing from the git source tree
# not needed if installing from a tarball.

python setup.py branding

# run this if you have installed previous versions before

python setup.py clean

python setup.py install # as root if installing globally.



Running the App
-----------------

If you're running a branded build, the script name will have a infix that
depends on your build flavor. Look for it in /usr/local/bin

% leap-springbok-client

In order to run in debub mode:

% leap-springbok-client --debug --logfile /tmp/leap.log

To see all options:

% leap-springbok-client --help


Development
==============

Hack
--------------

Some steps to be run when setting a development environment for the first time.

# recommended: enable a virtualenv to isolate your libraries.

% virtualenv .  # ensure your .gitignore knows about it
% source bin/activate

# make sure you're in the development branch

(leap_client)% git checkout develop

(leap_client)% pkg/postmkvenv.sh

(leap_client)% python setup.py branding
(leap_client)% python setup.py develop  

to avoid messing with the entry point and global versions installed,
it's recommended to run the app like this during development cycle:

(leap_client)% cd src/leap 
(leap_client)% python app.py --debug

Install testing dependencies
----------------------------

have a look at setup/test-requires
The ./run_tests.sh command should install all of them in your virtualenv for you.

Running tests
-------------

./run_tests.sh

force no virtualenv and create coverage reports:
./run_tests.sh -N -c

if you want to run specific tests, pass the (sub)module to nose:

nosetests leap.util

or

nosetests leap.util.test_leap_argparse

Colorized output
----------------
Install rednose locally and activate it.

  (leap_client)% pip install rednose
  (leap_client)% export NOSE_REDNOSE=1

enjoy :)

Tox
---
For running testsuite against all the supported python versions (currently 2.6 and 2.7), run:

  tox -v


Compiling resource/ui files
-----------------------------

You should refresh resource/ui files every time you
change an image or a resource/ui (.ui / .qc). From
the root folder:

make ui
make resources

As there are some tests to guard against unwanted resource updates,
you will have to update the resource hash in those failing tests.
