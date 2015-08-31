environment setup in osx
========================

TODO:: REALLY old notes, adapting to newest flow.

basically you need this to setup your environment:

# check and consolidate

# install xcode and homebrew

# brew install python2.7
# brew install python-virtualenwrapper
# brew install qt
# brew install git
# brew install platypus
# brew install upx

Requirements
============
pyinstaller
-----------

You need the development version. do `python setup.py develop` inside your
virtualenv.

platypus (tested with latest macports)

... + install environment as usual,
      inside virtualenv.

Building the package
====================

Building the binary
-------------------
We use the scripts in openvpn/build.zsh
The packaging Makefile is expecting the final binary in the location::

    ../../openvpn/build/openvpn.leap

Running the build
-----------------
IMPORTANT: activate the VIRTUALENV FIRST!
(you will get an import error otherwise)

For running all steps at once::

    make pkg
