environment setup in osx
========================
(I rm'd my README by mistake at some point. Re-do).

basically you need this to setup your environment:

# check and consolidate

# install xcode and macports 
# port -v selfupdate
# port install python26
# port install python_select
# port select python python26
# port install py26-pyqt4
# port install py26-pip
# port install py26-virtualenv
# port install git-core
# port install platypus
# port install upx

Requirements
============
pyinstaller
-----------
Expected in ~/pyinstaller

You need the development version.
Tested with: 2.0.373

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
